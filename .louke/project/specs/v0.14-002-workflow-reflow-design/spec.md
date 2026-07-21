# 工作流重构：技术设计与规范性 Agent 合同 — 需求规格

- **规格 ID**：`v0.14-002-workflow-reflow-design`
- **关联 Story**：`STR-1403`
- **创建日期**：2026-07-19
- **状态**：草稿
- **有效 FR 数量**：28（上限 30）
- **Revision identity**：`Lex round 1 revision`
- **Revision digest**：`PLACEHOLDER（由 Runtime 计算）`

> **职责边界**：本文只规定从 `M-REQ-APPROVAL` 到 `M-DESIGN` 完成的产品行为与规范合同。用户叙事见 `story.md`，阶段细节见 `flow.md`，可观察断言见 `acceptance.md`。
>
> **规范性工件集**：本 Spec revision 不只由 `story.md`、`spec.md`、`acceptance.md`、`flow.md`、Test Plan、Architecture、Interfaces 和 machine contracts 构成；凡本 Spec 声明受影响的 canonical Agent prompt source 也属于同一规范性工件集，必须共同 revision、review、digest 和 baseline。依据 Story `D-03`，002 受影响的 canonical prompt sources 是且仅是 `louke/agents/Archer.md` 与 `louke/agents/Prism.md`；未列入的 prompt 不属于本 Spec 的规范性变化。实际 prompt revision 与 bundle digest 在实施本 Spec 时生成；本草稿不预填伪 digest。
>
> Agent prompt 可规定角色语义、判断原则和 schema reference，但不得成为结构化输入输出 schema 的唯一来源。机器 schema 由程序拥有、版本化并通过 Runtime task manifest 传递。

## 功能需求

<a id="fr-0100"></a>
### FR-0100 M-DESIGN 入口与 Revision 身份

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-01`

Runtime 只可在当前 Story、Spec、Acceptance 已通过 `M-REQ-APPROVAL`，全部依赖 current 且宿主项目 workspace/base commit 可确认时进入 `M-DESIGN`。它必须建立唯一 design revision，绑定 run、release identity、requirements digests、base commit、宿主项目事实快照、actor 和 attempt；缺失、冲突或 stale 输入必须阻止 dispatch。

---

<a id="fr-0200"></a>
### FR-0200 宿主项目事实盘点与自主技术选择

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-02`

Runtime 必须向 Archer 提供当前需求、代码库结构、语言/运行时、构建与测试入口、版本源、artifact、部署/安装出口、既有 CI/hooks、兼容约束和已确认外部能力。Archer 必须优先兼容真实且有效的既有方案；全新项目或确无方案时，Archer 应依据产品目标和成熟工程惯例自主决定技术栈，不得向 Human 请求技术选择，也不得把任何工具自身仓库的配置泛化为宿主项目默认。

---

<a id="fr-0300"></a>
### FR-0300 设计写入授权与工件归属

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-01` / `BS-13`

Runtime 必须以 manifest 向 Archer 授予当前 revision 的单写者范围，列明可编辑设计文档、machine contracts 和受影响 canonical prompts，禁止 Git/阶段/GitHub 副作用。每轮前后必须归属 diff；越界或来源不明的变化不能静默纳入设计 baseline。

---

<a id="fr-0400"></a>
### FR-0400 Test Plan 设计

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-03` / `BS-04`

Archer 必须为全部有效 FR/NFR 与 Acceptance 设计 Test Plan。每个 AC 至少绑定 observable interface、required layer(s)、宿主测试入口、fixture/environment、CI gate/job、trace metadata 和选择理由；其中 observable interface 与执行入口必须解析到 Interfaces 中同一真实 interface identity，且其命令、路径与状态语义必须和对应 machine contract 及 Architecture 一致。允许一个 AC 需要多个层，但不允许以“已有某个测试引用”替代测试层闭包。主用户旅程、跨模块交互和异常传播必须按风险获得 integration/e2e 覆盖；缺失映射、orphan 或任一方向冲突必须阻止 baseline，并定位具体 FR/AC、interface、Architecture anchor 与 machine contract。

---

<a id="fr-0500"></a>
### FR-0500 Architecture 设计

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-03`

Architecture 必须定义满足当前需求的组件边界、依赖方向、数据与控制流、状态/一致性、故障边界、安全与信任边界、迁移/兼容策略和关键技术决定，并追溯到需求与宿主项目事实。Interfaces 声明的状态、权限、错误和恢复语义必须分别由 Architecture 中可追溯的组件、状态机制和安全/信任或故障边界承载，并与相关 Test Plan 观察点及 machine contract 的命令、路径、状态语义一致；缺失承载、orphan 或双向冲突必须阻止 baseline 并定位相关 FR/AC、interface、architecture anchor 与 contract。Architecture 不得把未决定的技术问题留给 Devon 临场选择。

---

<a id="fr-0600"></a>
### FR-0600 Interfaces 设计

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-03`

Interfaces 必须覆盖本功能真实挂载到宿主产品的入口与完整操作路径，包括适用的 UI、CLI、API、事件、文件/配置、错误和恢复出口；对每个接口定义稳定的真实 identity，以及输入、输出、状态、权限、错误语义、兼容性和可观察结果。该 identity 必须被 Test Plan 的 observable interface/执行入口解析，并将状态、权限、错误和恢复语义双向映射到 Architecture 的组件、状态机制及安全/信任或故障边界；相关 machine contract 的命令、路径和状态语义必须一致。若某类入口确实不适用，可不创造虚假界面，但必须从用户旅程和项目事实得出可审查理由；缺失、orphan 或双向冲突必须阻止 baseline 并定位相关 FR/AC、interface 与 contract。

---

<a id="fr-0700"></a>
### FR-0700 Machine Contract Registry

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-05` / `BS-11`

Runtime/program 必须拥有并提供可发现、有版本且可 schema 校验的 machine contract schema registry；每个权威 schema 具有 schema identity、version 与 digest。required contract kinds 是 `integration-test`、`e2e-test`、`pre-commit`、`github-actions-ci`、`release-version`、`build-artifact` 与 `publish-recovery`。Archer 只生成符合 registry 中 active 权威 schema 的 contract instance，不得随 instance 携带替代 schema 或以自身输出证明 schema 有效。每份 instance 至少具有 contract kind、schema identity/version/digest、revision/digest、适用范围、生成者、兼容版本、引用工件和失败策略；required kind 缺失以及未知、candidate、digest 不匹配的 schema/version 或必需字段必须被拒绝，不得静默忽略。合同升级必须提供兼容读取或显式 migration 诊断。

---

<a id="fr-0800"></a>
### FR-0800 Integration Test Contract

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-04` / `BS-05`

Archer 必须生成 project-local integration contract，定义测试根目录、发现规则、runner/setup/run 命令、service/fixture、环境、超时、AC metadata、required/optional suite、skip/quarantine policy、证据格式和失败语义。Runtime 必须能独立校验该合同与 Test Plan 的 integration 分配一致。

---

<a id="fr-0900"></a>
### FR-0900 E2E Test Contract

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-04` / `BS-05`

Archer 必须生成 project-local e2e contract，定义公开用户入口、旅程/场景、测试根目录、runner/setup/run 命令、环境与服务生命周期、fixture、隔离、超时、artifact、AC metadata、required suite、证据和失败恢复。E2E 必须验证真实可观察出口，不得仅调用内部实现冒充用户旅程。

---

<a id="fr-1000"></a>
### FR-1000 Pre-commit Contract

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-07`

Archer 必须依据宿主项目真实工具链设计 pre-commit contract，声明受控配置、安装入口、既有 hook 的保留/合并策略、版本、快速 format/lint/static/secret/trace checks、合理时长内可选的 unit tests、失败和自动修改语义，以及 Runtime 的安装/更新/readback 验证。pre-commit 只用于正式 commit 的快速本地 gate，不承担 Red 证明或最终全量质量门禁；Archer 与 Devon 不执行安装副作用。

---

<a id="fr-1100"></a>
### FR-1100 托管 GitHub Actions CI Contract

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-06`

Archer 必须为每个宿主项目生成 GitHub Actions machine contract，至少定义 provider、托管路径 `.github/workflows/louke-ci.yml`、目标分支/触发器、runner/matrix、setup、job DAG、宿主命令、权限、secrets/services、cache、artifact/evidence、超时和失败策略。合同必须覆盖 Test Plan 的 required unit/integration/e2e、静态检查、AC trace、build 与 artifact verification，不得使用固定语言模板代替项目设计。

---

<a id="fr-1200"></a>
### FR-1200 稳定 Required Check 与强制策略

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-06`

CI contract 必须定义名称稳定且唯一的聚合 check `Louke CI / required`。只有全部 required jobs 对同一 commit 成功时才可成功；失败、取消、超时、缺失、非法 skip 或结果不确定均为失败。合同必须定义由 Runtime 创建/更新 Louke 所有的 ruleset，或在能力不支持时使用兼容 branch protection，并要求回读确认且不删除用户已有规则。

---

<a id="fr-1300"></a>
### FR-1300 CI 共存、生成与漂移生命周期

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-06` / `BS-13`

设计必须规定托管 workflow 的确定性生成来源、contract revision/digest 和 owner marker。不存在时可创建，未被外部修改时可幂等更新；宿主项目其它 workflows 和 rules 默认保留。Human/外部工具直接修改托管文件时不得静默覆盖，Runtime 必须保留 diff，由授权 Agent 依据当前设计接受、讨论或语义合并，并建立新 baseline。缺失、非法 YAML、命令不存在或 contract drift 必须阻止通过。

---

<a id="fr-1400"></a>
### FR-1400 Canonical Release Identity 与版本源

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-08`

Archer 必须生成 registry required kind `release-version` 的 contract instance，Runtime/program 必须能通过 registry discovery 将其作为 required kind 发现；该 instance 把 Human 在 release 创建时提供的 canonical version 与 run、release branch、目标 tag 和宿主项目真实版本源建立明确映射。该 instance 必须通过 Runtime/program 权威 schema 的 identity/version/digest 校验，具有自身 revision/digest，并定义 adapter、version-source identity、读取/写入或准备入口、前缀/规范化比较和失败语义。已有项目应兼容其版本机制；全新项目由 Archer 选择单一权威版本源和 adapter。branch/tag 名称不能单独证明构建物版本；required kind 或 mapping 缺失、不可解析、不一致，或 schema 非 active/未知时必须阻止 baseline。

---

<a id="fr-1500"></a>
### FR-1500 Build、Artifact 与安装后版本合同

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-08`

Archer 必须生成 project-local build/artifact contract，定义准备版本源、可复现 build、全部必需 artifact 枚举、每类 artifact 的版本提取器/digest、canonical version 比较，以及适用安装、部署或运行后公开版本读取出口。多 artifact 任一缺失、无法提取、不一致或公开出口不一致均为失败；source declaration 不得替代真实 artifact 检查。

---

<a id="fr-1600"></a>
### FR-1600 Publish 与恢复合同

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-09`

Archer 必须定义 merge/main、tag、registry/artifact publish、GitHub Release、部署、安装/smoke 的适用顺序、前置 gate、稳定 operation identity、事实查询、幂等/不可变语义、凭据与授权边界、partial success reconcile、rollback/forward-fix 和发布后验证。无法确认外部结果时必须进入可恢复的 `needs_attention`，不得伪报成功或盲目重试。

---

<a id="fr-1700"></a>
### FR-1700 Agent Prompt 作为规范性工件

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-10`

每个 Spec revision 必须声明受影响的 canonical Agent prompt sources；本 Spec 的封闭集合是且仅是 `louke/agents/Archer.md` 与 `louke/agents/Prism.md`。这两个 prompt 必须与 Spec/设计工件在同一受控流程内修改、独立 review、计算 digest 并纳入 implementation baseline；漏列任一来源或夹带任一未授权 prompt 都必须阻止 baseline。prompt 后续变化必须产生新 revision，并使依赖旧 prompt identity 的 task/review/evidence stale。Human 产品批准不等同于对技术 prompt 文本另设批准 gate。

---

<a id="fr-1800"></a>
### FR-1800 Prompt Bundle Manifest 与身份

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-10` / `BS-12`

程序必须生成 prompt bundle manifest，至少记录 bundle/schema version、canonical source path/digest、role、frontmatter/permission/model abstraction、引用 protocols/skills、owning Spec/revision、input/output schema refs、转换规则版本、部署 path/digest 和 bundle digest。Runtime dispatch 必须绑定精确 bundle/role identity；聊天中声称使用某版本不能作为证据。

---

<a id="fr-1900"></a>
### FR-1900 Prompt 语义与机器 Schema 分离

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-11`

Agent input/output 与全部 machine contract schema 必须由 Runtime/program-owned、versioned registry 定义；每个权威 schema 都具有 identity、version 和 digest，并由 Context/Task Manifest 或 contract registry 传入/解析。Archer 只生成引用 active 权威 schema 的 contract instance，prompt 与 instance 只声明语义职责、约束和 schema reference，不得携带替代 schema或自证其 schema。程序至少校验 schema identity/version/digest、必需字段、字段类型、枚举、附加字段策略和 identity/freshness；未知或 candidate schema 必须拒绝，prompt 内示例不得成为唯一或更高优先级的格式权威。

---

<a id="fr-2000"></a>
### FR-2000 Prompt 确定性部署与 Drift 检测

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-12`

canonical prompt source 到运行时部署副本的转换必须确定、可重放并可 readback。程序必须区分语义源、模型绑定等环境转换和生成副本，验证 manifest/digest 一致；缺失、手工改写、旧副本或转换版本不匹配必须阻止使用或由 Runtime reconcile，不得静默运行未知 prompt。

---

<a id="fr-2050"></a>
### FR-2050 Prompt Candidate 的安全自举与原子激活

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-10` / `BS-12`

Runtime 必须区分执行当前 task 的 trusted active prompt bundle 与正在编辑/评审的 candidate bundle。当前 session/attempt 始终绑定启动时的 active identity，candidate 文件变化不得热替换正在运行的 Agent；candidate 只有在程序校验、独立 review、部署 readback 和 baseline 建立全部完成后，才可原子激活供后续 dispatch 使用。修改 reviewer 自身 prompt 时，评审必须由先前 trusted reviewer bundle 执行并记录两套 identity，防止候选提示词自报通过。

---

<a id="fr-2100"></a>
### FR-2100 Host Project 中的 Prompt 只读边界

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-10` / `D-03`

普通宿主项目 release 必须把当前安装的 canonical prompt bundle 视为包管理的只读工作流输入，不得为适配某个项目而把其语言、构建配置、目录或业务事实写回通用 Agent prompts。宿主差异必须通过 project facts、design artifacts、machine contracts 和 task manifest 传入。只有开发 Louke 自身且 Spec 显式列入 prompt source 时，相关源文件才成为该 release 的授权编辑工件。

---

<a id="fr-2200"></a>
### FR-2200 Archer 规范性语义合同

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-02` / `BS-03` / `BS-05` / `BS-10`

Archer prompt 必须限定其职责为读取当前 manifest 和项目事实，自主设计 Test Plan/Architecture/Interfaces/machine contracts，处理授权 direct diff，并返回语义结果或有锚点 gap。它不得主动向 Human 请求技术决定，不得执行安装、commit、push、dispatch、review 持久化或阶段推进；发现产品需求不足时只返回可追溯 advisory，由 Runtime 决定合法上游路径。

---

<a id="fr-2300"></a>
### FR-2300 Prism 设计评审语义合同

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-14`

Prism prompt 必须要求其独立评审精确 design revision 中的三份文档、全部 machine contracts 和受影响 prompt sources，检查需求追溯、可实现性、测试层闭包、接口挂载、宿主适配、schema 引用和职责一致性。Prism 只返回绑定输入 identity 的 PASS/REVISE 与 findings，不读取或伪造作者通过结果，不写 review artifact，不调用 Runtime 命令，也不推进阶段。

---

<a id="fr-2400"></a>
### FR-2400 Human 可选 Review 与 Direct Diff

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-13` / `D-04`

M-DESIGN 的文档界面必须允许 Human 查看、评论或直接编辑授权工件，但 Human 可以缺席。Runtime 必须把自上一 baseline 的 direct diff 连同 inline discussions 提供给 Archer，避免重复提出同一问题；Archer 认为修改合理时可接受，认为有技术问题时通过 inline discussion 说明。Human 修改不是自动批准，也不得形成新的技术 gate。

---

<a id="fr-2500"></a>
### FR-2500 独立 Review Loop 与 Freshness

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-14`

Runtime 必须在作者 revision 固定后单独 dispatch Prism，并将 verdict 绑定全部输入 digests、prompt bundle、reviewer、attempt 和 findings。REVISE 必须返回 Archer 形成新 revision；任一被评审工件变化都使旧 verdict stale。Archer 不得读取、代填或伪造 Prism PASS，Prism finding 也不得被当作 Human 产品决定。

---

<a id="fr-2600"></a>
### FR-2600 设计程序校验、Gap 与 Stale 传播

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-05` / `BS-14` / `BS-15`

Runtime 必须校验文档/schema 可读性、ID/引用、FR/AC/测试层闭包、prompt manifest/parity、未闭合 discussion 和无越界 diff；还必须双向校验 Test Plan observable interface/执行入口解析到 Interfaces 的真实 identity，Interfaces 状态/权限/错误/恢复由 Architecture 的组件、状态和信任/故障边界承载，以及 machine contracts 的命令/路径/状态语义与三份文档一致。任一缺失、orphan 或双向冲突必须按 FR/AC、interface、architecture anchor 与 contract 定位并阻止 baseline。技术 gap 由 Archer 与 Prism 确认后可直接形成新 M-DESIGN revision；产品意图、权限、范围或 Acceptance gap 必须经 Human 决定返回 M-SPEC/M-ACC 并重新批准。任何修订都按依赖传播 stale，禁止复用旧 review。

---

<a id="fr-2700"></a>
### FR-2700 Implementation Baseline 与无第二 M-LOCK

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-15`

当当前 design revision 的全部 program gates 与 Prism review PASS 后，Runtime 必须原子建立 implementation baseline，包含 requirements/design digests、base commit、machine contract registry、prompt bundle identity、Issue manifest、release identity 和 closed discussions，并直接进入 `M-IMPL`。不得创建第二个 `M-LOCK`、等待 Human 技术批准或把该 baseline 当作不可修订的永久冻结。

## 非功能需求

<a id="nfr-0100"></a>
### NFR-0100 确定性与可复现性

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-05` / `BS-12`

相同规范性输入、生成器版本和宿主事实必须得到字节稳定或规范化后 digest 稳定的 machine contracts、prompt deployment 和 implementation baseline；所有非确定输入必须显式记录。

---

<a id="nfr-0200"></a>
### NFR-0200 最小权限与 Secret 安全

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-06` / `BS-09`

设计和 prompt 合同必须遵守最小写入范围与最小 GitHub token 权限；不得在 prompt、合同、日志或测试 fixture 中持久化 secret。来自 fork/不受信代码的 CI 不得获得生产 secret 或高权限 token。

---

<a id="nfr-0300"></a>
### NFR-0300 宿主技术栈可移植性

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-02` / `D-03`

规范与 prompts 不得依赖某一种语言、包管理器、构建文件或 artifact 类型；至少能够通过 project-local adapter/contract 表达已有项目与全新项目的不同方案，并对不支持能力给出显式诊断。

---

<a id="nfr-0400"></a>
### NFR-0400 可恢复性与审计

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-01` / `BS-09` / `BS-14`

Runtime 重启后必须能从持久化 revision、manifest、diff、review、program evidence 和 operation design 重建 M-DESIGN 当前状态；缺失或 digest 不一致时必须 fail closed，并保留历史 revision。

---

<a id="nfr-0500"></a>
### NFR-0500 校验反馈可操作性

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-05` / `BS-14`

程序校验失败必须返回稳定 check ID、工件路径/字段、期望与实际、关联 FR/AC/contract/prompt identity 和可重试性；不得只返回通用“invalid design”。

---

<a id="nfr-0600"></a>
### NFR-0600 状态与 Schema 迁移兼容性

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-05` / `BS-15`

从旧 `M-LOCK-1`、第二 M-LOCK、prompt/schema 旧格式迁移时必须使用显式版本与兼容读取/单向 migration；新运行只能写 canonical `M-REQ-APPROVAL → M-DESIGN → M-IMPL` identity，不得同时维护两个可写真相。

## 澄清记录

- 2026-07-19：确认 M-DESIGN 之后取消第二个 M-LOCK；Human 是可选 reviewer，不批准技术方案。
- 2026-07-19：确认 pre-commit 仍需安装，但只承担正式 commit 的快速本地 gate，不用于证明 Red。
- 2026-07-19：确认 Agent prompts 从本版本起属于显式规范性工件；机器 schema 必须由程序提供。
- 2026-07-19：确认普通宿主项目不得修改通用 Louke prompts；项目差异通过设计合同与 manifest 注入。
