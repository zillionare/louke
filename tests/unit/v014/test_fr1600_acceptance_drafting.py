"""FR-1600: M-ACC 的 Acceptance 起草与 Review.

AC references:
- AC-FR1600-01: when Spec semantic and format results are both current PASS,
  M-ACC starts: the browser navigates to ``acceptance.md`` with Human
  readonly, and the Sage task input binds the current Story and Spec digests
  and continues the original Sage context.
- AC-FR1600-02: when the Acceptance draft is missing a section for a Valid
  FR/NFR and supplies no ``No Acceptance`` reason, the coverage check fails
  with ``ACCEPTANCE_COVERAGE_MISSING`` listing the requirement ID; M-LOCK-1
  is not visible and the run returns to Sage revision.
- AC-FR1600-03: when Human/Lex review and format all pass, Runtime completes
  M-ACC and the Project current page shows ``M-LOCK-1``; any subsequent
  Story or Spec digest change marks the Acceptance verdict stale and hides
  approve.
- AC-FR1600-04: when in Human/Lex review, Human edit/comment, Lex non-PASS,
  open discussions or format failure each produce their own bound
  revision/verdict/format error; the original Sage context receives the
  complete feedback and produces the next revision. Only Human ``no
  comment`` + Lex PASS + zero open threads + format PASS + matching
  Story/Spec digests lets the run leave M-ACC.
"""

from __future__ import annotations

import pytest

from louke.runtime.acceptance_drafting import (
    ACCEPTANCE_COVERAGE_MISSING,
    AcceptanceCoverageError,
    SageAcceptanceTaskInput,
    build_sage_acceptance_task_input,
    check_acceptance_coverage,
    decide_m_acc_advance,
    is_acceptance_verdict_stale_after_upstream_change,
)


def _spec_requirement_ids() -> tuple[str, ...]:
    return ("FR-0100", "FR-0200", "NFR-0100")


# AC-FR1600-01 ---------------------------------------------------------------
def test_sage_acceptance_task_input_binds_story_and_spec_digests() -> None:
    """AC-FR1600-01: the Sage Acceptance task input binds the current Story
    and Spec digests and continues the Sage context; Human is readonly and
    navigation goes to acceptance.md."""
    task_input = build_sage_acceptance_task_input(
        story_digest="sha256:" + "s" * 64,
        spec_digest="sha256:" + "p" * 64,
        spec_review_context_digest="sha256:" + "r" * 64,
        acceptance_template_path="templates/acceptance.md",
        acceptance_template_digest="sha256:" + "t" * 64,
        acceptance_revision=0,
        sage_session_id="sess_sage",
        run_id="run_1",
    )
    assert isinstance(task_input, SageAcceptanceTaskInput)
    assert task_input.story_digest == "sha256:" + "s" * 64
    assert task_input.spec_digest == "sha256:" + "p" * 64
    assert task_input.sage_session_id == "sess_sage"
    assert task_input.write_scope == ("acceptance.md",)
    assert task_input.navigation_document == "acceptance.md"
    assert task_input.human_edit_enabled is False


# AC-FR1600-02 ---------------------------------------------------------------
def test_missing_requirement_section_without_no_acceptance_reason_fails() -> None:
    """AC-FR1600-02: a missing Valid FR/NFR section without a ``No
    Acceptance`` reason fails coverage with
    ACCEPTANCE_COVERAGE_MISSING listing the requirement ID."""
    with pytest.raises(AcceptanceCoverageError) as exc_info:
        check_acceptance_coverage(
            spec_requirement_ids=_spec_requirement_ids(),
            acceptance_sections=(
                {"requirement_id": "FR-0100", "no_acceptance_reason": None},
                # FR-0200 missing entirely.
                {"requirement_id": "NFR-0100", "no_acceptance_reason": None},
            ),
        )
    assert exc_info.value.code == ACCEPTANCE_COVERAGE_MISSING
    assert "FR-0200" in exc_info.value.missing_ids


def test_missing_requirement_section_with_no_acceptance_reason_passes() -> None:
    """AC-FR1600-02: a missing Valid FR/NFR section with a ``No Acceptance``
    reason passes coverage."""
    result = check_acceptance_coverage(
        spec_requirement_ids=_spec_requirement_ids(),
        acceptance_sections=(
            {"requirement_id": "FR-0100", "no_acceptance_reason": None},
            {
                "requirement_id": "FR-0200",
                "no_acceptance_reason": "Covered by FR-0100 acceptance.",
            },
            {"requirement_id": "NFR-0100", "no_acceptance_reason": None},
        ),
    )
    assert result.ok is True
    assert result.missing_ids == ()


# AC-FR1600-03 ---------------------------------------------------------------
def test_m_acc_advance_requires_all_conditions() -> None:
    """AC-FR1600-04 + AC-FR1600-03: M-ACC advance requires Human
    no_comment, Lex PASS, zero open threads, format PASS and matching
    Story/Spec digests."""
    ok = decide_m_acc_advance(
        human_signal="no_comment",
        lex_verdict="PASS",
        open_threads=0,
        format_pass=True,
        story_digest_matches=True,
        spec_digest_matches=True,
    )
    assert ok.can_advance is True
    assert ok.target_phase == "M-LOCK-1"


@pytest.mark.parametrize(
    "human_signal, lex_verdict, open_threads, format_pass, story_match, spec_match",
    [
        ("comment", "PASS", 0, True, True, True),
        ("no_comment", "REJECT", 0, True, True, True),
        ("no_comment", "PASS", 1, True, True, True),
        ("no_comment", "PASS", 0, False, True, True),
        ("no_comment", "PASS", 0, True, False, True),
        ("no_comment", "PASS", 0, True, True, False),
    ],
)
def test_m_acc_advance_blocked_when_any_condition_fails(
    human_signal: str,
    lex_verdict: str,
    open_threads: int,
    format_pass: bool,
    story_match: bool,
    spec_match: bool,
) -> None:
    """AC-FR1600-04: any failing condition blocks M-ACC advance."""
    decision = decide_m_acc_advance(
        human_signal=human_signal,
        lex_verdict=lex_verdict,
        open_threads=open_threads,
        format_pass=format_pass,
        story_digest_matches=story_match,
        spec_digest_matches=spec_match,
    )
    assert decision.can_advance is False
    assert decision.target_phase == "M-ACC"
    assert decision.blocking_reasons  # non-empty


def test_acceptance_verdict_stale_after_upstream_digest_change() -> None:
    """AC-FR1600-03: when Story or Spec digest changes after Acceptance
    PASS, the Acceptance verdict is stale and approve must be hidden."""
    assert (
        is_acceptance_verdict_stale_after_upstream_change(
            story_digest_changed=True,
            spec_digest_changed=False,
        )
        is True
    )
    assert (
        is_acceptance_verdict_stale_after_upstream_change(
            story_digest_changed=False,
            spec_digest_changed=True,
        )
        is True
    )
    assert (
        is_acceptance_verdict_stale_after_upstream_change(
            story_digest_changed=False,
            spec_digest_changed=False,
        )
        is False
    )
