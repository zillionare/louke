"""FR-1400: M-SPEC Human/Lex 语义 Review 与格式验收.

AC references:
- AC-FR1400-01: when a Spec revision R is committed, Human and Lex reviews
  both bind to R; without a write lease Lex cannot change the document or
  discussions; once leased, Lex's threads are queryable from the review
  page and the persistent discussion outlet.
- AC-FR1400-02: when Human modifies R to R2 and submits a comment, Lex's
  final-round input is R2 with the Human diff; Lex's old R verdict is
  stale and cannot combine with Human's R2 verdict to pass.
- AC-FR1400-03: Human ``comment``, Lex non-PASS or open/reopen threads end
  the round: the original Sage session receives the complete feedback and
  produces a new revision; round number increments. Only Human ``no
  comment`` + Lex PASS + zero open/reopen + digest match enters format
  check.
- AC-FR1400-04: when semantic review passes but canonical format check
  fails, the page shows the specific file/line/rule; the current step
  stays M-SPEC and the M-ACC task count is 0. Format pass is required to
  enter M-ACC.
"""

from __future__ import annotations


from louke.v014.fr1400_spec_review import (
    LexReviewInput,
    MSpecFormatCheckResult,
    build_lex_review_input,
    decide_m_spec_semantic_gate,
    decide_m_spec_format_gate,
    lex_can_write_without_lease,
    start_first_spec_review_round,
    verdict_is_stale,
)


def _commit(c: str) -> tuple[str, str]:
    return f"c_{c}" * 20, f"sha256:{c * 64}"


# AC-FR1400-01 ---------------------------------------------------------------
def test_first_spec_review_round_binds_human_and_lex_to_same_revision() -> None:
    """AC-FR1400-01: both Human and Lex reviews bind to the same commit R
    and digest D."""
    commit_sha, digest = _commit("a")
    round_ = start_first_spec_review_round(
        spec_commit_sha=commit_sha,
        spec_digest=digest,
        sage_session_id="sess_sage",
        lex_session_id="sess_lex",
    )
    assert round_.round_number == 1
    assert round_.spec_commit_sha == commit_sha
    assert round_.spec_digest == digest
    assert round_.sage_session_id == "sess_sage"
    assert round_.lex_session_id == "sess_lex"
    assert round_.lex_session_id != round_.sage_session_id


def test_lex_cannot_write_without_lease() -> None:
    """AC-FR1400-01: without a write lease, Lex cannot change the document
    or discussions."""
    decision = lex_can_write_without_lease(has_lease=False)
    assert decision.can_write is False
    assert decision.code == "WRITE_SCOPE_DENIED"


def test_lex_can_write_with_lease() -> None:
    """AC-FR1400-01: with a write lease, Lex can leave discussions
    queryable."""
    decision = lex_can_write_without_lease(has_lease=True)
    assert decision.can_write is True
    assert decision.threads_queryable is True


# AC-FR1400-02 ---------------------------------------------------------------
def test_lex_input_binds_to_r2_and_includes_human_diff() -> None:
    """AC-FR1400-02: when Human modifies R to R2, Lex's input binds to R2
    and includes the Human diff."""
    commit_r1, digest_r1 = _commit("a")
    round_ = start_first_spec_review_round(
        spec_commit_sha=commit_r1,
        spec_digest=digest_r1,
        sage_session_id="sess_sage",
        lex_session_id="sess_lex",
    )
    commit_r2, digest_r2 = _commit("b")
    human_diff = b"diff content"
    lex_input = build_lex_review_input(
        round_=round_,
        human_commit_sha=commit_r2,
        human_digest=digest_r2,
        human_diff=human_diff,
    )
    assert isinstance(lex_input, LexReviewInput)
    assert lex_input.bound_digest == digest_r2
    assert lex_input.human_diff == human_diff
    assert lex_input.human_commit_sha == commit_r2


def test_lex_old_r_verdict_is_stale_and_cannot_combine_with_human_r2() -> None:
    """AC-FR1400-02: Lex's old verdict on R is stale; it cannot combine
    with Human's R2 verdict to pass."""
    commit_r1, digest_r1 = _commit("a")
    start_first_spec_review_round(
        spec_commit_sha=commit_r1,
        spec_digest=digest_r1,
        sage_session_id="sess_sage",
        lex_session_id="sess_lex",
    )
    commit_r2, digest_r2 = _commit("b")
    round_2 = start_first_spec_review_round(
        spec_commit_sha=commit_r2,
        spec_digest=digest_r2,
        sage_session_id="sess_sage",
        lex_session_id="sess_lex",
    )
    old_lex_verdict_on_r1 = type("V", (), {"digest": digest_r1, "verdict": "PASS"})()
    assert verdict_is_stale(old_lex_verdict_on_r1, round_2) is True


# AC-FR1400-03 ---------------------------------------------------------------
def test_semantic_gate_blocks_when_any_condition_fails() -> None:
    """AC-FR1400-03: Human comment / Lex non-PASS / open threads / digest
    mismatch each block the semantic gate."""
    commit_r, digest_r = _commit("a")
    round_ = start_first_spec_review_round(
        spec_commit_sha=commit_r,
        spec_digest=digest_r,
        sage_session_id="sess_sage",
        lex_session_id="sess_lex",
    )
    ok = decide_m_spec_semantic_gate(
        round_=round_,
        human_signal="no_comment",
        lex_verdict="PASS",
        open_threads=0,
        digest_matches=True,
    )
    assert ok.can_enter_format_check is True

    blocked = decide_m_spec_semantic_gate(
        round_=round_,
        human_signal="comment",
        lex_verdict="PASS",
        open_threads=0,
        digest_matches=True,
    )
    assert blocked.can_enter_format_check is False
    assert blocked.requires_rework is True
    assert blocked.round_increment == 1


def test_semantic_gate_pass_enters_format_check() -> None:
    """AC-FR1400-03: only Human no_comment + Lex PASS + zero open threads +
    digest match enters format check."""
    commit_r, digest_r = _commit("a")
    round_ = start_first_spec_review_round(
        spec_commit_sha=commit_r,
        spec_digest=digest_r,
        sage_session_id="sess_sage",
        lex_session_id="sess_lex",
    )
    decision = decide_m_spec_semantic_gate(
        round_=round_,
        human_signal="no_comment",
        lex_verdict="PASS",
        open_threads=0,
        digest_matches=True,
    )
    assert decision.can_enter_format_check is True
    assert decision.next_action == "format_check"


# AC-FR1400-04 ---------------------------------------------------------------
def test_format_check_failure_shows_file_line_rule_and_blocks_m_acc() -> None:
    """AC-FR1400-04: a format failure shows specific file/line/rule; the
    current step stays M-SPEC and the M-ACC task count is 0."""
    result = MSpecFormatCheckResult(
        passed=False,
        errors=(
            {
                "file": "spec.md",
                "line": 42,
                "rule": "requirement_missing_metadata",
                "message": "FR-0100 is missing the Valid/Testable/Decided table",
            },
        ),
    )
    decision = decide_m_spec_format_gate(result)
    assert decision.can_enter_m_acc is False
    assert decision.current_step == "M-SPEC"
    assert decision.m_acc_task_count == 0
    assert decision.format_errors == result.errors


def test_format_check_pass_enters_m_acc() -> None:
    """AC-FR1400-04: format pass enters M-ACC."""
    result = MSpecFormatCheckResult(passed=True, errors=())
    decision = decide_m_spec_format_gate(result)
    assert decision.can_enter_m_acc is True
    assert decision.current_step == "M-ACC"
    assert decision.m_acc_task_count >= 1
    assert decision.format_errors == ()
