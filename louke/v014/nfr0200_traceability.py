"""NFR-0200: 可追溯性与 Secret 安全.

Implements the deterministic contract slice of NFR-0200:

* :class:`TimelineEntry` is the canonical trace record. Each entry carries
  sequence, run_id, step, attempt_id, actor, at, correlation_id,
  input_digest, output_digest and event_type. :func:`sort_timeline` returns
  entries ordered by sequence (then event_id) so the timeline reads as a
  deterministic, append-only log (AC-NFR0200-01).

* :func:`build_issue_trace_record` builds an immutable
  :class:`IssueTraceRecord` that yields the same Story/Spec/Acceptance
  digests, requirement ID, Issue URL and release Project identity from both
  forward (Issue body) and reverse (Spec section) queries. The record is
  frozen so later revisions cannot rewrite historical digest records
  (AC-NFR0200-02).

* :func:`redact_secret` replaces raw secret byte strings with the
  ``[REDACTED:secret]`` marker. :func:`scan_for_secret_bytes` scans a dict
  of artifacts for raw secret bytes and returns a report with the leak
  count and leaking file names; clean artifacts return zero raw matches
  (AC-NFR0200-03).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


REDACTED = "[REDACTED:secret]"


# AC-NFR0200-01 ---------------------------------------------------------------
@dataclass(frozen=True)
class TimelineEntry:
    """A single timeline entry (IF-COMMON-03).

    Attributes:
        sequence: Monotonic sequence within the run.
        run_id: Opaque run identifier.
        step: Workflow step the entry belongs to.
        attempt_id: Agent attempt id when applicable; ``None`` otherwise.
        actor: Non-secret actor identity.
        at: UTC RFC 3339 timestamp.
        correlation_id: Stable correlation identity.
        input_digest: ``sha256:<hex>`` digest of the input artifact.
        output_digest: ``sha256:<hex>`` digest of the output artifact.
        event_type: Type of the event (``step_transition``, ``review``,
            ``gate``, ``task``, ``commit``, ``external_operation`` etc.).
        event_id: Optional event id used as a tie-breaker in
            :func:`sort_timeline`.
    """

    sequence: int
    run_id: str
    step: str
    attempt_id: str | None
    actor: str
    at: str
    correlation_id: str
    input_digest: str
    output_digest: str
    event_type: str
    event_id: str | None = None


def sort_timeline(entries: Iterable[TimelineEntry]) -> tuple[TimelineEntry, ...]:
    """Return ``entries`` ordered by sequence (then event_id).

    Args:
        entries: Iterable of :class:`TimelineEntry`.

    Returns:
        A tuple of :class:`TimelineEntry` ordered by ``sequence`` ascending;
        ties are broken by ``event_id`` ascending so the timeline is
        deterministic (AC-NFR0200-01).
    """
    return tuple(
        sorted(
            entries,
            key=lambda e: (e.sequence, e.event_id or ""),
        )
    )


# AC-NFR0200-02 ---------------------------------------------------------------
@dataclass(frozen=True)
class IssueTraceRecord:
    """Immutable trace record linking a requirement Issue to its digests.

    Attributes:
        requirement_id: Exact requirement ID.
        story_digest: ``sha256:<hex>`` Story digest at lock time.
        spec_digest: ``sha256:<hex>`` Spec digest at lock time.
        acceptance_digest: ``sha256:<hex>`` Acceptance digest at lock time.
        issue_url: Issue URL.
        release_project_identity: Foundation release GitHub Project node id.
        spec_section_anchor: Spec section anchor (e.g. ``fr-0100``).
        acceptance_section_anchor: Acceptance section anchor (e.g.
            ``ac-fr-0100``).
    """

    requirement_id: str
    story_digest: str
    spec_digest: str
    acceptance_digest: str
    issue_url: str
    release_project_identity: str
    spec_section_anchor: str
    acceptance_section_anchor: str

    def forward_query(self) -> dict[str, str]:
        """Return the forward-query view (Issue body -> digests/identity)."""
        return {
            "requirement_id": self.requirement_id,
            "story_digest": self.story_digest,
            "spec_digest": self.spec_digest,
            "acceptance_digest": self.acceptance_digest,
            "issue_url": self.issue_url,
            "release_project_identity": self.release_project_identity,
        }

    def reverse_query_from_spec_section(self) -> dict[str, str]:
        """Return the reverse-query view (Spec section -> Issue URL)."""
        return {
            "requirement_id": self.requirement_id,
            "spec_digest": self.spec_digest,
            "spec_section_anchor": self.spec_section_anchor,
            "issue_url": self.issue_url,
            "release_project_identity": self.release_project_identity,
        }


def build_issue_trace_record(
    *,
    requirement_id: str,
    story_digest: str,
    spec_digest: str,
    acceptance_digest: str,
    issue_url: str,
    release_project_identity: str,
    spec_section_anchor: str,
    acceptance_section_anchor: str,
) -> IssueTraceRecord:
    """Build an immutable :class:`IssueTraceRecord`.

    The record is frozen so later revisions cannot rewrite historical
    digest records (AC-NFR0200-02).
    """
    return IssueTraceRecord(
        requirement_id=requirement_id,
        story_digest=story_digest,
        spec_digest=spec_digest,
        acceptance_digest=acceptance_digest,
        issue_url=issue_url,
        release_project_identity=release_project_identity,
        spec_section_anchor=spec_section_anchor,
        acceptance_section_anchor=acceptance_section_anchor,
    )


# AC-NFR0200-03 ---------------------------------------------------------------
def redact_secret(text: str, *, secret_patterns: Iterable[str]) -> str:
    """Replace raw secret byte strings in ``text`` with :data:`REDACTED`.

    Args:
        text: The text to redact.
        secret_patterns: Iterable of regex patterns matching raw secret
            substrings.

    Returns:
        ``text`` with every match replaced by :data:`REDACTED`. The raw
        secret byte strings never appear in the result (AC-NFR0200-03).
    """
    redacted = text
    for pattern in secret_patterns:
        redacted = re.sub(pattern, REDACTED, redacted)
    return redacted


@dataclass(frozen=True)
class SecretScanReport:
    """Report returned by :func:`scan_for_secret_bytes`.

    Attributes:
        raw_match_count: Number of files containing at least one raw secret
            byte string.
        leaking_files: Tuple of file names that contained a raw secret.
        scanned_text: Concatenation of all scanned artifact text (for
            diagnostic purposes).
    """

    raw_match_count: int
    leaking_files: tuple[str, ...]
    _scanned_text: str = ""

    def scanned_text(self) -> str:
        """Return the concatenated scanned text (for diagnostics)."""
        return self._scanned_text


def scan_for_secret_bytes(
    artifacts: dict[str, str],
    *,
    secrets: Iterable[str],
) -> SecretScanReport:
    """Scan ``artifacts`` for raw secret byte strings.

    Args:
        artifacts: Dict mapping file name to text content.
        secrets: Iterable of raw secret byte strings to scan for.

    Returns:
        A :class:`SecretScanReport`. ``raw_match_count`` is the number of
        files containing at least one raw secret; ``leaking_files`` lists
        them. Clean artifacts return ``raw_match_count == 0``
        (AC-NFR0200-03).
    """
    leaking: list[str] = []
    scanned_parts: list[str] = []
    for name, content in artifacts.items():
        scanned_parts.append(content)
        for secret in secrets:
            if secret and secret in content:
                leaking.append(name)
                break
    return SecretScanReport(
        raw_match_count=len(leaking),
        leaking_files=tuple(leaking),
        _scanned_text="\n".join(scanned_parts),
    )
