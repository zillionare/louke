"""Ground-truth test: verify all 36 AC IDs are referenced by test files.

Walks ``tests/integration/v014_003_workflow_reflow`` and
``tests/e2e/v014_003_workflow_reflow`` to confirm every AC ID has at
least one test file referencing it.
"""
# AC-FR0100-01 (ground-truth half): independent AC coverage check.

from __future__ import annotations

from pathlib import Path


from .independent_validator import REQUIRED_AC_IDS, collect_test_ac_ids

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_PATHS = [
    REPO_ROOT / "tests" / "integration" / "v014_003_workflow_reflow",
    REPO_ROOT / "tests" / "e2e" / "v014_003_workflow_reflow",
]


def test_all_36_ac_ids_have_at_least_one_test_reference():
    """Every required AC ID must be referenced in at least one test file."""
    test_paths = [Path(p) for p in TEST_PATHS]
    coverage = collect_test_ac_ids(test_paths)
    missing = REQUIRED_AC_IDS - set(coverage.keys())
    assert not missing, f"{len(missing)} AC IDs have no test references:\n" + "\n".join(
        f"  {ac_id}" for ac_id in sorted(missing)
    )


def test_ac_references_are_in_test_files_only():
    """AC IDs must be referenced from ``tests/integration`` or ``tests/e2e``."""
    coverage = collect_test_ac_ids([Path(p) for p in TEST_PATHS])
    for ac_id, files in coverage.items():
        for file_path in files:
            assert "tests/" in str(file_path), (
                f"AC {ac_id} referenced from non-test path: {file_path}"
            )


def test_ac_reference_count_distribution():
    """Each AC ID should have at least 1 reference (sanity check)."""
    coverage = collect_test_ac_ids([Path(p) for p in TEST_PATHS])
    for ac_id in REQUIRED_AC_IDS:
        assert ac_id in coverage, f"AC {ac_id} has no references"
        assert len(coverage[ac_id]) >= 1, (
            f"AC {ac_id} has only {len(coverage[ac_id])} reference(s)"
        )
