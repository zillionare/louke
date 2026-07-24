"""IF-12: Structured operation evidence.

AC-NFR0001-02, AC-NFR0101-01, AC-NFR0501-01

Integration tests verify that structured evidence does not leak secrets,
that uncertain results are distinct from success, and that diagnostics are
actionable.
"""

from __future__ import annotations

import pytest

from louke.web.actionable_diagnostics import Diagnostic, validate_diagnostic
from louke.web.setup_operations import OperationResult


def test_uncertain_result_not_equal_to_succeeded():
    """AC-NFR0001-02: uncertain result state is not succeeded."""
    # AC-NFR0001-02
    result = OperationResult("uncertain", "cannot verify")
    assert result.state != "succeeded"
    assert result.state == "uncertain"


def test_failed_result_not_equal_to_succeeded():
    """AC-NFR0001-02: failed result state is not succeeded."""
    # AC-NFR0001-02
    result = OperationResult("failed", "git init failed")
    assert result.state != "succeeded"


def test_evidence_text_redacts_credentials():
    """AC-NFR0101-01: evidence text does not contain credential secrets in URLs."""
    # AC-NFR0101-01
    from louke.web.secret_redaction import redact_url

    canary = "super-secret-canary"
    raw = f"https://user:{canary}@github.com/org/repo.git"
    redacted = redact_url(raw)
    assert canary not in redacted


def test_diagnostic_contains_all_required_fields():
    """AC-NFR0501-01: diagnostic has failed_object, known_fact, impact, party, recovery."""
    # AC-NFR0501-01
    diag = Diagnostic(
        failed_object="repository_clone",
        known_fact="remote URL is unreachable",
        impact="Setup cannot complete repository binding",
        responsible_party="human",
        recovery_location="/setup?step=repository",
    )
    assert validate_diagnostic(diag) is True


def test_diagnostic_without_recovery_location_fails():
    """AC-NFR0501-01: diagnostic without recovery location is not valid."""
    # AC-NFR0501-01
    diag = Diagnostic(
        failed_object="repository_clone",
        known_fact="remote unreachable",
        impact="Setup blocked",
        responsible_party="human",
        recovery_location="",
    )
    with pytest.raises(ValueError, match="actionable"):
        validate_diagnostic(diag)


def test_diagnostic_without_impact_fails():
    """AC-NFR0501-01: diagnostic without impact description is not valid."""
    # AC-NFR0501-01
    diag = Diagnostic(
        failed_object="repository_clone",
        known_fact="remote unreachable",
        impact="",
        responsible_party="human",
        recovery_location="/setup?step=repository",
    )
    with pytest.raises(ValueError, match="actionable"):
        validate_diagnostic(diag)


def test_operation_result_requires_human_for_uncertain():
    """AC-NFR0501-01: uncertain operation result requires human attention."""
    # AC-NFR0501-01
    result = OperationResult("uncertain", "cannot read back result")
    assert result.requires_human is True
