u# 最小首次设置、Project 创建引导与 Project Status — 需求规格

- **规格 ID**：`v0.14-004-workspace-onboarding-workflow-status`
- **关联 Story**：`STR-1405`
- **Story SHA-256**：`f2595e5aa1c71ca829fcc2d27458aa599381d2ca51bf6e25e85df422000475af`
- **创建日期**：2026-07-24
- **状态**：草稿
- **有效 FR 数量**：16（上限 30）

> **职责边界**：本文只描述需求本身。Story 的产品叙事与主路径保留在 `story.md`；可观察断言写入 `acceptance.md`。本文取代本 Spec 先前基于连续多步骤 Setup Wizard 的草稿，不改变 `v0.14-001` 至 `v0.14-003` 未在下表明确接入或裁决的工作流合同。

## 产品集成与继承边界

| 主题 | 本次接入的宿主产品 surface / 合同 | 唯一产品结果 |
|---|---|---|
| Setup | 现有 `/setup`、首用户身份和 Setup 状态 | `/setup` 只承担首用户创建与真实 OpenCode 模型验证；Git、GitHub、repository、release 和 Project 不属于首次 Setup |
| 登录落点 | 现有 Workbench、`/projects` 与 authenticated entry resolver | 登录后在 Workbench 的 Projects 上下文显示活跃 Project Status；没有活跃 Project 时显示空 Project 与 `New Project` |
| New Project | 现有 `/projects/new` preview/confirm、`v0.14-001 FR-0300—FR-0500` | `New Project` 先执行按需环境门禁，再预览 Story/版本；确认后沿用同一 Project/release/WorkflowRun 身份并由 Scribe 形成 `story.md` |
| Project Status | 现有 Runtime workflow read model、`v0.14-001 FR-0600/FR-1700`、`v0.14-002` 与 `v0.14-003` 阶段合同 | Workbench main panel 突出当前节点，并以可导航的线性时间线展示 Runtime 权威的完整尝试历史、选中节点详情和合法回拨；新 Project 使用 `M-REQ-APPROVAL`，历史 `M-LOCK-1` 只作为同一节点的兼容别名，不建立第二节点或第二状态机 |
| Guide | 现有 Guide projection 与 session | Guide 在 Projects sidebar 中解释当前 Project 或空 Project 及环境检查；Runtime、Scribe 和各阶段 owning Agent 仍是事实与工件 authority |
| Dev Docs | 现有 Story 文档编辑/查看 surface 与稳定文档深链 | 创建成功后直接加载新 Project 的最新 `story.md`；兼容路由解析到同一对象，不创建孤立结果页 |

---

## 功能需求

### FR-0001 Setup 未完成时的全局用户入口保护

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-01`、`BS-03`、Story §3.1 / §4.1
- **交付入口**：`/setup`；任一用户功能地址

当当前 workspace 没有持久化的 Setup 完成状态时，系统必须将登录页、Workbench、Projects、Project/Run/文档深链及其他用户功能地址统一带到 `/setup`。呈现或提交 Setup 所必需的静态资源和内部接口可以工作，但不得形成绕过 Setup 的用户路径。

Setup 已完成时不得继续以首次设置为由拦截用户；Setup gate 只读取当前 workspace 的持久化状态，不得由 cookie、Guide 对话、OpenCode executable 存在或首用户单项完成来替代。

---

### FR-0101 首用户创建与可恢复连续性

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-01`、Story §3.1
- **交付入口**：`/setup`

当 workspace 尚无用户时，`/setup` 必须允许访问者创建唯一首个本地用户。创建成功后，该身份必须立即持久化并用于继续同一次 Setup；后续模型检查失败、页面刷新或服务重启均不得要求重新创建首用户。

首用户已存在时不得再次提供创建另一个“首用户”的成功路径。重复提交必须解析为同一已发生结果或明确冲突，不得产生重复身份；首用户建立本身不得把 Setup 标记为完成。

---

### FR-0201 OpenCode 与至少一个模型的真实运行验证

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-02`、Story §3.1、`D-02`；宿主能力 `louke.models.probe_model`
- **交付入口**：`/setup`

首用户建立后，Runtime 必须在当前 workspace 中执行一次无 Louke 产品副作用的最小 OpenCode 请求，并只在至少一个已配置模型真实成功响应时判定验证通过。仅发现 executable、读取 provider credential、列出模型或读取静态配置均不得判定通过。

若 OpenCode 不可调用、所有候选模型均失败、认证或网络失败、调用超时或结果无法确认，用户必须留在 `/setup`，看到可定位到 OpenCode/模型验证的非秘密原因和重试入口。重试不得创建 Project、Git/GitHub 资源、release 或 workflow。

---

### FR-0301 Setup 完成记录与 Workbench 交接

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-01`、`BS-03`、Story §3.1 / §4.1
- **交付入口**：`/setup` → Workbench Projects

系统只有在首用户已持久化且 FR-0201 的真实模型验证成功后，才可原子写入当前 workspace 的 Setup 完成状态。完成后，当前用户必须能够直接继续到 Workbench 的 Projects 上下文；不得再要求 Git、GitHub CLI、repository、release 或 Project 配置作为 Setup 完成条件。

刷新、重启和后续登录必须复用该完成状态，不重复首次 Wizard 或模型调用。Setup 状态写入失败或结果不确定时仍视为未完成，并从已成功的首用户步骤恢复，而不得伪报成功或产生两个完成记录。

---

### FR-0401 登录后的 Projects 状态落点

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-04`、Story §3.2；宿主 `entry_resolver`、`/projects`
- **交付入口**：登录成功 → Workbench Projects

Setup 已完成的用户登录后，系统必须在 Workbench 中进入 Projects 上下文。若 Runtime 存在唯一活跃 Project，main panel 必须显示该 Project 的 Project Status；若不存在活跃 Project，main panel 必须显示空 Project 状态、用途提示和 `New Project` 主动作。

活跃 Project 存在时不得同时把创建第二个主 Project 作为成功主路径。若持久事实无法安全确定唯一活跃 Project，系统必须显示需要处理的冲突并阻止选择或创建，而不得按列表顺序、最近访问记录或 Guide 推断一个 Project。

---

### FR-0501 Projects Sidebar 的 Guide 上下文

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-05`、Story §3.2—§3.3、`D-05`；Human 2026-07-24 澄清；宿主 Guide projection
- **交付入口**：Workbench Projects sidebar

Projects 上下文必须在 sidebar 提供 Guide session。存在活跃 Project 时，会话必须绑定该 Project 身份和当前 Runtime 状态；空 Project 时，会话必须明确处于空 Project 上下文，并能够解释 `New Project`、环境门禁及其修复位置。

Runtime 在环境检查期间必须把当前步骤和结果投影给同一 Guide session。每当检查产生阻断错误，chat window 必须先把 Runtime 的失败步骤与结果呈现为可与建议区分的权威状态，再由 Guide 无需用户输入即自动生成针对该错误的建议；建议可以渐进呈现，并必须说明失败影响、修复方法和 owning surface。用户仍可继续追问，但主动建议不得以用户先发送消息为前提。

Guide 可以解释影响、提供帮助并导航到 owning surface，但不得自行把检查标为通过、未经授权安装工具或改变认证、创建 Project、生成 Story、选择活跃节点、执行回拨或改写 workflow 状态。相同检查 revision 的重复投影不得反复产生同一主动建议；新的失败结果或重试结果可以产生对应的新状态与建议。

---

### FR-0601 New Project 的按需环境门禁编排

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-06`、Story §3.3、`D-01`、`D-04`
- **交付入口**：空 Project 的 `New Project` → Environment Wizard

只有用户从空 Project 点击 `New Project` 后，Runtime 才可启动模态 Environment Wizard；空 Workbench 和首次 Setup 不得预先强制执行该门禁。Runtime 必须在后台依次确认 GitHub CLI 可执行、GitHub 认证与必需 scopes，以及当前 workspace 的 Git repository/binding。

通过的步骤不得展开成要求用户逐项确认的页面；UI 只需在检查进行时说明正在检查，并在某一步未通过时显示该失败步骤、影响和重试/修复入口。任一必要检查失败或结果不确定均必须停留在 Wizard 并阻止 Story/版本输入与 Project 创建；重新检查通过后才可继续。

---

### FR-0701 GitHub CLI、认证与 Scope Readiness

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-06`、Story §3.3 / §4.1、`D-06`；宿主 readiness surface
- **交付入口**：同 FR-0601

Runtime 必须先确认 `gh` 已安装且可执行，再依据 `gh auth status` 的实际结果确认目标 GitHub host 已登录，并验证当前认证的 token scopes 同时包含 `gist`、`project`、`repo` 和 `workflow`。未安装、不可执行、未登录、host/身份无法确定或缺少任一 scope 均不得通过门禁。

失败结果必须明确指出未满足的项及其对新 Project 的阻断影响，并可由 Guide 提供安装、登录或补齐权限的帮助；系统不得未经 Human 授权自动安装工具或改变认证。四项 scope 齐全只表示本门禁通过，后续 GitHub 资源、push、workflow 或 release 操作仍须以各自真实结果为准。

---

### FR-0801 Git Repository 初始化、绑定与可用主分支

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-06`、`BS-07`、Story §3.3、`D-01`；继承 `v0.14-001 FR-0400`
- **交付入口**：同 FR-0601；失败时的 repository URL 输入

Runtime 必须确认当前 workspace 是已初始化的 Git repository，并具有可验证且与当前 workspace 一致的 GitHub repository binding。workspace 尚非 Git repository，或已初始化但缺少可验证 binding 时，Wizard 必须请求 repository URL；只有用户提交并继续后，Runtime 才可在当前 workspace 范围内执行初始化/绑定，并在重新检查实际结果通过后继续。

Repository binding 只有在 remote 身份可确认且后续 Foundation 能取得可用的权威主分支时才算通过。对用户提供的新建空 repository，获确认的初始化/绑定动作必须安全建立并验证一个可供 Foundation 使用的 canonical `main`；对已有 remote 的缺失、冲突、歧义或 divergent 主分支不得覆盖或猜测。任何部分成功或结果不确定必须保留可恢复事实并继续阻断，不得提交 Louke secret、运行状态或无法归属的用户文件来制造可用分支。

---

### FR-0901 Story 与 Release Version 的浏览器草稿

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-08`、Story §3.3、`D-07`
- **交付入口**：Environment Wizard 通过后的 New Project 输入步骤

环境门禁通过后，用户必须能输入非空 Story 设想和 release version。系统必须在进入预览前将未确认输入保存为当前浏览器中的草稿；刷新、关闭后返回或创建前中断时，同一浏览器应恢复草稿与可继续位置。

草稿不得创建 workspace 级正式文档、Project、WorkflowRun、GitHub Project、release branch 或阶段状态。跨浏览器/设备或浏览器数据被清除后的恢复不属于承诺；恢复时易变的环境结果必须重新确认，浏览器草稿本身不得绕过 FR-0601 门禁。

---

### FR-1001 Story/版本预览与无副作用取消

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-08`、Story §3.3；继承 `v0.14-001 FR-0300`
- **交付入口**：New Project 预览

对通过基础校验的 Story 与 release version，系统必须在任何 Project/release 副作用前展示本次 Story、规范化后的版本身份、workspace/repository 身份及 `Create`、`Cancel` 动作，使用户能核对将要创建的 Project。

Preview 必须绑定当前输入、环境事实与 preview revision，且不得创建 Project、Story 文件、WorkflowRun、GitHub Project、branch 或 Spec 目录。用户取消时返回空 Project，且不得产生上述副作用；显式取消或普通中断后，浏览器草稿仍可用于再次进入创建流程。影响 Preview 的输入或 readiness 变化必须使旧 Preview stale，不能被继续确认。

---

### FR-1101 确认创建、Scribe Story 与 Dev Docs 结果

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-08`、Story §3.3 / §4.1；继承 `v0.14-001 FR-0300—FR-0500`
- **交付入口**：New Project Preview 的 `Create` → Dev Docs 最新 `story.md`

已认证 Human 只能确认当前、未过期且环境门禁仍通过的 Preview。确认后，Runtime 必须按 `v0.14-001` 的单活跃 Project、权威 `main` 和 Foundation 合同创建或 reconcile 同一组 Project、规划 release、WorkflowRun、GitHub Project、release branch 与 Spec 目录身份，并进入 `M-STORY`；不得建立第二个平行 Project/Run 身份。

Foundation 可确认后，系统必须以当前确认的 Story 输入和 release version dispatch Scribe 生成该 Project 的 canonical `story.md` revision。最新 Story revision 持久化成功后，用户必须被导航到 Dev Docs，并在同一 Project 上下文中直接加载该 `story.md` 作为可见结果和继续工作的位置。

重复、并发或恢复 Confirm 必须复用同一 request/Project/Story 身份。若外部资源或 Scribe 只完成一部分、失败或结果不确定，系统不得伪报创建完成或跳到错误文档；它必须显示同一 Project 的可恢复状态，先 reconcile 已发生结果，再重试未完成步骤，不得重复创建资源或覆盖冲突的 Story。

---

### FR-1201 Project Status 的完整 Workflow 与活跃节点

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-09`、Story §3.4（含布局参考）；继承 `v0.14-001 FR-0600/FR-1700`、`v0.14-002 NFR-0600`、`v0.14-003`
- **交付入口**：活跃 Project 的 Workbench main panel

Project Status 必须使用 Runtime 持久化 read model，在同一 main panel 中突出当前活跃节点并展示可导航的线性时间线。时间线必须覆盖当前 Project 从 `M-START`、`M-STORY`、`M-SPEC`、`M-ACC`、`M-REQ-APPROVAL`、`M-DESIGN`、`M-IMPL`、`M-TEST`、`M-VERIFY`、`M-SECURITY`、`M-RELEASE`、`M-PUBLISH` 到 `M-MILESTONE` 的完整 canonical workflow，并区分已完成、活跃、待处理、需要处理及失效状态。新 Project 及新状态写入统一使用 `M-REQ-APPROVAL`；读取历史 `M-LOCK-1` 时必须映射为同一批准节点并可标识兼容别名，不得将两者展示为连续的两个阶段。批准后创建或关联 Issues 是该节点的结果/evidence，不是额外 workflow 节点。

活跃节点处于 running 类状态时，突出区域必须显示当前责任方、attempt/轮次与已运行时长；处于 `waiting_human`、`blocked`、`conflict` 等 attention 状态时，必须显示原因、影响与 Runtime 指定的唯一主要动作入口。两种模式均须保留 canonical 状态、当前 artifact/revision 或 operation、最近 evidence/错误和 owning surface，使用户无需从时间线中重新寻找当前任务。

时间线必须按实际发生顺序把每次阶段 attempt（包括被打回后的重做轮次）作为独立节点保留，以方向连接表达推进，并以可辨认的回边表达从哪个节点回到哪个节点；历史 attempt 不得折叠成一个阶段节点、被新轮次覆盖或被重写为从未发生。节点多到无法同时呈现时，初始视图必须聚焦活跃节点并保留其邻近上下文，同时让用户能导航到全部历史；横向滚动、缩放或等效交互由 M-DESIGN 决定。Guide、浏览器缓存和前端不得根据聊天内容、文件存在或估算百分比推进或改写节点状态。

---

### FR-1301 选中节点详情与上下文返回

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-09`、Story §3.4（含布局参考）；Product Integration Pass
- **交付入口**：Project Status workflow 节点

用户选择时间线中任一可查看节点时，Project Status 必须在不丢失时间线上下文的详情 surface 中显示该 attempt 的开始/结束时间、状态、责任方、关联 artifact/revision、关键 evidence/错误、状态转移原因（特别是打回或阻塞原因）、当前是否允许回拨及适用动作，并明确区分“选中查看的节点”与“当前活跃节点”。选择历史或未来节点只改变查看上下文，不得改变 Runtime 状态或 active pointer；浮层、相邻区域或等效组件由 M-DESIGN 决定。

节点详情必须提供到其 owning artifact/operation surface 的稳定入口；用户完成查看或从 owning surface 返回时，必须回到同一 Project Status 与可识别的节点上下文，而无需重新寻找 Project。不存在、stale 或无权访问的目标必须显示可定位结果，不得静默切换到另一 Project 或 revision。

---

### FR-1401 Runtime 允许的回拨指针与安全执行

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-09`、Story §3.4（含布局参考）、`D-08`；继承 `v0.14-001 FR-1500/FR-2100`、`v0.14-003 FR-2600/FR-2700`
- **交付入口**：Project Status 的回拨指针

Project Status 只能为 Runtime 对当前 Project/revision 明确允许的先前 attempt 展示回拨指针，并在线性时间线中显示既有回拨的来源、目标与方向。选中节点详情必须显示其当前回拨合法性；仅当允许时才提供回拨主动作。用户发起回拨时，系统必须先说明目标节点、将失效或需要重做的后续 artifact/review/evidence，以及不能自动逆转的外部后果；只有 Human 明确确认且 Runtime 再次验证该回拨仍合法后才可执行。

回拨必须更新同一 Project 的 canonical active pointer，保留历史与审计，并按 owning 阶段合同将受影响的下游结果标记 stale、superseded 或待 reconcile，而不得静默删除历史或伪装撤销外部副作用。并发推进、旧页面、目标已失效或 Runtime 不支持时不得修改状态；界面必须刷新当前事实并显示合法继续位置。

---

### FR-1501 Project 用户概念、对象身份与兼容入口

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §3.2—§3.3、`D-03`、Story §4.3；宿主 `/projects`、`/runs` 与 Workbench 路由
- **交付入口**：Workbench Projects、`/projects`、Project/Run/Story 兼容深链

本旅程的用户可见主对象必须统一称为 Project；一个 Project 承载一次规划中的 release，并与其 GitHub Project、Runtime WorkflowRun 和 Story 工件保持可追溯的一对一上下文关系。Projects landing、New Project、Project Status、Guide 和 Dev Docs 不得为同一工作创建或展示互不关联的对象身份。

现有 `/projects`、`/projects/new`、Project detail、Run 与 Story 深链可以保留或转发，但必须解析到同一 Workbench Project 上下文和 Runtime 事实。历史 `Workflow Runs` 数据无需因本 Story 全量重命名或复制；历史读取可保留兼容标签，新旅程和新写入必须使用 canonical Project 身份且只维护一份可写真相。

---

## 非功能需求

### NFR-0001 持久化恢复、幂等与并发安全

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-01`、`BS-03`、`BS-08`、`D-07`、Story §4.1；继承 `v0.14-001 FR-2100/NFR-0100`
- **交付入口**：无独立入口，依附 FR-0101、FR-0301、FR-0901、FR-1101、FR-1401

首用户、Setup 完成状态、Project/request/revision identity、Runtime 状态和外部 operation 结果必须按各自持久化边界恢复；浏览器草稿按 FR-0901 保存在当前浏览器。刷新、服务重启、重复提交、并发 Confirm/回拨和不确定外部结果不得重复身份或副作用、接受 stale revision、丢失可证明进度或把未知结果标为成功。

---

### NFR-0101 Secret、权限与外部副作用保护

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §4.1 / 风险、`D-06`；继承 `v0.14-001 NFR-0200`、`v0.14-002/003 NFR-0200`
- **交付入口**：无独立入口，适用于 `/setup`、Environment Wizard、Guide、Project Status 与 Dev Docs

Credential、password、session secret、GitHub token、repository URL 中的 credential 和 OpenCode/provider secret 不得进入 Setup 完成记录、browser draft、Guide/Agent 对话、Runtime event、日志、错误详情、Story 文档或 Git 提交。产品只展示完成判断所需的 redacted identity、scope 名称和非秘密诊断。

模型探测必须使用最小请求并不得携带 Louke 工件或用户 Story；Git 初始化/binding、GitHub 认证变更、Project 资源和回拨相关外部操作必须限制在当前 workspace/Project 与 Human 已确认的范围内，不得覆盖或删除无法归属的用户数据。

---

### NFR-0201 外部检查的新鲜度、超时与可操作诊断

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：`BS-02`、`BS-06`、Story §3.1—§3.3 / 风险；成熟恢复惯例
- **交付入口**：`/setup`、Environment Wizard、Guide

OpenCode/model、`gh`、认证/scopes、Git repository/binding 和 remote 主分支等外部检查必须具有有界等待，且在进入依赖其结果的动作前使用足够新鲜的事实。超时、输出无法解析、命令不可执行、网络错误或结果不确定必须 fail closed，不得沿用过期成功状态继续创建。

失败诊断必须指出失败对象、已知事实、对当前任务的影响和可执行恢复位置，同时避免只暴露内部异常或秘密。Guide 收到检查投影或生成主动建议失败不得阻塞 owning Wizard 显示权威结果，也不得把投影/建议失败解释为环境检查失败或通过；chat window 已显示的 Runtime 结果必须保持可见并提供 Wizard 的修复入口。

---

### NFR-0301 可访问且不丢失输入的操作路径

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §3.1—§3.4、`D-04`、`D-07`；宿主产品质量基线
- **交付入口**：`/setup`、Workbench Projects、Environment Wizard、Project Status

Setup、模态 Wizard、Story/版本输入、Preview、workflow 节点与回拨动作必须可通过键盘和可访问名称完成，状态和失败不得只依赖颜色。后台检查或 Guide 更新不得夺取焦点、清除用户输入或遮断取消/返回；在受支持窗口尺寸和文本缩放下，关键动作、失败原因和继续位置必须保持可达。

---

### NFR-0401 单一状态权威与升级兼容

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **来源**：Story §4.1 / §4.3、`D-03`、`D-05`、`D-08`；继承 `v0.14-002/003 NFR-0600`
- **交付入口**：无独立入口，适用于所有 FR

Setup、Projects landing、Environment Wizard、Project Status、Guide、Dev Docs 和兼容路由必须消费同一可识别 workspace/Project/Runtime revision。浏览器缓存、旧 `Workflow Runs` 页面、Guide 摘要或历史 artifact 不得覆盖较新的 canonical 状态，也不得形成第二套可写 Project、workflow 或回拨事实。

升级必须保留可映射的用户、Setup、Project、Run、release、Story、artifact、evidence 和 milestone 身份；已有符合本合同完成条件的 workspace 不得被无故要求重新 Setup。无法安全映射的旧状态必须明确只读或需要迁移，不得静默复制、丢弃或解释为当前状态。

---

## 澄清记录

- 2026-07-24：Human 审核后的 `STR-1405` 明确取代本 Spec 先前的多步骤首次 Setup Wizard。首次 Setup 现在只包含首用户创建与真实 OpenCode 模型运行；Git/GitHub/repository readiness 只在点击 `New Project` 后执行。
- 2026-07-24：用户可见对象统一为 Project；现有 WorkflowRun 作为同一 Project 的 Runtime 身份继续兼容，不建立平行产品对象。
- 2026-07-24：基于 `BS-07`、其“避免后续缺失 remote/main”说明及 `v0.14-001 FR-0400`，空 remote 的初始化/binding 必须形成可供 Foundation 使用的 canonical `main`；具体 Git 实现方式留给设计。
- 2026-07-24：Human 澄清 Environment 检查出现阻断错误时，Guide 必须在无需用户输入的情况下主动给出建议；chat window 先呈现 Runtime 权威结果，再呈现可区分的 Guide 建议。
- 2026-07-24：Human 为 Project Status 增加“突出当前节点 + 线性尝试时间线 + 节点详情”的视觉参考。本文锁定其用户可观察的信息层次、每轮独立历史、回边和可导航性；GitLab/GitHub 参考、卡片/浮层、横向滚动/缩放及像素布局只作为 M-DESIGN 输入，不锁定具体组件。
- 2026-07-24：按 `v0.14-001 FR-1700` 的等价关系与 `v0.14-002 NFR-0600` 的新写入规则，Project Status 对新 Project 使用 `M-REQ-APPROVAL`；历史 `M-LOCK-1` 仅映射为同一节点的兼容别名，不显示成第二阶段。
- 2026-07-24：无开放产品决定。
