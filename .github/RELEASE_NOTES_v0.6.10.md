# louke v0.6.10

**Patch release.** Clarifies that the **only** way Maestro dispatches subagents is via OpenCode's built-in `task` tool — not via `opencode run --agent <name>`. Adds an explicit warning in `agents/Maestro.md` and a new spec section (FR-0070.7) explaining the two invocation modes and why the CLI mode is not a subagent dispatch.

## What was the confusion

On 2026-07-04, while testing Sage in `opencode run --agent sage ...` (CLI mode), Aaron observed that the `question` tool did **not** pop up in the Maestro window. Sage wrote the questions to chat instead. Aaron correctly suspected this might be a different invocation mode from the production workflow.

After investigation, the conclusion:

| Mode | How `<name>` is invoked | `<name>` role | `question` behavior |
|---|---|---|---|
| Production (subagent) | OpenCode TUI + Maestro as primary → `task` tool | subagent | Pop-up bubbles to Maestro main window |
| CLI test (NOT subagent) | `opencode run --agent <name> "..."` | primary (own session) | Pop-up in `<name>`'s own window / stdout |

Both modes are valid OpenCode features, but only the **production** mode is what `agents/Maestro.md` documents. There is no second subagent dispatch mechanism.

## What was wrong

`agents/Maestro.md` line 60+ ("你的编排模式 (Layered Orchestration)") correctly said:

> 调 `task` 工具启动对应 subagent (隔离子会话, 焦点留在你主窗口)

But the prompt did not explicitly warn **against** using `opencode run`. A user (or the LLM itself in some edge case) might confuse the two.

`agents/Sage.md` also had a slightly different wording from the other 3 interactive subagents (Scout / Archer / Judge), missing the "实测确认 2026-07-03 14:00 by Aaron" parenthetical that the other three had.

## The fix

### 1. `agents/Maestro.md` (the dispatcher's prompt)

Added a clear warning block at the top of "## 你的编排模式":

> ⚠️ **只**用 OpenCode 内置的 `task` 工具调子 agent. **不要**用 `opencode run --agent <name>` 调子 agent.
>
> 原因: `opencode run` 是 OpenCode CLI 命令, 让 `<name>` 作为 **primary** 在新 session 跑, 没有 parent 可冒泡 question. 这**不是** subagent 模式.
>
> Subagent 模式 = 通过 `task` 工具从 primary 启动. **只有这一种**, 没有第二种.

Also added a "验证 / 调试 subagent (不**走这条路径**)" subsection explaining that `opencode run` is for **standalone testing of an agent as primary**, not for subagent dispatch. To verify question bubble behavior, the user must use the TUI with Maestro as primary, not the CLI.

### 2. `agents/Sage.md` (consistency fix)

Updated to match the wording of Scout / Archer / Judge:

> **调 `question` 工具在主会话窗口弹框**（实测确认：2026-07-03 14:00 by Aaron，弹框冒泡到 Maestro 主窗口）

### 3. `v0.6-009/spec.md` FR-0070.7 (new section)

Added a new spec subsection under FR-0070 ("交互式子代理") clarifying the two invocation modes with a table comparison, and explicitly stating Louke uses only the production mode:

> Louke 唯一的 subagent 模式:
> - 生产模式 (默认, 唯一): OpenCode TUI 里 Maestro 当 primary → 调内置 `task` 工具 → 启动 subagent 隔离子会话
> - 禁止用 `opencode run --agent <name>` 调子 agent (那是 OpenCode CLI 模式, 让 `<name>` 作为 primary 在新 session 跑, 不算 subagent 模式)

## How to verify

To verify the question tool bubbles to Maestro in the production mode:

```bash
# In one terminal:
opencode   # starts TUI, default agent is maestro

# In the TUI, send a message to maestro:
"分析 spec, 用 task 启动 Sage 提 7 个问题"

# Maestro dispatches Sage via task → Sage's question tool pops up in Maestro's window
# Answer in Maestro's window → Sage continues → focus returns to Maestro
```

Do **not** use:

```bash
# WRONG — this is CLI mode, sage is primary, no bubble
opencode run --agent sage "分析 spec 提 7 个问题"
```

This CLI command was Aaron's test, not the production flow. The "no bubble" behavior is **by design** in CLI mode, not a bug.

## Backward compatibility

- Pure clarification, no behavior change
- The 12 agent prompts continue to work the same way
- No new tests needed (this is documentation/spec clarification)

## Install / upgrade

```bash
lk upgrade
lk --version    # lk 0.6.10
```

## License

MIT
