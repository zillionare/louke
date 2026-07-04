# louke v0.6.13

**Critical bugfix release.** `lk models doctor` (introduced in v0.6.0) crashed with `TypeError: 'bool' object is not callable` whenever any model was bound to an alias. This is the **same pattern** of bug as v0.6.8 (which fixed it in `lk agent set-model`), but `cmd_doctor` was missed in that fix. GLM code review on 2026-07-04 caught it.

## What was the bug

In `models.py:cmd_doctor`:

```python
from ._color import ok, fail, warn, info, Spinner  # ok is a function
...
ok = True                                           # ← L337: shadows the function
fixes = {}
for name in used_models():
    status, resolved, note = _classify(name, models, auth, costs)
    if status == 'alias':
        print(f'{ok()} {name} -> {resolved} (alias)')  # ← TypeError: ok is bool
        continue
```

The local variable `ok = True` shadowed the imported `ok` function. On the first iteration where `status == 'alias'`, `ok()` tried to call `True` as a function → `TypeError: 'bool' object is not callable`.

## When it triggered

- User has **any** alias in `~/.louke/models.json` (the default configuration after `lk upgrade` from older versions)
- `lk models doctor` is the v0.6-008 FR-0201 core verification command — high frequency of use

So the bug effectively **broke `lk models doctor` for all users with aliases**, which is most users.

## Why v0.6.8 didn't catch this

v0.6.8 release notes:

> Rename the boolean variable to `probed` to avoid shadowing the imported `ok` function

The fix was correctly applied to `cmd_set_model` (`agent.py:331`), but `cmd_doctor` (`models.py:337`) was missed. The pattern is the same; the fix was not applied codebase-wide. **A grep would have caught it**:

```bash
grep -n "ok = " louke/*.py
# Should return zero results
```

(After this fix: 4 results remaining in `models.py:399, 415` and `scout.py:315`, all in functions that import `ok` as `_ok` or use `ok` only as a bool — no shadowing.)

## The fix

In `models.py:cmd_doctor` (4 occurrences):

```python
- ok = True
+ all_ok = True
  ...
-     ok = False
+     all_ok = False
  ...
-     ok = False
+     all_ok = False
  ...
- return 0 if ok else 1
+ return 0 if all_ok else 1
```

The shadowed variable is renamed to `all_ok` (boolean) so `ok()` (the imported function) is preserved.

## Regression test

Added `tests/test_models_doctor.bats` with 3 test cases:

1. **Single alias** — `lk models doctor` runs without TypeError when 1 alias exists (the bug case)
2. **Multiple aliases** — 3 aliases, all show `✓` correctly
3. **All unresolved** — no aliases, no `ok()` calls, smoke test for the all-unresolved path

Verified the test **catches the bug**: with the old code (v0.6.12), all 3 tests fail with `'bool' object is not callable`; with the fix, all 3 pass.

## Other fixes in this release

- `models.py:490` — dead code in ternary `len(candidates) if opencode_ok else len(auth) if not opencode_ok else "N"` simplified to `len(candidates) if opencode_ok else len(auth)`. The `else "N"` branch was unreachable.
- `agents/Maestro.md:97` — markdown bold typo `(不**走这条路径)` → `(**不**走这条路径)`. No functional change, just render correctness.

## Other GLM findings (deferred, not blocking)

GLM also identified (full review in `.louke/review-v0.6.6-v0.6.12.md`):

- **A6-5** (🚨): `lk agent set-model` and `lk agent list-models` lack spec FR/AC coverage
- **A8-3** (🚨): No dedicated bats tests for set-model / list-models (only the doctor test is added in this release)
- **A7-1 / A9-2** (💡): Root-resolution logic duplicated in 3 places; could be extracted to `_common.py`
- **A3-2** (💡): `chain` truncation at 30 chars; could add `--no-truncate`

These are tracked for follow-up versions. Critical path is the `cmd_doctor` fix.

## Install / upgrade

```bash
lk upgrade
lk --version    # lk 0.6.13
lk models doctor   # should now run without crashing
```

## License

MIT
