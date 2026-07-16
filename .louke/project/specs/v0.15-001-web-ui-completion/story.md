# v0.15 Web UI Completion

## 目标

在 v0.13 UI foundation 和 v0.14 workflow reflow 稳定后，完成需要独立安全设计或新产品语义的 Web UI 能力：完整 Settings、Chat 命令通道以及 End User Docs AI 辅助编辑。该版本不改变 v0.14 已锁定的 workflow 权威和审计边界。

## Settings

1. Gears → Settings 的左侧菜单至少包含版本更新、服务器设置和模型绑定；右侧显示所选设置项的详情、当前值、校验结果和保存结果。
2. 服务器设置允许配置监听地址和端口，并明确哪些变更需要重启；无效地址、端口冲突或不安全的暴露方式必须给出可操作错误，不得静默采用。
3. 模型绑定允许定义 S、A、B 级模型候选。Agent 获得符合其等级要求的模型选择集合，默认自动选择第一个可用模型，用户可以选择其他符合条件的模型。
4. 模型绑定修改应遵守 v0.12-001 的 binding snapshot 和审计合同：进行中的 task 不被追溯修改，新 task 使用新绑定，用户可以查看实际解析结果。
5. 版本更新界面应展示当前版本、可更新版本、兼容性和更新结果，并遵守 v0.14 定义的版本一致性检查，不绕过项目固定 runtime 或安全确认。

## Dev Docs 多文档工作区

6. Dev Docs 保留 v0.13 的编辑器与实时预览能力，并支持在同一个工作区打开两个或更多独立文档 pane；每个 pane 可以独立选择、对照、编辑、重载和关闭文档。
7. 多文档 pane 必须保留 inline-discussion 的显示/隐藏、下一个 discussion、下一个 unresolved 和显式保存能力；保存仍遵守 v0.13 的 story/spec/acceptance 可写白名单，不得自动写回只读 Dev Docs。

## Chat 命令通道

8. Chat 输入框支持普通对话、harness `/` 命令和操作系统 `!` 命令，并在提交前后明确显示当前输入类型、目标 Agent/session 和执行状态。
9. `/` 命令只透传给当前项目允许的 harness，并保留 session、actor、cwd、revision 和结果审计；它不能绕过 Runtime gate 或直接伪造 workflow 状态。
10. `!` 命令必须在 M-ARCH 明确权限、工作目录、超时、输出截断、secret redaction、取消、审计和危险命令策略后才能启用；默认不得把任意浏览器输入直接交给无约束 shell。
11. streaming transcript 应区分用户消息、Agent 回复、harness 命令、shell 命令、stdout/stderr、退出状态和取消结果，并保持不同 Agent/session 之间的隔离。

## End User Docs AI 辅助编辑

12. End User Docs 保留 v0.13 的 Markdown 展示、编辑和实时预览，并增加作用域限定在当前文档的 AI 辅助编辑。
13. 用户可以对选中文本请求改写、扩写或润色，也可以对全文请求一致性检查；在写回前必须展示建议或 diff，并由用户明确接受。
14. AI 辅助编辑不得作用于未选中的其他文档，不得修改 Dev Docs、Wiki、workflow artifact 或 stage-results；失败或取消不得留下部分写入。
15. 文档发现与渲染继续复用 v0.11-001 FR-0801，双栏编辑器/预览继续复用 v0.9-001 FR-0200；本版本只增加 AI 建议与受控写回能力。

## 完成性

16. v0.13 各 toolbar 入口在本版本完成一致的 loading、empty、error、permission-denied 和 reconnect 状态，并保持 tab 与 sidebar 状态可恢复。
17. 浏览器 E2E 至少覆盖 Settings 保存、Chat 命令类型隔离和 End User Docs AI 建议确认；workflow rollback/waive 的产品旅程归属 v0.14。
18. UI 字符串外置、多语言 catalog 和运行时 locale 切换属于 v0.16，本版本不得以临时翻译方案替代。
