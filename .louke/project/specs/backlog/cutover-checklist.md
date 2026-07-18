# v0.14 Programmatic Workflow Cutover Checklist

## 用途

本文保存 v0.14 从旧 Maestro 驱动流程切换到程序化 Runtime 所必需、但不宜全部写成用户故事的架构与交付约束。它是 `story.md` 的规范性配套输入；后续 `spec.md`、`acceptance.md`、`architecture.md`、`interfaces.md`、`test-plan.md`、Issue 拆分和发布审计必须逐项建立追踪，不得静默删除、降级为建议或仅以单元测试替代产品证据。

## A. Responsibility inventory 与 Agent 注销

- [ ] 建立真实、版本化、可审阅且零 `unclassified` 的 built-in responsibility inventory，完整覆盖内置 workflow definitions、Agent prompts/tool contracts、registered handlers 和实际 dispatch。
- [ ] inventory 中每项职责具有稳定 identity、来源、`program`/`semantic` 分类、分类理由、目标 handler/task 和迁移状态；原 mixed 职责在 dispatch 前拆除程序控制/权威副作用与语义输入/输出。
- [ ] catalog build、workflow 创建和 task dispatch 均拒绝缺项、分类不一致、纯工具包装 Agent、缺失 handler/prompt contract 或 semantic task 承担权威副作用。
- [ ] Scout、Warden、Keeper 从新 workflow dispatch、内置 Agent catalog、Chat Agent 列表和 model bindings 中正式注销；新 run 不得创建这三个角色的 task、session 或隐式 fallback。
- [ ] Scout 的语义残余归 Scribe，Warden 的 story 语义残余归 Scribe/Sage/Lex，Keeper 的语义审查归 Prism；其余确定性职责映射到明确的 program handler。
- [ ] cutover 后，active catalog、docs、help、prompts 和路由中必须排除 Scout、Warden 和 Keeper（职责清单覆盖三者，不仅是 Scout/Warden）；不可变的历史/审计 artifact 可保留其名称，不得仅因擦除名称而重写历史 artifact。

## B. 唯一生产装配与自动 Driver

- [ ] 建立唯一 production composition root，共享持久化 Store、版本化 Catalog、Handlers、Capabilities、Orchestrator、Gate service、OpenCode adapter 和 program executor；不得依赖测试夹具注入共享 store。
- [ ] 接入自动 workflow driver：进入 program step 时自动运行注册 handler 并验证真实结果；进入 semantic step 时才创建受控 Agent task；进入 human gate 时持久停止并等待匹配当前 revision/digest 的人类决定。
- [ ] Web、CLI 或 Agent 不得任意提交 program result、`done`、`pass`、目标 stage 或伪造的权威证据来推进 run；只接受对应 handler/adapter 的真实结果。
- [ ] 用完整、可完成的 `new_feature` 和 `bug_fix` definitions 替换生产最小演示图，并覆盖 Story、requirements/design approvals、实现、权威测试、release close 和 history。
- [ ] `lk serve`、Web 项目创建、Chat 和默认 Maestro 入口全部进入同一条新 Runtime；旧 `maestro advance` 与旧 M-FOUND 路径不能写入或推进 v0.14 run。
- [ ] 服务或进程重启后，run、gate、task、step attempt、artifact/evidence 和 event 能从持久化状态准确恢复；不依赖旧 Agent 会话保存隐式进度。

## C. 文档、产品面与兼容边界

- [ ] 同步更新 Maestro prompt、README、`docs/workflow.md`、Agent 列表、模型绑定说明、Chat 列表和用户操作文档；不得继续把 Scout/Warden/Keeper 或旧 Maestro pipeline 描述为 v0.14 默认流程。
- [ ] cutover 后，active catalog、docs、help、prompts 和路由中必须排除 Scout、Warden 和 Keeper（职责清单覆盖三者，不仅是 Scout/Warden）；不可变的历史/审计 artifact 可保留其名称，不得仅因擦除名称而重写历史 artifact。
- [ ] cutover 后不存在 Scout/Warden/Keeper 的 deprecated CLI adapter、旧可执行路径、旧 Agent prompt、旧 Agent session 或第二套状态权威；pre-cutover v0.13 开发基线在 release tag/cutover 前结束，安装后的 v0.14 无旧注册/路由/Runtime fallback/共存窗口。
- [ ] 旧 workspace 通过显式 preview/confirm 采用为**全新 v0.14 项目**；该 adoption 可检查代码/历史，但不得从 v0.13 Louke 状态（`current_stage`、evidence 等）迁移或推断 v0.14 权威 run 状态；旧证据只读保留。

## D. Installed-wheel E2E 与切换证据

- [ ] 从当前 checkout 构建并安装 v0.14 wheel，在隔离、干净 workspace 中仅通过公开 `lk serve`（运维启动命令）、Web Chat（核心开发唯一入口）、真实持久化 store 和声明的 external adapter 完成至少一条完整 `new_feature` 产品旅程；workflow 推进不得通过 CLI 完成。
- [ ] 该旅程至少覆盖 setup、Story、Go 人工决定、requirements approval、设计与 M-LOCK、program/semantic steps、服务重启、实现、权威测试、release confirmation 和 history archive。
- [ ] E2E 明确断言 Scout、Warden、Keeper 的 task/session/dispatch 数量均为零，并断言 program result 不能由客户端或 Agent 伪造。
- [ ] 另有公开入口证据覆盖 `bug_fix`、旧路径不能改变新 run、重启恢复和旧 workspace 采用不产生双重权威状态。
- [ ] 发布审计必须使用安装后产品和 public outlet 证据；底层类存在、单元测试通过、最小演示 graph 或测试内手工装配均不构成 cutover 完成。

## E. Louke Dogfood 与 Spec 规模门禁

- [ ] 使用 Louke 自己的 v0.14 spec 和实现工作完整 dogfood 一轮新 `new_feature` workflow，保存从 Story 到 history 的公开证据，并证明过程未 dispatch Scout、Warden、Keeper。pre-cutover v0.13 开发基线在 release tag 前结束；release tag 后不存在旧可执行路径、旧 Runtime fallback 或受控回退开关。
- [ ] 每个 Spec 最多包含 30 条有效 FR+NFR（`Valid=❌` 的历史需求不计数）；恰好 30 条允许，超过时不可 waiver。Louke 推荐一个 Story/Spec 对应一个 release，但硬门禁作用域是单个 Spec，不累计同一 release 的多个 Spec。
- [ ] 30 条上限由 Runtime 在 Sage 初稿/修订持久化后、dispatch Lex 之前执行；超限返回稳定错误 `SPEC_SCOPE_TOO_LARGE`，Lex 不参与是否拆分的决定，且不得执行 anchor、Issue、approval 或 lock 副作用。
- [ ] 超限 run 进入 `needs_story_split` 并合法返回 M-STORY；原 Story/Spec/Acceptance revision 完整保留。Scribe 提出独立价值切片，Human 决定；确认后原 Story 标记为 Split parent，子 Story 记录 `parent_story_id` 并进入后续独立 release/run。
- [ ] installed-wheel E2E 使用含 31 条有效需求的 Spec 证明：Runtime 在 Lex 前拒绝、无下游副作用、回退状态可重启恢复、父子 Story 可追溯、拆分后的子 Story 能独立继续；另验证 30 条通过及 `Valid=❌` 不计数。

## F. Cutover 后旧 workflow CLI 命令缺位合同与 unknown-command 处置

> 与 BS-30 / story.md §0.1 第 11 条（2026-07-17 修订） / research-report §15.17（2026-07-17 修订） 对齐；本节是 v0.14 切换日生效的稳定合同，不得在实现阶段自行放宽。本节取代并废止先前"deprecated no-op 行为合同与 audit 事件合同"（旧 BS-30、旧 §0.1 第 11/13 条、旧 research-report §15.17、旧 cutover-checklist §F 全部不再适用）。

- [ ] v0.14 release cutover 生效后，旧 workflow CLI 命令（包括但不限于 `lk agent ...` 等曾用于推进 workflow 的命令）**不作为公开命令存在**：它们不在 CLI 注册表中注册、不出现在 `--help` / shell completion / 任何文档/UI 命令列表中、不会被 CLI dispatcher 路由到 Runtime / 任何 Agent / 任何 workflow。
- [ ] cutover 后不存在 `cli_legacy_deprecated_noop` 这类专用 audit 事件类型；不存在 deprecated no-op 退出码合同；不存在专门的 exit-0 合同或专用迁移警告合同；唯一适用的是 CLI 自身的普通 unknown/unsupported-command 处置路径。
- [ ] 当 cutover 后用户尝试调用一个不再注册的旧 workflow 命令（无论通过 shell、脚本、CI、文档示例还是 dogfood），该调用只能命中 CLI 的普通 unknown/unsupported-command 行为：CLI 以与其它任何未知/不支持命令一致的方式向用户报告，不抛专用于"已废弃命令"的特殊错误码、不写专用于"已废弃命令"的 audit 事件、不提供任何 deprecated no-op 兼容 fallback、不静默转发到旧 Runtime / 旧 Agent / 旧 workflow、不 mutate 任何 run / project / Git 状态。
- [ ] v0.13 baseline 上的 pre-cutover 开发期间（在 v0.14 release tag 之前），CLI 仍按既有 v0.13 行为提供 workflow 推进命令以便 dogfood 与调试；cutover 由 Runtime 在 release cutover 阶段统一执行，过渡期不出现"新旧入口半切"的中间形态。
- [ ] 运维白名单命令（`lk serve`、`lk upgrade` 等）的行为不受本节约束影响；本节只针对 cutover 后被从公开命令表面移除的旧 workflow 推进命令。
- [ ] installed-wheel E2E 必须双向断言：(a) cutover 后的 CLI 不注册任何旧 workflow 命令，旧命令不在 `--help` / completion / 任何命令列表中可见；(b) 对一次典型旧命令的调用（例如 `lk agent ...`），CLI 走普通 unknown/unsupported-command 路径，不存在专用 deprecated no-op 退出码、不存在专用 audit 事件、不发生状态变更；(c) pre-cutover v0.13 baseline（v0.14 dev 期）允许存在并执行既有 CLI workflow 命令。

## G. Sage 例外 `question` 通道与 `waiting_human` 持久化

> 与 BS-31 / story.md §0.1 第 12 条 / research-report §15.12 对齐；本节是 Sage 例外 `question` 通道的稳定合同，不得在实现阶段自行放宽。

- [ ] Sage 在 M-SPEC 阶段例外使用 `question` 通道向 Human 提问时，Runtime 必须持久化 `waiting_human` 状态；被阻塞需求保持 `Decided=⚠️`。
- [ ] Runtime 不做默认决定、不消耗 review 轮次、不解除 requirements approval 或 M-LOCK 阻塞——`waiting_human` 期间该 run 必须停留在原状态。
- [ ] `lk serve` 重启并重新进入 chat 窗口后，Sage 通过例外 `question` 提出的未决问题必须仍可见；可观察性由 opencode session 恢复机制承载，Runtime 自身的 `waiting_human` 持久化与 gate 阻塞语义不依赖 opencode session 恢复。
- [ ] 只有匹配的 Human 回复落入同一 spec revision 后，Runtime 才恢复该 task 并继续后续 gate 判定；未匹配的回复或跨 revision 的回复不应被 Runtime 自动接受。
- [ ] installed-wheel E2E 必须双向断言：(a) 触发例外 `question` 后不回复，`waiting_human` 状态可读、需求 `Decided=⚠️`、round 计数不变、approval/lock 仍阻塞；(b) 重启 `lk serve` 后重新进入 chat 窗口仍可见 Sage 的提问；(c) 给出匹配的 Human 回复后 task 恢复并继续 gate 判定。

## H. 无 GitHub Backlog Project 与 Runtime Backlog 行为

> 与 BS-32 / story.md §0.1 第 14/19 条 / research-report §15.18/§15.23 对齐；本节是 v0.14 的稳定合同，不得在实现阶段自行放宽。继承 v0.12 FR-1001/FR-1101/FR-1701 已批准行为。

- [ ] v0.14 项目 setup 流程不得创建、复用或检查任何 per-repository GitHub backlog Project。
- [ ] Louke Backlog 维护为 Runtime-native 持久化状态；Park/No-Go 和被阻塞的项目请求使用该 canonical backlog。
- [ ] `backlog_project` 不作为 v0.14 的活动需求元数据。
- [ ] 同一 workspace 最多一个 active 非 hotfix 主 Project；`bug_fix`/hotfix 是唯一并行例外且完全隔离（继承 v0.12 FR-1001 AC-4/AC-5）。
- [ ] 主 Project active 时新 `new_feature` 请求保存/reconcile 到 Backlog，不创建第二个主 run（继承 v0.12 FR-1101 AC-3/AC-4、FR-1701 AC-5）。
- [ ] Web 列出所有 Backlog 条目（Park、No-Go、被阻塞请求），提供考虑启动操作——打开预填预览表单，重新运行验证/就绪/active-project 策略，Human 显式确认后原子创建最多一个新 Project/WorkflowRun。
- [ ] Park/No-Go 条目原始决定/状态/历史保持不可变/可审计，即使后续 run 已创建；不得破坏性删除条目。
- [ ] 重启后 Backlog 条目完整可读、可追溯；物理存储格式/路径由 Architecture 决定，但满足单一权威 store、无 split-brain、无丢失。
- [ ] installed-wheel E2E 必须断言：Park/No-Go 分流后 Backlog 条目可读且重启后不丢失；项目 setup 不触发任何 per-repository GitHub backlog Project 的 create/reuse/check/API 操作；适用的 per-release GitHub Project 真实操作仍可执行；若该操作因认证/权限失败，进入 `waiting_human` 并以相同 idempotency key 在 Human 授权后重试；主 Project active 时新 `new_feature` 进入 Backlog 而不创建第二个主 run；Backlog 条目预览→确认→原子创建流程正确；Park/No-Go 原始决定在后续 run 创建后仍可读。

## I. 无权限探测 Issue/PR

> 与 BS-33 / story.md §0.1 第 15 条 / research-report §15.19 对齐；本节是 v0.14 的稳定合同，不得在实现阶段自行放宽。

- [ ] `gh auth status` 仅用于认证健康检查，不得作为仓库/资源操作权限的证据。
- [ ] 仓库 `viewerPermission` 等粗糙信号仅可作诊断参考，不是未来操作通过的权威凭证。
- [ ] GitHub 远程认证操作（push、Issue/PR API 调用、per-release GitHub Project 操作、release/tag 发布等）因认证/权限失败时，Runtime 持久化该失败操作和可操作错误，将 run 置于 `waiting_human`。本地 commit 不是 GitHub 权限操作，不在本约束范围内。
- [ ] per-release GitHub Project 复用身份优先使用 manifest 记录的不可变 Project node ID；若无，匹配声明的 owner + exact release-scoped project identity/title + repository/release binding。零/多/冲突匹配进入 waiting_human；永不用模糊标题选取。
- [ ] Human 授予/变更授权后，Runtime 以相同 idempotency key 重试同一操作；权限失败不得被跳过、豁免、猜测或转换为 PASS；在真实操作成功前，下游不得推进。
- [ ] 不得产生一次性探测 Issue/PR 的副作用（side-effect smoke test）。
- [ ] installed-wheel E2E 必须断言：(a) 权限不足场景进入 `waiting_human` 且无探测性 Issue/PR；(b) Human 授权后以相同 idempotency key 重试成功；(c) 权限失败不被跳过或转换为 PASS。

## J. Setup 元数据权威推导与冲突仲裁

> 与 BS-34 / story.md §0.1 第 16 条 / research-report §15.20 对齐；本节是 v0.14 的稳定合同，不得在实现阶段自行放宽。

- [ ] 项目 setup 元数据从 Git remote、有效项目元数据、已认证身份和其它权威来源推导候选值；展示每个候选的 provenance。规范化的语义等价候选（如等价 repo URL 形式）可自动接受并记录所有 provenance，无需字节相等。冲突/歧义仍 waiting_human。
- [ ] 当多个权威来源产生冲突值时，Runtime 持久化显式 setup `waiting_human` 状态（含所有候选值及其 provenance），阻止外部修改和 WorkflowRun 创建/下游 setup 推进。
- [ ] Human 选择或提供权威值后，Runtime 持久化决定、actor、候选 provenance、setup revision/digest 和时间戳；以相同 setup revision/attempt 幂等恢复。
- [ ] 重启后保留未解决的冲突或已解决的决定；不得静默覆盖冲突值、不得在无决定时推进 setup。
- [ ] installed-wheel E2E 必须断言：(a) 多 remote/fork 冲突场景进入 `waiting_human` 且无 WorkflowRun 创建；(b) Human 不决定则无法推进 setup；(c) Human 决定后幂等恢复；(d) 重启后冲突/决定状态保留。

## K. 无 v0.13 → v0.14 Louke 状态迁移（finish-then-reinstall 唯一升级路径）

> 与 BS-35 / story.md §0.1 第 17 条 / research-report §15.21 对齐；本节是 v0.14 的稳定合同，不得在实现阶段自行放宽。

- [ ] 升级的唯一支持序列为：(1) v0.13 active release/run 在 v0.13 下正常完成；(2) v0.13 进程/安装被停止并移除；(3) 安装 v0.14；(4) v0.14 独立启动并创建全新 authority run——不导入/映射/恢复旧 authority。
- [ ] v0.14 不导入、不映射、不恢复、不修改、不附加 authority 到 v0.13 的 active run、stage、gate、task、session、evidence、catalog、audit 状态或 WorkflowDefinition。
- [ ] 无双版本状态命名空间、无兼容桥、无迁移向导、无 in-flight 迁移、无混合新旧 authority。
- [ ] 若 v0.13 release/run 未完成，v0.14 不接管该 run；用户用 v0.13 完成或放弃（在 v0.14 外处理）。
- [ ] v0.14 安装后旧 Louke/workflow 不得并发可用；pre-cutover v0.13 CLI 仅为 release cutover 前的开发基线，不是 v0.14 安装后的同步生产兼容面。
- [ ] 对既有 Git 仓库/代码库的 no-new-debt adoption 是**全新 v0.14 项目**；可检查代码/历史，但不得从 v0.13 Louke 状态（`current_stage`、evidence 等）迁移或推断 v0.14 权威 run 状态。
- [ ] installed-wheel E2E 必须断言：(a) 未完成的 v0.13 run 不被 v0.14 接管；(b) v0.14 adoption 不导入 v0.13 state；(c) 完成→移除→重装→新建 完整序列可执行。

## L. Agent 退役清单与表面清理（cutover 后）

> 与 BS-36 / story.md §0.1 第 18 条 / research-report §15.22 对齐；本节是 v0.14 的稳定合同，不得在实现阶段自行放宽。

- [ ] 职责清单覆盖 Scout、Warden 和 Keeper（不仅是 Scout/Warden），三者均从 active 表面排除。
- [ ] cutover 后，active catalog、docs、help、prompts 和路由中不得出现 Scout、Warden 或 Keeper。
- [ ] 不可变的历史/审计 artifact 可保留其名称；不得仅因擦除名称而重写历史 artifact。
- [ ] installed-wheel E2E 必须断言：(a) cutover 后 active 表面无 Scout/Warden/Keeper；(b) 历史/审计 artifact 中保留的名称可读且未被改写。

## M. M-FOUND 分支 reconciliation gate

> 与 BS-37 / story.md §0.1 第 20 条 / research-report §15.24 对齐；本节是 v0.14 的稳定合同，不得在实现阶段自行放宽。Sage B-08/B-09/B-10/B-11 补充。

- [ ] 扫描绑定到成功刷新的 declared remote 的权威 `main` SHA。本地 main 不匹配/分叉是可见阻塞 reconciliation 条件，不静默选择本地 main。
- [ ] 枚举本地 `refs/heads/*` 加上成功刷新的 declared-remote 分支 ref；排除 symbolic/非分支 ref 和绑定的权威 main ref。本地 `refs/heads/main` 和权威 remote main 均排除在普通非 main 分支 merge/delete 候选之外；本地 main 永不被删除或通过分支保留行处理。
- [ ] 本地 main reconciliation 单独展示，绑定 exact local main SHA + 权威 remote main SHA + scan revision，状态为 equal/behind/ahead/diverged（使用 ancestry/merge-base 判定）。
- [ ] `equal`：允许分支扫描继续。`behind`：Web 提供 Human 确认的安全 fast-forward 本地 main 到 remote main；dirty/冲突 worktree 或不确定更新以可操作错误阻塞；操作后 reconcile/rescan。`ahead`：Web 提供 Human 确认的 publish/push 本地 main（仅通过适用权威检查后；无 force push）；auth 失败用 BS-33 相同 key waiting_human/retry；刷新/rescan 必须达到 equal 才能 PASS。`diverged`：Web 可提供 Human 确认的 merge 权威 remote main 到本地 main，然后权威验证和非 force push；merge conflict/check 失败保持 blocked/waiting_human，无 reset/force/delete；Human 也可在外部解决，但 M-FOUND 仅在 refs 变化且权威 rescan 证明 allowed/equal 状态后恢复。
- [ ] 持久化状态、两个 SHA、merge-base、决策、actor、时间戳、操作/证据/idempotency identities；重启安全恢复。任何 SHA 变化使决策 stale。仅 equal 状态可产生 M-FOUND PASS。永不 force-push、reset/discard 独有 commit、或删除任一 main ref。
- [ ] 规范发现 identity = repository + full ref name + head SHA。相同 ref/SHA 的重复发现折叠；本地分支与其配置 upstream 同 SHA 时可显示为一个逻辑行并带两个别名/provenance；SHA 不同时显示为独立分叉行。不同分支名即使同 SHA 仍为独立行（决策/删除作用于名称）。
- [ ] 持久化 source refs/aliases、branch SHA、bound main SHA、merge-base SHA。
- [ ] `fully_merged=true` 当且仅当分支 head 是 bound main head 的祖先。`ahead_count` = `main..branch` 的可达 commit 数；UI 省略 behind 数。
- [ ] Declared-remote 枚举/fetch 必须权威完成：auth/权限失败进入 BS-33 相同 key waiting_human/reconcile/retry；瞬时网络失败持久化为 retryable_external_failure。Stale tracking ref 或部分枚举不得产生 PASS。
- [ ] 绑定到 active WorkflowRun 的分支（含当前/并行 release 或 fix 分支）为 `protected_active_run`。展示并参与扫描/staleness 证据，但 M-FOUND 不得 merge 或 delete 它；其 merge/delete 由该 run 的 M-LOCK/test/release/hotfix gate 独占。
- [ ] 对 ahead protected 分支，Web 禁用/拒绝 merge+delete 复选框，要求 Human 确认非空 retain/protected 理由（绑定 exact heads/revision）。Fully merged protected 分支始终展示，永不自动删除。对 protected 分支尝试选中 merge/delete 被无修改拒绝，在有效 protected-retain 决策存在前不通过。
- [ ] 非 protected unmerged/ahead 分支需要 Human 决策（选中 merge+delete 或非空保留理由）。所有 unmerged 分支决策完成且所有选中 merge+delete 成功前，M-FOUND 保持 waiting_human/non-PASS 且 M-SPEC 不得启动。
- [ ] 选中非 protected 分支由 Runtime 执行 merge into main、验证 ancestry/content 和权威检查、按需 push、仅 merge/push 成功后删除本地/远程分支。永不在验证 merge 前删除。
- [ ] merge conflict、check 失败、push/delete auth 失败或不确定结果持久化并阻塞；远程 auth 失败使用 BS-33 相同 key waiting_human/reconcile/retry。
- [ ] 未选中分支的持久化 Human 理由解决当前扫描而不 merge/delete；这是显式分支保留决策，不是 blanket waiver，仅对 exact 分支 head + main head/check revision 有效。
- [ ] 任何分支/main head 变化、新分支、删除分支或目标/证据变化使受影响扫描/决策 stale 并要求重新扫描/决策后 M-FOUND 才能 PASS。
- [ ] 已 fully merged 分支记录并展示，不自动删除；除非在显式清理操作下选中，删除必须安全且可审计。
- [ ] BS-37 允许的自动化仅为权威扫描、本地 main reconciliation（Human 确认的 behind fast-forward / ahead 验证非 force publish / diverged merge remote-main 到 local-main 后验证非 force push，无 force/reset/delete/discard）、Human-bound retain 决策、非 protected 选中分支的 merge→validate→push→delete。它不创建任意分支/worktree、不推断目标、不执行延迟 hotfix 同步、不替代 owning workflow 的 release/hotfix gate。
- [ ] installed-wheel E2E 必须覆盖：equal/behind/ahead/diverged 本地 main 状态、dirty worktree、merge conflict、auth retry、重启、stale SHA、永不 delete/force/reset main ref、release 和 fix 分支、protected active-run 分支、选中 merge+delete、保留-with-reason、unknown 目标、conflict/failure/retry、head 变化后 stale 决策、重启持久化、分支 reconciliation PASS 前无 M-SPEC。

## 追踪规则

后续规格必须为本清单每个条目建立稳定 requirement/AC 或明确的 release exit condition，并在实现计划中映射到 Issue、代码、测试和发布证据。任何条目若因范围变化被推迟，必须由人类显式批准目标版本与风险，不能在实现阶段自行删除。
