# louke v0.6.8

**Bugfix release.** `lk agent set-model` (added in v0.6.6) raised `TypeError: 'bool' object is not callable` when the abstract was already bound to an alias (no need for interactive bind) and probe ran successfully. The `ok` function imported from `louke._color` was shadowed by a local `ok` variable that captured the boolean return of `_probe_or_skip`.

## Bug

```python
from ._color import ok   # function

# in cmd_set_model:
if not args.no_probe:
    ok = _probe_or_skip(...)   # ← overwrites: ok is now a bool
    if not ok:
        ...
print(f'{ok(f"...")}')   # ← TypeError: ok is bool, not callable
```

### Reproduction (v0.6.6 and v0.6.7)

```bash
$ lk agent set-model devon minimax-m3
✓ devon.md: models[0] kimi-2.7-code -> minimax-m3
  验证 ark/minimax-m3 ...
  ✓ 可用
Traceback (most recent call last):
  ...
  File ".../louke/agent.py", line 338, in cmd_set_model
    print(f'{ok(f"{abstract} -> {resolved} (已绑定)")}')
TypeError: 'bool' object is not callable
```

Only triggered when:
- Abstract already has an alias in `~/.louke/models.json` (no interactive bind needed)
- Probe runs and succeeds (or user picks `a` to force after fail)
- The post-bind "已绑定" print fires

The interactive bind path was unaffected (different variable scope).

## Fix

Rename the boolean variable to `probed` to avoid shadowing the imported `ok` function:

```python
if not args.no_probe:
    probed = _probe_or_skip(resolved, False, allow_skip=True)
    if not probed:
        print(f'{warn(f"{resolved} probe 失败但已绑, 继续 (可能运行时失败)")}')
print(f'{ok(f"{abstract} -> {resolved} (已绑定)")}')   # ok is the function again
```

## Install / upgrade

```bash
lk upgrade
lk --version    # lk 0.6.8
```

## Backward compatibility

- Pure bugfix, no behavior change beyond the crash
- All v0.6.7 commands work identically

## License

MIT
