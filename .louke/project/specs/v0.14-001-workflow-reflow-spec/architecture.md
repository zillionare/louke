# v0.14 Workflow Reflow — Architecture

- **Spec ID**: `v0.14-001-workflow-reflow-spec`
- **需求基线**: Story `sha256:e04e88b336c7f08a3f67ef40354fa35c3e78ec66935805aa6f2da7272dfd0634`；Spec revision 8 / `sha256:32b2f4c51209b0c8e4167439533370877ad38040fb44ae696d20d01280c81069`；Acceptance revision 9 / `sha256:159e82bce6d43580200ab9f968ee5e645b528374ba896fbec8f5191b66799f9f`
- **范围**: 安装后的 `lk serve` 到 M-LOCK-1 后 24 个 requirement Issues 与 release GitHub Project 关联；不包含之后的设计、开发和发布流程。

## 1. 架构目标与不变量

1. Runtime Driver 是 run、phase、gate、revision、write lease、review、Agent task 和外部 operation 的唯一推进者；Web、Agent 文本和 Markdown 都只是带前置条件的输入。
2. 任何状态变化均以 SQLite 单事务写入权威行和 event；文件、Git、OpenCode、GitHub 等非事务副作用使用持久 operation identity 和 reconcile，不以超时推断结果。
3. `story.md`、`spec.md`、`acceptance.md` 是人可读 artifact；SQLite 保存其 digest、revision、owner、review 和 commit identity，而不是复制一份可独立演化的正文。
4. 所有写操作携带 expected run revision、artifact revision/version token 和适用 lease/challenge；竞争请求至多一个成功。
5. 用户可从页面、公开 API、Markdown/Git 和外部资源看到每个验收结果；测试不得读取私有 Python 对象。

## 2. 组件边界

| 模块 ID | 组件 | 职责 | 不负责 |
|---|---|---|---|
| `CLI` | `lk serve` launcher | 硬前置诊断、绑定 workspace、启动/停止 Web 服务、输出监听地址和 stderr | 推进需求 workflow、替 Human 决策 |
| `WEB` | Web Workbench + Human Session Boundary | 启动诊断、Setup、`/projects/new`、文档页、Project current、Chat 的呈现；建立并验证 Human principal/session；采集动作、dirty/连接状态；只消费公开 Runtime API | 自行计算 PASS、信任 payload 中的 actor/role、把 Agent session 提升为 Human、持久化权威 workflow 状态、直接调用 Git/GitHub |
| `DRIVER` | Runtime Driver | 校验命令前置条件；驱动 release Foundation 与 M-STORY→M-SPEC→M-ACC→M-LOCK-1→Issues；生成 read model；调度恢复 | 接受 Agent 自述推进、绕过 Human gate |
| `STORE` | SQLite WorkflowRun Store | 原子保存 setup/release request/run/event/phase/review/gate/task/attempt/lease/operation/evidence；CAS revision；生成有序 timeline | 保存 secret、以浏览器内存代替事实源 |
| `DOC` | Document CAS | canonical template 初始化、artifact bytes/digest/version token、单写 lease、dirty handoff、discussion/review binding、锁后拒写 | 推进 phase、执行全仓库 revert |
| `SESSION` | Agent Session Manager | 将 semantic task/attempt 绑定 Scribe/Sage/Lex OpenCode session；单 active turn；消息 outbox；timeout/reconnect/result reconcile | 把自由文本 PASS 当 verdict、让 author/reviewer 共用 session |
| `GIT` | Git Adapter | remote/main 关系证明、release branch、受控单文档 commit、commit/ref evidence、安全清理 | reset/checkout/force-push 或混入无关工作区内容 |
| `GH` | GitHub Adapter | workspace namespace 检查、release Project 与 requirement Issue/Project item 的精确查询、创建、关联、reconcile | 按相似标题猜测资源、在 M-LOCK-1 前建实现 Issue |
| `SETUP` | Diagnostic & Setup Coordinator | 聚合本地、Git、认证、模型、OpenCode 和 namespace 候选；preview/confirm/reconcile workspace 级 manifest | 创建任何具体 release 资源 |

### 2.1 文字组件图与依赖方向

```text
Desktop Browser
    -> WEB
       -> SETUP -> STORE
       -> DRIVER -> STORE
                 -> DOC -> Markdown artifacts
                 -> SESSION -> OpenCode adapter
                 -> GIT -> local Git + declared remote
                 -> GH -> GitHub API
CLI -> WEB application factory; CLI -> hard-preflight only

STORE change/event -> DRIVER read model -> WEB refresh/reconnect
STORE registered operation -> DOC write -> GIT prepared/ref-confirmed -> STORE accepted revision/event
GH/SESSION uncertain operation -> DRIVER reconcile -> STORE evidence
```

依赖只能朝右；adapter 不反向推进 Driver。`WEB` 不访问 SQLite、Git 或 Agent adapter。`SESSION`、`GIT`、`GH` 只通过 operation result 返回事实，最终状态由 `DRIVER` 校验后提交。

### 2.2 Human principal 与网络 trust boundary

`WEB` 是 Human principal/session 的唯一 owner，`DRIVER` 只接收由 `WEB` 服务端认证中间件附加的 `{principal_id, session_id, kind:"human"}`；任何 JSON、form、WebSocket、Chat message 或 Agent result 中的 `actor`/`role` 都是不可信声明，必须忽略并在其试图申请 Human authority 时拒绝。`SESSION` 只持有 `kind:"agent"` 的 task/attempt/session identity，不接收 Human bootstrap capability、Human cookie 或 CSRF token，也不存在 Agent→Human principal 的转换路径。

默认 `lk serve` 仅绑定 loopback。每次服务进程启动生成 256-bit、一次性、两分钟有效的 bootstrap challenge；自动打开的 URL 只在 fragment 携带 challenge，fragment 不进入 HTTP access log。`--no-open` 时同一 URL 仅向当前 controlling terminal 显示一次。Workbench 在 exact-origin 下交换 challenge，服务端销毁 challenge并建立绑定当前服务实例与 OS session owner 的 opaque Human session；session credential 使用 `HttpOnly`, `SameSite=Strict`, `Path=/`, 无 `Domain` cookie，loopback HTTP 不设置 `Secure`，HTTPS 时必须设置 `Secure`。session 在服务退出或连续八小时后失效；服务重启必须重新 bootstrap，不从 workflow/Agent 状态恢复认证。

所有 mutation（含 bootstrap exchange 后的动作）要求 exact `Origin`/`Host`、session-bound CSRF token 与 cookie；缺失、cross-origin、过期或 replay 均在进入 `DRIVER` 前失败。健康检查与不含 workspace identity 的启动诊断可匿名读取，其余 read 也要求 session。非 loopback `--host` 在本 Spec 中不开放：`CLI` 必须在监听 socket、创建 DB 或外部 operation 前以 `NON_LOOPBACK_AUTH_UNAVAILABLE` 硬失败；不得以关闭 Origin/CSRF、复用 loopback cookie或信任反向代理 header 的方式降级。未来远程访问须由另一个明确的 TLS/identity-provider 合同开放。

### 2.3 跨边界 owner 闭合

| 合同 | 单一owner | 协作者/消费者 | 接受完成的公开证据 |
|---|---|---|---|
| Human principal/session/Origin/CSRF | `WEB` | `CLI`, `DRIVER`, `SESSION` | IF-COMMON-01/02 session与拒绝结果；业务副作用不变 |
| controlled document operation | `DRIVER` | `STORE`（durable状态）, `DOC`, `GIT`, `WEB` | IF-API-06、IF-DATA-01、IF-EXT-02同operation ID到`accepted` |
| runner discovery与CI/publish DAG | `CLI`（project runner/CI入口） | 全部9模块测试消费者 | IF-CI-01 collection/report、同SHA required/real-smoke evidence |

其余模块owner保持§2表中职责；不存在由Agent、Shield或workflow display name补全的隐式owner。

## 3. 完整数据流

### 3.1 启动、诊断与 Setup

1. `CLI` 在启动 socket 前检查解释器、包加载、workspace 路径和端口；失败非零退出，且不创建 DB/run/外部资源。
2. 可建立 Web 时，`SETUP` 执行工作流 readiness 检查。失败项形成 `READY|BLOCKED|UNKNOWN` 诊断和 remediation；`BLOCKED/UNKNOWN` 禁用 release submit。
3. 首次或 manifest 失效时，`SETUP` 从项目事实与 adapter 读取候选，写入 setup revision 后展示 preview。确认动作绑定 revision、Human actor 和选择。
4. 每个 workspace 级修改先登记 operation，再调用外部 adapter；成功、失败、结果不确定分别记录。重启先 query。全部必要事实唯一、可读、身份一致后 manifest 才 `complete`。

### 3.2 Release 请求、`main` 证明与 Foundation

1. `/projects/new` preview 只校验非空 story 和 canonical release identity，不写 release 资源。
2. confirm 以 `workspace_id + request_digest` 为 logical identity。单事务检查 active main release；被阻塞时只写一个 Backlog entry 并终止创建会话。
3. 可开始的请求进入无 WorkflowRun 的 `preflight` operation。`GIT` fetch declared remote，并以 full ref/SHA 证明上一开发分支已合入权威 `refs/remotes/<remote>/main`，且本地关系可解释；任何失败保持零 release 资源。
4. 证明通过后，以同一 foundation identity 依序 reconcile/create 本地 Project、WorkflowRun、release GitHub Project、`refs/heads/releases/<canonical version>` branch 和 Spec 目录。唯一模式是把该 release branch **checkout 到当前受控 worktree**：Foundation complete 时 `git symbolic-ref HEAD` 必须精确等于该 `full_ref`，`HEAD` 与 `full_ref` 都等于已证明的 remote main SHA；不支持 detached HEAD、另一个 worktree checkout 或“后台维护非 checked-out release ref”。clean tracked paths可按remote main tree更新，但切换前已有的用户staged/unstaged/untracked intent及其bytes必须可证明保留；不能安全切换即`CONTROLLED_COMMIT_CONFLICT`。
5. Foundation manifest 为每个将受控写入的目标记录可归因 baseline：目标在 `HEAD` tree 与真实 index 中均不存在，或真实 index 恰有一个 stage-0 entry 且 `{mode,blob}` 等于 `HEAD` tree；目标 worktree bytes 必须等于已接受 artifact baseline（首次初始化则为“已证明不存在”）。目标存在 conflict stage、intent-to-add/特殊 index flag、已预先 staged，或 worktree 来源无法绑定该 baseline 时，必须在文件写/ref CAS 前 fail safe。
6. 全部完成才从 canonical Story template 创建 `story.md`。`DOC` 计算 bytes/digest，`GIT` 生成只包含该路径的 commit，并按§5.3把目标真实 index entry同步到 accepted blob；`STORE` 绑定revision后，规范成功态为 `HEAD == full_ref == accepted commit`、目标`HEAD/index/worktree`为同一accepted blob/bytes且`git status --porcelain=v2`没有目标记录，再导航 Story 页。

### 3.3 M-STORY

1. `DRIVER` 申请 Scribe author lease、创建 task/attempt；`SESSION` 启动或恢复绑定 session。页面 Story 只读，Chat 显示 task identity。
2. Scribe 建议与理由作为受控结果保存，但 phase 保持 `waiting_human`。只有认证 Human 对当前 Story revision 可提交 `Go|Park|No-Go`。
3. Park/No-Go 幂等写 Backlog 与终态；`GIT` 仅在证明 branch 只有初始化 revision、无 dirty/unattributed/remote ref 时删除 local ref，否则 `needs_attention`。
4. Go 延续同一 Scribe task/session。Human reply 先进入消息 outbox，再按 correlation identity dispatch；ack 丢失时 query transcript，不重复逻辑消息。
5. Scribe handoff 必须有文档实际变化。受控 commit 成功后，Human 与独立 Sage reviewer 对同一 digest 开始 review。Human 可编辑/discuss；Sage 与 Scribe session 分离。
6. Human 与 Sage 均 PASS、零 open/reopen discussion 且 digest 相同才进入 M-SPEC；否则同一 Scribe 上下文产生下一 revision，旧 verdict stale。

### 3.4 M-SPEC 与 M-ACC

1. M-SPEC 由继承 Story 上下文的 Sage author task 起草；Human 只读。结构验证和单文档 commit 后开放 Human review，并启动独立 Lex session。
2. Human 修改先 commit；Lex 总是读取最新 commit、Human diff/discussions，并只在 lease 生效时写 discussion。语义 gate 要求 Human `no comment`、Lex PASS、零未解决 discussion、相同 digest。
3. 语义 gate 后执行 deterministic format/coverage check；失败按 file/location/rule 返回原 Sage 修订。通过才进入下一 phase。
4. M-ACC 重用相同 review protocol，并绑定当前 Story/Spec digests；覆盖全部 Valid FR/NFR。上游 digest 变化立即使 Acceptance verdict stale。
5. Human return-upstream 只能选择 workflow 声明的目标。事务保留历史，把目标和下游 verdict/format/approval 标为 stale/superseded，再移动 phase；Agent 建议只形成 Human wait。

### 3.5 M-LOCK-1 与 Issues

1. 三文档当前 review/format/discussion 全闭合时，`DRIVER` 生成一次性 challenge，绑定 run revision 与 S/P/A digests；Project current 显示批准动作。
2. 认证 Human 提交 challenge 后，单事务批准 gate、锁定三个 artifact、写 event。锁后 `DOC` 对任何写请求返回 `REQUIREMENTS_LOCKED`。
3. `GH` 从锁定 Spec 枚举 Valid 非 `❌` requirement。本 revision 为 24 项。每项 operation identity 为 `repository node ID + spec_id + requirement_id + joint_digest`；只有 repository、token、body links、joint digest 和 Project item 全部精确匹配的唯一候选可复用。
4. create/link 分项记录；部分失败不回滚成功项。未知结果先 query；零/多/冲突候选进入 `needs_attention`，不创建第二候选。全部 24 项 `linked` 后 phase 完成。

## 4. 状态与生命周期

### 4.1 Run / phase

```text
M-STORY(authoring <-> review) -> M-SPEC(authoring <-> semantic_review -> format)
 -> M-ACC(authoring <-> semantic_review -> format) -> M-LOCK-1(pending)
 -> ISSUES(reconciling) -> requirements_ready
```

合法 return：M-SPEC→M-STORY；M-ACC→M-SPEC|M-STORY。Park/No-Go 从 M-STORY 进入对应终态。通用 run status：`running`, `waiting_human`, `waiting_agent`, `blocked`, `needs_attention`, `completed`, `parked`, `no_go`。`blocked` 表示已知可修复条件；`needs_attention` 表示 identity/副作用不能安全判定。只有 Driver transition command 能改变 phase。

### 4.2 Revision

- `artifact_revision` 单调递增，绑定 `document path + bytes digest + parent commit + commit SHA + actor + round + task`。
- 生命周期：`current` → `stale|superseded`；M-LOCK-1 后当前 revision 为 `locked`。历史 revision 不删除、不改写。
- 浏览器 `version_token` 是 artifact identity 的 opaque 表示；PUT 必须同时匹配 run revision、artifact revision、token 和 lease。
- Human 未保存编辑仅存在浏览器 dirty 状态；交接前 Web 通过 dirty endpoint 注册，Driver 禁止向 Agent 发 lease，直到 save 或显式 discard。

### 4.3 Review / gate

- review round：`collecting -> waiting_human|waiting_reviewer -> rework|passed|stale`。verdict 必须绑定 artifact digest；`comment`、dirty、open/reopen thread 均不等于 PASS。
- gate：`pending -> approved`，或因上游返回进入 `stale`。M-LOCK-1 无 Agent approval 路径；challenge 仅一次有效且绑定 joint digest。

### 4.4 Task / attempt / session

- task 是稳定 semantic intent；attempt 是一次可恢复执行；session 是 OpenCode 外部身份。
- attempt：`queued -> dispatching -> running -> reconciling -> completed|rejected|failed|interrupted|lost`。HTTP timeout 只进入 `reconciling`。
- 同一 task 最多一个 active attempt；同一 session 最多一个 active turn。只有确认 session lost 且无有效结果，才新建 attempt；author/reviewer task 不共享 session。

### 4.5 Write lease

- lease 字段：holder actor、role、run、document、base revision/token、lease ID、issued/expires time、status。
- `active -> released|expired|revoked`；同一 document 至多一个 active lease。到期不自动接受任何已产生 bytes；结果仍须 CAS。
- dirty Human 页面阻止 Agent lease；phase authoring 时 Human 无 lease且只读；第二轮 review 的 Human 默认可写，只在 Agent 实际写入窗口临时只读。

## 5. 持久化设计

### 5.1 SQLite WorkflowRun store

同一 workspace 使用 `.louke/runtime/workflow.sqlite3`，启用 foreign keys、WAL、busy timeout。关键公开 read model 由下列权威实体投影，实际表迁移可演进但不能改变 `interfaces.md` 的 JSON schema：

| 实体 | 唯一性 / CAS | 内容 |
|---|---|---|
| setup revisions/manifests | workspace + revision | candidates/provenance、decisions、readiness、operation refs |
| release requests/backlog | workspace + request digest | story、canonical version、阻塞原因、source identity |
| projects/runs/events | project/run ID；run revision CAS；run+sequence | phase/status、definition、ordered trace |
| phases/reviews/verdicts | run+phase+round+actor role+artifact digest | round、Human/reviewer结果、stale原因、format result |
| artifact revisions/leases | run+path+revision；每 path 单 active lease | digest/token/commit/actor；lease holder/base/expiry |
| semantic tasks/attempts/messages | task ID；task+attempt；correlation unique | role/scope/contract/session/status；outbox/dispatch evidence |
| gates | run+gate kind；challenge unique | expected revision、joint digest、actor/time/status |
| external/document operations/resources | provider+operation identity；stable resource ID | expected/actual identity、document operation的`registered|document_written|prepared|ref_confirmed|target_index_synced|accepted|conflict|needs_attention`、known effects、reconcile evidence、error |
| issue links | operation identity + requirement ID | Issue number/URL、Project node/item ID、link status |

任何 run mutation 同事务执行：校验 expected revision → 更新实体 → run revision +1 → 写 event。commit 前崩溃二者均无，commit 后二者均有。SQLite busy/constraint 映射稳定 409，不重试成双成功。

### 5.2 Markdown artifacts

- 路径限定为 `.louke/project/specs/<spec-id>/{story,spec,acceptance}.md`，canonical UTF-8/LF。
- 正文 digest 为 `sha256:<hex>`；self-referential digest 按上游已声明 placeholder scheme 验证。
- discussion 继续使用可被 `lk discuss query` 识别的 blockquote contract。Document CAS 原子写临时文件、fsync、rename；只有下述 document operation 到达 `accepted`，该 revision 才成为 current 并可进入 review。

### 5.3 Git commits 与脏工作区隔离

- `DRIVER` 在任何文件写之前登记稳定 `document_operation_id = hash(repository identity, full ref, run, artifact kind, base artifact revision, expected parent, intended digest, idempotency key)`；同一 logical write 永远复用该 ID。登记同时证明 `HEAD` symbolic ref=`full_ref`且两者=`expected_parent`，持久化preimage/intended digest、allowlisted path、目标`HEAD/index/worktree` baseline、**非目标 index semantic fingerprint**、确定性的commit metadata。fingerprint逐path包含全部stage的`mode/blob/stage`、intent-to-add/assume-unchanged/skip-worktree等Git可见flags及相对`expected_parent`的cached diff identity；它保护staged intent，不把index文件序列化bytes当产品不变量。
- 目标index前置条件唯一：目标在expected parent与index均不存在，或index只有一个stage-0 entry且`mode/blob`精确等于expected-parent tree；目标worktree必须为已登记preimage。预先staged、conflict stages、特殊flag、来源不明，或任一非目标index fingerprint在文件写/ref CAS前漂移，均fail safe且不覆盖index。非目标worktree bytes同样逐path比较；允许其既有staged/unstaged/untracked状态存在，但Runtime不得改变。ref已CAS后才观察到非目标漂移时不再接受operation；仅可按下述target repair消除Runtime造成的目标reverse diff。
- durable顺序固定为`registered → document_written → prepared → ref_confirmed → target_index_synced → accepted`。`DOC`原子写目标bytes；`GIT`用独立临时index从expected parent生成确定blob/tree/commit；`update-ref <full_ref> <prepared> <expected_parent>` CAS并回读后记`ref_confirmed`；随后执行一次受锁保护的**单路径真实index CAS**：仅把目标stage-0 entry设为prepared tree中的`{mode,blob}`（新文件则新增），且在同一index lock内验证目标仍为旧baseline、非目标semantic fingerprint仍完全相等。同步后回读目标entry与全部非目标entries，才记`target_index_synced`。最后`STORE`单事务插入artifact revision/event/current pointer并转`accepted`；此前不得登记verdict、派发review或推进phase。
- 单路径index CAS以真实Git index lock串行化：从锁内观察到的真实index构造候选，仅替换目标entry，验证候选的所有非目标entries/flags/cached intent与登记fingerprint相同后原子安装。底层index版本、extension或序列化bytes可由Git重写，不属于“不变”断言；公开语义必须不变。accepted时再次证明`symbolic HEAD=full_ref`、`HEAD/ref=prepared`、目标`HEAD/index/worktree`分别为prepared blob/intended bytes、非目标fingerprint不变，且porcelain-v2中目标无Runtime制造的reverse staged/unstaged记录。
- 恢复只按operation与独立Git/文件事实推进。ref仍为expected parent时复用同一prepared OID做一次CAS；ref=prepared而目标index仍为旧baseline时，从`ref_confirmed`继续单路径sync；若进程在index原子安装后、ledger写入前死亡，目标index已等于prepared blob且非目标fingerprint不变时只补记`target_index_synced`；该状态重启后验证HEAD/index/worktree再接受同一revision。若ref已为prepared、目标仍精确为旧baseline但非目标fingerprint已漂移，允许在index lock内保留**当前**全部非目标entries/flags并只把目标同步为prepared blob，随后转`needs_attention`而非accepted；这是target repair，不把新的非目标状态冒充operation baseline。目标index既非旧baseline也非prepared、HEAD不再指向full_ref或bytes无法归因时保持当前index/worktree并`conflict|needs_attention`。任何分支都不得建第二commit；已`accepted`重试返回原identity。
- crash可能留下OID相同的不可达object，或在`ref_confirmed`期间暂时暴露目标reverse staged diff；前者不算重复commit，后者在目标仍为旧baseline时必须由幂等sync/target repair消除，绝不能成为accepted或长期恢复结果。目标已被用户改变时不覆盖，porcelain差异归因为该外部变化并`needs_attention`。失败恢复不执行reset/checkout/全index还原，不恢复raw index snapshot；evidence明确列出目标HEAD/index/worktree blob、非目标fingerprint差异和porcelain-v2记录。

## 6. 故障边界与恢复

| 故障 | 边界与状态 | 恢复策略 | 禁止行为 |
|---|---|---|---|
| Web 建立前失败 | CLI 非零；无 DB/run/create | Human 按 stderr remediation 后重启 | 显示 Web READY |
| Web readiness 失败 | Web `BLOCKED` | 重跑单项检查；保留 setup revision | 提交 release |
| 网络/GitHub ack 丢失 | operation `uncertain` | 按 stable identity query；唯一精确匹配补 evidence，确认未发生才重试 | 将 timeout 当失败后立即 create |
| OpenCode timeout/断连 | attempt `reconciling` | 查询原 session/turn/result；running 等待，lost 才新 attempt | 重复 dispatch 或猜 PASS |
| 服务/浏览器重启 | 从 SQLite + files + adapters 重投影 | 回到同 phase/revision/task/session；SSE/轮询从 event cursor续接 | 依赖进程内 singleton/transcript |
| 并发状态/文档写 | 一个 CAS winner，其余 409 | 客户端刷新 current state，再明确重做 | last-write-wins |
| Human dirty 与 Agent lease | Agent lease 不授予 | Human save 或显式 discard；页面继续显示 dirty blocker | 自动丢弃草稿 |
| document operation 任一 crash seam | operation保持最后durable状态；revision/review不接受 | 比较preimage/intended bytes、prepared OID、HEAD/ref、目标index entry、非目标semantic fingerprint与porcelain-v2；依序补`ref_confirmed`/`target_index_synced`/同一revision，或`needs_attention` | 新建commit、把reverse diff当成功、恢复raw index、覆盖不可归因编辑 |
| Git dirty/index冲突/ref移动 | `CONTROLLED_COMMIT_CONFLICT` | ref CAS前保持全部bytes/index；ref已成功且目标仍为旧baseline时总是仅同步目标：fingerprint相等可继续，非目标漂移则保留其当前语义并`needs_attention`；目标已变则保持现场 | reset/checkout/force/全index替换 |
| Foundation identity冲突 | `conflict|needs_attention` | 展示 expected/actual；精确 reconcile 后继续 | 创建第二套资源 |
| SQLite损坏/无法开启 | Web workflow `BLOCKED`（服务仍可诊断） | 只读诊断、备份/修复；不自动重建丢失事实 | 空库当成功历史 |

## 7. 技术选型与版本

| 选型 | 版本合同 | 解决的问题 | 放弃方案 | 主要风险/控制 |
|---|---|---|---|---|
| Python | 支持 `3.11–3.14`，CI全矩阵 | 继承项目现有 Runtime/CLI | 迁移语言 | 多版本差异；矩阵验证 |
| Starlette / Uvicorn / httpx | 继承 `starlette>=0.38,<1.0`、`uvicorn>=0.30,<1.0`、`httpx>=0.27,<1.0` | Web/API、live server、协议 adapter | 新增 Web 框架 | 宽版本范围漂移；CI constraints 固定解析版本并保存 freeze evidence |
| SQLite `sqlite3` | Python stdlib，WAL + FK | 单用户 workspace 原子持久化与重启恢复 | 浏览器状态、外部 DB | 网络文件系统锁语义；限定本地 workspace并显式 busy/conflict |
| Git CLI | `>=2.39`，以现有 executable 调用 | refs、tree、commit 和 remote identity 可独立验证 | GitPython/libgit2 | 平台输出差异；使用 machine-readable flags、全 ref/SHA |
| OpenCode HTTP/SSE adapter | 继承现有 adapter contract | session/turn/message恢复 | 旧 `lk agent` orchestration | timeout不代表停止；operation reconcile |
| GitHub REST/GraphQL adapter | GitHub API + isolated stand-in | Project/Issue identity和关联 | 默认 shell `gh` 驱动产品 | eventual consistency/rate limit；stable IDs、query-before-create |
| Markdown + `markdown` | `markdown>=3.6,<4.0` | 人可读 artifact 与现有 preview | 富文本数据库 | bytes/CAS冲突；canonical UTF-8和digest |
| 测试 | `pytest==8.4.1`, `pytest-cov==6.2.1`, `playwright==1.54.0`, Chromium bundled revision | unit/integration/browser层统一 | Selenium、自建浏览器驱动 | browser下载与版本漂移；CI固定包和browser cache key |
| 质量/构建 | `pre-commit==4.6.0`, `mypy==1.16.1`, `build==1.2.2.post1` | format/lint/type、真实 wheel/sdist | 仅人工 review | 旧代码类型债；沿用项目非 strict mypy并阻止新增错误 |

不新增数据库、队列或缓存依赖。所有依赖须兼容 MIT 项目；上述工具均为成熟稳定版本。运行依赖仍由 `pyproject.toml` 声明，Devon 增加 CI 约束文件锁定测试解析结果，而不是把 Louke 技术栈泛化到 Louke 管理的其它宿主项目。

## 8. Release identity 与 artifact 验证

本 Spec 不新增或收窄 `/projects/new` 对“合法 release version”的产品政策；输入集合继承发布时已签署的宿主 Project preview 合同，Runtime 只消费该合同返回的 `{external,canonical,branch}`，本设计不另行排除 prerelease/build metadata。以下 artifact 同步只针对本次已确定的 Louke shipping identity：external tag `v0.14.0`、canonical/package metadata `0.14.0`、release branch `releases/0.14.0`。

本次需求 workflow 不执行 publish；但实现随 Louke `0.14.0` 交付，真实构建物为 wheel 与 sdist。权威版本源为 root `pyproject.toml [project].version`，project-local adapter 固定为 `tools/louke_python_release_adapter.py`：

1. PR/push CI 仅校验当前 version source 并构建；从 wheel/sdist metadata 提取版本，与 version source 精确比较。
2. tag/release 时 adapter `prepare --tag v0.14.0` 在构建工作副本写入 `0.14.0`；不把 tag 本身当 artifact version。
3. `python -m build` 产生 `dist/louke-0.14.0-py3-none-any.whl` 与 `dist/louke-0.14.0.tar.gz`；adapter `inspect --artifact` 提取每个版本。
4. wheel 安装到 clean venv 后，公开出口 `lk --version` 与 `importlib.metadata.version("louke")` 都必须为 `0.14.0`。sdist 的安装后出口相同；无独立部署出口（本产品是本地 CLI/Web package）。
5. evidence 分为 `scheme-selected`、`source-prepared`、`artifacts-built`、`artifact-versions-verified`。缺 identity、prepare/build/inspect失败、任一 artifact缺失/不匹配、安装后出口不匹配或结果不确定均阻断 publish。

## 9. GitHub Actions CI 合同

Devon 创建`.github/workflows/louke-ci.yml`（顶层`name: Louke CI`，聚合job id/name均为`required`，因此check精确显示`Louke CI / required`），并在同一迁移变更中把现有`ci.yml`的mandatory jobs/install matrix和`release.yml`的tag build/publish搬入该workflow后删除两份旧workflow；不得保留旧`lk agent archer ci-scan`或“查询最新CI run”的发布路径。目标分支为`main`与`releases/**`，tag为`v*`。一个workflow run内以`github.sha`贯穿build、required、real smoke与publish，避免按文件名、display name或latest run猜测evidence。

### 9.1 Runner、权限、触发与依赖

- `pull_request`/`push`：`main`, `releases/**`；`workflow_dispatch` 可重跑 stand-in。真实外部 smoke 使用独立 manual/release environment，不在 fork PR 上运行。
- 默认 `ubuntu-22.04`；unit matrix Python `3.11,3.12,3.13,3.14`；install compatibility 继承现有 Linux/macOS/Windows matrix，但不重复计入本 Spec功能 gate。
- workflow顶层及real-smoke job的GitHub Actions token均保持`permissions: contents: read`。PR jobs无secret/写token；real-smoke只在受保护environment approval后读取一个限制于sandbox owner、具备disposable repo create/delete及Issues/Projects读写的独立credential，不扩大workflow token，也绝不运行fork checkout。
- pip cache key包含 OS、Python、`pyproject.toml` 和 CI constraints digest；Playwright cache包含 package/browser revision。每 job 创建 clean venv，安装 wheel而非 editable package。

现有`tests/e2e/run_e2e.py`固定收集v0.13资产且parser没有real profile，本轮必须由Devon扩展而非让Shield绕过runner。唯一discovery事实源为新增`tests/runner-manifest.toml`（schema见IF-CI-01）：`integration/v014`必须指向`tests/integration/v014_workflow_reflow`，`e2e/v014`必须指向`tests/e2e/v014_workflow_reflow`，`profile=all`必须包含既有install/chromium及v014；`real-smoke/v014`只指向v0.14 real资产，并把完整公开旅程实际阻断的`AC-FR1700-03, AC-FR1800-02, AC-FR1900-01, AC-NFR0200-01, AC-NFR0200-02, AC-NFR0300-01, AC-NFR0300-03`列为`required_ac_ids`。runner必须先做pytest collect-only并输出collection JSON，再执行；目标路径不存在/零收集、请求profile或runtime没有case、manifest声明的required AC在该层漏收集、执行报告漏case或有skip/xfail均非零。`project.toml`现有两条命令因此实际覆盖其声明paths中的v0.14目录，而不再等同于硬编码v0.13文件。

唯一可复制入口固定为`tests/e2e/run-project-venv real-smoke --profile v014 --runtime local`，没有“代表Issue”或单资源模式。runner只能编排环境并操作公开协议；产品推进只能经IF-CLI-01、IF-COMMON-01、IF-WEB-01..09及对应IF-API/IF-EXT read/reconcile出口，不得import私有adapter、直写SQLite/Runtime文件、预造task/gate/revision或启用测试后门。

- **start**：下载本workflow `build-artifacts` job产生且identity report绑定当前`github.sha`的wheel，在全新venv非editable安装并核对wheel digest/`lk --version`。用受保护GitHub sandbox owner下的公开GitHub REST创建本run唯一、disposable private repository（`auto_init`产生`main`），clone到隔离`HOME/XDG/GIT_CONFIG`的空workspace；repository/provider namespace均带不可复用run identity，禁止产品repo、既有release Project或共享Issue。随后只执行安装wheel的`lk serve --host 127.0.0.1 --port <random> --no-open`，从controlling terminal取得一次性bootstrap URL。GitHub repo的预置/最终删除属于harness环境生命周期，不写Louke状态；release Project、branch、run、task、gate与Issues必须由产品公开旅程创建。
- **ready**：60秒内分别证明Workbench匿名health可达、真实OpenCode`/global/health`及身份可读、GitHub token对刚建repo/owner具备所需repository/Issues/Projects读写与delete权限；只做非业务read/probe，不创建release Project/Issue、不交换Human challenge。任何identity与本run sandbox不符即失败。
- **run**：Chromium从bootstrap URL建立唯一认证Human session，经启动诊断和`/setup` preview/confirm完成Setup；在`/projects/new`提交当前shipping release `0.14.0`并等待Foundation，核对IF-EXT-01显示checked-out release ref。然后完整走公开页面：真实OpenCode Scribe完成M-STORY author，认证Human提交Go并在允许的review编辑出口把三份文档分别收敛到本轮绑定Story/Spec/Acceptance bytes；M-STORY首个turn后关闭并重开Workbench，经公开current/task出口证明同一task/session仍可恢复且不重复dispatch。真实且互相隔离的Sage完成M-STORY review与M-SPEC/M-ACC author，真实Lex完成M-SPEC/M-ACC review。REJECT只能经页面discussion/rework继续，最多受job timeout约束，不能伪造PASS/result。所有review/format闭合后，Chromium读取当前challenge并点击M-LOCK-1 approve，actor必须来自该Human session。最后由Chromium点击Project current公开reconcile动作（产品调用IF-EXT-03），按locked Spec动态target执行完整集合（本revision精确21 FR+3 NFR=24），等待页面与GET出口均显示24项`linked|reused`；任何partial/uncertain/conflict均失败，不能缩减target。
- **evidence**：`real-smoke.json` schema固定为`{schema_version:1,mode:"real",source_sha,wheel:{digest,version,installed_outlets},command,workspace:{repository_node_id,repository_full_name,workspace_id},release:{external,canonical,full_ref,head_sha},documents:{story|spec|acceptance:{revision,digest,commit_sha}},opencode:{tasks:[{phase,role,task_id,attempt_id,session_id,result_status}],recovery:{task_id,before_session_id,after_session_id,dispatch_count_before,dispatch_count_after,evidence_sequence}},m_lock_1:{gate_id,status,actor,joint_digest},target:{locked_spec_digest,computed_count,required_ac_ids,requirement_ids},issues:[{requirement_id,operation_id,issue_number,issue_node_id,issue_url,project_node_id,item_id,status,forward_identity,reverse_identity}],counts:{requirements,issues,items},timeline:{first_sequence,last_sequence,digest},cleanup:{policy,attempted,deleted_ids,verified_absent,retained_ids}}`。三个count必须均为24，`requirement_ids`与独立locked fixture逐项相等、Issues数组无重/漏且正反identity绑定三文档digest；task列表必须证明上述六个真实author/reviewer角色阶段和不同session；recovery前后session与dispatch count必须相等；gate actor为Human。report的`required_ac_ids`必须精确等于manifest集合。
- **teardown/retention**：`finally`先经公开query保存非秘密最终evidence，再关闭browser/Workbench，使用GitHub公开API删除本run release Project及disposable repository，并以node ID/精确namespace查询证明均不存在（repo删除同时覆盖24 Issues/items仍须在cleanup manifest逐ID列出）。成功策略唯一为`policy:"delete-always"`且`retained_ids=[]`,`verified_absent=true`；无法删除或无法证明时exit非零、publish阻断，并输出redacted retained-resource manifest供sandbox管理员24小时内隔离清理，绝不把retention算PASS。

受保护`release-smoke`environment只提供`LOUKE_REAL_OPENCODE_URL`、`LOUKE_REAL_OPENCODE_TOKEN`、`LOUKE_GITHUB_SANDBOX_OWNER`和限制在该sandbox owner的`LOUKE_REAL_GITHUB_TOKEN`；Human credential只由本次loopback bootstrap产生。job不接受fork代码，不上传URL内credential/token/cookie。缺secret、零准备、identity/permission probe失败、绕过任一gate、非真实Agent结果、partial target、任一report字段/AC/cleanup proof缺失、collection为零、skip/not-run都必须非零。

### 9.2 Job DAG 与命令

```text
quality ─┬─> build-artifacts ─┬─> unit[3.11..3.14]
         │                    ├─> integration
         │                    └─> e2e-standin
         └─> ac-trace -------------------------┐
build-artifacts -> artifact-verify ------------┤
install-matrix + all mandatory jobs -----> Louke CI / required
tag/manual-release: required + build-artifacts + artifact-verify -> real-smoke
tag/manual-release: required + real-smoke + same artifacts -> publish
```

| job/check | 命令合同 | evidence |
|---|---|---|
| `quality` | `pre-commit run --all-files`；`python -m mypy louke` | logs |
| `build-artifacts` | `python -m build` | wheel、sdist、build log |
| `artifact-verify` | adapter inspect 每个 artifact；clean venv install；`lk --version` 与 metadata compare | JSON identity report |
| `unit` | `python -m pytest -q tests/unit --cov=louke --cov-report=xml --cov-fail-under=95` | per-version JUnit；3.12 coverage XML |
| `integration` | `tests/e2e/run-project-venv integration` | JUnit、stand-in ledgers、failure snapshots |
| `e2e-standin` | `tests/e2e/run-project-venv e2e --profile all --runtime both` | Playwright trace/video仅失败时、journey report `mode=stand-in` |
| `ac-trace` | 本次由 Devon 实现 project-local `python tools/check_ac_traceability.py --acceptance .louke/project/specs/v0.14-001-workflow-reflow-spec/acceptance.md --tests tests`；不调用旧 `lk agent` | closure report：82/82，anti-cheat report |
| `Louke CI / required` | `if: always()` 检查所有 required needs 的 conclusion 精确为 success | 单一稳定 required check |
| `real-smoke` | `needs:[required,build-artifacts,artifact-verify]`，仅tag或显式manual release；下载同run build artifact并执行唯一real命令 | 完整24项`real-smoke.json`；`source_sha`与wheel digest须等于本run`github.sha`/artifact report |
| `publish` | `needs:[required,real-smoke,build-artifacts,artifact-verify]`；只下载并发布该run已验证且real smoke实际安装的同digest wheel及配套已验证sdist，不重建/替换 | PyPI/GitHub Release evidence与输入artifact digests逐字相等 |

`required` 对 failed、cancelled、timed_out、skipped、缺失或未知 conclusion 一律失败。job timeout：quality/trace 10 分钟，build/unit 20 分钟，integration 25 分钟，e2e 35 分钟，real smoke 60分钟。所有 PR 强制quality、build、artifact verify、全部unit、integration、stand-in e2e、trace及现有install matrix；tag/manual release同样先跑这些gate。`publish`不得调用Actions API寻找check，不接受旧SHA、旧run、同名外部check或手工布尔输入；`needs`缺失/skipped/cancelled/timeout/unknown、artifact下载来源SHA不符、wheel/sdist digest与build/verify/real report任一不一致、real target非24/漏required AC、report not-run或cleanup失败一律不运行publish且workflow失败。

### 9.3 Evidence、安全与演进

- 保存 JUnit、coverage、artifact identity JSON、stand-in operation ledger、失败时 DOM/Playwright trace和 redaction scan，保留 14 天；wheel/sdist保留 7 天。上传前扫描 secret canary。
- stand-in 是外部协议替身，不替换 Driver、Store、Document CAS 或 reconcile。真实smoke必须从clean wheel/workspace经公开八步旅程形成locked revision并reconcile动态24项；report满足§9.1完整schema。不存在代表Issue、预锁定fixture state或private adapter路径；`delete-always` cleanup evidence缺失即失败并按retained-resource policy隔离。
- 迁移完成态只保留`.github/workflows/louke-ci.yml`：旧`ci.yml`和`release.yml`须在同一实现PR删除，避免旧workflow继续publish或产生漂移gate。普通jobs保持`contents:read`；real smoke仅从protected environment取得sandbox PAT；publish job单独使用`contents:write`和`PYPI_API_TOKEN`，前置job不得读取publish secret。branch rules只要求唯一`Louke CI / required`。任何runner、命令、测试路径、artifact或外部adapter变化必须同步三份设计文档与workflow。

## 10. 关键取舍总结

1. **单体模块化 Driver 而非微服务**：单用户本地产品需要跨状态/file/Git的强协调，进程内模块加 SQLite更易恢复；代价是进程故障域较大，以operation ledger和启动reconcile控制。
2. **SQLite事实源 + Markdown/Git artifact**：避免把聊天或浏览器当状态，又保留用户可审阅历史；代价是跨存储无法两阶段提交，采用prepare/execute/reconcile和commit evidence。
3. **lease + CAS，而非实时共编**：满足单写者和清晰commit归属；放弃多人实时编辑体验，本Spec本就限定单Human。
4. **临时index构建commit + checked-out branch上的目标index CAS**：临时index保证commit allowlist；accepted前再把真实index的目标entry同步到新HEAD，避免Runtime制造reverse diff，同时逐项保护非目标staged intent。放弃“raw index bytes完全不变”和非checked-out隐藏ref；代价是多一个持久状态/index-lock crash seam，以semantic fingerprint和幂等reconcile控制。
5. **精确GitHub identity而非标题搜索**：牺牲“自动猜测”便利，换取并发/ack loss下不重复资源。
6. **默认CI stand-in +受保护真实smoke**：PR可复现且不暴露secret；协议替身不能证明真实权限/生态漂移，因此release前真实smoke仍是阻断门禁。

## 11. 实现边界与技术风险

- 现有 Project collection 仍有进程内实现路径；本轮必须把 active Project、Backlog、preview 和 foundation identity统一迁入同一 SQLite事实源，否则 FR-0300/FR-2100不能成立。
- GitHub Project GraphQL eventual consistency可能在创建后暂时查不到 item；operation必须保持`uncertain`并有有界退避，不能转成第二次create。
- 浏览器 dirty 状态在tab崩溃时无法保存未提交bytes；合同只保证已保存流程事实恢复。页面须明确本地未保存草稿已丢失，不能伪称恢复。
- OpenCode能否稳定查询已断连turn/result仍是高风险；adapter必须区分`running/not_found/ambiguous`，ambiguous只能`needs_attention`。
- 真实OpenCode六个task及GitHub 24项使release smoke受模型时延、rate limit与review结果波动影响；不以重试伪造PASS，只允许公开rework并受60分钟timeout约束，任何不确定都阻断publish。
- Windows/macOS Git ref、文件锁和原子rename差异需要install matrix回归；主workflow功能e2e以Linux为required，发布兼容矩阵继续覆盖三平台。
- split/sparse index与Git index extension可能在目标单路径CAS时被Git重写；合同只保护可观察entry/flag/staged intent语义，integration矩阵必须覆盖支持的Git>=2.39形态，无法安全保留即fail safe。
- 当前依赖没有仓库级lock；CI constraints是本轮可复现性补强。更新依赖时必须先验证Python 3.11–3.14与wheel e2e。
