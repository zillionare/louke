# v0.9-001 - Web UI 精修与协作增强 - Acceptance Criteria

- **Spec ID**: v0.9-001-web-ui-refinement
- **创建日期**: 2026-07-09

> 验收标准集中处。`spec.md` 只保留 FR / NFR 的需求描述与元数据；这里定义可观察、可断言的通过条件。
> **编号约定**：每个 `### AC-N` 在机械追踪时规范化为 `AC-FRXXXX-NN`。

## FR-0100: sidebar Logout 按钮尺寸缩小

### AC-1
Canonical ID: `AC-FR0100-01`
- sidebar 中 Logout 按钮的渲染高度 <= 主导航链接行高。
- Logout 按钮不使用实心填充背景（non-filled），视觉重量低于导航链接。

### AC-2
Canonical ID: `AC-FR0100-02`
- Logout 按钮可点击区域 min-height >= 32px。
- hover 时有背景反馈但不使用 `--accent` 实心色。

## FR-0200: 编辑器与实时预览同步滚动

### AC-1
Canonical ID: `AC-FR0200-01`
- 在编辑器中滚动到文档中段时，预览区自动滚动到对应的渲染段落。
- 两个 pane 的滚动位置在视觉上对齐（段落级，不要求像素级）。

### AC-2
Canonical ID: `AC-FR0200-02`
- 在预览区中滚动时，编辑器反向同步滚动。
- 用户最后主动滚动的 pane 为"主控方"，另一个 pane 跟随。

### AC-3
Canonical ID: `AC-FR0200-03`
- 程序化触发的滚动（如 autosave 后光标恢复）不触发反向同步，避免循环抖动。

## FR-0300: Focus Content / Focus Discussion toggle 按钮

### AC-1
Canonical ID: `AC-FR0300-01`
- Focus Content 和 Focus Discussion 合并为 toggle 按钮组，工具栏中只占一个按钮位（或一个 toggle 组）。
- 默认状态为均衡双栏视图。

### AC-2
Canonical ID: `AC-FR0300-02`
- 点击 toggle 切换到 Content 聚焦模式；再次点击切换到 Discussion 聚焦模式（或回到均衡，取决于设计决策）。
- 当前激活的模式有明确的视觉指示（如 active 高亮）。

### AC-3
Canonical ID: `AC-FR0300-03`
- Collapse Discussion 按钮保留为独立控件，不受 toggle 影响。

## FR-0400: 5 秒自动存盘

### AC-1
Canonical ID: `AC-FR0400-01`
- 编辑器内容变更后，5 秒内无进一步输入则自动触发保存请求。
- 保存请求与手动 Save 走同一 API 端点。

### AC-2
Canonical ID: `AC-FR0400-02`
- 自动保存时 UI 显示轻量指示（如 "已自动保存" 文案），不弹模态、不抢焦点。
- 保存完成后指示消失或转为静态状态。

### AC-3
Canonical ID: `AC-FR0400-03`
- 用户在 autosave timer 触发前手动 Save 时，取消未触发的 timer，不产生重复保存。

## FR-0500: 写入冲突检测

### AC-1
Canonical ID: `AC-FR0500-01`
- 保存请求携带文件版本标识（mtime 或 content hash）。
- 服务端在文件已被他人修改时（版本标识不匹配）返回 HTTP 409 Conflict，不执行写入。

### AC-2
Canonical ID: `AC-FR0500-02`
- 客户端收到 409 后不覆盖本地编辑内容。
- UI 显示冲突提示，提供"查看远端版本"和"强制覆盖"选项。

### AC-3
Canonical ID: `AC-FR0500-03`
- "查看远端版本"将远端内容加载到预览区（只读），用户可对比后决定合并或放弃。
- "强制覆盖"跳过版本检查直接写入。

### AC-4
Canonical ID: `AC-FR0500-04`
- autosave（FR-0400）遇到 409 时静默转入冲突提示状态，不自动重试。

## FR-0600: inline-discussion 缩进线样式调整

### AC-1
Canonical ID: `AC-FR0600-01`
- inline-discussion 嵌套缩进竖线的 border-left-width 为 v0.8 值的 50%。
- 嵌套 4 层时缩进线仍可辨认，视觉噪声显著低于 v0.8。

### AC-2
Canonical ID: `AC-FR0600-02`
- 缩进线颜色透明度在 v0.8 基础上降低 10%（如 0.12 -> 0.108 或等效）。

## FR-0700: FR/NFR/Story 交叉引用可点击跳转

### AC-1
Canonical ID: `AC-FR0700-01`
- 预览区中 `FR-XXXX`、`NFR-XXXX` 文本渲染为可点击链接。
- `<prefix>-FR-XXXX`（如 `001-FR-210`）也被识别并渲染为链接。

### AC-2
Canonical ID: `AC-FR0700-02`
- 点击同一 spec 内的 FR 引用时，页面滚动到对应 `<a id="fr-XXXX">` anchor 位置。
- anchor 不存在时不报错，链接样式可区分（如灰色或删除线）。

### AC-3
Canonical ID: `AC-FR0700-03`
- 点击跨 spec 引用（`001-FR-210` -> spec `001`）时，加载对应 spec 文档并定位 anchor。

### AC-4
Canonical ID: `AC-FR0700-04`
- 跳转后用户可通过浏览器后退（history.back）或自定义 back 按钮返回跳转前的位置。

### AC-5
Canonical ID: `AC-FR0700-05`
- 链接样式与正文区分但不喧宾夺主（虚线下划线或浅色链接色）。

## FR-0800: valid/testable/decided 状态可点击 toggle

### AC-1
Canonical ID: `AC-FR0800-01`
- 讨论卡片上的 valid / testable / decided 标记渲染为可点击 toggle 按钮。
- 点击切换 on/off 状态，UI 立即更新。

### AC-2
Canonical ID: `AC-FR0800-02`
- 点击后通过 API 将变更写回 Markdown 源文件的 inline-discussion 标记行。
- 写回后 inline-discussion 格式完整（`>>>` / `<<<` / speaker tag 结构不破坏）。

### AC-3
Canonical ID: `AC-FR0800-03`
- 写回失败时（网络错误或 409 冲突）UI 回滚到点击前状态并提示错误。

### AC-4
Canonical ID: `AC-FR0800-04`
- 文件已被他人修改时，status toggle 写入返回 409，按 FR-0500 流程处理冲突。

## NFR-0100: 性能

### AC-1
Canonical ID: `AC-NFR0100-01`
- 同步滚动（FR-0200）在 5000 字文档下不产生可感知卡顿（帧时间 < 16ms）。
- autosave（FR-0400）不阻塞 UI 主线程。
- 交叉引用渲染（FR-0700）在 5000 字文档下首屏渲染延迟 < 200ms。

## NFR-0200: 向后兼容

### AC-1
Canonical ID: `AC-NFR0200-01`
- v0.8 的编辑、保存、讨论、模型绑定功能在 v0.9 改动后仍可正常使用。
- 文件格式不变（Markdown + inline-discussion 语法不变）。
