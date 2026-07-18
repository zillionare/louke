# v0.14 Workflow Reflow 调研报告

> 状态：研究输入，非规范性合同。
>
> 本文用于更新 `story.md`、编写后续 spec/acceptance、architecture、interfaces 和 test-plan。若本文与后续锁定合同冲突，以锁定合同为准。

## 1. 调研目标

本次调研覆盖 v0.10 至 v0.14 的 Story、Spec、Acceptance、Architecture、Test Plan、迁移规划、Agent 指令、Runtime、Web/Chat 和当前生产装配，目标是：

1. 区分已经交付、部分实现、仅存在底层类库或演示、尚未实现的能力。
2. 更新 v0.14 Story，使其反映 v0.13/v0.13.1 后的真实状态。
3. 明确 v0.14 的三项核心目标：
   - Agent 只承担语义分析、生成和意图建议，流程和权威质检由程序驱动；
   - 支持安全、灵活的回退、waiver 和既有项目 adoption；
   - 引入版本化的 workflow lifecycle hooks，作为后续扩展点。
4. 确认 workflow 后续仍可演进，同时不破坏 Spec → Acceptance → GitHub Issue → commit hash → authoritative test evidence 的追踪体系。

## 2. 版本演进

### 2.1 v0.10：Web 文档编辑体验

v0.10 主要目标是 Vditor 即时渲染、文件选择、多 pane、讨论过滤和页面布局重构：

- `.louke/project/specs/v0.10-001-vditor-redesign/spec.md`

它解决的是文档交互体验，不是 workflow authority。

### 2.2 v0.11：Web IDE 与 server 驱动构想

v0.11 已提出两项后来成为 v0.14 核心的方向：

- 通过 Web 操作 OpenCode session 和消息；
- 由 Louke server 实现工作流，取消只包装工具的 Agent。

来源：

- `.louke/project/specs/v0.11-001-web-ide/story.md:2-4`

但 v0.11 的目标没有完成生产 Runtime 切换，旧 Maestro/Agent pipeline 仍然保留。

### 2.3 v0.12：Programmatic Workflow Runtime 合同与核心类库

v0.12 正式确定：

- Runtime 是 workflow 状态和合法转移的唯一控制者；
- program step 执行确定性工作；
- semantic task 只承担理解、判断、审查和创造；
- Human gate 持久化并绑定 digest/revision；
- Agent 不能批准 gate、改变 WorkflowRun、commit/push 或自行进入下一阶段；
- Runtime 重启后必须恢复，而不是依赖聊天上下文。

来源：

- `.louke/project/specs/v0.12-001-programmatic-workflow-runtime/story.md:7-36`
- `.louke/project/specs/v0.12-001-programmatic-workflow-runtime/story.md:80-110`

当前代码已经实现大量 Runtime 核心原语：

- immutable/versioned workflow catalog：`louke/runtime/catalog.py`
- pinned run definition/version/digest：`louke/runtime/store.py`
- orchestrator 与 revision CAS：`louke/runtime/orchestrator.py`
- program handler/attempt：`louke/runtime/program_steps.py`
- gates、events、recovery 和 projects domain。

但这些主要是核心类库，尚未全部接入唯一 production composition root 和自动 Driver。

### 2.4 v0.13：Web/Chat/Runs 观察面

v0.13 交付：

- toolbar/sidebar/tabs Workbench；
- Chat transcript 和 streaming；
- Dev Docs、End User Docs、Wiki；
- Runs graph 和 stage artifact 只读观察面。

来源：

- `.louke/project/specs/v0.13-001-web-ui-foundation/story.md`

v0.13 明确不实现 workflow rollback、waiver、CI interruption 和 workflow reflow：

- `.louke/project/specs/v0.13-001-web-ui-foundation/story.md:37-40`

### 2.5 v0.13.1：安装、版本身份和提交前质量门

v0.13.1 已提供：

- project-local/global Louke runtime；
- PATH shim 与 local/global identity；
- AC 引用版本化；
- pre-commit/commit-msg 质量门；
- diff-only AC trace 和 full-scan fallback；
- release identity 基础合同。

v0.14 应继承这些能力，不应重新设计安装、AC@version 或基础 Git hooks。

## 3. 当前真实实现状态

| 能力                                             | 状态     | 说明                                                                       |
| ------------------------------------------------ | -------- | -------------------------------------------------------------------------- |
| Scribe prompt、Story schema、Sage peer-review    | 已实现   | 已有正式 Agent 文档与交接合同。                                            |
| Scribe Runtime dispatch                          | 未实现   | Runtime 不会自动建立 Scribe semantic task。                                |
| Web Workbench、Chat、SSE/OpenCode transport      | 部分实现 | 能聊天和 streaming，但 Agent picker 尚不能证明后端使用所选 Agent。         |
| Programmatic Runtime 核心库                      | 已实现   | Store、Catalog、Orchestrator、ProgramStepExecutor、Gate 等存在。           |
| 唯一 production composition root                 | 未实现   | Projects、Runtime、Gates、Bindings 仍可能使用不同内存 Store。              |
| 自动 workflow Driver                             | 未实现   | 进入 program/semantic/human step 后尚无完整生产调度。                      |
| 完整 `new_feature`/`bug_fix` production workflow | 未实现   | 当前产品装配仍包含最小演示 graph。                                         |
| 权威 program result 边界                         | 未完成   | Runtime API 仍可接受客户端提供的 result 字符串。                           |
| stage-results 旧 artifact                        | 已实现   | author/review/gate/waiver JSON 和 freshness 已存在。                       |
| Runtime-native artifact/evidence                 | 未实现   | Runtime Store 尚无完整 artifact/evidence/stale 模型。                      |
| rollback                                         | 未实现   | 旧 regress 只写记录，不改变 Runtime 状态。                                 |
| v0.14 bounded waiver                             | 未实现   | 旧 `--force` waiver 可以跳过整组检查，不符合 v0.14 安全边界。              |
| workflow lifecycle hooks                         | 未实现   | 当前仅有 Git hooks 和 Agent session-save 约定。                            |
| Git pre-commit/commit-msg hooks                  | 已实现   | v0.13.1 已在 Louke 自身 dogfood。                                          |
| `lk init .` 采用已有 Git 项目                    | 部分实现 | 可以加 Louke skeleton，但不是 v0.14 transactional adoption。               |
| legacy adoption/restore/rollback                 | 未实现   | 当前 MigrationWizard 主要是内存模拟。                                      |
| no-new-debt baseline                             | 未实现   | 现有 baseline 是人工 allowlist，缺少 adoption、owner、expiry、stale 管理。 |

## 4. v0.14 推荐定位

v0.14 不重新发明 Runtime，而是完成生产切换：

> 将 v0.12 Runtime 核心、v0.13 Web/Chat、v0.13.1 安装和质量门整合为唯一生产工作流，并增加可靠的 rollback、waiver、adoption 和 lifecycle hooks。

## 5. 目标一：语义 Agent，程序驱动

### 5.1 程序职责

程序拥有：

- WorkflowRun 状态、合法边和 revision；
- program checks、测试执行和证据采集；
- semantic task 创建、输入 manifest 和结果 schema 校验；
- GitHub Issue、branch/worktree、commit/push、tag/release；
- artifact、evidence、digest、freshness；
- gate、waiver、rollback；
- hooks、重试、恢复和审计；
- project/run/task 的持久化。

### 5.2 Agent 职责

Agent 只承担：

- Story 调研、澄清和生成；
- 需求语义分析和一致性评审；
- Test Plan、Architecture、Interfaces 设计；
- 代码和测试内容生成；
- 代码评审、威胁分析和知识整理；
- 基于用户意图建议 `new_feature`、`bug_fix`、backlog 或其他已注册 workflow。

Agent 可以提出结构化结果或 patch，但不能：

- 改变 WorkflowRun；
- 批准 gate；
- 声明测试/build 已通过；
- commit/push/tag/release；
- 选择未被 definition 允许的下一阶段。

### 5.3 Agent 注销与职责迁移

- Scout 的语义残余归 Scribe；确定性 foundation 归 program handler。
- Warden 的 Story 语义判断归 Scribe/Sage/Lex；结构检查归 program validator。
- Keeper 的语义评审归 Prism；commit format、AC trace、anti-pattern 等归 program check/Git hook。
- Scout、Warden、Keeper 不再出现在新 workflow task、Agent catalog、Chat picker 或 model bindings 中。

### 5.4 Human 与 AI 的决策边界

原则：

> 产品、价值、风险和授权由人决定；技术方案默认由 AI 决定，程序验证事实，人类可以参与或覆盖技术决定。

必须由人决定：

- Go/Park/No-Go；
- Story 和 requirements approval；
- 范围、优先级和产品行为；
- M-LOCK；
- adoption baseline 的风险接受；
- waiver；
- workflow policy 变化；
- 在途 run 的 workflow migration；
- release approval。

默认由 AI 决定：

- Test Plan；
- Architecture；
- Interfaces；
- 技术选型、模块边界、测试分层；
- 实现、重构和代码评审；
- 威胁分析、性能优化和技术债务方案。

人类可以暂停自动 reviewer、参与技术讨论或直接提出技术 constraint。Runtime 保存每轮文档 revision/diff；人类编辑后，旧 AI review 应变为 stale。最终 M-LOCK 批准完整 contract bundle。

## 6. 目标二：No-New-Debt Adoption

### 6.1 基本原则

既有项目不能因为历史代码和旧文档永远无法采用 Louke，也不能通过 blanket waiver 把历史问题伪装为 PASS。

采用 no-new-debt 模型：

- 历史问题可以经过审计后冻结为 `baseline-known`；
- `baseline-known` 不是 PASS；
- 新问题或恶化的问题阻断；
- 已修复的问题自动关闭；
- 关键不变量永远不能 baseline。
- 传染机制：一旦旧代码被修改，则必须适用 Louke 流程。
### 6.2 谁负责

程序负责事实：

- 在 adoption preview 固定 Git revision/workspace digest；
- 运行适用的测试、lint、typecheck、安全、文档和追踪检查；
- 生成 finding identity、原始证据和检查器版本；
- 比较新增、未变、恶化、移动和已修复；
- 持久化 ledger 并执行 no-new-debt gate。

AI 负责语义归类：

- Prism 分析代码、测试和架构债务；
- Sage/Lex 分析 Story/Spec/Acceptance/trace 债务；
- Judge 分析安全风险；
- AI 解释影响、建议优先级和 remediation，但不能自行接受风险。

人类负责风险接受：

- 确认 adoption；
- 批准可进入 baseline 的历史问题；
- 指定 owner、理由、期限或复查条件；
- 拒绝不可接受风险。

不新增一个只包装扫描器的 Agent。

### 6.3 Debt Ledger

每条 baseline finding 至少包含：

```text
check_id
rule_id
finding_identity
source_revision
evidence_digest
scope
severity
status
owner
reason
review_condition
expires_at
```

首版以仓库相对路径作为 baseline 主索引，以文件作为豁免和解除豁免的单位；文件内 finding 作为审计明细保留。这样执行粒度简单，但仍能解释文件为什么进入 baseline。

```yaml
baseline_files:
  src/legacy/parser.py:
    baseline_blob: sha256:...
    adopted_at_revision: abc123
    status: baseline-known
    applicable_checks: [ruff, mypy, test-trace, anti-pattern]
    findings:
      - rule_id: FAKE-002
        evidence: ...
    owner: migration-team
    reason: pre-existing code
    review_condition: touched-or-expiry
```

相对路径是主键，`baseline_blob` 用于防止 rename/copy 绕过规则。finding identity 不得仅使用 `file:line`，建议结合：

```text
check_id + rule_id + semantic_location + normalized_evidence + artifact_digest
```

> **Aaron:** 建议通过 commit hash + file: line 来锁定；或者直接按文件相对路径；一旦被修改，就不再豁免。

例如测试反模式以测试函数 identity 和规范化 AST/语义摘要定位，而不是行号。

执行“触碰即纳管（touch-to-clean）”：

- unchanged baseline 文件继续显示为 `baseline-known`，不是 PASS；
- 某 commit 首次修改 baseline 文件时，对整个文件执行当前适用检查，而不是只检查改动行；
- 全部通过后，该文件永久退出 baseline 并变为 `managed`；
- 以后即使文件恢复成 adoption 时的内容，也不恢复 baseline；
- 内容完全相同的纯 rename 可以携带 baseline，并记录 `renamed_from`；
- rename 并修改、copy、split 或新文件必须立即符合当前流程；
- delete 将 baseline 条目标记为 `removed`；
- 项目级覆盖率、依赖漏洞、构建失败和多文件架构冲突不强行归入文件 baseline，另存 workspace-level debt。

Pre-commit 提供快速反馈；Runtime/CI 使用最终 commit hash 再次验证并写入权威的 `baseline_file_activated` event。被触碰文件除质量检查外，还必须关联当前 run/task、Issue 和适用的 Spec/AC。

### 6.4 Adoption 流程

1. 用户请求 adoption preview。
2. Runtime 固定 workspace/revision digest。
3. 程序运行所有适用检查。
4. AI 对需要语义判断的 finding 归类。
5. UI 展示：
   - 阻止 adoption 的关键问题；
   - 可 baseline 的历史问题；
   - 可自动修复问题；
   - 无法判断问题。
6. 用户确认风险接受。
7. Runtime 建立 restore point，并原子写入 adoption 状态和 baseline。
8. 后续 gate 执行 no-new-debt。
9. adoption apply 失败可 rollback/resume，不产生双重权威。

v0.14 首版不承诺把旧 workflow、旧 active stage 或旧 RuntimeRun 无损迁移到新 definition。**2026-07-17 Human 裁决明确**：支持的升级路径是 finish-then-reinstall（用旧版本完成当前 release → 停止/卸载/移除旧 Louke → 安装 v0.14 → 启动新 v0.14 run），不是 in-place 状态迁移。v0.14 不导入、不映射、不恢复、不修改、不附加 authority 到 v0.13 的 active run、stage、gate、task、session、evidence、catalog、audit 状态或 WorkflowDefinition。对既有 Git 仓库/代码库的 no-new-debt adoption 是**全新 v0.14 项目**（经显式 preview/confirm 后采用）；该 adoption 可检查代码/历史，但不得从 v0.13 Louke 状态（`current_stage`、evidence 等）迁移或推断 v0.14 权威 run 状态。必要时允许 breaking adoption：用户可以保留原项目不变，在新的项目/workspace 中使用新 workflow。adoption 失败的最低保证是不会破坏用户文件、Git history 和既有证据；复杂的跨版本 workflow migration 留待后续增强。

### 6.5 文档 Adoption

- 已发布版本文档：只读历史；
- 当前有效合同：进入 canonical contract；
- 与当前合同冲突：必须人工处理；
- 缺少追踪：可成为历史债务；
- legacy `current_stage`：不得推断成活动 WorkflowRun。

## 7. 回退与 Waiver

必须区分：

1. workflow rollback/return-upstream；
2. adoption rollback；
3. local/global Louke runtime fallback。

### 7.1 Workflow Rollback

首版实现保持简单，产品操作称为“返回上游步骤（`return_upstream`）”：

- 只支持 active、尚未发布的 run；
- definition 声明少量固定合法目标，不支持用户输入任意 stage；
- M-LOCK 后必须由人确认，AI 只能建议；
- Runtime 暂停在途 task，创建新 run revision/attempt，并把流程指针切到目标步骤；
- 目标步骤及其后的 artifact/approval/evidence 统一标记 stale/superseded，不在首版实现精细 dependency graph；
- 文件、文档、branch、worktree 和 commit 都保留，不自动删除或 Git revert；旧代码成为尚未对新合同重新证明的候选成果；
- 不自动补偿不可逆外部副作用。发现已 publish/tag 或结果不确定的外部副作用时拒绝自动回退，进入 `needs_attention`；
- 修正后重新经过目标步骤之后的评审和 gate，尤其必须重新 M-LOCK；
- 已发布项目不能返回并改写历史 Spec，只能创建新 Spec 或 Bug Fix。

增强版可以在后续引入 artifact dependency graph、精细 freshness 传播和外部副作用 reconcile；它们不是 v0.14 首版完成条件。

### 7.2 Waiver

Waiver 是针对一个明确标记为 waivable 的失败的风险接受决定，不是把 FAIL 改成 PASS。

每个 waiver 至少绑定：

- actor/principal；
- reason；
- target check/evidence；
- scope；
- revision/digest；
- created/expiry；
- recheck condition；
- status/revocation；
- 原始 failure reference。

永不可 waive：

- requirements approval；
- M-LOCK；
- identity/secret；
- revision CAS 和原子性；
- artifact freshness；
- Agent 自批、自报测试或伪造 program result；
- release identity mismatch。

## 8. 目标三：内置 Workflow Lifecycle Hooks

### 8.1 首版边界

v0.14 首版只支持 Louke 内置、版本化 hooks，不允许项目提供任意 shell 命令。

首版目标是建立稳定扩展点，后续可通过新增 hook implementation 和发布新 workflow definition version 增加功能，而不修改 Runtime 核心调度模型。

### 8.2 建议生命周期点

- `before_step_enter`
- `after_step_enter`
- `before_semantic_dispatch`
- `after_semantic_result`
- `before_human_gate`
- `after_human_decision`
- `before_step_exit`
- `after_step_exit`
- `before_return_upstream`
- `after_return_upstream`
- `before_run_archive`

### 8.3 Hook 合同

每个 hook 必须声明：

```text
hook_id
hook_version
lifecycle_point
input/output schema
blocking
timeout
retry_policy
idempotency policy
permissions
redaction policy
```

并绑定：

```text
run_id
step_id
attempt_id
revision
correlation_id
```

Hook 由 Runtime 调度，不依赖 Agent prompt 自觉调用。

Hook 不得：

- 批准 gate；
- 提交 program result；
- 直接选择 next step；
- 执行未声明的任意 shell；
- 绕过 freshness、identity 或 CAS。

### 8.4 适合 Hook 的行为

- 保存用户输入、纠正、决定和 Agent 响应；
- 保存 session/artifact references；
- 生成阶段摘要；
- 通知；
- 非权威知识整理；
- 环境 preflight；
- 临时资源清理。

### 8.5 不适合作为 Hook 的行为

以下应建模为正式 program step：

- 创建 GitHub Issue；
- branch/worktree 管理；
- commit/push；
- 权威测试执行；
- gate 决定；
- release/tag/history；
- 任何决定 workflow transition 的动作。

### 8.6 行为 Hook 与观察 Hook

- 行为 hook：可能影响阻塞或 evidence，必须固定在 WorkflowDefinition 中。
- 观察 hook：日志/telemetry，不改变状态，可全局启用，失败不得影响 run。

## 9. Workflow 的版本化演进

### 9.1 当前基础

当前 Runtime 已支持：

- `WorkflowDefinition(definition_id, version, ...)`；
- 同一版本不可用不同内容重新注册；
- `WorkflowRun` 固定 `definition_version` 和 `contract_digest`；
- run 创建后不改变 bound definition。

来源：

- `louke/runtime/catalog.py:30-35,77-91,365-423`
- `louke/runtime/store.py:1-6,46-70,171-180`

### 9.2 后续修改方式

Workflow 可以演进，但必须创建新版本：

```text
new_feature@1.0
new_feature@1.1
new_feature@2.0
```

以下变化必须 bump definition version：

- 增删或重排步骤；
- 改变 gate/rollback/waiver；
- 改变 hook；
- 改变 handler 或 semantic capability；
- 改变 blocking/non-blocking 或 evidence 要求。

规则：

- 新 run 默认使用当前 approved definition；
- 已开始 run 默认继续使用 pinned definition；
- 历史 run 永远按原 definition 解释；
- 旧 definition 可 deprecated，但在被 run 引用时不可删除或原地改写。

### 9.3 在途 Run Migration

v0.14 首版不支持在途 run 跨 workflow definition version 迁移，也不承诺兼容前一版 workflow。新 definition 只用于新 run。用户选择升级/安装 v0.14 之前，可继续使用旧 Louke/workflow 仅用于完成当前 v0.13 release；一旦升级，finish-then-reinstall 适用，旧 Louke/workflow 在 v0.14 安装后不得共存。

必要时允许 breaking workflow update，但必须满足：

- 不覆盖或破坏用户文件、Git history、Spec/AC/Issue/commit 追踪资产；
- 不把旧 run 猜测性转换为新 run；
- 明确提示用户该 workspace/run 不能自动升级；
- 提供只读导出和新项目/新 run 的创建入口。

跨 definition migration、step mapping 和 stale evidence 精细迁移留到后续版本。

### 9.4 Hook 与 Definition 版本

WorkflowDefinition 引用固定 `hook_id + hook_version`。以后新增 hook：

1. 注册新的内置 hook；
2. 发布新的 workflow definition version；
3. 新 run 使用新 hook；
4. 旧 run 继续使用原 hook。

## 10. Trace/Evidence Graph 独立于 Workflow

项目核心资产的 identity 不应嵌死在 workflow stage 中：

```text
SPEC-ID
FR/NFR
AC
GitHub Issue
commit hash
artifact digest
```

WorkflowRun 只记录这些资产通过什么流程产生、检查和批准，不拥有或重写这些 identity。

因此 workflow 变化时：

- 不改 SPEC-ID；
- 不改 AC identity；
- 不改已有 GitHub Issue；
- 不改 commit hash；
- 不重写相互引用；
- 新 workflow/run 可以继续引用旧资产；
- 只有资产内容 digest 或适用合同变化时，相关 approval/evidence 才 stale。

建议将其建模为独立的 Trace Graph/Evidence Graph。

## 11. Branch/Worktree 策略与 Hotfix FAQ

### 11.1 最小分支模型

保留一个活动主开发分支的原则，同时增加明确的短生命周期维护分支：

```text
main
releases/{version}
fix/{issue-number}
maintenance/{task-or-run-id}
```

- `main`：当前已发布、可 hotfix 的产品基线；不允许 Agent 直接随意 commit。
- `releases/{version}`：一个版本唯一的活动 feature/release 分支。
- `fix/{issue-number}`：已发布产品缺陷或 CI 阻塞修复；来源和合并目标由 program handler 根据 failing branch 决定。
- `maintenance/{task-or-run-id}`：夜间重构、非行为性清理和无人值守维护；必须绑定独立 worktree、run/task 和有效期。

Branch/worktree 创建、切换、同步、合并和清理由 Runtime program handler 执行，Agent 只在 Runtime 指定的当前 worktree 中工作。

### 11.2 FAQ：功能开发期间出现紧急 Hotfix 怎么办？

Hotfix 的产品目标是 `main`，但实现不直接在 `main` 工作区中进行：

1. Runtime 从 `main` 创建 `fix/{issue-number}` 和隔离 worktree；
2. Bug Fix workflow 绑定既有 Spec/AC、Issue 和 failing evidence；
3. 修复通过 R-G-R、回归和适用安全门；
4. 先合入 `main` 并发布 hotfix；
5. 当前 `releases/{version}` 可以立即同步该修复，也可以延期到 release 合回 `main` 前处理。

立即同步是默认建议，尤其适用于安全问题、共享模块或当前 release 会修改同一区域的情况。允许延期时，Runtime 必须在活动 release run 中记录 `pending_hotfix_sync`；该债务在 release merge 前必须解决，不能静默遗漏。

同步方式由程序根据历史关系选择 merge 或 cherry-pick，并记录 main commit、release commit 和 Issue 的追踪关系。

### 11.3 夜间重构分支

夜间重构不应伪装成 `fix/*`。使用 `maintenance/{task-or-run-id}`：

- 从明确目标分支创建隔离 worktree；
- 只允许不改变已批准产品行为的重构、依赖维护和机械清理；
- 必须通过当前目标分支要求的 unit/integration/quality gates；
- 合并前重新同步目标分支并复验；
- 失败时保留诊断 evidence，安全删除 worktree；
- 若发现需要改变行为、Spec 或 Architecture，停止 maintenance run，转成 `new_feature` 或 `bug_fix`；
- 分支到期或任务结束后由程序清理。

### 11.4 CI 失败使用什么分支？

- `main` 的 CI 失败：创建 `fix/{issue-number}`，修复目标是 `main`。
- `releases/{version}` 独有的 CI 失败：从该 release branch 创建 `fix/{issue-number}`，先修 release；若问题也适用于 main，再建立显式 backport/forward-port 关系。
- 纯工具升级、格式化或非行为性维护可以使用 `maintenance/*`。
- 不能仅为了让 CI 变绿而降低断言、删除测试或扩大 baseline。

## 12. 现有 Story 建议调整

- Story 1–2：保留 Scribe/Sage/Human，但改为“v0.14 完成 Runtime dispatch”，不是重新实现 prompt。
- Story 3：重写 Human review 和 Archer revision；Archer 不自行 commit，Runtime 保存 revision/diff。
- Story 4–6：保留，转成 CI report 和测试证据合同。
- Story 7–10：扩展为正式 rollback/waiver 状态模型。
- Story 11：保留 branch/worktree program handler。
- Story 12：改为集成 v0.13.1 version identity gate。
- Story 14：移到 test/release exit condition。
- Story 15：Scribe 部分已完成；重点为 Runtime dispatch 和 Scout/Warden/Keeper 注销。
- Story 16–21：保留，但标明现状仅部分实现。
- Story 22：扩展为 no-new-debt transactional adoption。
- Story 25–26：移到 release/cutover exit conditions。
- 新增正式 lifecycle hooks 用户故事，替换 `story.md` 末尾 HTML 注释。

## 13. P0 生产风险

1. Runtime API 接受客户端 result，可能伪造 program/semantic step 完成。
2. Projects/Runtime/Gates/Bindings 生产装配可能使用不同内存 Store。
3. 旧 waiver 可以跳过本应不可 waive 的门禁。
4. Chat Agent 选择没有可靠传入 OpenCode session。
5. 没有自动 Driver 和完整 production workflow。
6. Stage artifacts 与 Runtime 分离，Runs UI 仍依赖 fixture/read-model 假实现。
7. legacy adoption/rollback 仍是内存模拟。
8. Scout/Warden/Keeper 仍出现在 Agent/CLI/Web/README 中。

## 14. 推荐实施顺序

1. 建立唯一持久 production composition root。
2. 关闭客户端/Agent 伪造 program result 的路径。
3. 接入自动 Driver 和完整 `new_feature`/`bug_fix` definitions。
4. 建立真实 responsibility inventory，注销 Scout/Warden/Keeper。
5. 建立 Runtime-native artifact/evidence/freshness。
6. 实现 workflow rollback 和 bounded waiver。
7. 实现 no-new-debt adoption transaction。
8. 实现内置 lifecycle hook registry/executor。
9. 接入 branch/worktree、CI report 和 release identity。
10. 完成 installed-wheel E2E、Louke dogfood 和生产文档切换。

## 15. 已确认决策

1. 既有项目采用 no-new-debt baseline：历史问题经审计后可冻结，但不是 PASS；新问题和恶化问题阻断。
2. v0.14 首版只支持内置、版本化 workflow hooks，不支持项目任意 shell hook。
3. Workflow definition 可持续演进，但必须版本化、不可变；在途 run 默认固定原版本。
4. Trace/Evidence Graph 独立于 workflow 定义，Spec/AC/Issue/commit identity 不因 workflow 变化而改变。
5. 非技术的产品、价值、风险和授权决定由人类负责；技术方案默认由 AI 决定，人类可以参与或覆盖；程序负责验证事实。
6. v0.14 首版不处理旧 workflow definition 或在途 run 的跨版本兼容；必要时允许 breaking update，用户可以在新项目/workspace 使用新 workflow，但不得破坏用户文件和 Git history。
7. Adoption baseline 以仓库相对路径为主索引、文件为豁免单位；文件首次有效修改后永久退出 baseline，实施触碰即纳管。
8. 首版 `return_upstream` 采用固定合法目标和保守的下游统一 stale 规则，保留代码与历史，不实现精细 dependency graph 或自动外部副作用补偿。
9. Hotfix 使用 `fix/{issue}` 从 main 隔离执行并合回 main；可立即或延期同步到活动 release，但 release 完成前必须消除 pending sync。
10. 夜间重构使用短生命周期 `maintenance/{task-or-run-id}` 和隔离 worktree，不复用 fix 分支。
11. **接口策略**：v0.14 在 v0.13 基础上开发，开发期 CLI 与 Web Chat **并行可用**——CLI 继续提供 v0.13 风格的 workflow 推进（含 `lk agent ...`），以便 dogfood、调试和回归；Web Chat 同步接入新 Runtime dispatch。v0.14 release tag 当日切换为 **Web Chat 唯一开发入口**，CLI 退化为 `lk serve` / `lk upgrade` 等少数运维命令。该切换必须由 Runtime 在 release cutover 阶段统一收敛，禁止在过渡期悄悄混合新旧入口策略。
12. **Sage 交互策略**：Sage 不再承担 Scribe 的需求发现职责，不要求在 M-SPEC 开始时使用 `question`。通常先形成 Spec 草稿，再通过可追溯 inline discussion 澄清；`question` 保留为无法形成文档锚点或必须立即取得产品决定时的例外通道。**例外 `question` 通道的等待语义（2026-07-17 稳定化）**：若 Sage 例外使用 `question` 且 Human 未在同一 spec revision 内回复，Runtime 必须持久化 `waiting_human` 状态；被阻塞需求保持 `Decided=⚠️`；Runtime 不做默认决定、不消耗 review 轮次、不解除 requirements approval 或 M-LOCK 的阻塞。`lk serve` 重启并重新进入 chat 窗口后，Sage 的提问必须仍可见——这由 opencode session 恢复机制承载，作为"可观察性"载体；Runtime 自身的 `waiting_human` 持久化与 gate 阻塞语义不依赖 opencode session 恢复。只有匹配的 Human 回复落入同一 spec revision 后，Runtime 才恢复该 task 并继续后续 gate 判定。
13. **Programmatic M-SPEC**：Runtime 负责 revision/digest/diff、结构验证、讨论扫描与循环、锚点、Git/GitHub Issue reconcile、requirements approval/lock 和重启恢复；Sage/Lex 每次只完成一轮语义任务，不调用 workflow/gate 工具。
14. **Spec 规模上限**：单个 Spec 最多 30 条有效 FR+NFR，`Valid=❌` 不计数，恰好 30 条允许。硬门禁由 Runtime 在 Lex 前执行且不可 waive；作用域不是 release 累计值。推荐一个 Story/Spec 对应一个 release。
15. **拆分回退**：超限进入 `needs_story_split` 并返回 M-STORY。Runtime 不自动决定拆分边界；Scribe 提案、Human 决策。原 Story 作为 Split parent 保留，子 Story 带 `parent_story_id` 并进入后续独立 release/run。
16. **M-TESTPLAN 评审**：Archer 负责作者职责，S 档 Prism 负责独立技术评审；Shield 可提供下游可执行性反馈但不批准，Sage 不再承担 Test Plan 评审。
17. **cutover 后旧 workflow CLI 命令缺位合同（2026-07-17 修订，替代先前 deprecated no-op 行为合同与 audit 事件合同）**：v0.14 release cutover 生效后，旧 workflow CLI 命令（包括但不限于 `lk agent ...` 等曾用于推进 workflow 的命令）不作为公开命令存在——它们不在 CLI 注册表中注册、不出现在 `--help` / shell completion / 任何命令列表中、不会被 CLI dispatcher 路由到 Runtime / 任何 Agent / 任何 workflow；不存在专用于"已废弃命令"的 audit 事件类型（`cli_legacy_deprecated_noop` 事件已废止）、不存在专用的 deprecated no-op 退出码合同、不存在专用的迁移警告合同、不存在任何 deprecated no-op 兼容 fallback；用户尝试调用一个不再注册的旧 workflow 命令只能命中 CLI 自身的普通 unknown/unsupported-command 处置路径。v0.13 baseline 上的 pre-cutover 开发期间（在 v0.14 release tag 之前），CLI 仍按既有 v0.13 行为提供 workflow 推进命令以便 dogfood 与调试；cutover 由 Runtime 在 release cutover 阶段统一执行，过渡期不出现"新旧入口半切"的中间形态。该合同是 BS-30 / cutover-checklist §F 的依据，不依赖其它 v0.14 子系统即可独立验证；先前"cutover 后 deprecated no-op 行为合同与 audit 事件合同"的所有内容（exit-0 / stderr-only 警告 / stdout 空 / `cli_legacy_deprecated_noop` audit 事件 / Runtime-native store / `command identity`+`actor`+`side_effect_invoked=false` 负载 / 警告英文、i18n 推迟到 v0.16）在本修订生效后全部不再适用。

18. **无 GitHub Backlog Project（2026-07-17 Human 裁决）**：v0.14 不创建、不依赖、不检查任何 per-repository GitHub backlog Project。Louke 的 Backlog 是 Runtime-native 持久化状态，Park/No-Go 和被阻塞的项目请求使用该 canonical backlog。项目 setup 流程不得创建/复用/检查 GitHub backlog Project；`backlog_project` 不作为 v0.14 的活动需求元数据。物理存储格式/路径由 Architecture 决定，但重启持久化、单一权威 store、无 split-brain、无丢失是产品需求。对应 story.md §0.1 第 14 条、BS-32、cutover-checklist §H。

19. **无权限探测 Issue/PR（2026-07-17 Human 裁决 + Sage blocker #4 修正）**：`gh auth status` 仅证明认证健康，不得作为仓库/资源操作权限的证据。粗糙信号（如仓库 `viewerPermission`）仅可作诊断参考，不是未来操作通过的权威凭证。Runtime 使用真实的即时远程认证业务操作（push、Issue/PR API、per-release GitHub Project 操作、release/tag 发布等）。per-release GitHub Project 复用身份优先使用 manifest 记录的不可变 Project node ID；若无，匹配声明的 owner + exact release-scoped project identity/title + repository/release binding。零/多/冲突匹配进入 waiting_human；永不用模糊标题选取。若这些操作因认证/权限失败，Runtime 持久化该失败操作和可操作错误，进入 `waiting_human`；Human 授予/变更授权后，Runtime 以相同 idempotency key 重试同一操作。权限失败不得被跳过、豁免、猜测或转换为 PASS；在真实操作成功前，下游不得推进。不得产生一次性探测 Issue/PR 的副作用。本地 commit 不是 GitHub 权限操作，不在本约束范围内。对应 story.md §0.1 第 15 条、BS-33、cutover-checklist §I。

20. **Setup 元数据权威推导与冲突仲裁（2026-07-17 Human 裁决 + Sage blocker #2 补充 + Lex 规范化建议）**：项目 setup 元数据从 Git remote、有效项目元数据、已认证身份和其它权威来源推导候选值，展示每个候选的 provenance。规范化的语义等价候选（如等价 repo URL 形式）可自动接受并记录所有 provenance，无需字节相等。冲突/歧义仍 waiting_human。当多个权威来源产生冲突值时，Runtime 持久化显式 setup `waiting_human` 状态（含所有候选值及其 provenance），阻止外部修改和 WorkflowRun 创建/下游 setup 推进。Human 选择或提供权威值后，Runtime 持久化决定、actor、候选 provenance、setup revision/digest 和时间戳；以相同 setup revision/attempt 幂等恢复。重启后保留未解决的冲突或已解决的决定。不得静默覆盖冲突值、不得在无决定时推进 setup。对应 story.md §0.1 第 16 条、BS-34、cutover-checklist §J。

21. **无 v0.13 → v0.14 Louke 状态/工作流迁移或共存合同（finish-then-reinstall 唯一升级路径，2026-07-17 Human 裁决 + Sage blocker #3 补充）**：升级的唯一支持序列为：(1) v0.13 active release/run 在 v0.13 下正常完成；(2) v0.13 进程/安装被停止并移除；(3) 安装 v0.14；(4) v0.14 独立启动并创建全新 authority run——不导入/映射/恢复旧 authority。若 v0.13 release/run 未完成，v0.14 不接管该 run；用户用 v0.13 完成或放弃（在 v0.14 外处理）。v0.14 安装后旧 Louke/workflow 不得并发可用。无双版本状态命名空间、无兼容桥、无迁移向导、无 in-flight 迁移、无混合新旧 authority。Pre-cutover v0.13 CLI 仅为 release cutover 前的开发基线，不是 v0.14 安装后的同步生产兼容面。对既有 Git 仓库/代码库的 no-new-debt adoption 保留为**全新 v0.14 项目**（经显式 preview/confirm 后采用）；该 adoption 可检查代码/历史，但不得从 v0.13 Louke 状态（`current_stage`、evidence 等）迁移或推断 v0.14 权威 run 状态。对应 story.md §0.1 第 17 条、BS-35、cutover-checklist §K。

22. **Agent 退役清单与表面清理（2026-07-17 Human 裁决）**：职责清单覆盖 Scout、Warden 和 Keeper（不仅是 Scout/Warden）。cutover 后，active catalog、docs、help、prompts、路由必须排除这些 Agent；不可变的历史/审计 artifact 可保留其名称，不得仅因擦除名称而重写历史。对应 story.md §0.1 第 18 条、BS-36、cutover-checklist §A / §L。

23. **Runtime Backlog UI 与项目启动行为（继承 v0.12 FR-1001/FR-1101/FR-1701，2026-07-17 Human 裁决）**：同一 workspace 最多一个 active 非 hotfix 主 Project；已发布产品的 `bug_fix`/hotfix 是唯一并行例外且完全隔离。主 Project active 时新 `new_feature` 请求进入 Runtime-native Backlog。Web 列出所有 Backlog 条目（Park、No-Go、被阻塞请求），提供考虑启动操作——打开预填预览表单、重新运行验证/就绪/active-project 策略、Human 显式确认后原子创建最多一个新 Project/WorkflowRun。Park/No-Go 原始决定/状态/历史不可变/可审计。继承 v0.12 FR-1001 AC-4、FR-1101 AC-3、FR-1701 AC-5 的已批准行为。对应 story.md §0.1 第 19 条、BS-32（强化）、cutover-checklist §H（强化）。

24. **M-FOUND 分支 reconciliation（2026-07-17 Human 裁决 + Sage B-08/B-09/B-10/B-11 补充）**：扫描绑定到成功刷新的 declared remote 的权威 `main` SHA；本地 main 不匹配为可见阻塞条件。本地 `refs/heads/main` 和权威 remote main 均排除在普通非 main 分支 merge/delete 候选之外。本地 main reconciliation 单独展示，状态为 equal/behind/ahead/diverged。equal → 分支扫描继续；behind → Human 确认 fast-forward；ahead → Human 确认 publish/push（无 force push）；diverged → Human 确认 merge remote main 到本地 main 后验证和非 force push。仅 equal 可产生 PASS。永不 force-push/reset/delete main ref。枚举本地 `refs/heads/*` + 已刷新 declared-remote 分支 ref，排除 symbolic/非分支 ref 和绑定的权威 main ref。规范 identity = repository + full ref name + head SHA；同 ref/SHA 折叠，同 SHA 不同 ref name 为独立行。`fully_merged=true` iff 分支 head 是 bound main head 的祖先；`ahead_count` = `main..branch`。Declared-remote fetch 必须权威完成。绑定到 active WorkflowRun 的分支为 `protected_active_run`——M-FOUND 不得 merge/delete。BS-37 允许的自动化仅为权威扫描、本地 main reconciliation、Human-bound retain 决策、非 protected 选中分支的 merge→validate→push→delete。对应 story.md §0.1 第 20 条、BS-37、cutover-checklist §M。

## 16. 后续 Story 更新应补充的正式用户故事

1. No-new-debt adoption preview/confirm/rollback。
2. Baseline debt ledger、expiry、review 和 no-worsening gate。
3. Versioned immutable workflow definitions 与在途 migration preview。
4. 独立 Trace/Evidence Graph。
5. Built-in lifecycle hooks、hook failure/retry/recovery。
6. Human/AI/Program decision boundary。
7. Runtime-native artifact freshness 和 rollback stale propagation。
8. Bounded waiver policy 与不可 waive invariants。

## 17. Runtime 调用 OpenCode Agent/Subagent 技术可行性调研（2026-07-18）

### 17.1 结论与范围

结论：**技术上可行**。OpenCode 已提供 Runtime 所需的 Agent/subagent 调用、结果返回、parent/child session、动态 Agent/模型选择、多轮消息和 server restart 后 session 恢复基础能力。v0.14 可以沿用“Runtime 拥有 workflow authority，OpenCode 承载 semantic task 对话与执行”的方向，不需要让 Agent 或 OpenCode session 成为 WorkflowRun 状态权威。

本节记录实机 API 调研和工程约束，是后续 Architecture、Interfaces、Test Plan 与实现的研究输入，不直接构成 Story 行为种子、Spec requirement 或 Acceptance Criteria。未实测的 schema 能力必须在集成/E2E 中继续验证，不能仅凭本节判定交付完成。

### 17.2 实测环境与证据

- OpenCode 版本：`1.18.1`。
- 能力来源：运行中 OpenCode server 的 `/doc` OpenAPI 文档及真实 HTTP probe。
- message endpoint：`POST /session/{sessionID}/message`。
- message schema 支持：`messageID`、`model`、`agent`、`noReply`、`tools`、`format`、`system`、`variant`、`parts`。
- input parts 支持：`TextPartInput`、`FilePartInput`、`AgentPartInput`、`SubtaskPartInput`。
- `SubtaskPartInput` 支持：`prompt`、`description`、`agent`、可选 `model` 和 `command`。
- 实测向 parent session 发送指定 `explore` subagent 的 `SubtaskPartInput`，返回值为预期的 `RUNTIME_SUBTASK_OK`。
- 实测 parent session：`ses_08cdd6e52ffewC6qsueDmSJeWC`。
- 实测 child session：`ses_08cdd6db4ffe9FaJsieiMECiYg`。
- 停止并重新启动 OpenCode server 后，parent session 仍可查询，并可通过 parent 的 children API 找回上述 child session。

该 probe 确认了“Runtime 创建 parent → 指定 subagent → 获得返回 → 建立 child → server restart 后恢复 parent/child 关联”的核心链路。该 probe 没有覆盖完整 Louke Web Chat、Runtime store、SSE 断线、permission flow、abort、并发 turn 或 installed-wheel 环境。

### 17.3 Runtime 如何传递指令

普通 Agent turn 可以在 message 顶层传递 `agent`、`model`、`system`、`tools`、`format` 和 `parts`。真正的 subagent task 应使用 `SubtaskPartInput`，明确传递目标 `agent`、任务 `prompt`、简短 `description` 和可选 `model`/`command`。

推荐 Runtime 输入由以下内容组成：

- immutable Context Manifest：`run_id`、`step_id`、`task_id`、`attempt_id`、workspace/revision、artifact identities/digests、allowed scope、forbidden side effects；
- Agent 固定 prompt/contract digest；
- 本次动态任务 prompt；
- 动态模型 `providerID` / `modelID`；
- 最小化 tools/capabilities；
- 必要的 text/file parts；
- 期望 output schema 或明确的 JSON result contract。

动态 `system`、prompt 和 tools 只能收窄或补充当前任务，不能扩大 Agent 固定权限、改变 WorkflowDefinition、授予 program-result/gate authority 或绕过 Runtime policy。

### 17.4 Agent/Subagent 如何返回结果

可用结果路径包括：

- 同步 message response 返回 assistant message；
- event/SSE 流返回增量、完成或错误事件；
- session messages API 读取已持久化 transcript；
- parent children API 定位 subtask 创建的 child session，再从 child session 回收原始结果。

本次实测确认同步 parent response 返回了 subagent 的预期结果，并确认 child session 已创建、可在 restart 后找回。OpenAPI schema 支持读取 session messages；“Runtime 总是从 child transcript 提取最终结构化结果”尚需单独集成验证。

生产设计不应只相信 parent Agent 对 child 的摘要。推荐 Runtime 定位 child session，读取 child 的最终 message/result，校验至少以下字段：

```json
{
  "task_id": "task_123",
  "attempt_id": "attempt_1",
  "manifest_digest": "sha256:...",
  "status": "completed",
  "verdict": "pass",
  "artifacts": [],
  "findings": [],
  "needs_human": null
}
```

空结果、无法解析、schema 不符、task/attempt 不匹配、manifest digest 不符、artifact 不存在或状态未知均不得被解释为完成/PASS。OpenCode 的 `format` 能力可用于约束 message response；subtask child 自身的结构化输出仍应由 prompt contract + Runtime validation 双重保障，并通过实测确认 `format` 对 parent/child 的具体作用域。

### 17.5 多轮对话

OpenCode session 是多轮消息容器。Runtime 获取 child session ID 后，可以继续向 `POST /session/{child_session_id}/message` 发送 Human 回答、上游修订或 review feedback，使任务在原上下文继续。

推荐约束：

- 一个 semantic task attempt 对应一个 child session；
- 同一 session 同时最多一个 active turn；
- Author 与独立 Reviewer 使用不同 session；
- Agent 之间不直接建立不可审计对话，Agent A 的结果先由 Runtime 持久化，再作为 Agent B 的 manifest 输入；
- Human 回答先写入 Runtime authority store，再发送到匹配的 child session；
- context 过长或 contract/input digest 已改变时创建新 attempt，不在旧 session 中伪装成同一输入继续执行。

### 17.6 Session 引用、持久化与恢复

Runtime 至少需要持久化：

```text
run_id
step_id
task_id
attempt_id
parent_session_id
child_session_id
agent_id
model_id
manifest_digest
last_message_id
last_event_id
task_status
```

OpenCode session 持久化对话和 parent/child 关系；Runtime store 持久化 WorkflowRun、当前 step、gate、`waiting_human`、task/attempt、幂等键和合法转移。OpenCode session 可作为恢复和可观察性载体，但不能成为 workflow authority。

推荐恢复顺序：

1. Runtime 从自己的持久化记录枚举未完成 semantic task。
2. 连接或重启使用相同数据目录的 OpenCode server。
3. 按 parent/child session ID 查询 session、children、messages 和 status。
4. 若已有有效最终结果，回收并校验，不重复 dispatch。
5. 若仍运行，恢复事件订阅或轮询。
6. 若明确失败/终止，记录 attempt outcome 后按 policy 决定是否创建新 attempt。
7. 若 session 丢失，以原 immutable Context Manifest 创建新 attempt；不得把新 session 伪称为原 attempt 的无缝恢复。

实测证明 OpenCode server restart 后 session/parent-child 关联可恢复；Runtime restart、OpenCode 数据目录丢失、版本升级和 transcript corruption 仍需 E2E 覆盖。

### 17.7 动态 Agent、模型与执行成本

OpenAPI schema 支持在顶层 Agent message 和 `SubtaskPartInput` 中动态指定 Agent/模型。Runtime 可以按 semantic role、task 类型或 pinned model policy 选择 `providerID` / `modelID`，但实际选择必须固化到 attempt record，运行中的 attempt 不得因后续 model binding 修改而漂移。

使用 `SubtaskPartInput` 仍需要 parent session，并可能消耗 parent Agent turn。该 parent 是 OpenCode subtask 机制的一部分，不要求 Louke Maestro 参与，但会带来成本、延迟和 parent 摘要失真风险。Runtime 应读取 child 结果而非只依赖 parent summary。若未来要求消除 parent turn，可评估把特定角色配置为可直接选择的 Agent；这属于成本/架构优化，不是当前技术可行性 blocker。

### 17.8 状态、中断、超时与取消

OpenAPI 提供 session status、messages、children、event stream、health 和 abort 等恢复/控制表面。Runtime 必须定义自己的业务 deadline；HTTP client timeout 只表示调用方没有及时得到响应，不证明 Agent 已停止，也不证明 task 失败。

推荐处理：

- HTTP timeout/断连后先按 session ID reconcile，禁止立即重复 dispatch；
- 查询到有效最终结果则直接回收；
- 查询到仍运行则继续等待、重订阅事件或按 Human/policy 决定取消；
- 超过 Runtime deadline 时调用 abort，并再次查询确认终止结果；
- server 不可用时重启后按 session ID 恢复；
- 无法证明完成时进入 `interrupted` / `needs_attention`，不得隐式 PASS；
- semantic task 状态建议至少覆盖 `created`、`dispatching`、`running`、`waiting_human`、`completed`、`failed`、`timed_out`、`aborting`、`interrupted`、`lost`、`needs_attention`。

status/event/abort 的具体 wire schema 和竞态行为来自 OpenAPI 能力发现，但本次 probe 未逐项执行，必须由 Interfaces 与集成测试锁定。

### 17.9 必须进入后续设计的风险与约束

1. **幂等与 uncertain outcome**：每次 dispatch 绑定 `task_id + attempt_id + manifest_digest`；网络失败后先查询/reconcile，避免重复 subtask 和重复副作用。
2. **副作用不是 exactly-once**：LLM/session 调用无法提供业务 exactly-once。代码、Git 和外部 API 操作必须由 Runtime 对 workspace/diff/resource 做 reconciliation。
3. **权限请求**：Agent 可能停在 OpenCode permission request。Runtime 必须监听并显式响应，或通过 Agent policy 消除无人处理的 `ask`；不能无限挂起。
4. **Human question**：Agent 返回结构化 `needs_human`，Runtime 持久化并通过 Web 展示，Human 回答再进入原 child session；Agent 不直接拥有 workflow wait/advance authority。
5. **并发**：同一 child session 禁止并发 turn；Runtime task/revision 使用 CAS 防止重复继续。
6. **结构化输出**：即使使用 JSON Schema，Runtime 仍需二次验证身份、digest、artifact 和状态。
7. **上下文膨胀**：长期 session 可能压缩或超过窗口；权威输入必须存在于 manifest/artifact，而非只存在 transcript。
8. **版本兼容**：OpenCode endpoint/schema 会演进。启动时应检查 health/OpenAPI capability，不能只按版本字符串假定功能。
9. **安全边界**：manifest 必须限制 workspace、tools、write scope、secrets 和 forbidden side effects；OpenCode tool permission 不能替代 Runtime authority。
10. **生命周期**：Architecture 需要定义 session 保留、归档、abort、删除和隐私策略，避免无限累积。

### 17.10 推荐的最小正式合同

后续 Architecture/Interfaces 至少应定义以下一等对象与状态机：

- `SemanticTask` / `SemanticTaskAttempt`；
- immutable `ContextManifest` 及 digest；
- Runtime task ↔ OpenCode parent/child session mapping；
- dispatch request 和 structured result schema；
- one-active-turn concurrency rule；
- Human continuation/wait protocol；
- timeout/abort/interruption/lost-session recovery；
- idempotency/reconciliation 规则；
- Agent/model/tool binding 与 contract digest；
- Runtime authority 与 OpenCode observability/session authority 的明确分离。

最终可行链路为：

```text
Runtime SemanticTask
  -> OpenCode parent session
  -> 指定 agent/model/prompt 的 child subtask
  -> child session result/transcript
  -> Runtime schema/digest/artifact validation
  -> Runtime workflow transition
```

恢复链路为：

```text
Runtime persisted attempt
  -> parent_session_id / child_session_id
  -> status/messages/children reconciliation
  -> 回收完成结果、继续原 session、显式 abort，或创建新 attempt
```
