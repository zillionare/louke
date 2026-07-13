---
locked: true
locked-at: 2026-07-13
locked-by: Aaron M-LOCK approval (recorded by Codex)
---
# Programmatic Workflow Control — Spec

- **Spec ID**：`v0.12-001-programmatic-workflow-runtime`
- **Created**：2026-07-13
- **Status**：M-LOCK Approved — M-DEV Not Started
- **Priority**：P0

> 本文描述完整的用户需求和行为边界。可观察、可断言的通过条件位于 `acceptance.md`。当前不得以提前形成的 architecture/test-plan/interfaces 草稿反向限制本文；正式设计只能在需求审批门通过后产生。

## User Stories

### US-0001

story: 作为 Louke 使用者，我希望程序而不是 Maestro 掌握工作流状态和合法转移，以便流程不会因 Agent 判断、遗漏或上下文漂移而跳步。
priority: P0

### US-0101

story: 作为 Louke 维护者，我希望工作流定义具有固定版本且每次运行绑定具体版本，以便历史运行可以解释和重放。
priority: P0

### US-0201

story: 作为 Louke 使用者，我希望 foundation 由程序自动检查和幂等修复，以便取消只包装工具调用的 Scout/Warden Agent。
priority: P0

### US-0301

story: 作为需要批准规格的人类，我希望 M-LOCK 绑定我看到的合同版本并由程序强制等待，以便 Agent 无法跳过或复用过期批准。
priority: P0

> **Aaron** [RESOLVED]: 需要分spec 和 M-DEV 之前，分别做两次人类同意（强制）。
>> **Codex**: 已落实为 `new_feature` 的 requirements approval 与 M-LOCK 两个独立、不可 waive/force-skip 的 gate。按后续 D6 决定，hotfix 只有在程序证明其继承既有已批准 spec/AC 时不重复 requirements approval，但仍强制 M-LOCK；若该例外不符合你对本 thread 的原意，请继续回复。
>>> **Aaron**: 好，我批准进入 M-ARCH。

### US-0401

story: 作为 Louke 使用者，我希望工作流在服务重启后恢复到准确状态，以便进度不依赖某个 Agent 会话仍然存在。
priority: P0

### US-0501

story: 作为需求批准者，我希望在 story、spec、acceptance 完成评审后明确批准当前版本，且批准前不能开始 test plan、architecture 或 interfaces，以便设计只建立在被人类认可的需求上。
priority: P0

### US-0601

story: 作为实现批准者，我希望在 test plan、architecture、interfaces 完成并 review 后再次通过 M-LOCK，且批准前不能开始开发，以便实现只建立在完整且被认可的合同上。
priority: P0

### US-0701

story: 作为 Louke 使用者，我希望在 Web sidebar 中管理当前和历史项目并创建新项目，以便从统一入口启动和查看开发工作流。
priority: P0

### US-0801

story: 作为 Louke 使用者，我希望创建项目时输入 story、release version 并选择 new feature 或 bug fix workflow，以便系统从正确流程开始执行。
priority: P0

### US-0901

story: 作为 Louke 使用者，我希望看到当前或历史运行的工作流图和当前位置，以便理解已经完成、正在等待和尚未执行的步骤。
priority: P0

### US-1001

story: 作为 Louke 使用者，我希望在工作流图附近查看 Agent-model 绑定图并通过拖拽修改绑定，以便下一个任务采用我选择的 model。
priority: P0

### US-1101

story: 作为 Louke 使用者，我希望程序管理真实 OpenCode 运行实例、会话生命周期和每步上下文，以便 Agent 工作可以 detach/attach、恢复和审计。
priority: P0

### US-1201

story: 作为 Louke 维护者，我希望确定性工作完全由程序完成，Agent 只执行受约束的语义任务，并能在合法范围内辅助动态选择 workflow 或分支，以便工作流兼具可靠性与适应性。
priority: P0

### US-1301

story: 作为第一次使用 Louke 的本地开发者，我希望通过受支持的初始化/采用流程得到可启动 workspace，并在 Web 中看到身份、依赖和模型就绪状态，以便无需手写 Louke 内部文件就能创建项目。
priority: P0

### US-1401

story: 作为正在推进项目的使用者，我希望项目详情明确显示当前为什么停止、下一步能做什么，以及相关产物、审批、Agent session 和证据，以便工作流图真正可操作。
priority: P0

### US-1501

story: 作为 Louke 使用者，我希望失败、重启、取消和归档都有受控路径，以便我可以纠正错误或退出工作流，同时不丢失历史和审计证据。
priority: P0

### US-1601

story: 作为选择 `new_feature` 或 `bug_fix` 的使用者，我希望两者都是从创建到验证、发布确认和历史归档的完整流程，以便不会进入只能开始却无法完成的演示路径。
priority: P0

### US-1701

story: 作为需求批准者，我希望每个 FR/AC 都能追踪到实现任务、代码证据和权威测试结果，以便项目只有在全部批准需求真实交付后才能完成。
priority: P0

### US-1801

story: 作为现有 Louke workspace 的维护者，我希望采用 v0.12 前先预览迁移并保留回滚与 legacy 历史，以便升级不会猜测旧状态或破坏已有资料。
priority: P0

### US-1901

story: 作为同时维护多个项目的 Louke 使用者，我希望每个项目固定并隔离自己的 Louke 版本，并能明确选择使用项目内或全局安装，以便项目 A 的 x.y 与项目 B 的 x.z 可以并行工作而不互相升级、迁移或串用运行时。
priority: P0

## Usage Scenarios

### scenario-0001 创建并推进运行

调用者选择已注册的 workflow definition。Runtime 创建 WorkflowRun，读取自己的持久化状态并执行当前步骤；调用者不能通过提供 stage 名称改变真实状态。

### scenario-0101 Foundation 前置条件

Runtime 在主流程前调用 `foundation.ensure`。已满足时直接通过；可修复时执行幂等程序；无法自动确定时停止并返回明确阻塞原因。

### scenario-0201 人类批准 M-LOCK

Runtime 创建 challenge 并进入 `waiting_for_human`。由宿主提供的已认证 human principal 批准匹配的 contract hash 后，Runtime 才执行定义中的批准转移。

### scenario-0301 冲突与恢复

两个客户端基于同一 revision 尝试推进时只有一个成功。服务重启后读取同一 WorkflowRun，并从最后一次已提交状态继续。

### scenario-0401 两次人类审批

story/spec/acceptance 评审结束后，Runtime 先等待需求审批；通过后才启动设计任务。test-plan/architecture/interfaces 评审结束后，Runtime 再等待 M-LOCK；通过后才启动 Devon 等实现任务。

### scenario-0501 Web 创建与查看工作流

用户在 Projects 中创建新项目或选择当前/历史项目。创建时提供 story、release version 和 workflow；查看时页面显示 workflow graph、当前位置和 Agent-model bindings。

### scenario-0601 OpenCode 与语义任务

Runtime 为当前步骤创建或恢复 OpenCode session，注入该步骤的 context manifest 和权限；Agent 返回语义产物，Runtime 完成确定性验证、副作用和状态转移。

### scenario-0701 第一次初始化与就绪检查

用户在现有 Git 仓库执行受支持的初始化/采用入口并启动 Web。首次访问建立本地 human principal；readiness 页面逐项显示 workspace、workflow catalog、OpenCode、models/providers 及当前 workflow 所需外部集成，缺失项带修复办法。

### scenario-0801 从项目详情完成当前动作

用户打开项目后看到 current step、停止原因、下一合法动作、artifact/review 状态和近期事件。到达需求审批或 M-LOCK 时，页面展示本次 gate 绑定的文档、digest、变更和自动检查，再接受人类批准或带理由拒绝。

### scenario-0901 失败、取消与归档

步骤失败时页面只提供 definition 允许的 retry、返回上游、人工澄清或取消动作。取消经确认后停止调度并清理受管运行资源，但项目、事件和 gate 证据作为只读历史保留。

### scenario-1001 完整 new feature 与 bug fix

`new_feature` 执行完整需求、设计、实现、验证和发布关闭流程。`bug_fix` 必须先验证 source contract/AC 及其既有 requirements approval，再按声明规则进入 quick R-G-R 或 design-required 分支；它继承既有批准而不创建新的 requirements gate。歧义时可咨询 Maestro，但两个分支都必须经过当前 run 的 M-LOCK 和完成证据门禁。

> **Lex** [RESOLVED]: [BLOCKER] `scenario-1001` 将 `bug_fix` 写成“在需求审批后”且称两个分支都保留 requirements approval，可能被实现为创建新的需求 gate；但 FR-0801、FR-2101 与 AC-FR0801-06/AC-FR2101-02/05 规定有效 hotfix 继承 source contract 的既有批准且不创建新需求 gate。请明确改写为：先验证并继承既有 requirements approval；`quick_rgr` 与 `design_required` 均不新建需求 gate，但两者都必须经过当前 run 的 M-LOCK。
>> **Codex**: 已按既有 D6 决定改写 scenario-1001：先验证并继承 source approval，不创建新 requirements gate；两个分支都强制当前 run 的 M-LOCK 与完成证据。该修改消除矛盾，不改变已确认的 hotfix 产品语义，等待 Lex 复查。

### scenario-1101 需求到交付证据闭环

Runtime 在派发实现任务前生成并验证 FR/AC 覆盖关系。每批 Devon task 只接收分配给它的 Issues/AC；完成时程序把 diff/commit 和权威测试证据回填矩阵，存在未覆盖、失败或 stale 证据时不得关闭项目。

### scenario-1201 显式采用旧 workspace

系统先只读扫描旧 `.louke` 数据并生成迁移预览。用户确认且迁移成功后，旧文档和版本作为 legacy 历史可见；没有可验证新 Runtime 事件的旧 `current_stage` 不会自动变成可恢复 run。

### scenario-1301 项目内 Louke 版本解析与全局回退

项目 A 声明 local Louke x.y，项目 B 声明 local Louke x.z，项目 C 明确选择 global mode。用户从各项目根目录或子目录启动受支持的 `lk` 入口时，Runtime 解析最近的 workspace，并在整个服务和 task 生命周期内固定同一 runtime identity；A/B 互相隔离，C 只有在全局版本通过 workspace 兼容性检查后才启动。已经声明 local 的项目若本地 runtime 不可用，不会悄悄改用全局版本。

## Review Map

这 30 条 FR/NFR 不是 30 个互不相关的功能，而是同一条可用产品旅程的六组合同。评审时建议按组确认目标和边界，再在组内处理 Lex blocker：

| 评审组              | 用户最终得到什么                                                                          | 对应要求                  |
| ------------------- | ----------------------------------------------------------------------------------------- | ------------------------- |
| A. 程序控制面       | 固定、持久、不可跳步且可恢复的 Runtime；Foundation 脱离 Agent                             | FR-0001—FR-0701           |
| B. 两次人类门禁     | 先批准 story/spec/acceptance 才能设计；再 M-LOCK 才能开发                                 | FR-0501、FR-0801、FR-0901 |
| C. 可操作 Web 项目  | 创建/当前/历史、graph、run model override、当前动作与审批 UI                              | FR-1001—FR-1301、FR-1901  |
| D. 受控语义 Agent   | 真实 OpenCode 生命周期、每步 context、程序/Agent 分工和动态分支                           | FR-1401—FR-1701           |
| E. 从首次使用到完成 | 初始化/readiness、失败/取消、两条完整 workflow、证据闭环、旧版本采用、项目级 runtime 隔离 | FR-1801、FR-2001—FR-2401  |
| F. 可交付底线       | 原子性、并发、诚实替身、产品 E2E、loopback 身份与 secret 安全                             | 全部 NFR                  |

## Functional Requirements

<a id="fr-0001"></a>

### FR-0001 版本化工作流定义


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- Workflow definition 必须具有稳定 `definition_id`、不可变 `version`、起始步骤和有限步骤集合。
- 每个步骤必须声明类型、允许的结果和对应转移；definition 中不得包含任意 shell 字符串作为可执行步骤。
- Runtime 必须在启动运行前验证不存在未知步骤、悬空转移、重复 ID、不可达必需步骤或不支持的步骤类型。
- WorkflowRun 创建后必须永久绑定启动时的 definition 版本；后续修改定义不得改变已有运行的语义。
- 验收引用：AC-FR0001-01 至 AC-FR0001-03。

---

<a id="fr-0101"></a>

### FR-0101 Runtime 是状态与转移的唯一写入者


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- WorkflowRun 的当前步骤、状态和 revision 只能由 Runtime 根据绑定定义和当前步骤结果写入。
- 外部调用者不得通过提交 `stage`、`next_step` 或修改持久化文件直接选择下一步。
- 每次状态改变必须同时校验 `run_id`、当前步骤和 `expected_revision`；不匹配时保持原状态并返回冲突。
- 未在当前步骤中声明的结果或转移必须被拒绝，不产生部分写入。
- 验收引用：AC-FR0101-01 至 AC-FR0101-04。

---

<a id="fr-0201"></a>

### FR-0201 持久化 WorkflowRun 与恢复


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- Runtime 必须持久化 run identity、definition identity/version、current step、status、revision、input digest、timestamps 和最近错误。
- 每次被接受的状态改变必须与对应事件在同一事务中提交。
- 服务重启后必须能列出并恢复未完成运行；恢复不得依赖 OpenCode 或 Maestro 的聊天历史。
- 对状态未知或结果不确定的中断步骤，Runtime 必须停在可诊断状态，不得猜测成功并自动越过。
- 验收引用：AC-FR0201-01 至 AC-FR0201-03。

---

<a id="fr-0301"></a>

### FR-0301 注册式程序步骤与幂等执行


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 程序步骤只能引用 Louke 注册表中的 handler 名称；definition 不能注入任意代码或命令。
- Runtime 必须为每次程序步骤尝试生成稳定 idempotency key，并向 handler 提供只读 StepContext。
- handler 必须返回符合声明 schema 的结构化结果；异常、超时或非法输出不得被当作成功。
- 对已经成功提交的同一 idempotency key，恢复或重试不得再次产生外部副作用。
- 验收引用：AC-FR0301-01 至 AC-FR0301-04。

---

<a id="fr-0401"></a>

### FR-0401 Foundation 程序前置条件


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- Runtime 必须通过注册程序步骤 `foundation.ensure` 检查项目进入开发所需的 foundation，而不是启动 Scout 或 Warden Agent。
- foundation 检查必须区分 `satisfied`、`repaired`、`blocked` 和 `failed`；只有前两者允许继续。
- 自动修复操作必须幂等；重复执行不得重复创建本地或远程资源。
- 缺少必须由人类选择的信息时必须返回 `blocked` 及结构化问题，不得由程序臆测。
- foundation 是 workflow 前置条件或条件步骤，不作为必须由 Maestro 推进的业务阶段。
- 验收引用：AC-FR0401-01 至 AC-FR0401-04。

---

<a id="fr-0501"></a>

### FR-0501 通用且不可绕过的人类门禁


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- human gate 必须持久化 `gate_id`、`challenge_id`、`run_id`、step、expected revision、所绑定的 artifact digest、状态和创建时间。
- Runtime 到达需求审批或 M-LOCK 等 gate 时必须进入 `waiting_for_human`，且在收到有效决定前不得执行该 gate 后的步骤。
- 批准者身份必须来自宿主认证上下文，不得接受请求体或 Agent 输出中的自由文本 `approved_by` 作为身份。
- 批准必须同时匹配 challenge、run、当前 step、revision 和 artifact digest；任何一个过期或不匹配都必须拒绝。
- 绑定的 artifact digest 在批准后发生变化时，Runtime 必须使旧批准失效并重新等待新 gate。
- reject 必须保持运行不可继续，并记录人类身份、时间、原因和被拒绝的 artifact digest。
- 验收引用：AC-FR0501-01 至 AC-FR0501-06。

---

<a id="fr-0601"></a>

### FR-0601 事件与证据


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 每次运行创建、步骤开始/结束、阻塞、重试、转移和 gate 决定必须产生 append-only 事件。
- 事件必须包含 run、step、attempt、revision、event type、timestamp、correlation id 和相关输入/输出 digest，不得把秘密或完整认证凭据写入事件。
- Runtime 必须提供按 run 有序读取事件和当前状态的接口，以便 Web、CLI、测试和后续审计使用同一事实来源。
- 验收引用：AC-FR0601-01 至 AC-FR0601-03。

---

<a id="fr-0701"></a>

### FR-0701 新旧流程隔离


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 新 WorkflowRun 不得读取 `project.toml current_stage` 作为自身状态，也不得由现有 `maestro advance --stage` 修改。
- 本期不得删除旧 pipeline；旧命令可继续服务旧运行，但必须与新 Runtime 的存储和 API 明确隔离。
- Runtime 尚未真实接入的 adapter、handler、step capability 或 definition version 必须在校验或执行前明确拒绝，不得以 echo、placeholder 或 `executed=false` 冒充成功；完整 v0.12 交付时，FR-1401 与 FR-1701 要求的 `agent_task`、`decision` 不得仍被列为 unsupported。
- 验收引用：AC-FR0701-01 至 AC-FR0701-03。

---

<a id="fr-0801"></a>

### FR-0801 需求文档人类审批门

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- story、spec、acceptance 完成用户与 Lex 评审后，Runtime 必须创建独立于 M-LOCK 的需求审批 gate，并绑定三份文档的共同 digest。
- 需求审批未通过时，Runtime 不得启动、完成或接受 test-plan、architecture、interfaces 对应的设计任务或产物。
- 人类批准后只允许进入设计阶段，不代表允许进入 M-DEV。
- 三份需求文档中任一份在批准后发生变化时，旧批准必须失效，并在重新评审后再次等待人类批准。
- reject 必须返回 M-SPEC/需求评审状态并保留拒绝原因和证据。
- requirements approval 适用于新增或改变产品行为的 workflow。`bug_fix` 快速路径只有在 GitHub Issue 可追溯到既有已批准 spec/AC、且不改变预期行为时才继承原 requirements approval；无法证明继承关系或实际要求改变行为时，Runtime 必须退出 hotfix 快速路径并转入新的需求流程。
- 验收引用：AC-FR0801-01 至 AC-FR0801-06。

---

<a id="fr-0901"></a>

### FR-0901 设计文档 Review 与 M-LOCK

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 只有需求审批有效时，系统才可以生成和评审 test-plan、architecture、interfaces。
- 三份设计文档完成程序校验、指定 Agent review 和用户 review 后，Runtime 必须创建 M-LOCK gate。
- M-LOCK 必须绑定已批准需求文档及当前设计文档的共同 contract digest。
- M-LOCK 未获得有效人类批准时，不得创建或启动任何实现任务，包括 Devon session、实现 worktree 或实现 commit。
- 绑定文档在批准后、实现开始前发生变化时，旧 M-LOCK 必须失效；变更影响哪个上游阶段由 workflow 规则决定，但不得静默继续开发。
- 验收引用：AC-FR0901-01 至 AC-FR0901-05。

---

<a id="fr-1001"></a>

### FR-1001 Projects 导航与历史项目

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- Web sidebar 必须提供 `Projects` 菜单，其下至少具有“历史项目”和“创建新项目”入口。
- Projects 入口必须让用户访问当前活动项目；历史项目入口必须列出已经结束或归档的项目。
- 每个列表项必须显示足以区分项目或 workflow run 的名称、release version、workflow 类型和状态。
- 首版 UI 中一个 Project 代表当前 workspace/repository 内的一次开发 workflow；非终态且未归档的 Project 属于当前列表，终态或显式归档的 Project 属于历史列表。
- 同一 workspace 同时最多存在一个非 hotfix active Project。已发布产品的 `bug_fix`/hotfix Project 是唯一并行例外，但必须与主 Project 的 run、worktree/branch、session、状态和证据隔离。
- 主 Project 活动期间收到的新需求不得启动另一个主 Project；用户必须能将其保存到 backlog，并在主 Project 结束后带入新的创建确认流程。
- 验收引用：AC-FR1001-01 至 AC-FR1001-05。

以上并发与 backlog 语义已按用户 inline-discussion 写入，并随 2026-07-13 requirements approval 一并确认。

---

<a id="fr-1101"></a>

### FR-1101 创建新项目并选择工作流

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 点击“创建新项目”后，页面必须收集 story、release version 和 workflow 类型；选择 `bug_fix` 时还必须收集或解析 GitHub Issue，并显示其关联的既有已批准 spec/AC。
- 首批明确可选 workflow 只包含 `new_feature` 和 `bug_fix`；其中 `bug_fix` 专指已发布产品相对既有需求的实现错误。提交前必须向用户显示实际选择及 definition version。
- 有效提交必须创建对应的项目或 WorkflowRun，并把用户带到该运行的工作流视图；不得只返回 `workflow_started=true` 而没有真实运行。
- 缺少字段、release version 非法、workflow 不存在或创建发生冲突时，系统必须显示明确错误且不留下半创建运行。
- 首版不直接提供 `spec_change`。backlog 条目可以在主 Project 槽位可用时预填创建表单，但仍须显示完整预览并由用户确认；系统不自动创建或选择 GitHub Project，`bug_fix` 只引用一个已存在的 GitHub Issue。
- 系统必须为 Project 分配不可变 identity，并从 story 生成可区分的初始 display title；不得为了满足列表展示而增加用户未要求的第四个必填字段。
- 创建产生运行副作用前必须显示 story 摘要、release version、workflow id/version 和 readiness 结果供用户确认；确认后的 Project 与首个 WorkflowRun 必须原子创建。
- 主 Project 已活动时，新的 `new_feature` 提交不得创建第二个 active Project，只能保存为 backlog；符合 hotfix 条件的 `bug_fix` 可以在明确展示并行隔离影响后创建。
- `bug_fix` Issue 若不能映射到既有已批准 spec/AC、描述了新行为或缺少可复现预期，创建必须停止并建议进入新需求流程，不得用 hotfix 名义跳过 requirements approval。
- 验收引用：AC-FR1101-01 至 AC-FR1101-07。

以上 catalog、backlog 与 GitHub Issue 边界已按用户 inline-discussion 写入，并随 2026-07-13 requirements approval 一并确认。

---

<a id="fr-1201"></a>

### FR-1201 工作流图与当前位置

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 用户选择当前活动或历史项目后，页面必须显示该运行绑定版本的完整 workflow graph，而不是从当前代码重新推测历史定义。
- 图中必须区分已完成、当前执行、等待人类、阻塞、失败、尚未开始和已跳过的节点，并突出当前或最终位置。
- 当前运行状态变化后，页面必须能够刷新或接收事件而显示新位置，且不得让 UI 自己改变 Runtime 状态。
- 本轮待评审提案：历史 Project 及其 WorkflowRun 完全只读，不允许原地恢复、重跑或 fork；当前非终态 run 的恢复只能沿 workflow 明确声明的边发生。
- 验收引用：AC-FR1201-01 至 AC-FR1201-04。

以上历史运行策略已随 2026-07-13 requirements approval 确认。

---

<a id="fr-1301"></a>

### FR-1301 Agent-model 绑定图与拖拽修改

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 工作流图的上方或下方必须显示 Agent 与当前 model 的绑定关系，并清楚区分默认绑定和用户覆盖。
- 用户必须能通过拖拽把一个可用 model 绑定到目标 Agent；无效或不可用 model 必须被拒绝并保持原绑定。
- 绑定变更不得影响已经开始的 Agent task，只对该 Agent 下一个尚未开始的 task 生效。
- 每次变更必须持久化并记录 actor、Agent、旧 model、新 model、生效边界和时间；重新加载页面后仍可见。
- 本轮待评审提案：拖拽只创建当前 WorkflowRun 的 Agent-model override；未覆盖时使用 Louke Agent 配置中的默认 model；历史 Project 只显示当时绑定，不允许修改。
- 验收引用：AC-FR1301-01 至 AC-FR1301-05。

以上绑定作用域已随 2026-07-13 requirements approval 确认。

---

<a id="fr-1401"></a>

### FR-1401 真实 OpenCode 运行实例与会话生命周期

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- Web 创建的 OpenCode 资源必须对应真实可观察的 server/workspace/session，不能只创建内存 echo 对象。
- 用户关闭或离开 Web client 时必须能 detach，而不自动丢失仍需保留的 server 和 session。
- 用户必须能重新 attach 到仍存在的运行资源并看到对应 session 历史和当前状态，且不同运行不得串线。
- 系统必须区分停止当前生成、结束/删除 session、释放 workspace instance 和终止 server，并向用户暴露与所选动作一致的结果。
- Louke 重启后必须能重新发现或明确标记无法恢复的受管资源，不得把丢失进程显示为 running。
- 验收引用：AC-FR1401-01 至 AC-FR1401-05。

---

<a id="fr-1501"></a>

### FR-1501 每步可定制且可追溯的 Agent 上下文

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 程序必须为每个语义任务生成 context manifest，至少记录 run/step/attempt、Agent、base commit/worktree、输入文档及 digest、允许工具、允许写路径、输出 schema 和禁止副作用。
- Agent session 的上下文必须由稳定项目规则、所选 Agent prompt、当前任务 manifest 和该 session 历史组成，不得隐式依赖 Maestro 主会话记住工作流状态。
- Devon 实现一批 Issues 时，输入必须明确列出 Issues、验收条件、相关设计文档、修改范围、权威测试和完成输出；不相关 Issues 不得无边界混入同一批次。
- Runtime 必须持久化实际使用的 manifest 和 Agent 结果，使同一任务在 session 丢失后能够重建或诊断。
- 对 manifest、base commit 或 contract digest 不匹配的旧 Agent 结果，Runtime 必须拒绝用于当前转移。
- 验收引用：AC-FR1501-01 至 AC-FR1501-05。

---

<a id="fr-1601"></a>

### FR-1601 程序职责与语义 Agent 职责分离

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 相同输入应产生相同结果且规则可枚举的职责必须由程序执行；需要理解、权衡、审查或创造的职责才可以交给 Agent。
- Workflow state、human gate、权威测试结果、Issue/commit/push/tag/publish 等控制面或发布副作用不得由 Agent 直接执行或伪造。
- Agent 可以在任务限定的 worktree 和 allowlist 内使用 read/search/edit/局部 test 获得反馈；程序必须检查最终 diff，并在干净环境权威重跑门禁。
- Scout、Warden、Keeper 等语义核心为空或被迁走的 Agent 必须退出新 workflow；混合 Agent 必须抽离程序职责后只接收结构化 semantic task。
- Agent 输出必须经过 schema、权限、artifact digest 和 allowed transition 验证后才能被 Runtime 接受。
- Louke 必须维护版本化、可审阅的 built-in responsibility inventory，覆盖所有内置 workflow definitions、内置 Agent prompts/tool contracts 与注册程序 handlers 中的每项职责；每项必须有稳定 identity、当前来源、`program`/`semantic`/`mixed` 分类、理由、目标 handler/task 和迁移状态，不允许 `unclassified` 或未登记职责。
- `mixed` 职责必须在 dispatch 前拆成程序控制/副作用与结构化 semantic input/output；catalog 验证和实际 task dispatch 都必须拒绝与 inventory 不一致、仍让 Agent 承担权威副作用或仅包装工具调用的定义。具体 inventory 存储格式由 M-ARCH 决定。
- 验收引用：AC-FR1601-01 至 AC-FR1601-06。

> **Lex** [RESOLVED]: [BLOCKER] FR-1601 的 AC 只能验证已经被挑选为确定性/已程序化的职责，不能发现遗漏，因而无法证明“Agent 中程序化执行的部分完全抽离”。请在需求合同中补充完整且可审阅的 built-in responsibility inventory：覆盖当前 workflow/Agent 的每项职责，标记 program/semantic/mixed 及迁移结果，不允许 unclassified；再增加 AC，验证所有内置 definition 和实际 task dispatch 均与该清单一致，且 mixed 职责的程序副作用已经从 semantic task 中移除。具体存储格式可留给 M-ARCH。
>> **Codex**: 已在 FR-1601 增加完整 inventory、零 unclassified、mixed 分解以及 catalog/dispatch 双重校验，并新增 AC-FR1601-06；存储格式仍留给 M-ARCH。由于这增加了可观察产品合同，FR-1601 暂回 `Decided=⚠️`，等待 Lex 与人类重新批准。

> **Codex** [RESOLVED]: @Aaron Lex 复查现已 PASS。相对你上一次批准，实质新增的是本 FR 的完整 built-in responsibility inventory 与 AC-FR1601-06；另有三处只为消除既有合同矛盾/补足直接断言的修订。请 review 当前 story/spec/acceptance；若同意，请在本 thread 批准当前版本进入 M-ARCH。收到批准后我会把 FR-1601 `Decided` 恢复为 ✅ 并开始正式 design，仍停在 M-LOCK 前等待第二次人类 review。
>> **Aaron:** 批准

---

<a id="fr-1701"></a>

### FR-1701 固定工作流、动态分支与多工作流选择

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 每个 workflow 必须由程序定义有限节点、合法边、门禁和版本；Agent 不能发明节点或直接选择未声明转移。
- 用户在创建时可以显式选择 workflow；程序也可以先用确定性规则分类输入。
- 输入歧义或 workflow 声明的 decision 节点需要语义判断时，程序可以咨询 Maestro，并只接受候选集合内的结构化建议。
- Maestro 建议不得直接产生副作用或改变状态；Runtime 必须验证建议并在需要时要求用户确认。
- 首批 workflow 覆盖 `new_feature` 和 `bug_fix`。程序必须先验证 `bug_fix` 是否为链接既有 contract 的 hotfix，再在 `quick_rgr` 与 `design_required` 候选中选择；无法映射既有需求时不得继续 hotfix，而应进入 backlog/新需求流程。
- 主 Project active 时，程序必须把新的 requirement 路由到 backlog，而不是创建第二个主 run；已发布产品 hotfix 是 definition 明确允许的并行例外。
- 验收引用：AC-FR1701-01 至 AC-FR1701-05。

---

<a id="fr-1801"></a>

### FR-1801 Workspace 初始化、首位用户与就绪检查

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- `lk serve` 必须能在一个尚无 Louke metadata 的现有 Git repository 上启动 setup-only Web，而不是因缺少 `project.toml` 退出；首次访问必须进入幂等 init-wizard，由向导创建新 Runtime 所需的最低元数据、存储和内置 workflow catalog。
- init-wizard 不得覆盖用户已有源文件或未确认迁移的 `.louke` 内容；重复进入必须报告 already-ready、可修复缺口或冲突，而不是复制一套平行状态。
- init-wizard 必须引导建立首位 loopback local human principal；后续 gate 决定必须使用已认证会话中的该身份，未建立身份时只能完成 setup/readiness，不能批准。
- 系统必须提供可观察 readiness，至少覆盖 workspace/Git、Runtime store、workflow catalog、OpenCode、可用 model/provider，以及所选 workflow 当前步骤必需的 GitHub 或其他外部能力。
- 某个外部能力缺失时，不依赖它的只读页面仍可使用；需要它的创建或步骤必须进入 `blocked`/degraded 状态并给出不泄露 secret 的检查结果和可执行修复说明。
- 除启动 `lk serve` 外，初始化、采用、Louke 配置和 OpenCode/model/provider readiness 不得要求另一条 Louke CLI；init-wizard 必须在 Web 内完成可由 Louke 完成的配置、授权或重新检测，并对操作系统级前置依赖提供可理解且不以手写内部文件为前提的修复动作。
- 验收引用：AC-FR1801-01 至 AC-FR1801-06。

---

<a id="fr-1901"></a>

### FR-1901 可操作的 Project 详情、Artifact Review 与审批 UI

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- Project 详情除 workflow graph 外，必须显示 run status/revision、current step、进入该状态的原因、阻塞/失败诊断和 definition 当前允许的下一动作；不得只用颜色要求用户猜测下一步。
- 页面必须能从对应节点或 current-step 区域打开该 run 的输入/输出 artifacts、实际 digest、required reviewer、review verdict、未闭合 discussion 和自动校验结果；历史版本不得被最新文件替换。
- requirements approval 与 M-LOCK 到达时，页面必须显示 gate 类型、绑定 artifacts、digest、相对上次已看版本的变化、检查状态和 stale 状态，并提供 approve 或带理由 reject；两种 gate 的文案和效果必须可区分。
- 自动校验、指定 Agent review 或 unresolved discussion 尚未满足时，UI 必须解释为什么不能批准，Runtime 也必须在服务端拒绝绕过页面的批准请求。
- 对当前 Agent task，页面必须显示 Agent、固化 model、task/session 状态及允许的 attach、detach、stop-generation 或退出动作；这些动作必须服从 FR-1401 的资源层级语义。
- Projects 列表和详情必须随 Runtime 事件更新，并突出 `waiting_for_human`、`blocked`、`failed` 等需要用户动作的项目；刷新后从事实来源重建，不依赖浏览器内存。
- Web 对 design documents 发起、回复、编辑或变更状态的 inline-discussion，必须写出 canonical 协议格式，并在返回成功前通过与 gate 相同的 parser round-trip；视觉上像 blockquote 但 `lk discuss query` 无法识别的内容必须视为保存失败并给出修复提示。
- requirements approval 必须聚合 story/spec/acceptance 中的 inline-discussion，M-LOCK 必须再聚合 test-plan/architecture/interfaces；任一绑定文档存在 open/reopen thread 时 gate 不得批准，并须显示原文锚点。非合同性质的 review guide 只用于导航，其结论必须映射回绑定文档才可改变 gate 状态。
- 验收引用：AC-FR1901-01 至 AC-FR1901-08。

---

<a id="fr-2001"></a>

### FR-2001 失败恢复、取消、资源清理与归档

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- program step、Agent task、external adapter 或恢复扫描失败时，Runtime 必须记录稳定错误类别、是否可重试、已知副作用和 definition 允许的 recovery actions；不得把“重新加载页面”当作恢复机制。
- retry/resume 只能由 Runtime 在 definition 声明且幂等条件满足时执行；结果不确定的副作用必须先进入 needs-attention/reconcile，不得盲目重放。
- 用户必须能对非终态 Project 发起带摘要和影响提示的取消确认；确认后 Runtime 停止新任务调度，按策略停止/保留当前 Agent task，并将 Project 变为可审计终态。
- 取消、完成或失败终止后的受管 session/workspace/server 必须按声明保留期清理或标为待清理；清理失败可重试且不改变 Project 的事实结果，清理动作不得删除事件、artifact digest 或 gate 证据。
- 终态/归档 Project 在历史中只读可见；首版不提供物理删除历史的普通 UI，错误创建通过取消而不是抹除记录处理。
- 验收引用：AC-FR2001-01 至 AC-FR2001-05。

---

<a id="fr-2101"></a>

### FR-2101 可完成的 `new_feature` 与 `bug_fix` Workflow

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 启动任一内置 workflow 前，程序必须先完成 foundation preflight 并保留结果；它不是 Maestro 业务 stage，也不需要 Scout/Warden Agent。内置 `new_feature` 的业务 graph 必须至少包含：story/spec/acceptance 语义生成与 Lex review loop；requirements approval；test-plan 生成与 review；architecture/interfaces 生成与 review；M-LOCK；可追溯实现任务；代码 review 与权威 unit/integration gate；E2E gate；按项目 policy 执行 security/release；人类确认 milestone close；历史归档。
- 内置 `bug_fix` 专指已发布产品相对既有已批准 spec/AC 的实现错误。它必须从已存在的 GitHub Issue 启动，并由程序验证 source contract、目标发布版本和可复现偏差；它继承原 requirements approval，不新建 story/spec/acceptance，也不重复需求审批。
- quick hotfix graph 必须至少包含：GitHub Issue/source-contract 校验；失败复现；M-LOCK；Devon R-G-R；代码 review/权威回归门禁；按 policy 发布确认与归档。涉及公共接口、数据迁移、安全边界或跨模块设计时，必须在 M-LOCK 前进入 test-plan、architecture/interfaces 及 review；规则不能确定时，Maestro 只可在 `quick_rgr`/`design_required` 候选中建议。
- `new_feature` 的 requirements approval 与 M-LOCK 都不可 waive/force-skip；`bug_fix` 只有在验证继承既有 requirements approval 后才能省略新的需求 gate，但 M-LOCK 仍不可 waive/force-skip。Issue 实际提出新行为、需求含糊或无法映射 source AC 时必须退出 hotfix 并进入 backlog/新需求流程。
- workflow 中每个程序校验、Agent review、失败返工、可选安全步骤和 milestone close 都必须是 definition 中的显式节点/边或 policy 结果；UI 与历史图必须准确显示实际走过和跳过的路径。
- Project 只有在全部必需 artifact、review、gate、implementation evidence、authoritative tests 和 release/close policy 满足后才能成为 `completed`；“Agent 已回复”或“代码已生成”不得作为 workflow 终点。
- 验收引用：AC-FR2101-01 至 AC-FR2101-06。

---

<a id="fr-2201"></a>

### FR-2201 需求、实现与验证的端到端追溯门禁

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- Runtime 必须为每个获批 contract 维护机器可验证的 trace ledger，把每个 FR/NFR 与其 AC、test-plan case、实现 task/Issue、代码 evidence 和权威 test result 关联起来，并保留各自 artifact/commit digest。
- hotfix trace ledger 必须从 GitHub Issue 反向链接到既有已批准 source spec/AC，并区分“修复实现偏差”与“提出新需求”；不能建立该链接时不得进入 quick R-G-R。
- 在派发实现任务前，程序必须验证所有应实现 AC 至少映射到一个实现 task 和一个计划中的权威验证；重复、冲突或未覆盖项必须阻止 M-DEV 启动并返回可定位缺口。
- Devon 批次必须来自已验证 task 集合，context manifest 只包含该批 Issues/AC 和允许范围；Agent 不得自行把未分配需求标记完成或合并进批次。
- 接受实现结果时，程序必须依据真实 diff/commit 与 task 输出回填代码 evidence；接受测试结果时必须记录所执行命令/runner、环境或 fixture identity、exit result、覆盖 AC 和被测 revision/digest。
- `completed` 判定必须由程序检查 ledger 中没有未实现、未验证、失败或 stale 的必需 AC；UI 必须能从 FR/AC 正向查看证据，也能从 task/commit/test 反向找到需求。
- 获批需求或设计发生有效变更时，Runtime 必须按影响关系使下游 task、代码或测试证据标记 stale，并返回相应 gate；不得通过保留旧绿色结果继续完成。
- 验收引用：AC-FR2201-01 至 AC-FR2201-06。

---

<a id="fr-2301"></a>

### FR-2301 v0.10/v0.11 Workspace 显式采用与 Legacy 历史

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 初始化入口检测到 pre-v0.12 `.louke` 时，必须先执行只读扫描并展示将新增、转换、保留、冲突和不支持恢复的项目；在用户确认前不得改写旧 metadata、design docs 或历史。
- 迁移执行前必须创建可验证备份/恢复点；任何一步失败时不得留下同时宣称新旧状态权威的半迁移 workspace，并必须给出回滚或继续修复路径。
- 已有 spec/release/history 必须可作为明确标记的 legacy Project 在历史列表查看，其原文与 Git identity 保留；不能把缺失新 Runtime event/gate 证据的历史显示成 v0.12-native completed。
- 旧 `project.toml current_stage`、Maestro session 或 OpenCode 内存 instance 不得自动转成 active WorkflowRun；恢复旧进行中工作必须由用户显式选择迁移方案，并通过当前 definition/contract 验证或新建 run。
- 新 Runtime 存储和命令必须与仍保留的旧 pipeline 状态隔离；迁移成功前旧命令仍按原数据工作，迁移成功后的不兼容命令必须明确拒绝而不是双写。
- pre-v0.12 workspace 没有 runtime mode 声明时，采用预览必须把它标记为待选择项；init-wizard 推荐 local，但允许用户明确保留兼容的 global mode。系统不得仅凭当时 PATH 中存在某个 `lk` 就猜测或永久记录安装模式。
- 验收引用：AC-FR2301-01 至 AC-FR2301-05。

---

<a id="fr-2401"></a>

### FR-2401 项目内 Louke 安装、版本固定与全局回退

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

> **Aaron** [RESOLVED]: 在开发项目 A 时，使用了 Louke x.y；还没完成，又进入项目 B，要求使用 Louke x.z。目前 `lk` 只支持全局安装。要求改为项目内安装，从项目目录下启动；如果用户不希望在项目内安装，则也允许回退到全局。
>> **Codex**: 已整理为“local mode 优先、global mode 显式选择”：新项目推荐项目内安装并固定精确 runtime identity；从项目目录或子目录启动时解析最近的 workspace。若项目已经声明 local，但本地安装缺失、损坏或版本不符，则 fail closed 并进入修复，不静默换成全局版本；只有用户明确选择 global mode 时才使用全局安装。首次由全局/bootstrap runtime 打开 init-wizard 并完成 local 安装后，需要受控重启到 local runtime，不能在同一服务进程中热切版本。具体 launcher 与环境目录留给 architecture。请确认这是否准确表达“允许回退到全局”的边界。
>>> **Aaron**: 好，我批准进入 M-ARCH。

- 每个 workspace 必须持久化、可审阅地声明 Louke 安装模式（`local` 或 `global`）和期望的精确版本/不可变 build identity；新项目的 init-wizard 必须推荐 `local`，只有用户主动选择不做项目内安装时才记录 `global`。
- 从 workspace 根目录或任意子目录调用受支持的 `lk` 入口时，解析器必须选择最近的 Louke workspace。`local` mode 必须使用该 workspace 的受管项目内 runtime，不受 PATH 中全局 Louke 版本影响；嵌套 workspace 必须以最近根为准。
- 不同 workspace 的 local runtime、Python/package dependencies、Louke workflow definitions、Agent prompts/templates 和可变运行数据必须相互隔离；项目 A 的 x.y 与项目 B 的 x.z 必须能够同时运行 server 和 tasks，不因任一项目安装、升级、修复或退出而串用或改变另一项目。
- workspace 已声明 `local` 但受管 runtime 缺失、损坏、identity 不符或与 workspace schema 不兼容时，必须在改变 workflow/project 状态前失败，显示期望值、实际值和可执行的安装/修复入口；不得静默回退到 global runtime。
- `global` mode 只能使用当前可解析的全局 Louke；启动前必须校验实际版本/build 与 workspace schema/contract 的兼容性。全局 runtime 缺失或不兼容时必须停在 setup/readiness，并且不改写项目状态。
- CLI 版本信息、Web setup/readiness、run/task manifest 和审计事件必须显示 effective workspace root、安装模式、runtime 来源、精确版本/build 与兼容性结果，使用户和测试能够证明实际执行的 Louke，而非只看到声明值。
- server 启动时必须固定 effective runtime identity；由它派生的程序步骤、OpenCode/Agent tasks、后台进程和恢复操作必须使用同一 executable/interpreter/package identity。init-wizard 安装 local runtime 或已运行服务期间发生升级后，必须要求受控重启，不能让未开始 task 在同一进程中热切到新版本。
- 安装、升级或修复 local runtime 只能改变当前 workspace；全局升级不得改写任何 local pin，另一项目的 local 操作也不得改变本项目。版本变更必须预览兼容性/迁移影响、经用户确认并提供失败恢复；受管 runtime 只能执行 Louke 管理且 identity/integrity 可验证的 artifact，不得因仓库中存在同名可执行文件而运行任意代码。项目声明应可纳入版本控制，受管环境、二进制和下载缓存不要求提交。
- 验收引用：AC-FR2401-01 至 AC-FR2401-08。

## Non-Functional Requirements

<a id="nfr-0001"></a>

### NFR-0001 原子性与崩溃安全


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 状态与事件提交必须具备事务原子性；测试必须覆盖在 handler 返回前、返回后提交前和提交后发生中断的情况。
- Runtime 不得因为部分写入而显示一个不存在对应事件的状态，或存在事件但状态未改变。
- 验收引用：AC-NFR0001-01 至 AC-NFR0001-02。

---

<a id="nfr-0101"></a>

### NFR-0101 并发一致性


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 同一 run 的状态写入必须使用乐观并发控制或等价机制；两个竞争写入最多一个成功。
- Runtime 不得以共享全局 `current_stage` 串写 run；首版实际允许的并发组合是一个 active 主 Project 加上经校验的 hotfix Project，第二个主 Project 必须在创建门被拒绝并进入 backlog。
- 验收引用：AC-NFR0101-01 至 AC-NFR0101-02。

---

<a id="nfr-0201"></a>

### NFR-0201 可测试性与诚实替身


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- CI 默认测试不得依赖真实 GitHub、OpenCode 或模型服务；外部依赖必须通过与真实接口相同的 controllable adapter 替代。
- stand-in 的成功不能作为真实集成已经完成的证据；未接入的能力必须在产品状态和测试名称中明确标记。
- 每个正式 implementation slice 的新增核心模块单元测试覆盖率必须不低于 95%；最终 v0.12 产品验收必须覆盖本 Spec 的全部 acceptance criteria。
- 验收引用：AC-NFR0201-01 至 AC-NFR0201-03。

---

<a id="nfr-0301"></a>

### NFR-0301 首次使用到历史归档的产品级 E2E

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 必须存在从干净 Git fixture 启动 `lk serve`、通过 Web init-wizard 初始化/创建首位本地用户、readiness、创建 `new_feature` Project、两次人类 gate、受控 Agent/program steps、重启恢复、完成到历史查看的产品级 E2E；不得预写内部 Runtime 状态、运行其他初始化 CLI 或直接调用内部 Python 对象。
- `new_feature` 至少有一条完整双 gate 路径；`bug_fix` 至少各有一条 linked-Issue quick R-G-R 与 design-required 路径。此外至少覆盖 active 主 Project 时新需求进入 backlog、hotfix 并行隔离、缺失 model/provider 阻塞、stale approval、Agent/adapter 失败恢复和取消清理。
- E2E 可以使用与真实边界同契约的 controllable OpenCode/GitHub/model adapters，但测试报告与产品 capability 必须明确区分 stand-in 与真实 smoke；发布 v0.12 前必须有真实 OpenCode 最小 smoke 证明 create/attach/task/detach/exit 契约未漂移。
- 本 requirement 不建立多浏览器兼容矩阵；一个受支持浏览器负责验证真实用户流，领域/API contract 测试负责其余确定性行为。
- E2E 必须覆盖两个 workspace 分别固定不同 local Louke 版本并发运行，以及第三个 workspace 明确使用 global mode；必须断言 server、子进程、workflow/task manifest 和历史证据的 runtime identity 没有跨项目污染。
- 验收引用：AC-NFR0301-01 至 AC-NFR0301-06。

> **Lex** [RESOLVED]: [BLOCKER] `verify-acceptance` 的 142/142 只证明 section 存在，不证明每个规范性子条款被断言。当前至少缺少：FR-0001 的 duplicate-ID/unreachable-required-step；FR-0601 的 blocked/retry 事件及完整 event schema；NFR-0301 的 backlog 与并行 hotfix 产品 E2E。请扩充现有 AC 或新增 AC，使这些条件具有直接可观察的 Given/When/Then；否则应收窄对应 requirement，不能留给 test plan 自行发明通过条件。
>> **Codex**: 已扩充 AC-FR0001-01 与 AC-FR0601-01，并新增 AC-NFR0301-06，直接覆盖 Lex 指出的全部规范性子条款；结构总数将由 Louke validator 重新计算，等待 Lex 复查语义闭合。

---

<a id="nfr-0401"></a>

### NFR-0401 Loopback 身份与 Secret 安全

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- Web 默认只能绑定 loopback；若操作者选择非 loopback 地址，系统必须拒绝启动或要求已配置的外部认证/传输保护，本期不把公网部署视为可支持能力。
- local human principal 的凭据不得以可直接读取的明文保存；session 必须防止客户端伪造身份，退出或凭据失效后不能继续批准 gate。
- provider token、GitHub credential、session secret 和其他 secret 不得出现在 Project artifacts、Agent context、events、普通日志、错误响应或 E2E artifact；Agent 只获得任务所需的受限能力而非原始 secret。
- 所有批准、取消、模型改绑和资源终止等改变控制面的 Web 请求必须验证认证身份、目标 run/revision 与防重放信息；失败不得产生部分状态改变。
- 验收引用：AC-NFR0401-01 至 AC-NFR0401-04。

## Clarification Log

### 2026-07-13 — 待用户与 Lex 逐项评审的初始提案

- 程序而非 Maestro 是工作流状态权威。
- M-FOUNDATION 应程序化，并退出 Maestro 主流程。
- 需求文档审批和 M-LOCK 是两个不同且都不可跳过的人类门禁。
- Web Projects、工作流图、Agent-model 绑定、OpenCode 生命周期与动态路由都属于完整目标；正式切片只能在需求锁定和 M-ARCH 后确定。

以上方向已获用户原则同意，但各 FR/NFR 的具体边界尚未逐项评审，因此 Decided 保持 ⚠️。

### 2026-07-13 — 用户已确认的流程决定

1. 暂停 v0.11-002；v0.12-001 在 M-SPEC 评审完成后成为下一 active spec。
2. 首版 human gate 接受 loopback 本地 Web 会话身份；是否需要更强账户认证由后续部署范围另行提出。
3. 严格遵循 Louke v0.10 顺序：先由用户与 Lex 评审 story/spec/acceptance；锁定需求后再设计 test-plan、architecture 和 interfaces；设计再次经用户 review 后才进入开发。

### 2026-07-13 — 本轮新增、尚待逐项批准的用户界面与门禁要求

1. 在 M-LOCK 之前增加独立的需求审批 gate；人类批准 story/spec/acceptance 后，才允许开始 test-plan、architecture、interfaces。
2. Web sidebar 增加 Projects，并提供当前项目、历史项目和创建新项目入口。
3. 创建页收集 story、release version 和 workflow；当前明确候选为 `new_feature` 与 `bug_fix`。
4. 项目详情显示绑定版本的 workflow graph、当前位置及 Agent-model 绑定；拖拽修改只对下一个尚未开始的 Agent task 生效。
5. Project 精确定义、首版 workflow catalog、历史运行策略和 model override 作用域已写成可评审提案，但尚未获得用户逐项同意，因此相关 `Decided` 保持 ⚠️。

### 2026-07-13 — 用户要求按端到端可用产品补全隐含需求

1. 需求不能只逐句转写用户明确提出的功能；必须检查从首次初始化到完成/历史是否存在无法操作的断点。
2. 代码扫描确认当前存在 server-ready 初始化、六个 sub-app 组装、真实 OpenCode、run/gate UI 和失败收尾等缺口；证据记录于 `exploration/product-journey-audit.md`。
3. 本 Spec 因而新增 initialization/readiness、可操作 project detail、recovery/cancel/archive、完整 `new_feature`/`bug_fix`、trace ledger、legacy migration、product E2E 与 local secret security。
4. 这些是“首个可用闭环”的候选合同，不是 architecture 方案；所有新增 FR/NFR 仍保持 `Decided=⚠️`，等待 Lex 与用户 review。

### 2026-07-13 — 用户通过 inline-discussion 回复 D1—D8

1. 同一 workspace 只允许一个 active 主 Project；已发布产品 hotfix 是并行例外；主项目期间的新需求进入 backlog。
2. `lk serve` 后首次打开 Web 运行 init-wizard；不使用额外初始化 CLI。
3. `bug_fix` 专指已有发布产品偏离既有 spec/AC 的实现错误：GitHub Issue 必需，支持快速 R-G-R；需要 architecture 时走完整设计流程；它不重新产生 requirements。
4. 用户同意其余提案：首版 catalog、历史只读、run-scoped model override、human milestone close、显式 legacy migration。
5. 正文与 AC 已按上述决定更新，并在原 threads 下回复映射；由 initiator 检查后标记 resolved，相关 `Decided` 在 thread 闭环前不提前改为 ✅。

### 2026-07-13 — 新增项目内安装与版本隔离需求

1. 用户要求项目 A 与项目 B 能分别固定 Louke x.y/x.z，并从各自项目目录启动；不希望项目内安装时允许使用全局 Louke。
2. 当前候选合同将其解释为显式 `local`/`global` mode：local 优先且 fail closed，global 只在用户主动选择后使用；该解释已锚定在 FR-2401 的 inline discussion，等待 initiator 确认。
3. launcher、受管环境目录和包管理工具属于后续 architecture；M-SPEC 只锁定可观察的解析、隔离、升级、重启、安全与证据行为。

### 2026-07-13 — 人类批准进入 M-ARCH

1. Aaron 明确回复“好，我批准进入 M-ARCH”，批准当前 story/spec/acceptance，包括 FR-2401 对 global fallback 的显式模式解释。
2. 两个由 Aaron 发起的 inline threads 已据此标记 `[RESOLVED]`；本次记录只改变评审状态与审计文字，没有改变获批的 requirement/AC 行为合同。
3. Lex 语义评审仍是进入正式设计前的独立门禁；若 Lex 提出导致合同正文变化的 blocker，变更后必须重新取得人类批准。
4. 本次批准将全部 30 条 FR/NFR 的 `Decided` 更新为 ✅；Clarification Log 中早期“尚待批准”的段落保留为当时状态的历史记录，不代表当前状态。

### 2026-07-13 — Lex Stage 1 语义复查退回

1. OpenCode Maestro 成功创建 Lex subtask，但 Lex 连续返回空 body；该结果明确记录为 `[LEX STAGE1 FAILED]`，没有伪装成通过。
2. 随后使用隔离 reviewer 按仓库 `Lex.md` Stage 1 rubric 做只读复查，得到 `[LEX STAGE1 REJECT]`：hotfix approval 场景矛盾、FR-1601 无法证明零遗漏、若干规范性子条款缺少直接 AC。
3. 三项 blocker 已作为 Lex inline threads 锚定到对应上下文，正文和 acceptance 已进入修订；因此 2026-07-13 的人类批准 digest 失效，状态回到 `Human Reapproval Required`，不得开始正式 M-ARCH 文档。

### 2026-07-13 — 修订后 requirements approval

1. Aaron 明确回复“批准”，批准含 FR-1601 built-in responsibility inventory 与 144 条 AC 的修订后 story/spec/acceptance。
2. Codex 发起的 reapproval thread 已由 initiator 标记 `[RESOLVED]`，FR-1601 `Decided` 恢复为 ✅；Lex re-review 已 PASS。
3. requirements approval 已闭合，正式进入 M-ARCH；此时只允许产生 test-plan、architecture、interfaces 与其 review 产物，禁止实现代码，直到第二次人类 M-LOCK approval。
