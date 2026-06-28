# v0.5-010 — bats test 名 ASCII 化 — Spec

- **Spec ID**: v0.5-010-ASCII-test-names
- **创建日期**: 2026-06-25
- **状态**: 草稿
- **关联**: v0.5-009-test-cleanup（修了 1/7 个 bats 文件）

## 背景

[v0.5-009-test-cleanup](v0.5-009-test-cleanup/spec.md) 顺手把 `tests/test_specforge_cli.bats` 的 31 个中文 test 名改为 ASCII ID（绕开 bats 多字节 test 名字符编码 bug）。但当时只扫到一个文件，剩余 6 个 bats 文件有同类问题：

| 文件 | 实际运行 | 期望 | 缺口 | 中文 test 名 |
|---|---|---|---|---|
| `test_identity_check.bats` | 0 | 15 | -15 | 15 |
| `test_issue_form.bats` | 0 | 37 | -37 | 37 |
| `test_maestro.bats` | 0 | 5 | -5 | 5 |
| `test_probe.bats` | 0 | 7 | -7 | 7 |
| `test_sage_lex_pr_discussion.bats` | 2 | 8 | -6 | 6 |
| `test_scout_project_board.bats` | 3 | 6 | -3 | 3 |
| **合计** | **5** | **78** | **-73** | **73** |

这 73 个测试**实际根本没跑**（bats 在解析 `@test "中文..."` 时抛 `unknown test name` 然后 skip），CI 基线不可信。任何这些文件里的功能 bug 都不会被捕获。

**漏检原因**：v0.5-009 全量回归时，bats 在 `tests/*.bats` glob 下读 23 个文件，218 个测试"执行了"，但其中 ~73 个是 silent skip。如果不是逐文件看 bats warning "Executed N instead of expected M"，根本察觉不到。

## 目标

1. 把 6 个 bats 文件中所有 `@test "中文..."` 改为 `@test "<ID>: <english_id> <short_desc>"` 形式
2. 跑全量 bats 验证 0 回归（除 v0.5-009 已记录的两类 pre-existing 失败）
3. bump VERSION 0.5.4 → 0.5.5
4. 在 `.specforge/wiki/decisions/` 补一条"bats test 名约定"小 ADR 或在 README 写明"test 名应为 ASCII"

## 非目标

- 不修测试**逻辑**（即便有失败，也只动 test 名）
- 不引入 bats locale 修复（env 配置）
- 不动 v0.5-009 已修的 `test_specforge_cli.bats`
- 不动其它 16 个 bats 文件（已经 ASCII 化或无中文 test 名）

## 用户故事

### US-010
story: 作为 specforge 维护者，我希望 `bats tests/*.bats` 真的跑 280+ 个测试，而不是被中文 test 名吃掉 73 个，以便 CI 基线可信。
priority: P0

### US-020
story: 作为 specforge 用户，我希望 `bats tests/test_identity_check.bats` 等能真正验证 `check_identity.py` 的行为（online/offline L1-L5 全跑），而不是空跑 0 个测试。
priority: P0

## 功能需求

### FR-010 test_identity_check.bats 15 个 ASCII 化

文件: `tests/test_identity_check.bats`
影响 test 名 (sample): `ID-001: check_identity.py 存在` → `ID-001: check_identity_py_exists`

AC: `bats tests/test_identity_check.bats` 实际跑数 ≥ 15，不再出现 "unknown test name"。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

### FR-020 test_issue_form.bats 37 个 ASCII 化

文件: `tests/test_issue_form.bats`
影响 test 名 (sample): `FORM-001: feature.yml 文件存在` → `FORM-001: feature_yml_exists`

AC: `bats tests/test_issue_form.bats` 实际跑数 ≥ 37。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

### FR-030 test_maestro.bats 5 个 ASCII 化

文件: `tests/test_maestro.bats`

AC: `bats tests/test_maestro.bats` 实际跑数 ≥ 5。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

### FR-040 test_probe.bats 7 个 ASCII 化

文件: `tests/test_probe.bats`

AC: `bats tests/test_probe.bats` 实际跑数 ≥ 7。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

### FR-050 test_sage_lex_pr_discussion.bats 6 个 ASCII 化

文件: `tests/test_sage_lex_pr_discussion.bats`

AC: `bats tests/test_sage_lex_pr_discussion.bats` 实际跑数 ≥ 8（之前 2 个 ASCII + 6 个中文 = 8）。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

### FR-060 test_scout_project_board.bats 3 个 ASCII 化

文件: `tests/test_scout_project_board.bats`

AC: `bats tests/test_scout_project_board.bats` 实际跑数 ≥ 6。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

### FR-070 命名约定文档化

在 `.specforge/wiki/decisions/008-bats-test-name-convention.md` 写明：
- bats test 名建议用 ASCII (`[a-z0-9_-:]`)
- 中文描述可作为 `## Description` 注释紧随 `@test` 行
- locale 不可控（CI runner 多为 `C.UTF-8`），多字节名字无法保证跨平台一致

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

### FR-080 跑全量 bats 0 新回归 + bump VERSION

- `bats tests/*.bats` 跑 280+ 测试（不再 silent skip 73 个）
- 已记录的 pre-existing 失败 (`test_branch_naming.bats` BRANCH-* × 6, `test_verify_acceptance.bats` VA-T02/T07) 不在本 spec 修复范围
- 新发现的失败若非字符编码问题，进入 `task-log.md` 留待下个 spec

AC:
- `bats tests/*.bats 2>&1 | grep "Executed N instead"` 输出为空（无 silent skip）
- VERSION = 0.5.5

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

## 验收标准

| ID | 描述 | 验证方法 |
|---|---|---|
| AC-010 | 6 个 bats 文件的所有中文 test 名被替换为 ASCII ID | `grep -rn '@test "[^"]*[^\x00-\x7f]' tests/` 输出为空（除个别允许的非 ASCII 注释） |
| AC-020 | bats 不再 silent skip 任何测试 | `bats tests/*.bats 2>&1 \| grep "Executed N instead"` 为空 |
| AC-030 | 全量 bats 无新失败 | 对比 v0.5-009 baseline，失败数 = v0.5-009 baseline（不增加） |
| AC-040 | VERSION 已 bump | `cat VERSION` = `0.5.5` |
| AC-050 | ADR 008 已写 | `.specforge/wiki/decisions/008-bats-test-name-convention.md` 存在 |
| AC-060 | 已 commit | `git log -1 --format=%s` 含 `v0.5-010` |

## 风险

- **R-010** 改 test 名可能引入复制粘贴错位（test ID 与断言行不对应） → 用 `bats --print-output-on-failure` 逐文件验证
- **R-020** 某些中文 test 名含 sub-assertion 描述（例："离线 - WRITE 通过 [通过], exit 0"），ASCII 化时需保留语义 → ID 用 `<scenario>_<expected_outcome>` 模板
- **R-030** 中文 ID 改 ASCII 后丢失人类可读性 → 在 `@test` 行后留中文注释作为 `## Description`

## 任务拆解

```
1. 写 ADR 008 (bats test name convention)
2. 改 test_identity_check.bats (15)
3. 改 test_issue_form.bats (37)
4. 改 test_maestro.bats (5)
5. 改 test_probe.bats (7)
6. 改 test_sage_lex_pr_discussion.bats (6)
7. 改 test_scout_project_board.bats (3)
8. 跑全量 bats 验证 0 新回归
9. bump VERSION 0.5.4 → 0.5.5
10. commit + tag v0.5.5
```