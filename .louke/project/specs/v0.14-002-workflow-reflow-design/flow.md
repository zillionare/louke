# v0.14-002-workflow-reflow-design 速览

## M-DESIGN

人类批准 M-SPEC 之后，就进入 M-DESIGN 阶段

1. **Runtime** 调用 **Archer** 以进行 test plan, architecture 和 interface 文档设计。
2. **Runtime** 开启文档界面上的对话小窗，允许**Human** 与**Archer**就生成的文档进行对话。
3. **Archer** 完成三份文档的输出，返回给**Runtime**
4. **Runtime** 启动**Prism**，对**Archer**的三份文件进行评审，将评审结果返回给**Runtime**
5. **Runtime** 根据评审结果，决定**Archer**是否要响应。如果评审结果通过，则退出 M-DESIGN
6. 如果**Archer**需要响应，则开启新一轮 review。

## M-LOCK

1. **Runtime** 重定向页面到 active project 页面，指针指向 M-LOCK 阶段，显示批准按钮
2. **Human** 人类批准后，进入 M-IMPL 阶段。如果人类不批准，可以回拨流程指针。此时需要提供原因。
