"""Ground-truth test: verify spec/acceptance/test-plan/interfaces closure.

Independent of any louke validator. Reads spec bytes directly.
"""
# AC-FR0100-01 (ground-truth half): independent closure baseline.

from __future__ import annotations

from pathlib import Path


from .independent_validator import (
    REQUIRED_003_INTERFACES,
    REQUIRED_AC_IDS,
    REQUIRED_FR_IDS,
    REQUIRED_INHERITED_INTERFACES,
    REQUIRED_NFR_IDS,
    parse_acceptance_ac_ids,
    parse_interfaces_ids,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_ROOT = (
    REPO_ROOT / ".louke" / "project" / "specs" / "v0.14-003-workflow-reflow-impl"
)


def test_interfaces_md_has_all_16_003_if_ids():
    """interfaces.md must enumerate all 16 003 Runtime observable interfaces."""
    interfaces_md = SPEC_ROOT / "interfaces.md"
    found = set(parse_interfaces_ids(interfaces_md))
    missing = REQUIRED_003_INTERFACES - found
    assert not missing, f"interfaces.md missing 003 IF IDs: {missing}"


def test_interfaces_md_has_all_7_inherited_if_ids():
    """interfaces.md §17 must reference all 7 inherited 002 contracts."""
    interfaces_md = SPEC_ROOT / "interfaces.md"
    text = interfaces_md.read_text(encoding="utf-8")
    # The §17 section explicitly lists the 7 inherited contracts.
    for if_id in REQUIRED_INHERITED_INTERFACES:
        assert if_id in text, f"interfaces.md missing inherited IF {if_id}"


def test_acceptance_covers_all_36_required_ac_ids():
    """acceptance.md must enumerate all 36 required AC IDs."""
    acceptance_md = SPEC_ROOT / "acceptance.md"
    found = set(parse_acceptance_ac_ids(acceptance_md))
    missing = REQUIRED_AC_IDS - found
    assert not missing, f"acceptance.md missing AC IDs: {missing}"


def test_spec_md_mentions_all_30_fr_ids():
    """spec.md must mention all 30 FR IDs (FR-0100..FR-3000)."""
    spec_md = SPEC_ROOT / "spec.md"
    text = spec_md.read_text(encoding="utf-8")
    for fr_id in REQUIRED_FR_IDS:
        assert fr_id in text, f"spec.md missing {fr_id}"


def test_spec_md_mentions_all_6_nfr_ids():
    """spec.md must mention all 6 NFR IDs (NFR-0100..NFR-0600)."""
    spec_md = SPEC_ROOT / "spec.md"
    text = spec_md.read_text(encoding="utf-8")
    for nfr_id in REQUIRED_NFR_IDS:
        assert nfr_id in text, f"spec.md missing {nfr_id}"


def test_acceptance_ac_ids_match_required_set_exactly():
    """acceptance.md AC IDs must match the required set exactly (no extra)."""
    acceptance_md = SPEC_ROOT / "acceptance.md"
    found = set(parse_acceptance_ac_ids(acceptance_md))
    assert found == REQUIRED_AC_IDS, (
        f"AC ID set mismatch; extra: {found - REQUIRED_AC_IDS}; "
        f"missing: {REQUIRED_AC_IDS - found}"
    )


def test_003_if_count_is_16():
    """003 observable interface count must be exactly 16 (interfaces.md §18.1)."""
    interfaces_md = SPEC_ROOT / "interfaces.md"
    text = interfaces_md.read_text(encoding="utf-8")
    # §18.1 declares "003 Runtime observable interfaces (16/16)"
    assert "16/16" in text or "16 个" in text, (
        "interfaces.md §18.1 must declare 16/16 003 observable interfaces"
    )


def test_inherited_if_count_is_7():
    """Inherited 002 contract count must be exactly 7 (interfaces.md §18.2)."""
    interfaces_md = SPEC_ROOT / "interfaces.md"
    text = interfaces_md.read_text(encoding="utf-8")
    # §18.2 declares "inherited 002 contracts 7/7"
    assert "7/7" in text or "7 个" in text, (
        "interfaces.md §18.2 must declare 7/7 inherited contracts"
    )
