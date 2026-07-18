---
spec_id: v0.14-001-workflow-reflow-spec
bound_spec_digest: sha256:a627a43b7ad1f2834b14cebb8c8f78af949676722e9319059d02bd0e7426f596
bound_acceptance_digest: sha256:992fcdc3b7a70cedc2f16b867bfd313b4cc64bd645350c202141c72f09747556
bound_story_digest: sha256:e04e88b336c7f08a3f67ef40354fa35c3e78ec66935805aa6f2da7272dfd0634
bound_doc_index_digest_sha256: sha256:384084747a9a67bca6eba544711da7e8de2e3a65883d41fa99ed081019ca528b
revision: 2
status: Draft v2 (pending Prism re-review)
---

# v0.14 Workflow Reflow（启动至 M-LOCK-1 + Issues）— Test Plan

## 0. Metadata

- **spec_id**: `v0.14-001-workflow-reflow-spec`
- **spec_status**: `Draft v2 / pending Prism re-review`
- **created**: `2026-07-18`
- **bound_spec_digest**: `sha256:a627a43b7ad1f2834b14cebb8c8f78af949676722e9319059d02bd0e7426f596`
- **bound_acceptance_digest**: `sha256:992fcdc3b7a70cedc2f16b867bfd313b4cc64bd645350c202141c72f09747556`
- **bound_story_digest**: `sha256:e04e88b336c7f08a3f67ef40354fa35c3e78ec66935805aa6f2da7272dfd0634`
- **bound_doc_index_digest_sha256**: `sha256:384084747a9a67bca6eba544711da7e8de2e3a65883d41fa99ed081019ca528b`
- **approval fixture**: `m-lock-1-decision.json`；只作为已锁定 digest/decision 的输入证据，不触发 Runtime、Issue 或其它副作用。
- **related acceptance**: `.louke/project/specs/v0.14-001-workflow-reflow-spec/acceptance.md`
- **interfaces status**: M-ARCH / Spec 3 尚未交付；本初稿只声明 acceptance 所需的可观察结果，§10 列出的出口须在 M-ARCH review 后闭合。
- **template conformance**: 本文复用 `.louke/templates/test-plan.md` 的黑盒边界、环境、Ground Truth、外部依赖分层、CI gate 与 review checklist；按本 Spec 要求重排为 §0–§11，未使用 `Valid / Testable / Decided` 列。

## 1. Test Strategy Overview

### 1.1 黑盒立场与风险覆盖

断言只落在公开 Web/API、`lk serve` 进程结果、持久化 store 的公开查询/只读 SQL 证据、受控文档 bytes、Git ref/tree/commit SHA、stand-in 外部调用账本，以及 GitHub-compatible stand-in 的 Issue/Project 查询结果。不得通过预注入 Louke 内部 Python 对象推进 run，不得把 Agent transcript 或 Agent 的“完成”文本当作结果。测试可替换 OpenCode/GitHub **外部边界**，但不得 mock Runtime 的状态转移、CAS、revision、review、gate 或 reconcile 核心。

| requirement | high-level risk（非新增需求） | planned layers |
|---|---|---|
| FR-0100 | 错误 readiness 放行或重复初始化 | contract, integration, smoke |
| FR-0200 | preview 产生副作用、冲突值被静默选择 | contract, integration |
| FR-0300 | 单活跃 release 竞争导致重复 Backlog/run | contract, integration |
| FR-0400 | 错误 main 基线或部分 foundation 被当作完成 | integration, contract |
| FR-0500 | Story 初始化覆盖已有 bytes 或混淆 commit | integration, contract |
| FR-0600 | 客户端/Agent 绕过 Runtime 推进流程 | unit, contract, integration |
| FR-0700 | Scribe 输入缺失、建议越权推进 | contract, integration |
| FR-0800 | 清理 branch 误伤用户修改 | integration |
| FR-0900 | 回复重派、无变更假完成、提交混入文件 | integration, contract |
| FR-1000 | stale write 覆盖、脏编辑丢失、错误 revert | contract, integration |
| FR-1100 | Human 编辑后被伪报 PASS | contract, integration |
| FR-1200 | author/reviewer 串 session 或旧 digest PASS | contract, integration |
| FR-1300 | 非法 Spec 被提交或越过 30 条门禁 | unit, contract, integration |
| FR-1400 | Human/Lex 评审 revision 漂移 | contract, integration |
| FR-1500 | Agent 或非法目标移动流程 | contract, integration |
| FR-1600 | Acceptance 覆盖缺口或上游变化后旧 PASS | unit, contract, integration |
| FR-1700 | stale/非 Human 批准、锁后仍可写 | contract, integration |
| FR-1800 | Issue/Project 重复、前缀误匹配、部分成功误报 | contract, integration, real smoke |
| FR-1900 | timeout 后重复 dispatch、假/越权结果获接收 | contract, integration, real smoke |
| FR-2000 | 受控 commit 混入或回退无关工作区 | integration |
| FR-2100 | 重启后跳步、重复副作用或未知结果自动 PASS | integration, stand-in smoke |
| NFR-0100 | 状态/event 单边提交与竞争双成功 | unit, contract, integration |
| NFR-0200 | digest 链断裂或 secret 泄漏 | contract, integration |
| NFR-0300 | 进程内测试通过但安装产物公开旅程失败 | e2e（Spec 4）, stand-in/real smoke（Spec 4） |

### 1.2 主要测试原则与防作弊

1. Ground Truth 由 Python stdlib `hashlib`、`sqlite3` 只读查询、`git` CLI、fixture 中预先声明的资源 identity 和 stand-in 调用账本独立计算；expected 不从被测响应回填。
2. 所有并发场景用 barrier 同时释放请求，并断言成功数、HTTP code、row/resource count；不以 sleep 推断顺序。
3. 每个测试实现首行引用规范化 AC ID（例如 `AC-FR0100-01`）；计划中的 `AC-1` 引用在落码时转换为该格式。CI 只使用真实契约：
   ```bash
   lk agent archer ci-scan \
     --acceptance .louke/project/specs/v0.14-001-workflow-reflow-spec/acceptance.md \
     --tests tests/
   ```
4. 禁止 `assert True`、吞异常、以唯一 `is not None` 断言、无 Issue 的 skip、mock Runtime 核心、修改 locked story/spec/acceptance 来让测试通过。
5. 单元/contract 由 Devon 补全；跨边界 integration 与后续 browser e2e 由 Shield 补全；Prism 审核断言强度。Ground Truth 变更须由非实现者重点审查。

## 2. Test Layers & Tooling

### 2.1 分层与边界

| layer | 工具与入口 | 允许替换 | 禁止事项 | 默认 CI |
|---|---|---|---|---|
| unit | `pytest` 收集；纯 digest、parser、validation、CAS 决策 | clock/UUID、纯外部响应值 | 以内部对象预置完整 workflow 后宣称 AC 通过 | 是，部分规则 |
| contract/API | `pytest` 收集；`httpx` 或 Starlette `TestClient` 通过公开 HTTP 路由 | OpenCode/GitHub protocol stand-in | patch orchestrator/store 结果 | 是 |
| integration | 权威 `[integration]` runner：`tests/e2e/run-project-venv integration`（`framework = "pytest"`, `cwd = "."`）；干净 tmp Git repo + SQLite store + in-memory OpenCode adapter + 真实 `git` CLI；服务从 `lk serve --project-root <tmp>` 或等价公开 server assembly 启动 | OpenCode/GitHub 外部边界 | 直接调用 `WorkflowOrchestrator.apply_command` 代替用户/Agent HTTP 行为；另造 integration 命令 | 是，本次主要层 |
| e2e | 权威 `[e2e]` runner：`tests/e2e/run-project-venv e2e --profile all --runtime both`（`framework = "pytest"`, `cwd = "."`）；`lk serve` live server + Playwright/Chromium，全部关键动作经页面 | CI 可用 protocol-faithful stand-in | 用 API 代替关键导航/点击/填写；另造 e2e 命令 | **deferred to Spec 4** |
| real smoke | live `lk serve` + 真实 OpenCode + GitHub 测试 repo/Project | 不替换目标外部服务 | 进入默认 PR CI、使用生产凭据 | Spec 4 release cutover 前手动 |

项目已有 Python `>=3.11`、`pytest` markers、Starlette/httpx、`tests/unit`、`tests/integration`、`tests/e2e` 和 Chromium e2e 先例。测试框架沿用 `pytest`；浏览器层沿用 Playwright/Chromium，但依赖精确版本和 installed-wheel runner 由 Spec 4/既有 release contract 负责，本计划不新增依赖或修改 `pyproject.toml`。仓库不存在独立 `[meta].test_framework` 文件；事实源已是 `.louke/project/project.toml` 的 `[meta].test_framework = "pytest"`。

### 2.2 Stand-in 与真实边界

- **默认 CI**：`LOUKE_OPENCODE_BACKEND=mock` 或 protocol-faithful HTTP stand-in；GitHub stand-in 记录 query/create/link/ack，支持确定性注入 timeout、ack loss、零/多候选、字段冲突与 partial success。报告必须标识 `stand-in`。
- **真实 smoke**：显式 marker `real_opencode`/release marker，要求隔离测试账户、测试 repo/Project 和人工提供凭据；报告标识 `real`。缺环境不是产品 PASS，必须单列为 not-run/infra failure。
- **受控 Agent 结果**：Sage/Lex/Scribe dispatch 失败、timeout 或 session 丢失后，只读取 M-ARCH 定义的受控结果出口；不得解析自由文本“PASS”或假定 Runtime 已接收结果。

### 2.3 环境、数据与执行

宿主 `.louke/project/project.toml` 的权威合同为：`[integration].run = "tests/e2e/run-project-venv integration"`、`framework = "pytest"`、`paths = ["tests/e2e", "tests/integration", "tests/fixtures", "tests/ground_truth"]`、`cwd = "."`；`[e2e].run = "tests/e2e/run-project-venv e2e --profile all --runtime both"`、`framework = "pytest"`、`paths = ["tests/e2e", "tests/fixtures", "tests/ground_truth"]`、`cwd = "."`。在 `tests/integration/` 下新增 `v0.14-workflow-reflow/` 子目录并由 `[integration]` runner 收集；单元/contract 由 `pytest` 收集；Spec 4 browser 资产位于 `tests/e2e/` 下并仅由 `[e2e]` runner 收集。不得另造执行命令。fixture 使用权威 paths 已包含的 `tests/fixtures/` 与 `tests/ground_truth/`，内容包括：bare declared remote、clone workspace、canonical Story/Spec/Acceptance template、locked digest manifest、setup candidates、authenticated Human cookie、OpenCode task/result scripts、GitHub resource catalog/call ledger、secret canaries。执行顺序为 unit/contract → integration runner → Spec 4 e2e runner。所有测试默认 offline、随机 loopback port、独立 HOME/XDG/GIT_CONFIG、独立 SQLite 和 Git remote。

Ground Truth 不需要独立算法实现：digest 用 stdlib 直接从 fixture bytes 计算；Git identity 用 `git rev-parse`/`git diff-tree`；Issue/Project count 用 stand-in 公共查询；event/row count 用公开 ledger/API，或 M-ARCH 明确允许的 SQLite 只读 schema。SQLite 只读查询只作为 fallback；如未在 M-ARCH 公开为接口，则记为 testability gap 而非 PASS，不得偷看私有表猜 schema。

## 3. Per-FR / Per-NFR Test Plans

> 本节按 24 个 FR/NFR 组织 24 个 requirement-level `TP-*` scenario contract group，不是测试代码清单；`1a/1b/...` 是同一 requirement-level TP 的合同 variants。一个 TP group 可在 pytest 中参数化覆盖其全部 linked AC；各变体使用隔离 fixture 生命周期。M-ARCH 未闭合的观察口见 §10。

### FR-0100

- **coverage_intent**: readiness 必须先于写副作用，重复启动复用有效 setup。
- **test_layers**: contract, integration, smoke
- **tests**: `TP-FR-0100-1`
  - **input fixtures**: 缺 provider/OpenCode workspace、全 READY manifest workspace、失败 dependency workspace、外部 create ledger。
  - **pre-conditions**: tmp Git workspace 干净；ledger/store row count 为 0 或 fixture 基线。
  - **steps**: 分别执行 `lk serve` 并经 HTTP 打开入口；READY fixture 连续启动两次。
  - **expected**: 缺失项页面逐项含 `BLOCKED` 与非空 remediation，release submit disabled；READY 两次可访问入口且 repository/Project/branch identity bytes 相等、create 增量 0；失败进程 exit code 非 0、stderr 含 dependency 名和 remediation，WorkflowRun/create count 均为 0。
  - **cleanup**: 终止 server，删除 tmp HOME/workspace，断言无远程写。
- **linked_acs**: `FR-0100 AC-1..AC-3`
- **linked_risks**: `R-05`, `R-07`
- **required_evidence**: process exit/stderr、readiness HTTP/DOM、foundation identity、run/create counts。

### FR-0200

- **coverage_intent**: preview 无写入，Human 决策绑定 revision，reconcile 不模糊选择。
- **test_layers**: contract, integration
- **tests**: `TP-FR-0200-1`
  - **input fixtures**: 单一候选、owner 冲突、Project 零/多/字段冲突候选及外部 ledger。
  - **pre-conditions**: 未确认 setup；所有资源数量有已知基线。
  - **steps**: GET preview；对冲突 fixture 重启；以当前 revision 确认并重复；运行冲突 reconcile。
  - **expected**: preview 每字段显示 value/provenance 且确认前四类写调用为 0；冲突重启后仍 `waiting_human` 且候选 bytes 不变，WorkflowRun 数与 repository、release Project、branch、项目配置四类外部修改数均为 0；确认 manifest 含 revision/actor/selection/all provenance/stable IDs/evidence，重复确认资源 count 不增；零/多/冲突结果不 complete、不按 title 复用并显示精确详情。
  - **cleanup**: teardown stand-in；删除 tmp workspace。
- **linked_acs**: `FR-0200 AC-1..AC-4`
- **linked_risks**: `R-05`, `C-08`
- **required_evidence**: preview response、manifest、resource counts、operation ledger、`waiting_human` 状态。

### FR-0300

- **coverage_intent**: 输入校验和单活跃 release 约束必须在副作用前且并发幂等。
- **test_layers**: contract, integration
- **tests**: `TP-FR-0300-1`
  - **input fixtures**: 空 story、非法 version、active main release、固定 request identity/content digest。
  - **pre-conditions**: 记录 Project/run/Backlog/ref/spec-dir 基线。
  - **steps**: 请求 preview；随后以 barrier 重复/并发确认同一 blocked request；重启再查 Projects。
  - **expected**: 非法输入的页面字段级错误可定位，Project、WorkflowRun、Backlog entry 和 release branch count 均不变；竞争确认后恰一 Backlog row，第二 Project/run/ref/spec-dir 均不存在；重启后原 story/version/reason/time/source identity 字节相等。
  - **cleanup**: stop server；删除 tmp refs/workspace。
- **linked_acs**: `FR-0300 AC-1..AC-3`
- **linked_risks**: `R-05`
- **required_evidence**: HTTP response、Backlog row count/digest、Project/run count、Git ref 与目录不存在证明。

### FR-0400

- **coverage_intent**: foundation 只能基于已刷新且已证明的权威 main，partial/unknown 必须 reconcile。
- **test_layers**: integration, contract
- **tests**: `TP-FR-0400-1`
  - **input fixtures**: bare remote 中 merge/ahead/behind/diverged/unknown 图、local-main mismatch、Project create 后 ack loss、错误 branch 起点。
  - **pre-conditions**: 记录 full refs/SHA M；无 M-STORY task。
  - **steps**: 经 Web 确认 preview；注入各关系和 ack loss；修复 ref 后重新检查。
  - **expected**: refresh/证明失败时页面显示 full ref、SHA、关系/错误及 remediation，foundation 非 PASS，branch/spec-dir/M-STORY count 不增；通过时 Project/run/release Project/branch/spec-dir 各一且 `git merge-base`/`rev-parse` 证明起点=M，evidence 含 stable identity；ack loss 后先 query 并复用同一 node ID；错误起点不能完成，确认不能绕过，修复后起点仍精确 M。
  - **cleanup**: 删除 stand-in Project、tmp remote/workspace。
- **linked_acs**: `FR-0400 AC-1..AC-4`
- **linked_risks**: `R-04`, `R-05`, `B-01`, `C-08`
- **required_evidence**: Git full refs/SHA/graph、foundation ledger、Project node ID、task/resource counts。

### FR-0500

- **coverage_intent**: canonical template 初始化、commit identity 与冲突不覆盖。
- **test_layers**: integration, contract
- **tests**: `TP-FR-0500-1`
  - **input fixtures**: template T、设想 S、matching/conflicting pre-existing story。
  - **pre-conditions**: release foundation 完成；记录 existing bytes/commit count。
  - **steps**: 初始化；以相同 identity 重试 matching 与 conflicting variants；跟随浏览器响应。
  - **expected**: story 指定位置含 S 且 T 其余章节存在，evidence 含 input/file digest、actor、commit SHA；matching retry digest/SHA 相同且 commit 增量 0；conflict 返回非成功响应且 body 含 `STORY_INITIALIZATION_CONFLICT`，bytes 不变（status code 待 M-ARCH/interfaces）；成功 URL/页面显示同一 run、`M-STORY`、revision。
  - **cleanup**: 删除 tmp branch/workspace。
- **linked_acs**: `FR-0500 AC-1..AC-3`
- **linked_risks**: `R-04`
- **required_evidence**: story bytes/digest、Git SHA/count、HTTP code/error、URL 与页面 identity。

### FR-0600

- **coverage_intent**: Runtime 是唯一状态写者，stale/非法动作无副作用且状态可重建。
- **test_layers**: unit, contract, integration
- **tests**: `TP-FR-0600-1`
  - **input fixtures**: M-SPEC revision R；Web/Agent/document 三种越权请求；waiting/blocked/review snapshots。
  - **pre-conditions**: 记录 run/artifact/gate/Issue bytes/count。
  - **steps**: 请求直接到 M-LOCK-1；刷新页面并重启服务。
  - **expected**: 越权请求返回非成功响应且 body 含 `WORKFLOW_STATE_CONFLICT`，step/R/artifact/gate/Issue 不变（status code 待 M-ARCH/interfaces）；刷新与重启后页面字段逐字等于持久化出口的 step/status/revision/writer/round/task-session/verdict/last-error。
  - **cleanup**: stop server；删除 tmp store。
- **linked_acs**: `FR-0600 AC-1..AC-2`
- **linked_risks**: `R-01`, `R-07`
- **required_evidence**: HTTP response、before/after digests/counts、Project read model、restart snapshot。

### FR-0700

- **coverage_intent**: Scribe task 输入/权限完整，建议不替代 Human 裁决。
- **test_layers**: contract, integration
- **tests**: `TP-FR-0700-1`
  - **input fixtures**: first/next-round M-STORY manifests、Scribe Go/Park/No-Go result、stale/Agent/invalid decisions。
  - **pre-conditions**: current Story revision R；M-SPEC task count 0。
  - **steps**: 启动 M-STORY dispatch；提交受控建议；尝试非法裁决后由 authenticated Human 对 R 裁决。
  - **expected**: 仅一个 Scribe task，Chat 绑定 run/R、编辑 disabled、write scope 仅 story；公开 manifest 含 AC-1 全部字段和适用 feedback digests；建议后仍 `waiting_for_human`/M-STORY 且 M-SPEC=0；非法裁决返回非成功响应，body 含 `WORKFLOW_STATE_CONFLICT` 且记录为空（status code 待 M-ARCH/interfaces），合法记录含 actor/R/value/time。
  - **cleanup**: stop stand-in session/server；删除 tmp store。
- **linked_acs**: `FR-0700 AC-1..AC-3`
- **linked_risks**: `R-03`, `R-07`, `C-01`
- **required_evidence**: task manifest/digest、session ID、DOM disabled、decision row、task counts。

### FR-0800

- **coverage_intent**: Park/No-Go 幂等终止；只有可证明隔离时删除未使用 local ref。
- **test_layers**: integration
- **tests**: `TP-FR-0800-1`
  - **input fixtures**: clean initialization-only branch；unattributed commit、dirty file、remote ref variants。
  - **pre-conditions**: Human 对当前 Story 作 Park/No-Go；记录 user bytes/refs。
  - **steps**: 执行退出两次；对不安全 variants 执行一次。
  - **expected**: Backlog 恰一 row，显式包含 Story identity/digest、decision、reason、actor、source run，Project 对应终态且 M-SPEC=0；安全 local ref 首次不存在、二次 no-op；不安全 variant 为 `needs_attention` 并列出 identity，refs/user bytes 不变，stand-in/git trace 中无 force/reset。
  - **cleanup**: 删除 tmp refs/workspace。
- **linked_acs**: `FR-0800 AC-1..AC-3`
- **linked_risks**: `R-02`, `R-04`
- **required_evidence**: Backlog row、Project/task status、Git refs/bytes、command audit。

### FR-0900

- **coverage_intent**: Human 回复先持久化再幂等发送，无变更完成被拒，handoff commit 纯净。
- **test_layers**: integration, contract
- **tests**: `TP-FR-0900-1`
  - **input fixtures**: Scribe session S、correlation ID、unchanged/changed Story、send ack loss。
  - **pre-conditions**: Human 已 Go；记录 event seq、transcript count、Git parent。
  - **steps**: 回复并重试发送；提交无变更完成；修改 Story 后提交 handoff。
  - **expected**: `reply_persisted.seq < reply_dispatched.seq` 且同 correlation/message bytes，重试后逻辑回复/transcript/S 各一；无变更返回非成功响应且 body 含 `STORY_CHANGE_REQUIRED`，仍 authoring、review task=0（status code 待 M-ARCH/interfaces）；变更 commit tree 仅 story，evidence 含 digest/parent/SHA/task/attempt/session，review event 序号晚于 commit evidence。
  - **cleanup**: stop session/server；删除 tmp repo。
- **linked_acs**: `FR-0900 AC-1..AC-3`
- **linked_risks**: `R-03`, `R-07`, `C-02`
- **required_evidence**: ordered events、transcript query、HTTP conflict、Git tree/SHA、task counts。

### FR-1000

- **coverage_intent**: 单写 lease + CAS + dirty guard；违规 patch 只可精确隔离，否则 needs_attention。
- **test_layers**: contract, integration
- **tests**:
  - `TP-FR-1000-1a` — valid-lease + same-token 竞争
    - **input fixtures**: Human/Agent 两个 writer，均有有效 lease authority 且携带同一 current version token。
    - **pre-conditions**: 记录 accepted revision bytes/digest、current token 与 workspace/index snapshot。
    - **steps**: barrier 同时释放两个保存请求并等待两者完成。
    - **expected**: 恰一 save 成功；败者 HTTP 409，body 含 `DOCUMENT_WRITE_CONFLICT` 与 current token；disk bytes 精确等于赢家内容，成功副作用一次。
    - **cleanup**: release lease；删除 tmp repo/store。
  - `TP-FR-1000-1b` — all-wrong-lease
    - **input fixtures**: 两个 writer 均携带错误/过期 lease，version token 与 fixture current token 已知。
    - **pre-conditions**: 记录 accepted revision bytes/digest、current token 与 workspace/index snapshot。
    - **steps**: barrier 同时释放所有错误 lease 保存请求并等待完成。
    - **expected**: 成功数为 0；全部返回非成功响应，body 均含 `DOCUMENT_WRITE_CONFLICT` 与 current token；disk bytes、revision 与 index bytes 不变。此 variant 的 status code 未由 acceptance 锁定，待 M-ARCH/interfaces。
    - **cleanup**: 清除错误 lease 请求；删除 tmp repo/store。
  - `TP-FR-1000-1c` — dirty / isolated / needs_attention
    - **input fixtures**: browser dirty flag、isolatable/non-isolatable disk edits、unrelated index bytes。
    - **pre-conditions**: 记录 accepted revision bytes/digest 与 workspace/index snapshot。
    - **steps**: 请求 Agent lease；经 M-ARCH 出口触发/观察违规写保护。
    - **expected**: dirty 时 lease 未授予且提示 save/cancel、Agent write 不改文件；可隔离时仅违规 patch 消失、其它 bytes/index 相等并产生 reread notice；基线缺失/来源不明时 `needs_attention` 且 command audit 无 repository-wide revert。
    - **cleanup**: release lease；删除 tmp repo/store。
- **linked_acs**: `FR-1000 AC-1..AC-3`
- **linked_risks**: `R-01`, `R-02`, `C-03`
- **required_evidence**: HTTP 409/body、lease/revision outlet、file/index hashes、notice、status/command audit。

### FR-1100

- **coverage_intent**: Human review 信号必须与编辑/discussion/current digest 一致。
- **test_layers**: contract, integration
- **tests**: `TP-FR-1100-1`
  - **input fixtures**: current revision、one-byte edit、canonical open/reopen/closed threads、unsaved edit。
  - **pre-conditions**: Human 持有 review 权；verdict count 0。
  - **steps**: 编辑或用 Web 创建/回复 thread；尝试 `no comment`；分别提交 comment/open/unsaved/clean-no-comment variants。
  - **expected**: 页面显示 revision、edited、open/reopen count，`lk discuss query` 可识别 thread；edited 时按钮 disabled，伪造请求返回非成功响应且 body 含 `HUMAN_REVIEW_EDITED`、无 PASS（status code 待 M-ARCH/interfaces）；前三种 variant 无 PASS，只有 clean current digest + no-comment + 0 open/reopen 产生一条 digest-bound Human PASS。
  - **cleanup**: 删除 fixture discussion/repo。
- **linked_acs**: `FR-1100 AC-1..AC-3`
- **linked_risks**: `R-01`, `R-06`
- **required_evidence**: DOM、discussion parser JSON、HTTP response、verdict rows/digest。

### FR-1200

- **coverage_intent**: Story Human/Sage 独立、同 revision 双 PASS，多轮保持 author session 且旧 verdict stale。
- **test_layers**: contract, integration
- **tests**: `TP-FR-1200-1`
  - **input fixtures**: handoff C/D、Human edit D2、review failures、Scribe revision D3。
  - **pre-conditions**: Scribe session 已记录；review rows 为空。
  - **steps**: 启动首轮；Human 修改后 dispatch Sage；提交任一失败并由 Scribe 响应；最终双 PASS D3。
  - **expected**: Human/Sage 均绑定 C/D，Sage session != Scribe session，旧 digest verdict 不计；Sage input 含 Human diff 且绑定 D2，两类 revision 为不同 commit；原 Scribe session 不变，旧 verdict=`stale`，round+1 仅审 D3，双 PASS D3 后才进入 M-SPEC。
  - **cleanup**: stop sessions/server；删除 tmp repo/store。
- **linked_acs**: `FR-1200 AC-1..AC-3`
- **linked_risks**: `R-01`, `R-06`, `R-07`, `C-04`
- **required_evidence**: session IDs、manifest digests/diff、commit SHAs、round/verdict ledger、step。

### FR-1300

- **coverage_intent**: M-SPEC 只在 Story 双 PASS 后由 Sage 受控起草，结构/规模失败不启动 Lex。
- **test_layers**: unit, contract, integration
- **tests**: `TP-FR-1300-1`
  - **input fixtures**: approved Story D；valid Spec；empty/duplicate/missing Source/metadata/31-unit variants。
  - **pre-conditions**: Story Human/Sage PASS 当前 D；Lex task=0。
  - **steps**: 启动 authoring；Sage 返回前尝试 Human save；提交各草案。
  - **expected**: URL 为 spec、控件 disabled，Sage input 含 D/review/template/revision/single write path；Human save 返回非成功响应且 body 含 `DOCUMENT_WRITE_CONFLICT`，bytes 不变（status code 待 M-ARCH/interfaces）；valid 仅提交 spec 并开放编辑；invalid 返回非成功响应，body 含 requirement/line，31-unit body 含 `SPEC_SCOPE_TOO_LARGE`，Lex=0 且留在 Sage 修订（status code 待 M-ARCH/interfaces）。
  - **cleanup**: stop session/server；删除 tmp repo。
- **linked_acs**: `FR-1300 AC-1..AC-3`
- **linked_risks**: `R-01`, `R-07`, `C-01`
- **required_evidence**: URL/DOM、task manifest、HTTP errors、Git tree、requirement count、Lex count。

### FR-1400

- **coverage_intent**: Human/Lex 同 revision 独立评审，语义通过后才格式验收。
- **test_layers**: contract, integration
- **tests**: `TP-FR-1400-1`
  - **input fixtures**: committed R、Human R2 diff、Lex PASS/non-PASS、open threads、format failure。
  - **pre-conditions**: current step M-SPEC；M-ACC task=0。
  - **steps**: 启动双 review；Lex 无/有 lease 写 thread；Human 改 R2 后 dispatch Lex；结束失败/通过 rounds 并运行 formatter。
  - **expected**: 双 review 绑定 R；无 lease HTTP 409 + `DOCUMENT_WRITE_CONFLICT`，有 lease thread 可解析；Lex 输入 R2+Human diff，R 结果 stale 且不能组合；失败意见回原 Sage、new revision、round+1；仅 no-comment+Lex PASS+0 open/reopen+同 digest 进入格式验收；格式失败显示 file/line/rule、留 M-SPEC、M-ACC=0，通过后才 M-ACC。
  - **cleanup**: stop sessions；删除 tmp repo/store。
- **linked_acs**: `FR-1400 AC-1..AC-4`
- **linked_risks**: `R-01`, `R-06`, `R-07`, `C-04`
- **required_evidence**: lease HTTP、discussion JSON、manifest/digest、verdict/round、format result、task count。

### FR-1500

- **coverage_intent**: 仅 Human 可选择阶段声明的上游目标，历史保留且下游 evidence stale。
- **test_layers**: contract, integration
- **tests**: `TP-FR-1500-1`
  - **input fixtures**: M-SPEC/M-ACC runs、合法/非法 target、Agent return suggestion。
  - **pre-conditions**: 记录 revision、Git log、artifact/review/format/approval ledger。
  - **steps**: 打开控件并提交非法 target；Human 确认合法 target；仅提交 Agent 建议不确认。
  - **expected**: M-SPEC 仅列 M-STORY，M-ACC 仅列 M-SPEC/M-STORY；非法返回非成功响应且 body 含 `UPSTREAM_RETURN_TARGET_INVALID`，revision 不变（status code 待 M-ARCH/interfaces）；合法返回后历史行仍存在，T 及下游 verdict/format/approval=`stale|superseded`，step=T、Git log 未删；Agent 建议仅显示 waiting Human，step/revision 不变。
  - **cleanup**: 删除 tmp store/repo。
- **linked_acs**: `FR-1500 AC-1..AC-3`
- **linked_risks**: `R-06`, `C-05`
- **required_evidence**: target DOM/API、HTTP conflict、ledger before/after、Git log、step/revision。

### FR-1600

- **coverage_intent**: Acceptance 继承当前上游 digests、完整覆盖 requirement，并复用独立 review 规则。
- **test_layers**: unit, contract, integration
- **tests**: 以下 variants 与 `TP-FR-1400-1` 的 Human/Lex independent review 协议显式并列；M-ACC 不采用较弱的 review 条件。
  - `TP-FR-1600-1a` — M-ACC authoring、coverage 与 independent review binding
    - **input fixtures**: current Story/Spec digests、valid Acceptance、missing requirement section/no-reason variants、Human/Lex review fixtures。
    - **pre-conditions**: Spec semantic/format 当前 PASS；M-LOCK-1 不可见。
    - **steps**: 启动 M-ACC；执行 coverage validation；对 committed Acceptance revision R 启动 Human/Lex review；令 Lex 分别无 lease/有 lease 写 thread。
    - **expected**: URL 为 acceptance、Human readonly，Sage task 绑定两个 digest 且沿用 Sage context；缺 section/no reason 返回非成功响应且 body 明列 requirement ID，approve 不可见并回 Sage（status code 待 M-ARCH/interfaces）；Human/Lex 均绑定同一 revision R；Lex 无 lease 写入 HTTP 409 且 body 含 `DOCUMENT_WRITE_CONFLICT`，获得 lease 后 thread 可由 canonical parser 解析。
    - **cleanup**: stop review sessions；删除 variant tmp repo/store。
  - `TP-FR-1600-1b` — Human edited guard
    - **input fixtures**: committed Acceptance R、Human one-byte edit、伪造 `no comment` 请求。
    - **pre-conditions**: Human/Lex independent review 已绑定 R；PASS count 为 0。
    - **steps**: Human 编辑后从客户端直接提交 `no comment`。
    - **expected**: 返回非成功响应且 body 含 `HUMAN_REVIEW_EDITED`，Human verdict 不为 PASS（status code 待 M-ARCH/interfaces）。
    - **cleanup**: 删除 variant discussion/repo。
  - `TP-FR-1600-1c` — thread/verdict/digest joint gate
    - **input fixtures**: open/reopen thread、Lex PASS/non-PASS、Human `comment`/`no comment`、digest match/mismatch、format result。
    - **pre-conditions**: 双 review 绑定同一 current revision；M-LOCK-1 不可见。
    - **steps**: 分别结束 open/reopen、失败与 clean-pass rounds；通过时运行 canonical formatter。
    - **expected**: 任一 open/reopen thread、Human 非 `no comment`、Lex 非 PASS 或 digest mismatch 均无 PASS 且不进入格式验收；仅 Lex PASS + Human `no comment` + 0 open/reopen + digest match 才进入格式验收；review 与格式均通过后显示 `M-LOCK-1`。
    - **cleanup**: stop review sessions；删除 variant repo/store。
  - `TP-FR-1600-1d` — rework round 与上游失效
    - **input fixtures**: review failure、Sage response revision R2、upstream Story/Spec digest mutation。
    - **pre-conditions**: Sage author session identity 已记录；R 上存在 review verdict。
    - **steps**: 将完整意见返回 Sage 并提交 R2；启动下一轮；随后改变任一上游 digest。
    - **expected**: 原 Sage session 沿用、round 加 1，R 的旧 verdict 标为 `stale` 且新一轮只审 R2；上游变化后 Acceptance verdict stale、approve 隐藏。
    - **cleanup**: stop Sage/review sessions/server；删除 tmp repo/store。
- **linked_acs**: `FR-1600 AC-1..AC-3`
- **linked_risks**: `R-01`, `R-06`, `R-07`, `C-04`
- **required_evidence**: URL/DOM、task/session identity、validator response、verdict/step/gate visibility。

### FR-1700

- **coverage_intent**: gate 绑定当前三文档与 joint/doc-index digest，仅 authenticated Human 可批；批准后服务端锁定。
- **test_layers**: contract, integration
- **tests**: `TP-FR-1700-1`
  - **input fixtures**: locked story/spec/acceptance bytes、`m-lock-1-decision.json` digest values、incomplete reviews、authenticated Human/Agent、stale challenge/revision/digest。
  - **pre-conditions**: 不修改三文档；Issue count 基线 0。
  - **steps**: 尝试 blocked approve；由文件独立计算三 digest 和 doc-index binding 并查询 gate/run；提交非法 approvals；Human 批准后 PUT 三文档。
  - **expected**: blocker 时按钮 disabled、请求 HTTP 409 + `WORKFLOW_STATE_CONFLICT`、列 blocker、Issue=0；gate 页面/出口的 S/P/A/joint 与锁定输入相等，当前 run 的 `doc_index_digest_sha256` 精确等于 `sha256:3840...528b`，全程不写三文档；Agent/old challenge/wrong revision/digest HTTP 409 + `WORKFLOW_STATE_CONFLICT` 且 pending；有效批准记录 actor/time/challenge/revision/digests，后续每个写请求 HTTP 423 + `REQUIREMENTS_LOCKED` 且 bytes/digests 不变。
  - **cleanup**: 删除 tmp copy/store；源三文档 hash 再次等于 pre-test hash。
- **linked_acs**: `FR-1700 AC-1..AC-3`
- **linked_risks**: `R-01`, `R-05`
- **required_evidence**: independent hashes、doc-index/joint digest、gate record、HTTP 409/423、Issue count、before/after bytes。

### FR-1800

- **coverage_intent**: 一个有效 FR/NFR 精确一个 Issue + 一个 Project item，且严格 identity reconcile。
- **test_layers**: contract, integration, real smoke
- **tests**: `TP-FR-1800-1`
  - **input fixtures**: locked 24-unit docs、stand-in repository/Project、ack loss、partial failure、wrong token/body/link/Project candidates。
  - **pre-conditions**: gate pending/approved variants；记录 Issue/item counts。
  - **steps**: 批准前请求 split；批准后执行全部 requirement operation；重复/并发/重启；注入 partial failure 后修复；运行 mismatch reconcile。
  - **expected**: 批准前拒绝且 counts 不变；批准后每个 24 unit 恰一 Issue/item，title UTF-8 bytes 以精确 `[{ID}]` 开头，body 含 ID、locked spec/acceptance section URLs，item 指向 manifest Project；同 identity 重试/ack loss query 复用；partial 页面逐 ID 为 `created|linked|failed|uncertain` 且成功 number 不变、全 linked 前不完成；任一 mismatch 不复用，返回稳定 `*_CONFLICT` 或 `needs_attention` 并列字段，消歧前不 create 第二候选。
  - **cleanup**: CI stand-in reset；real smoke 仅删除标记为本次测试的隔离资源并保存 ledger。
- **linked_acs**: `FR-1800 AC-1..AC-5`
- **linked_risks**: `R-05`, `C-06`, `C-08`
- **required_evidence**: 24 requirement IDs、Issue title/body/number、Project node/item ID、operation identity/joint digest、query/create/link ledger、status/error。

### FR-1900

- **coverage_intent**: task/attempt/session 持久绑定；timeout 先 reconcile；仅受控且 schema/digest/role/scope 匹配结果可生效。
- **test_layers**: contract, integration, real smoke
- **tests**: `TP-FR-1900-1`
  - **input fixtures**: Scribe/Sage/Lex manifests、active-turn timeout、valid controlled result、wrong role/attempt/manifest/artifact/schema/scope results、lost session。
  - **pre-conditions**: dispatch ledger/task evidence 基线；document/revision/verdict hashes 已记录。
  - **steps**: dispatch roles；timeout 后重试；通过待 M-ARCH adapter 查询受控结果；提交各 invalid result；确认 lost 后恢复。
  - **expected**: evidence 含 run/step/role/artifact/write scope/output contract/attempt/session，author 与 reviewer session 不同；status/result reconcile 前 dispatch count 不增，valid existing result 被回收、running 继续等待；invalid 结果=`rejected` 且 revision/verdict/doc bytes 不变；lost/interrupted 原 attempt + new attempt/new session + 相同 authority input digests，任何 attempt 不自动 PASS。
  - **cleanup**: stop all sessions/server；reset stand-in ledger/store。
- **linked_acs**: `FR-1900 AC-1..AC-4`
- **linked_risks**: `R-03`, `R-07`, `C-01`
- **required_evidence**: task/attempt/session rows、manifest/result digest、dispatch/query counts、rejection reason、before/after artifact state。

### FR-2000

- **coverage_intent**: Git revision 严格 allowlist，冲突不 reset/checkout/force，无关 index/bytes 不变。
- **test_layers**: integration
- **tests**: `TP-FR-2000-1`
  - **input fixtures**: staged/unstaged/untracked/other-doc changes、controlled spec change、index conflict、branch move、unprovable source。
  - **pre-conditions**: 保存 `git status --porcelain=v2`、index blob IDs、file hashes、parent SHA。
  - **steps**: 通过 workflow 提交 spec；查询 evidence；执行三类冲突 variant。
  - **expected**: `git diff-tree` 仅 spec，其他 bytes/index 与快照相等；evidence 含 expected digest/parent/result SHA/actor/run/round/task 且 ref SHA=记录 SHA；冲突返回非成功响应且 body 含 `CONTROLLED_COMMIT_CONFLICT`（status code 待 M-ARCH/interfaces），下一 review 未启动，Git command audit 无 reset/checkout/force push且无关 hashes 不变。
  - **cleanup**: 删除 tmp repo。
- **linked_acs**: `FR-2000 AC-1..AC-3`
- **linked_risks**: `R-02`, `R-04`, `C-07`
- **required_evidence**: porcelain/index/file hashes、commit tree/SHA、revision evidence、HTTP error、command audit。

### FR-2100

- **coverage_intent**: 任意中断从持久化事实恢复，unknown 外部结果先 reconcile，客户端断开不复制任务/资源。
- **test_layers**: integration, stand-in smoke
- **tests**: `TP-FR-2100-1`
  - **input fixtures**: review run with lease/task/Human wait、external unknown operation 的 completed/not-happened/ambiguous variants、browser/OpenCode disconnect。
  - **pre-conditions**: 记录 step/revision/round/digest/lease/task/session/gate/error 与 dispatch/resource counts。
  - **steps**: kill/restart `lk serve`；执行 recovery scan；重新打开 Project/Chat。
  - **expected**: restart 后所有记录字段相等且 completed dispatch count 不增；unknown 不 PASS/不推进，证明完成补记同 resource ID，证明未发生以同 idempotency identity 重试，ambiguous 为 `needs_attention` 并显示 operation/target/effects；客户端断开后页面恢复 revision/task/session 且 task/resource count 不增。
  - **cleanup**: stop server/stand-in；删除 tmp store/workspace。
- **linked_acs**: `FR-2100 AC-1..AC-3`
- **linked_risks**: `R-03`, `R-05`, `R-07`, `C-08`
- **required_evidence**: pre/post snapshots、dispatch/resource ledger、operation status/id、Project/Chat read model。

### NFR-0100

- **coverage_intent**: state/event 原子提交、CAS 单赢家、四类副作用幂等、资源 identity 严格匹配。
- **test_layers**: unit, contract, integration
- **tests**: `TP-NFR-0100-1`
  - **input fixtures**: M-ARCH 定义的 transaction fault boundary、same expected revision/token barrier、Backlog/Project/gate/Issue duplicate requests、resource zero/multi/conflict/fuzzy candidates。
  - **pre-conditions**: 每 variant 独立 store；公开 row/resource count 基线。
  - **steps**: commit 前/后注入进程终止并恢复；并发请求；查询最终状态；执行 resource reconcile。
  - **expected**: commit 前 state/event 均不存在、commit 后两者均存在且 revision 相同；竞争恰一成功，败者 HTTP 409 + current revision/token + 稳定 `*_CONFLICT`，副作用一次；每 logical identity 恰一 entry/run/gate decision/Issue；零/多/conflict/fuzzy 返回 `*_CONFLICT` 或 `needs_attention`，列 kind/namespace/fields 且 create/reuse 增量 0，仅唯一精确候选复用。
  - **cleanup**: 删除 fault-process/tmp DB；reset stand-in。
- **linked_acs**: `NFR-0100 AC-1..AC-4`
- **linked_risks**: `R-01`, `R-03`, `R-05`, `C-08`
- **required_evidence**: transaction row counts/revisions、HTTP responses、logical identity/resource ledger、conflict fields。

### NFR-0200

- **coverage_intent**: 全链路可双向追踪且任何出口不泄漏原始 secrets。
- **test_layers**: contract, integration
- **tests**: `TP-NFR-0200-1`
  - **input fixtures**: setup→Issue golden stand-in run、locked Issue、unique credential/token/cookie/provider-secret canaries。
  - **pre-conditions**: canary 仅注入外部输入；记录三文档与 doc-index locked digests。
  - **steps**: 按 run 读取有序 evidence；从 Issue 正查与 Spec section 反查；枚举 manifest/docs/events/logs/errors/commit messages/Agent inputs。
  - **expected**: ledger 覆盖 setup/step/revision/review/gate/task/commit/external operation，每行含适用 run/step/attempt、actor/time/correlation/input-output digest；正反向得到同一 Story/Spec/Acceptance/doc-index digests、ID、Issue URL、Project identity且历史未改写；每个原始 canary匹配数=0，只可见 redacted/identity/digest。
  - **cleanup**: 删除 canary workspace/logs；reset stand-in。
- **linked_acs**: `NFR-0200 AC-1..AC-3`
- **linked_risks**: `R-02`, `R-04`, `R-07`, `C-07`
- **required_evidence**: ordered ledger、bidirectional identity links、digest equality、recursive byte scan report。

### NFR-0300

- **coverage_intent**: 安装产物仅经 `lk serve` + Web 完成公开旅程，并区分 stand-in 与 real 证据。
- **test_layers**: e2e, stand-in smoke, real smoke（均 deferred to Spec 4）
- **tests**: `TP-NFR-0300-1`
  - **input fixtures**: installed wheel、clean Git workspace、Chromium、stand-in/real isolated accounts、故障注入 scenario manifest。
  - **pre-conditions**: 未预写 Runtime state；产品进程从安装 wheel 启动；外部 counts 已记录。
  - **steps**: 仅用 Web 完成 setup→Issue link；注入 edit/discussion/rework/CAS/restart/disconnect/GitHub ack loss；在 release cutover 跑最小 real smoke。
  - **expected**: timeline 逐步有公开 evidence且无 CLI workflow advance/内部 Python 调用；每类故障得到合同规定 conflict/recovery/reconcile、旧 verdict 不推进、task/Issue/item 不重复；报告 mode 分别为 `stand-in`/`real`，real 记录 recoverable session ID、Issue number、Project node/item ID。
  - **cleanup**: teardown server/browser；删除 wheel env/tmp workspace；隔离账户资源按 manifest 清理。
- **linked_acs**: `NFR-0300 AC-1..AC-3`
- **linked_risks**: `R-01..R-07`, `B-01`, `C-01..C-08`
- **required_evidence**: wheel metadata/server path、Playwright trace、timeline、fault report、mode、session/Issue/Project IDs。

## 4. Issue Tracking & Project Linking Tests

本节不新增测试 ID；由 `TP-FR-1800-1`、`TP-NFR-0100-1`、`TP-NFR-0200-1` 共同约束：

1. 锁定 Spec 的 21 FR + 3 NFR 各自独立映射为一个 Issue；不能按章节聚合。最终查询必须得到 24 个不同 requirement identity、24 个匹配 Issue、24 个对应 Project item。
2. title 的**字节前缀**为 UTF-8 `[{ID}]`，首个 requirement token 精确等于 ID；title 相似不能成为复用依据。body 同时核对 ID、锁定 Spec anchor 与 Acceptance anchor，Project item 必须属于 foundation manifest 指定 Project。
3. reconcile identity 至少受已锁定合同约束为 repository + spec_id + requirement ID + joint digest；外部资源的精确字段集合由 M-ARCH 按 resource kind 定义，不在本计划假定统一 tuple。
4. 重复、barrier 并发、服务重启、create 成功后 ack 丢失、link partial success 均从公开 query/call ledger 断言；不得通过真实 `gh` 进入默认 CI。real GitHub 只属于 Spec 4 release smoke。

## 5. Reconcile / Recovery / Conflict Tests

- `TP-FR-1000-1a`：valid-lease + same-token 竞争 → 单赢家；败者 HTTP 409 + `DOCUMENT_WRITE_CONFLICT` + current token，bytes 等于赢家。`TP-FR-1000-1b`：all-wrong-lease → 零成功；全部非成功响应 + `DOCUMENT_WRITE_CONFLICT` + current token，bytes 不变；1b status code 待 M-ARCH。
- `TP-FR-0600-1`：非法阶段推进 → 非成功响应 + `WORKFLOW_STATE_CONFLICT`，run/artifact/gate/Issue 不变；status code 待 M-ARCH。`TP-NFR-0100-1`：expected revision/token 竞争错配 → HTTP 409 + stable `*_CONFLICT` + current revision/token，run/event 不产生单边变化。
- `TP-FR-0700-1`：stale/Agent/候选外裁决 → 非成功响应 + `WORKFLOW_STATE_CONFLICT`，裁决记录为空；status code 待 M-ARCH。
- `TP-FR-0500-1`：Story identity bytes 冲突 → 非成功响应 + `STORY_INITIALIZATION_CONFLICT`；status code 待 M-ARCH。
- `TP-FR-0900-1`：Agent 无文档变化却完成 → 非成功响应 + `STORY_CHANGE_REQUIRED`；status code 待 M-ARCH。
- `TP-FR-1100-1`：Human 编辑后伪造 no-comment → 非成功响应 + `HUMAN_REVIEW_EDITED`；status code 待 M-ARCH。
- `TP-FR-1300-1`：Sage 返回前 Human save → 非成功响应 + `DOCUMENT_WRITE_CONFLICT`；31 个 FR+NFR → 非成功响应 + `SPEC_SCOPE_TOO_LARGE`；两者 status code 待 M-ARCH。
- `TP-FR-1500-1`：非法上游目标 → 非成功响应 + `UPSTREAM_RETURN_TARGET_INVALID`；status code 待 M-ARCH。
- `TP-FR-1600-1a`：Acceptance coverage 缺口 → 非成功响应且明列 requirement ID；status code 待 M-ARCH。`TP-FR-1600-1b`：Human edited 后伪造 no-comment → 非成功响应 + `HUMAN_REVIEW_EDITED`；status code 待 M-ARCH。
- `TP-FR-1700-1`：非法/stale gate → HTTP 409 + `WORKFLOW_STATE_CONFLICT`；锁后写 → HTTP 423 + `REQUIREMENTS_LOCKED`。
- `TP-FR-2000-1`：Git 来源/index/ref 冲突 → 非成功响应 + `CONTROLLED_COMMIT_CONFLICT`；status code 待 M-ARCH。
- `TP-FR-1900-1` / `TP-FR-2100-1`：服务重启、网络中断、OpenCode session 丢失时，先按受控 task/operation identity query；dispatch/create 计数不得增加，除非已证明未发生或原 attempt 确认 lost。Issue 同理先核验 title/body/Project 后复用。

## 6. Installed-wheel Smoke Tests（deferred to Spec 4）

本计划只保留 `TP-NFR-0300-1` 的验收合同，不在 Spec 2 重复设计 runner、wheel build/install、browser provisioning、真实账号管理或 release evidence 归档。Spec 4 必须补齐：

1. 从 clean checkout 构建并安装 wheel，证明产品子进程导入 installed distribution 而非 checkout。
2. Playwright/Chromium 通过 live `lk serve` 执行完整 Web golden journey 与 fault journey。
3. 默认 CI stand-in 报告和 release 前 real OpenCode/GitHub 最小 smoke；真实环境缺失不能记作 PASS。
4. installed-wheel 的版本/tag/artifact identity、切换证据与归档合同属于 Spec 4，不由本计划新增。

## 7. Out-of-Scope

- `flow.md` L96+ 的任何能力；M-LOCK-1/Issue 关联后的 design/dev/release/archive 工作流。
- mandatory lifecycle hooks、项目自定义 shell hooks、PR 流程、Issue/CI report interruption matrix、cross-workflow-definition migration。
- backlog 中 bounded waiver、no-new-debt adoption、通用 return-upstream、旧 CLI 缺位合同、旧 active run 迁移。
- 多用户审批、移动端、完整离线、Workbench 视觉重做、任意文件锁服务。
- 处理“Spec 2 先于 Spec 3”的顺序异常。本计划明确 pending M-ARCH；不假装 lease schema、attempt schema 或 result adapter 已锁定。
- 本阶段不写 architecture.md/interfaces.md、不写 production/test code、不触发 Runtime/Agent/GitHub dispatch。

## 8. Test Environment & Idempotency

### 8.1 Clean workspace contract

每条 `TP-*` 从新的 `tmp_path` Git workspace、bare remote、随机 server port、隔离 HOME/XDG/Git config、独立 SQLite、全新 stand-in ledger 开始。fixture 只能通过文件、环境变量、外部 protocol 或公开 setup/Web/API 装入；不得 import 内部对象预写 run。每个测试在 cleanup 中无条件停止 server/session/browser，删除 tmp 资源，并比对宿主 checkout 的 `git status` 与 locked 三文档 hash 未变化。

### 8.2 Fixtures

- `workspace_clean`, `workspace_dirty_matrix`, `bare_declared_remote`
- `locked_requirements_bundle`（只读 copy + 三 digest + doc-index digest + decision JSON）
- `authenticated_human_session`, `agent_identity`
- `opencode_standin`（session/status/message/result/fault ledger）
- `github_standin`（repository/Project/Issue/item/query/create/link/ack ledger）
- `workflow_fault_manifest`（只描述外部 timeout/ack loss/process kill；transaction 内 fault seam 待 M-ARCH）
- `secret_canaries`, `canonical_templates`, `setup_candidate_matrix`

所有重复/并发测试以 logical identity 和最终 row/resource count 判定幂等；每个 fixture teardown 后 count 回到基线。测试数据是合成且无敏感信息；real smoke 凭据只从 CI secret store 注入且不可进入 artifact。

## 9. Test Acceptance Criteria for this Plan

1. 24 个 FR/NFR 均有一个 `TP-*` scenario contract；78 条 acceptance AC 均被其同名 requirement 的 TP 引用，落码时转换为 `AC-FRXXXX-YY` / `AC-NFRXXXX-YY`。
2. 每个 TP 均声明 input fixtures、pre-conditions、steps、可机器断言 expected、cleanup、evidence；不存在“通过即可”软断言。
3. 所有 expected 只使用 §1 的公开观察面；M-ARCH 尚未定义的 outlet 明列 §10，不以内部 mock 或猜测 schema 填补。
4. 默认 CI 无网络、无需 `gh`/真实 OpenCode；stand-in/real 报告明确区分。real smoke 和 installed-wheel e2e deferred 到 Spec 4。
5. 测试实现通过 `lk agent archer ci-scan ...` 后仍须由 Prism 检查断言强度；覆盖率沿用项目 `fail_under = 95`，但不能用覆盖率替代 AC closure。
6. Ground Truth 独立于被测实现；如新增 `tests/ground_truth/`，不得 import `louke.*`。
7. 实施前必须用仅含一个规范化引用（例如 `AC-FR0100-01`）的最小 fixture 执行 §1.2 所列 `lk agent archer ci-scan` 契约并确认其接受 `AC-FRXXXX-NN` / `AC-NFRXXXX-NN` 格式；命令非 0 或引用未被识别时，本计划的落码验收不得 PASS。

## 10. Deferred to M-ARCH / Spec 3

以下是 **M-ARCH review checklist**，不是本计划为 Devon 指定的实现/schema：

1. **D-ARCH-01 — write ownership/lease outlet**：lease holder/id、document、run、revision/version token 的公开请求与观察契约；dirty browser 如何阻止交接。
   - → `TP-FR-1000-1a/1b/1c`、`TP-FR-1300-1`、`TP-FR-1400-1`、`TP-FR-1600-1a`
2. **D-ARCH-02 — 违规 patch 隔离算法**：accepted baseline 的可得性、何时可证明“只移除违规 patch”、何时必须 `needs_attention`；不得 repository-wide revert。
   - → `TP-FR-1000-1c`
3. **D-ARCH-03 — semantic task/attempt persistence**：task、attempt、active turn、session、correlation、lost/interrupted、dispatch/query count 的外部 schema 与重启语义。
   - → `TP-FR-0700-1`、`TP-FR-0900-1`、`TP-FR-1200-1`、`TP-FR-1300-1`、`TP-FR-1400-1`、`TP-FR-1600-1a/1d`、`TP-FR-1900-1`、`TP-FR-2100-1`
4. **D-ARCH-04 — OpenCode controlled-result validation adapter**：Runtime 如何从 Sage/Lex/Scribe 的 role/task/attempt/manifest/artifact/schema/scope 验证受控结果；dispatch 失败后测试只读此出口，不读自由文本假完成。
   - → `TP-FR-0700-1`、`TP-FR-0900-1`、`TP-FR-1200-1`、`TP-FR-1300-1`、`TP-FR-1400-1`、`TP-FR-1600-1a/1c/1d`、`TP-FR-1900-1`
5. **D-ARCH-05 — transaction fault seam**：NFR-0100 AC-1 在 state/event 原子提交前后如何由进程级 deterministic seam 注入崩溃，且不让测试直接调用 store 私有方法。
   - → `TP-NFR-0100-1`
6. **D-ARCH-06 — resource-specific reconcile identity**：repository/branch/Project/Issue 各自的 provider namespace、stable ID 与可比较字段；不强制统一 tuple。
   - → `TP-FR-0200-1`、`TP-FR-0400-1`、`TP-FR-1800-1`、`TP-FR-2100-1`、`TP-NFR-0100-1`
7. **D-ARCH-07 — workflow read model/events**：Project 页面所需 writer/round/task/session/verdict/error、ordered evidence、row count/digest equality 的公开 API 或获准只读 DB contract。
   - → `TP-FR-0100-1`、`TP-FR-0200-1`、`TP-FR-0600-1`、`TP-FR-0900-1`、`TP-FR-1200-1`、`TP-FR-1400-1`、`TP-FR-1600-1a/1c/1d`、`TP-FR-1700-1`、`TP-FR-2100-1`、`TP-NFR-0100-1`、`TP-NFR-0200-1`
8. **D-ARCH-08 — joint/doc-index digest contract**：joint digest 的 canonical encoding，以及当前 run 如何公开绑定已锁定 `doc_index_digest_sha256`；测试不得改写 story/spec/acceptance 来验证。
   - → `TP-FR-1700-1`、`TP-FR-1800-1`、`TP-NFR-0200-1`
9. **D-ARCH-09 — Git command/evidence outlet**：受控 commit allowlist、禁止 reset/checkout/force 的可观察 audit 与 conflict response。
   - → `TP-FR-0400-1`、`TP-FR-0500-1`、`TP-FR-0800-1`、`TP-FR-0900-1`、`TP-FR-1000-1c`、`TP-FR-1500-1`、`TP-FR-2000-1`
10. **D-ARCH-10 — stand-in protocol controls**：GitHub/OpenCode fault scenarios 如何从测试外部控制，而不在生产接口中加入 test-only workflow bypass。
    - → `TP-FR-0100-1`、`TP-FR-0200-1`、`TP-FR-0400-1`、`TP-FR-1800-1`、`TP-FR-1900-1`、`TP-FR-2100-1`、`TP-NFR-0100-1`、`TP-NFR-0300-1`

M-ARCH 完成后应逐项把 §3 的“待 M-ARCH 出口”绑定到 interfaces.md；如果无法提供公开出口，相应 AC 标记 testability gap 并回到设计 review，不得由 Shield 猜测。

## 11. Test Plan Acceptance / Lex + Prism Review

### 11.1 Review chain

1. Archer 提交本 Draft v2，并保持绑定的 story/spec/acceptance bytes 不变。
2. **Lex semantic review**：核对 24 requirement/78 AC 的语义、scope L1-L95、B-01/C-01..C-08 与 deferred 边界；Lex 不作技术最终批准。
3. Archer 仅修订 `test-plan.md` 回应意见并递增 revision。
4. **Prism S 档 technical review**：作为 M-TESTPLAN 唯一技术批准者，验证可执行性、断言强度、stand-in 边界、cleanup、无内部 bypass 和 M-ARCH deferred 完整性。Shield 可提供 executability feedback，但不批准；Sage 不得批准 M-TESTPLAN。
5. Lex 或 Prism reject 时回到 Archer 修订；不得推进 M-ARCH gate，不得通过修改 locked 三件套消除 test-plan 冲突。两者所需 review artifact 必须绑定当前 test-plan digest/revision。

### 11.2 Technical review checklist（Prism）

- [ ] 风险、24 个 requirement 和 78 个 AC 闭合。
- [ ] 每个 scenario contract 有确定输入、步骤、expected、cleanup 与 evidence。
- [ ] 黑盒断言未依赖内部类、状态机、队列或 test-only workflow bypass。
- [ ] test data 可复现，CI 默认 offline，real smoke 明确分离。
- [ ] lease、controlled result、attempt、fault seam、reconcile identity、read model 均未越权预设实现。
- [ ] Spec 4 installed-wheel/browser/real smoke deferred 清晰，未被记为本阶段 PASS。
- [ ] `lk agent archer ci-scan` 与 AC docstring convention 明确。
