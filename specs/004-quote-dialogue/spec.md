# 需求澄清改用 Markdown Quote Block 对话 — Spec

- **Spec ID**: 004-quote-dialogue
- **创建日期**: 2026-06-14
- **状态**: 草稿（Sage Interview 进行中）

## 用户故事

| ID | 故事 | 验收标准 | 优先级 |
|----|------|---------|--------|
| US-001 | 作为 specforge 用户，我希望 Sage 在 spec.md 中用 markdown quote block 提问、我用 quote 回复，以便需求澄清不需要开 PR / 不需要 GitHub 写权限 | AC-1: spec.md 含 `> **Sage:**` 块; AC-2: 用户用 `>> **Name:**` 回复 | P0 |
| US-002 | 作为 Sage，我需要能机读地判定 spec.md 中的 quote 对话是否所有问题都已闭环，以便决定是否进入 Lex 阶段 | AC-3: 0 个 `[open]` quote 时 Sage 才能 lock spec | P0 |
| US-003 | 作为 specforge 用户，我希望 quote 对话保留在 git 历史中以便追溯，无需查 PR 评论 | AC-4: 每次对话 commit 进 git; AC-5: `git blame` 可定位 | P0 |

## 功能需求

> **锚点约定**: 每个 FR 单元前必须有显式 HTML 锚点 `<a id="fr-XXX"></a>` (小写、3 位零填充), 供 GitHub issue 反向链接。FR-016 起新编号, 避开 v0.3 init-adopt 的 FR-008~015 与 model-config 的 FR-001~007。

<a id="fr-016"></a>
**FR-016**: spec.md 必须支持 markdown quote block 形式的对话, 嵌套深度表示对话线程深度, 单 `>` 是 Sage 提问, `>>` 是用户回复, 任意方都可以发起追问。可测试性: ✅

<a id="fr-017"></a>
**FR-017**: 每条 quote 结尾必须包含状态标记, 三个值:
- `✓ resolved` — 已闭环
- `[open]` — 待回复 (Sage 用此标记问题)
- `[blocked-by-N]` — 被其他 FR 阻塞, N 是阻塞它的 FR 编号

可测试性: ✅

<a id="fr-018"></a>
**FR-018**: Sage 必须能通过 `tools/quote_parser.py` 解析 spec.md, 返回三类信息:
1. 所有 `[open]` quote 列表 (Sage 据此决定是否继续追问)
2. 对话统计 (总轮次、每方发言数)
3. 嵌套深度直方图

可测试性: ✅

<a id="fr-019"></a>
**FR-019**: Sage.md 必须重写 §2.2 章节: 移除所有 `gh api pulls/{n}/comments` / `gh pr create` / `gh pr merge` 调用; 改为使用 `tools/quote_parser.py` + 直接编辑 spec.md 并 push 到 spec 分支。可测试性: ✅

<a id="fr-020"></a>
**FR-020**: Lex.md 必须改写: 不再使用 `gh api reviews` 的 Approve/Request changes, 改为读 spec.md 中 quote 状态 (所有 `[open]` 为 0 时 Approve) + 在 spec.md 中用 quote 形式留言 Lex 审查意见。可测试性: ✅

<a id="fr-021"></a>
**FR-021**: README §2.2 章节必须改写, 用 quote block 演示替代 PR inline comment 示例。可测试性: ✅

<a id="fr-022"></a>
**FR-022**: 完整流程必须支持 quote 嵌套深度 ≥ 3 (即追问链: Sage 提问 → 用户回复 → Sage 追问 → 用户再回复)。[待澄清-1] 可测试性: ✅

<a id="fr-023"></a>
**FR-023**: quote 解析器必须能区分:
- 内嵌代码块中的 `>` (不应被当成 quote)
- 用户在 commit message 里写的 quote (不应污染解析)
- HTML 标签中的 quote (不应被当成 quote)

可测试性: ✅

<a id="fr-024"></a>
**FR-024**: spec 流程结束时, 所有 `[open]` 必须为 0; 否则 Lex 拒绝 Approve 并由 Sage 继续追问。可测试性: ✅

## 非功能需求

| ID | 需求 | 指标 |
|----|------|------|
| NFR-001 | quote_parser.py 用 Python stdlib (无第三方包) | 0 deps |
| NFR-002 | bats 测试新增 case 数 | ≥ 10 (覆盖解析、状态检测、嵌套深度、跳过代码块等) |
| NFR-003 | Sage.md 重写后总行数 | ≤ 之前 + 50 行 (不膨胀) |
| NFR-004 | quote 对话记录在 git 历史中 | git log --follow 可定位 |
| NFR-005 | 完整 spec 004 流程本身必须用 quote dialogue 走完 (dogfood) | spec/004 分支的 commit history 含 ≥ 3 次 quote 轮次 |

## Sage Interview (in-document quote dialogue)

下面是本 spec 自身的 Sage Interview, 演示新流程的 quote 格式。**用户 (Aaron) 在 chat 里用 `>> **Aaron:**` 回复即可, 不需要 push 到 git**。

### 用户故事 (US-002 补充)

> **Sage:** US-002 提到"机读地判定 quote 对话是否所有问题都已闭环", 这里的"判定时机"是什么? 是每轮 quote 后增量检查, 还是 spec 完成后一次性扫描?
>
> > **Sage:** 我倾向**一次性扫描** (即 Lex 阶段开始前扫一次 spec.md), 因为增量检查会让 Sage 反复中断工作流去做 LLM 解析。一次性扫描更简单, 但代价是用户能在 spec.md 中偷偷留 `[open]` 而 Sage 看不见 (因为 Lex 才会扫)。
> >
> >> **Sage:** (追问) 折中方案: Sage 在每完成一轮 quote push 前, 自己先扫一遍 `[open]` 状态 (因为 Sage 自己写的 quote, 不需要 LLM 解析, 简单的 grep 就够), 防止遗留 open 问题。这样日常流程是简单的 (grep 自检), Lex 阶段再做最终保险扫描。
> >>> **Sage:** 你倾向哪种?
> >>>> **[open]** Aaron, please answer (1) 增量扫描 vs 一次性扫描 vs 折中方案, (2) 是否还需要其他状态 (如 `[wontfix]` `[superseded]`)?

### 流程集成 (FR-019 / FR-020)

> **Sage:** FR-019 说"重写 Sage.md §2.2 章节", FR-020 说"Lex 不再使用 gh api reviews"。但 specforge 的 stage 编排 (Maestro) 可能仍要触发 Lex, 那 Lex 怎么知道 spec.md 已经 ready?
>
> > **Sage:** Maestro 当前的触发逻辑 (在 agents/Maestro.md 里) 是基于事件 (PR merged) 或文件名约定。如果改用 quote 流程, 需要新的触发信号: **spec.md 中 0 个 `[open]` quote**。
> >
> >> **Sage:** 提议 Maestro 调用 `tools/quote_parser.py spec.md --check-ready` 作为 gate。但这把 quote_parser 从 Sage 内部工具提升到 Maestro 调用, 增加耦合。
> >>
> >>> **Sage:** (折中) 把 `check-ready` 作为 quote_parser 的一个子命令, 同时供 Lex 和 Maestro 调用。这样 Sage 自己仍然只用更高层的接口。
> >>>> **[open]** Aaron, please confirm: (1) 是否同意把 quote_parser 的 `--check-ready` 暴露给 Maestro 作为 gate? (2) FR-019/FR-020 是否需要新增 FR 描述 Maestro 适配?

### PR 流程 deprecation (跨 spec 影响)

> **Sage:** spec 003 的 spec.md / acceptance.md / test-plan.md 中所有"git push 触发 PR Review"的描述现在过时了。要不要在 spec 003 里追加一个 fix commit 把过时描述换成 quote 流程描述, 还是接受历史描述"过时"?
>
> > **Sage:** 历史 spec 是 immutable 历史记录, 不应回改。可以在 README 加一段"历史说明"指向本 spec (004) 作为 supersede, 类似 ADR 的 Superseded 关系。
> >
> >> **Sage:** 但 README §2.2 是流程总入口, 不写过时流程等于遗忘。所以 README §2.2 整段改写为 quote 流程, 旧的 PR 流程作为"参见历史 spec 001-003"附录, 不删除。
> >>
> >>> **[open]** Aaron, please decide: (1) 历史 spec 是否回改? (2) README §2.2 旧 PR 流程段是删除、保留、还是作为附录?

### [open] quote 汇总

当前 spec.md 仍 open 的问题:

1. (来自 US-002) Sage 自检 vs Lex 一次性扫描 vs 折中
2. (来自 FR-019/FR-020) Maestro 是否也调用 quote_parser 作 gate, 是否新增 FR 描述
3. (来自 PR deprecation) 历史 spec 是否回改 + README §2.2 旧 PR 流程段的处置

## Lex 审核结果

- [ ] 所有 FR 可断言
- [ ] 所有 FR 有锚点
- [ ] 所有 `[open]` quote 已闭环 (Sage 不检查, Lex 才检查)
- [ ] spec 自身用 quote 流程走完 (NFR-005)

## 附录: 编号说明

FR-016 起新编号。前置编号占用:
- FR-001~007: specforge v0.2 模型配置 (历史)
- FR-008~015: spec 003-init-adopt-mode (v0.3)
- FR-016+: 本 spec