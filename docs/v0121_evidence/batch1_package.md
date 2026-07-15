# Batch 1 Evidence - Package Discovery (S1) & Version Convergence (S2)

- **Issues**: #174 (S1), #175 (S2)
- **Baseline**: `ed0c7b1` (Batch 0)
- **SHA range**: `ed0c7b1..HEAD`
- **Date**: 2026-07-15

---

## 1. Before/After Wheel `zipfile.namelist()` Diff

### Before (Batch 0 baseline, `pyproject.toml` packages = explicit list)

```
[tool.setuptools]
packages = ["louke", "louke._tools", "louke.web"]
```

Wheel: `louke-0.11.0-py3-none-any.whl`

Top-level `louke.<sub>` dirs in built wheel:
```
  louke/.github                            2 files
  louke/_tools                            12 files
  louke/agents                            18 files
  louke/templates                         18 files
  louke/web                               10 files
```

Expected v0.12 subpackages (all ABSENT):
```
  louke/runtime                         ABSENT
  louke/opencode                        ABSENT
  louke/web/api                         ABSENT
  louke/web/pages                       ABSENT
```

### After (Batch 1, `pyproject.toml` packages = dynamic discovery)

```toml
[tool.setuptools.packages.find]
include = ["louke*"]
```

Wheel: `louke-0.12.1-py3-none-any.whl`

v0.12 subpackages now present:
```
--- louke/runtime/ (28 files) ---
  louke/runtime/__init__.py
  louke/runtime/agent_bindings.py
  louke/runtime/capabilities.py
  louke/runtime/catalog.py
  louke/runtime/context_manifest.py
  louke/runtime/contract_gates.py
  louke/runtime/domain.py
  louke/runtime/e2e_journey.py
  ... and 20 more (events, failure_recovery, foundation, gates, etc.)

--- louke/opencode/ (7 files) ---
  louke/opencode/__init__.py
  louke/opencode/adapter.py
  louke/opencode/dispatch.py
  louke/opencode/in_memory.py
  louke/opencode/persistence.py
  louke/opencode/process.py
  louke/opencode/real.py

--- louke/web/api/ (13 files) ---
  louke/web/api/__init__.py
  louke/web/api/_common.py
  louke/web/api/_runtime_store.py
  louke/web/api/bindings.py
  louke/web/api/discussions.py
  louke/web/api/gates.py
  louke/web/api/migration.py
  louke/web/api/opencode.py
  ... and 5 more (projects, readiness, runtime, security, setup)

--- louke/web/pages/ (7 files) ---
  louke/web/pages/__init__.py
  louke/web/pages/gates.py
  louke/web/pages/migration.py
  louke/web/pages/opencode.py
  louke/web/pages/projects.py
  louke/web/pages/runs.py
  louke/web/pages/setup.py
```

---

## 2. Clean-Venv Import Smoke

Built wheel installed into a throwaway venv (no repo source on path):

```bash
python -m venv /tmp/lk-batch1-smoke-venv
/tmp/lk-batch1-smoke-venv/bin/python -m ensurepip --upgrade --default-pip
/tmp/lk-batch1-smoke-venv/bin/python -m pip install --force-reinstall \
    /tmp/lk-batch1-evidence/louke-0.12.1-py3-none-any.whl
```

Import smoke result:
```
$ /tmp/lk-batch1-smoke-venv/bin/python -c \
    "import louke.runtime, louke.opencode, louke.web.api, louke.web.pages"
rc: 0   (success - no ModuleNotFoundError)
```

---

## 3. Clean-Venv `lk --version` Result

```
$ /tmp/lk-batch1-smoke-venv/bin/lk --version
lk 0.12.1
```

```
$ /tmp/lk-batch1-smoke-venv/bin/python -c \
    "from louke import __version__; print(__version__)"
0.12.1
```

---

## 4. Git Log for This Batch

```
b838569 refactor: – #174 – S1: extract fixtures for hermetic wheel/venv reuse
93d42cf feat: green – #174 – S1: setuptools dynamic discovery so wheel includes runtime/opencode/web.api/web.pages
```

Plus (after this evidence write):
```
1249e60 feat: green – #175 – S2: converge version sources to 0.12.1
```

Note: The Red phase was not committed separately (per RGR §5.1: "Do not commit during Red phase; commit test + implementation together during Green"). The Red test file (`tests/integration/runtime/test_package_smoke.py`) was written first and confirmed failing on the baseline `pyproject.toml`, then committed together with the Green implementation.

---

## 5. Version Literal Classification Audit

Every `0.10` / `0.11` / `0.12` literal found in source was classified before any change. **No global string replacement** was performed (gap-analysis §6 #4). Only literals classified as "package version" were changed; all schema/contract/identifier versions were preserved.

### 5.1 Changed (package version -> 0.12.1)

| File:Line | Before | After | Classification |
|-----------|--------|-------|----------------|
| `pyproject.toml:7` | `version = "0.11.0"` | `version = "0.12.1"` | **Package version** (PEP 621 `[project].version`; becomes wheel METADATA `Version`) |
| `VERSION:1` | `0.10.0` | `0.12.1` | **Package version** (orphaned file; no Python consumer in `louke/`; synced to remove drift. `install.sh` uses its own `VERSION` shell var, does not read this file) |

### 5.2 Preserved (NOT package version - kept at contract value)

| File:Line | Literal | Classification | Reason kept |
|-----------|---------|----------------|-------------|
| `louke/serve.py:63` | `version = "0.12"` | **Project schema version** (in `_MINIMAL_PROJECT_TOML` template written to `.louke/project/project.toml`) | This is the schema/contract version the workspace declares, NOT the installed louke package version. Matches `.louke/project/project.toml:8` `version = "0.12"` |
| `louke/serve.py:65` | `project = "louke-v0.12"` | **Project identifier** (template default project name) | Identifier string, not a version |
| `louke/serve.py:67` | `spec_id = "v0.12-001-programmatic-workflow-runtime"` | **Spec identifier** (template default spec id) | Spec contract reference, not a package version |
| `louke/serve.py:137` | `declared_version="0.12.0"` | **Runtime declared/contract version** (passed to `RuntimeSelector`) | This is the runtime version the workspace pins, validated against the actual local runtime. NOT the pip-installed package version. Changing it would alter runtime selection semantics. |
| `louke/runtime/runtime_selector.py:75` | `_MIN_GLOBAL_VERSION = "0.12.0"` | **Minimum compatible runtime version** (global runtime compatibility floor) | Compatibility policy constant, not the package version. Only changes when the global-runtime compatibility policy changes. |
| `louke/__main__.py:220-222` | `"v0.12 commands (B8)"` etc. | **Help text label** (user-facing CLI help grouping) | Documentation label, not a version string |
| `louke/__init__.py:35` | `MIN_OPENCODE_VERSION = "1.1.1"` | **Minimum OpenCode version** (NFR-0040) | Unrelated to louke package version (OpenCode external tool) |
| `louke/__init__.py:28` | `__version__ = "0.0.0+unknown"` | **Fallback only** (when `importlib.metadata` cannot find the dist) | Not the real version; the real `__version__` is read from installed wheel METADATA at runtime. Fallback is correct (unknown when not installed). |

### 5.3 How `louke.__version__` resolves

`louke/__init__.py` reads the installed package version via `importlib.metadata.version("louke")`. This returns the `Version` from the wheel METADATA (`0.12.1` after this batch). No hardcoded version constant exists in `__init__.py`; the only literal is the `"0.0.0+unknown"` fallback for source-tree-without-install scenarios.

`lk --version` (`louke/__main__.py:154`) prints `f"lk {__version__}"`, so it inherits the METADATA version automatically.

---

## 6. Test Results

```
$ python -m pytest tests/integration/runtime/test_package_smoke.py -v
tests/integration/runtime/test_package_smoke.py::TestWheelPackageContents::test_wheel_contains_v012_subpackages PASSED
tests/integration/runtime/test_package_smoke.py::TestWheelPackageContents::test_wheel_contains_subpackage_init_modules PASSED
tests/integration/runtime/test_package_smoke.py::TestWheelPackageContents::test_clean_venv_can_import_v012_subpackages PASSED
tests/integration/runtime/test_package_smoke.py::TestVersionConvergence::test_wheel_metadata_version_matches_release PASSED
tests/integration/runtime/test_package_smoke.py::TestVersionConvergence::test_installed_dunder_version_matches_release PASSED
tests/integration/runtime/test_package_smoke.py::TestVersionConvergence::test_lk_cli_version_matches_release PASSED
6 passed
```

Unit regression (no new failures introduced):
```
$ python -m pytest tests/unit -q
397 passed, 2 skipped, 1 warning
```
(same as Batch 0 baseline; the 1 warning is a pre-existing tempfile unraisable warning)

---

## 7. Exit Conditions (gap-analysis §3 P0-1)

- [x] wheel METADATA and `lk --version` both report `0.12.1`
- [x] wheel contains runtime/opencode/web.api/web.pages
- [x] clean venv import smoke passes (`import louke.runtime, louke.opencode, louke.web.api, louke.web.pages`)
- [x] `louke.__version__ == "0.12.1"` in clean install
- [x] no global string replacement of `0.12.0` / `0.11.0` (each literal classified individually)
- [x] `serve.py` schema/contract/identifier versions preserved
- [ ] setup-only `lk serve` + `/health` smoke from installed wheel in minimal git workspace (deferred to S7 per gap-analysis issue split; this batch is S1+S2 only)

---

## 8. Notes / Assumptions

1. **VERSION file**: Audited as orphaned (no Python code in `louke/` reads it; `install.sh` uses its own shell variable named `VERSION`, not this file). Per gap-analysis §3 P0-1 ("若已废弃，应删除消费者并明确废弃"), since there are no consumers to deprecate, syncing to `0.12.1` removes the drift without breaking anything. Deleting was considered but rejected as more disruptive (external tooling/scripts may reference it).

2. **serve.py `declared_version="0.12.0"`**: This is the runtime version contract passed to `RuntimeSelector`, NOT the package version. The runtime version and package version are intentionally separate (a workspace pins its runtime version independent of which louke patch release is installed). Left unchanged.

3. **Test environment quirk**: The dev machine uses a uv-managed standalone CPython where `venv.create(with_pip=True)` crashes (ensurepip subprocess SIGABRT due to missing `DYLD_LIBRARY_PATH` for `libpython.dylib`). The test handles this by creating the venv without pip, then bootstrapping pip via `ensurepip` with the library path propagated. On standard CPython (CI) the same code path works identically. This is documented in `_subprocess_env()` and `_create_clean_venv()` docstrings.

4. **Red phase commits**: Per RGR §5.1, the Red phase test was not committed separately. The failing test was confirmed on the baseline, then committed together with the Green implementation. This matches the Devon workflow ("commit them together with the implementation during the Green phase").
