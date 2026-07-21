"""FR-1600: M-ACC 的 Acceptance 起草与 Review.

Implements the deterministic contract slice of FR-1600:

* :func:`build_sage_acceptance_task_input` builds the Sage author task input
  for M-ACC. The input binds the current Story and Spec digests, continues
  the original Sage OpenCode session, and exposes the single allowed write
  path ``acceptance.md``; Human edit is disabled while Sage authors
  (AC-FR1600-01).

* :func:`check_acceptance_coverage` validates that every Valid Spec
  requirement has either an Acceptance section or an explicit ``No
  Acceptance`` reason. Missing sections without a reason raise
  :class:`AcceptanceCoverageError` with code ``ACCEPTANCE_COVERAGE_MISSING``
  listing the missing requirement IDs (AC-FR1600-02).

* :func:`decide_m_acc_advance` decides whether the run may leave M-ACC for
  M-LOCK-1. All of the following must hold: Human ``no_comment``, Lex
  ``PASS``, zero open/reopen threads, format PASS, Story digest match, Spec
  digest match. Any failing condition blocks advance with a non-empty list
  of blocking reasons (AC-FR1600-03, AC-FR1600-04).

* :func:`is_acceptance_verdict_stale_after_upstream_change` returns ``True``
  when Story or Spec digest has changed after the Acceptance PASS; the
  Acceptance verdict is stale and approve must be hidden (AC-FR1600-03).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol


ACCEPTANCE_COVERAGE_MISSING = "ACCEPTANCE_COVERAGE_MISSING"


@dataclass(frozen=True)
class SageAcceptanceTaskInput:
    """Sage author task input for M-ACC.

    Attributes:
        run_id: Opaque run identifier.
        story_digest: ``sha256:<hex>`` digest of the bound Story revision.
        spec_digest: ``sha256:<hex>`` digest of the bound Spec revision.
        spec_review_context_digest: ``sha256:<hex>`` digest of the Spec
            review context (verdicts + diffs).
        acceptance_template_path: Canonical Acceptance template path.
        acceptance_template_digest: ``sha256:<hex>`` digest of the template
            bytes.
        acceptance_revision: Acceptance artifact revision the Sage authors
            (0 for the first draft).
        sage_session_id: Sage OpenCode session id (continues from M-SPEC).
        write_scope: Always ``('acceptance.md',)``.
        navigation_document: Always ``acceptance.md``.
        human_edit_enabled: Always ``False`` while Sage authors.
    """

    run_id: str
    story_digest: str
    spec_digest: str
    spec_review_context_digest: str
    acceptance_template_path: str
    acceptance_template_digest: str
    acceptance_revision: int
    sage_session_id: str
    write_scope: tuple[str, ...] = ("acceptance.md",)
    navigation_document: str = "acceptance.md"
    human_edit_enabled: bool = False


def build_sage_acceptance_task_input(
    *,
    story_digest: str,
    spec_digest: str,
    spec_review_context_digest: str,
    acceptance_template_path: str,
    acceptance_template_digest: str,
    acceptance_revision: int,
    sage_session_id: str,
    run_id: str,
) -> SageAcceptanceTaskInput:
    """Build the Sage author task input for M-ACC.

    Args:
        story_digest: ``sha256:<hex>`` digest of the bound Story revision.
        spec_digest: ``sha256:<hex>`` digest of the bound Spec revision.
        spec_review_context_digest: ``sha256:<hex>`` digest of the Spec
            review context.
        acceptance_template_path: Canonical Acceptance template path.
        acceptance_template_digest: ``sha256:<hex>`` digest of the template
            bytes.
        acceptance_revision: Acceptance artifact revision the Sage authors.
        sage_session_id: Sage OpenCode session id (continues from M-SPEC).
        run_id: Opaque run identifier.

    Returns:
        A :class:`SageAcceptanceTaskInput` bound to Story/Spec digests with
        ``write_scope == ('acceptance.md',)`` and ``human_edit_enabled is
        False`` (AC-FR1600-01).
    """
    return SageAcceptanceTaskInput(
        run_id=run_id,
        story_digest=story_digest,
        spec_digest=spec_digest,
        spec_review_context_digest=spec_review_context_digest,
        acceptance_template_path=acceptance_template_path,
        acceptance_template_digest=acceptance_template_digest,
        acceptance_revision=acceptance_revision,
        sage_session_id=sage_session_id,
        write_scope=("acceptance.md",),
        navigation_document="acceptance.md",
        human_edit_enabled=False,
    )


class _AcceptanceSection(Protocol):
    """Structural shape of an Acceptance section descriptor."""

    requirement_id: str
    no_acceptance_reason: str | None


@dataclass(frozen=True)
class AcceptanceCoverageResult:
    """Result of a successful :func:`check_acceptance_coverage`.

    Attributes:
        ok: Always ``True``; failures raise :class:`AcceptanceCoverageError`.
        missing_ids: Always ``()`` on success.
    """

    ok: bool
    missing_ids: tuple[str, ...] = ()


class AcceptanceCoverageError(Exception):
    """Raised when Acceptance coverage validation fails.

    Attributes:
        code: Always :data:`ACCEPTANCE_COVERAGE_MISSING`.
        missing_ids: Tuple of requirement IDs missing both a section and a
            ``No Acceptance`` reason.
    """

    def __init__(self, *, missing_ids: tuple[str, ...]) -> None:
        super().__init__(
            f"{ACCEPTANCE_COVERAGE_MISSING}: requirement IDs missing both a "
            f"section and a No Acceptance reason: {list(missing_ids)}"
        )
        self.code = ACCEPTANCE_COVERAGE_MISSING
        self.missing_ids = missing_ids


def check_acceptance_coverage(
    *,
    spec_requirement_ids: Iterable[str],
    acceptance_sections: Iterable[_AcceptanceSection],
) -> AcceptanceCoverageResult:
    """Validate Acceptance coverage against the Spec requirement list.

    Args:
        spec_requirement_ids: Iterable of Valid Spec requirement IDs.
        acceptance_sections: Iterable of Acceptance section descriptors.
            Each section has ``requirement_id`` and ``no_acceptance_reason``
            (``None`` when an actual Acceptance section is present).

    Returns:
        An :class:`AcceptanceCoverageResult` with ``ok is True`` when every
        Spec requirement has either a section or a ``No Acceptance``
        reason.

    Raises:
        AcceptanceCoverageError: When one or more Spec requirements are
            missing both a section and a ``No Acceptance`` reason. ``code``
            is :data:`ACCEPTANCE_COVERAGE_MISSING` and ``missing_ids`` lists
            the offenders (AC-FR1600-02).
    """
    sections_by_id: dict[str, str | None] = {}
    for section in acceptance_sections:
        rid = (
            section["requirement_id"]
            if isinstance(section, dict)
            else section.requirement_id
        )
        reason = (
            section["no_acceptance_reason"]
            if isinstance(section, dict)
            else section.no_acceptance_reason
        )
        sections_by_id[rid] = reason
    missing: list[str] = []
    for rid in spec_requirement_ids:
        if rid not in sections_by_id:
            missing.append(rid)
            continue
        reason = sections_by_id[rid]
        if reason is None:
            # An entry with no_acceptance_reason == None means a section was
            # declared but the actual content body is empty/missing. Treat
            # the entry as covering the requirement only when a non-None
            # reason is supplied. For our contract, a section entry with
            # reason=None means the section body is present (i.e. covered).
            # To detect a missing section, we look for absence of the id in
            # sections_by_id. So this branch is a no-op: the requirement is
            # covered by an actual section.
            pass
    if missing:
        raise AcceptanceCoverageError(missing_ids=tuple(missing))
    return AcceptanceCoverageResult(ok=True, missing_ids=())


@dataclass(frozen=True)
class MaccAdvanceDecision:
    """Decision returned by :func:`decide_m_acc_advance`.

    Attributes:
        can_advance: ``True`` only when all conditions hold.
        target_phase: ``M-LOCK-1`` when ``can_advance``; ``M-ACC`` otherwise.
        blocking_reasons: Non-empty when ``not can_advance``; empty otherwise.
    """

    can_advance: bool
    target_phase: str
    blocking_reasons: tuple[str, ...] = ()


def decide_m_acc_advance(
    *,
    human_signal: str,
    lex_verdict: str,
    open_threads: int,
    format_pass: bool,
    story_digest_matches: bool,
    spec_digest_matches: bool,
) -> MaccAdvanceDecision:
    """Decide whether the run may leave M-ACC for M-LOCK-1.

    Args:
        human_signal: ``comment`` or ``no_comment``.
        lex_verdict: ``PASS`` or ``REJECT``.
        open_threads: Number of OPEN/REOPEN discussions on the current
            Acceptance revision.
        format_pass: Whether the Acceptance format check passed.
        story_digest_matches: Whether the Story digest still matches the one
            the Acceptance was bound to.
        spec_digest_matches: Whether the Spec digest still matches the one
            the Acceptance was bound to.

    Returns:
        An :class:`MaccAdvanceDecision`. ``can_advance is True`` only when
        all of the following hold: ``human_signal == 'no_comment'``,
        ``lex_verdict == 'PASS'``, ``open_threads == 0``,
        ``format_pass is True``, ``story_digest_matches is True``,
        ``spec_digest_matches is True`` (AC-FR1600-03, AC-FR1600-04).
    """
    blockers: list[str] = []
    if human_signal != "no_comment":
        blockers.append("human_signal must be 'no_comment'")
    if lex_verdict != "PASS":
        blockers.append("lex_verdict must be 'PASS'")
    if open_threads > 0:
        blockers.append(f"open_threads must be 0 (got {open_threads})")
    if not format_pass:
        blockers.append("format check must pass")
    if not story_digest_matches:
        blockers.append("Story digest must match the Acceptance binding")
    if not spec_digest_matches:
        blockers.append("Spec digest must match the Acceptance binding")
    if blockers:
        return MaccAdvanceDecision(
            can_advance=False,
            target_phase="M-ACC",
            blocking_reasons=tuple(blockers),
        )
    return MaccAdvanceDecision(
        can_advance=True,
        target_phase="M-LOCK-1",
        blocking_reasons=(),
    )


@dataclass(frozen=True)
class AcceptancePassDecision:
    """Tagged result of an Acceptance PASS (placeholder for future
    evidence). Currently unused by tests but reserved for AC-FR1600-03
    advance evidence."""


def is_acceptance_verdict_stale_after_upstream_change(
    *,
    story_digest_changed: bool,
    spec_digest_changed: bool,
) -> bool:
    """Return ``True`` when the Acceptance verdict must be marked stale.

    Args:
        story_digest_changed: Whether the Story digest changed after the
            Acceptance PASS.
        spec_digest_changed: Whether the Spec digest changed after the
            Acceptance PASS.

    Returns:
        ``True`` when either digest changed; ``False`` otherwise. When
        ``True``, the M-LOCK-1 approve action must be hidden
        (AC-FR1600-03).
    """
    return story_digest_changed or spec_digest_changed
