---
status: Locked — M-LOCK Approved; M-DEV Not Started
spec_id: v0.12-001-programmatic-workflow-runtime
created: 2026-07-13
locked: true
---

# Programmatic Workflow Control — External Interfaces Contract

## 1. 使用规则

本文只定义调用者和测试可观察的 contract；不暴露类层级、状态机实现、数据库表、缓存、私有方法或调度细节。所有时间为 RFC 3339 UTC，所有 ID 为不透明字符串。写操作的成功响应包含新的 `revision`；调用者须带最近读取到的 `expected_revision`，否则返回 `revision_conflict`。

所有 JSON 错误使用：

```json
{"error":{"code":"gate_digest_mismatch","message":"human-readable explanation","details":{"expected_digest":"…"},"correlation_id":"…"}}
```

`details` 不得包含 credential、secret 或未获授权的 artifact 内容。接口只监听 loopback，所有改变状态的 endpoint 要求已认证 local human session 与 CSRF token；审计中会显示 actor 类型与 ID。

## 2. Runtime、setup 与启动入口

### 2.1 CLI contract

| 入口 | 成功的外部结果 | 失败的外部结果 |
| --- | --- | --- |
| `lk init` | 创建或显示最小 workspace，输出 `workspace_root`、选择的 `runtime_identity`、下一步 setup URL；必要时以所选 runtime controlled restart | 不写半成品 lock；返回可修复项目和命令 |
| `lk adopt --preview` | 仅输出 legacy scan、可迁移项目、不可解释状态、拟写入内容；不改变任何文件 | 以非零退出显示读取/兼容错误 |
| `lk adopt --apply <preview-id>` | 输出 migration id、备份/rollback reference 和 legacy summary | preview stale、未确认或兼容失败时不迁移 |
| `lk serve` | 输出 resolved runtime identity 与 loopback URL；setup-only workspace 也能启动 setup wizard | local runtime 不可验证或 global 不兼容时非零退出，不自动改用另一个 runtime |
| `lk runtime install|repair|upgrade` | 输出本 workspace 的 old/new identity、integrity/compatibility result 和 restart requirement | 不影响其他 workspace；失败时保留上一个可验证 identity |

### 2.2 Runtime identity view

`GET /api/runtime`、CLI 输出和 child-launch audit 都使用同一 schema：

```json
{
  "workspace_root":"/absolute/path",
  "mode":"local",
  "runtime_identity":{"package":"louke","version":"0.12.0","build":"…","artifact_digest":"sha256:…","schema_compatibility":"v12"},
  "source":"nearest_workspace",
  "status":"ready",
  "repair_action":null
}
```

`mode` 为 `local` 或 `global`。`status=blocked` 必须带 `repair_action`；声明 local 时缺少/损坏/不匹配 artifact 的 response 绝不可显示 global identity。所有由本 server 创建的 session/task 视图都回显同一 `runtime_identity`。

### 2.3 Setup/readiness

`GET /api/setup/readiness` 返回按项数组：

```json
{"items":[{"key":"workspace","status":"ready|blocked|action_required","summary":"…","repair_action":"…"}],"first_user":{"status":"missing|ready"}}
```

项至少覆盖 workspace/runtime、workflow catalog、authenticated human、OpenCode、可用 provider/model、当前 workflow 要求的 integrations。`POST /api/setup/first-user` 接受本地账户初始化字段，成功后不回显密码或 session secret。`GET /setup` 必须在 setup 不完整时可访问，而项目创建 API 返回 `setup_incomplete` 并列出未满足项。

## 3. Catalog、project 与 workflow run

### 3.1 可读 catalog

`GET /api/workflow-definitions` 返回可选择 definition 列表。每项含：

```json
{"definition_id":"new_feature","version":"1","label":"New feature","entry_requirements":["setup_ready"],"supported":true}
```

`GET /api/workflow-definitions/{id}/{version}` 额外返回 public graph（见 §4）和 `responsibility_inventory` summary。若 inventory 未覆盖、分类无效、handler/prompt contract 不一致，catalog 不可选择且 `GET /api/setup/readiness` 报 `catalog_invalid`；不得创建 run。

### 3.2 Project collection 与创建

`GET /api/projects?scope=active|history|all` 返回 `ProjectSummary[]`：

```json
{
  "project_id":"prj_…","name":"…","story_excerpt":"…","release_version":"v0.12.0",
  "workflow":{"definition_id":"new_feature","version":"1"},
  "run_id":"run_…","run_status":"waiting_for_human","current_step":"requirements_approval",
  "updated_at":"…","archived_at":null,"runtime_identity":{"version":"0.12.0","mode":"local"}
}
```

`POST /api/projects` 接受 `story`、`release_version`、`workflow_definition_id`、`workflow_version` 和可选 `source_contract`（bug fix 必需）。服务端验证 workflow、release 格式、setup 及 bug fix source evidence；成功创建的 run 已绑定 definition/version/runtime identity，响应 `201` 及 `ProjectDetail`。调用者不能提交 stage、current step、gate 状态或任意 shell 命令。

`GET /api/projects/{project_id}` 返回下列只读组合视图：`project`、`run`、`current_step`、`blocked_reason`、`next_actions`、`workflow_graph`、`gates`、`artifacts`、`sessions`、`recent_events`、`trace_summary`、`revision`。active/history 都可读取；archive 项目的 `next_actions` 为空。

## 4. 工作流图、动作和 gate

### 4.1 Graph view

`GET /api/projects/{id}/workflow-graph` 返回：

```json
{
  "definition":{"definition_id":"bug_fix","version":"1"},"run_id":"run_…",
  "nodes":[{"id":"m_lock","kind":"human_gate","label":"M-LOCK","state":"waiting|completed|blocked|pending|skipped_by_definition","required":true}],
  "edges":[{"from":"source_contract_verify","to":"quick_rgr","condition":"validated quick branch"}],
  "current_node_id":"m_lock","revision":17
}
```

节点状态来自实际 run；`skipped_by_definition` 仅表示该 definition 声明不适用，绝不能用于跳过 requirements approval 或当前 run 的 M-LOCK。`new_feature` graph 必须含 requirements author/review/approval、test-plan author/review、architecture/interfaces author/review、M-LOCK、implementation batch、code review/权威 unit/integration、E2E、适用的 security/release、human milestone close 和 archive。验证过 source approval 的 `bug_fix` graph 可标记 requirements approval 为 `inherited`；quick path 含 Issue/source-contract、失败复现、M-LOCK、R-G-R、权威回归、release/archive，design-required 在 M-LOCK 前增加设计/review；两支都含当前 run 的 M-LOCK。

### 4.2 Action contract

`POST /api/projects/{id}/actions` 只接受由详情中的 `next_actions` 枚举出的：

```json
{"action":"retry|return_upstream|request_clarification|cancel|continue","expected_revision":17,"reason":"required for reject/cancel"}
```

成功返回更新后 `run`、`current_step`、`next_actions`、`revision` 和新 event reference。非法动作、过期 revision、未满足 gate、终态 run 分别返回 `illegal_transition`、`revision_conflict`、`gate_not_approved`、`run_terminal`。取消要求二次确认字段 `confirm_project_id`，成功时视图显示 `cancellation` event 和每个受管资源的 cleanup outcome；历史仍可读取。

### 4.3 人类门禁与 artifact review

`GET /api/projects/{id}/gates/{gate_id}` 返回 gate kind、status、bound artifact refs/digests、自动校验、变更摘要、allowed decisions、actor/reason/time（若已有决定）。

`POST /api/projects/{id}/gates/{gate_id}/decision`：

```json
{"decision":"approve|reject","bound_digest":"sha256:…","expected_revision":17,"reason":"required when reject"}
```

服务必须拒绝未认证 actor、错误 run/gate、错误或 stale digest、重复/终态 decision、requirements gate 前的设计任务以及 M-LOCK 前的开发任务。requirements gate 的 bound artifacts 正好是 story/spec/acceptance；M-LOCK 的共同 contract digest 必须同时绑定已批准的 story/spec/acceptance、已审查的 test-plan/architecture/interfaces 及其 review/validation 摘要。批准 response 包含 `gate.status=approved` 和进入的下一 node；拒绝 response 带 definition 所规定的上游返回 node。

`GET /api/projects/{id}/artifacts` 返回 artifact 的 type、revision、digest、created_by、review status、redacted display URL；`GET /api/projects/{id}/artifacts/{artifact_id}` 仅在调用者有权读取时返回内容或受控下载。内容变更创建新 revision，旧 gate 不会自动复用。

## 5. Agent-model binding、semantic task 与 OpenCode session

### 5.1 Binding 图

`GET /api/projects/{id}/agent-bindings` 返回 nodes（agent/role、effective model、provider、source default/override、availability）与 edges（仅角色关系），以及 `binding_revision`。

`PATCH /api/projects/{id}/agent-bindings` 接受一个或多个拖拽结果：

```json
{"changes":[{"agent_role":"devon","model":"provider/model"}],"expected_binding_revision":3}
```

成功建立新 override revision，返回有效图和 `effective_from="next_task"`。服务校验 model 可用且角色允许；不修改已创建/运行任务的 `model_snapshot`，不接受 workflow state 字段。

### 5.2 Semantic task / Context Manifest

`GET /api/projects/{id}/tasks/{task_id}` 返回状态、role、assigned FR/AC/issue refs、model snapshot、context manifest digest、session ref、output validation status、runtime identity 和事件引用。

`GET /api/projects/{id}/tasks/{task_id}/context-manifest` 返回经 redact 的 manifest：

```json
{"task_id":"…","run_id":"…","step_id":"…","definition_version":"…","runtime_identity":"…",
 "assignments":{"fr":["FR-2201"],"ac":["AC-FR2201-01"],"issues":["#123"]},
 "artifact_refs":[{"id":"…","digest":"sha256:…","access":"read"}],
 "permissions":{"tools":["git.read"],"write_scopes":["src/…"],"side_effects":[]},
 "model_snapshot":{"role":"devon","model":"provider/model"},
 "output_contract":"semantic-result/v1","redactions":["credentials"]}
```

manifest 是创建时的 snapshot；不得含 secret、未经授权的项目资料或隐式全仓库写权限。`POST /api/.../tasks/{task_id}/result` 只接受 output contract 所定义的结构化 result；schema、assignment、artifact digest 或允许候选不匹配返回 `semantic_result_invalid`，不能改变 workflow 状态。

### 5.3 OpenCode 生命周期

公开 session 操作：

| Endpoint | 请求 / 成功观察点 |
| --- | --- |
| `POST /api/projects/{id}/tasks/{task_id}/sessions` | 创建或恢复该 task 的受管 session，返回 `session_id`、`status=attached`、instance ref、runtime identity |
| `POST /api/sessions/{id}/detach` | 返回 `status=detached`、detach time；session 和 message history 保留 |
| `POST /api/sessions/{id}/attach` | 返回 `status=attached` 或可恢复性明确的 `session_unavailable` |
| `POST /api/sessions/{id}/messages` | 接受 message，返回 message/event ref；只允许 attached/allowed state |
| `GET /api/sessions/{id}` / `/messages` | 返回 owner task、status、lifecycle times、redacted manifest ref、message history |
| `POST /api/sessions/{id}/cancel` / `/end` | 返回终态及 cleanup result；end 后禁止再 send/attach |

服务重启后的同一 `GET` 能返回原 session 关联和实际 attachability。真实 provider 不可用不得伪装已交付；测试 adapter 必须以 `adapter_kind="contract"` 明示。

## 6. Evidence、events、历史与迁移

### 6.1 事件流

`GET /api/projects/{id}/events?after=<event_id>` 返回 append-only `WorkflowEvent[]`：

```json
{"event_id":"evt_…","run_id":"…","sequence":42,"type":"gate.approved","at":"…",
 "actor":{"kind":"human|runtime|agent","id":"…"},"correlation_id":"…",
 "from_step":"…","to_step":"…","revision":18,"artifact_refs":["art_…"],"details":{"redacted":true}}
```

必备事件类型覆盖 run 创建/恢复/冲突、step 开始/成功/失败、gate 创建/批准/拒绝、semantic dispatch/result、session lifecycle、artifact revision、trace verification、cancel/cleanup/archive、runtime/migration。sequence 单调，事件不被改写。

### 6.2 Trace ledger 与完成判定

`GET /api/projects/{id}/trace` 返回所有 FR/AC 的 ledger 条目：

```json
{"requirement":"FR-2201","acceptance":"AC-FR2201-01","task_refs":["task_…"],
 "code_evidence":[{"ref":"commit:…","status":"fresh"}],
 "test_evidence":[{"run_ref":"test_…","verdict":"pass","status":"fresh"}],
 "status":"complete|missing|failed|stale"}
```

`POST /api/projects/{id}/completion-check` 返回每条未闭合项和 `can_release` / `can_archive`。release/archive action 只在所有批准 FR/AC 都为 complete 且权威测试通过时出现在 `next_actions`；Agent 声明不构成 evidence。

### 6.3 Archive、legacy 与 runtime migration

`POST /api/projects/{id}/archive` 采用 action contract；成功之后 `GET /api/projects?scope=history` 可见不可变项目摘要、workflow graph、gates、events、trace、runtime identity。`GET /api/migrations` 与 `/api/migrations/{id}` 提供 preview/apply/rollback 的 status、legacy refs、warning 和 actor/time；未知 legacy stage 显示 `legacy_unverified`，不是 active/recoverable run。

## 7. 责任 inventory 的可审查出口

`GET /api/workflow-definitions/{id}/{version}/responsibilities` 返回 versioned inventory 的公共摘要：

```json
{"inventory_revision":"…","complete":true,"items":[
 {"subject":"foundation.ensure","kind":"program","program_effects":["preflight"],"semantic_contract":null},
 {"subject":"workflow.branch_advisor","kind":"mixed","program_effects":["candidate validation"],"semantic_contract":"branch-recommendation/v1"}
]}
```

任何 `complete=false`、未知 kind、缺少 built-in/prompt/handler subject 或 `mixed` 未同时给出两边界时，catalog/readiness 给出失败状态且 dispatch/create run 被拒绝。这既让人审查“Agent 只做语义”，也给测试提供不窥探内部结构的出口。

## 8. AC → outlet → test-plan 闭环

| AC 组 | 可观察 outlet | 测试计划章节 |
| --- | --- | --- |
| AC-FR0001-01—AC-FR0701-04 | definition/catalog、project/run view、actions、events、foundation/readiness | §5.1、§6.1 |
| AC-FR0801-01—AC-FR0901-06 | gate view/decision、artifact digest、actions/events | §5.2、§6.2 |
| AC-FR1001-01—AC-FR1301-06 | project collection/detail、graph、bindings endpoints、Projects UI | §5.3、§6.3 |
| AC-FR1401-01—AC-FR1501-06 | task/manifest/session endpoints、adapter kind、events | §5.4、§6.4 |
| AC-FR1601-01—AC-FR1701-05 | responsibility inventory、catalog validation、decision/action/events | §5.5、§6.5 |
| AC-FR1801-01—AC-FR2001-05 | setup/readiness, detail, actions, archive/events | §5.6、§6.6 |
| AC-FR2101-01—AC-FR2201-06 | graph, source-contract result, gate, trace, completion check | §5.7、§6.7 |
| AC-FR2301-01—AC-FR2401-08 | CLI output, runtime view, migrations, child/session runtime identity | §5.8、§6.8 |
| AC-NFR0001-01—AC-NFR0401-04 | actions/conflict/event/recovery, adapter kind, product UI, security error/redaction | §5.9、§6.9 |

任何新增 AC 若没有本文件 outlet，必须先扩展本合同，再写测试；测试不能读取私有 store 或 mock workflow core 来取得断言依据。
