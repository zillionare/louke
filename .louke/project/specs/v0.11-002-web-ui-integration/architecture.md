# Louke Web IDE — Web UI 集成 — Architecture

- **Spec ID**: `v0.11-002-web-ui-integration`
- **基线**: 继承 `v0.11-001-web-ide` 的架构、16 个 HTTP endpoint 与 8 个公开 schema
- **运行基线**: Python `>=3.11`、Starlette、vanilla JavaScript、pytest-playwright

## 1. 上下文与目标

本期把 v0.11-001 已交付的六个独立 ASGI sub-app 接入 `louke/web/app.py`，让 v0.10 的 home、wiki、models、docs、login 页面通过 JavaScript client 消费真实 API 而非 mock，并把 NFR-0102 升级为 Playwright 真导航、点击、填写、重载与页面状态断言。

六个 sub-app 的业务逻辑和 v0.11-001 锁定契约不变；`FR-0101` 继续延期。本期不是页面视觉重设计，也不增加服务能力。

## 2. 模块划分

<!-- archer validate-arch requires the literal substring "## 模块划分" to
appear (not "## 2. 模块划分"). This anchor section provides that exact
string for the substring check while preserving the numbered section
hierarchy for human readers. -->

| 模块 | 职责 | 允许依赖 | 不得承担 |
|---|---|---|---|
| **Web UI Client** | `louke/web/assets/client.js`；统一 JSON 请求、错误解析；按选中资源调用六类 API；更新公开 UI 状态 | v0.11-001 HTTP 契约、浏览器 `fetch` | 文件 IO、业务规则、fixture/mock 数据、绕过页面直接成功 |
| **Main App Assembly** | `create_app()` 中组合六个 sub-app 的公开 routes；保持同一 origin；解决既有 wildcard 的顺序冲突 | Starlette route composition、六个 `app` 对象 | 复制 endpoint 实现、改写响应 schema、吞掉错误 |
| **Page Binding** | 为既有 home/wiki/models/docs/login 输出加载 client，并以 `data-testid` 绑定控件、结果和错误出口 | Web UI Client | 新前端框架、依赖 CSS class/DOM 层级、预置成功数据 |
| **六个 sub-app** | OpenCode、Intent、Wiki、Backlog、Files、Tasks 的既有 API 与状态 | v0.11-001 内部 adapter/filesystem 边界 | 本期业务修改或 UI 认知 |
| **UI E2E** | 从页面执行关键用户动作；Chromium/Firefox 共用场景 | `tests/e2e/conftest.py`、真实 main app、确定性 fixture | 以 API 调用替代关键 When、DOM 注入、固定 sleep |

### 2.1 页面归属

| 页面 | 本期绑定 |
|---|---|
| `/` home | OpenCode、Intent、Backlog、Files 操作区及全局导航 |
| `/wiki`、`/wiki/{page}` | canonical Wiki 加载/刷新与 API 错误反馈 |
| `/models` | OpenCode 实例上下文与真实实例数据入口；保留既有 bindings 功能 |
| `/docs/{spec_id}/{doc_name}` | 文档读取/保存与 FR/NFR 三 task checkbox |
| `/login` | 保留既有认证行为；只补稳定导航/页面标识，不接管 auth API |

### 2.2 明确不动

- 不修改 `louke/opencode_api.py`、`intent_api.py`、`wiki_api.py`、`backlog_api.py`、`files_api.py`、`tasks_api.py` 的业务行为。
- 不移除或改变 v0.10 auth、bindings、render、events、store 与旧 Wiki/doc routes。
- 不修改 v0.11-001 locked 文档、37 个 AC 或 API schema；不实现 `FR-0101`。

## 3. 依赖方向与装配

```text
Page Binding -> Web UI Client -> fetch /api/...
                              -> Main App Assembly
                              -> six ASGI route sets
                              -> InMemoryAdapter / filesystem / existing workflow
UI E2E -> browser -> Page Binding (不得直接替代关键 UI 动作)
```

依赖与 v0.11-001 architecture §2.2 一致：UI 只依赖公开 HTTP；sub-app 不 import `louke.web`，领域模块不知道 DOM。

### 3.1 Route composition 规则

六个 sub-app 当前已把完整 `/api/...` 写入自身 route；因此 Main App Assembly **复用其 Route 对象或等价 `add_route` 组合**，不对已带前缀的 app 再做会产生双前缀的朴素 `Mount("/api/...", app)`。这是装配 glue，不复制 endpoint。

组合顺序遵守“具体 API 在 wildcard 前”：`/api/wiki/{type}` 的五个 canonical type/method 必须优先于 v0.10 `/api/wiki/{page:path}`；旧 `/api/wiki`、`/api/wiki/refresh` 和其他页面路由保持原行为。其余五类 route 在同 method/path 无冲突时直接组合。集成测试以真实 HTTP 验证，不检查内部 routes 数组。

## 4. 数据流与失败语义

1. 页面加载后 client 从真实 GET endpoint hydrate；不提供 fallback mock。
2. 用户点击/填写后，binding 将当前 `instance_id`、backlog id、path、revision、`fr_id`/task 明确传给 client。
3. 2xx 响应更新对应 `[data-testid]` 状态；实例消息按 id 独立渲染，task patch 只合并目标字段。
4. 非 2xx 按 v0.11-001 `ErrorResponse` 显示在页面 error exit，清除 pending，且不得显示 success；网络/非 JSON 失败映射为通用可见错误，不伪造业务机器码。
5. backlog 删除、文件保存、task 修改成功后以响应更新并允许 reload/reopen 再由 GET/文件事实确认持久化。

本期不新增 SSE。OpenCode 回显使用已锁定 messages GET；Wiki 可继续使用既有页面刷新行为。若实现复用 v0.11-001 SSE，只能消费原契约，不得建立新的 UI event bus 公共接口。

## 5. 技术选择与权衡

| 选择 | 解决的问题 | 放弃方案 | 主要风险 / 控制 |
|---|---|---|---|
| Starlette route composition | sub-app 已声明完整路径；同 server、无 proxy | 朴素 prefix Mount、复制 handlers、独立端口反代 | v0.10 Wiki wildcard 抢先；以具体 route 优先、代表 endpoint integration test 控制 |
| `louke/web/assets/client.js` vanilla JS | 复用现有 server-rendered 单文件页面与 `/assets`，零构建链 | React/Vue、Node bundler、每页重复 inline fetch | 全局 API 漂移；以 `window.LoukeClient` 契约和 client unit test 控制 |
| `data-testid` + accessible label | Shield 可稳定定位且兼顾可访问性 | CSS class、DOM 深度、仅易变文案 | 标识遗漏；interfaces §7 列为强制页面出口 |
| HTTP JSON + messages GET | 最小接通已锁定能力，不新增协议 | 新 WebSocket/UI event bus | 轮询实时性有限；只在用户动作/实例切换后刷新，本期无实时性 AC |
| 既有 30 API e2e + 12 UI 场景 | API 契约与用户流职责分离 | 所有 API 场景在浏览器重写、只做页面 GET smoke | suite 时间增加；UI 只覆盖 FR-0202..0206/NFR-0102 关键流 |
| pytest-playwright 双浏览器 | 复用 Python fixture 与 CI，满足 Chromium/Firefox | Cypress/Selenium/WebKit | browser 安装与 flake；固定依赖、条件等待、trace/screenshot，禁止 sleep |

不新增运行时第三方库；沿用项目 lock 中 Starlette/uvicorn。开发依赖沿用已选 `pytest`、`pytest-playwright`、`playwright`，不在未检查 lock 时臆造精确版本；均与项目 MIT license 兼容。

## 6. 接口契约增量

| 增量 | 规范出口 |
|---|---|
| JavaScript public client | `interfaces.md` §7.1 的 `window.LoukeClient` 六个 namespace/method |
| 页面与导航 | §7.2 的 page/nav `data-testid` |
| OpenCode/Backlog/Files/Tasks | §7.3–§7.6 的 control、result、success/error exits |
| Wiki/models/login | §7.7 的页面及真实数据/失败出口 |
| 错误 | §7.8：`ui-error` 可见、`ui-success` 不可见；保持锁定 ErrorResponse |

## 7. 验证与关闭条件

- mount integration 通过同一 `create_app()` 对六类代表 endpoint 发真实 HTTP；页面 route 无回归。
- 12 个 UI 场景仅以公开控件完成关键 When，并在 Chromium、Firefox 零失败。
- 23/23 AC 由 `interfaces.md` §8 指向 `test-plan.md` §8 的函数族；CI 执行 `lk agent archer ci-scan --acceptance .louke/project/specs/v0.11-002-web-ui-integration/acceptance.md --tests tests/`。
- Devon 可按模块边界、route precedence 与 client method 直接实现；Shield 可按稳定 control/result/error exits 独立编写 e2e。
