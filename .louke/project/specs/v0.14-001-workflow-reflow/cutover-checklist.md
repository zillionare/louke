# v0.14 Programmatic Workflow Cutover Checklist

## 用途

本文保存 v0.14 从旧 Maestro 驱动流程切换到程序化 Runtime 所必需、但不宜全部写成用户故事的架构与交付约束。它是 `story.md` 的规范性配套输入；后续 `spec.md`、`acceptance.md`、`architecture.md`、`interfaces.md`、`test-plan.md`、Issue 拆分和发布审计必须逐项建立追踪，不得静默删除、降级为建议或仅以单元测试替代产品证据。

## A. Responsibility inventory 与 Agent 注销

- [ ] 建立真实、版本化、可审阅且零 `unclassified` 的 built-in responsibility inventory，完整覆盖内置 workflow definitions、Agent prompts/tool contracts、registered handlers 和实际 dispatch。
- [ ] inventory 中每项职责具有稳定 identity、来源、`program`/`semantic` 分类、分类理由、目标 handler/task 和迁移状态；原 mixed 职责在 dispatch 前拆除程序控制/权威副作用与语义输入/输出。
- [ ] catalog build、workflow 创建和 task dispatch 均拒绝缺项、分类不一致、纯工具包装 Agent、缺失 handler/prompt contract 或 semantic task 承担权威副作用。
- [ ] Scout、Warden、Keeper 从新 workflow dispatch、内置 Agent catalog、Chat Agent 列表和 model bindings 中正式注销；新 run 不得创建这三个角色的 task、session 或隐式 fallback。
- [ ] Scout 的语义残余归 Scribe，Warden 的 story 语义残余归 Scribe/Sage/Lex，Keeper 的语义审查归 Prism；其余确定性职责映射到明确的 program handler。

## B. 唯一生产装配与自动 Driver

- [ ] 建立唯一 production composition root，共享持久化 Store、版本化 Catalog、Handlers、Capabilities、Orchestrator、Gate service、OpenCode adapter 和 program executor；不得依赖测试夹具注入共享 store。
- [ ] 接入自动 workflow driver：进入 program step 时自动运行注册 handler 并验证真实结果；进入 semantic step 时才创建受控 Agent task；进入 human gate 时持久停止并等待匹配当前 revision/digest 的人类决定。
- [ ] Web、CLI 或 Agent 不得任意提交 program result、`done`、`pass`、目标 stage 或伪造的权威证据来推进 run；只接受对应 handler/adapter 的真实结果。
- [ ] 用完整、可完成的 `new_feature` 和 `bug_fix` definitions 替换生产最小演示图，并覆盖 Story、requirements/design approvals、实现、权威测试、release close 和 history。
- [ ] `lk serve`、Web 项目创建、Chat 和默认 Maestro 入口全部进入同一条新 Runtime；旧 `maestro advance` 与旧 M-FOUND 路径不能写入或推进 v0.14 run。
- [ ] 服务或进程重启后，run、gate、task、step attempt、artifact/evidence 和 event 能从持久化状态准确恢复；不依赖旧 Agent 会话保存隐式进度。

## C. 文档、产品面与兼容边界

- [ ] 同步更新 Maestro prompt、README、`docs/workflow.md`、Agent 列表、模型绑定说明、Chat 列表和用户操作文档；不得继续把 Scout/Warden/Keeper 或旧 Maestro pipeline 描述为 v0.14 默认流程。
- [ ] 如需保留 Scout/Warden/Keeper 旧 CLI 名称，只能作为明确 deprecated 的 program adapter，调用与 Runtime 相同的 handler；不得保留 Agent prompt、Agent session 或第二套状态权威。
- [ ] 旧 workspace 通过显式 preview/confirm 采用；无法证明的新 Runtime 状态不得由 legacy `current_stage` 猜测生成，旧证据只读保留。

## D. Installed-wheel E2E 与切换证据

- [ ] 从当前 checkout 构建并安装 v0.14 wheel，在隔离、干净 workspace 中仅通过公开 `lk serve`、Web/CLI、真实持久化 store 和声明的 external adapter 完成至少一条完整 `new_feature` 产品旅程。
- [ ] 该旅程至少覆盖 setup、Story、Go 人工决定、requirements approval、设计与 M-LOCK、program/semantic steps、服务重启、实现、权威测试、release confirmation 和 history archive。
- [ ] E2E 明确断言 Scout、Warden、Keeper 的 task/session/dispatch 数量均为零，并断言 program result 不能由客户端或 Agent 伪造。
- [ ] 另有公开入口证据覆盖 `bug_fix`、旧路径不能改变新 run、重启恢复和旧 workspace 采用不产生双重权威状态。
- [ ] 发布审计必须使用安装后产品和 public outlet 证据；底层类存在、单元测试通过、最小演示 graph 或测试内手工装配均不构成 cutover 完成。

## E. 受控回退与 Louke Dogfood

- [ ] v0.14 切换期保留显式、可审计、默认不触发的受控回退开关。回退只改变入口选择，不得让旧路径与新 Runtime 同时写入同一个 run/project，也不得在新路径失败时静默触发。
- [ ] 回退开关记录 actor、reason、scope、目标 runtime、开始/结束时间和受影响 run；切回新 Runtime 前执行 readiness、schema、版本和单一权威检查。
- [ ] 使用 Louke 自己的 v0.14 spec 和实现工作完整 dogfood 一轮新 `new_feature` workflow，保存从 Story 到 history 的公开证据，并证明过程未 dispatch Scout、Warden、Keeper。
- [ ] 只有 installed-wheel E2E 与 Louke v0.14 dogfood 均通过、阻塞缺陷闭合、生产文档完成切换后，才允许删除旧可执行路径和受控回退开关。
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

## 追踪规则

后续规格必须为本清单每个条目建立稳定 requirement/AC 或明确的 release exit condition，并在实现计划中映射到 Issue、代码、测试和发布证据。任何条目若因范围变化被推迟，必须由人类显式批准目标版本与风险，不能在实现阶段自行删除。
