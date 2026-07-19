---
status: Draft v7 (Sage authored after Scribe/Sage prompt update; pending human review before Sage revises acceptance.md)
spec_id: v0.14-001-workflow-reflow-spec
bound_story: STR-1402
bound_story_digest: sha256:e04e88b336c7f08a3f67ef40354fa35c3e78ec66935805aa6f2da7272dfd0634
spec_digest: __SPEC_DIGEST__
acceptance_digest: __ACCEPTANCE_DIGEST__
doc_index_digest_sha256: __DOC_INDEX_DIGEST__
revision: 7
lex_review_artifact: .louke/project/specs/v0.14-001-workflow-reflow-spec/spec-review.md
scope: flow.md L1-L95 (install -> M-LOCK-1 + GitHub Issues)
prompt_basis: .opencode/agents/scribe.md + .opencode/agents/sage.md (rewritten 2026-07-18)
journey_first: true
author: Sage (subagent), pending Aaron review
author_identity_note: written by Sage subagent under model openai/gpt-5.6-sol at 2026-07-18; NOT written by Maestro
digest_scheme: each digest is sha256 over the file with the digest field literally replaced by its placeholder text (canonical placeholder-bearing body). Substitution back from this digest does not reproduce the file hash; this is expected for self-referential digests. See the acceptance.md or downstream tool for the verification rule.
---

# v0.14 Workflow Reflow — Requirements Spec

> 本合同覆盖 `flow.md` L1-L95：用户从安装后的 `lk serve` 进入 Web Workbench，完成 Workspace Setup、新 release 的需求定义、M-LOCK-1，并得到关联 release GitHub Project 的 Issues。合同共 24 个有效单元（21 FR + 3 NFR），采用 User Journey 优先结构；下列 surface/context 只描述 `story.md` 与 `flow.md` 已给出的用户可见元素，例如启动诊断页、Workspace Setup、`/projects/new`、文档编辑页、工作台 Chat、Project current 页及等待批准提示，不定义组件树、样式、框架或内部接口。

## User Journey

### Step 1 — 启动并进入 Web Workbench
- **入口 / 触发**：Human 在目标 workspace 安装或升级 Louke 后执行 `lk serve`。
- **Mounted surface**：启动诊断页显示 Louke、依赖、配置、模型、OpenCode 与 workspace 身份，检查通过后进入 Web Workbench（`flow.md` L5-L13；`story.md:40-51`）。
- **关键动作**：Human 只处理诊断中可定位的缺失依赖、登录、授权或模型配置；Runtime 判断应进入 Setup 还是直接进入 release 请求入口。
- **可见结果**：检查通过时 Workbench 可访问；失败时诊断保留原因和可执行修复方向，且不会把启动误报为成功。
- **继续 / 返回**：setup 有效则继续 Step 3；首次、缺失、冲突或失效则继续 Step 2；修复失败项后可从同一 workspace 重试。
- **服务 FR/NFR**：FR-0100、FR-0600、FR-2100、NFR-0300。

### Step 2 — 完成或复用 Workspace Setup
- **入口 / 触发**：启动检查发现 workspace 首次使用，或 setup 信息缺失、冲突、失效。
- **Mounted surface**：Workspace Setup preview 展示候选值、来源、冲突与需要授权的操作；完成后展示有效 foundation manifest 所代表的 workspace/resource 身份（`flow.md` L15-L23；`story.md:46-52`）。
- **关键动作**：Human 只补充缺失值、裁决冲突值并确认需要授权的操作；确认前不发生对应外部修改。
- **可见结果**：必要资源真实存在且身份一致后 Setup 完成；不确定、冲突或部分失败保持待处理并显示具体资源状态。
- **继续 / 返回**：完成后进入 Step 3；取消或失败时留在 Setup，修复后按已保存 preview 和外部事实继续，不重复创建资源。
- **服务 FR/NFR**：FR-0200、FR-2100、NFR-0100、NFR-0200、NFR-0300。

### Step 3 — 创建 release 请求
- **入口 / 触发**：Human 从 Workbench 的新建项目页面 `/projects/new` 发起新 release。
- **Mounted surface**：新建 release 页面展示一句话设想、版本信息及确认前 preview；若已有活跃主 release，则显示阻塞原因与已保存的 Backlog 结果（`flow.md` L25-L29；`story.md:46-52`）。
- **关键动作**：Human 填写并确认 release 请求；Runtime 在产生 release 副作用前检查该 workspace 是否已有冲突的活跃主 release。
- **可见结果**：无冲突的请求进入前置检查；有冲突的请求只形成一个可查询 Backlog 条目并结束本次创建会话。
- **继续 / 返回**：可开始时继续 Step 4；被阻塞时返回 Projects/Backlog 查看原因，且不会进入 M-STORY 或产生第二个主 release。
- **服务 FR/NFR**：FR-0300、FR-0600、FR-2100、NFR-0100、NFR-0300。

### Step 4 — 验证 `main` 并完成 Foundation
- **入口 / 触发**：release 请求通过单活跃主 release 检查。
- **Mounted surface**：当前 release 的创建进度显示权威 `main`、上一主开发分支合入关系、必要资源与失败修复方向；结果归入同一 Project/run 上下文（`flow.md` L29-L31；`story.md:64-66`）。
- **关键动作**：Runtime 证明上一主开发的预期修改已进入权威 `main`，随后创建或复用 release Project、run、release branch 与 Spec 目录。
- **可见结果**：所有资源身份一致且 release branch 从本次验证的 `main` 起点建立后 Foundation 完成；无法证明、分叉或部分成功时保持阻塞，不伪报完成。
- **继续 / 返回**：成功后继续 Step 5；Human 修复分支或权限问题后重新检查，恢复时先核对已发生的外部副作用。
- **服务 FR/NFR**：FR-0400、FR-0600、FR-2000、FR-2100、NFR-0100、NFR-0200、NFR-0300。

### Step 5 — 形成初始 `story.md`
- **入口 / 触发**：Foundation 完成并取得本 release 的 Spec 目录。
- **Mounted surface**：本 release 的 Story 编辑页显示 `story.md`、当前阶段与 revision；该页面延续刚创建的 release/Project 身份（`flow.md` L30-L32；`story.md:64-67`）。
- **关键动作**：Runtime 从 Story 模板创建文件，将 Human 原始设想写入原始输入位置，并提交仅属于该文档的初始 revision。
- **可见结果**：用户在 Story 页看到原始设想与模板结构，并能识别当前 run、M-STORY 阶段及 revision；冲突内容不会被静默覆盖。
- **继续 / 返回**：提交成功后原地进入 Step 6 的 Scribe Chat；初始化失败时留在当前 release，解决冲突后复用或重试。
- **服务 FR/NFR**：FR-0500、FR-0600、FR-2000、FR-2100、NFR-0200、NFR-0300。

### Step 6 — 完成 M-STORY 与独立评审
- **入口 / 触发**：初始 Story revision 已提交，Story 页进入 M-STORY。
- **Mounted surface**：只读 Story 旁的工作台 Chat 承载 Scribe 对话；随后 Story review 页面开放 Human 编辑、inline discussion、`comment`/`no comment` 与 Sage 独立评审状态（`flow.md` L34-L57；`story.md:66-68`）。
- **关键动作**：Scribe 先调查并给出 Go/Park/No-Go 建议，Human 裁决；Go 时同一 Scribe 上下文继续访谈并交稿，之后 Human 与独立 Sage 对同一 revision 多轮评审。
- **可见结果**：Park/No-Go 安全保存到 Backlog 并结束；Go 路径产生可追溯 Story revision，只有 Human 与 Sage 对当前 revision 均通过才完成 M-STORY。
- **继续 / 返回**：通过后进入 Step 7；未通过时 Scribe 响应意见形成新 revision；未保存编辑、写权冲突、中断或旧 revision 结论均留在当前轮次并可恢复。
- **服务 FR/NFR**：FR-0700、FR-0800、FR-0900、FR-1000、FR-1100、FR-1200、FR-1900、FR-2000、FR-2100、NFR-0100、NFR-0200、NFR-0300。

### Step 7 — 完成 M-SPEC、M-ACC 并批准 M-LOCK-1
- **入口 / 触发**：当前 Story revision 的 Human 与 Sage 独立评审均通过。
- **Mounted surface**：Workbench 依次打开 Spec 编辑页、Acceptance 编辑页和 Project current 页；作者工作时 Human 只读，评审时显示 Human/Lex 意见、inline discussions、当前 revision，最后显示 M-LOCK-1 等待批准提示与按钮（`flow.md` L59-L93；`story.md:68-70`）。
- **关键动作**：Sage 依次起草 Spec 与 Acceptance，Human/Lex 对各自当前 revision 多轮独立评审并完成格式验收；发现上游产品问题时由 Human 明确返回合法上游；三件套全部通过后 Human 批准当前 M-LOCK-1。
- **可见结果**：每阶段仅在语义、格式和当前 revision 结论齐备后前进；批准后 Story、Spec、Acceptance 在产品中只读，批准身份与三件套版本可追溯。
- **继续 / 返回**：有效批准后继续 Step 8；未通过则回到相应作者修订，Human 也可返回 M-SPEC 或 M-STORY并使受影响下游结论失效。
- **服务 FR/NFR**：FR-0600、FR-1000、FR-1100、FR-1300、FR-1400、FR-1500、FR-1600、FR-1700、FR-1900、FR-2000、FR-2100、NFR-0100、NFR-0200、NFR-0300。

### Step 8 — 创建并关联 GitHub Issues
- **入口 / 触发**：已认证 Human 对当前三件套完成 M-LOCK-1 批准。
- **Mounted surface**：Project current 页在同一 release 上显示各需求 Issue 的创建/复用、GitHub Project 关联、失败或不确定状态；结果可跳转到对应 Issue（`flow.md` L87-L95；`story.md:70-71`）。
- **关键动作**：Runtime 按锁定 Spec 的每个有效 FR/NFR 创建或复用一个 Issue，并关联 foundation 指定的 release GitHub Project。
- **可见结果**：每个需求最多对应一个身份匹配的 Issue 和一个 Project item；部分失败逐需求可见，批准前不会产生本次实现 Issues。
- **继续 / 返回**：全部关联后用户可从 Project/Issue 进入后续 Spec 承接的设计与开发流程；失败或确认丢失时留在本步骤核对后重试，不回滚已成功 Issue。
- **服务 FR/NFR**：FR-0600、FR-1700、FR-1800、FR-2100、NFR-0100、NFR-0200、NFR-0300。

## Functional Requirements

### FR-0100 `lk serve` 启动诊断与产品入口
<a id="fr-0100"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-01; `story.md:40-51`; `flow.md L5-L13`

Human 在目标 workspace 执行 `lk serve` 时，系统必须在开放工作流动作前检查 Louke、必要依赖、配置、模型、OpenCode 可用性和 workspace 身份，并在启动诊断页逐项展示非秘密状态与可执行修复方向。

检查通过且 setup 有效时，系统进入 Web Workbench 的 release 请求入口；首次、缺失、冲突或失效 setup 进入 Workspace Setup。启动失败不得显示可继续状态，重复启动不得重复初始化 workspace 或外部资源。

- **Journey**: Step 1.

### FR-0200 Workspace Setup Preview、确认与 Manifest
<a id="fr-0200"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-01, BS-02, BS-15; `story.md:46-52`; `flow.md L15-L23`

系统必须从可用项目事实与认证身份推导项目名称、repository、owner、release version 等必要候选值，并在 Workspace Setup preview 中展示候选值及来源。Human 确认前，不得执行该 preview 所列的外部创建或修改。

缺失、冲突、歧义或授权要求必须保持为等待 Human 的可恢复状态；系统不得静默选择冲突身份。Human 的决定必须绑定当前 setup revision并可追溯到 actor、候选来源和选择结果。

确认后，系统创建或复用必要资源并形成 foundation manifest，记录 workspace、repository、release、branch、Project 的稳定身份和实际状态。只有资源真实存在且身份一致时 Setup 才完成；重试或重启先 reconcile，匹配不唯一或证据不足时继续等待处理而不重复创建。

- **Journey**: Step 2.

### FR-0300 Web Release 请求与单活跃主 Release
<a id="fr-0300"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-03; `story.md:46-52`; `flow.md L25-L29`

`/projects/new` 必须让 Human 提交非空的一句话设想和合法 release version，并在产生 release 副作用前展示本次请求及其 workspace 身份供确认。

同一 workspace 已有活跃主 release 时，确认请求必须幂等保存为一个可查询 Backlog 条目，展示阻塞原因并结束本次创建会话；不得创建第二个主 Project、run、release branch 或 Spec 目录，也不得进入 M-STORY。重复或并发确认不得产生重复条目。

- **Journey**: Step 3.

### FR-0400 新 Release 的 `main` 前置检查与 Foundation
<a id="fr-0400"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-04, BS-15; `story.md:64-66`; `flow.md L29-L31`

对可开始的 release，系统必须在创建 release branch 前刷新 declared remote，并证明上一主开发分支的预期修改已经合入该 remote 的权威 `main`。本地与权威 `main` 不一致，或上一分支相对权威 `main` 为未合入、ahead、behind、diverged、无法判定时，页面必须展示相关引用、版本身份、关系和修复方向；Human 修复并重新检查通过前不得绕过阻塞。

检查通过后，系统创建或复用本 release 的 Project、run、release GitHub Project、Spec 目录和基于本次权威 `main` 版本的 release branch。分支起点与已证明的 `main` 不一致、任一操作部分成功、权限失败或结果不确定时，Foundation 不得显示完成或进入 M-STORY；恢复必须先核对已发生副作用。

- **Journey**: Step 4.

### FR-0500 初始 `story.md` Revision 与页面跳转
<a id="fr-0500"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-04; `story.md:64-67`; `flow.md L30-L32`

系统必须从 canonical Story template 创建本 release 的 `story.md`，把 Human 原始设想写入原始输入位置并保留模板其余结构，形成绑定输入、文件、actor 和提交身份的初始 revision。

同一初始化重试必须复用内容匹配的目录、文件和 revision；已存在内容冲突时停止并向用户显示冲突，不得覆盖。初始 revision 成功后，Web 导航到本 release 的 Story 编辑页并显示当前 run、阶段和 revision。

- **Journey**: Step 5.

### FR-0600 Runtime 权威工作流与 Web 当前状态
<a id="fr-0600"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-07, BS-15; `story.md:58-71`; `flow.md L34-L95`

Runtime 必须是 M-STORY、M-SPEC、M-ACC、M-LOCK-1 的当前步骤、合法转移、write ownership、review round 和状态的唯一推进 authority；Agent 消息、文档文字或客户端声明不能直接推进流程。

Project 页面必须从持久化事实显示当前步骤、状态、artifact revision、当前写者、待处理 Human 动作、Agent task/session、review 结论和最近错误。刷新或重启后必须重建同一用户上下文；stale 或非法动作不得改变 run、文档或外部资源，并应显示当前状态冲突及可继续位置。

- **Journey**: Steps 1, 3-8.

### FR-0700 Scribe 调查、分流建议与 Human 裁决
<a id="fr-0700"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-05, BS-06; `story.md:114-122`; `flow.md L34-L43`

M-STORY 开始时，系统必须在 Story 旁打开绑定当前 run 的 Chat、使 Human 暂时只读，并派发仅可更新当前 `story.md` 的 Scribe author task。任务上下文必须包含当前 run/step/attempt、spec 身份、Story revision与digest、适用模板身份、Human 原始请求、foundation 身份，以及适用的上一轮反馈。

系统必须刷新已保存 Story 内容，并等待 Scribe 返回 Go/Park/No-Go 建议及理由。建议只供 Human 裁决；只有已认证 Human 对当前 Story revision 的明确合法选择可改变分流结果，旧 revision 或 Agent 自行裁决不得生效。

- **Journey**: Step 6.

### FR-0800 Park/No-Go 的 Backlog 与安全退出
<a id="fr-0800"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-06, BS-15; `story.md:119-122`; `flow.md L42-L42`

Human 对当前 Story revision 裁决 Park 或 No-Go 后，系统必须幂等保存 Story、决定、理由、actor、digest 和来源 run 到 Backlog，并把本次 release 流程置为对应终态；不得进入 M-SPEC。

只有能够证明本地 release branch 不含初始 Story 之外的用户或未归属修改时，系统才可删除未使用的本地分支。无法隔离修改或远程分支已存在时必须保留并显示需要 Human 处理，不得重置、强制删除或回退无关内容。重复执行不得产生重复 Backlog 条目或重复删除。

- **Journey**: Step 6.

### FR-0900 Go 后的访谈、Story 完成与交接 Revision
<a id="fr-0900"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-06, BS-09; `story.md:119-137`; `flow.md L43-L57`

Human 裁决 Go 后，系统必须让同一 Scribe task/session 继续访谈；Human 回复在发送前进入可恢复的 run/task 记录，发送重试不得在 Chat 或 Scribe 上下文中形成第二条逻辑回复。

Scribe 声明完成时，系统必须验证 `story.md` 已落盘且相对交接基线有实际内容变化；无变化则提示 Scribe 补写并保持 authoring。验证通过后只提交当前 `story.md` 的交接 revision，记录文档与 Scribe task/session 身份，提交成功后才开始独立 review。

- **Journey**: Step 6.

### FR-1000 文档 Write Ownership、CAS 与脏编辑保护
<a id="fr-1000"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-07, BS-09; `story.md:124-137`; `flow.md L47-L57, L63-L72, L81-L84`

对 `story.md`、`spec.md` 和 `acceptance.md`，任一时刻只能有一个获授权写者；保存必须匹配当前 run、document、writer lease 与 revision/version。失配不得覆盖当前内容，并须让用户或 Agent 看见最新 revision 与冲突原因。

收回 Human 写权前必须处理浏览器未保存内容：等待保存或由 Human 明确取消，不得让 Agent 覆盖。第二轮起页面可持续向 Human 开放，只在 Scribe、Sage 或 reviewer 实际写入期间临时只读。

非授权写入不得成为接受的 revision。系统必须保留足以取得最近一次已接受文档精确内容的 revision evidence；仅在违规 patch 来源可证明且可隔离时移除该 patch并通知违规 Agent 重读，无法证明时停止并保护全 workspace 的其它内容。

- **Journey**: Steps 6-7.

### FR-1100 Human Review 的编辑、Discussion 与明确结论
<a id="fr-1100"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-08, BS-11; `story.md:129-147`; `flow.md L47-L52, L66-L72`

Human review 页面必须允许对当前文档 revision 直接编辑或创建、回复 inline discussion，并显示当前 revision、未解决 threads 和本轮是否已编辑。

Human 必须用 `comment` 或 `no comment` 明确结束本轮；本轮发生文档修改时，页面不得允许 `no comment`，直接提交同等信号也不得形成 PASS。系统必须先保存并提交 Human 修改与 discussion，再交给 Agent reviewer；未保存编辑、未解决 discussion 或 `comment` 均不是 Human PASS。

- **Journey**: Steps 6-7.

### FR-1200 Story 的独立 Sage Review 与多轮返工
<a id="fr-1200"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-08, BS-09; `story.md:129-137`; `flow.md L47-L57`

首轮 Story review 必须对同一 committed Story revision开放 Human review并启动独立 Sage review；Sage 与 Scribe 使用独立任务上下文，Sage只留下评审内容和绑定当前 digest 的 verdict，不作为 Story author 或流程批准者。

Human 提交本轮内容后，Sage 必须针对最新 committed revision以及 Human diff/discussions 评审。只有 Human 和 Sage 都对同一当前 digest 给出 PASS 且没有未解决 discussion 时本轮通过；任一方未通过则由原 Scribe 上下文响应，形成新 revision并使旧 verdict 失效。

- **Journey**: Step 6.

### FR-1300 M-SPEC 的 Sage 起草
<a id="fr-1300"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-10; `story.md:139-142`; `flow.md L59-L66`

当前 Story revision 的 Human 与 Sage review 都通过后，系统必须在同一 release 上打开 `spec.md` 编辑页、保持 Human 只读，并让 Sage 继承已确认 Story 与 review 上下文起草 Spec；Sage 返回前不得开放 Human 编辑。

Sage 返回后，系统必须验证 Spec 非空、需求身份唯一、具有必要 Source 与 metadata，并遵守有效 FR 数量上限；有效草案只提交 `spec.md` 后开放 Human review。结构失败须在页面定位到需求或文档位置并返回 Sage 修订，不得启动 Lex 或进入 M-ACC。

- **Journey**: Step 7.

### FR-1400 M-SPEC Human/Lex 语义 Review 与格式验收
<a id="fr-1400"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-09, BS-10, BS-11; `story.md:134-147`; `flow.md L66-L74`

系统必须对同一 Spec revision开放 Human review并启动独立 Lex review；Lex 只能在取得当前写权后留下 inline discussions，并返回绑定精确 digest 的语义 verdict。

Human 修改或提交意见后，系统必须先提交 Human revision，再让 Lex 重读并生成意见。只有当前 revision 收到 Human `no comment`、Lex PASS且没有未解决 discussion时语义 review完成；否则由原 Sage上下文响应并形成使旧 verdict失效的新 revision。

语义 review通过后必须执行确定性格式验收；格式错误须定位并返回 Sage修订，格式通过才进入 M-ACC。评审期间 Human 发现 Story 级问题时可使用 FR-1500 的返回路径。

- **Journey**: Step 7.

### FR-1500 Human 主导的合法返回上游
<a id="fr-1500"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-12; `story.md:149-152`; `flow.md L75-L75, L79-L85`

在 M-SPEC 中 Human 可明确返回 M-STORY；在 M-ACC 中 Human 可返回 M-SPEC，或在确认是 Story 问题时返回 M-STORY。Agent 或 reviewer可通过评审意见建议目标，但不能自行移动流程指针；页面只提供当前阶段合法的上游目标并要求 Human明确确认。

执行返回时必须保留历史 artifact/review，并把目标及受影响下游 verdict、格式结果和批准 evidence标为 stale或superseded；流程从目标阶段重新完成，不删除 Git历史，也不复用旧 PASS推进。

- **Journey**: Step 7.

### FR-1600 M-ACC 的 Acceptance 起草与 Review
<a id="fr-1600"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-09, BS-11, BS-13; `story.md:154-157`; `flow.md L77-L85`

Spec 语义与格式均通过后，系统必须在同一 release 上打开 `acceptance.md` 编辑页、保持 Human只读，并让 Sage延续需求上下文，基于当前 Story/Spec digests起草 Acceptance。每个有效 FR/NFR必须有对应 Acceptance或明确可验证的 No Acceptance理由。

Sage返回后，系统提交 Acceptance revision并复用 M-SPEC 的单写者、Human/Lex独立 review、明确 Human信号、多轮返工和格式验收规则；所有结论绑定当前 Acceptance及上游 digests。通过后导航到 Project current页并进入 M-LOCK-1；上游变化使旧 Acceptance结论失效。

- **Journey**: Step 7.

### FR-1700 M-LOCK-1 三文档批准与只读锁定
<a id="fr-1700"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-14; `story.md:159-162`; `flow.md L87-L93`

仅当当前 `story.md`、`spec.md`、`acceptance.md` 的必需 review、discussion与格式结果全部通过时，Project current页才显示可用的 M-LOCK-1批准动作，并展示其绑定的三份文档版本身份。批准前不得创建本次实现 Issues。

只有已认证 Human可批准匹配当前 run和三件套版本的 gate；Agent、旧挑战或 stale版本不得生效。有效批准必须使三份文档在产品中强制只读，并持久记录 actor、时间、批准挑战、revision与digests；后续写入不得改变文件内容。

- **Journey**: Steps 7-8.

### FR-1800 M-LOCK-1 后的 GitHub Issue 创建与 Project 关联
<a id="fr-1800"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-14, BS-15; `story.md:159-167`; `flow.md L94-L95`

M-LOCK-1批准后，系统必须为锁定 Spec中每个 Valid不为 `❌` 的 FR/NFR创建或复用一个 GitHub Issue；Issue title以精确的单一 `[{ID}]` requirement token开头，body包含 requirement ID、锁定 Spec section链接和对应 Acceptance section链接，并关联 foundation manifest指定的 release GitHub Project。

reconcile必须同时核对 repository、spec、requirement、锁定三件套身份、Issue内容和Project关联，不得仅凭相似标题复用。重复、并发、重启或远端成功但本地确认丢失时，不得产生第二个匹配 Issue或Project item；匹配冲突或证据不足时须显示冲突并停止新增候选。

Project current页必须逐需求显示创建、复用、关联、失败或不确定结果。只有全部目标 Issue身份匹配且已关联后本步骤完成；部分失败可修复后重试，不回滚已成功外部 Issue。

- **Journey**: Step 8.

### FR-1900 Semantic Task、Agent Session 与受控结果
<a id="fr-1900"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-05, BS-08, BS-09, BS-10, BS-13, BS-15; `story.md:114-167`; `flow.md L38-L57, L63-L72, L81-L84`

每次 Scribe、Sage或Lex任务必须持久绑定 run、step、role、artifact/review digests、write scope、结果合同、attempt与session身份；author与独立reviewer不得共享session，同一session同时最多执行一个active turn。

调用超时、连接中断或浏览器关闭不能被当作 Agent已停止；系统必须先按原task/session核对状态和结果，不得立即重复派发。只有role、任务身份、输入artifact与结果合同匹配的输出可改变文档或review；空、非法、stale或越权结果不得推进。

session确认丢失时，原attempt必须保留为中断或丢失状态，并从同一权威输入建立新attempt；页面应让用户识别上下文已恢复或重建，不得猜测 PASS。

- **Journey**: Steps 6-7.

### FR-2000 受控 Git Revision 与无关工作区保护
<a id="fr-2000"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-04, BS-06, BS-07, BS-09, BS-15; `story.md:109-137`; `flow.md L31, L45-L55, L69-L72`

系统为文档 revision提交 Git时，只能包含当前阶段预期的受控文档；workspace中已有的 staged、unstaged、untracked及其它文档修改必须保持不变。

每次受控提交必须可追溯到预期文档digest、parent、result commit、actor、run、round和task。提交失败不得显示 revision完成或启动下一轮 review；文档来源无法证明、index冲突或目标branch移动时必须停止并显示可操作冲突，不得全仓库重置、检出或强制推送。

- **Journey**: Steps 4-7.

### FR-2100 全流程中断恢复与外部副作用 Reconcile
<a id="fr-2100"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-15; `story.md:164-167`; `flow.md L13, L23, L45-L55, L69-L72, L84-L94`

系统必须持久保存当前 run/step/revision、write ownership、review round/verdict、artifact与commit身份、task/attempt/session、Human waits/gates、外部操作身份、状态和最近错误；浏览器内存或Agent transcript不能是唯一事实源。

Louke、浏览器、网络或Agent会话中断后，用户必须回到最后已保存步骤和同一artifact revision；已完成动作不重复，结果未知的动作不自动 PASS。对repository、branch、Project、Issue等外部副作用，恢复先按已记录稳定身份查询实际状态：确认完成则补记evidence，确认未发生才重试，冲突或无法判断则在当前步骤显示需要处理的目标与已知后果。

- **Journey**: Steps 1-8.

## Non-Functional Requirements

### NFR-0100 原子性、CAS 与竞争请求
<a id="nfr-0100"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-03, BS-07, BS-14, BS-15; `story.md:124-167`; `flow.md L28, L47-L57, L69-L72, L91-L94`

run状态、对应event、write ownership、review结果和适用artifact binding必须原子一致，不得出现状态已推进而无对应evidence，或evidence存在而状态未改变。

两个使用同一预期revision/version的竞争状态或文档写入至多一个成功；失败方获得当前revision和稳定冲突结果。Backlog routing、Project/run创建、M-LOCK-1批准与Issue reconcile在重复和并发请求下必须幂等。

外部资源reconcile必须按资源类型使用 foundation manifest或既有operation evidence中的provider namespace、稳定资源ID及适用的name/version/head等精确可比身份；不得只凭模糊名称或标题选择。零个、多个、字段冲突或证据不足的匹配必须保持冲突或需要处理，不得猜测复用或创建。

- **Journey**: Steps 2-4, 6-8.

### NFR-0200 可追溯性与 Secret 安全
<a id="nfr-0200"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-02, BS-07, BS-14, BS-15; `story.md:76-81`; `flow.md L18-L23, L45-L55, L69-L72, L91-L94`

用户可从 run的公开状态与artifact追踪 setup决定、步骤转移、文档revision、review、gate、Agent task、Git commit和外部operation；每条记录必须具有适用的run/step/attempt、actor、time、correlation identity、输入/输出digest与结果。

Story、Spec、Acceptance、Issue和Project之间的identity与digest链必须可双向追踪，后续变化不得静默改写历史。credential、token、cookie、provider secret及完整认证材料不得进入manifest、需求文档、event、log、错误详情、commit message或Agent输入；仅允许非秘密identity、redacted诊断和digest。

- **Journey**: Steps 2, 4-8.

### NFR-0300 安装产物的公开入口 E2E
<a id="nfr-0300"></a>

| Valid | Testable | Decided |
|---|---|---|
| ✅ | ✅ | ✅ |

- **Source**: BS-01, BS-02, BS-03, BS-04, BS-05, BS-06, BS-07, BS-08, BS-09, BS-10, BS-11, BS-12, BS-13, BS-14, BS-15; `story.md:62-81`; `flow.md L5-L95`

发布候选必须能从干净 Git workspace 使用安装后的 `lk serve` 和受支持桌面浏览器走完 Setup、M-START、M-STORY、M-SPEC、M-ACC、M-LOCK-1及Issue/Project关联；不得预写内部流程状态、调用内部对象或使用CLI推进需求工作流。

公开旅程必须证明 Human编辑、inline discussion、多轮author/reviewer返工、写入冲突、服务重启、Agent断连和GitHub操作确认丢失后仍可从用户可见入口继续，且不跳步、不重复副作用、不使用旧revision PASS。发布前必须用真实OpenCode与GitHub测试身份完成最小端到端验证；替代服务仅可用于可辨识的确定性测试。

- **Journey**: Steps 1-8.

## Out of Scope

- M-LOCK-1 与 Issue/Project 关联之后的 Test Plan、Architecture、Interfaces、实现、测试、安全、发布和归档流程。
- `flow.md` L96之后的候选流程，以及任意阶段的通用 return-upstream、bounded waiver、no-new-debt adoption和通用 lifecycle hooks。
- 旧版 active run向本工作流迁移、双版本共存或兼容桥。
- 使用 CLI推进 M-STORY、M-SPEC、M-ACC或M-LOCK-1。
- 多用户同时登录、多人共同审批、移动端与完整离线模式。
- 重做 Workbench整体视觉系统、建设通用协作文档平台或任意文件锁服务。
- Agent替 Human作出 Go/Park/No-Go、上游返回或M-LOCK-1批准。

## Downstream documents

**Test Plan** 将把本合同的 24 个需求单元映射为公开出口可观察的验收与回归场景，重点覆盖完整八步旅程、Human/Agent review循环、竞争写入、中断恢复和外部副作用reconcile；它不改变本 Spec 的产品政策。

**Architecture / Interfaces** 将定义 workflow driver、持久化状态、artifact revision与write lease、review verdict、semantic task/session、Git提交隔离和外部资源reconcile的技术边界，同时保留本 Spec规定的用户可见路径与authority。

**Development** 将按锁定 requirement/Issue身份交付从安装产物到M-LOCK-1/Issues的实现，并保持每项变更、测试evidence与对应 FR/NFR可追溯；不得把后续流程能力并入本 Spec。

**Release** 将验证安装后的公开入口、真实OpenCode/GitHub最小旅程、升级后setup reconcile及文档锁定结果；M-LOCK-1之后的设计、开发、测试与发布工作流由后续 Spec另行定义。
