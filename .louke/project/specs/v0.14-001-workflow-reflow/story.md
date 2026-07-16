# v0.14 Workflow Reflow

## 目标

在 v0.13 已提供可体验 UI 和 Runs 观察面的基础上，重新组织 Louke 的 Story、测试、CI 反馈、人工回退、豁免、版本和分支工作流，并完成从旧 Maestro 驱动流程到程序化 Runtime 的生产切换。Runtime 是 workflow 状态、合法转移和权威副作用的唯一控制者；UI、CLI 与 Agent 只提交经授权的命令或结构化语义结果，不自行推断、改写或跳过状态。安装 v0.14 后，用户应能从受支持的产品入口直接运行并完成新的内置 workflow，不需要 Scout、Warden 或 Keeper Agent，也不需要手工注入 store、调用内部 Python 对象或回退到旧流程。

## 用户故事

1. 作为提出新想法的产品负责人，我希望在需求澄清前由正式的 Story Agent 调查竞品和本产品既有 story，必要时向我追问，并把充分、必要且无已知冲突的内容以 EARS 表达为可独立交接的 `story.md`，以便后续需求工作不从一句含糊描述直接开始。
2. 作为决定是否投入需求工作的产品负责人，我希望 Story Agent 给出有依据的 Go、Park 或 No-Go 建议，但最终决定始终由我作出；无论选择什么，story 和决定都保留记录，只有我确认 Go 才开始需求流程，以便 Agent 建议不会替代产品决策。
3. 作为 Louke 的使用者，我一般只参与 Story 与 Spec 阶段的评审。但偶尔也会参与技术架构设计并评审(Test-Plan, Architecture, Interfaces)。在评审交互期间，可以暂停 Prism 的 Review，以加快评审速度。在这种情况下，Archer 也有需要在每轮交互时，提交当前设计文档的变更，以便可以通过 diff 来了解变更情况。
4. 作为持续提交代码的开发者，我希望 unit、integration、E2E 和真实环境测试具有清晰边界，快速 integration 在每次 push 后自动反馈，而 E2E 能追溯到 Story 场景并按明确标准覆盖主要 happy path，以便我能快速定位失败层级且产品旅程有真实证据。
5. 作为正在推进 workflow 的使用者，我希望 CI report 只有在匹配当前 revision 和 run 状态时才影响流程；系统应告诉我是立即中断、在安全点处理还是仅记录，以便迟到或无关的 CI 结果不会打断或改写当前工作。
6. 作为批准里程碑的发布维护者，我希望适用的 E2E 在 M-MILESTONE-CUT 前完成，并清楚看到 passed、failed、skipped、waived 和 not-run 的区别，以便 waiver 或 skip 不会伪装成产品已经通过。
7. 作为发现流程从某阶段开始执行不严格的使用者，我希望能在 Runs UI 请求回到允许的上游阶段，并在执行前看到合法回退点、artifact/revision 新鲜度和受影响的下游结果，以便修复流程问题而不制造未知状态。
8. 作为审计回退结果的使用者，我希望旧 artifact、批准和证据在回退后仍然可读，并明确标记为 superseded、stale 或等价状态，与新 revision 区分，以便历史不会因返工被删除或改写。
9. 作为面对外部不稳定检查或政策允许例外的使用者，我希望在 UI 看到原始失败证据，并能提交包含身份、理由、范围、有效期或复查条件的 waiver，以便继续执行的风险决定完整、可审计且可复查。
10. 作为依赖 Louke 安全边界的使用者，我希望 requirements approval、M-LOCK、并发原子性、身份和 secret 安全、artifact freshness 以及 Agent 禁止自批自跳等关键不变量永远不能被 waive，并且 waiver 不会把原始失败改写为通过，以便例外机制不能破坏流程可信性。
11. 作为同时处理多个任务和分支的贡献者，我希望系统在正确时点创建、切换和关闭 branch/worktree，并让我能从 run、revision 和 task 追踪到实际工作位置，以便 Agent 不会未经授权切分支或把不同任务的代码和证据串线。
12. 作为准备发布版本的维护者，我希望在明确时点看到版本号被提议、批准和写入，并自动确认构建物、安装后 CLI 与项目声明一致，以便发布不会携带互相矛盾的版本身份。
13. 作为让 Louke 执行夜间重构的维护者，我希望重构在隔离分支或 worktree 中进行，只有通过规定门禁的结果才能合入；失败时保留可诊断记录并安全清理，以便无人值守工作不会污染活动 workflow。
14. 作为接手 v0.12.1 测试与 AC 证据缺口的维护者，我希望 v0.14 按测试层级和用户风险补齐真实证据，而不是为了覆盖数字把所有规则机械搬入浏览器 E2E，以便测试既可信又可持续运行。
15. 作为安装 v0.14 的使用者，我希望在 Agent 列表、模型绑定和 workflow 进度中看到 Story 成为正式入口，并且不再看到或等待 Scout、Warden、Keeper，以便项目初始化、前置检查和质量门不再消耗三个只包装工具的 Agent 会话。
16. 作为第一次使用 Louke 的使用者，我希望安装 v0.14 后只需在现有或空白 Git workspace 启动 `lk serve`，即可完成 setup、创建项目并开始新 workflow，而不必再运行隐藏的初始化步骤、手写运行状态或了解旧 Maestro 流程。
17. 作为同时使用 Web、CLI 和 Chat 的使用者，我希望无论从哪个受支持入口查看或操作项目，都看到同一个 project、run、当前步骤、合法动作和证据，以便不会因入口不同进入互不一致的工作流；任一入口失败时都必须明确报错，不能静默切到旧流程。
18. 作为推进项目的使用者，我希望确定性检查和副作用在轮到它们时自动执行，只有需要理解、判断、审查或创造的步骤才等待对应 Agent；项目详情应说明当前工作由程序还是 Agent 承担、为什么停下以及下一步能做什么，以便我不必手工调度流程或猜测后台正在发生什么。
19. 作为依赖 Louke 门禁的使用者，我希望 Web、CLI 或 Agent 的一句 `done`、`pass`、测试已通过或批准声明都不能伪造程序结果、权威证据或流程状态；只有当前 revision 上真实执行且可追溯的检查、测试和人类决定才能推进 workflow，以便新的自动流程仍然可信。
20. 作为交付功能或修复缺陷的使用者，我希望 v0.14 内置的 `new_feature` 和符合 source-contract 条件的 `bug_fix` 都能从公开入口运行到发布确认和历史归档，而不是只创建一个无法完成的演示 run，以便安装后的新流程可以直接承担真实项目工作。
21. 作为在长时间 workflow 中工作的使用者，我希望关闭浏览器、重启 Louke 或遇到可恢复的 Agent/程序失败后，重新进入项目仍能看到准确的 run、gate、task、artifact、evidence、失败原因和恢复动作，并从原位置继续，以便进度不依赖某个会话或进程仍然存活。
22. 作为升级既有 Louke workspace 的使用者，我希望先预览采用 v0.14 新流程会迁移什么、保留什么和拒绝推断什么，再由我确认；迁移或恢复失败时，旧证据保持可读且不会出现新旧流程同时声称拥有同一项目状态，以便升级不会损坏历史或制造双重权威。
23. 作为 Louke 项目维护者，我希望能审阅每项内置 workflow 和 Agent 职责当前由程序还是语义 Agent 承担、迁移理由和实际执行目标，并在存在遗漏、未分类职责、纯工具包装 Agent 或声明与实际 dispatch 不一致时阻止创建 workflow，以便注销 Scout、Warden、Keeper 后没有隐藏职责或新的包装角色重新出现。
24. 作为负责切换 v0.14 的发布维护者，我希望新 Runtime 是安装后的明确默认路径，失败时不会自动 fallback；在限定切换期内如确需退回旧 runtime，我只能通过显式、可审计且避免新旧流程双写的受控操作完成，以便既能安全止损，又不会掩盖新流程故障或污染项目状态。
25. 作为批准 v0.14 发布的维护者，我希望从当前构建实际安装产品，在隔离 workspace 中通过公开入口看到一条包含 setup、Story、人工决定、程序与 Agent 步骤、重启恢复、权威测试、发布和归档的完整旅程，并确认全程没有 Scout、Warden、Keeper task/session；在删除旧执行路径前，Louke 自己的 v0.14 开发也应完整使用并证明这条新流程，以便发布结论来自真实产品和 dogfood，而不是底层类、演示图或测试专用装配。
26. 作为阅读安装与工作流说明的使用者，我希望 README、workflow 文档、Maestro 行为、Agent/模型列表和产品 UI 对 v0.14 默认流程给出一致描述，以便不会按照过期文档重新启动已注销 Agent 或绕过新 Runtime。

[`cutover-checklist.md`](cutover-checklist.md) 将上述用户故事派生为生产切换所需的架构、迁移、文档同步、installed-wheel E2E、受控回退和 dogfood 交付条件。后续 M-SPEC、M-ARCH、实现计划与发布验收必须从对应故事建立可追踪关系；该清单不得引入无法追溯到本 story 的独立范围，也不得遗漏本 story 已承诺的结果。

## 版本边界

1. 本版本复用 v0.13 的 toolbar/sidebar/tab 和 Runs 观察面，为 rollback、waive 与 CI interruption 增加必要的状态展示和经授权操作入口，但不重新设计整个 UI chrome。
2. v0.14 不保留 Scout、Warden、Keeper 作为隐藏、可选或 fallback Agent；兼容旧命令不等于保留旧 Agent，且不得形成第二套状态权威。
3. v0.14 的 cutover 包含新安装和旧 workspace 的显式采用边界，但不把无法证明状态的 legacy `current_stage` 伪装成可恢复的新 run；旧证据作为只读历史保留。
4. 完整 Settings、harness/shell 命令和 End User Docs AI 辅助编辑属于 v0.15；UI i18n 属于 v0.16。
