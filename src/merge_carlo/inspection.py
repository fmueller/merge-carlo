"""Read-only aggregate quality reporting for projected cohort datasets."""

import json
import shutil
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path
from typing import Annotated, Literal, Self, cast

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator

from merge_carlo.store import Count, Identifier, Kind, Manifest, Reason, Sha, Status


class InspectionError(ValueError):
    """Static dataset or output diagnostic that never includes stored content."""


_FAMILIES = ("pull_requests", "reviews", "lifecycle_events", "ci_observations", "derived_features")
_STATUSES = ("complete", "partial", "unavailable", "not_requested")
_MAX_DATASET_BYTES = 1_000_000_000
_MAX_RECORDS = 1_000_000
_MAX_PAYLOAD_BYTES = 8_000_000
_connect = sqlite3.connect
_DATES: dict[str, tuple[str, ...]] = {
    "pull_requests": ("created_at", "updated_at", "closed_at", "merged_at", "observed_at"),
    "reviews": ("submitted_at", "observed_at"),
    "lifecycle_events": ("created_at",),
    "ci_observations": ("started_at", "completed_at"),
    "derived_features": ("ready_at",),
}
_MISSING: dict[str, dict[str, tuple[str, ...]]] = {
    "pull_requests": {
        "author": ("user",),
        "draft_status": ("draft",),
        "merge_time": ("merged_at",),
        "size": ("additions", "deletions", "changed_files"),
    },
    "reviews": {"author": ("user",), "submission_time": ("submitted_at",), "revision": ("commit_id",)},
    "lifecycle_events": {"actor": ("actor",), "revision": ("commit_id",)},
    "ci_observations": {
        "start_time": ("started_at",),
        "completion_time": ("completed_at",),
        "revision": ("head_sha",),
    },
    "derived_features": {"ready_time": ("ready_at",)},
}


class _StoredModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class _StoredActor(_StoredModel):
    id: str = Field(pattern=r"^[0-9a-f]{64}$")
    type: Literal["User", "Bot", "Organization", "Mannequin"]


class _StoredHead(_StoredModel):
    sha: Sha


class _StoredPull(_StoredModel):
    observed_at: AwareDatetime | None = None
    id: Identifier
    number: Identifier
    state: Literal["open", "closed"]
    created_at: AwareDatetime
    updated_at: AwareDatetime
    closed_at: AwareDatetime | None = None
    merged_at: AwareDatetime | None = None
    draft: Annotated[bool, Field(strict=True)] | None = None
    user: _StoredActor | None = None
    head: _StoredHead | None = None
    additions: Count | None = None
    deletions: Count | None = None
    changed_files: Count | None = None


class _StoredReview(_StoredModel):
    observed_at: AwareDatetime | None = None
    id: Identifier
    state: Literal["APPROVED", "CHANGES_REQUESTED", "COMMENTED", "DISMISSED", "PENDING"]
    submitted_at: AwareDatetime | None = None
    user: _StoredActor | None = None
    commit_id: Sha | None = None


class _StoredEvent(_StoredModel):
    id: Identifier
    event: Literal["ready_for_review", "converted_to_draft", "closed", "reopened", "merged", "review_dismissed"]
    created_at: AwareDatetime
    actor: _StoredActor | None = None
    commit_id: Sha | None = None


class _StoredCI(_StoredModel):
    id: Identifier
    status: Literal["queued", "in_progress", "completed", "waiting", "requested", "pending"]
    conclusion: (
        Literal[
            "success",
            "failure",
            "neutral",
            "cancelled",
            "skipped",
            "timed_out",
            "action_required",
            "stale",
            "startup_failure",
        ]
        | None
    ) = None
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    head_sha: Sha | None = None


class _StoredFeature(_StoredModel):
    id: Identifier
    ready_at: AwareDatetime | None = None
    readiness_basis: Literal["observed_event", "supported_reconstruction", "created_at_proxy", "unknown"]
    readiness_policy: Literal["strict", "created_at_proxy"]
    origin: Literal["human", "ai", "non_ai_automation", "unknown"]
    origin_basis: Literal[
        "observed",
        "derived",
        "proxy",
        "assumed",
        "synthetic",
        "unmapped",
        "missing_author",
        "conflicting_mapping",
    ]
    fit_eligible: Annotated[bool, Field(strict=True)]
    fit_exclusion_reason: (
        Literal["reopened", "repeated_readiness_cycle", "incomplete_lifecycle", "unknown_readiness"] | None
    ) = None
    basis: Literal["observed", "derived", "proxy", "assumed", "synthetic"]


class _StoredStatus(_StoredModel):
    kind: Kind
    pr_id: Identifier | None
    status: Status
    reason: Reason | None

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (self.kind == "pull_requests") != (self.pr_id is None):
            raise ValueError("invalid collection parent")
        if self.status in ("complete", "not_requested") and self.reason is not None:
            raise ValueError("invalid collection reason")
        return self


_STORED_MODELS: dict[str, type[_StoredModel]] = {
    "pull_requests": _StoredPull,
    "reviews": _StoredReview,
    "lifecycle_events": _StoredEvent,
    "ci_observations": _StoredCI,
    "derived_features": _StoredFeature,
}


def _fraction(count: int, total: int) -> float | None:
    return count / total if total else None


def _read_dataset(path: Path) -> dict[str, object]:
    """Read one extraction without requiring the private pseudonymization key."""
    try:
        total_bytes = sum(
            candidate.stat().st_size
            for candidate in (path, path.with_name(path.name + "-wal"), path.with_name(path.name + "-shm"))
            if candidate.is_file()
        )
        if total_bytes > _MAX_DATASET_BYTES:
            raise InspectionError("dataset exceeds inspection budget")
        db = _connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            db.execute("BEGIN")
            if db.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall() != [(1,)]:
                raise InspectionError("unsupported dataset schema")
            page_count = cast(int, db.execute("PRAGMA page_count").fetchone()[0])
            page_size = cast(int, db.execute("PRAGMA page_size").fetchone()[0])
            if page_count * page_size > _MAX_DATASET_BYTES:
                raise InspectionError("dataset exceeds inspection budget")
            if db.execute("PRAGMA foreign_key_check").fetchall():
                raise InspectionError("invalid dataset")
            extractions = db.execute("SELECT id, manifest FROM extractions").fetchall()
            if len(extractions) != 1:
                raise InspectionError("dataset must contain one extraction")
            extraction_id, manifest_json = extractions[0]
            manifest = Manifest.model_validate_json(manifest_json).model_dump(mode="json")
            if str(manifest["id"]) != extraction_id:
                raise InspectionError("invalid dataset")
            result: dict[str, object] = {"manifest": manifest}
            record_count = 0
            for family in _FAMILIES:
                count, largest = db.execute(
                    f"SELECT COUNT(*), COALESCE(MAX(LENGTH(payload)), 0) FROM {family} WHERE extraction_id = ?",
                    (extraction_id,),
                ).fetchone()
                record_count += cast(int, count)
                if record_count > _MAX_RECORDS or cast(int, largest) > _MAX_PAYLOAD_BYTES:
                    raise InspectionError("dataset exceeds inspection budget")
                columns = "id, payload" if family == "pull_requests" else "pr_id, id, payload"
                records = db.execute(
                    f"SELECT {columns} FROM {family} WHERE extraction_id = ?", (extraction_id,)
                ).fetchall()
                validated = []
                for row in records:
                    payload = _STORED_MODELS[family].model_validate_json(row[-1]).model_dump(mode="json")
                    if payload["id"] != row[-2]:
                        raise InspectionError("invalid dataset")
                    validated.append({**({} if family == "pull_requests" else {"pr_id": row[0]}), **payload})
                result[family] = validated
            status_count = cast(
                int,
                db.execute(
                    "SELECT COUNT(*) FROM collection_status WHERE extraction_id = ?", (extraction_id,)
                ).fetchone()[0],
            )
            if record_count + status_count > _MAX_RECORDS:
                raise InspectionError("dataset exceeds inspection budget")
            status_rows = db.execute(
                "SELECT kind, pr_id, status, reason FROM collection_status WHERE extraction_id = ?", (extraction_id,)
            ).fetchall()
            result["collection_status"] = [
                _StoredStatus.model_validate(
                    {"kind": kind, "pr_id": parent or None, "status": status, "reason": reason}
                ).model_dump(mode="json")
                for kind, parent, status, reason in status_rows
            ]
            db.execute("COMMIT")
            return result
        finally:
            if db.in_transaction:
                db.execute("ROLLBACK")
            db.close()
    except InspectionError:
        raise
    except (json.JSONDecodeError, OSError, sqlite3.Error, TypeError, ValidationError):
        raise InspectionError("cannot read projected dataset") from None


def _records(data: dict[str, object], family: str) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], data[family])


def _distribution(rows: list[dict[str, object]], field: str) -> dict[str, object]:
    counts = Counter(cast(str, row.get(field, "unknown")) for row in rows)
    total = len(rows)
    return {
        "total": total,
        "counts": dict(sorted(counts.items())),
        "fractions": {name: count / total for name, count in sorted(counts.items())} if total else {},
        "unknown_fraction": _fraction(counts["unknown"], total),
    }


def inspect_dataset(path: Path) -> dict[str, object]:
    """Build a deterministic, de-identified summary from one projected extraction."""
    data = _read_dataset(path)
    manifest = cast(dict[str, object], data["manifest"])
    pulls = _records(data, "pull_requests")
    features = _records(data, "derived_features")
    statuses = _records(data, "collection_status")

    endpoint_coverage: dict[str, object] = {}
    for family in _FAMILIES:
        family_rows = [row for row in statuses if row["kind"] == family]
        status_counts = Counter(cast(str, row["status"]) for row in family_rows)
        reason_counts = Counter(cast(str, row["reason"]) for row in family_rows if row["reason"] is not None)
        endpoint_coverage[family] = {
            "collection_units": len(family_rows),
            "statuses": {status: status_counts[status] for status in _STATUSES},
            "incomplete_reasons": dict(sorted(reason_counts.items())),
        }

    date_coverage: dict[str, object] = {}
    missingness: dict[str, object] = {}
    for family in _FAMILIES:
        rows = _records(data, family)
        family_dates: dict[str, object] = {}
        for field in _DATES[family]:
            values = sorted(cast(str, row[field]) for row in rows if row.get(field) is not None)
            family_dates[field] = {
                "observed": len(values),
                "earliest": values[0] if values else None,
                "latest": values[-1] if values else None,
            }
        date_coverage[family] = family_dates
        family_missingness: dict[str, object] = {}
        for label, fields in _MISSING[family].items():
            count = sum(any(row.get(field) is None for field in fields) for row in rows)
            family_missingness[label] = {"count": count, "fraction": _fraction(count, len(rows))}
        missingness[family] = family_missingness

    open_count = sum(row["state"] == "open" for row in pulls)
    unmerged_count = sum(row.get("merged_at") is None for row in pulls)
    exclusions = Counter(
        cast(str, row["fit_exclusion_reason"])
        for row in features
        if not row["fit_eligible"] and row.get("fit_exclusion_reason") is not None
    )
    eligible = sum(bool(row["fit_eligible"]) for row in features)
    excluded = len(features) - eligible
    incomplete = any(row["status"] in {"partial", "unavailable"} for row in statuses)
    limitations = [
        "Snapshot reconciliation is not a point-in-time GitHub transaction.",
        "GitHub activity Events are not used as an archive; only allowlisted issue lifecycle events are retained.",
        "Unknown readiness is excluded from ready-based calibration rather than replaced with zero draft time.",
    ]
    if incomplete:
        limitations.append(
            "Partial and unavailable endpoint collections are incomplete evidence and must not be interpreted as "
            "empty, complete history."
        )
    if any(row["status"] == "not_requested" for row in statuses):
        limitations.append("Not-requested endpoint collections provide no evidence for that collection family.")

    return {
        "schema_version": 1,
        "dataset": {
            name: manifest[name]
            for name in ("repository_id", "api_version", "analysis_start", "analysis_end", "retrieved_at")
        },
        "counts": {family: len(_records(data, family)) for family in _FAMILIES},
        "date_coverage": date_coverage,
        "missingness": missingness,
        "censoring": {
            "open_pull_requests": {"count": open_count, "fraction": _fraction(open_count, len(pulls))},
            "unmerged_pull_requests": {"count": unmerged_count, "fraction": _fraction(unmerged_count, len(pulls))},
        },
        "endpoint_coverage": endpoint_coverage,
        "readiness_basis": _distribution(features, "readiness_basis"),
        "origin_attribution": _distribution(features, "origin"),
        "lifecycle_exclusions": {
            "eligible": eligible,
            "excluded": excluded,
            "excluded_fraction": _fraction(excluded, len(features)),
            "reasons": dict(sorted(exclusions.items())),
        },
        "limitations": limitations,
    }


def _percent(value: object) -> str:
    return "n/a" if value is None else f"{cast(float, value):.1%}"


def render_inspection(report: dict[str, object]) -> str:
    """Render the machine report without carrying source records into prose."""
    dataset = cast(dict[str, object], report["dataset"])
    lines = [
        "# Dataset inspection",
        "",
        "## Dataset coverage",
        "",
        f"- Analysis interval: `{dataset['analysis_start']}` (inclusive) to `{dataset['analysis_end']}` (exclusive)",
        f"- Retrieved at: `{dataset['retrieved_at']}`",
        f"- API version: `{dataset['api_version']}`",
        "",
        "## Counts",
        "",
        "| Collection family | Records |",
        "|---|---:|",
    ]
    counts = cast(dict[str, int], report["counts"])
    lines.extend(f"| `{family}` | {counts[family]} |" for family in _FAMILIES)
    lines.extend(
        [
            "",
            "## Endpoint coverage",
            "",
            "| Collection family | Complete | Partial | Unavailable | Not requested | Incomplete reasons |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    coverage = cast(dict[str, dict[str, object]], report["endpoint_coverage"])
    for family in _FAMILIES:
        statuses = cast(dict[str, int], coverage[family]["statuses"])
        reasons = cast(dict[str, int], coverage[family]["incomplete_reasons"])
        reason_text = ", ".join(f"{name}: {count}" for name, count in reasons.items()) or "none"
        lines.append(
            f"| `{family}` | {statuses['complete']} | {statuses['partial']} | {statuses['unavailable']} | "
            f"{statuses['not_requested']} | {reason_text} |"
        )
    lines.extend(
        [
            "",
            "## Date coverage",
            "",
            "| Collection family | Timestamp | Observed | Earliest | Latest |",
            "|---|---|---:|---|---|",
        ]
    )
    date_coverage = cast(dict[str, dict[str, dict[str, object]]], report["date_coverage"])
    for family in _FAMILIES:
        lines.extend(
            f"| `{family}` | `{field}` | {value['observed']} | {value['earliest'] or 'n/a'} | "
            f"{value['latest'] or 'n/a'} |"
            for field, value in date_coverage[family].items()
        )
    lines.extend(["", "## Attribution and readiness", ""])
    for label, key in (("Work origin", "origin_attribution"), ("Readiness basis", "readiness_basis")):
        distribution = cast(dict[str, object], report[key])
        values = cast(dict[str, int], distribution["counts"])
        fractions = cast(dict[str, float], distribution["fractions"])
        lines.append(
            f"- **{label}:** "
            + ", ".join(f"{name} {count} ({_percent(fractions[name])})" for name, count in values.items())
        )
        lines.append(f"- **{label} unknown fraction:** {_percent(distribution['unknown_fraction'])}")
    exclusions = cast(dict[str, object], report["lifecycle_exclusions"])
    reasons = cast(dict[str, int], exclusions["reasons"])
    censoring = cast(dict[str, dict[str, object]], report["censoring"])
    open_pulls = censoring["open_pull_requests"]
    unmerged_pulls = censoring["unmerged_pull_requests"]
    lines.extend(
        [
            "",
            "## Censoring and exclusions",
            "",
            f"- Open pull requests: {open_pulls['count']} ({_percent(open_pulls['fraction'])})",
            f"- Unmerged pull requests: {unmerged_pulls['count']} ({_percent(unmerged_pulls['fraction'])})",
            (
                f"- Excluded from lifecycle fitting: {exclusions['excluded']} "
                f"({_percent(exclusions['excluded_fraction'])})"
            ),
            "- Exclusion reasons: " + (", ".join(f"{name}: {count}" for name, count in reasons.items()) or "none"),
            "",
            "## Missingness",
            "",
            "| Collection family | Field | Missing | Fraction |",
            "|---|---|---:|---:|",
        ]
    )
    missingness = cast(dict[str, dict[str, dict[str, object]]], report["missingness"])
    for family in _FAMILIES:
        lines.extend(
            f"| `{family}` | {field} | {value['count']} | {_percent(value['fraction'])} |"
            for field, value in missingness[family].items()
        )
    lines.extend(["", "## Extraction limitations", ""])
    lines.extend(f"- {item}" for item in cast(list[str], report["limitations"]))
    return "\n".join(lines) + "\n"


def write_inspection(dataset: Path, out: Path) -> None:
    """Stage both report forms and publish them together into an empty destination."""
    if out.is_symlink() or (out.exists() and (not out.is_dir() or any(out.iterdir()))):
        raise InspectionError("output must be an empty directory or absent")
    report = inspect_dataset(dataset)
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{out.name}-", dir=out.parent))
    try:
        (stage / "inspection.json").write_text(
            json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8"
        )
        (stage / "report.md").write_text(render_inspection(report), encoding="utf-8")
        if out.exists():
            out.rmdir()
        stage.rename(out)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
