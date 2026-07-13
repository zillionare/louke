# v0.12-001-programmatic-workflow-runtime Review (2026-07-13)

> **范围**: spec.md (708 行) + story.md (108 行) + acceptance.md (729 行) + exploration/ 目录
>
> **方法**: 覆盖度 (story→spec↔AC) → 一致性 (三文档互证) → 可测性 (AC 边界) → 新发现问题

---

## 第一部分: 整体质量评估

| 维度            | 评分  | 说明                                                                           |
| --------------- | ----- | ------------------------------------------------------------------------------ |
| 结构完整性      | ★★★★★ | 24 FR + 5 NFR, 分 6 组 (Review Map), 18 条 US, 12 个 scenario                  |
| story→spec 覆盖 | ★★★★★ | story 的 17 条期望结果全部有对应 FR；16 个场景有 12 个对应 scenario (4 个合并) |
| spec→AC 覆盖    | ★★★★★ | 29 条 FR/NFR 各有 AC, 共 127 条 AC, 全部 Given-When-Then 格式                  |
| 可测性          | ★★★★☆ | 多数 AC 可公开接口验证, 少数需特殊断言 (见 §第三部分)                          |
| Decided 状态    | ★★★☆☆ | 全部 29 条为 ⚠️ (待逐项评审), 但 Clarification Log 中部分已实质决定             |

**结论**: 这是一份高质量的 spec——结构严谨、覆盖完整、AC 规范。主要改进空间在于 Decided 状态的精细化管理和个别边界场景的补充。

---

## 第二部分: story↔spec↔AC 覆盖度映射

### 2.1 story 期望结果 → spec FR 映射

| #   | story 期望结果                     | 对应 FR          | 覆盖 |
| --- | ---------------------------------- | ---------------- | ---- |
| 1   | Louke 程序成为工作流状态唯一控制者 | FR-0001, FR-0101 | ✓    |
| 2   | 工作流步骤/转移由版本化定义固定    | FR-0001, FR-1701 | ✓    |
| 3   | 确定性工作由程序执行               | FR-0301, FR-1601 | ✓    |
| 4   | M-FOUNDATION 自动检查幂等前置条件  | FR-0401          | ✓    |
| 5   | M-LOCK 持久化人类门禁              | FR-0501, FR-0901 | ✓    |
| 6   | Agent 无法跳过或复用过期批准       | FR-0501, FR-1601 | ✓    |
| 7   | 需求审批后开始设计                 | FR-0801          | ✓    |
| 8   | M-LOCK 后开始开发                  | FR-0901          | ✓    |
| 9   | 重启后从原步骤恢复                 | FR-0201          | ✓    |
| 10  | Web 项目创建/历史/当前             | FR-1001, FR-1101 | ✓    |
| 11  | Web 工作流图与位置                 | FR-1201          | ✓    |
| 12  | Web Agent-model 绑定与拖拽         | FR-1301          | ✓    |
| 13  | 真实 OpenCode 生命周期             | FR-1401          | ✓    |
| 14  | 每步定制 context manifest          | FR-1501          | ✓    |
| 15  | 程序/Agent 职责分离                | FR-1601          | ✓    |
| 16  | 初始化/readiness                   | FR-1801          | ✓    |
| 17  | 可操作 Project 详情                | FR-1901          | ✓    |
| 18  | 失败/取消/归档受控路径             | FR-2001          | ✓    |
| 19  | new_feature/bug_fix 完整 workflow  | FR-2101          | ✓    |
| 20  | FR→AC→task→code→test 证据闭环      | FR-2201          | ✓    |
| 21  | 旧 workspace 显式采用              | FR-2301          | ✓    |

**结论**: 21/21 条期望结果 100% 覆盖。

### 2.2 story 场景 → spec scenario 映射

| story 场景                 | spec scenario                 | 覆盖              |
| -------------------------- | ----------------------------- | ----------------- |
| 场景一: 启动工作流         | scenario-0001                 | ✓                 |
| 场景二: Foundation 已满足  | scenario-0101                 | ✓                 |
| 场景三: Foundation 可修复  | scenario-0101 (repaired)      | ✓                 |
| 场景四: 批准需求后开始设计 | scenario-0401                 | ✓                 |
| 场景五: 等待 M-LOCK        | scenario-0201                 | ✓                 |
| 场景六: 批准后规格变化     | — (隐含在 FR-0501 AC-5)       | ⚠ 无独立 scenario |
| 场景七: 进程中断与恢复     | scenario-0301                 | ✓                 |
| 场景八: Web 创建项目       | scenario-0501                 | ✓                 |
| 场景九: 查看工作流         | scenario-0501 / scenario-0901 | ✓                 |
| 场景十: 调整 Agent model   | scenario-0501 / scenario-1001 | ✓                 |
| 场景十一: 语义 Agent 任务  | scenario-0601                 | ✓                 |
| 场景十二: 第一次使用 Louke | scenario-0701                 | ✓                 |
| 场景十三: Project 详情操作 | scenario-0801                 | ✓                 |
| 场景十四: 失败/取消/恢复   | scenario-0901                 | ✓                 |
| 场景十五: 完整 workflow    | scenario-1001 / scenario-1101 | ✓                 |
| 场景十六: 采用旧 workspace | — (隐含在 FR-2301)            | ⚠ 无独立 scenario |

**结论**: 16 个故事场景有 12 个独立 scenario, 4 个通过现有 scenario 或 FR 隐含覆盖。

**发现 1 (P2)**: story 场景六 (批准后规格变化导致旧批准失效) 和场景十六 (采用旧 workspace) 在 spec 中无独立 scenario。虽然 FR 有覆盖，但作为使用场景独立列出有助于理解。

---

## 第三部分: AC 可测性分析

### 3.1 可测性良好的 AC (示例)

| FR       | AC             | 可测性 | 说明                                             |
| -------- | -------------- | ------ | ------------------------------------------------ |
| FR-0001  | AC-1           | ★★★★★  | 未知步骤/悬空转移 → validation error, 可单元测试 |
| FR-0101  | AC-1/AC-3      | ★★★★★  | 并发冲突检测, revision 校验                      |
| FR-0201  | AC-1/AC-2      | ★★★★★  | 重启恢复, 事务幂等                               |
| FR-0501  | AC-1/AC-2/AC-6 | ★★★★★  | gate 等待/批准/拒绝, 公开 API 可验证             |
| FR-1101  | AC-1/AC-3/AC-4 | ★★★★★  | 表单验证/创建/错误处理                           |
| FR-1201  | AC-1/AC-4      | ★★★★★  | graph 渲染/历史只读                              |
| FR-2101  | AC-1/AC-2/AC-6 | ★★★★★  | workflow 完整性/完成判定                         |
| FR-2301  | AC-1/AC-4      | ★★★★★  | 迁移预览/旧数据不自动恢复                        |
| NFR-0001 | AC-1/AC-2      | ★★★★★  | 原子性/崩溃安全                                  |
| NFR-0101 | AC-1           | ★★★★★  | 并发一致性                                       |

### 3.2 可测性需关注的 AC (部分)

| FR       | AC   | 问题                                                                          | 建议                                                                              |
| -------- | ---- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| FR-1501  | AC-2 | "不继承 Maestro 主聊天中的隐式工作流状态" — 需验证 session context 的来源组成 | 建议补充验证方法: 通过对比"有/无 Maestro 对话"两种情况下 task manifest 内容       |
| FR-1801  | AC-2 | "已就绪资源不重复创建" — 需验证幂等性                                         | 建议明确: 重复初始化时, 外部 adapter 观察到每种资源仅创建一次 (类似 FR-0401 AC-2) |
| NFR-0201 | AC-3 | "statement coverage ≥ 95%" — 需 CI 工具测量                                   | 已明确, 可接受                                                                    |

**结论**: 绝大多数 AC 可被测试断言。少数需补充验证方法的 AC 建议补充。

---

## 第四部分: 新发现的问题

### P1-1: Decided 状态全部为 ⚠️ 但部分已实质决定

**位置**: spec.md 全部 29 条 FR/NFR

Clarification Log 中已记录多处用户确认:
- 用户要求按端到端可用产品补全隐含需求 → 新增 FR-1801~FR-2301 + NFR-0301/NFR-0401
- 首版 human gate 接受 loopback 本地 Web 会话身份 → NFR-0401
- 严格遵循 Louke v0.10 顺序 → FR-0801/FR-0901

**问题**: 全部标记为 ⚠️ (待逐项评审) 虽然安全，但可能误导后续 Agent/实施者，让他们以为已确认的决策也需要重新讨论。

**建议**: 将已获用户确认的 FR 标记为 ✅，将仍有争议的标记为 ⚠️。例如：
- FR-0001~FR-0700 (程序控制面核心): ✅ (方向已原则同意)
- FR-0801/FR-0901 (两次门禁): ✅ (Clarification Log 已确认)
- FR-1001~FR-1300 (Web UI): ⚠️ (首版细节待评审)
- FR-1801~FR-2301 (端到端能力): ⚠️ (新增需求待确认)
- NFR-0001/NFR-0101/NFR-0401: ✅ (基础安全/并发/保密)
- NFR-0301 (产品级 E2E): ⚠️ (E2E 范围待确认)

### P2-1: story 场景六和场景十六无独立 spec scenario

**位置**: story.md "场景六" (批准后规格变化) + "场景十六" (采用旧 workspace) vs spec.md 12 个 scenario

**分析**:
- 场景六 (批准后规格变化 → 旧批准失效) 是核心安全机制，在 FR-0501 AC-5 中有覆盖，但作为 scenario 独立列出有助于理解 "stale detection" 行为。
- 场景十六 (采用旧 workspace) 涉及复杂的迁移流程，FR-2301 有完整覆盖，但 scenario 缺失使实施者难以直观理解用户旅程。

**建议**: 新增 scenario-0601 (批准后规格变化) 和 scenario-1201 (采用旧 workspace) 到 spec.md。

### P2-2: FR-2101 (new_feature/bug_fix workflow) 缺少 graph 可视化

**位置**: FR-2101 + AC-FR2101-01~AC-FR2101-06

**分析**: 两个 workflow 的 graph 非常复杂：
- new_feature: requirements author/review → requirements approval → test-plan → architecture/interfaces → M-LOCK → implementation → tests → E2E → security/release → milestone close → history
- bug_fix: bug contract → Lex review → requirements approval → repair test plan → standard/high-impact decision → M-LOCK → R-G-R → review/regression → policy release → history

纯文本描述难以理解，特别是 bug_fix 的分支逻辑 ("standard" vs "high-impact")。

**建议**: 在 spec.md 中为两个 workflow 各提供一幅 ASCII 构图 (类似 v0.2-002-ui 的 mockup 风格)，标注节点、边、门禁和分支条件。

### P2-3: FR-1001 "Project" 概念分散定义

**位置**: FR-1001, FR-1101, FR-1201, FR-1901, FR-2001

**分析**: "Project" 是整个 spec 的核心实体，但定义分散在多个 FR 中：
- FR-1001: "一个 Project 代表当前 workspace/repository 内的一次开发工作流"
- FR-1101: "系统必须为 Project 分配不可变 identity, 并从 story 生成可区分的初始 display title"
- FR-2001: "终态/归档 Project 在历史中只读可见"

**建议**: 在 FR-1001 开头 (或在 spec 开头) 提供独立的 "Project" 实体定义，明确其属性、生命周期、与 WorkflowRun 的关系。目前 FR-1101 说 "创建 Project 并创建 WorkflowRun"，暗示 Project 是容器，WorkflowRun 是实例，但关系不够清晰。

### P2-4: "contract" 术语歧义

**位置**: FR-0901 ("contract digest") vs FR-2201 ("获批 contract")

**分析**:
- FR-0901: M-LOCK 绑定 "已批准需求文档及当前设计文档的共同 contract digest" — 这里 contract = requirements + design docs
- FR-2201: "为每个获批 contract 维护 trace ledger" — 这里 contract = 需求文档 (FR/AC)

两处 "contract" 指向不同范围：FR-0901 的 contract 包含设计文档，FR-2201 的 contract 仅需求。可能引起歧义。

**建议**: 明确术语：
- "requirements contract" = story + spec + acceptance (需求审批 gate 绑定)
- "design contract" = test-plan + architecture + interfaces (M-LOCK gate 绑定)
- "M-LOCK contract" = requirements contract + design contract (实现阶段启动的完整合同)

### P2-5: FR-0001 "definition 中不得包含任意 shell 字符串" 需明确禁止范围

**位置**: FR-0001 + FR-0301

**分析**: FR-0001 说 "definition 中不得包含任意 shell 字符串作为可执行步骤", FR-0301 说 "程序步骤只能引用 Louke 注册表中的 handler 名称"。但 "definition" 的格式 (YAML? JSON? Python DSL?) 和 handler 注册表的组织方式 (目录结构? 配置文件? 自动发现?) 均未定义。

**建议**: spec 中不需要定义格式细节（这属于 architecture），但应明确 "definition 的具体格式和注册表组织由 implementation 决定，但 spec 约束：所有步骤必须引用已知 handler, 不得包含可执行代码/命令"。

### P3 (轻微): story.md "当前边界" 中 "不提供通用 workflow editor" 值得在 spec 中引用

**位置**: story.md "当前边界" + spec.md "Clarification Log — 不借可用性扩张"

**分析**: story 明确说 "不提供允许用户任意绘制节点和边的通用 workflow editor; 工作流由程序定义, 用户只从允许的 workflow 中选择"。spec 的 Clarification Log 也有类似描述，但 FR 正文中未明确拒绝 "自定义 workflow 创建"。

**建议**: 在 FR-0001 或 FR-1101 中加一条 "不做": "不接受用户创建自定义 workflow definition (workflow 由 Louke 内置注册)"。这样实施者不会猜测 "是否允许用户定义新 workflow"。

---

## 第五部分: 与 exploration 文件的交叉检查

### 5.1 lex-stage1-attempt.md 反馈已纳入 spec

| 失败原因             | 对应 FR                            | 覆盖 |
| -------------------- | ---------------------------------- | ---- |
| Lex 不能作为 primary | FR-1401 (真实 OpenCode session)    | ✓    |
| Agent 返回空 body    | FR-1601 AC-5 (schema-invalid 拒绝) | ✓    |
| 空结果误记为 pass    | FR-2001 AC-1 (失败分类/可重试)     | ✓    |

**结论**: Lex 尝试的反馈已全部编码到 FR-1401/FR-1601/FR-2001。

### 5.2 product-journey-audit.md 反馈已纳入 spec

| 代码缺口           | 对应 FR                                  | 覆盖 |
| ------------------ | ---------------------------------------- | ---- |
| 初始化不完整       | FR-1801                                  | ✓    |
| sub-app 未 mount   | FR-1901 (可操作 Project 详情)            | ✓    |
| OpenCode 内存 echo | FR-1401 (真实实例) + NFR-0201 (诚实替身) | ✓    |
| 无 gate 审批 UI    | FR-0801/FR-0901 + FR-1901                | ✓    |
| 无失败/取消/归档   | FR-2001                                  | ✓    |
| 无历史/migration   | FR-2301                                  | ✓    |

**结论**: product-journey-audit.md 识别的 6 个代码缺口全部有对应 FR。

---

## 第六部分: 总结

| 指标                 | 数值                               |
| -------------------- | ---------------------------------- |
| story 期望结果覆盖   | 21/21 (100%)                       |
| story 场景覆盖       | 16/16 (通过 scenario + FR 隐含)    |
| FR/NFR → AC 覆盖     | 29/29 (100%, 127 条 AC)            |
| AC 可测性            | 127/127 可测试, 少数需补充验证方法 |
| 新发现问题           | 1 个 P1 + 5 个 P2 + 1 个 P3        |
| exploration 反馈纳入 | 全部已编码                         |

**总体评价**: 这是一份**高质量、高完成度**的 spec——结构清晰、覆盖完整、AC 规范，且已吸收了 exploration 阶段的失败反馈。主要改进空间在于 Decided 状态精细化管理 (P1-1)、workflow 可视化 (P2-2) 和术语歧义 (P2-4)。建议优先处理 P1-1，其余 P2/P3 可在 Lex review 阶段处理。
