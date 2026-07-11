---
locked: true
locked-at: 2026-07-11T15:30:00Z
locked-by: maestro (record-lock bypassed due to issue #110)
lock-bypass-reason: "verify-issue 扫所有 Feature label 历史的脏 issues,无法在 v0.11 内修复;issue #110 跟踪"
---

# Louke Web IDE 与工作流服务化 — Spec

- **Spec ID**: v0.11-001-web-ide
- **Created**: 2026-07-11
- **Status**: Locked (bypassed)
- **Target users**: Louke 项目的内部使用者
- **Priority**: 本文全部用户故事与需求均为 P0

> 本文描述需求与边界。可观察、可断言的通过条件集中记录于 `acceptance.md`。

## User Stories

### US-0001

story: 作为 Louke 内部使用者，我希望在 Web 页面创建、切换、操作和停止 OpenCode 运行实例，以便不离开浏览器完成交互。
priority: P0

### US-0101

story: 作为 Louke 内部使用者，我希望由 Louke Server 推进可工具化的工作流，并仅在需要判断时调用保留的角色，以便减少纯工具调用型 Agent。
priority: P0

### US-0201

story: 作为 Louke 内部使用者，我希望系统在执行每条指令前识别意图并选择或确认正确流程，以免错误启动开发或修改流程。
priority: P0

### US-0301

story: 作为 Louke 内部使用者，我希望浏览统一、可追溯且可更新的 Wiki，以便获得项目当前事实和技术裁决。
priority: P0

### US-0401

story: 作为 Louke 维护者，我希望 `.louke` 中的服务、评审、会话与 Wiki 产物有明确归档位置，以便管理 Louke 元数据。
priority: P0

### US-0501

story: 作为 Louke 内部使用者，我希望在 Web 页面切换 FR/NFR 的 Markdown task 状态并持久化，以便直接完成需求评审。
priority: P0

### US-0601

story: 作为 Louke 内部使用者，我希望先把新 story 存入本地 backlog，再选择条目进入现有开发流程，以便延后启动开发。
priority: P0

### US-0701

story: 作为 Louke 内部使用者，我希望查看工作区文件、变更和 diff，并编辑允许修改的设计文档，以便在 Web IDE 中评审工作。
priority: P0

### US-0801

story: 作为 Louke 内部使用者，我希望渲染查看 design documents、README 和 `docs/*.md`，以便集中阅读项目文档。
priority: P0

## Usage Scenarios

### scenario-0001 OpenCode 交互

用户在 Web 页面创建或选择实例，发送消息或支持的命令，观察输出和运行状态，必要时停止实例。

### scenario-0101 指令路由

用户提交指令；系统先显示识别出的意图与拟执行动作；分类不确定时先询问，确认后进入对应 Louke 流程。

### scenario-0201 Wiki 更新

用户点击更新按钮，或每日定时任务检测到源文档变化后，系统重建 Wiki 并保留事实来源链接。

### scenario-0301 Backlog 转开发

用户创建 backlog 条目，在列表中选中一项并点击进入开发，随后衔接 Louke 现有的新 story 开发流程。

### scenario-0401 工作区阅读与设计文档编辑

用户浏览文件、Git 变更和 diff；源代码保持只读，允许的设计文档可以编辑和保存。

## Functional Requirements

### FR-0001 OpenCode 实例与会话操作


| Valid | Testable                                              | Decided |
| ----- | ----------------------------------------------------- | ------- |
| ✅    | ✅                                                    | ✅      |

Decision: 所有 `/` 命令均透传给 OpenCode；实例状态与输出采用 OpenCode 返回结果，不另定义命令白名单。

- Web 页面必须允许创建、选择和停止 OpenCode 运行实例。
- 用户必须能向选中实例发送普通消息并看到消息回显及运行状态回显。
- 页面必须支持 OpenCode 命令交互；`models` 与 `agent` 是已明确的代表性命令。

> **Aaron:** 这些都是 '/' 命令，只要支持透传给 opencode 即可支持所有的命令

- 一个实例的输出不得显示到另一个实例的会话中。
- 验收引用：AC-FR0001-01 至 AC-FR0001-04。

---

### FR-0101 Louke Server 工作流推进与 Agent 工具化


| Valid | Testable                                     | Decided |
| ----- | -------------------------------------------- | ------- |
| ✅    | ✅                                           | ✅      |

Decision: 本需求延后至下一个 spec；Archer 完成本 spec 架构设计后再决定 Agent 工具化清单。

- Louke Server 必须承担可表达为确定性工具调用的工作流推进步骤。
- 仅执行工具调用且不承担判断职责的 Agent 应在迁移清单确认后取消，其能力由 Louke Server 提供。
- Maestro 角色暂予保留；工作流在需要决定下一步时可以调用 Maestro，但不再由 Maestro 独占整个工作流协调职责。
- 每项迁移必须能通过同一输入触发的新服务路径及不再触发的旧 Agent 路径观察。
- 验收引用：AC-FR0101-01 至 AC-FR0101-03。

> **Aaron:** 本需求延后到下一个 spec 做。@Archer 在做完本 spec 的架构设计后，即可决定哪些 Agent 可以工具化。

---

### FR-0201 用户指令意图分类与路由


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅    | ✅       | ✅      |

Decision: 用户已确认意图不确定时必须询问；本 requirement 无其他未决项。

- 系统必须在执行每条用户指令前先分类其意图，再确定动作。
- 至少识别 `story`、`spec change`、`bug fix` 三类意图，并分别支持“进入新开发或存入 backlog”、“spec change”、“fix”动作。
- 对 `story` 意图，系统必须让用户选择立即进入新开发或存入 backlog，不得静默代选。
- 对歧义、低置信度或不属于已知类别的输入，系统必须询问用户并在确认前不执行流程动作。
- 验收引用：AC-FR0201-01 至 AC-FR0201-04。

---

### FR-0301 可追溯项目 Wiki


| Valid | Testable                                              | Decided |
| ----- | ----------------------------------------------------- | ------- |
| ✅    | ⚠️ 汇总粒度、事实冲突优先级和技术决定来源范围待确认 | ✅      |

Decision: Wiki 按文档类型分别生成 story、spec、test-plan、architecture、interfaces 汇总页；手动按钮与每日定时更新并存，且无源变更时不更新。

- Wiki 必须分别维护一份反映当前最新且最完整状态的 story、spec、test-plan、architecture、interfaces 汇总文档。
- 汇总文档使用文档内标题序号而非 FR-XXXX 作为展示编号。
- 每条 story/spec 事实必须包含指回原始 story、spec、acceptance、test-plan、architecture 或 interfaces 文档相应位置的链接。
- Wiki 必须记录 review 中被争议并最终裁定的技术决定、裁定结果和原因。
- 首页必须包含 README 内容或入口，以及指向 story、spec 等设计文档的链接。
- Wiki 必须包含 FAQ 和项目信息；项目信息至少包括版本、分支、GitHub Project、版本开发开始时间和结束时间。
- Web 页面必须提供手动更新按钮；定时任务必须每日检查源文档，只有检测到变更时才更新 Wiki。
- 本 requirement 的实现探索、现状审计、推荐数据模型、增量编译流水线、来源优先级与待确认决策见 `wiki-exploration.md`；该文件是提案输入，不把本节 `Decided: ⚠️` 的事项自动视为已确认。
- 验收引用：AC-FR0301-01 至 AC-FR0301-05。

---

### FR-0401 `.louke` 产物目录规划


| Valid | Testable                              | Decided |
| ----- | ------------------------------------- | ------- |
| ✅    | ✅                                    | ✅      |

Decision: 用户已明确同意本 requirement 描述；具体目录映射与兼容迁移规则由后续设计确定。

- 必须为 Louke Server 文件、code review 输出、会话保存和各类 Wiki 文件定义互不混淆的规范存放位置。
- 运行时产生的上述文件必须写入其规范位置。
- 本 requirement 只规定本功能需要形成并遵循目录规划；当前 M-SPEC 阶段不得修改目录结构。
- 验收引用：AC-FR0401-01 至 AC-FR0401-03。

> **Aaron:** 同意

---

### FR-0501 FR/NFR task 状态编辑与持久化


| Valid | Testable                            | Decided |
| ----- | ----------------------------------- | ------- |
| ✅    | ✅                                  | ✅      |

Decision: 三个状态为 `Valid`、`Testable`、`Decided`，并持久化到源文件。

- FR/NFR 状态必须以标准 Markdown task list（`- [ ]` / `- [x]`）存储和渲染，不再以表格存储。
- Web 页面必须允许点击每个 task 的 checkbox 切换状态，并将变更持久化到对应设计文档源文件。
- 可以采用一行视觉布局，但每个状态仍必须保持独立、可操作的 Markdown task 语义。
- 在状态名称确认前，不得把 story 中重复出现的“可测试性”自行解释为新状态。
- 验收引用：AC-FR0501-01 至 AC-FR0501-03。

---

### FR-0601 本地 Story Backlog


| Valid | Testable                                 | Decided |
| ----- | ---------------------------------------- | ------- |
| ✅    | ✅                                       | ✅      |

Decision: backlog 最小字段为 story 正文；条目成功进入开发后从 backlog 移除。

- 用户必须能创建本地 story backlog 条目并在列表中查看。
- 用户必须能选中一个 backlog 条目并点击动作按钮，将该条目交给 Louke 现有的新 story 开发流程。
- 本期不要求 backlog 的完整 CRUD、排序或去重，除非后续明确加入。
- 验收引用：AC-FR0601-01 至 AC-FR0601-03。

---

### FR-0701 工作区文件、变更与 Diff


| Valid | Testable                                                           | Decided |
| ----- | ------------------------------------------------------------------ | ------- |
| ✅    | ✅                                                                 | ✅      |

Decision: 文件访问仅限当前 workspace；仅 `story.md`、`spec.md`、`acceptance.md` 可编辑，其他文件只读；符号链接解析后的目标不得越过 workspace 边界。

- Web 页面必须显示工作区文件、当前变更文件及选中变更的 diff。
- 源代码必须只读；允许修改的设计文档必须可在页面中编辑并保存。
- 二进制文件不得预览。
- 超过 500 行的文件在读取或预览正文前必须请求用户批准；用户拒绝时不得加载正文。
- 验收引用：AC-FR0701-01 至 AC-FR0701-04。

---

### FR-0801 Markdown 文档展示


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅    | ✅       | ✅      |

Decision: design documents 发现范围为 `.louke/project/**` 下约定的 Louke 设计 Markdown，且递归发现 `docs/**/*.md`；二进制不预览，超过 500 行的文件须先获用户批准。

- Web 页面必须发现并渲染 design documents、仓库 README 及 `docs/*.md` Markdown 文件。
- 文档导航必须允许用户选择上述文件并看到与当前文件对应的渲染内容。
- 二进制文件和不属于允许文档范围的文件不得经此文档渲染入口展示。
- 超过 500 行的 Markdown 文档适用 FR-0701 的用户批准规则。
- 验收引用：AC-FR0801-01 至 AC-FR0801-03。

---

## Non-Functional Requirements

### NFR-0001 自动化质量门槛


| Valid | Testable                  | Decided |
| ----- | ------------------------- | ------- |
| ✅    | ✅                        | ✅      |

Decision: 用户已明确同意 95% 单元测试覆盖率门槛及不得排除本功能核心模块的统计约束。

- 测试框架为 pytest。
- Definition of Done 为约定的端到端路径全部通过，且单元测试覆盖率不低于 95%。
- 覆盖率统计不得通过排除本功能核心模块来规避门槛。
- 验收引用：AC-NFR0001-01 至 AC-NFR0001-02。

> **Aaron:** 同意

---

### NFR-0101 浏览器兼容性


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅    | ✅       | ✅      |

Decision: 本期兼容性承诺及自动化 Web e2e 覆盖 Chromium 和 Firefox，不承诺 WebKit。

- 自动化 Web e2e 至少覆盖 `project.toml` 当前定义的 Chromium。
- 验收引用：AC-NFR0101-01。

---

### NFR-0201 文件访问安全


| Valid | Testable                                  | Decided |
| ----- | ----------------------------------------- | ------- |
| ✅    | ✅                                        | ✅      |

Decision: 访问仅限当前 workspace，符号链接按解析后的真实目标校验且不得越界；仅 `story.md`、`spec.md`、`acceptance.md` 可写，其他文件只读。

- 文件读取、diff 和保存操作不得访问允许工作区之外的路径。
- 源代码写入请求必须被拒绝；只有明确列入可编辑范围的设计文档可写。
- 验收引用：AC-NFR0201-01 至 AC-NFR0201-02。

---

## Known Constraints

- 当前工作在 `releases/v0.10` 分支起草；后续推进由 Maestro 切换至 `releases/v0.11`。
- 目标用户为 Louke 项目内部使用者。
- 当前 `project.toml` 仍记载旧版本元数据；本 spec 不负责修改该文件。
- Markdown task 必须保持标准 Markdown task 的存储语义和点击可操作性。
- 大于 500 行的文件必须先获得用户批准；二进制文件不预览。

## Out of Scope

- 在 M-SPEC 阶段实际重排 `.louke` 目录、实现服务、编写代码或测试。
- 通用源代码在线编辑器能力；源代码保持只读。
- Backlog 的完整 CRUD、排序和自动去重。
- 未经确认自行决定取消哪些 Agent。
- 本期承诺 Chromium 之外的浏览器兼容性。

## Clarification Log

- 2026-07-11：用户确认 9 项均为 P0。
- 2026-07-11：用户确认 Web 页面需创建与管理 OpenCode 实例。
- 2026-07-11：用户确认工具化取决于 Agent 是否仅调用工具；Maestro 可能保留，并让出部分流程推进职责。
- 2026-07-11：用户确认意图不确定时必须询问用户。
- 2026-07-11：用户确认 Wiki 同时支持页面按钮与每日定时更新，且无源变更时不更新。
- 2026-07-11：用户要求 backlog 保持简单，选择条目并点击后进入现有新 story 流程。
- 2026-07-11：用户确认源代码只读、设计文档可修改、二进制不预览、超过 500 行需先获批准。
- 2026-07-11：用户确认 task 状态切换需持久化源文件。
- 2026-07-11：用户确认所有 `/` 命令透传给 OpenCode；FR-0101 延后至下一个 spec。
- 2026-07-11：用户确认文件访问仅限当前 workspace，仅 `story.md`、`spec.md`、`acceptance.md` 可编辑，其他文件只读。
- 2026-07-11：用户确认状态名为 `Valid`、`Testable`、`Decided`；backlog 最小字段为 story 正文，成功进入开发后移除。
- 待确认项均保留 `Decided: ⚠️`；不得把未回答内容视为同意。

## Lock Bypass Tech Debt

- **Issue**: https://github.com/zillionare/louke/issues/110
- **原因**: `lk agent lex verify-issue` 当前扫描仓库所有 `Feature` label 的 issues 做 schema check，无法按 `--spec` 过滤。仓库有 ~230+ 历史脏 issues（标题 `[FR-002]` 非 `[FR-0002]`、缺 `Requirement ID`/`Spec Link`/`Acceptance Criteria` 段），导致 v0.11 record-lock rc=1。
- **决策**: 用户授权"主线优先"，手动写 `locked: true` frontmatter，跳过 verify-issue 信号。
- **后续**: issue #110 修复并发布后，本 spec 的 record-lock 需要补跑一次以恢复完整 3-signal 校验记录。
