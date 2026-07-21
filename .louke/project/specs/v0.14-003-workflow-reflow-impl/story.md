# STR-1404: 以可证明的 RGR、全量验证和可恢复发布完成宿主项目 Release

---

| Story ID | 创建时间 | 分流建议 |
| :--- | :--- | :--- |
| STR-1404 | 2026-07-19T00:00:00+08:00 | Go |

---

## 0. 原始输入

> 从 `M-IMPL` 开始梳理完整工作流。Runtime 驱动流程，Agent 只做语义评审或 coding。Archer 生成实施任务图，Devon 严格执行 Red → Green → Refactor，Shield 编写 integration/e2e，Prism/Judge 独立评审。Runtime 负责 commit、GitHub CI、状态、证据、发布和恢复。
>
> Red 阶段必须能够被证明和独立 review，但不应因为普通 pre-commit 预期失败而进入 release branch。已同意由 Runtime 创建 parent 为 task baseline、包含 test-only tree 的私有 Git checkpoint，并以 `refs/louke/rgr/{run}/{task}/{attempt}/red` 保活；Green 再形成 release branch 上的正式 commit。
>
> CI 必须运行宿主项目全部历史单元测试，并按当前 Test Plan 运行 required integration/e2e；GitHub Actions 是 Louke 当前强制支持的 CI。发布前必须验证真实 artifact 和安装后版本。

## 1. 用户意图

- **主要用户**：希望 Louke 接管宿主项目从技术设计到可验证发布全过程的项目维护者。
- **当前处境**：设计已经完成，但旧流程依赖 Maestro 或 Agent 自报状态；Red 没有稳定 Git 身份，Agent 可能自行 commit/push，局部测试可能掩盖历史回归，发布中断也缺少可靠恢复事实。
- **目标结果**：Runtime 以 task manifest 和程序门禁驱动各专业 Agent，留下不可伪造的 RGR lineage、全量测试/CI/安全证据，并经 Human 发布授权后幂等完成发布与归档。
- **成功信号**：每个发布结果都能从 FR/AC 追溯到任务、Red checkpoint、正式代码 commit、测试/CI、安全、artifact、公开版本和发布事实；失败或中断不会被误报为完成。

## 2. 核心操作路径

### 2.1 主路径

- **起点上下文**：当前 M-DESIGN revision 已通过程序校验与 Prism review，Runtime 已获得精确 implementation baseline。
- **入口/触发**：Runtime reconcile pre-commit 和工作区后进入 `M-IMPL`。

1. Archer 将设计拆成可独立验证的纵向 implementation task graph；Runtime 校验覆盖、依赖和 write scope，Prism 独立评审。
2. Runtime 为 ready task 建立 manifest 和单写者 lease。Devon 先只写测试；Runtime 验证合法 Red，创建私有 `R` commit/ref，并让 Prism 审查精确 `B..R`。
3. Red 通过后 Devon 编写最小实现；Runtime 运行目标测试和全部历史单元测试，创建通过正常 pre-commit 的正式 Green commit，再完成可选 Refactor 和最终 task review。
4. 所有 task 完成后，Shield 按 Test Plan 编写 integration/e2e，Prism 审查测试语义，Runtime 运行并按证据分流缺陷。
5. Runtime 冻结 candidate，执行全部本地质量链、历史回归、真实 build、artifact/version/install 验证和精确 commit 的 GitHub Actions required CI；Prism 做整体复审。
6. Runtime 执行程序安全扫描，Judge 对同一 candidate 做深度语义安全审查；修复必须重新经过受影响阶段。
7. Runtime 展示不可绕过的发布预览。Human 选择 Release 后，Runtime 按 operation ledger 执行 merge/tag/publish/release/smoke，并在中断后 reconcile 外部事实。
8. 发布验证成功后，Runtime 闭合 trace、归档 evidence、更新 Issues/Project，安全删除已经归档的私有 Red refs，完成里程碑。

- **继续/返回**：成功后进入历史只读状态并允许创建下一 release；技术缺口返回设计，实现或测试缺陷返回对应任务，产品缺口经 Human 返回需求阶段，发布不确定则保持 `needs_attention` 直至恢复。

### 2.2 行为种子

### BS-01 实现入口与 Pre-commit Reconcile

- EARS: `WHEN 当前设计 baseline 通过且工作区可归属, THE 系统 SHALL 按设计合同安装、更新并回读 pre-commit 后建立 implementation baseline。`
- 来源: flow.md §3
- 说明: 正式 commit 从第一笔实现起就在当前本地 gate 下产生。

### BS-02 可执行任务图

- EARS: `WHEN 进入 M-IMPL Planning, THE 系统 SHALL 由 Archer 形成覆盖全部 FR/AC、依赖和验证责任的纵向 task DAG，并由 Prism 独立评审。`
- 来源: flow.md §4
- 说明: GitHub requirement Issues 与 Runtime task graph 关联但不混同。

### BS-03 写入隔离与外部 Diff

- EARS: `WHILE task 获得写 lease, THE 系统 SHALL 只允许 manifest 授权范围被 Agent 修改，并识别 Human 或外部工具产生的额外 diff。`
- 来源: flow.md §5.1 / §13.2
- 说明: 不覆盖用户修改，也不让未归属变化进入证据。

### BS-04 合法 Red

- EARS: `WHEN Devon 提交 Red patch, THE 系统 SHALL 仅接受与当前 AC 对应的 test-only diff 和预期行为/精确缺失接口失败。`
- 来源: RGR 讨论 / flow.md §5.2
- 说明: 环境、fixture、依赖或无关编译错误不能伪装成 Red。

### BS-05 私有 Red Checkpoint

- EARS: `WHEN Red gate 通过, THE 系统 SHALL 创建 parent=B、tree=B+tests 的真实私有 commit R，并以 attempt-scoped ref 保活且不移动或 push release branch。`
- 来源: 已确认技术方案
- 说明: 让 Red 可恢复、可寻址、可由 Prism 精确 review。

### BS-06 独立 Red Review

- EARS: `WHEN R 已建立, THE 系统 SHALL 要求 Prism 对同一 R 及其失败证据 PASS 后才允许 Green。`
- 来源: flow.md §5.2
- 说明: Devon 自报 TDD 或测试失败不能替代独立证据。

### BS-07 Green 与测试不可弱化

- EARS: `WHEN 进入 Green, THE 系统 SHALL 恢复已评审 R 的精确测试 tree，并仅接受使其通过的最小实现；修改测试必须回到新 Red attempt。`
- 来源: flow.md §5.3
- 说明: 防止在实现阶段改写失败条件。

### BS-08 正式 Commit 与 RGR Lineage

- EARS: `WHEN Green checks 通过, THE 系统 SHALL 在 release branch 从 B 创建正常经过 pre-commit 的正式 G，并验证 B→R 为测试、R→G 默认仅为实现。`
- 来源: flow.md §5.3
- 说明: R 是旁支证据而非正式 ancestry，G 才进入发布历史。

### BS-09 Refactor 与最终 Task Review

- EARS: `WHEN Green 完成, THE 系统 SHALL 在测试保护下记录独立 Refactor commit 或 no-change evidence，并由 Prism 复审完整正式 range 与 RGR lineage。`
- 来源: flow.md §5.4-5.5
- 说明: 重构不得偷偷改变行为或设计。

### BS-10 Integration/E2E 闭包

- EARS: `WHEN 所有实现 task 完成, THE 系统 SHALL 由 Shield 按 Test Plan 编写 required integration/e2e，并由 Prism 审查、Runtime 执行和分流失败。`
- 来源: flow.md §6
- 说明: 用户旅程与跨模块行为必须在公开出口验证。

### BS-11 冻结 Candidate 与全量历史验证

- EARS: `WHEN 测试资产闭合, THE 系统 SHALL 冻结精确 candidate 并运行全部历史单元测试、required integration/e2e、静态检查、trace 和真实 build。`
- 来源: flow.md §7
- 说明: 当前 Spec 的局部测试不能替代产品整体回归。

### BS-12 GitHub Required CI

- EARS: `WHEN candidate 被 push, THE 系统 SHALL 只接受同一 commit 的 Louke CI / required 成功并回读分支规则后通过 CI gate。`
- 来源: flow.md §7.4
- 说明: Agent 转述、其它 commit 的绿色结果或非法 skip 均无效。

### BS-13 构建物与公开版本

- EARS: `WHEN 验证 release candidate, THE 系统 SHALL 构建全部 artifact、提取并比较 canonical version，并从适用安装/部署/运行出口再次确认。`
- 来源: flow.md §7.3
- 说明: 保证用户安装到的就是本次 release。

### BS-14 整体与安全复审

- EARS: `WHEN 本地和 CI gate 通过, THE 系统 SHALL 由 Prism 复审整体实现，再由 Runtime 与 Judge 对同一 candidate 完成程序和语义安全审查。`
- 来源: flow.md §7.5 / §8
- 说明: 局部 task review 不足以发现跨 task 漂移和深层安全问题。

### BS-15 Human 发布门禁

- EARS: `WHEN 全部不可 waiver gate 对同一 candidate PASS, THE 系统 SHALL 向 Human 展示绑定证据的发布预览，并仅在 Release 决定后执行外部副作用。`
- 来源: flow.md §9
- 说明: Human 决定发布时机，但不能用批准绕过技术失败。

### BS-16 幂等发布与失败恢复

- EARS: `WHEN 执行 merge/tag/publish/release/smoke, THE 系统 SHALL 以稳定 operation identity 先查询事实、记录结果并在中断后安全 reconcile。`
- 来源: flow.md §10
- 说明: 防止重复 tag、重复发布或不确定结果被误报完成。

### BS-17 Trace 闭环与 Red Ref 清理

- EARS: `WHEN 发布事实全部验证, THE 系统 SHALL 归档完整 trace/evidence 后只删除当前 run manifest 登记的私有 Red refs，并完成 Project/WorkflowRun。`
- 来源: flow.md §11
- 说明: 兼顾审计恢复与 Git 对象清理。

### BS-18 Hotfix 复用质量链

- EARS: `WHEN 已发布行为相对现有 Spec/AC 出现实现偏差, THE 系统 SHALL 在隔离 fix branch/worktree 中复用 RGR、全量验证、发布和归档链路。`
- 来源: flow.md §12
- 说明: 小修复不能跳过独立 review 和历史回归。

### BS-19 定义化返回、重试与 Waiver

- EARS: `WHEN 发现上游缺口、操作失败或政策允许例外, THE 系统 SHALL 只按 WorkflowDefinition 执行 return/retry/waiver/cancel，并传播 stale。`
- 来源: flow.md §13
- 说明: 客户端和 Agent 不能任意移动阶段或复用旧证据。

### BS-20 Agent 合同迁移

- EARS: `WHEN 本流程生效, THE 系统 SHALL 同步锁定 Archer、Devon、Shield、Prism、Judge、Librarian、Keeper 与 Maestro 的规范性提示词，使 Agent 只承担语义或 coding 职责。`
- 来源: flow.md §15 / prompt 规范决定
- 说明: Runtime 状态机与实际 Agent 指令必须一致。

## 3. 范围、约束与例外

### 3.1 必须保持的产品约束

- 本文中的项目均为使用 Louke 的宿主项目；测试、构建和 artifact 方案由当前宿主项目事实与设计决定。
- Runtime 是 commit/push、Git refs、阶段、program gates、GitHub、发布和证据的唯一 authority；Agent 不伪造这些结果。
- Human 不承担架构、测试、实现、安全修复或 CI 技术决定，但保留产品需求、授权、不可逆冲突和发布时机决定权。
- 普通 feature 使用当前 release branch 和串行单写者 lease；只有定义允许的 hotfix 使用隔离 branch/worktree。
- 私有 Red checkpoint 是必须保留至 evidence 安全归档的真实 Git commit，不进入正式发布 ancestry，也不 push。
- GitHub Actions required CI 与全部历史测试是不可省略的 release gate。

### 3.2 非常规要求

- Red 允许因已设计但尚未实现的 symbol/interface 产生精确 compile/type failure，以支持 Java、Go、Rust 等静态语言；无关编译错误仍是无效 Red。
- 普通 pre-commit 不运行于私有 Red checkpoint；它仍是所有正式 Green/Refactor/受控测试 commit 的强制本地 gate。

### 3.3 Out-of-Scope

- 本批次只定义 Story/Spec/Acceptance，不修改 Runtime、Agent prompts、GitHub workflow 或其它实现。
- 不引入 per-task feature branch、由 Agent 自行 commit/push 的兼容模式或第二个状态 authority。
- 不以本次新增测试替代历史测试，也不把非 GitHub CI provider 纳入早期强制支持范围。

## 4. 重要推导与证据

### D-01 Red 不应依赖普通 Commit Hook 证明

- **结论**：Red 的真实性由 test-only program gate、失败 fingerprint、私有 commit identity 和 Prism review 共同证明。
- **依据**：pre-commit 可以只包含格式、lint 等快速检查，并不必然因合法 Red 失败；反过来，某些 hook 可能运行全量测试而阻止记录 Red。
- **影响**：私有 checkpoint 绕开普通 formal-commit hook，但 Red 专用检查不能被省略。

### D-02 R 与 G 必须是兄弟关系

- **结论**：`R` 和 `G` 都以 `B` 为 parent；`R` 通过私有 ref 保活，`G` 进入 release branch。
- **依据**：既要保留测试先于实现的可审查身份，又不能把预期失败 commit 放进正式 release ancestry。
- **影响**：Runtime 必须用 tree/diff 证明 `B→R` 与 `R→G`，而不是仅检查提交顺序。

### D-03 CI 必须包含历史测试

- **结论**：所有历史 unit tests 以及当前 required integration/e2e 都属于 candidate gate。
- **依据**：CI 的职责是维护整个产品质量，不只是证明当前 Story 新增行为。
- **影响**：Test Plan 决定新增 AC 的测试层和新增用例，但不能删减已有有效回归集。

### D-04 Prompt 迁移是流程实现的一部分

- **结论**：只改 Runtime 而保留 Agent 自行推进、commit 或调用 Maestro 的旧提示词会形成冲突状态权威。
- **依据**：Agent 实际行为受已部署 prompt bundle 约束。
- **影响**：003 必须把下游 Agent prompt revision 与 Runtime 代码、schema、测试一起纳入同一实现 baseline 和验收范围。

## 5. 开放产品决定

无。具体宿主技术栈、测试命令、构建器、artifact 和发布 adapter 都由 002 的当前设计合同决定，不应在本 Story 中向 Human 提问。

## 6. 必要性、风险与分流建议

- **既有能力**：v0.12 已有 TDD、review、测试、安全和发布目标；当前代码已有部分 Runtime program/semantic responsibility、manifest 和 GitHub 能力。
- **冲突**：旧 Agent prompts 与部分命令仍可能由 Maestro/Agent 执行状态推进和 Git 副作用；现有 Red 证据不一定具备独立 commit identity。
- **重要风险**：私有 ref 若未做 compare-and-set、归档和精确清理会导致 attempt 混淆或证据丢失；全量 CI 与外部发布若不绑定 candidate 会错误复用绿色结果。
- **分流建议**：Go — 这是 v0.14 runtime 驱动工作流的核心实施与发布闭环。

## 7. 可追溯信息

- **Story ID**：`STR-1404`
- **创建时间**：`2026-07-19T00:00:00+08:00`
- **关联 Spec/Issue**：`v0.14-003-workflow-reflow-impl`；Issue 待 `M-REQ-APPROVAL` 后建立
- **Sage peer review**：`Pending`
