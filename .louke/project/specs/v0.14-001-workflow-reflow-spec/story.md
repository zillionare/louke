# STR-1402: 以 Web 工作台完成发布需求定义

---

| Story ID | 创建时间 | 分流结论 |
| :--- | :--- | :--- |
| STR-1402 | 2026-07-18T00:00:00+08:00 | Go（Agent 建议） |

---

## 0. 原始输入

> 现在的任务是对工作流进行重构，计划发布在 v0.14中，分4个 spec。
>
> 我在.louke/project/specs/v0.14-001-workflow-reflow-spec/flow.md 中，提供了一个直到 spec 完成时的工作流。
>
> 其它部分暂不处理，放在.louke/project/specs/backlog中，你可以参考。
>
> 你的任务，参考 Scribe 的指令，把这个工作流转换成为 story, 以便我们可以开始一个新的 release.
>
> 注意
> 1. 只注重主体内容（templates/story.md） 中的主体部分
> 2. 使用中文
> 3. 不派子代理，你自己完成。
> 4. 你可以对我进行 interview。
> 5. story 要确保技术上可行性（尽管我们已做了调研，在 backlog 中，但那些只是参考）

---

## 1. 用户与场景 (Who & Where)

### 1.1 用户画像 (Who)

- **主要角色**：在单个 Git workspace 中使用 Louke 推进产品发布的负责人。他既提出发布设想，也负责产品范围、Story、Spec、Acceptance 和最终需求锁定的人工决策。
- **次要角色**：N/A。本 Story 中的 Scribe、Sage、Lex 是受 Runtime 调度的语义协作者，不是产品用户，也不拥有流程推进权。
- **用户规模**：单一用户。首版不处理多人同时登录和多人协同审批。
- **使用频次**：中频。每次创建新 release 时集中使用，并在需求评审期间持续多轮交互。
- **网络环境**：稳定办公网络。文档编辑和本地状态可在短暂断网时保留，但 Git remote、GitHub Project、Issue 和模型调用需要网络；网络失败不得被当作成功。

### 1.2 使用终端 (Where)

- **终端类型**：Web 桌面浏览器。用户通过 `lk serve` 启动本地服务，后续 release 创建、Agent 对话、文档评审和批准均在 Web Workbench 完成。
- **适配要求**：仅桌面端；复用既有 Workbench、Chat 和 Dev Docs 视觉框架，不在本 Story 重做整体 UI chrome。
- **离线场景**：不要求完整离线工作流。短暂断网或服务重启后，已保存的流程位置、文档 revision、评审结果和待处理问题必须可恢复；依赖远程服务的步骤保持阻塞并展示可操作错误。

### 1.3 产品入口与生命周期 (Access & Lifecycle)

- **主入口**：用户在目标 workspace 执行 `lk serve` 后进入 Web Workbench；创建 release 的入口为 Web 中的新建项目页面，当前路径为 `/projects/new`。
- **辅助入口**：CLI 仅负责安装、升级和 `lk serve` 等运维动作，不作为本 Story 中需求工作流的推进入口。Agent 对话通过工作台内的小型 Chat 窗口承载。
- **获得产品**：复用 v0.13.1 已有的项目本地/全局安装方式。首次启动或 setup 信息失效时，Web 展示启动诊断和 Workspace Setup；用户只补充缺失值、裁决冲突值并处理登录、授权或模型配置。
- **升级与迁移**：升级复用已有 Louke 升级入口。本 Story 要求升级后重新执行启动检查，并对已有有效 setup 和外部资源进行 reconcile，不重复初始化或创建资源；不定义旧版 active run 向新工作流的迁移。
- **失败恢复**：安装或启动失败时保留可操作诊断；setup、release 创建、Agent 评审、文档保存、Git/GitHub 操作中断后，从已持久化的当前步骤和操作继续，并在重试前核对已发生的副作用。

---

## 2. 功能与价值 (What & Why)

### 2.1 功能描述 (What)

Louke v0.14 的第一个工作流 Story，要让用户从 `lk serve` 开始，在 Web Workbench 中完成一个新 release 的需求定义。Runtime 负责启动与 setup、单活跃 release 约束、工作流位置、文档写入次序、Agent 调度、revision 提交和恢复；Scribe、Sage、Lex 只负责各自的撰写或独立评审。用户通过对话补充产品事实，通过 Web 编辑或 inline discussion 审阅文档，并在 Story 分流和需求三件套锁定处作出明确决定。Story、Spec、Acceptance 均通过后，用户批准 M-LOCK-1，系统锁定三件套并按 Spec 创建关联到 release GitHub Project 的 Issues，为后续三个 Spec 承接的设计与开发流程提供入口。

**快乐路径（Happy Path）**：

1. 用户安装或升级 Louke，在目标 workspace 执行 `lk serve`；Runtime 完成诊断，对首次或失效 workspace 展示 setup preview，用户只处理缺失、冲突和授权后确认。
2. 用户在 Web 新建 release，填写一句话设想和版本信息；Runtime 确认没有冲突的活跃主 release、上一开发分支已合回 `main`，创建本次 release 的必要资源、Spec 目录和初始 `story.md` revision，然后打开 Story 编辑页。
3. Runtime 在只读文档旁启动 Scribe 对话。Scribe 先调查并提出 Go/Park/No-Go 建议，由用户裁决；只有裁决为 Go 时，Scribe 才继续访谈用户并完成一份可独立评审的 Story，Runtime 随后提交该 revision。
4. 用户与独立 Sage 对当前 Story revision 进行评审。用户可以编辑或发起 inline discussion；Runtime 协调单写者次序、保存每轮 revision，并让 Scribe 回应未解决意见，直到用户和 Sage 都通过当前版本。
5. Runtime 依次进入 M-SPEC 与 M-ACC。Sage 在继承需求上下文的会话中分别起草 `spec.md` 和 `acceptance.md`，Human 与 Lex 对当前 revision 独立评审；未通过时由 Sage 响应并进入下一轮，格式和语义都通过后才离开当前阶段。
6. 用户在需求三件套任一阶段发现上游产品问题时，明确要求返回；Runtime 将流程指针回到合法上游阶段，并使受影响的下游评审结论失效后重新完成评审。
7. Story、Spec、Acceptance 均通过后，项目页显示 M-LOCK-1 等待批准。用户点击批准后，三份文档转为只读，Runtime 按当前 Spec 幂等创建 GitHub Issues 并关联本 release 的 GitHub Project。

### 2.2 问题陈述与目标 (Why)

- **问题陈述**：当前 Louke 已有 Runtime 原语、Web Workbench、文档编辑、项目 preview、OpenCode 会话和部分 gate 能力，但它们尚未组成一条从启动到需求三件套锁定的生产流程。用户仍需依赖对话约定或手工命令协调 Agent、文档写入、评审轮次和 Git 提交，容易出现流程跳步、并发覆盖、评审针对旧 revision、重启丢失上下文或未批准就创建下游工作的情况。
- **北极星目标**：用户只需从 `lk serve` 进入 Web Workbench，就能完成一次可恢复、可追溯、不会被 Agent 越权推进的新 release 需求定义，并在一次明确批准后得到锁定的 Story/Spec/Acceptance 和对应 GitHub Issues。
- **可观测指标**：
  1. 安装后的 Louke 可仅通过 `lk serve` 与 Web Workbench 完成 setup、release 创建、M-STORY、M-SPEC、M-ACC、M-LOCK-1 和 Issue 创建的完整产品旅程。
  2. 对每个文档 revision，都能识别作者、评审结论和对应提交；Human 与 Agent 的并发操作不会静默覆盖对方内容。
  3. 在 setup、访谈、任一评审轮或外部操作中重启服务后，流程能恢复到同一步骤、同一文档 revision 和同一 Agent task/session，不重复已完成副作用。
  4. M-LOCK-1 批准前不会创建本次实现 Issues；批准后重复执行 reconcile 仍只产生一组与当前 Spec 对应的 Issues 和 Project 关联。
  5. 除 setup 缺失/冲突、产品访谈、评审意见和明确批准外，用户不需要手工运行命令来协调流程或转交 Agent。

### 2.3 行为种子（EARS-lite）

以下为从故事中提取的行为种子，用于 M-SPEC 继续展开；不要求在 M-STORY 锁定完整验收合同。

> EARS 句式说明：
> - **WHEN（事件驱动）**：用户主动触发的操作
> - **IF（状态驱动）**：系统处于特定状态时的响应
> - **WHILE（持续型）**：过程中持续反馈
> - **WHERE（可选型）**：特定上下文/平台变体
> - **THE [系统] SHALL（通用型）**：无条件的系统行为

### BS-01 启动诊断与 Setup
- EARS: `WHEN 用户在 workspace 执行 lk serve, THE 系统 SHALL 检查 Louke、依赖、配置、模型、OpenCode 和 workspace 身份，并在必要时进入可预览、可确认、可恢复的 Workspace Setup`
- 来源: 快乐路径
- 说明: 已有效 setup 的 workspace 直接进入请求入口；重复启动不重复创建资源。

### BS-02 Setup 冲突由 Human 裁决
- EARS: `IF setup 所需值缺失、冲突或需要授权, THE 系统 SHALL 展示候选值及来源并等待 Human 决定，且在确认前不执行对应外部修改`
- 来源: 边界条件
- 说明: Runtime 可推导事实，但不能静默替用户选择冲突身份或授权。

### BS-03 单活跃 Release 与 Backlog
- EARS: `WHEN 用户创建新 release AND 当前仍有活跃主开发, THE 系统 SHALL 将请求保存到 Backlog、展示原因并结束本次创建会话，而不进入 M-STORY`
- 来源: `flow.md` M-START
- 说明: 避免两个主 release 同时争用 workspace、分支和文档权威。

### BS-04 新 Release 基线与初始 Story
- EARS: `WHEN 新 release 请求可开始, THE 系统 SHALL 确认既有开发已合回 main，创建或复用本次 release 必要资源和 Spec 目录，把用户原始设想写入 story.md 并形成可追溯 revision`
- 来源: 快乐路径
- 说明: 初始化完成后直接打开 Story 编辑页；中断重试不得重复创建资源。

### BS-05 Scribe 初步调查与分流建议
- EARS: `WHEN M-STORY 开始, THE 系统 SHALL 在 Story 文档只读期间启动 Scribe 对话，使其先调查当前请求、更新 Story 并向 Human 提出 Go/Park/No-Go 建议`
- 来源: `flow.md` M-STORY
- 说明: Scribe 只提供建议，不能替 Human 作出分流决定。

### BS-06 Story 分流与完成
- EARS: `WHEN Human 裁决 Story 为 Park 或 No-Go, THE 系统 SHALL 将 Story 及决定保存到 Backlog、清理本次未使用的本地开发分支并结束会话；WHEN Human 裁决为 Go, THE 系统 SHALL 让 Scribe 继续访谈并完成 Story，保存后才进入独立评审`
- 来源: `flow.md` M-STORY
- 说明: Scribe 退出访谈前必须保存 Story；Runtime 不接受没有文档变更的“已完成”声明。

### BS-07 文档单写者与 Revision 一致性
- EARS: `WHILE Human、author Agent 与 reviewer Agent 围绕同一文档协作, THE 系统 SHALL 保证任一时刻只有一个获授权写者，并使每次保存和评审绑定当前文档 revision`
- 来源: 风险应对
- 说明: 未获写权的修改不得覆盖已接受内容；违规写者应收到通知并基于最新 revision 重读。

### BS-08 Story 双方独立评审
- EARS: `WHEN Scribe 初稿已提交, THE 系统 SHALL 同时向 Human 开放评审并启动独立 Sage review，分别保存双方针对同一 Story revision 的意见和结论`
- 来源: 快乐路径
- 说明: Human 可直接编辑或使用 inline discussion；有编辑时不能把本轮误报为“无意见”。

### BS-09 多轮评审与会话延续
- EARS: `IF Human 或独立 reviewer 未通过当前 revision, THE 系统 SHALL 让 author Agent 响应意见、提交新 revision 并开始下一轮评审，同时延续各 Agent 的任务上下文`
- 来源: `flow.md` M-STORY/M-SPEC
- 说明: 从第二轮起，Web 可持续向 Human 开放，只在 Agent 实际写入期间短暂收回写权。

### BS-10 Spec 起草与评审
- EARS: `WHEN Story review 通过, THE 系统 SHALL 打开 spec.md、让 Sage 继承已确认的 Story 上下文起草 Spec，并在起草完成前保持 Human 只读；随后由 Human 与 Lex 独立评审直到语义和格式均通过`
- 来源: 快乐路径
- 说明: Runtime 负责轮次、revision 和写权；Sage 负责响应意见，Lex 不直接取代 author 改稿。

### BS-11 Human Review 明确信号
- EARS: `WHEN Human 完成一轮文档 review, THE 系统 SHALL 要求其明确提交“有意见”或“无意见”；IF Human 已修改当前文档, THE 系统 SHALL 禁止其将该轮标记为“无意见”`
- 来源: `flow.md` M-STORY/M-SPEC
- 说明: 文档修改本身意味着当前轮需要重新评审，避免修改与通过信号冲突。

### BS-12 合法返回上游
- EARS: `WHEN Human 在 M-SPEC 或 M-ACC 确认发现上游需求问题, THE 系统 SHALL 将流程返回到合法的 M-STORY 或 M-SPEC 节点，并使受影响的下游 review 结论失效`
- 来源: `flow.md` M-SPEC
- 说明: Agent 可提出返回建议，但不能自行移动流程指针。

### BS-13 Acceptance 起草与评审
- EARS: `WHEN Spec 的语义和格式均通过, THE 系统 SHALL 打开 acceptance.md，让 Sage 继承当前需求上下文起草 Acceptance，并复用 Human 与 Lex 的独立多轮评审规则直到通过`
- 来源: 快乐路径
- 说明: Acceptance 必须基于已确认的 Story/Spec；上游变化后旧结论不得继续生效。

### BS-14 M-LOCK-1 与 Issue 创建
- EARS: `WHEN Story、Spec、Acceptance 均通过 review, THE 系统 SHALL 展示等待 Human 批准的 M-LOCK-1；WHEN Human 批准当前三件套, THE 系统 SHALL 将其锁定为只读，并按当前 Spec 幂等创建 GitHub Issues 和 release GitHub Project 关联`
- 来源: 快乐路径
- 说明: Human 批准前不得创建本次实现 Issues；Agent 不能代为批准。

### BS-15 中断恢复与副作用 Reconcile
- EARS: `WHEN Louke、浏览器、网络或 Agent 会话在任一步骤中断, THE 系统 SHALL 从已持久化的 run、文档 revision、review、write ownership、task/session 和外部操作记录恢复，并在重试前 reconcile 已发生的副作用`
- 来源: 风险应对
- 说明: 无法证明完成的操作保持未完成或需要关注，不得猜测为 PASS。

---

## 3. 竞品与边界 (Scope & Competition)

### 3.1 Adopt

本 Story 没有完全对应的直接竞品，以下参考代码评审、CI/CD 和协作文档产品的成熟边界：

1. [GitHub Pull Request / Required Review]: 评审结论必须绑定具体 revision，内容变化后旧批准失效，有助于避免 Sage、Lex 或 Human 审阅旧文档。
2. [CI/CD Pipeline]: 流程位置和外部副作用由程序记录并恢复，评论或 Agent 自述不能直接把阶段标记为完成。
3. [协作文档的 revision/CAS]: 保存前验证当前版本，冲突时显式处理而非最后写入者静默覆盖；Louke 在此基础上增加单写者约束以保持 Agent revision 与 Git 提交清晰。

### 3.2 Avoid

1. [自由并发编辑]: Human 与多个 Agent 同时写同一 Markdown 文件会造成内容覆盖、review 对象漂移和提交归属不清；本 Story 不采用无约束的实时共编。
2. [聊天记录充当流程状态]: 仅依靠 Agent session 记住轮次会在重启、压缩上下文或会话丢失后失真；Runtime 必须保存权威步骤和 revision。
3. [Reviewer 直接改稿并自批]: reviewer 同时成为 author 会削弱独立性；Sage/Lex 的 author/reviewer 边界和 Human 最终决定应保持清晰。

### 3.3 Out-of-Scope（明确不做）

- [ ] M-LOCK-1 和 Issue 创建之后的 Test Plan、Architecture、Interfaces、开发、测试、安全、发布与归档流程；它们由 v0.14 后续三个 Spec 承接。
- [ ] backlog 中的 bounded waiver、no-new-debt adoption、通用 lifecycle hooks 和任意阶段 return-upstream 完整模型。
- [ ] 单个 Spec 的 30 条 FR/NFR 拆分门禁及父子 Story 治理；本 Story 只处理 `flow.md` 所定义的需求工作流。
- [ ] v0.13 active run 到 v0.14 run 的状态迁移、双版本共存或兼容桥。
- [ ] 通过 CLI 命令推进 M-STORY、M-SPEC、M-ACC 或 M-LOCK-1。
- [ ] 多用户同时登录、多人共同审批、移动端和完整离线模式。
- [ ] 重做 Workbench 整体视觉系统、通用协作文档平台或任意文件的锁服务。
- [ ] Agent 自动替 Human 作出 Go/Park/No-Go、上游返回或 M-LOCK-1 批准。

### 3.4 约束条件

- **技术约束**：复用现有 Python Runtime、Starlette Web、SQLite WorkflowRun store、Web Workbench、Markdown 文档、Git/GitHub 和 OpenCode 集成方向；Runtime 是步骤、写权、revision、提交和外部副作用的唯一协调者。任何 Agent 只能在获授权范围内撰写或评审，不能直接批准门禁或改变流程位置。持久化不能只依赖浏览器内存、进程内单例或 Agent transcript。
- **组织约束**：v0.14 分四个 Spec 交付，本 Story 是第一个边界；必须先形成从安装后产品公开入口到 M-LOCK-1/Issues 的可重复产品旅程，才能把后续设计与开发阶段接入该工作流。无额外法务或预算约束。

---

## 4. 风险与假设 (Risk & Assumption)

### 4.1 关键假设

### A-01
- 假设: 现有 WorkflowRun、gate、attempt 和 SQLite 持久化原语可以扩展为本 Story 的生产 Driver，而不需要推翻 v0.12 Runtime。
- 验证: 用完整节点定义做纵向原型，覆盖一次 M-STORY 多轮评审、服务重启和恢复。
- 负责人: 技术负责人

### A-02
- 假设: OpenCode 能按指定 Agent 建立并恢复多轮 session，使 Scribe/Sage/Lex 在 Runtime 保存 task 映射后继续原上下文。
- 验证: 在真实 OpenCode server 上验证创建、指定 Agent、消息返回、重启恢复、继续对话和会话丢失后的新 attempt 路径。
- 负责人: 技术负责人

### A-03
- 假设: 现有 Web Markdown 编辑器的 version token/CAS 能扩展为 Runtime 管理的单写者协议，并在不重做编辑器的前提下切换只读和可写状态。
- 验证: 实作 Human、Scribe、Sage/Lex 三方交错写入原型，验证冲突不覆盖、写权切换和页面实时刷新。
- 负责人: 前端负责人

### A-04
- 假设: 每轮文档 revision 可以由 Runtime 安全提交，且不会暂存、覆盖或回退 workspace 中与当前文档无关的用户修改。
- 验证: 在包含 staged、unstaged、untracked 和并发外部编辑的仓库中执行提交与违规写入恢复测试。
- 负责人: 技术负责人

### A-05
- 假设: GitHub release Project、branch 和 Issues 都能以稳定身份进行查询与 reconcile，使网络中断后的重试不会重复创建资源。
- 验证: 对每类外部操作注入请求超时、成功后本地未确认和权限失败，验证恢复后最多产生一个目标资源。
- 负责人: 测试负责人

### 4.2 主要风险

### R-01
- 风险: Human 与 Agent 的写权切换存在竞态，可能覆盖尚未保存的 Human 编辑，或让 reviewer 审阅旧 revision。
- 影响: 高
- 应对: 所有保存、锁申请、评审结果和提交绑定 version token/revision；切换写权前检测脏编辑并等待或明确阻塞。

### R-02
- 风险: 直接使用 Git 工作区“revert Agent 修改”可能误伤用户或其他进程的无关改动。
- 影响: 高
- 应对: Runtime 只处理受控文档和已记录基线之间的违规 patch，不执行全仓库回退；无法隔离来源时停止并请求 Human 处理。

### R-03
- 风险: OpenCode HTTP 调用超时不等于 Agent 已停止，立即重派可能产生重复 session、重复写入或两名 author 同时工作。
- 影响: 高
- 应对: task attempt 持久绑定 session 和 correlation identity；超时后先查询/reconcile，只有证明旧 attempt 终止或丢失后才新建 attempt。

### R-04
- 风险: 每轮自动 Git 提交遇到已有 staged/dirty 内容时，可能混入无关文件或使流程永久阻塞。
- 影响: 高
- 应对: 每次提交使用明确文件白名单和预期 digest；无关改动保持原样，当前文档来源不明确时显示可操作冲突而不是强行提交。

### R-05
- 风险: setup 或 M-START 在确认前后创建多个 Git/GitHub 资源，网络中断可能留下孤儿 Project、branch 或 Spec 目录。
- 影响: 中
- 应对: preview 与执行分离；每项操作具有稳定身份和 reconcile 路径，恢复时先查询已存在资源，再决定创建、复用或等待 Human。

### R-06
- 风险: “有意见/无意见”、直接修改和 inline discussion 三种 Human 信号若关系不清，可能让修改后的文档被错误判定为通过。
- 影响: 中
- 应对: 页面明确展示当前 revision、是否已编辑、未解决讨论和本轮结论；发生编辑时禁用“无意见”，新 revision 必须重新进入双方评审。

### R-07
- 风险: Story、Spec、Acceptance 的长轮次对话造成上下文膨胀，Agent 后续响应遗漏早期决定。
- 影响: 中
- 应对: 权威事实保存在当前文档、revision 和结构化 task 输入中；session 只提供连续对话体验，不能成为唯一事实来源。

---

## 5. 必要性与冲突 (Necessity & Conflict)

- **已实现？**：部分实现，但尚未形成目标旅程。现有代码已有项目 preview/confirm 和单活跃主项目检查（`louke/runtime/projects.py`）、WorkflowRun/gate/attempt 持久化原语（`louke/runtime/store.py`、`louke/runtime/gates.py`）、Web 文档 version token/CAS 保存（`louke/web/documents.py`、`louke/web/pages/workbench.py`）以及 OpenCode session/message/SSE adapter（`louke/opencode/real.py`）。当前项目 store 和默认 workflow 仍以进程内或最小演示装配为主，且没有完整 Driver、文档写权协议、Agent task/session 映射和从 M-STORY 到 Issue 创建的生产定义。
- **相抵触？**：否。本 Story 继承 v0.12 的 Runtime 权威边界、v0.13 的 Web Workbench/Chat/Dev Docs 和 v0.13.1 的安装体验。它从 backlog 中覆盖全生命周期的 v0.14 Workflow Reflow 草案切出“启动到需求三件套锁定与 Issue 创建”这一前置价值段，不把 backlog 的其余能力带入本 Spec。
- **结论**：分叉。以本 Story 作为 v0.14 四个 Spec 中的第一个独立范围；backlog 调研只作技术可行性和后续范围参考，不作为本 Story 的附加合同。

---

## 6. 方案疑议（A/B Advisory，非决策）

- **状态**：无异议。
- **建议**：N/A。`flow.md` 已明确用户入口、角色分工、评审循环和本 Story 终点；当前代码与调研未发现需要替换该产品方向的证据。
- **说明**：Agent 仅提示，不替用户做市场 / 产品判断，也不自动替换方案。

---

## 7. 分流结论与门禁 (Gate)

- **分流结论**：Go（Agent 建议）。用户场景、入口、价值、流程边界和技术验证路径均已明确；主要风险可通过 revision/CAS、单写者、task/session reconcile 和幂等外部操作控制。
- **Sage peer review**：Pending（本次仅产出 Story 主体，不执行评审流程）
- **绑定 Story digest**：待后续流程需要时生成
- **Human 确认**（仅决策点，Agent 已自检其余）：
  - [ ] 分流结论认同（Go / Park / No-Go）
  - [ ] 冲突 / A-B 建议已裁决（若 Agent 提出）
- **Backlog 登记**：Go 后进入本 release 的需求定义实现；Park/No-Go 时按 `flow.md` 保存 Story 和决定并结束当前会话。

---

## 8. 可追溯种子 (Traceability)

- **Story ID**：`STR-1402`
- **创建时间**：`2026-07-18T00:00:00+08:00`
- **关联 Issue（待填充）**：`#待创建`
- **关联 Spec ID（待填充）**：`v0.14-001-workflow-reflow-spec`
- **主要来源**：`.louke/project/specs/v0.14-001-workflow-reflow-spec/flow.md`
- **参考资料（非合同）**：`.louke/project/specs/backlog/`

---

*—— 本故事主体由 Scribe（M-STORY）于 2026-07-18 生成；后续是否进入 Spec 由 Human 决定。*
