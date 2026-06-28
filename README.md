# holdpoint

> **Gated specs hold agents accountable.**
> **规格把关，Agent 担责。**

A spec-driven methodology where every stage transition is a machine-enforced hold point. Requirements are tracked at AC-FRXXXX-YY granularity across spec → code → test.

---

## English

### Why holdpoint?

When multiple AI agents work on the same project, things go wrong:

- Two agents edit the same file → merge conflict
- An agent makes an assumption → silent bug
- A test passes but doesn't actually verify → false confidence
- One agent finishes its work but the next can't start because the handoff isn't defined

**The failure mode isn't agents being bad at coding. It's the absence of explicit, tool-enforced handoffs between them.**

`holdpoint` defines 12 specialized agents, a 10-stage pipeline, and an `hp` CLI that makes every transition a real check — not a soft "agent reviews agent". The name is the mechanism: at every **point**, work is **held** until a different agent verifies it.

### The Pipeline

| Stage | Implementer | Reviewer | Notes |
|---|---|---|---|
| M-FOUND | Scout | Warden | Project setup + permission gate |
| M-SPEC | Sage | Lex | Spec + acceptance.md |
| M-TESTPLAN | Archer | Sage | Test plan (Sage has unique spec context) |
| M-ARCH | Archer | Prism | Architecture + interfaces |
| M-LOCK | Maestro | User | 3-signal lock (Sage quote-parser + Lex 3 stages + User confirm) |
| M-DEV | Devon | **Prism → Keeper ★** | Code + unit tests |
| M-E2E | Shield | **Prism → Keeper ★** | e2e tests (B-level) |
| M-BUGFIX | Devon | **Keeper ★** | Bug fixes |
| M-SECURITY | Judge (S-level) | User | Deep security audit |
| M-MILESTONE | Librarian | Maestro | raw → wiki distillation |

★ **HOLD POINT** — tool-enforced check (`hp` CLI returns 0/1; pipeline doesn't advance until it passes)

**Principle: implementer ≠ reviewer. Always.**

### Install

```bash
git clone https://github.com/your-org/holdpoint
cd holdpoint
pip install -e .
hp --help
```

You now have:
- `hp` CLI (32 commands across 12 agents)
- `agents/` — 14 prompt files, one per role
- `templates/` — 4 doc templates (spec, acceptance, test-plan, security-checklist)
- `tools/` — Python scripts wrapped by `hp`

### Use in Your Project

Copy the framework into your project:

```bash
cd your-project
cp -r /path/to/holdpoint/agents ./
cp -r /path/to/holdpoint/templates ./
```

Or initialize via the CLI:

```bash
hp scout foundation --repo owner/repo --version v0.1 --spec-id v0.1-001-init
# → creates .quanti-forge/project/project-info.md (TODO: rename to .holdpoint/)
# → creates .quanti-forge/project/specs/v0.1-001-init/story.md
# → opens editor for you to fill in story (interactive)
```

`hp scout foundation` walks you through:
1. Step 1 — Collect story/version/repo/DoD (interactive)
2. Step 2 — Create repo + project + permissions
3. Step 3 — Verify gh + git identity
4. Step 4 — Run `hp warden foundation-check` (F1-F11 automated checks)
5. Step 5 — Commit + push

### Use with Your AI Assistant

`agents/*.md` are written as natural-language agent prompts. Any coding agent that reads instructions can use them.

#### OpenCode

Add the framework as a plugin in `~/.config/opencode/opencode.json`:

```json
{"plugin": ["holdpoint"]}
```

#### Claude Code

Place `agents/` under `.claude/agents/` and reference each role via `--agent`:

```bash
claude --agent agents/Sage.md "interview me about user auth"
```

#### VSCode (Cursor / Continue / Copilot)

Add the agent prompts to your rules:

```json
// .continue/config.json
{
  "rules": [
    "agents/Maestro.md",
    "agents/Sage.md",
    "agents/Archer.md"
  ]
}
```

In Cursor: **Settings → Rules → Add file → `agents/Sage.md`**

### A Working Session

In a typical session with one of the above AI assistants:

```
1. hp scout foundation            # Initialize project, verify permissions
2. "You are Sage. Interview me about user auth."   # AI plays Sage role
3. hp sage commit-spec --spec ...  # Commit spec + acceptance
4. hp lex verify-acceptance       # [HOLD POINT] Different agent, tool-enforced
5. "You are Archer. Write test-plan + arch + interfaces."
6. hp archer ci-scan              # AC 引用 + 反模式 扫描
7. "You are Devon. Implement in R-G-R."
8. hp devon commit-rgr --phase red/green/refactor
9. hp keeper gate                 # [HOLD POINT] Tool-enforced commit format
10. hp judge security-audit       # [HOLD POINT] S-level security review
11. hp librarian from-raw         # Distill session → wiki
12. hp maestro status             # Check progress
```

Each `★` HOLD POINT returns 0 (pass) or 1 (fail). The pipeline doesn't advance until it passes.

### How It Works: One Spec, End to End

Say you want to build user auth:

1. **M-FOUND** (Scout) — `hp scout foundation` creates the repo, GitHub Project, and a Test Issue to verify permissions.
2. **M-SPEC** (Sage → Lex) — Sage interviews you Socratically (MFA? session timeout? rate limiting?). Lex finds 3 issues. Sage fixes, marks spec locked when **3 signals align**: `hp sage quote-check` exit 0, Lex 3 stages pass, user confirms in IDE.
3. **M-TESTPLAN** (Archer → Sage) — Archer writes `test-plan.md` with 3-layer testing strategy + AC traceability + anti-pattern rules. Sage reviews (it has unique spec context from M-SPEC).
4. **M-ARCH** (Archer → Prism) — Archer writes `architecture.md` + `interfaces.md`. Prism checks spec/code consistency.
5. **M-LOCK** — Spec locked. Implementation begins.
6. **M-DEV** (Devon → Prism → Keeper) — Devon implements in R-G-R. Each commit prefixed `test: red`, `feat: green`, `refactor`. Prism reviews (cynical + test patterns + security quick scan). Keeper runs `hp keeper gate` (commit format + tests).
7. **M-E2E** (Shield → Prism → Keeper) — Shield writes e2e (B-level, simple methods: Playwright/testclient/DB). Same Prism + Keeper.
8. **M-SECURITY** (Judge S-level → User) — `hp judge security-audit` does pattern scan + S-level semantic review. User makes final call.
9. **M-MILESTONE** (Librarian → Maestro) — `hp librarian from-raw` distills the session to wiki. `hp maestro advance --stage M-MILESTONE` closes the milestone.

Each transition is a different agent. Each hold point is tool-enforced. Each handoff is explicit.

### Comparison

| Framework | Spec role | Review model | Agent handoff | Hold point enforcement |
|---|---|---|---|---|
| **spec-kit** (GitHub) | Drives code (single agent) | None | N/A | None |
| **superpowers** (obra, 240k★) | Triggers skills | Subagent reviews | TDD + subagent | TDD (test) |
| **oh-my-openagent** (code-yeongyu, 64k★) | Guides agent | Team of agents | Parallel | Skills + hooks |
| **antigravity-awesome-skills** (1,693+ skills) | (skill library) | None | N/A | None |
| **holdpoint** | **Holds agents accountable** | **Different agent per stage** | **10 stage transitions** | **`hp` CLI tool-enforced** |

The unique claim: **gated specs hold agents accountable via hold points, not just inform them**.

### Architecture (Light)

```
  agents/*.md              templates/*.md                hp/                  tools/*.py
  (12 prompts)            (spec, acceptance,           (32 commands,         (Python scripts,
                         test-plan, security-          12 agents)           wrapped by hp)
                         checklist)
       │                       │                            │                      │
       └───────────┬───────────┴────────────┬───────────────┘                      │
                   │                        │                                      │
                   ↓                        ↓                                      ↓
            AI assistant              Tool-enforced                            wrapped by hp
         (OpenCode, Cursor,           hold points
          Claude Code,                 (hp keeper gate,
          Continue, etc.)               hp judge
                                      security-audit)

  Two-tier memory:
    .quanti-forge/raw/    →   episodic, per-agent session records
    .quanti-forge/wiki/   →   distilled knowledge, maintained by Librarian
```

- **12 agents** = implementer + reviewer per stage, all distinct
- **`hp` CLI** = tool-enforced hold points (return 0/1)
- **Two-tier memory** = `raw/` (what happened) + `wiki/` (what we know)
- **Traceability** = every test docstring must reference `AC-FRXXXX-YY`; CI scans for it

### License

MIT

---

## 中文

### 为什么是 holdpoint？

当多个 AI Agent 在同一个项目上协作时：

- 两个 Agent 改了同一个文件 → 合并冲突
- 一个 Agent 做了隐式假设 → 静默 bug
- 测试通过但没真正验证 → 假阳性
- 一个 Agent 完成了，下一个 Agent 不知道从哪接手 → 卡住

**失败模式不是 Agent 写代码不行，而是缺少显式的、工具强制的 handoff。**

`holdpoint` 定义了 12 个专业 Agent、10 阶段流水线、一个 `hp` CLI——让每次转换都是真正的检查，不是"agent 互相 review"那种软约束。名字就是机制：**在每个 point 上，工作被 hold（= 验证 + 卡点）**。

### 流水线

| 阶段 | 实施者 | 评审者 | 说明 |
|---|---|---|---|
| M-FOUND | Scout | Warden | 项目奠基 + 权限门 |
| M-SPEC | Sage | Lex | 规格 + acceptance.md |
| M-TESTPLAN | Archer | Sage | 测试计划（Sage 有独有 spec 上下文）|
| M-ARCH | Archer | Prism | 架构 + 接口 |
| M-LOCK | Maestro | 用户 | 3 信号锁定 |
| M-DEV | Devon | **Prism → Keeper ★** | 代码 + 单元测试 |
| M-E2E | Shield | **Prism → Keeper ★** | e2e 测试（B 级）|
| M-BUGFIX | Devon | **Keeper ★** | Bug 修复 |
| M-SECURITY | Judge（S 级）| 用户 | 深度安全审计 |
| M-MILESTONE | Librarian | Maestro | raw → wiki 蒸馏 |

★ **HOLD POINT**——工具强制检查（`hp` CLI 返回 0/1；不通过就不前进）

**核心原则：实施者 ≠ 评审者。始终。**

### 安装

```bash
git clone https://github.com/your-org/holdpoint
cd holdpoint
pip install -e .
hp --help
```

你会得到：
- `hp` CLI（12 agent × 32 命令）
- `agents/` — 14 个 agent prompt 文件
- `templates/` — 4 个文档模板（spec, acceptance, test-plan, security-checklist）
- `tools/` — Python 脚本，被 `hp` 包装

### 在项目中使用

把框架复制到你的项目：

```bash
cd your-project
cp -r /path/to/holdpoint/agents ./
cp -r /path/to/holdpoint/templates ./
```

或通过 CLI 初始化：

```bash
hp scout foundation --repo owner/repo --version v0.1 --spec-id v0.1-001-init
```

`hp scout foundation` 引导你完成：
1. Step 1 — 收集 story/版本号/repo 名/DoD（交互式）
2. Step 2 — 创建 repo + project + 权限
3. Step 3 — 验证 gh + git 账号一致
4. Step 4 — 跑 `hp warden foundation-check`（F1-F11 自动检查）
5. Step 5 — 提交 + push

### 与你的 AI 助手配合

`agents/*.md` 是自然语言 agent prompt。任何能读指令的 coding agent 都能用。

#### OpenCode

在 `~/.config/opencode/opencode.json` 加 plugin：

```json
{"plugin": ["holdpoint"]}
```

#### Claude Code

把 `agents/` 放到 `.claude/agents/`，通过 `--agent` 引用：

```bash
claude --agent agents/Sage.md "跟我聊用户认证"
```

#### VSCode（Cursor / Continue / Copilot）

把 agent prompt 加到 rules：

```json
// .continue/config.json
{
  "rules": [
    "agents/Maestro.md",
    "agents/Sage.md",
    "agents/Archer.md"
  ]
}
```

Cursor：**Settings → Rules → Add file → `agents/Sage.md`**

### 一个工作流

用上面任一 AI 助手，典型会话：

```
1. hp scout foundation            # 初始化项目，验证权限
2. "你是 Sage，跟我聊用户认证"    # AI 扮演 Sage
3. hp sage commit-spec --spec ...  # 提交 spec + acceptance
4. hp lex verify-acceptance       # [HOLD POINT] 不同 agent，工具强制
5. "你是 Archer，写 test-plan + arch + interfaces"
6. hp archer ci-scan              # AC 引用 + 反模式 扫描
7. "你是 Devon，用 R-G-R 实现"
8. hp devon commit-rgr --phase red/green/refactor
9. hp keeper gate                 # [HOLD POINT] commit 格式
10. hp judge security-audit       # [HOLD POINT] S 级安全审计
11. hp librarian from-raw         # 会话 → wiki
12. hp maestro status             # 进度
```

每个 `★` HOLD POINT 返回 0（通过）或 1（失败）。不通过就不前进。

### 一个 Spec 的端到端

假设要建用户认证：

1. **M-FOUND**（Scout）— `hp scout foundation` 创建 repo、GitHub Project、Test Issue 验证权限
2. **M-SPEC**（Sage → Lex）— Sage 苏格拉底式追问（MFA？session 超时？rate limiting？）。Lex 找到 3 个问题。Sage 修复后，**3 信号齐**时锁定 spec：`hp sage quote-check` exit 0 + Lex 3 阶段通过 + 用户 IDE 确认
3. **M-TESTPLAN**（Archer → Sage）— Archer 写 test-plan + 3 层测试策略 + AC 追溯 + 反模式规则。Sage 评审（有 M-SPEC 的独有上下文）
4. **M-ARCH**（Archer → Prism）— Archer 写 architecture.md + interfaces.md。Prism 查 spec/code 一致性
5. **M-LOCK**— Spec 锁定。开始实现
6. **M-DEV**（Devon → Prism → Keeper）— Devon 用 R-G-R 实现。每次 commit 前缀 `test: red` / `feat: green` / `refactor`。Prism 评审（批判 + 测试反模式 + 安全 quick scan）。Keeper 跑 `hp keeper gate`（commit 格式 + tests）
7. **M-E2E**（Shield → Prism → Keeper）— Shield 写 e2e（B 级，固定方法：Playwright/testclient/DB）。同 Prism + Keeper
8. **M-SECURITY**（Judge S 级 → 用户）— `hp judge security-audit` 做 pattern 扫描 + S 级语义审查。用户最终拍板
9. **M-MILESTONE**（Librarian → Maestro）— `hp librarian from-raw` 把会话蒸馏到 wiki。`hp maestro advance --stage M-MILESTONE` 关闭 milestone

每次转换是不同 Agent。每次 hold point 工具强制。每次 handoff 显式。

### 对比

| 框架 | spec 角色 | review 模式 | agent handoff | hold point 强制 |
|---|---|---|---|---|
| **spec-kit**（GitHub）| 驱动代码（单 agent）| 无 | N/A | 无 |
| **superpowers**（obra，240k★）| 触发 skills | subagent review | TDD + subagent | TDD（test）|
| **oh-my-openagent**（code-yeongyu，64k★）| 指导 agent | team of agents | parallel | skills + hooks |
| **antigravity-awesome-skills**（1,693+ skills）| (skill 库) | 无 | N/A | 无 |
| **holdpoint** | **让 Agent 担责** | **不同 agent per stage** | **10 阶段转换** | **`hp` CLI 工具强制** |

独特主张：**spec 通过 hold point 让 agent 担责，不只是给 agent 看**。

### 架构（简）

```
  agents/*.md              templates/*.md                hp/                  tools/*.py
  (12 prompts)            (spec, acceptance,           (32 commands,         (Python scripts,
                         test-plan, security-          12 agents)           wrapped by hp)
                         checklist)
       │                       │                            │                      │
       └───────────┬───────────┴────────────┬───────────────┘                      │
                   │                        │                                      │
                   ↓                        ↓                                      ↓
            AI 助手                    工具强制                              被 hp 包装
         (OpenCode, Cursor,           hold points
          Claude Code,                 (hp keeper gate,
          Continue 等)                   hp judge
                                      security-audit)

  两层记忆:
    .quanti-forge/raw/    →   事件级, per-agent 会话记录
    .quanti-forge/wiki/   →   蒸馏后的知识, 由 Librarian 维护
```

- **12 Agent** = 实施者 + 评审者 per stage，全不同
- **`hp` CLI** = 工具强制的 hold point（返回 0/1）
- **两层记忆** = `raw/`（发生了什么）+ `wiki/`（我们知道什么）
- **追溯** = 每个测试 docstring 必须引用 `AC-FRXXXX-YY`；CI 扫描校验

### 许可证

MIT