# Agent 花名册

每个阶段有专门的实施者与评审者，由 Maestro 统一协调。
Agent 的详细 prompt 见 `agents/` 目录下同名 `.md` 文件。

| 阶段 | 实施者 | 评审者 | 一句话任务 |
|------|--------|--------|-----------|
| 全程 | **Maestro** (指挥) | | 协调各 Agent，驱动流程推进，处理异常与决策上报 |
| Story/PRD | **Scout** (勘探) | **Warden** (守门) | Scout 勘探项目前置条件 / Warden 守门确认退出条件 |
| Interview | **Sage** (贤者) | **Lex** (律者) | Sage 苏格拉底式追问产出 spec / Lex 审核需求可追踪可断言 |
| Issue Tracker | **Clerk** (书记) | **Auditor** (审计) | Clerk 将 spec 拆为 GitHub issue / Auditor 审计可追溯性 |
| Test Plan | **Probe** (探针) | **Judge** (裁判) | Probe 设计分层测试计划 / Judge 裁判测试方案可执行性 |
| 执行规划 | **Archer** (架构) | **Cynic** (批评) | Archer 设计任务划分与测试关联 / Cynic 批评审核完整性 |
| 任务执行 | **Forge** (锻造) | **Prism** (棱镜) → **Keeper** (守门) | Forge 按 R-G-R 循环锻造代码 / Prism 多角度 Code Review / Keeper 守住完成门禁 |
| 验收 | **Herald** (传令) | **Arbiter** (终审) | Herald 汇总全量测试与覆盖 / Arbiter 终审裁决 |
| Bug 修复 | **Hunter** (猎手) | **Shield** (盾牌) | Hunter TDD 猎杀 Bug / Shield 守护无回归 |

## 流程对照

```
Story/PRD ── Scout → Warden ──┐
                                │
Interview ── Sage → Lex ───────┤
                                │
Issue Tracker ── Clerk → Auditor┤
                                │
Test Plan ── Probe → Judge ───┤
                                │
执行规划 ── Archer → Cynic ───┤
                                │
任务执行 ── Forge → Prism → Keeper ─┤  ← Red-Green-Refactor 循环
                                │
验收 ── Herald → Arbiter ─────┘

Bug 修复 ── Hunter → Shield (独立流程，同样 R-G-R)
```

## 命名由来

| Agent | 含义 | 职责联想 |
|-------|------|---------|
| Maestro | 指挥家 | 协调整支乐队 |
| Scout | 勘探者 | 探路、确认前置条件 |
| Warden | 看守人 | 守门、确认退出条件 |
| Sage | 贤者 | 苏格拉底式追问 |
| Lex | 律法 | 审核法律级精确性 |
| Clerk | 书记 | 组织、归档、编号 |
| Auditor | 审计员 | 交叉验证、追踪 |
| Probe | 探针 | 为每个需求设计测试探针 |
| Judge | 裁判 | 裁决测试方案是否可执行 |
| Archer | 射手/架构师 | 设计执行路径 |
| Cynic | 愤世嫉俗者 | 批评性审核 |
| Forge | 锻造 | 从测试的烈火中锻造代码 |
| Prism | 棱镜 | 多角度审视代码质量 |
| Keeper | 守护者 | 守住质量门禁 |
| Herald | 传令官 | 传达验收结果 |
| Arbiter | 仲裁者 | 终审裁决 |
| Hunter | 猎手 | 精确猎杀 Bug |
| Shield | 盾牌 | 守护无回归 |