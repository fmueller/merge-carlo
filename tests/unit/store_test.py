"""Projected-store contracts exercised with synthetic observations only."""

import hashlib
import hmac
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from merge_carlo import store as store_module
from merge_carlo.store import Batch, Manifest, ProjectedStore, StoreError, WorkspaceKey

pytestmark = pytest.mark.unit
STAMP = "2026-01-02T03:04:05Z"


def manifest(number: int = 1, retrieved_at: str = STAMP) -> Manifest:
    return Manifest(
        id=UUID(int=number),
        repository_id=17,
        api_version="2022-11-28",
        analysis_start=datetime.fromisoformat("2026-01-01T00:00:00Z"),
        analysis_end=datetime.fromisoformat("2026-02-01T00:00:00Z"),
        retrieved_at=datetime.fromisoformat(retrieved_at),
    )


def pull(number: int = 7) -> dict[str, object]:
    return {
        "id": number,
        "number": number + 10,
        "state": "open",
        "created_at": STAMP,
        "updated_at": STAMP,
        "user": {"id": 42, "type": "User", "login": "private-login"},
    }


@pytest.fixture
def key(tmp_path: Path) -> WorkspaceKey:
    return WorkspaceKey.create(tmp_path / "private")


def test_migration_reopen_foreign_keys_and_future_version(tmp_path: Path, key: WorkspaceKey) -> None:
    path = tmp_path / "observations.sqlite"
    for _ in range(2):
        with ProjectedStore(path, key) as store:
            assert store.schema_version == 1
            store.save(manifest(), [Batch("pull_requests", [pull()])])
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT version FROM schema_migrations").fetchall() == [(1,)]
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        db.execute("INSERT INTO schema_migrations VALUES (2)")
    with pytest.raises(StoreError, match="unsupported schema"):
        ProjectedStore(path, key)


def test_projection_export_and_privacy(tmp_path: Path, key: WorkspaceKey) -> None:
    secrets = ["BODY_SECRET", "PATCH_SECRET", "a@private.example", "TOKEN_SECRET", "private-login"]
    raw = pull()
    raw.update(
        body=secrets[0],
        patch=secrets[1],
        email=secrets[2],
        token=secrets[3],
        description="DESCRIPTION_SECRET",
        diff="DIFF_SECRET",
        message="MESSAGE_SECRET",
        avatar_url="AVATAR_SECRET",
        output={"text": "OUTPUT_SECRET"},
    )
    batches = [
        Batch("pull_requests", [raw]),
        Batch(
            "reviews",
            [
                {
                    "id": 11,
                    "state": "APPROVED",
                    "submitted_at": STAMP,
                    "user": {"id": 42, "type": "Bot", "email": secrets[2]},
                    "body": secrets[0],
                }
            ],
            pr_id=7,
        ),
        Batch(
            "lifecycle_events",
            [
                {
                    "id": 12,
                    "event": "ready_for_review",
                    "created_at": STAMP,
                    "actor": {"id": 42, "type": "User"},
                    "body": secrets[0],
                }
            ],
            pr_id=7,
        ),
        Batch(
            "ci_observations",
            [
                {
                    "id": 13,
                    "status": "completed",
                    "conclusion": "success",
                    "started_at": STAMP,
                    "completed_at": STAMP,
                    "output": secrets[0],
                }
            ],
            pr_id=7,
        ),
        Batch(
            "derived_features",
            [
                {
                    "id": 7,
                    "ready_at": STAMP,
                    "readiness_basis": "observed_event",
                    "origin": "unknown",
                    "basis": "derived",
                    "body": secrets[0],
                }
            ],
            pr_id=7,
        ),
    ]
    path = tmp_path / "observations.sqlite"
    with ProjectedStore(path, key) as store:
        store.save(manifest(), batches)
        exported = store.export(manifest().id)
        assert exported["schema_version"] == 1
        text = json.dumps(exported)
        expected = hmac.new(
            (tmp_path / "private" / "actor.key").read_bytes(), b"github-actor:42", hashlib.sha256
        ).hexdigest()
        assert text.count(expected) == 3
        assert '"origin": "unknown"' in text
        assert '"type": "Bot"' in text
        assert exported["reviews"] == [
            {
                "id": 11,
                "pr_id": 7,
                "state": "APPROVED",
                "submitted_at": STAMP,
                "user": {"id": expected, "type": "Bot"},
                "commit_id": None,
            }
        ]
        assert exported["manifest"] == {
            "repository_id": 17,
            "api_version": "2022-11-28",
            "analysis_start": "2026-01-01T00:00:00Z",
            "analysis_end": "2026-02-01T00:00:00Z",
        }
        first_hash = store.content_hash(manifest().id)
        store.save(manifest(2), list(reversed(batches)))
        assert store.content_hash(manifest(2).id) == first_hash
        # Replacing a populated extraction removes its children and old statuses.
        store.save(manifest(), [Batch("pull_requests", [pull(8)])])
        replacement = store.export(manifest().id)
        for name in ("reviews", "lifecycle_events", "ci_observations", "derived_features"):
            assert replacement[name] == []
    for forbidden in secrets + [
        "DESCRIPTION_SECRET",
        "DIFF_SECRET",
        "MESSAGE_SECRET",
        "AVATAR_SECRET",
        "OUTPUT_SECRET",
    ]:
        assert forbidden not in text
        assert forbidden.encode() not in path.read_bytes()
    assert (tmp_path / "private").stat().st_mode & 0o777 == 0o700
    assert (tmp_path / "private" / "actor.key").stat().st_mode & 0o777 == 0o600
    assert WorkspaceKey(tmp_path / "private").actor(42) == key.actor(42)
    assert WorkspaceKey.create(tmp_path / "other").actor(42) != key.actor(42)


def test_hash_normalization_dedup_order_and_retrieval_independence(tmp_path: Path, key: WorkspaceKey) -> None:
    with ProjectedStore(tmp_path / "store.sqlite", key) as store:
        a, b = pull(7), pull(8)
        equivalent = dict(a, created_at="2026-01-02T04:04:05+01:00")
        store.save(manifest(), [Batch("pull_requests", [a, b, a])])
        first = store.content_hash(manifest().id)
        store.save(manifest(2, "2026-02-02T00:00:00Z"), [Batch("pull_requests", [b, equivalent])])
        assert store.content_hash(manifest(2).id) == first
        exported = store.export(manifest().id)
        assert (
            first
            == hashlib.sha256(
                json.dumps(exported, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            ).hexdigest()
        )
        store.save(manifest(3), [Batch("pull_requests", [dict(a, state="closed"), b])])
        assert store.content_hash(manifest(3).id) != first


def test_atomic_replacement_orphan_and_conflicting_duplicate(tmp_path: Path, key: WorkspaceKey) -> None:
    path = tmp_path / "store.sqlite"
    with ProjectedStore(path, key) as store:
        store.save(manifest(), [Batch("pull_requests", [pull()])])
        before = store.export(manifest().id)
        for batches in [
            [Batch("reviews", [{"id": 11, "state": "APPROVED"}], pr_id=99)],
            [Batch("pull_requests", [pull(), dict(pull(), state="closed")])],
            [Batch("pull_requests", [dict(pull(), id="DROP TABLE pull_requests;TOKEN_SECRET")])],
        ]:
            with pytest.raises(StoreError) as error:
                store.save(manifest(), batches)
            assert "TOKEN_SECRET" not in str(error.value)
            assert store.export(manifest().id) == before
        # A successful replace removes obsolete children, not the other extraction.
        store.save(manifest(2), [Batch("pull_requests", [pull(8)])])
        store.save(manifest(), [Batch("pull_requests", [pull(9)])])
        assert store.export(manifest(2).id)["pull_requests"] != store.export(manifest().id)["pull_requests"]


def test_statuses_and_empty_missing_are_distinct(tmp_path: Path, key: WorkspaceKey) -> None:
    with ProjectedStore(tmp_path / "store.sqlite", key) as store:
        store.save(
            manifest(),
            [
                Batch("pull_requests", [pull()], status="partial", reason="page_limit"),
                Batch("reviews", [], pr_id=7, status="unavailable", reason="permission"),
                Batch("ci_observations", [], pr_id=7, status="not_requested"),
            ],
        )
        assert store.export(manifest().id)["collection_status"] == [
            {"kind": "ci_observations", "pr_id": 7, "status": "not_requested", "reason": None},
            {"kind": "pull_requests", "pr_id": None, "status": "partial", "reason": "page_limit"},
            {"kind": "reviews", "pr_id": 7, "status": "unavailable", "reason": "permission"},
        ]
        with pytest.raises(StoreError, match="not found"):
            store.export(UUID(int=900))


def test_key_mismatch_and_unsafe_permissions(tmp_path: Path, key: WorkspaceKey) -> None:
    path = tmp_path / "store.sqlite"
    with ProjectedStore(path, key):
        pass
    with pytest.raises(StoreError, match="workspace key"):
        ProjectedStore(path, WorkspaceKey.create(tmp_path / "other"))
    (tmp_path / "private" / "actor.key").chmod(0o644)
    with pytest.raises(StoreError, match="private workspace"):
        WorkspaceKey(tmp_path / "private")


def test_interrupted_save_rolls_back(tmp_path: Path, key: WorkspaceKey, monkeypatch: pytest.MonkeyPatch) -> None:
    with ProjectedStore(tmp_path / "store.sqlite", key) as store:
        store.save(manifest(), [Batch("pull_requests", [pull()])])
        before = store.export(manifest().id)
        canonical = store_module._canonical

        def interrupt(value: object) -> str:
            if isinstance(value, dict) and "repository_id" in value:
                raise KeyboardInterrupt
            return canonical(value)

        with monkeypatch.context() as patch:
            patch.setattr(store_module, "_canonical", interrupt)
            with pytest.raises(KeyboardInterrupt):
                store.save(manifest(), [Batch("pull_requests", [pull(8)])])
        assert store.export(manifest().id) == before


def test_open_failure_has_static_error(tmp_path: Path, key: WorkspaceKey) -> None:
    with pytest.raises(StoreError, match="cannot open projected store"):
        ProjectedStore(tmp_path / "missing" / "TOKEN_SECRET", key)


def test_parallel_initialization_and_writes(tmp_path: Path, key: WorkspaceKey) -> None:
    path = tmp_path / "store.sqlite"

    def write(number: int) -> str:
        with ProjectedStore(path, key) as store:
            store.save(manifest(number), [Batch("pull_requests", [pull(number)])])
            return store.content_hash(manifest(number).id)

    with ThreadPoolExecutor(max_workers=4) as pool:
        hashes = list(pool.map(write, range(1, 9)))
    assert len(set(hashes)) == 8
    with ProjectedStore(path, key) as store:
        assert [store.content_hash(manifest(n).id) for n in range(1, 9)] == hashes


@pytest.mark.parametrize("value", [0, -1, True, "42", 2**63])
def test_identifiers_reject_coercion_and_overflow(tmp_path: Path, key: WorkspaceKey, value: object) -> None:
    with (
        ProjectedStore(tmp_path / "store.sqlite", key) as store,
        pytest.raises(StoreError, match="invalid projected observation"),
    ):
        store.save(manifest(), [Batch("pull_requests", [dict(pull(), id=value)])])


@pytest.mark.parametrize(
    "changes",
    [
        {"pr_id": 7},
        {"status": "unavailable"},
        {"status": "not_requested"},
        {"reason": "permission"},
        {"status": "invented"},
        {"reason": "TOKEN_SECRET"},
    ],
)
def test_invalid_batch_metadata(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError) as error:
        Batch("pull_requests", [pull()], **changes)
    assert "TOKEN_SECRET" not in str(error.value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_canonical_json_rejects_nonfinite_numbers(value: float) -> None:
    with pytest.raises(ValueError):
        store_module._canonical({"value": value})


@pytest.mark.parametrize("size", [0, 31, 33, 64])
def test_invalid_key_length(tmp_path: Path, key: WorkspaceKey, size: int) -> None:
    (tmp_path / "private" / "actor.key").write_bytes(b"x" * size)
    with pytest.raises(StoreError, match="^invalid private workspace$"):
        WorkspaceKey(tmp_path / "private")


def test_key_create_never_overwrites_and_rejects_symlinks(tmp_path: Path, key: WorkspaceKey) -> None:
    with pytest.raises(StoreError, match="^cannot create private workspace$"):
        WorkspaceKey.create(tmp_path / "private")
    assert WorkspaceKey(tmp_path / "private").actor(42) == key.actor(42)
    (tmp_path / "linked").symlink_to(tmp_path / "private", target_is_directory=True)
    with pytest.raises(StoreError, match="^invalid private workspace$"):
        WorkspaceKey(tmp_path / "linked")
    (tmp_path / "private" / "actor.key").rename(tmp_path / "private" / "original.key")
    (tmp_path / "private" / "actor.key").symlink_to(tmp_path / "private" / "original.key")
    with pytest.raises(StoreError, match="^invalid private workspace$"):
        WorkspaceKey(tmp_path / "private")


def test_workspace_directory_permissions_and_missing_key(tmp_path: Path, key: WorkspaceKey) -> None:
    (tmp_path / "private").chmod(0o750)
    with pytest.raises(StoreError, match="^invalid private workspace$"):
        WorkspaceKey(tmp_path / "private")
    (tmp_path / "private").chmod(0o700)
    (tmp_path / "private" / "actor.key").unlink()
    with pytest.raises(StoreError, match="^invalid private workspace$"):
        WorkspaceKey(tmp_path / "private")


def test_failed_migration_rolls_back_and_existing_orphans_are_rejected(tmp_path: Path, key: WorkspaceKey) -> None:
    path = tmp_path / "store.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE reviews (unrelated TEXT)")
    with pytest.raises(StoreError, match="^cannot open projected store$"):
        ProjectedStore(path, key)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall() == [("reviews",)]
        db.execute("DROP TABLE reviews")
    with ProjectedStore(path, key) as store:
        store.save(manifest(), [Batch("pull_requests", [pull()])])
    with sqlite3.connect(path) as db:
        saved = json.loads(db.execute("SELECT manifest FROM extractions").fetchone()[0])
        assert saved == manifest().model_dump(mode="json")
        db.execute("INSERT INTO reviews VALUES (?, ?, ?, ?)", (str(manifest().id), 99, 1, "{}"))
    with pytest.raises(StoreError, match="^foreign key violation$"):
        ProjectedStore(path, key)


def test_duplicate_batches_and_empty_orphans_are_not_complete(tmp_path: Path, key: WorkspaceKey) -> None:
    with ProjectedStore(tmp_path / "store.sqlite", key) as store:
        with pytest.raises(StoreError, match="^duplicate collection$"):
            store.save(manifest(), [Batch("pull_requests", []), Batch("pull_requests", [])])
        with pytest.raises(StoreError, match="^cannot save projected extraction$"):
            store.save(manifest(), [Batch("reviews", [], pr_id=7)])
        with pytest.raises(StoreError, match="^extraction not found$"):
            store.export(manifest().id)
