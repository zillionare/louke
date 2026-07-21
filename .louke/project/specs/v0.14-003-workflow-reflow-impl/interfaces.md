# 工作流重构：实现、验证、安全与发布闭环 — Public Interfaces

## 0. 文档身份、边界与通用约定

| 项 | 合同 |
|---|---|
| Spec / artifact | `v0.14-003-workflow-reflow-impl` / `.louke/project/specs/v0.14-003-workflow-reflow-impl/interfaces.md` |
| 绑定输入 | Story `sha256:2a04c965b8c97a34a6aec9cf5a7aa1418d84f394830abe5bdf32c2333a10ea3e`；Spec `sha256:a5c95c7a7ea1f8237913d9779fbc598d679211ece9be314ace944874b706280a`；Acceptance `sha256:a19e25689e59f722d2b72d6903ce4be1b333cf0441c5e3b14a351f6566dfe287` |
| 本文接口集 | 003 Runtime observable `16` 个；继承 002 machine-contract `7` 个；合计 `23` 个稳定 identity |
| 权威边界 | Runtime 是 workflow current、正式 Git、evidence、provider side effect 的唯一写 authority；Human 只提交允许的产品动作；Agent/Prism/Judge 只返回 manifest/schema 约束的非可信 proposal、patch 或 verdict |
| Schema 基线 | JSON 为 UTF-8 canonical JSON；object key 排序、无浮点/NaN/Infinity、未知字段拒绝；schema 默认 `additionalProperties:false`；digest 为 `sha256:<64 lowercase hex>`，Git OID 为仓库实际 object format |
| 公共读取 | authenticated Project member 可经 Workbench 或 `/api/v14/runs/{run_id}/...` 读取本文定义的 current/history projection；evidence blob 只通过其 `evidence_id`、digest、media type、redaction status 暴露 |
| Evidence envelope | `{evidence_id,kind,subject_id,attempt_id,input_identities,producer,tool_identity?,environment_identity?,status,output_digest,observed_at,supersedes?}`；`status=PASS|FAIL|STALE|SKIP|UNKNOWN`，摘要不得覆盖原状态或 bytes |
| Command envelope | `{command_id,run_id,actor,expected_workflow_revision,idempotency_key,action,payload}`；成功或失败均回 `{command_id,status,result?,error?,workflow_revision}`；相同 key+bytes 返回相同结果，不同 bytes 返回冲突 |
| Error envelope | `{code,message,subject_id?,expected?,actual?,retryable,owner,remediation,evidence_ids:[]}`；不得含 credential、secret 原文或未脱敏 provider response |
| CAS / history | current pointer 以 expected revision/OID CAS；attempt、event、evidence、decision、operation 只追加。`missing|stale|cancelled|timeout|partial|unknown` 均不满足 PASS gate |
| 时间与重试 | timestamp 只用于审计，不用于 identity 或 lineage；重试复用 logical identity 并新增 execution attempt，只有 contract/definition 标记幂等或 reconcile-safe 的操作可自动重试 |
| `modules` 规则 | 每节列出 architecture `ARC-*` producer/consumer；本文 23 个接口均跨至少两个模块，Shield 必须提供 integration evidence |

本文只定义外部可观察数据、命令、状态、错误与证据，不规定内部类、私有方法、缓存或数据库表。002 machine-contract 的 payload 不在本文复制；§17 仅作精确引用和消费边界。

---

## 1. `IF-IMPL-01` — Implementation baseline 与 Pre-commit reconcile readback

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-IMPL-01`；Primary `ARC-02`；证明 M-DESIGN 输入、workspace attribution 与 inherited `IF-PC-01` 已形成可 dispatch 的 implementation baseline |
| `modules` | `ARC-02` producer；`ARC-01,ARC-03,ARC-04,ARC-05,ARC-10` consumers（跨模块） |
| Caller / authority | Runtime 发起 reconcile、运行 project-local pre-commit adapter及受控 infrastructure commit；Archer/Devon只读诊断，不能安装 hook 或批准 drift |
| Input schema / identity | `{run_id,attempt_id,expected_workflow_revision,base_commit,requirements_digests,design_manifest:{revision,digest,program_evidence,prism_review},workspace_snapshot:{tree_digest,diffs:[{path,digest,source}]},precommit_contract:{instance_revision,instance_digest,schema_ref}}` |
| Read / output | `GET /api/v14/runs/{run_id}/implementation-baseline` → `{baseline_id,attempt_id,status,input_identities,attribution:[{path,source,disposition}],precommit:{operation_id,entry,tool_version,config_digest,hook_stage_digests,preserved_hooks,readback_status},infrastructure_commit?,dispatch_eligible,errors:[],evidence_ids:[]}` |
| Status / transition | `pending→reconciling→ready|blocked|needs_attention|stale`；只有 design program+Prism current、workspace全部归属、hook readback=`in_sync` 后 `ready`；tracked managed config变化可产生受控 commit并发布新 baseline |
| Persistence / evidence | 每 reconcile attempt immutable；保存 before/after tree、contract/schema/prompt/design digest、command/exit、readback及Git OID；本地 hook identity只记 evidence，不伪装成 tracked commit |
| Permission / trust boundary | repository hooks/config是不可信可执行输入，只执行 contract argv/cwd/env allowlist；Runtime拥有本地 Git写权限，Agent无；external/Human diff必须保留且不得静默覆盖 |
| Deterministic errors | `IMPL_DESIGN_NOT_CURRENT`, `IMPL_WORKSPACE_DIRTY_UNATTRIBUTED`, `IMPL_BASELINE_CONFLICT`, `IMPL_PC_CONTRACT_MISSING`, `IMPL_PC_INSTALL_FAILED`, `IMPL_PC_READBACK_MISSING`, `IMPL_PC_DRIFT`, `IMPL_HOOK_REWRITE_UNVERIFIED`, `IMPL_INFRA_COMMIT_CONFLICT`, `IMPL_HOST_UNSUPPORTED` |
| Idempotency / concurrency / CAS | identity=`sha256(input digests + base_commit + IF-PC-01 revision)`；同输入重放复用ready事实；workspace/tree/contract变化必须新attempt；infrastructure commit以expected branch OID CAS，冲突不force |
| Retry / recovery | command失败可在同logical reconcile下新增execution attempt；hook已写但DB未确认时重新readback，精确匹配才补确认；drift/external diff先重新snapshot再决定新baseline或return |
| Related requirements / AC | `FR-0100`, `NFR-0500`；`AC-FR0100-01`, `AC-NFR0500-01` |
| Test Plan layer / runner | `U+C+I`，兼容性另`E+CE+A`；unit runner与`tests/e2e/run-project-venv integration`，`baseline_precommit_matrix/host_matrix`；gates=`unit,workflow-contract,integration,e2e-standin,ci-e2e,artifact-verify` |

---

## 2. `IF-WFR-01` — WorkflowRun / Project current、历史与允许动作

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-WFR-01`；Primary `ARC-01`；把 canonical context、聚合状态、领域 evidence links、用户动作和只读历史作为唯一公开流程事实 |
| `modules` | `ARC-01` producer；`ARC-02..ARC-16` consumers/producers；Workbench/API/CLI consumer（跨模块） |
| Caller / authority | authenticated Project member 可读；Human 可提交界面显示为 enabled 的 `Release|Delay|Return|Cancel`；Runtime 可提交 definition 声明的 `continue|retry|reconcile|technical_return|start_hotfix`；Agent 不可调用状态转换 |
| Read input / identity | `GET /api/v14/runs/{run_id}?history_cursor=&limit=`；`GET /api/v14/projects/{project_id}/current`；精确 identity 为 `{project_id,run_id,release_id,workflow_definition:{revision,digest},workflow_revision}` |
| Read output | `{identity,canonical_context,state,status,subject_pointers:{graph?,task?,candidate?,preview?,publish?,archive?},allowed_actions:[{action,visible,enabled,reason?,target_enum?}],freshness,active_attempt?,last_confirmed_step?,blocking_errors:[],evidence_links:[],history_cursor,continue_url,next_release_eligibility}` |
| Context / status enum | context=`M-IMPL|M-TEST|M-VERIFY|M-SECURITY|M-RELEASE|M-PUBLISH|M-MILESTONE|HISTORY`；status=`running|blocked|release_waiting|returned_upstream|publishing|needs_attention|closing|complete|stale|cancelled|read_only`；evidence status 仍使用 §0 五值 |
| Command input | `POST /api/v14/runs/{run_id}/commands` 使用 §0 Command envelope；`Return` 必须带 `{preview_id?,target,reason}`，`start_hotfix` 必须带 `{source_contract,issue_id,source_version,reproduction_digest}`，waiver/retry/reconcile 参数只接受 definition/policy 枚举 |
| Command output | `accepted|rejected|conflict|already_applied`，返回 transition/decision/attempt identity、before/after revision、changed pointers、stale/superseded evidence IDs 和最新 `allowed_actions`；异步动作 `accepted` 不等于 gate PASS |
| Surface / visible behavior | Workbench 当前 Project 是自然入口；running 显示 attempt/last confirmed step；blocked 显示 owner/category/remediation；stale/dirty/conflict 先刷新且禁止越过；publishing/closing 隐藏 Release/Delay/Return；complete 只能从 history 打开并显示下一 release 资格 |
| State transition | 仅 WorkflowDefinition 中的边可发生；技术 gap 需绑定 Archer+Prism evidence 后 `technical_return`，产品 gap 需 Human 允许；合法 return 原子发布目标 context 和 dependent stale closure；非法 stage string 不改变 current |
| Persistence / evidence | current revision CAS 与 immutable event 同事务；每 event 含 actor/time/attempt/input/output/decision identity；history append-only且可链接各领域原始 evidence；summary 不可改变状态 |
| Permission / trust boundary | Human command 已认证但 payload 不可信，须验证角色、CSRF/replay、allowed action 和 expected revision；Agent/legacy UI/兼容 CLI 无第二 current 写入口；credential 不进入 command/evidence |
| Deterministic errors | `WFR_NOT_FOUND`, `WFR_REVISION_CONFLICT`, `WFR_ACTION_NOT_ALLOWED`, `WFR_TARGET_NOT_ALLOWED`, `WFR_EVIDENCE_NOT_CURRENT`, `WFR_PUBLISH_ALREADY_STARTED`, `WFR_CANCEL_FORBIDDEN_AFTER_EFFECT`, `WFR_READ_ONLY`, `WFR_NEEDS_ATTENTION` |
| Idempotency / concurrency / CAS | `command_id+idempotency_key` 唯一；同 bytes重放返回原结果，异 bytes为 `WFR_IDEMPOTENCY_CONFLICT`；并发 transition 恰一 expected revision CAS成功；loser读取新 current，不覆盖 |
| Retry / recovery | 重启先 reconcile durable intents再开放写动作；客户端断线按 command ID 查询，禁止盲重交；过期客户端得到 current identity 后刷新；unknown 只显示 `reconcile`，不显示跨 gate `continue` |
| Related requirements | `FR-0100,0300,0400,1300,1400,2000,2100,2300,2400,2500,2600,2700,3000`；`NFR-0300,0400,0600` |
| Related AC | `AC-FR0100-01, AC-FR0300-01, AC-FR0400-01, AC-FR1300-01, AC-FR1400-01, AC-FR2000-01, AC-FR2100-01, AC-FR2300-01, AC-FR2400-01, AC-FR2500-01, AC-FR2600-01, AC-FR2700-01, AC-FR3000-01, AC-NFR0300-01, AC-NFR0400-01, AC-NFR0600-01` |
| Test Plan layer / runner | `U+C+I+E+CE+S` 按具体 AC；`tests/e2e/run-project-venv integration` 与 `... e2e --profile all --runtime both`；hotfix另 `ci-e2e`；gates=`unit,workflow-contract,integration,e2e-standin,ci-e2e,security` |

---

## 3. `IF-TASK-01` — Implementation task DAG、manifest 与 write lease

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-TASK-01`；Primary `ARC-03`，manifest/lease authority `ARC-04`；闭合 task graph、每 attempt 执行合同和单写者归属 |
| `modules` | `ARC-03,ARC-04` producers；`ARC-01,ARC-05,ARC-08` consumers（跨模块） |
| Caller / authority | Archer 仅按授权 schema 提交 graph proposal；Runtime 校验、分配 revision、物化 manifest和 lease；Devon/Shield只消费自己的 current manifest，不能改 graph/lease |
| Graph input / identity | `{run_id,baseline_id,requirements:{fr_ids,nfr_ids,ac_ids,digests},design_refs,prompt_schema_refs,tasks:[{task_id,issue_id,fr_ids,nfr_ids,ac_ids,objective,depends_on,write_scopes,forbidden_scopes,devon_responsibility,shield_responsibility,contracts,commands,completion_outlets}]}`；`graph_revision=sha256(canonical graph+baseline+requirements/design digests)` |
| Manifest input / identity | `{run_id,task_id,attempt_no,graph_revision,baseline_commit,issue/fr/nfr/ac refs,design_refs,phase,write_scopes,forbidden_scopes,test_commands,external_diff_snapshot,prompt_bundle,schema_refs,output_contract,deadline,retry_policy}`；`manifest_digest`参与attempt identity |
| Read / output | `GET /api/v14/runs/{run_id}/task-graph` 与 `/tasks/{task_id}/attempts/{attempt_no}` → graph diagnostics/closure、manifest、`lease:{lease_id,holder_role,session_id,status,expires_at,workspace_digest}`, external diff attribution、allowed phase actions、evidence links |
| Status / transition | graph=`proposed|validating|waiting_prism|current|invalid|stale`；task=`pending|ready|leased|blocked|return_requested|stale|cancelled|complete`；lease=`available|active|reconcile_required|released|expired|conflict`；依赖 complete 且 graph review current 才 ready |
| State transition / persistence / evidence | duplicate/missing dependency/cycle/write-scope conflict/orphan AC/task/缺责任或出口分别出稳定 diagnostic；每次graph validation、Prism link、graph revision、manifest、lease CAS与external diff attribution形成不可改写evidence；Issue只作需求 identity，不为内部task新建重复Issue |
| Permission / trust boundary | path先canonicalize并拒绝绝对路径、`..`、NUL、symlink/hardlink escape及forbidden scope；external/Human diff是不可信内容，保留 before/after digest和来源；Agent无 lease授予权 |
| Deterministic errors | `TASK_DUPLICATE_ID`, `TASK_DEPENDENCY_MISSING`, `TASK_GRAPH_CYCLE`, `TASK_SCOPE_CONFLICT`, `TASK_AC_ORPHAN`, `TASK_ORPHAN`, `TASK_MANIFEST_INCOMPLETE`, `TASK_SCOPE_DENIED`, `TASK_BASELINE_STALE`, `TASK_EXTERNAL_DIFF_UNKNOWN`, `TASK_LEASE_HELD`, `TASK_LEASE_LOST` |
| Idempotency / concurrency / CAS | 同canonical graph得到同revision；内容变化必须新revision并使旧review/manifest stale；active普通feature lease唯一，acquire/renew/release用expected lease/workflow revision CAS；竞争恰一winner |
| Retry / recovery | session异常使lease=`reconcile_required`；重新snapshot workspace/baseline后可为同manifest开新session attempt；可归属Human diff生成新manifest，未知或baseline变化停止并return/reconcile，不覆盖文件 |
| Related requirements | `FR-0200,0300,0400,0500,2800`；`NFR-0100,0200` |
| Related AC | `AC-FR0200-01, AC-FR0300-01, AC-FR0400-01, AC-FR0500-01, AC-FR2800-01, AC-NFR0100-01, AC-NFR0200-01` |
| Test Plan layer / runner | `U+C+I+S`；unit/contract runner及`tests/e2e/run-project-venv integration`，`task_graph_matrix/lease_manifest_matrix`；gates=`unit,workflow-contract,integration,security` |

---

## 4. `IF-RGR-01` — Red/Green/Refactor program gate、private ref 与 lineage evidence

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-RGR-01`；Primary `ARC-05`，private ref authority `ARC-06`；公开每 task 的合法 Red、真实 `B/R/G/F` sibling lineage、正式 commit gate及cleanup引用 |
| `modules` | `ARC-05,ARC-06` producers；`ARC-01,ARC-07,ARC-09,ARC-10,ARC-16` consumers（跨模块） |
| Caller / authority | Devon提交phase-bound patch；Runtime独立执行program commands、创建Git object/ref/formal commit并readback；Prism只经`IF-REV-02`评审；任何Agent不能commit/ref/push或写PASS |
| Submission input / identity | `{run_id,task_id,attempt_id,manifest_digest,phase:"red|green|refactor|final",baseline_oid,expected_branch_oid,patch_digest,test_command_ids,reviewed_red_oid?,expected_private_ref_oid?,idempotency_key}`；phase与manifest scope必须一致 |
| Read / output | `GET /api/v14/runs/{run_id}/tasks/{task_id}/rgr` → attempts数组：`{attempt_id,phase,status,B,R?,G?,F?,red_ref?,trees,diffs:{B_R,R_G?,G_F?},failure_fingerprint?,program_checks,precommit?,review_links,no_change?,branch_readback,remote_readback,evidence_ids}` |
| Red gate result | `{test_only,format,syntax,secret,ac_trace,anti_pattern,static_checks,command_exit,assertion_identity,failure_category,failure_fingerprint,status}`；只有精确behavior assertion failure或已设计未实现symbol/type failure可PASS；unexpected test PASS为Red FAIL |
| Private ref contract | `R.parent=B`、`R.tree=B+approved test-only diff`；唯一ref=`refs/louke/rgr/{run}/{task}/{attempt}/red`，metadata绑定command/fingerprint/output；branch仍B，remote无R，普通pre-commit/CI不运行R |
| Green / Refactor result | Green要求获批R tests字节不变、target+全部历史unit+适用static/contract PASS；`G.parent=B`且含tests+最小实现。Refactor有变化为`F.parent=G`正式commit，无变化为绑定G的`no_change` evidence；均重跑Green checks，正式commit完整pre-commit |
| State transition / persistence / evidence | `red_authoring→red_program_passed→red_review_passed→green_authoring→green_program_passed→green_committed→refactor_committed|refactor_no_change→final_program_passed→final_review_passed→complete`；每attempt、OID、tree、failure/program/pre-commit/readback output形成append-only evidence |
| Permission / trust boundary | patch、test output、hook rewrite均不可信；Runtime按manifest scope/secret/path检查后才构造object。Git OID/tree/parent/ref/remote由独立Git readback；Red ref归档前不可删，只有`ARC-16`可按manifest CAS清理 |
| Deterministic errors | `RGR_PHASE_MISMATCH`, `RGR_RED_NOT_TEST_ONLY`, `RGR_RED_UNEXPECTED_PASS`, `RGR_RED_FAILURE_INVALID`, `RGR_RED_TRACE_MISSING`, `RGR_RED_REF_CONFLICT`, `RGR_RED_REVIEW_NOT_CURRENT`, `RGR_TEST_MUTATED`, `RGR_HISTORY_TEST_FAILED`, `RGR_GREEN_SCOPE_DENIED`, `RGR_PRECOMMIT_FAILED`, `RGR_LINEAGE_INVALID`, `RGR_BRANCH_CONFLICT`, `RGR_REFACTOR_CONTRACT_CHANGED`, `RGR_FINAL_GATE_FAILED` |
| Idempotency / concurrency / CAS | Red ref `update-ref(new,old)`：同attempt同OID为幂等，不同OID冲突；formal G/F以expected branch OID CAS；并发仅一方成功。相同phase input复用logical result，不同patch/tree必须新attempt，旧事实不改写 |
| Retry / recovery | Git更新后确认前崩溃按actual==new补确认、actual==old安全重试、其它冲突；Red review timeout可对同R重试，test bytes变化必须新R；Green需改test返回新Red；pre-commit改写后重验scope/lineage/checks |
| Related requirements | `FR-0500,0600,0700,0800,0900,1000,1100,1400,1500,2400,2500,2600,2700`；`NFR-0100,0300` |
| Related AC | `AC-FR0500-01, AC-FR0600-01, AC-FR0700-01, AC-FR0800-01, AC-FR0900-01, AC-FR1000-01, AC-FR1100-01, AC-FR1400-01, AC-FR1500-01, AC-FR2400-01, AC-FR2500-01, AC-FR2600-01, AC-FR2700-01, AC-NFR0100-01, AC-NFR0300-01` |
| Test Plan layer / runner | `U+C+I+E+CE+S`按AC；真实Git/subprocess的`tests/e2e/run-project-venv integration`，hotfix/return公开journey另E/CE；fixtures=`red_failure_matrix,rgr_git_matrix`；gates=`unit,workflow-contract,integration,e2e-standin,ci-e2e,security` |

---

## 5. `IF-REV-02` — Prism/Judge review snapshot、verdict、freshness 与 route

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-REV-02`；Primary `ARC-07`；给 task graph、Red、final task、Shield tests、whole candidate和security review一个精确绑定、不可自证的结果出口 |
| `modules` | `ARC-07` producer；`ARC-01,ARC-03,ARC-05,ARC-06,ARC-08,ARC-09,ARC-13` consumers/producers（跨模块） |
| Caller / authority | Runtime构造/dispatch并校验结果；Prism处理除security外review kind，Judge的security verdict经`ARC-13`接入；reviewer只返回schema output，无Git/program/state authority |
| Input schema / identity | `{review_kind:"task_graph|red|final_task|shield_tests|candidate|security",subject:{kind,id,revision},requirements_digests,design_digests,input_artifacts:[{identity,digest}],program_evidence:[{id,digest,status}],reviewer_role,reviewer_execution_bundle,manifest_digest,attempt_id}`；`review_id=sha256(kind+subject+有序input/evidence digests+role)` |
| Result / output | `GET /api/v14/runs/{run_id}/reviews/{review_id}` → `{review_id,kind,subject,attempt_id,actor,input_snapshot_digest,program_evidence_ids,verdict:"PASS|REVISE",findings:[{id,severity,artifact,anchor,category,message,required_fix,route,fr_ids,ac_ids,interface_ids}],advisory:[],freshness,status,evidence_id}` |
| Status / transition | `queued|running|PASS|REVISE|FAIL|STALE|UNKNOWN`；invalid schema/timeout/crash=`FAIL|UNKNOWN`而非REVISE；只有schema-valid且input current的PASS可解锁下一步；input变化追加STALE event |
| Persistence / evidence | 原始脱敏review output、snapshot manifest、reviewer bundle/role、input/output digest和validated result append-only；candidate reviewer execution bundle不得是未信任candidate自证bundle |
| Permission / trust boundary | source/diff/prompt/reviewer output均不可信；Runtime校验scope、schema、identity、secret和capability；Prism/Judge不能运行command、改文件、持久化PASS、推进状态或读credential |
| Deterministic errors | `REV_KIND_UNSUPPORTED`, `REV_INPUT_INCOMPLETE`, `REV_PROGRAM_EVIDENCE_NOT_CURRENT`, `REV_SUBJECT_MISMATCH`, `REV_SCHEMA_INVALID`, `REV_ACTOR_INVALID`, `REV_BUNDLE_UNTRUSTED`, `REV_OUTPUT_SECRET`, `REV_TIMEOUT`, `REV_STALE`, `REV_ROUTE_INVALID` |
| Idempotency / concurrency / CAS | 同review ID的重复dispatch若已有validated result则回读，不二次写；同ID不同input为integrity conflict；多个attempt可并存，但current subject pointer只CAS到精确fresh verdict |
| Retry / recovery | timeout/crash可对同snapshot开新execution attempt；REVISE按finding route建立对应新task/test/candidate attempt；任何subject bytes变化产生新review ID，旧PASS永不恢复为current |
| Related requirements | `FR-0300,0700,1000,1100,1200,1800,1900,2900` |
| Related AC | `AC-FR0300-01, AC-FR0700-01, AC-FR1000-01, AC-FR1100-01, AC-FR1200-01, AC-FR1800-01, AC-FR1900-01, AC-FR2900-01` |
| Test Plan layer / runner | `U+C+I+S`按kind；contract runner与`tests/e2e/run-project-venv integration`，`review_agent_matrix/security_matrix`；gates=`unit,workflow-contract,integration,security` |

---

## 6. `IF-TEST-02` — Integration/E2E submission、suite execution 与 defect route

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-TEST-02`；Primary `ARC-08`；约束 Shield 测试资产、证明 required suites真实执行并给四类缺陷确定路由 |
| `modules` | `ARC-08` producer；`ARC-01,ARC-04,ARC-07,ARC-09,ARC-10,ARC-11,ARC-16` consumers（跨模块） |
| Caller / authority | Runtime从Test Plan和inherited `IF-TST-01`生成submission task；Shield只提交授权integration/e2e patch；Prism评审patch；Runtime执行runner和创建受控测试commit |
| Submission input / identity | `{run_id,test_task_id,attempt_id,manifest_digest,implementation_tip,contract:{revision,digest,schema_ref},test_plan:{revision,digest},authorized_paths,required_layers,required_ac_ids,patch_digest,metadata_inventory,public_interface_ids}` |
| Execution input | `{review_id,reviewed_patch_digest,expected_branch_oid,runner_id,command_id,cwd,env_allowlist,fixture_manifest_digest,suite_manifest:[{suite_id,layer,required,ac_ids}],timeout_seconds}`；命令必须逐字来自project-local contract |
| Read / output | `GET /api/v14/runs/{run_id}/tests` → `{submissions:[{identity,paths,patch_digest,ac_metadata,interfaces,review,status}], executions:[{attempt_id,commit,runner,environment,fixture,command,suite_inventory,results,covered_ac_ids,status,defect?}],controlled_test_commit?,trace_edges,evidence_ids}` |
| Result / status | submission=`draft|scope_valid|waiting_prism|REVISE|approved|stale`；execution=`queued|running|PASS|FAIL|UNKNOWN|STALE`。required suite 的skip/not-run/timeout/cancel/unknown使总体非PASS；局部selector结果只能diagnostic |
| Defect route | `{category:"test_or_fixture|implementation|design|requirement",owner:"Shield|Devon|M-DESIGN|M-SPEC_OR_ACC",anchors,evidence_ids,required_rerun_layers,review_required}`；技术归因由Runtime/Prism，不向Human提问 |
| State transition / persistence / evidence | approved patch→Runtime execution→全部required PASS→普通pre-commit/branch CAS→controlled test commit→trace current；patch、Prism、runner/suite/fixture、commit/readback和route各自形成append-only evidence；任何修复产生新attempt，旧结果保留且按依赖stale |
| Permission / trust boundary | Shield只能写contract paths，不可改产品代码、选择框架、降低层、读私有store或声明PASS；fixture/runner output不可信且先secret scan；Runtime Git/runner authority与Agent session隔离 |
| Deterministic errors | `TEST_PATH_DENIED`, `TEST_PRODUCT_CODE_CHANGED`, `TEST_FRAMEWORK_UNDECLARED`, `TEST_LAYER_DOWNGRADED`, `TEST_AC_METADATA_MISSING`, `TEST_PRIVATE_OUTLET_USED`, `TEST_REVIEW_NOT_CURRENT`, `TEST_SUITE_REQUIRED_MISSING`, `TEST_SUITE_SKIPPED`, `TEST_RUNNER_FAILED`, `TEST_DEFECT_ROUTE_INVALID`, `TEST_COMMIT_CONFLICT` |
| Idempotency / concurrency / CAS | submission identity绑定patch+manifest+contract+plan；同内容重放回原result，不同内容新attempt；执行绑定精确commit/runner/fixture；controlled commit以expected branch OID CAS，不覆盖并发变化 |
| Retry / recovery | runner crash保留partial JUnit/stdout digest并标UNKNOWN/FAIL；修复test/fixture回Shield，implementation保留tests回Devon，design/requirement按route；仅重跑合同要求的受影响层并重新review，required闭包仍须全PASS |
| Related requirements | `FR-1200,1300,1500,1700`；`NFR-0500` |
| Related AC | `AC-FR1200-01, AC-FR1300-01, AC-FR1500-01, AC-FR1700-01, AC-NFR0500-01` |
| Test Plan layer / runner | `C+I+E+CE+A`按AC；contract runner、`tests/e2e/run-project-venv integration`、`... e2e --profile all --runtime both`及CI readback；`test_suite_matrix/host_matrix`；gates=`workflow-contract,integration,e2e-standin,ci-e2e,artifact-verify` |

---

## 7. `IF-CAND-01` — Candidate freeze、write-disable 与 freshness projection

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-CAND-01`；Primary `ARC-09`；把唯一正式 commit 冻结为可验证 candidate，并公开clean/ancestry/write-disable及依赖变化后的精确 stale 集 |
| `modules` | `ARC-09` producer；`ARC-01,ARC-05,ARC-08,ARC-10,ARC-11,ARC-12,ARC-13,ARC-14` consumers（跨模块） |
| Caller / authority | 仅Runtime在全部implementation/Shield完成后请求freeze；Agent和Human只读；冻结后普通Agent写command统一拒绝，只有正式return/fix流程可创建新candidate cycle |
| Input schema / identity | `{run_id,release_id,expected_workflow_revision,expected_branch_oid,workspace_tree_digest,task_completion_ids,test_completion_id,requirements/design/interfaces/test_plan/contracts/prompts/config/policy digests,private_red_manifest_digest}`；`candidate_id=sha256(commit_oid+全部dependency digests)` |
| Read / output | `GET /api/v14/runs/{run_id}/candidate` → `{candidate_id,commit_oid,release_branch,freeze_attempt,status,workspace:{clean,tree_digest},formal_ancestry:{commits,private_red_present},completion_inputs,dependency_manifest,write_disabled,freshness,stale_evidence_ids,gate_links,history}` |
| Status / transition | `absent→freezing→frozen→verifying→candidate_review→security_review→releasable→awaiting_human_decision`；旁路=`blocked|stale|needs_attention`；只有clean、正式commits/current review/pre-commit齐全且无private R ancestry可frozen |
| Persistence / evidence | freeze snapshot、commit/tree/ancestry readback、dependency manifest和write-disable event immutable；current candidate pointer CAS；任一 dependency bytes/digest变化生成新candidate identity并追加旧证据STALE事件 |
| Permission / trust boundary | workspace/Git由Runtime独立readback，不信Agent clean声明；candidate source/tests/config是不可信可执行内容，后续只在隔离runner运行；private ref存在本身合法，但进入formal ancestry必须阻断 |
| Deterministic errors | `CAND_WORKSPACE_DIRTY`, `CAND_BRANCH_CONFLICT`, `CAND_TASK_INCOMPLETE`, `CAND_TESTS_INCOMPLETE`, `CAND_REVIEW_STALE`, `CAND_PRECOMMIT_STALE`, `CAND_PRIVATE_RED_IN_ANCESTRY`, `CAND_DEPENDENCY_MISSING`, `CAND_FREEZE_CONFLICT`, `CAND_WRITE_DISABLED`, `CAND_STALE` |
| Idempotency / concurrency / CAS | 相同commit+dependency set返回同candidate；同release current pointer竞争恰一freeze成功；commit相同但dependency变化也必须新identity；旧candidate/evidence不可就地复活 |
| Retry / recovery | freeze进程中断先重读workspace/branch/dependencies再CAS；失败不留下半冻结current；post-freeze mutation先标旧candidate stale并禁用Release，再完成新的task/test/freeze链；重连读取same current snapshot |
| Related requirements | `FR-1400,1800,1900,2000,2100`；`NFR-0100` |
| Related AC | `AC-FR1400-01, AC-FR1800-01, AC-FR1900-01, AC-FR2000-01, AC-FR2100-01, AC-NFR0100-01` |
| Test Plan layer / runner | `U+C+I+E+S`；unit/contract、`tests/e2e/run-project-venv integration`与公开e2e，`candidate_quality_matrix/release_ui_matrix/security_matrix`；gates=`unit,workflow-contract,integration,e2e-standin,security` |

---

## 8. `IF-QUAL-01` — Candidate 本地权威质量链 report

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-QUAL-01`；Primary `ARC-10`；证明同一candidate执行完整project-local静态、RGR、历史/required tests、trace、policy、兼容和真实build链 |
| `modules` | `ARC-10` producer；`ARC-01,ARC-05,ARC-07,ARC-08,ARC-09,ARC-12,ARC-13,ARC-14,ARC-16` consumers（跨模块） |
| Caller / authority | 仅Runtime按current contracts/policy运行；Devon/Shield可读失败诊断但不能选selector或标skip；Human不能waive required gate |
| Input schema / identity | `{candidate_id,commit_oid,contract_refs:{precommit,test,build},policy:{revision,digest},trace_manifest_digest,suite_manifest_digest,command_manifest:[{gate_id,argv,cwd,env_allowlist,timeout,required}]}`；report identity绑定全部input与toolchain |
| Read / output | `GET /api/v14/runs/{run_id}/candidates/{candidate_id}/local-quality` → `{report_id,candidate_id,status,gates:[{gate_id,command_identity,tool_version,all_files?,suite_inventory?,started_at,finished_at,status,exit,evidence_ids}],required_gate_set,aggregate,missing,skip_quarantine,trace_closure,build_link,freshness}` |
| Required gate set | format/lint/static/type、pre-commit config/install drift+all-files、RGR、全部历史unit、全部required integration/e2e/regression、AC双向trace、skip/quarantine、anti-pattern、policy、docs/migration/compat及真实build；不适用只可来自current contract/policy明示 |
| Status / transition | `queued→running→PASS|FAIL|UNKNOWN|STALE`；聚合仅全部required gate current PASS；fail/cancel/timeout/skip/missing/unknown均非PASS；局部selector report标`diagnostic`且不可进入candidate review |
| Persistence / evidence | 每gate保存candidate、argv/cwd/env names、tool/config digest、suite/all-files inventory、exit和raw output digest；aggregate链接原evidence；rerun为新attempt，不覆盖历史 |
| Permission / trust boundary | candidate命令是不可信代码，只在credential-less隔离环境按contract argv执行；env allowlist且stdout/JUnit上传前secret scan；Agent文字或既有CI绿色不替代本地执行 |
| Deterministic errors | `QUAL_CONTRACT_NOT_CURRENT`, `QUAL_GATE_MISSING`, `QUAL_COMMAND_FAILED`, `QUAL_TIMEOUT`, `QUAL_REQUIRED_SUITE_MISSING`, `QUAL_REQUIRED_SUITE_SKIPPED`, `QUAL_HISTORY_EXCLUDED`, `QUAL_SELECTOR_PARTIAL`, `QUAL_QUARANTINE_INVALID`, `QUAL_TRACE_INCOMPLETE`, `QUAL_BUILD_FAILED`, `QUAL_EVIDENCE_UNKNOWN`, `QUAL_CANDIDATE_STALE` |
| Idempotency / concurrency / CAS | report identity按candidate+manifests固定；可并行执行独立gate，但aggregate只CAS到相同candidate完整结果；同gate重复执行产生execution attempts并确定性聚合，不能混用其它candidate |
| Retry / recovery | runner crash保留已完成gate和partial诊断；修复前失败报告不变，修复导致bytes变化则先新candidate；纯环境可重试同candidate但必须重新证明受影响gate和完整required集合 |
| Related requirements | `FR-0800,1500,3000` |
| Related AC | `AC-FR0800-01, AC-FR1500-01, AC-FR3000-01` |
| Test Plan layer / runner | `U+C+I+E+S`；unit runner、`tests/e2e/run-project-venv integration`与`... e2e --profile all --runtime both`，`candidate_quality_matrix`；gates=`unit,workflow-contract,integration,e2e-standin,security,build-artifacts` |

---

## 9. `IF-CI-02` — GitHub candidate CI trigger/readback、required check 与 rules reconcile

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-CI-02`；Primary `ARC-11`；证明精确candidate运行托管CI完整suite，并确认唯一required check及Runtime-owned rules不破坏用户规则 |
| `modules` | `ARC-11` producer；`ARC-01,ARC-07,ARC-08,ARC-09,ARC-10,ARC-13,ARC-14,ARC-16` consumers（跨模块） |
| Caller / authority | Runtime GitHub adapter可push/trigger/query/reconcile；default PR job仅只读且无生产secret；protected/manual adapter持最小独立credential；Agent/Human不能伪造check或直接写rules |
| Trigger input / identity | `{candidate_id,repository_id,remote_url,commit_oid,workflow:{path:".github/workflows/louke-ci.yml",blob_oid,contract_revision,digest},trigger,correlation_id,required_suite_manifest_digest,expected_rules_revision}`；observation=`{repository_id,workflow_path@blob_oid,commit_oid,provider_run_id,run_attempt}` |
| Read / output | `GET /api/v14/runs/{run_id}/candidates/{candidate_id}/github-ci` → `{observation_id,mode:"stand-in|real",repository,workflow,commit,provider_run_id,run_attempt,status,jobs:[{id,name,status,conclusion,started,completed,evidence}],artifacts,suite_coverage,required_check,rules:{before,desired,actual,existing_rules_preserved,status},poll_attempts,evidence_ids}` |
| Required check contract | 只接受同repository/workflow blob/candidate SHA/run attempt的唯一`Louke CI / required`；其required jobs为`quality,workflow-contract,ac-trace,build-artifacts,artifact-verify,unit,integration,e2e-standin,ci-e2e,security`，release/manual另要求`protected-smoke`；每项必须`success` |
| Status / transition | `planned→pushed→triggered→running→PASS|FAIL|UNKNOWN|needs_attention|STALE`；failure/cancelled/timed_out/skipped/neutral/action_required/missing/unknown和required suite排除均非PASS；rules partial/mismatch=`needs_attention` |
| Persistence / evidence | 保存每次GitHub公开run/jobs/check/artifact/rules response digest、suite inventory/runner reports、provider identity、mode与credential boundary；同名其它SHA/check作为拒绝证据，不合并 |
| Permission / trust boundary | fork bytes不在高权限token下运行；workflow默认`contents:read`；规则写与provider真实smoke仅protected environment；第三方Action固定architecture锁定commit SHA；evidence上传前secret scan |
| Deterministic errors | `CI_CONTRACT_NOT_CURRENT`, `CI_PUSH_CONFLICT`, `CI_WORKFLOW_MISMATCH`, `CI_RUN_NOT_FOUND`, `CI_RUN_AMBIGUOUS`, `CI_COMMIT_MISMATCH`, `CI_REQUIRED_JOB_MISSING`, `CI_REQUIRED_JOB_NOT_SUCCESS`, `CI_SUITE_COVERAGE_INCOMPLETE`, `CI_REQUIRED_CHECK_AMBIGUOUS`, `CI_RULE_CAPABILITY_MISSING`, `CI_RULE_READBACK_MISMATCH`, `CI_API_UNKNOWN` |
| Idempotency / concurrency / CAS | 相同candidate不重复push；trigger用correlation且只接受唯一匹配run；rules reconcile只修改owner标记字段并用expected revision/ETag，保留用户规则；并发partial不得宣告PASS |
| Retry / recovery | run暂不可见按`2,4,8,16,30s`带jitter轮询至90分钟deadline；超时UNKNOWN；重启复用observation并query，不重复push/trigger；rules只补Runtime-owned差异，能力不足或多义冲突保持needs_attention |
| Related requirements | `FR-1700,2500`；`NFR-0200,0300,0500` |
| Related AC | `AC-FR1700-01, AC-FR2500-01, AC-NFR0200-01, AC-NFR0300-01, AC-NFR0500-01` |
| Test Plan layer / runner | `C+I+CE+S`，兼容性另`E+A`；contract、integration及托管workflow readback，`github_ci_matrix/host_matrix`；gates=`workflow-contract,integration,ci-e2e,security,e2e-standin,artifact-verify,Louke CI / required` |

---

## 10. `IF-BLD-02` — Canonical version、真实 artifact 与 install/runtime evidence

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-BLD-02`；Primary `ARC-12`；按 inherited release/build contracts 依序证明版本源、真实build、每件artifact内嵌版本以及安装/运行公开版本 |
| `modules` | `ARC-12` producer；`ARC-09,ARC-10,ARC-13,ARC-14,ARC-15` consumers（跨模块） |
| Caller / authority | 仅Runtime调用current `IF-REL-01/IF-BLD-01` adapter；Human只提供产品release identity，不能选版本文件/adapter；Agent不能build后自报verified或修改用户workspace |
| Canonical input / identity | `{candidate_id,commit_oid,human_release_identity,canonical_release_identity,external:{branch,tag,prerelease?},release_contract:{revision,digest},build_contract:{revision,digest},clean_workspace_id,attempt_id}`；Louke本次canonical=`0.14.0`、tag=`v0.14.0` |
| Louke artifact set | 必须恰一wheel `dist/louke-*.whl`与恰一sdist `dist/louke-*.tar.gz`，均由clean candidate执行`python -m build`产生；deployment outlet=`N/A`（本地包无独立deployment endpoint） |
| Read / output | `GET /api/v14/runs/{run_id}/candidates/{candidate_id}/artifacts` → `{verification_id,canonical_identity,external_mapping,adapter_identity,status,stages:{version_scheme_selected,version_source_prepared,artifacts_built,artifact_versions_verified,installed_runtime_versions_verified},artifacts:[{artifact_id,kind,path,digest,size,extracted_version,payload_manifest,install_environment,outlets:[{command,value,status}],status}],evidence_ids}` |
| Version outlets | wheel从`.dist-info/METADATA`、sdist从`PKG-INFO`提取Version；每件artifact独立clean venv安装后分别回读`lk --version`与`importlib.metadata.version("louke")`；四个outlet结果均须精确等于`0.14.0` |
| Status / transition | `scheme_selected→source_prepared→built→artifact_version_verified→installed_runtime_verified`；各stage单独evidence。只有全部artifact最终stage current PASS时aggregate=`verified`；后续not-run不得标PASS |
| Persistence / evidence | 保存source path/selector/digest、adapter/toolchain digest、build command/exit、枚举清单、raw-byte SHA-256、提取值、payload检查、clean-install环境和outlet stdout；artifact identity=`sha256(raw bytes)` |
| Permission / trust boundary | prepare只写隔离build workspace中contract声明version source；artifact是不可信archive，提取拒绝path traversal；build/install无发布credential；其它宿主仅消费其project-local contract，不套用Louke Python路径 |
| Deterministic errors | `BLD_RELEASE_IDENTITY_INVALID`, `BLD_CONTRACT_NOT_CURRENT`, `BLD_ADAPTER_FAILED`, `BLD_SOURCE_MISSING`, `BLD_SOURCE_VERSION_MISMATCH`, `BLD_COMMAND_FAILED`, `BLD_ARTIFACT_MISSING`, `BLD_ARTIFACT_EXTRA`, `BLD_ARTIFACT_CORRUPT`, `BLD_VERSION_UNEXTRACTABLE`, `BLD_VERSION_MISMATCH`, `BLD_PAYLOAD_MISSING`, `BLD_INSTALL_FAILED`, `BLD_OUTLET_MISMATCH`, `BLD_RESULT_UNKNOWN` |
| Idempotency / concurrency / CAS | 同candidate+canonical+contracts为verification logical identity；每attempt先清空隔离dist且只枚举本attempt产物；不得复用旧/不确定artifact；current verification pointer以candidate revision CAS |
| Retry / recovery | 任一阶段失败从source prepare开始新build attempt并重新枚举全部artifact；中断后的文件不接受；source/tag正确不能抵消artifact失败；contract/canonical变化使全部旧build/install evidence stale |
| Related requirements | `FR-1600,2300`；`NFR-0500` |
| Related AC | `AC-FR1600-01, AC-FR2300-01, AC-NFR0500-01` |
| Test Plan layer / runner | `C+I+E+A`，兼容性含`CE`；contract/integration、`python -m build`、逐artifact clean venv及公开e2e smoke，`release_artifact_matrix/host_matrix`；gates=`workflow-contract,integration,e2e-standin,build-artifacts,artifact-verify,ci-e2e` |

---

## 11. `IF-SEC-01` — Security program、Judge verdict、finding、skip/waiver 与 route

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-SEC-01`；Primary `ARC-13`；证明current candidate先完成policy program scans，再获得受限Judge语义审查，并公开可执行finding route |
| `modules` | `ARC-13` producer；`ARC-01,ARC-07,ARC-09,ARC-14,ARC-16` consumers（跨模块） |
| Caller / authority | Runtime执行scanner、构造Judge snapshot并校验verdict；Judge只返回findings；policy-authorized operator可提交允许的medium/low waiver，Human/Agent不能waive禁止项或写program PASS |
| Input schema / identity | `{candidate_id,commit_oid,policy:{revision,digest,required_scanners,waiver_rules,skip_rules,sensitive_boundaries},prompt_bundle,design_interfaces_digests,dependency_manifest,diff/full_code_refs,prior_findings,program_results:[{scanner_id,tool_digest,status,evidence_id}],candidate_review_id,attempt_id}` |
| Read / output | `GET /api/v14/runs/{run_id}/candidates/{candidate_id}/security` → `{security_id,candidate,policy,status,programs:[{scanner,status,evidence}],completeness,judge:{review_id,actor,bound_snapshot,verdict,status},findings:[{finding_id,location,severity,impact,required_fix,category,route,status}],waivers,skips,rerun_requirements,evidence_ids}` |
| Finding / waiver schema | route=`implementation|security_test|design|requirement`；waiver=`{finding_id,candidate_id,actor,reason,scope,issue_id,expires_at,policy_digest}`；skip=`{scanner,reason,scope,issue_id,owner,expires_at,policy_digest}`；任一字段缺失无效 |
| Status / transition | `program_scanning→waiting_judge→PASS|FAIL|UNKNOWN|STALE`；任一required scanner缺失/非PASS时不dispatch Judge或不接受PASS；finding修复必须新candidate并重走完整Verify、candidate Prism、program scans和Judge |
| Non-waivable | secret/credential、权限越界、发布完整性、RGR/CI/evidence伪造、critical/high及policy禁止项不可waiver；认证、权限、secret、支付、敏感数据变化不可用普通skip绕过 |
| Persistence / evidence | scanner命令/tool/policy/candidate/output digest、Judge exact snapshot/verdict和finding history append-only；secret命中只存rule、location hash和redacted fingerprint，原值不落盘/上传 |
| Permission / trust boundary | candidate、dependencies、scanner/Judge outputs均不可信；Judge无command/file/Git/state/provider/credential能力；credential只在Runtime operation边界，fork CI无生产secret |
| Deterministic errors | `SEC_POLICY_NOT_CURRENT`, `SEC_SCANNER_REQUIRED_MISSING`, `SEC_SCAN_FAILED`, `SEC_SCAN_UNKNOWN`, `SEC_SECRET_DETECTED`, `SEC_JUDGE_INPUT_INCOMPLETE`, `SEC_JUDGE_SCHEMA_INVALID`, `SEC_JUDGE_STALE`, `SEC_JUDGE_CAPABILITY_VIOLATION`, `SEC_FINDING_ROUTE_INVALID`, `SEC_WAIVER_FORBIDDEN`, `SEC_WAIVER_INVALID`, `SEC_SKIP_FORBIDDEN`, `SEC_SKIP_INVALID` |
| Idempotency / concurrency / CAS | security identity绑定candidate+policy+prompt+program result set；同snapshot可重试Judge为新execution attempt；waiver/skip按finding/scanner+candidate唯一且expected policy revision CAS；candidate变化全部失效 |
| Retry / recovery | scanner timeout可同candidate/policy重跑但仍UNKNOWN直到完整；Judge timeout对同snapshot重试；finding按route修复，新candidate后不能只重跑原scanner；secret输出无法证明脱敏则丢弃blob并FAIL |
| Related requirements | `FR-1900,2000,2900`；`NFR-0200` |
| Related AC | `AC-FR1900-01, AC-FR2000-01, AC-FR2900-01, AC-NFR0200-01` |
| Test Plan layer / runner | `C+I+E+CE+S`按AC；contract/integration、security pytest journeys、公开e2e及fork CI，`security_matrix/secret_canaries`；gates=`workflow-contract,integration,e2e-standin,ci-e2e,security` |

---

## 12. `IF-REL-02` — Release preview 与 Human `Release/Delay/Return`

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-REL-02`；Primary `ARC-14`；在Project current给Human完整、current、不可绕过的发布预览与三种决定出口 |
| `modules` | `ARC-14` producer；`ARC-01,ARC-09,ARC-13,ARC-15` consumers/producers；Workbench/API consumer（跨模块） |
| Caller / authority | authenticated且有release-decision权限的Human可提交三种动作；Runtime生成preview、验证gate/expected revision并持久化decision；Agent、CI、Judge不能代Human选择Release |
| Preview input / identity | `{candidate_id,canonical_identity,main_target,tag,requirements/issue/trace refs,user_change_digest,quality_id,ci_id,artifact_verification_id,candidate_review_id,security_id,risks,waivers,planned_operations,recovery_plan,workflow_revision}`；`preview_id=sha256(全部current inputs)` |
| Read / visible output | `GET /api/v14/runs/{run_id}/release-preview` → `{preview_id,status,candidate,canonical_version,main,tag,user_changes,issues,fr_ac_trace,tests_ci,reviews,security,artifacts:[{id,digest,version,outlets}],risks,waivers,planned_side_effects,recovery_plan,freshness,allowed_return_targets,actions,decision?,evidence_links}` |
| Action availability | gates running：Release disabled，Delay enabled，Return按definition；全部不可waiver evidence current PASS且workspace clean：三者enabled；dirty/stale/missing/FAIL/UNKNOWN/security blocked：Release disabled；publishing/closing/complete：三者hidden/disabled |
| Command input / output | `POST /api/v14/runs/{run_id}/commands`：`{action:"Release|Delay|Return",payload:{preview_id,candidate_id,reason?,target?}}`；Return reason非空且target为返回枚举。输出decision identity、new state/context、authorization或stale set和最新actions |
| State transition | `Release`原子创建唯一publish authorization并进入publishing；`Delay`进入release_waiting且不改变candidate/preview/provider事实；`Return`进入合法upstream context并传播dependent stale；非法动作不改变current |
| Surface feedback / recovery | 提交中动作disabled防重复；成功显示decision identity；失败定位gate/owner；stale client显示expected/current并要求refresh；Delay后从Project current可再次打开同candidate preview；reconnect按command ID/current server state恢复 |
| Persistence / evidence | preview immutable；decision含Human actor、command ID、preview/candidate、reason/target、before/after revision、time；任何candidate/evidence/artifact/plan变化生成新preview并使旧approval STALE |
| Permission / trust boundary | Human payload已认证但仍做allowed-action/CAS/replay校验，不能携带credential/provider command；Release authorization只供`ARC-15`消费，不直接暴露provider token |
| Deterministic errors | `REL_PREVIEW_NOT_READY`, `REL_PREVIEW_STALE`, `REL_REVISION_CONFLICT`, `REL_RELEASE_DISABLED`, `REL_GATE_NOT_CURRENT`, `REL_RETURN_REASON_REQUIRED`, `REL_RETURN_TARGET_INVALID`, `REL_ACTION_NOT_ALLOWED`, `REL_DECISION_CONFLICT`, `REL_ALREADY_PUBLISHING` |
| Idempotency / concurrency / CAS | command ID+preview唯一；同command重放返回同decision；并发三动作恰一workflow revision CAS成功；只有一个publish authorization，Delay/Return不会产生provider intent |
| Retry / recovery | ack loss按command ID query；不得改id重发Release；Delay重开若inputs current仍显示same preview，否则显示stale新preview；Return后修复须走新candidate/gate/preview，不恢复旧approval |
| Related requirements / AC | `FR-2100,2200`；`AC-FR2100-01, AC-FR2200-01` |
| Test Plan layer / runner | `U+C+I+E+S`；contract/integration与browser public journey `J-RELEASE-DELAY/J-RELEASE-RETURN/J-PUBLISH-CLOSE`，`release_ui_matrix/publish_matrix`；gates=`unit,workflow-contract,integration,e2e-standin,security` |

---

## 13. `IF-PUB-02` — Publish execute/reconcile operation ledger 与 provider fact readback

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-PUB-02`；Primary `ARC-15`；为每个发布副作用建立稳定intent/query/effect/result事实，并在ack loss/重启下避免重复不可变资源 |
| `modules` | `ARC-15` producer；`ARC-01,ARC-12,ARC-14,ARC-16` consumers（跨模块） |
| Caller / authority | 只有Runtime持current Human Release authorization后可execute/reconcile；provider adapter持最小credential；Agent/Human/CI不能直接创建tag/upload/release/deploy或补写confirmed |
| Input / operation identity | `{authorization_id,release_identity,candidate_id,artifact_set_id,publish_contract:{revision,digest},operation_kind,provider_namespace,canonical_target,payload_digest,predecessor_ids,credential_ref,idempotency_key}`；`operation_id=sha256(release+kind+namespace+target+payload digest)` |
| Applicable Louke DAG | `main candidate确认→canonical tag→wheel upload+sdist upload（逐件operation）→GitHub Release及精确assets→发布渠道clean-install/version/smoke`；其它宿主完全由current `IF-PUB-01`显式DAG决定 |
| Read / output | `GET /api/v14/runs/{run_id}/publish` 与 `/publish/operations/{operation_id}` → `{release_id,status,operations:[{operation_id,kind,target,payload_digest,status,attempts:[{intent,query,effect?,result?,response_digest,observed_at}],observed_fact,provider_ids,preconditions,error?,recovery}],confirmed_facts,unknowns,allowed_actions,evidence_ids}` |
| Operation status / transition | `planned→executing→confirmed|failed|unknown|needs_attention|forward_fix_required`；每attempt顺序必须`intent persisted→query→必要时effect→result→独立readback`；overall保持publishing直至全部required confirmed |
| Provider match rule | query zero且contract声明create/retry safe才执行；唯一exact identity/digest/OID匹配补confirmed；multiple、相同名称不同OID/digest、partial或不可判定均needs_attention；不得用`--skip-existing`推断相同 |
| Persistence / evidence | ledger append-only，保存authorization/candidate/artifact、request非敏感摘要、provider公开response digest、resource ID、query cardinality和actor=Runtime；confirmed项不可回退或重复effect |
| Permission / trust boundary | credential只存opaque `credential_ref`并在adapter内短期注入，不进入argv/prompt/log/evidence；provider response是不可信外部事实，须绑定namespace/target并secret scan；Agent无provider网络权限 |
| Deterministic errors | `PUB_AUTHORIZATION_MISSING`, `PUB_AUTHORIZATION_STALE`, `PUB_PRECONDITION_FAILED`, `PUB_CONTRACT_NOT_CURRENT`, `PUB_OPERATION_CONFLICT`, `PUB_DEPENDENCY_UNCONFIRMED`, `PUB_PROVIDER_ZERO_UNSAFE`, `PUB_PROVIDER_AMBIGUOUS`, `PUB_RESOURCE_IDENTITY_MISMATCH`, `PUB_ACK_UNKNOWN`, `PUB_IMMUTABLE_CONFLICT`, `PUB_CREDENTIAL_UNAVAILABLE`, `PUB_RECONCILE_REQUIRED` |
| Idempotency / concurrency / CAS | operation ID稳定且唯一；同payload重放只query/回读，不重复confirmed effect；异payload复用ID为integrity conflict；并发execute claim CAS恰一winner，其余观察ledger |
| Retry / recovery | timeout/ack loss标unknown并query-before-retry；process restart只扫描planned/executing/unknown/partial；confirmed跳过；zero exact可按contract同ID新execution attempt，conflict/多匹配需要attention；不删除公开资源伪装rollback |
| Related requirements | `FR-2200,2300,2700`；`NFR-0100,0300` |
| Related AC | `AC-FR2200-01, AC-FR2300-01, AC-FR2700-01, AC-NFR0100-01, AC-NFR0300-01` |
| Test Plan layer / runner | `U+C+I+E+A+S`；unit/contract、integration fault injection、`J-PUBLISH-CLOSE`与published artifact smoke，`publish_matrix`；gates=`unit,workflow-contract,integration,e2e-standin,artifact-verify,security,protected-smoke` |

---

## 14. `IF-TRACE-01` — 双向 trace、archive、Red cleanup 与 next-release eligibility

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-TRACE-01`；Primary `ARC-16`；闭合需求到发布的双向可追溯性，先归档再精确清理Red refs，最后发布只读历史与下一release资格 |
| `modules` | `ARC-16` producer；`ARC-01..ARC-15` producers/consumers；Project history UI consumer（跨模块） |
| Caller / authority | Runtime持续追加trace edge并在publish facts confirmed后close；只有`ARC-16`可写archive/cleanup/eligibility；Project member只读；Agent/Human不能删ref、改历史或提前complete |
| Trace input / identity | edge=`{edge_id,source:{kind,id,digest},relation,target:{kind,id,digest},run_id,release_id,actor,evidence_id}`；必须支持`FR/NFR→AC→Test Plan→Issue/task→R/review→formal code/test→CI→artifact→security→decision→publish`双向遍历 |
| Archive input / identity | `{release_id,candidate_id,requirements/design/interfaces/test_plan/prompts/schema/policy digests,trace_root,task_lineages,review/gate/CI/artifact/security/decision/provider evidence_ids,red_refs:[{refname,expected_oid}]}`；`archive_id=sha256(release+candidate+sorted members)` |
| Read / output | `GET /api/v14/runs/{run_id}/trace`、`/archive`、`/history` → `{trace_root,closure:{forward_missing,reverse_orphans,ambiguous},archive:{id,status,manifest_digest,members_readback},cleanup:[{refname,expected_oid,actual_oid?,status}],release_status,issues_project_projection,history_read_only,next_release_eligibility:{enabled,reasons,conflicts},evidence_ids}` |
| Status / transition | publish confirmed→`closing`→trace valid→archive written/readback→每ref CAS cleanup/readback→`complete`；任一失败保持`closing|needs_attention`。history complete后只读，next release仅全部条件真时enabled |
| Cleanup semantics | 只删除archive manifest列出的精确`refname`且actual OID==expected R；已不存在为幂等success；不同OID=`conflict`且绝不删；foreign/unarchived refs必须保持不变 |
| Persistence / evidence | trace edge、archive manifest/blob digest、member readback、ref before/after及Project/Issue projection append-only；完成后更正只能追加erratum或新release/hotfix引用，不能改原status/bytes |
| Permission / trust boundary | archive member/output先digest/media type/secret复核；历史UI安全渲染且summary不覆盖原证据；next release是Runtime计算事实，客户端不能通过隐藏按钮绕过占用冲突 |
| Deterministic errors | `TRACE_EDGE_INVALID`, `TRACE_FORWARD_MISSING`, `TRACE_REVERSE_ORPHAN`, `TRACE_AMBIGUOUS`, `ARCHIVE_PUBLISH_UNCONFIRMED`, `ARCHIVE_MEMBER_MISSING`, `ARCHIVE_DIGEST_MISMATCH`, `ARCHIVE_READBACK_FAILED`, `CLEANUP_REF_CONFLICT`, `CLEANUP_FOREIGN_REF`, `CLEANUP_INCOMPLETE`, `HISTORY_PROJECTION_FAILED`, `NEXT_RELEASE_NOT_ELIGIBLE` |
| Idempotency / concurrency / CAS | 同edge/member identity去重但内容冲突fail；每ref delete用expected OID CAS；archive logical identity immutable；close/current release CAS恰一成功；重复cleanup不重发publish |
| Retry / recovery | crash后先验证archive root再仅重试未确认cleanup；complete前不开放next release；archive失败不删Red；cleanup conflict显示owner/reconcile；发布facts unknown返回`ARC-15`而非重建archive |
| Related requirements | `FR-1100,1300,1800,2400,2500,2600,2700`；`NFR-0300,0400,0600` |
| Related AC | `AC-FR1100-01, AC-FR1300-01, AC-FR1800-01, AC-FR2400-01, AC-FR2500-01, AC-FR2600-01, AC-FR2700-01, AC-NFR0300-01, AC-NFR0400-01, AC-NFR0600-01` |
| Test Plan layer / runner | `U+C+I+E+CE+S`按AC；contract/integration及`J-PUBLISH-CLOSE/J-HOTFIX`公开e2e，Git ref Ground Truth，`archive_matrix`；gates=`unit,workflow-contract,integration,e2e-standin,ci-e2e,security` |

---

## 15. `IF-PROMPT-02` — 003 canonical prompt bundle 与 role capability readback

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-PROMPT-02`；Primary `ARC-01`；公开八角色canonical/deployed prompt bytes、schema/capability parity及dispatch实际绑定identity |
| `modules` | `ARC-01` producer；`ARC-03,ARC-04,ARC-07,ARC-08,ARC-13` consumers（跨模块） |
| Caller / authority | Runtime/program validator发布和激活bundle；Archer/Devon/Shield/Prism/Judge/Librarian/Keeper/Maestro只消费自己的active manifest；Agent不能改prompt current pointer或扩大工具权限 |
| Input schema / identity | `{bundle_version,owning_spec,source_manifest:[{role,path,digest,frontmatter,permissions,tools,write_scopes,input_schema_ref,output_schema_ref}],transformer:{identity,version,digest},deployments:[{role,path,digest,environment}],responsibility_catalog_digest,workflow_definition_digest}`；bundle identity为canonical manifest digest |
| Read / output | `GET /api/v14/runtime/prompt-bundles/{bundle_digest}` 与 `/api/v14/runs/{run_id}/prompt-bindings` → `{bundle_digest,status,sources,deployments,readback:[{role,status,expected,actual}],capability_report:[{role,allowed,denied,violations}],dispatches:[{attempt_id,role,manifest_digest,bundle/source/deployment/schema digests}],evidence_ids}` |
| Role contract | Archer只task graph/advisory；Devon只manifest phase授权unit/implementation；Shield只integration/e2e；Prism多kind review；Judge安全语义review；Librarian仅definition要求的授权文档；Keeper无semantic dispatch；Maestro仅无状态advisory/意图路由 |
| Forbidden capabilities | 全部Agent不得自写program PASS/state、commit/push/branch/ref、GitHub/provider副作用、advance/regress/waive/release/archive或向Human索要技术决定；Keeper不dispatch；Maestro不spawn专业Agent |
| Status / transition | bundle=`candidate|validating|active|retired|drifted|stale`；schema/lint/capability、trusted review和deployment readback全PASS后CAS激活；已启动attempt固定原active digest，不热加载candidate |
| Persistence / evidence | source/deployment/transformer/schema/capability report和每dispatch binding append-only；deployed bytes漂移使新dispatch blocked并使依赖evidence按freshness stale，旧attempt仍保留原identity |
| Permission / trust boundary | prompt文本及Agent output不可信且不得嵌credential；tool/write scope由Runtime capability enforcement而非文字自律；review candidate须记录trusted execution bundle与被审candidate bundle，禁止candidate自证 |
| Deterministic errors | `PROMPT_BUNDLE_MISSING`, `PROMPT_SOURCE_SCOPE_DENIED`, `PROMPT_SCHEMA_INVALID`, `PROMPT_DEPLOYMENT_MISSING`, `PROMPT_DEPLOYMENT_DRIFT`, `PROMPT_CAPABILITY_VIOLATION`, `PROMPT_ROLE_UNSUPPORTED`, `PROMPT_BUNDLE_UNTRUSTED`, `PROMPT_BINDING_STALE`, `PROMPT_SECRET_DETECTED` |
| Idempotency / concurrency / CAS | 相同canonical bytes得到同bundle digest；内容变化新digest；active pointer按expected bundle CAS，竞争恰一winner；同attempt dispatch重放必须返回原binding，不换bundle |
| Retry / recovery | deployment/readback失败修复后以新validation attempt复核；drift不静默采纳；Agent crash可在同manifest/bundle开新session attempt；capability violation终止session并保留脱敏evidence |
| Related requirements | `FR-1900,2800,2900,3000`；`NFR-0200,0600` |
| Related AC | `AC-FR1900-01, AC-FR2800-01, AC-FR2900-01, AC-FR3000-01, AC-NFR0200-01, AC-NFR0600-01` |
| Test Plan layer / runner | `C+I+E+S`；contract semantic lint、capability harness、integration dispatch及legacy e2e，`review_agent_matrix/legacy_matrix`；gates=`workflow-contract,integration,e2e-standin,security` |

---

## 16. `IF-MIG-01` — Legacy run/stage/evidence/prompt migration 与只读 export

| 字段 | 公开合同 |
|---|---|
| Stable identity / owner / purpose | `IF-MIG-01`；Primary `ARC-01`，archive consumer `ARC-16`；把legacy事实显式标为read-only或迁移到单一canonical authority，绝不伪造缺失Red/PASS |
| `modules` | `ARC-01` producer；`ARC-02,ARC-16` consumers（跨模块） |
| Caller / authority | Runtime startup/migration operator可发起；authenticated member只读export/diagnostic；旧Maestro/Agent/compat UI不能写canonical current或触发外部副作用 |
| Input schema / identity | `{source:{store_id,schema_version,revision,digest,run_ids,stage_ids,evidence_refs,prompt_schema_refs,operation_refs},target_schema:{version,digest},mode:"migrate|read_only",expected_source_revision,idempotency_key}`；key=`source store identity+revision+target schema` |
| Read / output | `GET /api/v14/migrations/{migration_id}` 与 `/api/v14/runs/{run_id}/legacy-export` → `{migration_id,source,target,status,identity_map:[{source,target?}],facts:[{kind,source_status,canonical_status,diagnostic}],backup_digest,target_run_ids,current_authority,read_only_export,evidence_id}` |
| Canonical mapping | 可独立验证且source revision未变→migrated；缺program PASS→`UNKNOWN/legacy_unverified`；缺private R/B-R-G→`lineage_unavailable`；旧Agent/Maestro声明→untrusted note；旧prompt/schema保留digest只读；provider identity不足→needs_attention且禁止create retry |
| Status / transition | `planned→claimed→backed_up→migrating→validated→migrated|read_only|unsupported|failed|conflict`；全部integrity/current-pointer检查成功才切换canonical pointer；较新schema由旧binary只读拒绝，不自动downgrade |
| Persistence / evidence | migration前只读backup+SHA-256、source→target map、diagnostics、integrity/foreign-key/current-pointer结果和attempts append-only；失败rollback且保留source；新run只写canonical store |
| Permission / trust boundary | legacy bytes/notes不可信，不能执行旧prompt或沿用credential；migration不import未验证PASS；compat adapter只能翻译公开command/read `IF-WFR-01`，不能写旧stage/store |
| Deterministic errors | `MIG_SOURCE_NOT_FOUND`, `MIG_SOURCE_REVISION_CONFLICT`, `MIG_SOURCE_DIGEST_MISMATCH`, `MIG_SCHEMA_UNSUPPORTED`, `MIG_TARGET_OLDER`, `MIG_IDENTITY_AMBIGUOUS`, `MIG_INTEGRITY_FAILED`, `MIG_CURRENT_AUTHORITY_CONFLICT`, `MIG_OPERATION_IDENTITY_MISSING`, `MIG_DUAL_WRITE_DETECTED`, `MIG_INTERRUPTED` |
| Idempotency / concurrency / CAS | migration key唯一；同source/target重放回同mapping；source bytes变化冲突；project migration lease和expected source revision CAS恰一winner；禁止legacy/canonical dual write及双commit authority |
| Retry / recovery | kill后先query现有mapping/backup/current pointer；精确相同继续未完成step，不重复外部operation；无法唯一映射保持read_only；失败保持canonical dispatch disabled或原旧只读，不在部分schema运行 |
| Related requirements / AC | `NFR-0600`；`AC-NFR0600-01` |
| Test Plan layer / runner | `U+C+I+E`；unit/contract、`tests/e2e/run-project-venv integration`及legacy公开e2e，`legacy_matrix`；gates=`unit,workflow-contract,integration,e2e-standin` |

---

## 17. Inherited 002 machine-contract interfaces（引用，不重定义）

### 17.1. 统一版本边界

| 项 | 合同 |
|---|---|
| Source artifact | Spec `v0.14-002-workflow-reflow-design` 的 `.louke/project/specs/v0.14-002-workflow-reflow-design/interfaces.md`；接口 identity 必须精确解析到该Spec current design manifest绑定的artifact revision与SHA-256，而非按路径读取任意latest bytes |
| Machine schema boundary | `IF-TST-01`映射`louke.machine-contract.integration-test`与`louke.machine-contract.e2e-test`；`IF-PC-01/CI-01/REL-01/BLD-01/PUB-01`依次映射`louke.machine-contract.pre-commit|github-actions-ci|release-version|build-artifact|publish-recovery`；version均为`1.0.0`。schema digest从002 registry精确resolve，003不得内嵌、补字段或fallback到candidate/unknown版本 |
| Prompt boundary | `IF-PRM-01`精确消费002 current prompt bundle manifest/deployment contract及其bundle/source/deployment/schema digests；003的`IF-PROMPT-02`只做八角色运行结果/parity readback，不复制或替代`IF-PRM-01` |
| Instance binding | 每次003 run在implementation baseline解析并持久化每个inherited interface的`{source_spec,interface_id,artifact_revision,artifact_digest,schema_ref,instance_revision,instance_digest}`；任一缺失、invalid、unsupported或漂移均使consumer blocked/stale |
| Authority | 这些接口定义“宿主项目应运行什么”；003 `ARC-*`只按精确contract执行并发布Runtime evidence。Runtime不得从Louke仓库语言/目录猜其它宿主命令，Shield不得临时设计runner，Devon不得改选adapter |

### 17.2. 七个继承接口的消费索引

| Inherited IF | 002 精确引用 | `modules`（003） | 本 Spec 消费方式；不复制的边界 | Related FR / AC | Test Plan layer / runner |
|---|---|---|---|---|---|
| `IF-PC-01` | 002 Interfaces §3 `IF-PC-01 — Pre-commit install/readback contract`；active `louke.machine-contract.pre-commit@1.0.0` | `ARC-02,ARC-05,ARC-10`（跨模块） | `IF-IMPL-01`据其install/readback建立baseline；`IF-RGR-01/QUAL-01`据其正式commit/all-files gate执行；不重述hooks、命令或版本 | `FR-0100,0900`；`AC-FR0100-01, AC-FR0900-01` | `C+I`；contract + integration，gates=`workflow-contract,integration,quality` |
| `IF-TST-01` | 002 Interfaces §3 `IF-TST-01 — Integration/E2E contract`；active integration/e2e schemas均`1.0.0` | `ARC-08,ARC-05,ARC-10,ARC-11`（跨模块） | 生成Shield scopes、suite inventory、runner/cwd/env/service/teardown并供local/GitHub执行；不重述路径、命令或fixture | `FR-1200`；`AC-FR1200-01` | `C+I`，实际journey另`E/CE`；project-venv runners |
| `IF-CI-01` | 002 Interfaces §3 `IF-CI-01 — CI contract generation、readback 与 required check`；active `louke.machine-contract.github-actions-ci@1.0.0` | `ARC-11,ARC-09,ARC-10`（跨模块） | render/readback `.github/workflows/louke-ci.yml`，供`IF-CI-02`触发、suite/check/rules事实验证；不复制workflow payload | `FR-1700`；`AC-FR1700-01` | `C+I+CE+S`；`workflow-contract,integration,ci-e2e,security` |
| `IF-REL-01` | 002 Interfaces §4 `IF-REL-01 — Release Version Adapter`；active `louke.machine-contract.release-version@1.0.0` | `ARC-12,ARC-14,ARC-15`（跨模块） | `IF-BLD-02`取得canonical映射、版本源与project-local adapter；`IF-REL-02/PUB-02`只消费其identity；不重定义adapter命令 | `FR-1600`；`AC-FR1600-01` | `C+I+A`；`workflow-contract,integration,artifact-verify` |
| `IF-BLD-01` | 002 Interfaces §4 `IF-BLD-01 — Build/Artifact verification`；active `louke.machine-contract.build-artifact@1.0.0` | `ARC-12,ARC-10,ARC-15`（跨模块） | `IF-BLD-02`取得build、完整artifact清单、extract/install/run outlets；quality/publish只消费verified结果；不猜宿主artifact | `FR-1600`；`AC-FR1600-01` | `C+I+A`；真实`build-artifacts,artifact-verify` |
| `IF-PUB-01` | 002 Interfaces §4 `IF-PUB-01 — Publish operation ledger 与恢复`；active `louke.machine-contract.publish-recovery@1.0.0` | `ARC-15,ARC-12,ARC-14,ARC-16`（跨模块） | `IF-PUB-02`取得operation DAG、query/create/readback、conflict及forward-fix语义；不重述provider命令或credential | `FR-2200`；`AC-FR2200-01` | `C+I+E+S`；fault/restart journey及`protected-smoke` |
| `IF-PRM-01` | 002 Interfaces §5 `IF-PRM-01 — Prompt bundle manifest、deployment readback 与激活`；精确current bundle/schema digests | `ARC-01,ARC-03,ARC-04,ARC-07,ARC-08,ARC-13`（跨模块） | `IF-PROMPT-02`将003八角色source/deployment/capability与该contract比对，每次dispatch绑定精确digest；不复制manifest/deploy schema | `FR-2800,2900`；`AC-FR2800-01, AC-FR2900-01` | `C+I+S`；semantic lint、capability与dispatch integration |

七项都要求Shield integration覆盖其003 consumer wiring；002自身的schema/contract tests仍由current 002 validator负责。003不得因002 instance缺失而另造兼容payload，必须返回对应consumer的`*_CONTRACT_NOT_CURRENT|*_HOST_UNSUPPORTED`确定性错误。

---

## 18. `23/23 IF → ARC → Test Plan → FR/AC` 交叉索引

### 18.1. 003 Runtime observable interfaces（16/16）

`Test Plan`列的层级与gate精确继承`test-plan.md` §2.3、§4和§7；`U/C/I/E/CE/A/S`不得互相降级替代。

| IF | Primary / supporting ARC | Test Plan required layer / gate | Related FR/NFR → AC |
|---|---|---|---|
| `IF-IMPL-01` | `ARC-02 / ARC-01,03,04` | `U+C+I`；`unit,workflow-contract,integration`；兼容矩阵另`E+CE+A` | `FR-0100→AC-FR0100-01`; `NFR-0500→AC-NFR0500-01` |
| `IF-WFR-01` | `ARC-01 / ARC-02..16` | AC各自`U/C/I/E/CE/S`；`unit,workflow-contract,integration,e2e-standin,ci-e2e,security` | `FR-0100→AC-FR0100-01`; `FR-0300→AC-FR0300-01`; `FR-0400→AC-FR0400-01`; `FR-1300→AC-FR1300-01`; `FR-1400→AC-FR1400-01`; `FR-2000→AC-FR2000-01`; `FR-2100→AC-FR2100-01`; `FR-2300→AC-FR2300-01`; `FR-2400→AC-FR2400-01`; `FR-2500→AC-FR2500-01`; `FR-2600→AC-FR2600-01`; `FR-2700→AC-FR2700-01`; `FR-3000→AC-FR3000-01`; `NFR-0400→AC-NFR0400-01`; `NFR-0600→AC-NFR0600-01` |
| `IF-TASK-01` | `ARC-03,04 / ARC-01,05,08` | `U+C+I+S`；`unit,workflow-contract,integration,security` | `FR-0200→AC-FR0200-01`; `FR-0300→AC-FR0300-01`; `FR-0400→AC-FR0400-01`; `FR-0500→AC-FR0500-01`; `FR-2800→AC-FR2800-01`; `NFR-0100→AC-NFR0100-01`; `NFR-0200→AC-NFR0200-01` |
| `IF-RGR-01` | `ARC-05,06 / ARC-07,09,10,16` | AC各自`U/C/I/E/CE/S`；真实Git integration为必需 | `FR-0500→AC-FR0500-01`; `FR-0600→AC-FR0600-01`; `FR-0700→AC-FR0700-01`; `FR-0800→AC-FR0800-01`; `FR-0900→AC-FR0900-01`; `FR-1000→AC-FR1000-01`; `FR-1100→AC-FR1100-01`; `FR-1400→AC-FR1400-01`; `FR-1500→AC-FR1500-01`; `FR-2400→AC-FR2400-01`; `FR-2500→AC-FR2500-01`; `FR-2600→AC-FR2600-01`; `FR-2700→AC-FR2700-01`; `NFR-0100→AC-NFR0100-01`; `NFR-0300→AC-NFR0300-01` |
| `IF-REV-02` | `ARC-07 / ARC-03,05,06,08,09,13` | `C+I`，规则/安全另`U/S`；`workflow-contract,integration,unit,security` | `FR-0300→AC-FR0300-01`; `FR-0700→AC-FR0700-01`; `FR-1000→AC-FR1000-01`; `FR-1100→AC-FR1100-01`; `FR-1200→AC-FR1200-01`; `FR-1800→AC-FR1800-01`; `FR-2900→AC-FR2900-01` |
| `IF-TEST-02` | `ARC-08 / ARC-01,07,09,10,11` | `C+I+E+CE+A`按AC；`workflow-contract,integration,e2e-standin,ci-e2e,artifact-verify` | `FR-1200→AC-FR1200-01`; `FR-1300→AC-FR1300-01`; `FR-1500→AC-FR1500-01`; `FR-1700→AC-FR1700-01`; `NFR-0500→AC-NFR0500-01` |
| `IF-CAND-01` | `ARC-09 / ARC-01,10,11,12,13,14` | `U+C+I+E+S`；`unit,workflow-contract,integration,e2e-standin,security` | `FR-1400→AC-FR1400-01`; `FR-1800→AC-FR1800-01`; `FR-1900→AC-FR1900-01`; `FR-2000→AC-FR2000-01`; `FR-2100→AC-FR2100-01`; `NFR-0100→AC-NFR0100-01` |
| `IF-QUAL-01` | `ARC-10 / ARC-05,08,09,12` | `U+C+I+E+S`；全本地required quality jobs | `FR-0800→AC-FR0800-01`; `FR-1500→AC-FR1500-01`; `FR-3000→AC-FR3000-01` |
| `IF-CI-02` | `ARC-11 / ARC-01,08,09,10,13,14` | `C+I+CE+S`，兼容另`E+A`；`workflow-contract,integration,ci-e2e,security` | `FR-1700→AC-FR1700-01`; `FR-2500→AC-FR2500-01`; `NFR-0200→AC-NFR0200-01`; `NFR-0300→AC-NFR0300-01`; `NFR-0500→AC-NFR0500-01` |
| `IF-BLD-02` | `ARC-12 / ARC-09,10,13,14,15` | `C+I+E+A`，兼容另`CE`；`build-artifacts,artifact-verify` | `FR-1600→AC-FR1600-01`; `FR-2300→AC-FR2300-01`; `NFR-0500→AC-NFR0500-01` |
| `IF-SEC-01` | `ARC-13 / ARC-01,07,09,14,16` | `C+I+E+CE+S`；`workflow-contract,integration,e2e-standin,ci-e2e,security` | `FR-1900→AC-FR1900-01`; `FR-2000→AC-FR2000-01`; `FR-2900→AC-FR2900-01`; `NFR-0200→AC-NFR0200-01` |
| `IF-REL-02` | `ARC-14 / ARC-01,09,13,15` | `C+I+E+S`，operation规则另`U`；`workflow-contract,integration,e2e-standin,security,unit` | `FR-2100→AC-FR2100-01`; `FR-2200→AC-FR2200-01` |
| `IF-PUB-02` | `ARC-15 / ARC-01,12,14,16` | `U+C+I+E+A+S`；`unit,workflow-contract,integration,e2e-standin,artifact-verify,security,protected-smoke` | `FR-2200→AC-FR2200-01`; `FR-2300→AC-FR2300-01`; `FR-2700→AC-FR2700-01`; `NFR-0100→AC-NFR0100-01`; `NFR-0300→AC-NFR0300-01` |
| `IF-TRACE-01` | `ARC-16 / ARC-01..15` | AC各自`U/C/I/E/CE/S`；`workflow-contract,integration,e2e-standin,ci-e2e,security` | `FR-1100→AC-FR1100-01`; `FR-1300→AC-FR1300-01`; `FR-1800→AC-FR1800-01`; `FR-2400→AC-FR2400-01`; `FR-2500→AC-FR2500-01`; `FR-2600→AC-FR2600-01`; `FR-2700→AC-FR2700-01`; `NFR-0300→AC-NFR0300-01`; `NFR-0400→AC-NFR0400-01`; `NFR-0600→AC-NFR0600-01` |
| `IF-PROMPT-02` | `ARC-01 / ARC-03,04,07,08,13` | `C+I+E+S`；`workflow-contract,integration,e2e-standin,security` | `FR-1900→AC-FR1900-01`; `FR-2800→AC-FR2800-01`; `FR-2900→AC-FR2900-01`; `FR-3000→AC-FR3000-01`; `NFR-0200→AC-NFR0200-01`; `NFR-0600→AC-NFR0600-01` |
| `IF-MIG-01` | `ARC-01 / ARC-02,16` | `U+C+I+E`；`unit,workflow-contract,integration,e2e-standin` | `NFR-0600→AC-NFR0600-01` |

---

### 18.2. Inherited project-local machine contracts（7/7）

| IF | Primary / supporting ARC | Test Plan required layer / gate | Related FR → AC |
|---|---|---|---|
| `IF-PC-01` | `ARC-02 / ARC-05,10` | `C+I`；`workflow-contract,integration,quality` | `FR-0100→AC-FR0100-01`; `FR-0900→AC-FR0900-01` |
| `IF-TST-01` | `ARC-08 / ARC-05,10,11` | `C+I`，journey另`E/CE`；`workflow-contract,integration,e2e-standin,ci-e2e` | `FR-1200→AC-FR1200-01` |
| `IF-CI-01` | `ARC-11 / ARC-09,10` | `C+I+CE+S`；`workflow-contract,integration,ci-e2e,security` | `FR-1700→AC-FR1700-01` |
| `IF-REL-01` | `ARC-12 / ARC-14,15` | `C+I+A`；`workflow-contract,integration,artifact-verify` | `FR-1600→AC-FR1600-01` |
| `IF-BLD-01` | `ARC-12 / ARC-10,15` | `C+I+A`；`workflow-contract,integration,build-artifacts,artifact-verify` | `FR-1600→AC-FR1600-01` |
| `IF-PUB-01` | `ARC-15 / ARC-12,14,16` | `C+I+E+S`；`workflow-contract,integration,e2e-standin,security,protected-smoke` | `FR-2200→AC-FR2200-01` |
| `IF-PRM-01` | `ARC-01 / ARC-03,04,07,08,13` | `C+I+S`；`workflow-contract,integration,security` | `FR-2800→AC-FR2800-01`; `FR-2900→AC-FR2900-01` |

### 18.3. Closure accounting 与实现/验证就绪

| Closure | Count | Result |
|---|---:|---|
| 003 observable interfaces | `16/16` | 每项有独立section、stable identity、owner、modules、input/output/status、persistence、trust、errors、CAS、recovery和Test Plan runner |
| inherited 002 contracts | `7/7` | 每项有精确002引用、`1.0.0`/bundle版本边界、003 consumer与integration责任；未重定义payload |
| Architecture components | `16/16 ARC` | `ARC-01..ARC-16` 均由至少一个公开接口承担producer/consumer责任，无第二current authority |
| Requirements | `30/30 FR + 6/6 NFR` | 本节索引覆盖`FR-0100..FR-3000`和`NFR-0100..NFR-0600` |
| Acceptance | `36/36 AC` | 每个`AC-FRXXXX-01`/`AC-NFRXXXX-01`均映射到至少一个本文IF及Test Plan required layer/gate |
| Cross-module integration | `23/23 IF` | 所有IF均跨至少两个ARC；Shield integration不可由unit/contract替代 |
| Human interaction | `IF-WFR-01,IF-REL-02,IF-PUB-02,IF-TRACE-01` | Project current入口、动作可用性、running/success/fail/dirty/stale/conflict/unknown/reconnect、只读history及next-release恢复全部有E2E出口 |

**Devon readiness**：可以按16个003 schema/command/error合同实现Runtime公开出口、受控Git/provider adapter与unit/contract，并按7个inherited contract接线；无需自行选择owner、版本adapter、artifact、runner、CI required check或恢复语义。

**Shield readiness**：可以按23个跨模块接口、Test Plan fixtures与已锁定project-venv runners编写integration/e2e/CI E2E/artifact/security场景；所有断言均落在本文公开read model、Git/provider readback、artifact outlet或Human surface，不需读取私有store。

**Residual risks**：真实GitHub rules能力/provider最终一致性、不可变publish partial success、SQLite本地磁盘完整性、stand-in与真实provider漂移及inherited contract缺失仍可能产生`UNKNOWN|needs_attention|blocked`；这些都有确定owner和fail-closed恢复合同，不是待Devon/Shield/Human补选的产品行为。
