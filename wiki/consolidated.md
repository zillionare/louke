# specforge — 项目知识库
> 最后整合时间: 2026-05-23

## 项目概览
specforge 是一套 TDD-first 多 Agent 协作开发方法论。核心原则是先写测试（Red），再写实现（Green），最后重构（Refactor），每个阶段由实施者执行、评审者把关，Maestro 统一协调。项目通过自举（自己用自己）验证方法论可行性。

## 架构决策
- **双仓库分离**: 开源代码 (`project`) + 机密文档 (`project-spec`)。来源: first-conversation
- **讨论界面**: GitHub PR Review on Markdown Files（替代飞书）。HedgeDoc 无 Inline Comment，Outline 太重。来源: first-conversation
- **PR 行级评论**: Sage 和 Lex 通过 `gh api repos/{owner}/{repo}/pulls/{pr-number}/comments` 留行级 inline comment，Lex 通过 `gh api .../reviews` 提交 Approve/Request changes。来源: branch-naming-convention
- **分支命名约定**: `spec/{spec-id}` / `feat/{spec-id}/{task-id}` / `fix/{issue-number}`（Scout 不需要专属分支，直接在默认分支工作）。来源: branch-naming-convention
- **Agent 合并**: Clerk+Auditor 合并入 Lex。两者都是规则驱动的结构化验证，不需要深度推理。Lex 职责扩展为：spec 审核 + issue 验证补充 + 关联 Project。来源: lex-clerk-merge
- **Wiki 系统**: 纯 Markdown 文件 + Librarian LLM 整合（Karpathy 风格）, 零外部依赖。来源: first-conversation
- **安装方式**: Shell 脚本 `curl | bash`。来源: sage-interview
- **Agent 设计参考**: 以飞书文档 [specforge 开发流程](https://qcnj2a4uoe9q.feishu.cn/wiki/FBNqwXG27iVnemkJN34cRNdvnOh) 为数据源。来源: 001-agent-design-reference

## V1 功能与规格
- **V1 范围**: Guide Agent, Librarian Agent, 8 个输出模板, `specforge init` 工具。来源: sage-interview
- **验收标准**: 自举成功 — specforge 用自身 7 阶段流程完成了 v1 开发。来源: sage-interview, herald-arbiter
- **模板策略**: 严格模板 — Agent 输出必须包含模板中所有一级标题，缺失为不通过。来源: sage-interview
- **Librarian 触发**: 手动 + 自动（`wiki/entries/` ≥ 5 条）。来源: sage-interview
- **会话保存**: Agent 返回结果前自动写入 `wiki/entries/YYYY-MM-DD-{主题}.md`。来源: sage-interview

## V1 执行记录
- **Stages 完成**: 7/7 (Story/PRD → Interview → Issue Tracker → Test Plan → 执行规划 → 任务执行 → 验收) 全部通过。来源: 全部条目
- **GitHub Issues**: #2~#6 覆盖 12 个 FR, 可按验收报告关闭。来源: clerk-auditor, herald-arbiter
- **任务执行**: 8 个任务, 4 个已就绪 (Guide/Librarian/模板/ROSTER), 4 个新实现 (install.sh/init/onboarding/会话保存)。来源: archer-cynic
- **测试结果**: 19/20 shell 测试通过, 5 个 LLM 依赖测试跳过 (需宿主工具介入)。来源: herald-arbiter

## 流程经验
- **任务粒度判断**: 共享相同 R-G-R 模式的任务应合并, 不因文件不同而拆分。来源: archer-cynic
- **Cynic 阻塞策略**: Cynic 的批评有价值, 但 Maestro 有权驳回（如 IT-004 阻塞）。来源: archer-cynic
- **Issue 分组策略**: 按功能模块而非 FR 一对一创建 issue, 降低管理成本。来源: clerk-auditor
- **Lex 审核策略**: 验收标准必须可断言, "去重""严格"等词汇需具体化。来源: sage-interview

## 已知问题
- **GitHub Projects**: token `quantclaws` 无权为 `zillionare` 创建 Project。需账户管理员配置。来源: clerk-auditor
- **GitHub Labels**: repo Labels API 404, 需 Settings > Issues > Labels 启用。来源: clerk-auditor
- **shellcheck**: 未安装, install.sh 和 bin/specforge 未经自动 lint。来源: herald-arbiter
- **FR-009 自动触发**: Librarian 自动触发仅在 prompt 中定义, 实际执行需 Maestro/外部监控。来源: herald-arbiter
