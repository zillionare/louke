# Programmatic Workflow Runtime — Architecture Exploration Draft

> 本文件是在 M-SPEC 完成前形成的探索快照，不属于当前合同，不得用于约束 story/spec/acceptance。只有需求经用户与 Lex 评审并锁定后，Archer 才能以锁定合同为输入重新设计正式 `architecture.md`。

- **Spec ID**：`v0.12-001-programmatic-workflow-runtime`
- **Created**：2026-07-13
- **Status**：Draft

## 1. Architecture Goal

本切片建立一个不依赖 Maestro 对话的 workflow kernel。所有状态改变经过同一个 Runtime transaction；Agent、Web、CLI 和后续 OpenCode adapter 都只能调用 application service，不能直接写状态。

```text
HTTP / future CLI / tests
          |
          v
  WorkflowApplicationService
          |
          v
    WorkflowRuntime -------- DefinitionRegistry
       |      |                       |
       |      `---- StepRegistry -----'
       |
       +---- HumanGatePolicy <---- authenticated Principal
       |
       +---- WorkflowStore ---- SQLite
       |
       `---- FoundationHandler ---- local/remote adapters
```

OpenCode、Maestro、Devon 不在本切片的执行路径中。后续通过新的 executor port 接入，而不是获得 store 写权限。

## 2. 模块划分

建议在 `louke/workflow/` 下建立以下模块；模块名可在实现 review 中调整，但职责边界保持不变。

| 模块 | 职责 | 对应需求 |
|---|---|---|
| `definition` | 读取、规范化、验证不可变 workflow definition | FR-0001、FR-0701 |
| `model` | WorkflowRun、StepAttempt、Gate、Event、Result 值对象 | FR-0201、FR-0501、FR-0601 |
| `runtime` | 当前步骤执行、结果验证、合法转移、resume | FR-0101、FR-0201 |
| `store` | transaction、CAS revision、查询和恢复 | FR-0201、NFR-0001、NFR-0101 |
| `steps` | handler registry、StepContext、idempotency policy | FR-0301 |
| `foundation` | `foundation.ensure` handler 和外部 adapter | FR-0401 |
| `gates` | challenge 创建、principal 验证、批准失效 | FR-0501 |
| `events` | append-only event schema、脱敏与读取 | FR-0601 |
| `service` | API 使用的 application boundary 和错误映射 | 全部外部出口 |

现有 `louke/maestro.py` 不被 Runtime import；否则旧 pipeline 很容易重新成为隐式状态控制者。

## 3. 核心模型

### 3.1 WorkflowDefinition

定义是 versioned immutable value：

```text
definition_id
version
start_step
steps[]
  id
  type = program | human_gate
  handler?                 program only
  result_schema
  transitions {result -> target/completed/failed}
  retry_policy?
```

本期只允许 `program` 和 `human_gate`。`agent_task`、`decision` 名称预留给后续 spec，但本期 loader 必须拒绝而不是静默降级。

定义来自版本控制内的内建或项目文件，例如 `.louke/project/workflows/*.toml`。文件只能引用注册 handler，不能包含 shell command、Python import path 或模板表达式执行代码。

### 3.2 WorkflowRun

```text
run_id
definition_id + definition_version + definition_digest
workspace_id
status
current_step_id
revision
input_digest
created_at / updated_at
last_error?
```

`project.toml current_stage` 不参与该模型。每个 run 独立，多个 spec 或 workflow 可并存。

### 3.3 StepAttempt

每次尝试有独立 attempt id；幂等 key 由下列稳定字段计算：

```text
run_id + step_id + logical_execution_number + normalized_input_digest
```

retry 不改变 logical execution number；明确的人类 re-run 决定会创建新的 logical execution number。

### 3.4 HumanGate

```text
gate_id
challenge_id
run_id
step_id
expected_revision
contract_digest
status = pending | approved | rejected | stale
actor_id?
decision_at?
comment?
```

Principal 由宿主认证层注入 application service。Runtime 只信任结构化 principal，不从 HTTP body、Agent output 或自由文本中解析 actor。

## 4. 状态与转移算法

每个外部写操作都遵循同一顺序：

1. 开启 store transaction。
2. 按 run id 加载当前状态。
3. 比较 expected revision 和 expected current step。
4. 从 run 绑定的 definition 查找当前步骤。
5. 验证 result/challenge/principal。
6. 计算 definition 唯一允许的下一状态。
7. 写 StepAttempt/Gate、append Event、更新 WorkflowRun revision。
8. 原子提交。

客户端永远不提交 authoritative next step。客户端最多提交“请求 resume”“当前 executor 的结构化 result”或“人类对 challenge 的决定”。

## 5. Foundation 迁移

现有 Scout foundation 中的行为按性质拆分：

| 当前行为 | 新位置 |
|---|---|
| 检查 project metadata、目录、Git/repo 状态 | `foundation.ensure` 本地检查 |
| 创建缺失且输入充分的资源 | foundation adapter 的幂等 operation |
| foundation-check | handler 结束前的程序验证 |
| “主题/版本是否合理”等语义歧义 | 返回 `blocked` 问题；后续可由 human/decision 节点回答 |
| Scout/Warden Agent 会话 | 删除出新运行路径 |

本期实现不需要立即删除 Scout/Warden 文件；只需证明新 Runtime 路径完全不调用它们。待 v0.12-005 完成迁移后再删除 legacy 定义。

## 6. M-LOCK 迁移

M-LOCK 被表示为 definition 中的 `human_gate`，而不是一个带 `--confirm` 的命令：

```text
contract.verify(program)
    |
    v
contract.lock(human_gate, binds contract_digest)
    | approved
    v
completed-for-this-slice
```

本切片以 `completed-for-this-slice` 证明 gate 语义；后续完整 feature workflow 会把 approved 边连接到 Devon 开发步骤。

contract digest 由明确的合同文件集合规范化计算。初始建议集合为 `spec.md`、`acceptance.md`、`test-plan.md`、`architecture.md` 和 `interfaces.md`；文件缺失必须由 contract verification 明确处理。

## 7. 持久化

选择 Python 标准库 SQLite，默认路径：

```text
.louke/server/workflows.sqlite3
```

理由：

- 本地单服务部署无需引入外部数据库。
- transaction 和 compare-and-swap 比直接改 JSON 更可靠。
- 可同时保存 materialized run state 和 append-only events。
- 后续 Web 查询无需扫描大量目录文件。

运行数据库是本地状态，不进入 Git；实现时必须补充 `.gitignore`。设计合同和 workflow definitions 仍放在 `.louke/project/` 并进入版本控制。

建议表：

```text
workflow_definitions
workflow_runs
step_attempts
human_gates
workflow_events
idempotency_records
```

具体列和唯一约束以 `interfaces.md` 为准。

## 8. 并发、恢复与 lease

- 状态改变使用 `WHERE run_id=? AND revision=?` CAS；更新行数不是 1 即冲突。
- handler 不在持有长 SQLite write transaction 时执行。
- Runtime 先以短事务登记 attempt/lease，再执行 handler，再以 CAS 事务提交结果。
- lease 过期只说明 executor 消失，不说明副作用未发生；有 idempotency record 时查询/reconcile，没有可靠证据时进入 `needs_attention`。
- 不同 run 不共享 global current stage，可并行执行。

## 9. Event 设计

事件至少包括：

```text
run.created
step.started
step.succeeded
step.failed
run.transitioned
run.blocked
gate.requested
gate.approved
gate.rejected
gate.stale
run.completed
run.needs_attention
```

事件 payload 只保存业务字段、稳定错误码和 digest。完整输入、secret、token、session cookie 不进入事件。

## 10. 错误处理

| 情形 | Runtime 行为 |
|---|---|
| stale revision | 409 `STATE_CONFLICT`，无写入 |
| 非法 transition/result | 409 `TRANSITION_NOT_ALLOWED`，无转移 |
| 未注册 handler | definition validation 失败 |
| handler timeout/invalid output | attempt failed；按 policy retry 或停住 |
| 无 human principal | 403 `HUMAN_PRINCIPAL_REQUIRED` |
| stale gate/digest | 409 `GATE_STALE`，继续等待新 gate |
| uncertain crash outcome | `needs_attention`，不猜测成功 |

## 11. 与后续规格的边界

v0.12-002 将实现 OpenCodeRuntime port、隔离 worktree 和 context manifest，但只能向本 Runtime 提交 executor result；不能写 WorkflowStore。

v0.12-003 将定义统一 `SemanticTaskRequest/Result`，抽离各 Agent 的确定性职责，并扩展语义执行步骤类型：

- `agent_task`：调用指定 Agent 并验证结构化输出。

v0.12-004 将增加：

- `decision`：把有限候选交给 Maestro，验证其选择后转换成普通 step result。
- feature、bugfix、spec-change workflow definitions 及合法动态分支。

上述扩展仍必须经过本 Spec 定义的 transaction、revision、event 和 allowed transition 规则。

## 12. FR Traceability

| FR/NFR | 主要模块 | 外部出口 |
|---|---|---|
| FR-0001 | definition | validate/start errors, run definition identity |
| FR-0101 | runtime/store | resume/result conflict and resulting run state |
| FR-0201 | store/service | list/get/restart recovery |
| FR-0301 | steps | attempt result, adapter calls, errors |
| FR-0401 | foundation | foundation result and adapter log |
| FR-0501 | gates | pending gate and decision API |
| FR-0601 | events | ordered event API |
| FR-0701 | service/store | legacy isolation, unsupported error |
| NFR-0001 | store/runtime | restart/fault-injection results |
| NFR-0101 | store | CAS conflict behavior |
| NFR-0201 | test assembly | offline CI and capability status |
