# Programmatic Workflow Runtime — Test Plan Exploration Draft

> 本文件是在 M-SPEC 完成前形成的探索快照，不属于当前合同。正式 test plan 必须由锁定后的 spec/acceptance 推导，不能用本草稿反向约束需求。

- **Spec ID**：`v0.12-001-programmatic-workflow-runtime`
- **Created**：2026-07-13
- **Status**：Draft
- **Related acceptance**：`.louke/project/specs/v0.12-001-programmatic-workflow-runtime/acceptance.md`
- **Related interfaces**：`.louke/project/specs/v0.12-001-programmatic-workflow-runtime/interfaces.md`

## 1. 立场与边界

### 1.1 黑盒立场

测试只从以下公开出口判断行为：

- Workflow Runtime application service / HTTP API。
- 持久化 store 重新打开后的公开查询结果。
- append-only event 查询接口。
- foundation 外部依赖 adapter 的调用记录。
- 进程级启动、停止和恢复结果。

测试不得通过直接修改 Runtime 内部对象、猴子补丁状态机或伪造持久化行来使转移通过。

### 1.2 核心风险

1. 调用者仍能像当前 `--stage` 一样选择下一步。
2. 状态和事件分开写入，崩溃后互相矛盾。
3. handler 重试造成重复外部副作用。
4. Agent 文本或请求字段伪造 human approval。
5. contract 改变后旧批准仍被复用。
6. stand-in 测试被错误宣称为真实 OpenCode/Agent 集成。

### 1.3 反作弊约束

- 不允许 `assert True`、仅判断非空、吞掉异常或无 Issue 的 skip。
- 不允许 mock Runtime 的 transition/store 核心；只能替换 Runtime 边界外的 clock、foundation remote service 和 principal provider。
- expected transition 必须来自测试内独立 definition fixture，不能调用实现的“下一步计算”作为 ground truth。
- 每个测试 docstring 首行引用至少一个 `AC-FRXXXX-YY` 或 `AC-NFRXXXX-YY`。
- placeholder、echo、永远 `executed=false` 的返回不能满足执行类 AC。

## 2. 测试环境

- Python：项目支持的 Python 3.11+。
- Store：每个测试独立临时 SQLite 文件；integration 测试真实关闭并重新打开连接。
- Clock/ID：可控实现，保证并发、超时和事件顺序可重复。
- Foundation remote adapter：进程内 contract stand-in，公开记录 create/check 调用及 idempotency key。
- Human principal：由测试宿主注入，批准 payload 本身不得包含可作为身份来源的 actor。
- 默认无网络、无 GitHub token、无 OpenCode server、无模型凭据。

## 3. 测试层次

### 3.1 Unit

覆盖纯 definition validation、状态转移规则、结果 schema、digest、idempotency key、gate challenge 校验和错误码映射。

Unit 测试可以使用内存 repository port，但不得替换被测的 transition policy 或 gate policy。

### 3.2 Integration

使用真实 SQLite store 和 application service，覆盖：

- run + event 同事务提交。
- expected revision compare-and-swap。
- 真实关闭/重开后的恢复。
- program handler registry 和 foundation adapter 边界。
- contract digest 改变导致 gate 失效。
- 旧 pipeline 与新 store 的隔离。

### 3.3 E2E

通过正式 service/API 组装入口运行一个最小 `foundation -> contract-check -> human-gate -> complete` workflow：

1. 创建运行并自动完成 foundation。
2. 到达 gate 后尝试 resume、直接指定下一步和伪造 `approved_by`，全部失败。
3. 使用宿主 principal 批准后完成。
4. 在 gate 前后分别重启 service，结果保持一致。
5. adapter 记录中不存在 Scout、Warden 或重复远程资源创建。

E2E 不要求浏览器；Web UI 属于 v0.12-005。

## 4. 测试数据与 Ground Truth

测试定义保存在 `tests/assets/workflows/`，至少包含：

- 最小合法 program + gate definition。
- 悬空边、重复 ID、未知 handler、未知 step type 等无效定义。
- v1/v2 同名不同转移定义。
- contract digest 发生变化的输入快照。

Ground truth 由 fixture 文件中显式声明的步骤和边计算，不 import Runtime 的 transition 选择函数。外部资源是否重复创建以 stand-in 的独立调用日志为准。

## 5. Acceptance 覆盖策略

- FR-0001、FR-0101：unit 验证规则；integration 验证 Runtime 不接受客户端选择状态。
- FR-0201、NFR-0001、NFR-0101：integration 和进程重启 e2e 验证持久化、原子性与并发。
- FR-0301、FR-0401：integration 使用真实 registry 与 remote stand-in；e2e 验证幂等和无 Agent 调用。
- FR-0501：unit 覆盖 challenge 字段；integration/e2e 覆盖 principal、过期批准和 contract 变化。
- FR-0601：integration 只通过 event query 验证顺序、revision 和脱敏。
- FR-0701、NFR-0201：integration 验证 store 隔离和 unsupported 行为；CI 验证离线运行、AC 闭合与覆盖率。

实现阶段必须让 `lk agent archer ci-scan` 或等价 AC 扫描器确认每个有效 AC 至少有一个真实测试引用。

## 6. 外部依赖分层

### L1 — Deterministic

默认 CI。使用可控 clock、ID、principal 和 foundation adapter；覆盖所有业务状态、异常和恢复语义。

### L2 — Contract

默认 CI。以真实序列化/API 边界运行 stand-in，验证 request/response、错误码、idempotency key 与事件 schema；不得替换 Runtime 核心。

### L3 — Real environment smoke

本 Spec 不把真实 GitHub/OpenCode smoke 计入完成条件。若实现 foundation remote adapter 的真实路径，可提供手动/夜间 smoke 并明确标记，但不能用它替代 L1/L2。真实 OpenCode 验收属于 v0.12-002。

## 7. 故障注入

必须在以下边界注入一次中断：

- handler 产生副作用前。
- handler 已返回但 transaction 未提交。
- transaction 已提交但响应尚未返回客户端。
- gate 创建后、批准前。
- gate 批准事务提交后、执行下一步骤前。

每种情形都要通过关闭 store/service 并重新构造正式 Runtime 验证，不得只调用内部 rollback helper。

## 8. CI Gate

- 全部 unit、integration、e2e contract 测试离线通过。
- 每个测试引用有效 AC；每个有效 AC 至少被一个测试引用。
- 本切片核心模块 statement coverage ≥95%。
- 无无理由 skip、trivial assertion、internal-core mock 或 placeholder success。
- architecture、interfaces 与 acceptance 的状态和错误出口闭合。

## 9. Review Checklist

- [ ] 测试证明客户端不能选择下一步，而不只是“正常路径会前进”。
- [ ] 测试证明无批准、伪造批准和过期批准都不能越过 gate。
- [ ] 重启测试真实重建 service/store。
- [ ] 幂等测试从独立 adapter 日志判断副作用次数。
- [ ] 并发测试要求恰好一个写成功。
- [ ] stand-in 与真实集成状态在测试报告中没有混淆。
