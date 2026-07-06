# v0.6-016 — Quote Dialogue Speaker-Tag 协议 — Spec

- **Spec ID**: v0.6-016-quote-dialogue-protocol
- **创建日期**: 2026-07-04
- **状态**: 草稿
- **作者**: Kilo (受 GLM 委托, 见 `.louke/review-sage-question-tool.md` §7.0)
- **关联**:
  - 既有规范: v0.4-004-quote-dialogue (quote dialogue 流程)
  - 关联 issue: [#XX] Quote Dialogue 协议正式化
  - Aaron 2026-07-04 决定: 把 Sage.md Step 3 大段例子外提为规范

## 0. 范围与边界

### 0.1 本 spec 收纳

| 主题 | FR 范围 |
|---|---|
| Quote Dialogue 协议语法 | FR-0010 ~ FR-0030 |
| louke 12 个 agent 全部学习该协议 | FR-0040 |
| 用户文档 (cookbook) 教用户写 quote reply | FR-0050 |
| 与 v0.4-004 quote dialogue 流程的边界 | §0.2 |

### 0.2 supersede 关系

- **v0.4-004-quote-dialogue FR-010 (quote-block 语法识别)**: 仍有效, **不替代**. 本 spec 在其基础上**扩展** speaker-tag 协议 (Quote Dialogue 的子组件).
- **v0.4-004-quote-dialogue FR-020+ (quote dialogue 流程)**: 仍有效, **不替代**. 流程由 v0.4-004 定义, 语法由本 spec 定义.
- **agents/Sage.md L37-41 (Quote Dialogue 速查表)**: 草稿级, **本 spec 替代**. 后续 Sage.md 引用本 spec.
- **agents/Lex.md 自由使用 `> **Lex:**`**: 不规范, **本 spec 替代**. Lex.md 后续引用本 spec.
- **README.md / cookbook.md 关于 quote 协议的描述**: 当前不存在, 本 spec FR-0050 补上.

### 0.3 本 spec 不收纳

- quote_parser.py 解析器实现 (v0.4-004 FR-010 已覆盖)
- quote dialogue 流程 (v0.4-004 已覆盖, 重新引用)
- 其它 markdown 扩展语法 (tables, alerts 等) — 与本协议无关

---

## 1. 用户故事

<a id="us-0010"></a>

### US-0010

story: 作为 louke 用户, 我想在 IDE 里用标准 markdown 直接与 agent 多轮对话, 不需要装额外扩展.

priority: P0

---

## 2. 功能需求

> **编号约定(必读)**: FR 编码采用 4 位数字, 0 填充, 步长 10 (FR-0010, FR-0020, ...).
> **必读**: FR-XXXX 编号即该需求的 id. 禁止删除, 废弃标 `valid: false`.

<a id="fr-0010"></a>

### FR-0010 Quote Dialogue 协议正式语法

**正式名称**: **Quote Dialogue Protocol (QDP)** — 嵌套 markdown blockquote 上携带的**轻量级发言者标识** (speaker-tag), 借自 email/usenet 传统
(markdown `>` 直接源自 email `>`, 嵌套 `>>` = reply, 嵌套 `>>>` = reply-to-reply).

**语法形式**:

```markdown
> **SpeakerName:** {comment content}
```

- `>` 起始 (block quote marker, 见 CommonMark §5.1)
- 后接一个空格
- 然后 `**{SpeakerName}:`** — SpeakerName 是发言者的人/agent 标识 (粗体 + 冒号)
- 然后一个空格
- 然后 comment 内容

**SpeakerName 取值**:
- 用户: 用户自定义名 (例: `Aaron`, `Bob`, `张三`)
- louke agent: agent 角色名 (例: `Sage`, `Lex`, `Archer`, `Maestro`, `Judge`)
- 任意第三方 (其它 agent 或人类): 任意字符串

**嵌套规则**:
- `> **A:**` = 第 1 级 (A 的原话)
- `>> **B:**` = 第 2 级 (B 对 A 的回复)
- `>>> **A:**` = 第 3 级 (A 对 B 的回复)
- 嵌套层级仅指示**对话链的深度**, 不指示谁回复谁 (回复对象由阅读者根据上下文判断)
- 实际使用中, 嵌套通常 1-3 级足够, 4+ 级建议拆为新 FR 单元

**与 v0.4-004 quote-block 的关系**:
- v0.4-004 定义了 `> **Name:**` 的**解析** (speaker 提取, depth 计数)
- 本 spec 定义了 `> **Name:**` 的**语义** (谁是发言者, 多轮对话如何展开)
- 解析器和协议是同一个东西的两面, 协议替代解析器实现细节

**AC**:
- AC-1: spec.md 内任意 `> **Name:**` 块可被 quote_parser.py 解析为 (speaker, depth, content) 三元组
- AC-2: 嵌套 `>> **B:**` 的 depth = 2
- AC-3: SpeakerName 大小写敏感 (例: `Sage` ≠ `sage`)
- AC-4: 紧邻 `**Name:**` 后的内容 (一行内) 视为 speaker 的原话; 跨行内容视为延续 (CommonMark lazy continuation)

<a id="fr-0020"></a>

### FR-0020 三种 quote 类型语义区别

spec.md 中可出现三类 quote, 语义**不同**:

| 语法 | 语义 | 渲染 | 用途 |
|---|---|---|---|
| `> **SpeakerName:** content` | 角色对话 | 可见 (引用块) | agent ↔ 用户 ↔ 其它 agent 之间的多轮讨论 (本 spec 主用途) |
| `> [note] content` | 公开备注 | 可见 (引用块) | 单向说明, 不属于对话链 (如"本节待 Sage 第二轮补全") |
| `<!-- content -->` | agent 内部笔记 | **不可见** (HTML 注释) | agent 自己的草稿/待办, 不进 spec 终稿 |

**为什么 `[note]` 用方括号**: 避免被误以为是名为 "Note" 的 user/agent 的评论. `**Speaker**` 走粗体格式, `[note]` 走方括号格式, 视觉上立即区分.

**为什么 `<!-- -->` 必须隐藏**: agent 草稿不应进 git 历史 (如"我担心这个 FR 用户会反对, 但不敢说"). 见 NFR-0020.

**AC**:
- AC-1: parser 区分三类 (对话/备注/草稿), 仅前两类进 spec 终稿
- AC-2: 任意 `<!--` 开头的行被 parser 视为内部笔记, 不进 quote dialogue 链
- AC-3: `[note]` 解析为 note 角色, 不带 speaker (避免与"名为 Note 的用户"冲突)

<a id="fr-0030"></a>

### FR-0030 quote dialogue 多轮协议

**调用前提**: 已存在 v0.4-004 FR-010 定义的 quote_parser.py 解析能力. 本 spec 仅定义**多轮对话的展开规则**.

**单轮操作** (Sage/Lex/Archer 任一 agent 在 IDE 中):
1. 解析当前 spec.md, 找到所有 open 的 quote (depth, speaker, content)
2. 对每个 open quote 判断:
   - 是自己之前的问题 → 看用户是否在嵌套 `>>` 里回复; 没回复就**追问一次** (不擅自决定)
   - 是用户对自己的提问 → 在 `>>>` 嵌套里回答
   - 是用户对其它 agent 的提问 → 跳过, 不越权
3. 操作完做一次 commit + push, 让下一轮能拿到 diff

**退出条件** (单步操作后):
1. 无 open quote 残留
2. 所有受影响 FR 的 `是否已决定` 字段为 `✅`
3. spec.md 已 commit + push

**AC**:
- AC-1: agent 完成一轮 quote dialogue 后, `git log --oneline` 多一个新 commit
- AC-2: agent 不在 chat 里发纯文字回复 (违反协议 — 必须在 spec.md 里留 quote)
- AC-3: agent 不擅自把 `⚠️` 改为 `✅` (严禁沉默即同意)

<a id="fr-0040"></a>

### FR-0040 louke 12 个 agent 引用 QDP

**所有 agent 的 prompt 应在身份段（frontmatter 后第一段）以"何时使用"开头**引用单一信息源 `agents/_protocols/quote-dialogue.md`:

**统一模板** (L18 上下, 紧跟身份段):

```markdown
> **引用**: 当你需要 [本 agent 角色相关的触发场景] 时, 请参考本目录 [`_protocols/quote-dialogue.md`](_protocols/quote-dialogue.md) 的语法.
```

**措辞硬约束**:
- 必须以 "当你需要..." 开头 (动作触发, 避免被动描述"如需...")
- 必须说明**本 agent 角色**的典型使用场景 (e.g. Sage = 与用户多轮澄清, Lex = 对 spec 留审查意见)
- 不能在 prompt 内部重复 QDP 语法定义 (避免与单一信息源不一致)
- 12 个 agent 全部应遵守, 包括 `question: deny` 的非交互式 subagent (它们可能在被动收到 quote dialogue 时需要解析)

**各 agent 当前的"触发场景"** (作为基线, 后续可微调但**不能退回**到被动描述):

| Agent | 触发场景 (短) |
|---|---|
| Sage | 与用户多轮澄清 FR/NFR 边界、或在 spec.md 留 quote dialogue 历史 |
| Lex | 对 spec.md 追加结构化审查意见 (替代 PR review / chat 纯文字) |
| Archer | 就 test-plan.md / interfaces.md 发起多轮澄清、或在 spec.md 留测试问题 quote |
| Maestro | 多 agent 协作上下文以 quote dialogue 形式留痕在 spec.md / test-plan.md |
| Scout | 在 spec.md 中向用户/agent 留言、补充项目初设疑问 |
| Devon | 在 raw session 里留下 quote dialogue 历史 (让下游追溯实现决策) |
| Prism | 在 review 报告中引用 spec quote dialogue、或在 spec.md 留审查 quote |
| Keeper | 在门禁报告中留 quote dialogue (让 Sage 后续 review 时看到出处) |
| Shield | 在 e2e 报告中引用 spec quote dialogue 上下文 |
| Judge | 在审计报告中引用 spec quote dialogue 上下文 (攻击面 / 边界讨论) |
| Warden | 在 spec.md / acceptance.md 中留 quote 形式验收意见 |
| Librarian | 在 wiki 蒸馏 raw 段时保留 quote dialogue 上下文 (避免断章取义) |

**单一信息源的分发机制**:
- `agents/_protocols/quote-dialogue.md` 通过 `pyproject.toml` 的 `package-data` 配置 (`agents/_protocols/*.md`) 一起打包到 `site-packages/louke/agents/_protocols/`
- 用户装的 louke 里**没有** `.louke/project/specs/...` 路径, 引用必须指向 `_protocols/` 才能被 agent 看到

**AC**:
- AC-1: `grep -l '_protocols/quote-dialogue.md' agents/*.md` 返回 12 个文件
- AC-2: 每个 agent prompt 不再独立定义 Quote Dialogue 语法 (避免与 `_protocols/quote-dialogue.md` 不一致)
- AC-3: `tests/test_agent_frontmatter.bats` 加测试, 验证所有 12 agent 含 `_protocols/` 引用
- AC-4: 12 个 agent 引用行均以 "当你需要" 开头 (新增 — 防止退回被动描述)
- AC-5: `pyproject.toml` 的 `package-data` 含 `agents/_protocols/*.md`

<a id="fr-0050"></a>

### FR-0050 用户文档 (cookbook) 教用户写 quote reply

**`docs/cookbook.md` 必须新增一节** "Quote Dialogue — 怎么跟 agent 多轮对话":

- 用 3-5 个真实 example 展示用户常见场景
- 包含: 用户对 agent 提问的回复 / 用户主动发起新问题 / 解决 (resolved) 一个 quote
- **自包含** — 不引用 spec 或 `_protocols/quote-dialogue.md` (用户看不到这些路径, 教程必须独立可读)
- 完整内嵌: 三种 quote 语法 / speaker 命名 / 嵌套规则 / 场景示例 / 易错点清单

**AC**:
- AC-1: `docs/cookbook.md` 包含 "Quote Dialogue" 标题段
- AC-2: 该段至少 3 个可运行 example (回复/主动提问/三方对话)
- AC-3: 该段自包含, 不含 `../` 相对路径引用其它 spec/_protocols 文件

---

## 3. 非功能需求

<a id="nfr-0010"></a>

### NFR-0010 向后兼容 (含 deprecation 显式声明)

- v0.4-004 quote_parser.py 实现**保留** (解析 `> **Name:**` 语法)
- 旧 spec.md 中已存在的 quote 块**不需要重写**
- 本 spec 仅**扩展**语义, 不**变更**解析器
- 用户无感升级: 装新 louke 后, 旧 spec 仍可正常走 quote dialogue 流程

**AC**:
- AC-1: 任意 v0.4-004 时代 spec 文件在 louke v0.6.16+ 下走 quote dialogue 流程, 行为一致
- AC-2: `tools/quote_parser.py --check-ready` 对老 spec 仍返回 exit 0

<a id="nfr-0020"></a>

### NFR-0020 草稿不进 git

- agent 用 `<!-- ... -->` 写内部笔记时, 这些笔记**不应**进 git
- 实现路径: agent 在 commit 前必须 strip 所有 `<!-- ... -->` 块 (用 `git add` 之前 grep + sed 过滤)
- 这是 [Sage.md L464-468](../../../../agents/Sage.md#L464) 已有的"raw 不入 git"约定的**强制化**

**AC**:
- AC-1: agent 的 commit hook 包含 `<!--` grep 检查, 命中则 fail commit
- AC-2: `tests/test_quote_dialogue.bats` 验证: 包含 `<!-- agent draft -->` 的 spec.md 走 commit, git log 不含该字符串

<a id="nfr-0030"></a>

### NFR-0030 文档语言

- 本 spec FR 描述用中文 (与 louke 其它 spec 一致)
- speaker-tag 语法示例保留 markdown 原文 (跨语言)
- 教程段 (FR-0050) 可中英双语 (用户群国际化)

---

## 4. 受影响文件 (Kilo 实施时参考)

| 文件 | 改动 |
|---|---|
| `agents/Sage.md` L37-41 | 替换为 `Quote Dialogue 协议: 参见 v0.6-016 §FR-0010` 引用 |
| `agents/Sage.md` Step 3 | 大段例子外提, 引用本 spec; 保留流程定义 |
| `agents/Lex.md` (任意处) | 加 spec 引用 |
| `agents/{Archer,Judge,Scout,Devon,Keeper,Librarian,Prism,Shield,Warden,Maestro}.md` | 各加一处 spec 引用 (frontmatter 后第一段) |
| `docs/cookbook.md` | 加 "Quote Dialogue" 段 |
| `tests/test_agent_frontmatter.bats` | 加测试: 所有 12 agent 含规范引用 |
| `tools/quote_parser.py` | 不动 (FR-0010 兼容) |
| `.github/RELEASE_NOTES_v0.6.16.md` | 新建, 列 4 项改动 |

---

## 5. 退出条件 (待 Sage 阶段处理)

- [ ] 12 agent prompt 更新完成, 引用本 spec
- [ ] docs/cookbook.md 教程段写完
- [ ] `tests/test_agent_frontmatter.bats` 测试通过
- [ ] 实测一次 quote dialogue: 用户在 IDE 写 `> **Aaron:**` → agent 在 `>>` 回复 → commit + push 链路通
- [ ] release notes v0.6.16 写好

---

## 6. 状态

- 2026-07-04 17:54 Kilo 创建本 spec (受 GLM 委托, 根因 = 7 个 agent permission 不全 → 引出 quote dialogue 协议需要正式化)
- (待 Aaron 拍板) 决定是否采纳 §0.2 supersede 关系
- (待 Sage 阶段) 实施 §4 改动

---

## 7. 相关文件清单

| 文件 | 说明 |
|---|---|
| `.louke/project/specs/v0.4-004-quote-dialogue/spec.md` | quote dialogue 流程规范 (本 spec 在其基础上扩展) |
| `tools/quote_parser.py` | quote 块解析器 (FR-0010 兼容, 不需要改) |
| `agents/Sage.md` L37-41, L131+ | 当前 speaker-tag 速查表 + Step 3 大段例子 (待精简) |
| `agents/Lex.md` | 当前自由使用 `> **Lex:**` (待规范引用) |
| `docs/cookbook.md` | 当前无 quote dialogue 教程 (待补) |
| `tests/test_agent_frontmatter.bats` | 当前无规范引用测试 (待补) |
| `.louke/review-sage-question-tool.md` §7.0 | GLM 重判根因 (task: deny 缺失 → 引出本 spec) |
