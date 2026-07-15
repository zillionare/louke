# Web UI Foundation — Acceptance Criteria

- **Spec ID**：`v0.13-001-web-ui-foundation`
- **Created**：2026-07-15
- **Status**：Pre-M-LOCK — Stage 1 draft

> 每个条件从浏览器端可见的 Web UI、公开 HTTP API 或 Runtime 持久化观察出口验证。不得通过读取或修改内部 Python 对象伪造通过。所有 AC-FR13XX-NN 与 v0.12-001 的 AC-FR24XX-NN 不冲突；本 spec 复用 v0.12-001 已批准字段时只做引用，不复制其 AC。

<a id="ac-fr-1301"></a>
## FR-1301 主界面 chrome：toolbar + sidebar + tabs

### AC-1
AC-FR1301-01

- **Given** 浏览器加载 Louke Web 根页面，**When** 页面首次渲染完成，**Then** DOM 同时存在垂直 toolbar 区域、可多级菜单 sidebar 区域、含 tab 切换栏的 main panel 区域，且三者在 DOM 顺序、视觉顺序与可访问性树中相对位置稳定（可通过 querySelector / role 检查 toolbar、sidebar、tablist 三类节点）。

### AC-2
AC-FR1301-02

- **Given** 任意一个 toolbar 图标被渲染，**When** 鼠标悬停或键盘 focus 到该图标，**Then** 浏览器原生 tooltip 或 aria-label / title 属性返回可读的提示文字，且提示文字非空、不与图标名完全相同。

### AC-3
AC-FR1301-03

- **Given** 浏览器已加载主页面且 Chat tab 已激活，**When** 用户点击 Dev Docs toolbar 项，**Then** sidebar 内容切换到 Dev Docs 导航，main panel 激活 Dev Docs tab，且原 Chat tab 仍以可关闭 tab 形式存在。

### AC-4
AC-FR1301-04

- **Given** 浏览器已同时存在 Chat、Settings、Dev Docs、End User Docs、Wiki、Runs 六个打开的 tab，**When** 用户连续点击四个不同的 toolbar 项（任选 Chat / Dev Docs / End User Docs / Wiki / Runs 五个中任意四个；**不包含 Gears / Accounts，因为它们是全局入口，见 FR-1303 / FR-1304**），**Then** 六个 tab 全部保留且均未被关闭；切换 toolbar 项后 sidebar 与 main panel 仅反映当前激活项。

### AC-5
AC-FR1301-05

- **Given** 已激活的某个 tab，**When** 用户再次点击同一 toolbar 项，**Then** main panel 重新激活该已有 tab，不创建重复 tab 实例（通过检查对应 tab 的 instance id / data-attr 唯一性证明）。

---

<a id="ac-fr-1302"></a>
## FR-1302 toolbar 图标顺序与提示

### AC-1
AC-FR1302-01

- **Given** 主页面渲染完成，**When** 查询 toolbar 自上而下的可见图标列表，**Then** 顺序为：Chat、Dev Docs、End User Docs、Wiki、Runs（顺序由 toolbar 中 DOM / aria-label / data-name 字段证明）。

### AC-2
AC-FR1302-02

- **Given** 主页面渲染完成，**When** 查询 toolbar 自下而上的可见图标列表，**Then** 顺序为：Gears、Accounts。

### AC-3
AC-FR1302-03

- **Given** 主页面渲染完成，**When** 测量每个 toolbar 图标的可点击命中区，**Then** 每个命中区在桌面视口下 ≥ 32×32 像素，且 tooltip / aria-label 非空。

---

<a id="ac-fr-1303"></a>
## FR-1303 Settings tab 与可扩展入口

### AC-1
AC-FR1303-01

- **Given** 浏览器在主页面，**When** 用户点击 Gears toolbar 项，**Then** main panel 打开或激活 Settings tab，且 sidebar 不切换（仍为之前状态）。

### AC-2
AC-FR1303-02

- **Given** Settings tab 处于激活，**When** 页面渲染完成，**Then** 存在左菜单与右详情两栏布局，左菜单为可扩展入口列表，右详情显示当前选中入口的占位说明。

### AC-3
AC-FR1303-03

- **Given** Settings 左菜单渲染完成，**When** 列出可见条目，**Then** 至少出现"版本更新"、"服务器配置"、"S/A/B 模型绑定"三条预填占位条目（均**置灰禁用**并标记"待 v0.15"或等价通用文字）；不得出现其他具体功能名（如 workflow 回退、waive、i18n 等具体项）。

### AC-4
AC-FR1303-04

- **Given** Settings tab 激活，**When** 用户点击任一置灰占位条目，**Then** 右详情显示"待 v0.15"或等价占位说明，不发起任何写请求、不抛错、不切换 sidebar。

---

<a id="ac-fr-1304"></a>
## FR-1304 Accounts 菜单与 logout

### AC-1
AC-FR1304-01

- **Given** 浏览器在主页面，**When** 用户点击 Accounts toolbar 项，**Then** 弹出账号菜单浮层，至少包含 logout 可见条目。

### AC-2
AC-FR1304-02

- **Given** 账号菜单已打开且用户点击 logout，**When** logout 完成后，**Then** 浏览器 cookie / localStorage / sessionStorage 中不再持有可访问受保护 API 的凭据；后续访问受保护页面被服务端拒绝并跳转回 setup/login 入口。

### AC-3
AC-FR1304-03

- **Given** 用户已 logout，**When** 再次访问 Web，**Then** 不允许在未重新认证前提交任何 gate approve / reject 请求，且 loopback / local principal 边界未变化。

---

<a id="ac-fr-1305"></a>
## FR-1305 Chat Agent 列表与默认选中

### AC-1
AC-FR1305-01

- **Given** 浏览器在主页面，**When** 用户点击 Chat toolbar 项，**Then** sidebar 出现 Agent 列表，每项至少含图标元素与名称文本。

### AC-2
AC-FR1305-02

- **Given** Chat sidebar 列表渲染完成，**When** 查询列表第一项，**Then** 该项对应 Maestro，且该项处于"选中 / active"视觉与 ARIA 状态。

### AC-3
AC-FR1305-03

- **Given** Chat sidebar 渲染完成，**When** 尝试通过 UI 修改 Agent 列表（拖拽、隐藏、新增），**Then** UI 不暴露此类操作入口；非 UI 的 Agent 注册变更不在本 spec 范围。

---

<a id="ac-fr-1306"></a>
## FR-1306 Chat transcript、streaming 与普通输入

### AC-1
AC-FR1306-01

- **Given** Chat tab 处于激活且 Agent 已选，**When** Chat tab 渲染完成，**Then** 上方 transcript 区可观察到当前 Agent 的历史消息条目。

### AC-2
AC-FR1306-02

- **Given** Agent 正在产生 streaming 回复，**When** 监听 transcript DOM 变化，**Then** 新 token 以增量方式追加到当前消息节点尾部，而不是整段替换或重排 transcript。

### AC-3
AC-FR1306-03

- **Given** Chat tab 处于激活，**When** 用户在底部输入框输入普通文本并提交，**Then** 该文本作为新用户消息进入 transcript，且提交成功后输入框**立即清空**（变为空字符串，无残留草稿）。

### AC-4
AC-FR1306-04

- **Given** 用户先选中 Agent A，在 Chat tab 输入未提交；然后关闭 Chat tab；之后再次在 sidebar 选中 A 并激活 Chat tab，**When** 页面重新渲染，**Then** Chat tab 上方 transcript 仍对应 A，且 transcript 内容在该次关闭前后的最近可观察快照一致。

### AC-5
AC-FR1306-05

- **Given** Chat 输入框可输入文本，**When** 用户提交以 `/` 开头或 `!` 开头的输入，**Then** 输入按普通文本发送，Web 不识别为 harness 命令、不触发 shell 命令、不返回假成功提示。

---

<a id="ac-fr-1307"></a>
## FR-1307 Agent 切换与 transcript 隔离

### AC-1
AC-FR1307-01

- **Given** 当前 sidebar 选中 Agent A 且 Chat tab 显示 A 的 transcript，**When** 用户在 sidebar 选中 Agent B，**Then** Chat tab transcript 切换到 B 的会话，A 的 transcript 不再可见。

### AC-2
AC-FR1307-02

- **Given** A、B 两个 Agent 都有 transcript，**When** 用户在 A、B 间来回切换三次，**Then** 两次显示 A 时 transcript 一致，两次显示 B 时 transcript 一致；不出现 A 内容混入 B 或 B 内容混入 A。

### AC-3
AC-FR1307-03

- **Given** A、B 两个 Agent 在 transcript 中各有独立消息，**When** 通过公开 API 查询 Agent transcript 列表，**Then** A 的 transcript 与 B 的 transcript 在持久化观察出口分别独立可查。

### AC-4
AC-FR1307-04

- **Given** 用户尝试通过手动拼接 URL 访问未注册的 Agent X（/chat?agent=X）触发 transcript 加载，**When** 提交请求，**Then** Web **回退到默认 Agent（Maestro）**并显示对应 transcript；不返回 X 的 transcript；不抛出 JS 异常；URL 中多余的 agent 参数可保留但被忽略。

---

<a id="ac-fr-1308"></a>
## FR-1308 Dev Docs sidebar 目录树

### AC-1
AC-FR1308-01

- **Given** `.louke/project/specs` 下存在 N 个 spec 目录（v0.11-001、v0.12-001、v0.13-001…），**When** 用户点击 Dev Docs，**Then** sidebar 出现与这些 spec 目录一一对应的一级菜单项，目录数 N 与显示菜单数 N 相等。

### AC-2
AC-FR1308-02

- **Given** Dev Docs sidebar 已渲染，**When** 页面首次加载完成，**Then** 所有一级菜单初始处于折叠状态（DOM 中折叠 aria-expanded=false 且子项不可见）。

### AC-3
AC-FR1308-03

- **Given** Dev Docs sidebar 中某一 spec 目录当前为展开状态，**When** 用户点击该目录的折叠控件（toggle）或再次点击该目录的标签，**Then** 目录**就地切换**展开/折叠（点击 toggles 展开 ↔ 折叠）；同时浏览器 `localStorage`（key=`louke.dev-docs.tree.<spec-id>`）记录最新状态，关闭 tab、刷新页面、切到其他 toolbar 项后再切回 Dev Docs 时按已记录的展开/折叠状态恢复（每次 tab 重新激活时都恢复一次，不要求跨用户 / 跨设备持久化）。

### AC-4
AC-FR1308-04

- **Given** 展开某一 spec 目录，**When** 列出叶子项，**Then** 叶子项名称与该 spec 目录下的 Markdown 文件名（去掉 .md 后缀）一一对应，且无重名/缺失。

---

<a id="ac-fr-1309"></a>
## FR-1309 Dev Docs 文档展示、预览与交叉引用（复用 v0.11-001 FR-0801 / v0.9-001 FR-0200 / v0.9-001 FR-0700）

### AC-1
AC-FR1309-01

- **Given** 选中 Dev Docs 中一个 Markdown 文档，**When** main panel 渲染完成，**Then** 文档以与 v0.11-001 FR-0801 / AC-FR0801-* 一致的展示能力渲染（标题层级、列表、代码块、表格可识别）。

### AC-2
AC-FR1309-02

- **Given** Dev Docs 文档展示视图激活，**When** 切换到分栏编辑器/实时预览模式，**Then** 左右分栏与同步滚动行为沿用 v0.9-001 FR-0200（编辑与预览同步滚动）。

### AC-3
AC-FR1309-03

- **Given** Dev Docs 文档正文出现形如 `FR-0801`、`NFR-0101`、`US-1301` 的交叉引用，**When** 鼠标点击该引用，**Then** Web 跳转到目标章节锚点（hash 改变、目标章节进入可视区）。

### AC-4
AC-FR1309-04

- **Given** Dev Docs 视图渲染完成（覆盖 writable allowlist 内的 `story.md` / `spec.md` / `acceptance.md` 与所有只读文件），**When** 检查 UI 中**所有**按钮、菜单项、tab、右键菜单项、toolbar icon 与键盘快捷键映射（含编辑模式与只读模式），**Then** **不**存在任何 "AI 辅助编辑" / "AI rewrite" / "AI assist" / "AI 续写" / "AI suggestion" 等入口；Editor 分栏仅用于只读浏览与实时预览；Dev Docs 全集（writable allowlist 与只读）永不暴露 AI 写。

### AC-5
AC-FR1309-05

- **Given** Dev Docs sidebar 选中一个 spec_id 下的文档，**When** 检查目标文件的 "Save" 按钮可见性，**Then** 仅当目标路径属于 `.louke/project/specs/<spec-id>/{story.md, spec.md, acceptance.md}` allowlist 时显示 "Save" 按钮与编辑入口；同一 spec 目录下的 `test-plan.md`、`architecture.md`、`interfaces.md`、`gap-analysis.md`、`m-lock.md` 及任何其它文件**不**显示 Save 按钮、不显示编辑入口；如直接对后者发起 PUT/POST/PATCH/DELETE 写请求，服务端返回 4xx `PATH_NOT_ALLOWED`，文件不被覆盖。

### AC-6
AC-FR1309-06

- **Given** Dev Docs allowlist 内的一个文件 F 处于 dirty 状态（编辑器 `body_md` 与上次成功保存的 bytes 不同），**When** 用户点击 "Save" 并提交 `{body_md, expected_mtime}`，**Then** 服务端返回 HTTP 200，响应体含 `{path, sha256, saved_at, mtime}`，其中 `sha256` = `sha256(磁盘上 F 实际写入后的完整 UTF-8 bytes)`（即直接对 `open(F).read()` 或 `cat F` 的输出做 SHA-256，**不**对 rendered preview 或 HTML 做哈希）；UI 立即用响应 `sha256` 重 GET 完整 `body_md`，且 `sha256(GET 回来的 body_md)` == 响应 `sha256` == `sha256(磁盘 bytes)`，按钮回到 `disabled`；**保存过程中不得抽取、重排或规范化 inline-discussion**（`>`/`>>`/speaker-tag blockquote marker 必须按原样保留在 `body_md` 中，与前端编辑内容一致）。

### AC-7
AC-FR1309-07

- **Given** Dev Docs allowlist 内的某个 Markdown 文件正文中存在 Agent-attached inline-discussion（表现为 `>`/`>>`/speaker-tag blockquote marker），**When** main panel 渲染该文件，**Then** inline-discussion 由 Vditor/Workbench Client 通过读取 Markdown 正文中的 blockquote + speaker-tag marker 直接渲染；**不**存在 `louke.inline_discussions[]` 之类的 frontmatter discussion 列表读取路径，也**不**在 GET/PUT 响应中返回单独的 `discussions[]` 数组；编辑 reply 本质是在 Markdown body 中编辑 marker，通过同一 Save 流程落盘。

### AC-8
AC-FR1309-08

- **Given** Dev Docs allowlist 内的一个文件 F 已被加载（前端持有其 `sha256=H_load`、`mtime=M_load`），**When** 编辑器内容与 `H_load` 对应的 bytes 一致（无 dirty），**Then** "Save" 按钮处于 `disabled`（点击不发出任何写请求）；**When** 用户在编辑器中输入/删除/修改任意字符使内容偏离 `H_load` 对应的 bytes（dirty），**Then** 按钮立即恢复 `enabled`，按钮 label 反映 dirty 态（例如文案包含 "Save" + dirty 标记），且**不**做自动保存、防抖保存或离开页面保存。

### AC-9
AC-FR1309-09

- **Given** Dev Docs allowlist 内的一个文件 F 当前处于 dirty 状态（编辑器的 `body_md != sha256=H_load` 对应的 bytes）、磁盘 mtime 为 `M_load`，**When** 用户点击 "Save" 但服务端返回 4xx（如 `VALIDATION_FAILED` / `TOO_LARGE` / `PATH_NOT_ALLOWED`），**Then** 响应体含 `code` 与可读 `message`；UI 弹出错误 toast；**编辑器中用户已输入的内容保持不丢失**（用户关闭错误 toast 后仍可继续编辑或重试 Save）；磁盘文件 F 的 mtime 保持 `M_load` 未变化（通过 `stat -c %Y F` 或等价 API 校验）；且未对 F 落盘新内容。

### AC-10
AC-FR1309-10

- **Given** Dev Docs allowlist 内的一个文件 F，前端持有 `expected_mtime = M_load`，**And** 外部进程在用户编辑期间已修改 F（磁盘 mtime 已变为 `M_external`，且 `M_external != M_load`），**When** 用户点击 "Save" 提交 `{body_md, expected_mtime=M_load}`，**Then** 服务端返回 HTTP 409，响应体 `code=CONFLICT`；UI 弹出冲突提示"文件已被外部修改"，并提供**两个**互斥动作：(a) "重新加载并放弃我的编辑"——触发重 GET 并用服务端最新 bytes 覆盖编辑器（dirty 状态清零、按钮回到 `disabled`）；(b) "仍要覆盖"——**必须**经二次确认（模态确认框），确认后以 `force=true` 重发同一 `{body_md, expected_mtime=M_load}`，服务端接受并返回 200 + 新 `sha256`/`saved_at`/`mtime`；放弃二次确认则不发写请求。

### AC-11
AC-FR1309-11

- **Given** Dev Docs allowlist 内的一个文件 F（含一 fixture：**末尾无 `\n` 的 Markdown**——例如 `tests/fixtures/dev-docs/no-trailing-newline.md` 仅以非换行字符结尾），**When** 用户在编辑器中提交 `{body_md=<该 fixture 的完整字节序列，含末尾字符但不含末尾换行>, expected_mtime=<当前 mtime>}` 并点击 "Save"，**Then** 服务端返回 HTTP 200，响应 `sha256` = `sha256(磁盘写入后 F 的完整 bytes)`；且满足以下四点同时成立：
  1. `sha256(PUT 请求中的 body_md UTF-8 bytes)` == 响应 `sha256`
  2. `sha256(磁盘 F 实际 bytes)` == 响应 `sha256`（即服务端没有在底层自动追加 `\n` 或 `\r\n`，否则失败）
  3. UI 用响应 `sha256` 重 GET 后，`sha256(GET 回来的 body_md UTF-8 bytes)` == 响应 `sha256` 且 `body_md` 末尾仍然**不**含 `\n`
  4. 后续操作：关闭 Dev Docs tab → 浏览器刷新页面 → 重新打开同一文件 F → 拉取的 `body_md` 与 `sha256` 仍一致；并对 `<project>/.louke/serve` 进程执行 kill + relaunch 后重新打开 F，内容与 `sha256` 仍一致（覆盖关闭/刷新/重启三种持久化往返）。

  测试 fixture 要求：除现有 allowlist 内/外样本外，必须新增一个**无尾换行** fixture（文件末字节不为 `\n` 且不为 `\r\n`），且新增测试显式覆盖"服务端不应自动补尾换行"的负面断言。

> **Prism** [RESOLVED]: FR-1309 的验收仍未闭合。AC-5 与 AC-4 都只验证"无 AI 辅助入口"，语义重复；AC-7 只覆盖成功保存，却把不可观察的"preview bytes digest"当断言。请用一个 AC 保留 AI negative capability，并分别补齐：dirty/Save disabled 状态、4xx 后编辑不丢失、409 的 reload/force 二次确认、关闭/刷新/重启后的 byte-exact SHA round-trip。成功断言应比较 PUT 的完整 Markdown UTF-8 bytes、磁盘实际 bytes、响应 SHA 与重 GET 的完整 `body_md`，而不是 rendered preview digest；同时加入无尾换行 fixture，防止底层自动补换行后仍误通过。


>> **sage**: Applied: AC-4/5 merged; AC-7 split into 09-12 (dirty, 4xx preserve, 409 + force confirm, byte-exact SHA round-trip incl. no-trailing-newline fixture); AC-FR1309-07 now asserts sha256 over actual disk bytes.

<a id="ac-fr-1310"></a>
## FR-1310 End User Docs 文档树与基础编辑（复用 v0.11-001 FR-0801 / v0.9-001 FR-0200）

### AC-1
AC-FR1310-01

- **Given** End User Docs 内容目录存在多个 Markdown 文件，**When** 用户点击 End User Docs，**Then** sidebar 出现与该目录结构对应的文档树，文档树可多级展开；规范根为 `<project>/.louke/end-user-docs/`。

### AC-2
AC-FR1310-02

- **Given** 选中 End User Docs 中一个 Markdown 文件，**When** main panel 渲染完成，**Then** 至少提供展示模式与编辑模式两种视图，并能在两种视图间切换；编辑模式下输入会进入实时预览分栏。

### AC-3
AC-FR1310-03

- **Given** End User Docs 编辑模式激活，**When** 用户修改 Markdown 内容，**Then** 实时预览分栏随输入同步刷新（与 v0.9-001 FR-0200 的同步滚动/同步渲染行为一致）。

### AC-4
AC-FR1310-04

- **Given** End User Docs 视图渲染完成，**When** 检查 UI，**Then** 不暴露任何 AI 辅助编辑按钮、菜单或快捷键。

### AC-5
AC-FR1310-05

- **Given** End User Docs 编辑模式激活，**When** 检查 UI，**Then** 显式 "Save" 按钮可见；按钮在编辑器内容自上次加载或上次成功保存以来无变化时处于 `disabled` 状态；本期不做自动保存 / 防抖保存 / 离开页面保存。

### AC-6
AC-FR1310-06

- **Given** 编辑器内容相对上次加载/保存有变化，**When** 用户点击 "Save" 按钮，**Then** 浏览器发出写请求，服务端返回 HTTP 200，响应体含 `sha256`（保存后文件 digest）与 `saved_at`（ISO-8601 UTC）；前端用返回的 `sha256` 重新拉取预览并刷新分栏；按钮在保存成功后回到 `disabled` 状态（直到内容再次变化）。

### AC-7
AC-FR1310-07

- **Given** 编辑器内容超过 1 MiB 或文件名 / 路径违反 FR-1310 规则（如非 `.md`、含 `..`、绝对路径、与现有树冲突），**When** 用户点击 "Save"，**Then** 服务端返回 4xx（413 或 400），响应体含 `code`（`TOO_LARGE` / `VALIDATION_FAILED` / `PATH_NOT_ALLOWED`）与可读 `message`；UI 显示错误 toast；编辑器内容保持不丢失；文件 mtime 未变化。

### AC-8
AC-FR1310-08

- **Given** 自用户加载文件后文件 mtime 已被外部进程修改，**When** 用户点击 "Save" 并提交客户端持有的 `expected_mtime`，**Then** 服务端返回 HTTP 409，响应体 `code=CONFLICT`；UI 弹出冲突提示"文件已被外部修改"，并提供"重新加载并放弃我的编辑"与"仍要覆盖"两个动作；选"仍要覆盖"必须经二次确认后才发出写请求。

### AC-9
AC-FR1310-09

- **Given** 用户在编辑模式成功保存了一个文件 F（响应中返回 `sha256=H`，`saved_at=T`），**When** 用户关闭 End User Docs tab → 浏览器刷新页面 → 重新打开 End User Docs → 选中同一文件 F，**Then** main panel 渲染的文件字节与 `sha256=H` 完全一致（通过 `sha256sum` 校验）；最近一次保存以来的编辑内容被持久化，不丢失。

### AC-10
AC-FR1310-10

- **Given** 用户尝试保存到 `<project>/.louke/project/specs/...`、`<project>/.louke/project/acceptance.md` 或项目根的其它 `.md` 配置文件（如 `story.md` / `spec.md` / `test-plan.md` / `architecture.md` / `interfaces.md` / `project.toml`），**When** 提交写请求，**Then** 服务端返回 4xx（`PATH_NOT_ALLOWED`），文件不被覆盖；UI 显示错误 toast。

### AC-11
AC-FR1310-11

- **Given** user has saved file F (sha256=H, saved_at=T), then **louke serve** process restarts (kill + relaunch), **And** user reopens same file F, **Then** main panel renders the same bytes (sha256=H verified) with no data loss.

### AC-12
AC-FR1310-12

- **Given** user is viewing/editing an End User Docs file F that contains at least one Agent-attached inline-discussion represented as `>`/`>>`/speaker-tag blockquote markers in the Markdown body, **When** main panel renders F, **Then** each inline-discussion is rendered as a visible UI element near its anchor (read) **directly from the Markdown body via blockquote + speaker-tag markers**; **And** when user clicks the inline-discussion body and submits a new reply, **Then** the reply is persisted by editing the existing `>`/`>>`/speaker-tag markers in the Markdown body and saving the entire document through the same Save flow as any other content edit; **no** separate `louke.inline_discussions[]` frontmatter list is read or written; **no** `discussions[]` field appears in GET/PUT response bodies; **no** dedicated `/discussions/{id}/replies` endpoint exists in v0.13. No "resolved" status is shown.

---

<a id="ac-fr-1311"></a>
## FR-1311 Wiki 导航与只读渲染

### AC-1
AC-FR1311-01

- **Given** Wiki 内容目录存在至少一个 Markdown 页面，**When** 用户点击 Wiki toolbar 项，**Then** sidebar 出现 Wiki 导航树，main panel 打开或激活 Wiki tab。

### AC-2
AC-FR1311-02

- **Given** Wiki tab 处于激活，**When** 用户在 sidebar 选中一个 Wiki 页面，**Then** main panel 渲染该 Markdown 页面（标题、段落、列表、代码块等基本结构可识别）。

### AC-3
AC-FR1311-03

- **Given** Wiki tab 激活且已渲染某页面 P，**When** 用户关闭 Wiki tab 后再激活 Wiki tab（不切换 sidebar 选中），**Then** Wiki tab 仍渲染同一页面 P。

### AC-4
AC-FR1311-04

- **Given** Wiki tab 渲染完成，**When** 检查 UI，**Then** 不暴露编辑、创建、删除、重命名等写操作入口（按钮、菜单、右键菜单、URL 参数）。

### AC-5
AC-FR1311-05

- **Given** Wiki tab 激活，**When** 用户在 sidebar 选中一个未注册的 Wiki 页面路径，**Then** main panel 显示可读的 NotFound / "无该页面" 降级提示，HTTP 状态非 500，且 URL 不会触发写请求。

---

<a id="ac-fr-1312"></a>
## FR-1312 Wiki 结构复用与 NotFound / 未知页面降级（复用 v0.11-001 FR-0301）

### AC-1
AC-FR1312-01

- **Given** Wiki 目录存在 v0.11-001 FR-0301 规定的入口（首页、story、spec、test-plan、architecture、interfaces、技术决定、FAQ、项目信息），**When** 在 sidebar 依次点开每一项，**Then** 每一项均能渲染对应 Markdown，且渲染行为与 v0.11-001 FR-0301 已批准字段一致（不在 Web 层重新定义其内容）。

### AC-2
AC-FR1312-02

- **Given** sidebar 选中一个不存在的 Wiki 页面路径，**When** 渲染该路径，**Then** main panel 显示可读的 NotFound / "无该页面" 提示，HTTP 状态非 500，toolbar / sidebar / 其他 tab 均不受影响。

### AC-3
AC-FR1312-03

- **Given** Wiki 内容目录新增了一个 v0.14 / v0.15 才会引入的页面（不在 v0.11-001 FR-0301 列表内），**When** 在 v0.13 Web 中选中该页面，**Then** Web 以通用 Markdown 渲染方式呈现页面内容，不要求 schema 升级、不抛错、不留空白 tab。

### AC-4
AC-FR1312-04

- **Given** Wiki tab 渲染完成，**When** 检查 UI，**Then** 任何渲染路径下都不暴露 Wiki 编辑 / 创建 / 删除 / 重命名入口（按钮、菜单、右键菜单、URL 参数均不出现）；底层 HTTP API **按 v0.11-001 / v0.9-001 已批准合同**继续对外提供服务，v0.13 不在服务端关闭、收紧或替换这些接口。

---

<a id="ac-fr-1313"></a>
## FR-1313 Runs sidebar 与 workflow graph（复用 v0.12-001 FR-1001 / FR-1201）

### AC-1
AC-FR1313-01

- **Given** workspace 中存在至少一个 Project，**When** 用户点击 Runs toolbar 项，**Then** sidebar 出现 Projects 导航，并按 v0.12-001 FR-1001 区分当前项目与历史项目；包含创建新项目入口。

### AC-2
AC-FR1313-02

- **Given** Runs sidebar 中存在至少一个 run，**When** 用户选中某 run，**Then** main panel 渲染该 run 绑定的 workflow graph（节点、边、当前节点高亮等元素），且 graph 内容来自 run 绑定的 definition id/version，不随当前代码库升级而漂移。

### AC-3
AC-FR1313-03

- **Given** Runs sidebar 中存在至少一个 run，**When** 用户尚未选中任何 run，**Then** main panel 显示空状态（如 "选择一个 run 以查看 workflow graph"），而非空白、崩溃或 500。

### AC-4
AC-FR1313-04

- **Given** main panel 已渲染 run R1 的 workflow graph，**When** 用户切换 sidebar 选中到 run R2，**Then** main panel 同步刷新为 R2 的 workflow graph；R1 的 graph 不再可见。

---

<a id="ac-fr-1314"></a>
## FR-1314 stage 节点状态徽标（review verdict / gate / author）

### AC-1
AC-FR1314-01

- **Given** 一个 run 的 workflow graph 渲染完成，**When** 列出每个 stage 节点的可视化状态，**Then** 至少可区分：已完成、当前执行、等待人类、阻塞、失败、未开始、已跳过七种状态之一（颜色、徽标或图标可观察）。

### AC-2
AC-FR1314-02

- **Given** 一个 stage 节点存在 review verdict，**When** 渲染该节点，**Then** 节点上可观察到 verdict 的可视化标识（PASS / REJECT / WAIVED 或通用降级标识），不直接显示原始 verdict JSON。

### AC-3
AC-FR1314-03

- **Given** 一个 stage 节点对应一个 gate 或 author 步骤，**When** 渲染该节点，**Then** 节点上可观察到 gate pass/fail 与 author result 的可视化标识（颜色、徽标或图标）。

### AC-4
AC-FR1314-04

- **Given** workflow graph 渲染完成，**When** 检查节点 DOM，**Then** 节点上不得直接堆叠 stage-results 原始 JSON；原始 JSON 必须通过点击进入详情查看。

---

<a id="ac-fr-1315"></a>
## FR-1315 stage artifact 只读视图（复用 v0.12-001 FR-1201 / FR-1901 / FR-2201）

### AC-1
AC-FR1315-01

- **Given** workflow graph 已渲染某 run，**When** 用户点击其中任意 stage 节点，**Then** main panel 打开该 stage 的只读 artifact 详情视图（侧栏 / 抽屉 / 弹层任一即可，但必须是非模态或显式关闭可恢复 graph 的视图）。

### AC-2
AC-FR1315-02

- **Given** stage artifact 视图已打开，**When** 用户检查视图字段，**Then** 至少可见 digest、verdict、required reviewer、review 结论四个字段，且字段命名/取值与 v0.12-001 FR-1201 / FR-1901 / FR-2201 已批准 contract 一致。

### AC-3
AC-FR1315-03

- **Given** stage artifact 视图已打开，**When** 检查 UI 与对应 API，**Then** UI 不暴露编辑、提交、删除、回退、waive 等写操作入口；底层 stage / artifact 写 API **按 v0.12-001 FR-1201 / FR-1901 / FR-2201 已批准合同**对任何调用方（curl / CLI / 其他客户端）继续提供服务，v0.13 不在服务端关闭、收紧或替换这些接口；UI 仅是"不暴露入口"，并不否定上游 contract 的写入能力。

### AC-4
AC-FR1315-04

- **Given** 一个 stage 节点对应 v0.14 reflow 引入的、未在 v0.12-001 已批准字段中的 stage 类型，**When** 用户点击该节点，**Then** 视图显示可读的降级内容（如"未知 stage 类型"+ 现有通用字段），不返回 500 或空白。

---

<a id="ac-fr-1316"></a>
## FR-1316 未知 stage / status / result kind 的通用降级

### AC-1
AC-FR1316-01

- **Given** Runtime 持久化中出现 v0.13 未识别的 stage 名称、status 值或 result kind，**When** Web 加载对应 run / artifact，**Then** UI 以通用占位文本或标签渲染未知值（如"未知 stage: foo"），且不抛出 JS 异常、不返回 500。

### AC-2
AC-FR1316-02

- **Given** 任意未知 stage / status / result kind 出现，**When** 检查 toolbar、sidebar、main panel、tab 区域，**Then** 任何区域不得出现空白页、崩溃日志或 5xx 错误；其他已知 stage 仍正常渲染。

### AC-3
AC-FR1316-03

- **Given** UI 渲染未知值，**When** 用户检查对应 DOM，**Then** 该未知值被显式标记（如 `data-fallback="unknown"`、`aria-label="未知 status"`），便于后续调试与回归。

### AC-4
AC-FR1316-04

- **Given** 模拟 v0.14 reflow 引入一个全新 status 值 X，**When** Web 加载包含 X 的 run，**Then** Web 仍能完成 graph 渲染与 stage artifact 只读视图展示，且用户可识别 X 为"未知 status"而非正常业务状态。

---

<a id="ac-fr-1317"></a>
## FR-1317 浏览器主旅程端到端（US-1319）

### AC-1
AC-FR1317-01

- **Given** 一个含 fixture 项目与至少一个 run 的 workspace，**When** 浏览器（Playwright / Chromium headless 或受支持桌面浏览器）打开主页面，**Then** toolbar、sidebar、main panel 渲染完成且至少含一个 tab。

### AC-2
AC-FR1317-02

- **Given** 浏览器已加载主页面，**When** 测试依次点击 Dev Docs、Wiki、Runs 三个 toolbar 项，**Then** 每次切换后 sidebar 与 main panel 同步刷新，且 Dev Docs、Wiki、Runs tab 同时保留在 main panel 中可切换。

### AC-3
AC-FR1317-03

- **Given** Dev Docs 已激活，**When** 测试展开一个 spec 目录并选中一个 Markdown 文档，**Then** main panel 渲染该文档且 FR/NFR/Story 交叉引用可点击跳转；End User Docs / Wiki 任选其一重复一次均能完成打开-渲染流程。

### AC-4
AC-FR1317-04

- **Given** Runs 已激活，**When** 测试选中至少一个 run 并点击其 workflow graph 中至少一个 stage 节点，**Then** stage artifact 只读视图打开并显示 digest / verdict / required reviewer / review 结论；旅程全部步骤无 JS 异常、无网络 5xx、无空白页，且可在 CI 中重复运行通过。

---

<a id="ac-fr-1318"></a>
## FR-1318 v0.13 不实现范围（US-1320）

### AC-1
AC-FR1318-01

- **Given** v0.13 Web UI 已渲染完成，**When** 扫描所有可见 UI 元素（toolbar、sidebar、tab、右键菜单、按钮、菜单项），**Then** 不得出现：workflow 回退、workflow waive、CI report 中断、夜间重构分支、完整 Settings（版本更新 / 服务器配置 / S-A-B 模型绑定具体功能）、harness `/` 命令、shell `!` 命令、End User Docs AI 辅助编辑、UI i18n 切换器。

### AC-2
AC-FR1318-02

- **Given** 默认 settings 与 accounts 菜单渲染完成，**When** 列出其条目，**Then** 不得出现上述九类能力的具体入口；设置只展示可扩展占位，账号只展示 logout 等本期允许项。

### AC-3
AC-FR1318-03

- **Given** 本版本 README、UI 文案或内置帮助文案，**When** 关键词扫描（grep）"rollback"、"waive"、"CI report abort"、"nightly refactor"、"harness /"、"shell !"、"AI 辅助"、"i18n"，**Then** 不得出现对用户承诺上述能力已实现的文案。
