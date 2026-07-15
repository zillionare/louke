# Batch 5 Evidence — Server Boot Smoke (S7) + Chromium Product Journey (S8)

- **Issue**: #180
- **Spec**: v0.12-001-programmatic-workflow-runtime, gap-analysis §4 Batch 5 / §3 P0-3 + P1-2
- **Date**: 2026-07-15
- **Commit range**: `d9c4bf0..46c78fb` (4 commits: 2 green + 2 refactor)
- **Branch**: `main` (project `release_branch = "main"` per project.toml)

---

## 1. S7 — installed-wheel `lk serve` boot smoke

### Goal

Prove that a clean venv which installed the built wheel can actually boot
`lk serve` and serve `/health`. The source tree masks packaging bugs
because Python sees files on disk; a clean wheel install has no such
fallback, so a missing runtime dependency or a broken console-script entry
point fails here regardless of how the source tree looks.

This is the gap-analysis §3 P0-1 exit condition for the v0.12.1 release
gate.

### Test artifact

`tests/integration/runtime/test_server_boot.py` — 3 tests in
`TestInstalledLkServeBoot`:

1. `test_installed_lk_serve_starts_and_health_200` — `/health` returns 200
   with `status=ok` from a clean-wheel `lk serve` boot.
2. `test_installed_lk_serve_health_has_spec_id` — `/health` payload carries
   the v0.12 spec id (proves the real louke app is serving, not a stub).
3. `test_installed_lk_serve_setup_only_redirects_to_setup` — GET `/` in
   setup-only mode returns 303 redirect to `/setup`.

Shared hermetic fixtures live in `tests/integration/runtime/conftest.py`
(session-scoped `built_wheel`, function-scoped `clean_venv`, plus the
`build_wheel` / `create_clean_venv` / `install_wheel` helpers).

### Sample run (S7)

```
PORT: 55357
PID: 45422
HEALTH: {"status": "ok", "spec_id": "v0.12-001-programmatic-workflow-runtime"}
ROOT_STATUS: 303
ROOT_LOCATION: /setup
KILLED, rc: -15
```

- Server PID: `45422` (terminated with SIGTERM, rc `-15`, no zombie).
- Bound port: `55357` (free port discovered via transient socket).
- `/health` JSON: `{"status": "ok", "spec_id": "v0.12-001-programmatic-workflow-runtime"}`.
- `/` redirect: `303` -> `/setup` (setup-only mode, fresh project root).
- Teardown: SIGTERM -> `wait()` -> reaped; no leftover `lk serve` process.

### Hermeticity

- Wheel built via `python -m build --wheel` into a per-session temp dir.
- Clean venv created with `venv.create(with_pip=False)` + `ensurepip`
  bootstrap; `PYTHONPATH` stripped from the spawned `lk` env so the
  installed wheel is the only source of `louke`.
- `DYLD_LIBRARY_PATH` propagated so the venv python can resolve
  `libpython3.11.dylib` on macOS standalone CPython builds.
- Teardown is in a `try/finally` so the server is always killed even if an
  assertion fails.

---

## 2. S8 — Chromium product journey

### Goal

One supported-browser (Chromium) product journey against an installed-wheel
server, per gap-analysis §3 P1-2 / §4 Batch 5. Not a multi-browser matrix.

### Test artifact

`tests/e2e/test_v012_chromium_journey_e2e.py` — 1 test:

- `test_chromium_setup_journey` (marked `@pytest.mark.chromium_e2e`)

Journey:

1. Build wheel, install in clean venv, spawn `lk serve` (setup-only mode).
2. Launch Chromium via Playwright (headless).
3. Wait for `/health` to confirm server up.
4. Navigate to `/` -> assert redirect to `/setup`.
5. Assert setup page title contains `setup`.
6. Locate first-user form via semantic selectors (`#name`, `#credential`,
   `get_by_role("button", name="Create first user")`).
7. Fill form, submit.
8. Assert post-submit page still renders the setup shell (no 5xx error).
9. Screenshot captured to `tmp_path/chromium_setup_journey.png`.
10. Browser closed + server killed (always, in `finally`).

Selector strategy: semantic only (`#id`, `get_by_role`, title text). No
CSS classes, no pixel/layout assertions — those belong to the v0.14 UI
rewrite (gap-analysis §5.2).

### Chromium status

- **Status**: installed; journey PASSES.
- Detection: `chromium_is_installed()` checks that Playwright's expected
  `chromium.executable_path` actually exists on disk, not just that some
  `chromium-*` directory is cached. This catches the common version-mismatch
  case (older Chromium cached, newer Playwright expects a newer build).
- Installed executable:
  `~/Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`
- Playwright library version: expects `chromium-1228` (installed via
  `python -m playwright install chromium`).
- Skip path: when Chromium is not installed, the test skips with
  `"Chromium not installed; run python -m playwright install chromium to
  enable the S8 product journey test"`. The skip is an environment
  condition, NOT a product pass.

### Sample run (S8)

```
tests/e2e/test_v012_chromium_journey_e2e.py::test_chromium_setup_journey PASSED [100%]
1 passed in 13.52s
```

- Server: `lk serve` on a free port from a clean-wheel install.
- Browser: Chromium 1228, headless.
- `/` -> `/setup` redirect verified in-browser via `page.url`.
- Setup form filled (`aaron` / `secret-passphrase`) and submitted.
- Post-submit title still contains `setup` (no error page).
- Screenshot captured (asserted to exist in `tmp_path`).
- Teardown: browser closed, server SIGTERM'd, no leftover processes.

---

## 3. Test tree

```
tests/integration/runtime/
    conftest.py                       (shared hermetic wheel/venv fixtures)
    test_ci_contract.py
    test_layering_smoke.py
    test_package_smoke.py
    test_routes_production.py
    test_server_boot.py               (NEW — S7)
    test_workflow_run_lifecycle.py

tests/e2e/
    test_v012_chromium_journey_e2e.py (NEW — S8)
```

---

## 4. Marker registration

`pyproject.toml [tool.pytest.ini_options].markers`:

```toml
markers = [
    "e2e: end-to-end browser test (Playwright)",
    "integration: integration test (real TestClient / temp store / HTTP), not a browser E2E (see gap-analysis §3 P1-1 / issue #177)",
    "real_opencode: L3 smoke test that requires a live OpenCode provider (run only when LOUKE_RUN_REAL_OPENCODE=1 and real credentials are set)",
    "chromium_e2e: single-Chromium product journey against an installed-wheel server (gap-analysis §4 Batch 5 / issue #180); skips when Chromium is not installed",
]
```

`pytest --markers` confirms `chromium_e2e` is registered (no
`PytestUnknownMarkWarning`).

Selection:
- Default `tests/e2e` run: `chromium_e2e` is NOT auto-applied (only the
  path-based `e2e` marker is, via `tests/e2e/conftest.py`). The journey is
  collected under `-m e2e` but only runs if Chromium is installed; it can
  be excluded with `-m "not chromium_e2e"`.
- Dedicated run: `pytest -m chromium_e2e tests/e2e/test_v012_chromium_journey_e2e.py`.

---

## 5. Test counts

- S7: 3 tests added (`tests/integration/runtime/test_server_boot.py`).
- S8: 1 test added (`tests/e2e/test_v012_chromium_journey_e2e.py`).
- Total new: 4 tests.
- Regression check:
  - `tests/integration` (full): 35 passed (was 32 before Batch 5).
  - `tests/e2e -m "not chromium_e2e"` with `LOUKE_SKIP_LIVE_SERVER=1`:
    180 passed, 7 skipped, 1 deselected — no regressions.
  - `tests/integration/runtime/test_package_smoke.py` (Batch 1 territory):
    6 passed — unaffected by the new shared conftest (local module fixtures
    override the conftest's via pytest precedence).

---

## 6. Commit range

| SHA      | Phase    | Scope                                                                 |
| -------- | -------- | --------------------------------------------------------------------- |
| `d9c4bf0` | green    | S7: installed wheel boots + health 200 + setup_only redirect         |
| `7e4740b` | refactor | S7: simplify get_status with http.client; hoist imports; teardown    |
| `261ead4` | green    | S8: chromium_e2e marker + journey test (skip when no browser)         |
| `46c78fb` | refactor | S8: hoist imports, ruff-format all batch5 tests; marker registered   |

---

## 7. Constraints honored

- Test-first: S7 RED confirmed (server failed to boot due to missing
  `DYLD_LIBRARY_PATH` in the spawned env — a real packaging/env issue the
  test caught); S8 RED confirmed (initially failed because cached Chromium
  version did not match Playwright's expected version).
- No copying of tests; shared helpers extracted into
  `tests/integration/runtime/conftest.py`.
- No global refactor; only new test files + one marker line in pyproject.
- Forbidden paths untouched: `serve.py`, `__main__.py`, `louke/web/`,
  `tests/unit/`, `.github/workflows/*`, Batch 1-4 territory.
- User uncommitted files untouched: `gap-analysis.md`, `louke/agents/Story.md`,
  v0.13/v0.14/v0.15 specs, `docs/workflow.md`.
- Honest reporting: Chromium must be explicitly installed
  (`python -m playwright install chromium`); a missing browser skips with a
  clear message and is NOT reported as a pass.

---

## 8. Blockers

None.
