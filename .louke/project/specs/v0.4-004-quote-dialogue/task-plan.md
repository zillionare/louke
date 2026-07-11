# TASK-004-quote-dialogue-01 — 执行规划

## 版本与分支

- **版本号**: v0.4.0 (minor bump)
- **spec-id**: 004
- **任务分支命名**: `feat/004/TASK-{序号}`

## 架构分析

```
bin/specforge                    [unchanged, 仅工具入口]
agents/Sage.md                   [rewrite §2.2 章节, 删 PR inline comment 流程]
agents/Lex.md                    [rewrite §2, 改用 quote 状态]
agents/Maestro.md                [minimal update, gate 改用 quote_parser --check-ready]
agents/Scout.md                  [unchanged in this spec, FR-028/029 suspended]
tools/quote_parser.py            [DONE: 18 bats tests GREEN]
tools/git_diff_quote_resolver.py [DONE: 5 bats tests GREEN]
tests/test_quote_parser.bats     [DONE]
tests/test_git_diff_resolver.bats [DONE]
README.md                        [rewrite §2.2]
specs/v0.4-004-quote-dialogue/         [DONE: spec.md + test-plan.md]
```

## 任务列表

### TASK-01: Sage.md §2.2 重写

- 关联 issue: 待 Lex 创建 FR-016/017/018/020/021
- 关联 spec: 003 FR-016~020, FR-027
- 关联测试: UT-021-1-1 (无 gh api 调用)
- 分支: `feat/004/TASK-01`
- 描述:
  - 删除 Step 4 (gh api 创建 inline comment)
  - 删除 Step 5 (gh api 拉取 PR comments)
  - 重写为 IDE-based 流程: chat 通知 → 用户在 IDE 编辑 → 用户 chat 说"review 完了" → Sage `git diff` 解析 → Sage 据此追问
  - 新增 "触发机制" 章节: 用户在 chat 说"review 完了" 或 "continue"
  - 移除 `gh pr create`, `gh pr merge`, `gh api` 所有调用
- 依赖: 无
- 可并行: 是 (与 TASK-02 平行)

### TASK-02: Lex.md 重写

- 关联 issue: 待 Lex 创建 FR-022/FR-026
- 关联 spec: FR-022/FR-026
- 关联测试: UT-022-1-1 (无 gh api reviews)
- 分支: `feat/004/TASK-02`
- 描述:
  - 删除 "Stage 1: Spec 审核 (通过 GitHub PR Review)" 章节
  - 重写为: 读 spec.md, 运行 `tools/quote_parser.py --check-ready`
  - exit 0 → Approve, exit 1 → 在 spec.md 加 [open] quote 列出缺失项
  - 移除 `gh api reviews` 调用
- 依赖: 无
- 可并行: 是 (与 TASK-01 平行)

### TASK-03: README §2.2 改写

- 关联 issue: 待 Lex 创建 FR-023
- 关联 spec: FR-023
- 关联测试: UT-023-1-1 (grep README 含 IDE + quote)
- 分支: `feat/004/TASK-03`
- 描述:
  - 整段重写 §2.2 章节
  - 用 IDE-based 流程替代 PR Review 流程
  - 加 markdown quote 示例 (引用 spec 004 的 markdown 示例)
  - 旧 PR 流程作为附录 ("参见历史 spec 001-003")
- 依赖: TASK-01 完成 (引用 Sage.md 改写后的章节)
- 可并行: 否

### TASK-04: Maestro.md 适配

- 关联 issue: 待 Lex 创建 FR-026 (gating)
- 关联 spec: FR-026
- 关联测试: bats test for gate (TBD)
- 分支: `feat/004/TASK-04`
- 描述:
  - Lex 阶段触发信号: PR merged → spec.md is_ready (quote_parser --check-ready)
  - 移除 "PR merged" 事件触发
- 依赖: TASK-01 (Sage.md) + TASK-02 (Lex.md)
- 可并行: 否

### TASK-05: 集成测试 + 回归保护

- 关联 issue: FR-016/017/018/019/020/021/022/023/024/025/026
- 关联 spec: test-plan.md §IT-001/IT-002/IT-003
- 关联测试: IT-001/IT-002/IT-003
- 分支: `feat/004/TASK-05`
- 描述:
  - bats tests/test_spec_forge_ide_flow.bats (新): IT-001/IT-002/IT-003
  - 验证既有 tests/test_init.bats / test_init_adopt_*.bats 全部通过
- 依赖: TASK-01..04
- 可并行: 否

## 执行顺序

```
Week 1:
  Day 1: TASK-01 ∥ TASK-02 ∥ TASK-03 ∥ TASK-04 (parallel, all touch different files)
  Day 2: TASK-05 (integration + regression)
  Day 3: Keeper + Herald + Arbiter
```

## 依赖图

```
TASK-01 ─┬─> TASK-05
TASK-02 ─┤
TASK-03 ─┤
TASK-04 ─┘
```

## 编号说明

| FR | 来源 | 状态 |
|---|---|---|
| FR-016 | 本 spec | 实施 |
| FR-017 | 本 spec | 实施 |
| FR-018 | 本 spec | 工具已实现, 测试覆盖 |
| FR-019 | 本 spec | 工具已实现, 测试覆盖 |
| FR-020 | 本 spec | 实施 (silent 默认) |
| FR-021 | 本 spec | 实施 |
| FR-022 | 本 spec | 实施 |
| FR-023 | 本 spec | 实施 |
| FR-024 | 本 spec | 实施 |
| FR-025 | 本 spec | 工具已实现 (代码块排除) |
| FR-026 | 本 spec | 实施 (pending 全 resolved gate) |
| FR-027 | 本 spec | 实施 (文档约束) |
| FR-028 | 本 spec | **suspended** ([wontfix] 状态, 待 Aaron 后续) |
| FR-029 | 本 spec | **suspended** ([wontfix] 状态, 待 Aaron 后续) |

## 退出条件

- [x] 版本号和分支已确定 (v0.4.0, feat/004/TASK-{01-05})
- [x] 每条任务关联测试用例编号
- [x] 执行顺序已确定
- [x] 可并行任务已标注
- [x] FR-028/029 suspended 状态已记录

## 反模式检查

- ✅ 每个 TASK 有 issue# 关联
- ✅ 每个 TASK 有 UT/IT 关联
- ✅ 每个 TASK 描述具体, 不模糊
- ✅ 依赖关系清晰, 无循环
- ✅ 并行任务已标注
