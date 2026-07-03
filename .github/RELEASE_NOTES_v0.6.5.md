# louke v0.6.5

**Patch release.** `lk models bind` (interactive and `--all-unresolved` batch modes) now probes the selected model via `opencode run --model <m> ping` before saving the alias. If the probe fails (key expired, model deprecated, provider offline, 30s timeout), the user is prompted to retry / skip / force.

## Highlights

- **Probe before save**: when user picks a candidate (or types a custom `provider/model`), louke runs `opencode run --model <m> "ping"` and reports `✓ 可用` or `✗ 不可用`.
- **Interactive recovery** on probe failure: `[r]` retry, `[s]` skip (don't bind), `[a]` force (bind anyway, may fail at runtime).
- **Spinner** during probe (`probe <model>`) — auto-disabled in non-TTY.
- **No regression** in happy path: if probe passes (the common case), behavior is identical to v0.6.4. If `opencode` CLI is not installed, `probe_model` returns `False` and user is prompted (typically user picks `a` to force).

## What's in this release

### Before (v0.6.4, blind save)

```
$ lk models bind kimi-2.6
  ...
  1. ark/kimi-k2.6          ← 排第一 (Levenshtein 距离最小)
  0. 自定义
  q. 跳过

  → 选择: 1
✓ OK kimi-2.6 -> ark/kimi-k2.6 (写入 ~/.louke/models.json)
# ↑ 但 ark/kimi-k2.6 的 key 已过期, 实际跑 agent 时会 401
# 只能等 lk board opencode 失败再 debug
```

### After (v0.6.5, probe before save)

```
$ lk models bind kimi-2.6
  ...
  1. ark/kimi-k2.6
  0. 自定义
  q. 跳过

  → 选择: 1
  验证 ark/kimi-k2.6 ...
  ⠹ probe ark/kimi-k2.6
  ✗ 不可用 (probe 失败 / key 过期 / 模型下架 / 30s 超时)
  [r] 重试 / [s] 跳过 (不绑) / [a] 强制绑? [r/s/a]: s
  跳过 kimi-2.6
# ↑ 用户立刻知道 ark/kimi-k2.6 不可用, 不会被骗保存
```

### `lk models bind --all-unresolved` (batch)

Same per-abstract probe + prompt. Default behavior:
- For 8 unresolved abstracts: 8 probes × ~5-10s each = 40-80s total
- User can skip or force at each step

## Backward compatibility

- `lk models bind <abstract> <full>` (direct, no probe) — unchanged.
- Interactive flow: probe is now mandatory but user can force-skip via `a`.
- `opencode` not installed: probe returns `False` immediately (no subprocess cost), user picks `a` to force.

## Install / upgrade

```bash
lk upgrade
lk --version    # lk 0.6.5
```

## License

MIT
