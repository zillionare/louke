# louke v0.6.2

**UX polish release.** Adds interactive `lk models bind` for resolving unresolved abstract model names, ANSI color codes for status output, and a spinner for slow subprocess calls (opencode models, auth.json read).

## Highlights

- **`lk models bind <abstract>` (no `<full>`)** enters an interactive flow: lists the most relevant `opencode models` ranked by token-overlap with the abstract name, lets the user pick by number or type a custom `provider/model`. Falls back to listing auth providers from `~/.local/share/opencode/auth.json` if `opencode` CLI is not installed.
- **`lk models bind --all-unresolved`** walks through every unresolved abstract in source `agents/*.md` one by one. Useful after a fresh `lk init` or when adopting new source files.
- **Color codes** for ✓/✗/⚠ status, bold stage headings, dim secondary text, and the `[1/5]` step indicators. Auto-disabled when stdout is not a TTY (so scripts and CI logs stay clean).
- **Spinner** (`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`) for the two slow subprocess calls: `opencode models` and `auth.json + cost index` read.
- **`lk board opencode`** now ends with an actionable hint when it finds unbound abstracts in the output: lists each agent + abstract and suggests `lk models bind <abstract>` (interactive) or `lk models bind <abstract> <provider>/<model>` (direct).

## What's in this release

### Interactive `lk models bind`

Before v0.6.2, the only way to bind an abstract was:
```
lk models bind kimi-2.6 ark/kimi-k2.6
```

But for users who don't know which provider/model to use (or which real names exist in their `opencode` config), this required reading docs or running `opencode models` separately.

v0.6.2 adds an interactive flow:
```
$ lk models bind kimi-2.6
ℹ INFO kimi-2.6 ⚠ 未找到匹配 (8 个 unresolved 之一)
  opencode models: 64 个, 与 kimi-2.6 相关 4 个:
   1. ark/kimi-k2.6
   2. opencode/kimi-k2.6
   3. opencode/kimi-k2.5
   4. opencode/kimi-k2.7-code
   0. 自定义 provider/model
   q. 跳过

  → 选择 [1-64/0/q]: 1
✓ OK kimi-2.6 -> ark/kimi-k2.6 (写入 ~/.louke/models.json)
```

Ranking uses token-overlap (split abstract on `-`, drop pure-digit and `vN` parts, score each opencode model by how many parts appear in the model name, sort by score desc then alphabetical). This is robust to naming-style mismatches like `kimi-2.6` (abstract) vs `kimi-k2.6` (real).

For batch use:
```
$ lk models bind --all-unresolved
ℹ INFO 发现 8 个 unresolved abstract: deepseek-v4-flash, deepseek-v4-pro, glm-5.2, ...

[1/8]
ℹ INFO deepseek-v4-flash ⚠ 未找到匹配 (8 个 unresolved 之一)
  ...
[8/8]
ℹ INFO qwen-3.7-max ⚠ 未找到匹配 (1 个 unresolved 之一)
  ...
```

Falls back to listing auth providers (from `auth.json`) when `opencode` CLI is not installed, so users without `opencode` can still see which providers they have keys for and type `provider/model` manually.

### Color codes

All status output uses ANSI color codes that auto-disable when stdout is not a TTY:

| Element | Color |
|---|---|
| ✓ success | green |
| ✗ failure | red |
| ⚠ warning | yellow |
| ℹ info | cyan |
| Stage headings `[1/5]` | cyan |
| Secondary text (path, hints) | dim |
| Spinner | cyan |

### Spinner

Two subprocess calls are wrapped with a spinner (auto-disabled when not a TTY):
- `opencode models` (was ~2-3s silent wait)
- `auth.json + cost index` read

Example:
```
[2/5] 查询 opencode models + 解析 provider/model bind
      用户级 alias: /Users/.../.louke/models.json
      项目级 alias: /Users/.../millionaire/.louke/models.json
      调用 opencode models (N=5 abstract names)...
  ⠹ 查询 opencode models          ← spinner
      opencode models 返回 64 个 model
```

### `lk board opencode` unbound hint

When the output file has `model: <abstract>` (no provider prefix), that model is unusable. v0.6.2 detects this and prints a hint at the end:

```
[5/5] 完成: 生成 12 个 OpenCode agent -> /Users/.../millionaire/.opencode/agents

⚠ WARN 2 个 abstract 未绑定 (output model 没 provider 前缀, OpenCode 用不起来):
  - minimax-2.7
  - qwen-3.7-max

ℹ INFO 修复: lk models bind <abstract> <provider>/<model> 或 lk models bind <abstract> (交互式)
      交互式会列出 64 个 opencode model 供选择
```

## Backward compatibility

- `lk models bind <abstract> <full>` (direct bind, 2 positional args) still works exactly as before. New behavior only triggers when `<full>` is omitted.
- `lk models bind` (no args) used to error; now runs batch interactive.
- `lk upgrade`, `lk board opencode`, `lk models doctor`, `lk models list`, `lk agent lint` — all unchanged in behavior; only cosmetic color codes added.
- No new dependencies (ANSI codes only).

## Install / upgrade

```bash
# Upgrade (PyPI)
lk upgrade

# Or with specific index
lk upgrade --index https://pypi.org/simple/

# Verify
lk --version    # lk 0.6.2
```

## License

MIT
