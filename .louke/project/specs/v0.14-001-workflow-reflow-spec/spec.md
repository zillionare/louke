---
status: Draft v2 (pending M-LOCK-1)
spec_id: v0.14-001-workflow-reflow-spec
bound_story: STR-1402
bound_story_digest: sha256:e04e88b336c7f08a3f67ef40354fa35c3e78ec66935805aa6f2da7272dfd0634
spec_digest: sha256:a627a43b7ad1f2834b14cebb8c8f78af949676722e9319059d02bd0e7426f596
acceptance_digest: sha256:992fcdc3b7a70cedc2f16b867bfd313b4cc64bd645350c202141c72f09747556
doc_index_digest_sha256: sha256:384084747a9a67bca6eba544711da7e8de2e3a65883d41fa99ed081019ca528b
revision: 2
lex_review_artifact: .louke/project/specs/v0.14-001-workflow-reflow-spec/spec-review.md
---

# v0.14 Workflow Reflow — Requirements Spec

> 本合同仅覆盖 `flow.md` L1-L95，即从安装与启动到 M-LOCK-1 创建并关联 GitHub Issues。Story 的 User Stories、Happy Path 和风险叙事以 `story.md` 为唯一权威来源，不在此复述。
>
> Draft v2 含 21 FR + 3 NFR（24 单元），可由 `acceptance.md` 外部断言；M-SPEC 起草与 Lex peer review 已完成（见 `spec-review.md`）。提交 M-LOCK-1 时只接受已认证 Human 对当前 `bound_story_digest` + `doc_index_digest_sha256` 的批准；批准前不得创建本次实现 Issues（见 FR-1700 / FR-1800）。

## Functional Requirements

### FR-0100 `lk serve` 启动诊断与产品入口

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-01; `flow.md` L5-L13
- Human 在目标 workspace 执行 `lk serve` 时，Runtime 必须在开放工作流写操作前检查 Louke runtime identity、依赖、配置、模型/provider、OpenCode 可用性和 workspace identity，并在 Web 中提供逐项状态、非秘密诊断及可执行修复动作。
- 检查通过且 setup manifest 当前有效时，系统必须打开 Web Workbench 的 release 请求入口；首次、缺失、冲突或失效 setup 必须进入 Workspace Setup。
- 启动失败必须返回非零结果并保留可操作诊断；重复启动不得重复初始化 workspace、OpenCode 或远程资源。

---

### FR-0200 Workspace Setup Preview、确认与 Manifest

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-01, BS-02, BS-15; `flow.md` L15-L23
- Runtime 必须从 Git remote、已有有效项目资料和认证身份推导项目名称、repository、owner、release version 等必要候选值，并在 Web preview 中显示每个候选值及来源；确认前不得创建或修改 repository、release GitHub Project、branch 或项目配置。
- 缺失值、语义冲突、歧义或授权要求必须持久化为 `waiting_human`；Human 的选择必须绑定 setup revision，并记录 actor、选择值、候选来源和时间。Runtime 不得静默选择冲突值。
- Human 确认当前 preview 后，Runtime 必须 create-or-reuse 必要资源并发布 foundation manifest，至少记录 workspace/repository/release/branch/Project 的稳定身份、setup revision、资源状态和操作 evidence。只有资源真实存在且身份一致时 setup 才可完成。
- 重试或重启必须先按稳定资源身份 reconcile；零个、多个或冲突的远程匹配必须继续等待 Human，不得模糊选取或重复创建。

---

### FR-0300 Web Release 请求与单活跃主 Release

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-03; `flow.md` L25-L29
- `/projects/new` 必须收集非空的一句话设想和合法 release version，在产生副作用前显示当前输入和 workflow identity 的 preview，并只接受 Human 对当前 preview 的确认。
- 同一 workspace 已有活跃主 release 时，确认新 release 请求必须幂等写入 Runtime-native Backlog，展示阻塞原因并结束本次创建会话；不得创建第二个主 Project、WorkflowRun、release branch 或 Spec 目录，也不得进入 M-STORY。
- 相同请求 identity 与内容 digest 的重复或并发确认最多产生一个 Backlog entry；该 entry 及阻塞原因必须可在 Web 查询并在重启后保留。

---

### FR-0400 新 Release 的 `main` 前置检查与 Foundation

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-04, BS-15; `flow.md` L29-L31
- 对可开始的 release，Runtime 必须在创建新 release branch 前刷新 declared remote，并证明上一主开发分支的预期修改已合入 declared remote 的权威 `main`。本地 `main` 与权威 `main` 不同，或上一主开发分支相对权威 `main` 为未合入、ahead、behind、diverged 或无法判定时，必须阻塞，展示相关 full ref、SHA、可判定关系和修复动作；Human 完成修复后必须重新执行检查，不得以确认动作跳过该证明。
- 前置检查通过后，Runtime 必须 create-or-reuse 本 release 的 Project/WorkflowRun、release GitHub Project、基于本次检查所得权威 `main` SHA 的 release branch 和 Spec 目录；每项操作必须使用稳定 idempotency identity 并写入 evidence。分支实际起点 SHA 与该权威 `main` SHA 不一致时 foundation 不得完成。
- 任一 foundation 操作部分成功、权限失败或结果不确定时，不得报告完成或进入 M-STORY；恢复时必须先 reconcile 已发生副作用。

---

### FR-0500 初始 `story.md` Revision 与页面跳转

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-04; `flow.md` L30-L32
- Runtime 必须从 canonical Story template 创建本 release 的 `story.md`，把 Human 原始设想写入模板指定的原始输入位置，保留模板其余内容，并形成绑定输入 digest、文件 digest、actor 和 commit SHA 的初始 revision。
- 同一初始化 identity 重试时，已存在且 digest 匹配的目录、文件和 commit 必须复用；内容冲突必须停止并显示 `STORY_INITIALIZATION_CONFLICT`，不得覆盖现有文件。
- 初始 revision 提交成功后，Web 必须导航到本 release 的 Story 编辑页，并显示当前 run、阶段和 revision identity。

---

### FR-0600 Runtime 权威工作流与 Web 当前状态

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-07, BS-15; `flow.md` L34-L95
- Runtime 必须是 M-STORY、M-SPEC、M-ACC、M-LOCK-1 的当前步骤、合法转移、write ownership、review round 和状态的唯一写入者；Agent 消息、文档文字或客户端提交的目标阶段不得直接推进流程。
- Web Project 页面必须从持久化事实源显示当前步骤、状态、artifact revision、当前写者、待处理 Human 动作、Agent task/session、review 结论和最近错误，并在刷新或重启后重建同一状态。
- 只有当前步骤声明且前置 evidence 满足的动作可执行；非法或 stale 动作必须返回 `WORKFLOW_STATE_CONFLICT` 且不改变 run、文档或外部资源。

---

### FR-0700 Scribe 调查、分流建议与 Human 裁决

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-05, BS-06; `flow.md` L34-L43
- M-STORY 开始时，Runtime 必须打开绑定当前 run 的小型 Chat，收回 Story 的 Human 编辑权，并派发一个 Scribe semantic task；任务输入至少包含 run/step/attempt identity、spec ID、当前 Story revision/digest、canonical Story template path及其版本或digest、Human 原始请求、foundation manifest identity，以及适用时的上一轮 feedback digests。任务仅允许 Scribe 更新 `story.md` 和返回 Go/Park/No-Go 建议及理由。
- Runtime 必须持续向 Web 刷新已保存的 Story 内容，但在 Scribe 初次任务返回前保持只读。Scribe 建议不得改变流程；系统必须等待已认证 Human 对当前 Story revision 明确选择 Go、Park 或 No-Go。
- stale revision 的裁决、Agent 自行裁决或不在三个候选中的值必须拒绝，状态保持等待 Human。

---

### FR-0800 Park/No-Go 的 Backlog 与安全退出

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-06, BS-15; `flow.md` L42-L42
- Human 对当前 revision 裁决 Park 或 No-Go 后，Runtime 必须幂等保存 Story、决定、理由、actor、digest 和来源 run 到 canonical Backlog，并把本次 Project/WorkflowRun 置为相应终态；不得进入 M-SPEC。
- Runtime 只有在证明本地 release branch 未承载初始 Story 之外的用户或未归属修改时才可删除该未使用分支。无法隔离修改或远程分支已存在时，必须保留分支并进入 `needs_attention`，不得 reset、force-delete 或回退无关内容。
- 重复处理同一裁决不得产生重复 Backlog entry 或重复删除；原 Story 和裁决历史必须继续可读。

---

### FR-0900 Go 后的访谈、Story 完成与交接 Revision

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-06; `flow.md` L43-L46
- Human 裁决 Go 后，Runtime 必须让同一 Scribe task/session 继续访谈。每条 Human 回复必须先以唯一 correlation identity 和单调 run event sequence 持久化到 run/task，再以同一 correlation identity 发送到该 session；发送重试不得生成第二条逻辑回复。
- Scribe 声明访谈完成时，Runtime 必须验证 `story.md` 相对初始或上一已提交 revision 有实际内容变更且文件已落盘；无变更时返回 `STORY_CHANGE_REQUIRED` 并保持 Scribe task 未完成。
- 验证通过后，Runtime 必须提交仅包含当前 `story.md` 的交接 revision，并记录文件 digest、parent commit、commit SHA、Scribe task/attempt/session 和 Story handoff result；提交成功前不得开始 review。

---

### FR-1000 文档 Write Ownership、CAS 与脏编辑保护

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-07, BS-09; `flow.md` L47-L57, L63-L72, L81-L84
- 对 `story.md`、`spec.md` 和 `acceptance.md`，Runtime 必须在任一时刻只授予一个写者有效 write lease；保存必须同时匹配 run、document、lease holder、lease id 和 version token/revision。失配必须以 HTTP 409 返回包含 `DOCUMENT_WRITE_CONFLICT` 的响应且不覆盖当前 bytes。
- Runtime 收回 Human 写权前必须检测浏览器未保存内容；存在脏编辑时必须等待保存或显式取消，不得让 Agent 写入覆盖。第二轮起页面通常保持 Human 可写，仅在 Scribe、Sage 或 reviewer 实际持有 lease 期间临时只读。
- 非 lease holder 的磁盘修改不得成为被接受 revision。只有当前受控文档最近一次已接受 revision 的精确 bytes/digest 可取得，且能据此证明并隔离违规 patch 时，Runtime 才可只移除该 patch并通知违规 Agent重读；基线不可取得或无法证明来源时必须停止于 `needs_attention`，不得全仓库 revert。基线的保存方式与 lease 隔离算法由 Architecture 决定。

---

### FR-1100 Human Review 的编辑、Discussion 与明确结论

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-08, BS-11; `flow.md` L47-L52, L66-L72
- Human review 页面必须允许对当前文档 revision 直接编辑或创建/回复 canonical inline discussion，并显示当前 revision、未解决 threads 和本轮是否发生 Human 编辑。
- Human 必须用 `comment` 或 `no comment` 明确结束本轮；本轮发生过任何 Human 文档修改时，`no comment` 必须在 UI 禁用且服务端以 `HUMAN_REVIEW_EDITED` 拒绝伪造提交。
- Runtime 必须在交给 Agent reviewer 前，以 CAS 保存并提交 Human 的文档变更及 discussion；review 结论必须绑定保存后的精确 document digest。未保存编辑、open/reopen thread 或 `comment` 均不得计作 Human PASS。

---

### FR-1200 Story 的独立 Sage Review 与多轮返工

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-08, BS-09; `flow.md` L47-L57
- 首轮 Story review 必须对同一 committed Story revision并行开启 Human review 与独立 Sage review；Sage 与 Scribe 必须使用不同 task/session，Sage 只可留下 review 内容和 digest-bound verdict，不得改写 Story 产品叙事或推进流程。
- Human 本轮提交后，Runtime 必须让 Sage 基于最新 committed revision和 Human diff/discussions 生成意见；Sage 的受控文档变更必须单独提交。Human 与 Sage verdict 均为 PASS 且均绑定当前 digest 时，本轮才通过。
- 任一方未通过时，Runtime 必须把完整意见交给原 Scribe session响应；每次 Scribe 修订形成新 revision后，旧 verdict 自动 stale并开始下一轮。Agent task/session上下文必须延续，但文档和结构化输入始终是权威事实。

---

### FR-1300 M-SPEC 的 Sage 起草

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-10; `flow.md` L59-L66
- 当前 Story revision 的 Human 与 Sage review 都通过后，Runtime 必须导航到 `spec.md`、保持 Human 只读，并派发 Sage author task；输入必须包含已批准 Story digest、Story review上下文、canonical Spec模板、允许写路径和本次 revision。
- Sage 返回前不得开放 Human 编辑；返回后 Runtime 必须验证 `spec.md` 非空、每个 FR/NFR 具有四位唯一 ID、Source、canonical metadata，且草案 FR+NFR 总数不超过 30，然后提交仅该文档并开放 Human review。
- 结构失败必须返回可定位 requirement/line 的错误并把任务留在 Sage修订，不得启动 Lex或进入 M-ACC。

---

### FR-1400 M-SPEC Human/Lex 语义 Review 与格式验收

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-09, BS-10, BS-11; `flow.md` L66-L74
- Runtime 必须对同一 spec revision开放 Human review并启动独立 Lex review；Lex只能在获得 write lease 后写 canonical inline discussions，并返回绑定精确 digest的语义 verdict。
- Human 修改或提交意见后，Runtime必须先提交 Human revision，再让 Lex重读该 revision并生成意见；Lex变更另行提交。只有 Human `no comment`、Lex PASS、无 open/reopen discussion且两者绑定当前 digest时，语义 review才结束。
- 未通过时，Runtime必须让原 Sage session响应 Human和Lex意见、提交新 revision并重开一轮；旧 verdict自动 stale。语义 review通过后，Runtime必须执行确定性格式验收；格式失败返回 Sage修订，格式通过才可进入 M-ACC。

---

### FR-1500 Human 主导的合法返回上游

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-12; `flow.md` L75-L75, L79-L85
- 在 M-SPEC 中 Human 可明确返回 M-STORY；在 M-ACC 中 Human 可明确返回 M-SPEC，或在指出 Story 问题时返回 M-STORY。Agent只能提出建议，不能移动流程指针。
- 返回请求必须绑定当前 run revision并只展示该阶段声明的合法上游目标；任意目标以 `UPSTREAM_RETURN_TARGET_INVALID` 拒绝且不改变状态。
- 执行返回时，Runtime必须保留历史 artifact/review，标记目标及其下游 verdict、格式结果和批准 evidence为 stale/superseded，并从目标阶段重新完成所需 author/review；不得删除 Git历史或复用旧 PASS推进。

---

### FR-1600 M-ACC 的 Acceptance 起草与 Review

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-13, BS-09, BS-11; `flow.md` L77-L85
- Spec 语义与格式均通过后，Runtime必须导航到 `acceptance.md`、保持 Human只读，并让原 Sage上下文基于当前 Story/Spec digests起草 Acceptance；每个有效 FR/NFR必须有对应 `# FR-XXXX`/`# NFR-XXXX` section或明确 No Acceptance理由。
- Sage返回后，Runtime必须提交 Acceptance revision并复用 FR-1400 的 Human/Lex独立 review、write lease、明确 Human信号、多轮返工和格式验收规则，且所有结论绑定当前 Acceptance digest及其上游 digests。
- Acceptance通过后，Runtime必须导航到 Project current页面并把流程置于 M-LOCK-1；任一上游 digest变化必须使 Acceptance review结论 stale。

---

### FR-1700 M-LOCK-1 三文档批准与只读锁定

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-14; `flow.md` L87-L93
- 仅当当前 `story.md`、`spec.md`、`acceptance.md` 的必需 review和格式结果全部通过时，Project页才可显示 M-LOCK-1 `approve`；gate必须绑定三份文件各自 digest及确定性的joint digest，并显示这些身份。
- 只有已认证 Human可批准匹配当前 run revision和joint digest的 gate；Agent、自报文本、旧challenge或stale digest必须拒绝。批准前不得创建本次实现 Issues。
- 有效批准必须把三份文档转为服务端强制只读并持久化 actor、time、challenge、revision和digests。批准后的 Web/API写请求必须以 HTTP 423 返回包含 `REQUIREMENTS_LOCKED`，且文件 bytes不变。

---

### FR-1800 M-LOCK-1 后的 GitHub Issue 创建与 Project 关联

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-14, BS-15; `flow.md` L94-L94
- M-LOCK-1 批准后，Runtime program operation必须为锁定 Spec中每个 `Valid` 不为 `❌` 的 FR/NFR create-or-reuse一个 GitHub Issue；title必须以该需求ID的字节串 `[{ID}]` 开头，body必须包含需求ID、锁定 Spec section link和对应 Acceptance section link。
- 每个 Issue必须关联 foundation manifest指定的本 release GitHub Project。稳定 reconcile identity必须包含 repository、spec_id、requirement ID和锁定 joint digest；title 的首个 requirement token 必须精确等于 `[{ID}]`，但 reconcile 不得只凭 title 前缀判定匹配，还必须核对 body 中的 requirement ID、锁定 section links及Project关联。重复、并发或重启执行不得为同一 identity创建第二个 Issue或第二个 Project item。
- Human批准前、Spec未锁定、Project identity冲突或无法证明已有Issue匹配时，操作不得创建新Issue。远程成功与本地确认之间结果不确定时必须先查询title/body/Project关联再决定复用或创建。
- 仅当所有目标Issue存在、内容身份匹配并关联Project后，本步骤才可完成；部分失败必须显示逐需求状态并保持可重试，不得回滚已成功的外部Issue。

---

### FR-1900 Semantic Task、Agent Session 与受控结果

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-05, BS-08, BS-09, BS-10, BS-13, BS-15; `flow.md` L38-L57, L63-L72, L81-L84
- 每次 Scribe、Sage或Lex dispatch必须创建持久化 task/attempt，绑定 run、step、role、artifact/review digests、write scope、output contract和唯一session identity；author与独立reviewer不得共享session。
- 同一task session同时最多一个active turn。HTTP timeout、SSE断线或浏览器关闭不证明task停止；Runtime必须先按task/session identity查询状态和结果，禁止立即重复dispatch。
- Agent结果只有在role、task/attempt、manifest digest、artifact digest和schema全部匹配时才可接受；空、非法、stale或越权结果不得改变review、文档权威或流程。
- session丢失时必须把原attempt标为 `lost`/`interrupted`并基于同一权威输入创建新attempt；不得把新session伪称为原attempt无缝恢复，也不得猜测PASS。

---

### FR-2000 受控 Git Revision 与无关工作区保护

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-04, BS-06, BS-07, BS-09, BS-15; `flow.md` L31, L45-L55, L69-L72
- Runtime为文档revision提交Git时必须使用显式文件allowlist，提交内容只能包含当前阶段预期的受控文档；已有staged、unstaged、untracked及其它文档改动必须保持字节与index状态不变。
- 提交前后必须记录预期文档digest、parent SHA、result commit SHA、actor、run/round/task identity；commit失败不得被报告为revision完成或触发下一review。
- 预期文档来源无法从记录基线证明、index冲突或目标branch移动时，Runtime必须停止并显示 `CONTROLLED_COMMIT_CONFLICT`，不得执行全仓库reset、checkout或force push。

---

### FR-2100 全流程中断恢复与外部副作用 Reconcile

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-15; `flow.md` L13, L23, L45-L55, L69-L72, L84-L94
- Runtime必须持久化当前run/step/revision、write ownership、review round/verdict、artifact/commit digests、task/attempt/session、Human waits/gates、idempotency keys、外部操作状态和最近错误；浏览器内存或Agent transcript不得是唯一事实源。
- Louke进程、浏览器、网络或OpenCode中断后，恢复必须回到最后已提交步骤和同一artifact revision；已完成步骤不得因恢复而重复执行，结果未知的操作不得自动PASS或推进。
- 对repository/branch/Project/Issue及其它外部操作，恢复必须按稳定identity查询实际状态；确认已完成则补记evidence，确认未发生才安全重试，冲突或无法判断则进入 `needs_attention`并列出操作、target和已知副作用。

---

## Non-Functional Requirements

### NFR-0100 原子性、CAS 与竞争请求

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-03, BS-07, BS-14, BS-15; `flow.md` L28, L47-L57, L69-L72, L91-L94
- run状态、对应event、write lease/review结果及适用artifact binding必须以事务方式提交，不能出现状态已推进但无对应event/evidence，或event存在但状态未改变。
- 使用相同 expected revision/version token 的两个竞争状态或文档写入至多一个成功；失败方必须得到 HTTP 409 且响应包含当前 revision/token 与 `*_CONFLICT` 稳定代码。
- Backlog routing、Project/WorkflowRun创建、M-LOCK-1批准和Issue reconcile必须在重复及并发请求下保持幂等。
- 外部资源恢复 identity 必须按 resource kind 使用 foundation manifest 或原 operation evidence 中记录的 provider namespace、稳定资源ID及适用的name/version/head SHA等精确可比字段；不同资源类型不得被强制为同一固定元组，也不得仅凭模糊名称或title选择候选。零个、多个、字段冲突或证据不足的匹配必须返回以 `_CONFLICT` 结尾的稳定code或进入 `needs_attention`，不得猜测复用或创建。

---

### NFR-0200 可追溯性与 Secret 安全

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-02, BS-07, BS-14, BS-15; `flow.md` L18-L23, L45-L55, L69-L72, L91-L94
- Web/API必须能从run按顺序查询setup决定、步骤转移、文档revision、review、gate、task/attempt、Git commit和外部operation evidence；每条记录至少包含run/step/attempt、actor、time、correlation identity、适用输入/输出digest和结果。
- Story、Spec、Acceptance、Issue和Project之间的identity与digest链必须可双向追踪；后续内容变化不得静默改写历史记录。
- 原始credential、token、cookie、provider secret及完整认证材料不得出现在manifest、文档、event、log、错误响应、commit message或Agent输入；仅允许非秘密identity、redacted诊断和digest。

---

### NFR-0300 安装产物的公开入口 E2E

| Valid | Testable | Decided |
|---|---|---|
| ⚠️ | ⚠️ | ⚠️ |

- **Source**: BS-01 through BS-15; `flow.md` L5-L95
- 发布候选必须能从干净Git workspace使用安装后的`lk serve`和受支持桌面Web浏览器完成setup、M-START、M-STORY、M-SPEC、M-ACC、M-LOCK-1及Issue/Project关联，不预写Runtime内部状态、不调用内部Python对象，也不使用CLI推进需求工作流。
- 公开入口旅程必须覆盖至少一次Human编辑、inline discussion、多轮author/reviewer返工、CAS冲突、服务重启、Agent断连和GitHub操作成功后确认丢失的reconcile，并证明没有跳步、重复副作用或旧revision PASS。
- 外部stand-in可用于确定性CI，但报告必须标识stand-in；发布前必须以真实OpenCode和真实GitHub测试账户完成最小smoke，证明session恢复及Issue/Project create-or-reuse契约未漂移。

---

## Out of Scope

- M-LOCK-1/Issue关联之后的 Test Plan、Architecture、Interfaces、实现、测试、安全、发布和归档流程。
- 任意阶段通用return-upstream、bounded waiver、no-new-debt adoption、lifecycle hooks和旧active run迁移。
- CLI推进M-STORY/M-SPEC/M-ACC/M-LOCK-1，多用户并发审批、移动端和完整离线模式。
- 重做Workbench整体视觉系统、任意文件锁服务，以及`flow.md` L96之后的候选流程。

## Downstream documents

- **后续 Spec 2 占位**：Test Plan应覆盖本合同的公开入口golden path、各Human/Agent review循环、CAS/lease竞争、重启恢复及外部副作用reconcile；Architecture/Interfaces应定义workflow driver、artifact revision/write lease、review verdict和semantic task/session边界。
- **后续 Spec 3 占位**：Test Plan应覆盖M-LOCK-1之后的设计文档流程；Architecture/Interfaces应定义Test Plan、Architecture、Interfaces三件套的author/reviewer与gate接口。
- **后续 Spec 4 占位**：Test Plan应覆盖Issue到实现、权威测试与发布闭环；Architecture/Interfaces应定义Issue/task/commit/test evidence追踪及release接口。
