# STR-1701: v0.17 Workflow Enhancements — 从 v0.14 延后的增强与治理

---

## 0. 来源

本 Story 的所有内容均来自 v0.14 Workflow Reflow（STR-1401）的 Out-of-Scope 清单和 `research-report.md` 中已确认但明确推迟到后续版本的能力。v0.14 聚焦于"把 v0.12/v0.13/v0.13.1 整合为唯一生产工作流 + 四项首版 MVP 能力"；本 Story 承接那些需要更复杂设计、更丰富治理或更高成熟度的增强项。

---

## 1. 目标

在 v0.14 生产工作流稳定运行的基础上，补全以下增强能力：

1. **CI Report 完整中断矩阵**：支持 immediate/safe-point/record-only 三种中断模式，以及迟到报告的正确处理。
2. **Branch/Worktree 生命周期自动化**：夜间重构分支、hotfix 延迟同步自动管理、复杂 branch/worktree 生命周期。
3. **跨 Workflow Definition 的 In-Flight Migration**：支持在途 run 跨 workflow definition version 迁移、step mapping 和兼容处理。
4. **精细 Artifact Dependency Graph**：局部 freshness 传播、自动补偿/reconcile 不可逆副作用。
5. **Lifecycle Hooks 增强**：项目自定义 hook（在安全约束下）、复杂 hook marketplace/policy。
6. **Baseline 高级治理**：复杂语义 identity、owner/expiry 自动治理、workspace-level 高级 debt analytics。
7. **Waiver 高级治理**：expiry/renew/revoke、多 waiver 冲突处理。
8. **测试与证据补齐**：v0.12.1 测试债务清理、通用真实环境矩阵、全面浏览器覆盖。
9. **Hotfix/Branch 模型完善**：Hotfix 延迟同步、夜间重构的完整规则。

---

## 2. 承接清单（来源：v0.14 Out-of-Scope）

### 2.1 CI Report 完整中断矩阵

**v0.14 保留**：完成核心 workflow 必需的权威测试执行和证据。

**v0.17 承接**：

- 三种中断模式：immediate（立即中断当前 step）、safe-point（当前语义任务完成后中断）、record-only（仅记录，不中断）。
- 迟到报告处理：不匹配当前 revision 和 run 状态的 CI report 不改变 workflow 状态，但可被记录和审计。
- 用户可查看每个 CI report 的匹配状态、处理方式和影响。

### 2.2 Branch/Worktree 生命周期自动化

**v0.14 保留**：沿用现有 `main`、`releases/{version}`、`fix/{issue-number}` 最小分支规则。v0.14 不新增 `maintenance` 分支、不实现夜间重构、不做 branch/worktree 自动化创建/切换/清理。

**v0.17 承接**：

- 夜间自动重构：使用 `maintenance/{task-or-run-id}` 分支，隔离 worktree，通过规定门禁后合入。失败时保留诊断记录并安全清理。
- Hotfix 延迟同步自动管理：`fix/{issue}` 从 main 隔离执行并合入 main；可立即或延期同步到活动 release；release 完成前必须消除 `pending_hotfix_sync`。同步方式由程序根据历史关系选择 merge 或 cherry-pick。
- 复杂 branch/worktree 生命周期：创建、切换、同步、合并、清理的完整自动化，Agent 只在 Runtime 指定的 worktree 中工作。

### 2.3 Hotfix/Branch 详细规则

**以下规则从 v0.14 研究报告中提取，全部在 v0.17 实现**：

- **Hotfix 目标 main**：使用 `fix/{issue}` 隔离 worktree，先合 main。可立即或延期同步 active release，但 release 完成前必须解决 pending sync。
- **夜间重构**：使用 `maintenance/{task-or-run-id}`；若改变行为/Spec，转 `new_feature`/`bug_fix`。
- **CI 失败分支规则**：
  - `main` 的 CI 失败：创建 `fix/{issue}`，修复目标是 `main`。
  - `releases/{version}` 独有的 CI 失败：从该 release branch 创建 `fix/{issue}`，先修 release；若问题也适用于 main，建立显式 backport/forward-port 关系。
  - 纯工具升级、格式化或非行为性维护：使用 `maintenance/*`。
  - 不能仅为了让 CI 变绿而降低断言、删除测试或扩大 baseline。

### 2.4 跨 Workflow Definition 的 In-Flight Migration

**v0.14 保留**：Workflow definition 版本化不可变；新 run 使用当前 definition；已开始 run 固定原版本。v0.14 不做跨版本迁移。

**v0.17 承接**：

- 在途 run 跨 workflow definition version 迁移的 preview 和确认。
- Step mapping：旧 definition 的 step 到新 definition 的 step 的映射规则。
- 迁移后 stale evidence 的精细标记（而非统一下游 stale）。
- 旧 workflow 兼容边界：什么情况下可以迁移，什么情况下必须在新项目/workspace 使用新 workflow。

### 2.5 精细 Artifact Dependency Graph

**v0.14 保留**：return-upstream 后统一下游 stale（保守策略）。

**v0.17 承接**：

- Artifact 之间的依赖关系图。
- 局部 freshness 传播：上游 artifact 变化后，仅标记真正受影响的 artifact 为 stale。
- 自动补偿/reconcile 不可逆外部副作用（如已 publish 的 package、已发送的通知）。

### 2.6 Lifecycle Hooks 增强

**v0.14 保留**：仅 Louke 内置、版本化 hooks，覆盖语义结果保存、用户决定保存、session/artifact 保存和 return-upstream 前后。

**v0.17 承接**：

- 项目自定义 hook（在安全约束下，如限制执行环境、超时、权限）。
- Hook marketplace/policy：hook 的发现、注册、审批和版本管理。

### 2.7 Baseline 高级治理

**v0.14 保留**：文件级 baseline、touch-to-clean、相对路径主索引 + blob digest 防绕过。

**v0.17 承接**：

- 复杂语义 identity：finding 的稳定 identity（不依赖行号），支持 rename/copy/split 场景。
- Owner/expiry 自动治理：baseline 条目的负责人分配、到期提醒和自动复查。
- Workspace-level 高级 debt analytics：跨文件的架构冲突、依赖漏洞、覆盖率缺口等不归入文件 baseline 的 workspace-level debt。

### 2.8 Waiver 高级治理

**v0.14 保留**：bounded waiver MVP（actor/reason/scope/revision/原始失败保留）、永不可 waive 不变量。

**v0.17 承接**：

- Waiver expiry/renew/revoke 生命周期。
- 多 waiver 冲突处理（同一检查多个 waiver、waiver 范围重叠）。
- Waiver 审计和统计报告。

### 2.9 测试与证据补齐

**v0.14 保留**：核心产品旅程所需的权威测试执行和证据。

**v0.17 承接**：

- v0.12.1 全面测试债务清理。
- 通用真实环境矩阵（多 Python 版本、多 OS）。
- 全面浏览器覆盖（Chrome/Firefox/Safari/Edge）。

---

## 3. 明确不在 v0.17 的内容

以下内容已有明确归属版本，不在 v0.17 范围内：

- 完整 Settings、Chat `/`/`!` 命令、End User Docs AI 编辑：属 **v0.15**。
- UI i18n：属 **v0.16**。

---

## 4. 约束

- 所有增强项必须基于 v0.14 的稳定生产工作流扩展，不得破坏 v0.14 已建立的 Runtime 权威、Human/AI/Program 边界和不可 waive 不变量。
- 跨 definition migration 不得破坏用户文件、Git history 和 Trace/Evidence 资产 identity。
- 项目自定义 hook 必须在安全约束下运行（限制执行环境、超时、权限），不得绕过 Runtime gate authority。

---

## 5. 分流结论

- **分流结论**：Park（Agent 建议）— 等待 v0.14 生产工作流稳定后再启动。
- **Sage peer review**：N/A（backlog Story，待 v0.14 完成后再进入正式 M-STORY 流程）
- **Human 确认**：待定

---

## 6. 可追溯种子

- **Story ID**：`STR-1701`
- **创建时间**：`2026-07-17T00:00:00+08:00`
- **来源 Story**：`STR-1401`（v0.14 Workflow Reflow）Out-of-Scope 清单
- **关联 Issue（待填充）**：`#待创建`
- **关联 Spec ID（待填充）**：`#待创建`

---

*—— 本 Story 由 Scribe 于 2026-07-17 从 STR-1401 Out-of-Scope 清单中提取创建，作为 v0.17 的 backlog 承接。待 v0.14 完成且稳定后，需重新经过正式 M-STORY 流程（包括 Sage peer review 和 Human 确认）。*
