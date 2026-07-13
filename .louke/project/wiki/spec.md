# spec Wiki

## v0.1-001-louke

# louke v0.1 — Framework Init Spec
[source: project/specs/v0.1-001-louke/spec.md#louke-v01--framework-init-spec]
- **Spec ID**: v0.1-001-louke
- **目的**: louke 框架的初始化 spec；作为 verify_issue_schema 的 fixture
- **状态**: fixture（仅供 bats 测试使用，不进入真实工作流）
## 功能需求
[source: project/specs/v0.1-001-louke/spec.md#]
<a id="fr-0001"></a>
**FR-0001**: louke 框架定义 12 个专业 agent
<a id="fr-0002"></a>
**FR-0002**: 阶段表 (M-FOUND/M-SPEC/M-TESTPLAN/M-ARCH/M-LOCK/M-DEV/M-E2E/M-BUGFIX/M-SECURITY/M-MILESTONE)
<a id="fr-0003"></a>
**FR-0003**: 每阶段实施者 ≠ 评审者（构建/验收分离）
<a id="fr-0004"></a>
**FR-0004**: `lk` CLI 提供工具强制的 hold point
<a id="fr-0005"></a>
**FR-0005**: spec/acceptance/test-plan 通过 quote dialogue + Lex 审核锁定

## v0.1-001-specforge

# specforge v0.1 — Spec
[source: project/specs/v0.1-001-specforge/spec.md#specforge-v01--spec]
- **Spec ID**: SPEC-V0.1-001
- **创建日期**: 2026-05-23
- **状态**: 评审中
- **关联 Project**: specforge-0.1 (#3)
## 用户故事
[source: project/specs/v0.1-001-specforge/spec.md#]
| ID | 故事 | 验收条件 | 优先级 |
|----|------|---------|--------|
| US-001 | 作为项目发起人，我通过 Scout Agent 收集项目信息并创建 repo/project，以便项目有基础设施 | Scout 产出 `specs/project-info.md`（含 story/version/repo/project），GitHub repo 可访问，Project 可见 | P0 |
| US-002 | 作为项目发起人，我想运行全部 21 个 Agent 的完整开发流程，以便验证方法论可行 | 全部 21 个 Agent (Scout~Shield + Guide + Librarian) 的 prompt 文件就绪，每个 Agent 可加载执行 | P0 |
| US-003 | 作为新用户，我想通过 `specforge init` 一键初始化项目，以便快速开始使用 | 执行 `specforge init <name>` 后创建目录结构（agents/templates/wiki/specs），终端打印 onboarding 指引 | P0 |
| US-004 | 作为开发者，我想让 Agent 的对话在 GitHub 上显性化、可追踪，以便回顾和审计 | 每个 Agent 对话通过 wiki 条目记录；Sage/Lex 通过 PR Review 讨论 | P1 |
## 功能需求
[source: project/specs/v0.1-001-specforge/spec.md#]
> **锚点约定**：每个 FR 单元前必须有显式锚点 `<a id="fr-XXX"></a>`，供 GitHub issue 反向链接。
<a id="fr-001"></a>
**FR-001**: Scout 收集 story/version/repo 信息并写入 `specs/project-info.md`  可测试性: ✅
<a id="fr-002"></a>
**FR-002**: Scout 创建 GitHub repo（如不存在）和 Project `{repo}-{version}`，配置 status board  可测试性: ✅
<a id="fr-003"></a>
**FR-003**: Scout 验证 issue 权限：创建测试 issue → comment → close  可测试性: ✅
<a id="fr-004"></a>
**FR-004**: Scout 验证 Project 权限：能将 issue 添加到 Project 并移动 status  可测试性: ✅
<a id="fr-005"></a>
**FR-005**: Warden 读取 `specs/project-info.md`，验证所有字段、repo 可访问、Project 存在、测试 issue 已 close  可测试性: ✅
<a id="fr-006"></a>
**FR-006**: Sage 创建 spec 分支、生成初始 spec.md、发 PR 并在 Files Changed 逐行提问  可测试性: ✅
<a id="fr-007"></a>
**FR-007**: Lex 通过 GitHub PR Review 审核 spec，使用 Request changes/Approve  可测试性: ✅
<a id="fr-008"></a>
**FR-008**: 全部 21 个 Agent prompt 文件就绪，会话保存指令已嵌入  可测试性: ✅
<a id="fr-009"></a>
**FR-009**: `specforge init` Shell 脚本可用（curl | bash 安装）  可测试性: ✅
<a id="fr-010"></a>
**FR-010**: Guide Agent 可回答方法论问题，Librarian Agent 可整合 wiki  可测试性: ✅
<a id="fr-011"></a>
**FR-011**: Clerk/Auditor/Probe/Judge/Archer/Cynic/Forge/Prism/Keeper/Herald/Arbiter/Hunter/Shield 的 prompt 按方法论就绪  可测试性: ⚠️ prompt 就绪但需集成测试
## 非功能需求
[source: project/specs/v0.1-001-specforge/spec.md#]
| ID | 需求 | 指标 |
|----|------|------|
| NFR-001 | 所有 Agent 对话通过 Wiki 条目和 GitHub PR 双轨记录 | PR comment + wiki entry 可查 |
| NFR-002 | Agent 的状态传递通过 repo 文件（project-info.md、spec.md 等），不通过聊天文本 | 可被下游 Agent 程序化读取 |
| NFR-003 | 可以有不完美的发布，但不能有不完整的发布 | v0.1 必须包含全部 21 个 Agent + init 工具 |
## 澄清记录
[source: project/specs/v0.1-001-specforge/spec.md#]
| # | 问题 | 用户回答 |
|---|------|---------|
| Q1 | US-001 验收条件？ | Scout 产出 project-info.md，repo 可访问，Project 可见 |
| Q1+ | Scout 的职责边界？ | 1) 创建 repo/版本号/分支/Project；2) 确保 issue 创建和回复权限；3) 确保 Project 读/写/移动 issue 权限 |
| Q2 | v0.1 包含哪些 Agent？ | 全部 21 个 |
| Q3 | v0.1 是否包含 specforge init？ | 需要。可以有不完美的发布，但不能有不完整的发布 |
| Q4 | 后续 Agent 是否在 v0.1 范围？ | 是，全部 21 个 |
| Q5 | PRD 中 V1 标准全部纳入 v0.1？ | 已澄清（Q2/Q3 回答了范围问题） |
| Q6 | v0.1 "自举成功"定义？ | 本项目也要使用 specforge 将要定义的方法来完成 |
## 关联
[source: project/specs/v0.1-001-specforge/spec.md#]
- PRD: `specs/v0.1-001-specforge/prd.md`
- PR: https://github.com/zillionare/specforge/pull/13
## Lex 审核结果
[source: project/specs/v0.1-001-specforge/spec.md#lex-]
- [ ] 所有需求可追踪到用户故事
- [ ] 所有需求可断言（有明确的测试方法）
- [ ] 没有模糊词汇
- [ ] 所有 FR 都有显式锚点 `<a id="fr-XXX"></a>`

## v0.10-001-vditor-redesign

# v0.10-001 — Vditor WYSIWYG 编辑器与界面重构
[source: project/specs/v0.10-001-vditor-redesign/spec.md#v010-001--vditor-wysiwyg-]
## 目标
[source: project/specs/v0.10-001-vditor-redesign/spec.md#]
用 Vditor 替代 textarea+preview 双栏模式，实现 Typora 风格的即时渲染编辑。同时重构页面布局，支持多屏分栏、折叠侧边栏、精简工具栏。
## 功能需求
[source: project/specs/v0.10-001-vditor-redesign/spec.md#]
### FR-0100 Vditor 即时渲染编辑器
[source: project/specs/v0.10-001-vditor-redesign/spec.md#fr-0100-vditor-]
用 Vditor `ir` 模式替换 textarea，markdown 输入即时渲染为富文本。移除右侧 preview 面板。
### FR-0200 文件选择器
[source: project/specs/v0.10-001-vditor-redesign/spec.md#fr-0200-]
编辑器顶部左侧为文件下拉选择框，列出当前 spec 下的所有文档（spec、acceptance、story 等）。切换文件即加载到当前 pane。
### FR-0300 精简工具栏
[source: project/specs/v0.10-001-vditor-redesign/spec.md#fr-0300-]
编辑器顶部右侧为图标工具栏，依次为：
- 下一处 discussion（跳转到下一个 `>>>` 块）
- 折叠所有讨论
- 只显示未决讨论（隐藏含 `[resolved]` 标记的讨论）
- 分屏（新增一列 pane，最多 4 列）
- Save
- Reload
中间显示最后保存时间（hh:mm:ss）。
### FR-0400 多屏分栏
[source: project/specs/v0.10-001-vditor-redesign/spec.md#fr-0400-]
通过分屏按钮新增竖分 pane，最多 4 列。每个 pane 独立加载不同文档，有独立的文件选择器和工具栏。新增 pane 初始为空白。
### FR-0500 折叠侧边栏
[source: project/specs/v0.10-001-vditor-redesign/spec.md#fr-0500-]
sidebar 支持折叠/展开。折叠后变为窄条，点击展开恢复。
### FR-0600 清理页面冗余
[source: project/specs/v0.10-001-vditor-redesign/spec.md#fr-0600-]
移除页面顶部的 eyebrow 标题、h1 标题、lede 描述文本、Last modified 信息。将空间留给文档内容。
### FR-0700 表格样式
[source: project/specs/v0.10-001-vditor-redesign/spec.md#fr-0700-]
- 表头与 body 样式不同（表头加粗、有底色、有下边框）
- 不显示竖表格线
- body 单元格无背景色
### FR-0800 未决讨论过滤
[source: project/specs/v0.10-001-vditor-redesign/spec.md#fr-0800-]
点击「只显示未决讨论」按钮后，含 `[resolved]` 标记的 discussion 块被隐藏。再次点击恢复显示。
## 非功能需求
[source: project/specs/v0.10-001-vditor-redesign/spec.md#]
### NFR-0100 性能
[source: project/specs/v0.10-001-vditor-redesign/spec.md#nfr-0100-]
Vditor CDN 加载不影响首屏；CDN 失败时 fallback 到 textarea。
### NFR-0200 向后兼容
[source: project/specs/v0.10-001-vditor-redesign/spec.md#nfr-0200-]
服务端 API 不变；文档格式不变。

## v0.11-001-web-ide

---
locked: true
locked-at: 2026-07-11T15:30:00Z
locked-by: maestro (record-lock bypassed due to issue #110)
lock-bypass-reason: "verify-issue 扫所有 Feature label 历史的脏 issues,无法在 v0.11 内修复;issue #110 跟踪"
---
# Louke Web IDE 与工作流服务化 — Spec
[source: project/specs/v0.11-001-web-ide/spec.md#louke-web-ide---spec]
- **Spec ID**: v0.11-001-web-ide
- **Created**: 2026-07-11
- **Status**: Locked (bypassed)
- **Target users**: Louke 项目的内部使用者
- **Priority**: 本文全部用户故事与需求均为 P0
> 本文描述需求与边界。可观察、可断言的通过条件集中记录于 `acceptance.md`。
## User Stories
[source: project/specs/v0.11-001-web-ide/spec.md#user-stories]
### US-0001
[source: project/specs/v0.11-001-web-ide/spec.md#us-0001]
story: 作为 Louke 内部使用者，我希望在 Web 页面创建、切换、操作和停止 OpenCode 运行实例，以便不离开浏览器完成交互。
priority: P0
### US-0101
[source: project/specs/v0.11-001-web-ide/spec.md#us-0101]
story: 作为 Louke 内部使用者，我希望由 Louke Server 推进可工具化的工作流，并仅在需要判断时调用保留的角色，以便减少纯工具调用型 Agent。
priority: P0
### US-0201
[source: project/specs/v0.11-001-web-ide/spec.md#us-0201]
story: 作为 Louke 内部使用者，我希望系统在执行每条指令前识别意图并选择或确认正确流程，以免错误启动开发或修改流程。
priority: P0
### US-0301
[source: project/specs/v0.11-001-web-ide/spec.md#us-0301]
story: 作为 Louke 内部使用者，我希望浏览统一、可追溯且可更新的 Wiki，以便获得项目当前事实和技术裁决。
priority: P0
### US-0401
[source: project/specs/v0.11-001-web-ide/spec.md#us-0401]
story: 作为 Louke 维护者，我希望 `.louke` 中的服务、评审、会话与 Wiki 产物有明确归档位置，以便管理 Louke 元数据。
priority: P0
### US-0501
[source: project/specs/v0.11-001-web-ide/spec.md#us-0501]
story: 作为 Louke 内部使用者，我希望在 Web 页面切换 FR/NFR 的 Markdown task 状态并持久化，以便直接完成需求评审。
priority: P0
### US-0601
[source: project/specs/v0.11-001-web-ide/spec.md#us-0601]
story: 作为 Louke 内部使用者，我希望先把新 story 存入本地 backlog，再选择条目进入现有开发流程，以便延后启动开发。
priority: P0
### US-0701
[source: project/specs/v0.11-001-web-ide/spec.md#us-0701]
story: 作为 Louke 内部使用者，我希望查看工作区文件、变更和 diff，并编辑允许修改的设计文档，以便在 Web IDE 中评审工作。
priority: P0
### US-0801
[source: project/specs/v0.11-001-web-ide/spec.md#us-0801]
story: 作为 Louke 内部使用者，我希望渲染查看 design documents、README 和 `docs/*.md`，以便集中阅读项目文档。
priority: P0
## Usage Scenarios
[source: project/specs/v0.11-001-web-ide/spec.md#usage-scenarios]
### scenario-0001 OpenCode 交互
[source: project/specs/v0.11-001-web-ide/spec.md#scenario-0001-opencode-]
用户在 Web 页面创建或选择实例，发送消息或支持的命令，观察输出和运行状态，必要时停止实例。
### scenario-0101 指令路由
[source: project/specs/v0.11-001-web-ide/spec.md#scenario-0101-]
用户提交指令；系统先显示识别出的意图与拟执行动作；分类不确定时先询问，确认后进入对应 Louke 流程。
### scenario-0201 Wiki 更新
[source: project/specs/v0.11-001-web-ide/spec.md#scenario-0201-wiki-]
用户点击更新按钮，或每日定时任务检测到源文档变化后，系统重建 Wiki 并保留事实来源链接。
### scenario-0301 Backlog 转开发
[source: project/specs/v0.11-001-web-ide/spec.md#scenario-0301-backlog-]
用户创建 backlog 条目，在列表中选中一项并点击进入开发，随后衔接 Louke 现有的新 story 开发流程。
### scenario-0401 工作区阅读与设计文档编辑
[source: project/specs/v0.11-001-web-ide/spec.md#scenario-0401-]
用户浏览文件、Git 变更和 diff；源代码保持只读，允许的设计文档可以编辑和保存。
## Functional Requirements
[source: project/specs/v0.11-001-web-ide/spec.md#functional-requirements]
### FR-0001 OpenCode 实例与会话操作
[source: project/specs/v0.11-001-web-ide/spec.md#fr-0001-opencode-]
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
[source: project/specs/v0.11-001-web-ide/spec.md#fr-0101-louke-server--agent-]
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
[source: project/specs/v0.11-001-web-ide/spec.md#fr-0201-]
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
[source: project/specs/v0.11-001-web-ide/spec.md#fr-0301--wiki]
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
[source: project/specs/v0.11-001-web-ide/spec.md#fr-0401-louke-]
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
[source: project/specs/v0.11-001-web-ide/spec.md#fr-0501-fr-nfr-task-]
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
[source: project/specs/v0.11-001-web-ide/spec.md#fr-0601--story-backlog]
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
[source: project/specs/v0.11-001-web-ide/spec.md#fr-0701--diff]
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
[source: project/specs/v0.11-001-web-ide/spec.md#fr-0801-markdown-]
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
[source: project/specs/v0.11-001-web-ide/spec.md#non-functional-requirements]
### NFR-0001 自动化质量门槛
[source: project/specs/v0.11-001-web-ide/spec.md#nfr-0001-]
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
[source: project/specs/v0.11-001-web-ide/spec.md#nfr-0101-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅    | ✅       | ✅      |
Decision: 本期兼容性承诺及自动化 Web e2e 覆盖 Chromium 和 Firefox，不承诺 WebKit。
- 自动化 Web e2e 至少覆盖 `project.toml` 当前定义的 Chromium。
- 验收引用：AC-NFR0101-01。
---
### NFR-0201 文件访问安全
[source: project/specs/v0.11-001-web-ide/spec.md#nfr-0201-]
| Valid | Testable                                  | Decided |
| ----- | ----------------------------------------- | ------- |
| ✅    | ✅                                        | ✅      |
Decision: 访问仅限当前 workspace，符号链接按解析后的真实目标校验且不得越界；仅 `story.md`、`spec.md`、`acceptance.md` 可写，其他文件只读。
- 文件读取、diff 和保存操作不得访问允许工作区之外的路径。
- 源代码写入请求必须被拒绝；只有明确列入可编辑范围的设计文档可写。
- 验收引用：AC-NFR0201-01 至 AC-NFR0201-02。
---
## Known Constraints
[source: project/specs/v0.11-001-web-ide/spec.md#known-constraints]
- 当前工作在 `releases/v0.10` 分支起草；后续推进由 Maestro 切换至 `releases/v0.11`。
- 目标用户为 Louke 项目内部使用者。
- 当前 `project.toml` 仍记载旧版本元数据；本 spec 不负责修改该文件。
- Markdown task 必须保持标准 Markdown task 的存储语义和点击可操作性。
- 大于 500 行的文件必须先获得用户批准；二进制文件不预览。
## Out of Scope
[source: project/specs/v0.11-001-web-ide/spec.md#out-of-scope]
- 在 M-SPEC 阶段实际重排 `.louke` 目录、实现服务、编写代码或测试。
- 通用源代码在线编辑器能力；源代码保持只读。
- Backlog 的完整 CRUD、排序和自动去重。
- 未经确认自行决定取消哪些 Agent。
- 本期承诺 Chromium 之外的浏览器兼容性。
## Clarification Log
[source: project/specs/v0.11-001-web-ide/spec.md#clarification-log]
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
[source: project/specs/v0.11-001-web-ide/spec.md#lock-bypass-tech-debt]
- **Issue**: https://github.com/zillionare/louke/issues/110
- **原因**: `lk agent lex verify-issue` 当前扫描仓库所有 `Feature` label 的 issues 做 schema check，无法按 `--spec` 过滤。仓库有 ~230+ 历史脏 issues（标题 `[FR-002]` 非 `[FR-0002]`、缺 `Requirement ID`/`Spec Link`/`Acceptance Criteria` 段），导致 v0.11 record-lock rc=1。
- **决策**: 用户授权"主线优先"，手动写 `locked: true` frontmatter，跳过 verify-issue 信号。
- **后续**: issue #110 修复并发布后，本 spec 的 record-lock 需要补跑一次以恢复完整 3-signal 校验记录。

## v0.11-002-web-ui-integration

---
locked: true
locked-at: 2026-07-12T05:50:34Z
locked-by: lk agent sage record-lock
---
# Louke Web IDE — Web UI 集成 (v0.11-001 补漏) — Spec
[source: project/specs/v0.11-002-web-ui-integration/spec.md#louke-web-ide--web-ui--v011-001---spec]
- **Spec ID**: v0.11-002-web-ui-integration
- **Created**: 2026-07-12
- **Status**: Draft
- **Priority**: P0
> 本文只补齐 v0.11-001 已锁定需求的 Web UI 集成缺口；可观察、可断言的通过条件见 `acceptance.md`。
## Story
[source: project/specs/v0.11-002-web-ui-integration/spec.md#story]
作为 Louke 内部使用者，我希望既有 Web 页面连接 v0.11-001 已交付的六个 sub-app，并能通过浏览器完成关键操作，以便 Web IDE 不再只展示静态或 mock 页面，而是真正使用已锁定的 API 能力。
## Decided
[source: project/specs/v0.11-002-web-ui-integration/spec.md#decided]
- Web UI 集成范围为：在 `louke/web/app.py` mount 六个 sub-app、为既有页面增加 JavaScript client、升级 Playwright e2e。
- 复用 v0.11-001 已实现的 `opencode`、`intent`、`wiki`、`backlog`、`files`、`tasks` 六个 sub-app；不改变其内部逻辑，只接入主 Web app。
- 复用 v0.10 的 home、wiki、models、docs、login 页面模板；相关数据与操作改为通过 JavaScript 调用真实 API，不使用页面 mock 数据。
- NFR-0101 的浏览器验证在本补漏 spec 中升级为实际点击、填写表单和页面状态断言，而非只 GET 静态页面。
- 测试分为两层：v0.11-001 已有 API e2e 与本期新增 UI e2e；两层分别验证接口契约和浏览器用户流。
## Usage Scenarios
[source: project/specs/v0.11-002-web-ui-integration/spec.md#usage-scenarios]
- 用户从 Web 导航进入功能页，创建或选择数据、提交操作，并在页面看到来自真实 API 的结果。
- 用户刷新页面后，重新读取 API 数据并看到已持久化的 backlog、文档或 task 状态。
## Functional Requirements
[source: project/specs/v0.11-002-web-ui-integration/spec.md#functional-requirements]
### FR-0202 Web UI 路由与导航
[source: project/specs/v0.11-002-web-ui-integration/spec.md#fr-0202-web-ui-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅ | ✅ | ✅ |
- `louke/web/app.py` 必须接入六个 sub-app，使 v0.11-001 `interfaces.md` 锁定的 `/api/opencode`、`/api/intent`、`/api/wiki`、`/api/backlog`、`/api/files`、`/api/tasks` 公共端点可由同一 Web server 访问。
- 既有 home（`/`）、wiki（`/wiki`）、models（`/models`）和 docs（`/docs/...`）页面及其功能导航必须可访问，并通过 JavaScript client 调用对应真实 API。
- 页面不得以硬编码或 mock 数据伪造成功结果；API 失败时必须显示可观察的失败反馈。
- 验收引用：AC-FR0202-01 至 AC-FR0202-04。
---
### FR-0203 OpenCode Web 交互
[source: project/specs/v0.11-002-web-ui-integration/spec.md#fr-0203-opencode-web-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅ | ✅ | ✅ |
- home 页面必须允许用户创建实例、选择实例、向选中实例发送消息并看到该实例的消息与状态回显。
- 页面实例列表和消息结果必须来自已接入的 OpenCode API；切换实例不得混淆会话输出。
- 验收引用：AC-FR0203-01 至 AC-FR0203-04。
---
### FR-0204 Backlog Web 交互
[source: project/specs/v0.11-002-web-ui-integration/spec.md#fr-0204-backlog-web-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅ | ✅ | ✅ |
- backlog 页面必须允许用户填写并提交 story、查看 API 返回的 backlog 列表、选择条目并触发“进入开发”。
- 未选择条目时不得启动开发，并须显示可观察反馈；成功进入开发的条目须从页面列表移除。
- 验收引用：AC-FR0204-01 至 AC-FR0204-03。
---
### FR-0205 Files Web 交互
[source: project/specs/v0.11-002-web-ui-integration/spec.md#fr-0205-files-web-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅ | ✅ | ✅ |
- files 页面必须通过 Files API 展示工作区树、Git 变更列表和选中变更的 diff。
- 用户必须能打开允许编辑的设计文档、修改并保存；刷新或重新打开后显示已持久化内容。
- v0.11-001 锁定的只读、二进制、500 行批准和 workspace 边界规则继续适用，不在本 spec 改写。
- 验收引用：AC-FR0205-01 至 AC-FR0205-04。
---
### FR-0206 Tasks Web 交互
[source: project/specs/v0.11-002-web-ui-integration/spec.md#fr-0206-tasks-web-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅ | ✅ | ✅ |
- docs 页面必须显示所选 FR/NFR 的 `Valid`、`Testable`、`Decided` 三个 task checkbox，并通过 Tasks API 分别切换。
- 切换只能改变目标 task；页面重新加载后必须显示持久化状态。
- 验收引用：AC-FR0206-01 至 AC-FR0206-03。
---
## Non-Functional Requirements
[source: project/specs/v0.11-002-web-ui-integration/spec.md#non-functional-requirements]
### NFR-0102 Playwright 真 UI e2e
[source: project/specs/v0.11-002-web-ui-integration/spec.md#nfr-0102-playwright--ui-e2e]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅ | ✅ | ✅ |
- Playwright 必须通过真实浏览器的导航、点击、表单填写及页面状态断言覆盖 FR-0203 至 FR-0206 的关键成功路径，不得以直接调用 API 代替 UI 操作。
- UI e2e 必须与既有 API e2e 分层保留，并至少在 v0.11-001 NFR-0101 已承诺的 Chromium 与 Firefox 中执行。
- 验收引用：AC-NFR0102-01 至 AC-NFR0102-05。
---
## Known Constraints and Exclusions
[source: project/specs/v0.11-002-web-ui-integration/spec.md#known-constraints-and-exclusions]
- v0.11-001 的 spec、acceptance、interfaces、architecture、test-plan 均已锁定，本 spec 不修改其内容或 37 个 AC。
- FR-0101 Louke Server Agent 工具化（#99）不在本期，继续延后至后续 spec。
- 六个 sub-app 的业务逻辑和既有接口契约不在本期修改范围；本期只负责主 app 接入与 Web UI 消费。
- 本期不重设计 v0.10 页面模板，也不新增 v0.11-001 未定义的服务能力。
## Clarification Log
[source: project/specs/v0.11-002-web-ui-integration/spec.md#clarification-log]
- 2026-07-12：用户明确本 spec 为 v0.11-001 的补漏，范围限定为六个 sub-app 接入、真实 Web UI 用户流与 Playwright 真点击验证。

## v0.2-002-specforge

# specforge 模型配置 — Spec
[source: project/specs/v0.2-002-specforge/spec.md#specforge---spec]
- **Spec ID**: v0.2-002-specforge
- **创建日期**: 2026-06-02
- **状态**: 已锁定
## 用户故事
[source: project/specs/v0.2-002-specforge/spec.md#]
| ID | 故事 | 验收条件 | 优先级 |
|----|------|---------|--------|
| US-001 | 作为 specforge 用户，我想在 `init` 时输入可用模型列表，以便 specforge 为各 Agent 匹配合适模型 | init 交互提示后，`.opencode/agents/` 下生成带 frontmatter 的 agent 文件 | P0 |
| US-002 | 作为 specforge 用户，我想选择国内版或全局版模型策略 | 选择后 specforge 使用对应能力矩阵进行匹配 | P0 |
| US-003 | 作为 specforge 用户，我想手动控制每个 Agent 的模型分配 | 可逐 Agent 指定模型 | P0 |
## 功能需求
[source: project/specs/v0.2-002-specforge/spec.md#]
> **锚点约定（必读）**：每个 FR 单元前必须有显式 HTML 锚点 `<a id="fr-XXX"></a>`（小写、3 位零填充）。
<a id="fr-001"></a>
**FR-001**: specforge init 交互式收集可用模型列表，输入方式为逗号分隔字符串（如 `deepseek-v4-pro, gpt-5.5, kimi-k2.6`）  可测试性: ✅
<a id="fr-002"></a>
**FR-002**: init 交互式询问区域策略（国内版 / 全局版），用户选择后加载对应能力矩阵  可测试性: ✅
<a id="fr-003"></a>
**FR-003**: 根据用户选择的区域和可用模型，打印推荐表（Agent 名称 → 推荐档位 → 推荐模型），供用户手动逐 Agent 指定模型  可测试性: ✅
<a id="fr-004"></a>
**FR-004**: 生成 OpenCode 兼容的 agent 配置文件到 `.opencode/agents/*.md`，frontmatter 包含 `model`、`description`、`mode`（默认 `all`）  可测试性: ✅
<a id="fr-005"></a>
**FR-005**: 模型配置持久化到 `.specforge/models.json`，记录区域策略、可用模型列表、Agent→模型映射  可测试性: ✅
<a id="fr-006"></a>
**FR-006**: 当可用模型不足以覆盖所有档位时，自动降档到最接近的低档模型（如无 S 档模型则用 A 档替代）  可测试性: ✅
<a id="fr-007"></a>
**FR-007**: specforge init 输出 onboarding 指引，说明 `.opencode/agents/` 配置完成及后续 Agent 加载方式  可测试性: ✅
## 非功能需求
[source: project/specs/v0.2-002-specforge/spec.md#]
| ID | 需求 | 指标 |
|----|------|------|
| NFR-001 | 模型矩阵数据与实际代码解耦 | 能力矩阵存为独立数据文件（JSON），不硬编码在主逻辑中 |
| NFR-002 | init 交互过程有输入校验和错误提示 | 非法输入给出具体修复指引 |
## 澄清记录（Sage Interview 产出）
[source: project/specs/v0.2-002-specforge/spec.md#sage-interview-]
| # | 问题 | 用户回答 |
|---|------|---------|
| Q1 | OpenCode agent.md frontmatter 含哪些字段？ | C: model + description + mode（全量，Kilo 兼容） |
| Q2 | 国内版/全局版选择方式？ | A: 交互式询问（init 过程打印选项） |
| Q3 | 用户输入可用模型的方式？ | A: 逗号分隔字符串 |
| Q4 | 同一档位多个可用模型时的选择策略？ | B: 打印推荐表，用户手动逐 Agent 指定 |
| Q5 | 可用模型不足以覆盖所有档位时？ | A: 自动降档到最接近的低档模型 |
| Q6 | 模型配置是否持久化？ | A: 写入 `.specforge/models.json` |
## Lex 审核结果
[source: project/specs/v0.2-002-specforge/spec.md#lex-]
- [x] 所有需求可追踪到用户故事
- [x] 所有需求可断言（有明确的测试方法）
- [x] 没有模糊词汇
- [x] 所有 FR 都有显式锚点 `<a id="fr-XXX"></a>`
**审核结论**: ✅ APPROVED (2026-06-02)
**非阻塞观察**: PRD 中"自动匹配"表述已被 Q4 澄清改为"手动指定"，建议用户手动更新 PRD。

## v0.3-003-init-adopt-mode

# init 子命令支持既存项目非破坏性合并 — Spec
[source: project/specs/v0.3-003-init-adopt-mode/spec.md#init---spec]
- **Spec ID**: 003-init-adopt-mode
- **创建日期**: 2026-06-14
- **状态**: 草稿（Sage Interview 进行中）
## 用户故事
[source: project/specs/v0.3-003-init-adopt-mode/spec.md#]
| ID | 故事 | 验收条件 | 优先级 |
|----|------|---------|--------|
| US-001 | 作为 specforge 用户，我希望 `init` 能识别"目标路径已存在"并转入非破坏性合并模式，以便把 specforge 接入存量项目时不需要手工执行等价命令 | AC-1: `init <existing-path>` 不报错；AC-2: 既存源代码字节级不变 | P0 |
| US-002 | 作为 specforge 用户，我希望 adopt 模式能清晰地报告哪些文件被新增、哪些被跳过、哪些被备份，以便我能 audit 这次改动的范围 | AC-3: 输出 `[+]` / `[=]` / `[!]` 三档分类 | P1 |
| US-003 | 作为 specforge 用户，我希望在合并前能用 `--dry-run` 预览会做什么，以便我能确认不会破坏现有内容 | AC-4: `--dry-run` 后 working tree 字节级不变 | P0 |
## 功能需求
[source: project/specs/v0.3-003-init-adopt-mode/spec.md#]
> **锚点约定**：每个 FR 单元前必须有显式 HTML 锚点 `<a id="fr-XXX"></a>`（小写、3 位零填充）。FR-008 起新编号，与现有 FR-001~FR-007 不冲突。
<a id="fr-008"></a>
**FR-008**: `init` 子命令必须能识别"目标参数是既存路径 vs 新项目名"。**判定原则**：[待澄清-1]
<a id="fr-009"></a>
**FR-009**: 当判定为 adopt 模式时，`init <existing-path>` 必须不破坏既存路径下的任何源代码（递归扫描验证字节级不变）。可测试性: ✅
<a id="fr-010"></a>
**FR-010**: ~~adopt 模式对 `agents/`、`templates/`、`specs/`、`wiki/{pages,decisions}/`、`raw/sources/` 这 5 个目录的处理：**只创建缺的，不动有的**。~~
> **已废弃（superseded by v0.5-005 FR-020 + FR-030）** — 2026-06-23
> 旧路径（根目录 `wiki/`、`raw/`）已收归到 `.specforge/wiki/`、`.specforge/raw/`。
> 详见 `wiki/decisions/006-namespace-cleanup.md`。
> 锚点保留以避免引用混淆；不再进入新功能的 ready 判定。
> 有效需求: ❌（deprecated） | 可测性: ✅ | 是否已决定: ✅
<a id="fr-011"></a>
**FR-011**: adopt 模式对 `agents/*.md` 和 `templates/*.md` 文件的合并策略：**默认 skip + warn 同名已有文件**，可选 `--backup`（备份为 `.bak`）或 `--force`（覆盖）。可测试性: ✅
<a id="fr-012"></a>
**FR-012**: adopt 模式必须支持 `--dry-run` flag，触发后只打印会做什么，不实际改 working tree。可测试性: ✅
<a id="fr-013"></a>
**FR-013**: adopt 模式结束后必须打印分档报告，分类：[+] 新增、[=] 跳过（已有同名）、[!] 备份（启用 --backup 时）。可测试性: ✅
<a id="fr-014"></a>
**FR-014**: 向既存 `.gitignore` 追加 specforge 相关条目（不是覆盖），如果条目已存在则不重复添加。[待澄清-2] 追加哪些条目？ 可测试性: ✅
<a id="fr-015"></a>
**FR-015**: 既存 `init <bare-name>` 命令行为必须保持向后兼容：裸名 + 已存在目录 → 报错（与现有 `die "Directory '$PROJECT_NAME' already exists"` 一致）。可测试性: ✅
## 非功能需求
[source: project/specs/v0.3-003-init-adopt-mode/spec.md#]
| ID | 需求 | 指标 |
|----|------|------|
| NFR-001 | 既存 `bin/specforge` 总行数增量 | ≤ 150 行（含 dry-run、adopt 分支、报告函数） |
| NFR-002 | bats 测试新增 case 数 | ≥ 8（覆盖 5 个核心 FR + 3 个边界 case） |
| NFR-003 | 既存 `init <bare-name>` 行为字节级不变 | 对照 `tests/test_init.bats` 全部现有 case 通过 |
| NFR-004 | 文档更新覆盖 README §8.3 和 agents/README.md | 必改 |
## 澄清记录（Sage Interview 产出）
[source: project/specs/v0.3-003-init-adopt-mode/spec.md#sage-interview-]
| # | 问题 | 用户回答 |
|---|------|---------|
| 1 | [待澄清-1] 判定 "既存路径 vs 新项目名" 的规则？我倾向：**参数含 `/`、以 `.` 开头、或以 `~` 开头 → 既存路径**；否则视为裸名（新项目名）。这样 `init .`、`init ./proj`、`init /abs/path` 都走 adopt；`init myproj` 走新建。 | [待用户回答] |
| 2 | [待澄清-2] `.gitignore` 追加哪些条目？候选：`.kilo/`、`wiki/.cache`、`specs/.draft/`、`raw/sources/` 是否纳入？ | [待用户回答] |
| 3 | [待澄清-3] 默认行为如果既存文件**与 SPECFORGE_HOME 版本不同**（比如用户改过 `agents/Maestro.md`），应该 skip+warn 还是直接覆盖？我倾向 skip+warn（保护用户修改）。 | [待用户回答] |
| 4 | [待澄清-4] 是否需要 `--with-issue-template` flag 一并安装 `.github/ISSUE_TEMPLATE/feature.yml`？我倾向默认不装（避免与现有 GitHub 设置冲突），仅在显式 flag 时安装。 | [待用户回答] |
| 5 | [待澄清-5] 报告输出的格式：纯文本分档？还是 `--json` 可选输出机器可读？我倾向**默认纯文本**（用户友好），可选 `--json` flag 给 CI/script 用。 | [待用户回答] |
| 6 | [待澄清-6] 当目标路径不是 git repo 时怎么办？我倾向：**adopt 模式要求目标必须是 git repo**（否则报错），因为 specforge 流程严重依赖 git commit hash 回溯。 | [待用户回答] |
## Lex 审核结果
[source: project/specs/v0.3-003-init-adopt-mode/spec.md#lex-]
- [ ] 所有需求可追踪到用户故事
- [ ] 所有需求可断言（有明确的测试方法）
- [ ] 没有模糊词汇
- [ ] 所有 FR 都有显式锚点 `<a id="fr-XXX"></a>`
## 附录：FR-001~FR-007 历史
[source: project/specs/v0.3-003-init-adopt-mode/spec.md#fr-001fr-007-]
为避免编号冲突，本文 FR 从 008 起。原 specforge v0.2 spec 的 FR-001~FR-007 编号保留不变（属于"模型配置"主题）。

## v0.4-004-quote-dialogue

# Quote Dialogue 需求澄清 — Spec
[source: project/specs/v0.4-004-quote-dialogue/spec.md#quote-dialogue---spec]
- **Spec ID**: v0.4-004-quote-dialogue
- **创建日期**: 2026-06-15
- **状态**: 草稿
## 用户故事
[source: project/specs/v0.4-004-quote-dialogue/spec.md#]
<a id="us-010"></a>
### US-010
[source: project/specs/v0.4-004-quote-dialogue/spec.md#us-010]
story: 作为 spec 作者，我想用 markdown 的 quote 语法在 IDE 中直接跟 sage 对话澄清需求，以便免去 PR review 的繁琐流程。
priority: P0
> **Aaron**: 这是测试问题，请回答并关闭。
>> **Sage:** 收到，这条用作用例覆盖了"speaker 提取允许 `**Name**:` (无冒号) 与 `**Name:**` (有冒号) 两种" lex 路径。 ✓
<a id="us-020"></a>
### US-020
[source: project/specs/v0.4-004-quote-dialogue/spec.md#us-020]
story: 作为 spec 作者，我想既能在 sage 提问处回复，也能对 spec 任意段落提出自己的疑问，以便澄清工作既可由 sage 驱动，也可由作者主动发起。
priority: P0
## 用户使用场景
[source: project/specs/v0.4-004-quote-dialogue/spec.md#]
### scenario-010
[source: project/specs/v0.4-004-quote-dialogue/spec.md#scenario-010]
1. 用户在 IDE 中打开 `specs/{spec-id}/spec.md`
2. 看到 sage 留下的 `> **Sage:**` 提问块，作者在下方插入 `>> **Aaron:**` 回复。这里 Aaron 是用户名示例。
3. 看到 spec 中某段自己不确定的描述，作者直接在段落后插入 `> **Aaron:** {question}` 块
4. sage 在下一个回合读完整 spec，把所有新 `>` 块按 "speaker / depth" 解析，给出 `>>>` 回复
5. 一轮轮迭代，直到所有单元的 `resolved: ✅` 且没有未解决的 quote 块
## 功能需求
[source: project/specs/v0.4-004-quote-dialogue/spec.md#]
> **格式约定（必读）**: 每个 FR 单元都由三级标题+空格+FR-XXX（大写，3位零填充）+ {title} 引起，随后是需求描述和元数据，遇到以下情况时，本 FR 单元结束：
1. 遇到一个二级标题
2. 遇到下一个 FR 单元
3. 文件结尾
合格的 FR 单元必须满足以上格式要求。
> **编号约定(必读)**： FR 的编码采用3位数字，0填充，初稿时从10开始，每次增加10；以便后续可以随时在中间插入新的 FR。
> **必读**： FR-XXX 编号即该需求的 id。禁止删除已有需求 id，以避免引用混淆；如需废弃某 FR，在其元数据中, valid 改为 false，并在澄清记录中说明。
<a id="fr-010"></a>
### FR-010 quote-block 语法识别
[source: project/specs/v0.4-004-quote-dialogue/spec.md#fr-010-quote-block-]
`tools/quote_parser.py` 必须能够：
- 解析 `> **Name:**` 这种以加粗的 `**Name:**` 开头的 quote 块
- 区分 speaker (从 `**Name:**` 取) 与 depth (从 `>` 的层数取)
- 当同一段后存在多轮块时，按 depth 升序组织成对话链
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
<a id="fr-020"></a>
### FR-020 speaker 身份由加粗 name 决定
[source: project/specs/v0.4-004-quote-dialogue/spec.md#fr-020-speaker--name-]
speaker 身份**不**由 `>` 嵌套层数 (depth) 推断，而是由 `**Name:**` 前的加粗文本决定。depth 仅用于排序与"在 IDE 中自然缩进显示"。
**加宽容忍**：speaker 提取接受以下格式：
| 形式                 | 例                   | 备注                                                                  |
| -------------------- | -------------------- | --------------------------------------------------------------------- |
| 加粗, 冒号在 `**` 内 | `> **Name:** hello`  | 标准 markdown 加粗, `:` 在 bold 内                                    |
| 加粗, 冒号在 `**` 外 | `> **Name**: hello`  | 部分 IDE 自动补冒号                                                   |
| 加粗, 无冒号         | `> **Name** hello ✓` | 加粗后直接接内容                                                      |
| Plain (ASCII id)     | `> Aaron: hello`     | 无加粗, 必须是 ASCII identifier (`A-Za-z0-9_-`), 不接受纯中文 speaker |
**说明**: 纯中文 speaker 单独 + `:` 的形式 (如 `> 格式约定: ...`) 不被识别为 quote 对话, 仍按说明文字处理。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
<a id="fr-030"></a>
### FR-030 状态标记
[source: project/specs/v0.4-004-quote-dialogue/spec.md#fr-030-]
每条 quote 块的尾部（块内最后一行）允许用以下 5 种 status marker 之一收尾：
| marker           | 含义             |
| ---------------- | ---------------- |
| `✓`              | 已解决           |
| `[open]`         | 仍开放，等下一轮 |
| `[blocked-by-N]` | 被 quote N 阻塞  |
| `[wontfix]`      | 决定不处理       |
| `[superseded]`   | 已被新版本替代   |
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
<a id="fr-040"></a>
### FR-040 unit 划分与 yaml 元数据
[source: project/specs/v0.4-004-quote-dialogue/spec.md#fr-040-unit--yaml-]
`tools/quote_parser.py` 必须能：
- 切分 `### US/FR/NFR-XXX` 单元
- 解析每个单元末尾的 yaml 块（`testability / resolved / valid`）
- 把 quote 块按"**同一 ## 顶节**内 + 最近的 `### US/FR/NFR-XXX` 单元"规则归到某个 unit
**说明型 `>` 块过滤**：落在 `## 顶节` 内但**不属于任何 `### US/FR/NFR-XXX` 单元**、且**没有显式 status marker** 的 quote 块（如 `> **格式约定**: ...` 这类前言说明）应被丢弃，不计入对话统计、ready 判定、unit 关联。
**非 unit 段落（如 scenario）的虚拟 unit**：quote 出现在 `## 用户使用场景` 等**没有 yaml meta** 的大节时，按"该 quote 之前第一个非空非 quote 文本行"作为上下文锚定生成虚拟 unit（用于审计 trace），但不强制要求该虚拟 unit 走 `--check-ready` 判定。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
> **Sage:** FR-040 里"按它所在 spec 内的'上下文段落'归到某个 unit"，具体规则请你澄清：
> - Q1: 你的预期是 **preceding-unit**（quote 块往上找到最近的 `### US/FR/NFR-XXX` 单元），还是 **section**（按 `## 用户故事 / ## 功能需求 / ## 非功能需求` 大节归属）？
>> **Aaron**: ### US/FR/NFR-XXX
> - Q2: 如果 quote 块出现在 `## 用户使用场景` 这种没有 unit 的大节里，应该归到哪里（归到上一个 FR / 报错 / 标 unassigned）？
>> **Aaron**: 非 FR/NFR，没有meta 字段, 在 quote block内部解析是否完成。如果要找上下文，则它之前第一个非 quote block 的文本行就是（注意是非空文本行）
>>> **Sage:** 收到。Q1 采纳 preceding-unit；Q2 采纳"虚拟 unit 上下文锚定"。同时已实现 `> **Name**:` / `**Name:**` 两种格式都识别、explanatory `>` 块过滤。 ✓
> **Lex:** 💡 建议: FR-040 的"虚拟 unit 上下文锚定"概念, 在 `tools/quote_parser.py` 数据结构上没明说。Lex 看到 `Unit` dataclass 的 `last_quote / open_quotes` 字段已能承载, 但 spec 里没显式说。建议在 FR-040 加一句"虚拟 unit 复用 `Unit` 结构 (heading_line = quote 所在行), 但**不**进入 `is_ready()` 判定"。本条 Lex 接受当前实现, 非阻塞。 ✓
<a id="fr-050"></a>
### FR-050 unit-ready 判定
[source: project/specs/v0.4-004-quote-dialogue/spec.md#fr-050-unit-ready-]
`tools/quote_parser.py --check-ready` 应当：
- 对 FR/NFR 单元：要求 `yaml.resolved == ✅` **且** 该 unit 下 `last_quote.status != "open"`（**chain-wise 判定**：对话链只要最后一条 close 即可视为 closed, 中间未标 marker 的 reply 由后续 close 覆盖）
- 对 US 单元：要求最后一条 quote 状态是 `✓`/`[wontfix]`/`[superseded]`，或 unit 内无 quote
- 对 scenario 等"叙事性"段落：本身不参与 unit 切分（不算 unit），但其中的 quote 仍可被解析并归属到邻近 US/FR/NFR 虚拟上下文
- 输出每个 unit 的 ready 状态及阻塞原因
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
> **Sage:** FR-050 我倾向先只覆盖 FR/NFR，但需要你拍板：
> - Q3: US (用户故事) 单元要不要也走 `--check-ready` 判定？理由：US 主要是"我想要 X"，没 quote 时默认可视作 ready；但用同一套规则更简单。
>> **Aaron**: 需要，并且第101行已有说明
> - Q4: "用户使用场景" (scenario) 算不算 unit？我倾向不算（它是 narrative，不是 actionable requirement）。
>> **Aaron**: 算普通文本，但同样可能存在多轮澄清的需要。
>>> **Sage:** 收到。Q3 采纳"US 走 check-ready"（你已确认）；Q4 采纳"scenario 不算 unit，但 quote 链仍可被解析并被关联到邻近 unit 的虚拟上下文"。FR-050 spec 已同步更新。 ✓
<a id="fr-060"></a>
### FR-060 用户侧编辑器不需扩展
[source: project/specs/v0.4-004-quote-dialogue/spec.md#fr-060-]
用户只用原生 IDE 即可完成澄清（无需装 markdown 插件或扩展工具）。quote 块只是普通 markdown。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
<a id="fr-070"></a>
### FR-070 agent 侧无 PR 依赖
[source: project/specs/v0.4-004-quote-dialogue/spec.md#fr-070-agent--pr-]
sage / lex 在执行 quote dialogue 流程时，不应触发任何 GitHub PR 流程（包括开 PR、request review、PR review 评论）。所有"评审/澄清"动作都只发生在 spec.md 的 quote 块上。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| false | ✅ | ✅ |
> **Lex:** FR-070 是负向断言 ("不应触发 PR 流程"), 缺正向 AC。
> 修改建议: 改写为可断言: "对 `agents/Sage.md` `agents/Lex.md` `bin/specforge` 三处源码 grep `gh pr|gh api.*reviews|gh pr comment`, 匹配数 = 0" [open]
>> Aaron: invalid。只要我们没要求，没提供工具，就不会有主动创建 PR 这回事。
>>> **Sage:** 收到, Lex 的负向重写建议被 Aaron 拒绝 (理由: 现状已足够, 不会主动创建 PR)。FR-070 spec 保持原样, yaml.valid 维持 `✅`。 ✓
## 非功能需求
[source: project/specs/v0.4-004-quote-dialogue/spec.md#]
> **必读**: 本节的格式、编号等要求同 FR，此处省略。
<a id="nfr-010"></a>
### NFR-010 ~~废弃~~ quote 解析在 1MB spec 内 < 1s
[source: project/specs/v0.4-004-quote-dialogue/spec.md#nfr-010--quote--1mb-spec---1s]
`tools/quote_parser.py` 解析单文件 < 1MB 的 spec.md，端到端解析时间 < 1 秒（不含 yaml 解析之外的 IO）。
> **废弃说明 (Aaron 决定, sage round 3 关闭)**: Aaron 拒绝 Lex 的 AC 补全建议 (认为该 NFR 没必要)。已标 wontfix, 后续 Probe/Archer 不会为该废弃 NFR 生成测试。锚点保留, FR 编号不再复用。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| false | ✅ | ✅ |
> **Lex:** NFR-010 缺可断言的 AC 描述。"1MB spec < 1s" 是性能目标, 但未指明如何测、断言什么。
> 修改建议: 增加验收点 "在 1MB 合成 spec (含 10000 个 quote 块) 上跑 `python3 tools/quote_parser.py`, 端到端 wall time 断言 `time.time() - t0 < 1.0`" [open]
>> Aaron: 这个需求没必要。
>>> **Sage:** 收到, Aaron 拒绝 Lex 的 AC 补全建议, 认为 NFR-010 没必要保留。NFR-010 视为废弃, yaml.valid 维持 `false`, 不进入 ready 判定。本单元加入「澄清记录」, 后续 Probe/Archer 不会为废弃 NFR 生成测试。 [wontfix]
<a id="nfr-020"></a>
### NFR-020 错误信息包含 quote 块行号
[source: project/specs/v0.4-004-quote-dialogue/spec.md#nfr-020--quote-]
当 quote 块缺 status marker、speaker 缺失、深度冲突时，`quote_parser.py` 抛错必须包含 `line:N` 位置信息，便于 IDE 跳转。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

## v0.5-005-namespace-cleanup

# init 后目录收归到 .specforge/ 命名空间 — Spec
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#init--specforge----spec]
- **Spec ID**: v0.5-005-namespace-cleanup
- **创建日期**: 2026-06-23
- **状态**: 草稿
- **关联**: v0.3-003-init-adopt-mode（FR-010 将被本 spec 取代 / 改写）
## 背景
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#]
`specforge init` 当前在项目根目录创建两类非源码目录：
- `wiki/{pages,decisions}/` + `wiki/{index,overview,log}.md` —— Agent 知识库（LLM-Wiki 三层架构）
- `raw/sources/` —— Agent 完整会话记录原始层
这两类目录在项目根目录存在三个问题：
1. **命名空间污染** —— `raw/` 是泛用名，未来用户或工具可能也会用 `raw/`，冲突排查困难
2. **与"开发项目"语义不符** —— LLM-Wiki 来自 Karpathy 的个人知识库场景，硬塞到 dev project 根目录显得别扭
3. **持续累积的 git 风险** —— `raw/sources/` 会话记录会无限增长，污染 history（即便 gitignore 也容易误 commit）
`wiki/` 同理；用户在 v0.3-003 接受根目录布局时是"勉强接受"，现在借本 spec 一次性收归。
## 目标
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#]
将 `init` 创建的全部 specforge 自有目录收归到 `.specforge/` 命名空间下，使**项目根目录只包含用户自己的代码与 specforge 框架资产之外的东西**。同时为已 init 的项目提供自动迁移，零手工操作。
## 用户故事
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#]
### US-010
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#us-010]
story: 作为 specforge 用户，我希望 `init` 创建的 wiki/raw 目录位于 `.specforge/` 下，而不是项目根，以便项目根目录保持干净、不会被 specforge 自身的目录名污染。
priority: P0
### US-020
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#us-020]
story: 作为已 init 过的 specforge 用户，我希望重跑 `init --adopt` 时能自动把旧的 `wiki/` 和 `raw/` 移到新位置，以便我不需要手动执行 `mv`。
priority: P0
### US-030
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#us-030]
story: 作为 specforge 用户，我希望在迁移出错时能跳过自动迁移（`--no-migrate`），以便我能手动控制时机。
priority: P1
### US-040
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#us-040]
story: 作为 specforge 用户，我希望 Librarian 等 agent 在新旧路径并存时优先使用新路径（`.specforge/wiki/...`），以便迁移期间混合状态仍能正常工作。
priority: P1
### US-050
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#us-050]
story: 作为 specforge 用户，我希望 `specforge upgrade` 后 `$PATH` 里的 `specforge` 二进制也被自动刷新，以便我跑完 upgrade 立即能用到最新版的子命令和 flag。
priority: P0
## 用户使用场景
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#]
### scenario-010 新项目 init
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#scenario-010--init]
1. 用户在空目录执行 `specforge init myproj`
2. `bin/specforge` 创建 `.specforge/{agents,templates,project,wiki/pages,wiki/decisions,raw/sources}`
3. 项目根目录**没有** `wiki/`、**没有** `raw/`
### scenario-020 既存项目 adopt + 自动迁移
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#scenario-020--adopt--]
1. 已有项目（旧版 specforge init 过）：根目录有 `wiki/` 和 `raw/`
2. 用户升级 specforge 后执行 `specforge init .`
3. `bin/specforge` 检测到旧路径 → `git mv` 移到 `.specforge/wiki/` 与 `.specforge/raw/`
4. 再做 create-if-missing，幂等完成
5. 用户 `git status` 看到的是 rename，不是 delete+add
### scenario-030 拒绝自动迁移
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#scenario-030-]
1. 用户带 `--no-migrate`：`specforge init . --no-migrate`
2. `bin/specforge` 不做迁移
3. 在 tri-state 报告里标出"未迁移: wiki/ → .specforge/wiki/, raw/ → .specforge/raw/" 提示用户手动操作
## 功能需求
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#]
### FR-010 init 路径收归
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#fr-010-init-]
`init <bare-name>` 创建的目录**仅限**：
```
.specforge/agents/
.specforge/templates/
.specforge/project/
.specforge/wiki/pages/
.specforge/wiki/decisions/
.specforge/raw/sources/
```
**禁止**在项目根创建 `wiki/`、`raw/`、`wiki/pages/`、`wiki/decisions/`、`raw/sources/` 任一路径。AC：init 完成后 `find . -maxdepth 2 -type d -name wiki -o -name raw` 仅匹配 `.specforge/wiki`、`.specforge/raw` 两项。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-020 adopt 模式 create-if-missing 路径同步
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#fr-020-adopt--create-if-missing-]
`cmd_init_adopt` 的"5 个目录"（来自 v0.3-003 FR-010）路径修订为：
| 旧路径 | 新路径 |
|---|---|
| `agents/` | （取消，改为 `.specforge/agents/`，见 FR-010） |
| `templates/` | （取消，改为 `.specforge/templates/`，见 FR-010） |
| `specs/` | `.specforge/project/specs/`（v0.3-003 已部分对齐，需补全） |
| `wiki/{pages,decisions}/` | `.specforge/wiki/{pages,decisions}/` |
| `raw/sources/` | `.specforge/raw/sources/` |
AC：adopt 后 `for d in .specforge/agents .specforge/templates .specforge/project .specforge/wiki/pages .specforge/wiki/decisions .specforge/raw/sources; do [ -d "$d" ]; done` 全部通过。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-030 旧路径自动迁移
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#fr-030-]
`cmd_init_adopt` 在做 create-if-missing 之前，先执行"路径迁移"步骤：
| 检测条件 | 操作 |
|---|---|
| `[ -d wiki ]` 且 `[ ! -e .specforge/wiki ]` | `git mv wiki .specforge/wiki`（若跟踪）或 `mv wiki .specforge/wiki`（若未跟踪） |
| `[ -d raw ]` 且 `[ ! -e .specforge/raw ]` | `git mv raw .specforge/raw`（若跟踪）或 `mv raw .specforge/raw`（若未跟踪） |
| 旧路径不存在 | skip |
| 旧路径与新路径**都**存在 | 报错并退出，提示用户手动处理（防止数据丢失） |
迁移步骤的输出格式：`[→] wiki/ → .specforge/wiki/`（使用新的 `[→]` 档位，区别于现有的 `[+]`/`[=]`/`[!]`）。
AC：
- 既存 `wiki/` 被 `git mv` 到 `.specforge/wiki/` 后，`git status` 显示 rename 而非 delete+add
- 旧路径不存在时不报错（idempotent）
- 旧新并存时 exit code ≠ 0 且 stderr 含 `wiki` 和 `.specforge/wiki`
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-040 --no-migrate flag
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#fr-040---no-migrate-flag]
`init --adopt` 接受 `--no-migrate` flag，跳过 FR-030 的迁移步骤。skip 后必须在 tri-state 报告**末尾**追加一段迁移提示：
```
[→] 未迁移: wiki/ → .specforge/wiki/
[→] 未迁移: raw/  → .specforge/raw/
提示: 重新运行 'specforge init .' (无 --no-migrate) 自动迁移, 或手动执行:
git mv wiki .specforge/wiki && git mv raw .specforge/raw
```
AC：带 `--no-migrate` 时，旧路径**保持原位**（不删不移），且报告含上述提示。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-050 干跑（--dry-run）下的迁移报告
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#fr-050---dry-run]
`init --adopt --dry-run` 在不实际改动 working tree 的前提下，仍打印**会做什么**：
- 列出将被 `git mv` 的旧路径 → 新路径对
- 不会 `mkdir`、不会 `mv`、不会 `cp`
- `--dry-run` + `--no-migrate` 兼容：仅打印"将跳过迁移"的提示
AC：`--dry-run` 前后 `find . -type f -not -path "./.git/*" | xargs sha256sum` 字节级不变；输出含迁移计划文本。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-060 Librarian / 全部 agent prompt 路径同步
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#fr-060-librarian----agent-prompt-]
`agents/*.md` 内所有 `wiki/pages/`、`wiki/decisions/`、`raw/sources/` 引用**必须**更新为：
- `wiki/pages/` → `.specforge/wiki/pages/`
- `wiki/decisions/` → `.specforge/wiki/decisions/`
- `raw/sources/` → `.specforge/raw/sources/`
- `wiki/index.md` → `.specforge/wiki/index.md`
- `wiki/overview.md` → `.specforge/wiki/overview.md`
- `wiki/log.md` → `.specforge/wiki/log.md`
- `wiki/.cache` → `.specforge/wiki/.cache`
**例外**：`Librarian.md` 的"三层架构"示意图允许保留简写（`raw/sources`、`wiki/pages`），但需在图下方加一行注释：*实际路径 = `.specforge/raw/sources/`、`.specforge/wiki/pages/`*。
**例外**：`wiki/entries/`（legacy，out of scope）相关引用不在本 spec 处理。
AC：`grep -RE 'wiki/(pages|decisions|index|overview|log)|raw/sources' agents/` 命中行全部包含 `.specforge/` 前缀（或属于上述两个例外）。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-070 README + 文档路径同步
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#fr-070-readme--]
`README.md`、`wiki/overview.md`、`wiki/log.md`、`wiki/pages/*.md` 中所有 wiki/raw 路径引用同步更新到 `.specforge/wiki/...`、`.specforge/raw/...`。`README.md` §11.x 架构决策表格中的 `[`wiki/decisions/`]` 链接同步更新。
AC：`grep -nE '\bwiki/(pages|decisions|index|overview|log)\b' README.md` 命中行全部包含 `.specforge/` 前缀。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-080 v0.3-003 FR-010 标 deprecated
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#fr-080-v03-003-fr-010--deprecated]
`.specforge/project/specs/v0.3-003-init-adopt-mode/spec.md` 第 26 行的 FR-010 改为"已由 v0.5-005 取代"，表格 `有效需求` 改 `❌`，并在文末加 supersedes 注释指向本 spec。**不删除**锚点 `fr-010`，避免引用混淆（与 v0.4-004 的废弃规则一致）。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-090 ADR 留痕
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#fr-090-adr-]
在 `.specforge/wiki/decisions/006-namespace-cleanup.md` 新增一条 ADR，包含：
- 背景：根目录污染问题
- 决策：迁移到 `.specforge/`
- 备选：方案 B（彻底砍掉 raw + LLM-Wiki）— 拒绝理由：保留 LLM-Wiki 差异化卖点
- 后果：~25 个文件路径同步，零功能损失
并在 `README.md` §11.x 决策表格中追加一行 `[006]`。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
## 非功能需求
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#]
### NFR-010 既存测试仍通过
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#nfr-010-]
`tests/test_init.bats` + `tests/test_init_adopt_flow.bats` + `tests/test_wiki.bats` 全部 case 通过；`test_init_adopt_flow.bats` 中 `FR10_T01` 的 `wiki/pages`、`wiki/decisions`、`raw/sources` 断言改写为 `.specforge/wiki/...`、`.specforge/raw/...`。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### NFR-020 specforge 自身先吃狗粮
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#nfr-020-specforge-]
本 spec 的实施 PR 必须在 specforge 自身项目里先跑通（即 specforge 自己 init 出的 `.specforge/wiki/` 与 `.specforge/raw/` 必须用起来，不再于根目录创建 `wiki/` 或 `raw/`）。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### NFR-030 upgrade 同步刷新 \$PATH 里的 `specforge` 二进制
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#nfr-030-upgrade--path--specforge-]
`cmd_upgrade` 在 `git fetch + git merge --ff-only` 之后，必须把更新后的 `$SPECFORGE_HOME/bin/specforge` 重新拷贝到 `$BIN_DIR/specforge`（即用户 `$PATH` 里的入口），否则用户跑 `specforge upgrade` 后，$PATH 上的可执行文件仍是旧版（pre-existing bug：`install.sh:30-31` 在 install 时 copy 一次，但 upgrade 路径不 copy）。
**AC**：
- `cmd_upgrade` 末尾追加 `cp $SPECFORGE_HOME/bin/specforge $BIN_DIR/specforge`（含 fallback 提示）
- `tests/test_specforge_cli.bats` 新增一个 case 验证：执行 `specforge upgrade` 后，`$BIN_DIR/specforge` 的 hash 与 `$SPECFORGE_HOME/bin/specforge` 的 hash 一致
- 若 `$BIN_DIR` 不存在或不可写，打印 hint（不报错退出，因为有的用户把 specforge clone 后直接 `bin/specforge` 调，不依赖 $BIN_DIR 拷贝）
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
## 澄清记录（Sage Interview 产出）
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#sage-interview-]
> 待用户 review 时填入。
## Lex 审核结果
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#lex-]
- [ ] 所有需求可追踪到用户故事
- [ ] 所有需求可断言（有明确的测试方法）
- [ ] 没有模糊词汇
- [ ] 所有 FR 都有显式锚点 `<a id="fr-XXX"></a>`
## 设计决策（待你确认）
[source: project/specs/v0.5-005-namespace-cleanup/spec.md#]
以下 4 点已在我方案里默认采用，如不同意请在 review 时指出：
| # | 决策 | 默认选择 | 备选 |
|---|------|---------|------|
| D1 | `wiki/` 是否一并迁移 | **是**（原 Plan A 范围） | 只迁 `raw/`，保留 `wiki/` |
| D2 | `raw/sources/` 与 `.specforge/wiki/` 的关系 | **平行** (`.specforge/raw/sources/`) | 嵌套 (`.specforge/wiki/sources/`) |
| D3 | 旧路径处理方式 | **自动 `git mv`**（`--no-migrate` 可 opt-out） | 纯 break-change，提示用户手动 |
| D4 | `wiki/entries/`、`wiki/consolidated.md`（legacy） | **out of scope** | 顺手清理 |

## v0.5-006-verify-issue-no-ac-mode

# verify-issue L7 支持 No-Acceptance + spec-fragment 模式 — Spec
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#verify-issue-l7--no-acceptance--spec-fragment---spec]
- **Spec ID**: v0.5-006-verify-issue-no-ac-mode
- **来源**: issue #75
- **创建日期**: 2026-06-23
- **状态**: 草稿
## 背景
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#]
`verify_issue_schema.py` L7 当前对 `### 验收标准` 字段强约束: 必须是 `acceptance.md#ac-fr-XXX` 完整 URL + 锚点可达。
但实际项目里有三类 FR 不需要单独的 `acceptance.md` 章节:
| FR 类型 | AC 来源 | 例子 |
|---|---|---|
| 撮合 ground truth | test-plan §3.2 | FR-050/060/070/080 |
| 算法定义 | spec 章节公式 | FR-185 (4 条公式) |
| 声明性 FR | spec 章节描述 | FR-080 (跨模式差异) |
强行加 acceptance.md 占位章节 (millionaire 现有 83 行冗余) 是噪音, 不是工程。
## 目标
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#]
L7 支持三种 acceptance 形式, 用 issue body 的 `### 验收标准` 字段值区分:
| 字段值 | 校验 | 用途 |
|---|---|---|
| `acceptance.md#ac-fr-XXX` URL | acceptance.md 锚点存在 + 上下文含 FR-XXX | 默认: 有专属 AC |
| `spec(-vol)?.md#fr-XXX` URL | spec 锚点存在 + 上下文含 FR-XXX | AC 在 spec 章节中 |
| 字面值 `无` | acceptance.md `## No Acceptance` 列表包含此 FR | 算法 / 声明性 / 撮合 ground truth |
向后兼容: 现有 acceptance.md URL 形式不变, 旧 issue 不受影响。
## 用户故事
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#]
### US-010
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#us-010]
story: 作为 specforge 用户, 我希望撮合 / 算法 / 声明性 FR 的 issue `验收标准` 字段可以填 `无`, 以便不为这些 FR 写虚假的 acceptance.md 章节, 减少文档噪音。
priority: P0
### US-020
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#us-020]
story: 作为 specforge 用户, 我希望 AC 写在 spec 章节里的 FR, issue `验收标准` 字段可以填 spec-fragment URL, 以便 L7 校验 spec 锚点存在 (L5) + 上下文含 FR-XXX (L6), 不需要 acceptance.md 重复。
priority: P0
### US-030
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#us-030]
story: 作为 specforge 用户, 我希望 acceptance.md 有一个 `## No Acceptance` 列表, 显式声明 "哪些 FR 没有专属 acceptance", 以便 L8 双向覆盖 + Lex 阶段一可追溯这些 FR 的 AC 来源。
priority: P0
### US-040
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#us-040]
story: 作为 specforge 维护者, 我希望 L7 三种形式互相排斥 (一个 issue 只能选一种), 以便误填 (如同时填 URL + 列表) 报错。
priority: P1
## 用户使用场景
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#]
### scenario-010 撮合 FR (用 `无`)
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#scenario-010--fr--]
acceptance.md:
```markdown
## No Acceptance
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#no-acceptance]
以下 FR 无专属 acceptance (AC 在 test-plan §3.2 中描述):
- FR-050
- FR-060
- FR-070
- FR-080
```
issue body:
```
### 验收标准
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#]
无
```
期望: L7 pass, 继续走 L8 双向覆盖。
### scenario-020 算法 FR (用 spec-fragment)
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#scenario-020--fr--spec-fragment]
issue body:
```
### 验收标准
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#]
https://github.com/.../spec-strategy.md#fr-185
```
期望: L7 通过 spec-fragment URL 校验: spec-strategy.md 中存在 `<a id="fr-185"></a>` 锚点 + 锚点上下文含 "FR-185"。
### scenario-030 误填 (FR 不在 No Acceptance 列表中)
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#scenario-030--fr--no-acceptance-]
issue body:
```
### 验收标准
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#]
无
```
但 acceptance.md `## No Acceptance` 不含此 FR。
期望: L7 fail, 提示 "请把该 FR 加入 No Acceptance 列表, 或改用 acceptance.md#ac-fr-XXX URL"。
## 功能需求
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#]
### FR-010 L7 三模式判断
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#fr-010-l7-]
`check_issue` L7 分支:
| `raw_ac` 值 | 处理 |
|---|---|
| 空 | 报错 `L7 字段 '验收标准' 缺失` |
| `== "无"` | 走 FR-020 |
| 匹配 `RE_SPEC_URL` | 走 FR-030 (用现有 RE_SPEC_URL, 不引入新正则) |
| 匹配 `RE_AC_URL` | 现有 L7 逻辑 (向后兼容) |
| 其它 | 报错 `L7 字段格式错误`, 提示三种合法形式 |
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-020 `无` 模式校验
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#fr-020--]
校验链:
1. 取 acceptance.md 全文
2. 解析 `## No Acceptance` 节 (下一 `##` 之前), 抽取 `- FR-XXX` / `- NFR-XXX` 项
3. `raw_fr` (需求 ID 字段值) 必须在集合中
4. 不在 → fail: `L7 字段 '无' 但 acceptance.md 的 '## No Acceptance' 列表中找不到 {raw_fr}`
边界:
- acceptance.md 不存在 → fail: `L7 字段 '无' 需要 acceptance.md 存在`
- acceptance.md 存在但无 `## No Acceptance` 节 → fail: `L7 acceptance.md 缺 '## No Acceptance' 列表`
- `## No Acceptance` 节为空 (无 `- FR-XXX` 项) → 同上 fail
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-030 spec-fragment 模式校验
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#fr-030-spec-fragment-]
校验链 (复用 L3-L6 已有的 spec 文本缓存):
1. 解析 `raw_ac` 为 spec URL, 用现有 `RE_SPEC_URL`
2. 取 spec 文本 (优先用 `spec_cache[OFFLINE]` 离线模式 / 已有缓存; 否则 fetch)
3. 验证 fragment 是 spec 中的 `fr-XXX` / `nfr-XXX` 锚点
4. 验证锚点上下文 (锚点行 + 后续 5 行) 含 `raw_fr`
5. 跳过 acceptance.md 校验
`raw_ac` 必须是 spec URL, 不能是 acceptance URL。spec-fragment 走 RE_SPEC_URL, acceptance 走 RE_AC_URL, 二者格式不同, 不会混淆。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-040 form 模板 regex 放松
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#fr-040-form--regex-]
`.github/ISSUE_TEMPLATE/feature.yml` 的 `acceptance_criteria` 字段 `regex` 由:
```
^https://github\.com/.../acceptance\.md#ac-(fr|nfr)-\d{3}$
```
改为:
```
^(无|https://github\.com/.../spec(-\w+)?\.md#(fr|nfr)-\d{3}|https://github\.com/.../acceptance\.md#ac-(fr|nfr)-\d{3})$
```
字段 `description` 追加:
```
- 默认填 acceptance.md#ac-fr-XXX URL (有专属 AC 章节)
- 或填 spec(-vol)?.md#fr-XXX URL (AC 在 spec 章节中描述)
- 或填字面值 "无" (FR 在 acceptance.md No Acceptance 列表中)
```
`placeholder` 保留原 URL 示例, 但 description 把三种形式讲清。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-050 Sage Step 5 决策逻辑
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#fr-050-sage-step-5-]
`agents/Sage.md` Step 5 章节追加决策树:
```
创建 issue 时, "验收标准" 字段值按 FR 性质三选一:
1. FR 有专属 acceptance.md 章节 (AC-1/AC-2/...):
→ acceptance.md#ac-fr-XXX URL
2. FR 的 AC 在 spec 章节中 (如算法定义 FR-XXX 含 F-CB-1/2/3/4 公式):
→ spec(-vol)?.md#fr-XXX URL
3. FR 是 ground truth 覆盖 / 声明性 / 撮合 等 "无 AC 章节" 类型:
→ 字面值 "无"
(同时在 acceptance.md 的 ## No Acceptance 列表追加该 FR)
```
并在创建 issue 前, 先 grep acceptance.md 的 No Acceptance 列表决定路径 3 是否成立。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-060 Lex 阶段一 接受三种形式
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#fr-060-lex--]
`agents/Lex.md` 阶段一追加说明:
```
"验收标准" 字段校验: verify_issue_schema.py L7 接受三种形式:
- acceptance.md#ac-fr-XXX URL (默认)
- spec(-vol)?.md#fr-XXX URL (AC 在 spec)
- 字面值 "无" (FR 在 acceptance.md No Acceptance 列表)
Lex 阶段一不强制偏好, 按 Sage 决策为准。
```
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
## 非功能需求
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#]
### NFR-010 向后兼容
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#nfr-010-]
现有所有用 `acceptance.md#ac-fr-XXX` URL 的 issue 不受影响, VERIFY-100/301/400/401/402 等测试 (acceptance.md 模式) 必须继续 pass。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### NFR-020 完整测试覆盖
[source: project/specs/v0.5-006-verify-issue-no-ac-mode/spec.md#nfr-020-]
`tests/test_issue_form.bats` 新增 5 个 case:
- VERIFY-500: `无` + FR 在 No Acceptance 列表 → pass
- VERIFY-501: `无` + FR 不在 No Acceptance 列表 → fail
- VERIFY-502: `无` + acceptance.md 缺 No Acceptance 列表 → fail
- VERIFY-503: spec-fragment URL + 锚点存在 → pass
- VERIFY-504: spec-fragment URL + 锚点不存在 → fail
- VERIFY-505: spec-fragment URL + 锚点上下文无 FR-XXX → fail
- FORM-010: feature.yml regex 接受三种形式
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

## v0.5-007-multi-ide-boards

# 多 IDE Board 支持 — Spec
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#-ide-board---spec]
- **Spec ID**: v0.5-007-multi-ide-boards
- **创建日期**: 2026-06-24
- **状态**: 草稿
- **关联**: 替代 v0.2-002-specforge FR-001..007 (那批从未实施且与本设计冲突)
## 背景
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#]
当前 specforge agent prompt 放在 `.specforge/agents/*.md`, 只有 VS Code 通过 `.github/agents/*.agent.md` 软链能识别. 用户在 opencode 里跑 `/agents` 看不到 specforge 的 19 个 agent, 因为 opencode 只扫:
- `~/.config/opencode/agents/` (全局)
- `.opencode/agents/` (项目级)
**实测验证** (2026-06-24, 在 specforge 自己仓里手工生成 18 个 `.opencode/agents/*.md`):
- ✓ opencode `/agents` 列表正确显示
- ✓ 切到 `sage` agent 后, 左下角 model = `ark/kimi-k2.6` (即 model 隔离生效)
- ✓ 卸载 omo 后仍工作 (无 plugin 依赖)
## 目标
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#]
把"为每个 IDE 生成它能识别的 agent 文件"这件事抽成 `specforge board <ide>` 子命令, 支持:
- `vscode` (现有 .github/agents/ 软链, 从 cmd_init_new 抽出)
- `opencode` (新增 .opencode/agents/ 生成)
- 未来 `cursor`, `claude` 等
每个 source agent prompt 加 `models` 数组 frontmatter 字段, primary 在 [0], 后面是 fallback 候选. board opencode 把 `models[0]` 翻译成 opencode 原生 `model: ` 字段.
## 用户故事
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#]
### US-010
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#us-010]
story: 作为 specforge 用户, 我希望在 opencode 中 `/agents` 命令能看到 specforge 的全部 agent, 以便用 opencode 跑 specforge 工作流.
priority: P0
### US-020
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#us-020]
story: 作为 specforge 用户, 我希望每个 agent 在 opencode 里**用各自的 model** (S 档 kimi / A 档 deepseek-v4-pro / B 档 glm / C 档 deepseek-flash), 而不是全部用 opencode 全局默认, 以便发挥成本/能力梯度优势.
priority: P0
### US-030
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#us-030]
story: 作为 specforge 用户, 我希望 `specforge init .` 能根据本机环境**自动**生成所需 IDE 的 agent 文件 (检测到 .vscode/ 走 vscode 板, 检测到 ~/.config/opencode/ 走 opencode 板), 不需要手动跑.
priority: P0
### US-040
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#us-040]
story: 作为 specforge 用户, 我希望显式跑 `specforge board <ide>` 也能生成, 以便后期切 IDE 时不需要重 init.
priority: P1
### US-050
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#us-050]
story: 作为 specforge 用户, 我希望 `specforge board status` 能告诉我当前项目装了哪些板, 以便排查 agent 不见的问题.
priority: P2
### US-060
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#us-060]
story: 作为 specforge 维护者, 我希望 `models` 数组里的 fallback 候选**只是占位**, 不立即实现 fallback 切换 (opencode 原生不支持; omo 的 `fallback_models` 是 plugin 扩展), 先把数据结构落地.
priority: P1
## 用户使用场景
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#]
### scenario-010 新项目 init 自动装两块板
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#scenario-010--init-]
```
$ ls .vscode/                          # 用户有 vscode 配置
settings.json
$ ls ~/.config/opencode/opencode.json  # 也装了 opencode
ok
$ specforge init my-proj
→ 检测到 .vscode/ → 装 vscode 板 → .github/agents/*.agent.md (18 个软链)
→ 检测到 ~/.config/opencode/ → 装 opencode 板 → .opencode/agents/*.md (18 个生成)
```
### scenario-020 已存在项目, 后期手动加 opencode 板
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#scenario-020---opencode-]
```
$ cd my-existing-proj
$ ls .opencode/                        # 不存在
$ specforge board opencode             # 显式生成
→ 生成 .opencode/agents/{sage,lex,...}.md
$ specforge board status
vscode    ✓ (18 agents in .github/agents/)
opencode  ✓ (18 agents in .opencode/agents/)
```
### scenario-030 源 agent prompt 修改后, 刷新各 IDE 板
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#scenario-030--agent-prompt---ide-]
```
$ vim .specforge/agents/Sage.md        # 改了 description 或 body
$ specforge board opencode             # 重生成, 幂等
[=] .opencode/agents/sage.md (refreshed)
```
## 功能需求
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#]
### FR-010 source agent prompt 加 `models` 与 `mode` frontmatter
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#fr-010-source-agent-prompt--models--mode-frontmatter]
每个 `.specforge/agents/*.md` (specforge 自身仓为 `agents/*.md`) frontmatter 必须包含:
```yaml
---
name: sage
description: 需求澄清与 spec 撰写 — 把 story 翻译为可追踪的 spec
mode: all                    # primary / subagent / all (默认 all, 等同 opencode 原生)
models:                      # specforge 自定义: primary [0] + fallback
- kimi-k2.6                # primary (抽象名, 不带 provider 前缀)
- deepseek-v4-pro          # fallback 1
- glm-5.2                  # fallback 2
---
```
> Aaron： models 仅使用 kimi-k2.6这样的名字，它是一个抽象的模型名，并不是具体的模型 ID，也不要加 provider 前缀。如何绑定到具体的模型，我不知道，请建议。
>> **Sage:** 同意, source 改用抽象名 (cross-user / cross-provider). 绑定方案: 加两层架构 + 新 `specforge models` 子命令 (见 FR-080/090):
>>
>> 1. **抽象层** (source agent): `models: [kimi-k2.6, deepseek-v4-pro, glm-5.2]`
>> 2. **绑定层**: 用户本机 `~/.specforge/models.json` 或项目级 `.specforge/models.json` 存 alias map, 如:
>>    ```json
>>    {
>>      "kimi-k2.6":         "ark/kimi-k2.6",
>>      "deepseek-v4-pro":   "ark/deepseek-v4-pro",
>>      "glm-5.2":           "ark/glm-5.2",
>>      "deepseek-v4-flash": "ark/deepseek-v4-flash"
>>    }
>>    ```
>>    (国外用户可能映射成 `anthropic/claude-opus-4-5` / `openai/gpt-5` 等)
>> 3. **板生成时**: `specforge board opencode` 查 alias map, 把抽象名翻译成 opencode 全名写到 `.opencode/agents/sage.md` 的 `model:` 字段; 找不到对应键则报错并提示 `specforge models bind <抽象名> <opencode 全名>`
>> 4. **首次 init 时**: 若 `~/.specforge/models.json` 不存在, 走 interview (复活 v0.2-002 已废弃的 FR-001~005 思路, 见 FR-090)
>>
>> 这样 source 跨 user / 跨 provider 一致, 不需要改 18 个文件; 用户本机 alias 一次性配好即可.
>>> Aaron: alias map 如何配置？用户手工改？用户如何知道 opencode 中配置了哪些模型（provider/model），如果有 API 可获得 List，能否智能化关联？
>>>> **Sage:** 调查后确认: `opencode models` 命令存在且**机器可读**（一行一个 `provider/model-id`, stdout 直接 grep 即可）. 所以**用户完全不需要手填**, specforge 可以智能匹配:
>>>>
>>>> **匹配算法** (`specforge models doctor` / `init` interview / `models bind` 都用):
>>>> 1. 对 source 用到的每个抽象名 (如 `kimi-k2.6`), 取归一化 key: 小写去标点 → `kimik26`
>>>> 2. 调 `opencode models 2>/dev/null`, 对每行 (如 `ark/kimi-k2.6`) 取末段小写去标点 → `kimik26`
>>>> 3. 完全相等 → **strong match** (直接用)
>>>> 4. 包含关系 (抽象名是 model 末段子串) → **weak match** (提示用户确认)
>>>> 5. 无匹配 → **fail**, 让用户从全表里选, 或 `models bind` 显式指定
>>>>
>>>> **实测** (你本机, 配了 ark provider 5 个 model + opencode 内置 ~45 个):
>>>>   - `kimi-k2.6` → strong match `ark/kimi-k2.6` ✓ (也 strong match `opencode/kimi-k2.6`, 多重时选 user provider 优先 `ark` 而非 `opencode` 内置, 见匹配规则)
>>>>   - `deepseek-v4-pro` → strong match `ark/deepseek-v4-pro` ✓
>>>>   - `glm-5.2` → strong match `ark/glm-5.2` ✓
>>>>   - `deepseek-v4-flash` → strong match `ark/deepseek-v4-flash` ✓
>>>>
>>>> 即**你的环境零配置开箱即用** — init 不用 interview, 直接调 `opencode models` 跑一遍智能匹配, 写到 `~/.specforge/models.json`. 用户感知到的就是 "specforge init 完了, 它就工作". ✓
>>>>
>>>> 多重 strong match (user provider + opencode 内置) 时优先级:
>>>> 1. 用户项目级 `models.json` 显式绑定
>>>> 2. 用户级 `~/.specforge/models.json` 显式绑定
>>>> 3. **opencode 中非 `opencode/` 前缀的 provider** (用户自己配的 ark / openai / anthropic 等, 一般是 pay-per-token 直连)
>>>> 4. `opencode/` 前缀 (opencode 官方 subscription)
>>>>
>>>> 这样用户配的国内 ark 优先于 opencode 内置, 避免 subscription token 消耗.
**约束**:
- `models` 至少 1 个元素 (primary 必填)
- `models[0]` = primary; fallback 仅作占位 (opencode 原生不消费; 将来 omo plugin 模式可消费)
- `name` 仍保留 (specforge 自己工具用, 文件名也独立维护)
- `mode` 默认 `all` (specforge 现阶段不强制 primary/subagent 分层, US-040 之前讨论的 Maestro 自动编排是 v0.6 后续话题)
档位 → primary model 默认值 (抽象名, 与具体 provider 解耦):
| 档  | Agents                                                                              | primary             | fallback                             |
| --- | ----------------------------------------------------------------------------------- | ------------------- | ------------------------------------ |
| S   | Maestro, Sage, Lex                                                                  | `kimi-k2.6`         | `deepseek-v4-pro`, `glm-5.2`         |
| A   | Probe, Judge, Archer, Cynic, Herald, Arbiter, Warden, Hunter, Shield, Prism, Keeper | `deepseek-v4-pro`   | `kimi-k2.6`, `glm-5.2`               |
| B   | Scout, Forge                                                                        | `glm-5.2`           | `deepseek-v4-pro`                    |
| C   | Librarian, Guide                                                                    | `deepseek-v4-flash` | `glm-5.2`                            |
> **注**: 上表是 specforge 出厂默认值. 用户在本机或项目级 `models.json` 里把抽象名映射到自己的 provider (国内默认 ark, 国外可换 anthropic/openai/google). 见 FR-080/090.
> Aaron: 同上，模型只给抽象名字。比如 kimi-2.6, glm-5.2
>> **Sage:** 已确认, 上表已改成抽象名 (无 `ark/` 前缀). 具体 provider 绑定由 `~/.specforge/models.json` (用户本机 alias map) 完成, 不在 source 里硬编码. ✓
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### FR-020 新增 `specforge board <ide>` 子命令
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#fr-020--specforge-board-ide-]
```
specforge board <ide>           # 生成指定 IDE 的 agent 板
specforge board status          # 列出当前项目装了哪些板
specforge board <ide> --dry-run # 预览
```
`<ide>` 当前支持: `vscode`, `opencode`. 未来扩展: `cursor`, `claude`.
退出码:
- 0 = 成功 (或 dry-run)
- 1 = 未知 ide
- 2 = 当前目录不是 specforge 项目 (无 `.specforge/agents/` 也无 `agents/`)
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### FR-030 `board opencode` 生成 `.opencode/agents/*.md`
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#fr-030-board-opencode--opencode-agents-md]
行为:
1. 定位 source 目录:
- 优先 `.specforge/agents/` (installed project)
- fallback `agents/` (specforge 自身仓, dev mode)
2. 对每个 `*.md` 文件 (跳过 `README.md`, `ROSTER.md`):
- 解析 frontmatter, 取 `description` / `mode` / `models`
- 生成 `.opencode/agents/{lowercase-name}.md`, frontmatter:
```yaml
---
description: <copied>
mode: <copied or 'all'>
model: <models[0]>
---
<body copied>
```
- opencode 原生 frontmatter **不带 `models` 字段** (opencode 不识别会引发警告)
3. `.gitignore` 追加 `.opencode/agents/` (本地生成物, 不入库; 与 `.github/agents/` 规则一致)
4. **幂等**: 重跑无副作用, 同名文件覆盖 (因为是从 source 重生成)
5. **不破坏用户手工添加的 opencode agent**: 只处理 source 里有名字对应的文件; 用户在 `.opencode/agents/` 里手工放的不在 source 名单的 *.md 不动
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### FR-040 `board vscode` 抽取现有逻辑
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#fr-040-board-vscode-]
把 `cmd_init_new` 与 `cmd_init_adopt` 里的 `.github/agents/*.agent.md` 软链逻辑抽到 `cmd_board vscode`. init 现在变成: 创建目录 → 拷贝 source → 调 `cmd_board <detected-ide>` (FR-060).
软链相对路径保持: `.github/agents/sage.agent.md → ../../.specforge/agents/Sage.md`. (跟现状一致)
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### FR-050 `board status` 输出
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#fr-050-board-status-]
```
$ specforge board status
vscode    ✓  (.github/agents/ — 18 agent symlinks)
opencode  ✓  (.opencode/agents/ — 18 agent files)
cursor    -  (not installed)
```
每行: `<ide>` + `✓` / `-` + 简述. `✓` 必须同时满足:
1. 板目录存在
2. 至少有 1 个 agent 文件
3. (vscode) 文件是软链, 目标存在
4. (opencode) 文件 frontmatter 含 `model:` 字段
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### FR-060 init 自动探测 IDE 并装板
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#fr-060-init--ide-]
`cmd_init_new` 与 `cmd_init_adopt` 在拷贝 source 完毕后, 自动探测并装板:
| 探测条件                                                | 装的板     |
| ------------------------------------------------------- | ---------- |
| `.vscode/` 在项目里存在                                 | `vscode`   |
| `~/.config/opencode/opencode.json` 或 `.opencode/` 存在 | `opencode` |
| 都没有                                                  | 不装       |
新增 init flag `--board=<csv>` 覆盖自动探测:
- `--board=opencode,vscode` 强制装两个
- `--board=none` 都不装
- `--board=opencode` 只装 opencode (即便项目有 .vscode/)
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### FR-070 18 个 source agent 加上 `models` 与 `mode`
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#fr-070-18--source-agent--models--mode]
按 FR-010 档位表, 把现有 18 个 `agents/*.md` 的 frontmatter 加上 `models` 与 `mode`. ROSTER 与 README 不动 (描述性文件, 无需 model 信息).
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### FR-080 抽象名 → provider 全名的自动发现 + alias override
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#fr-080---provider---alias-override]
绑定分 3 层, **前两层显式 override, 第三层自动发现**:
| 优先级 | 来源 | 用途 |
|---|---|---|
| 1 (高) | `<project>/.specforge/models.json` | 项目级显式覆盖 |
| 2 | `~/.specforge/models.json` | 用户本机显式默认 |
| 3 (低) | `opencode models` | 自动发现, 零配置 |
显式 alias 文件格式 (可选, 没有也能工作):
```json
{
"$schema": "specforge://models-alias",
"version": 1,
"aliases": {
"kimi-k2.6": "ark/kimi-k2.6"
}
}
```
`specforge board opencode` 的 model resolve 流程:
1. 解析 source `models[0]` (抽象名, 如 `kimi-k2.6`)
2. 查项目级 `.specforge/models.json` (有则直接用)
3. 查用户级 `~/.specforge/models.json` (有则直接用)
4. 若仍未命中, 调 `opencode models 2>/dev/null`, 得到一行一个 `provider/model-id`
5. 对抽象名和每个 model-id 末段做 normalize (小写, 去掉 `._-/` 等标点), 完全相等为 strong match
6. strong match 只有 1 个 → 直接用
7. strong match 多个 → 按 provider 优先级选:
1. 非 `opencode/` 前缀的用户自配 provider (如 `ark/`, `anthropic/`, `openai/`)
2. `opencode/` 前缀 (官方 subscription)
3. 若仍并列, 取字典序最小, 并 warning
8. 无 strong match 但有 weak match (包含关系) → 交互确认; 非 tty 下 fail
9. 无匹配 → fail, 提示 `opencode models` 可用列表 + `specforge models bind <abstract> <full>` 手动绑定
新增 `specforge models` 子命令:
```
specforge models list                              # 列出 source 用到的抽象名 + resolve 结果
specforge models doctor                            # 检查未绑定/冲突/弱匹配, 给出建议
specforge models bind <abstract-name> <full-name>  # 写入 ~/.specforge/models.json (override)
specforge models bind <abstract-name> <full-name> --project  # 写项目级 override
specforge models unbind <abstract-name>            # 删除用户级绑定
```
约束:
- `models.json` 不再是必需文件, 只是 override
- 自动发现依赖 opencode CLI; 若 opencode 不在 PATH, board opencode fail 并提示安装/配置 opencode
- board vscode 不需要 model resolve
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### FR-090 init 首次运行的 model resolve
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#fr-090-init--model-resolve]
`specforge init` 不再问 region/interview. 规则:
1. 如果本次会生成 opencode board (auto-detect 或 `--board=opencode`), 在 board 前自动运行 `specforge models doctor --ide=opencode --fix-auto`
2. `--fix-auto` 对 strong match 自动写入 `~/.specforge/models.json` (作为缓存, 下次不再调用 `opencode models`)
3. 只有遇到 weak match 或 no match 才进入交互:
```
source model alias: kimi-k2.6
Found candidates from `opencode models`:
[1] ark/kimi-k2.6          (strong, user provider)
[2] opencode/kimi-k2.6     (strong, opencode subscription)
Choose [1]:
```
非 tty 时:
- strong match 多个 → 按 FR-080 provider 优先级自动选
- weak/no match → fail, 提示 `specforge models bind`
因此用户正常路径是零配置:
```
specforge init my-proj
→ 检测到 opencode
→ opencode models
→ 自动匹配 kimi-k2.6/deepseek-v4-pro/glm-5.2/deepseek-v4-flash
→ 写 ~/.specforge/models.json 缓存
→ board opencode 生成 .opencode/agents/*.md
```
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
## 非功能需求
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#]
### NFR-010 向后兼容
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#nfr-010-]
现有 `.github/agents/*.agent.md` 软链规则不变, vscode 用户升级到 0.5.2 不需要重做任何事 (再跑 init 也只是幂等覆盖).
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### NFR-020 provider 解耦
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#nfr-020-provider-]
source `models` 数组里**只放抽象名** (如 `kimi-k2.6`, `glm-5.2`), **不带 provider 前缀**. 抽象名 → 全名的映射由用户本机/项目级 `models.json` (FR-080) 完成, specforge 不限定 provider.
ADR 008 记录: 抽象名 → 默认 alias map 的内容, 与"为什么 source 不绑 provider"的理由.
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### NFR-030 测试覆盖
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#nfr-030-]
`tests/test_board.bats` (新增) 包含:
- BOARD_T01: `specforge board opencode` 在新项目生成 18 个文件
- BOARD_T02: 生成的文件 frontmatter 含 `model:` 且 = alias-resolve(source `models[0]`)
- BOARD_T03: 生成的文件 body 与 source body 一致 (sha256)
- BOARD_T04: 幂等 - 重跑无变化
- BOARD_T05: `board vscode` 生成软链, 目标可达
- BOARD_T06: `board status` 显示已装板与未装板
- BOARD_T07: `board <unknown-ide>` 退出码 1
- BOARD_T08: init 自动探测 .vscode/ 装 vscode 板 (现有测试改写为通过 board 流程实现)
- BOARD_T09: init 自动探测 ~/.config/opencode/ 装 opencode 板
- BOARD_T10: init --board=none 跳过自动探测
- BOARD_T11: init --board=opencode 显式只装 opencode
`tests/test_models.bats` (新增) 包含:
- MODELS_T01: `specforge models list` 列出 source 用到的全部抽象名
- MODELS_T02: `specforge models doctor` 调 `opencode models` 自动 strong-match
- MODELS_T03: 多个 strong match 时, 非 `opencode/` provider 优先于 `opencode/` provider
- MODELS_T04: `specforge models bind X Y` 写入 `~/.specforge/models.json` override
- MODELS_T05: `specforge models bind X Y --project` 写入项目级 override 且优先级高于用户级
- MODELS_T06: `specforge models unbind X` 删除用户级绑定
- MODELS_T07: `board opencode` 使用 resolve 后的 full model 写 `model:`
- MODELS_T08: `board opencode` 在 no-match 且非 tty 时 fail 并提示 `models bind`
- MODELS_T09: `models doctor --fix-auto` 把 strong match 写入 `~/.specforge/models.json` 缓存
- MODELS_T10: `opencode models` 不存在时 `board opencode` fail, board vscode 不受影响
`tests/test_init.bats` 与 `tests/test_init_adopt_flow.bats` 现有断言保持通过 (NFR-010).
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### NFR-040 ADR 留痕
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#nfr-040-adr-]
新增 `.specforge/wiki/decisions/008-multi-ide-boards.md`, 含:
- 背景 (specforge agent 在 opencode 不可见 + cross-provider 抽象需求)
- 决策 (board 子命令 + 抽象 models 数组 + models.json alias map 两层架构)
- 抽象名 → 默认 alias 表 (国内 region preset)
- 备选 A: 在 source 直接写 `ark/kimi-k2.6` (拒绝, 不跨 provider)
- 备选 B: omo plugin 模式 (拒绝, 强依赖 omo)
- 备选 C: 把 alias 写在 source frontmatter (拒绝, 每改 provider 要改 18 个文件)
- 后果 (18 个 source agent 改 frontmatter; 新增 `models` 子命令; init 首次 interview)
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### NFR-050 关闭关联的旧 issue
[source: project/specs/v0.5-007-multi-ide-boards/spec.md#nfr-050--issue]
实施后关闭以下 v0.2 残留 issue (`spec 002-specforge-v0.2` 从未实施, 本 spec 是其更优的取代):
- #18 [FR-001] 交互式收集逗号分隔的可用模型列表 → 由 FR-090 init interview 取代
- #19 [FR-002] 交互式选择国内版/全局版模型策略 → FR-090 region 选项取代
- #20 [FR-003] 打印推荐表并让用户手动指定每个 Agent 模型 → FR-010 档位表 + FR-080 alias map 取代
- #21 [FR-004] 生成 OpenCode 兼容的 agent 配置 → FR-020/030 `board opencode` 取代
- #22 [FR-005] 模型配置持久化到 .specforge/models.json → FR-080 `models.json` 取代
- #23 [FR-006] 可用模型不足时自动降档到低档模型 → 留作 backlog, fallback 由 plugin 实现 (本 spec 仅落地 `models[]` 数据结构)
- #24 [FR-007] init 输出 onboarding 指引 → 已由 cmd_init_new 现有 `下一步` 输出实现 (cc49718 之后)
每条以 commit ref 关闭并加 comment 说明对应到本 spec 的哪个 FR.
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

## v0.5-008-test-quality-standards

# 测试质量标准化: CI 静态扫描工具 + tests/ 布局建议 — Spec
[source: project/specs/v0.5-008-test-quality-standards/spec.md#-ci---tests----spec]
- **Spec ID**: v0.5-008-test-quality-standards
- **来源**: issue #71, #72
- **创建日期**: 2026-06-25
- **状态**: 草稿
## 背景
[source: project/specs/v0.5-008-test-quality-standards/spec.md#]
Millionaire 项目临时维护了 `.specforge/tools/check_acs.py` 与 `check_assertions.py`, 用于:
- AC 双向追溯: 测试 docstring/comment 必须引用 `AC-FRXXX-YY`; acceptance.md 中每条 AC 必须被至少一个测试引用
- Assertion hygiene: 禁止 `assert True`, `try: except: pass`, 无 issue 链接的 `pytest.skip/xfail` 等作伪模式
这些规则不是 Millionaire 特有, 是 specforge 方法论的通用质量门禁。
同时, specforge 当前没有推荐的 `tests/` 目录布局。Millionaire 的布局有价值, 但其中 `conftest.py`, `fixture`, `ground_truth` 等是 Python/量化项目强相关, 不应强制推广到所有项目。
## 目标
[source: project/specs/v0.5-008-test-quality-standards/spec.md#]
1. specforge 原生提供 `check_acs.py` 与 `check_assertions.py`, 作为安装/初始化后可用的通用 CI 工具。
2. 重写 `templates/test-plan.md` 为**测试策略文档**, 不再列 UT 清单/覆盖矩阵。
3. 给出推荐 `tests/` 结构: `unit/`, `e2e/`, `assets/`, 可选 `ground_truth/`; 仅建议, 不强制。
4. 建立 `AC traceability` 与 `coverage >= 95%` 的方法论边界: test-plan 讲策略, 工具从代码反查覆盖。
## 非目标
[source: project/specs/v0.5-008-test-quality-standards/spec.md#]
- 不为项目自动生成具体 UT/E2E 测试清单。
- 不从 spec.md 自动生成覆盖矩阵。
- 不强制 Python/pytest 布局。
- 不强制 `ground_truth/` 存在。
- 不在本 spec 实现 coverage.py / lcov / nyc 等语言特定覆盖率采集；本 spec 只定义 traceability/hygiene 静态扫描。
## 用户故事
[source: project/specs/v0.5-008-test-quality-standards/spec.md#]
### US-010
[source: project/specs/v0.5-008-test-quality-standards/spec.md#us-010]
story: 作为 specforge 用户, 我希望每个测试都能反向追溯到 acceptance.md 中的 AC, 以便 CI 能阻止"测试存在但不覆盖需求"的虚假质量。
priority: P0
### US-020
[source: project/specs/v0.5-008-test-quality-standards/spec.md#us-020]
story: 作为 specforge 用户, 我希望 CI 能发现作伪测试 (`assert True`, 空 catch, 无理由 skip), 以便防止测试看似通过但没有断言价值。
priority: P0
### US-030
[source: project/specs/v0.5-008-test-quality-standards/spec.md#us-030]
story: 作为 specforge 用户, 我希望 test-plan.md 只描述测试策略/约定, 不列具体测试用例表, 以便真实覆盖矩阵从测试代码反向生成, 避免文档与代码漂移。
priority: P0
### US-040
[source: project/specs/v0.5-008-test-quality-standards/spec.md#us-040]
story: 作为 specforge 用户, 我希望有一个跨语言可用的推荐 tests/ 布局, 以便新项目有默认结构, 但历史项目不被强制迁移。
priority: P1
## 功能需求
[source: project/specs/v0.5-008-test-quality-standards/spec.md#]
### FR-010 内置 `tools/check_acs.py`
[source: project/specs/v0.5-008-test-quality-standards/spec.md#fr-010--tools-check_acspy]
新增 `tools/check_acs.py`, stdlib-only, 支持:
```
python3 tools/check_acs.py --acceptance .specforge/project/specs/<id>/acceptance.md --tests tests/
```
功能:
1. 解析 acceptance.md 中的 AC 列表, 支持两种格式:
- `### AC-1` / `### AC-2` (当前模板常见)
- `AC-1:` / `AC-2:` (兼容旧写法)
2. 生成 canonical AC id: `AC-FR010-01`, `AC-NFR020-02`。
3. 扫描测试文件中的 AC 引用:
- Python docstring/comment: `AC-FR010-01`
- JS/TS/Go/Rust/Bash 等 comment 中同样匹配纯文本 `AC-FR010-01`
4. 检查:
- acceptance.md 中每个 AC 至少被一个测试引用
- 测试中引用的 AC 必须存在于 acceptance.md
5. 输出 human-readable report + `--json` 机器可读 report。
6. 支持 `--legacy-baseline <file>`: baseline 中列出的 missing AC 只 warning, 不 fail。
退出码:
- 0 = 全部通过
- 1 = traceability 失败
- 2 = 参数/文件错误
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### FR-020 内置 `tools/check_assertions.py`
[source: project/specs/v0.5-008-test-quality-standards/spec.md#fr-020--tools-check_assertionspy]
新增 `tools/check_assertions.py`, stdlib-only, 支持:
```
python3 tools/check_assertions.py --tests tests/
```
检查作伪模式 (初版跨语言 + Python 强化):
| ID | 模式 | 说明 |
| -------- | ------ | ---------- |
| FAKE-001 | `assert True` / `assert 1` | 无效断言 |
| FAKE-002 | `assert x is not None` 且无 AC 引用 | 弱断言, 只在无 AC 时 fail |
| FAKE-003 | `try: ... except: pass` | 吞异常 |
| FAKE-004 | `except Exception: pass` | 吞异常 |
| FAKE-005 | `pytest.skip(...)` 无 issue/URL/AC 引用 | 无追踪 skip |
| FAKE-006 | `pytest.mark.skip` / `xfail` 无 issue/URL/AC 引用 | 无追踪 skip/xfail |
| FAKE-007 | 测试函数体只有 `pass` / `return` | 空测试 |
| FAKE-008 | `TODO` / `NotImplemented` 出现在测试主体且无 issue/URL | 未完成测试 |
输出:
- 默认 human-readable
- `--json` 输出 machine-readable
- `--legacy-baseline <file>` 支持历史债务 baseline, baseline 命中只 warning
退出码:
- 0 = 全部通过
- 1 = assertion hygiene 失败
- 2 = 参数/文件错误
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### FR-030 新增 `specforge ci-scan`
[source: project/specs/v0.5-008-test-quality-standards/spec.md#fr-030--specforge-ci-scan]
`bin/specforge` 新增命令:
```
specforge ci-scan --acceptance <path> --tests <dir> [--json]
specforge ci-scan --spec <spec-id> --tests tests/ [--json]
```
行为:
1. 先运行 `check_acs.py`
2. 再运行 `check_assertions.py`
3. 任一失败则整体 exit 1
4. `--json` 时合并两个工具的 JSON report
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### FR-040 重写 `templates/test-plan.md` 为策略文档
[source: project/specs/v0.5-008-test-quality-standards/spec.md#fr-040--templates-test-planmd-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
删除当前模板中的:
- 单元测试表
- 集成测试表
- E2E 测试表
- 覆盖矩阵
改为以下结构:
- `# {Feature 标题} — Test Plan`
- `## 测试策略`
- `## 测试层级`
- `## AC 追溯约定`
- `## 覆盖率目标`
- `## 反模式与 CI 门禁`
- `## 测试数据`
- `## 推荐 tests/ 布局`
- `## Judge 评审清单`
必须明确:
- 测试用例住在代码中, 不住在 test-plan 表格中
- 每个测试通过 docstring/comment 引用 `AC-FRXXX-YY`
- 覆盖矩阵由 `check_acs.py` 反向生成
- 覆盖率目标: `<95%` 不接受 (但语言具体覆盖率工具由项目选择)
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### FR-050 推荐 tests/ 布局 (建议不强制)
[source: project/specs/v0.5-008-test-quality-standards/spec.md#fr-050--tests---]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
在 `templates/test-plan.md` 与 ADR 中推荐:
```
tests/
├── unit/          # 单元测试, 建议镜像源码树 (不强制)
├── e2e/           # 端到端场景测试
├── assets/        # 离线、可复现测试数据
└── ground_truth/  # 可选: 纯实现/参考实现, 禁止 import 被测系统
```
约束:
- `unit/` 与 `e2e/` 推荐存在, 但不由工具强制
- `assets/` 推荐用于测试数据, 命名可项目自定
- `ground_truth/` 明确标注为可选, 仅适合算法/金融/规则引擎等需要参考实现的项目
- 不出现 Python 专属词作为通用要求 (`fixture`, `conftest.py` 只能作为 Python 示例)
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### FR-060 更新 Probe / Judge prompt
[source: project/specs/v0.5-008-test-quality-standards/spec.md#fr-060--probe---judge-prompt]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
- Probe: 生成 test-plan 时只写策略, 不列测试清单/覆盖矩阵。
- Judge: 审查 test-plan 的策略完整性, 不要求 test-plan 含所有 UT 明细。
- Herald: 验收时优先运行 `specforge ci-scan` 读取真实测试代码覆盖。
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
## 非功能需求
[source: project/specs/v0.5-008-test-quality-standards/spec.md#]
### NFR-010 stdlib-only
[source: project/specs/v0.5-008-test-quality-standards/spec.md#nfr-010-stdlib-only]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
`check_acs.py` / `check_assertions.py` 只能使用 Python stdlib, 不引入 pytest/coverage/yaml 依赖。
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### NFR-020 测试覆盖
[source: project/specs/v0.5-008-test-quality-standards/spec.md#nfr-020-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
新增:
- `tests/test_ci_tools.bats`
- `tests/fixtures/ci-tools/acceptance.md`
- `tests/fixtures/ci-tools/tests_good/`
- `tests/fixtures/ci-tools/tests_bad/`
覆盖:
- AC 全覆盖 pass
- missing AC fail
- unknown AC fail
- legacy baseline downgrade 为 warning
- assert True fail
- try/except/pass fail
- skip without issue fail
- JSON 输出合法
- `specforge ci-scan` 聚合两个工具结果
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### NFR-030 ADR 留痕
[source: project/specs/v0.5-008-test-quality-standards/spec.md#nfr-030-adr-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
新增 `.specforge/wiki/decisions/009-test-quality-standards.md`, 记录:
- test-plan 是策略文档, 不是测试清单
- 覆盖矩阵从测试代码反向生成
- 推荐 tests/ 布局但不强制
- ground_truth 可选
- `fixture` 非通用术语, 只作 Python 示例
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
### NFR-040 关闭 issue
[source: project/specs/v0.5-008-test-quality-standards/spec.md#nfr-040--issue]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
实施后关闭:
- #71 — 内置 CI 静态扫描工具
- #72 — 推荐 tests/ 目录布局
每个 issue comment 引用实现 commit 和对应 FR。
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

## v0.5-009-test-cleanup

# v0.5 收尾：测试债 + agents 路径漏改修复 — Spec
[source: project/specs/v0.5-009-test-cleanup/spec.md#v05---agents---spec]
- **Spec ID**: v0.5-009-test-cleanup
- **创建日期**: 2026-06-25
- **状态**: 草稿
- **关联**: v0.5-005-namespace-cleanup（路径漏改）, v0.5-007-multi-ide-boards（.opencode/agents/ 复制污染）
## 背景
[source: project/specs/v0.5-009-test-cleanup/spec.md#]
v0.5-005 namespace cleanup (commit `cc49718`) 把 `wiki/` 与 `raw/` 收归到 `.specforge/wiki/` 与 `.specforge/raw/`，但**漏改了 `agents/*.md` 中所有"写入路径"行**——把旧路径 `wiki/pages/{x}.md` 在文本替换成 `wiki/` 前缀时多打了 `.specforge/`，变成 `.specforge/.specforge/wiki/pages/{x}.md`（多一个 `.specforge/`）。
后续 v0.5-007 OpenCode board 生成 `.opencode/agents/*.md` 时，从源 `agents/*.md` 复制，所以 bug 也被复制到了 `.opencode/agents/`。
**实际影响**: 12+ 个 agent 的 wiki 写入动作会写到错误路径 `.specforge/.specforge/wiki/`，导致 wiki 完全空（写到不存在目录的子路径里），用户感知不到数据写入。
v0.5-005 commit 消息同时记了 3 个 pre-existing 失败的回归测试债，状态经核验：
- `test_init_adopt_path` T01/T05 — 仍失败（断言旧的 `agents/` 路径）
- `test_templates` UT-012-02 — **已通过**（`templates/spec.md:74` 已有 `## 澄清记录`，不在范围内）
- `test_specforge_cli` CLI-601 — 47 个测试因中文 test 名字符编码问题只跑了 17 个，无法判断真伪
## 目标
[source: project/specs/v0.5-009-test-cleanup/spec.md#]
1. 修复 `agents/*.md` (12 个) 中所有 `.specforge/.specforge/wiki/` → `.specforge/wiki/`
2. 重新生成 `.opencode/agents/*.md` (10 个) 同步修复
3. 修复 `test_init_adopt_path` T01/T05 的路径断言
4. 把 `test_specforge_cli.bats` 的中文 test 名改为英文/拼音 ID，绕开 bats locale 问题
5. 跑全量 bats 0 回归，bump VERSION 0.5.1 → 0.5.2
## 非目标
[source: project/specs/v0.5-009-test-cleanup/spec.md#]
- 不修改 v0.5-005 的 `init` / `upgrade` 行为（已正确）
- 不重写任何 agent 的"职责描述"，仅修"写入路径"行
- 不引入 bats locale 修复（env 配置），只把中文 test 名 ASCII 化
- 不动 `tests/test_templates`（已通过）
## 用户故事
[source: project/specs/v0.5-009-test-cleanup/spec.md#]
### US-010
[source: project/specs/v0.5-009-test-cleanup/spec.md#us-010]
story: 作为 specforge 用户，我希望 Librarian / Scout / Sage 等 agent 把 wiki 页面写到 `.specforge/wiki/pages/`，而不是不存在的 `.specforge/.specforge/wiki/pages/`，以便 wiki 真的能被构建。
priority: P0
### US-020
[source: project/specs/v0.5-009-test-cleanup/spec.md#us-020]
story: 作为 specforge 用户，我希望 OpenCode IDE 加载的 agent 也用正确的写入路径，以便 OpenCode 环境下 wiki 写入同样有效。
priority: P0
### US-030
[source: project/specs/v0.5-009-test-cleanup/spec.md#us-030]
story: 作为 specforge 维护者，我希望 `bats tests/test_specforge_cli.bats` 真的跑 47 个测试，而不是被中文 test 名字符编码吃掉 30 个，以便我能信任回归基线。
priority: P0
### US-040
[source: project/specs/v0.5-009-test-cleanup/spec.md#us-040]
story: 作为 specforge 维护者，我希望 `test_init_adopt_path` 断言新路径 `.specforge/agents/`，与 v0.5-005 后的 init 行为一致。
priority: P0
## 功能需求
[source: project/specs/v0.5-009-test-cleanup/spec.md#]
### FR-010 修复 agents/*.md 写入路径
[source: project/specs/v0.5-009-test-cleanup/spec.md#fr-010--agents-md-]
`agents/{Arbiter,Archer,Maestro,Cynic,Warden,Sage,Forge,Lex,Keeper,Scout,Prism,Hunter,Shield,Guide}.md` 中所有形如：
```
.specforge/.specforge/wiki/pages/...
```
的行（通常是"写入路径"或 wiki 路径说明），替换为：
```
.specforge/wiki/pages/...
```
AC：`grep -rn '\.specforge/\.specforge/' agents/ | wc -l` 返回 0；`grep -rn '\.specforge/wiki/' agents/ | wc -l` 至少 13（每个 agent 至少 1 处）。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-020 重新生成 .opencode/agents/*.md
[source: project/specs/v0.5-009-test-cleanup/spec.md#fr-020--opencode-agents-md]
跑 `specforge_board.py`（v0.5-007 引入）重新生成 `.opencode/agents/*.md`，使 OpenCode 环境的 agent 写入路径同步修复。
AC：`grep -rn '\.specforge/\.specforge/' .opencode/ | wc -l` 返回 0；`.opencode/agents/*.md` 文件数与 `agents/*.md` 数量一致。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-030 test_init_adopt_path 路径断言同步
[source: project/specs/v0.5-009-test-cleanup/spec.md#fr-030-test_init_adopt_path-]
`tests/test_init_adopt_path.bats` T01 与 T05 的 `[ -d "agents" ]` / `[ -d "newproj/agents" ]` 改为 `[ -d ".specforge/agents" ]` / `[ -d "newproj/.specforge/agents" ]`。
AC：`bats tests/test_init_adopt_path.bats` 5/5 通过。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-040 test_specforge_cli.bats 中文 test 名 ASCII 化
[source: project/specs/v0.5-009-test-cleanup/spec.md#fr-040-test_specforge_clibats--test--ascii-]
`tests/test_specforge_cli.bats` 中所有 `@test "中文..."` 行，改为 `@test "CLI-NNN: <english_or_pinyin_id> <short_desc>"` 形式：
| 当前中文名 | 新 ID |
|---|---|
| `CLI-001: bin/specforge 启动` | `CLI-001: bin_specforge_starts` |
| `CLI-002: bin/specforge 无输出走 bash` | `CLI-002: bin_specforge_no_output_via_bash` |
| `CLI-003: 中文输出 (被 bash 截断)` | `CLI-003: chinese_output_truncated_by_bash` |
| `CLI-100: 缺 --help` | `CLI-100: missing_help_flag` |
| ... | (依此类推) |
重命名原则：
- 保留原中文描述作为行尾注释（可选，便于追踪）
- ID 用 `[a-z0-9_]` + 冒号 + 简短英文描述
- 冒号前后保持与现有 bats 习惯一致
AC：`bats tests/test_specforge_cli.bats` 实际跑的测试数 ≥ 47/47（不再有 "unknown test name" 警告）；跑通率 = 47/47，或失败仅限真实 bug 且记录在 AC 缺口表。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
---
### FR-050 全量回归 + bump VERSION
[source: project/specs/v0.5-009-test-cleanup/spec.md#fr-050---bump-version]
- `find tests -name '*.bats' | xargs bats` 0 回归
- VERSION 0.5.1 → 0.5.2
- `install.sh` 与 `bin/specforge` 的版本字串同步（如有）
AC：`bats tests/*.bats` exit code 0；`cat VERSION` 输出 `0.5.2`；`specforge version` 输出 `0.5.2`。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
## 用户使用场景
[source: project/specs/v0.5-009-test-cleanup/spec.md#]
### scenario-010 Agent 写入路径自检
[source: project/specs/v0.5-009-test-cleanup/spec.md#scenario-010-agent-]
1. 维护者升级 specforge 到 0.5.2
2. 在项目内启动任一 agent (如 Sage)
3. Sage 按 `agents/Sage.md` 写入 wiki → 实际写到 `.specforge/wiki/pages/sage-{topic}.md`
4. 维护者 `ls .specforge/wiki/pages/` 能看到新增文件
5. 之前漏改造成的 `.specforge/.specforge/` 鬼目录不再产生
### scenario-020 CI 跑全量 bats
[source: project/specs/v0.5-009-test-cleanup/spec.md#scenario-020-ci--bats]
1. 维护者在 CI 跑 `bats tests/*.bats`
2. `test_specforge_cli` 不再因 "unknown test name" 跳过 30 个测试
3. 真实跑 47/47，CI 能可靠地反映基线
## 待修复文件清单
[source: project/specs/v0.5-009-test-cleanup/spec.md#]
```
agents/Arbiter.md:101
agents/Archer.md:109
agents/Maestro.md:160
agents/Cynic.md:113
agents/Warden.md:118
agents/Sage.md:365
agents/Guide.md:38,39,40,41,46
agents/Forge.md:142
agents/Lex.md:283
agents/Keeper.md:108
agents/Scout.md:219
agents/Prism.md:154
agents/Hunter.md:142
agents/Shield.md:103
.opencode/agents/*.md  (10+ files, 由 specforge_board 重新生成)
tests/test_init_adopt_path.bats:28,58
tests/test_specforge_cli.bats (全部中文 test 名, ~30 个)
VERSION
```
## 风险
[source: project/specs/v0.5-009-test-cleanup/spec.md#]
- 改 agent 路径字符串后，已按旧路径写过的用户需要手动 `mkdir -p .specforge/wiki/pages` 重建或迁移（v0.5-005 已为 wiki/raw 做过迁移脚本；本 spec 不重复覆盖，但加 ADR 说明）
- `.opencode/agents/` 是 v0.5-007 生成的派生产物，重新生成可能改变 model alias 解析结果（不会，本 spec 不改 board 模型映射）
## 上游 commit 引用
[source: project/specs/v0.5-009-test-cleanup/spec.md#-commit-]
- v0.5-005: `cc49718` (refactor(layout)!: move wiki/ + raw/ to .specforge/ + auto-migrate)
- v0.5-007: `ed27d52` (feat(board): add OpenCode board generation and model alias resolution)
- v0.5-005 commit message 中"pre-existing 失败"清单（test_init_adopt_path T01/T05、test_templates UT-012-02、test_specforge_cli CLI-601）— 经核验 UT-012-02 已通过，本 spec 只修前 2 项

## v0.5-010-ASCII-test-names

# v0.5-010 — bats test 名 ASCII 化 — Spec
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#v05-010--bats-test--ascii---spec]
- **Spec ID**: v0.5-010-ASCII-test-names
- **创建日期**: 2026-06-25
- **状态**: 草稿
- **关联**: v0.5-009-test-cleanup（修了 1/7 个 bats 文件）
## 背景
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#]
[v0.5-009-test-cleanup](v0.5-009-test-cleanup/spec.md) 顺手把 `tests/test_specforge_cli.bats` 的 31 个中文 test 名改为 ASCII ID（绕开 bats 多字节 test 名字符编码 bug）。但当时只扫到一个文件，剩余 6 个 bats 文件有同类问题：
| 文件 | 实际运行 | 期望 | 缺口 | 中文 test 名 |
|---|---|---|---|---|
| `test_identity_check.bats` | 0 | 15 | -15 | 15 |
| `test_issue_form.bats` | 0 | 37 | -37 | 37 |
| `test_maestro.bats` | 0 | 5 | -5 | 5 |
| `test_probe.bats` | 0 | 7 | -7 | 7 |
| `test_sage_lex_pr_discussion.bats` | 2 | 8 | -6 | 6 |
| `test_scout_project_board.bats` | 3 | 6 | -3 | 3 |
| **合计** | **5** | **78** | **-73** | **73** |
这 73 个测试**实际根本没跑**（bats 在解析 `@test "中文..."` 时抛 `unknown test name` 然后 skip），CI 基线不可信。任何这些文件里的功能 bug 都不会被捕获。
**漏检原因**：v0.5-009 全量回归时，bats 在 `tests/*.bats` glob 下读 23 个文件，218 个测试"执行了"，但其中 ~73 个是 silent skip。如果不是逐文件看 bats warning "Executed N instead of expected M"，根本察觉不到。
## 目标
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#]
1. 把 6 个 bats 文件中所有 `@test "中文..."` 改为 `@test "<ID>: <english_id> <short_desc>"` 形式
2. 跑全量 bats 验证 0 回归（除 v0.5-009 已记录的两类 pre-existing 失败）
3. bump VERSION 0.5.4 → 0.5.5
4. 在 `.specforge/wiki/decisions/` 补一条"bats test 名约定"小 ADR 或在 README 写明"test 名应为 ASCII"
## 非目标
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#]
- 不修测试**逻辑**（即便有失败，也只动 test 名）
- 不引入 bats locale 修复（env 配置）
- 不动 v0.5-009 已修的 `test_specforge_cli.bats`
- 不动其它 16 个 bats 文件（已经 ASCII 化或无中文 test 名）
## 用户故事
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#]
### US-010
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#us-010]
story: 作为 specforge 维护者，我希望 `bats tests/*.bats` 真的跑 280+ 个测试，而不是被中文 test 名吃掉 73 个，以便 CI 基线可信。
priority: P0
### US-020
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#us-020]
story: 作为 specforge 用户，我希望 `bats tests/test_identity_check.bats` 等能真正验证 `check_identity.py` 的行为（online/offline L1-L5 全跑），而不是空跑 0 个测试。
priority: P0
## 功能需求
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#]
### FR-010 test_identity_check.bats 15 个 ASCII 化
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#fr-010-test_identity_checkbats-15--ascii-]
文件: `tests/test_identity_check.bats`
影响 test 名 (sample): `ID-001: check_identity.py 存在` → `ID-001: check_identity_py_exists`
AC: `bats tests/test_identity_check.bats` 实际跑数 ≥ 15，不再出现 "unknown test name"。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
### FR-020 test_issue_form.bats 37 个 ASCII 化
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#fr-020-test_issue_formbats-37--ascii-]
文件: `tests/test_issue_form.bats`
影响 test 名 (sample): `FORM-001: feature.yml 文件存在` → `FORM-001: feature_yml_exists`
AC: `bats tests/test_issue_form.bats` 实际跑数 ≥ 37。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
### FR-030 test_maestro.bats 5 个 ASCII 化
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#fr-030-test_maestrobats-5--ascii-]
文件: `tests/test_maestro.bats`
AC: `bats tests/test_maestro.bats` 实际跑数 ≥ 5。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
### FR-040 test_probe.bats 7 个 ASCII 化
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#fr-040-test_probebats-7--ascii-]
文件: `tests/test_probe.bats`
AC: `bats tests/test_probe.bats` 实际跑数 ≥ 7。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
### FR-050 test_sage_lex_pr_discussion.bats 6 个 ASCII 化
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#fr-050-test_sage_lex_pr_discussionbats-6--ascii-]
文件: `tests/test_sage_lex_pr_discussion.bats`
AC: `bats tests/test_sage_lex_pr_discussion.bats` 实际跑数 ≥ 8（之前 2 个 ASCII + 6 个中文 = 8）。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
### FR-060 test_scout_project_board.bats 3 个 ASCII 化
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#fr-060-test_scout_project_boardbats-3--ascii-]
文件: `tests/test_scout_project_board.bats`
AC: `bats tests/test_scout_project_board.bats` 实际跑数 ≥ 6。
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
### FR-070 命名约定文档化
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#fr-070-]
在 `.specforge/wiki/decisions/008-bats-test-name-convention.md` 写明：
- bats test 名建议用 ASCII (`[a-z0-9_-:]`)
- 中文描述可作为 `## Description` 注释紧随 `@test` 行
- locale 不可控（CI runner 多为 `C.UTF-8`），多字节名字无法保证跨平台一致
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
### FR-080 跑全量 bats 0 新回归 + bump VERSION
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#fr-080--bats-0---bump-version]
- `bats tests/*.bats` 跑 280+ 测试（不再 silent skip 73 个）
- 已记录的 pre-existing 失败 (`test_branch_naming.bats` BRANCH-* × 6, `test_verify_acceptance.bats` VA-T02/T07) 不在本 spec 修复范围
- 新发现的失败若非字符编码问题，进入 `task-log.md` 留待下个 spec
AC:
- `bats tests/*.bats 2>&1 | grep "Executed N instead"` 输出为空（无 silent skip）
- VERSION = 0.5.5
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
## 验收标准
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#]
| ID | 描述 | 验证方法 |
|---|---|---|
| AC-010 | 6 个 bats 文件的所有中文 test 名被替换为 ASCII ID | `grep -rn '@test "[^"]*[^\x00-\x7f]' tests/` 输出为空（除个别允许的非 ASCII 注释） |
| AC-020 | bats 不再 silent skip 任何测试 | `bats tests/*.bats 2>&1 \| grep "Executed N instead"` 为空 |
| AC-030 | 全量 bats 无新失败 | 对比 v0.5-009 baseline，失败数 = v0.5-009 baseline（不增加） |
| AC-040 | VERSION 已 bump | `cat VERSION` = `0.5.5` |
| AC-050 | ADR 008 已写 | `.specforge/wiki/decisions/008-bats-test-name-convention.md` 存在 |
| AC-060 | 已 commit | `git log -1 --format=%s` 含 `v0.5-010` |
## 风险
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#]
- **R-010** 改 test 名可能引入复制粘贴错位（test ID 与断言行不对应） → 用 `bats --print-output-on-failure` 逐文件验证
- **R-020** 某些中文 test 名含 sub-assertion 描述（例："离线 - WRITE 通过 [通过], exit 0"），ASCII 化时需保留语义 → ID 用 `<scenario>_<expected_outcome>` 模板
- **R-030** 中文 ID 改 ASCII 后丢失人类可读性 → 在 `@test` 行后留中文注释作为 `## Description`
## 任务拆解
[source: project/specs/v0.5-010-ASCII-test-names/spec.md#]
```
1. 写 ADR 008 (bats test name convention)
2. 改 test_identity_check.bats (15)
3. 改 test_issue_form.bats (37)
4. 改 test_maestro.bats (5)
5. 改 test_probe.bats (7)
6. 改 test_sage_lex_pr_discussion.bats (6)
7. 改 test_scout_project_board.bats (3)
8. 跑全量 bats 验证 0 新回归
9. bump VERSION 0.5.4 → 0.5.5
10. commit + tag v0.5.5
```

## v0.5-011-bats-name-lint-and-test-recovery

# v0.5-011 — bats name lint + 25 个 test 失败的根因修复 — Spec
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#v05-011--bats-name-lint--25--test---spec]
- **Spec ID**: v0.5-011-bats-name-lint-and-test-recovery
- **创建日期**: 2026-06-25
- **状态**: 草稿
- **关联**: v0.5-009-test-cleanup, v0.5-010-ASCII-test-names
## 背景
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#]
[v0.5-010](v0.5-010-ASCII-test-names/spec.md) ASCII 化 73 个 silent-skip 测试后，跑出真实基线：**291 个测试 / 266 通过 / 25 失败**。v0.5-009 之前这 25 个 silent skip，无人察觉，现在需要分门别类处理。
经深入分析（每条失败查测试断言、工具源码、agent prompt），25 个失败可归 6 类：
| 类别 | 数量 | 性质 | 修复方向 |
|---|---|---|---|
| BRANCH-* | 6 | 测过期约定（v0.4-004 退休的 `spec/{spec-id}`） | 删测试 |
| PROBE-FORM-001/002/004 | 3 | 测过期 Probe prompt 关键词（v0.5-008 重写后未同步） | 改测试 |
| PROBE-FORM-005/006/007 | 3 | 测过期 Probe 反模式声明 | 删测试 |
| SCOUT-ID-001/002/003 | 3 | **真实 bug**（Scout.md 漏身份检查步骤） | 改 Scout.md |
| QP_T04/T05/T17/IT-003 | 4 | **真实 bug**（quote_parser `is_ready` 算法错） | 改 quote_parser.py |
| QP_T19/T20 | 2 | **真实 bug**（JSON schema 缺 `owner_close_role` 字段） | 改 quote_parser.py |
| VA-T02/T07 | 2 | **真实 bug**（verify_acceptance L2 regex 匹配错标题级别） | 改 verify_acceptance.py |
| T05_sage/T06_lex | 2 | **真实 bug**（Sage.md/Lex.md 未引用 quote_parser） | 改 Sage.md/Lex.md |
**核心危害**：
- quote_parser `is_ready` 错算 → spec 004 quote gate 失效，6 open quote 仍报 ready
- verify_acceptance L2 regex 错配 → acceptance.md 漏 FR 不会被检出，Lex 拿到不完整 acceptance 仍进入 stage-2
- SCOUT 漏身份检查步骤 → Scout 在 git config 不一致时也能进 Stage 1，污染后续
- Sage/Lex 不引用 quote_parser → spec 004 工作流在 agent 端是"瞎子"，agent 看不到 quote 状态
## 目标
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#]
1. 防 silent skip 复发：写 `tools/lint_bats_names.sh`，CI 强制检查新 test 名 ASCII
2. 修 13 个真实 bug（agent prompt + Python 工具）
3. 删 9 个过期测试（BRANCH 6 + PROBE 3）
4. 改 3 个过期测试断言（PROBE-FORM-001/002/004）
5. 跑全量 bats 0 失败（除 known-failing 如有），bump VERSION 0.5.5 → 0.5.6
## 非目标
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#]
- 不实现 `bin/specforge lint-bats` 子命令（用 shell script 足够）
- 不引入 pre-commit hook（v0.6 再说）
- 不重写整个 quote_parser / verify_acceptance（只修对应 bug）
- 不动其它 16 个 bats 文件
## 用户故事
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#]
### US-010
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#us-010]
story: 作为 specforge 维护者，我希望 CI 拒绝任何新的中文 bats test 名入库，以便 silent skip bug 模式不再发生。
priority: P0
### US-020
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#us-020]
story: 作为 specforge 用户，我希望 Scout 在初始化项目时真跑身份检查（而不是文档写"必跑"但实际漏掉），以便 git config 不一致时不会污染项目。
priority: P0
### US-030
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#us-030]
story: 作为 specforge 用户，我希望 `quote_parser --check-ready` 在还有 open quote 时返回非 0，以便 IDE/agent 真正被 gate 挡住。
priority: P0
### US-040
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#us-040]
story: 作为 specforge 维护者，我希望 `verify_acceptance.py` 的 L2 检查真能检出"acceptance.md 缺 FR 节"，以便 Lex 拿到不完整 acceptance 时能 reject。
priority: P0
### US-050
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#us-050]
story: 作为 specforge 用户，我希望 Sage / Lex 在 spec 004 quote 工作流时引用 `tools/quote_parser.py`，以便 agent 能查 quote 状态做决策。
priority: P1
## 功能需求
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#]
### FR-010 tools/lint_bats_names.sh
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#fr-010-tools-lint_bats_namessh]
**触发**: `bin/specforge ci-lint-bats` 或 `make lint-bats` 或 CI step
**逻辑**: 扫描 `tests/*.bats`，找 `@test "<NAME>"` 行，断言 `<NAME>` 全部字节为 ASCII (`[\x00-\x7F]`)。失败退出码 1，输出每条违规的 file:line + 原名。
AC: `tools/lint_bats_names.sh tests/*.bats` exit 0（已 ASCII 化）；人为改回 1 个中文名后 exit 1 + 报错。
### FR-020 quote_parser.py is_ready 算法修
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#fr-020-quote_parserpy-is_ready-]
**Bug**: `tools/quote_parser.py:443` `result.is_ready = len(result.ready_blockers) == 0`，只看 `ready_blockers` 是否为空。但 spec 004 设计意图是"无 open quote 时 ready"。
**Fix**: 改为 `result.is_ready = len(result.open_quotes) == 0 and len(result.ready_blockers) == 0`。
AC: `bats tests/test_quote_parser.bats` QP_T04/T05/T17 通过。
### FR-030 quote_parser.py JSON 加 owner_close_role 字段
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#fr-030-quote_parserpy-json--owner_close_role-]
**Bug**: 工具 dataclass 已有 `owner_close_role` 字段（`tools/quote_parser.py:101, 241`），`--check-violations` 也用它（line 491），但 `--format json` 输出 schema 没暴露它（line 511-528）。
**Fix**: 在 JSON 输出加 `owner_close_role`（per quote 或 per result，由 schema 决定；这里选择 per quote，归到 `open_quotes[]` / `resolved_quotes[]` 每条记录里）。
AC: `bats tests/test_quote_parser.bats` QP_T19/T20 通过。
### FR-040 verify_acceptance.py L2 regex 改二级标题
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#fr-040-verify_acceptancepy-l2-regex-]
**Bug**: `tools/verify_acceptance.py:35` `RE_FR_SECTION = re.compile(r"^###\s+(FR|NFR)-...")` 匹配三级标题，但 acceptance.md 中 FR/NFR 节是二级 `## FR-`（line 38 已正确）。spec.md 用三级 `### FR-`（line 33）正确。所以工具只看 spec.md 的 FR 列表，但 acceptance.md 的 FR 节用同一 regex 找不到。
**Fix**: 拆成两个 regex：`RE_SPEC_FR` (三级，匹配 spec.md) 和 `RE_ACC_FR` (二级，匹配 acceptance.md)。`RE_ACC_FR` 已经存在 (line 38)。
AC: `bats tests/test_verify_acceptance.bats` VA-T02/T07 通过。
### FR-050 Scout.md 补身份检查
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#fr-050-scoutmd-]
**Bug**: `agents/Scout.md` 未在 Step 4 引用 `tools/check_identity.py`、未把身份检查放在 issue 冒烟之前、退出条件不含"身份一致"。
**Fix**: 在 `Scout.md` 加 Step 4a 身份一致性检查段、Step 4b 才是 issue/PR 权限冒烟、退出条件加"身份一致 (Scout-ID-001/002/003 覆盖)"。
AC: `bats tests/test_scout_project_board.bats` SCOUT-ID-001/002/003 通过。
### FR-060 Sage.md / Lex.md 引用 quote_parser
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#fr-060-sagemd---lexmd--quote_parser]
**Bug**: `agents/Sage.md` / `agents/Lex.md` 未引用 `tools/quote_parser.py`。
**Fix**: 在 quote dialogue 阶段相关段落加 `tools/quote_parser.py --check-ready` / `tools/quote_parser.py --check-violations` 引用。
AC: `bats tests/test_spec004_sage_lex.bats` T05/T06 通过。
### FR-070 删/改过期测试
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#fr-070--]
**删** (6+3=9 个):
- `test_branch_naming.bats` BRANCH-001/006/007/008/009/010（测过期分支约定）
- `test_probe.bats` PROBE-FORM-005/006/007（测 v0.5-008 已废的反模式声明）
**改** (3 个):
- `test_probe.bats` PROBE-FORM-001: 改测"Probe 引用 issue form 字段"（与 FORM-002 合并）
- `test_probe.bats` PROBE-FORM-002: 保留
- `test_probe.bats` PROBE-FORM-004: 改测"Probe 命名约定 UT-{issue#}-{AC序}-{测试序}"
AC: 跑全量 bats，0 失败（除 known-failing）。
### FR-080 run bats 0 fail + bump VERSION
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#fr-080-run-bats-0-fail--bump-version]
- 跑 `bats tests/*.bats` 应达到 0 失败（或只剩 known-failing）
- VERSION 0.5.5 → 0.5.6
- commit + tag
## 验收标准
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#]
| ID | 描述 | 验证 |
|---|---|---|
| AC-010 | `tools/lint_bats_names.sh` 存在并能工作 | `bash tools/lint_bats_names.sh tests/*.bats` exit 0 |
| AC-020 | quote_parser `is_ready` 算法修复 | `bats tests/test_quote_parser.bats` 22/22 通过 |
| AC-030 | quote_parser JSON 含 owner_close_role | `bats tests/test_quote_parser.bats` 22/22 通过 |
| AC-040 | verify_acceptance L2 修 | `bats tests/test_verify_acceptance.bats` 7/7 通过 |
| AC-050 | Scout.md 修 | `bats tests/test_scout_project_board.bats` 6/6 通过 |
| AC-060 | Sage.md + Lex.md 修 | `bats tests/test_spec004_sage_lex.bats` 8/8 通过 |
| AC-070 | 过期测试删除/修改 | `bats tests/test_branch_naming.bats` 仅剩 5 个 ASCII-passing 测试 |
| AC-080 | 全量 bats 0 fail | `bats tests/*.bats | grep -c "^not ok"` = 0 |
| AC-090 | VERSION 已 bump | `cat VERSION` = `0.5.6` |
| AC-100 | 已 commit + tag | `git tag | grep v0.5.6` |
## 任务拆解
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#]
```
T1. 写 tools/lint_bats_names.sh          (~30 行)
T2. 修 quote_parser.py is_ready           (~5 行改)
T3. 修 quote_parser.py JSON schema        (~10 行加)
T4. 修 verify_acceptance.py L2 regex      (~5 行拆)
T5. 修 agents/Scout.md (3 处)             (~10 行加)
T6. 修 agents/Sage.md + Lex.md (各 1 段)  (~10 行加)
T7. 删 BRANCH-* 6 个 + PROBE-FORM 005/006/007 3 个 + 改 PROBE-FORM-001/002/004 3 个
T8. 跑全量 bats 验证 0 fail
T9. bump VERSION 0.5.5 → 0.5.6 + commit + tag
```
## 风险
[source: project/specs/v0.5-011-bats-name-lint-and-test-recovery/spec.md#]
- **R-010** 改 quote_parser `is_ready` 算法可能影响下游 spec 004 gate 行为（spec 004 用户原本依赖 `len(ready_blockers)==0`）
→ 加 `result.is_ready_open_quotes_only` 旁路字段保留旧行为；默认改新行为
- **R-020** 删 BRANCH-* 测试可能丢失 v0.4 时期的回归保险
→ 在 `tests/test_branch_naming.bats` 顶部加注释说明这些约定已退役，新约定在 ADR 005
- **R-030** 修 Scout.md / Sage.md / Lex.md 可能引入 prompt 不一致
→ 改完跑 `bats tests/test_*.bats` 中所有引用这些 agent 的测试，确保无新失败

## v0.6-005-agent-consolidation-and-pairing

# v0.6-005 — Agent 命名重构（角色 + 智力双维度）— Spec
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#v06-005--agent----spec]
- **Spec ID**: v0.6-005-agent-consolidation-and-pairing
- **创建日期**: 2026-06-26
- **状态**: 草稿（命名方案待 Aaron 拍板）
- **关联**: v0.6-001-rebrand-to-quanti-forge
## 背景
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#]
在软件开发中，我们可以看到有以下流程：
1. 项目奠基。决定本次开发使用的 base brach, 本此发布的版本号、分支等基础设施。
2. 需求定义与澄清。需求可能从一个故事或者 PRD 开始，直到转化成一条条具体的、可以测试的需求结束。这些需求可能是功能性的，也可能是非功能性的（为了完成用户故事必须的、辅助性的）。最终输出是相互印证的 spec, acceptance和测试计划文档。
3. 设计阶段。根据2得到的文档，进行接口和架构设计。在 Agent 开发场景下，人类从这一步起开始淡出。人类可能还需要 review 下 interface 文档，但理论上，可以完全不管架构设计 -- 这是 Agent 应该去做、应该去试的部分。极端地，即使 Agent 设计出来的架构不工作，他们也应该有能力换一个 -- 但必须满足 spec 要求。
4. 构建阶段。这是代码生产的主要阶段。代码有功能代码、单元测试代码和e2e 代码。功能代码与单元测试代码应该由同一 Agent 来编写，但 e2e 代码需要另有其人来编写。
5. 构建阶段还涉及到大量、频繁的 code review，以及要决定哪一个 FR 先做，哪一个后做等等。
6. 需求需要通过 project 管理方法划分成为一个个 milestone。它的意义是，我们可以获得阶段性的成果，这对回滚来说很重要。由于 spec 之间互有依赖，这需要一个很强的架构师来决定。
7. 每个 milestone 结束，就应该打上 tag
8. 所有 milestone 完成，单元测试覆盖率超过约定，e2e 全部跑通，本次开发即可收尾
9. 技术作家入场，结合项目记忆，story, spec 等，撰写用户文档。
10. build master 准备打包发布。
Maestro - 负责协调、推进。
quanti-forge 当前有 **18 个 agent**（含 ROSTER.md + 17 个角色文件，3108 行），命名存在三个问题：
1. **配对不直观**：`Sage` 与 `Lex`、`Hunter` 与 `Shield` 命名看不出"成对儿"
2. **职责不可见**：看到名字不知道它在干什么（例如 `Herald` 是什么？）
3. **智力不显式**：看到名字不知道该配什么级别模型（强/弱）
Aaron 2026-06-26 的命名准则：
> 1. **反映角色的作用**：例如 `Maestro` — 看名字就知道是指挥、有协调能力、智力也不弱
> 2. **反映角色的智力**：看名字就知道大致该用哪个级别的模型
>
> 个别角色很难同时满足以上两点，**尽力追求**。
Aaron 暂未拍板最终方案，本 spec 列出**多个候选方案** + 评估，等 Aaron 决策后再进入实施。
## 命名准则（Aaron 2026-06-26 定稿）
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#aaron-2026-06-26-]
### 准则 1：反映作用（必须）
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#-1]
- 名字本身要**让人知道这个角色做什么**
- 看到名字能立刻判断"它是设计者 / 实现者 / 守门者 / 协调者"
- 必要时配**副标题/标题**（中文括注）强化作用
### 准则 2：反映智力（必须）
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#-2]
- 名字暗示**大致智力级别**，以便用户/调度器自动选模型
- 三档：
- **强**（claude-sonnet-4 / deepseek-v4-pro / glm-5.2）：复杂推理、架构设计、产出完整 spec
- **中**（claude-haiku-4.5 / deepseek-v4 / gpt-4o）：常规审核、守门、按清单检查
- **轻**（claude-haiku-3.5 / gpt-4o-mini / deepseek-v4-mini）：格式校验、关键词扫描、清单勾选
> 准则 2 是软约束：用户可手动覆盖模型，命名只提供默认建议。
### 准则 3：配对可视化（保留旧目标）
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#-3]
- 实施者 ↔ 验收者名字上有视觉关联（不强制 -ie，可考虑其它方案）
- 配对的目的：对话中说"Scout 通过了"用户立刻知道"那 Scoutie 也通过了吗"
## 候选命名方案（待 Aaron 决策）
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#-aaron-]
### 方案 A：**-ie 后缀约定**（原方案，保留参考）
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#-a-ie-]
| 角色 | 实施者 | 验收者 (-ie) | 智力暗示 |
|---|---|---|---|
| Story/PRD | Scout | Scoutie | Scout 中 / Scoutie 轻 |
| Interview | Sage | Sagie | Sage 强 / Sagie 中 |
| Test Plan | Probe | Probie | Probe 中 / Probie 轻 |
| 执行规划 | Archer | Archerie | Archer 强 / Archerie 中 |
| 任务执行 | Forge | Forgeie | Forge 强 / Forgeie 中 |
| Bug 修复 | Hunter | Hunterie | Hunter 中 / Hunterie 轻 |
| 指挥 | Maestro | — | 强 |
| 方法论 | Guide | — | 中 |
| 验收汇总 | Herald | — | 中 |
**评估**：
- ✅ 配对可视化强（差一个 `ie`）
- ✅ 智力暗示清晰（无 `-ie` = 实施者，强；`-ie` = 验收者，弱/中）
- ⚠️ 部分词根读音奇怪（Archerie、Hunterie 拼写长）
- ⚠️ 元角色（Maestro/Guide/Herald）不参与配对，规则不统一
**变体 A1**：Aaron 在 2026-06-26 后续反馈中提到"还没定"，所以这是参考方案。
### 方案 B：**-er / -ie 双后缀（实施/守门）**
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#-b-er----ie--]
| 角色 | 实施者 | 守门者 | 智力暗示 |
|---|---|---|---|
| Story/PRD | Scout | Scoutie | 强 / 轻 |
| Interview | Sage | Sageie / Sagie | 强 / 中 |
| Test Plan | Prober | Probier | 强 / 轻 |
| 执行规划 | Archer | Archerie | 强 / 中 |
| 任务执行 | Forger | Forgeie | 强 / 中 |
| Bug 修复 | Hunter | Hunterie | 强 / 轻 |
| 指挥 | Maestro | — | 强 |
| 方法论 | Guider | — | 中 |
**评估**：
- ⚠️ -er 后缀对部分词根不自然（Prober 听起来奇怪）
### 方案 C：**角色 + 智力双标签**（如 Scout-Pro / Scout-Lite）
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#-c---scout-pro---scout-lite]
| 角色 | 实施者 | 守门者 |
|---|---|---|
| Story/PRD | Scout-Pro | Scout-Lite |
| Interview | Sage-Pro | Sage-Lite |
| Test Plan | Probe-Pro | Probe-Lite |
| 执行规划 | Archer-Pro | Archer-Lite |
| 任务执行 | Forge-Pro | Forge-Lite |
| Bug 修复 | Hunter-Pro | Hunter-Lite |
| 指挥 | Maestro-Pro | — |
| 方法论 | Guide-Mid | — |
**评估**：
- ✅ 智力暗示**最显式**（-Pro/-Lite 直接说明）
- ⚠️ 名字变长（10+ 字符）
- ⚠️ 失去"昵称感"，更像工具名
### 方案 D：**守门者用"-Guard"后缀**
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#-d-guard]
| 角色 | 实施者 | 守门者 |
|---|---|---|
| Story/PRD | Scout | ScoutGuard |
| Interview | Sage | SageGuard |
| Test Plan | Probe | ProbeGuard |
| 执行规划 | Archer | ArcherGuard |
| 任务执行 | Forge | ForgeGuard |
| Bug 修复 | Hunter | HunterGuard |
| 指挥 | Maestro | — |
| 方法论 | Guide | — |
**评估**：
- ✅ "Guard" = 守卫，强语义
- ⚠️ "Guard" 暗示强智能（实际验收者是轻模型），语义矛盾
### 方案 E：**实施者 + Watcher 守门者**（来自 Aaron 思路的混合）
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#-e--watcher--aaron-]
| 角色 | 实施者 | 守门者 |
|---|---|---|
| Story/PRD | Scout | ScoutWatcher |
| Interview | Sage | SageWatcher |
| Test Plan | Probe | ProbeWatcher |
| 执行规划 | Archer | ArcherWatcher |
| 任务执行 | Forge | ForgeWatcher |
| Bug 修复 | Hunter | HunterWatcher |
| 指挥 | Maestro | — |
| 方法论 | Guide | — |
**评估**：
- ✅ "Watcher" = 监视者，弱智能职责明确
- ⚠️ 13 字符，仍偏长
### 方案 F：**保持 -ie 但强化智力暗示**（融合方案）
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#-f--ie-]
| 角色 | 实施者 (强/中) | 验收者 (-ie, 轻) |
|---|---|---|
| Story/PRD | Scout (中) | Scoutie (轻) |
| Interview | Sage (强) | Sagie (轻) |
| Test Plan | Probe (中) | Probie (轻) |
| 执行规划 | Archer (强) | Archerie (中) |
| 任务执行 | Forge (强) | Forgeie (中) |
| Bug 修复 | Hunter (中) | Hunterie (轻) |
| 指挥 | Maestro (强) | — |
| 方法论 | Guide (中) | — |
每个 agent 的 YAML frontmatter 加 `tier: pro|middle|lite` 显式标注，便于 `quanti_forge_board.py` 自动调度。
**评估**：
- ✅ -ie 配对 + tier 智力双维度
- ✅ 用户可一眼识别配对（差一个 `ie`）+ 通过 tier 字段看智力
- ⚠️ 仍是 13 字符内，复合词为主
## 推荐方案
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#]
**方案 F（融合方案）**：保留 `-ie` 配对约定（满足 Aaron 的核心构想）+ 显式 `tier` 字段标注智力。
**理由**：
1. 配对可视化最强（差一个 `ie`，符合 Aaron "一眼成对" 的核心需求）
2. 智力通过 `tier:` frontmatter 字段显式声明，比靠名字猜测更可靠
3. 元角色（Maestro/Guide）保持单名，配对规则不强制适用于元角色
4. 配对映射表（哪个 -ie 替代哪个旧评审）已在 Aaron 反馈中确认
## 削减方案（与命名独立）
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#]
无论选哪个命名方案，**agent 总数都建议削减到 13**：
- 6 实施 + 6 -ie 验收 + Maestro = 13
- **Aaron 决策**：Guide 砍掉 → 职责并入 Sagie；Herald 砍掉 → 职责并入 Scoutie
- 旧评审（Warden/Lex/Judge/Cynic/Keeper/Prism/Shield）**全部消失**，被对应 -ie 替代
## 用户故事
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#]
### US-010
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#us-010]
story: 作为 quanti-forge 用户，我希望看到 agent 名字就知道它在干什么（作用），以便对话引用时立刻定位角色。
priority: P0
### US-020
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#us-020]
story: 作为 quanti-forge 用户，我希望看到 agent 名字就知道它大致应该用什么级别模型（智力），以便调度器自动选模型。
priority: P0
### US-030
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#us-030]
story: 作为 quanti-forge 用户，我希望实施者 ↔ 验收者配对在名字上一眼可识别，以便对话中提到"Scout 通过了"立刻知道还要看 Scoutie。
priority: P0
### US-040
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#us-040]
story: 作为 quanti-forge 用户，我希望 agent 总数 ≤15，以便新用户上手成本可控。
priority: P1
## 功能需求
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#]
### FR-010 命名方案落地
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#fr-010-]
**采纳方案 F**：
- 实施者：保留原名（`Scout`, `Sage`, `Probe`, `Archer`, `Forge`, `Hunter`, `Maestro`, `Guide`）
- 验收者：实施者名 + `ie`（`Scoutie`, `Sagie`, `Probie`, `Archerie`, `Forgeie`, `Hunterie`）
- 元角色：保留原名（`Maestro`, `Guide`）
AC: `ls agents/*.md` 含 13 个非 ROSTER 文件 + ROSTER.md。
### FR-020 智力 tier 标注
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#fr-020--tier-]
每个 agent 的 YAML frontmatter 加 `tier:` 字段：
| Tier | 智力 | 默认模型 |
|---|---|---|
| `pro` | 强 | claude-sonnet-4, deepseek-v4-pro, glm-5.2 |
| `middle` | 中 | claude-haiku-4.5, deepseek-v4, gpt-4o |
| `lite` | 轻 | claude-haiku-3.5, gpt-4o-mini, deepseek-v4-mini |
**示例**（agents/Sagie.md）：
```markdown
---
name: sagie
description: 验收 spec.md 完整性 + 方法论问答（替代 Lex + Guide）
tier: lite
mode: all
models:
- claude-haiku-3.5
- deepseek-v4-mini
- gpt-4o-mini
---
```
AC: 每个 agent 的 frontmatter 含 `tier: pro|middle|lite` 字段。
### FR-030 旧 agent 文件处理（shim 机制）
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#fr-030--agent-shim-]
- 旧 `agents/{Warden,Lex,Judge,Cynic,Keeper,Prism,Shield,Arbiter,Herald,Guide}.md` 全部改为 shim
- shim 模板：
```markdown
---
name: {old-name}
description: [已替代] 本 agent 已被 v0.6-005 重构
---
# ⚠️ 本 agent 已被 v0.6-005 重构
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#--agent--v06-005-]
- 原职责 → `agents/{NewName}.md`（如 Warden → Scoutie）
- 本文件保留 30 天作为回退路径
```
- 30 天后清理 shim
AC: `cat agents/Warden.md` 含"已替代"或"已合并"字样；shim 不含完整 prompt。
### FR-040 ROSTER.md 重写
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#fr-040-rostermd-]
新表格 13 行（含 Maestro）：
| 阶段 | 实施者 (tier) | 验收者 (tier) |
|---|---|---|
| 全程 | **Maestro** (pro) | — |
| Story/PRD | **Scout** (middle) | **Scoutie** (lite) |
| Interview | **Sage** (pro) | **Sagie** (lite, 含 Guide 职责) |
| Test Plan | **Probe** (middle) | **Probie** (lite) |
| 执行规划 | **Archer** (pro) | **Archerie** (middle) |
| 任务执行 | **Forge** (pro) | **Forgeie** (middle) |
| Bug 修复 | **Hunter** (middle) | **Hunterie** (lite) |
> **Herald 合并入 Scoutie**：最终验收汇总由 Scoutie 输出
> **Guide 合并入 Sagie**：方法论问答由 Sagie 响应
AC: `agents/ROSTER.md` 表格 7 行数据 + tier 列。
### FR-050 bats 测试更新
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#fr-050-bats-]
- 旧 agent 引用更新到新名（除 shim 验证）
- 新增 `tests/test_agent_naming.bats`（6 个 case）：
1. 每个 Name 有 Nameie 配对（pair coverage = 6/6）
2. 每个 agent frontmatter 含 `tier:` 字段
3. -ie 版 tier ∈ {lite, middle}（不能是 pro）
4. 旧评审 agent (Warden/Lex/Judge/Cynic/Keeper/Prism/Shield/Arbiter) 全是 shim
5. shim 含"已替代"或"已合并"
6. ROSTER.md 表格含所有 13 个 agent + tier 列
AC: `bats tests/*.bats` 0 失败；新 `test_agent_naming.bats` 6/6 通过。
### FR-060 ADR 记录 -ie 约定 + tier 字段
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#fr-060-adr---ie---tier-]
**新 ADR**：`.quanti-forge/wiki/decisions/013-agent-ie-pairing-and-tier.md`
**必含段**：
1. 背景：配对不直观 + 模型成本问题
2. Aaron 命名准则（两条 + 尽力追求）
3. 候选方案 A-F + 评估
4. 最终选择：方案 F
5. 配对表 + tier 表
6. 元角色处理（Herald→Scoutie, Guide→Sagie）
7. 回退方案（30 天 shim）
AC: ADR 文件存在 + 含 7 段必含内容。
## 验收标准
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#]
| ID | 描述 | 验证 |
|---|---|---|
| AC-010 | agent 文件数 = 13 | `ls agents/*.md \| grep -v ROSTER \| wc -l` = 13 |
| AC-020 | 每个 Name 有 Nameie 配对 | pair coverage = 6/6 |
| AC-030 | 每个 agent 含 tier 字段 | frontmatter 解析出 tier ∈ {pro, middle, lite} |
| AC-040 | -ie 版 tier ≠ pro | tier 字段值校验 |
| AC-050 | 旧评审 agent 是 shim | `cat agents/Warden.md` 含"已替代" |
| AC-060 | ROSTER.md 表格 7 行 | `grep -c '^\|' agents/ROSTER.md` ≥ 10 |
| AC-070 | ADR 已写 | `.quanti-forge/wiki/decisions/013-agent-ie-pairing-and-tier.md` 存在 |
| AC-080 | bats 全过 | `bats tests/*.bats` 0 失败 |
## 任务拆解
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#]
```
T1. Aaron 拍板命名方案（本 spec 等待）
T2. 写 ADR 013 (含候选方案评估)
T3. 起草 6 个新 -ie agent prompt (含 tier 字段)
T4. 把旧评审 (Warden/Lex/Judge/Cynic/Keeper/Prism/Shield/Arbiter/Herald/Guide) 内容合并到对应新 agent
T5. 17 个旧 agent 文件改 shim
T6. 重写 ROSTER.md (7 行 + tier 列)
T7. 新增 tests/test_agent_naming.bats (6 case)
T8. 更新所有 bats tests 中 agent 引用
T9. 跑全量 bats
T10. commit + ADR
```
## 风险
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#]
- **R-010** Aaron 还没拍板最终命名方案（候选 A-F），本 spec 是**决策挂起**状态
→ spec 列出所有候选 + 评估，等 Aaron 选择
- **R-020** `tier:` 字段是软约定，工具不强制
→ `tools/quanti_forge_board.py` 读取 tier 并 fallback 到 models 列表
- **R-030** 用户已习惯旧名，新名映射需要过渡
→ 30 天 shim + ADR 含"旧名→新名对照表"
- **R-040** 部分 -ie 名读音奇怪（Archerie）
→ 文档明示"读作 ar-cher-ee"，避免误读
## 关联 spec
[source: project/specs/v0.6-005-agent-consolidation-and-pairing/spec.md#-spec]
- v0.6-001-rebrand：旧 prompt 中 `specforge` 字符串同步换为 `quanti-forge`
- v0.6-003-quanti-forge-web：`/agents` 配置页同步新 agent 名 + tier 字段
- v0.6-004-cron-llm-wiki：cron 默认用 `-ie` 配对的 lite 模型（节约 token）

## v0.6-008-louke-v030-usability-closure

# v0.6-008 — louke v0.3.0 可用性收口（usability closure）— Spec
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#v06-008--louke-v030-usability-closure-spec]
- **Spec ID**: v0.6-008-louke-v030-usability-closure
- **创建日期**: 2026-06-30
- **状态**: 草稿（GLM 仓库审计 + 我的差异对照已收敛；待 GLM 实施）
- **关联**:
- 释放的 draft 编号：v0.6-006-louke-init-and-board-commands、v0.6-007-stub-implementation（合并到本 spec）
- 既有 spec：v0.3-003-init-adopt-mode、v0.5-005-namespace-cleanup、v0.5-007-multi-ide-boards、v0.5-008-test-quality-standards
- 审计来源：`/tmp/louke-missing-spec.md`（GLM 仓库评估，345 行，§0–§18）
- 关联 issue：#76（Maestro 入口）、#77（S/A/B 模型校准）
## 0. 范围与边界
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#0-]
**本 spec 收纳** 仓库审计出来的全部"v0.3.0 不可用"缺口，按主题分 9 节：
1. §1 项目初始化（init / adopt / issue-template / invite-owner / upgrade）
2. §2 IDE 板生成（board opencode / models alias / source frontmatter 校验）
3. §3 默认 agent（Maestro 为入口）
4. §4 Stub 命令真实实现（scout foundation / sage create-issues / sage lock-spec / librarian from-raw & write / resolve_spec_path）
5. §5 工具链收口（lk --version / package-data / glob 修复 / verify-acceptance 分支 / FR-schema 4 位升级 / ci-scan 参数 / 测试命令可配置 / keeper gate 全检 / shield scaffold --spec / 等）
6. §6 Maestro 流程闭环（10 阶段 holdpoint 自动调用 / state 更新 / M-SECURITY 跳过判定 / M-MILESTONE merge&tag / Lex Project 验证）
7. §7 项目信息模板与 Librarian（project-info.md 字段对齐 / raw 路径统一 / 入 git 策略 / Librarian 完整功能）
8. §8 README 与文档一致性
9. §9 非功能需求与测试矩阵
**本 spec 不收纳**：
- v0.6-005 命名重构（独立 spec 进行中）
- 模型档位 S/A/B/C 校准细节（issue #77 backlog）
- 既有 v0.5-008 测试质量标准的具体 lint 规则（保持独立演进）
## 1. 用户故事（按主题聚类）
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#1-]
### US-0100 项目奠基
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#us-0100-]
- US-0100: 作为 louke 新用户，我希望 `lk init my-proj` 一次铺好项目骨架（agents / templates / wiki / raw / issue template / OpenCode 板 / default_agent），以便开箱即用
- US-0110: 作为存量项目维护者，我希望 `lk init . --dry-run` 预览改动、`--backup` / `--force` 保护/覆盖我的定制、`--json` 给脚本消费，以便非破坏接入
- US-0120: 作为 Scout agent，我希望 `lk scout invite-owner <o/r> --version V` 把 repo owner 加入 Project READER，以便 M-FOUND Step 6 收尾
- US-0130: 作为 louke 用户，我希望 `pip install --upgrade louke` 是默认升级路径（CLI `lk upgrade` 作为便捷包装）
### US-0200 IDE 集成
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#us-0200-ide-]
- US-0200: 作为 OpenCode 用户，我希望装完 louke 后 `/agents` 列表看到全部 12 个 agent（每个带正确 `model:` 字段），以便 IDE 内驱动流水线
- US-0210: 作为 louke 用户，我希望 agent prompt 里写的抽象模型名（`kimi-k2.6` / `glm-5.2`）在 init 时自动绑定到本机 OpenCode 已配置的 `provider/model`，weak match 走交互，no match 给 bind 提示
- US-0220: 作为 louke 维护者，我希望 source agent frontmatter 与档位表一致（mode + models），board 工具可直接解析
### US-0300 入口
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#us-0300-]
- US-0300: 作为 OpenCode 用户，我希望 `lk init` 后新会话的入口 agent 默认是 Maestro，不需要每次手动 `<leader>a` 切换
### US-0400 Stub 命令真实化
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#us-0400-stub-]
- US-0400: 作为 Scout agent，我希望 `lk scout foundation --repo OWNER/REPO --version V --spec-id ID` 走完 8 步奠基（写 project-info / story / 调 identity / warden / commit），不要再被占位挡住
- US-0410: 作为 Sage agent，我希望 `lk sage create-issues --spec ID` 把 spec 里所有 `FR-XXXX` 转成 GitHub issue（去重 + Project 关联），不再手写 12 个 `gh issue create`
- US-0420: 作为 Sage agent，我希望 `lk sage record-lock --spec ID` 在三信号齐后记录 `locked: true`（结果记录器，不可替代三信号判定）
- US-0430: 作为 Librarian agent，我希望 `lk librarian from-raw` 把 `status=resolved` raw 实际蒸馏到 wiki pages（幂等）
- US-0440: 作为 Librarian agent，我希望 `lk librarian write <page>` 写入 wiki 页（防 path traversal，写后 rebuild-index）
- US-0450: 作为 agent，我希望在子目录跑 `lk sage quote-check --spec specs/X/spec.md` 时，若 git root 下能找到，自动用 git root 路径
### US-0500 工具链收口
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#us-0500-]
- US-0500: 作为安装者，我希望 `lk --version` 真实返回版本号（不再 `?`）
- US-0510: 作为维护者，我希望 pyproject 版本号与 louke/__init__.py 单源同步
- US-0520: 作为用户，我希望 `pip install louke` 后 `lk init` 能找到 issue template / workflows（package-data 完整）
- US-0530: 作为用户，我希望 `lk scout commit-foundation` 真的把 specs/{id}/*.md 加进去（glob 正确展开）
- US-0540: 作为 Lex agent，我希望 `lk lex verify-acceptance` 默认读当前 release 分支（不是 main）
- US-0550: 作为 agent，我希望 FR/AC 编号在 spec.md / acceptance.md / issue template / 校验工具里统一为 4 位
- US-0560: 作为多语言项目用户，我希望 `lk archer ci-scan` / `lk devon run-tests` / `lk keeper gate --tests` 不硬编码 pytest，能读项目配置
- US-0570: 作为 Devon agent，我希望 `lk devon commit-rgr --issue #N` 把 `Closes #N` 写进 commit，并能 push
- US-0580: 作为 Keeper agent，我希望 `lk keeper gate` 不只查 commit prefix，还验证 R-G-R 顺序、测试先于实现、lint / typecheck / AC trace / 反模式完整集合
- US-0590: 作为 Prism agent，我希望 `lk prism review --diff HEAD~1..HEAD` 正确解析 range（不把 range 当 ref）
- US-0600: 作为 Judge agent，我希望 `lk judge security-audit` 是两阶段：pattern scan + agent 语义审查，输出机器可读报告供 Maestro 判定
- US-0610: 作为 Shield agent，我希望 `lk shield scaffold --type playwright --spec ID --scenario X` 不崩（--spec 已注册）
### US-0700 Maestro 闭环
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#us-0700-maestro-]
- US-0700: 作为 Maestro agent，我希望 `lk maestro advance --stage M-TESTPLAN` / `M-ARCH` 等 10 个阶段各自自动调用对应 holdpoint（不再打印 `[todo]`）
- US-0710: 作为用户，我希望 advance 成功后 `project-info.md` 的 stage 字段被更新（不只打印）
- US-0720: 作为用户，我希望 M-SECURITY 根据 DoD 的 `Security Audit` 字段自动 skip 或调 judge
- US-0730: 作为用户，我希望 M-MILESTONE 检查 Librarian 输出 + release merge + tag
- US-0740: 作为 Lex agent，我希望 `lk lex verify-project`（或 `verify-issue` 阶段二增强）验证 issue 与 Project 的关联
### US-0800 项目信息 / Librarian
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#us-0800----librarian]
- US-0800: 作为用户，我希望 `templates/project-info.md` 字段与 Scout.md Step 6 一致（Version / Repo / Project / Project ID / Spec ID / Release Branch / Smoke Test Issue / DoD / Security Audit / Created）
- US-0810: 作为用户，我希望 raw 路径在所有 agent prompt 里统一为 `.louke/raw/{date}/{session-id}.md`（去掉 Librarian.md 的 `.louke/raw/sources/`）
- US-0820: 作为用户，我希望 raw / wiki 是否进 git 在 README 与 .gitignore 中明确定稿
- US-0830: 作为 Librarian agent，我希望 librarian 命令支持 frontmatter type/title/date 校验、broken link 检测、orphan page 检测、duplicate detect、incremental cache、overview/log 更新
### US-0900 文档
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#us-0900-]
- US-0900: 作为新用户，我希望 README 不再误述 `lk scout foundation`（实际是占位）、不再写 `{"plugin": ["louke"]}`（实际不存在）、不再用 3 位 FR 示例
## 2. 关键场景
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#2-]
### scenario-0100 空目录 init
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#scenario-0100--init]
```
$ mkdir my-proj && cd my-proj
$ lk init .
mkdir .louke/{agents,templates,project,wiki/pages,wiki/decisions,raw/sources}
cp 12 agents → .louke/agents/
cp 7 templates → .louke/templates/
write .gitignore (.louke/agents/, .louke/templates/；去重)
detect OpenCode → 跑 board opencode (生成 .opencode/agents/*.md)
models doctor --fix-auto → 写 ~/.louke/models.json 缓存
write <root>/opencode.json {"default_agent": "maestro"}
prompt: "写入全局 ~/.config/opencode/opencode.json? (Y/n)"
install .github/ISSUE_TEMPLATE/feature.yml (4 位 schema)
report: opencode ✓, default_agent: maestro (project), 12 agents
$ lk board status
opencode    ✓  (.opencode/agents/ — 12 agents, default model: ark/kimi-k2.6)
default_agent: maestro (project opencode.json)
```
### scenario-0110 既存项目 adopt
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#scenario-0110--adopt]
```
$ cd ~/work/my-existing-repo
$ lk init . --dry-run
[+] .louke/agents/{12}.md
[+] .louke/templates/{7}.md
[→] (none; 无旧 wiki/raw)
[+] .opencode/agents/{12}.md
[+] opencode.json (default_agent)
[+] .github/ISSUE_TEMPLATE/feature.yml
$ lk init .       # 实际执行
12 added, 0 skipped, 0 backed, 0 migrated
$ git status      # 看到一批 [+] 文件
```
### scenario-0200 抽象模型自动绑定
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#scenario-0200-]
```
$ lk init .
...
source model: kimi-k2.6
Found candidates from `opencode models`:
[1] ark/kimi-k2.6        (strong, user provider)
[2] opencode/kimi-k2.6   (strong, opencode subscription)
Choose [1]:
Wrote ~/.louke/models.json: kimi-k2.6 → ark/kimi-k2.6
✓ 全部 agent 已绑定
```
### scenario-0400 Scout foundation MVP
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#scenario-0400-scout-foundation-mvp]
```
$ lk scout foundation \
--repo zillionare/my-proj --version v0.6 --spec-id v0.6-008-closure \
--story '...' --dod 'unit ≥95% + e2e pass'
→ 写 .louke/project/project-info.md（12 字段）
→ 写 .louke/project/specs/v0.6-008-closure/story.md
→ 调 lk scout identity-check --repo zillionare/my-proj
→ 调 lk warden foundation-check --repo ... --version v0.6 --spec-id ...
→ 调 lk scout commit-foundation --spec-id ... --message 'story/prd: ...' --version v0.6
→ 输出 [项目奠基完成] 块
```
### scenario-0420 lock-spec 三信号
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#scenario-0420-lock-spec-]
```
# Sage: 1) quote-check 通过; 2) 用户在 IDE 内确认; 3) Lex 三阶段通过
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#sage-1-quote-check--2--ide--3-lex-]
$ lk sage record-lock --spec v0.6-008-closure
→ 校验 3 信号: quote_check_ok=True, lex_3stage_ok=True, user_confirmed=True
→ 全部 True → 写 frontmatter locked: true, commit+push
→ 任一 False → exit 1，列出缺失信号
```
### scenario-0700 Maestro advance
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#scenario-0700-maestro-advance]
```
$ lk maestro advance --stage M-TESTPLAN
→ check lk archer validate-test-plan --spec ...
→ check lk sage review --spec ...   (rule-based 默认, --use-llm 可选)
→ 全部 exit 0 → 更新 project-info.md current_stage: M-TESTPLAN
→ 输出 "[阶段: M-TESTPLAN] Archer + Sage 完成 → 通过"
```
---
## 3. 功能需求 — §1 项目初始化
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#3---1-]
> **元数据列**: 有效需求 ✅/❌ | 可测性 ✅/⚠️ {原因} | 是否已决定 ✅/⚠️/❌
---
<a id="fr-0100"></a>
### FR-0100 `lk init <bare-name>` 新建项目
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0100-lk-init-bare-name-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**实现要点**（继承 v0.3-003 FR-015 向后兼容 + v0.5-005 路径收归到 `.louke/`）：
1. 判定 `argv[0]` 是否既存路径：`.`、`./`、`../`、`/abs` 或 `~/...` 且 target 是已存在目录 → 走 FR-0101 adopt；**否则视为新项目名**。**例外**：`./newpath` 在既存仓库下仍视为新项目名（AC-FR0100-09）
2. `<name>/` 已存在且非空 → exit 1，stderr 含 `Directory '<name>' already exists`
3. `mkdir -p <name>/.louke/{agents,templates,project,wiki/pages,wiki/decisions,raw/sources}`
4. 从 `$LOUKE_HOME/agents/`（即 `importlib.util.find_spec('louke').origin` 的父目录）拷贝所有 `*.md` 到 `<name>/.louke/agents/`（当前含 12 个 agent prompt；不含 ROSTER.md —— 历史 commit `6cfc63d` 已将 ROSTER 合并到 Maestro.md）
5. 从 `$LOUKE_HOME/templates/` 拷贝所有 `*.md` 到 `<name>/.louke/templates/`
6. 写 `<name>/.gitignore`：文件不存在 → 新建含 `.louke/agents/\n.louke/templates/\n`；存在 → `grep -qxF` 去重，append（前补空行）
7. 调 FR-0110 (issue template 安装)
8. 调 FR-0200 / FR-0201 / FR-0300 (board / models / default_agent)
9. 打印 onboarding：路径、agents/templates 计数、wiki/raw 路径、IDE 板状态、default_agent 状态、下一步
**AC**
- AC-FR0100-01: `lk init my-proj` 后 `ls my-proj/.louke/` 含 `agents templates project wiki raw` 五项
- AC-FR0100-02: `ls my-proj/.louke/agents/*.md | wc -l` = 12（与 `$LOUKE_HOME/agents/*.md` 数量一致；不含 ROSTER.md —— 历史 commit `6cfc63d` 已将 ROSTER 合并到 Maestro.md）
- AC-FR0100-03: `ls my-proj/.louke/templates/*.md | wc -l` = 10（与 `$LOUKE_HOME/templates/*.md` 数量一致；当前含 acceptance / bug-fix / issues / prd / project-info / security-checklist / spec / task-log / task-plan / test-plan）
- AC-FR0100-04: `cat my-proj/.gitignore` 含 `.louke/agents/` 与 `.louke/templates/`
- AC-FR0100-05: 第二次跑 `lk init my-proj` → exit 1，stderr 含 `already exists`
- AC-FR0100-06: init 前在 `<name>/` 下手工放的 `README.md` 字节级不变
- AC-FR0100-07: init 后 `<name>/.github/ISSUE_TEMPLATE/feature.yml` 存在
- AC-FR0100-08: init 后 `<name>/.opencode/agents/*.md` 存在 12 个
- AC-FR0100-09: 在既存仓库跑 `lk init ./newpath` 视为新项目名（不走 adopt）
---
<a id="fr-0101"></a>
### FR-0101 `lk init <existing-path>` 既存项目 adopt
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0101-lk-init-existing-path--adopt]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**实现要点**：
1. 解析 target 为绝对路径；**要求是 git repo** → 否则 exit 2（区分于一般错误的 exit 1）
2. `cd $TARGET`
3. **旧路径迁移**（继承 v0.5-005 FR-030，路径改为 `.louke/`）：若存在 `wiki/` 且无 `.louke/wiki/` → `git mv`（若跟踪）/ `mv`（若未跟踪）；`raw/` 同理。**冲突**（新旧并存）→ exit 1，stderr 同时含新旧路径名
4. **create-if-missing**：对 `.louke/{agents,templates,project,wiki/pages,wiki/decisions,raw/sources}/` 七项，只 `mkdir -p` 缺失的
5. **文件冲突处理**（继承 v0.3-003 FR-011）：
- target 不存在 → cp 计入 `[+]` added
- 字节相同 → 静默 skip 计入 `[=]` skipped
- 不同 + `--force` → cp 计入 `[=]` overwritten
- 不同 + `--backup` → `cp $dest $dest.bak` 计入 `[!]` backed
- 不同 + 默认 → warn + skip 计入 `[=]` skipped
6. 调 FR-0200 / FR-0201 / FR-0300
7. 调 FR-0110
8. **`.gitignore` 追加**：`.louke/agents/` 与 `.louke/templates/` 两条，去重；`--no-gitignore` 跳过
9. **报告**：默认四档 `[+]/[=]/[!]/[→]`；`--json` 输出 `{added:[], skipped:[], backed_up:[], migrated:[]}`
**flags**: `--dry-run` / `--backup` / `--force` / `--no-gitignore` / `--no-migrate` / `--board=<opencode|none>` / `--with-issue-template` / `--no-issue-template` / `--no-default-agent` / `--json`
**exit code**: 0=成功（含 dry-run），1=一般错误，2=非 git repo
**AC**
- AC-FR0101-01: 存量项目（含 src/、tests/）跑 `lk init .` → 源码字节级不变 + 新建 `.louke/` 骨架 + 报告
- AC-FR0101-02: `lk init . --dry-run` 后 working tree 字节级不变 + 报告打印计划
- AC-FR0101-03: `lk init . --backup` 后每个被 skip 的 `*.md` 都有对应 `.bak`
- AC-FR0101-04: `lk init . --force` 后 `.louke/agents/*.md` 与 `$LOUKE_HOME/agents/*.md` 字节同步
- AC-FR0101-05: `lk init . --json` 输出合法 JSON，含 `added`/`skipped`/`backed_up`/`migrated` 四键
- AC-FR0101-06: 非 git repo → exit 2，stderr 含 `not a git repo`
- AC-FR0101-07: 旧路径 `wiki/` + 新路径 `.louke/wiki/` 都存在 → exit 1，stderr 同时含两者
- AC-FR0101-08: `lk init . --no-migrate` 不动旧路径，报告追加"未迁移"提示
- AC-FR0101-09: 既存仓库内 `lk init ./newpath` 视为新项目名（不走 adopt）
- AC-FR0101-10: `lk init . --no-gitignore` 后 `.gitignore` 字节级不变
- AC-FR0101-11: `lk init .` 二次跑（项目已 init 过）→ 全部 skipped，idempotent
---
<a id="fr-0110"></a>
### FR-0110 `.github/ISSUE_TEMPLATE/feature.yml` 安装（4 位 schema）
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0110-github-issue_template-featureyml-4--schema]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**实现要点**：
1. `lk init` 默认从 `$LOUKE_HOME/.github/ISSUE_TEMPLATE/feature.yml` 拷贝到 `<target>/.github/ISSUE_TEMPLATE/feature.yml`
2. **feature.yml 升级为 4 位 FR schema**（修复 GLM B1.6）：regex `^FR-\d{4}$`，placeholder `FR-0001`，spec_url fragment 同样改为 `fr-0001`
3. 冲突策略同 FR-0101 step 5
4. `--no-issue-template` flag 关闭；默认 on
**AC**
- AC-FR0110-01: init 后 `.github/ISSUE_TEMPLATE/feature.yml` 含 `fr_id`/`spec_url`/`acceptance_criteria` 三 id
- AC-FR0110-02: feature.yml 内 `regex: "^FR-\\d{4}$"`（不是 3 位）
- AC-FR0110-03: 用户定制过的 feature.yml 在第二次 init 不被默认覆盖
- AC-FR0110-04: `lk init . --no-issue-template` 后 `.github/ISSUE_TEMPLATE/` 不创建
---
<a id="fr-0120"></a>
### FR-0120 `lk scout invite-owner <owner/repo> --version V`
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0120-lk-scout-invite-owner-owner-repo---version-v]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**命名空间归属**：本命令归 Scout（**不是**顶层 `lk invite-owner`），与 Scout.md Step 6 "确保人类 owner 拥有 project 访问权" 直接对齐。
**实现要点**：
1. 校验 `--version V` 必填
2. 拿 `gh api user -q .login` 得 agent 身份
3. `gh project list --owner $GH_USER --format json` 找 title = `{repo-basename}-{version}` 的 project id
4. `gh api graphql` 查 repo owner userId（query: `user(login:"OWNER"){id}`）
5. GraphQL `updateProjectV2Collaborators` mutation 把 owner 加入为 READER
6. 任一失败（gh 未认证 / project 不存在 / GraphQL 403 / owner 已是 collaborator）→ exit 1，**actionable stderr**
**flag**: `--dry-run` 打印会做什么不实际调 mutation
**`lk init` 行为**：**不**自动调 invite-owner（避免 init 阶段强制 gh auth）
**AC**
- AC-FR0120-01: 缺 `--version` → exit 1，stderr 含 `--version`
- AC-FR0120-02: `gh` 未认证 → exit 1，stderr 含 `gh 未认证`
- AC-FR0120-03: project 未在 agent 名下找到 → exit 1，stderr 含 project title + 创建命令提示
- AC-FR0120-04: GraphQL mutation 失败 → exit 1，stderr 含 GraphQL 错误响应
- AC-FR0120-05: 成功 → stdout 含 `${OWNER} 已加入 project '${TITLE}' 为 READER`
- AC-FR0120-06: `--dry-run` 不实际调 mutation 但打印所有将执行的命令
---
<a id="fr-0130"></a>
### FR-0130 `lk upgrade` — pip 包装（P1）
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0130-lk-upgrade--pip-p1]
| 有效需求 | 可测性 | 是否已决定                  |
| -------- | ------ | --------------------------- |
| ✅        | ✅      | ⚠️ GLM 提议 P1，本 spec 接受 |
**优先级**：P1（在 §1 完成 + §5 B1.1/B1.2 落地后再实现）。PyPI 包模型下，`pip install --upgrade louke` 是 native 路径，CLI 仅作便捷。
**实现要点**：
1. 解析 louke 安装位置：从 `sys.argv[0]` 软链追溯到 venv 内 `lk` → `dirname` 得 venv 路径
2. 在该 venv 内 `subprocess` 调 `pip install --upgrade louke`
3. 退出码透传
4. flag：`--dry-run`（只打印将执行的 pip 命令）、`--pre`（允许预发布）、`--reinstall`（等价 `--upgrade --force-reinstall`）
**AC**
- AC-FR0130-01: `lk upgrade --dry-run` stdout 含 `pip install --upgrade louke` 字样，不实际执行
- AC-FR0130-02: 非 dry-run 跑完后 `lk --version` 输出新版本号
- AC-FR0130-03: pip 失败（无网络 / PyPI 403）→ 透传 exit code，stderr 含 pip 错误
---
## 4. 功能需求 — §2 IDE 集成
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#4---2-ide-]
---
<a id="fr-0200"></a>
### FR-0200 `lk board <opencode|status>` OpenCode 板生成
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0200-lk-board-opencodestatus-opencode-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
> ⚠️ **SUPERSEDED by v0.6-009 FR-0060.2** (2026-07-03): 本 FR 隐含的"`/agents` 列表看到全部 12 个 agent"行为在 v0.6-009 之后被修订 —— TUI 顶层 `<Leader>a` 列表**只**显示 Maestro (mode: primary), 其余 11 个 agent 改 `mode: subagent`, 只能通过 Maestro 的 `task` 工具调用。详见 v0.6-009 spec §0.2 受影响下游段落。
**立场**：README 已声明 "OpenCode only (currently)"；**不再实现** `lk board vscode`（与 v0.5-007 NFR-010 历史兼容放 P1，未来按需开新 FR）。`lk board vscode` 调用应 exit 1。
**实现要点**：
1. **frontmatter 解析器**：复用 `tools/specforge_board.py:90-110` 已实现的 YAML-like 解析（不支持完整 YAML，但 `key: value` 与 `key:\n  - item` 形式够用）
2. **`lk board opencode`**：
- 源目录优先 `.louke/agents/`，fallback `agents/`（specforge 自身仓 dev 模式）
- 跳过 `README.md`、`ROSTER.md`
- 对每个 agent：解析 frontmatter 取 `name`/`description`/`mode`/`models`
- 在 `.opencode/agents/{lowercase-name}.md` 生成：
```yaml
---
description: <copied>
mode: <copied or 'all'>
model: <models[0] 经 FR-0201 解析得到的 full name>
---
<body copied>
```
- **不**生成 `models:` 数组（OpenCode 原生不识别）
- `.gitignore` 追加 `.opencode/agents/`（去重）
3. **`lk board status`** 输出：
```
opencode    ✓  (.opencode/agents/ — 12 agents, default model: ark/kimi-k2.6)
default_agent: maestro (project opencode.json)
```
- 判定：目录存在 + ≥1 文件 + frontmatter 含 `model:`
- `default_agent:` 三态：(project opencode.json) / (global opencode.json) / (not set)
4. **`lk init` 自动探测**：`.opencode/` 或 `~/.config/opencode/opencode.json` 存在 → 跑 board opencode；都没有 → 不装
5. `--board=opencode` 强制装；`--board=none` 不装
6. **幂等**：重跑无副作用（覆盖源名单内的；用户手写的其它 `.opencode/agents/*.md` 不动）
**AC**
- AC-FR0200-01: init 后 `.opencode/agents/{12}.md` 存在，每文件 frontmatter 含 `model:`
- AC-FR0200-02: `.opencode/agents/scout.md` body sha256 = `.louke/agents/Scout.md` sha256
- AC-FR0200-03: `lk board opencode --dry-run` 后 working tree 不变
- AC-FR0200-04: `lk board status` exit 0，stdout 含 `✓/-` 与 `default_agent:` 行
- AC-FR0200-05: init 后 `.gitignore` 含 `.opencode/agents/`（如装了 opencode 板）
- AC-FR0200-06: `lk board vscode` → exit 1，stderr 含 `not supported`
- AC-FR0200-07: `lk board unknown-ide` → exit 1
- AC-FR0200-08: init 自动探测 `~/.config/opencode/opencode.json` → 装 opencode 板
- AC-FR0200-09: init `--board=none` 跳过自动探测
---
<a id="fr-0201"></a>
### FR-0201 `lk models {list,doctor,bind,unbind}` 抽象模型解析
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0201-lk-models-listdoctorbindunbind-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**实现要点**：
1. **配置 schema URL 修正**（修复 GLM B1.7 + 我的 A2）：从历史 `specforge://models-alias` 改为 `louke://models-config`（统一 louke 命名）
2. **schema 形态**：
```json
{
"$schema": "louke://models-config",
"version": 1,
"aliases": { "kimi-k2.6": "ark/kimi-k2.6" }
}
```
3. **三层优先级**（继承 v0.5-007 FR-080）：
1. 项目级 `<root>/.louke/models.json`
2. 用户级 `~/.louke/models.json`
3. `opencode models 2>/dev/null` 自动发现
4. **强匹配算法**：`normalize = re.sub(r'[^a-z0-9]+', '', value.lower())`；抽象名与 model-id 末段完全相等 → strong match
5. **多 strong match 优先级**：非 `opencode/` 前缀 provider 优先；`opencode/` 次之；并列取字典序最小 + warning
6. **弱匹配**（包含关系）：tty 走编号选择；非 tty fail
7. **子命令**：
- `lk models list` — 列出 source 全部抽象名 + 解析结果（`{alias}\t{resolved}`）
- `lk models doctor [--fix-auto] [--ide=<ide>]` — 跑自动发现；`--fix-auto` 把 strong match 写 `~/.louke/models.json`
- `lk models bind <abstract> <full> [--project]` — 写用户级 / 项目级 alias
- `lk models unbind <abstract> [--project]` — 删对应键
8. **`opencode models` 缺失**：退化只查 1+2；无命中 → exit 1 提示 `opencode models` 不可用
9. **环境变量 override**：`LOUKE_MODELS_CONFIG` / `LOUKE_PROJECT_MODELS_CONFIG`（与 v0.5-007 一致）
10. **`lk init` 集成**：board 生成前自动 `lk models doctor --ide=opencode --fix-auto`；仅 weak/no match 时进交互
**AC**
- AC-FR0201-01: `lk models list` 输出含 source 全部抽象名，第二列是解析后全名或 `-`
- AC-FR0201-02: `opencode models` 输出含 `ark/kimi-k2.6` → doctor 打印 ✓ `ark/kimi-k2.6`
- AC-FR0201-03: 多个 strong match 时，非 `opencode/` provider 优先
- AC-FR0201-04: `lk models bind foo bar/foo` → `~/.louke/models.json` 含 `"foo": "bar/foo"`
- AC-FR0201-05: `lk models bind foo bar/foo --project` → `<root>/.louke/models.json` 含；项目级优先于用户级
- AC-FR0201-06: `lk models unbind foo` 删用户级键（不动项目级）
- AC-FR0201-07: `opencode models` 不存在 + alias map 未配 → doctor exit 1，stderr 含 `opencode models`
- AC-FR0201-08: 弱匹配 tty 下进交互；非 tty exit 1 提示 `lk models bind`
- AC-FR0201-09: `--fix-auto` 把 strong match 写 `~/.louke/models.json`
- AC-FR0201-10: 配置 schema `$schema` = `louke://models-config`（不再是 `specforge://`）
---
<a id="fr-0210"></a>
### FR-0210 source agent frontmatter 校验（不是新增）
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0210-source-agent-frontmatter-]
| 有效需求 | 可测性 | 是否已决定 |
| --- | --- | --- |
| ✅ | ✅ | ✅ |
**事实修正**（修复我的 A1）：当前 12 个 `louke/agents/*.md` **已**含 `mode: all` + `models:` frontmatter。本 FR 是**校验 + 规范化**，不是新增。
**开源模型政策**（Aaron 2026-06-30 拍板）：
**只使用 8 个开源模型**，按 3 档分配：
| 档 | 模型 | 说明 |
| --- | --- | --- |
| **S**（强） | `glm-5.2`, `minimax-m3` | 高质量、强推理 |
| **A**（中） | `kimi-2.6`, `kimi-2.7`, `deepseek-v4-pro` | 性价比主力 |
| **B**（轻） | `deepseek-v4-flash`, `glm-5` | 简单任务、低成本 |
**档位 → agent 映射**（v0.6-008 落地，**按任务复杂度分级**）：
| 档 | agent | primary | fallback | 任务复杂度 |
| --- | --- | --- | --- | --- |
| S | Maestro | `minimax-m3` | `glm-5.2` | 长程协调、状态跟踪 |
| S | Sage | `glm-5.2` | `minimax-m3` | Socratic 对话、需求澄清 |
| S | Judge | `minimax-m3` | `glm-5.2` | S 级深度安全审计 |
| S | Archer | `glm-5.2` | `minimax-m3` | 架构设计 |
| A | Devon | `kimi-2.7-code` | `deepseek-v4-pro` | R-G-R 编码 |
| A | Prism | `deepseek-v4-pro` | `kimi-2.6` | 代码评审（反模式 + 安全快扫） |
| A | Shield | `kimi-2.6` | `kimi-2.7-code` | e2e 模板编写 |
| B | Lex | `deepseek-v4-flash` | `glm-5` | 工具调用 + 结构校验 |
| B | Warden | `glm-5` | `minimax-2.7` | gate 检查 |
| B | Keeper | `minimax-2.7` | `deepseek-v4-flash` | commit 门禁 |
| B | Scout | `glm-5` | `minimax-2.7` | 交互式引导 |
| B | Librarian | `minimax-2.7` | `glm-5` | wiki 维护 |
**历史**：v0.5-007 写过 S/A/B/C 四档 tier 表（含 `gpt-5.4-mini` 等闭源模型），Aaron 2026-06-27（commit `655b215`）把 Scout 从 `glm-5.2` 改成 `gpt-5.4-mini` 时**没同步更新 spec**——说明 tier 表从一开始就不是 source of truth。2026-06-30 拍板：**只使用开源模型，移除 `gpt-5.4-mini`**，按 S/A/B 三档重排。
**实现要点**：
1. **lint 工具**（`tools/check_agent_frontmatter.py`，或 `lk archer lint-frontmatter`）：扫描 `louke/agents/*.md` + `.louke/agents/*.md`
2. **必查**（结构性）：
- `mode` ∈ {`primary`, `subagent`, `all`}
- `models` 至少 1 个元素（primary 必填）
- `name` 非空
- `description` 非空
- **`models` 元素必须 ∈ 8 模型白名单**（S/A/B 三个列表的并集）—— 闭源模型或未列入的抽象名直接 fail
3. **档位断言**（不强制，留 hint）：
- lint 报告可**展示**每个 agent 的档位（按"主 primary 落在哪个档"判断），但不阻断
- rationale 已落到 issue #77，未来调整档位表时改 spec FR-0210 与本表一致
4. **白名单变更流程**：未来加入/移除模型，需同时改：(a) spec FR-0210 表格、(b) 12 个 agent frontmatter（如果用到）、(c) `lk models list` 解析逻辑、(d) 文档
**AC**
- AC-FR0210-01: 当前 12 个 agent 全部通过 `lk archer lint-frontmatter` exit 0
- AC-FR0210-02: 把 Maestro 的 `mode` 改成 `xxx`（非法）→ lint exit 1，stderr 含 `mode`
- AC-FR0210-03: 缺 `models` 字段 → lint exit 1，stderr 含 `models`
- AC-FR0210-04: `models: []`（空数组）→ lint exit 1，stderr 含 `non-empty`
- AC-FR0210-05: 把任意 agent 的 primary 改成 `gpt-5`（闭源，不在白名单）→ lint exit 1，stderr 含 `whitelist` 与 `gpt-5`
- AC-FR0210-06: 把任意 agent 的 primary 改成 `kimi-2.6`（在白名单）→ lint exit 0
- AC-FR0210-07: lint 报告展示每个 agent 的当前 primary（如 `Maestro: glm-5.2`）
3. `lk agent lint`（或 `lk archer lint-frontmatter`）执行校验，exit 0/1
4. **不**自动改 frontmatter（agent prompt 改动需人审）
**AC**
- AC-FR0210-01: 当前 12 个 agent 全部通过 lint（无回归）
- AC-FR0210-02: 把 Maestro 的 `models[0]` 改成 `glm-5.2` → lint exit 1，stderr 列出冲突
- AC-FR0210-03: 缺 `mode` 字段 → lint exit 1
- AC-FR0210-04: `models` 为空数组 → lint exit 1
---
## 5. 功能需求 — §3 默认 agent
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#5---3--agent]
---
<a id="fr-0300"></a>
### FR-0300 `lk init` 写 default_agent: maestro
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0300-lk-init--default_agent-maestro]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**实现要点**：
1. **项目级** `<root>/opencode.json`：
- 不存在 → 新建 `{"default_agent": "maestro"}`
- 存在 + 无 `default_agent` 键 → 写入
- 存在 + `default_agent = "maestro"` → skip
- 存在 + `default_agent` 是其他值 → **默认拒绝并 warning**；`--force-default-agent` 覆盖；`--no-default-agent` 跳过
2. **全局 prompt**：tty 下询问 "是否同时把 default_agent 写入全局 ~/.config/opencode/opencode.json？(Y/n)"；Y 则同样规则写入
3. `--global-default-agent` 跳过 prompt 直接写；`--no-global-default-agent` 不写全局
4. **`lk board status` 集成**：输出 `default_agent: maestro (set in project opencode.json)` 或 `(set in global)` 或 `(not set)`
**AC**
- AC-FR0300-01: init 后 `<root>/opencode.json` 含 `"default_agent": "maestro"`
- AC-FR0300-02: 项目 `opencode.json` 已存在且 `default_agent = "build"` → 默认 exit 1 警告；`--force-default-agent` 覆盖
- AC-FR0300-03: tty 下回答 Y 后 `~/.config/opencode/opencode.json` 也含 `default_agent: maestro`
- AC-FR0300-04: `lk init . --no-default-agent` → 两个 `opencode.json` 都不被改
- AC-FR0300-05: `lk board status` 输出含 `default_agent:` 行
- AC-FR0300-06: `--force-default-agent` 非交互（CI 用），直接覆盖
---
## 6. 功能需求 — §4 Stub 命令真实实现
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#6---4-stub-]
---
<a id="fr-0400"></a>
### FR-0400 `lk scout foundation` MVP（明确分两阶段）
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0400-lk-scout-foundation-mvp]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**两阶段声明**（修复我的 A6 + 采纳 GLM §18.2 第 6 条）：
- **MVP（本 FR）**：写 `project-info.md` 与 `story.md`，调 `lk scout identity-check` / `lk warden foundation-check` / `lk scout commit-foundation`。**不**创建 GitHub repo / Project / Smoke Issue / Smoke PR / invite-owner。
- **完整 P0**（后续 FR-0401）：M-FOUND Step 2–5 全流程。
**MVP 实现要点**：
1. 校验 `--repo` / `--version` / `--spec-id` 必填
2. `--story <text>` / `--story-file <path>` / stdin 选填；缺则从 spec-id 推断路径
3. `--dod <text>` 选填；缺则用默认 `e2e 全通过 + 单元测试覆盖率 ≥95% + 安全审查 (M-SECURITY)`
4. 写 `<root>/.louke/project/project-info.md`（FR-0800 字段对齐）
5. 写 `<root>/.louke/project/specs/{spec-id}/story.md`
6. `subprocess` 调 `lk scout identity-check --repo {repo}`
7. `subprocess` 调 `lk warden foundation-check --repo {repo} --version {version} --spec-id {spec-id}`
8. step 7 exit 0 → `subprocess` 调 `lk scout commit-foundation --spec-id {spec-id} --message 'story/prd: initial draft for {spec-id}' --version {version}`
9. 输出 Scout.md 标准报告块
**flag**: `--no-commit` 跳过 step 8；`--dry-run` 打印计划不实际写
**AC**
- AC-FR0400-01: 缺任一必填 flag → argparse 错误（exit 2）
- AC-FR0400-02: 跑完后 `<root>/.louke/project/project-info.md` 含 FR-0800 全部 12 字段
- AC-FR0400-03: 跑完后 `<root>/.louke/project/specs/{spec-id}/story.md` 存在且非空
- AC-FR0400-04: `lk scout identity-check` 失败 → exit 1，stderr 含 `identity`
- AC-FR0400-05: `lk warden foundation-check` 失败 → exit 1，stderr 含 `foundation-check`
- AC-FR0400-06: 全部通过 + `--no-commit` → 不调 commit-foundation
- AC-FR0400-07: `--dry-run` 不写任何文件、不调任何子命令
- AC-FR0400-08: 已 init 项目重跑 → 幂等（不覆盖已写文件除非 `--force`）
---
<a id="fr-0401"></a>
### FR-0401 `lk scout foundation` 完整 P0（创建 repo / Project / Smoke）
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0401-lk-scout-foundation--p0-repo---project---smoke]
| 有效需求 | 可测性       | 是否已决定 |
| -------- | ------------ | ---------- |
| ✅        | ⚠️ 需 gh auth | ⚠️          |
**承接 FR-0400 MVP**。完整实现 Scout.md Step 2–5：
1. 创建 GitHub repo（如不存在）：`gh repo create {repo} --{public|private} --description ...`
2. 创建 `releases/{version}` 分支（基于 main）
3. 创建 GitHub Project `{repo}-{version}`：`gh project create --owner {GH_USER} --title ...`
4. 写 Project README
5. 调 FR-0120 `lk scout invite-owner`
6. Smoke Issue 创建 + 立即 close
7. Smoke PR 创建 + 立即 close
8. 调 FR-0400 MVP 后续步骤
**测试策略**：用 `gh` mock 跑测试（GLM §15 推荐）；真实 gh 调用只在 manual smoke test。
**AC**
- AC-FR0401-01: repo 已存在 → 跳过创建，stderr 含 `already exists`
- AC-FR0401-02: Project 已存在 → 跳过创建，复用
- AC-FR0401-03: invite-owner 失败 → 整体 exit 1，提示用户手动添加
- AC-FR0401-04: Smoke PR 创建后 `gh pr close` 立即关闭，PR 编号记入 project-info.md
---
<a id="fr-0402"></a>
### FR-0402 `lk scout foundation` 创建/确保 per-repo backlog project
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0402-lk-scout-foundation---per-repo-backlog-project]
| 有效需求 | 可测性 | 是否已决定 |
| --- | --- | --- |
| ✅ | ⚠️ 需 gh | ✅ |
**目标**：每次 `lk scout foundation`（FR-0401 完整 P0 Step 3 创建 `{repo}-{version}` Project 后）追加一步：确保 `{repo}-backlog` Project 存在（per-repo，**永久**，区别于 per-release 的 `{repo}-{version}`）。
**用途**：放"想到但未排期"的用户故事 / feature idea / 内部待办。`gh issue create --no-milestone` 创建的 issue 自然归入 backlog；planning 时把 backlog issue 拉进 `{repo}-{version}`。
> **注意**：本节是 louke 框架实现细节，仅在 spec 内部区分。**面向终端用户的 README 只描述 `{repo}-backlog` 一个概念**，不提及 louke 维护者自己的内部 backlog。
**实现要点**：
1. **dedup 规则**（你强调的"不要重复创建"）：
- 查询 `gh project list --owner {owner} --format json`
- 过滤 title 严格等于 `{repo}-backlog`（大小写敏感）
- 找到 → 跳过，stdout `{repo}-backlog reused (id: {PROJECT_ID})`
- 没找到 → 调 `gh project create --owner {owner} --title {repo}-backlog --description 'Backlog for {repo}: unscheduled user stories and feature ideas'`，记录 id 到 project-info.md
2. **owner 选择**：与 `{repo}-{version}` Project 一致（FR-0401 Step 3 用的 owner；若 agent 是 collaborator 模式仍可能失败，由 FR-0120 invite-owner 兜底）
3. **写入 project-info.md**：模板（FR-0800）增加字段 `Backlog Project: {repo}-backlog (#{PROJECT_ID})`
4. **fail 软策略**（采纳 NFR-0200 actionable）：backlog 创建失败不阻断 foundation（避免 1 个 gh API 失败让整个 init 卡住），warning to stderr 含 retry 命令
**AC**
- AC-FR0402-01: 首次 `lk scout foundation` → 实际调 `gh project create` 创建 `{repo}-backlog`，project-info.md 含 `Backlog Project:` 字段
- AC-FR0402-02: 二次 `lk scout foundation`（mock `gh project list` 返回已存在的 `{repo}-backlog`）→ 跳过创建，stdout 含 `reused`
- AC-FR0402-03: title 匹配严格（`{repo}-backlog-extra` 不算重复）
- AC-FR0402-04: backlog 创建失败（如 owner 无权限）→ warning 不阻断 foundation，stderr 含 `{repo}-backlog` 与 retry 提示
- AC-FR0402-05: owner 选择与 `{repo}-{version}` Project 一致（同一字段 `Project ID` 解析得到）
- AC-FR0402-06: `--dry-run` 不实际调 `gh project create`，stdout 打印将创建的 title
---
<a id="fr-0410"></a>
### FR-0410 `lk sage create-issues` 真实实现
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0410-lk-sage-create-issues-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**实现要点**：
1. 校验 `--spec` 必填（或 `--spec-file` 走 FR-0240 路径回落）
2. 读 `spec.md`，用 `re.findall(r'<a\s+id="fr-(\d{4})"></a>', text)` 提取所有 FR 编号
3. 对每个 FR：
- 提取标题（FR 标题行第一个非空）
- 决定 AC value（FR-0700 三选一：`acceptance.md#ac-fr-XXXX` 优先 / spec.md 锚 `无` / `无`）
4. body 模板：
```
### 需求 ID
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#-id]
FR-XXXX
### Spec 链接
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#spec-]
{REPO_URL}/blob/{BRANCH}/.louke/project/specs/{spec-id}/spec.md#fr-XXXX
### 验收标准
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#]
{AC_VALUE}
```
- **`{BRANCH}` 解析**（修复我的 A5）：取自 `<root>/.louke/project/project-info.md` 的 `Release Branch` 字段（如 `releases/v0.6`）；缺失则 fail 提示用户先跑 `lk scout foundation`
5. 去重：`gh issue list --repo {REPO} --search 'in:title [FR-XXXX]' --json number,title` 查到 → skip（计入 `[=]`）
6. `gh issue create --repo {REPO} --title '[FR-XXXX] {title}' --label Feature --body-file /tmp/issue-body.md`
7. **Project 关联**（采纳 GLM §18.2 第 8 条）：
- 默认行为：若 `project-info.md` 缺 Project URL → **exit 非零**（默认 mode 应阻塞，符合 Lex 阶段二必验要求）
- `--skip-project` flag：warning + 继续创建 issue（不关联 Project）
- 有 Project URL：`gh project item-add {PROJECT_URL} --url {ISSUE_URL}`
8. 输出：`Created: [FR-0001] #N ... / Skipped: [FR-0002] #M (exists) / Project: linked / Skipped-project: --skip-project`
**AC**
- AC-FR0410-01: spec.md 含 0 个 FR 锚点 → exit 0，stdout `0 created, 0 skipped`
- AC-FR0410-02: spec.md 含 3 个 FR；2 个已存在 → 1 created, 2 skipped
- AC-FR0410-03: `gh` 未认证 → exit 1，stderr 含 `gh 未认证`
- AC-FR0410-04: project-info.md 缺 Project URL + 默认模式 → exit 1
- AC-FR0410-05: project-info.md 缺 Project URL + `--skip-project` → warning + 继续创建
- AC-FR0410-06: `--dry-run` 不实际调 `gh`
- AC-FR0410-07: 缺 `Release Branch` 字段 → exit 1 提示跑 scout foundation
- AC-FR0410-08: body 模板 Spec 链接的 branch = project-info.md 的 `Release Branch`
---
<a id="fr-0420"></a>
### FR-0420 `lk sage record-lock` 结果记录器（三信号判定）
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0420-lk-sage-record-lock-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**重要语义澄清**（修复我的 A4 + 采纳 GLM §18.2 第 7 条）：
- `lk sage record-lock` **不是**锁定信号本身，而是**三信号齐之后的结果记录器**
- 三信号：
1. **Sage 信号**: `lk sage quote-check --spec {id} --check-ready` exit 0
2. **Lex 信号**: `lk lex verify-acceptance` + `lk lex verify-issue` + `lk lex verify-project` 三阶段全通过
3. **用户信号**: 人类在 IDE 内显式确认（Maestro 流程记录）
- `locked: true` 是**结果**，不可替代信号
**实现要点**：
1. 校验 `--spec` 必填；可选 `--confirm` flag 表示用户已显式确认
2. **三信号校验**：
- step 1: 跑 `lk sage quote-check --spec {id} --check-ready`；非零 → exit 1，stderr `Sage signal: 未通过 (quote 块未 resolved)`
- step 2: 跑 `lk lex verify-acceptance --spec {id}` + `lk lex verify-issue --spec {id}` + `lk lex verify-project --spec {id}`；任一非零 → exit 1，stderr 列出失败
- step 3: 缺 `--confirm` → exit 1，stderr `User signal: 缺 --confirm flag 或 IDE 内显式确认`
3. 三信号齐 → spec.md frontmatter 合并 `locked: true` + `locked-at: {ISO timestamp}` + `locked-by: lk sage record-lock`
4. `lk sage commit-spec --spec {id} --message 'spec: lock {spec-id}'`
**AC**
- AC-FR0420-01: 跑完三信号齐 → spec.md 含 `locked: true`
- AC-FR0420-02: quote-check 失败 → spec.md 不被修改，exit 1 提示 `Sage signal`
- AC-FR0420-03: 任一 Lex 阶段失败 → exit 1 列出失败阶段
- AC-FR0420-04: 缺 `--confirm` → exit 1 提示 `User signal`
- AC-FR0420-05: 已 lock 的 spec 再 record-lock → idempotent，exit 0 不报错
- AC-FR0420-06: 缺 `--spec` → argparse 错误
---
<a id="fr-0430"></a>
### FR-0430 `lk librarian from-raw` 真实蒸馏
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0430-lk-librarian-from-raw-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**实现要点**：
1. 扫描 `<root>/.louke/raw/{yy-mm-dd}/{session-id}.md`（FR-0810 统一路径）
2. 过滤 `status: resolved` 且 `superseded-by` 为空（或指向更新条目）
3. 对每条：生成 wiki 页 `<root>/.louke/wiki/pages/{yy-mm-dd}-{slug}.md`
4. frontmatter：
```yaml
---
date: 2026-06-30
title: <frontmatter title 或 "Session: {session-id}">
type: experience   # 默认；decision / entity 由 raw frontmatter 显式标注
session: {session-id}
raw_ref: ../raw/{yy-mm-dd}/{session-id}.md
agents: [...]
tags: [...]
---
```
5. body 拷贝 raw 中 `## 议题 / ## 决定 / ## 试过但放弃 / ## 开放问题` 四段
6. 写完后更新 raw frontmatter 加 `distilled-to: pages/{path}`
7. 同步刷新 `<root>/.louke/wiki/index.md`（FR-0830 lint）
**AC**
- AC-FR0430-01: 无 raw entries → exit 0，stdout `Distilled 0 entries`
- AC-FR0430-02: 1 resolved + 1 open → `Distilled 1 entries`，wiki 页生成
- AC-FR0430-03: wiki 页 frontmatter 含 `date`/`title`/`type: experience`/`session`/`raw_ref`
- AC-FR0430-04: 跑两次幂等：raw 含 `distilled-to` → 跳过
- AC-FR0430-05: `--since 2026-06-25` 只处理 6-25 之后（含）的 raw
- AC-FR0430-06: 蒸馏完成后 `wiki/index.md` 含新页
---
<a id="fr-0440"></a>
### FR-0440 `lk librarian write <page-relpath>` 含 path traversal 防护
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0440-lk-librarian-write-page-relpath--path-traversal-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**实现要点**（采纳 GLM §17.2 第 6 条 path traversal 防护）：
1. 校验 `<page-relpath>` 必须以 `pages/` 起；不含 `..` 段；解析后路径必须在 `<root>/.louke/wiki/` 内 → 否则 exit 1 提示 `path traversal rejected`
2. flag: `--type experience|decision|entity`（必填）；`--title T`；`--date YYYY-MM-DD`（默认今天）；body 来自 stdin 或 `--content-file <path>`
3. 写 `<root>/.louke/wiki/{page-relpath}.md`，自动生成 frontmatter（`date`/`title`/`type`/`slug`）
4. 写完调 `lk librarian rebuild-index --wiki .louke/wiki`（FR-0830）
**AC**
- AC-FR0440-01: 写入后文件存在，frontmatter 含 `type`/`title`/`date`
- AC-FR0440-02: `index.md` 含新页链接
- AC-FR0440-03: `--type xxx` 非法值 → argparse 错误
- AC-FR0440-04: `page-relpath = ../../etc/passwd` → exit 1，stderr 含 `path traversal`
- AC-FR0440-05: `page-relpath = agents/Maestro.md`（不在 pages/ 下）→ exit 1
- AC-FR0440-06: 写入失败（缺 type）→ exit 1
---
<a id="fr-0450"></a>
### FR-0450 `lk sage/lex quote-check` + `lk lex verify-acceptance` 加 resolve_spec_path
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0450-lk-sage-lex-quote-check--lk-lex-verify-acceptance--resolve_spec_path]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**实现要点**（修复 GLM §17.2 第 5 条 + 我的 v0.6-007 FR-0240/0250）：
1. 路径解析顺序：
- 绝对路径且存在 → 用
- 相对路径在 cwd 存在 → 用
- 否则 `git rev-parse --show-toplevel` 找 git root，拼 `<root>/<arg>` → 存在则用
- 都不存在 → 透传给下层工具，让其报错（stderr 包含原始 path + git root 作调试信息）
2. **应用到**：
- `lk sage quote-check --spec <path>` — `--spec` 参数走 resolve
- `lk lex quote-check --spec <path>` — 同样
- `lk lex verify-acceptance --spec-file <p> --acceptance-file <p>` — 两个路径都走 resolve
**AC**
- AC-FR0450-01: cwd 在 git root 子目录，`--spec specs/X/spec.md` 实际位于 git root → 找到并成功 check
- AC-FR0450-02: 路径 git root 也不存在 → exit ≠ 0，stderr 含原始 path + `git root: <root>`
- AC-FR0450-03: 不是 git repo → 跳过 git root 回落，直接走原路径
- AC-FR0450-04: `lk lex verify-acceptance` 的 `--spec-file` + `--acceptance-file` 同 AC-FR0450-01/02/03
---
## 7. 功能需求 — §5 工具链收口
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#7---5-]
---
<a id="fr-0500"></a>
### FR-0500 `lk --version` + 版本号单源同步
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0500-lk---version--]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM B1.1 / B1.2**：
- 当前 `lk --version` → argparse 错误（`<agent>` 必填）；`install.sh:121` 拿到 `?`
- `pyproject.toml` = `0.3.0`，但 `louke/__init__.py:__version__ = "0.1.0"`（不一致）
**实现要点**（采纳 GLM §18 标注，**不分两步**；当前 release 手动对齐即可）：
1. `__main__.py` 顶层加：
```python
if len(sys.argv) == 2 and sys.argv[1] in ("--version", "-v", "version"):
from . import __version__
print(f"lk {__version__}")
return 0
```
2. **手动对齐**：版本号写在 `pyproject.toml`（source of truth）；`louke/__init__.py:__version__` 由 release 流程手动同步
3. CI 加一个 `tests/test_version_sync.bats`：跑 `tomllib.load(open('pyproject.toml','rb'))['project']['version']` 与 `louke/__init__.__version__` 比较，**不一致 exit 1**（防止发版后忘了同步）
4. 删除 `install.sh:121` 的 `lk --version` workaround
**未来优化（不在本 FR 范围）**：构建时自动 sync（如 hatch hook / setuptools custom command）需要单独 spec；当前 setuptools + Makefile 体系下不强加，避免引入构建系统变化。
**AC**
- AC-FR0500-01: `lk --version` 输出形如 `lk 0.3.0`
- AC-FR0500-02: `lk -v` 同上
- AC-FR0500-03: `louke/__init__.py:__version__` 与 `pyproject.toml:version` 同步（CI 测试守门）
- AC-FR0500-04: `tests/test_version_sync.bats` 验证两处一致
---
<a id="fr-0510"></a>
### FR-0510 `pyproject.toml` package-data 扩充
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0510-pyprojecttoml-package-data-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM B1.3**：当前 package-data 只有 `["py.typed", "agents/*.md", "templates/*.md"]`，缺 `.github/ISSUE_TEMPLATE/` 与 `.github/workflows/`。
**实现要点**（采纳 GLM §18 标注——setuptools package-data 只能可靠包含**包目录内**文件；当前 `.github/` 在仓库根，不在 `louke/` 包目录）：
1. **把资源移到包内**（新建 `louke/resources/`）：
```
louke/resources/
.github/ISSUE_TEMPLATE/feature.yml
.github/workflows/louke-ci.yml
.github/workflows/louke-release.yml
```
2. `pyproject.toml` 更新：
```toml
[tool.setuptools.package-data]
louke = [
"py.typed",
"agents/*.md",
"templates/*.md",
"resources/.github/ISSUE_TEMPLATE/*.yml",
"resources/.github/workflows/*.yml",
]
```
3. **运行时访问**：用 `importlib.resources.files('louke').joinpath('resources/.github/ISSUE_TEMPLATE/feature.yml')`（Python 3.9+ 标准库；不引入 `pkg_resources`）
4. **sdist**：补 `MANIFEST.in` 含 `recursive-include louke/resources *`
**AC**
- AC-FR0510-01: `pip install louke` 后 `importlib.resources.files('louke').joinpath('resources/.github/ISSUE_TEMPLATE/feature.yml').is_file()` = True
- AC-FR0510-02: 同上 `.github/workflows/louke-ci.yml` is_file() = True
- AC-FR0510-03: wheel (`dist/*.whl`) 用 `unzip -l` 看含 `louke/resources/.github/ISSUE_TEMPLATE/feature.yml` 路径
- AC-FR0510-04: sdist (`dist/*.tar.gz`) 用 `tar tzf` 看含同样路径
---
<a id="fr-0520"></a>
### FR-0520 项目级 `.github/workflows/louke-ci.yml` 自动安装
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0520--github-workflows-louke-ciyml-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §3 + §15**：仓库没有 `.github/workflows/louke-ci.yml`，`lk init` 也不装。
**实现要点**（采纳 GLM §18 标注——`SPEC_ID` 通过 sed 推断不稳定）：
1. 资源位置：`louke/resources/.github/workflows/louke-ci.yml`（随 FR-0510 package-data）
2. **CI workflow 模板**：
```yaml
name: louke-ci
on:
push:
branches: [main, "releases/**"]
pull_request:
branches: [main, "releases/**"]
workflow_dispatch:
inputs:
spec_id:
description: "spec-id to scan (e.g. v0.6-008). Leave blank to scan all."
required: false
default: ""
jobs:
gate:
runs-on: ubuntu-latest
steps:
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
- run: pip install louke
- name: AC traceability scan
run: |
if [ -n "${{ inputs.spec_id }}" ]; then
lk archer ci-scan --spec "${{ inputs.spec_id }}"
else
for spec in .louke/project/specs/*/; do
spec_id=$(basename "$spec")
lk archer ci-scan --spec "$spec_id" || exit 1
done
fi
```
3. `lk init` 默认安装到 `<root>/.github/workflows/louke-ci.yml`（`--with-workflows` / `--no-workflows` flag）
4. **SPEC_ID 解析规则**：优先读 `workflow_dispatch` 输入；其次 CI 默认从 `.github/CODEOWNERS` 或 `.louke/project/project-info.md:Current Stage` 推断；都不存在则扫所有 spec（每个单独调用）
**AC**
- AC-FR0520-01: init 后 `<root>/.github/workflows/louke-ci.yml` 存在
- AC-FR0520-02: `--no-workflows` 不创建该文件
- AC-FR0520-03: workflow 含 `workflow_dispatch` 入口 + spec_id input
- AC-FR0520-04: workflow 含循环 `for spec in .louke/project/specs/*/`（不依赖 sed 推断）
- AC-FR0520-05: `pip install louke` 后 `lk archer ci-scan` 可调用
---
<a id="fr-0530"></a>
### FR-0530 `lk scout commit-foundation` glob 修复
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0530-lk-scout-commit-foundation-glob-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §6 + B1.4**：当前 `louke/scout.py:71-73` 用 `subprocess.run(['git', 'add', f"{spec_path}/*.md", ...])`，但 subprocess list 模式不走 shell，glob 不展开。
**实现要点**：
1. 改为先 `glob.glob(f"{spec_path}/*.md")` 得具体路径列表，再传给 `git add`
2. 若 `glob` 返回空 → warning + 继续（不阻断 commit）
3. 同步加 `.louke/project/project-info.md`（无 glob）
**AC**
- AC-FR0530-01: `lk scout commit-foundation` 后 `git status` 不再残留 untracked `*.md`
- AC-FR0530-02: 跑完后 `git log --name-only -1` 含 `specs/{id}/*.md` 文件名
- AC-FR0530-03: `*.md` glob 无匹配时 warning 但不 exit 非零
---
<a id="fr-0540"></a>
### FR-0540 `verify_acceptance.py` 默认 release 分支 + gh api 路径修正
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0540-verify_acceptancepy--release---gh-api-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §8 + B1.5**：当前 `verify_acceptance.py:86, 99, 104` 硬读 `?ref=main`；`--branch` 默认 `main`；gh api path 不完整。
**实现要点**：
1. `--branch` 默认从 `<root>/.louke/project/project-info.md` 的 `Release Branch` 字段读取（如 `releases/v0.6`）；缺失 fallback 到 `main` 并 warning
2. gh api path 补全：`/repos/{owner}/{repo}/contents/{path}?ref={branch}`
3. 增加 `--repo` 自动从 project-info.md 的 `Repo` 字段读（FR-0240 类回落）
4. `gh repo view` 仅在缺 project-info.md 时用
**AC**
- AC-FR0540-01: project-info.md 含 `Release Branch: releases/v0.6` → `verify-acceptance` 读 `releases/v0.6`（不是 main）
- AC-FR0540-02: project-info.md 缺 release branch → fallback main + warning
- AC-FR0540-03: gh api 调通读出 `releases/v0.6/.louke/project/specs/{id}/spec.md`
- AC-FR0540-04: `--branch releases/v0.5` 显式覆盖默认
---
<a id="fr-0550"></a>
### FR-0550 FR/AC 4 位 schema 全栈升级
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0550-fr-ac-4--schema-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM B1.6 / B1.7 / §14 + 我的 A2**：
- `.github/ISSUE_TEMPLATE/feature.yml` regex `^FR-\\d{3}$` (3 位)
- `louke/_tools/check_acs.py:13-14` regex `\d{3}`
- `louke/_tools/check_assertions.py` regex 待查
- `louke/_tools/verify_acceptance.py` regex 待查
- `louke/_tools/verify_issue_schema.py` regex 待查
- `louke/_tools/quote_parser.py` regex 待查
- `README.md:216` 比较表 `FR-XXX / AC-XXX-N`
- `README.zh.md:212` 比较表 `FR-XXX / AC-XXX-N`
**实现要点**：
1. 所有 FR/AC 正则改为 4 位：`re.compile(r'<a\s+id="(?:fr|nfr)-(\d{4})"', re.I)` 等
2. issue template 改为 `regex: "^FR-\\d{4}$"`，placeholder `FR-0001`，URL fragment `#fr-0001`
3. `louke/schema.py` 新增共享正则常量，所有 `_tools/*.py` 引用（避免各处重复定义）
4. README § "How louke compares" 表格行改：`FR-XXXX / AC-FRXXXX-YY + lk archer ci-scan`
5. README 比较表同步更新（GLM §14 第 3 条）
**AC**
- AC-FR0550-01: 12 个 `louke/_tools/*.py` 引用统一 4 位正则（来自 `louke/schema.py`）
- AC-FR0550-02: feature.yml `regex: "^FR-\\d{4}$"`（不是 3 位）
- AC-FR0550-03: README + README.zh 表格行 `FR-XXXX / AC-FRXXXX-YY`
- AC-FR0550-04: 用 4 位 FR 的 fixture spec.md 通过 verify-acceptance
---
<a id="fr-0560"></a>
### FR-0560 `lk archer ci-scan` 参数一致性 + 4 位 AC
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0560-lk-archer-ci-scan---4--ac]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §9 + B2.1**：当前 `archer.py:ci-scan` 只接 `--spec`；`cmd_ci_scan` 内部用 `--acceptance` + `--tests`，但 argparse 不暴露 → 用户按 `templates/test-plan.md` 示例调必崩。
**实现要点**：
1. `lk archer ci-scan` argparse 改：
- `--spec` 与 `--acceptance` 互斥（spec-id 解析到 acceptance.md 路径）
- `--tests DIR` 可选（默认 `tests/`）
- `--json` 输出结构化结果
2. 与 `templates/test-plan.md` 示例调用方式对齐
3. 4 位 AC 引用（FR-0550 已覆盖）
**AC**
- AC-FR0560-01: `lk archer ci-scan --spec v0.6-008-closure` 仍可用
- AC-FR0560-02: `lk archer ci-scan --acceptance .louke/.../acceptance.md --tests tests/` 也能用（template 示例方式）
- AC-FR0560-03: 互斥：同时给 `--spec` + `--acceptance` → argparse 错误
- AC-FR0560-04: `--json` 输出 `{"ac_total": N, "ac_referenced": M, "anti_patterns": [...], "passed": bool}`
---
<a id="fr-0570"></a>
### FR-0570 `lk devon run-tests` 项目配置化
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0570-lk-devon-run-tests-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §10 + B2.2**：当前硬编码 `pytest` + `tests/`。
**实现要点**：
1. 读 `<root>/pyproject.toml` 的 `[tool.louke.test]` 段（如不存在 → fallback 当前硬编码）：
```toml
[tool.louke.test]
command = "pytest"
args = ["-q", "--tb=short"]
paths = { unit = "tests/unit/", integration = "tests/", e2e = "tests/e2e/", all = "tests/" }
```
2. 非 Python 项目可在 `[tool.louke.test]` 配 `command = "npm test"` 等
3. `--scope` 仍按 unit/integration/e2e/all
4. `--fast` 保留 → 加 `-x` 到 args 末尾
**AC**
- AC-FR0570-01: pyproject.toml `[tool.louke.test]` 不存在 → 用硬编码 fallback
- AC-FR0570-02: 配置 `command = "npm test"` → 跑 `npm test` 而不是 pytest
- AC-FR0570-03: `--scope unit` 按 paths.unit 配置定位测试目录
- AC-FR0570-04: 配置错误（如 `command = ""`）→ exit 1 actionable
---
<a id="fr-0580"></a>
### FR-0580 `lk devon commit-rgr` 加 push + `--issue` + 可配置
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0580-lk-devon-commit-rgr--push----issue--]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §10 + B2.3 / B2.4**：当前只 commit，不 push；缺 `--issue` flag 写 `Closes #N`。
**实现要点**（采纳 GLM §18 标注——开发者指令要求不默认 push，避免 agent 误 push）：
1. **默认 no-push**：只 commit，不 push
2. `--push` flag 显式 push（agent prompt 中由 Maestro/用户显式传）
3. `--issue #N` 把 `Closes #N` 加到 commit message 末尾
4. 保留 `--task-id TASK-XX` 兼容 Devon.md 现有协议
5. message 格式：`test: red TASK-01 {message} {Closes #N}`
**AC**
- AC-FR0580-01: 默认跑完后 `git log -1` 含新 commit，`git status` 含 ahead 状态（未 push）
- AC-FR0580-02: `--push` 后 commit push 到 origin，`git status` 干净
- AC-FR0580-03: `--issue #42` 后 commit message 含 `Closes #42`
- AC-FR0580-04: 缺 `--phase` 或 `--message` → argparse 错误
---
<a id="fr-0590"></a>
### FR-0590 `lk keeper gate` 完整检查
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0590-lk-keeper-gate-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §10 + B2.5 / B2.6**：当前 `keeper.py:check_commit_messages` 只查 commit prefix。
**实现要点**：
1. **commit format**: R-G-R 前缀（已有）
2. **R-G-R 顺序**: 对 commit-range 内每个 commit，验证 phase 顺序（如 `test: red` → `feat: green` → `refactor:`），单 cycle 内不允许跳
3. **测试先于实现**: cycle 内 `test: red` 必须先于 `feat: green` 提交
4. **lint**（可选）: `[tool.louke.lint]` 配 `command = "ruff check"` 等；缺则跳过
5. **typecheck**（可选）: `[tool.louke.typecheck]` 配 `command = "mypy src"` 等；缺则跳过
6. **AC trace**: 调 `lk archer ci-scan --commit-range <range>` 验证 AC 引用闭合
7. **反模式**: 调 `lk archer check-acs` + `lk archer check-anti-patterns`（如实现）
8. **--tests**: 走 FR-0570 的项目配置
9. **退出**: 任一失败 → exit 1，stderr 列出失败项 + actionable 提示
**AC**
- AC-FR0590-01: commit range 内 `feat: green` 在 `test: red` 之前 → exit 1，stderr 含 `R-G-R order`
- AC-FR0590-02: commit message 不符前缀 → exit 1
- AC-FR0590-03: ci-scan 失败（AC 未引用） → exit 1，列出未引用 AC
- AC-FR0590-04: lint 配置存在 → 跑 lint；失败 exit 1
- AC-FR0590-05: 全部通过 → exit 0
- AC-FR0590-06: `--tests` 跑项目配置的 test command，失败 exit 1
---
<a id="fr-0600"></a>
### FR-0600 `lk prism review` diff range 支持
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0600-lk-prism-review-diff-range-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §10 + B2.7**：当前 `prism.py:50, 109, 126` 用 `get_diff_files('HEAD~1', args.diff)`，当 `args.diff='HEAD~1..HEAD'` 时把 range 当 ref。
**实现要点**：
1. 检测 `args.diff` 是否含 `..`：
- 含 → 拆为 `(left, right)`，直接传给 `git diff --name-only {left} {right}`
- 不含 → 维持 `get_diff_files('HEAD~1', args.diff)`（向后兼容）
2. 同步 `lk prism test-patterns` / `lk prism security-quick-scan` / `lk prism code-quality`
**AC**
- AC-FR0600-01: `lk prism review --diff HEAD~1..HEAD` 正确解析 range
- AC-FR0600-02: `lk prism review --diff HEAD` 仍 work（旧行为）
- AC-FR0600-03: 同步到 test-patterns / security-quick-scan / code-quality
---
<a id="fr-0610"></a>
### FR-0610 `lk judge security-audit` 两阶段
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0610-lk-judge-security-audit-]
| 有效需求 | 可测性           | 是否已决定 |
| -------- | ---------------- | ---------- |
| ✅        | ⚠️ 阶段二需 agent | ✅          |
**修复 GLM §10 + B2.8**：当前只有 pattern scan 框架；缺 S 级语义审查 + 机器可读报告。
**实现要点**（采纳 GLM §18.2 第 3 条）：
1. **阶段一（rule-based）**：`lk judge security-audit` 跑现有 pattern scan + 输出初判
2. **阶段二（agent semantic，可选）**：`--use-llm` flag 触发，调用本机模型（`~/.louke/models.json` 中 `kimi-k2.6` 映射，或 `$LOUKE_OPENCODE_REVIEW_MODEL`）生成 S 级审查报告
3. **机器可读报告 schema**（写 `<root>/.louke/raw/security-audit-{date}.json`）：
```json
{
"audit_id": "...",
"stage1_findings": [...],
"stage2_findings": [...] | null,
"blockers": [...],
"warnings": [...],
"verdict": "pass" | "fail" | "needs-human-review"
}
```
4. 退出码：0=pass, 1=fail (blocker), 2=needs-human-review
5. **未配置 LLM**：缺 `--use-llm` 默认 run 阶段一即可，不阻塞
**AC**
- AC-FR0610-01: 默认 `lk judge security-audit` 跑阶段一 + 输出报告
- AC-FR0610-02: `--use-llm` 跑阶段二（缺模型 → exit 1 actionable）
- AC-FR0610-03: 报告含 `verdict` 字段，Maestro 可直接读
- AC-FR0610-04: blocker 存在 → exit 1
---
<a id="fr-0620"></a>
### FR-0620 `lk shield scaffold` 加 `--spec`
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0620-lk-shield-scaffold----spec]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §10 + B2.9**：当前 `shield.py:51-55` 注册的 `scaffold` argparse 没 `--spec`，但 `cmd_scaffold:96` 用了 `args.spec` → 必崩。
**实现要点**：
1. `scaffold` argparse 加 `--spec`（必填）
2. 默认放路径 `.louke/project/specs/{spec}/tests/e2e/`（与 `commit-e2e` 对齐）
3. 错误信息：`The following arguments are required: --spec`
**AC**
- AC-FR0620-01: `lk shield scaffold --type playwright --spec v0.6-008 --scenario login --ac-id AC-FR0100-01` 不崩，生成模板文件
- AC-FR0620-02: 缺 `--spec` → argparse 错误
---
<a id="fr-0630"></a>
### FR-0630 `lk shield run-e2e` 项目配置化
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0630-lk-shield-run-e2e-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §10 + B2.10**：当前硬编码 `pytest` + playwright 参数。
**实现要点**：
1. 读 `[tool.louke.test]` 段（同 FR-0570），`paths.e2e` 走配置
2. `[tool.louke.test.e2e]` 子段（可选）：
```toml
[tool.louke.test.e2e]
command = "pytest"
args = ["-q", "--tb=short", "--browser={browser}"]
```
3. `--browser` 默认 `chromium`；非 Playwright 项目可忽略
**AC**
- AC-FR0630-01: 配置 `command = "behave"` → 跑 behave 而不是 pytest
- AC-FR0630-02: `--browser firefox` 替换 `{browser}` 占位
- AC-FR0630-03: e2e 测试不通过 → exit 非零
---
## 8. 功能需求 — §6 Maestro 流程闭环
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#8---6-maestro-]
---
<a id="fr-0700"></a>
### FR-0700 `lk maestro advance` 10 阶段 holdpoint 自动调用
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0700-lk-maestro-advance-10--holdpoint-]
| 有效需求 | 可测性           | 是否已决定 |
| -------- | ---------------- | ---------- |
| ✅        | ⚠️ 部分需 gh mock | ✅          |
**修复 GLM §11 + B3.1**：当前 `maestro.py:advance` 多阶段打印 `[todo]` 后阻塞。
**实现要点**（按 Maestro.md 阶段表）：
| `--stage`     | 自动调用的 holdpoint                                                  | 说明   |
| ------------- | --------------------------------------------------------------------- | ------ |
| `M-FOUND`     | `lk warden foundation-check --repo X --version V --spec-id ID`        | 已存在 |
| `M-SPEC`      | `lk lex verify-acceptance` + `lk lex verify-issue`                    | 已存在 |
| `M-TESTPLAN`  | `lk archer validate-test-plan`（FR-0720）                             | 待实现 |
| `M-ARCH`      | `lk archer validate-arch`（FR-0720）                                  | 待实现 |
| `M-LOCK`      | `lk sage record-lock --spec ID --confirm`（FR-0420）                  | 待实现 |
| `M-DEV`       | `lk keeper gate --commit-range <range>`（FR-0590）                    | 待实现 |
| `M-E2E`       | `lk keeper gate --commit-range <range> --tests` + `lk shield run-e2e` | 待实现 |
| `M-BUGFIX`    | `lk keeper regression --baseline X --current Y`                       | 已存在 |
| `M-SECURITY`  | 走 FR-0720 跳过判定 → 调 `lk judge security-audit` 或 skip            | 待实现 |
| `M-MILESTONE` | 走 FR-0730 合并/tag 检查 + `lk librarian from-raw`                    | 待实现 |
**AC**
- AC-FR0700-01: `lk maestro advance --stage M-FOUND` 调 foundation-check（exit 0 → advance 成功）
- AC-FR0700-02: `lk maestro advance --stage M-LOCK` 缺 `--confirm` → 调 record-lock 失败 → advance exit 1
- AC-FR0700-03: 任意阶段失败 → advance exit 1 + 列出失败子命令
- AC-FR0700-04: 全部成功 → 调 FR-0710 更新 project-info.md
---
<a id="fr-0710"></a>
### FR-0710 `lk maestro advance` 成功后更新 project-info.md
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0710-lk-maestro-advance--project-infomd]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §11 + B3.2**：当前 advance 只打印，不更新 state。
**实现要点**：
1. advance 成功后写 `<root>/.louke/project/project-info.md` 的 `Current Stage` 字段（新增）
2. 写 `<root>/.louke/raw/{date}/maestro-{spec-id}-stage-{stage}.md`（按 FR-0810 路径）记录推进事件
3. 若 M-MILESTONE → 追加 `Last Milestone: {ISO date}`
**AC**
- AC-FR0710-01: advance 成功后 project-info.md 含 `Current Stage: M-FOUND`
- AC-FR0710-02: raw 路径下生成 session 记录
- AC-FR0710-03: 下次 advance 读 `Current Stage` 推断前置阶段
---
<a id="fr-0720"></a>
### FR-0720 M-SECURITY 自动跳过判定
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0720-m-security-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §11 + B3.3**：当前 M-SECURITY 需手工触发。
**实现要点**：
1. `lk maestro advance --stage M-SECURITY`：
- 读 project-info.md 的 `Security Audit: enabled/disabled` 字段
- `disabled` → skip，stdout `[阶段: M-SECURITY] DoD 关闭，跳过`
- `enabled` → 调 `lk judge security-audit --release releases/{version}`（FR-0610）
**AC**
- AC-FR0720-01: `Security Audit: disabled` → advance exit 0，跳过 audit
- AC-FR0720-02: `Security Audit: enabled` → 调 `lk judge security-audit`
- AC-FR0720-03: audit verdict = `pass` → advance exit 0
- AC-FR0720-04: audit verdict = `fail` → advance exit 1
---
<a id="fr-0730"></a>
### FR-0730 M-MILESTONE 检查 Librarian + merge/tag
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0730-m-milestone--librarian--merge-tag]
| 有效需求 | 可测性  | 是否已决定 |
| -------- | ------- | ---------- |
| ✅        | ⚠️ 需 gh | ✅          |
**修复 GLM §11 + B3.4**：当前 M-MILESTONE 不验证 Librarian / merge / tag。
**实现要点**：
1. `lk maestro advance --stage M-MILESTONE`：
- 检查 `git status` clean
- 检查 `releases/{version}` 分支已合回 main（如 `gh pr view --base main --head releases/{version} --json state`）
- 检查 tag `v{version}` 存在
- 检查 `lk librarian from-raw` 已 distill 完（看 `.louke/raw/` 是否有未处理 resolved 条目）
- 全部通过 → exit 0
2. **未合回 main** → exit 1，提示跑 merge
3. **缺 tag** → exit 1，提示打 tag
**AC**
- AC-FR0730-01: `releases/v0.6` 已合 main + tag `v0.6` 存在 + raw 已 distill → advance exit 0
- AC-FR0730-02: 未合 main → exit 1，stderr 含 `merge releases/v0.6`
- AC-FR0730-03: 缺 tag → exit 1，stderr 含 `git tag v0.6`
---
<a id="fr-0740"></a>
### FR-0740 `lk lex verify-project` Issue↔Project 关联验证
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0740-lk-lex-verify-project-issueproject-]
| 有效需求 | 可测性  | 是否已决定 |
| -------- | ------- | ---------- |
| ✅        | ⚠️ 需 gh | ✅          |
**修复 GLM §8 + B3.6**：Lex 阶段二要求验证 Project 关联；当前 `verify_issue_schema` 不实现。
**实现要点**：
1. 新增 `lk lex verify-project --spec ID`：
- 读 project-info.md 的 Project URL
- 对 spec.md 每个 FR 对应的 issue，验证 `gh project item-list {PROJECT_URL} --format json` 包含该 issue URL
- 缺关联 → 报告未关联列表
2. `lk lex verify-issue --spec ID` 阶段三增强：自动调 verify-project 作为子检查
**AC**
- AC-FR0740-01: 全部 issue 已关联 Project → exit 0
- AC-FR0740-02: 2 个 issue 未关联 → exit 1，列出未关联编号
- AC-FR0740-03: project-info.md 缺 Project URL → exit 1 提示先跑 scout foundation
---
## 9. 功能需求 — §7 项目信息模板与 Librarian
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#9---7--librarian]
---
<a id="fr-0800"></a>
### FR-0800 `templates/project-info.md` 字段对齐 Scout.md
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0800-templates-project-infomd--scoutmd]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §6 + B3.5**：当前模板 8 字段，Scout.md Step 6 模板 12 字段。
**实现要点**：
1. `louke/templates/project-info.md` 改为：
```markdown
# Project Info
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#project-info]
- **Version**: {版本号}
- **Repo**: github.com/{owner}/{repo}
- **Project**: {repo}-{version}
- **Project ID**: https://github.com/users/{owner}/projects/{id}
- **Spec ID**: v{version}-{NNN}-{keyword}
- **Release Branch**: `releases/{version}`
- **Smoke Test Issue**: #{编号}（closed）
- **Smoke Test PR**: #{编号}（closed）
- **DoD**: {Step 1 收集的完成定义}
- **Security Audit**: {enabled / disabled}
- **Current Stage**: {M-FOUND | M-SPEC | ...}
- **Created**: {YYYY-MM-DD}
```
2. `check_foundation.py` F6 校验全部 12 字段（含 current_stage）
**AC**
- AC-FR0800-01: 模板含全部 12 字段
- AC-FR0800-02: `lk scout foundation`（FR-0400 MVP）跑完后 project-info.md 含全部 12 字段
- AC-FR0800-03: `lk warden foundation-check` 缺任一字段 → exit 1 列出缺失
---
<a id="fr-0810"></a>
### FR-0810 raw 路径统一
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0810-raw-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §12 + B4.1**：11 个 agent 用 `.louke/raw/{date}/{session-id}.md`，Librarian.md 用 `.louke/raw/sources/`。
**实现要点**：
1. `Librarian.md:25` 改为 `.louke/raw/{yy-mm-dd}/`（删除 `sources/` 引用）
2. 路径生成工具函数 `louke/_common.py:raw_path(date, session_id)` 统一接口
3. 现有 `wiki/.louke/raw/sources/` 残留条目（如果有）一次性迁移到 `.louke/raw/{date}/`（按 frontmatter `date` 字段）
**AC**
- AC-FR0810-01: 12 个 agent prompt 路径引用全部为 `.louke/raw/{date}/{session-id}.md`
- AC-FR0810-02: `librarian.py` 用 `raw_path()` 函数
- AC-FR0810-03: 旧 `raw/sources/` 残留目录被迁移或删除
---
<a id="fr-0820"></a>
### FR-0820 raw / wiki 入 git 策略
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0820-raw---wiki--git-]
| 有效需求 | 可测性 | 是否已决定 |
| --- | --- | --- |
| ✅ | ✅ | ✅ |
**v0.6-008 决定**（采纳 Aaron 2026-06-30 两条评论 + 关联 backlog issue）：
**默认**：`raw/` / `wiki/` **入 git**（与产品代码同仓）——多人协作 + agents IDE 内 git push 时一并提交 + 简单。
**未来增强**（**不在 v0.6-008 范围**，已建 backlog issue）：
- **Backlog issue [#78](https://github.com/zillionare/louke/issues/78)**：`.louke/project` 作为独立私有 GitHub repo（`private`，通过 git submodule 引入），分离 spec/wiki 与公开代码。**GLM review 标注：submodule 设计涉及多个 FR 改造（FR-0100/0101/0400/0401/0530/0730/0800 都要加 submodule 支持），单次 PR 风险高，独立 spec 实施**。
- **Backlog issue [#79](https://github.com/zillionare/louke/issues/79)**：louke web 服务（`louke serve`），渲染 + 可选在线编辑 wiki / spec / acceptance / test-plan。**GLM review 标注：web 服务是独立大件（部署/认证/编辑 API/PR 流程），独立 spec 实施**。
**实施要点**（v0.6-008 范围内）：
1. README § "Project memory" 段明确："`.louke/raw/` 与 `.louke/wiki/` **入 git**（多人共享协作记忆）；`.louke/agents/` 与 `.louke/templates/` 与 `.opencode/agents/` **不入 git**（本地缓存，由 `lk init` 重建）"
2. `.gitignore` 模板（FR-0100 step 6）只 ignore `agents/` / `templates/` / `.opencode/agents/`，**不**ignore `raw/` / `wiki/`
3. README 加段"Backlog project"（FR-0402 触发，per-repo backlog Project 用法），并链接 issue #78 / #79 提示未来增强路径
4. v0.6-005 epic #74 的"framework vs project split"对 raw/wiki 的处理与此保持一致
**AC**
- AC-FR0820-01: README § "Project memory" 段含明确"raw/wiki 入 git, agents/templates 不入"声明
- AC-FR0820-02: 生成的 `.gitignore` 不含 `.louke/raw/` / `.louke/wiki/`
- AC-FR0820-03: 文档与 `agents/*.md` 路径引用一致
- AC-FR0820-04: README 含"Backlog project"段（FR-0402 触发），并链接 issue #78 / #79 作为未来增强路径
---
<a id="fr-0830"></a>
### FR-0830 Librarian 完整功能（frontmatter 校验 / lint / cache / overview / log）
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0830-librarian-frontmatter----lint---cache---overview---log]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §12 + B4.3 / B4.4**：当前 `librarian.py` 简单实现。
**实现要点**：
1. **`lk librarian lint --wiki <dir>`** 增强：
- frontmatter 必填 `date`/`title`/`type`
- broken wikilinks `[[xxx]]` 检测（xxx 不存在 → warning）
- orphan pages（无任何 wikilink 引用）→ warning
- duplicate pages（title 重复）→ error
2. **`lk librarian rebuild-index --wiki <dir>`** 增强：
- 按 `type` 分组（decision / experience / entity）
- 按 `date` 倒序
- 每项包含 title + 日期 + frontmatter tags
3. **incremental cache** `<wiki>/.cache/sha256.json`：每页 sha256，lint 时只重算变更页
4. **`<wiki>/overview.md`**：自动生成（按 type 分组的高层摘要，每 type 最多 5 条最近）
5. **`<wiki>/log.md`**：自动追加每次 lint / rebuild-index / from-raw 的事件（ISO timestamp + 动作 + 操作者）
6. **`lk librarian frontmatter-lint`** 新子命令：只校验 frontmatter 不过 wikilink
**AC**
- AC-FR0830-01: wiki 页缺 `date` 字段 → lint exit 1 列出
- AC-FR0830-02: `[[nonexistent]]` wikilink → lint warning
- AC-FR0830-03: rebuild-index 后 `index.md` 按 type 分组
- AC-FR0830-04: lint 后 `.cache/sha256.json` 含每页 hash
- AC-FR0830-05: overview.md 含每 type 摘要
- AC-FR0830-06: log.md 含今日 lint 事件
---
## 10. 功能需求 — §8 文档一致性
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#10---8-]
---
<a id="fr-0900"></a>
### FR-0900 README / README.zh 文档修复（合并所有散点）
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#fr-0900-readme---readmezh-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**修复 GLM §4 / §13 / §14 + 我的 A5**（合并为一个 FR，AC 覆盖所有散点）：
1. **删除** `{"plugin": ["louke"]}` 误导配置（双 README）
2. **替换** § "Use in Your Project": `lk scout foundation` 示例 → `lk init <name>` + `lk init .`（FR-0100/0101）
3. **修正** § "Use with Your AI Assistant → OpenCode": 改为 `lk init` 自动生成 `.opencode/agents/*.md` + `default_agent: maestro`
4. **删除** README.zh:162 孤立 `s`（GLM §14 + 实测确认）
5. **比较表** `FR-XXX / AC-XXX-N` 改为 `FR-XXXX / AC-FRXXXX-YY`（双 README）
6. **加段** "How louke compares" 表底：标注 FR 编号已统一 4 位
7. **加段** README § Architecture 块底部：从"supported environments"补一句"版本查询：`lk --version`"
8. **替换** "32 commands" 描述（README § "You now have"）：自动从 `lk --help` 取实际命令数（template 脚本渲染）
9. **加段** § Install 末尾："升级: `pip install --upgrade louke`"（呼应 FR-0130 P1）
10. **加段** § Use with Your AI Assistant 后："用户心智入口仍是 `lk <agent> <cmd>`，顶层无 alias；Maestro 在 OpenCode 内调度"
**AC**
- AC-FR0900-01: `grep -E '"plugin".*louke|louke.*plugin' README*.md` 命中 0
- AC-FR0900-02: README § "Use in Your Project" 主体是 `lk init <name>` + `lk init .`，不是 `lk scout foundation`
- AC-FR0900-03: README.zh 不含孤立行 `^s$`
- AC-FR0900-04: README.md:216 比较表行 `FR-XXXX / AC-FRXXXX-YY`
- AC-FR0900-05: README.zh:212 同样
- AC-FR0900-06: README 含 `lk --version` 用法说明
- AC-FR0900-07: README 含 `pip install --upgrade louke` 升级指引
- AC-FR0900-08: README 顶部 "Supported environments" 段保留（已加）
- AC-FR0900-09: "32 commands" 改为自动从 `lk --help` 取
- AC-FR0900-10: **新增段** "Backlog project"（中英文 README 都加，面向终端用户），含：
- 何时创建：`lk scout foundation` 自动确保 `{repo}-backlog` Project 存在（dedup by title，重复跑不重建）
- 与 `{repo}-{version}` Project 区别：per-repo 永久 vs per-release 临时
- 用法示例：`gh issue create --no-milestone` 落到 backlog；planning 时把 backlog issue 拉进 `{repo}-{version}`
- **不**提及任何 louke 内部项目（如 `specforge-backlog`）；本段只面向终端用户
- AC-FR0900-11: backlog 段位置：§ Architecture 之后、§ Use with Your AI Assistant 之前，作为独立 `###` 段
- AC-FR0900-12: README + README.zh 含 "Agent capabilities & model tiers" 5 列表（Agent / Tier / Open-source example / Closed-source reference / 备注），覆盖全部 12 个 agent，档位标注 S/A/B
---
## 11. 非功能需求
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#11-]
---
<a id="nfr-0100"></a>
### NFR-0100 测试矩阵（GLM §15 端到端可用性测试）
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#nfr-0100-glm-15-]
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
**新增 bats 文件**（每个 FR 一组）：
- `tests/test_init.bats` — FR-0100/0101/0110
- `tests/test_board.bats` — FR-0200
- `tests/test_models.bats` — FR-0201
- `tests/test_default_agent.bats` — FR-0300
- `tests/test_scout_foundation.bats` — FR-0400/0401/0402/0530
- `tests/test_sage_create_issues.bats` — FR-0410
- `tests/test_sage_record_lock.bats` — FR-0420
- `tests/test_librarian.bats` — FR-0430/0440/0830
- `tests/test_resolve_spec_path.bats` — FR-0450
- `tests/test_version.bats` — FR-0500
- `tests/test_package_data.bats` — FR-0510/0520
- `tests/test_verify_acceptance.bats` — FR-0540
- `tests/test_fr_schema.bats` — FR-0550
- `tests/test_archer_ci_scan.bats` — FR-0560
- `tests/test_devon_config.bats` — FR-0570/0580
- `tests/test_keeper_gate.bats` — FR-0590
- `tests/test_prism_diff.bats` — FR-0600
- `tests/test_judge_security.bats` — FR-0610
- `tests/test_shield_scaffold.bats` — FR-0620/0630
- `tests/test_maestro_advance.bats` — FR-0700/0710/0720/0730
- `tests/test_lex_verify_project.bats` — FR-0740
- `tests/test_project_info_template.bats` — FR-0800
- `tests/test_raw_path.bats` — FR-0810
**GLM §15 10 项端到端测试**必须包含：
1. `lk --version` / `lk --help` 成功
2. `lk init --dry-run` 在空目录输出完整计划
3. `lk init/adopt` 在临时 git repo 生成 `.louke` / issue template / workflow / `.opencode/agents/`
4. `lk models doctor` 用 mock `opencode models` 自动绑定 `glm-5.2` → `provider/glm-5.2`
5. `lk board opencode` 生成 12 个 agent，`model:` 是 provider/model
6. `lk scout foundation` 用 gh mock 跑通（不触碰真实 GitHub）
7. `lk sage create-issues` gh mock 按 FR-XXXX 创建 issue 关联 Project
8. `lk lex verify-acceptance/verify-issue` 对 4 位 schema 通过
9. `lk archer ci-scan` 对 4 位 AC 引用通过
10. `lk maestro advance` 在 fixture 项目按阶段推进或给出明确阻塞原因
---
<a id="nfr-0200"></a>
### NFR-0200 错误信息 actionable
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#nfr-0200--actionable]
所有失败路径 stderr **必须**含：
- (a) 失败的具体子命令或检查
- (b) 用户下一步可以做什么（"运行 `lk X --help`" / "检查 ~/.louke/models.json" 等）
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
<a id="nfr-0300"></a>
### NFR-0300 现有 bats 测试不回归
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#nfr-0300--bats-]
`tests/test_*.bats` 现有所有 case 在本 spec 实施后必须继续通过；新功能只增不改现有路径。
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
<a id="nfr-0400"></a>
### NFR-0400 ADR 留痕
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#nfr-0400-adr-]
新增 `.louke/wiki/decisions/009-louke-v030-usability-closure.md`（或合并到 008），含：
- 背景：v0.3.0 PyPI 发布但端到端不可用
- 决策：§1-§8 共 ~30 FR 一次性收口
- 备选 A：分多个小 spec 跨数月（拒绝，慢）
- 备选 B：维持现状等用户报告（拒绝，损害品牌）
- 后果：~60 个文件修改（CLI/agents/templates/CI/docs/tests）
并在 README § Architecture / Decision 表格追加 `[009]` 一行。
| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
---
## 12. 澄清记录
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#12-]
| #   | 问题                                                                                                                                                     | 待回答              |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| 1   | FR-0400 MVP 与 FR-0401 完整 P0 实施时，是先 MVP 还是并行？倾向先 MVP（验收写 project-info + 调子命令），FR-0401 单独 PR                                  | Aaron: 需要全部实现 |
| 2   | FR-0610 `--use-llm` 阶段二，未配模型时是否要 hard fail 还是 warning + 仅阶段一？倾向 warning（不阻塞 CI）                                                | 仅阶段一            |
| 3   | FR-0820 raw/wiki 入 git——Aaron 2026-06-30 拍板：v0.6-008 默认入 git；submodule + web 服务进 backlog (#78 / #79)                                                  | resolved by minimax  |
| 4   | FR-0130 `lk upgrade` P1 还是 P0？GLM 倾向 P1，本 spec 已采纳                                                                                             | 已采纳 GLM          |
| 5   | FR-0830 wiki frontmatter `type` 取值约束：是 `experience / decision / entity` 三选一，还是允许 free-form + lint 校验？倾向三选一（与 Librarian.md 一致） | 三选一，以后可扩展  |
| 6   | FR-0700 M-LOCK 阶段 `lk sage record-lock` 的 `--confirm` 是必须 flag 还是默认 prompt？倾向 flag（CI 友好），人类 IDE 内由 Maestro 调度时显式传           | flag                |
> **GLM:** 暂不实现 FR-0100/FR-0101 中“agents=13（12 agent + ROSTER）”相关验收。当前仓库根目录与包内 `louke/agents/` 均没有 `ROSTER.md`，历史 `ROSTER.md` 已在迁移中删除；若要恢复，需先决定是恢复 ROSTER 作为包资源，还是把 AC-FR0100-02 改为 12 个 agent。直接实现会导致 init 测试按不存在资源失败。
> 状态: [resolved by minimax 2026-06-30] — AC-FR0100-02 改为 12（spec.md:196 / acceptance.md:63）；FR-0100 step 4 删除 ROSTER 引用；scenario-0100 删除 ROSTER 引用。无需恢复 ROSTER 资源。
>> Aaron:没有 roster 这个 Agent， 请改AC-FR0100-02 → 已采纳
> **GLM:** 暂不实现 FR-0100/FR-0101 中“templates=7”相关验收的精确数量。当前仓库 `templates/` 实际有 10 个 markdown 模板（acceptance、bug-fix、issues、prd、project-info、security-checklist、spec、task-log、task-plan、test-plan），spec.md 与 acceptance.md 均写 7，但又列出超过 7 个名称。需要先把模板数量定稿为 10，或明确只复制核心 7 个。
> 状态: [resolved by minimax 2026-06-30] — AC-FR0100-03 改为 10（spec.md:197 / acceptance.md:64），列出全部 10 个名称与 `$LOUKE_HOME` 数量一致。
> **GLM:** 暂不实现 FR-0500 的“构建时自动从 pyproject 同步 `louke/__init__.py`”完整方案。当前项目使用 setuptools + Makefile，没有 hatch hook；可以先实现 `lk --version` 与手动版本对齐，但 build-time version-sync 需要单独设计，避免引入构建系统变化。
> 状态: [resolved by minimax 2026-06-30] — FR-0500 step 2-4 改为手动同步 + `tests/test_version_sync.bats` 守门（spec.md:1448 段）。
> **GLM:** 暂不实现 FR-0510 中将 `.github/ISSUE_TEMPLATE/*.yml` 与 `.github/workflows/*.yml` 作为 `louke` 包内路径的方案。setuptools package-data 只能可靠包含包目录内文件；当前 `.github/` 在仓库根，不在 `louke/` 包目录。需要先决定是移动/复制资源到 `louke/resources/`，还是调整构建 MANIFEST + importlib.resources 访问方式。
> 状态: [resolved by minimax 2026-06-30] — FR-0510 step 1 改用 `louke/resources/` 装 + `importlib.resources` 访问（spec.md:1486 段）。
> **GLM:** 暂不实现 FR-0520 中给出的 GitHub Actions 示例原样逻辑。`SPEC_ID` 未定义时用 `ls .louke/project/specs/ | head -1 | sed 's:/.*::'` 不稳定，且多 spec 项目会误扫第一个 spec。需要先定义 CI 如何发现 active spec 或由 workflow input/env 明确传入。
> 状态: [resolved by minimax 2026-06-30] — FR-0520 step 2 改用 `workflow_dispatch` 输入 + 循环扫所有 spec（spec.md:1518 段）。
> **GLM:** 暂不实现 FR-0580 的默认 `git push` 行为。开发者指令要求不要在未明确请求时 push；把 `lk devon commit-rgr` 默认改为 push 会让本工具执行实现/测试时存在误 push 风险。建议命令支持 `--push` 显式推送，或保持默认不 push，并在 agent prompt 中要求 agent 显式传 `--push`。
> 状态: [resolved by minimax 2026-06-30] — FR-0580 step 1 改默认 no-push，加 `--push` flag（spec.md:1037 段）。
> **GLM:** 暂不实现 FR-0820 的"raw/wiki 入 git"默认策略。该条在 spec 自身仍标注"待 Aaron 拍板"；在拍板前不能修改 `.gitignore` 与 prompts 的入库策略，否则会改变项目记忆的版本化边界。
> 状态: [resolved by minimax 2026-06-30] — Aaron 拍板：v0.6-008 默认入 git；submodule + web 服务进 backlog issue #78 / #79；FR-0820 文本已改，澄清记录第 3 条已更新，AC-4 新增"README 含 Backlog project 段 + 链接 #78/#79"。
> **GLM:** 暂不依赖本 spec 的 `acceptance.md` 作为 `lk lex verify-acceptance` 门禁输入。当前 acceptance.md 使用 `### FR-0100` + `- **AC-FR...**` 索引式结构，而现有/目标 verify-acceptance 工具要求 `## FR-XXXX` 小节下 `### AC-N` 连续编号结构；实测 `lk lex verify-acceptance --spec-file ... --acceptance-file ...` 报缺少全部 FR/NFR 节。需要 Sage/minimax 先把 acceptance.md 改为工具契约结构，或另行修改工具契约。
> 状态: [resolved by minimax 2026-06-30] — acceptance.md 全文重写为 `## FR-XXXX {title}` + `### AC-N` 工具契约结构（与 verify_acceptance.py:155, 287 一致）。
## 13. Lex 审核结果
[source: project/specs/v0.6-008-louke-v030-usability-closure/spec.md#13-lex-]
- [ ] 所有需求可追踪到用户故事
- [ ] 所有需求可断言（有明确的测试方法）
- [ ] 没有模糊词汇
- [ ] 所有 FR 都有显式锚点 `<a id="fr-XXXX"></a>`
- [ ] 所有 FR 编号 4 位
- [ ] 与既有 spec（v0.5-007 / v0.5-008 / v0.6-005）的引用无冲突
- [ ] `agents/*.md` 路径引用与 FR-0810 一致

## v0.6-009-agent-permission-tightening

# v0.6-009 — Agent 权限收紧 + 分层编排 + 交互式子代理 — Spec
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#v06-009--agent-------spec]
- **Spec ID**: v0.6-009-agent-permission-tightening
- **创建日期**: 2026-07-03
- **修订**:
- 2026-07-03 12:45 Qwen 一轮 review 后重大修订（字段名 `permissions` → `permission`、格式改 YAML 对象、移除 `interactive: true`、改用 `permission.question`、改 lint 归属为 `lk agent lint`、Maestro 改 `mode: primary`、spec 拆分 v0.3.0/v0.3.1）
- 2026-07-03 13:35 Qwen 二轮 review（`external_directory` / `doom_loop` 显式 deny + FR-0070 方案 b + `MIN_OPENCODE_VERSION = "1.1.1"`）
- **2026-07-03 14:00 IDE 实测通过 + spec 完全锁定**：A-001-4 (subagent `question` 冒泡) 实证确认，FR-0070 从 v0.3.1 合并入 v0.3.0（移除 v0.3.0/v0.3.1 拆分，整 spec 一次性 v0.3.0 发版）
- **状态**: 草稿（Qwen 三轮 review 已完结；待 Aaron 最终拍板）
- **关联**:
- 既有 spec：v0.6-008 FR-0220（source frontmatter 与档位表一致）、v0.6-008 FR-0300（默认 agent = maestro）
- 关联 issue：#80（models doctor 三层验证，本 spec 的副产品是 frontmatter 收紧）
- Aaron 2026-07-03 调研：OpenCode 主代理-子代理分层编排模式
- Qwen 2026-07-03 12:15 / 13:05 / 14:30 review：3 个🚨关键发现 + spec 拆分建议 + 二轮 3 行动项 + 三轮 3 处文档内部不一致
- **Aaron 2026-07-03 14:00 IDE 实测**：subagent `question` 弹框冒泡到主窗口已确认（截图证据见 `.louke/qwen-review-v0.6-009.md` §10 Kilo 二轮回应）
## 0. 范围与边界
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#0-]
### 0.1 本 spec 收纳（v0.3.0 一次性发版）
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#01--spec-v030-]
| 主题 | FR 范围 |
|---|---|
| 权限收紧 (5 个 agent `permission:` frontmatter: 4 角色 + Maestro) | FR-0010 ~ FR-0050 |
| 分层编排 (Maestro `mode: primary` + 11 agent `mode: subagent`) | FR-0060 |
| 交互式 subagent (4 个允许 question, 7 个 deny + 1 个 Maestro deny) | **FR-0070** |
| 受影响下游 + supersede 标注 | §0.2 |
| 单一 primary agent 约束 + IDE 实测基线 | NFR-0040 / NFR-0050 |
### 0.2 受影响下游 / supersede
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#02----supersede]
- **v0.6-008 FR-0200**："装完 louke 后 `<Leader>a` agent 列表看到全部 12 个 agent" → **SUPERSEDED by v0.6-009 FR-0060.2**：TUI 顶层 `<Leader>a` 只看到 Maestro；其余 11 个通过 `task` 调用（OpenCode `mode: subagent` 行为：不在 Tab 循环、不在 `<Leader>a` 列表）
- **v0.6-008 FR-0210**：source frontmatter 验证（`models` 字段、4 位编号等）→ 扩展：新增 `mode` 约束（必须为 `subagent` 除 Maestro）/ 新增 `permission` 字段 schema 验证
- **用户已有 `.opencode/agents/`**：`lk board opencode` 重新生成后 agent 可见性会变（12 → 1），属 **breaking change**，NFR-0010 显式声明
### 0.3 本 spec 不收纳
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#03--spec-]
- 7 个非交互式 subagent 的完整 `permission` 块 — 留待 v0.6-010+ 跟进；v0.3.0 仅加 `permission.question: deny` 最小块 (FR-0070.2)
- OpenCode 端按文件路径限制 `edit` 范围（OpenCode 仅 per-tool 控制，无 path 白名单）—— 用 prompt 强约束代替
- 其余 8 个 agent（含 Maestro）的 prompt 内容修订 —— 仅改 frontmatter + 必要段落，业务 prompt 不动
- `lk archer ci-scan` 内部 spec/test 追溯逻辑（与 agent frontmatter 无关）
### 0.4 ~~v0.3.0 / v0.3.1 拆分~~ → 一次性 v0.3.0 发版
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#04-v030---v031----v030-]
**原拆分理由已失效**：
- 拆分仅因 A-001-4 (subagent `question` 冒泡) 未实测
- 2026-07-03 14:00 Aaron IDE 实测**确认** subagent `question` 弹框冒泡到主窗口
- 唯一 blocker 消除，整 spec 合并为一次性 v0.3.0 发版
**v0.3.0（最终发版范围）**：
- FR-0010 ~ FR-0050：权限收紧
- FR-0060：分层编排
- FR-0070：交互式 subagent (4 allow + 7 deny + Maestro deny, FR-0070.3 方案 b 已确保 prompt/config 一致)
- §0.2 / NFR-0010 / NFR-0050：受影响下游 + 单一 primary 约束
**v0.3.0 不再拆分为多个 release**。若 release 后发现问题，走 patch release (v0.3.0.1)。
---
## 1. 用户故事
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#1-]
### US-0100 收紧只读审计
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#us-0100-]
- US-0100: 作为 OpenCode 用户，我希望 Warden / Judge 在 IDE 里跑会话时**只能**读文件、跑命令、搜内容，**不能**改任何业务代码或 `wiki/`，以便审计角色不可能误伤项目
- US-0110: 作为 louke 维护者，我希望 source agent frontmatter 显式声明 `permission: { ... }`（YAML 对象），IDE / OpenCode 据此禁用未列出的工具，便于角色行为可声明、可审计
### US-0200 Archer / Librarian 受限写
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#us-0200-archer---librarian-]
- US-0200: 作为 OpenCode 用户，我希望 Archer / Librarian 在 IDE 里跑会话时**只能**写自己职责范围内的文件（Archer → spec 产物，Librarian → wiki），即使 prompt 失守也**不能**改业务代码
- US-0210: 作为 louke 维护者，我希望 OpenCode 板生成（`lk board opencode`）从 source agent 复制 `permission:` 字段到 `.opencode/agents/*.md`，使 IDE 内实际生效
### US-0300 可验证
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#us-0300-]
- US-0300: 作为 CI 维护者，我希望 `lk agent lint` 校验 source agent 的 `permission:` 字段是 YAML 对象 + 工具名 ∈ OpenCode 白名单 + 4 角色必填 `permission`
- US-0310: 作为 louke 维护者，我希望 README + agent prompt 明确"为什么这个角色有这个权限"，让权限决策有据可查
### US-0400 Maestro 全权工作流控制
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#us-0400-maestro-]
- US-0400: 作为 OpenCode 用户，我希望**只**在 TUI 顶层 `<Leader>a` 列表能看到 Maestro 这一个主代理，其余 11 个专业角色只能通过 Maestro 的 `task` 调用出现；这样工作流的"控制权"始终在 AI 手里（Maestro 自主推进），人类无需按 `Tab` 切换窗口
- US-0410: 作为 louke 维护者，我希望 Maestro 的 frontmatter 显式声明 `permission:`（含 `task`），IDE 据此允许它调用子代理；Maestro 改 `mode: primary` 防止被 subagent 递归调用
- US-0420: 作为 OpenCode 新用户，我希望 `lk init` 生成的 `opencode.json` 把 `default_agent` 设为 `maestro`，新会话默认进入 Maestro 而非其它 agent
### US-0500 交互式 subagent (v0.3.0)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#us-0500--subagent-v030]
- US-0500: 作为 OpenCode 用户，我希望 Scout / Sage / Archer / Judge 4 个 subagent 在执行中可以向用户提问（`permission.question: allow`），其余 7 个 subagent 不能提问（`permission.question: deny`）；弹框**冒泡到主会话窗口**（详见 spec FR-0070.6 测试基线）
- US-0510: 作为 louke 维护者，subagent 的"交互能力"由 `permission.question` 控制（OpenCode per-tool 权限），不是 boolean 开关；如未来发现 Lex / Devon 也需要交互，改 frontmatter 即可
- US-0520: 作为 OpenCode 用户，我**不想**手动按 `<Leader>+Down` 进入子会话查看 subagent 弹框（subagent 弹框冒泡到主窗口）
---
## 2. 关键场景
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#2-]
### scenario-0100 Warden 在 IDE 跑审计
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#scenario-0100-warden--ide-]
```
1. 用户在 OpenCode TUI 用 <Leader>a 切到 Warden
2. Warden 调 `bash` 跑 `lk scout check-foundation` —— ✓ (permission.bash: allow)
3. Warden 调 `read` 读 spec.md —— ✓ (permission.read: allow)
4. Warden 调 `grep` 找 "TODO" —— ✓ (permission.grep: allow)
5. (假设) Warden prompt 失守, 试图 `edit` 改 spec.md —— ✗ OpenCode 拒绝 (permission.edit: deny)
6. (假设) Warden 试图 `task` 创建 subagent —— ✗ OpenCode 拒绝 (permission.task: deny)
```
### scenario-0200 Archer 写 spec 产物
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#scenario-0200-archer--spec-]
```
1. 用户在 OpenCode TUI 用 <Leader>a 切到 Archer (注: v0.3.0 之后 <Leader>a 列表不含 Archer, 此场景仅说明权限模型)
2. Archer 读 spec/acceptance —— ✓ (permission.read: allow)
3. Archer 写 `.louke/project/specs/v0.6-010-foo/test-plan.md` —— ✓ (permission.edit: allow)
4. (假设) Archer prompt 失守, 试图 `edit` 改 `src/foo.py` —— ✓ (permission.edit: allow) ⚠️
↑ 此为已知折衷: OpenCode 无 path 白名单; 靠 prompt 强约束
5. Archer 试图 `task` 创建 Devon subagent —— ✗ OpenCode 拒绝 (permission.task: deny)
```
### scenario-0300 board opencode 透传 permission
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#scenario-0300-board-opencode--permission]
```
$ lk board opencode
generated 12 OpenCode agents
$ head .opencode/agents/warden.md
---
description: 审核人 — ...
mode: subagent
model: ark/deepseek-v4-flash
permission:
bash: allow
read: allow
grep: allow
glob: allow
edit: deny
task: deny
question: deny
webfetch: deny
websearch: deny
external_directory: deny
doom_loop: deny
---
(注意 permission 是 YAML 对象; 其它源 frontmatter 字段 (如 hidden/color) 走 PASSTHROUGH_KEYS 白名单)
```
### scenario-0400 Maestro 自主推进
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#scenario-0400-maestro-]
```
1. 用户在 OpenCode TUI 新建会话: 默认 agent = maestro
2. TUI 顶层 <Leader>a 列表: 仅 maestro 一个 primary 候选
(其余 11 个 role: Sage / Lex / ... 不在 <Leader>a 列表里; 它们 mode: subagent)
3. 用户说 "开始 v0.6-009 实施", maestro 收到指令
4. maestro 查 project.toml 的 `[meta].current_stage` 字段, 决定从哪个阶段起 (fix-002 后)
- 若是新项目 (Stage=F-PENDING) → 调 task 启动 Scout (项目奠基)
- 若是存量项目 (Stage=M-SPEC 等) → 跳过 Scout, 直接调 task 启动 Sage / Devon / ...
5. maestro 调 `task` 工具启动 Scout 子会话 (mode: subagent, 隔离)
6. Scout 执行 Step 1-3 项目奠基; 如需用户输入, **弹框冒泡到 maestro 主窗口**
7. 用户在主窗口看到问题弹框 (含 1/2/3 选项) → 选项回复
8. Scout 继续 → 完成后焦点自动回到 maestro
9. maestro 决策下一步: 调 task 启动 Sage (spec issues) → ... → Devon (TDD) → Archer (test-plan) → Shield (e2e) → Keeper (gate) → Judge (security) → Librarian (wiki) → Maestro 收尾
10. 全程用户不需要按 <Leader>a 切换主代理; subagent 弹框自然冒泡; 控制权始终在 maestro
11. (可选) 用户想看 subagent 实时进度, 按 `<Leader>+Down` 进入子会话查看; 按 `<Leader>+Up` 返回
12. 整个工作流完成, maestro 输出最终总结
```
### scenario-0500 11 subagent 各自权限
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#scenario-0500-11-subagent-]
```
- Scout (mode: subagent, permission.question: allow)   — 交互
- Sage (mode: subagent, permission.question: allow)    — 交互
- Lex (mode: subagent, permission.question: deny)     — 静默 + raw 记录
- Devon (mode: subagent, permission.question: deny)    — 静默 + raw 记录
- Archer (mode: subagent, permission.question: allow)  — 交互
- Shield (mode: subagent, permission.question: deny)  — 静默
- Keeper (mode: subagent, permission.question: deny)  — 静默
- Prism (mode: subagent, permission.question: deny)   — 静默
- Warden (mode: subagent, permission.question: deny)  — 静默
- Judge (mode: subagent, permission.question: allow)   — 交互
- Librarian (mode: subagent, permission.question: deny) — 静默
```
---
## 3. 功能需求
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#3-]
### FR-0010 4 角色 permission 表 (YAML 对象格式)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-0010-4--permission--yaml-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
OpenCode `permission` frontmatter 是 **YAML 对象**，键是工具名，值是 `allow` / `deny` / glob pattern。**未列出的键不默认 deny** —— 必须显式 `deny` 才禁用（与 A-003-4 一致）。
下表是 4 角色的 `permission:` 完整配置。**只列 allow 的键会失效**（OpenCode 会 merge 到全局默认，可能继承 allow），所以每个角色都列出所有相关键。
#### FR-0010.1 Warden (只读审计)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00101-warden-]
```yaml
mode: subagent
permission:
bash: allow
read: allow
edit: deny
grep: allow
glob: allow
task: deny
question: deny
webfetch: deny
websearch: deny
external_directory: deny   # Qwen A-8.2 确认: OpenCode 默认 ask, 显式 deny 避免打断审计
doom_loop: deny            # Qwen A-8.2 确认: OpenCode 默认 ask, 显式 deny
```
#### FR-0010.2 Judge (只读安全审计)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00102-judge-]
```yaml
mode: subagent
permission:
bash: allow
read: allow
edit: deny
grep: allow
glob: allow
task: deny
question: allow      # FR-0070 启用交互
webfetch: deny
websearch: deny
external_directory: deny
doom_loop: deny
```
#### FR-0010.3 Archer (写 spec 产物)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00103-archer--spec-]
```yaml
mode: subagent
permission:
bash: allow
read: allow
edit: allow
grep: allow
glob: allow
task: deny
question: allow      # FR-0070 启用交互
webfetch: deny
websearch: deny
external_directory: deny
doom_loop: deny
```
#### FR-0010.4 Librarian (写 wiki)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00104-librarian--wiki]
```yaml
mode: subagent
permission:
bash: allow
read: allow
edit: allow
grep: allow
glob: allow
task: deny
question: deny       # FR-0070 deny
webfetch: deny
websearch: deny
external_directory: deny
doom_loop: deny
```
#### FR-0010.5 OpenCode permission 键白名单
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00105-opencode-permission-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
OpenCode `permission` 支持的键（Qwen A-003-3 + A-8.2 确认）：
`read`, `edit`, `glob`, `grep`, `bash`, `task`, `skill`, `lsp`, `question`, `webfetch`, `websearch`, `external_directory`, `doom_loop`
`todowrite` **不在白名单**（OpenCode 内部控制，不通过 permission 配置）。FR-0060.1 中 Maestro 的 `permission` 也必须不含 `todowrite`。
---
### FR-0020 source frontmatter 落地
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-0020-source-frontmatter-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
在以下 5 个 source agent prompt 文件的 YAML frontmatter 中加 `permission:` 字段（位于 `models:` 之后）+ 改 `mode:`：
- `agents/Warden.md` — FR-0010.1
- `agents/Judge.md` — FR-0010.2
- `agents/Archer.md` — FR-0010.3
- `agents/Librarian.md` — FR-0010.4
- `agents/Maestro.md` — FR-0060.1（含 `task` 调子代理）
特别说明：
- 其余 7 个 agent (Sage / Lex / Devon / Scout / Shield / Keeper / Prism) 在 FR-0020 中**不加完整 `permission:` 块**；FR-0070 会为其追加最小 `permission:` 块（仅 `question: deny`），其余字段仍走 OpenCode 全局默认
- 7 个 agent **仍**改 `mode: all` → `mode: subagent` (FR-0060.2)
- FR-0070 会给 4 个交互式 subagent 加 `permission.question: allow`
---
### FR-0030 board opencode 透传白名单字段
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-0030-board-opencode-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
`louke/board.py` 当前 `cmd_opencode()`（`board.py:80`）**只**输出 `description` / `mode` / `model` 三个字段，其它 frontmatter 字段被**静默丢弃**。本 FR 要求：
- 维护**透传白名单** `PASSTHROUGH_KEYS`，白名单内的字段从 source frontmatter 原样复制到生成文件
- `model` 走 `resolve_model()` 重写
- `description` 走 `fm.get('description')` 提取
- `mode` 走 `fm.get('mode')` 透传（FR-0060.2 关键，确保 `mode: subagent` 不被改回 `all`）
- 不在白名单的字段：丢弃；dry-run 时打印 `[!] dropped unknown frontmatter key '<key>' from <agent>`
**白名单初值**（基于 OpenCode 文档列出的字段 + permission）：
```python
PASSTHROUGH_KEYS = {
'description',  # 但 board.py 已处理
'mode',         # 但 board.py 已处理（需透传不重写）
'model',        # 但 board.py 已重写
'permission',   # FR-0010/0020/0060.1 落地
'hidden',       # OpenCode 支持
'color',        # OpenCode 支持
'temperature',  # OpenCode 支持
'top_p',        # OpenCode 支持
'steps',        # OpenCode 支持
'disable',      # OpenCode 支持
}
```
**安全考虑**（A-008-2 风险）：未列白名单的字段不传，避免调试字段泄露到 LLM provider 作为模型参数。
实现位置：`louke/board.py` `cmd_opencode` 内 frontmatter 构造逻辑（约 lines 70-90）。
---
### FR-0040 `lk agent lint` 校验
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-0040-lk-agent-lint-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
**新增**子命令 `lk agent lint`，与 `lk archer ci-scan` / `lk librarian lint` 平行（采纳 A-009-2 建议）。职责：
1. **schema 校验**（exit 1 if fail）：
- 必填 `name`, `description`, `mode`, `models`（至少 1 个元素）
- 4 角色 (Warden / Judge / Archer / Librarian) 必填 `permission` (YAML 对象)
2. **permission 内容校验**（exit 1 if fail）：
- `permission` 是 YAML 字典（非字符串 / 非列表）
- 所有键 ∈ OpenCode 白名单 (FR-0010.5)
- 值 ∈ {`allow`, `deny`} 或 glob pattern 字符串
3. **mode 单一性约束**（exit 1 if fail，采纳 NFR-0050）：
- `agents/*.md` 中 `mode: primary` 数量 = 1（白名单 = `maestro`）
- `mode: all` 数量 = 0（已废弃用法）
- `mode: subagent` 数量 ≥ 1
4. **board.py 集成**：lint exit 0 → `lk board opencode` 生成的 frontmatter 与 source 一致（不丢字段）
**实现位置**：`louke/agent.py`（新建文件），`lk agent lint` 走 `lk` CLI 已有子命令模式。
**与 `lk archer ci-scan` 的分工**：
- archer ci-scan: spec ↔ test 双向追溯 + test anti-pattern
- agent lint: agent frontmatter schema + permission 验证
- 两者独立, 通过 `lk ci` 统一调度
---
### FR-0050 文档同步
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-0050-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
- **README.md + README.zh.md**：
- 在"agent 角色"章节加"Agent 权限矩阵"小表（4 角色 + 7 默认 + Maestro）
- 加"分层编排 (Layered Orchestration)"小节, 解释:
- 唯一主代理 = Maestro (mode: primary)
- 11 个专业角色 = Maestro 的 subagent (mode: subagent)
- 用户工作流: <Leader>a 切到 Maestro → 启动会话 → Maestro 调 `task` 委派 → 子代理交互在子会话窗口
- ✅ subagent 的 `question` 弹框出现在 maestro 主会话窗口，用户在主窗口选项回复即可，无需按 `<Leader>+Down` 进入子会话
- **4 个 agent prompt** (Warden / Judge / Archer / Librarian)：在"你不是来"段落之后加一段"## 你的工具"显式说明
- **`agents/Maestro.md`**：加"## 你的编排模式"段落
---
### FR-0060 Maestro 全权工作流控制
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-0060-maestro-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
#### FR-0060.1 Maestro `mode: primary` + `permission:` 显式声明
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00601-maestro-mode-primary--permission-]
`agents/Maestro.md` frontmatter 改：
```yaml
mode: primary                    # 改: all → primary, 防止被 subagent 递归调用 (A-010-4 risk 4)
models:
- minimax-m3
- glm-5.2
permission:
bash: allow
read: allow
edit: allow
grep: allow
glob: allow
task: allow                    # 调 subagent (核心)
question: deny                 # Maestro 不向用户提问 (上层协调者, 不需要)
webfetch: allow                # 查 GitHub issue / 外部参考
websearch: deny
skill: deny
lsp: deny
external_directory: ask        # Qwen A-8.2 确认: 子代理可能需要访问外部目录, 向用户确认
doom_loop: deny                 # Qwen A-8.2 确认: Maestro 自身不应陷入 doom loop
```
不含 `todowrite` (A-010-4 risk 2: 不在 OpenCode permission 白名单)。
不含 `question: allow` (Maestro 是协调者, 不亲自提问; 如需用户输入, 通过 subagent `question: allow` 转发)。
#### FR-0060.2 其余 11 个 agent `mode: subagent`
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00602--11--agent-mode-subagent]
11 个 agent frontmatter `mode: all` → `mode: subagent`：
- `agents/Sage.md`
- `agents/Lex.md`
- `agents/Devon.md`
- `agents/Scout.md`
- `agents/Shield.md`
- `agents/Keeper.md`
- `agents/Prism.md`
- `agents/Archer.md` (FR-0010.3 4 角色之一)
- `agents/Warden.md` (FR-0010.1 4 角色之一)
- `agents/Judge.md` (FR-0010.2 4 角色之一)
- `agents/Librarian.md` (FR-0010.4 4 角色之一)
OpenCode `mode: subagent` 文档语义（Qwen A-001-2 确认）：
- 不在 Tab 循环列表
- 不在 `<Leader>a` agent 列表
- 只能通过 `task` 工具调用或 `@` 提及
#### FR-0060.3 默认 agent
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00603--agent]
`lk init` 生成的 `opencode.json` (项目级) 与 `~/.config/opencode/opencode.json` (全局) 确保 `"default_agent": "maestro"` (复用 v0.6-008 FR-0300)。
#### FR-0060.4 board.py 透传 `mode:` 字段
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00604-boardpy--mode-]
`board.py` 当前不重写 `mode` 字段, 但 `cmd_opencode` 构造 frontmatter 时只输出固定模板 (FR-0030 改进). 本 FR 与 FR-0030 联动, 确保 `mode: subagent` 透传 (不被改回 `mode: all`)。
#### FR-0060.5 文档: 分层编排模式
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00605--]
- **README**: "分层编排"小节 (FR-0050 已列)
- **`agents/Maestro.md`** prompt 加"## 你的编排模式"段落:
> 你是 TUI 顶层唯一的 primary agent (mode: primary)。通过 `task` 工具调 Sage / Lex / Devon / Scout / Archer / Shield / Keeper / Prism / Warden / Judge / Librarian 11 个 subagent。subagent 在隔离的子会话里运行, 需要用户输入时调 `question` 工具弹框到主会话窗口。用户在主窗口选项回复即可，无需按 `<Leader>+Down` 进入子会话；用户若想查看实时进度，仍可手动 `<Leader>+Down` 进入子会话。subagent 完成后焦点自动回到你。**不要**让用户在 `<Leader>a` 切其它主代理。
- **11 个 subagent prompt** 加"## 你的身份"段落:
> 你是 subagent (mode: subagent), 由 Maestro 调起; 用户不在 TUI 顶层切换到你。你在子会话里运行; 如需向用户提问, 调 `question` 工具 (前提: 你的 `permission.question: allow`)。
---
### FR-0070 交互式 subagent (v0.3.0)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-0070--subagent-v030]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ (IDE 实测通过) | ✅ |
**背景**：OpenCode **不支持** `interactive: true` 字段 (Qwen A-002-1)，实际机制是 `permission.question: allow/deny`。本 FR 由此重构。
**5 分钟 IDE 实测基线** (详见 `.louke/qwen-review-v0.6-009.md` §10)：
- subagent 调用 `question` 工具时，弹框（含 1/2/3 选项）**冒泡到 maestro 主会话窗口**
- 用户在主窗口选项回复，无需按 `<Leader>+Down` 导航
- subagent 完成后焦点自动回 maestro
- A-001-4 唯一 blocker 消除 → FR-0070 合并入 v0.3.0
#### FR-0070.1 交互式需求识别 (Q6: 选 A, 4 个 allow + 7 个 deny + Maestro deny)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00701--q6--a-4--allow--7--deny--maestro-deny]
| Agent | permission.question | 理由 |
|---|---|---|
| **Scout** | `allow` | 项目奠基: repo owner / 版本 / spec-id 等必问 |
| **Sage** | `allow` | spec 澄清: 档位 / AC 边界 / 需求冲突 |
| **Archer** | `allow` | test-plan / architecture trade-off 选型 |
| **Judge** | `allow` | severity 校正 / finding 豁免 |
| Lex | `deny` | 保守判定 + raw 记录"待人工确认" |
| Devon | `deny` | fixtures 模板 + 最保守实现 |
| Shield | `deny` | 全自动测试生成 |
| Keeper | `deny` | 质量门禁全自动 |
| Prism | `deny` | code review 全自动 |
| Warden | `deny` | 列出原文 + 推论 + 报告 |
| Librarian | `deny` | 默认分类 + log 标记"待人工确认" |
| **Maestro** | `deny` | 协调者不亲自提问; 通过 subagent `question: allow` 转发 (FR-0060.1) |
#### FR-0070.2 frontmatter 落地 (v0.3.0 实际配置)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00702-frontmatter--v030-]
4 个交互式 subagent (Scout / Sage / Archer / Judge) 加 `permission.question: allow`；7 个非交互式 subagent + Maestro 加 `permission.question: deny`。完整 `permission:` 表见 acceptance.md AC-FR0070-1。
> ⚠️ 4 角色 (Warden / Judge / Archer / Librarian) 的 `permission` 块已在 FR-0010 定义，本 FR 仅添加 `question` 键；不与 FR-0010 冲突。
#### FR-0070.3 文档化 — 方案 (b) prompt 与 config 同步 (Qwen A-8.3 采纳)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00703----b-prompt--config--qwen-a-83-]
为避免 v0.3.0 期间"prompt 说能交互, config 实际不能"的 UX bug (Qwen 二轮指出的关键问题)，4 个交互式 subagent 的 prompt 写"交互式"行为，与 `permission.question: allow` 配置严格一致：
4 个交互式 subagent 的 v0.3.0 prompt ("## 你的交互能力" 段落)：
> 你是交互式 subagent (`permission.question: allow`)。执行中如需人类决策，调 `question` 工具在主会话窗口弹框（含选项式问题）。弹框冒泡到 maestro 主窗口，用户在主窗口选项回复即可，无需导航到子会话。用户回答后你继续执行；完成后焦点自动回到 Maestro (你的调用者)。
7 个非交互式 subagent 的 v0.3.0 prompt ("## 你的非交互身份" 段落)：
> 你是非交互式 subagent (`permission.question: deny`)。执行中不向用户提问；遇到不确定按合理默认继续，并在 raw session 里记录"假设 + 理由"，由 Maestro 或用户事后 review。
#### FR-0070.4 Maestro prompt 补充 (v0.3.0 明确区分)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00704-maestro-prompt--v030-]
`agents/Maestro.md` "## 你的编排模式" 段落显式区分：
> 11 个 subagent 中，Scout / Sage / Archer / Judge 4 个是**交互式**的 (`permission.question: allow`)，他们会在执行中向用户提问；你**不需要**预先收集这些信息，调起时无需带问题清单。其它 7 个 subagent (Lex / Devon / Shield / Keeper / Prism / Warden / Librarian) 是非交互式的 (`permission.question: deny`)，他们按合理默认继续执行；不确定项在 raw session 记录，由你事后 review 报告。
>
> **弹框冒泡保证**：subagent 的 `question` 弹框会出现在主会话窗口，用户在主窗口选项回复即可。你不需要导航到子会话。
#### FR-0070.5 必填交互 agent 的 question 场景表 (v0.3.0 落地)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00705--agent--question--v030-]
| Agent | 正常路径 | Error Path |
|---|---|---|
| **Scout** | repo owner / repo name / initial version / spec-id / release branch | GitHub API 权限不足 → "无写权限，改用手动 `gh auth login` 后重试?" |
| **Sage** | FR 档位 / AC 边界 / 需求冲突 | spec 内部矛盾 (FR-100 vs FR-200) → "已检测到 N 处矛盾，优先级: A 覆盖 B / B 覆盖 A / 升级人类?" |
| **Archer** | 测试策略 / 架构 trade-off | 多个 spec-id 同时存在 → "按 spec-id 优先级 A > B > C 处理?" |
| **Judge** | severity 校正 / finding 豁免 | 找到 critical 但用户已决定"接受风险" → "豁免理由: ________" (留 raw 记录) |
4 个交互式 subagent 的 prompt 中**显式列出**此表格，避免漏问 / 多问。
#### FR-0070.6 5 分钟 IDE 实测基线 (NFR-0040 子项)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00706-5--ide--nfr-0040-]
v0.3.0 release 前**必须**做一次 5 分钟 IDE 实测，确认以下 5 项（实测模板）：
```
FR-0070 实测: 2026-MM-DD HH:MM by Aaron/Kilo
1. <Leader>a agent 列表: [ ] 仅 maestro (符合 FR-0060.2)
2. Maestro 调 task 启动 Scout: [ ] Scout 子会话创建成功
3. Scout 调 question 工具: [ ] 弹框冒泡到主窗口 / [ ] 需 <Leader>+Down
4. 用户选项回复后: [ ] Scout 继续执行
5. Scout 完成后: [ ] 焦点自动回 Maestro, 全程未按 <Leader>a
结论: [ ] FR-0070 可放心落地 / [ ] 需 README 警告 / [ ] 退回方案
```
实测结果记录在 `.louke/qwen-review-v0.6-009.md` §10 + v0.6-009 spec 文件头。
#### FR-0070.7 Subagent 调度方式 (clarification, 2026-07-04)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#fr-00707-subagent--clarification-2026-07-04]
> 2026-07-04 Aaron 测试发现: `opencode run --agent <name>` (CLI) 和 OpenCode `task` 工具 (TUI 内部) 是两种不同层面的操作, 容易混淆. 本节明确 Louke 走哪条.
**Louke 唯一的 subagent 模式**:
- **生产模式** (默认, 唯一): OpenCode TUI 里 Maestro 当 primary → 调内置 `task` 工具 → 启动 subagent 隔离子会话
- **禁止**用 `opencode run --agent <name>` 调子 agent (那是 OpenCode CLI 模式, 让 `<name>` 作为 primary 在新 session 跑, 不算 subagent 模式)
| 模式 | 调用者 | `<name>` 角色 | 父窗口 | `question` 行为 | 适用 |
|---|---|---|---|---|---|
| `task` 工具 (生产) | OpenCode 内置 (Maestro 调) | subagent | Maestro | 弹框冒泡到 Maestro | Louke 工作流 (M-FOUND → M-SPEC → ...) |
| `opencode run --agent <name>` (CLI) | 用户 / 脚本 | primary | 无 (新 session) | 弹在 `<name>` 自己窗口 / stdout | 单独验证 / CI / 批处理 |
**实施规则**:
- `agents/Maestro.md` prompt **显式**写"只**用 `task` 工具调子 agent, **不要**用 `opencode run`" (v0.6.10 已加)
- 其它 11 agent prompt 维持现状: "你是 subagent, 由 Maestro 调起"
- 验证 subagent 行为 (如 question 冒泡) 必须用 OpenCode TUI, 不能用 CLI 测 (CLI 测不到冒泡是设计, 不是 bug)
**Aaron 的测试澄清**:
- `opencode run --agent sage "..."` 是 CLI 模式, sage 作 primary, question 不冒泡 (符合设计)
- TUI 里 Maestro → task → Sage 模式才会冒泡 (OpenCode 内置行为)
---
## 4. 非功能需求
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#4-]
### NFR-0010 向后兼容 (含 breaking change 显式声明)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#nfr-0010---breaking-change-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
⚠️ **Breaking change 显式声明**: 升级 v0.6-009 后, 用户的 `<Leader>a` 列表从 "12 agent" 变为 "仅 Maestro"。
未加完整 `permission:` 块的 7 个非交互式 subagent (Sage / Lex / Devon / Scout / Shield / Keeper / Prism) 在 v0.3.0 仅含 `permission.question: deny` 最小块，其余字段仍走 OpenCode 全局默认；若用户的 `~/.config/opencode/opencode.json` 设置了宽松默认，这 7 个 agent 仍可调用 `question` 之外的工具（这与 spec 期望“白名单默认 deny”不符，但属 v0.6-010+ 完整 `permission` 块范畴）。
`lk board opencode` 生成的 `.opencode/agents/{name}.md` 文件:
- 4 目标角色 → 含完整 `permission:` 块 (YAML 对象)
- Maestro → 含完整 `permission:` 块 (FR-0060.1)
- 其余 7 个 → 含最小 `permission:` 块（仅 `question: deny`），其余字段走 OpenCode 全局默认
**用户感知**:
- 升级前: 12 agent 顶层可见
- 升级后: 1 agent 顶层可见 (Maestro), 其它需通过 Maestro `task` 调
- 影响范围: 习惯于直接切 Sage/Devon 写代码的用户, 需要适应新工作流
### NFR-0020 不影响 lk models / lk init
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#nfr-0020--lk-models---lk-init]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
本 spec 不修改 `lk models` (属 v0.6-008 FR-0201 范围) 和 `lk init` 主体行为 (属 v0.6-008 §1 范围)。`lk init` 生成的 `opencode.json` 加 `"default_agent": "maestro"` 已在 v0.6-008 FR-0300 覆盖。
### NFR-0030 文档语言
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#nfr-0030-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
README / README.zh 双语同步; agent prompt 段落统一中文。
### NFR-0040 可降级 + OpenCode 版本检查
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#nfr-0040---opencode-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
`mode: subagent` 已通过文档确认支持 (A-001-2), **不需要回退**; FR-0060.2 可放心落地。
`permission.question` 控制 subagent 交互 (替代 `interactive: true`): OpenCode 文档明确支持 `permission` 字段的 `question` 键, 无需回退。
**OpenCode 版本检查** (采纳 A-007-1 建议): `lk agent lint` 加 `--check-opencode-version` flag (默认 off):
- 读 `opencode --version` 输出
- 与 `louke/__init__.py` 的 `MIN_OPENCODE_VERSION` 常量对比
- 低版本打印 warning, 但不阻塞 lint
`MIN_OPENCODE_VERSION = "1.1.1"` (Qwen A-8.4 校准: `permission` 对象格式替代 deprecated `tools` 布尔字段的引入版本; 低于此版本用户生成的 frontmatter 会被 OpenCode 忽略或报错)
### NFR-0050 单一 primary agent 约束
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#nfr-0050--primary-agent-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
升级本 spec 后, louke agent 集合**必须**只有 1 个 `mode: primary` (Maestro), 其余 11 个均为 `mode: subagent`。`lk agent lint` (FR-0040) 强制检查:
- `agents/*.md` 中 `mode: primary` 数量 = 1 (白名单 = maestro)
- `mode: all` 数量 = 0
- 否则 lint exit 1, stderr 含 `only maestro can be primary; found {N} agents with mode: primary/all`
---
## 5. 澄清记录 (Qwen 反馈后, Kilo 决定)
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#5--qwen--kilo-]
| Q | 议题 | Qwen 建议 | Kilo 决定 |
|---|---|---|---|
| Q1 (FR-0010 权限表) | 4 角色 permission 集合 | ✅ 已通过 (但字段名错, A-003) | 接受 A-003 重构, 详见 FR-0010 |
| Q2 (FR-0030) | 8 个非目标 agent 要不要显式 `permission: all` | 默认否 | 维持 (v0.3.0 不动, v0.6-010+ 再加) |
| Q3 (FR-0040) | lint 集成点 A/B/C | (B) `lk agent lint`, 先用 (C) PoC | 采纳 (B) + 直接落地, 不走 PoC 阶段 (工作量不大) |
| Q4.1 (FR-0060.2) | 11 agent 改 `mode: subagent` | ✅ 文档已确认 | 接受 |
| Q4.2 (FR-0060.1) | Maestro `permission` 集合 | (含 `task` / `webfetch` / 不含 `websearch` / `lsp` / `skill`) | 接受, 同时不含 `todowrite` (A-010-4 risk 2) |
| Q4.3 (NFR-0040) | 回退机制 | 改成"重构" + 加版本检查 | 接受 |
| Q5 (FR-0060.5 文档) | 11 subagent prompt 加"## 你的身份" | 默认 | 接受 |
| Q6 (FR-0070 交互式集合) | 4 vs 8 vs 11 | (A) 4 个 | 接受 (A), 详见 FR-0070.1 |
| **Q7 (A-004-1)** | v0.6-008 FR-0200 加 supersede 注释 | 加 `> ⚠️ SUPERSEDED by v0.6-009 FR-0060.2` | 接受, 实施 |
| **Q8 (A-006-1)** | AskUser 场景表加 Error Path | 加列 | 接受, 详见 FR-0070.5 |
| **Q9 (A-007-3)** | README "已知限制" 子段 | 加 | 接受, 详见 FR-0050 |
| **Q10 (A-008-3)** | board.py 透传白名单 | PASSTHROUGH_KEYS 维护 | 接受, 详见 FR-0030 |
| **Q11 (A-009-2)** | lint 工具名 `lk agent lint` | 接受 | 接受 |
| **Q12 (A-010-3)** | v0.3.0 / v0.3.1 拆分 | 拆分, FR-0070 推迟 | **已修订**：2026-07-03 14:00 IDE 实测通过, FR-0070 合并入 v0.3.0, 详见 §0.4 |
| **Q17 (实测结果)** | A-001-4 subagent `question` 冒泡 | Aaron IDE 实测通过 | 接受, FR-0070 全家合并 v0.3.0 |
| **Q13 (A-010-4 risk 4)** | Maestro `mode: all` → `mode: primary` | 改 | 接受, 详见 FR-0060.1 |
| **Q14 (Qwen 二轮 A-8.2)** | 4 角色 + Maestro 加 `external_directory` / `doom_loop` 显式 deny/ask | 接受 | 详见 FR-0010.1~0010.4 + FR-0060.1 |
| **Q15 (Qwen 二轮 A-8.3)** | FR-0070.3/0070.4 方案 (b): v0.3.0 prompt 与 config 同步非交互 | 接受 | 详见 FR-0070.3/0070.4 |
| **Q16 (Qwen 二轮 A-8.4)** | `MIN_OPENCODE_VERSION = "1.1.1"` | 接受 (Qwen 校准准确) | 详见 NFR-0040 |
---
## 6. 关联文件
[source: project/specs/v0.6-009-agent-permission-tightening/spec.md#6-]
| 文件 | 改动 |
|---|---|
| `agents/Warden.md` | 加 frontmatter `mode: subagent` + `permission: { ... }` (FR-0010.1) + "你的工具"段落 (FR-0050) + "你的身份"段落 (FR-0060.5) + "非交互身份"段落 (FR-0070.3) |
| `agents/Judge.md` | 同上 + permission 含 `question: allow` (FR-0010.2) + "你的交互能力"段落 (FR-0070.3) + AskUser 场景表 (FR-0070.5) |
| `agents/Archer.md` | 同 Warden + permission 含 `edit: allow, question: allow` (FR-0010.3) |
| `agents/Librarian.md` | 同 Warden + permission 含 `edit: allow` (FR-0010.4) |
| `agents/Maestro.md` | 改 `mode: all` → `mode: primary` (FR-0060.1) + `permission: { task: allow, ... }` + "你的编排模式"段落 (FR-0060.5) + subagent 交互模式说明 (FR-0070.4) |
| `agents/{Scout,Sage}.md` | `mode: all` → `mode: subagent` (FR-0060.2) + "你的身份"段落 (FR-0060.5) + "你的交互能力"段落 (FR-0070.3) + AskUser 场景表 (FR-0070.5) |
| `agents/{Lex,Devon,Shield,Keeper,Prism}.md` | `mode: all` → `mode: subagent` (FR-0060.2) + "你的身份"段落 (FR-0060.5) + "你的非交互身份"段落 (FR-0070.3) |
| `louke/board.py` | `cmd_opencode` 改用 `PASSTHROUGH_KEYS` 透传白名单 (FR-0030) + 透传 `mode:` (FR-0060.4) |
| `louke/agent.py` | **新建**: `lk agent lint` 实现 (FR-0040) |
| `louke/__init__.py` | 加 `MIN_OPENCODE_VERSION = "1.1.1"` (NFR-0040) |
| `louke/archer.py` | 无改动 (lint 移走) |
| `README.md` / `README.zh.md` | 加"Agent 权限矩阵"小节 (FR-0050) + "分层编排"小节 (FR-0060.5) + "已知限制" (FR-0050) |
| `.louke/project/specs/v0.6-008-louke-v030-usability-closure/spec.md` | FR-0200 段落加 `> ⚠️ SUPERSEDED by v0.6-009 FR-0060.2 (2026-07-03)` 注释 |
| `tests/test_agent_frontmatter.bats` | 新增: FR-0010/0020/0030/0040/0060 校验 + NFR-0050 单一 primary 约束 |

## v0.6-016-quote-dialogue-protocol

# v0.6-016 — Quote Dialogue Speaker-Tag 协议 — Spec (SUPERSEDED)
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#v06-016--quote-dialogue-speaker-tag---spec-superseded]
```yaml
valid: false
superseded-by: v0.7-003-inline-discussion-protocol
```
- **Spec ID**: v0.6-016-quote-dialogue-protocol
- **创建日期**: 2026-07-04
- **状态**: **SUPERSEDED** (被 v0.7-003 替代)
- **作者**: Kilo (受 GLM 委托, 见 `.louke/review-sage-question-tool.md` §7.0)
- **关联**:
- 既有规范: v0.4-004-quote-dialogue (quote dialogue 流程)
- 关联 issue: [#XX] Quote Dialogue 协议正式化
- Aaron 2026-07-04 决定: 把 Sage.md Step 3 大段例子外提为规范
## 0. 范围与边界
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#0-]
### 0.1 本 spec 收纳
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#01--spec-]
| 主题 | FR 范围 |
|---|---|
| Quote Dialogue 协议语法 | FR-0010 ~ FR-0030 |
| louke 12 个 agent 全部学习该协议 | FR-0040 |
| 用户文档 (cookbook) 教用户写 quote reply | FR-0050 |
| 与 v0.4-004 quote dialogue 流程的边界 | §0.2 |
### 0.2 supersede 关系
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#02-supersede-]
- **v0.4-004-quote-dialogue FR-010 (quote-block 语法识别)**: 仍有效, **不替代**. 本 spec 在其基础上**扩展** speaker-tag 协议 (Quote Dialogue 的子组件).
- **v0.4-004-quote-dialogue FR-020+ (quote dialogue 流程)**: 仍有效, **不替代**. 流程由 v0.4-004 定义, 语法由本 spec 定义.
- **agents/Sage.md L37-41 (Quote Dialogue 速查表)**: 草稿级, **本 spec 替代**. 后续 Sage.md 引用本 spec.
- **agents/Lex.md 自由使用 `> **Lex:**`**: 不规范, **本 spec 替代**. Lex.md 后续引用本 spec.
- **README.md / cookbook.md 关于 quote 协议的描述**: 当前不存在, 本 spec FR-0050 补上.
### 0.3 本 spec 不收纳
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#03--spec-]
- quote_parser.py 解析器实现 (v0.4-004 FR-010 已覆盖)
- quote dialogue 流程 (v0.4-004 已覆盖, 重新引用)
- 其它 markdown 扩展语法 (tables, alerts 等) — 与本协议无关
---
## 1. 用户故事
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#1-]
<a id="us-0010"></a>
### US-0010
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#us-0010]
story: 作为 louke 用户, 我想在 IDE 里用标准 markdown 直接与 agent 多轮对话, 不需要装额外扩展.
priority: P0
---
## 2. 功能需求
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#2-]
> **编号约定(必读)**: FR 编码采用 4 位数字, 0 填充, 步长 10 (FR-0010, FR-0020, ...).
> **必读**: FR-XXXX 编号即该需求的 id. 禁止删除, 废弃标 `valid: false`.
<a id="fr-0010"></a>
### FR-0010 Quote Dialogue 协议正式语法
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#fr-0010-quote-dialogue-]
**正式名称**: **Quote Dialogue Protocol (QDP)** — 嵌套 markdown blockquote 上携带的**轻量级发言者标识** (speaker-tag), 借自 email/usenet 传统
(markdown `>` 直接源自 email `>`, 嵌套 `>>` = reply, 嵌套 `>>>` = reply-to-reply).
**语法形式**:
```markdown
> **SpeakerName:** {comment content}
```
- `>` 起始 (block quote marker, 见 CommonMark §5.1)
- 后接一个空格
- 然后 `**{SpeakerName}:`** — SpeakerName 是发言者的人/agent 标识 (粗体 + 冒号)
- 然后一个空格
- 然后 comment 内容
**SpeakerName 取值**:
- 用户: 用户自定义名 (例: `Aaron`, `Bob`, `张三`)
- louke agent: agent 角色名 (例: `Sage`, `Lex`, `Archer`, `Maestro`, `Judge`)
- 任意第三方 (其它 agent 或人类): 任意字符串
**嵌套规则**:
- `> **A:**` = 第 1 级 (A 的原话)
- `>> **B:**` = 第 2 级 (B 对 A 的回复)
- `>>> **A:**` = 第 3 级 (A 对 B 的回复)
- 嵌套层级仅指示**对话链的深度**, 不指示谁回复谁 (回复对象由阅读者根据上下文判断)
- 实际使用中, 嵌套通常 1-3 级足够, 4+ 级建议拆为新 FR 单元
**与 v0.4-004 quote-block 的关系**:
- v0.4-004 定义了 `> **Name:**` 的**解析** (speaker 提取, depth 计数)
- 本 spec 定义了 `> **Name:**` 的**语义** (谁是发言者, 多轮对话如何展开)
- 解析器和协议是同一个东西的两面, 协议替代解析器实现细节
**AC**:
- AC-1: spec.md 内任意 `> **Name:**` 块可被 quote_parser.py 解析为 (speaker, depth, content) 三元组
- AC-2: 嵌套 `>> **B:**` 的 depth = 2
- AC-3: SpeakerName 大小写敏感 (例: `Sage` ≠ `sage`)
- AC-4: 紧邻 `**Name:**` 后的内容 (一行内) 视为 speaker 的原话; 跨行内容视为延续 (CommonMark lazy continuation)
<a id="fr-0020"></a>
### FR-0020 三种 quote 类型语义区别
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#fr-0020--quote-]
spec.md 中可出现三类 quote, 语义**不同**:
| 语法 | 语义 | 渲染 | 用途 |
|---|---|---|---|
| `> **SpeakerName:** content` | 角色对话 | 可见 (引用块) | agent ↔ 用户 ↔ 其它 agent 之间的多轮讨论 (本 spec 主用途) |
| `> [note] content` | 公开备注 | 可见 (引用块) | 单向说明, 不属于对话链 (如"本节待 Sage 第二轮补全") |
| `<!-- content -->` | agent 内部笔记 | **不可见** (HTML 注释) | agent 自己的草稿/待办, 不进 spec 终稿 |
**为什么 `[note]` 用方括号**: 避免被误以为是名为 "Note" 的 user/agent 的评论. `**Speaker**` 走粗体格式, `[note]` 走方括号格式, 视觉上立即区分.
**为什么 `<!-- -->` 必须隐藏**: agent 草稿不应进 git 历史 (如"我担心这个 FR 用户会反对, 但不敢说"). 见 NFR-0020.
**AC**:
- AC-1: parser 区分三类 (对话/备注/草稿), 仅前两类进 spec 终稿
- AC-2: 任意 `<!--` 开头的行被 parser 视为内部笔记, 不进 quote dialogue 链
- AC-3: `[note]` 解析为 note 角色, 不带 speaker (避免与"名为 Note 的用户"冲突)
<a id="fr-0030"></a>
### FR-0030 quote dialogue 多轮协议
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#fr-0030-quote-dialogue-]
**调用前提**: 已存在 v0.4-004 FR-010 定义的 quote_parser.py 解析能力. 本 spec 仅定义**多轮对话的展开规则**.
**单轮操作** (Sage/Lex/Archer 任一 agent 在 IDE 中):
1. 解析当前 spec.md, 找到所有 open 的 quote (depth, speaker, content)
2. 对每个 open quote 判断:
- 是自己之前的问题 → 看用户是否在嵌套 `>>` 里回复; 没回复就**追问一次** (不擅自决定)
- 是用户对自己的提问 → 在 `>>>` 嵌套里回答
- 是用户对其它 agent 的提问 → 跳过, 不越权
3. 操作完做一次 commit + push, 让下一轮能拿到 diff
**退出条件** (单步操作后):
1. 无 open quote 残留
2. 所有受影响 FR 的 `是否已决定` 字段为 `✅`
3. spec.md 已 commit + push
**AC**:
- AC-1: agent 完成一轮 quote dialogue 后, `git log --oneline` 多一个新 commit
- AC-2: agent 不在 chat 里发纯文字回复 (违反协议 — 必须在 spec.md 里留 quote)
- AC-3: agent 不擅自把 `⚠️` 改为 `✅` (严禁沉默即同意)
<a id="fr-0040"></a>
### FR-0040 louke 12 个 agent 引用 QDP
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#fr-0040-louke-12--agent--qdp]
**所有 agent 的 prompt 应在身份段（frontmatter 后第一段）以"何时使用"开头**引用单一信息源 `agents/_protocols/quote-dialogue.md`:
**统一模板** (L18 上下, 紧跟身份段):
```markdown
> **引用**: 当你需要 [本 agent 角色相关的触发场景] 时, 请参考本目录 [`_protocols/quote-dialogue.md`](_protocols/quote-dialogue.md) 的语法.
```
**措辞硬约束**:
- 必须以 "当你需要..." 开头 (动作触发, 避免被动描述"如需...")
- 必须说明**本 agent 角色**的典型使用场景 (e.g. Sage = 与用户多轮澄清, Lex = 对 spec 留审查意见)
- 不能在 prompt 内部重复 QDP 语法定义 (避免与单一信息源不一致)
- 12 个 agent 全部应遵守, 包括 `question: deny` 的非交互式 subagent (它们可能在被动收到 quote dialogue 时需要解析)
**各 agent 当前的"触发场景"** (作为基线, 后续可微调但**不能退回**到被动描述):
| Agent | 触发场景 (短) |
|---|---|
| Sage | 与用户多轮澄清 FR/NFR 边界、或在 spec.md 留 quote dialogue 历史 |
| Lex | 对 spec.md 追加结构化审查意见 (替代 PR review / chat 纯文字) |
| Archer | 就 test-plan.md / interfaces.md 发起多轮澄清、或在 spec.md 留测试问题 quote |
| Maestro | 多 agent 协作上下文以 quote dialogue 形式留痕在 spec.md / test-plan.md |
| Scout | 在 spec.md 中向用户/agent 留言、补充项目初设疑问 |
| Devon | 在 raw session 里留下 quote dialogue 历史 (让下游追溯实现决策) |
| Prism | 在 review 报告中引用 spec quote dialogue、或在 spec.md 留审查 quote |
| Keeper | 在门禁报告中留 quote dialogue (让 Sage 后续 review 时看到出处) |
| Shield | 在 e2e 报告中引用 spec quote dialogue 上下文 |
| Judge | 在审计报告中引用 spec quote dialogue 上下文 (攻击面 / 边界讨论) |
| Warden | 在 spec.md / acceptance.md 中留 quote 形式验收意见 |
| Librarian | 在 wiki 蒸馏 raw 段时保留 quote dialogue 上下文 (避免断章取义) |
**单一信息源的分发机制**:
- `agents/_protocols/quote-dialogue.md` 通过 `pyproject.toml` 的 `package-data` 配置 (`agents/_protocols/*.md`) 一起打包到 `site-packages/louke/agents/_protocols/`
- 用户装的 louke 里**没有** `.louke/project/specs/...` 路径, 引用必须指向 `_protocols/` 才能被 agent 看到
**AC**:
- AC-1: `grep -l '_protocols/quote-dialogue.md' agents/*.md` 返回 12 个文件
- AC-2: 每个 agent prompt 不再独立定义 Quote Dialogue 语法 (避免与 `_protocols/quote-dialogue.md` 不一致)
- AC-3: `tests/test_agent_frontmatter.bats` 加测试, 验证所有 12 agent 含 `_protocols/` 引用
- AC-4: 12 个 agent 引用行均以 "当你需要" 开头 (新增 — 防止退回被动描述)
- AC-5: `pyproject.toml` 的 `package-data` 含 `agents/_protocols/*.md`
<a id="fr-0050"></a>
### FR-0050 用户文档 (cookbook) 教用户写 quote reply
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#fr-0050--cookbook--quote-reply]
**`docs/cookbook.md` 必须新增一节** "Quote Dialogue — 怎么跟 agent 多轮对话":
- 用 3-5 个真实 example 展示用户常见场景
- 包含: 用户对 agent 提问的回复 / 用户主动发起新问题 / 解决 (resolved) 一个 quote
- **自包含** — 不引用 spec 或 `_protocols/quote-dialogue.md` (用户看不到这些路径, 教程必须独立可读)
- 完整内嵌: 三种 quote 语法 / speaker 命名 / 嵌套规则 / 场景示例 / 易错点清单
**AC**:
- AC-1: `docs/cookbook.md` 包含 "Quote Dialogue" 标题段
- AC-2: 该段至少 3 个可运行 example (回复/主动提问/三方对话)
- AC-3: 该段自包含, 不含 `../` 相对路径引用其它 spec/_protocols 文件
---
## 3. 非功能需求
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#3-]
<a id="nfr-0010"></a>
### NFR-0010 向后兼容 (含 deprecation 显式声明)
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#nfr-0010---deprecation-]
- v0.4-004 quote_parser.py 实现**保留** (解析 `> **Name:**` 语法)
- 旧 spec.md 中已存在的 quote 块**不需要重写**
- 本 spec 仅**扩展**语义, 不**变更**解析器
- 用户无感升级: 装新 louke 后, 旧 spec 仍可正常走 quote dialogue 流程
**AC**:
- AC-1: 任意 v0.4-004 时代 spec 文件在 louke v0.6.16+ 下走 quote dialogue 流程, 行为一致
- AC-2: `tools/quote_parser.py --check-ready` 对老 spec 仍返回 exit 0
<a id="nfr-0020"></a>
### NFR-0020 草稿不进 git
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#nfr-0020--git]
- agent 用 `<!-- ... -->` 写内部笔记时, 这些笔记**不应**进 git
- 实现路径: agent 在 commit 前必须 strip 所有 `<!-- ... -->` 块 (用 `git add` 之前 grep + sed 过滤)
- 这是 [Sage.md L464-468](../../../../agents/Sage.md#L464) 已有的"raw 不入 git"约定的**强制化**
**AC**:
- AC-1: agent 的 commit hook 包含 `<!--` grep 检查, 命中则 fail commit
- AC-2: `tests/test_quote_dialogue.bats` 验证: 包含 `<!-- agent draft -->` 的 spec.md 走 commit, git log 不含该字符串
<a id="nfr-0030"></a>
### NFR-0030 文档语言
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#nfr-0030-]
- 本 spec FR 描述用中文 (与 louke 其它 spec 一致)
- speaker-tag 语法示例保留 markdown 原文 (跨语言)
- 教程段 (FR-0050) 可中英双语 (用户群国际化)
---
## 4. 受影响文件 (Kilo 实施时参考)
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#4--kilo-]
| 文件 | 改动 |
|---|---|
| `agents/Sage.md` L37-41 | 替换为 `Quote Dialogue 协议: 参见 v0.6-016 §FR-0010` 引用 |
| `agents/Sage.md` Step 3 | 大段例子外提, 引用本 spec; 保留流程定义 |
| `agents/Lex.md` (任意处) | 加 spec 引用 |
| `agents/{Archer,Judge,Scout,Devon,Keeper,Librarian,Prism,Shield,Warden,Maestro}.md` | 各加一处 spec 引用 (frontmatter 后第一段) |
| `docs/cookbook.md` | 加 "Quote Dialogue" 段 |
| `tests/test_agent_frontmatter.bats` | 加测试: 所有 12 agent 含规范引用 |
| `tools/quote_parser.py` | 不动 (FR-0010 兼容) |
| `.github/RELEASE_NOTES_v0.6.16.md` | 新建, 列 4 项改动 |
---
## 5. 退出条件 (待 Sage 阶段处理)
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#5---sage-]
- [ ] 12 agent prompt 更新完成, 引用本 spec
- [ ] docs/cookbook.md 教程段写完
- [ ] `tests/test_agent_frontmatter.bats` 测试通过
- [ ] 实测一次 quote dialogue: 用户在 IDE 写 `> **Aaron:**` → agent 在 `>>` 回复 → commit + push 链路通
- [ ] release notes v0.6.16 写好
---
## 6. 状态
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#6-]
- 2026-07-04 17:54 Kilo 创建本 spec (受 GLM 委托, 根因 = 7 个 agent permission 不全 → 引出 quote dialogue 协议需要正式化)
- (待 Aaron 拍板) 决定是否采纳 §0.2 supersede 关系
- (待 Sage 阶段) 实施 §4 改动
---
## 7. 相关文件清单
[source: project/specs/v0.6-016-quote-dialogue-protocol/spec.md#7-]
| 文件 | 说明 |
|---|---|
| `.louke/project/specs/v0.4-004-quote-dialogue/spec.md` | quote dialogue 流程规范 (本 spec 在其基础上扩展) |
| `tools/quote_parser.py` | quote 块解析器 (FR-0010 兼容, 不需要改) |
| `agents/Sage.md` L37-41, L131+ | 当前 speaker-tag 速查表 + Step 3 大段例子 (待精简) |
| `agents/Lex.md` | 当前自由使用 `> **Lex:**` (待规范引用) |
| `docs/cookbook.md` | 当前无 quote dialogue 教程 (待补) |
| `tests/test_agent_frontmatter.bats` | 当前无规范引用测试 (待补) |
| `.louke/review-sage-question-tool.md` §7.0 | GLM 重判根因 (task: deny 缺失 → 引出本 spec) |

## v0.7-001-pre-commit-quality-gates

# v0.7-001 — pre-commit 接管 lint/format/typecheck/test + R-G-R Red 去 commit — Spec
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#v07-001--pre-commit--lint-format-typecheck-test--r-g-r-red--commit--spec]
- **Spec ID**: v0.7-001-pre-commit-quality-gates
- **创建日期**: 2026-07-05
- **状态**: 草稿（待 Aaron 拍板）
- **关联**:
- 取代 `/tmp/louke-design/quality-gates-design.md`（中性 `quality-gates.toml` 提案）—— 整份设计稿不再采用，本 spec §0.2 说明理由
- 受影响下游：v0.6-009 `agents/Keeper.md`（lint/test 职责描述）、`agents/Devon.md` §5.1 Red 阶段 commit、`louke/keeper.py` `run_external_tool` / `run_project_tests` / `_load_pyproject_tool` / `_load_pyproject_e2e_config`
- 受影响下游：`louke/devon.py` `commit-rgr --phase` 三阶段 → 两阶段
## 0. 范围与边界
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#0-]
### 0.1 本 spec 收纳
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#01--spec-]
| 主题 | FR 范围 |
|---|---|
| pre-commit 框架引入 + Scout 阶段安装 | FR-0100 |
| `.pre-commit-config.yaml` 模板体系（base + per-language） | FR-0200 |
| hook 内容定义（lint / format / typecheck / test） | FR-0300 |
| Devon R-G-R 改造：Red 不 commit + `commit-rgr` 移除 `--phase red` | FR-0400 |
| Devon 反模式：`--no-verify` 禁止 | FR-0500 |
| Keeper 瘦身：移除 lint/typecheck/test 代码路径 | FR-0600 |
| CI parity：`pre-commit run --all-files` | FR-0700 |
| 向后兼容 + pre-commit 依赖 + 文档同步 | NFR-0010 / NFR-0020 / NFR-0030 |
### 0.2 不采用 `quality-gates.toml` 提案（supersede）
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#02--quality-gatestoml-supersede]
`/tmp/louke-design/quality-gates-design.md` 提出：建中性 `.louke/project/quality-gates.toml` 描述 lint/typecheck/test 命令，`lk keeper gate` 读它执行。本 spec **否决**该方向，理由：
1. lint / format / typecheck 本质是**单文件、单 commit** 范围的检查，pre-commit 框架原生支持，零 token、语言生态维护，无需 louke 重新发明配置 schema + loader。
2. per-language 命令差异（ruff / eslint / golangci-lint）由 pre-commit 社区 hook repo 解决，louke 不必维护 N 套命令表。
3. 该提案存在未解问题（`paths` schema 与 `keeper.py:166` 不一致、漏迁 e2e loader、§6 风险表 `edit: deny` 事实错误），全部因改用 pre-commit 而消失。
4. `lk keeper gate` 仍需做**跨 commit 语义检查**（commit 消息格式、R-G-R 顺序、AC trace、反模式扫描），这些 pre-commit 做不了 —— Keeper 保留这部分，不消亡。
`quality-gates.toml` 不引入；keeper.py 的 `_load_quality_gates` / `run_external_tool` / `run_project_tests` 删除（FR-0600）；shield.py 的 `_load_quality_gates` / `_load_e2e_config` / `cmd_run_e2e` 保留（e2e 是 Shield 职责，不在本 spec 范围）。
> **与 v0.7-002 关系**：v0.7-002（知识蒸馏 Karpathy 化）早期版本曾含 `quality-gates.toml` 内容，现已剔除。本 spec 的否决声明是清理动作，防止未来 reviewer 看到旧设计稿误以为仍生效。
> **Sage:** §0.2 与现有代码不一致，请 Aaron 拍板 `quality-gates.toml` 的处置边界：
>
> 1. `keeper.py:139` 的 `_load_quality_gates()`、`shield.py:47` 的同函数、`Archer.md §6.4` 让 Archer 产出此文件，**v0.6 已 ship 这套机制**——§0.2 说"否决 / 不引入"事实上是砍掉已发布特性。
> 2. 建议方向：**保留文件 + loader，给 shield 的 `[test.e2e]` 段用**；删除 keeper 端对 `[lint] [typecheck] [test]` 段的读取代码路径。换言之 lint/typecheck/test 命令配置职责归 pre-commit，e2e 配置职责仍归 shield + `quality-gates.toml`。
> 3. 若 Aaron 同意方向 → §0.2 第 4 段重写，FR-0600 范围缩小为"删除 lint/typecheck/test 代码路径 + `[lint] [typecheck] [test]` 段读取"，**e2e 相关全部保留**。
> 4. 若 Aaron 仍要完全砍掉 `quality-gates.toml`（包括 shield 端）→ 需补一份 `quality-gates-e2e.toml` 或迁回 `pyproject.toml [tool.louke.test.e2e]`，本 spec 范围会扩大。
>
> 默认建议：方向 2（保留文件，仅砍 lint/typecheck/test 段读取）。OK？ ✓ resolved
>> **Aaron:** agree ✓ resolved
### 0.3 本 spec 不收纳
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#03--spec-]
- pre-commit hook 本身的版本升级策略（社区 hook repo 的 `rev` 字段管理）—— 留待 v0.7+ 跟进
- 多语言项目的语言探测冲突解决（如同时有 `pyproject.toml` + `package.json`）—— v0.7-001 默认两者都装，冲突由 Archer 在 M-ARCH 编辑
- `pre-commit autoupdate` 命令的集成（定期刷新 hook repo `rev`）—— 留待 v0.7+
- 非 Python 项目的 pre-commit 安装路径差异（纯 Node/Java 项目仍需 Python 装 `pre-commit` 包，NFR-0020 接受此约束）
---
## 1. 用户故事
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#1-]
### US-0100 lint / format / typecheck 不花 LLM token
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#us-0100-lint---format---typecheck--llm-token]
- US-0100: 作为 Maestro 调度者，我希望 lint / format / typecheck 检查在 `git commit` 时由 pre-commit hook 自动执行，零 LLM token、零 Keeper agent 调用，以便 Keeper 专注语义级检查、token 消耗下降
- US-0110: 作为 louke 维护者，我希望 per-language 规则由社区 hook repo 维护（ruff / eslint / golangci-lint），louke 只模板化 `.pre-commit-config.yaml`，避免在 louke 代码里维护 N 套 linter 命令表
### US-0200 R-G-R Red 去 commit 让测试可进 pre-commit
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#us-0200-r-g-r-red--commit--pre-commit]
- US-0200: 作为 Devon 工作流执行者，我希望 Red 阶段只在工作区写测试 + 跑测试观察失败、不创建 commit，以便 Green / Refactor commit 触发 pre-commit 时所有测试**应当**通过（pre-commit 可放心包含测试 hook）
- US-0210: 作为 Keeper 维护者，Red 不 commit 意味着 git 历史里只有 `feat: green` 和 `refactor` 两类 commit，R-G-R 顺序检查简化为"refactor 不得先于 green（同 issue 内）"
### US-0300 `--no-verify` 显式反模式
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#us-0300---no-verify-]
- US-0300: 作为 Maestro 协调者，我希望 Devon prompt 显式禁止 `git commit --no-verify`，违反即反模式；CI 跑 `pre-commit run --all-files` 复查，以便 `--no-verify` 绕过在 CI 阶段被捕获
### US-0400 Keeper 瘦身
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#us-0400-keeper-]
- US-0400: 作为 louke 维护者，我希望 `lk keeper gate` 不再跑 lint / typecheck / test，这些归 pre-commit；Keeper 保留：commit 消息格式（R-G-R 前缀）+ R-G-R 顺序 + AC trace + 反模式扫描
- US-0410: 作为 Keeper 用户，我希望 `lk keeper gate --tests` flag 移除（测试在 pre-commit + CI），避免 Keeper 重复跑测试
### US-0500 安装时机
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#us-0500-]
- US-0500: 作为新项目发起者，我希望 `lk scout foundation` 在创建 repo / branch 后、`commit-foundation` 前自动探测语言、生成 `.pre-commit-config.yaml`、跑 `pre-commit install`，以便 foundation commit 本身就经过 pre-commit 校验
- US-0510: 作为存量项目采用者，我希望 `lk init --adopt` 对已有 repo 也能补装 pre-commit hook
---
## 2. 关键场景
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#2-]
### scenario-0100 新项目 Scout 阶段装 pre-commit
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#scenario-0100--scout--pre-commit]
```
1. Scout Step 1 收集项目信息: 用户选 Python 项目 (intended stack)
2. Scout Step 2-4: 创建 repo / Project / releases 分支
3. Scout Step 5 (新增): 探测 manifest → 无 (greenfield) → 用用户声明的 stack
- 从 louke/templates/pre-commit/ 合并 base.yaml + python.yaml → 写 .pre-commit-config.yaml
- 跑 `pre-commit install` → .git/hooks/pre-commit 创建
4. Scout Step 6-8: 写 status / story / commit-foundation
- commit-foundation 触发 pre-commit: check-yaml / check-toml / trailing-whitespace 通过
5. Devon M-DEV 接手: Red 写测试 (不 commit) → Green commit (pre-commit 跑 ruff + mypy + pytest) → Refactor commit
```
### scenario-0200 Devon R-G-R 不再 commit Red
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#scenario-0200-devon-r-g-r--commit-red]
```
1. Devon 接收 issue #42 (FR-0001)
2. Phase 1 (Red):
- 写 tests/test_foo.py
- 跑 pytest → 失败 (期望)
- **不 commit**, 不调 commit-rgr --phase red
- 报告 Maestro: "Red 就绪, 测试失败信息指向 FR-0001"
3. Phase 2 (Green):
- 写 src/foo.py
- 跑 pytest → 全部通过
- 调 `lk devon commit-rgr --issue 42 --phase green --message "..."`
- 工具生成 commit message: "feat: green: ... Closes #42"
- git commit 触发 pre-commit:
✓ ruff check (lint)
✓ ruff format --check (format)
✓ mypy (typecheck)
✓ pytest (test)  ← 安全: Green 阶段测试必过
- commit 成功, push
4. Phase 3 (Refactor):
- 重构 src/foo.py
- 跑 pytest → 仍通过
- 调 `lk devon commit-rgr --issue 42 --phase refactor --message "..."`
- commit message: "refactor: ..."
- pre-commit 再跑一次 (同上)
- commit 成功, push
```
### scenario-0300 Devon 试图 --no-verify 被反模式挡
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#scenario-0300-devon----no-verify-]
```
1. Devon Green 阶段, pytest 在 pre-commit 里失败 (某个边界 case)
2. Devon 试图 `git commit --no-verify` 绕过
3. Devon.md §8 反模式已列 `--no-verify` → Devon 不执行
4. Devon 修复测试 / 实现后重跑 pytest → 通过 → 正常 commit
5. (若 Devon 仍执行 --no-verify) Maestro 在 git log 中看不到 pre-commit 标记, 视为反模式触发, 退回 Devon
```
### scenario-0400 CI 复查 --no-verify 绕过
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#scenario-0400-ci----no-verify-]
```
1. Devon (假设) 用 --no-verify 提交了 Green commit
2. 本地 pre-commit 没跑, lint 失败未暴露
3. push → CI 触发
4. CI workflow 加一步 `pre-commit run --all-files`
5. CI 失败 (ruff 报错) → Maestro 收到 CI 红灯 → 退回 Devon 修复
```
### scenario-0500 存量项目补装 pre-commit
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#scenario-0500--pre-commit]
```
1. 用户已有 Python repo, 无 .pre-commit-config.yaml
2. 跑 `lk init --adopt` (或 `lk scout install-precommit --force`)
3. louke 探测 pyproject.toml → 识别 Python
4. 生成 .pre-commit-config.yaml (base + python)
5. 跑 `pre-commit install`
6. 后续 commit 走 pre-commit
7. (可选) `pre-commit run --all-files` 一次性扫全仓, 看历史代码是否有 lint 问题
```
---
## 3. 功能需求
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#3-]
<a id="fr-0100"></a>
### FR-0100 pre-commit 框架引入 + Scout 阶段安装
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#fr-0100-pre-commit---scout-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
`pre-commit` 作为 louke 的**运行时依赖**加入 `pyproject.toml` 的 `dependencies`。用户 `pip install louke` 后即有 `pre-commit` 命令可用。
**安装时机**：`lk scout foundation` 在 Step 4b（权限冒烟）之后、Step 6（写状态文件）之前**新增 Step 5: 安装 pre-commit hook**。Step 5 流程：
1. **探测项目语言**（全部匹配项，非短路 —— 多语言项目同时装多个模板，见 §0.3）：
- `pyproject.toml` / `setup.py` / `pytest.ini` → Python
- `package.json` → Node / TypeScript（`typescript` 字段在 devDependencies 则含 typecheck）
- `go.mod` → Go
- `Cargo.toml` → Rust
- `pom.xml` / `build.gradle` → Java
- 上述都没有 → 仅装 base（FR-0200）
2. **生成 `.pre-commit-config.yaml`**：从 `louke/templates/pre-commit/base.yaml` + 探测到的 `{language}.yaml` 合并写入项目根目录。若已存在 `.pre-commit-config.yaml`，跳过生成（除非 `--force`）。
3. **跑 `pre-commit install`**：幂等，重复执行只更新 `.git/hooks/pre-commit`。
4. **记录到 `project.toml`**（fix-002 后）：`[meta].pre_commit = "installed ({language} + base)"`，下游 agent 可读。
**`lk init --adopt`** 走同样流程（已有 repo 补装 hook）。
**新增 CLI 子命令** `lk scout install-precommit [--force]`：单独触发 Step 5，供存量项目补装或重装。
---
<a id="fr-0200"></a>
### FR-0200 `.pre-commit-config.yaml` 模板体系
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#fr-0200-pre-commit-configyaml-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
louke 自带模板目录 `louke/templates/pre-commit/`：
| 文件 | 内容 | 适用 |
|---|---|---|
| `base.yaml` | trailing-whitespace / end-of-file-fixer / check-yaml / check-toml / check-merge-conflict / large-files | 所有项目 |
| `python.yaml` | `astral-sh/ruff-pre-commit`（check + format）/ `pre-commit/mirrors-mypy` | Python |
| `node.yaml` | `pre-commit/mirrors-eslint` / `pre-commit/mirrors-prettier` / 本地 `tsc --noEmit` | Node / TypeScript |
| `go.yaml` | `dominikh/pre-commit-golang`（golangci-lint + gofmt）+ 显式 `go-test` hook（`pre-commit.com/go-test`）跑 `go test ./...` | Go |
| `rust.yaml` | 本地 `cargo fmt --check` / `cargo clippy` / `cargo test` | Rust |
| `java.yaml` | `pre-commit/mirrors-spotless` 或 checkstyle | Java |
**合并规则**：
- `base.yaml` 始终包含
- 探测到多语言 → 多个 `{language}.yaml` 的 `repos:` 列表拼接
- 每个模板的 `rev` 字段在 louke 发版时由 `lk upgrade --precommit`（v0.7+ 提供）刷新；v0.7-001 锁定具体 tag（2026-07-05 时已知稳定）：
- ruff: `v0.6.x`（`astral-sh/ruff-pre-commit`）
- mypy: `v1.10.x`（`pre-commit/mirrors-mypy`）
- eslint: `v9.x`（`pre-commit/mirrors-eslint`）
- prettier: `v3.3.x`（`pre-commit/mirrors-prettier`）
- golangci-lint: `v1.59.x`（`dominikh/pre-commit-golang`）
- base hooks（trailing-whitespace 等）: `pre-commit/pre-commit-hooks v4.6.x`
**Archer 编辑权**：M-ARCH 阶段 Archer 可编辑 `.pre-commit-config.yaml`（如换 linter、加 project-local 规则）。Archer 的 `edit: allow` 配合 prompt 路径白名单已覆盖此文件（属于 architecture 决策范畴）。
---
<a id="fr-0300"></a>
### FR-0300 pre-commit hook 内容（lint / format / typecheck / test）
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#fr-0300-pre-commit-hook-lint---format---typecheck---test]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
每次 `git commit` 触发 pre-commit，依次跑：
| 阶段 | 检查项 | 失败行为 |
|---|---|---|
| lint | ruff check / eslint / golangci-lint / clippy | 阻止 commit |
| format | ruff format --check / prettier --check / gofmt | 阻止 commit（部分 hook 支持 `--apply` 自动修复后重跑） |
| typecheck | mypy / tsc --noEmit / cargo check | 阻止 commit |
| test | pytest / npm test / go test ./... | 阻止 commit |
**test hook 能进 pre-commit 的关键前提**：FR-0400 Red 阶段不 commit。Green / Refactor 是项目历史中**仅有的**包含测试相关改动的 commit 类型，且两者都要求测试全过。因此 pre-commit 的 test hook 在每次 commit 时都**应当**通过 —— 不会出现 Red commit 被测试 hook 拦死的情况。
**hook 作用域**：pre-commit 默认只跑 staged 文件相关的检查（快）。全仓扫描由 CI `pre-commit run --all-files` 负责（FR-0700）。
**性能预算**（per hook，staged 文件）：
- lint ≤ 5s（ruff / eslint / golangci-lint / clippy）
- format ≤ 3s（ruff format --check / prettier --check / gofmt）
- typecheck ≤ 10s（mypy / tsc --noEmit / cargo check）
- test ≤ 30s（pytest quick 模式 / npm test / go test）
全套 hook 在中等项目（< 1000 staged 文件）应在 60 秒内完成。**超时判定**：若 test hook 单独 > 60s，Archer 可在 `.pre-commit-config.yaml` 里把 test hook 拆到 CI-only（pre-commit 跑 lint/format/typecheck，CI 跑 test）—— 这是 project-level 决策，不属本 spec 强制。
> **Sage:** "30 秒内"是软目标还是硬指标，请 Aaron 拍板：
>
> - **软目标**（推荐）：超出不报错，Archer 可优化；CI 中 CI-only test hook 拆分作为兜底手段。
> - **硬指标**：pre-commit 启动超时 → commit 失败——会阻塞 agent 工作流，不建议。
>
> 默认建议：软目标。OK？ ✓ resolved
>> **Aaron:** agree ✓ resolved
---
<a id="fr-0400"></a>
### FR-0400 Devon R-G-R 改造：Red 不 commit + commit-rgr 移除 `--phase red`
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#fr-0400-devon-r-g-r-red--commit--commit-rgr----phase-red]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
#### FR-0400.1 Red 阶段不 commit
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#fr-04001-red--commit]
`agents/Devon.md` §5.1 Phase 1 (Red) 重写为：
1. 确认在 `releases/{version}` 分支
2. 阅读 issue 关联的 FR/NFR + acceptance
3. 识别测试框架
4. 编写单元测试代码
5. 跑测试确认失败（Red）
6. **不 commit，不调 `commit-rgr --phase red`**
7. 报告 Maestro："Red 就绪，测试失败信息指向 {FR-ID}，待 Green"
退出条件改为：
- [ ] 测试文件已在工作区
- [ ] 测试套件报告 Red
- [ ] 失败信息指向待实现功能
- （移除 "测试文件已提交" 项）
#### FR-0400.2 `commit-rgr` 移除 `--phase red`
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#fr-04002-commit-rgr----phase-red]
`louke/devon.py` `commit-rgr` 子命令：
- `--phase` 选项枚举值从 `{red, green, refactor}` 改为 `{green, refactor}`
- 调用 `--phase red` 直接报错：`error: --phase red 已废弃 (v0.7-001): Red 阶段不 commit，详见 agents/Devon.md §5.1`
- `RGR_PREFIX` 是嵌套 dict（key 为 `(label, phase)` tuple，`devon.py:16`），删除两个 tuple 键：`('feature', 'red')` 和 `('fix', 'red')`；保留 `('feature','green')` `('fix','green')` `('feature','refactor')` `('fix','refactor')`
- Green 仍自动追加 `Closes #{issue}`，Refactor 不追加
> [!NOTE]
> 现状提示：当前 `louke/devon.py:16-23` 的 `RGR_PREFIX` 仍含 `('feature', 'red')` 和 `('fix', 'red')` 键；`louke/agents/Devon.md` §5.1 仍含 `--phase red` 调用和 `test: red` 退出条件。本 FR 落地时同步修改，详见 §6 关联文件表。
#### FR-0400.3 R-G-R 顺序检查简化
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#fr-04003-r-g-r-]
`lk keeper gate` 的 R-G-R 顺序检查（FR-0600 保留）改为：
- 同 issue 内 commit 序列只允许 `[green]` 或 `[green, refactor...]` 或 `[refactor...]`（跨 issue 时不强制）
- **禁止** `refactor` 先于 `green`（同 issue 内）
- **不再检查** `test: red` 是否存在（Red 不 commit，git 历史无此 commit）
- `test: red` 前缀若出现在历史 commit（v0.7 前存量），视为 legacy，不报错
> **Sage:** FR-0400.3 写得很简略，但有两个边界场景请 Aaron 明确，确认后落到 acceptance.md AC-7：
>
> 1. **fix cycle**：`commit-rgr` 支持 `--label fix` 产出 `fix: green` 前缀（`devon.py:21`），fix cycle 内"refactor 不得先于 green"的语义跟 feature cycle 一致。请确认 `lk keeper gate` 把 `fix: green` / `feat: green` 都视为"green 前缀"同等检查。
> 2. **跨 issue 时不强制**：spec 文字"跨 issue 时不强制"——具体是 (a) 不同 issue 的 commit 序列不参与顺序校验、(b) 同 issue 内仍校验，(c) git log 输出按 issue 分组后再校验？建议 (a)——按 issue 分组过于精细，对 agent 增加不必要负担。
>
> 默认建议：fix cycle 等同 feature cycle + 跨 issue 不参与校验（即实现最简）。OK？ ✓ resolved
>> **Aaron:** agree ✓ resolved
---
<a id="fr-0500"></a>
### FR-0500 Devon 反模式：`--no-verify` 禁止
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#fr-0500-devon---no-verify-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
`agents/Devon.md` §8 反模式追加一条：
```
❌ 使用 `git commit --no-verify` 绕过 pre-commit hook
pre-commit 失败 → 修复根因（lint/格式/类型/测试）后重新 commit；不允许 --no-verify 跳过
若修复超出 Devon 能力 → 报告 Maestro, 由 Archer 介入或人工修复
```
**配套约束**：
- Devon prompt §6.2 Push 规则追加一句："commit 前若 pre-commit hook 失败，必须修复后重新 commit，**禁止** `--no-verify`"
- 假设 Devon 仍执行 `--no-verify` 提交 → push → CI 跑 `pre-commit run --all-files` 失败 → CI 红灯 → Maestro 收到信号退回 Devon 修复
> **Sage:** 原 spec 写"Maestro 在 git log 检查若发现 commit 缺 pre-commit 标记视为反模式触发"，这一句在技术上不成立：`git commit --no-verify` 与正常 `git commit` 产出的 tree / commit object 一致，`git log` 区分不出。建议**整段删除该句**，`--no-verify` 兜底机制只剩：
>
> 1. Devon prompt §8 反模式列表（约束 agent 行为）
> 2. Devon prompt §6.2 `--no-verify` 禁令（commit 前最后一道提示）
> 3. CI `pre-commit run --all-files`（FR-0700，全量复查，捕获漏网）
>
> 这三层已足够。OK？ ✓ resolved
>> **Aaron:** agree ✓ resolved
---
<a id="fr-0600"></a>
### FR-0600 Keeper 瘦身：移除 lint / typecheck / test 代码路径
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#fr-0600-keeper--lint---typecheck---test-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
#### FR-0600.1 `louke/keeper.py` 删除的代码路径
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#fr-06001-louke-keeperpy-]
| 函数 | 当前行号 | 删除理由 |
|---|---|---|
| `_load_quality_gates()` | keeper.py:139 | 不再从 `pyproject.toml [tool.louke.*]` 或 `quality-gates.toml` 读 lint/typecheck/test 命令（e2e 段读取由 shield 接管，见 FR-0600 关联说明） |
| `run_external_tool()` | keeper.py:178 | lint / typecheck 归 pre-commit |
| `run_project_tests()` | keeper.py:193 | test 归 pre-commit |
| `cmd_gate` 中 lint/typecheck/test 分支 | keeper.py:250-266 | 对应 `--lint` / `--typecheck` / `--tests` flag 一并移除（NFR-0010） |
> **Sage:** FR-0600.1 现状（v0.6 实测）有两处与原 spec 描述不符，请 Aaron 确认修订方向：
>
> 1. **函数名错**：spec 原写 `_load_pyproject_tool()` / `_load_pyproject_e2e_config()` / `cmd_run_e2e`，但 keeper.py 中实际是 `_load_quality_gates()` / `run_external_tool()` / `run_project_tests()`；`cmd_run_e2e` 在 shield.py:108，keeper.py 里**没有** e2e 相关函数（keeper 跑 e2e 是历史叙述）。
> 2. **e2e 处置**：建议 keeper.py 只删 lint/typecheck/test 代码路径，**`shield.py` 的 `_load_quality_gates()` + `_load_e2e_config()` + `cmd_run_e2e` 全部保留**（e2e 是 Shield 职责，不在本 spec 范围内）。需要 Aaron 显式同意"keeper 端瘦到只剩 R-G-R 顺序 / commit 消息格式 / AC trace / 反模式扫描，e2e 不动"。
> 3. **CLI flag 同步删**：keeper.py 当前 `--lint` / `--typecheck` / `--tests` 三个 flag — `--tests` spec 写了要删，`--lint` `--typecheck` 没明说。建议**三个一并删**（FR-0300 把测试归 pre-commit，lint/typecheck 也归 pre-commit，keeper 不重复跑）。
>
> 默认建议：上面表格的内容 + Q1 方向 2 一起锁定。OK？ ✓ resolved
>> **Aaron:** agree ✓ resolved
#### FR-0600.2 `lk keeper gate` 保留的检查项
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#fr-06002-lk-keeper-gate-]
| 检查项 | 数据源 | 为什么 pre-commit 做不了 |
|---|---|---|
| commit 消息格式（`feat: green` / `fix: green` / `refactor` 前缀） | `git log` | pre-commit 只看当前 commit 的 staged 文件，不看 commit 消息内容（虽然也有 `commit-msg` hook 但那是另一套） |
| R-G-R 顺序（refactor 不得先于 green、同 issue 内；`fix: green` 与 `feat: green` 等价检查） | `git log` 跨 commit | pre-commit 单 commit 作用域 |
| AC trace（docstring `AC-FRXXXX-YY` 锚点存在性） | 跨文件 AST 扫描 | pre-commit 不做语义分析 |
| 反模式扫描（`assert True` / `try: pass` / `# noqa` 滥用） | AST 扫描 | louke 特定规则，社区 hook 无 |
#### FR-0600.3 `lk keeper gate` CLI flag 移除（`--tests` / `--lint` / `--typecheck`）
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#fr-06003-lk-keeper-gate-cli-flag---tests-----lint-----typecheck]
`--tests` / `--no-tests` / `--lint` / `--typecheck` 选项全部删除。lint/typecheck/test 归 pre-commit（本地）+ CI（远程），Keeper 不重复跑。`_load_quality_gates` 的 `pyproject.toml [tool.louke.*]` fallback 路径一并删除。
Keeper.md description 字段更新：
```yaml
# 旧
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#]
description: 质量门禁 — 调度 lk keeper CLI 验证 R-G-R / 测试 / lint / commit 格式
# 新
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#]
description: 质量门禁 — 验证 R-G-R 顺序 / commit 消息格式 / AC trace / 反模式扫描
```
---
<a id="fr-0700"></a>
### FR-0700 CI parity：`pre-commit run --all-files`
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#fr-0700-ci-paritypre-commit-run---all-files]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
louke 自身的 CI（`.github/workflows/*.yml`）新增一步：
```yaml
- name: Run pre-commit on all files
run: pre-commit run --all-files
```
**目的**：捕获 `--no-verify` 绕过。本地 pre-commit 只跑 staged 文件；CI 跑全仓，任何漏网的 lint/格式/类型/测试失败都会暴露。
**用户项目 CI**：`lk scout foundation` 不直接改用户的 `.github/workflows/`（那是 Archer 的 architecture 决策范畴）。但 louke 提供独立 CI snippet 文件供 Archer 引用：
- `louke/templates/pre-commit/ci-snippet.yml` — 可直接 `cat` 复制到用户项目 `.github/workflows/`
- `louke/templates/pre-commit/README.md` — 使用说明 + 指向 ci-snippet.yml 的链接
> **Sage:** FR-0700 未明确 louke 自身是否 dogfood 这套模板，请 Aaron 拍板：
>
> 1. **dogfood**（推荐）：louke 仓库根目录写一份 `.pre-commit-config.yaml`（用 louke 模板的 base + python 组合），`pyproject.toml` 的 `dependencies` 同样依赖 `pre-commit`，CI `.github/workflows/ci.yml` 跑 `pre-commit run --all-files` 把模板自身当 lint 网——模板有问题第一时间在 louke 仓库暴露。
> 2. **不 dogfood**：只在 `louke/templates/pre-commit/` 产模板，自己 CI 用 ruff/mypy/pytest 原生命令。模板与 louke 自身 lint 规则可能漂移。
>
> 默认建议：dogfood。OK？ ✓ resolved
>> **Aaron:** dogfood ✓ resolved
**louke 自身 dogfood**（Aaron 已确认）：louke 仓库根目录写一份 `.pre-commit-config.yaml`（用 louke 模板的 base + python 组合），CI `.github/workflows/ci.yml` 跑 `pre-commit run --all-files`。模板有问题第一时间在 louke 仓库暴露，避免模板与 louke 自身 lint 规则漂移。
---
## 4. 非功能需求
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#4-]
<a id="nfr-0010"></a>
### NFR-0010 向后兼容
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#nfr-0010-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
⚠️ **Breaking changes 显式声明**：
1. **Devon `commit-rgr --phase red` 移除**：脚本 / prompt 仍传 `--phase red` 会报错。存量 Devon.md / 外部脚本需更新。
2. **`lk keeper gate --tests` / `--lint` / `--typecheck` 移除**：`--tests` 写了要删；`--lint` `--typecheck` 同样需删（FR-0300 把 lint/typecheck 归 pre-commit，keeper 不重复跑）。CI 脚本若调用 → 改为 `pre-commit run --all-files`。
3. **`pyproject.toml [tool.louke.*]` 不再读取**：v0.6 的 `_load_quality_gates()` 对 `[tool.louke.lint]` 等段有 fallback 读取；本 spec 后该 fallback 是否一并删（FR-0600 提示需要）——若保留则与"lint/typecheck 归 pre-commit"语义冲突，建议删。
4. **git 历史中的 `test: red` commit**：v0.7 前的存量 commit 不受影响（不重写历史）。Keeper 的 R-G-R 顺序检查对 legacy `test: red` commit 静默接受。
5. **模板同步**：`louke/templates/task-log.md` 和 `louke/templates/bug-fix.md` 中的 `Commit: test: red – {编号} {描述}` 模板需同步改为 `feat: green` / `fix: green` / `refactor` 前缀（FR-0400 后这些模板会让 agent 误产 `test: red` commit）。
6. **`.opencode/agents/` 部署产物**：`.opencode/agents/devon.md` 是 `lk board opencode` 的部署产物（非源文件）。FR-0400/FR-0500 改动只需改 `louke/agents/Devon.md`（单一来源），功能完成后跑 `lk board opencode` 刷新部署。
> **Sage:** 请 Aaron 把以下 4 个边界纳入 v0.7-001 改动清单（否则 spec 落地后这些会被遗忘）：
>
> 1. **CLI flag**：`lk keeper gate --lint` / `--typecheck` / `--tests` 全删，NFR-0010 已加。
> 2. **pyproject fallback**：`_load_quality_gates()` 的 `pyproject.toml [tool.louke.*]` fallback 路径是否一并删？默认建议：删（FR-0600 配套）。
> 3. **templates 同步**：`louke/templates/task-log.md:12` `louke/templates/bug-fix.md:26` 都是 `Commit: test: red – {编号} {描述}` 模板，FR-0400 后这些模板会让 agent 误产 `test: red` commit。建议同时改：
>    - `task-log.md:12` → 改为 `Commit: feat: green – ... 或 refactor: ...`
>    - `bug-fix.md:26` → `Commit: fix: green – BUG-{编号} {描述}` / `refactor: ...`
> 4. **Dual prompt file**: `.opencode/agents/devon.md:76` 跟 `louke/agents/Devon.md:90` 是两份独立 Dev prompt 源，FR-0400/FR-0500 改动只列了 `agents/Devon.md`。请确认 **两份都要改**，或 `.opencode/` 目录是 shadow / 旧版（如是 shadow 则 `agents/Devon.md` 单一来源）。 ✓ resolved
>> **Aaron:** 本项目下的.opencode/agents 视为部署，功能完成后，要执行 lk upgrade/board ✓ resolved
> **Sage:** 默认建议：以上 4 项全部纳入。OK？ ✓ resolved
>> **Aaron:** agree ✓ resolved
**升级路径**：
- `lk upgrade` 升级到 v0.7+ 后，跑 `lk scout install-precommit --force` 补装 pre-commit hook
- 现有 `pyproject.toml [tool.louke.lint]` 配置：louke 不再读取，用户可手动迁移到 `.pre-commit-config.yaml`（louke 不提供自动迁移工具，因为字段差异大）
**最小迁移指南**（详见 `louke/templates/pre-commit/README.md`）：
1. 识别旧 `[tool.louke.lint]` 的 `command` + `args`
2. 查社区 hook repo 对应（ruff → `astral-sh/ruff-pre-commit`，eslint → `pre-commit/mirrors-eslint`）
3. 写入 `.pre-commit-config.yaml` 的 `repos:` 列表
4. 跑 `pre-commit run --all-files` 验证
- Archer 在 M-ARCH 阶段把 lint 决策从 spec 产物迁移到 `.pre-commit-config.yaml`
<a id="nfr-0020"></a>
### NFR-0020 pre-commit 框架依赖
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#nfr-0020-pre-commit-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
- `pre-commit` 加入 `pyproject.toml` 的 `dependencies`（非 dev-dependencies，因为 louke 运行时需要它安装 hook）
- 版本约束：`pre-commit >= 3.0, < 5.0`（允许 3.x / 4.x，留主版本缓冲；hook repo 在主版本切换时可能破坏向后兼容）
- 非 Python 项目（纯 Node / Java / Rust）仍需 Python 环境装 `pre-commit` —— 接受此约束，因 louke 本身依赖 Python，用户装 louke 时已有 Python
> **Sage:** 请 Aaron 决定 `pre-commit` 依赖上限。`pre-commit 4.x` 已发布，hook repo 在主版本切换时可能破坏向后兼容。建议钉 `pre-commit >= 3.0, < 5.0`（允许 3.x / 4.x，留缓冲）。OK？ ✓ resolved
>> **Aaron:** agree ✓ resolved
<a id="nfr-0030"></a>
### NFR-0030 文档同步
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#nfr-0030-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
- **README.md / README.zh.md**：在"工作流"章节加"pre-commit 质量门禁"小节，说明 lint/format/typecheck/test 在 commit 时自动跑、零 token、`--no-verify` 是反模式
- **`agents/Devon.md`**：§5.1 Red 不 commit、§6.2 加 `--no-verify` 禁令、§8 加反模式条目
- **`agents/Keeper.md`**：description 改、§3 任务描述移除"调度 lint/test"、§2.1 tools 移除 lint/test 相关 CLI 调用
- **`agents/Scout.md`**：新增 Step 5 安装 pre-commit hook 的流程描述
- **`agents/Archer.md`**：§6 加"`.pre-commit-config.yaml` 是 Archer 可编辑的架构产物之一"
---
## 5. 澄清记录
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#5-]
| Q | 议题 | 决定 |
|---|---|---|
| Q1 | lint / format / typecheck 放 Keeper agent 还是 pre-commit | pre-commit —— 零 token、单文件级、语言生态原生 |
| Q2 | test 能否进 pre-commit | 能 —— 前提是 Red 阶段不 commit（FR-0400），Green/Refactor commit 时测试必过 |
| Q3 | Red 不 commit 是否影响 R-G-R 工作流 | 不影响 —— Red 仍是工作区写测试 + 跑测试观察失败；只是不进 git 历史。Green/Refactor commit 仍是 R-G-R 的 Green/Refactor |
| Q4 | `quality-gates.toml` 提案是否采纳 | 否决（§0.2）—— per-language 命令问题 pre-commit 生态已解决 |
| Q5 | `--no-verify` 如何防范 | Devon prompt 反模式 + CI `pre-commit run --all-files` 复查 |
| Q6 | 存量项目如何升级 | `lk scout install-precommit --force` 补装；存量 `[tool.louke.lint]` 配置不自动迁移 |
| Q7 | 多语言项目如何处理 | 探测到多语言 → 多个 `{language}.yaml` 拼接；冲突由 Archer 编辑 |
| Q8 | pre-commit hook 的 `rev` 如何升级 | v0.7-001 固定稳定 rev；v0.7+ 提供 `lk upgrade --precommit` 刷新 |
| Q9 | e2e 测试归谁 | Shield agent + CI —— Keeper 不调度 e2e（`cmd_run_e2e` 在 `louke/shield.py:108`，不在 keeper.py；本 spec 不改 shield 的 e2e 调度） |
---
## 6. 关联文件
[source: project/specs/v0.7-001-pre-commit-quality-gates/spec.md#6-]
| 文件 | 改动 |
|---|---|
| `pyproject.toml` | 加 `pre-commit >= 3.0` 到 `dependencies`；移除 `[tool.louke.lint]` / `[tool.louke.test]` 相关配置（若存在） |
| `louke/templates/pre-commit/base.yaml` | **新建**：通用 hook（whitespace / yaml / toml / large-files） |
| `louke/templates/pre-commit/python.yaml` | **新建**：ruff check + ruff format + mypy |
| `louke/templates/pre-commit/node.yaml` | **新建**：eslint + prettier + tsc |
| `louke/templates/pre-commit/go.yaml` | **新建**：golangci-lint + gofmt + go-test |
| `louke/templates/pre-commit/rust.yaml` | **新建**：cargo fmt + clippy + test |
| `louke/templates/pre-commit/java.yaml` | **新建**：spotless / checkstyle |
| `louke/templates/pre-commit/README.md` | **新建**：自定义指南 + 指向 ci-snippet.yml 的链接 |
| `louke/templates/pre-commit/ci-snippet.yml` | **新建**：CI 配置片段（YAML），供 Archer 引用到用户项目 |
| `louke/scout.py` | 加 `cmd_install_precommit` 实现 + Step 5 流程 |
| `louke/devon.py` | `commit-rgr` `--phase` 枚举移除 `red`；`RGR_PREFIX` 移除 `('feature','red')` / `('fix','red')` 两个 tuple 键 |
| `louke/keeper.py` | 删 `_load_quality_gates` / `run_external_tool` / `run_project_tests`；`cmd_gate` 移除 lint/typecheck/test 调用；`--tests` / `--lint` / `--typecheck` flag 移除 |
| `louke/shield.py` | 保留 `_load_quality_gates` / `_load_e2e_config` / `cmd_run_e2e`（e2e 是 Shield 职责，不在本 spec 范围） |
| `louke/agents/Devon.md` | §5.1 Red 不 commit；§6.2 加 `--no-verify` 禁令；§8 加反模式 |
| `louke/agents/Keeper.md` | description 改；§3 移除 lint/test；§2.1 tools 移除 lint/test CLI |
| `louke/agents/Scout.md` | 新增 Step 5: 安装 pre-commit hook |
| `louke/agents/Archer.md` | §6 加 `.pre-commit-config.yaml` 是 Archer 可编辑产物 |
| `louke/templates/task-log.md` | `Commit: test: red` 模板改为 `feat: green` / `refactor` 前缀 |
| `louke/templates/bug-fix.md` | `Commit: test: red` 模板改为 `fix: green` / `refactor` 前缀 |
| `README.md` / `README.zh.md` | 加"pre-commit 质量门禁"小节 |
| `.github/workflows/ci.yml` | 加 `pre-commit run --all-files` 步骤 |
| `tests/test_devon_commit_rgr.bats` | 更新：`--phase red` 报错；`--phase green` / `refactor` 通过 |
| `tests/test_keeper_gate.bats` | 更新：移除 lint/test 相关断言；保留 R-G-R 顺序 + commit 格式 + AC trace + 反模式 |
| `tests/test_scout_install_precommit.bats` | **新建**：Step 5 探测 + 生成 + install 流程 |

## v0.7-002-knowledge-distillation-karpathy

# v0.7-002 — 知识蒸馏（Karpathy 风格）— Spec
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#v07-002--karpathy--spec]
- **Spec ID**: v0.7-002-knowledge-distillation-karpathy
- **创建日期**: 2026-07-05
- **修订**:
- 2026-07-05 21:30 初稿（Kilo 起草，聚焦知识蒸馏；跨语言质量门禁内容已拆分到 `v0.7-001-pre-commit-quality-gates`）
- **状态**: 草稿（待 Sage 起草 / Lex 复核 / Aaron 拍板）
- **关联**:
- **关键参考**：Karpathy [autoresearch](https://github.com/karpathy/autoresearch) — 知识蒸馏的核心思想来源（`train.py` = current best state，git history = journal）
- 受影响下游：v0.6-009 FR-0010.4 Librarian permission（CLI 模式兼容，`permission.question: deny` 无需改）
- 受影响下游：既有 `lk librarian from-raw` / `lk librarian distill`（机械 copy，违反"投影而非积累"，需替换）
---
## 0. 范围与边界
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#0-]
### 0.1 本 spec 收纳（v0.7.0 一次性发版）
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#01--spec-v070-]
| 主题 | FR 范围 |
|---|---|
| 知识蒸馏三原则（raw = journal / pages = projection / 整体重写） | FR-0070 |
| `lk librarian compact` / `lk librarian rewrite` 实现 | FR-0080 |
| cron 触发 + 跳日 catch-up | FR-0090 |
| raw = append-only journal（不进 git） | FR-0100 |
| `lk librarian lint` 适配重写模型 | FR-0110 |
| LLM 调度机制（`opencode run --agent librarian`） | FR-0130 |
| 上下文窗口应对（增量 / 全量 / Map-Reduce 分层） | FR-0140 |
| `lk init --install-cron` 目标改为 `lk librarian compact` | FR-0150 |
| Librarian 文档 Identity 框架对齐（Devon 框架英文） | FR-0120 |
| 受影响下游 + supersede + 可降级 | §0.2 / NFR-0010 / NFR-0020 |
### 0.2 受影响下游 / supersede
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#02----supersede]
- **既有 `lk librarian from-raw`**（机械 copy raw → pages）—— **SUPERSEDED by FR-0080**：删除；改用 `cmd_compact`（准备 bundle）+ `cmd_rewrite`（LLM 整体重写）
- **既有 `lk librarian distill`**（仅 print 待蒸馏列表）—— **保留 + 重定义**：语义改为"列出待 compact 的 raw"，由 `cmd_distill` 改为 wrapper 调 `cmd_compact --dry-run`
- **既有 `lk librarian lint`** —— **扩展**（FR-0110）：新增"重复主题" / "缺 frontmatter 必填字段"检查项
- **既有 `lk librarian daily`**（本会话初版）—— **SUPERSEDED by FR-0080 / FR-0090**：拆分 `compact` + `rewrite` 两个子命令；cron 默认调 `compact`，`rewrite` 显式触发
- **既有 `louke/agents/Librarian.md`** —— **重写**（FR-0120）：Identity / tools / permissions 段对齐 Devon 框架（英文）；§5 改写（cron 触发 + compact/rewrite 子命令 + 窗口 [last_distill, 昨天]）
### 0.3 本 spec 不收纳
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#03--spec-]
- 跨语言质量门禁 —— 已拆分到 `v0.7-001-pre-commit-quality-gates`（pre-commit 框架接管）
- `lk agent lint` 校验 wiki 文件 schema —— 留 v0.7-003
- raw/ 历史的自动归档 / 压缩 —— raw 是 journal，append-only，不删不改
- LLM 调用的具体 API 实现（OpenAI / Anthropic SDK）—— 走 OpenCode 自身路由，本 spec 仅约束"shell-out 到 OpenCode CLI"
- 矢量检索 / RAG —— 留 v0.7.1+，M2 Map-Reduce 兜底（FR-0140.1）
- `lk init --install-cron` 的实现 —— **已迁移至 FR-0150**（v0.7-002 实施）
### 0.4 wiki 命名空间处理策略（P1-5）
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#04-wiki-p1-5]
实际 wiki 结构（louke/.louke/wiki/）：
```
pages/         — 7 文件，本 spec 聚焦
decisions/     — 11 ADR 文件（含 008 编号重复），rewrite 范围**外**
entries/       — 7 legacy 文件（迁移前产物），**DEPRECATED**
consolidated.md — legacy 整合文件，**DEPRECATED**
index.md / log.md / overview.md — Librarian 维护
```
| 路径 | 状态 | 本 spec 处理 |
|---|---|---|
| `pages/*.md` | 主要目标 | rewrite 重写范围 |
| `index.md` / `log.md` / `overview.md` | 索引与日志 | FR-0080 rewrite 后由 LLM 调 `rebuild-index` + `lint` 刷新 |
| `.cache.toml` | 持久状态（`last_distill` + SHA256） | compact 写入 |
| `.compact-bundle*.md` | **临时中间产物** | FR-0140.2 compact 开始清理 |
| `decisions/*.md` | ADR 档案 | **不纳入 rewrite**（rewrite 不改 ADR）；008 编号重复问题 → **留 v0.7-003** 决定 |
| `entries/*.md` | legacy 迁移产物 | **DEPRECATED**：本 spec §0.3 声明 deprecated，Agent 不再写 entries；现有 7 个文件保留至 v0.7-003 决定是否迁移到 `pages/` 或删除 |
| `consolidated.md` | legacy 整合文件 | **DEPRECATED**：同上处理 |
---
## 1. 用户故事
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#1-]
### A. 投影而非积累
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#a-]
#### US-0100 wiki 只显示当前决策
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#us-0100-wiki-]
- US-0100: 作为 wiki 读者，我希望 wiki 只显示**当前**决策，不带任何**过时**知识 —— 过期决策在新 raw 出现后自动消失
- US-0110: 作为 raw session 写入者，我希望 raw 是 append-only 的 journal（保留试错与未决），不被任何"清理"动作触碰
### B. 整体重写而非补丁
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#b-]
#### US-0200 整体重写一致性
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#us-0200-]
- US-0200: 作为 LLM 蒸馏的执行者（Librarian subagent），我希望每次更新都是**整体重写** pages/，不是 patch 现有页面 —— 这样不会出现"页面 A 是旧决策 + 页面 B 是新决策，互相打架"的不一致状态
- US-0210: 作为 LLM，我希望每次重写前能拿到一份**context bundle**（含 raw 全文 + 现有 pages/ + 蒸馏指令），不是只拿到"自上次以来新增的 raw" —— 这样能基于全局重新判断哪些决策仍成立
### C. 触发机制
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#c-]
#### US-0300 自动触发 + 幂等
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#us-0300---]
- US-0300: 作为项目所有者，我希望知识蒸馏由系统级 cron 每日自动触发，无需我手动跑 —— 这样即便我忘记，wiki 也不会停滞
- US-0310: 作为 cron 用户，我希望重跑 cron 是幂等的 —— 即便某天 cron 因故没跑，下一天会自动 catch-up `[last_distill, 昨天]` 区间，不会漏处理
### D. 上下文窗口可扩展
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#d-]
#### US-0400 raw 累积不撑爆 LLM
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#us-0400-raw--llm]
- US-0400: 作为 louke 长期使用方（1 年 + 数百 session），我希望 raw 累积超出任何模型窗口时，蒸馏仍能完成 —— 通过自动分块 / 选用大模型 / Map-Reduce 等策略
- US-0410: 作为常规使用方（数月内 < 200 session），我希望默认走"增量"模式，**不**消耗大模型 quota
### E. 文档对齐
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#e-]
#### US-0500 Librarian Identity 框架对齐
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#us-0500-librarian-identity-]
- US-0500: 作为 agent prompt 维护者，我希望 Librarian 的 §1 Identity / §2 tools 段框架对齐 Devon.md（英文），便于跨 agent 培训新人
---
## 2. 关键场景
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#2-]
### scenario-0100 整体重写（incremental 模式）
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#scenario-0100-incremental-]
```
# 现状: raw/ 有 14 条 resolved session, pages/ 有 3 条旧 wiki
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#-raw---14--resolved-session-pages---3--wiki]
$ ls .louke/raw/2026-06-*/
...14 个 *.md 文件, 全部 status: resolved
$ ls .louke/wiki/pages/
old-decision-x.md  old-api-v1.md  old-feature-y.md
# 1. compact: 准备 bundle
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#1-compact--bundle]
$ lk librarian compact
[compact] 扫描 raw: 14 条 resolved
[compact] 写 bundle: .louke/wiki/.compact-bundle.md (含全部 14 raw + 现有 3 pages)
[compact] 更新 .cache.toml: last_distill = 2026-07-04
# 2. rewrite: LLM 整体重写 (cron 不自动跑; 用户手动或 --auto-rewrite)
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#2-rewrite-llm--cron-----auto-rewrite]
$ lk librarian rewrite
[rewrite] shell-out: opencode run --agent librarian -- <prompt>
... LLM 读 bundle → 重写 pages/ → 调 lk librarian rebuild-index + lint ...
[rewrite] exit 0
# 3. 结果
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#3-]
$ ls .louke/wiki/pages/
current-decision-x.md     # 旧 "old-decision-x" 已过期, 被新名替换
current-api.md            # 旧 "old-api-v1" 与新决策合并
new-feature-z.md          # 全新条目
# 注意: 不再有 old-* 前缀; 旧 "old-api-v1.md" 因过期被整体替换
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#--old----old-api-v1md-]
$ lk librarian lint
=== Wiki Lint ===
[broken links] 0
[orphaned pages] 0
→ wiki 健康
```
### scenario-0200 cron 跳日 catch-up
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#scenario-0200-cron--catch-up]
```
# 用相对日期: Day N 表示"今天" (= cron 实际触发日).
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#-day-n---cron-]
# 关键不变式: 窗口上限始终是"昨天" (今天 - 1), 不是"今天".
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#-----1-]
# 这与 cmd_compact 实现一致: yesterday = (today - timedelta(days=1)).isoformat()
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#-cmd_compact--yesterday--today---timedeltadays1isoformat]
$ crontab -l
0 4 * * * cd <project> && lk librarian compact >> .louke/wiki/.cron.log 2>&1
# ===== Day 1 (周四) — 正常运行 =====
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#-day-1----]
[compact] cache.last_distill 未设置, 从 1970-01-01 开始处理所有历史 raw
[compact] 蒸馏窗口: [1970-01-01, Day0]   # yesterday = Day1 - 1 = Day0
[compact] token 估算: <N>  (M0 模式)
[compact] 写 .compact-bundle.md
[compact] → .cache.last_distill: (unset) → Day0
# ===== Day 2 (周五) — 机器关机, cron 没跑 =====
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#-day-2----cron--]
# (no log entry)
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#no-log-entry]
# ===== Day 3 (周六) — 开机, cron 重新触发 =====
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#-day-3----cron--]
[compact] 上次蒸馏: Day0 (跳过了 Day1)
[compact] 蒸馏窗口: [Day0, Day2]      # yesterday = Day3 - 1 = Day2, catch-up 跨 3 天
[compact] → .cache.last_distill: Day0 → Day2
# ===== Day 4 (周日) — 正常运行 =====
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#-day-4----]
[compact] 上次蒸馏: Day2
[compact] 蒸馏窗口: [Day2, Day3]      # yesterday = Day4 - 1 = Day3
[compact] → .cache.last_distill: Day2 → Day3
```
**易错点**（实施时注意）：
- 窗口上限 = `date.today() - timedelta(days=1)`，**不是** `date.today()`
- 若 cron 在凌晨 04:00 跑，"今天"是 cron 触发日；昨天 = cron 触发日 - 1
- 跳日 catch-up 时窗口可能跨度大（3 天、7 天），仍按 `[last_distill, yesterday]` 计算
### scenario-0300 上下文窗口超出（Map-Reduce 模式 M2）
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#scenario-0300-map-reduce--m2]
```
# 累积 1 年: 400K tokens 超出任何模型窗口
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#-1--400k-tokens-]
$ lk librarian compact
[compact] 总 token 估算: 412,500 (超出 200K 阈值)
[compact] 按月分块: 12 个 bundle
+ .compact-bundle-2026-01.md (32K)
+ .compact-bundle-2026-02.md (35K)
...
+ .compact-bundle-2026-12.md (38K)
+ .compact-bundle-manifest.md (引用所有 12 bundle)
[compact] 更新 .cache.toml: last_distill = 2026-12-31
$ lk librarian rewrite
[rewrite] 检测到 13 个文件 (12 monthly + 1 manifest)
[rewrite] Map phase: 调用 12 次 opencode run --agent librarian (每块产 mini-distillation)
[rewrite] Reduce phase: 调用 1 次 opencode run --agent librarian (合并所有 mini-distillation)
[rewrite] exit 0
```
### scenario-0400 LLM 在 CLI 模式下不弹问题
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#scenario-0400-llm--cli-]
```
# cron 跑 lk librarian rewrite
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#cron--lk-librarian-rewrite]
$ opencode run --agent librarian -- "..."
[OpenCode session 启动, librarian 作 primary]
[OpenCode] Agent has 200K context, 400K tokens incoming
[OpenCode] Token 超出, model gemini-1.5-pro 自动选用 (louke models bind)
... LLM 推理 ...
[OpenCode] Wrote .louke/wiki/pages/current-decision-x.md
[OpenCode] Wrote .louke/wiki/pages/current-api.md
[OpenCode] exit 0
# 注意: LLM 没有调 question 工具 (CLI 无 UI, permission.question: deny 阻止)
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#-llm--question--cli--ui-permissionquestion-deny-]
# 这是设计行为, 不是 bug
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#--bug]
```
---
## 3. 功能需求
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#3-]
### A. 知识蒸馏（Karpathy 化）
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#a-karpathy-]
#### FR-0070 三原则
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-0070-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
基于 Karpathy [autoresearch](https://github.com/karpathy/autoresearch) 的 `train.py` 模型：
1. **`raw/` = journal**：所有 Agent session append-only；保留试错、未决、过时决策；不删不改
2. **`pages/` = current understanding (projection)**：每次更新是**整体重写**，不是 patch；过期条目随重写消失
3. **python 脚本不直接调用 LLM SDK**：脚本只做机械工作（compact / lint / rebuild-index）；distillation 推理通过 `opencode run --agent librarian` CLI 入口完成（P2-9 修正）。"不调 LLM API" 措辞特指不 `import openai / anthropic SDK` 发送 HTTP 请求
#### FR-0080 `lk librarian compact` / `lk librarian rewrite`
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-0080-lk-librarian-compact---lk-librarian-rewrite]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
**删除** `cmd_from_raw`（错误：机械 copy raw → pages，违反"投影而非积累"）。
**新增**两个子命令：
##### `lk librarian compact`
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#lk-librarian-compact]
- **谁做**：python 脚本（cron 友好）
- **做什么**：
0. **清理旧 bundle**（FR-0140.2）：删除 `.compact-bundle*.md`（P0-3 / P1-4）
1. 扫描 `.louke/raw/**/*.md` 找 `status: resolved` 条目
2. **无 `date` 字段的条目跳过 + warning**（P1-8，详见下方）
3. 按 `date` 字段过滤 `[last_distill, 昨天]`
4. 拼出 `.louke/wiki/.compact-bundle.md`，含：
- 所有匹配 raw 全文（append-only 不可修改）
- 现有 `pages/` 内容（如存在）
- 蒸馏指令（基于 raw + 现有 pages 整体重写，保留仍成立决策，删除/更新过时决策，补充新主题，每条 wiki 决策必须能从 raw 找到依据）
5. 更新 `.louke/wiki/.cache.toml` 的 `last_distill = 昨天`
6. **若 token 估算 > 阈值**：按月分块产 `.compact-bundle-{YYYY-MM}.md` + 末尾 `.compact-bundle-manifest.md`（参 FR-0140；manifest 仅列 sub-bundle 路径，rewrite 走真 Map-Reduce，Qoder #4 / #7）
- **副作用**：只写 `.compact-bundle*.md` + `.cache.toml`；**不**写 `pages/`
- **幂等**：再跑一次若无新 resolved raw，bundle 内容不变 + cache 不变（P2-11 修正）
- **`--dry-run`**：仅打印计划，不写文件、不更新 cache、不清理 bundle
**P1-8 — 无 `date` 字段的 raw 处理**：
无 `date` 字段的 raw 条目被**跳过 + warning**（不进入 bundle，不计入 M0/M1/M2 token 估算）：
```python
date_m = re.search(r'^date:\s*(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
file_date = date_m.group(1) if date_m else ''
if not file_date:
skipped_no_date.append(fp)
continue
```
**理由**：
- 无 `date` 的条目无法参与 `[last_distill, 昨天]` 窗口过滤
- 无 `date` 也无法参与 M2 按月分块
- 若无条件包含，会污染重写结果（LLM 无法判断该决策的时间边界）
- warning 而非报错：保留人工修复入口（用户可补 `date` 字段后再跑 compact）
**输出**（stdout）：
```
[compact] WARN: 3 个 raw 条目无 date 字段, 已跳过:
- .louke/raw/2026-06-15/no-date-1.md
- .louke/raw/2026-06-22/no-date-2.md
- .louke/raw/2026-07-01/no-date-3.md
```
##### `lk librarian rewrite`
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#lk-librarian-rewrite]
- **谁做**：python 脚本 → shell out → **`opencode run --agent librarian`**（CLI 模式，参 FR-0130）
- **python 脚本职责**（轻量，不调 LLM API）：
1. 检查 `.compact-bundle.md` 存在（compact 必须先跑）
2. shell out：`opencode run --agent librarian [--model <id>] -- <prompt>`，prompt 含 bundle 路径 + 蒸馏指令
3. 捕获 exit code（0 = rewrite 完成且 lint 通过；1 = 失败）
4. 退出码透传给 cron / 调用方
- **LLM 在 OpenCode 内做什么**（由 Librarian prompt 驱动，**基线版**见 FR-0130；**M2 扩展版**按月分块 map → 合并 reduce，见 FR-0140.3 P2-14 澄清）：
1. 读 `.louke/wiki/.compact-bundle.md`（bundle = raw 全文 + 现有 pages/ + 蒸馏指令）
2. 读 `.louke/wiki/pages/` 全部现存页面
3. **整体重写** pages/：
- 保留仍成立的决策
- 删除/合并过时的
- 补充新出现的主题
- 每条 wiki 决策必须能从 raw 中找到依据（quote dialogue 语法，详见 v0.4-004-quote-dialogue）
4. **不**保留旧 page 文件名 —— 重写后整体替换
5. 重写后调 `lk librarian rebuild-index` + `lk librarian lint`
- **Librarian 在 CLI 模式下行为差异**（v0.6-009 已支持）：
- `permission.question: deny` —— CLI 模式无 UI，匹配现有 deny 配置，无需改 frontmatter
- `permission.edit: allow` —— CLI 模式仍允许写 `pages/`
- prompt 区分两种调用模式（参 FR-0120.1）
#### FR-0090 cron 触发 + 跳日 catch-up
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-0090-cron----catch-up]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
cron 入口（由 **FR-0150** 安装）跑 `lk librarian compact`（**不**含 rewrite）。
**窗口逻辑**（在 `cmd_compact` 内）：
- 读 `.cache.toml:last_distill`
- 若为空 → 首次运行，window = `[1970-01-01, 昨天]`（处理所有历史）
- 否则 → window = `[last_distill, 昨天]`（处理上次到今天）
- 跑完后 `.cache.toml:last_distill = 昨天`
**跳日语义**：若周四 cron 失败，周六重跑，window = `[2026-07-02, 2026-07-04]`，catch-up 跨 3 天。
**rewrite 触发**：默认**不**由 cron 触发（避免半夜 token 烧光 + 需人工审视重写结果）。可选 `--auto-rewrite` flag 让 cron 跑 `compact` + `rewrite` 双步。
#### FR-0100 raw = append-only journal
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-0100-raw--append-only-journal]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
- `raw/` 不进 git（写入 `.gitignore`）
- python 脚本不删 / 不改 raw 下任何文件（除 `compact` 写入 `.compact-bundle*.md` 在 wiki/，不在 raw/）
- 各 source agent 自己写 raw（Librarian **不**写 raw）
- `status` 字段语义：Agent 写 raw 时必填 `status: open | resolved | superseded`；Librarian 仅读 `status: resolved`
#### FR-0110 `lk librarian lint` 适配
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-0110-lk-librarian-lint-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
`cmd_lint` 当前**已实现**的检查（librarian.py:79-129）：
- broken links（`[[wikilink]]` 目标不存在）
- orphaned pages（无任何 wikilink 引用）
**首次实现**检查项（P2-12 修正 — 现状代码无，FR-0110 首次落地）：
- **缺 frontmatter 必填字段**（`type` / `date` / `title`） → high 严重度
- **重复主题**（多 page 描述同一主题） → 提示合并（**不自动合并**，由人决策）
**注**：P2-13 — 现有 `cmd_rebuild_index`（librarian.py:131-151）只生成扁平 `- [[stem]] (path)` 列表，未实现 Librarian.md §4 "按类型 + 按日期" 二维布局。本 spec 不修复（v0.7-003 处理），但需知晓：rewrite prompt 让 LLM 调 `rebuild-index` 后，index.md 会是扁平列表，与 §4 agent prompt 不一致。
---
### B. LLM 调度机制
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#b-llm-]
#### FR-0130 `lk librarian rewrite` 通过 `opencode run --agent` 调 LLM
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-0130-lk-librarian-rewrite--opencode-run---agent--llm]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
**问题**：cron 跑 `lk librarian rewrite` 时需要 LLM 写 pages/。python 脚本**不**调 LLM API（避免 SDK 耦合 + token 计费穿透 python）。需要 OpenCode 提供 CLI 入口调 LLM 跑 agent。
**方案**：shell out 到 `opencode run --agent librarian -- <prompt>`，由 OpenCode 在新 session 内启 LLM 跑 Librarian primary，agent 自行完成 pages/ 重写。
**实现**（`louke/librarian.py:cmd_rewrite`）：
```python
def cmd_rewrite(args):
"""触发 LLM 整体重写 pages/. 调用 opencode run --agent librarian."""
bundle = Path.cwd() / '.louke' / 'wiki' / '.compact-bundle.md'
if not bundle.exists():
print('error: .compact-bundle.md 不存在, 请先跑 lk librarian compact', file=sys.stderr)
return 1
if args.dry_run:
print(f'[dry-run] 将 shell-out: opencode run --agent librarian [--model {args.model}] -- <prompt>')
return 0
prompt = f'''
你是 Librarian subagent，处于 CLI 批处理模式（通过 `opencode run --agent librarian` 启动）。
任务：基于 raw 整体重写 wiki pages/。
输入：
1. 读 {bundle}（含 raw 全文 + 现有 pages/ + 蒸馏指令）
2. 读 .louke/wiki/pages/ 全部现存页面
输出：
1. **整体重写** .louke/wiki/pages/（不是 patch）：
- 保留仍成立的决策
- 删除/合并过时的
- 补充新出现的主题
- 每条 wiki 决策必须能从 raw 中找到依据（quote dialogue 语法）
2. 跑 `lk librarian rebuild-index` 重建 index.md
3. 跑 `lk librarian lint` 健康检查；如有 broken links / 缺失 frontmatter 自愈
完成后 exit 0。如 lint 不过自愈不了 exit 1。
'''
cmd = ['opencode', 'run', '--agent', 'librarian']
if args.model:
cmd += ['--model', args.model]
cmd += ['--', prompt]
rc = subprocess.run(cmd).returncode
return rc
```
**`opencode run --agent` 行为契约**（基于 v0.6-009 FR-0070.7）：
| 维度 | TUI `task` 工具 | CLI `opencode run --agent` |
|---|---|---|
| 调用者 | Maestro 在主会话内 | python 脚本 / 用户 shell |
| agent 角色 | subagent（隔离子会话） | primary（新 session） |
| `permission.question: allow` 行为 | 弹框冒泡到主窗口 | 无 UI，prompt 走 stdout |
| 适用 | Louke 工作流（M-FOUND → ...） | **cron 批处理 / CI** ← FR-0130 |
| 退出码 | 由 OpenCode 子会话退出码 | 由 OpenCode session 退出码 |
**为什么选 `opencode run --agent librarian` 而不是别的方式**：
| 替代方案 | 否决理由 |
|---|---|
| python 直接调 LLM API（OpenAI / Anthropic SDK） | 需 SDK 依赖 + token 计费穿透 + 模型路由与 louke `models.py` 解耦 |
| python 调 OpenCode HTTP API | OpenCode 没有公开 HTTP API |
| **CLI `opencode run --agent`** | **唯一非交互式调度路径，与 louke 模型路由一致，无 SDK 依赖** |
**Librarian prompt 适配（FR-0120.1）**：
`louke/agents/Librarian.md` 加 §"调用模式识别"段：
> 你可能被两种方式调起：
> 1. **TUI subagent 模式**：Maestro 调 `task` 启动你；可调 `question` 工具向用户提问
> 2. **CLI 批处理模式**：`opencode run --agent librarian -- "..."` 启动你（无 UI）；你**不**应调 `question`（无 UI 会卡住）
>
> 在 CLI 模式下，按 FR-0130 prompt 完成整体重写；完成后正常 exit。
---
### C. 上下文窗口应对
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#c-]
#### FR-0140 分层蒸馏策略
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-0140-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
**问题**：louke raw 累积速度远超任何模型上下文窗口：
| 时间窗 | session 数（估） | 累计 token | 适配窗口 |
|---|---|---|---|
| 1 周 | 5-10 | 5K-15K | 所有模型 OK |
| 1 月 | 20-50 | 30K-80K | 32K+ 模型 |
| 1 quarter | 60-150 | 100K-250K | Claude Sonnet 200K / Gemini 1.5 Pro |
| 1 年 | 200-500 | 400K-1M | **超出所有模型**，必须分块 |
**核心策略**：按 token 量自动选择蒸馏模式。
##### FR-0140.1 模式选择表（由 `cmd_compact` 自动判定）
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-01401--cmd_compact-]
| 模式 | 触发条件 | 总 token | 蒸馏路径 | LLM 调用次数 |
|---|---|---|---|---|
| **M0: 增量模式**（默认） | `last_distill - yesterday` 区间 ≤ 50K tokens | ≤ 50K | 单次 `opencode run --agent librarian`，bundle 全量喂入 | 1 |
| **M1: 全量模式** | 50K-200K tokens | 50K-200K | 单次，但用 `--model` flag 指定 200K+ 模型 | 1 |
| **M2: Map-Reduce 模式** | 200K-1M tokens | 200K-1M | 按 issue / 月分块 map → reduce 合成 | 块数 + 1 |
| **M3: 层级摘要模式** | > 1M tokens | > 1M | 多层摘要索引（罕见，v0.7.1+） | 多轮 |
##### FR-0140.2 `cmd_compact` 自动分块（实现要点）
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-01402-cmd_compact-]
```python
def cmd_compact(args):
# 1. 清理旧 bundle (P0-3 + P1-4: bundle 不持久化)
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#1--bundle-p0-3--p1-4-bundle-]
_cleanup_old_bundles(wiki_dir)  # 删除 .compact-bundle*.md
matched, skipped_no_date = scan_resolved_raw(since=args.since, until=yesterday())
if skipped_no_date:
print(f'[compact] WARN: {len(skipped_no_date)} 个 raw 无 date 字段, 已跳过')
total_tokens = estimate_tokens(matched)  # 字符数 / 4 估算
if total_tokens <= 50_000:
# M0: 单 bundle
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#m0--bundle]
write_bundle('.compact-bundle.md', matched)
elif total_tokens <= 200_000:
# M1: 单 bundle 但打 warning 提示用大模型
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#m1--bundle--warning-]
write_bundle('.compact-bundle.md', matched)
print(f'[compact] WARN: bundle={total_tokens} tokens, 建议 --model gemini-1.5-pro')
else:
# M2: 按 month 分块
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#m2--month-]
grouped = group_by_month(matched)
for month, entries in grouped.items():
write_bundle(f'.compact-bundle-{month}.md', entries)
write_manifest('.compact-bundle-manifest.md', list_of_bundles=True)
```
**Bundle 清理（**P0-3 / P1-4**）**：
- **为什么清理**：bundle 是 compact 的中间产物（rewrite 一次性消费），不持久化。若不清理：
- 磁盘累积（每次 compact 写 1+ 个 bundle）
- **M2 误判**：旧 `.compact-bundle.md` 残留时，`cmd_rewrite` 的 `glob('.compact-bundle*.md')` 会把它当作第 N 个 map 输入，产生重复 mini-distillation
- **清理时机**：`cmd_compact` 步骤 1（在 scan 之前），删除所有 `.compact-bundle*.md`（含 `.compact-bundle.md` / `.compact-bundle-{YYYY-MM}.md` / `.compact-bundle-manifest.md`）
- **不在 `.cache.toml` 清理**：cache 含 `last_distill`，是持久状态，bundle 是临时产物
- **dry-run 不清理**：避免 dry-run 副作用
##### FR-0140.3 `cmd_rewrite` 多模式支持
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-01403-cmd_rewrite-]
```python
def cmd_rewrite(args):
bundles = sorted(glob('.compact-bundle*.md'))
single = '.compact-bundle.md'
if single in bundles and len(bundles) == 1:
# M0/M1: 单次 LLM 调用
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#m0-m1--llm-]
prompt = build_single_prompt(bundles[0])
return opencode_run('--agent', 'librarian', '--model', args.model, prompt)
if all(b for b in bundles if b.endswith('-manifest.md')):
# M2: Map-Reduce
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#m2-map-reduce]
for b in bundles[:-1]:  # map phase
prompt = build_map_prompt(b)
opencode_run('--agent', 'librarian', '--model', args.model, prompt)
# reduce phase
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#reduce-phase]
prompt = build_reduce_prompt(bundles[-1])  # manifest bundle
return opencode_run('--agent', 'librarian', '--model', args.model, prompt)
```
##### FR-0140.4 `--model` flag 与优先级链（P1-7 修正）
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-01404---model-flag-p1-7-]
`lk librarian rewrite` 的模型选择按以下**优先级链**解析（高 → 低）：
```
1. --model <id>             (CLI 显式指定, 透传给 opencode run --model)
2. --model-from-config      (调 `lk models bind --get-current` 取绑定模型)
3. frontmatter models: 第一项 (OpenCode 默认)
```
**实现（`cmd_rewrite`）**：
```python
model_flag = []
if args.model:
model_flag = ['--model', args.model]                            # 优先级 1
elif args.model_from_config:
try:
bound = subprocess.run(['lk', 'models', 'bind', '--get-current'],
capture_output=True, text=True, check=False)
if bound.returncode == 0 and bound.stdout.strip():
model_flag = ['--model', bound.stdout.strip()]          # 优先级 2
except FileNotFoundError:
pass
# 优先级 3: 不传 --model, OpenCode 用 frontmatter models: 第一项
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#-3----model-opencode--frontmatter-models-]
```
**冲突规则**：
- `--model` 与 `--model-from-config` **同时传** → `--model` 胜出（`--model-from-config` 静默忽略，不报错；这样 cron 脚本可无条件加 `--model-from-config` 而人临时 `--model` 时不冲突）
- 都不传 → 不传 `--model` 给 OpenCode，OpenCode 用 Librarian frontmatter 的 `models:` 列表第一项
**上下文窗口超阈值 fallback**：
| 模式 | token 量 | 推荐模型 |
|---|---|---|
| M0 (≤ 50K) | frontmatter 第一项即可 | `minimax-2.7` / `deepseek-v4-flash`（Louke 默认） |
| M1 (50K-200K) | `--model` 显式指定 | `claude-sonnet-4` (200K) |
| M2 (200K-1M) | `--model` 必显式 | `gemini-1.5-pro` (1M) |
超阈值时**不**自动 fallback（避免静默换模型让用户疑惑），由 cmd_rewrite 打 stderr warning 提示：
```bash
# M2 模式下用户忘了 --model
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#m2----model]
$ lk librarian rewrite
[rewrite] WARN: bundle=412K tokens (M2), 当前模型 minimax-2.7 (32K context)
[rewrite] WARN: 建议 --model gemini-1.5-pro (1M context) 或 claude-sonnet-4 (200K)
[rewrite] shell-out: opencode run --agent librarian -- <prompt>
# (不阻止, 但 LLM 收到 bundle 后会报 token 不足)
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#--llm--bundle--token-]
```
**注**：本 spec **不**估算 frontmatter `models:` 列表中各模型的上下文窗口（这是 louke 模型路由层职责，不在 v0.7-002 范围）。M2 模式 + 未指定 `--model` 时 Louke 应通过 `lk models bind` 路由到合适的模型（用户责任）。
##### FR-0140.5 Karpathy 风格：增量优先
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-01405-karpathy-]
**默认走 M0**：cron 每日触发，只处理 `[last_distill, 昨天]` 区间，正常情况 ≤ 50K tokens。M1/M2 仅在 catch-up 跨多日 + 累积历史大时触发。
**为什么不全量重写**：
- 全量每次跑耗时 + 耗 token 高
- 大多数日子没有新决策，旧决策不需要重写
- 增量保留"近期决策稳定"的属性，符合 wiki = current understanding 语义
**什么时候全量重写**：
- 用户显式 `lk librarian rewrite --full`（覆盖默认增量）
- v0.7.1+ 加 `--periodic-full` 自动每季度触发（待设计）
##### FR-0140.6 RAG 备选方案（v0.7.1+ 备选，**本 spec 不实现**）
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-01406-rag-v071--spec-]
如果 M2 也不够（> 1M tokens）：
| 方案 | 优势 | 劣势 | 选型 |
|---|---|---|---|
| 向量检索 (RAG) | 扩展性最强，按 page 主题取 top-K raw | 需向量库 + embedding 依赖 | 留 v0.7.1+ |
| 文件级 RAG (grep + LLM 选) | 无新依赖，LLM 自己选 | LLM 可能漏选 | **本 spec 默认走这条**（FR-0140.5 增量模式） |
| Map-reduce + 摘要索引 | 中等开销，无新依赖 | 摘要丢失细节 | M2 模式（FR-0140.1） |
本 spec **默认增量**（M0），**兜底 map-reduce**（M2），**不引入向量库依赖**。理由：
1. louke 1-2 个 milestone 内 raw 累计不会 > 1M tokens
2. 增量模式与"raw = journal / pages = projection"的 Karpathy 模型一致
3. 引入向量库是 infra 重决策，应单独 spec
##### FR-0140.7 token 估算（实现）
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-01407-token-]
`cmd_compact` 估算 `total_tokens` 用简单启发式：
```python
def estimate_tokens(raw_entries: list[Path]) -> int:
total_chars = sum(p.stat().st_size for p in raw_entries)
return total_chars // 4   # ~4 chars / token 经验值
```
`--threshold-tokens` flag 让用户覆盖默认 50K / 200K 阈值（高级用户调优）。
---
### D. Agent 文档对齐
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#d-agent-]
#### FR-0120 Librarian Identity 框架对齐
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-0120-librarian-identity-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
`louke/agents/Librarian.md` §1 + §2 改英文，框架对齐 Devon.md：
**§1 Identity & Runtime Context** — 英文：说明 subagent 模式 + 非交互 + raw assumption 处理
**§2 tools, skills and permissions** — 英文：
- §2.1 tools：`bash` + `read` + `edit` + `grep` + `glob` 允许；`task` + `question` + `webfetch` + `websearch` + `external_directory` + `doom_loop` 拒绝；附 `lk librarian` CLI 表（含 `compact` / `rewrite` / `lint` / `rebuild-index` / `distill`）
- §2.2 skills：`inline-comments` + `reserve-memory`
- §2.3 permissions：明确允许 `edit` 的范围（`pages/*.md` via rewrite + `index.md` + `log.md` + `overview.md` + `.cache.toml`），禁止写入 raw/ + 业务代码 + spec 产物
**P1-6 — `.compact-bundle*.md` 写入权属澄清**：
| 文件 | 写入方 | 触发 |
|---|---|---|
| `pages/*.md` | LLM（via `opencode run --agent librarian` 的 `edit`） | rewrite 后 |
| `index.md` / `log.md` / `overview.md` | LLM `edit` + python CLI（`rebuild-index` / `lint`） | rewrite 后 / 手动 |
| `.cache.toml` | python CLI（`cmd_compact`） | 每次 compact |
| `.compact-bundle*.md` | **python CLI（`cmd_compact`）**，**不**经 LLM `edit` | 每次 compact |
LLM 的 `edit` 权限白名单仅限 `pages/*.md` + `index.md` + `log.md` + `overview.md`（参 v0.6-009 FR-0010.4）。bundle 文件由 python 脚本（cron 进程）写入，**不**受 LLM `edit` 权限约束。但 LLM 也不**应**触碰 bundle（不读不写），bundle 是 rewrite 的输入。
**Librarian 特性化**（与 Devon 区别）：
- `webfetch` / `websearch` / `external_directory`: **deny**（wiki 是本地内容，无外部查询需求）
- `edit` 范围：**限 wiki 命名空间**（其他 agent 是全项目 edit / 业务代码 edit）
- 工作流主线：trigger（cron daily / 手动）→ compact（python）→ rewrite（LLM via `opencode run --agent`）→ lint
- 不写业务代码 / spec 产物
#### FR-0120.1 调用模式识别段（CLI vs TUI）
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-01201-cli-vs-tui]
`louke/agents/Librarian.md` 加 §"调用模式识别"段（与 FR-0130 联动）：
> 你可能被两种方式调起：
> 1. **TUI subagent 模式**：Maestro 调 `task` 启动你（`mode: subagent`）；可调 `question` 工具向用户提问
> 2. **CLI 批处理模式**：`opencode run --agent librarian -- "..."` 启动你（`mode: primary` 新 session，无 UI）；你**不**应调 `question`（无 UI 会卡住，且 `permission.question: deny` 阻止）
>
> **检测方式**：看你是否在 OpenCode TUI 内（subagent 模式）还是 stdout（CLI 模式）。CLI 模式下按 FR-0080 prompt 完成整体重写；完成后正常 exit。
>
> **frontmatter 不变**：`permission.question: deny` 在两种模式下都安全（CLI 无 UI / TUI 子会话弹框冒泡不依赖此 permission）。
---
### E. cron 安装与目标命令
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#e-cron-]
#### FR-0150 `lk init --install-cron` 目标改为 `lk librarian compact`
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#fr-0150-lk-init---install-cron--lk-librarian-compact]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
**问题**：本 spec §0.2 FR-0090 引用"cron 入口（在 v0.7-001 安装）"，但 v0.7-001 范围是 pre-commit 接管，**不含** cron 安装。`louke/init.py:_install_cron()` 是本会话初版独立添加的，未纳入任何 spec。这导致 cron target 指向即将删除的 `lk librarian daily` 命令。
**方案**（v0.7-002 实施）：
- `louke/init.py:_install_cron()` 的 cron entry 从 `lk librarian daily` 改为 `lk librarian compact`（已在 `louke/init.py:167` 同步）
- v0.7-001 的 `lk scout install-precommit` 不再负责 cron 安装（cron 安装归 v0.7-002）
- v0.7-002 的 cron 安装由 `lk init`（默认开 `--install-cron`）或 `lk init --no-cron`（显式跳过）控制
**职责边界**（与 v0.7-001 / 后续 spec）：
| 任务 | spec 归属 |
|---|---|
| pre-commit 框架接管 lint/format/typecheck/test | v0.7-001 |
| cron 触发 `lk librarian compact` | **v0.7-002（本 FR-0150）** |
| pre-commit hook 的 `rev` 升级（`lk upgrade --precommit`） | v0.7+ 待定 |
---
## 4. 非功能需求
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#4-]
### NFR-0010 向后兼容（含 breaking change 显式声明）
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#nfr-0010--breaking-change-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
⚠️ **Breaking changes**：
1. **既有 `lk librarian from-raw` 调用者**：命令删除；改用 `lk librarian compact` + `lk librarian rewrite`
2. **既有 `lk librarian distill` 调用者**：保留，但语义改为"列出待 compact 的 raw"（wrapper 调 `cmd_compact --dry-run`）
3. **既有 `lk librarian daily` 调用者（本会话初版）**：命令删除；改用 `lk librarian compact`（cron 友好），`lk librarian rewrite` 显式触发
**非 breaking**：
- `lk librarian lint` / `lk librarian rebuild-index` 命令不变（FR-0110 是扩展）
- raw/ 不动（仅追加 `.gitignore` 排除）
- Librarian frontmatter `permission.question: deny` 不变（CLI 模式兼容）
- cron 入口从 `lk librarian daily` 改为 `lk librarian compact`（由 FR-0150 实施的 `--install-cron` 流程里调）
### NFR-0020 Python 3.9 兼容
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#nfr-0020-python-39-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
- `bool \| None` (PEP 604) 不使用
- 现有 `tuple` 无参数化已符合 py3.9
- 无强制新增依赖（不引入 tomli_w）
### NFR-0030 文档语言
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#nfr-0030-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
README / README.zh 双语同步；agent prompt 中英混排（§1 / §2 英文，§3+ 中文）。
### NFR-0040 可降级
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#nfr-0040-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
- `cmd_compact` 找不到 raw → 返回 `{}`，无错误
- `cmd_rewrite` 找不到 bundle → stderr 报错 "请先跑 compact"，exit 1
- `opencode run --agent librarian` 失败 → exit code 透传，cron 日志可查
- M2 Map-Reduce 中单次 map 失败 → stderr 报错 + 退出非 0（不静默继续）
### NFR-0050 可审计
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#nfr-0050-]
| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
- cron 日志追加到 `.louke/wiki/.cron.log`，可追溯每日 compact 结果
- `lk librarian compact --dry-run` 支持预览，便于人工审视
- `.compact-bundle.md` 是 raw + pages 的完整 snapshot，可作审计依据
- `lk librarian lint` 在 rewrite 后自动跑，失败立即可见
---
## 5. 澄清记录（review 后决定）
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#5-review-]
| Q | 议题 | Reviewer 建议 | Kilo 决定 |
|---|---|---|---|
| **Q1** (raw 累积超出上下文窗口) | 1 年后 raw 累计 400K-1M tokens，超出所有模型窗口 | **分层策略**：增量默认 (M0) / 全量大模型 (M1) / Map-Reduce (M2) / 层级摘要 (M3, 罕见, v0.7.1+)；不引入向量库依赖 | 接受，FR-0140 |
| **Q2** (Karpathy 增量 vs 全量) | 每次 cron 跑全量重写还是只增量 | **增量优先**：cron 默认 `[last_distill, 昨天]` 区间，正常情况 ≤ 50K tokens 单次喂入；全量用 `--full` flag 显式触发 | 接受，FR-0140.5 |
| **Q3** (LLM 调度机制) | cron 跑 rewrite 时如何调 LLM？python 调 API / TUI task / OpenCode CLI | **`opencode run --agent librarian`**（CLI 模式，唯一非交互路径） | 接受，FR-0130；v0.6-009 FR-0070.7 已定义 `opencode run --agent` 与 TUI `task` 的边界 |
| **Q4** (CLI 模式与现有 permission 兼容) | `permission.question: deny`（v0.6-009）是否适合 CLI 批处理 | **正好适合**（CLI 无 UI 不应 question）；frontmatter 不变，仅 prompt 区分模式 | 接受，FR-0130 / FR-0120.1 |
| **Q5** (raw 进 git?) | raw 是 journal 性质，不应分享 | 加 `.gitignore` 排除 `.louke/raw/` | 接受，FR-0100 |
| **Q6** (知识蒸馏为何放 v0.7-002 而非 v0.7-001) | v0.7-001 是 pre-commit 接管 gate，与本 spec 无关 | 拆分：v0.7-001 = pre-commit 接管；v0.7-002 = 知识蒸馏 Karpathy 化 | 接受，本 spec 只聚焦 wiki |
| **Q7** (向量库 RAG 何时引入) | raw 累积超 1M tokens 时 | v0.7.1+ 单独 spec；本 spec 默认增量 (M0) 兜底 map-reduce (M2) | 接受，FR-0140.6 |
| **Q8** (cmd_daily 命令去留) | 本会话初版的 `cmd_daily` 是否保留 | **删除**：拆分为 `compact` + `rewrite`；cron 只调 `compact`，`rewrite` 显式触发 | 接受，FR-0080 / FR-0090 |
### QoderWork 评审 (2026-07-05)
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#qoderwork--2026-07-05]
| Q | 议题 | Reviewer 建议 | Kilo 决定 |
|---|---|---|---|
| **P0-1** (scenario-0200 日期错) | 2026-07-02 是周四不是周五；窗口上限应为昨天不是今天 | 重写用相对日期 + 确认与 `cmd_compact` 实现一致 | 接受，已用 Day N 相对日期重写（scenario-0200） |
| **P0-2** (cron 入口虚假引用) | v0.7-001 不含 cron，引用是虚假 | 在 v0.7-002 新增 FR-0150 显式归属 cron 安装 | 接受，新增 FR-0150 |
| **P0-3** (M2 旧 bundle 被当 map 输入) | M0→M2 切换时 `.compact-bundle.md` 残留触发重复处理 | FR-0140.2 加清理逻辑 | 接受，FR-0140.2 已加 |
| **P1-4** (bundle 不清理) | 磁盘累积 | 清理逻辑放在 compact 步骤 1 | 接受，FR-0140.2 |
| **P1-5** (decisions/entries/consolidated.md) | 不在重写范围 | §0.4 明确状态：entries/consolidated.md deprecated；decisions 留 v0.7-003 | 接受，新增 §0.4 |
| **P1-6** (edit 白名单漏 bundle) | bundle 是 python 写不是 LLM edit | §2.3 注明 bundle 写入权属 | 接受，§2.3 加澄清段 |
| **P1-7** (model flag 优先级不清) | --model / --model-from-config / frontmatter 三者优先级 | FR-0140.4 明确优先级链 + 实现伪代码 | 接受，FR-0140.4 已加优先级表 |
| **P1-8** (无 date 字段 raw 处理) | 未定义 | 跳过 + warning | 接受，FR-0080 加 P1-8 段 |
| **P2-9** ("不调 LLM API" 措辞) | 改"不调 SDK，shell-out opencode" | 改写 | 接受，FR-0070 第 3 条已改 |
| **P2-10** (缺 quote-dialogue 引用) | 应引 v0.4-004 | 加引用 | 接受，FR-0080 已加 `(详见 v0.4-004-quote-dialogue)` |
| **P2-11** (幂等性松散) | 改写更精确 | 改"再跑若无新 raw，bundle + cache 不变" | 接受，FR-0080 compact 段已改 |
| **P2-12** (frontmatter 是 NEW) | 不是"保留" | 措辞改为"首次实现" | 接受，FR-0110 已改 |
| **P2-13** (rebuild-index 扁平) | 现状与 §4 agent prompt 不一致 | 标注为已有 bug，v0.7-003 处理 | 接受，FR-0110 注明 |
| **P2-14** (FR-0130 硬编码 prompt 矛盾) | 与 FR-0140.3 动态 prompt 矛盾 | 标注 FR-0130 为基线版，FR-0140.3 为扩展版 | 接受，FR-0080 rewrite 段已加标注 |
---
## 6. 关联文件
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#6-]
| 文件 | 改动 |
|---|---|
| `louke/librarian.py` | **删除** `cmd_from_raw` + `cmd_daily`（FR-0080：机械 copy + cron 旧入口被替代）；**新增** `cmd_compact`（拼 bundle + 写 cache + 清理旧 bundle FR-0140.2 + no-date warning FR-0080 P1-8 + M0/M1/M2 模式）；**新增** `cmd_rewrite`（shell-out `opencode run --agent librarian -- <prompt>`，FR-0130 + FR-0140.4 优先级链）；**新增** `--model` / `--model-from-config` / `--full` / `--threshold-tokens` / `--m2-threshold` flag；**保留** `cmd_distill` / `cmd_lint`（FR-0110 扩展：新增 frontmatter + 重复主题检查） / `cmd_rebuild_index`（已知 bug：扁平列表，P2-13） |
| `louke/init.py` | `_install_cron()` cron entry 从 `lk librarian daily` 改为 `lk librarian compact`（FR-0150，**已实施**于本 spec 起草期 init.py:167） |
| `louke/agents/Librarian.md` | §1 Identity 改英文；§2 tools / skills / permissions 改英文 + bundle 写入权属澄清（P1-6）；新增 `lk librarian` CLI 表（含 `compact` / `rewrite` / `distill` / `lint` / `rebuild-index`）；§5 改写（cron 触发 + compact/rewrite 子命令 + 窗口 [last_distill, 昨天] + M0/M1/M2 模式 + P1-8 no-date 处理）；明确 pages/ 写入权限；新增 §"调用模式识别"段（CLI vs TUI，FR-0120.1）；新增 §"上下文窗口策略"段（FR-0140） |
| `.gitignore` | 加 `.louke/raw/`（raw 是 journal，不分享）；加 `.louke/wiki/.compact-bundle*.md`（bundle 是临时中间产物，不持久化） |
| `.louke/wiki/entries/` | **DEPRECATED**（§0.4 P1-5）：Agent 不再写 entries；现有 7 个文件保留至 v0.7-003 决定迁移/删除 |
| `.louke/wiki/consolidated.md` | **DEPRECATED**（§0.4 P1-5）：同上处理 |
| `tests/test_librarian_compact.bats` | **新建**：FR-0080/0090/0140/0150 单元测试（compact 拼 bundle、写 cache、跳日 catch-up、token 估算触发分块、bundle 清理、no-date warning） |
| `tests/test_librarian_rewrite.bats` | **新建**：FR-0130/0140.4 单元测试（`opencode run --agent` shell-out 退出码透传、M0/M1/M2 模式选择、模型优先级链） |
| `README.md` / `README.zh.md` | 加"知识蒸馏（Karpathy 模型）"小节（FR-0070 三原则 + cron 流程图） |
---
## 附录 A: 与 v0.7-001 的边界
[source: project/specs/v0.7-002-knowledge-distillation-karpathy/spec.md#-a--v07-001-]
| 主题 | v0.7-001 (pre-commit) | v0.7-002 (本 spec) |
|---|---|---|
| 跨语言 lint/format/typecheck/test | **pre-commit 框架接管**（hook + `.pre-commit-config.yaml`） | 不涉及 |
| `lk keeper gate` 加载 quality-gates.toml | 不涉及（本 spec 已否决该方向） | 不涉及 |
| `lk init --install-cron` | **在 v0.7-002 FR-0150 实施**（cron 框架），cron TARGET 是 `lk librarian compact` | 引用其产出；不在 v0.7-001 重复实现 |
| `lk librarian compact` / `rewrite` | 不涉及 | **本 spec 实施** |
| 知识蒸馏 Karpathy 模型 | 不涉及 | **本 spec 实施**（FR-0070） |
| LLM 调度机制（`opencode run --agent`） | 不涉及 | **本 spec 实施**（FR-0130） |
| 上下文窗口应对（FR-0140 分层） | 不涉及 | **本 spec 实施** |
| 文档对齐（FR-0120 Librarian Identity） | 不涉及 | **本 spec 实施** |

## v0.7-003-inline-discussion-protocol

# v0.7-003 — Inline Discussion 协议 — Spec
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#v07-003--inline-discussion---spec]
- **Spec ID**: v0.7-003-inline-discussion-protocol
- **创建日期**: 2026-07-07
- **状态**: 草稿（待 QoderWork 二次 review）
- **作者**: Kilo
- **关联**:
- **替代** v0.6-016-quote-dialogue-protocol（作废）
- **依赖** v0.4-004-quote-dialogue（quote_parser.py 基础）
- **参考** QoderWork 评审 `review-2026-07-07.md`（10 个 P0/P1/P2 项已采纳）
---
## 0. 范围与边界
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#0-]
### 0.1 本 spec 收纳
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#01--spec-]
| 主题 | FR |
|---|---|
| skill 语法勘误 + 协议重命名为 `inline-discussion` | FR-0010 |
| **`_tools/discuss.py` 新建**（Layer 3：parser + 定位 + 写）| FR-0020 |
| **`lk discuss` CLI 新建**（Layer 2：5 子命令）| FR-0030 |
| agent 专属命令迁移（Layer 1：sage / lex / prisme 等）| FR-0040 |
| 5 元组定位 + Levenshtein 4 级降级查找 | FR-0050 |
| `is_ready` / `check-ready` 门禁迁移 | FR-0060 |
| v0.6-016 spec 作废标记 + cookbook 迁移 | FR-0070 |
| tests 迁移 | FR-0080 |
### 0.2 本 spec **不**收纳
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#02--spec-]
- v0.6-016 协议全文（作废）
- `inline-comments` skill（被 `inline-discussion` 替代）
- comment / admonition 类别（移除）
- 旧 5 元状态（`[open]` / `✓` / `[blocked-by-N]` / `[wontfix]` / `[superseded]`）简化为 3 元
### 0.3 三层架构（QoderWork P0-4）
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#03-qoderwork-p0-4]
```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: agent 专属命令 (内部调用 Layer 3)                  │
│   lk sage quote-check / lk sage record-lock / lk lex ...    │
└────────────────┬────────────────────────────────────────────┘
│ Python import
┌────────────────▼────────────────────────────────────────────┐
│ Layer 2: lk discuss 共享 CLI (内部调用 Layer 3)              │
│   query / start / reply / edit / set-status                  │
└────────────────┬────────────────────────────────────────────┘
│ Python import
┌────────────────▼────────────────────────────────────────────┐
│ Layer 3: louke/_tools/discuss.py 底层工具                    │
│   parser / 5 元组定位 / Levenshtein 4 级降级 / 写操作          │
└─────────────────────────────────────────────────────────────┘
```
**实施**：新建 `louke/_tools/discuss.py` 包含完整 parser/定位/写。`louke/__main__.py` 注册 `lk discuss` 子命令。`lk <agent> <cmd>` 内部调 `discuss.py` API。
---
## 1. 用户故事
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#1-]
> 完整 story 在 `louke/agents/_skills/inline-discussion/SKILL.md`。本 spec 直接以 skill 为规范，**不**重复。
**核心 5 条**：
1. **写**：用 `> **Speaker:**` 嵌套 blockquote 表示对话
2. **状态**：仅根评论行 `[STATUS]` 标记有效；嵌套回复方括号作普通文本
3. **RESOLVED 权限**：**仅发起人**（即根评论 speaker）能标 `[RESOLVED]`；其他人标无效
4. **REOPEN**：任何人都可设 REOPEN
5. **找会话断点**：agent 调 `lk discuss query --blocker <我的名字>` 看 3 类别（`unanswered` / `unresolved` / `awaiting_my_reply`）
---
## 2. 功能需求
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#2-]
### FR-0010 (核心) inline-discussion skill 验证 + 8 处勘误
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#fr-0010--inline-discussion-skill---8-]
**位置**：`louke/agents/_skills/inline-discussion/SKILL.md`
**已修 8 处**（QoderWork 列出 7 项 + 1 项 S6 thread_id 设计缺陷）：
| # | 行号 | 修正 |
|---|---|---|
| S1 | L3 | `description` 重写为 "Defines inline-discussion format for structured discussion in spec files. Use when agents need to leave traceable multi-round comments and query discussion status via lk discuss." |
| S2 | L104 | "输入为一个 `json`" → "输出为一个 JSON 数组" |
| S3 | L92 | "@方法" → "@mention" |
| S4 | L94 | "## 如何使用 inline-discussion skill?" → "## 6. 如何使用 inline-discussion"（编号修复） |
| S5 | L60 | `> [!attention]` 改为 `> **注意:**`（避免自相矛盾使用 admonition）|
| S6 | L112 | thread_id 设计缺陷（见 FR-0050 重写）|
| S7 | L135 | `--anchor` 标志未定义（见 FR-0050 新增 `lk discuss anchor`）|
| S8 | L113-121 | 4 元组 + SHA256 → 5 元组 + Levenshtein（见 FR-0050 完整设计） |
**AC**:
- AC-1: 8 处修正**逐条列出行号 + 内容摘要**（不依赖 "active file diff"）
- AC-2: `pyproject.toml [tool.setuptools.package-data]` 含 `agents/_skills/inline-discussion/SKILL.md`
- AC-3: skill **不**再出现 `python -m ...` 例子
- AC-4: skill 中 thread_id 描述与 FR-0050 一致（**不**含"SHA256 4 元组"）
### FR-0020 (Layer 3) `louke/_tools/discuss.py` 新建（parser + 定位 + 写）
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#fr-0020-layer-3-louke-_tools-discusspy-parser----]
**位置**：`louke/_tools/discuss.py`（**不**是 `louke/discuss.py`——QoderWork P0-4）
**模块导出 API**：
```python
@dataclass
class Thread:
thread_id: str                         # "T-001" 自增序号
initiator: str                         # 根评论 speaker
status: str                           # "open" | "resolved" | "reopen"
last_speaker: str                     # thread 最后说话的人
reply_count: int
snippet: str                          # 根评论 body 前 80 字
# 5 元组定位字段（QoderWork P0-2）
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#5-qoderwork-p0-2]
total_lines: int                      # 创建时文件总行数
anchor_line: int                      # 被评论内容行号
anchor_text: str                      # 归一化文本
root_line: int                        # 根评论 `>` 行号
root_text: str                        # 根评论归一化文本
class DiscussParser:
def parse_file(path: Path) -> ParseResult
def get_thread(self, thread_id: str) -> Thread
def find_thread(self, anchor_line, anchor_text, root_line, root_text) -> Thread  # 4 级降级查找
def add_thread(self, anchor_line, anchor_text, initiator, body, status="open") -> Thread
def add_reply(self, thread_id, body, speaker) -> None
def edit_comment(self, thread_id, depth, speaker, new_body) -> None
def set_status(self, thread_id, new_status, operator_speaker) -> None
def is_ready(self) -> tuple[bool, list[str]]  # 与 quote_parser 同接口
```
**5 元组定位字段**（QoderWork P0-2）：
| 字段 | 类型 | 含义 |
|---|---|---|
| `total_lines` | int | 创建时文件总行数（行号漂移修正用）|
| `anchor_line` | int | 被评论内容行号（快速跳转 hint）|
| `anchor_text` | str | 被评论内容（归一化）|
| `root_line` | int | 根评论 `>` 行号 |
| `root_text` | str | 根评论 speaker + body（归一化）|
**thread_id 格式**：`T-NNN`（per file 自增序号，**不**含位置/内容 hash）。parser 维护 `T-{max+1}` 计数器。
**归一化规则**：strip 首尾空白 + 合并连续空白为单空格 + Unicode NFC。**不改大小写，不去 markdown 格式**。
**speaker 大小写**：比较时 lowercase 归一化，显示保留原大小写。
**@mention 语法**（QoderWork P1-NEW-3 保留）：speaker tag 支持 `**@Speaker:**` 前缀表示"@提及某 agent"，与 `**Speaker:**` 等价。parser 在解析 thread 时收集 `mentioned_agents` 列表，`--blocker` filter 包含被 mention 的 agent（即使不是 last_speaker）。
**AC**:
- AC-1: `louke/_tools/discuss.py` 存在，导出 `Thread` / `DiscussParser` 类
- AC-2: `parse_file()` 解析 `[open]` / `[RESOLVED]` / `[REOPEN]` 三态；嵌套回复的方括号作普通文本（不识别）
- AC-3: `set_status()` 验证 RESOLVED 时 `operator_speaker == thread.initiator`，否则拒绝；REOPEN 不限
- AC-4: `is_ready()` 接口与 quote_parser 兼容（`ParseResult` 含 `is_ready: bool` + `ready_blockers: list[str]`）
- AC-5: thread_id 格式 `T-NNN`，per file 自增
- AC-6: 不解析 `<!-- -->` / `[!NOTE]` / `[!WARNING]` 等（comment + admonition 已移除）
- AC-7: 5 元组定位字段完整（`total_lines` / `anchor_line` / `anchor_text` / `root_line` / `root_text`）
- AC-8: **@mention 语法保留**（QoderWork P1-NEW-3）：parser 识别 `**@Speaker:**` 前缀；SKILL.md §2.2 示例 `> **Sage:** @Lex, ...` 有效
### FR-0030 (Layer 2) `lk discuss` CLI 新建（5 子命令）
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#fr-0030-layer-2-lk-discuss-cli-5-]
**位置**：`louke/__main__.py` 注册 `discuss` 顶级子命令（**不**用单独的 `louke/discuss.py` 间接层 —— QoderWork P2-1，直接在 `__main__.py` import + 注册）
**5 子命令**（QoderWork P0-4）：
```bash
# 1. query — 列出 thread（含 5 元组定位字段）
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#1-query---thread-5-]
# 注: P1-NEW-2 决定**不**新增 anchor 子命令, 因为 start 命令直接接受 anchor-line 行号
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#-p1-new-2--anchor---start--anchor-line-]
# `--blocker` 含义 (QoderWork P2-2 明确): 3 个类别
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#--blocker--qoderwork-p2-2--3-]
# - unanswered: 我 (--blocker 给的 agent) 起的对话, 无回复
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#--unanswered----blocker--agent--]
# - unresolved: 我起的对话, 最后一层回复未置 resolved
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#--unresolved---resolved]
# - awaiting_my_reply: @提及我的 thread, 最后一层既不是我也不是 resolved
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#--awaiting_my_reply--thread--resolved]
lk discuss query --file <path> [--initiator <agent>] [--blocker <agent>] [--status <s>] [--check-ready]
# 2. start — 创建新 thread（插在 anchor 段落后的空行之后）
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#2-start---thread-anchor-]
lk discuss start --file <path> --anchor-line <N> --speaker <agent> <message>
# 3. reply — 追加回复到 thread 末尾
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#3-reply---thread-]
# 5 元组定位字段 (anchor-line/anchor-text/root-line/root-text) 用于在行号漂移后定位 thread
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#5--anchor-line-anchor-text-root-line-root-text--thread]
lk discuss reply --file <path> --thread-id <id> \
--anchor-line <N> --anchor-text <t> --root-line <N> --root-text <t> \
--speaker <agent> <message>
# 4. edit — 修改自己某条评论（仅原作者; 多行内容保持 > 缩进）
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#4-edit-----]
lk discuss edit --file <path> --thread-id <id> \
--anchor-line <N> --anchor-text <t> --root-line <N> --root-text <t> \
--depth <N> --speaker <agent> <new_body>
# 5. set-status — 修改 thread 状态（RESOLVED 仅 initiator; REOPEN 任意人）
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#5-set-status---thread-resolved--initiator-reopen-]
lk discuss set-status --file <path> --thread-id <id> \
--anchor-line <N> --anchor-text <t> --root-line <N> --root-text <t> \
--status <resolved|reopen> --operator <agent>
```
**4 级降级查找**（QoderWork P0-2，在 start/reply/edit/set-status 命令里共用）：
```
Step 0: 计算行号偏移
current_total = len(file.readlines())
delta = current_total - thread.total_lines
adjusted_anchor = thread.anchor_line + delta
adjusted_root = thread.root_line + delta
Level 0 — 精确命中：
normalized(adjusted_anchor_line) == thread.anchor_text ?
AND normalized(adjusted_root_line) 含 speaker-tag 且 root_text 匹配 ?
→ 命中 ✓
Level 1 — Levenshtein 窗口搜索（行号漂移 + 内容微改）：
搜索范围 = adjusted_anchor ± max(|delta| + 5, 10) 行
对范围内每行计算 edit_distance(normalize(line), anchor_text)
找到距离最小候选 → 在其下方扫 blockquote 块
对块内根评论计算 edit_distance(normalize(root), root_text)
→ anchor 距离 ≤ max(5, len(text) * 0.2) AND root 距离 ≤ 阈值 → 命中 ✓
Level 2 — 仅根评论定位（锚点被大幅修改）：
全文扫根评论（depth=1 `>` 行）
对每个根评论计算 edit_distance(normalize(root), root_text)
→ 距离最小且 speaker 匹配 → 命中 ✓（更新 anchor）
Level 3 — 未找到：
返回 "thread not found" + 建议操作（重新 query）
```
**写操作语义**（QoderWork P0-4）：
| 场景 | 规则 |
|---|---|
| `start` 插入位置 | anchor 段落后的第一个空行之后；同 anchor 下多 thread 按时间顺序 |
| `reply` 插入位置 | thread 最后一行之后，与下一个 `>` block 之间空一行 |
| `edit` 内容替换 | 定位 depth+speaker 的评论；多行内容保持 `>` 前缀和缩进一致 |
| `set-status` 权限 | RESOLVED 仅 initiator；REOPEN 任意人 |
| 并发安全 | 用 `flock` 写 tmp 文件 → rename 覆盖；parse 失败回滚 |
| 空行分隔 | 写操作自动插空行（blockquote 间必须有空行 CommonMark 解析要求）|
**AC**:
- AC-1: 5 个子命令都注册并可调用
- AC-2: `query` 输出 JSON 含 thread 列表（每 thread 含 5 元组定位字段）
- AC-3: `start` 插在 anchor 段落后的空行之后
- AC-4: `reply` 追加到 thread 末尾（与下一个 `>` 间有空行）
- AC-5: `edit` 仅原作者可改；多行内容保持 `>` 缩进
- AC-6: `set-status` 验证 RESOLVED 权限（仅 initiator）
- AC-7: 4 级降级查找都实现
- AC-8: 并发安全用 `flock`；write 失败回滚
### FR-0040 (Layer 1) agent 专属命令迁移
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#fr-0040-layer-1-agent-]
**12 agent 全部**（QoderWork P1-1：spec 之前只列 5 个是错的，应全部迁移）：
| Agent | 旧 | 新 |
|---|---|---|
| **Sage** | `quote_parser` 引用 + quote-check | `lk sage quote-check`（内部调 `_tools/discuss.is_ready()`）|
| **Lex** | `quote_dialogue` 形式 | `lk discuss query` for review |
| **Prism** | M-ARCH 评审 `inline-comments` | M-ARCH 评审 `inline-discussion` |
| **Archer** | L43 + L246 `inline-comments` 引用 | 引用 `inline-discussion` skill |
| **Librarian** | L28 `quote_dialogue` 引用 | 引用 `inline-discussion` skill |
| **Scout** | （在 `.opencode/agents/` 中引用 quote）| 引用 `inline-discussion` skill |
| **Devon** | （在 `.opencode/agents/` 中引用 quote）| 引用 `inline-discussion` skill |
| **Maestro** | L113, L153, L160 quote 引用 | `lk discuss` louke + `lk sage record-lock` |
| **Keeper** | （间接依赖）| `lk discuss` louke |
| **Shield** | （e2e 报告引 spec）| `lk discuss` |
| **Judge** | （审计报告引 spec）| `lk discuss` |
| **Warden** | （spec/acceptance 留 quote）| `lk discuss` |
**AC**:
- AC-1: 12 agent prompt **不**再含 `quote_parser` / `quote_dialogue` / `quote dialogue` 字符串
- AC-2: 12 agent prompt **引用** `inline-discussion` skill（`agents/_skills/inline-discussion/SKILL.md`）
- AC-3: agent prompt 中 `lk discuss` 命令示例**不**用 `python` 写法
### FR-0050 (核心) 5 元组定位 + Levenshtein 4 级降级查找
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#fr-0050--5---levenshtein-4-]
**已在 FR-0020 + FR-0030 中实现**，本 FR 是**契约说明**（不重复实现细节）：
- thread_id = `T-NNN` 自增序号（**不**含 SHA256 4 元组）
- 定位 = 5 元组（`total_lines` / `anchor_line` / `anchor_text` / `root_line` / `root_text`）
- 4 级降级查找：精确命中 → Levenshtein 窗口 → 全文根评论 → 未找到
- 边界处理：行号漂移用 `delta = current_total - total_lines` 修正
**AC**: 同 FR-0020 AC-5 + FR-0030 AC-7。
### FR-0060 `is_ready` / `check-ready` 门禁迁移
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#fr-0060-is_ready---check-ready-]
**问题**（QoderWork P0-3）：Maestro `record-lock` 依赖 `quote-check exit 0` 做门禁。新协议下需要等效。
**等效命令**：
- `lk discuss query --file <path> --check-ready` — 输出 `is_ready: bool` + `ready_blockers: list[str]`
- 或 `lk sage record-lock` 内部调 `discuss.is_ready()`
**ready 判定**（与 quote_parser 兼容）：
- 单元 `yaml_resolved == "✅"`（**保留**——YAML 是 SKILL 不禁止的元数据）
- 单元下**所有 thread 状态 == "resolved"**（即 reopen / open 都算阻塞 —— QoderWork P0-NEW 修正）
- 单元 `is_explanatory` 不算 thread
**AC**:
- AC-1: `_tools/discuss.py` 导出 `is_ready()` 接口（与 quote_parser 兼容）
- AC-2: `lk discuss query --check-ready` CLI 命令输出 `is_ready: bool` + `ready_blockers: list[str]`
- AC-3: `lk sage record-lock` 内部调 `discuss.is_ready()`（**不**调 quote_parser）
- AC-4: `lk keeper gate` M-SPEC 阶段也用 `lk discuss query --check-ready` 替代 quote-check
### FR-0070 v0.6-016 spec 作废 + cookbook 迁移
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#fr-0070-v06-016-spec---cookbook-]
**v0.6-016 spec 作废**（QoderWork E 节）：
- 在 `.louke/project/specs/v0.6-016-quote-dialogue-protocol/spec.md` 头部加 `valid: false`（YAML 头部）+ supersede 注释指向 v0.7-003
- `_protocols/quote-dialogue.md` 删除（QoderWork P1-3）；改用 `_skills/inline-discussion/SKILL.md` 作单一信息源
- `pyproject.toml` 的 `package-data` 含 `agents/_skills/*/*.md`
**cookbook 迁移**（QoderWork P1-4）：
- `docs/cookbook.md` 加 "Inline Discussion" 段
- 自包含（不引用 `../` 或 `agents/` 路径）
- 覆盖：3-5 个真实 example + 语法 + 易错点清单
**AC**:
- AC-1: v0.6-016 spec 含 `valid: false`
- AC-2: `_protocols/quote-dialogue.md` 文件**不存在**
- AC-3: `pyproject.toml package-data` 含 `agents/_skills/*/*.md`
- AC-4: `docs/cookbook.md` 含 "Inline Discussion" 段（≥ 3 example）
### FR-0080 tests 迁移
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#fr-0080-tests-]
**新增** `tests/test_inline_discussion.bats`：
- `lk discuss start` 跑后 spec.md 含根评论
- `lk discuss reply` 跑后 spec.md 含回复
- `lk discuss query` 返回正确 JSON（含 5 元组）
- `lk discuss query --blocker` / `--initiator` 过滤正确
- `lk discuss edit` 仅原作者可改
- `lk discuss set-status` RESOLVED 仅 initiator
- 4 级降级查找（行号漂移 / Levenshtein）测试
- 写操作并发安全（flock）
**AC**:
- AC-1: **≥ 8 个 test cases 全部通过**（QoderWork P2-3: 4 级降级查找可拆为 4 子测试）
- AC-2: **不**修改其他 test 文件（仅修改 fixture 数据允许）
- AC-3: 新建 `tests/test_inline_discussion.bats`
---
## 3. 退出条件
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#3-]
- [ ] FR-0010: skill 8 处勘误完成（AC-1 逐行列出）
- [ ] FR-0020: `louke/_tools/discuss.py` 新建，API 完整
- [ ] FR-0030: `lk discuss` 5 子命令可调用（query / start / reply / edit / set-status）
- [ ] FR-0040: 12 agent prompt 迁移（**全部**）
- [ ] FR-0050: 5 元组定位 + Levenshtein 4 级降级查找实现
- [ ] FR-0060: `is_ready` 门禁迁移（`lk sage record-lock` 内部调 `discuss.is_ready()`）
- [ ] FR-0070: v0.6-016 spec 作废 + cookbook 迁移 + `_protocols/quote-dialogue.md` 删除
- [ ] FR-0080: `tests/test_inline_discussion.bats` 8 个 test cases 通过
---
## 4. 状态
[source: project/specs/v0.7-003-inline-discussion-protocol/spec.md#4-]
- 2026-07-07 Kilo 重写本 spec（QoderWork 首次 review 后采纳 P0-1/P0-2/P0-3/P0-4/P1-1 等核心修正）
- 等等二次 review

## v0.8-001-web-server

# v0.8-001 — Web Server 协作界面 — Spec
[source: project/specs/v0.8-001-web-server/spec.md#v08-001--web-server---spec]
- **Spec ID**: v0.8-001-web-server
- **创建日期**: 2026-07-08
- **状态**: 草稿（M-ARCH，待 closure pass）
- **关联**:
- **来源 story**: `story.md`
- **相关背景**: README 中的 issue `#79`（`louke serve` web UI）
- **相关协议**: `v0.7-003-inline-discussion-protocol`
> **Responsibility split**: 本文只描述需求本身，以及哪些边界已经决定。
> 具体技术栈、前后端分层、部署形态、实时同步机制、权限实现细节由 Archer 在 `M-ARCH` 决定。
> 可观察、可断言的通过条件统一写在 `acceptance.md`。
---
## 0. 范围与边界
[source: project/specs/v0.8-001-web-server/spec.md#0-]
### 0.1 本 spec 收纳
[source: project/specs/v0.8-001-web-server/spec.md#01--spec-]
| 主题                                                | FR 范围 |
| --------------------------------------------------- | ------- |
| 团队内多人可访问的 web server 工作台                | FR-0100 |
| 拖拽式模型绑定                                      | FR-0200 |
| 按 Agent / 按抽象角色两层绑定                       | FR-0300 |
| wiki 浏览与编辑                                     | FR-0400 |
| 设计文档浏览与编辑（spec / acceptance / test-plan） | FR-0500 |
| `inline-discussion` 渲染与编辑支持                  | FR-0600 |
| FR / NFR 卡片式渲染                                 | FR-0700 |
| 协作可见性与变更提示                                | FR-0800 |
| 常用 Markdown 格式渲染支持                          | FR-0900 |
| `inline-discussion` 的正文/讨论聚焦与折叠           | FR-1000 |
### 0.2 本 spec 不收纳
[source: project/specs/v0.8-001-web-server/spec.md#02--spec-]
- 前端框架、后端框架、状态管理、编辑器组件选型
- 单机部署、局域网部署、反向代理部署的具体实现方式
- 权限系统、身份认证、会话管理的具体方案
- 实时协作是 WebSocket、SSE、长轮询还是文件锁机制
- 是否拆分独立服务进程、是否引入数据库
### 0.3 关键设计原则
[source: project/specs/v0.8-001-web-server/spec.md#03-]
- web server 是 louke 工作流的可视化入口，不替代 `spec.md` / `acceptance.md` / `test-plan.md` / wiki 的 Markdown 源文件。
- UI 必须服务于现有流程约束，尤其是 `inline-discussion` 和 FR / NFR 的结构化约定，而不是发明另一套脱离文件的存储格式。
- 本期面向团队内部多人协作；即使具体权限模型待定，也不能把产品目标降级成“单人本地浏览器壳”。
---
## 1. 用户故事
[source: project/specs/v0.8-001-web-server/spec.md#1-]
### US-0010
[source: project/specs/v0.8-001-web-server/spec.md#us-0010]
story: 作为团队成员，我希望在浏览器中拖拽式绑定模型到 Agent 或抽象角色，这样我能直观看到当前模型编排关系并快速调整。
priority: P0
### US-0020
[source: project/specs/v0.8-001-web-server/spec.md#us-0020]
story: 作为团队成员，我希望直接在 web 页面中阅读和编辑 wiki，这样知识沉淀可以从命令行文件操作转为更低门槛的协作界面。
priority: P0
### US-0030
[source: project/specs/v0.8-001-web-server/spec.md#us-0030]
story: 作为团队成员，我希望在同一个 web 界面中阅读和修改 `spec.md`、`acceptance.md`、`test-plan.md`，这样需求、验收和测试设计可以集中协作。
priority: P0
### US-0040
[source: project/specs/v0.8-001-web-server/spec.md#us-0040]
story: 作为需求参与者，我希望设计文档中的 `inline-discussion` 能被良好展示和编辑，这样人与 Agent 的澄清链路保持可追踪。
priority: P0
### US-0050
[source: project/specs/v0.8-001-web-server/spec.md#us-0050]
story: 作为文档阅读者，我希望每个 FR / NFR 都以卡片形式展示关键元信息，这样我能更高效地浏览和过滤需求。
priority: P1
### US-0060
[source: project/specs/v0.8-001-web-server/spec.md#us-0060]
story: 作为文档阅读者，我希望设计文档在渲染时支持代码块、表格、列表等常用 Markdown 格式，这样 web 页面不会丢失 Markdown 文档应有的表达能力。
priority: P1
### US-0070
[source: project/specs/v0.8-001-web-server/spec.md#us-0070]
story: 作为文档阅读者，我希望 `inline-discussion` 默认弱化显示，并且可以在“看正文”和“看讨论”之间切换、折叠讨论，这样我能根据当前任务聚焦正文或讨论而不被噪声淹没。
priority: P1
## 2. 关键场景
[source: project/specs/v0.8-001-web-server/spec.md#2-]
### scenario-0010 模型绑定画布
[source: project/specs/v0.8-001-web-server/spec.md#scenario-0010-]
团队成员打开 web 工作台，看到左侧模型列表、右侧 Agent / 角色列表和当前绑定关系。用户把某个模型拖到某个 Agent 卡片上，页面即时显示新绑定；如果某个抽象角色已有默认绑定，界面也能展示其继承关系和覆盖关系。
### scenario-0020 wiki 协作
[source: project/specs/v0.8-001-web-server/spec.md#scenario-0020-wiki-]
团队成员在浏览器中打开 wiki 页面列表，进入某个 wiki 页面后可阅读现有内容、编辑 Markdown、保存改动，并在列表或详情中看到最后更新时间与最近修改痕迹。
### scenario-0030 设计文档协作
[source: project/specs/v0.8-001-web-server/spec.md#scenario-0030-]
团队成员在 web 工作台内切换 `spec.md`、`acceptance.md`、`test-plan.md`，可直接编辑正文、保留 Markdown 结构和锚点，并在需要澄清的段落附近发起或回复 `inline-discussion`。
### scenario-0040 需求卡片浏览
[source: project/specs/v0.8-001-web-server/spec.md#scenario-0040-]
文档阅读者打开 spec 页面时，不只看到原始 Markdown，还能以卡片视图浏览每个 FR / NFR 的标题、有效性、可测试性、决策状态和正文摘要，并快速跳回原文位置。
### scenario-0050 Markdown 富文本阅读
[source: project/specs/v0.8-001-web-server/spec.md#scenario-0050-markdown-]
文档阅读者打开 `spec.md` 或 wiki 页面时，能够在 web 界面里正确看到代码块、表格、列表等常用 Markdown 结构，而不是退化为一整块纯文本；需要编辑时，渲染和源码编辑之间的对应关系仍然清晰。
### scenario-0060 正文 / 讨论聚焦切换
[source: project/specs/v0.8-001-web-server/spec.md#scenario-0060----]
文档阅读者打开带有 `inline-discussion` 的设计文档时，默认看到较弱化的讨论显示；当他点击“看讨论”时，讨论区域变得更突出、正文相对退后；当他点击折叠时，可临时收起讨论线程以专注正文。
---
## 3. 功能需求
[source: project/specs/v0.8-001-web-server/spec.md#3-]
### FR-0100 团队内多人可访问的 web server 工作台
[source: project/specs/v0.8-001-web-server/spec.md#fr-0100--web-server-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |
系统必须提供一个可运行的 web server 入口，使团队内多人可以通过浏览器访问 louke 的协作界面。该界面至少整合模型绑定、wiki、设计文档三类能力，而不是分别依赖离散脚本或本地文件浏览。
---
### FR-0200 拖拽式模型绑定
[source: project/specs/v0.8-001-web-server/spec.md#fr-0200-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |
系统必须提供拖拽式交互来建立、调整和查看模型绑定关系。用户应能在界面中通过可视化操作完成绑定，不要求记忆 CLI 参数，也不应退化为仅文本输入框加保存按钮。
---
### FR-0300 同时支持 Agent 绑定与抽象角色绑定
[source: project/specs/v0.8-001-web-server/spec.md#fr-0300--agent-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |
模型绑定至少支持两类目标：
1. 具体 Agent 绑定，例如 `Sage`、`Archer`、`Lex`
2. 抽象角色绑定，例如 A/B/S 级或其他 louke 内部约定的角色层
界面必须能明确展示两类绑定，并让用户分辨默认绑定与覆盖绑定。v0.8 的抽象角色命名空间固定为 `A` / `B` / `S` 三类；Agent 到角色的归属关系以 `interfaces.md` 中定义的 roster 为权威来源，不得在实现阶段临时从 README 表格或自然语言描述中猜测。
---
### FR-0400 wiki 浏览与编辑
[source: project/specs/v0.8-001-web-server/spec.md#fr-0400-wiki-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |
系统必须支持在 web 页面中浏览 wiki 列表、打开 wiki 页面、编辑内容并保存。该能力面向团队协作，不得限制为只读模式，也不得要求用户跳回本地编辑器才能完成正常更新。
---
### FR-0500 设计文档浏览与编辑
[source: project/specs/v0.8-001-web-server/spec.md#fr-0500-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |
系统必须支持在 web 页面中浏览和编辑至少以下设计文档：
1. `spec.md`
2. `acceptance.md`
3. `test-plan.md`
编辑后必须保留文档的 Markdown 结构，包括标题层级、锚点、FR / NFR 编号和已有的结构化内容，不得因 web 编辑过程破坏 louke 工作流依赖的文本约定。
注：`M-ARCH` 已确定文档编辑采用“双栏源码编辑 + 实时预览”模式：左栏编辑 Markdown 源文，右栏渲染预览并承载 `inline-discussion` 与 FR / NFR 卡片视图。v0.8 不采用 Typora 式单窗即时渲染编辑，以避免 Markdown / 协议保真与锚点稳定性风险。
---
### FR-0600 `inline-discussion` 渲染与编辑支持
[source: project/specs/v0.8-001-web-server/spec.md#fr-0600-inline-discussion-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |
针对设计文档，系统必须支持 `inline-discussion` 的阅读、发起、回复和状态理解。至少要保证用户能在接近原文上下文的位置看到讨论线程，而不是被迫切到独立聊天面板中失去锚点关联。具体编辑器交互和存储同步方式由 `M-ARCH` 决定，但对既有协议的兼容是硬约束。
---
### FR-0700 FR / NFR 卡片式渲染
[source: project/specs/v0.8-001-web-server/spec.md#fr-0700-fr---nfr-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |
在 spec 视图中，系统必须为每个 FR / NFR 提供卡片式渲染。卡片至少要展示编号、标题、正文摘要以及元信息表中的关键状态（例如 Valid / Testable / Decided），并允许用户跳转回原始 Markdown 上下文。
---
### FR-0800 协作可见性与变更提示
[source: project/specs/v0.8-001-web-server/spec.md#fr-0800-]
| Valid | Testable                 | Decided |
| ----- | ------------------------ | ------- |
| ✅     | ⚠️ 具体实现待架构阶段定义 | ✅       |
由于本期面向团队内多人，系统必须让用户感知文档和绑定关系的最新状态，避免多人协作时发生静默覆盖。至少需要有“当前内容是否已更新”以及“谁最后修改了内容”的可见性。冲突处理、锁定策略和实时机制留到 `M-ARCH` 细化。
---
### FR-0900 常用 Markdown 格式渲染支持
[source: project/specs/v0.8-001-web-server/spec.md#fr-0900--markdown-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |
设计文档与 wiki 在 web 页面中渲染时，必须支持常用 Markdown 格式，至少包括代码块、表格、列表等常见结构。页面不得把这些结构降级成难以辨认的纯文本，也不得因渲染层引入与原始 Markdown 明显不一致的语义偏差。
渲染与编辑的组织方式在 v0.8 中已锁定为**双栏源码编辑 + 实时预览**：
1. 左栏显示 Markdown 源文本并支持编辑
2. 右栏实时渲染代码块、表格、列表等常用 Markdown 结构
3. 预览区与源码区的内容对应关系必须清晰，用户可以在不整页跳转的前提下完成编辑与核对
---
### FR-1000 `inline-discussion` 的正文/讨论聚焦与折叠
[source: project/specs/v0.8-001-web-server/spec.md#fr-1000-inline-discussion--]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |
对于设计文档中的 `inline-discussion`，系统必须支持以下展示控制：
1. 默认以较淡样式显示讨论，避免正文阅读被过度打断
2. 提供“看正文 / 看讨论”的切换能力，并在切换后实现正文与讨论的视觉主次对换
3. 允许用户折叠讨论线程，以便在需要时专注正文
具体视觉样式、按钮位置、交互动画和持久化策略由 `M-ARCH` 决定，但“弱化默认显示 + 视图切换 + 折叠”是本期明确需求。
---
## 4. 非功能需求
[source: project/specs/v0.8-001-web-server/spec.md#4-]
### NFR-0100 Markdown 兼容与工作流保真
[source: project/specs/v0.8-001-web-server/spec.md#nfr-0100-markdown-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |
web 界面读写后的文件必须继续兼容 louke 现有工作流。也就是说，CLI、agent prompt、`inline-discussion` 工具和后续 `M-TESTPLAN` / `M-ARCH` / `M-LOCK` 流程读取这些文档时，不需要为了 web 版本另写一套解析规则。
---
### NFR-0200 交互稳定，不得依赖导致明显闪烁的粗暴刷新
[source: project/specs/v0.8-001-web-server/spec.md#nfr-0200-]
| Valid | Testable           | Decided |
| ----- | ------------------ | ------- |
| ✅     | ⚠️ 需在架构阶段量化 | ✅       |
web 界面的内容刷新和状态更新必须保持稳定顺滑，不得通过高频整页刷新或会造成明显闪烁的粗暴轮询来实现核心交互，尤其是文档编辑和模型绑定视图。
---
### NFR-0300 面向团队内使用的可部署性
[source: project/specs/v0.8-001-web-server/spec.md#nfr-0300-]
| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |
本期产物必须是可实际运行和访问的 web server，而不是仅有静态原型图或脱离仓库文件系统的演示页面。具体部署拓扑由 `M-ARCH` 决定，但交付目标必须是团队内可以使用的真实服务。
---
## 5. 澄清记录
[source: project/specs/v0.8-001-web-server/spec.md#5-]
| 议题                   | 结论                                                                          |
| ---------------------- | ----------------------------------------------------------------------------- |
| 模型绑定范围           | 同时支持“按 Agent 绑定”和“按抽象角色绑定”                                     |
| 设计文档范围           | 至少覆盖 `spec.md`、`acceptance.md`、`test-plan.md`                           |
| wiki 能力              | 需要支持编辑，不是只读                                                        |
| 目标用户               | 团队内多人                                                                    |
| 文档体验               | 必须支持 `inline-discussion`，且 FR / NFR 需要卡片式渲染                      |
| Markdown 渲染          | 需要支持代码块、表格、列表等常用 Markdown 格式                                |
| discussion 可视化      | 默认弱化显示讨论，并支持正文/讨论切换与折叠                                   |
| Markdown 编辑/预览模式 | 已由 Archer 在 `M-ARCH` 定案：采用双栏源码编辑 + 实时预览，不做 Typora 式单窗 |
| 技术选型               | 不在 M-SPEC 决定，交由 Archer 在 `M-ARCH` 产出                                |

## v0.9-001-web-ui-refinement

# v0.9-001 - Web UI 精修与协作增强 - Spec
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#v09-001---web-ui----spec]
- **Spec ID**: v0.9-001-web-ui-refinement
- **创建日期**: 2026-07-09
- **状态**: 草稿
- **关联**:
- **上游**: `v0.8-001-web-server`（web 协作界面 v0.8 基线）
- **相关协议**: `v0.7-003-inline-discussion-protocol`
> **Responsibility split**: 本文只描述需求本身与已决定的边界。技术实现
> 细节（同步滚动算法、冲突检测策略、autosave debounce 机制）由 Archer 在
> `M-ARCH` 决定。可观察、可断言的通过条件统一写在 `acceptance.md`。
---
## 0. 范围与边界
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#0-]
### 0.1 本 spec 收纳
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#01--spec-]
| 主题 | FR 范围 |
| --- | --- |
| sidebar Logout 按钮尺寸缩小 | FR-0100 |
| 编辑器与实时预览同步滚动 | FR-0200 |
| Focus Content / Focus Discussion 改为 toggle 按钮 | FR-0300 |
| 5 秒自动存盘 | FR-0400 |
| 写入冲突检测（防止覆盖他人修改） | FR-0500 |
| inline-discussion 缩进线宽度缩减一半 + 颜色变浅 10% | FR-0600 |
| FR/NFR/Story 交叉引用可点击跳转 + 后退返回 | FR-0700 |
| valid/testable/decided 状态可点击 toggle 并写回文件 | FR-0800 |
### 0.2 本 spec 不收纳
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#02--spec-]
- 新增页面或全新功能模块（本期全部是对 v0.8 已有页面的精修）
- 后端架构重构、数据库引入、WebSocket 实时推送
- 权限模型变更
- 移动端适配（仅保证桌面端可用）
### 0.3 关键设计原则
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#03-]
- 所有改动必须在**不破坏 v0.8 已有功能**的前提下进行。
- FR-0500（冲突检测）优先保证"不静默覆盖"，而非实时协作锁。
- FR-0700（交叉引用跳转）依赖现有 Markdown 渲染管线，不引入额外
解析器；跳转目标通过已有的 FR anchor 机制定位。
- FR-0800（状态 toggle）写回文件时必须保持 inline-discussion 格式
不被破坏。
---
## 1. 用户故事
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#1-]
### US-1（FR-0100）
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#us-1fr-0100]
作为协作者，我希望 sidebar 的 Logout 按钮不要那么大，因为它占据
了过多视觉空间，与导航项的视觉层级不匹配。
### US-2（FR-0200）
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#us-2fr-0200]
作为文档编辑者，我希望编辑器滚动时预览区同步滚动（反之亦然），这样
我在长文档中编辑某段时能立即看到对应的渲染结果，不需要手动寻找位置。
### US-3（FR-0300）
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#us-3fr-0300]
作为文档审阅者，我希望 Focus Content 和 Focus Discussion 是 toggle
按钮（点一次激活、再点一次取消），而不是各自独占一个按钮位，节省
工具栏空间。
### US-4（FR-0400）
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#us-4fr-0400]
作为文档编辑者，我希望编辑后 5 秒自动存盘，这样即使我忘记手动保存
也不会丢失工作；同时存盘不应干扰我的编辑焦点。
### US-5（FR-0500）
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#us-5fr-0500]
作为多人协作者，我希望在保存时检测到文件已被他人修改时，系统阻止
我的写入并提示冲突，而不是静默覆盖他人的工作。
### US-6（FR-0600）
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#us-6fr-0600]
作为文档读者，我希望 inline-discussion 的缩进竖线更细更淡，因为
当前样式在嵌套较深时视觉噪声过大，干扰正文阅读。
### US-7（FR-0700）
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#us-7fr-0700]
作为 spec 读者，我希望在预览中看到 `FR-0400` / `001-FR-210` 这类
交叉引用时可以点击跳转到对应 FR 的定义位置，并且能后退返回原处。
### US-8（FR-0800）
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#us-8fr-0800]
作为 spec 维护者，我希望在讨论卡片上直接点击 valid / testable /
decided 标记来切换状态，系统自动将变更写回 Markdown 文件，而不
需要手动编辑源码。
---
## 2. 功能需求
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#2-]
### FR-0100: sidebar Logout 按钮尺寸缩小
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#fr-0100-sidebar-logout-]
**现状**: Logout 按钮使用标准按钮样式（height 46px, padding 0 18px），
与主导航链接的视觉层级不匹配，过大。
**要求**:
- Logout 改为 ghost / text 按钮风格，视觉重量低于主导航链接。
- 高度不超过导航链接行高；字号与 sidebar 次要文字一致。
- 保留可点击区域（min height >= 32px 以满足触控友好）。
- hover 时有轻微背景反馈，但不使用实心填充按钮样式。
### FR-0200: 编辑器与实时预览同步滚动
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#fr-0200-]
**现状**: 编辑器和预览区各自独立滚动，长文档中编辑某段后预览不跟随。
**要求**:
- 编辑器滚动时，预览区按比例同步滚动到对应位置。
- 预览区滚动时，编辑器反向同步。
- 同步方向以用户最后一次主动滚动的 pane 为准（避免循环抖动）。
- 当用户在某一 pane 内手动滚动时，另一个 pane 跟随；当程序化
触发滚动时（如 autosave 后恢复光标），不触发反向同步。
- 同步精度为"段落级"即可（不需要像素级精确），通过行/段映射实现。
### FR-0300: Focus Content / Focus Discussion toggle 按钮
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#fr-0300-focus-content---focus-discussion-toggle-]
**现状**: Focus Content 和 Focus Discussion 是两个独立按钮，各占
一个位。
**要求**:
- 合并为一个 toggle 按钮组（或单一 toggle），点击切换 Content /
Discussion 聚焦模式。
- 再次点击当前激活的焦点模式时，恢复双栏均衡视图（取消聚焦）。
- 三态：均衡（默认）-> Content 聚焦 -> Discussion 聚焦 -> 均衡。
或两态 toggle：Content <-> Discussion，默认均衡。
- Collapse Discussion 按钮可保留为独立按钮，不纳入 toggle。
### FR-0400: 5 秒自动存盘
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#fr-0400-5-]
**现状**: 仅手动 Save 按钮触发保存。
**要求**:
- 编辑器内容变更后，5 秒内无进一步输入则自动触发保存。
- 保存与手动 Save 走同一 API 端点，写入同一文件。
- 自动保存时在 UI 上显示轻量指示（如 "已自动保存" 文案或 icon），
不弹模态、不抢焦点。
- 自动保存失败时（如冲突，见 FR-0500）显示错误提示。
- 用户手动 Save 时取消未触发的 autosave timer（避免重复保存）。
### FR-0500: 写入冲突检测
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#fr-0500-]
**现状**: 保存时直接覆盖文件，无冲突检测。
**要求**:
- 保存请求携带客户端已知的文件版本标识（如 last-known mtime 或
content hash）。
- 服务端在写入前校验：如果磁盘上文件的当前版本标识与客户端提交
的不一致，拒绝写入并返回 409 Conflict。
- 客户端收到 409 后：
- 不覆盖本地编辑（保留用户输入）。
- 显示冲突提示，提供"查看远端版本"和"强制覆盖"两个选项。
- "查看远端版本"加载远端内容到预览区（只读），用户决定合并或放弃。
- autosave（FR-0400）遇到 409 时同样静默转为冲突提示状态，不重试。
### FR-0600: inline-discussion 缩进线样式调整
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#fr-0600-inline-discussion-]
**现状**: 嵌套讨论的缩进竖线宽度为当前值，颜色为当前值。
**要求**:
- 缩进竖线 border-left-width 缩减为当前值的 50%（如 2px -> 1px）。
- 颜色透明度在当前基础上再降低 10%（如 rgba(0,0,0,0.12) ->
rgba(0,0,0,0.108)，或等效的 lighten/darken）。
- 嵌套 4 层以上仍可辨认层级，但视觉噪声显著降低。
### FR-0700: FR/NFR/Story 交叉引用可点击跳转
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#fr-0700-fr-nfr-story-]
**现状**: 预览区中 `FR-0400`、`001-FR-210` 等引用为纯文本。
**要求**:
- 渲染时检测文本中的 FR/NFR 交叉引用模式：
- `FR-XXXX`（4 位数字）
- `NFR-XXXX`
- `<prefix>-FR-XXXX`（如 `001-FR-210`，prefix 为数字或字母段）
- `Story` / `US-N` 引用（可选，优先级低于 FR/NFR）
- 将匹配到的引用渲染为可点击链接。
- 点击后跳转到：
- 同一 spec 内的 FR 定义 -> 滚动到对应 `<a id="fr-XXXX">` anchor。
- 跨 spec 引用（`001-FR-210` 指向 spec `001` 的 FR-0210）-> 加载
对应 spec 文档并定位 anchor。
- 跳转后提供"后退"机制（浏览器 history.back 或自定义 back 按钮），
使用户能返回跳转前的位置。
- 链接样式与正文区分但不喧宾夺主（如虚线下划线或浅色链接色）。
### FR-0800: valid/testable/decided 状态可点击 toggle
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#fr-0800-valid-testable-decided--toggle]
**现状**: 讨论卡片上的 valid / testable / decided 标记为静态显示。
**要求**:
- 每个标记渲染为可点击 toggle 按钮（点击切换 on/off）。
- 点击后通过 API 将变更写回 Markdown 源文件中的
inline-discussion 标记行。
- 写回时保持 inline-discussion 格式完整性（不破坏 `>>>` / `<<<`
/ speaker tag 等结构）。
- 写回成功后 UI 立即更新标记状态；失败时回滚 UI 并提示错误。
- 与 FR-0500 冲突检测联动：若文件已被他人修改，status toggle
写入同样返回 409，按 FR-0500 流程处理。
---
## 3. 非功能需求
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#3-]
### NFR-0100: 性能
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#nfr-0100-]
- 同步滚动（FR-0200）不得引入可感知的卡顿（< 16ms per frame）。
- autosave（FR-0400）不得阻塞 UI 线程。
- 交叉引用渲染（FR-0700）不得使首屏渲染延迟超过 200ms（对 5000 字文档）。
### NFR-0200: 向后兼容
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#nfr-0200-]
- 所有改动不得破坏 v0.8 已有的编辑、保存、讨论、模型绑定功能。
- 文件格式不变（仍是 Markdown + inline-discussion 语法）。
### NFR-0300: 可测试性
[source: project/specs/v0.9-001-web-ui-refinement/spec.md#nfr-0300-]
- FR-0500 冲突检测、FR-0800 状态写回可通过 API 测试（不依赖浏览器）。
- FR-0200 同步滚动可通过 DOM 断言测试（检查 scroll position 联动）。
