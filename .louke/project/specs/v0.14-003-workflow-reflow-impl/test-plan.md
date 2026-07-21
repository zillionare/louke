# 工作流重构：实现、验证、安全与发布闭环 — Test Plan

- **Spec ID**: `v0.14-003-workflow-reflow-impl`
- **Created**: `2026-07-20`
- **Bound Story**: `sha256:2a04c965b8c97a34a6aec9cf5a7aa1418d84f394830abe5bdf32c2333a10ea3e`
- **Bound Spec**: `sha256:a5c95c7a7ea1f8237913d9779fbc598d679211ece9be314ace944874b706280a`
- **Bound Acceptance**: `sha256:a19e25689e59f722d2b72d6903ce4be1b333cf0441c5e3b14a351f6566dfe287`
- **Related acceptance**: `.louke/project/specs/v0.14-003-workflow-reflow-impl/acceptance.md`
- **Related interfaces**: `.louke/project/specs/v0.14-003-workflow-reflow-impl/interfaces.md`（Stage 2 assertion basis；本计划 §1.6 先锁定稳定 `IF-*` identity）
- **Inherited design contracts**: `v0.14-002-workflow-reflow-design` 的 current Architecture/Interfaces/Test Plan，尤其 `IF-TST-01`、`IF-PC-01`、`IF-CI-01`、`IF-REL-01`、`IF-BLD-01`、`IF-PUB-01`、`IF-PRM-01`

## 1. Stance and Boundaries

### 1.1. Black-box Statement

断言只落在公开可回读事实：Workflow/Project current 与历史 surface、Runtime API/read model、task graph/manifest、受控 Git commit/ref、结构化 gate/review/test/CI/security evidence、真实 artifact、安装后版本出口、operation ledger 和 provider query/readback。Agent 的自然语言“PASS/完成”、命令摘要、进程内状态、私有数据库字段或 branch/tag 声明不能证明验收。

本仓库 dogfood 事实是 Python `>=3.11`、setuptools、pytest、wheel+sdist、console script `lk`；这些事实只用于 Louke 自身实现和 artifact 验证。嵌套宿主 fixture 必须只消费各自 project-local contracts，不得把 Louke 的语言、路径或构建命令泛化为默认。

### 1.2. Non-observable Objects (tests do not directly depend on)

- Runtime 内部类层次、调度队列、cache、锁对象和未提交内存；
- Agent 私有会话文本、模型思维过程和自报执行结果；
- Git 操作包装器的调用次数；Git 真值由独立 Git CLI/对象图读取；
- GitHub/PyPI stand-in 的内部字段；只读其公开协议响应和 append-only call ledger；
- UI 组件树、CSS 与未保存浏览器内存；交互只断言可见状态、动作可用性、反馈与恢复。

需要的状态若未由 §1.6 identity 在 Stage 2 的 `interfaces.md` 暴露，即为 testability gap；不得用私有 store 查询或内部 mock 绕过。

### 1.3. Cheating Patterns (CI enforced interception)

| # | 禁止模式 | 阻断证据 |
|---|---|---|
| 1 | 修改断言迎合实现、单独断言非空、`assert True` | anti-pattern scan + Prism 测试语义 review |
| 2 | required suite 被 selector 排除、非法 skip/quarantine、只跑当前 Spec 新测 | suite inventory 与 runner report 不闭合，`Louke CI / required` 失败 |
| 3 | mock Runtime gate、task graph、lease、RGR lineage、freshness、ledger 核心后声称 integration 通过 | fixture/import review 失败；这些核心必须真实接线 |
| 4 | 以被测 Runtime 输出生成 expected graph、Git lineage、trace 或版本 | Ground Truth isolation 失败 |
| 5 | 把普通 pre-commit 失败当合法 Red，或让私有 `R` 运行普通 pre-commit/CI | IF-RGR-01 evidence 与 Git 真值不一致 |
| 6 | 只按 commit 时间推断 Red 先于 Green，不证明 `B→R`/`R→G` tree 与 sibling parent | Git object Ground Truth 失败 |
| 7 | 用同名绿色 check、其它 commit/run 或 Agent 转述冒充 candidate required CI | IF-CI-02 identity/readback 失败 |
| 8 | 只看 source/tag，未真实构建、逐 artifact 提取版本并 clean install | IF-BLD-02 artifact gate 失败 |
| 9 | timeout/ack loss 后盲重试 tag/upload/release，或用 `--skip-existing` 推断相同 | IF-PUB-02 query-before-retry 场景失败 |
| 10 | fixture、prompt、diff、log、evidence 或 CI artifact 回显 secret canary | security gate 失败并拒绝上传 evidence |

### 1.4. Safeguards (CI checks + PR process)

1. 每个自动化测试首行 docstring/邻近注释至少包含一个规范 ID `AC-FRXXXX-YY` 或 `AC-NFRXXXX-YY`。继承 002 已锁定、由 Devon 实现的 `tools/check_ac_traceability.py`，对本 Acceptance 执行 36/36 双向 closure，并校验 required layer evidence。
2. 每个 §4 策略行的 `IF-*` 必须在 Stage 2 `interfaces.md` 唯一存在；所有 003 interface 也必须至少被一个策略行引用。identity 缺失、重复或层级下降阻断 M-DESIGN baseline。
3. required integration/e2e 不允许 skip；正式 quarantine 必须含 policy digest、Issue、owner、范围、expiry，且不得覆盖本 Spec 的 required journey。
4. fault injection 仅作用于外部 Agent/provider、clock/UUID、filesystem、process kill、网络 ack、Git CAS 竞争和测试 fixture；不得替换被测 Runtime 的判定、状态转换、trace、freshness 或 reconcile。
5. coverage `>=95%` 是附加门禁，不能替代 36/36 trace、contract、integration、e2e、CI E2E、artifact/install 或 security evidence。
6. 测试变更 PR 必须分类为 AC/Spec 变化或带 Issue 的 flake/environment 修复；“实现行为不同所以改测试”不可接受。

### 1.5. Test Division of Labor

- **Devon**：unit、contract、公开 read model/CLI adapter 配套测试、workflow 实现及 trace/anti-pattern 工具。
- **Shield**：全部跨模块 integration、公开 workflow e2e、GitHub CI E2E、异构宿主、并发/重启/partial-result 场景和 security journeys。
- **独立测试审查者**：Ground Truth、failure fingerprint、Git object lineage、suite inventory、artifact extraction 与 provider ledger 语义。
- **Runtime**：独立执行并持久化 program evidence；Agent 运行结果不成为 gate。
- **Prism/Judge**：分别评审测试/实现语义与深度安全；不编写或持久化自己的 PASS evidence。

### 1.6. Stable Observable Interface Identities

以下 identity 在本计划锁定，Stage 2 必须原样复用并补齐 schema、权限、错误和 `modules`；测试不得自行另造出口。

| Identity | 公开可观察出口 | 主要断言 |
|---|---|---|
| `IF-WFR-01` | WorkflowRun/Project current、历史 API/UI、allowed actions | canonical stage/context、状态、stale/unknown、Human 动作、重连与继续/返回路径 |
| `IF-IMPL-01` | implementation baseline 与 pre-commit reconcile readback | 输入 digests、workspace attribution、hook/config identity、阻塞诊断、受控 infrastructure commit |
| `IF-TASK-01` | implementation task DAG、task manifest、write lease read model | AC/Issue/责任/依赖/scope/command/output 闭包、revision、lease owner/冲突、external diff |
| `IF-RGR-01` | Red gate/checkpoint 与 `B/R/G/(Refactor)` lineage evidence；公开 Git object/ref | test-only、failure fingerprint、private ref CAS、sibling lineage、正式 commit/pre-commit、no-change |
| `IF-REV-02` | implementation/test/candidate review input/result read model | review kind、精确 input/evidence digest、actor、PASS/REVISE、freshness、findings/route |
| `IF-TEST-02` | Shield test patch、suite inventory、execution/result/defect routing evidence | contract paths、AC metadata、公开出口、runner/environment/fixture、required suite 运行与分流 |
| `IF-CAND-01` | candidate freeze/freshness read model | 唯一 commit、clean workspace、正式 ancestry、写入禁用、依赖变化后的 stale 集合 |
| `IF-QUAL-01` | candidate 本地权威质量链 report | format/lint/static/type、all-files、RGR、全部历史 unit、required integration/e2e、trace、真实 build |
| `IF-CI-02` | candidate GitHub run/jobs/artifacts/check 与 ruleset/branch-protection readback | repository/workflow/commit/attempt identity、suite coverage、job conclusion、唯一 required check、用户规则保留 |
| `IF-BLD-02` | release execution 的版本源/build/artifact/install evidence | canonical identity、source prepared、wheel+sdist built/digest/version、每件 clean-install outlets |
| `IF-SEC-01` | security program results、Judge input/verdict、finding/skip/route read model | policy/candidate identity、scan completeness、severity/impact/fix、不可 waiver、修复重跑 |
| `IF-REL-02` | Project current 的 release preview 与 `Release/Delay/Return` action result | preview identity、全部 gate/artifact/风险/副作用、动作可用性、waiting/upstream/stale 反馈 |
| `IF-PUB-02` | publish operation ledger 与 provider fact readback | stable operation identity、intent/query/result、confirmed/unknown/needs_attention、无重复副作用 |
| `IF-TRACE-01` | 双向 trace export、archive manifest、只读 history 与 next-release eligibility | FR/NFR→AC→task/R/code/test/CI/artifact/release、归档、Red ref 精确清理、closing/complete |
| `IF-PROMPT-02` | 003 canonical prompt bundle manifest/readback 与 role capability report | Archer/Devon/Shield/Prism/Judge/Librarian/Keeper/Maestro 的职责、工具/scope、输入输出 identity |
| `IF-MIG-01` | legacy run/stage/evidence/prompt migration/read-only export | source/target schema、只读或 migrated、CAS、单一 current authority、可重试诊断 |

002 的 `IF-PC-01`、`IF-TST-01`、`IF-CI-01`、`IF-REL-01`、`IF-BLD-01`、`IF-PUB-01`、`IF-PRM-01` 是 003 执行时消费的 project-local machine contracts；003 新 identity 是 Runtime 执行结果/用户可观察状态，不复制或取代这些 contracts。

---

## 2. Test Environment

### 2.1. Directory Layout (project customization)

```text
tests/
├── unit/
│   └── v014_workflow_impl/          # Devon：规则、schema、fingerprint、freshness、prompt contract
├── integration/
│   └── v014_workflow_impl/          # Shield：Runtime/store/Git/runner/stand-in 真实接线
├── e2e/
│   ├── v014_workflow_impl/          # Shield：installed wheel + public API/UI journeys
│   └── run-project-venv             # 已有 project-venv bootstrap
├── fixtures/
│   └── v014_workflow_impl/          # repos、graphs、RGR、agents、policies、providers、legacy
└── ground_truth/
    └── v014_workflow_impl/          # 不 import louke.* 的 Git/trace/artifact/provider 真值
```

当前 manifest 只授权本文件，故不修改 `project.toml`。已有宿主运行合同保持：integration=`tests/e2e/run-project-venv integration`，e2e=`tests/e2e/run-project-venv e2e --profile all --runtime both`，framework=`pytest`，cwd=`.`。新增资产放入现有 `tests/` 路径，由 runner 发现；Shield 不选择新框架或入口。

### 2.2. Naming Conventions

- 文件按公开行为命名 `test_<journey_or_contract>__<condition>.py`，不按私有类名命名。
- markers：`integration`、`e2e`、`chromium_e2e`、`real_opencode`；新增真实 GitHub sandbox 场景使用 Stage 2 必须登记的 provider-smoke marker，默认 fork PR 不运行。
- fixture identity 至少含 `base_commit`、`run/task/attempt`、requirements/design/prompt/schema/policy digest、canonical release identity；目录名不代表 PASS。
- 每次并发/重启场景使用独立 HOME/XDG/Git config/store/repository/provider namespace；失败后 teardown 仍执行，但先保存并脱敏 evidence。

### 2.3. Execution and Required Layers

| 层 | 入口/runner | 环境 | CI gate | 边界 |
|---|---|---|---|---|
| Unit (`U`) | `python -m pytest -q tests/unit --cov=louke --cov-report=xml --cov-fail-under=95` | Python 3.11–3.14；可控 clock/UUID | `unit` | 纯规则、schema、身份、fingerprint、权限、freshness；不证明跨模块 |
| Contract (`C`) | 同 pytest runner 中的 003 contract suite + 002 project-local contract validators | Python 3.12；locked schemas/prompts/contracts | `workflow-contract` | public payload、exit/failure 语义、prompt capability、workflow render/readback |
| Integration (`I`) | `tests/e2e/run-project-venv integration` | clean tmp Git repos、真实 subprocess/store/files、Agent/provider stand-ins | `integration` | Runtime↔Git/store/runner/contract/provider 接线、CAS、kill/restart、routing |
| E2E (`E`) | `tests/e2e/run-project-venv e2e --profile all --runtime both` | built wheel、clean project venv、live API/Workbench/Chromium、stand-ins | `e2e-standin` | 公开主流程、Human Release/Delay/Return、history/next release；不调用私有推进 API |
| CI E2E (`CE`) | 托管 `.github/workflows/louke-ci.yml` 在精确 fixture candidate 上运行；Runtime 经 GitHub API 回读 | 每 PR 使用 GitHub protocol stand-in；protected/manual 使用隔离 GitHub sandbox | `ci-e2e` | job/suite/check/rules provider 闭环；真实 sandbox 不使用生产发布 secret |
| Artifact/version/install (`A`) | `python -m build` + 002 `IF-REL-01`/`IF-BLD-01` adapter/readback | clean build tree + 每件 artifact 独立 clean venv | `build-artifacts`,`artifact-verify` | `pyproject.toml` source → wheel+sdist → metadata/digest → `lk --version`/`importlib.metadata` |
| Security (`S`) | current policy-declared scanners + pytest security journeys + Judge schema contract | candidate bytes、dependency manifest、secret canaries；无真实 credential | `security` | secret/SCA/SAST/project checks、角色权限、finding route/waiver/skip、Judge identity |

默认 DAG：`quality → workflow-contract/ac-trace → build-artifacts → artifact-verify → unit/integration/e2e-standin/ci-e2e/security → Louke CI / required`。任一 required gate fail/cancel/timeout/skip/missing/unknown，聚合不得成功。

### 2.4. Test Data (required)

| Fixture family | 内容与用途 |
|---|---|
| `baseline_precommit_matrix` | current/missing/stale design review、clean/dirty/unattributed workspace、preserved/drifted hooks、hook rewrite/failure |
| `task_graph_matrix` | valid vertical DAG；duplicate/missing/cycle/scope conflict/orphan；revision mutation；design/product gap |
| `lease_manifest_matrix` | 完整/缺字段 manifest，两个竞争 writers，Human/external/unknown diff，path traversal/symlink escape |
| `red_failure_matrix` | 合法行为 assertion、合法 missing-symbol type failure、unexpected PASS、syntax/dependency/fixture/env/permission/unrelated failure、伪断言 |
| `rgr_git_matrix` | `B/R/G/Refactor` objects、same-attempt CAS race、wrong parent/tree、remote leak、test mutation、hook rewrite、no-change |
| `review_agent_matrix` | Prism review kinds与 stale/REVISE；Agent outputs、invalid schema/identity、越权 commit/push/state evidence |
| `test_suite_matrix` | 历史 unit/integration/e2e inventory、required/current suites、illegal skip/quarantine、四类 M-TEST defect |
| `candidate_quality_matrix` | clean/dirty freeze、private R ancestry、post-freeze changes、局部 selector、历史失败、document/migration/build failure |
| `github_ci_matrix` | required jobs全结论、其它 SHA/attempt、同名伪 check、suite exclusion、rules partial success/readback mismatch、用户规则 |
| `release_artifact_matrix` | canonical `0.14.0`/tag `v0.14.0`、source mismatch、wheel/sdist missing/corrupt/wrong version、old installed outlet、prompt/schema omission |
| `security_matrix` | secret/SCA/SAST/project scanner结果、Judge stale/invalid finding、四类 route、critical/high waiver、policy skip、敏感边界 |
| `release_ui_matrix` | current/stale preview、Release disabled/enabled、Delay/reopen、合法/非法 Return、dirty/stale/conflict/reconnect |
| `publish_matrix` | merge/tag/PyPI/GitHub Release/smoke 的 success/fail/ack-loss/zero/multi/conflict/partial truth 与 process kill |
| `archive_matrix` | 完整/缺失 trace、archive failure、Red evidence缺失、foreign refs、cleanup retry、closing/complete/next-release eligibility |
| `host_matrix` | Louke Python wheel+sdist、Node tarball fixture、unsupported adapter；各自 hooks/workflows/rules/contracts |
| `legacy_matrix` | 旧 Maestro/Agent run、旧 stages、无 Red ref evidence、旧 prompt/schema、migration kill/retry |
| `secret_canaries` | 唯一 synthetic token/key/cookie；只从不可信输入注入，任何输出不得包含原文 |

全部 fixture 为合成或最小临时 Git repo，manifest 固定生成器/digest。unit 与 e2e 使用不同 run/release/task identity 和数据，避免对同一 golden 过拟合。

### 2.5. Public User/Agent Journeys

| Journey | Surface/context 与动作 | 可见结果、可用条件与恢复 |
|---|---|---|
| `J-IMPL-RGR` | current Project 从已通过 M-DESIGN 继续；Runtime dispatch Archer/Devon/Prism stand-ins | task graph/revision、lease、Red→review→Green→Refactor/none 按 IF-TASK-01/IF-RGR-01/IF-REV-02 可见；blocked/stale 显示原因且无越权继续动作，重连恢复同一 attempt |
| `J-TEST-VERIFY` | 完成 tasks 后 Runtime dispatch Shield，随后 freeze candidate 并触发本地与 GitHub gates | IF-TEST-02 显示 runner/fixture/suites/route；IF-CAND-01/QUAL-01/CI-02 显示同一 commit。执行中不可写；失败可回到定义目标，旧 evidence 显示 stale |
| `J-RELEASE-DELAY` | Project current 打开 current preview，Human 选择 Delay，断开并重连后再次打开 | `Release` 仅 gates current 时 enabled；Delay 后 release-waiting、candidate/preview 不变且无外部副作用；可继续决定 |
| `J-RELEASE-RETURN` | Human 在 preview 输入原因并选 definition 允许目标；另尝试非法目标 | 合法目标进入对应上游 context，受影响 facts 显示 stale/superseded；非法目标不改变 context；旧 approval 不可继续 |
| `J-PUBLISH-CLOSE` | Human Release；Runtime 在 stand-ins 执行并于 ack-loss/restart 后 reconcile | operation逐项 planned/executing/confirmed/unknown；未知为 needs_attention且无重复；验证后 history只读、trace完整、仅归档Red refs删除、下一release入口 enabled |
| `J-HOTFIX` | 从已发布 Issue/source contract 启动 bug_fix；分别提供偏差与新行为 | 偏差进入隔离 `fix/{issue}` 并复用全链；新行为退出 hotfix；active releases 不串写，冲突为 needs_attention |

---

## 3. Ground Truth Method

### 3.1. General Principle

| 断言 | 独立 Ground Truth |
|---|---|
| task DAG/AC closure | `tests/ground_truth` 独立解析 Acceptance 与 task fixture，用标准拓扑算法检查节点/边/责任；不调用被测 graph validator |
| test-only 与 R/G lineage | Git CLI `cat-file`、`rev-parse`、`merge-base`、`diff`、`for-each-ref` 直接读取 object graph/tree/ref/remote；path classification 来自 locked fixture manifest |
| Red failure fingerprint | fixture 声明的 runner exit、normalized diagnostic category 与 expected public assertion；不复制被测 fingerprint 输出 |
| 全部历史/required suites | candidate 上独立 discovery inventory + project-local contract required suite manifest，与 JUnit/runner report 双向比较 |
| candidate/freshness/trace | immutable input digest manifest 和 append-only public audit export；expected stale 集由独立依赖 fixture计算 |
| GitHub CI/rules | GitHub API 或 protocol-faithful stand-in 的 run/jobs/check-runs/rules公开响应及 call ledger；按 candidate SHA/attempt匹配 |
| artifact/version/install | stdlib `zipfile`/`tarfile`、SHA-256、clean venv 的 `lk --version` 与 `importlib.metadata.version("louke")` |
| publish唯一性 | provider公开query结果与append-only create/upload ledger；expected operation identity来自release fixture |
| archive/Red cleanup | archive manifest digest + Git CLI ref/object readback +公开history/eligibility surface |

### 3.2. Ground Truth Isolation (mandatory rule)

`tests/ground_truth/v014_workflow_impl/**` 不得 `import louke.*`，只可用 Python stdlib、Git CLI、fixture bytes和公开 provider protocol。expected identity、digest、版本、suite集合或状态不得从被测 Runtime report 回填。Ground Truth 变更要求独立 focused review；CI 静态检查违规即失败。

---

## 4. Test Scope

覆盖 30 FR、6 NFR、36 个稳定 Acceptance section。`U/C/I/E/CE/A/S` 定义见 §2.3；下表是需求级责任分配，不是测试函数清单。每行所有层都是 required，较低层不能替代较高层。

### 4.1. AC → observable interface → required layer(s) → runner/fixture/environment → CI gate → evidence

| AC | Observable interface identity | Required layers | Runner / fixture / environment | CI gate | Evidence、失败注入与分配理由 |
|---|---|---|---|---|---|
| `AC-FR0100-01` | IF-IMPL-01, IF-WFR-01, IF-PC-01 | U+C+I | unit + integration；baseline_precommit_matrix、tmp Git workspace | unit,workflow-contract,integration | hook保留/合并/readback和受控baseline；缺PASS/stale/dirty/drift阻止dispatch，跨Runtime/Git/hooks故需I |
| `AC-FR0200-01` | IF-TASK-01 | C+I | task_graph_matrix；locked 36-AC registry | workflow-contract,integration | DAG可解析且字段/责任/Issue映射完整；内部task不复制Issue，36/36有去向 |
| `AC-FR0300-01` | IF-TASK-01, IF-REV-02, IF-WFR-01 | U+C+I | duplicate/missing/cycle/conflict/orphan与revision mutation | unit,workflow-contract,integration | 每类诊断独立；Prism PASS绑定baseline；graph变更使review stale，gap只走定义目标 |
| `AC-FR0400-01` | IF-TASK-01, IF-WFR-01 | U+C+I+S | lease_manifest_matrix；barrier并发 writers、external diff、path escape | unit,workflow-contract,integration,security | manifest全identity；恰一lease；越界拒绝；Human diff保留并归因，unknown/baseline change停止而不覆盖 |
| `AC-FR0500-01` | IF-RGR-01, IF-TASK-01 | U+C+I+S | red_failure_matrix；真实host test subprocess | unit,workflow-contract,integration,security | 仅合法assertion/missing-symbol failure且test-only通过；语法/依赖/env/permission/无trace/伪测均拒绝并保持B |
| `AC-FR0600-01` | IF-RGR-01 | C+I | rgr_git_matrix；真实Git objects、CAS barrier、local bare remote | workflow-contract,integration | `R` parent/tree/ref/metadata正确；branch仍B、无remote/CI/hook；same-attempt不同OID CAS失败且归档前不删除 |
| `AC-FR0700-01` | IF-RGR-01, IF-REV-02 | C+I | review_agent_matrix + changed test tree/unexpected PASS/fingerprint | workflow-contract,integration | Prism精确收到B..R和evidence；双PASS同R才Green；correction新attempt/ref，旧verdict stale |
| `AC-FR0800-01` | IF-RGR-01, IF-QUAL-01 | U+C+I | rgr_git_matrix + historical suite inventory；真实runner | unit,workflow-contract,integration | 从获批R tree恢复，target+全部历史unit+static/contract全过；test mutation/skip历史失败/设计偏离阻断并返回Red |
| `AC-FR0900-01` | IF-RGR-01, IF-PC-01 | C+I | B/R/G objects、hook rewrite、`--no-verify` attempt | workflow-contract,integration | G parent=B且含tests+impl/trailer；Git真值证明B→R test-only、R→G impl-only、R非ancestor；pre-commit重验 |
| `AC-FR1000-01` | IF-RGR-01, IF-REV-02 | U+C+I | Refactor change/no-change/public contract mutation | unit,workflow-contract,integration | 独立Refactor commit或绑定G no-change；重跑Green checks；外部行为/interface/data/layer/architecture变化只return upstream |
| `AC-FR1100-01` | IF-RGR-01, IF-REV-02, IF-TRACE-01 | C+I+S | final range、secret/generated/unattributed diff、Agent self-report | workflow-contract,integration,security | final program+Prism review绑定完整lineage/range；缺Red/review/hook或Agent自建commit不完成且Issue非release-complete |
| `AC-FR1200-01` | IF-TEST-02, IF-TST-01, IF-REV-02 | C+I | test_suite_matrix；contract paths、public outlets、Shield patch | workflow-contract,integration | 只写integration/e2e，AC metadata和required层闭合；产品代码/新框架/窥私有状态/降层/缺trace拒绝；Prism绑定patch digest |
| `AC-FR1300-01` | IF-TEST-02, IF-WFR-01, IF-TRACE-01 | C+I+E | 四类defect、runner/env/fixture、J-TEST-VERIFY | workflow-contract,integration,e2e-standin | Runtime独立记录执行身份并受控commit；test/impl/design/requirement分别路由，修复后重跑/review且Human不判技术归因 |
| `AC-FR1400-01` | IF-CAND-01, IF-RGR-01, IF-WFR-01 | U+C+I+E | candidate_quality_matrix；post-freeze file mutation/reconnect | unit,workflow-contract,integration,e2e-standin | clean/current时唯一candidate且无R ancestry；写入禁用；六类变化产生新candidate并精确stale旧review/CI/build/security/approval |
| `AC-FR1500-01` | IF-QUAL-01, IF-TEST-02, IF-RGR-01 | C+I+E | historical inventory、illegal selector/skip/quarantine、真实build | workflow-contract,integration,e2e-standin | 同candidate report含全部质量链；只跑新测、排除历史失败或无policy quarantine均不能PASS |
| `AC-FR1600-01` | IF-BLD-02, IF-REL-01, IF-BLD-01 | C+I+A | release_artifact_matrix；clean build tree与每artifact独立venv | workflow-contract,integration,build-artifacts,artifact-verify | 顺序证明source prepared→wheel+sdist built→digest/version matched→两公开出口matched；missing/corrupt/mismatch/unknown均FAIL |
| `AC-FR1700-01` | IF-CI-02, IF-CI-01, IF-TEST-02 | C+I+CE+S | github_ci_matrix；stand-in每PR、真实sandbox protected/manual | workflow-contract,integration,ci-e2e,security | 精确SHA/workflow/attempt实际执行全部历史unit与required I/E；同名伪绿/其它SHA/skip/各非成功结论拒绝；rule readback保留用户规则 |
| `AC-FR1800-01` | IF-CAND-01, IF-REV-02, IF-TRACE-01 | C+I | full candidate snapshot、REVISE/stale route | workflow-contract,integration | Prism仅在local/GitHub gates后收到完整design/task/trace；PASS同commit；REVISE新candidate，旧review不可进Security |
| `AC-FR1900-01` | IF-SEC-01, IF-CAND-01, IF-PROMPT-02 | C+I+S | security_matrix；program result missing、Judge stale/invalid/越权 | workflow-contract,integration,security | secret/SCA/SAST/project checks齐全后才Judge；finding含location/severity/impact/fix；Judge不能改代码/写gate/推进 |
| `AC-FR2000-01` | IF-SEC-01, IF-WFR-01, IF-CAND-01 | C+I+E+S | 四类finding、critical/high waiver、policy skip、敏感边界 | workflow-contract,integration,e2e-standin,security | 路由后可见新candidate和受影响实现/测试+完整Verify/Judge重跑；禁止项不可waiver，合法skip全identity且不覆盖敏感变更 |
| `AC-FR2100-01` | IF-REL-02, IF-WFR-01, IF-CAND-01 | C+I+E+S | release_ui_matrix；J-RELEASE-DELAY/RETURN、dirty/stale/reconnect | workflow-contract,integration,e2e-standin,security | preview全字段；Release按gate显示/禁用；Delay零副作用且可重开；Return仅合法目标并传播stale；旧approval不可绕过 |
| `AC-FR2200-01` | IF-PUB-02, IF-REL-02, IF-PUB-01 | U+C+I+E+S | publish_matrix；每个operation后kill、ack loss、conflict | unit,workflow-contract,integration,e2e-standin,security | 每项先intent/query后call/result且actor Runtime；confirmed不重复，unknown needs_attention；无第二tag/upload/overwrite/Agent补写 |
| `AC-FR2300-01` | IF-PUB-02, IF-BLD-02, IF-WFR-01 | C+I+E+A | provider stand-ins + clean published-artifact install；rollback/forward-fix | workflow-contract,integration,e2e-standin,artifact-verify | main/tag/release/artifacts均指approved candidate且真实install/version/smoke；失败保持publishing/needs_attention并按contract恢复 |
| `AC-FR2400-01` | IF-TRACE-01, IF-RGR-01, IF-WFR-01 | C+I+E | archive_matrix；J-PUBLISH-CLOSE、cleanup kill/retry、foreign refs | workflow-contract,integration,e2e-standin | 36需求双向trace；归档前保留R、后仅删manifest refs；closing重试不重发；complete后history只读且next release enabled，异常时disabled |
| `AC-FR2500-01` | IF-WFR-01, IF-RGR-01, IF-CI-02, IF-TRACE-01 | C+I+E+CE | J-HOTFIX；deviation/new behavior、parallel releases/sync conflict | workflow-contract,integration,e2e-standin,ci-e2e | 仅approved偏差进入隔离fix branch/worktree并复用RGR、全历史verify、required CI和release closure；新行为拒绝，冲突needs_attention |
| `AC-FR2600-01` | IF-WFR-01, IF-TRACE-01, IF-RGR-01 | U+C+I+E | technical/product gap、arbitrary stage input、stale dependency graph | unit,workflow-contract,integration,e2e-standin | 技术gap需Archer+Prism，产品gap需Human；非法阶段不改变context；合法return后下游全stale且历史/未归档R保留 |
| `AC-FR2700-01` | IF-WFR-01, IF-PUB-02, IF-RGR-01, IF-TRACE-01 | U+C+I+E+S | retry/waiver/cancel matrix、Red CAS race、published/unpublished | unit,workflow-contract,integration,e2e-standin,security | 仅definition幂等操作可retry且attempt不可改写；不可waiver表全拒绝；waiver字段完整；发布前可取消、发布后只能恢复/关闭 |
| `AC-FR2800-01` | IF-PROMPT-02, IF-TASK-01 | C+I+S | canonical/deployed Archer/Devon/Shield prompts；semantic lint + capability harness | workflow-contract,integration,security | 三角色只做task graph/advisory或授权tests/impl，绑定manifest/schema；无Maestro/commit/push/Issue/hook/gate/stage/Human技术询问能力 |
| `AC-FR2900-01` | IF-PROMPT-02, IF-REV-02, IF-SEC-01 | C+I+S | Prism/Judge/Librarian prompt/result/capability matrix | workflow-contract,integration,security | review kind/schema/scope/input identity清晰；无Git/GitHub/program gate/state/PASS持久化；非required Librarian不阻断milestone |
| `AC-FR3000-01` | IF-PROMPT-02, IF-WFR-01, IF-QUAL-01 | C+I+S | ResponsibilityCatalog/WorkflowDefinition、兼容CLI、Maestro capability harness | workflow-contract,integration,security | 无Keeper semantic dispatch；旧质量能力由同一Runtime handler且无双写；Maestro advisory无法spawn/advance/waive/commit/release/archive/改state |
| `AC-NFR0100-01` | IF-TASK-01, IF-RGR-01, IF-CAND-01, IF-PUB-02 | U+C+I | barrier并发 lease/stage/commit/ref/candidate/operation，重复输入 | unit,workflow-contract,integration | 每组恰一CAS成功，其余可重试冲突且不覆盖；同输入同identity/result，不同attempt历史完整 |
| `AC-NFR0200-01` | IF-PROMPT-02, IF-TASK-01, IF-CI-02, IF-SEC-01 | C+I+CE+S | capability/permission matrix、fork CI、secret_canaries | workflow-contract,integration,ci-e2e,security | Agent scopes匹配角色，credential仅Runtime边界；CI最小权限；canary在prompt/diff/commit/fixture/log/evidence均阻断并脱敏 |
| `AC-NFR0300-01` | IF-RGR-01, IF-CI-02, IF-PUB-02, IF-TRACE-01 | U+C+I+E | 在Red/Green/CI/tag/publish/cleanup确认边界kill；缺失/冲突identity | unit,workflow-contract,integration,e2e-standin | restart从最后确认事实继续且不重复；不确定fail closed/needs_attention；修复外部事实后同identity安全reconcile |
| `AC-NFR0400-01` | IF-TRACE-01, IF-WFR-01 | C+I+E | 全流程audit/history、status matrix、摘要篡改 | workflow-contract,integration,e2e-standin | 所有事实有actor/time/attempt/input/output identity；PASS/FAIL/STALE/SKIP/UNKNOWN存储展示不混同，摘要不能覆盖原证据 |
| `AC-NFR0500-01` | IF-IMPL-01, IF-TEST-02, IF-CI-02, IF-BLD-02 | C+I+E+CE+A | Python/Node/unsupported host_matrix；各自contracts与已有assets | workflow-contract,integration,e2e-standin,ci-e2e,artifact-verify | 两异构栈完成到candidate并保留hooks/workflows/rules；无Louke默认泄漏；unsupported给capability诊断 |
| `AC-NFR0600-01` | IF-MIG-01, IF-WFR-01, IF-PROMPT-02, IF-TRACE-01 | U+C+I+E | legacy_matrix；migration中断/重试与new run | unit,workflow-contract,integration,e2e-standin | 旧run/stage/no-R/prompt/schema只读或显式migration且不伪造；新run仅canonical Runtime truth；无双current/commit authority/重复操作 |

### 4.2. Coverage Summary

| Requirement group | 数量 | 主风险 | 必需层 |
|---|---:|---|---|
| FR-0100..FR-1100 | 11 | 入口漂移、task/lease越界、伪Red、R/G lineage、测试弱化 | U+C+I；scope/secret另S |
| FR-1200..FR-1800 | 7 | Shield层级下降、历史回归遗漏、candidate stale、CI伪绿、artifact错版 | C+I+E+CE+A |
| FR-1900..FR-2400 | 6 | 安全职责混淆、Human gate绕过、重复发布、归档/资格提前 | C+I+E+S+A |
| FR-2500..FR-3000 | 6 | hotfix降级、任意return/waiver、prompt双authority、Keeper/Maestro残留 | U+C+I+E+CE+S |
| NFR-0100..NFR-0600 | 6 | 并发、secret、重启、审计、跨栈、迁移双写 | U+C+I+E+CE+A+S |
| **Total** | **30 FR + 6 NFR = 36** | **36/36 Acceptance sections** | **全部七类测试层均有 required 分配** |

---

## 5. Acceptance Criteria

1. `36/36` AC 均有自动化引用，且 §4 每个 required layer 都有独立 evidence；不得以 unit/contract 替代 integration/e2e/CI E2E。
2. Louke host candidate 运行全部历史 unit tests、全部 current required integration/e2e/regression；suite inventory 与 runner/CI report 双向闭合，无非法 skip/quarantine。
3. 每个 task 的 `B/R/G/(Refactor)` Git object、private Red ref、failure/review/current evidence可独立重建；`R` 与 `G` 为 sibling，`R` 不进入正式 ancestry/remote。
4. 精确 candidate 的本地 gates、GitHub `Louke CI / required`、rules readback、Prism/Judge、artifact/install evidence全部 current；任何 unknown 都 fail closed。
5. wheel 与 sdist 均真实构建、逐件 SHA-256/版本/payload检查并分别 clean install，`lk --version` 与 `importlib.metadata.version("louke")` 匹配 canonical identity。
6. Human `Release/Delay/Return`、publish restart/reconcile、archive/Red ref cleanup 与 next-release eligibility 的公开旅程全部通过。
7. coverage `>=95%`；但 coverage 不替代 AC trace、Ground Truth、并发、重启、真实 artifact、security 或 provider readback。

---

## 6. External Dependency Layered Testing (enabled)

### 6.1. Three Unavoidable Constraints

| # | Constraint | Consequence |
|---|---|---|
| C1 | fork PR 不可持有 GitHub/PyPI/发布 credential，真实发布资源不可重复创建 | 默认 CI 使用 protocol-faithful stand-in；隔离 GitHub sandbox 仅 protected/manual；production publish 本身由一次性 release evidence验证 |
| C2 | provider ack loss、eventual consistency、Runtime/process crash 会产生不确定结果 | 必须 query-before-retry；timeout 只能是 unknown/needs_attention，不能推断成功或失败 |
| C3 | 不能等待真实多阶段时间，也不能 mock Runtime 核心 | clock/Agent/provider可控；真实 Git/store/subprocess/gate/freshness/ledger 接线运行 |

### 6.2. Stance: Controllable vs Mock

- **可控替身**：wall clock/UUID、Agent session outputs、GitHub Checks/Actions/rules API、PyPI query/upload、GitHub Release、network ack、Human action输入。
- **必须真实**：Runtime WorkflowDefinition/transition、task validator、write lease、Git object/ref/CAS、test subprocess、candidate freeze、freshness/trace、operation ledger、wheel+sdist build和clean install。
- **Agent替身边界**：返回 schema-valid/invalid patch或verdict，用来驱动公开dispatch合同；不直接写state/evidence/commit/ref，也不替Runtime宣告PASS。
- **provider替身边界**：实现公开query/create/upload/check/readback与append-only ledger；不选择资源、不补写expected、不自动消除unknown。

### 6.3. Three-Layer Test Pyramid

| Layer | 名称 | 覆盖 | 默认运行 |
|---|---|---|---|
| L1 | deterministic unit/contract | graph/rules/schema/fingerprint/freshness/prompt capabilities | 每个 PR，Python矩阵中的适用job |
| L2 | integration + installed-wheel E2E | Git/store/runner接线、RGR、M-TEST、candidate、安全、Human旅程、restart | 每个 PR，stand-ins无生产secret |
| L3 | real CI/artifact/provider evidence | wheel+sdist/install每PR；隔离GitHub sandbox protected/manual；production release事实一次性 | artifact每PR；provider/release时 |

L3 环境缺失、not-run 或 readback unknown 不能显示 PASS。真实 provider smoke 与 stand-in evidence必须标明 `mode`、repository/namespace、candidate、run attempt和credential boundary，二者不可互相冒充。

### 6.4. Responsibility Contract of Test Infrastructure

| Component | 公开责任 | 不负责 |
|---|---|---|
| Host repo builder | 生成隔离Git repo、project-local contracts、历史tests/hooks/workflows/rules和独立inventory | 不替Runtime校验task或选择宿主adapter |
| Agent session harness | 接收manifest/phase并返回绑定identity的patch/review fixture | 不写Git/state/evidence，不自报program PASS |
| Failure controller | barrier、process kill、ack loss、filesystem drift、hook rewrite、network结果 | 不修改expected、核心store或判定器 |
| Git Ground Truth reader | 从objects/refs/trees/remotes导出B/R/G lineage | 不调用Runtime Git wrapper |
| Test runner observer | 记录command/cwd/env allowlist/suite inventory/JUnit/exit | 不把excluded/not-run改成success |
| GitHub/PyPI stand-in | 公开provider协议、事实查询、partial/unknown与append-only calls | 不执行Runtime reconcile或选择唯一匹配 |
| Browser harness | installed wheel启动Workbench，执行Human动作、重连并保存trace | 不调用私有stage推进或直接改store |
| Artifact verifier | clean build、逐件extract/hash/install/outlet读取 | 不接受source/tag代替artifact identity |

### 6.5. Assertion Basis — Closure with interfaces.md

- implementation/task/RGR/review：`IF-IMPL-01`、`IF-TASK-01`、`IF-RGR-01`、`IF-REV-02`；
- tests/candidate/quality/CI：`IF-TEST-02`、`IF-CAND-01`、`IF-QUAL-01`、`IF-CI-02`；
- artifact/security/release/publish：`IF-BLD-02`、`IF-SEC-01`、`IF-REL-02`、`IF-PUB-02`；
- workflow/trace/prompts/migration：`IF-WFR-01`、`IF-TRACE-01`、`IF-PROMPT-02`、`IF-MIG-01`；
- inherited machine contracts：002 `IF-PC-01`、`IF-TST-01`、`IF-CI-01`、`IF-REL-01`、`IF-BLD-01`、`IF-PUB-01`、`IF-PRM-01`。

§4 已引用全部 16 个 003 identity，并为每个跨模块候选出口分配 integration。Stage 2 若不能以这些 identity 暴露断言字段，必须修订 Interfaces/Architecture；不得在测试侧新增后门。

---

## 7. CI Gate

### 7.1. Required Workflow Contract

Devon 按 002 锁定设计及本计划后续 Stage 2 合同实现/更新 `.github/workflows/louke-ci.yml`；保留现有 `.github/workflows/ci.yml` 与 `release.yml`，但不得由其它 workflow 产生同名 `Louke CI / required`。现有 workflow 尚不能满足本 Spec 的稳定聚合、全层suite证明和rules readback，不能被当作已完成事实。

| Gate/job | Trigger | 宿主入口/接口 | Failure semantics |
|---|---|---|---|
| `quality` | PR/push | `pre-commit run --all-files`; `python -m mypy louke` | nonzero/timeout/自动改写未复核/drift均失败 |
| `workflow-contract` | PR/push | pytest 003 contract suite + inherited 002 contract validators | schema/identity/exit/permission/IF closure 任一fail/unknown失败 |
| `ac-trace` | PR/push | `python tools/check_ac_traceability.py --acceptance .louke/project/specs/v0.14-003-workflow-reflow-impl/acceptance.md --tests tests`（002已明确要求实现的project-local入口） | 非36/36、未知AC、required layer/evidence缺失失败 |
| `build-artifacts` | PR/push/release | `python -m build` | build非0或wheel/sdist任一缺失失败 |
| `artifact-verify` | PR/push/release | 002 IF-REL-01/IF-BLD-01 adapter、逐件clean-install outlets | source/artifact/digest/version/payload/install任一missing/mismatch/unknown失败 |
| `unit` | PR/push | §2.3 unit入口，Python 3.11–3.14 | 任一matrix、历史unit、coverage失败 |
| `integration` | PR/push | `tests/e2e/run-project-venv integration` | required suite skip/not-run、CAS/restart/route不闭合或nonzero失败 |
| `e2e-standin` | PR/push | `tests/e2e/run-project-venv e2e --profile all --runtime both` | 任一profile/runtime/required journey未运行或失败 |
| `ci-e2e` | PR/push + protected/manual real sandbox | IF-CI-02 provider readback；default stand-in、real sandbox分开标识 | 其它SHA、suite缺失、job非success、同名伪绿、rules mismatch/unknown失败 |
| `security` | PR/push/release | current policy scanners + security suite + IF-SEC-01/Judge contract | required scan缺失、blocking finding、非法skip/waiver、secret泄漏失败 |
| `protected-smoke` | release/manual | 隔离GitHub provider readback；production release后IF-PUB-02/BLD-02只读核验 | environment缺失/not-run/partial/unknown阻断publish或closure |
| `Louke CI / required` | PR/push/release | `if: always()` 聚合所有适用 required jobs | fail/cancel/timeout/skip/missing/unknown一律失败；publish不可绕过 |

### 7.2. Required Evidence

上传 JUnit、coverage XML、36/36 closure JSON、contract/anti-pattern/secret reports、historical+required suite inventory、RGR Git lineage report、candidate/freshness/trace snapshot、workflow/run/jobs/check/rules readback、security program/Judge schema report、artifact identity JSON、clean-install outputs、stand-in call ledger和journey report；浏览器失败附 Playwright trace/DOM/redacted server log。每份 evidence 至少绑定 source commit、run/task/attempt、requirements/design/prompt/schema/policy digest、runner/tool version、fixture identity和 `mode=stand-in|real`。上传前扫描 secret canary；无法脱敏则不上传并使gate失败。

---

## 8. Judge Review Checklist

- [ ] 30 FR + 6 NFR、36/36 Acceptance sections 均在 §4 以稳定 ID 显式分配。
- [ ] 每项均含 observable `IF-*`、required layer、runner/fixture/environment、CI gate、evidence与分配理由。
- [ ] task graph、单写者 lease、合法 Red、私有 Red ref、`B→R` test-only 与 R/G sibling lineage 有真实 Git/CAS/restart覆盖。
- [ ] Red program gate/Prism、Green/Refactor/final review 和 Shield integration/e2e 职责/evidence互不冒充。
- [ ] candidate freeze 后的代码/测试/设计/contract/prompt/config变化均使对应旧证据 stale。
- [ ] 本地与 GitHub 都证明全部历史 unit 和全部 required integration/e2e实际运行；伪绿、skip、missing、unknown fail closed。
- [ ] `Louke CI / required` 唯一稳定，rules readback保留用户规则；fork无生产secret。
- [ ] wheel+sdist真实build、逐件版本/digest/payload与clean-install公开版本出口全部验证。
- [ ] Judge、安全finding路由/不可waiver/skip、Release/Delay/Return和publish partial/unknown恢复全部覆盖。
- [ ] trace/archive、next-release eligibility、只读history和Red ref精确清理有失败/重试证明。
- [ ] 异构宿主fixtures只消费各自contracts，未把Louke Python事实泛化。
- [ ] Ground Truth不import `louke.*`，测试不读取私有store或接受Agent自报PASS。

## 9. Stage 1 Handoff and Residual Risks

**Shield readiness**：可以开始准备 §2 的目录、fixture families、Ground Truth、stand-ins、并发/kill harness 以及 §4 分配的 integration/e2e/CI E2E 场景；无需选择测试框架、runner、artifact类型或公开观察 identity。具体字段/schema、模块归属和 provider-smoke marker 名称必须由随后 Stage 2 `architecture.md`/`interfaces.md`按 §1.6 锁定后再写断言，避免猜测 payload。

**主要风险**：

1. 当前仓库尚无托管 `.github/workflows/louke-ci.yml`，现有 `ci.yml` 仍使用旧 `lk agent archer ci-scan` 且无稳定 required 聚合；Stage 2 必须锁定 replacement/coexistence 和完整 job DAG。
2. 真实 GitHub ruleset/branch-protection 能力受 token/repository plan 影响；default stand-in不能替代 protected real readback，unknown 必须保持 blocker。
3. publish provider 的真实不可变副作用无法在每个 PR 重放；正确性由 stand-in fault matrix、隔离 provider smoke和一次性 production operation/readback evidence三者分层证明。
4. 并发 lease/ref/candidate/ledger 与 process-kill 场景易产生 flake；必须用barrier和公开确认点，禁止 sleep-based timing assertion。
5. prompt迁移涉及八类角色与旧state authority；仅文本lint不足，必须同时做 capability harness、Runtime dispatch integration和legacy migration E2E。
