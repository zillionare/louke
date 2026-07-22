"""Runtime-owned v0.14 release preview, confirmation and status service."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from louke.runtime.catalog import DefinitionNotFoundError, WorkflowDefinition
from louke.runtime.store import WorkflowRunStore
from louke.v014.fr0300_release_request import preview_release_request


class StalePreviewError(ValueError):
    """Raised when confirmation does not match the persisted preview revision."""


class ReleaseRequestConflictError(ValueError):
    """Raised when a request is replayed with a different idempotency key."""


@dataclass(frozen=True)
class MainCheck:
    """Public main-preflight evidence returned by a Foundation adapter."""

    status: str
    remote_main: dict[str, str]
    previous_branch: dict[str, str]
    remediation: str
    local_main: dict[str, str] | None = None
    checked_at: str = ""


@dataclass(frozen=True)
class FoundationOutcome:
    """Public Foundation reconciliation result and stable resource identities."""

    status: str
    resources: dict[str, Any]
    remediation: str


class FoundationAdapter(Protocol):
    """Port for real Git/GitHub Foundation orchestration."""

    def preflight(self, story: str, release_version: str) -> MainCheck:
        """Refresh and inspect Git/GitHub main state without creating release resources."""

    def provision(
        self,
        story: str,
        release_version: str,
        run_id: str,
        main_check: MainCheck,
    ) -> FoundationOutcome:
        """Query/reconcile Foundation resources and report uncertain effects explicitly."""


class ReleaseRequestStore:
    """SQLite persistence for v0.14 preview and confirmation identities."""

    _ACTIVE_STATUSES = ("preflight", "foundation", "ready", "conflict")

    def __init__(self, run_store: WorkflowRunStore) -> None:
        self._run_store = run_store
        self._conn = run_store._conn
        self._lock = threading.RLock()
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS v14_release_requests (
                request_id TEXT PRIMARY KEY,
                preview_id TEXT NOT NULL UNIQUE,
                workspace_id TEXT NOT NULL,
                request_digest TEXT NOT NULL UNIQUE,
                preview_revision INTEGER NOT NULL,
                story TEXT NOT NULL,
                release_version TEXT NOT NULL,
                status TEXT NOT NULL,
                idempotency_key TEXT,
                actor TEXT,
                main_check TEXT,
                foundation TEXT,
                backlog TEXT,
                project_id TEXT,
                run_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def create_preview(
        self, workspace_id: str, story: str, release_version: str, digest: str
    ) -> dict[str, Any]:
        """Persist or reuse a preview keyed by workspace and request digest."""
        now = _now()
        request_id = f"req_{digest[7:31]}"
        preview_id = f"prev_{digest[7:31]}"
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO v14_release_requests
                (request_id, preview_id, workspace_id, request_digest,
                 preview_revision, story, release_version, status, created_at,
                 updated_at)
                VALUES (?, ?, ?, ?, 0, ?, ?, 'preview', ?, ?)
                """,
                (
                    request_id,
                    preview_id,
                    workspace_id,
                    digest,
                    story,
                    release_version,
                    now,
                    now,
                ),
            )
        return self.get(request_id)

    def claim(
        self,
        request_id: str,
        expected_revision: int,
        request_digest: str,
        idempotency_key: str,
        actor: str,
    ) -> dict[str, Any]:
        """Atomically validate a preview and claim confirmation or backlog it."""
        with self._lock, self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            record = self.get(request_id)
            _assert_preview(record, expected_revision, request_digest)
            if record["status"] != "preview":
                if record.get("idempotency_key") != idempotency_key:
                    raise ReleaseRequestConflictError(
                        "request already confirmed with another idempotency key"
                    )
                return record
            if self._has_active_release(record["request_id"]):
                backlog = {
                    "entry_id": f"bl_{request_digest[7:31]}",
                    "story": record["story"],
                    "release_version": record["release_version"],
                    "reason": "an active main release already exists",
                    "created_at": _now(),
                    "source_identity": {
                        "workspace_id": record["workspace_id"],
                        "request_digest": request_digest,
                    },
                }
                self._update(
                    request_id,
                    status="backlogged",
                    idempotency_key=idempotency_key,
                    actor=actor,
                    backlog=backlog,
                )
                return self.get(request_id)
            self._update(
                request_id,
                status="preflight",
                idempotency_key=idempotency_key,
                actor=actor,
            )
            return self.get(request_id)

    def update(self, request_id: str, **fields: Any) -> dict[str, Any]:
        """Persist a status read-model update and return the current record."""
        with self._lock, self._conn:
            self._update(request_id, **fields)
            return self.get(request_id)

    def get(self, request_id: str) -> dict[str, Any]:
        """Return one persisted request or raise ``KeyError``."""
        row = self._conn.execute(
            "SELECT * FROM v14_release_requests WHERE request_id = ?", (request_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"release request {request_id!r} not found")
        record = dict(row)
        for field in ("main_check", "foundation", "backlog"):
            record[field] = json.loads(record[field]) if record[field] else None
        return record

    def _has_active_release(self, request_id: str) -> bool:
        placeholders = ",".join("?" for _ in self._ACTIVE_STATUSES)
        row = self._conn.execute(
            f"SELECT 1 FROM v14_release_requests WHERE request_id != ? "
            f"AND status IN ({placeholders}) LIMIT 1",
            (request_id, *self._ACTIVE_STATUSES),
        ).fetchone()
        return row is not None

    def _update(self, request_id: str, **fields: Any) -> None:
        allowed = {
            "status",
            "idempotency_key",
            "actor",
            "main_check",
            "foundation",
            "backlog",
            "project_id",
            "run_id",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"unsupported release request fields: {sorted(unknown)}")
        assignments: list[str] = []
        values: list[Any] = []
        for key, value in fields.items():
            assignments.append(f"{key} = ?")
            values.append(
                json.dumps(asdict(value), sort_keys=True)
                if key in {"main_check", "foundation"} and value is not None
                else json.dumps(value, sort_keys=True)
                if key == "backlog" and value is not None
                else value
            )
        assignments.append("updated_at = ?")
        values.append(_now())
        values.append(request_id)
        self._conn.execute(
            f"UPDATE v14_release_requests SET {', '.join(assignments)} WHERE request_id = ?",
            values,
        )


class ReleaseEntryService:
    """Coordinate v0.14 public release APIs through Runtime persistence."""

    def __init__(
        self,
        run_store: WorkflowRunStore,
        foundation: FoundationAdapter,
        *,
        workspace_id: str,
        definition_id: str = "new_feature",
        definition_version: str = "0.14.0",
    ) -> None:
        self._run_store = run_store
        self._foundation = foundation
        self._workspace_id = workspace_id
        self._definition_id = definition_id
        self._definition_version = definition_version
        self._requests = ReleaseRequestStore(run_store)

    def preview(self, story: str, release_version: str) -> dict[str, Any]:
        """Validate and persist a side-effect-free release preview read model."""
        preview = preview_release_request(
            workspace_id=self._workspace_id,
            story=story,
            release_version=release_version,
            active_main_release_present=False,
        )
        record = self._requests.create_preview(
            self._workspace_id,
            preview.story,
            preview.release_version,
            preview.request_digest,
        )
        return {
            "preview_id": record["preview_id"],
            "preview_revision": record["preview_revision"],
            "request_id": record["request_id"],
            "request_digest": record["request_digest"],
            "workspace_id": self._workspace_id,
            "story": record["story"],
            "release": self._release_identity(record["release_version"]),
            "side_effects": [],
        }

    def confirm(
        self,
        preview_id: str,
        *,
        expected_preview_revision: int,
        request_digest: str,
        idempotency_key: str,
        actor: str,
    ) -> dict[str, Any]:
        """Confirm a preview, run real Foundation checks, and persist recovery state."""
        request_id = self._request_id_for_preview(preview_id)
        record = self._requests.claim(
            request_id,
            expected_preview_revision,
            request_digest,
            idempotency_key,
            actor,
        )
        if record["status"] != "preflight":
            return self._read_model(record)
        return self._run_preflight(record)

    def recheck(self, request_id: str, *, actor: str) -> dict[str, Any]:
        """Re-run a blocked or uncertain Foundation request without bypassing checks."""
        record = self._requests.get(request_id)
        if record["status"] not in {"blocked", "conflict"}:
            return self._read_model(record)
        self._requests.update(request_id, status="preflight", actor=actor)
        return self._run_preflight(self._requests.get(request_id))

    def status(self, request_id: str) -> dict[str, Any]:
        """Return the persisted public status read model for a release request."""
        return self._read_model(self._requests.get(request_id))

    def _run_preflight(self, record: dict[str, Any]) -> dict[str, Any]:
        check = self._foundation.preflight(record["story"], record["release_version"])
        self._requests.update(record["request_id"], main_check=check)
        if check.status != "pass":
            return self._read_model(
                self._requests.update(record["request_id"], status="blocked")
            )
        run = self._create_run()
        project_id = (
            f"prj_{hashlib.sha256(record['request_id'].encode()).hexdigest()[:12]}"
        )
        self._requests.update(
            record["request_id"],
            status="foundation",
            project_id=project_id,
            run_id=run.run_id,
        )
        outcome = self._foundation.provision(
            record["story"], record["release_version"], run.run_id, check
        )
        resources = dict(outcome.resources)
        resources.setdefault("local_project", {"id": project_id})
        resources.setdefault("workflow_run", {"id": run.run_id})
        outcome = FoundationOutcome(outcome.status, resources, outcome.remediation)
        status = (
            "ready"
            if outcome.status == "ready"
            else "conflict"
            if outcome.status == "conflict"
            else "blocked"
        )
        return self._read_model(
            self._requests.update(
                record["request_id"],
                status=status,
                foundation=outcome,
                project_id=project_id,
            )
        )

    def _create_run(self):
        definition = self._definition()
        return self._run_store.create_run(definition)

    def _definition(self) -> WorkflowDefinition:
        """Resolve the immutable entry definition from the Runtime catalog."""
        catalog = self._run_store._catalog
        if catalog is None:
            raise DefinitionNotFoundError("Runtime catalog is not configured")
        try:
            return catalog.get(self._definition_id, self._definition_version)
        except DefinitionNotFoundError:
            if self._definition_id != "new_feature":
                raise
            return catalog.get("new_feature", "1")

    def _request_id_for_preview(self, preview_id: str) -> str:
        """Resolve the persisted request id for an opaque preview id."""
        digest = preview_id.removeprefix("prev_")
        return f"req_{digest}"

    def _release_identity(self, version: str) -> dict[str, str]:
        """Return the non-secret release identity displayed by preview."""
        canonical = version.removeprefix("v")
        return {
            "external": version,
            "canonical": canonical,
            "branch": f"releases/{canonical}",
        }

    def _read_model(self, record: dict[str, Any]) -> dict[str, Any]:
        """Convert a persisted request record into IF-API-03 response fields."""
        return {
            "request_id": record["request_id"],
            "status": record["status"],
            "backlog": record["backlog"],
            "main_check": record["main_check"],
            "foundation": record["foundation"],
            "project_id": record["project_id"],
            "run_id": record["run_id"],
            "continue_url": (
                f"/projects/{record['project_id']}/requirements/story"
                if record["project_id"]
                else None
            ),
        }


def _assert_preview(record: dict[str, Any], revision: int, digest: str) -> None:
    """Reject stale preview revisions or mismatched request digests."""
    if record["preview_revision"] != revision or record["request_digest"] != digest:
        raise StalePreviewError(
            "preview revision or request digest is stale; refresh the release preview"
        )


def _now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()
