
## 开始一个新的 release

在 opencode 中，确认当前的 Agent 是 Maestro 后，输入（以下为示例）：

```md
现在我们要开始这个项目的 UI 部分。story 已经在 v0.2-002-ui 下了。项目版本号是0.2
```

> [!tip]
> Scout 默认绑定的模型是 opencode/deepseek-v4-flash-free。它是免费使用的。因为是免费，所以，它的 context window 会小一些。当你从 Maestro 切换过来时，有可能会遇到一次下下文压缩。所以，你也可以考虑直接使用 Maestro 所用的模型，以避免丢失上下文。

Maestro 会启动子代理 Scout:

![](https://cdn.jsdelivr.net/gh/zillionare/imgbed2@main/images/2026/07/20260703140732.png)

<!--Scout 会对当前的工作区进行扫描，并给出一个项目概览：

![](https://cdn.jsdelivr.net/gh/zillionare/imgbed2@main/images/2026/07/20260703104723.png)

示例中，这些信息已经完整了。否则，Scout 会向你询问相关信息，并把 project 等创建起来。
-->

Scout 启动之后，会在后台处理一些工作，然后会放出灵魂之问，我们如何定义这个需求被完成了？

![](https://cdn.jsdelivr.net/gh/zillionare/imgbed2@main/images/2026/07/20260703104947.png)

这是使用 LouKe 来做项目，可以放手让 AI 去干活的关键要点。你定义需求和验收标准，AI 来写代码满足这些需求，最后看代码的测试覆盖有没有达到要求。每一段测试代码都能反向追踪到一个个需求项。所有这些连环锁定。

最后，Scout 把关键项目信息写入到 project-info.md 中，后面的流程中，其它 Agent 将使用这些关键信息。

然后它会给出报告，并提示唤起 Warden 对它的工作进行复核。

![](https://cdn.jsdelivr.net/gh/zillionare/imgbed2@main/images/2026/07/20260703105330.png)

> [!info]
> 越是基础、奠基性的工作，越是不能出错。所以，即使是这么简单的任务，我们也要专门配置一个 Agent 来进行复核。



