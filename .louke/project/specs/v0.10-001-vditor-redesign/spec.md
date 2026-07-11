# v0.10-001 — Vditor WYSIWYG 编辑器与界面重构

## 目标

用 Vditor 替代 textarea+preview 双栏模式，实现 Typora 风格的即时渲染编辑。同时重构页面布局，支持多屏分栏、折叠侧边栏、精简工具栏。

## 功能需求

### FR-0100 Vditor 即时渲染编辑器
用 Vditor `ir` 模式替换 textarea，markdown 输入即时渲染为富文本。移除右侧 preview 面板。

### FR-0200 文件选择器
编辑器顶部左侧为文件下拉选择框，列出当前 spec 下的所有文档（spec、acceptance、story 等）。切换文件即加载到当前 pane。

### FR-0300 精简工具栏
编辑器顶部右侧为图标工具栏，依次为：
- 下一处 discussion（跳转到下一个 `>>>` 块）
- 折叠所有讨论
- 只显示未决讨论（隐藏含 `[resolved]` 标记的讨论）
- 分屏（新增一列 pane，最多 4 列）
- Save
- Reload

中间显示最后保存时间（hh:mm:ss）。

### FR-0400 多屏分栏
通过分屏按钮新增竖分 pane，最多 4 列。每个 pane 独立加载不同文档，有独立的文件选择器和工具栏。新增 pane 初始为空白。

### FR-0500 折叠侧边栏
sidebar 支持折叠/展开。折叠后变为窄条，点击展开恢复。

### FR-0600 清理页面冗余
移除页面顶部的 eyebrow 标题、h1 标题、lede 描述文本、Last modified 信息。将空间留给文档内容。

### FR-0700 表格样式
- 表头与 body 样式不同（表头加粗、有底色、有下边框）
- 不显示竖表格线
- body 单元格无背景色

### FR-0800 未决讨论过滤
点击「只显示未决讨论」按钮后，含 `[resolved]` 标记的 discussion 块被隐藏。再次点击恢复显示。

## 非功能需求

### NFR-0100 性能
Vditor CDN 加载不影响首屏；CDN 失败时 fallback 到 textarea。

### NFR-0200 向后兼容
服务端 API 不变；文档格式不变。
