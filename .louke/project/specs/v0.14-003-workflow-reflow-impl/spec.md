# 工作流重构：实现、验证、安全与发布闭环 — 需求规格

- **规格 ID**：`v0.14-003-workflow-reflow-impl`
- **关联 Story**：`STR-1404`
- **创建日期**：2026-07-19
- **状态**：草稿
- **有效 FR 数量**：30（上限 30）
- **Revision identity**：`Lex round 1 revision`
- **Revision digest**：`PLACEHOLDER（由 Runtime 计算）`

> **职责边界**：本文规定 `M-IMPL → M-TEST → M-VERIFY → M-SECURITY → M-RELEASE → M-PUBLISH → M-MILESTONE` 的行为。用户叙事见 `story.md`，完整顺序与返回路径见 `flow.md`，断言见 `acceptance.md`。
>
> **规范性工件集**：除本目录文档、Runtime definition/schema/handlers/tests 和 project-local contracts 外，本 Spec 至少影响 `louke/agents/Archer.md`、`Devon.md`、`Shield.md`、`Prism.md`、`Judge.md`、`Librarian.md`、`Keeper.md` 与 `Maestro.md`。这些 canonical prompt sources 的当前 revision/digest 必须与代码和 schema 一同 review、baseline 和 stale 传播；本草稿不预填未生成的 prompt bundle digest。
>
> 本文中的“项目”均指安装并使用 Louke 的宿主项目。宿主语言、工具链、测试框架、构建和 artifact 只能来自当前 design baseline 与真实项目事实。

## 功能需求

<a id="fr-0100"></a>
### FR-0100 M-IMPL 入口与 Pre-commit Reconcile

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-01`

Runtime 只可在 current implementation baseline 完整、设计程序校验和 Prism review PASS、workspace 修改均可归属时进入 `M-IMPL`。它必须按 pre-commit contract 保留/合并既有 hooks，安装或更新并 readback 实际入口、版本和配置 digest；tracked config 变化以受控 infrastructure commit 更新 baseline，本地 hook identity 只记录 evidence。失败或 drift 必须阻止 Agent dispatch。

---

<a id="fr-0200"></a>
### FR-0200 Implementation Task Graph

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-02`

Runtime 必须 dispatch Archer 依据当前 requirements/design baseline 生成内部 implementation task DAG。每个 task 至少包含 ID、requirement Issue、FR/NFR/AC、目标闭包、依赖、write/forbidden scopes、Devon unit/contract test 与实现责任、Shield integration/e2e 责任、适用 contracts 和完成出口。task 应为可独立验证的纵向切片；GitHub Project/Issues 保持需求追踪身份，不得替代内部 task graph。

---

<a id="fr-0300"></a>
### FR-0300 Task Graph 程序校验与 Review

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-02`

Runtime 必须校验 task ID/依赖存在、DAG 无环、write scope 无冲突、全部有效 FR/AC 具有实现与验证责任且无 orphan task；Prism 必须独立评审可实施性、测试性和设计一致性。任何图变化形成新 revision 并使旧 review stale；设计缺口返回 M-DESIGN，产品缺口经 Human 返回 M-SPEC/M-ACC，不得让 Devon 临场补设计。

---

<a id="fr-0400"></a>
### FR-0400 Task Manifest、单写者与外部修改

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-03`

每个 task attempt 必须具有绑定 baseline commit、Issue/FR/AC、design refs、phase、write/forbidden scopes、测试命令、Human/external diff、prompt/schema identity 和 output contract 的 manifest。普通 feature 同时只能有一个写 lease；Agent 越界修改必须拒绝。Human/外部修改须保留并交给当前专业 Agent 判断：可接受则纳入受控流程，有问题则发起 discussion，改变 baseline 或来源不明则停止并 reconcile/return upstream。

---

<a id="fr-0500"></a>
### FR-0500 Red 编写与专用 Program Gate

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-04`

在 `phase=red` 中 Devon 只能添加证明当前 task 缺失行为的 unit/contract tests，不得修改产品代码、降低既有预期或改变流程事实。Runtime 必须验证 test-only diff、format、测试语法、secret、AC trace、测试反模式和适用静态检查，并要求新测试产生与当前 requirement/interface 精确对应的行为断言失败，或因已设计但未实现 symbol/interface 导致的精确 compile/type failure。环境、fixture、权限、依赖或无关错误均为无效 Red。

---

<a id="fr-0600"></a>
### FR-0600 私有 Red Git Checkpoint

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-05`

合法 Red 后，Runtime 必须使用临时 Git index 创建 parent 为 task baseline `B`、tree 为 `B + test-only diff` 的真实 commit `R`，并以 `refs/louke/rgr/{run}/{task}/{attempt}/red` 通过 compare-and-set 保活。该 ref 不移动 release branch、不进入正式 history、不 push、不触发普通 pre-commit/CI，并绑定 task/attempt/baseline/test command/failure fingerprint/output digest/creator；归档前不得删除或覆盖。

---

<a id="fr-0700"></a>
### FR-0700 Red 独立 Review 与 Correction

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-06`

Runtime 必须 dispatch Prism 评审精确 `B..R`、当前 requirements/Acceptance、测试层合同和 Red evidence。verdict 必须绑定同一 `R` 与 evidence digest；只有 program gate 和 Prism 都 PASS 才能进入 Green。REVISE、测试意外通过、失败类型错误或 diff 越界必须产生 Red correction attempt；任何 test tree 变化建立新 `R` 并使旧 review stale。

---

<a id="fr-0800"></a>
### FR-0800 Green 最小实现与 Red 测试保护

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-07`

进入 Green 时 Runtime 必须恢复已通过 review 的精确 `R` tree，release branch 仍为 `B`。Devon 只能添加使 Red 通过的最小实现，并遵循当前设计/CI contracts；`R` 中测试不得删除、弱化或改写，确需修正时必须回到 Red。Runtime 必须独立运行 target tests、宿主项目全部历史 unit tests、适用 lint/format/type/static 和 task contract checks；历史失败不得因不属于当前 Spec 而 skip。

---

<a id="fr-0900"></a>
### FR-0900 正式 Green Commit 与 Lineage

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-08`

Green checks 通过后，Runtime 必须在 release branch 从 `B` 创建正式 commit `G`，tree 包含已评审测试和最小实现，并在 evidence/commit trailers 关联 task 与 `R`。`G` 必须运行当前普通 pre-commit，禁止 blanket `--no-verify`；hook 改写文件时须重新校验。Runtime 必须证明 `B→R` 仅测试、`R→G` 默认仅实现，并记录 `B/R/G`；`R` 不得成为 `G` parent。

---

<a id="fr-1000"></a>
### FR-1000 Refactor 子阶段

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-09`

Runtime 必须在 `G` 之后允许 Devon 在测试保护下作不改变外部行为的结构改进，并重跑 Green 全部 checks。有变化时创建通过普通 pre-commit 的独立 Refactor commit；无变化时记录绑定 `G` 的 no-change evidence。需要改变 public interface、数据语义、测试分层或架构时必须停止并 return upstream。

---

<a id="fr-1100"></a>
### FR-1100 最终 Task Review 与完成 Gate

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-09`

Runtime 必须校验最终正式 commit range 的 scope、依赖、secret、生成文件、AC trace、测试反模式、外部 diff 和 current `B/R/G/(Refactor)` lineage；Prism 必须独立评审完整代码、测试真实性、设计/CI 一致性和可维护性。改变 Red 测试的 correction 必须回到新 Red lineage。全部 task 只有在 program gates 与当前 Prism PASS 后完成；Agent 自报、commit 或 push 不构成 gate。

---

<a id="fr-1200"></a>
### FR-1200 M-TEST 测试资产生成与 Review

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-10`

全部 implementation tasks 完成后，Runtime 必须按 Test Plan 和 project-local contracts创建 Shield tasks。Shield 只可在授权目录编写 required integration/e2e，使用宿主框架支持的 metadata/邻近注释追溯 AC，通过公开接口断言，不得选择新框架、降低测试层或修改产品代码迎合测试。Runtime 保存 patch/digest，Prism 在执行 gate 前独立评审测试忠实性与分层。

---

<a id="fr-1300"></a>
### FR-1300 M-TEST 执行与缺陷分流

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-10`

Prism 认可测试合同后，Runtime 必须独立执行 integration/e2e 并记录 runner、环境/fixture、commit、命令、结果和覆盖 AC。测试/fixture 错误返回 Shield，实现缺陷保留测试并返回 Devon，设计缺口返回 M-DESIGN，需求/Acceptance 缺口经 Human 返回 M-SPEC/M-ACC；语义不明可由 Prism diagnostic，不得交给 Human 判断技术归因。修复后重跑受影响层并重新 review，成功后创建受控测试 commit。

---

<a id="fr-1400"></a>
### FR-1400 Release Candidate 冻结与 Freshness

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-11`

Runtime 必须确认 workspace 清洁、全部正式 commits 在 release branch、每个 task 的 lineage/Red review/final review/pre-commit evidence current 后冻结唯一 candidate commit。私有 `R` 不进入 ancestry。冻结后普通 Agent 不得写入；任何代码、测试、设计、contract、prompt 或配置变化都产生新 candidate，并使旧 review/CI/build/artifact/security/release approval stale。

---

<a id="fr-1500"></a>
### FR-1500 本地全量权威质量链

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-11`

Runtime 必须对同一 candidate 执行当前 contracts 声明的 format/lint/static/type、pre-commit config/installation drift 与 all-files、RGR lineage、宿主项目全部历史 unit tests、全部 required integration/e2e/regression、AC 双向 trace、skip/quarantine policy、测试反模式、文档/迁移/兼容检查和真实 build。局部 selector 仅作开发反馈；历史测试只有正式 policy-bound quarantine/deprecation 才能排除。

---

<a id="fr-1600"></a>
### FR-1600 版本、Build、Artifact 与公开版本验证

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-13`

Runtime 必须按当前 release contract 依次准备/校验 canonical version source、真实 build、枚举全部 artifact、从每个 artifact 提取并比较版本，再从适用安装/部署/运行出口复核公开版本。evidence 必须区分 source prepared、artifact built、artifact version verified、installed/runtime version verified；缺失、无法提取、不一致或不确定均阻止 candidate PASS。

---

<a id="fr-1700"></a>
### FR-1700 GitHub Candidate CI 与 Required Rule

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-12`

Runtime 必须 push 精确 candidate，触发托管 `.github/workflows/louke-ci.yml`，并经 GitHub API 关联 repository、workflow revision、commit、run attempt、jobs 和 artifacts。该托管 workflow 必须对同一 candidate 实际执行宿主项目全部历史 unit tests 和当前 contracts 声明的全部 required integration/e2e；只有执行证据覆盖这些必需 suites，且该 commit 的 `Louke CI / required` 全部 required jobs 成功才可 PASS。任一必需 suite 缺失、被排除或非法 skip，以及 job 失败、取消、超时、缺失或结果不确定，均使聚合 check 不得 PASS。Runtime 必须幂等 reconcile 自有 ruleset/branch protection 并回读，保留用户规则；权限、网络、partial success 或能力不足进入 `needs_attention`。

---

<a id="fr-1800"></a>
### FR-1800 Candidate 整体 Prism Review

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-14`

本地与 GitHub gates 对同一 candidate PASS 后，Runtime 必须 dispatch Prism 对完整 candidate 做独立一致性复审，检查 Architecture/Interfaces/Test Plan、跨 task 漂移、重复、回归风险和 machine contracts 实现。REVISE 必须返回对应 Devon/Shield/上游并生成新 candidate；退出 M-VERIFY 必须具有同一 candidate 的完整 evidence snapshot 和 current Prism PASS。

---

<a id="fr-1900"></a>
### FR-1900 Security Program Gates 与 Judge Review

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-14`

Runtime 必须先对当前 candidate 执行 policy 声明的 secret scan、dependency/SCA、SAST 和项目安全 checks，再向 Judge 提供 candidate diff/full code、Architecture/Interfaces、依赖、信任边界、历史 findings 和程序结果。Judge 只返回带位置、严重度、影响和 required fix 的语义 findings/verdict，不修改代码、不执行程序 gate、不写状态或推进流程。

---

<a id="fr-2000"></a>
### FR-2000 Security Finding 路由与 Policy Skip

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-14` / `BS-19`

实现漏洞返回 Devon，安全测试缺口返回 Shield，架构边界错误返回 M-DESIGN，权限/数据后果需求缺口经 Human 返回 M-SPEC/M-ACC；技术修复不交给 Human 选择。修复后重走受影响实现/测试、完整 M-VERIFY 与 Judge。只有 current policy 明确允许的非阻塞 finding 可记录残余风险；critical/high 或 policy 禁止项不可 waiver。合法深度审计 skip 必须绑定 policy digest 和范围，敏感边界变更不得被普通规则静默跳过。

---

<a id="fr-2100"></a>
### FR-2100 M-RELEASE Preview 与 Human Gate

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-15`

Runtime 必须在 Project current 的发布预览中展示绑定 preview identity 的 canonical version、candidate/main/tag、用户变化、Issues/FR/AC、全量 tests/CI、Prism/Judge、artifact digests/versions/公开版本、非阻塞风险、发布/恢复计划和即将发生的副作用。全部不可 waiver gates current PASS 前 Release 不可用。Human 可选择 Release、Delay 或 Return：Delay 不产生任何发布副作用，保留 candidate 并使 Project 进入可恢复的 release-waiting 状态，Human 随后可从 Project current 再次打开同一 candidate 的 current preview；Return 必须记录产品/发布原因，只能进入 WorkflowDefinition 允许的上游目标及其对应项目上下文，并按 stale 传播规则处理目标之后的受影响结果。任一 candidate/evidence/artifact/计划变化使旧 approval stale。

---

<a id="fr-2200"></a>
### FR-2200 M-PUBLISH Operation Ledger 与幂等执行

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-16`

Human Release 绑定当前 preview 后，Runtime 必须为 merge/main、canonical tag、registry/artifact publish、GitHub Release/notes、部署和 smoke 等每个适用外部操作建立稳定 identity，在执行前查询事实并持久化 intent/result。Agent 不得执行或模拟这些副作用。重启后已成功操作不得重复，不确定结果进入 `needs_attention`；不得改打不同 tag、重复上传或覆盖不可变 artifact。

---

<a id="fr-2300"></a>
### FR-2300 发布后验证与恢复

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-16`

Runtime 必须确认 main/tag/release/artifact 指向获批 candidate，并从真实安装、部署或运行出口执行版本与基本 smoke。失败时按当前 rollback/forward-fix contract 执行自动安全步骤；涉及凭据、外部所有权或不可逆冲突时请求 Human 授权，技术修复仍返回专业 Agent。全部事实验证前状态保持 `publishing`/`needs_attention`，不得 completed。

---

<a id="fr-2400"></a>
### FR-2400 M-MILESTONE Trace、归档与资源清理

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-17`

发布验证后，Runtime 必须闭合每个有效 FR/NFR→AC→Test Plan→task/Issue→R/review→code/test/CI→artifact/release 的双向 trace，更新 requirement Issues/Project，归档 run/tasks/reviews/gates/events/diffs/RGR/CI/artifact/security/publish evidence，并将项目转历史只读。只有发布事实已验证且全部必需归档闭合后，Project/WorkflowRun 才可 completed 并释放下一主 release 的创建资格；`closing` 或 `needs_attention` 时不得提前释放该资格。只有 Red commit/tree 与证据进入可恢复归档后，才可精确删除 run manifest 登记的 `refs/louke/rgr/{run}/...`；关闭失败保持 `closing` 幂等重试，不得重发 release。

---

<a id="fr-2500"></a>
### FR-2500 Bug Fix / Hotfix 变体

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-18`

`bug_fix` 只适用于已发布产品相对既有 approved Spec/AC 的实现偏差；新行为必须进入 backlog/new feature。Runtime 必须验证 source contract/Issue/version/复现，按影响选择 `quick_rgr` 或 `design_required`，在隔离 `fix/{issue-number}` 与 worktree 中执行。两者均复用 RGR、M-TEST、完整历史 M-VERIFY、required CI、独立 review、release/publish/milestone；发布后按策略同步 main 与受影响 active releases。

---

<a id="fr-2600"></a>
### FR-2600 Return Upstream 与 Stale 传播

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-19`

Agent 只能返回有 evidence 和 artifact anchor 的 gap advisory；Runtime 依据 WorkflowDefinition 校验目标。技术 gap 由 Archer+Prism 确认后返回 M-DESIGN，无需 Human；产品/Acceptance gap 需 Human 批准返回 M-SPEC/M-ACC 并重做 M-REQ-APPROVAL。返回后保留历史并将目标之后的 graph/baseline/RGR/commits/reviews/candidate/CI/artifact/security/release approval 标记 stale/superseded；旧 Red refs 归档前仍保留且不得覆盖。

---

<a id="fr-2700"></a>
### FR-2700 Retry、Waiver 与取消

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-19`

Runtime 只可 retry definition 声明为幂等/reconcile-safe 的操作，每个 attempt 独立且不改写旧事实；Red ref 同 attempt 重试须 compare-and-set 得到同一 commit，否则新建 attempt。waiver 只适用于 current policy 的非关键检查并绑定 actor/reason/scope/candidate/expiry；需求批准、release approval、trace/freshness、required CI、artifact version、critical security 和发布 identity 不可 waiver。Human 可取消未发布 run；已有发布事实只能恢复/关闭。

---

<a id="fr-2800"></a>
### FR-2800 Archer、Devon 与 Shield Prompt 合同

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-20` / `D-04`

本 Spec 必须修订并锁定三类 author prompts：Archer 只生成 implementation task graph/advisory，不创建 GitHub tasks 或推进流程；Devon 只按 manifest/phase 编辑授权 unit tests 与实现，Red/Green/Refactor 规则明确，不 commit/push/安装或绕过 hooks/关闭 Issue/写 gate evidence；Shield 只编写授权 integration/e2e 并返回语义 handoff，不提交、push、宣告程序 PASS 或要求 Maestro 推进。三者不得主动向 Human 请求技术决定。

---

<a id="fr-2900"></a>
### FR-2900 Prism、Judge 与 Librarian Prompt 合同

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-20` / `D-04`

本 Spec 必须修订并锁定 review/closure prompts：Prism 分别评审精确 Red checkpoint、最终 task range、测试资产和 candidate，只返回绑定 identity 的 verdict/findings；Judge 只做深度语义安全审查，程序扫描与 gate 由 Runtime 执行；Librarian 仅在 definition 要求时编辑授权知识/用户文档，不改变发布事实或流程状态。三者均不得持久化自己的 PASS、执行 Git/GitHub 副作用或推进阶段。

---

<a id="fr-3000"></a>
### FR-3000 Keeper 退役与 Maestro 降权

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-20` / `D-04`

Keeper 不再作为 workflow Agent dispatch；其 format/RGR/AC trace/anti-pattern/regression 能力必须迁移为 Runtime 注册 program checks，若保留 CLI 仅为同一 handler 的兼容入口。Maestro 不再 spawn/协调专业 Agents，不调用 advance/regress/waive，不 commit/release/archive 或管理 branch；若保留，只可作用户意图路由、证据摘要或无状态 advisory，且不能直接改变 workflow state。

## 非功能需求

<a id="nfr-0100"></a>
### NFR-0100 确定性、原子性与并发安全

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-03` / `BS-05` / `BS-19`

状态转换、write lease、controlled commit、Red ref、candidate freeze 和 operation ledger 必须使用原子/compare-and-set 语义；同一输入重试应收敛到同一事实，并发 attempt 不得覆盖或串写。

---

<a id="nfr-0200"></a>
### NFR-0200 最小权限与 Secret 保护

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-03` / `BS-12` / `BS-14`

Agent tools/write scopes、GitHub token、CI jobs 和发布 credentials 必须最小化；secret 不得进入 prompt、diff、commit、test fixture、log 或 evidence payload。所有外部写操作必须由 Runtime 在授权边界执行。

---

<a id="nfr-0300"></a>
### NFR-0300 重启恢复与幂等性

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-05` / `BS-16` / `BS-17`

Runtime 在任一阶段重启后必须从持久化 manifest、refs、commits、reviews、evidence 和 operation ledger 恢复，不重复已确认副作用；无法确认时 fail closed/needs_attention。归档和清理必须可安全重试。

---

<a id="nfr-0400"></a>
### NFR-0400 审计与可观察性

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-08` / `BS-11` / `BS-17`

每个 task、gate、review、commit/ref、CI run、artifact/security finding、Human decision 和 publish operation 必须记录 actor、时间、input/output identity、attempt、状态和关联 trace；历史页面应能重建全流程且区分 PASS、FAIL、STALE、SKIP、UNKNOWN。

---

<a id="nfr-0500"></a>
### NFR-0500 宿主项目兼容性

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-01` / `BS-10` / `BS-13`

实现必须通过 002 的 project-local contracts 支持不同语言、构建器、测试框架和 artifact 类型，保留已有 hooks/workflows/rules，并对全新项目使用 Archer 当前设计；不得硬编码 Louke 自身仓库事实。

---

<a id="nfr-0600"></a>
### NFR-0600 状态与证据迁移兼容性

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-19` / `BS-20`

旧 Maestro/Agent 驱动 run、旧 stage identity、缺少 RGR ref 的历史 evidence 和旧 prompt/schema bundle 必须以显式版本只读展示或 migration；新运行只能写 canonical stages 和 Runtime-owned evidence，不得保留双写状态权威。

## 澄清记录

- 2026-07-19：确认合法 Red 不必形成 release branch commit；Runtime 使用私有真实 commit/ref 提供可恢复、可 review 的证据。
- 2026-07-19：确认 Red checkpoint 不运行普通 pre-commit；正式 Green/Refactor/测试 commit 仍必须运行 pre-commit。
- 2026-07-19：确认 CI 和 M-VERIFY 运行宿主项目全部历史 unit tests，并运行全部 required integration/e2e。
- 2026-07-19：确认 Agent prompts 与 Runtime/schema 同属本 Spec 的规范性实现范围，不再把旧提示词视为隐式规范。
