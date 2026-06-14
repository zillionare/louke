# 需求澄清改用 Markdown Quote Block 对话 — Spec

- **Spec ID**: 004-quote-dialogue
- **创建日期**: 2026-06-14
- **状态**: 草稿（Sage Interview 进行中）

## 用户故事

| ID     | 故事                                                                                                                                    | 验收标准                                                                         | 优先级 |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ------ |
| US-001 | 作为 specforge 用户，我希望在本地 IDE 中打开 spec.md 直接编辑、用 quote block 标注我的回复，以便需求澄清不依赖 GitHub PR 权限           | AC-1: 用户能用文本编辑器修改 spec.md; AC-2: quote 块用 markdown `>` 语法         | P0     |
| US-002 | 作为 Sage，我需要在用户 push 之后通过 `git pull` + `git diff` 自动识别用户的修改，以便针对性追问                                        | AC-3: Sage 调用 `git diff origin/spec/{id}..HEAD -- specs/{id}/spec.md` 解析变更 | P0     |
| US-003 | 作为 specforge 用户，我希望在 review 整个 spec.md 时能发现 Agent 自己的记录错误，并直接在文档里改正，以便需求澄清不只是回答问题         | AC-4: 用户可增删改任何段落, 不仅限 quote block                                   | P0     |
| US-004 | 作为 specforge 用户，我希望 quote block 用 `[open]` / `✓ resolved` 等状态 marker 标注 Sage 的疑问，以便我自己 review 时知道哪里还有疑点 | AC-5: 0 个 `[open]` 时 Sage 进入 Lex 阶段                                        | P0     |
| US-005 | 作为 specforge 用户，我希望 quote block 嵌套深度表示追问链（`>` = Sage, `>>` = 我, `>>>` = Sage 追问），以便对话结构可视化              | AC-6: 嵌套深度 ≥ 3 在 spec 004 中实际使用                                        | P0     |

> **Aaron**： 请根据 story.md 重写此部分。特别是用户没有提出来要使用 git push。spec澄清完全可以就在本地工作区完成。
> **Aaron**: sage 在请用户 review 之前，需要将 story, spec 提交一次，如果用户修改原文（而不仅仅是增加评论），这样可以通过 git diff 来识别。

## 设计原则

### 为什么 quote dialogue 不在 chat 里

quote block 对话的**真正价值**不是"用 markdown 替代 PR 评论", 而是:

1. **用户面对完整文档而非孤立问题** — Agent 在记录 story 时可能根本性错误（漏需求、误解意图、错位优先级），用户必须看完整文档才能发现
2. **用户能改任何地方** — 不限于回答 Agent 问题, 可以重写整段、新增 FR、删除错的
3. **Diff 是 review 的核心信号** — `git diff` 暴露用户的修改, Agent 据此追问
4. **GitHub 权限不再是瓶颈** — 任何能 `git push` 的人都能用, 不需 GitHub 写权限

### chat 是补充, 不是主通道

chat 里 Agent 可以:
- 解释"我为什么加这个 FR"
- 提示用户"spec.md L42 有一个潜在歧义"
- 通知用户"Sage 已更新 spec.md, 请在 IDE 中 review"
- 询问元问题 (如"项目叫什么名字", "FR 编号从几开始")

但**澄清对话本身在 IDE 编辑的 spec.md 里**。

## 功能需求

> **锚点约定**: 每个 FR 单元前必须有显式 HTML 锚点 `<a id="fr-XXX"></a>` (小写、3 位零填充), 供 GitHub issue 反向链接。FR-016 起新编号。

<a id="fr-016"></a>
**FR-016**: spec.md 必须支持 markdown quote block 形式的对话, 嵌套深度表示追问链, 单 `>` 是 Sage 提问, `>>` 是用户回复, 任意方都可发起追问。quote block 必须在 spec.md 中段后追加, 紧跟被讨论的原文段落之后, 物理位置即引用。可测试性: ✅

> **Aaron**: 单'>'也可以是用户先提问。一段评论是谁的，关于取决于'>'后面接的用户名。

<a id="fr-017"></a>
**FR-017**: 每条 quote 结尾必须包含状态标记, 三个值:
- `✓ resolved` — 已闭环
- `[open]` — 待回复 (Sage 用此标记疑点, 用户 review 时会看到)
- `[blocked-by-N]` — 被 FR-N 阻塞

> **Aaron**: [open]标识没有必要。quote block 只要没有被✓ resolved标识，就是没有完成。避免用户开启的会话，他忘了加[open]状态标记的情况。
> **Aaron**: 此处应该给一个 markdown 的示例。

可测试性: ✅

<a id="fr-018"></a>
**FR-018**: Sage 必须能通过 `tools/quote_parser.py` 解析 spec.md, 返回:
1. 所有 `[open]` quote 列表 (用户 review 入口 + Sage 决策依据)
2. 对话统计 (总轮次、每方发言数)
3. 嵌套深度直方图
   
> **Aaron**: 嵌套深度直方图不必要。

可测试性: ✅

<a id="fr-019"></a>
**FR-019**: Sage 必须在用户 push 后自动识别变更, 通过:
- `git fetch origin`
- `git diff origin/spec/{id}..HEAD -- specs/{id}/spec.md`
- 解析 diff, 区分: (a) quote block 状态变更 (open→resolved); (b) 新增 quote; (c) 原文段落增删改

> **Aaron**: 用户完成修改后，回到对话，提示 Agent 进行下一步。

可测试性: ✅

<a id="fr-020"></a>
**FR-020**: 当 `git diff` 显示用户修改了原文段落（不是 quote block）时, Sage 必须能识别这是"用户更正 Agent 记录错误"而非"用户回答 quote 问题", 据此调整后续追问策略（例如减少对已修正段落的追问、增补由用户修正引发的下游疑问）。可测试性: ✅

<a id="fr-021"></a>
**FR-021**: Sage.md §2.2 必须改写: 移除 `gh api pulls/.../comments` / `gh pr create` / `gh pr merge` 调用; 改为 IDE-based 流程, 通过 `git push/pull` + `tools/quote_parser.py` + 直接编辑 spec.md。可测试性: ✅

<a id="fr-022"></a>
**FR-022**: Lex.md 必须改写: 不使用 `gh api reviews`; 改为读 spec.md 中 quote 状态 (所有 `[open]` 为 0 时 Approve) + 在 spec.md 中用 quote 形式留 Lex 审查意见。可测试性: ✅

<a id="fr-023"></a>
**FR-023**: README §2.2 章节必须改写, 演示 IDE-based 流程而非 PR inline comment。可测试性: ✅

<a id="fr-024"></a>
**FR-024**: 完整流程必须支持 quote 嵌套深度 ≥ 3 (追问链)。可测试性: ✅

<a id="fr-025"></a>
**FR-025**: quote 解析器必须能区分:
- 内嵌代码块中的 `>` (不应被当成 quote)
- 用户在 commit message 里的 quote (不污染 spec.md 解析)

可测试性: ✅

<a id="fr-026"></a>
**FR-026**: spec 流程结束时, 所有 `[open]` 必须为 0; 否则 Lex 拒绝 Approve 并由 Sage 继续追问。可测试性: ✅

<a id="fr-027"></a>
**FR-027**: Sage 在 chat 中可以辅助引导, 但 chat 不是 quote dialogue 的载体。chat 用途限于: 通知用户 "spec.md 已更新, 请在 IDE 中 review"; 解释 Agent 设计意图; 询问元问题 (如"项目叫什么名字")。可测试性: ✅

<a id="fr-028"></a>
**FR-028**: Sage 启动时必须先检查上游 Scout 产物 `specs/{spec-id}/story.md`:
- story.md 存在 → 作为 spec 的设计源
- story.md 不存在但 GitHub 有匹配 Issue (label=Story 或 spec-id tag) → Issue body 作为设计源
- 两者都不存在 → Sage 拒绝启动, 要求用户先走 Scout 流程 (或由 Sage 兼任 Scout)

可测试性: ✅

<a id="fr-029"></a>
**FR-029**: Scout.md 必须明确输出契约: 输出 `specs/{spec-id}/story.md` (含 story, 版本号, repo, project) + 把用户在会话中提供的一句话 PRD 扩写为结构化 story.md。Warden (peer 检查) 验证 story.md 完整性后才允许 Sage 启动。可测试性: ✅

## 非功能需求

| ID      | 需求                                                            | 指标                                                                   |
| ------- | --------------------------------------------------------------- | ---------------------------------------------------------------------- |
| NFR-001 | quote_parser.py 用 Python stdlib (无第三方包)                   | 0 deps                                                                 |
| NFR-002 | bats 测试新增 case 数                                           | ≥ 10 (覆盖解析、状态检测、嵌套深度、跳过代码块等)                      |
| NFR-003 | Sage.md 重写后总行数                                            | ≤ 之前 + 50 行                                                         |
| NFR-004 | quote 对话记录在 git 历史                                       | git log --follow 可定位                                                |
| NFR-005 | spec 004 流程本身必须用 IDE-based quote dialogue 走完 (dogfood) | spec/004 分支 commit history 含 ≥ 3 次"用户 push 修改 + Sage 拉取"轮次 |

## Sage Interview (in-document quote dialogue)

下面是本 spec 自身的 Sage Interview, 演示新流程。**用户在 IDE 中直接编辑本段**。

### 用户故事澄清 (US-002 / US-003)

> **Sage:** US-002 提到"用户 push 之后通过 git diff 自动识别", US-003 说"用户能改任何地方"。但如果用户改了 spec.md 中跟 quote 无关的段落, Sage 怎么知道这是"回答 quote"还是"重写错误"?

> > **Sage:** 我建议分两类处理: (a) 用户改 quote block (状态变更 / 新增 quote) → 视作对 quote 的回复, Sage 据此调整; (b) 用户改原文段落 (US/FR/AC 等) → 视作"用户更正 Agent 记录", Sage 不追问已修正段落, 但可能追问"这次修正是否引发下游 FR 调整?"。区分方法: 用 `git diff` 中是否触及 quote 行判断。
> >
> >> **Sage:** (追问) 那么 chat 中是否需要 Sage 主动告知用户"我看到你改了 L42 段落的 AC-2, 是要顺便更新 AC-3 吗?", 还是静默接受用户的修改、不做引导?
> >>
> >>> **[open]** Aaron, please decide: (1) 用户改原文段落后, Sage 应主动引导下游调整 (proactive) 还是静默接受 (silent)? (2) 如果 proactive, 引导是放 chat 里还是放 spec.md 的 quote block 里?
> >>>> **Aaron** 我已对 US-002提出质疑。待该问题决定后再讨论此问题，有可能就不存在了。

### 与 PR 流程的关系 (跨 spec 影响)

> **Sage:** spec 003 的 spec.md / acceptance.md / test-plan.md 中所有"git push 触发 PR Review"的描述现在过时了。要不要追加 fix commit 把过时描述换成 quote 流程描述, 还是接受历史描述"过时"?
>
> > **Sage:** 历史 spec 是 immutable 历史记录, 不应回改。可以在 README 加一段"历史说明"指向本 spec (004) 作为 supersede, 类似 ADR 的 Superseded 关系。
> >
> >> **Sage:** 但 README §2.2 是流程总入口, 不写过时流程等于遗忘。所以 README §2.2 整段改写为 IDE 流程, 旧的 PR 流程作为"参见历史 spec 001-003"附录, 不删除。
> >>
> >>> **[open]** Aaron, please decide: (1) 历史 spec 是否回改? (2) README §2.2 旧 PR 流程段是删除、保留、还是作为附录?

### chat 引导的边界 (FR-027)

> **Sage:** FR-027 限定 chat 用途为"通知用户 review / 解释设计意图 / 询问元问题"。但 spec 流程中, Sage 经常需要问"项目叫什么 / FR 编号从几开始 / 是否合并到现有 spec"等元问题。这些走 chat 还是 spec.md?
>
> > **Sage:** 我倾向**元问题走 chat** (快速、不进 spec), **内容澄清走 spec.md quote** (持久、可追溯)。区分依据: 答案是否影响 spec.md 内容。如果回答后会改 spec.md, 必须走 spec.md quote; 如果回答后只影响 Agent 工作流, 走 chat。
> >
> >> **Sage:** (补充) 项目名 / FR 起点等元问题其实**也会影响 spec.md** (要写进 frontmatter 或开头), 所以严格按规则也应该走 spec.md。但用户体验上, 每次启动都要先开 IDE 编辑 spec.md 回答元问题, 太重。
> >>
> >>> **[open]** Aaron, please decide: 元问题 (项目名、FR 起点等) 走 chat 还是 spec.md? 如果走 chat, Sage 是不是要等用户 chat 回复后再初始化 spec.md?

### 上游 Scout 契约 (Sage 启动条件)

> **Sage:** 我刚意识到 spec 004 漏掉了上游 Scout→Sage 的契约。当前 Sage.md Step 0 假设 `prd.md` 存在, 但 Scout 的实际输出是 `story.md` (Scout.md 第 95 行: 写入 `specs/project-info.md` 等状态文件)。语义错位: Scout 写的是"项目元信息", Sage 假设有"PRD"。这两者不是一回事。
>
> > **Sage:** 提议新增 FR-028 (Sage 启动时读 `story.md` 或 GitHub Issue, 否则拒绝) 和 FR-029 (Scout 必须输出 `story.md`, Warden 验证)。这样 Scout→Sage 的契约就显式了。
> >
> >> **Sage:** (追问) GitHub Issue 作为设计源这一点, 是 specforge 现有 §1 双源设计 (spec.md ↔ Issue) 的延伸。我们是不是要把"任意上游产物都可以是 Issue"这一原则**正式写入 spec 004** 作为 NFR? 或者保持隐式 (只在 FR-028 里隐含)?
> >>
> >>> **[open]** Aaron, please decide: (1) 我新增的 FR-028 / FR-029 描述准确吗? (2) "上游产物可以是 Issue"这一原则要不要单独写成 NFR, 还是隐式包含在 FR-028 里即可?

### [open] quote 汇总

当前 spec.md 仍 open 的问题:

1. 用户改原文段落后, Sage 主动引导 vs 静默接受?
2. 历史 spec 是否回改? README §2.2 旧 PR 流程段处置?
3. 元问题走 chat 还是 spec.md?
4. FR-028/FR-029 描述准确吗? Issue 双源原则是否单独写 NFR?

## 流程示意（参考）

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. Sage 在 spec.md 中追加 quote block (用 [open] 标疑点)         │
│    $ git add specs/004/spec.md                                    │
│    $ git commit -m "spec: 004-quote-dialogue — initial draft..." │
│    $ git push                                                       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 2. 用户在 IDE 中打开 spec.md, 完整 review                          │
│    - 看 quote block 回答 Sage 的疑点                               │
│    - 同时检查 Agent 写错的地方 (FR 描述、AC 标准、漏需求等)         │
│    - 直接编辑: 改 quote block 状态、改原文段落、新增/删除 FR        │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 3. 用户 commit + push                                                │
│    $ git add specs/004/spec.md                                     │
│    $ git commit -m "spec: 004 — resolve Q1, fix FR-018 typo"    │
│    $ git push                                                       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 4. Sage 自动检测: git pull + git diff 解析变更                      │
│    - 分类: quote 状态变更 / 原文段变更 / 新增 quote                 │
│    - 据此调整下一步                                                  │
│    - 如果仍有 [open], 回到步骤 1                                   │
│    - 如果所有 [open] 闭环, 进入 Lex 阶段                          │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 5. Lex 在 spec.md 中追加 quote (Lex 的审查意见)                    │
│    - 用 ✓ resolved 标 "accept" / [open] 标 "needs more"          │
│    - 用户在 IDE 中回复 (Lex quote + 原 quote 区分)                 │
│    - 全部 ✓ resolved → Sage 进入 issue 创建阶段                   │
└──────────────────────────────────────────────────────────────────┘
```

## Lex 审核结果

- [ ] 所有 FR 可断言
- [ ] 所有 FR 有锚点
- [ ] 所有 `[open]` quote 已闭环
- [ ] spec 自身用 IDE 流程走完 (NFR-005)

## 附录: 编号说明

FR-016 起新编号。前置编号占用:
- FR-001~007: specforge v0.2 模型配置 (历史)
- FR-008~015: spec 003-init-adopt-mode (v0.3)
- FR-016+: 本 spec
