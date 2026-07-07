---
name: inline-discussion
description: Defines inline-discussion format for structured discussion in spec files. Use when agents need to leave traceable multi-round comments and query discussion status via lk discuss.
license: MIT
compatibility: opencode
metadata:
  audience: agents
  workflow: louke
---

## What I do

定义了 inline-discussion 的格式规范，何时使用它，以及读写工具。

### When to use inline-discussion?

- Clarifying FR/NFR boundaries with users or other agents
- Reviewing spec coverage, test plans, interfaces, or architecture
- Any multi-round discussion that must be traceable in project docs


## 1. 概述
**Inline Discussion** 允许审阅者在 Markdown 文件的特定内容下方，直接发起或参与异步讨论。整个讨论通过 Markdown 原生的**块引用（Blockquote）**语法进行嵌套表示，无需引入额外的前端标记语言，确保纯文本环境下的高可读性和 Git 版本追踪的友好性。

## 2. 核心语法定义

### 2.1 讨论节点（Discussion Node）

一个讨论节点由 **根评论（Root Comment）** 及其下方的 **嵌套回复（Nested Replies）** 组成。

- **根评论（发起新讨论）**：使用 **1 个** `>` 符号开头。
- **回复评论**：每回复一层，在原有的 `>` 基础上 **增加 1 个** `>` 符号（即增加一级缩进）。

### 2.2 评论行格式

每一行评论必须遵循以下结构：

```markdown
> [缩进层级] **发言者标签 [状态标记]:** 评论内容
```

| 组成部分 | 说明 |
| :--- | :--- |
| **缩进层级** | 由连续的 `>` 符号组成（如 `>`, `>>`, `>>>`），数量代表嵌套深度。 |
| **SpeakerName** | 被一对 `**`（加粗）包裹的字符串，代表评论作者（如 `**Sage**`）。SpeakerName 大小写不敏感（`Sage` / `sage` / `SAGE` 视为同一 speaker），但显示时保留原样，不做大小写转换。 |
| **状态标记** | **仅限根评论行使用**，紧跟在发言者标签之后，用 `[` `]` 包裹（如 `[RESOLVED]`）。非根评论（回复）不得包含此标记，解析器应忽略回复行中的此类标记。 |
| **分隔符** | 发言者标签（或状态标记）后必须紧跟一个英文冒号 `:`，冒号后空一格再写评论内容。 |
| **评论内容** | 任意 Markdown 文本，支持 `@提及`、行内代码、加粗等基础内联语法。 |

## 3. 状态机规则（判断“讨论是否已完成”）

为了在下一轮 Review 中快速过滤，引入显式状态标记：

| 状态 | 标记语法 | 触发者 | 说明 |
| :--- | :--- | :--- | :--- |
| **进行中 (Open)** | **隐式默认**（无标记） | 系统自动 | 若根评论行中没有 `[RESOLVED]`，则该整棵讨论树视为未完成。 |
| **已解决 (Resolved)** | `[RESOLVED]` | **仅限**该讨论的发起人（根评论作者） | 发起人认为已得到满意答复时，可编辑自己的**根评论行**添加此标记。该标记生效后，整棵讨论树（含所有子回复）在后续审阅中视为“已关闭”。 |
| **重新打开 (Reopen)** | `[REOPEN]` | 所有人 | 在发起人确认已解决后，其它人重开 |

> **注意:** 解析器/渲染器在检测状态时，**只检查一级缩进（即单个 `>`）的根评论行**。二级及以下的嵌套回复中的 `[RESOLVED]` 字符串应被视为普通文本，不具备状态切换权限。


## 4. 讨论线程的边界界定

如何区分两个不同的讨论？规则如下：

- **新线程开始**：每当解析器遇到一个 **一级缩进（`>`）** 的评论行，且它**不是**紧接在另一个一级缩进的下方作为回复时，即视为创建一个全新的 Inline Discussion 线程。
- **线程归属**：某个一级缩进行之后的所有 **更高缩进层级（`>>`、`>>>` 等）** 均归属于该线程，直到遇到下一个新的一级缩进（`>`）为止。


## 5. 标准语法示例

以下示例展示了完整的语法结构及状态标记的用法：

```markdown
# 原文段落（下方锚定讨论）

> **Sage [RESOLVED]:** What should happen when depth is zero?
>> **Maestro:** I don't know, need @Aaron's input.
>>> **Aaron:** Treat it as invalid input and return -1.

> **Aaron:** This is another thread, need help with the API.
>> **Sage:** I'll handle this later. 
>> (注：此线程根评论无 `[RESOLVED]` 标记，系统默认其为 `OPEN` 状态)
```

**解析结果说明：**

- **线程 1**：由 `Sage` 发起，状态为 **已解决（RESOLVED）**。`Maestro` 和 `Aaron` 的回复分别使用 `>>` 和 `>>>` 缩进。
- **线程 2**：由 `Aaron` 发起，根评论无标记，状态为 **进行中（OPEN）**。`Sage` 的回复使用 `>>` 缩进。
- 在线程1中，Maestro 还通过 `@Aaron` mention 请求 Aaron 来回答此问题。

## 6. 如何使用 inline-discussion

inline-discussion 提供了工具来查找文档中所有的 inline-discussion 会话，以及各种过滤工具。

### 查找所有的对话

```bash
lk discuss query --file <markdown-file>
```

输出为一个 JSON 数组，格式如下：

```json
[
  {"thread_id": "T-001", "initiator": "Sage", "status": "RESOLVED", "last_speaker": "Aaron", "reply_count": 2, "snippet": "What should happen when depth is zero?",
   "total_lines": 230, "anchor_line": 45, "anchor_text": "用户用邮箱 + 密码登录。密码至少 8 位。", "root_line": 47, "root_text": "Sage: What should happen when depth is zero?"},
  {"thread_id": "T-002", "initiator": "Aaron", "status": "OPEN", "last_speaker": "Sage", "reply_count": 1, "snippet": "This is another thread, need help with the API."}
]
```

**thread_id**: `T-NNN` 格式（per file 自增序号），**不**含位置/内容 hash。定位由 5 元组字段（`total_lines` / `anchor_line` / `anchor_text` / `root_line` / `root_text`）提供，agent 调用 reply/edit/set-status 时传回 parser 做 4 级降级查找。

### 会话筛选

1. 查找 `<Agent>` 发起的所有会话:
   ```bash
   lk discuss query --file <markdown-file> --initiator <agent>
   ```
2. 加上状态过滤（`open` / `resolved` / `reopen`）:
   ```bash
   lk discuss query --file <markdown-file> --initiator <agent> --status open
   ```
3. 加上 `--blocker` 过滤（查找正在等待某 `<Agent>` 回复的 Open 会话）:
   ```bash
   lk discuss query --file <markdown-file> --blocker <agent> --status open
   ```

### 发起对话

```bash
lk discuss start --file <markdown-file> --anchor-line <N> --speaker <agent> "<message>"
```

`--anchor-line <N>` 是被评论内容的行号（agent 从 `query` 输出或自己读 spec.md 拿到）。`lk` 自动读取该行内容作 anchor_text，`<message>` 插入到该行后第一个空行之后。

> 注: **不**新增 `lk discuss anchor` 子命令（P1-NEW-2 决定）—— `start --anchor-line` 已足够 agent 选择锚点。

### 回复会话

```bash
lk discuss reply --file <markdown-file> --thread-id <id> \
  --anchor-line <N> --anchor-text "<text>" \
  --root-line <N> --root-text "<text>" \
  --speaker <agent> "<message>"
```

`lk` 通过 `thread-id` 定位会话，5 元组定位字段辅助在文件变更后仍能定位。`<message>` 追加到该会话末尾。

