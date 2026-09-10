"""Offline cohort reconciliation and historical observation boundaries."""

from datetime import datetime
from pathlib import Path
from typing import cast

import httpx
import pytest

from merge_carlo.cohort import _batch, collect_cohort
from merge_carlo.github import Collection, GitHubTransport, TransportLimits
from merge_carlo.store import ProjectedStore, StoreError, WorkspaceKey

pytestmark = pytest.mark.unit
START = datetime.fromisoformat("2026-01-01T00:00:00Z")
END = datetime.fromisoformat("2026-02-01T00:00:00Z")
NOW = datetime.fromisoformat("2026-03-01T00:00:00Z")


def pull(identifier: int, created: str = "2026-01-05T00:00:00Z", **fields: object) -> dict[str, object]:
    return dict(
        id=identifier,
        number=identifier + 10,
        state="open",
        created_at=created,
        updated_at=created,
        body="PRIVATE_BODY",
        **fields,
    )


def rows(data: dict[str, object], kind: str) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], data[kind])


def test_cohort_union_pagination_children_and_cutoff(tmp_path: Path) -> None:
    paths: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        paths.append(str(request.url))
        if request.url.path == "/repos/example/repo":
            return httpx.Response(200, json={"id": 91})
        if request.url.path.endswith("/pulls"):
            if request.url.params.get("state") == "open":
                return httpx.Response(200, json=[pull(1, "2020-01-01T00:00:00Z"), pull(2)])
            if request.url.params.get("page") == "2":
                return httpx.Response(200, json=[pull(2), pull(4, "2026-02-01T00:00:00Z")])
            closed = pull(3, closed_at="2026-01-08T00:00:00Z")
            closed["state"] = "closed"
            return httpx.Response(
                200,
                json=[closed, pull(2)],
                headers={"Link": '<https://api.github.com/repos/example/repo/pulls?page=2>; rel="next"'},
            )
        if request.url.path.endswith("/reviews"):
            return httpx.Response(
                200, json=[{"id": 5, "state": "APPROVED", "submitted_at": "2026-01-10T00:00:00Z"}] * 2
            )
        return httpx.Response(
            200,
            json=[
                {"id": 6, "event": "ready_for_review", "created_at": "2026-01-09T00:00:00Z"},
                {"id": 7, "event": "labeled", "label": {"name": "PRIVATE"}},
            ],
        )

    with (
        GitHubTransport(transport=httpx.MockTransport(respond)) as transport,
        ProjectedStore(tmp_path / "data.sqlite", WorkspaceKey.create(tmp_path / "key")) as store,
    ):
        manifest = collect_cohort(transport, store, "example/repo", START, END, clock=lambda: NOW)
        data = store.export(manifest.id)
        assert {row["id"] for row in rows(data, "pull_requests")} == {1, 2, 3}
        assert len(rows(data, "reviews")) == 3
        assert len(rows(data, "lifecycle_events")) == 3
        assert "PRIVATE" not in str(data)
        assert all(row["observed_at"] == "2026-03-01T00:00:00Z" for row in rows(data, "pull_requests"))
        assert store.historical(manifest.id, END)["pull_requests"] == []
        assert len(store.historical(manifest.id, END)["lifecycle_events"]) == 3
        assert store.historical(manifest.id, NOW)["pull_requests"] == data["pull_requests"]
        assert len(paths) == 10


def test_partial_resume_restarts_enumeration_and_preserves_on_interrupt(tmp_path: Path) -> None:
    phase = "partial"
    calls: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/repos/example/repo":
            return httpx.Response(200, json={"id": 91})
        if phase == "interrupt":
            raise KeyboardInterrupt
        if request.url.path.endswith("/pulls"):
            headers = {"Link": '<?page=2>; rel="next"'} if phase == "partial" else {}
            return httpx.Response(200, json=[pull(2)], headers=headers)
        return httpx.Response(200, json=[])

    with (
        GitHubTransport(transport=httpx.MockTransport(respond), limits=TransportLimits(max_pages=1)) as transport,
        ProjectedStore(tmp_path / "data.sqlite", WorkspaceKey.create(tmp_path / "key")) as store,
    ):
        first = collect_cohort(transport, store, "example/repo", START, END, clock=lambda: NOW)
        assert rows(store.export(first.id), "collection_status")[0]["status"] == "not_requested"
        assert any(row["status"] == "partial" for row in rows(store.export(first.id), "collection_status"))
        phase = "complete"
        second = collect_cohort(transport, store, "example/repo", START, END, resume=True, clock=lambda: NOW)
        assert first.id == second.id
        before = store.export(first.id)
        assert not any(row["status"] == "partial" for row in rows(before, "collection_status"))
        phase = "interrupt"
        with pytest.raises(KeyboardInterrupt):
            collect_cohort(transport, store, "example/repo", START, END, resume=True, clock=lambda: NOW)
        assert store.export(first.id) == before
        assert calls.count("/repos/example/repo/pulls") == 5


def test_reconciliation_prefers_newer_time_not_page_order() -> None:
    old = pull(1)
    new = {**old, "updated_at": "2026-01-05T00:00:00.100Z", "draft": True}
    for records in ([old, new], [new, old]):
        batch = _batch("pull_requests", [Collection("2022-11-28", "complete", None, records)], NOW)
        assert batch.status == "complete"
        assert batch.records[0]["draft"] is True
    conflict = {**old, "draft": False}
    a = _batch("pull_requests", [Collection("2022-11-28", "complete", None, [old, conflict])], NOW)
    b = _batch("pull_requests", [Collection("2022-11-28", "complete", None, [conflict, old])], NOW)
    assert a == b
    assert (a.status, a.reason) == ("partial", "invalid_payload")


@pytest.mark.parametrize("event", [None, [], {"secret": "PRIVATE"}])
def test_malformed_event_is_partial_not_silently_complete(event: object) -> None:
    batch = _batch("lifecycle_events", [Collection("2022-11-28", "complete", None, [{"event": event}])], NOW, 1)
    assert (batch.status, batch.reason, batch.records) == ("partial", "invalid_payload", [])


def test_invalid_repository_identity_is_static(tmp_path: Path) -> None:
    with (
        GitHubTransport(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"id": "PRIVATE"}))
        ) as transport,
        ProjectedStore(tmp_path / "data.sqlite", WorkspaceKey.create(tmp_path / "key")) as store,
    ):
        with pytest.raises(StoreError, match="invalid collection input") as error:
            collect_cohort(transport, store, "example/repo", START, END)
        assert "PRIVATE" not in str(error.value)


def test_boundaries_child_pagination_and_statuses(tmp_path: Path) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/example/repo":
            return httpx.Response(200, json={"id": 91})
        if path.endswith("/pulls"):
            return httpx.Response(
                200,
                json=[
                    {**pull(1, "2025-01-01T00:00:00Z"), "state": "closed", "closed_at": "2025-12-31T23:59:59Z"},
                    {**pull(2, "2025-01-01T00:00:00Z"), "state": "closed", "closed_at": "2026-01-01T00:00:00Z"},
                    pull(3, "2026-01-01T00:00:00Z"),
                    {**pull(4, "2025-01-01T00:00:00Z"), "state": "closed"},
                ],
            )
        if path.endswith("/reviews"):
            if request.url.params.get("page") == "2":
                return httpx.Response(403)
            return httpx.Response(
                200, json=[{"id": 81, "state": "COMMENTED"}], headers={"Link": '<?page=2>; rel="next"'}
            )
        return httpx.Response(404)

    with (
        GitHubTransport(transport=httpx.MockTransport(respond)) as transport,
        ProjectedStore(tmp_path / "data.sqlite", WorkspaceKey.create(tmp_path / "key")) as store,
    ):
        manifest = collect_cohort(transport, store, "example/repo", START, END, clock=lambda: NOW)
        data = store.export(manifest.id)
        assert {row["id"] for row in rows(data, "pull_requests")} == {2, 3, 4}
        assert len(rows(data, "reviews")) == 3
        statuses = {
            (row["kind"], row["pr_id"]): (row["status"], row["reason"]) for row in rows(data, "collection_status")
        }
        assert statuses["reviews", 2] == ("partial", "permission")
        assert statuses["lifecycle_events", 3] == ("unavailable", "unavailable")
        assert statuses["pull_requests", None] == ("complete", None)


@pytest.mark.parametrize("change", ["repository", "start", "end", "version", "missing", "no_resume"])
def test_resume_rejects_incompatible_identity(tmp_path: Path, change: str) -> None:
    repository_id = 91

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": repository_id} if request.url.path == "/repos/example/repo" else [])

    with (
        GitHubTransport(transport=httpx.MockTransport(respond)) as transport,
        ProjectedStore(tmp_path / "data.sqlite", WorkspaceKey.create(tmp_path / "key")) as store,
    ):
        if change != "missing":
            collect_cohort(transport, store, "example/repo", START, END, clock=lambda: NOW)
        repository_id = 92 if change == "repository" else 91
        transport.api_version = "2026-03-10" if change == "version" else "2022-11-28"
        with pytest.raises(StoreError, match="resume"):
            collect_cohort(
                transport,
                store,
                "example/repo",
                END if change == "start" else START,
                NOW if change in {"start", "end"} else END,
                resume=change != "no_resume",
            )


def test_initial_interrupt_leaves_incomplete_manifest(tmp_path: Path) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/example/repo":
            return httpx.Response(200, json={"id": 91})
        raise KeyboardInterrupt

    with (
        GitHubTransport(transport=httpx.MockTransport(respond)) as transport,
        ProjectedStore(tmp_path / "data.sqlite", WorkspaceKey.create(tmp_path / "key")) as store,
    ):
        with pytest.raises(KeyboardInterrupt):
            collect_cohort(transport, store, "example/repo", START, END)
        manifest = store.manifests()[0]
        assert rows(store.export(manifest.id), "collection_status") == [
            {"kind": "pull_requests", "pr_id": None, "status": "partial", "reason": "interrupted"}
        ]


@pytest.mark.parametrize(
    "repository", ["https://evil/repo", "example/../other", "example/..", "example/repo?token=PRIVATE"]
)
def test_invalid_path_never_reaches_transport(tmp_path: Path, repository: str) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        pytest.fail("invalid repository reached transport")

    with (
        GitHubTransport(transport=httpx.MockTransport(respond)) as transport,
        ProjectedStore(tmp_path / "data.sqlite", WorkspaceKey.create(tmp_path / "key")) as store,
        pytest.raises(StoreError, match="invalid repository"),
    ):
        collect_cohort(transport, store, repository, START, END)
