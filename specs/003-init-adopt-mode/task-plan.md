# TASK-003-init-adopt-mode-01 — 执行规划

## 版本与分支

- **版本号**: v0.3.0 (minor bump)
- **spec-id**: 003
- **任务分支命名**: `feat/003/TASK-{序号}` （按 specforge §2.5 约定）

## 架构分析

### 模块边界

```
bin/specforge
├── helpers
│   ├── die(), note()              ← 已有
│   ├── resolve_python()           ← 已有
│   └── is_existing_path()         ← [新] FR-008 路径检测
├── subcommands
│   ├── cmd_version()              ← 已有
│   ├── cmd_help()                 ← 已有
│   ├── cmd_init()                 ← [改] 智能检测 + 分流到 init_new / init_adopt
│   ├── cmd_init_new()             ← [新] 抽出原 init 逻辑
│   ├── cmd_init_adopt()           ← [新] adopt 模式主入口
│   ├── cmd_init_adopt_dry_run()   ← [新] FR-012 dry-run 包装
│   ├── cmd_init_adopt_report()    ← [新] FR-013 分档报告生成
│   └── ...
tests/test_init.bats               ← [改] 加 35 UT + 5 IT
README.md                           ← [改] §8.3 文档
agents/README.md                   ← [改] init 章节
```

### 依赖关系

```
TASK-01 (helpers + 检测) ──┐
                            ├──> TASK-04 (集成 + IT-001/002/005)
TASK-02 (init_adopt 主体) ─┤
                            ├──> TASK-05 (.gitignore + FR-014)
TASK-03 (报告函数) ────────┘
```

## 任务列表

### TASK-01: 路径检测 helper + 子命令框架

- **关联 issue**: #27 (FR-008)
- **关联 spec**: 003-init-adopt-mode §FR-008
- **关联测试**: UT-027-1-1, UT-027-2-1, UT-027-3-1, UT-027-4-1, UT-027-5-1
- **分支**: `feat/003/TASK-01`
- **描述**:
  - 新增 `is_existing_path()` 函数：检测参数是否含 `/`、以 `.` 开头、以 `~` 开头
  - 重构 `cmd_init`：检测后分发到 `cmd_init_new` (原逻辑) 或 `cmd_init_adopt` (新逻辑)
  - 保持 `tests/test_init.bats` 全部既有 UT 通过
- **依赖**: 无
- **可并行**: 是

### TASK-02: adopt 模式主体逻辑

- **关联 issue**: #28 (FR-009), #29 (FR-010), #30 (FR-011), #34 (FR-015)
- **关联 spec**: 003-init-adopt-mode §FR-009, §FR-010, §FR-011, §FR-015
- **关联测试**: UT-028-*, UT-029-*, UT-030-*, UT-034-*
- **分支**: `feat/003/TASK-02`
- **描述**:
  - 实现 `cmd_init_adopt`:
    1. 验证目标是 git repo (FR-015 / UT-034-1-1) — 不是则报错并提示 `git init`
    2. 跳过 mkdir 阶段，直接按目录清单处理 (FR-010)
    3. 对 agents/*.md 和 templates/*.md 应用 skip/backup/force 策略 (FR-011)
    4. 全部过程不得触碰 .git/ 和源代码区 (FR-009)
  - 命令行参数解析: `--backup` `--force` `--dry-run` `--with-issue-template` `--json` `--no-gitignore`
- **依赖**: TASK-01 (需要路径检测)
- **可并行**: 否 (阻塞 TASK-04)

### TASK-03: 分档报告函数

- **关联 issue**: #32 (FR-013)
- **关联 spec**: 003-init-adopt-mode §FR-013
- **关联测试**: UT-032-1-1, UT-032-2-1, UT-032-3-1, UT-032-4-1
- **分支**: `feat/003/TASK-03`
- **描述**:
  - 实现 `cmd_init_adopt_report`：从 adopt 过程收集 (path, status) 元组
  - 输出格式: `[+] newpath` / `[=] skipped` / `[!] backed_up`
  - 排序: `[+]` → `[=]` → `[!]`，各组内按 path 字典序
  - 末尾汇总: `N 个新文件, M 个跳过, K 个备份`
  - `--json` flag 时输出 JSON
- **依赖**: TASK-01 (函数签名)
- **可并行**: 是 (与 TASK-02 并行; 但 merge 时需协调)

### TASK-04: 集成测试 + 回归保护

- **关联 issue**: #34 (FR-015 兼容性)
- **关联 spec**: 003-init-adopt-mode §IT-001, §IT-002, §IT-003, §IT-005
- **关联测试**: IT-001, IT-002, IT-003, IT-005
- **分支**: `feat/003/TASK-04`
- **描述**:
  - 编写 IT-001: 真实 Python 项目端到端 adopt
  - 编写 IT-002: dry-run 幂等性
  - 编写 IT-003: 三策略冲突矩阵
  - 编写 IT-005: bats tests/test_init.bats + tests/test_specforge_cli.bats 全部通过
- **依赖**: TASK-02, TASK-03
- **可并行**: 否 (最终集成)

### TASK-05: .gitignore 追加逻辑

- **关联 issue**: #33 (FR-014)
- **关联 spec**: 003-init-adopt-mode §FR-014
- **关联测试**: UT-033-1-1, UT-033-2-1, UT-033-3-1, UT-033-4-1, UT-033-5-1, IT-004
- **分支**: `feat/003/TASK-05`
- **描述**:
  - 实现 `append_gitignore_entry(target_path, entry)`:
    1. 不存在 → 创建 + 写入
    2. 已存在但无 entry → append
    3. 已存在且有 entry → 幂等不重复
    4. 不动其他行
  - 默认追加 `.specforge/`
  - `--no-gitignore` flag 禁用此步
- **依赖**: TASK-02 (在 adopt 流程中调用)
- **可并行**: 否 (在 TASK-02 中集成)

### TASK-06: dry-run 实现

- **关联 issue**: #31 (FR-012)
- **关联 spec**: 003-init-adopt-mode §FR-012
- **关联测试**: UT-031-1-1, UT-031-2-1, UT-031-3-1
- **分支**: `feat/003/TASK-06`
- **描述**:
  - 实现 `cmd_init_adopt_dry_run`:
    1. 调用 adopt 流程但所有写操作 no-op
    2. 报告生成仍运行（让用户预览）
  - 验证: dry-run 前后 working tree 字节级不变
- **依赖**: TASK-02, TASK-03
- **可并行**: 是 (与 TASK-05 并行; 但 merge 时需协调)

### TASK-07: 文档更新

- **关联 issue**: 无（文档任务）
- **关联 spec**: README §8.3, agents/README.md
- **关联测试**: 无
- **分支**: `feat/003/TASK-07`
- **描述**:
  - 更新 README.md §8.3: 增加 init 智能检测 + adopt 模式段
  - 更新 agents/README.md: 同上
  - 增加 examples: `specforge init .` `specforge init --backup` 等
- **依赖**: TASK-02 (代码稳定后)
- **可并行**: 是 (与 TASK-04 并行)

## 执行顺序与并行性

### 时间线

```
Week 1:
  Day 1-2: TASK-01 (独立)
  Day 2-3: TASK-02 ∥ TASK-03 (并行)
  Day 3:   TASK-05 (在 TASK-02 内集成)
  Day 4:   TASK-06 ∥ TASK-07 (并行)
  Day 5:   TASK-04 (集成所有)

Week 2:
  Day 1-3: Keeper 验证 + Herald 验收 + Arbiter 终审
```

### 依赖图

```
TASK-01 ─┬─> TASK-02 ─┬─> TASK-04
         │           ├─> TASK-05 ─┘
         └─> TASK-03 ─┴─> TASK-06 ─┘

TASK-07 (独立, 与 TASK-04 并行)
```

## Change History (Wiki)

```yaml
type: decision
title: specforge v0.3 — init adopt mode
date: 2026-06-14
agents: [Scout, Warden, Sage, Lex, Probe, Judge, Archer]
sources: [specs/003-init-adopt-mode/spec.md, specs/003-init-adopt-mode/test-plan.md]
related: [[003-init-adopt-mode-overview]]
```

详细 wiki 页面另存 `wiki/pages/003-init-adopt-mode.md`（Forge 完成时写）。

## 退出条件

- [x] 版本号和分支已确定 (v0.3.0, `feat/003/TASK-{01-07}`)
- [x] 每条任务关联了测试用例编号 (35 UT + 5 IT 全部分配)
- [x] 执行顺序已确定 (1 → {2∥3} → 5 → {6∥7} → 4)
- [x] 可并行任务已标注 (TASK-01, 03, 06, 07 可并行)
- [x] Wiki Change History 已规划 (Herald 阶段落地)

## 反模式检查

- ✅ 每个 TASK 都有 issue# 关联
- ✅ 每个 TASK 都有 UT/IT 关联
- ✅ 每个 TASK 描述具体，不模糊
- ✅ 依赖关系清晰，无循环
- ✅ 并行任务已标注