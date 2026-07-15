# v0.12.1 Batch 4 - CI unit+integration+coverage+package-smoke

- **Issue**: #179 (S6: CI runs unit+integration+coverage from current checkout)
- **Spec ref**: gap-analysis §3 P0-3, P1-1, §4 Batch 4, §6 #8
- **Baseline SHA**: `6c2e309` (Batch 3 head)
- **Date**: 2026-07-15

## 1. ci.yml `test` job step list - BEFORE (at `6c2e309`)

```
- name: Checkout
- name: Setup Python ${{ matrix.python-version }}
- name: Install build tooling
- name: Run pre-commit on all files
- name: Sync .github resources into package
- name: Build wheel/sdist
- name: Install wheel into a clean venv
- name: "Smoke test: lk --help"
- name: Install bats-core + pyyaml for bats tests
- name: Run bats suite
```

Observations (gap-analysis §3 P0-3 / Batch 0 §0.9):
- No `pytest` invocation anywhere.
- No coverage measurement.
- No package import smoke beyond `lk --help`.
- No `lk --version` assertion.

## 2. ci.yml `test` job step list - AFTER (at `c1ef7bf`)

```
- name: Checkout
- name: Setup Python ${{ matrix.python-version }}
- name: Install build tooling
- name: Run pre-commit on all files
- name: Sync .github resources into package
- name: Build wheel/sdist
- name: Install wheel into a clean venv
- name: Install test dependencies                                      [NEW]
- name: Run unit + integration + ground_truth with coverage            [NEW]
- name: "Package smoke: import v0.12 subpackages in installed wheel"   [NEW]
- name: "Package smoke: lk --version in installed wheel"               [NEW]
- name: "Smoke test: lk --help"
- name: Install bats-core + pyyaml for bats tests
- name: Run bats suite
```

New step bodies:

```yaml
- name: Install test dependencies
  run: python -m pip install pytest pytest-cov

- name: Run unit + integration + ground_truth with coverage
  run: |
    python -m pytest tests/unit tests/integration tests/ground_truth \
      --cov=louke.runtime --cov-report=term-missing --cov-report=xml -q

- name: "Package smoke: import v0.12 subpackages in installed wheel"
  run: |
    /tmp/lk-venv/bin/python -c "import louke.runtime, louke.opencode, louke.web.api, louke.web.pages, louke.cli_v12; print('OK')"

- name: "Package smoke: lk --version in installed wheel"
  run: /tmp/lk-venv/bin/lk --version | grep "0.12.1"
```

Design notes:
- The four new steps run **after** wheel build+install and **before** the
  existing `lk --help` smoke and BATS suite, matching the job spec order.
- Coverage target is `--cov=louke.runtime`; the gate threshold
  (`fail_under = 95` in `pyproject.toml [tool.coverage.report]`) is **not
  lowered** (§6 #8).
- BATS suite is retained (v0.5 commit-policy / gap-analysis Batch 4).
- `pytest` and `pytest-cov` are installed into the runner Python (the same
  interpreter that builds the wheel), not into `/tmp/lk-venv`, because the
  test sources live in the checkout, not in the installed wheel.

## 3. Local run: pytest + coverage

Command (matches the CI step, with `--cov-report=term` for console):

```
python -m pytest tests/unit tests/integration tests/ground_truth \
  --cov=louke.runtime --cov-report=term -q
```

Final lines:

```
--------------------------------------------------------------
TOTAL                                       2459    103    96%
Required test coverage of 95.0% reached. Total coverage: 95.81%
440 passed, 2 skipped, 1 warning in 53.15s
```

- **440 passed, 2 skipped** - no regressions vs Batch 0 baseline (397 unit + 190 e2e;
  the count changed because Batch 3 moved/restructured tests into
  `tests/integration/` and added `tests/ground_truth/`).
- **Coverage: 95.81%** of `louke.runtime` - above the 95% gate.
- The 95% gate (`fail_under = 95`) was **not** modified.

## 4. Local run: `lk --version` from clean venv

```bash
python -m build --wheel --outdir dist
python -m venv /tmp/lk-batch4-smoke
/tmp/lk-batch4-smoke/bin/python -m pip install --force-reinstall dist/louke-0.12.1-*.whl
/tmp/lk-batch4-smoke/bin/lk --version
```

Output:

```
lk 0.12.1
```

Package import smoke from the same clean venv:

```
/tmp/lk-batch4-smoke/bin/python -c "import louke.runtime, louke.opencode, louke.web.api, louke.web.pages, louke.cli_v12; print('OK')"
OK
```

This is the S1/S2 exit condition (gap-analysis §3 P0-1): the installed
wheel, not the source tree, supplies the v0.12 subpackages.

## 5. pytest marker registration

Before this batch, markers (`e2e`, `integration`, `real_opencode`) were
registered only in `tests/conftest.py` via `pytest_configure`. They are
now also registered under `[tool.pytest.ini_options]` in `pyproject.toml`,
making them visible to `pytest --markers`, IDE tooling and `-m` selection
without depending on conftest collection order.

```toml
[tool.pytest.ini_options]
markers = [
    "e2e: end-to-end browser test (Playwright)",
    "integration: integration test (real TestClient / temp store / HTTP), not a browser E2E (see gap-analysis §3 P1-1 / issue #177)",
    "real_opencode: L3 smoke test that requires a live OpenCode provider (run only when LOUKE_RUN_REAL_OPENCODE=1 and real credentials are set)",
]
```

The conftest-side registration is left in place (harmless duplication; it
predates this batch and removing it is outside the permitted scope).

## 6. louke-ci.yml - status quo and decision

### Current state (NOT modified in v0.12.1)

`.github/workflows/louke-ci.yml` installs louke from **PyPI**, not from the
current checkout:

```yaml
- run: pip install louke
- name: AC traceability scan
  run: |
    if [ -n "${SPEC_ID:-}" ]; then
      lk agent archer ci-scan --spec "$SPEC_ID"
    elif [ -d .louke/project/specs ]; then
      for spec in .louke/project/specs/*; do
        [ -d "$spec" ] || continue
        lk agent archer ci-scan --spec "$(basename "$spec")"
      done
    else
      echo "No .louke specs found; skipping louke ci-scan"
    fi
```

### Problem

`pip install louke` may install a **different (older) version** from PyPI
than the current checkout. The AC traceability scan then runs against a
`lk` binary that does not match the source under review, so it cannot
prove the current commit is releasable.

### Decision: leave as-is in v0.12.1, record as v0.13 follow-up

Rationale:
1. This job is a **secondary** gate (AC traceability scan), not a release
   gate. Its purpose is backward-compatibility scanning, not release
   integrity.
2. Changing it to install from the current checkout wheel requires
   restructuring the job (checkout, build, install) and validating that
   `lk agent archer ci-scan` works against the local wheel - this is
   scope creep for v0.12.1 (gap-analysis §4 Batch 4 only requires the
   primary `ci.yml` to run unit/integration/coverage/package-smoke).
3. gap-analysis §3 P0-3 explicitly allows either fixing louke-ci.yml or
   "明确说明该 job 只验证向后兼容而非当前构建" (explicitly document
   that this job only verifies backward compatibility, not the current
   build). This evidence file serves as that explicit documentation.

**Follow-up**: v0.13 should make `louke-ci.yml` install from the current
checkout wheel (or `pip install .`) so the AC scan runs against the code
under review.

## 7. Contract test

`tests/integration/runtime/test_ci_contract.py` (10 tests) statically
asserts the workflow contract so a future edit that silently drops a gate
fails in CI rather than only being noticed at release time:

- `TestCIWorkflowContract` (7 tests):
  - ci.yml file exists
  - ci.yml runs `pytest tests/unit tests/integration tests/ground_truth`
  - ci.yml measures `--cov=louke.runtime`
  - ci.yml installs `pytest-cov`
  - ci.yml smoke-imports all v0.12 subpackages from the wheel
  - ci.yml asserts `lk --version` reports `0.12.1`
  - ci.yml retains the BATS suite
- `TestPytestMarkerRegistration` (3 tests, parametrized):
  - pyproject.toml registers `e2e` marker
  - pyproject.toml registers `integration` marker
  - pyproject.toml registers `real_opencode` marker

## 8. git log

```
$ git log --oneline 6c2e309..HEAD
c1ef7bf feat: green – #179 – S6: add unit+integration+coverage+package-smoke steps to ci.yml
```

(Refactor commit with marker registration + this evidence file follows.)

## 9. Acceptance criteria checklist (issue #179)

- [x] After build wheel, before bats: step running
      `python -m pip install pytest pytest-cov`
- [x] After build wheel, before bats: step running
      `pytest tests/unit tests/integration tests/ground_truth --cov=louke.runtime --cov-report=term-missing --cov-report=xml -q`
- [x] Coverage gate NOT lowered (still `fail_under = 95`; local run 95.81%)
- [x] Pytest markers (`e2e`, `integration`, `real_opencode`) registered in
      `[tool.pytest.ini_options]` in pyproject.toml
- [x] Package smoke step: import v0.12 subpackages from installed wheel
- [x] Package smoke step: `lk --version` = `0.12.1` from installed wheel
- [x] BATS job NOT deleted
- [x] pre-commit job NOT broken (not touched)
- [x] Coverage gate NOT lowered
- [x] louke-ci.yml: left as-is, limitation explicitly documented (§6 above)
- [x] No user uncommitted file modified
