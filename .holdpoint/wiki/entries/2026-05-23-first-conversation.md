# 首次对话：specforge 项目初始化与竞争分析

- **日期**: 2026-05-23
- **参与者**: User
- **阶段**: Story/PRD（前置准备）

## 讨论摘要

用户描述了 specforge 项目的核心目标：一个基于 TDD 的多 Agent 协作开发方法。核心亮点包括 GitHub issue 跟踪、GitHub Projects 管理发布、代码与需求关联、国内模型推荐。

用户要求进行竞争分析，找出 5 个著名的 alternative 进行交叉比对。后续对话中，用户明确了：

1. 现阶段做成手动调用模式，不搞自动化编排
2. 需要 Guide Agent 回答使用方法论的问题
3. 需要模板化产出（借鉴 spec-kit）
4. 需要 LLM Wiki + 自动 Consolidation（Karpathy 风格）
5. 需要一个 Markdown 讨论界面替代飞书

## 关键结论

- **5 个 alternatives 已识别**：github/spec-kit (105k★)、OpenHands (74.5k★)、MetaGPT (68.2k★)、CrewAI (52k★)、PR-Agent (11.3k★)
- specforge 的独特价值在于 TDD-first + 双人评审 + 国内模型适配
- **讨论界面选型**：HedgeDoc 不满足（无 Inline Comment），最终选择 GitHub PR Review on Markdown Files
- **仓库策略**：采用双仓库分离（公开 code repo + 私有 spec repo）
- **自举原则**：specforge 必须用自身方法论来开发自身

## 已决策

- [x] 使用 GitHub PR Review on Markdown Files 替代飞书进行文档讨论
- [x] 纯 Markdown 文件做 Wiki（零外部依赖）
- [x] 不做 CLI 自动化编排，现阶段手动调用
- [x] specforge 自身 repo 公开（方法论本身），项目文档放入私有 companion repo

## 待决策

- [ ] specforge v1 的具体功能边界（待 Scout/Sage 澄清）
- [ ] Agent 数量是否精简（19→12），待实践反馈
