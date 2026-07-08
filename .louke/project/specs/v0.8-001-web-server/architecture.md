# v0.8-001 — Web Server 协作界面 — Architecture

- **Spec ID**: v0.8-001-web-server
- **创建日期**: 2026-07-08
- **关联**: `spec.md` / `acceptance.md` / `test-plan.md`

## 1. 架构结论

本期采用 **单进程 Python ASGI web server + 文件系统作为唯一业务真相源 + 浏览器双栏编辑/预览工作台** 的方案。

关键决定如下：

| 议题              | 决策                                                                                      | 理由                                                                                                                |
| ----------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| 服务形态          | 单进程 ASGI 服务，`lk serve` 启动                                                         | louke 现有主体是 Python CLI，复用语言与打包链最省增量                                                               |
| 部署边界          | 面向团队内部网络；默认本机或局域网部署；若需公网暴露，必须由外层反向代理 / VPN / SSO 保护 | 当前 spec 没有要求内建鉴权系统，但又明确不是“单人本地壳”                                                            |
| 数据真相源        | 继续使用仓库内 Markdown / JSON 文件                                                       | 必须兼容 louke 现有 CLI / Agent 工作流                                                                              |
| 协作策略          | 保存级协作，不做 Google Docs 式逐字符协同编辑                                             | 本期只要求多人可见性与冲突提示，不要求实时共享光标                                                                  |
| 内容刷新          | SSE 推送 + 乐观并发控制；禁止高频整页轮询                                                 | 对齐 NFR-0200，避免闪烁                                                                                             |
| Markdown 编辑模式 | **降级为双栏方案**：左侧源码编辑，右侧实时预览                                            | Typora 式单窗即时渲染在 Markdown 保真、`inline-discussion` 协议兼容、锚点稳定性上实现成本过高，不适合作为 v0.8 首版 |

> **Archer 裁决**：`FR-0900` 的优先方案原本是 Typora 式单窗，但经过实现复杂度评估，v0.8 采用“源码编辑 + 实时预览双栏”作为正式架构决策。原因不是体验偏好，而是为了确保 Markdown 与 `inline-discussion` 协议保真，不把首版做成高返工风险的富文本编辑器。

## 2. 部署拓扑

### 2.1 目标拓扑

```text
浏览器 A/B/...
    |
    | HTTP + SSE
    v
lk serve  (single ASGI process)
    |
    +-- 读写 .louke/project/specs/<spec_id>/*.md
    +-- 读写 .louke/wiki/pages/*.md
    +-- 读写 .louke/models.json
    +-- 追加 .louke/project/.serve-activity.jsonl
```

### 2.2 运行环境

- **服务运行平台**：macOS / Linux
- **默认运行方式**：在项目根目录执行 `lk serve`
- **默认访问范围**：
  - 开发时可监听 `127.0.0.1`
  - 团队共享时可监听内网地址并放在受信任网络内
- **不纳入 v0.8 的内容**：
  - 独立数据库
  - 外部对象存储
  - 内建 RBAC / SSO
  - 多实例横向扩容

### 2.3 安全假设

- v0.8 的安全边界是“团队内部工具”，不是公网 SaaS。
- 如果需要跨机器访问，推荐放在：
  - 内网机器
  - Tailscale / VPN 后面
  - 或已有企业反向代理 / SSO 后面
- 服务本身不承担公网暴露时的完整身份鉴别责任；这是明确的部署前提，而不是遗漏。

## 模块划分

| 模块              | 建议路径                 | 职责                                                             | 不负责         |
| ----------------- | ------------------------ | ---------------------------------------------------------------- | -------------- |
| Serve 入口        | `louke/serve.py`         | 注册 CLI、启动 ASGI、装配配置                                    | 业务解析逻辑   |
| Web App           | `louke/web/app.py`       | 路由、页面、API、SSE 装配                                        | 文件解析细节   |
| Project Store     | `louke/web/store.py`     | 定位 spec/wiki/models 文件路径，统一读写与版本令牌               | HTML 渲染      |
| Bindings Service  | `louke/web/bindings.py`  | 读取/保存模型绑定、合成 Agent/角色视图                           | 直接操作 DOM   |
| Documents Service | `louke/web/documents.py` | 设计文档与 wiki 的加载、保存、冲突检测                           | 浏览器交互     |
| Render Service    | `louke/web/render.py`    | Markdown → HTML、FR/NFR 卡片提取、`inline-discussion` 结构化渲染 | 文件持久化     |
| Activity / Events | `louke/web/events.py`    | SSE 推送、最近修改记录、更新提示                                 | 文档真相存储   |
| Static UI         | `louke/web/static/`      | 双栏编辑器、模型拖拽、切换/折叠、SSE 客户端                      | 服务端路径决策 |

### 3.1 模块依赖方向

```text
lk serve
  -> louke/serve.py
      -> louke/web/app.py
          -> louke/web/store.py
          -> louke/web/bindings.py
          -> louke/web/documents.py
          -> louke/web/render.py
          -> louke/web/events.py
          -> louke/web/static/*
```

依赖约束：

- `store.py` 是唯一直接理解 `.louke/` 路径布局与落盘规则的底层模块
- `bindings.py` / `documents.py` 只能通过 `store.py` 读写文件，不允许各自绕过 store 直接落盘
- `render.py` 不负责保存文件，只负责把 Markdown 转成可渲染结构和卡片 / discussion 衍生视图
- `events.py` 不生成业务状态，只消费“已成功提交的变更事件”并向 SSE 广播
- `static/` 只消费 `interfaces.md` 定义的页面与 API 出口，不假设 Python 内部对象结构

## 4. 核心数据与真相源

### 4.1 设计文档

| 文档            | 路径                                           |
| --------------- | ---------------------------------------------- |
| `spec.md`       | `.louke/project/specs/{spec_id}/spec.md`       |
| `acceptance.md` | `.louke/project/specs/{spec_id}/acceptance.md` |
| `test-plan.md`  | `.louke/project/specs/{spec_id}/test-plan.md`  |

### 4.2 wiki

| 对象         | 路径                      |
| ------------ | ------------------------- |
| wiki 页面    | `.louke/wiki/pages/*.md`  |
| wiki 索引    | `.louke/wiki/index.md`    |
| distill 缓存 | `.louke/wiki/.cache.toml` |

web server 只编辑 `pages/` 下页面，不改写 raw/distill 机制本身。

### 4.3 模型绑定

模型绑定继续复用 `.louke/models.json`，不另建第二套 web 专用配置文件。

采用如下职责分层：

- `aliases`: 继续表示“抽象模型名 -> provider/model”的解析映射
- `assignments.roles`: 角色级绑定，例如 `A` / `B` / `S`
- `assignments.agents`: Agent 级绑定，例如 `Sage` / `Archer` / `Lex`

v0.8 的角色命名空间与 Agent 归属关系在本 spec 中直接锁定如下，这张表就是实现期的**权威 roster**：

| 角色 | Agent                                                   |
| ---- | ------------------------------------------------------- |
| `S`  | `Judge`                                                 |
| `A`  | `Maestro`, `Sage`, `Archer`, `Devon`, `Prism`, `Shield` |
| `B`  | `Lex`, `Warden`, `Keeper`, `Scout`, `Librarian`         |

补充约束：

- `Archer` 在 README 中有 “S/A” 能力描述，但在 v0.8 的运行时角色绑定语义里固定归入 `A`
- 如果某个 Agent 需要突破角色默认绑定，必须通过 `assignments.agents` 显式覆盖，而不是临时扩展角色集合
- v0.8 不允许实现阶段再发明 `A/B/S` 之外的第四类角色

解析优先级：

1. Agent 级绑定
2. 角色级绑定
3. Agent frontmatter 中的默认 `models`
4. `aliases` 将抽象模型名解析到具体 `provider/model`

> **共享语义决定**：web UI 只读写项目级 `.louke/models.json`，不写 `~/.louke/models.json`。原因是当前 story 面向“团队内多人协作”，必须保证浏览器里看到的是团队共享配置，而不是某个人的本机私有覆盖。

### 4.4 协作元数据

为满足 `FR-0800` 的“谁最后修改了内容 / 当前内容是否已更新”要求，本期引入**非业务真相** sidecar：

- `.louke/project/.serve-activity.jsonl`

它只记录协作提示事件，例如：

- 谁保存了哪个文档
- 谁改了模型绑定
- 发生了哪次版本冲突

该文件不是业务真相源，不参与 louke 文档协议解析；即使删除，也不会破坏 spec/wiki/models 的有效内容。

### 4.5 `version_token` 生成语义

`version_token` 对外是 opaque string，但在架构层必须满足以下行为：

- 对每个可编辑目标独立生成，不能跨文档 / wiki / models 共用一个全局 token
- 读取后立即可用于一次保存尝试
- 只要底层文件内容变化，旧 token 就必须失效
- token 的生成输入至少覆盖“目标路径 + 文件内容摘要”；不能只靠时间戳，避免某些文件系统精度不足导致误判

推荐实现：

- 使用 `sha256(path + "\n" + body_md)` 或等价稳定摘要
- 对 `.louke/models.json` 先做稳定 JSON 序列化，再计算摘要，避免字段顺序造成伪冲突

## 5. 关键交互设计

### 5.1 文档编辑工作台

采用 **双栏布局**：

- 左栏：Markdown 源码编辑器
- 右栏：实时预览

右栏承担三类额外职责：

- 渲染 Markdown 结构（代码块 / 表格 / 列表）
- 将 `inline-discussion` 以接近原文位置的线程形式显示
- 提供 FR / NFR 卡片视图和原文跳转

### 5.2 为什么不做 Typora 单窗

Typora 式单窗即时渲染编辑在本项目里有三个高风险点：

1. Markdown 源文本必须保真，不能被富文本层“修正”到和原文不一致
2. `inline-discussion` 是 louke 自定义协议，不是通用 Markdown AST 的现成节点
3. FR / NFR 卡片、锚点、编号都依赖稳定源码结构，富文本编辑很容易引入不可见漂移

因此 v0.8 选择更保守、可验证、可回归的双栏方案。

### 5.3 discussion 交互

讨论不是独立聊天面板，而是预览区的 inline thread。

支持：

- 默认弱化显示
- “看正文 / 看讨论”切换
- 折叠 / 展开线程
- 在当前上下文位置发起 / 回复讨论

不支持：

- 实时共享光标
- 逐字符协同编辑
- 独立 IM 式聊天流

### 5.4 模型绑定画布交互

模型绑定页采用三栏信息组织：

- 左栏：可拖拽模型列表（展示 abstract model 与解析后的 full model）
- 中栏：角色绑定区（`A` / `B` / `S`）
- 右栏：Agent 绑定区（按 roster 固定顺序展示 12 个 Agent）

可观察交互约束：

- 拖到角色卡片上表示写 `assignments.roles`
- 拖到 Agent 卡片上表示写 `assignments.agents`
- Agent 卡片必须显示当前生效来源：`agent override` / `role default` / `agent default`
- 已有显式绑定的目标必须提供“清除覆盖”入口；清除 Agent 覆盖后回退到角色绑定或 frontmatter 默认值
- 绑定成功后仅局部更新受影响卡片，不重绘整页

该页面的关键不是画布美术效果，而是把“覆盖优先级”展示清楚，避免用户误把角色默认值看成 Agent 显式绑定。

### 5.5 编辑器页面状态机

文档页与 wiki 页共享同一套页面级状态机：

```text
idle
  -> editing      (用户修改源码)
  -> remote-stale (收到别人更新事件且本地未改)

editing
  -> previewing   (debounce 后请求 /api/render)
  -> saving       (用户点击保存)
  -> conflict     (保存返回 409)

previewing
  -> editing      (继续输入)
  -> saving

saving
  -> idle         (保存成功并回写新 version_token)
  -> conflict
  -> error

remote-stale
  -> idle         (用户接受刷新)
  -> editing      (用户开始本地修改，后续保存时自行承担冲突检查)

conflict
  -> idle         (用户放弃本地草稿并重载)
  -> editing      (用户保留本地草稿继续处理)
```

关键约束：

- “远端有新版本”与“本地存在未保存修改”必须同时可见，不能用自动刷新吞掉本地草稿
- 预览刷新是 `editing` 的派生效果，不得把用户焦点从源码区抢走
- `409 Conflict` 后默认保留本地草稿，并提供“重新加载远端版本”和“稍后手工合并”两条路径

## 6. 协作与一致性策略

### 6.1 并发模型

本期采用 **乐观并发控制**，不是悲观锁。

每次读取文档或绑定配置时，服务端返回一个 `version_token`。

每次保存时，客户端必须回传该 token：

- 若 token 一致：保存成功
- 若 token 过期：返回 `409 Conflict`

### 6.2 更新传播

为避免轮询闪烁，服务端通过 SSE 推送以下事件：

- `document.updated`
- `wiki.updated`
- `bindings.updated`
- `conflict.detected`

客户端收到事件后只更新局部状态和提示条，不刷新整页。

### 6.3 身份标识

v0.8 不做完整登录系统，但为了显示“谁改了内容”，浏览器首次进入时要求输入一个 display name，并保存在本地浏览器中，后续写请求携带该名称。

这不是安全身份认证，只是团队内协作标识。

### 6.4 写入时序

所有可编辑对象遵循一致的写入序列：

```text
客户端提交 body + version_token + actor_name
  -> 服务端读取当前真相源
  -> 校验 token 是否仍匹配
  -> 生成目标文件新内容
  -> 原子写入目标文件
  -> 追加 .serve-activity.jsonl
  -> 生成新的 version_token
  -> 广播 SSE 事件
  -> 返回 200 + 新 token
```

顺序约束：

- 必须先完成目标文件落盘，再写 `.serve-activity.jsonl`，避免“提示已更新但正文没落盘”
- 必须在落盘成功后才推 SSE，避免客户端收到幽灵更新
- 若 sidecar 追加失败，不得回滚业务文件；应记录错误并继续返回业务成功，同时在日志中暴露 sidecar 故障

### 6.5 预览渲染策略

为了兼顾体验与实现复杂度，预览采用“本地输入驱动、服务端统一解释”的模式：

- 输入区变化后由前端 debounce 触发 `POST /api/render`
- 预览区只替换渲染容器，不重建整个页面
- 渲染请求不写文件、不写 activity、不发 SSE
- 若连续输入导致旧渲染响应晚于新响应返回，客户端按请求序号丢弃过期响应

这保证双栏预览使用与最终落盘同一套解释逻辑，同时避免逐字符广播带来的闪烁和无谓负载

## 7. 技术选型

| 主题             | 选型                                        | 决策 |
| ---------------- | ------------------------------------------- | ---- |
| Web 服务         | `Starlette` + `uvicorn`                     | 采用 |
| 页面组织         | 服务端模板 + 原生 ES modules + 少量局部增强 | 采用 |
| 编辑器模式       | 源码编辑 + 右侧预览                         | 采用 |
| Markdown 渲染    | 服务端统一渲染                              | 采用 |
| 讨论协议渲染     | 在服务端解析后输出结构化 HTML               | 采用 |
| 页面更新         | SSE                                         | 采用 |
| 拖拽绑定         | 原生 Drag and Drop API                      | 采用 |
| 数据存储         | 仓库文件系统                                | 采用 |
| 数据库           | 不引入                                      | 否决 |
| WebSocket        | 首版不引入                                  | 否决 |
| SPA + 前端构建链 | 首版不引入 React/Vite 级复杂链路            | 否决 |

### 7.1 为什么是 Starlette

- louke 当前主体是 Python CLI，接入 ASGI 成本最低
- 足够承载页面、JSON API、SSE
- 不强迫项目引入前后端双语言构建体系

### 7.2 为什么服务端统一渲染 Markdown

- 可以让 web 与 CLI 共用同一套协议解释逻辑
- 更容易处理 `inline-discussion` 这样的 louke 私有语法
- 可以减少“前端预览正常、落盘后协议坏了”的双实现漂移

### 7.3 为什么首版不引入 React/Vite

- 当前目标是闭合 louke 工作流，不是建设长期演进的前端平台层
- 双栏编辑、局部刷新、拖拽和 SSE 在原生 ES modules 下足以实现
- 首版若引入前端构建链，会同时增加包管理、构建产物、测试基建和部署复杂度
- 等协作语义稳定后，如后续确有复杂组件需求，再迁移到更重的前端栈，成本更可控

## 8. 关键 trade-off

### 8.1 双栏 vs 单窗

| 维度                         | 双栏（采用） | 单窗 Typora 式（否决）   |
| ---------------------------- | ------------ | ------------------------ |
| Markdown 保真                | 高           | 中，需解决富文本回写漂移 |
| `inline-discussion` 协议兼容 | 高           | 低到中，需自定义复杂节点 |
| 首版落地风险                 | 低           | 高                       |
| 返工概率                     | 低           | 高                       |

### 8.2 SSE vs 轮询

| 维度         | SSE（采用） | 高频轮询（否决） |
| ------------ | ----------- | ---------------- |
| 闪烁风险     | 低          | 高               |
| 服务复杂度   | 中          | 低               |
| 多人协作提示 | 好          | 一般             |

### 8.3 文件系统 vs 数据库

| 维度                    | 文件系统（采用） | 数据库（否决） |
| ----------------------- | ---------------- | -------------- |
| 与现有 louke 工作流兼容 | 高               | 低             |
| 引入成本                | 低               | 高             |
| Markdown 真相源一致性   | 高               | 中             |

## 9. 风险与缓解

| 风险                                       | 缓解                                                           |
| ------------------------------------------ | -------------------------------------------------------------- |
| 双栏体验不如 Typora 流畅                   | 用预览侧的原文定位、discussion 就地操作、FR/NFR 卡片跳转来弥补 |
| 多人同时编辑时冲突频繁                     | 采用 `version_token` + 409 冲突提示 + SSE 更新提示             |
| 无内建鉴权带来部署风险                     | 明确仅面向内网 / VPN / 反向代理后的受控环境                    |
| 服务端渲染压力过大                         | 预览渲染按 debounce 触发，不做逐字符全量广播                   |
| `.louke/models.json` schema 演进影响旧 CLI | 保持 `aliases` 兼容；新增内容放入已预留的 `assignments` 下     |

## 10. 与 interfaces.md 的闭合

`interfaces.md` 需要对以下外部可观测契约给出确定出口：

- `lk serve` 的 CLI 启动契约
- `/health` 与页面 / API / SSE 路由
- `.louke/models.json` 的共享绑定 schema
- `A/B/S` 角色 roster 的权威来源
- 设计文档与 wiki 的加载 / 保存 / 冲突契约
- 协作元数据与更新提示事件

test-plan 中要求验证的“启动、保存、冲突、刷新、多人可见性”都必须只通过这些外部出口断言，而不是窥探内部对象。

### 10.1 architecture -> interfaces 映射

| architecture 决策     | interfaces 出口                                 |
| --------------------- | ----------------------------------------------- |
| 单进程 `lk serve`     | `lk serve` + `GET /health`                      |
| 双栏文档工作台        | `GET /docs/{spec_id}/{doc_name}` 的最低 UI 契约 |
| wiki 双栏编辑         | `GET /wiki/{page}` 的最低 UI 契约               |
| 角色 / Agent 双层绑定 | `GET/PUT /api/bindings` + `.louke/models.json`  |
| 服务端统一渲染        | `POST /api/render`                              |
| discussion 线程写回   | `POST /api/discussions/mutate`                  |
| 乐观并发 + 冲突提示   | `version_token` + `409 Conflict`                |
| 协作更新传播          | `GET /api/events` + `.serve-activity.jsonl`     |

### 10.2 implementation slices

建议实现顺序如下：

1. `lk serve`、`/health`、首页路由、静态资源装配
2. `store.py` + 文档 / wiki 读取与保存 + `version_token`
3. `render.py` + 双栏预览闭合 + Markdown / discussion 渲染
4. `bindings.py` + `.louke/models.json` 双层绑定读写
5. `events.py` + `.serve-activity.jsonl` + SSE 提示
6. 浏览器端交互增强：拖拽、正文/讨论切换、冲突提示、卡片跳转

原因：

- 先闭合最小 web 壳和文件读写，能尽快验证“真实服务 + 真实持久化”底线
- 再叠加渲染、绑定与协作提示，降低多人协作功能把基础 I/O 问题掩盖掉的风险
