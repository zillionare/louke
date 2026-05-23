# TEST-V1-001 — specforge v1 测试计划

- **Spec ID**: SPEC-V1-001
- **创建日期**: 2026-05-23

## 测试环境

- **OS**: macOS 14+ / Ubuntu 22.04+
- **Shell**: bash 5.x
- **工具依赖**: git, curl
- **LLM 宿主**: Kilo CLI（用于验证 Agent prompt 行为）
- **数据构造**: 无需数据库 — 所有测试操作在临时目录进行
- **环境搭建**: `mkdir -p /tmp/specforge-test && cd /tmp/specforge-test && specforge init test-project`

## 可追溯矩阵

| spec FR ID              | 单元测试                          | 集成测试    |
|-------------------------|----------------------------------|------------|
| FR-001                  | UT-001-01, UT-001-02            | IT-001     |
| FR-002                  | UT-002-01~05                     | IT-001     |
| FR-003                  | UT-003-01, UT-003-02            | IT-001     |
| FR-004                  | UT-004-01~03                     | IT-002     |
| FR-005                  | UT-005-01, UT-005-02            | IT-002     |
| FR-006                  | UT-006-01, UT-006-02            | IT-003     |
| FR-007                  | UT-007-01~03                     | IT-003     |
| FR-008                  | UT-008-01                        | IT-003     |
| FR-009                  | UT-009-01, UT-009-02            | IT-003     |
| FR-010                  | UT-010-01~03                     | IT-004     |
| FR-011                  | UT-011-01~08                     | IT-005     |
| FR-012                  | UT-012-01~03                     | IT-005     |

## 单元测试

### FR-001: specforge init 创建项目目录

#### UT-001-01: init 在空目录下创建项目
- 输入: `specforge init test-project`（在 /tmp/specforge-test/ 执行）
- 预期输出: 进程返回 exit code 0，`/tmp/specforge-test/test-project/` 目录存在
- 覆盖分支: 正常初始化路径

#### UT-001-02: init 在已存在目录时给出提示
- 输入: 先 mkdir 再 `specforge init test-project`（目录已存在）
- 预期输出: stderr 包含 "already exists" 或 "已存在"，exit code ≠ 0
- 覆盖分支: 异常路径 — 目录冲突

### FR-002: init 创建正确的目录结构

#### UT-002-01: agents/ 目录存在且含 ≥21 个 .md 文件
- 输入: 执行 init 后 `ls test-project/agents/*.md | wc -l`
- 预期输出: 数值 ≥ 21
- 覆盖分支: 核心文件数量

#### UT-002-02: templates/ 目录存在且含 8 个 .md 文件
- 输入: 执行 init 后 `ls test-project/templates/*.md | wc -l`
- 预期输出: 数值 = 8
- 覆盖分支: 模板文件数量

#### UT-002-03: wiki/entries/ 目录存在
- 输入: 执行 init 后 `test -d test-project/wiki/entries`
- 预期输出: exit code 0（目录存在）
- 覆盖分支: wiki 子目录创建

#### UT-002-04: wiki/decisions/ 目录存在
- 输入: 执行 init 后 `test -d test-project/wiki/decisions`
- 预期输出: exit code 0（目录存在）
- 覆盖分支: wiki 子目录创建

#### UT-002-05: specs/ 目录存在
- 输入: 执行 init 后 `test -d test-project/specs`
- 预期输出: exit code 0（目录存在）
- 覆盖分支: specs 目录创建

### FR-003: init 打印 onboarding 指引文本

#### UT-003-01: stdout 包含关键指引关键词
- 输入: 执行 `specforge init test-project 2>&1`
- 预期输出: stdout 包含 "下一步" 或 "next step" 或 "开始" 或 "start"
- 覆盖分支: 指引文本存在性

#### UT-003-02: stdout 包含模型推荐信息
- 输入: 执行 `specforge init test-project 2>&1`
- 预期输出: stdout 包含 "模型" 或 "model" 或 "deepseek" 或 "kimi"（不区分大小写）
- 覆盖分支: 模型推荐存在性

### FR-004: Guide 知识覆盖范围

#### UT-004-01: Guide 能回答阶段相关问题
- 输入: 加载 Guide prompt 为 system message → 询问 "specforge 有哪些开发阶段？"
- 预期输出: 回答中包含 "Story/PRD" 或 "Interview" 或 "Test Plan" 或 "执行规划" 或 "验收"
- 覆盖分支: ROSTER.md 知识检索

#### UT-004-02: Guide 能回答 Agent 职责问题
- 输入: 加载 Guide prompt → 询问 "Scout 的职责是什么？"
- 预期输出: 回答中包含 "勘探" 或 "前置条件" 或 "PRD"
- 覆盖分支: Agent 文件知识检索

#### UT-004-03: Guide 能回答模型选择问题
- 输入: 加载 Guide prompt → 询问 "Forge 应该用什么模型？"
- 预期输出: 回答中涉及 "S 档" 或 "deepseek-v4-pro" 或 "opus"（不区分大小写）
- 覆盖分支: README.md 模型矩阵检索

### FR-005: Guide 不编造信息

#### UT-005-01: 超出知识范围的问题 → 拒绝回答
- 输入: 加载 Guide prompt → 询问 "如何用 Rust 重写 Linux 内核？"
- 预期输出: 回答中不含实现细节，包含 "超出" 或 "不知道" 或 "无法" 等拒绝信号
- 覆盖分支: 知识边界约束

#### UT-005-02: 回答中包含文件路径引用
- 输入: 加载 Guide prompt → 询问 "模板有哪些？"
- 预期输出: 回答中出现如 "agents/" "templates/" "ROSTER.md" 等路径样式字符串
- 覆盖分支: 引用文档的保证

### FR-006: Librarian 生成 consolidated.md

#### UT-006-01: consolidation 后文件存在
- 输入: wiki/entries/ 有 3 个条目 → 调用 Librarian
- 预期输出: `wiki/consolidated.md` 文件存在
- 覆盖分支: 产出文件创建

#### UT-006-02: consolidated.md 内容非空
- 输入: 同上
- 预期输出: `wc -c wiki/consolidated.md` > 0
- 覆盖分支: 产出内容非空

### FR-007: Consolidation 规则

#### UT-007-01: 同决策条目去重合并
- 输入: wiki/entries/ 有 2 个描述同一决策的条目 → 调用 Librarian
- 预期输出: `grep -c "该决策描述" wiki/consolidated.md` 输出 1（只出现一次）
- 覆盖分支: 去重逻辑

#### UT-007-02: 矛盾结论标注冲突
- 输入: 2 个条目描述同一主题但结论相反 → 调用 Librarian
- 预期输出: consolidated.md 中该主题下出现 "冲突" 或 "矛盾" 字样
- 覆盖分支: 冲突检测

#### UT-007-03: 过时条目标注
- 输入: 1 个条目含 "[已过时]" 或 "不再适用" → 调用 Librarian
- 预期输出: consolidated.md 中该条目被标注为 `[已过时]`
- 覆盖分支: 过时标记

### FR-008: Librarian 不修改原始文件

#### UT-008-01: consolidation 后原始文件未变
- 输入: 记录 3 个条目文件的 md5 → 调用 Librarian → 再次计算 md5
- 预期输出: md5 值前后一致
- 覆盖分支: 文件安全性

### FR-009: Librarian 触发模式

#### UT-009-01: 手动触发有效
- 输入: 用户发送 "Librarian, consolidate the wiki"
- 预期输出: Librarian 开始执行 consolidation，非等待自动触发
- 覆盖分支: 手动触发路径

#### UT-009-02: 自动触发（N=5）
- 输入: wiki/entries/ 下创建第 5 个条目文件
- 预期输出: 在 5 秒内 Librarian 自动执行（无需用户手动命令）
- 覆盖分支: 自动触发路径

### FR-010: Agent 会话自动保存

#### UT-010-01: 对话后在 wiki/entries/ 有新文件
- 输入: 用 Scout prompt 执行一次对话
- 预期输出: 对话结束后 `wiki/entries/` 下出现新的 .md 文件
- 覆盖分支: 文件写入

#### UT-010-02: 文件命名格式正确
- 输入: 同上
- 预期输出: 新文件名匹配正则 `^\d{4}-\d{2}-\d{2}-.+\.md$`
- 覆盖分支: 命名规范

#### UT-010-03: 文件包含必需章节
- 输入: 同上
- 预期输出: 文件内容包含 "讨论主题" 或 "日期" 或 "参与者" 或 "关键结论"
- 覆盖分支: 内容结构

### FR-011: 8 个模板文件存在

#### UT-011-01~08: 逐个验证模板文件
- 输入: `test -f templates/prd.md` → exit 0
- 输入: `test -f templates/spec.md` → exit 0
- 输入: `test -f templates/issues.md` → exit 0
- 输入: `test -f templates/test-plan.md` → exit 0
- 输入: `test -f templates/task-plan.md` → exit 0
- 输入: `test -f templates/task-log.md` → exit 0
- 输入: `test -f templates/acceptance.md` → exit 0
- 输入: `test -f templates/bug-fix.md` → exit 0
- 覆盖分支: 文件存在性

### FR-012: Agent 输出遵循模板

#### UT-012-01: prd.md 模板 — Agent 输出包含所有一级标题
- 输入: 用 prd.md 模板 + Scout prompt 生成 PRD
- 预期输出: 输出中包含 `## 背景` `## 目标` `## 验收标准` `## 非目标` `## 风险`
- 覆盖分支: 标题完整性

#### UT-012-02: spec.md 模板 — Agent 输出包含所有一级标题
- 输入: 用 spec.md 模板 + Sage prompt 生成 spec
- 预期输出: 输出中包含 `## 用户故事` `## 功能需求` `## 非功能需求` `## 澄清记录`
- 覆盖分支: 标题完整性

#### UT-012-03: task-log.md 模板 — Agent 输出包含所有一级标题
- 输入: 用 task-log.md 模板 + Forge prompt 生成日志
- 预期输出: 输出中包含 `## Phase 1: Red` `## Phase 2: Green` `## Phase 3: Refactor` `## Keeper 门禁`（不分大小写）
- 覆盖分支: 标题完整性

## 集成测试

### IT-001: specforge init 全流程
- 前置条件: 空目录
- 操作步骤: `specforge init test-project`
- 期望结果: 
  - 目录创建成功
  - agents/ 有 ≥21 个 .md 文件
  - templates/ 有 8 个 .md 文件
  - wiki/entries/ 和 wiki/decisions/ 存在
  - 终端输出含指引文本

### IT-002: Guide Agent 端到端
- 前置条件: specforge 项目已初始化
- 操作步骤: 加载 Guide prompt → 依次询问 3 类问题（阶段、Agent 职责、模型选择）
- 期望结果: 3 次询问均返回相关、准确、有文档引用的回答

### IT-003: Librarian 整合 → 自动触发
- 前置条件: wiki/entries/ 已有 4 个条目，consolidated.md 为旧版本
- 操作步骤: 创建第 5 个条目
- 期望结果: consolidated.md 被更新，文件修改时间晚于第 5 个条目的创建时间，内容包含新条目信息

### IT-004: 会话保存全链路
- 前置条件: 项目已初始化
- 操作步骤: 运行任意 Agent 对话（如 Scout）
- 期望结果: wiki/entries/ 出现新文件 → 文件命名合规 → 内容包含必需章节

### IT-005: 全部模板格式合规
- 前置条件: templates/ 8 个模板就绪
- 操作步骤: 对每个模板，用对应的 Agent prompt 生成输出
- 期望结果: 8 次输出均不缺失模板定义的任何一级标题

## QA 场景

### QA-001: init 脚本可安装性
- 工具: curl + bash
- 步骤: `curl -sSL https://raw.githubusercontent.com/zillionare/specforge/main/install.sh | bash`
- 预期结果: 终端出现 `specforge` 命令可用，`specforge --version` 返回 v1.0.0

### QA-002: 新用户 onboarding 体验
- 工具: 终端
- 步骤: 执行 init → 阅读指引 → 按指引操作（调用 Guide）
- 预期结果: 用户在 5 分钟内能成功调用 Guide 并获得可用回答
