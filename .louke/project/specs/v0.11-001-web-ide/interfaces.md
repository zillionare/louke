# Louke Web IDE 与工作流服务化 — Interfaces

- **Spec ID**: `v0.11-001-web-ide`
- **Base URL**: `http://127.0.0.1:8765`
- **Content-Type**: `application/json; charset=utf-8`（SSE 除外）
- **Auth profile**: `local-session`（loopback 本地会话；本期无账户 API）
- **延期项**: `FR-0101` 无本期接口

## 1. HTTP API 契约

### 1.1 通用字段

| 类型 | 字段 |
|---|---|
| `Instance` | `{id: string, status: "starting"|"running"|"stopping"|"stopped"|"error", created_at: RFC3339, error?: ErrorResponse}` |
| `Message` | `{id: string, instance_id: string, role: "user"|"assistant"|"system", kind: "message"|"command"|"status"|"error", content: string, created_at: RFC3339}` |
| `WikiPage` | `{type: WikiType, status: "fresh"|"stale"|"building"|"failed", markdown: string, sources: [{path: string, anchor: string}], updated_at?: RFC3339, build_id?: string}` |
| `BacklogEntry` | `{id: string, story: string, status: "pending"|"dispatching"|"removed"|"failed", created_at: RFC3339, error?: ErrorResponse}` |
| `FileEntry` | `{path: string, kind: "file"|"directory", changed: boolean, binary?: boolean, line_count?: integer, readable: boolean, writable: boolean, approval_required: boolean}` |
| `TaskState` | `{fr_id: string, document_path: string, tasks: {Valid: boolean, Testable: boolean, Decided: boolean}, revision: string}` |
| `WikiType` | `"story"|"spec"|"test-plan"|"architecture"|"interfaces"` |

### 1.2 Endpoint 清单

| # | Method / Path | Auth | Request | Success response | Errors | AC 出口 |
|---:|---|---|---|---|---|---|
| 1 | `POST /api/opencode/instances` | local-session | `{}` | `201 Instance`，唯一 `id`，初始/最终状态可观察 | `503 OPENCODE_UNAVAILABLE` | AC-FR0001-01 |
| 2 | `GET /api/opencode/instances` | local-session | — | `200 {instances: Instance[]}` | `500 INTERNAL_ERROR` | AC-FR0001-01、04 |
| 3 | `DELETE /api/opencode/instances?id={id}` | local-session | — | `200 Instance`，状态为 `stopped`（重复停止幂等） | `404 INSTANCE_NOT_FOUND` | AC-FR0001-04 |
| 4 | `POST /api/opencode/instances/{id}/messages` | local-session | `{content: string}`；`/...` 不改写 | `202 {message: Message, accepted: true}` | `404 INSTANCE_NOT_FOUND`、`409 INSTANCE_NOT_RUNNING`、`504 OPENCODE_TIMEOUT` | AC-FR0001-02..04 |
| 5 | `GET /api/opencode/instances/{id}/messages?after={message_id?}` | local-session | — | `200 {instance_id: string, messages: Message[]}`，只含该实例 | `404 INSTANCE_NOT_FOUND` | AC-FR0001-02..03 |
| 6 | `POST /api/intent/route` | local-session | `{input: string, selection?: "start_development"|"save_backlog"|"spec_change"|"fix", confirmation?: boolean}` | `200 IntentRouteResult` | `400 VALIDATION_ERROR`、`409 CONFIRMATION_REQUIRED` | AC-FR0201-01..04 |
| 7 | `GET /api/wiki/{type}` | local-session | query `include_content=true|false`，`type` 为 `WikiType` | `200 WikiPage` | `404 WIKI_SOURCE_NOT_FOUND`、`400 WIKI_TYPE_INVALID` | AC-FR0301-01..04 |
| 8 | `PUT /api/wiki/{type}` | local-session | `{trigger: "manual"|"scheduled"}` | `202 {build_id: string, type: WikiType, status: "building"|"unchanged"}` | `404 WIKI_SOURCE_NOT_FOUND`、`409 WIKI_BUILD_ACTIVE` | AC-FR0301-05 |
| 9 | `GET /api/backlog` | local-session | — | `200 {entries: BacklogEntry[]}` | `500 BACKLOG_STORE_ERROR` | AC-FR0601-01..03 |
| 10 | `POST /api/backlog` | local-session | `{story: string}` | `201 BacklogEntry` | `400 VALIDATION_ERROR`、`500 BACKLOG_STORE_ERROR` | AC-FR0601-01 |
| 11 | `DELETE /api/backlog` | local-session | `{id: string, action: "start_development"}` | `200 {id: string, status: "removed", workflow_started: true}`；仅 workflow 接受后删除 | `400 SELECTION_REQUIRED`、`404 BACKLOG_NOT_FOUND`、`409 WORKFLOW_REJECTED` | AC-FR0601-02..03 |
| 12 | `GET /api/files?view={tree|changes|content|documents}&path={relative?}&approved={false|true}` | local-session | — | `200 FileListResponse` 或 `200 FileContentResponse` | `403 PATH_OUTSIDE_WORKSPACE`、`403 APPROVAL_REQUIRED`、`415 BINARY_NOT_PREVIEWABLE`、`404 FILE_NOT_FOUND` | AC-FR0701-01、04；AC-FR0801-01..03；AC-NFR0201-01 |
| 13 | `GET /api/files/diff?path={relative}` | local-session | — | `200 {path: string, diff: string}` | `403 PATH_OUTSIDE_WORKSPACE`、`404 FILE_NOT_FOUND`、`409 FILE_NOT_CHANGED` | AC-FR0701-01；AC-NFR0201-01 |
| 14 | `PUT /api/files/{path}` | local-session | `{content: string, revision?: string}`；`path` 为 URL 编码 workspace-relative path | `200 {path: string, revision: string, saved: true}` | `403 PATH_OUTSIDE_WORKSPACE`、`403 FILE_READ_ONLY`、`403 FILE_PERMISSION_DENIED`、`409 REVISION_CONFLICT`、`415 BINARY_NOT_PREVIEWABLE` | AC-FR0701-02..03；AC-NFR0201-01..02 |
| 15 | `PATCH /api/tasks/{fr_id}` | local-session | `{document_path: string, task: "Valid"|"Testable"|"Decided", checked: boolean, revision?: string}` | `200 TaskState` | `403 PATH_OUTSIDE_WORKSPACE`、`403 FILE_READ_ONLY`、`404 TASK_NOT_FOUND`、`409 REVISION_CONFLICT` | AC-FR0501-01..03；AC-NFR0201-02 |
| 16 | `GET /health` | none/loopback | — | `200 {status: "ready", workspace: "ready", opencode: "ready"|"degraded"}`；仅 e2e mock 必须为 `ready` | `503 {status: "starting"|"unhealthy"}` | AC-NFR0001-01、AC-NFR0101-01 |

### 1.3 复合响应 schema

| Schema | Contract |
|---|---|
| `IntentRouteResult` | `{intent: "story"|"spec_change"|"bug_fix"|"unknown", confidence: number[0..1], proposed_action: "choose_story_destination"|"spec_change"|"fix"|"clarify", requires_confirmation: boolean, clarification_question?: string, executed: boolean, execution_id?: string}` |
| `FileListResponse` | `{view: "tree"|"changes"|"documents", entries: FileEntry[]}` |
| `FileContentResponse` | `{path: string, content: string, format: "text"|"markdown", rendered_html?: string, line_count: integer, revision: string}` |

### 1.4 文件范围契约

| 操作 | 允许范围 | 拒绝范围 |
|---|---|---|
| list/read/diff | canonical workspace 内非 symlink 目标 | 绝对路径、`..`、编码 traversal、symlink、realpath 越界 |
| document discovery/render | `.louke/project/**` 中约定 Louke design Markdown、根 `README.md`、`docs/**/*.md` | 其他范围、二进制；>500 行未批准正文 |
| write | `.louke/project/**/story.md`、`spec.md`、`acceptance.md` | 源代码及所有其他文件 |
| task patch | 上述可写文件内既有 `Valid`/`Testable`/`Decided` Markdown task | 表格伪状态、不存在 task、非 allowlist 文档 |

## 2. SSE 契约

### 2.1 流入口

| Stream | Method / Path | Query/headers | Event types | 结束条件 | Errors |
|---|---|---|---|---|---|
| OpenCode stream | `GET /api/opencode/instances/{id}/messages/stream` | `Last-Event-ID` 可选 | `instance.status`、`message.echo`、`message.delta`、`message.completed`、`instance.error` | client disconnect 或 instance `stopped/error` | 连接前使用 ErrorResponse；连接后使用 `instance.error` |
| Wiki progress | `GET /api/wiki/{type}/events?build_id={id}` | `Last-Event-ID` 可选 | `wiki.started`、`wiki.progress`、`wiki.unchanged`、`wiki.completed`、`wiki.failed` | `unchanged/completed/failed` | 连接前使用 ErrorResponse；连接后使用 `wiki.failed` |

### 2.2 Event envelope

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | string | stream 内单调、可用于 `Last-Event-ID` |
| `event` | enum | 与上表 event type 一致 |
| `data.correlation_id` | string | 对应触发请求 |
| `data.instance_id` | string? | OpenCode event 必须存在，严禁跨实例 |
| `data.build_id` | string? | Wiki event 必须存在 |
| `data.status` | string | 当前公开状态 |
| `data.content` | string? | message delta/echo；错误不得携带 workspace 外内容 |
| `data.progress` | integer? | Wiki `0..100` |
| `data.error` | ErrorResponse? | 仅错误 event |

## 3. OpenCode 协议抽象

### 3.1 Public adapter interface

| Operation | Input | Output | Failure |
|---|---|---|---|
| `create_instance` | `{correlation_id}` | `Instance` | `OpenCodeUnavailable` |
| `list_instances` | — | `list[Instance]` | `OpenCodeUnavailable` |
| `stop_instance` | `{instance_id}` | `Instance(status=stopped)` | `InstanceNotFound` |
| `send_message` | `{instance_id, content, correlation_id}` | `{accepted_message: Message}` | `InstanceNotFound`、`InstanceNotRunning`、`OpenCodeTimeout` |
| `stream_events` | `{instance_id, after_event_id?}` | async stream of `OpenCodeEvent` | `InstanceNotFound`、`OpenCodeDisconnected` |
| `health` | — | `"ready"|"degraded"|"unavailable"` | — |

### 3.2 `OpenCodeEvent`

| 字段 | 类型 | 约束 |
|---|---|---|
| `event_id` | string | instance stream 内唯一 |
| `instance_id` | string | 必须等于订阅 id |
| `kind` | `status|echo|delta|completed|error` | 外部协议归一化值 |
| `content` | string? | `/models`、`/agent` 及任意 `/` 命令结果不做业务改写 |
| `status` | Instance status? | 状态事件必填 |
| `error` | ErrorResponse? | error 事件必填 |
| `created_at` | RFC3339 | 可控 clock 生成 |

### 3.3 Stand-in 一致性

| 要求 | Contract |
|---|---|
| 真实 adapter 与 mock adapter | 实现同一 operation/event schema |
| mock 可脚本化 | success、明确错误、延迟、超时、断连、停止后拒绝 |
| mock 公开记录 | `{instance_id, operation, content?, correlation_id, received_at}`；仅供外部 contract/e2e fixture 断言 |
| 隔离 | 每个 instance 独立事件序列；每个测试独立 mock state |

## 4. 错误响应 schema

### 4.1 `ErrorResponse`

| 字段 | 类型 | 约束 |
|---|---|---|
| `error_code` | string | 稳定机器码，大写 snake case |
| `message` | string | 面向用户，不含 stack trace/secrets |
| `detail` | object | 可含 `correlation_id`、逻辑 `path`、`instance_id`、`retryable`；不得含 workspace 外文件正文 |

### 4.2 状态码与机器码

| HTTP | error_code |
|---:|---|
| 400 | `VALIDATION_ERROR`、`WIKI_TYPE_INVALID`、`SELECTION_REQUIRED` |
| 403 | `PATH_OUTSIDE_WORKSPACE`、`FILE_READ_ONLY`、`FILE_PERMISSION_DENIED`、`APPROVAL_REQUIRED` |
| 404 | `INSTANCE_NOT_FOUND`、`WIKI_SOURCE_NOT_FOUND`、`BACKLOG_NOT_FOUND`、`FILE_NOT_FOUND`、`TASK_NOT_FOUND` |
| 409 | `INSTANCE_NOT_RUNNING`、`CONFIRMATION_REQUIRED`、`WIKI_BUILD_ACTIVE`、`WORKFLOW_REJECTED`、`REVISION_CONFLICT`、`STATE_CONFLICT`、`FILE_NOT_CHANGED` |
| 415 | `BINARY_NOT_PREVIEWABLE` |
| 500 | `BACKLOG_STORE_ERROR`、`INTERNAL_ERROR` |
| 503 | `OPENCODE_UNAVAILABLE` |
| 504 | `OPENCODE_TIMEOUT` |

## 5. 状态机契约

### 5.1 OpenCode instance lifecycle

| Current | Trigger | Next | Observable exit |
|---|---|---|---|
| absent | create | `starting` → `running` | POST response、instances GET、`instance.status` |
| `running` | send message/command | `running` | 202 + message SSE/GET |
| `running` | stop | `stopping` → `stopped` | DELETE + status SSE/GET |
| `running` | timeout/disconnect | `error` | ErrorResponse/`instance.error` |
| `stopped` | stop | `stopped` | 幂等 200 |
| `stopped/error` | send | unchanged | `409 INSTANCE_NOT_RUNNING` |

### 5.2 Wiki page staleness lifecycle

| Current | Trigger/guard | Next | Observable exit |
|---|---|---|---|
| `fresh` | source digest unchanged | `fresh` (`unchanged`) | PUT 202 status + `wiki.unchanged`；bytes/mtime 不变 |
| `fresh` | source digest changed | `stale` → `building` | GET status、progress SSE |
| `stale` | manual/daily trigger | `building` | PUT 202 + `wiki.started` |
| `building` | validated publish | `fresh` | `wiki.completed` + GET 新内容/来源 |
| `building` | missing source/build failure | `failed` | `wiki.failed`；GET 仍可返回上一成功内容及 failed 状态 |
| `failed` | valid retrigger | `building` | 新 build id |

### 5.3 Backlog entry lifecycle

| Current | Trigger/guard | Next | Observable exit |
|---|---|---|---|
| absent | valid POST | `pending` | 201 + GET list |
| `pending` | selected start-development | `dispatching` | DELETE request correlation id |
| `dispatching` | workflow accepted | `removed` | 200；后续 GET 不含该项 |
| `dispatching` | workflow rejected | `failed` | 409；GET 保留条目及 error |
| no selection | DELETE | unchanged | `400 SELECTION_REQUIRED`；workflow 未启动 |

## 6. 接口出口到测试覆盖

| 接口出口 | 覆盖层 | Test Plan 依据 |
|---|---|---|
| instance/message HTTP + OpenCode SSE + adapter contract | unit、integration、e2e | §2.1–2.3、§3 FR-0001、§5.2 |
| intent route result/确认门 | unit、integration、e2e | §3 FR-0201、§6.3 指令路由 |
| Wiki HTTP/progress/页面来源 | unit、integration、e2e | §3 FR-0301、§5.3、§6.3 Wiki 更新 |
| 规范产物路径 | integration | §3 FR-0401、§6.5 |
| task PATCH/TaskState | unit、integration、e2e | §3 FR-0501、§6.3 文档状态 |
| backlog HTTP/lifecycle | unit、integration、e2e | §3 FR-0601、§6.3 Backlog |
| files tree/content/diff/save + ErrorResponse | unit、integration、e2e | §3 FR-0701/0801/NFR-0201、§7.2 |
| health、pytest/coverage/e2e 退出码 | CI、e2e | §3 NFR-0001/0101、§6.1–6.2、§8 |
