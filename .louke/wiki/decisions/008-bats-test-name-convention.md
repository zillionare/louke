# 008 — bats test 名约定：必须 ASCII

- **状态**: 已采纳
- **日期**: 2026-06-25
- **影响**: 6 个 bats 文件 + ~73 个 test 名 + 新增 4 条自动化 guard

## 背景

[v0.5-009-test-cleanup](../project/specs/v0.5-009-test-cleanup/spec.md) 修 test 名时只扫描到 1/7 个中文 bats 文件，剩余 6 个文件 (`test_identity_check`, `test_issue_form`, `test_maestro`, `test_probe`, `test_sage_lex_pr_discussion`, `test_scout_project_board`) 共 73 个测试 **silently skipped** —— bats 解析 `@test "中文..."` 在 `C.UTF-8` / `zh_CN.UTF-8` locale 下会抛 `unknown test name` 后 skip，且只在 stderr 输出一行警告，stdout 的 TAP 计数 (`1..N`) 减少但**不报错**。

[v0.5-010-ASCII-test-names](../project/specs/v0.5-010-ASCII-test-names/spec.md) 把 73 个 test 名改为 ASCII 后，跑出真实基线：

| 文件 | 跑出 | 通过 | 失败 | 失败性质 |
|---|---|---|---|---|
| test_identity_check | 15 | 15 | 0 | — |
| test_issue_form | 37 | 37 | 0 | — |
| test_maestro | 5 | 5 | 0 | — |
| test_probe | 7 | 1 | 6 | pre-existing 功能 bug (Probe.md 缺 gh/UT/背景参考) |
| test_sage_lex_pr_discussion | 8 | 8 | 0 | — |
| test_scout_project_board | 6 | 3 | 3 | pre-existing 功能 bug (Scout.md 缺 check_identity 引用) |
| **合计** | **78** | **69** | **9** | 9 个都是 pre-existing, 非 ASCII 化引入 |

**ASCII 化最大的副产物**：暴露了 9 个之前 silent skip、无人察觉的功能 bug（6 个 Probe.md + 3 个 Scout.md）。这证明 silent skip 本身就是 silent regression。

## 决策

强制要求 bats `@test "..."` 的名称为 ASCII `[a-zA-Z0-9_-:]+`。

### 命名模板

```
@test "<CATEGORY>-<NUMBER>: <lowercase_snake_or_kebab>_<scenario>_<expected_outcome>" {
```

| 部分 | 规则 | 示例 |
|---|---|---|
| CATEGORY | 大写字母 + 短横线分隔 | `CLI`, `ID`, `FORM`, `VERIFY`, `PROBE-FORM`, `LEX-SCHEMA`, `SCOUT-ID` |
| NUMBER | 三位零填充 | `001`, `002`, `100`, `201`, `301` |
| 分隔符 | 英文冒号 + 单空格 | `: ` |
| 描述 | 小写英文 + snake_case / kebab-case | `check_identity_py_exists` |
| 子组 | 简短场景 + 期望 | `offline_two_identities_L4_fail_reject_exit_1` |

### 中文如何保留？

中文不应出现在 test 名中，但**应作为 `## Description` 注释紧随 `@test` 行**：

```bash
@test "ID-200: offline_single_identity_WRITE_role_pass_exit_0" {
    # 离线 - 单一身份 + WRITE 角色 → [通过], exit 0
    run python3 "$SCRIPT" --offline ...
}
```

这样：
- bats 解析器跨 locale/平台稳定（CI runner 任何 locale 都能跑）
- 人类阅读时仍能看到中文语义
- 自动化 linter 可以 grep `@test` 一行做检查（无需解析注释）

### 自动化 guard（v0.5-011 实现）

1. **lint script**: `tools/lint_bats_names.sh`
   - 失败条件：任意 `@test "<NAME>"` 行中 `<NAME>` 含非 ASCII 字节
   - 输出：违规文件 + 行号 + 原 test 名
2. **CI step**: `make lint-bats` 或 `bin/specforge ci-lint`，在 `ci-scan` 之前跑
3. **pre-commit hook**: （可选）开发者本地 commit 前自动 lint
4. **README** 章节: `tests/README.md` 加一节"Bats 测试名约定"

## 备选

### 方案 A：环境变量注入 locale

在 CI runner 的 `~/.bashrc` / Dockerfile 写死 `export LANG=C.UTF-8` 和 `export LC_ALL=C.UTF-8`，让 bats 解析中文 test 名不报错。

**拒绝理由**：
- 不解决 macOS 上用户本地开发 locale 不一致的问题（部分人 macOS 默认 en_US.UTF-8，部分 zh_CN.UTF-8，部分 POSIX）
- CI runner 多为 `C.UTF-8`，但 GitHub Actions macOS runner 是 `en_US.UTF-8` —— 跨平台依然不可控
- 引入 locale 依赖是隐性技术债，不符合"显式优于隐式"

### 方案 B：bats fork / 升级

升级 bats 到支持多字节 test 名的版本，或 fork bats 改解析器。

**拒绝理由**：
- bats 上游不接受 test 名含特殊字符（issue tracker 多次讨论，结论是"用 ASCII"）
- fork 成本远高于改 test 名（73 个文件 < 5 分钟手工 + 30 秒 grep-verify）

### 方案 C：保留中文 + skip 警告显眼化

让 bats 在 silent skip 时输出更明显的警告（exit code 非 0，或 stderr 强制打印）。

**拒绝理由**：bats 上游短期不会改，我们也无法保证所有 CI runner 的 bats 版本都是改过的。最简单稳的方案是测试名用 ASCII，让 silent skip 无发生条件。

## 后果

### 短期（v0.5-010 本次）

- 73 个测试名改为 ASCII
- 6 个 bats 文件新增可读性（人类一眼能扫到哪个 test 是测什么）
- 暴露 9 个 pre-existing 功能 bug，进入 v0.5-011 task-log

### 中期（v0.5-011）

- 加 `tools/lint_bats_names.sh`
- 加 CI step 阻止新中文 test 名入库
- 9 个 pre-existing 失败归类：是 spec 期望过严（v0.5-008 改 Probe/Scout 流程）还是代码缺实现（v0.5-005 漏改 agent），分别 spec 处理

### 长期

- 所有新 bats 文件默认 lint-pass
- 旧的 silent skip bug 模式再不会发生（CI 会拒绝）

## 上游 commit

- v0.5-009: `77b352b` fix(agents+tests): v0.5 收尾 (修了 1/7 个 bats 文件)
- v0.5-010: (本 commit) ASCII 化剩余 6 个 bats 文件

## 相关 spec

- [v0.5-009-test-cleanup](../project/specs/v0.5-009-test-cleanup/spec.md)
- [v0.5-010-ASCII-test-names](../project/specs/v0.5-010-ASCII-test-names/spec.md)
- ADR 007-agent-path-fixup (silent skip + silent bug 同类问题)