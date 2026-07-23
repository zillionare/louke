# Workspace Setup Wizard、Guide 与 Workflow Status 驾驶舱 — Acceptance Criteria

- **Spec ID**：`v0.14-004-workspace-onboarding-workflow-status`
- **关联 Story**：`STR-1405`
- **创建日期**：2026-07-23
- **修订说明**：2026-07-24 通过 `T-001` 修订；标题统一为全局 `AC-FRXXXX-YY` / `AC-NFRXXXX-YY`，使 `tools/check_ac_traceability.py` 可机器解析。

> 本文是 `spec.md` 中全部有效 FR/NFR 的可观察验收合同。每项 AC 通过公开产品入口、持久化 artifact/state、Runtime read model 或可核对的外部结果断言；未要求精确文案、组件实现或内部数据结构。
>
> 编号约定：每个 FR/NFR section 内 `AC-1`/`AC-2` 局部序号保持可读，但相应标题始终使用全局 ID `AC-FRXXXX-YY` / `AC-NFRXXXX-YY`（4 位需求号 + 2 位顺序），与现有 `tools/check_ac_traceability.py` 的 `AC-FR\d{4}-\d{2}` / `AC-NFR\d{4}-\d{2}` 解析正则一一对应。section 锚点保留为 `ac-fr-XXXX` / `ac-nfr-XXXX` 以兼容现有 Wiki/issue 引用。

<a id="ac-fr-0001"></a>

## FR-0001 空白 Workspace 的稳定产品入口与状态解析

### AC-FR0001-01
- Web 服务能够建立时，从完全空白目录或既有 workspace 执行 `lk serve` 均可到达同一 Workbench shell；未认证用户先看到首用户建立或登录入口，认证后才进入对应任务视图。
- 对 Setup 缺失/失效、attention active work、其它 active work、仅有最近 Released、有效 Setup 且无工作的 workspace，登录后的主视图依次可观察为 Setup、Current Work、Current Work、Released、Ready/Empty；新 active work 与历史 Released 并存时以 Current Work 为主且仍可访问历史结果。

### AC-FR0001-02
- 登录、刷新或再次打开产品不会自动切换到独立聊天页；改变 cookie 或 Guide 对话而不改变持久化产品状态，不会改变 resolver 选择的任务落点。
- Web 服务本体无法建立时，用户在启动出口看到对应硬前置失败，产品不报告已进入可修复的 Setup Wizard。

<a id="ac-fr-0101"></a>

## FR-0101 连续 Setup Wizard 与进度边界

### AC-FR0101-01
- 空白 workspace 的 Setup 在同一连续旅程中按“本地身份 → Repository → 运行依赖 → Review → Apply/Complete”推进，并始终可辨认当前步骤、已完成步骤、剩余步骤和阻塞项。
- Confirm 前返回修改上游选择后，受影响的下游结论会重新验证；未受影响且仍有效的已验证结果保持完成，不要求重复填写。

### AC-FR0101-02
- 每一步只要求用户处理无法稳定推导、存在冲突或需要授权的值；可推导值与其 provenance 同时可见。
- 用户在 Setup 局部完成后离开再返回，Story/release 动作仍不可用，且页面不显示 Setup Complete。

<a id="ac-fr-0201"></a>

## FR-0201 首用户建立、登录与 Setup 连续性

### AC-FR0201-01
- 无本地用户时，用户能创建唯一首个 Workspace Owner/Human；创建成功后该身份在刷新或服务重启后仍存在，登录成功直接继续同一 workspace 的 Repository 步骤。
- 首用户存在后，首用户创建入口不再提供创建第二个首用户的成功路径；重复提交返回与已存在身份一致的稳定结果。

### AC-FR0201-02
- 身份建立失败时不会将 Setup 标为完成，并提供可定位的失败结果。
- 页面、Setup Manifest、Guide 及用户可访问的诊断或日志出口均不出现提交的 credential 原文。

<a id="ac-fr-0301"></a>

## FR-0301 Repository 来源选择与明确副作用

### AC-FR0301-01
- 当前目录已是 Git repository 时，Repository 步骤显示经验证的 repository、remote 与默认分支候选；不是 Git repository 时，用户必须明确选择在当前 workspace init 或 clone 已有 repository，并在执行前看到目标、本地内容影响和 remote/provider 影响。
- 形成 init/clone 选择并浏览 Review 前，文件系统和外部 provider 中不存在该选择导致的新 repository、clone、remote 或外部资源副作用。

### AC-FR0301-02
- 对非空目录冲突、不可访问 clone 来源、权限不足或结果不确定，Wizard 停留在 Repository/Apply，显示失败对象、证据与恢复位置；现有文件未被覆盖，Setup 与 binding 未被误报完成。

<a id="ac-fr-0401"></a>

## FR-0401 Workspace/Repository Binding、候选与 Provenance

### AC-FR0401-01
- Binding 步骤同时显示 workspace/repository identity、owner/provider namespace、declared remote、权威默认分支及每项 provenance。
- 零候选、多候选、身份不一致或无法验证时，状态保持 waiting Human，并要求用户在明确候选间裁定；候选顺序、名称相似或 Guide 建议不会自动形成 binding。

### AC-FR0401-02
- Human 选择可核对为绑定当前 Setup revision；当 revision 变化时旧选择不会被静默套用。
- 只有 init/clone 实际结果、repository identity、remote/provider 身份和所选 binding 可共同验证后，该步骤才显示完成，后续 Story/release 使用的 identity 与此 binding 一致。

<a id="ac-fr-0501"></a>

## FR-0501 运行依赖与 Workspace 能力检查

### AC-FR0501-01
- Runtime 步骤分别呈现 Louke store/catalog、OpenCode、provider 认证、至少一个可用模型、Backlog/release-project namespace 或创建能力的真实检查结果；每项可辨认为 READY、需要用户操作或阻塞，并提供非秘密诊断。
- 任一必要项未通过或结果不确定时，用户不能完成 Review/Confirm 或 Setup Complete，且该项不会显示 READY。

### AC-FR0501-02
- 用户修复认证或外部依赖后执行 Recheck，页面显示基于当前事实的新结果；已就绪项保持可辨认，不以 placeholder 冒充检查结果。
- 检查结果和诊断不显示 credential 或 token 原文。

<a id="ac-fr-0601"></a>

## FR-0601 Setup Review、Preview Revision 与 Human Confirm

### AC-FR0601-01
- Review 一次显示拟采用的 workspace Manifest、字段 provenance、readiness 结论、Confirm 后拟执行的 init/clone、binding 或 workspace 级外部配置操作及其影响。
- 只生成或查看 Preview 不产生所列操作，也不创建具体 Story/release 的 Project、run、branch、外部 Project 或 Spec 目录。

### AC-FR0601-02
- 只有已认证 Human 能对当前 preview revision 明确 Confirm；确认记录可核对 actor、revision 与所选操作。
- 影响 Preview 的事实或选择变化后，旧 Confirm 被识别为 stale；重复或并发 Confirm 最多产生一次获准副作用，不会套用旧选择。

<a id="ac-fr-0701"></a>

## FR-0701 Setup Apply、Reconcile 与 Manifest 完成条件

### AC-FR0701-01
- Confirm 后仅执行当前 Preview 列出的授权操作；每项可观察为 pending、applying、completed、failed、conflict 或结果不确定，并与实际 repository/provider 结果一致。
- 对重复 Apply 或恢复，身份精确匹配的既有结果被复用；冲突或无法确认的结果保持 attention，不重复创建或伪报成功。

### AC-FR0701-02
- 仅当 binding、运行依赖、namespace/capability 和全部必要操作均验证通过时，系统写入持久化 Setup Manifest、显示 Setup Complete 并进入 Ready/Empty，用户随后可使用 Start Story。
- 任一必要项仅局部成功时，不显示 Setup Complete、不开放 Start Story，也不删除或回滚不属于获准操作的用户文件。

<a id="ac-fr-0801"></a>

## FR-0801 Setup 与 Story 启动的中断恢复

### AC-FR0801-01
- 在 Confirm 前关闭浏览器或重启服务后，用户登录可回到同一 Setup revision，看到仍有效的选择，并获得对易变事实的最新复查结果，而不是从首用户创建重新开始。
- 在 Confirm 后中断并恢复时，产品先显示已完成、未开始、失败或不确定的实际操作结果；已完成的 init、clone、remote 或外部资源不被重复创建。

### AC-FR0801-02
- 有效 Setup Manifest 存在时重新登录不重播 onboarding；Manifest/binding 失效时进入 Setup attention，同时原 Story/release identity 仍可访问。
- Story 启动中断后恢复同一 delivery request；刷新、重启或重试不会重复 Confirm、创建第二 Story/release container，未知结果不会显示 ready 或成功。

<a id="ac-fr-0901"></a>

## FR-0901 Start Story 与交付容器 Preview

### AC-FR0901-01
- Setup 有效且无 active work 时，用户从 Project/驾驶舱 Ready/Empty 的“开始 Story”入口输入一个问题或交付设想，并在不离开当前 workspace 上下文的情况下进入 Preview。
- 无 active release 时，Preview 同时显示原始 Story 输入、workspace identity、external/canonical version、拟议 release identity/目标版本、拟创建 branch、preview revision/request digest，且 Confirm 前无 release 副作用。

### AC-FR0901-02
- Human Confirm 后，成功请求进入同一 Story/release 的 Foundation/请求状态，并可继续到 Story artifact；blocked/conflict 请求显示证据、remediation、Recheck 与返回 Ready/Projects/Backlog 的入口。
- 已有 active release 时，主视图保持 Current Work 且没有创建第二主容器的成功路径；通过 stale 或兼容入口提交的新请求只产生可见 Backlog 记录和阻塞结果，不产生第二 active release。

<a id="ac-fr-1001"></a>

## FR-1001 Workflow Status 驾驶舱与对象连续性

### AC-FR1001-01
- Project activity 的默认主视图按产品状态显示 Ready/Empty、Current Work 或 Released；三种视图中的 workspace、Story、release Project 与 WorkflowRun identity 可相互核对为同一对象链。
- Ready/Empty 提供 readiness 与 Start Story；Current Work 提供 active work；Released 提供最近 Milestone/release、发布时间或结果、artifacts、历史及开始下一个 Story 的入口。

### AC-FR1001-02
- Released 后出现新 active work 时，重新进入 Project 显示 Current Work，原发布结果仍可从当前对象上下文访问。
- 从驾驶舱进入 Project/Run/artifact 后返回，不会出现平行对象或要求用户重新寻找当前工作。

<a id="ac-fr-1101"></a>

## FR-1101 阶段进度、责任方、Evidence 与合法动作

### AC-FR1101-01
- 对任一 active workflow，驾驶舱显示可与 Runtime read model 核对的 release/project、阶段序列与当前阶段、canonical 状态、当前责任方、适用 artifact/revision、最近状态变化/evidence 摘要、最近错误和 required action。
- 进度只区分已完成、当前、待处理及 attention 状态，不显示 Runtime 未提供的百分比或 Guide 推断的完成度。

### AC-FR1101-02
- 当状态为 `waiting_human`、`blocked`、`conflict`、`interrupted`、`needs_attention` 或 `closing` 时，首屏可见原因、任务后果与恢复位置，并且至多有一个与 Runtime required action 一致的主要流程动作。
- 执行 Recheck、Human 决定或继续 artifact 时使用当前 revision/attempt；没有合法用户动作时显示正在等待的责任方，普通导航不会改变流程状态。

<a id="ac-fr-1201"></a>

## FR-1201 Workbench 导航挂载与稳定深链

### AC-FR1201-01
- Workbench 同一 shell 中可访问 Project、Docs、End User Docs、Wiki、Runs、Settings；从状态 resolver 选择的 Setup/Project 切换到其它 activity 后，可通过公开入口返回同一 Project 当前上下文。
- 直接访问 `/projects`、`/projects/new`、Project detail、Story、Gate 或 Run 兼容深链，打开或导航到与 Workbench 相同的对象身份和 canonical 状态，不出现版本专属或独立 release 状态副本。

### AC-FR1201-02
- 对有效目标，返回、刷新和书签重开后仍解析到相同 workspace/project/run/artifact；不存在或无权访问的目标显示可定位的 not-found/forbidden 结果，不静默落入其它 Project。

<a id="ac-fr-1301"></a>

## FR-1301 Sidebar 的 Guide 固定挂载与用户空间控制

### AC-FR1301-01
- 默认 Workbench sidebar 上方约 `2/3` 显示当前 activity 的导航/功能，下方约 `1/3` 显示 Guide；在 Project、Docs、End User Docs、Wiki、Runs、Settings 和 Setup 间切换时，Guide 保持同一挂载位置，主内容随 activity 切换。
- Guide 不取代或遮蔽上方正式功能，切换 activity 后其说明可辨认为新上下文。

### AC-FR1301-02
- 用户可以折叠 Guide、调整分隔位置并恢复默认比例；刷新或重新登录后恢复该用户最后保存的选择。
- 在受支持的小窗口和文本缩放条件下，主功能、Guide 恢复入口和当前合法下一动作仍可操作；折叠或调整 Guide 不改变 Runtime 状态。

<a id="ac-fr-1401"></a>

## FR-1401 Guide 的上下文说明、对话与非干扰行为

### AC-FR1401-01
- Guide 的初始说明可与当前 workspace、activity、Story/release/artifact 和 Runtime read model 核对，并回答所在位置、该处能力、状态含义和正式下一步位置；追问可得到解释或导航，但 Confirm、Human decision 和 Runtime action 仍只能在 owning surface 执行。
- 切换 workspace、任务对象或 activity 后，Guide 明确标示上下文变化；旧会话可回看但不会被标作当前事实。

### AC-FR1401-02
- 首次 Setup、首次 Story、首次 Released 或新 attention 状态可触发 Guide 的显著说明，但不会自动切换 activity、抢夺键盘焦点、滚动/遮蔽主功能、清除未发送输入或阻止用户直接操作正式功能。
- 状态未变化时重复登录不会重复追加同一欢迎/提醒；改变 Guide 内容或 last-seen 而不改变 canonical 状态，不会改变登录落点、责任方或合法动作。

<a id="ac-fr-1501"></a>

## FR-1501 Guide、专业 Agent Chat 与 Maestro 退役边界

### AC-FR1501-01
- 新用户旅程和 Agent picker 不展示或 dispatch Maestro，Guide 也不作为可选专业 Agent；Guide 中的交互不能 author/review artifact、提交 Human decision、选择/dispatch Agent、触发阶段转移、写入 evidence 或改变 Runtime 状态。
- Guide 提供的下一步与 Runtime required action 一致；尝试从 Guide 越权执行正式动作不会产生 workflow 状态变化。

### AC-FR1501-02
- Scribe、Sage、Archer、Devon 等专业 Agent Chat 可核对地绑定 Runtime 指定的 task/session、artifact、write/review scope，并在产品中与 Guide 会话明确区分。
- 历史 Maestro session/evidence 若可访问，仅显示为只读历史或明确迁移状态，不会成为当前 Guide/Runtime 的第二 authority。

<a id="ac-nfr-0001"></a>

## NFR-0001 持久化恢复、幂等与并发安全

### AC-NFR0001-01
- 在 Setup 各步骤、Confirm/Apply 中及 Story 启动后分别刷新或重启，恢复结果与最近持久化的 Setup revision、Human 选择、Manifest、operation result、Workbench 对象和 Runtime state 一致。
- 对同一 revision 并发或重复 Confirm/重试，外部 repository/provider 结果和产品对象均至多创建一次；stale revision 被拒绝且不会覆盖当前状态。

### AC-NFR0001-02
- 外部结果无法确认时，公开状态保持 attention/结果不确定，保留可用于 reconcile 的 evidence，并且不会开放依赖成功结果的下一动作。

<a id="ac-nfr-0101"></a>

## NFR-0101 Secret、权限与本地副作用保护

### AC-NFR0101-01
- 使用可识别的测试 credential 执行身份、provider 和 Setup 流程后，在 Setup Manifest、Guide/Agent 输入、事件、日志、错误详情、文档和提交出口中均检索不到原始 secret；只可见非秘密 identity、计数、redacted diagnosis 或 digest。
- 未获得当前 Human 对当前 revision 的明确授权时，init、clone、remote/binding 和外部 namespace 均无新增或修改结果。

### AC-NFR0101-02
- 对 workspace 范围外目标、权限不足或无法归属的已有文件/资源执行 Setup，操作被拒绝或进入 attention，且这些文件/资源未被覆盖或删除。

<a id="ac-nfr-0201"></a>

## NFR-0201 单一状态权威与可验证新鲜度

### AC-NFR0201-01
- 对同一 workspace/release/revision，Setup、驾驶舱、Guide、兼容深链和专业 Agent Chat 展示的 canonical 状态、责任方与 required action 相互一致，并可核对同一 Runtime/Manifest revision。
- Runtime 状态推进后，使用旧客户端缓存、旧聊天摘要或历史页面不能把状态回退；产品刷新到当前状态并显示当前可继续位置。

### AC-NFR0201-02
- 对 stale、对象 identity 不匹配或 revision conflict 的读写尝试，不产生第二份兼容状态或对象；用户看到冲突及 canonical 对象的恢复入口。

<a id="ac-nfr-0301"></a>

## NFR-0301 可访问、响应式且非侵入的 Workbench

### AC-NFR0301-01
- 仅使用键盘即可依次到达并操作 Wizard 步骤、错误恢复、Confirm、Guide 折叠/恢复和 Runtime 合法下一动作；这些控件具有可理解的可访问名称，状态和错误不只用颜色区分。
- 在产品声明支持的最小窗口尺寸和文本缩放范围内，主功能、Guide 控制和合法下一动作保持可见或可达，内容不因 Guide 固定挂载而不可操作。

### AC-NFR0301-02
- Guide 在用户编辑主功能或尚有未发送输入时收到状态更新，不会改变当前焦点或造成输入丢失；更新可通过非侵入状态提示被辅助技术识别。

<a id="ac-nfr-0401"></a>

## NFR-0401 四 Spec 升级与历史兼容

### AC-NFR0401-01
- 升级一个具有有效 Setup、Project、Run、release request、artifact 和 milestone 历史的 workspace 后，无需重新 Setup 即可在 Workbench 访问相同 identity、状态和 artifacts，且没有因迁移产生的重复对象。
- 在兼容期通过旧路由或版本化协议读取/提交受支持操作，结果解析到 canonical Workbench 对象；一次新写入只产生一份权威状态。

### AC-NFR0401-02
- 无法安全映射的历史 Maestro/run 显示为只读或明确需要迁移；它不会被静默显示为当前 Guide 会话、Runtime 状态或可执行 action。

<a id="ac-nfr-0501"></a>

## NFR-0501 可操作诊断与用户可理解性

### AC-NFR0501-01
- 对 Wizard 和驾驶舱的代表性失败、冲突及结果不确定状态，用户可见结果包含失败对象、当前已知事实、对任务的影响、当前责任方和可执行恢复位置；仅有内部异常、run ID 或笼统“失败/重试”的结果不通过验收。
- 用户从空白 workspace 完成 Setup 并开始 Story 的主路径只要求处理身份、repository、依赖、Review/Confirm 和 Story 输入；没有一步要求用户输入或解释 Runtime stage、release container 或 Agent 编排术语。需要诊断时，可以从当前上下文展开 evidence 和相关 artifact。
