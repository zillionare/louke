---
reviewer: Prism
review_round: 3
spec_id: v0.14-001-workflow-reflow-spec
reviewed_at: 2026-07-20
verdict: PASS
reviewed_digests:
  story: sha256:e04e88b336c7f08a3f67ef40354fa35c3e78ec66935805aa6f2da7272dfd0634
  spec: sha256:32b2f4c51209b0c8e4167439533370877ad38040fb44ae696d20d01280c81069
  acceptance: sha256:159e82bce6d43580200ab9f968ee5e645b528374ba896fbec8f5191b66799f9f
  test_plan: sha256:98789f6fc1baee0bf7492e6a451ce222cb5e0292fbebc3810a568abc7cbb5a71
  architecture: sha256:bc03090128f3aa29db6fc4c6fde1830b508335851a078de7d7b1a824dd8faa08
  interfaces: sha256:09ae38907b2d20aba663a3b4381922144635cb318fe19adede35b6e686887e1f
---

# v0.14-001 Design Independent Review — Round 3

## Verdict

**PASS**

六个实际文件 digest 均与本轮调度值一致。本轮完整重读 Test Plan、Architecture、Interfaces，并重新对照未变化的 Story、24项 Spec、82项 Acceptance、`project.toml`、现有 runner 与两个宿主 workflows。Round 2 两项 blocker 已形成 architecture → public interface → required test layer → CI evidence 的可实施闭环；Round 1 三项 blocker 仍保持闭合，未发现新的需求、authority、identity、owner、环境或发布门禁矛盾。

## Coverage

| 项目 | 统计 | Round 3 结论 |
|---|---:|---|
| 有效 requirements | **24/24**（21 FR + 3 NFR） | 每项均有 requirement-level 风险、公开出口、required layers 与 CI gate |
| Acceptance Criteria | **82/82** | Acceptance 82个唯一AC；Test Plan §4.1有82个唯一对应行，集合无缺失/多余 |
| User Journey | **8/8** | installed-wheel browser stand-in及release real journey均保留用户公开路径 |
| Public interfaces | **31/31** | 31个唯一接口；Test Plan引用无未知接口；每个跨模块接口有integration责任 |
| Architecture module owners | **9/9** | CLI/WEB/DRIVER/STORE/DOC/SESSION/GIT/GH/SETUP全部被interfaces使用且职责单一 |
| AC → interface → layer/runner → CI | **82/82** | U/I/E/R分配、manifest discovery、required AC与job归属均可追踪 |

## Round 2 Blocker Closure Summary

### 1. checked-out branch target index sync — **CLOSED**

- Architecture §3.2现在唯一允许Foundation把release `full_ref` checkout到当前受控worktree；完成态明确要求`symbolic HEAD == full_ref`，排除了Devon自行选择后台ref的歧义。
- Architecture §5.1/§5.3把document operation扩展为：`registered → document_written → prepared → ref_confirmed → target_index_synced → accepted`。临时index仍只用于构造单文档commit；ref CAS后由真实index lock内的单路径CAS同步目标entry。
- baseline与CAS逐path保护全部非目标stage/mode/blob、intent-to-add/assume-unchanged/skip-worktree flags及cached staged intent；不再把raw index序列化bytes错误地当产品不变量。目标预staged、conflict stage、特殊flag或来源不明均在副作用前fail safe。
- ref成功后若非目标index发生外部漂移，只保留当前非目标语义并repair Runtime造成的目标reverse diff，然后进入`needs_attention`；目标已变为第三值则不覆盖。失败恢复不使用reset/checkout/全index snapshot，也不生成第二commit。
- IF-API-06、IF-DATA-01、IF-EXT-01/02公开了目标HEAD/index/worktree、非目标semantic fingerprint、porcelain-v2与每个durable state；`prepared|ref_confirmed|target_index_synced`均不得提前产生revision、verdict或phase推进。
- Test Plan §3.1/§4.4使用真实Git CLI、真实SQLite与live HTTP，覆盖file write、prepared object、ref CAS前后、index安装前后、`target_index_synced`后及Store事务前后kill seam。accepted ground truth独立证明目标HEAD/index/worktree一致、porcelain-v2无目标记录、非目标staged intent及其它bytes语义不变，且至多一个可达controlled commit。

### 2. installed-wheel public real smoke — **CLOSED**

- Architecture §9.1及IF-CI-01定义唯一命令：`tests/e2e/run-project-venv real-smoke --profile v014 --runtime local`；不存在representative-Issue、private adapter、预锁定fixture或直写SQLite路径。
- start从同workflow、同`github.sha`的已验证wheel进行clean non-editable install；harness仅创建带run identity的disposable private repository/workspace。release Project、branch、run、tasks、gate与Issues全部由安装后的`lk serve`及公开Workbench旅程产生。
- run由Chromium完成bootstrap Human session、Setup、release/Foundation、M-STORY/M-SPEC/M-ACC，并产生六个真实且按author/reviewer隔离的Scribe/Sage/Lex task/session；关闭并重开Workbench证明原task/session恢复且dispatch count不增。
- M-LOCK-1只能由认证Human读取并消费当前challenge；之后从Project current公开reconcile动作调用IF-EXT-03，按locked Spec动态执行完整21 FR + 3 NFR = **24** target，partial/uncertain/conflict均失败。
- `real-smoke.json`固定记录source SHA、wheel identity、三文档revision/digest/commit、六task/session、恢复证据、Human gate、locked target、24个Issue/Project item正反identity、timeline及cleanup。report required AC必须精确匹配manifest声明。
- teardown唯一成功策略为`delete-always`：删除本run release Project与disposable repository，逐identity证明不存在；删除或证明失败时real job非0并阻断publish，retained manifest只用于隔离清理，不能算PASS。
- `.github/workflows/louke-ci.yml`设计为同run DAG：mandatory/build/verify → `Louke CI / required` → real-smoke → publish。real必须安装该run artifact；publish只消费相同digest wheel及配套已验证sdist，不重建、不查询latest run。failed/skipped/cancelled/timeout/missing/unknown、SHA/digest/report/24 target/cleanup任一不符均fail closed。

## Round 1 Blocker Closure Summary

| Round 1 blocker | Round 3状态 | 复核结果 |
|---|---|---|
| Human authority/trust boundary | **CLOSED** | WEB单一Human principal owner；loopback-only一次性bootstrap、exact Origin/Host、session-bound CSRF、expiry/replay；Agent不能取得或委托Human authority；return与M-LOCK失败均在Driver前拒绝且有U/I/E不变证据 |
| document ref成功但Store未接受 | **CLOSED** | deterministic OID、stable operation identity、ref proof、target-index sync、Store acceptance与全部crash recovery组成单一durable operation；只有`accepted`可登记revision/review |
| runner/real-smoke/same-SHA publish | **CLOSED** | manifest-aware collection、zero/missing/skip/xfail fail-closed、真实完整24项公开旅程、single-run same-SHA artifact chain及稳定required check均已明确 |

## Consistency Review

- [✅] **architecture ↔ spec**：24个requirements及八步journey均有组件、状态、failure/recovery和owner落点；未增加M-LOCK-1之后的产品流程。
- [✅] **interfaces ↔ acceptance可观测性**：82项AC均可从Web/HTTP、artifact/event、Git、OpenCode/GitHub或installed artifact公开边界观察。
- [✅] **interfaces无实现细节泄露**：定义外部schema、状态与invariant；未把内部类层次、私有方法、缓存策略或数据库表实现锁入接口。
- [✅] **AC → interfaces → test-plan闭合**：82个AC集合完全一致；31个接口均有最低覆盖，跨模块行为未降级为unit mock。
- [✅] **技术选择及权衡**：SQLite、临时index+目标index CAS、stable GitHub identity、stand-in+real smoke、版本与build工具均说明问题、放弃方案和主要风险。
- [✅] **project.toml配置**：`[meta].test_framework="pytest"`及`[integration]`/`[e2e]`的run、paths、cwd、framework均存在；设计通过manifest-aware runner继承而非改写该宿主合同。
- [✅] **AC测试层分配**：每项均有observable interface、required U/I/E/R、CI job及风险理由；用户journey保留browser E2E，真实外部成功证据未被stand-in替代。
- [✅] **托管GitHub CI可实施**：明确迁移并删除现有`ci.yml`/`release.yml`、保留全部mandatory/install jobs、最小权限与protected secrets、稳定`Louke CI / required`、fail-closed needs、同SHA artifact evidence和publish不重建语义。

## Non-blocking Implementation Watchpoints

1. target worktree在ref CAS与index sync之间被外部修改时，实现应按已签合同只同步仍为old-baseline的index entry、保留worktree用户bytes并转`needs_attention`，使该用户修改表现为正常unstaged diff而不是Runtime reverse staged diff；建议在§4.4矩阵中作为target“第三值”的一个参数明确落地。
2. 合并现有workflow时，`all mandatory jobs`必须实际包含当前`bats`与first-install matrix；不能只实现Architecture §9.2表中按本Spec新增的功能jobs。
3. Human session“连续8小时”在实现与fake-clock fixture中应统一为绝对寿命或idle timeout，避免两种解释产生不一致测试。
