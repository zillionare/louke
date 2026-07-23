# v0.14-004 Workspace Onboarding 与 Workflow Status 架构

## 1. 范围与事实基线

本文落实 `STR-1405`、本目录 `spec.md` 与 `acceptance.md` 的 Workspace 集成、Setup Wizard、登录落点、驾驶舱和 Guide 合同。`v0.14-001` 仍拥有 Setup、release、Foundation、M-STORY 的领域语义；`v0.14-002` 与 `v0.14-003` 分别拥有后续设计和实现阶段语义。本 Spec 只提供连续的人机入口与只读状态投影，不复制 Runtime 状态机。

宿主项目为现有 Python 包，而非新项目：

- Python `>=3.11`，构建源和版本源均为 `pyproject.toml`；构建物为 wheel 与 sdist。
- Web 服务使用 Starlette，服务入口为 `python -m louke serve`。
- 持久化沿用项目 SQLite/文件事实源；测试使用 pytest、pytest-asyncio、Playwright、ruff、mypy。
- `tests/e2e/run-project-venv` 与 `tests/e2e/run_e2e.py` 是安装态 integration/e2e runner；当前 runner 尚未发现本 Spec 的资产，Devon 必须按本文扩充，不另造入口。
- `.github/workflows/louke-ci.yml` 是 Louke 托管 workflow；本文锁定其本轮更新合同。
- 2026-07-24 当前调用明确授权 `.louke/project/project.toml` 的 `[meta].test_framework`、`[integration]` 与 `[e2e]` schema/write scope；第 9 节记录已写入的 project-local runner contract。
- 当前调用虽提及 machine-contract schema 授权，但未给出 program-owned exact active schema reference、instance output path 或逐路径 write scope；本 Spec也未将 Agent prompt 列为规范性工件。因此本 revision 不从旧 candidate/prompt/instance 推断 schema，不生成或自称激活 machine-contract instance。Runtime 未补齐 exact reference 时必须 fail closed。

本 Spec 不改变产品版本、tag、artifact 身份或发布清单，因此无需新的版本同步 adapter。现有 `pyproject.toml` 权威版本、`python -m build`、wheel/sdist metadata 提取和安装态 `importlib.metadata.version("louke")` 验证合同保持不变；CI 仍必须真实构建和复核两种 artifact。

## 2. 模块边界

| 模块 | 职责 | 不拥有的职责 | 公开观察边界 |
|---|---|---|---|
| `Workbench Presentation` | 呈现统一 shell、Setup、Project/Story/Run 页面、驾驶舱、Workflow Status 与 Guide；表达可见/禁用/只读/反馈状态 | 不推导 canonical workflow，不直接执行 Git、依赖检查或 dispatch | HTTP 页面、浏览器可访问名称/状态、稳定 URL |
| `Entry Resolver` | 根据身份、session、Setup manifest、active project/release 和 Runtime projection 选择唯一落点 | 不写 Setup/Runtime，不以浏览器缓存决定落点 | `EntryProjection` API 与 redirect URL |
| `Setup Application` | 驱动连续 Wizard，校验 step action，保存恢复点，组织 Preview/Confirm/Recheck/Reconcile | 不直接调用 shell，不重定义 v0.14-001 Setup 语义 | Setup projection 与 command API |
| `Repository Adapter` | 校验 remote URL，执行安全的 init/clone staging、冲突检测与 reconcile；返回脱敏结果 | 不接触认证页面或保存 URL credential | Repository preview/result projection |
| `Dependency Adapter` | 探测 Python、Git、GitHub CLI、OpenCode 等运行依赖，给出可重试的逐项结果 | 不把 provider metadata 变成流程事实 | Dependency check projection |
| `Runtime Projection` | 从 Runtime/program 和 artifact facts 生成只读 Workflow Status、合法 actions、evidence、错误与更新时间 | 不 dispatch、不推进阶段、不估算百分比 | Workflow status API |
| `Guide Application` | 将当前 projection 转成责任方、下一步、风险与导航，维护 Guide 对话与用户偏好 | 不拥有流程状态；不把模型文本当事实；不 dispatch、不执行正式输入/决定/action | Guide projection、对话、导航与偏好 API |
| `Release Entry` | 复用 release/Story Preview/Confirm 和打开 Story/Run 的稳定合同 | 不改变 release 作为交付容器的语义 | 稳定 release API 与深链 |
| `Workspace Fact Store` | 原子保存 Setup manifest、operation ledger、Guide 用户偏好及既有项目/release/runtime facts | 不保存明文秘密，不成为浏览器私有状态 | 版本化 JSON/SQLite 事实及 readback API |
| `External Adapters` | 隔离 Git/GitHub/OpenCode/subprocess 与系统时钟；允许测试替身 | 不向 UI 暴露 transport/session metadata | 结构化 adapter result |

## 3. 依赖方向与 authority

```text
Browser
  -> Workbench Presentation
      -> Entry Resolver -------------> Workspace Fact Store
      -> Setup Application ----------> Repository/Dependency Adapters
      -> Runtime Projection ---------> Runtime/program + artifact facts
      -> Guide Application ----------> Runtime Projection
      -> owning-surface actions -----> Runtime-authorized action dispatcher
      -> Release Entry --------------> existing release/Story contracts

Repository/Dependency Adapters -> controlled subprocess/external stand-ins
```

规则：

1. `Runtime/program` 是 canonical 状态、责任方、合法 action、dispatch 和推进的唯一 authority。Guide 与 Presentation 只消费 projection。
2. `Entry Resolver` 是纯读决策；每次认证、刷新、重连和服务器重启后都从持久事实重新计算，绝不信任浏览器缓存中的阶段。
3. Setup command 只可由 `Setup Application` 调用 adapter。每个写操作采用 operation id、预览摘要和事实 readback，重复提交返回相同结果或明确冲突。
4. Runtime 发放的 opaque action id 只在对应 owning surface 呈现和提交；服务端在执行前重新校验当前 revision。Guide 只能链接到该 surface。stale action 返回冲突，不 dispatch。
5. provider/session metadata 仅为 transport metadata，不写入 Workflow Status，也不改变责任方。

## 4. Setup、Repository 与恢复设计

### 4.1 连续 Wizard 与持久恢复

Setup 只有一个 shell 内旅程，固定阶段为 `identity -> repository -> dependencies -> review -> applying -> complete`。每一步的 projection 同时给出当前步骤、已完成步骤、可用动作、阻塞项和安全返回路径。服务端只在成功 readback 后推进；页面刷新或服务重启后按 manifest 继续。

Setup manifest 采用带 schema version 的原子事实，记录 workspace identity、step、选择、非秘密 remote display URL、preview digest、operation ledger、dependency results、时间戳和完成状态。写入使用临时文件/事务后原子替换；损坏、未知 schema 或与 workspace identity 不匹配时 fail closed，显示可定位错误和 Recheck/Reconcile，而不猜测完成。

### 4.2 Git init

非 Git workspace 选择 `init` 后，Preview 列出目标根目录、将创建的 `.git`、保留的现有文件和冲突。Confirm 只在 preview digest 与当前文件树摘要一致时执行 `git init`。若期间事实变化，返回 stale conflict 并要求重新 Preview。已有 Git repository 的重复 Confirm 通过 readback 返回 completed，不重复破坏。

### 4.3 Remote clone/binding

允许 `https://` 与 `ssh://`/SCP-like Git URL；拒绝控制字符、URL userinfo/password、`file://`、本地路径和非 Git scheme。UI 与日志只保留脱敏 display URL；credential 必须由受控 Git credential/SSH 环境提供，不写 manifest、日志或 evidence。

clone 采用同一文件系统中的 sibling staging directory：

1. Preview 校验 URL、目标 workspace、是否为空、现有 `.louke` facts 和冲突；只做只读 remote probe。
2. Confirm 将 remote clone 到随机 staging，验证它是 Git worktree、HEAD 可解析且路径不含逃逸。
3. 对目标逐路径比较。目标为空时使用原子 rename；目标只含当前 `.louke` 时，将 clone tree 与 Louke facts 做封闭 merge，任何同名不同内容均成为 conflict。
4. 写 operation ledger 后执行 rename/merge，再 readback HEAD、origin 的脱敏 URL 和 Setup facts。成功前不删除可恢复 staging；失败时保留目标原状并暴露 reconcile token。
5. Reconcile 根据 ledger 和 readback 选择“已完成”“可安全回滚 staging”“需用户解决冲突”之一，不自动覆盖或删除用户文件。

不采用“直接在非空 cwd 执行 `git clone .`”，因为部分失败会污染 workspace；不采用下载 archive，因为会丢失 Git identity 与 remote binding。staging 增加磁盘占用和跨设备 rename 风险，因此 staging 必须与目标同一父目录，并在空间不足/跨设备时在写入前失败。

### 4.4 依赖检查

依赖探测通过 adapter 返回 `ready|missing|error`、非秘密版本摘要、修复说明和 `recheck` 能力。单项检查相互隔离；一个外部工具超时不应把其他项标成通过。默认每项 10 秒并有总超时；超时结果是可重试 error。Review 仅在必要依赖 ready 且 Repository readback 成功后启用 Apply。

## 5. Workbench、Workflow Status 与 Guide

### 5.1 入口拓扑

`/` 是 canonical shell：无首用户时打开 Setup Identity；有用户无 session 时显示 Login；认证后由 `Entry Resolver` 返回：

- Setup 未完成：打开对应 Wizard step；
- 有 active project/current work：打开 Current Work；
- 无 current work 但有 released item：打开 Released；
- Setup 完成且为空：打开 Project 驾驶舱 Ready/Empty，主动作是 Start Story。

旧 `/workbench`、`/setup`、`/projects` 及现有 v0.14 API 别名保留为兼容入口，但最终进入同一 shell/context；不得复制状态实现。

### 5.2 Workflow Status

状态投影同时包含 release/project、阶段序列和当前阶段、canonical 状态、责任方、artifact/revision、evidence、最近错误、required action、更新时间与 stale 标识。展示仅使用 `completed|current|pending|attention`，不显示百分比。缺失/未知 canonical 字段必须显示 `Unavailable/Attention`，不能推测成功。

当 projection revision 变化、网络断开或超过 30 秒未成功刷新时，Presentation 标为 stale 并禁用 mutating action；只读导航保留。重连后自动 readback：revision 相同恢复动作，revision 不同刷新内容并提示状态已更新。冲突保留用户输入并提供 Refresh/Retry；权限不足隐藏无意义的危险动作并显示只读原因。

### 5.3 Guide

Guide 固定在 Workbench sidebar 下方约 `1/3` 高度，可折叠；折叠偏好按用户持久化。窄高/200% zoom 下可自动临时折叠，但不覆盖用户偏好。支持范围锁定为：`>=1024x768`、100% zoom；以及 `>=1280x720`、最高 200% zoom。主内容、sidebar 导航与 Guide 均不得互相遮挡；键盘可到达折叠、导航和 action 控件。

Guide 摘要由 deterministic projection 生成，包含当前阶段/状态、责任方、下一步、阻塞/错误和导航。若使用 Agent 生成解释，只能补充非规范说明，服务端仍从 projection 渲染 canonical facts；模型失败时 deterministic 内容完整可用。

Guide 只提供到 owning surface 的导航。Workflow Status 的 `allowed_actions` 由对应正式 surface 呈现；单击后立即显示 pending 并禁用重复提交，成功显示新的 revision/导航，失败显示错误、未推进声明与 Retry。危险或不可逆 action 使用 Preview/Confirm；取消回到当前上下文且不产生 dispatch。

## 6. 持久化、并发与安全

- Setup manifest 和 operation ledger 随 workspace 持久化；Guide 的 collapsed、divider ratio 与 last-seen preference 绑定 authenticated user。浏览器 `localStorage` 只可作为展示缓存，不可作为事实源。
- 所有 command 接收 `expected_revision` 和 `Idempotency-Key`。revision 不匹配返回 `409 stale_revision`；同 key 同 payload 返回原结果，同 key 异 payload 返回 `409 idempotency_conflict`。
- CSRF、session、同源与权限沿用现有 Web 安全边界。认证前只允许读取首次 Setup 必需事实并提交首用户；其他项目/runtime 数据不可见。
- remote、subprocess 参数使用 argv 传递，不拼 shell；环境变量采用 allowlist。输出需去除 token、userinfo、home path credential helper 内容。
- Setup 与 owning-surface Runtime command 的 structured audit 记录 action、actor、workspace、revision、result/error code 和时间，不记录 password、token、完整 credential URL 或 provider session metadata。Guide message/preference/last-seen 不写 Runtime evidence，访问日志也不记录对话正文。
- 两个浏览器并发操作时只允许首个匹配 revision 的 command 成功；后续返回冲突并要求刷新。

## 7. 技术选型、依赖与取舍

| 选择 | 解决的问题 | 放弃的替代 | 主要风险/缓解 |
|---|---|---|---|
| 继承 Python 3.11+、Starlette 与现有原生 Web 资产 | 避免为单一集成 Spec 引入第二套 runtime/front-end build | React/Vue SPA 重写 | 手写交互状态复杂；以 typed projection、可访问语义和 Playwright 合同约束 |
| 继承现有 SQLite/版本化 JSON 事实源 | 可恢复、可 readback，复用项目事务边界 | 浏览器状态、Redis、新数据库 | schema 演进；未知版本 fail closed，并保持 migration/readback 测试 |
| Python stdlib `subprocess` + project-local adapters | 精确控制 Git/tool argv、超时和脱敏；无需新 runtime 包 | GitPython、直接 shell command | subprocess 平台差异；argv allowlist、Windows/POSIX integration matrix |
| Git sibling staging + atomic merge ledger | clone 失败不污染当前 workspace | 直接 clone 到 cwd、archive 下载 | 双倍磁盘与清理；预检空间、同父目录、reconcile ledger |
| deterministic Workflow/Guide projection | 保证 Runtime authority 和无模型降级 | 由 Agent 自由推理状态 | 文案较机械；允许非规范解释但 canonical facts 永远由 projection 渲染 |
| pytest + pytest-asyncio + Playwright，版本继承 `pyproject.toml` lock/constraints | 与现有测试和安装态 runner 一致 | 新增 Cypress/Jest | 浏览器 suite 时间；仅关键旅程 e2e，边界下沉 integration/unit |

本 Spec不引入新的 runtime 或 test 第三方库。Devon 必须使用 `pyproject.toml` 当前锁定/约束版本；若实现发现必须增加依赖，须先修订本设计并记录 license、版本与取舍，不能自行选择。

文档保持 Markdown；Python 代码风格、ruff、mypy、pytest markers 沿用 `pyproject.toml`。实现配置包括扩充 runner discovery、traceability manifest 和 workflow；Archer 不创建业务脚手架。

## 8. 测试可替换性与资产边界

- `SystemClock`、Git/remote probe、GitHub/OpenCode/provider、filesystem operation 和 action dispatcher 均通过 adapter 边界注入。
- unit 使用临时目录、固定时钟和纯 adapter fake；不得 mock 公开 HTTP 出口来证明 integration。
- integration 资产：`tests/integration/v014_workspace_onboarding/`，覆盖 HTTP/application/store/adapters 真实接线；remote clone 使用 loopback Git HTTP fixture，不访问公网。
- e2e 资产：`tests/e2e/v014_workspace_onboarding/`，通过安装 wheel 的产品 Python 启动真实 Web 服务；使用 mock OpenCode backend、临时 HOME/workspace、loopback Git remote 和真实 Chromium。
- fixtures：`tests/fixtures/v014_workspace_onboarding/`，只含无秘密的 bare Git seed、manifest revisions 和 Runtime projection 样本。
- 测试进程拥有临时 workspace 和 HOME；不得读取开发者真实 `~/.gitconfig`、credential helper、SSH agent 或生产 secret。

## 9. `project.toml` 运行合同（author revision）

2026-07-24 当前调用已授权 `.louke/project/project.toml` 的 `[meta].test_framework`、`[integration]` 与 `[e2e]` schema/write scope。配置保留既有项目资产并加入本 Spec 的确定路径；这只是 project-local runner contract 的 author 写入，不代表 Runtime candidate activation：

```toml
[meta]
test_framework = "pytest"

[integration]
cwd = "."
paths = ["tests/e2e", "tests/integration", "tests/fixtures", "tests/ground_truth", "tests/integration/v014_design_contracts", "tests/integration/v014_workspace_onboarding", "tests/fixtures/v014_workspace_onboarding"]
run = "tests/e2e/run-project-venv integration"

[e2e]
cwd = "."
paths = ["tests/e2e", "tests/fixtures", "tests/ground_truth", "tests/e2e/v014_design_contracts", "tests/e2e/v014_workspace_onboarding", "tests/fixtures/v014_workspace_onboarding"]
run = "tests/e2e/run-project-venv e2e --profile all --runtime both"
ready_timeout_seconds = 60
```

`start`/`ready`/`teardown` 省略：现有 runner 按 case 启动安装态产品服务、做 readiness 并在 `finally` 清理；Devon 必须扩充 `v014` profile discovery 包含本目录，不能要求 Shield 手工启动服务。`[meta].test_framework = "pytest"` 已与设计一致，无需重复改值。

## 10. GitHub Actions CI 合同

### 10.1 触发、runner 与权限

Devon 更新而不替换 `.github/workflows/louke-ci.yml`。触发保持 `pull_request`、默认分支 push、release/tag workflow dispatch；默认 `permissions: contents: read`。PR，尤其 fork PR，不使用 production secret、不运行 `pull_request_target`、不执行真实 provider smoke。Python 主验证版本为 3.11；安装/平台兼容矩阵继承现有 Ubuntu/macOS/Windows 与项目支持版本，不能缩小当前支持面。

actions 版本策略继承现有受审 major pin（`actions/checkout@v4`、`actions/setup-python@v5` 等）；任何新增 action 必须固定到完整 commit SHA。Python 依赖使用仓库 lock/constraints 和 wheel cache key（OS、Python、lock digest），不得缓存 workspace facts、credentials 或测试结果。

### 10.2 必需 job DAG

```text
quality ───────────────┐
unit ─────────────────┤
traceability ─────────┤
build-artifacts -> artifact-verify ─┤
integration ──────────┤
e2e-standin ──────────┤
install-matrix ────────┤
                       -> required
```

- `quality`：执行 `pre-commit run --all-files`（其中包含仓库 ruff/文档 hooks），再执行 `python -m mypy louke`。
- `unit`：沿用安装态命令 `/tmp/lk-venv/bin/python -m pytest -q tests/unit --cov=louke.runtime --cov-report=xml --cov-report=term-missing --cov-fail-under=95`；上传 coverage/JUnit evidence。
- `traceability`：保留现有 v0.14-001 scan，并对本 Spec 执行 `python tools/check_ac_traceability.py --acceptance .louke/project/specs/v0.14-004-workspace-onboarding-workflow-status/acceptance.md --tests tests --expected-count 43`。Devon 必须为现有 project-local tool 增加 `--expected-count` 并令零声明/数量不符失败；缺 AC、未知 AC或层级 evidence 不足均失败。
- `build-artifacts`：`python -m build`，上传唯一 wheel、sdist、SHA-256 manifest 和 source commit。
- `artifact-verify`：Devon 扩充现有 project-local adapter，执行 `python tools/louke_python_release_adapter.py verify-dist --source pyproject.toml --dist dist --evidence dist/verified-identity.json`，精确验证一个 wheel、一个 sdist 及两者 metadata 与 source version；再在隔离 venv 安装该 wheel并执行 `lk --version` 与 `python -c "import importlib.metadata as m; print(m.version('louke'))"`。artifact 缺失、多余、无法提取或不匹配均失败。
- `integration`：调用 `tests/e2e/run-project-venv integration`，必须发现本 Spec integration 路径；零收集失败。上传 JUnit、脱敏 adapter/audit evidence。
- `e2e-standin`：调用 `tests/e2e/run-project-venv e2e --profile all --runtime both`，必须发现本 Spec e2e 路径；真实 Chromium、安装态 wheel、mock provider、loopback Git。上传 Playwright trace/screenshot（仅失败）、runner evidence 与服务日志。
- `install-matrix`：保持现有 local/global 与受支持 OS 安装验证，证明新 shell/静态资产进入 wheel。
- `required`：job 展示名固定 `required`，workflow 名固定 `Louke CI`，形成唯一稳定 check `Louke CI / required`。使用 `if: always()` 检查每个 required need；任何失败、取消、超时、skipped、缺失或未知均非成功。

job timeout：quality/unit/traceability 15 分钟，build/artifact-verify 15 分钟，integration 20 分钟，e2e/install matrix 每 shard 30 分钟，required 5 分钟。测试失败不自动 rerun；flaky 必须修复，不能用 retry 伪造通过。

### 10.3 外部服务、evidence 与发布门禁

默认 required CI 的 Git remote 和 provider 均为可控替身，无 secret。真实 GitHub/OpenCode smoke 保持独立 protected/manual job，只接受环境级最小权限 secret，记录 target identity、source commit、artifact digest、非秘密 endpoint、AC 集合和 teardown；不记录 token。真实 smoke 不能在 fork PR 运行。

若现有 release/publish 合同要求真实 smoke，则 publish 必须依赖 `Louke CI / required`、artifact-verify 及匹配同一 source/artifact identity 的 real-smoke evidence；否则本 Spec 不新增 publish 行为。任何 evidence 身份不一致或不确定都阻断 publish。

artifact retention：JUnit/traceability/runner evidence 30 天，失败 Playwright trace 与脱敏日志 14 天，wheel/sdist及 digest 按现有 release retention。所有 evidence 包含 source SHA、Python/runtime、安装模式、suite、AC IDs 和结果。

### 10.4 演进规则

`.github/workflows/louke-ci.yml`、`tests/e2e/run_e2e.py` discovery、`project.toml` 运行合同和三份设计文档必须同步。改变入口、资产路径、artifact、默认分支、required gate 或外部 adapter 均需新 design revision；Devon 不得在实现阶段重新选择 CI 架构。

## 11. 风险与失败策略

| 风险 | 失败策略 |
|---|---|
| Setup manifest 损坏/未知 | fail closed；显示错误位置与 Recheck/Reconcile，不进入 Complete |
| clone 中断或目标变化 | 不覆盖；保留 ledger/staging，返回 conflict/reconcile |
| credential 泄漏 | URL userinfo 输入即拒绝；日志/evidence 脱敏 gate 失败即阻断 CI |
| Runtime projection 缺失/断连 | UI 标 stale/attention，禁用 mutation，保留只读导航并重连 readback |
| 重复点击/并发 tab | idempotency key + expected revision；一个成功，其余 stale conflict |
| Agent/provider 故障 | deterministic Guide 仍工作；绝不推测 workflow 状态 |
| 旧 URL/API 调用方 | 兼容 redirect/alias 到同一 application service；contract test 防止语义漂移 |
| 浏览器缩放遮挡 | 支持视口组合 Playwright 截图/可访问断言；自动临时折叠 Guide |

## 12. 实现交接结论

接口、模块、runner、数据与 CI 技术方案已经确定，Devon/Shield 无需补做技术选择。Sage 已按 inline discussion `T-001` 在 2026-07-24 把 43 项 Acceptance ID 统一改为全局 `AC-FRXXXX-YY` / `AC-NFRXXXX-YY`，scanner 由原 `0/0 covered` 变为 `42/43 covered`，`AC-NFR0501-01` 尚无 `tests/` 资产引用，由 Devon 在新增 `tests/integration/v014_workspace_onboarding/` 或同等 e2e 资产中加入相应 token 后闭合（见 `test-plan.md` §7.3）；CI 仍需扩展 `louke-ci.yml` 的 `ac-trace` job 同时跑 v0.14-001 与 v0.14-004 acceptance，并增加 `--expected-count 43` 失败闭锁。第 9 节的 `project.toml` runner contract 已写入 author revision；Runtime 仍负责 program validation、result persistence 和 activation。machine-contract instance 因缺 exact active schema reference 与逐路径 output authorization 继续 fail closed。

Sage 临时接管本 Spec 的 GitHub Issue 生成（在 v0.14 阶段 Runtime 不可用），并已落实：

- `spec.md` 之前没有 `<a id="fr-/nfr-XXXX">` 锚点，与现有 `louke/_tools/verify_issue_schema.py` 的 L5/L6 合同不兼容。Sage 在不动现有产品合同的前提下，向 `spec.md` 的 22 个 FR/NFR heading 前各插入一行 `<a id="...">` 锚点；该修改影响 GitHub 渲染和 PR review，但不改需求语义，不引入新需求。`acceptance.md` 的 `ac-fr-/ac-nfr-XXXX` 锚点已于 Sage T-001 修订时就位。
- 22 条 issue 已通过 `gh issue create --repo zillionare/louke` 创建，编号 `#322`—`#343`，标题 `[FR-XXXX] ...` / `[NFR-XXXX] ...`；body 三段（Requirement ID / Spec Link / Acceptance Criteria）符合 `.github/ISSUE_TEMPLATE/feature.yml`。
- 创建新 label `spec:v0.14-004-onboarding-status`（完整名 `spec:v0.14-004-workspace-onboarding-workflow-status` 超出 GitHub 50 字符标签上限，已在 issues.md 记录长度原因）；其余 labels 沿用既有 `Feature`、`v0.14`、`FR-1800`。
- 22 条 issue 已通过 `gh project item-add 20 --owner quantclaws --url <issue>` 全部加入 Project `#20 louke-0.14.0`，由 GraphQL 复核 22/22 命中。Human 在本轮明确选择「沿用 #20」：`gh project view 12 --owner quantclaws` 仍不可解析，但已不再阻塞。
- `python louke/_tools/verify_issue_schema.py --offline --spec-file ... --acceptance-file ... --issues-json <gh export>` 报告 22/22 PASS，覆盖 L1—L8 全字段与双向覆盖。
- raw session：`.louke/raw/26-07-24/sage-v0.14-004-issues.md` 与 `.louke/raw/26-07-24/sage-v0.14-004-devon-handover.md` 含创建序列、label 选择和 Devon M-IMPL 交接清单。

Devon 2026-07-24 已接管 M-IMPL（Human 选项 1）：补 `AC-NFR0501-01` 引用与断言、扩 `louke-ci.yml` 的 `ac-trace` job 同时跑两个 Spec acceptance + `--expected-count 43`、扩 `tests/e2e/run_e2e.py` discovery、`tools/check_ac_traceability.py --expected-count` 参数、`tools/louke_python_release_adapter.py verify-dist` 子命令。Machine-contract instance 仍然 fail closed，等 Runtime 提供 active contract schema reference 与 write scope。
