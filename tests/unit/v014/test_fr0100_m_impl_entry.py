"""AC-FR0100-01: M-IMPL entry & pre-commit reconcile.

Runtime may only enter ``M-IMPL`` when the current implementation baseline
is complete, the design program check and Prism review are both PASS, and
every workspace modification is attributable.  Entry must preserve/merge
existing hooks per the pre-commit contract, install or update the managed
entry, and read back the actual entry/version/config digest.  Tracked
config changes form a controlled infrastructure commit and a new baseline;
local hook identity is only recorded as evidence.  Any missing design PASS,
stale digest, unattributed modification, hook install/readback failure or
drift must block Archer/Devon dispatch and enter a diagnosable blocked
state.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from louke.v014.fr0100_m_impl_entry import (
    ImplEntryError,
    ImplementationBaselineRecord,
    PreCommitReadback,
    enter_m_impl,
)

_ROOT = Path(__file__).resolve().parents[3]
_SPEC_ROOT = _ROOT / ".louke" / "project" / "specs" / "v0.14-003-workflow-reflow-impl"
_PC_CONTRACT_ROOT = (
    _ROOT
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
    / "design-artifacts"
    / "contracts"
    / "pre-commit.candidate.json"
)


def _design_pass() -> dict[str, Any]:
    return {
        "revision": "design-rev:abc",
        "digest": "sha256:" + "a" * 64,
        "program_evidence_id": "ev-design-program-pass",
        "prism_review_id": "rev-design-prism-pass",
        "program_status": "PASS",
        "prism_verdict": "PASS",
    }


def _clean_workspace() -> dict[str, Any]:
    return {"tree_digest": "sha256:" + "c" * 64, "diffs": []}


def _precommit_contract() -> dict[str, Any]:
    import json

    return json.loads(_PC_CONTRACT_ROOT.read_bytes())


def _inputs() -> dict[str, Any]:
    return {
        "run_id": "run-v0.14.003-impl-r1",
        "release_identity": {
            "version": "0.14.0",
            "spec_id": "v0.14-003-workflow-reflow-impl",
            "branch": "releases/0.14.0",
            "tag": "v0.14.0",
        },
        "actor_id": "runtime:program",
        "attempt_id": "att-impl-r1",
        "base_commit": "2734177ef5398e4c10a1f68039ec469ccc21f2b8",
        "design": _design_pass(),
        "workspace": _clean_workspace(),
    }


def test_enter_m_impl_persists_full_baseline_record() -> None:
    """AC-FR0100-01: current inputs yield a baseline record binding every identity."""
    record = enter_m_impl(
        _inputs(),
        precommit_contract=_precommit_contract(),
        installed_stages=["pre-commit"],
        managed_config_present=True,
    )
    assert isinstance(record, ImplementationBaselineRecord)
    assert record.run_id == "run-v0.14.003-impl-r1"
    assert record.attempt_id == "att-impl-r1"
    assert record.dispatch_eligible is True
    assert record.block_reason is None
    assert record.precommit.entry == "pre-commit"
    assert record.precommit.tool_version
    assert record.precommit.config_digest.startswith("sha256:")
    assert record.precommit.readback_status == "in_sync"


def test_enter_m_impl_blocks_when_design_program_not_pass() -> None:
    """AC-FR0100-01: missing design program PASS blocks dispatch."""
    inputs = _inputs()
    inputs["design"] = _design_pass() | {"program_status": "FAIL"}
    with pytest.raises(ImplEntryError) as exc:
        enter_m_impl(
            inputs,
            precommit_contract=_precommit_contract(),
            installed_stages=["pre-commit"],
            managed_config_present=True,
        )
    assert exc.value.code == "IMPL_DESIGN_NOT_CURRENT"


def test_enter_m_impl_blocks_when_prism_review_not_pass() -> None:
    """AC-FR0100-01: missing Prism PASS blocks dispatch."""
    inputs = _inputs()
    inputs["design"] = _design_pass() | {"prism_verdict": "REVISE"}
    with pytest.raises(ImplEntryError) as exc:
        enter_m_impl(
            inputs,
            precommit_contract=_precommit_contract(),
            installed_stages=["pre-commit"],
            managed_config_present=True,
        )
    assert exc.value.code == "IMPL_DESIGN_NOT_CURRENT"


def test_enter_m_impl_blocks_when_workspace_has_unattributed_diff() -> None:
    """AC-FR0100-01: unattributed workspace modification blocks dispatch."""
    inputs = _inputs()
    inputs["workspace"] = {
        "tree_digest": "sha256:" + "d" * 64,
        "diffs": [
            {"path": "src/x.py", "digest": "sha256:" + "1" * 64, "source": "unknown"},
        ],
    }
    with pytest.raises(ImplEntryError) as exc:
        enter_m_impl(
            inputs,
            precommit_contract=_precommit_contract(),
            installed_stages=["pre-commit"],
            managed_config_present=True,
        )
    assert exc.value.code == "IMPL_WORKSPACE_DIRTY_UNATTRIBUTED"


def test_enter_m_impl_blocks_when_hook_install_missing() -> None:
    """AC-FR0100-01: hook install/readback failure blocks dispatch."""
    inputs = _inputs()
    with pytest.raises(ImplEntryError) as exc:
        enter_m_impl(
            inputs,
            precommit_contract=_precommit_contract(),
            installed_stages=[],
            managed_config_present=True,
        )
    assert exc.value.code == "IMPL_PC_INSTALL_FAILED"


def test_enter_m_impl_blocks_when_managed_config_missing() -> None:
    """AC-FR0100-01: managed config missing blocks dispatch."""
    inputs = _inputs()
    with pytest.raises(ImplEntryError) as exc:
        enter_m_impl(
            inputs,
            precommit_contract=_precommit_contract(),
            installed_stages=["pre-commit"],
            managed_config_present=False,
        )
    assert exc.value.code == "IMPL_PC_READBACK_MISSING"


def test_enter_m_impl_blocks_when_drift_detected() -> None:
    """AC-FR0100-01: hook drift (missing expected stage) blocks dispatch."""
    inputs = _inputs()
    with pytest.raises(ImplEntryError) as exc:
        enter_m_impl(
            inputs,
            precommit_contract=_precommit_contract(),
            installed_stages=["commit-msg"],  # missing pre-commit stage
            managed_config_present=True,
        )
    assert exc.value.code == "IMPL_PC_DRIFT"


def test_tracked_config_change_produces_infrastructure_commit() -> None:
    """AC-FR0100-01: tracked managed config change yields infra commit + new baseline."""
    inputs = _inputs()
    record = enter_m_impl(
        inputs,
        precommit_contract=_precommit_contract(),
        installed_stages=["pre-commit"],
        managed_config_present=True,
        tracked_config_changes=[
            {"path": ".pre-commit-config.yaml", "digest": "sha256:" + "9" * 64},
        ],
    )
    infra = record.infrastructure_commit
    assert infra is not None  # AC-FR0100-01
    assert infra.paths == (".pre-commit-config.yaml",)
    assert record.infrastructure_commit.expected_branch_oid == inputs["base_commit"]
    assert record.precommit.readback_status == "in_sync"


def test_local_hook_identity_recorded_only_as_evidence() -> None:
    """AC-FR0100-01: local hook identity does not become a tracked commit."""
    record = enter_m_impl(
        _inputs(),
        precommit_contract=_precommit_contract(),
        installed_stages=["pre-commit"],
        managed_config_present=True,
    )
    # No tracked config changes -> no infrastructure commit; hook identity
    # is only carried in the readback evidence envelope.
    assert record.infrastructure_commit is None
    assert record.precommit.preserved_hooks  # existing hooks captured
    assert record.precommit.readback_status == "in_sync"


def test_baseline_record_immutable_and_reidentifies_inputs() -> None:
    """AC-FR0100-01: the persisted baseline is immutable and reidentifies inputs."""
    record = enter_m_impl(
        _inputs(),
        precommit_contract=_precommit_contract(),
        installed_stages=["pre-commit"],
        managed_config_present=True,
    )
    with pytest.raises(Exception):
        record.run_id = "tampered"  # type: ignore[misc]
    again = enter_m_impl(
        _inputs(),
        precommit_contract=_precommit_contract(),
        installed_stages=["pre-commit"],
        managed_config_present=True,
    )
    assert again.baseline_id == record.baseline_id


def test_readback_records_preserved_and_managed_hooks() -> None:
    """AC-FR0100-01: readback distinguishes preserved vs managed hooks."""
    contract = _precommit_contract()
    record = enter_m_impl(
        _inputs(),
        precommit_contract=contract,
        installed_stages=["pre-commit"],
        managed_config_present=True,
    )
    assert isinstance(record.precommit, PreCommitReadback)
    preserved = {h["id"] for h in record.precommit.preserved_hooks}
    managed = {h["id"] for h in record.precommit.managed_hooks}
    assert "preserve-existing" in preserved
    assert "louke-fast-quality" in managed
