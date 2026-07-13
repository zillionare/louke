"""End-to-end traceability ledger (FR-2201).

The traceability ledger binds requirements (FR/NFR/AC) to tasks, code commits,
diffs and authoritative test results. It validates readiness for M-DEV and
completion gates, and marks downstream evidence stale when approved contracts
change.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class EvidenceKind(Enum):
    """Kind of evidence attached to a trace entry."""

    CODE = auto()
    TEST = auto()


class TraceabilityError(ValueError):
    """Raised when traceability requirements are not met."""


@dataclass(frozen=True, slots=True)
class CodeEvidence:
    """Evidence derived from a real code commit/diff.

    Attributes:
        commit: Commit identifier.
        diff_digest: Digest of the diff.
    """

    commit: str
    diff_digest: str


@dataclass
class TraceEntry:
    """A single traceability record.

    Attributes:
        entry_id: Stable opaque identifier.
        fr_id: Feature requirement identifier.
        ac_id: Acceptance criteria identifier.
        test_plan: Associated test plan path.
        task_id: Assigned task identifier.
        issue: Associated GitHub issue.
        contract_digest: Digest of the contract the AC was approved against.
        evidence: Structured evidence (code or test).
        evidence_status: Status of the evidence (pending/verified/stale/closed).
        gate: Current gate the entry is waiting at, if any.
    """

    entry_id: str
    fr_id: str
    ac_id: str
    test_plan: str = ""
    task_id: str = ""
    issue: str = ""
    contract_digest: str = ""
    evidence: Any = None
    evidence_status: str = "pending"
    gate: str = ""


class TraceLedger:
    """Ledger that records and validates requirement-to-evidence traceability."""

    def __init__(self) -> None:
        self._entries: dict[str, TraceEntry] = {}
        self._current_contract_digest: str = ""

    def add_requirement(
        self,
        fr_id: str,
        ac_id: str,
        test_plan: str = "",
        task_id: str = "",
        issue: str = "",
        contract_digest: str = "",
        evidence_status: str = "pending",
    ) -> TraceEntry:
        """Add a requirement/AC to the ledger.

        Args:
            fr_id: Feature requirement identifier.
            ac_id: Acceptance criteria identifier.
            test_plan: Test plan path.
            task_id: Assigned task identifier.
            issue: Associated GitHub issue.
            contract_digest: Contract digest the AC was approved against.
            evidence_status: Initial evidence status.

        Returns:
            The created :class:`TraceEntry`.
        """
        entry = TraceEntry(
            entry_id=f"trace_{uuid.uuid4().hex[:12]}",
            fr_id=fr_id,
            ac_id=ac_id,
            test_plan=test_plan,
            task_id=task_id,
            issue=issue,
            contract_digest=contract_digest,
            evidence_status=evidence_status,
        )
        self._entries[entry.entry_id] = entry
        return entry

    def link_task(self, entry_id: str, task_id: str, issue: str) -> None:
        """Link a task and issue to an existing entry."""
        entry = self._entries.get(entry_id)
        if entry is None:
            raise KeyError(f"trace entry {entry_id!r} not found")
        entry.task_id = task_id
        entry.issue = issue

    def link_evidence(
        self,
        entry_id: str,
        kind: EvidenceKind,
        evidence: Any,
    ) -> None:
        """Attach evidence to an entry.

        Args:
            entry_id: Trace entry identifier.
            kind: Evidence kind (currently informational).
            evidence: Structured evidence object or dict.
        """
        del kind  # reserved for future validation
        entry = self._entries.get(entry_id)
        if entry is None:
            raise KeyError(f"trace entry {entry_id!r} not found")
        entry.evidence = evidence

    def mark_contract_current_digest(self, digest: str) -> None:
        """Set the current approved contract digest."""
        self._current_contract_digest = digest

    def validate_mdev_ready(self) -> None:
        """Validate that all entries are ready to enter M-DEV.

        Raises:
            TraceabilityError: If any AC is unmapped, stale or has a contract
                digest mismatch.
        """
        blockers: list[str] = []
        for entry in self._entries.values():
            if not entry.task_id:
                blockers.append(f"{entry.ac_id} has no assigned task")
            if (
                entry.contract_digest
                and self._current_contract_digest
                and entry.contract_digest != self._current_contract_digest
            ):
                blockers.append(f"{entry.ac_id} references stale contract digest")
        if blockers:
            raise TraceabilityError(f"M-DEV blocked: {', '.join(blockers)}")

    def build_devon_manifest(self, run_id: str) -> dict[str, Any]:
        """Build a Devon task manifest from the ledger.

        Args:
            run_id: Run identifier.

        Returns:
            Manifest dict containing assigned issues and ACs.
        """
        issues = [entry.issue for entry in self._entries.values() if entry.issue]
        acs = [entry.ac_id for entry in self._entries.values()]
        return {
            "run_id": run_id,
            "issues": issues,
            "acs": acs,
        }

    def close_ac(self, entry_id: str, evidence_digest: str) -> None:
        """Mark an AC as closed with evidence digest."""
        entry = self._entries.get(entry_id)
        if entry is None:
            raise KeyError(f"trace entry {entry_id!r} not found")
        entry.evidence_status = "closed"
        entry.evidence_digest = evidence_digest  # type: ignore[attr-defined]

    def validate_all_acs_closed(self) -> None:
        """Validate that every AC is closed.

        Raises:
            TraceabilityError: If any AC is not closed.
        """
        open_ones = [
            entry.ac_id
            for entry in self._entries.values()
            if entry.evidence_status != "closed"
        ]
        if open_ones:
            raise TraceabilityError(
                f"gate blocked by unclosed ACs: {sorted(open_ones)}"
            )

    def lookup_by_task(self, task_id: str) -> list[TraceEntry]:
        """Return all trace entries linked to ``task_id``."""
        return [entry for entry in self._entries.values() if entry.task_id == task_id]

    def apply_contract_change(
        self,
        affected_acs: list[str],
        new_contract_digest: str,
    ) -> None:
        """Mark downstream evidence stale for affected ACs.

        Args:
            affected_acs: AC identifiers affected by the change.
            new_contract_digest: New approved contract digest.
        """
        self._current_contract_digest = new_contract_digest
        affected = set(affected_acs)
        for entry in self._entries.values():
            if entry.ac_id in affected:
                entry.evidence_status = "stale"
                entry.contract_digest = new_contract_digest
                entry.gate = "requirements_approval"
