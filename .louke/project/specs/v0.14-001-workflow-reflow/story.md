# STR-1401: v0.14 Workflow Reflow — 生产工作流统一

---

| Story ID | 创建时间 | 分流结论 |
| :--- | :--- | :--- |
| STR-1401 | 2026-07-17T00:00:00+08:00 | Go（Agent 建议） |

---

## 0. 原始输入

> 把 v0.12 Runtime 核心、v0.13 Web/Chat、v0.13.1 安装和质量门整合为唯一生产工作流，并增加首版可靠但简单的 return-upstream、bounded waiver、no-new-debt adoption 和内置 lifecycle hooks。

---

## 0.1 已确认约束（来自后续讨论，非用户逐字原话）

Scribe 在 Story 推进过程中通过 inline-discussion 与 initiator 反复确认了下列约束，作为 §0 原始输入的产品边界补充。这些约束本身**不是**用户最早提出的字面设想，但是 v0.14 Story 必须服从的硬条件：

1. **Runtime 权威控制**：Runtime 是 workflow 状态、合法转移和权威副作用的唯一控制者；Web/CLI/Chat/Agent 不能伪造 program result、pass、approval 或 next step。
2. **三层职责划分**：program 自动执行确定性检查和副作用；semantic Agent 负责理解、分析、设计、代码/测试内容生成、评审；Human 决定产品、价值、风险、requirements approval、M-LOCK、waiver、adoption 和 release。
3. **3-piece 整合目标**：从 v0.12 核心类库、v0.13 观察面、v0.13.1 安装/质量门到一条完整可完成的 `new_feature` 和 `bug_fix` 生产旅程，并通过 installed-wheel E2E 和 Louke dogfood 证明。
4. **Scribe/Sage 职责切分**：Scribe 产出完整 canonical Story；Sage 在 M-SPEC 不重复 Story discovery，也不在 Spec 中改写 User Stories。
5. **Sage 交互策略**：Sage 不要求在 M-SPEC 开头使用 `question`；默认 draft-first + 锚定 inline discussion 澄清；`question` 仅在无法形成文档锚点或必须立即取得产品决定时作为例外通道。
6. **Runtime 拥有 M-SPEC 主循环**：Runtime 负责 artifact revision/digest/diff、结构验证、讨论扫描与等待、锚点、Git/GitHub Issue reconcile、requirements approval/lock、重启恢复；Sage/Lex 每次只完成一轮语义任务，不调用 workflow/gate 工具。
7. **Spec 规模硬门禁**：单个 Spec 最多 30 条有效 FR+NFR（`Valid=❌` 不计入），恰好 30 条允许；>30 条不可 waive。硬门禁作用域是单个 Spec，不累计同一 release 的多个 Spec。
8. **超限处理**：Runtime 在 Sage 初稿/修订持久化后、dispatch Lex 前执行 30-count 检查；超限返回稳定错误 `SPEC_SCOPE_TOO_LARGE` 并进入 `needs_story_split`，合法返回 M-STORY。Runtime 不自动决定拆分边界；Scribe 提案、Human 决策。原 Story/Spec/Acceptance revision 完整保留；确认后原 Story 标记为 Split parent，子 Story 记录 `parent_story_id` 并进入后续独立 release/run。
9. **M-TESTPLAN 评审分工**：M-TESTPLAN author 是 Archer；独立技术 reviewer 是 S 档 Prism；Shield 可提供下游可执行性反馈但不批准；Sage 不再承担 Test Plan 评审（Sage 是 S 档需求分析 reviewer）。
10. **过渡期入口策略**：v0.14 在 v0.13 基础上开发，发布前 CLI 与 Web Chat **并行可用**；v0.14 release tag 当日切换为 Web Chat 唯一开发入口，CLI 退化为 `lk serve` / `lk upgrade` 等少数运维命令。该切换由 Runtime 在 release cutover 阶段统一收敛。**cutover 后，旧 workflow CLI 命令（如 `lk agent ...` 等曾用于推进 workflow 的命令）必须以 deprecated no-op 方式接受：解析成功、不报错、不静默调用旧 Runtime / 旧 Agent、不 mutate run 或 project 状态、不产生外部副作用，但必须输出引导用户改用 Web Chat 的 actionable 警告，并向 audit log 写入可追溯事件。**（Human Go 决策约束，详见 BS-30）

> **Aaron [RESOLVED]:** v0.14发布后，CLI 模式将只允许少数运维相关命令如`lk upgrade`, `lk serve`。核心开发流程只能通过 Chat (基于 web page，以下称 Web Chat)来完成。
>> **Scribe:** 已按此约束更新用户终端、产品入口、功能描述、北极星目标、Happy Path、BS-01 和 BS-15：**v0.14 发布后**核心开发唯一入口为 Web Chat；CLI 仅保留 lk serve、lk upgrade 等少数运维命令；API 仅为内部 program boundary。同时在 1.2/1.3/3.4 增加过渡期说明：**v0.14 在 v0.13 基础上开发期间** CLI 与 Web Chat 并存，CLI 继续提供 v0.13 风格的 workflow 推进以便 dogfood 与调试；release tag 当日切换为 Web Chat 唯一入口。请 initiator 确认后关闭本讨论。
>
> **Aaron [RESOLVED — post-Go]:** cutover 当日，旧 CLI workflow 命令（如 `lk agent ...`）不能再"悄悄还能跑"。它们必须被接受为 deprecated no-op：不执行 workflow、不调用旧 Runtime / 旧 Agent、不 mutate run 或 project 状态、不报硬错；要输出引导用户改用 Web Chat 的 actionable 警告，并向 audit log 写入可追溯事件。
>> **Scribe:** 已固化为 BS-30，并在 §0.1 第 10 条约束、§1.3 入口收敛段落、§3.3 组织约束、§7 Human 确认处同步收敛；任何旧命令必须可被审计（事件含调用命令名、是否触发实际副作用 = false）。请 initiator 确认后关闭本讨论。

---

## 1. 用户与场景 (Who & Where)

### 1.1 用户画像 (Who)

- **主要角色**：使用 Louke 开发项目的产品负责人兼技术维护者。该角色既是需求的提出者（决定 Go/Park/No-Go、批准 requirements、M-LOCK、waiver、adoption），也是技术方案的参与者（可参与技术 review、暂停 reviewer、提出 constraint）。
- **次要角色**：Louke 自身的发布维护者（负责验证 installed-wheel E2E、dogfood 全流程、执行受控回退）。
- **用户规模**：单一用户（本地桌面应用，无多用户协作）。
- **使用频次**：高频（每日）。该角色在推进功能或修复缺陷时持续与 workflow 交互。
- **网络环境**：稳定办公网络。离线场景下可本地操作，但 Git push、外部 API 调用等需要网络。

### 1.2 使用终端 (Where)

- **终端类型**：Web（桌面浏览器）。**v0.14 发布后**的核心开发流程唯一入口为 Web Chat（基于 Web 页面的 Chat tab）；CLI 仅保留少数运维命令（`lk serve`、`lk upgrade`），不作为 `new_feature`/`bug_fix` 开发推进入口；API 是内部 program boundary，供 program handler 和 adapter 调用，不是用户开发入口。
- **v0.14 开发期（v0.13 基础上）**：在 v0.14 正式发布前的开发与调试阶段，CLI 与 Web Chat **并行可用**，CLI 仍按 v0.13 行为提供 workflow 推进、运行调试、`lk agent ...` 等命令；Web Chat 作为 v0.14 的产品入口并先接入新的 dispatch。发布日（v0.14 release tag）后立即切换为 Web Chat 唯一入口，CLI 退化为运维。
- **适配要求**：桌面浏览器，不要求移动端适配。
- **离线场景**：核心 workflow 推进（program step、语义 Agent 工作、human gate）在本地完成；Git push、CI report 接收等需要网络，离线时允许延后但不静默跳过。

### 1.3 产品入口与生命周期 (Access & Lifecycle)

- **主入口（v0.14 发布后）**：Web Chat（通过 `lk serve` 启动后，在 Web 页面 Chat tab 中完成所有核心开发操作）。这是 `new_feature` 和 `bug_fix` 的唯一开发入口。
- **辅助入口**：CLI（仅限少数运维命令：`lk serve` 启动服务、`lk upgrade` 升级；不提供 workflow 推进能力）。API（供 program handler 和 adapter 调用，内部 program boundary）。
- **双接口过渡期（v0.14 开发期）**：v0.14 在 v0.13 之上开发，发布前 CLI 与 Web Chat **并存**。CLI 在过渡期继续提供 v0.13 风格的 `lk agent ...` / `lk serve` / `lk ...` workflow 推进能力，以便当前阶段的运行、调试与 dogfood；Web Chat 同步接入新的 Runtime dispatch。v0.14 release tag 当日起，CLI 仅保留 `lk serve` / `lk upgrade` 等运维命令，workflow 推进由 Web Chat 独占。该切换由 Runtime 在 release cutover 阶段统一收敛，禁止在过渡期悄悄混合新旧入口策略。
- **cutover 后旧 workflow CLI 命令（deprecated no-op）**：v0.14 release cutover 生效后，CLI 上的旧 workflow 推进命令（如 `lk agent ...`）不再触发 workflow；它们被 Runtime 接受为 **deprecated no-op**——解析成功、不抛硬错、不静默调用旧 Runtime / 旧 Agent / 旧 workflow、不 mutate 任何 run / project / Git 状态、不产生外部副作用，但会输出 actionable 警告引导用户改用 Web Chat，并向 audit log 写入可追溯事件（事件须记录调用命令名、调用者、是否触发实际副作用 = false）。白名单运维命令（`lk serve`、`lk upgrade` 等）行为不受本约束影响。详见 BS-30。
- **获得产品**：用户通过 `curl | sh`（Linux/macOS）或 bat/ps（Windows）安装全局 `lk`；在项目目录中 `lk install` 创建本地 `.venv` 并安装 Louke Python 包。首次 setup 通过 `lk serve` 启动后由 Web init-wizard 完成项目初始化、依赖检查和模型就绪确认。
- **升级与迁移**：
  - **升级触发**：用户主动执行 `lk upgrade`（项目级或全局级）。v0.14 不自动升级。
  - **旧 workspace 迁移**：用户通过显式 preview/confirm 采用 v0.14 新 workflow。旧 `current_stage` 不推断为新 run；旧证据只读保留。迁移失败时，旧 workspace 保持原样，用户可在新项目/workspace 使用新 workflow。
  - **失败恢复**：adoption 失败不破坏用户文件、Git history 和既有证据。必要时允许 breaking adoption，用户在新 workspace 使用新流程。
  - **v0.14 不承诺**：跨 workflow definition version 的 in-flight run 迁移、旧 workflow 兼容。这些属于 v0.17。

---

## 2. 功能与价值 (What & Why)

### 2.1 功能描述 (What)

v0.14 将 v0.12 的 Runtime 核心类库、v0.13 的 Web/Chat/Runs 观察面和 v0.13.1 的安装与质量门装配为**唯一生产级工作流**。用户安装后启动 `lk serve`，即可通过 Web Chat 创建 `new_feature` 或 `bug_fix` run，经历完整的 Story → 需求三件套（story/spec/acceptance）评审 → 需求审批 → 设计三件套（test-plan/architecture/interfaces）评审 → M-LOCK 六件套锁定 → Issue 拆分 → 实现 → 权威测试 → 发布确认 → 归档的流程。CLI 仅保留少数运维命令（`lk serve`、`lk upgrade`），核心开发流程只能通过 Web Chat 完成。

核心能力包括：

- **Runtime 权威控制**：程序是 workflow 状态和合法转移的唯一控制者。确定性检查（lint、typecheck、测试执行、Git 操作）由 program handler 自动执行。语义任务（Story 调研、设计、代码生成、评审）由 Agent 承担，但 Agent 不能伪造 program result、批准 gate 或自行推进 run。
- **两层人类门禁**：`new_feature` 必须在需求三件套评审结束后独立批准（requirements approval gate，绑定 story/spec/acceptance 共同 digest），才能进入设计三件套；设计三件套评审结束后必须 M-LOCK（六件套共同 digest 锁定），才能进入实现。`bug_fix` 在程序验证其继承既有已批准 spec/AC 后继承 source requirements approval，但仍强制本次 run 的 M-LOCK。
- **return-upstream（返回上游）**：对未发布 active run，用户可在 M-LOCK 后请求返回 definition 声明的固定合法上游目标。目标及下游 artifact/approval/evidence 统一标记 stale/superseded，保留文件、文档和 commit 历史。不可逆外部副作用进入 `needs_attention`。
- **bounded waiver（有界豁免）**：对明确标记为 waivable 的失败检查，用户可提交含 actor/reason/scope/revision 的 waiver。原始失败保留，不改写为 PASS。requirements approval、M-LOCK、identity/secret、CAS、artifact freshness、Agent 自批、伪造 program result、release identity mismatch 永不可 waive。
- **no-new-debt adoption（不新增债务的采用）**：既有项目通过 read-only preview 运行全部检查，历史问题经审计后可冻结为 baseline-known（不是 PASS）。已进入 baseline 的文件一旦被修改，整文件必须符合当前流程并永久退出 baseline。新问题或恶化问题阻断 adoption。关键不变量不可 baseline。
- **内置 lifecycle hooks**：首版只支持 Louke 内置、版本化 hooks，覆盖语义结果保存、用户决定保存、session/artifact 保存和 return-upstream 前后。Hook 由 Runtime 调度，无 transition/gate authority。项目自定义 shell hooks 不做。
- **Agent 职责重组**：Scout/Warden/Keeper 从新 workflow 注销。确定性职责归 program handler，语义残余归 Scribe/Sage/Lex/Prism。Scribe 已有 prompt/Sage peer 合同；v0.14 接入真实 Runtime dispatch。
- **旧 CLI workflow 命令 deprecated no-op（cutover 后）**：v0.14 release cutover 生效后，CLI 上的旧 workflow 推进命令（如 `lk agent ...`）在用户尝试调用时被 Runtime 接受为 deprecated no-op，不触发任何 workflow 或外部副作用，不 mutate run/project 状态，不静默回退到旧 Runtime/旧 Agent/旧 workflow，但会输出 actionable 警告引导用户改用 Web Chat 并写入 audit log 事件。运维白名单命令（`lk serve`、`lk upgrade` 等）行为不变。
- **持久化与重启恢复**：Runtime-native run/task/gate/artifact/evidence/event 持久化。关闭浏览器、重启 Louke 或 Agent 失败后，重新进入项目即可从原位置继续，不依赖会话存活。
- **Workflow definition 版本化不可变**：同一版本不可用不同内容重新注册；新 run 默认使用当前 approved definition；已开始 run 固定原版本。
- **Spec 规模硬门禁与拆分回退**：单个 Spec 最多 30 条有效 FR+NFR；Runtime 在 Sage 初稿/修订持久化后、dispatch Lex 前执行 count 检查；超限返回 `SPEC_SCOPE_TOO_LARGE` 并进入 `needs_story_split` 返回 M-STORY；Runtime 不决定拆分边界，Scribe 提案、Human 决策；原 Story 作为 Split parent 保留，子 Story 带 `parent_story_id` 进入后续独立 release/run。
- **Sage 交互策略**：M-SPEC 默认 draft-first + 锚定 inline discussion 澄清；`question` 保留为无法形成文档锚点或必须立即取得产品决定时的例外通道。

**快乐路径（Happy Path）**：

1. 用户安装 v0.14，在项目目录执行 `lk serve`，Web 端打开项目。
2. 用户在 Web Chat 中提出新功能设想，Runtime 自动创建 `new_feature` run 并 dispatch Scribe semantic task。
3. Scribe 完成 Story 调研与撰写，输出 canonical `story.md`；Sage 对 Story 不重复发现、不改写 User Stories。Human 确认 Go（agent 给出建议，最终由 Human 决定）。
4. Runtime 推进到 M-SPEC：Scribe/Sage/Lex 按 definition 完成需求三件套（story.md / spec.md / acceptance.md），Runtime 在 dispatch Lex 前先做结构验证、30-count 检查与锚定 inline discussion 循环。
5. Runtime 创建 requirements approval gate，绑定 story/spec/acceptance 共同 digest；Human 批准后才允许进入设计。任一绑定文档 digest 改变会使旧批准失效。
6. Runtime 推进到设计阶段：dispatch Archer/Lex 等生成 test-plan.md / architecture.md / interfaces.md 三件套及其 review 产物；M-TESTPLAN 由 Archer 撰写、S 档 Prism 独立技术评审、Shield 可提供下游可执行性反馈但不批准。
7. Runtime 创建 M-LOCK gate，绑定 story.md + spec.md + acceptance.md + test-plan.md + architecture.md + interfaces.md 六件套共同 contract digest；Human 批准后才允许进入 M-DEV。六件套任一份变化使 M-LOCK 失效。
8. Runtime 推进到实现阶段：先按已批准六件套拆分 GitHub Issue 与实现任务，再 dispatch 实现 Agent 在 Runtime 指定的 workspace/工作位置中生成代码和测试；program handler 自动执行 lint/typecheck/unit/integration 测试。
9. 用户发现设计遗漏，在 M-LOCK 后请求 return-upstream 到设计阶段。Runtime 标记下游 artifact 为 stale/superseded，用户重新经过设计评审和 M-LOCK。
10. 所有检查通过后，Runtime 进入 release confirmation。Human 确认发布，Runtime 执行 tag/release/history archive。
11. 用户关闭浏览器。重启 `lk serve` 后，历史 run 完整可读，active run 可继续推进。

### 2.2 问题陈述与目标 (Why)

- **问题陈述**：当前 v0.12 Runtime 核心类库、v0.13 Web/Chat 观察面和 v0.13.1 安装/质量门各自独立，尚未装配为唯一生产工作流。用户从 `lk serve` 启动后无法完成一条从 Story 到发布归档的完整旅程。Scout/Warden/Keeper 仍是三个只包装工具的 Agent，消耗 session 和上下文。没有自动 Driver、production composition root、权威 program result 边界、return-upstream、waiver、adoption、Spec 规模硬门禁或内置 lifecycle hooks。
- **北极星目标**：用户安装 v0.14 后，只需 `lk serve` 即可通过 Web Chat 完成一条完整的 `new_feature` 产品旅程，全程由 Runtime 驱动，Agent 只做语义工作，Human 只做产品决策，程序验证所有事实。
- **可观测指标**：
  1. 一条完整的 installed-wheel `new_feature` E2E 旅程（setup → Story → 需求审批 → 设计 → M-LOCK → Issue → 实现 → 测试 → release → archive）可无阻塞完成。
  2. 该旅程中 Scout、Warden、Keeper 的 task/session/dispatch 数量均为零。
  3. program result 不能由客户端或 Agent 伪造（通过 E2E 断言验证）。
  4. Louke 自身的 v0.14 开发通过 dogfood 完整使用新 workflow，证明新流程可承担真实项目工作。
  5. 用含 31 条有效 FR+NFR 的 Spec 完成 installed-wheel E2E：Runtime 在 Lex 前拒绝、无下游副作用、回退状态可重启恢复、父子 Story 可追溯、拆分后的子 Story 能独立继续；另验证 30 条通过及 `Valid=❌` 不计数。

### 2.3 行为种子（EARS-lite）

以下为从故事中提取的行为种子，用于 M-SPEC 继续展开；不要求在 M-STORY 锁定完整验收合同。

> EARS 句式说明：
> - **WHEN（事件驱动）**：用户主动触发的操作
> - **IF（状态驱动）**：系统处于特定状态时的响应
> - **WHILE（持续型）**：过程中持续反馈
> - **WHERE（可选型）**：特定上下文/平台变体
> - **THE [系统] SHALL（通用型）**：无条件的系统行为

### BS-01 自动 Driver 入口
- EARS: `WHEN 用户通过 Web Chat 启动 new_feature, THE 系统 SHALL 创建 WorkflowRun 并自动执行 program steps 和 dispatch semantic tasks`
- 来源: 快乐路径
- 说明: 核心开发唯一入口为 Web Chat；CLI 仅保留运维命令，不作为 workflow 推进入口

### BS-02 权威 program result 边界
- EARS: `WHEN 一个 Agent 或客户端提交 program result, THE 系统 SHALL 拒绝，仅接受对应 program handler 的真实执行结果`
- 来源: 核心原则
- 说明: 防止 Agent 或客户端伪造测试结果、gate 状态或审批

### BS-03 重启恢复
- EARS: `WHEN Louke 服务重启, THE 系统 SHALL 从持久化 store 恢复 run、gate、task、artifact、evidence 和当前步骤，允许从原位置继续`
- 来源: 快乐路径
- 说明: 关闭浏览器或 Agent 失败后不丢失进度

### BS-04 return-upstream 目标选择
- EARS: `WHEN 用户请求 return-upstream AND 当前 run 为 active 且未发布, THE 系统 SHALL 展示 definition 声明的固定合法上游目标并等待用户确认`
- 来源: 快乐路径
- 说明: 返回上游有固定合法目标，不可任意跳转

### BS-05 return-upstream 下游 stale
- EARS: `WHEN return-upstream 执行, THE 系统 SHALL 将目标步骤及下游 artifact/approval/evidence 标记为 stale/superseded，保留文件、文档和 commit 历史`
- 来源: 边界条件
- 说明: 下游产物标记过期但不删除，保留完整历史

### BS-06 return-upstream 不可逆边界
- EARS: `IF return-upstream 遇到不可逆外部副作用（已 publish/tag）, THE 系统 SHALL 拒绝自动回退并进入 needs_attention`
- 来源: 边界条件
- 说明: 已发布/tag 的副作用不可自动回退，需人工介入

### BS-07 bounded waiver 记录
- EARS: `WHEN 用户对 waivable 检查提交 waiver, THE 系统 SHALL 记录 actor/reason/scope/target evidence/revision 并保留原始失败证据，不将 FAIL 改写为 PASS`
- 来源: 边界条件
- 说明: waiver 保留原始失败，不改写结果

### BS-08 不可 waive 不变量
- EARS: `WHERE 检查为 requirements approval、M-LOCK、identity/secret、CAS、artifact freshness、Agent 自批或 release identity mismatch, THE 系统 SHALL 拒绝任何 waiver`
- 来源: 核心原则
- 说明: 安全关键检查永远不可豁免

### BS-09 no-new-debt adoption preview
- EARS: `WHEN 用户对既有项目请求 adoption preview, THE 系统 SHALL 固定 Git revision/workspace digest、运行全部适用检查并展示可 baseline 的历史问题与阻断 adoption 的新问题`
- 来源: 快乐路径
- 说明: 只读预览，不修改用户文件

### BS-10 touch-to-clean
- EARS: `IF baseline 文件在 adoption 后被首次修改, THE 系统 SHALL 对该文件执行当前全部适用检查，全部通过后该文件永久退出 baseline`
- 来源: 边界条件
- 说明: 修改 baseline 文件触发全量检查，通过后不再享受 baseline 豁免

### BS-11 adoption 失败安全保证
- EARS: `IF adoption 或 baseline 操作失败, THE 系统 SHALL NOT 破坏用户文件、Git history 或既有证据`
- 来源: 边界条件
- 说明: adoption 失败不产生副作用

### BS-12 内置 lifecycle hooks 调度
- EARS: `WHEN 语义结果、用户决定或 session 被保存, THE 系统 SHALL 调用已注册的内置 versioned lifecycle hook`
- 来源: 快乐路径
- 说明: Hook 由 Runtime 调度，无 transition/gate 权限

### BS-13 Agent 注销
- EARS: `THE 系统 SHALL NOT 在新 workflow run 中创建 Scout、Warden 或 Keeper 的 task、session 或 dispatch`
- 来源: 核心原则
- 说明: 旧 Agent 完全注销，不再参与新 workflow

### BS-14 workflow definition 不可变
- EARS: `THE 系统 SHALL NOT 允许以不同内容重新注册同一 workflow definition version`
- 来源: 竞品补全（Adopt: GitHub Actions）
- 说明: 已注册版本不可变，防止在途 run 不一致

### BS-15 完整可完成 workflow
- EARS: `THE 系统 SHALL 支持通过 Web Chat（经 lk serve 启动）完成 new_feature 和 bug_fix 的完整产品旅程（Story → 需求三件套评审 → 需求审批 → 设计三件套评审 → M-LOCK 六件套锁定 → Issue 拆分 → 实现 → 权威测试 → release → archive）；CLI 仅保留少数运维命令（lk serve、lk upgrade），不作为开发推进入口`
- 来源: 北极星目标
- 说明: 核心开发唯一入口为 Web Chat，CLI 仅运维；两套人类门禁顺序不可乱

### BS-16 E2E 权威验证
- EARS: `WHEN installed-wheel E2E 执行, THE 系统 SHALL 断言 Scout/Warden/Keeper dispatch 数量为零且 program result 不可由客户端/Agent 伪造`
- 来源: 可观测指标
- 说明: E2E 自动验证核心不变量

### BS-17 3-piece 整合目标
- EARS: `THE 系统 SHALL 在唯一 production composition root 下装配 v0.12 Runtime 核心、v0.13 Web/Chat/Runs 观察面和 v0.13.1 安装与质量门，并提供完整 new_feature 与 bug_fix 旅程`
- 来源: 原始输入
- 说明: 3-piece 整合是 v0.14 的根本产品目标

### BS-18 需求三件套 gate（requirements approval）
- EARS: `WHEN story.md、spec.md、acceptance.md 三份需求文档完成评审, THE 系统 SHALL 创建绑定该三份文档共同 digest 的 requirements approval gate；批准前不得启动或接受 test-plan/architecture/interfaces 任务或产物`
- 来源: 核心原则 + v0.12 FR-0801
- 说明: 需求审批是独立于 M-LOCK 的第一道人类门禁；任一绑定文档 digest 变化必须使旧批准失效

### BS-19 M-LOCK 六件套 gate
- EARS: `WHEN test-plan.md、architecture.md、interfaces.md 三份设计文档完成评审 AND 需求审批有效, THE 系统 SHALL 创建绑定 story.md + spec.md + acceptance.md + test-plan.md + architecture.md + interfaces.md 六件套共同 contract digest 的 M-LOCK gate；M-LOCK 未批准时不得创建或启动实现任务`
- 来源: 核心原则 + v0.12 FR-0901
- 说明: M-LOCK 锁的是六件套，不是设计三件套；任一绑定文档变化使 M-LOCK 失效

### BS-20 Issue 拆分时机
- EARS: `THE 系统 SHALL 仅在当前 run 的 M-LOCK 批准后才允许根据已批准六件套拆分 GitHub Issue 与实现任务；M-LOCK 未批准时 Issue 拆分不得创建实现 worktree、commit 或 push`
- 来源: 核心原则 + Trace/Evidence Graph 独立性
- 说明: Issue 与实现 worktree/commit/push 必须由 M-LOCK 之后的 program handler 完成，Agent 不能伪造

### BS-21 bug_fix 继承 requirements approval
- EARS: `WHEN bug_fix 由程序验证其链接既有已批准 spec/AC 且不改变预期行为, THE 系统 SHALL 继承 source requirements approval 而不创建新的需求 gate；任一验证失败时拒绝 hotfix 并要求进入新需求流程`
- 来源: v0.12 FR-0801 / FR-2101
- 说明: bug_fix 继承不等于绕过 M-LOCK

### BS-22 Runtime 拥有 M-SPEC 主循环
- EARS: `THE 系统 SHALL 由 Runtime 负责 M-SPEC 的 artifact revision/digest/diff、结构验证、讨论扫描与等待、锚点、Git/GitHub Issue reconcile、requirements approval/lock 和重启恢复；Sage 和 Lex 每次只完成一轮语义任务，不调用 workflow/gate 工具`
- 来源: 已确认约束 §0.1
- 说明: 把 dispatch/recovery/approval/lock 等副作用与 Sage/Lex 的语义任务解耦

### BS-23 Spec 规模硬门禁
- EARS: `WHEN Sage 完成 Spec 初稿或修订并持久化, THE 系统 SHALL 在 dispatch Lex 之前计算有效 FR+NFR 数量（Valid=❌ 不计）并与 30 比较；恰好 30 条允许、超过时返回 SPEC_SCOPE_TOO_LARGE 并将 run 标记为 needs_story_split`
- 来源: 已确认约束 §0.1 + cutover-checklist §E
- 说明: 硬门禁作用域是单个 Spec，不累计同一 release 的多个 Spec

### BS-24 超限拆分回退与父子 Story
- EARS: `WHEN run 进入 needs_story_split, THE 系统 SHALL 合法返回 M-STORY 并完整保留原 Story/Spec/Acceptance revision；Scribe 提出独立价值切片、Human 决策；确认后原 Story 标记为 Split parent 并由子 Story 记录 parent_story_id 进入后续独立 release/run`
- 来源: 已确认约束 §0.1
- 说明: Runtime 不自动决定拆分边界；父子追溯由 spec_id/Story digest 链路保留

### BS-25 Scribe/Sage 职责切分
- EARS: `THE 系统 SHALL 由 Scribe 产出完整 canonical Story；Sage 在 M-SPEC 不重复 Story discovery，也不在 spec.md 中改写 User Stories；Scribe Story digest 与 spec.md User Stories 引用必须可追溯到同一 source revision`
- 来源: 已确认约束 §0.1
- 说明: 防止 Story 与 Spec 双权威漂移

### BS-26 Sage draft-first 交互策略
- EARS: `WHEN Sage 在 M-SPEC 阶段处理 Spec 草稿, THE 系统 SHALL 默认走 draft-first + 锚定 inline discussion 澄清；question 仅在无法形成文档锚点或必须立即取得产品决定时作为例外通道`
- 来源: 已确认约束 §0.1 + research-report §15.12
- 说明: Sage 不承担 Scribe 的需求发现

### BS-27 M-TESTPLAN 评审分工
- EARS: `THE 系统 SHALL 由 Archer 撰写 M-TESTPLAN、由 S 档 Prism 独立技术评审、由 Shield 提供下游可执行性反馈但不批准；Sage 不再承担 Test Plan 评审`
- 来源: 已确认约束 §0.1 + research-report §15.16
- 说明: 评审分工与 M-SPEC 评审（Sage 是需求分析 reviewer）解耦

### BS-28 过渡期入口收敛
- EARS: `WHEN v0.14 release cutover 触发, THE 系统 SHALL 统一把核心开发入口切换为 Web Chat 并将 CLI 收敛到 lk serve / lk upgrade 等少数运维命令；过渡期禁止悄悄混合新旧入口策略`
- 来源: 已确认约束 §0.1 + research-report §15.11
- 说明: 入口切换由 Runtime 在 release cutover 阶段统一执行，不在过渡期半切换

### BS-29 installed-wheel 31 条 E2E 验证
- EARS: `WHEN installed-wheel E2E 使用含 31 条有效 FR+NFR 的 Spec 执行, THE 系统 SHALL 证明 Runtime 在 Lex 前拒绝、无下游副作用（无 anchor、Issue、approval、lock）、回退状态可重启恢复、父子 Story 可追溯、拆分后的子 Story 能独立继续；同一 E2E 另验证恰好 30 条通过以及 Valid=❌ 不计数`
- 来源: cutover-checklist §E
- 说明: 这是 30 条硬门禁 + 拆分回退的权威证据

### BS-30 旧 workflow CLI 命令 deprecated no-op
- EARS: `WHEN v0.14 release cutover 已生效 AND 用户调用旧 workflow 命令（例如 lk agent ... 等 CLI workflow 推进命令）, THE 系统 SHALL 接受该调用、将其作为 deprecated no-op 处理，不执行任何 workflow 或外部副作用、不 mutate 任何 run / project 状态、不静默回退到旧 Runtime 或旧 Agent 行为；THE 系统 SHALL 输出 actionable 警告引导用户改用 Web Chat，并向 audit log 写入可追溯事件`
- 来源: Human 确认（STR-1401 Go 决策约束）+ cutover-checklist §B + research-report §15.11
- 说明: 旧 CLI workflow 命令在 cutover 后必须保留解析但只作为 deprecated no-op：必须可调用、不报错、不静默、不动状态、要可审计；事件字段须足以区分是哪种旧命令与是否触发实际副作用（本字段在 E2E 中应当为 false）

---

## 3. 竞品与边界 (Scope & Competition)

### 3.1 Adopt / Avoid 清单（补全素材，非市场裁决）

鉴于 v0.14 是 Louke 自身 workflow 架构的整合与升级，而非面向终端用户的新功能，本 Story 无直接竞品。以下基于类似 CI/CD pipeline-as-code 产品的实践模式做补全式分析：

**Adopt**

1. [GitHub Actions / Jenkins]: 将 workflow definition 作为版本化不可变合同，run 创建后固定 definition version，不随定义更新而改变在途 run — 防止 workflow 定义变更导致在途 run 进入不一致状态，与我们已有 catalog 设计一致。
2. [GitLab CI / CircleCI]: 程序化 gate 执行——pipeline 状态只能由真实执行的 job 结果推进，不能由 API 调用者声明 "pass" — 直接对应 v0.14 的"Agent 不能伪造 program result"核心要求。
3. [GitHub Issue + Spec/AC 链接]: 已发布产品缺陷必须链接既有已批准 spec/AC，证明属于实现偏差而非新需求 — 与我们 v0.12 bug_fix 继承 source approval 模式一致。

**Avoid**

1. [部分 CI 产品的 blanket skip]: 允许跳过整组检查的 `--force` 或全局 bypass，导致安全门被静默绕过 — 我们的旧 `--force` waiver 就是这种模式。v0.14 的 bounded waiver 必须保留原始失败、限制 waivable 范围、永不可 waive 关键不变量。
2. [某些 Agent 自批模式]: 允许生成代码的 Agent 自行声明测试通过或代码审查通过，没有独立验证 — 直接对应 v0.14 的"Agent 不能自批、自报测试或伪造 program result"。
3. [Cumulative per-release 限额模式]: 把限额做在 release 维度（多个 Spec 累加），导致单 Spec 仍可越限 — v0.14 明确硬门禁作用域是单个 Spec，不累计同一 release 的多个 Spec；M-STORY 推荐 1 Story/Spec 对应 1 release 也是为了便于单 Spec 自洽。
4. [旧 CLI 命令的硬报错或静默透传]: cutover 后把旧 CLI workflow 命令直接抛 `CommandRemoved` 或干脆不解析（用户得到静默失败 / 找不到命令），或反之把它们透传回旧 Runtime"以保持兼容" — 这两类做法都会让用户失去清晰的下一步行动，或让旧 Runtime 偷偷复活。v0.14 选中间路径：deprecated no-op + actionable 警告 + audit log 事件（详见 BS-30）。

### 3.2 Out-of-Scope（明确不做）

以下内容明确属于 v0.17 或更晚版本，不在 v0.14 范围内：

- [ ] 完整 CI report interruption matrix（immediate/safe-point/record-only、迟到报告处理等）。v0.14 只保留完成核心 workflow 必需的权威测试执行和证据。
- [ ] 夜间自动重构、`maintenance/*` 分支、复杂 branch/worktree 生命周期自动化、hotfix 延迟同步自动管理。
- [ ] 跨 workflow definition version 的 in-flight migration、step mapping、兼容旧 workflow。
- [ ] 精细 artifact dependency graph、局部 freshness 传播、自动补偿/reconcile 不可逆副作用。
- [ ] 项目自定义或任意 shell lifecycle hooks；复杂 hook marketplace/policy。
- [ ] baseline finding 的复杂语义 identity、owner/expiry 自动治理和 workspace-level 高级 debt analytics。
- [ ] waiver expiry/renew/revoke/多 waiver 冲突等高级治理。
- [ ] v0.12.1 全面测试债务清理、通用真实环境矩阵、全面浏览器覆盖。
- [ ] 完整 Settings、Chat `/`/`!` 命令、End User Docs AI 编辑（属 v0.15）；i18n（属 v0.16）。
- [ ] 复杂 controlled legacy fallback、旧 Runtime 双版本兼容。
- [ ] 版本号提议/写入的重新设计（复用 v0.13.1 release identity）。
- [ ] 把 30 条 FR+NFR 限额做在 release 累计维度；v0.14 硬门禁作用域明确为单个 Spec。
- [ ] Runtime 自动决定 needs_story_split 拆分边界；v0.14 由 Scribe 提案、Human 决策。
- [ ] Sage 在 M-SPEC 开头使用 `question` 作为默认交互方式；v0.14 默认 draft-first + 锚定 inline discussion。
- [ ] Lex 替代 Sage 承担 Test Plan 评审；Test Plan 技术评审固定为 S 档 Prism。
- [ ] v0.14 完整移除旧 CLI workflow 命令的解析入口 / 改名为其它子命令 / 把旧命令透传到新 Runtime；cutover 后它们只作为 deprecated no-op 接受，解析保留但无副作用。彻底下线旧命令解析属于 v0.17。
- [ ] 为旧 CLI workflow 命令提供完整的 deprecation timeline、文档站横幅、独立 telemetry dashboard；本 Story 仅要求可审计的 audit log 事件，不构建周边发布物。

### 3.3 约束条件

- **技术约束**：
  - 程序化 workflow 必须基于 Python（与现有 Louke 技术栈一致）。
  - 持久化 store 必须支持重启恢复，不依赖内存状态或 Agent 会话。
  - v0.13 的 toolbar/sidebar/tab 和 Runs 观察面复用，不重新设计 UI chrome。
  - v0.14 必须完成 v0.12 Runtime 核心类库、v0.13 Web/Chat 观察面、v0.13.1 安装与质量门 3-piece 整合，形成唯一 production composition root。
  - 单个 Spec 最多 30 条有效 FR+NFR（`Valid=❌` 的历史需求不计入），恰好 30 条允许；超限不可 waive。硬门禁作用域是单个 Spec，不累计同一 release 的多个 Spec；M-STORY 推荐一个 Story/Spec 对应一个 release。
  - 30-count 检查由 Runtime 在 Sage 完成 Spec 初稿或修订并持久化后、dispatch Lex 之前执行；超限返回稳定错误 `SPEC_SCOPE_TOO_LARGE`，进入 `needs_story_split`，Lex、anchor、Issue、approval、lock 等下游副作用一律不得执行。
  - Runtime 拥有 M-SPEC 主循环（revision/digest/diff、结构验证、讨论扫描、锚点、Git/GitHub Issue reconcile、requirements approval/lock、重启恢复）；Sage/Lex 每次只完成一轮语义任务，不调用 workflow/gate 工具。
- **组织约束**：
  - installed-wheel E2E 和 Louke dogfood 均通过后方可删除旧执行路径和受控回退开关。
  - Spec/AC/Issue/commit hash/artifact digest 等 Trace/Evidence 资产 identity 不因 workflow 变化而重写。
  - v0.14 开发期 CLI 与 Web Chat 双接口并存；v0.14 release tag 当日由 Runtime 在 release cutover 阶段统一收敛为 Web Chat 唯一入口（CLI 仅保留运维命令）。cutover 生效后，旧 CLI workflow 命令（如 `lk agent ...`）必须被 Runtime 接受为 deprecated no-op：不执行任何 workflow 或外部副作用、不 mutate run / project 状态、不静默调用旧 Runtime / 旧 Agent / 旧 workflow、不得报硬错；必须输出引导用户改用 Web Chat 的 actionable 警告，并向 audit log 写入可追溯事件（事件须含调用命令名、是否触发实际副作用 = false 等审计字段）。此约束与 BS-30、§1.3 cutover 后段落、§7 Human 确认一致。
  - M-TESTPLAN author = Archer；独立技术 reviewer = S 档 Prism；Sage 不再承担 Test Plan 评审（仅承担需求分析评审）。

---

## 4. 风险与假设 (Risk & Assumption)

### 4.1 关键假设

### A-01
- 假设: 现有 v0.12 Runtime 核心类库（Store、Catalog、Orchestrator、ProgramStepExecutor）可以无重大重构装配为 production composition root
- 验证: 代码走查 + 装配原型验证
- 负责人: 技术负责人

### A-02
- 假设: v0.13 Web/Chat 的 OpenCode transport 和 SSE streaming 可以可靠接入新 Runtime 的 semantic task dispatch
- 验证: 集成测试：Chat 中启动 Scribe task 并验证 Runtime state
- 负责人: 技术负责人

### A-03
- 假设: 现有 Git 项目（非 Louke 项目）可以接受 no-new-debt adoption 的 baseline 模型，用户愿意接受"历史问题冻结但不通过"的约束
- 验证: 在真实既有项目上试运行 adoption preview
- 负责人: PM

### A-04
- 假设: return-upstream 的"固定合法目标 + 统一下游 stale"策略覆盖 80% 以上的实际返工场景
- 验证: 收集 v0.12/v0.13 开发期间的返工案例并对照验证
- 负责人: PM

### A-05
- 假设: Runtime 在 dispatch Lex 前的 30-count 检查可以依赖现有 FR/NFR 的 `Valid` 字段判定有效性，不需要重新扫描正文
- 验证: 抽样 5-10 个既有 Spec 验证 Valid 字段与正文是否一致
- 负责人: 技术负责人

### A-06
- 假设: 31 条有效 FR+NFR 的 E2E Spec 不会因为其他 FR/NFR 改动而影响拆分边界判定
- 验证: 锁定 E2E Spec 文本并复跑多次
- 负责人: 测试负责人

### 4.2 主要风险

### R-01
- 风险: Runtime API 当前可接受客户端提供的 result 字符串，关闭此路径可能影响现有 adapter
- 影响: 高
- 应对: 逐 adapter 迁移到 program handler 真实执行，设置过渡期标记和 deprecated 警告

### R-02
- 风险: 从旧 Maestro 驱动切换到自动 Driver 后，隐藏的依赖顺序或副作用可能暴露
- 影响: 高
- 应对: 先建立完整 responsibility inventory，逐项验证后再注销 Scout/Warden/Keeper

### R-03
- 风险: no-new-debt adoption 的 baseline 模型可能对既有大型项目过于严格，导致 adoption 失败率高
- 影响: 中
- 应对: 提供 preview 模式让用户提前评估；必要时允许分步 adoption 或 workspace-level 豁免（v0.17 增强）

### R-04
- 风险: installed-wheel E2E 旅程可能因环境差异（Python 版本、OS、网络）而不可复现
- 影响: 中
- 应对: 使用隔离 venv + 固定依赖版本；CI 中运行 E2E 作为门禁

### R-05
- 风险: 重启恢复依赖持久化 store 的完整性；store 损坏或 schema 不兼容可能导致 run 丢失
- 影响: 中
- 应对: 持久化 store 添加 schema version 和完整性校验；提供只读导出入口

### R-06
- 风险: 30-count 检查如果错误把 `Valid=❌` 的需求计入或漏计，可能误杀或放过超限 run
- 影响: 中
- 应对: A-05 抽样验证；E2E 用 31 条与 30 条双向断言覆盖；错误码 `SPEC_SCOPE_TOO_LARGE` 需在 E2E 中证明可重复触发

### R-07
- 风险: needs_story_split 拆分边界若由 Runtime 自动决定会与产品价值边界错位；若 Scribe 仅给一个建议而 Human 不介入，父子 Story 链路可能不完整
- 影响: 中
- 应对: 流程上明确 Scribe 必须给出多个独立价值切片，Human 显式批准；Runtime 只检测不决策；E2E 必须断言可重启恢复与父子可追溯

---

## 5. 必要性与冲突 (Necessity & Conflict)

- **已实现？**：否。v0.12 已完成 Runtime 核心类库（Store、Catalog、Orchestrator、ProgramStepExecutor、Gate），但未装配为唯一 production composition root、未接入自动 Driver、未实现完整 `new_feature`/`bug_fix` workflow。v0.13 已完成 Web/Chat/Runs 观察面，但明确将 rollback、waiver、CI interruption 和 workflow reflow 推迟到 v0.14。v0.13.1 已完成安装和 pre-commit 质量门。Scribe prompt/Sage peer 合同已存在，但未接入 Runtime dispatch。Scout/Warden/Keeper 仍存在于 Agent catalog 和 Chat 列表中。
  - 证据：`research-report.md` §3（当前真实实现状态表）；v0.13 story.md:37-40（"本版本不实现：workflow 回退、waive、CI report 中断语义"）。
- **相抵触？**：否。v0.14 是 v0.12/v0.13/v0.13.1 的整合点，不与其目标冲突。v0.12 确立的 Runtime 合同（程序是状态唯一控制者）在 v0.14 中进一步强化为生产现实。v0.13 的 UI chrome 和观察面在 v0.14 中复用。v0.13.1 的安装、AC@version 和 pre-commit 质量门在 v0.14 中继承。Spec 规模硬门禁（每 Spec ≤30 FR+NFR、`Valid=❌` 不计、Scope per-Spec 非 per-release）与 v0.12 已锁定的 30/30 acceptance 模型兼容——后者本身就是单 Spec 维度的样本。
- **结论**：新建。v0.14 是继承 v0.12/v0.13/v0.13.1 的整合版本，不是替代或分叉。往期版本中明确推迟到 v0.14 的能力（return-upstream、waiver、adoption、lifecycle hooks）均为首次实现。

---

## 6. 方案疑议（A/B Advisory，非决策）

- **状态**：无异议。
- **说明**：v0.14 的核心目标（整合 v0.12/v0.13/v0.13.1 + 四项新能力 + Spec 规模硬门禁 + M-SPEC 主循环重排）与往期版本路线一致，无冲突。v0.12 确立的 Human/AI/Program 边界、v0.13 的 UI 设计、v0.13.1 的安装模式在 v0.14 中均被继承和强化，无替代方案需要提出。已确认约束在 §0.1 中以用户裁决形式固化为 Story 边界，不再作为疑议回退。

---

## 7. 分流结论与门禁 (Gate)

- **分流结论**：Go（Agent 建议）
- **Sage peer review**：[Pending — 由 Sage 独立对当前 Story digest 完成 peer review 后填写，Scribe 不得伪造或代填]
- **绑定 Story digest**：[待 Sage 独立 review 后由 Sage 写入 `sha256:...`；本字段一旦填写即视为本 Story 的权威 digest，任何后续编辑都会使旧 digest 失效并要求重新 peer review 与 Human 确认]
- **Human 确认**（仅决策点，Agent 已自检其余）：
  - [ ] 分流结论认同（Go / Park / No-Go）
  - [ ] §0.1 已确认约束作为 v0.14 Story 的硬边界（裁决 §6 无异议）
- **Backlog 登记**：Go → 继续 M-FOUND/M-SPEC 流程；Park → 登记 Backlog 标记 `Park`；No-Go → 登记 Backlog 标记 `NO-GO`（story 永久存档，不删除）

---

## 8. 可追溯种子 (Traceability)

- **Story ID**：`STR-1401`
- **创建时间**：`2026-07-17T00:00:00+08:00`
- **关联 Issue（待填充）**：`#待创建`（按 BS-20，Issue 拆分只在 M-LOCK 批准后才允许启动）
- **关联 Spec ID（待填充）**：`#待创建`（按 BS-23，受单 Spec ≤30 有效 FR+NFR 硬门禁约束）
- **配套文档**：
  - `research-report.md`：调研报告（研究输入，非规范性合同；§15 已确认决策与本 Story §0.1 一一对应）
  - `cutover-checklist.md`：生产切换架构与交付约束清单（与 §3.3、§4.1/§4.2、BS-23/24/29 一一对应）
- **下游合同 bundle**：`story.md` + `spec.md` + `acceptance.md` + `test-plan.md` + `architecture.md` + `interfaces.md` 六件套按 BS-19 共同 digest 由 M-LOCK 锁定。

---

*—— 本故事由 Scribe（M-STORY）于 2026-07-17 生成；经 Sage peer review 且 Human 确认后：Go → 进入后续流程，Park / No-Go → 存档入 Backlog 并标记（story 永久保留，不删除）。*
