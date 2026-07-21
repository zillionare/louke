# v0.14-001-workflow-reflow-spec — Lex Semantic Review Round 3

- **reviewer**: Lex
- **round**: 3
- **reviewed_story_digest**: `sha256:e04e88b336c7f08a3f67ef40354fa35c3e78ec66935805aa6f2da7272dfd0634`
- **reviewed_spec_digest**: `sha256:32b2f4c51209b0c8e4167439533370877ad38040fb44ae696d20d01280c81069`
- **reviewed_acceptance_digest**: `sha256:159e82bce6d43580200ab9f968ee5e645b528374ba896fbec8f5191b66799f9f`
- **reviewed_spec_revision**: 8
- **reviewed_acceptance_revision**: 9
- **verdict**: `PASS`
- **reviewed_at**: `2026-07-20`
- **supersedes**: stale v6 review, Lex round-1 review, and Lex round-2 review
- **scope**: `story.md`, `story-review.md`, `flow.md` L1-L95, `spec.md` v8, `acceptance.md` v9

## Verdict

**PASS**

当前 Spec/Acceptance 忠实覆盖 Story 的产品不变量，并形成从 `lk serve`、Workspace Setup、`/projects/new`、M-STORY、M-SPEC、M-ACC、M-LOCK-1 到 GitHub Issues/Project 结果的连续产品旅程。

前两轮提出的所有 blocker 均已闭合。当前 revision 未引入新的范围漂移、对象身份冲突、权限越界、恢复矛盾或不可断言的关键用户结果，可以移交后续确定性格式门禁及 Human review。

## Prior Blocker Closure

### 1. 启动硬前置失败与 Web readiness 边界

**状态：已闭合。**

FR-0100、AC-FR0100-01 与 AC-FR0100-03 已明确区分：

- Web 服务本体无法建立的硬前置失败：进程非零退出、stderr 提供修复方向、Web 不可访问。
- Web 可建立但配置、provider/auth、模型、OpenCode 或 workspace readiness 不完整：Web 保持可访问、显示 `BLOCKED`、release 动作不可提交。

同一失败项不得同时归入两类，入口、失败结果及修复后重试路径一致。

### 2. Workspace Setup 与 release Foundation 的资源归属

**状态：已闭合。**

Step 2、FR-0200 与 AC-FR0200-01..05 将 Setup 限定为 workspace/repository identity、provider namespace、认证、模型、OpenCode readiness 及 namespace/create capability 等 workspace 级事实。

Setup 不得创建、复用或预占具体 release 的 Project、WorkflowRun、release GitHub Project、release branch 或 Spec 目录。上述 release 级资源仅可在 release 请求确认、单活跃主 release 检查及 `main` 前置检查通过后，由 FR-0400 Foundation 创建或 reconcile。

### 3. 所有 `main` 检查失败的零 release 副作用及错误资源恢复

**状态：已闭合。**

- AC-FR0400-04 以"本次 release 尚无任何 release 级资源"为初态，覆盖本地 `main` 不一致以及上一开发分支相对权威 `main` 为 ahead、behind、diverged 或无法判定的情况。
- 该 AC 明确断言 Project、WorkflowRun、release GitHub Project、release branch、Spec 目录及 M-STORY task 均不增加，Human 修复并重新检查前不能绕过阻塞。
- AC-FR0400-05 独立覆盖恢复时发现错误 branch 起点或 stable identity 冲突的场景。
- 冲突资源保持 `conflict` 或 `needs_attention`，不得被当作 Foundation 完成，不得创建其它候选资源、静默改写既有资源或进入 M-STORY；页面向 Human 展示实际/预期 identity 与 remediation。

AC-FR0400-01、AC-FR0400-04 与 AC-FR0400-05 共同证明 FR-0400 的正常前置失败、零副作用及异常恢复不变量。

## Coverage Summary

- **Story behavior seeds**: 15/15 已覆盖。
- **Functional requirements**: 21。
- **Non-functional requirements**: 3。
- **Current valid requirement units**: 24。
- **Acceptance sections**: 24/24，每个有效 FR/NFR 均有对应 section。
- **Acceptance criteria**: 82 个，未发现重复语义身份。
- **User Journey**: 8/8 steps。
- **Story review**: Sage PASS，绑定当前 Story digest。

关键路径完整覆盖：

`现有 workspace → lk serve → 启动诊断/Setup → /projects/new → main/Foundation → Story → Spec → Acceptance → M-LOCK-1 → Issues/Project → 后续流程入口`

每个步骤均说明入口或触发、关键动作、用户可见结果以及继续、返回或恢复位置。

## Scope and Product Invariants

- 未引入 `flow.md` L96 之后的 Test Plan、Architecture、Interfaces、实现、测试、发布、归档或通用 lifecycle 能力。
- CLI 仅用于安装、升级和 `lk serve`，不用于推进 M-STORY、M-SPEC、M-ACC 或 M-LOCK-1。
- 未引入多人审批、移动端、完整离线模式或旧 active run 迁移。
- Human 独占 Go/Park/No-Go、return-upstream 与 M-LOCK-1 的决定权。
- Runtime 是流程步骤、写权、revision、review、gate 与外部副作用的唯一推进 authority。
- Scribe、Sage 与 Lex 不能自行批准门禁或改变流程位置。
- Story、Spec、Acceptance 的 review 均绑定当前 revision/digest；上游变化使下游 PASS 与批准 evidence 失效。
- 单写者、CAS、脏编辑保护及受控 Git commit 防止静默覆盖和无关 workspace 修改。
- setup、Foundation、Agent session、Git 与 GitHub 操作均具有中断恢复、精确 identity reconcile 和幂等边界。
- credentials、tokens、cookies 与 provider secrets 不得进入文档、manifest、event、log、错误详情、commit message 或 Agent input。

## Blockers

无。

## Non-blocking Notes

1. AC-FR0400-02 中的 `release Project` 结合其与本地 Project、WorkflowRun 并列的上下文，可理解为 release GitHub Project；后续文档可统一术语，但不影响当前产品语义或可断言性。
2. 具体状态存储、事务边界、资源查询算法、UI 组件与内部 API payload 均仍保留给 Architecture/Interfaces 设计，本合同没有不必要地锁定实现方案。
3. 后续若 FR/NFR 的 Valid 状态发生变化，Issue 目标数量应继续按锁定 Spec revision 的实际有效单元数计算，而不是永久固定为 24。
