"""Ground-truth test: parse acceptance.md and verify 34 AC IDs are present
and well-formed. Independent of louke validators.
"""
# AC-FR0400-01 (ground-truth half): independent AC closure baseline.

from __future__ import annotations

from pathlib import Path


from .independent_validator import parse_acceptance_ac_ids

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_ROOT = (
    REPO_ROOT / ".louke" / "project" / "specs" / "v0.14-002-workflow-reflow-design"
)
ACCEPTANCE_MD = SPEC_ROOT / "acceptance.md"


def test_acceptance_has_34_ac_ids():
    """acceptance.md must enumerate exactly 34 AC IDs (28 FR + 6 NFR)."""
    ac_ids = parse_acceptance_ac_ids(ACCEPTANCE_MD)
    assert len(ac_ids) == 34, f"expected 34 AC IDs, got {len(ac_ids)}: {ac_ids}"


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


def test_acceptance_has_28_fr_and_6_nfr():
    """Of 34 ACs, 28 must be FR and 6 must be NFR."""
    ac_ids = parse_acceptance_ac_ids(ACCEPTANCE_MD)
    fr = [a for a in ac_ids if a.startswith("AC-FR")]
    nfr = [a for a in ac_ids if a.startswith("AC-NFR")]
    assert len(fr) == 28, f"expected 28 FR ACs, got {len(fr)}"
    assert len(nfr) == 6, f"expected 6 NFR ACs, got {len(nfr)}"
