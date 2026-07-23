"""AC-FR1400-01: Release candidate freeze & freshness.

Runtime freezes a unique candidate commit only after: workspace clean,
all formal commits on the release branch, every task's lineage/Red
review/final review/pre-commit evidence current.  Private ``R`` does NOT
enter ancestry.  After freeze, ordinary Agents may not write.  Any
code/test/design/contract/prompt/config change creates a new candidate
and marks old review/CI/build/artifact/security/release approval stale.
"""

from __future__ import annotations


import pytest

from louke.runtime.release_candidate import (
    Candidate,
    CandidateFreezeError,
    CandidateStore,
    DependencyManifest,
    freeze_candidate,
    is_stale_after,
)

_B = "b" * 40
_G = "g" * 40


def _deps(
    *,
    code_changed: bool = False,
    test_changed: bool = False,
    design_changed: bool = False,
    contract_changed: bool = False,
    prompt_changed: bool = False,
    config_changed: bool = False,
) -> DependencyManifest:
    return DependencyManifest(
        code_digest="sha256:" + ("c2" if code_changed else "c1") * 32,
        test_digest="sha256:" + ("t2" if test_changed else "t1") * 32,
        design_digest="sha256:" + ("d2" if design_changed else "d1") * 32,
        contract_digest="sha256:" + ("k2" if contract_changed else "k1") * 32,
        prompt_digest="sha256:" + ("p2" if prompt_changed else "p1") * 32,
        config_digest="sha256:" + ("f2" if config_changed else "f1") * 32,
    )


def test_freeze_candidate_creates_unique_candidate_id() -> None:
    """AC-FR1400-01: freeze produces a unique candidate identity."""
    store = CandidateStore()
    candidate = freeze_candidate(
        store=store,
        run_id="run-1",
        branch_oid=_G,
        workspace_clean=True,
        formal_ancestry_clean=True,
        no_private_red_in_ancestry=True,
        task_lineage_current=True,
        test_completion_current=True,
        precommit_current=True,
        deps=_deps(),
    )
    assert isinstance(candidate, Candidate)
    assert candidate.candidate_id.startswith("cand:")
    assert candidate.commit_oid == _G
    assert candidate.write_disabled is True


def test_freeze_rejects_dirty_workspace() -> None:
    """AC-FR1400-01: dirty workspace blocks freeze."""
    store = CandidateStore()
    with pytest.raises(CandidateFreezeError) as exc:
        freeze_candidate(
            store=store,
            run_id="run-1",
            branch_oid=_G,
            workspace_clean=False,
            formal_ancestry_clean=True,
            no_private_red_in_ancestry=True,
            task_lineage_current=True,
            test_completion_current=True,
            precommit_current=True,
            deps=_deps(),
        )
    assert exc.value.code == "CAND_WORKSPACE_DIRTY"


def test_freeze_rejects_private_red_in_ancestry() -> None:
    """AC-FR1400-01: private R in formal ancestry blocks freeze."""
    store = CandidateStore()
    with pytest.raises(CandidateFreezeError) as exc:
        freeze_candidate(
            store=store,
            run_id="run-1",
            branch_oid=_G,
            workspace_clean=True,
            formal_ancestry_clean=True,
            no_private_red_in_ancestry=False,
            task_lineage_current=True,
            test_completion_current=True,
            precommit_current=True,
            deps=_deps(),
        )
    assert exc.value.code == "CAND_PRIVATE_RED_IN_ANCESTRY"


def test_freeze_rejects_stale_task_lineage() -> None:
    """AC-FR1400-01: stale task lineage blocks freeze."""
    store = CandidateStore()
    with pytest.raises(CandidateFreezeError) as exc:
        freeze_candidate(
            store=store,
            run_id="run-1",
            branch_oid=_G,
            workspace_clean=True,
            formal_ancestry_clean=True,
            no_private_red_in_ancestry=True,
            task_lineage_current=False,
            test_completion_current=True,
            precommit_current=True,
            deps=_deps(),
        )
    assert exc.value.code == "CAND_REVIEW_STALE"


def test_freeze_rejects_stale_precommit() -> None:
    """AC-FR1400-01: stale pre-commit evidence blocks freeze."""
    store = CandidateStore()
    with pytest.raises(CandidateFreezeError) as exc:
        freeze_candidate(
            store=store,
            run_id="run-1",
            branch_oid=_G,
            workspace_clean=True,
            formal_ancestry_clean=True,
            no_private_red_in_ancestry=True,
            task_lineage_current=True,
            test_completion_current=True,
            precommit_current=False,
            deps=_deps(),
        )
    assert exc.value.code == "CAND_PRECOMMIT_STALE"


def test_dependency_change_creates_new_candidate_and_stales_old() -> None:
    """AC-FR1400-01: any dependency bytes change creates a new candidate."""
    store = CandidateStore()
    a = freeze_candidate(
        store=store,
        run_id="run-1",
        branch_oid=_G,
        workspace_clean=True,
        formal_ancestry_clean=True,
        no_private_red_in_ancestry=True,
        task_lineage_current=True,
        test_completion_current=True,
        precommit_current=True,
        deps=_deps(),
    )
    b = freeze_candidate(
        store=store,
        run_id="run-1",
        branch_oid=_G,
        workspace_clean=True,
        formal_ancestry_clean=True,
        no_private_red_in_ancestry=True,
        task_lineage_current=True,
        test_completion_current=True,
        precommit_current=True,
        deps=_deps(code_changed=True),
    )
    assert a.candidate_id != b.candidate_id
    assert store.is_stale(a.candidate_id) is True
    assert store.is_stale(b.candidate_id) is False


def test_is_stale_after_various_dependency_changes() -> None:
    """AC-FR1400-01: code/test/design/contract/prompt/config changes all stale old."""
    for change in (
        "code_changed",
        "test_changed",
        "design_changed",
        "contract_changed",
        "prompt_changed",
        "config_changed",
    ):
        old_deps = _deps()
        new_kwargs = {change: True}
        new_deps = _deps(**new_kwargs)
        assert is_stale_after(old_deps, new_deps) is True


def test_no_change_no_new_candidate() -> None:
    """AC-FR1400-01: same dependency set yields same candidate id."""
    store = CandidateStore()
    a = freeze_candidate(
        store=store,
        run_id="run-1",
        branch_oid=_G,
        workspace_clean=True,
        formal_ancestry_clean=True,
        no_private_red_in_ancestry=True,
        task_lineage_current=True,
        test_completion_current=True,
        precommit_current=True,
        deps=_deps(),
    )
    b = freeze_candidate(
        store=store,
        run_id="run-1",
        branch_oid=_G,
        workspace_clean=True,
        formal_ancestry_clean=True,
        no_private_red_in_ancestry=True,
        task_lineage_current=True,
        test_completion_current=True,
        precommit_current=True,
        deps=_deps(),
    )
    assert a.candidate_id == b.candidate_id


def test_write_disabled_after_freeze() -> None:
    """AC-FR1400-01: ordinary Agent writes are disabled after freeze."""
    store = CandidateStore()
    candidate = freeze_candidate(
        store=store,
        run_id="run-1",
        branch_oid=_G,
        workspace_clean=True,
        formal_ancestry_clean=True,
        no_private_red_in_ancestry=True,
        task_lineage_current=True,
        test_completion_current=True,
        precommit_current=True,
        deps=_deps(),
    )
    assert candidate.write_disabled is True
    # A second freeze with the same deps is idempotent.
    again = freeze_candidate(
        store=store,
        run_id="run-1",
        branch_oid=_G,
        workspace_clean=True,
        formal_ancestry_clean=True,
        no_private_red_in_ancestry=True,
        task_lineage_current=True,
        test_completion_current=True,
        precommit_current=True,
        deps=_deps(),
    )
    assert again.candidate_id == candidate.candidate_id
