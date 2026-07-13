"""WorkflowRun state store.

Persists WorkflowRun identity, the pinned definition version, current step,
status and monotonic revision.  The store validates the definition through the
catalog before a run is created and never mutates a definition after creation.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from louke.runtime.catalog import (
    DefinitionValidationError,
    WorkflowDefinition,
    validate_definition,
)


class DefinitionInvalidError(ValueError):
    """Raised when a WorkflowRun is requested for an invalid definition."""

    def __init__(self, errors: list[DefinitionValidationError]) -> None:
        self.errors = errors
        super().__init__(f"definition invalid: {errors!r}")


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
        status: Run lifecycle status (e.g. ``created``).
        created_at: ISO 8601 UTC timestamp of run creation.
        updated_at: ISO 8601 UTC timestamp of the last update.
    """

    run_id: str
    definition_id: str
    definition_version: str
    current_step: str
    revision: int
    status: str
    created_at: str
    updated_at: str


_RUN_COLUMNS: tuple[str, ...] = (
    "run_id",
    "definition_id",
    "definition_version",
    "current_step",
    "revision",
    "status",
    "created_at",
    "updated_at",
)


def _run_to_tuple(run: WorkflowRun) -> tuple[str, str, str, str, int, str, str, str]:
    """Return a tuple matching ``_RUN_COLUMNS`` for the given ``run``."""
    return (
        run.run_id,
        run.definition_id,
        run.definition_version,
        run.current_step,
        run.revision,
        run.status,
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
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class WorkflowRunStore:
    """SQLite-backed store for WorkflowRun records.

    Args:
        db_path: Path to the SQLite database.  Defaults to an in-memory
            database so unit tests are isolated by default.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._conn = sqlite3.connect(db_path or ":memory:")
        self._conn.row_factory = sqlite3.Row
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
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
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

        now = datetime.now(timezone.utc).isoformat()
        run = WorkflowRun(
            run_id=f"run_{uuid.uuid4().hex[:12]}",
            definition_id=definition.definition_id,
            definition_version=definition.version,
            current_step=definition.start_step,
            revision=0,
            status="created",
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
