
1. 通过 web page 来操作 opencode 运行实例，实现发送消息、回显（含状态回显）、命令（models, agent 等）
2. 通过 louke server 来实现工作流，不再使用 maestro 协调工作流（但保留角色作为辅助），将可以工具化的 Agent 集成为 louke server的一部分，从而取消这些 Agent.
3. maestro 指令强化：对用户输入的每一条指令，先判断意图（story, spec change, bug fix），再决定操作 （进入新开发|存 backlog|spec change|fix）
4. wiki 的目标是：
    1.  从众多的 specs 文档中，维护反映最新且最全状态 story, spec, test plan, architecture, interfaces（各一份）；重新格式化（不使用FR-XXXX 的编号），而是文档标题序号；但每一个story/spec 事实都要链接回原始的 story/spec/test plan 等文档。
    2.  记录各类 story, spec 的技术决定：那些在 review 时被提出来 argue，最终被裁定的结果及原因
    3.  首页由 readme 和指责 story, spec等设计文档的链接组成
    4.  包含 FAQ，项目信息（版本、分支、github project、版本开发起、止时间）等
5. 重新规划 .louke 的目录，以保存：louke server 相关文件、code review 输出文件、会话保存文件、wik各类文件等
6. FR/NFR状态表由表格改为 task list，这样可以在 web page 上通过点击进行切换，即
   ```md
   - [x] 有效需求
   - [x] 可测性
   - [x] 可测试性
   ```
   如果有可能，则一行显示：`[x] 有效需求 [x] 可测性 [x] 可测试性`。但要求一行显示时，仍能按 `markdown tasks`来显示并有可操作性（通过点击能 toggle 状态）
7.  新建 story 到本地 backlog(list)，此后可以从中挑选成为一个新的 story进入开发
8.  查看工作区文件、变更文件及文件 diff
9.  显示design document, readme, docs/*.md 等
