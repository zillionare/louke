# v0.14 Workflow Reflow — Public Interfaces

- **Spec ID**: `v0.14-001-workflow-reflow-spec`
- **契约基线**: Spec revision 8；Acceptance revision 9
- **约定**: 本文只定义外部可观察合同。`modules` 来自 `architecture.md`；含两个及以上模块的接口均为跨模块，必须有 integration 覆盖。

## 1. 通用协议

### IF-COMMON-01 — 身份、时间与 digest

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, STORE, DOC, SESSION, GIT, GH`（跨模块） |
| opaque IDs | `workspace_id`, `project_id`, `run_id`, `task_id`, `attempt_id`, `session_id`, `lease_id`, `gate_id`, `challenge_id`, `operation_id` 均为非空、不复用字符串；调用者不得解析其前缀 |
| revision | run 与 artifact revision 为非负、单调递增整数；写请求使用 `expected_*_revision` |
| digest | `sha256:<64 lowercase hex>`；artifact body digest按需求文档声明的placeholder scheme |
| time | UTC RFC 3339，带时区；排序使用 event `sequence`，不得依赖墙钟先后 |
| release identity | `/projects/new`输入合法集合不由本设计收窄；继承宿主已签Project preview合同并使用其返回的opaque `{external,canonical,branch}`。本次shipping identity另固定为tag `v0.14.0` / package `0.14.0` |
| Human principal | 只有`WEB`在服务端认证上下文建立`{principal_id,session_id,kind:"human"}`；业务payload中的`actor`/`role`无authority且不得覆盖上下文。read接口须认证（health/无workspace identity的启动诊断除外）；decision、return、M-LOCK-1须该Human principal |
| bootstrap | `POST /api/v14/auth/bootstrap` body `{challenge}`，只接受exact Origin下、当前服务实例生成、尚未使用且未超过120秒的challenge；成功204并设置opaque session cookie，返回页面随后从`GET /api/v14/auth/session`取得`{principal_id,expires_at,csrf_token}` |
| credential | cookie名`louke_session`，`HttpOnly; SameSite=Strict; Path=/`且无`Domain`；HTTPS另有`Secure`。CSRF token绑定session并由mutation的`X-Louke-CSRF`携带；session在服务停止或连续8小时后失效 |
| Agent exclusion | Chat/OpenCode task/attempt/session只能是`kind:"agent"`，永远不能接收bootstrap challenge、Human cookie/CSRF或获得/委托Human principal；Agent/anonymous即使提交`role=human`仍拒绝 |
| 覆盖 | `TP-COMMON`；所有 integration/e2e场景校验格式和不可解析性 |

### IF-COMMON-02 — 成功与错误 envelope

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, STORE`（跨模块） |
| success | HTTP 2xx JSON 至少含 `ok:true`, `request_id`, `current:{run_id?,run_revision?,phase?,artifact_revision?}`；create为201，幂等复用可200 |
| error | `{"ok":false,"request_id":"…","error":{"code":"…","message":"非秘密说明","retryable":bool,"current":{…},"details":{…},"remediation":"…"}}` |
| 400 | 输入/结构非法：`VALIDATION_FAILED`, `RELEASE_VERSION_INVALID`, `SPEC_SCOPE_TOO_LARGE`, `ACCEPTANCE_COVERAGE_MISSING` |
| 401/403 | 缺/过期session为401 `AUTH_REQUIRED|SESSION_EXPIRED`；anonymous/Agent调用Human动作403 `HUMAN_AUTHORITY_REQUIRED`；错误/缺失Origin或CSRF为403 `ORIGIN_FORBIDDEN|CSRF_FAILED`；过期/其它实例challenge为403 `AUTH_CHALLENGE_INVALID`；另有`WRITE_SCOPE_DENIED` |
| 404 | opaque identity不存在，不泄漏其它workspace信息 |
| 409 | stale/CAS/phase/identity/replay冲突：`WORKFLOW_STATE_CONFLICT`, `DOCUMENT_WRITE_CONFLICT`, `STORY_INITIALIZATION_CONFLICT`, `UPSTREAM_RETURN_TARGET_INVALID`, `CONTROLLED_COMMIT_CONFLICT`, `RESOURCE_IDENTITY_CONFLICT`, `AUTH_CHALLENGE_REPLAYED`, `GATE_CHALLENGE_REPLAYED` |
| 423 | `REQUIREMENTS_LOCKED` |
| 502/503/504 | 外部失败/不可用/timeout；若副作用结果未知，`retryable:false` 且 current operation为`uncertain`，要求先reconcile |
| 恢复 | 所有冲突返回当前 revision/phase 和 `continue_url`；客户端刷新该URL后重做明确动作，不自动重放危险请求 |
| auth fail invariant | 认证/Origin/CSRF/challenge失败在业务dispatch前结束：run/gate/artifact/文档bytes/Git ref/operation ledger及外部调用计数全部不变；challenge失败不建立cookie，session过期导航到当前服务的新bootstrap入口而不重放原mutation |
| 覆盖 | `TP-ERROR` contract + integration；所有失败AC复用 |

### IF-COMMON-03 — Workflow event/timeline

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, STORE, DOC, SESSION, GIT, GH`（跨模块） |
| endpoint | `GET /api/v14/runs/{run_id}/events?after={sequence}&limit={1..500}` |
| output | `events[]:{event_id,sequence,type,at,actor:{kind,id},phase,attempt_id?,correlation_id,input_digest?,output_digest?,result,resource_ref?}`, `next_after` |
| 状态 | sequence在run内连续递增；setup/step/revision/review/gate/task/commit/external operation均有类型化event |
| secret | actor仅非秘密identity；details、error、digest不得含credential/token/cookie/provider secret |
| reconnect | 重连使用最后已确认sequence；重复返回相同event bytes，不生成新业务动作 |
| 覆盖 | `TP-FR0600`, `TP-FR0900`, `TP-FR2100`, `TP-NFR0200`, golden e2e |

## 2. CLI 与启动诊断

### IF-CLI-01 — `lk serve`

| 字段 | 合同 |
|---|---|
| `modules` | `CLI, WEB, SETUP, STORE`（跨模块） |
| 命令 | `lk serve [--host 127.0.0.1] [--port PORT] [--no-open]`；cwd即目标workspace；需求workflow无其它CLI推进命令。`--host`解析为非loopback地址时以`NON_LOOPBACK_AUTH_UNAVAILABLE`硬失败 |
| stdout | 服务建立后单行公开`Louke Workbench: http://HOST:PORT`；自动打开或`--no-open` controlling-terminal还得到一次性fragment bootstrap URL（不得进入access log）；不得在硬失败时输出READY |
| stderr | 硬前置失败逐项 `code`, 非秘密target, remediation；不得输出secret |
| exit | 正常收到SIGINT/SIGTERM并完成关闭为0；解释器/package/workspace/port/app factory失败为非0；Web建立后的readiness BLOCKED不导致进程退出 |
| 副作用 | 硬失败（含非loopback host）不得监听、创建DB/WorkflowRun/外部资源；重复启动有效setup不得修改manifest或create资源 |
| 恢复 | 修复后从同cwd重跑；已有SQLite/run由服务启动reconcile |
| 覆盖 | `TP-FR0100`, `TP-FR2100`, `TP-NFR0300`；unit/integration/e2e |

### IF-WEB-01 — 启动诊断页

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, SETUP, DRIVER`（跨模块） |
| surface | `GET /`；Web可建立时默认挂载在Workbench主区域，不能被独立隐藏页替代 |
| input/action | 页面自动读取readiness；Human可逐项`重新检查`，或进入Setup；无需CLI推进 |
| visible | `louke`, `dependencies`, `configuration`, `provider_auth`, `model`, `opencode`, `workspace_identity` 每项显示 `READY|BLOCKED|UNKNOWN`、非秘密identity、message、remediation |
| availability | 所有项READY且setup有效：显示/启用release入口；否则release动作显示但disabled并列blockers |
| states | loading显示正在检查且禁止submit；error/unknown不伪报blocked已知原因；reconnect后以最新readiness刷新 |
| continue | setup有效→`/projects/new`；需setup→`/setup`；失败项→同页recheck |
| 覆盖 | `TP-FR0100`, `TP-NFR0300`；integration + e2e |

### IF-API-01 — Readiness

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, SETUP, DRIVER, STORE`（跨模块） |
| endpoints | `GET /api/v14/readiness`; `POST /api/v14/readiness/recheck` body `{check_ids?:[]}` |
| output | `{overall:"READY|BLOCKED|UNKNOWN", checks:[{id,status,identity?,message,remediation}], setup:{status,revision?}, release_submit_enabled, checked_at}` |
| errors | recheck外部失败仍返回可观察check `UNKNOWN`；非法check id为400 |
| 覆盖 | `TP-FR0100`, `TP-FR0200`, `TP-FR2100`；contract + integration |

## 3. Workspace Setup

### IF-WEB-02 — Setup preview

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, SETUP, STORE, GH`（跨模块） |
| surface | `GET /setup`，由诊断页自然进入 |
| visible | setup revision；每个workspace级字段的候选`value/provenance/status`；冲突、缺失、授权、已完成/失败/不确定operation及remediation |
| actions | 对缺失字段输入；冲突候选单选；授权operation明确勾选；`确认`、`取消`、`重新核对` |
| availability | 无未裁决冲突且必要输入完整时确认enabled；提交中全部变更动作disabled；取消留在Setup且无外部修改 |
| feedback | dirty输入在导航前提示；stale revision显示冲突并保留当前未提交选择供Human重做；partial/reconnect恢复同revision与逐项状态 |
| boundary | 页面不得展示或创建具体release Project/run/GitHub Project/branch/Spec目录 |
| 覆盖 | `TP-FR0200`, `TP-NFR0100`, `TP-NFR0200`, golden e2e |

### IF-API-02 — Setup preview/decision/reconcile

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, SETUP, STORE, GH`（跨模块） |
| GET | `GET /api/v14/setup` → `{status:"preview|waiting_human|applying|blocked|complete",revision,candidates:[{field,required,options:[{value,provenance}],selected?,status}],operations:[...],manifest?}` |
| confirm | `POST /api/v14/setup/confirm` body `{expected_revision,selections:{field:value},authorized_operation_ids:[],idempotency_key}` |
| reconcile | `POST /api/v14/setup/reconcile` body `{expected_revision}`；只查询/继续已授权workspace级operation |
| manifest | `{workspace_id,repository:{provider,node_id,full_name},owner,provider_namespace,auth_identity,model_identity,opencode_identity,backlog_namespace,release_project_capability,setup_revision,decision:{actor,at,selections,provenance},operations[]}`；不得含secret |
| errors | 409 stale；冲突未裁决为400；权限/多个namespace/证据不足保持`waiting_human|blocked`，不模糊选择 |
| idempotency | 相同confirm key返回同revision/operation IDs；已完成项不重复修改 |
| 覆盖 | `TP-FR0200`, `TP-FR2100`, `TP-NFR0100`, `TP-NFR0200`；contract + integration |

## 4. Release 请求与 Foundation

### IF-WEB-03 — `/projects/new` release preview

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, STORE, GIT, GH`（跨模块） |
| surface | `GET /projects/new`；readiness READY后的主动作 |
| input | 非空一句话`story`；`release_version`须通过宿主已签Project preview合同的合法性校验，本设计不另行限制其格式或prerelease/build metadata |
| actions | `预览`只校验并显示workspace/story/version/canonical branch；`确认`绑定preview revision/digest；确认中disabled |
| visible result | 非法输入显示字段级error；active release显示Backlog identity、阻塞原因和Projects/Backlog返回链接并结束session；preflight/Foundation显示full refs/SHA/relation、各资源状态/remediation |
| states | preview dirty；confirm loading；blocked/uncertain/conflict不进入Story；reconnect恢复request/operation |
| continue | Foundation + Story初始commit成功→Story编辑页；blocked→Projects/Backlog；修复main/权限后在同release request点击recheck |
| 覆盖 | `TP-FR0300`, `TP-FR0400`, `TP-FR0500`, `TP-NFR0300`；integration + e2e |

### IF-API-03 — Release preview/confirm/status

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, STORE, GIT, GH`（跨模块） |
| preview | `POST /api/v14/releases/preview` body `{story,release_version}` → `{preview_id,preview_revision,request_digest,workspace_id,story,release:{external,canonical,branch},side_effects:[]}` |
| confirm | `POST /api/v14/releases/confirm` body `{preview_id,expected_preview_revision,request_digest,idempotency_key}` → 202 `{request_id,status,continue_url}` |
| status | `GET /api/v14/releases/requests/{request_id}` → `{status:"preflight|backlogged|foundation|blocked|conflict|ready",backlog?,main_check?,foundation?,project_id?,run_id?,continue_url}` |
| active conflict | 单事务形成唯一`backlog:{entry_id,story,release_version,reason,created_at,source_identity}`；不得产生release资源 |
| errors | invalid 400；stale 409；main/ref/identity错误以200 status read model可见，confirm不得绕过 |
| idempotency | workspace+request_digest唯一；重复/并发confirm返回相同request/backlog/project identity或明确409 conflict |
| 覆盖 | `TP-FR0300`, `TP-FR0400`, `TP-NFR0100`, `TP-FR2100`；contract + integration |

### IF-EXT-01 — Foundation manifest 与 Git identity

| 字段 | 合同 |
|---|---|
| `modules` | `DRIVER, STORE, GIT, GH`（跨模块） |
| observation | `GET /api/v14/releases/requests/{request_id}/foundation` |
| main check | `{declared_remote,remote_main:{full_ref,sha},previous_branch:{full_ref,sha,relation:"merged|ahead|behind|diverged|unknown"},local_main?,checked_at,status,remediation}` |
| resources | `{local_project:{id},workflow_run:{id},github_project:{node_id,url},release_branch:{full_ref,start_sha,checked_out,head_symbolic_ref,head_sha},spec_directory:{path,digest},operations:[{operation_id,kind,status,expected_identity,actual_identity?,error?}]}` |
| index baseline | `{target_path,target_head:{present,mode?,blob?},target_index:{present,stage?,mode?,blob?,flags:[]},target_worktree_digest?,non_target_semantic_fingerprint}`；首次目标不存在或目标单一stage-0 entry与HEAD tree一致，非目标fingerprint覆盖全部entries/flags/staged intent |
| complete | 仅所有identity唯一匹配、branch start=`remote_main.sha`、`checked_out=true`、`head_symbolic_ref=full_ref`、`head_sha=full_ref SHA`且operations confirmed时true；不支持detached/非checked-out release ref |
| errors/recovery | refresh失败、关系非merged、checkout不能保留非目标index/worktree语义、目标预staged/conflict/special flag/来源不明、identity冲突或unknown均complete=false；partial先按operation query，不创建候选资源 |
| 覆盖 | `TP-FR0400`, `TP-FR2100`, `TP-NFR0100`, `TP-NFR0200`；integration |

### IF-WEB-04 — Story 初始化与编辑页入口

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, DOC, GIT, STORE`（跨模块） |
| surface | `GET /projects/{project_id}/requirements/story`（兼容链接可重定向至该canonical URL） |
| visible | project/run ID、phase `M-STORY`、artifact revision/digest/commit、正文、writer/readonly原因、review/dirty/discussion状态、Chat |
| initialization | 正文原始输入位置含完整Human story且template其余结构保留；冲突显示`STORY_INITIALIZATION_CONFLICT`，现有bytes不变 |
| navigation | Foundation上下文→Story→同页Chat/review；后续可从Project current返回三文档页 |
| 覆盖 | `TP-FR0500`, `TP-FR0700`, golden e2e |

## 5. Run、phase、revision 与 write lease API

### IF-API-04 — Project current / run read model

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, STORE, DOC, SESSION, GIT, GH`（跨模块） |
| endpoint | `GET /api/v14/projects/{project_id}/current`；亦可按`GET /api/v14/runs/{run_id}`读取同一run部分 |
| output | `{project,run:{run_id,revision,phase,status},artifact:{kind,path,revision,version_token,digest,commit_sha,locked},writer?,human_wait?,review:{round,human_verdict,agent_verdict,open_threads,edited,format},task:{task_id,attempt_id,session_id,status,connection},gate?,issues?,last_error?,allowed_actions:[],continue_url,event_cursor}` |
| allowed actions | 服务端计算；UI只渲染列表中动作。stale/illegal客户端声明不能新增动作 |
| refresh/restart | 相同持久化事实产生字段相同的read model；仅时间相关connection可变化且须明确 |
| 覆盖 | `TP-FR0600`及所有phase TP；integration + e2e |

### IF-API-05 — Phase action

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, STORE, DOC, SESSION`（跨模块） |
| endpoint | `POST /api/v14/runs/{run_id}/actions` |
| input | `{action:"story_decision|human_review|return_upstream|retry|cancel_dirty|reconcile",expected_run_revision,expected_artifact_revision?,idempotency_key,payload:{...}}` |
| output | success envelope + updated read model/continue URL |
| authority | `story_decision`、`human_review`、`return_upstream`仅取服务端Human principal；input无actor/role authority。anonymous、Agent session、cross-origin、stale session、CSRF失败均按IF-COMMON-02拒绝；Agent output不得调用phase transition；`retry`只对read model列出的可重试项 |
| conflicts | phase/action非法、revision stale均409 `WORKFLOW_STATE_CONFLICT`且所有artifact/gate/external counts不变 |
| 覆盖 | `TP-FR0600`, `TP-FR0700`, `TP-FR0800`, `TP-FR1100`, `TP-FR1500`, `TP-NFR0100` |

### IF-API-06 — Artifact read/write CAS

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, DOC, STORE, GIT`（跨模块） |
| read | `GET /api/v14/runs/{run_id}/artifacts/{story|spec|acceptance}` → `{path,body_md,rendered_html,revision,version_token,digest,commit_sha,writer,readonly,readonly_reason,dirty_registered,locked}` |
| write | `PUT` same path body `{body_md,expected_run_revision,expected_artifact_revision,version_token,lease_id,idempotency_key}` |
| success | 200 `{revision,commit_sha,document_operation:{operation_id,status:"accepted",prepared_commit,ref_confirmed_at,target_index_synced_at,accepted_at,reconcile:{observed_head,observed_ref,observed_document_digest,target_index_blob,non_target_index_fingerprint,porcelain_v2_digest,decision}}}`；相同idempotency key返回同operation/revision/commit，不新增commit/event |
| pending/reconcile | crash后同一PUT或`POST .../reconcile` body `{operation_id,expected_run_revision}`返回当前`document_operation.status`；`prepared|ref_confirmed|target_index_synced`不是write success且不得启动review。只有checked-out HEAD/ref、目标HEAD/index/worktree、非目标index semantics全部满足IF-EXT-02才补记同一`accepted`revision |
| conflict | stale token/revision/lease 409 `DOCUMENT_WRITE_CONFLICT`含current revision/token；锁后423；wrong scope403；bytes不变 |
| commit failure | 409 `CONTROLLED_COMMIT_CONFLICT`，operation为`conflict|needs_attention`，不启动下一review；返回expected/actual HEAD/ref、document digest、目标index entry、非目标semantic fingerprint差异、porcelain-v2、known effects和remediation，不覆盖不可归因bytes |
| 覆盖 | `TP-FR0500`, `TP-FR0900`, `TP-FR1000`, `TP-FR1300`, `TP-FR1700`, `TP-FR2000`, `TP-NFR0100` |

### IF-API-07 — Dirty 与 write lease

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, DOC, STORE, SESSION`（跨模块） |
| dirty | `PUT /api/v14/runs/{run_id}/artifacts/{kind}/dirty` body `{expected_artifact_revision,dirty:true|false,client_id}`；dirty=false只表示无未保存修改，不保存正文 |
| acquire | `POST .../leases` body `{holder:{kind:"human|agent",id,role},expected_run_revision,expected_artifact_revision,version_token,task_id?}` |
| output | `{lease_id,status:"active|blocked",holder,document,base_revision,version_token,issued_at,expires_at,blockers:[]}` |
| release | `DELETE .../leases/{lease_id}`；幂等200；lease到期后任何write仍需current CAS |
| availability | Human dirty时Agent acquire返回409 `HUMAN_DIRTY_BLOCKS_HANDOFF`；页面提示save/discard；同document第二holder返回409含current holder |
| feedback | lease被收回/过期时编辑器立即readonly；未保存Human内容不得被自动discard |
| 覆盖 | `TP-FR1000`, `TP-FR1300`, `TP-FR1400`, `TP-FR1600`, `TP-NFR0100`；integration + e2e |

### IF-DATA-01 — Artifact revision evidence

| 字段 | 合同 |
|---|---|
| `modules` | `DRIVER, DOC, STORE, GIT, WEB`（跨模块） |
| endpoint | `GET /api/v14/runs/{run_id}/artifacts/{kind}/revisions` |
| item | `{revision,status:"current|stale|superseded|locked",digest,parent_commit,commit_sha,actor,run_revision,round,task_id?,attempt_id?,session_id?,created_at,document_operation:{operation_id,status:"accepted",prepared_commit,ref_confirmed_at,target_index_synced_at,accepted_at}}`；另有`pending_operations[]`公开`registered|document_written|prepared|ref_confirmed|target_index_synced|conflict|needs_attention`、目标HEAD/index/worktree及非目标fingerprint reconcile evidence |
| invariant | `git symbolic-ref HEAD`=受控full ref且`git rev-parse HEAD/full_ref`均等于current commit；accepted目标的HEAD/index blob与worktree digest为current evidence，porcelain-v2无目标记录；非目标entries/flags/staged intent与operation baseline语义相等。`ref_confirmed`或`target_index_synced`可在重启后补记同一operation/revision，未accepted operation无current revision/verdict；历史不可改写 |
| 覆盖 | `TP-FR0500`, `TP-FR0900`, `TP-FR1000`, `TP-FR1200`, `TP-FR2000`, `TP-NFR0200` |

## 6. Story / Spec / Acceptance 人机交互

### IF-WEB-05 — Chat 面板

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, SESSION, STORE`（跨模块） |
| surface | 当前Story/Spec/Acceptance页侧边Chat；绑定当前run、phase、task，不是独立workflow入口 |
| visible | Agent role、task/attempt/session IDs、connection `connected|reconnecting|recovered|rebuilt|blocked`、消息发送状态、建议/verdict、最近非秘密error |
| action | Human发送reply、retry connection、回到current位置；reply含客户端correlation identity，发送中disabled以抑制重复 |
| feedback | reply先显示`persisted`再`dispatched|uncertain`；断连不显示Agent停止；恢复原session显示`recovered`，确认丢失的新session显示`rebuilt`且不伪报PASS |
| permissions | Chat不能呈现Agent可点击的Human decision/approve；author/reviewer write由lease决定；Chat/Agent transport不转发Human cookie/CSRF/bootstrap且Agent session不能调用Human-only endpoint |
| 覆盖 | `TP-FR0700`, `TP-FR0900`, `TP-FR1900`, `TP-FR2100`, golden/fault e2e |

### IF-API-08 — Semantic task/session/message

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, SESSION, STORE, DOC`（跨模块） |
| task read | `GET /api/v14/runs/{run_id}/tasks/{task_id}` → `{task_id,run_id,phase,role,artifact:{kind,revision,digest},write_scope,output_contract_digest,status,attempts:[...],active_attempt,session_id}` |
| attempt | `{attempt_id,status,session_id,input_digest,manifest_digest,dispatch_count,result_status?,error?}` |
| reply | `POST .../messages` body `{client_message_id,correlation_id,body,expected_attempt_id}` → `{message_id,status:"persisted|dispatched|uncertain",event_sequences:{persisted,dispatched?}}` |
| reconcile | `POST .../reconcile`查询原session/turn/result；只在not-found且无结果时新attempt；running不dispatch |
| result validation | 受控结果须匹配role/task/attempt/manifest/artifact/output schema/write scope；否则`result_status=rejected`并列reason，run/artifact/verdict不变 |
| secret | task manifest/Agent input只含非秘密identity/digest及必要需求正文，不含credential/token/cookie |
| 覆盖 | `TP-FR0700`, `TP-FR0900`, `TP-FR1200`, `TP-FR1300`, `TP-FR1400`, `TP-FR1600`, `TP-FR1900`, `TP-FR2100` |

### IF-WEB-06 — Human review 与 inline discussion

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, DOC, STORE, SESSION`（跨模块） |
| surface | 三个文档页的review上下文；显示revision/digest、round、edited、open/reopen count、Human/Agent verdict |
| actions | direct edit/save；create/reply/resolve/reopen discussion；提交`comment`或`no comment` |
| availability | dirty或本轮已产生document edit时`no comment`disabled；open/reopen/未保存编辑时不能PASS；Agent写窗口readonly |
| success | clean current revision + `no comment` + zero open/reopen记录digest-bound Human PASS；comment显示等待author rework |
| errors/recovery | 伪造no-comment返回409 `HUMAN_REVIEW_EDITED`; stale提交显示current revision；刷新/重连保留threads、edited和verdict |
| 覆盖 | `TP-FR1100`, `TP-FR1200`, `TP-FR1400`, `TP-FR1600`, fault e2e |

### IF-API-09 — Discussion / review verdict

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, DOC, STORE, SESSION`（跨模块） |
| discussions | `GET /api/v14/runs/{run_id}/artifacts/{kind}/discussions?revision=R`; `POST .../discussions` body `{action:"create|reply|resolve|reopen",anchor,thread_id?,body,expected_artifact_revision,lease_id}` |
| discussion output | canonical thread `{thread_id,status:"OPEN|RESOLVED|REOPEN",initiator,last_speaker,anchor,artifact_revision}`，写回Markdown后可被`lk discuss query`识别 |
| Human verdict | `POST /api/v14/runs/{run_id}/reviews/{round}/human` body `{signal:"comment|no_comment",expected_artifact_revision,expected_digest,idempotency_key}` |
| Agent verdict | 只由validated task result登记 `{reviewer_role,verdict:"PASS|REJECT",digest,task_id,attempt_id}`，无公共伪造POST |
| format result | read model `{status:"pending|pass|fail|stale",errors:[{file,location,rule,message}]}` |
| 覆盖 | `TP-FR1100`, `TP-FR1200`, `TP-FR1400`, `TP-FR1600`, `TP-NFR0200` |

### IF-WEB-07 — Spec 编辑页

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, DOC, SESSION, STORE`（跨模块） |
| surface | `GET /projects/{project_id}/requirements/spec`；M-STORY通过后自动导航 |
| visible/action | Sage authoring时readonly+task；review时复用IF-WEB-06；结构/format错误显示requirement或文档location；合法return仅M-STORY |
| continue | semantic+format当前PASS→Acceptance页；失败→同一Sage上下文修订；return确认→Story页 |
| 覆盖 | `TP-FR1300`, `TP-FR1400`, `TP-FR1500`, golden e2e |

### IF-WEB-08 — Acceptance 编辑页

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, DOC, SESSION, STORE`（跨模块） |
| surface | `GET /projects/{project_id}/requirements/acceptance`；M-SPEC semantic+format通过后自动导航 |
| visible/action | Sage authoringreadonly；显示绑定Story/Spec digests、缺失requirement IDs；review复用IF-WEB-06；return targets为M-SPEC/M-STORY |
| continue | review+format+coverage当前PASS→Project current M-LOCK-1；上游digest变化显示stale并隐藏approve |
| 覆盖 | `TP-FR1500`, `TP-FR1600`, golden e2e |

### IF-API-10 — Return upstream

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, STORE, DOC, SESSION`（跨模块） |
| discover | current read model `allowed_return_targets`: M-SPEC=`[M-STORY]`; M-ACC=`[M-SPEC,M-STORY]` |
| submit | IF-API-05 action `return_upstream`, payload `{target,reason,confirm:true}` |
| success | phase=target；历史artifact/review保留；target及下游 verdict/format/approval=`stale|superseded`；Git history不删除 |
| authority/error | 仅服务端Human principal；Agent suggestion形成`human_wait`；anonymous/Agent/cross-origin/stale session/challenge replay按IF-COMMON-02失败且phase/revision、文档bytes、Git/外部operation全不变；非法target 409 `UPSTREAM_RETURN_TARGET_INVALID`且phase/revision不变 |
| 覆盖 | `TP-FR1500`, `TP-FR1600`; integration + e2e |

## 7. M-LOCK-1 与 Project current

### IF-WEB-09 — Project current 页

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, STORE, DOC, GH`（跨模块） |
| surface | `GET /projects/{project_id}/current`; Workbench Projects中的active项目入口 |
| visible | IF-API-04全部状态；三文档links/revision/digests/locked；M-LOCK-1 blockers/challenge；Issue逐requirement状态与URL；timeline |
| approve availability | 仅三文档当前review、discussion、format、上游digests全闭合时显示且enabled；pending blocker列具体项；只有认证Human可见可用动作 |
| feedback | approve进行中防重复；success显示locked和Issue reconcile；partial/uncertain逐ID显示provider error/remediation；刷新/重连恢复同位置 |
| continue | 文档link返回只读文档；Issue URL跳GitHub；失败修复后`reconcile`；全部linked显示后续流程入口（本Spec不定义其行为） |
| 覆盖 | `TP-FR0600`, `TP-FR1600`, `TP-FR1700`, `TP-FR1800`, `TP-FR2100`, golden e2e |

### IF-API-11 — M-LOCK-1 gate

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, STORE, DOC, GH`（跨模块） |
| read | `GET /api/v14/runs/{run_id}/gates/m-lock-1` → `{gate_id,status:"blocked|pending|approved|stale",challenge_id?,expected_run_revision,documents:{story:{revision,digest},spec:{...},acceptance:{...}},joint_digest,blockers:[],decision?}` |
| approve | `POST .../approve` body `{challenge_id,expected_run_revision,joint_digest,idempotency_key}`；actor只来自服务端Human principal，payload不得声明/覆盖 |
| decision | `{actor,at,challenge_id,run_revision,documents,joint_digest}`；同key/revision重试返回同decision |
| errors | anonymous/Agent/cross-origin/stale session为401/403；同idempotency key的响应重取按`decision`行返回原decision，已消费challenge被其它key/session replay则409 `GATE_CHALLENGE_REPLAYED`，过期/其它session challenge为403；blocker/revision/digest错误为409。全部失败保持原gate状态、三文档bytes/locked flag/Git ref不变且Issue/其它外部operations不新增；批准后三个artifact atomic locked |
| locked write | IF-API-06 返回423，bytes/digests不变 |
| 覆盖 | `TP-FR1700`, `TP-FR1800`, `TP-NFR0100`, `TP-NFR0200`; integration + e2e |

## 8. Git/GitHub 外部合同

### IF-EXT-02 — 受控 Git revision

| 字段 | 合同 |
|---|---|
| `modules` | `DRIVER, DOC, GIT, STORE`（跨模块） |
| public evidence | `GET /api/v14/runs/{run_id}/git-operations/{operation_id}`与IF-DATA-01/timeline；外部可用`git symbolic-ref`, `git rev-parse`, `git cat-file`, `git diff-tree`, `git ls-files --stage/-v`, `git diff --cached --raw`, `git status --porcelain=v2`独立核对 |
| identity | `{operation_id,repository_identity,repository_worktree,full_ref,run_id,artifact_kind,base_revision,expected_parent,document_path,preimage_digest,intended_digest,idempotency_key_digest,prepared_commit?}`；`full_ref`是当前worktree的symbolic HEAD，相同logical write稳定不变 |
| baseline | `{head:{symbolic_ref,commit,target:{present,mode?,blob?}},index:{target:{present,entries:[{stage,mode,blob}],flags:[]},non_target_semantic_fingerprint},worktree:{target_digest?,non_target_digest},porcelain_v2_digest}`；目标须与expected parent一致/共同不存在，预staged、conflict stage、特殊flag或来源不明在副作用前拒绝 |
| state/evidence | `{status:"registered|document_written|prepared|ref_confirmed|target_index_synced|accepted|conflict|needs_attention",prepared:{blob,tree,commit}?,ref:{expected,observed,confirmed_at?},head:{symbolic_ref,observed},document:{observed_digest},index:{target:{stage,mode,blob},non_target_semantic_fingerprint,synced_at?},porcelain_v2_digest,known_effects:[],reconcile:{at,decision,proofs:[]},accepted_revision?}` |
| reconcile | `POST /api/v14/runs/{run_id}/git-operations/{operation_id}/reconcile` body `{expected_run_revision}`；ref=expected parent时复用prepared commit做一次CAS；ref=prepared且目标index仍为baseline时只同步该entry。非目标fingerprint相等才补`target_index_synced`并在完整验证后接受；非目标已漂移则保留锁内观察到的当前非目标entries/flags、仅repair目标reverse diff并转`needs_attention`。index已为prepared时不重写；目标为第三值或其它不可归因变化转`conflict|needs_attention` |
| invariant | prepared/result tree diff只含document；accepted时`symbolic HEAD=full_ref`且`HEAD=ref=result commit`，目标HEAD/index/worktree为accepted blob/bytes，porcelain-v2没有目标staged/unstaged记录。所有**非目标**index entries、stage/mode/blob、flags及cached staged intent、原非目标staged/unstaged/untracked与其它文件bytes语义不变；不要求raw index file bytes相等 |
| crash seams | ref CAS成功但target sync前、目标index原子安装后但状态写入前、`target_index_synced`后/Store accepted前均可kill；恢复只能补同一operation/OID/revision。任一pre-accepted状态无新verdict/phase推进 |
| error | target预staged/source unknown、index lock/CAS失败、非目标fingerprint漂移、HEAD/ref/bytes归因冲突返回`CONTROLLED_COMMIT_CONFLICT`及差异evidence；ref已CAS时目标仍为旧baseline则必须单路径sync/repair后fail，目标已变则不覆盖。不得回滚或全index恢复，无reset/checkout/force push、无第二commit、下一review不启动 |
| branch cleanup | Park/No-Go只有证明local-only且仅初始化commit/无其它修改才delete；否则保留并`needs_attention` |
| 覆盖 | `TP-FR0800`, `TP-FR0900`, `TP-FR1000`, `TP-FR2000`, `TP-FR2100`；integration |

### IF-EXT-03 — Requirement Issue / Project association

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, STORE, GH`（跨模块） |
| endpoints | `GET /api/v14/runs/{run_id}/issues`; `POST /api/v14/runs/{run_id}/issues/reconcile` body `{expected_run_revision}` |
| item | `{requirement_id,operation_id,status:"pending|created|linked|reused|failed|uncertain|conflict",issue:{number,url,node_id,title,body_identity}?,project:{node_id,item_id?},expected_identity,actual_identity?,provider_error?,remediation?}` |
| expected identity | repository node ID + spec ID + exact requirement ID + locked joint digest；title首个且唯一token精确`[{ID}]`；body含ID、locked Spec anchor URL、Acceptance anchor URL；Project node ID来自Foundation |
| target | 按locked Spec Valid非`❌`单元动态计算；当前为21 FR+3 NFR=24 |
| gate | M-LOCK-1未approved时403/409，远端search/create/link计数均不增 |
| reconcile | 唯一精确候选复用；零候选且确认未创建才create；多候选/字段冲突/模糊标题进入conflict，不创建第二候选；partial只补失败项 |
| complete | 每个target恰一Issue和Project item且status linked/reused；否则phase不complete |
| real path | real smoke不得直调`GH` adapter或预写locked state；只能从clean installed wheel经Workbench Setup/release/Foundation、六个真实OpenCode author/reviewer task和认证Human M-LOCK页面形成locked revision，再点击Project current reconcile动作触发本接口。当前real operation必须返回完整24 items；不存在代表Issue/partial-success模式 |
| real evidence | report逐target公开`requirement_id,operation_id,issue_number,issue_node_id,issue_url,project_node_id,item_id,status,forward_identity,reverse_identity`；target/Issue/item count均24、ID集合等于locked Spec且全部linked/reused才成功 |
| 覆盖 | `TP-FR1800`, `TP-FR2100`, `TP-NFR0100`, `TP-NFR0200`, stand-in/完整real e2e |

### IF-DATA-02 — Backlog query

| 字段 | 合同 |
|---|---|
| `modules` | `WEB, DRIVER, STORE`（跨模块） |
| endpoint | `GET /api/v14/backlog?workspace_id=...` |
| item | `{entry_id,request_digest,story,release_version,reason,created_at,source_identity,decision?,story_digest?,source_run?}` |
| identity | blocked release confirm和Park/No-Go分别以其logical identity唯一；重启bytes不变 |
| 覆盖 | `TP-FR0300`, `TP-FR0800`, `TP-NFR0100`；integration + e2e |

## 9. Release artifact 与 CI 接口

### IF-REL-01 — project-local release adapter

| 字段 | 合同 |
|---|---|
| `modules` | `CLI, GIT`（跨模块） |
| canonical input | tag `vMAJOR.MINOR.PATCH`；本次shipping identity `v0.14.0` / canonical `0.14.0` |
| prepare | `python tools/louke_python_release_adapter.py prepare --tag "$TAG"`；只写构建工作副本的root `pyproject.toml [project].version`；非法/缺失tag非0 |
| inspect | `python tools/louke_python_release_adapter.py inspect --artifact PATH` → JSON `{artifact:absolute_path,kind:"wheel|sdist",version}`；缺失/非法/无metadata非0 |
| build | `python -m build`；必须同时产生一个wheel和一个sdist |
| installed outlets | clean venv中的 `lk --version` 和 `importlib.metadata.version("louke")`；均精确canonical version |
| evidence | scheme-selected、source-prepared、artifacts-built、artifact-versions-verified分开记录；最后一项前不得publish |
| failure | 任一source/build/artifact/inspect/installed出口不匹配或不确定均exit非0 |
| 覆盖 | `TP-REL`, CI `artifact-verify`；integration/build gate |

### IF-CI-01 — 宿主测试/质量命令

| 字段 | 合同 |
|---|---|
| `modules` | `CLI, WEB, DRIVER, STORE, DOC, SESSION, GIT, GH, SETUP`（跨模块） |
| quality | `pre-commit run --all-files`; `python -m mypy louke` |
| unit | `python -m pytest -q tests/unit --cov=louke --cov-report=xml --cov-fail-under=95` |
| discovery manifest | Devon新增`tests/runner-manifest.toml`，schema v1：每个`[[target]]`必含`id`, `command="integration|e2e|real-smoke"`, `profile`, `paths`, `runtimes`, `required_ac_ids`；必须声明`integration/v014→tests/integration/v014_workflow_reflow, runtimes=["host"]`、`e2e/v014→tests/e2e/v014_workflow_reflow, runtimes=["local","global"]`、`real-smoke/v014→tests/e2e/v014_workflow_reflow/real, runtimes=["local"]`。real target的`required_ac_ids`精确为`[AC-FR1700-03,AC-FR1800-02,AC-FR1900-01,AC-NFR0200-01,AC-NFR0200-02,AC-NFR0300-01,AC-NFR0300-03]`；`e2e --profile all`展开全部非real target |
| collection gate | 修改现有`tests/e2e/run_e2e.py`读取manifest，逐target/runtime执行pytest collect-only与run并输出`runner-report.json:{source_sha,command,requested_profiles,targets:[{id,runtime,collected,executed,skipped,xfail,required_ac_ids,observed_ac_ids,result,evidence_path?}]}`；path/profile/runtime零收集、required AC不在collected/executed或real report、skip/xfail、漏target、报告不确定均exit非0 |
| integration | `tests/e2e/run-project-venv integration`；必须实际收集manifest的v014 integration target及project.toml声明范围，不再固定`tests/integration/install_experience` |
| e2e | `tests/e2e/run-project-venv e2e --profile all --runtime both`；必须实际收集v014 local/global及既有manifest profiles，不再固定v0.13文件 |
| real smoke | 唯一命令`tests/e2e/run-project-venv real-smoke --profile v014 --runtime local`；start=同SHA wheel clean install+disposable repo/workspace+`lk serve`，ready=Workbench/OpenCode/GitHub identity与权限，run=公开Setup→release/Foundation→六个真实OpenCode tasks→认证Human M-LOCK-1→IF-EXT-03动态24项，teardown=`delete-always`并证明Project/repo不存在。`real-smoke.json`完整schema见Architecture §9.1；零准备、private adapter/SQLite、绕gate、partial target、report/cleanup/retention proof缺失或not-run均非0 |
| trace | 本次明确要求 Devon 实现并由 CI 调用 `python tools/check_ac_traceability.py --acceptance .louke/project/specs/v0.14-001-workflow-reflow-spec/acceptance.md --tests tests`；必须输出82/82规范AC closure，否则非0；不依赖旧 `lk agent` |
| output | 每命令0=合同全部通过；非0/timeout/cancel/unknown=gate失败；JUnit/coverage/journey/trace报告不得把not-run算PASS |
| required check | `.github/workflows/louke-ci.yml`顶层`name: Louke CI`、job id/name=`required`，稳定check精确`Louke CI / required`；聚合所有mandatory jobs且`if:always()` fail-closed |
| triggers/DAG | `.github/workflows/louke-ci.yml`在PR/push/tag/manual运行；tag/manual publish DAG固定`mandatory/build/verify→Louke CI / required→real-smoke→publish`，同一run `github.sha`。real smoke必须安装该run已验证wheel；publish只发布同digest wheel及配套已验证sdist。required/real的SHA、wheel digest、完整24项/required AC、delete-always cleanup任一不等或missing/skipped/cancelled/timeout/unknown/旧SHA均fail closed |
| migration | 同一实现变更把`ci.yml` mandatory/install jobs及`release.yml` publish搬入`louke-ci.yml`后删除旧文件；禁止Actions API按workflow文件名、display name或latest run轮询，禁止旧`lk agent archer ci-scan` |
| 覆盖 | 测试计划§7；CI合同测试与workflow review |

## 10. 接口—测试闭合索引

| 接口 | 最低覆盖 |
|---|---|
| IF-COMMON-01..03 | contract + integration；timeline另有e2e |
| IF-CLI-01, IF-WEB-01, IF-API-01 | integration + e2e；硬失败进程integration |
| IF-WEB-02, IF-API-02 | integration + e2e |
| IF-WEB-03, IF-API-03, IF-EXT-01 | integration + e2e；Git关系integration |
| IF-WEB-04 | integration + e2e |
| IF-API-04..07, IF-DATA-01 | integration；write/dirty主旅程e2e |
| IF-WEB-05, IF-API-08 | integration + e2e；real smoke验证真实session |
| IF-WEB-06..08, IF-API-09..10 | integration + e2e |
| IF-WEB-09, IF-API-11 | integration + e2e |
| IF-EXT-02 | integration |
| IF-EXT-03 | integration + stand-in e2e + real smoke |
| IF-DATA-02 | integration + e2e |
| IF-REL-01 | build/integration artifact gate |
| IF-CI-01 | workflow contract + 每次CI实际执行 |
