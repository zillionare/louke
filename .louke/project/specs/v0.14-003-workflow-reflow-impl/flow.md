# v0.14-003-workflow-reflow-impl — 流程速览

> 状态：Review Draft。本文只梳理流程、职责、阶段边界和返回路径，不是正式 Spec。
>
> 范围：承接 v0.14-002 的 `M-DESIGN`。从当前设计 revision 通过 Prism 评审与 Runtime 程序校验、Runtime 准备进入 `M-IMPL` 开始，到构建物发布、里程碑归档结束。
>
> 本文中的“项目”均指安装并使用 Louke 的宿主项目；宿主项目采用什么语言、构建工具、测试框架和 artifact 类型，只能由该项目当前有效的需求/设计 baseline 与真实代码库决定。

## 1. 不变量

1. **Runtime 是唯一流程 authority**：只有 Runtime 可以创建/推进/回拨阶段，授予写权限，持久化 task/review/gate/evidence，执行 commit/push、GitHub API、CI、发布和归档副作用。
2. **Agent 只产出专业语义或代码**：Archer 产出实施计划，Devon 编写单元测试与实现，Shield 编写集成/e2e 测试，Prism/Judge 评审。Agent 不 commit/push、不写 PASS artifact、不改变 Issue/Project/WorkflowRun 状态。
3. **Human 不承担技术决策**：Human 可以主动评论或修改，但 Agent 不把架构、测试、实现、CI 或修复方案作为选择题推给 Human。只有产品意图、需求范围、发布时机、权限/授权和不可逆外部冲突需要 Human 决定。
4. **技术设计可以按流程修订**：从 `M-IMPL` 到 `M-SECURITY`，任何 Agent 都可以返回有锚点的 design-gap advisory。Runtime 交由 Archer 与 Prism 裁定；两者都确认有效时直接返回 `M-DESIGN`，不要求 Human 批准。涉及产品意图或需求范围时才返回 `M-SPEC`/`M-ACC` 并重新经过 Human 决策边界。
5. **所有结果绑定身份**：task、diff、review、test、CI run、artifact、security finding 和 release gate 都必须绑定当前 baseline digest、代码 commit、attempt 和 actor；上游变化使受影响结果 stale。
6. **Agent 自报不是证据**：`tests passed`、`review pass`、`done`、命令输出摘要或聊天文本不能推进阶段；Runtime 必须从权威程序出口重新执行或读取证据。
7. **实现发生在当前 release branch**：普通 feature 不创建 per-task branch/worktree；Runtime 串行授予单写者 lease。只有 definition 明确允许与主 release 并行的 hotfix，才由 Runtime 创建隔离的 `fix/{issue-number}` 与 worktree。
8. **失败不伪报成功**：失败、取消、超时、缺失、skip、结果不确定或外部状态无法确认时，不得标记 PASS、完成或已发布。

## 2. 阶段总览

安装与 Workspace Setup 是 release workflow 的前置条件，不是每个 release 的持久化阶段。全流程 canonical stage identity 与顺序固定为：

`M-START → M-STORY → M-SPEC → M-ACC → M-REQ-APPROVAL → M-DESIGN → M-IMPL → M-TEST → M-VERIFY → M-SECURITY → M-RELEASE → M-PUBLISH → M-MILESTONE`

| 阶段 | 主要作者/执行者 | 语义评审或 Human 参与 | Runtime 权威退出条件 |
|---|---|---|---|
| `M-START` | Runtime 建立 release foundation | Human 发起并确认产品请求 | release/run/branch/spec 资源身份一致且可恢复 |
| `M-STORY` | Scribe 调研并撰写 Story | Sage 独立评审；Human 回答产品问题并 review | 当前 Story revision 的 review/discussion 闭合，Human 作出 Go |
| `M-SPEC` | Sage 撰写 Spec | Lex 独立评审；Human review 产品需求 | 当前 Spec revision 的语义与程序校验通过 |
| `M-ACC` | Sage 撰写 Acceptance | Lex 独立评审；Human review 可观察结果 | 当前 Acceptance revision 的覆盖与程序校验通过 |
| `M-REQ-APPROVAL` | Runtime 生成需求 baseline preview | **Human 决定 Approve/Return** | Human approval 绑定当前 Story/Spec/Acceptance digests；随后 reconcile requirement Issues |
| `M-DESIGN` | Archer 撰写 Test Plan、Architecture、Interfaces 及 integration/e2e、CI、pre-commit、release machine contracts | Prism 独立评审；Human 是允许缺席的可选 reviewer | 当前设计 revisions 的 Prism review 与程序校验通过；不等待 Human 批准 |
| `M-IMPL` | Archer 制定 implementation task graph；Devon 按 task 执行 Red → Green → Refactor | Prism 分别评审 Red checkpoint 与最终 task range | task graph、RGR lineage、单元测试、pre-commit、静态检查及 diff/trace gate 通过 |
| `M-TEST` | Shield 编写 integration/e2e 测试 | Prism | Runtime integration/e2e 与覆盖闭包 gate 通过 |
| `M-VERIFY` | Runtime 冻结 release candidate | Prism 做整体一致性复审 | 本地全量回归、GitHub CI、build/artifact/version gate 通过 |
| `M-SECURITY` | Runtime 执行程序扫描；Judge 深度语义审查 | Judge | 当前 candidate 的 security policy/findings gate 通过 |
| `M-RELEASE` | Runtime 生成发布预览 | **Human 决定 Release/Delay/Return** | Human release approval 绑定当前 candidate/evidence/artifacts |
| `M-PUBLISH` | Runtime 执行发布副作用 | — | 幂等外部操作及发布后验证完成 |
| `M-MILESTONE` | Runtime 收尾；Librarian 可做知识提炼 | — | trace 闭包、归档和资源清理完成 |

`M-REQ-APPROVAL` 与 `M-RELEASE` 是仅有的、专门作为 Human gate 存在的 stage identity：前者批准需求 baseline，后者授权发布副作用。Human 在 M-START/M-STORY/文档 review 中仍可作产品决定，但不因此增加新的 gate stage。表中的 13 个名称是 WorkflowDefinition 可持久化的完整 stage identity 集合；Planning、Red、Green、Refactor 和 task attempt 是 `M-IMPL` 内部状态，不得再作为同级 stage identity。

旧 `M-E2E` 的职责并入 `M-TEST`，因为 Shield 同时负责 integration 与 e2e；设计后的第二个 `M-LOCK` 被取消；旧 Keeper Agent 不再是节点，确定性质量检查属于 Runtime program gate。

## 3. M-IMPL 入口

1. **触发**：`M-DESIGN` 的当前 Test Plan、Architecture、Interfaces 和 machine contracts 已通过 Prism 评审与 Runtime 程序校验。
2. **Runtime** 重新计算并核对以下输入：
   - Story、Spec、Acceptance、Test Plan、Architecture、Interfaces 的 revision/digest；
   - Archer 写入或要求实现的 integration/e2e/CI/pre-commit/release-version machine contracts；
   - requirements Issue manifest、release Project、目标 release branch 和 canonical release identity；
   - `M-REQ-APPROVAL` identity、Prism 对当前设计 baseline 的 PASS，以及全部 closed discussions。
3. Runtime 按 pre-commit contract reconcile 宿主项目配置和本地 hook 安装，保留并合并既有 hooks，再回读确认实际入口、版本和配置 digest。配置文件需要变化时，Runtime 通过受控 adapter 创建独立 infrastructure commit 并据此更新 baseline；`.git/hooks` 等本地安装副作用只记录 identity，不纳入代码 commit。Archer 负责 contract，Runtime 负责安装/更新副作用；Devon 不安装或修改 hook 来绕过门禁。
4. 任一输入缺失、stale、冲突、pre-commit 无法按 contract 生效或工作区包含未归属修改时，Runtime 不 dispatch 实现 Agent，进入 `needs_attention` 或返回对应上游。
5. **Human** 不需要再次确认技术细节；Human 在 M-DESIGN 的意见由 Archer 判断如何处理，Human 缺席也不阻塞进入实现。
6. **产物**：revision-bound implementation baseline，包括 requirements/design digests、baseline commit、release identity、Issue manifest、project-local machine contracts 和已回读的 pre-commit installation identity。它不是永久锁；合法上游修订会产生新 baseline，并使依赖旧 baseline 的结果 stale。
7. **退出**：implementation baseline 完整、current 且可追溯，进入 `M-IMPL` 的 Planning 步骤。

## 4. M-IMPL / Planning（实施切片与任务图）

### 4.1 初稿

1. **Runtime** dispatch Archer 的 implementation-planning task，传入当前 requirements/design baseline、Issue manifest、代码库 baseline、模块依赖、测试层分配和 pre-commit/CI/release 合同。
2. **Archer** 自主形成实施切片，不向 Human 询问技术顺序。每个 task 至少包含：
   - task identity、对应 requirement Issue、FR/NFR 与 AC；
   - 目标用户结果或技术闭包；
   - 前置依赖、允许写入范围和禁止触碰范围；
   - Devon 应完成的 unit/contract test 与实现责任；
   - Shield 后续应完成的 integration/e2e 责任；
   - 适用的 pre-commit/CI workflow、build、artifact/version 或迁移责任；
   - 完成条件和可观察出口。
3. task 应按可独立验证的纵向切片组织；不得简单按文件层、前端/后端层或 Agent 方便程度拆分，也不得把一个 AC 拆成无人负责的碎片。
4. `M-REQ-APPROVAL` 后建立的 GitHub Issues 是 requirement 追踪身份，不自动等同于一个代码 commit。一个 Issue 可以映射多个 Runtime task，但每个 task 必须反向链接唯一的责任集合。
5. implementation task graph 是 Runtime 持久化的内部执行 DAG，不是 GitHub Project，也不是复制一批 GitHub Issues。GitHub Project/Issues 面向需求与发布追踪；task graph 面向 Agent dispatch、依赖、write scope、attempt 和程序门禁。Runtime 维护两者映射。

### 4.2 Review 与程序校验

1. **Runtime** 保存 implementation task graph revision/digest，执行确定性检查：ID 唯一、DAG 无环、依赖存在、write scope 不冲突、所有有效 requirement/AC 有实现和验证去向、没有 orphan task。
2. **Prism** 独立评审切片是否可实施、可测试、符合 Architecture/Interfaces、没有技术职责空洞或不必要耦合。
3. Prism REVISE 时，Runtime 把 findings 交回 Archer；Archer 修改 implementation task graph。需要改变设计时走 `M-DESIGN` revision，不在 task graph 中隐藏设计变化。
4. 如果规划暴露接口、测试策略或架构缺口，Archer/Prism 返回有锚点的 upstream gap；两者确认有效后 Runtime 直接回到 `M-DESIGN`。如果暴露产品需求缺口，则 Runtime 请求 Human 确认返回 `M-SPEC`/`M-ACC`。两类返回都使受影响的 baseline 及其下游结果 stale。不得让 Devon 临场补设计。
5. **退出**：implementation task graph 的 program checks 与 Prism review 均绑定当前 requirements/design baseline 并 PASS，进入 `M-IMPL` 的逐 task RGR 循环。

实施中可以重排尚未开始的 task 或细化 write scope，但必须产生新 implementation task graph revision 并重新通过上述校验/review；只要不改变产品需求，不需要向 Human 请求技术批准。

## 5. M-IMPL / RGR（逐 task 的 TDD 实现循环）

Runtime 按依赖选择 ready task；普通 feature 在 release branch 上一次只运行一个可写 task。

### 5.1 Task manifest 与写入隔离

1. **Runtime** 为当前 task 创建 manifest：baseline commit、Issue/FR/AC、当前设计引用、phase、write scope、测试命令、禁止路径、当前 Human/external diff 和 output contract。
2. Runtime 授予 Devon 单写者 lease；其它 Agent 与 Web 代码编辑保持只读。
3. **Devon** 只能编辑 manifest 授权的宿主项目代码、unit test、文档或 CI 实现文件。它不修改需求/设计 artifact、task 状态、Git history 或 GitHub Issue。

### 5.2 Red

1. Runtime 以 `phase=red` dispatch 或恢复当前 Devon task。
2. **Devon** 只添加能够证明本 task 缺失行为的 unit/contract test，不修改产品代码、既有正确预期或流程状态；CI 实现 task 可以添加证明 workflow 缺失、漂移或失败传播错误的确定性合同测试。
3. **Runtime** 以 task baseline commit `B` 校验 test-only diff，并执行 Red 专用 program gate：
   - format、测试源码语法、secret、AC trace、测试反模式及适用于 Red 的 static checks 通过；
   - 新测试产生与当前 requirement/interface 精确对应的预期失败；行为断言失败，或静态语言中因尚未实现的已设计 symbol/interface 产生的精确 compile/type failure，都可以是合法 Red；
   - 依赖、fixture、端口、权限、环境、无关语法或未声明 compile error 不得作为 Red；
   - 测试不是通过硬编码、私有实现细节、降低既有预期或制造无关失败得到；
   - baseline 的既有绿色 evidence 仍 current；runner 支持隔离时，除声明的 Red target/fingerprint 外不得出现其它新失败。
4. Red gate 通过后，Runtime 使用临时 Git index 创建 parent 为 `B`、tree 为 `B + test-only diff` 的真实 commit object `R`，并用 `refs/louke/rgr/{run}/{task}/{attempt}/red` 保活。该 ref：
   - 不移动 release branch、不进入正式历史、不 push，也不触发普通 pre-commit 或 GitHub CI；
   - 绑定 task、attempt、baseline、test command、expected failure fingerprint、输出 digest 和创建者；
   - 在对应 evidence 归档前不得删除，以保证重启恢复和 Git GC 安全。
5. **Runtime** dispatch Prism 评审精确的 `B..R` test-only diff、当前 requirement/Acceptance、测试层合同和 Red program evidence。Prism 检查测试是否忠于公开行为、确实先于实现、能证明缺失行为且没有伪 Red；verdict 绑定 `R` 和 evidence digest，由 Runtime 持久化。
6. Prism REVISE、测试已经通过、失败类型错误或 diff 越界时，Runtime 返回 Devon 的 Red correction attempt；任何修改都会创建新的 `R` identity，并使旧 Red review stale。
7. 只有 Red program gate 与 Prism review 对同一 `R` PASS，Runtime 才允许进入 Green。

### 5.3 Green

1. Runtime 从已通过评审的 `R` tree 恢复工作区，以同一 task/session dispatch `phase=green`；release branch 仍指向 `B`。
2. **Devon** 只编写使 Red 测试通过的最小实现。`R` 中的测试默认不可删除、弱化或改写；确需修正测试时必须返回 Red，生成新 checkpoint 并重新由 Prism 评审。
3. 若 task 含托管 GitHub CI，Devon 严格实现 Archer 当前设计 revision 中的 workflow、宿主命令、required check、权限、secret 和失败语义，不重新选择 CI 架构。
4. **Runtime** 独立执行：当前 targeted tests、宿主项目**全部历史单元测试**、适用的 lint/format/type/static checks，以及 task 声明的合同校验。
5. 任一历史单元测试失败都必须修复；不得因为它不属于当前 Spec 而跳过、改成 skip 或从 CI 中删除。
6. Green program checks 通过后，Runtime 在 release branch 上从 parent `B` 创建正式 Green commit `G`，其 tree 包含 `R` 的测试和最小实现，并在 evidence/commit trailers 中记录 Red checkpoint 与 task identity。该 commit 必须正常执行当前 pre-commit contract；不得使用 blanket `--no-verify`，hook 自动修改文件时必须重新校验 tree 和测试后再提交。
7. Runtime 验证 `B → R` 只有测试变化，`R → G` 默认只有实现变化，并保存 `B/R/G` lineage、测试结果和 pre-commit evidence。`R` 是私有旁支证据，不成为 `G` 的 parent。

### 5.4 Refactor

1. Runtime 从 `G` 继续同一 Devon task，允许在既有测试保护下消除重复、改善结构、命名和边界；没有必要重构时 Devon 可以返回 no-change 及理由。
2. Refactor 不得改变当前 requirements/design baseline 的外部行为，也不得弱化 `R` 中已评审的测试。Runtime 重新执行 Green 的全部 program checks。
3. 有实际变化时 Runtime 创建独立受控 Refactor commit，正常执行当前 pre-commit contract；无变化时记录绑定 `G` 的 no-change evidence。
4. 如果重构需要改变 public interface、数据语义、测试分层或架构，停止并 return upstream，不把它伪装成局部清理。

### 5.5 最终 Review 与 task 完成

1. Runtime 校验最终 task range：write scope、依赖策略、secret、生成文件、AC trace、测试反模式、未归属修改，以及 `B/R/G/(Refactor)` lineage 完整且 evidence current。
2. **Prism** 对当前 task 的完整正式 commit range 和 RGR lineage 做独立代码评审，检查正确性、设计一致性、测试真实性、可维护性、普通安全模式和 CI 实现一致性。
3. Prism REVISE 时回到 Devon correction attempt；实现/重构修复由 Runtime 重新执行受影响 checks 并创建受控 commit。若 finding 要求改变已评审 Red 测试，则必须回到 Red 并形成新的 `R/G` lineage。
4. Runtime program gate 最终确认：Red 测试先于实现、Red failure 有效且经 Prism PASS、Green 保留该测试并使其通过、正式 commits 全部通过 pre-commit、Refactor 未改变行为、Agent 未自行 commit/push。
5. Prism PASS 后，Runtime 记录 task implementation evidence并推进下一个 ready task。是否 push 正式 commit 由 Runtime policy 决定，但私有 Red refs 不 push。requirement Issue 此时可以标记“实现完成”，但在 integration/e2e、CI、artifact 和 release evidence 闭合前不作为 release-complete 关闭。
6. **退出**：task graph 中全部必需实现 task 完成、每个 task 都有 current RGR lineage 和最终 Prism PASS、没有 unresolved code finding、trace ledger 中不存在无人负责的实现 AC，进入 `M-TEST`。

## 6. M-TEST（Shield 编写 integration/e2e）

### 6.1 测试资产生成

1. **Runtime** 按当前 Test Plan 和 implementation task graph 创建 Shield tasks；输入包含每个 AC 的 observable interface、required layer、宿主测试框架、`[integration]`/`[e2e]` 合同、candidate baseline 和 write scope。
2. **Shield** 在 Archer 指定的宿主项目目录编写测试：
   - integration 覆盖所有被分配为 integration 的 AC、跨模块接口及关键错误传播；
   - e2e 覆盖被分配为 e2e 的公开主用户旅程；
   - 每个测试使用宿主框架支持的 metadata 或邻近注释追溯到 AC；
   - 不选择新框架、不降低测试层、不修改产品代码来迎合测试。
3. Runtime 保存 test patch/digest；**Prism** 先独立审查测试是否忠于 Acceptance、通过公开出口断言、没有实现耦合或伪测试。

### 6.2 执行与缺陷分流

1. Prism 认为测试合同成立后，Runtime 独立执行 `[integration].run` 和 `[e2e].run`，并记录 runner、环境/fixture、被测 commit、命令、退出结果和覆盖 AC。
2. 失败由当前证据分流：
   - 测试与合同不符、fixture/runner 错误 → 返回 Shield；
   - 有效测试证明实现错误 → 保留测试 patch，返回对应 `M-IMPL` task 给 Devon；
   - 接口/架构不足 → 返回 `M-DESIGN`；
   - Acceptance/Spec 缺口 → 返回 `M-ACC`/`M-SPEC`。
3. 分流需要语义判断时，Runtime 可 dispatch Prism diagnostic review；不得把“测试还是实现错了”交给 Human。
4. 修复实现后，Runtime 重跑受影响 unit、integration/e2e，并要求 Prism 对变化后的测试/代码 revision重新 review。
5. 全部通过后 Runtime 创建受控测试 commit，更新 trace ledger。
6. **退出**：当前 Spec 要求的 integration/e2e 资产和映射全部存在、Prism PASS、程序执行通过，进入 `M-VERIFY`。

## 7. M-VERIFY（完整回归、CI 与 release candidate）

### 7.1 冻结 candidate

1. Runtime 确认工作区没有未归属修改，所有正式 controlled commits 位于当前 release branch，每个实现 task 的 `B/R/G/(Refactor)` lineage、Red/最终 Prism review 和 pre-commit evidence 均 current，然后冻结 candidate commit。私有 Red checkpoint 不进入 candidate ancestry。
2. candidate 冻结后普通 Agent 不再获得写权限；任何代码、测试、设计或配置变化都会产生新 candidate，旧 review/CI/artifact evidence stale。

### 7.2 本地权威质量链

Runtime 从当前 validated machine contracts 执行完整质量链，至少包含：

- format/lint/static/type checks；
- 当前 pre-commit contract/config/installation 无漂移，并以 all-files 模式通过其声明的完整快速检查；
- RGR lineage、Red checkpoint/review freshness 及正式 commit 的 pre-commit evidence；
- 宿主项目**全部单元测试**，包括历史功能回归，不只运行当前 Spec 的测试；
- 全部 required integration suite；
- 全部 required e2e/regression suite，包括历史稳定旅程与当前新增旅程；
- AC 双向 trace、skip/quarantine 合法性、断言反模式和测试路径登记；
- 文档、迁移和兼容性检查（若适用）；
- 真实 build 及全部声明 artifact。

局部 test selector 只用于开发反馈，不能替代本阶段全量 gate。历史测试只有在绑定有效 Issue 和当前 policy revision 的正式 quarantine/deprecation 流程下才可排除；“与本次需求无关”不是排除理由。

### 7.3 版本与构建物验证

1. Runtime 以创建 release 时 Human 提供的 canonical release identity 驱动 Archer 设计的 project-local adapter/tool。
2. 按当前 release contract 的顺序执行：准备/校验版本源 → 真实 build → 枚举全部 artifact → 从每个 artifact 提取版本 → 与 canonical identity 比较 → 从适用的安装/部署/运行出口复核版本。
3. artifact 缺失、版本无法提取、不一致、公开版本出口不一致或结果不确定均阻止 candidate PASS。
4. evidence 必须区分 source version prepared、artifact built、artifact version verified 和 installed/runtime version verified。

### 7.4 GitHub Actions CI

1. Runtime push 精确 candidate commit，触发 Louke 托管的 `.github/workflows/louke-ci.yml`。
2. Runtime 通过 GitHub API 关联 repository、workflow revision、candidate commit、run attempt、jobs 和 artifact；不接受 Agent 转述或另一个 commit 的绿色结果。
3. 稳定聚合 check `Louke CI / required` 只有在全部必需 job 成功时才成功；失败、取消、超时、缺失、非法 skip 或结果不确定均视为失败。
4. Runtime 创建或更新自己拥有的 ruleset/branch protection，使目标分支要求该 check，并回读确认；不得删除用户已有规则或 required checks。
5. 权限、套餐能力、网络中断、API partial success 或回读不一致进入可重试 reconcile/`needs_attention`，不能伪报“CI 已强制启用”。

### 7.5 整体实现复审

1. 本地与 GitHub program gates 通过后，Runtime dispatch Prism 对完整 candidate 做一次独立一致性复审：实现是否整体符合 Architecture/Interfaces/Test Plan，是否存在跨 task 漂移、重复或被局部 review 遗漏的回归风险。
2. Prism REVISE 按 finding 所属返回 Devon、Shield 或上游；任何修订都创建新 candidate并重跑本阶段。
3. **产物**：release candidate identity、全量 test/CI/build/artifact evidence、Prism current PASS 和完整 trace ledger snapshot。
4. **退出**：所有 program gates 与 Prism review 对同一 candidate PASS，进入 `M-SECURITY`。

## 8. M-SECURITY（深度安全审计）

1. Runtime 先确认 CI 中的 secret scan、dependency/SCA、SAST 和项目声明的程序安全检查已经对当前 candidate PASS。
2. 按当前项目 policy revision dispatch **Judge**，输入当前 candidate diff、完整代码、Architecture/Interfaces、依赖、威胁边界、历史 findings 和程序扫描结果。
3. Judge 只做语义安全审查并返回有位置、严重度、影响和修复要求的 findings；不修改代码、不持久化 gate、不推进流程。
4. findings 按来源返回：
   - 实现漏洞 → Devon；
   - integration/e2e 安全场景缺失 → Shield；
   - 架构安全边界错误 → M-DESIGN；
   - 产品权限/数据后果合同缺失 → M-SPEC/M-ACC。
5. 技术修复方案由相应 Agent 决定，不要求 Human 选择。修复后必须重新经过受影响的 M-IMPL/M-TEST、完整 M-VERIFY 和当前 candidate 的 Judge复审。
6. 只有当前 policy revision 明确允许的非阻塞 finding 才可作为残余风险记录；critical/high 或 policy 声明不可接受的 finding 不可 waiver。
7. 若当前 policy revision 对该类项目明确禁用深度审计，Runtime 记录 `skipped_by_policy`、policy digest、依据和适用范围；涉及安全边界、认证、权限、secret、支付或敏感数据的变更不得被普通禁用规则静默跳过。
8. **退出**：Judge PASS 或合法 policy skip 与当前 candidate绑定，且没有 blocking finding，进入 `M-RELEASE`。

## 9. M-RELEASE（Human 发布门禁）

1. **Runtime** 在 Project current 页面展示发布预览：
   - canonical version、candidate commit、目标 main/release branch 和 tag；
   - 本次用户可见变化、Issues/FR/AC 完成情况；
   - 本地全量测试、GitHub required CI、Prism/Judge review；
   - artifact 清单、digest、提取版本和安装/运行后版本；
   - 已知非阻塞风险、发布/回滚步骤和即将发生的外部副作用。
2. 只有全部不可 waiver gate PASS 且 evidence current，发布按钮才可用；Human 不能用发布确认绕过失败的测试、安全、trace、版本或 CI 门禁。
3. **Human** 对同一 preview identity 选择：
   - `Release`：授权 Runtime 执行所列不可逆发布副作用；
   - `Delay`：保持 candidate 和等待状态，不自动发布；
   - `Return`：给出产品/发布原因并选择 definition 允许的上游目标。
4. Agent 可以总结 evidence，但不能代替 Human 作出发布决定，也不得主动把技术风险选择推给 Human。
5. candidate、artifact、evidence 或发布计划任一变化都会使旧 release approval stale，必须生成新 preview。
6. **退出**：Human 的 `Release` 决定绑定当前 preview/candidate，进入 `M-PUBLISH`。

## 10. M-PUBLISH（发布执行与恢复）

1. Runtime 为每个外部操作建立稳定 operation identity，并在执行前先查询当前事实。典型顺序为：
   - 再次确认 candidate commit 的 `Louke CI / required` 和 release approval current；
   - 按当前 release strategy 将精确 candidate 合并/推进到 main；
   - 创建指向同一 commit 的 canonical tag；
   - 发布已经验证的 artifact，或按当前可复现 build contract 从同一 commit/tag 生成并验证等价 artifact；
   - 创建/更新 GitHub Release、release notes 和 artifact links；
   - 从真实安装、部署或运行出口复核公开版本与基本 smoke。
2. tag、GitHub Release、registry publish、merge 和部署不得由 Agent 执行或通过聊天文本模拟。
3. 中断后 Runtime 逐项 reconcile 外部状态；已成功的 operation 不重复执行，未知结果进入 `needs_attention`，不得重新打不同 tag、重复上传或覆盖不可变 artifact。
4. 发布后验证失败时，Runtime 按当前 rollback/forward-fix policy 执行可自动恢复步骤；需要凭据、外部所有权或不可逆冲突处理时请求 Human 授权。技术修复仍返回相应 Agent。
5. 在所有必需发布操作与公开版本验证成功前，Project 状态保持 `publishing`/`needs_attention`，不得标记 completed。
6. **产物**：main commit、tag、release URL、published artifact identities、安装/部署 smoke evidence 和 operation ledger。
7. **退出**：发布事实全部可验证，进入 `M-MILESTONE`。

## 11. M-MILESTONE（闭环与归档）

1. Runtime 对 trace ledger 做最终闭包：每个有效 FR/NFR → AC → test-plan → Runtime task/Issue → Red checkpoint/review → code commit → test/CI result → artifact/release identity 均可正反向追溯，且没有 missing/failed/stale 必需 evidence。
2. Runtime 在发布验证完成后幂等完成：
   - 关闭或更新 requirement Issues 和 release GitHub Project；
   - 归档 WorkflowRun、task attempts、reviews、human gates、events、diffs、RGR checkpoint/lineage、CI/artifact/security/publish evidence；
   - 将项目移入只读历史并释放下一个主 release 的创建资格；
   - 在 Red commit/tree 和 failure/review evidence 已进入可恢复归档后，逐项删除当前 run manifest 中登记的 `refs/louke/rgr/{run}/...`；清理或按保留期标记 OpenCode sessions、临时目录和 hotfix worktree；
   - 保留历史 release/fix branches，除非独立、明确且可恢复的清理 policy 要求处理。
3. 如果当前 DoD revision 要求项目知识或用户文档更新，Runtime 可 dispatch Librarian 做语义提炼；Librarian 只修改授权 wiki/docs，不改变发布事实或流程状态。其 required/optional 性由当前 requirements/design baseline 决定。
4. 发布已经成功但归档/清理失败时，Project 保持 `closing`，Runtime 重试收尾；不得回滚真实发布事实或创建第二次发布。
5. **退出**：发布和 trace 已闭环，必需归档完成，Project/WorkflowRun 标记 `completed`，历史页面可重建全部事实。

## 12. Bug Fix / Hotfix 变体

1. `bug_fix` 只适用于已发布产品相对既有 approved Spec/AC 的实现偏差。Runtime 必须先验证 GitHub Issue、source contract、目标版本和可复现失败；实际提出新行为时退出 hotfix，进入 backlog/new feature。
2. `quick_rgr` 继承并绑定 source requirement approval；`design_required` 还必须形成当前 M-DESIGN revision。涉及 public interface、数据迁移、安全边界或跨模块设计时先走 M-DESIGN；不能确定时由 Archer/Prism 做技术判断，不要求 Human 选择架构路径。
3. 两条路径都复用本文的 `M-IMPL → M-TEST → M-VERIFY → M-SECURITY/policy → M-RELEASE → M-PUBLISH → M-MILESTONE`。测试范围可以按影响收窄开发反馈，但 M-VERIFY 的历史回归和 required CI 不能省略。
4. Hotfix 不因“改动小”自动跳过 Prism；review 深度可按风险调整，但必须有独立 semantic review 和权威 regression evidence。
5. Runtime 是唯一 branch/worktree authority：创建隔离 `fix/{issue-number}`，防止与 active release 串写；发布后按当前同步策略把修复同步到 main 和仍受影响的 active release，冲突时进入 `needs_attention`。

## 13. 通用返回、修改与恢复规则

### 13.1 Return Upstream

- Devon/Shield/Prism/Judge 只能返回有证据和锚点的 gap advisory；Runtime 根据 WorkflowDefinition 校验合法目标并移动流程。
- 返回 `M-DESIGN`：implementation task graph、Architecture、Interfaces、Test Plan 或 pre-commit/CI/release 技术合同需要改变。Runtime dispatch Archer 与 Prism 裁定；两者确认有效即可返回，不需要 Human 批准。
- 返回 `M-SPEC`/`M-ACC`：用户结果、权限、范围、数据后果、不可逆语义或 Acceptance 需要改变。Runtime 先展示影响，由 Human 批准返回需求阶段；修订后必须重新完成 review 和 `M-REQ-APPROVAL`。
- 返回上游后，Runtime 保留历史，但将目标之后的 implementation task graph、baselines、RGR checkpoints/lineages、commits/reviews、candidate、CI/artifact/security/release approval 标记 stale/superseded；不得继续复用旧绿色证据。stale Red ref 在归档前仍保留，不能被新 attempt 覆盖。

### 13.2 Human 或外部工具直接修改

- Runtime 在每个写 lease 和 program gate 前比较 workspace 与当前 baseline，识别 Human/外部工具直接修改的 diff，不静默覆盖。
- 修改符合当前 baseline 且通过当前 task review/gates 时可以纳入 controlled commit；存在问题时由相应 Agent 通过现有 discussion/review 渠道提出，不把“Human 写的”当作自动批准。
- 修改改变当前 baseline 或来源不明时停止当前 task，要求合法 return-upstream 或 reconcile。

### 13.3 Retry、Waiver 与取消

- retry 只能重试 definition 声明且幂等/reconcile-safe 的 operation；每次 attempt 有独立 identity，旧 attempt 不被改写。Red checkpoint 创建使用 compare-and-set `update-ref`，同一 attempt 重试只能得到同一 commit，否则产生新 attempt。
- waiver 只适用于当前 policy revision 明确列出的非关键检查，并绑定 actor、理由、范围、candidate 和到期条件。`M-REQ-APPROVAL`、release approval、trace/freshness、required CI、artifact version、critical security 和发布身份不可 waiver。
- Human 可以取消未发布的 run；Runtime 停止新 dispatch、处理当前 lease、保留审计并清理资源。已经产生外部发布事实后只能进入发布恢复/关闭，不得用“取消”抹除历史。

## 14. 已纳入的 M-IMPL 前流程定稿

以下结论已经反映在本文和 v0.14-001/002 的 flow 中；后续正式 Spec 与 Runtime migration 必须同步：

1. **需求决策阶段统一命名**：canonical identity 是 `M-REQ-APPROVAL`，不再使用 `M-LOCK-1`。旧文档、持久化 run、event 或 API 字段如存在旧值，必须通过显式 migration/兼容读取处理，不能让新状态机同时保留两个可写 identity。
2. **取消设计后的第二次 M-LOCK**：M-DESIGN 由 Archer 创作、Prism 独立评审、Runtime 做程序校验；Human 是可选 reviewer，可以评论但允许缺席，也不批准技术方案。当前设计 revision 通过后直接形成 implementation baseline。
3. **GitHub Project/Issues 与 implementation task graph 分离**：Project/Issues 追踪需求和 release；task graph 是 Runtime 内部的 Agent 执行 DAG，记录依赖、write scope、attempt 和 gate。二者通过 requirement identity 映射，但不能互相冒充。
4. **设计 baseline 覆盖完整输入**：除 Test Plan、Architecture、Interfaces 外，还包含 `[integration]`、`[e2e]`、CI、pre-commit、release-version adapter、build/artifact 和公开版本出口等 machine contracts。所有输入都有 revision/digest，并可由 Archer 按流程修订；修订会使依赖旧 revision 的下游证据 stale。
5. **M-DESIGN 使用完整 review loop**：Runtime 管理单写者、Human direct diff、inline discussion、revision/digest、Prism freshness、程序校验和合法 return-upstream。Agent 不负责锁、commit、dispatch 或推进。
6. **Archer 不向 Human 推卸技术决定**：Human 可以主动提出建议，Archer 可以采纳或以技术理由不采纳；Prism 对最终 revision 独立评审。只有发现产品需求缺口时才返回 Human 决策边界。
7. **上游返回是定义化转移**：返回 M-DESIGN 由 Archer+Prism 裁定，不要求 Human；返回 M-SPEC/M-ACC 需要 Human 批准，并重新取得 M-REQ-APPROVAL。Runtime 记录原因、目标 revision 和 stale 传播，客户端或 Agent 不能直接填写阶段名。
8. **需求批准不是永久冻结**：实现或设计期间发现的新需求可以经 Human 批准返回需求阶段、形成新 revision，并在同一 release 批次重新审批；不能默认一律转入下一批 Backlog。

## 15. 后续 Spec 必须同步的 Agent 合同

当前工作区中，Scribe/Sage/Lex/Archer 已部分转向 v0.14 边界，但 M-IMPL 之后的 Agent 仍大量保留 v0.12/Maestro 驱动指令。正式 Spec 不能只实现 Runtime graph，还必须同步清理这些冲突：

1. **Archer**：增加 M-IMPL Planning 的实施切片职责；implementation task graph 绑定当前 requirements/design baseline，不是 GitHub Project 或新的产品需求，也不向 Human 请求技术决定。M-DESIGN 还必须设计宿主项目 pre-commit contract，区分快速正式 commit gate 与 Runtime/CI 的权威全量 gate；Archer 不执行安装。
2. **Devon**：删除“由 Maestro 调用/协调”、自行 `commit-rgr`、push、选择 branch、关闭 Issue、安装/绕过 pre-commit、写 Runtime evidence 和阶段推进等指令；改为按 task manifest/phase 编辑授权文件并返回代码与语义 handoff。Red 只写测试，Green 默认不得改 Red 测试；Devon 可以运行测试获得反馈，但 Runtime 的复跑结果才是门禁证据。
3. **Shield**：删除自行 git add/commit/push、写 author-result 或决定测试 PASS；只按 manifest 编写 integration/e2e 测试并返回。缺少设计合同时返回有锚点的 gap，不“要求 Maestro 推动”。
4. **Prism**：删除运行/persist `prism review`、写 review-result、调用 Keeper 或推进阶段；分别评审绑定私有 Red checkpoint 的 test-only diff/evidence，以及最终正式 task range/RGR lineage，只返回独立 review/diagnostic 语义。
5. **Judge**：删除由 Agent 执行并以 exit code 持久化安全门禁的做法；程序扫描由 Runtime 执行，Judge 只输出深度语义 findings/review。技术风险不推给 Human 选择修复方案。
6. **Keeper**：不再作为 Agent dispatch。现有 format/RGR/AC trace/anti-pattern/regression 能力拆成 Runtime 注册的 program checks，其中 RGR gate 校验 `B/R/G/(Refactor)` lineage、Red review 与正式 commit 的 pre-commit evidence；如保留 CLI，只能是同一 handler 的兼容入口，不能形成第二状态权威。
7. **Maestro**：不再 spawn 实现/评审 Agent，不调用 `advance/regress/waive`，不 commit/release/archive，也不管理 branch。若保留 Maestro，只用于用户意图路由、证据摘要或受限候选内的语义建议，建议不能直接改变状态。

## 16. 参考基线

- `v0.12.1` 的 `v0.12-001-programmatic-workflow-runtime`：保留完整 new feature/hotfix、两次 Human gate、trace closure、authoritative tests、E2E、security/policy release、human milestone close 与 history 的产品目标。
- `v0.12.1` 及当前工作区的 Devon/Shield/Prism/Keeper/Judge/Maestro 实现：用于识别已有 TDD、review、regression、安全和发布能力，以及必须从 Agent/Maestro 移入 Runtime 的副作用。
- v0.14-001/002：承接 `M-REQ-APPROVAL`、Issue identity 和 M-DESIGN；§14 记录 review 后已定稿、仍需同步到正式 Spec/Runtime 的前置流程结论。
- 当前 Archer/Devon/Shield/Prism prompts 与 v0.14-002 Story：补入宿主项目 managed GitHub CI、全测试层覆盖、artifact version 和安装/运行后版本验证。
