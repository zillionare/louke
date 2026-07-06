# fix-002 — project-info.md 迁移 TOML（`project.toml`）

- **Fix ID**: fix-002
- **日期**: 2026-07-06
- **作者**: Kilo (经 Aaron 拍板)
- **状态**: 草稿，实施中
- **关联**:
  - **取代** fix-000（project-info.md history 拆分 + parser bug 修复）—— Aaron 决定直接走 TOML，跳过 fix-000 中间方案
  - **前置** fix-001a（`project-config.toml` 新增 e2e env 配置）—— 仍独立进行；本 fix 不影响
  - **受影响 spec**: v0.6-009, v0.7-001（shipped，需更新引用）+ agent prompts（Scout / Sage / Warden / Archer）

---

## 0. 决策与背景

### 0.1 Aaron 决策

> "直接把 project-info.md 改成 project.toml。最终两个文件，history.md, project.toml。"

### 0.2 fix-000 vs fix-002 对比

| 维度 | fix-000 (作废) | fix-002 (本 fix) |
|---|---|---|
| 当前版本文件 | `project-info.md` (Markdown) | `project.toml` (TOML) |
| 历史文件 | `history.md` (Markdown) | `history.md` (Markdown, 不变) |
| parser | 行级 regex (`- **Label**: value`) | `tomllib.load()` |
| 多行 prose (Story) | 行内一段 | TOML `'''...'''` 三引号 |
| 5 个 caller 改动 | 改成共享 `_common._read_project_info_field` | 同左，调用 tomllib |
| M-MILESTONE 迁移 | current → history, 清空 current | 同样 current → history, 清空 current |

**fix-000 的 parser bug fix 直接被本 fix 涵盖**：tomllib 解析无 first-match 问题。

### 0.3 不需要 fix-000 的原因

fix-000 拆 Markdown 字段 + history.md 后，"first match" 仍然正确（因为只剩一段）。但既然要迁 TOML，**省去 Markdown 中间态**，直接一步到位。

---

## 1. 文件结构

**前**：
```
.louke/project/
├── project-info.md    # 含 4 个 ## vX.Y 段（parser bug）
├── history.md         # 不存在
└── specs/
```

**后**：
```
.louke/project/
├── project.toml       # 当前版本（TOML, 单文件）
├── history.md         # 归档版本（Markdown, 多段）
└── specs/
```

---

## 2. project.toml Schema

```toml
# .louke/project/project.toml
# 当前活跃版本的元信息. 由 Scout M-FOUND 初始化, Maestro / Lex / Sage 读.
# 历史版本在 history.md (Markdown, agent 不解析).

[project]
version = "0.7"
repo = "github.com/zillionare/louke"
project = "louke-v0.7 (#8)"
project_id = "https://github.com/users/quantclaws/projects/8"
spec_id = "v0.7-002-knowledge-distillation-karpathy"
release_branch = "releases/v0.7"

[meta]
created = "2026-07-05"
tag = "v0.7.0 (zillionare/louke@v0.7.0)"
security_audit = "disabled"
smoke_test_issue = "#80 (closed, previous v0.6 milestone 冒烟)"

# Story / 备注等多行文本用 TOML 三引号
story = """
pre-commit 接管 lint/format/typecheck/test + R-G-R Red 去 commit + Keeper 瘦到 R-G-R/format/AC trace/反模式 + 知识蒸馏 Karpathy 化（cron 触发 raw → pages 重写）.
"""

[meta.known_carryover]
# 自由格式字段, 不被 parser 解析 (parser 只读 [project] / [meta] 顶层 key)
dirty_files = "louke 工作树里有 ~70 个 pre-existing dirty 文件 (agents/ 目录迁移、Makefile 删除等), 跟当前 spec 无关"
project_owner = "Project `louke-v0.7` (#8) owner 是 quantclaws (gh auth 限制), zillionare 已加 ADMIN"
commit_rgr = "`lk agent devon commit-rgr` 当前版本要求 `--task-id` 参数, 后续 v0.7+ 应去掉以保持 R-G-R commit 格式干净"
```

**字段语义**（由谁读）：

| 字段 | 写入者 | 读取者 |
|---|---|---|
| `[project].version` | Scout M-FOUND | Sage / Lex / Warden |
| `[project].repo` | Scout | Sage / Lex (`--repo` 默认) |
| `[project].project_id` | Scout | Sage (`gh project item-add`) |
| `[project].spec_id` | Scout + Sage | Lex / Warden |
| `[project].release_branch` | Scout | Lex (`--branch` 默认) |
| `[meta].security_audit` | 用户（Scout / Warden 写入 'enabled' / 'disabled'） | Warden F6 |
| `[meta].smoke_test_issue` | Scout | Warden F3 |
| `[meta].known_carryover.*` | Scout | 人类查阅（agent 不解析） |
| `[meta].tag`, `created` | Scout | 人类 + Librarian (wiki 引用) |

---

## 3. history.md 保持 Markdown（不动）

历史版本 prose 多（Story / Implementation / Known carryover），Markdown 仍然合适。**agent 不解析 history.md**（仅人类查阅）。

```markdown
# Project History (Archived Versions)

> 由 M-MILESTONE 收尾触发，Maestro 把 `project.toml` 内容追加到此文件。
> agent 不解析此文件（仅人类查阅）。

## v0.7 (2026-07-05) — pre-commit + 知识蒸馏

[archived from project.toml, formatted as Markdown for readability]
```

---

## 4. 实施变更

### 4.1 创建 `project.toml`

见 §2 schema。

### 4.2 重写 5 个 parser（统一指向 `project.toml`）

| 文件 | 改动 |
|---|---|
| `louke/_common.py` | `_read_project_info_field(label)` 改用 tomllib；新增 `_read_project_info_all()` 返回 dict |
| `louke/maestro.py` | 删除 `_read_project_info`，改 import `_common._read_project_info_field` |
| `louke/lex.py` | 删除本地 `_read_project_info`，改 import |
| `louke/sage.py` | 删除 `_read_project_info_value`，改 import |
| `louke/scout.py` | `_read_project_info(path)` 改用 `_common._read_project_info_all()`，写文件用 tomllib 或文本拼接（TomlLibW 不在 stdlib，**写用文本** 或用 `tomli_w`） |
| `louke/verify_acceptance.py` | (若存在) 类似重构 |

**Scout 写 project.toml 的实现要点**：

```python
def _write_project_info(path: Path, fields: dict) -> None:
    """写 project.toml. 用手写 TOML（避免 tomli_w 依赖）."""
    lines = []
    sections = {
        'project': ['version', 'repo', 'project', 'project_id', 'spec_id', 'release_branch'],
        'meta': ['created', 'tag', 'security_audit', 'smoke_test_issue'],
    }
    for section, keys in sections.items():
        section_lines = [f'[{section}]']
        for k in keys:
            if k in fields:
                v = fields[k]
                if '\n' in v:
                    section_lines.append(f'{k} = """')
                    section_lines.append(v)
                    section_lines.append('"""')
                else:
                    section_lines.append(f'{k} = "{v}"')
        lines.append('\n'.join(section_lines) + '\n')
    path.write_text('\n'.join(lines))
```

### 4.3 更新 agent prompts

| Agent | 当前 | 改 |
|---|---|---|
| `Scout.md` | "记录到 project-info.md" | "记录到 project.toml" |
| `Sage.md` | "上一阶段产生的 .louke/project/project-info.md" | "上一阶段产生的 .louke/project/project.toml" |
| `Sage.md` L290-291 bash | `grep -E '^\- \*\*Project ID\*\*' project-info.md` | `tomlq -r .project.project_id project.toml` 或 python one-liner |
| `Archer.md` L125 | "project info (.louke/project/project-info.md)" | "project info (.louke/project/project.toml)" |
| `Archer.md` L135 | ".louke/project/project-info.md" | ".louke/project/project.toml" |
| `Warden.md` L44 (F6) | "project-info.md 包含必须字段: Version, Repo, Project, Spec ID, Release Branch" | "project.toml 包含 [project] 段必填字段: version, repo, project, spec_id, release_branch" |

### 4.4 更新 shipped specs（v0.6-009, v0.7-001）

这些 spec 已 shipped，但需更新引用：

| Spec | 位置 | 改动 |
|---|---|---|
| `v0.6-009-agent-permission-tightening/spec.md` L138 | "查 project-info.md 的 Stage 字段" | "查 project.toml 的 [meta].current_stage 字段" (注：旧文案 Stage 字段实际不存在，修正为 Current Stage → current_stage) |
| `v0.7-001-pre-commit-quality-gates/spec.md` L177 | "记录到 project-info.md: Pre-commit: installed (..." | "记录到 project.toml: [meta].pre_commit = 'installed (python + base)'" |
| `v0.7-001-pre-commit-quality-gates/test-plan.md` L15, 207, 248 | 3 处 "project-info.md" | 改为 "project.toml" + 字段名 |
| `v0.7-001-pre-commit-quality-gates/architecture.md` L44 | "写 project-info.md Pre-commit 字段" | "写 project.toml [meta].pre_commit 字段" |
| `v0.7-001-pre-commit-quality-gates/interfaces.md` L24, 127, 205, 227 | 4 处 | 改为 "project.toml [meta].pre_commit" |
| `v0.7-001-pre-commit-quality-gates/acceptance.md` AC-6 | "project-info.md 含 Pre-commit: installed (...) 字段" | "project.toml [meta].pre_commit = 'installed (python + base)'" |

### 4.5 删除 `project-info.md`

迁完后删除 `project-info.md`，避免歧义。

### 4.6 更新 Maestro.md

新增 M-MILESTONE 收尾触发：把 `project.toml` 当前内容追加到 `history.md`，清空 `project.toml`。

---

## 5. 兼容性

**Breaking**：
- `_read_project_info(label)` 返回空字符串 if 项目没迁 (过渡期)
- 已 ship 项目 (v0.7.0) 不需要回滚 —— 升级 louke 后 Scout 写新格式

**迁移路径**：
- 升级 louke 到含本 fix 的版本
- 跑 `lk migrate project-info-toml`（待实现）：把现有 `project-info.md` 自动转 `project.toml` + `history.md`
- 一次性迁移，存量项目不需手工

---

## 6. 验证

| 场景 | 预期 | 验证方式 |
|---|---|---|
| `_read_project_info_field('version')` 返回 '0.7' | ✓ | fixture: tmp dir + 写 project.toml |
| `_read_project_info_field('repo')` 返回 louke URL（不是 v0.1 specforge URL） | ✓ | 回归 bug |
| 5 个 caller 行为不变 | ✓ | 跑所有 `lk` 子命令 smoke test |
| M-MILESTONE 触发迁移 | project.toml 内容追加到 history.md，project.toml 重置 | fixture |
| Warden F6 检查通过 | `[project]` 段含 version/repo/project/spec_id/release_branch | 跑 `lk warden check-f6` |
| 缺失 project.toml | parser 返回空字符串，不报错 | fixture: tmp dir 无文件 |

---

## 7. 实施步骤

1. **Step 1**: 写本设计文档（本文件）
2. **Step 2**: 更新 shipped specs（v0.6-009, v0.7-001）—— 6 个文件
3. **Step 3**: 创建 `project.toml`（v0.7 字段）
4. **Step 4**: 重写 5 个 parser 到 `_common.py`
5. **Step 5**: 更新 agent prompts（Scout / Sage / Warden / Archer）
6. **Step 6**: 更新 Warden F6 check
7. **Step 7**: end-to-end 验证
8. **Step 8**: 删除 `project-info.md`
9. **Step 9**: 更新 Maestro.md（M-MILESTONE 迁移）

---

## 8. 与其他 fix / spec 关系

| fix / spec | 关系 |
|---|---|
| `fix-000-project-info-history` | **取代**。本 fix 是 fix-000 的"超集"：直接 TOML，parser bug 同时消失 |
| `fix-001a-e2e-env-contract` | **正交**。fix-001a 新增 `project-config.toml` 是 e2e 配置；本 fix 把 `project-info.md` 改 `project.toml`。两个 TOML 文件共存 |
| `v0.6-009-agent-permission-tightening` | 本 fix 更新 L138 引用 |
| `v0.7-001-pre-commit-quality-gates` | 本 fix 更新多处引用 |
| `v0.6-016-quote-dialogue-protocol` | 不涉及 |

---

## 9. 待 review 问题

1. **TOML 三引号跨平台**：TOML `"""..."""` 字符串保留换行（vs `'''...'''` 不保留换行）。多行 Story 用哪种？
2. **scout 写 TOML 用 `tomli_w` 还是手工构造**：倾向手工（无新依赖，与 v0.7-001 一致）；如有 pyproject.toml 已有 `tomli` 可加 `tomli_w`
3. **history.md 格式**：archived project 内容是从 TOML 转 Markdown 还是直接贴 TOML？
4. **M-MILESTONE 触发时机**：当前 `lk maestro advance --stage M-MILESTONE` 触发（Maestro.md L130）？还是在 Librarian 蒸馏完成后自动触发？
5. **缺失字段处理**：project.toml 字段缺失时 parser 返回空 vs 抛错？倾向空（兼容 Warden F6 必须字段显式列出）