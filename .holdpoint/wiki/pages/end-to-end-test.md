---
type: experience
title: 端到端实战测试 v0.4
date: 2026-06-15
agents: [Scout, Warden]
sources: [2026-06-15-end-to-end-test]
related: [[scout-v0.1]]
---

## 讨论摘要

用 spec 004-quote-dialogue 已有的 story.md 走完整 Scout → Warden 流程，验证 foundation 重构 + agent-as-collaborator 模型。

## 关键结论

- F1-F11 foundation 验收一键通过
- quantclaws (gh) 作为 zillionare repo 的 collaborator 完成了全流程
- F2 历史 bug（dict vs list）被修复
- F10 加了"豁免当前 release"逻辑
- 新工具 `specforge invite-owner` 调 GraphQL `updateProjectV2Collaborators`

## 实战中暴露的问题

- F5 PR 初次失败：releases 分支无 commits 时 gh 拒绝创建 PR
- Fine-grained PAT 缺 project 权限，checkup L6 未拦截
- bash 双引号内 `\{` 不转义导致 GraphQL 语法错误

## 已决策

- [x] framework 改进（agent-as-collaborator）commit 到 main
- [x] release 分支合入 main framework 才能让 Warden 在 release 上跑通
- [x] v0.4 实战测试通过验收
