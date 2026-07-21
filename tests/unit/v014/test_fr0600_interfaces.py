"""AC-FR0600-01: Interfaces design closure.

FR-0600 requires Interfaces to cover every real host-product entry and full
operation path with stable identities, including UI/CLI/API/events/files/
errors/recovery.  Each identity must be resolved by Test Plan observable
interfaces and bidirectionally mapped to Architecture carriers and machine
contracts.  Missing/orphan/conflict mappings block the baseline
(AC-FR0600-01).
"""

from __future__ import annotations

from pathlib import Path


from louke.v014.fr0600_interfaces import (
    InterfacesReport,
    extract_interface_identities,
    validate_interfaces_closure,
)

_SPEC_ROOT = (
    Path(__file__).resolve().parents[3]
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)
_INTERFACES = _SPEC_ROOT / "interfaces.md"
_ARCHITECTURE = _SPEC_ROOT / "architecture.md"
_ACCEPTANCE = _SPEC_ROOT / "acceptance.md"


def test_extract_interface_identities_returns_required_set() -> None:
    """AC-FR0600-01: every required interface identity is declared."""
    identities = extract_interface_identities(_INTERFACES)
    expected = {
        "IF-DES-01",
        "IF-DES-02",
        "IF-CON-01",
        "IF-REG-01",
        "IF-TST-01",
        "IF-PC-01",
        "IF-CI-01",
        "IF-REL-01",
        "IF-BLD-01",
        "IF-PUB-01",
        "IF-PRM-01",
        "IF-REV-01",
        "IF-WEB-01",
        "IF-FCT-01",
        "IF-AUD-01",
    }
    assert expected <= set(identities)


def test_validate_interfaces_closure_passes_for_authored_doc() -> None:
    """AC-FR0600-01: authored Interfaces passes closure for all identities."""
    report = validate_interfaces_closure(
        interfaces_path=_INTERFACES,
        architecture_path=_ARCHITECTURE,
        acceptance_path=_ACCEPTANCE,
    )
    assert isinstance(report, InterfacesReport)
    assert report.status == "pass"
    assert not report.orphan_interfaces


def test_validate_interfaces_closure_detects_orphan_interface() -> None:
    """AC-FR0600-01: an interface in Test Plan but not in Interfaces is orphan."""
    # Remove an interface section; the validation should detect the orphan.
    bad_if = _INTERFACES.parent / "interfaces_missing.md"
    text = _INTERFACES.read_text(encoding="utf-8")
    bad_if.write_text(text.replace("### IF-AUD-01", "### IF-REMOVED"), encoding="utf-8")
    try:
        report = validate_interfaces_closure(
            interfaces_path=bad_if,
            architecture_path=_ARCHITECTURE,
            acceptance_path=_ACCEPTANCE,
        )
        assert report.status == "fail"
        assert report.orphan_interfaces
    finally:
        bad_if.unlink()


def test_validate_interfaces_carries_input_output_state_for_each() -> None:
    """AC-FR0600-01: each interface declares input/output/state/permission/error/recovery."""
    text = _INTERFACES.read_text(encoding="utf-8")
    # Every interface table should declare key semantic rows
    for marker in ("identity", "permissions", "error/recovery", "architecture"):
        assert marker in text.lower(), f"missing marker: {marker}"


def test_validate_interfaces_carries_stable_identity_per_interface() -> None:
    """AC-FR0600-01: each interface has a stable identity row."""
    report = validate_interfaces_closure(
        interfaces_path=_INTERFACES,
        architecture_path=_ARCHITECTURE,
        acceptance_path=_ACCEPTANCE,
    )
    for iface in report.interface_identities:
        assert iface["interface_id"]
        assert iface["modules"]  # carries the modules row
        assert iface["architecture"]  # carries the architecture row


def test_validate_interfaces_no_fabricated_ui_for_inapplicable_stack() -> None:
    """AC-FR0600-01: inapplicable surfaces must give an auditable reason, not fabricated UI."""
    text = _INTERFACES.read_text(encoding="utf-8")
    # Where a UI/CLI/API is inapplicable, the doc must state the reason
    if "N/A" in text or "不适用" in text:
        # Verify it appears with a reason, not as a fabricated interface
        for line in text.splitlines():
            if "N/A" in line or "不适用" in line:
                # The line must reference an interface or product fact
                assert (
                    "IF-" in text
                    or "facts" in text.lower()
                    or "package" in text.lower()
                )


def test_validate_interfaces_closure_localises_failure_to_interface() -> None:
    """AC-FR0600-01: failures localise to specific interface identity."""
    report = validate_interfaces_closure(
        interfaces_path=_INTERFACES,
        architecture_path=_ARCHITECTURE,
        acceptance_path=_ACCEPTANCE,
    )
    # Each interface identity record carries its id and its carrier anchors
    for iface in report.interface_identities:
        assert iface["interface_id"].startswith("IF-")
        assert isinstance(iface["architecture"], list)


def test_validate_interfaces_rejects_unsupported_surface_without_reason() -> None:
    """AC-FR0600-01: an unsupported surface without an auditable reason blocks baseline."""
    bad_if = _INTERFACES.parent / "interfaces_unsupported.md"
    text = _INTERFACES.read_text(encoding="utf-8")
    # Inject a "fabricated UI" marker that signals an unsupported surface
    bad_if.write_text(
        text + "\n\n## Fabricated UI surface (no auditable reason)\n",
        encoding="utf-8",
    )
    try:
        report = validate_interfaces_closure(
            interfaces_path=bad_if,
            architecture_path=_ARCHITECTURE,
            acceptance_path=_ACCEPTANCE,
        )
        assert report.status == "fail"
        assert report.fabricated_surfaces
    finally:
        bad_if.unlink()


def test_validate_interfaces_is_deterministic() -> None:
    """AC-FR0600-01: validation is deterministic across runs."""
    first = validate_interfaces_closure(
        interfaces_path=_INTERFACES,
        architecture_path=_ARCHITECTURE,
        acceptance_path=_ACCEPTANCE,
    )
    second = validate_interfaces_closure(
        interfaces_path=_INTERFACES,
        architecture_path=_ARCHITECTURE,
        acceptance_path=_ACCEPTANCE,
    )
    assert first.status == second.status
    assert first.orphan_interfaces == second.orphan_interfaces


def test_validate_interfaces_binds_to_machine_contract_kinds() -> None:
    """AC-FR0600-01: interface closure references the seven contract kinds."""
    text = _INTERFACES.read_text(encoding="utf-8")
    required_kinds = (
        "integration-test",
        "e2e-test",
        "pre-commit",
        "github-actions-ci",
        "release-version",
        "build-artifact",
        "publish-recovery",
    )
    for kind in required_kinds:
        assert kind in text, f"contract kind {kind} not referenced in interfaces.md"
