# v0.14-004 Workspace Onboarding 与 Workflow Status 接口合同

## 1. 通用 HTTP 合同

| 项目 | 合同 |
|---|---|
| Media type | JSON API 使用 `application/json; charset=utf-8`；页面使用 `text/html; charset=utf-8` |
| 认证 | 首用户创建与 Login surface 外，其余接口要求现有 authenticated session；未认证 JSON 返回 `401`，页面进入 Login 并保留安全的 `next` |
| 写请求 | 必须带 `Idempotency-Key`；已有 projection 的命令还必须带 body `expected_revision` |
| 成功 | 读 `200`；创建 `201`；无 body 操作 `204` |
| 错误 | `{"error":{"code":string,"message":string,"field":string|null,"retryable":bool,"current_revision":string|null}}` |
| 冲突 | stale revision、同 key 异 payload、文件树变化均返回 `409`；不得伪报成功 |
| 秘密 | response、URL、日志和 evidence 不返回 password、token、URL userinfo、credential-helper 输出或 provider session metadata |
| 时间 | RFC 3339 UTC；所有列表顺序稳定 |

公开错误码封闭集合：`validation_error`、`authentication_required`、`permission_denied`、`not_found`、`stale_revision`、`idempotency_conflict`、`setup_blocked`、`repository_conflict`、`dependency_unavailable`、`action_not_allowed`、`operation_uncertain`、`service_unavailable`、`internal_error`。未知内部异常映射为 `internal_error`，不返回 stack trace。

## 2. 接口目录

| ID | 分类/接口 | modules | 跨模块 | 验收锚点 |
|---|---|---|---|---|
| IF-01 | Workbench shell 与稳定导航 | `Workbench Presentation`, `Entry Resolver` | 是 | FR-0101、FR-1001、FR-1201、FR-1301、FR-1601 |
| IF-02 | 首用户与 Login | `Workbench Presentation`, `Workspace Fact Store` | 是 | FR-0201、FR-0801 |
| IF-03 | `GET /api/workbench/entry` | `Entry Resolver`, `Workspace Fact Store`, `Runtime Projection`, `Release Entry` | 是 | FR-0101、FR-0801、FR-0901 |
| IF-04 | `GET /api/setup/workspace` | `Setup Application`, `Workspace Fact Store`, `Workbench Presentation` | 是 | FR-0301、FR-0701、FR-1501 |
| IF-05 | Repository selection/Preview/Confirm | `Setup Application`, `Repository Adapter`, `Workspace Fact Store`, `Workbench Presentation` | 是 | FR-0401、FR-0501、NFR-0101、NFR-0501 |
| IF-06 | Dependency Recheck | `Setup Application`, `Dependency Adapter`, `Workspace Fact Store`, `Workbench Presentation` | 是 | FR-0601、NFR-0401 |
| IF-07 | Setup Review/Apply/Reconcile | `Setup Application`, `Repository Adapter`, `Dependency Adapter`, `Workspace Fact Store`, `Workbench Presentation` | 是 | FR-0701、FR-1501、NFR-0501 |
| IF-08 | `GET /api/workbench/status` | `Runtime Projection`, `Workspace Fact Store`, `Release Entry`, `Workbench Presentation` | 是 | FR-1101、FR-1201、FR-1501 |
| IF-09 | Guide projection 与偏好 | `Guide Application`, `Runtime Projection`, `Workspace Fact Store`, `Workbench Presentation` | 是 | FR-1301、FR-1401、NFR-0201、NFR-0301 |
| IF-10 | Owning-surface Runtime action | `Runtime Projection`, `Workbench Presentation` | 是 | FR-1101、FR-1401、FR-1501、NFR-0101 |
| IF-11 | Start Story 与 Release/Story 深链 | `Release Entry`, `Runtime Projection`, `Workbench Presentation` | 是 | FR-0901、FR-1001、FR-1601 |
| IF-12 | 结构化操作 evidence | `Setup Application`, `Runtime Projection`, `External Adapters`, `Workspace Fact Store` | 是 | NFR-0101、NFR-0401、NFR-0501 |
| IF-13 | 可访问与响应式交互出口 | `Workbench Presentation`, `Guide Application` | 是 | NFR-0201、NFR-0301 |
| IF-14 | 兼容 URL/API | `Workbench Presentation`, `Entry Resolver`, `Release Entry` | 是 | FR-1601、NFR-0601 |
| IF-15 | CI gates 与 evidence | `Workbench Presentation`, `Setup Application`, `Runtime Projection`, `Guide Application`, `Release Entry` | 是 | 全部 AC |

`modules` 来自 `architecture.md`。以上接口全部跨越至少两个模块，Shield 必须提供 integration 覆盖；面向用户的主旅程另需 e2e。

## 3. IF-01 — Workbench shell 与导航

| Surface/context | 用户动作 | 可见结果与可用条件 | 状态/恢复 |
|---|---|---|---|
| `GET /` | 打开产品 | 返回统一 Workbench shell；按 IF-03 进入 Identity、Login、Setup、Current Work、Released 或 Ready/Empty | entry 请求 loading 时显示明确 loading；失败显示 Retry，不显示错误落点 |
| Sidebar | 选择 Project、Story、Run | URL 与主内容同步；active item 有 `aria-current="page"` | 无权限 item 不显示；暂不可用 item 为 disabled 并给原因 |
| 任意 Workbench context | 刷新、前进、后退、复制深链 | 保持同一 Project/Story/Run context；不存在返回可定位 not-found 和回到 Project | 断线保留只读内容并标 stale；重连 readback |

稳定页面 URL：`/projects/{project_id}`、`/projects/{project_id}/stories/{story_id}`、`/projects/{project_id}/runs/{run_id}`。标识符必须 URL encode；非法或跨 workspace identity 返回 `404`，不泄露资源存在性。

## 4. IF-02 — 首用户与 Login

| 接口/surface | 输入 | 成功输出 | 失败/可见语义 |
|---|---|---|---|
| `GET /api/setup/status`（继承） | 无 | `{"initialized":bool,"first_principal_id":string|null}` | 只暴露首次 Setup 必需事实 |
| `POST /api/setup/first-user`（继承） | `{"name":string,"credential":string}` | `201 {"principal_id":string,"name":string,"continue_url":"/login?next=/"}` | 字段错误定位；已有用户 `409`；credential 永不回显 |
| `POST /api/auth/login`（继承） | 现有 username/credential payload 与安全 `next` | authenticated session；`{"continue_url":"/"}` | 错误不区分用户不存在/密码错误；保留 name，不保留 credential |
| Identity/Login surface | 输入并提交、重试 | Identity 成功后明确要求 Login；Login 成功进入 IF-03 解析结果 | pending 禁止重复提交；失败聚焦错误摘要并关联字段；可键盘完成 |

## 5. IF-03 — EntryProjection

`GET /api/workbench/entry` 返回：

```json
{
  "revision": "entry_opaque",
  "destination": "setup|current_work|released|ready_empty",
  "url": "/setup?step=repository",
  "reason": "setup_incomplete|active_work|latest_released|no_current_work",
  "project_id": null,
  "release_id": null,
  "story_id": null,
  "run_id": null,
  "setup_step": "repository",
  "read_only": false
}
```

| 条件（优先级从高到低） | destination/url |
|---|---|
| Setup manifest 未完成 | `setup`，指向其当前/首个未完成 step |
| active project 且存在 current work | `current_work`，稳定 Story 或 Run 深链 |
| 无 current work 且有 released item | `released`，稳定 Project/Story 深链 |
| Setup complete 且以上均无 | `ready_empty`，Project 驾驶舱 |

缺失/矛盾事实返回 `503 service_unavailable`，不得猜测 destination。GET 无副作用。

## 6. IF-04 — SetupProjection

`GET /api/setup/workspace` 返回：

```json
{
  "schema_version": "1",
  "revision": "setup_opaque",
  "workspace_id": "workspace_opaque",
  "status": "in_progress|blocked|applying|complete|attention",
  "current_step": "identity|repository|dependencies|review|applying|complete",
  "steps": [{"id":"repository","state":"completed|current|pending|attention"}],
  "repository": {"mode":null,"workspace_identity":"...","repository_identity":null,"display_remote":null,"default_branch":null,"binding_fields":[],"state":"pending","preview":null},
  "dependencies": [{"id":"louke_store","required":true,"state":"ready|missing|error","version":null,"message":"..."}],
  "operations": [{"id":"opaque","kind":"repository_init","state":"pending|applying|completed|failed|conflict|uncertain","evidence_id":null}],
  "blocking_items": [],
  "allowed_actions": ["select_repository"],
  "updated_at": "2026-07-23T00:00:00Z"
}
```

`preview` 为 `{preview_id,digest,summary[],conflicts[],expires_at}`。`binding_fields` 的每项为 `{name,required,candidates:[{value,provenance:{source,evidence}}],selected,status:"pending|conflict|done|failed|uncertain"}`，必须覆盖 owner/provider namespace、declared remote、权威默认分支及适用 identity；零/多候选不自动选中。依赖项封闭 ID 为 `louke_store`、`catalog`、`opencode`、`provider_auth`、`model`、`namespace_capability`；Git repository 自身检查属于 repository projection。`summary` 只能描述将创建/绑定/保留的事实；Preview 期间 `workspace_config_modification_count` 与 `release_resource_creation_count` 均为 `0`。complete projection 提供 `continue_url`，不得创建 release/Story 作为探测副作用。

## 7. IF-05 — Repository commands

| Endpoint | Body | 成功 | 错误与用户反馈 |
|---|---|---|---|
| `PUT /api/setup/repository/selection` | `{"expected_revision":string,"mode":"init|clone","remote_url":string|null}` | `200 SetupProjection`，step 保持 repository 并启用 Preview | clone 缺 URL/非法 scheme/userinfo/控制字符为 `422 validation_error`；字段内可见 |
| `POST /api/setup/repository/preview` | `{"expected_revision":string}` | `200 SetupProjection`，含 preview id/digest、目标、保留项、冲突；无写副作用 | remote 不可达为 retryable error；秘密必须脱敏 |
| `POST /api/setup/repository/confirm` | `{"expected_revision":string,"preview_id":string,"preview_digest":string}` | `200 SetupProjection`；完成后进入 dependencies；响应含 `repository_result:{mode,head,display_remote|null,outcome:"applied|already_applied"}` | preview/树已变 `409 stale_revision|repository_conflict`；不覆盖，显示 Re-preview/Reconcile |

Confirm 在 pending 时控件 disabled 且显示进度；重复同 key 同 payload返回同一 outcome/revision。取消 Preview 回到 selection，不修改 workspace。

## 8. IF-06 — Dependency commands

`POST /api/setup/dependencies/recheck` body：

```json
{"expected_revision":"setup_opaque","dependency_ids":["python","git","github_cli","opencode"]}
```

返回 `200 SetupProjection`。每项保留独立 `ready|missing|error`、非秘密版本、message 与 retryable；空列表表示检查全部。只在 required 项全 `ready` 时启用 Continue/Review。检查中只禁用相同项的重复 Recheck；用户仍可查看其他结果和返回 Repository。timeout 显示 error，不把旧 ready 冒充本轮结果。

## 9. IF-07 — Review、Apply 与 Reconcile

| Endpoint | Body | 成功输出 | 失败语义 |
|---|---|---|---|
| `POST /api/setup/apply` | `{"expected_revision":string,"confirmed_preview_digest":string}` | `200 SetupProjection`；依次可见 applying，readback 后 complete；`continue_url` 为 Project 驾驶舱 | 仅 review 且无 blocker 时允许；失败返回未完成项、已完成项和 Reconcile，不声称 complete |
| `POST /api/setup/reconcile` | `{"expected_revision":string,"operation_id":string}` | `200 SetupProjection`，每项 outcome 为 `completed|rolled_back|needs_human` | 不确定返回 `operation_uncertain` 与安全说明，不覆盖/删除用户文件 |

Review surface 必须列 Identity、Repository、dependencies、将修改的 workspace facts 和“Setup 不创建 release/Story”。Back 保留输入；Apply pending 禁止离开危险步骤或弹出明确确认。Complete 显示 Start Story 与 Project 导航。

## 10. IF-08 — WorkflowStatusProjection

`GET /api/workbench/status?project_id={id}&story_id={id?}&run_id={id?}` 返回：

```json
{
  "revision": "status_opaque",
  "context": {"project_id":"...","release_id":"...","story_id":"...","run_id":null},
  "phases": [{"id":"M-STORY","label":"Story","state":"completed|current|pending|attention"}],
  "current_phase": "M-DESIGN",
  "canonical_state": "waiting_author",
  "responsible_party": {"kind":"human|agent|runtime","label":"Archer"},
  "artifact": {"path":"...","revision":"...","digest":"..."},
  "evidence": [{"id":"...","kind":"...","identity":"...","result":"..."}],
  "last_transition": {"from":"...","to":"...","at":"...","evidence_id":"..."},
  "last_error": {"code":"...","message":"...","at":"..."},
  "required_action": {"label":"...","action_id":"..."},
  "allowed_actions": [{"id":"opaque","label":"...","kind":"navigate|dispatch|preview","danger":"none|confirm","href":null}],
  "freshness": {"observed_at":"...","stale":false}
}
```

| 状态 | Presentation 合同 |
|---|---|
| loading | 显示 skeleton/status label；mutating actions disabled |
| fresh | phases、canonical state、责任方、artifact/revision、evidence、last error、required action 可访问名称完整 |
| empty/not applicable | 显式 `None/Not applicable`，不省略造成歧义 |
| stale/disconnected | 显示 stale 与最后更新时间；mutation disabled；提供 Retry，保留只读导航 |
| attention/error | 对应 phase 为 attention；错误与 required action 相邻，不用百分比 |
| permission denied | 显示只读原因；无权限 mutation 隐藏或 disabled，不可调用成功 |

## 11. IF-09 — GuideProjection 与偏好

| Endpoint | 输入/输出 |
|---|---|
| `GET /api/workbench/guide?...same context...` | `200 {revision,status_revision,context,summary,current_phase,canonical_state,responsible_party,next_step,blockers[],links[],preference:{collapsed:bool,divider_ratio:number},freshness}`；`links` 只能导航到 owning surface，不含 dispatch token |
| `PUT /api/workbench/guide/preference` | body `{"collapsed":bool?,"divider_ratio":number?,"reset":bool?}`；`200 {"collapsed":bool,"divider_ratio":number}`，按 authenticated user 持久化；ratio 范围 `0.20..0.50`，默认 `0.3333`，`reset:true` 恢复默认 |
| `GET /api/workbench/guide/messages?context_id=...` | `200 {session_id,context,status_revision,items:[GuideMessage]}`；旧 context 的 item 明示 `historical:true`，不能标为当前事实 |
| `POST /api/workbench/guide/messages` | body `{"session_id":string|null,"expected_status_revision":string,"context":object,"content":string}`；`201 {session_id,user_message,guide_message}`，不得 dispatch 或写 Runtime |

`GuideMessage` 为 `{id,role:"human|guide",content,context,status_revision,historical,created_at,links[]}`；`content` 是非规范解释，canonical 状态始终由同响应的 context/status revision 核对。message pending 时禁止重复提交；失败保留未发送输入并可 Retry。

Guide surface 固定在 sidebar 下方约 `1/3`；可用按钮是 Collapse/Expand、divider 调整/恢复默认和 projection 给出的 owning-surface 导航，绝不呈现或提交 IF-10 action。auto-collapse 只改变本次 layout，不改 preference。Guide loading、empty、dirty（未发送输入）、stale、permission、error/retry 与 IF-08 同源；`status_revision` 不一致时导航到 owning surface 后先刷新。Agent/解释服务失败时 summary 仍包含全部 canonical 字段并显示“解释暂不可用”，不阻塞导航。

专业 Agent Chat 继续使用既有 `/api/opencode/instances` 与 message/event 接口，但公开 instance projection 必须增加 `session_kind:"specialist_agent|historical_maestro"`、`agent`、`runtime_binding:{task_id,artifact_path,artifact_revision,write_scope,review_scope}`、`read_only`。新建 instance 只接受 Runtime projection 允许且带 binding 的专业 Agent；`guide`、`maestro` 不能成为新建 agent。历史 Maestro 为 `historical_maestro/read_only:true`，message POST/abort/recover 均返回 `409 action_not_allowed`。Guide session 不出现在 Agent picker 或 `/api/opencode/instances` 中。

## 12. IF-10 — Owning-surface Runtime-authorized action

`POST /api/workbench/actions/{action_id}` body：

```json
{"expected_status_revision":"status_opaque","confirmation_token":null,"input":{}}
```

| action kind | 合同 |
|---|---|
| `navigate` | 不 POST；使用 action 的同源 `href` |
| `dispatch` | pending 时禁用重复提交；`200 {outcome:"accepted|completed",status:WorkflowStatusProjection,continue_url:string|null}` |
| `preview`/danger confirm | 首次 `200 {confirmation:{token,summary,expires_at}}`，Human Confirm 后携 token 再 POST；Cancel 无副作用 |

服务端必须从当前 Runtime projection 重新校验 action id、权限和 revision。非法/过期为 `409 action_not_allowed|stale_revision`；失败 response 明示“状态未推进”并提供 retryability。HTTP timeout 后客户端先 GET IF-08 readback，不能盲目重发。

该 POST 控件只可出现在 IF-08 指定 action 所属的 Setup、Story、artifact、decision 或其它正式 owning surface；Guide 只能导航至该 surface，调用 Guide message/preference API 永不触发此接口。

## 13. IF-11 — Start Story 与深链

Start Story 复用 `v0.14-001` release/Story Preview/Confirm 公开合同与稳定 `/api/releases/...` namespace；`/api/v14/releases/...` 只是相同 application service 的兼容别名。

| Context | 动作与结果 |
|---|---|
| Ready/Empty 驾驶舱 | 主动作 `Start Story` 导航到 release 中 Story 的 Preview/Confirm；没有“Create Next Release”替代动作 |
| Released | 打开 released Story/readback；若 Runtime 允许开始下一个 Story，Guide/required action 使用同一 Start Story 入口 |
| Current Work | 打开 current Story 或 Run 深链，不创建新 release/run |
| Story Confirm | 成功后进入对应 Story/current work；重复确认遵循既有 idempotency/readback 合同 |

## 14. IF-12 — 结构化 evidence

每个 Setup 或 owning-surface Runtime command 产生一条脱敏结构化事件，sink 可由测试/CI 捕获：

```json
{
  "event":"setup.action|workflow.action",
  "operation_id":"opaque",
  "actor_id":"opaque",
  "workspace_id":"opaque",
  "action":"repository_confirm",
  "expected_revision":"opaque",
  "result_revision":"opaque|null",
  "outcome":"succeeded|failed|conflict|uncertain",
  "error_code":null,
  "started_at":"RFC3339",
  "finished_at":"RFC3339"
}
```

字段集合中禁止 credential、token、remote userinfo、provider session metadata 和未脱敏 subprocess output。失败事件和 HTTP error code 必须一致；`uncertain` 永不等同 succeeded。

Guide message、preference 与 last-seen 绝不写入 Runtime evidence，也不使用 `workflow.action` 事件；普通访问日志不得包含对话正文或未发送输入。Guide context 发送到解释 adapter 前使用与本接口相同的秘密过滤，只允许 IF-08 的非秘密 projection 字段。

## 15. IF-13 — 可访问与响应式出口

| 条件 | 可观察合同 |
|---|---|
| Keyboard | 从 skip link 到 sidebar、主内容、Workflow Status、Guide 顺序可预测；所有 action 可 Enter/Space；focus 可见；dialog 捕获并归还 focus |
| Accessible name/status | step、field error、pending、success、stale、conflict、permission、reconnect 均由 role/name/description 或 live region 可观测，不仅靠颜色 |
| `1024x768 @ 100%` | 主内容、sidebar 和 Guide 不重叠；水平滚动不用于主要操作 |
| `1280x720 @ 200%` | Guide 可临时折叠；导航、当前状态和主动作仍可见/可达 |
| Reduced motion | 进度与状态不依赖动画；关闭动画不丢信息 |

## 16. IF-14 — 兼容合同

| 旧入口 | 合同 |
|---|---|
| `/workbench`、`/setup`、`/projects` | 同源 redirect 或 shell bootstrap 到 IF-01，不复制事实；保留可识别 context |
| `/api/v14/releases/...` | 与稳定 `/api/releases/...` 共享语义、鉴权、错误、idempotency；响应不得漂移 |
| bookmarked Project/Story/Run URL | 有权且存在则打开同一资源；无权/不存在为安全 `404`；Setup 未完成时先进入 Setup 并保存安全 continue URL |

redirect 不得丢失合法同源 `next`，不得接受开放重定向。兼容入口会在删除前经过单独 deprecation Spec；本 Spec 不删除。

## 17. IF-15 — CI 命令与 evidence

| Gate/job | 宿主命令 | 成功出口 | 失败语义 |
|---|---|---|---|
| `quality` | `pre-commit run --all-files`；`python -m mypy louke` | tool report/exit 0 | 任一诊断或命令缺失失败 |
| `unit` | `/tmp/lk-venv/bin/python -m pytest -q tests/unit --cov=louke.runtime --cov-report=xml --cov-report=term-missing --cov-fail-under=95` | coverage/JUnit + exit 0；非零 collected | failed/cancelled/zero collection 失败 |
| `traceability` | `python tools/check_ac_traceability.py --acceptance .louke/project/specs/v0.14-004-workspace-onboarding-workflow-status/acceptance.md --tests tests --expected-count 43`（并保留既有 001 scan） | 43 个 `AC-FR*`/`AC-NFR*` 映射 interface/layer/job；tool 必须拒绝零声明/数量不符 | missing/unknown/insufficient layer 失败 |
| `build-artifacts` | `python -m build` | 唯一 wheel+sdist、SHA-256、source SHA | build/缺失/多余 artifact 失败 |
| `artifact-verify` | `python tools/louke_python_release_adapter.py verify-dist --source pyproject.toml --dist dist --evidence dist/verified-identity.json`；隔离安装 wheel 后执行 `lk --version` 与 `python -c "import importlib.metadata as m; print(m.version('louke'))"` | 唯一 wheel、sdist、installed version 均等于 `pyproject.toml` | 缺失/多余/无法提取/任一不匹配/不确定失败 |
| `integration` | `tests/e2e/run-project-venv integration` | JUnit、IF-01..15 contract evidence | 本 Spec路径未发现、zero collection、任一失败 |
| `e2e-standin` | `tests/e2e/run-project-venv e2e --profile all --runtime both` | Playwright/runner evidence，含本 Spec node ids | 本 Spec路径未发现、浏览器/服务失败、任一 runtime 失败 |
| `install-matrix` | 现有 local/global install matrix | 安装态 shell/static/version evidence | 任一受支持环境失败 |
| `required` | workflow aggregation（无宿主 shell command） | 唯一 `Louke CI / required` success | 任一 required need 非 success/缺失/未知则失败 |

所有 evidence 至少含 `source_sha`、artifact digest（适用时）、runtime/OS/Python、suite、collected node ids、AC ids、result 和时间；不得只凭 workflow step 文案声称 PASS。
