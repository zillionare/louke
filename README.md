# SpecForge — TDD 驱动的多 Agent 开发方法

## 1. 概述

SpecForge 是通过一组预定义好的 Agent 实现 **TDD-first 协作开发方法**：每个阶段由实施者执行、评审者把关，由 Maestro 统一协调推进。核心原则是 **先写测试，后写实现**，所有产出必须满足退出条件才能推进到下一阶段。

它的核心要点是：

1. 按照 Story/PRD > Spec > Test Plan > Implementation 的流程来进行功能开发规划。
2. 每一个 Spec 都通过 Github issues 来进行跟踪。
3. 通过 Github Projecdt 来管理发布。
4. 每一个流程，都实现实施者、审查者（测试者）配对工作。
5. 基于[LLM-Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)自动创建和管理项目 wiki，确保任何时候都存在、且只有一份正确的项目信息（比如技术决策）。

完整的开发流程如下。

## 2. 功能开发流程

### 2.1. 项目奠基

1. 向用户收集项目信息（story, 版本号, repo 名称）
2. 创建 github repo(如不存在)、github project
3. 确认gh权限和各个 Agent 的可用性

由 scout确保项目奠基，由 Warden 来进行检查。

### 2.2. 需求澄清与 Issue 组织

用户提供一句话的 story/PRD，Sage 通过苏格拉底式追问将模糊需求转化为可测试的 spec，Lex 审核后创建和验证 GitHub issue。所有提问和审核通过 **GitHub PR Review 行级评论**显性化：

1. Sage 创建 `spec/{spec-id}` 分支，生成含 `[待澄清]` 标注的 spec.md，开 PR 并在 Files Changed 留 inline comment 追问
2. 用户在 PR inline comment 下逐条回复
3. Sage 根据回复修改 spec.md 并 push，resolve 对应 comment
4. 重复 2-3 直到所有 `[待澄清]` 已 resolve
5. Lex 通过 `gh api` 提交 PR Review（行级 comment + Approve/Request changes）
6. Lex 通过后 merge PR
7. Sage 根据 spec 中的功能需求创建 GitHub issue（每个 FR 需求 ID 对应一个 issue）
8. Lex 验证 issue 覆盖完整性、补充遗漏、关联 Project

**分支命名约定**（仅需要 PR Review 的阶段才使用专属分支）：

| 阶段      | 分支模式                   | 示例                      | 创建者 | 目的                               |
| --------- | -------------------------- | ------------------------- | ------ | ---------------------------------- |
| Spec 讨论 | `spec/{spec-id}`           | `spec/001-specforge-v0.1` | Sage   | PR Review 行级提问与审核           |
| 任务执行  | `feat/{spec-id}/{task-id}` | `feat/001/TASK-01`        | Forge  | R-G-R 循环 + Prism/Keeper 代码审查 |
| Bug 修复  | `fix/{issue-number}`       | `fix/42`                  | Hunter | TDD Bug 修复 + Shield 回归审查     |


## 3. Hotfix 开发流程

## 4. Agent 花名册与阶段映射

```
Story/PRD ── Scout → Warden ──┐
                                │
Interview ── Sage → Lex ───────┤  ← Sage 产出 spec 并创建 issue，Lex 审核 spec + 验证 issue
Test Plan ── Probe → Judge ──────┤
执行规划 ── Archer → Cynic ─────┤
任务执行 ── Forge → Prism → Keeper ─┤  ← Red-Green-Refactor 循环
验收 ── Herald → Arbiter ────────┘
Bug 修复 ── Hunter → Shield（独立流程，同样 R-G-R）

全程协调：Maestro
```

| 阶段          | 实施者      | 评审者                 | 一句话任务                                           | 流程章节 |
| ------------- | ----------- | ---------------------- | ---------------------------------------------------- | -------- |
| 全程          | **Maestro** | —                      | 协调各 Agent，驱动流程推进                           | 全局     |
| Story/PRD     | **Scout**   | **Warden**             | 勘探前置条件 / 守门确认退出条件                      | 1.1      |
| Interview     | **Sage**    | **Lex**                | 苏格拉底式追问产出 spec 并创建 issue / 审核 spec + 验证补充 issue 并关联 Project | 1.2.1    |
| Test Plan     | **Probe**   | **Judge**              | 设计分层测试计划 / 裁判可执行性                      | 1.2.2    |
| 执行规划      | **Archer**  | **Cynic**              | 任务划分与测试关联 / 批评审核完整性                  | 1.3      |
| 任务执行      | **Forge**   | **Prism** → **Keeper** | R-G-R 循环锻造代码 / 棱镜审视代码质量 / 守住完成门禁 | 1.4      |
| 验收          | **Herald**  | **Arbiter**            | 汇总全量测试与覆盖 / 终审裁决                        | 1.5      |
| Bug 修复      | **Hunter**  | **Shield**             | TDD 猎杀 Bug / 守护无回归                            | 2        |

## 5. Agent → 模型映射能力矩阵

> 更新时间：2026-05-22
> 模型排名基于发布时点的编码能力评估，后续模型发布后需重新评估。

### 5.1. 模型能力档位（2026.05.22）

| 档位 | 全局版            | 国内版            | 特点                         |
| ---- | ----------------- | ----------------- | ---------------------------- |
| S    | opus-4.7          | deepseek-v4-pro   | 深度推理、架构决策、复杂逻辑 |
| A    | gpt-5.5           | kimi-k2.6         | 强编码、长上下文、综合能力强 |
| A-   | gpt-5.4           | qwen3.6-plus      | 稳定编码、较低成本           |
| B    | deepseek-v4-pro   | glm-5.1           | 编码可用、成本更低           |
| C    | deepseek-v4-flash | deepseek-v4-flash | 快速、低成本、适合轻量任务   |
| C+   | gemini-3.5-flash  | —                 | 快速、多模态、低成本         |

### 5.2. 全局版（不限模型）

| Agent       | 角色         | 推荐模型          | 理由                                     |
| ----------- | ------------ | ----------------- | ---------------------------------------- |
| **Maestro** | 协调/路由    | gpt-5.5           | 需综合判断与多步规划，A 档平衡能力与速度 |
| **Scout**   | 勘探         | deepseek-v4-flash | 事实性检查，C 档足够                     |
| **Warden**  | 守门         | deepseek-v4-flash | 结构化验证，C 档足够                     |
| **Sage**    | 苏格拉底追问 | opus-4.7          | 需深度理解与创意提问，S 档最佳           |
| **Lex**     | spec 审核+issue 组织 | gpt-5.4           | 规则性审核+结构化操作，A- 档够用                    |
| **Probe**   | 测试设计     | gpt-5.5           | 需求覆盖推理，A 档                       |
| **Judge**   | 测试评审     | gpt-5.4           | 规则性评审，A- 档够用                    |
| **Archer**  | 执行规划     | gpt-5.5           | 需架构推理与依赖分析，A 档               |
| **Cynic**   | 规划批评     | gpt-5.5           | 需逆向思维与漏洞发现，A 档               |
| **Forge**   | TDD 编码     | opus-4.7          | 编码核心，S 档最可靠                     |
| **Prism**   | 代码审查     | gpt-5.5           | 多角度审查需综合推理，A 档               |
| **Keeper**  | 质量门禁     | deepseek-v4-flash | 结构化检查，C 档足够                     |
| **Herald**  | 验收汇总     | deepseek-v4-flash | 事实性汇总，C 档足够                     |
| **Arbiter** | 终审         | gpt-5.4           | 规则性裁决，A- 档够用                    |
| **Hunter**  | Bug 修复     | opus-4.7          | 定位 Bug 需深度推理，S 档                |
| **Shield**  | 回归守护     | deepseek-v4-flash | 全量测试运行检查，C 档足够               |

### 5.3. 国内版（排除国外模型）

| Agent       | 角色         | 推荐模型          | 理由                       |
| ----------- | ------------ | ----------------- | -------------------------- |
| **Maestro** | 协调/路由    | kimi-k2.6         | A 档国内最强综合能力       |
| **Scout**   | 勘探         | deepseek-v4-flash | 结构化检查，C 档足够       |
| **Warden**  | 守门         | deepseek-v4-flash | 结构化验证，C 档足够       |
| **Sage**    | 苏格拉底追问 | deepseek-v4-pro   | S 档（国内），深度推理     |
| **Lex**     | spec 审核+issue 组织 | kimi-k2.6         | 规则+理解+结构化操作，A 档            |
| **Probe**   | 测试设计     | kimi-k2.6         | 需覆盖推理，A 档           |
| **Judge**   | 测试评审     | qwen3.6-plus      | 规则性评审，A- 档够用      |
| **Archer**  | 执行规划     | kimi-k2.6         | 架构推理，A 档             |
| **Cynic**   | 规划批评     | deepseek-v4-pro   | 逆向思维，S 档优势         |
| **Forge**   | TDD 编码     | deepseek-v4-pro   | 编码核心，国内 S 档        |
| **Prism**   | 代码审查     | kimi-k2.6         | 多角度审查需综合能力，A 档 |
| **Keeper**  | 质量门禁     | deepseek-v4-flash | 结构化检查，C 档足够       |
| **Herald**  | 验收汇总     | deepseek-v4-flash | 事实性汇总，C 档足够       |
| **Arbiter** | 终审         | qwen3.6-plus      | 规则性裁决，A- 档够用      |
| **Hunter**  | Bug 修复     | deepseek-v4-pro   | 定位 Bug 需深度推理        |
| **Shield**  | 回归守护     | deepseek-v4-flash | 测试检查，C 档足够         |

### 5.4. 模型选择原则

1. **推理深度决定档位**：需要深度推理的 Agent（Sage, Forge, Hunter, Cynic）用最高档；规则验证型（Warden, Lex, Judge, Keeper）用中低档即可
2. **成本与速度**：评审类 Agent 大量运行结构化检查，用 C 档模型降低成本；核心创作类 Agent 用 S/A 档保证质量
3. **Maestro 特殊**：作为路由器，需要广而不需要极深，A 档综合能力最合适
4. **表会在新模型发布后过期**：每次有重大模型更新时，应重新评估档位分配

## 6. 文件清单

```
agents/
├── Maestro.md      # 全程协调
├── Scout.md        # Story/PRD 勘探
├── Warden.md       # Story/PRD 守门
├── Sage.md         # 需求澄清（苏格拉底追问）
├── Lex.md          # spec 审核 + issue 组织（律者）
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

## 7. 如何使用

每个 Agent 的 `.md` 文件即为其系统 prompt。调用方式取决于宿主工具：

- **Claude Code**: 将 prompt 内容写入 `~/.claude/agents/<name>.md`，通过 `/agents` 调用
- **OpenCode**: 在 `opencode.jsonc` 的 `agents` 配置中引用，或通过 skill 机制注册
- **Codex**: 将 prompt 写入 `~/.codex/agents/<name>.md`，或在 `AGENTS.md` 中引用
- **通用**: 将 prompt 作为 system message 注入任意 LLM 调用
