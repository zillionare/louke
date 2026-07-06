# Quote Dialogue Protocol (louke 引用协议)

## 1. 用途

louke 多 agent 用 markdown **嵌套 blockquote + speaker-tag** 在 `spec.md` / `acceptance.md` 里直接展开多轮讨论, 不需要 PR, 不需要在 chat 里发纯文字.

**适用场景**:
- Sage ↔ 用户澄清需求 (Step 2-3)
- Lex ↔ 用户质疑 spec 覆盖率
- 任何 subagent ↔ 用户的多轮问答
- 用户主动发起对 spec 任意段落的疑问
- 给其它 Agent/人类看的提醒 - 使用 >[!NOTE]

## 2. 语法

### 2.1 三种 quote 块

louke 识别三种 quote, 视觉外观和用途都不一样:

| 用途 | 语法 | 渲染 | 何时用 |
|---|---|---|---|
| 角色对话 | `> **Speaker**: 内容` | 可见 (引用块) | 你 ↔ Agent 多轮讨论 (本协议主用途) |
| 公开备注 | `> [!NOTE] 内容` | 可见 (GFM admonition 色块) | 单向说明, 不属于对话链 (如"本节待 Sage 在第二轮补全") |
| Agent 内部笔记 | `<!-- 内容 -->` | **不可见** (HTML 注释) | 自己的草稿/待办, **不应**进 git 历史 |

**关于 `[!NOTE]` admonition**: 沿用 GitHub Flavored Markdown (GFM) 的 admonition 语法. 渲染时带颜色框 (note 是蓝色), 视觉上**立即**区分于普通对话 quote. 也可用 `[!TIP]` / `[!WARNING]` / `[!IMPORTANT]` 等 GFM 变体.

**关于 speaker-tag 与 `[!NOTE]` 的区别**: speaker-tag (粗体) 是**对话** (有 reply 对象, 多轮嵌套); `[!NOTE]` 是**说明** (无 reply, 单向). 视觉上: speaker 走 `**` 粗体, NOTE 走 `[!]` 方括号大写, 不会混淆. (两者都是 Quote Dialogue 协议的一部分, 只是语义角色不同.)

**为什么 `<!-- -->` 必须隐藏**: agent 草稿/猜测不应进 git 历史 (如"我担心这个 FR 用户会反对, 但不敢说"). agent 在 commit 前必须 strip 所有 `<!-- ... -->` 块.

### 2.2 speaker 标识

格式: `> **SpeakerName:** {comment content}`

- `>` 后必须有空格 (CommonMark 规范)
- `**{SpeakerName}:`** — SpeakerName 是发言者, 粗体 + 冒号
- 然后一个空格, 然后是 comment 内容

**SpeakerName 取值**:
- 用户: 用户自定义名 (例: `Aaron`, `Bob`, `张三`)
- louke agent: agent 角色名 (例: `Sage`, `Lex`, `Archer`, `Maestro`, `Judge`)
- 任意第三方 (其它 agent 或人类): 任意字符串

**大小写不敏感** (从 louke v0.6.16 起):
- `Sage` / `sage` / `SAGE` 解析为**同一** speaker
- `Aaron` / `aaron` / `AARON` 解析为**同一** speaker
- 实现: parser 内部统一 lowercase 比较/存储, 但**显示**保留用户原始大小写
- 理由: 人名不会因为大小写就变成另外一个人; 大小写敏感会让用户和 agent 都踩坑

### 2.3 Mention 语法 (`@` 前缀)

在多人对话场合下, 显式 mention 某人要求其回复. 借鉴 GitHub/Slack/discourse 的 `@` 习惯:

| 语法 | 语义 |
|---|---|
| `> **Sage:** 问...` | 普通 quote (被 reply) |
| `> **@Sage:** 你来回答` | **显式 mention** (要求 Sage 必须回复) |
| `> **@Sage+Lex:** 你俩都要看` | 多人 mention |

**与嵌套组合**: mention 不影响 quote 嵌套层级, 可与 `>>` 自由组合 (`>> **@Sage:**`, `>>> **@Lex:**`).

**Mention 优先级** (agent 处理流程时):
1. 解析所有 `> **@Speaker:**` 标记为 pending-mention
2. 即使本轮流程不归该 speaker 负责, 也要在下轮回应
3. 多个 mention 同时存在时, 严格按 mention 出现的**顺序**处理 (先到先答)

**Mention 与普通 quote 的视觉差异**: `@` 前缀仅作语义标记, 渲染上与普通 quote 相同. parser 解析时区分.

### 2.4 嵌套规则 (多轮对话)

借自 email/usenet 传统 — markdown 的 `>` 直接源自 email 的 `>`. 嵌套 `>>` = reply, `>>>` = reply-to-reply:

| 嵌套层级 | 含义 | 例 |
|---|---|---|
| `> **A:**` | 第 1 级 (A 的原话) | `> **Aaron:** 这个半径是 DP 还是物理像素?` |
| `>> **B:**` | 第 2 级 (B 对 A 的回复) | `>> **Sage:** 是设备无关像素` |
| `>>> **A:**` | 第 3 级 (A 对 B 的回复) | `>>> **Aaron:** OK, 锁定` |
| `>>>>`+ | 第 4+ 级 | 极少用, 建议拆为新 FR |

**重要约束**:
- 嵌套层级**仅指示对话链的深度**, 不直接指示"谁回复谁" — 回复对象由阅读者根据上下文判断
- 实际使用中, 嵌套通常 **1-3 级足够**, 4+ 级建议拆为新 FR 单元
- 每多 `>` 一级 = 多回复一层

### 2.5 跨行内容 (CommonMark lazy continuation)

speaker 第一行后的内容可跨行延续, 解析器会把整段视为该 speaker 的原话:

```markdown
> **Sage:** 这个问题分两部分:
> 1. 颜色和粗细
> 2. 撤销/重做
>
> 第 1 个我建议加工具条; 第 2 个先不做.
```

注意第 4 行 `>` 是**空 quote** (speaker 内的段落分隔), 不要和"speaker 切换"混淆.

## 3. 完整示例

```markdown
### FR-0010 用户登录

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

用户用邮箱 + 密码登录. 密码至少 8 位.

> **Sage:** 密码需要支持特殊字符吗?
>> **Aaron:** 支持, 但不强制要求. 让用户自己决定.
> **@Lex:** 这个 AC 覆盖到了吗?
>> **Lex:** 我审了, 覆盖率 OK.
>>> **Sage:** 收到. FR-0010 锁定.

> [!NOTE]
> 这一批 FR 都已通过 Lex 审, 可以并行进 Archer 阶段.
```

## 4. 易错点 (清单)

- ❌ `> **Name**` 后忘记加空格 — CommonMark 规范要求 `>` 后必须有空格
- ❌ `**Name**` 忘记 `**` 粗体包裹 — 不会被解析为 speaker
- ❌ 嵌套 `>>` 后忘记加一个空格 — 同上
- ❌ 在 chat 里发纯文字回复 — 违反协议, 必须留 quote dialogue 历史
- ❌ 用 `[note]` 而非 `[!NOTE]` — 不是 GFM admonition, 不会带色块渲染
- ❌ 用 `<!-- -->` 写完不删就 commit — 草稿会进 git 历史
- ❌ 嵌套 4+ 级不拆 FR — 视觉混乱, 难追踪
- ❌ 用 `@Speaker` 在 chat 里 (不写 quote) — mention 必须在 quote block 内才有效
- ❌ 用 `@all` / `@everyone` 群 mention — louke 不支持, 请按需具体 mention

## 5. 版本

- v1.1 (2026-07-04) — 大小写不敏感 + `@` mention 语法 + `[!NOTE]` admonition
- v1.0 (2026-07-04) — 初版, 随 louke v0.6.16 发版
