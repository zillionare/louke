# v0.5 收尾：测试债 + agents 路径漏改修复 — Spec

- **Spec ID**: v0.5-009-test-cleanup
- **创建日期**: 2026-06-25
- **状态**: 草稿
- **关联**: v0.5-005-namespace-cleanup（路径漏改）, v0.5-007-multi-ide-boards（.opencode/agents/ 复制污染）

## 背景

v0.5-005 namespace cleanup (commit `cc49718`) 把 `wiki/` 与 `raw/` 收归到 `.specforge/wiki/` 与 `.specforge/raw/`，但**漏改了 `agents/*.md` 中所有"写入路径"行**——把旧路径 `wiki/pages/{x}.md` 在文本替换成 `wiki/` 前缀时多打了 `.specforge/`，变成 `.specforge/.specforge/wiki/pages/{x}.md`（多一个 `.specforge/`）。

后续 v0.5-007 OpenCode board 生成 `.opencode/agents/*.md` 时，从源 `agents/*.md` 复制，所以 bug 也被复制到了 `.opencode/agents/`。

**实际影响**: 12+ 个 agent 的 wiki 写入动作会写到错误路径 `.specforge/.specforge/wiki/`，导致 wiki 完全空（写到不存在目录的子路径里），用户感知不到数据写入。

v0.5-005 commit 消息同时记了 3 个 pre-existing 失败的回归测试债，状态经核验：
- `test_init_adopt_path` T01/T05 — 仍失败（断言旧的 `agents/` 路径）
- `test_templates` UT-012-02 — **已通过**（`templates/spec.md:74` 已有 `## 澄清记录`，不在范围内）
- `test_specforge_cli` CLI-601 — 47 个测试因中文 test 名字符编码问题只跑了 17 个，无法判断真伪

## 目标

1. 修复 `agents/*.md` (12 个) 中所有 `.specforge/.specforge/wiki/` → `.specforge/wiki/`
2. 重新生成 `.opencode/agents/*.md` (10 个) 同步修复
3. 修复 `test_init_adopt_path` T01/T05 的路径断言
4. 把 `test_specforge_cli.bats` 的中文 test 名改为英文/拼音 ID，绕开 bats locale 问题
5. 跑全量 bats 0 回归，bump VERSION 0.5.1 → 0.5.2

## 非目标

- 不修改 v0.5-005 的 `init` / `upgrade` 行为（已正确）
- 不重写任何 agent 的"职责描述"，仅修"写入路径"行
- 不引入 bats locale 修复（env 配置），只把中文 test 名 ASCII 化
- 不动 `tests/test_templates`（已通过）

## 用户故事

### US-010
story: 作为 specforge 用户，我希望 Librarian / Scout / Sage 等 agent 把 wiki 页面写到 `.specforge/wiki/pages/`，而不是不存在的 `.specforge/.specforge/wiki/pages/`，以便 wiki 真的能被构建。
priority: P0

### US-020
story: 作为 specforge 用户，我希望 OpenCode IDE 加载的 agent 也用正确的写入路径，以便 OpenCode 环境下 wiki 写入同样有效。
priority: P0

### US-030
story: 作为 specforge 维护者，我希望 `bats tests/test_specforge_cli.bats` 真的跑 47 个测试，而不是被中文 test 名字符编码吃掉 30 个，以便我能信任回归基线。
priority: P0

### US-040
story: 作为 specforge 维护者，我希望 `test_init_adopt_path` 断言新路径 `.specforge/agents/`，与 v0.5-005 后的 init 行为一致。
priority: P0

## 功能需求

### FR-010 修复 agents/*.md 写入路径

`agents/{Arbiter,Archer,Maestro,Cynic,Warden,Sage,Forge,Lex,Keeper,Scout,Prism,Hunter,Shield,Guide}.md` 中所有形如：

```
.specforge/.specforge/wiki/pages/...
```

的行（通常是"写入路径"或 wiki 路径说明），替换为：

```
.specforge/wiki/pages/...
```

AC：`grep -rn '\.specforge/\.specforge/' agents/ | wc -l` 返回 0；`grep -rn '\.specforge/wiki/' agents/ | wc -l` 至少 13（每个 agent 至少 1 处）。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-020 重新生成 .opencode/agents/*.md

跑 `specforge_board.py`（v0.5-007 引入）重新生成 `.opencode/agents/*.md`，使 OpenCode 环境的 agent 写入路径同步修复。

AC：`grep -rn '\.specforge/\.specforge/' .opencode/ | wc -l` 返回 0；`.opencode/agents/*.md` 文件数与 `agents/*.md` 数量一致。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-030 test_init_adopt_path 路径断言同步

`tests/test_init_adopt_path.bats` T01 与 T05 的 `[ -d "agents" ]` / `[ -d "newproj/agents" ]` 改为 `[ -d ".specforge/agents" ]` / `[ -d "newproj/.specforge/agents" ]`。

AC：`bats tests/test_init_adopt_path.bats` 5/5 通过。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-040 test_specforge_cli.bats 中文 test 名 ASCII 化

`tests/test_specforge_cli.bats` 中所有 `@test "中文..."` 行，改为 `@test "CLI-NNN: <english_or_pinyin_id> <short_desc>"` 形式：

| 当前中文名 | 新 ID |
|---|---|
| `CLI-001: bin/specforge 启动` | `CLI-001: bin_specforge_starts` |
| `CLI-002: bin/specforge 无输出走 bash` | `CLI-002: bin_specforge_no_output_via_bash` |
| `CLI-003: 中文输出 (被 bash 截断)` | `CLI-003: chinese_output_truncated_by_bash` |
| `CLI-100: 缺 --help` | `CLI-100: missing_help_flag` |
| ... | (依此类推) |

重命名原则：
- 保留原中文描述作为行尾注释（可选，便于追踪）
- ID 用 `[a-z0-9_]` + 冒号 + 简短英文描述
- 冒号前后保持与现有 bats 习惯一致

AC：`bats tests/test_specforge_cli.bats` 实际跑的测试数 ≥ 47/47（不再有 "unknown test name" 警告）；跑通率 = 47/47，或失败仅限真实 bug 且记录在 AC 缺口表。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-050 全量回归 + bump VERSION

- `find tests -name '*.bats' | xargs bats` 0 回归
- VERSION 0.5.1 → 0.5.2
- `install.sh` 与 `bin/specforge` 的版本字串同步（如有）

AC：`bats tests/*.bats` exit code 0；`cat VERSION` 输出 `0.5.2`；`specforge version` 输出 `0.5.2`。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

## 用户使用场景

### scenario-010 Agent 写入路径自检

1. 维护者升级 specforge 到 0.5.2
2. 在项目内启动任一 agent (如 Sage)
3. Sage 按 `agents/Sage.md` 写入 wiki → 实际写到 `.specforge/wiki/pages/sage-{topic}.md`
4. 维护者 `ls .specforge/wiki/pages/` 能看到新增文件
5. 之前漏改造成的 `.specforge/.specforge/` 鬼目录不再产生

### scenario-020 CI 跑全量 bats

1. 维护者在 CI 跑 `bats tests/*.bats`
2. `test_specforge_cli` 不再因 "unknown test name" 跳过 30 个测试
3. 真实跑 47/47，CI 能可靠地反映基线

## 待修复文件清单

```
agents/Arbiter.md:101
agents/Archer.md:109
agents/Maestro.md:160
agents/Cynic.md:113
agents/Warden.md:118
agents/Sage.md:365
agents/Guide.md:38,39,40,41,46
agents/Forge.md:142
agents/Lex.md:283
agents/Keeper.md:108
agents/Scout.md:219
agents/Prism.md:154
agents/Hunter.md:142
agents/Shield.md:103
.opencode/agents/*.md  (10+ files, 由 specforge_board 重新生成)
tests/test_init_adopt_path.bats:28,58
tests/test_specforge_cli.bats (全部中文 test 名, ~30 个)
VERSION
```

## 风险

- 改 agent 路径字符串后，已按旧路径写过的用户需要手动 `mkdir -p .specforge/wiki/pages` 重建或迁移（v0.5-005 已为 wiki/raw 做过迁移脚本；本 spec 不重复覆盖，但加 ADR 说明）
- `.opencode/agents/` 是 v0.5-007 生成的派生产物，重新生成可能改变 model alias 解析结果（不会，本 spec 不改 board 模型映射）

## 上游 commit 引用

- v0.5-005: `cc49718` (refactor(layout)!: move wiki/ + raw/ to .specforge/ + auto-migrate)
- v0.5-007: `ed27d52` (feat(board): add OpenCode board generation and model alias resolution)
- v0.5-005 commit message 中"pre-existing 失败"清单（test_init_adopt_path T01/T05、test_templates UT-012-02、test_specforge_cli CLI-601）— 经核验 UT-012-02 已通过，本 spec 只修前 2 项
