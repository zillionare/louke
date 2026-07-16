# v0.7-003 — Inline Discussion 协议 — Spec

- **Spec ID**: v0.7-003-inline-discussion-protocol
- **创建日期**: 2026-07-07
- **状态**: 草稿（待 QoderWork 二次 review）
- **作者**: Kilo
- **关联**:
  - **替代** v0.6-016-quote-dialogue-protocol（作废）
  - **依赖** v0.4-004-quote-dialogue（quote_parser.py 基础）
  - **参考** QoderWork 评审 `review-2026-07-07.md`（10 个 P0/P1/P2 项已采纳）

---

## 0. 范围与边界

### 0.1 本 spec 收纳

| 主题 | FR |
|---|---|
| skill 语法勘误 + 协议重命名为 `inline-discussion` | FR-0010 |
| **`_tools/discuss.py` 新建**（Layer 3：parser + 定位 + 写）| FR-0020 |
| **`lk discuss` CLI 新建**（Layer 2：5 子命令）| FR-0030 |
| agent 专属命令迁移（Layer 1：sage / lex / prisme 等）| FR-0040 |
| 5 元组定位 + Levenshtein 4 级降级查找 | FR-0050 |
| `is_ready` / `check-ready` 门禁迁移 | FR-0060 |
| v0.6-016 spec 作废标记 + cookbook 迁移 | FR-0070 |
| tests 迁移 | FR-0080 |

### 0.2 本 spec **不**收纳

- v0.6-016 协议全文（作废）
- `inline-comments` skill（被 `inline-discussion` 替代）
- comment / admonition 类别（移除）
- 旧 5 元状态（`[open]` / `✓` / `[blocked-by-N]` / `[wontfix]` / `[superseded]`）简化为 3 元

**规范优先级澄清（2026-07-16）**：v0.7-003 是 inline-discussion 语法的唯一规范根。v0.4-004 仅作为旧 parser 的流程、unit 和定位基础依赖；其“无冒号 bold speaker”不属于 inline-discussion，但 plain ASCII speaker 以受限兼容形式保留。v0.7 接受 `**Name:**` / `**Name**:` 两种 bold 冒号布局，以及 `Name:` 形式的无粗体 ASCII identifier（排除 `Note:` 等说明标签）。v0.6-016 已整体作废。v0.8/v0.9 只定义渲染交互，v0.12 FR-1901 只定义 canonical round-trip 与 gate，v0.13 只定义 marker 随 Markdown 全文持久化；它们均引用本协议而不重新定义语法。

### 0.3 三层架构（QoderWork P0-4）

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: agent 专属命令 (内部调用 Layer 3)                  │
│   lk sage quote-check / lk sage record-lock / lk lex ...    │
└────────────────┬────────────────────────────────────────────┘
                 │ Python import
┌────────────────▼────────────────────────────────────────────┐
│ Layer 2: lk discuss 共享 CLI (内部调用 Layer 3)              │
│   query / start / reply / edit / set-status                  │
└────────────────┬────────────────────────────────────────────┘
                 │ Python import
┌────────────────▼────────────────────────────────────────────┐
│ Layer 3: louke/_tools/discuss.py 底层工具                    │
│   parser / 5 元组定位 / Levenshtein 4 级降级 / 写操作          │
└─────────────────────────────────────────────────────────────┘
```

**实施**：新建 `louke/_tools/discuss.py` 包含完整 parser/定位/写。`louke/__main__.py` 注册 `lk discuss` 子命令。`lk <agent> <cmd>` 内部调 `discuss.py` API。

---

## 1. 用户故事

> 完整 story 在 `louke/agents/_skills/inline-discussion/SKILL.md`。本 spec 直接以 skill 为规范，**不**重复。

**核心 5 条**：

1. **写**：canonical 写法用 `> **Speaker:**` 嵌套 blockquote 表示对话；读取兼容历史 `> **Speaker**:` 写法
2. **状态**：仅根评论行 `[STATUS]` 标记有效；嵌套回复方括号作普通文本
3. **RESOLVED 权限**：**仅发起人**（即根评论 speaker）能标 `[RESOLVED]`；其他人标无效
4. **REOPEN**：任何人都可设 REOPEN
5. **找会话断点**：agent 调 `lk discuss query --blocker <我的名字>` 看 3 类别（`unanswered` / `unresolved` / `awaiting_my_reply`）

---

## 2. 功能需求

### FR-0010 (核心) inline-discussion skill 验证 + 8 处勘误

**位置**：`louke/agents/_skills/inline-discussion/SKILL.md`

**已修 8 处**（QoderWork 列出 7 项 + 1 项 S6 thread_id 设计缺陷）：

| # | 行号 | 修正 |
|---|---|---|
| S1 | L3 | `description` 重写为 "Defines inline-discussion format for structured discussion in spec files. Use when agents need to leave traceable multi-round comments and query discussion status via lk discuss." |
| S2 | L104 | "输入为一个 `json`" → "输出为一个 JSON 数组" |
| S3 | L92 | "@方法" → "@mention" |
| S4 | L94 | "## 如何使用 inline-discussion skill?" → "## 6. 如何使用 inline-discussion"（编号修复） |
| S5 | L60 | `> [!attention]` 改为 `> **注意:**`（避免自相矛盾使用 admonition）|
| S6 | L112 | thread_id 设计缺陷（见 FR-0050 重写）|
| S7 | L135 | `--anchor` 标志未定义（见 FR-0050 新增 `lk discuss anchor`）|
| S8 | L113-121 | 4 元组 + SHA256 → 5 元组 + Levenshtein（见 FR-0050 完整设计） |

**AC**:
- AC-1: 8 处修正**逐条列出行号 + 内容摘要**（不依赖 "active file diff"）
- AC-2: `pyproject.toml [tool.setuptools.package-data]` 含 `agents/_skills/inline-discussion/SKILL.md`
- AC-3: skill **不**再出现 `python -m ...` 例子
- AC-4: skill 中 thread_id 描述与 FR-0050 一致（**不**含"SHA256 4 元组"）

### FR-0020 (Layer 3) `louke/_tools/discuss.py` 新建（parser + 定位 + 写）

**位置**：`louke/_tools/discuss.py`（**不**是 `louke/discuss.py`——QoderWork P0-4）

**模块导出 API**：

```python
@dataclass
class Thread:
    thread_id: str                         # "T-001" 自增序号
    initiator: str                         # 根评论 speaker
    status: str                           # "open" | "resolved" | "reopen"
    last_speaker: str                     # thread 最后说话的人
    reply_count: int
    snippet: str                          # 根评论 body 前 80 字
    # 5 元组定位字段（QoderWork P0-2）
    total_lines: int                      # 创建时文件总行数
    anchor_line: int                      # 被评论内容行号
    anchor_text: str                      # 归一化文本
    root_line: int                        # 根评论 `>` 行号
    root_text: str                        # 根评论归一化文本

class DiscussParser:
    def parse_file(path: Path) -> ParseResult
    def get_thread(self, thread_id: str) -> Thread
    def find_thread(self, anchor_line, anchor_text, root_line, root_text) -> Thread  # 4 级降级查找
    def add_thread(self, anchor_line, anchor_text, initiator, body, status="open") -> Thread
    def add_reply(self, thread_id, body, speaker) -> None
    def edit_comment(self, thread_id, depth, speaker, new_body) -> None
    def set_status(self, thread_id, new_status, operator_speaker) -> None
    def is_ready(self) -> tuple[bool, list[str]]  # 与 quote_parser 同接口
```

**5 元组定位字段**（QoderWork P0-2）：

| 字段 | 类型 | 含义 |
|---|---|---|
| `total_lines` | int | 创建时文件总行数（行号漂移修正用）|
| `anchor_line` | int | 被评论内容行号（快速跳转 hint）|
| `anchor_text` | str | 被评论内容（归一化）|
| `root_line` | int | 根评论 `>` 行号 |
| `root_text` | str | 根评论 speaker + body（归一化）|

**thread_id 格式**：`T-NNN`（per file 自增序号，**不**含位置/内容 hash）。parser 维护 `T-{max+1}` 计数器。

**归一化规则**：strip 首尾空白 + 合并连续空白为单空格 + Unicode NFC。**不改大小写，不去 markdown 格式**。

**speaker 大小写**：比较时 lowercase 归一化，显示保留原大小写。

**@mention 语法**（QoderWork P1-NEW-3 保留）：speaker tag 支持 `**@Speaker:**` 前缀表示"@提及某 agent"，与 `**Speaker:**` 等价。parser 在解析 thread 时收集 `mentioned_agents` 列表，`--blocker` filter 包含被 mention 的 agent（即使不是 last_speaker）。

**人类输入兼容合同（2026-07-16 固定）**：

- `lk discuss` 的 canonical 输出为 `> **Speaker:** body`；根状态写作 `> **Speaker [RESOLVED]:** body` / `> **Speaker [REOPEN]:** body`（冒号位于粗体内）。
- parser 同时接受历史/人工常见写法 `> **Speaker**: body` 与 `> **Speaker** [RESOLVED]: body`（冒号位于粗体外）；两种写法必须得到相同的 speaker、status、body、depth、thread 和 readiness 结果。
- parser 也接受无粗体的人类写法 `> Speaker: body` 与 `> Speaker [RESOLVED]: body`。其中 Speaker 必须是以 ASCII 字母开头的 ASCII identifier（`A-Za-z0-9_-`）；无粗体形式不支持空格或非 ASCII 名称。
- 无冒号 bold speaker 不在兼容集合中。`Note:`、`Warning:`、`Tip:`、`Important:`、`Definition:`、`Example:`、`Remark:`、`Attention:`、`Caution:` 等常见说明标签保持普通 blockquote，不成为 discussion；若它们确为人名，必须用 canonical bold 写法。
- 识别按行进行并跳过 fenced code block，不要求 discussion 紧邻标题、FR 或文件边界。discussion 前后的普通 Markdown 不得抑制识别；根评论以其上方最近的非空、非 blockquote 行作为 anchor。因此“普通说明文字 + 空行 + `> **Aaron:** ...` + 普通说明文字”必须发现一个 inline-discussion。
- 上述兼容只放宽 separator/status marker 的既有两种布局以及周围上下文，不把缺少 speaker tag 的普通 blockquote、HTML comment 或 admonition 当作 discussion；因此不与 v0.12-001 FR-1901 的“不可 round-trip 输入必须拒绝”冲突。

**AC**:
- AC-1: `louke/_tools/discuss.py` 存在，导出 `Thread` / `DiscussParser` 类
- AC-2: `parse_file()` 解析 `[open]` / `[RESOLVED]` / `[REOPEN]` 三态；嵌套回复的方括号作普通文本（不识别）
- AC-3: `set_status()` 验证 RESOLVED 时 `operator_speaker == thread.initiator`，否则拒绝；REOPEN 不限
- AC-4: `is_ready()` 接口与 quote_parser 兼容（`ParseResult` 含 `is_ready: bool` + `ready_blockers: list[str]`）
- AC-5: thread_id 格式 `T-NNN`，per file 自增
- AC-6: 不解析 `<!-- -->` / `[!NOTE]` / `[!WARNING]` 等（comment + admonition 已移除）
- AC-7: 5 元组定位字段完整（`total_lines` / `anchor_line` / `anchor_text` / `root_line` / `root_text`）
- AC-8: **@mention 语法保留**（QoderWork P1-NEW-3）：parser 识别 `**@Speaker:**` 前缀；SKILL.md §2.2 示例 `> **Sage:** @Lex, ...` 有效
- AC-9: parser 对 `**Speaker:**` / `**Speaker**:` / `Speaker:` 及其根状态 marker 的三种布局解析等价；所有写操作只输出 `**Speaker [STATUS]:**` canonical 形式
- AC-10: inline-discussion 前后存在普通 Markdown 时仍被发现，`anchor_text` 是根评论上方最近的非空、非 blockquote 行；fenced code 中的同形文本仍不解析

### FR-0030 (Layer 2) `lk discuss` CLI 新建（5 子命令）

**位置**：`louke/__main__.py` 注册 `discuss` 顶级子命令（**不**用单独的 `louke/discuss.py` 间接层 —— QoderWork P2-1，直接在 `__main__.py` import + 注册）

**5 子命令**（QoderWork P0-4）：

```bash
# 1. query — 列出 thread（含 5 元组定位字段）
# 注: P1-NEW-2 决定**不**新增 anchor 子命令, 因为 start 命令直接接受 anchor-line 行号
# `--blocker` 含义 (QoderWork P2-2 明确): 3 个类别；OPEN 和 REOPEN 都纳入
#   - unanswered: 我 (--blocker 给的 agent) 起的对话, 无回复
#   - unresolved: 我起的对话, 最后一层回复未置 resolved
#   - awaiting_my_reply: @提及我的 thread, 最后一层既不是我也不是 resolved
lk discuss query --file <path> [--initiator <agent>] [--blocker <agent>] [--status <s>] [--check-ready]

# 2. start — 创建新 thread（插在 anchor 段落后的空行之后）
lk discuss start --file <path> --anchor-line <N> --speaker <agent> <message>

# 3. reply — 追加回复到 thread 末尾
# 5 元组定位字段 (anchor-line/anchor-text/root-line/root-text) 用于在行号漂移后定位 thread
lk discuss reply --file <path> --thread-id <id> \
    --anchor-line <N> --anchor-text <t> --root-line <N> --root-text <t> \
    --speaker <agent> <message>

# 4. edit — 修改自己某条评论（仅原作者; 多行内容保持 > 缩进）
lk discuss edit --file <path> --thread-id <id> \
    --anchor-line <N> --anchor-text <t> --root-line <N> --root-text <t> \
    --depth <N> --speaker <agent> <new_body>

# 5. set-status — 修改 thread 状态（RESOLVED 仅 initiator; REOPEN 任意人）
lk discuss set-status --file <path> --thread-id <id> \
    --anchor-line <N> --anchor-text <t> --root-line <N> --root-text <t> \
    --status <resolved|reopen> --operator <agent>
```

**4 级降级查找**（QoderWork P0-2，在 start/reply/edit/set-status 命令里共用）：

```
Step 0: 计算行号偏移
  current_total = len(file.readlines())
  delta = current_total - thread.total_lines
  adjusted_anchor = thread.anchor_line + delta
  adjusted_root = thread.root_line + delta

Level 0 — 精确命中：
  normalized(adjusted_anchor_line) == thread.anchor_text ?
  AND normalized(adjusted_root_line) 含 speaker-tag 且 root_text 匹配 ?
  → 命中 ✓

Level 1 — Levenshtein 窗口搜索（行号漂移 + 内容微改）：
  搜索范围 = adjusted_anchor ± max(|delta| + 5, 10) 行
  对范围内每行计算 edit_distance(normalize(line), anchor_text)
  找到距离最小候选 → 在其下方扫 blockquote 块
  对块内根评论计算 edit_distance(normalize(root), root_text)
  → anchor 距离 ≤ max(5, len(text) * 0.2) AND root 距离 ≤ 阈值 → 命中 ✓

Level 2 — 仅根评论定位（锚点被大幅修改）：
  全文扫根评论（depth=1 `>` 行）
  对每个根评论计算 edit_distance(normalize(root), root_text)
  → 距离最小且 speaker 匹配 → 命中 ✓（更新 anchor）

Level 3 — 未找到：
  返回 "thread not found" + 建议操作（重新 query）
```

**写操作语义**（QoderWork P0-4）：

| 场景 | 规则 |
|---|---|
| `start` 插入位置 | anchor 段落后的第一个空行之后；同 anchor 下多 thread 按时间顺序 |
| `reply` 插入位置 | thread 最后一行之后，与下一个 `>` block 之间空一行 |
| `edit` 内容替换 | 定位 depth+speaker 的评论；多行内容保持 `>` 前缀和缩进一致 |
| `set-status` 权限 | RESOLVED 仅 initiator；REOPEN 任意人 |
| 并发安全 | 用 `flock` 写 tmp 文件 → rename 覆盖；parse 失败回滚 |
| 空行分隔 | 写操作自动插空行（blockquote 间必须有空行 CommonMark 解析要求）|

**AC**:
- AC-1: 5 个子命令都注册并可调用
- AC-2: `query` 输出 JSON 含 thread 列表（每 thread 含 5 元组定位字段）
- AC-3: `start` 插在 anchor 段落后的空行之后
- AC-4: `reply` 追加到 thread 末尾（与下一个 `>` 间有空行）
- AC-5: `edit` 仅原作者可改；多行内容保持 `>` 缩进
- AC-6: `set-status` 验证 RESOLVED 权限（仅 initiator）
- AC-7: 4 级降级查找都实现
- AC-8: 并发安全用 `flock`；write 失败回滚

### FR-0040 (Layer 1) agent 专属命令迁移

**12 agent 全部**（QoderWork P1-1：spec 之前只列 5 个是错的，应全部迁移）：

| Agent | 旧 | 新 |
|---|---|---|
| **Sage** | `quote_parser` 引用 + quote-check | `lk sage quote-check`（内部调 `_tools/discuss.is_ready()`）|
| **Lex** | `quote_dialogue` 形式 | `lk discuss query` for review |
| **Prism** | M-ARCH 评审 `inline-comments` | M-ARCH 评审 `inline-discussion` |
| **Archer** | L43 + L246 `inline-comments` 引用 | 引用 `inline-discussion` skill |
| **Librarian** | L28 `quote_dialogue` 引用 | 引用 `inline-discussion` skill |
| **Scout** | （在 `.opencode/agents/` 中引用 quote）| 引用 `inline-discussion` skill |
| **Devon** | （在 `.opencode/agents/` 中引用 quote）| 引用 `inline-discussion` skill |
| **Maestro** | L113, L153, L160 quote 引用 | `lk discuss` louke + `lk sage record-lock` |
| **Keeper** | （间接依赖）| `lk discuss` louke |
| **Shield** | （e2e 报告引 spec）| `lk discuss` |
| **Judge** | （审计报告引 spec）| `lk discuss` |
| **Warden** | （spec/acceptance 留 quote）| `lk discuss` |

**AC**:
- AC-1: 12 agent prompt **不**再含 `quote_parser` / `quote_dialogue` / `quote dialogue` 字符串
- AC-2: 12 agent prompt **引用** `inline-discussion` skill（`agents/_skills/inline-discussion/SKILL.md`）
- AC-3: agent prompt 中 `lk discuss` 命令示例**不**用 `python` 写法

### FR-0050 (核心) 5 元组定位 + Levenshtein 4 级降级查找

**已在 FR-0020 + FR-0030 中实现**，本 FR 是**契约说明**（不重复实现细节）：

- thread_id = `T-NNN` 自增序号（**不**含 SHA256 4 元组）
- 定位 = 5 元组（`total_lines` / `anchor_line` / `anchor_text` / `root_line` / `root_text`）
- 4 级降级查找：精确命中 → Levenshtein 窗口 → 全文根评论 → 未找到
- 边界处理：行号漂移用 `delta = current_total - total_lines` 修正

**AC**: 同 FR-0020 AC-5 + FR-0030 AC-7。

### FR-0060 `is_ready` / `check-ready` 门禁迁移

**问题**（QoderWork P0-3）：Maestro `record-lock` 依赖 `quote-check exit 0` 做门禁。新协议下需要等效。

**等效命令**：
- `lk discuss query --file <path> --check-ready` — 输出 `is_ready: bool` + `ready_blockers: list[str]`
- 或 `lk sage record-lock` 内部调 `discuss.is_ready()`

**ready 判定**（与 quote_parser 兼容）：
- 单元 `yaml_resolved == "✅"`（**保留**——YAML 是 SKILL 不禁止的元数据）
- 单元下**所有 thread 状态 == "resolved"**（即 reopen / open 都算阻塞 —— QoderWork P0-NEW 修正）
- 单元 `is_explanatory` 不算 thread

**AC**:
- AC-1: `_tools/discuss.py` 导出 `is_ready()` 接口（与 quote_parser 兼容）
- AC-2: `lk discuss query --check-ready` CLI 命令输出 `is_ready: bool` + `ready_blockers: list[str]`
- AC-3: `lk sage record-lock` 内部调 `discuss.is_ready()`（**不**调 quote_parser）
- AC-4: `lk keeper gate` M-SPEC 阶段也用 `lk discuss query --check-ready` 替代 quote-check

### FR-0070 v0.6-016 spec 作废 + cookbook 迁移

**v0.6-016 spec 作废**（QoderWork E 节）：
- 在 `.louke/project/specs/v0.6-016-quote-dialogue-protocol/spec.md` 头部加 `valid: false`（YAML 头部）+ supersede 注释指向 v0.7-003
- `_protocols/quote-dialogue.md` 删除（QoderWork P1-3）；改用 `_skills/inline-discussion/SKILL.md` 作单一信息源
- `pyproject.toml` 的 `package-data` 含 `agents/_skills/*/*.md`

**cookbook 迁移**（QoderWork P1-4）：
- `docs/cookbook.md` 加 "Inline Discussion" 段
- 自包含（不引用 `../` 或 `agents/` 路径）
- 覆盖：3-5 个真实 example + 语法 + 易错点清单

**AC**:
- AC-1: v0.6-016 spec 含 `valid: false`
- AC-2: `_protocols/quote-dialogue.md` 文件**不存在**
- AC-3: `pyproject.toml package-data` 含 `agents/_skills/*/*.md`
- AC-4: `docs/cookbook.md` 含 "Inline Discussion" 段（≥ 3 example）

### FR-0080 tests 迁移

**新增** `tests/test_inline_discussion.bats`：
- `lk discuss start` 跑后 spec.md 含根评论
- `lk discuss reply` 跑后 spec.md 含回复
- `lk discuss query` 返回正确 JSON（含 5 元组）
- `lk discuss query --blocker` / `--initiator` 过滤正确
- `lk discuss edit` 仅原作者可改
- `lk discuss set-status` RESOLVED 仅 initiator
- 4 级降级查找（行号漂移 / Levenshtein）测试
- 写操作并发安全（flock）
- 人类输入兼容：冒号/根状态 marker 位于粗体内外两种布局解析等价，且 discussion 前后可有普通 Markdown

**AC**:
- AC-1: **≥ 8 个 test cases 全部通过**（QoderWork P2-3: 4 级降级查找可拆为 4 子测试）
- AC-2: **不**修改其他 test 文件（仅修改 fixture 数据允许）
- AC-3: 新建 `tests/test_inline_discussion.bats`

---

## 3. 退出条件

- [ ] FR-0010: skill 8 处勘误完成（AC-1 逐行列出）
- [ ] FR-0020: `louke/_tools/discuss.py` 新建，API 完整
- [ ] FR-0030: `lk discuss` 5 子命令可调用（query / start / reply / edit / set-status）
- [ ] FR-0040: 12 agent prompt 迁移（**全部**）
- [ ] FR-0050: 5 元组定位 + Levenshtein 4 级降级查找实现
- [ ] FR-0060: `is_ready` 门禁迁移（`lk sage record-lock` 内部调 `discuss.is_ready()`）
- [ ] FR-0070: v0.6-016 spec 作废 + cookbook 迁移 + `_protocols/quote-dialogue.md` 删除
- [ ] FR-0080: `tests/test_inline_discussion.bats` 8 个 test cases 通过

---

## 4. 状态

- 2026-07-07 Kilo 重写本 spec（QoderWork 首次 review 后采纳 P0-1/P0-2/P0-3/P0-4/P1-1 等核心修正）
- 等等二次 review
