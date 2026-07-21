"""Integration tests for FR-1400: Release candidate freeze & freshness.

AC-FR1400-01: With clean workspace, complete formal commits, and every
task's lineage/Red review/final review/pre-commit evidence current,
Runtime freezes a unique candidate; its ancestry excludes private Red
commits. Post-freeze modifications to code/tests/design/contract/prompt/
config create a new candidate and stale-mark old review/CI/build/
artifact/security/release approval.

Interfaces covered (per interfaces.md):
- IF-CAND-01 (Primary ARC-09)
- IF-RGR-01 (lineage, ARC-05)
- IF-WFR-01 (workflow context, ARC-01)
"""
# AC-FR1400-01

from __future__ import annotations

import pytest

from louke.v014.fr1400_release_candidate import (
    ERROR_CODES,
    Candidate,
    CandidateFreezeError,
    CandidateStore,
    DependencyManifest,
    freeze_candidate,
    is_stale_after,
)


def _valid_deps() -> DependencyManifest:
    return DependencyManifest(
        code_digest="sha256:code",
        test_digest="sha256:test",
        design_digest="sha256:design",
        contract_digest="sha256:contract",
        prompt_digest="sha256:prompt",
        config_digest="sha256:config",
    )


def _valid_freeze_kwargs(store: CandidateStore) -> dict:
    return dict(
        store=store,
        run_id="run-001",
        branch_oid="c" * 40,
        workspace_clean=True,
        formal_ancestry_clean=True,
        no_private_red_in_ancestry=True,
        task_lineage_current=True,
        test_completion_current=True,
        precommit_current=True,
        deps=_valid_deps(),
    )


# ---------------------------------------------------------------------------
# freeze_candidate
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_freeze_candidate_creates_unique_candidate_with_write_disabled():
    """AC-FR1400-01: valid freeze -> Candidate with write_disabled=True."""
    store = CandidateStore()
    cand = freeze_candidate(**_valid_freeze_kwargs(store))
    assert isinstance(cand, Candidate)
    assert cand.write_disabled is True
    assert cand.commit_oid == "c" * 40
    assert cand.candidate_id.startswith("cand:")


@pytest.mark.real_module
def test_freeze_candidate_rejects_dirty_workspace():
    """AC-FR1400-01: dirty workspace -> CAND_WORKSPACE_DIRTY."""
    store = CandidateStore()
    kw = _valid_freeze_kwargs(store)
    kw["workspace_clean"] = False
    with pytest.raises(CandidateFreezeError) as exc:
        freeze_candidate(**kw)
    assert exc.value.code == "CAND_WORKSPACE_DIRTY"


@pytest.mark.real_module
def test_freeze_candidate_rejects_private_red_in_ancestry():
    """AC-FR1400-01: private R in ancestry -> CAND_PRIVATE_RED_IN_ANCESTRY."""
    store = CandidateStore()
    kw = _valid_freeze_kwargs(store)
    kw["no_private_red_in_ancestry"] = False
    with pytest.raises(CandidateFreezeError) as exc:
        freeze_candidate(**kw)
    assert exc.value.code == "CAND_PRIVATE_RED_IN_ANCESTRY"


@pytest.mark.real_module
def test_freeze_candidate_rejects_stale_task_lineage():
    """AC-FR1400-01: task lineage/review not current -> CAND_REVIEW_STALE."""
    store = CandidateStore()
    kw = _valid_freeze_kwargs(store)
    kw["task_lineage_current"] = False
    with pytest.raises(CandidateFreezeError) as exc:
        freeze_candidate(**kw)
    assert exc.value.code == "CAND_REVIEW_STALE"


@pytest.mark.real_module
def test_freeze_candidate_rejects_stale_test_completion():
    """AC-FR1400-01: test completion not current -> CAND_TESTS_INCOMPLETE."""
    store = CandidateStore()
    kw = _valid_freeze_kwargs(store)
    kw["test_completion_current"] = False
    with pytest.raises(CandidateFreezeError) as exc:
        freeze_candidate(**kw)
    assert exc.value.code == "CAND_TESTS_INCOMPLETE"


@pytest.mark.real_module
def test_freeze_candidate_rejects_stale_precommit():
    """AC-FR1400-01: pre-commit not current -> CAND_PRECOMMIT_STALE."""
    store = CandidateStore()
    kw = _valid_freeze_kwargs(store)
    kw["precommit_current"] = False
    with pytest.raises(CandidateFreezeError) as exc:
        freeze_candidate(**kw)
    assert exc.value.code == "CAND_PRECOMMIT_STALE"


@pytest.mark.real_module
def test_freeze_candidate_rejects_foreign_ancestry():
    """AC-FR1400-01: foreign commits in ancestry -> CAND_BRANCH_CONFLICT."""
    store = CandidateStore()
    kw = _valid_freeze_kwargs(store)
    kw["formal_ancestry_clean"] = False
    with pytest.raises(CandidateFreezeError) as exc:
        freeze_candidate(**kw)
    assert exc.value.code == "CAND_BRANCH_CONFLICT"


# ---------------------------------------------------------------------------
# is_stale_after
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_is_stale_after_detects_dependency_change():
    """AC-FR1400-01: any dependency digest change -> stale."""
    old = _valid_deps()
    new = DependencyManifest(
        code_digest="sha256:code-v2",  # changed
        test_digest=old.test_digest,
        design_digest=old.design_digest,
        contract_digest=old.contract_digest,
        prompt_digest=old.prompt_digest,
        config_digest=old.config_digest,
    )
    assert is_stale_after(old, new) is True


@pytest.mark.real_module
def test_is_stale_after_returns_false_for_same_deps():
    """AC-FR1400-01: same dependency set -> not stale."""
    old = _valid_deps()
    new = _valid_deps()
    assert is_stale_after(old, new) is False


# ---------------------------------------------------------------------------
# CandidateStore stale propagation
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_new_candidate_marks_old_candidate_stale():
    """AC-FR1400-01: new freeze -> old candidate + evidence stale."""
    store = CandidateStore()
    c1 = freeze_candidate(**_valid_freeze_kwargs(store))
    # Second freeze with different deps.
    kw2 = _valid_freeze_kwargs(store)
    kw2["deps"] = DependencyManifest(
        code_digest="sha256:code-v2",
        test_digest="sha256:test",
        design_digest="sha256:design",
        contract_digest="sha256:contract",
        prompt_digest="sha256:prompt",
        config_digest="sha256:config",
    )
    c2 = freeze_candidate(**kw2)
    assert store.is_stale(c1.candidate_id) is True
    assert store.is_stale(c2.candidate_id) is False
    assert store.current() == c2


@pytest.mark.real_module
def test_candidate_id_changes_when_deps_change():
    """AC-FR1400-01: same commit + different deps -> different candidate_id."""
    store = CandidateStore()
    c1 = freeze_candidate(**_valid_freeze_kwargs(store))
    kw2 = _valid_freeze_kwargs(store)
    kw2["deps"] = DependencyManifest(
        code_digest="sha256:code-v2",
        test_digest="sha256:test",
        design_digest="sha256:design",
        contract_digest="sha256:contract",
        prompt_digest="sha256:prompt",
        config_digest="sha256:config",
    )
    c2 = freeze_candidate(**kw2)
    assert c1.candidate_id != c2.candidate_id


@pytest.mark.real_module
def test_candidate_id_deterministic_for_same_commit_and_deps():
    """AC-FR1400-01: same commit + same deps -> same candidate_id (idempotent)."""
    store = CandidateStore()
    c1 = freeze_candidate(**_valid_freeze_kwargs(store))
    # Same inputs again won't be added (store marks prior as stale), but the
    # candidate_id derived from same commit+deps is identical.
    from louke.v014.fr1400_release_candidate import _candidate_id

    cid = _candidate_id("run-001", "c" * 40, _valid_deps())
    assert cid == c1.candidate_id


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR1400-01: ERROR_CODES includes all codes from interfaces.md §7."""
    expected = {
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
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
