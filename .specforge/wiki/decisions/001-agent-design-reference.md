# ADR 001 — Agent 设计参考文档

- **日期**: 2026-05-23
- **状态**: 已采纳

## 背景

当前所有 Agent prompt 是基于飞书文档 [specforge 开发流程](https://qcnj2a4uoe9q.feishu.cn/wiki/FBNqwXG27iVnemkJN34cRNdvnOh) 设计的。该文档定义了下述流程结构：

```
Story/PRD → Interview → Issue Tracker → Test Plan → 
执行规划 → 任务执行(R-G-R) → 验收
Bug 修复(R-G-R) 独立流程
```

每个阶段有实施者(implementer) + 评审者(reviewer) 的双人模式。

## 决策

- Agent 的设计遵循此飞书文档的结构，但在自举过程中逐步增强了以下能力：
  1. Wiki 系统（LLM 可读写 Markdown 文件）
  2. Librarian consolidation
  3. Guide 指导 Agent
  4. 会话自动保存
- 飞书文档是权威源，但其内容本文档的 wiki/consolidated.md 应以引用而非拷贝方式记录。

## 后果

- 当飞书文档不可访问时，Agent 理解流程的能力依赖 wiki/consolidated.md 中的摘要
- 需要定期将飞书文档更新的内容同步到 wiki
