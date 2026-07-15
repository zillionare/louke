# v0.14 Workflow Reflow

## 目标

在 v0.13 已提供可体验 UI 和 Runs 观察面的基础上，重新组织 Louke 的 Story、测试、CI 反馈、人工回退、豁免、版本和分支工作流。Runtime 仍是 workflow 状态与转移的唯一权威；UI 只提交经授权的命令并展示结果，不自行推断或改写状态。

## 用户故事

1. Louke 需要独立的 Story 阶段。进入需求澄清前，Story 阶段应调查竞品和本产品既有 story，必要时询问用户，判断故事是否充分、必要、无冲突，并以 EARS 表达形成可独立作为后续输入的 `story.md`。
2. Story 阶段应给出 Go、Park 或 No-Go 建议，由人类作最终决定；无论结论如何，story 都保留可审计记录，只有 Go 进入后续需求流程。
3. Louke 应明确区分 unit、integration、E2E 和真实环境测试。Integration 必须快速、可在每次 push 后自动运行；E2E 必须与 Story 场景建立可追踪关系，并覆盖按明确量化标准选出的主要 happy path。
4. Maestro 在收到 CI report 后，应根据报告所属 revision、当前 workflow 状态和失败类型决定立即中断、在安全点处理或仅记录，不得让迟到或不相关的 CI 结果改写当前 run。
5. E2E 在 M-MILESTONE-CUT 之前完成；测试报告必须区分 passed、failed、skipped、waived 和 not-run，不得用 waiver 或 skip 冒充通过。
6. 人类可以在 v0.13 Runs UI 上请求把 workflow 拉回到允许的上游阶段，以修复从某一阶段开始未严格执行流程的问题。Runtime 必须验证合法回退点、artifact/revision freshness、受影响的下游状态和审计要求后再执行。
7. 回退不得删除或改写历史证据；被失效的下游 artifact、批准和结果应保留历史记录，并以 superseded/stale 或等价状态与新 revision 区分。
8. 当部分流程检查或测试无法达标时，人类可以在 UI 查看失败证据，并对政策允许的项目提交 waiver。waiver 必须包含 actor、reason、scope、有效期或复查条件及审计事件。
9. requirements human approval、M-LOCK human approval、Runtime CAS/原子性、身份与 secret 安全、artifact digest freshness、Agent 禁止自批/自跳等关键不变量不可 waive。waiver 只能改变是否允许继续的控制决定，不能把原始失败改写为通过。
10. workflow 必须规定何时创建、切换和关闭分支，防止 Agent 在未授权阶段随意切分支；branch、worktree、run、revision 和 task identity 必须可追踪且不串线。
11. workflow 必须规定版本号的提议、批准和写入时点，并自动检查构建物版本、安装后 CLI 版本及 `.louke/project/project.toml` 中声明的一致性。
12. 夜间重构必须使用隔离的新分支或 worktree；成功结果经过规定门禁后才可合入，失败必须留下可诊断记录并安全回滚，不污染活动 workflow。
13. v0.12.1 已明确移交的测试分层和 AC 证据缺口在本版本按新的测试模型处理；不得为了数字闭合而把所有规则机械搬入浏览器 E2E。

## 版本边界

14. 本版本复用 v0.13 的 toolbar/sidebar/tab 和 Runs 观察面，为 rollback、waive 与 CI interruption 增加必要的状态展示和经授权操作入口，但不重新设计整个 UI chrome。
15. 完整 Settings、harness/shell 命令和 End User Docs AI 辅助编辑属于 v0.15；UI i18n 属于 v0.16。
