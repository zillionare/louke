# v0.14-002-workflow-reflow-design 速览

## M-DESIGN

Human 在 M-REQ-APPROVAL 批准当前需求基线后，进入 M-DESIGN 阶段。

1. **Runtime** 调用 **Archer** 以进行 test plan、architecture、interface 及宿主项目 machine contracts 设计。machine contracts 至少覆盖 integration/e2e、GitHub CI、pre-commit、release version、build/artifact 和发布恢复。
2. **Runtime** 开启文档界面上的对话小窗，允许 **Human** 与 **Archer** 就生成的文档进行对话；Human 是可选 reviewer，允许缺席，其建议不是技术批准门禁。
3. **Archer** 完成三份文档及 machine contracts，返回给 **Runtime**。其中 pre-commit contract 必须基于宿主项目真实工具链，定义应保留/合并的既有 hooks、快速格式/lint/static/secret/trace checks、可在合理时间内运行的可选单元测试及失败语义；pre-commit 只负责正式 commit 的快速本地 gate，不承担 Red 证明或最终质量门禁。
4. **Runtime** 启动 **Prism**，对 **Archer** 的三份文档和全部 machine contracts 进行评审，将评审结果返回给 **Runtime**。
5. **Runtime** 根据评审结果，决定 **Archer** 是否要响应。当前 revision 的程序校验与 Prism 评审通过后退出 M-DESIGN，不等待 Human 批准；Runtime 后续按该 contract 安装、更新和回读 pre-commit，不由 Archer 或 Devon 执行安装副作用。
6. 如果**Archer**需要响应，则开启新一轮 review。
7. M-DESIGN 之后不再设置第二个 M-LOCK。Runtime 将通过评审和程序校验的当前设计 revision 作为实现基线，进入 M-IMPL；后续 Agent 发现有效设计问题时，可以按定义化流程返回 M-DESIGN 并形成新 revision。
