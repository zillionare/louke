# v0.12-001 Gap Analysis — Story → Spec → AC → Test → Code

- **分析日期**: 2026-07-14
- **分析人**: QoderWork (Aaron 委托)
- **背景**: Maestro 将项目进度推进到 M-MILESTONE，但实际集成工作未完成。本报告量化 story 到可用产品之间的真实 gap。

---

## 一、总览

| 层级 | 完成度 | 说明 |
|------|--------|------|
| Story 场景 | 18/18 (100%) | 所有场景在 spec 中都有 FR 覆盖 |
| Spec FR/NFR | 30/30 (100%) | 25 FR + 5 NFR，全部 Decided=✅ |
| AC 定义 | 144/144 (100%) | 每个 FR/NFR 都有 Given-When-Then AC |
| Unit Test 代码 | 30/30 (100%) | 每个 FR/NFR 都有对应 unit test |
| E2E Test 代码 | 16/30 (53%) | 9 个 FR 仅 unit test，无 E2E |
| Runtime 域逻辑 | 25/25 FR (100%) | 8,296 行 domain code，全部"Full" |
| **Web 集成** | **0/25 FR (0%)** | web/app.py 仍为 v0.11，未接入 runtime |
| **`lk serve` 集成** | **未改** | serve 未检测初始化状态、未接入 runtime_selector；其余 CLI 保持 v0.11 即可 (FR-0701) |
| **产品可用性** | **0/18 场景 (0%)** | 用户无法通过 Web/CLI 触发任何 v0.12 功能 |
| **真实 OpenCode** | **0/1 (0%)** | 仅有 contract protocol + in_memory mock，无真实 adapter |

**核心结论**: Runtime 域逻辑 (louke/runtime/) 100% 完成，但它是一个**孤岛** — 没有 HTTP 端点、没有 CLI 命令、没有前端页面与之对接。用户无法实际使用任何 v0.12 功能。

---

## 二、场景 → Spec → AC 覆盖矩阵

| # | 场景 | 覆盖 FR | AC 数 | Unit Test | E2E Test | Web 端点 | CLI 命令 |
|---|------|---------|-------|-----------|----------|----------|----------|
| 1 | 启动工作流 | FR-0001,0101,0301,0401,1101,1701, NFR-0001 | 22 | ✅ | ⚠️ 部分 | ❌ | ❌ |
| 2 | Foundation 已满足 | FR-0301,0401,0601,1601 | 14 | ✅ | ❌ | ❌ | ❌ |
| 3 | Foundation 可自动修复 | FR-0301,0401,0601 | 11 | ✅ | ❌ | ❌ | ❌ |
| 4 | 批准需求后才设计 | FR-0501,0801,0901,1901 | 25 | ✅ | ⚠️ FR-1901 | ❌ | ❌ |
| 5 | 等待 M-LOCK | FR-0101,0201,0501,0901,1901 | 24 | ✅ | ⚠️ FR-1901 | ❌ | ❌ |
| 6 | 规格变化使批准失效 | FR-0501,0601,0801,0901 | 18 | ✅ | ❌ | ❌ | ❌ |
| 7 | 进程中断与恢复 | FR-0101,0201,0301, NFR-0001,0101 | 15 | ✅ | ⚠️ 部分 | ❌ | ❌ |
| 8 | Web 创建项目和工作流 | FR-1001,1101,1201,1701,1801,2401 | 37 | ✅ | ✅ FR-1801~2401 | ❌ | ❌ |
| 9 | 查看工作流 | FR-0601,1001,1201,1301 | 16 | ✅ | ❌ | ❌ | ❌ |
| 10 | 调整 Agent model | FR-1301 | 5 | ✅ | ❌ | ❌ | ❌ |
| 11 | 执行语义 Agent 任务 | FR-0701,1401,1501,1601,1701 | 25 | ✅ | ❌ | ❌ | ❌ |
| 12 | 第一次使用 Louke | FR-1801,2401, NFR-0401 | 18 | ✅ | ✅ FR-1801,2401 | ❌ | ❌ |
| 13 | 项目详情完成动作 | FR-0501,0601,0801,0901,1901 | 31 | ✅ | ✅ FR-1901 | ❌ | ❌ |
| 14 | 任务失败、取消与恢复 | FR-0201,0301,0601,1401,2001, NFR-0001 | 22 | ✅ | ✅ FR-2001 | ❌ | ❌ |
| 15 | 完成完整 workflow | FR-0401,0801,0901,1601,1701,2101,2201 | 37 | ✅ | ✅ FR-2101,2201 | ❌ | ❌ |
| 16 | 采用旧 workspace | FR-0701,2301,2401 | 13 | ✅ | ✅ FR-2301,2401 | ❌ | ❌ |
| 17 | 活动项目期间新需求 | FR-1001,1101,1701, NFR-0101 | 14 | ✅ | ❌ | ❌ | ❌ |
| 18 | 两个项目不同版本 | FR-2401, NFR-0301 | 14 | ✅ | ✅ FR-2401 | ❌ | ❌ |

---

## 三、集成层 Gap 详解

### Gap-1: Web 端点缺失 (阻断全部 18 场景)

`web/app.py` (2,988 行) 是 v0.11 时代产物，所有路由指向 v0.11 模块。v0.12 runtime 需要的新端点一个都没有：

| 需要的端点 | 对应 FR | 现状 |
|-----------|---------|------|
| `POST /api/projects` | FR-1101 | ❌ web/store.py (文件系统) vs runtime/projects.py (SQLite) |
| `GET /api/projects` | FR-1001 | ❌ 同上，两套存储不互通 |
| `GET /api/projects/{id}/workflow-graph` | FR-1201 | ❌ runtime/workflow_graph.py 无 HTTP 暴露 |
| `POST /api/gates/{id}/decide` | FR-0501,0801,0901 | ❌ runtime/gates.py 无 HTTP 暴露 |
| `GET /api/projects/{id}/detail` | FR-1901 | ❌ runtime/project_detail.py 无 HTTP 暴露 |
| `PUT /api/bindings/{agent}` | FR-1301 | ⚠️ web/bindings.py 存在但是 v0.11 版本，不经过 runtime/agent_bindings.py |
| `POST /api/runtime/create` | FR-0001,0101 | ❌ runtime/orchestrator.py 无 HTTP 暴露 |
| `GET /api/runtime/events` | FR-0601 | ❌ runtime/events.py 无 HTTP 暴露 |
| `POST /api/opencode/sessions` | FR-1401 | ⚠️ opencode_api.py 存在但是 v0.11 版本，不经过 runtime/opencode_sessions.py |
| `GET /api/readiness` | FR-1801 | ❌ runtime/workspace_init.py 无 HTTP 暴露 |
| `GET /api/migration/preview` | FR-2301 | ❌ runtime/legacy_adoption.py 无 HTTP 暴露 |

### Gap-2: CLI 命令缺失 (阻断 CLI 路径)

`louke/__main__.py` (474 行) 只注册 v0.11 子命令。v0.12 runtime 没有 CLI 入口：

| 需要的命令 | 对应 FR | 现状 |
|-----------|---------|------|
| `lk runtime status` | FR-0101,0201 | ❌ 不存在 |
| `lk project create` | FR-1101 | ❌ 不存在（v0.11 用 `lk init`） |
| `lk gate approve/reject` | FR-0501,0801,0901 | ❌ 不存在（v0.11 用 `lk tasks toggle`） |
| `lk workflow list/graph` | FR-1201,1701 | ❌ 不存在 |
| `lk runtime recover` | FR-2001 | ❌ 不存在 |
| `lk migrate preview/apply` | FR-2301 | ❌ 不存在 |

### Gap-3: 持久化层双轨 (架构风险)

两套独立存储系统并存但互不通信：

| 维度 | v0.11 web/store.py | v0.12 runtime/store.py |
|------|-------------------|----------------------|
| 后端 | 文件系统 (JSON) | SQLite |
| 内容 | docs, wiki, bindings, users, activity | WorkflowRun, events, step attempts |
| 并发控制 | version token CAS | revision CAS |
| 互通 | 无 | 无 |

这意味着即使 web 端点接上 runtime，用户数据 (认证、文档) 和工作流数据 (run、gate) 仍在两个不同世界。

### Gap-4: intent_api.py 是半成品

`louke/intent_api.py` 文档明确写道: "executed always False, not actually triggering Backlog/Maestro"。这个模块只做关键词分类，不执行任何真实操作。

### Gap-5: 前端页面缺失

即使后端端点补齐，前端也需要新增：

| 需要的页面 | 对应 FR | 现状 |
|-----------|---------|------|
| Projects 列表 (当前/历史/backlog) | FR-1001 | ❌ web/app.py 无此页面 |
| 创建项目表单 | FR-1101 | ❌ |
| 工作流图渲染 | FR-1201 | ❌ |
| Agent-model 绑定拖拽 UI | FR-1301 | ❌ (v0.11 bindings 是下拉选择) |
| Gate 审批面板 | FR-1901 | ❌ (v0.11 tasks_api 是 checkbox) |
| Init-wizard | FR-1801 | ❌ |
| 迁移预览 | FR-2301 | ❌ |
| Project 详情 (step/gate/artifact) | FR-1901 | ❌ |

---

## 四、Unit Test → E2E Test Gap

### 有 E2E Test 的 FR (14 个)

FR-0001 (opencode_e2e), FR-0201 (intent_e2e), FR-0301 (wiki_e2e), FR-0501 (tasks_e2e), FR-0601 (backlog_e2e), FR-0701 (files_e2e), FR-0801 (files_e2e + documents), FR-1801, FR-1901, FR-2001, FR-2101, FR-2201, FR-2301, FR-2401

**注意**: FR-0001~FR-0801 的 E2E 测试是 v0.11 时代的，测试的是 v0.11 web 端点而非 v0.12 runtime。只有 FR-1801~FR-2401 的 E2E 是 v0.12 原生测试。

### 无 E2E Test 的 FR (11 个)

FR-0101, FR-0401, FR-0901, FR-1001, FR-1101, FR-1201, FR-1301, FR-1401, FR-1501, FR-1601, FR-1701

### Stub/Placeholder 测试 (3 个)

1. `test_fr0101_deferred.py` — stub，FR-0101 的 v0.11 legacy path 显式延迟
2. `test_browser_compat_placeholder.py` — stub，真实 Playwright 测试在同目录的另一个文件中
3. `test_real_opencode_l3__smoke.py` — conditional，需 `LOUKE_RUN_REAL_OPENCODE=1`

---

## 五、Pre-v0.12 代码现状

### BATS 测试 (38 个文件)

全部测试 v0.5~v0.11 时代功能: agent frontmatter、branch naming、CI parity、commit rules、keeper gate、inline discussion、sage/lex gating、scout foundation 等。

**这些测试与 v0.12 runtime 无关。** 但 v0.12 的 FR-0701 (新旧流程隔离) 明确要求不删除旧 pipeline。因此这些测试应保持通过。

### Agent 定义 (12 个 .md 文件)

Maestro/Scout/Warden/Sage/Lex/Archer/Prism/Devon/Keeper/Shield/Judge/Librarian 全部保留。v0.12 FR-1601 要求:
- Scout/Warden 的 foundation 职责已程序化 → 这两个 agent 的 M-FOUND 角色应退出新 workflow
- Keeper 的 per-commit gate 是程序+语义混合 → 需要拆分

目前 agent .md 文件**未做任何修改**以反映 v0.12 职责变更。

### CLI 工具 (28 个 .py 文件)

Maestro (advance/regress)、Scout (foundation)、Warden (foundation-check)、Keeper (gate)、Sage (create-issues)、Lex (verify-acceptance) 等 CLI 全部保留。v0.12 运行时这些命令的行为需要调整但目前未做。

---

## 六、优先级排序

### P0 — 阻断用户使用的集成 gap

| # | Gap | 影响 | 工作量估算 |
|---|-----|------|-----------|
| G1 | Web 端点层 (HTTP API for runtime) | 所有 18 场景不可用 | 大 (新 Starlette 路由 + adapter) |
| G2 | 前端页面 (Projects/graph/gate/wizard) | 所有 Web 场景不可用 | 大 (HTML + JS + SSE) |
| G3 | 持久化层统一 (SQLite vs 文件系统) | 用户/文档与 workflow 隔离 | 中 (store adapter 或迁移) |
| G4 | `lk serve` 集成 (init-wizard 检测 + runtime_selector) | 首次使用无法自动进入 wizard；版本解析不经过 runtime_selector | 小 (改 serve.py + 接入 workspace_init 和 runtime_selector) |
| G5 | **真实 OpenCode adapter** | FR-1401 AC-01 明确要求"内存 echo 不满足"；当前只有 in_memory mock | 大 (server 启动/workspace 管理/session 真实生命周期/detach-attach/recovery 重连) |

### P1 — 有 unit test 但缺 E2E

| # | Gap | 影响 |
|---|-----|------|
| G6 | FR-0901~FR-1701 无 E2E (9 个 FR) | 集成风险未验证 |
| G7 | v0.11 E2E 测试不覆盖 runtime 路径 | 旧测试≠新功能验证 |

### P2 — Agent 职责迁移

| # | Gap | 影响 |
|---|-----|------|
| G8 | Agent .md 未反映 v0.12 职责拆分 | FR-1601 built-in responsibility inventory 不完整 |
| G9 | intent_api.py 半成品 | 关键词分类不触发真实操作 |

---

## 七、数据量统计

| 指标 | 数量 |
|------|------|
| Story 场景 | 18 |
| Spec scenarios | 13 (story) + spec 自有 |
| FR | 25 |
| NFR | 5 |
| AC | 144 |
| Unit test 文件 | 35 (runtime) + 15 (root) = 50 |
| Unit test 行数 | 6,286 (runtime) |
| E2E test 文件 | 16 |
| BATS test 文件 | 38 (全 pre-v0.12) |
| Runtime 源码文件 | 26 |
| Runtime 源码行数 | 8,296 |
| Web 源码文件 | 8 |
| Web 源码行数 | 4,363 (全 v0.11) |
| CLI 源码文件 | 28 |
| CLI 源码行数 | 8,137 (大部分 v0.11) |
| Agent 定义文件 | 12 + 2 protocols + 3 skills |
| Agent 定义行数 | 2,937 |
| 总 Python 代码 | ~27,100 行 |



---

## 八、Story 18 场景 × E2E 覆盖（v0.12.0 tag 真实状态）

**分析日期**: 2026-07-15
**方法**: 解析 `tests/e2e/*.py` 中所有以 `test_` 开头的函数 docstring，提取 `AC-FRxxxx-NN` 标记；与 `acceptance.md` 定义的 127 AC 交叉。

| # | 场景 | FR 涉及 | E2E 覆盖 | 状态 |
|---|------|---------|----------|------|
| 1 | 启动工作流 | FR-0001, FR-0101 | 8/7 | FULL |
| 2 | Foundation 已满足 | FR-0201 | 4/3 | FULL |
| 3 | Foundation 可自动修复 | FR-0201 | 4/3 | FULL |
| 4 | 批准需求后才开始设计 | FR-0501 | **3/6 (50%)** | **PART** |
| 5 | 等待 M-LOCK | FR-0301, FR-0601 | 8/7 | FULL |
| 6 | 规格在批准前后发生变化 | FR-0301 | 5/4 | FULL |
| 7 | 进程中断与恢复 | FR-0401 | **1/4 (25%)** | **PART** |
| 8 | 从 Web 创建项目和工作流 | FR-0701, FR-0801 | **6/9 (66%)** | **PART** |
| 9 | 查看当前或历史工作流 | FR-0901, FR-1001 | **7/10 (70%)** | **PART** |
| 10 | 调整 Agent model | FR-1001, FR-1301 | **5/10 (50%)** | **PART** |
| 11 | 执行语义 Agent 任务 | FR-1101, FR-1201 | **4/11 (36%)** | **PART** |
| 12 | 第一次使用 Louke | FR-1801 | 6/6 | FULL |
| 13 | 在项目详情完成当前动作 | FR-1901 | 8/8 | FULL |
| 14 | 任务失败、取消与恢复 | FR-2001 | 5/5 | FULL |
| 15 | 完成完整 workflow | FR-1601, FR-2101, FR-2201 | **13/18 (72%)** | **PART** |
| 16 | 采用旧 Louke workspace | FR-2301 | 5/5 | FULL |
| 17 | 活动项目期间收到新需求或 hotfix | FR-0601, FR-2401 | 11/11 | FULL |
| 18 | 两个项目使用不同 Louke 版本 | FR-2401 | 8/8 | FULL |

**汇总**: 18 场景中 **11 FULL + 7 PART + 0 NONE**。
**涉及 AC**: 7 个 PART 场景共缺 **30 个 AC 的 e2e 覆盖**（其中 0 个由 unit 覆盖，全部为"裸露"）。

### 8.1 缺失 AC 明细（按场景分组）

#### 场景 4 — 批准需求后才设计
- AC-FR0501-04: stale digest 提交旧批准 → 返回 stale-gate / state-conflict
- AC-FR0501-05: gate 已批准后，artifact digest 改变 → 旧批准失效
- AC-FR0501-06: 同一 digest 重复批准 → 不破坏状态

#### 场景 7 — 进程中断与恢复
- AC-FR0401-02: foundation ensure idempotent（首次 `repaired`，再次 `satisfied`）
- AC-FR0401-03: ensure 失败时持有 partial 资源，run 进入 reconcile
- AC-FR0401-04: 服务重启后 run state 还原到中断前步骤

#### 场景 8 — 从 Web 创建项目和工作流
- AC-FR0701-03: definition 引用未接入的 capability → 返回 unsupported error
- AC-FR0801-04: 需求 gate 批准后，story/spec/acceptance 任一改变 → 旧批准 stale
- AC-FR0801-05: 字段缺失 / 非法 → 不留半创建记录
- AC-FR0801-06: 并发提交创建 → 不留半创建记录

#### 场景 9 — 查看当前或历史工作流
- AC-FR0901-05: M-LOCK 批准后任一绑定文档改变 → 旧批准 stale
- AC-FR1001-04: active 非 hotfix Project 存在时 → 不创建第二个新 Project
- AC-FR1001-05: 列表展示 active vs history 正确分区

#### 场景 10 — 调整 Agent model
- AC-FR1001-04, AC-FR1001-05: 同上
- AC-FR1301-03: 进行中 task 继续使用原 model A
- AC-FR1301-04: 下一个尚未开始 task 使用新 model B
- AC-FR1301-05: 变更产生可审计记录

#### 场景 11 — 执行语义 Agent 任务
- AC-FR1101-04: 字段缺失 / 非法 / 冲突 → 不留半创建
- AC-FR1101-05: OpenCode session 只能由 program adapter 创建
- AC-FR1101-06: context manifest 绑定到 step 不可被 Agent 修改
- AC-FR1101-07: Agent 输出中的"自批门禁 / 自跳阶段"声明不生效
- AC-FR1201-02: 节点状态正确分类
- AC-FR1201-03: 语义 task 失败时 step 进入 `failed`，不下一步
- AC-FR1201-04: 同一 Agent 同一时间只有一个 active task

#### 场景 15 — 完成完整 workflow
- AC-FR1601-02: Agent 自批门禁 / 自完成 commit 等声明本身不产生副作用
- AC-FR1601-03..06: 验证 / 发布 / 归档路径的同义要求

### 8.2 评估

这些缺失 AC 中**没有任何一个被 unit 测试覆盖**——它们要么是**集成边界**（Web form 提交、HTTP 提交、Agent 输出处置），要么是**持久化 + 重启**（基础 ensure、recovery、scenarios 7/14），要么是**状态机不变量**（gate 失效、并发、agent 角色边界）。

它们**不应当被 e2e 跳过**——任何一项缺失都是一个明确的 AC 失败。建议在 v0.12.x patch series 补齐：
- **优先级 P0**（影响发布门禁/数据完整性）：AC-FR0501-04/05、AC-FR0801-04、AC-FR0901-05、AC-FR1601-02..06
- **P1**（影响用户体验/可恢复性）：AC-FR0401-02..04、AC-FR1101-04..07、AC-FR1201-02..04
- **P2**（影响多用户并发/审计）：AC-FR0701-03、AC-FR0801-05/06、AC-FR1001-04/05、AC-FR1301-03..05

### 8.3 跟 v0.12.0 tag 关系

- v0.12.0 tag **正确**地反映了当前代码状态：127 AC 中 91 通过 e2e 验证 + 6 通过 unit 验证 = 97/127 (76%)，30 裸露 AC 已诚实记录在此表。
- tag 注释中"144/144 AC referenced at M-DEV unit layer" 指的是**代码引用**（测试 docstring 引用了 AC ID），不是**真实验证通过率**。`Keeper` gate 检查"每条 AC 至少有 1 个 unit test 引用"，这是一道粗筛——不替代真实 e2e 覆盖。本表 8.1 是真实通过率。
- 后续 v0.12.1/0.12.2 可基于本表优先级补 30 个 AC。
