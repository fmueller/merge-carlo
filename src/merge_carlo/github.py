"""Serial, bounded, GET-only GitHub REST transport. No payload persistence."""

import json
import logging
import math
import os
import random
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from types import TracebackType
from typing import Literal, Self

import httpx
from pydantic import BaseModel, ConfigDict, Field


class _UnsafeURL(ValueError):
    """A static diagnostic for refused URLs."""


@contextmanager
def _private_diagnostics() -> Iterator[None]:
    # HTTPTransport uses HTTP/1.1 without proxies. httpcore DEBUG traces include
    # remote headers and exception text. Suppress only this thread's low-level
    # traces during transport operations, leaving application logging untouched.
    thread = threading.get_ident()

    def other_thread(record: logging.LogRecord) -> bool:
        return record.thread != thread

    loggers = [logging.getLogger(name) for name in ("httpcore.connection", "httpcore.http11")]
    for logger in loggers:
        logger.addFilter(other_thread)
    try:
        yield
    finally:
        for logger in loggers:
            logger.removeFilter(other_thread)


class TransportLimits(BaseModel):
    """Per-collection budgets; retries and redirects consume request budget."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    max_requests: int = Field(default=1000, gt=0)
    max_pages: int = Field(default=100, gt=0)
    max_payload_bytes: int = Field(default=8_000_000, gt=0)
    max_records: int = Field(default=100_000, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout: float = Field(default=30, gt=0, allow_inf_nan=False)
    max_wait: float = Field(default=3600, ge=0, allow_inf_nan=False)


@dataclass(frozen=True)
class Collection:
    """Extraction metadata includes the API version, even for failed collections.

    Records are transient raw JSON objects, not a projected dataset. A 304 has
    no records and requires the caller's previously stored representation.
    """

    api_version: str
    status: Literal["complete", "partial", "unavailable"]
    reason: str | None
    records: list[dict[str, object]] = field(repr=False)
    etag: str | None = None
    last_modified: str | None = None


class GitHubTransport:
    """Owns a connection pool; use as a context manager. Reads GITHUB_TOKEN.

    An injected transport is trusted infrastructure, intended for offline tests.
    No arbitrary request method, caller headers, cookies, proxy environment, or
    automatic redirects are exposed. A lock serializes complete collections.
    """

    def __init__(
        self,
        *,
        api_version: str = "2022-11-28",
        limits: TransportLimits | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self._token = os.environ.get("GITHUB_TOKEN", "")
        self._origin = httpx.URL("https://api.github.com")
        if not api_version or not api_version.isascii() or any(c not in "0123456789-" for c in api_version):
            raise ValueError("invalid API version")
        if self._token and (not self._token.isascii() or any(ord(c) < 33 or ord(c) == 127 for c in self._token)):
            raise ValueError("invalid GitHub credential")
        self.api_version = api_version
        self.limits = limits or TransportLimits()
        self._transport = transport if transport is not None else httpx.HTTPTransport(trust_env=False)
        self._sleep, self._clock, self._jitter = sleep, clock, jitter
        self._lock = threading.Lock()
        self._ready_at = 0.0

    def _url(self, value: str) -> httpx.URL:
        try:
            url = httpx.URL(value)
            if (
                url.scheme != "https"
                or not url.host
                or url.userinfo
                or url.fragment
                or (self._token and self._token in str(url))
            ):
                raise ValueError
        except (ValueError, httpx.InvalidURL):
            raise _UnsafeURL("unsafe_url") from None
        return url

    def _target(self, current: httpx.URL, target: str) -> httpx.URL:
        url = self._url(str(current.join(target)))
        if (url.scheme, url.host, url.port) != (self._origin.scheme, self._origin.host, self._origin.port):
            raise _UnsafeURL("unsafe_url")
        return url

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        with self._lock, _private_diagnostics():
            self._transport.close()

    def _delay(self, headers: httpx.Headers, fallback: float) -> float:
        delays: list[float] = []
        retry = headers.get("retry-after")
        if retry is not None:
            try:
                delay = float(retry)
                if math.isfinite(delay) and not (retry.isascii() and retry.isdecimal()):
                    delay = fallback
            except ValueError:
                try:
                    delay = parsedate_to_datetime(retry).timestamp() - self._clock()
                except (ValueError, TypeError, OverflowError):
                    delay = fallback
            delays.append(delay)
        if headers.get("x-ratelimit-remaining") == "0":
            try:
                delays.append(float(headers["x-ratelimit-reset"]) - self._clock())
            except (KeyError, ValueError):
                delays.append(max(60, fallback))
        if any(not math.isfinite(delay) for delay in delays):
            return self.limits.max_wait + 1
        return max(0, max(delays, default=fallback))

    def collect(
        self, path: str, *, etag: str | None = None, last_modified: str | None = None, single: bool = False
    ) -> Collection:
        """Fetch a JSON object-array collection, following Link rel=next.

        Conditional headers apply only to the initial resource. `not_modified`
        is unavailable, never a falsely complete empty collection. Validators
        are returned only for a single-page complete response.
        """
        with self._lock, _private_diagnostics():
            return self._collect(path, etag, last_modified, single)

    def _collect(self, path: str, etag: str | None, last_modified: str | None, single: bool) -> Collection:
        records: list[dict[str, object]] = []
        pages = requests = retries = 0
        seen: set[str] = set()

        def failed(reason: str, *, partial: bool = False) -> Collection:
            return Collection(self.api_version, "partial" if pages or partial else "unavailable", reason, records)

        try:
            url = self._target(self._origin, path)
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": "merge-carlo",
                "X-GitHub-Api-Version": self.api_version,
                "Accept-Encoding": "identity",
            }
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"
            for name, value in (("If-None-Match", etag), ("If-Modified-Since", last_modified)):
                if value is not None:
                    if not value.isascii() or any(ord(c) < 32 or ord(c) == 127 for c in value):
                        return failed("invalid_validator")
                    headers[name] = value
            while True:
                if pages >= self.limits.max_pages:
                    return failed("page_limit", partial=True)
                if requests >= self.limits.max_requests:
                    return failed("request_limit", partial=True)
                wait = max(0, self._ready_at - self._clock())
                if wait > self.limits.max_wait:
                    return failed("wait_limit", partial=True)
                if wait:
                    self._sleep(wait)
                requests += 1
                request = httpx.Request(
                    "GET",
                    url,
                    headers=headers,
                    extensions={"timeout": dict.fromkeys(("connect", "read", "write", "pool"), self.limits.timeout)},
                )
                try:
                    response = self._transport.handle_request(request)
                except httpx.TransportError:
                    if retries >= self.limits.max_retries:
                        return failed("network_error")
                    self._ready_at = self._clock() + 2**retries + self._jitter()
                    retries += 1
                    continue
                try:
                    response.request = request
                    status = response.status_code
                    if 300 <= status < 400 and status != 304:
                        url = self._target(url, response.headers["location"])
                        headers.pop("If-None-Match", None)
                        headers.pop("If-Modified-Since", None)
                        continue
                    payload = bytearray()
                    if status in (200, 403):
                        if response.headers.get("content-encoding", "identity") != "identity":
                            return failed("unsupported_encoding", partial=True)
                        for chunk in response.iter_bytes(chunk_size=65536):
                            if len(payload) + len(chunk) > self.limits.max_payload_bytes:
                                return failed("payload_limit", partial=True)
                            payload.extend(chunk)
                    rate_limited = status == 429 or (
                        status == 403
                        and (
                            "retry-after" in response.headers
                            or response.headers.get("x-ratelimit-remaining") == "0"
                            or b"secondary rate limit" in payload.lower()
                        )
                    )
                    if rate_limited or status in (500, 502, 503, 504):
                        if retries >= self.limits.max_retries:
                            return failed("retry_limit")
                        fallback = (60 if rate_limited else 1) * 2**retries
                        delay = max(2**retries, self._delay(response.headers, fallback))
                        self._ready_at = self._clock() + delay + self._jitter()
                        retries += 1
                        continue
                    if status != 200:
                        return failed(
                            {401: "authentication", 403: "permission", 304: "not_modified"}.get(status, "unavailable")
                        )
                    if self._token and self._token.encode() in payload:
                        return failed("credential_in_response")
                    data = json.loads(payload)
                    if single:
                        if not isinstance(data, dict):
                            return failed("invalid_payload")
                        data = [data]
                    if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
                        return failed("invalid_payload")
                    room = self.limits.max_records - len(records)
                    records.extend(data[:room])
                    pages += 1
                    if len(data) > room:
                        return failed("record_limit", partial=True)
                    if response.headers.get("x-ratelimit-remaining") == "0":
                        self._ready_at = self._clock() + self._delay(response.headers, 0)
                    next_url = response.links.get("next", {}).get("url")
                    if not next_url:
                        etag = response.headers.get("etag") if pages == 1 else None
                        last_modified = response.headers.get("last-modified") if pages == 1 else None
                        if self._token:
                            etag = None if etag and self._token in etag else etag
                            last_modified = None if last_modified and self._token in last_modified else last_modified
                        return Collection(self.api_version, "complete", None, records, etag, last_modified)
                    seen.add(str(url))
                    url = self._target(url, next_url)
                    if str(url) in seen:
                        return failed("pagination_cycle")
                    if len(records) >= self.limits.max_records:
                        return failed("record_limit", partial=True)
                    headers.pop("If-None-Match", None)
                    headers.pop("If-Modified-Since", None)
                    retries = 0
                finally:
                    response.close()
        except _UnsafeURL:
            return failed("unsafe_url")
        except (httpx.HTTPError, httpx.InvalidURL, ValueError, KeyError, UnicodeError, RecursionError):
            # Never interpolate a URL, credential, response, or underlying error.
            return failed("invalid_response")
