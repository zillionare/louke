# v0.14-004 Workspace Onboarding 与 Workflow Status 测试计划

## 1. 概述

### 1.1 目标

验证空白和既有 workspace 均能通过统一 Workbench shell 完成身份、Repository、依赖、Review/Apply，并在登录、刷新、服务重启、冲突或断线后解析到正确的 Setup/Current Work/Released/Ready 状态；同时验证 Workflow Status 与 Guide 只呈现 Runtime/program 的 canonical facts，不成为第二 authority。

计划覆盖 `acceptance.md` 的全部 43 项 AC、`interfaces.md` 的 IF-01 至 IF-15，以及兼容、安全、恢复、幂等、可访问和 CI/artifact 门禁。Acceptance 当前以 section anchor 加局部 `AC-1/AC-2` 表达；traceability gate 使用规范化 ID `AC-FRxxxx-yy` / `AC-NFRxxxx-yy`，例如 `ac-fr-0101` 下 `AC-2` 记作 `AC-FR0101-02`。

### 1.2 测试范围

**包含：**

- Workbench shell、首用户/Login、Entry Resolver 和稳定 Project/Story/Run 导航。
- 连续 Setup Wizard 的 init/clone 两个 Repository 分支、binding/provenance、依赖 Recheck、Review/Apply/Reconcile 和持久恢复。
- Ready/Empty、Current Work、Released 驾驶舱，Start Story Preview/Confirm 的有机入口。
- Workflow Status 全字段、新鲜度、合法动作和 Guide 挂载/偏好/解释/非干扰边界。
- stale、并发、重复提交、部分成功、结果不确定、权限、路径逃逸、秘密脱敏和旧 route/API 兼容。
- Python unit、安装态 integration、真实 Chromium e2e、真实 wheel/sdist 构建与安装验证、AC traceability 和 Louke CI required aggregation。

**不包含：**

- `v0.14-002` 的 M-DESIGN 领域逻辑和 `v0.14-003` 的 M-IMPL 至 M-MILESTONE 状态机内部正确性；本计划只验证其公开 projection/深链接线。
- 新的 release version、tag 或 publish 行为。本 Spec 不改变 artifact 身份；只回归既有 build/version gate。
- 视觉品牌、像素级布局和未承诺的小于支持范围的 viewport；仍验证接口规定的布局不遮挡和可访问语义。
- 真实第三方服务作为默认 PR 证据；默认使用可控 stand-in，protected/manual smoke 只作既有发布合同要求的补充，不能替代 required suite。

---

## 2. 测试策略

### 2.1 测试层级

| 层级 | 负责人 | 资产/入口 | 边界 |
|---|---|---|---|
| 单元测试 | Devon | 现有 unit 目录与 pytest unit 入口 | 纯 resolver/projection、URL 校验、revision/idempotency 决策、脱敏、layout preference 规则；使用固定时钟、临时目录和 adapter fake |
| 集成测试 | Shield | `tests/integration/v014_workspace_onboarding/`；`tests/e2e/run-project-venv integration` | 通过真实 HTTP/application/store 与受控 Git/provider adapter 接线验证 IF-01..IF-15；不得 mock 被断言的公开 HTTP 出口 |
| E2E 测试 | Shield | `tests/e2e/v014_workspace_onboarding/`；`tests/e2e/run-project-venv e2e --profile all --runtime both` | 安装 wheel、隔离 HOME/workspace、真实 Web server + Chromium，模拟主用户旅程、恢复、响应式/键盘和兼容深链 |

所有 `interfaces.md` 条目跨至少两个模块，因此均有 integration 覆盖。面向用户的主成功旅程及关键恢复旅程有 e2e；unit 不能替代 integration/e2e evidence。

### 2.2 AC → 接口 → 必需层 → CI 分配

缩写：`U`=unit、`I`=integration、`E`=e2e。`unit`、`integration`、`e2e-standin` 均为 `Louke CI` job；`T` 表示 `traceability` 同时校验映射。每行均为强制分配。

| Acceptance ID | 可观察接口 | 必需层 | CI gate/job | 分配理由 |
|---|---|---|---|---|
| AC-FR0001-01 | IF-01、IF-02、IF-03 | U+I+E | unit/integration/e2e-standin/T | resolver 优先级需纯边界验证；空白/既有 workspace 登录落点需浏览器证明 |
| AC-FR0001-02 | IF-01、IF-03 | U+I+E | unit/integration/e2e-standin/T | cookie/Guide 不改变事实；硬启动失败在公共启动出口验证 |
| AC-FR0101-01 | IF-04、IF-05、IF-06、IF-07 | U+I+E | unit/integration/e2e-standin/T | 连续步骤、失效传播和可见进度是主 Wizard 旅程 |
| AC-FR0101-02 | IF-04、IF-07、IF-11 | I+E | integration/e2e-standin/T | provenance、局部离开和 Story action 禁用必须经公开 UI/API |
| AC-FR0201-01 | IF-02、IF-03、IF-04 | U+I+E | unit/integration/e2e-standin/T | 唯一首用户、持久化和重启后连续性 |
| AC-FR0201-02 | IF-02、IF-12 | U+I+E | unit/integration/e2e-standin/T | 错误定位和 credential 不泄漏覆盖 projection、日志与页面 |
| AC-FR0301-01 | IF-04、IF-05 | U+I+E | unit/integration/e2e-standin/T | init/clone 是两个关键用户分支；Preview 必须零副作用 |
| AC-FR0301-02 | IF-05、IF-07、IF-12 | U+I+E | unit/integration/e2e-standin/T | 冲突/权限/不确定需真实文件 readback 和浏览器恢复出口 |
| AC-FR0401-01 | IF-04、IF-05 | U+I+E | unit/integration/e2e-standin/T | 候选/provenance 与 waiting Human 展示 |
| AC-FR0401-02 | IF-05、IF-07、IF-11 | U+I+E | unit/integration/e2e-standin/T | revision binding、真实 Git identity 与后续对象一致性 |
| AC-FR0501-01 | IF-04、IF-06 | U+I+E | unit/integration/e2e-standin/T | 多项 readiness 分离和 Review 阻断 |
| AC-FR0501-02 | IF-06、IF-12 | U+I+E | unit/integration/e2e-standin/T | Recheck 当前事实、placeholder 禁止和 token 脱敏 |
| AC-FR0601-01 | IF-04、IF-05、IF-07、IF-11 | U+I+E | unit/integration/e2e-standin/T | Review 的完整可见影响与零 release 副作用 |
| AC-FR0601-02 | IF-07、IF-12 | U+I+E | unit/integration/e2e-standin/T | auth、actor/revision evidence、stale 与并发幂等 |
| AC-FR0701-01 | IF-07、IF-12 | U+I+E | unit/integration/e2e-standin/T | operation 状态、重复 Apply 和不确定 readback |
| AC-FR0701-02 | IF-03、IF-04、IF-07、IF-11 | U+I+E | unit/integration/e2e-standin/T | Complete gate 与 Start Story 启用是 Wizard happy path 终点 |
| AC-FR0801-01 | IF-02、IF-04、IF-07 | U+I+E | unit/integration/e2e-standin/T | Confirm 前后浏览器/服务重启恢复是关键用户旅程 |
| AC-FR0801-02 | IF-03、IF-08、IF-11 | U+I+E | unit/integration/e2e-standin/T | manifest attention 与 Story delivery idempotent 恢复 |
| AC-FR0901-01 | IF-03、IF-11 | I+E | integration/e2e-standin/T | Ready/Empty 到 Story Preview 主成功旅程及零副作用 |
| AC-FR0901-02 | IF-08、IF-10、IF-11 | U+I+E | unit/integration/e2e-standin/T | Confirm、blocked recovery 与单 active container |
| AC-FR1001-01 | IF-03、IF-08、IF-11 | U+I+E | unit/integration/e2e-standin/T | 三种驾驶舱和对象链可见一致性 |
| AC-FR1001-02 | IF-01、IF-03、IF-11 | I+E | integration/e2e-standin/T | Released→Current Work、进入/返回不丢 context |
| AC-FR1101-01 | IF-08、IF-09 | U+I+E | unit/integration/e2e-standin/T | projection 全字段与禁止百分比需 API/UI 双层证明 |
| AC-FR1101-02 | IF-08、IF-10 | U+I+E | unit/integration/e2e-standin/T | attention 原因、单主动作、无动作等待责任方 |
| AC-FR1201-01 | IF-01、IF-08、IF-14 | I+E | integration/e2e-standin/T | 同 shell activities 与兼容深链对象一致性 |
| AC-FR1201-02 | IF-01、IF-14 | U+I+E | unit/integration/e2e-standin/T | bookmark/history 与安全 not-found/permission |
| AC-FR1301-01 | IF-01、IF-09、IF-13 | I+E | integration/e2e-standin/T | Guide 固定挂载和 activity context 是浏览器合同 |
| AC-FR1301-02 | IF-09、IF-13 | U+I+E | unit/integration/e2e-standin/T | 折叠/分隔/恢复、持久偏好和缩放可用性 |
| AC-FR1401-01 | IF-08、IF-09、IF-10 | U+I+E | unit/integration/e2e-standin/T | Guide 解释与 owning surface action 边界 |
| AC-FR1401-02 | IF-09、IF-13 | U+I+E | unit/integration/e2e-standin/T | 显著说明去重、焦点/输入非干扰、resolver 不变 |
| AC-FR1501-01 | IF-08、IF-09、IF-10 | U+I+E | unit/integration/e2e-standin/T | Maestro/Guide 不可 dispatch 和越权不改变 Runtime |
| AC-FR1501-02 | IF-01、IF-08、IF-09、IF-14 | I+E | integration/e2e-standin/T | 专业 Agent/Guide/历史会话在 UI 明确分界 |
| AC-NFR0001-01 | IF-04、IF-07、IF-10、IF-12 | U+I+E | unit/integration/e2e-standin/T | 各中断点恢复、同 revision at-most-once |
| AC-NFR0001-02 | IF-07、IF-08、IF-12 | U+I+E | unit/integration/e2e-standin/T | uncertain fail-closed 与 reconcile evidence |
| AC-NFR0101-01 | IF-02、IF-05、IF-07、IF-12 | U+I+E | unit/integration/e2e-standin/T | secret 扫描和授权前零副作用需多出口验证 |
| AC-NFR0101-02 | IF-05、IF-07、IF-12 | U+I | unit/integration/T | 路径范围/权限保护由临时文件与真实 adapter readback 证明 |
| AC-NFR0201-01 | IF-03、IF-08、IF-09、IF-14 | U+I+E | unit/integration/e2e-standin/T | 多 surface 同 revision 与旧缓存不可回退 |
| AC-NFR0201-02 | IF-08、IF-10、IF-14 | U+I+E | unit/integration/e2e-standin/T | identity/revision conflict 不产生平行状态并有恢复出口 |
| AC-NFR0301-01 | IF-01、IF-04、IF-09、IF-10、IF-13 | I+E | integration/e2e-standin/T | 键盘与支持 viewport/zoom 必须真实浏览器验证 |
| AC-NFR0301-02 | IF-09、IF-13 | I+E | integration/e2e-standin/T | 状态更新不抢焦点/丢输入与 live region |
| AC-NFR0401-01 | IF-03、IF-08、IF-11、IF-14 | U+I+E | unit/integration/e2e-standin/T | 历史 workspace 升级、旧协议单写权威 |
| AC-NFR0401-02 | IF-09、IF-14 | I+E | integration/e2e-standin/T | Maestro 历史只读/迁移态可见语义 |
| AC-NFR0501-01 | IF-04、IF-05、IF-07、IF-08、IF-09、IF-11、IF-12 | U+I+E | unit/integration/e2e-standin/T | 可操作诊断和无内部编排术语的端到端主路径 |

`traceability` gate 还必须证明 IF-01..IF-15 至少被一个 collected node id 覆盖；IF-15 由 CI contract integration 和 required aggregation 自测覆盖。

### 2.3 测试框架与依赖

- 测试框架：pytest、pytest-asyncio、现有 Starlette HTTP 测试支持和 Python Playwright；精确版本继承 `pyproject.toml` 当前 lock/constraints，不新增框架。
- Browser：CI 安装与当前 Playwright package 匹配的 Chromium；不得用系统随机版本。
- Git：测试 runner 的受支持 Git 版本；clone 使用 loopback HTTP remote 和无 credential 的 seed repository。
- 静态质量：ruff format/check 与 mypy，配置和版本以 `pyproject.toml` 为准。
- 构建：`python -m build` 真实产生 wheel/sdist；e2e 只能导入安装 wheel，不得从 checkout 源树导入。

### 2.4 Mock/Stub 策略

| 依赖 | unit | integration/e2e-standin | 禁止做法 |
|---|---|---|---|
| 时钟 | fixed fake clock | runner-controlled clock/可等待公开时间 | 修改生产全局时间造成竞态 |
| Git filesystem | adapter fake + temp tree | 真实 Git、临时 workspace、loopback bare remote | 读取开发者 repo config/credential |
| GitHub/provider namespace | typed fake result | 本地 HTTP stand-in，支持 ready/permission/timeout/uncertain | 默认 CI 访问生产或使用 secret |
| OpenCode/model | deterministic fake | `--opencode-backend mock`，覆盖 ready/error | 用模型自由输出证明 canonical 状态 |
| Runtime/program | 固定 read-model fixture | 真实 projection adapter 接 fixture store；action dispatcher 记录受权调用 | 在 UI test 直接修改 DOM 当作 Runtime 推进 |
| 网络 | adapter error/timeout | Browser→真实本地 server；外部仅 loopback | 隐式公网访问 |

### 2.5 测试环境

- CI：GitHub-hosted Ubuntu 负责完整 quality/unit/integration/e2e；现有 macOS/Windows 和 Python 支持矩阵负责安装/adapter 兼容。PR 无 secret。
- 每个 case 创建独立 `HOME`、workspace、store、ports、Git config、browser context 和 operation ledger；case 结束无论成功失败都 teardown server/remote/temp resources。
- `run-project-venv` 构建 wheelhouse，分别安装 local/global runtime，校验 product Python 与 repo `.venv` 不同，再启动 `python -m louke serve --project-root <case> --host 127.0.0.1 --opencode-backend mock`。
- server readiness 最长 60 秒；未 ready 直接失败，不执行假浏览器断言。integration/e2e job 分别 20/30 分钟超时。

---

## 3. 功能测试

### 3.1 正常流程

Shield 按公开 surface 组合以下用户旅程，不以具体测试函数作为合同：

1. **空白 workspace/init 主旅程**：打开 `/` → 创建首用户 → Login → Repository 选择 init → Preview → Confirm → dependencies 全项 Recheck/ready → Review/Apply → Ready/Empty → Start Story Preview。逐步断言 IF-02/04/05/06/07/11 的可见步骤、零副作用边界、Git readback、complete gate 和对象 identity。
2. **空白 workspace/clone 主旅程**：使用 loopback Git remote，选择 clone → 预览脱敏 remote/目标/影响 → Confirm → 完成 Setup；断言 workspace HEAD/origin、seed 文件、Setup binding 和 UI identity 一致。
3. **已有 workspace 入口矩阵**：分别准备 setup attention、active work、released only、ready empty、active+released，登录/刷新后验证 IF-03 优先级，历史 Released 从 current context 仍可访问。
4. **驾驶舱/Guide 旅程**：在 Ready、Current、Released、attention 之间切换 fixture revision；断言 IF-08 全字段、无百分比、单 required action、Guide 同 context、activity 切换、偏好持久化及 owning surface 边界。
5. **兼容/深链旅程**：从旧 `/workbench`、`/setup`、`/projects`、versioned release API 和 bookmarked Story/Run 进入，断言与 canonical object/revision 相同；返回/前进/刷新不生成平行对象。

### 3.2 异常与恢复流程

- 首用户 validation/store 失败：不进入 Repository，不回显 credential；retry 成功只创建一个 owner。
- remote invalid/unreachable、目标非空冲突、路径范围外、permission denied：Preview/Confirm 停留 Repository/attention，现有文件 digest 不变。
- clone/init 在 operation 已发生但响应丢失：重启后 Reconcile 从 Git readback 返回 completed/already applied，不重复创建；无法确认则 uncertain，Start Story disabled。
- dependency ready→timeout/missing：本轮结果不沿用旧 ready；Review disabled；修复后 Recheck 恢复。
- preview 后文件树、selection 或 revision 变化：旧 Confirm `409`；并发两个 Confirm 仅一个产生 side effect。
- Apply 期间关闭浏览器/杀 server：重启后显示 completed/pending/failed/uncertain item，保持同 revision；只继续未完成项。
- status 网络断开/超过 freshness：标 stale、mutation disabled；重连 readback revision 变化时更新并提示，不回退。
- owning surface action timeout：先 readback；已接受则显示新状态，未接受才可 Retry。Guide 仅导航，越权/过期 action 不 dispatch。
- 不存在/无权 deep link：安全 not-found/只读 permission 反馈，不落入其他 Project。

### 3.3 边界值与状态组合

- URL：最大允许长度、Unicode host 的规范化、SCP-like SSH；空、控制字符、userinfo/password、`file://`、相对/绝对本地路径、未知 scheme 拒绝。
- workspace：完全空、仅 `.louke`、已有 Git/无 remote、已有 Git/多 remote、detached HEAD、同名相同文件、同名不同文件、只读目录、symlink 逃逸。
- revision/idempotency：当前、旧、未知、空；同 key 同 payload、同 key 异 payload、两 session 并发。
- dependencies：全 ready、逐项 missing、error、timeout、ready 后变化、非必需项失败。
- Workflow Status：每种 phase display state；每种 attention canonical state；artifact/evidence/error/action 各自 null 和完整；未知字段/schema fail closed。
- Guide：首次/重复提示、context 变化、未发送输入、collapsed/expanded、divider 最小/最大/默认、解释 backend failure。

---

## 4. 页面与交互测试

### 4.1 Surface/动作/反馈矩阵

| Surface/context | 关键动作与输入 | 可见/可用条件 | 必测状态与恢复出口 |
|---|---|---|---|
| Identity/Login | name/credential、提交、重试 | 首用户只在未初始化显示；pending 禁止重复 | field error、store failure、success→Login、restart persistence；credential 不回显 |
| Repository | init/clone、remote URL、Preview/Confirm/Back | Confirm 仅对当前无冲突 preview 启用 | loading、invalid、unreachable、conflict、stale、uncertain、Re-preview/Reconcile |
| Dependencies | 单项/全部 Recheck、Continue | required 全 ready 才能 Review | ready/missing/error/timeout、修复后重查、非秘密诊断 |
| Review/Apply | Back、Confirm、Cancel、Apply | authenticated、current revision、无 blocker | zero-side-effect preview、pending、partial、success、failed、uncertain、reconcile |
| Ready/Empty | Start Story、导航 | Setup valid 且无 active work | readiness、Story input、Preview、blocked 返回路径 |
| Current Work | 打开 Story/Run/artifact/Released history | stable object identity | attention、waiting party、required action、返回 context |
| Released | 历史 artifact、开始下一个 Story | 无 active work 才提供开始入口 | 新 active work 后 resolver 切 Current，历史仍可达 |
| Workflow Status | Retry、合法 action、导航 | mutation 只在 fresh/authorized | loading、empty、fresh、stale、conflict、permission、reconnect、error |
| Guide | 折叠、调整、追问、导航 | action 只来自 Runtime；formal decision 仅 owning surface | context change、首次提示、去重、解释失败、未发送输入、只读历史 |

### 4.2 导航与对象连续性

- sidebar 所有承诺 activity：Project、Docs、End User Docs、Wiki、Runs、Settings、Setup；Guide 保持挂载，主内容和 URL 更新。
- Project/Story/Run 深链、browser back/forward、refresh、new context/bookmark 均核对同一 workspace/project/release/story/run identity。
- Setup 未完成访问深链时保存安全同源 continue URL；完成后返回目标。外部/协议相对 `next` 被拒绝，防止 open redirect。
- `/api/releases/...` 与 `/api/v14/releases/...` 对同一请求返回同一 object/revision；写操作仅一次。

### 4.3 可访问性与响应式

- 真实 Chromium 只用键盘完成 init 主旅程；验证 skip link、focus order、dialog focus return、Enter/Space 和错误摘要聚焦。
- 状态、错误、pending、stale、conflict、permission、Guide 更新由 role/name/description/live region 可观测且不只依赖颜色。
- viewport/zoom 强制组合：`1024x768 @ 100%`、`1280x720 @ 100%`、`1280x720 @ 200%`；断言无主操作遮挡、Guide 恢复入口和 required action 可达。
- Guide 在主表单有焦点和未发送输入时收到 status revision 更新：active element 和输入值不变，辅助技术能获知非侵入更新。
- reduced-motion 模式下状态信息完整；自动临时折叠不覆盖持久 preference。

---

## 5. 非功能测试

### 5.1 安全

- 使用 canary credential/token/remote userinfo 字符串跑身份、provider、clone 和失败路径；递归检查 HTTP body、页面文本、Setup facts、Guide/Agent 输入、structured events、server log、JUnit、Playwright trace/screenshot、runner evidence 与 git-visible files，原文匹配即失败。
- 未认证访问 Runtime/Project/Guide/action；低权限访问其他 workspace；CSRF/同源和 stale action 均不得产生 state/side effect。
- Git URL/路径输入覆盖 shell metacharacter、控制字符、path traversal、symlink escape 和 malicious repository filename；subprocess evidence 不应显示 shell 解释结果。
- Preview/未 Confirm 前以及 permission/conflict 后，对 workspace tree、Git refs/remotes 和 stand-in provider resource 做前后 digest/count 比较。

### 5.2 可靠性、恢复与并发

- 在每个 Wizard step、Repository Confirm 前后、Apply 每类 operation 结果、Story Confirm 后注入 browser close/server termination；重启后从 IF-03/04/08/11 readback 验证同 revision/object。
- 两 browser context 对同 revision Confirm/Apply/action：精确一个获准，另一 stale/conflict；Git/provider/object count 至多一份。
- adapter timeout、进程返回非零、响应丢失、store 写失败、manifest 未知 schema：均 fail closed，无 complete/success/next action。
- 默认 CI 不以 sleep 猜测完成；使用 readiness、公开 projection revision 和 bounded polling。

### 5.3 性能与新鲜度

Spec 未承诺吞吐/绝对延迟，不设置产品性能 SLO。防回归预算：本地 stand-in 下 Entry/Status/Guide read p95 <= 500ms，纯本地 Setup projection <= 500ms；外部 dependency probe 单项 <= 10s 且总检查有界。预算失败作为 integration 诊断门禁，环境明显抖动必须记录而不能自动 retry 冒充通过。

Workflow Status 连续 30 秒无成功 readback 必须进入 stale；网络恢复后的下一次成功 readback 更新 revision/observed time。测试以公开 freshness 字段和 UI stale label 断言，不读取内部 timer。

### 5.4 兼容与构建物

- 用 fixture 升级含有效 Setup、Project、Run、release request、artifact、milestone 和历史 Maestro evidence 的 workspace；对象 count/identity/digest 前后相同。
- wheel 与 sdist 均从 metadata 提取版本并与 `pyproject.toml` 比较；隔离安装 wheel 后核对 import metadata、CLI 版本出口（若已有）和新 Workbench 静态资产。
- local/global runtime、Linux 完整 suite；现有 macOS/Windows 安装矩阵验证路径、subprocess argv 和静态资产可用性。

---

## 6. 测试数据与 Fixtures

### 6.1 数据位置

- `tests/fixtures/v014_workspace_onboarding/`
  - 最小 Git seed 内容与生成说明（CI 运行时创建 bare remote，不提交真实 credential）。
  - Setup manifest：缺失、各 step、complete、blocked、unknown schema、corrupt、operation uncertain。
  - Runtime projection：Ready/Current/Released、各 attention 状态、artifact/evidence/allowed action 组合。
  - 历史 workspace：v0.14 前 Setup/Project/Run/release/artifact/Maestro read-only 样本。
- 动态数据全部在 runner temp root 创建；固定 ID 使用明显 `fixture_*` 前缀，时间由固定 clock 提供。

### 6.2 隔离与清理

- 每个 case 使用唯一 workspace/home/port/browser context/idempotency namespace；禁止 case 顺序依赖。
- fixture 只读复制后运行；测试不修改仓库内 fixture。
- server、loopback Git HTTP、provider stand-in 均由 fixture context 管理，在 `finally` 终止并验证无残留进程/锁。
- 测试环境清除 `PYTHONPATH`，隔离 `HOME`、Git config 与 credential helper；不继承 SSH agent、GitHub/OpenCode token。
- 失败保留的 trace/log 先脱敏再上传；临时 workspace 不作为 artifact 整体上传。

### 6.3 关键数据组合

| 数据集 | 用途 | 关键断言 |
|---|---|---|
| `blank-init` | 空目录 init happy path | Preview 零副作用、Confirm 后一个 `.git`、Setup complete |
| `blank-clone` | loopback remote clone happy path | HEAD/origin/seed/binding 一致，URL 脱敏 |
| `nonempty-conflict` | 同名不同内容 | 目标 digest 不变，attention + Reconcile |
| `partial-operation` | clone/apply 响应丢失 | restart readback，不重复 side effect |
| `entry-matrix` | Setup/current/released/empty | resolver 优先级和历史可达 |
| `status-matrix` | waiting/blocked/conflict/interrupted/closing | 单主动作、责任方、错误、无百分比 |
| `legacy-workspace` | 兼容升级 | object identity/count 不变，Maestro 只读 |
| `secret-canary` | 泄漏扫描 | 所有用户/evidence 出口零原文匹配 |

---

## 7. CI 执行与质量门禁

### 7.1 触发与 gate

| 事件 | 必跑 gate | 外部服务/secret |
|---|---|---|
| pull request（含 fork） | quality、unit、traceability、build-artifacts、artifact-verify、integration、e2e-standin、install-matrix、required | 仅 stand-in；无 production secret |
| 默认分支 push | 与 PR 相同 | 仅 stand-in |
| release/tag | 同一 source/artifact identity 的全部 required gate；再按现有发布合同运行 protected real-smoke/publish | environment secret 最小权限；publish 不得绕过 required/artifact verify |
| manual smoke | 选择性真实 GitHub/OpenCode smoke，明确 target/source/artifact/AC identity | protected environment；结果不能替代默认 required |

稳定聚合 check 唯一名称为 `Louke CI / required`。它以 `if: always()` fail closed 汇总所有 needs；任一失败、取消、超时、skipped、缺失或未知时不得 success。

### 7.2 Job 输入与 evidence

- `quality`：ruff format/check、mypy、现有合同检查。
- `unit`：JUnit、collected/failed counts 和 AC markers。
- `traceability`：43 个规范 AC ID、IF-01..15、required layers、CI job 与 collected node ids 闭合；未知/缺失/只用低层替代均失败。
- `build-artifacts`/`artifact-verify`：真实 wheel/sdist、SHA-256、source SHA、每 artifact metadata version、隔离安装 readback。
- `integration`：必须发现 `tests/integration/v014_workspace_onboarding/`，上传 JUnit、脱敏 operation evidence；zero collection 失败。
- `e2e-standin`：必须发现 `tests/e2e/v014_workspace_onboarding/` 并在 local/global 两 runtime 运行；上传 runner evidence，失败时上传脱敏 Playwright trace/screenshot/log。
- `install-matrix`：继承现有 OS/runtime 安装覆盖，验证 shell/static 进入 artifact。

JUnit/traceability/runner evidence 保留 30 天；失败浏览器 evidence 14 天；artifact retention 沿用 release workflow。所有 evidence 带 source SHA、runtime/OS/Python、suite、node ids、AC IDs、结果和时间。

### 7.3 失败语义

- 测试不自动 rerun；flaky 视为失败并修复。timeout、零收集、evidence schema/identity 不确定均失败。
- artifact 构建失败、wheel/sdist 缺失或多余、版本无法提取/不一致、安装态公开版本不一致均阻断 required/publish。
- secret canary 发现、外部公网意外调用、清理失败、残留服务或测试读取真实 HOME/credential 均阻断。
- runner discovery、`project.toml` 契约、workflow 或本文路径漂移时 contract gate 失败，不允许 Shield 临时改命令绕过。
- `tools/check_ac_traceability.py` 当前对 v0.14-001 acceptance 已 82/82 covered。Sage 于 2026-07-24 完成 v0.14-004 的 43 项标题规范化后，scanner 报告 `42/43 covered`：`AC-NFR0501-01`（NFR-0501 可操作诊断与用户可理解性，主路径）尚无 `tests/` 资产引用。Devon 必须在新增 `tests/integration/v014_workspace_onboarding/`（或同等 e2e 资产）写入 `AC-NFR0501-01` token，覆盖诊断暴露、术语抑制与 Start Story 主路径。
- `Louke CI` 的 `ac-trace` job 当前仅扫描 v0.14-001 acceptance；Devon 必须扩展使其同时扫描 v0.14-004 acceptance 并以 `--expected-count 43` 失败闭锁。本计划默认该 job 已同步扩展，未扩展前 required check 不得宣称激活。

---

## 8. 完成标准

- [ ] 43 个 Acceptance ID 全部映射到 `interfaces.md` 出口、必需测试层、CI job 与 collected evidence。
- [ ] IF-01 至 IF-15 每项至少有 integration 覆盖；所有跨模块接口未被 unit 替代。
- [ ] init 与 clone 两个 Setup 主分支、重启恢复、Ready→Start Story、驾驶舱/Guide 和稳定深链均有安装态 Chromium e2e。
- [ ] loading、success、failure、empty、dirty/输入保留、stale、conflict、permission、uncertain 和 reconnect 的适用交互状态均由公开接口断言。
- [ ] 支持 viewport/zoom、键盘、focus、live region 和 Guide 非侵入行为通过 e2e。
- [ ] secret/权限/路径/授权前零副作用、并发 at-most-once 与 reconcile fail-closed 通过。
- [ ] `run-project-venv` 确定性发现本 Spec integration/e2e 资产，安装态产品不从 checkout 导入。
- [ ] GitHub Actions 完成 quality、unit、traceability、真实 build/artifact verify、integration、e2e、install matrix，并由唯一 `Louke CI / required` fail closed 聚合。
- [x] `project.toml` 的 `[meta].test_framework`、`[integration]` 与 `[e2e]` 已按当前授权写入，并与 `architecture.md` 第 9 节一致；这只是 author revision，Runtime 仍负责 program validation/result persistence/activation。
- [x] `spec.md` 已补充 22 个 `<a id="fr-/nfr-XXXX">` 锚点以满足 `louke/_tools/verify_issue_schema.py` 的 L5/L6 合同；`acceptance.md` 的 `<a id="ac-fr-/ac-nfr-XXXX">` 锚点已在 T-001 修订时就位。
- [x] 本 Spec 的 22 个 issue (`#322—#343`) 已在 `zillionare/louke` 创建，并通过 `gh project item-add 20 --owner quantclaws` 全部加入 Project #20；`louke/_tools/verify_issue_schema.py --offline` 报告 22/22 PASS（L1—L8 + 双向覆盖）。已建立 `spec:v0.14-004-onboarding-status` label（GitHub 50 字符上限截断）。`issues.md` 持久化 22 条 URL，inline discussion `T-002` 由 Sage 标 RESOLVED。
- [ ] required machine-contract instance 尚缺 program-owned exact active schema reference、instance output path 与逐路径授权；不得从旧 candidate 自证或标记 activated；Runtime 在 M-LOCK-1 阶段负责。
- [x] Devon 已接管 M-IMPL（Human 2026-07-24 选项 1）：补 `AC-NFR0501-01` 引用与断言、扩 `louke-ci.yml ac-trace` 双扫 + `--expected-count 43`、扩 `tests/e2e/run_e2e.py` discovery、`tools/check_ac_traceability.py --expected-count` 参数、`tools/louke_python_release_adapter.py verify-dist` 子命令。具体取舍与执行由 Devon 在本 Spec 锁定的 interface/layer/CI 框架内落地。
- [ ] Devon 无需重新选择模块、endpoint、runner、CI DAG、required check、依赖、Git adapter 或版本验证方案；Shield 无需发明环境、数据路径或测试入口。
