# 需求澄清改用 Markdown Quote Block 对话 — Spec

- **Spec ID**: 004-quote-dialogue
- **创建日期**: 2026-06-15
- **状态**: 草稿（Sage Interview 进行中）

## 用户故事

### US-010 作为 specforge 用户，我希望在 IDE 中完成 spec 澄清

story: 作为 specforge 用户，我希望通过 markdown quote block 在 IDE 中完成需求澄清，避免 GitHub PR 权限与 branch 管理的负担。
priority: P0

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### US-020 作为 specforge 用户，我希望 quote 状态可被工具自动判定

story: 作为 specforge 用户，我希望通过 YAML `resolved` 字段和 quote 末标记让工具自动判定 spec 锁定状态，避免人工判定。
priority: P0

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### US-030 作为 Sage，我希望通过 git diff 自动识别用户修改

story: 作为 Sage，我希望通过 `git diff` 自动区分 quote 状态变更、原段修改与新增 quote 三种情况，据此调整追问。
priority: P0

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### US-040 作为 Lex，我希望在 spec.md 中留 quote 形式审查意见

story: 作为 Lex，我希望在 spec.md 中以 quote block 留审查意见而不是 GitHub PR Review，让用户在 IDE 中直接处理。
priority: P0

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

## 设计原则

### 为什么 quote dialogue 不在 chat 里

quote block 对话的**真正价值**不是"用 markdown 替代 PR 评论"，而是:

1. **用户面对完整文档而非孤立问题** — Agent 在记录 story 时可能根本性错误（漏需求、误解意图、错位优先级），用户必须看完整文档才能发现
2. **用户能改任何地方** — 不限于回答 Agent 问题，可以重写整段、新增 FR、删除错的
3. **Diff 是 review 的核心信号** — `git diff` 暴露用户的修改，Agent 据此追问
4. **GitHub 权限不再是瓶颈** — 任何能 `git push` 的人都能用，不需 GitHub 写权限

### chat 是补充，不是主通道

chat 里 Agent 可以:
- 解释"我为什么加这个 FR"
- 提示用户"spec.md L42 有一个潜在歧义"
- 通知用户"Sage 已更新 spec.md，请 review"
- 询问元问题（如"项目叫什么名字"、"FR 编号从几开始"）

但**澄清对话本身在 IDE 编辑的 spec.md 里**。

> **Sage:** FR-027 限定 chat 用途为"通知用户 review / 解释设计意图 / 询问元问题"。但 spec 流程中，Sage 经常需要问"项目叫什么 / FR 起点"。chat 算不算元问题？
>> **Aaron:** 元问题走 chat（快速、不进 spec），内容澄清走 spec.md quote（持久、可追溯）。区分依据：答案是否影响 spec.md 内容。
> > **Sage:** 那么"项目名"这种元问题如果**会**写进 spec frontmatter（属于 spec 内容），是否要走 spec.md？
> > > **Aaron:** 对，会写进文件内容的元问题也走 spec.md。chat 只问"不会被持久化"的事。

```yaml
testability: ⚠️
resolved: ⚠️
valid: ✅
```

## 功能需求

### FR-010 spec.md 必须支持 markdown quote block 形式的对话

spec.md 必须支持 markdown quote block 形式的对话。speaker 由 `**Name:**` 决定（与 depth 无关），嵌套深度仅表示追问链。quote 块必须在 spec.md 中段后追加，紧跟被讨论的原文段落之后，物理位置即引用。

> **Sage:** 例子中说话方用 `> **Sage:**` 和 `> **Aaron:**` 显式标注身份。但有些 Agent 实现可能省略前缀 `**Name:**`（如 `> 这是问题`）。需要规则化强制 `**Name:**` 前缀吗？
>> **Aaron:** 强制。`quote_parser.py` 会因没 `**Name:**` 跳过这条 quote，所以 Agent 必须带前缀。这是格式契约。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### FR-020 每个 FR/NFR 单元必须有 YAML meta 标识 resolved 状态

每个 FR/NFR 单元必须包含一个 ` ```yaml ` 代码块，至少有 `resolved: ✅/⚠️` 字段。`quote_parser.py` 据此判定每个单元是否已闭环。

> **Sage:** ⚠️ `resolved: ✅` 与该单元下 quote 末标记 `✓ resolved` 必须同时满足才认 close？还是只认 YAML 即可？
>> **Aaron:** 两个都查。YAML 是单元总闸，quote 末标记是单条 quote 状态。两条规则都得通过，单元才算 close。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### FR-030 Sage 通过 git diff 自动识别用户修改类型

Sage 在用户声明"review 完了"后，必须执行 `git diff` 并区分:
- (a) **quote 状态变更**（open → resolved 等）: 调整后续追问
- (b) **新增 quote**: 视作用户追问
- (c) **原段修改**（FR/AC 等）: 视作"用户更正 Agent 记录"，silent 不追问

> **Sage:** (c) silent 是否会让用户感觉 Agent 漏读了？
>> **Aaron:** silent 是相对的——Sage 仍然记录用户改了哪里，但**不**主动追问"为什么改"。如果改了之后产生新的歧义，Sage 可以追加新 quote。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### FR-040 quote 状态标记必须支持 5 种值

quote 末必须包含以下状态标记之一:
- `✓ resolved` — 已闭环
- `[open]` — 待回复
- `[blocked-by-N]` — 被 FR-N 阻塞
- `[wontfix]` — 终止
- `[superseded]` — 被新 spec 取代

无 marker 默认为 `open`。`quote_parser.py` 据此分类。

> **Sage:** 是否需要同时支持 emoji 字符作为状态标记（`✅` `⚠️`）？在 YAML 里用 emoji 看起来清楚。
>> **Aaron:** YAML 字段用 emoji（`resolved: ✅`）。quote 末标记保持 ASCII 风格（`✓ resolved`）以便纯文本编辑器可见。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### FR-050 chat 通知触发条件

Sage 在 spec.md 发生任何变更后（含本地修改、push），必须在 chat 通知用户"spec.md 已更新，请 review"。无需用户 push 才能触发。

> **Sage:** "任何变更"如果是本地未 push 的修改，Agent 怎么知道？靠 inotify 还是用户主动告知？
>> **Aaron:** 用户告知（"review 完了" / "continue"）触发 Sage 进入 diff 流程。Agent 不需要文件系统监听。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### FR-060 嵌套深度必须支持 ≥ 3

quote 嵌套深度必须支持 ≥ 3（A → B → A → B 追问链）。`quote_parser.py` 必须能正确解析深度直方图。

> **Sage:** 深度直方图有什么用？
>> **Aaron:** 用处不大，统计信息而已。但**支持深度 ≥ 3** 是必须的（实际对话中会有多轮追问）。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### FR-070 git push 是可选的

spec 澄清可以在本地工作区完成，git push 不是必需步骤。是否 push 由用户决定（远端协作需要 push，单机自举不需要）。

> **Sage:** 那 chat 通知里的"spec 已更新"指本地还是远端？
>> **Aaron:** 指本地。push 后 chat 再补一句"已 push 到远端"。用户可选择是否需要远端可见。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

## 非功能需求

### NFR-010 quote_parser 必须能区分内嵌代码块与 quote

`tools/quote_parser.py` 必须能区分内嵌代码块（``` ``` ```）中的 `>` 字符与真正的 quote。代码块内 `>` 不应被当作 quote 解析。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

### NFR-020 quote_parser 必须能在 specs/001-003 历史 spec 上不 crash

`tools/quote_parser.py` 在历史 spec（无 `### FR-XXX` 单元结构）上不能 crash，应正确降级为"无单元"判定。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

## 历史 spec 兼容性

历史 spec（001-specforge-v0.1, 002-specforge-v0.2, 003-init-adopt-mode-v0.3）使用 PR inline comment 流程，文档本身**不修改**。新流程（quote dialogue）从 spec 004 起适用。README §2.2 章节改写为 IDE-based 流程说明，旧流程作为"参见历史 spec 003"提及。

```yaml
testability: ✅
resolved: ✅
valid: ✅
```

## 排除项

- 不在本 spec 范围：PR Review API 的二次封装（`gh api reviews` 不在 Sage/Lex 工具链使用）
- 不在本 spec 范围：自动 commit 触发器（chat 通知由 Sage 主动发送，不靠 git hook）
- 不在本 spec 范围：可视化 spec review 工具（用户在任意 markdown IDE 中编辑即可）

## Lex 退出条件

- [ ] 所有 quote block 都 ✓ resolved
- [ ] 所有 FR/NFR 单元的 `yaml.resolved == ✅`
- [ ] `quote_parser --check-ready` 返回 exit 0
- [ ] `verify_issue_schema.py` L1-L8 全部通过
- [ ] 用户已明确确认 spec 锁定
