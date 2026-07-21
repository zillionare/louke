"""Integration tests for FR-0100: M-IMPL entry & pre-commit reconcile.

AC-FR0100-01: Runtime may only enter M-IMPL after the current
implementation baseline is complete, the design program check and Prism
review are both PASS, and every workspace modification is attributable.
Entry preserves/merges existing hooks per the pre-commit contract,
installs/updates the managed entry, and reads back the actual
entry/version/config digest. Tracked managed-config changes form a
controlled infrastructure commit and a new baseline; local hook identity
is recorded only as evidence. Failure or drift blocks Archer/Devon
dispatch with a stable, diagnosable reason.

Interfaces covered (per interfaces.md):
- IF-IMPL-01 (Primary ARC-02)
- IF-PC-01 (inherited, ARC-02/ARC-05/ARC-10)
- IF-WFR-01 (ARC-01 context)

This file calls Devon's real ``louke.v014.fr0100_m_impl_entry`` module.
"""
# AC-FR0100-01

from __future__ import annotations

import pytest

from louke.v014.fr0100_m_impl_entry import (
    ERROR_CODES,
    ImplEntryError,
    ImplementationBaselineRecord,
    PreCommitReadback,
    enter_m_impl,
)


# ---------------------------------------------------------------------------
# Helpers: build valid baseline inputs
# ---------------------------------------------------------------------------


def _valid_inputs() -> dict:
    return {
        "run_id": "run-001",
        "release_identity": {
            "version": "0.14.0",
            "spec_id": "v0.14-003-workflow-reflow-impl",
            "branch": "releases/0.14.0",
            "tag": "v0.14.0",
        },
        "actor_id": "runtime:program",
        "attempt_id": "attempt-1",
        "base_commit": "a" * 40,
        "design": {
            "revision": "prism-r3-remediation-candidate",
            "digest": "sha256:design-digest",
            "program_evidence_id": "ev-001",
            "prism_review_id": "rev-001",
            "program_status": "PASS",
            "prism_verdict": "PASS",
        },
        "workspace": {
            "tree_digest": "sha256:tree",
            "diffs": [
                {
                    "path": ".pre-commit-config.yaml",
                    "digest": "sha256:cfg",
                    "source": "controlled-commit",
                },
            ],
        },
    }


def _valid_precommit_contract() -> dict:
    return {
        "payload": {
            "managed_config_path": ".pre-commit-config.yaml",
            "tool_version": "4.6.0",
            "stages": ["pre-commit"],
            "hooks": [
                {"id": "preserve-existing", "stages": ["pre-commit"]},
                {"id": "louke-rgr", "stages": ["pre-commit"]},
            ],
        }
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_enter_m_impl_returns_baseline_record_when_all_inputs_current():
    """AC-FR0100-01: valid inputs -> dispatch_eligible=True with full identity."""
    record = enter_m_impl(
        _valid_inputs(),
        precommit_contract=_valid_precommit_contract(),
        installed_stages=["pre-commit"],
        managed_config_present=True,
    )
    assert isinstance(record, ImplementationBaselineRecord)
    assert record.dispatch_eligible is True
    assert record.block_reason is None
    # Full identity binding per IF-IMPL-01 readback contract.
    for key in (
        "run_id",
        "release_identity",
        "baseline_id",
        "attempt_id",
        "actor_id",
        "base_commit",
        "design",
        "workspace",
        "precommit",
    ):
        # AC-FR0100-01: every identity field must be present and bound.
        assert getattr(record, key), f"record missing {key}"
    # Pre-commit readback must carry hook/config identity.
    assert isinstance(record.precommit, PreCommitReadback)
    assert record.precommit.readback_status == "in_sync"
    assert record.precommit.tool_version == "4.6.0"
    assert record.precommit.config_digest.startswith("sha256:")
    # Preserved and managed hooks are recorded separately (IF-IMPL-01
    # "preserved_hooks" / "managed_hooks" outputs).
    assert len(record.precommit.preserved_hooks) == 1
    assert len(record.precommit.managed_hooks) == 1


@pytest.mark.real_module
def test_enter_m_impl_blocks_when_design_program_not_pass():
    """AC-FR0100-01: design program_status != PASS -> IMPL_DESIGN_NOT_CURRENT."""
    inputs = _valid_inputs()
    inputs["design"]["program_status"] = "FAIL"
    with pytest.raises(ImplEntryError) as exc:
        enter_m_impl(
            inputs,
            precommit_contract=_valid_precommit_contract(),
            installed_stages=["pre-commit"],
            managed_config_present=True,
        )
    assert exc.value.code == "IMPL_DESIGN_NOT_CURRENT"


@pytest.mark.real_module
def test_enter_m_impl_blocks_when_prism_verdict_not_pass():
    """AC-FR0100-01: design prism_verdict != PASS -> IMPL_DESIGN_NOT_CURRENT."""
    inputs = _valid_inputs()
    inputs["design"]["prism_verdict"] = "REVISE"
    with pytest.raises(ImplEntryError) as exc:
        enter_m_impl(
            inputs,
            precommit_contract=_valid_precommit_contract(),
            installed_stages=["pre-commit"],
            managed_config_present=True,
        )
    assert exc.value.code == "IMPL_DESIGN_NOT_CURRENT"


@pytest.mark.real_module
def test_enter_m_impl_blocks_when_workspace_has_unattributed_diffs():
    """AC-FR0100-01: workspace with unattributed modifications blocks entry."""
    inputs = _valid_inputs()
    inputs["workspace"]["diffs"].append(
        {"path": "mystery.py", "digest": "sha256:x", "source": "unknown-tool"}
    )
    with pytest.raises(ImplEntryError) as exc:
        enter_m_impl(
            inputs,
            precommit_contract=_valid_precommit_contract(),
            installed_stages=["pre-commit"],
            managed_config_present=True,
        )
    assert exc.value.code == "IMPL_WORKSPACE_DIRTY_UNATTRIBUTED"


@pytest.mark.real_module
def test_enter_m_impl_blocks_when_precommit_contract_missing():
    """AC-FR0100-01: missing IF-PC-01 contract -> IMPL_PC_CONTRACT_MISSING."""
    with pytest.raises(ImplEntryError) as exc:
        enter_m_impl(
            _valid_inputs(),
            precommit_contract={},
            installed_stages=["pre-commit"],
            managed_config_present=True,
        )
    assert exc.value.code == "IMPL_PC_CONTRACT_MISSING"


@pytest.mark.real_module
def test_enter_m_impl_blocks_when_managed_config_absent():
    """AC-FR0100-01: managed_config_present=False -> IMPL_PC_READBACK_MISSING."""
    with pytest.raises(ImplEntryError) as exc:
        enter_m_impl(
            _valid_inputs(),
            precommit_contract=_valid_precommit_contract(),
            installed_stages=["pre-commit"],
            managed_config_present=False,
        )
    assert exc.value.code == "IMPL_PC_READBACK_MISSING"


@pytest.mark.real_module
def test_enter_m_impl_blocks_when_installed_stages_drift():
    """AC-FR0100-01: installed stages missing expected -> IMPL_PC_DRIFT."""
    with pytest.raises(ImplEntryError) as exc:
        enter_m_impl(
            _valid_inputs(),
            precommit_contract=_valid_precommit_contract(),
            installed_stages=[],  # nothing installed
            managed_config_present=True,
        )
    assert exc.value.code == "IMPL_PC_INSTALL_FAILED"

    # And a partial drift -> IMPL_PC_DRIFT
    with pytest.raises(ImplEntryError) as exc2:
        enter_m_impl(
            _valid_inputs(),
            precommit_contract={
                "payload": {
                    "managed_config_path": ".pre-commit-config.yaml",
                    "tool_version": "4.6.0",
                    "stages": ["pre-commit", "pre-push"],
                    "hooks": [],
                }
            },
            installed_stages=["pre-commit"],  # missing pre-push
            managed_config_present=True,
        )
    assert exc2.value.code == "IMPL_PC_DRIFT"


@pytest.mark.real_module
def test_enter_m_impl_emits_infrastructure_commit_on_tracked_config_change():
    """AC-FR0100-01: tracked_config_changes -> controlled infra commit
    (IF-IMPL-01 infrastructure_commit field)."""
    record = enter_m_impl(
        _valid_inputs(),
        precommit_contract=_valid_precommit_contract(),
        installed_stages=["pre-commit"],
        managed_config_present=True,
        tracked_config_changes=[
            {"path": ".pre-commit-config.yaml", "digest": "sha256:new"},
        ],
    )
    # AC-FR0100-01: tracked config changes produce a controlled infra commit.
    assert record.infrastructure_commit  # not None
    assert ".pre-commit-config.yaml" in record.infrastructure_commit.paths
    assert record.infrastructure_commit.expected_branch_oid == "a" * 40
    # Without tracked changes, no infrastructure commit is requested.
    record2 = enter_m_impl(
        _valid_inputs(),
        precommit_contract=_valid_precommit_contract(),
        installed_stages=["pre-commit"],
        managed_config_present=True,
    )
    # AC-FR0100-01: no tracked changes -> no infra commit.
    assert record2.infrastructure_commit is None or not record2.infrastructure_commit


@pytest.mark.real_module
def test_enter_m_impl_baseline_id_is_deterministic():
    """AC-FR0100-01: same inputs -> same baseline_id (IF-IMPL-01 identity)."""
    r1 = enter_m_impl(
        _valid_inputs(),
        precommit_contract=_valid_precommit_contract(),
        installed_stages=["pre-commit"],
        managed_config_present=True,
    )
    r2 = enter_m_impl(
        _valid_inputs(),
        precommit_contract=_valid_precommit_contract(),
        installed_stages=["pre-commit"],
        managed_config_present=True,
    )
    assert r1.baseline_id == r2.baseline_id
    assert r1.baseline_id.startswith("impl-baseline:")


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR0100-01: ERROR_CODES tuple includes every documented stable code
    from interfaces.md §1 (deterministic errors)."""
    expected = {
        "IMPL_DESIGN_NOT_CURRENT",
        "IMPL_WORKSPACE_DIRTY_UNATTRIBUTED",
        "IMPL_PC_CONTRACT_MISSING",
        "IMPL_PC_INSTALL_FAILED",
        "IMPL_PC_READBACK_MISSING",
        "IMPL_PC_DRIFT",
        "IMPL_INFRA_COMMIT_CONFLICT",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
