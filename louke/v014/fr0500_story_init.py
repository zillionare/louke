"""FR-0500: 初始 ``story.md`` Revision 与页面跳转.

Implements the deterministic contract slice of FR-0500:

* :func:`initialize_story_revision` fills the canonical Story template by
  substituting the human's original input placeholder with the supplied
  story, preserving the rest of the template structure byte-for-byte. The
  resulting ``story.md`` bytes, file digest, input digest and revision
  evidence (actor, run id, commit SHA) are deterministic over the inputs.

* When ``existing_bytes`` are supplied and do not match the expected file
  digest, :class:`StoryInitConflict` is raised with code
  ``STORY_INITIALIZATION_CONFLICT`` and the existing bytes are preserved
  unchanged for the caller to surface (FR-0500 AC-02). No overwrite is
  performed.

* The :attr:`StoryInitResult.navigation` identity points to the canonical
  Story edit page for the current spec, run, ``M-STORY`` phase and revision
  (FR-0500 AC-03).

The module does not perform Git or filesystem IO; it produces the
deterministic bytes and evidence that the Driver/DOC/GIT adapters commit
and persist.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional


STORY_INITIALIZATION_CONFLICT = "STORY_INITIALIZATION_CONFLICT"


@dataclass(frozen=True)
class StoryTemplate:
    """Canonical Story template with an original-input placeholder.

    Attributes:
        body: Full template text including the placeholder.
        original_input_placeholder: The exact placeholder substring in
            ``body`` that is replaced with the human story.
    """

    body: str
    original_input_placeholder: str


@dataclass(frozen=True)
class StoryRevisionEvidence:
    """Evidence for an initial Story revision.

    Attributes:
        input_digest: ``sha256:<hex>`` of the human story bytes.
        file_digest: ``sha256:<hex>`` of the resulting ``story.md`` bytes.
        actor: Non-secret actor identity (e.g. ``human:alice``).
        run_id: Opaque run identifier.
        commit_sha: Git commit SHA recorded for the revision.
    """

    input_digest: str
    file_digest: str
    actor: str
    run_id: str
    commit_sha: str


@dataclass(frozen=True)
class StoryNavigation:
    """Navigation identity for the Story edit page.

    Attributes:
        run_id: Opaque run identifier.
        spec_id: Canonical spec identifier.
        phase: Always ``M-STORY`` for the initial Story revision.
        document: Always ``story``.
        revision_digest: ``sha256:<hex>`` of the ``story.md`` bytes.
        commit_sha: Git commit SHA recorded for the revision.
    """

    run_id: str
    spec_id: str
    phase: str
    document: str
    revision_digest: str
    commit_sha: str


@dataclass(frozen=True)
class StoryInitResult:
    """Result of :func:`initialize_story_revision`.

    Attributes:
        story_md_bytes: Canonical UTF-8 ``story.md`` bytes.
        evidence: :class:`StoryRevisionEvidence` for the initial revision.
        navigation: :class:`StoryNavigation` pointing to the Story edit page.
    """

    story_md_bytes: bytes
    evidence: StoryRevisionEvidence
    navigation: StoryNavigation


class StoryInitConflict(Exception):
    """Raised when existing ``story.md`` bytes do not match the expected digest.

    Attributes:
        code: Always :data:`STORY_INITIALIZATION_CONFLICT`.
        existing_bytes: The existing on-disk bytes, preserved unchanged.
        expected_file_digest: The ``sha256:<hex>`` digest that the new
            initialisation would produce.
    """

    def __init__(
        self,
        *,
        existing_bytes: bytes,
        expected_file_digest: str,
    ) -> None:
        super().__init__(
            f"{STORY_INITIALIZATION_CONFLICT}: existing story.md bytes do not match expected digest {expected_file_digest}"
        )
        self.code = STORY_INITIALIZATION_CONFLICT
        self.existing_bytes = existing_bytes
        self.expected_file_digest = expected_file_digest


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def initialize_story_revision(
    *,
    template: StoryTemplate,
    human_story: str,
    actor: str,
    run_id: str,
    commit_sha: str,
    spec_id: str = "v0.14-001-workflow-reflow-spec",
    existing_bytes: Optional[bytes] = None,
) -> StoryInitResult:
    """Produce the deterministic initial ``story.md`` revision.

    Args:
        template: Canonical :class:`StoryTemplate` with an original-input
            placeholder.
        human_story: Non-empty human one-sentence release设想; substituted
            into ``template.original_input_placeholder``.
        actor: Non-secret actor identity (e.g. ``human:alice``).
        run_id: Opaque run identifier the revision belongs to.
        commit_sha: Git commit SHA recorded for the revision.
        spec_id: Canonical spec identifier; defaults to the v0.14-001 spec.
        existing_bytes: Optional on-disk bytes when retrying. When supplied
            and not byte-equal to the expected new bytes, a
            :class:`StoryInitConflict` is raised and the existing bytes are
            preserved unchanged.

    Returns:
        A :class:`StoryInitResult` containing the canonical ``story.md``
        bytes, revision evidence and navigation identity.

    Raises:
        StoryInitConflict: When ``existing_bytes`` is supplied and does not
            match the expected file digest. The existing bytes are preserved
            unchanged.

    Side effects:
        None. The function is pure; callers persist bytes, evidence and
        navigation through their own adapters.
    """
    if template.original_input_placeholder not in template.body:
        raise ValueError(
            "template.original_input_placeholder must appear in template.body"
        )
    filled_body = template.body.replace(
        template.original_input_placeholder, human_story
    )
    story_md_bytes = filled_body.encode("utf-8")
    file_digest = f"sha256:{_sha256_hex(story_md_bytes)}"
    input_digest = f"sha256:{_sha256_hex(human_story.encode('utf-8'))}"

    if existing_bytes is not None and existing_bytes != story_md_bytes:
        raise StoryInitConflict(
            existing_bytes=existing_bytes,
            expected_file_digest=file_digest,
        )

    evidence = StoryRevisionEvidence(
        input_digest=input_digest,
        file_digest=file_digest,
        actor=actor,
        run_id=run_id,
        commit_sha=commit_sha,
    )
    navigation = StoryNavigation(
        run_id=run_id,
        spec_id=spec_id,
        phase="M-STORY",
        document="story",
        revision_digest=file_digest,
        commit_sha=commit_sha,
    )
    return StoryInitResult(
        story_md_bytes=story_md_bytes,
        evidence=evidence,
        navigation=navigation,
    )
