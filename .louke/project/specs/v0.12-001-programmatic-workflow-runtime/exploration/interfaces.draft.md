# Programmatic Workflow Runtime — Interfaces Exploration Draft

> 本文件是在 M-SPEC 完成前形成的探索快照，不属于当前合同。正式接口必须在 story/spec/acceptance 经用户与 Lex 锁定后重新设计。

- **Spec ID**：`v0.12-001-programmatic-workflow-runtime`
- **Created**：2026-07-13
- **Status**：Draft
- **Base URL**：`/api/workflows`

## 1. Boundary Rule

所有 Web、CLI、测试和未来 Agent executor 都通过 `WorkflowApplicationService`。只有 `WorkflowRuntime` 可以调用 store 的写接口。

HTTP 是本期正式外部观察出口；CLI 若实现，只能是 HTTP/application service 的薄适配器，不能复制转移逻辑。

## 2. Public Schemas

### 2.1 WorkflowDefinitionSummary

```json
{
  "definition_id": "contract-bootstrap",
  "version": 1,
  "digest": "sha256:...",
  "start_step": "foundation",
  "supported": true,
  "validation_errors": []
}
```

### 2.2 WorkflowRun

```json
{
  "run_id": "run_...",
  "definition_id": "contract-bootstrap",
  "definition_version": 1,
  "definition_digest": "sha256:...",
  "workspace_id": "workspace_...",
  "status": "running|blocked|waiting_for_human|needs_attention|completed|failed|cancelled",
  "current_step_id": "contract-lock",
  "revision": 4,
  "input_digest": "sha256:...",
  "last_error": null,
  "created_at": "RFC3339",
  "updated_at": "RFC3339"
}
```

响应中的 `current_step_id` 只由 Runtime 产生。任何 start/resume/decision request 均不接受 authoritative `next_step`。

### 2.3 HumanGate

```json
{
  "gate_id": "gate_...",
  "challenge_id": "challenge_...",
  "run_id": "run_...",
  "step_id": "contract-lock",
  "expected_revision": 4,
  "contract_digest": "sha256:...",
  "status": "pending|approved|rejected|stale",
  "created_at": "RFC3339",
  "decision": null
}
```

批准后的 `decision`：

```json
{
  "value": "approve|reject",
  "actor_id": "principal stable id",
  "actor_display": "safe display name",
  "comment": "optional",
  "decided_at": "RFC3339"
}
```

`actor_id` 和 `actor_display` 来自服务端 Principal，不从请求 JSON 读取。

### 2.4 WorkflowEvent

```json
{
  "event_id": "evt_...",
  "sequence": 12,
  "run_id": "run_...",
  "step_id": "contract-lock",
  "attempt_id": null,
  "revision": 4,
  "type": "gate.requested",
  "correlation_id": "corr_...",
  "payload": {
    "contract_digest": "sha256:..."
  },
  "created_at": "RFC3339"
}
```

## 3. HTTP API

| Method / Path | Request | Success | 主要错误 |
|---|---|---|---|
| `GET /definitions` | — | `200 {definitions: WorkflowDefinitionSummary[]}` | `500 STORE_ERROR` |
| `POST /definitions/validate` | `{document: string, format: "toml"}` | `200 WorkflowDefinitionSummary` | `400 DEFINITION_INVALID` |
| `POST /runs` | `{definition_id, definition_version, workspace_id, input}` | `201 WorkflowRun` | `400 DEFINITION_INVALID`, `404 DEFINITION_NOT_FOUND` |
| `GET /runs` | filters: `status?`, `definition_id?` | `200 {runs: WorkflowRun[]}` | `400 VALIDATION_ERROR` |
| `GET /runs/{run_id}` | — | `200 {run, pending_gate?, last_step?}` | `404 RUN_NOT_FOUND` |
| `POST /runs/{run_id}/resume` | `{expected_revision}` | `200/202 WorkflowRun` | `409 STATE_CONFLICT`, `409 RUN_NOT_RESUMABLE` |
| `GET /runs/{run_id}/events` | `after_sequence?` | `200 {events: WorkflowEvent[]}` | `404 RUN_NOT_FOUND` |
| `POST /runs/{run_id}/gates/{gate_id}/decisions` | `{challenge_id, expected_revision, contract_digest, decision, comment?}` | `200 WorkflowRun` | `403 HUMAN_PRINCIPAL_REQUIRED`, `409 GATE_STALE`, `409 STATE_CONFLICT` |

### 3.1 明确禁止的请求字段

以下字段若出现在写请求中，必须返回 `400 FORBIDDEN_STATE_FIELD`，不能忽略后继续：

```text
stage
current_step
next_step
status
revision_to_set
approved_by
actor_id
```

这样可防止旧客户端以为这些字段仍有控制作用。

## 4. Application Service Contract

HTTP route 调用等价的 application service operation：

```text
list_definitions(query) -> DefinitionSummary[]
validate_definition(document) -> DefinitionSummary
start_run(definition_ref, workspace_id, input, correlation_id) -> WorkflowRun
get_run(run_id) -> RunView
list_runs(query) -> WorkflowRun[]
resume_run(run_id, expected_revision, correlation_id) -> WorkflowRun
decide_gate(run_id, gate_id, challenge, expected_revision,
            contract_digest, decision, comment, principal, correlation_id)
    -> WorkflowRun
list_events(run_id, after_sequence) -> WorkflowEvent[]
```

`principal` 是宿主调用上下文参数，不是用户 payload 的一部分。

## 5. Step Handler Contract

```text
ProgramStepHandler.execute(context: StepContext) -> ProgramStepResult
```

### 5.1 StepContext

```json
{
  "run_id": "run_...",
  "definition_id": "contract-bootstrap",
  "definition_version": 1,
  "step_id": "foundation",
  "attempt_id": "attempt_...",
  "attempt_number": 1,
  "idempotency_key": "idem_...",
  "workspace_id": "workspace_...",
  "normalized_input": {},
  "input_digest": "sha256:...",
  "correlation_id": "corr_..."
}
```

context 对 handler 只读，不暴露 WorkflowStore。

### 5.2 ProgramStepResult

```json
{
  "outcome": "succeeded|blocked|failed",
  "result_code": "definition-declared string",
  "output": {},
  "output_digest": "sha256:...",
  "retryable": false,
  "questions": []
}
```

Runtime 先按 definition 的 result schema 验证，再选择 `result_code` 对应的唯一 transition。

## 6. Foundation Contract

注册 handler 名称：`foundation.ensure`。

合法 result code：

| result_code | 含义 | 是否可进入下一步骤 |
|---|---|---|
| `satisfied` | 全部前置条件已满足 | 是 |
| `repaired` | 本次完成幂等修复并复验通过 | 是 |
| `blocked` | 缺少必须由人决定的输入 | 否 |
| `failed` | 检查或修复失败 | 否；按 retry policy |

`questions` 中每一项：

```json
{
  "question_id": "foundation.repo-owner",
  "prompt": "...",
  "choices": [],
  "required": true
}
```

Foundation adapter 的 create operation 必须接受 Runtime idempotency key，并对相同 key 返回同一资源结果。

## 7. Definition Example

```toml
definition_id = "contract-bootstrap"
version = 1
start_step = "foundation"

[[steps]]
id = "foundation"
type = "program"
handler = "foundation.ensure"

[steps.transitions]
satisfied = "contract-verify"
repaired = "contract-verify"

[[steps]]
id = "contract-verify"
type = "program"
handler = "contract.verify"

[steps.transitions]
verified = "contract-lock"

[[steps]]
id = "contract-lock"
type = "human_gate"
bind = ["contract_digest"]

[steps.transitions]
approved = "$complete"
rejected = "$failed"
```

`$complete` 和 `$failed` 是 Runtime 保留终态，不是可覆盖步骤名。

## 8. State Machines

### 8.1 Run status

| Current | Trigger/guard | Next |
|---|---|---|
| absent | valid start | `running` |
| `running` | program result allows next program | `running` |
| `running` | program result blocked | `blocked` |
| `running` | enter human gate | `waiting_for_human` |
| `waiting_for_human` | valid approve | definition target (`running` or `completed`) |
| `waiting_for_human` | valid reject | definition target, normally `failed` |
| any unfinished | uncertain crash outcome | `needs_attention` |
| `blocked`/`needs_attention` | valid resume policy | `running` |

没有与当前状态、step 和 definition edge 同时匹配的 trigger 一律拒绝。

### 8.2 Gate status

| Current | Trigger | Next |
|---|---|---|
| absent | enter human gate | `pending` |
| `pending` | valid approve | `approved` |
| `pending` | valid reject | `rejected` |
| `pending` | revision/contract changed | `stale`，并创建新 pending gate |
| terminal | any decision | reject as `GATE_ALREADY_DECIDED` |

## 9. Persistence Constraints

SQLite 至少满足：

- `workflow_runs.run_id` primary key。
- definition identity 为 `(definition_id, version)` unique，保存 immutable document digest。
- `workflow_events` 对 `(run_id, sequence)` unique。
- `human_gates.challenge_id` unique。
- 同一 run/step/revision 最多一个 pending gate。
- `idempotency_records.idempotency_key` unique。
- run update 使用 `WHERE run_id=? AND revision=?`，成功后 revision 加一。

Runtime DB 默认位于 `.louke/server/workflows.sqlite3`，必须被 Git 忽略。规格、acceptance、workflow definition 仍是版本控制内容。

## 10. Error Envelope

```json
{
  "error_code": "STATE_CONFLICT",
  "message": "Workflow run changed; reload before retrying.",
  "detail": {
    "run_id": "run_...",
    "expected_revision": 3,
    "actual_revision": 4,
    "correlation_id": "corr_...",
    "retryable": true
  }
}
```

稳定错误码：

```text
VALIDATION_ERROR
DEFINITION_INVALID
DEFINITION_NOT_FOUND
UNSUPPORTED_STEP_TYPE
UNREGISTERED_HANDLER
RUN_NOT_FOUND
RUN_NOT_RESUMABLE
STATE_CONFLICT
TRANSITION_NOT_ALLOWED
STEP_OUTPUT_INVALID
STEP_TIMEOUT
HUMAN_PRINCIPAL_REQUIRED
GATE_NOT_FOUND
GATE_STALE
GATE_ALREADY_DECIDED
FORBIDDEN_STATE_FIELD
STORE_ERROR
```

错误 detail 不得包含 secret、credential 或 workspace 外文件正文。
