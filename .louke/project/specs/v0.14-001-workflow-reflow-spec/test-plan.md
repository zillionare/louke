# v0.14 Workflow Reflow（启动至 M-LOCK-1 + Issues）— Test Plan

- **Spec ID**: `v0.14-001-workflow-reflow-spec`
- **Created**: `2026-07-20`
- **Bound Story**: `sha256:e04e88b336c7f08a3f67ef40354fa35c3e78ec66935805aa6f2da7272dfd0634`
- **Bound Spec**: revision 8 / `sha256:32b2f4c51209b0c8e4167439533370877ad38040fb44ae696d20d01280c81069`
- **Bound Acceptance**: revision 9 / `sha256:159e82bce6d43580200ab9f968ee5e645b528374ba896fbec8f5191b66799f9f`
- **Related acceptance**: `.louke/project/specs/v0.14-001-workflow-reflow-spec/acceptance.md`
- **Related interfaces**: `.louke/project/specs/v0.14-001-workflow-reflow-spec/interfaces.md`

## 1. Stance and Boundaries

### 1.1 Black-box Statement

断言仅落在 `interfaces.md` 定义的公开出口：浏览器页面及可用动作、HTTP JSON、`lk serve` 进程退出/stdout/stderr、Workflow timeline/read model、受控 Markdown bytes、Git HEAD/ref/tree/index/worktree、OpenCode/GitHub公开protocol边界、构建artifact与安装后的CLI版本。不得导入私有orchestrator/adapter、直写SQLite或Runtime文件来预写状态，不得把Agent自由文本或浏览器内存当事实源；real smoke同样从Setup公开入口建立全部前置事实。

### 1.2 Non-observable Objects (tests do not directly depend on)

- 内部类层次、函数调用次数（外部adapter ledger除外）、私有队列和缓存；
- Driver内部transition实现、SQLite未公开表名/列名；
- Agent“我已完成/PASS”的自然语言；
- CSS、组件树或像素布局。

需要状态的AC必须通过 IF-API-04、IF-COMMON-03、IF-DATA-01 或 IF-EXT-03读取；没有出口时先修订`interfaces.md`，不偷看内部对象。

### 1.3 Cheating Patterns (CI enforced interception)

| # | 禁止模式 | 门禁 |
|---|---|---|
| 1 | 修改断言迎合实现、`assert True`、只断言非空 | project-local trace/anti-cheat scan失败 |
| 2 | 无Issue链接的skip/xfail、把真实smoke未运行记PASS | scan及report schema失败 |
| 3 | mock Driver/Store/Document CAS/reconcile后宣称integration通过 | review + fixture import scan |
| 4 | expected值取自被测响应 | Ground Truth review失败 |
| 5 | 用API替代Acceptance承诺的页面动作 | e2e evidence缺失 |
| 6 | sleep推断并发/恢复顺序 | 必须使用barrier、event sequence或provider ledger |
| 7 | 直接写SQLite/Runtime state、调用private adapter或测试后门构造run/lock/Issue | fixture/import scan失败；只能经公开Setup/Web/API建立 |
| 8 | 真凭据或provider response进入artifact | secret canary scan失败 |

### 1.4 Safeguards (CI checks + PR process)

1. 每个自动化测试的首行docstring/comment至少含一个规范ID `AC-FRXXXX-YY` 或 `AC-NFRXXXX-YY`。Devon实现 `tools/check_ac_traceability.py`，验证当前82个AC均被引用、每个测试均有有效AC、无未知ID。
2. 测试变更PR必须分类为新AC、Spec变更或flake/环境修复并链接来源；禁止“实现与Spec不同所以改测试”。
3. 竞争测试以barrier同时释放，并断言赢家数、revision、event和外部resource最终数量。
4. fault注入只能位于进程边界、外部协议stand-in、时钟/UUID或明确transaction crash seam；不得替换核心判定结果。
5. 覆盖率`>=95%`是附加门禁，不能替代AC closure、integration或e2e。

### 1.5 Test Division of Labor

- **Devon**：unit/contract测试、公开API实现配套测试、trace工具与CI workflow。
- **Shield**：所有跨模块integration、浏览器e2e、stand-in与真实OpenCode/GitHub smoke资产。
- **独立reviewer**：Ground Truth、故障注入真实性、断言强度和secret扫描。

---

## 2. Test Environment

### 2.1 Directory Layout

```text
tests/
├── runner-manifest.toml          # Devon：runner discovery + required AC合同
├── unit/                         # Devon：纯规则/validator/CAS decision
├── integration/
│   └── v014_workflow_reflow/     # Shield：HTTP + SQLite + Git + stand-ins
├── e2e/
│   ├── v014_workflow_reflow/     # Shield：installed wheel + live server + Chromium
│   └── run-project-venv          # 既有权威runner
├── fixtures/
│   └── v014_workflow_reflow/     # 合成workspace、Git图、协议脚本、canary
└── ground_truth/
    └── v014_workflow_reflow/     # 独立digest/Git/identity核验
```

宿主`project.toml`现有公开合同保持：

- integration：`tests/e2e/run-project-venv integration`，paths包含`tests/e2e`, `tests/integration`, `tests/fixtures`, `tests/ground_truth`；
- e2e：`tests/e2e/run-project-venv e2e --profile all --runtime both`，paths包含`tests/e2e`, `tests/fixtures`, `tests/ground_truth`；
- framework：`pytest`，cwd为repo root。

本manifest只授权三份设计文档，故不改`project.toml`；上述字段已存在并锁定Shield的入口/资产范围，但必须完成§2.3的runner discovery改造后才可声称实际执行闭合。

### 2.2 Naming Conventions

- 文件按用户场景命名：`test_<journey>__<failure>.py`；不按私有类命名。
- 测试名可按scenario表达，但首行必须含AC ID；一个参数化scenario可引用多个语义一致AC。
- marker：`integration`, `e2e`, `chromium_e2e`, `real_opencode`；增加`real_github`时必须由本次实现注册并只用于受保护环境。

### 2.3 Execution

| 层 | 入口 | 环境 | 默认PR CI | why |
|---|---|---|---|---|
| unit/contract | `python -m pytest -q tests/unit ...` | Python 3.11–3.14；外部value/clock可替换 | 是 | 纯版本解析、状态合法性、schema、格式/coverage规则快速定位 |
| integration | `tests/e2e/run-project-venv integration` | clean tmp Git workspace、真实SQLite/HTTP/Git CLI、OpenCode/GitHub stand-in | 是 | 所有2+模块接口及事务/CAS/reconcile必须验证真实接线 |
| e2e stand-in | `tests/e2e/run-project-venv e2e --profile all --runtime both` | 构建wheel、clean venv、live `lk serve`、Playwright Chromium、协议stand-in | 是 | 验证用户承诺的页面旅程，不能由低层测试替代 |
| real smoke | `tests/e2e/run-project-venv real-smoke --profile v014 --runtime local` | 同SHA installed wheel、真实OpenCode、disposable GitHub repo/Project/provider namespace、认证Human browser | release/manual protected | 公开八步旅程+动态完整24项；required AC/report/cleanup任一不完整均失败 |

现有runner只硬编码`tests/integration/install_experience`与v0.13 install/Chromium，且parser没有real profile；因此上述命令**尚未执行闭合**，是Devon本轮必需实现变化。Devon按IF-CI-01新增`tests/runner-manifest.toml`并修改runner：`integration/v014`收集`tests/integration/v014_workflow_reflow`，`e2e/v014`收集`tests/e2e/v014_workflow_reflow`且`profile=all`包含它，real只收集`.../real`。real target的required AC精确为`AC-FR1700-03, AC-FR1800-02, AC-FR1900-01, AC-NFR0200-01, AC-NFR0200-02, AC-NFR0300-01, AC-NFR0300-03`。每个target/runtime先collect-only再run；path/profile/runtime/required AC零收集或漏执行、skip/xfail、report不完整均非零。Shield只按manifest放置资产，不修改discovery逻辑。

执行顺序：quality/trace → build → unit → integration → stand-in e2e；tag/manual release再执行唯一real命令。每个场景使用随机loopback port、隔离HOME/XDG/GIT_CONFIG、独立DB、bare remote和provider namespace。real runner严格按Architecture §9.1：start安装同workflow/SHA wheel并创建disposable repo/workspace；ready只探测Workbench、真实OpenCode和GitHub identity/权限；run由Chromium经公开Setup、release/Foundation、真实Scribe/Sage/Lex author/review、认证Human M-LOCK-1，再点击Project current reconcile动作使IF-EXT-03完成locked动态target（当前24）；finally按`delete-always`删除Project/repo并逐identity证明不存在。零准备、private adapter/SQLite、绕gate、partial target、cleanup不确定均非零；不存在一个代表Issue的profile。

### 2.4 Test Data

| fixture | 内容与用途 |
|---|---|
| `workspace_matrix` | 首次/有效/冲突/部分setup；无真实credential |
| `git_graph_matrix` | bare declared remote；merged/ahead/behind/diverged/unknown；local main mismatch；错误branch start |
| `canonical_templates` | Story/Spec/Acceptance合法、重复ID、缺Source、31 FR、缺Acceptance section variants |
| `dirty_workspace_matrix` | staged/unstaged/untracked/其它文档、branch移动、isolatable/unattributed patch |
| `opencode_standin` | session/turn/transcript/result；timeout/running/lost/invalid role/digest/schema/scope |
| `github_standin` | repository/Project/Issue/item catalog与query/create/link ledger；ack loss、partial、零/多/模糊/冲突候选 |
| `review_matrix` | Human one-byte edit、dirty、comment/no-comment、open/resolved/reopen threads、stale verdict |
| `auth_matrix` | anonymous、Agent transport、cross-origin、缺/错CSRF、过期session、当前/过期/已消费bootstrap与M-LOCK challenge；只含合成credential |
| `document_operation_crash_matrix` | 同一operation的preimage/intended bytes、deterministic commit metadata、目标HEAD/index/worktree baseline、非目标index semantic fingerprint；文件写后/commit object后/ref CAS与target-index-sync之间/index安装后/`target_index_synced`后/Store前后kill seam |
| `secret_canaries` | 唯一token/cookie/provider-secret bytes；仅从外部输入注入 |
| `locked_24_requirements` | 当前21 FR+3 NFR、anchors、独立计算digests；只读copy |

fixture manifest记录schema version和生成digest；全部合成、可重复。real smoke凭据仅从GitHub protected environment注入；repo、release Project及24项资源带run identity，report列完整target与`delete-always` cleanup manifest，失败留redacted retained-resource清单但不得算PASS。

---

## 3. Ground Truth Method

### 3.1 General Principle

本功能不是数值算法，但identity、digest、Git graph和resource count需要独立真值：

| 断言 | 独立真值 |
|---|---|
| artifact/joint digest | stdlib `hashlib`直接读取fixture bytes，按placeholder scheme计算 |
| Git commit与index语义 | `git symbolic-ref HEAD`、`git rev-parse HEAD`、`git rev-parse <full_ref>`、`git diff-tree`、`git ls-tree`、`git ls-files --stage -z`、`git ls-files -v -z`、`git diff --cached --raw -z`、`git status --porcelain=v2 -z`；不比较raw index file bytes |
| Human authority失败无副作用 | 认证前后IF-API-04/10/11 bytes、Git命令、event/operation数量及stand-in ledger的独立snapshot；不得信任请求actor |
| document operation恢复 | SQLite公开IF-DATA-01/IF-EXT-02与`git cat-file`/HEAD/ref/tree、目标index/worktree、非目标entry/flag/staged-intent fingerprint及porcelain交叉核对operation ID、prepared OID、target-index-sync与accepted revision |
| main merge关系 | fixture预先构造的commit DAG + `git merge-base --is-ancestor` |
| Issue/Project唯一性 | stand-in或GitHub公开query结果与独立locked-24 manifest；real逐项正反查询24 requirement/Issue/item与release Project identity，不读取Driver期望值 |
| event顺序/幂等 | IF-COMMON-03 sequence、公开resource IDs与provider call ledger |
| release artifact version | wheel/sdist metadata、clean install后的`importlib.metadata`与`lk --version` |

### 3.2 Ground Truth Isolation

`tests/ground_truth/v014_workflow_reflow/**`不得import `louke.*`，只可用stdlib、Git CLI和fixture文件。expected IDs/links从locked fixture与provider catalog生成，不能从被测API回填。CI静态扫描违反即失败；变更须由非实现者重点review。

---

## 4. Test Scope

覆盖全部24个有效需求、82个AC、八步Journey以及失败/恢复/幂等/并发。下表每一项均为requirement-level策略，不是测试函数清单；`I`=integration，`E`=stand-in browser e2e，`U`=unit/contract，`R`=真实外部smoke。所有`I/E`分别进入`integration`/`e2e-standin` job；`R`进入release `real-smoke`。

### 4.1 AC → observable interface → required layer → CI gate

| AC | Observable interface | required layers / CI | 策略与分配理由 |
|---|---|---|---|
| AC-FR0100-01 | IF-CLI-01, IF-WEB-01, IF-API-01 | I+E | 缺model/provider/OpenCode逐项BLOCKED、remediation与disabled release；跨启动/Web且用户可见 |
| AC-FR0100-02 | IF-CLI-01, IF-API-01, IF-API-02 | I+E | 连续启动并比较manifest identity及外部ledger零create；公开入口回归 |
| AC-FR0100-03 | IF-CLI-01 | U+I | 端口/package/app factory及非loopback host断言非零、稳定error、无listener/DB/run/create；Web不存在不虚构e2e |
| AC-FR0200-01 | IF-WEB-02, IF-API-02 | I+E | 候选/provenance与确认前workspace/release副作用全零 |
| AC-FR0200-02 | IF-WEB-02, IF-API-02 | I+E | owner冲突重启后revision/candidates字节相等且waiting_human |
| AC-FR0200-03 | IF-API-02, IF-COMMON-03 | I+E | Human确认manifest全字段、actor/provenance/operation evidence及重试幂等 |
| AC-FR0200-04 | IF-WEB-02, IF-API-02 | U+I+E | 零/多/冲突namespace与权限矩阵不模糊选择、不complete |
| AC-FR0200-05 | IF-WEB-02, IF-API-02 | I+E | partial update后kill/network故障，逐项恢复，只继续未完成且release create为0 |
| AC-FR0300-01 | IF-WEB-03, IF-API-03 | U+I+E | 空/非法输入字段错误；preview对Project/run/GitHub/ref/dir/Backlog全零副作用 |
| AC-FR0300-02 | IF-API-03, IF-DATA-02 | I+E | barrier并发confirm，恰一Backlog且无第二主资源 |
| AC-FR0300-03 | IF-DATA-02, IF-WEB-09 | I+E | 重启后story/version/reason/time/source identity保持 |
| AC-FR0400-01 | IF-WEB-03, IF-EXT-01 | I+E | fetch失败/未merge显示full ref/SHA/error，所有release资源和task零 |
| AC-FR0400-02 | IF-EXT-01 | I+E | Foundation各一；branch start=M且symbolic HEAD/full_ref均为checked-out release branch；target baseline与stable IDs齐全 |
| AC-FR0400-03 | IF-EXT-01, IF-COMMON-03 | I+E | Project create ack loss后query复用node ID，count不增且M-STORY未早启 |
| AC-FR0400-04 | IF-WEB-03, IF-EXT-01 | U+I+E | local mismatch/ahead/behind/diverged/unknown矩阵，remediation及零副作用 |
| AC-FR0400-05 | IF-EXT-01, IF-WEB-03 | I+E | 错branch起点/resource identity冲突保持needs_attention，不改写/造候选 |
| AC-FR0500-01 | IF-WEB-04, IF-API-06, IF-DATA-01 | I+E | template+原始输入bytes、digest/actor/commit；accepted后目标HEAD/index/worktree同blob且porcelain无目标记录 |
| AC-FR0500-02 | IF-API-06, IF-DATA-01 | I+E | matching retry同SHA零commit；bytes conflict稳定409且不覆盖 |
| AC-FR0500-03 | IF-WEB-04, IF-API-04 | I+E | 跟随导航并显示同run/M-STORY/revision |
| AC-FR0600-01 | IF-COMMON-01/02, IF-API-05, IF-API-04 | U+I | contract枚举anonymous/Agent payload role/cross-origin/stale session；真实HTTP中均在Driver前拒绝且run/artifact/gate/Git/Issue ledger不变 |
| AC-FR0600-02 | IF-WEB-09, IF-API-04 | I+E | waiting/blocked/review刷新与服务重启后所有read-model字段一致 |
| AC-FR0600-03 | IF-API-05, IF-WEB-09 | U+I+E | stale/illegal action无副作用，页面显示current与continue_url |
| AC-FR0700-01 | IF-WEB-04, IF-WEB-05, IF-API-08 | I+E | Scribe task manifest全字段、story-only scope、readonly与Chat绑定 |
| AC-FR0700-02 | IF-API-04, IF-WEB-05 | I+E | 建议后仍waiting_human/M-STORY，M-SPEC task零 |
| AC-FR0700-03 | IF-COMMON-01/02, IF-API-05, IF-COMMON-03 | U+I+E | contract+integration覆盖anonymous、Agent伪`role=human`、cross-origin、错CSRF、expired session；均拒绝且零副作用；browser用bootstrap Human合法值并记录服务端actor/R/time |
| AC-FR0800-01 | IF-DATA-02, IF-API-04 | I+E | Park/No-Go Backlog全identity、终态、M-SPEC task零 |
| AC-FR0800-02 | IF-EXT-02, IF-DATA-02 | I | 安全branch清理两次，首次删local ref、二次no-op、Backlog仍一 |
| AC-FR0800-03 | IF-EXT-02, IF-WEB-09 | I+E | unattributed commit/dirty/remote ref保留bytes/ref，无force/reset，needs_attention |
| AC-FR0900-01 | IF-WEB-05, IF-API-08, IF-COMMON-03 | I+E | persisted.seq<dispatched.seq；ack loss重试消息/transcript/session各一 |
| AC-FR0900-02 | IF-API-08, IF-API-04 | U+I+E | unchanged handoff返回STORY_CHANGE_REQUIRED，仍authoring且review task零 |
| AC-FR0900-03 | IF-API-06, IF-DATA-01, IF-EXT-02, IF-COMMON-03 | I+E | 真实Git+SQLite在document_written/prepared/ref_confirmed/target_index_synced恢复；同OID/revision，review event严格晚于index同步后的accepted且旧verdict不推进 |
| AC-FR1000-01 | IF-API-06, IF-API-07 | U+I+E | barrier同token/lease保存：至多一成功，败者current token，disk=winner |
| AC-FR1000-02 | IF-API-07, IF-WEB-06 | I+E | 注册dirty后Agent lease blocked；save/discard前Agent不能改变bytes |
| AC-FR1000-03 | IF-DATA-01, IF-EXT-02, IF-WEB-09 | I+E | 正常成功仅限目标旧baseline+非目标fingerprint匹配；ref后非目标漂移只repair目标并fail，保留当前非目标index；目标已变不覆盖，均无全repo revert |
| AC-FR1100-01 | IF-WEB-06, IF-API-09 | I+E | direct edit标edited；thread写回后`lk discuss query`可识别及count正确 |
| AC-FR1100-02 | IF-WEB-06, IF-API-09 | U+I+E | one-byte edit禁用no-comment；伪造请求409且无Human PASS |
| AC-FR1100-03 | IF-API-09, IF-API-04 | U+I+E | comment/open/dirty均无PASS；仅clean current no-comment通过 |
| AC-FR1200-01 | IF-API-08, IF-API-09 | I+E | Human/Sage绑定C/D；reviewer session≠Scribe；旧digest不计 |
| AC-FR1200-02 | IF-DATA-01, IF-API-08 | I+E | Human D2先commit；Sage input含diff+D2；两个独立commit |
| AC-FR1200-03 | IF-API-04, IF-DATA-01, IF-API-08 | I+E | 原Scribe session返工D3、旧verdict stale、双PASS后才M-SPEC |
| AC-FR1300-01 | IF-WEB-07, IF-API-08 | I+E | 导航Spec、readonly、Sage input含Story/review/template/single path |
| AC-FR1300-02 | IF-API-06, IF-WEB-07 | I+E | Sage返回前Human write拒绝；有效后只commit spec并开放 |
| AC-FR1300-03 | IF-API-09, IF-WEB-07 | U+I+E | empty/duplicate/missing metadata/31-FR规则定位，Lex task零 |
| AC-FR1400-01 | IF-API-07, IF-API-09, IF-WEB-07 | I+E | Human/Lex同R；Lex无lease不可写，有leasethread页面/API均可查 |
| AC-FR1400-02 | IF-API-08, IF-API-09 | I+E | Human R2后Lex输入R2+diff，旧R stale不可组合 |
| AC-FR1400-03 | IF-API-09, IF-API-04 | U+I+E | comment/nonPASS/open触发原Sage新revision+round；联合条件才semantic pass |
| AC-FR1400-04 | IF-API-09, IF-WEB-07 | U+I+E | format error file/location/rule，M-ACC task零；修复PASS后前进 |
| AC-FR1500-01 | IF-COMMON-01, IF-COMMON-02, IF-WEB-07, IF-WEB-08, IF-API-10 | U+I+E | 各phase只显示合法targets；contract/integration拒绝anonymous/Agent/cross-origin/stale session；browser E2E从页面发起失败return并断言phase/revision、三文档bytes、Git ref与外部operation ledger全不变 |
| AC-FR1500-02 | IF-API-10, IF-DATA-01 | I+E | 仅当前Human session合法返回；成功保留ledger/Git并将目标/下游evidence stale/superseded，失败路径不产生stale标记 |
| AC-FR1500-03 | IF-API-10, IF-WEB-09 | I+E | Agent建议只显示Human wait，不移动step/revision |
| AC-FR1600-01 | IF-WEB-08, IF-API-08 | I+E | Spec semantic+format PASS后导航Acceptance、readonly、Sage沿用上下文/绑定digests |
| AC-FR1600-02 | IF-API-09, IF-WEB-08 | U+I+E | 缺FR/NFR section且无理由时列ID、approve隐藏、返回Sage |
| AC-FR1600-03 | IF-WEB-09, IF-API-11 | I+E | 全PASS后M-LOCK-1；上游digest变化Acceptance stale且approve隐藏 |
| AC-FR1600-04 | IF-WEB-06, IF-API-09, IF-API-08 | U+I+E | edit/comment/nonPASS/open/format失败完整返工；联合fresh条件才离开 |
| AC-FR1700-01 | IF-WEB-09, IF-API-11 | U+I+E | 任一blocker按钮disabled/服务拒绝并列项，Issue count不变 |
| AC-FR1700-02 | IF-COMMON-01, IF-COMMON-02, IF-WEB-09, IF-API-11 | U+I+E | contract/integration覆盖anonymous、Agent、cross-origin、expired session及已消费challenge replay；browser E2E提交stale/replayed challenge，断言gate pending、三文档bytes/locked、Git ref与Issue/外部operation数全不变 |
| AC-FR1700-03 | IF-API-11, IF-API-06, IF-WEB-09 | I+E+R | 当前bootstrap Human approve evidence完整；real由Chromium session合法消费challenge；三文档锁，后续PUT 423 |
| AC-FR1800-01 | IF-API-11, IF-EXT-03 | U+I+E | gate前split/reconcile拒绝，provider search/create/link count不增 |
| AC-FR1800-02 | IF-EXT-03, IF-WEB-09 | I+E+R | stand-in与real均从locked Spec动态证明24 IDs各一Issue/item、精确title/body anchors/Foundation Project；partial target非零 |
| AC-FR1800-03 | IF-EXT-03, IF-COMMON-03 | I+E | barrier/repeat/restart/ack loss后每ID最多一Issue/item，精确复用 |
| AC-FR1800-04 | IF-EXT-03, IF-WEB-09 | I+E | partial逐ID状态/error；修复只补失败，成功number不变；未全linked不complete |
| AC-FR1800-05 | IF-EXT-03 | U+I+E | duplicated/imprecise token、body/link/Project mismatch均conflict且不造第二候选 |
| AC-FR1900-01 | IF-API-08 | I+E+R | 所有task evidence字段；real报告六个Scribe/Sage/Lex author/reviewer task且session按角色/任务分离 |
| AC-FR1900-02 | IF-API-08, IF-WEB-05 | I+E | stand-in可控timeout完整证明先reconcile、dispatch不增、valid回收/running等待；real只验证session边界不冒充全部Then |
| AC-FR1900-03 | IF-API-08, IF-API-04 | U+I | wrong role/attempt/manifest/digest/schema/scope均rejected且状态/bytes不变 |
| AC-FR1900-04 | IF-API-08, IF-WEB-05 | I+E | confirmed lost→原attempt lost/interrupted，新session同authority input，无自动PASS；故障控制需可证明lost，real不负责制造该完整条件 |
| AC-FR2000-01 | IF-EXT-02 | I | commit tree只含spec；accepted目标HEAD/index/worktree一致且无porcelain记录；所有非目标entries/flags/cached staged intent及staged/unstaged/untracked语义与其它bytes不变，不断言raw index bytes |
| AC-FR2000-02 | IF-DATA-01, IF-EXT-02 | I | prepared/ref-confirmed/target_index_synced/accepted evidence全字段；symbolic HEAD/full_ref SHA=记录commit；两个index-sync kill seam只补同一revision/OID |
| AC-FR2000-03 | IF-API-06, IF-EXT-02, IF-WEB-09 | I+E | 目标预staged/source unknown、非目标fingerprint漂移、外部HEAD/ref/bytes并发均conflict/needs_attention；不覆盖index/编辑、不启动review/旧verdict、不执行危险命令 |
| AC-FR2100-01 | IF-API-04, IF-API-08, IF-API-07 | I+E | review任意round kill/restart，step/revision/lease/task/gate/error相等，dispatch不增 |
| AC-FR2100-02 | IF-COMMON-03, IF-EXT-01, IF-EXT-02, IF-EXT-03 | I+E | document operation三分支含ref已CAS/index未同步与index已安装/ledger未记：补target_index_synced/同revision或needs_attention；无重复commit/resource |
| AC-FR2100-03 | IF-WEB-05, IF-WEB-09, IF-API-04 | I+E | browser/OpenCode断连后页面恢复revision/session且task/resource不重复 |
| AC-NFR0100-01 | IF-COMMON-03, IF-API-04, IF-DATA-01, IF-EXT-02 | U+I | SQLite边界及跨file/ref/index/Store seam：ref-CAS前后、index安装前后、target_index_synced后均未accepted无revision/verdict；恢复补原operation/revision |
| AC-NFR0100-02 | IF-API-05, IF-API-06, IF-API-07 | U+I | same expected revision/token barrier恰一winner，稳定409和一次副作用 |
| AC-NFR0100-03 | IF-API-03, IF-API-11, IF-EXT-03, IF-DATA-02 | I | Backlog/Project/gate/Issue重复并发后每logical identity唯一 |
| AC-NFR0100-04 | IF-EXT-01, IF-EXT-03 | U+I | zero/multi/stable-ID conflict/fuzzy候选均needs_attention且数量/identity不变 |
| AC-NFR0200-01 | IF-COMMON-03, IF-API-04 | I+E+R | stand-in与real timeline均覆盖Setup→24 Issues；real report含sequence范围/digest及六个task/gate/commit/external evidence |
| AC-NFR0200-02 | IF-EXT-03, IF-DATA-01 | I+E+R | stand-in与real逐项证明完整24项正反trace、三文档digests与Project identity；无代表Issue |
| AC-NFR0200-03 | IF-COMMON-02, IF-API-02, IF-API-08, IF-EXT-03 | U+I+E | canary递归扫描manifest/docs/events/log/error/commit/Agent input零原字节 |
| AC-NFR0300-01 | IF-CLI-01, IF-WEB-01..09, IF-WEB-09 | E+R | stand-in与real均从clean installed wheel/browser走公开八步；real用disposable repo、真实Agents、Human lock与完整24项，禁止内部推进 |
| AC-NFR0300-02 | IF-API-04..11, IF-EXT-02..03 | I+E | 单一fault journey注入edit/discussion/rework/CAS/restart/Agent断连/GH ack loss并完成 |
| AC-NFR0300-03 | IF-API-08, IF-EXT-03, IF-CI-01 | E+R | 唯一real命令报告六个真实task/session、至少一个同session重连恢复证明及动态24项全部Issue number/Project node+item IDs；同SHA wheel、required AC、delete-always proof任一缺失失败 |

### 4.2 Requirement-level strategy summary

| requirement | 主风险 | 必需层 |
|---|---|---|
| FR-0100..0500 | 入口/Setup/请求/Foundation副作用过早、identity漂移 | U（规则）+I+E |
| FR-0600..1200 | authority、session、单写者、Human review和旧revision推进 | U+I+E |
| FR-1300..1700 | Spec/Acceptance author-review-format、return、锁定 | U+I+E；real另验证AC-FR1700-03成功路径 |
| FR-1800..2100 | GitHub/Git/OpenCode幂等、超时与重启恢复 | U+I+E；real另验证FR-1800完整24项与FR-1900 task identity，不承担fault矩阵 |
| NFR-0100 | transaction/CAS/并发 | U+I |
| NFR-0200 | trace与secret | U+I+E；real另验证完整timeline/24项正反identity |
| NFR-0300 | 安装产物公开旅程与真实边界报告 | E+R（AC-NFR0300-01/03）；fault旅程AC-NFR0300-02仍由stand-in负责 |

### 4.3 Human trust boundary 闭合

| 威胁/状态 | Observable interfaces | required layers / gate | 不变断言 |
|---|---|---|---|
| anonymous或payload伪`role=human` | IF-COMMON-01/02, IF-API-05/10/11 | U contract + I | 401/403；actor不从payload出现；run/gate/document/Git/external ledger snapshot相等 |
| Agent/Chat session调用Human动作 | IF-WEB-05, IF-API-08, IF-API-10/11 | U contract + I | Human principal不可建立/委托；task/session与workflow事实不变 |
| cross-origin、缺/错CSRF | IF-COMMON-01/02 | U contract + live HTTP I | Driver/event/operation调用数为零；cookie不泄露，响应无secret |
| expired/stale Human session | IF-COMMON-01/02, IF-API-10/11 | fake clock contract + restart/live I | `SESSION_EXPIRED`，新bootstrap前不重放原动作；业务事实不变 |
| bootstrap或M-LOCK challenge replay | IF-COMMON-01/02, IF-API-11 | U contract + I；M-LOCK另E | challenge只消费一次；失败不锁文档、不建Issue、不移动ref |
| return/M-LOCK browser failure | IF-WEB-07/08/09, IF-API-10/11 | E `e2e-standin` | 页面显示可恢复auth/stale反馈；phase/gate、三文档bytes/locked、Git ref与所有外部operation计数不变 |

### 4.4 Controlled document commit crash matrix

Shield用**真实Git CLI + 真实SQLite + live HTTP**，先在checked-out release branch构造非目标staged/unstaged/untracked、conflict-stage与index flags组合，并保存：每个非目标path的`stage/mode/blob/flags`、相对HEAD cached diff、worktree bytes及`git status --porcelain=v2 -z`记录；目标保存HEAD tree entry、真实index entry和worktree blob。不得以`.git/index` raw bytes hash作为通过条件。

对同一IF-EXT-02 operation分别在`document_written`后、prepared object可`cat-file`后、**ref CAS成功而target index sync未开始**、目标index原子安装后但`target_index_synced`未落库、`target_index_synced`落库后、Store accepted事务前/后立即kill。每次从原workspace重启且只调用公开read/reconcile：prepared OID不变；ref-CAS后目标index为旧baseline时仅同步目标；index已为prepared blob时只补记`target_index_synced`；最终只接受同一revision/event。accepted ground truth必须同时满足：symbolic HEAD=full_ref、HEAD/ref=prepared commit、目标HEAD/index/worktree为同一accepted blob/bytes、porcelain-v2无目标记录；所有非目标entry/flag/cached staged intent和status记录与baseline语义相等，commit DAG至多一个可达controlled commit。

另在ref CAS前注入目标预staged/source unknown和非目标fingerprint漂移，断言零ref/index写；ref CAS后注入非目标漂移时断言仅repair仍为旧baseline的目标、当前非目标entries/flags逐项保留、operation`needs_attention`且porcelain无Runtime reverse diff；注入目标第三值时断言不覆盖该值并fail。均不接受revision，不用reset/checkout/全index snapshot恢复。所有seam断言无旧verdict/phase推进。该矩阵为AC-FR0900-03、AC-FR2000-01..03、AC-FR2100-02、AC-NFR0100-01的integration evidence，不得mock Store/Git。

---

## 5. Acceptance Criteria for the Test Plan

1. 上表82个规范AC均至少一个自动化引用，且每个required layer都有独立evidence；integration/e2e不得被unit替代。
2. `Louke CI / required` 在每个PR/push聚合quality、build/artifact verify、unit矩阵、integration、stand-in e2e和trace；任一missing/skip/unknown均失败。
3. 所有用户主成功旅程从installed wheel的`lk serve`进入真实页面；API只作为断言出口，不替代点击/填写/导航。
4. 所有跨模块接口至少integration；IF-WEB-*关键动作至少e2e；真实OpenCode/GitHub在release前smoke。
5. coverage `>=95%`，但82/82 trace、24 requirement策略和failure evidence均独立成立。

---

## 6. External Dependency Layered Testing

### 6.1 Three Unavoidable Constraints

| 约束 | 后果 |
|---|---|
| PR不能使用生产GitHub/OpenCode凭据 | 默认CI必须使用protocol-faithful stand-in |
| timeout/ack loss与真实外部状态不同步 | 必须测试query-before-retry和`uncertain`，不能用HTTP结果代替事实 |
| 不得mock Runtime核心 | stand-in只能替换OpenCode/GitHub/declared remote等系统外边界 |

### 6.2 Stance: Controllable vs Mock

- 可控：wall clock/UUID、Git remote、OpenCode HTTP/SSE、GitHub REST/GraphQL、进程kill点、网络ack。
- 不可替换：Driver authority、SQLite transaction、lease/CAS、review联合判定、Git allowlist commit、operation reconcile。
- Stand-in必须记录公开query/create/link/dispatch/result ledger并实现成功、明确失败、timeout后成功、零/多/冲突候选；不替Driver作identity判定。

### 6.3 Three-Layer Test Pyramid

| 层 | 名称 | 覆盖 | 运行 |
|---|---|---|---|
| L1 | deterministic contract | version/schema/validator/CAS/phase rules | 每PR unit |
| L2 | protocol integration + browser stand-in | 全跨模块与八步Journey、故障注入 | 每PR integration/e2e |
| L3 | real environment smoke | clean wheel/workspace经公开Setup→Foundation→六个真实Agent task→Human M-LOCK-1→动态24 Issues/items；完整identity/cleanup report | release/manual protected environment |

L3不是跳过L2，也不承担timeout/lost/ack-loss等故障矩阵；但它必须实际覆盖八步公开成功journey和当前24项Then，不能降级为protocol单资源smoke。start/ready/run/teardown与report严格采用Architecture §9.1；Setup、revision、Agent result、review、M-LOCK和Issues均不得预写或私调。缺secret/权限/环境、任一真实Agent/gate未完成、target不足24、required AC/report缺失、cleanup/retention无法证明均非零并阻断release。sandbox repo/Project/provider namespace每run唯一且`delete-always`，不得复用或操作生产资源。

### 6.4 Test Infrastructure Responsibility Contract

| 组件 | 对外责任 | 不负责 |
|---|---|---|
| OpenCode stand-in | session/turn/message/result/status协议、correlation与fault ledger | 生成产品判定或修改Runtime状态 |
| GitHub stand-in | repository/Project/Issue/item query/create/link协议和eventual visibility | 选择可复用候选 |
| Git fixture orchestrator | 创建确定commit DAG与remote refs、提供独立Git观察 | 代替Foundation判定 |
| Browser harness | 安装wheel、启动/ready/teardown live server、页面动作、trace | 调内部Python对象推进 |
| fault controller | kill进程、断连接、丢ack、barrier | 修改期望状态或补写DB |

### 6.5 Assertion Basis — Closure with interfaces.md

- 通用identity/error/event：IF-COMMON-01/02/03（所有contract/integration场景）；状态：IF-API-04；
- 文档/lease/review：IF-API-06/07/09、IF-DATA-01；
- Setup/Foundation：IF-API-01/02/03、IF-EXT-01；
- Agent：IF-WEB-05/IF-API-08；
- Git/GitHub：IF-EXT-02/03；
- 用户交互：IF-WEB-01..09；
- CLI/artifact/CI：IF-CLI-01、IF-REL-01、IF-CI-01。

每个接口均已在§4映射或由跨场景公共contract覆盖；不得增加仅测试可见的后门。

---

## 7. CI Gate

### 7.1 Required workflow

Devon按`architecture.md`实现`.github/workflows/louke-ci.yml`，并在同一迁移中搬入现有`ci.yml` mandatory/install matrix与`release.yml` publish后删除旧workflow。稳定聚合check为`Louke CI / required`；禁止旧`lk agent archer ci-scan`和按workflow文件名/latest run轮询。

| gate | trigger | 命令 | fail semantics |
|---|---|---|---|
| quality | PR/push/tag/manual | `pre-commit run --all-files`; `python -m mypy louke` | 任一非0/timeout失败 |
| build | PR/push/tag/manual | `python -m build` | wheel或sdist缺一失败 |
| artifact verify | PR/push/tag/manual | IF-REL-01 prepare/inspect/install出口；PR比较source version，release比较canonical tag | 任一artifact/installed version不确定或不匹配失败并阻断publish |
| unit | PR/push/tag/manual | `python -m pytest -q tests/unit --cov=louke --cov-report=xml --cov-fail-under=95` on Python 3.11–3.14 | 任一matrix失败 |
| integration | PR/push/tag/manual | `tests/e2e/run-project-venv integration` | manifest target/path/required AC零收集或漏执行、skip、ledger不闭合或非0失败 |
| e2e-standin | PR/push/tag/manual | `tests/e2e/run-project-venv e2e --profile all --runtime both` | v014或任一manifest runtime/profile未收集/运行、skip或失败 |
| trace | PR/push/tag/manual | `python tools/check_ac_traceability.py --acceptance .louke/project/specs/v0.14-001-workflow-reflow-spec/acceptance.md --tests tests` | 非82/82、未知ID、anti-cheat失败；该tool由本次实现，不依赖旧`lk agent` |
| `Louke CI / required` | PR/push/tag/manual | `if:always()`精确聚合全部mandatory needs | missing/skipped/cancelled/timeout/unknown或任一非success失败 |
| real-smoke | tag/manual release，needs required+build+verify | `tests/e2e/run-project-venv real-smoke --profile v014 --runtime local` | 同SHA wheel/start/ready、公开八步、真实六task、Human lock、24 target、required AC/report/delete proof任一缺失均阻断publish |
| publish | tag/manual release，needs required+real-smoke+build+verify | 发布同一run已验证、real安装同digest wheel及配套sdist；不重建替换 | needs非success、SHA/digest/24项/cleanup任一不匹配时不得执行且workflow失败 |

### 7.2 Evidence

上传JUnit、coverage XML、trace closure JSON、`runner-report.json`、artifact identity JSON、stand-in operation ledgers、journey/`real-smoke.json`；失败时上传Playwright trace/DOM snapshot、non-secret log与redacted retained-resource manifest。real report严格采用Architecture §9.1 schema，含同一source SHA/wheel digest、三文档/gate、六task/session、locked requirement集合、24个Issue/Project item正反identity、timeline与`delete-always` proof；不得含credential。publish逐digest消费同一workflow run的build artifacts/needs，不查询latest checks也不重建替换。

---

## 8. Judge Review Checklist

- [ ] 21 FR + 3 NFR、82 AC均在§4以规范ID显式分配。
- [ ] 每项分配包含真实observable interface、required layer、CI gate与理由。
- [ ] 所有2+模块接口有integration，所有关键Web成功旅程有e2e。
- [ ] Shield可直接使用`project.toml`命令及IF-CI-01要求Devon实现的manifest-aware runner，不需发明入口或discovery。
- [ ] Setup/Foundation、review、M-LOCK-1与Issue失败不被伪报成功。
- [ ] 幂等、barrier并发、dirty/CAS、服务重启、Agent timeout、GitHub ack loss均有覆盖。
- [ ] checked-out release ref的accepted目标HEAD/index/worktree一致；非目标index semantic fingerprint/staged intent不变，ref-CAS/index-sync两侧kill seam均覆盖。
- [ ] Ground Truth不import `louke.*`，不从被测输出生成expected。
- [ ] 默认CI无生产secret；真实smoke从clean wheel走公开八步、六个真实Agent task与完整24项，same-SHA/delete-always/not-run均fail closed。
- [ ] wheel/sdist真实build、metadata与clean-install公开版本出口均验证。
- [ ] interfaces.md每个出口在本计划有覆盖，测试不读取未公开SQLite schema。
