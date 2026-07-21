# 工作流重构：实现、验证、安全与发布闭环 — Architecture

## 0. 文档身份与本轮范围

### 0.1 Artifact identity

| 字段 | 值 |
|---|---|
| Spec ID | `v0.14-003-workflow-reflow-impl` |
| Artifact | `.louke/project/specs/v0.14-003-workflow-reflow-impl/architecture.md` |
| 写作分段 | `2/2-complete` |
| 文档 revision | 由 Runtime design manifest 在接纳本文时分配；revision 不自嵌入文档字节 |
| 文档 SHA-256 | 由 Runtime 对接纳的完整文件计算并写入 design manifest；digest 不自嵌入以避免循环身份 |
| 状态 | `complete`；是否为 current 仍由绑定输入与 program/review evidence 决定 |

### 0.2 Input identities

Runtime 在将本文纳入 design baseline 前必须解析并固化下列动态 identity；未解析、无法回读或与 current 输入不一致时，不得把本文标记为 current。动态值写入外部 immutable design manifest，文档正文不承载这些运行时值。

| 输入 | 绑定规则 |
|---|---|
| Story binding（由 Test Plan 声明） | `sha256:2a04c965b8c97a34a6aec9cf5a7aa1418d84f394830abe5bdf32c2333a10ea3e` |
| Spec binding（由 Test Plan 声明） | `sha256:a5c95c7a7ea1f8237913d9779fbc598d679211ece9be314ace944874b706280a` |
| Acceptance binding（由 Test Plan 声明） | `sha256:a19e25689e59f722d2b72d6903ce4be1b333cf0441c5e3b14a351f6566dfe287` |
| 本轮直接需求输入 | Architecture 第一段读取 `FR-0100..FR-1800`；完整 30 FR、6 NFR、36 AC 的执行分配继承当前 Test Plan，Runtime 分别计算 fragment 与整份输入 digest |
| Test Plan identity | 对当前 `.louke/project/specs/v0.14-003-workflow-reflow-impl/test-plan.md` 完整字节计算 SHA-256并记录 revision |
| Interfaces identity | 在 `interfaces.md` 形成后由 Runtime绑定其 revision/SHA-256；缺失时 M-DESIGN 不得完成，而非接受任意版本 |
| 继承设计合同 identity | 解析 `v0.14-002-workflow-reflow-design` 的 current Architecture/Interfaces/Test Plan revision与digest；Test Plan声明的七个 inherited `IF-*` 必须全部存在 |
| Runtime/workflow schema identity | 解析执行时 current schema的名称、版本、digest；schema变化使依赖 evidence stale |
| Canonical prompt bundle identity | 解析八角色 deployed bundle manifest的revision、digest与capability report |
| Security policy identity | 解析执行时 current policy revision、scanner清单、规则digest与waiver policy |

这些动态 identity 没有通配匹配语义。每次运行、task、candidate、review、CI、artifact、release evidence 都必须保存其实际解析值，不能在事后跟随 `current` 漂移。任何缺失值都是可定位的 program blocker，不是交给 Human 选择的技术问题。

### 0.3 Scope

完整 Architecture 锁定：

1. Runtime authority 与架构原则；
2. `ARC-*` 组件边界、职责和依赖方向；
3. 从 implementation baseline 到 archive/cleanup 的全链路拓扑；
4. task、candidate、release 状态机；
5. `B/R/G/(Refactor)` sibling Git 模型；
6. Test Plan 中全部 `IF-*` 的架构所有者，不遗漏 inherited machine contracts；
7. 事务、持久化、evidence、失败恢复、安全、CI、artifact、发布、归档、trace、迁移和技术取舍；
8. Test Plan 锁定的 30 FR、6 NFR、36 AC 到 `IF-*`、`ARC-*` 和下游实现责任的闭包。

`FR-0100..FR-1800` 的组件行为以本轮直接需求输入为依据；安全、发布、归档、hotfix、prompt和迁移行为以当前 Test Plan 已锁定的 AC/`IF-*`/journey/gate为设计输入。Architecture 不改写产品需求；若后续 Spec 与该 Test Plan 分配不一致，Runtime 必须把相应 design evidence 标为 stale 并返回需求流程。

---

## 1. Architecture Principles 与 Runtime Authority

### 1.1. Runtime 是唯一流程事实与副作用 authority

`ARC-01 Runtime Authority Kernel` 是 workflow current context、状态转换、attempt identity、freshness、受控写入和副作用授权的唯一 authority。Archer、Devon、Shield、Prism、Judge 只在 manifest 授权范围内返回结构化 proposal、patch、诊断或 verdict；它们不能直接：

- 推进 task/candidate/release 状态；
- 持久化自己的 PASS 作为 program gate；
- 创建正式 commit、移动 branch、push candidate 或维护私有 Red ref；
- 写 GitHub required check/rules、发布 provider 或 operation ledger；
- 将不确定结果解释为成功；
- 替 Human 作 `Release/Delay/Return` 决策。

Runtime 必须独立执行 program checks、读取 Git/provider/artifact Ground Truth、验证 Agent output identity，并在 compare-and-set 成功后才发布新的 current read model。

### 1.2. Program evidence 优先于 Agent 声明

自然语言“完成”“PASS”、命令摘要或 Agent session 退出码不构成 gate。每个通过结论必须指向 Runtime 执行或独立 readback 的结构化 evidence，并绑定：

`run + task/candidate/release + attempt + input digests + source commit + command/adapter + environment + output digest + actor + observed_at`。

Prism/Judge verdict 是必要的独立语义评审输入，但不能替代 program evidence；program evidence 也不能替代要求的 Prism/Judge verdict。

### 1.3. Identity-first 与 immutable attempts

- task graph、manifest、review、candidate、CI run attempt、artifact 与 publish operation 都有稳定 identity；
- correction/retry 创建新 attempt，不覆盖旧 attempt；
- 同一 identity 的重复请求必须幂等；内容不同却复用 identity 必须冲突；
- `current` 只是指针，历史 evidence 只追加并保持可回读；
- digest、commit OID、provider resource ID 不得用名称、时间或 Agent 转述替代。

### 1.4. Fail closed、freshness 与无隐式降级

`missing`、`stale`、`cancelled`、`timeout`、`unknown`、`partial` 不能折算为 PASS。上游代码、测试、设计、contract、prompt 或配置变化后，依赖它的 review/CI/build/artifact/security/release approval 必须失效。required integration/e2e、历史测试、artifact 或 provider readback 不得因环境缺失而降级到较低测试层。

### 1.5. 单写者与 compare-and-set

对 workspace、task attempt、private ref、candidate current pointer、workflow transition 和 publish operation 使用预期 revision/OID 的 compare-and-set。普通 feature 同时仅一个 write lease；冲突方得到可重试冲突而不是覆盖。Agent 无权持有可绕过 Runtime 的 Git/provider credential。

### 1.6. Project-local contracts 优先

宿主项目的 pre-commit、test、CI、release/build/publish 和 prompt machine contracts 是命令、路径、artifact 与版本出口的来源。Louke 自身 Python/wheel 事实仅适用于 Louke dogfood，不得成为 Node 或其它宿主的默认。`IF-PC-01`、`IF-TST-01`、`IF-CI-01`、`IF-REL-01`、`IF-BLD-01`、`IF-PUB-01`、`IF-PRM-01` 由 adapter 消费，不由 Runtime 猜测。

### 1.7. Git、provider 与 artifact 独立回读

- Git lineage 由 object/tree/ref/remote readback 证明；
- GitHub run/check/rules 由精确 repository/workflow/commit/attempt readback 证明；
- artifact 由真实 build、逐件 digest/version extraction 和 clean-install/runtime outlet 证明；
- publish 由 intent、query、effect、result ledger 和 provider query 共同证明。

任何 branch/tag/check 名称都不能单独代表上述事实。

### 1.8. 交互层只消费公开 read model

Workbench/API/CLI 只展示 `IF-WFR-01` 及各领域 `IF-*` 的 current/history 投影，并把 Human 动作作为带 expected revision 的 command 交给 Runtime。交互层不能直接修改内部 store 或推断 gate。进行中、blocked、stale、unknown、conflict、reconnect 后状态均来自可回读事实。

---

## 2. 组件目录与职责

### 2.1. Component catalog

| ARC | 组件 | 核心职责 | 权威输入 | 主要产出 | 明确不负责 |
|---|---|---|---|---|---|
| `ARC-01` | Runtime Authority Kernel | workflow command/transition、current/history 投影、attempt/CAS、role capability 与 dispatch authorization；协调全链而不替代领域 gate | current baseline、resolved digests、expected revision、Human/Runtime command | canonical workflow context、allowed actions、transition/audit envelope | Agent 语义工作、Git/provider 真值伪造、Human release 决策 |
| `ARC-02` | Implementation Baseline Reconciler | 校验 M-DESIGN program/Prism PASS、workspace attribution；消费 pre-commit contract，安装/更新/readback；必要时申请受控 infrastructure commit | requirements/design baseline、workspace diff、`IF-PC-01` | current implementation baseline、hook/config evidence、阻塞诊断 | 生成 task DAG、允许 drift 下 dispatch |
| `ARC-03` | Task Graph | 生成/验证纵向 implementation DAG；闭合 Issue/FR/NFR/AC、责任、依赖、scope、commands、contracts 和完成出口；管理 graph revision | implementation baseline、Archer graph proposal、AC registry | validated DAG revision、graph diagnostics、review input | workspace lease、执行 Devon/Shield、把 Issue 当内部 task |
| `ARC-04` | Manifest / Write Lease | 为每个 attempt 物化完整 manifest；授予单写者 lease；校验 write/forbidden scope、external diff attribution 与 expected baseline | validated DAG、workspace snapshot、prompt/schema/output contracts | immutable manifest、lease/current holder、scope verdict、reconcile/return request | 判定 Red 是否有效、提交 Git |
| `ARC-05` | RGR Gate | 执行 Red 专用 program gate、Green checks、Refactor checks、final task gate；证明 test-only/implementation-only、failure fingerprint、历史 unit 与 contract 约束 | leased task manifest、patch、runner/project contracts、Git readback | phase gate evidence、`B/R/G/(Refactor)` lineage report、task completion eligibility | 持有 private ref、用 Prism verdict替代 program gate |
| `ARC-06` | Private Ref | 使用临时 index 创建真实 `R` commit；对 `refs/louke/rgr/{run}/{task}/{attempt}/red` CAS；保证不移动正式 branch/remote；提供精确 object readback | approved Red tree、`B` OID、task/attempt identity | `R` OID、private-ref CAS evidence、archive cleanup target | 普通 pre-commit/CI、删除未归档 Red、创建正式 `G` verdict |
| `ARC-07` | Prism Dispatcher | 按 review kind 组装精确、最小且完整的 review snapshot；校验 verdict schema、actor、input/evidence digest 与 freshness；路由 REVISE | review request、candidate/task evidence、`IF-PRM-01` | current PASS/REVISE verdict、findings、route、stale marker | 运行 program gate、写 commit、自己持久化 PASS |
| `ARC-08` | Shield Controller | 从 Test Plan/project-local contract 生成 Shield integration/e2e tasks；限制资产路径；保存 patch；在 Prism 认可后独立运行 suites并分类 defect | completed implementation tasks、Test Plan、`IF-TST-01`、Shield output | test patch/digest、suite inventory、execution evidence、controlled test commit eligibility、defect route | 修改产品代码、选择新框架、降低测试层、让 Human 判技术归因 |
| `ARC-09` | Candidate Freezer | 校验 clean workspace、正式 ancestry、所有 task/current reviews/pre-commit；冻结唯一 commit并禁止普通 Agent 写；计算 dependent evidence stale set | release branch、task/test completion evidence、dependency digests | immutable candidate identity、freeze snapshot、write-disabled state、freshness projection | 执行质量链、接受 private `R` ancestry |
| `ARC-10` | Local Quality Chain | 对同一 candidate 执行 project-local 全量 format/lint/static/type/pre-commit、RGR、历史 unit、required I/E/regression、trace、policy、docs/migration/compat 和真实 build | frozen candidate、`IF-PC-01`、`IF-TST-01`、suite/policy manifests | 本地权威质量 report、suite inventory、gate evidence | 局部 selector 冒充全量、执行 provider publish |
| `ARC-11` | GitHub CI Adapter | push 精确 candidate；触发/定位托管 workflow；回读 run/jobs/artifacts/check；幂等 reconcile ruleset/branch protection并保留用户规则 | candidate、`IF-CI-01`、GitHub capability/credential | `IF-CI-02` snapshot、唯一 required check readback、needs_attention | 接受同名其它 SHA/check、在 fork 使用生产 secret |
| `ARC-12` | Artifact Verifier | 消费 release/build contract准备 canonical version source；真实 build；枚举并逐件提取 digest/version；clean install/deploy/run 出口复核 | candidate、canonical release identity、`IF-REL-01`、`IF-BLD-01` | source-prepared、artifact-built、artifact-version-verified、installed/runtime-version-verified evidence | 以 tag/source 代替 artifact、替实现者猜 adapter |
| `ARC-13` | Security / Judge Controller | 汇总 candidate-bound program security results；构造 Judge snapshot；校验 verdict/finding identity、权限和 freshness；路由修复 | candidate、policy、prompt/capability identity、quality/CI/artifact/review evidence | security program report、Judge verdict、findings、route/block decision | Judge 写 gate/代码/状态、unknown 或非法 waiver 变 PASS |
| `ARC-14` | Release Decision | 生成 current release preview与 allowed actions；以 expected candidate/revision接受 Human `Release/Delay/Return`；传播 waiting/return/stale | 完整 current gate snapshot、candidate、Human command | release decision record、release-waiting 或合法 upstream route、publish authorization | 代 Human 选择、执行 provider 副作用、复用 stale approval |
| `ARC-15` | Publish Ledger | 为 merge/tag/upload/release/smoke 建稳定 operation identity；按 intent→query→effect→result 执行；重启时 query-before-retry | publish authorization、candidate/artifacts、`IF-PUB-01`、provider readback | append-only operation ledger、confirmed/unknown/needs_attention、publish fact snapshot | 盲重试、覆盖不可变资源、把 timeout 当成功 |
| `ARC-16` | Archive / Cleanup | 验证双向 trace/archive manifest；先归档再按 manifest 精确清理 private Red refs；发布 closing/complete 和 next-release eligibility | confirmed publish facts、全部 evidence、private-ref manifest | archive identity、read-only history、cleanup readback、next-release eligibility | 删除 foreign/unarchived ref、归档失败时宣告 complete |

### 2.2. Dependency direction

主依赖方向如下；领域组件不能反向修改上游事实，只能向 `ARC-01` 返回 command result/evidence，由 Runtime CAS 发布新 current：

```text
ARC-01 Runtime Authority Kernel
  ├─ ARC-02 Baseline Reconciler
  ├─ ARC-03 Task Graph ── ARC-04 Manifest/Write Lease
  │                         └─ ARC-05 RGR Gate ── ARC-06 Private Ref
  │                                  └─ ARC-07 Prism Dispatcher
  ├─ ARC-08 Shield Controller ─────── ARC-07 Prism Dispatcher
  ├─ ARC-09 Candidate Freezer
  │    ├─ ARC-10 Local Quality Chain
  │    ├─ ARC-11 GitHub CI Adapter
  │    ├─ ARC-12 Artifact Verifier
  │    ├─ ARC-07 Candidate Prism Review
  │    └─ ARC-13 Security/Judge Controller
  ├─ ARC-14 Release Decision
  ├─ ARC-15 Publish Ledger
  └─ ARC-16 Archive/Cleanup
```

共享依赖均通过版本化公开 contract 或 evidence envelope 交互：

| 边界 | 规则 |
|---|---|
| Agent session | 只收 manifest + input identities，只回 schema-bound output；无 workflow/Git/provider authority |
| Host workspace/Git | 写入须有 lease；正式 commit/private ref/push 只由 Runtime 受控 adapter 执行 |
| Project-local contracts | adapter 只消费已绑定 revision/digest，不从语言或目录猜命令 |
| Evidence store/read model | immutable attempts + CAS current pointer；摘要不能覆盖原始 evidence |
| GitHub/provider | credential 仅在 Runtime adapter 边界；先 query/readback，结果绑定 provider identity |
| Workbench/API/CLI | command/read model 边界；不得成为第二 current authority |

---

## 3. 端到端数据流

### 3.1. Happy-path topology

```text
implementation baseline
  → validated task DAG revision + Prism PASS
  → per-task manifest + write lease
  → B → Red patch/program gate → private R + Prism PASS
  → restore R tree → Green implementation/checks → formal G sibling
  → optional Refactor commit/no-change → final gate + Prism PASS
  → all implementation tasks complete
  → Shield integration/e2e patch + Prism review + Runtime execution
  → controlled test commit
  → freeze unique candidate
  → local quality + GitHub CI + artifact verification
  → whole-candidate Prism PASS
  → security programs + Judge PASS
  → Human Release / Delay / Return
  → publish operation ledger + provider readback
  → archive manifest + exact private-Red cleanup
  → read-only history + next-release eligibility
```

### 3.2. Stage-by-stage data products

| Step | Producer | Input identity | Durable output | Forward gate |
|---:|---|---|---|---|
| 1 | `ARC-02` | current requirements/design/workspace/pre-commit contract | implementation baseline commit + reconcile evidence | program checks与设计 Prism均 current，workspace可归属 |
| 2 | `ARC-03` + `ARC-07` | implementation baseline | validated task DAG revision + review | DAG完整、无环/冲突/orphan，review绑定同 revision |
| 3 | `ARC-04` | DAG node + baseline + external diff snapshot | attempt manifest + exclusive lease | manifest完整且scope/来源可接受 |
| 4 | `ARC-05` | Red patch + task contract | Red gate/failure fingerprint | 精确行为失败或已设计未实现 symbol failure；其它失败拒绝 |
| 5 | `ARC-06` + `ARC-07` | `B` + approved test-only tree | private `R` ref/readback + Red review | program与Prism均PASS且绑定同一 `R`/digest |
| 6 | `ARC-05` | reviewed `R` tree + Devon implementation | target/history/static/contract results | tests未变弱且全部 required Green checks通过 |
| 7 | `ARC-05` | `B/R` + passing tree | formal `G` + lineage/pre-commit evidence | `G.parent=B`、`R`非ancestor、tree关系成立 |
| 8 | `ARC-05` + `ARC-07` | `G` + optional refactor | Refactor commit或no-change + final review | 外部行为不变且final gate/review current |
| 9 | `ARC-08` + `ARC-07` | all completed tasks + Test Plan/contracts | reviewed Shield patch、suite execution、controlled test commit | required integration/e2e真实运行并正确分流 |
| 10 | `ARC-09` | formal release branch + all current evidence | frozen candidate snapshot | clean、唯一 commit、无 private R ancestry、普通写禁用 |
| 11 | `ARC-10/11/12` | 同一 candidate + locked contracts | local/CI/artifact evidence | 每个 required gate成功且无missing/stale/unknown |
| 12 | `ARC-07` | complete candidate/design/task/trace/gate snapshot | whole-candidate Prism verdict | PASS绑定同一 candidate；REVISE产生新candidate路径 |
| 13 | `ARC-13` | 同一 candidate + security policy + current review | security/Judge evidence | required scans齐全、Judge current、无blocking finding |
| 14 | `ARC-14` | releasable snapshot + expected revision | Human decision record | 只有`Release`产生publish authorization |
| 15 | `ARC-15` | authorization + artifacts + provider contracts | operation ledger + confirmed/unknown facts | 所有必需副作用经query/readback确认 |
| 16 | `ARC-16` | confirmed publish + complete trace | archive/cleanup/history/eligibility | archive先完成，且仅manifest列出的Red refs清理成功 |

### 3.3. Return 与失效传播

- task/Red/Green/Refactor 缺陷只回到能改变对应事实的 owner；新 attempt 不覆写旧 lineage。
- Shield 发现测试/fixture问题返回 `ARC-08`；实现缺陷保留测试并返回相应 task；设计或需求缺口由 `ARC-01` 路由到定义目标。
- candidate freeze 后任何 dependency bytes/digest 变化均由 `ARC-09` 生成新 candidate identity，并使旧 local/CI/artifact/review/security/release approval stale。
- `Delay` 不改变 candidate 或制造 provider 副作用；`Return` 只允许当前 workflow definition 声明的目标，并传播 dependent stale。
- publish `unknown/partial` 保持原 operation identity并进入 reconcile/needs_attention，不回退成“未发生”后盲重试。
- archive/cleanup 失败保持 `closing`，不得重复 publish，也不得提前开放下一 release。

freshness 采用显式 dependency digest 集，不靠阶段名或时间推断：

| 变化事实 | 直接 stale | 级联结果 |
|---|---|---|
| requirements/Acceptance/design/interfaces | task graph/review、未完成attempt | task/test/candidate及全部下游evidence失效，返回定义目标 |
| task graph revision/manifest/prompt/schema | 对应lease、Agent output、review | 未提交attempt终止；已提交历史保留但不能证明current |
| reviewed Red tree/failure evidence | Red Prism、Green与final review | 建立新Red attempt/ref；旧`R`保留到归档 |
| source/test/config/contract bytes | candidate freeze与suite inventory | 生成新candidate；local/CI/artifact/Prism/security/release approval全失效 |
| CI workflow revision或required-suite manifest | CI result、candidate review | 同candidate重新运行CI；旧run保留为history |
| release/build contract或canonical identity | build/artifact/install evidence | 重新准备source并真实build所有artifact |
| security policy/prompt bundle | scan/Judge verdict | 同candidate按新policy重跑，不能沿用旧PASS |
| provider事实 | publish operation readback | operation进入reconcile；不使已确认的其它operation倒退 |
| archive manifest/cleanup readback | complete与next-release eligibility | 保持`closing`，不得再次publish |

Runtime 维护由 input digest 到 evidence identity 的反向索引。提交新事实时在同一 transaction 中计算直接 stale 集并递归闭包，将 stale event 与新 current revision 一起持久化；失败则新事实不成为 current。修复后只能产生新 evidence identity，旧 PASS 不“恢复”。

---

## 4. 状态机

### 4.1. Task 与 attempt 状态机

```text
pending
  → ready
  → leased
  → red_authoring
  → red_program_passed
  → red_review_passed
  → green_authoring
  → green_program_passed
  → green_committed
  → refactor_active ─┬→ refactor_committed
                    └→ refactor_no_change
  → final_program_passed
  → final_review_passed
  → complete
```

| 状态/转换 | 必需事实 | 失败或 correction |
|---|---|---|
| `pending→ready` | 依赖 tasks complete，DAG/review current | 依赖变化回 `pending`；图变化建立新 graph revision |
| `ready→leased` | manifest完整、baseline匹配、唯一 lease CAS成功 | scope/external diff问题为 `blocked` 或 return upstream |
| `red_authoring→red_program_passed` | test-only与合法 failure evidence | correction建立新 attempt；baseline仍为 `B` |
| `red_program_passed→red_review_passed` | private `R` current；Prism PASS绑定 `R`和evidence | REVISE/测试变化建立新 Red attempt，旧 verdict stale |
| `red_review_passed→green_authoring` | 精确 reviewed `R` tree恢复；正式 branch仍在 `B` | 需要改测试则返回新 Red attempt |
| `green_authoring→green_program_passed` | target、全部历史 unit、适用静态/contract checks通过 | implementation correction留在新 Green attempt；不能skip历史失败 |
| `green_program_passed→green_committed` | 普通pre-commit完成；正式 `G` CAS成功；lineage readback成立 | hook改写后重验；branch竞争为conflict/reconcile |
| `green_committed→refactor_*` | 外部行为不变；重跑全部Green checks | public contract/data/layer/architecture变化return upstream |
| `refactor_*→final_program_passed` | final range scope/secret/generated/trace/diff/lineage checks完整 | finding返回拥有该事实的阶段 |
| `final_program_passed→final_review_passed` | Prism绑定完整final range与program evidence PASS | REVISE进入对应新attempt，旧review stale |
| `final_review_passed→complete` | Runtime CAS；program与review仍current | Agent self-report/commit/push不能触发 |

旁路状态：

- `blocked`：缺依赖、lease冲突、未知external diff、contract/drift或required evidence缺失；保留可定位原因。
- `return_requested`：设计/需求或public contract变化，等待 `ARC-01` 合法路由。
- `stale`：attempt所绑定 baseline/graph/design/prompt/schema发生变化；不可继续。
- `cancelled`：仅在 workflow policy 允许且未产生不可逆发布副作用时由 Runtime记录；不删除历史/evidence/private R。

### 4.2. Candidate 状态机

```text
absent
  → freezing
  → frozen
  → verifying
      ├─ local_quality
      ├─ github_ci
      └─ artifact_verify
  → candidate_review
  → security_review
  → releasable
  → awaiting_human_decision
```

| 状态 | 进入条件 | 可离开路径 |
|---|---|---|
| `freezing` | all tasks与Shield assets完成，expected release branch revision匹配 | validation失败回上游；CAS冲突重新读取 |
| `frozen` | clean、正式commits完整、reviews/current、无private R ancestry；写入禁用 | 启动同candidate gates；dependency变化转`stale` |
| `verifying` | local/CI/artifact各自绑定candidate | 全部成功进入candidate review；任一fail回owner；unknown阻塞 |
| `candidate_review` | 本地与GitHub gates及artifact evidence current | Prism PASS进入security；REVISE路由修复并最终形成新candidate |
| `security_review` | candidate Prism PASS current，program scans齐全 | Judge PASS进入releasable；finding路由修复并形成新candidate |
| `releasable` | 全部required evidence current且无unknown | 发布preview可将其置为awaiting Human decision |
| `stale` | 任何依赖输入变化 | 只可保留历史并基于新commit重新freeze；不可恢复旧approval |

`verifying` 是同一 candidate 上的证据汇合，不允许某一分支拿另一 commit 的 PASS。`ARC-10` 本地质量与 `ARC-12` artifact build/verify 可在 candidate freeze 后并行准备；`ARC-11` 只接受已push的同一OID。whole-candidate Prism 要求 local required gates、artifact verification和GitHub required check均current；`ARC-13` 还要求该Prism PASS、policy声明的全部program scans及其原始evidence齐全。并行job失败不取消已产生的可诊断evidence，但聚合状态为FAIL；取消、超时、skip、missing和unknown均不得进入下一状态。

### 4.3. Release 状态机

```text
awaiting_human_decision
  ├─ Delay   → release_waiting → awaiting_human_decision
  ├─ Return  → returned_upstream → new candidate cycle
  └─ Release → publishing → closing → complete
                         └→ needs_attention → reconcile → publishing/closing
```

| Human/Runtime动作 | 前置条件 | 原子结果 | 禁止语义 |
|---|---|---|---|
| `Delay` | preview与candidate current，expected revision匹配 | 记录decision并进入`release_waiting`；candidate/preview可回读 | 不push/tag/upload，不把Delay当拒绝或PASS失效 |
| `Return(target, reason)` | target在allowed actions且revision匹配 | 记录reason/target，进入对应upstream context并标记dependent evidence stale | 非法target不改变context；旧approval不可继续 |
| `Release` | candidate releasable、preview current、全部gate current | 创建唯一publish authorization并进入`publishing` | Human/Agent不能直接执行provider side effect |
| `reconcile` | operation为unknown/partial或进程恢复 | 以同operation identity query-before-retry | 不创建第二tag/upload/release，不覆盖冲突资源 |
| `close` | 必需publish facts confirmed、trace可归档 | 进入`closing`，归档/cleanup成功后`complete` | cleanup失败不重发publish、不提前complete |

### 4.4. 状态发布规则

所有状态转换都必须：验证 expected current revision → 验证所需 evidence identity/freshness → 预写 command/operation intent → 执行领域操作 → 独立 readback → append evidence/audit event → CAS 更新 current。纯本地可回滚变更在单一 store transaction 中提交；Git/provider等外部副作用使用 durable intent + reconcile，不伪装成分布式原子事务。

current CAS 与 append-only event/evidence index 必须同事务提交；失败时 current不变。外部副作用已发生但result未提交时，恢复器读取intent并查询外部事实：唯一且identity匹配则补记`confirmed`；零匹配且contract声明create可安全重试时用同operation identity重试；多匹配、冲突或不可判定进入`needs_attention`。任何路径都不能由Agent写状态或补造evidence。

---

## 5. `B/R/G/(Refactor)` Sibling Git 模型

### 5.1. Object graph

```text
                 R  (parent=B, tree=B+reviewed test-only diff)
                /
... ── B ────── G ── F? ── next task baseline
       \       ↑
        \______|  G.parent=B, tree=B+same reviewed tests+minimal implementation

private: refs/louke/rgr/{run}/{task}/{attempt}/red → R
formal:  release branch B → G → optional Refactor F
```

`R` 与 `G` 是 sibling：两者 parent 都是 `B`；`R` 不是 `G` parent，也不在 `G` ancestry。图中的连线表示 parent 关系，不表示 cherry-pick/merge `R`。

### 5.2. Invariants

| 对象 | 必须满足 |
|---|---|
| `B` | task manifest绑定的正式 release-branch baseline OID；attempt期间不能静默漂移 |
| `R` | `parent=B`；tree恰为`B + test-only diff`；合法failure与review evidence绑定同OID |
| Red ref | 固定路径且CAS创建；同attempt同内容幂等，不同OID冲突；不push、不触发普通pre-commit/CI；归档前保留 |
| `G` | `parent=B`；tree含精确reviewed Red tests与最小实现；通过普通pre-commit；trailers/evidence关联task和`R` |
| `B→R` | 只允许授权unit/contract test与必要test metadata，不含产品实现 |
| `R→G` | 默认只增加实现；不能删除、弱化或改写`R` tests；需改测试时建立新Red attempt |
| Refactor `F` | 有变化时`parent=G`的独立正式commit；外部行为不变并重跑Green checks；无变化记录绑定`G`的no-change evidence |
| next `B` | 当前task最终正式tip，即`G`或`F`；private `R`永远不是后续baseline |

### 5.3. Workspace 与 index discipline

- `R` 由 `ARC-06` 使用临时 index/object creation，从 `B` 与已批准 test patch构造；不得通过 checkout 私有 commit 移动正式 branch。
- Green authoring workspace可恢复 `R` tree内容，但 branch ref仍指向 `B`；正式 `G` 由 Runtime在expected `B`上CAS创建。
- pre-commit若改写文件，`ARC-05` 必须重新执行scope、tree relation和全部受影响checks，再决定是否创建/接受 `G/F`。
- concurrent branch/ref变更、OID不匹配、unattributed diff均是可观察冲突；禁止force覆盖或blanket `--no-verify`。
- cleanup只由 `ARC-16` 在archive manifest已确认后删除精确列举的Red refs；foreign refs和未归档attempt不受影响。

---

## 6. FR-0100..FR-1800 的组件归属

| Requirement | Primary ARC | Supporting ARC | 架构出口 |
|---|---|---|---|
| `FR-0100` | `ARC-02` | `ARC-01` | current implementation baseline与pre-commit reconcile readback |
| `FR-0200` | `ARC-03` | `ARC-01` | implementation task DAG revision |
| `FR-0300` | `ARC-03` | `ARC-07`, `ARC-01` | program diagnostics、Prism verdict、stale/return route |
| `FR-0400` | `ARC-04` | `ARC-01` | attempt manifest、write lease、external diff attribution |
| `FR-0500` | `ARC-05` | `ARC-04` | Red program result与failure fingerprint |
| `FR-0600` | `ARC-06` | `ARC-05` | private `R` object/ref/CAS readback |
| `FR-0700` | `ARC-07` | `ARC-05`, `ARC-06` | Red review、correction attempt与freshness |
| `FR-0800` | `ARC-05` | `ARC-04` | Green workspace/check evidence、test immutability |
| `FR-0900` | `ARC-05` | `ARC-06`, `ARC-02` | formal `G`与sibling lineage/pre-commit evidence |
| `FR-1000` | `ARC-05` | `ARC-07`, `ARC-01` | Refactor commit/no-change与upstream return |
| `FR-1100` | `ARC-05` | `ARC-07`, `ARC-16` | final program/review与task completion eligibility |
| `FR-1200` | `ARC-08` | `ARC-04`, `ARC-07` | Shield task/patch/review read model |
| `FR-1300` | `ARC-08` | `ARC-01`, `ARC-07` | Runtime execution、defect route、controlled test commit |
| `FR-1400` | `ARC-09` | `ARC-01`, `ARC-05` | unique candidate freeze与freshness projection |
| `FR-1500` | `ARC-10` | `ARC-05`, `ARC-08`, `ARC-16` | candidate-bound本地全量质量report |
| `FR-1600` | `ARC-12` | `ARC-10` | source/build/artifact/install分阶段evidence |
| `FR-1700` | `ARC-11` | `ARC-08`, `ARC-09` | candidate CI、required check与rules readback |
| `FR-1800` | `ARC-07` | `ARC-09`, `ARC-10`, `ARC-11`, `ARC-12` | whole-candidate review snapshot/verdict/route |

---

## 7. `IF-*` → `ARC-*` 所有者闭合表

### 7.1. 规则

- **Primary owner** 负责该公开出口的 schema 版本、current/history 投影和领域完整性。
- **Producer/consumer ARC** 只通过已版本化接口提交或读取 evidence，不能另建同义 current authority。
- 带多个 ARC 的接口属于跨模块接口，Test Plan 已要求 integration；本文锁定领域语义、持久化与失败规则，`interfaces.md` 必须据此给出外部字段、权限、错误和modules列，不得改变owner或新增第二current authority。
- `IF-*-02` 不复制 inherited `IF-*-01` project-local contract：前者是 Runtime 结果/readback，后者是宿主命令与机器合同。

### 7.2. Owner table

| IF identity | Primary owner | Producer / consumer ARC | Component / contract 完整语义 | 持久化、失败与权限语义 |
|---|---|---|---|---|
| `IF-WFR-01` | `ARC-01` | `ARC-02..ARC-16` | 唯一聚合WorkflowRun/Project current/history、canonical context、allowed actions和领域evidence links；UI/API/CLI仅消费该read model | current用revision CAS；history append-only；stale/unknown/conflict明确分型；仅Runtime可写，Human只提交带expected revision的允许动作 |
| `IF-IMPL-01` | `ARC-02` | `ARC-01`, `ARC-03`, `ARC-04` | 绑定requirements/design/review/workspace/pre-commit contract，公开hook/config readback、归属分类、infrastructure commit和dispatch eligibility | reconcile attempt不可覆盖；dirty/drift/unattributed/command失败阻断；Runtime执行hook与commit，Agent只诊断 |
| `IF-TASK-01` | `ARC-03` | `ARC-01`, `ARC-04`, `ARC-05`, `ARC-08` | DAG node/edge、36-AC closure、Issue、责任、scope、commands/contracts、manifest revision、lease与external diff投影 | graph revision immutable；lease CAS单写者；cycle/orphan/conflict/越界或未知diff阻断；Archer提案、Runtime校验与发布 |
| `IF-RGR-01` | `ARC-05` | `ARC-06`, `ARC-07`, `ARC-09`, `ARC-10`, `ARC-16` | Red program/fingerprint、private ref、`B/R/G/F` OID/tree/parent、pre-commit、review/no-change与cleanup链接的统一lineage出口 | 每attempt append-only；Git独立readback；CAS冲突不覆盖；失败保持`B`；仅Runtime建commit/ref，归档前`R`不可删 |
| `IF-REV-02` | `ARC-07` | `ARC-03`, `ARC-05`, `ARC-08`, `ARC-09`, `ARC-13` | `task_graph/red/final_task/shield_tests/candidate/security` review kind，精确snapshot/evidence digest、actor、verdict、findings和route | timeout/invalid output为失败而非REVISE/PASS；input变化即stale；Prism/Judge只返回verdict，Runtime校验并持久化 |
| `IF-TEST-02` | `ARC-08` | `ARC-01`, `ARC-07`, `ARC-09`, `ARC-10`, `ARC-11` | Shield授权path/patch digest、AC metadata、公开outlet、suite inventory、runner/env/fixture/result、controlled commit和四类defect route | required suite不可skip；进程失败保留原report；test→Shield、implementation→Devon、design→M-DESIGN、requirement→需求流程；Runtime执行/commit |
| `IF-CAND-01` | `ARC-09` | `ARC-01`, `ARC-10`, `ARC-11`, `ARC-12`, `ARC-13`, `ARC-14` | freeze输入manifest、唯一commit、clean/formal ancestry、private-R exclusion、write-disable、依赖digests与精确stale集合 | candidate pointer CAS；冻结后Agent写拒绝；任一依赖bytes变化建立新candidate，旧evidence保持history但不可release |
| `IF-QUAL-01` | `ARC-10` | `ARC-01`, `ARC-07`, `ARC-09`, `ARC-13`, `ARC-14` | project-local全量quality commands、all-files、RGR、历史unit、required I/E/regression、trace/policy/docs/migration/build与suite closure | 每gate保存command/env/tool/inventory/result；局部selector仅diagnostic；fail/cancel/timeout/skip/missing/unknown使聚合失败；Runtime runner authority |
| `IF-CI-02` | `ARC-11` | `ARC-01`, `ARC-07`, `ARC-09`, `ARC-13`, `ARC-14` | repository、workflow revision、candidate SHA、run attempt、jobs/artifacts、suite coverage、唯一`Louke CI / required`及rules readback | eventual consistency轮询有deadline；同名其它SHA拒绝；非success/缺失/unknown阻断；rules partial进入needs_attention；GitHub token仅adapter持有 |
| `IF-BLD-02` | `ARC-12` | `ARC-09`, `ARC-10`, `ARC-13`, `ARC-14`, `ARC-15` | canonical identity、版本源准备、真实build、逐artifact path/type/digest/extracted version/payload、独立clean-install和运行出口 | 四阶段evidence分离且全绑定candidate；任件missing/corrupt/mismatch/unknown失败；adapter来自`IF-REL-01/BLD-01`，Runtime执行 |
| `IF-SEC-01` | `ARC-13` | `ARC-01`, `ARC-07`, `ARC-09`, `ARC-14`, `ARC-16` | candidate/policy、required scanner completeness、原始结果digest、Judge snapshot/verdict、finding location/severity/impact/fix、skip/waiver与route | scanner缺失或secret泄漏即失败；critical/high及敏感变更不可waiver；Judge无写权限；修复生成新candidate并全链重跑 |
| `IF-REL-02` | `ARC-14` | `ARC-01`, `ARC-09`, `ARC-13`, `ARC-15` | current preview绑定candidate/gates/artifacts/risks/副作用，公开Release/Delay/Return显示与可用性、decision result和恢复入口 | command用expected preview revision；stale时Release禁用；Delay零副作用；Return仅definition目标；只有Human Release授权publish |
| `IF-PUB-02` | `ARC-15` | `ARC-01`, `ARC-12`, `ARC-14`, `ARC-16` | 每个merge/tag/upload/release/smoke operation的stable identity、intent/query/effect/result、provider IDs/facts和总体状态 | ledger append-only；ack-loss先query；confirmed不重复；零/多/冲突/partial按contract重试或needs_attention；credential仅Runtime adapter |
| `IF-TRACE-01` | `ARC-16` | `ARC-01..ARC-15` | 双向`FR/NFR→AC→task→R/G/code→test→CI→artifact→security→decision→publish`、archive manifest、cleanup、history和eligibility | 每边绑定source/target identity与digest；缺边阻断archive；history只读；仅manifest Red refs可CAS删除；全部确认后才开放next release |
| `IF-PROMPT-02` | `ARC-01` | `ARC-03`, `ARC-04`, `ARC-07`, `ARC-08`, `ARC-13` | 八角色canonical/deployed prompt manifest、capabilities、tools/scopes和input/output schema对比；dispatch引用精确digest | capability越权或deployed drift阻断dispatch；prompt不含credential；Agent无Git/state/gate/release authority；报告append-only |
| `IF-MIG-01` | `ARC-01` | `ARC-02`, `ARC-16` | legacy source schema/run/stage/evidence/prompt identity、`read_only|migrated`结果、target IDs、diagnostics与export | migration用source revision CAS与idempotency key；中断可重跑；不伪造旧Red/evidence；新run只有canonical Runtime current authority |
| `IF-PC-01`（inherited） | `ARC-02` | `ARC-05`, `ARC-10` | 宿主pre-commit安装、入口、版本、配置digest、all-files/readback命令contract | 只消费精确inherited revision；缺失或unsupported阻断并诊断；003不复制命令，执行权在Runtime |
| `IF-TST-01`（inherited） | `ARC-08` | `ARC-05`, `ARC-10`, `ARC-11` | 宿主unit/integration/e2e资产路径、cwd、commands、required suite inventory与环境contract | runner与路径必须精确回读；缺入口由实现按继承设计补齐，不由Shield临场发明；Runtime/CI执行 |
| `IF-CI-01`（inherited） | `ARC-11` | `ARC-09`, `ARC-10` | 托管workflow、宿主gate命令、required jobs、artifact/evidence与rules目标contract | workflow revision固定到candidate；用户规则保留；能力不足fail closed；Devon按锁定设计实现、Runtime reconcile |
| `IF-REL-01`（inherited） | `ARC-12` | `ARC-14`, `ARC-15` | canonical release identity、外部tag表示、权威版本源、prepare/validate adapter输入输出contract | 非法/缺失identity阻断；adapter选择已由继承设计锁定；Human不选择技术adapter，Runtime调用 |
| `IF-BLD-01`（inherited） | `ARC-12` | `ARC-10`, `ARC-15` | 宿主真实build命令、artifact清单、版本提取和安装/部署/运行outlet contract | 每件artifact都required；命令非零、清单漂移或出口不确定失败；不借用其它项目命令 |
| `IF-PUB-01`（inherited） | `ARC-15` | `ARC-12`, `ARC-14`, `ARC-16` | 宿主publish operation顺序、query/create/upload/readback、冲突与恢复contract | provider副作用仅Runtime；query-before-retry；不可变资源不覆盖；unknown阻断closure |
| `IF-PRM-01`（inherited） | `ARC-01` | `ARC-03`, `ARC-04`, `ARC-07`, `ARC-08`, `ARC-13` | project-local prompt bundle定位、角色工具/scope与schema contract，供`IF-PROMPT-02`部署比对 | inherited identity缺失/漂移阻断dispatch；Agent只收最小授权输入，无credential与状态写能力 |

### 7.3. Coverage accounting

| 集合 | Test Plan 中数量 | 本表数量 | 结果 |
|---|---:|---:|---|
| 003 Runtime observable identities | 16 | 16 | 完整 |
| inherited project-local machine contracts | 7 | 7 | 完整 |
| **合计** | **23** | **23** | **无遗漏** |

本表完成 Architecture 层的owner、领域语义、持久化、失败与权限闭合。`interfaces.md` 负责把这些语义编码为外部schema/command/error/modules列；它不得更名identity、降低错误语义、隐去Human状态或拆出第二authority。23项均跨越至少两个组件，Shield必须按Test Plan为每项保留integration evidence；面向人的`IF-WFR-01/REL-02/PUB-02/TRACE-01`还必须由公开e2e journey证明。

---

## 8. 完整设计交接

本文锁定16个`ARC-*`组件、完整数据流、三类状态机、R/G sibling Git invariant、23/23 `IF-*`所有权，以及后续章节的事务、恢复、安全、CI、artifact、发布、归档、trace、迁移和技术取舍。Runtime始终是Git/state/GitHub/release副作用唯一authority；Human只拥有已批准的`Release/Delay/Return`产品决策；Agent只提交manifest约束的结构化结果。

Devon据此实现Runtime、公开read model/commands、project-local adapters、托管CI和unit/contract tests；Shield据Test Plan实现所有跨模块integration、公开e2e、CI E2E、artifact/security以及并发/kill/partial-result场景。两者不得重新选择owner、持久化authority、RGR lineage、required gate、release adapter或failure semantics。

---

## 9. 事务、CAS、持久化与 Evidence Identity

### 9.1. 持久化基线

Runtime canonical metadata采用Python stdlib `sqlite3`管理的project-local SQLite数据库；启用foreign keys、WAL和明确busy timeout。大型stdout/stderr、JUnit、coverage、trace、artifact与provider response保存在project-local content-addressed evidence目录，SQLite只保存SHA-256、长度、media type、redaction状态和相对blob key。写blob使用同目录临时文件→flush/fsync→SHA-256复核→原子rename；数据库只可引用已完成rename且digest匹配的blob。孤立blob可由维护任务回收，但不得影响current/history。

选择SQLite是因为本地CLI/Workbench需要真实transaction、唯一约束、CAS与重启恢复，且Python 3.11+无需新增runtime依赖。拒绝单个JSON/TOML current文件加进程锁：它不能可靠表达多实体CAS、append-only history和crash recovery。拒绝在当前范围引入PostgreSQL：它增加服务编排和credential边界，且单project-local writer模型不需要远程数据库。网络共享文件系统上的SQLite/WAL不受支持；此类宿主必须使用本地Runtime store并让Git/provider承担跨机事实同步。

### 9.2. Canonical records

| Record family | Key / uniqueness | 更新模型 | 内容边界 |
|---|---|---|---|
| workflow current | `run_id`唯一 | `WHERE revision=expected_revision` CAS，成功后revision+1 | canonical context/state、current graph/task/candidate/release pointers |
| immutable event | `event_id`唯一，`(run_id, sequence)`唯一 | append-only | actor、command、before/after revision、input/output identity、status、time |
| evidence metadata | `evidence_id`唯一 | append-only；仅可追加supersedes/stale event | kind、subject、attempt、inputs、producer、status、blob digest、tool/environment |
| dependency edge | `(input_identity, evidence_id)`唯一 | append-only | freshness反向索引与trace边 |
| task/lease | task revision唯一；active feature lease部分唯一 | lease acquire/renew/release均CAS | manifest digest、owner session、expiry、workspace/baseline snapshot |
| external intent | `operation_id`唯一 | append planned/executing/query/result attempts | provider、canonical target、idempotency key、request/response digest |
| migration | `(source_identity, target_schema)`唯一 | CAS claim + append attempts | source digest、mode、target IDs、diagnostics |
| archive manifest | `archive_id`和release唯一 | 一次生成，内容不可改 | trace root、evidence list、Red refs/OIDs、provider/artifact facts |

SQLite transaction必须同时完成：校验expected revision/lease/freshness、插入event/evidence metadata、插入dependency/trace edges、更新current pointer。任何constraint、disk、serialization或CAS失败均rollback；外部Git/provider操作绝不放在持锁数据库transaction内。

### 9.3. Identity derivation

Runtime使用受限canonical JSON编码：UTF-8、对象key按Unicode code point排序、无空白、整数十进制、时间为UTC RFC 3339、digest小写hex、禁止float/NaN/Infinity、路径规范为仓库根相对POSIX形式。identity输入先schema校验再编码；未知字段不能静默丢弃。

| Identity | 生成规则 |
|---|---|
| `run_id` / Human command id | Runtime生成不可预测UUID并持久化；重试必须携带原idempotency key |
| task graph revision | `sha256(canonical graph + baseline + requirements/design/AC digests)` |
| task attempt | `(run_id, task_id, monotonically allocated attempt_no, manifest_digest)`；attempt_no在transaction中分配 |
| candidate | `sha256(commit_oid + requirements/design/interfaces/test-plan + contracts/prompts/config/policy digests)` |
| review | `sha256(review_kind + subject identity + exact input/evidence digest set + reviewer role)` |
| CI observation | `(repository_id, workflow_path@blob_oid, candidate_oid, provider_run_id, run_attempt)` |
| artifact | `sha256(raw artifact bytes)`；artifact set另绑定canonical version、candidate和有序成员 |
| publish operation | `sha256(release_identity + operation_kind + provider_namespace + canonical target + payload digest)` |
| evidence | `sha256(kind + subject + attempt + canonical input identities + output blob digest + producer/tool identity)` |
| archive | `sha256(release + candidate + sorted evidence/trace/ref/provider identities)` |

同identity而canonical content不同视为integrity conflict并fail closed；不同identity不能因display name相同而合并。时间只用于审计排序，不参与证明Red先于Green或选择GitHub run/provider resource。

### 9.4. Evidence status与保留

状态只允许`PASS|FAIL|STALE|SKIP|UNKNOWN`，其中`SKIP`必须引用current policy/Issue/owner/scope/expiry且不能覆盖required journey或敏感变更；`UNKNOWN`永不满足gate。原始evidence immutable，状态变化通过新event表达。摘要、UI缓存、Agent文字都只能链接evidence ID，不能覆盖其status或bytes。

未归档release的task/Red/review/gate/provider evidence不得自动删除。release完成后archive manifest成为保留根；private Red ref可清理但对应OID、tree、metadata和review evidence仍由archive可重建。任何包含未脱敏secret的blob不落盘、不上传；记录一个不含原值的blocked security event。

---

## 10. 故障语义与重启恢复

### 10.1. Deadline 与 attempt policy

每个manifest必须写绝对deadline、可重试类别和最大attempt；缺失即contract错误。默认policy为Agent session 30分钟、单个本地program command 30分钟、完整e2e/build 60分钟、GitHub run/readback 90分钟、单次provider consistency query window 10分钟；project-local contract可在manifest生成时收紧或按已声明的长任务上调，但执行中不能由Agent延长。测试使用可控clock，不以sleep证明并发或恢复。

超时只终止当前process/session并记录`timeout`诊断；它不自动撤销已发生的Git/provider事实，也不产生PASS。自动重试只用于manifest/policy明确为幂等且尚无冲突事实的操作，并复用同一logical identity、创建新execution attempt。

### 10.2. Agent、workspace、RGR 与 Git failure matrix

| 故障点 | 立即状态与持久化 | 恢复与公开语义 |
|---|---|---|
| Agent timeout/crash/invalid schema | session attempt=`FAIL`，保存脱敏output digest；current不推进，lease进入reconcile | 同manifest可新session attempt；先复核baseline/workspace；显示role、phase、deadline与last confirmed output |
| external/Human diff出现 | 保存before/after workspace tree、paths与来源分类；暂停写lease | 当前专业Agent只给accept/discuss诊断；可归属且不改变baseline者进入新manifest，未知/越界/baseline变化则return/reconcile且不覆盖diff |
| Red unexpected PASS | Red gate=`FAIL`，不建`R`，保持`B` | 返回Devon新Red attempt；显示command/assertion与expected failure未出现，绝不转Green |
| Red语法/依赖/fixture/env/permission/无关失败 | 分类evidence=`FAIL`，不建`R` | 修复test infrastructure或Red后新attempt；不得记录为合法failure fingerprint |
| Red PASS但Prism timeout/REVISE | `R`和private ref保留，review未通过或REVISE | 同`R`可重试timeout review；test bytes变化必须新`R`；旧verdict保持history/stale |
| Green target/history/static失败 | Green execution=`FAIL`，正式branch仍`B` | implementation correction用新execution attempt；需改测试则新Red lineage；不得skip历史失败 |
| pre-commit改写/失败 | 不创建或不接受`G/F`；保存hook identity与changed tree | 改写后重跑scope、lineage和受影响checks；hook drift回`ARC-02`；禁止blanket `--no-verify` |
| private Red ref CAS竞争 | 回读实际ref；同OID为幂等，不同OID为`conflict` | 不覆盖；不同OID只能建立合法新attempt/ref或停止；孤立object不算成功 |
| formal branch CAS竞争 | `G/F` object不成为current，branch保持实际tip | 实际tip等于精确目标才补确认，否则baseline stale并重建attempt；禁止force update或rebase旧evidence |
| Git ref更新后、DB确认前崩溃 | durable intent仍`executing`，workflow current未推进 | 重启按old/new OID回读：精确new补确认、old可重试、其它conflict；仅Runtime写recovery event |

### 10.3. CI、artifact、security、publish 与 archive failure matrix

| 故障点 | 立即状态与持久化 | 恢复与公开语义 |
|---|---|---|
| CI trigger后run暂不可见 | observation=`UNKNOWN/pending`，candidate不通过 | 以repository/workflow/SHA/dispatch correlation轮询；不重复push，不接受同名其它SHA |
| CI jobs/check eventual consistency | 保存每次provider response digest，聚合pending | 指数backoff `2s→4s→8s→16s→30s`并加jitter，受90分钟deadline约束；可控clock用于测试 |
| CI non-success或suite缺失 | job/run evidence保留，required聚合FAIL | failure/cancelled/timed_out/skipped/neutral/action_required/missing/unknown均非success；修复后新run attempt |
| ruleset partial update/readback mismatch | intent=`partial`，保存before/desired/actual | 只补Runtime-owned差异并保留用户规则；权限/能力/多义冲突进入needs_attention |
| artifact build/extract/install失败 | 对应阶段FAIL，后续not-run而非PASS | 修复source/adapter后新build attempt并重新枚举全部artifact；source/tag正确不能抵消失败 |
| security scanner/Judge timeout | `UNKNOWN`或`FAIL`，不得进入release | scanner可按同candidate/policy重跑；Judge新attempt必须绑定完整program results |
| publish ack loss/timeout | operation=`UNKNOWN`，release保持publishing或needs_attention | 必须query-before-retry；只在query=zero且contract允许时以同operation ID重试；不用`--skip-existing`推断相同 |
| provider partial success | 已确认operations保持confirmed，未确认逐项unknown/failed | 按operation DAG仅reconcile未确认项；不可逆冲突走contract声明的forward-fix/needs_attention，不伪装整体rollback |
| archive/blob/ref cleanup中断 | release保持`closing`，attempt可见 | 验证archive root后按manifest逐ref CAS删除；重试不重跑publish、不开放下一release、不删foreign ref |

CI eventual consistency超过deadline即`UNKNOWN`而非FAIL成功；provider稍后出现结果时Runtime可在同observation identity下追加readback attempt并重新聚合，但只有current candidate且所有required job为success才可继续。

### 10.4. Startup recovery 与 reconnect

Runtime启动时在接受新写command前执行：

1. 在单transaction中把过期session/lease标为`reconcile_required`，但不删除workspace、intent或private refs；
2. 校验SQLite integrity、schema version和current pointer引用；失败进入只读diagnostic mode；
3. 扫描`planned/executing/unknown/partial` intents，按Git→GitHub/rules→publish provider→archive cleanup顺序做read-only query；
4. Git应用`actual==expected new`确认、`actual==expected old`安全重试、其它conflict三分法；provider应用zero/one exact/multiple/conflict四分法；
5. 校验workspace tree、formal branch、private refs和candidate snapshot，差异产生external-diff或stale event；
6. 重算freshness闭包和allowed actions，通过CAS发布恢复后的current revision；
7. 仅在无blocking conflict且重新取得write lease后继续dispatch。

重复启动必须得到相同current/evidence result且不重复副作用。恢复中再次崩溃只追加query attempt，下次仍从同一intent与确认边界继续。

Workbench/API/CLI重连只读取current revision与history cursor；客户端revision落后时先显示stale并刷新，不重放无idempotency key的动作。进行中显示attempt及last confirmed step；失败显示owner、category、可重试性与合法return target；conflict/unknown显示`needs_attention`并禁用越过动作。`Retry`只在Runtime policy声明幂等时可用，任何required evidence非current/PASS时`Release`禁用。

---

## 11. Security 与 Trust Boundaries

### 11.1. Trust classification

| Boundary / data | Trust | 控制 |
|---|---|---|
| Runtime executable、workflow schema、current design/contracts | trusted only after digest/program verification | 启动与每次dispatch绑定digest；漂移阻断，不允许运行时自动接受 |
| Human command | authenticated but semantically untrusted input | authorization、allowed-action、expected revision、CSRF/replay protection；不能携带provider credential |
| Agent/Prism/Judge output | untrusted structured proposal | schema、identity、scope、path、size、secret与capability校验；无Git/state/provider authority |
| repository source/tests/hooks/workflows | untrusted executable content | 在受限subprocess执行；candidate-bound；PR环境无生产secret；hook改写后重验 |
| external/Human diff、fixture、prompt文本 | untrusted content | path canonicalization、symlink escape防护、secret scan、size limit与来源归属 |
| Git objects/refs | authoritative repository fact, not policy verdict | 用OID/tree/parent/remote readback；仍需scope、lineage、review和gate解释 |
| GitHub/PyPI/provider response | external fact with eventual consistency | TLS/provider auth、repository/namespace/resource identity、response digest、query-before-retry |
| evidence summary/UI rendering | derived/untrusted presentation | 原始evidence链接、output encoding、secret redaction；摘要不能改变status |
| SQLite/evidence blobs | canonical local fact after integrity check | filesystem permissions、digest/length验证、transaction、backup/restore identity |

Runtime process按最小权限拆分credential-less orchestration与credential-bearing adapters。Agent subprocess使用独立HOME/XDG、显式env allowlist和工作目录；禁止继承GitHub/PyPI/token、SSH agent、cloud credential、browser cookie或用户全局Git credential helper。Git commit/ref本地写入能力也不交给Agent：Agent只产出patch，Runtime在scope检查后应用。

### 11.2. Secret lifecycle 与不可信输出

credential只可从Runtime secret provider注入到执行该provider operation的子进程内存环境，按operation最小scope和最短lifetime获取；不写manifest、prompt、argv、Git config、workspace、SQLite、evidence或CI artifact。GitHub default CI使用`contents: read`；需要check/rules写权限的protected/manual reconcile与fork PR执行分离。fork代码绝不在拥有production secret或高权限token的context运行。

所有以下边界在持久化、上传和UI展示前执行同一secret scan/redaction pipeline：Agent input/output、Human/external diff、prompt、fixture、subprocess stdout/stderr、JUnit/coverage、Git diff/commit message、provider request/response、browser trace/DOM/screenshot metadata和archive。扫描使用current policy声明的pattern、entropy和synthetic canary；发现命中时：

1. 立即停止对应gate/上传；
2. 内存中生成仅含分类、location hash和policy rule的finding，不保留secret原文；
3. 对可安全重建的日志做确定性redaction后重新扫描；无法证明完整脱敏则丢弃blob并FAIL；
4. 使candidate security evidence与release preview保持blocked；
5. credential疑似真实时由Runtime operator boundary执行rotation，Agent/Judge不接触值。

不能仅依赖字符串替换：结构化字段按allowlist输出，URL移除userinfo/query secret，环境只记录变量名allowlist，HTTP header仅保留非敏感子集，path中用户目录归一化。digest不用于“脱敏后恢复”secret，系统不保存原值映射。

### 11.3. Filesystem、command 与 supply-chain controls

- manifest path先拒绝绝对路径、`..`、NUL与平台歧义，再解析realpath并验证仍位于授权repo/worktree；symlink/hardlink escape和case-fold collision均拒绝；
- command必须来自绑定project-local contract，以argv数组和固定cwd执行；不把Agent/Human字符串交给shell拼接；环境采用allowlist；
- patch应用前限制总bytes/files、文件类型与generated/binary policy，拒绝修改`.git`、Runtime store、credential目录和forbidden scopes；
- dependency安装只使用宿主lock/constraint和绑定toolchain；CI cache key包含lockfile/runtime/OS，不缓存credential或可执行workspace output到跨信任边界；
- third-party GitHub Actions固定到不可变commit SHA；版本升级必须更新workflow revision并使旧CI evidence stale；
- archive/evidence下载使用digest和media type复核，UI按纯文本或安全解析器展示，禁止直接执行HTML/script。

### 11.4. Security program、Judge 与 waiver

`ARC-13`先验证policy列出的secret scan、SCA、SAST和project-specific checks对同一candidate全部有program result，再dispatch Judge。Judge input只含必要的脱敏source context、program evidence和policy identity；Judge输出必须包含finding location、severity、impact、fix与route，不能运行命令、改代码、写gate或推进状态。

| 类别 | 处理 |
|---|---|
| secret/credential exposure、权限越界、发布完整性、RGR/CI/evidence伪造 | 不可waiver；修复并生成新candidate，重跑完整Verify与Judge |
| critical/high dependency或code finding | 不可在本workflow waiver；按implementation/design/requirement owner路由 |
| medium/low且policy允许 | waiver必须绑定candidate、finding、理由、actor、Issue、scope、expiry和policy digest；candidate变化失效 |
| scanner skip | 仅当policy明确允许且包含工具、原因、范围、Issue、owner、expiry；required敏感边界与当前Spec security journey不可skip |
| false positive | 仍作为finding记录，通过policy允许的dismissal evidence处理；Judge文字声明不能自行清除 |

修复后的candidate必须重新执行受影响implementation/tests、全部local quality、GitHub required CI、artifact verification、candidate Prism、security programs和Judge；不得只重跑报错scanner后沿用旧release approval。

---

## 12. Human Release Decision、Archive 与下一 Release

### 12.1. Release preview 与动作可用性

`ARC-14`从current candidate及`IF-QUAL-01/CI-02/BLD-02/REV-02/SEC-01/TRACE-01`生成immutable preview。preview必须显示candidate commit/canonical version、每个required gate及freshness、artifact清单/digests/安装出口、blocking findings/waivers、计划provider副作用、current revision和allowed Return targets。

| 可见状态 | `Release` | `Delay` | `Return` | 反馈与恢复 |
|---|---|---|---|---|
| gates执行中 | disabled | enabled | enabled if definition有目标 | 显示每gate running/last confirmed step；重连恢复同preview revision |
| 全部current PASS且workspace clean | enabled | enabled | enabled | Human可提交一个动作；提交中防重复；成功显示decision identity |
| dirty或candidate dependency变化 | disabled | enabled | enabled | 显示dirty paths/stale evidence；必须新candidate，旧approval不可恢复 |
| missing/FAIL/UNKNOWN/security blocked | disabled | enabled | enabled | 定位owner/category；只显示Runtime允许的retry/return，不允许越过 |
| stale client preview | disabled until refresh | command rejected | command rejected | 返回revision conflict且不改变server context，刷新后重新选择 |
| publishing/closing | hidden/disabled | hidden | hidden | 只显示operation/cleanup进度和reconcile入口，不接受第二decision |
| complete/history | hidden | hidden | hidden | 只读release事实、trace/archive；显示next-release eligibility |

Human command必须包含preview identity、candidate、expected workflow revision、action和唯一command id；`Return`还必须有非空reason与definition枚举target。Runtime在同transaction验证allowed action并记录decision；客户端超时重试相同command id得到相同结果，不创建第二authorization。

### 12.2. Release、Delay、Return semantics

- **Release**：只有Human可触发。Runtime原子创建绑定preview/candidate的publish authorization和operation DAG，然后`ARC-15`执行；Human、Agent或GitHub check都不能直接调用provider。
- **Delay**：记录`release_waiting`和reason（可空），不改变candidate/preview evidence，不push/tag/upload，不释放其历史。重新打开时若依赖仍current可继续决定；若已变化则preview显示stale并禁用Release。
- **Return**：只接受WorkflowDefinition列出的上游目标。Runtime记录reason、计算freshness闭包并切换canonical context；非法target、stale revision或无权限时不改变context。技术缺陷路由由Runtime/Prism决定，Human只选择产品合同允许的Return动作。
- **Reconnect**：先读server current，不根据浏览器本地“已点击”推断成功；decision为unknown时按command id查询，不盲目重交。

### 12.3. Publish operation DAG

Louke dogfood release按`main candidate确认 → canonical tag → wheel/sdist逐件upload → GitHub Release与精确artifact关联 → 从发布渠道clean install/version/smoke`执行；每个节点是独立stable operation并先写intent。若current inherited `IF-PUB-01`对其它宿主声明不同provider或artifact，`ARC-15`按其显式DAG执行，但必须保留“candidate确认先于不可逆副作用、每件artifact独立确认、最终公开出口复核”不变量。

merge/main、tag、release和每件published artifact都必须回读并证明指向approved candidate/canonical identity。相同name但OID/digest不同是冲突，不覆盖。中途失败不删除已发布不可变资源来伪装原子回滚；状态保持publishing/needs_attention，按project-local contract执行安全resume或forward-fix，并在preview/history展示已经发生和尚未确认的副作用。

### 12.4. Archive、Red ref cleanup 与 next-release eligibility

`ARC-16`仅在所有required publish operations和published-artifact smoke为confirmed后生成archive manifest。manifest至少包含requirements/design/interfaces/test-plan/prompt/schema/policy digests、36条AC trace roots、task graph与每个task的`B/R/G/F` OID/evidence、Shield tests、candidate gates、CI/rules、artifact/install/security/review/decision/provider facts，以及待清理Red ref的精确`refname + expected R OID`。

关闭顺序不可交换：

1. 验证双向trace无missing/orphan/ambiguous edge；
2. 写入content-addressed archive blobs和immutable manifest；
3. 独立回读archive root、所有成员digest及只读history投影；
4. 对manifest逐个Red ref执行`delete only if current OID == expected R OID`；相同ref已不存在视为幂等成功，不同OID为冲突且绝不删除；
5. 回读全部目标refs、确认foreign refs未变并记录cleanup evidence；
6. CAS将release从`closing`改为`complete`并计算next-release eligibility。

next-release入口只有在以下条件全真时enabled：release=`complete`、archive current且可读、所有manifest Red refs已精确清理或幂等不存在、无unknown/partial publish operation、history只读投影成功、active release/branch/worktree namespace无冲突。任一条件失败保持disabled并显示owner和reconcile入口；cleanup不得成为重复publish的理由。

完成后的history禁止修改原evidence/status/decision/provider facts；更正只能追加勘误或新release/hotfix记录并引用原identity。approved bug deviation可启动隔离`fix/{issue}` branch/worktree和独立run/release namespace，复用完整RGR/quality/CI/release闭环；新行为返回正常需求流程，不能伪装hotfix。

---

## 13. Local Quality、GitHub CI 与 Artifact Contract

### 13.1. 托管 GitHub Actions topology

Devon创建/更新唯一托管`.github/workflows/louke-ci.yml`；已有`ci.yml`与`release.yml`保留其不同名称职责，但不得产生`Louke CI / required`同名check，也不得绕过它publish。workflow在`pull_request`、目标分支push运行，release/manual增加`protected-smoke`；fork PR只跑无secret的stand-in链。

runner固定`ubuntu-24.04`。unit使用Python `3.11, 3.12, 3.13, 3.14`矩阵，其它contract/integration/e2e/build/security使用Python `3.12`作为canonical evidence环境；浏览器journey安装contract声明的Chromium。GitHub Actions使用`actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683`、`actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065`、`actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02`，不得用可移动major tag执行。升级SHA视为workflow revision变化并使旧CI evidence stale。

```text
quality
  ├─ workflow-contract
  └─ ac-trace
       \ /
   build-artifacts
        ↓
   artifact-verify
        ↓
  ┌─────┼───────────┬────────────┬────────┬─────────┐
 unit  integration  e2e-standin  ci-e2e  security  [protected-smoke]
  └─────┴───────────┴────────────┴────────┴─────────┘
                         ↓ if: always()
                 Louke CI / required
```

`Louke CI / required`显式依赖所有适用jobs，读取每个`needs.<job>.result`，只有全为`success`才exit 0；failure/cancelled/skipped/missing/unknown或聚合脚本无法解析均exit nonzero。release/manual中`protected-smoke`是publish/closure required；PR中不伪造其PASS，而是按trigger applicability排除并在evidence标明not-applicable。

### 13.2. Job commands、权限与 evidence

| Job | 锁定入口 | Evidence / failure |
|---|---|---|
| `quality` | `pre-commit run --all-files`; `python -m mypy louke` | tool/config digest、all-files清单、stdout/stderr；nonzero/timeout/改写未重验失败 |
| `workflow-contract` | `python -m pytest -q tests/unit/v014_workflow_impl -m contract`；suite内部调用current inherited 002 contract validators | 23/23 IF inventory、schema/permission/exit report；unknown identity或validator缺失失败 |
| `ac-trace` | `python tools/check_ac_traceability.py --acceptance .louke/project/specs/v0.14-003-workflow-reflow-impl/acceptance.md --tests tests` | 36/36双向closure与required-layer JSON；missing/unknown/层级下降失败 |
| `build-artifacts` | `python -m build` | wheel+sdist路径、SHA-256、builder/toolchain；任件缺失失败 |
| `artifact-verify` | current `IF-REL-01/IF-BLD-01` adapter入口 | source/artifact/install四阶段JSON；任件version/payload/outlet不一致失败 |
| `unit` | `python -m pytest -q tests/unit --cov=louke --cov-report=xml --cov-fail-under=95` | matrix JUnit、coverage XML、historical inventory；任一Python版本失败则required失败 |
| `integration` | `tests/e2e/run-project-venv integration` | JUnit、fixture/runner/env、CAS/restart/route report；required skip/not-run/nonzero失败 |
| `e2e-standin` | `tests/e2e/run-project-venv e2e --profile all --runtime both` | journeys、runtime/profile inventory、browser trace；任一组合未运行或失败则失败 |
| `ci-e2e` | current `IF-CI-01`声明的provider harness，由上述project-venv runner执行其required CI profile | stand-in run/jobs/check/rules ledger；protected/manual另存`mode=real`，两者不可互冒 |
| `security` | current security policy中有序scanner commands + security pytest journeys + Judge schema validator | scanner completeness、finding/waiver/secret report；缺失、非法skip、blocking finding或泄漏失败 |
| `protected-smoke` | current `IF-CI-01/PUB-01` provider readback和发布后`IF-PUB-02/BLD-02` clean-install smoke | repository/namespace/candidate/run/credential-boundary；not-run/partial/unknown阻断publish或closure |

workflow顶层和普通jobs默认`permissions: contents: read`；不授予`pull-requests: write`、`checks: write`、`id-token: write`或`packages: write`。Runtime rules/publish adapter在独立protected environment中取得最小token，且不执行fork bytes。并发键包含workflow与ref/candidate，PR新run可取消旧run，但旧run结论保留且不能为新candidate提供PASS；release/publish reconcile不得被自动取消。

pip/cache只缓存下载物，key含OS、Python、dependency lock/constraint digest；不缓存venv、built artifact、Runtime store或evidence。所有上传artifact使用无secret的确定名称加candidate/run attempt，保存期按repository policy；上传前secret scan，扫描失败则不上传且job失败。JUnit、coverage、trace closure、suite inventory、RGR lineage、candidate freshness、CI/rules readback、artifact identity/install、security/Judge、stand-in ledger和journey report均required evidence。

### 13.3. Canonical version 与 Louke artifact adapter

Human release version的canonical identity使用无`v`前缀的PEP 440 public version；Test Plan release fixture为`0.14.0`，外部Git tag表示为`v0.14.0`，branch name不参与artifact identity。Louke dogfood的权威版本源是`pyproject.toml`中project version；版本准备/校验入口必须使用current inherited `IF-REL-01`选定的project-local adapter，Devon不得改选其它版本文件或手工只改tag。其它宿主完全使用其自身`IF-REL-01/BLD-01`，不继承Louke Python方案。

Louke required artifact恰为一个wheel和一个sdist，由`python -m build`在clean candidate tree生成。`ARC-12`：

1. 调用adapter以canonical identity准备或验证`pyproject.toml`版本源并readback；
2. 清理旧dist输出后真实build，枚举本attempt新增的wheel与sdist，拒绝零件、多件或旧文件混入；
3. 对原始bytes计算SHA-256；从wheel的`.dist-info/METADATA`与sdist的`PKG-INFO`独立提取`Version`，并检查filename/top-level identity；
4. 按`IF-BLD-01` payload manifest验证console entry point、canonical prompts、workflow schemas及运行所需package data均在两件artifact中；
5. 为每件artifact建立独立clean venv，以artifact本身安装，不从source tree import；
6. 在每个venv分别执行`lk --version`与`python -c 'import importlib.metadata as m; print(m.version("louke"))'`，两出口均须等于canonical identity；
7. 保存source-prepared、artifact-built、artifact-version-verified、installed/runtime-version-verified四类独立evidence。

任何非法canonical identity、adapter失败、source mismatch、build nonzero、artifact缺失/多余/损坏、digest不确定、extracted version/payload/公开出口不匹配都阻断candidate和publish。只有最后一类evidence对wheel与sdist全部current PASS，才满足“artifact版本已验证”；前面三类不能单独授权发布。

---

## 14. FR/NFR/AC → IF → ARC 追溯与实现责任

### 14.1. 闭合规则

以下36行是Architecture对Test Plan 36/36策略行的下游责任投影，不新增AC。Devon负责对应`ARC-*`实现、公开read model/command adapter及unit/contract；Shield负责表中required的全部`I/E/CE/A/S`，且跨模块`IF-*`至少有integration。Runtime负责真实执行、持久化与gate，Prism/Judge只评审。`U/C/I/E/CE/A/S`与CI gate沿用Test Plan定义；任何一行缺IF、owner、Devon实现或required Shield evidence均使`ac-trace`失败。

### 14.2. FR-0100..FR-1100

| Requirement / AC | Observable IF | Owning ARC | Devon implementation责任 | Shield required evidence |
|---|---|---|---|---|
| `FR-0100 / AC-FR0100-01` | `IF-IMPL-01,WFR-01,PC-01` | `ARC-02,01` | baseline/pre-commit reconcile、attribution、dispatch blocker及U/C | I：真实workspace/Git/hooks current/drift/dirty矩阵 |
| `FR-0200 / AC-FR0200-01` | `IF-TASK-01` | `ARC-03` | DAG schema/validator、36-AC closure与C | I：真实graph/store接线及完整责任映射 |
| `FR-0300 / AC-FR0300-01` | `IF-TASK-01,REV-02,WFR-01` | `ARC-03,07,01` | cycle/orphan/scope/revision/freshness/route及U/C | I：graph revision→Prism→stale/return闭环 |
| `FR-0400 / AC-FR0400-01` | `IF-TASK-01,WFR-01` | `ARC-04,01` | manifest、lease CAS、scope/path/external diff及U/C | I+S：并发单写者、Human diff保留、escape/unknown阻断 |
| `FR-0500 / AC-FR0500-01` | `IF-RGR-01,TASK-01` | `ARC-05,04` | Red classifier/fingerprint、test-only/anti-pattern/trace及U/C | I+S：真实subprocess覆盖合法与全部非法failure类别 |
| `FR-0600 / AC-FR0600-01` | `IF-RGR-01` | `ARC-06,05` | temporary-index commit、private-ref CAS/readback及C | I：真实Git object/ref/remote、竞争与归档前保留 |
| `FR-0700 / AC-FR0700-01` | `IF-RGR-01,REV-02` | `ARC-07,05,06` | Red review snapshot/verdict/freshness/correction及C | I：精确`B..R`、双PASS、test变化新attempt |
| `FR-0800 / AC-FR0800-01` | `IF-RGR-01,QUAL-01` | `ARC-05,10` | reviewed R恢复、Green scope、历史unit/static/contract及U/C | I：真实runner、test mutation/skip/history failure返回Red |
| `FR-0900 / AC-FR0900-01` | `IF-RGR-01,PC-01` | `ARC-05,06,02` | formal G CAS、trailers、pre-commit重验、sibling validator及C | I：Git Ground Truth证明`G.parent=B`、R非ancestor与tree关系 |
| `FR-1000 / AC-FR1000-01` | `IF-RGR-01,REV-02` | `ARC-05,07,01` | Refactor/no-change、Green rerun、public-contract return及U/C | I：commit/no-change、外部语义变化阻断 |
| `FR-1100 / AC-FR1100-01` | `IF-RGR-01,REV-02,TRACE-01` | `ARC-05,07,16` | final scope/secret/generated/trace/lineage gate与C | I+S：完整range/review、越权Agent/secret/unattributed diff阻断 |

### 14.3. FR-1200..FR-1800

| Requirement / AC | Observable IF | Owning ARC | Devon implementation责任 | Shield required evidence |
|---|---|---|---|---|
| `FR-1200 / AC-FR1200-01` | `IF-TEST-02,TST-01,REV-02` | `ARC-08,07,04` | Shield task/scope/patch/review controller与C | I：仅授权I/E资产、AC metadata、公开outlet、无降层/产品改写 |
| `FR-1300 / AC-FR1300-01` | `IF-TEST-02,WFR-01,TRACE-01` | `ARC-08,01,16` | Runtime runner、四类defect router、controlled test commit与C | I+E：真实journey、runner/env/fixture、修复后重跑/review |
| `FR-1400 / AC-FR1400-01` | `IF-CAND-01,RGR-01,WFR-01` | `ARC-09,05,01` | freeze/CAS/formal ancestry/write-disable/freshness及U/C | I+E：post-freeze mutation/reconnect、六类依赖变化精确stale |
| `FR-1500 / AC-FR1500-01` | `IF-QUAL-01,TEST-02,RGR-01` | `ARC-10,08,05` | full-chain orchestrator、suite inventory/policy/trace与C | I+E：全部历史/required suites、selector/skip/quarantine与真实build |
| `FR-1600 / AC-FR1600-01` | `IF-BLD-02,REL-01,BLD-01` | `ARC-12` | version/build adapter调用、逐件extract/install/outlet readback与C | I+A：clean build、wheel+sdist独立venv、全部mismatch/unknown |
| `FR-1700 / AC-FR1700-01` | `IF-CI-02,CI-01,TEST-02` | `ARC-11,08,09` | managed workflow、GitHub adapter、required aggregation/rules reconcile与C | I+CE+S：stand-in与隔离real、伪绿/其它SHA/suite缺失/partial rules |
| `FR-1800 / AC-FR1800-01` | `IF-CAND-01,REV-02,TRACE-01` | `ARC-07,09,10,11,12` | whole-candidate snapshot/freshness/REVISE router与C | I：完整design/task/trace/gates同candidate，REVISE新candidate |

### 14.4. FR-1900..FR-2400

| Requirement / AC | Observable IF | Owning ARC | Devon implementation责任 | Shield required evidence |
|---|---|---|---|---|
| `FR-1900 / AC-FR1900-01` | `IF-SEC-01,CAND-01,PROMPT-02` | `ARC-13,09,01` | scanner completeness、Judge snapshot/schema/capability与C | I+S：missing/stale/invalid/越权Judge、finding完整性 |
| `FR-2000 / AC-FR2000-01` | `IF-SEC-01,WFR-01,CAND-01` | `ARC-13,01,09` | finding route、waiver/skip policy、freshness重跑与C | I+E+S：四类route、不可waiver、敏感边界与新candidate全链 |
| `FR-2100 / AC-FR2100-01` | `IF-REL-02,WFR-01,CAND-01` | `ARC-14,01,09` | preview/allowed-actions/expected-revision command与C | I+E+S：Release/Delay/Return、dirty/stale/conflict/reconnect公开journey |
| `FR-2200 / AC-FR2200-01` | `IF-PUB-02,REL-02,PUB-01` | `ARC-15,14` | operation identity/ledger/query-before-retry/reconcile与U/C | I+E+S：每operation kill/ack loss/zero/multi/conflict且无重复副作用 |
| `FR-2300 / AC-FR2300-01` | `IF-PUB-02,BLD-02,WFR-01` | `ARC-15,12,01` | publish DAG/provider readback/恢复状态与C | I+E+A：main/tag/release/artifact同candidate、published clean-install/smoke |
| `FR-2400 / AC-FR2400-01` | `IF-TRACE-01,RGR-01,WFR-01` | `ARC-16,05,01` | archive manifest、trace closure、ref CAS cleanup、eligibility与C | I+E：closing kill/retry、foreign refs、只读history与next-release gate |

### 14.5. FR-2500..FR-3000

| Requirement / AC | Observable IF | Owning ARC | Devon implementation责任 | Shield required evidence |
|---|---|---|---|---|
| `FR-2500 / AC-FR2500-01` | `IF-WFR-01,RGR-01,CI-02,TRACE-01` | `ARC-01,05,11,16` | isolated hotfix namespace、deviation gate、全链复用与C | I+E+CE：偏差/新行为、parallel releases、sync conflict/needs_attention |
| `FR-2600 / AC-FR2600-01` | `IF-WFR-01,TRACE-01,RGR-01` | `ARC-01,16,05` | definition-valid return、gap route、stale closure及U/C | I+E：technical/product gap、非法stage不变、合法return保留history/R |
| `FR-2700 / AC-FR2700-01` | `IF-WFR-01,PUB-02,RGR-01,TRACE-01` | `ARC-01,15,05,16` | retry/waiver/cancel policy、immutable attempts与U/C | I+E+S：CAS race、不可waiver、发布前后cancel/recovery语义 |
| `FR-2800 / AC-FR2800-01` | `IF-PROMPT-02,TASK-01` | `ARC-01,03,04` | Archer/Devon/Shield prompt manifest与capability enforcement及C | I+S：semantic lint+capability harness，无Git/state/Issue/gate authority |
| `FR-2900 / AC-FR2900-01` | `IF-PROMPT-02,REV-02,SEC-01` | `ARC-01,07,13` | Prism/Judge/Librarian review kinds/schema/scope与C | I+S：无Git/GitHub/program gate/PASS persistence；非required Librarian不阻断 |
| `FR-3000 / AC-FR3000-01` | `IF-PROMPT-02,WFR-01,QUAL-01` | `ARC-01,10` | ResponsibilityCatalog/WorkflowDefinition、兼容CLI、单一Runtime handler与C | I+S：无Keeper semantic dispatch/双写；Maestro advisory无法spawn/advance/release |

### 14.6. NFR-0100..NFR-0600

| Requirement / AC | Observable IF | Owning ARC | Devon implementation责任 | Shield required evidence |
|---|---|---|---|---|
| `NFR-0100 / AC-NFR0100-01` | `IF-TASK-01,RGR-01,CAND-01,PUB-02` | `ARC-03,04,05,06,09,15` | CAS/idempotency/immutable attempt primitives及U/C | I：barrier并发lease/stage/commit/ref/candidate/operation，恰一winner |
| `NFR-0200 / AC-NFR0200-01` | `IF-PROMPT-02,TASK-01,CI-02,SEC-01` | `ARC-01,03,04,11,13` | capability、env/credential boundary、secret pipeline与C | I+CE+S：fork CI最小权限、canary覆盖prompt/diff/log/evidence |
| `NFR-0300 / AC-NFR0300-01` | `IF-RGR-01,CI-02,PUB-02,TRACE-01` | `ARC-05,06,11,15,16` | durable intent、startup reconcile、unknown/needs_attention及U/C | I+E：Red/Green/CI/tag/publish/cleanup确认边界kill与安全resume |
| `NFR-0400 / AC-NFR0400-01` | `IF-TRACE-01,WFR-01` | `ARC-16,01` | append-only audit、status分型、tamper-detecting digest与C | I+E：全流程actor/time/attempt/input/output，摘要不可篡改原证据 |
| `NFR-0500 / AC-NFR0500-01` | `IF-IMPL-01,TEST-02,CI-02,BLD-02` | `ARC-02,08,11,12` | contract-driven adapter capability/unsupported diagnostics与C | I+E+CE+A：Python/Node异构宿主，保留hooks/workflows/rules且无默认泄漏 |
| `NFR-0600 / AC-NFR0600-01` | `IF-MIG-01,WFR-01,PROMPT-02,TRACE-01` | `ARC-01,02,16` | migration/read-only export/CAS、single-current authority及U/C | I+E：legacy/no-R/prompt/schema、中断重试且无伪造/双写/重复operation |

### 14.7. Trace cardinality 与 CI closure

| 统计 | 数量 | Gate |
|---|---:|---|
| Functional Requirements | 30/30 | 每项恰有一个stable `AC-FRXXXX-01`策略根 |
| Non-functional Requirements | 6/6 | 每项恰有一个stable `AC-NFRXXXX-01`策略根 |
| Acceptance sections | 36/36 | `ac-trace`双向解析Acceptance与tests metadata |
| 003 observable IF | 16/16 | `workflow-contract`唯一identity/schema且至少被一个AC引用 |
| inherited machine contracts | 7/7 | current 002 contract validator与consumer owner均存在 |
| ARC components | 16/16 | 每个AC至少一个owner；每个ARC至少被IF或trace责任引用 |

`ac-trace`导出有向边而非仅计数：requirement→AC、AC→required IF/layers/gates、IF→primary/supporting ARC、AC→task、task→Red/G/code、AC→tests/evidence、candidate→CI/artifact/security/review、release→decision/publish/archive。正向缺边、反向orphan、重复AC identity、未知IF/ARC、required layer无evidence或同一evidence冒充不同candidate均失败。

---

## 15. 技术决定、迁移兼容、拒绝方案与残余风险

### 15.1. Architecture decision record

| 决定 | 选择与版本策略 | 解决问题 | 放弃方案 | 主要风险/缓解 |
|---|---|---|---|---|
| Runtime baseline | 继承Python `>=3.11`；canonical CI为3.12，unit覆盖3.11–3.14 | 与Louke现有dogfood事实一致并验证声明范围 | 本Spec迁移语言/runtime | Python新版本依赖兼容；矩阵required且lock drift阻断 |
| Metadata store | stdlib `sqlite3`/SQLite，WAL、foreign keys、CAS transaction | 单project并发、history、recovery、唯一约束 | JSON/TOML+lock、PostgreSQL | network FS不安全；限定本地store并做integrity/read-only recovery |
| Evidence blobs | SHA-256 content-addressed filesystem + SQLite metadata | 大evidence不膨胀DB，保持完整性/去重 | 全部塞DB、仅保存路径 | orphan/磁盘满；atomic rename、digest readback、保留根与GC隔离 |
| Serialization | 受限canonical JSON，无float、schema first | 稳定identity、跨重启可复算 | pickle、非canonical JSON、时间/名称identity | Unicode/path差异；固定规则并做contract vectors |
| Git integration | system Git plumbing/porcelain中受控子进程，最低Git `2.39`；`commit-tree/update-ref <ref> <new> <old>`实现OID CAS | 创建真实objects、临时index、独立readback与sibling lineage | GitPython/libgit2、Agent直接Git | Git版本/平台差异；启动capability probe、argv执行、Ground Truth集成 |
| External side effects | durable intent + provider query/readback saga | 无分布式事务条件下安全处理ack loss/partial | 假两阶段提交、盲重试、自动rollback不可变资源 | provider eventual consistency；bounded polling与needs_attention |
| GitHub integration | REST/Checks/Actions/rules adapter；default protocol stand-in，protected/manual real sandbox | fork安全且可测partial/unknown | 每PR生产credential、仅mock内部方法 | stand-in漂移；provider contract tests+隔离real smoke |
| CI Actions | `checkout/setup-python/upload-artifact`固定§13.1 commit SHA | supply-chain可复现 | movable major tags | SHA更新维护成本；显式upgrade使old evidence stale |
| Host commands | 只消费`IF-PC/TST/CI/REL/BLD/PUB/PRM-01` revision | 跨Python/Node且不猜路径 | Louke命令全局默认、Shield临场脚手架 | inherited contract缺失；capability diagnostic并阻断baseline |
| Artifact identity | raw-byte SHA-256 + embedded version + clean-installed outlets | branch/tag不能冒充可运行artifact | 只验source/tag/filename | build nondeterminism；每attempt clean build和逐件evidence |
| Agent isolation | subprocess/session sandbox、env/path/capability allowlist、patch-only output | 防credential/authority泄露和越界写 | 信任prompt自律、把Git token给Agent | OS sandbox能力不同；最小环境+post-run tree scan+security gate |
| Time/concurrency tests | injected clock/UUID、barrier、真实SQLite/Git/store | 可重复证明timeout/CAS/restart | sleep-based测试、mock核心判定 | fixture复杂；Ground Truth隔离和独立namespace |
| Cache/message queue | 不引入共享cache或broker；current来自SQLite，dispatch recovery扫描durable intents | 避免第二authority和额外服务 | Redis/queue作为状态源 | 大规模吞吐受限；当前单project单写者范围足够，指标触发后续独立Spec |

本Spec不新增第三方Python runtime库：SQLite、hash、JSON、subprocess、archive extraction与基础HTTP能力均使用stdlib或宿主当前已锁定依赖；pytest、coverage、mypy、build、setuptools、pre-commit与browser tooling的精确版本继承当前project lock/config并写入evidence，003不得静默升级。缺lock或版本无法readback是`IF-IMPL-01/QUAL-01` blocker，不由Human选版本。

### 15.2. Migration 与 compatibility

Runtime store schema使用单调整数版本与migration digest。启动发现旧schema时先取得project migration lease，生成只读backup及SHA-256，再在SQLite transaction中执行有序migration并做foreign-key/integrity/current-pointer检查；全部成功才更新schema version。transaction失败回滚到旧schema并保持只读diagnostic，不在部分新schema上dispatch。较新schema由较旧binary打开时只读拒绝，禁止自动downgrade。

legacy workflow按以下确定规则处理：

| Legacy事实 | Canonical处理 |
|---|---|
| 完整、可验证且source revision未变 | 以`IF-MIG-01` CAS迁移，保存source→target identity map和migration evidence |
| 缺program evidence的PASS/阶段完成 | 保留原始历史，canonical status=`UNKNOWN/legacy_unverified`；不能满足current gate |
| 缺private Red ref或`B/R/G` lineage | 明确记录`lineage_unavailable`；不伪造`R`、fingerprint或review |
| 旧Agent/Maestro声称commit/PASS/推进 | 作为untrusted legacy note保留；Git/evidence readback决定可验证事实 |
| 旧prompt/schema | 保存原digest并只读导出；新dispatch只用`IF-PROMPT-02` canonical bundle |
| 进行中的外部publish事实 | 有精确provider IDs/targets时导入durable intent并query；否则needs_attention，禁止重试create |
| 无法唯一映射的stage/current | 保持legacy只读，不创建第二current；用户可查看export但不能从猜测状态继续 |

迁移idempotency key为`source store identity + source revision + target schema`；process kill后重复执行先查询现有mapping，内容相同返回同结果，内容不同冲突。新run只写canonical Runtime store；禁止legacy/canonical dual write和两个commit authority。

旧CLI/Workbench入口可保留兼容adapter，但它们只把命令翻译为`ARC-01`公开command并消费`IF-WFR-01`，不能直接写旧stage/store。Keeper不再作semantic dispatch；Maestro仅advisory且无spawn/advance/waive/commit/release/archive权限。Python与Node宿主通过各自project-local contracts接入同一ARC拓扑；unsupported adapter返回capability diagnostic，不回退为Louke Python默认。

### 15.3. 明确拒绝的实现方案

1. **Agent直接commit/push/ref/state/gate/publish**：破坏单一authority、scope enforcement和独立evidence，拒绝。
2. **把`R` merge/cherry-pick为`G` parent**：破坏sibling lineage与`R→G`实现差异证明，拒绝；`G.parent`始终为`B`。
3. **普通pre-commit/CI运行私有Red**：会把预期失败当普通质量失败并泄漏private ref，拒绝。
4. **同名GitHub check或branch/tag作为成功证明**：identity不足，拒绝；必须绑定repository/workflow/SHA/attempt/jobs与artifact/provider readback。
5. **用数据库transaction包住Git/provider调用**：无法实现跨系统原子性且会长期持锁，拒绝；采用durable intent saga。
6. **ack loss后blind retry或`--skip-existing`**：可能重复不可变副作用且无法证明内容相同，拒绝；先query并比较精确identity。
7. **只运行本Spec新tests、非法skip/quarantine或低层替代E2E**：不能证明历史回归与用户journey，拒绝。
8. **source/tag版本验证替代artifact/install验证**：不能证明交付物身份和可运行出口，拒绝。
9. **legacy与canonical双写、伪造旧Red/PASS**：制造双current authority和虚假trace，拒绝。
10. **让Human选择technical route/adapter/故障归因**：产品决策与技术判定混淆，拒绝；owner、adapter和route由本文及current contracts锁定。

### 15.4. 残余技术风险

| 风险 | 影响 | 已定缓解 | Release语义 |
|---|---|---|---|
| GitHub plan/token不支持ruleset完整readback | required protection无法确认 | capability probe、保留用户规则、protected/manual real readback | `needs_attention`，不得publish |
| provider最终一致性超过deadline | run/tag/release/upload事实暂不可判定 | stable identity、bounded poll、后续同identity reconcile | `UNKNOWN`，不得推断PASS/FAIL |
| 不可变publish资源部分成功 | 无法真实rollback | operation DAG、逐项query、resume/forward-fix | 保持publishing/needs_attention，已确认项不重复 |
| SQLite所在磁盘损坏、满或被网络共享 | current/evidence不可安全写 | local-only约束、integrity check、atomic blob、只读recovery和backup digest | fail closed；不dispatch/不release |
| hooks/scanners/build产生非确定输出 | flaky gate或artifact digest变化 | tool/config lock、clean environment、全量rerun、保存tool/env/inventory | 任一不确定为FAIL/UNKNOWN |
| secret scanner false negative/positive | 泄漏或阻塞 | pattern+entropy+canary、结构化allowlist、Judge与人工operator rotation边界 | 命中阻断；dismissal仅按policy且敏感项不可waiver |
| stand-in与真实GitHub/provider漂移 | PR证据不能代表生产协议 | provider contract tests、隔离real smoke、mode identity分离 | real required处not-run不能被stand-in替代 |
| legacy缺Red/provider identity | 无法证明旧lineage或安全恢复副作用 | 只读`legacy_unverified`、不伪造、精确事实才迁移 | 旧PASS不满足新gate；未知publish需attention |
| 36-AC全链与Python矩阵增加CI时间 | feedback变慢、取消/flake概率提高 | deterministic cache、并行fan-out、barrier而非sleep、保留partial diagnostics | required job仍不可降层或跳过 |
| inherited project-local contract缺失/漂移 | 无法确定命令、artifact或adapter | baseline capability/identity validator与明确owner | blocker，不让Devon/Shield/Human猜测 |

这些是已分配owner和失败语义的技术风险，不是等待Human决定的架构选项。只有产品级release version、交付物或权限合同在上游发生变化时才返回需求流程；工具故障、provider不确定和实现缺陷按本设计自动路由或进入`needs_attention`。
