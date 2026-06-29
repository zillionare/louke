# 011 — Agent 评审配对演化（v0.5–v0.6）

- **状态**: 历史档案
- **日期**: 2026-06-28
- **影响**: REVIEW-PAIRINGS.md 删除，相关配对信息已下沉到各 agent 的 .md 文件

## v0.5 (2026-06-26)

- Forge → **Devon** 重命名（原 Forge 用 R-G-R，重命名后保留 R-G-R 工作流）
- **Shield** 的"回归守护"职责合并到 **Keeper** gate（per-commit + per-bug-fix 触发）
- e2e 编写归 **Shield**（B 级 agent，e2e 方法固定，省成本）

## v0.6 (2026-06-28)

- 确立 **Archer 两阶段**配对：
  - 阶段一（test-plan） → **Sage** 评审（spec 上下文优势不可替代）
  - 阶段二（architecture + interfaces） → **Prism** 评审
- Judge 角色从 arch/interfaces 评审者转为 **S 级安全审计者**（M-SECURITY 阶段）
- M-E2E 评审结构与 M-DEV 保持一致：Prism 多视角 + Keeper gate
- Sage 不再承担 M-ARCH 评审（其提示词已承载主流程 + M-TESTPLAN 评审，再加 M-ARCH 容易出错）

## 文件迁移

这些规则原来集中在 `agents/REVIEW-PAIRINGS.md`（含"name: review-pairings"前置元 matter，被工具误识为 Agent）。v0.6 末清理后：

- 配对表 → 已下沉到 `agents/Maestro.md` 的"流程阶段与 Agent 映射"表
- 各 agent 的具体评审职责 → 已下沉到各 agent 自己的 `.md`（例如 Archer 阶段一评审 → Sage 的额外职责详见 `agents/Sage.md` L323 起；M-ARCH 评审 → Prism 的本职延伸详见 `agents/Prism.md` L14）
- 变更历史 → 本文件
