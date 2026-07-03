# louke v0.6.7

**Feature release.** Adds `lk agent list-models` to view all agents' `models:` chain and their current resolved model in one table.

## Highlights

- **`lk agent list-models`** — show for each of the 12 agents:
  - `models:` chain (the fallback list from frontmatter)
  - Current resolved model (the first in the chain that resolves to a real model via alias or `opencode models`)
  - `✓` cyan if resolved, `(未绑)` yellow if no model in chain resolves
- **`--unbound-only`** — only show agents that have NO resolved model (i.e., all chain entries fail to resolve)
- **`--root <path>`** — same git-or-path requirement as `lk board opencode` and `lk agent set-model` (v0.6.4)

## What's in this release

### Before (v0.6.6, multiple steps)

```bash
$ lk models list       # 列所有 abstract + resolved, 但不显示哪个 agent
# glm-5.2              ark/glm-5.2 (alias)
# deepseek-v4-flash    ark/deepseek-v4-flash
# ...

# 想知道 archer 用了哪些 model? 只能 cat agents/Archer.md
$ head -10 agents/Archer.md
# --- 手动找 models: 那一行
```

### After (v0.6.7, one command)

```bash
$ lk agent list-models
agent      | models: chain                            | current resolved
--------------+------------------------------------------+---------------------------------
archer     | glm-5.2, minimax-m3, qwen-3.7-max         | ark/glm-5.2
devon      | kimi-2.7-code, deepseek-v4-pro, ...      | ark/deepseek-v4-pro
keeper     | deepseek-v4-flash, minimax-2.7           | (未绑) ← 跑 lk models bind
maestro    | minimax-m3, glm-5.2                     | ark/minimax-m3
...
```

### `--unbound-only` for quick gap analysis

```bash
$ lk agent list-models --unbound-only
agent   | models: chain              | current resolved
--------+----------------------------+---------------------------------
keeper  | deepseek-v4-flash, ...     | (未绑) ← 跑 lk models bind
shield  | kimi-2.7-code, ...         | (未绑) ← 跑 lk models bind
```

## Use cases

- **After `lk upgrade`**: verify all agents still resolve to working models
- **Before `lk board opencode`**: spot agents that will fail at runtime
- **Debugging**: "which agent uses model X?" — `lk agent list-models` then grep
- **Bulk rebinding**: see which abstracts need binding after a model rename

## Install / upgrade

```bash
lk upgrade
lk --version    # lk 0.6.7
```

## Backward compatibility

- All v0.6.6 commands work identically
- New `lk agent list-models` is purely additive
- No dependency changes

## License

MIT
