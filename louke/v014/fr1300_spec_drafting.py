"""FR-1300: M-SPEC 的 Sage 起草.

Implements the deterministic contract slice of FR-1300:

* :func:`build_sage_spec_task_input` builds the Sage author task input for
  M-SPEC. The input carries the bound Story digest, the Story review
  context digest, the canonical Spec template path and digest, the Spec
  revision, and the single allowed write path ``spec.md``. Human edit is
  disabled while Sage authors (AC-FR1300-01).

* :func:`decide_human_spec_save_during_sage_authoring` decides whether a
  Human save of Spec is allowed. While Sage has not returned, the save is
  rejected with ``WRITE_SCOPE_DENIED`` and Spec bytes are unchanged; once
  Sage returns and Runtime commits only ``spec.md``, Human editing opens
  (AC-FR1300-02).

* :func:`validate_spec_draft_structure` validates a Sage Spec draft. Empty
  content, duplicate requirement IDs, missing ``Source`` or ``metadata``
  and more than 30 valid FRs (NFRs not counted) all fail with a stable
  code naming the offending requirement/line or ``SPEC_SCOPE_TOO_LARGE``;
  the Lex task count stays 0 and the run stays in Sage revision
  (AC-FR1300-03).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Protocol


SPEC_SCOPE_TOO_LARGE = "SPEC_SCOPE_TOO_LARGE"
_VALID_FR_CAP = 30


@dataclass(frozen=True)
class SageSpecTaskInput:
    """Sage author task input for M-SPEC.

    Attributes:
        run_id: Opaque run identifier.
        story_digest: ``sha256:<hex>`` digest of the bound Story revision.
        story_review_context_digest: ``sha256:<hex>`` digest of the Story
            review context (verdicts + diffs).
        spec_template_path: Canonical Spec template path.
        spec_template_digest: ``sha256:<hex>`` digest of the template bytes.
        spec_revision: Spec artifact revision the Sage authors (0 for the
            first draft).
        write_scope: Always ``('spec.md',)``; Sage may not write Story or
            Acceptance during M-SPEC.
        navigation_document: Always ``spec.md``; the browser navigates here
            when M-SPEC starts.
        human_edit_enabled: Always ``False``; Human edit is disabled while
            Sage authors.
    """

    run_id: str
    story_digest: str
    story_review_context_digest: str
    spec_template_path: str
    spec_template_digest: str
    spec_revision: int
    write_scope: tuple[str, ...] = ("spec.md",)
    navigation_document: str = "spec.md"
    human_edit_enabled: bool = False


def build_sage_spec_task_input(
    *,
    story_digest: str,
    story_review_context_digest: str,
    spec_template_path: str,
    spec_template_digest: str,
    spec_revision: int,
    run_id: str,
) -> SageSpecTaskInput:
    """Build the Sage author task input for M-SPEC.

    Args:
        story_digest: ``sha256:<hex>`` digest of the bound Story revision.
        story_review_context_digest: ``sha256:<hex>`` digest of the Story
            review context (verdicts + diffs).
        spec_template_path: Canonical Spec template path.
        spec_template_digest: ``sha256:<hex>`` digest of the template bytes.
        spec_revision: Spec artifact revision the Sage authors (0 for the
            first draft).
        run_id: Opaque run identifier.

    Returns:
        A :class:`SageSpecTaskInput` with ``write_scope == ('spec.md',)``,
        ``navigation_document == 'spec.md'`` and ``human_edit_enabled is
        False`` (AC-FR1300-01).
    """
    return SageSpecTaskInput(
        run_id=run_id,
        story_digest=story_digest,
        story_review_context_digest=story_review_context_digest,
        spec_template_path=spec_template_path,
        spec_template_digest=spec_template_digest,
        spec_revision=spec_revision,
        write_scope=("spec.md",),
        navigation_document="spec.md",
        human_edit_enabled=False,
    )


@dataclass(frozen=True)
class SpecWriteBlocked:
    """Decision returned by :func:`decide_human_spec_save_during_sage_authoring`.

    Attributes:
        allowed: ``True`` when Human may save Spec; ``False`` otherwise.
        code: ``WRITE_SCOPE_DENIED`` when ``allowed is False``; ``None``
            otherwise.
        sage_has_returned: Whether Sage has returned a valid draft.
    """

    allowed: bool
    code: Optional[str]
    sage_has_returned: bool


def decide_human_spec_save_during_sage_authoring(
    *,
    sage_has_returned: bool,
) -> SpecWriteBlocked:
    """Decide whether a Human save of Spec is allowed during Sage authoring.

    Args:
        sage_has_returned: Whether Sage has returned a valid draft and
            Runtime has committed only ``spec.md``.

    Returns:
        A :class:`SpecWriteBlocked`. ``allowed is True`` only when
        ``sage_has_returned is True``. Otherwise ``code ==
        'WRITE_SCOPE_DENIED'`` and Spec bytes are unchanged (AC-FR1300-02).
    """
    if sage_has_returned:
        return SpecWriteBlocked(
            allowed=True,
            code=None,
            sage_has_returned=True,
        )
    return SpecWriteBlocked(
        allowed=False,
        code="WRITE_SCOPE_DENIED",
        sage_has_returned=False,
    )


class _RequirementBlock(Protocol):
    """Structural shape of a requirement block in a Spec draft."""

    id: str
    line: int
    source: str
    metadata: bool


@dataclass(frozen=True)
class SpecDraftValidationResult:
    """Result of a successful :func:`validate_spec_draft_structure`.

    Attributes:
        ok: Always ``True``; failures raise :class:`SpecStructureError`.
        valid_fr_count: Number of valid FR blocks (capped at 30).
        valid_nfr_count: Number of valid NFR blocks (not capped).
    """

    ok: bool
    valid_fr_count: int
    valid_nfr_count: int


class SpecStructureError(Exception):
    """Raised when a Spec draft fails structural validation.

    Attributes:
        code: ``VALIDATION_FAILED`` for content/ID/Source/metadata errors;
            :data:`SPEC_SCOPE_TOO_LARGE` when valid FR count > 30.
        message: Non-secret human-readable explanation.
        line: 1-based line number of the offending block when applicable;
            ``None`` otherwise.
        lex_task_count: Always ``0``; the run stays in Sage revision.
    """

    def __init__(
        self,
        *,
        code: str,
        message: str,
        line: Optional[int] = None,
    ) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.line = line
        self.lex_task_count = 0


def validate_spec_draft_structure(
    *,
    spec_md_bytes: bytes,
    requirement_blocks: Iterable[_RequirementBlock],
) -> SpecDraftValidationResult:
    """Validate the structure of a Sage Spec draft.

    Args:
        spec_md_bytes: The Spec draft bytes.
        requirement_blocks: Iterable of requirement block descriptors parsed
            from the draft. Each block has ``id``, ``line``, ``source`` and
            ``metadata``.

    Returns:
        A :class:`SpecDraftValidationResult` with the valid FR/NFR counts.

    Raises:
        SpecStructureError: When the content is empty, IDs are duplicate, a
            block is missing ``Source`` or ``metadata``, or the valid FR
            count exceeds 30. ``code`` is ``VALIDATION_FAILED`` for content/
            ID/Source/metadata errors and :data:`SPEC_SCOPE_TOO_LARGE` for
            the FR cap. ``lex_task_count`` is always 0 (AC-FR1300-03).
    """
    if not spec_md_bytes or not spec_md_bytes.strip():
        raise SpecStructureError(
            code="VALIDATION_FAILED",
            message="spec draft is empty",
        )
    seen_ids: dict[str, int] = {}
    fr_count = 0
    nfr_count = 0
    for block in requirement_blocks:
        block_id = block["id"] if isinstance(block, dict) else block.id
        line = block["line"] if isinstance(block, dict) else block.line
        source = block["source"] if isinstance(block, dict) else block.source
        metadata = block["metadata"] if isinstance(block, dict) else block.metadata
        if block_id in seen_ids:
            raise SpecStructureError(
                code="VALIDATION_FAILED",
                message=(
                    f"duplicate requirement id {block_id!r} at line {line} "
                    f"(first seen at line {seen_ids[block_id]})"
                ),
                line=line,
            )
        seen_ids[block_id] = line
        if not source:
            raise SpecStructureError(
                code="VALIDATION_FAILED",
                message=(
                    f"requirement {block_id!r} at line {line} is missing "
                    "the Source field"
                ),
                line=line,
            )
        if not metadata:
            raise SpecStructureError(
                code="VALIDATION_FAILED",
                message=(
                    f"requirement {block_id!r} at line {line} is missing "
                    "the Valid/Testable/Decided metadata table"
                ),
                line=line,
            )
        if block_id.startswith("FR-"):
            fr_count += 1
        elif block_id.startswith("NFR-"):
            nfr_count += 1
    if fr_count > _VALID_FR_CAP:
        raise SpecStructureError(
            code=SPEC_SCOPE_TOO_LARGE,
            message=(
                f"spec has {fr_count} valid FRs which exceeds the cap of "
                f"{_VALID_FR_CAP} (NFRs are not counted)"
            ),
        )
    return SpecDraftValidationResult(
        ok=True,
        valid_fr_count=fr_count,
        valid_nfr_count=nfr_count,
    )


class SpecDraftValidationError(Exception):
    """Backward-compatibility alias for :class:`SpecStructureError`."""
