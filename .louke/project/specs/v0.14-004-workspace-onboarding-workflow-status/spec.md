# Workspace Setup Wizard、Guide 与 Workflow Status 驾驶舱 — 需求规格

- **规格 ID**：`v0.14-004-workspace-onboarding-workflow-status`
- **关联 Story**：`STR-1405`
- **创建日期**：2026-07-23
- **状态**：草稿
- **有效 FR 数量**：16（上限 30）

> **职责边界**：本文是 v0.14 四个 Spec 的产品集成合同，规定空白 workspace 的 Setup Wizard、登录落点、Start Story、Workbench 驾驶舱和 Guide。它不重写 `001` 的需求工作流、`002` 的 M-DESIGN 或 `003` 的实现到发布状态机；重叠处按下表锁定唯一用户可见行为。

## Release 合同继承与冲突裁决

| 重叠主题 | v0.14 唯一真实行为 | 继承与替代边界 |
| :--- | :--- | :--- |
| 启动与 Setup | Web 服务可建立后，完全空白或 Setup 失效的 workspace 进入 Workbench 中的连续 Setup Wizard；Web 服务本体无法建立仍在终端失败 | 继承 `001 FR-0100/0200` 的 readiness、preview/confirm、Manifest 和零未授权副作用语义；本文替代独立启动诊断页或平面 Setup 页面作为完成路径，并增加首用户、init/clone 和 Wizard 顺序 |
| 开始产品工作 | Setup 完成后，用户主动作是“开始 Story”；没有 active release 时，系统同时 preview/confirm 承载该 Story 的 release identity | 继承 `001 FR-0300/0400/0500` 的单活跃 release、零副作用 Preview、Foundation 和 Story 初始化；本文替代“创建首个 Release”这一用户心智和孤立 `/projects/new` 页面 |
| 需求、设计与实现 | Runtime 是 M-STORY 至 M-MILESTONE 的唯一状态、责任方、合法转移和 evidence authority | `001 FR-0600/2100`、`002` 全部有效需求及 `003` 除下述 Maestro 重叠外的全部有效需求保持权威；本文只提供统一读模型和导航，不创建第二状态机 |
| 当前工作与发布结果 | Project/驾驶舱在同一对象上下文展示 Ready、Current Work、attention、Released 和历史，不另建平行对象身份 | 继承 `001` 的 Project/run identity 与 `003 FR-2100—FR-2400` 的 release/publish/milestone 事实；本文替代分散的 Project current、Run 和发布结果作为默认用户落点 |
| Guide 与 Agent Chat | Guide 是始终可见的解释/导航层；专业 Agent Chat 仍绑定具体 Runtime task | 本文替代 `003 FR-3000` 中“Maestro 若保留可作 advisory”的新运行行为；`001 FR-0700` 等 Scribe/Sage/专业 Agent 对话继续有效，Guide 不参与 author/review 或 dispatch |
| 路由与版本 | 用户使用稳定 Workbench/Project/Story 入口；版本化协议可作为兼容边界，但不得产生版本专属页面或重复产品事实 | 现有 `/projects`、`/projects/new`、Project/Run 深链必须解析到同一 Workbench 对象上下文；通用 Create Release 能力不得复制为 `v15_release.py`、`v16_release.py` 等页面 |

若四个 Spec 的文字在上述重叠主题上仍可解释为两个用户结果，以本表和本文对应 FR 为准；未列入的阶段政策继续由原 owning Spec 负责。任何实现不得双写两个 Setup、Project、workflow 或 Guide/Maestro 权威状态来“兼容”冲突。

## 功能需求

<a id="fr-0001"></a>
### FR-0001 空白 Workspace 的稳定产品入口与状态解析

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.1、§2.4；BS-03、BS-07；继承 `001 FR-0100/0600`

用户在完全空白或已有 workspace 执行 `lk serve` 时，只要 Web 服务本体能够建立，就必须能到达同一个 Workbench shell。未认证用户先完成首用户建立或登录；认证后，系统必须按以下优先顺序解析主视图：Setup 缺失/失效进入 Setup Wizard；存在需要 Human attention 的 active work 进入其 Current Work；存在其它 active work 进入 Current Work；无 active work 且最近 Milestone 已发布进入 Released；Setup 有效且无工作进入 Ready/Empty。

历史发布与新 active work 同时存在时以 active work 为主，历史发布可从同一对象上下文访问。登录不得自动切换到独立聊天页，也不得仅依据账号新旧、cookie 或 Guide 对话推断落点。Web 服务无法建立的硬前置失败继续遵循 `001 FR-0100`，不得伪装成 Wizard 内可修复状态。

---

<a id="fr-0101"></a>
### FR-0101 连续 Setup Wizard 与进度边界

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.1；BS-01、BS-02；Human 明确要求 Setup 为 Wizard

Setup 必须作为一个连续 Wizard，按“本地身份 → Repository → 运行依赖 → Review → Apply/Complete”的任务顺序呈现。Wizard 必须显示当前步骤、已完成步骤、剩余步骤和阻塞项；用户在 Confirm 前可返回修改选择，已验证且未受上游修改影响的结果不得要求重复填写。

Wizard 每一步只收集当前仍缺失、冲突或需要授权的信息，能够从 workspace、Git/provider 身份及既有配置稳定推导的值直接展示其 provenance。用户离开 Wizard 不得开放 Story/release 动作，也不得把局部完成误报为 Setup 完成。

---

<a id="fr-0201"></a>
### FR-0201 首用户建立、登录与 Setup 连续性

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.1 Step 1；BS-01

没有本地用户时，Wizard 必须先让用户建立唯一首个 Workspace Owner/Human。创建成功后系统必须持久化该身份并进入登录；登录成功后返回同一 workspace 的 Repository 步骤，而不是把“首用户已存在”视为 Setup 完成或重新开始 Wizard。

首用户已存在时不得再次展示可创建第二个首用户的成功路径。身份建立失败、重复提交或服务重启必须产生稳定结果，且 credential 不得回显到页面、日志、Manifest 或 Guide。

---

<a id="fr-0301"></a>
### FR-0301 Repository 来源选择与明确副作用

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.1 Steps 2—3；BS-02；D-01

Repository 步骤必须检查当前 workspace 的 Git 事实。当前 workspace 已是 Git repository 时，系统读取可验证的 repository、remote 和默认分支候选；不是 Git repository 时，Wizard 必须让 Human 明确选择“在当前 workspace 初始化 repository”或“克隆已有 repository”，并在执行前展示目标、会改变的本地内容和适用 remote/provider 影响。

选择 init/clone 只形成当前 Setup revision 的拟议操作，Review/Confirm 前不得执行。目录非空、目标冲突、clone 来源不可访问、权限不足或操作结果无法确认时，系统必须停在 Repository/Apply 上显示证据和 remediation，不得覆盖现有文件、猜测目标或把文件操作成功等同于 binding 已确认。

---

<a id="fr-0401"></a>
### FR-0401 Workspace/Repository Binding、候选与 Provenance

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.1 Step 3；BS-02；D-01；继承 `001 FR-0200`

Wizard 必须为 workspace/repository identity、owner/provider namespace、declared remote 和权威默认分支展示推导值及 provenance。零个候选、多个候选、身份字段不一致或无法验证时保持 waiting Human；系统不得按名称相似、列表顺序或 Guide 建议静默选择。

Human 的选择必须绑定当前 Setup revision。只有 init/clone 的实际结果、repository identity、remote/provider 身份和所选 binding 可共同验证时，该步骤才完成；后续 Story/release/Foundation 只消费这个已确认 binding。

---

<a id="fr-0501"></a>
### FR-0501 运行依赖与 Workspace 能力检查

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.1 Step 4；继承 `001 FR-0100/0200`

Runtime 步骤必须在同一 Wizard 中检查 Louke store/catalog、OpenCode 可执行性、provider 认证、至少一个可用模型，以及 Backlog/release-project namespace 或创建能力。每项必须显示 READY、需要用户操作或阻塞的非秘密诊断；已就绪项不得以 placeholder 或固定默认值冒充真实检查。

用户完成认证或外部修复后可以 Recheck 当前事实。未通过的必要项必须阻止 Review/Confirm 或 Setup Complete；检查不得展示 credential/token 值，也不得把无法连接、超时或结果不确定解释为 READY。

---

<a id="fr-0601"></a>
### FR-0601 Setup Review、Preview Revision 与 Human Confirm

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.1 Step 5；BS-02；继承 `001 FR-0200`

必要候选可确定后，Review 步骤必须一次展示拟采用的 workspace Manifest、各字段 provenance、readiness 结论，以及 Confirm 后将执行的 init/clone、binding 或 workspace 级外部配置操作及其影响。Preview 本身不得执行所列操作，也不得创建具体 Story/release 的 Project、run、branch、GitHub Project 或 Spec 目录。

Confirm 必须由已认证 Human 明确触发并绑定当前 preview revision、actor 和选择。任一影响 preview 的事实或选择变化都使旧 preview stale；重复、并发或 stale Confirm 不得执行两次或套用旧选择。

---

<a id="fr-0701"></a>
### FR-0701 Setup Apply、Reconcile 与 Manifest 完成条件

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.1 Steps 6—7；BS-01、BS-02；继承 `001 FR-0200/2100`

Confirm 后，系统只执行 Preview 中由 Human 授权的 workspace 级操作，并逐项显示 pending、applying、completed、failed、conflict 或结果不确定。每项操作必须在重试前查询实际结果；身份精确匹配的既有结果复用，未发生才可安全重试，冲突或不确定保持 attention。

只有 repository binding、运行依赖、namespace/capability 和全部必要操作均已验证时，系统才可写入持久化 Setup Manifest 并显示 Setup Complete。完成结果必须进入 Workbench Ready/Empty；任何局部成功不得开放 Start Story，也不得以回滚无关用户文件来制造“干净”结果。

---

<a id="fr-0801"></a>
### FR-0801 Setup 与 Story 启动的中断恢复

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.2；D-02；继承 `001 FR-2100`、`003 NFR-0300`

浏览器关闭、服务/设备重启或网络中断后，系统必须从持久化的 Setup revision、Human 决定、operation identity/result 和当前外部事实恢复最后一个可证明步骤。Confirm 前恢复有效候选与选择并重查易变事实；Confirm 后先 reconcile 已授权操作，不重复 init、clone、remote 或外部资源副作用。

Setup 已完成且 Manifest 有效时不得重播 onboarding。Manifest 或必要 binding 后来失效时，用户进入可恢复的 Setup attention 状态，同时保留已有 Story/release 身份。Story 启动中断时恢复同一 delivery request；不得重复 Confirm、创建第二 Story/release container 或把未知结果标为成功。

---

<a id="fr-0901"></a>
### FR-0901 Start Story 与交付容器 Preview

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.1 Steps 7—9；BS-03、BS-04；D-07；继承 `001 FR-0300/0400/0500`

Setup 有效且无 active work 时，Project/驾驶舱的主动作必须是“开始 Story”，让 Human 输入一个要解决的问题或交付设想。Story 是用户表达交付意图的单位，并对应一个 release 中的 `story.md`；当前合同不引入 feature set 的集合管理心智。

没有 active release 时，系统必须同时提出承载该 Story 的 release identity/目标版本，并在 Confirm 前展示 workspace identity、原始 Story 输入、external/canonical version、拟创建 branch、preview revision/request digest 和零 release 副作用。Confirm 后的单活跃 release 检查、权威 `main`/Foundation、资源创建与 Story 初始化严格继承 `001 FR-0300/0400/0500`。已有 active release 时，主视图必须回到 Current Work 且不得提供创建第二个主容器的成功路径；用户经 stale 或兼容入口提交的新请求按 `001 FR-0300` 幂等保存到 Backlog并显示阻塞结果。

---

<a id="fr-1001"></a>
### FR-1001 Workflow Status 驾驶舱与对象连续性

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.3；BS-05；继承 `001 FR-0600`、`003 FR-2400`

Project activity 必须将驾驶舱作为当前工作的默认主视图，并始终延续同一 workspace、Story、release Project 和 WorkflowRun identity。Ready/Empty 显示 workspace readiness 与 Start Story；Current Work 显示 active work；Released 显示最近完成的 Milestone/release、发布时间/结果、可访问 artifacts、历史和开始下一个 Story 的入口。

若 Released 之后已有新 active work，Current Work 必须成为主视图，已发布结果保留为历史上下文。驾驶舱不得创建与 Project/Run 页面平行的对象、状态副本或需要用户离开当前对象重新寻找功能的孤立页面。

---

<a id="fr-1101"></a>
### FR-1101 阶段进度、责任方、Evidence 与合法动作

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.3；BS-05、BS-06；继承 `001 FR-0600`、`002`/`003` 各阶段合同

驾驶舱必须从 Runtime read model 显示当前 release/project、阶段序列与当前阶段、canonical 状态、当前责任方、适用 artifact/revision、最近状态变化/evidence 摘要、最近错误和 required action。阶段进度只表示 Runtime 已完成、当前、待处理和 attention 事实，不得显示客户端或 Guide 估算的百分比。

`waiting_human`、`blocked`、`conflict`、`interrupted`、`needs_attention`、`closing` 等影响用户任务的状态必须突出原因、后果与恢复位置。每个状态至多呈现一个 Runtime 指定的主要下一动作；修复后 Recheck、Human 决定、继续到 artifact 等动作必须作用于当前 revision/attempt。没有合法用户动作时明确显示正在等待的责任方，普通导航不得伪装成流程推进。

---

<a id="fr-1201"></a>
### FR-1201 Workbench 导航挂载与稳定深链

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.3—§2.4；D-04；当前 Workbench toolbar/sidebar 与 `/projects`、`/runs` 公开入口

Workbench 必须提供 Project activity，与 Docs、End User Docs、Wiki、Runs、Settings 等现有 activities 共享同一 shell。状态 resolver 选择 Project/Setup 主视图后，用户仍可切换其它 activity，并能从其公开入口返回同一 Project 当前上下文。

现有 `/projects`、`/projects/new`、Project detail、Story、Gate 和 Run 深链可以作为兼容入口，但必须打开或导航到同一 Workbench 对象与状态，不得维护独立的 release 页面状态或版本专属页面。返回、刷新和书签必须保留可解析的 workspace/project/run/artifact 身份；不存在或无权访问的目标显示可定位结果而非静默落到错误 Project。

---

<a id="fr-1301"></a>
### FR-1301 Sidebar 的 Guide 固定挂载与用户空间控制

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.4 Guide 挂载合同；BS-07；D-04、D-05

Workbench sidebar 必须垂直分为两个持续可见区域：上方默认约 `2/3` 显示当前 activity 的既有导航/功能，下方默认约 `1/3` 显示 Guide 对话。Guide 在 Project、Docs、End User Docs、Wiki、Runs、Settings 及 Setup 中保持同一挂载位置；切换 activity 时上方内容切换，Guide 更新上下文但不取代主内容。

用户必须能折叠 Guide、调整分隔位置并恢复默认比例；Workbench 记住该用户的选择。小窗口或无障碍缩放时必须优先保证主功能可操作，且折叠 Guide 不改变 Runtime 状态或阻止合法流程动作。

---

<a id="fr-1401"></a>
### FR-1401 Guide 的上下文说明、对话与非干扰行为

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.4；BS-06、BS-07；D-03—D-05

Guide 必须基于当前 workspace、activity、所选 Story/release/artifact 和 Runtime read model，先简洁说明“用户在哪里、这里能做什么、当前状态意味着什么、应到哪里执行下一步”，再允许用户追问。它可以解释 evidence、选项影响并导航到正式功能，但正式输入、编辑、Confirm、Human decision 和 Runtime action 必须在 owning surface 完成。

首次 Setup、首次 Story、首次查看 Released，以及新进入 Human attention 状态时，Guide 可以更新并突出对应说明；它不得自动切换 activity、夺取键盘焦点、滚动或遮蔽主功能、清除未发送输入，也不得要求用户先回复才能继续。状态未变化时不得在每次登录重复追加欢迎或提醒消息。

Guide 会话必须按 workspace 与任务上下文区分；切换对象/activity 时可保留历史供回看，但必须标明上下文变化，不得把旧解释呈现为当前事实。Guide 内容和 last-seen 只能决定说明是否突出，不能决定 workflow 状态或登录落点。

---

<a id="fr-1501"></a>
### FR-1501 Guide、专业 Agent Chat 与 Maestro 退役边界

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.1、§3.1；BS-06；D-03；Human 决定退休 Maestro；冲突裁决 `003 FR-3000`

Guide 不得作为可选 Agent 出现在 Agent picker，不得 author/review artifact、选择或 dispatch 专业 Agent、提交 Human decision、调用阶段转移、伪造 evidence 或改变 Runtime 状态。责任方和合法 action 完全由 Runtime 决定，Guide 只解释并导航。

Scribe、Sage、Archer、Devon 等专业 Agent Chat 必须继续绑定 Runtime 指定的 task/session、artifact 和 write/review scope，并与 Guide 对话明确区分。新运行和新用户旅程不得依赖、展示或 dispatch Maestro；历史 Maestro session/evidence 仅按 `003 NFR-0600` 只读展示或迁移，不得形成 Guide 与 Maestro 双重 advisory authority。

---

## 非功能需求

<a id="nfr-0001"></a>
### NFR-0001 持久化恢复、幂等与并发安全

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.2；继承 `001 FR-2100/NFR-0100`、`003 NFR-0300`

Setup revision、Human 选择、Manifest、operation identity/result、onboarding/last-seen、Workbench 当前对象和适用 Runtime state 必须持久化。刷新、重启、重复/并发 Confirm 与重试不得重复外部副作用、创建平行对象或接受 stale revision；无法确认结果时 fail closed 并保留可恢复 evidence。

---

<a id="nfr-0101"></a>
### NFR-0101 Secret、权限与本地副作用保护

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §3.1、风险；继承 `001 NFR-0200`、`002/003 NFR-0200`

Credential、token、cookie、provider secret 和完整认证材料不得进入 Setup Manifest、Guide/Agent 输入、event、日志、错误详情、文档或提交；产品只展示非秘密 identity、计数、redacted diagnosis 和 digest。init/clone、remote/binding 及外部 namespace 操作必须受当前 Human 明确授权和 workspace 范围约束，不得覆盖或删除无法归属的用户内容。

---

<a id="nfr-0201"></a>
### NFR-0201 单一状态权威与可验证新鲜度

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story BS-05、BS-06；D-03；四 Spec Runtime authority 合同

Setup、驾驶舱、Guide、兼容深链和专业 Agent Chat 必须消费同一 Runtime/Manifest 事实及可识别 revision。客户端缓存、聊天摘要或历史页面不得覆盖较新的 canonical 状态；读取 stale、对象不匹配或 revision 冲突时必须刷新并显示当前可继续位置，不能双写兼容状态。

---

<a id="nfr-0301"></a>
### NFR-0301 可访问、响应式且非侵入的 Workbench

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story D-05；Guide 挂载合同

Wizard 的步骤、错误、完成状态和操作必须可通过键盘及可访问名称理解；状态不得只依赖颜色。Sidebar 在受支持窗口尺寸和文本缩放下必须保持主功能、Guide 折叠/恢复及合法下一动作可达。Guide 更新应通过非侵入的状态提示表达，不得无请求抢焦点或造成用户输入丢失。

---

<a id="nfr-0401"></a>
### NFR-0401 四 Spec 升级与历史兼容

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Human 要求四 Spec 统筹；Story D-06；继承 `002 NFR-0600`、`003 NFR-0600`

升级必须将现有 Setup、Project、Run、release request、artifact 和 milestone identity 映射到本文 Workbench 视图，不得要求有效 workspace 重新 Setup 或把历史工作复制成新对象。旧路由和版本化协议在兼容期可读取/转发到 canonical 行为，但新写入只产生一份权威状态；无法安全映射的历史 Maestro/run 状态必须显式只读或标记需要迁移，不得静默解释为当前 Guide/Runtime 状态。

---

<a id="nfr-0501"></a>
### NFR-0501 可操作诊断与用户可理解性

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §2.1—§2.4、风险；继承 `002 NFR-0500`

Wizard 与驾驶舱的失败结果必须指出失败对象、当前已知事实、对用户任务的影响、责任方和可执行恢复位置；不得只显示内部异常、run ID 或“失败/重试”。普通成功路径保持渐进披露：新用户无需先理解 Runtime stage、release container 或 Agent 编排即可开始 Story，但需要诊断时可展开 evidence 和 artifact 入口。

---

## 澄清记录

- 2026-07-23：Human 决定 Setup 必须是 Wizard；主路径先完整描述完全空白 workspace，再单独描述中断恢复。
- 2026-07-23：Human 决定空白 workspace 完成 Setup 后以“首个 Story”作为用户目标，不使用“首个 Release”或 feature set；Story 是比 feature 更大的交付意图单位，release 是承载 Story 的交付容器。
- 2026-07-23：Story 登录矩阵中遗留的 `Create Next Release` 与其后 Human 决定 D-07 冲突；本文统一为“开始下一个 Story”，需要新 delivery container 时由同一预览一并提出 release identity。
- 2026-07-23：Human 决定 Guide 固定挂载于每个 Workbench activity 的 sidebar 下方约 `1/3`，上方约 `2/3` 保留现有功能。
- 2026-07-23：Human 决定不使用 Maestro 并准备将其退休；流程控制完全由 Runtime 决定，Guide 只解释与导航。
- 2026-07-23：四个 v0.14 Spec 共同组成一个 release；本文已明确重叠主题的 owning contract 和替代边界，不保留双重真实行为。
