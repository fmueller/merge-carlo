"""Allowlisted observations, transactional SQLite snapshots, and private identities.

This layer has no transport dependency. Raw dictionaries exist only at the
projection boundary; text-bearing API fields are never handed to SQLite.
"""

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import stat
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Annotated, Literal, Self, cast
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)


class StoreError(ValueError):
    """Static diagnostics, never raw input or underlying database errors."""


class WorkspaceKey:
    """Local secret outside datasets; no reversible actor mapping is retained.

    Create once in an owner-only directory, then reopen it for every dataset in
    that workspace. Losing the key loses stable cross-extraction identities.
    """

    @classmethod
    def create(cls, directory: Path) -> Self:
        try:
            directory.mkdir(mode=0o700)
            fd = os.open(directory / "actor.key", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(secrets.token_bytes(32))
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            raise StoreError("cannot create private workspace") from None
        return cls(directory)

    def __init__(self, directory: Path) -> None:
        try:
            info = directory.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
                raise StoreError("invalid private workspace")
            fd = os.open(directory / "actor.key", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
                    raise StoreError("invalid private workspace")
                key = stream.read(33)
            if len(key) != 32:
                raise StoreError("invalid private workspace")
        except OSError:
            raise StoreError("invalid private workspace") from None
        self._key = key

    def actor(self, actor_id: int) -> str:
        return hmac.new(self._key, f"github-actor:{actor_id}".encode(), hashlib.sha256).hexdigest()


Identifier = Annotated[int, Field(strict=True, gt=0, le=2**63 - 1)]
Count = Annotated[int, Field(strict=True, ge=0, le=2**63 - 1)]
Timestamp = Annotated[AwareDatetime, AfterValidator(lambda value: value.astimezone(UTC))]
Sha = Annotated[str, Field(pattern=r"^[0-9a-f]{40}([0-9a-f]{24})?$")]
Kind = Literal["pull_requests", "reviews", "lifecycle_events", "ci_observations", "derived_features"]
Status = Literal["complete", "partial", "unavailable", "not_requested"]
Reason = Literal[
    "page_limit",
    "request_limit",
    "record_limit",
    "payload_limit",
    "wait_limit",
    "retry_limit",
    "network_error",
    "unsupported_encoding",
    "authentication",
    "permission",
    "not_modified",
    "unavailable",
    "credential_in_response",
    "invalid_payload",
    "pagination_cycle",
    "invalid_validator",
    "unsafe_url",
    "invalid_response",
    "interrupted",
]


class Manifest(BaseModel):
    """Extraction identity and observation time, separate from source timestamps."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    id: UUID
    repository_id: Identifier
    api_version: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    analysis_start: Timestamp
    analysis_end: Timestamp
    retrieved_at: Timestamp

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.analysis_start >= self.analysis_end:
            raise ValueError("invalid analysis interval")
        return self


class Batch(BaseModel):
    """One complete collection result, not one transport page.

    A PR batch has no parent; child batches use the immutable PR identifier.
    Omitted collections remain omitted, never inferred complete.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    kind: Kind
    records: list[dict[str, object]] = Field(repr=False)
    pr_id: Identifier | None = None
    status: Status = "complete"
    reason: Reason | None = None

    def __init__(self, kind: Kind, records: list[dict[str, object]], **kwargs: object) -> None:
        super().__init__(kind=kind, records=records, **kwargs)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (self.kind == "pull_requests") != (self.pr_id is None):
            raise ValueError("invalid collection parent")
        if self.status in ("not_requested", "unavailable") and self.records:
            raise ValueError("unavailable collection has records")
        if self.status in ("complete", "not_requested") and self.reason is not None:
            raise ValueError("invalid collection reason")
        return self


class _Projection(BaseModel):
    model_config = ConfigDict(extra="ignore", hide_input_in_errors=True)


class _Actor(_Projection):
    id: Identifier
    type: Literal["User", "Bot", "Organization", "Mannequin"]


class _Head(_Projection):
    sha: Sha


class _Pull(_Projection):
    observed_at: Timestamp | None = Field(default=None, exclude_if=lambda value: value is None)
    id: Identifier
    number: Identifier
    state: Literal["open", "closed"]
    created_at: Timestamp
    updated_at: Timestamp
    closed_at: Timestamp | None = None
    merged_at: Timestamp | None = None
    draft: Annotated[bool, Field(strict=True)] | None = None
    user: _Actor | None = None
    head: _Head | None = None
    additions: Count | None = None
    deletions: Count | None = None
    changed_files: Count | None = None


class _Review(_Projection):
    observed_at: Timestamp | None = Field(default=None, exclude_if=lambda value: value is None)
    id: Identifier
    state: Literal["APPROVED", "CHANGES_REQUESTED", "COMMENTED", "DISMISSED", "PENDING"]
    submitted_at: Timestamp | None = None
    user: _Actor | None = None
    commit_id: Sha | None = None


class _Event(_Projection):
    id: Identifier
    event: Literal["ready_for_review", "converted_to_draft", "closed", "reopened", "merged", "review_dismissed"]
    created_at: Timestamp
    actor: _Actor | None = None
    commit_id: Sha | None = None


class _CI(_Projection):
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
    started_at: Timestamp | None = None
    completed_at: Timestamp | None = None
    head_sha: Sha | None = None


class _Feature(_Projection):
    id: Identifier
    ready_at: Timestamp | None = None
    readiness_basis: Literal["observed_event", "supported_reconstruction", "created_at_proxy", "unknown"]
    origin: Literal["human", "ai", "non_ai_automation", "unknown"]
    basis: Literal["observed", "derived", "proxy", "assumed", "synthetic"]


_MODELS: dict[str, type[_Projection]] = {
    "pull_requests": _Pull,
    "reviews": _Review,
    "lifecycle_events": _Event,
    "ci_observations": _CI,
    "derived_features": _Feature,
}


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def project_observation(kind: Kind, raw: dict[str, object]) -> dict[str, object]:
    """Validate and allowlist a transient record; actor pseudonymization is at save."""
    try:
        return _MODELS[kind].model_validate(raw).model_dump(mode="json")
    except ValidationError:
        raise StoreError("invalid projected observation") from None


# Only these source-owned identifiers are interpolated in SQL; every value is bound.
_MIGRATION_1 = (
    "CREATE TABLE workspace (fingerprint TEXT NOT NULL)",
    "CREATE TABLE extractions (id TEXT PRIMARY KEY, manifest TEXT NOT NULL)",
    "CREATE TABLE pull_requests (extraction_id TEXT NOT NULL REFERENCES extractions(id) ON DELETE CASCADE, "
    "id INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY (extraction_id, id))",
    *(
        f"CREATE TABLE {name} (extraction_id TEXT NOT NULL, pr_id INTEGER NOT NULL, "
        "id INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY (extraction_id, pr_id, id), "
        "FOREIGN KEY (extraction_id, pr_id) REFERENCES pull_requests(extraction_id, id) ON DELETE CASCADE)"
        for name in ("reviews", "lifecycle_events", "ci_observations", "derived_features")
    ),
    "CREATE TABLE collection_status (extraction_id TEXT NOT NULL REFERENCES extractions(id) ON DELETE CASCADE, "
    "kind TEXT NOT NULL, pr_id INTEGER NOT NULL, status TEXT NOT NULL, reason TEXT, "
    "PRIMARY KEY (extraction_id, kind, pr_id))",
)


class ProjectedStore:
    """One connection per thread; SQLite serializes writes across connections.

    save() atomically replaces an extraction, including statuses and children.
    Readers export a single snapshot. Conflicting duplicates fail closed; cohort
    reconciliation belongs to the collector, not insertion order.
    """

    def __init__(self, path: Path, key: WorkspaceKey, *, existing_only: bool = False) -> None:
        self._key = key
        try:
            self._db = sqlite3.connect(
                path.resolve().as_uri() + "?mode=rw" if existing_only else path,
                uri=existing_only,
                isolation_level=None,
            )
        except sqlite3.Error:
            raise StoreError("cannot open projected store") from None
        try:
            self._db.execute("PRAGMA foreign_keys = ON")
            self._db.execute("BEGIN IMMEDIATE")
            self._db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)")
            versions = self._db.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
            if existing_only and not versions:
                raise StoreError("existing projected store required")
            if versions not in ([], [(1,)]):
                raise StoreError("unsupported schema")
            if not versions:
                for statement in _MIGRATION_1:
                    self._db.execute(statement)
                self._db.execute("INSERT INTO workspace VALUES (?)", (key.actor(0),))
                self._db.execute("INSERT INTO schema_migrations VALUES (?)", (1,))
            if self._db.execute("SELECT fingerprint FROM workspace").fetchall() != [(key.actor(0),)]:
                raise StoreError("workspace key mismatch")
            if self._db.execute("PRAGMA foreign_key_check").fetchall():
                raise StoreError("foreign key violation")
            self._db.execute("COMMIT")
        except BaseException as error:
            self._db.close()
            if isinstance(error, sqlite3.Error):
                raise StoreError("cannot open projected store") from None
            raise

    @property
    def schema_version(self) -> int:
        return 1

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self._db.close()

    def save(self, manifest: Manifest, batches: list[Batch]) -> None:
        """Project before beginning a write; rollback the entire replacement on error."""
        projected: dict[tuple[str, int, int], str] = {}
        statuses: dict[tuple[str, int], tuple[str, str | None]] = {}
        try:
            for batch in batches:
                parent = batch.pr_id or 0
                status_key = (batch.kind, parent)
                if status_key in statuses:
                    raise StoreError("duplicate collection")
                statuses[status_key] = (batch.status, batch.reason)
                for raw in batch.records:
                    data = project_observation(batch.kind, raw)
                    for actor_field in ("user", "actor"):
                        actor = data.get(actor_field)
                        if actor is not None:
                            assert isinstance(actor, dict)
                            actor["id"] = self._key.actor(actor["id"])
                    record_key = (batch.kind, parent, cast(int, data["id"]))
                    payload = _canonical(data)
                    if record_key in projected and projected[record_key] != payload:
                        raise StoreError("conflicting duplicate observation")
                    projected[record_key] = payload
        except StoreError:
            raise
        except (ValidationError, KeyError, TypeError, ValueError):
            raise StoreError("invalid projected observation") from None
        extraction_id = str(manifest.id)
        try:
            self._db.execute("BEGIN IMMEDIATE")
            self._db.execute("DELETE FROM extractions WHERE id = ?", (extraction_id,))
            self._db.execute(
                "INSERT INTO extractions VALUES (?, ?)",
                (extraction_id, _canonical(manifest.model_dump(mode="json"))),
            )
            # Parent rows always precede children, regardless of completion order.
            for name in _MODELS:
                for (kind, parent, identifier), payload in sorted(projected.items()):
                    if name != kind:
                        continue
                    if kind == "pull_requests":
                        self._db.execute(
                            "INSERT INTO pull_requests VALUES (?, ?, ?)", (extraction_id, identifier, payload)
                        )
                    else:
                        self._db.execute(
                            f"INSERT INTO {name} VALUES (?, ?, ?, ?)", (extraction_id, parent, identifier, payload)
                        )
            for (kind, parent), (status, reason) in sorted(statuses.items()):
                if (
                    parent
                    and not self._db.execute(
                        "SELECT 1 FROM pull_requests WHERE extraction_id = ? AND id = ?", (extraction_id, parent)
                    ).fetchone()
                ):
                    raise StoreError("missing collection parent")
                self._db.execute(
                    "INSERT INTO collection_status VALUES (?, ?, ?, ?, ?)",
                    (extraction_id, kind, parent, status, reason),
                )
            self._db.execute("COMMIT")
        except (sqlite3.Error, StoreError):
            raise StoreError("cannot save projected extraction") from None
        finally:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")

    def export(self, extraction_id: UUID) -> dict[str, object]:
        """Versioned semantic content: no extraction UUID, retrieval time or secret.

        Source timestamps, analysis bounds, API version, statuses, and repository
        identity are semantic. Retrieval provenance remains in the local manifest.
        """
        try:
            self._db.execute("BEGIN")
            row = self._db.execute("SELECT manifest FROM extractions WHERE id = ?", (str(extraction_id),)).fetchone()
            if row is None:
                raise StoreError("extraction not found")
            metadata = json.loads(row[0])
            del metadata["id"], metadata["retrieved_at"]
            result: dict[str, object] = {"schema_version": self.schema_version, "manifest": metadata}
            for name in _MODELS:
                columns = "payload" if name == "pull_requests" else "pr_id, payload"
                rows = self._db.execute(
                    f"SELECT {columns} FROM {name} WHERE extraction_id = ?", (str(extraction_id),)
                ).fetchall()
                result[name] = sorted(
                    [
                        json.loads(row[0]) if name == "pull_requests" else {"pr_id": row[0], **json.loads(row[1])}
                        for row in rows
                    ],
                    key=_canonical,
                )
            result["collection_status"] = [
                {"kind": kind, "pr_id": parent or None, "status": status, "reason": reason}
                for kind, parent, status, reason in self._db.execute(
                    "SELECT kind, pr_id, status, reason FROM collection_status "
                    "WHERE extraction_id = ? ORDER BY kind, pr_id",
                    (str(extraction_id),),
                )
            ]
            self._db.execute("COMMIT")
            return result
        except sqlite3.Error:
            raise StoreError("cannot export projected extraction") from None
        finally:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")

    def content_hash(self, extraction_id: UUID) -> str:
        return hashlib.sha256(_canonical(self.export(extraction_id)).encode()).hexdigest()

    def manifests(self) -> list[Manifest]:
        """Read extraction identities for resume without a persisted page cursor."""
        try:
            return [
                Manifest.model_validate_json(row[0]) for row in self._db.execute("SELECT manifest FROM extractions")
            ]
        except (sqlite3.Error, ValidationError):
            raise StoreError("cannot read extraction manifest") from None

    def historical(self, extraction_id: UUID, cutoff: datetime) -> dict[str, list[dict[str, object]]]:
        """Conservative inputs, not reconstructed features or a complete history.

        PR and mutable review snapshots require observation by the cutoff;
        lifecycle events use source time. Undated snapshots are not evidence.
        CI and derived features have no historical reader contract yet.
        """
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise StoreError("cutoff must be timezone aware")
        data = self.export(extraction_id)
        result: dict[str, list[dict[str, object]]] = {}
        for kind in ("pull_requests", "reviews", "lifecycle_events"):
            rows = data[kind]
            assert isinstance(rows, list)
            field = "created_at" if kind == "lifecycle_events" else "observed_at"
            result[kind] = [
                row for row in rows if row.get(field) is not None and datetime.fromisoformat(row[field]) <= cutoff
            ]
        return result
