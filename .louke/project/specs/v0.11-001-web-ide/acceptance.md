# Louke Web IDE 与工作流服务化 — Acceptance Criteria

- **Spec ID**: v0.11-001-web-ide
- **Created**: 2026-07-11
- **Status**: Draft

> 每项采用 Given / When / Then 表述并可由 pytest 单元或 e2e 自动化断言。未决边界以 spec.md 的 `Decided: ⚠️` 为准。

## FR-0001 OpenCode 实例与会话操作

### AC-1
AC-FR0001-01
- **Given** Web 页面可访问且不存在运行实例，**When** 用户创建实例，**Then** 页面显示一个可选择且具有唯一标识的运行实例。

### AC-2
AC-FR0001-02
- **Given** 存在两个实例且用户选中其中一个，**When** 用户发送消息，**Then** 请求发往选中实例，页面显示该实例的消息回显和状态回显，另一实例不出现该输出。

### AC-3
AC-FR0001-03
- **Given** 一个可用实例，**When** 用户执行 `models` 或 `agent` 命令，**Then** 页面显示该实例返回的命令结果或明确错误状态。

### AC-4
AC-FR0001-04
- **Given** 一个运行实例，**When** 用户停止该实例，**Then** 页面将其显示为非运行状态，且后续发送操作不会被当作成功执行。

## FR-0101 Louke Server 工作流推进与 Agent 工具化

### AC-1
AC-FR0101-01
- **Given** 经确认的迁移清单包含一个纯工具调用步骤，**When** 工作流到达该步骤，**Then** Louke Server 直接执行对应工具且不启动被替代 Agent。

### AC-2
AC-FR0101-02
- **Given** 工作流到达需要判断下一步的节点，**When** 该节点配置为由 Maestro 决策，**Then** Server 调用 Maestro 获得决定并按决定继续。

### AC-3
AC-FR0101-03
- **Given** 一项 Agent 能力尚未列入经确认的迁移清单，**When** 工作流使用该能力，**Then** 系统不得仅凭“可能可工具化”而取消该 Agent 路径。

## FR-0201 用户指令意图分类与路由

### AC-1
AC-FR0201-01
- **Given** 用户输入可明确识别为新 story，**When** 系统完成分类，**Then** 在启动动作前要求用户选择“进入新开发”或“存 backlog”。

### AC-2
AC-FR0201-02
- **Given** 用户输入可明确识别为 spec change，**When** 系统完成分类，**Then** 系统选择 spec change 动作而非新开发或 fix。

### AC-3
AC-FR0201-03
- **Given** 用户输入可明确识别为 bug fix，**When** 系统完成分类，**Then** 系统选择 fix 动作而非新开发或 spec change。

### AC-4
AC-FR0201-04
- **Given** 输入歧义、低置信度或不属于已知类别，**When** 分类结束，**Then** 系统提出澄清问题，且在用户确认前不启动任何候选动作。

## FR-0301 可追溯项目 Wiki

### AC-1
AC-FR0301-01
- **Given** 一组已纳入范围的源设计文档，**When** Wiki 更新完成，**Then** 存在 story、spec、test-plan、architecture、interfaces 五类当前汇总文档，展示编号不使用 FR-XXXX。

### AC-2
AC-FR0301-02
- **Given** 汇总文档中的任一 story/spec 事实，**When** 检查其来源，**Then** 该事实包含可解析到原始设计文档相应位置的链接。

### AC-3
AC-FR0301-03
- **Given** review 中存在有最终裁决和原因的技术争议，**When** Wiki 更新，**Then** 技术决定区域包含争议、结果、原因及来源链接。

### AC-4
AC-FR0301-04
- **Given** Wiki 构建成功，**When** 打开首页和项目信息，**Then** 可访问 README、story/spec 等设计文档、FAQ，并看到版本、分支、GitHub Project、开发起止时间字段。

### AC-5
AC-FR0301-05
- **Given** 页面更新按钮和每日任务均可触发检查，**When** 源文档有变更，**Then** Wiki 被更新；**When** 无变更，**Then** 每日任务不改写 Wiki 产物。

### Candidate ACs pending FR-0301 decisions

> 下列条目来自 `wiki-exploration.md`，用于使“唯一、最新、最全”可机器验证；在 spec 的来源范围、冲突优先级和目录映射拍板前不计入正式 AC 编号。

- **Given** 当前 source manifest，**When** 任一纳入范围的源文件新增、修改、删除或重命名并成功更新 Wiki，**Then** 发布 manifest 的 source digest 等于更新时重新扫描所得 digest；无变化时不调用 LLM，生成产物字节和 mtime 均不改变。
- **Given** Wiki 发布候选，**When** 执行唯一性校验，**Then** story、spec、test-plan、architecture、interfaces 五种 canonical kind 各恰好存在一个，任一重复或缺失均不得替换上一份成功发布结果。
- **Given** 任一 active Wiki 事实和纳入范围的 mandatory source section，**When** 执行 provenance/coverage 校验，**Then** 每个事实至少有一个可解析来源，每个 mandatory section 均被标记为 rendered、superseded、conflict 或 excluded-with-reason，不存在 silent drop。
- **Given** 新版本设计文档只覆盖旧版本的部分 topic，**When** Wiki 更新，**Then** 只替换被明确覆盖的 topic，旧版本仍有效且未被覆盖的事实继续存在。
- **Given** 两个权威来源存在冲突但没有最终裁决，**When** Wiki 更新，**Then** 相关 topic 显示为 unresolved/degraded，系统不得由模型静默选择其中一个作为事实。
- **Given** review 中存在技术争议，**When** 系统决定是否记录 final decision，**Then** 只有同时具有争议、结果、原因和有效来源的记录可标 final，其余记录保持 unresolved。
- **Given** build 期间源再次变化、LLM 输出不满足 schema、来源链接失效或任一发布门禁失败，**When** build 结束，**Then** staging 不发布，用户继续看到上一份完整 Wiki，并可查看失败状态。
- **Given** 手动按钮与每日任务，**When** 两者分别触发更新，**Then** 它们调用同一 change detector、编译和原子发布流水线；并发触发不会产生两个交错发布结果。

## FR-0401 `.louke` 产物目录规划

### AC-1
AC-FR0401-01
- **Given** 经确认的目录规划，**When** 检查规划，**Then** Louke Server、code review、会话保存和 Wiki 文件各自具有明确规范位置。

### AC-2
AC-FR0401-02
- **Given** 任一上述类别的新产物，**When** 系统保存该产物，**Then** 文件出现在其规范位置而非其他类别目录。

### AC-3
AC-FR0401-03
- **Given** 当前仅处于 M-SPEC 阶段，**When** 比较任务前后的目录，**Then** 不因撰写本 spec 而发生目录重排。

## FR-0501 FR/NFR task 状态编辑与持久化

### AC-1
AC-FR0501-01
- **Given** 含 FR/NFR 状态的设计文档，**When** 页面渲染该需求，**Then** 每个状态显示为独立可点击的 Markdown task checkbox，而非状态表格。

### AC-2
AC-FR0501-02
- **Given** 一个未选中的状态 task，**When** 用户点击并保存，**Then** 源文件对应项变为 `- [x]`，重新加载后仍为选中状态；反向切换同理写为 `- [ ]`。

### AC-3
AC-FR0501-03
- **Given** 页面采用一行视觉布局，**When** 用户分别点击任一状态，**Then** 仅目标 Markdown task 的状态改变，其他 task 不变。

## FR-0601 本地 Story Backlog

### AC-1
AC-FR0601-01
- **Given** backlog 可用，**When** 用户提交一个有效 story 条目，**Then** 该条目被持久化并出现在本地列表中。

### AC-2
AC-FR0601-02
- **Given** backlog 中有多个条目，**When** 用户选中其中一项并点击进入开发，**Then** 仅选中项被传给 Louke 现有新 story 开发流程。

### AC-3
AC-FR0601-03
- **Given** 用户未选中条目，**When** 点击进入开发，**Then** 系统不启动新 story 流程并显示需先选择条目的反馈。

## FR-0701 工作区文件、变更与 Diff

### AC-1
AC-FR0701-01
- **Given** 工作区包含已跟踪文件和 Git 变更，**When** 用户打开相应页面，**Then** 可查看文件列表、变更文件列表及所选变更的 diff。

### AC-2
AC-FR0701-02
- **Given** 用户打开源代码文件，**When** 尝试保存修改，**Then** 系统拒绝写入且文件内容不变。

### AC-3
AC-FR0701-03
- **Given** 用户打开允许编辑的设计文档，**When** 修改并保存，**Then** 对应源文件持久化该内容，重新加载后内容一致。

### AC-4
AC-FR0701-04
- **Given** 文件为二进制或超过 500 行，**When** 用户请求预览，**Then** 二进制文件不显示正文；超过 500 行的文本在用户批准前不加载正文，拒绝后仍不加载。

## FR-0801 Markdown 文档展示

### AC-1
AC-FR0801-01
- **Given** 工作区含 `.louke/project/**` 下的 Louke 设计 Markdown、README 和递归 `docs/**/*.md`，**When** 打开文档导航，**Then** 范围内文件可被发现和选择。

### AC-2
AC-FR0801-02
- **Given** 用户选择一个范围内 Markdown 文件，**When** 渲染完成，**Then** 页面内容来自所选文件并按 Markdown 展示。

### AC-3
AC-FR0801-03
- **Given** 一个二进制文件、范围外文件或超过 500 行的 Markdown 文件，**When** 请求文档展示，**Then** 前两者不经该入口渲染，后者仅在用户批准后渲染正文。

## NFR-0001 自动化质量门槛

### AC-1
AC-NFR0001-01
- **Given** 候选交付版本，**When** 执行约定的 pytest 单元测试与 e2e，**Then** 全部 e2e 通过且无失败或错误测试。

### AC-2
AC-NFR0001-02
- **Given** 候选交付版本，**When** 按确认后的统计范围生成单元测试覆盖率报告，**Then** 覆盖率不低于 95%。

## NFR-0101 浏览器兼容性

### AC-1
AC-NFR0101-01
- **Given** Chromium 与 Firefox 测试环境，**When** 执行本 spec 约定的 Web e2e 关键路径（OpenCode 交互、指令路由、Wiki 更新、backlog 转开发、文件/diff 查看、文档状态保存），**Then** 两个浏览器下所有路径全部通过。WebKit 不在本期承诺范围。

## NFR-0201 文件访问安全

### AC-1
AC-NFR0201-01
- **Given** 指向允许工作区之外目标的读取、diff 或保存请求，**When** 服务处理请求，**Then** 请求被拒绝且目标内容未被读取或修改。

### AC-2
AC-NFR0201-02
- **Given** 对源代码或未列入可编辑设计文档清单的文件发起写请求，**When** 服务处理请求，**Then** 请求被拒绝且文件字节保持不变。
