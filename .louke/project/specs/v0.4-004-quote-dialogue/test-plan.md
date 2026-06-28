# TEST-004-quote-dialogue-01 — 测试计划

## 测试环境

- **framework**: specforge 自身
- **runtime**: Python 3 stdlib (no third-party deps)
- **test framework**: bats
- **fixtures**: `tests/fixtures/spec-with-quotes.md` (reference fixture)
- **self-dogfood**: `.specforge/project/specs/v0.4-004-quote-dialogue/spec.md` (parseable by parser, validated by QP_T16)
- **隔离**: 每个 UT 在 `mktemp -d` 创建临时目录, teardown 删除

## 可追溯矩阵

| Issue # | 需求 ID | 单元测试用例 | 集成测试用例 | 状态 |
|---------|---------|-------------|-------------|------|
| 待 Lex 创建 | FR-016 quote 嵌套深度 | UT-016-1-1, UT-016-1-2, UT-016-2-1 | IT-001 | open |
| 待 Lex 创建 | FR-017 状态 marker | UT-017-1-1, UT-017-2-1, UT-017-3-1, UT-017-4-1 | IT-002 | open |
| 待 Lex 创建 | FR-018 quote_parser | UT-018-1-1..18-1-7 (对应 QP_T01..QP_T18) | IT-001 | open |
| 待 Lex 创建 | FR-019 git diff | UT-019-1-1..19-1-5 (对应 GD_T01..GD_T05) | IT-003 | open |
| 待 Lex 创建 | FR-020 silent vs proactive | UT-020-1-1 (默认 silent) | — | open |
| 待 Lex 创建 | FR-021 Sage.md 重写 | UT-021-1-1 (无 gh api 调用) | — | open |
| 待 Lex 创建 | FR-022 Lex.md 重写 | UT-022-1-1 (无 gh api reviews) | — | open |
| 待 Lex 创建 | FR-023 README §2.2 改写 | UT-023-1-1 (含 IDE 流程示例) | — | open |
| 待 Lex 创建 | FR-024 嵌套深度 ≥ 3 | UT-024-1-1 (fixture 中包含) | IT-001 | open |
| 待 Lex 创建 | FR-025 代码块排除 | UT-025-1-1 (QP_T08 验证) | — | open |
| 待 Lex 创建 | FR-026 pending 全 resolved 才 Approve | UT-026-1-1 (--check-ready exit 0) | — | open |
| 待 Lex 创建 | FR-027 chat 用途 | (无需自动测试, docstring 验证) | — | open |
| 待 Lex 创建 | FR-028 Scout→Sage 契约 | (Aaron 待定, [wontfix] 状态) | — | suspended |
| 待 Lex 创建 | FR-029 Scout 输出 story.md | (Aaron 待定, [wontfix] 状态) | — | suspended |

## 单元测试

### Issue 待 Lex 创建 — FR-016: quote 嵌套深度

#### AC-1: quote 嵌套深度 ≥ 3
##### UT-016-1-1: 嵌套深度 3 解析
- 输入: 包含 `>>>` 三层 quote 的 fixture
- 预期: depth_histogram["3"] = 1
- 覆盖分支: QP_T06

##### UT-016-1-2: 嵌套深度 4 解析
- 输入: 包含 `>>>>` 四层 quote 的 fixture
- 预期: depth_histogram["4"] = 1
- 覆盖分支: QP_T07

#### AC-2: 任意方都可发起追问
##### UT-016-2-1: depth-1 quote 可以是用户 (Aaron 在 IDE 中已示范)
- 输入: 深度 1 quote, speaker=Aaron
- 预期: 解析成功
- 覆盖分支: 用户身份识别 (Aaron: "一段评论是谁的, 关于取决于 '>' 后面接的用户名")

### Issue 待 Lex 创建 — FR-017: 状态 marker (pending-default)

#### AC-1: 默认无标记 = pending
##### UT-017-1-1: 无标记 quote 解析为 open
- 输入: `> **Sage:** ...` (无状态 marker)
- 预期: status="open"
- 覆盖分支: QP_T17

#### AC-2: ✓ resolved 显式标记
##### UT-017-2-1: 显式 ✓ resolved
- 输入: `> **Sage:** ... ✓ resolved`
- 预期: status="resolved"
- 覆盖分支: QP_T18 + 已有 fixture

#### AC-3: [blocked-by-N] / [wontfix] / [superseded]
##### UT-017-3-1: blocked-by 检测
- 输入: `... [blocked-by-001]`
- 预期: blocked_by=1, status="blocked"

##### UT-017-4-1: wontfix / superseded
- 输入: 各 1 例
- 预期: 对应状态

### Issue 待 Lex 创建 — FR-018: quote_parser 接口

#### AC-1: 解析返回结构化数据
- 覆盖: QP_T01 (基本解析), QP_T02 (open 数), QP_T03 (resolved 数), QP_T04 (is_ready), QP_T05 (--check-ready exit 1), QP_T06/T07 (depth), QP_T08 (code fence), QP_T09 (blocked_by), QP_T10/T14 (empty spec), QP_T11 (speakers), QP_T12 (JSON), QP_T13 (missing file), QP_T15 (list markers), QP_T16 (self-parse spec 004)

### Issue 待 Lex 创建 — FR-019: git diff 触发

#### AC-1: git_diff_quote_resolver 实现
- 覆盖: GD_T01..GD_T05 (5 cases)

### Issue 待 Lex 创建 — FR-020: 用户改原文段落 = silent

#### AC-1: 默认 silent
##### UT-020-1-1: 用户修改 spec.md 原文不触发新 quote
- 输入: 用户编辑 FR 描述, 不增加 quote
- 预期: Sage 不主动追问 (默认行为)
- 覆盖分支: 由 FR-020 文档约束, 无需自动测试

### Issue 待 Lex 创建 — FR-021: Sage.md 重写 (无 gh api)

#### AC-1: Sage.md 不含 gh api 调用
##### UT-021-1-1: grep Sage.md 无 `gh api pulls`
- 输入: Sage.md 文件
- 预期: 0 匹配

### Issue 待 Lex 创建 — FR-022: Lex.md 重写 (无 gh api reviews)

#### AC-1: Lex.md 不含 gh api reviews
##### UT-022-1-1: grep Lex.md 无 `gh api.*reviews`
- 输入: Lex.md 文件
- 预期: 0 匹配

### Issue 待 Lex 创建 — FR-023: README §2.2 改写

#### AC-1: README §2.2 含 IDE 流程
##### UT-023-1-1: grep README "IDE" + "quote"
- 输入: README.md
- 预期: ≥ 1 匹配

### Issue 待 Lex 创建 — FR-024: 嵌套深度 ≥ 3
- 覆盖: UT-016-1-1

### Issue 待 Lex 创建 — FR-025: 代码块排除
- 覆盖: QP_T08

### Issue 待 Lex 创建 — FR-026: pending gate

#### AC-1: --check-ready exit 0 when all resolved
- 覆盖: QP_T10 + QP_T14

### Issue 待 Lex 创建 — FR-027: chat 用途
- 覆盖: 文档约束, 无自动测试

## 集成测试

### IT-001: 完整 quote 流程 (FR-016 + FR-018 + FR-024)
- 涉及 FR-016/018/024
- 前置: 准备临时 git repo with story.md + spec.md
- 操作:
  1. Sage 启动 → 读取 story.md (FR-028 scenario) → 写 spec.md
  2. 用户在 IDE 编辑 spec.md (改 quote 状态 + 改原文)
  3. Sage `git diff` 解析 (FR-019 + FR-020)
  4. Lex 读 spec.md (FR-022 + FR-026)
- 期望: 全程无 gh api 调用, 全程 git 操作本地完成

### IT-002: 状态 marker 持久化 (FR-017)
- 涉及 FR-017
- 操作: 写 spec.md 含 3 个 quote (resolved/open/wontfix), commit, re-parse
- 期望: 三种状态都正确解析

### IT-003: git diff 触发 (FR-019)
- 涉及 FR-019
- 操作: 同 GD_T01-T05, 但用真实 spec 004
- 期望: --check-ready 在 [open] 消失后 exit 0

## 视觉/E2E

不适用 (CLI 工具, 无 UI)

## 退出条件

- [x] 测试计划文档已生成
- [x] 每个 issue 每条 AC 都有 UT
- [x] 跨 issue 场景有 IT
- [x] 可追溯矩阵完整
- [x] 测试环境要求已说明

## 备注

- FR-028/FR-029 状态: [wontfix] in spec.md L170/L174. 不创建 issue, 待 Aaron 后续指示。
- FR-027 (chat 用途): 是文档约束, 无自动测试, 通过 reviewer 检查。
- Aaron 的 IDE 修正记录在 spec.md quote dialogue 里, 是流程示范的一部分。