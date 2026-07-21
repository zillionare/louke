# 工作流重构：实现、验证、安全与发布闭环 — 验收标准

- **Spec ID**：`v0.14-003-workflow-reflow-impl`
- **创建日期**：2026-07-19
- **Revision identity**：`Lex round 1 revision`
- **Revision digest**：`PLACEHOLDER（由 Runtime 计算）`

> 本文是 `spec.md` 中全部 FR/NFR 的验收注册表。每个 `### AC-N` 从 1 开始；项目级稳定引用使用条目中的 `AC-FRXXXX-YY` / `AC-NFRXXXX-YY`。

## FR-0100 M-IMPL 入口与 Pre-commit Reconcile

### AC-1
- **验收 ID**：`AC-FR0100-01`
- current implementation baseline 与清洁 workspace 下，Runtime 保留/合并 fixture 的既有 hooks，安装并回读 contract 入口、版本、配置 digest；tracked config 变化形成受控 infrastructure commit 和新 baseline。
- 缺失设计 PASS、stale digest、未归属修改、hook 安装/回读失败或 drift 时，不 dispatch Archer/Devon 并进入可诊断阻塞状态。

## FR-0200 Implementation Task Graph

### AC-1
- **验收 ID**：`AC-FR0200-01`
- Archer 输出可解析 DAG；每个 task 具有 Issue/FR/AC、目标、依赖、write/forbidden scopes、Devon/Shield 责任、contracts 与完成出口，所有有效需求均有去向。
- task graph 以 Runtime 内部 identity 持久化并映射 requirement Issues；系统不会为每个内部 task 复制 GitHub Issue 或把 Project 当执行 DAG。

## FR-0300 Task Graph 程序校验与 Review

### AC-1
- **验收 ID**：`AC-FR0300-01`
- 对 duplicate ID、missing dependency、cycle、scope conflict、orphan AC/task 的 fixture，program gate 分别失败；有效 DAG 获得绑定 baseline 的 Prism PASS。
- 修改 DAG 后旧 review 变 stale；design gap 只能返回 M-DESIGN，product gap 未经 Human 不能返回 M-SPEC/M-ACC。

## FR-0400 Task Manifest、单写者与外部修改

### AC-1
- **验收 ID**：`AC-FR0400-01`
- task manifest 可读出 baseline/Issue/FR/AC/design/phase/scopes/commands/external diff/prompt/schema/output identities，且同一普通 feature 只授予一个 active write lease。
- Agent 越界 diff 被拒绝；Human 合法修改可纳入受控 commit，有技术问题时生成 discussion，来源不明或改变 baseline 时停止 task 而不覆盖。

## FR-0500 Red 编写与专用 Program Gate

### AC-1
- **验收 ID**：`AC-FR0500-01`
- 合法行为断言失败和“已设计但缺失 symbol”的精确 compile/type failure fixture 都可通过 Red gate，且 diff 仅含当前 AC 的测试。
- 产品代码变化、测试弱化、无关语法、dependency/fixture/env/permission failure、无 AC trace 或伪测试 fixture 均被拒绝并保留 baseline。

## FR-0600 私有 Red Git Checkpoint

### AC-1
- **验收 ID**：`AC-FR0600-01`
- Red PASS 后 Git 中存在 parent=`B`、tree=`B+tests` 的 commit `R`，且只有精确 `refs/louke/rgr/{run}/{task}/{attempt}/red` 保活；metadata/evidence 包含命令与 failure fingerprint。
- release branch 仍指向 `B`，`R` 不在正式 ancestry/remote/普通 pre-commit/CI 中；同 attempt 不同 commit 的 compare-and-set 更新失败。

## FR-0700 Red 独立 Review 与 Correction

### AC-1
- **验收 ID**：`AC-FR0700-01`
- Prism 收到精确 `B..R`、requirements/Acceptance、test-layer contract 和 program evidence；Green 只有在同一 `R` 的两类 PASS 都 current 时可启动。
- 修改 test tree、REVISE、unexpected PASS 或错误 fingerprint 会创建新 attempt/ref，并使旧 verdict 无法推进 Green。

## FR-0800 Green 最小实现与 Red 测试保护

### AC-1
- **验收 ID**：`AC-FR0800-01`
- Green workspace 从获批 `R` tree 恢复，Devon 只能在授权实现范围补最小代码；Runtime 的 target tests、全部历史 unit tests 和适用 static/contract checks 全部 PASS。
- 删除/弱化/改写 `R` 测试、跳过历史失败或违反设计合同会阻止 Green；合法测试修正必须回到新 Red review。

## FR-0900 正式 Green Commit 与 Lineage

### AC-1
- **验收 ID**：`AC-FR0900-01`
- 成功后 release branch 新 commit `G` 的 parent 为 `B`，tree 含获批测试+实现，trailers/evidence 引用 task 与 `R`，普通 pre-commit 完整通过。
- Runtime 可验证 `B→R` test-only、`R→G` 默认 implementation-only，且 `R` 不是 `G` ancestor；`--no-verify` 或 hook 改写后未重验不能提交。

## FR-1000 Refactor 子阶段

### AC-1
- **验收 ID**：`AC-FR1000-01`
- 有结构改进时生成独立 Refactor commit 并重跑 Green checks/pre-commit；无变化时有绑定 `G` 的 no-change evidence。
- public behavior/interface/data/test-layer/architecture 变化被识别为 upstream gap，不能伪装成 Refactor 完成。

## FR-1100 最终 Task Review 与完成 Gate

### AC-1
- **验收 ID**：`AC-FR1100-01`
- Prism 最终 review 绑定完整正式 range、`B/R/G/(Refactor)` lineage 与 current checks，且 program gate 验证 scope、secret、trace、生成文件和无未归属 diff。
- 缺少有效 Red/review/pre-commit、改变 Red tests 或只有 Agent 自报 PASS/自建 commit 时，task 不完成且 requirement Issue 不会被标记 release-complete。

## FR-1200 M-TEST 测试资产生成与 Review

### AC-1
- **验收 ID**：`AC-FR1200-01`
- Shield 仅在 contract 路径中生成带可解析 AC metadata 的 integration/e2e，并通过公开 observable interface 覆盖 Test Plan required layers；Prism verdict 绑定测试 patch digest。
- 修改产品代码、引入未设计框架、降低测试层、窥探内部状态或缺 trace 的 patch 被拒绝。

## FR-1300 M-TEST 执行与缺陷分流

### AC-1
- **验收 ID**：`AC-FR1300-01`
- Runtime 对获评审测试记录 runner/environment/fixture/commit/command/result/covered AC，并在全部通过后创建受控测试 commit 与更新 trace。
- fixture/test defect、implementation defect、design gap、requirements gap 四类 fixture 分别路由到 Shield、Devon、M-DESIGN、Human-controlled M-SPEC/M-ACC；不得请求 Human 判断技术归因。

## FR-1400 Release Candidate 冻结与 Freshness

### AC-1
- **验收 ID**：`AC-FR1400-01`
- 清洁 workspace、完整正式 commits 和全部 task current lineage/reviews/pre-commit 下，Runtime 冻结唯一 candidate；其 ancestry 不含私有 Red commits。
- 冻结后修改代码、测试、设计、contract、prompt 或配置会创建新 candidate，并使旧 CI/build/artifact/review/security/release approval 全部 stale。

## FR-1500 本地全量权威质量链

### AC-1
- **验收 ID**：`AC-FR1500-01`
- 当前 candidate 的 gate evidence 包含静态检查、pre-commit all-files/drift、RGR、全部历史 unit、required integration/e2e/regression、trace、policy、文档/迁移和真实 build。
- 只运行当前 Spec selector、以“无关”为由排除历史失败、或无正式 policy identity 的 skip/quarantine 均不能 PASS。

## FR-1600 版本、Build、Artifact 与公开版本验证

### AC-1
- **验收 ID**：`AC-FR1600-01`
- 对全部声明 artifact，evidence 分别显示 version source prepared、artifact built、digest/version extracted+matched、适用 installed/runtime version matched，且均绑定 candidate/canonical identity。
- 注入 artifact 缺失、无法提取、任一版本不一致或公开出口旧版本时，candidate gate FAIL，不会以 branch/tag/source 声明代替。

## FR-1700 GitHub Candidate CI 与 Required Rule

### AC-1
- **验收 ID**：`AC-FR1700-01`
- 精确 candidate 的 GitHub run/job/evidence 可逐项证明托管 `.github/workflows/louke-ci.yml` 实际执行宿主项目全部历史 unit suites 和当前 contracts 声明的全部 required integration/e2e suites；全部执行成功后，Runtime 才接受该 run 的 `Louke CI / required`，并回读自有 ruleset/branch protection 已要求该 check且保留用户规则。
- 从托管 workflow 中缺失或排除任一必需 suite，或注入任一必需 suite 的 illegal skip/failure 时，即使其它 jobs 或同名聚合 check 为绿色，`Louke CI / required` 也不得被 Runtime 认定 PASS；其它 commit 的 green、job cancel/timeout/missing、网络/API partial success 或 readback mismatch 同样不能 PASS，并进入可幂等 reconcile 状态。

## FR-1800 Candidate 整体 Prism Review

### AC-1
- **验收 ID**：`AC-FR1800-01`
- Prism 在本地/CI gates 后收到完整 candidate、design/contracts、task reviews 和 trace snapshot；其 PASS 与所有 program evidence 绑定同一 commit。
- Prism REVISE 路由到责任 Agent/上游并创建新 candidate；旧整体 review 不可复用进入 M-SECURITY。

## FR-1900 Security Program Gates 与 Judge Review

### AC-1
- **验收 ID**：`AC-FR1900-01`
- Runtime 对 candidate 执行 current policy 的 secret/SCA/SAST/project checks 后，Judge 获得完整安全上下文并返回含位置、severity、impact、required fix 的 schema-valid verdict/findings。
- 缺少任一 required program result、Judge input stale，或 Judge 尝试修改代码/写 gate/推进状态时，M-SECURITY 不能 PASS。

## FR-2000 Security Finding 路由与 Policy Skip

### AC-1
- **验收 ID**：`AC-FR2000-01`
- 实现、测试、设计、产品合同四类安全 finding 分别走定义路径，修复后可观察到新 candidate 的受影响实现/测试、完整 M-VERIFY 和 Judge 重跑。
- critical/high 或 policy 禁止 finding 无法 waiver；合法 skip 必须记录 current policy digest/rationale/scope，涉及认证、权限、secret、支付或敏感数据的变更不能被普通禁用规则跳过。

## FR-2100 M-RELEASE Preview 与 Human Gate

### AC-1
- **验收 ID**：`AC-FR2100-01`
- preview 展示 canonical version/candidate/main/tag、用户变化、trace、tests/CI/reviews/security、artifact identities/versions、风险、操作与恢复，Release 仅在不可 waiver evidence current 时可用。
- Human 对 current preview 选择 Delay 后，Project current 显示可恢复的 release-waiting 状态，candidate 与 preview identity 保留，main/tag/registry/GitHub Release/部署等发布事实均未改变；Human 可再次从 Project current 打开同一 candidate 的 current preview并继续作发布决定。
- Human 选择 Return 时，持久化决定包含原因、preview identity 和 WorkflowDefinition 允许的目标；Project current 进入该目标对应的上游上下文，目标之后受影响的 candidate/CI/artifact/security/release approval 等结果可观察为 stale/superseded。非法目标不得改变上下文。任一 candidate/artifact/evidence/计划变化使旧 approval stale，且 Release 不能绕过失败 gate。

## FR-2200 M-PUBLISH Operation Ledger 与幂等执行

### AC-1
- **验收 ID**：`AC-FR2200-01`
- 获批后每个适用 merge/tag/publish/release/deploy/smoke 操作在执行前已有稳定 identity/intent 和事实查询，执行结果持久化且 actor 为 Runtime。
- 在任一操作后模拟重启，已确认成功项不重复；unknown 项停在 `needs_attention`，不会创建第二 tag、重复上传、覆盖 immutable artifact 或由 Agent 文本补写成功。

## FR-2300 发布后验证与恢复

### AC-1
- **验收 ID**：`AC-FR2300-01`
- 发布成功只有在 main/tag/release/artifacts 指向获批 candidate且真实 install/deploy/run version 与 smoke 均验证后成立。
- 发布后验证失败按 contract 进入 rollback/forward-fix 或 Human 外部授权；完成前状态保持 publishing/needs_attention，技术方案仍由 Agent 而非 Human 选择。

## FR-2400 M-MILESTONE Trace、归档与资源清理

### AC-1
- **验收 ID**：`AC-FR2400-01`
- 历史记录可为每个有效需求双向追溯 AC、plan、Issue/task、R/review、formal commits、tests/CI、artifact/security/release，且 Project/WorkflowRun/Issues 状态与真实发布一致。
- 未归档 Red evidence 时 refs 保留；归档成功后只删除当前 run manifest 列出的 refs。归档/清理故障保持 closing 可重试且不重复发布。
- 发布事实已验证且全部必需归档闭合后，Project/WorkflowRun 显示 completed，公开的新建 release 入口允许开始下一主 release，同时刚完成的项目仍只能从只读历史打开；在 `closing` 或 `needs_attention` fixture 中，该入口仍因当前主 release 占用而不允许创建下一主 release。

## FR-2500 Bug Fix / Hotfix 变体

### AC-1
- **验收 ID**：`AC-FR2500-01`
- 已批准行为的可复现偏差可在 Runtime 创建的 `fix/{issue-number}`/worktree 中选择 quick_rgr 或 design_required，并完成 RGR、independent review、全量历史 verification、required CI 和 release closure。
- 实际新行为不会走 hotfix；小改动也不能跳过 Prism/回归。并行 active release 未被串写，发布后同步冲突进入 needs_attention。

## FR-2600 Return Upstream 与 Stale 传播

### AC-1
- **验收 ID**：`AC-FR2600-01`
- 带 evidence/anchor 的技术 gap 经 Archer+Prism 可返回 M-DESIGN；产品 gap 未经 Human 不可返回 M-SPEC/M-ACC，客户端/Agent 传入任意阶段名被拒绝。
- 合法返回后，目标之后全部 graph/baseline/RGR/reviews/commits/candidate/CI/artifact/security/approval 标记 stale/superseded，历史与未归档 Red ref 保留。

## FR-2700 Retry、Waiver 与取消

### AC-1
- **验收 ID**：`AC-FR2700-01`
- 只有 definition 标记幂等安全的操作可 retry；attempt identity 不改写，Red same-attempt compare-and-set 对不同 commit 失败。
- 不可 waiver 清单中的 gate 拒绝 waiver；合法 waiver 含 actor/reason/scope/candidate/expiry。未发布 run 可审计取消，已有发布事实只能进入恢复/关闭。

## FR-2800 Archer、Devon 与 Shield Prompt 合同

### AC-1
- **验收 ID**：`AC-FR2800-01`
- 锁定 prompt bundle 中，Archer 只输出 task graph/advisory，Devon 按 phase 编辑 unit tests/实现，Shield 编辑 integration/e2e；三者输出均引用 program-owned schema 和 manifest identity。
- lint/behavior fixtures 证明 prompts 不包含 Maestro 协调、Agent commit/push/Issue close/hook install-bypass/gate persistence/stage advance 或主动要求 Human 技术决定的指令。

## FR-2900 Prism、Judge 与 Librarian Prompt 合同

### AC-1
- **验收 ID**：`AC-FR2900-01`
- Prism 的多 review kind、Judge 安全 review、Librarian 授权文档任务均有明确 schema reference 与只读/受限写范围，结果绑定输入 identity。
- prompts 不要求三者执行 Git/GitHub/程序 gate/状态推进或自写 PASS；Librarian 未被 definition 标为 required 时不会阻塞 milestone。

## FR-3000 Keeper 退役与 Maestro 降权

### AC-1
- **验收 ID**：`AC-FR3000-01`
- canonical WorkflowDefinition/ResponsibilityCatalog 中不存在 Keeper semantic dispatch；其原质量能力由 Runtime program handlers 提供，兼容 CLI 调用同一 handler且不写第二份状态。
- Maestro prompt/tools 无 spawn 专业 Agent、advance/regress/waive、commit/release/archive/branch 管理能力；其 advisory 无法直接改变 persisted workflow state。

## NFR-0100 确定性、原子性与并发安全

### AC-1
- **验收 ID**：`AC-NFR0100-01`
- 并发 lease、stage transition、controlled commit、Red ref、candidate 和 publish operation fixture 中恰有一个 compare-and-set 成功，其余得到可重试冲突且不覆盖成功事实。
- 同一幂等输入重放得到相同 identity/result；不同 attempt 各自保留完整历史。

## NFR-0200 最小权限与 Secret 保护

### AC-1
- **验收 ID**：`AC-NFR0200-01`
- Agent manifest/tool scopes 与角色合同匹配，GitHub/registry credentials 只在 Runtime operation 边界可用，CI 使用最小 permissions。
- 向 prompt/diff/commit/fixture/log/evidence 注入测试 secret 时，gate 阻止并脱敏报告；Agent 无法读取未授权 credential。

## NFR-0300 重启恢复与幂等性

### AC-1
- **验收 ID**：`AC-NFR0300-01`
- 在 Red ref、Green commit、CI polling、tag/publish 和 milestone cleanup 后模拟进程终止，恢复后从最后确认事实继续且不重复副作用。
- evidence/ref/operation identity 缺失或冲突时 fail closed/needs_attention，不伪造 PASS；修复事实后可安全重试。

## NFR-0400 审计与可观察性

### AC-1
- **验收 ID**：`AC-NFR0400-01`
- 历史 API/UI 可查询每个 task/gate/review/ref/commit/CI/artifact/finding/Human decision/operation 的 actor、timestamp、attempt、input/output identity 和状态。
- PASS、FAIL、STALE、SKIP、UNKNOWN 在存储与展示中保持不同语义，不能由摘要文本覆盖原始证据。

## NFR-0500 宿主项目兼容性

### AC-1
- **验收 ID**：`AC-NFR0500-01`
- 至少两个不同技术栈 fixture 均通过各自 project-local test/build/artifact/pre-commit/CI contracts 完成到 candidate，且保留既有 hooks/workflows/rules。
- 执行路径不读取 Louke 自身语言/构建配置作为宿主默认；不支持的 adapter 返回明确 capability 诊断。

## NFR-0600 状态与证据迁移兼容性

### AC-1
- **验收 ID**：`AC-NFR0600-01`
- 旧 Maestro/Agent 驱动 run、旧 stages、无私有 R ref 的历史和旧 prompt/schema bundle 可以只读展示或经显式 migration 转换，原历史不被伪造。
- 新 run 只写 canonical Runtime-owned stage/evidence；migration 重试不产生双 current state、双 commit authority 或重复外部操作。
