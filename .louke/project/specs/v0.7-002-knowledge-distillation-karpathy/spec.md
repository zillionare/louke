# v0.7-002 — 知识蒸馏（Karpathy 风格）— Spec

- **Spec ID**: v0.7-002-knowledge-distillation-karpathy
- **创建日期**: 2026-07-05
- **修订**:
  - 2026-07-05 21:30 初稿（Kilo 起草，聚焦知识蒸馏；跨语言质量门禁内容已拆分到 `v0.7-001-pre-commit-quality-gates`）
- **状态**: 草稿（待 Sage 起草 / Lex 复核 / Aaron 拍板）
- **关联**:
  - **关键参考**：Karpathy [autoresearch](https://github.com/karpathy/autoresearch) — 知识蒸馏的核心思想来源（`train.py` = current best state，git history = journal）
  - 受影响下游：v0.6-009 FR-0010.4 Librarian permission（CLI 模式兼容，`permission.question: deny` 无需改）
  - 受影响下游：既有 `lk librarian from-raw` / `lk librarian distill`（机械 copy，违反"投影而非积累"，需替换）

---

## 0. 范围与边界

### 0.1 本 spec 收纳（v0.7.0 一次性发版）

| 主题 | FR 范围 |
|---|---|
| 知识蒸馏三原则（raw = journal / pages = projection / 整体重写） | FR-0070 |
| `lk librarian compact` / `lk librarian rewrite` 实现 | FR-0080 |
| cron 触发 + 跳日 catch-up | FR-0090 |
| raw = append-only journal（不进 git） | FR-0100 |
| `lk librarian lint` 适配重写模型 | FR-0110 |
| LLM 调度机制（`opencode run --agent librarian`） | FR-0130 |
| 上下文窗口应对（增量 / 全量 / Map-Reduce 分层） | FR-0140 |
| `lk init --install-cron` 目标改为 `lk librarian compact` | FR-0150 |
| Librarian 文档 Identity 框架对齐（Devon 框架英文） | FR-0120 |
| 受影响下游 + supersede + 可降级 | §0.2 / NFR-0010 / NFR-0020 |

### 0.2 受影响下游 / supersede

- **既有 `lk librarian from-raw`**（机械 copy raw → pages）—— **SUPERSEDED by FR-0080**：删除；改用 `cmd_compact`（准备 bundle）+ `cmd_rewrite`（LLM 整体重写）
- **既有 `lk librarian distill`**（仅 print 待蒸馏列表）—— **保留 + 重定义**：语义改为"列出待 compact 的 raw"，由 `cmd_distill` 改为 wrapper 调 `cmd_compact --dry-run`
- **既有 `lk librarian lint`** —— **扩展**（FR-0110）：新增"重复主题" / "缺 frontmatter 必填字段"检查项
- **既有 `lk librarian daily`**（本会话初版）—— **SUPERSEDED by FR-0080 / FR-0090**：拆分 `compact` + `rewrite` 两个子命令；cron 默认调 `compact`，`rewrite` 显式触发
- **既有 `louke/agents/Librarian.md`** —— **重写**（FR-0120）：Identity / tools / permissions 段对齐 Devon 框架（英文）；§5 改写（cron 触发 + compact/rewrite 子命令 + 窗口 [last_distill, 昨天]）

### 0.3 本 spec 不收纳

- 跨语言质量门禁 —— 已拆分到 `v0.7-001-pre-commit-quality-gates`（pre-commit 框架接管）
- `lk agent lint` 校验 wiki 文件 schema —— 留 v0.7-003
- raw/ 历史的自动归档 / 压缩 —— raw 是 journal，append-only，不删不改
- LLM 调用的具体 API 实现（OpenAI / Anthropic SDK）—— 走 OpenCode 自身路由，本 spec 仅约束"shell-out 到 OpenCode CLI"
- 矢量检索 / RAG —— 留 v0.7.1+，M2 Map-Reduce 兜底（FR-0140.1）
- `lk init --install-cron` 的实现 —— **已迁移至 FR-0150**（v0.7-002 实施）

### 0.4 wiki 命名空间处理策略（P1-5）

实际 wiki 结构（louke/.louke/wiki/）：

```
pages/         — 7 文件，本 spec 聚焦
decisions/     — 11 ADR 文件（含 008 编号重复），rewrite 范围**外**
entries/       — 7 legacy 文件（迁移前产物），**DEPRECATED**
consolidated.md — legacy 整合文件，**DEPRECATED**
index.md / log.md / overview.md — Librarian 维护
```

| 路径 | 状态 | 本 spec 处理 |
|---|---|---|
| `pages/*.md` | 主要目标 | rewrite 重写范围 |
| `index.md` / `log.md` / `overview.md` | 索引与日志 | FR-0080 rewrite 后由 LLM 调 `rebuild-index` + `lint` 刷新 |
| `.cache.toml` | 持久状态（`last_distill` + SHA256） | compact 写入 |
| `.compact-bundle*.md` | **临时中间产物** | FR-0140.2 compact 开始清理 |
| `decisions/*.md` | ADR 档案 | **不纳入 rewrite**（rewrite 不改 ADR）；008 编号重复问题 → **留 v0.7-003** 决定 |
| `entries/*.md` | legacy 迁移产物 | **DEPRECATED**：本 spec §0.3 声明 deprecated，Agent 不再写 entries；现有 7 个文件保留至 v0.7-003 决定是否迁移到 `pages/` 或删除 |
| `consolidated.md` | legacy 整合文件 | **DEPRECATED**：同上处理 |

---

## 1. 用户故事

### A. 投影而非积累

#### US-0100 wiki 只显示当前决策

- US-0100: 作为 wiki 读者，我希望 wiki 只显示**当前**决策，不带任何**过时**知识 —— 过期决策在新 raw 出现后自动消失
- US-0110: 作为 raw session 写入者，我希望 raw 是 append-only 的 journal（保留试错与未决），不被任何"清理"动作触碰

### B. 整体重写而非补丁

#### US-0200 整体重写一致性

- US-0200: 作为 LLM 蒸馏的执行者（Librarian subagent），我希望每次更新都是**整体重写** pages/，不是 patch 现有页面 —— 这样不会出现"页面 A 是旧决策 + 页面 B 是新决策，互相打架"的不一致状态
- US-0210: 作为 LLM，我希望每次重写前能拿到一份**context bundle**（含 raw 全文 + 现有 pages/ + 蒸馏指令），不是只拿到"自上次以来新增的 raw" —— 这样能基于全局重新判断哪些决策仍成立

### C. 触发机制

#### US-0300 自动触发 + 幂等

- US-0300: 作为项目所有者，我希望知识蒸馏由系统级 cron 每日自动触发，无需我手动跑 —— 这样即便我忘记，wiki 也不会停滞
- US-0310: 作为 cron 用户，我希望重跑 cron 是幂等的 —— 即便某天 cron 因故没跑，下一天会自动 catch-up `[last_distill, 昨天]` 区间，不会漏处理

### D. 上下文窗口可扩展

#### US-0400 raw 累积不撑爆 LLM

- US-0400: 作为 louke 长期使用方（1 年 + 数百 session），我希望 raw 累积超出任何模型窗口时，蒸馏仍能完成 —— 通过自动分块 / 选用大模型 / Map-Reduce 等策略
- US-0410: 作为常规使用方（数月内 < 200 session），我希望默认走"增量"模式，**不**消耗大模型 quota

### E. 文档对齐

#### US-0500 Librarian Identity 框架对齐

- US-0500: 作为 agent prompt 维护者，我希望 Librarian 的 §1 Identity / §2 tools 段框架对齐 Devon.md（英文），便于跨 agent 培训新人

---

## 2. 关键场景

### scenario-0100 整体重写（incremental 模式）

```
# 现状: raw/ 有 14 条 resolved session, pages/ 有 3 条旧 wiki
$ ls .louke/raw/2026-06-*/
...14 个 *.md 文件, 全部 status: resolved

$ ls .louke/wiki/pages/
old-decision-x.md  old-api-v1.md  old-feature-y.md

# 1. compact: 准备 bundle
$ lk librarian compact
[compact] 扫描 raw: 14 条 resolved
[compact] 写 bundle: .louke/wiki/.compact-bundle.md (含全部 14 raw + 现有 3 pages)
[compact] 更新 .cache.toml: last_distill = 2026-07-04

# 2. rewrite: LLM 整体重写 (cron 不自动跑; 用户手动或 --auto-rewrite)
$ lk librarian rewrite
[rewrite] shell-out: opencode run --agent librarian -- <prompt>
... LLM 读 bundle → 重写 pages/ → 调 lk librarian rebuild-index + lint ...
[rewrite] exit 0

# 3. 结果
$ ls .louke/wiki/pages/
current-decision-x.md     # 旧 "old-decision-x" 已过期, 被新名替换
current-api.md            # 旧 "old-api-v1" 与新决策合并
new-feature-z.md          # 全新条目
# 注意: 不再有 old-* 前缀; 旧 "old-api-v1.md" 因过期被整体替换

$ lk librarian lint
=== Wiki Lint ===
[broken links] 0
[orphaned pages] 0
→ wiki 健康
```

### scenario-0200 cron 跳日 catch-up

```
# 用相对日期: Day N 表示"今天" (= cron 实际触发日).
# 关键不变式: 窗口上限始终是"昨天" (今天 - 1), 不是"今天".
# 这与 cmd_compact 实现一致: yesterday = (today - timedelta(days=1)).isoformat()

$ crontab -l
0 4 * * * cd <project> && lk librarian compact >> .louke/wiki/.cron.log 2>&1

# ===== Day 1 (周四) — 正常运行 =====
[compact] cache.last_distill 未设置, 从 1970-01-01 开始处理所有历史 raw
[compact] 蒸馏窗口: [1970-01-01, Day0]   # yesterday = Day1 - 1 = Day0
[compact] token 估算: <N>  (M0 模式)
[compact] 写 .compact-bundle.md
[compact] → .cache.last_distill: (unset) → Day0

# ===== Day 2 (周五) — 机器关机, cron 没跑 =====
# (no log entry)

# ===== Day 3 (周六) — 开机, cron 重新触发 =====
[compact] 上次蒸馏: Day0 (跳过了 Day1)
[compact] 蒸馏窗口: [Day0, Day2]      # yesterday = Day3 - 1 = Day2, catch-up 跨 3 天
[compact] → .cache.last_distill: Day0 → Day2

# ===== Day 4 (周日) — 正常运行 =====
[compact] 上次蒸馏: Day2
[compact] 蒸馏窗口: [Day2, Day3]      # yesterday = Day4 - 1 = Day3
[compact] → .cache.last_distill: Day2 → Day3
```

**易错点**（实施时注意）：
- 窗口上限 = `date.today() - timedelta(days=1)`，**不是** `date.today()`
- 若 cron 在凌晨 04:00 跑，"今天"是 cron 触发日；昨天 = cron 触发日 - 1
- 跳日 catch-up 时窗口可能跨度大（3 天、7 天），仍按 `[last_distill, yesterday]` 计算

### scenario-0300 上下文窗口超出（Map-Reduce 模式 M2）

```
# 累积 1 年: 400K tokens 超出任何模型窗口
$ lk librarian compact
[compact] 总 token 估算: 412,500 (超出 200K 阈值)
[compact] 按月分块: 12 个 bundle
  + .compact-bundle-2026-01.md (32K)
  + .compact-bundle-2026-02.md (35K)
  ...
  + .compact-bundle-2026-12.md (38K)
  + .compact-bundle-manifest.md (引用所有 12 bundle)
[compact] 更新 .cache.toml: last_distill = 2026-12-31

$ lk librarian rewrite
[rewrite] 检测到 13 个文件 (12 monthly + 1 manifest)
[rewrite] Map phase: 调用 12 次 opencode run --agent librarian (每块产 mini-distillation)
[rewrite] Reduce phase: 调用 1 次 opencode run --agent librarian (合并所有 mini-distillation)
[rewrite] exit 0
```

### scenario-0400 LLM 在 CLI 模式下不弹问题

```
# cron 跑 lk librarian rewrite
$ opencode run --agent librarian -- "..."
[OpenCode session 启动, librarian 作 primary]
[OpenCode] Agent has 200K context, 400K tokens incoming
[OpenCode] Token 超出, model gemini-1.5-pro 自动选用 (louke models bind)
... LLM 推理 ...
[OpenCode] Wrote .louke/wiki/pages/current-decision-x.md
[OpenCode] Wrote .louke/wiki/pages/current-api.md
[OpenCode] exit 0

# 注意: LLM 没有调 question 工具 (CLI 无 UI, permission.question: deny 阻止)
# 这是设计行为, 不是 bug
```

---

## 3. 功能需求

### A. 知识蒸馏（Karpathy 化）

#### FR-0070 三原则

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

基于 Karpathy [autoresearch](https://github.com/karpathy/autoresearch) 的 `train.py` 模型：

1. **`raw/` = journal**：所有 Agent session append-only；保留试错、未决、过时决策；不删不改
2. **`pages/` = current understanding (projection)**：每次更新是**整体重写**，不是 patch；过期条目随重写消失
3. **python 脚本不直接调用 LLM SDK**：脚本只做机械工作（compact / lint / rebuild-index）；distillation 推理通过 `opencode run --agent librarian` CLI 入口完成（P2-9 修正）。"不调 LLM API" 措辞特指不 `import openai / anthropic SDK` 发送 HTTP 请求

#### FR-0080 `lk librarian compact` / `lk librarian rewrite`

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

**删除** `cmd_from_raw`（错误：机械 copy raw → pages，违反"投影而非积累"）。

**新增**两个子命令：

##### `lk librarian compact`

- **谁做**：python 脚本（cron 友好）
- **做什么**：
  0. **清理旧 bundle**（FR-0140.2）：删除 `.compact-bundle*.md`（P0-3 / P1-4）
  1. 扫描 `.louke/raw/**/*.md` 找 `status: resolved` 条目
  2. **无 `date` 字段的条目跳过 + warning**（P1-8，详见下方）
  3. 按 `date` 字段过滤 `[last_distill, 昨天]`
  4. 拼出 `.louke/wiki/.compact-bundle.md`，含：
     - 所有匹配 raw 全文（append-only 不可修改）
     - 现有 `pages/` 内容（如存在）
     - 蒸馏指令（基于 raw + 现有 pages 整体重写，保留仍成立决策，删除/更新过时决策，补充新主题，每条 wiki 决策必须能从 raw 找到依据）
  5. 更新 `.louke/wiki/.cache.toml` 的 `last_distill = 昨天`
  6. **若 token 估算 > 阈值**：按月分块产 `.compact-bundle-{YYYY-MM}.md` + 末尾 `.compact-bundle-manifest.md`（参 FR-0140；manifest 仅列 sub-bundle 路径，rewrite 走真 Map-Reduce，Qoder #4 / #7）
- **副作用**：只写 `.compact-bundle*.md` + `.cache.toml`；**不**写 `pages/`
- **幂等**：再跑一次若无新 resolved raw，bundle 内容不变 + cache 不变（P2-11 修正）
- **`--dry-run`**：仅打印计划，不写文件、不更新 cache、不清理 bundle

**P1-8 — 无 `date` 字段的 raw 处理**：

无 `date` 字段的 raw 条目被**跳过 + warning**（不进入 bundle，不计入 M0/M1/M2 token 估算）：

```python
date_m = re.search(r'^date:\s*(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
file_date = date_m.group(1) if date_m else ''
if not file_date:
    skipped_no_date.append(fp)
    continue
```

**理由**：
- 无 `date` 的条目无法参与 `[last_distill, 昨天]` 窗口过滤
- 无 `date` 也无法参与 M2 按月分块
- 若无条件包含，会污染重写结果（LLM 无法判断该决策的时间边界）
- warning 而非报错：保留人工修复入口（用户可补 `date` 字段后再跑 compact）

**输出**（stdout）：

```
[compact] WARN: 3 个 raw 条目无 date 字段, 已跳过:
  - .louke/raw/2026-06-15/no-date-1.md
  - .louke/raw/2026-06-22/no-date-2.md
  - .louke/raw/2026-07-01/no-date-3.md
```

##### `lk librarian rewrite`

- **谁做**：python 脚本 → shell out → **`opencode run --agent librarian`**（CLI 模式，参 FR-0130）
- **python 脚本职责**（轻量，不调 LLM API）：
  1. 检查 `.compact-bundle.md` 存在（compact 必须先跑）
  2. shell out：`opencode run --agent librarian [--model <id>] -- <prompt>`，prompt 含 bundle 路径 + 蒸馏指令
  3. 捕获 exit code（0 = rewrite 完成且 lint 通过；1 = 失败）
  4. 退出码透传给 cron / 调用方
- **LLM 在 OpenCode 内做什么**（由 Librarian prompt 驱动，**基线版**见 FR-0130；**M2 扩展版**按月分块 map → 合并 reduce，见 FR-0140.3 P2-14 澄清）：
  1. 读 `.louke/wiki/.compact-bundle.md`（bundle = raw 全文 + 现有 pages/ + 蒸馏指令）
  2. 读 `.louke/wiki/pages/` 全部现存页面
  3. **整体重写** pages/：
     - 保留仍成立的决策
     - 删除/合并过时的
     - 补充新出现的主题
     - 每条 wiki 决策必须能从 raw 中找到依据（quote dialogue 语法，详见 v0.4-004-quote-dialogue）
  4. **不**保留旧 page 文件名 —— 重写后整体替换
  5. 重写后调 `lk librarian rebuild-index` + `lk librarian lint`
- **Librarian 在 CLI 模式下行为差异**（v0.6-009 已支持）：
  - `permission.question: deny` —— CLI 模式无 UI，匹配现有 deny 配置，无需改 frontmatter
  - `permission.edit: allow` —— CLI 模式仍允许写 `pages/`
  - prompt 区分两种调用模式（参 FR-0120.1）

#### FR-0090 cron 触发 + 跳日 catch-up

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

cron 入口（由 **FR-0150** 安装）跑 `lk librarian compact`（**不**含 rewrite）。

**窗口逻辑**（在 `cmd_compact` 内）：
- 读 `.cache.toml:last_distill`
- 若为空 → 首次运行，window = `[1970-01-01, 昨天]`（处理所有历史）
- 否则 → window = `[last_distill, 昨天]`（处理上次到今天）
- 跑完后 `.cache.toml:last_distill = 昨天`

**跳日语义**：若周四 cron 失败，周六重跑，window = `[2026-07-02, 2026-07-04]`，catch-up 跨 3 天。

**rewrite 触发**：默认**不**由 cron 触发（避免半夜 token 烧光 + 需人工审视重写结果）。可选 `--auto-rewrite` flag 让 cron 跑 `compact` + `rewrite` 双步。

#### FR-0100 raw = append-only journal

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- `raw/` 不进 git（写入 `.gitignore`）
- python 脚本不删 / 不改 raw 下任何文件（除 `compact` 写入 `.compact-bundle*.md` 在 wiki/，不在 raw/）
- 各 source agent 自己写 raw（Librarian **不**写 raw）
- `status` 字段语义：Agent 写 raw 时必填 `status: open | resolved | superseded`；Librarian 仅读 `status: resolved`

#### FR-0110 `lk librarian lint` 适配

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

`cmd_lint` 当前**已实现**的检查（librarian.py:79-129）：
- broken links（`[[wikilink]]` 目标不存在）
- orphaned pages（无任何 wikilink 引用）

**首次实现**检查项（P2-12 修正 — 现状代码无，FR-0110 首次落地）：
- **缺 frontmatter 必填字段**（`type` / `date` / `title`） → high 严重度
- **重复主题**（多 page 描述同一主题） → 提示合并（**不自动合并**，由人决策）

**注**：P2-13 — 现有 `cmd_rebuild_index`（librarian.py:131-151）只生成扁平 `- [[stem]] (path)` 列表，未实现 Librarian.md §4 "按类型 + 按日期" 二维布局。本 spec 不修复（v0.7-003 处理），但需知晓：rewrite prompt 让 LLM 调 `rebuild-index` 后，index.md 会是扁平列表，与 §4 agent prompt 不一致。

---

### B. LLM 调度机制

#### FR-0130 `lk librarian rewrite` 通过 `opencode run --agent` 调 LLM

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

**问题**：cron 跑 `lk librarian rewrite` 时需要 LLM 写 pages/。python 脚本**不**调 LLM API（避免 SDK 耦合 + token 计费穿透 python）。需要 OpenCode 提供 CLI 入口调 LLM 跑 agent。

**方案**：shell out 到 `opencode run --agent librarian -- <prompt>`，由 OpenCode 在新 session 内启 LLM 跑 Librarian primary，agent 自行完成 pages/ 重写。

**实现**（`louke/librarian.py:cmd_rewrite`）：

```python
def cmd_rewrite(args):
    """触发 LLM 整体重写 pages/. 调用 opencode run --agent librarian."""
    bundle = Path.cwd() / '.louke' / 'wiki' / '.compact-bundle.md'
    if not bundle.exists():
        print('error: .compact-bundle.md 不存在, 请先跑 lk librarian compact', file=sys.stderr)
        return 1

    if args.dry_run:
        print(f'[dry-run] 将 shell-out: opencode run --agent librarian [--model {args.model}] -- <prompt>')
        return 0

    prompt = f'''
你是 Librarian subagent，处于 CLI 批处理模式（通过 `opencode run --agent librarian` 启动）。

任务：基于 raw 整体重写 wiki pages/。

输入：
1. 读 {bundle}（含 raw 全文 + 现有 pages/ + 蒸馏指令）
2. 读 .louke/wiki/pages/ 全部现存页面

输出：
1. **整体重写** .louke/wiki/pages/（不是 patch）：
   - 保留仍成立的决策
   - 删除/合并过时的
   - 补充新出现的主题
   - 每条 wiki 决策必须能从 raw 中找到依据（quote dialogue 语法）
2. 跑 `lk librarian rebuild-index` 重建 index.md
3. 跑 `lk librarian lint` 健康检查；如有 broken links / 缺失 frontmatter 自愈

完成后 exit 0。如 lint 不过自愈不了 exit 1。
'''
    cmd = ['opencode', 'run', '--agent', 'librarian']
    if args.model:
        cmd += ['--model', args.model]
    cmd += ['--', prompt]
    rc = subprocess.run(cmd).returncode
    return rc
```

**`opencode run --agent` 行为契约**（基于 v0.6-009 FR-0070.7）：

| 维度 | TUI `task` 工具 | CLI `opencode run --agent` |
|---|---|---|
| 调用者 | Maestro 在主会话内 | python 脚本 / 用户 shell |
| agent 角色 | subagent（隔离子会话） | primary（新 session） |
| `permission.question: allow` 行为 | 弹框冒泡到主窗口 | 无 UI，prompt 走 stdout |
| 适用 | Louke 工作流（M-FOUND → ...） | **cron 批处理 / CI** ← FR-0130 |
| 退出码 | 由 OpenCode 子会话退出码 | 由 OpenCode session 退出码 |

**为什么选 `opencode run --agent librarian` 而不是别的方式**：

| 替代方案 | 否决理由 |
|---|---|
| python 直接调 LLM API（OpenAI / Anthropic SDK） | 需 SDK 依赖 + token 计费穿透 + 模型路由与 louke `models.py` 解耦 |
| python 调 OpenCode HTTP API | OpenCode 没有公开 HTTP API |
| **CLI `opencode run --agent`** | **唯一非交互式调度路径，与 louke 模型路由一致，无 SDK 依赖** |

**Librarian prompt 适配（FR-0120.1）**：

`louke/agents/Librarian.md` 加 §"调用模式识别"段：

> 你可能被两种方式调起：
> 1. **TUI subagent 模式**：Maestro 调 `task` 启动你；可调 `question` 工具向用户提问
> 2. **CLI 批处理模式**：`opencode run --agent librarian -- "..."` 启动你（无 UI）；你**不**应调 `question`（无 UI 会卡住）
>
> 在 CLI 模式下，按 FR-0130 prompt 完成整体重写；完成后正常 exit。

---

### C. 上下文窗口应对

#### FR-0140 分层蒸馏策略

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

**问题**：louke raw 累积速度远超任何模型上下文窗口：

| 时间窗 | session 数（估） | 累计 token | 适配窗口 |
|---|---|---|---|
| 1 周 | 5-10 | 5K-15K | 所有模型 OK |
| 1 月 | 20-50 | 30K-80K | 32K+ 模型 |
| 1 quarter | 60-150 | 100K-250K | Claude Sonnet 200K / Gemini 1.5 Pro |
| 1 年 | 200-500 | 400K-1M | **超出所有模型**，必须分块 |

**核心策略**：按 token 量自动选择蒸馏模式。

##### FR-0140.1 模式选择表（由 `cmd_compact` 自动判定）

| 模式 | 触发条件 | 总 token | 蒸馏路径 | LLM 调用次数 |
|---|---|---|---|---|
| **M0: 增量模式**（默认） | `last_distill - yesterday` 区间 ≤ 50K tokens | ≤ 50K | 单次 `opencode run --agent librarian`，bundle 全量喂入 | 1 |
| **M1: 全量模式** | 50K-200K tokens | 50K-200K | 单次，但用 `--model` flag 指定 200K+ 模型 | 1 |
| **M2: Map-Reduce 模式** | 200K-1M tokens | 200K-1M | 按 issue / 月分块 map → reduce 合成 | 块数 + 1 |
| **M3: 层级摘要模式** | > 1M tokens | > 1M | 多层摘要索引（罕见，v0.7.1+） | 多轮 |

##### FR-0140.2 `cmd_compact` 自动分块（实现要点）

```python
def cmd_compact(args):
    # 1. 清理旧 bundle (P0-3 + P1-4: bundle 不持久化)
    _cleanup_old_bundles(wiki_dir)  # 删除 .compact-bundle*.md

    matched, skipped_no_date = scan_resolved_raw(since=args.since, until=yesterday())
    if skipped_no_date:
        print(f'[compact] WARN: {len(skipped_no_date)} 个 raw 无 date 字段, 已跳过')

    total_tokens = estimate_tokens(matched)  # 字符数 / 4 估算

    if total_tokens <= 50_000:
        # M0: 单 bundle
        write_bundle('.compact-bundle.md', matched)
    elif total_tokens <= 200_000:
        # M1: 单 bundle 但打 warning 提示用大模型
        write_bundle('.compact-bundle.md', matched)
        print(f'[compact] WARN: bundle={total_tokens} tokens, 建议 --model gemini-1.5-pro')
    else:
        # M2: 按 month 分块
        grouped = group_by_month(matched)
        for month, entries in grouped.items():
            write_bundle(f'.compact-bundle-{month}.md', entries)
        write_manifest('.compact-bundle-manifest.md', list_of_bundles=True)
```

**Bundle 清理（**P0-3 / P1-4**）**：

- **为什么清理**：bundle 是 compact 的中间产物（rewrite 一次性消费），不持久化。若不清理：
  - 磁盘累积（每次 compact 写 1+ 个 bundle）
  - **M2 误判**：旧 `.compact-bundle.md` 残留时，`cmd_rewrite` 的 `glob('.compact-bundle*.md')` 会把它当作第 N 个 map 输入，产生重复 mini-distillation
- **清理时机**：`cmd_compact` 步骤 1（在 scan 之前），删除所有 `.compact-bundle*.md`（含 `.compact-bundle.md` / `.compact-bundle-{YYYY-MM}.md` / `.compact-bundle-manifest.md`）
- **不在 `.cache.toml` 清理**：cache 含 `last_distill`，是持久状态，bundle 是临时产物
- **dry-run 不清理**：避免 dry-run 副作用

##### FR-0140.3 `cmd_rewrite` 多模式支持

```python
def cmd_rewrite(args):
    bundles = sorted(glob('.compact-bundle*.md'))
    single = '.compact-bundle.md'

    if single in bundles and len(bundles) == 1:
        # M0/M1: 单次 LLM 调用
        prompt = build_single_prompt(bundles[0])
        return opencode_run('--agent', 'librarian', '--model', args.model, prompt)

    if all(b for b in bundles if b.endswith('-manifest.md')):
        # M2: Map-Reduce
        for b in bundles[:-1]:  # map phase
            prompt = build_map_prompt(b)
            opencode_run('--agent', 'librarian', '--model', args.model, prompt)
        # reduce phase
        prompt = build_reduce_prompt(bundles[-1])  # manifest bundle
        return opencode_run('--agent', 'librarian', '--model', args.model, prompt)
```

##### FR-0140.4 `--model` flag 与优先级链（P1-7 修正）

`lk librarian rewrite` 的模型选择按以下**优先级链**解析（高 → 低）：

```
1. --model <id>             (CLI 显式指定, 透传给 opencode run --model)
2. --model-from-config      (调 `lk models bind --get-current` 取绑定模型)
3. frontmatter models: 第一项 (OpenCode 默认)
```

**实现（`cmd_rewrite`）**：

```python
model_flag = []
if args.model:
    model_flag = ['--model', args.model]                            # 优先级 1
elif args.model_from_config:
    try:
        bound = subprocess.run(['lk', 'models', 'bind', '--get-current'],
                               capture_output=True, text=True, check=False)
        if bound.returncode == 0 and bound.stdout.strip():
            model_flag = ['--model', bound.stdout.strip()]          # 优先级 2
    except FileNotFoundError:
        pass
# 优先级 3: 不传 --model, OpenCode 用 frontmatter models: 第一项
```

**冲突规则**：

- `--model` 与 `--model-from-config` **同时传** → `--model` 胜出（`--model-from-config` 静默忽略，不报错；这样 cron 脚本可无条件加 `--model-from-config` 而人临时 `--model` 时不冲突）
- 都不传 → 不传 `--model` 给 OpenCode，OpenCode 用 Librarian frontmatter 的 `models:` 列表第一项

**上下文窗口超阈值 fallback**：

| 模式 | token 量 | 推荐模型 |
|---|---|---|
| M0 (≤ 50K) | frontmatter 第一项即可 | `minimax-2.7` / `deepseek-v4-flash`（Louke 默认） |
| M1 (50K-200K) | `--model` 显式指定 | `claude-sonnet-4` (200K) |
| M2 (200K-1M) | `--model` 必显式 | `gemini-1.5-pro` (1M) |

超阈值时**不**自动 fallback（避免静默换模型让用户疑惑），由 cmd_rewrite 打 stderr warning 提示：

```bash
# M2 模式下用户忘了 --model
$ lk librarian rewrite
[rewrite] WARN: bundle=412K tokens (M2), 当前模型 minimax-2.7 (32K context)
[rewrite] WARN: 建议 --model gemini-1.5-pro (1M context) 或 claude-sonnet-4 (200K)
[rewrite] shell-out: opencode run --agent librarian -- <prompt>
# (不阻止, 但 LLM 收到 bundle 后会报 token 不足)
```

**注**：本 spec **不**估算 frontmatter `models:` 列表中各模型的上下文窗口（这是 louke 模型路由层职责，不在 v0.7-002 范围）。M2 模式 + 未指定 `--model` 时 Louke 应通过 `lk models bind` 路由到合适的模型（用户责任）。

##### FR-0140.5 Karpathy 风格：增量优先

**默认走 M0**：cron 每日触发，只处理 `[last_distill, 昨天]` 区间，正常情况 ≤ 50K tokens。M1/M2 仅在 catch-up 跨多日 + 累积历史大时触发。

**为什么不全量重写**：
- 全量每次跑耗时 + 耗 token 高
- 大多数日子没有新决策，旧决策不需要重写
- 增量保留"近期决策稳定"的属性，符合 wiki = current understanding 语义

**什么时候全量重写**：
- 用户显式 `lk librarian rewrite --full`（覆盖默认增量）
- v0.7.1+ 加 `--periodic-full` 自动每季度触发（待设计）

##### FR-0140.6 RAG 备选方案（v0.7.1+ 备选，**本 spec 不实现**）

如果 M2 也不够（> 1M tokens）：

| 方案 | 优势 | 劣势 | 选型 |
|---|---|---|---|
| 向量检索 (RAG) | 扩展性最强，按 page 主题取 top-K raw | 需向量库 + embedding 依赖 | 留 v0.7.1+ |
| 文件级 RAG (grep + LLM 选) | 无新依赖，LLM 自己选 | LLM 可能漏选 | **本 spec 默认走这条**（FR-0140.5 增量模式） |
| Map-reduce + 摘要索引 | 中等开销，无新依赖 | 摘要丢失细节 | M2 模式（FR-0140.1） |

本 spec **默认增量**（M0），**兜底 map-reduce**（M2），**不引入向量库依赖**。理由：
1. louke 1-2 个 milestone 内 raw 累计不会 > 1M tokens
2. 增量模式与"raw = journal / pages = projection"的 Karpathy 模型一致
3. 引入向量库是 infra 重决策，应单独 spec

##### FR-0140.7 token 估算（实现）

`cmd_compact` 估算 `total_tokens` 用简单启发式：
```python
def estimate_tokens(raw_entries: list[Path]) -> int:
    total_chars = sum(p.stat().st_size for p in raw_entries)
    return total_chars // 4   # ~4 chars / token 经验值
```

`--threshold-tokens` flag 让用户覆盖默认 50K / 200K 阈值（高级用户调优）。

---

### D. Agent 文档对齐

#### FR-0120 Librarian Identity 框架对齐

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

`louke/agents/Librarian.md` §1 + §2 改英文，框架对齐 Devon.md：

**§1 Identity & Runtime Context** — 英文：说明 subagent 模式 + 非交互 + raw assumption 处理

**§2 tools, skills and permissions** — 英文：
- §2.1 tools：`bash` + `read` + `edit` + `grep` + `glob` 允许；`task` + `question` + `webfetch` + `websearch` + `external_directory` + `doom_loop` 拒绝；附 `lk librarian` CLI 表（含 `compact` / `rewrite` / `lint` / `rebuild-index` / `distill`）
- §2.2 skills：`inline-comments` + `reserve-memory`
- §2.3 permissions：明确允许 `edit` 的范围（`pages/*.md` via rewrite + `index.md` + `log.md` + `overview.md` + `.cache.toml`），禁止写入 raw/ + 业务代码 + spec 产物

**P1-6 — `.compact-bundle*.md` 写入权属澄清**：

| 文件 | 写入方 | 触发 |
|---|---|---|
| `pages/*.md` | LLM（via `opencode run --agent librarian` 的 `edit`） | rewrite 后 |
| `index.md` / `log.md` / `overview.md` | LLM `edit` + python CLI（`rebuild-index` / `lint`） | rewrite 后 / 手动 |
| `.cache.toml` | python CLI（`cmd_compact`） | 每次 compact |
| `.compact-bundle*.md` | **python CLI（`cmd_compact`）**，**不**经 LLM `edit` | 每次 compact |

LLM 的 `edit` 权限白名单仅限 `pages/*.md` + `index.md` + `log.md` + `overview.md`（参 v0.6-009 FR-0010.4）。bundle 文件由 python 脚本（cron 进程）写入，**不**受 LLM `edit` 权限约束。但 LLM 也不**应**触碰 bundle（不读不写），bundle 是 rewrite 的输入。

**Librarian 特性化**（与 Devon 区别）：
- `webfetch` / `websearch` / `external_directory`: **deny**（wiki 是本地内容，无外部查询需求）
- `edit` 范围：**限 wiki 命名空间**（其他 agent 是全项目 edit / 业务代码 edit）
- 工作流主线：trigger（cron daily / 手动）→ compact（python）→ rewrite（LLM via `opencode run --agent`）→ lint
- 不写业务代码 / spec 产物

#### FR-0120.1 调用模式识别段（CLI vs TUI）

`louke/agents/Librarian.md` 加 §"调用模式识别"段（与 FR-0130 联动）：

> 你可能被两种方式调起：
> 1. **TUI subagent 模式**：Maestro 调 `task` 启动你（`mode: subagent`）；可调 `question` 工具向用户提问
> 2. **CLI 批处理模式**：`opencode run --agent librarian -- "..."` 启动你（`mode: primary` 新 session，无 UI）；你**不**应调 `question`（无 UI 会卡住，且 `permission.question: deny` 阻止）
>
> **检测方式**：看你是否在 OpenCode TUI 内（subagent 模式）还是 stdout（CLI 模式）。CLI 模式下按 FR-0080 prompt 完成整体重写；完成后正常 exit。
>
> **frontmatter 不变**：`permission.question: deny` 在两种模式下都安全（CLI 无 UI / TUI 子会话弹框冒泡不依赖此 permission）。

---

### E. cron 安装与目标命令

#### FR-0150 `lk init --install-cron` 目标改为 `lk librarian compact`

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

**问题**：本 spec §0.2 FR-0090 引用"cron 入口（在 v0.7-001 安装）"，但 v0.7-001 范围是 pre-commit 接管，**不含** cron 安装。`louke/init.py:_install_cron()` 是本会话初版独立添加的，未纳入任何 spec。这导致 cron target 指向即将删除的 `lk librarian daily` 命令。

**方案**（v0.7-002 实施）：

- `louke/init.py:_install_cron()` 的 cron entry 从 `lk librarian daily` 改为 `lk librarian compact`（已在 `louke/init.py:167` 同步）
- v0.7-001 的 `lk scout install-precommit` 不再负责 cron 安装（cron 安装归 v0.7-002）
- v0.7-002 的 cron 安装由 `lk init`（默认开 `--install-cron`）或 `lk init --no-cron`（显式跳过）控制

**职责边界**（与 v0.7-001 / 后续 spec）：

| 任务 | spec 归属 |
|---|---|
| pre-commit 框架接管 lint/format/typecheck/test | v0.7-001 |
| cron 触发 `lk librarian compact` | **v0.7-002（本 FR-0150）** |
| pre-commit hook 的 `rev` 升级（`lk upgrade --precommit`） | v0.7+ 待定 |

---

## 4. 非功能需求

### NFR-0010 向后兼容（含 breaking change 显式声明）

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

⚠️ **Breaking changes**：

1. **既有 `lk librarian from-raw` 调用者**：命令删除；改用 `lk librarian compact` + `lk librarian rewrite`
2. **既有 `lk librarian distill` 调用者**：保留，但语义改为"列出待 compact 的 raw"（wrapper 调 `cmd_compact --dry-run`）
3. **既有 `lk librarian daily` 调用者（本会话初版）**：命令删除；改用 `lk librarian compact`（cron 友好），`lk librarian rewrite` 显式触发

**非 breaking**：
- `lk librarian lint` / `lk librarian rebuild-index` 命令不变（FR-0110 是扩展）
- raw/ 不动（仅追加 `.gitignore` 排除）
- Librarian frontmatter `permission.question: deny` 不变（CLI 模式兼容）
- cron 入口从 `lk librarian daily` 改为 `lk librarian compact`（由 FR-0150 实施的 `--install-cron` 流程里调）

### NFR-0020 Python 3.9 兼容

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- `bool \| None` (PEP 604) 不使用
- 现有 `tuple` 无参数化已符合 py3.9
- 无强制新增依赖（不引入 tomli_w）

### NFR-0030 文档语言

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

README / README.zh 双语同步；agent prompt 中英混排（§1 / §2 英文，§3+ 中文）。

### NFR-0040 可降级

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- `cmd_compact` 找不到 raw → 返回 `{}`，无错误
- `cmd_rewrite` 找不到 bundle → stderr 报错 "请先跑 compact"，exit 1
- `opencode run --agent librarian` 失败 → exit code 透传，cron 日志可查
- M2 Map-Reduce 中单次 map 失败 → stderr 报错 + 退出非 0（不静默继续）

### NFR-0050 可审计

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- cron 日志追加到 `.louke/wiki/.cron.log`，可追溯每日 compact 结果
- `lk librarian compact --dry-run` 支持预览，便于人工审视
- `.compact-bundle.md` 是 raw + pages 的完整 snapshot，可作审计依据
- `lk librarian lint` 在 rewrite 后自动跑，失败立即可见

---

## 5. 澄清记录（review 后决定）

| Q | 议题 | Reviewer 建议 | Kilo 决定 |
|---|---|---|---|
| **Q1** (raw 累积超出上下文窗口) | 1 年后 raw 累计 400K-1M tokens，超出所有模型窗口 | **分层策略**：增量默认 (M0) / 全量大模型 (M1) / Map-Reduce (M2) / 层级摘要 (M3, 罕见, v0.7.1+)；不引入向量库依赖 | 接受，FR-0140 |
| **Q2** (Karpathy 增量 vs 全量) | 每次 cron 跑全量重写还是只增量 | **增量优先**：cron 默认 `[last_distill, 昨天]` 区间，正常情况 ≤ 50K tokens 单次喂入；全量用 `--full` flag 显式触发 | 接受，FR-0140.5 |
| **Q3** (LLM 调度机制) | cron 跑 rewrite 时如何调 LLM？python 调 API / TUI task / OpenCode CLI | **`opencode run --agent librarian`**（CLI 模式，唯一非交互路径） | 接受，FR-0130；v0.6-009 FR-0070.7 已定义 `opencode run --agent` 与 TUI `task` 的边界 |
| **Q4** (CLI 模式与现有 permission 兼容) | `permission.question: deny`（v0.6-009）是否适合 CLI 批处理 | **正好适合**（CLI 无 UI 不应 question）；frontmatter 不变，仅 prompt 区分模式 | 接受，FR-0130 / FR-0120.1 |
| **Q5** (raw 进 git?) | raw 是 journal 性质，不应分享 | 加 `.gitignore` 排除 `.louke/raw/` | 接受，FR-0100 |
| **Q6** (知识蒸馏为何放 v0.7-002 而非 v0.7-001) | v0.7-001 是 pre-commit 接管 gate，与本 spec 无关 | 拆分：v0.7-001 = pre-commit 接管；v0.7-002 = 知识蒸馏 Karpathy 化 | 接受，本 spec 只聚焦 wiki |
| **Q7** (向量库 RAG 何时引入) | raw 累积超 1M tokens 时 | v0.7.1+ 单独 spec；本 spec 默认增量 (M0) 兜底 map-reduce (M2) | 接受，FR-0140.6 |
| **Q8** (cmd_daily 命令去留) | 本会话初版的 `cmd_daily` 是否保留 | **删除**：拆分为 `compact` + `rewrite`；cron 只调 `compact`，`rewrite` 显式触发 | 接受，FR-0080 / FR-0090 |

### QoderWork 评审 (2026-07-05)

| Q | 议题 | Reviewer 建议 | Kilo 决定 |
|---|---|---|---|
| **P0-1** (scenario-0200 日期错) | 2026-07-02 是周四不是周五；窗口上限应为昨天不是今天 | 重写用相对日期 + 确认与 `cmd_compact` 实现一致 | 接受，已用 Day N 相对日期重写（scenario-0200） |
| **P0-2** (cron 入口虚假引用) | v0.7-001 不含 cron，引用是虚假 | 在 v0.7-002 新增 FR-0150 显式归属 cron 安装 | 接受，新增 FR-0150 |
| **P0-3** (M2 旧 bundle 被当 map 输入) | M0→M2 切换时 `.compact-bundle.md` 残留触发重复处理 | FR-0140.2 加清理逻辑 | 接受，FR-0140.2 已加 |
| **P1-4** (bundle 不清理) | 磁盘累积 | 清理逻辑放在 compact 步骤 1 | 接受，FR-0140.2 |
| **P1-5** (decisions/entries/consolidated.md) | 不在重写范围 | §0.4 明确状态：entries/consolidated.md deprecated；decisions 留 v0.7-003 | 接受，新增 §0.4 |
| **P1-6** (edit 白名单漏 bundle) | bundle 是 python 写不是 LLM edit | §2.3 注明 bundle 写入权属 | 接受，§2.3 加澄清段 |
| **P1-7** (model flag 优先级不清) | --model / --model-from-config / frontmatter 三者优先级 | FR-0140.4 明确优先级链 + 实现伪代码 | 接受，FR-0140.4 已加优先级表 |
| **P1-8** (无 date 字段 raw 处理) | 未定义 | 跳过 + warning | 接受，FR-0080 加 P1-8 段 |
| **P2-9** ("不调 LLM API" 措辞) | 改"不调 SDK，shell-out opencode" | 改写 | 接受，FR-0070 第 3 条已改 |
| **P2-10** (缺 quote-dialogue 引用) | 应引 v0.4-004 | 加引用 | 接受，FR-0080 已加 `(详见 v0.4-004-quote-dialogue)` |
| **P2-11** (幂等性松散) | 改写更精确 | 改"再跑若无新 raw，bundle + cache 不变" | 接受，FR-0080 compact 段已改 |
| **P2-12** (frontmatter 是 NEW) | 不是"保留" | 措辞改为"首次实现" | 接受，FR-0110 已改 |
| **P2-13** (rebuild-index 扁平) | 现状与 §4 agent prompt 不一致 | 标注为已有 bug，v0.7-003 处理 | 接受，FR-0110 注明 |
| **P2-14** (FR-0130 硬编码 prompt 矛盾) | 与 FR-0140.3 动态 prompt 矛盾 | 标注 FR-0130 为基线版，FR-0140.3 为扩展版 | 接受，FR-0080 rewrite 段已加标注 |

---

## 6. 关联文件

| 文件 | 改动 |
|---|---|
| `louke/librarian.py` | **删除** `cmd_from_raw` + `cmd_daily`（FR-0080：机械 copy + cron 旧入口被替代）；**新增** `cmd_compact`（拼 bundle + 写 cache + 清理旧 bundle FR-0140.2 + no-date warning FR-0080 P1-8 + M0/M1/M2 模式）；**新增** `cmd_rewrite`（shell-out `opencode run --agent librarian -- <prompt>`，FR-0130 + FR-0140.4 优先级链）；**新增** `--model` / `--model-from-config` / `--full` / `--threshold-tokens` / `--m2-threshold` flag；**保留** `cmd_distill` / `cmd_lint`（FR-0110 扩展：新增 frontmatter + 重复主题检查） / `cmd_rebuild_index`（已知 bug：扁平列表，P2-13） |
| `louke/init.py` | `_install_cron()` cron entry 从 `lk librarian daily` 改为 `lk librarian compact`（FR-0150，**已实施**于本 spec 起草期 init.py:167） |
| `louke/agents/Librarian.md` | §1 Identity 改英文；§2 tools / skills / permissions 改英文 + bundle 写入权属澄清（P1-6）；新增 `lk librarian` CLI 表（含 `compact` / `rewrite` / `distill` / `lint` / `rebuild-index`）；§5 改写（cron 触发 + compact/rewrite 子命令 + 窗口 [last_distill, 昨天] + M0/M1/M2 模式 + P1-8 no-date 处理）；明确 pages/ 写入权限；新增 §"调用模式识别"段（CLI vs TUI，FR-0120.1）；新增 §"上下文窗口策略"段（FR-0140） |
| `.gitignore` | 加 `.louke/raw/`（raw 是 journal，不分享）；加 `.louke/wiki/.compact-bundle*.md`（bundle 是临时中间产物，不持久化） |
| `.louke/wiki/entries/` | **DEPRECATED**（§0.4 P1-5）：Agent 不再写 entries；现有 7 个文件保留至 v0.7-003 决定迁移/删除 |
| `.louke/wiki/consolidated.md` | **DEPRECATED**（§0.4 P1-5）：同上处理 |
| `tests/test_librarian_compact.bats` | **新建**：FR-0080/0090/0140/0150 单元测试（compact 拼 bundle、写 cache、跳日 catch-up、token 估算触发分块、bundle 清理、no-date warning） |
| `tests/test_librarian_rewrite.bats` | **新建**：FR-0130/0140.4 单元测试（`opencode run --agent` shell-out 退出码透传、M0/M1/M2 模式选择、模型优先级链） |
| `README.md` / `README.zh.md` | 加"知识蒸馏（Karpathy 模型）"小节（FR-0070 三原则 + cron 流程图） |

---

## 附录 A: 与 v0.7-001 的边界

| 主题 | v0.7-001 (pre-commit) | v0.7-002 (本 spec) |
|---|---|---|
| 跨语言 lint/format/typecheck/test | **pre-commit 框架接管**（hook + `.pre-commit-config.yaml`） | 不涉及 |
| `lk keeper gate` 加载 quality-gates.toml | 不涉及（本 spec 已否决该方向） | 不涉及 |
| `lk init --install-cron` | **在 v0.7-002 FR-0150 实施**（cron 框架），cron TARGET 是 `lk librarian compact` | 引用其产出；不在 v0.7-001 重复实现 |
| `lk librarian compact` / `rewrite` | 不涉及 | **本 spec 实施** |
| 知识蒸馏 Karpathy 模型 | 不涉及 | **本 spec 实施**（FR-0070） |
| LLM 调度机制（`opencode run --agent`） | 不涉及 | **本 spec 实施**（FR-0130） |
| 上下文窗口应对（FR-0140 分层） | 不涉及 | **本 spec 实施** |
| 文档对齐（FR-0120 Librarian Identity） | 不涉及 | **本 spec 实施** |