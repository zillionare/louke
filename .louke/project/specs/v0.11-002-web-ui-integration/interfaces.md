# Louke Web IDE — Web UI 集成 — Interfaces

- **Spec ID**: `v0.11-002-web-ui-integration`
- **基线契约**: `../v0.11-001-web-ide/interfaces.md` §1–§6 原样继承并锁定
- **增量范围**: 本文件只增加 `[ui]` 页面/client 契约；不改变 16 endpoints、8 schemas、SSE、错误码或状态机

## 1–6 继承的 locked 接口

| 范围 | 规范来源 | 本期规则 |
|---|---|---|
| 16 HTTP endpoints、8 schemas、文件范围 | v0.11-001 `interfaces.md` §1 | 原样生效，不覆盖 |
| OpenCode/Wiki SSE | v0.11-001 §2 | 原样生效；本期不新增 stream |
| OpenCode adapter | v0.11-001 §3 | 原样生效 |
| `ErrorResponse` | v0.11-001 §4 | UI 解析并展示，不改写机器码 |
| lifecycle | v0.11-001 §5 | UI 状态不得超前于公开响应 |
| API 出口测试覆盖 | v0.11-001 §6 | 既有 API e2e 保留 |

## 7. `[ui]` Web UI 客户端契约（本期新增）

### 7.1 JavaScript public API

| 模块 / operation | Signature | 调用的 locked endpoint | Promise result |
|---|---|---|---|
| 模块 | `window.LoukeClient`，资产 `/assets/client.js` | — | 页面可在 `DOMContentLoaded` 后调用 |
| `opencode.create` | `create()` | `POST /api/opencode/instances` | `Instance` |
| `opencode.list` | `list()` | `GET /api/opencode/instances` | `Instance[]` |
| `opencode.send` | `send(instanceId, content)` | `POST /api/opencode/instances/{id}/messages` | `{message, accepted}` |
| `opencode.messages` | `messages(instanceId, after?)` | `GET /api/opencode/instances/{id}/messages` | `Message[]`（仅该 id） |
| `intent.route` | `route(input, selection?, confirmation?)` | `POST /api/intent/route` | `IntentRouteResult` |
| `wiki.get` | `get(type, includeContent=true)` | `GET /api/wiki/{type}` | `WikiPage` |
| `wiki.build` | `build(type, trigger="manual")` | `PUT /api/wiki/{type}` | build acknowledgement |
| `backlog.list/create/start` | `list()` / `create(story)` / `start(id)` | `GET/POST/DELETE /api/backlog` | locked backlog responses |
| `files.list/content/diff/save` | `list(view, path?, approved?)` / `content(path, approved?)` / `diff(path)` / `save(path, content, revision?)` | locked Files endpoints | locked file responses |
| `tasks.get/toggle` | `get(frId, documentPath)` / `toggle(frId, documentPath, task, checked, revision?)` | `GET/PATCH /api/tasks/{fr_id}` | `TaskState` |

| Client failure | Contract |
|---|---|
| locked non-2xx JSON | rejected value `{status, error_code, message, detail}`，保留服务端字段 |
| network/non-JSON failure | rejected value `{status: 0, error_code: "CLIENT_REQUEST_FAILED", message}`；仅为 UI client failure，不新增 HTTP error code |
| request body | 仅发送 locked endpoint 定义字段；不把 fixture、DOM 或 mock success 写入 body |

### 7.2 页面与导航 identifiers

| 页面/控件 | `data-testid` | 可观察契约 |
|---|---|---|
| 所有页面根 | `page-home`、`page-wiki`、`page-models`、`page-docs`、`page-login` | 与 `/`、`/wiki...`、`/models`、`/docs/...`、`/login` 对应且唯一可见 |
| 主导航 | `nav-home`、`nav-wiki`、`nav-models`、`nav-docs` | click 后 URL 与目标页面一致 |
| 全局 request 状态 | `ui-pending`、`ui-success`、`ui-error` | pending/success/error 互斥；error 时不得显示 success |
| API fixture marker | `api-data` | 文本/值来自最近成功 API response，不允许模板预置 mock |

### 7.3 OpenCode controls（home）

| `data-testid` | Element/value contract |
|---|---|
| `opencode-create` | button；click 调 `opencode.create` |
| `opencode-instance-list` | 每项 `opencode-instance-{id}`，显示 API id/status |
| `opencode-select-{id}` | button/radio；设置当前实例，`aria-pressed` 或 checked 可观察 |
| `opencode-message-input` | labelled textbox；提交非空 content |
| `opencode-send` | button；只向当前 id 发送 |
| `opencode-status` | 当前实例公开 status |
| `opencode-messages` | 仅当前实例 messages；切换后替换而非合并其他实例 |
| `opencode-error` | 发送/create/list 失败的可见 message/error_code；失败消息不得标成功 |

### 7.4 Backlog controls（home）

| `data-testid` | Element/value contract |
|---|---|
| `backlog-story-input` / `backlog-submit` | labelled textbox/button；click 调 `backlog.create` |
| `backlog-list` | 每项 `backlog-entry-{id}`，显示 API story/status |
| `backlog-select-{id}` | button/radio；唯一选择可观察 |
| `backlog-start` | 无选择时不发 DELETE，显示 `backlog-error`；有选择时调 `start(id)` |
| `backlog-success` / `backlog-error` | 成功或失败互斥；成功 start 后目标项消失，其他项不变 |

### 7.5 Files controls（home）

| `data-testid` | Element/value contract |
|---|---|
| `files-view-tree` / `files-view-changes` | button；分别请求 `view=tree|changes` |
| `files-list` | 每项 `file-entry-{encoded-path}`，path 与 API 一致 |
| `file-open-{encoded-path}` | 打开 content；只读性由 `FileEntry.writable`/失败响应决定 |
| `file-diff-{encoded-path}` / `file-diff` | click 请求该 path；结果区显示对应 diff |
| `file-editor` | labelled textbox/editor；值为 API content |
| `file-save` | 使用当前 path/content/revision 调 save |
| `file-save-success` / `file-error` | 互斥；拒写时 error 可见且 success 不可见 |

### 7.6 Task controls（docs）

| `data-testid` | Element/value contract |
|---|---|
| `task-valid`、`task-testable`、`task-decided` | labelled checkbox；checked 与 `TaskState.tasks` 对应 |
| `task-state` | 携带当前 `fr_id`、`document_path`、`revision` 的公开页面状态 |
| `task-success` / `task-error` | toggle 结果互斥；失败回滚 checkbox 到最近成功 TaskState |
| checkbox click | 只发送目标 task/checked；成功后另外两个 checked 值保持响应中的值 |

### 7.7 Wiki、models 与 login exits

| 页面 | `data-testid` | Contract |
|---|---|---|
| wiki | `wiki-type`、`wiki-load`、`wiki-content`、`wiki-refresh`、`wiki-error` | canonical type 经 `wiki.get/build`；内容/错误来自 locked response |
| models | `models-instance-list`、`models-error` | 实例数据来自 `opencode.list`；不替换既有 binding controls |
| login | `login-submit`、`login-error` | 保留 v0.10 auth 契约；仅提供稳定 UI identifier |

### 7.8 UI 状态与事件规则

| Trigger | Success exit | Failure exit |
|---|---|---|
| page hydrate/list | 对应 list/content/status 区可见并替换旧数据 | 对应 `*-error` 可见；不得显示 fixture/mock fallback |
| mutation click | pending → response 驱动 success/result | pending → error；success hidden，资源 UI 不提前提交 |
| instance switch | status/messages 替换为选中 id 的 GET 结果 | 保留明确选择并显示 error，不混入其他 id 输出 |
| reload/reopen | GET/API/文件事实重建 backlog、document、TaskState | 可见 error，不使用上次内存 success 冒充持久化 |
| SSE/event bus | **无新增 UI 公共契约** | 若消费 inherited SSE，event schema 必须仍为 v0.11-001 §2 |

## 8. AC 闭合到接口与测试

| AC | 接口出口 | Test Plan §8 函数族 |
|---|---|---|
| AC-FR0202-01 | locked §1 endpoints + architecture §3.1 assembly | `test_web_app_mounts.py::test_ac_fr0202_01_*` |
| AC-FR0202-02 | §7.2 page/nav | `test_web_ui_routes.py::test_ac_fr0202_02_*` |
| AC-FR0202-03 | §7.2 `api-data`；§7.3–7.7 result exits | `test_web_ui_routes.py::test_ac_fr0202_03_*` |
| AC-FR0202-04 | §7.1 failure；§7.2/7.8 error rule | `test_web_ui_routes.py::test_ac_fr0202_04_*` |
| AC-FR0203-01 | §7.3 create/list/status | `test_web_ui_opencode.py::test_ac_fr0203_01_*` |
| AC-FR0203-02 | §7.3 select/send/messages | `test_web_ui_opencode.py::test_ac_fr0203_02_*` |
| AC-FR0203-03 | §7.3 messages isolation；§7.8 switch | `test_web_ui_opencode.py::test_ac_fr0203_03_*` |
| AC-FR0203-04 | §7.3 `opencode-error`；§7.8 failure | `test_web_ui_opencode.py::test_ac_fr0203_04_*` |
| AC-FR0204-01 | §7.4 create/list | `test_web_ui_backlog.py::test_ac_fr0204_01_*` |
| AC-FR0204-02 | §7.4 select/start/removal | `test_web_ui_backlog.py::test_ac_fr0204_02_*` |
| AC-FR0204-03 | §7.4 no-selection guard/error | `test_web_ui_backlog.py::test_ac_fr0204_03_*` |
| AC-FR0205-01 | §7.5 view controls/list | `test_web_ui_files.py::test_ac_fr0205_01_*` |
| AC-FR0205-02 | §7.5 diff controls/result | `test_web_ui_files.py::test_ac_fr0205_02_*` |
| AC-FR0205-03 | §7.5 editor/save/success；§7.8 reload | `test_web_ui_files.py::test_ac_fr0205_03_*` |
| AC-FR0205-04 | §7.5 `file-error` + locked read-only response | `test_web_ui_files.py::test_ac_fr0205_04_*` |
| AC-FR0206-01 | §7.6 checkboxes/TaskState | `test_web_ui_tasks.py::test_ac_fr0206_01_*` |
| AC-FR0206-02 | §7.6 target-only toggle | `test_web_ui_tasks.py::test_ac_fr0206_02_*` |
| AC-FR0206-03 | §7.6 + §7.8 reload | `test_web_ui_tasks.py::test_ac_fr0206_03_*` |
| AC-NFR0102-01 | §7.3 all user controls/exits | `test_web_ui_opencode.py::test_ac_nfr0102_01_*` |
| AC-NFR0102-02 | §7.4 all user controls/exits | `test_web_ui_backlog.py::test_ac_nfr0102_02_*` |
| AC-NFR0102-03 | §7.5 all user controls/exits | `test_web_ui_files.py::test_ac_nfr0102_03_*` |
| AC-NFR0102-04 | §7.6 all user controls/exits | `test_web_ui_tasks.py::test_ac_nfr0102_04_*` |
| AC-NFR0102-05 | §7.2–§7.8 stable controls + browser-visible exits | Chromium/Firefox matrix；`test_ac_nfr0102_05_*` |

| Closure | Status |
|---|---|
| Acceptance → interface exit | 23/23 mapped |
| Interface exit → planned coverage | §7.1 client: unit/integration；§7.2–7.8: integration/UI e2e；locked exits: existing API e2e |
| 新 observation method | 无；所有断言基于 locked API/文件事实或本文件 `[ui]` browser exits |
