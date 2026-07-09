# v0.8-001 — Web Server 协作界面 — Interfaces

- **Spec ID**: v0.8-001-web-server
- **创建日期**: 2026-07-08
- **关联**: `spec.md` / `acceptance.md` / `architecture.md` / `test-plan.md`

> 本文件是 v0.8 web server 的**外部可观测契约**唯一源。测试只能依赖这里声明的 CLI / HTTP / 文件出口，不得依赖内部对象、私有函数或前端组件内部状态。

---

## 1. CLI 入口契约

### 1.1 `lk serve`

| 项 | 值 |
| --- | --- |
| 子命令路径 | `serve` |
| 默认工作目录 | 当前项目根目录 |
| flags | `--host`、`--port`、`--project-root` |
| 成功退出码 | 长驻进程；正常启动后保持运行 |
| 失败退出码 | 非 0 |
| stdout | 打印监听地址、项目根路径、当前 spec_id |
| stderr | 启动失败原因（项目未初始化、端口占用、缺少 `.louke/` 等） |

**契约要求**：

- `lk serve` 启动后必须提供健康检查端点
- 默认读取当前项目根目录下的 `.louke/`
- `--project-root` 可显式指向另一个 louke 项目目录

### 1.2 健康检查

`GET /health`

| 项 | 值 |
| --- | --- |
| 返回码 | `200 OK` |
| 内容类型 | `application/json` |
| 最小返回体 | `{"status":"ok","spec_id":"v0.8-001-web-server"}` |

---

## 2. 页面路由契约

### 2.1 顶层页面

| 路径 | 含义 | 最低可观测要求 |
| --- | --- | --- |
| `GET /` | 工作台首页 | 同时出现“模型绑定”、“wiki”、“设计文档”三个入口 |
| `GET /models` | 模型绑定页面 | 可见模型列表、角色绑定区、Agent 绑定区 |
| `GET /wiki` | wiki 列表页 | 可见 wiki 页面列表 |
| `GET /wiki/{page}` | wiki 详情页 | 可阅读与编辑页面 |
| `GET /docs/{spec_id}/{doc_name}` | 设计文档页 | `doc_name ∈ {spec, acceptance, test-plan}` |

### 2.2 文档页最低 UI 契约

`GET /docs/{spec_id}/{doc_name}` 返回的 HTML 页面必须同时包含：

- 源码编辑区域
- 实时预览区域
- discussion 显示控制（至少含“看正文 / 看讨论”切换）
- discussion 折叠入口
- FR / NFR 卡片视图入口（`spec` 页面）

### 2.3 wiki 页最低 UI 契约

`GET /wiki/{page}` 返回的 HTML 页面必须同时包含：

- Markdown 编辑区域
- 实时预览区域
- 保存入口
- 最近修改提示区域

---

## 3. HTTP API 契约

## 3.1 会话身份

所有写请求必须携带 `actor_name`，可通过请求头 `X-Louke-Actor` 或 JSON body 字段提交。

用途：

- 写入 `.serve-activity.jsonl`
- 在 UI 中显示“最后修改者”

未携带时：

- 返回 `400 Bad Request`

### 3.2 模型绑定

v0.8 的抽象角色集合固定为 `A` / `B` / `S`，其 Agent roster 以本文件为权威来源：

| 角色 | Agent |
| --- | --- |
| `S` | `Judge` |
| `A` | `Maestro`, `Sage`, `Archer`, `Devon`, `Prism`, `Shield` |
| `B` | `Lex`, `Warden`, `Keeper`, `Scout`, `Librarian` |

补充语义：

- `Archer` 的运行时角色固定视为 `A`
- 角色绑定只允许上述 3 个 key
- Agent 绑定只允许上述 12 个 Agent 名称
- UI 和服务端都不得从 README prose 或 agent prompt 的自然语言描述推断角色归属

#### `GET /api/bindings`

返回：

```json
{
  "version_token": "opaque-string",
  "aliases": {
    "minimax-m3": "ark/minimax-m3"
  },
  "assignments": {
    "roles": {
      "A": "minimax-m3"
    },
    "agents": {
      "Sage": "glm-5.2"
    }
  },
  "resolved": {
    "roles": {
      "A": {
        "abstract": "minimax-m3",
        "full": "ark/minimax-m3"
      }
    },
    "agents": {
      "Sage": {
        "source": "agent",
        "abstract": "glm-5.2",
        "full": "provider/glm-5.2"
      },
      "Lex": {
        "source": "role",
        "role": "B",
        "abstract": "deepseek-v4-flash",
        "full": "provider/deepseek-v4-flash"
      }
    }
  }
}
```

最低语义要求：

- 同时返回角色绑定、Agent 绑定、解析后的最终视图
- 能区分 `source ∈ {agent, role, default}`
- `version_token` 用于后续保存

#### `PUT /api/bindings`

请求：

```json
{
  "version_token": "opaque-string",
  "aliases": {},
  "assignments": {
    "roles": {},
    "agents": {}
  },
  "actor_name": "Aaron"
}
```

返回：

- `200 OK`：保存成功并返回新的 `version_token`
- `409 Conflict`：版本过期

副作用：

- 写 `.louke/models.json`
- 追加 `.louke/project/.serve-activity.jsonl`
- 推送 `bindings.updated`

### 3.3 wiki

#### `GET /api/wiki`

返回 wiki 页面列表：

```json
{
  "pages": [
    {
      "page": "current-api",
      "path": ".louke/wiki/pages/current-api.md",
      "updated_at": "2026-07-08T20:00:00Z",
      "last_modified_by": "Aaron"
    }
  ]
}
```

#### `GET /api/wiki/{page}`

返回：

```json
{
  "page": "current-api",
  "path": ".louke/wiki/pages/current-api.md",
  "body_md": "# title\n...",
  "rendered_html": "<h1>title</h1>",
  "version_token": "opaque-string",
  "updated_at": "2026-07-08T20:00:00Z",
  "last_modified_by": "Aaron"
}
```

#### `PUT /api/wiki/{page}`

请求：

```json
{
  "body_md": "# title\n...",
  "version_token": "opaque-string",
  "actor_name": "Aaron"
}
```

返回：

- `200 OK`：保存成功
- `409 Conflict`：版本过期

副作用：

- 写 `.louke/wiki/pages/{page}.md`
- 追加 `.serve-activity.jsonl`
- 推送 `wiki.updated`

### 3.4 设计文档

#### `GET /api/docs/{spec_id}/{doc_name}`

其中：

- `spec_id` 例如 `v0.8-001-web-server`
- `doc_name ∈ {spec, acceptance, test-plan}`

返回：

```json
{
  "spec_id": "v0.8-001-web-server",
  "doc_name": "spec",
  "path": ".louke/project/specs/v0.8-001-web-server/spec.md",
  "body_md": "# ...",
  "rendered_html": "<h1>...</h1>",
  "version_token": "opaque-string",
  "updated_at": "2026-07-08T20:00:00Z",
  "last_modified_by": "Aaron",
  "cards": [
    {
      "id": "FR-0100",
      "kind": "FR",
      "title": "团队内多人可访问的 web server 工作台",
      "valid": true,
      "testable": true,
      "decided": true,
      "summary": "..."
    }
  ]
}
```

**契约要求**：

- `spec` 页必须返回 `cards`
- `acceptance` / `test-plan` 可返回空数组
- `rendered_html` 必须保留代码块、表格、列表结构

#### `PUT /api/docs/{spec_id}/{doc_name}`

请求：

```json
{
  "body_md": "# ...",
  "version_token": "opaque-string",
  "actor_name": "Aaron"
}
```

返回：

- `200 OK`
- `409 Conflict`

副作用：

- 写目标 Markdown 文件
- 追加 `.serve-activity.jsonl`
- 推送 `document.updated`

### 3.5 预览渲染

#### `POST /api/render`

请求：

```json
{
  "kind": "doc",
  "doc_name": "spec",
  "body_md": "# ..."
}
```

返回：

```json
{
  "rendered_html": "<h1>...</h1>",
  "cards": [],
  "discussion_threads": []
}
```

用途：

- 给双栏预览提供服务端统一渲染结果
- 保证前端预览与落盘后解析使用同一解释逻辑

### 3.6 discussion 动作

#### `POST /api/discussions/mutate`

请求：

```json
{
  "target_kind": "doc",
  "target_path": ".louke/project/specs/v0.8-001-web-server/spec.md",
  "version_token": "opaque-string",
  "actor_name": "Aaron",
  "action": "reply",
  "anchor": {
    "section_id": "fr-0100"
  },
  "payload": {
    "body": "建议补一条降级策略"
  }
}
```

语义要求：

- 服务端负责把动作转换为合法的 `inline-discussion` Markdown
- 客户端不需要手写协议文本拼接
- 保存结果仍然是原始 Markdown 文件

返回：

- `200 OK`：返回新 `body_md`、`rendered_html`、`version_token`
- `409 Conflict`：版本过期
- `422 Unprocessable Entity`：无法在目标上下文合法插入 discussion

### 3.7 事件流

#### `GET /api/events`

返回：

- `200 OK`
- `Content-Type: text/event-stream`

事件类型：

| event | data 最低字段 |
| --- | --- |
| `document.updated` | `target`, `updated_at`, `actor_name` |
| `wiki.updated` | `target`, `updated_at`, `actor_name` |
| `bindings.updated` | `updated_at`, `actor_name` |
| `conflict.detected` | `target`, `actor_name`, `updated_at` |

客户端最低行为要求：

- 收到事件后只更新局部提示，不整页刷新

---

## 4. 文件 schema 契约

### 4.1 `.louke/models.json`

沿用现有 schema 标识：

```json
{
  "$schema": "louke://models-config",
  "version": 1,
  "aliases": {},
  "assignments": {
    "roles": {},
    "agents": {}
  }
}
```

约束：

- `aliases`：`{abstract_model: full_model}`
- `assignments.roles`：`{role_name: abstract_model}`，其中 `role_name ∈ {"A","B","S"}`
- `assignments.agents`：`{agent_name: abstract_model}`，其中 `agent_name` 只能取上文 roster 中的 12 个 Agent
- web UI 只写项目级 `.louke/models.json`
- `assignments.roles` / `assignments.agents` 的语义以本文件 §3.2 的 roster 为准

### 4.2 设计文档文件

| 目标 | 路径模式 |
| --- | --- |
| spec | `.louke/project/specs/{spec_id}/spec.md` |
| acceptance | `.louke/project/specs/{spec_id}/acceptance.md` |
| test-plan | `.louke/project/specs/{spec_id}/test-plan.md` |

要求：

- 服务端保存后不得破坏标题层级、锚点、FR/NFR 编号、表格结构

### 4.3 wiki 页面文件

| 目标 | 路径模式 |
| --- | --- |
| wiki 页面 | `.louke/wiki/pages/{page}.md` |

要求：

- 服务端保存后页面仍可被 `lk agent librarian lint` / `rebuild-index` 读取

### 4.4 协作 sidecar

`.louke/project/.serve-activity.jsonl`

每行 1 个 JSON 事件，例如：

```json
{
  "type": "document.updated",
  "target": ".louke/project/specs/v0.8-001-web-server/spec.md",
  "actor_name": "Aaron",
  "updated_at": "2026-07-08T20:00:00Z"
}
```

约束：

- 只作为协作提示来源
- 不是业务真相源
- 即使缺失，也不能导致文档 / wiki / 绑定文件损坏

---

## 5. 并发与错误契约

### 5.1 `version_token`

`version_token` 是服务端返回的 opaque string，用于检测“我编辑的是不是旧版本”。

它的内部生成方式不是接口契约的一部分，但外部行为必须满足：

- 读取后得到 token
- 保存时必须带回 token
- 若文件在此期间被别人改过，则 token 失效并返回 `409`

### 5.2 错误码

| 场景 | 状态码 |
| --- | --- |
| 正常读取 | `200` |
| 创建成功（如后续新增显式 create 路由） | `201` |
| 参数缺失 / `actor_name` 缺失 | `400` |
| 目标不存在 | `404` |
| 版本冲突 | `409` |
| discussion 插入位置非法 | `422` |
| 未处理异常 | `500` |

---

## 6. 与 test-plan 的闭合

| test-plan 关注点 | 对应接口出口 |
| --- | --- |
| 服务启动 / 健康检查 | `lk serve` + `GET /health` |
| 模型绑定读取 / 保存 | `GET/PUT /api/bindings` + `.louke/models.json` |
| wiki 阅读 / 编辑 | `GET/PUT /api/wiki*` + `.louke/wiki/pages/*.md` |
| 文档阅读 / 编辑 | `GET/PUT /api/docs*` + spec 目录下 Markdown |
| Markdown 渲染保真 | `POST /api/render` |
| discussion 写回 | `POST /api/discussions/mutate` + 文档文件结果 |
| 多人可见性 / 冲突提示 | `GET /api/events` + `409 Conflict` + `.serve-activity.jsonl` |

闭合要求：

- test 只能断言这些外部出口
- 不允许通过直接 import 私有 Python 模块内部状态完成验收
