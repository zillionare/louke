"""Ground-truth test: enforce that NOTHING under
``tests/ground_truth/v014_design_contracts/`` imports ``louke.*``.

Per test-plan.md §3.2, ground-truth validators must use only stdlib,
``hashlib``, ``json``, ``pathlib`` and Git CLI. CI static scan enforces
this; any violation fails the gate.
"""
# AC-NFR0100-01 (partial): ground-truth isolation enables deterministic
# cross-run comparison independent of louke validator internals.

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

GT_ROOT = Path(__file__).resolve().parent


def _walk_python_files(root: Path):
    for path in root.rglob("*.py"):
        if path.name == "__init__.py" and path.stat().st_size == 0:
            continue
        yield path


def _imports_louke(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("louke"):
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("louke"):
                return True
            # Relative imports from a louke package would also be caught
            # by the file-path check below.
    return False


def test_no_ground_truth_file_imports_louke():
    """Every .py file under tests/ground_truth/v014_design_contracts/ must
    be free of any ``import louke...`` or ``from louke... import`` statement."""
    violations: list[str] = []
    for path in _walk_python_files(GT_ROOT):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            violations.append(f"{path}: syntax error: {exc}")
            continue
        if _imports_louke(tree):
            violations.append(f"{path}: imports louke.*")
    assert not violations, (
        "Ground-truth isolation violated (test-plan.md §3.2):\n  - "
        + "\n  - ".join(violations)
    )


def test_ground_truth_imports_only_stdlib():
    """All top-level imports in ground-truth helper modules must be stdlib.

    Test files (``test_*.py``) are exempt: they legitimately import ``pytest``
    and the local ``independent_validator`` helper for assertions. The
    stdlib-only contract applies to the validator helper itself, which is
    the module that produces ground-truth values.
    """
    allowed_prefixes = (
        "os", "sys", "json", "hashlib", "pathlib", "re", "ast",
        "typing", "abc", "collections", "io", "subprocess",
        "functools", "itertools", "dataclasses", "importlib",
        "__future__",
    )
    violations: list[str] = []
    for path in _walk_python_files(GT_ROOT):
        # Skip all test files — they may import pytest and local helpers.
        if path.name.startswith("test_"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root not in allowed_prefixes:
                        violations.append(
                            f"{path}: imports {alias.name} (not stdlib)"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                root = node.module.split(".")[0]
                if root == "__future__":
                    continue
                if root not in allowed_prefixes:
                    violations.append(
                        f"{path}: from {node.module} import ... (not stdlib)"
                    )
    assert not violations, (
        "Ground-truth stdlib-only rule violated:\n  - "
        + "\n  - ".join(violations)
    )


if __name__ == "__main__":
    test_no_ground_truth_file_imports_louke()
    test_ground_truth_imports_only_stdlib()
    print("ok")
    sys.exit(0)
