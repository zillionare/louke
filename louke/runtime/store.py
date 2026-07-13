"""WorkflowRun state store.

Persists WorkflowRun identity, the pinned definition version, current step,
status and monotonic revision.  The store validates the definition through the
catalog before a run is created and never mutates a definition after creation.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from louke.runtime.catalog import (
    DefinitionInvalidError,
    DefinitionRegistry,
    WorkflowDefinition,
    derive_status,
    validate_definition,
)
from louke.runtime.domain import (
    RevisionConflictError,
    WorkflowEvent,
)


class RunNotFoundError(ValueError):
    """Raised when a requested run id does not exist in the store."""


@dataclass(frozen=True, slots=True)
class WorkflowRun:
    """A persisted workflow run record.

    Attributes:
        run_id: Opaque stable identifier for the run.
        definition_id: The definition id the run was created from.
        definition_version: The immutable definition version the run is bound to.
        current_step: The step the run is currently positioned at.
        revision: Monotonic revision starting at 0 for the initial record.
        status: Run lifecycle status (e.g. ``waiting_for_human``).
        contract_digest: Deterministic digest of the bound definition.
        created_at: ISO 8601 UTC timestamp of run creation.
        updated_at: ISO 8601 UTC timestamp of the last update.
    """

    run_id: str
    definition_id: str
    definition_version: str
    current_step: str
    revision: int
    status: str
    contract_digest: str
    created_at: str
    updated_at: str


_RUN_COLUMNS: tuple[str, ...] = (
    "run_id",
    "definition_id",
    "definition_version",
    "current_step",
    "revision",
    "status",
    "contract_digest",
    "created_at",
    "updated_at",
)


def _run_to_tuple(
    run: WorkflowRun,
) -> tuple[str, str, str, str, int, str, str, str, str]:
    """Return a tuple matching ``_RUN_COLUMNS`` for the given ``run``."""
    return (
        run.run_id,
        run.definition_id,
        run.definition_version,
        run.current_step,
        run.revision,
        run.status,
        run.contract_digest,
        run.created_at,
        run.updated_at,
    )


def _row_to_run(row: sqlite3.Row) -> WorkflowRun:
    """Reconstruct a ``WorkflowRun`` from a SQLite row."""
    return WorkflowRun(
        run_id=row["run_id"],
        definition_id=row["definition_id"],
        definition_version=row["definition_version"],
        current_step=row["current_step"],
        revision=row["revision"],
        status=row["status"],
        contract_digest=row["contract_digest"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_event(row: sqlite3.Row) -> WorkflowEvent:
    """Reconstruct a ``WorkflowEvent`` from a SQLite row."""
    return WorkflowEvent(
        event_id=row["event_id"],
        run_id=row["run_id"],
        sequence=row["sequence"],
        type=row["type"],
        at=row["at"],
        actor=json.loads(row["actor"]),
        from_step=row["from_step"],
        to_step=row["to_step"],
        revision=row["revision"],
        details=json.loads(row["details"]),
    )


def _definition_digest(definition: WorkflowDefinition) -> str:
    """Return a deterministic digest of ``definition``.

    The digest covers the definition id, version, start step and the full
    step/transition graph so that equal definitions always produce the same
    digest and any structural change produces a different digest.
    """
    payload = {
        "definition_id": definition.definition_id,
        "version": definition.version,
        "start_step": definition.start_step,
        "steps": [
            {
                "step_id": step.step_id,
                "kind": step.kind,
                "required": step.required,
                "transitions": [
                    {
                        "edge_id": edge.edge_id,
                        "from_step": edge.from_step,
                        "to_step": edge.to_step,
                        "condition": edge.condition,
                    }
                    for edge in step.transitions
                ],
            }
            for step in definition.steps
        ],
    }
    content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


class WorkflowRunStore:
    """SQLite-backed store for WorkflowRun records.

    Args:
        db_path: Path to the SQLite database.  Defaults to an in-memory
            database so unit tests are isolated by default.
        catalog: Optional registry used to validate and pin definitions by
            id/version.  When provided, runs are bound to the registered
            definition rather than the caller-supplied object.
    """

    def __init__(
        self,
        db_path: str | None = None,
        catalog: DefinitionRegistry | None = None,
    ) -> None:
        self._db_path = db_path or ":memory:"
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._catalog = catalog
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_runs (
                run_id TEXT PRIMARY KEY,
                definition_id TEXT NOT NULL,
                definition_version TEXT NOT NULL,
                current_step TEXT NOT NULL,
                revision INTEGER NOT NULL,
                status TEXT NOT NULL,
                contract_digest TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_events (
                event_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                type TEXT NOT NULL,
                at TEXT NOT NULL,
                actor TEXT NOT NULL,
                from_step TEXT,
                to_step TEXT,
                revision INTEGER NOT NULL,
                details TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def create_run(self, definition: WorkflowDefinition) -> WorkflowRun:
        """Create and persist a WorkflowRun bound to ``definition``.

        Args:
            definition: The valid workflow definition to bind the run to.

        Returns:
            The newly created ``WorkflowRun`` with ``revision`` set to 0.

        Raises:
            DefinitionInvalidError: If the definition fails catalog validation.
        """
        validation_errors = validate_definition(definition)
        if validation_errors:
            raise DefinitionInvalidError(validation_errors)

        if self._catalog is not None:
            definition = self._catalog.get(definition.definition_id, definition.version)

        now = datetime.now(timezone.utc).isoformat()
        run = WorkflowRun(
            run_id=f"run_{uuid.uuid4().hex[:12]}",
            definition_id=definition.definition_id,
            definition_version=definition.version,
            current_step=definition.start_step,
            revision=0,
            status=derive_status(definition.start_step, definition),
            contract_digest=_definition_digest(definition),
            created_at=now,
            updated_at=now,
        )
        column_list = ", ".join(_RUN_COLUMNS)
        placeholders = ", ".join("?" for _ in _RUN_COLUMNS)
        self._conn.execute(
            f"INSERT INTO workflow_runs ({column_list}) VALUES ({placeholders})",
            _run_to_tuple(run),
        )
        self._conn.commit()
        return run

    def get_run(self, run_id: str) -> WorkflowRun:
        """Retrieve the persisted ``WorkflowRun`` for ``run_id``.

        Args:
            run_id: The opaque run identifier returned by :meth:`create_run`.

        Returns:
            The matching ``WorkflowRun`` record.

        Raises:
            RunNotFoundError: If no run with the given id exists.
        """
        row = self._conn.execute(
            "SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise RunNotFoundError(f"run {run_id!r} not found")
        return _row_to_run(row)

    def list_runs(self) -> tuple[WorkflowRun, ...]:
        """Return all persisted workflow runs ordered by ``updated_at`` desc."""
        rows = self._conn.execute(
            "SELECT * FROM workflow_runs ORDER BY updated_at DESC"
        ).fetchall()
        return tuple(_row_to_run(row) for row in rows)

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    def update_run(
        self,
        run: WorkflowRun,
        expected_revision: int,
    ) -> WorkflowRun:
        """Atomically update ``run`` if its stored revision matches ``expected_revision``.

        The new revision is always ``expected_revision + 1`` so callers cannot
        skip revisions.

        Args:
            run: The desired run state (``revision`` is ignored).
            expected_revision: The revision the caller last observed.

        Returns:
            The updated ``WorkflowRun`` with the new revision.

        Raises:
            RunNotFoundError: If the run does not exist.
            RevisionConflictError: If the stored revision differs from
                ``expected_revision``.
        """
        with self._conn:
            row = self._conn.execute(
                "SELECT revision FROM workflow_runs WHERE run_id = ?",
                (run.run_id,),
            ).fetchone()
            if row is None:
                raise RunNotFoundError(f"run {run.run_id!r} not found")
            current_revision = row["revision"]
            if current_revision != expected_revision:
                raise RevisionConflictError(
                    f"revision conflict: expected {expected_revision}, "
                    f"found {current_revision}",
                    current_revision=current_revision,
                )

            new_revision = expected_revision + 1
            now = datetime.now(timezone.utc).isoformat()
            self._conn.execute(
                """
                UPDATE workflow_runs
                SET current_step = ?, revision = ?, status = ?, updated_at = ?
                WHERE run_id = ?
                """,
                (run.current_step, new_revision, run.status, now, run.run_id),
            )

        return self.get_run(run.run_id)

    def append_event(self, event: WorkflowEvent) -> WorkflowEvent:
        """Persist ``event`` to the append-only event stream.

        Args:
            event: The event to persist.  If ``event.sequence`` is 0, the next
                sequence number for the run is assigned automatically.

        Returns:
            The persisted event with its final sequence number.
        """
        sequence = event.sequence
        if sequence == 0:
            row = self._conn.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM workflow_events WHERE run_id = ?",
                (event.run_id,),
            ).fetchone()
            sequence = row[0]

        self._conn.execute(
            """
            INSERT INTO workflow_events (
                event_id, run_id, sequence, type, at, actor, from_step, to_step,
                revision, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.run_id,
                sequence,
                event.type,
                event.at,
                json.dumps(event.actor),
                event.from_step,
                event.to_step,
                event.revision,
                json.dumps(event.details),
            ),
        )
        self._conn.commit()
        return WorkflowEvent(
            event_id=event.event_id,
            run_id=event.run_id,
            sequence=sequence,
            type=event.type,
            at=event.at,
            actor=event.actor,
            from_step=event.from_step,
            to_step=event.to_step,
            revision=event.revision,
            details=event.details,
        )

    def get_events(self, run_id: str) -> tuple[WorkflowEvent, ...]:
        """Return all events for ``run_id`` in ascending sequence order."""
        rows = self._conn.execute(
            "SELECT * FROM workflow_events WHERE run_id = ? ORDER BY sequence",
            (run_id,),
        ).fetchall()
        return tuple(_row_to_event(row) for row in rows)

    def get_definition(self, run_id: str) -> WorkflowDefinition:
        """Return the definition pinned to the run identified by ``run_id``.

        Args:
            run_id: The opaque run identifier returned by :meth:`create_run`.

        Returns:
            The ``WorkflowDefinition`` the run is bound to, looked up from the
            catalog by ``definition_id`` and ``definition_version``.

        Raises:
            RunNotFoundError: If no run with the given id exists.
            DefinitionNotFoundError: If the pinned definition is not present
                in the attached catalog.
            RuntimeError: If the store was created without a catalog.
        """
        if self._catalog is None:
            raise RuntimeError("store has no catalog to resolve definitions")

        run = self.get_run(run_id)
        return self._catalog.get(run.definition_id, run.definition_version)
