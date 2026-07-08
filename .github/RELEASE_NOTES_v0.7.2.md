# louke v0.7.2

**Hotfix — `lk --version` reported a stale version on v0.7.1.** No code
changes from v0.7.1.

## What was the bug

The v0.7.0 / v0.7.1 wheels shipped with `louke/__init__.py` containing a
hardcoded `__version__ = "0.6.14"`. The wheel's package metadata
(`pyproject.toml` overridden at build time) correctly said 0.7.0 / 0.7.1,
so `importlib.metadata.version("louke")` returned the right value — but
`lk --version` reads `__version__` from the source module, not the
package metadata, so it printed the stale 0.6.14.

```
$ pip show louke | head -2
Name: louke
Version: 0.7.1                     # correct (from wheel METADATA)

$ lk --version
lk 0.6.14                          # wrong (from hardcoded __init__.py)
```

This wasn't caught by the release workflow because there was no test
asserting `lk --version` matches the wheel version.

## What changed

| File | Change |
|---|---|
| `louke/__init__.py` | `__version__` now reads from `importlib.metadata.version("louke")`; falls back to `0.0.0+unknown` only if the package is not installed (source tree import). The hardcoded literal is gone, so the constant can no longer drift from the released version. |
| `pyproject.toml` | `0.7.1` → `0.7.2` |
| `VERSION` | `0.7.1` → `0.7.2` |

No other source files in `louke/` or `agents/` were touched.

## Why v0.7.2 instead of overwriting v0.7.1

PyPI does not allow re-uploading a wheel with the same version
(PEP 592 / 658). The release workflow uses `twine upload --skip-existing`,
so even forcing a re-push would be a no-op. The clean path is a new
version number; the release notes are now done correctly under the new
version.

## Verification after upgrade

```bash
pip install --upgrade louke        # → 0.7.2
lk --version                        # → lk 0.7.2   (was: lk 0.6.14)
python -c "import importlib.metadata as m; print(m.version('louke'))"   # → 0.7.2
python -c "import louke; print(louke.__version__)"                     # → 0.7.2
```

All four commands must agree.

## Going forward

- `louke/__version__` is now derived from package metadata; it cannot
  drift unless the wheel is built with a different `version` than the
  metadata reports (which the release workflow guards against by
  syncing `pyproject.toml` to the tag before building).
- A test will be added in a follow-up to assert `lk --version` equals
  the wheel version, so this class of bug is caught by CI.
