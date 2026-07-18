# v0.14-001-workflow-reflow-spec — Lex Peer Review (2026-07-18)

> 来源：Lex（独立语义 review）。产物用于驱动 Sage 下一轮修订。
> 文件路径：`.louke/project/specs/v0.14-001-workflow-reflow-spec/spec-review.md`
> 范围：spec.md / acceptance.md / story.md / flow.md L1-L95。`flow.md` L96 之后不在本 Spec 内。

---

## 1. Verdict

**PASS-WITH-COMMENTS**

合同在 story.md / flow.md / spec.md / acceptance.md 之间双向可追；每条 FR 都有可断言 AC；Out-of-Scope 与 `flow.md` L96+ 严格分离。唯一 blocker 是 M-START 中"上一开发分支未合 main"在 FR-0400 + AC-1 写得过粗，需要 1 句话补正。其余 6 项均为建议项。

---

## 2. Coverage 三列表

### 2.1 `flow.md L1-L95` → 本 Spec FR/NFR 编号

- L5-L13（启动与启动诊断）→ FR-0100, NFR-0100
- L15-L23（Workspace Setup）→ FR-0200, NFR-0200
- L25-L29（创建 release 表单）→ FR-0300, NFR-0100
- L29-L31（分支合回 main / foundation）→ FR-0400, NFR-0100, NFR-0200, FR-2000
- L30-L32（初始 story.md 与跳转）→ FR-0500, FR-2000
- L34-L43（M-STORY 启动与 Human 裁决）→ FR-0600, FR-0700
- L42（Park/No-Go 退出）→ FR-0800, FR-2000
- L43-L46（Go 后访谈与 Scribe 继续）→ FR-0900, FR-1900
- L47-L57（文档写权与多轮 review）→ FR-1000, FR-1100, FR-1200, FR-1900, FR-2000, NFR-0100, NFR-0200
- L59-L66（M-SPEC 起草）→ FR-1300, FR-1900
- L66-L74（M-SPEC Human/Lex review 与格式验收）→ FR-1400, FR-1900, FR-2000
- L75（M-SPEC/M-ACC 返回上游）→ FR-1500
- L77-L85（M-ACC 起草与 review）→ FR-1600, FR-1900
- L87-L93（M-LOCK-1 批准）→ FR-1700, NFR-0100, NFR-0200
- L94（Issue 创建 + Project 关联）→ FR-1800, NFR-0100, NFR-0200
- L13, L23, L45-L55, L69-L72, L84-L94（横切：中断恢复）→ FR-2100, NFR-0100, NFR-0200
- L5-L95（横切：installed-wheel golden path）→ NFR-0300

> MISSING：无。L96 之后不在本 Spec 范围。

### 2.2 `story.md BS-01 .. BS-15` → 本 Spec FR/NFR 编号

- BS-01 → FR-0100, FR-0200, NFR-0300
- BS-02 → FR-0200, NFR-0200
- BS-03 → FR-0300, NFR-0100
- BS-04 → FR-0400, FR-0500, FR-2000
- BS-05 → FR-0700, FR-1900
- BS-06 → FR-0800, FR-0900, FR-2000
- BS-07 → FR-0600, FR-1000, NFR-0100
- BS-08 → FR-1100, FR-1200
- BS-09 → FR-1000, FR-1200, FR-1400, FR-1600, FR-1900, FR-2000
- BS-10 → FR-1300, FR-1400, FR-1900
- BS-11 → FR-1100, FR-1400, FR-1600
- BS-12 → FR-1500
- BS-13 → FR-1600, FR-1900
- BS-14 → FR-1700, FR-1800, NFR-0100, NFR-0200
- BS-15 → FR-0200, FR-0400, FR-0600, FR-0800, FR-1800, FR-1900, FR-2000, FR-2100, NFR-0100, NFR-0200

> 双向闭合：每个 BS 都至少被一个 FR/NFR 引用；每个 FR/NFR 的 Source 行都包含至少一个 BS（NFR-0300 引用 BS-01..15 全体，符合横切条款）。

### 2.3 反向：本 Spec FR/NFR → flow.md 至少一次被引用

- FR-0100 → flow.md L5-L13
- FR-0200 → flow.md L15-L23
- FR-0300 → flow.md L25-L29
- FR-0400 → flow.md L29-L31
- FR-0500 → flow.md L30-L32
- FR-0600 → flow.md L34-L95（横切）
- FR-0700 → flow.md L34-L43
- FR-0800 → flow.md L42
- FR-0900 → flow.md L43-L46
- FR-1000 → flow.md L47-L57
- FR-1100 → flow.md L47-L52
- FR-1200 → flow.md L47-L57
- FR-1300 → flow.md L59-L66
- FR-1400 → flow.md L66-L74
- FR-1500 → flow.md L75, L79-L85
- FR-1600 → flow.md L77-L85
- FR-1700 → flow.md L87-L93
- FR-1800 → flow.md L94
- FR-1900 → flow.md L38-L57, L63-L72, L81-L84
- FR-2000 → flow.md L31, L45-L55, L69-L72
- FR-2100 → flow.md L13, L23, L45-L55, L69-L72, L84-L94
- NFR-0100 → flow.md L28, L47-L57, L69-L72, L91-L94
- NFR-0200 → flow.md L18-L23, L45-L55, L69-L72, L91-L94
- NFR-0300 → flow.md L5-L95

> 反向闭合：每个 FR/NFR 都在 flow.md 至少被引用一次。

---

## 3. Blockers

### B-01

- **where**: spec.md FR-0400 body + acceptance.md FR-0400 AC-1
- **why**: FR-0400 要求"刷新 declared remote 并证明上一主开发分支已合入权威 `main`"，但 acceptance.md FR-0400 AC-1 只在"刷新失败或未合入"路径上断言阻止；没有规定"刷新成功但证明失败（例如 divergent、需要 fast-forward、需要 human decision）"以及"已合入但 release branch 起点 SHA 与预期 main 不一致"等场景的精确行为。Devon 看到 FR-0400 body 仍会问"main 同步需要 human 时，run 怎么恢复"。
- **evidence**: spec.md FR-0400 line 24-26；acceptance.md FR-0400 AC-1 line 70-74
- **fix_direction**: 在 FR-0400 body 增加"main 不等于 declared remote 权威 main 时必须记录 divergent/behind/ahead 状态并要求 Human 确认 fast-forward/push 后再继续"；相应把 acceptance.md FR-0400 增加 AC-4 覆盖 divergent 场景（与 BS-37 行为语义对齐，但只覆盖本 Spec 的 main 一处同步）。

---

## 4. Comments（非 blocker）

### C-01

- **where**: spec.md FR-0700 body
- **why**: "派发一个 Scribe semantic task" 的输入 contract 没有声明最小输入（已有 release manifest / story template 路径 / 上游 Story digest / 上一轮 feedback list）。Devon 实现 dispatch 时仍可能漏掉已确认字段。
- **fix_direction**: 把"task input manifest 含：run_id / step_id / attempt_id / spec_id / template_path / spec digest / 上轮 feedback digests"作为强制子句加入 FR-0700。

### C-02

- **where**: acceptance.md FR-0900 AC-1
- **why**: "回复先出现在 run/task event 中再出现在 session S transcript 中" 难以断言"先后顺序"，因为两边都是事件流而系统时钟/单调时钟口径未声明。
- **fix_direction**: 用单调时间戳或固定 `correlation_id` 把两者绑定；AC 改为"reply 的 event.seq 小于 session transcript 中同 reply message 的 msg.seq"或等价可断言口径。

### C-03

- **where**: spec.md FR-1000 body
- **why**: "若能从受控文档基线精确隔离违规 patch，Runtime 可只移除该 patch" 这条规则依赖"受控文档基线 = 上一已提交 revision bytes" 的精确副本；storage schema 需要声明是否在每次 write 时存一份完整历史，否则 revert 算法无法实现。Archer 在 Architecture 阶段决定 lease 隔离算法是正确的，但 FR-1000 body 应预留一个隐式约束供 Archer 满足。
- **fix_direction**: 在 FR-1000 body 增加一条要求"Runtime 必须为每个受控文档保留 N 个最近 committed revision bytes（含本轮可用的最新一次）供 patch 隔离使用"，无需指定 N。

### C-04

- **where**: spec.md FR-1200 + acceptance.md FR-1200 AC-3
- **why**: "Human 与 Sage verdict 均为 PASS 且均绑定当前 digest 时，本轮才通过" 的语义在 M-SPEC 与 M-ACC 复用，但 spec.md FR-1400/FR-1600 重新声明了一遍。重复定义容易漂移。
- **fix_direction**: 把"review 通过条件"抽象为一条独立的合同声明（可放在 spec.md 顶部"## Review contract"或 NFR-0100 中），让 FR-1200 / FR-1400 / FR-1600 引用，避免漂移。

### C-05

- **where**: spec.md FR-1500 body
- **why**: "在 M-ACC 中 Human 可明确返回 M-SPEC，或在指出 Story 问题时返回 M-STORY" 暴露了"指出 Story 问题"的判定由 Human 自决；但当 Lex 在 M-ACC review 中发现 Story 级问题时，FR-1500 没说 Lex 也可以请求返回，仅说"Agent 只能提出建议"。
- **fix_direction**: 在 FR-1500 body 增加"Lex 在 M-ACC review 阶段发现 Story 级问题时可写一条 canonical inline discussion 标注 `RETURN_TO_M-STORY` 候选；Runtime 不自动返回，须由 Human 在 UI 显式确认。" 这与 backlog 的 `return-upstream` 完整契约不同，但与本 Spec 的 Human-主导边界一致。

### C-06

- **where**: spec.md FR-1800 body
- **why**: 现有契约写"title 必须以 `[FR-0100]` 开头"，但 backlog 中 PR / cross-link 工具也可能生成形如 `[FR-0100][AC-1]` 的 title；reconcile identity 应避免被前缀误匹配。
- **fix_direction**: FR-1800 body 增加"reconcile 必须从 title 中解析单一 `[ID]` token，ID 必须精确等于 requirement ID（不允许重复 token、附加后缀或复合 ID）"。

### C-07

- **where**: spec.md FR-2000 body
- **why**: "提交内容只能包含当前阶段预期的受控文档" 已声明文件白名单；但未声明 commit message 是否包含 actor/run/attempt 信息。
- **fix_direction**: FR-2000 增加一条 "commit message 必须含 `[run=<run_id>] [round=<n>] [actor=<principal>] [task=<task_id>]` 字节串"，便于人工审计。

### C-08

- **where**: spec.md FR-2100 + NFR-0100
- **why**: "对 repository/branch/Project/Issue 及其它外部操作，恢复必须按稳定 identity 查询实际状态"——但"稳定 identity"在不同资源类型下口径不同，未给出最小查询契约。
- **fix_direction**: 在 NFR-0100 增加 "recovery identity 必须由 (resource_kind, owner, name, version, head_sha) 五元组构成；reconcile 必须使用最严格可比五元组"，与 FR-0400 / FR-1800 reconcile identity 引用一致。

---

## 5. 越界检查

- **flow.md L96+ 越界**：无。本 Spec 所有 FR 的 Source 都引用 `flow.md` L5-L95 或具体到 L95 之内。
- **backlog 中"全生命周期"合同越界**：未引入 FR-0910（CLI 缺位）、FR-0110（program result 边界）、FR-0720（通用 return-upstream）等 backlog 合同到本 Spec。FR-1500 的 return-upstream 是"启动到 M-LOCK-1"专用最小版本，未越界扩展为通用合同。
- **v0.13 迁移 / CLI 推进 / 多用户审批**：未越界。Out-of-Scope 明确排除。
