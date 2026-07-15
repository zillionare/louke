---
locked: true
locked-at: 2026-07-15T13:51:46Z
locked-by: lk agent sage record-lock
---
# Web UI Foundation — Spec

- **Spec ID**：`v0.13-001-web-ui-foundation`
- **Created**：2026-07-15
- **Status**：Pre-M-LOCK — Stage 1 draft (3 blockers fixed in-place 2026-07-15)
- **Priority**：P0

> 本文描述 v0.13 Web UI 基础版面的完整用户需求与行为边界。可观察、可断言的通过条件位于 `acceptance.md`。当前不得以提前形成的 architecture / test-plan / interfaces 草稿反向限制本文；正式设计只能在需求审批门通过后产生。

## User Stories

> 本版本复用了多份已批准上游合同的能力：
> - v0.11-001 FR-0801（Markdown 文档展示）— 见 US-1311、US-1312
> - v0.9-001 FR-0200（编辑器/实时预览分栏与同步滚动）— 见 US-1311、US-1312
> - v0.9-001 FR-0700（FR/NFR/Story 交叉引用跳转）— 见 US-1311
> - v0.11-001 FR-0301（Wiki 首页/story/spec/test-plan/architecture/interfaces 汇总、技术决定、FAQ、项目信息）— 见 US-1314
> - v0.12-001 FR-1001（Projects 导航：当前项目、历史项目）— 见 US-1315
> - v0.12-001 FR-1201（工作流图与当前位置）— 见 US-1315、US-1316
> - v0.12-001 FR-1901（可操作的 Project 详情 / Artifact Review UI / approve·reject）— 见 US-1316、US-1317
> - v0.12-001 FR-2201（端到端追溯 ledger 与 stage-results）— 见 US-1317
>
> 上述上游 FR 本期不重复定义新合同；本 spec 只规定 Web UI 在该能力之上**如何**以只读 / 受限方式呈现，并在 v0.13 中闭合 UI chrome、tab 共存与降级展示等只属于本期的边界。
>
> **关于"只读"的范围（重要）**：v0.13 的"只读"承诺仅适用于本期 Web UI 层（toolbar、sidebar、main panel、tab、右键菜单、按钮、菜单项、URL 参数）。本期不重新定义、不替换、也不在服务端关闭 v0.12-001 已批准的任何 HTTP 写接口（如 `gate approve` / `gate reject`、stage artifact 写回、Wiki / End User Docs / Dev Docs 的写 API 等）；那些写接口对任何调用方（curl、CLI、其他客户端）仍按 v0.12-001 / v0.11-001 / v0.9-001 已批准合同提供服务。Web UI 只是不暴露入口。如果将来某个上游版本要在服务端禁用部分写接口，由对应版本的 spec 显式提案，不在 v0.13 范围。

### US-1301

story: 作为 Louke 使用者，我希望 Web 主界面由 toolbar、sidebar 和多 tab 主面板三部分构成（类 VS Code activity bar / side panel / editor tabs），以便获得稳定且可预期的 chrome。
priority: P0

acceptance:
- 整页包含垂直 toolbar、可多级菜单 sidebar、含多个 tab 的 main panel 三个区域。
- 三个区域的相对位置和角色在所有页面之间保持一致。
- toolbar 只显示图标，鼠标悬停显示提示文字。

out-of-scope:
- 自定义 toolbar 图标顺序或更换图标。
- 主题、皮肤、密度切换。

### US-1302

story: 作为 Louke 使用者，我希望 toolbar 自上而下显示 Chat、Dev Docs、End User Docs、Wiki、Runs，自下而上显示 Gears、Accounts，并在悬停时看到提示，以便快速进入各主要功能。
priority: P0

acceptance:
- toolbar 自上而下顺序：Chat、Dev Docs、End User Docs、Wiki、Runs。
- toolbar 自下而上顺序：Gears、Accounts。
- 鼠标悬停图标时显示可读的提示文字（tooltip）。
- 图标命中区足以支持日常点击与悬停。

out-of-scope:
- 拖拽重排 toolbar。
- 用户自定义图标集。

### US-1303

story: 作为 Louke 使用者，我希望切换 toolbar 项时 sidebar 切换到对应导航、main panel 打开或激活对应 tab，且已打开的 Chat / Settings / Docs / Wiki / Runs tab 可以共存、不被关闭，以便多任务并行浏览。
priority: P0

acceptance:
- 切换 toolbar 项后，sidebar 切换到与该功能对应的导航树。
- 已打开的 Chat、Settings、Dev Docs、End User Docs、Wiki、Runs tab 在切换 toolbar 项之后仍保留。
- 再次点击同一 toolbar 项可激活对应已有 tab，而不是重复打开。
- 用户主动关闭 tab 是唯一关闭路径。

out-of-scope:
- 关闭所有 tab 的全局动作。
- 跨会话持久化 tab 集合。

### US-1304

story: 作为 Louke 使用者，我希望点击 Gears 后打开或激活 Settings tab，并采用左菜单 + 右详情的两栏结构；本版本只建立设置框架与可扩展入口，版本更新、服务器配置、S/A/B 模型绑定在 v0.15 实现。
priority: P0

acceptance:
- 点击 Gears 后 main panel 打开或激活 Settings tab。
- Settings tab 采用左侧菜单、右侧详情的两栏结构。
- Settings 菜单列出可扩展入口（占位或框架条目），不包含 v0.15 才有的版本更新 / 服务器配置 / S-A-B 模型绑定等具体功能。
- Settings 在本版本不要求落地具体设置项的保存。

out-of-scope:
- 版本更新通道。
- 服务器配置 UI。
- S/A/B 模型绑定 UI（v0.15）。
- 用户偏好持久化（除设置框架本身）。

### US-1305

story: 作为 Louke 使用者，我希望点击 Accounts 弹出账号菜单，本版本至少提供 logout，并保持现有认证边界，以便安全退出而无需额外 CLI。
priority: P0

acceptance:
- 点击 Accounts 后弹出账号菜单。
- 账号菜单至少包含 logout 入口。
- logout 之后浏览器侧不再保留可用的审批 / 数据访问凭据。
- 本期认证边界（loopback / local principal）不被破坏。

out-of-scope:
- 多账号切换、SSO、密码管理。
- 修改 loopback 认证之外的认证模型。

### US-1306

story: 作为 Louke 使用者，我希望点击 Chat 后 sidebar 显示 Agent 图标与名称列表，Maestro 位于最上方并默认选中，以便快速定位当前对话。
priority: P0

acceptance:
- 点击 Chat 后 sidebar 出现 Agent 列表。
- Maestro 位于列表最上方并默认选中。
- 列表项显示 Agent 图标与名称。
- 列表只读，不可被 UI 编辑（Agent 注册来自上游配置）。

out-of-scope:
- 自定义 Agent 顺序、隐藏 Agent、添加未注册 Agent。
- Chat 内搜索/历史/导出。

### US-1307

story: 作为 Louke 使用者，我希望 Chat tab 顶部显示当前 Agent 的 session transcript（支持 streaming），底部提供普通对话输入框，以便与选定 Agent 进行实时对话。
priority: P0

acceptance:
- Chat tab 上方显示当前 Agent 的 session transcript。
- 新增消息以 streaming 形式追加，而非整段重排。
- Chat tab 底部提供普通对话输入框并可发送。
- transcript 在 Chat tab 关闭再激活（不退出 sidebar 选择）时保留当前 Agent 上下文。

out-of-scope:
- harness `/` 命令（v0.15）。
- 操作系统 `!` 命令（v0.15）。
- 富文本 / Markdown 输入编辑工具栏。
- 多模态附件。

### US-1308

story: 作为 Louke 使用者，我希望切换 sidebar 中 Agent 时 Chat tab 切换到该 Agent 对应会话上下文，不混淆不同 Agent 的 transcript，以便同时观察不同 Agent 的状态。
priority: P0

acceptance:
- 在 sidebar 选中另一 Agent 后，Chat tab 顶部 transcript 切换到该 Agent 的会话。
- 不同 Agent 的 transcript 互不覆盖、互不串行。
- 切回先前 Agent 时能看到之前的对话内容（受 streaming 与 session 持久化约束）。
- transcript 切换由 sidebar 选中驱动，不由 URL 手动拼接。

out-of-scope:
- 跨 Agent 共享或合并 transcript。
- Agent transcript 的搜索与导出。

### US-1309

story: 作为 Louke 使用者，我希望本版本 Chat 只支持普通对话输入，harness `/` 命令和操作系统 `!` 命令在 v0.15 设计与实现，以便本版本边界清晰、风险可控。
priority: P0

acceptance:
- Chat 输入框接受普通文本。
- 以 `/` 开头的输入按普通文本提交；不识别为 harness 命令。
- 以 `!` 开头的输入按普通文本提交；不触发 shell 命令。
- 提交行为对未实现命令不抛错、不假装成功。

out-of-scope:
- harness `/` 命令解析与执行（v0.15）。
- 操作系统 `!` 命令执行（v0.15）。

### US-1310

story: 作为 Louke 使用者，我希望点击 Dev Docs 后 sidebar 以 `.louke/project/specs` 下的 spec 目录为一级菜单（初始折叠、记忆展开状态），展开后显示目录中的 Markdown 文档，以便在 Web 中浏览设计文档。
priority: P0

acceptance:
- 点击 Dev Docs 后 sidebar 的一级菜单与 `.louke/project/specs` 下每个 spec 目录一一对应。
- 菜单初始折叠。
- 展开状态在同一会话内被记住（同一用户、同一 Web 上下文）。
- 展开后叶子项展示对应 spec 目录下的 Markdown 文档名。

out-of-scope:
- 全局跨用户/跨设备的展开持久化。
- 文档内全文搜索。
- 文档新建 / 删除（Dev Docs 由 Agent 生成，本期不提供 AI 辅助编辑）。

### US-1311

story: 作为 Louke 使用者，我希望 Dev Docs 复用 v0.11-001 FR-0801 的文档发现与渲染、v0.9-001 FR-0200 的编辑器/实时预览分栏、v0.9-001 FR-0700 的 FR/NFR/Story 交叉引用跳转，且 Dev Docs 由 Agent 生成、不提供 AI 辅助编辑，以便用户尽早看到已生成的设计文档。
priority: P0

acceptance:
- 选中 Markdown 文档后 main panel 以 v0.11-001 FR-0801 规定的展示能力渲染。
- 编辑器/实时预览分栏与同步滚动沿用 v0.9-001 FR-0200 行为。
- FR/NFR/Story 交叉引用以 v0.9-001 FR-0700 形式可点击跳转。
- Dev Docs 不暴露 AI 辅助编辑入口。

out-of-scope:
- Dev Docs 的 AI 辅助编辑。
- Dev Docs 之外的自定义 Markdown 渲染。

### US-1312

story: 作为 Louke 使用者，我希望点击 End User Docs 后 sidebar 显示面向最终用户的 Markdown 文档树，main panel 支持展示、编辑和实时预览；基础能力复用 v0.11-001 FR-0801 与 v0.9-001 FR-0200；AI 辅助编辑在 v0.15 实现，以便最终用户文档可独立维护。
priority: P0

acceptance:
- 点击 End User Docs 后 sidebar 显示面向最终用户的 Markdown 文档树。
- main panel 至少提供文档展示、编辑和实时预览三种能力。
- 文档展示沿用 v0.11-001 FR-0801。
- 编辑/实时预览分栏沿用 v0.9-001 FR-0200。
- End User Docs 不暴露 AI 辅助编辑入口。

out-of-scope:
- End User Docs AI 辅助编辑（v0.15）。
- 终版文档导出 / 发布渠道。

### US-1313

story: 作为 Louke 使用者，我希望点击 Wiki 后 sidebar 显示 Wiki 导航树，main panel 打开或激活 Wiki tab，并渲染所选 Markdown 页面，以便在 Web 中浏览 Wiki。
priority: P0

acceptance:
- 点击 Wiki 后 sidebar 出现 Wiki 导航树。
- main panel 打开或激活 Wiki tab。
- 在 sidebar 选中 Wiki 页面后，main panel 渲染所选 Markdown。
- Wiki tab 关闭再激活时保留最近一次选中的页面。

out-of-scope:
- Wiki 在线编辑。
- Wiki 页面创建 / 删除 / 重命名。
- Wiki 评论 / 订阅。

### US-1314

story: 作为 Louke 使用者，我希望 Wiki 的首页、story/spec/test-plan/architecture/interfaces 汇总、技术决定、FAQ 和项目信息结构复用 v0.11-001 FR-0301，且对未知 / 后续版本新增的 Wiki 页面采用可读的通用降级展示（不崩溃）。
priority: P0

acceptance:
- Wiki 首页、story/spec/test-plan/architecture/interfaces 汇总、技术决定、FAQ、项目信息结构沿用 v0.11-001 FR-0301。
- 选中一个不存在的 Wiki 页面路径时，main panel 不崩溃；显示可读的 NotFound / 无该页面降级提示。
- 对后续 v0.14 等版本可能新增的 Wiki 页面，本版本界面以通用 Markdown 渲染方式呈现而不要求 schema 升级。
- Wiki 渲染为只读，不暴露编辑 / 创建 / 删除入口。

out-of-scope:
- Wiki 编辑 / 创作。
- Wiki 全文搜索 / 版本对比。
- Wiki 评论 / 通知。

### US-1315

story: 作为 Louke 使用者，我希望点击 Runs 后 sidebar 显示当前项目、历史项目及其 run（沿用 v0.12-001 FR-1001 的 Projects 导航），main panel 显示所选 run 的 workflow graph，以便理解各 run 的状态。
priority: P0

acceptance:
- 点击 Runs 后 sidebar 出现 Projects 导航，沿用 v0.12-001 FR-1001 的当前项目 / 历史项目 / 创建新项目结构。
- 选中某 run 后 main panel 显示该 run 绑定的 workflow graph（沿用 v0.12-001 FR-1201）。
- 未选中任何 run 时 main panel 显示空状态而非崩溃。
- 切换 sidebar 选择后 main panel 同步刷新 graph。

out-of-scope:
- Runs 面板的写入操作（v0.13 只读）。
- workflow 回退 / waive（用户故事 #20 明确排除）。

### US-1316

story: 作为 Louke 使用者，我希望 workflow graph 的每个 stage 节点以状态徽标、颜色或等价图形标注 stage-results，包括 review verdict、gate pass/fail 和 author result，不直接以原始 JSON 作为主要界面，以便快速读取每个 stage 的实际结果。
priority: P0

acceptance:
- 每个 stage 节点带可识别的状态徽标或颜色，对应 stage-results 的核心状态（已完成 / 当前执行 / 等待人类 / 阻塞 / 失败 / 未开始 / 已跳过）。
- review verdict（PASS / REJECT / WAIVED）、gate pass/fail、author result 在节点上有可见区分。
- 节点旁边不直接堆叠 stage-results 的原始 JSON；点击进入只读详情查看完整结果。
- 状态视觉与 v0.12-001 FR-1201 已定义的标记一致。

out-of-scope:
- 节点自定义颜色 / 形状。
- 工作流回退 / 重跑 / 取消操作按钮（v0.13 观察面）。

### US-1317

story: 作为 Louke 使用者，我希望点击 stage 节点后可以只读查看 artifact 的 digest、verdict、required reviewer 和 review 结论；stage-results 不提供编辑入口。该展示复用 v0.12-001 FR-1201、FR-1901 和 FR-2201。
priority: P0

acceptance:
- 点击 stage 节点后打开该 stage 的只读 artifact 视图。
- 视图显示 digest、verdict、required reviewer 和 review 结论。
- 视图沿用 v0.12-001 FR-1201 / FR-1901 / FR-2201 已批准字段。
- 视图不暴露编辑、提交、删除、回退或 waive 等写操作入口。
- 对未实现的 stage 节点（如 v0.14 reflow 新增）显示可读降级视图。

out-of-scope:
- stage-results 编辑 / 写回（v0.15+）。
- stage 之间的人工干预（waive / 回退）。

### US-1318

story: 作为 Louke 使用者，我希望 UI 对未知或后续版本新增的 stage、status 和 result kind 采用可读的通用降级展示，不因 v0.14 workflow reflow 增加状态而崩溃，以便本版本 UI 不被未来 contract 漂移破坏。
priority: P0

acceptance:
- 对 v0.14 / v0.15 等后续版本新增的 stage 名称、status、result kind，UI 以通用占位文本 / 标签渲染。
- 未知状态不会让 toolbar、sidebar、main panel、tab 任何部分崩溃或抛错。
- 降级展示本身被显式标记（如"未知 stage"，"未知 status"），便于调试。
- 不允许因未知值返回 500 或空白 tab。

out-of-scope:
- 跨版本 schema 自动升级。
- 自定义降级模板。

### US-1319

story: 作为 Louke 使用者，我希望本版本存在至少一条浏览器产品主旅程：启动 Web UI → 切换 toolbar → 打开一个文档 → 进入一个 run 并查看 stage artifact，以便尽早体验并为 v0.14 reflow 提供反馈。
priority: P0

acceptance:
- 浏览器端到端旅程覆盖：启动 Web → 至少切换两个 toolbar 项 → 打开 Dev Docs 或 End User Docs 或 Wiki 中的至少一个文档 → 进入 Runs 中至少一个 run 并点击至少一个 stage 节点查看 artifact。
- 上述旅程必须可重复执行，不依赖手写内部状态。
- 旅程通过真实受支持浏览器（本期不强求多浏览器矩阵）端到端执行。

out-of-scope:
- 多浏览器兼容矩阵。
- 旅程性能基准。

### US-1320

story: 作为 Louke 维护者，我希望明确 v0.13 不实现：workflow 回退 / waive / CI report 中断语义 / 夜间重构分支 / 完整 Settings 功能 / harness `/` 与 shell `!` 命令 / End User Docs AI 辅助编辑 / UI i18n，以便本期边界清晰、不混入下一阶段风险。
priority: P0

acceptance:
- 上述排除项在本版本 Web UI 中无任何对应入口、按钮、菜单或 API。
- 默认 settings 与 accounts 菜单不出现上述能力。
- 任何 README / 文档 / UI 文案不向用户承诺上述能力。

out-of-scope:
- 上述八类能力本身。

## Usage Scenarios

### scenario-1301 启动 Web 并进入主旅程

用户启动 `lk serve`，浏览器打开主界面。toolbar 显示 Chat、Dev Docs、End User Docs、Wiki、Runs、Gears、Accounts。点击任意顶部 toolbar 项，sidebar 切换并 main panel 打开或激活对应 tab。已打开 tab 不会因切换 toolbar 而关闭。

### scenario-1302 Chat 切换 Agent

用户在 Chat sidebar 选中 A1，transcript 显示 A1 历史与新消息流。切到 A2，transcript 切换为 A2 的内容。切回 A1，之前的 A1 transcript 仍可读。

### scenario-1303 浏览 Dev Docs

用户点击 Dev Docs，sidebar 出现 spec 目录树。展开某一 spec 后选中 Markdown，main panel 渲染并可分栏编辑/预览。FR/NFR/Story 交叉引用可点击跳转。

### scenario-1304 浏览 End User Docs

用户点击 End User Docs，sidebar 显示面向最终用户的 Markdown 树；选中后 main panel 既可展示，也可进入编辑并实时预览。本期不出现 AI 辅助编辑。

### scenario-1305 浏览 Wiki

用户点击 Wiki，sidebar 显示 Wiki 导航。选中首页 / story / spec / test-plan / architecture / interfaces / 技术决定 / FAQ / 项目信息任一入口，main panel 渲染对应页面。选中不存在的路径时 main panel 显示可读 NotFound 降级。Wiki 不提供编辑入口。

### scenario-1306 浏览 Runs

用户点击 Runs，sidebar 显示当前 / 历史项目及 run。选中一个 run 后 main panel 渲染 workflow graph；节点带有 review verdict、gate pass/fail、author result 的可视化标识。点击节点打开只读 artifact 视图，显示 digest、verdict、required reviewer 与 review 结论，无任何写入口。

### scenario-1307 未知 stage / status 降级

v0.14 reflow 引入新的 stage 名称与 status 后，v0.13 Web UI 不崩溃，节点以通用降级文本呈现，stage artifact 视图也以通用字段渲染。toolbar、sidebar、tab 不出现 500 或空白。

### scenario-1308 Settings 与 Accounts 最小闭环

用户点击 Gears，main panel 打开或激活 Settings tab，左菜单 + 右详情结构出现，但仅展示可扩展入口占位，不包含 v0.15 才有的版本更新 / 服务器配置 / S-A-B 模型绑定。点击 Accounts 弹出菜单，至少包含 logout。

## Functional Requirements

<a id="fr-1301"></a>

### FR-1301 主界面 chrome：toolbar + sidebar + tabs

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- Web 主界面必须包含垂直 toolbar、可多级菜单的 sidebar、承载多 tab 的 main panel 三个区域，且三者相对位置在所有页面之间保持一致。
- toolbar 项必须只以图标呈现，鼠标悬停时显示提示文字。
- 切换 toolbar 项（**Gears 与 Accounts 除外**——见 FR-1303 / FR-1304）后，sidebar 必须切换到与该功能对应的导航，main panel 必须打开或激活对应 tab。
- 已经打开的 Chat、Settings、Dev Docs、End User Docs、Wiki、Runs tab 必须共存，不得因切换 toolbar 项而被关闭；再次点击同一 toolbar 项必须激活已有 tab 而非重复打开。
- tab 共存**不限数量上限**，由浏览器自然承载。
- 关闭 tab 必须只能由用户主动操作触发。
- 验收引用：AC-FR1301-01 至 AC-FR1301-05。

---

<a id="fr-1302"></a>

### FR-1302 toolbar 图标顺序与提示

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- toolbar 自上而下顺序必须为：Chat、Dev Docs、End User Docs、Wiki、Runs。
- toolbar 自下而上顺序必须为：Gears、Accounts。
- 每个图标必须有可读的 hover tooltip。
- 图标命中区必须满足日常点击与悬停操作。
- 验收引用：AC-FR1302-01 至 AC-FR1302-03。

---

<a id="fr-1303"></a>

### FR-1303 Settings tab 与可扩展入口

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- **Gears 是全局入口（与 Chat / Dev Docs / End User Docs / Wiki / Runs 的角色不同）**：点击 Gears 必须打开或激活 Settings tab。Gears **不切换 sidebar 内容**，sidebar 维持点击前最后一次由其它 toolbar 项设置的状态；main panel 切换到 Settings tab。
- Settings tab 必须采用左侧菜单、右侧详情的两栏结构。
- Settings 菜单**预填 v0.15 计划项作为占位条目**（"版本更新" / "服务器配置" / "S/A/B 模型绑定"），均**置灰禁用**并打通用标记（如"待 v0.15"），不展示具体设置 UI；这样既明确传递路线图，又不向用户承诺已实现。
- 本版本不要求落地具体设置项的保存路径；后续版本通过该入口结构添加。
- 验收引用：AC-FR1303-01 至 AC-FR1303-04。

---

<a id="fr-1304"></a>

### FR-1304 Accounts 菜单与 logout

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 点击 Accounts 必须弹出账号菜单。
- 账号菜单至少包含 logout 入口。
- logout 后浏览器侧不得保留可用的审批 / 数据访问凭据。
- 本期认证边界（loopback / local principal）不得被破坏。
- 验收引用：AC-FR1304-01 至 AC-FR1304-03。

---

<a id="fr-1305"></a>

### FR-1305 Chat Agent 列表与默认选中

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 点击 Chat 后 sidebar 必须显示 Agent 列表，每项含图标与名称。
- Maestro 必须位于列表最上方并默认选中。
- 列表必须只读，不暴露 UI 编辑入口（Agent 注册来自上游配置）。
- 验收引用：AC-FR1305-01 至 AC-FR1305-03。

---

<a id="fr-1306"></a>

### FR-1306 Chat transcript、streaming 与普通输入

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- Chat tab 上方必须显示当前 Agent 的 session transcript。
- 新增消息必须以 streaming 形式追加，不得整段重排覆盖既有 transcript。
- Chat tab 底部必须提供普通对话输入框，支持提交普通文本。
- 当 Chat tab 关闭再被同一 sidebar Agent 选中激活时，transcript 必须保留当前 Agent 上下文。
- 以 `/` 开头的输入按普通文本提交；不得识别为 harness 命令。
- 以 `!` 开头的输入按普通文本提交；不得触发 shell 命令或返回假成功。
- 验收引用：AC-FR1306-01 至 AC-FR1306-05。

---

<a id="fr-1307"></a>

### FR-1307 Agent 切换与 transcript 隔离

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 在 sidebar 切换 Agent 后，Chat tab transcript 必须切换到该 Agent 的会话。
- 不同 Agent 的 transcript 必须互不覆盖、互不串行。
- 切回先前 Agent 时必须显示其之前的内容（在持久化与 streaming 允许范围内）。
- transcript 切换必须由 sidebar 选中驱动；不允许通过手动拼接 URL 强行切换到未注册 Agent。
- 验收引用：AC-FR1307-01 至 AC-FR1307-04。

---

<a id="fr-1308"></a>

### FR-1308 Dev Docs sidebar 目录树

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 点击 Dev Docs 后 sidebar 必须以 `.louke/project/specs` 下每个 spec 目录为一组一级菜单。
- 菜单必须初始折叠。
- 菜单展开状态必须在同一 Web 会话内被记住；收起后再展开保持上次状态。
- 展开后叶子项必须显示对应 spec 目录下的 Markdown 文档名。
- 验收引用：AC-FR1308-01 至 AC-FR1308-04。

---

<a id="fr-1309"></a>

### FR-1309 Dev Docs 文档展示、预览与交叉引用（复用 v0.11-001 FR-0801 / v0.9-001 FR-0200 / v0.9-001 FR-0700）

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 选中 Dev Docs 中一个 Markdown 文档后，main panel 必须以 v0.11-001 FR-0801 规定的展示能力渲染该文档。
- 编辑器/实时预览分栏与同步滚动行为必须沿用 v0.9-001 FR-0200。
- 文档内的 FR/NFR/Story 交叉引用必须以 v0.9-001 FR-0700 形式可点击跳转。
- Dev Docs 由 Agent 生成、不提供 AI 辅助编辑：UI **不暴露** "Save" / "保存" 按钮、不暴露 "AI 辅助编辑" / "AI rewrite" / "AI assist" 等任何写入口；编辑器分栏仅用于只读浏览与实时预览，不向服务端发起任何 PUT/POST/PATCH/DELETE 写请求。
- 验收引用：AC-FR1309-01 至 AC-FR1309-05。

---

<a id="fr-1310"></a>

### FR-1310 End User Docs 文档树与基础编辑（复用 v0.11-001 FR-0801 / v0.9-001 FR-0200）

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 点击 End User Docs 后 sidebar 必须显示面向最终用户的 Markdown 文档树。
- main panel 必须支持文档展示、编辑和实时预览三种能力。
- 文档展示能力沿用 v0.11-001 FR-0801。
- 编辑器/实时预览分栏沿用 v0.9-001 FR-0200。
- 不得暴露 AI 辅助编辑入口。
- 验收引用：AC-FR1310-01 至 AC-FR1310-10。

**End User Docs 持久化与保存契约（v0.13 本期明确）**：

- **规范根目录**：`<project>/.louke/end-user-docs/`，即相对于项目根的 `.louke/end-user-docs/`；本期不支持项目级以外的全局文档根。
- **可写文件范围**：仅 `.md` 后缀、且直接位于该根目录（或其子目录）下的 Markdown 文件；其它扩展名、隐藏文件、符号链接、`.louke/` 内部 spec / acceptance / story / test-plan / architecture / interfaces / project 配置文件均**不可写**。
- **文件名规则**：仅允许 Unicode 字母 / 数字 / `-` / `_` / `.` / 空格；最大长度 120 字符；不允许空名、不允许 `..` 路径段、不允许绝对路径；与现有树冲突的文件名在保存时返回 4xx。
- **大小上限**：单文件 ≤ 1 MiB；超出返回 413。
- **保存触发**：显式 "Save" 按钮（**不做**自动保存 / 防抖保存 / 离开页面保存）；按钮在编辑器内容自上次保存或加载以来无变化时处于禁用。
- **保存成功**：HTTP 200，响应体含 `sha256`（保存后文件 digest）与 `saved_at`（ISO-8601 UTC）；前端用 `sha256` 重新拉取预览并刷新分栏。
- **保存失败**：HTTP 4xx，响应体含 `code`（如 `VALIDATION_FAILED` / `TOO_LARGE` / `PATH_NOT_ALLOWED` / `CONFLICT`）与可读 `message`；UI 显示错误 toast，编辑器内容保持不丢失。
- **冲突检测**：保存请求携带客户端已知的 `expected_mtime`（来自加载响应或上一次保存响应）；若文件 mtime 已变化，服务端返回 409 `CONFLICT`，UI 提示"文件已被外部修改"，并提供"重新加载并放弃我的编辑"与"仍要覆盖"两个动作（后者必须二次确认）。
- **持久化往返**：保存成功后，关闭 tab / 刷新页面 / 重启 Web 服务后再次打开同一文件，main panel 渲染内容必须等于最后一次成功保存的字节（通过 SHA 校验）。
- **认证边界**：保存走现有 loopback / local principal 边界（与 v0.11-001 一致）；不允许未认证写。
- **底层能力**：与 Dev Docs 完全一致（FR-1309 复用 v0.11-001 FR-0801 / v0.9-001 FR-0200 / v0.9-001 FR-0700）；额外支持 inline-discussion 的**编辑与显示**（不做 resolved 状态查询）。

---

<a id="fr-1311"></a>

### FR-1311 Wiki 导航与只读渲染

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 点击 Wiki 后 sidebar 必须出现 Wiki 导航树。
- main panel 必须打开或激活 Wiki tab。
- 选中 Wiki 页面后 main panel 必须渲染所选 Markdown。
- Wiki tab 关闭再被激活时，必须保留最近一次选中的页面。
- 不得暴露 Wiki 编辑 / 创建 / 删除 / 重命名入口（UI 层承诺；不覆盖 v0.11-001 / v0.9-001 已批准的服务端 Wiki 写接口）。
- 验收引用：AC-FR1311-01 至 AC-FR1311-05。

---

<a id="fr-1312"></a>

### FR-1312 Wiki 结构复用与 NotFound / 未知页面降级（复用 v0.11-001 FR-0301）

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- Wiki 首页、story / spec / test-plan / architecture / interfaces 汇总、技术决定、FAQ、项目信息结构必须沿用 v0.11-001 FR-0301。
- 选中不存在的 Wiki 页面路径时，main panel 必须显示可读的 NotFound / 无该页面降级提示，不得返回空白或 500。
- 对后续 v0.14 等版本可能新增的 Wiki 页面，必须以通用 Markdown 渲染方式呈现，不要求 schema 升级。
- 渲染必须为只读（UI 层不暴露编辑入口；不覆盖 v0.11-001 / v0.9-001 已批准的服务端 Wiki 写接口）。
- 验收引用：AC-FR1312-01 至 AC-FR1312-04。

---

<a id="fr-1313"></a>

### FR-1313 Runs sidebar 与 workflow graph（复用 v0.12-001 FR-1001 / FR-1201）

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 点击 Runs 后 sidebar 必须出现 Projects 导航，沿用 v0.12-001 FR-1001 的当前项目 / 历史项目 / 创建新项目结构。
- 选中某 run 后 main panel 必须显示该 run 绑定的 workflow graph，沿用 v0.12-001 FR-1201。
- 未选中任何 run 时 main panel 必须显示空状态而非崩溃。
- 切换 sidebar 选择后 main panel 必须同步刷新 graph。
- 验收引用：AC-FR1313-01 至 AC-FR1313-04。

---

<a id="fr-1314"></a>

### FR-1314 stage 节点状态徽标（review verdict / gate / author）

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 每个 stage 节点必须带可识别的状态徽标或颜色，至少覆盖：已完成 / 当前执行 / 等待人类 / 阻塞 / 失败 / 未开始 / 已跳过。
- 节点必须显示 review verdict（PASS / REJECT / WAIVED 之一或通用降级）的可视化标识。
- 节点必须显示 gate pass/fail 的可视化标识。
- 节点必须显示 author result 的可视化标识。
- 节点旁不得直接堆叠 stage-results 原始 JSON；必须通过点击进入详情查看。
- 状态视觉与 v0.12-001 FR-1201 已定义的标记一致。
- 验收引用：AC-FR1314-01 至 AC-FR1314-04。

---

<a id="fr-1315"></a>

### FR-1315 stage artifact 只读视图（复用 v0.12-001 FR-1201 / FR-1901 / FR-2201）

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 点击 stage 节点必须打开该 stage 的只读 artifact 视图。
- 视图必须显示 digest、verdict、required reviewer、review 结论，且字段沿用 v0.12-001 FR-1201 / FR-1901 / FR-2201。
- 视图不得暴露编辑、提交、删除、回退、waive 等写操作入口（UI 层承诺；不覆盖 v0.12-001 FR-1201 / FR-1901 / FR-2201 已批准的服务端 stage / artifact 写接口，对 curl / CLI / 其他客户端仍按 v0.12 合同提供服务）。
- 对未实现的 stage 节点（如 v0.14 reflow 新增）必须显示可读降级视图。
- 验收引用：AC-FR1315-01 至 AC-FR1315-04。

---

<a id="fr-1316"></a>

### FR-1316 未知 stage / status / result kind 的通用降级

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 对 v0.14 / v0.15 等后续版本新增的 stage 名称、status、result kind，UI 必须以通用占位文本或标签渲染。
- 未知值不得让 toolbar、sidebar、main panel、tab 任何部分崩溃或抛错。
- 降级展示本身必须被显式标记（如"未知 stage"、"未知 status"）。
- 未知值不得让 UI 返回 500 或留下空白 tab。
- 验收引用：AC-FR1316-01 至 AC-FR1316-04。

---

<a id="fr-1317"></a>

### FR-1317 浏览器主旅程端到端（US-1319）

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 必须存在一条端到端浏览器产品主旅程：启动 Web UI → 切换至少两个 toolbar 项 → 打开 Dev Docs / End User Docs / Wiki 中至少一个文档 → 进入 Runs 中至少一个 run 并点击至少一个 stage 节点查看 artifact。
- 旅程必须可重复执行，不依赖手写内部状态。
- 旅程必须通过受支持的浏览器（本期不强求多浏览器矩阵）端到端执行；CI 必须包含至少一个 Playwright/Chromium smoke 覆盖该旅程。
- 验收引用：AC-FR1317-01 至 AC-FR1317-04。

---

<a id="fr-1318"></a>

### FR-1318 v0.13 不实现范围（US-1320）

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- 本版本 Web UI 不得提供以下任何入口、按钮、菜单或 API：workflow 回退、workflow waive、CI report 中断语义、夜间重构分支、完整 Settings 功能、harness `/` 命令、shell `!` 命令、End User Docs AI 辅助编辑、UI i18n。
- 默认 settings 与 accounts 菜单不得出现上述能力。
- 任何 README、文档或 UI 文案不得向用户承诺上述能力。
- 验收引用：AC-FR1318-01 至 AC-FR1318-03。

---

## Out-of-Scope（确认项）

以下项目本期不实现，请在 M-LOCK 阶段由人类再次确认：

1. workflow 回退（workflow rollback）。
2. workflow waive。
3. CI report 中断语义。
4. 夜间重构分支（nightly refactor branch）。
5. 完整 Settings 功能（版本更新、服务器配置、S/A/B 模型绑定）。
6. harness `/` 命令。
7. 操作系统 shell `!` 命令。
8. End User Docs AI 辅助编辑。
9. UI i18n。
10. workflow reflow（v0.14 主线，本版仅保证对其降级兼容）。
11. 多浏览器兼容矩阵。
12. 跨用户 / 跨设备的 Settings / tab 展开状态持久化。
13. 在 v0.13 服务端关闭、替换或收紧 v0.12-001 / v0.11-001 / v0.9-001 已批准的 HTTP 写接口（gate approve/reject、stage artifact 写回、Wiki / End User Docs / Dev Docs 写 API 等）。v0.13 仅为"Web UI 层不暴露写入口"，不修改上游 contract。

## 待确认问题（PENDING）

下列 ⚠️ 项默认采用括号内计划；如不同意，请在 M-LOCK 之前回复：

1. **FR-1301 / US-1303**：已打开 tab 是否设上限？（默认：不限上限，由浏览器自然承载）
> **Aaron:** agree → **Decided：不限上限**
2. **FR-1303 / US-1304**：Settings 占位条目是否预填 v0.15 计划项名？（默认：仅空条目 + 通用"待 v0.15"标记）
> **Aaron:** 预填 → **Decided：预填 v0.15 计划项并置灰 + "待 v0.15" 标记**
3. **FR-1310 / US-1312**：End User Docs 是否在 v0.13 就支持编辑 + 实时预览？（默认：本期就支持）
> **Aaron:** 支持。底层能力与 Dev Docs 完全一致。也支持 inline-discussion（仅编辑、显示、不查 resolved 状态）→ **Decided：本期支持编辑 + 实时预览，编辑契约见 FR-1310 第二段（规范根、可写范围、Save 触发、成功/失败/冲突、持久化往返）**
4. **FR-1314 / US-1316**：stage 节点 status 视觉是否复用 v0.12-001 FR-1201 已定义的颜色与图标，还是另起？（默认：复用 v0.12-001 FR-1201）
> **Aaron:** agree → **Decided：复用 v0.12-001 FR-1201**
5. **FR-1317 / US-1319**：主旅程是否必须经过 Wiki？（默认：Dev Docs / End User Docs / Wiki 至少一个即可，但若该 fixture 不可用则降级到 Dev Docs）
> **Aaron:** 需要包含 wiki，但测试时， wiki 内容可以 mock → **Decided：必须包含 Wiki（测试可 mock 内容）**

所有 ⚠️ 已翻转至 ✅，无遗留 PENDING。
