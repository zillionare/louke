
## 开始一个新的 release

在 opencode 中，确认当前的 Agent 是 Maestro 后，输入（以下为示例）：

```md
现在我们要开始这个项目的 UI 部分。story 已经在 v0.2-002-ui 下了。项目版本号是0.2
```

> [!note]
> v0.14 的 foundation 由 Runtime program 执行，不创建 foundation Agent session。
> 旧的 `lk agent scout` 只作为兼容脚本入口保留。

![](https://cdn.jsdelivr.net/gh/zillionare/imgbed2@main/images/2026/07/20260703140732.png)

<!-- 历史截图保留作版本记录；当前流程不再创建旧 foundation Agent。

![](https://cdn.jsdelivr.net/gh/zillionare/imgbed2@main/images/2026/07/20260703104723.png)

旧流程示例中，这些信息由 foundation Agent 收集；新流程使用 Runtime program。
-->

Runtime foundation program 完成确定性检查后，Maestro 只汇总结果并路由需求澄清。

![](https://cdn.jsdelivr.net/gh/zillionare/imgbed2@main/images/2026/07/20260703104947.png)

这是使用 LouKe 来做项目，可以放手让 AI 去干活的关键要点。你定义需求和验收标准，AI 来写代码满足这些需求，最后看代码的测试覆盖有没有达到要求。每一段测试代码都能反向追踪到一个个需求项。所有这些连环锁定。

关键项目信息由 Runtime 持久化；后续 semantic Agent 只消费绑定的 task manifest。
质量和回归检查同样由 Runtime program 执行，不创建旧 gate/reviewer session。

![](https://cdn.jsdelivr.net/gh/zillionare/imgbed2@main/images/2026/07/20260703105330.png)

> [!info]
> 基础检查是确定性的 Runtime gate；需要语义判断时才调度 canonical semantic Agent。

## Inline Discussion — 怎么跟 agent 多轮对话

当 spec 处于 M-SPEC / M-ARCH 阶段，agent 会用 inline-discussion 协议在 spec.md 里向你提问。**所有讨论留在 spec.md 内**，不刷 git chat。

### 3 个 example

**1. 简单问答**

```md
> **Sage [RESOLVED]:** FR-0001 密码加密用 bcrypt 还是 argon2?
>> **Aaron:** 用 argon2. Argon2id 在 2024 年仍是推荐方案。
```

> 含义：Sage 提问，**嵌套 `>>`** 是你的回复。**RESOLVED 由 Sage 标**（只有发起人）。

**2. 多方讨论（Agent ↔ Agent ↔ User）**

```md
> **Sage [RESOLVED]:** 是否有 rate limit?
>> **Lex:** 应该限流, 5 req/min.
>>> **Aaron:** 我反对, 内部 API 不需要.
```

> 含义：嵌套深度 3。`>>` = Lex 对 Sage 回复，`>>>` = Aaron 对 Lex 回复。状态只写在根评论上。

**3. 你发起新话题**

```md
> **Aaron [RESOLVED]:** 这个 API 需要支持 GraphQL 吗?
>> **Sage:** 暂不支持, v0.X 仅 REST.
```

工具固定输出上面的 canonical 写法（冒号在 `**` 内）。为了兼容人类输入，读取时也接受 `> **Aaron**: ...`、`> Aaron: ...` 及其 `[RESOLVED]` 形式。discussion 前后可以有普通 Markdown；只要 speaker 行在 fenced code block 之外，`lk discuss query` 就会识别它。`> Note: ...`、`> Warning: ...` 这类说明标签不会被当成讨论。

### 易错点清单

- ❌ **不要**省略 speaker tag 或冒号；推荐 canonical 形式为 `> **Sage:** ...`
- ❌ **不要**在嵌套回复上标 `[RESOLVED]`（仅根评论的 RESOLVED 有效）
- ❌ **不要**替他人在自己起的 thread 标 RESOLVED（仅发起人能标）
- ❌ **不要**在 chat 窗口写纯文字讨论（必须写进 spec.md）
- ✅ **要**用 `lk discuss query` 找你的会话断点（不自己 grep）
