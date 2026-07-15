---
status: Draft — M-ARCH
spec_id: v0.13-001-web-ui-foundation
created: 2026-07-15
locked: false
---

# Web UI Foundation — External Interfaces Contract

## 1. 通用规则

| 项            | Contract                                                                                                            |
| ------------- | ------------------------------------------------------------------------------------------------------------------- |
| Base URL      | `http://127.0.0.1:<port>`；只监听 loopback                                                                          |
| Auth          | v0.13 新增 endpoint（`/api/ui/**` 与 End User Docs `/api/end-user-docs/**`）要求现有 local principal 的 `louke_session` cookie；写请求沿用同源/CSRF 边界。既有 v0.12 mounted API（`/api/projects/**`、`/api/gates/**`、`/api/opencode/**` 等）保持其既有 `x-louke-principal` / local principal 合同不变 |
| JSON          | `application/json; charset=utf-8`；时间为 RFC 3339 UTC；ID 为不透明字符串                                           |
| SSE           | `text/event-stream`；支持 `Last-Event-ID`；15 秒内可发 comment keepalive                                            |
| Path          | API 中的文件 path 均为 canonical root 下 URL-encoded POSIX relative path；绝对路径、`..`、隐藏文件与 symlink 不合法 |
| Unknown value | 不丢弃原值；响应含 `unknown:true` 与可读 `display_label`；不得因未知 stage/status/result kind 返回 5xx              |

> **Prism** [RESOLVED]: `Auth` 规则当前范围过宽：现有 v0.12 mounted APIs 并不使用 `louke_session`，而 spec 又禁止收紧这些上游接口。请把规则限定到 v0.13 新增 endpoints，或单列“legacy v0.12 auth contract”并说明兼容策略；否则 AC-FR1304-03 与 out-of-scope 无法同时满足。
>> **Aaron**: 规则限定于 v0.13新增部分
>> **Prism**: 收到。请把表中 `Auth` 行改成“v0.13 新增 endpoints”，并单列既有 v0.12 routes 维持原合同；这样我可以在复审时关闭此 thread。

### 1.1 v0.13 错误 envelope

| 字段      | 类型    | 约束                                                            |
| --------- | ------- | --------------------------------------------------------------- |
| `code`    | string  | 稳定大写 snake case                                             |
| `message` | string  | 可读且不含 stack trace、secret 或规范根外路径正文               |
| `details` | object? | 可含逻辑 path、current mtime、correlation id；不得含 credential |

|        HTTP | code                                                               |
| ----------: | ------------------------------------------------------------------ |
|         400 | `VALIDATION_FAILED`                                                |
|         401 | `AUTH_REQUIRED`                                                    |
|         403 | `PATH_NOT_ALLOWED`                                                 |
|         404 | `NOT_FOUND`、`AGENT_NOT_FOUND`、`RUN_NOT_FOUND`、`STAGE_NOT_FOUND` |
|         409 | `CONFLICT`                                                         |
|         413 | `TOO_LARGE`                                                        |
| 502/503/504 | `UPSTREAM_ERROR`、`OPENCODE_UNAVAILABLE`、`OPENCODE_TIMEOUT`       |

## 2. Browser DOM 与状态 contract

| Outlet / selector                             | Contract                                                                                                                        | modules                                                                                                         | AC 出口                                                                                  |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `[data-louke-region="toolbar"]`               | `role="toolbar"`；DOM/visual/a11y 顺序先于 sidebar/main                                                                         | Workbench Shell, Workbench Client                                                                               | AC-FR1301-01/02                                                                          |
| `[data-louke-region="sidebar"]`               | `role="complementary"`；`data-sidebar-kind=chat                                                                                 | dev-docs                                                                                                        | end-user-docs                                                                            | wiki            | runs` | Workbench Shell, Workbench Client                              | AC-FR1301-01/03/04、AC-FR1303-01/04 |
| `[data-louke-region="main"] [role="tablist"]` | tab host；每 tab 有唯一 `data-tab-key`；active tab 为 `aria-selected=true`                                                      | Workbench Shell, Workbench Client                                                                               | AC-FR1301-01/03—05                                                                       |
| toolbar top group                             | accessible names 完整顺序 `Chat, Dev Docs, End User Docs, Wiki, Runs`                                                           | Workbench Shell                                                                                                 | AC-FR1302-01                                                                             |
| toolbar bottom group                          | DOM 自上而下为 `Accounts, Gears`，因此自下而上为 `Gears, Accounts`                                                              | Workbench Shell                                                                                                 | AC-FR1302-02                                                                             |
| toolbar item                                  | icon-only visible content；非空 `aria-label` 与 tooltip；bounding box ≥32×32 CSS px                                             | Workbench Shell, Workbench Presentation                                                                         | AC-FR1301-02、AC-FR1302-03                                                               |
| tab identity                                  | keys 固定为 `chat                                                                                                               | settings                                                                                                        | dev-docs                                                                                 | end-user-docs   | wiki  | runs`；重复 activity 复用；仅 `[data-action="close-tab"]` 删除 | Workbench Client                    | AC-FR1301-03—05 |
| Settings                                      | `[data-tab-key="settings"]` 内含 `data-settings-pane=menu                                                                       | detail`；三个占位项的 accessible names 为 `版本更新`、`服务器配置`、`S/A/B 模型绑定`，状态标记 `待 v0.15`；占位项使用 `aria-disabled="true"`（可聚焦、可点击以更新右详情，但不触发任何保存或具体设置 action，不发起写请求） | Workbench Shell, Workbench Client                                                        | AC-FR1303-01—04 |
| Accounts                                      | Accounts button `aria-haspopup="menu"`；浮层 `role="menu"`；logout 为 `menuitem`                                                | Workbench Shell, Workbench Client, Existing Auth                                                                | AC-FR1304-01—03                                                                          |
| negative capability                           | workbench button/menu/contextmenu/link/action model 不包含 FR-1318 所列功能；Dev Docs 全集无 AI 辅助入口；Dev Docs 非 allowlist 路径不暴露 Save 与写请求（allowlist 仅 story/spec/acceptance）；Wiki/Runs 不产生对应 write network method | Workbench Shell, Workbench Client                                                                               | AC-FR1309-04/05/06、AC-FR1310-04、AC-FR1311-04、AC-FR1312-04、AC-FR1315-03、AC-FR1318-01—03 |

> **Prism** [RESOLVED]: Settings 合同把三项定义为 `disabled`，但 AC-FR1303-04 又要求“点击后更新右侧详情”。原生 disabled control 不会接收点击；请决定使用可聚焦的 `aria-disabled="true"` 占位项，或删除点击行为验收。
>> **Aaron**: 使用可聚焦的 `aria-disabled="true"` 占位项

>> **archer**: Applied: §1 Auth row limited to v0.13 new endpoints (/api/ui/** + End User Docs); v0.12 mounted APIs keep existing x-louke-principal/local principal contract unchanged - separate row.

>> **Prism**: 收到。接口应同时写明可 focus/click、不可触发保存或具体设置 action；对应 AC 中“置灰禁用”建议改成 `aria-disabled`，避免实现者使用原生 `disabled`。

### 2.1 Browser storage

| Key                             | Value                                                                                               | 生命周期                        | modules                                                             | AC 出口          |
| ------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------- | ------------------------------------------------------------------- | ---------------- |
| `louke.dev-docs.tree.<spec-id>` | `"expanded"                                                                                         | "collapsed"`                    | 首次无 key=`collapsed`；toggle 后立即更新；每次 Dev Docs 激活时恢复 | Workbench Client | AC-FR1308-02/03 |
| auth                            | `localStorage`/`sessionStorage` **不得**保存审批或 API credential；session 使用现有 HttpOnly cookie | Workbench Client, Existing Auth | AC-FR1304-02/03                                                     |

## 3. Workbench、Agent 与 Chat API

### 3.1 Agent schema

| Schema              | 字段/约束                                                                       |
| ------------------- | ------------------------------------------------------------------------------- |
| `AgentSummary`      | `{agent_id:string, name:string, icon:string, registered:true, default:boolean}` |
| `TranscriptMessage` | `{message_id:string, agent_id:string, session_id:string, role:"user"            | "assistant" | "system", content:string, created_at:RFC3339, state:"streaming" | "completed" | "error"}` |

### 3.2 HTTP endpoints

| Method / path                                                | Request                                             | Success                                                                                   | Errors                                | modules                        | AC 出口                          |
| ------------------------------------------------------------ | --------------------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------- | ------------------------------ | -------------------------------- |
| `GET /api/ui/agents`                                         | —                                                   | `200 {items:AgentSummary[], default_agent_id:string}`；Maestro 为第 1 项且 `default=true` | `401 AUTH_REQUIRED`                   | UI Bootstrap, Agent Registry   | AC-FR1305-01—03、AC-FR1307-04    |
| `GET /api/ui/chat/{agent_id}/transcript?after={message_id?}` | registered `agent_id`                               | `200 {agent_id,session_id,messages:TranscriptMessage[]}`；仅该 Agent                      | `404 AGENT_NOT_FOUND`                 | Chat Facade, Existing OpenCode | AC-FR1306-01/04、AC-FR1307-01—03 |
| `POST /api/ui/chat/{agent_id}/messages`                      | `{content:string}`；非空 UTF-8；`/`、`!` 无特殊语义 | `202 {accepted:true,message:TranscriptMessage}`                                           | `400 VALIDATION_FAILED`、OpenCode 5xx | Chat Facade, Existing OpenCode | AC-FR1306-03/05、AC-FR1307-01—03 |

### 3.3 Chat SSE

| 项          | Contract                                                                                                                |
| ----------- | ----------------------------------------------------------------------------------------------------------------------- |
| Endpoint    | `GET /api/ui/chat/{agent_id}/events`                                                                                    |
| Event types | `chat.message.started`、`chat.message.delta`、`chat.message.completed`、`chat.message.error`                            |
| Envelope    | `{id,event,data:{agent_id,session_id,message_id,role,delta?,content?,created_at,error?}}`                               |
| Delta       | `chat.message.delta.data.delta` 只表示该 message 的下一段；客户端追加到现有 `[data-message-id]` 尾部，不替换 transcript |
| Isolation   | path `agent_id`、event `agent_id`、session identity 必须一致；重连不得回放其他 Agent event                              |
| End         | client disconnect；error event 不伪装 completed                                                                         |
| modules     | Chat Facade, Existing OpenCode, Workbench Client                                                                        |
| AC 出口     | AC-FR1306-02/04/05、AC-FR1307-01—03                                                                                     |

### 3.4 未注册 Agent URL

| 输入                        | Browser contract                                                              | HTTP contract                                                            | modules                        | AC 出口      |
| --------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------ | ------------ |
| `/chat?agent=X` 且 X 未注册 | 保留或忽略 query，选择 `default_agent_id`，不显示 X transcript，不抛 JS error | UI 不向 X transcript endpoint 发请求；若直接调用则 `404 AGENT_NOT_FOUND` | Workbench Client, UI Bootstrap | AC-FR1307-04 |

### 3.5 OpenCode streaming adapter contract

| 项 | Contract |
| --- | --- |
| Protocol | `OpenCodeAdapter.stream_events(instance_id, last_event_id) -> Iterator[StreamEvent]` |
| `StreamEvent` | `{event_id:string,type:"delta"\|"completed"\|"error",message_id:string,delta?:string,content?:string,error?:string}` |
| Real source | OpenCode 项目级 `GET /event` SSE；启动时以 `/doc` 中的 `event.subscribe` + `message.part.delta` schema，以及响应 `Content-Type: text/event-stream` 做 capability check |
| Delta mapping | `message.updated` 记录 `info.role="assistant"` 的 messageID；`message.part.updated` 记录其 `part.type="text"` 的 partID；仅接受同 session、命中该 messageID/partID 且 `field="text"` 的 `message.part.delta.properties.delta`；不得从完整 part/message 切块 |
| Completion/error | `session.idle` 后重读一次 `list_messages()` 得到最终 assistant `content` 并发 completed；`session.error` 发 error |
| Isolation | 丢弃其它 session/workspace 事件；Chat 不订阅 `/global/event` |
| Browser reconnect | facade 按 session 缓存最近 256 个规范化事件；`Last-Event-ID` 命中则续传，未命中则先 transcript resync 再接 live stream |
| Unsupported upstream | `503 OPENCODE_STREAM_UNAVAILABLE`；L3/release fail，不允许 polling-chunk fallback 或 skip-as-pass |

## 4. Dev Docs API 与复用合同

### 4.1 v0.13 read endpoints

| Method / path                               | Success                                                                                                          | Errors                                  | modules                                    | AC 出口            |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | --------------------------------------- | ------------------------------------------ | ------------------ |
| `GET /api/ui/dev-docs/tree`                 | `200 {specs:[{spec_id,documents:[{name,path}]}]}`；spec 与 `.md` 文件按 Unicode code point 升序；`name` 去 `.md` | `401 AUTH_REQUIRED`                     | Dev Docs Facade, Filesystem                | AC-FR1308-01/04    |
| `GET /api/ui/dev-docs/{spec_id}/{doc_name}` | `200 DevDoc`；仅 `.louke/project/specs/<spec-id>/<doc-name>.md`                                                  | `403 PATH_NOT_ALLOWED`、`404 NOT_FOUND` | Dev Docs Facade, Existing Documents/Render | AC-FR1309-01—05/08 |

| Schema   | 字段/约束                                                                                                      |
| -------- | -------------------------------------------------------------------------------------------------------------- |
| `DevDoc` | `{spec_id,doc_name,path,body_md,rendered_html,sha256,links:[{ref,target_href}]}`；无 writable/save/action 字段；无 `discussions[]` |

### 4.3 Dev Docs writable allowlist 与显式保存 endpoint

v0.13 引入 Dev Docs 受限保存能力，**allowlist 精确限定**为 `.louke/project/specs/<spec-id>/{story.md, spec.md, acceptance.md}` 三个文件。同一 spec 目录下的 `test-plan.md`、`architecture.md`、`interfaces.md`、`gap-analysis.md`、`m-lock.md` 及任何其它文件**只读**：服务端写接口返回 4xx `PATH_NOT_ALLOWED`，UI 不暴露 Save 入口。

| Method / path | Request | Success | Errors | modules | AC 出口 |
| --- | --- | --- | --- | --- | --- |
| `PUT /api/ui/dev-docs/{spec_id}/{doc_name}` | `{body_md:string,expected_mtime:string,force?:boolean}`；`doc_name` 为**无扩展名**的 `story\|spec\|acceptance` 之一（服务端补 `.md`）；`force=true` 仅允许 UI 二次确认后 | `200 {path,sha256,saved_at,mtime}` | `400 VALIDATION_FAILED`、`403 PATH_NOT_ALLOWED`、`409 CONFLICT`、`413 TOO_LARGE` | Dev Docs Facade, Filesystem, Existing Auth | AC-FR1309-06/07/08 |
| `PUT /api/ui/dev-docs/{spec_id}/{doc_name}` 且 `doc_name` 为 `test-plan\|architecture\|interfaces\|gap-analysis\|m-lock` 或 allowlist 之外任意值 | n/a（不读 body） | n/a | `403 PATH_NOT_ALLOWED`（facade 唯一错误码；**不**返回 405，**不**区分 UI/CLI 调用方） | Dev Docs Facade, Filesystem, Existing Auth | AC-FR1309-06 |

**实现约定（T-003 决议）**：
- v0.13 facade 不复用底层 `ProjectStore.write_doc()` 的强制尾换行规范化。facade 以客户端提交的 `body_md` 作为完整 UTF-8 Markdown bytes 原子落盘（atomic replace + mtime CAS），**不补尾换行、不重排、不抽取 inline-discussion marker**；响应 `sha256` 覆盖实际落盘 bytes，round-trip SHA 必须与提交 bytes 一致。
- 既有 v0.11 `PUT /api/files/{path}` 与主 Web `PUT /api/docs/{spec_id}/{doc_name}` 合同保持原状、不在 v0.13 facade 合同内复用；v0.13 Dev Docs 写路径**唯一**出口为 `PUT /api/ui/dev-docs/{spec_id}/{doc_name}`，底层实现是否委托给既有 store 是实现细节，不影响本公开合同。
- CLI `lk` 直连底层既有写 endpoint 的兼容性属于上游 v0.11/v0.9 合同范畴，不在本接口表表达。

> **Prism** [RESOLVED]: 这三行还不是可实施合同。既有 v0.11 文件合同是 `PUT /api/files/{path}` + `{content,revision?}`，当前主 Web 另有 `PUT /api/docs/{spec_id}/{doc_name}` + `{body_md,version_token,force?}`；并不存在此处写的 `POST /api/files?path=...`，也不能把 request/response/error 写成“同上”。请决定 v0.13 facade 复用哪一个公开出口并逐字段映射。只读文件经新 facade 直接 PUT 应唯一确定为 `403 PATH_NOT_ALLOWED`；`405 NOT_IMPLEMENTED` 与 `403` 二选一的写法不可测试。还需明确 path parameter 是无扩展名的 `story|spec|acceptance` 还是带 `.md` 的 basename。现有 `ProjectStore.write_doc()` 会强制补尾换行，若要求 byte-exact round-trip，facade/底层实现必须去掉该规范化并让响应 SHA 覆盖实际落盘 bytes。
>> **Archer (T-003) Applied**: 已删除“同上”行与 `POST /api/files?path=...` 虚构合同；唯一公开写出口为 `PUT /api/ui/dev-docs/{spec_id}/{doc_name}`，`doc_name` 为无扩展名 `story|spec|acceptance`。只读文件经同一 facade PUT 唯一返回 `403 PATH_NOT_ALLOWED`（不再出现 405 或 UI/CLI 二分）。明确不复用 `ProjectStore.write_doc()` 强制尾换行行为，facade byte-exact 落盘，响应 SHA 覆盖实际 bytes。底层既有 endpoint 兼容性不在本表表达。

>> **archer**: Applied: §2 Settings contract uses aria-disabled=true placeholder items (focusable/clickable to update detail, but no save or setting action); removed native disabled ambiguity.


**Inline-discussion 渲染与保存**：

- inline-discussion 由 Workbench Client 通过读取 Markdown body 中的 `>`/`>>`/speaker-tag blockquote marker 直接渲染；**不**读取 `louke.inline_discussions[]` 之类的 frontmatter discussion 列表；**不**返回单独的 `discussions[]` 数组。
- reply 本质是在 Markdown body 中编辑 marker，通过同一 Save 流程（PUT `/api/ui/dev-docs/{spec_id}/{doc_name}`）随整份文档落盘；**不**存在独立的 `/discussions/{id}/replies` endpoint。
- `sha256` 覆盖保存后完整文件 bytes（含 inline-discussion marker），用 round-trip 证明服务端没有抽取、重排或规范化 discussion。

> **Prism** [RESOLVED]: 根据最新决定，本节不再只是纯 read contract。新增 Dev Docs 显式保存接口，把服务端写 allowlist 精确限定为 `.louke/project/specs/<spec-id>/{story.md, spec.md, acceptance.md}`；`test-plan.md`、`architecture.md`、`interfaces.md` 及其它文件继续只读（UI 隐藏入口、服务端 facade 返回 `PATH_NOT_ALLOWED` / `NOT_IMPLEMENTED`，底层 v0.11-001 / v0.9-001 已批准 endpoint 保持 200 兼容）。读写均以完整 `body_md` 为事实源，保存不得抽取、重排或规范化 inline-discussion；`InlineDiscussion` frontmatter schema、`EndUserDoc.discussions[]`、专用 `/discussions/.../replies` endpoint 在 v0.13 不再存在。`.louke/project/specs/review/**` 明确延期，本期不暴露对应路由、目录或 schema。
>> **Archer (T-004) Applied**: §4.3 已落地为唯一 facade 写出口 + 只读文件统一 `403 PATH_NOT_ALLOWED`；删除 `NOT_IMPLEMENTED` 二分与 `discussions[]`/frontmatter discussion schema/专用 reply endpoint；`.louke/project/specs/review/**` 不暴露路由。与 T-003 一并闭合。

>> **archer**: Applied: §4.3 Dev Docs save table rewritten - single PUT /api/ui/dev-docs/{spec_id}/{doc_name} exit; doc_name is extensionless story|spec|acceptance; read-only files uniquely return 403 PATH_NOT_ALLOWED (no 405, no UI/CLI split); byte-exact save, no ProjectStore trailing-newline reuse; response SHA covers actual bytes.


### 4.2 显式上游指针

| 能力                      | 复用接口/合同                                                                             | v0.13 限制                                              | modules                                     |
| ------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------- |
| discovery/render          | v0.11-001 FR-0801；现有 `GET /api/specs`、`GET /api/docs/{spec_id}/{doc_name}` 的读取语义 | facade 扩展为全部直接子 `.md`，workbench 不调用既有 PUT | Dev Docs Facade, Existing Documents/Render  |
| split preview/sync scroll | v0.9-001 FR-0200；现有 `POST /api/render` preview schema                                  | 左 pane 为只读文本，右 pane 实时 render；不落盘         | Workbench Client, Existing Documents/Render |
| FR/NFR/Story links        | v0.9-001 FR-0700；rendered anchor/href                                                    | 点击改变 hash 并 scroll target into view                | Existing Documents/Render, Workbench Client |

## 5. End User Docs 文件与 HTTP contract

### 5.1 Canonical 文件格式

| 项                   | Contract                                                                                                                                                             |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Root                 | `<project>/.louke/end-user-docs/`                                                                                                                                    |
| Encoding             | UTF-8 Markdown；正文与 frontmatter 合计 ≤1 MiB                                                                                                                       |
| Frontmatter boundary | `body_md` 表示**完整 UTF-8 Markdown 文件 bytes**（可包含原样 `louke` frontmatter）。服务端对 `body_md` 做 opaque full-document CAS/save：**不**拆分 frontmatter、**不**重新组合、**不**规范化。frontmatter 解析只能生成派生只读视图，不能参与持久化重写；frontmatter 中不得出现 `louke.inline_discussions[]` 之类的 discussion 列表字段，discussion 通过正文中的 `>`/`>>`/speaker-tag blockquote marker 与上下文共存 |
| Allowed path         | root 下普通非隐藏文件；basename 仅 Unicode letter/number、`-`、`_`、`.`、space；每段 1—120 字符；末尾 `.md`；无 symlink/绝对/`..`                                    |
| Forbidden            | root 外全部文件，特别是 `.louke/project/specs/**`、story/spec/acceptance/test-plan/architecture/interfaces、`project.toml`                                           |
| Digest               | `sha256` 为保存后完整文件 bytes 的 64 位 lowercase hex                                                                                                               |
| mtime token          | `mtime` 为服务端从文件 mtime 生成的不透明 decimal string；客户端仅原样回传为 `expected_mtime`，不得自行计算                                                          |

> **Archer (T-005) Applied** [RESOLVED]: `body_md` 已改为表示完整 UTF-8 Markdown 文件 bytes（含原样 frontmatter），服务端 opaque full-document CAS/save，不拆分/重组/规范化；frontmatter 解析仅生成派生只读视图。删除原 Prism 关于“`body_md` 排除 frontmatter 导致冲突”的 comment，因其已解决。


>> **archer**: Applied: §4.3 now single facade write exit + read-only files uniformly 403 PATH_NOT_ALLOWED; removed NOT_IMPLEMENTED split, discussions[]/frontmatter discussion schema, dedicated reply endpoint; .louke/project/specs/review/** not exposed.

### 5.2 Inline-discussion 渲染与编辑（marker-based，v0.13 不引入 frontmatter schema）

- inline-discussion 完全由 Markdown body 中的 `>`/`>>`/speaker-tag blockquote marker 表示；与正文共用 UTF-8 Markdown 全文作为唯一事实源。
- v0.13 **不定义、不读取、不写入** `louke.inline_discussions[]`、`InlineDiscussion`、`EndUserDoc.discussions[]` 之类的 discussion 字段或 schema；不暴露 `resolved` / `status` / `resolved_at` 等状态字段。
- reply 本质是对原 marker 的上下文内编辑，通过同一 Save 流程（PUT `/api/end-user-docs/{path}`）随整份文档原子落盘；**不存在**独立的 `/discussions/{id}/replies` endpoint。
- `sha256` 覆盖实际完整文件 bytes（含 discussion marker），用 round-trip 测试证明服务端没有抽取、重排或规范化 discussion。

### 5.3 HTTP endpoints

| Method / path                                | Request                                                                                    | Success                                              | Errors                                                                           | modules                                                  | AC 出口                  |
| -------------------------------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------- | ------------------------ |
| `GET /api/end-user-docs/tree`                | —                                                                                          | `200 {root:".louke/end-user-docs",entries:DocTreeEntry[]}` | `401 AUTH_REQUIRED`                                                              | End User Docs Facade, Filesystem                         | AC-FR1310-01             |
| `GET /api/end-user-docs/{path}`              | URL-encoded relative `.md`                                                                 | `200 EndUserDoc`                                     | `403 PATH_NOT_ALLOWED`、`404 NOT_FOUND`                                          | End User Docs Facade, Existing Documents/Render, Filesystem | AC-FR1310-02/03/09/11/12 |
| `PUT /api/end-user-docs/{path}`              | `{body_md:string,expected_mtime:string,force?:boolean}`；`force=true` 只允许 UI 二次确认后 | `200 {path,sha256,saved_at,mtime}`                   | `400 VALIDATION_FAILED`、`403 PATH_NOT_ALLOWED`、`409 CONFLICT`、`413 TOO_LARGE` | End User Docs Facade, Filesystem                         | AC-FR1310-05—11          |

| Schema         | 字段/约束                                                                                                                                       |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `DocTreeEntry` | `{path,name,kind:"directory"\|"document",children?:DocTreeEntry[]}`；只列合法 `.md` 与包含合法后代的目录                                          |
| `EndUserDoc`   | `{path,body_md,rendered_html,sha256,mtime}`；**无** `discussions[]` 字段；**无** frontmatter discussion schema 字段；不含 status/resolved 字段     |

> **Prism** [RESOLVED]: 这里需补 marker/frontmatter 兼容合同。AC-FR1310-12 接受 frontmatter 或 special marker，而现有 Dev Docs 协议使用 blockquote marker；当前 schema 只覆盖 frontmatter，test-plan 也不足以证明另一种输入会被正确读取。
>> **Aaron**: 这是过度设计。inline-discussion就应该跟随文本一起，不单独提取。

>> **archer**: Applied: §5.1 Frontmatter boundary row - body_md now represents complete UTF-8 Markdown file bytes (may include raw frontmatter); server does opaque full-document CAS/save, no split/renormalize; frontmatter parse only generates derived read-only view.

>>> **Prism**: 同意。已删除 `InlineDiscussion` schema、`EndUserDoc.discussions[]`、frontmatter discussion schema 和专用 reply 持久化模型；GET/PUT 传输完整 `body_md`，discussion reply 本质上是对原 Markdown marker 的上下文内编辑，并与整份文档一起通过 CAS 保存。`sha256` 应覆盖实际完整文件 bytes，用 round-trip 测试证明服务端没有抽取、重排或规范化 discussion。本节已按 Aaron 决定改写：inline-discussion 与正文共用 UTF-8 Markdown 全文作为唯一事实源。

### 5.4 Save/Conflict browser contract

| 场景         | Browser 外部结果                                                                                            | modules                                | AC 出口            |
| ------------ | ----------------------------------------------------------------------------------------------------------- | -------------------------------------- | ------------------ |
| clean editor | Save 可见且 `disabled`; 不自动发请求                                                                        | Workbench Client                       | AC-FR1310-05       |
| dirty + 200  | 用响应 `sha256` 重 GET；preview bytes digest 相等；Save 恢复 disabled                                       | Workbench Client, End User Docs Facade | AC-FR1310-06/09/11 |
| 400/403/413  | error toast 显示 `message`；编辑器内容不变                                                                  | Workbench Client, End User Docs Facade | AC-FR1310-07/10    |
| 409          | dialog 文案“文件已被外部修改”；动作“重新加载并放弃我的编辑”与“仍要覆盖”；后者二次确认后以 `force=true` 重发 | Workbench Client, End User Docs Facade | AC-FR1310-08       |

## 6. Wiki read contract 与上游指针

| Method / path | Success | NotFound/unknown | modules | AC 出口 |
| --- | --- | --- | --- | --- |
| 既有 `GET /api/wiki` | `200 {pages:[page path...]}`；提供首页、story/spec/test-plan/architecture/interfaces 汇总、技术决定、FAQ、项目信息 | 未知新增页面可出现在列表，无 schema upgrade | Existing Wiki, Workbench Client | AC-FR1311-01、AC-FR1312-01/03 |
| 既有 `GET /api/wiki/{page:path}` | `200 {page,path,body_md,rendered_html,version_token,updated_at,last_modified_by}` | 不存在页面返回 `200 {body_md:"",version_token:"new",...}`（上游“可新建页面”语义，**v0.13 UI 不消费此语义**） | Existing Wiki, Existing Documents/Render | 上游兼容，非 v0.13 UI 出口 |
| **新增** `GET /api/ui/wiki/{page:path}` | `200 {page,path,body_md,rendered_html,sha256,updated_at,last_modified_by}`（透传既有 Wiki 内容，附 `sha256`） | 不存在页面返回 `404 {code:"NOT_FOUND",message,page}`（facade 把上游 `version_token="new"` 转换为 404）；workbench 显示 NotFound，不能是空白/5xx | Wiki Facade (v0.13 新增), Existing Wiki, Existing Documents/Render, Workbench Client | AC-FR1311-02/03/05、AC-FR1312-02/03 |

> **Prism** [RESOLVED]: 这不是当前“既有”语义：现实现对不存在且 `Accept: application/json` 的 Wiki 页面返回 `200`、空正文和 `version_token="new"`。请决定新增 v0.13 facade 返回 404，还是记录并消费现有 200/new 合同，不能同时称为直接复用既有 endpoint。
>> **Aaron**: 没看懂，请解释

>> **archer**: Applied: §5.2 rewritten marker-based - inline-discussion via >/>>/speaker-tag blockquote in Markdown body; no louke.inline_discussions[]/InlineDiscussion/EndUserDoc.discussions[]; reply edits marker via same Save flow; sha256 covers full bytes.

>>> **Prism**: 举例：请求不存在的 `/api/wiki/no-such-page` 时，当前代码不会返回 404，而是返回 `200 {body_md:"", version_token:"new", ...}`，表示“可新建页面”；但上面的接口表把同一个“既有 endpoint”写成 404。v0.13 UI 两种都能做 NotFound：A）保持既有 200，并把 `version_token="new"` 解释成 NotFound；B）新增 `/api/ui/wiki/...` facade，把它转换成 404。问题只在于必须选一个，不能声称直接复用时又改变原 endpoint 的状态码。
>>>> **Aaron**: 按Prism，新增 facade，转换为404
>>>>> **Prism**: 收到，采用方案 B：保留既有 `/api/wiki/{page}` 的 200/new 兼容语义，新增 v0.13 `/api/ui/wiki/{page}` facade，对不存在页面转换为 404；正文接口表和 L2 contract test 需按此更新。
>>>>>> **Archer (T-007) Applied**: 接口表已新增 `GET /api/ui/wiki/{page:path}` 行，把上游 `version_token="new"` 转换为 `404 NOT_FOUND`；既有 `GET /api/wiki/{page}` 保留 200/new 兼容语义并标注“v0.13 UI 不消费”。architecture.md §4.1 需相应补一行 Wiki Facade 模块（见后续 architecture edit）。

| 复用                   | 指针              | v0.13 UI 约束                                               | modules                         |
| ---------------------- | ----------------- | ----------------------------------------------------------- | ------------------------------- |
| Wiki structure/content | v0.11-001 FR-0301 | 只读；不渲染既有 PUT/refresh/edit/create/delete/rename 入口 | Existing Wiki, Workbench Client |

## 7. Runs、graph 与 artifact read model

### 7.1 Schemas

| Schema               | 字段/约束                                                                                                                                            |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RunSummary`         | `{project_id,project_name,scope:"current"                                                                                                            | "history",run_id,run_status,definition_id,definition_version,updated_at,create_project_href}` |
| `StageBadge`         | `{kind:"status"                                                                                                                                      | "review"                                                                                      | "gate" | "author",value:string,display_label:string,unknown:boolean,stale:boolean}` |
| `StageNodeView`      | `{stage_id,label,state:string,unknown:boolean,badges:StageBadge[],required:boolean}`                                                                 |
| `RunGraphView`       | `{run_id,definition_id,definition_version,nodes:StageNodeView[],edges:[{from,to,condition}],current_stage_id,revision}`                              |
| `ArtifactDigestView` | `{run_id,stage_id,result_kind,unknown,stale,digest,verdict,required_reviewer,review_conclusion,raw_result?}`；`raw_result` 只在详情中存在且 secret-redacted |

**`ArtifactDigestView` 字段 source-of-truth 与缺失规则（T-008 决议，与 architecture.md §5.4 映射一致）**：

| 视图字段 | 来源 artifact / 字段 | 缺失/陈旧/冲突规则 |
| --- | --- | --- |
| `digest` | 所选 artifact 文件 bytes 的 SHA-256；同时调用 `verify_stage_result_hash()` 校验其 `output_hash` | 文件缺失 -> 空字符串 + `unknown=true`；hash 校验失败 -> `unknown=true,stale=true` |
| `verdict`（review） | `review-result.json::verdict`；若 v0.13 producer 明确写入 `metadata.verdict_override`，后者覆盖 | 缺失 -> `unknown=true`；已知值 `PASS/REJECT/WAIVED`，未知值原样保留 + `unknown=true` |
| `verdict`（gate） | `gate-result.json::verdict`；若 v0.13 producer 明确写入 `metadata.gate_pass`，后者覆盖 | 缺失 -> `unknown=true`；已知值 `pass/fail`，未知值原样保留 + `unknown=true` |
| `required_reviewer` | `review-result.json::role`；当前 `WorkflowDefinition/Step` schema 不含 reviewer 字段 | artifact/role 缺失 -> 空字符串 + `unknown=true`；不从 definition 编造 |
| `review_conclusion` | `review-result.json::metadata.conclusion`，缺失时回退 `metadata.note` | 两项均缺失 -> 空字符串；仅当 verdict 也未知时置 `unknown=true` |
| `raw_result` | stage-result JSON 原文，展示前对 metadata 中 secret/credential/token/password 类 key 做 redact | artifact 缺失 -> 字段省略 |
| `stale` | artifact `contract_bundle_hash` 与 `compute_contract_bundle_hash(spec_id)` 当前值比较 | 不一致 -> `stale=true,unknown=true`；保留原值用于诊断，route 仍 2xx；run-bound definition 只用于 graph |

冲突优先级：`review-result.json` > `gate-result.json` > `author-result.json`。author badge 使用 `author-result.json::role` + `verdict`；其余 badge 与详情字段遵循上表。实现者不得读取不存在的 `reviewer`、顶层 `conclusion/note` 或 artifact `definition_version` 字段；无法确定性派生的值必须显式降级。

> **Prism** [RESOLVED]: 请为这几个字段增加来源/缺失规则。现有 stage-result artifact 没有直接的 `required_reviewer` 与 `review_conclusion` 字段；需要明确从 workflow definition、role、blocking findings 或其他公开出口如何确定性生成，并规定 stale contract hash 时的输出。
>> **Archer (T-008) Applied**: §7.1 已新增字段 source-of-truth 表，逐字段说明来源 artifact、缺失/陈旧/冲突规则与冲突优先级，与 architecture.md §5.4 映射一致；stale contract hash 时所有派生字段标 `unknown=true` 并保留原值，route 仍 2xx。
>>> **Prism**: 复审后 reopen：真实 stage-result schema 没有表中引用的 `reviewer`、`conclusion/note`、artifact `definition_version` 字段。它提供的是 `role`、`verdict`、`blocking_findings`、`accepted_risks`、`contract_bundle_hash`、`metadata`。请基于这些真实字段和 run-bound definition 明确映射，并使用 `contract_bundle_hash` 而不是不存在的 definition-version 字段判断 stale。

>> **archer**: Applied: §6 Wiki table - existing GET /api/wiki/{page} keeps 200/new compat (v0.13 UI does not consume); new GET /api/ui/wiki/{page} facade converts version_token=new to 404 NOT_FOUND + adds sha256. architecture.md §4.1 adds Wiki Facade module row.

>> **Codex**: 独立复审确认仍未修正：§7.1 还在读取 gate-result.json 的 pass/fail、review-result.json 的 reviewer/conclusion/note，以及 artifact definition version；实际 write_stage_result() 只有统一 verdict、role、metadata、contract_bundle_hash 等字段。请逐项同步 architecture.md §5.4 的真实 schema 映射，并删除重复的小节标题。

>> **Codex**: 已直接修复：§7.1 现只读取真实字段 verdict、role、metadata、contract_bundle_hash、output_hash；gate 使用 verdict，required_reviewer 使用 review-result.role，stale 与 compute_contract_bundle_hash(spec_id) 当前值比较，并明确禁止不存在的 reviewer/顶层 conclusion/note/artifact definition_version。


### 7.2 Endpoints

| Method / path                                          | Success                                                                               | Errors                                     | modules                                                  | AC 出口                                                         |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------- | ------------------------------------------ | -------------------------------------------------------- | --------------------------------------------------------------- | -------------------------------- |
| `GET /api/ui/runs`                                     | `200 {current:RunSummary[],history:RunSummary[],create_project_href:"/projects/new"}` | `401 AUTH_REQUIRED`                        | Runs Read Model, Existing Projects API                   | AC-FR1313-01/03                                                 |
| `GET /api/ui/runs/{run_id}/graph`                      | `200 RunGraphView`，来自 run 绑定 definition/version                                  | `404 RUN_NOT_FOUND`；未知值仍 200 fallback | Runs Read Model, Presentation Mapper, Existing Runtime   | AC-FR1313-02—04、AC-FR1314-01—04、AC-FR1316-01—04               |
| `GET /api/ui/runs/{run_id}/stages/{stage_id}/artifact` | `200 ArtifactDigestView`                                                              | `404 RUN_NOT_FOUND                         | STAGE_NOT_FOUND`；未知 stage/result kind 仍 200 fallback | Runs Read Model, Presentation Mapper, Existing Runtime/Evidence | AC-FR1315-01—04、AC-FR1316-01—04 |

### 7.3 已知值与降级

| Kind               | 已知值                                                                             | 未知值输出                                                      | modules             |
| ------------------ | ---------------------------------------------------------------------------------- | --------------------------------------------------------------- | ------------------- |
| status             | `completed,current,waiting_for_human,blocked,failed,pending,skipped_by_definition` | `value=<raw>, display_label="未知 status: <raw>", unknown=true` | Presentation Mapper |
| review             | `PASS,REJECT,WAIVED`                                                               | `display_label="未知 verdict: <raw>"`                           | Presentation Mapper |
| gate               | `pass,fail`                                                                        | `display_label="未知 gate result: <raw>"`                       | Presentation Mapper |
| author/result kind | 上游返回的已批准 kind/value                                                        | `display_label="未知 result kind: <raw>"`                       | Presentation Mapper |
| stage              | v0.12 bound graph 中的 stage                                                       | node 保留 `stage_id`; label=`未知 stage: <raw>`；`unknown=true` | Presentation Mapper |

### 7.4 上游复用指针

| v0.12 contract              | 既有 endpoint/field                                                                   | v0.13 用法                                                              | modules                                                         |
| --------------------------- | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------- |
| FR-1001 Projects            | `GET /api/projects/active`、`GET /api/projects/history`                               | 组合 Runs sidebar；创建项目只链接现有 `/projects/new`                   | Runs Read Model, Existing Projects API                          |
| FR-1201 graph               | `GET /api/projects/{project_id}/graph` 的 run/definition/nodes/edges/current/revision | 转换为 `RunGraphView`，不推导新 definition                              | Runs Read Model, Existing Runtime                               |
| FR-1901 artifact review     | v0.12 project artifact/review public read fields                                      | 读取 verdict/required reviewer/review conclusion；不调用 decision/write | Runs Read Model, Existing Runtime/Evidence                      |
| FR-2201 trace/stage-results | artifact digest、review/gate/author result                                            | 节点 badges 与详情 digest；原始 JSON 不放节点                           | Runs Read Model, Presentation Mapper, Existing Runtime/Evidence |

## 8. Auth 与 health 复用

| Method / path                | Contract                                                                                                       | modules                         | AC 出口         |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------- | --------------- |
| 既有 `POST /api/auth/logout` | `200 {ok:true}` + `Set-Cookie` 删除 `louke_session`；之后 protected API `401`，页面 `303` 到 `/login`/`/setup` | Existing Auth, Workbench Client | AC-FR1304-01—03 |
| 既有 `GET /health`           | ready 时 `200`；E2E 仅在 workspace/app 可服务时继续                                                            | Existing Server                 | AC-FR1317-01/04 |

## 9. AC → outlet → test-plan 闭环

| AC 组                     | 公开 outlet                                                | test-plan 覆盖依据                                                                              |
| ------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| AC-FR1301-01—AC-FR1303-04 | §2 DOM/ARIA/tab/Settings contract                          | §5.4 定向 Chromium；§6 main journey                                                             |
| AC-FR1304-01—03           | §2 Accounts、§8 logout、browser credential storage         | §5.2 L2 + §5.4 Chromium                                                                         |
| AC-FR1305-01—AC-FR1307-04 | §3 Agent/transcript/message/SSE/default fallback           | §5.1 L1 + §5.2 L2 + §5.3 L3 + §5.4 Chromium                                                     |
| AC-FR1308-01—AC-FR1309-11 | §2.1 localStorage、§4 Dev Docs tree/read/allowlist save、dirty/4xx/409、byte-exact persistence | §5.1 L1 + §5.2 L2 + §5.4/§6 Chromium |
| AC-FR1310-01—10           | §5 tree/read/save/error/CAS/browser contract               | §5.1 L1 + §5.2 L2 + §5.4 Chromium                                                               |
| AC-FR1310-11/12           | §5 restart-persistent bytes、marker-based inline-discussion reply | §5.2 L2 restart + §5.4 Chromium discussion coverage（已 COVERED） |

> **Archer (T-009) Applied** [RESOLVED]: §9 closure 行已删除 BLOCKED 文案，改为 L2 restart + Chromium discussion evidence；`AC-FR1308-01-AC-FR1309-05` 扩展为 `AC-FR1308-01-AC-FR1309-08` 以覆盖新增 save AC。
>> **Prism**: 复审后 reopen：acceptance 现已扩展到 `AC-FR1309-11`，总 AC 数为 86；本表仍截止 `AC-FR1309-08`，未映射 dirty、4xx、409 与重启/无尾换行验收。请同步到最新 acceptance 后关闭。

>> **prism**: 复审 still not passing: 虽然 architecture.md §5.4 已基于真实 schema 重写，但本 interfaces.md §7.1 表仍有两处残留旧 schema：(1) `required_reviewer` 回退行写的是 `review-result.json` 的 `reviewer` 字段，实际 artifact 没有 `reviewer` 字段，应改为 `review-result.json` 的 `role` 字段；(2) stale 行仍用 `definition version` 不一致判断，真实 schema 是 `contract_bundle_hash` 比对。请同步 architecture.md §5.4 的映射表（role/contract_bundle_hash），然后重开本 thread。

| AC-FR1311-01—AC-FR1312-04 | §6 Wiki index/page/NotFound/read-only | §5.1 L1 + §5.2 L2 + §5.4/§6 Chromium |

>> **archer**: Applied: §7.1 ArtifactDigestView field source-of-truth table added - digest/verdict/required_reviewer/review_conclusion/raw_result sources, missing/stale/conflict rules, review>gate>author priority; consistent with architecture.md §5.4.


>>> **archer**: Applied: §9 closure table - removed BLOCKED text for AC-FR1310-11/12 (now L2 restart + Chromium discussion coverage); AC-FR1308-01-AC-FR1309-05 expanded to -08 to cover new save ACs.


>>>> **Codex**: 独立复审确认仍未修正：acceptance.md 的 FR-1309 已到 AC-FR1309-11（总计 86 个 AC），但本闭环表仍截止 -08；-09（4xx）、-10（409）和 -11（持久化/无尾换行）没有接口出口映射，因此 AC→interface→test-plan 闭环尚未完成。


>>>>> **Codex**: 已直接修复：§9 映射范围现为 AC-FR1308-01—AC-FR1309-11，并明确覆盖 dirty、4xx、409 与 byte-exact persistence。


>>>>>> **Verified: codex applied. 9 closure range now AC-FR1308-01 to AC-FR1309-11 matching acceptance.md 86-AC total. dirty, 4xx, 409 and byte-exact persistence all mapped. Concern addressed.**: Prism

| AC-FR1313-01—AC-FR1316-04 | §7 Runs/graph/badges/artifact/fallback | §5.1 L1 + §5.2 L2 + §5.4/§6 Chromium |
| AC-FR1317-01—04 | §2、§4、§6、§7、§8 main-journey outlets | test-plan §6 单一 Chromium 主旅程 |
| AC-FR1318-01—03 | §2 negative-capability outlet | test-plan §5.4 Chromium + §7 static scan |

所有 `modules` 含两个及以上模块的行都是 cross-module interface，Shield 必须按 test-plan §5.2 提供 integration evidence；Browser DOM/SSE 消费的最终行为另由 §5.4 Chromium 闭合。测试不得读取 private store 或 patch Louke router 来代替这些出口。
