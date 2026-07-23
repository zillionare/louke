# STR-1405: 首次 Workspace Onboarding、Release 引导与 Workflow Status 驾驶舱

---

| Story ID | 创建时间                  | 分流建议         |
| :------- | :------------------------ | :--------------- |
| STR-1405 | 2026-07-23T20:13:19+09:00 | Go（Agent 建议） |

---

## 0. 原始输入

> 现在我们开始新的 story, 版本号依然是0.14. sotry是：首次 Workspace Onboarding、Release 引导与 Workflow Status 驾驶舱

## 1. 用户意图

- **主要用户**：在本地 Git workspace 中使用 `lk serve` 创建或恢复 release 的 Workspace Owner/Human。
- **当前处境**：首次访问虽可创建首用户，但 workspace 未必已确认关联唯一 repository；登录后用户缺少按当前工作状态决定的入口，工作流中断，需要人工接续。
- **目标结果**：用户从首次访问建立身份、确认 workspace repository，到开始首个 Story 或恢复现有工作，始终知道当前状态、阻塞原因和唯一可继续动作；不需要猜测内部路径、run ID 或应由谁处理问题。
- **成功信号**：完全空白的 workspace 在登录后能一次完成 Setup，并从“开始首个 Story”进入无副作用的交付预览；有 active、已确认、待裁定、阻塞或已发布的交付工作时，用户在 Workbench 的 project view/驾驶舱看到对应上下文、状态和可执行的继续/恢复入口。

## 2. 核心操作路径

### 2.1 完全空白 Workspace 的 Happy Path

- **起点上下文**：用户在一个没有 Louke 配置、没有本地用户、也可能不是 Git repository 的空白目录执行 `lk serve` 并首次打开产品。
- **入口/触发**：系统识别 workspace 尚未完成 Setup，在 Workbench shell 中进入 Workspace Setup；完成前不开放 Story 创建和交付流程。

1. **建立本地身份**：用户创建首个 Workspace Owner/Human 并登录。系统持久化首用户，同时明确显示 workspace Setup 尚未完成。
2. **选择 repository 来源**：系统检查当前目录。若不是 Git repository，用户明确选择在当前 workspace 初始化 repository，或克隆已有 repository；若已经是 Git repository，系统直接读取可验证事实，不要求重复输入。
3. **确认 workspace/repository binding**：系统展示推导出的 workspace、repository、owner/provider namespace、remote/main 等候选值及 provenance。用户只处理缺失、冲突或涉及创建/修改副作用的项目；系统不得静默选择多个候选之一。
4. **完成运行依赖检查**：同一 Setup 继续检查 Louke store/catalog、OpenCode 可执行性、provider 认证、可用模型，以及 Backlog/release-project namespace 或创建能力。已就绪项直接完成；缺失项提供就地操作或明确 remediation，并在修复后 Recheck。
5. **查看 Setup Preview**：必要输入可确定后，系统一次展示拟采用的 workspace manifest、各值来源，以及仍需执行的 init/clone、binding 或外部配置操作及其影响。Preview 本身不执行所列副作用。
6. **确认并执行 Setup**：用户确认当前 preview revision；Runtime 执行获准操作，对每项结果 reconcile，并重新验证 repository binding、运行依赖和外部身份。失败、冲突或结果不确定时停留在 Setup，不伪报完成。
7. **完成 Setup**：全部必要检查通过后，Runtime 持久化 Setup Manifest。用户进入 Workbench 的 Project/驾驶舱 Ready/Empty 状态，看到已绑定的 workspace/repository，以及“开始首个 Story”主动作；Guide 在 sidebar 下方说明 workspace 已就绪和该功能的位置。
8. **开始首个 Story**：用户输入想解决的问题或功能设想。若当前没有 active release，系统同时提出承载该 Story 的 release identity/目标版本；用户查看无副作用的预览，确认的是 Story 输入及其交付容器，而不是一个抽象 workflow 状态。
9. **进入工作**：确认后 Workbench 展示 Foundation/请求状态。成功时进入该 Story 的上下文；阻塞或冲突时显示证据、remediation、Recheck 与返回入口。

- **完成结果**：用户从完全空白目录得到具有本地 Owner、可信 repository binding、可用运行依赖和持久化 Setup Manifest 的 workspace，并开始第一个可交付 story。
- **继续/返回**：无 active work 时回到 Ready/Empty 和“开始 Story”；有 active work 时回到 Current Work。

### 2.2 Setup 中断与恢复

- **恢复入口**：用户关闭浏览器、服务退出或设备重启后，再次执行 `lk serve` 并登录。系统读取持久化 Setup revision、已确认决定、operation 状态和当前外部事实，返回同一个 Workspace Setup，而不是从首用户创建重新开始。

1. **Preview 确认前中断**：恢复已保存的候选、provenance 和用户选择，并重新检查可能变化的 Git、认证、模型及 namespace 事实；有效选择继续保留，变化或冲突项重新要求确认。
2. **确认后执行中断**：Runtime 先 reconcile 每项 init、clone、binding 或外部配置操作，区分已成功、未开始、失败和结果不确定；已存在且身份匹配的结果直接复用，不重复创建 repository、remote 或外部资源。
3. **需要 Human 介入**：权限失效、候选冲突、外部结果不确定或不可逆操作无法安全重试时，Setup 显示证据、影响和唯一合法恢复动作，等待 Human 修复、裁定或 Recheck。
4. **Setup 完成后中断**：若 Manifest 仍有效，登录直接进入 Ready/Empty、Current Work 或 Released 驾驶舱，不重新播放 onboarding；若 binding 或必要依赖后来失效，进入可恢复的 Setup/attention 状态，并保留已有 Story/release 上下文。
5. **Story 启动阶段中断**：Setup 不重复执行；Workbench 恢复同一个 delivery request。`ready` 继续到 Story，`blocked/conflict` 显示 remediation 和 Recheck，非终态继续读取 Runtime 状态而不重复确认。

- **恢复结果**：用户从最后一个可证明的持久化状态继续；刷新或重启不重复外部副作用，也不创建重复 Story 或 release container。

### 2.3 Workflow Status 驾驶舱

- **定位**：驾驶舱是 Workbench 中处理当前工作的主视图，不是聊天摘要或仅供排障的日志页。用户登录后有现有 release/request/workflow 时直接看到它；无当前工作时，驾驶舱以空状态呈现 workspace readiness、“开始 Story”主动作和 Guide 引导。Released 状态是 M-MILESTONE（v0.14-003 FR-2400）结果的只读展示，不重定义 milestone 行为。
- **首屏信息层级**：先让用户一眼确认“我正在哪个 workspace/release 上、目前处于什么阶段、谁正在处理、我现在是否需要行动”；随后展示能解释该结论的进度、状态和最近事件。
- **必须可见的信息**：workspace/repository identity、当前 release/project、当前阶段和阶段序列、工作状态、当前责任方、当前 artifact/revision（如适用）、最近一次状态变化及其证据摘要、Runtime 指定的 required action。
- **进度呈现**：以 Runtime 已定义的 workflow 阶段形成可理解的 stepper/timeline，标识已完成、当前、待处理、等待 Human、blocked、conflict 或 interrupted；不展示由前端估算或聊天推断的虚假百分比。
- **状态与动作呈现**：`waiting_human`、`blocked`、`conflict` 和 `interrupted` 必须在首屏突出其原因、影响和恢复入口。每个状态只呈现 Runtime 允许的下一动作；例如 Human 决定、修复后 Recheck、继续到已就绪 artifact、回到 Projects/Backlog。没有合法动作时明确说明正在等待的责任方，而不是提供可误导用户的通用继续按钮。
- **历史与诊断**：用户可展开近期 workflow 事件、错误/冲突证据和相关 artifact 入口，以理解状态变化；驾驶舱不要求用户读取原始日志才能找到下一步。
- **Guide 的关系**：Guide 在驾驶舱上下文中解释当前卡片和导航至相应功能；驾驶舱的状态、进度和动作仍直接由 Runtime read model 提供，Guide 不充当数据源或控制面。

### 2.4 登录落点与 Guide 挂载

登录成功后，系统先解析 workspace setup、active release/request、Runtime 状态和最近完成的 Milestone，再决定任务落点。用户不会仅因“首次/返回登录”身份被送入一个脱离任务上下文的通用聊天页。

| 登录时的产品状态                                                  | 登录后的主落点                               | 首屏结果                                                                                                                    | Guide 行为                                                                                                        |
| :---------------------------------------------------------------- | :------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------- |
| **初次登录，Setup 未完成**                                        | Workbench shell 内的 Workspace Setup         | 显示首用户建立后的 repository init/clone、binding 验证和完成条件；release 功能保持不可用                                    | Guide 固定显示在 sidebar 下部，解释为什么需要 binding、当前步骤及功能位置；不代替用户选择 repository 或确认副作用 |
| **Setup 已完成，但从未创建 Story 且无 active request/workflow** | Workbench 的 Project/驾驶舱 Ready/Empty 状态 | 显示 workspace 已就绪、“开始首个 Story”主动作和创建路径                                                                   | Guide 解释 Story 的作用并导航到正式创建功能；若无 active release，再说明系统将同时建立其交付容器                |
| **正在活跃开发**                                                  | Workbench 的 Project/驾驶舱 Current Work     | 打开 active release/project，显示阶段 stepper、当前责任方、状态、最近变化和 Runtime required action                         | Guide 固定可见但不抢占焦点；`waiting_human`、`blocked`、`conflict` 或 `interrupted` 时将对应解释置顶              |
| **Milestone 已完成且产品已发布，无后续 active release/request**   | Workbench 的 Project/驾驶舱 Released 状态    | 显示刚完成的 Milestone/release、发布时间/结果与可访问的 artifacts，并提供 Create Next Release、查看历史或返回产品文档的入口 | Guide 显示“已发布/接下来可以做什么”，但用户可直接使用上方正式功能而不必先完成聊天                                 |
| **已发布，但已有后续 active release/request**                     | Workbench 驾驶舱的 Current Work              | 以当前 active release 为主，已发布 Milestone 作为历史上下文可访问                                                           | 按活跃开发规则处理，不因历史发布状态跳回庆祝或聊天页                                                              |

> **Lex:** Story §2.4 登录落点矩阵第 4 行（"Milestone 已完成且产品已发布..."）仍列出 "Create Next Release" 入口；Human 在 §4 D-07 已明确 Setup 完成后用户目标是开始 Story 而非创建下一个 Release，且 spec.md 澄清记录 + FR-0901/FR-1001 都把 Released 后的主入口改为"开始下一个 Story"，必要时由同一 Preview 提出 release identity。请 Sage 修订 Story 表格第四行主落点为"开始下一个 Story"，并与驾驶舱 Released 视图的入口保持一致。


#### Guide 的产品挂载合同

- Workbench sidebar 垂直分为两个持续可见区域：上方约 `2/3` 保留当前 icon/activity 的既有导航与功能（Project、Docs、Wiki、Runs 等），下方约 `1/3` 固定为 Guide 对话窗口。
- Guide 在每一个 icon/activity 下都显示，不属于 Chat agent picker 中的某个 Agent，也不成为取代 Setup、驾驶舱、文档或 Wiki 的独立首页。用户切换 icon 时，上方功能立即切换，Guide 留在原位并取得新的可见上下文。
- Guide 先显示短小的上下文说明：“你在哪里、这里能做什么、当前状态意味着什么、应到哪里执行下一步”，再承载用户追问；正式数据、编辑、确认和 Runtime action 始终在上方功能区或主内容区完成。
- 默认比例为 `2/3 : 1/3`；为避免小窗口、长文档树或无障碍缩放时可用区域过小，用户可以折叠 Guide 或调整分隔位置，Workbench 记住个人选择，并提供恢复默认比例的方式。
- Guide 更新上下文时不得自动夺取键盘焦点、滚动上方列表或清除尚未发送的输入；新的重要状态只在 Guide 标题/摘要中显著提示。
- Guide 的会话按 workspace 与当前任务上下文隔离；切换 release/project 或 icon 后，可以保留历史供回看，但必须明确标示上下文切换，不得把上一任务的解释伪装成当前事实。

#### 自动进入聊天的条件

- 登录后始终进入 Workbench shell 中由状态 resolver 选择的正式功能，Guide 已在 sidebar 下方可见；产品**不再自动跳转或切换到聊天页面**。
- 首次 Setup、首次 Story、首次看到发布完成，以及新进入 `waiting_human`、`blocked`、`conflict` 或 `interrupted` 时，Guide 自动更新并突出对应说明，但不抢焦点、不遮蔽上方功能，也不要求用户先回复。
- `active/running` 且无需 Human 行动时，Guide 显示简短的当前阶段与责任方，不主动发起对话；已解释且状态未变化时不重复追加欢迎或提醒消息。
- Guide 的自动内容依据持久化 onboarding/last-seen 状态和 Runtime 状态变化，而非浏览器临时状态或 Guide 自己对聊天内容的判断。

### 2.5 行为种子

### BS-01 首用户与 Workspace Setup 分离

- EARS: `WHEN 首用户创建并登录后 workspace 尚无已确认的 repository binding, THE 系统 SHALL 将用户引导至可恢复的 Workspace Setup，且 SHALL NOT 允许开始 Story 或创建其交付容器`
- 来源: 主路径 / 用户讨论
- 说明: 身份建立不应误报为已具备开始产品工作的条件。

### BS-02 Repository binding 的可见确认

- EARS: `IF workspace repository identity 缺失、存在多个候选、身份冲突、权限不足或无法验证, THE 系统 SHALL 显示候选、provenance 和 remediation；WHEN workspace 不是 Git repository, THE 系统 SHALL 提供由 Human 明确选择的初始化本地 repository 或克隆已有 repository 路径，并在操作后等待 Human 确认或修复后 recheck`
- 来源: 主路径 / Human 决定
- 说明: 让非 Git workspace 可完成 setup，同时防止 release 在缺少可信 remote/repository identity 时失败或误作用于错误仓库。

### BS-03 状态驱动的登录落点

- EARS: `WHEN Human 登录 Workbench, THE 系统 SHALL 根据持久化的 setup、release request、active workflow 与 required action 决定落点；IF 无 active work 且 setup 已完成, THE 系统 SHALL 提供“开始 Story”引导`
- 来源: 主路径 / 用户讨论
- 说明: 用户无需猜测 `/projects/new`、run 或恢复入口。

### BS-04 Release 引导与可恢复反馈

- EARS: `WHEN Human 在无 active release 的 Workbench 开始 Story, THE 系统 SHALL 将该 Story 输入与拟承载它的 release identity 一并 preview/confirm，并持续显示请求和 Foundation 状态；WHEN 状态为 ready, THE 系统 SHALL 继续至 Story；IF 状态为 blocked 或 conflict, THE 系统 SHALL 显示 remediation、recheck 与 Projects/Backlog 返回入口`
- 来源: 主路径 / 既有 release 合同
- 说明: 用户以 Story 为目标开始工作；release 是承载该 Story 的交付容器，其创建结果仍需完整可见。

### BS-05 Workflow Status 驾驶舱

- EARS: `WHILE workspace 存在 active、interrupted、waiting_human、blocked 或 conflict 的 workflow, THE 系统 SHALL 将 Workflow Status 驾驶舱作为 Workbench 当前工作的主视图，显示 workspace/repository identity、当前 release/project、阶段 stepper、状态、当前责任方、artifact revision、最近状态变化/证据与 Runtime 指定的唯一下一动作`
- 来源: 主路径 / 用户讨论
- 说明: `waiting_human`、`blocked`、`conflict` 和 `interrupted` 需突出原因及恢复入口；进度应来自持久化 Runtime read model，而不是前端猜测或虚假百分比。

### BS-06 Guide 的解释与导航边界

- EARS: `WHEN Guide 为 Human 解释当前 workflow, THE 系统 SHALL 仅依据 Runtime 公开的状态、evidence 与 required action 提供正在发生什么、功能位置和下一步的说明与导航；IF action 要求 Human 决定或指定专业 Agent, THE 系统 SHALL 保持该责任归属，不得由 Guide 自行裁定、分派或推进`
- 来源: 主路径 / Human 决定 / 既有 Runtime authority 合同
- 说明: Guide 降低理解和发现功能的成本，同时不越过 Human 主权和 Runtime 流程权威。Guide 对状态的描述必须可与 Runtime read model 字段核对，不得断言 read model 中不存在的状态、责任方或下一动作。

### BS-07 常驻 Guide 与 Workbench 布局

- EARS: `WHEN Human 登录并按 BS-03 完成落点后, WHILE Human 使用任一 icon/activity, THE 系统 SHALL 在 sidebar 上方约 2/3 保留该功能并在下方约 1/3 持续显示 Guide；THE 系统 SHALL NOT 自动切换到独立聊天页`
- 来源: Human 追问 / 当前 Workbench 产品入口
- 说明: 初次 Setup、首次开始 Story、首次查看发布完成以及新出现的 Human attention 状态更新 Guide 说明；普通 active/running 和未变化状态不重复打扰或抢占焦点。

## 3. 范围、约束与例外

### 3.1 必须保持的产品约束

- 首用户创建成功不等于 Workspace Setup 完成；未确认 repository binding 时不得开始 Story 或创建其交付容器。
- 对非 Git workspace，初始化本地 repository 或克隆已有 repository 必须由 Human 明确选择和确认；完成后仍须通过 repository binding 验证，不能因文件操作成功即视为 setup 完成。
- 登录落点、workflow 状态、责任归属和合法下一动作必须来自持久化事实及 Runtime 公开合同；聊天内容、前端状态或 Agent 自述不得推进流程。
- 新 release 继续复用 v0.14 已签的 preview/confirm、Foundation、单活跃 release、Backlog 和 Story 初始化合同；本 Story 不绕过这些检查或外部副作用恢复规则。
- 本 Story 扩展 v0.14-001 FR-0200（Workspace Setup），新增 repository provisioning（init/clone）与 binding 验证；FR-0200 “Setup 不创建或复用具体 release 的 Project、WorkflowRun、release GitHub Project、release branch 或 Spec 目录” 的约束继续有效。
- Create Release 是跨 Louke 版本持续存在的 Workbench 产品能力：用户入口保持稳定，当前版本、可用字段和合法动作来自 project/Runtime contract；后续版本不得通过复制 `v15_release.py`、`v16_release.py` 等版本专属页面来演进。
- 本 Story 的用户侧引导使用 Guide，不使用 Maestro；Maestro 的退役准备不得改变 Runtime 的状态、责任归属或合法 action。
- Guide 可以解释和导航，但不能代替 Human 做产品、权限、不可逆或流程 gate 决定，也不能自行选择、分派或 dispatch 专业 Agent。

### 3.2 非常规要求

- 无。

### 3.3 Out-of-Scope

- 不重写 Scribe、Sage、Lex、Archer、Devon 或 Shield 的专业 author/review/implementation 职责。
- 不定义新的 workflow 阶段、API schema、组件树、前端框架或 Agent runtime 状态机。
- 不把聊天记录本身作为 workflow 的权威状态或审计来源。

## 4. 重要推导与证据

### D-01 Workspace repository binding 是 release 前置条件

- **结论**：repository identity 应在 Workspace Setup 中确认并持久化；缺失时可由 Human 明确选择 init/clone 后再验证 binding，Story 启动及其 delivery container 只消费已确认 binding，而非在用户开始工作后才失败。
- **依据**：当前 `/tmp/louke` 空 workspace 可创建首用户但缺少 Git remote；现有 v0.14 FR-0300 至 FR-0400 要求 release preview/confirm 依赖 workspace identity、declared remote 和权威 `main`。
- **影响**：将身份建立、repository provisioning/binding 和 release 副作用分层，避免用户在 `/projects/new` 才发现基础条件不足。

### D-02 Landing 应由状态而非账号新旧决定

- **结论**：是否显示 onboarding/release 引导应由 setup 完成度、active release/request 和 required action 决定，而非账号创建时间或浏览器 cookie。
- **依据**：现有登录默认进入 `/`，而 workspace 可能在服务重启、换浏览器或中断后仍有待恢复的持久化工作；v0.14 FR-0600 要求刷新和重启恢复同一上下文。
- **影响**：首次用户可获得引导，返回用户不会被重复 onboarding 打扰，待处理 Human action 也不会被隐藏。

### D-03 Guide 是解释层而非流程 authority

- **结论**：Guide 是 Workbench 的用户侧解释与导航层，读取 Runtime read model 说明正在发生什么、用户应到哪里使用功能以及可继续的下一步；责任方和合法动作由 Runtime 返回。
- **依据**：Human 明确决定不用 Maestro、改用 Guide，且流程控制完全由 Runtime 决定；既有 v0.14 Story/Spec 将 Runtime 定义为当前步骤、转移、write ownership 和状态的唯一 authority，并限制 Agent 代替 Human 推进。
- **影响**：用户获得统一的说明和功能发现入口，同时避免自然语言推测导致错误分派、伪造完成或越权裁定，并为 Maestro 退役移除用户流程依赖。

### D-04 Guide 应依附真实任务视图，而非成为登录首页

- **结论**：登录 resolver 先选择 Workbench 中的 Setup 或驾驶舱状态；Guide 固定在每个 activity 的 sidebar 下方约 `1/3`，以当前功能和 Runtime attention 状态更新说明，普通登录不跳独立聊天页。
- **依据**：当前 `/` 已进入 Workbench，且各 activity 已复用 toolbar/sidebar/main shell；Human 决定在 sidebar 上方 `2/3` 保留 icon 对应功能、下方 `1/3` 常驻 Guide。Guide 要解释“在做什么、到哪里找功能”，其价值依赖当前任务上下文；若聊天取代 Setup/驾驶舱，反而会隐藏 Runtime 的权威状态与合法 action。
- **影响**：三类用户有稳定、可预期的登录落点；切换 Project、Docs、Wiki 等功能时不失去 Guide，也不因错误或过度精细的登录跳转而离开可用的 Workbench shell。

### D-05 常驻辅助面板应帮助上手而不争夺主任务

- **结论**：`2/3 : 1/3` 是 Guide 的默认信息分配，但应允许折叠/调节并记住用户选择；状态更新不得自动聚焦或重复发送说明。
- **依据**：常见 IDE 和管理工作台将导航、资源树保留为主区域，将帮助/助手作为可调整的辅助区域；固定不可调整的三分之一在小窗口、无障碍缩放或长目录中会显著损害主要功能。
- **影响**：新用户持续看到指导，熟练用户可减少占用；Guide 仍然随时可恢复，不会演变成强制聊天流程。

### D-06 Release 创建是与 Louke 产品版本无关的长期能力

- **结论**：Create Release 从 v0.13 及任何后续版本都属于 Workspace/Project 的长期产品能力，不存在“v0.14 Release 页面”这一用户概念。修复前 `v14_release.py` 的页面命名和默认版本硬编码属于实现边界错误；当前已收敛为通用 `release.py` 页面与稳定 `/api/releases/...` 用户功能入口。
- **依据**：用户执行的任务始终是“为当前 workspace 创建下一次 release”，而不是“使用某个 Louke 版本的 release 页面”。修复前的文件把通用任务与 `/api/v14/...` 协议路径、默认 `v0.14.0` 和页面文件身份混在一起；即使底层合同需要版本化，也不应传播为版本专属用户功能。
- **影响**：Workbench 后续整合继续使用通用 Create Release 能力，由 project/Runtime 提供当前 release context；底层已签协议如需保留版本兼容，应封装在功能边界之后。不得为 v0.13、v0.15、v0.16 等复制不同 Create Release 页面。

### D-07 Setup 完成后以 Story 而非 Release 作为用户目标

- **结论**：空白 workspace 完成 Setup 后的主动作是“开始首个 Story”。若没有 active release，Runtime 同时建立或提出承载该 Story 的 release identity；不把“创建首个 Release”表述成用户目标或 workflow 状态。Story 是用户表达交付意图的单位，比 feature 更大；一个 Story 对应一个 release 中的 `story.md`（M-STORY 产物）。
- **依据**：Human 明确指出“首个 release”容易与 workflow 状态混淆；当前 M-STORY 入口接收一句设想并形成一个 Story，而不是需要集合级增删、排序和范围管理的 feature set。
- **影响**：新用户先表达要解决的问题，再理解目标版本和交付容器；本 Story 不引入 feature set 产品模型。Release Preview/Confirm 仍负责安全地展示和确认该 Story 的交付 identity。

## 5. 开放产品决定

- 无。Human 已决定：非 Git workspace 的 Setup 提供由 Human 明确确认的 init/clone repository 路径。

## 6. 必要性、风险与分流建议

- **既有能力**：已有首用户 API/登录、setup readiness、`/projects/new` release preview/confirm/status、Foundation read model、Workbench、Runtime workflow authority，以及现有 Maestro agent。当前 release 页面已开始提供 preview/confirm/status，但缺少统一登录落点、repository setup 闭环、Guide 和全局状态驾驶舱。
- **冲突**：无；本 Story 补齐 v0.14 已有“`lk serve` → Setup → `/projects/new` → Story”的用户路径，并保持其已签 release 约束。
- **重要风险**：repository init/clone、binding 若模糊选择目标或把未验证身份视为完成，可能作用于错误仓库或产生意外本地副作用；Guide 若被赋予流程推进、分派或裁定权会破坏 Runtime/Human authority 边界；常驻 Guide 若不可折叠、频繁抢焦点或重复消息会压缩主要导航并形成干扰；状态驾驶舱若读取非持久化前端数据会在刷新或重启后误导用户。
- **分流建议**：Go — 用户已实际遇到首用户、登录、release 创建和浏览器兼容链路断裂；本 Story 以既有 Runtime/release 合同为基础补齐可发现、可恢复的入口、repository provisioning/binding 和状态闭环。本 Story 范围较大，M-SPEC 展开后可能超过 30 条 FR 硬门禁（v0.14-001 §0.1 约束 7）；若超限，建议按 “onboarding/登录落点” 与 “驾驶舱/Guide” 两个子主题拆分，而不是按 workflow 阶段拆分。

## 7. 可追溯信息

- **Story ID**：`STR-1405`
- **创建时间**：`2026-07-23T20:13:19+09:00`
- **关联 Spec/Issue**：待建立
- **Sage peer review**：`Pending`（Scribe 不得填写通过结果）
