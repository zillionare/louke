# 最小首次设置、Project 创建引导与 Project Status — Acceptance Criteria

- **Spec ID**：`v0.14-004-workspace-onboarding-workflow-status`
- **关联 Story**：`STR-1405`
- **Story SHA-256**：`f2595e5aa1c71ca829fcc2d27458aa599381d2ca51bf6e25e85df422000475af`
- **Spec SHA-256**：`4d9aec6c0073a225b0aaeff2a530671f5b6ea233775c1a167beadf716508e5cd`
- **创建日期**：2026-07-24
- **状态**：草稿

> 本 Acceptance 人工绑定上述 Story/Spec digests，作为 v0.14 Runtime 尚未接管阶段的 M-ACC 上游版本。本文不声明流程状态已由 Runtime 推进。
>
> 每项 AC 通过公开产品入口、用户可见结果、持久化状态、Runtime read model 或可核对的外部结果断言；不要求未被 Spec 锁定的精确文案、组件、API schema 或内部算法。

## FR-0001 Setup 未完成时的全局用户入口保护

### AC-FR0001-01
- 在没有 Setup 完成状态的 workspace 中分别访问登录页、Workbench、Projects、Project/Run/文档深链及其他用户功能地址，浏览器最终均停留在 `/setup`，且不能操作被请求的用户功能。
- `/setup` 所需资源和提交入口仍可完成首用户与模型验证，但直接调用这些入口不能打开其他用户功能或伪造 Setup 完成。

### AC-FR0001-02
- 当前 workspace 写入有效 Setup 完成状态后，重新访问登录页或用户功能地址不再因首次设置被送回 `/setup`。
- 仅改变 cookie、Guide 内容、首用户存在性或 OpenCode executable 存在性，而不满足完整 Setup 状态时，入口保护仍然生效。

## FR-0101 首用户创建与可恢复连续性

### AC-FR0101-01
- 无本地用户时，用户能在 `/setup` 创建唯一首用户；创建成功后刷新页面或重启服务，该用户仍存在且 Setup 从模型验证继续，不再要求重新创建用户。
- 首用户存在后，页面不再提供创建第二个“首用户”的成功路径。

### AC-FR0101-02
- 对同一首用户请求重复提交，产品复用已发生结果或显示明确冲突，持久身份数量不增加。
- 首用户创建失败或只有首用户创建成功时，Setup 完成状态仍不存在，其他用户功能仍受 FR-0001 保护。

## FR-0201 OpenCode 与至少一个模型的真实运行验证

### AC-FR0201-01
- 当 OpenCode executable、provider credential 和模型列表均存在但实际最小模型请求失败时，Setup 不显示验证通过。
- 只有 Runtime 在当前 workspace 中执行真实最小请求且至少一个已配置模型成功响应后，模型验证才显示通过；该请求不会创建 Louke Project、Git/GitHub 资源、release 或 workflow。

### AC-FR0201-02
- 对 OpenCode 不可调用、全部模型失败、认证/网络错误、超时及结果无法确认的代表性场景，用户仍停留在 `/setup`，能看到定位到 OpenCode/模型检查的非秘密原因和重试入口。
- 修复后使用重试入口可获得基于新事实的结果，同时已经创建的首用户不需要重新创建。

## FR-0301 Setup 完成记录与 Workbench 交接

### AC-FR0301-01
- 首用户已持久化且真实模型验证成功后，当前 workspace 产生唯一 Setup 完成状态，并将当前用户直接带到 Workbench Projects。
- 此完成路径不要求配置 Git、GitHub CLI、repository、release 或 Project。

### AC-FR0301-02
- Setup 完成后刷新、重启或再次登录，用户复用同一完成状态进入产品，不重复首次用户步骤或模型探测。
- Setup 状态写入失败或结果不确定时，产品保持未完成并恢复到模型验证位置，不显示完成、不开启其他用户功能，也不产生第二个完成记录。

## FR-0401 登录后的 Projects 状态落点

### AC-FR0401-01
- Setup 完成的用户登录后，WorkBench 进入 Projects 上下文；存在唯一活跃 Project 时，main panel 显示该 Project Status。
- 不存在活跃 Project 时，main panel 显示空 Project、用途提示和 `New Project` 主动作，而不是要求用户先访问 Runs 或通用 Chat。

### AC-FR0401-02
- 活跃 Project 存在时，Projects 主路径不提供创建第二个主 Project 的成功动作。
- 持久事实同时声称多个 Project 活跃时，页面显示可定位冲突并阻止选择或创建；改变列表顺序、最近访问记录或 Guide 建议不会静默选定其中一个。

## FR-0501 Projects Sidebar 的 Guide 上下文

### AC-FR0501-01
- Projects sidebar 始终提供 Guide session；活跃 Project 页面中的会话可核对为绑定该 Project 与当前 Runtime revision，空 Project 页面中的会话明确处于空 Project 上下文。
- Guide 能从当前上下文解释 `New Project`、环境门禁及 owning Wizard 的修复位置，而无需用户重新说明正在操作哪个 Project。

### AC-FR0501-02
- Environment 检查产生阻断错误时，chat window 先显示可与建议区分的 Runtime 失败步骤和结果，随后 Guide 在用户未发送消息的情况下自动给出针对该错误的建议。
- 自动建议包含失败对创建 Project 的影响、修复方法和 owning surface；建议可渐进出现，用户仍可在其后继续追问。
- 同一检查 revision 被重复投影时不会重复追加同一主动建议；产生新失败或重试结果后可显示相应的新状态与建议。

### AC-FR0501-03
- Guide 内容或用户在 Chat 中的回复不能把检查标为通过、安装工具、改变认证、创建 Project/Story、选择活跃节点、执行回拨或推进 Runtime 状态。
- 需要安装、认证或其他外部修改时，用户必须在正式授权入口执行；只阅读 Guide 建议不产生该副作用。

## FR-0601 New Project 的按需环境门禁编排

### AC-FR0601-01
- 用户停留在首次 Setup 或空 Project 而未点击 `New Project` 时，不会被强制进入 Git/GitHub 环境门禁；点击后才打开 Environment Wizard 并开始后台检查。
- 检查按 GitHub CLI、GitHub 认证/scopes、Git repository/binding 覆盖全部必要项；通过项不展开成逐项确认页面，全部通过后用户直接进入 Story/版本输入。

### AC-FR0601-02
- 任一检查失败或结果不确定时，Wizard 显示对应失败步骤、影响和重试/修复入口，且用户不能进入 Story/版本输入、Preview 或 Project 创建。
- 修复后重新检查，只有全部必要项基于当前事实通过才解除门禁；已通过步骤仍不膨胀为无意义的交互步骤。

## FR-0701 GitHub CLI、认证与 Scope Readiness

### AC-FR0701-01
- 对 `gh` 缺失、不可执行、`gh auth status` 失败、GitHub host/身份无法确定，以及分别缺少 `gist`、`project`、`repo` 或 `workflow` scope 的场景，门禁均显示失败并阻止 Project 创建。
- 只有 `gh` 可执行、目标 host 已登录且当前认证同时具有四项必需 scope 时，此检查显示通过。

### AC-FR0701-02
- 失败结果明确列出未满足项及其阻断影响，Guide 无需用户先输入即可提供安装、登录或补 scope 的修复建议。
- 未经 Human 在正式入口授权，产品不会自动安装 `gh` 或改变认证；scope 检查通过后，后续 GitHub 操作若真实失败仍显示该操作自身的失败，不会引用 readiness 伪报成功。

## FR-0801 Git Repository 初始化、绑定与可用主分支

### AC-FR0801-01
- 当前 workspace 不是 Git repository，或虽已初始化但没有可验证 GitHub binding 时，Wizard 显示 repository URL 输入并保持阻断。
- 用户提交 URL 并继续后，Runtime 仅在当前 workspace 范围内执行初始化/binding；只有重新读取 repository、remote identity 与 binding 均通过才进入后续输入步骤。

### AC-FR0801-02
- 用户提供的新建空 repository 在门禁成功前具有可供 Foundation 验证的 canonical `main`；后续创建不会再因 remote 不存在 `main` 而通过门禁后立即失败。
- 对已有 remote 的主分支缺失、冲突、歧义、diverged、部分成功或结果不确定，门禁保持阻断并显示恢复位置，且不会覆盖 remote、提交 Louke secret/运行状态或无法归属的用户文件。

## FR-0901 Story 与 Release Version 的浏览器草稿

### AC-FR0901-01
- 环境门禁通过后，用户输入非空 Story 与 release version 并进入下一步；刷新、关闭后在同一浏览器返回时，输入和可继续位置能够恢复。
- 恢复草稿后，若环境事实已经变化，产品先重新确认门禁而不是直接使用草稿绕过检查。

### AC-FR0901-02
- 仅填写、保存或恢复草稿时，workspace 中没有由该草稿创建的正式 Story、Project、WorkflowRun、GitHub Project、release branch、Spec 目录或阶段状态。
- 在其他浏览器/设备打开或清除浏览器数据后无法恢复草稿，不视为本合同失败。

## FR-1001 Story/版本预览与无副作用取消

### AC-FR1001-01
- Preview 在创建副作用前同时显示 Story、规范化 release version、workspace/repository identity 及 `Create`、`Cancel` 动作。
- 仅生成或查看 Preview 时，不存在由本次请求创建的 Project、Story 文件、WorkflowRun、GitHub Project、branch 或 Spec 目录。

### AC-FR1001-02
- 用户选择 `Cancel` 后返回空 Project，未产生上述副作用；再次进入创建流程时，同一浏览器的 Story/版本草稿仍可恢复。
- 修改输入/readiness 后提交旧 Preview，产品将其识别为 stale 并拒绝创建，随后提供基于当前事实重新预览的位置。

## FR-1101 确认创建、Scribe Story 与 Dev Docs 结果

### AC-FR1101-01
- 已认证 Human 确认当前且 readiness 仍通过的 Preview 后，产品创建或 reconcile 一组可相互核对的 Project、规划 release、WorkflowRun、GitHub Project、release branch 与 Spec 目录身份，并基于已验证 `main` 进入同一 Project 的 `M-STORY`。
- Scribe 使用该确认的 Story/版本生成 canonical `story.md` revision；持久化成功后浏览器进入 Dev Docs，加载该 Project 的最新 `story.md`，并可从该上下文继续工作。

### AC-FR1101-02
- 对同一 Preview 重复、并发或恢复 Confirm，最终只有一个 request/Project/Story 身份及一组 Foundation 资源，不产生第二个活跃 Project。
- 外部资源或 Scribe 部分成功、失败或结果不确定时，页面显示同一 Project 的可恢复状态，不跳到错误文档；重试先 reconcile 已发生结果，不重复资源、不覆盖冲突 Story，也不伪报完成。

## FR-1201 Project Status 的完整 Workflow 与活跃节点

### AC-FR1201-01
- 活跃 Project 的 main panel 同时突出 Runtime 指定的当前节点并提供可导航线性时间线；时间线覆盖从 `M-START` 到 `M-MILESTONE` 的全部 canonical 阶段，并区分完成、活跃、待处理、需要处理和失效状态。
- 新 Project 只显示 `M-REQ-APPROVAL`；读取含 `M-LOCK-1` 的历史时，它映射为同一批准节点而不是第二阶段，批准后的 Issues 作为该节点的结果/evidence 显示。

### AC-FR1201-02
- running 节点的突出区域显示责任方、attempt/轮次与随时间推进的运行时长；`waiting_human`、`blocked` 或 `conflict` 节点显示原因、影响和与 Runtime 一致的唯一主要动作。
- 两种模式均能看到 canonical 状态、当前 artifact/revision 或 operation、最近 evidence/错误及 owning surface；改变 Guide 或客户端缓存不能改变这些事实。

### AC-FR1201-03
- 每次阶段 attempt（包括打回后的重做）按实际顺序显示为独立节点；新 attempt 不会折叠、覆盖或改写历史 attempt，推进方向和既有回拨的来源/目标均可辨认。
- 节点超出可见范围时，初始视图保持活跃节点及邻近上下文可见，并提供访问全部历史节点的交互；不要求特定滚动、缩放或组件实现。

## FR-1301 选中节点详情与上下文返回

### AC-FR1301-01
- 选择任一可查看时间线节点后，详情显示该 attempt 的开始/结束时间、状态、责任方、artifact/revision、关键 evidence/错误、状态转移原因、当前回拨合法性和适用动作。
- 详情明确区分选中节点与当前活跃节点；选择历史或未来节点不改变 Runtime active pointer 或 workflow 状态。

### AC-FR1301-02
- 从节点详情可进入对应 owning artifact/operation；artifact 存在时可跳转 Dev Docs 或适用 surface，返回后仍处于同一 Project 和可识别的节点上下文。
- 目标不存在、stale 或无权访问时显示对应可定位结果，不会静默进入另一 Project、attempt 或 revision。

## FR-1401 Runtime 允许的回拨指针与安全执行

### AC-FR1401-01
- 时间线只对 Runtime 当前允许的先前 attempt 显示回拨能力；选中节点详情显示其当前合法性，只有合法目标提供回拨主动作。
- 已发生回拨在时间线中显示可辨认的来源、目标与方向；不支持或已失效目标不能通过旧页面触发状态改变。

### AC-FR1401-02
- 发起合法回拨后，确认界面在执行前显示目标、会失效或重做的下游 artifact/review/evidence，以及不能自动逆转的外部后果；取消确认不改变状态。
- Human 确认且 Runtime 复核仍合法后，同一 Project 的 active pointer 回到目标，历史保留，下游结果按 owning 合同显示 stale、superseded 或待 reconcile；并发推进或复核失败时不执行并显示当前继续位置。

## FR-1501 Project 用户概念、对象身份与兼容入口

### AC-FR1501-01
- Projects landing、New Project、Project Status、Guide 与 Dev Docs 对同一工作统一使用 Project 概念，并可核对其规划 release、GitHub Project、WorkflowRun 与 Story 属于同一对象链。
- 完成 New Project 到 Dev Docs 再返回 Project Status 的旅程，不会产生第二 Project/Run 身份或要求用户重新选择同一工作。

### AC-FR1501-02
- `/projects`、`/projects/new`、Project detail、Run 与 Story 兼容深链解析到同一 Workbench Project 和 Runtime 状态；刷新或返回不会进入平行对象页面。
- 历史 `Workflow Runs` 可保留兼容标签，但不因升级被复制；新旅程和新写入只产生 canonical Project 身份与一份可写状态。

## NFR-0001 持久化恢复、幂等与并发安全

### AC-NFR0001-01
- 分别在首用户创建后、Setup 完成后、Project Confirm 部分完成时及回拨执行中刷新或重启，恢复结果与最近可证明的持久化身份、revision、Runtime 状态和外部 operation 结果一致。
- 浏览器草稿只按 FR-0901 在同一浏览器恢复，不会被误写成 workspace 的正式 Project 状态。

### AC-NFR0001-02
- 对同一 revision 重复或并发提交用户创建、Setup 完成、Project Confirm、外部重试或回拨，至多一个请求改变 canonical 状态，各产品/外部身份至多创建一次。
- stale 请求或外部结果无法确认时，公开结果保持冲突/attention/不确定并保留 reconcile evidence，不开放依赖成功的下一动作。

## NFR-0101 Secret、权限与外部副作用保护

### AC-NFR0101-01
- 使用可识别测试 secret 完成 Setup、GitHub/Git 检查、Guide 建议和 Project 创建后，在 Setup 状态、browser draft、Guide/Agent 对话、Runtime event、日志、错误详情、Story、Git 历史及用户可下载出口中检索不到原始 password、session secret、token、URL credential 或 provider secret。
- 用户可见内容仅包含完成判断需要的 redacted identity、缺失 scope 名称及非秘密诊断。

### AC-NFR0101-02
- 模型探测请求不含 Louke artifact 或用户 Story，且不会产生 Project/Git/GitHub 副作用。
- 未经 Human 在正式入口确认，Git 初始化/binding、认证变更、GitHub Project 创建和回拨外部操作均无结果；范围外或无法归属的数据不会被覆盖或删除。

## NFR-0201 外部检查的新鲜度、超时与可操作诊断

### AC-NFR0201-01
- OpenCode/model、`gh`、认证/scopes、Git repository/binding 和 remote 主分支检查在产品声明的有界等待后得到成功或可定位失败；超时、不可执行、无法解析、网络错误及结果不确定均不会沿用旧成功继续创建。
- 从检查通过到依赖动作之间改变对应外部事实，产品在执行前检测变化并重新阻断，而不是使用 stale readiness。

### AC-NFR0201-02
- 代表性失败结果包含失败对象、已知事实、对任务的影响和修复位置，且不只显示内部异常、run ID 或笼统“失败”。
- Guide 投影或主动建议生成失败时，Wizard 仍显示权威检查结果；chat window 已出现的 Runtime 结果保持可见并提供 owning Wizard 入口，且该 Guide 故障不被解释成环境检查通过或失败。

## NFR-0301 可访问且不丢失输入的操作路径

### AC-NFR0301-01
- 仅使用键盘即可完成 Setup、打开/取消 Environment Wizard、修复后重试、输入 Story/版本、Preview/Create、选择 workflow 节点及发起/取消回拨；操作具有可理解的可访问名称。
- Setup、检查、节点和错误状态不只依赖颜色表达，辅助技术可辨认当前状态、失败原因和主要动作。

### AC-NFR0301-02
- 后台检查或 Guide 自动建议出现时，不改变用户当前焦点、不清除 Story/版本或 Chat 未发送输入，也不遮断取消、返回和 owning Wizard 修复入口。
- 在产品声明支持的窗口尺寸与文本缩放范围内，关键动作、失败原因、Guide 和 Project Status 全部历史的导航入口保持可达。

## NFR-0401 单一状态权威与升级兼容

### AC-NFR0401-01
- 对同一 workspace/Project/revision，Projects landing、Environment Wizard、Project Status、Guide、Dev Docs 及兼容路由显示的 canonical 状态、责任方与合法动作相互一致并可核对同一 Runtime revision。
- Runtime 状态推进后，旧缓存、旧 Guide 摘要、历史 artifact 或旧页面不能将状态回退或创建第二套可写事实；产品显示当前 revision 与继续位置。

### AC-NFR0401-02
- 升级具有有效用户、Setup、Project、Run、release、Story、artifact、evidence 与 milestone 历史的 workspace 后，用户无需无故重做 Setup，且能通过同一对象身份访问可映射历史，不产生重复对象。
- 无法安全映射的旧状态显示为只读或明确需要迁移；历史 `M-LOCK-1` 只映射为 `M-REQ-APPROVAL` 的兼容别名，不成为第二可写阶段。
