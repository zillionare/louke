---
type: experience
title: Clerk → Auditor — Issue 拆分与审计
date: 2026-05-23
agents: [Clerk, Auditor]
sources: [clerk-auditor]
related: [[sage-interview]], [[herald-arbiter]]
---

## 讨论摘要

Clerk 将 spec 中的 12 个 FR 按功能分组为 5 个 GitHub issue，提交到 zillionare/specforge 仓库。Auditor 交叉验证覆盖完整，Auditor 通过。

## 关键结论

- 5 个 issue 已创建：#2(specforge init), #3(Guide), #4(Librarian), #5(会话保存), #6(模板)
- 12 个 FR 全部覆盖，ID 标注与 spec 一致
- 2 项非阻塞提示：未配置 GitHub Project 关联、Feature 标签未创建（repo Settings 问题）

## 已决策

- [x] Issue 分组策略：按功能模块（CLI + Guide + Librarian + 会话 + 模板）各一个，而非按 FR 一一对应
- [x] NFR 不单独建 issue，各 Issue 验收时一并检查
- [x] Auditor 审核通过
