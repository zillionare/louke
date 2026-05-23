# specforge v0.1 — Spec

- **Spec ID**: SPEC-V0.1-001
- **创建日期**: 2026-05-23
- **状态**: 评审中
- **关联 Project**: specforge-0.1 (#3)

## 用户故事

| ID | 故事 | 验收条件 | 优先级 |
|----|------|---------|--------|
| US-001 | 作为项目发起人，我通过 Scout Agent 收集项目信息并创建 repo/project，以便项目有基础设施 | [待澄清: Q1] | P0 |
| US-002 | [待澄清: Q2 — v0.1 包含哪些 Agent？全部 21 个还是仅 Scout→Warden→Sage→Lex？] | [待澄清] | P0 |
| US-003 | [待澄清: Q3 — v0.1 是否需要 specforge init 工具？还是仅 Agent prompt 文件？] | [待澄清] | [待澄清] |

## 功能需求

| ID | 需求 | 可测试性 |
|----|------|----------|
| FR-001 | Scout 收集 story/version/repo 信息并写入 `specs/project-info.md` | ✅ |
| FR-002 | Scout 创建 GitHub repo（如不存在）和 Project `{repo}-{version}` | ✅ |
| FR-003 | Warden 读取 `specs/project-info.md` 验证所有字段和权限 | ✅ |
| FR-004 | Sage 创建 spec 分支、生成初始 spec.md、发 PR 并在 Files Changed 逐行提问 | ✅ |
| FR-005 | Lex 通过 GitHub PR Review 审核 spec，使用 Request changes/Approve | ✅ |
| FR-006 | [待澄清: Q4 — 后续 Agent（Clerk/Auditor/Probe/Judge/Archer/Cynic/Forge/Prism/Keeper/Herald/Arbiter）是否需要在此版本覆盖？] | ⚠️ |

## 非功能需求

| ID | 需求 | 指标 |
|----|------|------|
| NFR-001 | 所有 Agent 对话通过 Wiki 条目和 GitHub PR 双轨记录 | PR comment + wiki entry 可查 |
| NFR-002 | Agent 的状态传递通过 repo 文件（project-info.md、spec.md 等），不通过聊天文本 | 可被下游 Agent 程序化读取 |

## 澄清记录（Sage Interview 产出）

| # | 问题 | 用户回答 |
|---|------|---------|
| Q1 | US-001 的用户故事是否需要更具体？"有基础设施"的验收条件是什么？ | [待澄清] |
| Q2 | v0.1 的范围是全部 21 个 Agent，还是仅跑通 Scout→Warden→Sage→Lex 的前 4 个阶段？ | [待澄清] |
| Q3 | v0.1 的交付物是否包含 `specforge init`（Shell 脚本），还是仅 Agent prompt 文件 + 模板？ | [待澄清] |
| Q4 | 后续 Agent（Clerk → Auditor → …→ Arbiter）是否也在 v0.1 范围内？ | [待澄清] |
| Q5 | PRD 中 "V1" 的验收标准（Guide Agent、Librarian Agent、specforge init 工具）是否全部纳入 v0.1？ | [待澄清] |
| Q6 | v0.1 的"自举成功"定义是什么？跑通哪些阶段算"成功"？ | [待澄清] |

## Lex 审核结果

- [ ] 所有需求可追踪到用户故事
- [ ] 所有需求可断言（有明确的测试方法）
- [ ] 没有模糊词汇
