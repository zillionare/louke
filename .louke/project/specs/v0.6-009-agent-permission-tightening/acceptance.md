# v0.6-009 — Agent 权限收紧 + 分层编排 — Acceptance Criteria

- **Spec ID**: v0.6-009-agent-permission-tightening
- **创建日期**: 2026-07-03
- **修订**: 2026-07-03 12:50 (Qwen review 后, 字段名 `permissions` → `permission`, 格式改 YAML 对象, 移除 `interactive: true`)

> 验收标准集中处。spec.md 只保留 FR/NFR 的需求描述与元数据；可观察、可断言的通过条件在本表里。

---

## FR-0010 4 角色 permission 表

### AC-1 (FR-0010.1 ~ 0010.4)
- 4 个目标 agent 的 `permission:` frontmatter 是 YAML 对象, 键集合完全匹配 spec §3 FR-0010.X (11 键, 含 `external_directory` + `doom_loop` 显式 deny)
  - Warden: `bash, read, grep, glob` = allow; `edit, task, question, webfetch, websearch, external_directory, doom_loop` = deny
  - Judge: 同 Warden + `question: allow` (FR-0070 v0.3.0)
  - Archer: `edit: allow` + 同 Warden 的 deny 集 + `question: allow`
  - Librarian: `edit: allow` + 同 Warden 的 deny 集 (含 `question: deny`)
- 所有 `permission` 键 ∈ OpenCode 白名单 (FR-0010.5)

### AC-2 (FR-0010.5)
- 白名单键集合 = `{read, edit, glob, grep, bash, task, skill, lsp, question, webfetch, websearch, external_directory, doom_loop}`
- `todowrite` **不在**白名单
- 4 agent 的 `permission` 块不出现 `todowrite` 键

### AC-3
- 4 agent 的 `permission` 块中未列出的工具键 = 显式 `deny` (不依赖 OpenCode 默认行为)
- 4 agent 显式 deny `external_directory` + `doom_loop` (Qwen A-8.2), 不依赖 OpenCode 默认 `ask`

---

## FR-0020 source frontmatter 落地

### AC-1
- `agents/Warden.md` / `Judge.md` / `Archer.md` / `Librarian.md` / `Maestro.md` (5 个) 的 frontmatter 含完整 `permission:` 块, 位置在 `models:` 之后
- 其余 7 agent (Sage / Lex / Devon / Scout / Shield / Keeper / Prism) 在 FR-0070 中含最小 `permission:` 块（仅 `question: deny`）

### AC-2
- 5 个含 `permission:` 的 agent 的 frontmatter 仍能被 `louke/board.py:parse_frontmatter` 正确解析 (YAML 对象, 不破坏结构)
- `models.py:used_models` 仍能正确读 `models:` 字段

### AC-3
- 4 agent 中 Warden / Judge / Archer / Librarian 的 `mode:` 字段 = `subagent` (FR-0060.2)
- Maestro 的 `mode:` 字段 = `primary` (FR-0060.1)
- 其余 7 agent 的 `mode:` 字段 = `subagent` (FR-0060.2)

---

## FR-0030 board opencode 透传白名单字段

### AC-1
- `louke/board.py` 定义 `PASSTHROUGH_KEYS = {description, mode, model, permission, hidden, color, temperature, top_p, steps, disable}`
- `cmd_opencode` 解析 source frontmatter 时遍历, 白名单内字段 (除 `description` / `mode` / `model` 已处理) 原样写入生成文件

### AC-2
- 4 agent 加 `permission:` 后, 跑 `lk board opencode` 生成 `.opencode/agents/{warden,judge,archer,librarian}.md`, frontmatter 含完整 `permission:` 块 (YAML 对象)
- 其余 7 agent 的生成文件 frontmatter 含最小 `permission:` 块（仅 `question: deny`）
- Maestro 的生成文件 frontmatter 含完整 `permission:` 块 (FR-0060.1)

### AC-3
- 所有 12 个生成文件的 `mode:` 字段 = source `mode:` (透传, 不重写)
- 4 agent + Maestro 的生成文件 `mode:` = `subagent` / `primary`, 验证透传无误

### AC-4
- `lk board opencode --dry-run` 预览输出中能看到透传字段
- 生成文件能被 OpenCode 正确加载 (YAML 语法正确)

### AC-5
- source frontmatter 含白名单外字段 (如 `_debug: true`), 跑 `lk board opencode --dry-run` 时打印 `[!] dropped unknown frontmatter key '_debug' from <agent>`, 生成文件中**不**出现该字段

---

## FR-0040 `lk agent lint` 校验

### AC-1 (新增命令)
- `lk agent lint` 命令存在, 走 `lk` CLI 已有子命令模式
- 实现位置: `louke/agent.py` (新建文件)

### AC-2 (schema 校验)
- 4 角色 (Warden / Judge / Archer / Librarian) 缺 `permission:` → 报错 `missing permission block for <name>`, exit 1
- 4 角色的 `permission` 不是 YAML 字典 (如写成字符串) → 报错, exit 1
- 4 角色的 `permission` 含未知键 (如 `todowrite: allow`) → 报错, exit 1
- 4 角色的 `permission` 值非法 (如 `edit: maybe`) → 报错, exit 1
- 其余 7 agent 不强求 `permission:` (lint 不报缺失)

### AC-3 (mode 单一性)
- `agents/*.md` 中 `mode: primary` 数量 = 1 (Maestro) → pass
- `mode: primary` 数量 ≠ 1 (多了或少了) → 报错 `only maestro can be primary; found {N} agents`, exit 1
- `mode: all` 数量 > 0 → 报错 `mode: all is deprecated; use primary or subagent`, exit 1
- `mode: subagent` 数量 ≥ 1 → pass

### AC-4 (board.py 集成)
- `lk agent lint` exit 0 → `lk board opencode` 生成的 frontmatter 与 source 一致 (无字段丢失)
- `tests/test_agent_frontmatter.bats` 新增:
  - `permission-required-for-4-roles`: 删任一目标角色 `permission:` → fail
  - `permission-whitelist`: 注入 `permission: { todowrite: allow }` → fail
  - `permission-board-passthrough`: 加 permission 跑 `lk board opencode` → 生成文件含该块
  - `permission-backward-compat`: 7 个非目标 agent 不加 permission → 跑 board 不报错, 生成文件不含该块
  - `mode-single-primary`: 临时改任一 agent 为 `mode: primary` → fail

---

## FR-0050 文档同步

### AC-1
- `README.md` 和 `README.zh.md` 新增"Agent 权限矩阵"小节, 覆盖 5 个 (4 角色 + Maestro) 显式 permission 的 agent + 7 个走 OpenCode 默认的 agent
- 5 个 agent prompt (Warden / Judge / Archer / Librarian / Maestro) 新增对应工具/编排段落
- 11 个 subagent prompt (含 4 角色之外的 7 个) 新增"## 你的身份"段落

### AC-2 (README "已知限制" 子段)
- README "分层编排" 小节末尾加 `⚠️ 已知限制` 段落:
  > 子代理的 `question` 弹框在 v0.3.0 **已实测确认**冒泡到主会话窗口 (2026-07-03 14:00 by Aaron)，用户在主窗口选项回复即可，无需按 `<Leader>+Down` 进入子会话。

---

## FR-0060 Maestro 全权工作流控制

### AC-1 (FR-0060.1)
- `agents/Maestro.md` frontmatter:
  - `mode: primary` (不是 `all`)
  - `permission:` 块含 `{bash, read, edit, grep, glob, task, question, webfetch, websearch, skill, lsp, external_directory, doom_loop}` 共 13 个键
  - 值: `task: allow, webfetch: allow, external_directory: ask, doom_loop: deny, question: deny, websearch: deny, skill: deny, lsp: deny`, 其余 `allow`
  - **不**含 `todowrite` 键

### AC-2 (FR-0060.2)
- 11 个非 Maestro agent 的 `mode:` 字段 = `subagent`
- `lk board opencode` 生成的 12 个 `.opencode/agents/*.md` 文件中:
  - 11 个 `mode: subagent`
  - 1 个 (maestro) `mode: primary`
- TUI 顶层 `<Leader>a` agent 列表**只**显示 maestro (手动 IDE 验证 1 次)

### AC-3 (FR-0060.3)
- `lk init` 生成的 `opencode.json` (项目级 + 全局) `"default_agent": "maestro"` (v0.6-008 FR-0300 复用)

### AC-4 (FR-0060.4)
- board.py 透传 `mode: subagent` (不被改回 `mode: all`)

### AC-5 (FR-0060.5)
- `agents/Maestro.md` 新增"## 你的编排模式"段落
- 11 个 subagent prompt 新增"## 你的身份"段落

---

## FR-0070 交互式 subagent (v0.3.0, IDE 实测 2026-07-03 14:00 通过)

### AC-1 (FR-0070.2, v0.3.0 实际配置落地)
- 4 交互式 subagent (Scout / Sage / Archer / Judge) frontmatter `permission` 块含 `question: allow`
- 7 非交互式 subagent (Lex / Devon / Shield / Keeper / Prism / Warden / Librarian) frontmatter `permission` 块含 `question: deny`
- Maestro frontmatter `permission` 块含 `question: deny` (FR-0060.1)
- `lk board opencode` 生成的 12 个文件, 4 个含 `question: allow`, 8 个 (含 Maestro) 含 `question: deny`

### AC-2 (FR-0070.3, 方案 b — Qwen A-8.3)
- 4 交互式 subagent (Scout / Sage / Archer / Judge) prompt 新增"## 你的交互能力"段落, 写"交互式"行为, 与 `permission.question: allow` config 严格一致
- 7 非交互式 subagent (Lex / Devon / Shield / Keeper / Prism / Warden / Librarian) prompt 新增"## 你的非交互身份"段落
- 0 个 prompt/config 不匹配

### AC-3 (FR-0070.4, Maestro 编排模式)
- `agents/Maestro.md` "## 你的编排模式" 段落显式区分 4 交互式 + 7 非交互式
- 段落含 "**弹框冒泡保证**" 子项, 引用 2026-07-03 14:00 IDE 实测结果

### AC-4 (FR-0070.5, 场景表 + Error Path)
- 4 交互式 subagent prompt 含完整的 question 场景表 (含 Error Path 列)
- 表格覆盖:
  - Scout: repo 元数据 (正常) + GitHub API 权限不足 (error)
  - Sage: 档位/AC/冲突 (正常) + spec 内部矛盾 (error)
  - Archer: 测试策略/trade-off (正常) + 多 spec-id 优先级 (error)
  - Judge: severity/豁免 (正常) + 接受风险流程 (error)

### AC-5 (FR-0070.6, 5 分钟 IDE 实测基线)
- v0.3.0 release 前**必须**做一次 5 分钟 IDE 实测
- 实测模板 5 项 (见 spec.md FR-0070.6) 全部 ✓
- 实测结果记录在 `.louke/qwen-review-v0.6-009.md` + v0.6-009 spec 文件头
- 实测 fail: 退回方案 (FR-0070 走 prompt 与 config 同步 deny 模式, 实际配置推迟 patch release)

---

## NFR-0010 向后兼容 (含 breaking change)

### AC-1
- ⚠️ 升级 v0.6-009 后, `<Leader>a` 列表从 12 agent 变 1 agent (Maestro); changelog / README "已知限制" 段显式声明

### AC-2
- 加 `permission:` 前生成一组 `.opencode/agents/*.md` 作 baseline
- 加 `permission:` 后重生成, 对比:
  - 4 agent 文件多完整 `permission:` 块
  - Maestro 文件多完整 `permission:` 块 + `mode: primary`
  - 其余 7 agent 文件多最小 `permission:` 块（仅 `question: deny`）+ `mode: subagent`

### AC-3
- `lk models doctor` / `lk init` / `lk board status` 三个命令行为与 v0.6-009 前一致

---

## NFR-0040 OpenCode 版本检查

### AC-1
- `louke/__init__.py` 含 `MIN_OPENCODE_VERSION = "1.1.1"` 常量 (Qwen A-8.4 校准: `permission` 对象格式替代 deprecated `tools` 布尔字段的引入版本)
- `lk agent lint --check-opencode-version` (默认 off) 读 `opencode --version` 输出, 低于 `MIN_OPENCODE_VERSION` 时打印 warning, 不阻塞 lint

---

## NFR-0050 单一 primary agent 约束

### AC-1
- `lk agent lint` 校验:
  - `mode: primary` 数量 = 1 (maestro) → pass
  - 违反: lint exit 1, stderr 含 `only maestro can be primary`

### AC-2
- `mode: all` 数量 = 0 → pass; > 0 → 报错
- 所有 agent 必须显式 `mode: primary` 或 `mode: subagent`
