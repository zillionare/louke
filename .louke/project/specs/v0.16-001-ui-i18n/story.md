# v0.16 Web UI Internationalization

## 目标与范围

1. 本版本只解决 v0.13—v0.15 Web UI 的 i18n 框架、UI 字符串外置、语言选择、持久化、回退和运行时切换。
2. `louke/agents/*.md` 提示词统一使用英文属于内容标准，可由独立 lint/check 保证，但提示词翻译动作不属于本 UI i18n spec。
3. 与 Agent 的会话内容、用户文档正文、Dev Docs、Wiki Markdown、CI report、测试结果、后端错误和 CLI 输出不翻译；UI 对这些内容原样展示。

## 用户故事

4. toolbar tooltip、sidebar 菜单、tab 标签、Settings、对话框、操作按钮、错误提示和空状态等所有面向用户的 UI chrome 字符串，以稳定 message id 从代码外置到 i18n catalog。
5. 至少提供 `en` 基准 locale 与 `zh-CN` locale；缺失翻译回退到 `en`，不得抛错或显示空白。
6. 用户可以在 Gears → Settings 中选择语言；选择结果持久化，并在 reload、重新登录或重新打开既有 tab 后保持。
7. 切换语言后，toolbar、sidebar、main panel 和各已打开 tab 的 UI 文案即时生效，无需整页刷新或只需轻量刷新。
8. i18n 框架不得改变或破坏以下既有合同：
   - v0.13 的 toolbar/sidebar/tab、Chat、Dev Docs、End User Docs、Wiki 和 Runs；
   - v0.14 的 rollback、waive、CI interruption 状态与操作；
   - v0.15 的完整 Settings、Chat 命令通道和 End User Docs AI 辅助编辑；
   - v0.11-001 FR-0801、FR-0301，v0.9-001 FR-0200，以及 v0.12-001 FR-1201/FR-1901/FR-2201。
9. 用户、Agent 和工具链内容天然允许多语言，但不受 catalog 约束；i18n 只覆盖 UI chrome，不触碰内容正文或后端返回文本。

## 可测试性

10. 每个 UI 字符串具有稳定 message id；关键路径至少验证 toolbar tooltip、sidebar、Settings、对话框和操作结果在 `en`/`zh-CN` 下正确显示。
11. 自动测试验证缺失翻译安全回退、locale 持久化、运行时切换和已打开 tab 更新，并确认后端/用户内容没有被错误翻译。
