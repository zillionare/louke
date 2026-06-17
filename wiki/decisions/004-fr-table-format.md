# ADR 004 — FR/NFR 元数据由 YAML 改为表格 (table + --- separator)

- **日期**: 2026-06-16
- **状态**: 已采纳 (FR-082)

## 背景

此前 FR/NFR 单元的元数据用紧跟在描述后的 YAML 代码块存放：

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

YAML 在 IDE / GitHub 渲染里都正常，但有三个痛点：

1. **可读性差** — 代码块远离标题，眼睛要扫几段才能对齐到状态。
2. **不易复制** — 复制单条 FR 引用时，YAML 块会被一并带走。
3. **容易在 quote dialogue 中被误判** — `resolved: ✅` 这类带 emoji 的行有可能被 quote parser 误识别为对话行。

## 决策

采用 markdown 三列表格紧贴 FR/NFR 标题，并以 `---` 作为相邻 FR 之间的视觉分隔。模板形式：

```markdown
### FR-010 {title}

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

{需求描述}

---
```

理由：

- **可读性** — 表格紧接标题，扫一眼即知 FR 状态。
- **复制友好** — 单行 `| ✅ | ✅ | ✅ |` 易于在 PR 评论 / issue body 引用。
- **解析友好** — 对 `tools/quote_parser.py` 而言，表格行有明确边界（`|` 起止），不会再因 emoji 被误判为 quote。
- **统一中文表头** — 三列用中文命名，更贴近 spec 的用户语境，不再需要解释 yaml 字段含义。

## 字段映射

| 旧 yaml 字段 | 新表格列 | 说明 |
|---|---|---|
| `valid` | "有效需求" | ✅ = 仍生效 / ❌ = 已废弃 |
| `testability` | "可测性" | ✅ = 可测 / ⚠️ {原因} = 有保留 / ❌ = 不可测 |
| `resolved` | "是否已决定" | ✅ = 用户已 review 通过 / ⚠️ = 待澄清 / ❌ = 用户明确否决 |

`tools/quote_parser.py` 中的 `COLUMN_ALIASES` 同时接受中文表头和原 yaml 字段名作为列名，便于过渡期混用。

## 影响面

- `templates/spec.md`：FR-010 / FR-020 / NFR-010 全部由 yaml 块改写为表格 + `---`。
- `.specforge/specs/004-quote-dialogue-v0.4/spec.md`：所有 FR/NFR 元数据同步迁移。
- `tests/fixtures/spec-with-quotes.md` 同步迁移（如使用了 yaml 元数据）。
- `tests/test_quote_parser.bats` / `tests/test_spec004_*.bats` 适配新格式。
- `agents/Sage.md`：示例与"yaml resolved"等表述改为"表格元数据 / 是否已决定"。
- 不影响 issue body（仍用 `AC-N: ...` 形式）。
- 不影响 acceptance.md 的 `- AC-N:` 项目符号。

## 备选方案

1. 维持原 YAML 格式 — 痛点未解决。
2. 用 HTML `<table>` 替代 markdown 表格 — markdown 表格更原生且 GitHub / IDE 都已支持。
3. 用单行 `key=value` 形式 — 不易解析，且失去对齐效果。
4. **采用：markdown 表格 + `---` 分隔符**（本决议）。
