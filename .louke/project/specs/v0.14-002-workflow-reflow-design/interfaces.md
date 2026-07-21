# 工作流重构：技术设计与规范性 Agent 合同 — Public Interfaces

- **Spec ID**：`v0.14-002-workflow-reflow-design`
- **需求基线**：Story `sha256:06d5573efbf59dd18b480d6539ad16df237fd4460f9f95d1589110cbfeec1993`；Spec `sha256:315c8d20254fceb63971b029d69c81889972eedb581621981a012f17edc8867f`；Acceptance `sha256:39b09cbf36cc0f4f0dcc8f0e8a79949049a2b6baddcecbcf2183ad407e493559`
- **约定**：本文只定义外部可观察合同。`modules` 来自 `architecture.md` §2；两个及以上模块即跨模块，必须有 integration 覆盖。JSON schema 默认 `additionalProperties: false`，digest 均为 `sha256:<64 lowercase hex>`。

## 1. 通用身份、状态与错误

### IF-DES-01 — Design revision manifest 与公开 read model

| 字段 | 合同 |
|---|---|
| `modules` | `DESIGN, FACTS, STORE, WEB, SESSION`（跨模块） |
| identity | `{run_id, release_identity, design_revision_id, attempt_id, actor_id, requirements:{story,spec,acceptance}, base_commit, project_facts_digest, task_manifest_digest}`；所有 digest/commit 必须可回读，revision 不可复用 |
| create precondition | requirements approval current、workspace/base commit 可证明、facts current；任一缺失或 stale 时不生成 Archer task |
| read | `GET /api/v14/runs/{run_id}/design` → 当前 identity、`status`, artifacts/contracts/prompts/review/program_checks、`allowed_actions`, `continue_url` |
| status | `authoring | validating | waiting_prism | revise | ready_for_implementation | blocked | needs_attention`；状态是 Runtime 事实，不接受 Agent 文本直接写入 |
| permissions | authenticated Human 可读；只有 Runtime 可创建 revision/dispatch/推进；Archer 仅写 manifest allowlist；Prism 只返回 review result |
| error/recovery | `DESIGN_INPUT_MISSING|DESIGN_INPUT_STALE|BASE_COMMIT_CONFLICT|WRITE_SCOPE_DENIED`；返回 current identity 与 remediation。修复后以新 attempt/revision 重试，不改写历史 |
| architecture | `ARC-DESIGN`, `ARC-FACTS`, `ARC-STORE`, `ARC-SECURITY` |

### IF-DES-02 — 统一 validation result

| 字段 | 合同 |
|---|---|
| `modules` | `VALIDATOR, REGISTRY, CONTRACTS, PROMPTS, CI, STORE, WEB`（跨模块） |
| invocation | project-local program entry（本 Spec 由 Devon 实现）：`python -m louke._tools.design_contract validate --manifest PATH --format json --output PATH` |
| output | `{status:"pass|fail", revision_id, checks:[{check_id,status:"pass|fail",artifact_path?,field?,expected?,actual?,fr_ids:[],ac_ids:[],interface_ids:[],architecture_anchors:[],contract_refs:[],prompt_identity?,retryable,remediation}], evidence_digest}` |
| stable check IDs | 至少包含 `DESIGN.TRACE.CLOSURE`, `DESIGN.INTERFACE.RESOLUTION`, `DESIGN.ARCH.CARRIER`, `DESIGN.CONTRACT.PARITY`, `DESIGN.SCHEMA.ACTIVE`, `DESIGN.PROMPT.PARITY`, `DESIGN.DISCUSSION.OPEN`, `DESIGN.DIFF.SCOPE`, `DESIGN.SECRET` |
| secrecy | `actual`, message 与 evidence 不得回显检测到的 secret；只给路径、字段和 redacted fingerprint |
| exit | 全部 pass 为 0；任一 fail、缺失、unknown、输出无法持久化为非 0。不得以 warning 代替 required failure |
| recovery | `retryable=true` 可在修复指定 artifact 后生成新 evidence；identity/digest 变化使旧 evidence stale |
| architecture | `ARC-VALIDATE`, `ARC-SECURITY`, `ARC-STORE` |

### IF-CON-01 — Machine contract instance envelope

| 字段 | 合同 |
|---|---|
| `modules` | `REGISTRY, CONTRACTS, VALIDATOR, STORE`（跨模块） |
| candidate / canonical path | 本revision可评审candidate：`.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/contracts/<kind>.candidate.json`；Runtime激活后的project-local canonical安装目标：`.louke/project/contracts/<spec-id>/<kind>.json`。candidate不得冒充current；每个required kind激活后恰一current instance，UTF-8 canonical JSON |
| canonical envelope | `{kind,identity,revision,schema_ref:{identity,version,digest},manifest_ref:{identity,revision},scope:{workspace_id,spec_id,base_commit,project_facts_digest,project_facts_artifact:{kind,path,identity,revision},release_identity},generated_by:{owner,role,task_manifest_digest,task_manifest_artifact:{kind,path,identity,revision}},compatible_runtime,artifact_refs:[],payload:{commands:[],...,failure_policy}}`；`commands`和`failure_policy`只在`payload`出现 |
| digest resolution | instance不含自身digest或`digest_scope`。resolver以`manifest_ref.identity + manifest_ref.revision + kind`查找外部design artifact manifest中唯一instance entry，校验entry的artifact kind/path/bytes digest后返回`{contract_path,contract_digest}`；digest覆盖完整instance bytes，无自引用循环 |
| provenance | `project_facts_digest`必须解析到`kind=host-project-facts-snapshot`的声明path/bytes；`task_manifest_digest`必须解析到`kind=archer-author-task-manifest`的声明path/bytes。只有sha格式、错kind、错path、`project.toml`或review bytes均为`CONTRACT_PROVENANCE_MISMATCH` |
| required kinds | `integration-test`, `e2e-test`, `pre-commit`, `github-actions-ci`, `release-version`, `build-artifact`, `publish-recovery` |
| status | instance 自身不声明 PASS；本批次7份均为design candidate。只有active registry/validator evidence可给`valid|invalid|stale`；当前registry未激活，必须`SCHEMA_NOT_ACTIVE`且baseline fail closed |
| permissions | Archer 仅能在 manifest 授权路径生成 instance；schema 只读且不能嵌入/覆盖 |
| error/recovery | kind 缺失、manifest ref不唯一、字段/引用/digest scope/provenance错误、unknown/candidate schema 为 `CONTRACT_*` fail；旧 active schema 通过显式 reader migration，不能猜读 |
| architecture | `ARC-REGISTRY`, `ARC-CONTRACTS`, `ARC-VALIDATE` |

## 2. Machine Contract Registry

### IF-REG-01 — Registry discovery、resolve 与 validation API

| 字段 | 合同 |
|---|---|
| `modules` | `REGISTRY, VALIDATOR, CONTRACTS, PROMPTS`（跨模块） |
| registry source | 设计candidate入口`design-artifacts/registry/registry.candidate.json`及其7个machine schema + 4个Agent I/O schema files，owner=`Runtime/program`, activation_state=`candidate`；Devon实现后active source才是package-owned `louke/schemas/registry.json`与`louke/schemas/{machine-contracts,agent-io}/<identity>/<version>.json`，宿主项目只读 |
| public calls | `discover(kind: str | None) -> RegistryView`; `resolve(identity: str, version: str, digest: str) -> SchemaDocument`; `validate(schema_ref: SchemaRef, instance_bytes: bytes) -> ValidationResult`；同能力CLI为`python -m louke._tools.contract_registry {discover|resolve|validate} --format json ...` |
| discover | 返回 `{registry_version,registry_digest,schemas:[{identity,kind,version,digest,status:"active|candidate|retired",compatibility,migration?}]}` |
| candidate identities | machine contracts固定为`louke.machine-contract.{integration-test|e2e-test|pre-commit|github-actions-ci|release-version|build-artifact|publish-recovery}` version `1.0.0`；Agent I/O固定为`louke.agent-io.archer-design-task-input`、`louke.agent-io.archer-design-result`、`louke.agent-io.prism-design-review-task-input`、`louke.agent-io.prism-design-review` version `1.0.0`。exact candidate digest见registry；所有active digest由canonical schema bytes计算并原子登记，不能手填或使用`current`/`digest_source` |
| Agent task validation | Archer/Prism task的`dispatch.authority`只能是`Runtime/program`；`execution_transport`仅含不透明`provider_metadata`/`session_metadata`且不参与current state或判定。Archer input必须含所有input identities/digests、allowed write set、forbidden effects、M-DESIGN/spec/revision、exact output schema和freshness；Prism input还必须绑定trusted reviewer execution与reviewed candidate manifest/bundle。`output_contract.delivery`只能返回Runtime/program作validation/persistence。缺失/extra/type/enum/digest/freshness错误均拒绝dispatch/result |
| activation | prerequisites为registry/validator实现、11/11 schema meta-validation、2 input + 2 output闭合、7/7 instance program validation、34/34 required test evidence、trusted active Prism review、wheel+sdist clean-install readback和Runtime单一pointer CAS。任一未完成、partial或unknown时discover可展示candidate但resolve拒绝，不能产生active子集 |
| resolve | exact `{identity,version,digest}`；只返回 bytes digest 匹配的 active schema。candidate/unknown/digest mismatch 不回退 |
| validate | 输入 schema ref + document bytes；输出 `{valid,schema_ref,document_digest,errors:[{json_pointer,keyword,expected,actual_type}]}`；contract另执行manifest/provenance resolver并返回`contract_digest`。不解析 prompt 示例作为 schema |
| permissions | Runtime/program 可发布 registry；Agent、prompt、宿主 release 不可写 registry |
| error/recovery | `SCHEMA_UNKNOWN|SCHEMA_NOT_ACTIVE|SCHEMA_DIGEST_MISMATCH|SCHEMA_VALIDATION_FAILED|SCHEMA_MIGRATION_REQUIRED`；migration 只从声明 source version 到 target version且生成新 digest |
| architecture | `ARC-REGISTRY`, `ARC-SECURITY` |

## 3. Test、Pre-commit 与 CI contracts

### IF-TST-01 — Integration/E2E contract

| 字段 | 合同 |
|---|---|
| `modules` | `CONTRACTS, VALIDATOR, CI`（跨模块） |
| kinds | IF-CON-01 的 `integration-test` 与 `e2e-test` |
| integration payload | `{commands,paths,discovery:{framework,expected_manifest,preserve_historical,zero_collection},runner,setup,run,services,fixtures,environment:{production_secrets,network_publish,external_services,core_modules_mocked},timeout_seconds,suites:[{id,required,paths,ac_ids,interface_ids,architecture_anchors}],skip_policy,quarantine_policy,evidence:{schema,formats,required_ac_layer_reconciliation},teardown,failure_policy}` |
| e2e payload | `{commands,paths,discovery,runner,setup,run,services,ready,fixtures,environment,timeout_seconds,suites,public_surfaces,journeys:[{id,entry,actions,visible_result,recovery,ac_ids}],isolation,artifacts,evidence,teardown,failure_policy}`；required journey 不得仅调用私有模块 |
| nested policy | 上述影响discovery/environment/lifecycle/evidence的每个object及service/suite/journey item均声明required/type/enum和`additionalProperties:false`；空object、拼写字段或unknown状态必须schema fail |
| public commands | integration=`tests/e2e/run-project-venv integration`；e2e=`tests/e2e/run-project-venv e2e --profile all --runtime both`。Devon扩展现有`run_e2e.py`：integration paths精确为历史`tests/integration/install_experience`+`tests/integration/v014_design_contracts`；e2e profiles精确为`install|chromium|design-contracts|all`，`all`展开三者，design-contracts path=`tests/e2e/v014_design_contracts`且按local/global运行 |
| lifecycle | `design-contracts` runner以installed wheel启动`lk web --host 127.0.0.1 --port <allocated>`；`GET /health`每250ms检查HTTP 200和expected version，60秒超时；finally TERM进程组、等待10秒、必要时KILL，清理temp HOME/XDG/workspace/ports。integration不启动Workbench |
| evidence | 每次命令输出JUnit和`v014-runner-evidence.json`：`schema_version,release_identity,spec_id,base_commit,runner_digest,command,profile,runtime,expected_node_ids,collected_node_ids,ac_layers,suite_results,service_lifecycle,started_at,finished_at,exit_reason,evidence_digest`；AC/layer与design artifact manifest双向对账 |
| command status | 每个命令记录cwd/env allowlist；仅expected required paths/nodes/AC-layers全部collected并通过、lifecycle/teardown成功时0。required path缺失、零收集、漏跑、unknown profile/runtime、nonzero/timeout/cancel/required skip/not-run/unknown均非0。当前runner未实现此语义，故candidate未安装前即使旧命令0也不是v014 PASS |
| permissions | PR fixture 无生产 secret；teardown 无论成功失败执行；测试只能写临时 workspace |
| recovery | service 未 ready 在 timeout 后 fail；失败 evidence 保留，临时外部资源按 ledger 清理 |
| architecture | `ARC-CONTRACTS`, `ARC-CI`, `ARC-SECURITY` |

### IF-PC-01 — Pre-commit install/readback contract

| 字段 | 合同 |
|---|---|
| `modules` | `PRECOMMIT, CONTRACTS, VALIDATOR, STORE`（跨模块） |
| contract | `{managed_config_path,tool_version,install_command,stages,hooks:[{id,entry,version,timeout_seconds,may_modify}],existing_hook_snapshot,merge_policy,authoritative_full_gate}` |
| Louke host instance | 保留 root `.pre-commit-config.yaml` 现有 local Keeper hooks及第三方 hooks；`pre-commit==4.6.0`；快速 format/lint/static/secret/trace，超时目标 120 秒；`authoritative_full_gate=false` |
| install | 仅 Runtime 在 implementation/reconcile 阶段执行 contract 的 `install_command`；Archer/Devon 不安装。返回 `{operation_id,status,config_digest,hook_stage_digests}` |
| readback | 读取 managed config + installed hook stages，比较 contract revision/digest、所有 preserved hook identity 与 entry；输出 `in_sync|drifted|missing|conflict` |
| failure | hook nonzero 阻止正式 commit；自动修改返回 nonzero并列 changed paths，用户复核后重跑；Red 证明和全量测试不由 hook 声称完成 |
| recovery | drift 先保留 diff；只有 owner marker/current baseline匹配才幂等更新，外部修改进入 conflict，不静默覆盖 |
| architecture | `ARC-PRECOMMIT`, `ARC-SECURITY`, `ARC-STORE` |

### IF-CI-01 — CI contract generation、readback 与 required check

| 字段 | 合同 |
|---|---|
| `modules` | `CI, CONTRACTS, VALIDATOR, STORE, PUBLISH`（跨模块） |
| contract payload | `{commands,provider:"github-actions",managed_path:".github/workflows/louke-ci.yml",owner_marker,contract_revision,target_branches,triggers,runner_matrix,setup,jobs:[{id,required,command_ref,needs,timeout_minutes,permissions,evidence}],dag:{edges:[{from,to}],aggregate},permissions:{default,pull_request_write,fork_pr_secrets},secrets,services,caches,evidence,timeouts,failure_policy,required_check,rules_readback}`；不存在顶层commands/failure policy或instance内`contract_digest` |
| resolver output | IF-CON-01 resolver从外部manifest返回`{contract_path,contract_digest}`；render/readback必须使用该digest。`contract_digest`不是instance自引用字段 |
| generate | project-local program entry（Devon 实现）`python -m louke._tools.ci_contract render --contract PATH --output .github/workflows/louke-ci.yml`；相同输入产生相同 canonical YAML/digest |
| readback | `python -m louke._tools.ci_contract readback --contract PATH --workflow .github/workflows/louke-ci.yml --format json` → `{status:"in_sync|missing|invalid|drifted|conflict",contract_digest,workflow_digest,diff?,checks,commands}`；digest必须等于resolver对manifest entry的结果 |
| coexistence | 只管理 owner marker 所属文件和 Louke-owned ruleset；保留 `.github/workflows/ci.yml`, `release.yml` 与用户 rules/checks；既有 workflow 不得另产同名 required check |
| required check | 唯一 `Louke CI / required`；`if: always()` 聚合同一 commit 全部 required jobs；fail/cancel/timeout/missing/skip/unknown 一律 fail |
| rules readback | `{owner,target,required_check,observed,existing_rules_preserved}`；Runtime 创建/更新并回读，能力不足时显式 branch-protection fallback |
| permissions | 默认 `contents: read`；fork PR 无 secret/写 token；publish/real smoke 使用 protected environment 和最小单独权限 |
| nested policy | jobs item、DAG edge、permissions、secrets、service、cache、timeouts、rules readback都关闭unknown字段并要求执行/权限/timeout/evidence所需字段；`jobs:[{}]`、`dag:{}`、`permissions:{}`确定schema fail |
| recovery | 外部修改显示 diff并建立新设计 revision后才能接受/合并；invalid YAML、command missing、drift 阻止 PASS |
| architecture | `ARC-CI`, `ARC-SECURITY`, `ARC-STORE`, `ARC-PUBLISH` |

## 4. Release、Build/Artifact 与 Publish

### IF-REL-01 — Release Version Adapter

| 字段 | 合同 |
|---|---|
| `modules` | `VERSION, CONTRACTS, BUILD, PUBLISH`（跨模块） |
| registry schema boundary | `louke.machine-contract.release-version@1.0.0`严格要求IF-CON-01 envelope和`payload:{commands,canonical_input,normalization,branch_mapping,tag_mapping,version_source:{path,selector},adapter,read_command,prepare_command,write_policy,compare,evidence,failure_policy}`，所有object均`additionalProperties:false`；schema只约束kind、schema ref、必需mapping、类型与失败形状，不固定release/spec/revision/manifest/runtime、路径、adapter或命令 |
| generic adapter contract | release identity、branch/tag、version source、adapter、commands和compatible runtime全部来自project facts并落在instance；不存在语言默认。同schema异构正例为`design-artifacts/validation/release-version-node-host.valid.candidate.json`（Node/SemVer/package.json），Louke值只在`contracts/release-version.candidate.json` |
| Louke canonical identity | Human external `v0.14.0` → canonical `0.14.0`；branch `releases/0.14.0`；tag `v0.14.0`；预发布不适用于本次 release |
| project candidate/readback | target project identity=`{version:"0.14.0",spec_id:"v0.14-002-workflow-reflow-design",release_branch:"releases/0.14.0"}`，见`design-artifacts/runner/project-runner.candidate.json`。当前`.louke/project/project.toml`仍为0.13.1/001/releases/0.13.1；Devon foundation安装前readback必须`drifted`并阻断baseline，不得把candidate声明当active事实 |
| Louke source/adapter | root `pyproject.toml [project].version`；沿用并扩展project-local `tools/louke_python_release_adapter.py`。读取：`python tools/louke_python_release_adapter.py inspect-source`；准备：`python tools/louke_python_release_adapter.py prepare --tag "$TAG"`；只在隔离 build workspace 写 version source |
| inspect/read | `inspect-source` stdout JSON `{source:absolute_path,selector:"project.version",version}`；非法/缺失 tag、source selector 不存在、非 PEP 440 或 mapping mismatch 为非 0。`inspect-source`子命令由本Spec明确要求Devon补齐，不是既有入口 |
| evidence | `version-scheme-selected`, `version-source-prepared` 分离，包含 canonical identity、source path/digest、adapter digest |
| permission/recovery | PR 默认只校验；release prepare 仅写声明的 source。失败恢复原 build workspace或重建，不修改用户工作区 |
| architecture | `ARC-VERSION`, `ARC-FACTS`, `ARC-SECURITY` |

### IF-BLD-01 — Build/Artifact verification

| 字段 | 合同 |
|---|---|
| `modules` | `BUILD, VERSION, CONTRACTS, CI, PUBLISH`（跨模块） |
| contract payload | `{prepare_version,build_command,artifacts:[{id,glob,required,extract_command,digest_algorithm,installed_outlets}],comparison,evidence}` |
| Louke build | `python -m build`；必需且仅验证本次发布集合：wheel `dist/louke-*.whl`、sdist `dist/louke-*.tar.gz` |
| extraction | `python tools/louke_python_release_adapter.py inspect --artifact PATH` → `{artifact:absolute_path,kind:"wheel|sdist",version}`；另计算 SHA-256 |
| installed outlets | 每件 artifact 分别 clean venv 安装后，`lk --version` 与 `importlib.metadata.version("louke")` 必须均为 `0.14.0`；本地包无独立 deployment endpoint，故 deployment outlet `N/A` |
| prompt payload check | wheel/sdist 必须包含 canonical `louke/agents/Archer.md`, `louke/agents/Prism.md` 及 registry/schema；安装后 IF-PRM-01 readback可解析同一 bundle |
| ordered gate | version prepare/validate → real build → enumerate every artifact → digest/extract/compare → clean install/public outlet readback |
| output | `{status:"verified|failed",canonical_version,source,evidence:{source_prepared,artifacts_built,artifact_versions_verified},artifacts:[...]}`；只有 `verified` 可 publish |
| errors/recovery | identity/source/build/artifact/extract/version/outlet/prompt 缺失、不匹配或 unknown 均 fail；清空隔离 dist 后从 prepare 重跑，不复用不确定 artifact |
| architecture | `ARC-BUILD`, `ARC-VERSION`, `ARC-PUBLISH` |

### IF-PUB-01 — Publish operation ledger 与恢复

| 字段 | 合同 |
|---|---|
| `modules` | `PUBLISH, STORE, CI, BUILD, VERSION`（跨模块） |
| contract | 以项目事实声明适用操作及顺序。Louke：`merge/main evidence → tag → PyPI wheel+sdist → GitHub Release assets → clean-install smoke`；独立部署 `N/A` |
| operation | `{operation_id,kind,expected_identity,provider,preconditions,credential_ref,status,attempts,observed_fact,artifact_digests,error,recovery,updated_at}`；identity 对同一 release+kind+target 稳定 |
| statuses | `planned | executing | confirmed | failed | uncertain | needs_attention | rolled_back | forward_fix_required`；timeout/ack loss只能 `uncertain`，事实不明确转 `needs_attention` |
| preconditions | current `Louke CI / required` success、IF-BLD-01 `verified`、当前 tag/main映射、所需 protected credential；任一缺失不得调用 provider |
| query-before-retry | tag按 exact ref/SHA，PyPI按 project/version/file digest，GitHub Release按 tag/asset digest，smoke按安装版本查询；唯一精确匹配补记 confirmed，确认未发生才同 identity 重试 |
| idempotency | tag/registry version视为不可变；不得覆盖不匹配资源或用 `--skip-existing` 推断相同；partial success保留 confirmed 项，只继续未完成项 |
| permissions | credential只以 secret reference出现；Runtime/PUBLISH adapter可执行，Agent与PR job无权限 |
| nested policy | `operations[]`、`credentials:{storage,PR_access,minimum_scope_per_operation}`与`deployment:{applicable,reason}`均required且`additionalProperties:false`；空credentials/deployment或unknown provider状态schema fail |
| recovery | 可安全删除的未公开临时资产可 rollback；已公开不可变版本采用 forward-fix；无法确定时停在 `needs_attention`，不报告 success |
| architecture | `ARC-PUBLISH`, `ARC-STORE`, `ARC-SECURITY` |

## 5. Prompt bundle 与独立评审

### IF-PRM-01 — Prompt bundle manifest、deployment readback 与激活

| 字段 | 合同 |
|---|---|
| `modules` | `PROMPTS, REGISTRY, VALIDATOR, SESSION, STORE`（跨模块） |
| closed source set | 本 Spec candidate 精确为 `louke/agents/Archer.md`, `louke/agents/Prism.md`；其它 prompt patch 为 scope error |
| manifest | `{schema_version,bundle_version,bundle_identity,activation_state:"active|candidate-not-deployed|retired",sources:[{path,digest,role,frontmatter,permissions,model_abstraction,protocol_refs,skill_refs,input_schema_ref:{identity,version,digest,activation_state},output_schema_ref:{identity,version,digest,activation_state}}],owning_spec,design_revision,transformer:{identity,version,source,digest},deployments:[{record,record_digest,path,rendered_digest,role,environment_binding,state}],bundle_digest,bundle_digest_scope,activation_prerequisites,stale_if,failure_semantics}`；Archer/Prism input/output均为registry exact refs，禁止`current`/`digest_source` |
| candidate storage | source在package tree；本轮candidate manifest=`design-artifacts/prompts/prompt-bundle.candidate.json`，完整转换结果的bytes length/digest及in-memory readback记录于`design-artifacts/prompts/staging/{archer,prism}.render.candidate.json`，deployment readback与reviewer binding同目录。staging record不包含可被误执行的active副本且未写`.opencode/agents/**`。激活后manifest才按digest进入`.louke/runtime/prompt-bundles/<bundle_digest>.json`；deployed path由environment binding明确，不能从source path猜测 |
| transformer | identity=`louke.board.cmd_opencode`，source=`louke/board.py`，base source digest和version见bundle manifest；移除source-only name/quotation、解析model binding、保留permission、正文语义不变。当前environment binding=`codexmanager/gpt-5.6-sol` |
| deploy/readback | 本轮只作deterministic **staging** render/readback，不调用会覆盖`.opencode/agents/**`的active deployment。readback重新读取source、transformer、staging并返回`candidate_staging_in_sync|missing|drifted|stale`及每项expected/actual digest；它不声称active in_sync |
| dispatch | task manifest先按role-specific input schema验证，再携带 exact active `bundle_digest+role+source/deployment digest`；聊天声明无效。已启动 attempt固定其 active identity，不热加载 candidate |
| activation | candidate 仅在 schema/lint、IF-DES-02、trusted Prism review、deployment readback、implementation baseline均成功后原子替换 active pointer，供后续 dispatch |
| reviewer bootstrap | `reviewer-binding.candidate.json`记录当前Prism执行文件=`.opencode/agents/prism.md`及其既有trusted active bytes digest，review对象为新candidate bundle digest；二者必须不同。candidate不能修改执行中的attempt、自报review或生成PASS |
| stale | source closed set漏列/夹带、source/transformer/environment/staging任一digest drift、requirements/design/contracts/base/discussion任一输入变化，都使bundle/readback/review stale并阻止activation |
| permissions/error | 普通宿主 release只读 installed bundle；`PROMPT_SCOPE_DENIED|PROMPT_DRIFT|PROMPT_UNTRUSTED|PROMPT_SCHEMA_INVALID` fail closed；reconcile产生新 identity，不静默采用手改副本 |
| architecture | `ARC-PROMPTS`, `ARC-REGISTRY`, `ARC-SECURITY`, `ARC-STORE` |

### IF-REV-01 — Prism review result 与 Implementation Baseline

| 字段 | 合同 |
|---|---|
| `modules` | `REVIEW, SESSION, VALIDATOR, STORE, DESIGN`（跨模块） |
| review input | `{design_revision_id,input_digests:{requirements,design_docs,contracts,prompt_bundle},reviewer_execution_bundle,reviewed_candidate_bundle?,attempt_id,reviewer_id}` |
| result | 由 manifest 指定 active Agent I/O schema校验：`{verdict:"PASS|REVISE",bound_input_digest,findings:[{id,severity,artifact,anchor,fr_ids,ac_ids,interface_ids,architecture_anchors,contract_refs,message}],questions:[],advisory:[]}` |
| authority | Prism不写 review artifact、不调用 Runtime命令；Archer无提交 PASS 出口。Runtime持久化 validated result |
| freshness | 任一输入 digest、bundle、discussion或base commit变化使 verdict/program evidence stale；REVISE回到新 Archer revision |
| baseline | 仅同一 revision全部 program checks PASS + fresh Prism PASS后原子生成 `{requirements,design,contracts,registry,prompt_bundle,base_commit,issue_manifest,release_identity,closed_discussions,digest}` 并进入 M-IMPL |
| no second lock | 无 Human 技术 approve字段或第二 M-LOCK action；Human缺席不阻塞，Human direct diff只是下一 author input |
| error/recovery | review task timeout按 session reconcile；invalid identity/schema/result拒绝且不推进。重启从持久 review/attempt恢复，不重复已完成 attempt |
| architecture | `ARC-REVIEW`, `ARC-STORE`, `ARC-DESIGN`, `ARC-SECURITY` |

## 6. Human M-DESIGN surface、事实与迁移

### IF-WEB-01 — M-DESIGN 文档与校验 surface

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DESIGN, STORE, VALIDATOR, REVIEW`（跨模块） |
| surface | Workbench 当前 Project 的 `M-DESIGN` context；自然入口来自批准后的 requirements current，继续路径为 current design/revision，不创建孤立工具页 |
| visible | 精确 requirements/base/facts/revision identity；三文档、七类 contract、两个 prompt source及 digest；program checks、Prism verdict/findings、inline discussions、direct diff |
| actions | authenticated Human 可查看、comment、在 manifest 授权原文 direct edit；可刷新/重连。没有“批准技术方案”动作 |
| availability | Agent lease时原文只读；非授权路径隐藏编辑；validating/review中危险重复动作 disabled；stale显示 expected/current并禁止以旧结果继续 |
| feedback | authoring/validating/waiting_prism/revise/ready/blocked/needs_attention；失败展示 IF-DES-02 定位字段与 remediation；direct edit显示 dirty→saved/new revision，冲突保留用户草稿供明确重做 |
| reconnect/recovery | 由 IF-DES-01 read model恢复同一 revision、diff、discussion、review；未保存浏览器草稿不声称已恢复；`continue_url`回当前锚点 |
| architecture | `ARC-WEB`, `ARC-DESIGN`, `ARC-STORE`, `ARC-REVIEW` |

### IF-FCT-01 — Host Project Facts snapshot

| 字段 | 合同 |
|---|---|
| `modules` | `FACTS, DESIGN, CONTRACTS, VALIDATOR`（跨模块） |
| output | `{workspace_id,base_commit,snapshot_digest,inventory:{languages,runtimes,dependency_files,lockfiles,build_entries,test_entries,version_sources,artifacts,install_deploy_run_outlets,ci_workflows,hooks,default_branch,external_capabilities},observations:[{kind,path_or_identity,status:"present|absent|unsupported",digest?,source}]}` |
| rule | 所有路径必须来自 snapshot；“不存在”也是带 observation 的事实。设计引用使用 observation identity，不引用代码行号 |
| empty project | 明确 `inventory` 空集合 + product constraints；Archer在 design decision中给出完整技术选择、替代和风险，不请求 Human |
| isolation | Louke package/repository facts只在 workspace本身是Louke时可作为宿主事实；通用 prompt/contract不得内置 Python/npm/Maven 等默认 |
| error/recovery | 无法确认 workspace/base、路径逃逸、facts stale 为 `PROJECT_FACTS_*` 且阻止 dispatch；重新盘点产生新 digest并使依赖设计 stale |
| architecture | `ARC-FACTS`, `ARC-SECURITY`, `ARC-DESIGN` |

### IF-AUD-01 — Audit export、restart recovery 与 migration

| 字段 | 合同 |
|---|---|
| `modules` | `STORE, DESIGN, VALIDATOR, REVIEW, PUBLISH, WEB`（跨模块） |
| export | `GET /api/v14/runs/{run_id}/design/audit` → revisions、manifests、diff attribution、program evidence、review identities、operation ledger、baseline refs与digest；secret redacted |
| restart | 从持久化 identity/digest恢复唯一 current revision、pending work和历史；已完成 attempt不重复 dispatch |
| migration input | 旧 `M-LOCK-1`/第二 M-LOCK、旧 prompt/contract schema只读 fixture；输出 `{source_version,target_version,status:"migrated|read_only|unsupported",diagnostics,evidence_digest}` |
| write rule | 新 run只写 `M-REQ-APPROVAL → M-DESIGN → M-IMPL` 和 active canonical schema；migration为单向、可重试、CAS，禁止双写两个 current truth |
| failure/recovery | 缺失/篡改 digest、未知旧版本、migration中断均 fail closed；保留历史和明确 retryability，不创建第二 current revision |
| architecture | `ARC-STORE`, `ARC-MIGRATION`, `ARC-SECURITY` |

## 7. 接口—测试闭合索引

| 接口 | 最低覆盖 |
|---|---|
| IF-DES-01, IF-WEB-01 | integration + CI E2E |
| IF-DES-02, IF-CON-01, IF-REG-01 | unit/contract + integration |
| IF-TST-01, IF-PC-01, IF-CI-01 | contract + integration；CI render/readback另有 CI E2E |
| IF-REL-01, IF-BLD-01 | contract + real build/artifact verification integration |
| IF-PUB-01 | contract + integration fault/recovery |
| IF-PRM-01, IF-REV-01 | contract + integration + CI E2E（trusted review闭包） |
| IF-FCT-01 | contract + integration（至少两个异构 fixture） |
| IF-AUD-01 | integration restart/migration；可操作错误另有 CI E2E |

## 8. Candidate contract 双向索引

| contract kind | 主要IF | ARC carriers | AC binding | candidate path / activation |
|---|---|---|---|---|
| `integration-test` | IF-TST-01及15/15公开出口 | ARC-CONTRACTS, ARC-VALIDATE, ARC-CI, ARC-SECURITY及各IF carrier | 34/34 AC的required integration去向 | `design-artifacts/contracts/integration-test.candidate.json`；runner安装前not-run |
| `e2e-test` | IF-TST-01, IF-WEB-01, IF-DES-01, IF-PRM-01, IF-REV-01, IF-AUD-01 | ARC-WEB, ARC-DESIGN, ARC-PROMPTS, ARC-REVIEW, ARC-STORE | test-plan要求E的9 AC | `design-artifacts/contracts/e2e-test.candidate.json`；Workbench lifecycle安装前not-run |
| `pre-commit` | IF-PC-01, IF-CON-01 | ARC-PRECOMMIT, ARC-CONTRACTS, ARC-SECURITY | AC-FR1000-01, AC-NFR0200-01 | `design-artifacts/contracts/pre-commit.candidate.json`；未安装hooks |
| `github-actions-ci` | IF-CI-01, IF-TST-01, IF-BLD-01 | ARC-CI, ARC-CONTRACTS, ARC-SECURITY, ARC-BUILD | 34/34 AC required jobs/evidence聚合 | `design-artifacts/contracts/github-actions-ci.candidate.json`；workflow未实现 |
| `release-version` | IF-REL-01, IF-REG-01, IF-CON-01 | ARC-VERSION, ARC-FACTS, ARC-REGISTRY | AC-FR1400-01, AC-NFR0100-01, AC-NFR0300-01 | `design-artifacts/contracts/release-version.candidate.json`；project identity drifted |
| `build-artifact` | IF-BLD-01, IF-REL-01, IF-PRM-01 | ARC-BUILD, ARC-VERSION, ARC-PROMPTS | AC-FR1500-01, AC-FR1700-01, AC-FR1800-01, AC-FR1900-01, AC-FR2000-01 | `design-artifacts/contracts/build-artifact.candidate.json`；未真实build |
| `publish-recovery` | IF-PUB-01, IF-CI-01, IF-BLD-01, IF-AUD-01 | ARC-PUBLISH, ARC-CI, ARC-BUILD, ARC-STORE | AC-FR1600-01, AC-NFR0200-01, AC-NFR0400-01 | `design-artifacts/contracts/publish-recovery.candidate.json`；无provider副作用 |

每个candidate instance的`artifact_refs`反向列出本文IF、对应AC/ARC及三文档bytes digest，`commands`逐项绑定公开命令与success/failure。`design-artifact-manifest.candidate.json`再从AC端列出contract kinds，形成34 AC / 15 IF / 16 ARC / 7 contract kinds的machine-readable闭包；instance或manifest任一侧漏项/冲突均`DESIGN.CONTRACT.PARITY`失败。
