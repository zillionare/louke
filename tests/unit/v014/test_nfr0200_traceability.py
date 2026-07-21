"""NFR-0200: 可追溯性与 Secret 安全.

AC references:
- AC-NFR0200-01: a run's timeline covers setup decisions, step transitions,
  revisions, reviews, gates, tasks, commits and external operations; each
  record carries run/step/attempt, actor, time, correlation, input digest
  and output digest.
- AC-NFR0200-02: from any locked requirement's GitHub Issue, querying
  forward (Issue body) and reverse (Spec section) yields the same
  Story/Spec/Acceptance digests, requirement ID, Issue URL and release
  Project identity; historical digest records are not rewritten by later
  revisions.
- AC-NFR0200-03: known credential/token/cookie/provider-secret byte strings
  injected into setup/OpenCode/GitHub inputs never appear as raw bytes in
  manifests, documents, events, logs, error responses, commits or Agent
  inputs; only redacted values, non-secret identities and digests appear.
"""

from __future__ import annotations

import pytest

from louke.v014.nfr0200_traceability import (
    REDACTED,
    IssueTraceRecord,
    TimelineEntry,
    build_issue_trace_record,
    redact_secret,
    scan_for_secret_bytes,
    sort_timeline,
)


# AC-NFR0200-01 ---------------------------------------------------------------
def test_timeline_entries_carry_required_trace_fields() -> None:
    """AC-NFR0200-01: each TimelineEntry carries run/step/attempt, actor,
    time, correlation, input digest and output digest."""
    entry = TimelineEntry(
        sequence=1,
        run_id="run_1",
        step="M-STORY",
        attempt_id="att_1",
        actor="human:alice",
        at="2026-07-21T00:00:00+00:00",
        correlation_id="corr_1",
        input_digest="sha256:" + "i" * 64,
        output_digest="sha256:" + "o" * 64,
        event_type="step_transition",
    )
    assert entry.run_id == "run_1"
    assert entry.step == "M-STORY"
    assert entry.attempt_id == "att_1"
    assert entry.actor == "human:alice"
    assert entry.at
    assert entry.correlation_id == "corr_1"
    assert entry.input_digest.startswith("sha256:")
    assert entry.output_digest.startswith("sha256:")


def test_timeline_sorted_by_sequence() -> None:
    """AC-NFR0200-01: the timeline is ordered by sequence; ties are broken
    deterministically by event_id."""
    entries = [
        TimelineEntry(
            sequence=3,
            run_id="r",
            step="M-SPEC",
            attempt_id="a",
            actor="x",
            at="t3",
            correlation_id="c3",
            input_digest="sha256:i3",
            output_digest="sha256:o3",
            event_type="e3",
            event_id="e3",
        ),
        TimelineEntry(
            sequence=1,
            run_id="r",
            step="M-STORY",
            attempt_id="a",
            actor="x",
            at="t1",
            correlation_id="c1",
            input_digest="sha256:i1",
            output_digest="sha256:o1",
            event_type="e1",
            event_id="e1",
        ),
        TimelineEntry(
            sequence=2,
            run_id="r",
            step="M-STORY",
            attempt_id="a",
            actor="x",
            at="t2",
            correlation_id="c2",
            input_digest="sha256:i2",
            output_digest="sha256:o2",
            event_type="e2",
            event_id="e2",
        ),
    ]
    sorted_entries = sort_timeline(entries)
    assert [e.sequence for e in sorted_entries] == [1, 2, 3]


# AC-NFR0200-02 ---------------------------------------------------------------
def test_issue_trace_record_supports_forward_and_reverse_query() -> None:
    """AC-NFR0200-02: an IssueTraceRecord yields the same Story/Spec/
    Acceptance digests, requirement ID, Issue URL and release Project
    identity from both forward (Issue body) and reverse (Spec section)
    queries."""
    record = build_issue_trace_record(
        requirement_id="FR-0100",
        story_digest="sha256:" + "s" * 64,
        spec_digest="sha256:" + "p" * 64,
        acceptance_digest="sha256:" + "a" * 64,
        issue_url="https://github.com/zillionare/louke/issues/226",
        release_project_identity="P_node_1",
        spec_section_anchor="fr-0100",
        acceptance_section_anchor="ac-fr-0100",
    )
    assert isinstance(record, IssueTraceRecord)
    # Forward: Issue body -> digests.
    forward = record.forward_query()
    assert forward["requirement_id"] == "FR-0100"
    assert forward["story_digest"] == "sha256:" + "s" * 64
    assert forward["spec_digest"] == "sha256:" + "p" * 64
    assert forward["acceptance_digest"] == "sha256:" + "a" * 64
    assert forward["issue_url"].endswith("/issues/226")
    assert forward["release_project_identity"] == "P_node_1"
    # Reverse: Spec section -> Issue URL.
    reverse = record.reverse_query_from_spec_section()
    assert reverse["issue_url"].endswith("/issues/226")
    assert reverse["requirement_id"] == "FR-0100"
    assert reverse["spec_digest"] == "sha256:" + "p" * 64


def test_issue_trace_history_is_not_rewritten_by_later_revisions() -> None:
    """AC-NFR0200-02: the trace record's digests are immutable; later
    revisions cannot rewrite historical digest records."""
    record = build_issue_trace_record(
        requirement_id="FR-0100",
        story_digest="sha256:" + "s" * 64,
        spec_digest="sha256:" + "p" * 64,
        acceptance_digest="sha256:" + "a" * 64,
        issue_url="https://github.com/zillionare/louke/issues/226",
        release_project_identity="P_node_1",
        spec_section_anchor="fr-0100",
        acceptance_section_anchor="ac-fr-0100",
    )
    # Immutability: the record is frozen.
    with pytest.raises(Exception):
        record.story_digest = "sha256:" + "z" * 64  # type: ignore[misc]


# AC-NFR0200-03 ---------------------------------------------------------------
def test_redact_secret_replaces_raw_secret_with_redacted_marker() -> None:
    """AC-NFR0200-03: redact_secret replaces raw secret bytes with the
    ``[REDACTED:secret]`` marker."""
    text = "token=ghp_AAAABBBBCCCCDDDD; cookie=session=xyz"
    redacted = redact_secret(
        text, secret_patterns=(r"ghp_[A-Za-z0-9]+", r"session=[A-Za-z0-9]+")
    )
    assert "ghp_AAAABBBBCCCCDDDD" not in redacted
    assert "session=xyz" not in redacted
    assert REDACTED in redacted


def test_scan_for_secret_bytes_returns_zero_raw_matches_in_clean_artifacts() -> None:
    """AC-NFR0200-03: a scan over clean artifacts (no raw secrets) returns
    zero raw matches."""
    canary = "ghp_SUPERSECRETTOKEN1234"
    artifacts = {
        "manifest.json": '{"token": "[REDACTED:secret]"}',
        "event.json": '{"actor": "human:alice", "details": {"token": "[REDACTED:secret]"}}',
        "log.txt": "[INFO] refresh ok",
        "error.json": '{"code": "VALIDATION_FAILED", "message": "bad input"}',
        "commit.msg": "feat: add offline cache",
        "agent_input.json": '{"task_id": "t_1", "auth": "[REDACTED:secret]"}',
    }
    report = scan_for_secret_bytes(artifacts, secrets=(canary,))
    assert report.raw_match_count == 0
    assert canary not in report.scanned_text()


def test_scan_for_secret_bytes_detects_raw_secret_leak() -> None:
    """AC-NFR0200-03: a scan over artifacts containing a raw secret reports
    the leak with file and count."""
    canary = "ghp_SUPERSECRETTOKEN1234"
    artifacts = {
        "manifest.json": f'{{"token": "{canary}"}}',  # leak
        "event.json": '{"actor": "human:alice"}',
    }
    report = scan_for_secret_bytes(artifacts, secrets=(canary,))
    assert report.raw_match_count == 1
    assert "manifest.json" in report.leaking_files
