# specforge v1 — Spec

- **Spec ID**: SPEC-V1-001
- **创建日期**: 2026-05-23
- **状态**: 已确认

## 用户故事

| ID | 故事 | 验收条件 | 优先级 |
|----|------|---------|--------|
| US-001 | 作为新用户，我想通过一条命令初始化 specforge 项目，以便快速开始 | 执行 `specforge init my-project` 后，目录结构被创建，终端打印下一步指引 | P0 |
| US-002 | 作为新用户，我想询问 Guide Agent 来了解如何使用 specforge | 调用 Guide 后，能正确回答至少 5 类常见问题（阶段顺序、Agent 职责、模型选择、模板用法、跳过规则） | P0 |
| US-003 | 作为开发者，我想在每次 Agent 对话后自动保存关键结论到 Wiki | Agent 完成对话后，`wiki/entries/` 下出现新条目文件，包含日期、参与者、结论 | P0 |
| US-004 | 作为项目成员，我想通过 Librarian 整合分散的 Wiki 条目为统一知识库 | 调用 Librarian 后，`wiki/consolidated.md` 被更新为所有条目的去重合并版本 | P1 |
| US-005 | 作为开发者，我想用标准模板填写各阶段的产出物 | 每个阶段有对应的 `.md` 模板，Agent 输出严格遵循模板格式 | P0 |

## 功能需求

| ID | 需求 | 可测试性 |
|----|------|----------|
| FR-001 | `specforge init <name>` 命令创建指定名称的项目目录 | ✅ |
| FR-002 | init 创建的目录包含 `agents/`（21 个 Agent prompt）、`templates/`（8 个模板）、`wiki/entries/`、`wiki/decisions/`、`specs/` | ✅ |
| FR-003 | init 完成后终端打印指引文本，内容包括：推荐的第一步（调用 Scout/Guide）、推荐模型、模板目录说明 | ✅ |
| FR-004 | Guide Agent 的知识范围覆盖 ROSTER.md、README.md、templates/ 目录 | ✅ |
| FR-005 | Guide Agent 引用具体文档路径作答，不编造信息 | ✅ |
| FR-006 | Librarian Agent 读取 `wiki/entries/` 和 `wiki/decisions/`，生成 `wiki/consolidated.md` | ✅ |
| FR-007 | Librarian consolidation 规则：(a) 两个条目描述同一决策且结论一致 → 合并为一条，保留最新日期；(b) 结论矛盾 → 保留最新一条并标注冲突；(c) 条目提到"已过时""不再适用"等明确废弃信号 → 在 consolidated 中标注 `[已过时]` | ✅ |
| FR-008 | Librarian 不删除、不修改原始条目文件 | ✅ |
| FR-009 | Librarian 支持手动触发（用户命令）和自动触发（wiki/entries/ 下文件数 ≥ 5 时） | ✅ |
| FR-010 | 开发流程 Agent（Scout~Shield）在返回最终结果前，将以下内容写入 `wiki/entries/YYYY-MM-DD-{主题}.md`：(a) 讨论主题 (b) 参与者 (c) ≥1 条关键结论 (d) 待决策事项 | ✅ |
| FR-011 | 8 个模板文件覆盖 7 个 Feature 阶段 + 1 个 Bug 修复阶段：prd.md, spec.md, issues.md, test-plan.md, task-plan.md, task-log.md, acceptance.md, bug-fix.md | ✅ |
| FR-012 | Agent 输出文件必须包含对应模板中所有一级标题（`##` 开头），缺失任一标题为不通过 | ✅ |

## 非功能需求

| ID | 需求 | 指标 |
|----|------|------|
| NFR-001 | `specforge init` 在 macOS/Linux 上 3 秒内执行完成 | ≤ 3s |
| NFR-002 | Guide Agent 响应时间 | ≤ 10s |
| NFR-003 | Librarian 处理 20 个条目以内的 consolidation | ≤ 15s |
| NFR-004 | 所有 agent prompt 和模板为纯文本 Markdown 格式 | 无二进制依赖 |

## 澄清记录（Sage Interview 产出）

| # | 问题 | 用户回答 |
|---|------|---------|
| 1 | V1 应该包含哪些交付物？ | Guide Agent、Librarian Agent、8 个输出模板、安装/初始化工具 |
| 2 | Librarian 的触发方式？ | 两者都支持：手动 + 自动（阈值 N=5） |
| 3 | 会话保存为 Wiki 条目的触发方式？ | Agent 自动保存（每次对话完成后写入） |
| 4 | 8 个模板的使用方式？ | 严格模板 — Agent 必须按模板格式输出 |
| 5 | CLI 工具范围？ | 仅 `specforge init` |
| 6 | specforge 安装方式？ | Shell 脚本（curl \| bash） |
| 7 | init 后用户看到什么？ | 打印指引文本（下一步、推荐模型等） |
| 8 | V1 验收标准？ | 自举成功 — specforge 用自身流程完成了 specforge v1 的开发 |

## Lex 审核结果

- [ ] 所有需求可追踪到用户故事
- [ ] 所有需求可断言（有明确的测试方法）
- [ ] 没有模糊词汇（"优化""改进""增强"需具体化）
