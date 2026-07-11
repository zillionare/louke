# init 子命令支持既存项目非破坏性合并 — Spec

- **Spec ID**: 003-init-adopt-mode
- **创建日期**: 2026-06-14
- **状态**: 草稿（Sage Interview 进行中）

## 用户故事

| ID | 故事 | 验收条件 | 优先级 |
|----|------|---------|--------|
| US-001 | 作为 specforge 用户，我希望 `init` 能识别"目标路径已存在"并转入非破坏性合并模式，以便把 specforge 接入存量项目时不需要手工执行等价命令 | AC-1: `init <existing-path>` 不报错；AC-2: 既存源代码字节级不变 | P0 |
| US-002 | 作为 specforge 用户，我希望 adopt 模式能清晰地报告哪些文件被新增、哪些被跳过、哪些被备份，以便我能 audit 这次改动的范围 | AC-3: 输出 `[+]` / `[=]` / `[!]` 三档分类 | P1 |
| US-003 | 作为 specforge 用户，我希望在合并前能用 `--dry-run` 预览会做什么，以便我能确认不会破坏现有内容 | AC-4: `--dry-run` 后 working tree 字节级不变 | P0 |

## 功能需求

> **锚点约定**：每个 FR 单元前必须有显式 HTML 锚点 `<a id="fr-XXX"></a>`（小写、3 位零填充）。FR-008 起新编号，与现有 FR-001~FR-007 不冲突。

<a id="fr-008"></a>
**FR-008**: `init` 子命令必须能识别"目标参数是既存路径 vs 新项目名"。**判定原则**：[待澄清-1]

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
**FR-014**: 向既存 `.gitignore` 追加 specforge 相关条目（不是覆盖），如果条目已存在则不重复添加。[待澄清-2] 追加哪些条目？ 可测试性: ✅

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
| 1 | [待澄清-1] 判定 "既存路径 vs 新项目名" 的规则？我倾向：**参数含 `/`、以 `.` 开头、或以 `~` 开头 → 既存路径**；否则视为裸名（新项目名）。这样 `init .`、`init ./proj`、`init /abs/path` 都走 adopt；`init myproj` 走新建。 | [待用户回答] |
| 2 | [待澄清-2] `.gitignore` 追加哪些条目？候选：`.kilo/`、`wiki/.cache`、`specs/.draft/`、`raw/sources/` 是否纳入？ | [待用户回答] |
| 3 | [待澄清-3] 默认行为如果既存文件**与 SPECFORGE_HOME 版本不同**（比如用户改过 `agents/Maestro.md`），应该 skip+warn 还是直接覆盖？我倾向 skip+warn（保护用户修改）。 | [待用户回答] |
| 4 | [待澄清-4] 是否需要 `--with-issue-template` flag 一并安装 `.github/ISSUE_TEMPLATE/feature.yml`？我倾向默认不装（避免与现有 GitHub 设置冲突），仅在显式 flag 时安装。 | [待用户回答] |
| 5 | [待澄清-5] 报告输出的格式：纯文本分档？还是 `--json` 可选输出机器可读？我倾向**默认纯文本**（用户友好），可选 `--json` flag 给 CI/script 用。 | [待用户回答] |
| 6 | [待澄清-6] 当目标路径不是 git repo 时怎么办？我倾向：**adopt 模式要求目标必须是 git repo**（否则报错），因为 specforge 流程严重依赖 git commit hash 回溯。 | [待用户回答] |

## Lex 审核结果

- [ ] 所有需求可追踪到用户故事
- [ ] 所有需求可断言（有明确的测试方法）
- [ ] 没有模糊词汇
- [ ] 所有 FR 都有显式锚点 `<a id="fr-XXX"></a>`

## 附录：FR-001~FR-007 历史

为避免编号冲突，本文 FR 从 008 起。原 specforge v0.2 spec 的 FR-001~FR-007 编号保留不变（属于"模型配置"主题）。
