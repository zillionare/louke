# SpecForge — TDD 驱动的多 Agent 开发方法

## 1. 概述

SpecForge 是通过一组预定义好的 Agent 实现 **TDD-first 协作开发方法**：每个阶段由实施者执行、评审者把关，由 Maestro 统一协调推进。核心原则是 **先写测试，后写实现**，所有产出必须满足退出条件才能推进到下一阶段。

它的核心要点是：

1. 按照 Story/PRD > Spec > Test Plan > Implementation 的流程来进行功能开发规划。
2. 每一个 Spec 都通过 Github issues 来进行跟踪。
3. 通过 Github Project 来管理发布。
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

用户提供一句话的 story/PRD，Sage 通过苏格拉底式追问将模糊需求转化为可测试的 spec，Lex 审核后创建和验证 **结构化** GitHub issue。所有提问和审核通过 **GitHub PR Review 行级评论**显性化。

**双源设计**（避免重复解析和漂移）：

| 源 | 形式 | 用途 | Agent |
|----|------|------|-------|
| **spec.md**（设计源） | git 内 markdown，PR 评审 | 人读、Sage/Lex 评审、NFR/澄清记录 | Sage / Lex |
| **GitHub Issue**（操作源） | Issue form schema，结构化字段 | 机器读、Probe/Archer/Herald 工作输入、状态跟踪 | Probe / Herald |

1. Sage 创建 `spec/{spec-id}` 分支，生成含 `[待澄清]` 标注的 spec.md，开 PR 并在 Files Changed 留 inline comment 追问
2. 用户在 PR inline comment 下逐条回复
3. Sage 根据回复修改 spec.md 并 push，resolve 对应 comment
4. 重复 2-3 直到所有 `[待澄清]` 已 resolve
5. Lex 通过 `gh api` 提交 PR Review（行级 comment + Approve/Request changes）
6. Lex 通过后 merge PR
7. Sage 根据 spec 中的功能需求，**通过 issue form** 创建 GitHub issue（每个 FR 需求 ID 对应一个 issue）—— body 必须是 `### 需求 ID` / `### Spec 链接` / `### 验收标准` 三个 form 字段
8. Lex 运行 `tools/verify_issue_schema.py` 验证所有 issue 满足 schema（L1-L8），补充遗漏，关联 Project

**Issue Form Schema**（`.github/ISSUE_TEMPLATE/feature.yml`）：

```yaml
需求 ID:    ^FR-\d{3}$                    # 与 spec 锚点 fr-XXX 严格对应
Spec 链接:  ^https://github\.com/.../spec\.md#fr-\d{3}$   # 完整 URL,fragment 小写
验收标准:  ^AC-\d+: ...                   # 每行一条,从 AC-1 连续编号
```

**锚点约定**：spec.md 中每个 FR 单元前必须有 `<a id="fr-XXX"></a>`（小写、3 位零填充），保证 issue 的 Spec 链接跳转稳定。Probe/Archer/Herald 都不再重新解析 spec.md，直接消费 issue form 字段。

**分支命名约定**（仅需要 PR Review 的阶段才使用专属分支）：

| 阶段      | 分支模式                   | 示例                      | 创建者 | 目的                               |
| --------- | -------------------------- | ------------------------- | ------ | ---------------------------------- |
| Spec 讨论 | `spec/{spec-id}`           | `spec/001-specforge-v0.1` | Sage   | PR Review 行级提问与审核           |
| 任务执行  | `feat/{spec-id}/{task-id}` | `feat/001/TASK-01`        | Forge  | R-G-R 循环 + Prism/Keeper 代码审查 |
| Bug 修复  | `fix/{issue-number}`       | `fix/42`                  | Hunter | TDD Bug 修复 + Shield 回归审查     |


### 2.3. 测试计划

Probe 根据 **GitHub Feature issue form schema** 生成分层测试计划，Judge 裁判测试方案的可执行性。**不再重新解析 spec.md**——直接消费 issue form 字段。

**Probe 的工作**：

1. 拉取所有 Feature issue → `gh issue list --state all --label Feature --json body`
2. 解析每个 issue form → 抽取 `fr_id` / `AC-N: ...`（复用 `tools/verify_issue_schema.py` 的解析逻辑）
3. 设计单元测试 → 每个 AC 至少一个 UT（命名 `UT-{issue#}-{AC序}-{测试序}`）
4. 设计集成测试 → 跨 issue 场景（`IT-{序号}`）
5. 设计视觉/E2E 测试（可选）→ UI 相关的端到端场景（`VT-{序号}`）
6. 建立可追溯矩阵 → issue# ↔ fr_id ↔ AC-N ↔ UT 编号
7. 说明测试环境搭建要求
8. 输出测试计划文档，写入 `specs/{spec-id}/test-plan.md`

**为何 Probe 不读 spec.md**：
- spec.md（设计源）由人读、Sage/Lex 评审，不保证结构化
- issue form（操作源）已 schema 化，机器可稳定解析
- 双源读取会产生"哪个对"的争议，浪费 token 仲裁

**Judge 的审核**：

1. 引用验证：每个 issue# / AC-N 都出现在测试矩阵中，允许跨 issue 引用但需验证无循环
2. 可执行性检查：每个测试用例是否有可观测的期望行为
3. QA 场景检查：是否有具体工具 + 步骤 + 预期结果
4. Schema 一致性：测试 ID 编号体系与 issue# / AC-N 对应无误
5. 无阻塞项 → **通过**；有阻塞项 → 退回 Probe（每次最多 3 个阻塞问题）

**交接产出**：`specs/{spec-id}/test-plan.md`（含可追溯矩阵），供 Archer 使用。

### 2.4. 执行规划

Archer 将测试计划拆解为可执行任务列表，Cynic 批评审核完整性。

**Archer 的工作**：

1. 确定版本号与分支策略（`feat/{spec-id}/{task-id}`）
2. 架构分析 → 分析模块边界和依赖关系
3. 任务拆解 → 每个任务必须包含：
   - 关联 issue、spec 需求 ID、测试用例编号
   - 分支名、描述、依赖关系、是否可并行
4. 排序 → 确定执行顺序，标注可并行任务
5. 输出任务列表文档，写入 `specs/{spec-id}/task-plan.md`

**Cynic 的审核**：

1. 测试覆盖完整性：是否有孤儿测试（未被任何任务关联）
2. 任务粒度：是否过大（需多轮 R-G-R）或过小（不值得独立提交）
3. 依赖与顺序：依赖关系是否正确，是否存在循环依赖
4. 遗漏检查：是否缺少集成测试执行任务、数据迁移任务、环境搭建任务
5. 无阻塞项 → **通过**；有阻塞项 → 退回 Archer（每次最多 3 个阻塞问题）

**交接产出**：`specs/{spec-id}/task-plan.md`（含任务列表 + 依赖图），供 Forge 使用。

### 2.5. 任务执行

Forge 按 Red→Green→Refactor 循环编码，Prism 审视代码质量，Keeper 守住完成门禁。

**Forge 的工作（每个任务一个 R-G-R 循环）**：

1. 创建任务分支：`git checkout -b feat/{spec-id}/TASK-{序号}`
2. **Red** → 写失败测试 → 运行确认 Red → 提交（`test: red – {用例编号} {描述}`）
3. **Green** → 写最小实现 → 运行确认 Green → 提交（`feat: green – {用例编号} {描述}`）
4. **Refactor** → 在测试保护下重构 → 提交（`refactor: {描述}`）
5. 每次 commit 后立即 `git push`

**Prism 的审查**（Forge 每轮 R-G-R 完成后）：

1. 可读性审查：命名、结构、注释适度性
2. 设计模式审查：是否合理使用、是否过度设计
3. DRY 审查：是否存在超过 3 行的重复代码
4. 变更影响分析：本次修改可能影响哪些其他模块
5. 无阻塞项 → **通过**；有阻塞项 → 退回 Forge 修正（每次最多 3 个阻塞项）

**Keeper 的门禁**（Prism 通过后）：

1. R-G-R 循环验证：是否有 Red→Green→Refactor 的提交顺序
2. 测试通过：运行关联测试用例，全部 Green
3. 代码质量：运行 lint + typecheck，0 错误
4. 提交合规：commit message 是否遵循 PactKit 风格，是否包含测试编号
5. 4 条全部 ✅ → **通过**；否则退回 Forge

**并行执行**：当 Cynic 标注多个任务可并行时，每个任务在独立分支上各自遵循 R-G-R，合并前必须运行全量测试。

### 2.6. 验收

Herald 汇总全量测试结果与测试计划覆盖，Arbiter 终审裁决。

**Herald 的工作**：

1. 运行全量测试（单元 + 集成）
2. 对照测试计划的可追溯矩阵，逐条确认每个测试用例是否执行且通过
3. 生成验收报告，写入 `specs/{spec-id}/acceptance.md`

**Arbiter 的终审**：

1. 全量测试结果：是否有 RED、是否有跳过
2. 测试计划覆盖：是否有遗漏未执行的测试用例
3. 无回归：是否有之前通过的测试现在失败
4. 用户可操作性：用户是否有足够信息核实功能
5. 全部满足 → **通过**（建议用户关闭 GitHub issue）；否则退回


## 3. Bug 修复流程

独立的 R-G-R 流程，不经过功能开发的 6 阶段：

1. **Hunter 澄清** → 确认 Bug 的分支/版本号、复现步骤、验证方法
2. **创建修复分支** → `git checkout -b fix/{issue-number}`
3. **Red** → 编写测试精确复现 Bug → 提交（`test: red – BUG-{编号} {描述}`）
4. **Green** → 编写最小修复 → 提交（`fix: green – BUG-{编号} {描述}`）
5. **Refactor** → 在测试保护下清理 → 提交（`refactor: BUG-{编号} {描述}`）
6. **全量回归** → Shield 运行全量测试套件，确认无回归
7. **关闭 issue** → 先 `gh issue comment` 留修复信息，再 `gh issue close`（禁止使用 `-c` 参数）

**Shield 的守护**：

1. 全量测试 GREEN
2. 无新增失败
3. 修改范围合理（仅限 Bug 相关代码）
4. 变更影响分析：修改的文件被哪些模块依赖，是否需要额外回归

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

| 阶段      | 实施者      | 评审者                 | 一句话任务                                                                       | 流程章节 |
| --------- | ----------- | ---------------------- | -------------------------------------------------------------------------------- | -------- |
| 全程      | **Maestro** | —                      | 协调各 Agent，驱动流程推进                                                       | 全局     |
| Story/PRD | **Scout**   | **Warden**             | 勘探前置条件 / 守门确认退出条件                                                  | 1.1      |
| Interview | **Sage**    | **Lex**                | 苏格拉底式追问产出 spec 并创建 issue / 审核 spec + 验证补充 issue 并关联 Project | 1.2.1    |
| Test Plan | **Probe**   | **Judge**              | 设计分层测试计划 / 裁判可执行性                                                  | 1.2.2    |
| 执行规划  | **Archer**  | **Cynic**              | 任务划分与测试关联 / 批评审核完整性                                              | 1.3      |
| 任务执行  | **Forge**   | **Prism** → **Keeper** | R-G-R 循环锻造代码 / 棱镜审视代码质量 / 守住完成门禁                             | 1.4      |
| 验收      | **Herald**  | **Arbiter**            | 汇总全量测试与覆盖 / 终审裁决                                                    | 1.5      |
| Bug 修复  | **Hunter**  | **Shield**             | TDD 猎杀 Bug / 守护无回归                                                        | 2        |

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

| Agent       | 角色                 | 推荐模型          | 理由                                     |
| ----------- | -------------------- | ----------------- | ---------------------------------------- |
| **Maestro** | 协调/路由            | gpt-5.5           | 需综合判断与多步规划，A 档平衡能力与速度 |
| **Scout**   | 勘探                 | deepseek-v4-flash | 事实性检查，C 档足够                     |
| **Warden**  | 守门                 | deepseek-v4-flash | 结构化验证，C 档足够                     |
| **Sage**    | 苏格拉底追问         | opus-4.7          | 需深度理解与创意提问，S 档最佳           |
| **Lex**     | spec 审核+issue 组织 | gpt-5.4           | 规则性审核+结构化操作，A- 档够用         |
| **Probe**   | 测试设计             | gpt-5.5           | 需求覆盖推理，A 档                       |
| **Judge**   | 测试评审             | gpt-5.4           | 规则性评审，A- 档够用                    |
| **Archer**  | 执行规划             | gpt-5.5           | 需架构推理与依赖分析，A 档               |
| **Cynic**   | 规划批评             | gpt-5.5           | 需逆向思维与漏洞发现，A 档               |
| **Forge**   | TDD 编码             | opus-4.7          | 编码核心，S 档最可靠                     |
| **Prism**   | 代码审查             | gpt-5.5           | 多角度审查需综合推理，A 档               |
| **Keeper**  | 质量门禁             | deepseek-v4-flash | 结构化检查，C 档足够                     |
| **Herald**  | 验收汇总             | deepseek-v4-flash | 事实性汇总，C 档足够                     |
| **Arbiter** | 终审                 | gpt-5.4           | 规则性裁决，A- 档够用                    |
| **Hunter**  | Bug 修复             | opus-4.7          | 定位 Bug 需深度推理，S 档                |
| **Shield**  | 回归守护             | deepseek-v4-flash | 全量测试运行检查，C 档足够               |

### 5.3. 国内版（排除国外模型）

| Agent       | 角色                 | 推荐模型          | 理由                       |
| ----------- | -------------------- | ----------------- | -------------------------- |
| **Maestro** | 协调/路由            | kimi-k2.6         | A 档国内最强综合能力       |
| **Scout**   | 勘探                 | deepseek-v4-flash | 结构化检查，C 档足够       |
| **Warden**  | 守门                 | deepseek-v4-flash | 结构化验证，C 档足够       |
| **Sage**    | 苏格拉底追问         | deepseek-v4-pro   | S 档（国内），深度推理     |
| **Lex**     | spec 审核+issue 组织 | kimi-k2.6         | 规则+理解+结构化操作，A 档 |
| **Probe**   | 测试设计             | kimi-k2.6         | 需覆盖推理，A 档           |
| **Judge**   | 测试评审             | qwen3.6-plus      | 规则性评审，A- 档够用      |
| **Archer**  | 执行规划             | kimi-k2.6         | 架构推理，A 档             |
| **Cynic**   | 规划批评             | deepseek-v4-pro   | 逆向思维，S 档优势         |
| **Forge**   | TDD 编码             | deepseek-v4-pro   | 编码核心，国内 S 档        |
| **Prism**   | 代码审查             | kimi-k2.6         | 多角度审查需综合能力，A 档 |
| **Keeper**  | 质量门禁             | deepseek-v4-flash | 结构化检查，C 档足够       |
| **Herald**  | 验收汇总             | deepseek-v4-flash | 事实性汇总，C 档足够       |
| **Arbiter** | 终审                 | qwen3.6-plus      | 规则性裁决，A- 档够用      |
| **Hunter**  | Bug 修复             | deepseek-v4-pro   | 定位 Bug 需深度推理        |
| **Shield**  | 回归守护             | deepseek-v4-flash | 测试检查，C 档足够         |

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
├── Probe.md        # 测试计划设计（探针，从 issue form 取需求）
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

.github/
└── ISSUE_TEMPLATE/
    └── feature.yml # Feature issue form (3 必填字段 schema)

tools/
└── verify_issue_schema.py   # 验证所有 Feature issue 满足 L1-L8 schema 不变量

templates/
└── spec.md        # 含 <a id="fr-XXX"></a> 显式锚点约定
```

## 7. Wiki 架构（LLM-Wiki 模式）

基于 Karpathy 的 [LLM-Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 模式，三层架构：

```
raw/sources/        ← Agent 完整会话记录（零 token，由 Hook 或 Agent 自行写入）
wiki/pages/         ← 结构化 wiki 页面（Agent 对话结束时零额外 token 写入，带 YAML frontmatter + [[wikilink]]）
  ├── {主题}.md     ← 每个 Agent 会话产出为一个 wiki 页面
  └── ...
wiki/decisions/     ← 架构决策记录 (ADR)
wiki/index.md       ← 导航目录（Librarian 维护）
wiki/log.md         ← 操作日志（Librarian 维护）
wiki/overview.md    ← 全局摘要（Librarian 维护）
wiki/.cache         ← SHA256 增量缓存（Librarian 内部使用）
```

### 数据流

```
Agent 对话结束
    ↓ 零额外 token（只是输出格式变了）
    ├→ 写入 wiki/pages/{主题}.md（带 YAML frontmatter + [[wikilink]]）
    └→ （未来 Hook 可用后）写入 raw/sources/{会话ID}.md

Librarian 被触发
    ↓ 仅处理增量（SHA256 对比）
    ├→ 重建 wiki/index.md（导航目录）
    ├→ 更新 wiki/overview.md（全局摘要）
    └→ 执行 Lint（孤立页面、死链接、缺失元数据）

Guide 查询 wiki
    ↓ 读取 wiki/index.md 定位 → 读取相关 pages → 回答问题
```

### Wiki 页面格式

```markdown
---
type: decision | experience | entity
title: {简短标题}
date: YYYY-MM-DD
agents: [{参与 Agent}]
sources: [{来源}]
related: [[{其他 wiki 页面}]]
---

## {正文}
{使用 [[wikilink]] 交叉引用，每条结论标注来源}
```

### Token 消耗对比

| 方式                               | 额外 token                             |
| ---------------------------------- | -------------------------------------- |
| Agent 直接写 wiki/pages/           | 零（本来就要写会话记录，只是格式变了） |
| Librarian 维护 index/overview/lint | 极低（仅增量处理）                     |

## 8. 如何使用

每个 Agent 的 `.md` 文件即为其系统 prompt。调用方式取决于宿主工具：

- **Claude Code**: 将 prompt 内容写入 `~/.claude/agents/<name>.md`，通过 `/agents` 调用
- **OpenCode**: 在 `opencode.jsonc` 的 `agents` 配置中引用，或通过 skill 机制注册
- **Codex**: 将 prompt 写入 `~/.codex/agents/<name>.md`，或在 `AGENTS.md` 中引用
- **通用**: 将 prompt 作为 system message 注入任意 LLM 调用
