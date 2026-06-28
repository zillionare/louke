# init 后目录收归到 .specforge/ 命名空间 — Spec

- **Spec ID**: v0.5-005-namespace-cleanup
- **创建日期**: 2026-06-23
- **状态**: 草稿
- **关联**: v0.3-003-init-adopt-mode（FR-010 将被本 spec 取代 / 改写）

## 背景

`specforge init` 当前在项目根目录创建两类非源码目录：

- `wiki/{pages,decisions}/` + `wiki/{index,overview,log}.md` —— Agent 知识库（LLM-Wiki 三层架构）
- `raw/sources/` —— Agent 完整会话记录原始层

这两类目录在项目根目录存在三个问题：

1. **命名空间污染** —— `raw/` 是泛用名，未来用户或工具可能也会用 `raw/`，冲突排查困难
2. **与"开发项目"语义不符** —— LLM-Wiki 来自 Karpathy 的个人知识库场景，硬塞到 dev project 根目录显得别扭
3. **持续累积的 git 风险** —— `raw/sources/` 会话记录会无限增长，污染 history（即便 gitignore 也容易误 commit）

`wiki/` 同理；用户在 v0.3-003 接受根目录布局时是"勉强接受"，现在借本 spec 一次性收归。

## 目标

将 `init` 创建的全部 specforge 自有目录收归到 `.specforge/` 命名空间下，使**项目根目录只包含用户自己的代码与 specforge 框架资产之外的东西**。同时为已 init 的项目提供自动迁移，零手工操作。

## 用户故事

### US-010
story: 作为 specforge 用户，我希望 `init` 创建的 wiki/raw 目录位于 `.specforge/` 下，而不是项目根，以便项目根目录保持干净、不会被 specforge 自身的目录名污染。
priority: P0

### US-020
story: 作为已 init 过的 specforge 用户，我希望重跑 `init --adopt` 时能自动把旧的 `wiki/` 和 `raw/` 移到新位置，以便我不需要手动执行 `mv`。
priority: P0

### US-030
story: 作为 specforge 用户，我希望在迁移出错时能跳过自动迁移（`--no-migrate`），以便我能手动控制时机。
priority: P1

### US-040
story: 作为 specforge 用户，我希望 Librarian 等 agent 在新旧路径并存时优先使用新路径（`.specforge/wiki/...`），以便迁移期间混合状态仍能正常工作。
priority: P1

### US-050
story: 作为 specforge 用户，我希望 `specforge upgrade` 后 `$PATH` 里的 `specforge` 二进制也被自动刷新，以便我跑完 upgrade 立即能用到最新版的子命令和 flag。
priority: P0

## 用户使用场景

### scenario-010 新项目 init

1. 用户在空目录执行 `specforge init myproj`
2. `bin/specforge` 创建 `.specforge/{agents,templates,project,wiki/pages,wiki/decisions,raw/sources}`
3. 项目根目录**没有** `wiki/`、**没有** `raw/`

### scenario-020 既存项目 adopt + 自动迁移

1. 已有项目（旧版 specforge init 过）：根目录有 `wiki/` 和 `raw/`
2. 用户升级 specforge 后执行 `specforge init .`
3. `bin/specforge` 检测到旧路径 → `git mv` 移到 `.specforge/wiki/` 与 `.specforge/raw/`
4. 再做 create-if-missing，幂等完成
5. 用户 `git status` 看到的是 rename，不是 delete+add

### scenario-030 拒绝自动迁移

1. 用户带 `--no-migrate`：`specforge init . --no-migrate`
2. `bin/specforge` 不做迁移
3. 在 tri-state 报告里标出"未迁移: wiki/ → .specforge/wiki/, raw/ → .specforge/raw/" 提示用户手动操作

## 功能需求

### FR-010 init 路径收归

`init <bare-name>` 创建的目录**仅限**：

```
.specforge/agents/
.specforge/templates/
.specforge/project/
.specforge/wiki/pages/
.specforge/wiki/decisions/
.specforge/raw/sources/
```

**禁止**在项目根创建 `wiki/`、`raw/`、`wiki/pages/`、`wiki/decisions/`、`raw/sources/` 任一路径。AC：init 完成后 `find . -maxdepth 2 -type d -name wiki -o -name raw` 仅匹配 `.specforge/wiki`、`.specforge/raw` 两项。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-020 adopt 模式 create-if-missing 路径同步

`cmd_init_adopt` 的"5 个目录"（来自 v0.3-003 FR-010）路径修订为：

| 旧路径 | 新路径 |
|---|---|
| `agents/` | （取消，改为 `.specforge/agents/`，见 FR-010） |
| `templates/` | （取消，改为 `.specforge/templates/`，见 FR-010） |
| `specs/` | `.specforge/project/specs/`（v0.3-003 已部分对齐，需补全） |
| `wiki/{pages,decisions}/` | `.specforge/wiki/{pages,decisions}/` |
| `raw/sources/` | `.specforge/raw/sources/` |

AC：adopt 后 `for d in .specforge/agents .specforge/templates .specforge/project .specforge/wiki/pages .specforge/wiki/decisions .specforge/raw/sources; do [ -d "$d" ]; done` 全部通过。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-030 旧路径自动迁移

`cmd_init_adopt` 在做 create-if-missing 之前，先执行"路径迁移"步骤：

| 检测条件 | 操作 |
|---|---|
| `[ -d wiki ]` 且 `[ ! -e .specforge/wiki ]` | `git mv wiki .specforge/wiki`（若跟踪）或 `mv wiki .specforge/wiki`（若未跟踪） |
| `[ -d raw ]` 且 `[ ! -e .specforge/raw ]` | `git mv raw .specforge/raw`（若跟踪）或 `mv raw .specforge/raw`（若未跟踪） |
| 旧路径不存在 | skip |
| 旧路径与新路径**都**存在 | 报错并退出，提示用户手动处理（防止数据丢失） |

迁移步骤的输出格式：`[→] wiki/ → .specforge/wiki/`（使用新的 `[→]` 档位，区别于现有的 `[+]`/`[=]`/`[!]`）。

AC：
- 既存 `wiki/` 被 `git mv` 到 `.specforge/wiki/` 后，`git status` 显示 rename 而非 delete+add
- 旧路径不存在时不报错（idempotent）
- 旧新并存时 exit code ≠ 0 且 stderr 含 `wiki` 和 `.specforge/wiki`

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-040 --no-migrate flag

`init --adopt` 接受 `--no-migrate` flag，跳过 FR-030 的迁移步骤。skip 后必须在 tri-state 报告**末尾**追加一段迁移提示：

```
[→] 未迁移: wiki/ → .specforge/wiki/
[→] 未迁移: raw/  → .specforge/raw/
提示: 重新运行 'specforge init .' (无 --no-migrate) 自动迁移, 或手动执行:
      git mv wiki .specforge/wiki && git mv raw .specforge/raw
```

AC：带 `--no-migrate` 时，旧路径**保持原位**（不删不移），且报告含上述提示。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-050 干跑（--dry-run）下的迁移报告

`init --adopt --dry-run` 在不实际改动 working tree 的前提下，仍打印**会做什么**：

- 列出将被 `git mv` 的旧路径 → 新路径对
- 不会 `mkdir`、不会 `mv`、不会 `cp`
- `--dry-run` + `--no-migrate` 兼容：仅打印"将跳过迁移"的提示

AC：`--dry-run` 前后 `find . -type f -not -path "./.git/*" | xargs sha256sum` 字节级不变；输出含迁移计划文本。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-060 Librarian / 全部 agent prompt 路径同步

`agents/*.md` 内所有 `wiki/pages/`、`wiki/decisions/`、`raw/sources/` 引用**必须**更新为：

- `wiki/pages/` → `.specforge/wiki/pages/`
- `wiki/decisions/` → `.specforge/wiki/decisions/`
- `raw/sources/` → `.specforge/raw/sources/`
- `wiki/index.md` → `.specforge/wiki/index.md`
- `wiki/overview.md` → `.specforge/wiki/overview.md`
- `wiki/log.md` → `.specforge/wiki/log.md`
- `wiki/.cache` → `.specforge/wiki/.cache`

**例外**：`Librarian.md` 的"三层架构"示意图允许保留简写（`raw/sources`、`wiki/pages`），但需在图下方加一行注释：*实际路径 = `.specforge/raw/sources/`、`.specforge/wiki/pages/`*。

**例外**：`wiki/entries/`（legacy，out of scope）相关引用不在本 spec 处理。

AC：`grep -RE 'wiki/(pages|decisions|index|overview|log)|raw/sources' agents/` 命中行全部包含 `.specforge/` 前缀（或属于上述两个例外）。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-070 README + 文档路径同步

`README.md`、`wiki/overview.md`、`wiki/log.md`、`wiki/pages/*.md` 中所有 wiki/raw 路径引用同步更新到 `.specforge/wiki/...`、`.specforge/raw/...`。`README.md` §11.x 架构决策表格中的 `[`wiki/decisions/`]` 链接同步更新。

AC：`grep -nE '\bwiki/(pages|decisions|index|overview|log)\b' README.md` 命中行全部包含 `.specforge/` 前缀。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-080 v0.3-003 FR-010 标 deprecated

`.specforge/project/specs/v0.3-003-init-adopt-mode/spec.md` 第 26 行的 FR-010 改为"已由 v0.5-005 取代"，表格 `有效需求` 改 `❌`，并在文末加 supersedes 注释指向本 spec。**不删除**锚点 `fr-010`，避免引用混淆（与 v0.4-004 的废弃规则一致）。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-090 ADR 留痕

在 `.specforge/wiki/decisions/006-namespace-cleanup.md` 新增一条 ADR，包含：
- 背景：根目录污染问题
- 决策：迁移到 `.specforge/`
- 备选：方案 B（彻底砍掉 raw + LLM-Wiki）— 拒绝理由：保留 LLM-Wiki 差异化卖点
- 后果：~25 个文件路径同步，零功能损失

并在 `README.md` §11.x 决策表格中追加一行 `[006]`。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

## 非功能需求

### NFR-010 既存测试仍通过

`tests/test_init.bats` + `tests/test_init_adopt_flow.bats` + `tests/test_wiki.bats` 全部 case 通过；`test_init_adopt_flow.bats` 中 `FR10_T01` 的 `wiki/pages`、`wiki/decisions`、`raw/sources` 断言改写为 `.specforge/wiki/...`、`.specforge/raw/...`。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### NFR-020 specforge 自身先吃狗粮

本 spec 的实施 PR 必须在 specforge 自身项目里先跑通（即 specforge 自己 init 出的 `.specforge/wiki/` 与 `.specforge/raw/` 必须用起来，不再于根目录创建 `wiki/` 或 `raw/`）。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### NFR-030 upgrade 同步刷新 \$PATH 里的 `specforge` 二进制

`cmd_upgrade` 在 `git fetch + git merge --ff-only` 之后，必须把更新后的 `$SPECFORGE_HOME/bin/specforge` 重新拷贝到 `$BIN_DIR/specforge`（即用户 `$PATH` 里的入口），否则用户跑 `specforge upgrade` 后，$PATH 上的可执行文件仍是旧版（pre-existing bug：`install.sh:30-31` 在 install 时 copy 一次，但 upgrade 路径不 copy）。

**AC**：
- `cmd_upgrade` 末尾追加 `cp $SPECFORGE_HOME/bin/specforge $BIN_DIR/specforge`（含 fallback 提示）
- `tests/test_specforge_cli.bats` 新增一个 case 验证：执行 `specforge upgrade` 后，`$BIN_DIR/specforge` 的 hash 与 `$SPECFORGE_HOME/bin/specforge` 的 hash 一致
- 若 `$BIN_DIR` 不存在或不可写，打印 hint（不报错退出，因为有的用户把 specforge clone 后直接 `bin/specforge` 调，不依赖 $BIN_DIR 拷贝）

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

## 澄清记录（Sage Interview 产出）

> 待用户 review 时填入。

## Lex 审核结果

- [ ] 所有需求可追踪到用户故事
- [ ] 所有需求可断言（有明确的测试方法）
- [ ] 没有模糊词汇
- [ ] 所有 FR 都有显式锚点 `<a id="fr-XXX"></a>`

## 设计决策（待你确认）

以下 4 点已在我方案里默认采用，如不同意请在 review 时指出：

| # | 决策 | 默认选择 | 备选 |
|---|------|---------|------|
| D1 | `wiki/` 是否一并迁移 | **是**（原 Plan A 范围） | 只迁 `raw/`，保留 `wiki/` |
| D2 | `raw/sources/` 与 `.specforge/wiki/` 的关系 | **平行** (`.specforge/raw/sources/`) | 嵌套 (`.specforge/wiki/sources/`) |
| D3 | 旧路径处理方式 | **自动 `git mv`**（`--no-migrate` 可 opt-out） | 纯 break-change，提示用户手动 |
| D4 | `wiki/entries/`、`wiki/consolidated.md`（legacy） | **out of scope** | 顺手清理 |
