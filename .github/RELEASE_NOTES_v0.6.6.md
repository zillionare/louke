# louke v0.6.6

**Feature release.** Adds `lk agent set-model <name> <abstract>` for one-command model changing with built-in interactive binding and probe validation. Previously required 3+ steps: edit source → `lk models bind` → `lk board opencode`.

## Highlights

- **`lk agent set-model <name> <abstract>`** — change an agent's primary model in one command. The flow:
  1. Updates `agents/<name>.md` `models[0]` to the new abstract
  2. Resolves the abstract to a real model:
     - If `~/.louke/models.json` has an alias → use it
     - Else → run interactive `lk models bind` (Levenshtein-sorted candidates + probe before save)
  3. Probes the resolved model to verify it's actually callable
  4. (Default) Regenerates `.opencode/agents/<name>.md` via `lk board opencode`
- **`--dry-run`**: shows what would change without modifying files
- **`--no-probe`**: skip the model probe (faster but unsafe)
- **`--no-regen`**: don't auto-rerun `lk board opencode` (for batch operations)
- **`--root <path>`**: same git-or-path requirement as `lk board opencode` (v0.6.4)
- **Reuses the v0.6.5 probe flow**: if probe fails, prompts `[r]` retry / `[s]` skip / `[a]` force-bind

## What's in this release

### Usage

```bash
# 改 archer 用的模型为 glm-5.2 (改 source + 交互式 bind + probe + 自动重生 board)
lk agent set-model archer glm-5.2

# 看看会改什么, 不实际改
lk agent set-model archer glm-5.2 --dry-run

# 改完不自动重生 board (手工控制)
lk agent set-model archer glm-5.2 --no-regen

# 跳过 probe (不推荐, 除非已确认 model 可用)
lk agent set-model archer glm-5.2 --no-probe

# 非 git 目录: 显式指定
lk agent set-model archer glm-5.2 --root /path/to/louke-project
```

### Example flow (full)

```bash
$ lk agent set-model archer kimi-2.6
ℹ archer.md: models[0] glm-5.2 -> kimi-2.6
⚠ kimi-2.6 未绑定, 进入交互式...
ℹ INFO kimi-2.6 ⚠ 未找到匹配 (4 个 unresolved 之一)
  opencode models: 64 个, 与 kimi-2.6 相关 4 个:
   1. ark/kimi-k2.6
   2. opencode/kimi-k2.6
   3. opencode/kimi-k2.5
   4. opencode/kimi-k2.7-code
   0. 自定义 provider/model
   q. 跳过

  → 选择: 1
  验证 ark/kimi-k2.6 ...
  ⠹ probe ark/kimi-k2.6
  ✗ 不可用 (probe 失败 / key 过期 / 模型下架 / 30s 超时)
  [r] 重试 / [s] 跳过 (不绑) / [a] 强制绑? [r/s/a]: a
  ⚠ 强制保存, OpenCode 实际用时可能失败
✓ OK kimi-2.6 -> ark/kimi-k2.6 (写入 ~/.louke/models.json)
[5/5] 完成: 生成 12 个 OpenCode agent -> /Users/.../millionaire/.opencode/agents
```

## Install / upgrade

```bash
lk upgrade
lk --version    # lk 0.6.6
```

## Backward compatibility

- All v0.6.5 commands work identically
- New `lk agent set-model` is purely additive
- Source file format unchanged: still `models:` field with abstract names

## License

MIT
