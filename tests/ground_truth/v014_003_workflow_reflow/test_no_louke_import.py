"""Ground-truth test: ensure no module in this package imports louke.

Per test-plan.md §3.2 (Ground Truth Isolation - mandatory rule):
``tests/ground_truth/v014_003_workflow_reflow/**`` may NOT
``import louke.*``.
"""
# AC-FR0100-01 (ground-truth half): isolation rule.

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE_DIR = Path(__file__).resolve().parent


def _walk_python_files():
    for path in PACKAGE_DIR.rglob("*.py"):
        if path.name.startswith("__pycache__"):
            continue
        yield path


def _imported_modules(path: Path) -> list[str]:
    """Return a list of module names imported by ``path``."""
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return []
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.append(node.module)
    return imported


def test_no_module_imports_louke():
    """No file in this package may ``import louke`` (any subpath)."""
    violations: list[tuple[str, str]] = []
    for path in _walk_python_files():
        for module in _imported_modules(path):
            if module == "louke" or module.startswith("louke."):
                violations.append((str(path.relative_to(PACKAGE_DIR)), module))
    assert not violations, (
        f"Ground-truth isolation violated: {len(violations)} import(s) of "
        f"louke.* found:\n" + "\n".join(f"  {p}: {m}" for p, m in violations)
    )


def test_only_stdlib_imports():
    """All imports must be stdlib or relative (no third-party)."""
    allowed_prefixes = (
        # stdlib
        "os",
        "sys",
        "json",
        "re",
        "hashlib",
        "pathlib",
        "ast",
        "typing",
        "dataclasses",
        "datetime",
        "collections",
        "itertools",
        "functools",
        "subprocess",
        "shutil",
        "importlib",
        "time",
        "enum",
        "__future__",
        # pytest is allowed for test files
        "pytest",
    )
    # Modules within this package (relative imports resolve to these).
    package_modules = {p.stem for p in _walk_python_files()}
    for path in _walk_python_files():
        for module in _imported_modules(path):
            if module.startswith("."):
                continue  # relative import
            top = module.split(".")[0]
            if top in allowed_prefixes:
                continue
            # Allow imports from within this package
            if top in package_modules or module in package_modules:
                continue
            # Allow relative imports within this package
            if top == "tests":
                continue
            pytest.fail(
                f"{path.relative_to(PACKAGE_DIR)} imports non-stdlib module: "
                f"{module} (top: {top})"
            )
