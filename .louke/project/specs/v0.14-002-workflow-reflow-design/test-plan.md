# 工作流重构：技术设计与规范性 Agent 合同 — Test Plan

- **Spec ID**: `v0.14-002-workflow-reflow-design`
- **Created**: `2026-07-20`
- **Bound Story**: `sha256:06d5573efbf59dd18b480d6539ad16df237fd4460f9f95d1589110cbfeec1993`
- **Bound Spec**: `sha256:315c8d20254fceb63971b029d69c81889972eedb581621981a012f17edc8867f`
- **Bound Acceptance**: `sha256:39b09cbf36cc0f4f0dcc8f0e8a79949049a2b6baddcecbcf2183ad407e493559`
- **Related acceptance**: `.louke/project/specs/v0.14-002-workflow-reflow-design/acceptance.md`
- **Related interfaces**: `.louke/project/specs/v0.14-002-workflow-reflow-design/interfaces.md` (assertion basis — see §6.5)

## 1. Stance and Boundaries

### 1.1. Black-box Statement

断言只落在 `interfaces.md` 的公开出口：design read model/Workbench、结构化validation result、registry/schema discovery、project-local contract文件、prompt bundle manifest与部署readback、托管workflow/rules readback、pre-commit readback、真实build artifact及安装后版本出口、publish ledger、Prism result、implementation baseline和audit export。测试不以Agent“我已完成/PASS”、prompt中的示例、私有Python对象或数据库私有表证明验收。

### 1.2. Non-observable Objects (tests do not directly depend on)

- Runtime内部类层次、调度状态机、队列、cache和函数调用次数；
- registry/validator内部索引、prompt transformer中间AST、YAML renderer中间对象；
- 浏览器组件树、CSS和未保存内存；
- provider timeout之后未经事实查询的猜测状态。

需要状态时使用 IF-DES-01/02、IF-CON-01、IF-PRM-01、IF-REV-01、IF-AUD-01 或对应adapter readback；没有出口先修订Interfaces，不能从私有store偷看。

### 1.3. Cheating Patterns (CI enforced interception)

| # | 禁止模式 | 门禁 |
|---|---|---|
| 1 | 修改断言迎合实现、`assert True`、只断言非空 | AC trace/anti-cheat scan失败 |
| 2 | 无Issue依据skip required suite，或把not-run/unknown记PASS | report schema与required聚合失败 |
| 3 | mock Registry/Validator/Prompt Manager/Design Coordinator后声称integration通过 | fixture import scan + review失败 |
| 4 | expected digest/schema/closure来自被测validator输出 | Ground Truth隔离检查失败 |
| 5 | 只解析prompt示例或instance内嵌schema证明schema有效 | registry contract测试失败 |
| 6 | 用内部API代替Acceptance承诺的M-DESIGN Workbench旅程 | CI E2E evidence缺失 |
| 7 | 只检查source/tag，不真实构建并逐artifact安装验证 | artifact gate失败 |
| 8 | timeout后直接重试publish并以`--skip-existing`推断相同 | ledger scenario失败 |
| 9 | candidate Prism审查自己、或把作者结果写成Prism PASS | bundle/review identity断言失败 |
| 10 | fixture写入真实token、日志回显secret canary | secret scan失败 |

### 1.4. Safeguards (CI checks + PR process)

1. 每个自动化测试首行docstring/comment至少含一个规范ID `AC-FRXXXX-YY` 或 `AC-NFRXXXX-YY`。Devon实现 `tools/check_ac_traceability.py`，验证34/34 AC、无未知ID、每个required layer均有evidence；不依赖旧`lk agent`。
2. 所有Test Plan `IF-*`和runner必须可解析到Interfaces与contract；所有`ARC-*`必须存在。CI运行IF-DES-02双向closure gate。
3. skip/quarantine必须有Issue、owner、expiry且不能作用于required suite；required skip始终使`Louke CI / required`失败。
4. fault injection只允许在时钟/UUID、文件损坏、进程kill、外部GitHub/PyPI/OpenCode stand-in及ack边界；不得替换核心判定。
5. 测试变更PR分类为新AC、Spec变更或flake/环境修复并链接来源；禁止“实现不同所以改测试”。
6. coverage `>=95%`是附加门禁，不能替代34/34 trace、contract、integration或CI E2E。

### 1.5. Test Division of Labor

- **Devon**：unit、schema/contract测试、公开CLI/readback配套测试、trace/validation工具及`.github/workflows/louke-ci.yml`。
- **Shield**：所有跨模块integration、Workbench CI E2E、异构宿主fixtures、外部stand-ins、restart/partial-success恢复场景。
- **独立测试审查者**：Ground Truth canonicalization、prompt semantic golden、provider ledger和secret redaction。
- **Prism**：产品内独立设计语义review；不等同于测试代码review，也不生成测试evidence。

---

## 2. Test Environment

### 2.1. Directory Layout (project customization)

```text
tests/
├── unit/                              # Devon：schema/rule/canonicalization/adapter decisions
├── integration/
│   └── v014_design_contracts/         # Shield：Runtime+store+files+stand-ins真实接线
├── e2e/
│   ├── v014_design_contracts/         # Shield：installed wheel + live Workbench + Chromium
│   └── run-project-venv               # 现有宿主runner
├── fixtures/
│   └── v014_design_contracts/         # 异构repo、contracts、prompts、legacy、provider脚本
└── ground_truth/
    └── v014_design_contracts/         # 不import louke.*的digest/closure/artifact reference
```

本轮 author scope 授权三份设计文档、`design-artifacts/**` candidate 与两个 canonical prompt sources；明确不授权 `project.toml`、runner、Runtime、workflow 或 `.opencode/agents/**`。公开命令保持 integration `tests/e2e/run-project-venv integration`、e2e `tests/e2e/run-project-venv e2e --profile all --runtime both`，但**当前 runner 尚不收集本 Spec 新目录**：integration 只收集 `tests/integration/install_experience`，e2e 只收集旧 install/chromium suites。因此这些命令当前返回 0 也不是 v014 evidence。`design-artifacts/runner/project-runner.candidate.json` 锁定 Devon 必须先完成的 discovery/参数变更；安装并经 collect/readback 验证之前，Shield可准备fixture和测试代码，但 Runtime/CI必须把 v014 I/E 状态记为 `not-run`并 fail closed，不得声称 executable PASS。

### 2.2. Naming Conventions

- 文件按公开场景命名：`test_<contract_or_journey>__<failure>.py`，不按私有类命名。
- markers：`integration`, `e2e`, `chromium_e2e`, `real_opencode`；本Spec默认CI不新增真实PyPI publish marker，publish使用protocol-faithful stand-in。
- fixture identity包含`facts_digest`, `schema_registry_digest`, `base_commit`, `bundle_digest`，禁止以目录名暗示PASS。

### 2.3. Execution

| 层 | 入口 | 环境 | CI job | 边界 |
|---|---|---|---|---|
| unit | `python -m pytest -q tests/unit --cov=louke --cov-report=xml --cov-fail-under=95` | Python 3.11–3.14；stdlib clock/UUID可控 | `unit` | 纯解析、canonicalization、schema关键词、状态/权限/错误规则 |
| contract | `python -m louke._tools.design_contract validate --manifest <fixture> --format json --output <report>` + pytest contract assertions | Python 3.12、只读schema registry、fixture repo | `design-contract` | 文件/schema/引用/命令/readback合同，不替代跨模块接线 |
| integration | `tests/e2e/run-project-venv integration` | clean tmp Git workspace、真实store/files/build、外部stand-ins | `integration` | 所有2+模块接口、restart、CAS、drift、reconcile |
| CI E2E | `tests/e2e/run-project-venv e2e --profile all --runtime both` | built wheel、clean project venv、live Workbench、Chromium、stand-ins | `e2e-standin` | 从requirements approval到M-IMPL baseline的公开用户/Agent路径 |
| real build | `python -m build` + IF-BLD-01 verification | clean build/venv；无editable install | `build-artifacts`,`artifact-verify` | wheel+sdist逐件版本、prompt/schema内容及安装出口 |

执行顺序：quality → contract/trace → build/artifact → unit → integration → CI E2E。每场景隔离HOME/XDG/Git config、workspace/store、ports、prompt active pointer和provider namespace；teardown总是执行，失败evidence先redact再上传。

### 2.3.1 Runner/project candidate 的精确 foundation contract

1. Devon首先修改现有`tests/e2e/run_e2e.py`，不得新增另一套公开runner：integration默认paths从仅`tests/integration/install_experience`扩为顺序集合`[tests/integration/install_experience, tests/integration/v014_design_contracts]`；e2e保留`install`和`chromium`profile，并新增`design-contracts` profile，`all`精确展开`install,chromium,design-contracts`。新profile路径是`tests/e2e/v014_design_contracts`，在`local`和`global`两种installed-wheel runtime各运行一次。
2. parser的`--profile` choices精确改为`install|chromium|design-contracts|all`；`--runtime`保持`local|global|both`。unknown profile/runtime由`argparse`非0退出。现有命令字符串不变，从而保留历史suite兼容。
3. runner在调用pytest前生成expected collection manifest；pytest使用JUnit输出并在结束后生成`v014-runner-evidence.json`。证据至少含`schema_version=1.0.0`、release/spec/base/runner digest、command/profile/runtime、expected/collected node IDs、AC IDs及layers、suite results、service lifecycle、start/end时间、exit reason。required目录不存在、零收集、expected node/AC/layer漏跑、unknown、skip、not-run、timeout或cancel均非0；不得仅透传pytest在空收集时的偶然结果。
4. integration使用project `.venv`且真实store/files/stand-ins，不启动Workbench。design-contracts e2e使用已构建wheel创建隔离product venv，runner启动`lk web --host 127.0.0.1 --port $ALLOCATED_PORT`，以`GET /health`每250ms轮询至HTTP 200且body报告预期installed version，超时60秒；Chromium从公开Workbench入口执行。无论成功失败，先保存redacted evidence，再向进程组发送TERM、等待10秒、必要时KILL，并删除temp HOME/XDG/workspace/ports；teardown失败使命令非0。
5. 依赖由project `.venv`安装锁定的`pytest==8.4.1`、`pytest-cov==6.2.1`、`playwright==1.54.0`及Chromium对应revision、`build==1.2.2.post1`、`jsonschema==4.25.1`；default CI不使用production secret。candidate未安装前，implementation baseline明确列此差异为Devon首个foundation task，Shield不得自行改变runner拓扑。

### 2.4. Test Data (required)

| fixture | 内容与用途 |
|---|---|
| `approved_design_inputs` | current/stale/missing requirements、base commit、facts、actor/attempt/release identities |
| `host_matrix` | Python wheel+sdist既有项目、Node tarball既有项目、空白项目、不支持能力；路径只引用各自事实 |
| `schema_registry_matrix` | active/candidate/retired/unknown、digest mismatch、缺字段/错类型/extra field、兼容/不兼容migration |
| `release-version-node-host-valid` | `design-artifacts/validation/release-version-node-host.valid.candidate.json`：具体Node/SemVer/package.json/`.mjs` adapter/npm命令host，必须由与Louke instance相同的`release-version@1.0.0` schema接受；不得引用Python/pyproject/PEP 440 |
| `negative-schema-fixtures` | 八个独立mutation：缺task input ref、facts/task artifact kind互换、空CI job、nested permission未知字段、digest scope冲突，以及Node release mapping缺branch、tag类型错误、version source未知字段；每项声明预期schema/provenance错误 |
| `design_closure_matrix` | 34 AC、orphan IF/ARC/contract、command/path/status冲突、required层缺失 |
| `prompt_matrix` | Archer/Prism canonical source、deterministic transform、手改/缺失/旧副本、active/candidate双bundle |
| `ci_hook_matrix` | 用户workflow/rules/hooks、managed clean/drift/invalid YAML、job所有conclusion、fork权限 |
| `release_artifact_matrix` | canonical/非法tag、版本源不匹配、wheel/sdist缺失/坏metadata/错installed outlet/缺prompt/schema |
| `publish_matrix` | tag/PyPI/GitHub Release/smoke成功、明确失败、ack loss后成功、zero/multi/conflict、partial success |
| `review_restart_matrix` | Human缺席/direct diff/discussion、Prism PASS/REVISE/stale、author/check/review边界kill |
| `legacy_matrix` | 旧M-LOCK-1/第二锁、旧prompt/contract schema、未知版本、migration中断 |
| `secret_canaries` | 唯一token/cookie/API key字节，仅由外部输入注入，任何report不得回显 |

全部fixture合成且manifest记录生成器版本/digest；默认CI无真实credential或网络publish。

### 2.5 Candidate design bundle 与 active 隔离

- Machine-readable入口：`design-artifacts/design-artifact-manifest.candidate.json`。它枚举7/7 program-owned machine schema candidates、4/4 Agent I/O schemas、7/7 canonical-envelope instances、facts/task provenance artifacts、2/2 canonical prompt sources及staging renders、validation record、runner/project candidate、全部bytes digest和activation prerequisite。
- schema registry：`design-artifacts/registry/registry.candidate.json`，owner=`Runtime/program`且`activation_state=candidate`。Archer/Prism各有独立input/output schema；task input递归校验stage/spec/revision、input identity/digest、write/effect/output/freshness，Prism还校验trusted reviewer execution和reviewed candidate binding。instance仅引用exact machine schema且通过外部manifest解析自身bytes digest及facts/task artifact kind/path/digest；schema不是prompt或instance内容。Devon实现package registry并完成required tests、artifact安装readback、trusted Prism review与Runtime原子pointer交换后才可成为active。当前不存在active registry，resolve必须`SCHEMA_NOT_ACTIVE`并阻断baseline。
- design-time validator固定`jsonschema==4.25.1`：先meta-validate 11 schemas，再验证Runtime-authoritative Archer task input、7个Louke正例instance及`validation/release-version-node-host.valid.candidate.json`异构正例，最后应用`validation/negative-schema-fixtures.candidate.json`八个mutation。Node正例必须由同一release schema通过且不含Python常量；八个负例都必须以声明的schema/provenance错误失败。正例失败或任一负例意外通过即candidate validation失败。结果记录在`validation/schema-validation-record.candidate.json`，仅证明candidate bytes检查，不代表active或Runtime PASS。
- contracts：candidate存于`design-artifacts/contracts/<kind>.candidate.json`；Runtime激活后project-local canonical安装目标才是`.louke/project/contracts/v0.14-002-workflow-reflow-design/<kind>.json`。candidate不是生产合同、未执行且不宣称PASS。
- prompts：closed set且仅`louke/agents/Archer.md`、`louke/agents/Prism.md`。staging render bytes length/digest与in-memory readback位于`design-artifacts/prompts/staging/*.render.candidate.json`，不会生成或覆盖active `.opencode/agents/`副本。当前Prism执行identity绑定既有trusted active digest；review对象绑定candidate bundle digest，二者必须不同。漏列、夹带、source/transformer/render drift或任一上游输入变化都使candidate/review stale。
- release/project：candidate identity固定`0.14.0`、`v0.14-002-workflow-reflow-design`、`releases/0.14.0`。当前未授权修改的`.louke/project/project.toml`仍是`0.13.1`/001/`releases/0.13.1`，故candidate未安装前project readback必须失败，不伪造current。

---

## 3. Ground Truth Method

### 3.1. General Principle

| 断言 | 独立真值 |
|---|---|
| schema/instance/provenance bytes digest | stdlib `hashlib`直接读取fixture；manifest按kind+path定位唯一bytes，instance无自引用digest；canonical JSON由独立小脚本排序编码 |
| AC/IF/ARC closure | 独立Markdown token/表格解析器读取locked fixture，不调用被测validator |
| prompt source/deployment parity | 预先锁定transform rule fixture + 原始bytes SHA-256；不读被测manifest期望值 |
| workflow coexistence | 独立读取Git tree和YAML，比较managed file之外path/digest及job/check集合 |
| artifact identity/version | `zipfile`/`tarfile`读取metadata、SHA-256、clean venv的公开CLI/metadata出口 |
| external operation唯一性 | stand-in公开query结果和append-only call ledger；expected identity来自fixture manifest |
| stage migration唯一current | public IF-AUD-01 export + locked old/new workflow identities，不查私有表 |

### 3.2. Ground Truth Isolation (mandatory rule)

`tests/ground_truth/v014_design_contracts/**`不得`import louke.*`，只使用stdlib、Git CLI和fixture bytes。expected digest/IDs/paths不能从被测IF-DES-02/manifest回填。变更须由非实现者重点review；CI静态扫描违反即失败。

---

## 4. Test Scope

覆盖28 FR、6 NFR、34个稳定AC。下表是需求级责任分配，不是测试函数清单。`U`=unit，`C`=contract，`I`=integration，`E`=CI E2E。所有`I/E`分别进入`integration`/`e2e-standin`；真实build另进入artifact gate。

### 4.1. AC → observable interface → required layer(s) → CI gate/job

| AC | Observable interface | Required layers / CI | Fixture/environment | 策略、trace与分配理由 |
|---|---|---|---|---|
| `AC-FR0100-01` | IF-DES-01, IF-FCT-01 | U+C+I / design-contract,integration | approved_design_inputs | current输入持久完整identity；逐项missing/stale/base conflict无Archer task；跨Coordinator/Store故需I |
| `AC-FR0200-01` | IF-FCT-01, IF-DES-01 | C+I / design-contract,integration | host_matrix | 两个异构已有项目只引用真实入口；空项目无Human选择仍有完整决定；检测Louke默认泄漏 |
| `AC-FR0300-01` | IF-DES-01, IF-WEB-01, IF-AUD-01 | C+I+E / design-contract,integration,e2e-standin | scope/direct-diff fixture | manifest allowlist、三文档/contracts/prompts与禁止副作用；越界patch/diff拒绝且baseline不变；用户surface需E |
| `AC-FR0400-01` | IF-DES-02, IF-TST-01 | C+I / design-contract,integration | design_closure_matrix | 34 AC字段、IF/runner解析、层/fixture/job/trace/rationale双向闭合；unit-only跨模块、orphan/冲突定位失败 |
| `AC-FR0500-01` | IF-DES-02, IF-AUD-01 | C+I / design-contract,integration | design_closure_matrix | 组件/流/状态/安全/迁移/决定齐全；每个接口语义解析ARC承载；未决技术边界和orphan阻断 |
| `AC-FR0600-01` | IF-DES-02, IF-WEB-01, IF-CON-01 | C+I+E / design-contract,integration,e2e-standin | closure + Workbench | 主旅程入口到真实IF identity、状态/权限/错误/恢复；不适用surface不虚构；Workbench可见闭包用E |
| `AC-FR0700-01` | IF-REG-01, IF-CON-01 | U+C+I / unit,design-contract,integration | schema_registry_matrix + Node release positive + negative-schema-fixtures | 七required kinds discovery、canonical envelope、external manifest bytes digest、facts/task kind+path+digest；同一release schema接受Node正例；candidate/unknown/empty nested/digest scope/malformed mapping/migration错误拒绝 |
| `AC-FR0800-01` | IF-TST-01, IF-DES-02 | C+I / design-contract,integration | integration contract fixture | 路径/discovery/setup/run/services/fixtures/env/timeout/AC/suite/evidence完整；required AC无去向/skip失败 |
| `AC-FR0900-01` | IF-TST-01, IF-WEB-01 | C+I+E / design-contract,integration,e2e-standin | e2e journey fixture | 公开entry/actions/visible result/lifecycle/isolation/evidence；内部模块冒充用户旅程与缺runner拒绝 |
| `AC-FR1000-01` | IF-PC-01, IF-CON-01 | C+I / design-contract,integration | ci_hook_matrix | 保留既有hooks、install/readback/version/快速checks/modify/fail；Agent安装、Red/full-gate语义被拒 |
| `AC-FR1100-01` | IF-CI-01, IF-FCT-01 | C+I / design-contract,integration | Python+Node host_matrix | 两栈各用真实setup/build/test/artifact并含DAG/权限/service/cache/evidence；required层遗漏失败 |
| `AC-FR1200-01` | IF-CI-01 | U+C+I / unit,design-contract,integration | job conclusion/rules fixture | 唯一稳定required；fail/cancel/timeout/missing/skip/unknown均失败；回读保留已有checks |
| `AC-FR1300-01` | IF-CI-01, IF-AUD-01 | C+I / design-contract,integration | managed drift fixture | 同contract重复render规范化digest相同且其它workflow/rules不变；Human drift保留diff；missing/invalid/command missing拒绝 |
| `AC-FR1400-01` | IF-REG-01, IF-REL-01, IF-CON-01 | U+C+I / unit,design-contract,integration | Louke release instance + concrete Node release positive/negative mappings | registry发现generic strict release-version；同schema分别接受Louke Python与Node/SemVer完整instance；canonical→source/adapter/branch/tag唯一映射；缺branch、错tag类型、unknown source字段、未知schema/tag-only/Human选工具阻断 |
| `AC-FR1500-01` | IF-BLD-01, IF-REL-01 | C+I / design-contract,artifact-verify | release_artifact_matrix + clean venv | 严格顺序真实build、wheel/sdist逐件digest/extract/compare/install/outlet；任一缺失/不匹配确定FAIL |
| `AC-FR1600-01` | IF-PUB-01 | U+C+I / unit,design-contract,integration | publish_matrix stand-in | 全适用operation顺序/gate/identity/query/idempotency/credential/recovery；partial/unknown进入needs_attention且不重复 |
| `AC-FR1700-01` | IF-PRM-01, IF-REV-01 | C+I / design-contract,integration | prompt closed-set fixture | source集合精确Archer/Prism、baseline有digests/review；漏列/夹带拒绝，变化使旧task/review/evidence stale |
| `AC-FR1800-01` | IF-PRM-01 | U+C+I / unit,design-contract,integration | prompt_matrix | manifest的Archer/Prism exact input+output identity/version/digest、task exact bundle/role回溯；`current`/`digest_source`/聊天声明版本拒绝 |
| `AC-FR1900-01` | IF-REG-01, IF-CON-01, IF-PRM-01 | U+C+I / unit,design-contract,integration | schema/prompt matrix + Node release positive + negative-schema-fixtures | 不解析prompt示例即可validate Runtime-authoritative两个task input、两个result output、7 Louke contracts和同schema Node release正例；Maestro authority/return destination、缺task ref、错provenance kind、空nested、unknown nested、digest scope冲突、malformed release mapping、type/enum/additional字段错误均拒绝 |
| `AC-FR2000-01` | IF-PRM-01 | U+C+I / unit,design-contract,integration | deploy drift matrix | 重复transform/deploy digest稳定且readback映射；缺失/手改/旧transform/digest mismatch阻止dispatch或显式reconcile |
| `AC-FR2050-01` | IF-PRM-01, IF-REV-01 | C+I+E / design-contract,integration,e2e-standin | active/candidate双bundle | 运行attempt固定旧active；candidate经lint/schema/trusted review/readback/baseline后原子激活；记录双bundle防自证 |
| `AC-FR2100-01` | IF-FCT-01, IF-PRM-01, IF-DES-01 | C+I / design-contract,integration | Java/Node host + Louke fixture | 普通宿主差异只在facts/contracts/manifests且installed prompts不改；Louke自身仅显式prompt paths可写 |
| `AC-FR2200-01` | IF-PRM-01, IF-DES-01 | C+I / design-contract,integration | Archer semantic lint/behavior + transport fixture | prompt职责含三文档/contracts/direct diff/gap和自主选择；Runtime独占dispatch/state/validation/persistence，provider/session仅opaque transport；question/install/Git/dispatch/review/推进指令不存在 |
| `AC-FR2300-01` | IF-PRM-01, IF-REV-01 | C+I / design-contract,integration | Prism semantic/result + transport fixture | manifest精确全部identity，result只返回Runtime且仅schema允许字段；provider不持久化，无写review/gate/推进/伪造/替Human决定指令 |
| `AC-FR2400-01` | IF-WEB-01, IF-DES-01, IF-REV-01 | I+E / integration,e2e-standin | Human absent/direct diff/discussion | surface从current Project进入；缺席仍完成；comment/diff下一round可见去重；技术问题锚定且Human不自动PASS |
| `AC-FR2500-01` | IF-REV-01, IF-AUD-01 | C+I+E / design-contract,integration,e2e-standin | PASS/REVISE/stale/restart | author持久后独立Prism task；verdict全identity；输入变化stale、REVISE新revision；无Archer PASS/文本推进路径 |
| `AC-FR2600-01` | IF-DES-02, IF-CON-01, IF-PRM-01 | C+I / design-contract,integration | full failure matrix | 坏ref/层/schema/drift/discussion/scope及三向/contract冲突均稳定check定位FR/AC/IF/ARC/contract；修订传播stale |
| `AC-FR2700-01` | IF-REV-01, IF-DES-01, IF-AUD-01 | C+I+E / design-contract,integration,e2e-standin | full happy + stale gate | 同revision program+Prism PASS原子baseline并M-IMPL；workflow/read model无第二M-LOCK/Human技术等待；stale不推进 |
| `AC-NFR0100-01` | IF-DES-02, IF-PRM-01, IF-REV-01 | U+C+I / unit,design-contract,integration | fixed clock/env repeat fixture | 同输入重复生成contract/deployment/baseline规范digest相同；generator/schema/tool版本全部可见 |
| `AC-NFR0200-01` | IF-DES-01, IF-CI-01, IF-AUD-01 | C+I / design-contract,integration | permission + secret_canaries | Archer/Prism无Git/GitHub/阶段写工具；CI最小权限/fork无secret；四类artifact扫描定位但不回显canary |
| `AC-NFR0300-01` | IF-FCT-01, IF-CON-01, IF-CI-01, IF-REL-01 | C+I / design-contract,integration | Python+Node+unsupported host_matrix | 两异构fixture各自通过且无跨栈路径；unsupported诊断含kind/facts，不回退固定语言默认 |
| `AC-NFR0400-01` | IF-AUD-01, IF-DES-01, IF-REV-01 | I+E / integration,e2e-standin | review_restart_matrix | author/check/review边界kill后恢复同current/pending/history且不重复attempt；删/篡digest fail closed并保留历史 |
| `AC-NFR0500-01` | IF-DES-02, IF-WEB-01 | C+I+E / design-contract,integration,e2e-standin | schema/trace/prompt/path failures | 四类失败都有稳定ID、path/field、expected/actual、关联identity、retryability；UI可导航锚点而非通用字符串 |
| `AC-NFR0600-01` | IF-AUD-01, IF-REG-01, IF-DES-01 | U+C+I / unit,design-contract,integration | legacy_matrix | 旧锁/prompt/contract显式迁移或只读诊断；新run只写canonical stage/schema；中断可重试、无双current，未知fail closed |

### 4.2. Requirement-level strategy summary

| requirement group | 主风险 | 必需层 |
|---|---|---|
| FR-0100..0600 | stale入口、事实泛化、授权越界、三文档orphan | C+I；Human surface E |
| FR-0700..1300 | schema自证、contract不可执行、CI/hooks覆盖或漂移 | U+C+I |
| FR-1400..1600 | tag冒充版本、漏artifact、partial publish重复副作用 | U+C+I + real build gate |
| FR-1700..2300 | prompt漏锁、部署漂移、candidate自举、Agent职责越权 | C+I；原子激活E |
| FR-2400..2700 | Human误成技术gate、Prism不独立、stale evidence推进 | C+I+E |
| NFR-0100..0600 | 非确定、secret、跨栈泄漏、重启/迁移双truth、不可定位错误 | U+C+I；用户恢复/反馈E |

---

## 5. Acceptance Criteria

1. 34/34 AC均有自动化引用，且表中每个required layer有独立evidence；unit/contract不能替代integration/CI E2E。
2. 所有跨模块接口至少integration；M-DESIGN Human主成功旅程、candidate激活、Prism闭包和M-IMPL继续路径至少CI E2E。
3. Registry无需读取prompt示例即可校验；七required contract kinds与Archer/Prism各自input/output四份Agent I/O schema完整、active schema exact、无orphan。
4. Louke wheel和sdist均真实构建、逐件版本/digest/prompt/schema检查，并分别clean install验证公开版本出口。
5. coverage `>=95%`，但不能替代AC closure、三向一致性、drift、恢复和安全evidence。

---

## 6. External Dependency Layered Testing (enabled)

### 6.1. Three Unavoidable Constraints

| # | Constraint | Consequence |
|---|---|---|
| C1 | PR不能持有生产GitHub/PyPI/OpenCode凭据 | 默认CI使用protocol-faithful stand-in；fork始终无secret |
| C2 | provider ack、eventual consistency和Runtime crash会造成结果未知 | operation ledger必须query-before-retry，不用HTTP timeout推断 |
| C3 | 不能mock Runtime/Registry/Validator/Prompt激活核心 | fault只注入外部协议、clock、filesystem和process边界 |

### 6.2. Stance: Controllable vs Mock

- **可控替身**：wall clock/UUID、GitHub rules/API、PyPI file query/upload、OpenCode session、filesystem drift、network ack与process kill。
- **不可替换**：Design Coordinator、Schema Registry exact resolve、closure validator、prompt candidate activation、baseline transaction、publish identity/reconcile。
- stand-in记录公开query/create/upload/readback ledger并支持成功、明确失败、timeout后成功、零/多/冲突候选；不替系统选候选或补写状态。

### 6.3. Three-Layer Test Pyramid

| Layer | 名称 | 覆盖 | 默认运行 |
|---|---|---|---|
| L1 | deterministic unit/contract | schema、canonicalization、状态/权限、文档/contract closure | 每PR |
| L2 | integration + browser stand-in | 跨模块、M-DESIGN旅程、drift/restart/partial publish | 每PR |
| L3 | real artifact/install + protected provider smoke | wheel/sdist和公开版本必跑；真实provider最小readback在release/manual | build每PR；provider release/manual |

L3 provider环境缺失为`not-run`并阻断publish，不得显示PASS；真实publish本身不作为测试动作，使用只读/隔离namespace smoke。

### 6.4. Responsibility Contract of Test Infrastructure

| Component | Responsibility (external) | Boundary |
|---|---|---|
| Host fixture builder | 创建两种已有栈与空白repo，输出独立facts manifest | 不替Archer选技术方案 |
| Schema fixture registry | 提供active/candidate/legacy bytes和immutable digest | 不判定instance业务语义 |
| Prompt deployment harness | 执行声明transform、暴露source/deployed bytes与drift | 不决定candidate可激活 |
| GitHub/PyPI stand-in | query/rules/upload/release协议、ack fault ledger | 不选择resource或宣告publish成功 |
| Browser harness | built wheel启动Workbench、页面动作、trace/reconnect | 不调用私有Runtime推进 |
| Fault controller | kill、ack loss、文件篡改、barrier | 不改expected或store |

### 6.5. Assertion Basis — Closure with interfaces.md

- revision/surface/checks：IF-DES-01、IF-DES-02、IF-WEB-01；
- schema/contracts/facts：IF-REG-01、IF-CON-01、IF-TST-01、IF-FCT-01；
- hooks/CI：IF-PC-01、IF-CI-01；
- version/build/publish：IF-REL-01、IF-BLD-01、IF-PUB-01；
- prompt/review/audit：IF-PRM-01、IF-REV-01、IF-AUD-01。

每个接口已在§4映射且最低层满足`interfaces.md` §7；不得增加test-only后门。

---

## 7. CI Gate

### 7.1. Required workflow

Devon按`architecture.md` §9实现`.github/workflows/louke-ci.yml`。现有`ci.yml`/`release.yml`保留但不得产生同名check；release只接受当前commit的`Louke CI / required`和IF-BLD-01 verified evidence。

| gate | trigger | 命令/接口 | fail semantics |
|---|---|---|---|
| quality | PR/push | `pre-commit run --all-files`; `python -m mypy louke` | 任一非0/timeout/自动修改未复核失败 |
| design-contract | PR/push | IF-DES-02 validate入口 | 任一schema/trace/parity/scope/secret check fail/unknown失败 |
| ac-trace | PR/push | `python tools/check_ac_traceability.py --acceptance .louke/project/specs/v0.14-002-workflow-reflow-design/acceptance.md --tests tests` | 非34/34、未知ID、required层无evidence失败 |
| build/artifact | PR/push/release | `python -m build` + IF-BLD-01 | wheel/sdist/prompt/schema/installed outlet任一缺失或不匹配失败 |
| unit | PR/push | §2.3 unit入口，Python 3.11–3.14 | 任一matrix/coverage失败 |
| integration | PR/push | `tests/e2e/run-project-venv integration` | required suite skip/not-run、ledger不闭合、非0失败 |
| e2e-standin | PR/push | `tests/e2e/run-project-venv e2e --profile all --runtime both` | 任一runtime/profile/journey未运行或失败 |
| protected-smoke | release/manual | contract声明的真实provider只读/隔离smoke | secret/environment缺失、not-run、外部unknown均阻断publish |
| required | PR/push/release | `Louke CI / required`聚合 | fail/cancel/timeout/skip/missing/unknown一律失败 |

### 7.2. Evidence

上传JUnit、coverage XML、34/34 closure JSON、IF-DES-02 checks、schema/contract parity report、prompt readback、workflow/rules/hook readback、artifact identity JSON、stand-in operation ledgers和journey report；失败时增加Playwright trace/DOM和redacted server log。每份report含source commit、design revision、facts/registry/bundle digest、Python/browser/tool版本和`mode=stand-in|real`。上传前secret-canary扫描。

---

## 8. Judge Review Checklist

- [ ] 28 FR + 6 NFR、34 AC均在§4以稳定ID显式分配。
- [ ] 每项含真实observable interface、required layer、runner/job、fixture/environment、trace与理由。
- [ ] 所有2+模块接口有integration；Human M-DESIGN主路径有CI E2E。
- [ ] 七required contract kinds、四份Agent I/O schema、Runtime唯一workflow authority、Schema Registry active/exact语义、同一release schema的Louke+Node正例、malformed mapping负例、artifact provenance和三向闭包均有正反测试。
- [ ] 异构宿主fixtures不引用彼此路径，空项目由Archer自主选择，未泛化Louke栈。
- [ ] prompt source/deployment/candidate/trusted reviewer/baseline identity闭合。
- [ ] CI/pre-commit保留用户资产，drift不静默覆盖，required fail closed。
- [ ] release identity、wheel+sdist、安装出口和publish partial/unknown恢复全部覆盖。
- [ ] Ground Truth不import`louke.*`，默认CI无生产secret。
- [ ] interfaces.md每个出口在本计划有覆盖，测试不读取私有store/schema实现。
