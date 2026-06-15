# 端到端实战测试：Scout → Warden v0.4

- **日期**: 2026-06-15
- **参与者**: User, Scout, Warden
- **阶段**: Story/PRD（实战演练）

## 讨论摘要

用 spec 004-quote-dialogue 现有的 `story.md` 跑了一次 Scout → Warden 端到端实战，验证刚合并的 Scout/Warden foundation 重构 + agent-as-collaborator 模型。

实测路径：Story（已存在）→ 收集信息 → 切到 `releases/v0.4` 分支 → 创建 Test Issue #50 / Test PR #51 → 写 project-info v0.4 段 → 跑 `specforge foundation` 11 项 → F2 因 project owner 错位先失败 → 加 `specforge invite-owner` 子命令 + L6 检测 + F2 双 owner 查找 + F10 豁免当前 release → 全部通过。

## 关键结论

- **Scout/Warden foundation 重构工作正常**——F1-F11 全部可通过 `specforge foundation` 一键验收
- **agent-as-collaborator 模型已落地**——quantclaws (gh) 不是 zillionare (repo owner)，但能完成全流程
- **F2 长存 bug 已修**——`gh project list --format json` 返回 `{"projects": [...]}` 是 dict 不是 list，老代码 fall through 到 "未找到"
- **F10 设计缺陷已修**——当前工作的 release 分支不应被自身 orphan 检查打到自己
- **`specforge invite-owner` 是新工具**——自动调 GitHub GraphQL `updateProjectV2Collaborators(role: READER)` API

## 实战中暴露的问题

- **F5 PR 初次失败**：`releases/v0.4` 刚切出来没有 commits，gh pr create 报 "No commits between main and releases/v0.4"。Scout.md Step 5 需加一条"如果 PR 失败因分支无 commits，先 commit 一个 placeholder"
- **Fine-grained PAT 找不到 Account-level Projects 权限**：GitHub 2025+ 取消了 fine-grained PAT 的 Projects 权限，需走 classic PAT。**checkup L6 没有拦截这个**
- **bash 双引号内 `\{` 不会被转义**——`specforge invite-owner` 第一次跑 `gh api graphql` 报 GraphQL syntax error。最终改为不加反斜杠
- **`SPECFORGE_HOME` 没设时 bin/specforge 走 `~/.specforge/`**——开发时必须显式设环境变量

## 已决策

- [x] framework 改进（agent-as-collaborator）commit 到 main
- [x] release 分支合入 main framework 才能让 Warden 在 release 上跑通（merge commit `4736608`）
- [x] v0.4 实战测试通过验收

## 待决策

- [ ] Scout.md Step 5 是否补"PR placeholder commit"指令
- [ ] checkup L6 是否加 fine-grained PAT 缺 project 权限的检测
- [ ] 是否写 ADR 记录 agent-as-collaborator 架构决策
- [ ] 实战产生的 Test Issue #50 / Test PR #51 是否清理（已在 specforge 自己的 issue/PR 列表里）
- [ ] 实战产生的 `.scout-test-pr-placeholder` 文件是否要保留（已 commit 在 release 分支）
