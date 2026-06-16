# specforge v0.1 — Spec

- **Spec ID**: SPEC-V0.1-001
- **创建日期**: 2026-05-23
- **状态**: 评审中
- **关联 Project**: specforge-0.1 (#3)

## 用户故事

| ID | 故事 | 验收条件 | 优先级 |
|----|------|---------|--------|
| US-001 | 作为项目发起人，我通过 Scout Agent 收集项目信息并创建 repo/project，以便项目有基础设施 | Scout 产出 `specs/project-info.md`（含 story/version/repo/project），GitHub repo 可访问，Project 可见 | P0 |
| US-002 | 作为项目发起人，我想运行全部 21 个 Agent 的完整开发流程，以便验证方法论可行 | 全部 21 个 Agent (Scout~Shield + Guide + Librarian) 的 prompt 文件就绪，每个 Agent 可加载执行 | P0 |
| US-003 | 作为新用户，我想通过 `specforge init` 一键初始化项目，以便快速开始使用 | 执行 `specforge init <name>` 后创建目录结构（agents/templates/wiki/specs），终端打印 onboarding 指引 | P0 |
| US-004 | 作为开发者，我想让 Agent 的对话在 GitHub 上显性化、可追踪，以便回顾和审计 | 每个 Agent 对话通过 wiki 条目记录；Sage/Lex 通过 PR Review 讨论 | P1 |

## 功能需求

> **锚点约定**：每个 FR 单元前必须有显式锚点 `<a id="fr-XXX"></a>`，供 GitHub issue 反向链接。

<a id="fr-001"></a>
**FR-001**: Scout 收集 story/version/repo 信息并写入 `specs/project-info.md`  可测试性: ✅

<a id="fr-002"></a>
**FR-002**: Scout 创建 GitHub repo（如不存在）和 Project `{repo}-{version}`，配置 status board  可测试性: ✅

<a id="fr-003"></a>
**FR-003**: Scout 验证 issue 权限：创建测试 issue → comment → close  可测试性: ✅

<a id="fr-004"></a>
**FR-004**: Scout 验证 Project 权限：能将 issue 添加到 Project 并移动 status  可测试性: ✅

<a id="fr-005"></a>
**FR-005**: Warden 读取 `specs/project-info.md`，验证所有字段、repo 可访问、Project 存在、测试 issue 已 close  可测试性: ✅

<a id="fr-006"></a>
**FR-006**: Sage 创建 spec 分支、生成初始 spec.md、发 PR 并在 Files Changed 逐行提问  可测试性: ✅

<a id="fr-007"></a>
**FR-007**: Lex 通过 GitHub PR Review 审核 spec，使用 Request changes/Approve  可测试性: ✅

<a id="fr-008"></a>
**FR-008**: 全部 21 个 Agent prompt 文件就绪，会话保存指令已嵌入  可测试性: ✅

<a id="fr-009"></a>
**FR-009**: `specforge init` Shell 脚本可用（curl | bash 安装）  可测试性: ✅

<a id="fr-010"></a>
**FR-010**: Guide Agent 可回答方法论问题，Librarian Agent 可整合 wiki  可测试性: ✅

<a id="fr-011"></a>
**FR-011**: Clerk/Auditor/Probe/Judge/Archer/Cynic/Forge/Prism/Keeper/Herald/Arbiter/Hunter/Shield 的 prompt 按方法论就绪  可测试性: ⚠️ prompt 就绪但需集成测试

## 非功能需求

| ID | 需求 | 指标 |
|----|------|------|
| NFR-001 | 所有 Agent 对话通过 Wiki 条目和 GitHub PR 双轨记录 | PR comment + wiki entry 可查 |
| NFR-002 | Agent 的状态传递通过 repo 文件（project-info.md、spec.md 等），不通过聊天文本 | 可被下游 Agent 程序化读取 |
| NFR-003 | 可以有不完美的发布，但不能有不完整的发布 | v0.1 必须包含全部 21 个 Agent + init 工具 |

## 澄清记录

| # | 问题 | 用户回答 |
|---|------|---------|
| Q1 | US-001 验收条件？ | Scout 产出 project-info.md，repo 可访问，Project 可见 |
| Q1+ | Scout 的职责边界？ | 1) 创建 repo/版本号/分支/Project；2) 确保 issue 创建和回复权限；3) 确保 Project 读/写/移动 issue 权限 |
| Q2 | v0.1 包含哪些 Agent？ | 全部 21 个 |
| Q3 | v0.1 是否包含 specforge init？ | 需要。可以有不完美的发布，但不能有不完整的发布 |
| Q4 | 后续 Agent 是否在 v0.1 范围？ | 是，全部 21 个 |
| Q5 | PRD 中 V1 标准全部纳入 v0.1？ | 已澄清（Q2/Q3 回答了范围问题） |
| Q6 | v0.1 "自举成功"定义？ | 本项目也要使用 specforge 将要定义的方法来完成 |

## 关联
- PRD: `specs/001-specforge-v0.1/prd.md`
- PR: https://github.com/zillionare/specforge/pull/13

## Lex 审核结果

- [ ] 所有需求可追踪到用户故事
- [ ] 所有需求可断言（有明确的测试方法）
- [ ] 没有模糊词汇
- [ ] 所有 FR 都有显式锚点 `<a id="fr-XXX"></a>`
