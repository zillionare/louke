# v0.14-001-workflow-reflow-spec — 流程速览

> Source of truth: 当前 `flow.md` 编辑中, 仅做执行权限与职责说明. 不写正式合同.

## 1. 安装与启动

- **触发**：Human 安装或升级 Louke，在目标 workspace 执行 `lk serve`。
- **Runtime**：检查 Louke 版本、依赖、配置、模型和 OpenCode 可用性，启动本地服务并打开 Web Workbench。
- **Agent**：不参与启动判定。
- **Human**：处理缺失依赖、登录、授权或模型配置。
- **产物**：可访问的 Web Workbench；启动诊断和当前 workspace 身份。
- **退出**：启动检查通过，进入 Workspace Setup；已经 setup 的 workspace 直接进入请求入口。
- **恢复**：重复执行 `lk serve` 不重复初始化资源；启动失败保留可操作错误。

## 2. Workspace Setup

- **触发**：首次打开 workspace，或现有 setup 信息缺失、冲突、失效。
- **Runtime**：从 Git remote、项目文件和认证身份推导项目名称、仓库、owner、版本等候选值并展示来源；在 Human 确认前不执行外部修改。
- **Agent**：不负责创建仓库、分支、Project、配置或判断 setup PASS。
- **Human**：只处理缺失值、冲突值和需要授权的操作，确认 setup preview。
- **产物**：项目配置、repository/release Project/branch 等必要资源，以及绑定其身份和状态的 foundation manifest。
- **退出**：所有必要资源真实存在、身份一致、当前 manifest 有效。
- **恢复**：每项操作可查询、可重试、可复用；重启或网络中断后先 reconcile，不能重复创建资源。

## M-START（创建新的 release）

1. **Human** 在工作台创建新的发布（当前实现为 /projects/new），填写一句话 story，版本号等信息
2. **Runtime** 判断是否有活跃开发还在进行中；如果是，加入 backlog，**本次会话结束**，不进入 M-STORY 阶段。
3. **Runtime** 检查分支是否已 merge 回 main（以便开始新分支时，能继承所有修改）
4. **Runtime** 完成 M-FOUNDATION 阶段工作（+创建新的 spec 目录）
5. **Runtime** 将 story 落盘（替换 templates/story.md 中第13行）并提交。
6. **Runtime** 重定向到 Story.md 编辑页面（如workbench?spec=v0.13-001-web-ui-foundation&doc=story）

## M-STORY

Scribe 创建 story 文档，人类与 Sage 共同完成评审。

1. **Runtime** 弹出对话窗口（小窗口，允许人类与 Scribe 就 spec 进行对话）
2. **Runtime** 设置网页端文档为不可编辑状态
3. **Scribe** 按<agent>.md 指令对 story 进行调查，更新 story.md文档，提出 GO/NO-GO/PARK 的建议 -- 通过对话
4. **Runtime** 及时刷新文档，仍保持网页端不可编辑。
5. **Human** 对 Scribe 的建议进行裁决，如果裁决为NO-GO/PARK，**Runtime** 将story 记入 backlog, 删除本地分支（此时应该只有一个 story.md 为脏状态）**本次会话结束**，不进入 M-SPEC 阶段。
6. **Scribe** 通过对话小窗口对人类发起 interview
7. **Scribe** 收集到足够信息，决定退出 intreview（确保 Story 已写盘）
8. **Runtime** 检查并确保 story.md有变更，否则提示 Scribe 写盘。
9. **Runtime** 提交Scribe 修改的 story
10. **Runtime** 开放网页端编辑权，通过消息提示 **human** 开始 review；并且启动 Sage，开始 peer review（提示他需要等待写权限）。
11. **Human** 进行review: 可直接修改文件，或者启动 inline-discussion。
12. **Human** 在网页上通过按钮表示『comment』（本轮 review 已完成，但有评论，不通过），或者『no comment』;一旦人类在网页上修改过，则『no comment』按钮应该 disable
13. **Runtime** 将human在网页上的修改写文件并提交。释放写锁给Sage，让他通过 diff 和 inline-discussion 工具查看变更和评论，发表自己的审核意见。如果**Runtime**在落盘 **Human**的变更时，发现 story 为脏状态，这应该是 Sage 未遵循约定，需要 revert **Sage**的修改，写入**Human**的变更，同时提示**Sage**文件已发生变化，他需要重读文件和生成评论意见。
14. **Runtime** 在**Human**完成本轮评论后，要求**Sage**将评论意见落盘，会话返回评审结论。
15. **Runtime** 将**Sage**的变更提交。此时第一轮评审结束。
16. **Runtime** 判断评审是否结束。如果人类和Sage 会话返回的结论都是通过，则评审结束，进入 M-SPEC-1；否则，进入下一轮评审。
17. **Runtime** 如果评审未结束，则交给 Scribe 响应，进入下一轮 Review; 在 Scribe 返回时，同样要对他的变更进行提交。

> **Aaron** 从第二轮 Review 起，Scribe, Sage 写文件前都要请求写锁，网页编辑权全程对人类开放，只在 Scribe/Sage 写的那一刻临时收回。
> **Aaron** Agent 的会话状态应该得到保留。

## M-SPEC

Sage 创建 spec 文档。人类和Lex 共同评审。

1. **Runtime** 将**Human**重定向到 spec.md 的编辑页面。
2. **Runtime** 启动 **Sage** 进行 spec 文档写作。Sage 应该继承上一轮 story review 的上下文。
3. **Runtime** 等待**Sage** 从会话返回。在此之前，不给**Human**开放网页编辑权限。
4. **Runtime** 在**Sage**返回之后，提交 spec 文档，对**Human**开放网页编辑权限; 同时启动**Lex**进行 review。
5. **Lex** 对spec 进行 review，通过 inline-discussion skill 发表评审意见。但在写文件之前，需要先从 runtime 处得到写锁。
6. **Human** 对 spec 进行 review，在网页端编辑、发表评论，通过『comment』,"no comment"按钮发表评论意见。一旦人类修改过文件，则『no comment』按钮应该 disabled。
7. **Runtime** 在人类提交意见后，将他的变更写盘并 commit，开放写锁给 **Lex**
8. **Runtime** 与**Lex**对话，要求他将评论写入文件。如果这一轮人类有发表意见，则还要他重新读取文件，重新生成意见。
9. **Runtime** 在**Lex**返回结论后，检查spec 是否有变更，有则提交。
10. **Runtime** 根据人类意见（coment/no comment）和 **Lex**结论，决定本轮语义评审是否结束。如果不能结束，在与**Sage**的对话中，要求他响应**Human**和**Lex**的评论，推动新一轮语义评审，直到循环结束。
11. **Runtime** 在语义评审结束后，进行格式验收。

> **Aaron:** 在评审时，可能出现要修改 Story 的情况，此时人类可以回拨流程指针到 M-STORY 阶段。

## M-ACC

在 spec 文档语义审查结束后，进入 Acceptance 阶段。

1. **Runtime** 将**Human** 重定向到 acceptance.md 的编辑页面。
2. **Runtime** 启动**Sage** 进行 acceptance.md 文档写作。**Sage**应该继承上一轮 M-SPEC的上下文。
3. **Runtime** 等待**Sage**从会话中返回。在此之前，不给**Human**开放网页编辑权限。
4. 重复 M-SPEC 中第4到第11步，只不过文档对象是 acceptance.md。
5. 本步骤结束后，重定向到 project/current 页面，进入 M-LOCK-1阶段。

## M-LOCK-1

在 story, spec, aceptance 都通过 review 之后，进入 M-LOCK-1阶段。

1. **Runtime** 网页端显示当前的 project 状态，流程指针指向 M-LOCK-1。在这个节点上，显示等待 approve 提示和按钮。
2. **Human** 点击『approve』按钮，锁定 story, spec, acceptance。
3. **Runtime** 将上述文档的网页编辑权收回，界面只读显示文档。
4. **Runtime** 对 spec 进行拆分，按格式要求创建对应的 github issue，并关联 github project.

<!-- 旧版候选（暂保留以便对照）

## M-SPEC-2

## 3. 工作请求路由

- **触发**：Human 在 Web Chat 提出新功能、缺陷修复，或选择一个 Backlog 条目继续考虑。
- **Runtime**：读取当前 active Project、已发布版本和 Backlog 状态，执行并发与来源规则。
- **Agent**：Triage Agent 从自然语言中提议 `new_feature` 或 `bug_fix`，给出理由；不创建 Project 或 WorkflowRun。
- **Human**：请求类型或目标版本不明确时确认分类；查看并确认 Project preview。
- **产物**：Backlog entry，或一个绑定类型、workspace、source、WorkflowDefinition 的新 Project/WorkflowRun。
- **退出**：有效 `new_feature`/`bug_fix` run 创建完成；若主 Project 已占用，则请求留在 Backlog，不创建第二个主 run。
- **恢复**：重复或并发确认最多创建一个 Project/WorkflowRun；失败的 preview 不消费 Backlog 条目。

## 4. Story 调研与撰写

- **触发**：`new_feature` run 创建完成；`bug_fix` 仅在无法继承已有批准需求时进入本节点。
- **Runtime**：创建 Scribe semantic task，传入原始请求、项目上下文和当前约束；持久化 task、session、问题和回答。
- **Scribe**：与 Human 多轮澄清用户、场景、问题、目标、主流程、范围和关键风险，撰写一份可独立理解的 Story；不写 Spec、Acceptance 或技术实现方案。
- **Human**：回答产品问题、纠正意图、决定范围。
- **产物**：`story.md` 初稿和仍未解决的问题。
- **退出**：Scribe 认为 Story 足以交给独立 reviewer，且没有被隐藏或默认回答的产品问题。
- **恢复**：Human 回答继续原 Scribe task；session 丢失时从已持久化 Story、问答和 manifest 创建新 attempt。

## 5. Story 评审与 Go/Park/No-Go

- **触发**：Story 初稿完成。
- **Runtime**：先检查文档存在、格式和 revision，再 dispatch 独立 Story reviewer；保存 review findings 和每轮 diff。
- **Sage**：只评审 Story 是否完整、连贯、忠于原始请求并足以进入需求定义；不重做 discovery，不直接改写 Story。
- **Scribe**：根据已确认反馈修订 Story。
- **Human**：通过 inline discussion 处理分歧；最终选择 Go、Park 或 No-Go。
- **产物**：通过独立评审的 Story digest，以及 Human 决定。
- **退出**：Go 进入 M-FOUND；Park/No-Go 写入 Backlog/history 并结束当前 run。
- **恢复**：Story 内容变化使旧 review 失效；未完成讨论和 Human 决定在重启后继续可见。

## 6. M-FOUND 基线就绪

- **触发**：Human 对当前 Story 选择 Go。
- **Runtime**：以 program checks 验证 repository、release Project、配置、身份、Story/review digest、WorkflowDefinition、Agent contracts、main 和其它分支是否形成可开发的唯一权威基线。
- **Agent**：不判断 M-FOUND PASS，不执行确定性修复。
- **Human**：确认具有风险的修复、授权和分支保留/合并决定。
- **产物**：绑定当前输入 revision 的 foundation evidence。
- **退出**：所有 blocking checks 当前有效且 PASS，main 成为明确开发基线。
- **恢复**：外部状态变化使相关 evidence stale；重启后从未完成 check/operation 继续，不重复已完成副作用。

## 7. Spec 起草与评审

- **触发**：M-FOUND PASS。
- **Runtime**：冻结本轮 Story digest，dispatch Sage 起草 Spec；执行编号、格式、来源、覆盖和双向 trace 等确定性检查，维护 inline discussion 状态和 revision。
- **Sage**：将 Story 转成可断言的 FR/NFR；只描述产品必须具备的行为和约束，不改写 Story，不提前生成 Acceptance。
- **Lex**：在 Spec 草稿完整后独立检查语义、覆盖、边界和可断言性；只给 findings，不直接改稿。
- **Human**：通过 inline discussion 确认需求含义、优先级和边界。
- **产物**：绑定当前 Story 的 `spec.md`。
- **退出**：Story/Spec 内容冻结；无未解决 discussion；确定性检查和独立语义评审通过。
- **恢复**：发现产品缺口时返回 Story 节点；Story 变化后旧 Spec review 全部 stale，重新评审当前 revision。

## 8. Acceptance 生成与校验

- **触发**：Story 和 Spec 已冻结。
- **Runtime**：只在冻结输入上 dispatch 一次 Acceptance 生成；随后执行结构、编号、FR/NFR 覆盖和双向 trace 检查。
- **Sage**：为每条需求生成外部可观察、可判定 PASS/FAIL 的 Acceptance Criteria，不引入新产品行为。
- **Scribe**：只读检查 Acceptance 是否忠于 Story。
- **Lex**：只读检查 Acceptance 是否覆盖 Spec 且语义可断言。
- **Prism**：只读检查 Acceptance 在技术上是否可实现、可测试。
- **Human**：确认 Acceptance 表达了真正想验收的行为。
- **产物**：绑定冻结 Story/Spec 的 `acceptance.md` 和 review findings。
- **退出**：所有检查通过，Human 没有未解决异议，需求三件套冻结。
- **恢复**：任何 finding 若要求修改 Story/Spec，则返回对应节点；Acceptance 作废并在上游重新冻结后重新生成，不在旧输入上反复补丁。

## 9. Requirements Approval

- **触发**：Story、Spec、Acceptance 全部冻结并通过检查。
- **Runtime**：展示三份文档的摘要、diff、review 结果和共同 digest；只接受 Human 的显式决定。
- **Agent**：不能批准、拒绝或代替 Human 回答。
- **Human**：批准，或指定返回 Story/Spec/Acceptance 的原因。
- **产物**：绑定三件套 digest、actor 和时间的 requirements approval。
- **退出**：批准后进入 Test Plan；拒绝则返回指定上游节点。
- **恢复**：三件套任一内容变化立即使 approval stale；重启不丢失待审批状态。

## 10. Test Plan

- **触发**：Requirements Approval 有效。
- **Runtime**：dispatch Archer，提供冻结需求三件套和项目测试能力；执行结构和 trace 检查，保存 review/revision。
- **Archer**：把 Acceptance 转成分层测试策略，定义 unit、integration、E2E、安全和失败路径的验证责任，不写生产代码。
- **Prism**：独立评审测试策略、风险覆盖和可执行性。
- **Shield**：只读反馈后续 integration/E2E 是否能按计划实施，不承担批准权。
- **Human**：处理测试成本、风险覆盖和明确的取舍。
- **产物**：`test-plan.md`。
- **退出**：Acceptance 全部有测试去向，独立评审通过，无未解决讨论。
- **恢复**：需求缺口返回需求节点；仅测试策略问题留在本节点修订。

## 11. Architecture 与 Interfaces

- **触发**：Test Plan 稳定。
- **Runtime**：dispatch Architecture author，提供冻结需求、Acceptance、Test Plan 和代码库上下文；保存 revision、检查 trace，并 dispatch 独立 reviewer。
- **Archer**：设计组件边界、数据和状态模型、Runtime/Agent/Human authority、接口、错误、幂等、恢复和迁移策略；不修改已批准产品需求。
- **Prism**：独立评审技术正确性、复杂度、可维护性和与 Test Plan 的一致性。
- **Human**：参与重大技术取舍，决定成本、兼容性和长期约束。
- **产物**：`architecture.md` 和 `interfaces.md`。
- **退出**：设计覆盖全部需求和测试需要，接口可实现，独立评审通过，无未解决讨论。
- **恢复**：产品行为变化返回需求节点；测试策略变化返回 Test Plan；纯设计问题留在本节点修订。

## 12. M-LOCK

- **触发**：需求三件套、Test Plan、Architecture、Interfaces 全部通过评审。
- **Runtime**：展示六件套摘要、trace、未决项和共同 contract digest；检查所有输入 freshness。
- **Agent**：不能创建或批准 M-LOCK。
- **Human**：确认设计可以进入实现，或指定返回上游的节点和原因。
- **产物**：绑定六件套 digest、actor 和时间的 M-LOCK。
- **退出**：M-LOCK 有效后才允许创建实现任务、Issue、worktree 或生产代码。
- **恢复**：六件套任一内容变化使 M-LOCK stale，并阻止新的实现工作继续进入。

## 13. Issue 与实现任务拆分

- **触发**：M-LOCK 有效。
- **Runtime**：dispatch planning semantic task；验证每个任务的需求/AC trace、依赖、工作范围和完成条件；确认后幂等创建 GitHub Issues 和 Runtime tasks。
- **Planning Agent**：按可独立实现和验证的增量提出任务拆分、顺序和依赖，不改变锁定合同。
- **Human**：只处理拆分边界、优先级或并行策略的歧义。
- **产物**：带 Spec/AC/test trace 的 Issues、任务图和执行顺序。
- **退出**：每个锁定需求都有实现归属，每个任务有明确输入、输出和验证方式，无重复或无主任务。
- **恢复**：重复执行 reconcile 已有 Issue；拆分暴露合同缺口时返回上游并使 M-LOCK stale。

## 14. M-DEV 实现循环

- **触发**：某个实现任务的依赖已完成，且 M-LOCK 仍有效。
- **Runtime**：创建隔离 branch/worktree，dispatch Devon；按 Red-Green-Refactor 顺序运行权威 program checks，记录 diff、测试证据和 trace，并控制 commit。
- **Devon**：先写失败测试，再做最小实现使其通过，最后重构；只修改任务声明范围，不自行宣称测试或任务 PASS。
- **Prism**：在 program checks 通过后独立评审正确性、设计一致性和回归风险。
- **Human**：只处理新出现的产品歧义、重大设计偏离或不可自动决定的风险。
- **产物**：代码、测试、受控 commit、Issue/AC/commit trace 和 review 结果。
- **退出**：任务范围内测试和质量检查通过，review findings 关闭，Runtime 标记任务完成。
- **恢复**：失败留在同一任务循环；发现上游合同错误则停止实现、保留工作和证据并 return-upstream。

## 15. 集成、E2E 与安全验证

- **触发**：本轮所有实现任务完成并集成到候选分支。
- **Runtime**：构建安装产物，在干净环境执行 unit、integration、installed-wheel E2E、兼容性、文档和安全 program checks，汇总权威证据。
- **Shield**：按 Test Plan 编写或补全 integration/E2E 测试，不修改产品合同来迎合实现。
- **Judge**：进行一次独立安全审计，输出按严重度排序的 findings。
- **Prism**：检查整体实现与 Architecture、Interfaces、Test Plan 的一致性。
- **Human**：决定非关键残余风险是否接受；不可 waiver 的安全、身份、trace 和 freshness 问题必须修复。
- **产物**：release candidate、完整测试/安全/review evidence 和残余风险列表。
- **退出**：所有 blocking checks PASS，无 stale artifact，无未处理的 blocking finding。
- **恢复**：实现缺陷返回对应 M-DEV 任务；设计或需求缺陷 return-upstream，并使受影响下游结果 stale。

## 16. Release Confirmation

- **触发**：Release candidate 通过全部权威验证。
- **Runtime**：展示版本、变更、需求覆盖、Issues、commits、测试、安全、文档、已知风险和发布操作 preview。
- **Agent**：可以总结 release evidence，但不能确认发布。
- **Human**：选择 Release、Delay 或 Return Upstream。
- **产物**：绑定 release candidate digest、evidence set、actor 和时间的发布决定。
- **退出**：Release 进入发布执行；Delay 保持候选状态；Return Upstream 返回指定节点。
- **恢复**：候选代码或 evidence 变化使旧确认失效；重启后仍等待同一 Human 决定。

## 17. 发布与归档

- **触发**：Human 对当前 release candidate 明确选择 Release。
- **Runtime**：按顺序 reconcile/执行最终 merge、push、tag、release、版本记录、Project/Issue 收尾和历史归档；每个外部操作都有幂等身份。
- **Agent**：不执行或批准发布副作用。
- **Human**：只处理权限失败、外部冲突或不可逆异常。
- **产物**：可验证的发布版本、tag/release URL、最终 trace/evidence graph 和只读历史 run。
- **退出**：所有发布操作被证明成功，Project/WorkflowRun 标记完成，workspace 可接受下一个主 Project。
- **恢复**：中断后逐项查询外部状态再继续；不能确定的操作进入 `needs_attention`，不得重复发布或伪造成功。

## 18. 任意节点的等待、恢复与返回上游

- **Runtime authority**：只有 Runtime 可以改变 WorkflowRun、当前节点、gate、task 状态和 program result；Agent/Human 输入只能触发 Runtime 校验后的合法操作。
- **等待 Human**：缺少产品决定、授权或风险确认时持久化 `waiting_human`；不默认回答、不消耗评审轮次、不自动推进。
- **Agent session**：Runtime 持久化 semantic task 与 OpenCode parent/child session 映射；多轮继续原 task，结果必须经过 schema、identity、digest 和 artifact 校验。
- **重启恢复**：Runtime 先从自己的 store 恢复 run，再 reconcile Agent session、workspace 和外部资源；状态不明时不 PASS、不盲目重试。
- **Return Upstream**：Human 或下游 reviewer 可以提出返回原因和目标；Runtime 只允许 WorkflowDefinition 声明的目标，并把目标之后的 artifact、review、approval、lock 和 evidence 标记 stale/superseded，保留历史。
- **Waiver**：只适用于明确标记为可 waiver 的非关键检查，必须记录 actor、理由、范围和绑定 revision；需求批准、M-LOCK、身份/权限、安全关键项、CAS、freshness、trace 和 Agent 自批不可 waiver。
-->
