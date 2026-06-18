i# specforge — PRD

## 背景
AI coding agent 生态已成熟（Claude Code、Codex、Kilo 等），但缺乏一套结构化的、TDD-first 的多 Agent 协作开发方法论。现有方案要么是单 Agent 自主开发（OpenHands），要么是有协作但无 TDD 纪律（MetaGPT、CrewAI），要么只有规范驱动但无多角色评审（spec-kit）。

specforge 填补空白：以 TDD Red-Green-Refactor 为核心，以双人评审（实施者+评审者）为质量门禁，以国内模型适配为实际考量。

## 目标
让 specforge v1 达到 **自举成功**：specforge 自身通过自身的 TDD 流程完成功能开发，证明方法论可行。

## 验收标准（V1）
- [ ] specforge 使用自身的 8 阶段流程完成了 specforge v1 的开发
- [ ] 所有代码提交遵循 R-G-R 循环（Red test → Green impl → Refactor）
- [ ] Guide Agent 可回答方法论问题
- [ ] Librarian Agent 可整合 Wiki 条目为 consolidated.md
- [ ] `specforge init` 可一键初始化新项目目录结构
- [ ] 新用户执行 init 后能通过终端指引文本自行开始第一个需求会话

## 非目标（Out of Scope）
- CLI 自动化编排（Maestro 自动调度各 Agent）
- 模型评测/benchmark 工具
- CI/CD 整合模板
- Agent 数量精简（19→12）
- 流程裁剪（跳过可选阶段）

## 风险
- **Agent 依赖的宿主工具不是 specforge 控制的** — 方法论的 agent prompt 能否在不同工具（Claude Code/Kilo/Codex）中表现一致？
- **自举是鸡生蛋问题** — 第一个 Agent 调用需要外部手动触发
- **模型可用性** — 国内模型 API 稳定性、速率限制

## 关联
- Spec ID: SPEC-V1-001
- Plan: `.kilo/plans/1779502769488-kind-lagoon.md`
