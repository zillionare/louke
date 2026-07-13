---
locked: true
locked-at: 2026-07-12T05:50:34Z
locked-by: lk agent sage record-lock
---
# Louke Web IDE — Web UI 集成 (v0.11-001 补漏) — Spec

- **Spec ID**: v0.11-002-web-ui-integration
- **Created**: 2026-07-12
- **Status**: Draft
- **Priority**: P0

> 本文只补齐 v0.11-001 已锁定需求的 Web UI 集成缺口；可观察、可断言的通过条件见 `acceptance.md`。

## Story

作为 Louke 内部使用者，我希望既有 Web 页面连接 v0.11-001 已交付的六个 sub-app，并能通过浏览器完成关键操作，以便 Web IDE 不再只展示静态或 mock 页面，而是真正使用已锁定的 API 能力。

> **Aaron:** 哪6个？

## Decided

- Web UI 集成范围为：在 `louke/web/app.py` mount 六个 sub-app、为既有页面增加 JavaScript client、升级 Playwright e2e。
- 复用 v0.11-001 已实现的 `opencode`、`intent`、`wiki`、`backlog`、`files`、`tasks` 六个 sub-app；不改变其内部逻辑，只接入主 Web app。
- 复用 v0.10 的 home、wiki、models、docs、login 页面模板；相关数据与操作改为通过 JavaScript 调用真实 API，不使用页面 mock 数据。
- NFR-0101 的浏览器验证在本补漏 spec 中升级为实际点击、填写表单和页面状态断言，而非只 GET 静态页面。
- 测试分为两层：v0.11-001 已有 API e2e 与本期新增 UI e2e；两层分别验证接口契约和浏览器用户流。

## Usage Scenarios

- 用户从 Web 导航进入功能页，创建或选择数据、提交操作，并在页面看到来自真实 API 的结果。
- 用户刷新页面后，重新读取 API 数据并看到已持久化的 backlog、文档或 task 状态。

## Functional Requirements

### FR-0202 Web UI 路由与导航


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅    | ✅       | ✅      |

- `louke/web/app.py` 必须接入六个 sub-app，使 v0.11-001 `interfaces.md` 锁定的 `/api/opencode`、`/api/intent`、`/api/wiki`、`/api/backlog`、`/api/files`、`/api/tasks` 公共端点可由同一 Web server 访问。
- 既有 home（`/`）、wiki（`/wiki`）、models（`/models`）和 docs（`/docs/...`）页面及其功能导航必须可访问，并通过 JavaScript client 调用对应真实 API。
- 页面不得以硬编码或 mock 数据伪造成功结果；API 失败时必须显示可观察的失败反馈。
- 验收引用：AC-FR0202-01 至 AC-FR0202-04。

---

### FR-0203 OpenCode Web 交互


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅    | ✅       | ✅      |

- home 页面必须允许用户创建实例、选择实例、向选中实例发送消息并看到该实例的消息与状态回显。
- 页面实例列表和消息结果必须来自已接入的 OpenCode API；切换实例不得混淆会话输出。
- 验收引用：AC-FR0203-01 至 AC-FR0203-04。

---

### FR-0204 Backlog Web 交互


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅    | ✅       | ✅      |

- backlog 页面必须允许用户填写并提交 story、查看 API 返回的 backlog 列表、选择条目并触发“进入开发”。
- 未选择条目时不得启动开发，并须显示可观察反馈；成功进入开发的条目须从页面列表移除。
- 验收引用：AC-FR0204-01 至 AC-FR0204-03。

---

### FR-0205 Files Web 交互


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅    | ✅       | ✅      |

- files 页面必须通过 Files API 展示工作区树、Git 变更列表和选中变更的 diff。
- 用户必须能打开允许编辑的设计文档、修改并保存；刷新或重新打开后显示已持久化内容。
- v0.11-001 锁定的只读、二进制、500 行批准和 workspace 边界规则继续适用，不在本 spec 改写。
- 验收引用：AC-FR0205-01 至 AC-FR0205-04。

---

### FR-0206 Tasks Web 交互


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅    | ✅       | ✅      |

- docs 页面必须显示所选 FR/NFR 的 `Valid`、`Testable`、`Decided` 三个 task checkbox，并通过 Tasks API 分别切换。
- 切换只能改变目标 task；页面重新加载后必须显示持久化状态。
- 验收引用：AC-FR0206-01 至 AC-FR0206-03。

---

## Non-Functional Requirements

### NFR-0102 Playwright 真 UI e2e


| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅    | ✅       | ✅      |

- Playwright 必须通过真实浏览器的导航、点击、表单填写及页面状态断言覆盖 FR-0203 至 FR-0206 的关键成功路径，不得以直接调用 API 代替 UI 操作。
- UI e2e 必须与既有 API e2e 分层保留，并至少在 v0.11-001 NFR-0101 已承诺的 Chromium 与 Firefox 中执行。
- 验收引用：AC-NFR0102-01 至 AC-NFR0102-05。

---

## Known Constraints and Exclusions

- v0.11-001 的 spec、acceptance、interfaces、architecture、test-plan 均已锁定，本 spec 不修改其内容或 37 个 AC。
- FR-0101 Louke Server Agent 工具化（#99）不在本期，继续延后至后续 spec。
- 六个 sub-app 的业务逻辑和既有接口契约不在本期修改范围；本期只负责主 app 接入与 Web UI 消费。
- 本期不重设计 v0.10 页面模板，也不新增 v0.11-001 未定义的服务能力。

## Clarification Log

- 2026-07-12：用户明确本 spec 为 v0.11-001 的补漏，范围限定为六个 sub-app 接入、真实 Web UI 用户流与 Playwright 真点击验证。
