"""Dataset inspection reports from deliberately incomplete synthetic data."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest
from typer.testing import CliRunner

from merge_carlo import inspection as inspection_module
from merge_carlo.cli import app
from merge_carlo.inspection import inspect_dataset
from merge_carlo.store import Batch, Manifest, ProjectedStore, WorkspaceKey

pytestmark = pytest.mark.unit
STAMP = "2026-03-01T00:00:00Z"
FIXTURES = Path(__file__).parent / "fixtures"


def _dataset(tmp_path: Path) -> Path:
    dataset = tmp_path / "dataset.sqlite"
    manifest = Manifest(
        id=UUID(int=21),
        repository_id=91,
        api_version="2022-11-28",
        analysis_start=datetime.fromisoformat("2026-01-01T00:00:00Z"),
        analysis_end=datetime.fromisoformat("2026-02-01T00:00:00Z"),
        retrieved_at=datetime.fromisoformat(STAMP),
    )
    pulls = [
        {
            "id": 1,
            "number": 11,
            "state": "open",
            "created_at": "2026-01-02T00:00:00Z",
            "updated_at": "2026-01-03T00:00:00Z",
            "observed_at": STAMP,
            "user": {"id": 101, "type": "User", "login": "PRIVATE_LOGIN"},
            "body": "PRIVATE_BODY",
            "deletions": 2,
            "changed_files": 1,
        },
        {
            "id": 2,
            "number": 12,
            "state": "closed",
            "created_at": "2026-01-04T00:00:00Z",
            "updated_at": "2026-01-16T00:00:00Z",
            "closed_at": "2026-01-15T00:00:00Z",
            "merged_at": "2026-01-15T00:00:00Z",
            "observed_at": STAMP,
            "draft": False,
            "head": {"sha": "a" * 40},
            "additions": 10,
            "changed_files": 2,
        },
        {
            "id": 3,
            "number": 13,
            "state": "closed",
            "created_at": "2026-01-05T00:00:00Z",
            "updated_at": "2026-01-06T00:00:00Z",
            "closed_at": "2026-01-06T00:00:00Z",
            "observed_at": STAMP,
            "draft": True,
            "user": {"id": 103, "type": "Bot"},
            "additions": 0,
            "deletions": 0,
        },
    ]
    features = [
        {
            "id": 1,
            "readiness_basis": "unknown",
            "readiness_policy": "strict",
            "origin": "unknown",
            "origin_basis": "unmapped",
            "fit_eligible": False,
            "fit_exclusion_reason": "unknown_readiness",
            "basis": "derived",
        },
        {
            "id": 2,
            "ready_at": "2026-01-05T00:00:00Z",
            "readiness_basis": "observed_event",
            "readiness_policy": "strict",
            "origin": "ai",
            "origin_basis": "assumed",
            "fit_eligible": True,
            "basis": "derived",
        },
        {
            "id": 3,
            "ready_at": "2026-01-05T00:00:00Z",
            "readiness_basis": "created_at_proxy",
            "readiness_policy": "created_at_proxy",
            "origin": "human",
            "origin_basis": "observed",
            "fit_eligible": False,
            "fit_exclusion_reason": "reopened",
            "basis": "proxy",
        },
    ]
    batches = [Batch("pull_requests", pulls, status="partial", reason="page_limit")]
    for pr_id in range(1, 4):
        batches.extend(
            [
                Batch(
                    "reviews",
                    [{"id": 20, "state": "COMMENTED", "observed_at": STAMP}] if pr_id == 1 else [],
                    pr_id=pr_id,
                    status=("partial" if pr_id == 1 else "complete" if pr_id == 2 else "unavailable"),
                    reason=("permission" if pr_id == 1 else "unavailable" if pr_id == 3 else None),
                ),
                Batch(
                    "lifecycle_events",
                    [{"id": 30 + pr_id, "event": "ready_for_review", "created_at": f"2026-01-0{pr_id + 2}T00:00:00Z"}]
                    if pr_id < 3
                    else [],
                    pr_id=pr_id,
                    status=("partial" if pr_id == 1 else "complete" if pr_id == 2 else "unavailable"),
                    reason=("page_limit" if pr_id == 1 else "unavailable" if pr_id == 3 else None),
                ),
                Batch("ci_observations", [], pr_id=pr_id, status="not_requested"),
                Batch("derived_features", [features[pr_id - 1]], pr_id=pr_id),
            ]
        )
    with ProjectedStore(dataset, WorkspaceKey.create(tmp_path / "private")) as store:
        store.save(manifest, batches)
    return dataset


def test_inspect_writes_quality_report_without_identifying_text(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "inspection"

    result = runner.invoke(app, ["inspect", "--dataset", str(_dataset(tmp_path)), "--out", str(out)])

    assert result.exit_code == 0, result.output
    report = json.loads((out / "inspection.json").read_text(encoding="utf-8"))
    markdown = (out / "report.md").read_text(encoding="utf-8")
    assert markdown == (FIXTURES / "inspection-report.md").read_text(encoding="utf-8")
    assert report["counts"] == {
        "ci_observations": 0,
        "derived_features": 3,
        "lifecycle_events": 2,
        "pull_requests": 3,
        "reviews": 1,
    }
    assert report["endpoint_coverage"]["reviews"] == {
        "collection_units": 3,
        "statuses": {"complete": 1, "not_requested": 0, "partial": 1, "unavailable": 1},
        "incomplete_reasons": {"permission": 1, "unavailable": 1},
    }
    assert report["origin_attribution"]["unknown_fraction"] == pytest.approx(1 / 3)
    assert report["readiness_basis"]["unknown_fraction"] == pytest.approx(1 / 3)
    assert report["lifecycle_exclusions"] == {
        "eligible": 1,
        "excluded": 2,
        "excluded_fraction": pytest.approx(2 / 3),
        "reasons": {"reopened": 1, "unknown_readiness": 1},
    }
    assert report["censoring"]["open_pull_requests"] == {"count": 1, "fraction": pytest.approx(1 / 3)}
    assert report["missingness"]["pull_requests"]["author"] == {"count": 1, "fraction": pytest.approx(1 / 3)}
    assert "partial" in markdown.lower()
    assert "permission" in markdown
    assert "## Date coverage" in markdown
    assert "PRIVATE_BODY" not in json.dumps(report)
    assert "PRIVATE_LOGIN" not in json.dumps(report)
    assert "PRIVATE_BODY" not in markdown
    assert "PRIVATE_LOGIN" not in markdown


@pytest.mark.parametrize("corruption", ["manifest", "payload", "status"])
def test_inspect_rejects_unvalidated_content_without_publishing(
    runner: CliRunner, tmp_path: Path, corruption: str
) -> None:
    dataset = _dataset(tmp_path)
    with sqlite3.connect(dataset) as db:
        if corruption == "manifest":
            manifest = json.loads(db.execute("SELECT manifest FROM extractions").fetchone()[0])
            manifest["api_version"] = "PRIVATE_EMAIL@example.invalid"
            db.execute("UPDATE extractions SET manifest = ?", (json.dumps(manifest),))
        elif corruption == "status":
            db.execute("UPDATE collection_status SET reason = ? WHERE reason IS NOT NULL", ("PRIVATE_BODY",))
        else:
            rowid, feature_json = db.execute("SELECT rowid, payload FROM derived_features LIMIT 1").fetchone()
            feature = json.loads(feature_json)
            feature["origin"] = "PRIVATE_BODY"
            db.execute("UPDATE derived_features SET payload = ? WHERE rowid = ?", (json.dumps(feature), rowid))

    out = tmp_path / "inspection"
    result = runner.invoke(app, ["inspect", "--dataset", str(dataset), "--out", str(out)])

    assert result.exit_code == 2
    assert result.output == "Cannot inspect: invalid or inaccessible dataset/output.\n"
    assert "PRIVATE" not in result.output
    assert not out.exists()


def test_inspect_reads_one_snapshot_during_replacement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dataset = _dataset(tmp_path)
    with sqlite3.connect(dataset) as db:
        assert db.execute("PRAGMA journal_mode = WAL").fetchone() == ("wal",)
    real_connect = sqlite3.connect
    replaced = False

    class InterleavingConnection:
        def __init__(self) -> None:
            self.connection: sqlite3.Connection = real_connect(dataset.resolve().as_uri() + "?mode=ro", uri=True)

        @property
        def in_transaction(self) -> bool:
            return self.connection.in_transaction

        def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> sqlite3.Cursor:
            nonlocal replaced
            if not replaced and sql.startswith("SELECT id, payload FROM pull_requests"):
                replaced = True
                replacement = {
                    "id": 99,
                    "number": 99,
                    "state": "open",
                    "created_at": "2026-01-20T00:00:00Z",
                    "updated_at": "2026-01-20T00:00:00Z",
                    "closed_at": None,
                    "merged_at": None,
                    "draft": None,
                    "user": None,
                    "head": None,
                    "additions": None,
                    "deletions": None,
                    "changed_files": None,
                }
                with real_connect(dataset) as writer:
                    extraction_id = writer.execute("SELECT id FROM extractions").fetchone()[0]
                    for family in ("reviews", "lifecycle_events", "ci_observations", "derived_features"):
                        writer.execute(f"DELETE FROM {family}")
                    writer.execute("DELETE FROM collection_status")
                    writer.execute("DELETE FROM pull_requests")
                    writer.execute(
                        "INSERT INTO pull_requests VALUES (?, ?, ?)",
                        (extraction_id, 99, json.dumps(replacement)),
                    )
                    writer.execute(
                        "INSERT INTO collection_status VALUES (?, ?, ?, ?, ?)",
                        (extraction_id, "pull_requests", 0, "complete", None),
                    )
            return self.connection.execute(sql, parameters)

        def close(self) -> None:
            self.connection.close()

    monkeypatch.setattr(inspection_module, "_connect", lambda *args, **kwargs: InterleavingConnection())

    report = inspect_dataset(dataset)

    assert replaced
    assert report["counts"] == {
        "ci_observations": 0,
        "derived_features": 3,
        "lifecycle_events": 2,
        "pull_requests": 3,
        "reviews": 1,
    }


@pytest.mark.parametrize(
    ("budget", "limit"),
    [("_MAX_DATASET_BYTES", 1), ("_MAX_RECORDS", 1), ("_MAX_PAYLOAD_BYTES", 1)],
)
def test_inspect_rejects_dataset_over_resource_budget(
    runner: CliRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    budget: str,
    limit: int,
) -> None:
    dataset = _dataset(tmp_path)
    monkeypatch.setattr(inspection_module, budget, limit)

    result = runner.invoke(app, ["inspect", "--dataset", str(dataset), "--out", str(tmp_path / "inspection")])

    assert result.exit_code == 2
    assert not (tmp_path / "inspection").exists()


def test_inspect_rechecks_size_after_opening_snapshot(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = _dataset(tmp_path)
    real_connect = sqlite3.connect
    monkeypatch.setattr(inspection_module, "_MAX_DATASET_BYTES", dataset.stat().st_size + 4096)
    grown = False

    class GrowingConnection:
        def __init__(self) -> None:
            self.connection: sqlite3.Connection = real_connect(dataset.resolve().as_uri() + "?mode=ro", uri=True)

        @property
        def in_transaction(self) -> bool:
            return self.connection.in_transaction

        def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> sqlite3.Cursor:
            nonlocal grown
            if not grown and sql == "BEGIN":
                grown = True
                with real_connect(dataset) as writer:
                    writer.execute("CREATE TABLE padding (value BLOB)")
                    writer.execute("INSERT INTO padding VALUES (zeroblob(1000000))")
            return self.connection.execute(sql, parameters)

        def close(self) -> None:
            self.connection.close()

    monkeypatch.setattr(inspection_module, "_connect", lambda *args, **kwargs: GrowingConnection())

    result = runner.invoke(app, ["inspect", "--dataset", str(dataset), "--out", str(tmp_path / "inspection")])

    assert grown
    assert result.exit_code == 2
    assert not (tmp_path / "inspection").exists()
