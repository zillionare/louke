"""FR-0500: 初始 ``story.md`` Revision 与页面跳转.

AC references:
- AC-FR0500-01: initial Story creation produces a ``story.md`` whose original
  input section contains the human's story ``S``, with the rest of the
  canonical template structure preserved. Revision evidence contains the
  input digest, file digest, actor and commit SHA.
- AC-FR0500-02: retrying the same initialisation identity with a matching
  digest reuses the same file digest and commit SHA and adds zero commits.
  When the on-disk bytes do not match the expected digest, the response is
  ``STORY_INITIALIZATION_CONFLICT`` and the existing bytes are unchanged.
- AC-FR0500-03: after a successful initial Story commit, the navigation
  identity points to the current spec's Story edit page and shows the same
  run ID, ``M-STORY`` phase and revision identity.
"""

from __future__ import annotations

import hashlib

import pytest

from louke.runtime.story_init import (
    STORY_INITIALIZATION_CONFLICT,
    StoryInitConflict,
    StoryInitResult,
    StoryTemplate,
    initialize_story_revision,
)


def _template() -> StoryTemplate:
    return StoryTemplate(
        body=(
            "# Story\n\n"
            "## 0. 原始输入\n\n"
            "> {{LOUKE_HUMAN_STORY_INPUT}}\n\n"
            "## 1. 用户画像\n\n"
            "(to be filled by Scribe)\n"
        ),
        original_input_placeholder="{{LOUKE_HUMAN_STORY_INPUT}}",
    )


# AC-FR0500-01 ---------------------------------------------------------------
def test_initialize_story_fills_original_input_and_preserves_template_structure() -> (
    None
):
    """AC-FR0500-01: ``story.md`` original input section contains the human
    story; the rest of the template structure is preserved byte-for-byte."""
    template = _template()
    human_story = "让用户能在 Web 工作台完成 release 需求定义。"
    result = initialize_story_revision(
        template=template,
        human_story=human_story,
        actor="human:alice",
        run_id="run_abc",
        commit_sha="c" * 40,
    )
    assert isinstance(result, StoryInitResult)
    assert human_story in result.story_md_bytes.decode("utf-8")
    # The placeholder has been replaced.
    assert (
        template.original_input_placeholder.encode("utf-8") not in result.story_md_bytes
    )
    # Other sections preserved.
    assert b"## 1. " in result.story_md_bytes
    assert b"(to be filled by Scribe)" in result.story_md_bytes


def test_initialize_story_revision_evidence_records_input_file_actor_commit() -> None:
    """AC-FR0500-01: revision evidence contains input digest, file digest,
    actor and commit SHA."""
    template = _template()
    human_story = "Add offline cache for project list."
    result = initialize_story_revision(
        template=template,
        human_story=human_story,
        actor="human:alice",
        run_id="run_abc",
        commit_sha="c" * 40,
    )
    expected_input_digest = (
        f"sha256:{hashlib.sha256(human_story.encode('utf-8')).hexdigest()}"
    )
    expected_file_digest = f"sha256:{hashlib.sha256(result.story_md_bytes).hexdigest()}"
    assert result.evidence.input_digest == expected_input_digest
    assert result.evidence.file_digest == expected_file_digest
    assert result.evidence.actor == "human:alice"
    assert result.evidence.commit_sha == "c" * 40
    assert result.evidence.run_id == "run_abc"


# AC-FR0500-02 ---------------------------------------------------------------
def test_initialize_story_is_deterministic_for_same_inputs() -> None:
    """AC-FR0500-02: identical inputs produce identical file bytes, file
    digest and revision evidence, supporting idempotent retry with zero new
    commits."""
    template = _template()
    args = dict(
        template=template,
        human_story="Same story.",
        actor="human:alice",
        run_id="run_abc",
        commit_sha="c" * 40,
    )
    first = initialize_story_revision(**args)
    second = initialize_story_revision(**args)
    assert first.story_md_bytes == second.story_md_bytes
    assert first.evidence.file_digest == second.evidence.file_digest
    assert first.evidence.input_digest == second.evidence.input_digest
    assert first.evidence.commit_sha == second.evidence.commit_sha


def test_initialize_story_conflict_when_existing_bytes_differ() -> None:
    """AC-FR0500-02: when the existing on-disk bytes do not match the expected
    file digest, the response is ``STORY_INITIALIZATION_CONFLICT`` and the
    existing bytes are returned unchanged for the caller to surface."""
    template = _template()
    human_story = "Add offline cache."
    expected = initialize_story_revision(
        template=template,
        human_story=human_story,
        actor="human:alice",
        run_id="run_abc",
        commit_sha="c" * 40,
    )
    # Simulate an existing file with different bytes (e.g. another process
    # wrote a different story).
    existing_bytes = b"# Story\n\nUnrelated content written by someone else.\n"
    with pytest.raises(StoryInitConflict) as exc_info:
        initialize_story_revision(
            template=template,
            human_story=human_story,
            actor="human:alice",
            run_id="run_abc",
            commit_sha="c" * 40,
            existing_bytes=existing_bytes,
        )
    assert exc_info.value.code == STORY_INITIALIZATION_CONFLICT
    # Existing bytes are preserved unchanged.
    assert exc_info.value.existing_bytes == existing_bytes
    # The expected digest is also exposed for diagnostic comparison.
    assert exc_info.value.expected_file_digest == expected.evidence.file_digest


# AC-FR0500-03 ---------------------------------------------------------------
def test_initialize_story_navigation_identity_points_to_story_edit_page() -> None:
    """AC-FR0500-03: navigation identity contains the run ID, M-STORY phase,
    spec id and revision identity, matching the Story edit page."""
    template = _template()
    result = initialize_story_revision(
        template=template,
        human_story="Some story.",
        actor="human:alice",
        run_id="run_abc",
        commit_sha="c" * 40,
        spec_id="v0.14-001-workflow-reflow-spec",
    )
    nav = result.navigation
    assert nav.run_id == "run_abc"
    assert nav.phase == "M-STORY"
    assert nav.spec_id == "v0.14-001-workflow-reflow-spec"
    assert nav.document == "story"
    assert nav.revision_digest == result.evidence.file_digest
    assert nav.commit_sha == "c" * 40
