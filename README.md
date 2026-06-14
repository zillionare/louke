# SpecForge — TDD 驱动的多 Agent 开发方法

## 1. 概述

SpecForge 是通过一组预定义好的 Agent 来实现 **TDD-first 的协作开发方法**：每个阶段由实施者执行、评审者把关，由 Maestro 统一协调推进。核心原则是 **先写测试，后写实现**，所有产出必须满足退出条件才能推进到下一阶段。

核心要点是：

1. 按照 Story/PRD > Spec > Test Plan > Implementation 的流程来进行功能开发规划。
2. 每一项 spec 都有 ID 标识，并通过 github issue, git commit hash 来关联和跟踪。
3. 每一项 spec 都有测试计划，记录在 spec 对应的 github issue 中（第一个 reply），测试代码也通过 git commit hash 来关联。
4. 通过 Github Project 来管理版本发布。
5. 流程中的每一个环节，都实现实施者、审查者（测试者）配对工作。
6. 基于[LLM-Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)自动创建和管理项目 wiki，确保任何时候都存在、且只有一份正确的项目信息（比如技术决策）。

### 背景

你可能会发现，已经有一些类似的实现，比如 [Oh My OpenAgent](https://github.com/code-yeongyu/oh-my-openagent)，[Speckit](https://github.com/github/spec-kit)， [Superpowers](https://github.com/obra/superpowers)。

为什么还要自己动手做一套新的？这是不是在重新发明轮子？

这是 deepseek 做的调研：

与 speckit 相比，SpecForge 通过Agent角色、Issue管理和TDD流程，为 speckit 的核心规范提供了工程化保障。在我看来，这正是很多企业级项目真正需要的东西——把规则变成自动化，确保每一步都严格执行。

而且 speckit 并不是原生多 Agent 架构。SpecForge 多 Agent 协作机制可以让每一个 Agent 有自己的专属上下文（从而扩展了 LLM 的 context window 限制），并且彼此的 rule, prompt 不会混淆、冲突。

更重要的区别在于可落地性。在 SpecForge 的作者看来，其它方案仍然存在理念很先进，但执行上依赖 LLM 的指令遵循能力。比如，包括 speckit 在内的一些方案，在需求阶段，都可能生成详细地 spec 条目，并且为每一个条目指定了编号以便跟踪；但是，需求仍然集中存放在一个 Markdown 文档中，这对企业级项目来讲，仍然是混乱之源 -- 至少在现阶段，你仍然不能指望 AI 能在一个有十万字级别的需求文档中，既快速、又精准地跟踪一个需求项。

SpecForge 会把这些需求拆解成一个个 github issue，并且保持着与 spec 文档的引用。这样一来，spec文档就可以成为一个更宏观的规格文档，而github issue 可成为深入讨论和跟踪实现细节、技术决定的地方。

Speckit 在规格定义阶段就要求赋予优先级，这当然没有错，但是一旦需要重调优先级，你就得修改 markdown -- 一个纯文本文件。我更喜欢 github project 中，可以把 github issues 任意指定到一个 project 中的自由。

一些方案把代码审查当成流程的重心 -- 但是以 AI 生成代码的速度，人类真的 review 不过来了。相反，人类必须决定我需要什么、如何判断 AI 生成的东西就是我想要的 -- 这就是测试用例。好的流程，应该只强调需求和验证方案，这才是人类需要花时间来制定和审查的部分。

## 2. 基于SpecForge 的开发流程

### 2.1. 项目奠基

1. 向用户收集项目信息（story, 版本号, repo 名称）
2. 创建 github repo(如不存在)、github project
3. 确认gh权限和各个 Agent 的可用性

由 scout确保项目奠基，由 Warden 来进行检查。

### 2.2. 需求澄清和分解 (spec 004 修订: IDE-based)

用户提供一句话的 story/PRD, Sage 通过苏格拉底式追问将模糊需求转化为可测试的需求, Lex 审核后创建和验证 **结构化** GitHub issue。**所有提问和审核通过 markdown quote block 在 spec.md 中进行**, 用户在 IDE 中直接编辑 spec.md, 不需要 GitHub PR 权限 (Aaron 设计)。

**双源设计**（避免重复解析和漂移）:

| 源                         | 形式                          | 用途                                           | Agent          |
| -------------------------- | ----------------------------- | ---------------------------------------------- | -------------- |
| **spec.md**（设计源）      | git 内 markdown + quote dialogue | 人读、Sage/Lex 评审、NFR/澄清记录              | Sage / Lex     |
| **GitHub Issue**（操作源） | Issue form schema, 结构化字段 | 机器读、Probe/Archer/Herald 工作输入、状态跟踪 | Probe / Herald |

**流程**：

1. 用户把一句话 PRD 写入 `specs/{spec-id}/story.md` (或直接 chat 告诉 Sage)
2. Sage 创建 `spec/{spec-id}` 分支, 写 spec.md, 在原文段落后追加 quote block 标注疑点 (FR-016):
   ```markdown
   <a id="fr-016"></a>
   **FR-016**: 这是原文段落正文。
   
   > **Sage:** 这是 Sage 的疑问, 默认 pending (无显式状态 marker)。
   > > 追问嵌套示例 (depth=2)。
   ```
3. Sage push 到 spec 分支, **在 chat 通知用户 "spec.md 已更新, 请在 IDE 中 review"** (FR-019 修订触发机制)
4. **用户在 IDE 中直接编辑 spec.md** (Aaron: 不需要 git push, 可在本地工作区完成):
   - 改 quote block 状态: `pending` → `✓ resolved` (FR-017 默认无 marker = pending)
   - 改任何原文段: 视作"用户更正 Agent 记录", **silent** (FR-020)
   - 加新 quote 追问
5. 用户在 chat 说 "review 完了" 或 "continue"
6. Sage `git pull` + `git diff` 解析变更 (FR-019), 决定下一步
7. 仍有 pending → 回到 2; 全部 ✓ resolved → 进入 7
8. Sage 根据 spec 中的功能需求, **通过 issue form** 创建 GitHub issue
9. Lex 运行 `tools/quote_parser.py --check-ready` (FR-026 修订锁定信号, 替代 PR merged) + `tools/verify_issue_schema.py` 验证 issue 满足 schema

**Quote 状态约定** (FR-017, Aaron 设计):

| 标记 | 语义 |
|---|---|
| 无 marker (默认) | pending / open |
| `✓ resolved` | 闭环 |
| `[blocked-by-N]` | 被 FR-N 阻塞 |
| `[wontfix]` | 终止 (不实施) |
| `[superseded]` | 被新 spec 取代 |

**markdown 示例**：

```markdown
原文段落。

> **Sage:** 问题 (默认 pending)

> > **Aaron:** 回答 ✓ resolved
```

**锚点约定**：spec.md 中每个 FR 单元前必须有 `<a id="fr-XXX"></a>`（小写、3 位零填充），保证 issue 的 Spec 链接跳转稳定。Probe/Archer/Herald 都不再重新解析 spec.md，直接消费 issue form 字段。

**Issue Form Schema**（`.github/ISSUE_TEMPLATE/feature.yml`）：

```yaml
需求 ID:    ^FR-\d{3}$                    # 与 spec 锚点 fr-XXX 严格对应
Spec 链接:  ^https://github\.com/.../spec\.md#fr-\d{3}$   # 完整 URL,fragment 小写
验收标准:  ^AC-\d+: ...                   # 每行一条,从 AC-1 连续编号
```

**分支命名约定**：

| 阶段      | 分支模式                   | 示例                      | 创建者 | 目的                                          |
| --------- | -------------------------- | ------------------------- | ------ | --------------------------------------------- |
| Spec 讨论 | `spec/{spec-id}`           | `spec/001-specforge-v0.1` | Sage   | IDE quote dialogue + chat trigger             |
| 任务执行  | `feat/{spec-id}/{task-id}` | `feat/001/TASK-01`        | Forge  | R-G-R 循环 + Prism/Keeper 代码审查            |
| Bug 修复  | `fix/{issue-number}`       | `fix/42`                  | Hunter | TDD Bug 修复 + Shield 回归审查                |

> 旧版 PR Review 流程见 git history (pre-spec 004)。spec 003 之前的 spec 都用 PR Review, 自 spec 004 起改用 IDE-based quote dialogue.


### 2.3. 测试计划

Probe 根据 **GitHub Feature issue form schema** 生成分层测试计划，Judge 裁判测试方案的可执行性。

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

## 8. 如何使用（用户手册）

### 8.1 安装

**一键安装**（推荐）：

```bash
curl -sSL https://raw.githubusercontent.com/zillionare/specforge/main/install.sh | bash
```

这会做：
1. `git clone --depth 1` 到 `~/.specforge/`
2. 把 `bin/specforge` 复制到 `~/.local/bin/specforge`
3. 把 `~/.local/bin` 加进 PATH（如果还没在）

**装完后**：
```bash
$ specforge version
specforge 0.1.0
  install path: /Users/you/.specforge
```

**手动安装**（适合 dev 或离线场景）：
```bash
git clone https://github.com/zillionare/specforge.git ~/.specforge
cp ~/.specforge/bin/specforge ~/.local/bin/
chmod +x ~/.local/bin/specforge
export PATH="$HOME/.local/bin:$PATH"
```

### 8.2 升级

```bash
specforge upgrade
```

内部是 `git pull --ff-only origin main`。**在非 main 分支上拒绝运行**（避免误改 dev 仓）—— 这是个安全护栏，不是 bug。

升级前会 fetch + fast-forward merge，输出新版本号。建议每月一次，或看到新功能公告时升级。

`upgrade` 是 **user-driven** 的 lifecycle 命令 —— agent 不会自动跑（升级有破坏性，agent prompts 文件会变）。

### 8.3 初始化项目

#### 8.3.1 新建项目

```bash
specforge init my-project
cd my-project
ls
# agents/  templates/  specs/  wiki/  raw/
```

`init <bare-name>` 会把 `agents/*.md` 和 `templates/*.md` 拷到你的项目目录。**Python 工具（`tools/*.py`）不复制**——它们是 framework 的实现细节，留在 `~/.specforge/tools/`，通过 `specforge` CLI 调用。

#### 8.3.2 接入既存项目（adopt 模式）

v0.3 起，`init` 支持把 specforge 非破坏性地接入既存项目：

```bash
cd /path/to/existing-project  # 必须是 git repo
specforge init .               # 当前目录
specforge init /abs/path       # 绝对路径
specforge init ~/projects/x    # home 缩写
specforge init ./sub           # 相对路径
```

**判定规则**：参数含 `/`、以 `.` 开头、以 `~` 开头 → 既存路径（adopt 模式）；否则视为裸名（新建项目）。

**adopt 模式保证**：
- 既存源代码字节级不变（递归 SHA256 验证）
- `.git/` 不被触碰
- `agents/` `templates/` 等 specforge-owned 目录：缺则创建，有则保留
- 同名文件：默认 skip + warn；可加 `--backup`（备份为 `.bak`）或 `--force`（覆盖）
- `.gitignore` 自动追加 `.specforge/`（`--no-gitignore` 跳过）
- 三档报告：`[+]` 新增 / `[=]` 跳过 / `[!]` 备份

**Flags**：

| Flag | 作用 |
|---|---|
| `--dry-run` | 只打印将做什么，不实际改 |
| `--backup` | 既存文件 → `.bak` 后跳过（不覆盖） |
| `--force` | 既存文件强制覆盖 |
| `--with-issue-template` | 同时安装 `.github/ISSUE_TEMPLATE/feature.yml` |
| `--no-gitignore` | 不动 `.gitignore` |
| `--json` | 输出机器可读 JSON 替代纯文本 |

**示例**：

```bash
# 接入 millionaire，dry-run 预览
specforge init . --dry-run

# 接入并保留用户修改
specforge init . --backup

# CI/script 用法：JSON 输出
specforge init . --json | jq '.added | length'
```

### 8.4 配置

#### 8.4.1 身份一致性（必做，会话级不变量）

**为什么需要**：specforge 同时用 `gh` CLI（issue/PR/label）和 `git`（push/clone）。两者如果用不同 GitHub 账号，会出现 "git push 成功但 gh 操作 403" 这种半成功半失败的窘境。Maestro 会在每次会话启动时自动跑这个检查；用户也可以手动跑：

```bash
specforge checkup OWNER/REPO
```

输出三档：
- `[通过]` — gh 与 git 身份完全一致，权限足够
- `[通过+警告]` — 主体一致，但有提示项（如 remote owner 与 gh user 不同，可能是合法的个人 token 操作 org repo）
- `[拒绝]` — 身份不一致或权限不足，**会话不能启动**

修复（按提示）：
- `gh auth switch` 切换到正确的 GitHub 账号
- `gh auth refresh -h github.com -s repo,project` 加 scope
- `git config user.email <gh 账号关联邮箱>` 改 git 身份

#### 8.4.2 GitHub Token

`specforge checkup` 会自动检查 token scopes。最简配置：
- `repo`（创建/编辑 issue、PR、push code）
- `project`（创建/管理 GitHub Project）

可选：
- `delete_repo`（CLI 删 repo）
- `workflow`（编辑 `.github/workflows/`）

#### 8.4.3 模型选择

`agents/README.md` 第 5 节给了全局版和国内版两套模型映射。按表选即可，框架本身不绑死任何 provider。

### 8.5 启动开发流程

```bash
# 1. (新会话) 跑一次身份体检
specforge checkup OWNER/REPO

# 2. 加载 Guide Agent 了解方法论
#    把 agents/Guide.md 的内容粘贴到 AI 工具的 system message,问"我该如何开始"

# 3. 有了 PRD/Story 后,加载 Scout Agent 启动 §2.1 项目奠基
#    把 agents/Scout.md 加载,告诉它你的项目信息

# 4. 流程推进:每个阶段 agent prompt 在 agents/{name}.md
#    Sage → Lex → Probe → Judge → Archer → Cynic → Forge → ...
```

### 8.6 验证与体检（Agent 内部调用）

下列命令**主路径上由 agent 在 AI 工具上下文内自动调用**，用户不需要切换到终端。`specforge help` 列出它们只是为了人在 agent 卡住时可以手动跑一次 debug。

| 命令                               | 用途                                   | 调用方              | 何时跑                        |
| ---------------------------------- | -------------------------------------- | ------------------- | ----------------------------- |
| `specforge checkup OWNER/REPO`     | 身份一致性体检 (L1-L5)                 | **Agent** — Maestro | 每次 Maestro 启动时（自动）   |
| `specforge doctor`                 | checkup 的别名                         | **Agent** — Maestro | 同上                          |
| `specforge verify-issue --spec ID` | 验证 Feature issue form schema (L1-L8) | **Agent** — Lex     | Lex 阶段三 issue 准入（自动） |

**资源开销**：以上所有命令合计 0 LLM token，1 次 `gh api`，< 5 秒。

**用户何时手动跑这些**：当 Maestro/Lex 报告 `[拒绝]` 或持续失败，但又看不出原因时，可以自己跑一次看完整 L1-L8 输出，再 `gh auth status` / `git config` 等 debug。**不是常规操作**。

### 8.7 卸载

```bash
rm -rf ~/.specforge
rm ~/.local/bin/specforge
# 也可手动从 ~/.zshrc / ~/.bashrc 删掉 PATH 那行
```

### 8.8 与 AI 工具的集成

每个 Agent 的 `.md` 文件即为其系统 prompt。调用方式取决于宿主工具：

- **Claude Code**: 将 prompt 内容写入 `~/.claude/agents/<name>.md`，通过 `/agents` 调用
- **OpenCode**: 在 `opencode.jsonc` 的 `agents` 配置中引用，或通过 skill 机制注册
- **Codex**: 将 prompt 写入 `~/.codex/agents/<name>.md`，或在 `AGENTS.md` 中引用
- **Kilo Code**（specforge 自举所用）: 在 `.kilo/agent/*.md` 注册
- **通用**: 将 prompt 作为 system message 注入任意 LLM 调用

### 8.9 命令分类

`specforge` 的 6 个子命令按"主调用方"分两类。**CLI 入口统一，但调用方不同**：

#### User-driven（人在终端跑）

用户主动跑。Agent 不会自动调，因为这些操作有破坏性或是一次性。

| 命令          | 用途                                      | 频次                |
| ------------- | ----------------------------------------- | ------------------- |
| `init <name>` | 初始化新项目（拷贝 agents/ + templates/） | 每个新项目一次      |
| `upgrade`     | 升级 framework 到最新 main                | 每月一次 / 看公告时 |
| `version`     | 打印版本 + install 路径                   | 偶尔 debug          |
| `help`        | 用法                                      | 偶尔查              |

#### Agent-driven（AI 工具在上下文内跑）

主路径上由 agent prompt 触发，在 LLM token 流中作为 tool call 执行。**用户感知不到**。`specforge help` 列出它们只是为了人能在 agent 卡住时手动跑一次 debug。

| 命令                     | 用途                                   | 谁调                    |
| ------------------------ | -------------------------------------- | ----------------------- |
| `checkup <owner/repo>`   | 身份一致性体检 (L1-L5)                 | Maestro (session-start) |
| `doctor`                 | `checkup` 的别名                       | Maestro                 |
| `verify-issue --spec ID` | Feature issue form schema 验证 (L1-L8) | Lex (issue 准入)        |

**判定原则**：

- **machine-consumed 验证**（输出是 L1-L8 失败列表，agent 自己消化）→ agent-driven；人不该看，也不该手动调
- **lifecycle 动作**（建项目、升级、查版本）→ user-driven；agent 不该自作主张

**调试路径**：agent 报告 `[拒绝]` 或卡在某步 → 用户手动跑对应命令 → 看完整 stdout → 决定是 `gh auth switch` / `gh auth refresh` / 改 git config 等。

---

## 9. 部署与分发路线图

### 9.1 当前形态（v0.1.0）

- **安装**：`curl ... | bash`（git clone 到 `~/.specforge/`）
- **升级**：`specforge upgrade`（git pull ff-only）
- **依赖**：Python 3 stdlib（无第三方包）、bash、git、gh CLI
- **发布**：直推 GitHub `main` 分支，无版本号（直到加 VERSION 文件前）

### 9.2 v0.2 计划

- **VERSION 文件**（已加）→ `specforge version` 打印
- **Homebrew tap**（`zillionare/homebrew-specforge`）：
  - 用户：`brew install zillionare/specforge/specforge`
  - 好处：macOS 用户最熟悉，自动 PATH 设置，签名校验
- **Windows / WSL 支持**：当前 install.sh 是 bash only，Win 用户需 WSL

### 9.3 v1.0 计划

- **GitHub Releases with SHA256SUMS**：
  - 每次发版打 tag，CI 生成 tarball + checksum
  - install.sh 增加 `--verify` 模式（curl 后对 checksum）
  - 适合企业用户、防供应链攻击
- **可选 venv**（在 `bin/specforge` 的 `resolve_python` 切换）：
  - 何时启用：当任何工具开始用第三方包（`requests`、`pyyaml`、`jinja2`）时
  - 切换方式：`install.sh` 末尾 `python3 -m venv ~/.specforge/.venv && ~/.specforge/.venv/bin/pip install ...`
  - **agent prompt 完全不需要改**——`bin/specforge` 已经是唯一入口
- **离线安装包**：`specforge-{version}.tar.gz` 镜像（无网络环境）

### 9.4 不会做的

- **PyPI 包**：specforge 不是 Python 库，是 "framework + markdown prompts"，pip 装没意义
- **Docker 镜像**：specforge 本质是 prompt + CLI 脚本，容器化反而增加门槛
- **自托管 web 服务**：specforge 是给本地开发者用的，不是 SaaS

### 9.5 升级兼容性策略

- **次版本号（0.1 → 0.2）**：可加新子命令、新 agent，老 agent prompt 行为不变
- **次版本号（0.x → 0.y）**：agent prompt 字段可加但不可改，老调用方式仍工作
- **主版本号（0.x → 1.0）**：保证"在 0.9 写出的 spec 能用 1.0 的 verifier 校验"，反之亦然
- **agent 协议变更**：必须同时更新 Scout（首次接触新 spec 的 agent） 和 Guide（方法论入口），并在 wiki/decisions/ 留 ADR
