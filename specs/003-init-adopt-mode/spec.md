# init 子命令支持既存项目非破坏性合并 — Spec

- **Spec ID**: 003-init-adopt-mode
- **创建日期**: 2026-06-14
- **状态**: 已确认（Lex 已 Approve，PR #25 已 merge；本 commit 补齐 Sage Interview 澄清记录）

## 用户故事

| ID | 故事 | 验收条件 | 优先级 |
|----|------|---------|--------|
| US-001 | 作为 specforge 用户，我希望 `init` 能识别"目标路径已存在"并转入非破坏性合并模式，以便把 specforge 接入存量项目时不需要手工执行等价命令 | AC-1: `init <existing-path>` 不报错；AC-2: 既存源代码字节级不变 | P0 |
| US-002 | 作为 specforge 用户，我希望 adopt 模式能清晰地报告哪些文件被新增、哪些被跳过、哪些被备份，以便我能 audit 这次改动的范围 | AC-3: 输出 `[+]` / `[=]` / `[!]` 三档分类 | P1 |
| US-003 | 作为 specforge 用户，我希望在合并前能用 `--dry-run` 预览会做什么，以便我能确认不会破坏现有内容 | AC-4: `--dry-run` 后 working tree 字节级不变 | P0 |

## 功能需求

> **锚点约定**：每个 FR 单元前必须有显式 HTML 锚点 `<a id="fr-XXX"></a>`（小写、3 位零填充）。FR-008 起新编号，与现有 FR-001~FR-007 不冲突。

<a id="fr-008"></a>
**FR-008**: `init` 子命令必须能识别"目标参数是既存路径 vs 新项目名"。**判定原则**：参数含 `/`、以 `.` 开头、或以 `~` 开头 → 既存路径（走 adopt）；否则视为裸名（走新建，行为不变）。可测试性: ✅

<a id="fr-009"></a>
**FR-009**: 当判定为 adopt 模式时，`init <existing-path>` 必须不破坏既存路径下的任何源代码（递归扫描验证字节级不变）。可测试性: ✅

<a id="fr-010"></a>
**FR-010**: adopt 模式对 `agents/`、`templates/`、`specs/`、`wiki/{pages,decisions}/`、`raw/sources/` 这 5 个目录的处理：**只创建缺的，不动有的**。可测试性: ✅

<a id="fr-011"></a>
**FR-011**: adopt 模式对 `agents/*.md` 和 `templates/*.md` 文件的合并策略：**默认 skip + warn 同名已有文件**，可选 `--backup`（备份为 `.bak`）或 `--force`（覆盖）。可测试性: ✅

<a id="fr-012"></a>
**FR-012**: adopt 模式必须支持 `--dry-run` flag，触发后只打印会做什么，不实际改 working tree。可测试性: ✅

<a id="fr-013"></a>
**FR-013**: adopt 模式结束后必须打印分档报告，分类：[+] 新增、[=] 跳过（已有同名）、[!] 备份（启用 --backup 时）。可测试性: ✅

<a id="fr-014"></a>
**FR-014**: 向既存 `.gitignore` 追加 specforge 相关条目（不是覆盖），如果条目已存在则不重复添加。**追加清单**（最小集）：`.specforge/`（用户模型配置运行时目录）。**不在 gitignore 处理的**（因为它们是 specforge-owned 默认就该在仓内或不存在的）：`.kilo/`、`wiki/.cache` 都不需要。可测试性: ✅

<a id="fr-015"></a>
**FR-015**: 既存 `init <bare-name>` 命令行为必须保持向后兼容：裸名 + 已存在目录 → 报错（与现有 `die "Directory '$PROJECT_NAME' already exists"` 一致）。可测试性: ✅

## 非功能需求

| ID | 需求 | 指标 |
|----|------|------|
| NFR-001 | 既存 `bin/specforge` 总行数增量 | ≤ 150 行（含 dry-run、adopt 分支、报告函数） |
| NFR-002 | bats 测试新增 case 数 | ≥ 8（覆盖 5 个核心 FR + 3 个边界 case） |
| NFR-003 | 既存 `init <bare-name>` 行为字节级不变 | 对照 `tests/test_init.bats` 全部现有 case 通过 |
| NFR-004 | 文档更新覆盖 README §8.3 和 agents/README.md | 必改 |

## 澄清记录（Sage Interview 产出）

| # | 问题 | 用户回答 |
|---|------|---------|
| 1 | FR-008 判定规则：参数含 `/`、以 `.` 开头、或以 `~` 开头 → 既存路径（adopt）；否则裸名（新建） | 已采纳（用户在会话中确认"走 C 智能检测 (推荐)"，C 方案即此判定） |
| 2 | `.gitignore` 追加清单 | 已采纳最小集：仅 `.specforge/`。其他（`.kilo/`、`wiki/.cache`）不需要 gitignore 处理 |
| 3 | 既存文件与 SPECFORGE_HOME 版本不同时策略 | 已采纳：默认 skip+warn，flag `--backup` 备份为 `.bak`，flag `--force` 覆盖 |
| 4 | 是否默认安装 `.github/ISSUE_TEMPLATE/feature.yml` | 已采纳：默认不装，flag `--with-issue-template` 显式触发 |
| 5 | 报告输出格式 | 已采纳：默认纯文本分档 `[+]/[=]/[!]`，可选 flag `--json` 输出机器可读 |
| 6 | adopt 模式是否要求目标是 git repo | 已采纳：要求；否则报错并提示先 `git init` |

**注**：#1 的"采纳"基于用户在会话中明确选择 C 方案（C 方案定义即此判定规则）。#2–#6 的"采纳"基于用户在 PR #25 的 PR-level comment (`4701972133`) 上对 Sage 推测答案的默认采纳；如需修改请在该 PR 的对应 inline comment 处回复纠正（本 commit 之后该路径已合并，对应修改应开新 PR 跟进）。

## Lex 审核结果

- [x] 所有需求可追踪到用户故事
- [x] 所有需求可断言（有明确的测试方法）
- [x] 没有模糊词汇（[待澄清] 已 resolve，详见澄清记录）
- [x] 所有 FR 都有显式锚点 `<a id="fr-XXX"></a>`

**Lex PR Review**: https://github.com/zillionare/specforge/pull/25 — zillionare APPROVED at 2026-06-14 13:57:11Z。

## 附录：FR-001~FR-007 历史

为避免编号冲突，本文 FR 从 008 起。原 specforge v0.2 spec 的 FR-001~FR-007 编号保留不变（属于"模型配置"主题）。