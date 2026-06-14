# TEST-003-init-adopt-mode-01 — init 子命令支持既存项目非破坏性合并

## 测试环境

- **框架**: specforge 自身 (bash + bats)
- **Python**: 3.x (供 `verify_issue_schema.py` 使用)
- **测试 runtime**: `bats` (已在 `tests/` 目录使用)
- **外部依赖**: 无；纯文件系统操作
- **隔离方式**: 每个 UT 在 `mktemp -d` 创建临时目录，teardown 删除
- **关键约束**: `SPECFORGE_HOME` 必须指向已安装的 specforge（dev 模式可 `SPECFORGE_HOME=.`）

## 可追溯矩阵

| Issue # | 需求 ID | 单元测试用例 | 集成测试用例 | 状态 |
|---------|---------|-------------|-------------|------|
| #27 | FR-008 | UT-027-1-1, UT-027-1-2, UT-027-1-3, UT-027-1-4, UT-027-1-5 | IT-001 | open |
| #28 | FR-009 | UT-028-1-1, UT-028-2-1, UT-028-3-1, UT-028-3-2 | IT-001 | open |
| #29 | FR-010 | UT-029-1-1, UT-029-2-1, UT-029-3-1, UT-029-4-1, UT-029-5-1 | IT-002 | open |
| #30 | FR-011 | UT-030-1-1, UT-030-2-1, UT-030-3-1, UT-030-4-1, UT-030-5-1 | IT-003 | open |
| #31 | FR-012 | UT-031-1-1, UT-031-2-1, UT-031-3-1 | IT-002 | open |
| #32 | FR-013 | UT-032-1-1, UT-032-2-1, UT-032-3-1, UT-032-4-1 | IT-001 | open |
| #33 | FR-014 | UT-033-1-1, UT-033-2-1, UT-033-3-1, UT-033-4-1, UT-033-5-1 | IT-004 | open |
| #34 | FR-015 | UT-034-1-1, UT-034-2-1, UT-034-3-1 | IT-005 | open |

总计 35 个 UT + 5 个 IT。

## 单元测试

### Issue #27 [FR-008]: init 子命令支持既存路径智能检测

#### AC-1: `init .` 不报错，转入 adopt 模式
##### UT-027-1-1: 当前目录 (.) 触发 adopt
- 输入: `mkdir tmpdir && cd tmpdir && git init && specforge init .`
- 预期输出: 退出码 0；stderr/stdout 含 "adopt" 关键字；`agents/` `specs/` 等被创建
- 覆盖分支: 路径检测 = `.`

#### AC-2: `init ./proj` 不报错，转入 adopt 模式
##### UT-027-2-1: 相对路径触发 adopt
- 输入: `mkdir -p existing && cd existing && git init && specforge init ./sub`
- 预期输出: 退出码 0；adopt 模式生效
- 覆盖分支: 路径检测 = `./sub`

#### AC-3: `init /abs/path` 不报错，转入 adopt 模式
##### UT-027-3-1: 绝对路径触发 adopt
- 输入: `mkdir -p /tmp/foo && cd /tmp/foo && git init && specforge init /tmp/foo`
- 预期输出: 退出码 0
- 覆盖分支: 路径检测 = `/abs/path`

#### AC-4: `init ~/path` 不报错，转入 adopt 模式
##### UT-027-4-1: home 缩写触发 adopt
- 输入: `mkdir -p ~/foo && git init ~/foo && specforge init ~/foo`
- 预期输出: 退出码 0
- 覆盖分支: 路径检测 = `~/path`

#### AC-5: `init myproj`（裸名）保持现有行为不变
##### UT-027-5-1: 裸名走新建（与原 init 兼容）
- 输入: `cd /tmp && specforge init myproj`
- 预期输出: 退出码 0；`myproj/agents/` 等被创建
- 覆盖分支: 路径检测 = bare-name（无 `/` `.` `~`）

### Issue #28 [FR-009]: adopt 模式不破坏既存源代码

#### AC-1: adopt 前后字节级 diff 为空
##### UT-028-1-1: SHA256 清单对比
- 输入: 建立测试项目（含 quantide/ data/ notebooks/），调用 `specforge init .`
- 预期输出: `find . -type f -not -path "./.git/*" -not -path "./specs/*" -not -path "./agents/*" -not -path "./templates/*" -not -path "./wiki/*" -not -path "./raw/*" -exec sha256sum {} \;` 前后输出相同
- 覆盖分支: SHA256 baseline vs post-adopt

#### AC-2: 既存源代码递归验证不变
##### UT-028-2-1: quantide/ data/ notebooks/ 不被触碰
- 输入: 同上，单独验证每个目录
- 预期输出: 各目录 byte count / mtime 不变

#### AC-3: 既存 .git/ 目录不被 adopt 触碰
##### UT-028-3-1: .git/ 完整保留
- 输入: git init + commit 一个文件 + specforge init .
- 预期输出: git log 仍然显示原有 commit；git status 干净（除新增的 specforge-owned 目录外）

### Issue #29 [FR-010]: adopt 模式创建缺失目录而非整体 mkdir

#### AC-1: 缺 agents/ 时创建并复制所有 *.md
##### UT-029-1-1: 全空项目走新建
- 输入: `mkdir empty && cd empty && git init && specforge init .`
- 预期输出: agents/ 含 ≥19 个 .md（与现有 test_init.bats UT-002-01 一致）

#### AC-2: 已有 agents/ 时不动
##### UT-029-2-1: agents/ 完整保留
- 输入: 预创建 `agents/My.md` 内容为 "user-customized"，adopt
- 预期输出: `agents/My.md` 内容仍是 "user-customized"；未新增任何 .md

#### AC-3: 缺 specs/ 时创建空目录
##### UT-029-3-1: specs/ 自动创建
- 输入: 全空项目 adopt
- 预期输出: `specs/` 存在且为空

#### AC-4: 已有 specs/ 时不动
##### UT-029-4-1: specs/ 保留
- 输入: 预创建 `specs/001-old/spec.md`，adopt
- 预期输出: `specs/001-old/spec.md` 仍在

#### AC-5: wiki/{pages,decisions}/、raw/sources/ 同上规则
##### UT-029-5-1: 其他 specforge-owned 目录
- 输入: 预创建 `wiki/pages/x.md`，adopt
- 预期输出: `wiki/pages/x.md` 仍在；`wiki/decisions/` `raw/sources/` 被创建（之前不存在）

### Issue #30 [FR-011]: adopt 模式对 agents/templates 文件 skip+warn 默认策略

#### AC-1: 既存文件与 SPECFORGE_HOME 版本相同时：跳过（无提示）
##### UT-030-1-1: 同版本无警告
- 输入: 预创建 `agents/Maestro.md` 内容与 `$SPECFORGE_HOME/agents/Maestro.md` 完全相同
- 预期输出: stderr 无警告（silent skip）

#### AC-2: 既存文件与 SPECFORGE_HOME 版本不同时：skip + stderr 警告
##### UT-030-2-1: 异版本警告
- 输入: 预创建 `agents/Maestro.md` 内容为 "user-modified"
- 预期输出: stderr 含 `agents/Maestro.md exists, skipped` 字样；文件未被覆盖

#### AC-3: `--backup` flag 启用时：备份为 .bak 再跳过
##### UT-030-3-1: 备份模式
- 输入: 预创建 `agents/Maestro.md`；`specforge init . --backup`
- 预期输出: `agents/Maestro.md.bak` 存在（内容 = 原 modified 版本）；`agents/Maestro.md` 仍是 modified

#### AC-4: `--force` flag 启用时：覆盖
##### UT-030-4-1: 强制覆盖
- 输入: 预创建 `agents/Maestro.md`；`specforge init . --force`
- 预期输出: `agents/Maestro.md` 内容 = `$SPECFORGE_HOME/agents/Maestro.md`（被覆盖）；无 .bak

#### AC-5: 上述规则对 agents/*.md 和 templates/*.md 都生效
##### UT-030-5-1: 规则覆盖两个目录
- 输入: 预创建 `templates/spec.md`；adopt
- 预期输出: stderr 含 `templates/spec.md exists, skipped`；文件未变

### Issue #31 [FR-012]: adopt 模式支持 `--dry-run` flag

#### AC-1: `--dry-run` 不修改任何文件
##### UT-031-1-1: dry-run 字节级零变更
- 输入: 建立项目，调用 `specforge init . --dry-run`
- 预期输出: `find . -type f | sha256sum` 前后相同（除 report 输出到 stdout）

#### AC-2: `--dry-run` 输出与实际 adopt 等价的分档报告
##### UT-031-2-1: 报告内容一致
- 输入: 同一项目两次调用（一次 `--dry-run`，一次不带），对比 stdout
- 预期输出: `[+]/[=]/[!]` 报告内容相同（仅顺序可能略不同）

#### AC-3: `--dry-run` 与 adopt 的报告必须一致
##### UT-031-3-1: dry-run 是真实预演
- 输入: 同上
- 预期输出: 报告中每行涉及的 path 在 dry-run 和 actual 中都一致

### Issue #32 [FR-013]: adopt 模式结束打印分档报告

#### AC-1: 报告每行一个文件，格式 `[+] path` / `[=] path` / `[!] path`
##### UT-032-1-1: 行格式
- 输入: adopt 输出
- 预期输出: stdout 每行匹配 `^(\[+=\!\])\s+.+`

#### AC-2: 报告按 `[+][=][!]` 分组排序
##### UT-032-2-1: 排序
- 输入: 含多个 [+]/[=]/[!] 的 adopt
- 预期输出: 所有 [+] 在前，[=] 居中，[!] 在后

#### AC-3: 报告结尾打印汇总：N 个新文件，M 个跳过，K 个备份
##### UT-032-3-1: 汇总行
- 输入: adopt
- 预期输出: stdout 末尾含 `\d+ 个新文件, \d+ 个跳过, \d+ 个备份`

#### AC-4: `--json` flag 时输出机器可读 JSON
##### UT-032-4-1: JSON 输出
- 输入: `specforge init . --json`
- 预期输出: stdout 是 valid JSON，含 `added/skipped/backed_up` 数组

### Issue #33 [FR-014]: adopt 模式向 `.gitignore` 追加 `.specforge/`

#### AC-1: 目标 `.gitignore` 不存在时创建并写入
##### UT-033-1-1: 创建 .gitignore
- 输入: 全空项目 adopt
- 预期输出: `.gitignore` 存在且含 `.specforge/` 一行

#### AC-2: 目标 `.gitignore` 已存在且无 `.specforge/` 时追加
##### UT-033-2-1: append
- 输入: 预创建 `.gitignore` 含 `__pycache__\n*.pyc`；adopt
- 预期输出: `.gitignore` 含原内容 + 新追加的 `.specforge/`

#### AC-3: 目标 `.gitignore` 已有 `.specforge/` 时不重复
##### UT-033-3-1: 幂等
- 输入: 预创建 `.gitignore` 含 `.specforge/`；adopt
- 预期输出: `.specforge/` 仍只出现 1 次

#### AC-4: 追加是 append，不是 overwrite
##### UT-033-4-1: 保留其他行
- 输入: 预创建 `.gitignore` 含 10 行；adopt
- 预期输出: 原 10 行 + 新 1 行 = 11 行；行顺序保留

#### AC-5: 不动 `.gitignore` 中其他条目
##### UT-033-5-1: 不删不改
- 输入: 预创建 `.gitignore` 含注释 `# my config` 和复杂 glob；adopt
- 预期输出: 所有原行原样保留，仅追加

### Issue #34 [FR-015]: init 裸名+既存目录报错保持向后兼容

#### AC-1: 裸名 + 既存目录 → 报错
##### UT-034-1-1: 现有行为保留
- 输入: `mkdir myproj && specforge init myproj`
- 预期输出: 退出码非 0；stderr 含 "already exists" 字样

#### AC-2: 报错信息保留现有文案
##### UT-034-2-1: 文案兼容
- 输入: 同上
- 预期输出: stderr 完全匹配 `Directory 'myproj' already exists`

#### AC-3: 既有 `tests/test_init.bats UT-001-02` 仍然通过
##### UT-034-3-1: 回归保护
- 输入: `bats tests/test_init.bats`
- 预期输出: 所有现有 test case 全部通过（特别是 UT-001-02）

## 集成测试

### IT-001: 端到端 adopt 真实 Python 项目
- 涉及 issues: #27 (FR-008), #28 (FR-009), #32 (FR-013)
- 前置条件: 复制 millionaire 仓库（或类似真实 Python 项目）到临时目录
- 操作步骤:
  1. `cd tmpdir && git init`
  2. `specforge init . --dry-run` → 检查报告
  3. `specforge init .` → 实际 adopt
  4. `find . -newer tmpdir_start -type f` → 应只含 agents/ specs/ wiki/ raw/ 下的文件
  5. `sha256sum` 对比源代码区
  6. `git status` 验证 .git 不被破坏
- 期望结果: 真实 Python 项目的 adopt 工作正常；源代码 0 变更；报告清晰

### IT-002: adopt + dry-run + report 一致性
- 涉及 issues: #29 (FR-010), #31 (FR-012)
- 前置条件: 含 quantide/ data/ notebooks/ 的项目
- 操作步骤:
  1. 第一次: `specforge init . --dry-run --json` → 解析 JSON
  2. 第二次: `specforge init . --dry-run --json` → 解析 JSON
  3. 对比两次 JSON
  4. 第三次: `specforge init . --dry-run` → 对比 stdout
- 期望结果: 三次报告内容完全一致（dry-run 幂等）

### IT-003: 同名文件冲突三策略
- 涉及 issues: #30 (FR-011)
- 前置条件: 预创建 `agents/Maestro.md` 内容 = "v1"
- 操作步骤:
  1. `specforge init .` → 验证 skip+warn（stderr 含 skipped），文件仍是 v1
  2. `specforge init . --backup` → 验证 v1.bak 存在，文件仍是 v1
  3. `rm agents/Maestro.md.bak`
  4. `specforge init . --force` → 验证文件被覆盖为 SPECFORGE_HOME 版本
- 期望结果: 三种 flag 各自行为正确，互不干扰

### IT-004: .gitignore 在 idempotent adopt 中的稳定性
- 涉及 issues: #33 (FR-014)
- 前置条件: `.gitignore` 含 `.specforge/`
- 操作步骤:
  1. `specforge init .` 第一次
  2. `specforge init .` 第二次
  3. `git diff .gitignore` → 期望无 diff
- 期望结果: .gitignore 在多次 adopt 下保持稳定（不重复追加）

### IT-005: 向后兼容性 (回归保护)
- 涉及 issues: #34 (FR-015)
- 前置条件: specforge 已安装
- 操作步骤:
  1. `bats tests/test_init.bats` → 所有现有 UT 通过
  2. `bats tests/test_specforge_cli.bats` → CLI 集成测试通过
- 期望结果: 既有测试 0 失败（防止 adopt 改动破坏 init 基础行为）

## 视觉/E2E 测试

不适用。本 spec 涉及纯 CLI 行为，无 UI 组件。

## 退出条件

- [x] 测试计划文档已生成
- [x] 每个 issue 的每条 AC 都有对应 UT
- [x] 跨 issue 场景有 IT 覆盖
- [x] 可追溯矩阵完整
- [x] 测试环境要求已说明