# 最小首次设置、Project 创建引导与 Project Status — Interfaces

- **Spec ID**：`v0.14-004-workspace-onboarding-workflow-status`
- **Assertion basis**：本文件中的公开出口是 `test-plan.md` 的唯一断言依据。

## 1. 通用 HTTP、身份与错误合同

| 项目 | 合同 |
|---|---|
| Content type | JSON API成功/失败均为 `application/json`；页面为 `text/html` |
| API naming | 规范接口按产品资源使用语义化namespace（`/api/setup`、`/api/projects`、`/api/guide`、`/api/runs`、`/api/releases`）；release版本不进入URL，版本号不得形成公开合同或独立事实面 |
| Human writes | 除首次创建首用户外，需要有效authenticated session、同源请求、session-bound `X-Louke-CSRF`、`Idempotency-Key`，以及请求体中的 `expected_revision`。首次创建首用户使用`GET /setup`建立的pre-auth Setup session及其revision-bound CSRF token；成功后pre-auth session失效并旋转为authenticated session。缺少/跨session/过期token均为403且不创建用户 |
| Session cookie | pre-auth Setup session最长10分钟，authenticated session沿用7天；均为opaque、`HttpOnly`、`SameSite=Strict`、`Path=/`，HTTPS时必须`Secure`；登录、首用户成功和权限边界变化时旋转，logout/expiry后失效 |
| Revision | 非负整数；成功 mutation 后单调增加；客户端不得自行增加 |
| Error envelope | `{ "error_code": string, "message": string, "current_revision": integer|null, "recovery_url": string|null, "details": object|null }` |
| Validation | `400 VALIDATION_FAILED`；字段级非秘密 `details.fields` |
| Authentication | `401 AUTH_REQUIRED`；Setup 未完成但首用户已存在时 `recovery_url=/setup` |
| Authorization/CSRF | `403 PERMISSION_DENIED|ORIGIN_FORBIDDEN|CSRF_INVALID`；无任何 mutation |
| Setup gate | `428 SETUP_REQUIRED`；`recovery_url=/setup`；不得执行目标 handler |
| Stale/idempotency | `409 STALE_REVISION|STALE_PREVIEW|IDEMPOTENCY_CONFLICT`；返回当前 revision/readback URL；无第二副作用 |
| External uncertainty | `409 OPERATION_UNCERTAIN` 或成功 status projection中的 `state=uncertain`；依赖成功的动作不可用 |
| Not found | `404 NOT_FOUND`；不得静默解析到另一 workspace/Project/run/revision |
| Redaction | password、session bearer secret、credential/provider token、URL userinfo、完整credential output不得出现在body、header debug字段、日志、Guide message或evidence。防伪CSRF token只允许出现在绑定同一session的指定HTML/API出口，不得持久化、记录、跨session复用或进入错误/evidence |
| Untrusted text/URL | Story、Guide、diagnosis、provider output和外部identity按纯文本转义呈现，不解释其中HTML/script/command；`continue_url`、`recovery_url`、`owning_url`、`return_url`和`return_to`只允许已声明的same-origin canonical route，非法外部/协议相对/跨workspace目标为400或安全默认Projects页 |

## 2. Setup 与全局入口

### IF-WEB-01 — Setup 全局入口保护

| 分类 | Surface / Contract | 可观察结果 | modules |
|---|---|---|---|
| Web 路由 | Setup未完成时访问 `/`、`/login`、`/workbench`、`/projects*`、`/runs*`、`/docs*`、`/wiki*`、`/models` 及任一用户功能深链 | 最终 `303` 到 canonical `/setup`；响应不包含被请求功能的用户数据或可用动作 | `Setup Gate`, `Workbench Presentation`, `Compatibility Router`, `Fact Stores` |
| API gate | Setup未完成时调用 Setup allowlist以外的 `/api/**` | `428 SETUP_REQUIRED`；目标读写均未发生 | `Setup Gate`, `Setup Application`, `Fact Stores` |
| Allowlist | `/setup`、`/assets/**`、`/health`、`GET /api/setup/status`、`POST /api/setup/first-user`、`POST/GET /api/setup/model-checks/**`、用于已有首用户继续Setup的 `POST /api/auth/login` | 仅能完成/恢复Setup；不能打开Project/Run/Doc或伪造complete | `Setup Gate`, `Setup Application`, `OpenCode Adapter` |
| Gate解除 | manifest为有效v2 `complete` | 不再因Setup重定向；未认证用户去 `/login`，认证用户去 Workbench Projects | `Setup Gate`, `Project Context`, `Workbench Presentation` |

### IF-SETUP-01 — Setup projection、持久 manifest 与页面状态

| 分类 | Surface / Schema | 合同 | modules |
|---|---|---|---|
| API | `GET /api/setup/status` | `200`：`{workspace_id, revision, status: pending_user|pending_model|complete, first_user: {principal_id,name}|null, model_check: ModelCheck|null, available_actions: string[], continue_url, csrf_token}`；`csrf_token`只绑定当前pre-auth/authenticated session和revision，不写日志/manifest | `Setup Application`, `Setup Gate`, `OpenCode Adapter`, `Fact Stores`, `Workbench Presentation` |
| 文件 | `.louke/web-setup-state.json` schema v2 | `{version:2, workspace_id, revision, status, first_principal_id, model_check:{check_id,revision,state,model_id|null,diagnosis,observed_at}|null, completed_at|null}`；原子写；不得含credential或Story | `Setup Application`, `Setup Gate`, `Fact Stores` |
| 页面 | `GET /setup` | `pending_user`显示首用户表单；`pending_model`有session时显示模型检查/Retry，无session时显示首用户登录表单；`complete`不再显示首次Setup并导航登录或Projects | `Setup Gate`, `Setup Application`, `Workbench Presentation` |
| 可见状态 | `/setup` | idle/running时主要提交禁用且有进度；失败/uncertain显示对象、已知事实、影响、原因和Retry；成功显示完成并转Projects；错误不清除尚未成功提交的用户名输入 | `Setup Application`, `Workbench Presentation`, `OpenCode Adapter` |
| 迁移 | 读取旧v1 Setup | 只有存在首用户且可核对真实model-probe passed evidence时映射complete；否则保留用户并显示`pending_model`及migration reason | `Setup Application`, `Setup Gate`, `Fact Stores` |

### IF-SETUP-02 — 唯一首用户命令

| 分类 | Surface / Input | 成功/冲突出口 | modules |
|---|---|---|---|
| API | `POST /api/setup/first-user`；body `{name, credential, expected_revision}`；header `X-Louke-CSRF`、`Idempotency-Key` | 首次成功 `201`：`{principal_id,name,setup_revision,status:"pending_model",continue_url:"/setup"}`，pre-auth session旋转为authenticated session；同key/同payload `200`同identity；已有首用户或不同payload `409`；用户数量最多增加1 | `Setup Application`, `Setup Gate`, `Fact Stores`, `Workbench Presentation` |
| 恢复登录 | `POST /api/auth/login` from `/setup` | 只允许已存在首用户登录；成功返回/redirect `/setup`继续`pending_model`；不创建用户、不完成Setup | `Setup Gate`, `Setup Application`, `Fact Stores`, `Workbench Presentation` |

### IF-SETUP-03 — OpenCode 真实模型检查

| 分类 | Surface / Schema | 合同 | modules |
|---|---|---|---|
| API start/retry | `POST /api/setup/model-checks`；body `{expected_revision}`；header `Idempotency-Key` | `202`：`ModelCheck`；只在首用户已建立且Human session有效时运行；retry产生新check revision或复用同key结果 | `Setup Application`, `OpenCode Adapter`, `Fact Stores`, `Workbench Presentation` |
| API read | `GET /api/setup/model-checks/{check_id}` | `200 ModelCheck`；未知id `404` | `Setup Application`, `OpenCode Adapter`, `Fact Stores` |
| `ModelCheck` | JSON object | `{check_id, revision, state: queued|running|passed|failed|uncertain, current_model_id|null, attempted_models:[{model_id,result}], diagnosis:{object,known_facts,impact,recovery_url}|null, observed_at, deadline_at, retry_allowed, setup_revision, continue_url|null}` | `OpenCode Adapter`, `Setup Application`, `Fact Stores`, `Workbench Presentation` |
| External invocation | controlled `opencode` executable | 成功必须观察到至少一次 `opencode run --model <configured-id> "please echo hi"` exit 0；模型list/credential/executable检查本身不得产出`passed`；调用不含Story/artifact | `OpenCode Adapter`, `Setup Application` |
| 完成交接 | `ModelCheck.state=passed`且manifest CAS成功 | readback中Setup为唯一`complete`且`continue_url=/workbench?activity=projects`；CAS失败/未知仍是`pending_model` | `OpenCode Adapter`, `Setup Application`, `Setup Gate`, `Fact Stores`, `Workbench Presentation` |

## 3. Projects、Guide 与 Environment Wizard

### IF-PROJECT-01 — Workbench Projects context

| 分类 | Surface / Schema | 合同 | modules |
|---|---|---|---|
| 页面 | `/workbench?activity=projects` | 导航中Projects为当前activity；main panel只呈现`empty|active|conflict`之一；sidebar始终有Guide | `Workbench Presentation`, `Project Context`, `Guide Session`, `Runtime Projection` |
| API | `GET /api/projects/current` | `{workspace_id, projection_revision, state:empty|active|conflict, project:ProjectIdentity|null, conflicts:[ProjectIdentity], primary_action:{kind,href,enabled,reason}|null, guide_session_id}` | `Project Context`, `Fact Stores`, `Runtime Projection`, `Guide Session`, `Workbench Presentation` |
| Empty | `state=empty` | main显示用途提示及唯一主动作`New Project`，动作enabled；不会自动启动Environment check | `Project Context`, `Workbench Presentation`, `Environment Gate` |
| Active | `state=active` | main加载该Project Status；不显示创建第二主Project的成功动作 | `Project Context`, `Runtime Projection`, `Workbench Presentation` |
| Conflict | `state=conflict` | 显示每个冲突identity与恢复位置；Project选择和`New Project`禁用；排序、recent或Guide改变不影响结果 | `Project Context`, `Fact Stores`, `Workbench Presentation`, `Guide Session` |

### IF-GUIDE-01 — context-bound Guide session与主动建议

| 分类 | Surface / Schema | 合同 | modules |
|---|---|---|---|
| API read | `GET /api/guide/session?context=empty` 或 `?project_id=<id>` | `{session_id, context:{workspace_id,project_id|null,runtime_revision|null,kind:empty|project}, messages:GuideMessage[], composer_enabled, owning_links}` | `Guide Session`, `Project Context`, `Runtime Projection`, `Environment Gate`, `Workbench Presentation`, `Fact Stores` |
| Message | `GuideMessage` | `{message_id, sequence, kind:runtime_status|guide_advice|guide_error|user|guide_reply, authority:runtime|guide|human, check_revision|null, content, impact|null, remediation|null, owning_url|null, created_at, historical}` | `Guide Session`, `Environment Gate`, `Runtime Projection`, `Fact Stores`, `Workbench Presentation` |
| Environment ordering | 同一`check_revision`阻断错误 | 第一条必须是`authority=runtime/kind=runtime_status`且包含失败step/result；随后无需用户message自动出现`guide_advice`或`guide_error`；dedupe key相同不重复 | `Environment Gate`, `Guide Session`, `Fact Stores`, `Workbench Presentation` |
| User chat | `POST /api/guide/session/{session_id}/messages` body `{content,expected_context_revision}` | 只追加对话；响应不得包含或执行install/auth/bind/create/select/return/advance能力；context stale返回409 | `Guide Session`, `Project Context`, `Runtime Projection`, `Workbench Presentation` |
| UI state | Projects sidebar | Runtime状态与Guide建议有可访问的authority标签；建议渐进出现不夺焦点/不清除composer；Guide失败时Runtime消息和Wizard链接仍可用 | `Guide Session`, `Workbench Presentation`, `Environment Gate` |

### IF-ENV-01 — 按需 Environment check

| 分类 | Surface / Schema | 合同 | modules |
|---|---|---|---|
| Start | `POST /api/projects/environment-checks` body `{expected_project_context_revision}` + idempotency | 只由empty context的`New Project`动作调用；`202 EnvironmentCheck`并打开模态Wizard；Setup或空页面静置不产生check | `Environment Gate`, `Project Context`, `GitHub/Git Adapters`, `Workbench Presentation`, `Guide Session`, `Fact Stores` |
| Read/retry | `GET /api/projects/environment-checks/{check_id}`；`POST /api/projects/environment-checks/{check_id}/retry` body `{expected_revision}` | read返回当前投影；retry基于新外部事实增加revision；stale/active Project出现则409并关闭创建路径 | `Environment Gate`, `Project Context`, `GitHub/Git Adapters`, `Fact Stores`, `Workbench Presentation`, `Guide Session` |
| `EnvironmentCheck` | JSON object | `{check_id,revision,state:running|passed|failed|uncertain,current_step,steps:EnvironmentStep[],observed_at,fresh_until,fingerprint,story_input_enabled,preview_enabled,create_enabled,guide_session_id}` | `Environment Gate`, `GitHub/Git Adapters`, `Fact Stores`, `Workbench Presentation`, `Guide Session` |
| `EnvironmentStep` | JSON object | `{id:gh_executable|gh_auth_scopes|repository_binding|canonical_main,state:pending|running|passed|failed|uncertain,observed:{host|null,identity|null,version|null,scopes:string[],repository|null,main_sha|null},missing:string[],diagnosis:{object,known_facts,impact,recovery_url}|null,actions:string[]}` | `Environment Gate`, `GitHub/Git Adapters`, `Workbench Presentation`, `Guide Session` |
| UI条件 | modal Wizard | running显示当前step；passed step折叠且无逐项确认；failed/uncertain只展开阻断step和修复/Retry；只有全部passed且仍fresh时进入Story输入 | `Environment Gate`, `Workbench Presentation`, `Guide Session` |
| Scope判定 | `gh_auth_scopes` | `gh`可执行、目标host/identity唯一，且集合同时含`gist,project,repo,workflow`才passed；缺任一项在`missing`列出且不自动安装/登录/改scope | `Environment Gate`, `GitHub/Git Adapters`, `Guide Session` |

### IF-ENV-02 — Repository binding preview/confirm/reconcile

| 分类 | Surface / Input | 成功/失败出口 | modules |
|---|---|---|---|
| Preview | `POST /api/projects/environment-checks/{check_id}/repository-preview` body `{repository_url,expected_revision}` | `200 {binding_preview_id,preview_revision,repository:{host,owner,name,display_url},workspace_id,effects,excluded_paths,side_effects:[]}`；credential/local/non-GitHub/歧义URL为400 | `Environment Gate`, `GitHub/Git Adapters`, `Fact Stores`, `Workbench Presentation` |
| Confirm | `POST /api/projects/environment-checks/{check_id}/repository-confirm` body `{binding_preview_id,expected_preview_revision,expected_check_revision}` + idempotency | `202 {operation_id,state:running|passed|blocked|conflict|uncertain,check_revision,recovery_url}`；只在Human明确动作后执行当前workspace范围内init/bind/main | `Environment Gate`, `GitHub/Git Adapters`, `Fact Stores`, `Workbench Presentation`, `Guide Session` |
| Operation read | `GET /api/projects/environment-checks/{check_id}/repository-operations/{operation_id}` | `{operation_id,state,repository_identity,local_git:{is_worktree,remote_name,main_sha},remote_main:{sha|null},effects,excluded_paths,diagnosis,reconcile_required,observed_at}` | `Environment Gate`, `GitHub/Git Adapters`, `Fact Stores`, `Workbench Presentation` |
| Safety result | operation evidence/readback | 空remote成功后存在可fetch的`refs/heads/main`；不stage/commit secret、`.louke`运行状态或unowned文件；已有不同remote、非空remote缺main、歧义/diverged/force需求、未知结果均不passed | `Environment Gate`, `GitHub/Git Adapters`, `Fact Stores` |

## 4. Draft、Preview、Create 与对象身份

### IF-DRAFT-01 — 浏览器本地 New Project draft

| 分类 | Surface / Schema | 合同 | modules |
|---|---|---|---|
| Browser storage | key `louke.new-project.v1:<workspace_id>:<principal_id>` | `{version:1,story,release_version,resume_step:input|preview,saved_at}`；不得含credential/token/repository URL/preview token/Project identity | `Workbench Presentation`, `Environment Gate`, `Release Entry` |
| Visible state | Story/version form | `Saving…|Saved in this browser|Draft not saved`；刷新/关闭后同浏览器恢复输入和意图位置；恢复后先重验Environment，preview需重新生成 | `Workbench Presentation`, `Environment Gate`, `Release Entry` |
| Lifecycle | Cancel/success | Cancel和普通中断保留；只有最新canonical Story在Dev Docs成功加载后清除；其他浏览器/清storage可为空 | `Workbench Presentation`, `Document Surface`, `Release Entry` |

### IF-PREVIEW-01 — Project Preview与planned release identity

| 分类 | Surface / Input | 成功/失败出口 | modules |
|---|---|---|---|
| Canonical API | `POST /api/projects/preview` body `{story,release_version,environment_check_id,environment_revision}` | `200 ProjectPreview`；既有语义alias `POST /api/releases/preview`返回同对象 | `Release Entry`, `Environment Gate`, `Project Context`, `Fact Stores`, `Workbench Presentation` |
| `ProjectPreview` | JSON object | `{preview_id,preview_revision,request_id,request_digest,story,release:{input,canonical,tag,branch},workspace:{workspace_id},repository:{host,owner,name,main_sha},environment:{check_id,revision,fingerprint,fresh_until},side_effects:[],actions:{create,cancel}}` | `Release Entry`, `Environment Gate`, `GitHub/Git Adapters`, `Fact Stores`, `Workbench Presentation` |
| Version | Preview字段 | PEP440 canonical；单个前导`v`可接受；一段/两段release tuple补齐到三段；local/dirty/非法ref不接受；例如`0.14 -> canonical 0.14.0/tag v0.14.0/branch releases/0.14.0` | `Release Entry`, `Foundation/Scribe`, `Workbench Presentation` |
| UI | Preview surface | 同时可见Story、canonical version、workspace/repository identity、Create和Cancel；Create仅在preview/current readiness都fresh且Human有权限时enabled | `Workbench Presentation`, `Release Entry`, `Environment Gate` |
| Stale/Cancel | readiness/input变化或Cancel | 旧preview Confirm为`409 STALE_PREVIEW`；Cancel返回empty Project且不创建正式资源，draft保留 | `Release Entry`, `Environment Gate`, `Project Context`, `Workbench Presentation`, `Fact Stores` |

### IF-CREATE-01 — Confirm、Foundation/Scribe status与恢复

| 分类 | Surface / Input | 合同 | modules |
|---|---|---|---|
| Confirm | `POST /api/projects/confirm` body `{preview_id,expected_preview_revision,request_digest,environment_check_id,expected_environment_revision}` + idempotency | authenticated Human only；`202 ProjectCreation`；既有语义alias `/api/releases/confirm`相同 | `Release Entry`, `Environment Gate`, `Project Context`, `Foundation/Scribe`, `Fact Stores`, `Workbench Presentation` |
| Status/retry | `GET /api/projects/requests/{request_id}`；`POST /api/projects/requests/{request_id}/retry` body `{expected_revision}` | `ProjectCreation` readback；retry先reconcile；existing release aliases解析同request | `Release Entry`, `Foundation/Scribe`, `Project Context`, `Runtime Projection`, `Document Surface`, `Fact Stores`, `Workbench Presentation` |
| `ProjectCreation` | JSON object | `{request_id,revision,state:foundation|scribe|ready|blocked|conflict|uncertain,project:ProjectIdentity|null,foundation:{operations,resources,diagnosis}|null,story:{path,revision,digest,commit_sha}|null,run:{run_id,current_step,runtime_revision}|null,primary_action,continue_url}` | `Release Entry`, `Foundation/Scribe`, `Runtime Projection`, `Document Surface`, `Fact Stores`, `Workbench Presentation` |
| Success | `state=ready` | 一组稳定identity，run进入同Project `M-STORY`，Story持久readback成功；`continue_url`打开该Project最新Story的Dev Docs | `Release Entry`, `Foundation/Scribe`, `Runtime Projection`, `Document Surface`, `Fact Stores`, `Workbench Presentation` |
| Partial/duplicate | repeated/concurrent/restart | 同request digest/idempotency只出现一个Project/Run/Story/resource set；partial/unknown显示同Project recovery，不跳错误Doc、不覆盖冲突Story | `Release Entry`, `Foundation/Scribe`, `Project Context`, `Fact Stores`, `Workbench Presentation` |

### IF-IDENTITY-01 — Project identity chain

| 分类 | Schema / Outlet | 合同 | modules |
|---|---|---|---|
| `ProjectIdentity` | 所有Project相关API/页面 | `{workspace_id,project_id,request_id,planned_release:{canonical,tag,branch},github_project:{node_id,url}|null,run_id,spec_id,story:{path,revision,digest}|null,activity_state:active|historical|migration_required,identity_revision}` | `Project Context`, `Release Entry`, `Foundation/Scribe`, `Runtime Projection`, `Document Surface`, `Compatibility Router`, `Fact Stores` |
| Identity invariant | Project/Guide/Status/Docs/aliases | 同一工作每个surface的上述非空字段相等；新写入只有一份可写binding；映射不安全时`migration_required`且只读 | `Project Context`, `Guide Session`, `Runtime Projection`, `Document Surface`, `Compatibility Router`, `Fact Stores` |

## 5. Project Status、节点详情与回拨

### IF-STATUS-01 — Project Status read model与可见状态

| 分类 | Surface / Schema | 合同 | modules |
|---|---|---|---|
| API | `GET /api/projects/{project_id}/status`；支持`If-None-Match` | `200 ProjectStatus`、未变`304`；错误不解析到其他Project | `Runtime Projection`, `Project Context`, `Fact Stores`, `Workbench Presentation`, `Guide Session` |
| `ProjectStatus` | JSON object | `{project:ProjectIdentity,projection_revision,run_revision,observed_at,fresh_until,canonical_state,active:ActiveNode,stage_catalog:Stage[],timeline:TimelineNode[],return_edges:ReturnEdge[],recent_evidence:Evidence[],recent_error:null|Diagnostic,primary_action:null|Action,owning_url}` | `Runtime Projection`, `Project Context`, `Fact Stores`, `Workbench Presentation`, `Guide Session` |
| Stage | `stage_catalog` | canonical顺序恰为`M-START,M-STORY,M-SPEC,M-ACC,M-REQ-APPROVAL,M-DESIGN,M-IMPL,M-TEST,M-VERIFY,M-SECURITY,M-RELEASE,M-PUBLISH,M-MILESTONE`；历史`M-LOCK-1`只以`source_alias`附着批准节点 | `Runtime Projection`, `Fact Stores`, `Workbench Presentation` |
| Active | `ActiveNode` | `{attempt_id,canonical_step_id,source_alias|null,status,display_state:active|attention,owner,attempt_ordinal,started_at,observed_at,elapsed_seconds,reason|null,impact|null,artifact|null,operation|null,evidence|null,error|null,owning_url}` | `Runtime Projection`, `Fact Stores`, `Workbench Presentation`, `Guide Session` |
| Timeline | `TimelineNode` | `{node_kind:attempt|pending_placeholder,attempt_id|null,canonical_step_id,source_alias|null,sequence,attempt_ordinal|null,status,display_state:completed|active|pending|attention|invalidated,started_at|null,ended_at|null,selected,active,viewable}`；实际attempt不折叠 | `Runtime Projection`, `Fact Stores`, `Workbench Presentation` |
| Return edge | `ReturnEdge` | `{edge_id,source_attempt_id,target_attempt_id,occurred_at,reason,status}`；来源/目标/方向可见 | `Runtime Projection`, `Return Application`, `Fact Stores`, `Workbench Presentation` |
| UI freshness | main panel | active居中且邻近前后各至少3节点；全部历史键盘/滚动可达；5秒刷新，失败或超过`fresh_until`显示stale并禁用mutation；重连readback后提示revision变化 | `Runtime Projection`, `Workbench Presentation`, `Guide Session` |
| Read-only/permission | status surface | historical/migration/无权限时信息可见但mutation隐藏或disabled并显示原因；状态不只用颜色 | `Runtime Projection`, `Project Context`, `Workbench Presentation` |

### IF-ATTEMPT-01 — 选中 attempt详情与返回上下文

| 分类 | Surface / Schema | 合同 | modules |
|---|---|---|---|
| API | `GET /api/projects/{project_id}/status/attempts/{attempt_id}` | `{project_id,run_revision,selected_attempt_id,active_attempt_id,canonical_step_id,source_alias,status,owner,started_at,ended_at,artifact,evidence,error,transition_reason,return_eligibility:{allowed,reason,preview_url|null},actions:Action[],owning_url,return_url}` | `Runtime Projection`, `Return Application`, `Document Surface`, `Fact Stores`, `Workbench Presentation` |
| Selection | timeline node click/keyboard | URL含`selected_attempt=<id>`；只改变查看上下文，不改变run revision/active pointer；详情明确selected与active | `Workbench Presentation`, `Runtime Projection` |
| Navigation | `owning_url`/`return_url` | artifact/operation存在时进入绑定surface，返回同Project+attempt；missing/stale/forbidden显示404/409/403及恢复位置 | `Document Surface`, `Runtime Projection`, `Compatibility Router`, `Workbench Presentation` |

### IF-RETURN-01 — 回拨 Preview/Confirm

| 分类 | Surface / Schema | 合同 | modules |
|---|---|---|---|
| Eligibility | IF-STATUS-01/IF-ATTEMPT-01 | 只有Runtime当前允许的历史attempt有`allowed=true`和Preview action；pending/active/stale/unsupported无可执行动作 | `Runtime Projection`, `Return Application`, `Fact Stores`, `Workbench Presentation` |
| Preview | `POST /api/projects/{project_id}/returns/preview` body `{target_attempt_id,expected_run_revision}` | `200 {return_preview_id,preview_revision,source_attempt,target_attempt,invalidated_artifacts,invalidated_reviews,invalidated_evidence,external_consequences,side_effects:[],confirm_enabled}` | `Return Application`, `Runtime Projection`, `Fact Stores`, `Workbench Presentation` |
| Confirm | `POST /api/projects/{project_id}/returns/confirm` body `{return_preview_id,expected_preview_revision,expected_run_revision}` + idempotency | Human+CSRF；`202 {operation_id,state,project_id,run_revision,status_url}`；复核失败409且无状态改变 | `Return Application`, `Runtime Projection`, `Fact Stores`, `Workbench Presentation` |
| Status | `GET /api/projects/{project_id}/returns/{operation_id}` | `{state:running|completed|conflict|uncertain,source_attempt,target_attempt,new_active_attempt|null,return_edge|null,downstream_results,diagnosis,continue_url}` | `Return Application`, `Runtime Projection`, `Fact Stores`, `Workbench Presentation` |
| Cancel | confirmation UI `Cancel` | 不调用Confirm、不改run revision；关闭确认后保持同selected attempt | `Workbench Presentation`, `Return Application` |

## 6. Dev Docs、兼容入口、日志与运行合同

### IF-DOC-01 — canonical Story与Dev Docs结果

| 分类 | Surface / Schema | 合同 | modules |
|---|---|---|---|
| Artifact API | `GET /api/runs/{run_id}/artifacts/story` | `{project_id,run_id,spec_id,path,revision,digest,commit_sha,status,content_url}`；只返回绑定latest或明确请求revision | `Document Surface`, `Foundation/Scribe`, `Runtime Projection`, `Fact Stores` |
| Dev Docs | `/workbench?activity=dev-docs&project=<id>&document=story&revision=<rev>&return_to=<encoded>` | 加载该Project canonical `story.md`，可见Project/revision；Story安全转义/渲染，不能注入script；加载成功才清browser draft；`return_to`只接受同Project canonical route并保持Project Status/selected attempt | `Document Surface`, `Workbench Presentation`, `Project Context`, `Runtime Projection` |
| Failure | missing/stale/forbidden | 显示目标identity、原因和返回同Project的URL；不得打开其他Spec/最新任意Story | `Document Surface`, `Compatibility Router`, `Workbench Presentation` |

### IF-COMPAT-01 — 兼容路由解析

| 入口 | Canonical结果 | modules |
|---|---|---|
| `/`、登录成功、`/workbench` | Setup gate通过后 `/workbench?activity=projects` | `Compatibility Router`, `Setup Gate`, `Project Context`, `Workbench Presentation` |
| `/projects` | Projects activity的empty/active/conflict | `Compatibility Router`, `Project Context`, `Workbench Presentation` |
| `/projects/new` | empty时打开同一Environment Wizard；active/conflict时显示对应status/conflict且不创建第二对象 | `Compatibility Router`, `Project Context`, `Environment Gate`, `Workbench Presentation` |
| `/projects/{project_id}` | 同一Project Status | `Compatibility Router`, `Project Context`, `Runtime Projection`, `Workbench Presentation` |
| `/runs/{run_id}` | 有Project binding时同一Project Status；无安全映射时历史只读或migration required | `Compatibility Router`, `Project Context`, `Runtime Projection`, `Workbench Presentation` |
| `/projects/{project_id}/requirements/story`、旧Story深链 | 同一IF-DOC-01 Story/Dev Docs | `Compatibility Router`, `Document Surface`, `Project Context`, `Workbench Presentation` |

### IF-AUDIT-01 — 结构化 operation/audit evidence

| 分类 | Schema / Outlet | 合同 | modules |
|---|---|---|---|
| Event | Runtime SQLite event/公开status evidence及`.louke/project/.serve-activity.jsonl`适用记录 | `{event_id,correlation_id,workspace_id,project_id|null,run_id|null,step_id|null,attempt_id|null,operation_id|null,kind,actor:{kind,id},expected_revision,result,status,error_code|null,at,input_digest|null,output_digest|null}` | `Setup Application`, `Environment Gate`, `Release Entry`, `Foundation/Scribe`, `Return Application`, `Fact Stores` |
| Security | 所有evidence/log/readback | secret字段缺失或redacted；不得记录Guide正文为Runtime evidence，不得记录provider/session transport metadata为workflow事实 | `Fact Stores`, `Guide Session`, `Runtime Projection`, `GitHub/Git Adapters`, `OpenCode Adapter` |
| Uncertain recovery | operation evidence | 保留已知external identity/result、`status=uncertain`和reconcile URL；不写`passed/completed`直到readback确认 | `Environment Gate`, `Release Entry`, `Foundation/Scribe`, `Return Application`, `Fact Stores` |

### IF-REL-01 — 宿主 Python release adapter与版本 evidence

| 命令 | 输入 | stdout/evidence/退出语义 | modules |
|---|---|---|---|
| `python tools/louke_python_release_adapter.py prepare --tag TAG --source pyproject.toml --planned-source .louke/project/project.toml --evidence PATH` | tag `v<PEP440>`；planned `[project].version`；package source | stdout JSON `{tag,canonical,planned_version,package_version,write,evidence}`；原子准备后才0；缺失/非法/不匹配/写入未知非0 | `Release Entry`, `Foundation/Scribe`, `Fact Stores` |
| `... verify-dist --source pyproject.toml --planned-source ... --tag TAG --dist dist --evidence PATH` | prepared source、planned source、恰好1 wheel+1 sdist | JSON列每个绝对path/version/SHA256和总canonical；全部精确匹配才0 | `Foundation/Scribe`, `Fact Stores` |
| `... verify-installed --expected VERSION --wheel PATH --sdist PATH --evidence PATH` | verified artifacts | 分别从wheel、sdist-built-wheel clean venv取得`lk --version`和metadata；全部等于expected才0 | `Foundation/Scribe`, `Fact Stores` |
| Public version | installed `lk --version`、`importlib.metadata.version("louke")` | 两者均含/返回artifact canonical version；branch/tag不能替代此证据 | `Workbench Presentation`, `Fact Stores` |

### IF-TEST-01 — Project-local integration/e2e runner

| Layer | 命令与资产 | 退出/evidence | modules |
|---|---|---|---|
| Integration | `tests/e2e/run-project-venv integration`；`tests/integration/v014_workspace_onboarding`、`tests/fixtures/v014_workspace_onboarding` | 0=收集非零且全部通过；非零/零收集失败；输出JUnit/AC-layer/adapter evidence | `Workbench Presentation`, `Setup Application`, `Environment Gate`, `Release Entry`, `Runtime Projection`, `Guide Session`, `Fact Stores` |
| E2E | `tests/e2e/run-project-venv e2e --profile all --runtime both`；`tests/e2e/v014_workspace_onboarding` | 0=local/global安装态真实Chromium旅程通过；输出runner identity、service lifecycle、AC layers；失败trace/screenshot/log | `Workbench Presentation`, `Setup Gate`, `Project Context`, `Document Surface`, `Runtime Projection` |

### IF-CI-01 — GitHub Actions稳定门禁

| Gate | 命令/依赖 | 可观察证据与失败语义 | modules |
|---|---|---|---|
| `quality` | constraints安装；`pre-commit run --all-files` | hook输出；任一失败阻断 | `Fact Stores` |
| `ac-trace` | `tools/check_ac_traceability.py`，本Spec `--expected-count 44` | AC closure报告；缺失/未知/数量不符失败 | `Fact Stores` |
| `build-artifacts` / `artifact-verify` | IF-REL-01 + `python -m build --wheel --sdist` | source/planned/tag/artifact/install evidence；不确定非成功 | `Foundation/Scribe`, `Fact Stores` |
| `unit` | pytest unit + runtime coverage `>=95%` | matrix/JUnit/coverage | `Fact Stores` |
| `integration` / `e2e-standin` | IF-TEST-01 | JUnit、runner evidence、失败browser artifacts | `Workbench Presentation`, `Setup Application`, `Environment Gate`, `Runtime Projection`, `Fact Stores` |
| `install-matrix` | existing `install.sh`/`install.ps1` from verified wheel | OS/Python/local/global public version evidence | `Workbench Presentation`, `Fact Stores` |
| Required check | workflow `Louke CI`，job `required`，check `Louke CI / required` | `if:always()`检查所有mandatory needs严格为success；failed/cancelled/timed_out/skipped/missing/unknown均失败 | `Fact Stores` |
| Release | protected `real-smoke`后`publish` | 只发布同source SHA和artifact digest的verified wheel/sdist；required/smoke/identity任一不current则阻断 | `Foundation/Scribe`, `Fact Stores` |

## 7. 交互状态总表

| Surface | 进行中 | 成功 | 失败/空 | dirty/stale/conflict/permission/reconnect | 可用动作 |
|---|---|---|---|---|---|
| `/setup` | model check进度，提交禁用 | complete后Projects | 首用户表单或可定位model失败 | 未提交输入保留；manifest冲突显示current revision；重启从首用户或model位置恢复 | Create first user、Retry、已有用户Continue |
| Projects empty | 无自动检查 | N/A | 用途提示+New Project | 多active为conflict；无权限只读且按钮禁用 | New Project |
| Environment Wizard | 当前check step；取消可达 | 全部passed直接输入Story/version | 仅展开失败/uncertain step | freshness过期回检查；Guide更新不夺焦点；权限失败不自动修复 | Retry、repository Preview/Confirm、Cancel |
| Story/version | browser save状态 | Preview | 空字段字段级错误 | draft write失败可见；恢复先recheck；输入不因Guide更新丢失 | Preview、Cancel |
| Preview | Create pending去重 | creation status/Dev Docs | validation/Foundation恢复 | old preview/readiness为stale；权限不足禁用Create | Create、Cancel、Re-preview |
| Project creation | foundation/scribe当前operation | Dev Docs latest Story | blocked/conflict/uncertain同Project恢复 | 重连readback同request；并发Confirm无第二identity | Retry/Reconcile、Open owning surface |
| Project Status | running card/elapsed | current revision | empty evidence显示Unavailable，不推测 | 断连/超时stale禁 mutation；历史只读；revision冲突自动readback | Runtime唯一primary action、节点选择 |
| Attempt detail | N/A | 绑定artifact/action | missing/stale/forbidden可定位 | selected与active明确；返回保留上下文 | Open artifact、Return preview（仅allowed）、Close/Back |
| Return confirm | Confirm pending禁重复 | 新active pointer+return edge | conflict/uncertain显示继续位置 | old target/revision禁用；Cancel无副作用；重连readbackoperation | Confirm、Cancel、Refresh |
| Guide | 建议可渐进出现 | context-bound reply | Guide error不遮Runtime结果 | runtime/advice authority可辨；draft/composer/focus保留；历史消息标识 | Send、owning surface links；无正式workflow action |
