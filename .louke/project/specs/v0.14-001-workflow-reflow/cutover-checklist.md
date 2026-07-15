# v0.14 Programmatic Workflow Cutover Checklist

## 用途

本文保存 v0.14 从旧 Maestro 驱动流程切换到程序化 Runtime 所必需、但不宜全部写成用户故事的架构与交付约束。它是 `story.md` 的规范性配套输入；后续 `spec.md`、`acceptance.md`、`architecture.md`、`interfaces.md`、`test-plan.md`、Issue 拆分和发布审计必须逐项建立追踪，不得静默删除、降级为建议或仅以单元测试替代产品证据。

## A. Responsibility inventory 与 Agent 注销

- [ ] 建立真实、版本化、可审阅且零 `unclassified` 的 built-in responsibility inventory，完整覆盖内置 workflow definitions、Agent prompts/tool contracts、registered handlers 和实际 dispatch。
- [ ] inventory 中每项职责具有稳定 identity、来源、`program`/`semantic` 分类、分类理由、目标 handler/task 和迁移状态；原 mixed 职责在 dispatch 前拆除程序控制/权威副作用与语义输入/输出。
- [ ] catalog build、workflow 创建和 task dispatch 均拒绝缺项、分类不一致、纯工具包装 Agent、缺失 handler/prompt contract 或 semantic task 承担权威副作用。
- [ ] Scout、Warden、Keeper 从新 workflow dispatch、内置 Agent catalog、Chat Agent 列表和 model bindings 中正式注销；新 run 不得创建这三个角色的 task、session 或隐式 fallback。
- [ ] Scout 的语义残余归 Story，Warden 的 story 语义残余归 Story/Sage/Lex，Keeper 的语义审查归 Prism；其余确定性职责映射到明确的 program handler。

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

## 追踪规则

后续规格必须为本清单每个条目建立稳定 requirement/AC 或明确的 release exit condition，并在实现计划中映射到 Issue、代码、测试和发布证据。任何条目若因范围变化被推迟，必须由人类显式批准目标版本与风险，不能在实现阶段自行删除。
