# Agent Review Pairings

本文档定义 specforge 中各 Agent 的评审配对关系。Maestro 阶段推进的"评审"步骤按此执行。

## 配对表

| 实施者 | 评审者 | 评审对象 | 触发 |
| --- | --- | --- | --- |
| Scout | Warden | 项目奠基（基础设施是否就绪） | Scout Step 6 完成后 |
| Sage | Lex | spec.md / acceptance.md / GitHub issue 覆盖 | spec 锁定 + Sage Step 5 完成 |
| **Archer 阶段一** | **Sage** | **test-plan.md** | **Archer 阶段一产出后** |
| **Archer 阶段二** | **Judge** | **architecture.md + interfaces.md** | **Archer 阶段二产出后** |
| Devon | Prism → Keeper | 代码改动（多视角 + 完成门禁） | 每次 push + 任务完成 |
| Hunter | Shield | Bug 修复的回归守护 | fix 完成 |
| Librarian | （无） | wiki 健康维护 | 自身 |

注: Sage 的"test-plan 评审"是 spec 阶段交付后承担的一项**额外职责**（Sage 在 Lex 通过后、Archer 启动前的窗口空闲），不参与 Sage 主流程的 5 步计数。

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

**为什么是 Sage，不是 Judge**:
- Sage 刚写完 spec，FR/NFR 编号、最新状态一清二楚
- Sage 知道 quote dialogue 的隐忧历史
- Judge 不知道 spec 内部上下文，需读 spec 补课
- Sage 此时正好空闲（Lex 验证已通过、Archer 启动前的窗口）

### Archer 阶段二 → Judge（architecture + interfaces 评审）

**Judge 的额外职责**（test-plan 通过后承担）:
- 评审范围：`.quanti-forge/project/specs/{spec-id}/architecture.md` + `interfaces.md`
- 核心检查项（详见 `agents/Judge.md`）:
  - 架构 4 项：模块边界、依赖无环、trade-off、技术选型
  - 接口 4 项：硬规则（仅外部可观测）、不含内部细节、每出口清晰、不规定实现
  - 三方闭合：interfaces ↔ test-plan ↔ spec
  - 与 test-plan 的一致性
- 退出条件：12 项检查项全部满足 + 阻塞项 ≤ 0

**为什么是 Judge，不是 Sage**:
- Judge 的核心知识是"测试 + 测试可观测性"
- interfaces.md 是"开发-测试契约"，是 Judge 的领域
- architecture.md 的 trade-off 评估需要技术广度
- Sage 在阶段一已经审查过 test-plan，应保持独立避免 bias

**为什么不合并到 Sage 一个人**:
- 阶段一（test-plan）和阶段二（arch + interfaces）领域差别大
- Sage 阶段一已经利用了 spec 上下文优势
- 阶段二更需 testing/contract 知识，Judge 更合适
- 单评审者模式会牺牲其中一边的质量

## 配对原则

1. **领域契合** — 评审者必须对该领域有专业判断（不是"找空闲的人来审"）
2. **负载均衡** — 不应让单个 agent 同时承担多领域评审
3. **creator/checker 分离** — 实施者与评审者必须是不同 agent（禁止自审）
4. **可执行** — 评审者的 prompt 必须明确写出"评审 XX 文档"的任务定义
5. **时机契合** — 评审者最好在承担评审时是空闲状态（避免与本职冲突）

## 变更历史

- **v0.6 (2026-06-27)** — 确立 Archer 两阶段配对: Sage 阶段一（test-plan） + Judge 阶段二（architecture + interfaces）
  - 修正: 初版决定是"Judge 全包"，后分析认为 Sage 阶段一（test-plan 评审）有不可替代的 spec 上下文优势
