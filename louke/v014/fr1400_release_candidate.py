"""FR-1400: Release candidate freeze & freshness.

Runtime freezes a unique candidate commit only after: workspace clean,
all formal commits on the release branch, every task's lineage/Red
review/final review/pre-commit evidence current.  Private ``R`` does
NOT enter ancestry.  After freeze, ordinary Agents may not write.  Any
code/test/design/contract/prompt/config change creates a new candidate
and marks old review/CI/build/artifact/security/release approval stale
(AC-FR1400-01).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

ERROR_CODES = (
    "CAND_WORKSPACE_DIRTY",
    "CAND_BRANCH_CONFLICT",
    "CAND_TASK_INCOMPLETE",
    "CAND_TESTS_INCOMPLETE",
    "CAND_REVIEW_STALE",
    "CAND_PRECOMMIT_STALE",
    "CAND_PRIVATE_RED_IN_ANCESTRY",
    "CAND_DEPENDENCY_MISSING",
    "CAND_FREEZE_CONFLICT",
    "CAND_WRITE_DISABLED",
    "CAND_STALE",
)


class CandidateFreezeError(Exception):
    """A fail-closed candidate freeze rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DependencyManifest:
    """The dependency digest set used to derive candidate identity (AC-FR1400-01).

    Attributes:
        code_digest: ``sha256:<hex>`` of all source bytes.
        test_digest: ``sha256:<hex>`` of all test bytes.
        design_digest: ``sha256:<hex>`` of design artifacts.
        contract_digest: ``sha256:<hex>`` of project-local contracts.
        prompt_digest: ``sha256:<hex>`` of canonical prompt bundle.
        config_digest: ``sha256:<hex>`` of config files.
    """

    code_digest: str
    test_digest: str
    design_digest: str
    contract_digest: str
    prompt_digest: str
    config_digest: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code_digest": self.code_digest,
            "test_digest": self.test_digest,
            "design_digest": self.design_digest,
            "contract_digest": self.contract_digest,
            "prompt_digest": self.prompt_digest,
            "config_digest": self.config_digest,
        }


def is_stale_after(old: DependencyManifest, new: DependencyManifest) -> bool:
    """Return ``True`` if ``new`` differs from ``old`` in any digest (AC-FR1400-01)."""
    return old.to_dict() != new.to_dict()


@dataclass(frozen=True)
class Candidate:
    """A frozen release candidate (AC-FR1400-01).

    Attributes:
        candidate_id: Stable candidate identity.
        run_id: Runtime-issued run id.
        commit_oid: Frozen commit OID.
        branch_oid: Branch OID (same as commit_oid).
        workspace_clean: ``True`` if workspace was clean at freeze.
        formal_ancestry_clean: ``True`` if formal ancestry has no foreign commits.
        no_private_red_in_ancestry: ``True`` if no private R is in ancestry.
        write_disabled: ``True`` after freeze (ordinary Agent writes blocked).
        deps: :class:`DependencyManifest` used to derive identity.
    """

    candidate_id: str
    run_id: str
    commit_oid: str
    branch_oid: str
    workspace_clean: bool
    formal_ancestry_clean: bool
    no_private_red_in_ancestry: bool
    write_disabled: bool
    deps: DependencyManifest


class CandidateStore:
    """In-memory candidate pointer store with stale tracking (AC-FR1400-01)."""

    def __init__(self) -> None:
        self._candidates: dict[str, Candidate] = {}
        self._stale: set[str] = set()

    def add(self, candidate: Candidate) -> None:
        # Mark all prior candidates as stale.
        for existing_id in list(self._candidates.keys()):
            self._stale.add(existing_id)
        self._candidates[candidate.candidate_id] = candidate

    def is_stale(self, candidate_id: str) -> bool:
        return candidate_id in self._stale

    def current(self) -> Candidate | None:
        for cid, candidate in self._candidates.items():
            if cid not in self._stale:
                return candidate
        return None


def _candidate_id(run_id: str, commit_oid: str, deps: DependencyManifest) -> str:
    payload = json.dumps(
        {
            "run_id": run_id,
            "commit_oid": commit_oid,
            "deps": deps.to_dict(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "cand:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def freeze_candidate(
    *,
    store: CandidateStore,
    run_id: str,
    branch_oid: str,
    workspace_clean: bool,
    formal_ancestry_clean: bool,
    no_private_red_in_ancestry: bool,
    task_lineage_current: bool,
    test_completion_current: bool,
    precommit_current: bool,
    deps: DependencyManifest,
) -> Candidate:
    """Freeze a unique release candidate (AC-FR1400-01).

    Args:
        store: :class:`CandidateStore` for stale tracking.
        run_id: Runtime-issued run id.
        branch_oid: Branch OID to freeze.
        workspace_clean: ``True`` if workspace is clean.
        formal_ancestry_clean: ``True`` if formal ancestry is clean.
        no_private_red_in_ancestry: ``True`` if no private R is in ancestry.
        task_lineage_current: ``True`` if every task's lineage is current.
        test_completion_current: ``True`` if test completion is current.
        precommit_current: ``True`` if pre-commit evidence is current.
        deps: :class:`DependencyManifest` for candidate identity.

    Returns:
        An immutable :class:`Candidate` with ``write_disabled=True``.

    Raises:
        CandidateFreezeError: With a stable code from :data:`ERROR_CODES`
            if any precondition fails.
    """
    if not workspace_clean:
        raise CandidateFreezeError("CAND_WORKSPACE_DIRTY", "workspace is dirty")
    if not no_private_red_in_ancestry:
        raise CandidateFreezeError(
            "CAND_PRIVATE_RED_IN_ANCESTRY",
            "private R commit is in formal ancestry",
        )
    if not task_lineage_current:
        raise CandidateFreezeError(
            "CAND_REVIEW_STALE", "task lineage/review is not current"
        )
    if not test_completion_current:
        raise CandidateFreezeError(
            "CAND_TESTS_INCOMPLETE", "test completion evidence is not current"
        )
    if not precommit_current:
        raise CandidateFreezeError(
            "CAND_PRECOMMIT_STALE", "pre-commit evidence is not current"
        )
    if not formal_ancestry_clean:
        raise CandidateFreezeError(
            "CAND_BRANCH_CONFLICT", "formal ancestry contains foreign commits"
        )
    candidate = Candidate(
        candidate_id=_candidate_id(run_id, branch_oid, deps),
        run_id=run_id,
        commit_oid=branch_oid,
        branch_oid=branch_oid,
        workspace_clean=workspace_clean,
        formal_ancestry_clean=formal_ancestry_clean,
        no_private_red_in_ancestry=no_private_red_in_ancestry,
        write_disabled=True,
        deps=deps,
    )
    store.add(candidate)
    return candidate
