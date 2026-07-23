"""Unit contracts for actionable Setup and Workbench diagnostics.

AC-NFR0501-01
"""

from louke.web.actionable_diagnostics import Diagnostic, validate_diagnostic


def test_diagnostic_contains_object_fact_impact_owner_and_recovery() -> None:
    """AC-NFR0501-01: generic failure text is insufficient."""
    diagnostic = Diagnostic(
        failed_object="repository remote",
        known_fact="origin is unreachable",
        impact="Setup cannot bind this workspace",
        responsible_party="Human",
        recovery_location="Repository step",
    )

    assert validate_diagnostic(diagnostic)
