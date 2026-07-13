---
status: Locked — M-LOCK Approved; M-DEV Not Started
spec_id: v0.12-001-programmatic-workflow-runtime
created: 2026-07-13
locked: true
related_acceptance: acceptance.md
related_interfaces: interfaces.md
---

# Programmatic Workflow Control — Test Plan

## 1. 立场与边界

### 1.1 黑盒声明

本计划只通过 [interfaces.md](interfaces.md) 所列 CLI、HTTP/HTML UI、artifact/gate/trace/event 可读出口和受控测试文件系统观察行为。测试不读取 Runtime 私有对象、SQLite 内部表、调度器状态机、私有 prompt 或 queue。需要观察的内部事实必须先成为接口合同中的公开 view/event。

测试目标是证明程序控制面不能跳步，而非证明某个 Agent“通常会遵守提示词”。所有 workflow transition、gate、证据和 runtime identity 都由 public response/event 断言。

### 1.2 非观察对象

- Python 类层级、函数调用顺序、SQL 语句和数据库表结构；
- 私有 registry、缓存和 session manager 内存状态；
- Agent 的隐藏思考过程或 provider 的内部实现；
- 多浏览器兼容性矩阵（本版本明确不在范围）。

### 1.3 反作弊规则

1. 每个测试的首行 docstring 或注释必须引用至少一个 `AC-FRxxxx-yy` 或 `AC-NFRxxxx-yy`；CI 双向检查所有 144 个 AC 都被引用、每个测试也都有 AC。
2. 禁止 `assert True`、仅 `is not None`、`try/except: pass`、根据当前实现改预期，或把 workflow core mock 掉。
3. 禁止无 GitHub issue 引用的 skip；真实 OpenCode L3 使用 marker/external environment，不用静默 skip 代替。
4. expected result 必须由 spec/acceptance、固定 definition fixture、独立输入或 public contract 推得，不能从被测实现输出反推。
5. 测试改动 PR 必须标为新增 AC、批准的 spec 变化，或带 issue 的环境修复；“实现与需求不一致所以改测试”不接受。

### 1.4 AC 闭环与责任

实现者提交 unit/integration 测试；测试负责人提交 product E2E；审查者检查 AC 引用和独立断言。测试性缺口先补 interfaces.md，不准以访问私有 store 或过度 mock 绕过。CI 执行 AC closure、assertion anti-pattern、ground-truth import 和覆盖率检查。

## 2. 测试环境

### 2.1 工具与目录

- Python ≥3.11、`pytest`、Starlette `TestClient`、覆盖率门槛 95%。本轮继承已有依赖；SQLite 使用标准库。
- `tests/unit/runtime/`：纯 catalog、identity、manifest、gate digest、trace 规则。
- `tests/integration/runtime/`：真实临时 workspace/state store、HTTP TestClient、contract OpenCode adapter。
- `tests/e2e/`：独立临时 workspace 上的实际 `lk`/server/Projects UI journey；保留 `tests/fixtures/` 作为输入资产。
- `tests/ground_truth/`：definition graph、artifact digest、trace coverage 的小型独立计算器；不得 import `louke.*`。

每次 test 使用临时 workspace、随机端口和独立 runtime artifact fixture。fixture 只模拟外部 OpenCode provider/clock/keychain，不 mock catalog、orchestrator、store、gate 或 program step。所有网络在 L1/L2 离线。

### 2.2 命名与执行

文件使用 `test_<area>__<behavior>.py`，函数使用 `test_ac_<id>_<scenario>`。执行顺序：unit → integration → e2e；`@pytest.mark.e2e` 标记 product journey，`@pytest.mark.real_opencode` 标记 L3。

```bash
python -m pytest tests/unit tests/integration
python -m pytest -m e2e tests/e2e
python -m pytest -m real_opencode tests/e2e
lk agent archer ci-scan --acceptance .louke/project/specs/v0.12-001-programmatic-workflow-runtime/acceptance.md --tests tests/
```

CI 默认运行前两条（包括 contract-adapter E2E）；真实 OpenCode smoke 仅在提供真实凭据和受控 project 时运行。产品 UI E2E 只覆盖一个受支持浏览器，不建立浏览器矩阵。

## 3. Ground Truth 方法

本项目的规则正确性来自批准的 definition/AC，而非数值算法。独立 ground truth 脚本读取固定 fixture 的 definition、artifact bytes、输入 action 和 mock provider transcript，独立计算：可达 node、合法 action 集、SHA-256 digest、FR/AC 覆盖集合以及 runtime lock 的期望选择；它不能 import 或调用 Runtime。

源文件位于 `tests/ground_truth/`，仅使用标准库和 `tests/fixtures/`，CI 静态禁止 `import louke`。UI、API 和 CLI 断言使用同一个公开预期对象，但不使用实现计算出的值作为 expected。需要时间的场景使用显式 fake clock；真实时间仅属 L3。

## 4. 测试范围

仅覆盖当前 spec/acceptance 中 Valid/Testable/Decided 均为 ✅ 的 25 个 FR、5 个 NFR 与 144 个 AC。范围包括 v0.12 新 runtime 与显式 adopt；不回写旧 workspace、也不测试旧 Maestro/Scout/Warden 的内部行为。现有 v0.11 Web UI integration 的浏览器矩阵不作为 v0.12 通过条件。

## 5. 分层策略与风险覆盖

### 5.1 L1 unit：不可跳步的规则与安全边界

L1 覆盖 definition schema/可达性/版本绑定、责任 inventory 完整性、program/semantic/mixed 分界、合法转移、CAS 入参、gate digest/actor/reject reason、source-contract hotfix 分类、artifact/trace freshness、manifest 最小权限/redaction、binding snapshot、runtime lock 验证和 error classification。主要风险是“实现把 policy 写回 Agent 或引入静默 fallback”；断言必须以 public catalog/domain 输出表达。

### 5.2 L2 integration：真实持久化与接口合同

L2 用真实临时 state store 和 Starlette API，覆盖并发 revision、事务崩溃恢复、幂等 foundation/retry、事件连续性、setup/first user、project collection/detail、gate UI/API、archive/history、legacy preview/apply/rollback、local/global resolver、A/B 隔离与 child identity。OpenCode 使用明示 `adapter_kind=contract` 的可控服务，验证 lifecycle/context/result schema，而不是宣称真实 provider 行为。

### 5.3 L3 real environment：最小真实依赖 smoke

L3 在隔离 project、真实 OpenCode 及受控凭据中完成一次 create → attach/send → detach/attach → end 的语义任务往返，并确认 provider 失败被诚实报告。它不测试生产数据、不运行任意仓库命令、不替代 L1/L2 规则证明。失败会产生可诊断 report，不能通过修改 run 状态伪造成功。

### 5.4 E2E：从用户入口到可审计历史

E2E 使用实际 `lk init/adopt/serve` 和 Projects UI：创建项目、选择 workflow、查看图和下一动作、执行两个人工决策、调整 model、管理 session、完成/取消/归档。API-only TestClient 场景不替代 UI 主旅程；UI 只验证操作可见可完成和结果可读，不断言像素/内部渲染结构。

## 6. AC → public outlet → layer 闭环

以下是测试策略闭环，不是将来具体测试函数清单。每个单独 AC 至少在其所属组内有一条带精确 AC tag 的测试；CI 以 acceptance 文件为全集复核。

| AC 组 | public outlet（interfaces.md） | 主层 | 必须证明的行为 |
| --- | --- | --- | --- |
| AC-FR0001-01—AC-FR0701-04 | workflow definitions、runtime/project/actions/events、readiness | L1 + L2 | versioned graph 拒绝坏定义；Runtime 独占转移；持久恢复；program foundation；legacy 隔离 |
| AC-FR0801-01—AC-FR0901-06 | gate/artifact review/decision、actions、events | L1 + L2 + E2E | 先 requirements approval 才生成设计；M-LOCK 精确绑定已审查设计，均不可绕过/复用 |
| AC-FR1001-01—AC-FR1301-06 | Projects collection/detail、graph、agent-bindings | L2 + E2E | sidebar current/history/new；创建字段校验；图当前位置；拖拽仅影响下一个 task |
| AC-FR1401-01—AC-FR1501-06 | task、manifest、session lifecycle/messages、events | L1 + L2 + L3 | create/detach/attach/cancel/end、重启恢复、context 最小且可审计、真实/contract 明示 |
| AC-FR1601-01—AC-FR1701-05 | responsibility inventory、catalog、actions/events | L1 + L2 + E2E | 所有 built-in 归类；程序 effects 与语义结果分离；finite branch/多 workflow 均由 Runtime 校验 |
| AC-FR1801-01—AC-FR2001-05 | setup/readiness、detail、actions、archive/events | L2 + E2E | 零手写 init、readiness 修复、阻塞/next action、retry/return/cancel/cleanup/history |
| AC-FR2101-01—AC-FR2201-06 | graph、gate、source contract、trace/completion check | L1 + L2 + E2E | full new feature；quick/design hotfix 继承批准但各自 M-LOCK；无 fresh trace 不可完成 |
| AC-FR2301-01—AC-FR2401-08 | CLI/runtime view、migrations、session/task identity | L1 + L2 + E2E | preview/rollback、legacy 诚实显示、nearest root、local fail-closed、global explicit、A/B 版本隔离 |
| AC-NFR0001-01—AC-NFR0401-04 | conflict/error/event/recovery、adapter kind、UI、redacted responses | L1 + L2 + E2E + L3 | 原子性/并发、替身诚实、完整用户旅程、loopback/认证/secret redaction |

### 6.1 程序控制面专项

使用非法 stage/action、悬空/重复/不可达 definition、并发 action、kill-after-prepare、重复 idempotency key 和 restart fixture。只允许一个 action commit；失败外部 attempt 可被查询/补偿而非猜测成功。foundation 必须重复运行产生同一可观察结果或清楚 blocked action。

### 6.2 Gate 与合同版本专项

对 story/spec/acceptance、design 三件套分别变更一个字节并计算独立 digest。验证 stale 或别的 run 的 approve 被拒绝，拒绝无理由被拒绝，requirements gate 之前没有设计 dispatch，M-LOCK 前没有 implementation dispatch；并验证 M-LOCK 的共同 digest 同时包含已批准需求三件套和已审查设计三件套，任一变化均使批准 stale。hotfix 验证 source approval 时，graph 显示 inherited 而不是新 requirements gate，两个 branch 都无法绕开本次 M-LOCK。

### 6.3 Projects UI 专项

单浏览器 E2E 从 `/projects` 进入创建表单，输入 story/release/workflow，查看 active/history 列表、workflow graph 和 current node；用拖拽改变 binding 后创建下一个 task，比较前后 manifest 的 model snapshot。通过 gate/取消/归档后刷新页面，核对 detail、events、history 与 API 相同。浏览器的视觉样式和跨浏览器布局不作断言。

### 6.4 OpenCode/context 专项

contract adapter 接收由公有 session endpoint 发出的 create/send/detach/attach/cancel/end 请求，返回固定 transcript。测试 context manifest 的 task/FR/AC/artifact/model/permission snapshot 与 secret redaction，重启后查询/attach 的语义，结束后的禁止发送。L3 额外对真实 adapter 做一趟最小生命周期；若 provider 不可用，必须返回明确 unavailable/error，而不是 `completed`。

### 6.5 动态选择专项

固定 fixture 驱动既定 action；semantic advisor 只能返回有限 enum + required evidence。非法 enum、缺 evidence、想直接指定 node、inventory 缺 handler/prompt/built-in 或 mixed 单边界均使 catalog/dispatch 拒绝。合法建议仍由 Runtime 生成事件和转移，不能由 Agent 直接写入。

### 6.6 失败、迁移与可用性专项

对失败 step 分别断言 definition 所给 retry/return/clarification/cancel，不暴露其他动作；取消后调度停止、资源 cleanup outcome 记录、历史只读。adopt preview 不修改输入，apply 有 migration ref，rollback 可恢复；未知 legacy stage 保持 `legacy_unverified`。

### 6.7 完整 workflow 与证据专项

使用批准的 artifact fixture 走完 new feature；构造 valid source contract 分别走 quick R-G-R 和 design-required hotfix。人为删除 task/commit/test/freshness 任一 trace link，completion check 必须拒绝；恢复每项后才能 release/archive。该测试以 trace public view 和权威 test-run ref 断言，不接受 Agent 自报。

### 6.8 Project-local runtime 专项

嵌套目录启动检查最近 root；local lock 的缺失 wheel、错误 hash/version、schema 不兼容均 fail closed 且给 repair action；global mode 只在 explicit lock + compatibility 时可启动。两个临时 project 的 identity 为 x.y/x.z，并发 server/task/session 输出各自 identity；install/repair/upgrade 只改变被选 workspace。init wizard 先以 bootstrap 启动后 controlled restart，且不得执行任意 project executable。

### 6.9 非功能专项

原子/并发以外部 response 与 event sequence 断言；contract vs real adapter 标识被 API/E2E 明确暴露。首次使用 E2E 包含 init、new feature、active main project 中再建 hotfix、backlog/parallel 项目、归档回看（AC-NFR0301-06）。Security 测试检查非-loopback 拒绝、未认证写拒绝、CSRF/actor audit、生敏字段在 API/event/manifest 不出现。

## 7. CI Gate

每个 PR 运行 unit/integration、contract-adapter E2E、coverage ≥95%、AC 双向引用、anti-pattern、ground-truth import、format/lint/type checks。`real_opencode` 是环境标记的发布前/夜间 gate；它的结果和 adapter kind 进入 evidence，失败阻止声明真实集成已验证。

本版本的 project E2E contract：在 repo root 启动 `python -m louke e2e start --host 127.0.0.1 --port 8765 --opencode mock`，健康检查 `curl -sf http://127.0.0.1:8765/health`，执行 `python -m pytest -m e2e tests/e2e`，再以 `python -m louke e2e stop --port 8765 --cleanup-workspace` 清理。实施阶段会使该 harness 支持 setup-only 临时 workspace；在未实现前本文件不声称它已通过。

## 8. 审查清单

- [ ] 本计划覆盖 144/144 AC，且每个 AC 有 interfaces.md 出口。
- [ ] 所有状态/安全/证据断言只落在公共 contract，不访问内部实现。
- [ ] local/global runtime、双 gate、hotfix 继承/M-LOCK 和 project E2E 都有独立覆盖。
- [ ] contract adapter 不能替代真实 OpenCode L3，且两者在证据中可区分。
- [ ] 测试未把浏览器兼容性矩阵重新引入范围。
- [ ] CI 能拒绝 AC 漏测、弱断言、无理由 skip、循环 ground truth 与低覆盖。
