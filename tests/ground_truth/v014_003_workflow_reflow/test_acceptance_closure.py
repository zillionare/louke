"""Ground-truth test: parse acceptance.md and verify 36 AC IDs are present
and well-formed. Independent of any louke validator.
"""
# AC-FR0100-01 (ground-truth half): independent AC closure baseline.

from __future__ import annotations

from pathlib import Path


from .independent_validator import parse_acceptance_ac_ids

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_ROOT = (
    REPO_ROOT / ".louke" / "project" / "specs" / "v0.14-003-workflow-reflow-impl"
)
ACCEPTANCE_MD = SPEC_ROOT / "acceptance.md"


def test_acceptance_has_36_ac_ids():
    """acceptance.md must enumerate exactly 36 AC IDs (30 FR + 6 NFR)."""
    ac_ids = parse_acceptance_ac_ids(ACCEPTANCE_MD)
    assert len(ac_ids) == 36, f"expected 36 AC IDs, got {len(ac_ids)}: {ac_ids}"


def test_acceptance_ac_ids_are_unique():
    """AC IDs must not repeat."""
    ac_ids = parse_acceptance_ac_ids(ACCEPTANCE_MD)
    assert len(ac_ids) == len(set(ac_ids)), "duplicate AC IDs found"


def test_acceptance_ac_ids_match_pattern():
    """Every AC ID must match ``AC-(FR|NFR)XXXX-YY``."""
    import re

    ac_ids = parse_acceptance_ac_ids(ACCEPTANCE_MD)
    pattern = re.compile(r"^AC-(?:FR|NFR)\d{4}-\d{2}$")
    for ac_id in ac_ids:
        assert pattern.match(ac_id), f"bad AC ID format: {ac_id}"


def test_acceptance_has_30_fr_and_6_nfr():
    """Of 36 ACs, 30 must be FR and 6 must be NFR."""
    ac_ids = parse_acceptance_ac_ids(ACCEPTANCE_MD)
    fr = [a for a in ac_ids if a.startswith("AC-FR")]
    nfr = [a for a in ac_ids if a.startswith("AC-NFR")]
    assert len(fr) == 30, f"expected 30 FR ACs, got {len(fr)}"
    assert len(nfr) == 6, f"expected 6 NFR ACs, got {len(nfr)}"


def test_acceptance_covers_fr_0100_through_fr_3000():
    """FR AC IDs must span FR-0100 through FR-3000 in steps of 100."""
    ac_ids = parse_acceptance_ac_ids(ACCEPTANCE_MD)
    fr_numbers = sorted(int(a[5:9]) for a in ac_ids if a.startswith("AC-FR"))
    expected = list(range(100, 3100, 100))
    assert fr_numbers == expected, f"FR AC numbers mismatch: {fr_numbers}"


def test_acceptance_covers_nfr_0100_through_nfr_0600():
    """NFR AC IDs must span NFR-0100 through NFR-0600 in steps of 100."""
    ac_ids = parse_acceptance_ac_ids(ACCEPTANCE_MD)
    nfr_numbers = sorted(int(a[6:10]) for a in ac_ids if a.startswith("AC-NFR"))
    expected = list(range(100, 700, 100))
    assert nfr_numbers == expected, f"NFR AC numbers mismatch: {nfr_numbers}"
