# Dev Agents — TDD 驱动的多 Agent 开发方法

## 概述

这组 Agent 共同实现了 **TDD-first 多 Agent 协作开发方法**：每个阶段由实施者执行、评审者把关，由 Maestro 统一协调推进。核心原则是 **先写测试，后写实现**，所有产出必须满足退出条件才能推进到下一阶段。

开发流程参考文档：
- 飞书（单源权威）：https://qcnj2a4uoe9q.feishu.cn/wiki/FBNqwXG27iVnemkJN34cRNdvnOh
- 本地镜像：`~/.agents/rules/develop_process.md`

## Agent 花名册与阶段映射

```
Story/PRD ── Scout → Warden ─────┐
Interview ── Sage → Lex ─────────┤
Issue Tracker ── Clerk → Auditor ─┤
Test Plan ── Probe → Judge ──────┤
执行规划 ── Archer → Cynic ─────┤
任务执行 ── Forge → Prism → Keeper ─┤  ← Red-Green-Refactor 循环
验收 ── Herald → Arbiter ────────┘
Bug 修复 ── Hunter → Shield（独立流程，同样 R-G-R）

全程协调：Maestro
```

| 阶段 | 实施者 | 评审者 | 一句话任务 | 流程章节 |
|------|--------|--------|-----------|----------|
| 全程 | **Maestro** | — | 协调各 Agent，驱动流程推进 | 全局 |
| Story/PRD | **Scout** | **Warden** | 勘探前置条件 / 守门确认退出条件 | 1.1 |
| Interview | **Sage** | **Lex** | 苏格拉底式追问产出 spec / 审核可追踪可断言 | 1.2.1 |
| Issue Tracker | **Clerk** | **Auditor** | spec 拆为 GitHub issue / 审计可追溯性 | 1.2.2 |
| Test Plan | **Probe** | **Judge** | 设计分层测试计划 / 裁判可执行性 | 1.2.3 |
| 执行规划 | **Archer** | **Cynic** | 任务划分与测试关联 / 批评审核完整性 | 1.3 |
| 任务执行 | **Forge** | **Prism** → **Keeper** | R-G-R 循环锻造代码 / 棱镜审视代码质量 / 守住完成门禁 | 1.4 |
| 验收 | **Herald** | **Arbiter** | 汇总全量测试与覆盖 / 终审裁决 | 1.5 |
| Bug 修复 | **Hunter** | **Shield** | TDD 猎杀 Bug / 守护无回归 | 2 |

## Agent → 模型映射能力矩阵

> 更新时间：2026-05-22
> 模型排名基于发布时点的编码能力评估，后续模型发布后需重新评估。

### 模型能力档位（2026.05.22）

| 档位 | 全局版 | 国内版 | 特点 |
|------|--------|--------|------|
| S | opus-4.7 | deepseek-v4-pro | 深度推理、架构决策、复杂逻辑 |
| A | gpt-5.5 | kimi-k2.6 | 强编码、长上下文、综合能力强 |
| A- | gpt-5.4 | qwen3.6-plus | 稳定编码、较低成本 |
| B | deepseek-v4-pro | glm-5.1 | 编码可用、成本更低 |
| C | deepseek-v4-flash | deepseek-v4-flash | 快速、低成本、适合轻量任务 |
| C+ | gemini-3.5-flash | — | 快速、多模态、低成本 |

### 全局版（不限模型）

| Agent | 角色 | 推荐模型 | 理由 |
|-------|------|---------|------|
| **Maestro** | 协调/路由 | gpt-5.5 | 需综合判断与多步规划，A 档平衡能力与速度 |
| **Scout** | 勘探 | deepseek-v4-flash | 事实性检查，C 档足够 |
| **Warden** | 守门 | deepseek-v4-flash | 结构化验证，C 档足够 |
| **Sage** | 苏格拉底追问 | opus-4.7 | 需深度理解与创意提问，S 档最佳 |
| **Lex** | spec 审核 | gpt-5.4 | 规则性审核，A- 档够用 |
| **Clerk** | issue 组织 | deepseek-v4-flash | 结构化操作，C 档足够 |
| **Auditor** | 追溯审计 | deepseek-v4-flash | 交叉验证，C 档足够 |
| **Probe** | 测试设计 | gpt-5.5 | 需求覆盖推理，A 档 |
| **Judge** | 测试评审 | gpt-5.4 | 规则性评审，A- 档够用 |
| **Archer** | 执行规划 | gpt-5.5 | 需架构推理与依赖分析，A 档 |
| **Cynic** | 规划批评 | gpt-5.5 | 需逆向思维与漏洞发现，A 档 |
| **Forge** | TDD 编码 | opus-4.7 | 编码核心，S 档最可靠 |
| **Prism** | 代码审查 | gpt-5.5 | 多角度审查需综合推理，A 档 |
| **Keeper** | 质量门禁 | deepseek-v4-flash | 结构化检查，C 档足够 |
| **Herald** | 验收汇总 | deepseek-v4-flash | 事实性汇总，C 档足够 |
| **Arbiter** | 终审 | gpt-5.4 | 规则性裁决，A- 档够用 |
| **Hunter** | Bug 修复 | opus-4.7 | 定位 Bug 需深度推理，S 档 |
| **Shield** | 回归守护 | deepseek-v4-flash | 全量测试运行检查，C 档足够 |

### 国内版（排除国外模型）

| Agent | 角色 | 推荐模型 | 理由 |
|-------|------|---------|------|
| **Maestro** | 协调/路由 | kimi-k2.6 | A 档国内最强综合能力 |
| **Scout** | 勘探 | deepseek-v4-flash | 结构化检查，C 档足够 |
| **Warden** | 守门 | deepseek-v4-flash | 结构化验证，C 档足够 |
| **Sage** | 苏格拉底追问 | deepseek-v4-pro | S 档（国内），深度推理 |
| **Lex** | spec 审核 | kimi-k2.6 | 规则+理解，A 档 |
| **Clerk** | issue 组织 | deepseek-v4-flash | 结构化操作，C 档足够 |
| **Auditor** | 追溯审计 | deepseek-v4-flash | 交叉验证，C 档足够 |
| **Probe** | 测试设计 | kimi-k2.6 | 需覆盖推理，A 档 |
| **Judge** | 测试评审 | qwen3.6-plus | 规则性评审，A- 档够用 |
| **Archer** | 执行规划 | kimi-k2.6 | 架构推理，A 档 |
| **Cynic** | 规划批评 | deepseek-v4-pro | 逆向思维，S 档优势 |
| **Forge** | TDD 编码 | deepseek-v4-pro | 编码核心，国内 S 档 |
| **Prism** | 代码审查 | kimi-k2.6 | 多角度审查需综合能力，A 档 |
| **Keeper** | 质量门禁 | deepseek-v4-flash | 结构化检查，C 档足够 |
| **Herald** | 验收汇总 | deepseek-v4-flash | 事实性汇总，C 档足够 |
| **Arbiter** | 终审 | qwen3.6-plus | 规则性裁决，A- 档够用 |
| **Hunter** | Bug 修复 | deepseek-v4-pro | 定位 Bug 需深度推理 |
| **Shield** | 回归守护 | deepseek-v4-flash | 测试检查，C 档足够 |

### 模型选择原则

1. **推理深度决定档位**：需要深度推理的 Agent（Sage, Forge, Hunter, Cynic）用最高档；规则验证型（Warden, Lex, Judge, Keeper）用中低档即可
2. **成本与速度**：评审类 Agent 大量运行结构化检查，用 C 档模型降低成本；核心创作类 Agent 用 S/A 档保证质量
3. **Maestro 特殊**：作为路由器，需要广而不需要极深，A 档综合能力最合适
4. **表会在新模型发布后过期**：每次有重大模型更新时，应重新评估档位分配

## 文件清单

```
agents/
├── Maestro.md      # 全程协调
├── Scout.md        # Story/PRD 勘探
├── Warden.md       # Story/PRD 守门
├── Sage.md         # 需求澄清（苏格拉底追问）
├── Lex.md          # spec 审核（律者）
├── Clerk.md        # issue 组织（书记）
├── Auditor.md      # 追溯审计
├── Probe.md        # 测试计划设计（探针）
├── Judge.md        # 测试计划评审（裁判）
├── Archer.md       # 执行规划（架构）
├── Cynic.md        # 规划批评
├── Forge.md        # TDD 编码（锻造）
├── Prism.md        # 代码质量审查（棱镜）
├── Keeper.md       # 代码质量门禁
├── Herald.md       # 验收汇总（传令）
├── Arbiter.md      # 验收终审
├── Hunter.md       # Bug 修复（猎手）
├── Shield.md       # 回归守护（盾牌）
├── ROSTER.md       # 花名册索引
└── README.md       # 本文件
```

## 如何使用

每个 Agent 的 `.md` 文件即为其系统 prompt。调用方式取决于宿主工具：

- **Claude Code**: 将 prompt 内容写入 `~/.claude/agents/<name>.md`，通过 `/agents` 调用
- **OpenCode**: 在 `opencode.jsonc` 的 `agents` 配置中引用，或通过 skill 机制注册
- **Codex**: 将 prompt 写入 `~/.codex/agents/<name>.md`，或在 `AGENTS.md` 中引用
- **通用**: 将 prompt 作为 system message 注入任意 LLM 调用