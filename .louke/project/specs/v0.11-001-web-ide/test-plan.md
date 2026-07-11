# Louke Web IDE 与工作流服务化 — Test Plan

- **Spec ID**: v0.11-001-web-ide
- **Created**: 2026-07-11
- **Related acceptance**: `.louke/project/specs/v0.11-001-web-ide/acceptance.md`
- **Related interfaces**: `.louke/project/specs/v0.11-001-web-ide/interfaces.md`（M-ARCH 阶段补齐的断言出口；见 §6.5）
- **Test framework**: `pytest`

## 1. 概述与边界（Stance and Boundaries）

### 1.1 测试目标与范围

本计划验证 Web IDE 的外部可观察行为：OpenCode 实例交互、指令分类与路由、Wiki 更新、`.louke` 产物落位、FR/NFR task 状态持久化、本地 story backlog、工作区文件与 diff、Markdown 文档展示，以及自动化质量、双浏览器兼容和文件访问安全。

正式自动化范围为本 spec 中本期实施的 8 个 FR 与 3 个 NFR，共 34 个 AC。`FR-0101` 虽在 `acceptance.md` 中保留 3 个 AC，但 spec 已明确延后至下一个 spec；本期不得实现、不得为其编写占位或跳过测试，也不把它计入本期 AC 闭合分母。

### 1.2 黑盒立场与可观察对象

测试只通过以下外部出口断言；最终名称、schema 和错误语义由 M-ARCH 的 `interfaces.md` 固化：

- Web 页面可操作控件、可访问文本、状态和导航；
- Web service 的公开 HTTP/WebSocket 出口；
- OpenCode mock server 收到的协议请求及返回的协议响应；
- workspace、backlog、Wiki 和设计文档的持久化文件；
- Git diff 和公开的结构化运行状态/错误响应；
- 进程退出码、pytest 结果和 coverage 报告。

测试不得依赖内部 class 层次、私有方法、内部队列、状态机、registry 或缓存。若 AC 所需状态在 `interfaces.md` 中没有出口，视为可测试性缺口，先修订接口设计，不允许从测试侧窥探内部状态。

### 1.3 不在范围

- `FR-0101` 的 Louke Server 多 Agent 工具化、迁移清单和 Maestro 调度路径；
- WebKit、移动浏览器和视觉像素级回归；
- 真实外部 OpenCode 服务的持续 CI 可用性或性能；
- backlog 完整 CRUD、排序、去重；
- 通用源代码编辑能力；
- `acceptance.md` 中 FR-0301 的未编号 Candidate AC；待其成为正式 AC 后另行纳入。

### 1.4 防作弊与追踪约束

1. 每个测试函数 docstring/comment 首行必须含完整 `AC-FRXXXX-YY` 或 `AC-NFRXXXX-YY`。
2. CI 使用真实运行契约：

   ```bash
   lk agent archer ci-scan \
     --acceptance .louke/project/specs/v0.11-001-web-ide/acceptance.md \
     --tests tests/
   ```

   扫描时须按本 spec 的延期决策排除 `AC-FR0101-01..03`；若当前 `ci-scan` 不支持 spec 级排除，这是合并前必须解决的 gate 配置缺口，不得用 skip 规避。
3. 禁止仅有 `assert True`、吞异常、以实现输出生成 expected、无 issue 链接的 skip，或 mock 系统内部核心逻辑。
4. 测试变更 PR 必须标识 New AC / Spec change / flake-environment issue；不得因实现偏离 spec 而弱化断言。

### 1.5 分工

- Devon：单元测试与集成测试，随实现提交；核心业务模块纳入 coverage。
- Shield：独立编写 host-project e2e，使用公开 UI/API 和外部 stand-in。
- Prism/Judge：检查 AC 引用、断言强度、双浏览器结果和 fixture 独立性。

## 测试策略

### 2.1 单元测试

面向纯规则与边界函数：意图分类结果、命令透传、实例隔离、路径规范化和 realpath 越界判定、可写文件 allowlist、二进制/行数判定、Markdown task 定点修改、文档发现规则、backlog 选择规则、Wiki change detection 和来源链接生成。外部 OpenCode、文件系统、Git 和时钟通过公开依赖边界替换；不 mock 被测规则本身。

### 2.2 集成测试

使用项目现有 `conftest` 组织的 pytest fixture，并以 Starlette `TestClient`/公开 app assembly point 连接真实路由、持久化 adapter 与临时 workspace。集成层验证 HTTP/WebSocket 协议、文件落盘、Git diff、mock OpenCode 协议、Wiki 构建触发和 reload 后状态，不启动真实浏览器。

### 2.3 E2E 测试

采用 `pytest` + Playwright Python plugin 驱动真实页面；所有承诺的 Web 关键路径在 Chromium 与 Firefox 两个 project 上执行。e2e 不 patch Louke 内部对象，只允许启动独立 OpenCode mock server、使用临时 workspace 和可控时间源。API-only 的安全负例可用公开 HTTP client 补充，但不能替代双浏览器关键路径。

### 2.4 Ground Truth Method

本功能以协议、文件与规则正确性为主，不建立独立算法 ground-truth 实现。expected 来自预置输入 fixture、Git 自身公开输出、保存前后的原始文件字节和 mock server 协议记录，不从被测实现反算。若后续引入 Wiki 内容算法，其 reference 数据放在 `tests/ground_truth/`，且不得 import `louke.*`。

## 3. 需求覆盖分配

> 本节只规定 AC 到测试层的责任分配，不预先固定测试函数清单；最终双向闭合由 `lk agent archer ci-scan` 从测试代码反向生成。

- **FR-0001** — `AC-FR0001-01..04`：单元验证透传、隔离和停止规则；集成验证公开协议与 mock OpenCode；e2e 验证创建、选择、消息/状态回显、`models`/`agent` 和停止。
- **FR-0101（延期）** — `AC-FR0101-01..03`：本期不覆盖、不进入闭合分母；下一 spec 依据迁移清单重新设计。
- **FR-0201** — `AC-FR0201-01..04`：单元验证分类/低置信度规则；集成验证动作出口；e2e 验证 story 二选一、spec change、fix 和确认前零动作。
- **FR-0301** — `AC-FR0301-01..05`：单元验证 change detection、编号和来源规则；集成验证五类产物、首页/项目信息、手动与定时同一路径；e2e 验证更新按钮、可追溯内容和无变更不改写。
- **FR-0401** — `AC-FR0401-01..03`：集成验证经 M-ARCH 确认的目录映射、四类产物落位及基线目录不被 spec 阶段重排；无独立 UI e2e。
- **FR-0501** — `AC-FR0501-01..03`：单元验证 Markdown task 定点变换；集成验证持久化；e2e 验证 checkbox 独立切换、保存和 reload。
- **FR-0601** — `AC-FR0601-01..03`：单元验证选择规则；集成验证本地持久化和流程交接；e2e 验证创建、单项进入开发、未选择反馈和成功后移除。
- **FR-0701** — `AC-FR0701-01..04`：单元验证访问/预览规则；集成验证 Git 与文件出口；e2e 验证文件、变更、diff、可写文档、源代码拒写、二进制和 500 行批准门。
- **FR-0801** — `AC-FR0801-01..03`：单元验证 glob/范围/预览规则；集成验证 Markdown 读取与渲染出口；e2e 验证导航、选中文档对应内容及拒绝项。
- **NFR-0001** — `AC-NFR0001-01..02`：CI 集成层验证 pytest/e2e 零失败及核心模块 coverage ≥95%；`AC-NFR0001-01` 同时由 e2e run 结果覆盖。
- **NFR-0101** — `AC-NFR0101-01`：仅由 Chromium + Firefox e2e matrix 的六条关键路径共同覆盖；不以 user-agent 单元测试替代。
- **NFR-0201** — `AC-NFR0201-01..02`：单元覆盖 path traversal、绝对路径、`..`、symlink realpath 与 allowlist；集成验证公开读取/diff/save 均拒绝且目标字节不变；e2e 验证 UI/API 不泄露、不写入。

计划引用覆盖数（测试层可重叠）：单元 28 个 AC，集成 33 个 AC，e2e 30 个 AC；本期正式闭合分母为 34 个 AC。

## 4. 测试基础设施

### 4.1 pytest 配置与目录

沿用项目既有 pytest 和现有根级 fixture 约定；若当前尚无根级 `conftest.py`，Devon/Shield 应在既有 `tests/` 下建立共享 fixture，而不是另建测试框架。

```text
tests/
├── unit/             # 纯规则；镜像 louke/ 模块边界
├── integration/      # TestClient + 临时 workspace + 外部 stand-in
├── e2e/              # Shield 的 Playwright 场景
├── fixtures/         # 离线、可复现输入
└── ground_truth/     # 仅在后续出现独立 reference 算法时启用
```

- 文件：`test_<scenario>__<subscenario>.py`；函数：`test_ac_<requirement>_<ac>_<subscenario>`。
- markers：`unit`、`integration`、`e2e`；browser 由 Playwright project/fixture 参数化。
- 顺序：unit → integration → e2e；测试不得依赖执行顺序。
- coverage：以 `pytest-cov` 对本功能核心 `louke` 模块计量，不得通过 omit 排除新 Web IDE 核心模块。

### 4.2 可替换外部依赖

- **OpenCode 实例**：独立 mock server 实现 M-ARCH 确认的最小公开协议，记录 instance id、消息/命令和 stop 请求，可脚本化成功、错误、延迟与断连；不实现 Louke 路由逻辑。
- **文件 IO 权限**：真实临时目录和真实 symlink；通过 OS 文件权限补充只读失败，但业务 allowlist 仍须由公开请求验证。
- **Wiki 生成**：固定源文档与可控时钟/触发器；替代外部生成服务，不替代 Louke change detection、来源追踪或发布逻辑。
- **Git**：每例初始化临时 Git repository 并产生确定性 staged/unstaged diff，不 mock Git 解析结果。

## 5. 数据与 Fixture

### 5.1 Web IDE 沙箱

每个测试获得独立临时 workspace，包含最小 `.louke/project`、`README.md`、递归 `docs/`、源代码、允许编辑的三类文档、501 行文本、二进制文件、workspace 外 sentinel 及指向 sentinel 的 symlink。测试结束核对 sentinel 和只读文件字节不变并清理沙箱。

### 5.2 OpenCode mock server

fixture 分配随机本地端口，预置两个具有唯一 id 的实例和按 instance 隔离的输出队列。代表性脚本包括普通消息、`/models`、`/agent`、明确错误、停止后发送失败；所有请求日志在公开 mock 管理出口可读取，用于断言请求发往正确实例。

### 5.3 Mock 文件系统与 Wiki 数据

单元层可使用最小 fake filesystem boundary；集成/e2e 必须使用真实临时文件系统，以实际验证 realpath、symlink、mtime、原子保存和 Git diff。Wiki fixture 固定五类源文档、review 裁决、FAQ、项目字段和来源 anchor；无变更场景记录产物 bytes/mtime，避免只断言“调用次数”。

### 5.4 隔离与可复现性

- 所有数据离线、无 secrets，不访问生产 OpenCode/GitHub。
- browser context、workspace、mock server 状态按测试隔离。
- 时间、端口和文件路径不得硬编码；随机值需在失败输出中记录。
- unit 与 e2e 使用不同内容样本，防止围绕同一 fixture 过拟合。

## 6. Host-project E2E

### 6.1 框架与浏览器承诺

选择 `pytest` + `pytest-playwright`/Playwright Python API，与项目测试入口一致，并复用 Starlette/uvicorn 的既有启动方式。每条 Web 关键路径必须在 `chromium` 和 `firefox` 执行；WebKit 明确不在范围。版本在 M-ARCH 根据当时 lock/兼容矩阵固定，本阶段不臆造未安装版本。

### 6.2 启动、就绪、执行契约

M-ARCH 应把以下 host-project 契约写入 `.louke/project/project.toml [e2e]`；本阶段仅声明目标，不修改当前属于 v0.8 的旧 e2e 配置：

- `cwd = "."`
- `paths = ["tests/e2e", "tests/fixtures"]`
- `start = "python -m louke serve --host 127.0.0.1 --port 8765"`（复用既有入口）
- `ready = "curl -sf http://127.0.0.1:8765/health"`
- `ready_timeout_seconds = 60`
- `run`：由 M-ARCH 在 Playwright 依赖与 pytest markers 落定后写成项目可直接运行且同时覆盖 Chromium/Firefox 的单命令；不得保留仅 `pytest tests` 的模糊入口。
- `teardown`：M-ARCH 必须设计能可靠停止 `start` 进程的 host-project 既有/新增正式入口；不得以 `true` 冒充清理。

Shield 执行顺序固定为 start → ready 重试 → run → 无论成功失败均 teardown；OpenCode mock server 的生命周期由 e2e fixture 管理。

### 6.3 E2E 场景族（30 个 AC 引用，非预制测试函数清单）

1. **OpenCode 交互**：创建/选择唯一实例；双实例定向消息与输出隔离；`/models`、`/agent` 透传成功或明确错误；停止及停止后发送失败（4 AC）。
2. **指令路由**：story 显示“立即开发/存 backlog”选择；spec change 与 fix 各走正确动作；歧义输入先澄清且确认前无副作用（4 AC）。
3. **Wiki 更新**：五类汇总与展示编号；事实来源链接；review 裁决；首页/FAQ/项目信息；手动更新和无变化不改写（5 AC）。
4. **Backlog 转开发**：创建并持久化；多个条目只传递选中项且成功后移除；未选择时阻止启动（3 AC）。
5. **文件/diff 与文档**：文件/变更/diff；源代码拒写与文档保存；二进制及 500 行批准门；允许 Markdown 发现、导航、渲染及范围拒绝（7 AC）。
6. **文档状态保存**：三个独立 task checkbox；`- [ ]`/`- [x]` 双向保存和 reload；单项变化不污染其他 task（3 AC）。
7. **安全负例**：workspace 外 read/diff/save（含 symlink）全部拒绝且 sentinel 不变；非 allowlist 写入拒绝且字节不变（2 AC）。
8. **交付与兼容门**：e2e run 零失败；上述六条用户关键路径在 Chromium 与 Firefox 全通过（2 AC）。

`AC-NFR0001-02` 的 coverage gate 由 CI 集成检查覆盖，不属于浏览器 e2e；`FR-0401` 的目录规划由集成测试覆盖。

### 6.4 自动化断言原则

- 使用 role/label/test-id 等稳定公开语义定位，禁止依赖 CSS 层次和 sleep。
- 页面动作之后同时断言用户可见结果与对应公开持久化出口；不得直接读取内部 Python 对象。
- 等待明确网络/状态条件；失败产出 trace、screenshot 和 server log，但 artifact 不含 workspace 外文件内容。
- 同一逻辑场景参数化浏览器，不复制两套易漂移脚本。

### 6.5 与 interfaces.md 的闭合

M-ARCH 必须至少定义：实例/会话操作出口、指令分类与确认出口、Wiki 更新状态与产物 schema、目录映射、task 保存、backlog 保存/交接、workspace 文件/read/diff/save、Markdown 文档导航/渲染、结构化错误与 health。所有断言只能落在这些出口。每个接口出口在本计划的 unit、integration 或 e2e 至少有一层覆盖；接口新增时必须同步修订本计划。

## 7. 外部依赖分层、风险与开放项

### 7.1 分层

- **L1 deterministic simulation（默认 CI）**：可控时钟、固定文档、纯规则和临时 filesystem。
- **L2 contract simulation（默认 CI）**：独立 OpenCode mock server + 真实 Louke app + 真实浏览器/HTTP client。
- **L3 real environment smoke（manual/nightly，可选）**：真实 OpenCode 最小 round-trip；不计入本期 DoD，必须显式 marker，不得用无 issue skip 混入默认 CI。

### 7.2 NFR-0201 文件访问安全

攻击输入至少覆盖绝对路径、`..`、URL 编码 traversal、workspace 前缀碰撞、指向外部文件/目录的 symlink、read/diff/save 三种操作及 TOCTOU 可观察结果。成功标准不是仅返回错误：还须证明响应不泄露 sentinel 内容、外部及只读目标 bytes/mtime 不变。不同 OS 的 symlink 权限差异须在支持环境执行；若 CI 平台不能创建 symlink，应增加具备该能力的 CI job，而非跳过 AC。

### 7.3 风险与开放项

- 当前仓库未发现 Playwright 配置/依赖；M-ARCH 必须固定兼容 Python ≥3.11 的稳定版本、browser install 命令和 CI cache，评估新增依赖影响。
- 当前 `[e2e]` 属于 v0.8 且只列 Chromium、`run = "python -m pytest tests"`、`teardown = "true"`；M-ARCH 必须替换为 v0.11 的双浏览器和可靠清理契约。
- OpenCode 实际协议尚需 interfaces.md 固化；mock server 必须契约一致，不能依据实现私有调用编写。
- Wiki 定时任务需可控时钟或公开触发出口；缺失时是接口阻塞项。
- `FR-0101` 延期：本 e2e 不验证 Louke Server 多 Agent 流程，也不创建占位测试；下一 spec 独立闭合。
- `ci-scan` 对延期正式 AC 的排除能力需在实现测试前确认，否则 34/37 分母会产生假失败。

## 8. 退出标准与 Judge Review Checklist

### 8.1 退出标准

- 本期 34 个 AC 每个至少被一个非 skip 自动化测试引用；`FR-0101` 三项按延期规则明确排除。
- unit、integration 全通过；Chromium 和 Firefox 的 host-project e2e 全通过，零 failure/error。
- 本功能核心单元测试 coverage ≥95%，且无 omit/路径配置规避。
- NFR-0201 的外部 sentinel、源代码和非 allowlist 文件均保持未读泄露/未修改。
- `lk agent archer ci-scan` 的 AC 闭合、反作弊和 coverage gate 通过。
- 无未解决的 interfaces 可观察性缺口；测试 artifact 足以定位失败且不泄密。

### 8.2 Judge Review Checklist

- [ ] 测试策略覆盖 OpenCode、路由、Wiki、backlog、文件/diff、文档状态和安全风险
- [ ] 34 个本期 AC 可从代码反向追踪，3 个延期 AC 有 gate 排除依据
- [ ] 测试计划未将示例场景固化为实现导向的测试函数清单
- [ ] Chromium 与 Firefox 均执行同一关键路径集合
- [ ] 测试数据离线、可复现、互相隔离
- [ ] 外部依赖只在公开边界被 stand-in 替换，未 mock Louke 内部核心
- [ ] `interfaces.md` 的每个外部出口至少有一层测试覆盖
- [ ] coverage ≥95%，核心模块未被排除
- [ ] start/ready/run/teardown 可在干净环境单命令执行并可靠清理
