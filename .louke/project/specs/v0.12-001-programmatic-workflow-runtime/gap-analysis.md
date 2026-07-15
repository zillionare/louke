# v0.12.1 Stabilization Gap Analysis and Execution Runbook

- **文档状态**: 当前执行基线，替代 2026-07-14/15 的旧 gap 结论
- **分析日期**: 2026-07-15
- **分析基线**: `main` at `6a6545a`，位于 `v0.12.0` tag 之后 1 个审计提交
- **目标版本**: `v0.12.1`
- **适用范围**: 发布完整性、生产集成、测试门禁和证据一致性修复
- **不在本轮范围**: v0.13 workflow reflow、v0.14 UI relaunch、v0.15 i18n 功能实现

---

## 1. 执行结论

当前不应直接进入 v0.14 或 v0.15 的实现，也不应按本文件旧版本中的“30 个裸露 AC”逐条补 E2E。

正确路径是：

1. 先完成一个严格限界的 `v0.12.1` 稳定化 patch。
2. `v0.12.1` 只修复发布包、生产路由、CI、测试分层的最低闭环和证据表述，不扩展产品功能。
3. `v0.12.1` 通过退出门后，进入 v0.13，由 v0.13 正式完成 Story 阶段、integration/E2E reflow、人工回退和 waive 语义。
4. v0.14 只能建立在稳定的 v0.12 Runtime API 和 v0.13 控制面上。
5. v0.15 只能建立在稳定的 v0.14 UI chrome 上，不能提前实现。

### 1.1 为什么必须先做 v0.12.1

当前主要风险不是 Runtime 域逻辑完全缺失，而是：

- 仓库中的 v0.12 代码没有被正确纳入 Python 发布包；
- 一个 v0.14 会直接依赖的生产 API 当前真实返回 404；
- 主 CI 不执行 v0.12 的 pytest/coverage 门；
- 测试目录和测试名称混淆 unit、integration、E2E；
- M-E2E 的失败、waiver 和项目 DoD 的表述相互矛盾。

如果跳过这些问题继续做 v0.14，新的 UI 会建立在不可发布、未被生产入口验证的控制面上。届时出现故障时无法判断是 UI 问题、HTTP 装配问题、wheel 漏包问题，还是 Runtime 行为问题，返工和诊断成本都会上升。

### 1.2 为什么不能机械补“30 个 E2E”

旧报告的“30”是按 7 个 Story 场景累加出来的，其中 `AC-FR1001-04/05` 在两个场景中重复，实际只有 **28 个唯一 AC**。

这 28 个唯一 AC 均能在 `tests/unit/` 中找到精确 AC 引用，而且对应测试函数确实被 pytest 收集和执行；但这只能证明“存在并运行了带该 tag 的测试”，**不能证明测试完整实现了该 AC 的 Given/When/Then**。

逐项对照 acceptance 后，当前审计判断为：

- **7 个有效 L1 证据**：测试真实调用产品域代码，并对 AC 的核心状态、结果或副作用作出较完整断言；
- **18 个部分证据**：不是空引用，也有真实断言，但遗漏 AC 的重要输入组合、公开接口、持久化、负面副作用或 UI/重启边界；
- **3 个错标/无效证明**：测试 tag 与 acceptance 语义不一致，或者主要验证测试内临时编写的 fake 逻辑，不能证明产品实现。

因此，旧报告中“0 个由 unit 覆盖，全部裸露”的结论不正确；但把它反过来写成“28 个 AC 已完成 unit 测试”同样不正确。正确表述是：**28 个 AC 都有可执行引用，其中只有一部分已有可信 L1 证明，其余仍需修正或补测。**

此外，批准的 `test-plan.md` 明确将不同 AC 分配给 L1 unit、L2 integration、E2E 和 L3 real environment。它没有要求每一个 AC 都必须进入 E2E。把所有异常、CAS、digest、非法输入和 Agent 越权组合都塞进浏览器 E2E，会造成：

- E2E 数量膨胀且运行变慢；
- 同一不变量在多个 UI 场景中重复验证；
- 失败定位困难；
- v0.14 重写 UI 时产生大量无意义返工。

正确做法是：规则在 unit 证明，真实 store/HTTP/重启/并发在 integration 证明，用户主旅程在少量 E2E 证明，真实 OpenCode 生命周期在 L3 证明。

---

## 2. 已验证的当前事实

本节只记录在当前 HEAD 上实际检查过的事实。后续执行者不得用旧报告覆盖这些事实。

### 2.1 已存在并基本可工作的能力

当前仓库已经存在以下 v0.12 实现：

- `louke/runtime/` 下的 workflow definition、store、orchestrator、gate、events、projects、workflow graph、recovery、trace、workspace init 和 runtime selector；
- `louke/opencode/` 下的 in-memory 与 real adapter、process 和 persistence；
- `louke/web/api/` 下的 projects、runtime、gates、bindings、OpenCode、readiness、setup、migration、security 和 discussion API；
- `louke/web/pages/` 下的 Projects、Runs、Gates、Setup、Migration 和 OpenCode 页面；
- `louke/cli_v12.py` 及 `project/gate/workflow/migrate` CLI 注册；
- 真实 OpenCode L3 适配修复和 runbook。

因此，旧报告中的以下结论已经失效，不能继续作为任务来源：

- “Web 集成 0/25 FR”；
- “产品可用性 0/18”；
- “真实 OpenCode adapter 不存在”；
- “v0.12 CLI 完全不存在”；
- “Agent 定义完全没有反映 v0.12 职责变化”。

### 2.2 当前验证结果

已执行并得到以下结果：

| 检查                   | 当前结果                        | 解释                                                      |
| ---------------------- | ------------------------------- | --------------------------------------------------------- |
| `lex verify-issue`     | 30 PASS / 0 FAIL                | 30 个 FR/NFR Feature issue schema 有效                    |
| `lex verify-project`   | PASS                            | 25 个 FR issue 已关联 Project #15                         |
| `pytest tests/unit -q` | 397 passed, 2 skipped           | 当前 unit 层为绿；有 1 个 tempfile unraisable warning     |
| 非浏览器 E2E           | 190 passed, 7 skipped           | `LOUKE_SKIP_LIVE_SERVER=1` 下通过                         |
| 真实 live-server E2E   | 190 passed, 1 skipped, 6 errors | 6 个错误来自当前 venv 未安装 Playwright，不是产品断言失败 |
| 生产 bindings 路由探针 | 404                             | `GET /api/runtime/bindings/devon` 被错误 Mount 顺序遮蔽   |

注意：Feature issue 和 AC 引用闭合只能证明追踪结构存在，不能替代行为测试。反过来，某个 AC 没有 E2E tag 也不能自动证明它没有 unit/integration 证据。

### 2.3 28 个唯一 AC 的语义覆盖审计

#### 审计口径

本节不以 AC 字符串是否出现作为通过标准。一个测试只有同时满足以下条件，才可记为“有效 L1 证据”：

1. AC ID 位于实际被 pytest 收集的测试函数，而不是仅出现在模块注释或 helper；
2. 测试调用仓库产品代码，而不是主要测试函数内部临时实现的规则；
3. 输入符合 acceptance 的 Given，不能用一个违反前置条件的 fixture；
4. 操作对应 acceptance 的 When；
5. 断言覆盖核心 Then，包括必要的状态不变、无副作用、审计或持久结果；
6. expected result 来自 acceptance 或独立 fixture，而不是从被测实现输出反推；
7. 测试实际运行并通过。

“有效 L1”仍不代表整个 AC 已完成产品验收。只要 acceptance 同时要求 HTTP、持久化重载、进程重启或用户 UI，仍需对应 L2/E2E 证据。

#### 逐 AC 结果

| AC           | 判定                         | 当前测试实际证明了什么                                                                        | 缺失或问题                                                                                                                   | v0.12.1 动作                                                                        |
| ------------ | ---------------------------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| AC-FR0401-02 | **有效 L1**                  | 首次 `repaired`、再次 `satisfied`，同一 adapter 资源只创建一次                                | 仍需真实 workspace/store 的 L2 幂等验证                                                                                      | 保留 unit，补 L2                                                                    |
| AC-FR0401-03 | **部分**                     | human-decidable gap 不创建资源，attempt result 为 `blocked`                                   | 没有断言结构化问题真正从公开结果返回；run 最终状态断言为 `completed` 而非 AC 所述 `blocked`                                  | 修正公开 blocked view，并补结构化问题断言                                           |
| AC-FR0401-04 | **有效 L1**                  | 不可恢复和 retryable 两条 policy 分支均不进入主步骤，并记录对应 result                        | 仍需真实持久状态/公开 view 证明用户看到 failed/retryable                                                                     | 保留 unit，补 L2                                                                    |
| AC-FR0501-04 | **部分**                     | stale revision、step、digest 会抛 `StaleGateError`                                            | 未验证 stale challenge；未通过公开 API 断言 stale-gate/state-conflict 响应；负面状态断言不完整                               | 参数化四种 stale 输入并补 production API L2                                         |
| AC-FR0501-05 | **有效 L1**                  | 已批准 gate 在 digest 改变后回到 `waiting_for_human`，challenge 更新，旧批准被拒绝            | 仍需通过生产 artifact 更新路径证明，不只直接调用 `ensure_gate`                                                               | 保留 unit，补 L2                                                                    |
| AC-FR0501-06 | **有效 L1**                  | rejection 记录 actor、时间、reason、digest 和 event，未进入 design                            | 缺少顶层 API/页面可观察性                                                                                                    | 保留 unit，补一个 L2                                                                |
| AC-FR0701-03 | **部分**                     | 未注册 capability 会拒绝 definition、不会创建 run                                             | “agent_task/decision 因真实实现而可用”使用测试内 mock adapter 证明；未覆盖 capability version                                | 保留 unsupported 测试；用实际组装的 capability registry 补真实 report/dispatch test |
| AC-FR0801-04 | **部分**                     | story digest 改变会使 approval stale、绑定新 digest、产生 stale event                         | 只改变 story，没有分别验证 spec/acceptance；未证明设计 dispatch 被阻止                                                       | 参数化三份文档并断言无 design attempt                                               |
| AC-FR0801-05 | **有效 L1**                  | rejection 返回 requirements review，reason/digest/actor 可审计，无 design event/attempt       | 仍需公开 API 层验证                                                                                                          | 保留 unit，补 L2                                                                    |
| AC-FR0801-06 | **有效 L1**                  | 有效 source contract 产生 inherited approval；behavior change、缺 issue、错误 approval 被拒绝 | “需求含糊”类别和真实 Issue/source mapping adapter 尚未覆盖                                                                   | 保留 unit；在 contract-adapter L2 补映射/含糊输入                                   |
| AC-FR0901-05 | **部分**                     | 设计 digest 改变会使 M-LOCK stale，旧 approval 失效，无 implementation attempt                | 只改变 test-plan；没有断言 Runtime 返回声明的上游步骤；批准动作已把 run 切到 implementation，前置时序需要更精确 fixture      | 参数化六份绑定文档并断言 upstream transition/current step                           |
| AC-FR1001-04 | **部分**                     | 第二个 new_feature 被拒绝并保存 backlog，active 数仍为 1                                      | 没有断言既有 run 的 revision/state/events 完全不变；没有顶层页面保存路径                                                     | 补 existing-run snapshot 和 production app L2                                       |
| AC-FR1001-05 | **部分，fixture 违反 Given** | 两个 Project/run id 不同，事件的 run_id 没有混写                                              | 测试直接创建没有 source contract 的 `bug_fix`，不满足“校验通过的 hotfix”；没有 worktree/branch/session/evidence 隔离         | 改用真实已批准 source contract；补所有隔离 identity                                 |
| AC-FR1101-04 | **部分**                     | 缺 story、非法版本、未知 workflow 被拒绝，active project 为空                                 | 未覆盖并发冲突；只查 Project list，未证明 WorkflowRun 无半记录；Web test 不经过顶层 app                                      | 补并发事务和 Project/run 双侧原子性 L2                                              |
| AC-FR1101-05 | **错标/未证明**              | 现有精确 tag 测试的是“未知 workflow 返回 404”                                                 | 该行为属于 AC-FR1101-04；没有证明 `spec_change` 不展示、backlog 只预填仍需确认、不会暗中创建 GitHub Project/近似映射         | 纠正错误 tag；为 AC-FR1101-05 新增真实测试                                          |
| AC-FR1101-06 | **部分**                     | active 主 Project 时新 story 进入 backlog且不创建第二个 active run                            | 未覆盖主项目结束后从 backlog 预填、重新 preview、confirm 前不创建、confirm 后才创建                                          | 补完整 backlog lifecycle L2/E2E                                                     |
| AC-FR1101-07 | **部分**                     | 缺 source contract 被拒；有效批准 source contract 可创建 inherited hotfix                     | 未覆盖“非已发布问题”、无法映射、需求含糊等输入；隔离和“不生成新 requirements 文档”断言不完整                                 | 扩充拒绝矩阵和隔离/无新文档断言                                                     |
| AC-FR1201-02 | **部分**                     | graph view 区分 completed、waiting、pending、skipped                                          | 未覆盖 current executing、blocked、failed、terminal 等状态；没有 UI 可区分标记证据                                           | 参数化全部实际状态，L2 验 schema，E2E 验语义标记                                    |
| AC-FR1201-03 | **有效 L1**                  | run revision 改变后 graph view 同 revision，单纯 build graph 不改变 run                       | 未验证页面事件订阅/主动刷新                                                                                                  | 保留 unit，补页面或 HTTP L2                                                         |
| AC-FR1201-04 | **部分**                     | archived run 的 `apply_command` 抛异常且 revision 不变                                        | 使用宽泛 `pytest.raises(Exception)`；没有断言 status/events 不变；未覆盖 recover/retry/fork/binding 等写入口和 UI 隐藏       | 改为精确异常并覆盖所有公开写入口                                                    |
| AC-FR1301-03 | **部分**                     | 已解析的 manifest 对象保持 model A，下一次 resolve 得到 B                                     | 没有真实 active task/session，不能证明进行中任务实际继续使用 A                                                               | 用 task lifecycle L2 固化并查询两个 task manifest                                   |
| AC-FR1301-04 | **部分**                     | 同一内存 `BindingStore` 再查询可见 override，audit 字段较完整                                 | 注释所谓“reload”只是同对象 re-query；没有重新构造 store、进程重启或页面 reload，不能证明持久化                               | 首先实现/确认持久化，再做重新打开 store + production API L2                         |
| AC-FR1301-05 | **部分**                     | BindingStore 可解析 default/override DTO，readonly 标记后拒绝 override                        | 没有由 Runtime 创建真实 Agent task，也没有证明解析结果固化进持久 task manifest                                               | 补真实 task creation/manifest/restart L2                                            |
| AC-FR1601-02 | **错标/无效证明**            | 测试证明注册的 program handler 会产生 `gate_approved` side effect                             | 没有向 Runtime 提交 Agent 输出；没有证明 Agent 自报不能产生副作用，甚至测试中的 side effect 确实发生                         | 删除/重写该证明：分别提交自批、自测、自 commit/push/tag/publish claim，断言零副作用 |
| AC-FR1601-03 | **无效证明**                 | `ResponsibilityRegistry` 会执行一个测试函数内部定义的 `gate_runner`                           | allowlist 和 gate 规则完全写在测试里，不是产品实现；没有 clean environment 权威测试，也没有拒绝 Agent 自报                   | 针对真实 program adapter/authoritative runner 写测试，禁止在测试中重写被测规则      |
| AC-FR1601-04 | **部分**                     | synthetic catalog 中两个 entry 可标为 program/semantic                                        | 没有检查实际 built-in workflow、Scout/Warden/Keeper 职责，也没有模拟 dispatch 证明 program 项不创建 Agent task               | 从真实 built-in inventory/definitions 生成矩阵并断言 dispatch                       |
| AC-FR1601-05 | **部分**                     | schema 缺 key 会被 `validate_result` 拒绝                                                     | 未覆盖越权、digest mismatch、undeclared transition；没有 run，因此未证明运行不推进                                           | 参数化四类非法结果并断言真实 run revision/step/events 不变                          |
| AC-FR1601-06 | **部分**                     | synthetic catalog 拒绝一个 `UNCLASSIFIED` entry 和 unknown lookup                             | 没有枚举发布候选的真实 definitions/prompts/tool contracts/handlers；未覆盖 pure wrapper、inventory mismatch、dispatch 前失败 | 建立真实 built-in inventory closure test 和负向 mutation fixtures                   |

#### 已确认的错误 AC tag

除上表外，Web API tests 中还有明确的 tag 错配，后续 AC scanner 必须能够发现，而不是把它们计为通过：

| 当前测试                      | 当前错误 tag | 实际行为      | 应如何处理                                                                                 |
| ----------------------------- | ------------ | ------------- | ------------------------------------------------------------------------------------------ |
| unknown gate/list run         | AC-FR0501-04 | 404 NOT_FOUND | 不能替代 stale revision/step/digest/challenge；改为正确接口错误 AC 或只作未映射回归测试    |
| unauthenticated gate decision | AC-FR0501-05 | 403 FORBIDDEN | 实际对应 AC-FR0501-03 的 human principal 要求，不是 artifact change invalidation           |
| unknown workflow create       | AC-FR1101-05 | 404 NOT_FOUND | 实际属于 AC-FR1101-04 的 workflow 不存在输入，不是 spec_change/backlog/GitHub Project 行为 |

#### 审计结论

这 28 个 AC 不是“只引用一下”这么单一：大部分测试确实运行了产品代码并有业务断言；但也绝对不能说已经完成测试。当前应把它们视为 **7 个可信 L1 起点、18 个待补全的部分证明、3 个必须重写的错误证明**。

后续修复必须先完成本表中的 L1 语义缺口，再按 test plan 补 L2/E2E。不能先把现有 tag 数量重新统计成 100%。

---

## 3. 当前真实 Gap 和优先级

### P0-1: 发布版本和 wheel 内容错误

#### 现状

- `pyproject.toml` 的项目版本仍是 `0.11.0`；
- `VERSION` 仍是 `0.10.0`；
- `[tool.setuptools] packages` 只列出 `louke`、`louke._tools`、`louke.web`；
- 当前 `louke.egg-info/SOURCES.txt` 不包含 `louke/runtime/`、`louke/opencode/`、`louke/web/api/`、`louke/web/pages/`；
- `serve.py` 还有硬编码的 `0.12`/`0.12.0`，其中有些表示项目 schema/最低兼容版本，有些表示当前安装版本，不能全局替换。

#### 风险

从源码目录运行测试会因为 Python 能直接看到所有文件而通过，但构建 wheel 后，新子包可能根本没有被安装。CI 当前只对 wheel 执行 `lk --help`，该命令不一定 import 所有 v0.12 子包，因此无法发现缺包。

这意味着 `v0.12.0` tag 可以在源码 checkout 中工作，但通过 wheel/pip 安装的用户拿不到同一产品。这是发布阻断项。

#### 决策

以 `v0.12.1` 修复，不移动、不删除、不重打 `v0.12.0` tag。

推荐将显式 packages 改为 package discovery，例如：

```toml
[tool.setuptools.packages.find]
include = ["louke*"]
```

具体实现可等价，但必须从构建出的 wheel 内容证明，而不能只检查源码目录。

版本来源必须收敛：

- `pyproject.toml` 和 installed METADATA 报告 `0.12.1`；
- `lk --version` 在 clean venv 中报告 `0.12.1`；
- `VERSION` 若仍被发布/脚本使用，必须同步为 `0.12.1`；若已废弃，应删除消费者并明确废弃，而不是继续漂移；
- workflow schema 版本、最低兼容版本、项目声明版本不得通过字符串全局替换误改。

#### 退出条件

构建 wheel 后，在一个不引用 repo 源码的 clean venv 中完成：

```bash
python -m build
python -m venv /tmp/louke-v0121-wheel-smoke
/tmp/louke-v0121-wheel-smoke/bin/pip install --force-reinstall dist/louke-0.12.1-*.whl
/tmp/louke-v0121-wheel-smoke/bin/lk --version
/tmp/louke-v0121-wheel-smoke/bin/python -c "import louke.runtime, louke.opencode, louke.web.api, louke.web.pages"
```

还必须在 `/tmp` 下的最小 Git workspace 中通过 installed wheel 启动一次 setup-only `lk serve` 并访问 `/health` 或 `/api/readiness`。测试进程结束后必须清理 server，不得留下后台进程。

---

### P0-2: `/api/runtime/bindings` 在生产 app 中被遮蔽

#### 现状

`louke/web/app.py` 先注册：

```python
Mount("/api/runtime", app=runtime_app),
```

之后才注册：

```python
Mount("/api/runtime/bindings", app=bindings_app),
```

Starlette 按顺序匹配 Mount，较宽的 `/api/runtime` 先消费请求。当前真实探针：

```text
GET /api/runtime/bindings/devon
404 {"error_code":"NOT_FOUND","message":"Not Found"}
```

现有 bindings API 测试直接测试 `louke.web.api.bindings.create_app()`，没有经过生产 `louke.web.app.create_app()`。`tests/e2e/test_v12_integration_e2e.py` 还使用 wrapper 绕开了生产路由，因此测试为绿但产品入口失败。

#### 风险

v0.14 的 Settings/模型绑定和 v0.12 FR-1301 都依赖该路径。若不先修，v0.14 UI 会在一个已知 404 API 上开发，并可能再次引入测试 wrapper 掩盖问题。

#### 修复顺序

1. 先增加一个针对完整 `louke.web.app.create_app(tmp_path)` 的失败 integration test。
2. 通过生产路径创建 bindings test run。
3. 通过生产路径读取默认 binding、修改 override、读取 audit。
4. 再调整 Mount 顺序，较具体路径必须先于较宽路径。
5. 扫描所有 Mount 前缀，增加通用 precedence smoke，防止 `/projects/.../gates` 一类问题复发。

禁止只修改 wrapper 测试或只给 `/api/runtime` 子应用增加一个假路由来吞掉 bindings。

#### 退出条件

至少断言：

- `POST /api/runtime/bindings/runs` 不返回 404；
- `GET /api/runtime/bindings/devon?run_id=...` 返回 bindings schema；
- `PUT /api/runtime/bindings/devon?run_id=...` 修改 override；
- `GET /api/runtime/bindings/devon/audit?run_id=...` 返回审计记录；
- 请求实际经过顶层 `create_app()`，测试不得直接构造 bindings sub-app。

---

### P0-3: CI 没有执行 v0.12 Python 行为门

#### 现状

`.github/workflows/ci.yml` 当前主要执行：

- pre-commit；
- build；
- clean venv 安装；
- `lk --help`；
- BATS。

它没有执行：

- `pytest tests/unit`；
- `pytest tests/integration`；
- runtime coverage；
- contract-adapter product tests；
- wheel 中 v0.12 子包 import/start smoke。

`.github/workflows/louke-ci.yml` 还通过 `pip install louke` 安装公开源上的版本，而不是当前 checkout 构建出的 wheel。这样可能用旧发布版的 `lk` 扫描新源码，不能证明当前提交可发布。

#### 风险

当前 397 个 unit 和 190 个所谓 E2E 即使本地为绿，也不会在每次 push 自动阻止回归。发布包漏文件同样不会被 `lk --help` 捕获。

#### 决策

v0.12.1 必须先建立快速、稳定、每次 push 可运行的门；完整测试分类重排留给 v0.13。

CI 至少分为：

1. `unit-integration`：支持的 Python 版本矩阵或明确的最小/主版本矩阵；
2. `package-smoke`：构建 wheel、clean install、import/start；
3. `bats-legacy`：保留旧 pipeline 回归；
4. `e2e-chromium`：单一支持浏览器的有限主旅程，可按成本放在 main/PR required gate；
5. `real-opencode`：有环境条件的 release/nightly L3，不得伪装为默认 CI 已执行。

测试依赖必须在项目中声明。推荐增加明确的 `[project.optional-dependencies].test` extra，而不是依赖开发机恰好安装。至少包含 `pytest`、`pytest-cov` 和 `playwright`；版本范围必须先在 Python 3.11-3.14 CI 矩阵中验证，再写入 `pyproject.toml`。不得提交无版本约束的临时依赖，也不得猜测一个未经 CI 验证的版本范围。

#### 退出条件

- PR/push 会真实执行 unit 和 integration；
- coverage 工具在 clean CI 环境可用；
- coverage 门的测量对象和阈值明确；
- package smoke 从当前 checkout 构建 wheel；
- `louke-ci` 不再静默使用一个可能更旧的 PyPI Louke 来验证当前版本，或者明确说明该 job 只验证向后兼容而非当前构建；
- CI 失败时能从 job 名称区分 unit、integration、package、browser 和 L3。

---

### P1-1: 测试分层与批准的 test plan 不一致

#### 现状

批准的 test plan 指定：

- `tests/unit/runtime/`：纯规则；
- `tests/integration/runtime/`：真实临时 workspace/store、HTTP TestClient、contract adapter；
- `tests/e2e/`：实际 `lk`/server/Projects UI journey；
- `tests/ground_truth/`：独立计算器，不 import `louke.*`。

当前实际情况：

- `tests/integration/` 不存在；
- `tests/ground_truth/` 不存在；
- `tests/e2e/test_v12_integration_e2e.py` 名称已承认自己是 integration，但被标为 E2E；
- 多个 `tests/e2e/test_fr*.py` 直接 import Runtime 域对象，实际上更接近 unit 或 component test；
- 旧 v0.11 browser compatibility 测试和 v0.12 产品 E2E 混在同一目录；
- 当前 M-E2E gate 按 AC tag 数量扫描，进一步诱导把非 E2E 测试放入 E2E 目录。

#### 决策

v0.12.1 只做最低限度纠偏：

1. 建立 `tests/integration/runtime/`；
2. 将 `test_v12_integration_e2e.py` 移入 integration，并去掉错误的 E2E marker；
3. 新增的顶层 production-app 路由测试全部放 integration；
4. 为 graph/digest/trace 至少建立最小独立 ground-truth fixture，或者生成一个明确的未完成项阻止声称 test plan 全部满足；
5. 不在 v0.12.1 大规模移动所有历史测试，完整 reflow 由 v0.13 执行。

#### 决策理由

大规模移动测试会改变历史 M-E2E evidence 路径，并容易把稳定化 patch 变成测试架构重写。当前最重要的是让“每次 push 的快速 integration”真实存在，并让新增修复不再继续污染 E2E。

---

### P1-2: 缺少一个可信的 v0.12 单浏览器产品主旅程

#### 现状

当前 6 个 Playwright case 来自旧 UI 的 home/wiki/login 双浏览器兼容测试。v0.12 明确不要求多浏览器矩阵，但 test plan 要求一个支持浏览器上的 Projects UI 主旅程，且明确说明 API-only TestClient 不能替代 UI 主旅程。

当前 `test_nfr0301_golden_journey__e2e.py` 提供大量产品语义证据，但其实现方式不等同于真实浏览器从 setup/Projects/Runs/Gates 操作页面。

#### 决策

v0.12.1 只补 **一个 Chromium 主旅程**，不为即将由 v0.14 重写的视觉布局建立大规模 DOM 测试。

该旅程至少证明：

1. installed wheel 启动 setup-only server；
2. 用户能进入 setup/readiness；
3. 用户能创建 Project；
4. Projects 列表能看到 active run；
5. 用户能打开 run/graph；
6. 用户能完成至少一个真实 UI 控制动作，例如 gate decision 或 model binding；
7. 刷新后状态仍存在；
8. server 能被可靠清理。

使用语义 selector 或稳定 `data-testid`，不得断言像素、颜色和 v0.14 会重写的布局细节。

若该旅程因现有 UI 缺少稳定入口无法完成，必须记录为真实产品 gap；不能用直接调用 API 的 helper 假装浏览器已完成操作。

> **QoderWork:** 与本文决策不一致。本文 §8 将 Chromium 主旅程列入「现在修」，但我认为 **P1-2 应推迟到 v0.14**。理由：v0.14 会重写整个 UI（toolbar/sidebar/tabs），现在写的 Chromium 旅程测试注定要重写。本文也承认「若该旅程因现有 UI 缺少稳定入口无法完成，必须记录为真实产品 gap」——这说明当前 UI 可能根本无法支持一个可靠的旅程。与其花成本写一个注定废弃的测试并可能遇到入口缺失的问题，不如等 v0.14 UI 稳定后一次到位。§5.2 已将「当前页面的视觉重写」和「大量 DOM/截图测试」列入 v0.14 修，Chromium 旅程测试本质上属于同一类。
>> **Aaron:** 同意QoderWork，推迟到 v0.14.


---

### P1-3: M-E2E evidence 与 DoD 表述不一致

#### 现状

当前 stage results 中：

- `M-E2E/author-result.json` 的 `verdict` 是 `fail`；
- `M-E2E/gate-result.json` 的 `verdict` 是 `fail`；
- `M-E2E/waiver.json` 由 human 接受了 AC trace 结构和历史 R-G-R 风险；
- `project.toml` 的 DoD 却写“unit/integration/e2e 全通过”。

Waiver 本身可以是合法的里程碑决定，但“waived”不等于原始 gate “pass”。

#### 决策

- 不得修改历史 `v0.12.0` fail/waiver artifact 来伪造当时通过；
- 为 `v0.12.1` 生成新的、可追踪的验证证据；
- project metadata 应区分 `passed`、`waived`、`skipped with scope` 和 `not run`；
- real OpenCode L3 必须记录确切命令、版本、adapter kind 和结果；
- browser 未安装或未执行不能写成 browser E2E pass。

如果现有 stage-results schema 不支持 patch release，先增加一个明确的 `v0.12.1` release audit 文档或使用现有工具支持的独立 spec/run；不得手改旧 JSON 的 verdict。

> **QoderWork:** 与本文决策不一致。本文 §8 将 evidence reconciliation 列入「现在修」，但我认为 **P1-3 应推迟到 v0.13**。理由：v0.13 story 第 4 条定义了 waive 语义（什么可以 waive、什么不可以、waiver 的 actor/reason/scope/expiry），这正是 P1-3 需要的「pass/waived/skipped/not-run」区分标准的上游输入。如果 v0.12.1 先定义了 evidence 格式，v0.13 的 waive 语义可能与该格式不兼容，导致二次修改。§5.1 已经写了「v0.13 接手的工作」包含「有严格边界的 waive」，evidence 表述应在 waive 语义确定后统一修正。
>> **Aaron:** 同意推迟


---

### P1-4: 旧 gap 生成方法错误

#### 问题

旧算法以“Story 涉及某 FR”为依据，要求该 FR 的全部 AC 都出现在该 Story 的 E2E 中，导致：

- 一个 AC 被多个 Story 重复计算；
- 出现 `8/7`、`4/3` 这类分子大于分母的结果；
- L1/L2 AC 被错误要求进入 E2E；
- unit 明明存在却被报告为 0；
- v0.11 和 v0.12 同编号 FR 的测试容易混淆。

#### 正确模型

以后必须维护两个不同矩阵：

1. **AC coverage matrix**：每个 AC 至少映射到一个主测试层和具体测试；允许 L1/L2/E2E/L3，不要求全部层都有。
2. **Story scenario E2E matrix**：每个 Story 场景映射到 1 个或少量用户主旅程，验证量化的 happy path，不以覆盖该场景涉及 FR 的所有异常 AC 为目标。

统计时：

- AC 以规范化 ID 去重；
- 必须区分 spec ID，不能只按 `FR-xxxx`；
- 必须解析实际 pytest collection，而不是只扫描任意 docstring 文本；
- skipped、xfail、not collected、pass 分开统计；
- unit 引用、integration pass、E2E pass 和 real L3 pass 分开报告；
- 不能把“有引用”写成“行为已通过”。

---

### P2-1: 双 store 不应在本轮盲目统一

#### 现状

v0.11 Web 文件 store 和 v0.12 Runtime SQLite store 同时存在。旧报告直接把“技术不同”判断为必须统一。

#### 决策

v0.12.1 不进行全面 store 合并。先验证 ownership：

- 文档、Wiki、旧 Web 用户资料由谁权威写入；
- WorkflowRun、step attempt、gate、event、trace 由 SQLite Runtime 权威写入；
- 是否有同一个业务字段被两套 store 同时写入；
- archive/readiness/project identity 是否存在不一致或非原子跨 store 更新。

只有发现“同一事实有两个权威写入者”或“必需事务跨两个 store 无法恢复”时，才创建具体修复 issue。技术后端不同本身不是缺陷。

全面持久化架构调整应进入 v0.13 architecture，而不是混入 v0.12.1 发布修复。

---

### P2-2: `intent_api.py` 是否保留由 v0.14 Chat/harness 决定

旧 `intent_api.py` 的 `executed=false` 是 v0.11 的诚实限制。v0.14 将重新定义 Chat、Agent 选择、harness `/` 命令和 shell `!` 命令。

v0.12.1 不应把关键词分类器临时接到 Runtime 形成另一条控制路径。这样会绕过 v0.12“Runtime 是唯一状态写入者”的原则。

本轮只需保证：

- API 不谎报已执行；
- 不允许 intent classifier 直接写 run/gate；
- v0.14 M-ARCH 明确决定删除、适配或替换该模块。

---

## 4. v0.12.1 详细执行路径

以下批次必须按顺序执行。每个批次应独立提交并保持可回滚。低能力执行模型不得同时展开多个批次后再统一测试。

### Batch 0: 建立不可争议的修复基线

#### 目标

在修改业务代码前固定当前结果，避免修复过程中把已有失败误认为新回归。

#### 操作

1. 记录 `git rev-parse HEAD` 和 `git status --short`。
2. 不修改、不删除用户当前未提交的 v0.13/v0.14/v0.15 story 和 `louke/agents/Story.md`。
3. 运行 unit：

```bash
.venv/bin/python -m pytest tests/unit -q
```

4. 运行不需要浏览器的当前 E2E：

```bash
LOUKE_SKIP_LIVE_SERVER=1 .venv/bin/python -m pytest -m e2e tests/e2e -q
```

5. 记录 bindings 生产路由当前为 404 的失败测试或探针。
6. 保存 wheel 当前包清单，证明新子包缺失。

#### 退出条件

- 基线结果和本文件第 2.2 节一致，或差异已解释；
- 没有改动无关用户文件；
- 后续每个修复都能对应一个基线失败。

---

### Batch 1: 修复 package discovery 和版本来源

#### 测试先行

先增加 package smoke，要求从 wheel 安装后 import：

- `louke.runtime`；
- `louke.opencode`；
- `louke.web.api`；
- `louke.web.pages`；
- `louke.cli_v12`。

测试还应断言 installed `lk --version` 与 wheel METADATA 一致。

#### 实现

1. 修复 setuptools package discovery。
2. 将发布版本设为 `0.12.1`。
3. 审计 `VERSION` 是否仍有消费者并同步或废弃。
4. 审计 `serve.py` 的硬编码版本：
   - 当前安装版本应从 `louke.__version__`/METADATA 读取；
   - workflow/project schema 版本继续使用其合同值；
   - `_MIN_GLOBAL_VERSION` 只有兼容政策变化时才修改；
   - 禁止全仓库搜索替换 `0.12.0`。
5. 构建 sdist 和 wheel。

#### 验证

```bash
python -m build
python -m venv /tmp/louke-v0121-wheel-smoke
/tmp/louke-v0121-wheel-smoke/bin/pip install --force-reinstall dist/louke-0.12.1-*.whl
/tmp/louke-v0121-wheel-smoke/bin/lk --version
/tmp/louke-v0121-wheel-smoke/bin/python -c "import louke.runtime, louke.opencode, louke.web.api, louke.web.pages, louke.cli_v12"
```

#### 提交边界

本批次只包含 packaging/version/smoke，不顺手改路由或 UI。

---

### Batch 2: 修复生产 app 路由装配

#### 测试先行

在 `tests/integration/` 增加完整 app 测试。必须 import 顶层 `create_app`，不得只 import sub-app。

先让以下测试在旧代码上失败：

```text
POST /api/runtime/bindings/runs
GET  /api/runtime/bindings/{agent}?run_id=...
PUT  /api/runtime/bindings/{agent}?run_id=...
GET  /api/runtime/bindings/{agent}/audit?run_id=...
```

#### 实现

1. 将具体 Mount 放在宽 Mount 前。
2. 检查 `/api/runtime/bindings` 是否应长期作为 `/api/runtime` 子路由；如果只是调整 Mount 顺序即可，不做大规模 API 重命名。
3. 检查其他 prefix shadow：
   - `/projects/{id}/gates` vs `/projects`；
   - `/runs/{id}`；
   - `/api/v12/discussions` vs 旧 discussions；
   - `/api/readiness`、`/api/setup`、`/api/migration`。
4. 所有修复都必须通过顶层 app 测试。

#### 验证

```bash
.venv/bin/python -m pytest tests/integration -q
.venv/bin/python -m pytest tests/unit/web -q
```

#### 提交边界

本批次只修 production composition 和对应 integration tests，不改页面视觉。

---

### Batch 3: 建立最小正确测试分层

#### 操作

1. 创建 `tests/integration/runtime/`。
2. 移动/拆分明显的 TestClient + real temporary store 测试。
3. 首先处理 `test_v12_integration_e2e.py`，因为它已经明确命名为 integration。
4. 审计被移动测试使用的 fixture；共享 fixture 应放在 `tests/conftest.py` 或目标层自己的 `conftest.py`，不得从 `tests/e2e/conftest.py` 导入。
5. 保持 AC tag，不通过复制文件制造双重覆盖。
6. E2E 目录只留下真正跨进程/用户入口旅程和明确 L3 测试。
7. 对暂时不移动的历史文件建立 reflow backlog，交给 v0.13。
8. 建立最小 `tests/ground_truth/`：至少独立验证一个 definition graph 预期和一个 artifact digest；该目录不得 import `louke.*`。

#### 判断规则

| 测试特征                                                             | 放置位置                         |
| -------------------------------------------------------------------- | -------------------------------- |
| 纯函数、状态机规则、digest/CAS 输入校验                              | unit                             |
| Starlette TestClient、真实 SQLite/temp workspace、重启恢复、并发事务 | integration                      |
| 启动 installed `lk serve`、浏览器或真实 CLI、从用户入口走完整路径    | E2E                              |
| 真实 OpenCode server/provider                                        | L3 marker，可位于 E2E 但单独 job |
| 不 import 产品、独立计算 expected                                    | ground_truth                     |

#### 验证

```bash
.venv/bin/python -m pytest tests/unit tests/integration -q
LOUKE_SKIP_LIVE_SERVER=1 .venv/bin/python -m pytest -m e2e tests/e2e -q
! rg -n '(^|[[:space:]])(from|import)[[:space:]]+louke' tests/ground_truth
```

第二条在本批次只验证现有非浏览器 E2E 没有因移层回归；真实 Chromium 运行在 Batch 5 完成。第三条 shell 检查应按 CI shell 兼容性实现；命令只是表达“不允许 ground_truth import louke”的门。

---

### Batch 4: 把 unit/integration/package smoke 接入 CI

#### 操作

1. 在项目 test extra 中声明 pytest、coverage 和 browser 所需依赖。
2. CI 从当前 checkout 安装 `.[test]` 或当前 wheel。
3. 每次 push/PR 至少运行：

```bash
python -m pytest tests/unit tests/integration --cov=louke.runtime --cov-report=term-missing
```

4. coverage 阈值按批准合同保持，不得为了让 CI 变绿而降低。
5. 保留 BATS job 验证 legacy pipeline。
6. package smoke 必须安装刚构建的 wheel。
7. AC scan 必须使用当前 checkout/wheel 的 `lk`，不能无说明地使用 PyPI 旧版本。
8. 缓慢或需要外部服务的 real OpenCode L3 独立运行和报告。

#### 失败处理

- 如果 coverage 工具当前缺失，补依赖，不删除 coverage 参数；
- 如果 Python 3.14 上第三方依赖不兼容，应单独记录兼容 issue，不能让所有版本静默 allowed failure；
- 如果 browser 安装成本高，可将 browser job 与快速 integration 分开，但不能把 browser 未执行写成 pass。

#### 退出条件

required CI 能阻止以下人为回归：

- 删除 `louke/runtime` package；
- 恢复错误 Mount 顺序；
- 破坏 gate stale digest；
- 破坏 SQLite recovery；
- coverage 低于门槛。

---

### Batch 5: 增加一个稳定的 Chromium 产品旅程

#### 实施原则

- 只支持 Chromium，不恢复 v0.12 已排除的浏览器矩阵要求；
- 使用 installed wheel 启动 server；
- 使用真实页面入口，不以 API helper 代替关键用户动作；
- OpenCode 可用诚实标识的 controllable adapter；
- selector 绑定语义控件，不绑定 CSS 布局；
- 旅程失败必须保留 server log 和页面错误信息；
- teardown 必须执行，即使测试失败。

安装 `playwright` Python 依赖并不等于安装了浏览器。CI 在运行本批次前还必须显式安装 Chromium，例如：

```bash
python -m playwright install --with-deps chromium
```

本地非 Linux 环境可使用适合该平台的等价命令，但最终 required CI 证据必须来自声明支持的 CI 环境。

#### 最小场景

```text
clean Git workspace
  -> lk serve setup-only
  -> setup/readiness
  -> create project
  -> active project visible
  -> open run graph
  -> perform one gate or binding action
  -> reload
  -> state persists and audit/detail is readable
  -> stop server and clean workspace
```

不要在本批次验证 v0.14 toolbar/sidebar/tab 结构，也不要增加截图像素比较。

---

### Batch 6: 重新生成 gap/evidence 并发布 v0.12.1

#### 必须重新生成的报告

1. package content report；
2. unit/integration/E2E/L3 分层结果；
3. AC coverage matrix，按 spec ID + AC ID 去重；
4. Story scenario E2E matrix；
5. skipped/waived/not-run 明细；
6. production route smoke；
7. clean wheel smoke；
8. CI run URL 或可审计引用。

#### 元数据规则

- `v0.12.0` 历史不重写；
- 旧 fail/waiver artifact 不删除；
- `v0.12.1` 新结果独立记录；
- DoD 只写实际结果；
- 若某门通过 waiver，必须写“waived”及风险，不写“pass”；
- real L3 只在实际运行时写 pass；
- tag 只能在 clean wheel smoke、required CI、生产 route integration 和单浏览器主旅程均满足后创建。

#### 发布退出门

`v0.12.1` 只有同时满足以下条件才可发布：

- [ ] wheel METADATA 和 `lk --version` 均为 `0.12.1`；
- [ ] wheel 包含 runtime/opencode/web.api/web.pages；
- [ ] clean venv import 和 setup-only serve smoke 通过；
- [ ] production bindings route 不再 404；
- [ ] unit 和 integration 为绿；
- [ ] runtime coverage 达到批准阈值；
- [ ] BATS legacy 回归为绿；
- [ ] 一个 Chromium v0.12 产品主旅程为绿；
- [ ] real OpenCode L3 有可审计的既有或新鲜兼容证据；
- [ ] pass/skip/waive/not-run 表述一致；
- [ ] 没有修改 v0.13/v0.14/v0.15 story 的产品范围；
- [ ] 创建新 `v0.12.1` tag，不移动 `v0.12.0`。

---

## 5. v0.13、v0.14、v0.15 的衔接

### 5.1 v0.13 接手的工作

v0.13 应在 v0.12.1 之后正式处理：

- 独立、充分、必要且使用 EARS 的 Story 阶段；
- integration 与 E2E 的完整目录/marker/gate reflow；
- 每次 push 的快速 integration report 如何被 Maestro 消费；
- Story scenario 与 E2E 一一对应及 happy-path 量化标准；
- 人工把流程拉回某个阶段；
- 人工 waive 的状态、范围、证据、审计和恢复语义。

v0.13 的 waive 必须先解决与 v0.12 不可绕过门禁的冲突。推荐边界：

- 可 waive：明确列出的非关键环境检查、已知外部不稳定测试、政策允许的阶段结果；
- 不可 waive：requirements human approval、M-LOCK human approval、Runtime CAS/原子性、身份/secret 安全、artifact digest freshness、Agent 自批/自跳限制；
- 任一 waiver 必须包含 actor、reason、scope、expiry/recheck 条件和审计事件；
- waiver 不能把失败证据改写为原始通过，只能改变“是否允许继续”的控制决定。

最终边界必须在 v0.13 M-SPEC/M-ARCH 由用户批准，不能由实现者自行决定。

### 5.2 v0.14 可以复用但不能提前实现的部分

v0.14 Runs 页面明确依赖 v0.12 的 Projects、workflow graph、artifact/detail 和 trace 合同。因此 v0.12.1 必须先保证这些接口能从发布 wheel 和生产 app 使用。

可以延后到 v0.14：

- toolbar/sidebar/tab 的新布局；
- 当前页面的视觉重写；
- 大量 DOM/截图测试；
- Chat/harness 对 `intent_api.py` 的替换；
- Settings 中模型等级 S/A/B 的新产品语义；
- End User Docs AI 辅助编辑。

不能延后到 v0.14：

- wheel 缺包；
- bindings 生产路由 404；
- CI 不跑 Runtime 测试；
- Runtime gate/recovery/inventory 没有正确测试层；
- 发布证据将 waived 写成 passed。

### 5.3 v0.15 为什么必须最后做

v0.15 的 message catalog、locale persistence 和运行时切换依赖 v0.14 已稳定的 toolbar、sidebar、tabs 和 Settings。如果提前实现，v0.14 每次调整 UI chrome 都会让 message ID、catalog 和测试重复变化。

因此 v0.15 只保持 story ready，不进入实现。

---

## 6. 对低能力执行模型的强制约束

以下规则用于防止修复范围失控：

1. **一次只执行一个 Batch。** 每个 Batch 独立测试、独立 review、独立提交。
2. **测试先行。** P0 缺陷必须先有能在旧代码上失败的测试，再修实现。
3. **不得改写历史。** 不移动/删除 `v0.12.0` tag，不把旧 fail/waiver JSON 手改为 pass。
4. **不得全局替换版本字符串。** 先区分 package version、workflow schema、project version、minimum compatible version 和示例 placeholder。
5. **不得用 sub-app test 代替 production app test。** 路由修复必须经过顶层 `create_app()`。
6. **不得复制测试制造覆盖。** 移层时使用 `git mv` 或拆分职责，不保留两份相同测试只为了 AC 数量。
7. **不得把全部 28 个 AC 加入浏览器 E2E。** 按第 2.3 节分层。
8. **不得为了 CI 变绿降低 coverage 阈值、删除断言或增加无 issue skip。**
9. **不得无设计合并两套 store。** 先证明重复权威写入或事务问题。
10. **不得实现 v0.14 UI。** 本轮 UI 只允许增加稳定 selector 和一个 v0.12 Chromium 主旅程所需的最小可测试性修改。
11. **不得修改用户未提交的规划文件。** 当前 `v0.13`、`v0.14`、`v0.15` story 及其他用户工作树改动必须保留。
12. **不得把环境错误写成产品通过。** Playwright 未安装、真实 OpenCode 未运行、browser skipped 都必须单独报告。
13. **遇到生产合同变化必须停下。** 如果修复需要重命名 API、改变 gate 语义或改变持久化 schema，先回到用户/架构评审，不能自行扩展 patch。

---

## 7. 推荐 Issue 拆分

为降低低能力模型一次处理过多上下文的风险，建议至少拆成以下 issue：

| Issue                           | 范围                                     | 依赖     | 完成证据                  |
| ------------------------------- | ---------------------------------------- | -------- | ------------------------- |
| S1 package discovery            | wheel 包含全部 v0.12 子包                | 无       | clean wheel import smoke  |
| S2 version convergence          | METADATA/CLI/VERSION/serve identity 一致 | S1       | clean venv `lk --version` |
| S3 production route precedence  | 修复 bindings 404，扫描相邻 Mount        | 无       | top-level app integration |
| S4 integration test root        | 建目录并移动明显 integration test        | S3       | fast integration command  |
| S5 minimal ground truth         | graph + digest 独立 expected             | S4       | no `louke` import gate    |
| S6 CI unit/integration/coverage | 当前 checkout 的快速门                   | S1/S4/S5 | required CI green         |
| S7 package/server smoke         | installed wheel setup-only serve         | S1/S2    | process smoke report      |
| S8 Chromium product journey     | 一个 v0.12 用户主旅程                    | S3/S7    | Playwright Chromium green |
| S9 evidence reconciliation      | 分层矩阵、waiver/DoD 一致                | S6/S8    | v0.12.1 release audit     |
| S10 v0.12.1 release             | tag 和 release metadata                  | S1-S9    | immutable v0.12.1 tag     |

不要把 S1-S10 合并成一个“大修复” issue。S1、S3 是最高优先级，可以分别完成，但发布前必须汇合到同一个经过完整验证的 commit。

---

## 8. 最终决策摘要

### 现在修

- wheel/package discovery；
- 版本漂移；
- production bindings route 404；
- 每次 push 的 unit/integration/coverage；
- 最小正确测试分层；
- clean installed-wheel server smoke；
- 一个 Chromium v0.12 产品主旅程；
- M-E2E/waiver/DoD 证据一致性。

### v0.13 修

- 完整测试 reflow；
- Story 阶段；
- CI report 驱动的 workflow interruption；
- 人工回退；
- 有严格边界的 waive；
- 需要架构决定的 store ownership 改造。

### v0.14 修

- 新 toolbar/sidebar/tab UI；
- Runs/artifact 的新视觉表达；
- Chat/harness；
- Settings 和 S/A/B 模型配置；
- 当前 UI E2E 的全面替换。

### v0.15 修

- UI message catalog；
- `en`/`zh-CN`；
- locale persistence、fallback 和运行时切换。

本轮的成功标准不是“让 gap 数字变成 100%”，而是证明用户安装到的 `v0.12.1` 与源码测试的是同一个产品、生产入口确实可达、每次提交都有正确层级的自动门，并且所有 pass/skip/waive 声明都与真实证据一致。


---

## 战略评审补充（inline-discussion）

> **QoderWork:** 本文 §5 已详述 v0.13/v0.14/v0.15 的衔接关系，但以下三点未被覆盖：
>
> **1. v0.13 story 太薄。** 目前只有 4 条，而 v0.12 有 18 个场景、v0.14 有 17 条。建议 spec 阶段充分展开——特别是第 2 条（integration/E2E 区分）需要明确：哪些测试归哪层、Maestro 如何在 CI report 后决策打断工作流、E2E 的 happy path 量化指标是什么、以及第 3 条「流程拉回」的合法回退点和安全约束。
>
> **2. v0.14 范围很大，建议 spec 阶段考虑拆分。** 17 条 story 涵盖 toolbar、sidebar、5 个 main panel tab（Chat、Dev Docs、End User Docs、Wiki、Runs）、Settings、模型绑定、AI 辅助编辑。其中第 16 条（End User Docs AI 辅助编辑）是一个独立能力，可以拆为 v0.14.1 或单独一个 spec，避免大版本交付压力过重。
>
> **3. v0.14 多处写「复用 v0.12-001 FR-1201/FR-1901/FR-2201」，但 v0.12 的这些 Web 端点刚建好、尚未经过生产验证。** 这正是 v0.12.1 P0-2 必须先修 bindings 404 的原因之一——v0.14 会在一个未验证的 API 层上建 UI，风险较高。
>> **Aaron:** ok, 后面开发0.13/0.14时考虑
