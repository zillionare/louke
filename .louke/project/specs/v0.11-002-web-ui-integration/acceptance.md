# Louke Web IDE — Web UI 集成 (v0.11-001 补漏) — Acceptance Criteria

- **Spec ID**: v0.11-002-web-ui-integration
- **Created**: 2026-07-12
- **Status**: Draft

> 每项均采用 Given / When / Then 表述，并可由 Playwright UI e2e 或既有 API e2e 自动化断言。

## FR-0202 Web UI 路由与导航

### AC-1
AC-FR0202-01
- **Given** Louke Web server 已启动，**When** 分别通过同一 server 请求六类已锁定 API 的代表端点，**Then** `/api/opencode`、`/api/intent`、`/api/wiki`、`/api/backlog`、`/api/files`、`/api/tasks` 均由对应 sub-app 处理，而非返回主页面 404。

### AC-2
AC-FR0202-02
- **Given** 用户已打开 Web UI，**When** 通过页面导航访问 home、wiki、models 和 docs，**Then** 每个目标页面可访问，且导航后 URL 与所选功能一致。

### AC-3
AC-FR0202-03
- **Given** 对应 API 返回可识别的 fixture 数据，**When** 用户打开相关页面或触发加载，**Then** 页面显示该 API 数据，且不显示预置 mock 数据替代响应。

### AC-4
AC-FR0202-04
- **Given** 对应 API 返回明确错误，**When** 用户从页面触发该请求，**Then** 页面显示失败反馈且不显示成功状态。

## FR-0203 OpenCode Web 交互

### AC-1
AC-FR0203-01
- **Given** home 页面可访问且没有运行实例，**When** 用户点击创建实例按钮，**Then** 页面出现由 OpenCode API 返回的唯一实例标识和可观察运行状态。

### AC-2
AC-FR0203-02
- **Given** 页面存在两个实例，**When** 用户点击选择其中一个，填写消息并点击发送，**Then** 请求关联到选中实例，页面显示该实例的消息和状态回显。

### AC-3
AC-FR0203-03
- **Given** 两个实例各有不同会话输出，**When** 用户在页面切换所选实例，**Then** 消息区域只显示当前实例的输出，不显示另一实例的输出。

### AC-4
AC-FR0203-04
- **Given** 一个已停止或不可用实例，**When** 用户填写消息并点击发送，**Then** 页面显示发送失败状态，且不把消息显示为成功执行。

## FR-0204 Backlog Web 交互

### AC-1
AC-FR0204-01
- **Given** backlog 页面可访问，**When** 用户填写有效 story 并点击提交，**Then** 页面列表显示由 Backlog API 持久化并返回的新条目。

### AC-2
AC-FR0204-02
- **Given** backlog 列表含多个条目，**When** 用户点击选中其中一项并点击进入开发，**Then** 仅该项被提交给开发流程，成功后从页面列表消失。

### AC-3
AC-FR0204-03
- **Given** 用户没有选中 backlog 条目，**When** 点击进入开发，**Then** 页面提示需先选择条目，列表保持不变且开发流程未启动。

## FR-0205 Files Web 交互

### AC-1
AC-FR0205-01
- **Given** workspace 含文件和 Git 变更，**When** 用户打开 files 页面并点击树视图与变更视图，**Then** 页面分别显示 Files API 返回的文件和变更条目。

### AC-2
AC-FR0205-02
- **Given** 变更列表中存在可查看项，**When** 用户点击该项的 diff 操作，**Then** 页面显示与所选路径对应的 diff 内容。

### AC-3
AC-FR0205-03
- **Given** 用户打开允许编辑的 `story.md`、`spec.md` 或 `acceptance.md`，**When** 修改内容并点击保存，**Then** 页面显示保存成功，重新打开该文档后内容与保存值一致。

### AC-4
AC-FR0205-04
- **Given** 用户打开只读源代码文件，**When** 尝试保存修改，**Then** 页面显示拒绝反馈，重新读取后文件内容未改变。

## FR-0206 Tasks Web 交互

### AC-1
AC-FR0206-01
- **Given** docs 页面已打开含 FR/NFR task 的文档，**When** 页面完成加载，**Then** 显示 `Valid`、`Testable`、`Decided` 三个可点击 checkbox，状态与 Tasks API 返回值一致。

### AC-2
AC-FR0206-02
- **Given** 三个 task 具有已知初始状态，**When** 用户点击其中一个 checkbox，**Then** 只有目标 task 的页面状态和 API 状态改变，另外两个保持不变。

### AC-3
AC-FR0206-03
- **Given** 用户已通过页面切换一个 task，**When** 重新加载 docs 页面，**Then** 三个 checkbox 显示持久化后的状态，目标 task 不恢复为旧值。

## NFR-0102 Playwright 真 UI e2e

### AC-1
AC-NFR0102-01
- **Given** Chromium 的 Playwright 环境和可控 OpenCode fixture，**When** 执行 OpenCode UI e2e，**Then** 测试通过页面点击创建与选择实例、填写并发送消息，并断言页面回显与状态。

### AC-2
AC-NFR0102-02
- **Given** Chromium 的 Playwright 环境和可控 backlog fixture，**When** 执行 backlog UI e2e，**Then** 测试通过页面填写 story、点击提交、选择条目并点击进入开发，并断言列表变化。

### AC-3
AC-NFR0102-03
- **Given** Chromium 的 Playwright 环境和包含变更及可编辑文档的 workspace fixture，**When** 执行 files UI e2e，**Then** 测试点击文件与 diff、填写文档并点击保存，并断言 diff 与重载后的内容。

### AC-4
AC-NFR0102-04
- **Given** Chromium 的 Playwright 环境和含三个 task 的文档 fixture，**When** 执行 tasks UI e2e，**Then** 测试点击目标 checkbox、重新加载页面，并断言目标状态持久化且其他状态不变。

### AC-5
AC-NFR0102-05
- **Given** Chromium 与 Firefox 测试环境，**When** 执行覆盖 FR-0203 至 FR-0206 的 Playwright UI e2e 集合，**Then** 两个浏览器均无失败；测试步骤包含页面导航、点击、表单填写和页面状态断言，且不以 API 请求替代关键 UI 操作。
