# Louke Web IDE 与工作流服务化 — Architecture

- **Spec ID**: `v0.11-001-web-ide`
- **适用范围**: 本期 8 个 FR、3 个 NFR；`FR-0101` 明确延期
- **运行基线**: Python `>=3.11`，继承现有 Starlette/uvicorn 与 pytest 技术栈

## 1. 上下文与目标

本期在现有 Louke Python 包上增加一个本地 Web IDE。浏览器通过 Louke Server 使用 OpenCode 实例、浏览及生成 Wiki、维护 story backlog、查看 workspace 文件/Git diff、展示 Markdown，并仅编辑明确允许的设计文档。Louke Server 是浏览器与本地资源之间唯一的信任边界；OpenCode 集成经可替换协议适配器完成，CI 可用独立 mock 替代真实 OpenCode。

本期不实现 `FR-0101` 的 Agent 工具化、迁移清单或 Maestro 调度。不得为延期能力建立占位服务路径；下一 spec 需重新完成接口与测试闭合。

## 2. 总体架构

## 模块划分

### 2.1 模块边界

| 模块 | 职责 | 允许依赖 | 禁止承担 |
|---|---|---|---|
| **Louke Server** | Starlette app assembly、HTTP/SSE 路由、请求校验、统一错误映射、`/health`、模块生命周期 | 下列应用模块及 adapter 的公开边界 | OpenCode 私有协议细节；直接绕过文件沙箱 |
| **Web UI** | 实例选择与交互、意图确认、Wiki/Backlog/文件/文档页面、稳定可访问控件 | Louke Server 的 HTTP/SSE 契约 | 直接文件 IO；以浏览器路径判断替代服务端授权 |
| **OpenCode Adapter** | OpenCode 实例 create/list/stop、消息发送、事件流归一化；真实端与 mock 端可互换 | 外部 OpenCode 协议/进程 | 意图分类；跨实例合并输出 |
| **Wiki Generator** | 五类 canonical Wiki 的变更检测、生成、来源链接、构建进度与原子发布；手动/每日触发共用入口 | 安全文件读取、时钟/调度 boundary | 在无源变更时重写产物；静默虚构来源 |
| **Backlog Manager** | 本地 story 条目持久化、列表、选中条目交接、成功交接后删除 | 规范 backlog store、现有新 story 流程公开入口 | 排序、去重、完整 CRUD |
| **File Browser** | workspace 文件/变更/diff、文档发现、二进制与行数门、realpath 沙箱及可写 allowlist | filesystem、Git subprocess boundary | 读取 workspace 外目标；写源代码 |
| **Doc Editor** | Markdown 渲染；允许设计文档保存；FR/NFR 三个 task 的定点持久化 | File Browser 的授权后读写出口、Markdown renderer | 自行扩展可写范围；通用源码编辑 |
| **Intent Router** | 分类 `story`/`spec_change`/`bug_fix`/未知，产生拟执行动作或澄清要求；确认后才交接 | classifier boundary、Backlog Manager/现有流程公开入口 | 低置信度时执行；实现延期的 Agent 工具化 |

### 2.2 依赖方向

```text
Web UI -> Louke Server
Louke Server -> Intent Router -> Backlog Manager / existing workflow entry
Louke Server -> OpenCode Adapter -> OpenCode instance
Louke Server -> Wiki Generator -> File Browser -> filesystem / Git
Louke Server -> Doc Editor -> File Browser
Backlog Manager -> File Browser-authorized canonical store
```

依赖箭头只向领域能力和外部 boundary。领域模块不得 import Web UI 或 HTTP route；这样 Devon 可在单元层替换 OpenCode、时钟、Git 和 filesystem，Shield 可仅从公开 HTTP/SSE 驱动完整系统。

### 2.3 规范产物位置

| 类别 | 规范位置 | 写入者 | 可观察方式 |
|---|---|---|---|
| Louke Server runtime | `.louke/server/` | Louke Server | 文件列表/运行日志 |
| code review | `.louke/reviews/` | review workflow | 安全文件读取/Wiki 来源 |
| session save | `.louke/raw/{yy-mm-dd}/` | session reserve | 安全文件读取 |
| Wiki | `.louke/project/wiki/` | Wiki Generator | `/api/wiki/{type}` |
| story backlog | `.louke/project/backlog.json` | Backlog Manager | `/api/backlog` |

目录创建与兼容迁移必须由实现以一次性、幂等方式完成；本架构文档本身不移动现存目录。

## 3. 关键决策与需求映射

| Requirement | 模块 | 外部接口/出口 | 决策 |
|---|---|---|---|
| FR-0001 | Web UI、Louke Server、OpenCode Adapter | instance、message HTTP API；OpenCode SSE | 按 instance id 隔离；所有 `/` 命令原样透传 |
| FR-0101 | — | — | **延期，不放入本期架构、接口、代码或测试分母** |
| FR-0201 | Intent Router、Web UI | `POST /api/intent/route` | route 先返回拟执行；需选择/澄清时零副作用 |
| FR-0301 | Wiki Generator、File Browser、Web UI | Wiki HTTP API、Wiki progress SSE | 五类 canonical 页面；手动和每日走同一生成入口；无变化不发布 |
| FR-0401 | Louke Server、Wiki Generator、Backlog Manager | 规范路径表、对应读取 API | server/review/session/wiki 互不混放 |
| FR-0501 | Doc Editor、File Browser | `PATCH /api/tasks/{fr_id}` | 仅修改目标 `Valid`/`Testable`/`Decided` task |
| FR-0601 | Backlog Manager、Intent Router | `/api/backlog` | 最小字段为 story；交接成功后删除 |
| FR-0701 | File Browser、Doc Editor | `/api/files`、`/diff`、`PUT /{path}` | realpath 沙箱；二进制拒绝；>500 行需显式批准 |
| FR-0801 | Doc Editor、File Browser、Web UI | `/api/files?scope=documents` | 仅 Louke design Markdown、README、`docs/**/*.md` |
| NFR-0001 | 全部核心模块 | pytest/coverage/e2e 退出码 | 核心模块 coverage ≥95%，e2e 零失败 |
| NFR-0101 | Web UI、Louke Server | `[e2e].run` | 同一关键路径覆盖 Chromium 与 Firefox |
| NFR-0201 | File Browser、Louke Server | 所有 files/diff/save 出口及统一错误 | 规范化、realpath、symlink、TOCTOU 防护均在服务端 |

## 4. 进程与并发模型

- Louke Web 服务采用**单进程 ASGI** 基线；单一 workspace 下的写操作按目标资源串行化，避免 task、backlog 和 Wiki 发布互相覆盖。
- OpenCode 实例是受 Adapter 管理的外部进程/连接，不把其输出队列暴露为测试接口。每条事件都携带 `instance_id`，Server 只向该实例订阅流回送。
- Wiki 每次仅允许一个 active build；并发触发复用或返回当前 build id。每日检查通过可替换 clock/scheduler 触发。
- Playwright e2e 可由 pytest worker 并行，但每个 fixture 使用独立 browser context、随机端口和临时 workspace；不得让多个 worker 共享可写目录或 mock 状态。

## 5. 数据流

### 5.1 OpenCode 消息流

```text
用户 -> Web UI -> Louke Server -> OpenCode Adapter -> OpenCode 实例
用户 <- Web UI <- SSE(instance_id,event) <- Louke Server <- OpenCode Adapter
```

1. Web UI 将消息和当前 `instance_id` 发送给 Server。
2. Server 验证实例处于 `running`，把普通消息或完整 `/...` 命令原样交给 Adapter。
3. Adapter 将外部响应归一化为接口事件；Server 保留 `instance_id` 并经 SSE 回送。
4. Web UI 只把事件追加到同 id 会话；断流可按最后 `event_id` 重连，不跨实例补发。

### 5.2 其他主数据流

- **Intent**：输入 → 分类结果/置信度 → 拟执行或澄清 → 用户选择/确认 → 对应流程；确认前不产生流程副作用。
- **Wiki**：触发 → 扫描允许源 → digest 比较 → 变更时构建五类页面 → 校验来源 → 原子发布 → SSE 终态；无变化返回 `unchanged`。
- **文件**：请求 path → URL decode/规范化 → workspace realpath containment → 类型/行数/写 allowlist → 读取、Git diff 或原子写入。

## 6. 错误处理与降级

| 场景 | HTTP/事件行为 | 降级与一致性 |
|---|---|---|
| OpenCode 无响应/断连 | `504 OPENCODE_TIMEOUT` 或流事件 `instance.error` | 实例转 `error`；不把超时伪装为成功；其他实例不受影响，可停止或重建 |
| OpenCode 已停止后发送 | `409 INSTANCE_NOT_RUNNING` | 不调用外部实例，保留既有消息历史 |
| 文件权限拒绝 | `403 FILE_PERMISSION_DENIED` | 不回传文件正文；原文件 bytes/mtime 不变 |
| traversal/symlink 越界 | `403 PATH_OUTSIDE_WORKSPACE` | 在打开前及使用已验证文件句柄时校验；detail 不泄露外部内容 |
| Wiki 源不存在 | `404 WIKI_SOURCE_NOT_FOUND`；build 为 `failed` | 不替换上一份成功 Wiki；SSE 给出失败终态和缺失的逻辑源标识 |
| Wiki 无变化 | `200`，状态 `unchanged` | 不调用生成器、不改写 bytes/mtime |
| 输入/状态冲突 | `400 VALIDATION_ERROR` / `409 STATE_CONFLICT` | 无部分写入；客户端 reload 后可重试 |

所有失败使用 `interfaces.md` 的统一错误 schema；server log 记录 correlation id 和逻辑路径，不记录 workspace 外正文或 secrets。

## 7. 安全边界

1. **沙箱根**：启动时注入一个 canonical workspace root；读、diff、写均先 URL decode 一次、拒绝绝对路径与 `..`，再以 `realpath` containment 校验。
2. **symlink**：请求路径任一组件为 symlink 即拒绝；即使解析目标仍在 workspace 也不依赖 symlink 作为授权路径，消除替换竞态。解析后越界必定返回 `PATH_OUTSIDE_WORKSPACE`。
3. **TOCTOU**：授权与 IO 使用同一已解析目标/安全打开方式；写入临时文件后在同目录原子替换，并再次确认目标身份。
4. **读写分离**：workspace 内源代码及一般文档只读；唯一可写 basename 为 `story.md`、`spec.md`、`acceptance.md`，且必须位于 `.louke/project/**`。task PATCH 也受同一 allowlist 约束。
5. **展示门**：二进制永不返回正文；超过 500 行仅在请求携带当次明确 `approved=true` 后返回正文。文档渲染入口进一步限制为 Louke design Markdown、根 README 和 `docs/**/*.md`。
6. **认证**：本期是 loopback 内部工具，不引入账户系统；服务默认绑定 `127.0.0.1`。接口 `auth` 标为 local-session，若非 loopback 部署必须由部署层提供认证，不能直接暴露。

## 8. E2E 入口契约

`project.toml [e2e]` 是 Shield/CI 的唯一编排来源：

| 阶段 | 契约 | 设计保证 |
|---|---|---|
| start | `python -m louke e2e start --host 127.0.0.1 --port 8765 --opencode mock` | 正式 host-project 入口；后台启动 Server 与独立 mock OpenCode，创建 tmp workspace，并写受控 pid/state |
| ready | `curl -sf http://127.0.0.1:8765/health` | 仅在 HTTP、workspace 与 mock adapter 均 ready 时返回 200 |
| run | `python -m pytest -m e2e tests/e2e --browser chromium --browser firefox` | 同一场景参数化执行 Chromium 与 Firefox；WebKit 不在承诺范围 |
| teardown | `python -m louke e2e stop --port 8765 --cleanup-workspace` | 无论测试结果均停止受控进程并清理本轮 tmp workspace；幂等 |

`e2e start/stop` 是 Devon 需要实现的 host-project CLI 契约，不是让 Shield 临时发明脚本；Shield 只编写 `tests/e2e` 和 fixture。浏览器二进制安装由 CI 使用 Playwright 官方安装命令完成。

## 9. 技术选择与权衡

| 选择 | 解决的问题 | 放弃的方案 | 主要风险/控制 |
|---|---|---|---|
| Python `>=3.11` + Starlette `>=0.38,<1.0` + uvicorn `>=0.30,<1.0` | 继承当前运行时和 ASGI app，减少迁移 | 新建 Node/React server 或 Django | Starlette 大版本范围较宽；以 lock/CI 矩阵固定解析版本，升级需 contract tests |
| HTTP JSON + SSE | 命令式 CRUD 与单向流式回显/进度 | 全部 WebSocket、轮询 | SSE 仅单向且代理可能断连；以 event id、终态和重连支持控制 |
| OpenCode Adapter protocol | CI 可替换、实例隔离、外部协议变化集中处理 | route 直接调用 OpenCode | adapter 与真实协议漂移；mock 与可选 real smoke 共用 contract suite |
| filesystem JSON/Markdown 规范存储 | 保持 Louke 本地、可审阅、无需数据库 | SQLite/外部 DB | 并发写与损坏；资源锁、临时文件、fsync/atomic replace |
| Python-Markdown `>=3.6,<4.0` | 继承现有 Markdown 渲染 | 前端独立 parser | HTML 注入；输出必须 sanitize/escape，不允许源 HTML 获得脚本权限 |
| httpx `>=0.27,<1.0` | Adapter/集成测试异步 HTTP | requests | API 在 1.0 前可能变化；lock 并由 adapter contract 隔离 |
| pytest + pytest-cov + pytest-playwright | 同一 Python 门槛下 unit/integration/e2e，双浏览器 | Jest/Cypress 或 Selenium | 浏览器下载体积与 flake；固定 lock、官方 browser cache、无 sleep、trace 诊断 |
| 单进程 + 文件锁/原子替换 | 本地工具简单且行为确定 | 多 worker/分布式队列 | 长 Wiki build 阻塞风险；异步 task + progress SSE，本期不引入队列服务 |

新增开发依赖应在实现 PR 中锁定当时支持 Python 3.11 且稳定的 `pytest-playwright`、`playwright`、`pytest-cov` 版本；架构不在未检查 lock 的情况下臆造精确版本。所有所选库与项目 MIT license 兼容。文档沿用 Markdown；lint/typecheck 沿用项目既有 pre-commit/mypy 约定，不引入第二套格式化体系。
