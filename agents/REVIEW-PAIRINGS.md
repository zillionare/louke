# Agent Review Pairings

本文档定义 specforge 中各 Agent 的评审配对关系。Maestro 阶段推进的"评审"步骤按此执行。

## 配对表

| 实施者 | 评审者 | 评审对象 | 触发 |
| --- | --- | --- | --- |
| Scout | Warden | 项目奠基（基础设施是否就绪） | Scout Step 6 完成后 |
| Sage | Lex | spec.md / acceptance.md / GitHub issue 覆盖 | spec 锁定 + Sage Step 5 完成 |
| **Archer 阶段一** | **Sage** | **test-plan.md** | **Archer 阶段一产出后** |
| **Archer 阶段二** | **Prism** | **architecture.md + interfaces.md** | **Archer 阶段二产出后** |
| Devon | Prism → Keeper | 代码改动（多视角 + 完成门禁） | 每次 push + 任务完成 |
| Shield | Keeper | Bug 修复的回归守护（合并到 Keeper gate） | fix 完成 |
| Judge (S 级) | 用户 | 安全审计 | per-milestone（DoD 中可关闭） |
| Librarian | （无） | wiki 健康维护 | 自身 |

注: Sage 只承担 M-TESTPLAN 评审（spec 上下文不可替代）。M-ARCH 评审由 Prism 承担（质疑代码与 spec/arch 的一致性，是其本职的延伸）。

## 详细配对

### Archer 阶段一 → Sage（test-plan 评审）

**Sage 的额外职责**（spec 阶段交付后空闲期承担）:
- 评审范围：`.quanti-forge/project/specs/{spec-id}/test-plan.md`
- 核心检查项（详见 `agents/Sage.md` 的"Archer 阶段一评审"段）:
  - **AC 引用闭合**（每个 AC ≥1 测试，每个测试 ≥1 AC）
  - **状态字段感知**（标了 ⚠️ 的 FR 必须有测试空间）
  - **隐忧继承**（quote dialogue 中用户表达过的顾虑）
  - **spec 一致性**（test-plan 不能与 spec 矛盾）
- 反馈方式：复用 FR-0022 quote dialogue 协议
- 退出条件：4 项检查项全部满足 + 阻塞项 ≤ 0

### Archer 阶段二 → Prism（architecture + interfaces 评审）

**Prism 的额外职责**（test-plan 通过后承担）:
- 评审范围：`.quanti-forge/project/specs/{spec-id}/architecture.md` + `interfaces.md`
- 核心检查项（详见 `agents/Prism.md` 的"职责边界"段）:
  - **架构与 spec 一致性**（质疑模块边界、依赖关系、关键 trade-off 是否与 spec 对齐）
  - **interfaces 闭合 test-plan**（interfaces 定义的每个外部出口在 test-plan 中有对应测试）
  - **interfaces 闭合 spec**（spec 要求的状态在 interfaces 中有对应可观测出口）
  - **interfaces 不含内部实现**（无内部类/调度/中间数据/私有字段；不规定实现选型）
- 反馈方式：复用 FR-0022 quote dialogue 协议
- 退出条件：4 项检查项全部满足 + 阻塞项 ≤ 0

**为什么是 Prism，不是 Sage**:
- Prism 已在 M-DEV 阶段做"代码与 arch 是否一致"的批判性审视（本职延伸）
- Sage 提示词已长（主流程 5 步 + M-TESTPLAN 评审），加 M-ARCH 易出错
- 不增加 agent 数量

**为什么不是 Judge**:
- Judge 已转为 S 级安全审计者（M-SECURITY），不再做 arch/interfaces 评审

### M-SECURITY → 用户（安全审计终审）

**Judge (S 级) 的额外职责**（per-milestone 触发）:
- 评审范围：`git diff <last-tag>..releases/{version}` 全量代码变更
- 核心检查项（详见 `agents/Judge.md` + `templates/security-checklist.md`）:
  - 输入验证 / 认证 / 数据保护 / 错误处理 / 依赖 / 日志 / 业务逻辑
  - 语义层漏洞（CI 静态扫描抓不到的部分）
- 反馈方式：审计报告（critical/high/medium/low + 修复建议）
- 退出条件：无 critical/high 漏洞 → 通过；否则拒绝，milestone 标记为 blocked
- **触发条件**: 每个 milestone 结束前（M-SECURITY 阶段，在 M-MILESTONE 之前）
- **可禁用**: 内部项目可在 Scout DoD 中关闭 M-SECURITY（详见 Scout Step 1）

**为什么 Judge 是 S 级**:
- 安全漏洞识别需要深度推理（攻击向量、上下文边界、隐式信任链）
- CI 静态扫描只能抓 pattern matching（约 30%）；语义层漏洞需要 S 级 agent
- S 级慢/贵，但安全 bug 代价远超审阅成本

**为什么不是 Prism**:
- Prism 做代码 review（多角度 + 批判性 + 测试反模式）
- Prism 浅扫安全 pattern（§6 quick scan）但不做深度审计
- 深度安全审计需要专门 agent（Judge），不能与代码 review 合并

### Devon → Prism → Keeper（代码 + 测试 + gate）

**Prism**:
- 范围：生产代码 + 单元测试 + e2e 测试
- 维度（6 个）：可读性 / 设计模式 / DRY / 变更影响 / 测试代码反模式 / **安全 quick scan**（§6）
- 批判性视角（Prism 内置的 cynical 视角——质疑设计假设、寻找被掩盖的缺陷）

**Keeper**:
- 范围：per-commit gate（R-G-R + tests pass + lint + commit 格式）+ **回归判断**（合并 Shield 的判断部分）
- 触发：每次 push + 任务完成 + bug fix 完成

## 配对原则

1. **领域契合** — 评审者必须对该领域有专业判断（不是"找空闲的人来审"）
2. **负载均衡** — 不应让单个 agent 同时承担多领域评审
3. **creator/checker 分离** — 实施者与评审者必须是不同 agent（禁止自审）
4. **可执行** — 评审者的 prompt 必须明确写出"评审 XX 文档"的任务定义
5. **时机契合** — 评审者最好在承担评审时是空闲状态（避免与本职冲突）
6. **安全例外** — 安全审计用 S 级智能体，是例外（不能由其他 reviewer 兼任）

## 变更历史

- **v0.6 (2026-06-28)** — 确立 Archer 两阶段配对: Sage 阶段一（test-plan）+ Prism 阶段二（arch + interfaces）
  - 修正: 初版决定是"Judge 全包"，后分析认为 Sage 阶段一（test-plan 评审）有不可替代的 spec 上下文优势
  - 修正: Archer 阶段二评审者从 Judge 改为 Sage，再改为 Prism（Sage 负载过重；Prism 评审与本职延伸自然衔接）
  - 修正: Judge 从 arch/interfaces 评审者改为 S 级安全审计者（M-SECURITY 阶段）
- **v0.5 (2026-06-26)** — Forge→Devon 重命名；Shield 的回归判断合并到 Keeper；e2e 编写归 Shield（B 级）