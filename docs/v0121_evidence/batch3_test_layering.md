# Batch 3 Evidence - Test Layering Reflow (S4) & Minimal Ground Truth (S5)

- **Issues**: #177 (S4), #178 (S5)
- **Baseline**: `a321b15` (Batch 2)
- **SHA range**: `a321b15..HEAD`
- **Date**: 2026-07-15

---

## 0. AC trace

- gap-analysis §3 P1-1 (test layering vs approved test plan)
- gap-analysis §4 Batch 3 (minimal correct test layering)
- gap-analysis §6 #6 (no copying tests to inflate coverage)
- gap-analysis §6 #11 (no modifying v0.13/v0.14/v0.15 story / gap-analysis)

---

## 1. Tree comparison: `tree tests/ -L 3` before / after

### Before (baseline `a321b15`)

```
tests/
├── conftest.py
├── e2e
│   ├── ... (21 e2e files including test_v12_integration_e2e.py)
│   └── test_v12_integration_e2e.py          <-- mis-layered integration test
├── fixtures
├── integration
│   └── runtime
│       ├── test_package_smoke.py            (Batch 1)
│       └── test_routes_production.py        (Batch 2)
├── test_*.py (top-level legacy)
└── unit
```

- `tests/ground_truth/` did NOT exist.
- `tests/integration/` had no `conftest.py` and no `integration` marker registered.

### After (HEAD)

```
tests/
├── conftest.py                              (+integration marker registered)
├── e2e
│   ├── ... (20 e2e files; test_v12_integration_e2e.py REMOVED via git mv)
│   └── (no test_v12_integration_e2e.py)
├── fixtures
├── ground_truth                             <-- NEW (S5)
│   ├── __init__.py
│   ├── conftest.py                          (AST gate: rejects `import louke`)
│   ├── fixtures
│   │   ├── expected_new_feature_topology.json
│   │   └── expected_status_digests.json
│   ├── test_definition_graph.py             (7 invariants, stdlib only)
│   └── test_digest_independence.py          (4 sha256 contract checks, stdlib only)
├── integration
│   ├── conftest.py                          <-- NEW (path-based integration auto-mark)
│   └── runtime
│       ├── test_layering_smoke.py           <-- NEW (S4 state-probe)
│       ├── test_package_smoke.py
│       ├── test_routes_production.py
│       └── test_workflow_run_lifecycle.py   <-- MOVED from tests/e2e/test_v12_integration_e2e.py
├── test_*.py (top-level legacy)
└── unit
```

Key deltas:
- `git mv tests/e2e/test_v12_integration_e2e.py tests/integration/runtime/test_workflow_run_lifecycle.py` (no copy; single move, gap-analysis §6 #6)
- `tests/ground_truth/` created (did not exist before).
- `tests/integration/conftest.py` created (path-based auto-mark, mirrors `tests/e2e/conftest.py`).
- `integration` marker registered in `tests/conftest.py` (additive, one line, mirrors existing `e2e` registration).

---

## 2. pytest collection diff: `-m e2e` and `-m integration` before / after

### `-m e2e tests/e2e`

| State  | Collected |
|--------|-----------|
| Before | 197       |
| After  | 187       |

Delta: -10 (the 10 lifecycle tests moved out of `tests/e2e/`). The moved file
carried no `@pytest.mark.e2e` decorator; it was auto-marked by
`tests/e2e/conftest.py`'s path-based `pytest_collection_modifyitems`. Moving it
out of `tests/e2e/` automatically drops the e2e mark.

```
$ python -m pytest -m e2e tests/e2e --collect-only -q   (LOUKE_SKIP_LIVE_SERVER=1)
# before: 197 tests collected
# after:  187 tests collected
```

### `-m integration tests/integration`

| State  | Collected |
|--------|-----------|
| Before | 0         |
| After  | 22        |

Before: the `integration` marker was not registered, so `-m integration`
deselected everything (8 deselected). After: 22 tests collected:
- 8 (Batch 1+2: `test_package_smoke` 6 + `test_routes_production` 2)
- 10 (moved `test_workflow_run_lifecycle.py`)
- 4 (`test_layering_smoke.py` S4 state-probe)

```
$ python -m pytest -m integration tests/integration --collect-only -q
# before: no tests collected (8 deselected)
# after:  22 tests collected
```

### Moved file membership (cross-check)

```
$ python -m pytest -m integration tests/integration --collect-only -q | grep test_workflow_run_lifecycle
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_0101_workflow_run_lifecycle
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_0401_project_store_crud_via_http
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_0901_m_lock_gate_semantics
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_1001_project_listing_active_and_history
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_1101_project_creation_preview_confirm
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_1201_workflow_graph_nodes_and_edges
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_1301_agent_bindings_default_and_override
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_1501_context_manifest_event_stream
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_1601_responsibility_catalog_two_definitions
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_1701_workflow_definitions_catalog_validation

$ python -m pytest -m e2e tests/e2e --collect-only -q | grep -E 'test_v12_integration_e2e|test_workflow_run_lifecycle'
# (empty - the moved file is no longer e2e-collected)
```

---

## 3. No-regression: `pytest tests/unit tests/integration tests/ground_truth`

```
$ python -m pytest tests/unit tests/integration tests/ground_truth -q --tb=no
... (output elided) ...
430 passed, 2 skipped, 1 warning in 60.90s
```

Breakdown vs Batch 2 baseline (405 passed):
- Batch 1+2: 405 passed, 2 skipped (unchanged)
- +10 moved lifecycle tests (now in integration)
- +4 S4 layering smoke
- +11 S5 ground_truth
= 430 passed, 2 skipped.

The 2 skips are pre-existing (`test_package_smoke` markers, Batch 1).
The 1 warning is the pre-existing `test_cli_v12.py` tempfile unraisable
warning (Batch 0 baseline §0.3, Batch 1 evidence §6) - unrelated to this
change.

The moved file passes on its own at the new location:

```
$ python -m pytest tests/integration/runtime/test_workflow_run_lifecycle.py -v
collected 10 items
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_0101_workflow_run_lifecycle PASSED [ 10%]
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_0401_project_store_crud_via_http PASSED [ 20%]
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_0901_m_lock_gate_semantics PASSED [ 30%]
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_1001_project_listing_active_and_history PASSED [ 40%]
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_1101_project_creation_preview_confirm PASSED [ 50%]
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_1201_workflow_graph_nodes_and_edges PASSED [ 60%]
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_1301_agent_bindings_default_and_override PASSED [ 70%]
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_1501_context_manifest_event_stream PASSED [ 80%]
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_1601_responsibility_catalog_two_definitions PASSED [ 90%]
tests/integration/runtime/test_workflow_run_lifecycle.py::test_e2e_fr_1701_workflow_definitions_catalog_validation PASSED [100%]
============================== 10 passed in 0.14s ==============================
```

---

## 4. Git log: `git log --oneline a321b15..HEAD`

```
2c42600 feat: green – #178 – S5: minimal tests/ground_truth/ - conftest AST gate rejects louke imports (pytest_pycollect_makemodule + Collector.CollectError); test_definition_graph (7 invariants over new_feature topology fixture); test_digest_independence (4 sha256 contract checks, stdlib only); 11 tests pass, grep no-louke clean
d4ed62e refactor: – #177 – S4: ruff-format test_layering_smoke.py (collapse single-line path expr); tests still 14 passed, -m e2e 187 / -m integration 22 unchanged
d49d86a feat: green – #177 – S4: git mv test_v12_integration_e2e.py -> tests/integration/runtime/test_workflow_run_lifecycle.py; add integration conftest auto-mark + integration marker; add layering smoke (RED->GREEN); update docstrings
```

SHA range: `a321b15..2c42600`

- `d49d86a` - S4 green: RED layering smoke + `git mv` + integration conftest/marker + docstring update (Closes #177)
- `d4ed62e` - S4 refactor: ruff-format the new smoke file (no behavior change)
- `2c42600` - S5 green: ground_truth dir + AST gate + 2 fixtures + 2 test modules (Closes #178)

Red-phase note (RGR §5.1): per the Devon workflow, the RED tests were not
committed separately. The S4 layering smoke was confirmed failing on the
pre-move state (assertion: "expected test_workflow_run_lifecycle.py to exist
after the S4 move"), then committed together with the GREEN move. The S5
ground_truth gate was confirmed firing on a temporary `import louke` stub
(collection error), the stub deleted, then the real GREEN tests committed.

---

## 5. ground_truth conftest hook (source)

File: `tests/ground_truth/conftest.py`

```python
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
```

### Gate-fires sanity check (manual, per AC #178)

A temporary stub `tests/ground_truth/test_doctest_no_louke.py` containing
`import louke` was added and collected. The gate rejected it as a collection
error (not INTERNALERROR), and the 11 clean ground-truth tests still
collected. The stub was then deleted.

```
$ cat > tests/ground_truth/test_doctest_no_louke.py <<'EOF'
import louke  # noqa: F401  -- intentionally forbidden; triggers the gate


def test_stub_imports_louke_should_be_rejected() -> None:
    pass
EOF
$ python -m pytest tests/ground_truth --collect-only
...
_________ ERROR collecting tests/ground_truth/test_doctest_no_louke.py _________
ground-truth tests must not import louke (gap-analysis §3 P1-1 / issue #178): line 1: import louke
=========================== short test summary info ============================
ERROR tests/ground_truth/test_doctest_no_louke.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
===================== 11 tests collected, 1 error in 0.05s ======================
$ rm tests/ground_truth/test_doctest_no_louke.py
```

### Why `pytest_pycollect_makemodule` and not `pytest_collect_file`

An earlier attempt used `pytest_collect_file` returning a custom `Module`
subclass. That caused double collection (22 items instead of 11): the default
`pytest_collect_file` and the override both ran, each producing a collector
for the same file. `pytest_pycollect_makemodule` is the single hook the
default `pytest_collect_file` delegates to (`_pytest.python.pytest_collect_file`
calls `ihook.pytest_pycollect_makemodule(...)`), so overriding it yields
exactly one collector per file. `pytest_collectstart` was also tried but
raising there aborts the whole session (INTERNALERROR) instead of producing a
per-file collection error.

---

## 6. ground_truth no-louke check (gap-analysis §6 verification command)

```
$ grep -rn '^import louke\|^from louke' tests/ground_truth/
$ echo "rc=$?"
rc=1
```

(empty output; rc=1 = no matches = clean)

Permissive pattern (catches indented imports too):

```
$ grep -rn '(^|[[:space:]])(from|import)[[:space:]]+louke' tests/ground_truth/
$ echo "rc=$?"
rc=1
```

(empty output; clean)

AST parse check (all ground_truth test modules parse cleanly):

```
$ python -c "
import ast
from pathlib import Path
for p in Path('tests/ground_truth').rglob('*.py'):
    if 'conftest' not in p.name and 'test_' in p.name:
        ast.parse(p.read_text())
        print('parsed OK:', p)
"
parsed OK: tests/ground_truth/test_definition_graph.py
parsed OK: tests/ground_truth/test_digest_independence.py
```

Note: `tests/ground_truth/conftest.py` references the string `"louke"` in its
docstrings and in the gate-detection logic (`alias.name == "louke"`), but it
does NOT execute `import louke` or `from louke ...` -- the grep for actual
import statements returns clean. The conftest imports only `ast`, `pathlib`,
`_pytest.nodes`, and `_pytest.python` (pytest internals required to install
the collection hook), which is the minimal set needed to enforce the
no-louke invariant and is not itself a ground-truth "test module".

---

## 7. Ground-truth tests added (S5)

### 7.1 `tests/ground_truth/test_definition_graph.py` (7 tests)

Independent expected topology for the `new_feature` workflow definition, read
from a hand-authored JSON fixture (`fixtures/expected_new_feature_topology.json`).
Uses only the Python stdlib (`json`, `pathlib`). Asserts the fixture is
internally self-consistent and matches the gap-analysis contract:

- `test_fixture_shape_matches_new_feature_contract` - identity fields
- `test_node_count_is_six` - 6 nodes
- `test_edge_count_is_five` - 5 edges
- `test_terminal_node_is_complete` - terminal = `complete` (zero out-degree)
- `test_all_nodes_reachable_from_start` - no orphan required steps
- `test_max_depth_equals_edge_count_for_chain` - chain depth = 5
- `test_edges_form_single_chain` - unbranched chain

This is the ground-truth side of a drift-detection pair: the product side
(`louke.web.api._runtime_store._new_feature_definition`) must produce a
structurally equivalent graph; the matching unit test in
`tests/unit/runtime/test_fr1701_workflow_definitions.py` covers the product
side. Agreement between the two is the contract; if either changes without
the other, drift is detected.

### 7.2 `tests/ground_truth/test_digest_independence.py` (4 tests)

Independent SHA-256 digest recomputation using only `hashlib` + `json`. The
fixture `fixtures/expected_status_digests.json` holds three sample artifact
bundles and their expected digests (computed with stdlib, not imported from
louke):

- `test_digest_shape_is_sha256_hex_prefixed` - `sha256:` + 64 hex chars
- `test_digest_matches_fixture_values` - recomputed == fixture
- `test_digest_is_deterministic` - same input -> same digest
- `test_digest_is_input_shape_sensitive` - 3 distinct story digests -> 3 distinct digests

This is the ground-truth side of the digest contract pair: the product side
(`louke.runtime.contract_gates.contract_digest`) must produce identical
values; the matching unit tests in `tests/unit/runtime/test_fr0801_*` cover
the product side.

### Ground-truth test run

```
$ python -m pytest tests/ground_truth -v
collected 11 items
tests/ground_truth/test_definition_graph.py::test_fixture_shape_matches_new_feature_contract PASSED [  9%]
tests/ground_truth/test_definition_graph.py::test_node_count_is_six PASSED [ 18%]
tests/ground_truth/test_definition_graph.py::test_edge_count_is_five PASSED [ 27%]
tests/ground_truth/test_definition_graph.py::test_terminal_node_is_complete PASSED [ 36%]
tests/ground_truth/test_definition_graph.py::test_all_nodes_reachable_from_start PASSED [ 45%]
tests/ground_truth/test_definition_graph.py::test_max_depth_equals_edge_count_for_chain PASSED [ 54%]
tests/ground_truth/test_definition_graph.py::test_edges_form_single_chain PASSED [ 63%]
tests/ground_truth/test_digest_independence.py::test_digest_shape_is_sha256_hex_prefixed PASSED [ 72%]
tests/ground_truth/test_digest_independence.py::test_digest_matches_fixture_values PASSED [ 81%]
tests/ground_truth/test_digest_independence.py::test_digest_is_deterministic PASSED [ 90%]
tests/ground_truth/test_digest_independence.py::test_digest_is_input_shape_sensitive PASSED [100%]
============================== 11 passed in 0.01s ==============================
```

---

## 8. Exit conditions

### Issue #177 (S4)

- [x] `tests/integration/runtime/` exists and is now in active use
- [x] `git mv tests/e2e/test_v12_integration_e2e.py tests/integration/runtime/test_workflow_run_lifecycle.py`
- [x] moved file has no `@pytest.mark.e2e` (verified by AST scan in layering smoke); auto-marked `integration` by path
- [x] `pytest tests/integration/runtime/test_workflow_run_lifecycle.py -v` -> 10 passed
- [x] `-m e2e tests/e2e` count: 197 -> 187 (decreased by 10)
- [x] `-m integration tests/integration` count: 0 -> 22 (increased by 22)
- [x] no duplicate files (single `git mv`, gap-analysis §6 #6)
- [x] no batch move of other historical e2e files (v0.13 scope); only the one file moved
- [x] `tests/e2e/` real e2e (real_opencode, nfr0301, nfr0401, browser compat) left untouched
- [x] `integration` marker registered (additive, mirrors existing `e2e` registration)

### Issue #178 (S5)

- [x] `tests/ground_truth/` created with `__init__.py`
- [x] `tests/ground_truth/conftest.py` enforces no `import louke` / `from louke` via AST + `Collector.CollectError`
- [x] `tests/ground_truth/test_definition_graph.py` - independent topology invariants (7 tests, stdlib only)
- [x] `tests/ground_truth/test_digest_independence.py` - independent SHA-256 contract (4 tests, stdlib only)
- [x] `pytest tests/ground_truth -v` -> 11 passed
- [x] gate-fires sanity check documented (temporary `import louke` stub -> collection error)
- [x] `grep -rn '^import louke\|^from louke' tests/ground_truth/` -> empty (clean)
- [x] `tests/conftest.py` not modified in a way that affects other layers (only additive marker registration)

---

## 9. Notes / assumptions

1. **Marker registration location**: The `integration` marker is registered in
   `tests/conftest.py` (the existing `e2e` / `real_opencode` registration
   site), not in `pyproject.toml [tool.pytest.ini_options]`. This mirrors the
   existing pattern and keeps all marker registration in one place. The
   pyproject.toml was not modified (gap-analysis §6: only touch pyproject
   pytest config if needed; the conftest approach already works for `e2e`).

2. **Auto-mark vs decorator**: The moved lifecycle file carries no
   `@pytest.mark.integration` decorator. It is auto-marked by
   `tests/integration/conftest.py`'s path-based `pytest_collection_modifyitems`
   (mirroring `tests/e2e/conftest.py`). This is consistent with the existing
   e2e auto-mark convention and avoids editing every test function. The AC
   phrasing "remove the e2e marker (if any); change to integration" is
   satisfied: the file had no e2e *decorator* (only the path-based auto-mark,
   which is automatically dropped by moving out of `tests/e2e/`), and it is
   now integration-marked by the path-based auto-mark in its new location.

3. **Test function names not renamed**: The 10 moved test functions retain
   their `test_e2e_fr_*` names. Renaming them would change pytest node IDs
   that downstream AC scanners / historical M-E2E evidence may reference, and
   is out of scope for "test layering reflow" (the AC asks for a file move +
   marker change, not a function rename). The names are historical labels;
   the *layer* is now integration. v0.13 reflow may rename them.

4. **FR-1301 wrapper retained**: The moved file's `test_e2e_fr_1301_*` test
   builds a dedicated wrapper app instead of going through the production
   `create_app` bindings route. The production bindings route shadow was
   fixed in Batch 2 / issue #176, but the wrapper is retained here to keep
   the bindings lifecycle self-contained alongside the other FR lifecycle
   tests in this file. The Batch 2 production-route integration test
   (`test_routes_production.py`) is the authoritative production-path probe.
   This was documented in the moved file's docstring.

5. **ground_truth drift-detection pairing**: The ground-truth tests assert
   "we expect this shape/value". The product-side counterparts
   (`tests/unit/runtime/test_fr1701_workflow_definitions.py` for the graph,
   `tests/unit/runtime/test_fr0801_*` for the digest) assert "the runtime
   produces this shape/value". Agreement between the two is the contract.
   This batch does NOT add a cross-layer assertion that runs both in one
   test (that would require the ground-truth test to import louke, which is
   forbidden); the pairing is structural and will be enforced by CI running
   both layers.

6. **Digest fixture values are part of the contract**: Once committed, the
   expected digests in `expected_status_digests.json` are frozen. If the
   runtime's `contract_digest` algorithm ever changes, the unit test
   (product side) will fail against the runtime, and the ground-truth test
   (independent reimplementation) will still pass against the fixture -- the
   divergence surfaces as a unit-test failure, not a silent agreement.
