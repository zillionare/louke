"""Ground-truth test layer: independent expected-value calculations only.

The ground-truth layer (gap-analysis §3 P1-1 / §4 Batch 3, issue #178 S5) must
NOT import ``louke.*``. Its entire purpose is to provide an *independent*
expected value that product code is then checked against, so that a passing
test proves the product is correct rather than merely that the test agrees
with itself. If a ground-truth test imported ``louke``, a bug in the product
could silently satisfy the "expected" value and the test would still pass.

This conftest enforces that invariant at collection time: every Python module
under ``tests/ground_truth/`` is wrapped in :class:`_GroundTruthModule`, whose
``collect()`` parses the module AST and raises
:class:`_pytest.nodes.Collector.CollectError` if any ``import louke`` or
``from louke ...`` statement is present. The offending file is reported as a
collection error (never silently collected or run); clean ground-truth modules
collect and run normally.

Implementation note: the gate hooks ``pytest_pycollect_makemodule`` (the
single entry point the default ``pytest_collect_file`` delegates to) rather
than ``pytest_collect_file`` itself, so there is exactly one module collector
per file (no double collection).
"""

from __future__ import annotations

import ast
from pathlib import Path

from _pytest.nodes import Collector
from _pytest.python import Module

_GROUND_TRUTH_ROOT = Path(__file__).resolve().parent


def _is_ground_truth_module(path: str) -> bool:
    """Return True if ``path`` lives under the ground-truth test root."""
    try:
        Path(path).resolve().relative_to(_GROUND_TRUTH_ROOT)
    except (ValueError, OSError):
        return False
    return True


def _louke_imports(source: str) -> list[str]:
    """Return human-readable descriptions of any louke imports in ``source``.

    Walks the module AST and reports ``import louke`` and ``from louke ...``
    statements. Returns an empty list when the source is clean. Only static
    ``Import`` / ``ImportFrom`` nodes are inspected; a dynamic
    ``importlib.import_module("louke")`` would itself be a code smell worth
    flagging in review and is intentionally not chased here.
    """
    tree = ast.parse(source)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "louke" or alias.name.startswith("louke."):
                    hits.append(f"line {node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "louke" or (
                node.module is not None and node.module.startswith("louke.")
            ):
                hits.append(f"line {node.lineno}: from {node.module} import ...")
    return hits


class _GroundTruthModule(Module):
    """Module collector that rejects louke imports before collecting items.

    Subclassing ``Module`` and overriding ``collect`` lets pytest report the
    rejection as a per-file collection error (via ``Collector.CollectError``)
    rather than aborting the whole session, so clean ground-truth modules in
    the same directory still collect and run.
    """

    def collect(self):  # type: ignore[override]
        source = Path(self.fspath).read_text(encoding="utf-8")
        offenders = _louke_imports(source)
        if offenders:
            raise Collector.CollectError(
                "ground-truth tests must not import louke "
                "(gap-analysis §3 P1-1 / issue #178): " + "; ".join(offenders)
            )
        return super().collect()


def pytest_pycollect_makemodule(module_path, parent):
    """Wrap ground-truth ``.py`` modules in :class:`_GroundTruthModule`.

    Args:
        module_path: the :class:`pathlib.Path` of the module being collected.
        parent: the parent collector.

    Returns:
        A :class:`_GroundTruthModule` for files under ``tests/ground_truth/``;
        falls through to the default ``Module`` otherwise.
    """
    if _is_ground_truth_module(str(module_path)):
        return _GroundTruthModule.from_parent(parent, path=module_path)
    return Module.from_parent(parent, path=module_path)
