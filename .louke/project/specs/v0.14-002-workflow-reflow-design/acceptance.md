# 工作流重构：技术设计与规范性 Agent 合同 — 验收标准

- **Spec ID**：`v0.14-002-workflow-reflow-design`
- **创建日期**：2026-07-19
- **Revision identity**：`Lex round 1 revision`
- **Revision digest**：`PLACEHOLDER（由 Runtime 计算）`

> 本文是 `spec.md` 中全部 FR/NFR 的验收注册表。每个 `### AC-N` 从 1 开始；项目级稳定引用使用条目中的 `AC-FRXXXX-YY` / `AC-NFRXXXX-YY`。

## FR-0100 M-DESIGN 入口与 Revision 身份

### AC-1
- **验收 ID**：`AC-FR0100-01`
- 在批准的 requirements digests、base commit 和宿主事实均 current 时，进入 M-DESIGN 会持久化包含 run/release/revision/attempt/actor/全部输入 identity 的记录。
- 任一批准、digest、workspace 归属或 base commit 缺失/冲突/stale 时，不创建 Archer task，并返回稳定阻塞原因。

## FR-0200 宿主项目事实盘点与自主技术选择

### AC-1
- **验收 ID**：`AC-FR0200-01`
- 对已有项目，Archer 输入列出实际语言、build/test/version/artifact/CI/hooks/公开出口并在设计中引用；不存在的路径不会被虚构。
- 对空白项目，在没有 Human 技术选择的情况下，Archer 仍产出有依据且完整的技术方案；prompt/结果中不存在把 Louke 仓库配置当默认的规则。

## FR-0300 设计写入授权与工件归属

### AC-1
- **验收 ID**：`AC-FR0300-01`
- Archer manifest 明确列出允许的三份设计文档、machine contracts、受影响 prompt sources 与禁止副作用，并只接受该范围的 patch。
- 构造越界文件、Git/阶段副作用或未归属 diff 时，program gate 拒绝纳入 revision，且原 baseline 保持不变。

## FR-0400 Test Plan 设计

### AC-1
- **验收 ID**：`AC-FR0400-01`
- 校验器能为每个有效 AC 读取 observable interface、required layer(s)、runner/命令、fixture/environment、CI job、trace metadata 与 rationale；observable interface 与执行入口均解析到 Interfaces 的真实 identity，命令、路径和状态语义与对应 machine contract 及 Architecture 一致，且双向不存在 orphan。
- 只用 unit 覆盖跨模块行为、只用内部接口覆盖主用户旅程、required 多层中少一层，或任一 FR/AC/interface/contract 映射缺失、orphan、双向冲突时，Test Plan gate 失败，定位具体 FR/AC、interface、architecture anchor 与 machine contract，并阻止 implementation baseline。

## FR-0500 Architecture 设计

### AC-1
- **验收 ID**：`AC-FR0500-01`
- Architecture 对当前需求给出组件/依赖、数据和控制流、状态一致性、故障、安全、迁移兼容及关键决定，并可追溯到项目事实和 FR/AC；每项 Interfaces 状态、权限、错误、恢复语义均双向映射到承载它的组件、状态机制和安全/信任或故障边界，且与 Test Plan 观察点及 machine contract 的命令、路径、状态语义一致。
- 留有必须由 Devon 或 Human 临场选择的未决技术边界，或出现缺失承载、orphan、双向冲突时，Prism/program gate 返回 FR/AC、interface、architecture anchor 与 contract 锚点，不能形成 implementation baseline。

## FR-0600 Interfaces 设计

### AC-1
- **验收 ID**：`AC-FR0600-01`
- 每条主用户旅程均能从宿主产品现有或新设计入口追踪到具有真实 identity 的 interface 及其输入、输出、状态、权限、错误、恢复和可观察完成结果；Test Plan observable interface/执行入口可解析到该 identity，其语义由 Architecture 承载，并与 machine contract 的命令、路径、状态语义一致。
- Acceptance 需要观察但 Interfaces 无公开出口、文档为不适用技术栈虚构 UI/CLI/API，或任一映射缺失、orphan、双向冲突时，校验/Prism review 按 FR/AC、interface、architecture anchor 与 contract 定位并阻止 baseline。

## FR-0700 Machine Contract Registry

### AC-1
- **验收 ID**：`AC-FR0700-01`
- Runtime/program registry 可发现 `integration-test`、`e2e-test`、`pre-commit`、`github-actions-ci`、`release-version`、`build-artifact`、`publish-recovery` 全部 required kinds；每类权威 schema 可解析 identity/version/digest，每个 Archer 生成的 instance 均引用该 schema 并可解析自身 revision/digest、范围、引用和失败策略。
- 缺少任一 required kind，instance 自带/自证替代 schema，或使用未知、candidate、digest 不匹配的 schema/version、未知/缺失必需字段、无兼容 migration 的旧合同时，registry gate 明确拒绝并阻止 baseline，不会静默忽略。

## FR-0800 Integration Test Contract

### AC-1
- **验收 ID**：`AC-FR0800-01`
- integration contract 可被程序读取并验证路径、发现规则、setup/run、services/fixtures、环境、超时、AC metadata、suite policy、evidence 与失败语义。
- 从 Test Plan 分配一个 integration AC 但合同无可执行去向，或 required suite 被无依据 skip 时，gate 失败并引用该 AC。

## FR-0900 E2E Test Contract

### AC-1
- **验收 ID**：`AC-FR0900-01`
- e2e contract 可被程序读取并验证公开入口/旅程、路径、runner、环境服务生命周期、隔离、超时、artifact、trace 与恢复字段。
- 将 e2e 分配映射到仅调用内部模块的测试，或缺少 required journey 的运行出口时，Prism/program gate 不通过。

## FR-1000 Pre-commit Contract

### AC-1
- **验收 ID**：`AC-FR1000-01`
- 对带既有 hooks 的宿主 fixture，设计结果保留/合并现有行为，并可 readback 配置、安装入口、版本、快速 checks、自动修改与失败语义。
- 合同若要求 Archer/Devon 安装 hook、把 Red 失败作为 hook 目标、或把 pre-commit 当最终全量 gate，schema/semantic review 失败。

## FR-1100 托管 GitHub Actions CI Contract

### AC-1
- **验收 ID**：`AC-FR1100-01`
- 针对至少两个不同技术栈 fixture，生成的合同均使用各自真实 setup/build/test/artifact，包含托管路径、触发器、job DAG、权限、secret/service/cache/evidence/failure policy。
- Test Plan 中任一 required quality layer、AC trace、build 或 artifact check 未进入 CI job/gate 时，contract closure 校验失败。

## FR-1200 稳定 Required Check 与强制策略

### AC-1
- **验收 ID**：`AC-FR1200-01`
- 合同只定义一个稳定聚合名 `Louke CI / required`，全部 required jobs 成功才成功，并声明 ruleset/branch-protection 的 owner、target 和 readback。
- 模拟 job fail/cancel/timeout/missing/illegal-skip/unknown 任一状态时聚合结果为失败；生成的变更不删除 fixture 中既有 required checks。

## FR-1300 CI 共存、生成与漂移生命周期

### AC-1
- **验收 ID**：`AC-FR1300-01`
- 相同 contract 输入重复生成托管 workflow 得到相同规范化内容/digest，且其它 workflows/rules 不变；未漂移文件可幂等升级。
- Human 修改托管文件后，reconcile 保留可见 diff 且不静默覆盖；缺失、非法 YAML、命令不存在或 digest drift 均阻止 PASS。

## FR-1400 Canonical Release Identity 与版本源

### AC-1
- **验收 ID**：`AC-FR1400-01`
- 已有与全新项目 fixture 均可从 registry discovery 发现 required contract kind `release-version` 的 instance；它通过 Runtime/program 权威 schema identity/version/digest 校验，具有 instance revision/digest，并形成 canonical version→adapter/version-source identity→release branch/tag 的单一可解析映射及可程序比较的读取/准备入口、前缀规范化与失败语义。
- `release-version` kind 缺失，只有 branch/tag 名而无真实版本源，mapping 不可解析/不一致，instance 使用未知/candidate schema，或 Human 被要求选择 Maven/npm/Cargo 等技术实现时，registry/design gate 阻止 baseline。

## FR-1500 Build、Artifact 与安装后版本合同

### AC-1
- **验收 ID**：`AC-FR1500-01`
- 合同可依序执行 version prepare、真实 build、完整 artifact 枚举、每件 artifact digest/version extract/compare 和适用安装或运行后版本读取。
- 多 artifact 中任一缺失、不可提取、版本不匹配或公开版本不一致时，合同输出确定 FAIL，不能以源码声明代替。

## FR-1600 Publish 与恢复合同

### AC-1
- **验收 ID**：`AC-FR1600-01`
- 对所有适用 merge/tag/publish/release/deploy/smoke 操作，合同定义顺序、前置 gate、稳定 identity、事实查询、幂等性、凭据、验证及 rollback/forward-fix。
- 模拟 API partial success 或结果未知时，预期状态为可重试 `needs_attention`，且不得产生重复 tag/upload 或成功结论。

## FR-1700 Agent Prompt 作为规范性工件

### AC-1
- **验收 ID**：`AC-FR1700-01`
- Spec manifest 对本 revision 列出的 canonical prompt paths 精确等于封闭集合 `louke/agents/Archer.md`、`louke/agents/Prism.md`；implementation baseline 包含二者的 source digests 与独立 review identity。
- 漏列上述任一路径或夹带任一未授权 prompt 均阻止 implementation baseline；修改任一已 baseline prompt 后，旧 task/review/evidence 被标记 stale，未 review 的 prompt 不能进入 current baseline。

## FR-1800 Prompt Bundle Manifest 与身份

### AC-1
- **验收 ID**：`AC-FR1800-01`
- prompt bundle manifest 包含 schema/bundle version、source/deployed path+digest、role、frontmatter/permission/model abstraction、protocol/skill、Spec、schema refs 和 transformer version。
- Runtime task 能回溯到精确 bundle/role；删除任一必需 identity 或仅在聊天中声明版本时，dispatch/gate 被拒绝。

## FR-1900 Prompt 语义与机器 Schema 分离

### AC-1
- **验收 ID**：`AC-FR1900-01`
- 从 Runtime/program registry 可在不解析 prompt 示例或 contract instance 自带定义的情况下获得并验证 Agent input/output 与 machine contract 权威 schema identity/version/digest；task manifest/contract registry 携带精确 reference，Archer 输出只生成引用 active schema 的 instance。
- instance 自带或自证替代 schema，使用未知/candidate/digest 不匹配 schema，或存在缺字段、错误类型/枚举、禁止的附加字段时被程序拒绝；修改 prompt 示例或 instance 内容不会改变 schema 权威结果。

## FR-2000 Prompt 确定性部署与 Drift 检测

### AC-1
- **验收 ID**：`AC-FR2000-01`
- 相同 source bundle、转换规则和模型绑定重复部署产生一致的规范化 deployed digest，并可由 readback 验证 source→deployment 映射。
- 缺失副本、手工编辑、旧 transformer 或 digest mismatch 会被检测并阻止 dispatch，或由 Runtime 明确 reconcile 后生成新 identity。

## FR-2050 Prompt Candidate 的安全自举与原子激活

### AC-1
- **验收 ID**：`AC-FR2050-01`
- 修改当前 author/reviewer prompt 的 candidate 后，已启动 session 仍报告旧 active bundle identity；新内容只以 candidate artifact 出现，不会热加载或改变当前 attempt。
- candidate 仅在 lint/schema、独立 trusted-review、部署 readback 与 baseline 全部 PASS 后一次性成为后续 dispatch 的 active bundle；评审记录同时包含 reviewer execution bundle 与 reviewed candidate bundle，candidate 不能自报通过。

## FR-2100 Host Project 中的 Prompt 只读边界

### AC-1
- **验收 ID**：`AC-FR2100-01`
- 在普通 Java/Node 等宿主 release fixture 中，项目差异只出现在 facts/contracts/manifests，安装包 canonical prompts 不产生修改。
- 在 Louke 自身开发 fixture 中，只有 Spec 显式列入且 manifest 授权的 prompt source 可编辑；未列入路径的 patch 被拒绝。

## FR-2200 Archer 规范性语义合同

### AC-1
- **验收 ID**：`AC-FR2200-01`
- Archer prompt lint/behavior fixture 能确认其输出职责包含三份设计、machine contracts、direct diff 与 gap advisory，且全新项目由其自主作技术选择。
- prompt 中不存在主动 question Human 技术方案、安装、commit/push、dispatch、写 review/gate 或推进阶段的指令。

## FR-2300 Prism 设计评审语义合同

### AC-1
- **验收 ID**：`AC-FR2300-01`
- Prism design-review manifest 包含精确设计、contract、prompt bundle identities；输出 schema 只允许绑定 identity 的 verdict/findings/questions/advisory。
- prompt 中不存在写 review artifact、调用 Runtime gate/阶段命令、伪造作者结果或把 finding 视作 Human 决定的指令。

## FR-2400 Human 可选 Review 与 Direct Diff

### AC-1
- **验收 ID**：`AC-FR2400-01`
- Human 完全缺席时，设计仍可经 Archer、program gates 和 Prism 进入 implementation baseline；Human 评论和 direct diff 均在下一 author round 可见并去重。
- 对无问题 direct edit，Archer 可不新增 discussion；对有问题修改会创建锚定原文的 discussion，且 Human 作者身份不使修改自动 PASS。

## FR-2500 独立 Review Loop 与 Freshness

### AC-1
- **验收 ID**：`AC-FR2500-01`
- Prism 在 author revision 持久化后以独立 task 执行，verdict 记录 reviewer/attempt/全部 input digests/prompt identity/findings。
- 任一输入变化使 verdict stale；REVISE 产生新 Archer revision，且不存在由 Archer 写入 PASS 或以 reviewer 文本直接推进阶段的路径。

## FR-2600 设计程序校验、Gap 与 Stale 传播

### AC-1
- **验收 ID**：`AC-FR2600-01`
- 校验器能发现坏 ID/ref、AC 层缺口、schema 错误、prompt drift、未闭 discussion 和越界 diff；它还双向验证 Test Plan observable interface/执行入口解析到 Interfaces 的真实 identity、Interfaces 状态/权限/错误/恢复由 Architecture 承载，以及 machine contracts 命令/路径/状态语义与三份文档一致。
- 任一缺失、orphan 或双向冲突均返回稳定 check ID，并定位 FR/AC、interface、architecture anchor 与 contract 后阻止 baseline；技术 gap 可在 Archer+Prism 确认后回 M-DESIGN，产品 gap 未经 Human 不可回需求阶段，修订后旧下游证据均不可 current。

## FR-2700 Implementation Baseline 与无第二 M-LOCK

### AC-1
- **验收 ID**：`AC-FR2700-01`
- 全部 program gates 与 Prism review 对同一 revision PASS 后，Runtime 原子生成含 requirements/design/contracts/prompts/base/Issues/release/discussions identity 的 baseline 并进入 M-IMPL。
- WorkflowDefinition 与新 run history 中不存在设计后第二 M-LOCK 或 Human 技术批准等待；任一 gate stale 时不能进入 M-IMPL。

## NFR-0100 确定性与可复现性

### AC-1
- **验收 ID**：`AC-NFR0100-01`
- 在固定时间/环境等显式非确定输入后，同一规范性输入重复生成的 contract、prompt deployment 和 baseline 具有相同规范化 digest。
- 任何影响 digest 的 generator/schema/tool version 均在 manifest 中可观察。

## NFR-0200 最小权限与 Secret 安全

### AC-1
- **验收 ID**：`AC-NFR0200-01`
- 自动化 fixture 证明 Archer/Prism 没有 Git/GitHub/阶段写工具，CI contract 默认最小 token 权限，fork/untrusted job 无生产 secret。
- secret scanner 对 prompt、contract、log 和 fixture 中注入的测试 secret 均阻止 baseline 并报告位置而不回显 secret 值。

## NFR-0300 宿主技术栈可移植性

### AC-1
- **验收 ID**：`AC-NFR0300-01`
- 使用至少两个不同语言/build/artifact fixture 可分别通过 schema 与设计 gate，且生成内容只引用各自存在的项目事实。
- 不支持能力返回带 contract kind 和项目事实的显式诊断，不回退到硬编码 Python/Node/Java 默认。

## NFR-0400 可恢复性与审计

### AC-1
- **验收 ID**：`AC-NFR0400-01`
- 在 author、program check、Prism review 各边界模拟重启，Runtime 能恢复同一 current revision、pending work 和历史，不重复 dispatch 已完成 attempt。
- 删除或篡改持久化 digest 后恢复 fail closed，并保留可诊断的历史记录。

## NFR-0500 校验反馈可操作性

### AC-1
- **验收 ID**：`AC-NFR0500-01`
- 对 schema、trace、prompt drift 和 project path 四类失败，输出均包含稳定 check ID、路径/字段、期望/实际、关联 identity 与 retryability。
- UI/API 不只显示通用失败字符串，用户可从结果定位到待修工件锚点。

## NFR-0600 状态与 Schema 迁移兼容性

### AC-1
- **验收 ID**：`AC-NFR0600-01`
- 旧 `M-LOCK-1`/第二锁和旧 prompt/contract fixture 可被显式迁移或只读诊断，新 run 只产生 canonical stage/schema identities。
- migration 中断可重试且不产生两个 current revision 或双写阶段；未知旧版本 fail closed。
