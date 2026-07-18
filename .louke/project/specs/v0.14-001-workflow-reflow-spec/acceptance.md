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

# v0.14 Workflow Reflow — Acceptance Criteria

> 每节与 `spec.md` 的一个 FR/NFR 一一对应。所有条件只能通过公开Web/API、持久化artifact/event或外部Git/GitHub/OpenCode边界断言。M-LOCK-1 批准后本 acceptance 与 spec 共同 digest 进入只读；FR-1800 Issue 创建以此 digest 为 reconcile identity 之一。

# FR-0100

### AC-1
- **Given** 一个缺少model/provider或OpenCode的workspace
- **When** Human执行`lk serve`并打开Web
- **Then** Web列出Louke、依赖、配置、model/provider、OpenCode和workspace identity逐项状态，其中缺失项为`BLOCKED`并含非空remediation，release创建入口不可提交。

### AC-2
- **Given** setup manifest有效且所有启动检查通过
- **When** 连续两次执行`lk serve`
- **Then** 两次均可访问Workbench release入口，foundation manifest中的repository、Project和branch identity字节相等，外部adapter的create调用增量均为0。

### AC-3
- **Given** 启动依赖检查失败
- **When** `lk serve`结束
- **Then** 进程退出码非0，stderr含失败dependency名称与非空修复动作，且WorkflowRun与外部create调用数均为0。

# FR-0200

### AC-1
- **Given** Git remote、项目资料和认证身份产生候选值
- **When** Human打开Setup preview
- **Then** 每个必要字段显示value与provenance，且确认前repository、release Project、branch及项目配置的外部写调用数均为0。

### AC-2
- **Given** 两个权威来源对owner产生冲突
- **When** Human未裁决并重启`lk serve`
- **Then** setup仍为`waiting_human`，两个候选及provenance保持字节相等，WorkflowRun数和外部修改数均为0。

### AC-3
- **Given** Human对setup revision R选择候选值并确认
- **When** Runtime完成或重试setup
- **Then** foundation manifest记录R、actor、选择、全部候选来源、资源稳定ID和operation evidence；相同确认重试不增加repository、Project或branch数量。

### AC-4
- **Given** release Project查询返回零个、多个或身份冲突结果
- **When** setup reconcile执行
- **Then** Web显示`waiting_human`及精确匹配详情，不按模糊title选择，manifest不标记setup complete。

# FR-0300

### AC-1
- **Given** `/projects/new`收到空story或非法release version
- **When** Human请求preview
- **Then** 页面显示字段级错误且Project、WorkflowRun、Backlog entry和release branch数量均不变。

### AC-2
- **Given** workspace已有一个active主release
- **When** 相同新release preview被重复或并发确认
- **Then** Web显示本次会话已因active release结束，canonical Backlog中恰有一个匹配request identity/digest的entry，第二个Project、WorkflowRun、branch和Spec目录均不存在。

### AC-3
- **Given** 上述blocked Backlog entry已存在
- **When** `lk serve`重启并打开Projects页
- **Then** entry仍显示原story、version、阻塞原因、created time和source identity。

# FR-0400

### AC-1
- **Given** declared remote刷新失败或上一开发分支尚未合入权威main
- **When** Human确认release preview
- **Then** Web显示相关full ref与SHA或refresh错误，状态非PASS，release branch、Spec目录和M-STORY task均未创建。

### AC-2
- **Given** remote main SHA为M且前置检查通过
- **When** Runtime完成foundation
- **Then** Project、WorkflowRun、release Project、release branch和Spec目录各存在一个，release branch起点字节等于M，evidence包含每项stable identity。

### AC-3
- **Given** release Project已创建但本地确认前网络中断
- **When** 服务恢复并重试同一foundation identity
- **Then** Runtime先查询并复用原Project node ID，Project和branch总数不增加，未完成项继续执行而M-STORY不提前开始。

### AC-4
- **Given** declared remote刷新成功，但本地`main`与权威remote `main`不一致、上一开发分支相对权威`main`为ahead/behind/diverged/无法判定，或已创建release branch的起点不等于本次检查所得权威`main` SHA M
- **When** Runtime执行或恢复foundation前置检查
- **Then** Web显示每个相关full ref、SHA、关系与非空remediation，foundation状态非PASS且M-STORY task数不增加；Human完成修复并重新检查通过前，确认请求不能绕过阻塞，最终release branch起点SHA字节等于M。

# FR-0500

### AC-1
- **Given** 有效Human设想S和canonical Story template T
- **When** 初始Story创建成功
- **Then** `story.md`指定原始输入位置包含S，T其余预置章节保持存在，revision evidence含input digest、file digest、actor和commit SHA。

### AC-2
- **Given** 相同初始化identity已有digest匹配的Story commit
- **When** 初始化重试
- **Then** 复用同一文件digest与commit SHA且新增commit数为0；若bytes不匹配则响应含`STORY_INITIALIZATION_CONFLICT`且现有bytes不变。

### AC-3
- **Given** 初始Story commit成功
- **When** 浏览器跟随Runtime响应
- **Then** URL指向当前spec的Story编辑页，页面显示相同run ID、M-STORY和revision identity。

# FR-0600

### AC-1
- **Given** run当前在M-SPEC revision R
- **When** Web、Agent message或文档文字请求直接切换到M-LOCK-1
- **Then** 响应含`WORKFLOW_STATE_CONFLICT`，current step、R、artifact bytes、gate与Issue数量均不变。

### AC-2
- **Given** 任一阶段处于waiting、blocked或review中
- **When** Human刷新Project页或重启服务后重开该页
- **Then** 页面显示与持久化出口相同的step、status、artifact revision、writer、round、task/session、verdict和last error。

# FR-0700

### AC-1
- **Given** M-STORY开始且Story revision为R
- **When** Runtime派发Scribe调查
- **Then** Chat显示一个绑定run/R的Scribe task，Story编辑控件为disabled，task write scope只包含当前`story.md`；公开task manifest含run/step/attempt、spec ID、R及其digest、Story template path及版本或digest、Human原始请求、foundation manifest identity，并在非首轮时含上一轮feedback digests。

### AC-2
- **Given** Scribe返回Go/Park/No-Go建议及理由
- **When** Human尚未裁决
- **Then** run保持`waiting_for_human`且current step仍为M-STORY，M-SPEC task数为0。

### AC-3
- **Given** Human提交stale revision、Agent身份或候选外裁决
- **When** 服务端验证
- **Then** 请求被拒绝且裁决记录为空；当前Human对R提交三个合法值之一时记录包含actor、R、value和time。

# FR-0800

### AC-1
- **Given** Human对当前Story选择Park或No-Go并提供理由
- **When** Runtime完成退出
- **Then** canonical Backlog恰有一个entry，含Story identity/digest、decision、reason、actor和source run，Project为对应终态且M-SPEC task数为0。

### AC-2
- **Given** 本地release branch仅含初始化Story commit且无其它修改
- **When** Park/No-Go清理执行两次
- **Then** 第一次后该local ref不存在，第二次为no-op，Backlog entry仍只有一个。

### AC-3
- **Given** release branch含未归属commit、dirty文件或remote ref
- **When** Park/No-Go清理执行
- **Then** run为`needs_attention`，页面列出阻塞identity，相关ref和用户文件bytes保持不变且无force/reset调用。

# FR-0900

### AC-1
- **Given** Human已裁决Go且原Scribe session为S
- **When** Human回答访谈问题
- **Then** 持久化出口中该回复的`reply_persisted` event.seq小于同一correlation identity的`reply_dispatched` event.seq，session S transcript可按该identity查询到字节相同的消息；发送重试后逻辑回复、transcript消息和Scribe session仍各只有一个。

### AC-2
- **Given** Scribe声明完成但Story digest未变化
- **When** Runtime验证结果
- **Then** task收到`STORY_CHANGE_REQUIRED`，状态仍为authoring且review task数为0。

### AC-3
- **Given** Story已发生有效变化
- **When** Runtime接受Scribe handoff
- **Then** 新commit只含当前`story.md`，evidence含digest、parent/commit SHA和task/attempt/session，随后才出现review tasks。

# FR-1000

### AC-1
- **Given** Human与Agent持有同一旧version token或错误lease
- **When** 两者保存同一文档
- **Then** 最多一个成功，失败响应HTTP 409且body含`DOCUMENT_WRITE_CONFLICT`和当前token，落盘bytes等于成功者内容。

### AC-2
- **Given** Human浏览器存在未保存编辑
- **When** Agent请求write lease
- **Then** lease保持未授予且页面提示保存或取消；Human内容保存或明确取消前Agent写请求不能改变文件。

### AC-3
- **Given** 非holder修改受控文档且patch可精确隔离
- **When** Runtime保护Human保存
- **Then** 仅当最近已接受revision的精确bytes/digest可从公开revision evidence核对时，系统才只移除违规patch、保留其它workspace/index bytes并通知Agent重读；基线不可取得或来源不可隔离时状态为`needs_attention`且不执行repository-wide revert。

# FR-1100

### AC-1
- **Given** Human打开当前revision的review页
- **When** 直接编辑或创建inline discussion
- **Then** 页面标记本轮edited或显示可由`lk discuss query`识别的thread，并显示当前revision与open/reopen数量。

### AC-2
- **Given** 本轮Human已修改一个byte
- **When** UI渲染或客户端直接提交`no comment`
- **Then** UI按钮disabled，直接请求被拒绝且响应含`HUMAN_REVIEW_EDITED`，Human verdict不为PASS。

### AC-3
- **Given** Human提交`comment`、存在open/reopen thread或未保存编辑
- **When** Runtime计算Human review结果
- **Then** 均不产生PASS；只有无编辑的当前revision提交`no comment`且无open/reopen thread才记录digest-bound Human PASS。

# FR-1200

### AC-1
- **Given** Story handoff commit为C、digest为D
- **When** 首轮review启动
- **Then** Human与Sage review都绑定C/D，Sage session ID不等于Scribe session ID，二者任一旧digest verdict不计入通过。

### AC-2
- **Given** Human先提交修改产生D2
- **When** Sage生成本轮意见
- **Then** Sage输入包含Human diff并绑定D2，Human revision与Sage comment revision对应两个独立commit。

### AC-3
- **Given** Human或Sage未通过
- **When** Scribe提交响应revision D3
- **Then** 原Scribe session继续使用，D/D2 verdict标为stale，新一轮只评审D3；双方均PASS D3后current step才变为M-SPEC。

# FR-1300

### AC-1
- **Given** 当前Story双方review PASS且digest为D
- **When** M-SPEC authoring启动
- **Then** 浏览器导航到`spec.md`且编辑控件disabled，Sage task input含D、review context、template、revision与唯一允许写路径。

### AC-2
- **Given** Sage尚未返回
- **When** Human尝试Web/API保存Spec
- **Then** 请求被拒绝且Spec bytes不变；Sage返回有效草案后Runtime提交仅`spec.md`并开放Human编辑。

### AC-3
- **Given** 草案含重复ID、缺Source/metadata、空内容或31个FR+NFR
- **When** 结构验证执行
- **Then** 返回包含requirement/line或`SPEC_SCOPE_TOO_LARGE`的错误，Lex task数为0且run留在Sage修订。

# FR-1400

### AC-1
- **Given** committed spec revision为R
- **When** Human与Lex review启动
- **Then** 两者均绑定R，Lex无lease写入返回HTTP 409及`DOCUMENT_WRITE_CONFLICT`，获得lease后写出的thread可由canonical parser查询。

### AC-2
- **Given** Human修改R形成R2并提交意见
- **When** Lex开始最终本轮review
- **Then** Lex输入为R2并包含Human diff；Lex对R的旧结果标为stale且不能与Human R2 verdict组合通过。

### AC-3
- **Given** Human `comment`、Lex非PASS或存在open/reopen thread
- **When** 本轮结束
- **Then** 原Sage session收到完整意见并产生新revision，round加1；只有Human `no comment`、Lex PASS、零open/reopen且digest一致才进入格式验收。

### AC-4
- **Given** 语义review通过但canonical格式校验失败
- **When** Runtime处理格式结果
- **Then** 页面显示具体file/line/rule，current step仍为M-SPEC且M-ACC task数为0；校验通过后才进入M-ACC。

# FR-1500

### AC-1
- **Given** run分别处于M-SPEC和M-ACC
- **When** Human打开return-upstream控件
- **Then** M-SPEC只显示M-STORY，M-ACC显示M-SPEC及M-STORY；提交任意其它target返回`UPSTREAM_RETURN_TARGET_INVALID`且revision不变。

### AC-2
- **Given** Human确认合法target T
- **When** Runtime执行返回
- **Then** ledger保留原artifact/review并把T及其下游verdict、format和approval标为stale/superseded，current step等于T且Git历史未删除。

### AC-3
- **Given** Agent输出建议返回M-STORY
- **When** Human未确认
- **Then** run step和revision保持不变并显示等待Human决定。

# FR-1600

### AC-1
- **Given** Spec语义与格式结果均为当前PASS
- **When** M-ACC启动
- **Then** 浏览器导航到`acceptance.md`且Human只读，Sage task绑定当前Story/Spec digests并延续原Sage上下文。

### AC-2
- **Given** Acceptance缺少某有效FR/NFR section且无No Acceptance理由
- **When** 格式/coverage校验执行
- **Then** 错误明确列出该requirement ID，M-LOCK-1不可见且run返回Sage修订。

### AC-3
- **Given** Acceptance的Human/Lex review及格式均通过
- **When** Runtime完成M-ACC
- **Then** Project current页显示current step `M-LOCK-1`；随后任一Story或Spec digest变化会把Acceptance verdict标为stale并隐藏approve。

# FR-1700

### AC-1
- **Given** 三份文档任一review、format或discussion未闭合
- **When** Human打开Project页或直接调用approve
- **Then** approve按钮不可用，服务端拒绝且列出具体blocker，GitHub Issue数不变。

### AC-2
- **Given** 三文档均通过并具有digests S/P/A
- **When** M-LOCK-1 gate创建
- **Then** 页面与gate出口显示S、P、A和确定性joint digest；Agent、旧challenge、错误revision或错误joint digest批准均被拒绝且gate仍pending。

### AC-3
- **Given** 已认证Human批准当前challenge/joint digest
- **When** 再通过Web/API写三份文档之一
- **Then** 批准记录含actor/time/challenge/revision/digests，写请求返回HTTP 423且body含`REQUIREMENTS_LOCKED`，三文件bytes保持不变。

# FR-1800

### AC-1
- **Given** M-LOCK-1尚未批准
- **When** 任意调用者请求Issue split/create
- **Then** 请求被拒绝，目标repository的本spec Issue搜索结果和release Project item数均不增加。

### AC-2
- **Given** 锁定Spec含有效`FR-0100`及对应Acceptance section
- **When** Issue operation成功
- **Then** 恰有一个Issue title字节前缀为`[FR-0100]`，body包含`FR-0100`、锁定spec section URL与acceptance section URL，且该Issue URL出现在manifest指定release Project items中。

### AC-3
- **Given** 同一repository/spec/requirement/joint-digest operation被重复、并发或重启后执行
- **When** reconcile完成
- **Then** 每个requirement最多一个匹配Issue和一个Project item；复用的Issue首个requirement token精确等于该ID，body中的ID、锁定section links及Project关联均匹配，远端已成功但本地未确认的Issue被查询复用而非重建。

### AC-4
- **Given** 部分Issue创建或Project关联失败
- **When** Human查看Project页并在修复权限后重试
- **Then** 页面逐ID显示`created|linked|failed|uncertain`及provider error，已成功Issue number不变，只补齐失败项；全部linked前步骤不完成。

### AC-5
- **Given** 搜索结果含title以目标`[FR-0100]`开头、但首个requirement token重复/不精确，或body requirement ID、锁定section links、Project关联任一不匹配的Issue
- **When** Runtime reconcile `FR-0100`
- **Then** 该Issue不被复用，页面显示以`_CONFLICT`结尾的稳定code或`needs_attention`及不匹配字段；在Human消除歧义前不创建第二个候选Issue。

# FR-1900

### AC-1
- **Given** Scribe author、Sage author/reviewer和Lex reviewer tasks已派发
- **When** 查询task evidence
- **Then** 每项含run/step/role/artifact digest/write scope/output contract/attempt/session，author与独立reviewer session ID均不同。

### AC-2
- **Given** 某session有active turn且HTTP timeout
- **When** Runtime收到重试请求
- **Then** 在session status/result reconcile完成前dispatch计数不增加；已存在有效结果被回收，仍running则继续等待。

### AC-3
- **Given** Agent返回错误role、attempt、manifest/artifact digest、schema或越权write
- **When** Runtime验证
- **Then** 结果状态为rejected，workflow revision、review verdict和受控文档bytes不变。

### AC-4
- **Given** 原session确定丢失且无有效最终结果
- **When** Runtime恢复task
- **Then** 原attempt显示`lost`或`interrupted`，新attempt拥有新session ID并引用相同权威input digests，任何attempt都未被自动标为PASS。

# FR-2000

### AC-1
- **Given** workspace含预先staged、unstaged、untracked和其它文档修改
- **When** Runtime提交当前`spec.md` revision
- **Then** commit tree diff只包含该`spec.md`，其它文件bytes及index状态与提交前字节相等。

### AC-2
- **Given** 受控commit成功
- **When** 查询revision evidence
- **Then** expected document digest、parent SHA、commit SHA、actor、run/round/task均存在，且Git读取的ref SHA字节等于记录的commit SHA。

### AC-3
- **Given** index冲突、branch移动或文档来源无法证明
- **When** Runtime尝试commit
- **Then** 页面显示`CONTROLLED_COMMIT_CONFLICT`，下一review未启动且无reset、checkout、force push或无关文件变化。

# FR-2100

### AC-1
- **Given** run停在任一review round且包含write lease、tasks和Human wait
- **When** Louke进程终止并以同一workspace重启
- **Then** run恢复相同step/revision/round/artifact digest、lease状态、task/session、gate和last error，已完成步骤dispatch计数不增加。

### AC-2
- **Given** 外部操作结果在中断时未知
- **When** 恢复扫描执行
- **Then** run不显示PASS且不推进；查询证明完成时补记相同resource ID，证明未发生时使用同一idempotency identity重试，无法判断时进入`needs_attention`并显示operation/target/known effects。

### AC-3
- **Given** browser或OpenCode断连但Runtime仍运行
- **When** Human重新打开Project与Chat
- **Then** 页面从持久化出口恢复当前document revision和task/session identity，且未因客户端断开创建重复task或外部资源。

# NFR-0100

### AC-1
- **Given** 可在run状态/event事务提交边界注入崩溃
- **When** 分别在提交前和提交后恢复
- **Then** 提交前状态与event均不存在，提交后两者均存在且revision相同，不出现单边记录。

### AC-2
- **Given** 两个请求使用同一expected revision/token并发写状态或文档
- **When** 两者完成
- **Then** 恰好一个成功，另一个HTTP 409响应含当前revision/token及以`_CONFLICT`结尾的code，成功副作用只发生一次。

### AC-3
- **Given** Backlog、Project创建、M-LOCK-1批准和Issue reconcile分别收到重复/并发请求
- **When** 查询最终公开状态
- **Then** 每个logical identity只有一个entry/run/gate decision/Issue，且所有调用者得到同一identity或明确already-completed/conflict结果。

### AC-4
- **Given** 外部资源恢复查询按对应operation evidence执行，并返回零个、多个、稳定ID冲突或仅名称/title模糊匹配的候选
- **When** Runtime尝试reconcile
- **Then** Web/API返回以`_CONFLICT`结尾的稳定code或显示`needs_attention`，列出resource kind、provider namespace及冲突字段，且资源create/reuse调用数均不增加；只有精确字段匹配的单一候选可被复用。

# NFR-0200

### AC-1
- **Given** 一条流程完成setup到Issue关联
- **When** 按run读取event/evidence
- **Then** 有序记录覆盖setup决定、step、revision、review、gate、task、commit和external operation，且每条含适用run/step/attempt、actor、time、correlation和input/output digest。

### AC-2
- **Given** 任一锁定requirement的GitHub Issue
- **When** 从Issue body正向查询及从Spec section反向查询
- **Then** 可得到同一Story/Spec/Acceptance digests、requirement ID、Issue URL和release Project identity，历史digest记录未被后续revision改写。

### AC-3
- **Given** setup/OpenCode/GitHub输入含已知credential、token、cookie和provider secret字节串
- **When** 枚举manifest、文档、events、logs、error responses、commits和Agent inputs
- **Then** 原始字节串匹配数为0，只出现redacted值、非秘密identity或digest。

# NFR-0300

### AC-1
- **Given** 安装后的release candidate、干净Git workspace和受控桌面浏览器
- **When** 仅用`lk serve`与Web完成setup、M-START、M-STORY、M-SPEC、M-ACC、M-LOCK-1和Issue/Project关联
- **Then** golden journey完成，未预写Runtime state、未调用内部Python对象、未使用CLI推进workflow，且每个步骤在Project timeline有公开证据。

### AC-2
- **Given** E2E旅程注入Human edit、inline discussion、多轮返工、CAS冲突、服务重启、Agent断连和GitHub成功后ack丢失
- **When** 旅程恢复并完成
- **Then** 每类注入均产生本合同规定的冲突/恢复/reconcile结果，旧revision verdict未推进，Agent task、Issue和Project item均无重复。

### AC-3
- **Given** CI stand-in suite及发布前真实OpenCode/GitHub smoke环境
- **When** 两套验证完成
- **Then** 报告分别标识`stand-in`与`real`，真实smoke记录可恢复session ID、创建或复用的Issue number和Project node/item ID。
