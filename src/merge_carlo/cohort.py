"""Reconcile bounded GitHub collections into one atomic projected extraction."""

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from pydantic import ValidationError

from merge_carlo.attribution import AttributionConfig, resolve_attribution
from merge_carlo.github import Collection, GitHubTransport
from merge_carlo.store import Batch, Kind, Manifest, ProjectedStore, StoreError, project_observation

_EVENTS = {"ready_for_review", "converted_to_draft", "closed", "reopened", "merged", "review_dismissed"}


class SourceError(StoreError):
    """Source metadata is unavailable; no valid extraction can be identified."""


def _batch(kind: Kind, results: list[Collection], observed_at: datetime, pr_id: int | None = None) -> Batch:
    records: dict[int, dict[str, object]] = {}
    incomplete = next((result for result in results if result.status != "complete"), None)
    status = "partial" if incomplete else "complete"
    reason = incomplete.reason if incomplete else None
    for result in results:
        for raw in result.records:
            event = raw.get("event")
            if kind == "lifecycle_events" and isinstance(event, str) and event not in _EVENTS:
                continue
            try:
                row = project_observation(kind, {**raw, "observed_at": observed_at})
            except StoreError:
                status, reason = "partial", "invalid_payload"
                continue
            identifier = cast(int, row["id"])
            previous = records.get(identifier)
            if previous is not None and previous != row:
                # Updated PR snapshots supersede older ones; equal-time conflicts
                # and mutable child conflicts remain explicitly incomplete.
                if kind != "pull_requests" or previous["updated_at"] == row["updated_at"]:
                    status, reason = "partial", "invalid_payload"
                row = max(
                    (previous, row),
                    key=lambda item: (
                        datetime.fromisoformat(str(item["updated_at"])) if kind == "pull_requests" else observed_at,
                        json.dumps(item, sort_keys=True),
                    ),
                )
            records[identifier] = row
    if not records and incomplete and all(result.status == "unavailable" for result in results):
        status = "unavailable"
    return Batch(kind, list(records.values()), pr_id=pr_id, status=status, reason=reason)


def collect_cohort(
    transport: GitHubTransport,
    store: ProjectedStore,
    repository: str,
    analysis_start: datetime,
    analysis_end: datetime,
    *,
    resume: bool = False,
    attribution: AttributionConfig | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Manifest:
    """Always start at page one; no update-time cutoff or stored offset.

    The half-open cohort includes creations in the interval and carry-in work
    whose latest close does not precede it. Snapshot reconciliation is not a
    point-in-time GitHub transaction. Optional CI/features are not requested.
    """
    if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", repository) or repository.split("/")[1] in {".", ".."}:
        raise StoreError("invalid repository")
    base = f"/repos/{repository}"
    metadata = transport.collect(base, single=True)
    if metadata.status != "complete" or len(metadata.records) != 1:
        raise SourceError("repository identity unavailable")
    try:
        manifest = Manifest(
            id=uuid4(),
            repository_id=cast(int, metadata.records[0].get("id")),
            api_version=transport.api_version,
            analysis_start=analysis_start,
            analysis_end=analysis_end,
            retrieved_at=clock(),
        )
    except ValidationError:
        raise StoreError("invalid collection input") from None
    existing = store.manifests()
    if resume:
        if len(existing) != 1:
            raise StoreError("resume requires one existing extraction")
        prior = existing[0]
        if (prior.repository_id, prior.analysis_start, prior.analysis_end, prior.api_version) != (
            manifest.repository_id,
            manifest.analysis_start,
            manifest.analysis_end,
            manifest.api_version,
        ):
            raise StoreError("resume identity mismatch")
        manifest = manifest.model_copy(update={"id": prior.id})
    elif existing:
        raise StoreError("existing extraction requires resume")
    else:
        store.save(manifest, [Batch("pull_requests", [], status="partial", reason="interrupted")])

    attribution = attribution or AttributionConfig()
    results = [
        transport.collect(f"{base}/pulls?state={state}&sort=created&direction=asc&per_page=100")
        for state in ("all", "open")
    ]
    pulls = _batch("pull_requests", results, clock())
    pulls.records[:] = [
        row
        for row in pulls.records
        if datetime.fromisoformat(str(row["created_at"])) < manifest.analysis_end
        and (
            datetime.fromisoformat(str(row["created_at"])) >= manifest.analysis_start
            or row["state"] == "open"
            or row["closed_at"] is None
            or datetime.fromisoformat(str(row["closed_at"])) >= manifest.analysis_start
        )
    ]
    batches = [pulls]
    for row in pulls.records:
        pr_id = cast(int, row["id"])
        lifecycle: Batch | None = None
        children: tuple[tuple[Kind, str], ...] = (
            ("reviews", f"{base}/pulls/{row['number']}/reviews?per_page=100"),
            ("lifecycle_events", f"{base}/issues/{row['number']}/events?per_page=100"),
        )
        for kind, path in children:
            result = transport.collect(path)
            batch = _batch(kind, [result], clock(), pr_id)
            batches.append(batch)
            if kind == "lifecycle_events":
                lifecycle = batch
        assert lifecycle is not None
        feature = resolve_attribution(
            row,
            lifecycle.records,
            attribution,
            lifecycle_complete=lifecycle.status == "complete",
        )
        batches.append(Batch("derived_features", [dict(feature)], pr_id=pr_id))
        batches.append(Batch("ci_observations", [], pr_id=pr_id, status="not_requested"))
    manifest = manifest.model_copy(update={"retrieved_at": clock()})
    store.save(manifest, batches)
    return manifest
