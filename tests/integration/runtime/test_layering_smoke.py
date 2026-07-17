"""S4 layering smoke - probes the test-layering state for issue #177.

This is a state-probe (gap-analysis §3 P1-1 / §4 Batch 3). It asserts the
*target* test-layering invariant:

  - ``tests/integration/runtime/`` exists and the runtime import path works;
  - the v0.12 integration lifecycle test lives at
    ``tests/integration/runtime/test_workflow_run_lifecycle.py`` (moved out of
    ``tests/e2e/``);
  - the moved file is no longer collected by ``pytest -m e2e``.

Before the ``git mv`` (RED) the lifecycle-test assertion fails because the
file still lives at ``tests/e2e/test_v12_integration_e2e.py``. After the move
(GREEN) all assertions pass. The probe itself is path/AST based and does not
import the lifecycle test, so it cannot pass spuriously.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_INTEGRATION_RUNTIME = _REPO_ROOT / "tests" / "integration" / "runtime"
_E2E_LIFECYCLE_OLD = _REPO_ROOT / "tests" / "e2e" / "test_v12_integration_e2e.py"
_INTEGRATION_LIFECYCLE_NEW = _INTEGRATION_RUNTIME / "test_workflow_run_lifecycle.py"


def test_integration_runtime_dir_exists() -> None:
    """``tests/integration/runtime/`` must exist (S4 directory root)."""
    assert _INTEGRATION_RUNTIME.is_dir(), (
        f"expected directory {_INTEGRATION_RUNTIME} to exist"
    )


def test_runtime_import_path_works() -> None:
    """The runtime subpackage must be importable from the integration layer."""
    import louke.runtime.catalog  # noqa: F401
    import louke.runtime.contract_gates  # noqa: F401
    import louke.runtime.store  # noqa: F401


def test_v12_lifecycle_test_lives_in_integration() -> None:
    """The v0.12 lifecycle test must have been moved to the integration layer.

    RED before ``git mv``: the old path exists and the new path does not.
    GREEN after the move: the new path exists and the old path does not.
    """
    assert _INTEGRATION_LIFECYCLE_NEW.is_file(), (
        f"expected {_INTEGRATION_LIFECYCLE_NEW} to exist after the S4 move"
    )
    assert not _E2E_LIFECYCLE_OLD.is_file(), (
        f"old e2e path {_E2E_LIFECYCLE_OLD} must not linger "
        "(gap-analysis §6 #6: no duplicate files to inflate coverage)"
    )


def test_moved_test_does_not_carry_e2e_marker() -> None:
    """The moved lifecycle test must not declare or carry an ``e2e`` marker.

    Parses the moved file's AST and rejects any ``pytest.mark.e2e`` reference,
    so the file is selectable only via ``-m integration`` (path-based
    auto-mark) and not via ``-m e2e``.
    """
    if not _INTEGRATION_LIFECYCLE_NEW.is_file():
        pytest.skip("lifecycle test not yet moved (RED state); issue #177")
    source = _INTEGRATION_LIFECYCLE_NEW.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "e2e":
            pytest.fail(
                "moved lifecycle test still references `.e2e` marker; "
                "an integration test must not be e2e-marked"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
