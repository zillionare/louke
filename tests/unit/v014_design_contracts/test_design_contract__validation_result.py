"""AC-FR2600-01: IF-DES-02 unified design validation result.

``python -m louke._tools.design_contract validate`` runs the design-program
gate over the external manifest and emits a stable-check result envelope.  It
must expose the nine stable check IDs, resolve trace/interface/architecture/
contract closure, fail closed on an inactive registry, localise orphans/gaps to
FR/AC/interface/arch/contract, redact secrets, and be deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from louke._tools import design_contract as dc

_SPEC_ROOT = (
    Path(__file__).resolve().parents[3]
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)
_MANIFEST = _SPEC_ROOT / "design-artifacts" / "design-artifact-manifest.candidate.json"

_STABLE_CHECK_IDS = {
    "DESIGN.TRACE.CLOSURE",
    "DESIGN.INTERFACE.RESOLUTION",
    "DESIGN.ARCH.CARRIER",
    "DESIGN.CONTRACT.PARITY",
    "DESIGN.SCHEMA.ACTIVE",
    "DESIGN.PROMPT.PARITY",
    "DESIGN.DISCUSSION.OPEN",
    "DESIGN.DIFF.SCOPE",
    "DESIGN.SECRET",
}


def _manifest() -> dict[str, Any]:
    return json.loads(_MANIFEST.read_bytes())


def _checks_by_id(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["check_id"]: c for c in result["checks"]}


def test_result_exposes_all_stable_check_ids() -> None:
    """AC-FR2600-01: the validator emits every stable check ID."""
    result = dc.run(_manifest(), spec_root=_SPEC_ROOT)
    assert {c["check_id"] for c in result["checks"]} >= _STABLE_CHECK_IDS


def test_every_check_carries_localization_fields() -> None:
    """AC-FR2600-01: each check localises to FR/AC/interface/arch/contract."""
    result = dc.run(_manifest(), spec_root=_SPEC_ROOT)
    for check in result["checks"]:
        for field in (
            "fr_ids",
            "ac_ids",
            "interface_ids",
            "architecture_anchors",
            "contract_refs",
        ):
            assert isinstance(check[field], list)
        assert check["status"] in ("pass", "fail")
        assert isinstance(check["retryable"], bool)
        assert check["remediation"]


def test_trace_closure_passes_for_authored_manifest() -> None:
    """AC-FR2600-01: the authored manifest closes 34 AC with no orphan."""
    result = dc.run(_manifest(), spec_root=_SPEC_ROOT)
    closure = _checks_by_id(result)["DESIGN.TRACE.CLOSURE"]
    assert closure["status"] == "pass"


def test_contract_parity_passes_for_seven_instances() -> None:
    """AC-FR2600-01: contract parity validates all seven instances + provenance."""
    result = dc.run(_manifest(), spec_root=_SPEC_ROOT)
    parity = _checks_by_id(result)["DESIGN.CONTRACT.PARITY"]
    assert parity["status"] == "pass"
    assert len(parity["contract_refs"]) == 7


def test_schema_active_fails_closed_while_registry_candidate() -> None:
    """AC-FR2600-01: an inactive registry blocks baseline (fail-closed)."""
    result = dc.run(_manifest(), spec_root=_SPEC_ROOT)
    active = _checks_by_id(result)["DESIGN.SCHEMA.ACTIVE"]
    assert active["status"] == "fail"
    assert active["retryable"] is True
    assert result["status"] == "fail"  # any fail blocks baseline


def test_trace_closure_detects_missing_ac() -> None:
    """AC-FR2600-01: a dropped AC entry fails closure with expected/actual."""
    manifest = _manifest()
    manifest["ac_closure"] = manifest["ac_closure"][:-1]
    result = dc.run(manifest, spec_root=_SPEC_ROOT)
    closure = _checks_by_id(result)["DESIGN.TRACE.CLOSURE"]
    assert closure["status"] == "fail"
    assert closure["expected"] == 34
    assert closure["actual"] == 33


def test_interface_resolution_detects_orphan_interface() -> None:
    """AC-FR2600-01: an AC referencing an unknown interface is an orphan."""
    manifest = _manifest()
    manifest["ac_closure"][0]["if"] = ["IF-DOES-NOT-EXIST"]
    result = dc.run(manifest, spec_root=_SPEC_ROOT)
    resolution = _checks_by_id(result)["DESIGN.INTERFACE.RESOLUTION"]
    assert resolution["status"] == "fail"
    assert "IF-DOES-NOT-EXIST" in resolution["interface_ids"]
    assert resolution["ac_ids"]


def test_secret_check_never_echoes_actual_secret() -> None:
    """AC-FR2600-01: the secret gate reports paths/fingerprints, not raw secrets."""
    result = dc.run(_manifest(), spec_root=_SPEC_ROOT)
    secret = _checks_by_id(result)["DESIGN.SECRET"]
    assert secret["status"] == "pass"
    assert secret.get("actual") in (None, "")


def test_run_is_deterministic() -> None:
    """AC-NFR0100-01: repeated runs produce the same evidence digest."""
    first = dc.run(_manifest(), spec_root=_SPEC_ROOT)
    second = dc.run(_manifest(), spec_root=_SPEC_ROOT)
    assert first["evidence_digest"] == second["evidence_digest"]
    assert first["evidence_digest"].startswith("sha256:")


def test_cli_writes_output_and_exits_nonzero_when_failing(tmp_path: Path) -> None:
    """AC-FR2600-01: the CLI persists JSON evidence and exits non-zero on fail."""
    out = tmp_path / "evidence.json"
    code = dc.main(
        [
            "validate",
            "--manifest",
            str(_MANIFEST),
            "--format",
            "json",
            "--output",
            str(out),
        ]
    )
    assert code != 0  # fail-closed while registry is candidate
    payload = json.loads(out.read_text())
    assert {c["check_id"] for c in payload["checks"]} >= _STABLE_CHECK_IDS
