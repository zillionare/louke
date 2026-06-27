---
name: roster
description: Agent 花名册与阶段映射
---

# Agent 花名册

按 Maestro 流程表中的角色，列出实施者与评审者。Agent 的详细 prompt 见 `agents/` 目录下同名 `.md` 文件。

| 阶段代码 | 阶段 | 实施者 | 评审者 | 一句话任务 |
|---|---|---|---|---|
| `M-FULL` | 全程 | **Maestro** (指挥) | — | 协调各 Agent，驱动流程推进，处理异常与决策上报 |
| `M-FOUND` | 项目奠基 | **Scout** (勘探) | **Warden** (守门) | Scout 勘探项目前置条件 / Warden 守门确认退出条件 |
| `M-SPEC` | 定需求 | **Sage** (贤者) | **Lex** (律者) | Sage 苏格拉底式追问产出 spec 并创建 issue / Lex 审核 spec + 验证补充 issue 并关联 Project |
| `M-TESTPLAN` | 定测试计划 | **Archer** (射手) | **Sage** | Archer 设计 test-plan（含 3 层测试、外部依赖策略）/ Sage 用 spec 上下文评审 |
| `M-ARCH` | 架构设计 | **Archer** | **Prism** | Archer 设计 architecture.md + interfaces.md / Prism 评审与 spec 一致性 |
| `M-LOCK` | 需求锁定 | **Maestro** | 人类 | 三信号齐（Sage quote_parser + Lex 阶段一/二/三）后锁定 |
| `M-DEV` | 开发执行 | **Devon** (锻造) | **Prism** → **Keeper** (守门) | Devon R-G-R（含单测）/ Prism 多视角 + 批判性审视 / Keeper gate 检查 |
| `M-E2E` | e2e 开发 | **Shield** (e2e 编写) | **Prism** → **Keeper** | Shield 按 test-plan §6 写 e2e（B 级）/ Prism review / Keeper gate |
| `M-BUGFIX` | Bug 修复 | **Devon** | **Keeper** | Devon 复用 R-G-R 修 Bug / Keeper 跑回归判断 |
| `M-SECURITY` | 安全审计 | **Judge** (S 级) | 人类 | 深度安全审计（per-milestone；DoD 可关闭） |
| `M-MILESTONE` | milestone 结束 | **Librarian** (图书管理员) | **Maestro** | Librarian 蒸馏 raw → wiki / Maestro 推进下一 milestone |

注：
- M-TESTPLAN 评审由 Sage 兼（spec 上下文不可替代；不增加 agent）
- M-ARCH 评审由 Prism 兼（本职延伸——已在 M-DEV 做"代码与 arch 一致"审视）
- M-BUGFIX 实施者由 Devon 兼（bug fix 复用 R-G-R）
- M-E2E 实施者用 B 级 agent（Shield）—— e2e 方法固定，省成本
- Shield 的"回归守护"职责已并入 Keeper gate（per-commit + per-bug-fix）
- Herald/Arbiter/Cynic/Guide/Hunter/Probe 角色已整合到现有 agent（详见 `agents/REVIEW-PAIRINGS.md` 变更历史）

## 流程对照

```
M-FOUND   ── Scout → Warden ──┐
                              │
M-SPEC    ── Sage → Lex ──────┤  ← Sage 苏格拉底式追问产出 spec + 创 issue
                              │     Lex 审核 spec + 验证 issue + 关联 Project
M-TESTPLAN ── Archer → Sage ──┤  ← Archer 写 test-plan，Sage 用 spec 上下文审
                              │
M-ARCH    ── Archer → Prism ──┤  ← Archer 写 architecture + interfaces
                              │     Prism 评审与 spec 一致性
M-LOCK    ── Maestro ─────────┤  ← 3 信号齐（Maestro 自检）后锁定
                              │
M-DEV     ── Devon → Prism → Keeper ──┤  ← Devon R-G-R（含单测）
                              │            Prism 多视角 + 反模式 + 安全 quick scan
                              │            Keeper gate（tests + lint + commit）
M-E2E     ── Shield → Prism → Keeper ─┤  ← Shield 写 e2e（B 级）
                              │              Prism review
                              │              Keeper gate
M-BUGFIX  ── Devon → Keeper ─────────┤  ← Devon 复用 R-G-R 修 Bug
                              │            Keeper 跑回归判断
M-SECURITY ── Judge (S 级) → 用户 ──┤  ← S 级深度安全审计（per-milestone）
                              │            用户最终批准
M-MILESTONE ── Librarian → Maestro ──┘  ← Librarian 蒸馏 raw → wiki
```

## 命名由来

| Agent | 含义 | 职责联想 |
|-------|------|---------|
| Maestro | 指挥家 | 协调整支乐队 |
| Scout | 勘探者 | 探路、确认前置条件 |
| Warden | 看守人 | 守门、确认退出条件 |
| Sage | 贤者 | 苏格拉底式追问 |
| Lex | 律法 | 审核法律级精确性 + 组织 issue |
| Archer | 射手/架构师 | 设计执行路径（test-plan + architecture） |
| Devon | 锻造者 | 从测试的烈火中锻造代码（R-G-R） |
| Prism | 棱镜 | 多角度审视代码质量（含测试 + 安全 quick scan） |
| Judge | 裁判 | S 级深度安全审计 |
| Shield | e2e 编写 | 写端到端测试脚本（B 级） |
| Keeper | 守护者 | 守住质量门禁（gate + 回归判断） |
| Librarian | 图书管理员 | 整合 Wiki，维护项目记忆 |