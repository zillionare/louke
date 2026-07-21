"""FR-1300: M-SPEC 的 Sage 起草.

AC references:
- AC-FR1300-01: when both Story reviews PASS on digest D, M-SPEC authoring
  starts: navigation goes to ``spec.md`` with edit controls disabled, and
  the Sage task input contains D, review context, template, revision and
  the single allowed write path ``spec.md``.
- AC-FR1300-02: while Sage has not returned, any Human Web/API save of Spec
  is rejected and Spec bytes are unchanged; once Sage returns a valid draft,
  Runtime commits only ``spec.md`` and opens Human editing.
- AC-FR1300-03: a draft with duplicate IDs, missing Source/metadata, empty
  content or 31 valid FRs (NFRs not counted) fails structural validation
  with an error naming the requirement/line or ``SPEC_SCOPE_TOO_LARGE``;
  Lex task count stays 0 and the run stays in Sage revision.
"""

from __future__ import annotations

import pytest

from louke.v014.fr1300_spec_drafting import (
    SPEC_SCOPE_TOO_LARGE,
    SageSpecTaskInput,
    SpecStructureError,
    SpecWriteBlocked,
    build_sage_spec_task_input,
    decide_human_spec_save_during_sage_authoring,
    validate_spec_draft_structure,
)


# AC-FR1300-01 ---------------------------------------------------------------
def test_sage_spec_task_input_carries_story_digest_and_single_write_path() -> None:
    """AC-FR1300-01: the Sage task input for M-SPEC contains the Story
    digest, review context, template path/revision and the single allowed
    write path ``spec.md``."""
    task_input = build_sage_spec_task_input(
        story_digest="sha256:" + "a" * 64,
        story_review_context_digest="sha256:" + "r" * 64,
        spec_template_path="templates/spec.md",
        spec_template_digest="sha256:" + "t" * 64,
        spec_revision=0,
        run_id="run_1",
    )
    assert isinstance(task_input, SageSpecTaskInput)
    assert task_input.story_digest == "sha256:" + "a" * 64
    assert task_input.story_review_context_digest == "sha256:" + "r" * 64
    assert task_input.spec_template_path == "templates/spec.md"
    assert task_input.spec_template_digest == "sha256:" + "t" * 64
    assert task_input.spec_revision == 0
    # AC-FR1300-01: only spec.md is writable.
    assert task_input.write_scope == ("spec.md",)
    # Navigation goes to spec.md.
    assert task_input.navigation_document == "spec.md"
    # Edit controls disabled while Sage authors.
    assert task_input.human_edit_enabled is False


# AC-FR1300-02 ---------------------------------------------------------------
def test_human_save_during_sage_authoring_is_rejected() -> None:
    """AC-FR1300-02: while Sage has not returned, a Human save of Spec is
    rejected with WRITE_SCOPE_DENIED and Spec bytes are unchanged."""
    decision = decide_human_spec_save_during_sage_authoring(
        sage_has_returned=False,
    )
    assert isinstance(decision, SpecWriteBlocked)
    assert decision.allowed is False
    assert decision.code == "WRITE_SCOPE_DENIED"
    assert decision.sage_has_returned is False


def test_human_save_allowed_after_sage_returns_valid_draft() -> None:
    """AC-FR1300-02: once Sage returns a valid draft and Runtime commits
    only spec.md, Human editing is opened."""
    decision = decide_human_spec_save_during_sage_authoring(
        sage_has_returned=True,
    )
    assert decision.allowed is True
    assert decision.sage_has_returned is True


# AC-FR1300-03 ---------------------------------------------------------------
def test_spec_draft_empty_content_rejected() -> None:
    """AC-FR1300-03: empty Spec content fails structural validation."""
    with pytest.raises(SpecStructureError) as exc_info:
        validate_spec_draft_structure(
            spec_md_bytes=b"",
            requirement_blocks=(),
        )
    assert exc_info.value.code == "VALIDATION_FAILED"
    assert "empty" in exc_info.value.message.lower()


def test_spec_draft_duplicate_requirement_ids_rejected() -> None:
    """AC-FR1300-03: duplicate requirement IDs fail structural validation and
    name the offending ID."""
    with pytest.raises(SpecStructureError) as exc_info:
        validate_spec_draft_structure(
            spec_md_bytes=b"# Spec\n\n### FR-0100\nx\n\n### FR-0100\ny\n",
            requirement_blocks=(
                {"id": "FR-0100", "line": 3, "source": "BS-01", "metadata": True},
                {"id": "FR-0100", "line": 5, "source": "BS-01", "metadata": True},
            ),
        )
    assert exc_info.value.code == "VALIDATION_FAILED"
    assert "FR-0100" in exc_info.value.message
    assert exc_info.value.line == 5


def test_spec_draft_missing_source_rejected() -> None:
    """AC-FR1300-03: a requirement block missing the Source field fails
    structural validation and names the offending ID/line."""
    with pytest.raises(SpecStructureError) as exc_info:
        validate_spec_draft_structure(
            spec_md_bytes=b"# Spec\n\n### FR-0100\nx\n",
            requirement_blocks=(
                {"id": "FR-0100", "line": 3, "source": "", "metadata": True},
            ),
        )
    assert exc_info.value.code == "VALIDATION_FAILED"
    assert "FR-0100" in exc_info.value.message
    assert exc_info.value.line == 3


def test_spec_draft_missing_metadata_rejected() -> None:
    """AC-FR1300-03: a requirement block missing the metadata table fails
    structural validation and names the offending ID/line."""
    with pytest.raises(SpecStructureError) as exc_info:
        validate_spec_draft_structure(
            spec_md_bytes=b"# Spec\n\n### FR-0100\nx\n",
            requirement_blocks=(
                {"id": "FR-0100", "line": 3, "source": "BS-01", "metadata": False},
            ),
        )
    assert exc_info.value.code == "VALIDATION_FAILED"
    assert "metadata" in exc_info.value.message.lower()


def test_spec_draft_with_31_valid_frs_exceeds_scope() -> None:
    """AC-FR1300-03: 31 valid FRs (NFRs not counted) exceed the 30-FR cap and
    return SPEC_SCOPE_TOO_LARGE; Lex task count stays 0."""
    blocks = tuple(
        {
            "id": f"FR-{i:04d}",
            "line": 3 + i,
            "source": "BS-01",
            "metadata": True,
        }
        for i in range(1, 32)
    )
    with pytest.raises(SpecStructureError) as exc_info:
        validate_spec_draft_structure(
            spec_md_bytes=b"# Spec\n" + b"\n### FR-XXXX\nx\n" * 31,
            requirement_blocks=blocks,
        )
    assert exc_info.value.code == SPEC_SCOPE_TOO_LARGE
    assert "31" in exc_info.value.message
    # Lex task count stays 0; the run stays in Sage revision.
    assert exc_info.value.lex_task_count == 0


def test_spec_draft_with_30_frs_and_3_nfrs_passes() -> None:
    """AC-FR1300-03: 30 FRs + 3 NFRs is within scope (NFRs not counted) and
    passes structural validation."""
    blocks = tuple(
        {"id": f"FR-{i:04d}", "line": 3 + i, "source": "BS-01", "metadata": True}
        for i in range(1, 31)
    ) + tuple(
        {"id": f"NFR-{i:04d}", "line": 100 + i, "source": "BS-01", "metadata": True}
        for i in range(1, 4)
    )
    body = b"# Spec\n" + b"\n### FR-XXXX\nx\n" * 30 + b"\n### NFR-XXXX\ny\n" * 3
    result = validate_spec_draft_structure(
        spec_md_bytes=body,
        requirement_blocks=blocks,
    )
    assert result.ok is True
    assert result.valid_fr_count == 30
    assert result.valid_nfr_count == 3
