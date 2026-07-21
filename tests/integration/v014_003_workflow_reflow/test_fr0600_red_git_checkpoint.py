"""Integration tests for FR-0600: Private Red Git checkpoint.

AC-FR0600-01: After Red PASS, Git contains a commit ``R`` with
parent=``B`` and tree=``B + tests``, kept alive only by
``refs/louke/rgr/{run}/{task}/{attempt}/red``; metadata/evidence
includes command and failure fingerprint. The release branch still
points to ``B``, and ``R`` is not in formal ancestry/remote/ordinary
pre-commit/CI. A same-attempt different-commit compare-and-set fails.

Interfaces covered (per interfaces.md):
- IF-RGR-01 (Primary ARC-05, private ref authority ARC-06)
"""
# AC-FR0600-01

from __future__ import annotations

import pytest

from louke.v014.fr0600_red_git_checkpoint import (
    ERROR_CODES,
    PrivateRefError,
    PrivateRefStore,
    RedCheckpoint,
    RedCheckpointError,
    create_red_checkpoint,
)


def _valid_kwargs(store: PrivateRefStore) -> dict:
    return dict(
        store=store,
        run_id="run-001",
        task_id="T-001",
        attempt_no=1,
        baseline_oid="b" * 40,
        red_oid="r" * 40,
        test_command="pytest -q tests/unit/test_fr0100.py",
        failure_fingerprint="assertion:AC-FR0100-01",
        output_digest="sha256:output",
        creator="runtime:program",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_create_red_checkpoint_cas_creates_ref():
    """AC-FR0600-01: first-time CAS creates ref with R OID."""
    store = PrivateRefStore()
    cp = create_red_checkpoint(**_valid_kwargs(store))
    assert isinstance(cp, RedCheckpoint)
    expected_ref = "refs/louke/rgr/run-001/T-001/att-1/red"
    assert cp.ref == expected_ref
    assert store.refs[expected_ref] == "r" * 40
    # R.parent == B
    assert cp.parent == cp.baseline_oid == "b" * 40
    # Checkpoint metadata binds command, fingerprint, output digest, creator.
    assert cp.test_command == "pytest -q tests/unit/test_fr0100.py"
    assert cp.failure_fingerprint == "assertion:AC-FR0100-01"
    assert cp.output_digest == "sha256:output"
    assert cp.creator == "runtime:program"
    assert cp.checkpoint_id.startswith("red-cp:")


@pytest.mark.real_module
def test_create_red_checkpoint_does_not_move_release_branch():
    """AC-FR0600-01: branch still points to B; no remote push; no pre-commit/CI."""
    store = PrivateRefStore()
    create_red_checkpoint(**_valid_kwargs(store))
    assert store.branch_oid == "b" * 40  # still B
    assert store.remote_pushes == []  # no push
    assert store.precommit_invocations == 0  # R does NOT run pre-commit
    assert store.ci_invocations == 0  # R does NOT run CI


@pytest.mark.real_module
def test_create_red_checkpoint_idempotent_same_attempt_same_oid():
    """AC-FR0600-01: same attempt + same OID -> idempotent (no conflict)."""
    store = PrivateRefStore()
    kw = _valid_kwargs(store)
    cp1 = create_red_checkpoint(**kw)
    cp2 = create_red_checkpoint(**kw)  # same OID
    assert cp1.checkpoint_id == cp2.checkpoint_id
    assert cp1.red_oid == cp2.red_oid


@pytest.mark.real_module
def test_create_red_checkpoint_cas_fails_on_different_oid_same_attempt():
    """AC-FR0600-01: same attempt + different OID -> RGR_RED_REF_CONFLICT."""
    store = PrivateRefStore()
    create_red_checkpoint(**_valid_kwargs(store))
    # Same attempt, different OID.
    kw2 = _valid_kwargs(store)
    kw2["red_oid"] = "x" * 40
    with pytest.raises(PrivateRefError) as exc:
        create_red_checkpoint(**kw2)
    assert exc.value.code == "RGR_RED_REF_CONFLICT"


@pytest.mark.real_module
def test_create_red_checkpoint_rejects_missing_required_field():
    """AC-FR0600-01: missing required field -> RGR_RED_FAILURE_INVALID."""
    store = PrivateRefStore()
    kw = _valid_kwargs(store)
    kw["red_oid"] = ""
    with pytest.raises(RedCheckpointError) as exc:
        create_red_checkpoint(**kw)
    assert exc.value.code == "RGR_RED_FAILURE_INVALID"


@pytest.mark.real_module
def test_create_red_checkpoint_ref_uses_run_task_attempt_namespace():
    """AC-FR0600-01: ref name follows refs/louke/rgr/{run}/{task}/{attempt}/red."""
    store = PrivateRefStore()
    cp = create_red_checkpoint(**_valid_kwargs(store))
    assert cp.ref.startswith("refs/louke/rgr/run-001/T-001/att-")
    assert cp.ref.endswith("/red")


@pytest.mark.real_module
def test_create_red_checkpoint_distinct_attempts_have_distinct_refs():
    """AC-FR0600-01: two attempts on same task get distinct refs (no overwrite)."""
    store = PrivateRefStore()
    kw1 = _valid_kwargs(store)
    cp1 = create_red_checkpoint(**kw1)

    kw2 = _valid_kwargs(store)
    kw2["attempt_no"] = 2
    kw2["red_oid"] = "r2" + "r" * 38
    cp2 = create_red_checkpoint(**kw2)

    assert cp1.ref != cp2.ref
    # Both refs preserved (not overwritten).
    assert store.refs[cp1.ref] == "r" * 40
    assert store.refs[cp2.ref] == "r2" + "r" * 38


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR0600-01: ERROR_CODES includes all codes from interfaces.md §4."""
    expected = {
        "RGR_RED_REF_CONFLICT",
        "RGR_RED_FAILURE_INVALID",
        "RGR_LINEAGE_INVALID",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
