"""Synthetic, offline GitHub transport tests."""

import inspect
import logging
from collections.abc import Iterator

import httpx
import pytest

from merge_carlo.github import GitHubTransport, TransportLimits

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def synthetic_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)


def test_paginate_headers_and_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "private-token")
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "GET"
        assert request.url.scheme == "https"
        assert request.url.host == "api.github.com"
        assert request.headers["Authorization"] == "Bearer private-token"
        assert request.headers["X-GitHub-Api-Version"] == "2022-11-28"
        assert request.headers["Accept"] == "application/vnd.github+json"
        assert request.headers["User-Agent"] == "merge-carlo"
        if len(requests) == 1:
            return httpx.Response(200, json=[{"id": 7}], headers={"Link": '</repos/a/b/pulls?page=2>; rel="next"'})
        return httpx.Response(200, json=[{"id": 19}])

    with GitHubTransport(transport=httpx.MockTransport(respond)) as github:
        result = github.collect("/repos/a/b/pulls")
    assert result.records == [{"id": 7}, {"id": 19}]
    assert result.status == "complete"
    assert result.api_version == "2022-11-28"
    assert len(requests) == 2


@pytest.mark.parametrize("kind", ["Link", "Location"])
def test_refuses_cross_origin(kind: str) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        target = "https://evil.example/steal"
        return httpx.Response(
            302 if kind == "Location" else 200,
            headers={kind: target if kind == "Location" else f'<{target}>; rel="next"'},
            json=[{"id": 1}],
        )

    with GitHubTransport(transport=httpx.MockTransport(respond)) as github:
        result = github.collect("/repos/a/b/pulls")
    assert result.status != "complete"
    assert result.reason == "unsafe_url"
    assert len(requests) == 1


@pytest.mark.parametrize(
    "status,headers,delay",
    [
        (429, {"Retry-After": "3"}, 3),
        (403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "105"}, 5),
        (429, {}, 60),
        (503, {}, 1),
    ],
)
def test_retry(status: int, headers: dict[str, str], delay: int) -> None:
    waits: list[float] = []
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, headers=headers) if calls == 1 else httpx.Response(200, json=[])

    with GitHubTransport(
        transport=httpx.MockTransport(respond), sleep=waits.append, clock=lambda: 100, jitter=lambda: 0.25
    ) as github:
        assert github.collect("/repos/a/b/pulls").status == "complete"
    assert waits == [delay + 0.25]
    assert calls == 2


@pytest.mark.parametrize("status,reason", [(401, "authentication"), (403, "permission"), (404, "unavailable")])
def test_denial_is_not_retried(
    status: int, reason: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "private-token")
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, text="private-token")

    with GitHubTransport(transport=httpx.MockTransport(respond)) as github:
        result = github.collect("/repos/a/b/pulls")
    assert result.status == "unavailable"
    assert result.reason == reason
    assert calls == 1
    assert "private-token" not in repr(result) + caplog.text + repr(github)


@pytest.mark.parametrize(
    "limits,reason",
    [
        (TransportLimits(max_requests=1), "request_limit"),
        (TransportLimits(max_pages=1), "page_limit"),
        (TransportLimits(max_records=1), "record_limit"),
        (TransportLimits(max_payload_bytes=1), "payload_limit"),
    ],
)
def test_limits(limits: TransportLimits, reason: str) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": 1}, {"id": 2}], headers={"Link": '</next>; rel="next"'})

    with GitHubTransport(limits=limits, transport=httpx.MockTransport(respond)) as github:
        result = github.collect("/repos/a/b/pulls")
    assert result.status == "partial"
    assert result.reason == reason


def test_conditional_and_custom_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    def respond(request: httpx.Request) -> httpx.Response:
        assert "authorization" not in request.headers
        assert request.headers["X-GitHub-Api-Version"] == "2026-03-10"
        assert request.headers["If-None-Match"] == '"abc"'
        assert request.headers["If-Modified-Since"] == "yesterday"
        assert request.extensions["timeout"] == {"connect": 4, "read": 4, "write": 4, "pool": 4}
        return httpx.Response(304)

    with GitHubTransport(
        api_version="2026-03-10", limits=TransportLimits(timeout=4), transport=httpx.MockTransport(respond)
    ) as github:
        result = github.collect("/pulls", etag='"abc"', last_modified="yesterday")
    assert result.status == "unavailable"
    assert result.reason == "not_modified"
    assert result.records == []
    assert result.api_version == "2026-03-10"


@pytest.mark.parametrize(
    "path",
    [
        "http://api.github.com/x",
        "https://api.github.com:444/x",
        "https://user@api.github.com/x",
        "https://evil.test/x",
        "/x#fragment",
    ],
)
def test_invalid_target_never_sends(path: str) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        pytest.fail("unsafe request sent")

    with GitHubTransport(transport=httpx.MockTransport(respond)) as github:
        assert github.collect(path).reason == "unsafe_url"


def test_origin_is_not_configurable() -> None:
    assert "api_origin" not in inspect.signature(GitHubTransport).parameters


@pytest.mark.parametrize("version", ["", "hello", "2022\n", "é"])
def test_invalid_version(version: str) -> None:
    with pytest.raises(ValueError, match="invalid API version"):
        GitHubTransport(api_version=version)


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_retry_exhaustion(status: int) -> None:
    calls = 0
    waits: list[float] = []

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status)

    with GitHubTransport(
        limits=TransportLimits(max_retries=2),
        transport=httpx.MockTransport(respond),
        sleep=waits.append,
        clock=lambda: 0,
        jitter=lambda: 0.5,
    ) as github:
        result = github.collect("/pulls")
    assert result.reason == "retry_limit"
    assert calls == 3
    assert waits == ([60.5, 120.5] if status == 429 else [1.5, 2.5])


@pytest.mark.parametrize(
    "headers,delay",
    [
        ({"Retry-After": "Thu, 01 Jan 1970 00:02:00 GMT"}, 20),
        ({"Retry-After": "invalid"}, 60),
        ({"Retry-After": "-1"}, 60),
        ({"Retry-After": "1.5"}, 60),
        ({"Retry-After": "+1"}, 60),
        ({"Retry-After": "1e1"}, 60),
        ({"x-ratelimit-remaining": "0"}, 60),
        ({"x-ratelimit-remaining": "0", "x-ratelimit-reset": "invalid"}, 60),
        ({"Retry-After": "3", "x-ratelimit-remaining": "0", "x-ratelimit-reset": "108"}, 8),
    ],
)
def test_retry_header_variants(headers: dict[str, str], delay: int) -> None:
    calls = 0
    waits: list[float] = []

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers=headers) if calls == 1 else httpx.Response(200, json=[])

    with GitHubTransport(
        transport=httpx.MockTransport(respond), sleep=waits.append, clock=lambda: 100, jitter=lambda: 0
    ) as github:
        assert github.collect("/pulls").status == "complete"
    assert waits == [delay]


@pytest.mark.parametrize("retry_after", ["9999", "nan", "inf"])
def test_excessive_wait_stops(retry_after: str) -> None:
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"Retry-After": retry_after})

    with GitHubTransport(transport=httpx.MockTransport(respond), clock=lambda: 0, jitter=lambda: 0) as github:
        assert github.collect("/pulls").reason == "wait_limit"
    assert calls == 1


@pytest.mark.parametrize("recover", [True, False])
def test_network_retry_and_secret_error(
    recover: bool, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "private-token")
    calls = 0
    waits: list[float] = []

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if recover and calls == 2:
            return httpx.Response(200, json=[])
        raise httpx.ConnectError("private-token", request=request)

    with GitHubTransport(
        limits=TransportLimits(max_retries=1),
        transport=httpx.MockTransport(respond),
        sleep=waits.append,
        clock=lambda: 0,
        jitter=lambda: 0,
    ) as github:
        result = github.collect("/pulls")
    assert calls == 2
    assert waits == [1]
    assert result.reason == (None if recover else "network_error")
    assert "private-token" not in str(result) + caplog.text


@pytest.mark.parametrize(
    "payload,reason",
    [
        (b"not json", "invalid_response"),
        (b"{}", "invalid_payload"),
        (b"[1]", "invalid_payload"),
        (b'[{"body":"private-token"}]', "credential_in_response"),
    ],
)
def test_invalid_payload(payload: bytes, reason: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "private-token")
    with GitHubTransport(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=payload))) as github:
        result = github.collect("/pulls")
    assert result.status == "unavailable"
    assert result.reason == reason
    assert result.records == []


def test_redirect_validators_and_exact_limits() -> None:
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(301, headers={"Location": "/new"})
        assert request.url.path == "/new"
        assert "if-none-match" not in request.headers
        assert "if-modified-since" not in request.headers
        return httpx.Response(200, content=b'[{"id":3}]', headers={"ETag": '"new"', "Last-Modified": "today"})

    with GitHubTransport(
        limits=TransportLimits(max_requests=2, max_pages=1, max_records=1, max_payload_bytes=10),
        transport=httpx.MockTransport(respond),
    ) as github:
        result = github.collect("/old", etag='"old"', last_modified="yesterday")
    assert result.status == "complete"
    assert result.records == [{"id": 3}]
    assert result.etag == '"new"'
    assert result.last_modified == "today"


def test_partial_preserves_records_and_clears_validators() -> None:
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(200, json=[{"id": 9}], headers={"Link": '</next>; rel="next"', "ETag": '"old"'})
        assert "if-none-match" not in request.headers
        assert "if-modified-since" not in request.headers
        return httpx.Response(403)

    with GitHubTransport(transport=httpx.MockTransport(respond)) as github:
        result = github.collect("/old", etag='"old"', last_modified="yesterday")
    assert result.status == "partial"
    assert result.reason == "permission"
    assert result.records == [{"id": 9}]
    assert result.etag is None


def test_pagination_cycle() -> None:
    with GitHubTransport(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=[], headers={"Link": '</pulls>; rel="next"'})
        )
    ) as github:
        assert github.collect("/pulls").reason == "pagination_cycle"


def test_primary_limit_on_success_delays_next_collection() -> None:
    waits: list[float] = []
    with GitHubTransport(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json=[], headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "107"}
            )
        ),
        clock=lambda: 100,
        sleep=waits.append,
    ) as github:
        assert github.collect("/pulls").status == "complete"
        assert github.collect("/reviews").status == "complete"
    assert waits == [7]


def test_secondary_limit_without_headers() -> None:
    calls = 0
    waits: list[float] = []

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return (
            httpx.Response(403, json={"message": "You have exceeded a secondary rate limit."})
            if calls == 1
            else httpx.Response(200, json=[])
        )

    with GitHubTransport(
        transport=httpx.MockTransport(respond), clock=lambda: 0, sleep=waits.append, jitter=lambda: 0
    ) as github:
        assert github.collect("/pulls").status == "complete"
    assert waits == [60]


def test_dependency_diagnostics_are_private(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "private-token")
    caplog.set_level(logging.DEBUG)

    def respond(request: httpx.Request) -> httpx.Response:
        for name in ("httpcore.connection", "httpcore.http11"):
            logging.getLogger(name).debug("receive_response_headers.complete %r", {"echo": "private-token"})
        return httpx.Response(200, json=[])

    with GitHubTransport(transport=httpx.MockTransport(respond)) as github:
        assert github.collect("/pulls").status == "complete"
    assert "private-token" not in caplog.text
    logging.getLogger("httpcore.http11").debug("outside transport")
    assert "outside transport" in caplog.text


@pytest.mark.parametrize("validator", ["bad\r\nheader", "é", "\x7f"])
def test_invalid_validators_never_send(validator: str) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        pytest.fail("invalid header sent")

    with GitHubTransport(transport=httpx.MockTransport(respond)) as github:
        result = github.collect("/pulls", etag=validator)
    assert result.reason == "invalid_validator"
    assert result.status == "unavailable"


@pytest.mark.parametrize("token", ["bad token", "bad\nheader", "é", "\x7f"])
def test_invalid_credential_error_is_static(token: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", token)
    with pytest.raises(ValueError, match="^invalid GitHub credential$"):
        GitHubTransport()


def test_token_url_and_validators_are_not_exposed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "private-token")
    with GitHubTransport(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json=[], headers={"ETag": "private-token", "Last-Modified": "private-token"}
            )
        )
    ) as github:
        assert github.collect("/pulls?token=private-token").reason == "unsafe_url"
        result = github.collect("/pulls")
    assert result.status == "complete"
    assert result.etag is None
    assert result.last_modified is None


def test_stream_limit_closes_without_reading_rest() -> None:
    class Stream(httpx.SyncByteStream):
        closed = False

        def __iter__(self) -> Iterator[bytes]:
            yield b"x" * 65536
            pytest.fail("read beyond payload budget")

        def close(self) -> None:
            self.closed = True

    stream = Stream()
    with GitHubTransport(
        limits=TransportLimits(max_payload_bytes=10),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=stream)),
    ) as github:
        result = github.collect("/pulls")
    assert result.status == "partial"
    assert result.reason == "payload_limit"
    assert stream.closed


def test_compression_refused_before_stream_read() -> None:
    class Stream(httpx.SyncByteStream):
        def __iter__(self) -> Iterator[bytes]:
            pytest.fail("compressed response consumed")
            yield b""

    with GitHubTransport(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, headers={"Content-Encoding": "gzip"}, stream=Stream())
        )
    ) as github:
        result = github.collect("/pulls")
    assert result.status == "partial"
    assert result.reason == "unsupported_encoding"


def test_record_limit_preserves_prefix() -> None:
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200, json=[{"id": calls * 10 + 1}, {"id": calls * 10 + 2}], headers={"Link": '</next>; rel="next"'}
        )

    with GitHubTransport(limits=TransportLimits(max_records=3), transport=httpx.MockTransport(respond)) as github:
        result = github.collect("/pulls")
    assert result.status == "partial"
    assert result.reason == "record_limit"
    assert result.records == [{"id": 11}, {"id": 12}, {"id": 21}]
    assert calls == 2


def test_retry_budget_resets_per_page_and_multi_page_has_no_validators() -> None:
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls in (1, 3):
            return httpx.Response(503)
        return httpx.Response(
            200,
            json=[{"id": calls}],
            headers={"ETag": "tag", "Last-Modified": "now", **({"Link": '</next>; rel="next"'} if calls == 2 else {})},
        )

    with GitHubTransport(
        limits=TransportLimits(max_retries=1),
        transport=httpx.MockTransport(respond),
        sleep=lambda _: None,
        clock=lambda: 0,
        jitter=lambda: 0,
    ) as github:
        result = github.collect("/pulls")
    assert result.status == "complete"
    assert result.records == [{"id": 2}, {"id": 4}]
    assert result.etag is None
    assert result.last_modified is None
    assert calls == 4
