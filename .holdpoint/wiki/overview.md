# 项目概览
> 最后更新: 2026-05-31

specforge 是一套 TDD-first 多 Agent 协作开发方法。当前有 6 个 wiki 页面，涵盖 1 个决策、5 条经验。最近的变更包括：LLM-Wiki 架构升级（entries → pages + frontmatter + wikilink）、Lex-Clerk-Auditor 合并、分支命名约定确立。

## 架构决策
- **双仓库分离**: 开源代码 (`project`) + 机密文档 (`project-spec`)。来源: [[first-conversation]]
- **讨论界面**: GitHub PR Review on Markdown Files（替代飞书）。来源: [[first-conversation]]
- **PR 行级评论**: Sage 和 Lex 通过 `gh api` 留行级 inline comment，Lex 通过 `gh api .../reviews` 提交 Approve/Request changes。来源: [[branch-naming-convention]]
- **分支命名约定**: `spec/{spec-id}` / `feat/{spec-id}/{task-id}` / `fix/{issue-number}`（Scout 不需要专属分支）。来源: [[branch-naming-convention]]
- **Agent 合并**: Clerk+Auditor 合并入 Lex。Lex 职责扩展为：spec 审核 + issue 验证补充 + 关联 Project。来源: [[agent-merge-lex-clerk]]
- **Wiki 系统**: 纯 Markdown + LLM-Wiki 三层架构（.specforge/raw/sources + .specforge/wiki/pages + index/overview/log），零外部依赖。来源: [[first-conversation]]
- **安装方式**: Shell 脚本 `curl | bash`。来源: [[sage-interview]]

## 流程经验
- **任务粒度判断**: 共享相同 R-G-R 模式的任务应合并, 不因文件不同而拆分。来源: [[archer-cynic]]
- **Cynic 阻塞策略**: Cynic 的批评有价值, 但 Maestro 有权驳回。来源: [[archer-cynic]]
- **Issue 分组策略**: 按功能模块而非 FR 一对一创建 issue, 降低管理成本。来源: [[clerk-auditor]]
- **Lex 审核策略**: 验收标准必须可断言, "去重""严格"等词汇需具体化。来源: [[sage-interview]]

## 已知问题
- **GitHub Projects**: token 无权创建 Project。需账户管理员配置。来源: [[clerk-auditor]]
- **GitHub Labels**: repo Labels API 404, 需 Settings > Issues > Labels 启用。来源: [[clerk-auditor]]
- **shellcheck**: 未安装, install.sh 和 bin/specforge 未经自动 lint。来源: [[herald-arbiter]]
- **FR-009 自动触发**: Librarian 自动触发仅在 prompt 中定义, 实际执行需 Maestro/外部监控。来源: [[herald-arbiter]]
