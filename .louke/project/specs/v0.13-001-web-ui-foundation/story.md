# v0.13 Web UI Foundation

## 目标

尽早提供一个可持续使用的 Louke Web 主界面，使用户可以通过真实 UI 体验已有的 Chat、设计文档、最终用户文档、Wiki 和 Runs 能力，并用浏览器端到端旅程发现产品与 workflow 问题。该版本建立稳定的 UI chrome 和只读观察面，不提前实现 workflow reflow，也不纳入高风险的 shell 命令、AI 写回和模型等级配置。

## 用户故事

1. 应用主界面由三部分组成：垂直 toolbar、支持多级菜单的 sidebar，以及承载多个 tab 的 main panel；整体交互类似 VS Code 的 activity bar、side panel 和 editor tabs。
2. toolbar 只显示 icon，鼠标悬停时显示提示文字。顶部从上到下依次为 Chat、Dev Docs、End User Docs、Wiki、Runs；底部从下到上依次为 Gears、Accounts。
3. 当用户切换 toolbar 项时，sidebar 切换到对应导航，main panel 打开或激活对应 tab；已打开的 Chat、Settings、Docs、Wiki 和 Runs tab 可以共存，不因切换 toolbar 而被关闭。
4. 点击 Gears 后，main panel 打开或激活 Settings tab。该 tab 采用左侧菜单、右侧详情的两栏结构；本版本只建立设置框架和可扩展入口，版本更新、服务器配置和 S/A/B 模型绑定在 v0.15 实现。
5. 点击 Accounts 后弹出账号菜单，本版本至少提供 logout，并保持现有认证边界。

## Chat 可体验闭环

6. 点击 Chat 后，sidebar 显示 Agent 图标与名称列表；Maestro 位于最上方并默认选中。
7. main panel 打开或激活 Chat tab。上方显示当前 Agent 的 session transcript，并支持 streaming；底部提供普通对话输入框。
8. 用户在 sidebar 选择不同 Agent 时，Chat tab 切换到该 Agent 对应的会话上下文，不混淆不同 Agent 的 transcript。
9. 本版本只支持普通对话输入；harness `/` 命令和操作系统 `!` 命令在 v0.15 设计和实现。

## 文档与 Wiki

10. 点击 Dev Docs 后，sidebar 以 `.louke/project/specs` 下的 spec 目录为一级菜单，初始折叠并记忆展开状态；展开后显示目录中的 Markdown 文档。
11. Dev Docs 的文档发现与渲染复用 v0.11-001 FR-0801；编辑器/实时预览分栏复用 v0.9-001 FR-0200；FR/NFR/Story 交叉引用跳转复用 v0.9-001 FR-0700。Dev Docs 由 Agent 生成，不提供 AI 辅助编辑。
12. 点击 End User Docs 后，sidebar 显示面向最终用户的 Markdown 文档树，main panel 支持展示、编辑和实时预览；基础能力复用 v0.11-001 FR-0801 与 v0.9-001 FR-0200。AI 辅助编辑在 v0.15 实现。
13. 点击 Wiki 后，sidebar 显示 Wiki 导航树，main panel 打开或激活 Wiki tab，并渲染所选 Markdown 页面。
14. Wiki 的首页、story/spec/test-plan/architecture/interfaces 汇总、技术决定、FAQ 和项目信息结构复用 v0.11-001 FR-0301。

## Runs 观察面

15. 点击 Runs 后，sidebar 显示当前项目、历史项目及其 run，沿用 v0.12-001 FR-1001 的 Projects 导航；main panel 显示所选 run 的 workflow graph。
16. workflow graph 的每个 stage 节点以状态徽标、颜色或等价图形标注 stage-results，包括 review verdict、gate pass/fail 和 author result，不直接以原始 JSON 作为主要界面。
17. 点击 stage 节点后，可以只读查看 artifact 的 digest、verdict、required reviewer 和 review 结论；stage-results 不提供编辑入口。该展示复用 v0.12-001 FR-1201、FR-1901 和 FR-2201。
18. UI 对未知或后续版本新增的 stage、status 和 result kind 采用可读的通用降级展示，不因 v0.14 workflow reflow 增加状态而崩溃。

## 版本边界

19. 本版本必须形成至少一条浏览器产品主旅程，覆盖启动 Web UI、切换 toolbar、打开一个文档、进入一个 run 并查看 stage artifact，以便用户尽早体验并为 v0.14 reflow 提供反馈。
20. 本版本不实现：workflow 回退、waive、CI report 中断语义、夜间重构分支；完整 Settings 功能；harness `/` 与 shell `!` 命令；End User Docs AI 辅助编辑；UI i18n。

