# 007 — agents 写入路径漏改修复（v0.5-005 后续）

- **状态**: 已采纳
- **日期**: 2026-06-25
- **影响**: 14 个 agents/*.md + 18 个 .opencode/agents/*.md + 3 个 bats 测试文件 + VERSION 0.5.3 → 0.5.4

## 背景

[ADR 006](./006-namespace-cleanup.md)（v0.5-005 namespace cleanup）把 `wiki/` 与 `raw/` 收归到 `.specforge/wiki/` 与 `.specforge/raw/`，但**漏改了 `agents/*.md` 中所有"写入路径"行**。

原因复盘：在执行文本替换时，旧路径 `wiki/pages/{x}.md` 前缀应改为 `.specforge/wiki/pages/{x}.md`，但 sed/global replace 模式多打了一个 `.specforge/`，最终变成 `.specforge/.specforge/wiki/pages/{x}.md`（多一个 `.specforge/`）。这一 bug 跨越 14 个 agent 文件、~18 处"写入路径"行，被 v0.5-005 自身 dogfood 验证漏过（因为 framework 自己跑了一遍 `init` 后没让 agent 真去写 wiki）。

v0.5-007 (commit `ed27d52`) 的 OpenCode board 生成（`specforge_board.py`）从源 `agents/*.md` 复制内容到 `.opencode/agents/*.md`，bug 被一并复制到 18 个 OpenCode agent 文件。

**实际影响**：
- Sage / Scout / Librarian / Shield / Hunter / Prism / Forge / Lex / Keeper / Arbiter / Archer / Maestro / Cynic / Warden 等 14 个 agent 按 prompt 写入 wiki 页面时，写到不存在的 `.specforge/.specforge/wiki/pages/...` 路径
- 用户的 wiki 永远空（数据写到了错误的子路径里），且不报错（write to nonexistent path 在多数 LLM agent 工作流中会被静默忽略）
- OpenCode 用户（v0.5-007+）也受同样影响

**漏检原因**：
- v0.5-005 的 dogfood 验证只测了 `init`/`upgrade` 的目录布局与 `git mv` 行为，没测"agent 真按 prompt 写入"
- bats 测试集（`test_wiki.bats`）当时只有 5 个测试，断言 `Librarian mentions .specforge/wiki/pages/ directory` 这种字符串存在性，没断言"路径不重复"
- 用户实际使用时（手动让 agent 写 wiki）会触发，但 dogfood 阶段没人手动做这件事

## 决策

分两层修：

### 1. 立即修：v0.5-009-test-cleanup

- 把 14 个 `agents/*.md` 中所有 `.specforge/.specforge/wiki/` 字面量替换为 `.specforge/wiki/`（14 处）
- 删除 `.opencode/agents/` 后重跑 `bin/specforge board opencode` 重新生成（18 个文件）
- 修复 `tests/test_init_adopt_path.bats` T01/T05 的旧路径断言（`agents/` → `.specforge/agents/`）
- 把 `tests/test_specforge_cli.bats` 的 31 个中文 test 名改为 ASCII ID（绕开 bats 解析器对多字节字符名的 bug）
- 顺手发现并修 `CLI-301: doctor_is_checkup_alias` 的字符串断言（实际输出是 `[通过+警告]`，不是 `[通过]`）
- VERSION 0.5.3 → 0.5.4

### 2. 后续修：v0.5-010-ASCII-test-names（待开）

`tests/test_specforge_cli.bats` 暴露了同类问题在 6 个其它 bats 文件中也存在，影响 73 个测试：

| 文件 | 失败数 | 备注 |
|---|---|---|
| test_identity_check.bats | 15 | `ID-001` ~ `ID-400` |
| test_issue_form.bats | 37 | `FORM-001` ~ `FORM-009` |
| test_maestro.bats | 5 | `MAESTRO_*` |
| test_probe.bats | 7 | `PROBE_*` |
| test_sage_lex_pr_discussion.bats | 6 | `SAGE-PR-*` / `LEX-PR-*` |
| test_scout_project_board.bats | 3 | `SCOUT_*` |

不开在 v0.5-009，避免单次提交跨度过大。**但必须在 v0.6 之前清掉**，否则 CI 基线不可信。

## 备选

### 方案 A：v0.5-005 回滚重做

发现 bug 立即 revert v0.5-005，重新设计文本替换策略。

**拒绝理由**：v0.5-005 已发布到 v0.5.1 / v0.5.2 / v0.5.3，回滚成本远高于补 patch。漏改的范围明确（14 个文件 ~18 处），修补是 trivial 的单行替换。

### 方案 B：在 bin/specforge 加"路径 lint"

写一个 linter，扫描所有 agent prompt 文件，检测 `.specforge/\.specforge/` 这种重复 namespace 模式。

**接受**：长期有价值（防止以后又出现类似 bug）。但 linter 本身需要 spec 评审 + 工具 + 测试，本 ADR 暂不写代码，仅在 ADR 中立 flag 提示"v0.6 引入 agent prompt linter"。

### 方案 C：dogfood 时让 agent 真写一条 wiki 页面

把"agent 实际写 wiki"作为 dogfood 必跑步骤，暴露字符串错位 bug。

**接受**：是 v0.5-005 漏检的根本原因。需要在 dogfood checklist 里加一项，但本 ADR 不展开。

## 后果

### 短期（v0.5-009）

- 所有现有 user 项目需要 `cd $SPECFORGE_HOME && sed -i '' 's|\.specforge/\.specforge/wiki/|\.specforge/wiki/|g' agents/*.md` 一次性 patch（如果他们装过 v0.5.1 ~ v0.5.3）
- 升级到 0.5.4 后，agent 写入路径正确，wiki 真正能累积

### 长期

- v0.6 应加 agent prompt linter（方案 B）
- v0.6 应加 dogfood checklist：让 agent 真写一条 wiki 页面并断言 `ls .specforge/wiki/pages/` 多一个文件（方案 C）
- "bats test 名应为 ASCII" 应写入 `.specforge/wiki/decisions/` 风格的约定（v0.5-010 + v0.6 补）

## 上游 commit

- v0.5-005: `cc49718` refactor(layout)!: move wiki/ + raw/ to .specforge/ + auto-migrate
- v0.5-007: `ed27d52` feat(board): add OpenCode board generation and model alias resolution
- v0.5-008: `d1faa0b` feat(ci): add AC traceability and assertion hygiene tools

## 相关 spec

- [v0.5-009-test-cleanup](../project/specs/v0.5-009-test-cleanup/spec.md)
- [v0.5-005-namespace-cleanup](../project/specs/v0.5-005-namespace-cleanup/spec.md)
