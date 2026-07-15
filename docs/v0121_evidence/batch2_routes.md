# Batch 2 Evidence - Production Route Precedence (S3)

- **Issue**: #176 (S3)
- **Baseline**: `5115565` (Batch 1)
- **SHA range**: `5115565..HEAD`
- **Date**: 2026-07-15

---

## 1. Before/After Probe Table

Probes go through the **top-level** `louke.web.app.create_app(tmp_path)` (not a
sub-app import), with a shared `WorkflowRunStore` injected into the four v0.12
sub-apps. `POST /api/runtime/bindings/runs` creates a real run; the remaining
bindings probes use the returned `run_id`.

### Bindings endpoints (the shadowed set)

| Method | Path                                       | Before (Batch 0/1) | After (Batch 2) |
|--------|--------------------------------------------|--------------------|-----------------|
| POST   | `/api/runtime/bindings/runs`               | 404 NOT_FOUND      | **201**         |
| GET    | `/api/runtime/bindings/devon?run_id={id}`  | 404 NOT_FOUND      | **200**         |
| PUT    | `/api/runtime/bindings/devon?run_id={id}`  | 404 NOT_FOUND      | **200**         |
| GET    | `/api/runtime/bindings/devon/audit?run_id={id}` | 404 NOT_FOUND | **200**         |

Before source: `docs/v0121_evidence/batch0_baseline.txt` §0.5.
After source: live probe via `TestClient(create_app(tmp_path))` on HEAD.

### Wide-mount bare-prefix endpoints (unchanged, out of scope)

These bare prefixes (`GET /api/runtime`, `GET /api/setup`, ...) return 404 both
before and after because the sub-apps have **no internal `/` route** (their
routes are `/runs`, `/status`, `/preview`, etc.). This is correct routing
behavior, not a shadow bug. Adding a fake `/` route to the sub-apps is
explicitly forbidden by issue #176 ("不得通过给 `/api/runtime` 子 app 增加假路由").
Only `GET /api/readiness` returns 200 because its sub-app has a `/` route.

| Method | Path              | Before | After | Note                         |
|--------|-------------------|--------|-------|------------------------------|
| GET    | `/api/readiness`  | 200    | 200   | has internal `/` route       |
| GET    | `/api/runtime`    | 404    | 404   | no internal `/` route (correct) |
| GET    | `/api/setup`      | 404    | 404   | no internal `/` route (correct) |
| GET    | `/api/migration`  | 404    | 404   | no internal `/` route (correct) |
| GET    | `/api/security`   | 404    | 404   | no internal `/` route (correct) |
| GET    | `/api/opencode`   | 404    | 404   | no internal `/` route (correct) |
| GET    | `/api/gates`      | 404    | 404   | no internal `/` route (correct) |
| GET    | `/api/projects`   | 404    | 404   | no internal `/` route (correct) |

---

## 2. Mount Order Diff

```diff
--- a/louke/web/app.py
+++ b/louke/web/app.py
@@ -129,10 +129,15 @@ def create_app(
             ),
             Route("/api/events", endpoint=api_events, methods=["GET"]),
             # === v0.12 mounts ===
+            # Mount order matters: Starlette matches Mounts in declaration order
+            # and a wider prefix shadows any longer prefix declared after it.
+            # ``/api/runtime/bindings`` MUST precede ``/api/runtime`` or every
+            # bindings request is handed to the runtime sub-app (which has no
+            # ``bindings`` internal route) and returns 404. See #176.
             Mount("/api/projects", app=projects_app),
+            Mount("/api/runtime/bindings", app=bindings_app),
             Mount("/api/runtime", app=runtime_app),
             Mount("/api/gates", app=gates_app),
-            Mount("/api/runtime/bindings", app=bindings_app),
             Mount("/api/opencode", app=opencode_app),
             Mount("/api/readiness", app=readiness_app),
             Mount("/api/setup", app=setup_app),
```

**Root cause**: Starlette matches `Mount` entries in declaration order and
consumes the whole remaining path. With `/api/runtime` declared before
`/api/runtime/bindings`, every `/api/runtime/bindings/...` request was handed
to `runtime_app` (which has no `bindings` internal route) and returned 404.

**Fix**: move `Mount("/api/runtime/bindings", ...)` before
`Mount("/api/runtime", ...)`. No sub-app route changes, no fake routes added.

---

## 3. Test Output

### 3.1 New tests (RED -> GREEN)

File: `tests/integration/runtime/test_routes_production.py`

```
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0
configfile: pyproject.toml
plugins: anyio-4.14.2, base-url-2.1.0, playwright-0.8.0
collecting ... collected 2 items

tests/integration/runtime/test_routes_production.py::TestBindingsRoutesReachableViaCreateApp::test_bindings_routes_reachable_via_create_app PASSED [ 50%]
tests/integration/runtime/test_routes_production.py::TestMountOrderLongerPrefixFirst::test_mount_order_longer_prefix_first PASSED [100%]

========================= 2 passed in 0.10s ===============================
```

RED (before fix) - both tests failed with messages pointing at the shadow:
- `POST /api/runtime/bindings/runs returned 404 - the bindings sub-app is shadowed by the wider /api/runtime Mount`
- `longer prefix '/api/runtime/bindings' (index 3) is declared AFTER wider prefix '/api/runtime' (index 1)`

GREEN (after fix) - both tests pass.

### 3.2 No-regression run (tests/unit + tests/integration/runtime)

```
$ python -m pytest tests/unit tests/integration/runtime -q --tb=no
.................................................ss..................... [ 17%]
........................................................................ [ 35%]
........................................................................ [ 53%]
........................................................................ [ 70%]
........................................................................ [ 88%]
...............................................                          [100%]
405 passed, 2 skipped, 1 warning in 61.36s
```

The 2 skips are pre-existing (`test_package_smoke` markers). The 1 warning is
pre-existing (`test_cli_v12.py` tempfile cleanup, unrelated to this change).

### 3.3 e2e bindings test (FR-1301 wrapper-based) still passes

```
$ python -m pytest tests/e2e/test_v12_integration_e2e.py -q --tb=short
..........                                                               [100%]
10 passed in 0.10s
```

---

## 4. Git Log

```
$ git log --oneline 7a66911..HEAD
b581144 refactor: – #176 – S3: extract _Probe type alias, tighten failure message formatting
8f61c86 feat: green – #176 – S3: reorder Mount so /api/runtime/bindings precedes /api/runtime; add production route probe + precedence smoke
5115565 v0.12.1 Batch 1: shadow-copy stage-results to docs/v0121_evidence (tracked)
```

SHA range: `5115565..b581144`

- `8f61c86` - Green: test (RED->GREEN) + Mount reorder fix
- `b581144` - Refactor: extract `_Probe` type alias, tighten failure message formatting

---

## 5. AC Trace

- **gap-analysis §3 P0-2**: `/api/runtime/bindings` shadowed by `/api/runtime` -> FIXED
- **gap-analysis §4 Batch 2**: route precedence -> DONE
- **gap-analysis §6 #5**: no fake route on `/api/runtime` sub-app -> COMPLIANT (only Mount order changed)
- **Issue #176 AC**:
  - [x] Test-first: `tests/integration/runtime/test_routes_production.py` written, failed RED, passes GREEN
  - [x] Uses top-level `louke.web.app.create_app` (not a sub-app import)
  - [x] Precedence smoke: `test_mount_order_longer_prefix_first` statically asserts longer-prefix-first invariant
  - [x] Mount order adjusted: 4 bindings endpoints return 201/200 (not 404)
  - [x] No fake route added to `/api/runtime` sub-app
  - [x] No wrapper-test bypass
