# Programmatic Workflow Control — Story

- **Spec ID**：`v0.12-001-programmatic-workflow-runtime`
- **创建日期**：2026-07-13
- **状态**：M-LOCK Approved — M-DEV Not Started

## 原始问题

当前 Louke 的工作流主要由 Maestro 在对话中推动。Maestro 既判断下一步，也直接调用下一角色或命令。因此提示词中虽然规定了阶段顺序，程序本身却不能保证实际执行顺序，人类审批、M-LOCK 等步骤可能被跳过。

同时，M-FOUNDATION 中的大部分工作已经是确定性的检查和工具调用，却仍由 Scout/Warden 两个 Agent 包装。它既增加上下文和协调成本，也让“工作流阶段”与“项目应始终满足的前置条件”混在一起。

当前 `lk` 还以单一用户级安装为主，无法让两个尚未结束的项目分别固定并同时使用不同 Louke 版本。仅依赖 PATH 中偶然命中的全局 `lk`，还可能让项目在未察觉时被另一版本读取或迁移。

## 期望结果

Louke 程序成为工作流状态的唯一控制者：

1. 工作流允许哪些步骤及转移，由版本化定义固定。
2. 确定性工作由程序执行。
3. M-FOUNDATION 变成进入工作流前自动检查的幂等前置条件。
4. M-LOCK 变成持久化的人类门禁，未批准不能进入开发。
5. Maestro 和其他 Agent 即使提出“跳到下一步”，也没有改变状态的能力。
6. 在 story/spec/acceptance 完成后必须先由人类批准，批准前不能开始 test plan、architecture 或 interfaces。
7. test plan、architecture、interfaces 完成并经人类 review 后，必须再通过 M-LOCK，才能开始开发。
8. Louke 重启后能从原步骤继续，而不是依赖一段 Agent 对话记住进度。
9. Web 提供项目创建、历史与当前工作流查看、工作流图和 Agent-model 绑定操作。
10. Web 创建的 OpenCode 运行实例可以 detach、attach、停止生成和退出，并为每个语义任务提供可追溯的定制上下文。
11. 程序负责所有确定性步骤和权威副作用；Agent 只负责需要理解、判断、审查或创造的部分，并由完整、版本化的 built-in responsibility inventory 证明没有未分类或仍藏在 Agent 内的程序职责。
12. 新用户只需在现有 Git 仓库启动 `lk serve`，即可由首次打开的 Web init-wizard 完成 Louke 初始化、首位本地用户、依赖与模型就绪检查，不必运行初始化 CLI 或手写 `project.toml`/运行时存储。
13. 项目详情不仅显示图，还明确告诉用户“为什么停在这里、现在能做什么”，并能打开当前产物、审批、Agent session、错误和证据。
14. 失败、重启、误创建或主动取消都有受控的恢复/终止路径；历史与审计不会因清理运行资源而丢失。
15. `new_feature` 是从需求到发布归档的完整 workflow；`bug_fix` 专指已有发布产品相对既有已批准需求的实现错误，以 GitHub Issue 和 R-G-R 为快速路径，确需设计时进入完整设计分支。
16. 每条需求、AC、实现任务、代码变更和权威测试结果形成闭合证据；只完成部分需求时，项目不能显示为完成。
17. 现有 v0.10/v0.11 workspace 可以显式、可回滚地采用 v0.12，而不会被新 Runtime 猜测性接管或破坏历史资料。
18. 每个项目可以固定并隔离自己的 Louke 版本；从项目目录启动时优先使用该项目的本地安装，明确选择不做项目内安装时仍可使用兼容的全局版本。

## 使用场景

### 场景一：启动工作流

用户选择一个版本固定的 workflow。Louke 创建独立的 WorkflowRun，自动检查 foundation，并只执行当前定义允许的步骤。

### 场景二：Foundation 已满足

程序发现项目 foundation 已完整，记录检查证据后继续，不启动 Scout 或 Warden。

### 场景三：Foundation 可自动修复

程序执行已注册、幂等的 foundation 操作，再次验证成功后继续。重复执行不会创建重复资源。

### 场景四：批准需求后才开始设计

Sage/Lex 与用户完成 story、spec、acceptance 评审后，程序停在需求审批门。只有人类批准当前三份文档的 digest，才允许启动 test-plan、architecture 和 interfaces 的设计任务。

### 场景五：等待 M-LOCK

设计文档完成并经用户 review 后，程序生成绑定完整 contract hash 的 M-LOCK 批准请求并停止推进。Maestro、API 调用者或重启后的恢复逻辑都不能绕过该状态进入开发。

### 场景六：规格在批准前后发生变化

批准前规格变化会使旧 challenge 失效；批准后规格变化会使旧批准失效并重新进入等待状态。

### 场景七：进程中断与恢复

Louke 在任一步骤中断。重启后从持久化运行状态恢复；已完成的幂等步骤不会重复产生副作用。

### 场景八：从 Web 创建项目和工作流

用户在 sidebar 打开 Projects，选择创建新项目，输入 story、release version，并选择 `new feature` 或 `bug fix`。Louke 创建相应工作流并显示工作流图和当前位置。

### 场景九：查看当前或历史工作流

用户选择当前活动或历史项目，看到该运行绑定的工作流图、各节点状态、当前或最终位置，以及对应的 Agent-model 绑定图。

### 场景十：调整 Agent model

用户在 Agent-model 绑定图中拖拽 model 到 Agent。已经运行中的任务不变；该 Agent 的下一个尚未开始任务使用新 model，并留下变更记录。

### 场景十一：执行语义 Agent 任务

程序先依据完整的 built-in responsibility inventory 把当前职责拆成 program/semantic 边界，再为 Devon、Sage、Lex、Maestro 等 Agent 创建受控 OpenCode session 和 context manifest。Agent 可以在授权范围内思考、阅读、编辑或测试，但不能批准门禁、改变 WorkflowRun、commit/push 或自行进入下一阶段。

### 场景十二：第一次使用 Louke

用户在现有 Git 仓库启动 `lk serve`。即使 workspace 尚未初始化，Web 仍以 setup-only 模式打开 init-wizard；向导建立 Louke 内部状态和首位本地用户，并显示 workspace、Git、OpenCode、model/provider 及 workflow catalog 的就绪情况。除启动服务外，用户不需要运行初始化 CLI 或手工构造内部状态文件。

### 场景十三：在项目详情完成当前动作

用户打开一个等待中的项目，除工作流图外还能看到当前步骤说明、阻塞原因、下一合法动作、待评审文档和检查结果。需求审批或 M-LOCK 到达时，用户在同一项目上下文查看被绑定的产物及变更，再批准或带理由拒绝。

### 场景十四：任务失败、取消与恢复

Agent 断线、程序步骤失败或服务重启后，项目显示准确状态和可执行的重试/恢复动作。用户也可以确认取消误建项目；系统停止后续调度并清理受管运行资源，但保留项目、事件和审批证据为只读历史。

### 场景十五：完成完整 workflow

`new_feature` 经过需求、设计、两次人类门禁、实现、评审、权威测试和发布确认后成为历史项目。`bug_fix` 必须引用 GitHub Issue 和一个既有已批准 spec/AC，证明它是实现偏离而非新需求；标准 hotfix 直接走复现、M-LOCK、R-G-R 和回归门禁，需要 architecture/interfaces 时进入完整设计分支。hotfix 不重复 requirements approval，但不能绕过 M-LOCK 或完成证据检查。

### 场景十六：采用旧 Louke workspace

已有 v0.10/v0.11 文档和元数据先以迁移预览展示。用户确认后，历史内容作为 legacy 项目只读可见；无法证明当前状态的旧流程不会被自动伪装成可恢复的新 WorkflowRun。

### 场景十七：活动项目期间收到新需求或 hotfix

同一 workspace 已有 active `new_feature` 时，另一条新需求不能启动第二个主 Project，只能先写入 backlog；当前主 Project 结束后，backlog 条目可以带入创建确认流程。已发布产品的 hotfix 可以作为例外并行，但它必须使用隔离运行上下文，且不得串写主 Project 的状态或证据。

### 场景十八：两个项目使用不同 Louke 版本

项目 A 固定 Louke x.y，项目 B 固定 Louke x.z。用户分别从两个项目目录或其子目录启动 `lk serve`，两个服务及其后续程序步骤、Agent task 和模板始终使用各自解析出的版本，互不串用。选择 global mode 的项目可以使用全局 Louke，但项目已经声明 local mode 而本地安装缺失、损坏或版本不符时必须停止并给出修复入口，不能静默回退到全局版本。

## 当前边界

- 首批显式可选工作流是 `new feature` 和 `bug fix`；`bug fix` 在本期专指已发布产品的 hotfix。首版不直接暴露 `spec change`。
- 首版按 loopback 本地 Web 使用设计，不承诺公网多用户部署。
- 不提供允许用户任意绘制节点和边的通用 workflow editor；工作流由程序定义，用户只从允许的 workflow 中选择。
- `lk serve` 是首次使用所需的唯一 Louke CLI；初始化、采用、首位用户和 Louke/OpenCode/model/provider readiness 由 Web init-wizard 完成，不得把另一条 CLI 命令作为唯一修复路径，也不得要求用户手写内部元数据或运行状态。操作系统级前置依赖的安装方式由 architecture 设计，但向导必须可诊断并给出 Web 内可执行或可理解的下一步。
- 项目内安装是新项目的推荐模式；项目必须持久化安装模式和期望的精确 Louke runtime identity。受管环境、二进制与下载缓存不要求进入版本控制；具体 launcher、环境目录和包管理机制留给 requirements approval 之后的 architecture 决定。
- 浏览器兼容矩阵、像素级视觉回归、移动端布局和公网部署不属于本轮目标。
- 具体模块、存储、API 和分期方式必须在本 Story/Spec/Acceptance 锁定后由 architecture 决定；当前候选路线图不能反向限制需求。
