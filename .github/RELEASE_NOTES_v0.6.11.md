# louke v0.6.11

**Patch release (cleanup).** Removes redundant "实测确认 2026-07-03 14:00 by Aaron" annotations from the 4 interactive subagent prompts and the active spec text. Anything written into the spec is assumed tested — these inline test-date annotations are noise.

## What was cleaned

### Agent prompts (4 files)
- `agents/Scout.md`
- `agents/Archer.md`
- `agents/Judge.md`
- `agents/Maestro.md`

Removed the parenthetical `(实测确认：2026-07-03 14:00 by Aaron，弹框冒泡到 Maestro 主窗口)` (and equivalent wording). The prompts now simply say "调 `question` 工具在主会话窗口弹框" without the test-date annotation.

`agents/Sage.md` was already aligned in v0.6.10 (Aaron manually edited it for consistency).

### Spec text (`v0.6-009-agent-permission-tightening/spec.md`)
Removed redundant "实测确认" annotations from:
- `scenario-0400 Maestro 自主推进` section header
- `FR-0070 交互式 subagent (v0.3.0, 基于 2026-07-03 14:00 IDE 实测)` section header
- The embedded prompt text in FR-0070.5 (which mirrors what's in `agents/Maestro.md`)

**Kept** in the spec:
- Revision history entries (lines documenting when/why the spec changed)
- The 5-item test plan in FR-0070.6 (this is an actual *test procedure* to run before each release, not a one-time confirmation)

## Why this matters

These inline test-date annotations made the prompts and spec look amateurish. A spec is a contract — anything in it has been validated. Adding "(tested on date X by person Y)" inline implies the test might be questioned later, which it shouldn't be.

## Backward compatibility

- Pure wording cleanup, no behavior change
- No tests needed (this is documentation hygiene)
- The functional behavior (subagent `question` tool bubbles to Maestro main window) is unchanged — that's still documented in the spec, just without the inline date stamp

## Install / upgrade

```bash
lk upgrade
lk --version    # lk 0.6.11
```

## License

MIT
