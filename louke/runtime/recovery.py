"""Crash recovery for WorkflowRun state.

Recovery examines persisted step attempts and moves a run into a clear,
diagnosable status when it is impossible to know whether a step result was
committed before the Runtime process stopped.
"""

from __future__ import annotations

from louke.runtime.store import WorkflowRun, WorkflowRunStore


def recover_run(store: WorkflowRunStore, run_id: str) -> WorkflowRun:
    """Recover ``run_id`` after an uncertain interruption.

    If any step attempt is in ``started`` or ``uncertain`` status, the run is
    moved to ``needs_attention`` so a human can determine whether the step
    result was committed.  The run is never advanced automatically.

    Args:
        store: The workflow run store.
        run_id: The opaque run identifier.

    Returns:
        The recovered ``WorkflowRun``.
    """
    run = store.get_run(run_id)
    attempts = store.get_step_attempts(run_id)
    if not any(attempt.status in {"started", "uncertain"} for attempt in attempts):
        return run

    if run.status == "needs_attention":
        return run

    return store.update_run(
        WorkflowRun(
            run_id=run.run_id,
            definition_id=run.definition_id,
            definition_version=run.definition_version,
            current_step=run.current_step,
            revision=run.revision,
            status="needs_attention",
            contract_digest=run.contract_digest,
            created_at=run.created_at,
            updated_at=run.updated_at,
        ),
        run.revision,
    )
