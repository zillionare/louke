# v0.6-009 — Agent 权限收紧 + 分层编排 + 交互式子代理 — Spec

- **Spec ID**: v0.6-009-agent-permission-tightening
- **创建日期**: 2026-07-03
- **修订**:
  - 2026-07-03 12:45 Qwen 一轮 review 后重大修订（字段名 `permissions` → `permission`、格式改 YAML 对象、移除 `interactive: true`、改用 `permission.question`、改 lint 归属为 `lk agent lint`、Maestro 改 `mode: primary`、spec 拆分 v0.3.0/v0.3.1）
  - 2026-07-03 13:35 Qwen 二轮 review（`external_directory` / `doom_loop` 显式 deny + FR-0070 方案 b + `MIN_OPENCODE_VERSION = "1.1.1"`）
  - **2026-07-03 14:00 IDE 实测通过 + spec 完全锁定**：A-001-4 (subagent `question` 冒泡) 实证确认，FR-0070 从 v0.3.1 合并入 v0.3.0（移除 v0.3.0/v0.3.1 拆分，整 spec 一次性 v0.3.0 发版）
- **状态**: 草稿（Qwen 三轮 review 已完结；待 Aaron 最终拍板）
- **关联**:
  - 既有 spec：v0.6-008 FR-0220（source frontmatter 与档位表一致）、v0.6-008 FR-0300（默认 agent = maestro）
  - 关联 issue：#80（models doctor 三层验证，本 spec 的副产品是 frontmatter 收紧）
  - Aaron 2026-07-03 调研：OpenCode 主代理-子代理分层编排模式
  - Qwen 2026-07-03 12:15 / 13:05 / 14:30 review：3 个🚨关键发现 + spec 拆分建议 + 二轮 3 行动项 + 三轮 3 处文档内部不一致
  - **Aaron 2026-07-03 14:00 IDE 实测**：subagent `question` 弹框冒泡到主窗口已确认（截图证据见 `.louke/qwen-review-v0.6-009.md` §10 Kilo 二轮回应）

## 0. 范围与边界

### 0.1 本 spec 收纳（v0.3.0 一次性发版）

| 主题 | FR 范围 |
|---|---|
| 权限收紧 (5 个 agent `permission:` frontmatter: 4 角色 + Maestro) | FR-0010 ~ FR-0050 |
| 分层编排 (Maestro `mode: primary` + 11 agent `mode: subagent`) | FR-0060 |
| 交互式 subagent (4 个允许 question, 7 个 deny + 1 个 Maestro deny) | **FR-0070** |
| 受影响下游 + supersede 标注 | §0.2 |
| 单一 primary agent 约束 + IDE 实测基线 | NFR-0040 / NFR-0050 |

### 0.2 受影响下游 / supersede

- **v0.6-008 FR-0200**："装完 louke 后 `<Leader>a` agent 列表看到全部 12 个 agent" → **SUPERSEDED by v0.6-009 FR-0060.2**：TUI 顶层 `<Leader>a` 只看到 Maestro；其余 11 个通过 `task` 调用（OpenCode `mode: subagent` 行为：不在 Tab 循环、不在 `<Leader>a` 列表）
- **v0.6-008 FR-0210**：source frontmatter 验证（`models` 字段、4 位编号等）→ 扩展：新增 `mode` 约束（必须为 `subagent` 除 Maestro）/ 新增 `permission` 字段 schema 验证
- **用户已有 `.opencode/agents/`**：`lk board opencode` 重新生成后 agent 可见性会变（12 → 1），属 **breaking change**，NFR-0010 显式声明

### 0.3 本 spec 不收纳

- 7 个非交互式 subagent 的完整 `permission` 块 — 留待 v0.6-010+ 跟进；v0.3.0 仅加 `permission.question: deny` 最小块 (FR-0070.2)
- OpenCode 端按文件路径限制 `edit` 范围（OpenCode 仅 per-tool 控制，无 path 白名单）—— 用 prompt 强约束代替
- 其余 8 个 agent（含 Maestro）的 prompt 内容修订 —— 仅改 frontmatter + 必要段落，业务 prompt 不动
- `lk archer ci-scan` 内部 spec/test 追溯逻辑（与 agent frontmatter 无关）

### 0.4 ~~v0.3.0 / v0.3.1 拆分~~ → 一次性 v0.3.0 发版

**原拆分理由已失效**：
- 拆分仅因 A-001-4 (subagent `question` 冒泡) 未实测
- 2026-07-03 14:00 Aaron IDE 实测**确认** subagent `question` 弹框冒泡到主窗口
- 唯一 blocker 消除，整 spec 合并为一次性 v0.3.0 发版

**v0.3.0（最终发版范围）**：
- FR-0010 ~ FR-0050：权限收紧
- FR-0060：分层编排
- FR-0070：交互式 subagent (4 allow + 7 deny + Maestro deny, FR-0070.3 方案 b 已确保 prompt/config 一致)
- §0.2 / NFR-0010 / NFR-0050：受影响下游 + 单一 primary 约束

**v0.3.0 不再拆分为多个 release**。若 release 后发现问题，走 patch release (v0.3.0.1)。

---

## 1. 用户故事

### US-0100 收紧只读审计
- US-0100: 作为 OpenCode 用户，我希望 Warden / Judge 在 IDE 里跑会话时**只能**读文件、跑命令、搜内容，**不能**改任何业务代码或 `wiki/`，以便审计角色不可能误伤项目
- US-0110: 作为 louke 维护者，我希望 source agent frontmatter 显式声明 `permission: { ... }`（YAML 对象），IDE / OpenCode 据此禁用未列出的工具，便于角色行为可声明、可审计

### US-0200 Archer / Librarian 受限写
- US-0200: 作为 OpenCode 用户，我希望 Archer / Librarian 在 IDE 里跑会话时**只能**写自己职责范围内的文件（Archer → spec 产物，Librarian → wiki），即使 prompt 失守也**不能**改业务代码
- US-0210: 作为 louke 维护者，我希望 OpenCode 板生成（`lk board opencode`）从 source agent 复制 `permission:` 字段到 `.opencode/agents/*.md`，使 IDE 内实际生效

### US-0300 可验证
- US-0300: 作为 CI 维护者，我希望 `lk agent lint` 校验 source agent 的 `permission:` 字段是 YAML 对象 + 工具名 ∈ OpenCode 白名单 + 4 角色必填 `permission`
- US-0310: 作为 louke 维护者，我希望 README + agent prompt 明确"为什么这个角色有这个权限"，让权限决策有据可查

### US-0400 Maestro 全权工作流控制
- US-0400: 作为 OpenCode 用户，我希望**只**在 TUI 顶层 `<Leader>a` 列表能看到 Maestro 这一个主代理，其余 11 个专业角色只能通过 Maestro 的 `task` 调用出现；这样工作流的"控制权"始终在 AI 手里（Maestro 自主推进），人类无需按 `Tab` 切换窗口
- US-0410: 作为 louke 维护者，我希望 Maestro 的 frontmatter 显式声明 `permission:`（含 `task`），IDE 据此允许它调用子代理；Maestro 改 `mode: primary` 防止被 subagent 递归调用
- US-0420: 作为 OpenCode 新用户，我希望 `lk init` 生成的 `opencode.json` 把 `default_agent` 设为 `maestro`，新会话默认进入 Maestro 而非其它 agent

### US-0500 交互式 subagent (v0.3.0)
- US-0500: 作为 OpenCode 用户，我希望 Scout / Sage / Archer / Judge 4 个 subagent 在执行中可以向用户提问（`permission.question: allow`），其余 7 个 subagent 不能提问（`permission.question: deny`）；弹框**冒泡到主会话窗口**（详见 spec FR-0070.6 测试基线）
- US-0510: 作为 louke 维护者，subagent 的"交互能力"由 `permission.question` 控制（OpenCode per-tool 权限），不是 boolean 开关；如未来发现 Lex / Devon 也需要交互，改 frontmatter 即可
- US-0520: 作为 OpenCode 用户，我**不想**手动按 `<Leader>+Down` 进入子会话查看 subagent 弹框（subagent 弹框冒泡到主窗口）

---

## 2. 关键场景

### scenario-0100 Warden 在 IDE 跑审计
```
1. 用户在 OpenCode TUI 用 <Leader>a 切到 Warden
2. Warden 调 `bash` 跑 `lk scout check-foundation` —— ✓ (permission.bash: allow)
3. Warden 调 `read` 读 spec.md —— ✓ (permission.read: allow)
4. Warden 调 `grep` 找 "TODO" —— ✓ (permission.grep: allow)
5. (假设) Warden prompt 失守, 试图 `edit` 改 spec.md —— ✗ OpenCode 拒绝 (permission.edit: deny)
6. (假设) Warden 试图 `task` 创建 subagent —— ✗ OpenCode 拒绝 (permission.task: deny)
```

### scenario-0200 Archer 写 spec 产物
```
1. 用户在 OpenCode TUI 用 <Leader>a 切到 Archer (注: v0.3.0 之后 <Leader>a 列表不含 Archer, 此场景仅说明权限模型)
2. Archer 读 spec/acceptance —— ✓ (permission.read: allow)
3. Archer 写 `.louke/project/specs/v0.6-010-foo/test-plan.md` —— ✓ (permission.edit: allow)
4. (假设) Archer prompt 失守, 试图 `edit` 改 `src/foo.py` —— ✓ (permission.edit: allow) ⚠️
   ↑ 此为已知折衷: OpenCode 无 path 白名单; 靠 prompt 强约束
5. Archer 试图 `task` 创建 Devon subagent —— ✗ OpenCode 拒绝 (permission.task: deny)
```

### scenario-0300 board opencode 透传 permission
```
$ lk board opencode
generated 12 OpenCode agents
$ head .opencode/agents/warden.md
---
description: 审核人 — ...
mode: subagent
model: ark/deepseek-v4-flash
permission:
  bash: allow
  read: allow
  grep: allow
  glob: allow
  edit: deny
  task: deny
  question: deny
  webfetch: deny
  websearch: deny
  external_directory: deny
  doom_loop: deny
---
(注意 permission 是 YAML 对象; 其它源 frontmatter 字段 (如 hidden/color) 走 PASSTHROUGH_KEYS 白名单)
```

### scenario-0400 Maestro 自主推进
```
1. 用户在 OpenCode TUI 新建会话: 默认 agent = maestro
2. TUI 顶层 <Leader>a 列表: 仅 maestro 一个 primary 候选
   (其余 11 个 role: Sage / Lex / ... 不在 <Leader>a 列表里; 它们 mode: subagent)
3. 用户说 "开始 v0.6-009 实施", maestro 收到指令
4. maestro 查 project-info.md 的 Stage 字段, 决定从哪个阶段起
   - 若是新项目 (Stage=F-PENDING) → 调 task 启动 Scout (项目奠基)
   - 若是存量项目 (Stage=M-SPEC 等) → 跳过 Scout, 直接调 task 启动 Sage / Devon / ...
5. maestro 调 `task` 工具启动 Scout 子会话 (mode: subagent, 隔离)
6. Scout 执行 Step 1-3 项目奠基; 如需用户输入, **弹框冒泡到 maestro 主窗口**
7. 用户在主窗口看到问题弹框 (含 1/2/3 选项) → 选项回复
8. Scout 继续 → 完成后焦点自动回到 maestro
9. maestro 决策下一步: 调 task 启动 Sage (spec issues) → ... → Devon (TDD) → Archer (test-plan) → Shield (e2e) → Keeper (gate) → Judge (security) → Librarian (wiki) → Maestro 收尾
10. 全程用户不需要按 <Leader>a 切换主代理; subagent 弹框自然冒泡; 控制权始终在 maestro
11. (可选) 用户想看 subagent 实时进度, 按 `<Leader>+Down` 进入子会话查看; 按 `<Leader>+Up` 返回
12. 整个工作流完成, maestro 输出最终总结
```

### scenario-0500 11 subagent 各自权限
```
- Scout (mode: subagent, permission.question: allow)   — 交互
- Sage (mode: subagent, permission.question: allow)    — 交互
- Lex (mode: subagent, permission.question: deny)     — 静默 + raw 记录
- Devon (mode: subagent, permission.question: deny)    — 静默 + raw 记录
- Archer (mode: subagent, permission.question: allow)  — 交互
- Shield (mode: subagent, permission.question: deny)  — 静默
- Keeper (mode: subagent, permission.question: deny)  — 静默
- Prism (mode: subagent, permission.question: deny)   — 静默
- Warden (mode: subagent, permission.question: deny)  — 静默
- Judge (mode: subagent, permission.question: allow)   — 交互
- Librarian (mode: subagent, permission.question: deny) — 静默
```

---

## 3. 功能需求

### FR-0010 4 角色 permission 表 (YAML 对象格式)

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

OpenCode `permission` frontmatter 是 **YAML 对象**，键是工具名，值是 `allow` / `deny` / glob pattern。**未列出的键不默认 deny** —— 必须显式 `deny` 才禁用（与 A-003-4 一致）。

下表是 4 角色的 `permission:` 完整配置。**只列 allow 的键会失效**（OpenCode 会 merge 到全局默认，可能继承 allow），所以每个角色都列出所有相关键。

#### FR-0010.1 Warden (只读审计)

```yaml
mode: subagent
permission:
  bash: allow
  read: allow
  edit: deny
  grep: allow
  glob: allow
  task: deny
  question: deny
  webfetch: deny
  websearch: deny
  external_directory: deny   # Qwen A-8.2 确认: OpenCode 默认 ask, 显式 deny 避免打断审计
  doom_loop: deny            # Qwen A-8.2 确认: OpenCode 默认 ask, 显式 deny
```

#### FR-0010.2 Judge (只读安全审计)

```yaml
mode: subagent
permission:
  bash: allow
  read: allow
  edit: deny
  grep: allow
  glob: allow
  task: deny
  question: allow      # FR-0070 启用交互
  webfetch: deny
  websearch: deny
  external_directory: deny
  doom_loop: deny
```

#### FR-0010.3 Archer (写 spec 产物)

```yaml
mode: subagent
permission:
  bash: allow
  read: allow
  edit: allow
  grep: allow
  glob: allow
  task: deny
  question: allow      # FR-0070 启用交互
  webfetch: deny
  websearch: deny
  external_directory: deny
  doom_loop: deny
```

#### FR-0010.4 Librarian (写 wiki)

```yaml
mode: subagent
permission:
  bash: allow
  read: allow
  edit: allow
  grep: allow
  glob: allow
  task: deny
  question: deny       # FR-0070 deny
  webfetch: deny
  websearch: deny
  external_directory: deny
  doom_loop: deny
```

#### FR-0010.5 OpenCode permission 键白名单

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

OpenCode `permission` 支持的键（Qwen A-003-3 + A-8.2 确认）：

`read`, `edit`, `glob`, `grep`, `bash`, `task`, `skill`, `lsp`, `question`, `webfetch`, `websearch`, `external_directory`, `doom_loop`

`todowrite` **不在白名单**（OpenCode 内部控制，不通过 permission 配置）。FR-0060.1 中 Maestro 的 `permission` 也必须不含 `todowrite`。

---

### FR-0020 source frontmatter 落地

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

在以下 5 个 source agent prompt 文件的 YAML frontmatter 中加 `permission:` 字段（位于 `models:` 之后）+ 改 `mode:`：

- `agents/Warden.md` — FR-0010.1
- `agents/Judge.md` — FR-0010.2
- `agents/Archer.md` — FR-0010.3
- `agents/Librarian.md` — FR-0010.4
- `agents/Maestro.md` — FR-0060.1（含 `task` 调子代理）

特别说明：
- 其余 7 个 agent (Sage / Lex / Devon / Scout / Shield / Keeper / Prism) 在 FR-0020 中**不加完整 `permission:` 块**；FR-0070 会为其追加最小 `permission:` 块（仅 `question: deny`），其余字段仍走 OpenCode 全局默认
- 7 个 agent **仍**改 `mode: all` → `mode: subagent` (FR-0060.2)
- FR-0070 会给 4 个交互式 subagent 加 `permission.question: allow`

---

### FR-0030 board opencode 透传白名单字段

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

`louke/board.py` 当前 `cmd_opencode()`（`board.py:80`）**只**输出 `description` / `mode` / `model` 三个字段，其它 frontmatter 字段被**静默丢弃**。本 FR 要求：

- 维护**透传白名单** `PASSTHROUGH_KEYS`，白名单内的字段从 source frontmatter 原样复制到生成文件
- `model` 走 `resolve_model()` 重写
- `description` 走 `fm.get('description')` 提取
- `mode` 走 `fm.get('mode')` 透传（FR-0060.2 关键，确保 `mode: subagent` 不被改回 `all`）
- 不在白名单的字段：丢弃；dry-run 时打印 `[!] dropped unknown frontmatter key '<key>' from <agent>`

**白名单初值**（基于 OpenCode 文档列出的字段 + permission）：

```python
PASSTHROUGH_KEYS = {
    'description',  # 但 board.py 已处理
    'mode',         # 但 board.py 已处理（需透传不重写）
    'model',        # 但 board.py 已重写
    'permission',   # FR-0010/0020/0060.1 落地
    'hidden',       # OpenCode 支持
    'color',        # OpenCode 支持
    'temperature',  # OpenCode 支持
    'top_p',        # OpenCode 支持
    'steps',        # OpenCode 支持
    'disable',      # OpenCode 支持
}
```

**安全考虑**（A-008-2 风险）：未列白名单的字段不传，避免调试字段泄露到 LLM provider 作为模型参数。

实现位置：`louke/board.py` `cmd_opencode` 内 frontmatter 构造逻辑（约 lines 70-90）。

---

### FR-0040 `lk agent lint` 校验

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

**新增**子命令 `lk agent lint`，与 `lk archer ci-scan` / `lk librarian lint` 平行（采纳 A-009-2 建议）。职责：

1. **schema 校验**（exit 1 if fail）：
   - 必填 `name`, `description`, `mode`, `models`（至少 1 个元素）
   - 4 角色 (Warden / Judge / Archer / Librarian) 必填 `permission` (YAML 对象)
2. **permission 内容校验**（exit 1 if fail）：
   - `permission` 是 YAML 字典（非字符串 / 非列表）
   - 所有键 ∈ OpenCode 白名单 (FR-0010.5)
   - 值 ∈ {`allow`, `deny`} 或 glob pattern 字符串
3. **mode 单一性约束**（exit 1 if fail，采纳 NFR-0050）：
   - `agents/*.md` 中 `mode: primary` 数量 = 1（白名单 = `maestro`）
   - `mode: all` 数量 = 0（已废弃用法）
   - `mode: subagent` 数量 ≥ 1
4. **board.py 集成**：lint exit 0 → `lk board opencode` 生成的 frontmatter 与 source 一致（不丢字段）

**实现位置**：`louke/agent.py`（新建文件），`lk agent lint` 走 `lk` CLI 已有子命令模式。

**与 `lk archer ci-scan` 的分工**：
- archer ci-scan: spec ↔ test 双向追溯 + test anti-pattern
- agent lint: agent frontmatter schema + permission 验证
- 两者独立, 通过 `lk ci` 统一调度

---

### FR-0050 文档同步

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

- **README.md + README.zh.md**：
  - 在"agent 角色"章节加"Agent 权限矩阵"小表（4 角色 + 7 默认 + Maestro）
  - 加"分层编排 (Layered Orchestration)"小节, 解释:
    - 唯一主代理 = Maestro (mode: primary)
    - 11 个专业角色 = Maestro 的 subagent (mode: subagent)
    - 用户工作流: <Leader>a 切到 Maestro → 启动会话 → Maestro 调 `task` 委派 → 子代理交互在子会话窗口
    - ✅ subagent 的 `question` 弹框出现在 maestro 主会话窗口，用户在主窗口选项回复即可，无需按 `<Leader>+Down` 进入子会话
- **4 个 agent prompt** (Warden / Judge / Archer / Librarian)：在"你不是来"段落之后加一段"## 你的工具"显式说明
- **`agents/Maestro.md`**：加"## 你的编排模式"段落

---

### FR-0060 Maestro 全权工作流控制

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

#### FR-0060.1 Maestro `mode: primary` + `permission:` 显式声明

`agents/Maestro.md` frontmatter 改：

```yaml
mode: primary                    # 改: all → primary, 防止被 subagent 递归调用 (A-010-4 risk 4)
models:
  - minimax-m3
  - glm-5.2
permission:
  bash: allow
  read: allow
  edit: allow
  grep: allow
  glob: allow
  task: allow                    # 调 subagent (核心)
  question: deny                 # Maestro 不向用户提问 (上层协调者, 不需要)
  webfetch: allow                # 查 GitHub issue / 外部参考
  websearch: deny
  skill: deny
  lsp: deny
  external_directory: ask        # Qwen A-8.2 确认: 子代理可能需要访问外部目录, 向用户确认
  doom_loop: deny                 # Qwen A-8.2 确认: Maestro 自身不应陷入 doom loop
```

不含 `todowrite` (A-010-4 risk 2: 不在 OpenCode permission 白名单)。
不含 `question: allow` (Maestro 是协调者, 不亲自提问; 如需用户输入, 通过 subagent `question: allow` 转发)。

#### FR-0060.2 其余 11 个 agent `mode: subagent`

11 个 agent frontmatter `mode: all` → `mode: subagent`：

- `agents/Sage.md`
- `agents/Lex.md`
- `agents/Devon.md`
- `agents/Scout.md`
- `agents/Shield.md`
- `agents/Keeper.md`
- `agents/Prism.md`
- `agents/Archer.md` (FR-0010.3 4 角色之一)
- `agents/Warden.md` (FR-0010.1 4 角色之一)
- `agents/Judge.md` (FR-0010.2 4 角色之一)
- `agents/Librarian.md` (FR-0010.4 4 角色之一)

OpenCode `mode: subagent` 文档语义（Qwen A-001-2 确认）：

- 不在 Tab 循环列表
- 不在 `<Leader>a` agent 列表
- 只能通过 `task` 工具调用或 `@` 提及

#### FR-0060.3 默认 agent

`lk init` 生成的 `opencode.json` (项目级) 与 `~/.config/opencode/opencode.json` (全局) 确保 `"default_agent": "maestro"` (复用 v0.6-008 FR-0300)。

#### FR-0060.4 board.py 透传 `mode:` 字段

`board.py` 当前不重写 `mode` 字段, 但 `cmd_opencode` 构造 frontmatter 时只输出固定模板 (FR-0030 改进). 本 FR 与 FR-0030 联动, 确保 `mode: subagent` 透传 (不被改回 `mode: all`)。

#### FR-0060.5 文档: 分层编排模式

- **README**: "分层编排"小节 (FR-0050 已列)
- **`agents/Maestro.md`** prompt 加"## 你的编排模式"段落:
  > 你是 TUI 顶层唯一的 primary agent (mode: primary)。通过 `task` 工具调 Sage / Lex / Devon / Scout / Archer / Shield / Keeper / Prism / Warden / Judge / Librarian 11 个 subagent。subagent 在隔离的子会话里运行, 需要用户输入时调 `question` 工具弹框到主会话窗口。用户在主窗口选项回复即可，无需按 `<Leader>+Down` 进入子会话；用户若想查看实时进度，仍可手动 `<Leader>+Down` 进入子会话。subagent 完成后焦点自动回到你。**不要**让用户在 `<Leader>a` 切其它主代理。
- **11 个 subagent prompt** 加"## 你的身份"段落:
  > 你是 subagent (mode: subagent), 由 Maestro 调起; 用户不在 TUI 顶层切换到你。你在子会话里运行; 如需向用户提问, 调 `question` 工具 (前提: 你的 `permission.question: allow`)。

---

### FR-0070 交互式 subagent (v0.3.0)

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ (IDE 实测通过) | ✅ |

**背景**：OpenCode **不支持** `interactive: true` 字段 (Qwen A-002-1)，实际机制是 `permission.question: allow/deny`。本 FR 由此重构。

**5 分钟 IDE 实测基线** (详见 `.louke/qwen-review-v0.6-009.md` §10)：
- subagent 调用 `question` 工具时，弹框（含 1/2/3 选项）**冒泡到 maestro 主会话窗口**
- 用户在主窗口选项回复，无需按 `<Leader>+Down` 导航
- subagent 完成后焦点自动回 maestro
- A-001-4 唯一 blocker 消除 → FR-0070 合并入 v0.3.0

#### FR-0070.1 交互式需求识别 (Q6: 选 A, 4 个 allow + 7 个 deny + Maestro deny)

| Agent | permission.question | 理由 |
|---|---|---|
| **Scout** | `allow` | 项目奠基: repo owner / 版本 / spec-id 等必问 |
| **Sage** | `allow` | spec 澄清: 档位 / AC 边界 / 需求冲突 |
| **Archer** | `allow` | test-plan / architecture trade-off 选型 |
| **Judge** | `allow` | severity 校正 / finding 豁免 |
| Lex | `deny` | 保守判定 + raw 记录"待人工确认" |
| Devon | `deny` | fixtures 模板 + 最保守实现 |
| Shield | `deny` | 全自动测试生成 |
| Keeper | `deny` | 质量门禁全自动 |
| Prism | `deny` | code review 全自动 |
| Warden | `deny` | 列出原文 + 推论 + 报告 |
| Librarian | `deny` | 默认分类 + log 标记"待人工确认" |
| **Maestro** | `deny` | 协调者不亲自提问; 通过 subagent `question: allow` 转发 (FR-0060.1) |

#### FR-0070.2 frontmatter 落地 (v0.3.0 实际配置)

4 个交互式 subagent (Scout / Sage / Archer / Judge) 加 `permission.question: allow`；7 个非交互式 subagent + Maestro 加 `permission.question: deny`。完整 `permission:` 表见 acceptance.md AC-FR0070-1。

> ⚠️ 4 角色 (Warden / Judge / Archer / Librarian) 的 `permission` 块已在 FR-0010 定义，本 FR 仅添加 `question` 键；不与 FR-0010 冲突。

#### FR-0070.3 文档化 — 方案 (b) prompt 与 config 同步 (Qwen A-8.3 采纳)

为避免 v0.3.0 期间"prompt 说能交互, config 实际不能"的 UX bug (Qwen 二轮指出的关键问题)，4 个交互式 subagent 的 prompt 写"交互式"行为，与 `permission.question: allow` 配置严格一致：

4 个交互式 subagent 的 v0.3.0 prompt ("## 你的交互能力" 段落)：

> 你是交互式 subagent (`permission.question: allow`)。执行中如需人类决策，调 `question` 工具在主会话窗口弹框（含选项式问题）。弹框冒泡到 maestro 主窗口，用户在主窗口选项回复即可，无需导航到子会话。用户回答后你继续执行；完成后焦点自动回到 Maestro (你的调用者)。

7 个非交互式 subagent 的 v0.3.0 prompt ("## 你的非交互身份" 段落)：

> 你是非交互式 subagent (`permission.question: deny`)。执行中不向用户提问；遇到不确定按合理默认继续，并在 raw session 里记录"假设 + 理由"，由 Maestro 或用户事后 review。

#### FR-0070.4 Maestro prompt 补充 (v0.3.0 明确区分)

`agents/Maestro.md` "## 你的编排模式" 段落显式区分：

> 11 个 subagent 中，Scout / Sage / Archer / Judge 4 个是**交互式**的 (`permission.question: allow`)，他们会在执行中向用户提问；你**不需要**预先收集这些信息，调起时无需带问题清单。其它 7 个 subagent (Lex / Devon / Shield / Keeper / Prism / Warden / Librarian) 是非交互式的 (`permission.question: deny`)，他们按合理默认继续执行；不确定项在 raw session 记录，由你事后 review 报告。
>
> **弹框冒泡保证**：subagent 的 `question` 弹框会出现在主会话窗口，用户在主窗口选项回复即可。你不需要导航到子会话。

#### FR-0070.5 必填交互 agent 的 question 场景表 (v0.3.0 落地)

| Agent | 正常路径 | Error Path |
|---|---|---|
| **Scout** | repo owner / repo name / initial version / spec-id / release branch | GitHub API 权限不足 → "无写权限，改用手动 `gh auth login` 后重试?" |
| **Sage** | FR 档位 / AC 边界 / 需求冲突 | spec 内部矛盾 (FR-100 vs FR-200) → "已检测到 N 处矛盾，优先级: A 覆盖 B / B 覆盖 A / 升级人类?" |
| **Archer** | 测试策略 / 架构 trade-off | 多个 spec-id 同时存在 → "按 spec-id 优先级 A > B > C 处理?" |
| **Judge** | severity 校正 / finding 豁免 | 找到 critical 但用户已决定"接受风险" → "豁免理由: ________" (留 raw 记录) |

4 个交互式 subagent 的 prompt 中**显式列出**此表格，避免漏问 / 多问。

#### FR-0070.6 5 分钟 IDE 实测基线 (NFR-0040 子项)

v0.3.0 release 前**必须**做一次 5 分钟 IDE 实测，确认以下 5 项（实测模板）：

```
FR-0070 实测: 2026-MM-DD HH:MM by Aaron/Kilo
1. <Leader>a agent 列表: [ ] 仅 maestro (符合 FR-0060.2)
2. Maestro 调 task 启动 Scout: [ ] Scout 子会话创建成功
3. Scout 调 question 工具: [ ] 弹框冒泡到主窗口 / [ ] 需 <Leader>+Down
4. 用户选项回复后: [ ] Scout 继续执行
5. Scout 完成后: [ ] 焦点自动回 Maestro, 全程未按 <Leader>a
结论: [ ] FR-0070 可放心落地 / [ ] 需 README 警告 / [ ] 退回方案
```

实测结果记录在 `.louke/qwen-review-v0.6-009.md` §10 + v0.6-009 spec 文件头。

#### FR-0070.7 Subagent 调度方式 (clarification, 2026-07-04)

> 2026-07-04 Aaron 测试发现: `opencode run --agent <name>` (CLI) 和 OpenCode `task` 工具 (TUI 内部) 是两种不同层面的操作, 容易混淆. 本节明确 Louke 走哪条.

**Louke 唯一的 subagent 模式**:

- **生产模式** (默认, 唯一): OpenCode TUI 里 Maestro 当 primary → 调内置 `task` 工具 → 启动 subagent 隔离子会话
- **禁止**用 `opencode run --agent <name>` 调子 agent (那是 OpenCode CLI 模式, 让 `<name>` 作为 primary 在新 session 跑, 不算 subagent 模式)

| 模式 | 调用者 | `<name>` 角色 | 父窗口 | `question` 行为 | 适用 |
|---|---|---|---|---|---|
| `task` 工具 (生产) | OpenCode 内置 (Maestro 调) | subagent | Maestro | 弹框冒泡到 Maestro | Louke 工作流 (M-FOUND → M-SPEC → ...) |
| `opencode run --agent <name>` (CLI) | 用户 / 脚本 | primary | 无 (新 session) | 弹在 `<name>` 自己窗口 / stdout | 单独验证 / CI / 批处理 |

**实施规则**:
- `agents/Maestro.md` prompt **显式**写"只**用 `task` 工具调子 agent, **不要**用 `opencode run`" (v0.6.10 已加)
- 其它 11 agent prompt 维持现状: "你是 subagent, 由 Maestro 调起"
- 验证 subagent 行为 (如 question 冒泡) 必须用 OpenCode TUI, 不能用 CLI 测 (CLI 测不到冒泡是设计, 不是 bug)

**Aaron 的测试澄清**:
- `opencode run --agent sage "..."` 是 CLI 模式, sage 作 primary, question 不冒泡 (符合设计)
- TUI 里 Maestro → task → Sage 模式才会冒泡 (OpenCode 内置行为)

---

## 4. 非功能需求

### NFR-0010 向后兼容 (含 breaking change 显式声明)

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

⚠️ **Breaking change 显式声明**: 升级 v0.6-009 后, 用户的 `<Leader>a` 列表从 "12 agent" 变为 "仅 Maestro"。

未加完整 `permission:` 块的 7 个非交互式 subagent (Sage / Lex / Devon / Scout / Shield / Keeper / Prism) 在 v0.3.0 仅含 `permission.question: deny` 最小块，其余字段仍走 OpenCode 全局默认；若用户的 `~/.config/opencode/opencode.json` 设置了宽松默认，这 7 个 agent 仍可调用 `question` 之外的工具（这与 spec 期望“白名单默认 deny”不符，但属 v0.6-010+ 完整 `permission` 块范畴）。

`lk board opencode` 生成的 `.opencode/agents/{name}.md` 文件:
- 4 目标角色 → 含完整 `permission:` 块 (YAML 对象)
- Maestro → 含完整 `permission:` 块 (FR-0060.1)
- 其余 7 个 → 含最小 `permission:` 块（仅 `question: deny`），其余字段走 OpenCode 全局默认

**用户感知**:
- 升级前: 12 agent 顶层可见
- 升级后: 1 agent 顶层可见 (Maestro), 其它需通过 Maestro `task` 调
- 影响范围: 习惯于直接切 Sage/Devon 写代码的用户, 需要适应新工作流

### NFR-0020 不影响 lk models / lk init

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

本 spec 不修改 `lk models` (属 v0.6-008 FR-0201 范围) 和 `lk init` 主体行为 (属 v0.6-008 §1 范围)。`lk init` 生成的 `opencode.json` 加 `"default_agent": "maestro"` 已在 v0.6-008 FR-0300 覆盖。

### NFR-0030 文档语言

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

README / README.zh 双语同步; agent prompt 段落统一中文。

### NFR-0040 可降级 + OpenCode 版本检查

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

`mode: subagent` 已通过文档确认支持 (A-001-2), **不需要回退**; FR-0060.2 可放心落地。

`permission.question` 控制 subagent 交互 (替代 `interactive: true`): OpenCode 文档明确支持 `permission` 字段的 `question` 键, 无需回退。

**OpenCode 版本检查** (采纳 A-007-1 建议): `lk agent lint` 加 `--check-opencode-version` flag (默认 off):
- 读 `opencode --version` 输出
- 与 `louke/__init__.py` 的 `MIN_OPENCODE_VERSION` 常量对比
- 低版本打印 warning, 但不阻塞 lint

`MIN_OPENCODE_VERSION = "1.1.1"` (Qwen A-8.4 校准: `permission` 对象格式替代 deprecated `tools` 布尔字段的引入版本; 低于此版本用户生成的 frontmatter 会被 OpenCode 忽略或报错)

### NFR-0050 单一 primary agent 约束

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

升级本 spec 后, louke agent 集合**必须**只有 1 个 `mode: primary` (Maestro), 其余 11 个均为 `mode: subagent`。`lk agent lint` (FR-0040) 强制检查:
- `agents/*.md` 中 `mode: primary` 数量 = 1 (白名单 = maestro)
- `mode: all` 数量 = 0
- 否则 lint exit 1, stderr 含 `only maestro can be primary; found {N} agents with mode: primary/all`

---

## 5. 澄清记录 (Qwen 反馈后, Kilo 决定)

| Q | 议题 | Qwen 建议 | Kilo 决定 |
|---|---|---|---|
| Q1 (FR-0010 权限表) | 4 角色 permission 集合 | ✅ 已通过 (但字段名错, A-003) | 接受 A-003 重构, 详见 FR-0010 |
| Q2 (FR-0030) | 8 个非目标 agent 要不要显式 `permission: all` | 默认否 | 维持 (v0.3.0 不动, v0.6-010+ 再加) |
| Q3 (FR-0040) | lint 集成点 A/B/C | (B) `lk agent lint`, 先用 (C) PoC | 采纳 (B) + 直接落地, 不走 PoC 阶段 (工作量不大) |
| Q4.1 (FR-0060.2) | 11 agent 改 `mode: subagent` | ✅ 文档已确认 | 接受 |
| Q4.2 (FR-0060.1) | Maestro `permission` 集合 | (含 `task` / `webfetch` / 不含 `websearch` / `lsp` / `skill`) | 接受, 同时不含 `todowrite` (A-010-4 risk 2) |
| Q4.3 (NFR-0040) | 回退机制 | 改成"重构" + 加版本检查 | 接受 |
| Q5 (FR-0060.5 文档) | 11 subagent prompt 加"## 你的身份" | 默认 | 接受 |
| Q6 (FR-0070 交互式集合) | 4 vs 8 vs 11 | (A) 4 个 | 接受 (A), 详见 FR-0070.1 |
| **Q7 (A-004-1)** | v0.6-008 FR-0200 加 supersede 注释 | 加 `> ⚠️ SUPERSEDED by v0.6-009 FR-0060.2` | 接受, 实施 |
| **Q8 (A-006-1)** | AskUser 场景表加 Error Path | 加列 | 接受, 详见 FR-0070.5 |
| **Q9 (A-007-3)** | README "已知限制" 子段 | 加 | 接受, 详见 FR-0050 |
| **Q10 (A-008-3)** | board.py 透传白名单 | PASSTHROUGH_KEYS 维护 | 接受, 详见 FR-0030 |
| **Q11 (A-009-2)** | lint 工具名 `lk agent lint` | 接受 | 接受 |
| **Q12 (A-010-3)** | v0.3.0 / v0.3.1 拆分 | 拆分, FR-0070 推迟 | **已修订**：2026-07-03 14:00 IDE 实测通过, FR-0070 合并入 v0.3.0, 详见 §0.4 |
| **Q17 (实测结果)** | A-001-4 subagent `question` 冒泡 | Aaron IDE 实测通过 | 接受, FR-0070 全家合并 v0.3.0 |
| **Q13 (A-010-4 risk 4)** | Maestro `mode: all` → `mode: primary` | 改 | 接受, 详见 FR-0060.1 |
| **Q14 (Qwen 二轮 A-8.2)** | 4 角色 + Maestro 加 `external_directory` / `doom_loop` 显式 deny/ask | 接受 | 详见 FR-0010.1~0010.4 + FR-0060.1 |
| **Q15 (Qwen 二轮 A-8.3)** | FR-0070.3/0070.4 方案 (b): v0.3.0 prompt 与 config 同步非交互 | 接受 | 详见 FR-0070.3/0070.4 |
| **Q16 (Qwen 二轮 A-8.4)** | `MIN_OPENCODE_VERSION = "1.1.1"` | 接受 (Qwen 校准准确) | 详见 NFR-0040 |

---

## 6. 关联文件

| 文件 | 改动 |
|---|---|
| `agents/Warden.md` | 加 frontmatter `mode: subagent` + `permission: { ... }` (FR-0010.1) + "你的工具"段落 (FR-0050) + "你的身份"段落 (FR-0060.5) + "非交互身份"段落 (FR-0070.3) |
| `agents/Judge.md` | 同上 + permission 含 `question: allow` (FR-0010.2) + "你的交互能力"段落 (FR-0070.3) + AskUser 场景表 (FR-0070.5) |
| `agents/Archer.md` | 同 Warden + permission 含 `edit: allow, question: allow` (FR-0010.3) |
| `agents/Librarian.md` | 同 Warden + permission 含 `edit: allow` (FR-0010.4) |
| `agents/Maestro.md` | 改 `mode: all` → `mode: primary` (FR-0060.1) + `permission: { task: allow, ... }` + "你的编排模式"段落 (FR-0060.5) + subagent 交互模式说明 (FR-0070.4) |
| `agents/{Scout,Sage}.md` | `mode: all` → `mode: subagent` (FR-0060.2) + "你的身份"段落 (FR-0060.5) + "你的交互能力"段落 (FR-0070.3) + AskUser 场景表 (FR-0070.5) |
| `agents/{Lex,Devon,Shield,Keeper,Prism}.md` | `mode: all` → `mode: subagent` (FR-0060.2) + "你的身份"段落 (FR-0060.5) + "你的非交互身份"段落 (FR-0070.3) |
| `louke/board.py` | `cmd_opencode` 改用 `PASSTHROUGH_KEYS` 透传白名单 (FR-0030) + 透传 `mode:` (FR-0060.4) |
| `louke/agent.py` | **新建**: `lk agent lint` 实现 (FR-0040) |
| `louke/__init__.py` | 加 `MIN_OPENCODE_VERSION = "1.1.1"` (NFR-0040) |
| `louke/archer.py` | 无改动 (lint 移走) |
| `README.md` / `README.zh.md` | 加"Agent 权限矩阵"小节 (FR-0050) + "分层编排"小节 (FR-0060.5) + "已知限制" (FR-0050) |
| `.louke/project/specs/v0.6-008-louke-v030-usability-closure/spec.md` | FR-0200 段落加 `> ⚠️ SUPERSEDED by v0.6-009 FR-0060.2 (2026-07-03)` 注释 |
| `tests/test_agent_frontmatter.bats` | 新增: FR-0010/0020/0030/0040/0060 校验 + NFR-0050 单一 primary 约束 |
