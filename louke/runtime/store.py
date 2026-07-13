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

    def with_status(self, status: str) -> "WorkflowRun":
        """Return a new run with the given ``status`` and updated timestamp."""
        from datetime import datetime, timezone

        return WorkflowRun(
            run_id=self.run_id,
            definition_id=self.definition_id,
            definition_version=self.definition_version,
            current_step=self.current_step,
            revision=self.revision,
            status=status,
            contract_digest=self.contract_digest,
            created_at=self.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def with_step(self, current_step: str, status: str) -> "WorkflowRun":
        """Return a new run positioned at ``current_step`` with ``status``."""
        from datetime import datetime, timezone

        return WorkflowRun(
            run_id=self.run_id,
            definition_id=self.definition_id,
            definition_version=self.definition_version,
            current_step=current_step,
            revision=self.revision,
            status=status,
            contract_digest=self.contract_digest,
            created_at=self.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )


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


class StepAttemptNotFoundError(ValueError):
    """Raised when a requested step attempt does not exist in the store."""


@dataclass(frozen=True, slots=True)
class StepAttempt:
    """A recorded attempt to execute a workflow step.

    Attributes:
        attempt_id: Opaque stable identifier for the attempt.
        run_id: Opaque run identifier the attempt belongs to.
        step_id: Step that was being attempted.
        idempotency_key: Stable key used to deduplicate the attempt.
        status: Lifecycle status of the attempt (``started``, ``completed``,
            ``failed`` or ``uncertain``).
        result: Result produced by the step, if already known.
        event_id: Id of the committed transition event, when completed.
        created_at: ISO 8601 UTC timestamp of attempt creation.
        updated_at: ISO 8601 UTC timestamp of the last update.
    """

    attempt_id: str
    run_id: str
    step_id: str
    idempotency_key: str
    status: str
    result: str | None
    event_id: str | None
    created_at: str
    updated_at: str

    def with_status(
        self,
        status: str,
        result: str | None = None,
        event_id: str | None = None,
    ) -> "StepAttempt":
        """Return a new attempt with the given status and updated timestamp."""
        from datetime import datetime, timezone

        return StepAttempt(
            attempt_id=self.attempt_id,
            run_id=self.run_id,
            step_id=self.step_id,
            idempotency_key=self.idempotency_key,
            status=status,
            result=result if result is not None else self.result,
            event_id=event_id if event_id is not None else self.event_id,
            created_at=self.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )


_ATTEMPT_COLUMNS: tuple[str, ...] = (
    "attempt_id",
    "run_id",
    "step_id",
    "idempotency_key",
    "status",
    "result",
    "event_id",
    "created_at",
    "updated_at",
)


def _attempt_to_tuple(
    attempt: StepAttempt,
) -> tuple[str, str, str, str, str, str | None, str | None, str, str]:
    """Return a tuple matching ``_ATTEMPT_COLUMNS`` for the given ``attempt``."""
    return (
        attempt.attempt_id,
        attempt.run_id,
        attempt.step_id,
        attempt.idempotency_key,
        attempt.status,
        attempt.result,
        attempt.event_id,
        attempt.created_at,
        attempt.updated_at,
    )


def _row_to_attempt(row: sqlite3.Row) -> StepAttempt:
    """Reconstruct a ``StepAttempt`` from a SQLite row."""
    return StepAttempt(
        attempt_id=row["attempt_id"],
        run_id=row["run_id"],
        step_id=row["step_id"],
        idempotency_key=row["idempotency_key"],
        status=row["status"],
        result=row["result"],
        event_id=row["event_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


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
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS step_attempts (
                attempt_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT,
                event_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_step_attempts_run_id
            ON step_attempts(run_id)
            """
        )
        self._conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_step_attempts_idempotency
            ON step_attempts(run_id, idempotency_key)
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

    def get_event(self, event_id: str) -> WorkflowEvent:
        """Retrieve a single event by ``event_id``.

        Args:
            event_id: The opaque event identifier.

        Returns:
            The matching ``WorkflowEvent``.

        Raises:
            ValueError: If no event with the given id exists.
        """
        row = self._conn.execute(
            "SELECT * FROM workflow_events WHERE event_id = ?", (event_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"event {event_id!r} not found")
        return _row_to_event(row)

    def record_step_attempt(
        self,
        run_id: str,
        step_id: str,
        idempotency_key: str,
        status: str = "started",
        result: str | None = None,
        event_id: str | None = None,
    ) -> StepAttempt:
        """Persist a new step attempt.

        Args:
            run_id: The run the attempt belongs to.
            step_id: The step being attempted.
            idempotency_key: Stable key used to deduplicate the attempt.
            status: Attempt status (``started``, ``completed``, ``failed`` or
                ``uncertain``).
            result: Step result, when already known.
            event_id: Committed transition event id, when completed.

        Returns:
            The newly created ``StepAttempt``.
        """
        now = datetime.now(timezone.utc).isoformat()
        attempt = StepAttempt(
            attempt_id=f"att_{uuid.uuid4().hex[:12]}",
            run_id=run_id,
            step_id=step_id,
            idempotency_key=idempotency_key,
            status=status,
            result=result,
            event_id=event_id,
            created_at=now,
            updated_at=now,
        )
        column_list = ", ".join(_ATTEMPT_COLUMNS)
        placeholders = ", ".join("?" for _ in _ATTEMPT_COLUMNS)
        self._conn.execute(
            f"INSERT INTO step_attempts ({column_list}) VALUES ({placeholders})",
            _attempt_to_tuple(attempt),
        )
        self._conn.commit()
        return attempt

    def get_step_attempts(self, run_id: str) -> tuple[StepAttempt, ...]:
        """Return all step attempts for ``run_id`` ordered by ``created_at`` asc."""
        rows = self._conn.execute(
            "SELECT * FROM step_attempts WHERE run_id = ? ORDER BY created_at",
            (run_id,),
        ).fetchall()
        return tuple(_row_to_attempt(row) for row in rows)

    def get_step_attempt_by_key(
        self,
        run_id: str,
        idempotency_key: str,
    ) -> StepAttempt | None:
        """Return the completed step attempt matching ``run_id`` and ``idempotency_key``.

        Args:
            run_id: The run to search within.
            idempotency_key: The stable idempotency key.

        Returns:
            The matching ``StepAttempt`` if one exists, otherwise ``None``.
        """
        row = self._conn.execute(
            """
            SELECT * FROM step_attempts
            WHERE run_id = ? AND idempotency_key = ? AND status = 'completed'
            """,
            (run_id, idempotency_key),
        ).fetchone()
        if row is None:
            return None
        return _row_to_attempt(row)

    def update_step_attempt(
        self,
        attempt: StepAttempt,
    ) -> StepAttempt:
        """Update an existing step attempt.

        Args:
            attempt: The attempt with updated fields.

        Returns:
            The updated ``StepAttempt``.

        Raises:
            StepAttemptNotFoundError: If the attempt does not exist.
        """
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """
            UPDATE step_attempts
            SET step_id = ?, idempotency_key = ?, status = ?, result = ?,
                event_id = ?, updated_at = ?
            WHERE attempt_id = ?
            """,
            (
                attempt.step_id,
                attempt.idempotency_key,
                attempt.status,
                attempt.result,
                attempt.event_id,
                now,
                attempt.attempt_id,
            ),
        )
        if cursor.rowcount == 0:
            raise StepAttemptNotFoundError(
                f"step attempt {attempt.attempt_id!r} not found"
            )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM step_attempts WHERE attempt_id = ?",
            (attempt.attempt_id,),
        ).fetchone()
        return _row_to_attempt(row)

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
