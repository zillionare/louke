# 最小首次设置、Project 创建引导与 Project Status — Test Plan

- **Spec ID**：`v0.14-004-workspace-onboarding-workflow-status`
- **Created**：2026-07-24
- **Related acceptance**：`.louke/project/specs/v0.14-004-workspace-onboarding-workflow-status/acceptance.md`
- **Related interfaces**：`.louke/project/specs/v0.14-004-workspace-onboarding-workflow-status/interfaces.md`（唯一断言依据，见 §6.5）
- **Acceptance identity**：`sha256:19bf2d0d9f4dc8d3cd27baa126a3a5fd92cc3e153e51c40f4180babbeabaaa81`（44 个唯一 AC）

## 1. 立场与边界（Stance and Boundaries）

### 1.1 黑盒声明（Black-box Statement）

本计划只使用系统外部可观察结果：

- `interfaces.md` 定义的 HTTP API、redirect、错误 envelope 与浏览器 URL；
- 通过可访问名称、文本、状态、focus 和动作可用性观察的 Web UI；
- `.louke/web-users.json`、`.louke/web-setup-state.json`、Runtime SQLite、Git refs/commits、Foundation/operation evidence 和结构化日志；
- 真实构建 wheel/sdist 的 metadata、SHA-256，以及 clean install 后 `lk --version` / `importlib.metadata.version("louke")`；
- 外部 OpenCode、`gh`、`git` stand-in 的协议调用记录，或 protected L3 sandbox 的真实结果。

浏览器 E2E 只通过安装后产品的页面/API产生状态，不直接导入 Louke 内部对象，不预写 Runtime 状态来伪造用户成功旅程。integration 可以预置公开持久化 schema 所声明的历史 fixture，但必须通过公开 HTTP/readback断言接线结果。

### 1.2 不可观察对象（Non-observable Objects）

测试不得直接依赖：

- 内部类层次、私有函数、协程/线程名称、路由 handler 实例；
- 内部缓存、队列、未公开状态变量和客户端组件树/CSS selector结构；
- Runtime 调度算法、Guide prompt/session transport metadata；
- 通过 monkeypatch Louke application核心来替代真实 HTTP/store/projection 行为。

若 AC 需要的结果不能从 `interfaces.md` 出口观察，先修订 interfaces；不得从测试侧窥探私有字段补洞。

### 1.3 作弊模式（CI enforced interception）

| # | 作弊模式 | 本项目症状 | 门禁 |
|---|---|---|---|
| 1 | 为实现改断言 | 旧六步 Setup 仍通过，于是把新 AC 改回旧 step | PR review + AC digest |
| 2 | skip 逃避 | Chromium/`gh`/OpenCode不可用时无 issue地 skip | static scan；required suite零收集/skip失败 |
| 3 | 断言降级 | 只断言HTTP 200，不断言无副作用、identity或可见结果 | Shield review |
| 4 | `try/except: pass` | 吞掉 timeout/conflict | static scan |
| 5 | 过度 mock | mock `Environment Gate` 自己，只验证mock返回passed | boundary review |
| 6 | Ground truth引用实现 | expected timeline由`project_status()`输出生成 | import taboo |
| 7 | 旧 evidence冒充current | 沿用旧43 AC/六步Wizard PASS | traceability count=44 + locked digest |
| 8 | trivial pass | `assert True`或只有`is not None` | static scan |

### 1.4 防护（Safeguards）

1. **AC强制追踪**
   - 每个测试函数首行 docstring/comment 至少含一个当前 `AC-FRXXXX-YY` 或 `AC-NFRXXXX-YY`。
   - `tools/check_ac_traceability.py` 对本 Acceptance 使用 `--expected-count 44`；每个 AC至少被引用一次，测试不得引用未知AC。
   - 同一 AC 如本计划要求多层，runner evidence的`ac_layers`必须出现全部必需层；低层不能替代integration/e2e。
2. **反作弊静态检查**
   - 禁止 sole `assert True/assert 1/is not None`、吞异常、无Issue skip、`tests/ground_truth`导入`louke.*`。
   - integration/e2e零收集、浏览器未启动、stand-in未收到预期真实调用均失败。
3. **测试变更分类**
   - PR必须标识New AC、Spec change或flake/environment issue；“实现不符合Spec所以改测试”禁止。
4. **身份绑定**
   - runner evidence记录 source SHA、wheel digest、Story/Spec/Acceptance digest、profile/runtime和44 AC集合；旧digest evidence不是current。
5. **可测性 fallback**
   - 缺公开出口时记录testability gap并回到 M-DESIGN；不以内部mock让测试先绿。

### 1.5 测试分工（Test Division of Labor）

- **Unit**：Devon；覆盖 manifest/version/identity/redaction/freshness、Project projection、alias、return eligibility、幂等与错误映射的确定性规则。
- **Integration**：Shield；覆盖所有 `modules` ≥2 的接口接线、真实Starlette + 临时事实源 + 外部stand-in，以及失败/边界/恢复。
- **E2E**：Shield；覆盖公开用户主旅程和一个代表性失败修复旅程：首次Setup、empty→Environment→Preview/Create→Dev Docs→Status、节点详情/回拨、兼容返回与升级恢复。
- **Ground Truth**：独立实现者或标准/第三方工具；不得复用被测 Louke projection/adapter。
- **Review**：Shield审查所有测试；Ground Truth和stand-in协议变化需专项审查。

---

## 2. 测试环境（Test Environment）

### 2.1 目录布局

```text
tests/
├── unit/                                      # Devon；现有结构
├── integration/
│   └── v014_workspace_onboarding/            # Shield；本Spec跨模块合同
├── e2e/
│   ├── run-project-venv
│   ├── run_e2e.py
│   ├── playwright-requirements.txt
│   └── v014_workspace_onboarding/            # Shield；安装态Chromium旅程
├── fixtures/
│   └── v014_workspace_onboarding/            # 无秘密固定输入/stand-in脚本/历史快照
└── ground_truth/                              # 不得import louke.*
```

旧 `v014_workspace_onboarding` 路径可以复用 harness、live server与fixture装配，但旧 `identity→repository→dependencies→review→applying` 行为断言必须删除或改写；它们不能作为当前 evidence。

### 2.2 命名约定

- 文件：`test_<surface>__<scenario>.py`。
- 函数：`test_ac_<fr-or-nfr>_<number>_<scenario>`；首行同时写完整 AC token。
- fixture identity使用 `ws_`、`prj_`、`run_`、`att_`、`chk_`、`op_` 前缀；secret使用可检索哨兵 `SECRET_V014004_*`，禁止真实credential。
- 浏览器定位优先 role/name/label/live-region，不依赖DOM层次或生成class。

### 2.3 执行

| 层 | 本地/CI命令 | 隔离与结果 |
|---|---|---|
| Unit | `/tmp/lk-venv/bin/python -m pytest -q tests/unit --cov=louke.runtime --cov-report=xml --cov-report=term-missing --cov-fail-under=95` | clean wheel venv；Runtime coverage≥95% |
| Integration | `tests/e2e/run-project-venv integration` | 必须发现`tests/integration/v014_workspace_onboarding`且非零；默认禁公网 |
| E2E | `tests/e2e/run-project-venv e2e --profile all --runtime both` | local/global安装态，真实Chromium，临时HOME/workspace；runner负责start/readiness/finally teardown |
| L3 smoke | `tests/e2e/run-project-venv real-smoke --profile v014 --runtime local` | protected tag/manual environment；真实OpenCode/GitHub sandbox；不在PR运行 |

执行顺序：quality/trace → build → unit → integration → e2e。所有 push/PR运行L1/L2和stand-in E2E；L3只在受保护release触发。测试不得依赖执行顺序共享状态。

### 2.4 测试数据

| 数据集 | 内容 | 来源/复现 | 用途 |
|---|---|---|---|
| `setup-empty` | project.toml存在、无user/manifest | fixture复制到临时目录 | gate、首用户、真实probe |
| `setup-user-pending` | scrypt测试用户 + v2 pending_model | 固定schema生成；password仅测试进程知道 | refresh/restart/重复用户 |
| `setup-complete-empty` | valid complete + no active Project | fixture builder + fixed clock | Projects empty/New Project |
| `project-active-history` | pinned definition、run/events/attempts、artifact/evidence、回边 | 直接按interfaces公开SQLite/event schema装载；expected sequence独立维护 | Status/attempt/return |
| `project-multi-active` | 两条互相冲突的Project chain | 固定SQLite fixture | fail-closed conflict |
| `legacy-lock` | historical `M-LOCK-1` event与旧身份链 | versioned upgrade fixture | alias/migration/read-only |
| `git-empty-remote` | workspace未init + 可控空remote | 外部Git stand-in/临时bare remote | init/bind/main |
| `git-conflicts` | wrong origin、non-empty no-main、diverged、timeout、partial push | 独立外部fixture | 阻断/reconcile/无覆盖 |
| `gh-matrix` | missing executable、auth fail、unknown host、每个缺scope、全scope | 可执行stand-in固定JSON/text transcript | Environment Gate |
| `opencode-matrix` | list成功/run失败、单模型成功、全失败、timeout、malformed | executable/protocol stand-in，记录argv/prompt | Setup model真实性 |
| `browser-draft` | 同浏览器、第二context、cleared storage、quota error | Playwright browser contexts | draft边界 |
| `secret-canary` | password/token/URL userinfo/provider secret哨兵 | 每run随机后缀 | 全出口扫描 |
| `untrusted-inputs` | HTML/script、控制字符、shell metacharacter、外部/协议相对/跨workspace return URL、跨session CSRF | 固定allowlist边界表 | 文本转义、argv调用、open-redirect/CSRF阻断 |

Unit与E2E使用不同identity/story/version值，避免为固定样本过拟合。所有fixture无真实secret；默认CI不读取开发者`~/.gitconfig`、credential helper、SSH agent、OpenCode/GitHub真实认证。

---

## 3. Ground Truth 方法

### 3.1 原则

| 规则 | 独立真值 |
|---|---|
| 完整workflow stage顺序 | locked `.louke/project/release-contract-bundle.json` 的definition + Acceptance明确13阶段；测试解析原始JSON，不调用Louke projection |
| attempt实际顺序/回边 | fixture中的append-only `sequence/from/to/attempt_id` 数据本身；独立小脚本按sequence排序，不导入Louke |
| Git relation/main | 系统Git的`rev-parse`、`ls-remote`、`merge-base --is-ancestor`直接结果；不使用Louke adapter输出作expected |
| planned/package版本 | PEP 440固定valid/invalid数据表 + artifact标准METADATA/PKG-INFO独立zip/tar提取；不调用被测release adapter提取expected |
| 无重复identity/副作用 | before/after公开文件、SQLite rows、Git refs和stand-in operation ids集合差分 |
| secret不泄漏 | 测试哨兵对workspace、日志、Guide/API body、Story/Git blob、trace/download全量字节搜索 |

本项目不是数值算法产品；不引入额外计算库。简单规则真值来自锁定contract和fixture本身。

### 3.2 Ground Truth 隔离

1. 独立脚本只放 `tests/ground_truth/`，不得 `import louke` 或从Louke读取expected。
2. 只允许stdlib、fixture文件、系统`git`及本计划固定的标准第三方工具。
3. artifact提取脚本直接读取zip/tar metadata，不调用 `tools/louke_python_release_adapter.py`。
4. 变更需Shield专项review；CI static scan阻断import taboo。

---

## 4. 测试范围（Test Scope）

本计划覆盖同目录 `spec.md` 中全部16个FR、5个NFR以及 `acceptance.md` 的44个唯一AC；均为 Valid/Testable/Decided。

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

范围包含四条连续公开旅程：全局Setup gate与最小Setup、登录后的Projects落点、按需New Project创建到Dev Docs、Project Status/attempt详情/回拨。也覆盖旧入口和旧状态升级兼容。精确视觉样式、非Chromium浏览器、操作系统包管理器安装命令、真实生产credential不在范围；其不影响已承诺的可访问状态与动作语义。

---

## 5. 验收门槛（Acceptance Criteria）

1. Runtime unit coverage `>=95%`；新增确定性规则必须有unit证据。
2. `interfaces.md` 每个 `modules`≥2 接口至少有integration happy +关键error/edge覆盖。
3. 所有面向人的主旅程和本计划指定的代表性失败修复旅程有安装态Chromium E2E。
4. 44/44 AC trace closure；未知AC、已删除的旧`NFR-0501`验收项、少层证据或零收集失败。
5. 默认CI L1/L2及stand-in E2E通过；protected L3可运行并在publish前通过。
6. wheel/sdist、wheel安装态、sdist重建安装态版本均与planned/tag/package source canonical identity一致。
7. Setup/Project/return重复、并发、restart和uncertain场景不产生重复身份/副作用，不接受stale revision。
8. 所有secret canary出口扫描为零命中。

---

## 6. 外部依赖分层测试（External Dependency Layered Testing）

### 6.1 三项不可避免约束

| # | 约束 | 结果 |
|---|---|---|
| C1 | PR不能连接生产OpenCode/GitHub | 默认用协议stand-in；真实smoke独立protected |
| C2 | 不能等待真实长超时/运行时长 | 注入外部clock/timeout结果，但通过公开projection观察 |
| C3 | 不能mock Louke核心 | 只替换系统外的OpenCode/gh/git/Guide generator/clock；HTTP、store、projection、gate仍为真实产品 |

### 6.2 Controllable 与 Mock 边界

- 可控替身：`opencode`/`gh`/`git` executable或loopback endpoint、Guide外部生成器、wall clock、GitHub sandbox。
- 不可替换：Setup Gate、Setup Application、Environment Gate、Release Entry、Foundation reconcile、Runtime Projection、Return Application、Guide消息排序/去重、Fact Stores、页面状态绑定。
- 替身只能实现外部协议和记录调用，不能代替Louke判定passed、创建Project、推进run或生成expected projection。

### 6.3 三层金字塔

| Layer | 名称 | 时间/环境 | 证据职责 | Default |
|---|---|---|---|---|
| L1 | Deterministic | fixed clock、temp store、纯规则/HTTP | 边界、状态映射、幂等、stale、redaction | ✅ |
| L2 | Contract stand-in | real app + executable/service stand-ins | 外部调用真实性、跨模块接线、故障/reconcile | ✅ |
| L3 | Real env smoke | real time + protected OpenCode/GitHub sandbox | 最小真实model、auth/scopes、repo/main、Project/Story artifact | release only |

同一AC可以因职责不同同时要求L1/L2/E2E；较低层不替代本计划明确要求的integration或E2E。

### 6.4 测试基础设施责任合同

| Component | 必须提供的外部行为 | 不实现的行为 |
|---|---|---|
| OpenCode stand-in | `models`/`run --model`结果矩阵、延迟、malformed、argv/prompt记录 | 不判定Setup complete，不读取Louke workspace内容 |
| `gh` stand-in | version、auth host/identity/scopes、Project操作结果与稳定resource id | 不判定Environment passed，不创建Louke Project |
| Git stand-in/fixture | init/remote/fetch/push/ls-remote/ref relation和部分失败 | 不替Louke选择remote/main或覆盖策略 |
| Guide generator stand-in | advice success/stream/fail/delay | 不写Runtime状态，不执行正式action |
| Fixed clock | now/advance、触发freshness/elapsed边界 | 不映射workflow status |
| Browser orchestrator | 安装wheel、临时HOME、启动/readiness/teardown、保存trace | 不调用内部对象推进 |

### 6.5 Assertion basis — 与 interfaces.md 闭合

| Interface出口 | 必需覆盖层 | 主要观察 |
|---|---|---|
| `IF-WEB-01` | integration + e2e | 全路由redirect/API 428、无handler副作用、gate解除 |
| `IF-SETUP-01` | unit + integration + e2e | v2 manifest、迁移、可见状态、restart |
| `IF-SETUP-02` | unit + integration + e2e | pre-auth cookie属性、跨session CSRF阻断/session旋转、唯一用户、重复/并发 |
| `IF-SETUP-03` | unit + integration + e2e + L3 | 真实run调用、timeout、passed→complete、无产品副作用 |
| `IF-PROJECT-01` | unit + integration + e2e | empty/active/conflict及动作可用性 |
| `IF-GUIDE-01` | unit + integration + e2e | context、authority顺序、自动建议、去重、无副作用 |
| `IF-ENV-01` | unit + integration + e2e + L3 | click后启动、全step、scope集合、freshness |
| `IF-ENV-02` | unit + integration + e2e + L3 | URL、preview/confirm、main、partial/reconcile/不覆盖 |
| `IF-DRAFT-01` | integration + e2e | same-browser恢复、storage边界、saved/error/clear |
| `IF-PREVIEW-01` | unit + integration + e2e | canonical identity、无副作用、stale/cancel |
| `IF-CREATE-01` | unit + integration + e2e + L3 | 单identity Foundation/Scribe、partial recovery、Dev Docs |
| `IF-IDENTITY-01` | unit + integration + e2e | 全surface同链、migration readonly |
| `IF-STATUS-01` | unit + integration + e2e | 13阶段、attempt历史、active/attention、stale/reconnect |
| `IF-ATTEMPT-01` | unit + integration + e2e | selected≠active、详情/owning/return context |
| `IF-RETURN-01` | unit + integration + e2e | eligibility、影响Preview、Human Confirm、atomic edge |
| `IF-DOC-01` | integration + e2e | latest Story identity、文本安全渲染、return URL allowlist、错误定位/返回上下文 |
| `IF-COMPAT-01` | integration + e2e | 所有alias解析同Project，无第二写面 |
| `IF-AUDIT-01` | unit + integration + e2e | identity/revision/uncertain evidence与secret scan |
| `IF-REL-01` | unit + integration + CI | prepare→build→extract→install identity及全部阻断条件 |
| `IF-TEST-01` | integration + e2e + CI | discovery、installed runtime、service lifecycle/evidence |
| `IF-CI-01` | CI contract integration | DAG、权限、required fail-closed、artifact identity |

---

## 7. CI Gate 与需求级分配

### 7.1 AC traceability命令

```bash
python tools/check_ac_traceability.py \
  --acceptance .louke/project/specs/v0.14-004-workspace-onboarding-workflow-status/acceptance.md \
  --tests tests \
  --expected-count 44
```

该命令是宿主已有入口；Devon只需把workflow中的旧`43`改为`44`。`ac-trace`同时保留 v0.14-001 的独立扫描。

### 7.2 AC → observable interface → required layer(s) → CI job

以下是需求责任分配，不是测试函数清单。

| AC | Observable interface | Required layer(s) | CI gate/job | 分配理由 |
|---|---|---|---|---|
| `AC-FR0001-01` | IF-WEB-01、IF-AUDIT-01 | integration + e2e | integration、e2e-standin、ac-trace | 必须证明多页面/API不能绕过且handler无副作用 |
| `AC-FR0001-02` | IF-WEB-01、IF-SETUP-01 | unit + integration + e2e | unit、integration、e2e-standin | gate完整条件和成功后页面连续性 |
| `AC-FR0101-01` | IF-SETUP-01、IF-SETUP-02 | unit + integration + e2e | unit、integration、e2e-standin | 唯一首用户与refresh/restart是公开主旅程 |
| `AC-FR0101-02` | IF-SETUP-02、IF-AUDIT-01 | unit + integration | unit、integration | 重复/冲突/计数由持久readback证明 |
| `AC-FR0201-01` | IF-SETUP-03、IF-AUDIT-01 | unit + integration + e2e + L3 | unit、integration、e2e-standin、real-smoke | 成功必须走真实run；stand-in与release smoke分别证明协议/真实provider |
| `AC-FR0201-02` | IF-SETUP-01、IF-SETUP-03 | unit + integration + e2e | unit、integration、e2e-standin | 代表性失败→修复→Retry是关键恢复旅程 |
| `AC-FR0301-01` | IF-SETUP-01、IF-SETUP-03、IF-PROJECT-01 | integration + e2e | integration、e2e-standin | complete原子readback和Projects handoff跨模块 |
| `AC-FR0301-02` | IF-SETUP-01、IF-WEB-01 | unit + integration + e2e | unit、integration、e2e-standin | restart复用及写入不确定fail-closed |
| `AC-FR0401-01` | IF-PROJECT-01、IF-STATUS-01 | unit + integration + e2e | unit、integration、e2e-standin | 登录主落点必须浏览器证明 |
| `AC-FR0401-02` | IF-PROJECT-01、IF-IDENTITY-01 | unit + integration | unit、integration | 多active conflict和禁止第二Project属于接线边界 |
| `AC-FR0501-01` | IF-GUIDE-01、IF-PROJECT-01 | unit + integration + e2e | unit、integration、e2e-standin | sidebar context是面向人出口 |
| `AC-FR0501-02` | IF-GUIDE-01、IF-ENV-01 | unit + integration + e2e | unit、integration、e2e-standin | runtime先于自动建议及代表性修复旅程必须真实UI观察 |
| `AC-FR0501-03` | IF-GUIDE-01、IF-AUDIT-01 | unit + integration | unit、integration | chat无authority/副作用由事件与资源差分证明 |
| `AC-FR0601-01` | IF-PROJECT-01、IF-ENV-01 | unit + integration + e2e | unit、integration、e2e-standin | click前后启动边界与通过项折叠为关键UI旅程 |
| `AC-FR0601-02` | IF-ENV-01、IF-GUIDE-01 | unit + integration + e2e | unit、integration、e2e-standin | 一项失败阻断并修复继续需跨模块和代表性UI恢复 |
| `AC-FR0701-01` | IF-ENV-01、IF-AUDIT-01 | unit + integration | unit、integration | executable/auth/每个scope矩阵适合确定性协议测试 |
| `AC-FR0701-02` | IF-ENV-01、IF-GUIDE-01 | integration + e2e + L3 | integration、e2e-standin、real-smoke | 用户诊断/自动建议及真实auth smoke；后续失败不被readiness掩盖 |
| `AC-FR0801-01` | IF-ENV-02、IF-ENV-01 | unit + integration + e2e + L3 | unit、integration、e2e-standin、real-smoke | URL→Human Confirm→readback是关键公开路径 |
| `AC-FR0801-02` | IF-ENV-02、IF-AUDIT-01 | unit + integration + L3 | unit、integration、real-smoke | main/ref冲突、partial与无覆盖需要真实Git边界 |
| `AC-FR0901-01` | IF-DRAFT-01、IF-ENV-01 | integration + e2e | integration、e2e-standin | 浏览器refresh/新context与readiness重验只能从公开浏览器证明 |
| `AC-FR0901-02` | IF-DRAFT-01、IF-AUDIT-01 | integration + e2e | integration、e2e-standin | draft无workspace副作用和跨浏览器边界 |
| `AC-FR1001-01` | IF-PREVIEW-01、IF-AUDIT-01 | unit + integration + e2e | unit、integration、e2e-standin | canonical预览可见且资源差分为空 |
| `AC-FR1001-02` | IF-PREVIEW-01、IF-DRAFT-01 | unit + integration + e2e | unit、integration、e2e-standin | Cancel/stale/re-preview与draft连续性 |
| `AC-FR1101-01` | IF-CREATE-01、IF-IDENTITY-01、IF-DOC-01 | integration + e2e + L3 | integration、e2e-standin、real-smoke | Foundation/Scribe/Dev Docs是核心跨系统主成功旅程 |
| `AC-FR1101-02` | IF-CREATE-01、IF-AUDIT-01 | unit + integration | unit、integration | 重复/并发/partial/unknown由identity及operation差分证明 |
| `AC-FR1201-01` | IF-STATUS-01 | unit + integration + e2e | unit、integration、e2e-standin | 完整13阶段、alias、Issues evidence必须UI可见 |
| `AC-FR1201-02` | IF-STATUS-01、IF-GUIDE-01 | unit + integration + e2e | unit、integration、e2e-standin | running/attention card与authority一致需projection+UI |
| `AC-FR1201-03` | IF-STATUS-01 | unit + integration + e2e | unit、integration、e2e-standin | 独立attempt/回边/全历史导航是核心交互 |
| `AC-FR1301-01` | IF-ATTEMPT-01、IF-STATUS-01 | unit + integration + e2e | unit、integration、e2e-standin | 选中详情与active不变需API及浏览器证明 |
| `AC-FR1301-02` | IF-ATTEMPT-01、IF-DOC-01 | integration + e2e | integration、e2e-standin | owning navigation/return context为公开旅程 |
| `AC-FR1401-01` | IF-RETURN-01、IF-STATUS-01 | unit + integration + e2e | unit、integration、e2e-standin | 只有Runtime允许目标可操作，旧页面不能执行 |
| `AC-FR1401-02` | IF-RETURN-01、IF-AUDIT-01 | unit + integration + e2e | unit、integration、e2e-standin | 危险动作Preview/Cancel/Confirm及原子历史保留必须UI闭合 |
| `AC-FR1501-01` | IF-IDENTITY-01、IF-CREATE-01、IF-DOC-01 | unit + integration + e2e | unit、integration、e2e-standin | New Project→Docs→Status全程同对象 |
| `AC-FR1501-02` | IF-COMPAT-01、IF-IDENTITY-01 | unit + integration + e2e | unit、integration、e2e-standin | 兼容深链不能形成平行页面/写事实 |
| `AC-NFR0001-01` | IF-SETUP-01、IF-CREATE-01、IF-RETURN-01、IF-AUDIT-01 | unit + integration + e2e | unit、integration、e2e-standin | 四个restart checkpoint中至少主journey浏览器重启，全部integration覆盖 |
| `AC-NFR0001-02` | IF-SETUP-02、IF-CREATE-01、IF-RETURN-01、IF-AUDIT-01 | unit + integration | unit、integration | 并发/stale/uncertain应在可控层穷举 |
| `AC-NFR0101-01` | IF-AUDIT-01、IF-DRAFT-01、IF-GUIDE-01、IF-DOC-01 | unit + integration + e2e | unit、integration、e2e-standin | secret canary需扫描所有公开/持久/浏览器artifact |
| `AC-NFR0101-02` | IF-SETUP-03、IF-ENV-02、IF-RETURN-01 | unit + integration | unit、integration | 最小prompt与Human确认前资源差分 |
| `AC-NFR0201-01` | IF-SETUP-03、IF-ENV-01、IF-ENV-02、IF-PREVIEW-01 | unit + integration | unit、integration | timeout/freshness/fingerprint变化矩阵 |
| `AC-NFR0201-02` | IF-GUIDE-01、IF-ENV-01、IF-SETUP-03 | unit + integration + e2e | unit、integration、e2e-standin | 诊断质量及Guide故障不遮Runtime结果需代表性UI观察 |
| `AC-NFR0301-01` | IF-SETUP-01、IF-ENV-01、IF-PREVIEW-01、IF-STATUS-01、IF-RETURN-01 | integration + e2e | integration、e2e-standin | keyboard和非颜色状态只能从浏览器可访问树证明 |
| `AC-NFR0301-02` | IF-DRAFT-01、IF-GUIDE-01、IF-STATUS-01 | integration + e2e | integration、e2e-standin | focus/input/layout/全历史可达需支持viewport/zoom组合 |
| `AC-NFR0401-01` | IF-IDENTITY-01、IF-STATUS-01、IF-GUIDE-01、IF-COMPAT-01 | unit + integration + e2e | unit、integration、e2e-standin | 同revision跨surface一致与旧缓存readback |
| `AC-NFR0401-02` | IF-SETUP-01、IF-IDENTITY-01、IF-STATUS-01、IF-COMPAT-01 | unit + integration + e2e | unit、integration、e2e-standin | v1/历史run/M-LOCK升级、只读迁移及无重复对象 |

### 7.3 GitHub Actions gate合同

| Trigger | Mandatory jobs | 附加job |
|---|---|---|
| pull request | quality、ac-trace、build-artifacts、artifact-verify、unit matrix、integration、e2e-standin、install-matrix、required | 无secret；无real smoke/publish |
| push `main`/`releases/**` | 同PR | 无publish，除非另有合法tag |
| tag `v*` | 全部required | protected real-smoke；通过后publish |
| manual CI | 全部required | 只有提供合法release tag且protected审批后才real-smoke/publish |

稳定 required check为唯一 `Louke CI / required`。`required` 使用 `if: always()`，任何mandatory job的failed/cancelled/timed_out/skipped/missing/unknown都不能成功。publish不得重建artifact，不得消费不同source SHA或未验证digest。

### 7.4 Release/version验证顺序

1. 从 `.louke/project/project.toml:[project].version` 读取Human planned canonical identity；tag是`v<canonical>`表示。
2. release event调用 `IF-REL-01 prepare`，先比较planned/tag，再准备`pyproject.toml:[project].version`；非release build只校验当前source。
3. `python -m build --wheel --sdist`真实构建，要求恰好一个wheel和一个sdist。
4. 独立从每个artifact提取version/SHA-256，与planned/tag/package source逐一比较。
5. 从wheel clean install和sdist重建wheel clean install，复核`lk --version`及metadata。
6. 只有`artifact_versions_verified` evidence current且`Louke CI / required`与real-smoke通过才允许publish。

缺/非法identity、prepare/source写入失败、build失败、artifact缺失/多余/无法提取、任一不匹配、安装/运行出口不匹配或结果不确定均阻断。

---

## 8. Judge Review Checklist

- [x] 测试策略覆盖Setup绕过、虚假模型通过、stale readiness、重复外部资源、Project authority、历史丢失、危险回拨、secret和版本漂移。
- [x] 44个AC均有`interface → required layer(s) → CI job`分配。
- [x] 本计划不列测试函数清单；§7.2仅是需求级责任分配。
- [x] 反作弊、零收集、AC count和ground-truth import gate已定义。
- [x] fixture/stand-in可离线复现，真实credential仅用于protected L3。
- [x] 目录、命令、local/global安装态和runner生命周期已确定。
- [x] Ground Truth来源独立，不引用Louke输出生成expected。
- [x] `interfaces.md`全部21个出口都有至少一种覆盖，跨模块接口均含integration。
- [x] 用户主旅程和关键恢复/回拨旅程有E2E；错误矩阵主要下沉integration。
- [x] wheel/sdist及全部适用安装/运行版本出口均纳入publish阻断门禁。
