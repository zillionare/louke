# v0.7-002 — 知识蒸馏（Karpathy 风格）— Acceptance Criteria

- **Spec ID**: v0.7-002-knowledge-distillation-karpathy
- **创建日期**: 2026-07-05
- **关联**: spec.md（同一目录）

> 验收标准集中处。可观察、可断言的通过条件在本表里。
> 编号约定: AC-FRXXXX-YY（4 位 FR + 2 位 AC 序号）。

---

## FR-0070 三原则

### AC-1 (raw = journal)
- `.louke/raw/` 不在 git tracked（`.gitignore` 含 `.louke/raw/`）
- `louke/librarian.py` 任何函数（含 `cmd_compact` / `cmd_rewrite`）不修改 `raw/` 下任何文件
- 各 source Agent 写 raw 时 `status` 字段 ∈ `{open, resolved, superseded}`，compact 仅处理 `resolved`

### AC-2 (pages = projection)
- `cmd_rewrite` prompt 显式声明"**整体重写** pages/，不是 patch"
- rewrite 后 `pages/` 下的旧文件名不保证保留（重写后整体替换）

### AC-3 (python 不调 LLM SDK)
- `louke/librarian.py` 顶部 `import` 不含 `openai` / `anthropic` 等 LLM SDK
- LLM 推理统一通过 `subprocess.run(['opencode', 'run', '--agent', 'librarian', ...])` shell-out

---

## FR-0080 `lk librarian compact` / `lk librarian rewrite`

### FR-0080.0 旧命令清理

#### AC-1 (cmd_from_raw 删除)
- `louke/librarian.py` 不定义 `cmd_from_raw` 函数
- `grep cmd_from_raw louke/librarian.py` 无命中

#### AC-2 (cmd_daily 删除)
- `louke/librarian.py` 不定义 `cmd_daily` 函数
- `grep cmd_daily louke/librarian.py` 无命中

### FR-0080.1 `cmd_compact`

#### AC-1 (子命令存在)
- `lk librarian compact` 命令存在
- 接受 `--dry-run` / `--threshold-tokens` / `--m2-threshold` flag

#### AC-2 (窗口计算)
- `last_distill` 为空 → window = `[1970-01-01, yesterday]`
- `last_distill` = '2026-07-04' 且今天 2026-07-06 → window = `[2026-07-04, 2026-07-05]`
- 窗口上限 `yesterday = today - 1`（**不是** today）

#### AC-3 (无 date 字段跳过 + warning)
- 含 raw 条目无 `date` 字段 → stdout 出现 `[compact] WARN: N 个 raw 条目无 date 字段`
- 该条目**不**进入 bundle，不计入 token 估算

#### AC-4 (bundle 写入)
- M0/M1: 写 `.louke/wiki/.compact-bundle.md`
- M2: 写 `.louke/wiki/.compact-bundle-{YYYY-MM}.md` × N + `.louke/wiki/.compact-bundle-manifest.md`（manifest 仅列出 sub-bundle 路径，不内联全文，Qoder #7）
- dry-run 不写任何文件

#### AC-5 (cache 更新)
- 跑完后 `.louke/wiki/.cache.toml` 的 `last_distill = yesterday`
- dry-run 不更新 cache

#### AC-6 (幂等)
- 重跑 compact 在无新 resolved raw 时：
  - bundle 内容不变
  - cache 不变（或仅 last_distill 推进到昨天，前提是有 raw 落入窗口）

### FR-0080.2 `cmd_rewrite`

#### AC-1 (子命令存在)
- `lk librarian rewrite` 命令存在
- 接受 `--model` / `--model-from-config` / `--full` / `--dry-run` flag

#### AC-2 (bundle 检查)
- 找不到 `.compact-bundle.md` 且无 `.compact-bundle-manifest.md` → stderr 报 "请先跑 lk librarian compact"，exit 1

#### AC-3 (shell-out)
- dry-run: stdout 打印 `opencode run --agent librarian [--model <id>] -- <prompt>`，不实际调用
- 实际跑: `subprocess.run(['opencode', 'run', '--agent', 'librarian', ...])`，exit code 透传

#### AC-4 (bundle 选择)
- `.compact-bundle-manifest.md` 存在 + 未传 `--full` → 透传 Map-Reduce prompts（map × N + reduce × 1）
- 其他情况 → 透传 `.compact-bundle.md`

---

## FR-0090 cron 触发 + 跳日 catch-up

### AC-1 (cron 入口)
- 用户 crontab 含 `0 4 * * * cd <project> && <lk> librarian compact >> .louke/wiki/.cron.log 2>&1`
- **cron entry 命令是 `compact`，不是 `daily` / `from-raw`**（FR-0150 已实施）

### AC-2 (跳日 catch-up)
- 假设周X 04:00 cron 跑，`last_distill = 周X-3`
- 当天 `yesterday = 周X-1`
- window = `[周X-3, 周X-1]`，跨 3 天
- `last_distill` 推进到周X-1

### AC-3 (rewrite 不自动)
- 默认 cron 只调 `compact`，**不**调 `rewrite`
- 需用户显式 `lk librarian rewrite` 或加 `--auto-rewrite` flag

---

## FR-0100 raw = append-only journal

### AC-1 (.gitignore)
- `.gitignore` 含 `.louke/raw/` 行
- `git check-ignore .louke/raw/2026-07-04/test.md` exit 0

### AC-2 (python 不改 raw)
- `louke/librarian.py` 全文 `grep raw_dir` 仅出现在 `Path.cwd() / '.louke/raw/'` 读取路径
- 任何写 raw 的路径不存在

### AC-3 (Librarian 不写 raw)
- `louke/agents/Librarian.md` §2.3 permissions 禁止写 `raw/`

---

## FR-0110 `lk librarian lint` 适配

### AC-1 (已有检查保留)
- broken links 检查（`[[wikilink]]` 目标不存在 → high）
- orphaned pages 检查（无任何 wikilink 引用 → low）

### AC-2 (新增 frontmatter 检查)
- 缺 `type` / `date` / `title` 字段 → high（blocking）
- 排除自动生成文件 `index.md` / `log.md` / `overview.md`（由 Librarian 维护, 不要求 frontmatter）

### AC-3 (新增重复主题检查)
- 多 page 描述同一主题（按 `title` frontmatter 或首标题匹配）→ 提示合并（**不自动合并**, medium, 不阻塞）
- 退出码: blocking = critical/high（broken links + missing frontmatter）; orphaned pages + duplicate topics 仅报告

### AC-4 (已知 bug 标注)
- `cmd_rebuild_index` 当前生成扁平列表（librarian.py:177-197）
- 与 Librarian.md §4 "按类型 + 按日期" 二维布局不一致
- 本 spec 不修复，v0.7-003 处理

---

## FR-0130 `lk librarian rewrite` 通过 `opencode run --agent` 调 LLM

### AC-1 (不调 LLM SDK)
- `grep -E 'import openai|import anthropic' louke/librarian.py` 无命中
- LLM 调用统一通过 `subprocess.run(['opencode', ...])`

### AC-2 (CLI 模式 prompt)
- `cmd_rewrite` 内嵌 prompt 显式说明"CLI 批处理模式（通过 `opencode run --agent librarian` 启动）"
- prompt 包含 bundle 路径 + 蒸馏指令 + 整体重写约束

### AC-3 (frontmatter 兼容)
- Librarian frontmatter `permission.question: deny`（v0.6-009）不变
- CLI 模式下 LLM 不调 question 工具（permission 阻止）

---

## FR-0140 分层蒸馏策略

### FR-0140.0 模式选择

#### AC-1 (模式表)
- `cmd_compact` 按 `total_tokens = sum_chars / 4` 估算 token
- total ≤ `--threshold-tokens` (默认 50K) → M0
- threshold < total ≤ `--m2-threshold` (默认 200K) → M1 + stderr warning 提示 `--model gemini-1.5-pro` / `claude-sonnet-4`
- total > m2-threshold → M2

### FR-0140.1 bundle 清理 (P0-3 / P1-4)

#### AC-1 (compact 步骤 1 清理)
- `cmd_compact` 步骤 1 删除 `.louke/wiki/.compact-bundle*.md`
- 删除前 stdout 报告 `[compact] 清理 N 个旧 bundle`

#### AC-2 (dry-run 不清理)
- `lk librarian compact --dry-run` 不删除任何文件
- `lk librarian compact --dry-run` 不更新 `.cache.toml`

#### AC-3 (M2 切换不重复)
- 旧 `.compact-bundle.md` 残留时，下一次 M2 compact 仍只产 monthly bundle + manifest（不重复旧单 bundle）
- `cmd_rewrite` 的 M2 map 循环不包含旧 `.compact-bundle.md`

### FR-0140.2 `cmd_compact` 自动分块

#### AC-1 (M0 模式)
- token ≤ 50K → 单 bundle `.compact-bundle.md`
- 包含 raw 全文 + 现有 pages + 蒸馏指令

#### AC-2 (M1 模式)
- 50K < token ≤ 200K → 单 bundle + stderr warning
- 不强制 `--model`，但 warning 强烈建议

#### AC-3 (M2 模式)
- token > 200K → 按 `file_date[:7]` (YYYY-MM) 分块
- 每个 month 一个 `.compact-bundle-{month}.md`
- 末尾追加 `.louke/wiki/.compact-bundle-manifest.md`（仅列出 sub-bundle 文件名 + token 数，不内联全文）

### FR-0140.3 `cmd_rewrite` 多模式支持

#### AC-1 (M0/M1 single-shot)
- `.compact-bundle.md` 存在 + 无 `.compact-bundle-merged.md` → 单次 LLM 调用
- prompt 引用 `.compact-bundle.md`

#### AC-2 (M2 map-reduce)
- `.compact-bundle-manifest.md` 存在 → M2 模式
- `cmd_rewrite` 调用 N 次 map + 1 次 reduce（Qoder #4 Map-Reduce 真实施）
- map prompt 引用对应 `.compact-bundle-{YYYY-MM}.md` + 写到 `.distillations/{YYYY-MM}.md`
- reduce prompt 引用 `.distillations/*.md` + 整合到 `pages/`
- map 任一失败 → abort, reduce 不跑

#### AC-3 (基线 vs 扩展 prompt)
- FR-0130 prompt 是**基线版**（M0/M1）
- FR-0140.3 M2 prompt 是**扩展版**（map + reduce 拆开）
- 两者结构一致，仅模式相关字段变量化

### FR-0140.4 模型优先级链 (P1-7)

#### AC-1 (优先级)
- `--model <id>` + `--model-from-config` 同时传 → `--model` 胜出（`--model-from-config` 静默忽略）
- 都未传 → OpenCode 用 frontmatter `models:` 第一项

#### AC-2 (--model 透传)
- `lk librarian rewrite --model gemini-1.5-pro`
- → shell-out `opencode run --agent librarian --model gemini-1.5-pro -- <prompt>`

#### AC-3 (--model-from-config 解析)
- `lk librarian rewrite --model-from-config`
- → 调 `subprocess.run(['lk', 'models', 'bind', '--get-current'])` 取绑定模型
- 成功 → 透传给 opencode
- 失败 → 不传 `--model`，OpenCode 用 frontmatter 第一项

#### AC-4 (M2 warning)
- M2 模式 + 未指定 `--model` → stderr warning "建议 --model gemini-1.5-pro (1M context)"
- **不**自动 fallback（避免静默换模型）

---

## FR-0150 `lk init --install-cron` 目标改为 `lk librarian compact`

### AC-1 (cron entry 修复)
- `louke/init.py:_install_cron()` 生成的 cron line 含 `lk librarian compact`（**不是** `lk librarian daily`）
- `grep -n 'librarian (daily\|compact)' louke/init.py` 显示 `compact`
- **已实施**: `louke/init.py:167`

### AC-2 (职责边界)
- v0.7-001 不含 cron 安装（pre-commit 框架接管）
- v0.7-002 FR-0150 显式归属 cron 安装
- `lk init` 默认 `--install-cron`，`--no-cron` 跳过

### AC-3 (幂等安装)
- 重复 `lk init` → 检测到 marker `# louke:wiki-distill:<abs-path>` 跳过
- 用户手动改 cron entry → `lk init` 不覆盖

---

## FR-0120 Librarian Identity 框架对齐

### AC-1 (Identity 英文)
- `louke/agents/Librarian.md` §1 标题 "Identity & Runtime Context (Subagent)"
- §1 正文英文（说明 subagent 模式 + 非交互）

### AC-2 (tools 英文)
- §2.1 tools 英文（allow / deny 列表）
- §2.2 skills 英文（inline-comments + reserve-memory）
- §2.3 permissions 英文（带 bundle 写入权属澄清，P1-6）

### AC-3 (CLI 表)
- §2.1 含 `lk librarian` CLI 表（compact / rewrite / distill / lint / rebuild-index）
- 每个子命令的功能描述

### AC-4 (调用模式识别段)
- §"调用模式识别"段说明 TUI subagent vs CLI 批处理
- CLI 模式不应调 question（无 UI）

### AC-5 (webfetch / websearch / external_directory: deny)
- Librarian frontmatter 三者均 `deny`
- 与 v0.6-009 FR-0010.4 一致

---

## §0.4 wiki 命名空间处理 (P1-5)

### AC-1 (entries/ deprecated)
- `louke/agents/Librarian.md` §2.3 permissions 禁止写 `.louke/wiki/entries/`
- 现有 7 个 entries/ 文件保留至 v0.7-003 决定迁移/删除

### AC-2 (consolidated.md deprecated)
- 同上处理

### AC-3 (decisions/ 不在 rewrite 范围)
- `cmd_rewrite` prompt 不引用 `.louke/wiki/decisions/`
- LLM 整体重写 pages/ 时**不**改 decisions/ 下任何 ADR
- 008 编号重复问题 → v0.7-003 处理

### AC-4 (decisions 写入权属)
- `louke/agents/Librarian.md` §2.3 permissions `decisions/` 不在 LLM `edit` 白名单
- python CLI 不写 decisions/（仅 spec 级 ADR 由相关 Agent 写）

---

## NFR-0010 向后兼容

### AC-1 (lk librarian daily 删除)
- `lk librarian daily` 报 "unknown command"
- 既有 cron entry 指向 `daily` → cron 日志持续报错（用户需手动改 cron 或重跑 `lk init`）

### AC-2 (lk librarian from-raw 删除)
- `lk librarian from-raw` 报 "unknown command"
- 替代: `lk librarian compact` + `lk librarian rewrite`

### AC-3 (lk librarian distill 保留)
- `lk librarian distill --source X --target Y` 仍可用
- 语义改为 wrapper 调 `compact --dry-run`

### AC-4 (lk librarian lint 不变)
- flag `--wiki` 不变
- 现有 broken links / orphaned pages 检查保留

---

## NFR-0020 Python 3.9 兼容

### AC-1 (无 PEP 604 语法)
- `grep -E '\| None|\[\[' louke/librarian.py | grep -v '#'` 无 `bool \| None` 之类语法
- `tuple` 无参数化

### AC-2 (无 tomli_w 强制)
- `_write_cache` 有 tomli_w fallback（手工构造 TOML）
- Python 3.9 无 tomli_w 也能跑

---

## NFR-0050 可审计

### AC-1 (cron 日志)
- `.louke/wiki/.cron.log` 含每次 compact 的输出
- 包含 `[compact]` 前缀的窗口 + token 估算 + 模式选择

### AC-2 (compact dry-run)
- `lk librarian compact --dry-run` 打印计划：
  - 窗口 [last_distill, yesterday]
  - token 估算 + 模式选择 (M0/M1/M2)
  - bundle 文件名 (但不写)
  - skipped no-date 列表

### AC-3 (rewrite dry-run)
- `lk librarian rewrite --dry-run` 打印：
  - bundle 选择 (main / merged)
  - 模型 (--model / --model-from-config / default)
  - shell-out 命令预览

---

## 关联文件覆盖度（与 spec §6 一致性）

| 文件 | AC 引用 |
|---|---|
| `louke/librarian.py` | FR-0070 AC-3 / FR-0080 全部 / FR-0130 AC-1 / FR-0140 全部 / NFR-0020 全部 |
| `louke/init.py` | FR-0150 全部 |
| `louke/agents/Librarian.md` | FR-0070 AC-1 / FR-0100 AC-3 / FR-0120 全部 / §0.4 AC-1 |
| `.gitignore` | FR-0100 AC-1 |
| `tests/test_librarian_compact.bats` | FR-0080/0090/0140/0150 全部 |
| `tests/test_librarian_rewrite.bats` | FR-0130/0140.4 全部 |
| `README.md` / `README.zh.md` | FR-0070 引用 |
