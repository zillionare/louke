"""Unit tests for louke/_tools/discuss.py — focus on the is_ready gate correctly
treating [REOPEN] as a blocker (reopen ≡ open).

Bug history: previously the is_ready() gate only checked threads anchored to
FR/NFR/US sections, ignoring unit-less threads in chapters like
'### 5.2 Chat'. v0.13 review surfaced this when architecture/interfaces/test-plan
threads in chapter sections were status='reopen' yet --check-ready returned ready=true.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from louke._tools.discuss import DiscussParser, STATUS_REOPEN, STATUS_OPEN


@pytest.fixture
def spec_with_chapter_thread(tmp_path: Path) -> Path:
    """Spec file with a chapter section (5.2 Chat) containing a [REOPEN]
    thread and no FR/NFR/US sections. Used to reproduce the original bug.
    """
    content = textwrap.dedent(
        """\
        # Programmatic Workflow Control — Test Spec

        ## 1. Goal

        Some intro.

        ### 5.2 Chat

        Some content.

        > **Prism**: Chat streaming upstream not implemented yet.
        >> **Archer**: Documented as deferred to v0.14.
        > **Prism** [REOPEN]: still missing concrete streaming reference.
        """
    )
    spec = tmp_path / "spec.md"
    spec.write_text(content)
    return spec


def test_chapter_reopen_thread_blocks_readiness(spec_with_chapter_thread: Path):
    """A [REOPEN] thread anchored to a chapter section (no FR/NFR/US link)
    must block readiness. Previously the gate silently returned ready=true
    because it only iterated over FR/NFR/US units.
    """
    parser = DiscussParser()
    result = parser.parse_file(spec_with_chapter_thread)
    print(f"DEBUG threads: {[t.thread_id + '/' + t.status for t in result.threads]}")
    print(f"DEBUG units: {result.units}")
    print(f"DEBUG is_ready: {result.is_ready}")
    print(f"DEBUG blockers: {result.ready_blockers}")
    reopen_count = sum(1 for t in result.threads if t.status == STATUS_REOPEN)
    assert reopen_count == 1, (
        f"parser should find the 1 [REOPEN] thread (got {reopen_count})"
    )
    assert result.is_ready is False, (
        f"is_ready must be False when a [REOPEN] thread exists; got True. blockers={result.ready_blockers}"
    )
    assert any(
        STATUS_REOPEN in b or "reopen" in b.lower() for b in result.ready_blockers
    ), f"blockers must mention the reopen thread; got {result.ready_blockers}"


@pytest.fixture
def spec_with_open_thread(tmp_path: Path) -> Path:
    """Spec with an [OPEN] thread in a chapter — must also block."""
    content = textwrap.dedent(
        """\
        # Test Spec

        ### 5.2 Chat

        > **Prism** [OPEN]: Chat streaming not implemented.
        """
    )
    spec = tmp_path / "spec.md"
    spec.write_text(content)
    return spec


def test_chapter_open_thread_blocks_readiness(spec_with_open_thread: Path):
    """Control case: an [OPEN] thread in a chapter also blocks."""
    parser = DiscussParser()
    result = parser.parse_file(spec_with_open_thread)
    open_count = sum(1 for t in result.threads if t.status == STATUS_OPEN)
    assert open_count == 1
    assert result.is_ready is False


@pytest.fixture
def spec_all_resolved(tmp_path: Path) -> Path:
    """Spec with all threads in chapter sections [RESOLVED] — must be ready."""
    content = textwrap.dedent(
        """\
        # Test Spec

        ### 5.2 Chat

        > **Prism** [RESOLVED]: Documented as deferred.
        """
    )
    spec = tmp_path / "spec.md"
    spec.write_text(content)
    return spec


def test_chapter_resolved_thread_does_not_block(spec_all_resolved: Path):
    """If all chapter-section threads are resolved, gate is ready."""
    parser = DiscussParser()
    result = parser.parse_file(spec_all_resolved)
    assert result.is_ready is True, (
        f"all resolved threads must give ready=true; got blockers={result.ready_blockers}"
    )
