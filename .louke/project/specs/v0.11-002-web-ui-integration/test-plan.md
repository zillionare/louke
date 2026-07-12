# Louke Web IDE — Web UI 集成 — Test Plan

- **Spec ID**: `v0.11-002-web-ui-integration`
- **Created**: 2026-07-12
- **Related acceptance**: `.louke/project/specs/v0.11-002-web-ui-integration/acceptance.md`
- **Assertion basis**: `.louke/project/specs/v0.11-001-web-ide/interfaces.md`（已锁定，本期不修改）
- **Test framework**: `pytest` + `pytest-playwright`

## 1. 立场与边界

### 1.1 Black-box declaration

本计划只验证系统外部可观察行为：同一 Web server 的页面与公开 HTTP 出口、浏览器可访问文本/控件/URL/状态、API 响应、临时 workspace 中允许观察的持久化文件，以及 pytest/Playwright 退出结果。六个 sub-app 的 schema、状态和错误语义继续以 v0.11-001 `interfaces.md` 为唯一 API 契约；本期验证它们 mount 后可被 Web UI 真实消费，不重测或改写其业务逻辑。

测试不得直接依赖内部 class、私有函数、registry、路由表对象、JavaScript 内部变量或缓存。AC 所需状态应从页面、锁定 API、持久化文件或进程结果观察；缺少出口时应报告接口 gap，不得从测试侧窥探实现。

### 1.2 范围与非范围

- 范围：六个 sub-app mount、既有页面 JavaScript client、真实点击/填写/状态断言、Chromium 与 Firefox。
- 保留：v0.11-001 已交付的 30 个 API e2e，继续作为 sub-app 接口契约回归层，不复制、不弱化。
- 非范围：sub-app 内部业务重写、v0.11-001 锁定文档修改、FR-0101、WebKit、视觉像素回归、生产 OpenCode。

### 1.3 防作弊与追踪

1. 每个新增测试函数 docstring/comment 首行引用完整 `AC-FRXXXX-YY` 或 `AC-NFRXXXX-YY`。
2. CI 使用真实契约：

   ```bash
   lk agent archer ci-scan \
     --acceptance .louke/project/specs/v0.11-002-web-ui-integration/acceptance.md \
     --tests tests/
   ```

3. 禁止 `assert True`、吞异常、无 issue 的 skip、以实现输出生成 expected、为适配实现而弱化断言。
4. Devon 负责 unit/integration；Shield 独立负责 UI e2e；Prism/Judge 检查 AC 引用、fixture 隔离和双浏览器结果。

## 2. 测试设计与环境

### 2.1 两层 E2E

- **API e2e（既有 30 个）**：直接验证六个 sub-app 的 16 个 HTTP endpoint、SSE/错误和持久化契约。本期不修改这些场景；它们防止 mount/UI 改动破坏接口。
- **UI e2e（本期约 12 个）**：由 Playwright 连接真实主 app，通过页面导航、点击和表单填写触发 JavaScript client，再断言可见状态、URL、锁定 API 响应关联及 reload 后持久化结果。关键用户动作不得改成 `request` fixture 直调 API。

### 2.2 Fixture 与数据

- 每例使用独立临时 workspace，包含两个可区分 OpenCode 实例、多个 backlog 条目、确定性 Git change/diff、可写设计文档、只读源码及含三个 task 的文档。
- OpenCode 仅替换为 v0.11-001 契约兼容的独立 mock server；Louke 主 app、mount、JavaScript client 与页面均为真实被测对象。
- fixture 可通过公开 API 准备前置数据，但关键 When 步骤必须由 UI 完成；页面结果不得由测试注入 DOM。
- browser context、端口、workspace 和 mock 状态按测试隔离；数据离线、无 secrets、无执行顺序依赖。

### 2.3 Ground Truth

本期无算法 ground truth。expected 来自预置 fixture、mock server 的公开协议记录、保存前后的文件字节及锁定 API schema，不从页面或实现反算。若增加 reference 脚本，应置于 `tests/ground_truth/` 且不得 import `louke.*`。

## 3. Unit Test Plan

轻量单元测试聚焦新增接线逻辑，不重复 sub-app 业务规则：

- app assembly/mount 声明能将六个前缀交给对应 ASGI app，且不会遮蔽 `/`、`/wiki`、`/models`、`/docs/...`、`/health`；
- JavaScript client 对 2xx、结构化错误、网络失败的解析与用户反馈映射；
- 请求 URL、method、body 与选中 instance/backlog/file/task 标识的绑定；
- 切换实例时客户端展示模型隔离，单 task 更新不覆盖另外两个状态。

测试替换 `fetch`/外部 OpenCode 边界即可，不 mock mount 目标、主 app 路由分发或被测 client 规则。新增核心 Python/JavaScript 逻辑计入项目 ≥95% coverage 门。

## 4. Integration Test Plan

以公开 `create_app()` assembly point + Starlette `TestClient` 或真实 uvicorn 主 app 验证：

- `GET /health` 返回锁定的 ready schema；
- 六类代表端点均经主 app URL 可达：OpenCode、Intent、Wiki、Backlog、Files、Tasks；非主页面 404，响应符合 v0.11-001 schema；
- mount 不回归 home/wiki/models/docs 页面路由；API 错误原样到达 JavaScript client 可消费边界；
- backlog、文档和 task 经主 app 路由写入后，后续 GET/reload 对应出口可观察持久化值。

集成层不启动浏览器；mount 断言必须发送真实 HTTP 请求，不能只检查内部 `routes` 数组。命令行 smoke 可用 `curl -sf /health` 后逐一请求代表 endpoint。

## 5. FR 核心 E2E 路径

- **FR-0202（2）**：导航 home/wiki/models/docs 并断言 URL；从页面加载 fixture API 数据，并在可控 API 失败时断言错误而非成功/mock 内容。
- **FR-0203（2）**：创建并选择实例后填写/发送消息；双实例切换验证输出隔离，并覆盖不可用实例失败反馈。
- **FR-0204（2）**：填写 story、提交、选择并进入开发后列表移除；无选择点击时反馈且列表/流程不变。
- **FR-0205（2）**：切换 tree/changes 并点击 diff；编辑允许文档、保存/reload，同时验证只读文件拒写。
- **FR-0206（2）**：加载三个 checkbox 并核对初态；点击单项、reload 后只目标状态持久化。
- **NFR-0102（6）**：导航与 API 数据/错误、OpenCode、Backlog、Files tree/diff、Files edit/save、Tasks 各一条真 UI 流；同一逻辑分别在 Chromium 与 Firefox 执行。

场景可合并 AC，但不得为了减少数量省略失败分支或 reload 断言。

## 6. Host-project E2E

### 6.1 执行契约

复用 `.louke/project/project.toml [e2e]`，本阶段不修改：`cwd = "."`；资产根为 `tests/`、`tests/fixtures`；start 使用 `python -m louke e2e start ... --opencode mock`；ready 为 `curl -sf http://127.0.0.1:8765/health`；run 为 `python -m pytest -m e2e tests/e2e --browser chromium --browser firefox`；无论成功失败均执行正式 teardown。

框架固定为 `pytest` + `pytest-playwright`，同一场景通过 browser fixture/project 参数化 Chromium 与 Firefox。现有 API e2e 30 个场景保持原文件和职责，不在本节重复。

### 6.2 本期 UI E2E 文件与 12 个场景

| 文件 | UI 场景数 | 场景族 |
|---|---:|---|
| `tests/e2e/test_web_ui_routes.py` | 2 | 四页面导航；真实 API 数据与错误反馈 |
| `tests/e2e/test_web_ui_opencode.py` | 3 | 创建/发送；双实例隔离；不可用实例失败 |
| `tests/e2e/test_web_ui_backlog.py` | 2 | 创建/选择/进入开发；未选择阻止 |
| `tests/e2e/test_web_ui_files.py` | 3 | tree/changes/diff；编辑保存 reload；只读拒写 |
| `tests/e2e/test_web_ui_tasks.py` | 2 | 三项初态；单项切换与 reload |

文件名是 Shield 的资产分区契约；函数可按 AC 合理合并，最终追踪由 `ci-scan` 从代码反向确认。

### 6.3 自动化断言原则

- 用 role、accessible name、label、稳定 test-id 定位；不依赖 CSS class、DOM 层级或文案的装饰性空白。
- 禁止 `sleep`；网络动作使用 `page.expect_response`，异步 UI 使用 locator assertion/`page.wait_for_selector` 等条件等待。
- 每个关键动作同时断言用户可见结果；持久化 AC 再 reload/reopen，通过页面断言最终值。
- 失败保留 trace、screenshot、browser console 和 server log；artifact 不得泄露 workspace 外内容。

## 7. Anti-pattern 与风险

沿用 v0.11-001 §7：默认 CI 只使用 deterministic fixture 与契约 stand-in；不连接生产依赖，不 mock Louke 内部核心，不以 manual/nightly smoke 代替默认门。

本期额外禁止：

- 用固定 sleep 掩盖 race；应等待 selector、response 或明确页面状态；
- 依赖 CSS class/DOM 深度，导致样式调整破坏语义测试；
- patch 主 Web app、mount 或 JavaScript client 后声称完成 UI e2e；必须运行 real app；
- 关键 When 步骤直接调用 API，仅用 `goto`/HTTP 200 冒充真实点击；
- 复用同一 workspace/browser context 造成状态串扰。

**已知接口 gap（不在本阶段修复）**：锁定的 v0.11-001 `interfaces.md` 完整定义 API，但未契约化本期页面路由、控件 accessible name/test-id、可见成功/失败状态或 JavaScript client 行为。API/持久化断言有出口，UI 定位与反馈出口仅由本期 acceptance 描述；M-ARCH 若仍必须保持 interfaces 不变，Devon 与 Shield需以现有页面公开语义协同，存在选择器漂移风险。

## 8. AC Coverage Mapping 与退出门

> 下表是责任落点而非预制测试实现；函数名为可追踪目标，Shield/Devon 可合并场景，但必须保留每个 AC 引用。

| AC | 计划测试文件 / 函数族 |
|---|---|
| AC-FR0202-01 | `tests/integration/test_web_app_mounts.py::test_ac_fr0202_01_*` |
| AC-FR0202-02 | `test_web_ui_routes.py::test_ac_fr0202_02_*` |
| AC-FR0202-03 | `test_web_ui_routes.py::test_ac_fr0202_03_*` |
| AC-FR0202-04 | `test_web_ui_routes.py::test_ac_fr0202_04_*` |
| AC-FR0203-01 | `test_web_ui_opencode.py::test_ac_fr0203_01_*` |
| AC-FR0203-02 | `test_web_ui_opencode.py::test_ac_fr0203_02_*` |
| AC-FR0203-03 | `test_web_ui_opencode.py::test_ac_fr0203_03_*` |
| AC-FR0203-04 | `test_web_ui_opencode.py::test_ac_fr0203_04_*` |
| AC-FR0204-01 | `test_web_ui_backlog.py::test_ac_fr0204_01_*` |
| AC-FR0204-02 | `test_web_ui_backlog.py::test_ac_fr0204_02_*` |
| AC-FR0204-03 | `test_web_ui_backlog.py::test_ac_fr0204_03_*` |
| AC-FR0205-01 | `test_web_ui_files.py::test_ac_fr0205_01_*` |
| AC-FR0205-02 | `test_web_ui_files.py::test_ac_fr0205_02_*` |
| AC-FR0205-03 | `test_web_ui_files.py::test_ac_fr0205_03_*` |
| AC-FR0205-04 | `test_web_ui_files.py::test_ac_fr0205_04_*` |
| AC-FR0206-01 | `test_web_ui_tasks.py::test_ac_fr0206_01_*` |
| AC-FR0206-02 | `test_web_ui_tasks.py::test_ac_fr0206_02_*` |
| AC-FR0206-03 | `test_web_ui_tasks.py::test_ac_fr0206_03_*` |
| AC-NFR0102-01 | `test_web_ui_opencode.py::test_ac_nfr0102_01_*` |
| AC-NFR0102-02 | `test_web_ui_backlog.py::test_ac_nfr0102_02_*` |
| AC-NFR0102-03 | `test_web_ui_files.py::test_ac_nfr0102_03_*` |
| AC-NFR0102-04 | `test_web_ui_tasks.py::test_ac_nfr0102_04_*` |
| AC-NFR0102-05 | 上述 UI 集合的 Chromium/Firefox matrix，`test_ac_nfr0102_05_*` |

退出条件：23/23 AC 均由至少一个非 skip 自动化测试引用；unit/integration 通过；12 个 UI 场景在 Chromium 与 Firefox 零失败；新增核心逻辑 coverage ≥95%；`ci-scan` 闭合且无反作弊命中；无新增未记录的可观察性缺口。

### Judge Review Checklist

- [ ] 六类 mount 经主 app 真实 HTTP 验证，既有 API e2e 未被复制或替代
- [ ] 23 个 AC 可从测试代码反向追踪
- [ ] 12 个 UI 场景包含点击、表单、状态及必要 reload 断言
- [ ] Chromium 与 Firefox 执行同一关键路径集合
- [ ] fixture 离线、隔离、可复现，real app 未被 mock
- [ ] 无 sleep/CSS class 定位，失败 artifact 足以诊断
- [ ] 已知 locked-interface gap 已显式记录
