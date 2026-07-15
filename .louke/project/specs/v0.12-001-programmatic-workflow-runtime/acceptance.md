# Programmatic Workflow Control — Acceptance Criteria

- **Spec ID**：`v0.12-001-programmatic-workflow-runtime`
- **Created**：2026-07-13
- **Status**：M-DEV completed (2026-07-14); v0.12.1 stabilization patch (Batches 1-6) committed on `main` 2026-07-15; tag `v0.12.1` (post-tag CI fixes: `eac37d9`, `d8cfee2`, `78a65e6`)

> 每个条件从 Runtime 的公开服务接口、Web 用户界面、持久化观察出口或外部 adapter 边界验证。不得通过读取或修改内部 Python 对象伪造通过。

<a id="ac-fr-0001"></a>
## FR-0001 版本化工作流定义

### AC-1
AC-FR0001-01

- **Given** 一个分别包含未知步骤、悬空转移、重复 step/edge ID、不可达必需步骤或不支持步骤类型的 definition，**When** 请求验证或启动运行，**Then** 每种无效情况都返回可定位类型和节点的稳定 validation error，且不创建 WorkflowRun。

### AC-2
AC-FR0001-02

- **Given** 一个有效 definition，**When** 创建 WorkflowRun，**Then** 查询结果包含固定的 definition id、version、起始步骤和 revision 0/初始 revision。

### AC-3
AC-FR0001-03

- **Given** 已经由 definition v1 创建的运行，**When** 同名 definition v2 被注册，**Then**旧运行仍按 v1 的步骤及转移推进，新运行才使用 v2。

<a id="ac-fr-0101"></a>
## FR-0101 Runtime 是状态与转移的唯一写入者

### AC-1
AC-FR0101-01

- **Given** 运行当前停在 `lock`，**When** 客户端请求直接执行 `development` 或提交 `next_step=development`，**Then** 请求被拒绝，current step、status、revision 和事件数均不发生成功转移。

### AC-2
AC-FR0101-02

- **Given** 当前步骤只声明 `approved` 和 `rejected` 两种结果，**When** executor 返回其他结果，**Then** Runtime 记录失败诊断但不执行任何未声明转移。

### AC-3
AC-FR0101-03

- **Given** 两个客户端读取相同 revision，**When** 第一个成功改变状态后第二个再提交，**Then** 第二个收到 state conflict，并能读取新的 revision。

### AC-4
AC-FR0101-04

- **Given** 一个有效当前步骤，**When** Runtime 接受其结果，**Then** next step 必须等于绑定 definition 对该结果声明的目标，客户端无法替换目标。

<a id="ac-fr-0201"></a>
## FR-0201 持久化 WorkflowRun 与恢复

### AC-1
AC-FR0201-01

- **Given** 一个停在 `waiting_for_human` 的运行，**When** Louke 进程停止并使用同一 workspace 重新启动，**Then** 列表和详情仍显示相同 run、step、gate、revision 和 contract digest。

### AC-2
AC-FR0201-02

- **Given** 一个步骤结果已经事务提交，**When** Runtime 重启并 resume，**Then** 已提交的步骤不会被再次当作未执行步骤产生副作用。

### AC-3
AC-FR0201-03

- **Given** Runtime 在步骤结果是否提交无法确定的位置中断，**When** 恢复运行，**Then** 运行进入明确的 recoverable/needs-attention 状态，而不是自动标记成功并进入下一步。

<a id="ac-fr-0301"></a>
## FR-0301 注册式程序步骤与幂等执行

### AC-1
AC-FR0301-01

- **Given** definition 引用未注册 handler 或包含任意 shell 命令字段，**When** 验证 definition，**Then** Runtime 拒绝它且不执行该内容。

### AC-2
AC-FR0301-02

- **Given** 一个已注册 handler，**When** Runtime 执行步骤，**Then** handler 收到包含 run、step、attempt、workspace 和 idempotency key 的只读上下文，并返回 schema-valid 结果。

### AC-3
AC-FR0301-03

- **Given** handler 抛出异常、超时或返回 schema-invalid 数据，**When** 本次 attempt 结束，**Then** Runtime 不把步骤标记成功，且公开状态包含稳定错误码和可诊断事件。

### AC-4
AC-FR0301-04

- **Given** 某 idempotency key 的外部副作用已经成功并记录，**When** 同一步骤因恢复被再次请求，**Then** adapter 观察到该副作用总计只发生一次。

<a id="ac-fr-0401"></a>
## FR-0401 Foundation 程序前置条件

### AC-1
AC-FR0401-01

- **Given** foundation 已完整，**When** 运行到 `foundation.ensure`，**Then** 结果为 `satisfied`，流程继续，Agent executor 没有收到 Scout 或 Warden 调用。

### AC-2
AC-FR0401-02

- **Given** foundation 缺少可自动创建的资源，**When** 首次和再次执行 ensure，**Then** 首次结果为 `repaired`、再次为 `satisfied`，外部 adapter 中每种资源最多创建一次。

### AC-3
AC-FR0401-03

- **Given** foundation 缺少必须由人选择的信息，**When** ensure 执行，**Then** 运行停止在 `blocked`，返回结构化问题，且不创建猜测资源。

### AC-4
AC-FR0401-04

- **Given** foundation 检查发生不可恢复错误，**When** ensure 结束，**Then** 运行显示 `failed` 或 policy 声明的 retryable 状态，不进入主 workflow 的下一步骤。

<a id="ac-fr-0501"></a>
## FR-0501 不可绕过的人类门禁

### AC-1
AC-FR0501-01

- **Given** Runtime 到达任一 human gate，**When** 没有人类决定，**Then** 状态为 `waiting_for_human`；重复 resume、Maestro 建议或后续步骤请求均不能推进。

### AC-2
AC-FR0501-02

- **Given** 一个有效 gate，**When** 已认证 human principal 使用匹配 challenge、revision 和 artifact digest 批准，**Then** Runtime 记录批准证据并只执行 definition 的 `approved` 转移。

### AC-3
AC-FR0501-03

- **Given** 请求体或 Agent 输出包含任意 `approved_by` 字符串但宿主没有 human principal，**When** 提交批准，**Then** Runtime 拒绝请求且 gate 保持 pending。

### AC-4
AC-FR0501-04

- **Given** challenge、revision、step 或 artifact digest 任一已过期，**When** 提交旧批准，**Then** 返回 stale-gate/state-conflict，且不进入后续步骤。

### AC-5
AC-FR0501-05

- **Given** gate 已批准，**When**该 gate 绑定的任一 artifact 在后续允许步骤开始前发生变化，**Then** 旧批准不再有效，运行重新进入绑定新 digest 的 `waiting_for_human`。

### AC-6
AC-FR0501-06

- **Given** 有效 human principal 拒绝 gate，**When** 查询运行和事件，**Then** 后续步骤未执行，并可观察 actor、时间、理由和被拒绝的 digest。

<a id="ac-fr-0601"></a>
## FR-0601 事件与证据

### AC-1
AC-FR0601-01

- **Given** 一次依次发生 run 创建、step start/end、blocked、retry、transition 和 gate decision 的运行，**When** 按 run 查询事件，**Then** append-only 事件按稳定顺序覆盖每种 event type，且每条都包含 run、step、attempt、revision、event type、timestamp、correlation id 及适用的 input/output digest。

### AC-2
AC-FR0601-02

- **Given** 一次状态改变成功提交，**When** 查询当前状态及最后事件，**Then** 两者具有一致 revision；不存在只提交其中一项的可观察状态。

### AC-3
AC-FR0601-03

- **Given** StepContext 或 human principal 包含 secret/credential，**When** 查询事件，**Then** 事件只含允许的身份标识与 digest，不包含秘密或完整凭据。

<a id="ac-fr-0701"></a>
## FR-0701 新旧流程隔离

### AC-1
AC-FR0701-01

- **Given** `project.toml current_stage` 与新 run 当前步骤不同，**When** 查询或 resume 新 run，**Then** 新 run 的状态不随该字段改变。

### AC-2
AC-FR0701-02

- **Given** 一个新 WorkflowRun，**When** 调用旧 `maestro advance --stage ...`，**Then** 新 Runtime 的 run revision、current step 和事件不发生变化。

### AC-3
AC-FR0701-03

- **Given** definition 引用未接入的 adapter、handler、step capability 或 version，**When** 验证或启动，**Then** 返回明确 unsupported error，不创建一个随后 echo 或永不执行的假运行；完整 v0.12 capability report 中 `agent_task` 与 `decision` 必须因真实实现而可用。

<a id="ac-fr-0801"></a>
## FR-0801 需求文档人类审批门

### AC-1
AC-FR0801-01

- **Given** story、spec、acceptance 已完成要求的评审，**When** Runtime 到达需求审批步骤，**Then** 创建一个绑定三份文档共同 digest 的 gate，并停在 `waiting_for_human`。

### AC-2
AC-FR0801-02

- **Given** 需求审批仍 pending 或已 rejected，**When** 任意调用者请求启动、完成或登记 test-plan、architecture、interfaces 任务，**Then** Runtime 拒绝请求，且没有设计任务或设计产物被记为已接受。

### AC-3
AC-FR0801-03

- **Given** human principal 对当前 digest 提交有效批准，**When** Runtime 接受决定，**Then** 运行只进入允许产生和评审设计文档的阶段，开发步骤仍不可启动。

### AC-4
AC-FR0801-04

- **Given** 需求 gate 已批准，**When** story、spec、acceptance 任一文档发生改变，**Then** 原批准变为 stale，设计流程不得基于旧批准继续，且新 gate 绑定新的共同 digest。

### AC-5
AC-FR0801-05

- **Given** human principal 拒绝需求 gate 并提供理由，**When** 查询运行和事件，**Then** 运行返回需求编写/评审状态，理由与 digest 可审计，且设计任务未启动。

### AC-6
AC-FR0801-06

- **Given** `bug_fix` 引用一个既有 GitHub Issue 和已批准 source spec/AC，**When** 程序验证它只修复实现偏差且不改变预期行为，**Then** run 继承 source requirements approval 而不创建新的需求 gate；缺少映射、需求含糊或行为改变时，hotfix 快速路径被拒绝并要求进入新需求流程。

<a id="ac-fr-0901"></a>
## FR-0901 设计文档 Review 与 M-LOCK

### AC-1
AC-FR0901-01

- **Given** 需求审批有效，**When** Runtime 沿已声明转移推进，**Then** test-plan、architecture、interfaces 的生成与评审任务可以启动；需求审批无效时相同请求被拒绝。

### AC-2
AC-FR0901-02

- **Given** 三份设计文档已完成规定的程序校验、Agent review 和用户 review，**When** Runtime 到达 M-LOCK，**Then** 创建绑定已批准需求文档和当前设计文档共同 contract digest 的 gate。

### AC-3
AC-FR0901-03

- **Given** M-LOCK 未获得当前有效批准，**When** 任意调用者请求创建或启动 Devon session、实现 worktree、实现任务或实现 commit，**Then** 请求被拒绝且不存在被接受的实现副作用。

### AC-4
AC-FR0901-04

- **Given** human principal 对当前 M-LOCK 提交有效批准，**When** Runtime 接受决定，**Then** 运行只沿 definition 的 `approved` 边进入实现阶段，并留下完整批准证据。

### AC-5
AC-FR0901-05

- **Given** M-LOCK 已批准但实现尚未开始，**When** 任一绑定文档改变，**Then** 原批准变为 stale，Runtime 按 workflow 声明返回对应上游步骤，且不得静默创建实现任务。

<a id="ac-fr-1001"></a>
## FR-1001 Projects 导航与历史项目

### AC-1
AC-FR1001-01

- **Given** 用户打开任意 Louke Web 页面，**When** 查看 sidebar 中的 Projects 菜单，**Then** 能访问当前项目列表、历史项目列表和“创建新项目”入口。

### AC-2
AC-FR1001-02

- **Given** workspace 中同时存在非终态未归档项目和终态/已归档项目，**When** 分别打开当前与历史列表，**Then** 前者只出现在当前列表，后者只出现在历史列表。

### AC-3
AC-FR1001-03

- **Given** Projects 列表包含两个以上项目，**When** 用户查看列表项，**Then** 每项显示可区分的名称、release version、workflow 类型和状态，并可打开对应详情。

### AC-4
AC-FR1001-04

- **Given** workspace 已有一个 active 非 hotfix Project，**When** 用户尝试创建另一个 `new_feature`，**Then** Runtime 不创建第二个主 Project，页面允许把 story 保存到 backlog，并保持现有 run 不变。

### AC-5
AC-FR1001-05

- **Given** workspace 已有一个 active 主 Project，**When** 用户创建满足 source Issue/contract 校验的已发布产品 hotfix，**Then** hotfix 可以作为 active 例外出现；两个 run 的 identity、worktree/branch、session、状态、事件和证据不发生串写。

<a id="ac-fr-1101"></a>
## FR-1101 创建新项目并选择工作流

### AC-1
AC-FR1101-01

- **Given** 用户点击“创建新项目”，**When** 页面加载完成，**Then** 表单提供 story、release version 和 workflow 输入并显示 catalog；选择 `bug_fix` 时额外要求 GitHub Issue，并显示解析出的 source spec/AC 或明确未找到。

### AC-2
AC-FR1101-02

- **Given** 首版 workflow catalog 已加载，**When** 用户查看和选择，**Then** 只直接提供 `new_feature` 与 `bug_fix`，提交前和确认结果中都显示实际 workflow id/version，并说明 `bug_fix` 是已发布产品 hotfix。

### AC-3
AC-FR1101-03

- **Given** 用户填写有效 story、release version 和 workflow，**When** 请求创建预览，**Then** 页面显示 story 摘要、release version、workflow id/version 和 readiness，且尚未创建 Project；用户确认同一预览后，系统原子持久化不可变 Project identity、从 story 形成的 display title 及首个真实 WorkflowRun，并导航到该运行详情。

### AC-4
AC-FR1101-04

- **Given** 字段缺失、release version 非法、workflow 不存在或创建发生并发冲突，**When** 提交表单，**Then** 页面显示可操作的错误，且项目与 WorkflowRun 均没有半创建记录。

### AC-5
AC-FR1101-05

- **Given** 用户打开首版创建表单，**When** 查看 workflow 选项或提交 backlog 条目，**Then** `spec_change` 不作为直接选项，backlog 只预填表单且仍需确认，系统不会暗中创建/选择 GitHub Project 或把条目映射到相近 workflow。

### AC-6
AC-FR1101-06

- **Given** active 主 Project 已占用 workspace，**When** 用户提交新的 `new_feature` story，**Then** 页面提供保存 backlog 而非启动第二个 run；主 Project 结束后从该条目进入创建页会预填原 story，但只有重新预览并确认才创建 Project。

### AC-7
AC-FR1101-07

- **Given** 用户选择 `bug_fix`，**When** GitHub Issue 缺失、不是已发布版本问题、无法映射已批准 spec/AC 或实际要求新行为，**Then** 创建被拒绝并建议 backlog/新需求流程；校验通过时可在 active 主 Project 旁创建隔离 hotfix，且不会生成新的 requirements 文档或 gate。

<a id="ac-fr-1201"></a>
## FR-1201 工作流图与当前位置

### AC-1
AC-FR1201-01

- **Given** 用户选择当前或历史项目，**When** 打开详情，**Then** 页面按该 run 绑定的 definition id/version 显示完整 workflow graph，definition 后续升级不改变历史图。

### AC-2
AC-FR1201-02

- **Given** run 中包含已完成、当前执行、等待人类、阻塞、失败、未开始或已跳过节点，**When** 渲染图，**Then** 每个实际出现的状态都有可区分标记，并突出当前节点或终态位置。

### AC-3
AC-FR1201-03

- **Given** 当前 run 的 revision 发生变化，**When** 页面收到事件或主动刷新，**Then** 图更新至同一 revision 的状态；仅操作图形本身不能改变 Runtime 状态。

### AC-4
AC-FR1201-04

- **Given** 用户打开历史 run，**When** 查看 UI 或调用对应管理 API，**Then** 原 run 完全只读，不提供恢复、重跑、fork 或绑定修改，任何写请求都不能改变其 revision、状态或事件。

<a id="ac-fr-1301"></a>
## FR-1301 Agent-model 绑定图与拖拽修改

### AC-1
AC-FR1301-01

- **Given** 项目包含一个或多个语义 Agent，**When** 打开 workflow 详情，**Then** 工作流图附近显示每个 Agent 的有效 model，并区分默认绑定与当前作用域覆盖。

### AC-2
AC-FR1301-02

- **Given** 用户把一个可用 model 拖到目标 Agent，**When** 服务端验证成功，**Then** 页面显示新绑定及“下一个任务生效”边界；不可用 model 被拒绝且原绑定不变。

### AC-3
AC-FR1301-03

- **Given** Agent task 已经开始并记录 model A，**When** 用户把该 Agent 改绑到 model B，**Then** 进行中的 task 继续记录并使用 A，该 Agent 下一个尚未开始的 task 使用 B。

### AC-4
AC-FR1301-04

- **Given** 一次绑定变更成功，**When** 重新加载页面并查询审计事件，**Then** 相同作用域内仍显示新绑定，事件包含 actor、Agent、旧 model、新 model、生效边界和时间。

### AC-5
AC-FR1301-05

- **Given** 当前 WorkflowRun 对 Agent 有 model override 或没有 override，**When** Runtime 创建新 Agent task，**Then** 前者使用 run override、后者使用 Louke Agent 默认 model，并把来源和解析结果固化到 task manifest；历史 run 不允许新增 override。

<a id="ac-fr-1401"></a>
## FR-1401 真实 OpenCode 运行实例与会话生命周期

### AC-1
AC-FR1401-01

- **Given** Web 报告 OpenCode 资源创建成功，**When** 通过管理接口查询，**Then** 存在与 run 绑定且可观察的真实 server、workspace 和 session identity；内存 echo 不能满足该条件。

### AC-2
AC-FR1401-02

- **Given** OpenCode task 仍需继续或稍后恢复，**When** 用户关闭页面或执行 detach，**Then** client connection 被释放但受管 server/session 按保留策略继续存在，WorkflowRun 不被误标为完成或删除。

### AC-3
AC-FR1401-03

- **Given** 一个仍可恢复的受管 session，**When** 同一授权 run 重新 attach，**Then** 用户看到该 session 的历史和当前状态；使用另一 run/session identity 的 attach 被拒绝。

### AC-4
AC-FR1401-04

- **Given** 一个活动 OpenCode 资源，**When** 用户分别选择停止当前生成、结束 session、释放 workspace instance 或终止 server，**Then** 只有所选层级发生定义的生命周期变化，并返回可验证的最终状态。

### AC-5
AC-FR1401-05

- **Given** Louke 服务重启且先前受管进程存在或已经丢失，**When** 执行恢复扫描，**Then** 可重连资源被重新关联，无法恢复的资源被标记为 lost/needs-attention，且不会虚假显示 running。

<a id="ac-fr-1501"></a>
## FR-1501 每步可定制且可追溯的 Agent 上下文

### AC-1
AC-FR1501-01

- **Given** Runtime 即将启动语义 Agent task，**When** 创建 task，**Then** 固化的 context manifest 至少包含 run/step/attempt、Agent、base commit/worktree、输入 artifact 及 digest、允许工具、允许写路径、输出 schema 和禁止副作用。

### AC-2
AC-FR1501-02

- **Given** 两个任务属于不同 run 或 step，**When** 分别创建 session context，**Then** 每个 context 只由稳定项目规则、所选 Agent prompt、自己的 task manifest 和自己的 session history 组成，不继承 Maestro 主聊天中的隐式工作流状态。

### AC-3
AC-FR1501-03

- **Given** Devon 被分配实现一批 GitHub Issues，**When** 检查其 manifest，**Then** 明确列出 Issues、各自验收条件、相关锁定设计文档、修改范围、权威测试和完成输出，未列出的 Issue 不自动进入任务范围。

### AC-4
AC-FR1501-04

- **Given** Agent session 丢失或 Louke 重启，**When** 查询 task 证据或按策略重建 session，**Then** 能读取当时实际使用的 manifest 和已持久化 Agent 结果，而不依赖操作者回忆 prompt。

### AC-5
AC-FR1501-05

- **Given** Agent 结果引用的 manifest、base commit 或 contract digest 与当前 task 不匹配，**When** 提交步骤结果，**Then** Runtime 拒绝该结果用于状态转移并记录稳定诊断。

<a id="ac-fr-1601"></a>
## FR-1601 程序职责与语义 Agent 职责分离

### AC-1
AC-FR1601-01

- **Given** 一项职责对相同输入有可枚举且确定的规则结果，**When** 验证 workflow definition 和 executor，**Then** 该职责由注册程序 handler 执行，不创建仅包装工具调用的 Agent task。

### AC-2
AC-FR1601-02

- **Given** Agent 输出声称改变 workflow state、批准 gate、通过权威测试或完成 commit/push/tag/publish，**When** Runtime 接收输出，**Then** 这些声明本身不产生控制面或发布副作用，只有对应程序 adapter 的真实证据可被接受。

### AC-3
AC-FR1601-03

- **Given** Agent 在允许 worktree 内产生 diff 和局部测试结果，**When** task 完成，**Then** 程序校验 diff/allowlist 并在声明的干净环境执行权威门禁，Agent 自报通过不能替代门禁结果。

### AC-4
AC-FR1601-04

- **Given** 新 workflow 包含原 Scout、Warden、Keeper 或其他 Agent 的职责，**When** 检查执行图，**Then** 已程序化的职责不再产生 Agent task；保留的 Agent task 必须声明需要语义判断的输入和输出。

### AC-5
AC-FR1601-05

- **Given** Agent 返回 schema-invalid、越权、artifact digest 不匹配或未声明 transition 的结果，**When** Runtime 验证结果，**Then** 结果被拒绝且运行不会推进到下一步骤。

### AC-6
AC-FR1601-06

- **Given** 发布候选中的全部内置 workflow definitions、Agent prompts/tool contracts、注册 handlers 与 built-in responsibility inventory，**When** 执行 catalog validation 并模拟实际 task dispatch，**Then** 每项内置职责恰有稳定 inventory entry 且无 `unclassified`/未登记项；`program` 只映射程序 handler，`semantic` task 只含声明的语义输入/输出，`mixed` 已拆除程序控制与权威副作用；插入任一漏登记职责、纯工具包装 Agent 或 inventory/dispatch 不一致都会在创建 Agent task 前失败。

<a id="ac-fr-1701"></a>
## FR-1701 固定工作流、动态分支与多工作流选择

### AC-1
AC-FR1701-01

- **Given** 一个 workflow definition，**When** 注册或启动，**Then** 所有节点、合法边、门禁、候选 decision 结果和版本均可枚举；Agent 不能在运行时增加节点或目标边。

### AC-2
AC-FR1701-02

- **Given** 用户在创建时明确选择一个已注册 workflow，**When** 创建 run，**Then** run 绑定该 definition/version；程序确定性分类只能在用户未明确选择且 definition 允许时发生。

### AC-3
AC-FR1701-03

- **Given** 输入存在歧义且当前节点声明需要语义 decision，**When** Runtime 咨询 Maestro，**Then** Maestro 只收到限定上下文和候选集合，并返回符合 schema 的候选、理由与置信信息。

### AC-4
AC-FR1701-04

- **Given** Maestro 返回候选外结果、直接副作用指令或需要人类确认的低置信建议，**When** Runtime 验证，**Then** 非法建议被拒绝或运行转入声明的人工澄清 gate，状态不会被建议本身改变。

### AC-5
AC-FR1701-05

- **Given** `new_feature`、有效 hotfix 及 active 主 Project 期间的新 requirement，**When** Runtime 分类并推进，**Then** 三者分别绑定完整需求 workflow、`quick_rgr|design_required` hotfix 图、或 backlog；任何 Agent 建议都不能跨 definition、绕过 source-contract 校验或创建第二个主 run。

<a id="ac-fr-1801"></a>
## FR-1801 Workspace 初始化、首位用户与就绪检查

### AC-1
AC-FR1801-01

- **Given** 一个符合支持条件但尚无 Louke metadata 的现有 Git repository，**When** 用户在该目录启动 `lk serve` 并首次打开 Web，**Then** server 提供 setup-only init-wizard 而不是因缺少 `project.toml` 退出；向导成功后 Runtime store/catalog 可读，且用户未运行另一条初始化 CLI或编辑内部文件。

### AC-2
AC-FR1801-02

- **Given** 同一 workspace 已初始化或包含可修复缺口/冲突，**When** 再次打开 init-wizard，**Then** 已就绪资源不重复创建，缺口以确定性方式修复或报告，冲突在用户确认前不覆盖已有源文件或 `.louke` 内容。

### AC-3
AC-FR1801-03

- **Given** initialized workspace 尚无 local human principal，**When** 首次访问 Web，**Then** 用户只能完成 setup/首位用户建立及只读 readiness；建立并登录后，gate API 才接受该 principal 的决定。

### AC-4
AC-FR1801-04

- **Given** workspace 的 Git、store、workflow catalog、OpenCode、models/providers 及 workflow-required integration 处于混合状态，**When** 查询 readiness，**Then** 每项显示稳定的 ready/degraded/blocked 状态、非秘密诊断和与该项对应的修复说明。

### AC-5
AC-FR1801-05

- **Given** OpenCode/provider 缺失但 Runtime store 和 docs 可用，**When** 用户浏览历史、文档或 readiness 并尝试启动 semantic task，**Then** 只读操作成功，task 停在 blocked 且不创建假 session，并显示完成授权/安装后重新检测的动作。

### AC-6
AC-FR1801-06

- **Given** init-wizard 检测到未完成的 Louke/OpenCode/model/provider 配置，**When** 用户在 Web 内完成 Louke 可管理的配置/授权并重新检测，**Then** 能观察到新能力且相关步骤可继续，不把另一条 Louke CLI 作为唯一动作；Project 文件、context manifest、事件、日志和响应均不包含原始 secret。

<a id="ac-fr-1901"></a>
## FR-1901 可操作的 Project 详情、Artifact Review 与审批 UI

### AC-1
AC-FR1901-01

- **Given** run 正在执行、等待、阻塞、失败或终止，**When** 用户打开 Project 详情，**Then** 页面显示同一 revision 的 status、current/final step、进入原因和 definition 当前允许的动作，不需要仅凭图形颜色猜测。

### AC-2
AC-FR1901-02

- **Given** 当前或历史节点具有输入/输出 artifacts 与 review evidence，**When** 用户从节点或 current-step 区域打开它们，**Then** 看到该 run 实际绑定版本、digest、required reviewer、verdict、未闭合 discussion 和检查结果，而不是磁盘上的任意最新文件。

### AC-3
AC-FR1901-03

- **Given** run 分别到达 requirements approval 与 M-LOCK，**When** 打开 gate panel，**Then** 页面明确区分两者，并显示绑定 artifacts/digest、相对上次 human decision 或本次 gate 创建基线的变化、检查与 stale 状态，以及 approve/reject 作用范围。

### AC-4
AC-FR1901-04

- **Given** required program check、Agent review 或 discussion 尚未闭合，**When** 用户查看或直接调用批准动作，**Then** UI 显示具体 blocker，服务端拒绝批准且 gate/revision 不变；条件满足后有效 approve 或带理由 reject 留下身份和证据。

### AC-5
AC-FR1901-05

- **Given** 当前 Agent task 有一个受管 OpenCode session，**When** 用户查看 task controls，**Then** 页面显示 Agent、固化 model、task/session 状态，并且只提供该资源当前允许的 attach、detach、stop-generation、end-session、release-workspace 或 stop-server 动作。

### AC-6
AC-FR1901-06

- **Given** Runtime 事件把 Project 变为 `waiting_for_human`、`blocked`、`failed` 或新 revision，**When** Projects 页面在线接收事件或刷新，**Then** 列表提示与详情从 Runtime 重建为一致状态，断开期间的事件不会因浏览器内存丢失。

### AC-7
AC-FR1901-07

- **Given** 用户在 Web 对 design document 发起、回复、编辑或变更 inline-discussion 状态，**When** 保存返回成功，**Then**落盘文本符合 canonical speaker/depth/status 语法并立即被 gate 使用的 parser 识别为同一 thread；无法 round-trip 的视觉 blockquote 被拒绝并给出可修复错误。

### AC-8
AC-FR1901-08

- **Given** requirements gate 绑定 story/spec/acceptance 或 M-LOCK 还绑定 test-plan/architecture/interfaces，**When** 任一绑定文档含 open/reopen inline-discussion，**Then** gate readiness 聚合并显示该 thread 的文档与锚点且拒绝批准；只有所有绑定 threads resolved 且正文 digest 匹配时才可继续，review guide 中未映射回合同的结论不能冒充 gate evidence。

<a id="ac-fr-2001"></a>
## FR-2001 失败恢复、取消、资源清理与归档

### AC-1
AC-FR2001-01

- **Given** program step、Agent task、external adapter 或恢复扫描失败，**When** 查询 Project 详情和事件，**Then** 显示稳定错误类别、retryability、已知副作用和 definition 允许的 recovery actions，且状态不被误报成功。

### AC-2
AC-FR2001-02

- **Given** 一个可重试幂等失败或副作用结果不确定的失败，**When** 用户请求 retry/resume，**Then** 前者按同一 idempotency contract 安全执行，后者先进入 reconcile/needs-attention 且不会盲目重复副作用。

### AC-3
AC-FR2001-03

- **Given** 非终态 Project 存在未开始或运行中的 tasks，**When** 用户发起取消并确认影响摘要，**Then** Runtime 停止新调度，按声明策略停止或保留当前 task，把 Project 设为 cancelled 终态，并记录 actor、reason 和当时 revision。

### AC-4
AC-FR2001-04

- **Given** Project 已取消、完成或失败终止且仍有受管 session/workspace/server，**When** retention/cleanup 执行或失败后重试，**Then** 每个资源最终状态可观察，清理失败不改写 Project 结果，且事件、artifact digest 与 gate evidence 仍存在。

### AC-5
AC-FR2001-05

- **Given** 一个 cancelled/completed/terminal-failed Project，**When** 用户从历史打开并尝试普通删除或修改，**Then** 内容只读且无物理删除入口，写请求不改变历史；错误创建以 cancelled 记录保留。

<a id="ac-fr-2101"></a>
## FR-2101 可完成的 `new_feature` 与 `bug_fix` Workflow

### AC-1
AC-FR2101-01

- **Given** 用户确认创建 `new_feature`，**When** programmatic foundation preflight 通过并让成功路径完成，**Then** preflight 证据位于业务 graph 之外且未调用 Scout/Warden；绑定 graph 依次覆盖 requirements author/review、requirements approval、test-plan author/review、architecture/interfaces author/review、M-LOCK、traceable implementation、code/authoritative tests、E2E、policy-required security/release、human milestone close 和 history。

### AC-2
AC-FR2101-02

- **Given** 用户用 GitHub Issue 创建 `bug_fix` 且程序验证其链接既有已批准 spec/AC，**When** foundation preflight 通过并让 quick path 完成，**Then** 不新建 requirements 文档或 gate；graph 覆盖 Issue/source-contract 校验、失败复现、M-LOCK、Devon R-G-R、review/authoritative regression、policy release confirmation 和 history。

### AC-3
AC-FR2101-03

- **Given** hotfix 明确不涉及公共接口、数据迁移、安全边界或跨模块设计，**When** decision 执行，**Then** 进入 `quick_rgr` 且 graph 标记 design skipped；任一高影响条件成立时必须先进入 test-plan、architecture/interfaces 及 reviews，再到 M-LOCK，不能由 Agent 建议跳过。

### AC-4
AC-FR2101-04

- **Given** hotfix 影响范围无法由规则确定，**When** Runtime 咨询 Maestro，**Then** 只接受 `quick_rgr`/`design_required` 候选及结构化理由，并在需要确认时等待用户；Maestro 输出本身不改变 run。

### AC-5
AC-FR2101-05

- **Given** `new_feature` 到达 requirements approval/M-LOCK，或有效 hotfix 到达 M-LOCK，**When** 客户端提交 force、waiver、resume 或 Agent 建议试图越过适用 gate，**Then** gate 保持等待；hotfix 只有经 source-contract 校验才可继承旧 requirements approval，且 M-LOCK 仍只能由匹配当前 artifact/revision 的 human approve 推进。

### AC-6
AC-FR2101-06

- **Given** Agent 已回复或代码已生成但任一必需 artifact、review、gate、implementation evidence、authoritative test、security/release policy 或 milestone close 尚未满足，**When** 请求完成 Project，**Then** Runtime 拒绝并列出缺口；全部满足后才转为 completed/history。

<a id="ac-fr-2201"></a>
## FR-2201 需求、实现与验证的端到端追溯门禁

### AC-1
AC-FR2201-01

- **Given** 一个获批新需求 contract 或 hotfix Issue，**When** 查询 trace ledger，**Then** 新需求的每个 FR/NFR/AC 关联 test-plan、task/Issue、code/test evidence；hotfix 从 Issue 反链既有 source spec/AC 并标记实现偏差，两类都显示相应 artifact/commit digest 与状态。

### AC-2
AC-FR2201-02

- **Given** task plan 存在未映射 AC、没有计划验证、重复冲突归属或引用旧 contract，**When** 请求进入 M-DEV，**Then** 程序验证失败并返回具体 FR/AC 缺口，且不派发 Devon task。

### AC-3
AC-FR2201-03

- **Given** 一批已验证实现 tasks，**When** 为 Devon 创建 task manifest，**Then** 只包含该批明确的 Issues/AC、范围与依赖；Agent 对未分配 requirement 的完成声明不会进入 ledger。

### AC-4
AC-FR2201-04

- **Given** Devon 返回实现结果且程序执行权威测试，**When** ledger 接受证据，**Then** code evidence 来自真实 diff/commit，test evidence 包含 runner/command、environment/fixture identity、exit result、覆盖 AC 和被测 revision/digest，而非 Agent 自报文本。

### AC-5
AC-FR2201-05

- **Given** ledger 存在未实现、未验证、失败或 stale 的必需 AC，**When** 请求通过 implementation gate 或 completed 判定，**Then** 请求失败并可从 AC 定位缺失证据；全部闭合时可从任一 task/commit/test 反查需求。

### AC-6
AC-FR2201-06

- **Given** 获批需求或设计发生被接受的变更，**When** Runtime 计算影响，**Then** 受影响的下游 task、code/test evidence 标为 stale 并回到声明 gate，不受影响证据保留但旧绿色状态不能覆盖新 contract。

<a id="ac-fr-2301"></a>
## FR-2301 v0.10/v0.11 Workspace 显式采用与 Legacy 历史

### AC-1
AC-FR2301-01

- **Given** workspace 含 pre-v0.12 `.louke` 且没有 runtime mode 声明，**When** 用户首次运行采用入口，**Then** 先得到只读 migration preview，列出新增、转换、保留、冲突、不支持恢复项以及待选择的 local/global mode；向导推荐 local 但允许明确选择兼容 global，且不会根据 PATH 猜测；未确认时所有旧 metadata/docs/history 字节保持不变。

### AC-2
AC-FR2301-02

- **Given** 用户确认迁移，**When** 执行前后发生可注入失败，**Then** 迁移前有可验证 restore point，失败结果可以回滚或继续修复，且 workspace 不会同时存在两个都被宣称为权威的半提交状态。

### AC-3
AC-FR2301-03

- **Given** 旧 workspace 包含多个 specs/releases/history，**When** 成功采用并打开历史 Projects，**Then** 原文和 Git identity 可从标记为 legacy 的只读条目访问，缺少 native event/gate evidence 的项目不会显示为 v0.12-native completed。

### AC-4
AC-FR2301-04

- **Given** 旧 `project.toml` 声称某 current_stage 或遗留 OpenCode/session 信息，**When** 采用完成，**Then** 系统不自动创建 active run；只有用户显式选择并通过当前 definition/contract 验证的迁移，或新建 run，才产生 v0.12 WorkflowRun。

### AC-5
AC-FR2301-05

- **Given** 迁移尚未提交或已经成功提交，**When** 分别运行旧 pipeline 命令，**Then** 前者仍只操作旧状态，后者对不兼容命令明确拒绝；任何阶段都不会同时写入旧 `current_stage` 与新 Runtime 作为双重事实来源。

<a id="ac-fr-2401"></a>
## FR-2401 项目内 Louke 安装、版本固定与全局回退

### AC-1
AC-FR2401-01

- **Given** 项目 A 声明 local Louke x.y、项目 B 声明 local Louke x.z，且两者的受管 runtime 均有效，**When** 分别从两个项目目录并发启动 server 并执行 workflow/program/Agent tasks，**Then** 每个项目始终报告并使用自己的精确 runtime identity、definitions、prompts/templates、dependencies 和运行数据，任一项目的操作不会改变或污染另一项目。

### AC-2
AC-FR2401-02

- **Given** 一个项目根、其多级子目录和其中另一个嵌套 Louke workspace，且各自声明不同 local 版本，**When** 从这些目录调用受支持的 `lk version` 与 `lk serve` 入口，**Then** 每次都选择最近 workspace 根及其 local runtime，而不是 PATH 中的 global 版本；输出同时显示 effective root、mode、source 和精确 version/build。

### AC-3
AC-FR2401-03

- **Given** 用户在 init-wizard 明确选择 global mode，**When** 启动 workspace，**Then** 使用实际可解析的 global runtime 并显示其 source/version/build；只有兼容性检查通过才允许读写 workflow 状态，global 缺失或不兼容时停在 setup/readiness 并给出修复动作。

### AC-4
AC-FR2401-04

- **Given** workspace 已声明 local x.y，但受管 runtime 分别处于缺失、损坏、实际为 x.z、integrity 失败或 schema 不兼容状态，**When** 调用任意会读取或推进项目的 `lk` 命令，**Then** 每种情况都在状态写入前失败并显示 expected/actual 与安装/修复入口，且不会调用 global Louke 作为后备。

### AC-5
AC-FR2401-05

- **Given** server 已从某 workspace 的有效 local runtime 启动，且系统 PATH/global Louke 随后改变，**When** server 派发程序步骤、OpenCode/Agent task、后台进程或执行恢复，**Then** 所有 task manifest/event 都记录与 server 相同的 executable/interpreter/package identity，并且没有子进程改用新 PATH/global 版本。

### AC-6
AC-FR2401-06

- **Given** setup-only Web 由兼容的 global/bootstrap runtime 启动，**When** 用户在 init-wizard 选择并成功安装 local Louke，**Then** 当前服务明确显示需要切换 runtime，在受控重启且 readiness 证明已运行于该 local identity 前不允许创建/推进 workflow；整个流程不要求另一条初始化或配置 CLI。若用户选择 global mode，则只有兼容性检查通过后才能继续。

### AC-7
AC-FR2401-07

- **Given** A/B 固定不同 local 版本、C 使用 global，且 A 有正在运行的 task，**When** 用户预览并确认升级/修复 A，或另行升级 global，**Then** A 的操作只改变 A；global 操作不改变 A/B 的 pin 或环境；已运行 task 保持启动时 identity，未开始 task 只在服务受控重启后使用 A 的新 identity；注入迁移/安装失败时可恢复到一致旧版本而无半迁移状态。

### AC-8
AC-FR2401-08

- **Given** 仓库包含同名 `lk`、伪造 runtime 目录或被篡改 artifact，**When** 解析、安装或启动 local runtime，**Then** 系统只接受 Louke 管理且 identity/integrity 验证通过的 artifact，不因当前目录或 PATH 顺序执行任意仓库代码；可审阅的 mode/version 声明保留，而受管环境、二进制和下载缓存无需提交版本控制。

<a id="ac-nfr-0001"></a>
## NFR-0001 原子性与崩溃安全

### AC-1
AC-NFR0001-01

- **Given** 可注入中断的持久化测试环境，**When** 分别在 handler 返回前、结果返回后提交前、事务提交后中断，**Then** 恢复结果分别为可重试/需关注、未发生半提交、已提交且不重复副作用。

### AC-2
AC-NFR0001-02

- **Given** 任意成功提交的 revision，**When** 比较 current state 与事件流，**Then** 每个 revision 都有且仅有对应的已提交状态事件。

<a id="ac-nfr-0101"></a>
## NFR-0101 并发一致性

### AC-1
AC-NFR0101-01

- **Given** 两个并发请求使用相同 expected revision，**When** 同时提交，**Then** 恰好一个成功，另一个稳定返回冲突。

### AC-2
AC-NFR0101-02

- **Given** 一个 active 主 Project 与一个 definition 允许并通过校验的 hotfix WorkflowRun，**When** 并发执行各自无冲突步骤，**Then** 两者都能完成且没有共享全局 stage、worktree/session 或证据造成串扰；第二个主 Project 的创建仍被拒绝。

<a id="ac-nfr-0201"></a>
## NFR-0201 可测试性与诚实替身

### AC-1
AC-NFR0201-01

- **Given** 默认 CI 环境没有 GitHub、OpenCode 或模型凭据，**When** 执行本 Spec 的测试，**Then** unit、integration 和 e2e contract 测试可离线完成。

### AC-2
AC-NFR0201-02

- **Given** 某能力只有 stand-in 而无 real adapter，**When** 查询产品 capability 或测试报告，**Then** 该能力明确标记为 stand-in/unsupported，不显示为真实集成完成。

### AC-3
AC-NFR0201-03

- **Given** 任一正式 implementation slice 及最终 v0.12 集成候选，**When** CI 运行，**Then** 每个 slice 的已分配 AC 引用闭合且新增核心模块 statement coverage 不低于 95%，最终候选覆盖本 Spec 全部有效 AC。

<a id="ac-nfr-0301"></a>
## NFR-0301 首次使用到历史归档的产品级 E2E

### AC-1
AC-NFR0301-01

- **Given** 一个干净 Git fixture 和 controllable external adapters，**When** E2E 只通过 `lk serve` 与 Web init-wizard 执行初始化、首位用户、readiness、创建 `new_feature`、两次批准、Agent/program steps、服务重启、完成与历史查看，**Then** golden journey 通过且测试没有预写 Runtime state、运行其他初始化 CLI 或调用内部 Python 对象。

### AC-2
AC-NFR0301-02

- **Given** `new_feature` 与 `bug_fix` definitions，**When** 执行产品 E2E suite，**Then** 前者至少一条完整双 gate 路径，后者至少一条 linked-Issue quick R-G-R 路径和一条 design-required 路径，并分别可观察正确 graph、适用 gates、trace evidence 和历史终态。

### AC-3
AC-NFR0301-03

- **Given** 缺失 model/provider、stale approval、Agent/adapter failure 和用户取消四类 fixture，**When** 运行对应用户流，**Then** 各自呈现规定的 blocked/reapproval/recovery/cleanup 结果，且没有假成功或丢失审计。

### AC-4
AC-NFR0301-04

- **Given** CI 的 contract-compatible stand-ins 和发布前真实 OpenCode 环境，**When** 分别运行 suite 与最小 smoke，**Then** 报告明确标记 stand-in/real，真实 smoke 证明 create、attach、task interaction、detach 和分层 exit；不要求多浏览器矩阵。

### AC-5
AC-NFR0301-05

- **Given** 两个干净 workspace fixture 分别安装并固定不同 local Louke runtime，第三个 fixture 明确选择 global mode，**When** 三者并发完成 init/readiness、启动 server、派发 task、重启并查看历史，**Then** 用户可见信息、child process、manifest、event 和历史证据均显示各自正确 runtime identity，且 suite 证明没有跨 workspace 的 package、definition、prompt、state 或升级污染。

### AC-6
AC-NFR0301-06

- **Given** 一个 active 主 `new_feature` Project、一个通过 source-contract 校验的并行 hotfix 和另一条新需求，**When** 只通过受支持 Web 用户流提交新需求并推进两个现有 run，**Then** 新需求进入 backlog 且不能启动第二个主 Project，hotfix 与主 Project 可以并行完成，同时 UI、events、worktree/session、trace ledger 和终态证据证明两者没有交叉写入或身份污染。

<a id="ac-nfr-0401"></a>
## NFR-0401 Loopback 身份与 Secret 安全

### AC-1
AC-NFR0401-01

- **Given** 用户未配置外部认证/传输保护，**When** 以默认或非 loopback host 启动 Web，**Then** 默认只监听 loopback，非 loopback 请求被拒绝并解释本期不支持的安全前提。

### AC-2
AC-NFR0401-02

- **Given** local human principal 已建立、退出或凭据失效，**When** 检查持久化凭据并尝试批准 gate，**Then** 凭据不是可直接读取的明文，退出/失效 session 不能伪造身份或继续批准。

### AC-3
AC-NFR0401-03

- **Given** external adapters 使用 provider/GitHub/session secrets，**When** 查询 Project artifacts、context manifest、events、logs、error responses 和 E2E artifacts，**Then** 原始 secret 不出现，Agent 只观察到任务所需的受限 capability 或非秘密 identity。

### AC-4
AC-NFR0401-04

- **Given** 批准、取消、模型改绑或资源终止请求带错误身份、run、revision 或重放信息，**When** 服务端验证，**Then** 请求被拒绝且控制面状态、资源与事件不存在部分成功；匹配请求只执行一次。
