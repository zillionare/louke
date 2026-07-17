"""Unit tests for verify_acceptance.py L6 max-requirements gate.

Tests the deterministic hard gate that limits active FR/NFR requirements in a
spec to 30.  Active means not explicitly deprecated with metadata ``Valid=❌``.
"""

from __future__ import annotations

import textwrap

from louke._tools import verify_acceptance as va


# -- helpers ------------------------------------------------------------------


def _spec_with_frns(count: int, *, nfr: bool = False, header: str = "Valid") -> str:
    """Build a minimal spec.md with *count* FR or NFR requirements.

    Each requirement gets a ``### FR-0001`` (or ``### NFR-0001``) heading plus
    a metadata table marking it ``Valid=✅``.  The ``header`` parameter controls
    the column name (English or Chinese).
    """
    kind = "NFR" if nfr else "FR"
    lines = ["# Test Spec"]
    for i in range(1, count + 1):
        rid = f"{kind}-{i:04d}"
        lines.append(f"### {rid} Requirement {i}")
        lines.append(f"| {header} | Testable | Decided |")
        lines.append("|---------|----------|---------|")
        lines.append("| ✅ | ✅ | ✅ |")
        lines.append("")
    return "\n".join(lines)


def _spec_with_deprecated(active: int, deprecated: int, *, nfr: bool = False) -> str:
    """Build a spec with *active* valid + *deprecated* Valid=❌ requirements."""
    kind = "NFR" if nfr else "FR"
    lines = ["# Test Spec"]
    for i in range(1, active + 1):
        rid = f"{kind}-{i:04d}"
        lines.append(f"### {rid} Active Requirement {i}")
        lines.append("| Valid | Testable | Decided |")
        lines.append("|-------|----------|---------|")
        lines.append("| ✅ | ✅ | ✅ |")
        lines.append("")
    for i in range(active + 1, active + deprecated + 1):
        rid = f"{kind}-{i:04d}"
        lines.append(f"### {rid} Deprecated Requirement {i}")
        lines.append("| Valid | Testable | Decided |")
        lines.append("|-------|----------|---------|")
        lines.append("| ❌ | ✅ | ✅ |")
        lines.append("")
    return "\n".join(lines)


# -- L6: check_L6_max_requirements --------------------------------------------


def test_L6_passes_when_no_fr_nfr():
    """A spec with zero FR/NFR sections should pass (count=0 ≤ 30)."""
    spec = "# Empty spec\n\n## Nothing here\n"
    result = va.check_L6_max_requirements(spec)
    assert result.passed
    assert "0" in result.message


def test_L6_passes_at_exactly_30():
    """Exactly 30 active FRs should pass."""
    spec = _spec_with_frns(30)
    result = va.check_L6_max_requirements(spec)
    assert result.passed
    assert "30" in result.message


def test_L6_fails_at_31():
    """31 active FRs should fail with a clear diagnostic."""
    spec = _spec_with_frns(31)
    result = va.check_L6_max_requirements(spec)
    assert not result.passed
    assert "31" in (result.message or "")
    assert "30" in (result.message or "")
    assert len(result.failures) >= 1
    failure = result.failures[0]
    assert "31" in failure
    assert "30" in failure


def test_L6_fails_at_50():
    """50 active FRs should fail with the actual count in the message."""
    spec = _spec_with_frns(50)
    result = va.check_L6_max_requirements(spec)
    assert not result.passed
    assert "50" in (result.message or "")
    assert "30" in (result.message or "")


def test_L6_mixed_fr_and_nfr():
    """FR and NFR both count toward the 30 limit."""
    fr_lines = _spec_with_frns(20).splitlines()
    nfr_lines = _spec_with_frns(11, nfr=True).splitlines()
    # Remove duplicate "# Test Spec" header
    spec = "\n".join(fr_lines + nfr_lines[1:])
    result = va.check_L6_max_requirements(spec)
    assert not result.passed
    assert "31" in (result.message or "")


def test_L6_deprecated_excluded_english():
    """Deprecated FRs with English Valid=❌ are excluded from the count."""
    spec = _spec_with_deprecated(active=30, deprecated=5)
    result = va.check_L6_max_requirements(spec)
    assert result.passed, f"30 active + 5 deprecated should pass: {result.message}"
    assert "30" in result.message


def test_L6_deprecated_excluded_causes_fail_when_active_over_30():
    """When active count exceeds 30 even with deprecated excluded, it fails."""
    spec = _spec_with_deprecated(active=31, deprecated=5)
    result = va.check_L6_max_requirements(spec)
    assert not result.passed
    assert "31" in (result.message or "")


def test_L6_chinese_header_deprecated():
    """Chinese metadata header 有效需求=❌ should also exclude the requirement."""
    lines = [
        "# Test Spec",
        "### FR-0001 Active",
        "| 有效需求 | 可测性 | 是否已决定 |",
        "|---------|--------|----------|",
        "| ✅ | ✅ | ✅ |",
        "",
        "### FR-0002 Deprecated",
        "| 有效需求 | 可测性 | 是否已决定 |",
        "|---------|--------|----------|",
        "| ❌ | ✅ | ✅ |",
        "",
    ]
    spec = "\n".join(lines)
    result = va.check_L6_max_requirements(spec)
    assert result.passed
    assert "1" in result.message or "active" in result.message.lower()


def test_L6_nfr_deprecated_excluded():
    """Deprecated NFRs are also excluded from the count."""
    lines = [
        "# Test Spec",
        "### NFR-0001 Active NFR",
        "| Valid | Testable | Decided |",
        "|-------|----------|---------|",
        "| ✅ | ✅ | ✅ |",
        "",
        "### NFR-0002 Deprecated NFR",
        "| Valid | Testable | Decided |",
        "|-------|----------|---------|",
        "| ❌ | ✅ | ✅ |",
        "",
    ]
    spec = "\n".join(lines)
    result = va.check_L6_max_requirements(spec)
    assert result.passed
    assert "1" in result.message


def test_L6_all_deprecated_passes():
    """A spec where all FR/NFR are deprecated should pass (count=0)."""
    lines = [
        "# Test Spec",
        "### FR-0001 Deprecated",
        "| Valid | Testable | Decided |",
        "|-------|----------|---------|",
        "| ❌ | ✅ | ✅ |",
        "",
        "### FR-0002 Deprecated",
        "| Valid | Testable | Decided |",
        "|-------|----------|---------|",
        "| ❌ | ✅ | ✅ |",
        "",
    ]
    spec = "\n".join(lines)
    result = va.check_L6_max_requirements(spec)
    assert result.passed
    assert "0" in result.message


def test_L6_fr_without_table_counts_as_active():
    """An FR without a metadata table is treated as active (no deprecated marker)."""
    spec = textwrap.dedent("""\
        # Test Spec
        ### FR-0001 No table
        Plain text, no metadata table.
    """)
    result = va.check_L6_max_requirements(spec)
    assert result.passed
    assert "1" in result.message


def test_L6_undecided_testability_does_not_remove_from_count():
    """Undecided or testability status does not affect activity count.

    Only Valid=❌ removes a requirement from the active count.  Requirements
    with Valid=⚠️, Valid= (empty), etc. are still counted as active.
    """
    spec = textwrap.dedent("""\
        # Test Spec
        ### FR-0001 Undecided
        | Valid | Testable | Decided |
        |-------|----------|---------|
        | ⚠️ | ❌ | ⚠️ |
    """)
    result = va.check_L6_max_requirements(spec)
    assert result.passed
    assert "1" in result.message


# -- integration: run_checks includes L6 --------------------------------------


def test_run_checks_includes_L6(monkeypatch, tmp_path):
    """run_checks() must include L6 in the result list."""
    spec = _spec_with_frns(31)
    # We need a minimal acceptance.md to pass L1-L5
    acceptance = _build_minimal_acceptance(spec)
    results = va.run_checks(spec, acceptance)
    l6_results = [r for r in results if r.code == "L6"]
    assert len(l6_results) == 1, (
        f"L6 check missing from run_checks: {[r.code for r in results]}"
    )
    assert not l6_results[0].passed


def test_run_checks_L6_passes_for_valid_spec(monkeypatch, tmp_path):
    """run_checks() L6 passes for a spec with ≤30 active requirements."""
    spec = _spec_with_frns(5)
    acceptance = _build_minimal_acceptance(spec)
    results = va.run_checks(spec, acceptance)
    l6_results = [r for r in results if r.code == "L6"]
    assert len(l6_results) == 1
    assert l6_results[0].passed


# -- helpers ------------------------------------------------------------------


def _build_minimal_acceptance(spec_text: str) -> str:
    """Build a minimal acceptance.md that passes L1-L5 for the given spec."""
    frs = va.parse_fr_sections(spec_text)
    lines = ["# Acceptance"]
    for fr in frs:
        lines.append(f"## {fr.fr_id} {fr.fr_id}")
        lines.append("### AC-1")
        lines.append(f"- Verify {fr.fr_id} works correctly")
        lines.append("")
    return "\n".join(lines)
