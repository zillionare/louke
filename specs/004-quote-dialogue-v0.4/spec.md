# Quote Dialogue 需求澄清 — Spec

- **Spec ID**: 004-quote-dialogue-v0.4
- **创建日期**: 2026-06-15
- **状态**: 草稿

## 用户故事

### US-010
story: 作为 spec 作者，我想用 markdown 的 quote 语法在 IDE 中直接跟 sage 对话澄清需求，以便免去 PR review 的繁琐流程。
priority: P0

### US-020
story: 作为 spec 作者，我想既能在 sage 提问处回复，也能对 spec 任意段落提出自己的疑问，以便澄清工作既可由 sage 驱动，也可由作者主动发起。
priority: P0

## 用户使用场景

### scenario-010

1. 用户在 IDE 中打开 `specs/{spec-id}/spec.md`
2. 看到 sage 留下的 `> **Sage:**` 提问块，作者在下方插入 `>> **Aaron:**` 回复
3. 看到 spec 中某段自己不确定的描述，作者直接在段落后插入 `> **Aaron:** {question}` 块
4. sage 在下一个回合读完整 spec，把所有新 `>` 块按 "speaker / depth" 解析，给出 `>>>` 回复
5. 一轮轮迭代，直到所有单元的 `resolved: ✅` 且没有未解决的 quote 块

## 功能需求

> **格式约定（必读）**: 每个 FR 单元都由三级标题+空格+FR-XXX（大写，3位零填充）+ {title} 引起，随后是需求描述和元数据，遇到以下情况时，本 FR 单元结束：
  1. 遇到一个二级标题
  2. 遇到下一个 FR 单元
  3. 文件结尾
   合格的 FR 单元必须满足以上格式要求。
> **编号约定(必读)**： FR 的编码采用3位数字，0填充，初稿时从10开始，每次增加10；以便后续可以随时在中间插入新的 FR。
> **必读**： FR-XXX 编号即该需求的 id。禁止删除已有需求 id，以避免引用混淆；如需废弃某 FR，在其元数据中, valid 改为 false，并在澄清记录中说明。

### FR-010 quote-block 语法识别

`tools/quote_parser.py` 必须能够：
- 解析 `> **Name:**` 这种以加粗的 `**Name:**` 开头的 quote 块
- 区分 speaker (从 `**Name:**` 取) 与 depth (从 `>` 的层数取)
- 当同一段后存在多轮块时，按 depth 升序组织成对话链

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### FR-020 speaker 身份由加粗 name 决定

speaker 身份**不**由 `>` 嵌套层数 (depth) 推断，而是由 `**Name:**` 前的加粗文本决定。depth 仅用于排序与"在 IDE 中自然缩进显示"。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### FR-030 状态标记

每条 quote 块的尾部（块内最后一行）允许用以下 5 种 status marker 之一收尾：

| marker | 含义 |
|---|---|
| `✓` | 已解决 |
| `[open]` | 仍开放，等下一轮 |
| `[blocked-by-N]` | 被 quote N 阻塞 |
| `[wontfix]` | 决定不处理 |
| `[superseded]` | 已被新版本替代 |

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### FR-040 unit 划分与 yaml 元数据

`tools/quote_parser.py` 必须能：
- 切分 `### US/FR/NFR-XXX` 单元
- 解析每个单元末尾的 yaml 块（`testability / resolved / valid`）
- 把 quote 块按它所在 spec 内的"上下文段落"归到某个 unit

```yaml
testability: ✅
resolved: ⚠️
valid: ✅
```

> **Sage:** FR-040 里"按它所在 spec 内的'上下文段落'归到某个 unit"，具体规则请你澄清：
> - Q1: 你的预期是 **preceding-unit**（quote 块往上找到最近的 `### US/FR/NFR-XXX` 单元），还是 **section**（按 `## 用户故事 / ## 功能需求 / ## 非功能需求` 大节归属）？
> - Q2: 如果 quote 块出现在 `## 用户使用场景` 这种没有 unit 的大节里，应该归到哪里（归到上一个 FR / 报错 / 标 unassigned）？
>
> ✓

### FR-050 unit-ready 判定

`tools/quote_parser.py --check-ready` 应当：
- 对 FR/NFR 单元：要求 `yaml.resolved == ✅` **且** 该 unit 内无 `[open]` quote
- 对 US 单元：要求最后一条 quote 状态是 `✓`/`[wontfix]`/`[superseded]`，或 unit 内无 quote
- 输出每个 unit 的 ready 状态及阻塞原因

```yaml
testability: ✅
resolved: ⚠️
valid: ✅
```

> **Sage:** FR-050 我倾向先只覆盖 FR/NFR，但需要你拍板：
> - Q3: US (用户故事) 单元要不要也走 `--check-ready` 判定？理由：US 主要是"我想要 X"，没 quote 时默认可视作 ready；但用同一套规则更简单。
> - Q4: "用户使用场景" (scenario) 算不算 unit？我倾向不算（它是 narrative，不是 actionable requirement）。
>
> [open]

### FR-060 用户侧编辑器不需扩展

用户只用原生 IDE 即可完成澄清（无需装 markdown 插件或扩展工具）。quote 块只是普通 markdown。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### FR-070 agent 侧无 PR 依赖

sage / lex 在执行 quote dialogue 流程时，不应触发任何 GitHub PR 流程（包括开 PR、request review、PR review 评论）。所有"评审/澄清"动作都只发生在 spec.md 的 quote 块上。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

## 非功能需求

> **必读**: 本节的格式、编号等要求同 FR，此处省略。

### NFR-010 quote 解析在 1MB spec 内 < 1s

`tools/quote_parser.py` 解析单文件 < 1MB 的 spec.md，端到端解析时间 < 1 秒（不含 yaml 解析之外的 IO）。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### NFR-020 错误信息包含 quote 块行号

当 quote 块缺 status marker、speaker 缺失、深度冲突时，`quote_parser.py` 抛错必须包含 `line:N` 位置信息，便于 IDE 跳转。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```
