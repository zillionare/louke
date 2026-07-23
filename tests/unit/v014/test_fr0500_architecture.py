"""AC-FR0500-01: Architecture design closure.

FR-0500 requires Architecture to define component boundaries, dependency
direction, data/control flow, state/consistency, fault boundaries, security
and trust boundaries, migration/compatibility strategy and key technical
decisions - all traceable to requirements and host project facts.  Each
Interfaces status/permission/error/recovery semantic must be bidirectionally
mapped to a carrier component, state mechanism and security/trust/fault
boundary.  Missing carriers, orphans or bidirectional conflicts block the
baseline (AC-FR0500-01).
"""

from __future__ import annotations

from pathlib import Path


from louke.runtime.architecture import (
    ArchitectureReport,
    extract_architecture_anchors,
    extract_component_table,
    validate_architecture_carriers,
)

_SPEC_ROOT = (
    Path(__file__).resolve().parents[3]
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)
_ARCHITECTURE = _SPEC_ROOT / "architecture.md"
_INTERFACES = _SPEC_ROOT / "interfaces.md"
_ACCEPTANCE = _SPEC_ROOT / "acceptance.md"


def test_extract_architecture_anchors_returns_stable_set() -> None:
    """AC-FR0500-01: every ARC-* anchor is parsed from the doc."""
    anchors = extract_architecture_anchors(_ARCHITECTURE)
    expected = {
        "ARC-WEB",
        "ARC-DESIGN",
        "ARC-FACTS",
        "ARC-REGISTRY",
        "ARC-CONTRACTS",
        "ARC-VALIDATE",
        "ARC-PROMPTS",
        "ARC-CI",
        "ARC-PRECOMMIT",
        "ARC-VERSION",
        "ARC-BUILD",
        "ARC-PUBLISH",
        "ARC-REVIEW",
        "ARC-STORE",
        "ARC-MIGRATION",
        "ARC-SECURITY",
    }
    assert expected <= set(anchors)


def test_extract_component_table_yields_module_boundaries() -> None:
    """AC-FR0500-01: every module is described with component/role/non-goal."""
    components = extract_component_table(_ARCHITECTURE)
    assert components, "component table not parsed"
    component_ids = {c["module_id"] for c in components}
    assert {"DESIGN", "FACTS", "REGISTRY", "CONTRACTS", "VALIDATOR"} <= component_ids
    for component in components:
        assert component["component"]
        assert component["responsibility"]
        assert component["not_responsible_for"]


def test_validate_architecture_carriers_returns_pass_for_authored_doc() -> None:
    """AC-FR0500-01: the authored Architecture carriers all interface semantics."""
    report = validate_architecture_carriers(
        architecture_path=_ARCHITECTURE,
        interfaces_path=_INTERFACES,
    )
    assert isinstance(report, ArchitectureReport)
    assert report.status == "pass"
    assert not report.orphan_anchors
    assert not report.unsupported_interfaces


def test_validate_architecture_carriers_detects_orphan_anchor() -> None:
    """AC-FR0500-01: an ARC-* used only in Interfaces but not Architecture is detected."""
    bad_arch = _ARCHITECTURE.parent / "architecture_missing.md"
    bad_arch.write_text(
        _ARCHITECTURE.read_text().replace("ARC-SECURITY", "ARC-REMOVED"),
        encoding="utf-8",
    )
    try:
        report = validate_architecture_carriers(
            architecture_path=bad_arch,
            interfaces_path=_INTERFACES,
        )
        assert report.status == "fail"
        # Either ARC-SECURITY is missing from architecture or ARC-REMOVED is an
        # orphan in interfaces - both block baseline.
        assert report.orphan_anchors or report.missing_anchors
    finally:
        bad_arch.unlink()


def test_validate_architecture_carriers_detects_unsupported_interface() -> None:
    """AC-FR0500-01: an interface without a carrier anchor blocks baseline."""
    # Strip ARC-PROMPTS from architecture so IF-PRM-01 loses its carrier.
    bad_arch = _ARCHITECTURE.parent / "architecture_no_prompts.md"
    bad_arch.write_text(
        _ARCHITECTURE.read_text().replace("ARC-PROMPTS", "ARC-REMOVED"),
        encoding="utf-8",
    )
    try:
        report = validate_architecture_carriers(
            architecture_path=bad_arch,
            interfaces_path=_INTERFACES,
        )
        assert report.status == "fail"
        # IF-PRM-01 should lose at least one of its carriers
        assert report.unsupported_interfaces or report.orphan_anchors
    finally:
        bad_arch.unlink()


def test_validate_carriers_localises_failure_to_anchor_and_interface() -> None:
    """AC-FR0500-01: failures localise to specific FR/AC/interface/anchor."""
    report = validate_architecture_carriers(
        architecture_path=_ARCHITECTURE,
        interfaces_path=_INTERFACES,
    )
    # When passing, every interface has at least one carrier anchor
    for iface in report.interface_carriers:
        assert iface["interface_id"]
        assert iface["carriers"]
    # The report exposes both interface-side and anchor-side views
    assert isinstance(report.interface_carriers, list)
    assert isinstance(report.anchor_carriers, list)


def test_validate_carriers_rejects_undecided_technical_boundary() -> None:
    """AC-FR0500-01: leaving a technical boundary undecided for Devon blocks baseline."""
    bad_arch = _ARCHITECTURE.parent / "architecture_undecided.md"
    # Inject a marker phrase that signals an undecided technical boundary
    text = _ARCHITECTURE.read_text(encoding="utf-8")
    text = text + "\n\n## TBD - Devon to choose at implementation time\n"
    bad_arch.write_text(text, encoding="utf-8")
    try:
        report = validate_architecture_carriers(
            architecture_path=bad_arch,
            interfaces_path=_INTERFACES,
        )
        assert report.status == "fail"
        assert report.undecided_boundaries
    finally:
        bad_arch.unlink()


def test_report_is_deterministic() -> None:
    """AC-FR0500-01: validation is deterministic across runs."""
    first = validate_architecture_carriers(
        architecture_path=_ARCHITECTURE,
        interfaces_path=_INTERFACES,
    )
    second = validate_architecture_carriers(
        architecture_path=_ARCHITECTURE,
        interfaces_path=_INTERFACES,
    )
    assert first.status == second.status
    assert first.orphan_anchors == second.orphan_anchors
    assert first.unsupported_interfaces == second.unsupported_interfaces


def test_architecture_carries_security_and_trust_boundary() -> None:
    """AC-FR0500-01: ARC-SECURITY is a cross-module trust boundary."""
    text = _ARCHITECTURE.read_text(encoding="utf-8")
    assert "ARC-SECURITY" in text
    assert "信任" in text or "trust" in text.lower() or "security" in text.lower()


def test_architecture_carries_migration_strategy() -> None:
    """AC-FR0500-01: migration/compatibility strategy is defined."""
    text = _ARCHITECTURE.read_text(encoding="utf-8")
    assert "MIGRATION" in text or "迁移" in text
    assert "ARC-MIGRATION" in text
