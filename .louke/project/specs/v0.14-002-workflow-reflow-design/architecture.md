# 工作流重构：技术设计与规范性 Agent 合同 — Architecture

- **Spec ID**：`v0.14-002-workflow-reflow-design`
- **需求基线**：Story `sha256:06d5573efbf59dd18b480d6539ad16df237fd4460f9f95d1589110cbfeec1993`；Spec `sha256:315c8d20254fceb63971b029d69c81889972eedb581621981a012f17edc8867f`；Acceptance `sha256:39b09cbf36cc0f4f0dcc8f0e8a79949049a2b6baddcecbcf2183ad407e493559`
- **范围**：定义 M-DESIGN 的实现基线以及 integration/e2e、CI、pre-commit、release/build/publish、prompt/review 的 machine contracts；本批次不执行安装、发布、Git 或阶段副作用。

## 1. 架构目标与不变量

1. Runtime 是 revision、dispatch、持久化、校验、review 记录、baseline 和阶段推进的唯一 authority；Archer/Prism只产生获授权语义结果。
2. 每个决定绑定精确 requirements、base commit、project facts、schema、prompt bundle 与 artifact digest；任何依赖变化按图传播 stale。
3. Schema 由 program-owned registry提供。七类machine contracts与Archer/Prism各自的task input/result output形成`7 + 4`个精确identity/version/digest合同；prompt和instance只引用registry schema，不能使用`current`、`digest_source`、内嵌替代schema或自证有效。
4. 所有宿主方案从 `Host Project Facts snapshot` 开始；Louke当前的 Python事实只用于本仓库 dogfood，绝不成为通用默认。
5. Test Plan、Architecture、Interfaces和machine contracts形成可程序双向解析的闭包；orphan、冲突或 unknown一律 fail closed。
6. 外部副作用使用稳定 operation identity、事实查询和持久 ledger；timeout不是失败或成功的证明。

## 2. 模块边界

| 模块 ID | 组件 | 职责 | 不负责 |
|---|---|---|---|
| `WEB` | M-DESIGN Workbench | 展示revision/facts/docs/contracts/prompts/checks/review；采集Human comment/direct edit；重连 | 计算PASS、推进阶段 |
| `DESIGN` | Design Revision Coordinator | 建立绑定输入的revision、授权allowlist、diff归属、stale传播、baseline装配 | 替Archer作语义设计或替Human作产品决定 |
| `FACTS` | Host Facts Inventory | 盘点宿主语言、工具链、版本源、artifact、outlet、CI/hooks与能力并生成snapshot | 使用Louke自身配置填补未知宿主事实 |
| `REGISTRY` | Machine Contract Registry | 发布/发现active schema；exact resolve；兼容与migration metadata | 接受instance内嵌schema |
| `CONTRACTS` | Machine Contract Compiler | 将Archer决定规范化为七类project-local instance；引用docs/facts/schema | 选择未在Architecture确定的技术方案 |
| `VALIDATOR` | Design Closure Validator | schema、引用、AC层、三文档、contract/prompt parity、scope/secret校验；结构化诊断 | 语义替代Prism review |
| `PROMPTS` | Prompt Bundle Manager | canonical source、deterministic transform、manifest/readback、active/candidate原子激活 | 热替换运行中attempt或允许candidate自证 |
| `CI` | CI Contract Generator | 生成/readback托管workflow和ruleset目标；保持用户workflow；required聚合 | 执行publish或暴露PR secrets |
| `PRECOMMIT` | Pre-commit Adapter | 合并/保留hooks的contract、安装operation与readback | 承担Red证明或最终全量gate |
| `VERSION` | Release Version Adapter | 根据宿主事实映射canonical identity、版本源、read/prepare/compare | 用branch/tag代替artifact版本 |
| `BUILD` | Build/Artifact Verifier | 真实build、完整枚举、digest/version提取、安装/运行outlet验证 | 接受源码声明替代artifact验证 |
| `PUBLISH` | Publish Recovery Ledger | 顺序、前置gate、operation identity、query/reconcile、rollback/forward-fix | 对不确定结果盲重试或伪报成功 |
| `SESSION` | Agent Session Boundary | Runtime签发task/attempt并绑定active bundle；可选subagent provider仅传输执行并回传不透明provider/session metadata；结果返回Runtime作schema校验 | 让provider拥有dispatch/current state、program validation、result persistence，或接受Agent自然语言推进/PASS |
| `REVIEW` | Prism Review Coordinator | 独立dispatch、identity-bound verdict、freshness；trusted reviewer bootstrap | 让作者写review evidence |
| `STORE` | Revision/Evidence Store | 原子持久化revision、manifest、diff、checks、review、ledger、baseline和审计历史 | 保存secret或以进程内状态为真相 |
| `MIGRATION` | Legacy Design Migrator | 旧stage/schema只读识别与单向CAS migration | 双写新旧current truth |

### 2.1 Architecture anchors

`interfaces.md` 用以下稳定 anchor 双向定位承载：

- `ARC-WEB`=`WEB`；`ARC-DESIGN`=`DESIGN`；`ARC-FACTS`=`FACTS`；`ARC-REGISTRY`=`REGISTRY`
- `ARC-CONTRACTS`=`CONTRACTS`；`ARC-VALIDATE`=`VALIDATOR`；`ARC-PROMPTS`=`PROMPTS`
- `ARC-CI`=`CI`；`ARC-PRECOMMIT`=`PRECOMMIT`；`ARC-VERSION`=`VERSION`；`ARC-BUILD`=`BUILD`
- `ARC-PUBLISH`=`PUBLISH`；`ARC-REVIEW`=`REVIEW+SESSION`；`ARC-STORE`=`STORE`
- `ARC-MIGRATION`=`MIGRATION`；`ARC-SECURITY`=跨模块信任边界（§7）

## 3. 依赖与数据流

```text
approved requirements baseline + workspace/base commit
    -> FACTS emits a typed snapshot artifact (identity/revision/kind/path; bytes digest held by manifest)
    -> DESIGN creates exact M-DESIGN revision + Runtime-authoritative Archer task manifest readback
    -> SESSION optionally transports the bound task through a subagent provider; provider/session metadata is opaque
       -> Archer writes authorized design docs + contract instances + affected prompt candidates
       -> result returns to Runtime/program for validation and persistence, never to the transport provider
    -> CONTRACTS/VALIDATOR resolves exact REGISTRY schema refs and checks instances (不替Archer生成语义决定)
    -> PROMPTS deterministically renders candidate bundle staging preview/readback (不覆盖active)
    -> VALIDATOR checks docs <-> interfaces <-> architecture <-> contracts <-> prompts
    -> REVIEW dispatches Prism with exact revision through trusted reviewer bundle
       REVISE -> new DESIGN revision -> repeat validation/review
       PASS + all program gates current
    -> STORE atomically creates implementation baseline
    -> M-IMPL (no second M-LOCK / no Human technical approval)
```

依赖方向：`WEB -> DESIGN`; `DESIGN -> FACTS/CONTRACTS/VALIDATOR/PROMPTS/REVIEW/STORE`; adapters只回传事实，不反向推进。`REGISTRY`不依赖Agent或project instance。`PUBLISH`消费CI/BUILD/VERSION已验证evidence，但不能制造它们。

### 3.1 Revision 与 stale 传播

`requirements/base/facts` → design docs → contract instances/prompt candidate → program evidence → Prism verdict → implementation baseline。任一上游digest变化使右侧全部evidence stale；历史不可改写。当前attempt绑定启动时active prompt，candidate变化只影响后续revision。写current pointer与baseline使用CAS和单事务；无法确认唯一current时为`needs_attention`。

### 3.2 Human direct diff

Human在Workbench授权路径的保存形成带actor/base/current digest的direct diff。下一Archer manifest包含该diff和去重后的inline discussions。合理修改可直接吸收；技术问题锚定discussion；Human作者身份不形成PASS。Agent lease期间只读，stale save返回current revision并保留浏览器草稿供明确重做。

## 4. 三向一致性与 machine-contract 交叉引用

### 4.1 稳定identity

- Test Plan每行以AC ID为主键，列出真实`IF-*`、required layers、宿主runner、fixture/environment、CI job、trace与理由。
- Interfaces每项给出`IF-*`、`modules`、输入/输出/状态/权限/错误/恢复及`ARC-*`。
- Architecture以`ARC-*`承载接口语义，并在组件/信任/故障边界中定义实现责任。
- contract instance的`artifact_refs`使用`{path,digest,anchors:[AC/IF/ARC]}`，命令和路径必须与三文档逐字规范化相等。

### 4.2 双向校验算法合同

1. 先解析`design-artifact-manifest`的input artifacts，以`artifact kind + path + bytes digest`回读Host Project Facts与Archer task manifest；`project.toml`、review bytes或只有sha格式的字符串都不能替代对应kind。再从Acceptance枚举34个AC，要求Test Plan恰有当前策略行且required layer非空。
2. 解析每个Test Plan `IF-*`，必须在Interfaces唯一存在；所有Interfaces也必须至少被一个策略或公共contract策略引用。
3. 每个Interfaces的状态/权限/错误/恢复至少有一个`ARC-*`，anchor必须存在且模块集合与`modules`相容。
4. 对每个contract读取IF-CON-01 canonical envelope，使用`manifest_ref(identity,revision)+kind`解析外部manifest中的instance bytes digest；再读取`artifact_refs`与`payload.commands/failure_policy`，规范化比较路径、命令、状态和failure语义。instance不得含自引用digest或第二套digest scope。
5. Schema先递归拒绝所有影响执行、权限、状态、失败与evidence的缺失/未知嵌套字段；随后运行artifact resolver与closure parity。输出IF-DES-02结构化定位；任一步unknown均阻止baseline。Prism再独立检查语义完整性，程序结果不替代review。

### 4.3 本 revision 的 candidate artifact topology

所有新增machine-readable工件都位于`.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/`，由`design-artifact-manifest.candidate.json`统一枚举bytes digest：

```text
registry/registry.candidate.json
registry/schemas/{7 kinds}-1.0.0.schema.json       # owner=Runtime/program, candidate
registry/agent-io/{archer,prism}-{task-input,result}-1.0.0.schema.json # 2 inputs + 2 outputs
inputs/host-project-facts.snapshot.json            # typed repo-facts readback, not project.toml bytes
inputs/archer-author-task-manifest.candidate.json  # Runtime dispatch contract readback; candidate, not active Runtime state
contracts/{7 kinds}.candidate.json                # Archer instances, refs only
prompts/prompt-bundle.candidate.json
prompts/deployment-readback.candidate.json
prompts/reviewer-binding.candidate.json
prompts/staging/{archer,prism}.render.candidate.json # exact in-memory render digest/readback; staging only
runner/project-runner.candidate.json
validation/release-version-node-host.valid.candidate.json # same release schema, heterogeneous Node/SemVer positive
validation/negative-schema-fixtures.candidate.json
validation/schema-validation-record.candidate.json # design-time check record, not activation evidence
```

Candidate staging path与最终安装path严格分离：Registry最终进入package-owned`louke/schemas/**`；instances最终进入`.louke/project/contracts/<spec-id>/<kind>.json`；prompt部署最终由Runtime的active pointer选择`.opencode/agents/**`；runner/project最终修改现有runner和`project.toml`。本revision的schema validation record只证明candidate bytes的正负验证，不宣称active registry、runner collection、deployment或PASS。Runtime在Devon实现、required tests、artifact readback和本轮trusted Prism review均current后一次性CAS激活registry/prompt/baseline；任一partial/unknown保持旧active并fail closed。

## 5. 宿主项目事实隔离与适配策略

### 5.1 事实盘点先行

`FACTS`从当前base commit和workspace读取实际文件/入口，记录present/absent/unsupported，不以扩展名猜完后静默采用。最少盘点语言/runtime、dependency/lock、build/test、version source、artifact、安装/部署/运行outlet、default branch、CI、hooks、外部能力。每个Architecture选择引用facts observation identity。

已有项目优先复用有效入口；冲突时Architecture明确兼容/迁移。空白项目以空facts和产品约束为输入，由Archer自主选择完整成熟方案并记录替代、风险、license；不向Human提技术问题。无法支持的能力输出带contract kind和facts identity的显式诊断，不回退Python/Node/Java默认。

### 5.2 Louke dogfood事实（不泛化）

当前workspace实际是MIT Python package：`pyproject.toml`要求Python>=3.11，setuptools build，root `[project].version`，console script `lk`；测试为pytest，existing runner在`tests/e2e/run-project-venv`；artifact为wheel+sdist；现有CI为`.github/workflows/ci.yml`/`release.yml`；pre-commit已有Keeper、ruff、mypy等hooks；release adapter为`tools/louke_python_release_adapter.py`。这些只决定本仓库002实现与发布合同。

## 6. 核心组件设计

### 6.1 Registry 与 Schema Store

Registry manifest和schema随program package发布，schema使用JSON Schema 2020-12，canonical JSON采用UTF-8、排序key、无非语义空白后SHA-256。required kinds各有独立identity/version；Agent I/O在同registry的独立namespace中固定为Archer task input、Archer result output、Prism review task input、Prism review output四份。两个task input schema递归定义stage/spec/revision、所有输入identity/digest、allowed write set、forbidden effects、output contract、freshness；Prism另要求trusted reviewer execution与reviewed candidate binding。active/candidate/retired显式，resolve必须exact。升级优先兼容读取；不兼容时只提供声明的单向migration并保留source evidence。

Contract canonical envelope固定为`{kind,identity,revision,schema_ref,manifest_ref,scope,generated_by,compatible_runtime,artifact_refs,payload}`。`payload`是commands、failure policy及kind-specific字段的唯一位置。instance不含自身bytes digest；resolver按`manifest_ref.identity + manifest_ref.revision + kind`在外部design manifest定位唯一`path + digest`并返回`contract_digest`。这样digest覆盖完整instance bytes且不产生自引用循环。facts/task provenance同样必须解析到manifest中声明的artifact kind/path/digest，不能只检查sha格式。

Candidate gate以`jsonschema==4.25.1`先执行11份schema meta-validation，再验证Runtime-authoritative Archer task、7份Louke contract正例，以及同一`release-version` schema下的Node/SemVer异构宿主正例；Prism task schema使用in-memory Runtime dispatch valid shape验证。随后逐一应用八个negative fixtures：原五项边界，加上release mapping缺branch、tag类型错误和version source未知字段，必须分别在schema/provenance resolver失败。异构正例失败或任一负例意外通过都视为validator失败，不得生成baseline。

### 6.2 Prompt Bundle Manager

canonical source、transformer、environment binding、deployment各自有digest；bundle digest覆盖每个role的source digest、精确input/output schema identity/version/digest、transformer与rendered digest，禁止`current`或`digest_source`占位。现有真实transformer是`louke.board.cmd_opencode`（source=`louke/board.py`）：读取`louke/agents/*.md`，解析frontmatter，以`.louke/models.json`/用户alias和provider inventory把`intelligence_quotation`解析为具体model，保留permission等passthrough字段、移除source-only `name`/quotation，并将正文写到`.opencode/agents/<lower-name>.md`。本candidate锁定transformer identity=`louke.board.cmd_opencode`、version=`board.py@base-2734177`、source digest和environment binding model=`codexmanager/gpt-5.6-sol`；candidate staging使用同一转换规则但输出Spec-local staging目录，绝不运行会覆盖active的`lk board opencode`。

部署是纯确定转换，model binding不能改语义正文。candidate manifest与readback分别记录source bytes、transformer source、rendered bytes；readback的`candidate_staging_in_sync`只证明staging与声明转换一致，不冒充active deployment。当前active `.opencode/agents/{archer,prism}.md`保持不变并记录digest；当前Prism review由该先前trusted active prism digest执行，评审新candidate bundle，二者不得相同或由candidate自证。激活在schema/lint、IF-DES-02、trusted Prism、staging readback、artifact clean-install readback和baseline均完成后，以CAS原子交换pointer。普通宿主project facts只进入task manifest，不写回package prompts。

### 6.3 CI Contract Generator

Generator只写owner marker的`.github/workflows/louke-ci.yml`，canonical render后readback。其它workflow/rules保留。ruleset由Runtime另以owner identity管理并回读。job结果聚合fail closed，publish仅接受同一commit `Louke CI / required`。外部修改产生diff/conflict，不以重新生成静默覆盖。

### 6.4 Pre-commit Adapter

Adapter先snapshot已有hooks，再按identity合并managed hooks，preserved hooks顺序与entry不可丢。安装是Runtime后续operation；design/implementation Agent不执行。pre-commit只运行快速format/lint/static/secret/trace和可在预算内unit子集；全量integration/e2e/build仍归CI。

### 6.5 Version、Build 与 Artifact

通用`release-version` schema只固定严格envelope、required release mapping、类型和所有层级`additionalProperties:false`，不固定release/spec/revision/manifest/runtime、语言、路径、adapter或命令；这些均由project-local instance从Host Project Facts选择。`design-artifacts/validation/release-version-node-host.valid.candidate.json`以`package.json`、SemVer、Node `.mjs` adapter和npm命令证明同一schema可承载非Python宿主。对Louke 0.14.0：external/tag=`v0.14.0`，canonical=`0.14.0`，branch=`releases/0.14.0`，权威源=`pyproject.toml [project].version`，adapter=`tools/louke_python_release_adapter.py`。现有`prepare`/artifact `inspect`继续复用；Devon按IF-REL-01补齐确定的`inspect-source`，不另选adapter。隔离build workspace prepare后执行`python -m build`，验证wheel和sdist metadata、SHA-256、clean install后的`lk --version`与`importlib.metadata.version("louke")`，并确认Archer/Prism prompts和schema registry进入两类artifact。无独立deployment outlet（本产品为本地package）。

Evidence严格分为：方案已确定、版本源已准备、artifact已构建、artifact版本/安装出口已验证。只有最后一项全量verified允许publish。

### 6.6 Publish Recovery Ledger

每个适用operation在外部调用前持久化stable identity和expected fact；调用后持久化observed fact。网络/进程中断后先query exact identity，再决定补记、同identity重试或needs_attention。不可变tag/PyPI version不回滚覆盖；partial publish保留已确认项，安全时forward-fix。凭据只保存reference，永不进evidence。

### 6.7 Existing runner 的 foundation migration（Devon首任务）

复用现有`tests/e2e/run-project-venv` shell bootstrap及`tests/e2e/run_e2e.py`，不创建第二入口。当前事实是integration仅传`tests/integration/install_experience`，e2e `all`仅展开`install/chromium`并运行旧paths；`project.toml.paths`不参与脚本discovery。Devon的首个foundation task按`design-artifacts/runner/project-runner.candidate.json`修改：

- integration按固定顺序收集历史path加`tests/integration/v014_design_contracts`；
- e2e新增`design-contracts` profile，`all`固定展开`install,chromium,design-contracts`，每个profile按请求的`local/global/both`installed-wheel runtime执行；
- 每次调用先建立expected collection/AC-layer manifest，pytest JUnit与runner evidence对账；required path缺失、零收集、漏node/AC/layer、skip/not-run/unknown/timeout/cancel、service lifecycle或teardown失败统一非0；
- `design-contracts` profile由runner在隔离HOME/XDG/workspace启动installed-wheel的`lk web --host 127.0.0.1 --port <allocated>`，`GET /health`验证expected version后启动Chromium，finally按TERM→10秒→KILL清理整个进程组并保留redacted evidence。

选择扩展现有runner而非直接`pytest tests/**/v014...`，解决installed-wheel local/global身份、历史suite兼容和Workbench生命周期一致性；放弃新脚本避免公开入口分裂。风险是profile矩阵耗时与漏收集，使用expected-vs-collected证据、40分钟job timeout和fail-closed聚合控制。candidate未安装前，Runtime不得把当前命令的0当本Spec PASS。

## 7. 安全、信任与故障边界

| 边界/故障 | 状态与恢复 | 禁止行为 |
|---|---|---|
| untrusted Human/project diff → design | allowlist、path containment、secret scan、CAS；冲突保留diff | 越界写、自动纳入baseline |
| Agent result → Runtime | exact task/attempt/bundle/schema/scope验证 | Agent自报PASS/推进 |
| candidate prompt → active | trusted reviewer + readback + atomic activation | candidate reviewer自证、热加载 |
| PR code → GitHub Actions | `contents: read`、无production secret；stand-in | `pull_request_target`运行fork代码、写token |
| Runtime → GitHub/PyPI | protected environment、最小分操作credential、ledger | secret写prompt/log/fixture |
| external timeout/ack loss | `uncertain`，query-before-retry | timeout后重复create/publish |
| persistence restart/corruption | digest链恢复；不一致fail closed并保留历史 | 空状态当成功、重复dispatch |
| schema/legacy migration | exact version、单向CAS、可重试 | 猜字段、双写两个current truth |

## 8. 技术选型、第三方依赖与取舍

| 选型 | 版本合同 | 解决问题 | 放弃方案 | 风险与控制 |
|---|---|---|---|---|
| Python | 继承宿主`3.11–3.14`支持矩阵 | 复用现有Runtime/Web/adapter | 迁移语言 | 多版本差异；unit矩阵 |
| `jsonschema` | `4.25.1`（MIT） | JSON Schema 2020-12 active schema校验和pointer诊断 | 手写validator、Pydantic-only schema | format checker差异；固定版本与golden contract |
| PyYAML | 继承`>=6,<7`，CI constraints固定`6.0.2` | workflow parse/readback | 自写YAML、ruamel新增依赖 | 注释/排序丢失；只管理canonical owner file，比较语义+digest |
| stdlib `hashlib/json/sqlite3` | Python runtime | canonical digest、持久revision/ledger | 外部DB/内容寻址服务 | canonicalization错误；独立ground truth |
| pytest | `8.4.1` | unit/contract/integration统一 | unittest分套 | plugin漂移；constraints固定 |
| pytest-cov | `6.2.1` | >=95%附加门禁 | 仅AC trace | coverage不证明语义；保持独立closure |
| Playwright | `1.54.0` + bundled Chromium | M-DESIGN真实用户surface E2E | API冒充UI、Selenium | browser下载；固定cache revision |
| build | `1.2.2.post1` | 真实wheel/sdist | 只看source version | backend漂移；clean build |
| pre-commit/mypy | `4.6.0` / `1.16.1`（CI tool constraints） | 快速hooks与static gate | 人工检查 | 当前repo hook revisions更高；contract readback识别并由新baseline显式升级，不静默覆盖 |

新增`jsonschema`是唯一运行时schema校验依赖；其MIT license兼容。具体constraints由Devon在宿主配置实现，不将这些版本写入通用宿主contract默认。

## 9. GitHub Actions CI 设计（Louke宿主实例）

### 9.1 触发、runner、权限与缓存

- Devon创建`.github/workflows/louke-ci.yml`；保留既有`ci.yml`和`release.yml`，后者迁移为只信同commit稳定check及artifact evidence，不再按workflow文件名轮询。
- PR/push目标`main`, `releases/**`；`workflow_dispatch`支持stand-in重跑；tag/release另跑protected publish prerequisites。
- `ubuntu-22.04`为quality/build/integration/e2e；unit Python矩阵`3.11,3.12,3.13,3.14`。顶层`contents: read`，PR无secret。actions固定major（checkout v4、setup-python v5、upload/download-artifact v4）；pip/Playwright cache key含OS、Python、`pyproject.toml`和constraints/browser digest。

### 9.2 Job DAG 与命令

```text
quality ─┬─> build-artifacts ─> artifact-verify ─┬─> unit[3.11..3.14]
         │                                       ├─> integration
         │                                       └─> e2e-standin
         ├─> design-contract ─────────────────────────┐
         └─> ac-trace ────────────────────────────────┤
all mandatory jobs ───────────────────────> Louke CI / required
```

| job | 宿主命令合同 | timeout | evidence |
|---|---|---:|---|
| `quality` | `pre-commit run --all-files`; `python -m mypy louke` | 10m | logs、hook digest |
| `build-artifacts` | `python -m build` | 15m | wheel、sdist、build log |
| `artifact-verify` | IF-REL-01/IF-BLD-01 inspect + clean install/outlet/prompt/schema检查 | 15m | artifact identity JSON |
| `unit` | `python -m pytest -q tests/unit --cov=louke --cov-report=xml --cov-fail-under=95` | 20m | JUnit；3.12 coverage XML |
| `integration` | `tests/e2e/run-project-venv integration` | 30m | JUnit、contract/readback/ledger reports |
| `e2e-standin` | `tests/e2e/run-project-venv e2e --profile all --runtime both` | 40m | journey、失败时Playwright trace/DOM/log |
| `design-contract` | IF-DES-02 validate当前design manifest；该入口由本Spec实现 | 10m | structured checks/evidence digest |
| `ac-trace` | `python tools/check_ac_traceability.py --acceptance .louke/project/specs/v0.14-002-workflow-reflow-design/acceptance.md --tests tests`（由本Spec实现，不依赖旧`lk agent`） | 10m | 34/34 closure JSON |
| `Louke CI / required` | `if: always()`检查所有required needs精确success | 5m | 单一稳定check |

任一job fail/cancel/timeout/skip/missing/unknown均使聚合失败。真实GitHub/PyPI smoke不在fork PR运行；release protected environment缺失/not-run视为publish blocker而非PASS。evidence上传前secret-canary扫描；测试报告14天、build artifact 7天。

## 10. 关键取舍

1. **版本化registry而非prompt示例**：程序可独立校验和迁移；代价是schema生命周期治理，使用exact refs和active状态控制。
2. **project-local typed contracts而非固定语言模板**：可移植且可审计；代价是adapter数量增加，以facts snapshot和unsupported诊断约束。
3. **三文档anchor closure而非自由文本交叉引用**：可定位orphan；代价是作者需维护稳定ID，由validator自动检查。
4. **deterministic managed CI file + coexistence**：Louke能托管required gate又不覆盖用户CI；代价是外部编辑必须走diff/revision。
5. **prompt candidate双bundle审查**：避免reviewer自举攻击；代价是激活延迟一个完整review/readback周期。
6. **persistent publish ledger而非workflow重试**：partial/unknown可恢复；代价是provider事实查询复杂，但避免重复tag/upload。
7. **无第二Human技术锁**：保持技术责任在Archer/Prism/program gates；后续有效gap仍可新建M-DESIGN revision，不把baseline永久冻结。

## 11. 实现边界与技术风险

- 现有Runtime仍包含旧M-LOCK协调语义；迁移必须确保新run不再写第二设计锁，同时旧history可读，避免双truth。
- 当前仓库尚无active program-owned machine schema registry、design contract CLI和AC trace tool；本revision提供7类machine schema/instance及2 input + 2 output Agent I/O schema **candidate** 和exact digest，Devon需按candidate实现package registry/validator，不能换成prompt内schema。激活前`SCHEMA_NOT_ACTIVE`是预期fail-closed；design-time validation record不是active验证状态。
- 当前`project.toml`仍声明`0.13.1`、001 Spec和`releases/0.13.1`，runner也不收集v014 suites；本轮禁止提前修改它们。implementation baseline必须把runner discovery/evidence与project identity同步列为Devon首个foundation task，完成readback前integration/e2e为`not-run`。
- PyYAML round-trip不保留用户注释；故generator只管理独立owner file，不能重写用户workflow。
- GitHub ruleset能力与token权限可能因repository plan变化；readback不确定必须阻断并显式fallback branch protection，不能假设成功。
- Prompt transformer涉及frontmatter/model/skill转换；canonicalization若覆盖语义字段会产生假一致，必须用source/deployed双digest与golden fixture。
- PyPI与GitHub Release eventual consistency可能使publish查询短暂unknown；ledger需有界退避后进入needs_attention，不得重复上传。
