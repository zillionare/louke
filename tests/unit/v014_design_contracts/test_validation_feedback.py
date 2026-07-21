"""AC-NFR0500-01: validation feedback operability.

NFR-0500 requires program validation failures to return a stable check ID,
artifact path/field, expected vs actual, related FR/AC/contract/prompt
identity and retryability - never a generic 'invalid design' string.  The
UI/API must let users navigate from the result to the failing artifact
anchor.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from louke._tools.validation_feedback import (
    FeedbackError,
    ValidationFeedback,
    build_feedback,
    feedback_to_dict,
    verify_actionable_feedback,
)

_SPEC_ROOT = (
    Path(__file__).resolve().parents[3]
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)


def test_build_feedback_returns_typed_record() -> None:
    """AC-NFR0500-01: a feedback record carries stable check id + path/field."""
    feedback = build_feedback(
        check_id="DESIGN.TRACE.CLOSURE",
        artifact_path=".louke/project/specs/v0.14-002/spec.md",
        field="acceptance.ac_ids",
        expected=34,
        actual=33,
        fr_ids=("FR-2600",),
        ac_ids=("AC-FR2600-01",),
        contract_refs=(),
        prompt_identity=None,
        retryable=True,
        remediation="restore every required AC closure entry before baseline",
    )
    assert isinstance(feedback, ValidationFeedback)
    assert feedback.check_id == "DESIGN.TRACE.CLOSURE"
    assert feedback.expected == 34
    assert feedback.actual == 33
    assert feedback.retryable is True
    assert feedback.fr_ids == ("FR-2600",)
    assert feedback.ac_ids == ("AC-FR2600-01",)


def test_verify_actionable_feedback_passes_for_complete_record() -> None:
    """AC-NFR0500-01: a complete record passes operability checks."""
    feedback = build_feedback(
        check_id="DESIGN.INTERFACE.RESOLUTION",
        artifact_path=".louke/project/specs/v0.14-002/interfaces.md",
        field="IF-DES-01",
        expected="IF-DES-01 in interface_set",
        actual="IF-DES-01 missing",
        fr_ids=("FR-2600",),
        ac_ids=("AC-FR2600-01",),
        contract_refs=(),
        prompt_identity=None,
        retryable=True,
        remediation="restore IF-DES-01 to interfaces.md",
    )
    verify_actionable_feedback(feedback)  # does not raise


def test_verify_actionable_feedback_rejects_generic_message() -> None:
    """AC-NFR0500-01: a generic 'invalid design' message is rejected."""
    feedback = ValidationFeedback(
        check_id="DESIGN.GENERIC",
        artifact_path="some/path.md",
        field="some.field",
        expected="x",
        actual="invalid design",
        fr_ids=("FR-1",),
        ac_ids=("AC-FR1-01",),
        contract_refs=(),
        prompt_identity=None,
        retryable=False,
        remediation="invalid design",
    )
    with pytest.raises(FeedbackError) as exc:
        verify_actionable_feedback(feedback)
    assert exc.value.code == "FEEDBACK_NOT_ACTIONABLE"


def test_verify_actionable_feedback_rejects_missing_check_id() -> None:
    """AC-NFR0500-01: a missing check id is rejected."""
    feedback = ValidationFeedback(
        check_id="",
        artifact_path="some/path.md",
        field="some.field",
        expected="x",
        actual="y",
        fr_ids=("FR-1",),
        ac_ids=("AC-FR1-01",),
        contract_refs=(),
        prompt_identity=None,
        retryable=True,
        remediation="fix it",
    )
    with pytest.raises(FeedbackError) as exc:
        verify_actionable_feedback(feedback)
    assert exc.value.code == "FEEDBACK_MISSING_CHECK_ID"


def test_verify_actionable_feedback_rejects_missing_artifact_path() -> None:
    """AC-NFR0500-01: a missing artifact path is rejected."""
    feedback = ValidationFeedback(
        check_id="DESIGN.X",
        artifact_path="",
        field="",
        expected="x",
        actual="y",
        fr_ids=("FR-1",),
        ac_ids=("AC-FR1-01",),
        contract_refs=(),
        prompt_identity=None,
        retryable=True,
        remediation="fix it",
    )
    with pytest.raises(FeedbackError) as exc:
        verify_actionable_feedback(feedback)
    assert exc.value.code == "FEEDBACK_MISSING_ARTIFACT_PATH"


def test_feedback_to_dict_includes_all_required_fields() -> None:
    """AC-NFR0500-01: the dict includes check_id/path/field/expected/actual/fr/ac/contract/retryable."""
    feedback = build_feedback(
        check_id="DESIGN.SECRET",
        artifact_path="path/to/file.json",
        field="$.payload.secrets[0]",
        expected="no secret",
        actual="redacted fingerprint abcd1234",
        fr_ids=("FR-2600",),
        ac_ids=("AC-FR2600-01",),
        contract_refs=("pre-commit",),
        prompt_identity="louke.prompt-bundle.v0.14-002",
        retryable=True,
        remediation="remove detected secrets",
    )
    payload = feedback_to_dict(feedback)
    for key in (
        "check_id",
        "artifact_path",
        "field",
        "expected",
        "actual",
        "fr_ids",
        "ac_ids",
        "contract_refs",
        "prompt_identity",
        "retryable",
        "remediation",
    ):
        assert key in payload


def test_feedback_for_secret_does_not_echo_secret_value() -> None:
    """AC-NFR0500-01: secret feedback records only the redacted fingerprint."""
    feedback = build_feedback(
        check_id="DESIGN.SECRET",
        artifact_path="contracts/pre-commit.candidate.json",
        field="$.payload.commands[0].command",
        expected="no secret",
        actual="redacted fingerprint " + "a" * 12,
        fr_ids=("FR-2600",),
        ac_ids=("AC-FR2600-01",),
        contract_refs=("pre-commit",),
        prompt_identity=None,
        retryable=True,
        remediation="remove detected secrets; evidence records only path and redacted fingerprint",
    )
    payload = feedback_to_dict(feedback)
    # The actual must NOT contain raw secret patterns
    text = str(payload)
    for marker in ("AKIA", "BEGIN PRIVATE KEY", "password=secret"):
        assert marker not in text


def test_feedback_is_immutable() -> None:
    """AC-NFR0500-01: feedback record is an immutable value object."""
    feedback = build_feedback(
        check_id="X",
        artifact_path="p",
        field="f",
        expected="a",
        actual="b",
        fr_ids=(),
        ac_ids=(),
        contract_refs=(),
        prompt_identity=None,
        retryable=True,
        remediation="r",
    )
    with pytest.raises(Exception):
        feedback.check_id = "Y"  # type: ignore[misc]


def test_feedback_for_schema_failure_includes_json_pointer() -> None:
    """AC-NFR0500-01: schema failures include a JSON pointer in the field."""
    feedback = build_feedback(
        check_id="DESIGN.SCHEMA.ACTIVE",
        artifact_path="contracts/release-version.candidate.json",
        field="$.schema_ref.identity",
        expected="louke.machine-contract.release-version",
        actual="unknown",
        fr_ids=("FR-1900",),
        ac_ids=("AC-FR1900-01",),
        contract_refs=("release-version",),
        prompt_identity=None,
        retryable=False,
        remediation="use only active registry schema identities",
    )
    assert feedback.field == "$.schema_ref.identity"
    assert feedback.retryable is False


def test_feedback_for_trace_failure_localises_to_ac() -> None:
    """AC-NFR0500-01: trace failures localise to specific AC IDs."""
    feedback = build_feedback(
        check_id="DESIGN.TRACE.CLOSURE",
        artifact_path=".louke/project/specs/v0.14-002/acceptance.md",
        field="ac_ids",
        expected=34,
        actual=33,
        fr_ids=("FR-2600",),
        ac_ids=("AC-FR2700-01",),
        contract_refs=(),
        prompt_identity=None,
        retryable=True,
        remediation="restore missing AC closure entry AC-FR2700-01",
    )
    assert "AC-FR2700-01" in feedback.ac_ids
    assert feedback.expected == 34
