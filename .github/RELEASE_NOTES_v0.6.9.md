# louke v0.6.9

**Redesign release.** `lk agent set-model` (added in v0.6.6) now writes **directly** to the output file (`.opencode/agents/<name>.md`), not the source. This is a temporary override that takes effect immediately and survives until the next `lk board opencode` run.

## Why this change

In v0.6.6-0.6.8, `lk agent set-model` modified the source file `agents/<name>.md`. This had two problems:
1. **No project-local source by design**: `lk init` no longer copies agents (per upcoming v0.6-010 design), so `set-model` had no project-local target.
2. **Permanent changes are wrong for the use case**: The actual reason to use `set-model` is **temporary model switching** (model too expensive, or busy right now), not permanent customization. The user wants the change to take effect immediately and not be permanent.

## New behavior (v0.6.9)

`lk agent set-model <name> <abstract>`:
1. **Resolves** the abstract to a real `provider/model-id`:
   - `~/.louke/models.json` alias → use it
   - Else → interactive bind (Levenshtein-ranked `opencode models` candidates)
2. **Probes** the resolved model to verify it's callable (skippable with `--no-probe`)
3. **Writes** the resolved `provider/model-id` directly to the `model:` line in `.opencode/agents/<name>.md`
4. **Done** — no `lk board opencode` re-run; the change is effective immediately for OpenCode

## Usage

```bash
# 临时切 archer 到 glm-5.2
$ lk agent set-model archer glm-5.2
✓ glm-5.2 -> ark/glm-5.2 (alias)
✓ archer.md: model -> ark/glm-5.2 (临时, 下次 lk board opencode 会覆盖)

# 模型太贵, 临时换 minimax-m3
$ lk agent set-model archer minimax-m3 --no-probe
✓ archer.md: model -> ark/minimax-m3 (临时, ...)

# 撤销 (跑 board 重生, 用 source 覆盖)
$ lk board opencode

# 看现状
$ lk agent list-models
agent      | models: chain                   | current resolved
archer     | glm-5.2, minimax-m3, qwen-3...  | ark/glm-5.2  ← source 里的第一项
```

## Flags

- `--no-probe`: skip the `opencode run --model <m> ping` check
- `--root <path>`: same git-or-path requirement as `lk board opencode`
- `--dry-run`: show what would change

**Removed**: `--no-regen` (no longer relevant — set-model never regenerates)

## Backward compatibility

- `lk agent set-model` is now **write-only on output**, not source
- For projects with local source (legacy `lk init` with agents copied): set-model change will be lost on next `lk board opencode` (by design — temporary)
- All other `lk agent` subcommands (`lint`, `list-models`, per-agent commands) unchanged

## Install / upgrade

```bash
lk upgrade
lk --version    # lk 0.6.9
```

## License

MIT
