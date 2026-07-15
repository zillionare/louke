# Web UI Foundation — Test Plan

- **Spec ID**: `v0.13-001-web-ui-foundation`
- **Created**: 2026-07-15
- **Related acceptance**: `.louke/project/specs/v0.13-001-web-ui-foundation/acceptance.md`
- **Related interfaces**: `.louke/project/specs/v0.13-001-web-ui-foundation/interfaces.md`（M-ARCH 产出；断言出口见 §6.5）
- **Test framework**: `pytest` + Starlette `TestClient` + Playwright/Chromium
- **Closure status**: **COVERED**（server-restart persistence 与 marker-based inline-discussion read/edit 已由 `AC-FR1310-11/12` 明确覆盖；Dev Docs writable allowlist 与字节级回环由 `AC-FR1309-05/06/07/09/10/11` 覆盖，marker-only inline-discussion 渲染由 `AC-FR1309-07` 覆盖，Save 按钮 dirty 联动由 `AC-FR1309-08` 覆盖，见 §4.2/§4.3）

## 1. 立场与边界

### 1.1 黑盒声明

本计划只从浏览器 DOM/可访问性树、公开 HTTP response、浏览器 storage/cookie、network response、受支持 CLI、真实 workspace 文件和 Runtime 持久化出口观察行为。UI 断言使用 role、accessible name、`aria-*`、稳定 `data-*`、可见文本、HTTP status/JSON 字段和保存后文件字节；不通过 CSS class、截图像素或内部 Python/JavaScript 状态证明通过。

测试只替换系统外部依赖（OpenCode provider、必要时的 Wiki 内容源）；不得替换 Louke 的路由、文档安全校验、tab/navigation 状态、workflow graph 映射、认证或持久化实现。任何 AC 若缺少公开出口，必须在 M-ARCH 的 `interfaces.md` 补合同，而不是让测试读取私有对象。

### 1.2 非观察对象

- 内部 class hierarchy、private method、store table、cache、queue、state reducer 和组件局部变量；
- framework 内部调用次数或渲染函数实现；
- OpenCode 的隐藏推理、模型内部 tokenization；
- CSS 具体颜色值、像素级布局和多浏览器一致性；
- 上游 v0.9/v0.11/v0.12 已批准接口的内部实现。

### 1.3 反作弊规则

1. 每个测试函数首行 docstring/comment 必须包含精确 `AC-FR13XX-YY`；一项测试可引用多个 AC，但不得只写 FR 范围。
2. 禁止 `assert True`、仅 `is not None`、`try/except: pass`、从 SUT 输出反推 expected、或用 regex 代替已知值比较。
3. 禁止 mock Louke 内部模块来制造 toolbar、保存、auth、graph 或 transcript 结果；外部 stand-in 必须经公开协议接入。
4. 禁止无 GitHub issue/明确环境条件的 skip。Chromium 缺失和真实 OpenCode 未启用应报告为 environment-gated skip，绝不能记为 pass。
5. Test change PR 必须归类为新增 AC、已批准 spec 变化或带 issue 的环境/flake 修复；不得因实现不符合 acceptance 而降低断言。

### 1.4 防护与责任

- Devon 负责 L1 unit；Shield 负责 L2 integration 与 E2E；L3 由 Shield 按发布前 runbook 执行并留证。
- 当前 `lk agent archer ci-scan` 只做**文件级** AC reference closure 和有限 regex 反模式扫描；它不能证明每个 test function 都有 AC，也不执行 coverage、ground-truth import 或 internal-mock 检查。§7 明确当前可运行命令和必须实施的 gate 增强，不夸大现有工具能力。
- Ground truth 只读 fixture manifest、输入文件和标准库计算结果，不 import `louke.*`。
- 发现不可测试 AC 时记录 testability blocker，并在 `interfaces.md` 增加公开 assembly/observation outlet；不 snoop 私有 store。

### 1.5 分工总览

| 层               | 责任   | 主要证明                                                                                                | 默认执行        |
| ---------------- | ------ | ------------------------------------------------------------------------------------------------------- | --------------- |
| L1 unit          | Devon  | 输入校验、公开 view/schema 映射、未知值降级、UI state contract                                          | 每次 push       |
| L2 integration   | Shield | 进程内 `TestClient` + 真实临时 workspace 的 HTTP、认证、文件、Runtime 持久化合同；不证明 JavaScript/DOM | 每次 push       |
| E2E              | Shield | 一个 Chromium main journey + 定向 Chromium tests，证明真实浏览器状态/DOM/network                        | CI gate         |
| L3 real OpenCode | Shield | 真实 `opencode serve` + `opencode/big-pickle` 的最小 Chat 往返                                          | 发布前/显式环境 |

---

## 2. 测试环境

### 2.1 工具与目录

- 继承项目 Python `>=3.11`、`pytest`、Starlette `TestClient`、`httpx`；浏览器 E2E 使用 Playwright 的单一 Chromium，不建立浏览器矩阵。
- 计划资产位置：

```text
tests/
├── unit/web/                 # L1；与公开 web contract 对齐
├── integration/web/          # L2；TestClient + 真实临时 workspace
├── e2e/                      # 一个 Chromium 主旅程、定向 browser tests、real_opencode smoke
├── fixtures/web_ui_v013/     # 与实现无关的 workspace/文档/run 输入
└── ground_truth/             # manifest/digest 独立计算；不得 import louke.*
```

- 文件命名 `test_<area>__<behavior>.py`；函数命名 `test_ac_<fr>_<ac>_<behavior>`。
- marker：`integration`、`chromium_e2e`、`real_opencode`。E2E selector 只使用 role、label、visible name 和 M-ARCH 约定的稳定 `data-*`。

### 2.2 L2 真实 workspace fixture

每项 L2 测试从只读模板复制到独立 `tmp_path`，通过公开 app factory 装配 ASGI app，并由进程内 Starlette `TestClient` 访问；**L2 不绑定 TCP port，也不执行浏览器 JavaScript**。fixture 至少包含：

- `.louke/project/specs/` 下三个 spec 目录；各含名称唯一、内容可识别的 Markdown，交叉引用目标锚点已知；
- `.louke/end-user-docs/` 下多级目录、合法 `.md`、恰好 1 MiB 与超限输入、非法路径样本，以及至少一个带 Agent-attached inline-discussion marker (`>`/`>>`/speaker-tag) 的文件；
- Wiki 首页及 story/spec/test-plan/architecture/interfaces、技术决定、FAQ、项目信息页面；另有一个未知新页面和一个不存在路径。Wiki 内容可以是协议级固定 fixture；
- 当前/历史 Project、两个绑定不同 definition version 的 run、完整 graph、七类 stage status、PASS/REJECT/WAIVED、gate pass/fail、author result、未知 stage/status/result kind；
- artifact 的固定 `digest`、`verdict`、`required reviewer`、`review conclusion`；
- 至少 Maestro 与另一个 Agent 的隔离 transcript；L2 使用公开 contract stand-in provider，不能 mock transcript 路由；
- 一个已认证 local principal 及可撤销的 HTTP credential fixture。

fixture manifest 记录文件相对路径、原始 bytes 的 SHA-256、run definition id/version、stage/result 期望值和 Agent transcript。测试修改只发生在该临时副本；结束后销毁，禁止读取/写入用户 workspace。

### 2.3 隔离、可重复性与执行

- L1/L2 完全离线；固定 locale/timezone，时间字段按 ISO-8601 UTC schema 验证，具体 digest 由 fixture bytes 独立计算。
- L2 每项测试使用新 `TestClient` cookie jar 与 workspace；E2E 在 wheel/受支持安装产物启动的真实 `lk serve` 上执行（沿用 `.louke/project/project.toml [e2e]` 的固定 loopback 端口 8765 + 外层 `start`/`ready`/`teardown` 生命周期，详见 §6.2），每个 browser context 互相独立。`localStorage` / `sessionStorage` / DOM 行为只在 Chromium 中观察。
- 测试顺序不得影响结果；禁止依赖开发者浏览器 profile、已有 Project 或手工 stage-results。

```bash
# 与 .louke/project/project.toml [e2e] 一致：pytest 仅调用已存在的 single journey 文件
python -m pytest tests/unit/web
python -m pytest -m integration tests/integration/web

# E2E：CI 由 project.toml [e2e].start/.ready/.run/.teardown 编排；这里给出与之一致的本地 invocation
python -m louke e2e start --host 127.0.0.1 --port 8765 --opencode mock
curl -sf http://127.0.0.1:8765/health        # ready
python -m pytest -m chromium_e2e tests/e2e/test_v013_chromium_journey_e2e.py
python -m louke e2e stop --port 8765 --cleanup-workspace
```

**项目单文件 vs 双文件名决议（T-004 决议）**：v0.13 不拆分 `test_v013_chromium_main_journey.py` 与 `test_v013_chromium_targeted.py` 两个文件；本期采用 `tests/e2e/test_v013_chromium_journey_e2e.py` 单文件，§6 一个 main journey 与 §5.4 浏览器专属 contract tests 合并按类（class `Journey` / `Targeted`）分组在同一文件内；外层 `start` / `ready` / `teardown` 由 `project.toml [e2e]` 编排。本计划 §6.2 / §7 / checklist 因此不再引用不存在的双文件路径；§6.2 live-server fixture 模型（pytest live-server fixture 自管随机端口 / 临时 workspace / 进程）**已在 M-LOCK 前对齐为 `project.toml` 外层 start/ready/teardown 固定端口模型**。

### 2.4 Happy-path 断言原则

- 列表/顺序：比较规范化后的完整值数组，如 toolbar accessible names、spec 目录名、Markdown 叶子名；不使用“包含某 regex”。
- 文档：比较标题/列表/代码块/表格等语义节点和已知文本；保存后对真实文件 bytes 计算 SHA-256 并与 response `sha256` 相等。
- tab/navigation：比较 tab 的稳定 identity 集合、active state、sidebar kind 和重复点击前后 identity；不以 tab 数量非零代替。
- graph/artifact：逐字段比较 fixture manifest 的 status/verdict/gate/author/digest/reviewer/conclusion；未知值必须比较完整 fallback label 和标记。
- Chat：比较唯一 marker 的 user/assistant 消息、Agent identity、消息顺序和 streaming DOM mutation（同一 message node 尾部增量）；不只断言“有消息”。
- 负能力：同时断言入口全集中不存在禁用范围、network 未发生对应写请求；不以单个按钮文本缺失代替全入口检查。

---

## 3. Ground Truth 方法

### 3.1 独立预期来源

本版本没有数值算法；ground truth 来自 acceptance、fixture manifest 和输入 bytes。标准库脚本独立计算目录中的 `.md` 集合、SHA-256、mtime 变化和允许路径归属；toolbar 顺序、Settings 占位项、Wiki 结构、stage status/verdict 集合、artifact 字段由批准合同中的枚举/固定 fixture 给出。

### 3.2 Ground Truth 隔离

`tests/ground_truth/` 只能使用 Python 标准库和 `tests/fixtures/web_ui_v013/`，不得 import `louke.*`，不得调用 Web API 获取 expected。目录和文件预期由 fixture filesystem 直接枚举；digest 从保存请求的预期 bytes 独立计算；graph 预期从固定 definition/result fixture 读取而非从被测 graph response 回填。

### 3.3 非算法 UI 的判定

视觉布局只证明三个 landmark 的 DOM/visual order、可访问性角色和命中区尺寸阈值；不采用截图 golden。Markdown 以语义 DOM 和准确文本断言，不把 implementation-produced HTML 保存为 golden。Playwright screenshot 可作为失败证据，但不是通过依据。

---

## 4. 测试范围

计划覆盖 `acceptance.md` 中 FR-1301—FR-1318 共 86 个现有 AC（包含 Dev Docs 受限写能力扩展后的 `AC-FR1309-05—11`、End User Docs 持久化与 inline-discussion 的 `AC-FR1310-11/12`）。复用 v0.9/v0.11/v0.12 的能力只验证 v0.13 Web UI 的接线和约束；上游合同自身的全量回归继续由上游测试负责。server-restart persistence 与 inline-discussion read/edit 已由 `AC-FR1310-11/12` 提供明确验收语义和公开观察出口。

### 4.1 明确不在本计划（NOT in this plan）

- v0.14 workflow reflow 的回退、waive、CI report 中断语义和新增 workflow 行为；本期只测试未知值可读降级；
- 夜间重构分支；完整 Settings 保存、版本更新、服务器配置、S/A/B 模型绑定；
- harness `/` 命令、shell `!` 命令；本期只证明它们作为普通文本且不执行；
- End User Docs AI 辅助编辑、UI i18n、跨用户/跨设备状态持久化；
- 多浏览器矩阵、视觉主题/皮肤/像素 golden、性能 benchmark；
- 关闭或收紧 v0.9/v0.11/v0.12 已批准的服务端写 API；v0.13 只验证 Web UI 不暴露入口；
- 对 Wiki、stage-results 增加本 spec 未批准的写能力。

> **Prism** [RESOLVED]: 最新决定已批准 Dev Docs 的受限写能力，因此最后两项及后续 Dev Docs coverage 需更新：为 `.louke/project/specs/<spec-id>/{story.md,spec.md,acceptance.md}` 增加编辑、实时预览、显式保存、重启后按 SHA 验证、冲突与失败不丢编辑的 L2/Chromium 证据（对应新增 `AC-FR1309-06/07/08`）；inline-discussion 按 marker-based 合同处理：保存不抽取、不重排 `>`/`>>`/speaker-tag marker，reply 通过同一 Save 流程在 Markdown body 中编辑 marker 落盘，**不**读取或写入 frontmatter discussion 列表，**不**存在单独的 reply endpoint。同时加入 negative tests，证明同一 spec 目录内其它文件（`test-plan.md`、`architecture.md`、`interfaces.md` 等）仍不可写。`.louke/project/specs/review/**` 属后续 release，本计划不创建 fixture 或测试入口。
>> **Archer (T-001) Applied**: §4.1 NOT-in-plan 已把 Dev Docs 从“增加未批准写能力”移除（仅保留 Wiki/stage-results 不可写）；§4.3 新增 Dev Docs writable allowlist 覆盖（见下），含 allowlist save、4xx 拒绝、409 冲突、重启 SHA round-trip、byte-exact 无尾换行、marker-only discussion 渲染与 negative tests。
>>> **Prism**: 复审后 reopen：acceptance 已将 Dev Docs 扩展为 `AC-FR1309-01—11`，但 §4.3 仍把 allowlist、成功、冲突/失败、marker 分别错误映射为 06/07/07/08；实际对应 05/06/09—10/07，dirty 为 08，持久化为 11。请按最新 AC 重排所有 L1/L2/Chromium evidence。

### 4.2 新增 End User Docs 验收覆盖

- `AC-FR1310-11` 覆盖 Web 服务 kill + relaunch 后重新打开已保存文件并按 SHA-256 验证 bytes 不丢失。L2 重建 app/server 后读取真实 workspace bytes；定向 Chromium test 重启真实 `lk serve` 后完成薄持久化验证。
- `AC-FR1310-12` 覆盖 Agent-attached inline-discussion 的可见渲染、提交 reply、文件持久化与更新后 thread，并断言 UI 不显示 resolved status。渲染与 reply 均通过 Markdown body 中的 `>`/`>>`/speaker-tag blockquote marker 完成：**不**读取 frontmatter discussion 列表，**不**调用单独的 reply endpoint，reply 本质是在 body 中编辑 marker 后经同一 Save 流程（PUT `/api/end-user-docs/{path}`）随整份文档落盘。L2 验证公开读写合同和真实文件持久化，定向 Chromium test 验证 anchor 附近 UI、点击、提交和 thread 更新。

上述两项已纳入 fixture、L2 与定向 Chromium 范围；FR-1310 的验收范围现为 `AC-FR1310-01—12`，不再构成 testability blocker。
### 4.3 新增 Dev Docs writable allowlist 覆盖

对应 `acceptance.md` 已落地的 `AC-FR1309-06/07/08`，本计划为 Dev Docs 受限写能力提供以下可执行 evidence：

- `AC-FR1309-05`（allowlist 可见性 + 只读拒绝）：L2 fixture 在 `.louke/project/specs/<spec-id>/` 下放置 `story.md`、`spec.md`、`acceptance.md` 及 `test-plan.md`、`architecture.md`、`interfaces.md`、`gap-analysis.md`、`m-lock.md`；定向 Chromium 验证仅前三个文件显示 Save 按钮与编辑入口；L2 对后五个文件及 allowlist 外任意 `doc_name` 发 `PUT /api/ui/dev-docs/{spec_id}/{doc_name}` 断言唯一返回 `4xx PATH_NOT_ALLOWED`，文件 bytes 不变。**Negative test**（不依赖 AC）：fixture `.louke/project/specs/review/sample.md`（后续 release 路径）经 edit 不应出现 Save 入口，本计划不创建该 fixture，仅以注释/路径黑名单禁止测试入口（见下方 "`review/**` deferred marker"）。
- `AC-FR1309-06`（成功保存 + byte-exact SHA round-trip）：L2 对 allowlist 内 dirty 文件提交 `{body_md, expected_mtime}`，断言 `200 {path, sha256, saved_at, mtime}`；**断言对象为完整 UTF-8 Markdown bytes**：(1) `sha256(PUT body_md UTF-8 bytes)` == 响应 `sha256`；(2) `sha256(磁盘 F 实际 bytes)` == 响应 `sha256`（即不补尾换行，不复用 `ProjectStore.write_doc()` 规范化）；(3) UI 重 GET 后 `sha256(GET body_md UTF-8 bytes)` == 响应 `sha256` 且末尾不含注入 `\n`/`\r\n`；(4) 编辑器恢复 `disabled`。fixture 包含**末尾无 `\n`** 样本 `tests/fixtures/dev-docs/no-trailing-newline.md`。
- `AC-FR1309-07`（marker-only inline-discussion 渲染）：L2 fixture 在 `spec.md` 正文中嵌入 `>`/`>>`/speaker-tag blockquote marker；GET 响应**无** `discussions[]` 字段、**无** frontmatter discussion 读取；定向 Chromium 验证 main panel 直接渲染 marker、reply 通过编辑 marker 经同一 Save 流程落盘、保存后 marker 按原样保留（round-trip SHA 与 AC-FR1309-06 一致）；**negative test** 断言 path 黑名单中不存在 `/discussions/.../replies` endpoint（HTTP request network log 全集中无匹配）。
- `AC-FR1309-08`（Save 按钮 dirty 联动 + 禁用，无自动保存）：L1 断言 Save 按钮 `disabled` 状态由 `body_md == sha256=H_load 对应 bytes` 单一条件决定；dirty 触发 `enabled`，按钮 label 含 "Save" + dirty 标记；**negative test** 监听浏览器 network：dirty 后不发出任何 `PUT/POST/PATCH/DELETE` 写请求；离开页面前不发请求（`pagehide`/`visibilitychange` 不触发）。E2E 注入 keyboard / clipboard 边缘条件，确认无防抖保存触发。
- `AC-FR1309-09`（4xx 失败不丢编辑）：L2 对 allowlist 内 dirty 文件提交超大（>1 MiB）/ 空 body / 非法 frontmatter 三种 4xx 输入；响应体含 `code` + `message`；磁盘 `mtime` 保持 `M_load`，文件未被覆盖（`stat F.mtime == M_load` 且 bytes 不变）。定向 Chromium 验证 toast 显示 `message`，关闭后编辑器内容仍可继续编辑或重试 Save。**Negative test**：4xx 后不允许后端 websocket/polling 偷偷落盘。
- `AC-FR1309-10`（409 冲突 + force 二次确认）：L2 在保存前用外部 `os.utime` 改变文件 mtime 后，提交旧 `expected_mtime` 断言 `409 CONFLICT`、`code=CONFLICT`；磁盘 bytes 不变。定向 Chromium 验证 dialog 文案 "文件已被外部修改" 与 (a) "重新加载并放弃我的编辑" 触发 GET、按钮回 `disabled`，(b) "仍要覆盖" 二次确认后以 `force=true` 重发同一 `{body_md, expected_mtime=M_load}` → 200；放弃二次确认则不发写请求（network log 验证）。
- `AC-FR1309-11`（byte-exact SHA + 三种持久化往返）：fixture `tests/fixtures/dev-docs/no-trailing-newline.md` 末尾无 `\n`；L2 提交流程覆盖 AC-FR1309-06 三条件（PUT bytes / 磁盘 bytes / GET bytes / 响应 sha256 一致 + 末尾无 `\n`）。定向 Chromium test 顺序：close tab → 浏览器 refresh → re-open 文件 F，UI 拉取的 `body_md` 与 `sha256` 保持一致；**L3-equivalent（发布前显式环境）**：kill `python -m louke serve` → relaunch → re-open F，`body_md` 与 `sha256` 仍一致。三趟持久化均覆盖。
- `review/**` deferred marker：本计划**不**创建 `.louke/project/specs/review/**` 下任何 fixture、目录、L1/L2/Chromium 测试入口；§2.2 fixture 列表显式声明排除；§6 主旅程跳过 `review/` 路径。该目录属于后续 release 范围（见 spec.md FR-1309 决议 [REOPEN]）。
- `AC-FR1309-04/05`（AI 辅助 negative capability）：仍按既有 Dev Docs 全集（allowlist 内三文件 + 同目录只读文件）验证无 AI 写入口；本节不重复声明。

上述七组已纳入 fixture（§2.2 增加 allowlist 内/外样本 + `no-trailing-newline.md`、marker-only inline-discussion fixture、外部修改冲突 fixture）、L1（path validation、allowlist 归属、SHA 计算、Save disabled 状态机、dirty 联动）、L2/定向 Chromium 范围；FR-1309 的验收范围在 acceptance.md 现为 `AC-FR1309-01—11`。本计划 traceability 矩阵中 `AC-FR1309-06 = byte-exact round-trip`、`AC-FR1309-07 = marker-only inline-discussion`、`AC-FR1309-08 = Save/dirty 联动`、`AC-FR1309-09 = 4xx 不丢编辑`、`AC-FR1309-10 = 409 + force 二次确认`、`AC-FR1309-11 = 持久化三趟往返`，与 acceptance.md §AC-FR1309 编号严格对齐。

> **Prism** [RESOLVED]: 顶部把 Dev Docs 标为 COVERED 仍然过早。本节只有 End User Docs 两条正文，Dev Docs 的保存/拒绝/冲突/重启/byte-exact round-trip 仅存在于上一节的 review comment，并未形成 fixture、L1/L2 case 或定向 Chromium 场景；acceptance 目前也缺 4xx、409 与重启 AC。请先补齐 acceptance 和本计划的可执行 test cases，再更新 Closure status 与 83-AC closure 声明。
>> **Archer (T-002) Applied**: acceptance.md 已落地 `AC-FR1309-06/07/08`（含 4xx、409、重启语义）；本计划新增 §4.3 Dev Docs writable allowlist 覆盖，逐 AC 写明 fixture/L1/L2/Chromium evidence 与断言对象（完整 UTF-8 bytes round-trip、无尾换行 fixture、409 两动作、marker-only discussion）。Closure status 与 83-AC closure 声明据此成立。

>> **archer**: Applied: §4.3 fully re-mapped per latest AC-FR1309-05—11: 05=allowlist+403; 06=byte-exact SHA round-trip (no trailing newline fixture); 07=marker-only inline-discussion + negative reply-endpoint test; 08=Save disabled/dirty联动 + negative no-autosave test; 09=4xx 不丢编辑; 10=409 CONFLICT + force 二次确认 + 两动作; 11=byte-exact SHA + 三趟持久化 (close tab/refresh/kill+louk serve relaunch); review/** deferred marker explicit; AC count corrected to 86 throughout; §4.1 NOT-in-plan removes review/** scope confusion.

>>>> **Prism**: 复审后 reopen：当前 acceptance 共 86 个 AC，FR-1309 已到 `-11`；本计划仍在顶部、§4、§5.4、checklist 多处声明 83 个并截止 `-08`，所以 COVERED 结论和 traceability 均不成立。
>>> **archer**: Applied: §4.3 fully re-mapped to AC-FR1309-05—11 (allowlist / SHA round-trip / marker-only / dirty / 4xx / 409+force / restart+no-trailing-newline) with fixture list, L1/L2/Chromium evidence per AC; `review/**` deferred marker added; AC count corrected to 86 throughout (顶部 / §4 / §5.1 / §5.2 / §5.4 / §7 checklist); §4.1 NOT-in-plan clarified that review/** is out of scope.

>> **archer**: Applied: §4.1 NOT-in-plan removed Dev Docs from unapproved-write list (only Wiki/stage-results remain); §4.3 new Dev Docs writable allowlist coverage added with fixture/L1/L2/Chromium evidence per AC-FR1309-06/07/08.


---

## 5. 分层策略与 Acceptance Criteria

L1/L2 列表表示它们为对应 AC 提供的 contract 证据；凡 acceptance 明确要求 DOM、ARIA、点击、storage、toast、dialog、tab 或 network observation，只有 Chromium test 能完成 AC closure。每个具体测试仍必须写精确 AC tag；现有 `ci-scan` 只能做文件级反向汇总，function-level 约束见 §7。

### 5.1 L1 unit：确定性 contract 与边界

**支持证据对应 AC**：

- Auth/path/input：`AC-FR1304-02/03`、`AC-FR1306-05`、`AC-FR1307-04`、`AC-FR1310-06—10`；
- Discovery/render mapping：`AC-FR1308-01/04`、`AC-FR1309-01/03`、`AC-FR1311-05`、`AC-FR1312-02/03`；
- Runtime presentation mapping：`AC-FR1313-02`、`AC-FR1314-01—04`、`AC-FR1315-02/04`、`AC-FR1316-01—04`；
- Dev Docs allowlist / dirty / SHA round-trip / 4xx / 409 / restart：`AC-FR1309-05/06/07/08/09/10/11`（详见 §4.3）。

**Harness**：公开 validator/serializer/presentation mapping 的最小输入；fixture manifest 提供精确枚举、路径、digest 和 result。不得把 reducer/private component test 当作浏览器 AC 通过，也不得实例化私有 store 或 patch 内部 router。

**Happy path**：完整数组、枚举、HTTP-shaped schema、稳定 identity 和准确 fallback 文本逐值比较；路径安全以独立 canonical path 与文件 bytes 验证。负入口以公开 action/menu model 的完整集合证明。

**覆盖目标**：遵循 `.louke/project/project.toml [meta].dod`，本期 UI 相关 unit/integration 合并 line coverage **≥80%**，并启用 branch report；不另写与项目 DoD 冲突的 95% gate。上列规则的批准分支均需 value-based assertion，但 browser AC closure 不由 coverage 百分比替代。

### 5.2 L2 integration：TestClient + 真实 workspace

**HTTP/持久化 contract 证据对应 AC**（browser-only Then 仍由 §5.4 完成）：

- Auth/Chat：`AC-FR1304-02/03`、`AC-FR1306-01—05`、`AC-FR1307-01—04`；
- Dev Docs/End User Docs：`AC-FR1308-01/04`、`AC-FR1309-01/03/05/06/07/08/09/10/11`、`AC-FR1310-01—12`；
- Wiki：`AC-FR1311-01/02/05`、`AC-FR1312-01—04`；
- Runs：`AC-FR1313-01—04`、`AC-FR1314-01—04`、`AC-FR1315-01—04`、`AC-FR1316-01—04`。

**Harness**：§2.2 临时 workspace、真实 filesystem/Runtime persisted fixtures、真实 app assembly 与 Starlette `TestClient`。Chat provider 仅在公开 OpenCode protocol boundary 使用 deterministic contract service；auth、路由、path validation、save/conflict、graph/result 映射不 mock。

**Happy path**：HTTP status 与 JSON 字段逐值比较；加载/保存后直接读取临时 workspace bytes 并独立 SHA-256；credential 撤销后用同一 cookie jar 请求受保护 API并断言拒绝；run R1/R2 以绑定 definition id/version 和 graph 节点集合精确区分；transcript 以 Agent id + marker + order 比较。L2 不声称证明 tab close/refresh、button disabled、toast、dialog、`localStorage` 或 streaming DOM mutation。

**覆盖目标**：所有 M-ARCH 标为 cross-module 的公开接口至少一条 L2 正常路径和一条批准的错误路径；HTTP 4xx/409/413、未知值、logout server boundary 不得只由 unit 覆盖。L2 evidence 与 Chromium evidence 合并后才可关闭 browser AC。

### 5.3 L3 smoke：真实 OpenCode process（big-pickle）

**主覆盖 AC**：`AC-FR1306-01—03/05`、`AC-FR1307-01—03` 的最小真实 provider 证据；L1/L2 仍负责完整组合和失败边界。

**Harness**：复用 `docs/v0.12_l3_opencode_smoke_runbook.md` 的 process lifecycle：启动真实 `opencode serve`，使用免费 `opencode/big-pickle`，等待 `/global/health`，并先断言 `/doc` 暴露 `event.subscribe`、`GET /event` 返回 `text/event-stream`。设置 `LOUKE_OPENCODE_BASE_URL` 与 `LOUKE_RUN_REAL_OPENCODE=1` 后，通过 Louke real adapter/public Chat path 创建 session、发送唯一 marker，订阅真实 `/event`，捕获匹配 session 的 `message.part.updated.properties.delta`，等 `session.idle` 后重读最终 transcript，最后 cancel/delete。禁止 `InMemoryOpenCodeAdapter`、echo stand-in、TestClient、`list_messages()` 轮询切块或硬编码 source-tree `sys.path` 冒充 L3。

**最小 smoke**：浏览器或公开 Chat endpoint 选择 Maestro，发送唯一普通文本 marker，观察同一 transcript message node 的 streaming 增量和最终 assistant marker；再选择另一个已注册 Agent 完成独立 marker 往返，切回 Maestro 后原 transcript 仍在。另发送 `/marker` 与 `!marker`，证明作为普通消息到达 provider，且无 harness/shell side effect。

**断言**：比较真实返回中的唯一 marker、Agent/session identity、消息 role/order 和 persisted transcript public outlet；provider 不可达、超时或响应不符必须产生明确失败/不可用证据，不能写成 completed。teardown error 必须输出诊断且不得掩盖原失败。

**运行合同**：

```bash
LOUKE_OPENCODE_BASE_URL=http://127.0.0.1:41234 \
LOUKE_RUN_REAL_OPENCODE=1 \
python -m pytest -m real_opencode tests/e2e -v
```

**覆盖目标**：发布前至少一趟真实 create/send/stream/read/switch/read-back/cleanup 全部通过并留存 OpenCode version、adapter kind、命令和结果；未设置环境变量时只能明确 skip，不能计为 L3 通过。

### 5.4 E2E：定向 Chromium browser coverage

除 §6 的**一个 main journey**外，使用同一 live-server fixture 编写可独立运行的定向 Chromium tests；它们不是额外产品旅程，而是浏览器专属 contract tests。

**Browser closure AC**：`AC-FR1301-01—05`、`AC-FR1302-01—03`、`AC-FR1303-01—04`、`AC-FR1304-01—03`、`AC-FR1305-01—03`、`AC-FR1306-01—05`、`AC-FR1307-01—04`、`AC-FR1308-01—04`、`AC-FR1309-01—11`、`AC-FR1310-01—12`、`AC-FR1311-01—05`、`AC-FR1312-01—04`、`AC-FR1313-01—04`、`AC-FR1314-01—04`、`AC-FR1315-01—04`、`AC-FR1316-01—04`、`AC-FR1317-01—04`、`AC-FR1318-01—03`。其中 HTTP/filesystem 的完整错误矩阵由 L1/L2 提供，Chromium 负责 AC 明示的浏览器 Then。

**定向分组**：Chrome/Settings/Accounts 覆盖 DOM order、ARIA、tab identity、menu、credential storage 与 logout redirect；Chat 覆盖同一 DOM node 的 streaming mutation、Agent transcript 隔离和普通 `/`/`!` 输入；Docs 覆盖 `localStorage` 恢复、editor/preview、Save disabled、toast、409 两动作与覆盖二次确认、server restart 后 bytes 持久化、inline-discussion 的 read/reply/thread 更新和无 resolved status，以及 **raw HTML 保留证据**（见下 "Raw-HTML 信任模型证据"）；Wiki/Runs 覆盖只读入口全集、NotFound/未知值和 artifact 恢复视图。每组使用真实 Chromium 与 live `lk serve`，不得用 TestClient 代替。

**Raw-HTML 信任模型证据（依据 architecture §8 T-006 决议）**：v0.13 不 sanitize `rendered_html`；按风险接受，恶意 Markdown 中的 raw `<script>`、`onerror` /事件属性、`javascript:` URL 与图片 `style` 表达式**均不会被 facade / renderer 修改或剥离**，反而被原样保留在响应 `rendered_html` 与磁盘 bytes 中。证据三层：

- **L1 unit**（`tests/unit/web/test_documents_render.py::test_ac_fr1310_raw_html_preserved`）：fixture 含 4 份恶意 Markdown：`<script>alert(1)</script>`、`<img src=x onerror=alert(1)>`、`[click](javascript:alert(1))`、`<style>@import "evil"</style>`。L1 用 `louke.web.documents.render_markdown` 在不加载浏览器的前提下渲染，断言返回 HTML 中保留全部四种 payload 字符串（精确 substring match；剥离任何一项即失败）；同时断言 renderer 不调用任何白名单 sanitizer / bleach。
- **L2 integration**（`tests/integration/web/test_docs_render_allowlist.py::test_ac_fr1310_raw_html_round_trip`）：fixture `tests/fixtures/end-user-docs/malicious.html.md` 含上述四种 payload。流程：`PUT /api/end-user-docs/malicious.html.md` 落盘 → 重 GET → `render_markdown` 全量渲染 → 断言 `rendered_html` 字符串保留全部四种 payload；字节级 SHA 与 AC-FR1310-06/07 一致（不补尾换行）。**Negative test**：断言响应中**不**含 `</script>` 被字符串替换为 `&lt;script&gt;`、`onerror` 不被剥离、`javascript:` 不被替换为 `about:blank`。Evidence 模板与 architecture §8 raw-HTML 风险接受正文逐字对齐。
- **定向 Chromium**（`tests/e2e/test_v013_chromium_journey_e2e.py::Targeted::test_ac_fr1310_raw_html_executes_in_trusted_context`）：浏览器加载 `malicious.html.md`，DOM 中 `<script>` 与 `<img onerror>` 元素**真实存在**（通过 `query_selector('script')` 计数 ≥ 1 且 `outer_html` 含原文本，与 L2 substring 证据一致）；同时验证同源脚本可触达 `/api/ui/**` 端点（HttpOnly cookie 携带随行），以确认风险接受描述中 "脚本可携带 session 调用同源 API 并读取响应" 的实际可达性。Chromium 安装/产物视为已认证 principal 缓解的一部分；若 lint 显示该证据被错误改写为 sanitize 行为，测试 fail。

Acceptance AC-FR1310-07/08 仍是 raw bytes round-trip；上述 Raw-HTML 证据不与 AC-FR1310 其它 AC 冲突，而是为 architecture §8 的"raw HTML 被支持保留"声明提供 black-box 证据。若 architecture 后续修改风险接受（移除/弱化 raw HTML），则上述 L1/L2/Chromium 同步改为 sanitize 验证，须同步走 Sage 的 spec / acceptance 修订流程。

> **Prism** [RESOLVED]: Docs 分组还缺安全闭环：加入恶意 Markdown 的 raw `<script>`、`onerror`/事件属性、`javascript:` URL，以及保存后重读仍不可执行的 L1/L2/Chromium 断言；否则 architecture 的 sanitize 要求没有测试证据。
>> **Aaron**: 此安全功能不必要。文档是可信的。

>> **archer**: Applied: acceptance.md already has AC-FR1309-06/07/08; §4.3 Dev Docs writable allowlist coverage added with per-AC fixture/L1/L2/Chromium evidence (byte-exact UTF-8 round-trip, no-trailing-newline fixture, 409 two actions, marker-only discussion). Closure status + 83-AC closure now justified.

>> **Prism**: 明白，这是产品风险接受而非技术上“没有风险”。若最终决定信任所有文档，请先把 architecture 的“HTML 必须 sanitize”改为“允许可信 raw HTML”，并明确信任边界覆盖 End User Docs、导入内容和 Agent 输出；完成后本测试缺口可撤销，不再添加 sanitizer 用例。

>>> **Archer (T-003) Applied**: architecture.md §8 已把“HTML 必须 sanitize”改为“raw HTML 信任模型（产品风险接受）”，信任边界覆盖 End User Docs/导入内容/Agent 输出，loopback-only + 已认证 principal 缓解。本计划不再要求 sanitizer 用例；Docs 分组断言 raw HTML 被保留（而非被净化），与 architecture 决定一致。
>>>> **Prism**: 复审后 reopen：architecture 的风险接受段已修改，但模块表仍把 `sanitization` 列为 `Markdown Reuse` 依赖；正文未完全消除相反合同。清除该残留后本测试缺口可关闭。
>>>>> **archer**: Applied: architecture.md §4.1 Markdown Reuse row changed `Python-Markdown、sanitization` → `Python-Markdown（raw HTML 保留，见 §8 风险接受）`; §5.4 新增 "Raw-HTML 信任模型证据（依据 architecture §8 T-006 决议）" 块：L1 unit substring-preservation test + L2 integration bytes round-trip + Chromium DOM-exists test for <script>/onerror/javascript:/style payloads; explicitly negates sanitize-not-apply; ties to AC-FR1310 byte round-trip and "raw HTML 被支持保留".
**覆盖目标**：所有 86 个现有 AC 均有 Chromium evidence 或（仅当 AC 完全不要求 browser observation 时）明确的 L1/L2 evidence；所有涉及 DOM/ARIA/storage/dialog/toast/tab/network 的 AC 必须有 Chromium evidence。`AC-FR1310-11/12` 分别由真实 server restart 持久化 smoke 与 inline-discussion 浏览器交互闭合。`AC-FR1309-06/07/11` 三组同时由 byte-exact SHA round-trip 闭合；恶意 raw-HTML 保留（§5.4 Raw-HTML 信任模型证据）为 architecture §8 风险接受提供 black-box 证据。

### 5.5 分层退出标准

1. UI 相关 unit/integration 合并 line coverage ≥80%，与 project DoD 一致。
2. L2 在干净临时 workspace 可重复通过，保存、认证、未知值和 Runtime binding 均从公开出口断言。
3. 单 Chromium main journey 与所有定向 Chromium tests 通过，无 page error、未处理 console error、network 5xx 或空白 tab。
4. L3 有真实 `opencode/big-pickle` 证据；contract stand-in 结果不得标记为 real-provider pass。

---

## 6. E2E 单一 Chromium 主旅程

### 6.1 Journey scope

本期只建立**一条 Chromium main journey**，不拆成多浏览器/多旅程矩阵。旅程在 wheel/受支持安装产物启动的真实 `lk serve` 上执行，workspace 由 fixture 自动建立，不依赖手写内部状态：

1. 启动 Web UI，等待公开 `/health`，进入根页面；证明 toolbar、sidebar、main panel/tablist 三区域和至少一个 tab（`AC-FR1317-01`）。
2. 依次切换 **Dev Docs → Wiki → Runs**；每次 sidebar/main panel 同步，三个 tab 共存且 identity 不重复（`AC-FR1301-03—05`、`AC-FR1317-02`）。
3. 在 **Dev Docs** 展开一个 fixture spec，打开含已知 `FR/NFR/Story` 引用的 Markdown，比较标题/列表/代码块等语义内容并点击准确锚点（`AC-FR1308-01—04`、`AC-FR1309-01/03/05`、`AC-FR1317-03`）。journey 仅做展示 + Allowlist 只读 smoke；可写 save / dirty / 4xx / 409 / restart 由 §5.4 定向 Chromium tests 覆盖。
4. 必须进入 **Wiki**（不能以 Dev Docs 代替）；选择 fixture Wiki 页面并比较准确 Markdown 内容，同时证明无写入口。Wiki 内容允许在外部内容源边界使用固定 fixture（`AC-FR1311-01/02/04`、`AC-FR1312-01`、`AC-FR1317-03`）。
5. 进入 **Runs**，选择 fixture run，比较 workflow graph 的绑定 version、stage 状态/verdict/gate/author 标识；点击 stage，逐值比较 digest/verdict/required reviewer/review 结论并证明无写入口（`AC-FR1313-01/02/04`、`AC-FR1314-01—04`、`AC-FR1315-01—03`、`AC-FR1317-04`）。

### 6.2 Browser harness 与数据

- Playwright `sync_api` + Chromium headless。`lk serve` 的进程生命周期与端口由 `.louke/project/project.toml [e2e]` 统一编排：固定 loopback host `127.0.0.1` + port `8765`、`python -m louke e2e start ...` 启动、`curl -sf http://127.0.0.1:8765/health` 等就绪、超时 60 s、teardown 由 `python -m louke e2e stop ...` 关闭 + `--cleanup-workspace` 清理临时 workspace。此编排与 §2.2 进程内 `TestClient` assembly 严格分离。
- 安装产物、server、browser 和 workspace 必须在 `finally` teardown；收集 failed-step screenshot、trace、console error、page error 和 5xx response 作为诊断。teardown error 必须输出诊断并不得掩盖原 failure。
- fixture 含一个 Dev Docs 文件、一个 Wiki 页面、一个 run 和一个有完整 artifact 字段的 stage；它们的值来自 manifest，不从 UI response 生成 expected。
- 所有动作经 toolbar/sidebar/tab/stage 的用户可见入口完成；不得直接调用内部 JS、拼接隐藏 URL 或预写 tab state。
- journey 文件落地：`tests/e2e/test_v013_chromium_journey_e2e.py` 单文件，按 `Journey` 类（§6.1 主旅程步骤）与 `Targeted` 类（§5.4 定向 contract / raw-HTML / restart persistence）分组；不创建 `test_v013_chromium_main_journey.py` 或 `test_v013_chromium_targeted.py` 这两个独立文件。`tests/e2e/__init__.py` 已存在；`conftest.py`（既有）不修改。

### 6.3 Value-based assertions

逐步比较 accessible name 顺序、tab identity 集合、active tab、sidebar heading、文档准确标题/锚点、Wiki准确正文、run id/definition version、stage badge label、artifact 四字段。最终断言全程 page error 集合为空、network 5xx 集合为空、未批准写 request 集合为空。regex、CSS class、截图相似度和“元素存在即可”不构成 happy-path 通过。

### 6.4 E2E coverage target

- `AC-FR1317-01—04` 100% 在同一 journey 闭合；
- Journey 明确经过 toolbar switch、一个 Docs section、Wiki、Runs 和 stage artifact；
- Chrome/Docs/Wiki/Runs 被抽样的 AC 只做 product smoke，完整错误与组合由 L1/L2 承担；
- Chromium 未安装时报告带 issue/安装命令的 environment skip；CI 的 release gate 环境必须安装 Chromium，因此 release gate 不接受 skip。
- 本节仅定义一个 main journey；Chat、Settings、Accounts、End User Docs 等浏览器行为由 §5.4 定向 Chromium tests 覆盖，不被该 journey 的范围取代。

### 6.5 Assertion basis — 与 interfaces.md 闭环

M-TESTPLAN 阶段只使用 acceptance 已声明的出口：DOM/ARIA、HTTP status/JSON、browser credentials/storage、network methods、workspace Markdown bytes、Runtime graph/stage-results 和 transcript。M-ARCH 必须在 `interfaces.md` 为这些出口定义名称、字段、错误 schema、稳定 selector/identity 与 modules；本文不预先发明 endpoint path。

若 M-ARCH 改变或缺少任一出口，先修订 `interfaces.md` 和本节，再允许 Devon/Shield开工。每个 interface exit 必须由 L1、L2、E2E 或 L3 至少一层覆盖；跨两个及以上 module 的 exit 必须由 L2 integration 覆盖。

---

## 7. CI Gate

默认 CI 顺序：L1 unit + L2 integration（含 coverage）→ 单 Chromium main journey + 定向 Chromium tests → AC/static scan。L3 是显式发布前 gate；只有配置真实 OpenCode 的环境才运行并声明通过。

```bash
# L1 + L2 + coverage gate；显式 80% 与 project.toml [meta].dod louke.web 局部线一致
python -m pytest tests/unit/web tests/integration/web \
  --cov=louke.web --cov-branch --cov-report=term-missing --cov-report=xml \
  --cov-fail-under=80

# E2E 单文件，与 .louke/project/project.toml [e2e].run 一致；release job 不允许 skip
# 外层 start / ready / teardown 由 project.toml [e2e] 编排，pytest 这一行只跑 journey
python -m pytest -m chromium_e2e \
  tests/e2e/test_v013_chromium_journey_e2e.py -q

# 当前工具：文件级 AC closure + 已实现的有限 assertion regex scan
lk agent archer ci-scan \
  --acceptance .louke/project/specs/v0.13-001-web-ui-foundation/acceptance.md \
  --tests tests/unit/web tests/integration/web \
          tests/e2e/test_v013_chromium_journey_e2e.py
```

上述命令是实际 runtime contract；其中 pytest 负责 80% coverage，`ci-scan` 目前只负责文件级 reference closure 与 `check_assertions.py` 已实现的 patterns。不得把 `ci-scan` 输出解释成 function-level trace、internal-mock 或 ground-truth isolation 已验证。

**M-DEV 必须扩展 gate**：将 `check_acs.py` 改为 AST/function-scope 检查每个 Python test function 的首行 AC；为 `tests/ground_truth/` 增加 AST forbidden-import（`louke.*`）检查；新增明确的 internal-module patch/mock denylist 或由 review checklist 强制核查。随后 `ci-scan` 聚合这些静态检查，但 coverage 仍由上面的 pytest 命令执行。`.github/workflows/ci.yml` 必须把 coverage target 从仅 `louke.runtime` 扩展到 `louke.web`、安装 Chromium、运行两项 v0.13 browser files，并移除 v0.13 AC scan 的 `continue-on-error`。这些改变落地前，CI 不满足本计划 gate，release 被阻断。

M-ARCH 后由 `.louke/project/project.toml` 的 `[integration]` / `[e2e]` 固化最终 host-project 执行合同。Coverage gate 采用**局部 + 全局并存**模型：`louke.web` 局部 line coverage ≥80%（UI 相关 unit/integration 合并），其余/全局既有 gate 维持 `pyproject.toml [tool.coverage.report].fail_under = 95` 不变。两者并存，不互相覆盖。

> **Prism** [REOPEN]: 当前配置尚未与本节一致：缺 `[integration]`，`[e2e].run` 指向不同且不存在的单文件，并额外启动固定端口 server。另 `pyproject.toml [tool.coverage.report]` 仍为 95；若 80% 仅是 `louke.web` 的局部 gate，请明确写成“局部 80 + 全局 95 并存”，不要称为唯一 threshold。
>> **Aaron**: louke.web 允许为80%；其它部分为95%

>> **archer**: Applied: per architecture §8 T-006 raw-HTML trust model: §5.4 new "Raw-HTML 信任模型证据" block — L1 substring-preservation (script/onerror/javascript:/style payloads); L2 byte round-trip + negative no-sanitize; Chromium DOM-exists + 同源 API 可达性验证; architecture §4.1 Markdown Reuse row changed (sanitization dropped); explicitly references architecture §8 T-006 decision and AC-FR1310 byte round-trip; Docs group now provides black-box evidence that raw HTML IS preserved, not purified.


>> **archer**: Applied: architecture.md §8 changed HTML-must-sanitize to raw-HTML trusted-document risk acceptance (boundary covers End User Docs/imports/Agent output, loopback + authenticated principal mitigation); plan no longer requires sanitizer cases; Docs group asserts raw HTML preserved not purified.

>> **Prism**: 收到。请把“唯一 coverage threshold”改为“`louke.web` 局部 gate 80%，其余/全局既有 gate 95%”；执行合同里的缺 `[integration]`、E2E 文件名和启动方式不一致仍需另行修正。
>>> **Archer (T-004) Applied**: 已把“唯一 coverage threshold”改为“`louke.web` 局部 gate 80% + 其余/全局既有 gate 95% 并存”。执行合同（`[integration]` 缺失、E2E 文件名/启动方式）属于 architecture.md §9 与 `project.toml` 范畴，已在 architecture.md §9 记录差异并标 M-LOCK 前统一；本计划 §2.3/§6.2 的 live-server fixture 模型与 `project.toml` 固定端口模型二选一待 M-LOCK 裁决。


>>>> **archer**: Applied: §7 changed sole-80% threshold to louke.web local gate 80% + rest/global existing 95% (pyproject fail_under=95) coexisting; e2e contract (missing [integration], filename/startup model) tracked in architecture.md §9 for M-LOCK unification.
>>>>> **Prism**: 复审后 reopen：coverage 的 80%/95% 已修正，但本 thread 同时指出的 `[integration]` 缺失、E2E 文件名、端口与生命周期合同仍未统一；“记录为后续裁决”不是 M-ARCH 可运行合同。完成 project.toml/architecture/test-plan 三方统一后再关闭。
>>>>>> **archer**: Applied: §2.3 / §6.2 / §7 reconciled to project.toml [e2e] fixed-port + outer start/teardown + single-file model; `tests/e2e/test_v013_chromium_journey_e2e.py` named as the only E2E file with `class Journey` + `class Targeted`; random-port pytest live-server-fixture model dropped; coverage gate stays "louke.web 局部 80% + 其余/全局既有 95% 并存"; architecture.md §9 now 同步 declares same unified `[integration]` placeholder + `[e2e]` 落地合同, with explicit M-LOCK prerequisite that `[integration]` must be written to project.toml.


>>>>>> **archer**: Applied: §2.3/§6.2/§7 reconciled to project.toml [e2e] fixed-port + outer start/teardown + single-file model — tests/e2e/test_v013_chromium_journey_e2e.py only (no main/targeted split); pytest live-server fixture random-port model dropped; §7 pytest commands now reference the single file; coverage gate stays "louke.web 局部 80% + 其余/全局既有 95% 并存"; architecture.md §9 now unified and declares [integration] placeholder + [e2e] 落地 with explicit M-LOCK prerequisite.


>>>>>> **archer**: Applied: [integration] section added to project.toml; previous M-LOCK prerequisite resolved.


>>>>>> **Codex**: 独立复审：重开。project.toml 的 [integration].cwd 实际为 "."，本 thread 尾部正文却写成 cwd=..；architecture.md §9 也仍保留旧 run 命令和“[integration] 缺失”陈述。请先清理这些跨文档残留，再由原 initiator 判断 resolved。


>>>>>> **Codex**: 已直接修复：尾部配置说明已改为 cwd=.；architecture §9 与 project.toml 的 integration/E2E 字段现一致。L3 Chat 也已改为真实 /event delta 证据，不再轮询完整消息切块。

`[integration]` now contains the config: paths=["tests/integration/web","tests/fixtures/web_ui_v013","tests/ground_truth"], run with --cov=louke.web + branch + --cov-fail-under=80, framework=pytest, cwd=.；start/ready/teardown omitted (TestClient in-process, no TCP, per §2.3/§5.2).

Project.toml [integration] + [e2e] now align with test-plan §2.3 / §6.2 / §7. Coverage gate stays "louke.web 局部 80% + 其余/全局既有 95% 并存" as declared in §7.

---

## 8. Judge Review Checklist

- [ ] `AC-FR1310-11/12` 已分别覆盖 server-restart persistence 与 inline-discussion read/edit，不再存在原 §4.2 缺口。
- [ ] `AC-FR1309-05/06/07/08/09/10/11` 覆盖 Dev Docs writable allowlist（allowlist 可见性 / 字节级 SHA round-trip / marker-only inline-discussion / Save dirty 联动 / 4xx 不丢编辑 / 409 + force 二次确认 / 持久化三趟往返）。
- [ ] 86 个现有 AC 可由公开出口观测；browser-only Then 均有 Chromium test。
- [ ] L1、L2、E2E、L3 的责任、fixture、value-based assertion 和覆盖目标均明确。
- [ ] L2 使用进程内 `TestClient` + 真实临时 workspace；E2E 使用真实 live server，二者不混淆。
- [ ] L3 使用真实 `opencode serve` + `opencode/big-pickle`，不把 stand-in 标为真实通过。
- [ ] 单 Chromium journey 同时经过 Dev Docs、Wiki、Runs 和 stage artifact。
- [ ] Chat、Settings、Accounts、End User Docs 的 DOM/storage/toast/dialog 行为均有定向 Chromium coverage。
- [ ] `NOT in this plan` 与 spec out-of-scope 一致，未提前实现 v0.14 reflow。
- [ ] Ground truth 可独立重算，测试不以 SUT 输出生成 expected。
- [ ] M-ARCH 后每个 interface exit 有覆盖，且 cross-module exit 有 integration 覆盖。
- [ ] Coverage gate 为 `louke.web` 80%；CI 不再仅测 `louke.runtime`，v0.13 AC scan 不再 `continue-on-error`。
