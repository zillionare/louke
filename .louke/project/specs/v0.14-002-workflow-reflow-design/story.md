# STR-1403: 形成可执行、可审查的宿主项目技术设计基线

---

| Story ID | 创建时间 | 分流建议 |
| :--- | :--- | :--- |
| STR-1403 | 2026-07-19T00:00:00+08:00 | Go |

---

## 0. 原始输入

> v0.14 系列的主要任务是把工作流从 Maestro 掌控改为 Runtime 驱动，Agent 只做语义内容输出或 coding；Archer 承担 Test Plan、Architecture、Interfaces，以及宿主项目 CI、pre-commit、release version、build/artifact 和发布恢复等技术设计。Human 只负责 Story 和产品需求，不应被要求替 Agent 作技术决定。设计通过 Prism 独立评审和程序校验后直接进入实现，不再设置第二个 M-LOCK。
>
> Louke 将部署到成百上千个不同技术栈的宿主项目中。Agent 指令不得写入只属于 Louke 自身仓库的技术事实。对全新项目没有既有技术事实时，Archer 应自行作出合理技术选择。
>
> 从这一版起，Agent 提示词本身应成为规范的一部分，与其它 Spec 工件一同修改、评审、锁定；机器可读 schema 不能只存在于 Agent 提示词中。

## 1. 用户意图

- **主要用户**：使用 Louke 管理宿主项目开发与发布的维护者，以及维护 Louke 工作流合同的开发者。
- **当前处境**：需求已经批准，但测试层、架构、接口、CI、版本与构建物等技术决定仍可能散落在自然语言或 Agent 提示词中；若这些决定缺少统一身份、机器合同和独立评审，Runtime 无法可靠地驱动后续实现。
- **目标结果**：Archer 根据当前需求基线和宿主项目事实自主形成完整设计，Runtime 能校验并持久化全部设计与提示词合同，Prism 独立评审后直接建立实现基线。
- **成功信号**：进入 `M-IMPL` 时，下游 Agent 和程序无需猜测技术方案、输入输出 schema、测试层、CI、版本或发布合同，且所有输入均绑定同一可追溯 revision/digest。

## 2. 核心操作路径

### 2.1 主路径

- **起点上下文**：Human 已在 `M-REQ-APPROVAL` 批准当前 Story、Spec 与 Acceptance revision。
- **入口/触发**：Runtime 校验需求批准和宿主项目事实后进入 `M-DESIGN`，授权 Archer 编辑本轮指定的设计工件。

1. Archer 读取需求基线、代码库事实、现有工具链和既有技术合同；全新项目缺少既有方案时，Archer自行选择适合目标产品的技术栈与工程方案。
2. Archer 形成 Test Plan、Architecture、Interfaces，并生成有版本的 integration/e2e、pre-commit、GitHub CI、release-version、build/artifact 和 publish/recovery machine contracts。
3. 本轮受影响的 Agent 提示词作为规范性工件进入同一设计 revision；其来源、部署结果、schema 引用和 digest 均被登记。
4. Human 可以在文档界面评论或直接修改授权原文，也可以完全缺席；Archer自行判断技术建议，发现产品缺口时才返回需求边界。
5. Runtime 执行结构、schema、引用、覆盖、漂移和安全校验；Prism 对当前精确 revision 做独立语义评审。
6. REVISE 形成新 revision 并重新评审；全部检查通过后，Runtime 将设计工件、machine contracts 和规范性提示词的精确身份合并为 implementation baseline。
7. 流程直接进入 `M-IMPL`，不要求 Human 批准技术方案；后续有效 design gap 可以按定义化路径返回 `M-DESIGN`。

- **继续/返回**：成功后进入 `M-IMPL`；技术缺口留在 `M-DESIGN` 修订，产品范围或 Acceptance 缺口经 Human 决定后返回 `M-SPEC`/`M-ACC`。

### 2.2 行为种子

### BS-01 设计阶段入口与上下文

- EARS: `WHEN 当前需求 baseline 已获批准且全部输入 current, THE 系统 SHALL 建立绑定精确需求与宿主项目事实的 M-DESIGN revision。`
- 来源: 主路径
- 说明: 防止 Archer 针对过期需求或错误代码基线进行设计。

### BS-02 自主技术决策

- EARS: `WHERE 宿主项目已有有效技术事实, THE 系统 SHALL 要求设计兼容并复用这些事实；WHERE 全新项目不存在既有方案, THE 系统 SHALL 由 Archer 自主选择技术方案。`
- 来源: 原始输入 / 产品约束
- 说明: 既不把某个工具仓库的做法泛化给所有项目，也不把技术责任推给 Human。

### BS-03 三类设计文档

- EARS: `WHEN Archer 完成设计, THE 系统 SHALL 产出彼此一致且可追溯到 FR/AC 的 Test Plan、Architecture 与 Interfaces。`
- 来源: flow.md M-DESIGN
- 说明: 为实现、测试和评审提供完整语义输入。

### BS-04 测试层闭包

- EARS: `WHEN Test Plan 分配验收条件, THE 系统 SHALL 为每个 AC 明确 observable interface、required test layer、执行入口与 CI gate。`
- 来源: CI 与测试讨论
- 说明: 避免仅复述功能或只写 unit test 而遗漏真实用户旅程。

### BS-05 有版本的 Machine Contracts

- EARS: `WHEN 设计包含程序需要执行的命令、路径、schema 或失败语义, THE 系统 SHALL 将其写入可校验且有版本的 machine contract。`
- 来源: flow.md / schema 讨论
- 说明: 下游程序和 Agent 不应从自然语言猜测接口。

### BS-06 托管 GitHub CI

- EARS: `WHEN 宿主项目进入 Louke 管理, THE 系统 SHALL 设计与真实技术栈匹配的 GitHub Actions CI、稳定 required check 和冲突安全的维护方案。`
- 来源: 已确认产品决定
- 说明: 用户不需要自行开发或维护基础 CI。

### BS-07 Pre-commit 合同

- EARS: `WHEN 宿主项目需要正式 commit gate, THE 系统 SHALL 设计保留既有 hooks 的快速 pre-commit 合同，并将全量权威检查留给 Runtime 与 CI。`
- 来源: RGR/pre-commit 讨论
- 说明: pre-commit 不承担 Red 证明，也不能成为唯一质量权威。

### BS-08 Release Version 与构建物身份

- EARS: `WHEN release 具有 canonical version, THE 系统 SHALL 设计该身份进入版本源、全部构建物及安装/运行后公开版本出口的可验证链路。`
- 来源: release version 讨论
- 说明: branch/tag 名称不能替代真实 artifact version。

### BS-09 发布与恢复合同

- EARS: `WHEN 设计发布过程, THE 系统 SHALL 明确幂等外部操作、发布后验证、回滚或 forward-fix 以及不确定结果的恢复行为。`
- 来源: flow.md M-PUBLISH
- 说明: Runtime 必须能够从中断和 partial success 中恢复。

### BS-10 提示词成为规范性工件

- EARS: `WHEN 某一 Spec 改变 Agent 的语义职责, THE 系统 SHALL 将受影响的 canonical prompt source 列入该 Spec 的规范性工件集并与其它设计工件共同 revision、review 和 baseline。`
- 来源: 原始输入
- 说明: Agent 行为不能继续作为未声明的隐式规范。

### BS-11 提示词与 Schema 分离

- EARS: `WHEN Agent 输入或输出需要结构化数据, THE 系统 SHALL 由程序拥有并版本化 schema，提示词只引用该 schema 和语义责任。`
- 来源: schema 来源讨论
- 说明: Devon 等 Agent 必须从 task manifest 得到可执行合同，而不是从另一 Agent 的文字猜测格式。

### BS-12 提示词部署一致性

- EARS: `WHEN canonical prompt source 被部署为运行时 Agent 配置, THE 系统 SHALL 生成可回读的 prompt bundle manifest 并检测来源、转换结果和部署副本的漂移。`
- 来源: 当前 prompt packaging 事实
- 说明: 确保实际运行的提示词就是当前设计基线中的版本。

### BS-13 Human 可选 Review 与直接修改

- EARS: `WHEN Human 在 M-DESIGN 评论或直接修改原文, THE 系统 SHALL 保留 diff 并由 Archer 按技术判断处理；WHEN Human 缺席, THE 系统 SHALL 继续技术评审。`
- 来源: Human diff / 技术责任讨论
- 说明: Human 可以干预，但不是技术批准门禁。

### BS-14 独立 Prism Review

- EARS: `WHEN 当前设计 revision 完成程序校验, THE 系统 SHALL 由未参与作者结果伪造的 Prism 独立评审全部设计、合同和规范性提示词。`
- 来源: flow.md
- 说明: 保证设计语义一致、可实现且没有职责空洞。

### BS-15 无第二次技术锁

- EARS: `WHEN 当前设计 revision 的程序校验与 Prism review 均通过, THE 系统 SHALL 直接建立 implementation baseline 并进入 M-IMPL。`
- 来源: 已确认流程决定
- 说明: Human 只批准产品需求，不承担技术方案签字。

## 3. 范围、约束与例外

### 3.1 必须保持的产品约束

- Runtime 是 dispatch、持久化、Git、GitHub、阶段推进和副作用的唯一 authority；Agent 只编辑获授权工件并返回语义结果。
- Archer 不主动向 Human 请求架构、测试、接口、CI、构建工具或其它技术决定；产品需求缺口必须通过 Runtime 返回需求阶段。
- 设计必须以宿主项目事实为依据，不得把 Louke 自身仓库的语言、构建配置或目录当作所有宿主项目默认。
- GitHub Actions 是当前强制支持的 CI provider；其它 CI provider 不在本批次内。
- 每份 Spec 最多 30 条有效 FR；本 Story 的提示词治理与 M-DESIGN 同属 002，不再拆分额外 batch。

### 3.2 非常规要求

- Agent 提示词从本版本起属于正式规范性工件，而非仅作为实现细节或部署副本存在。
- M-DESIGN 没有 Human 技术批准 gate；Human 的沉默不等于认可，但也不阻塞 Archer/Prism 完成技术职责。

### 3.3 Out-of-Scope

- 不实现 GitHub Actions、pre-commit adapter、version adapter、Runtime 状态机或 Agent prompt 修改；本批次文档只定义其合同。
- 不支持 GitLab CI、Jenkins 或其它 CI provider。
- 不允许普通宿主项目 release 修改 Louke 安装包内的 canonical Agent prompts；宿主项目只消费被当前运行绑定的 prompt bundle。
- 不规定所有宿主项目必须使用某一种语言、构建工具、测试框架、artifact 类型或版本文件。

## 4. 重要推导与证据

### D-01 Prompt source 与部署副本必须区分

- **结论**：canonical source、转换规则和部署副本应有独立 identity，并由同一 bundle manifest 关联。
- **依据**：当前实现从 `louke/agents/*.md` 生成 `.opencode/agents/*.md`，部署过程会重写 frontmatter/model/skill 引用。
- **影响**：只锁定源文件或只检查部署文件都不足以证明实际 Agent 合同一致。

### D-02 Prompt 不能拥有唯一的机器接口定义

- **结论**：Agent 的结构化输入输出 schema 必须由 Runtime 可发现的版本化 registry 提供。
- **依据**：下游 Agent 不会可靠地读取另一 Agent 的提示词；仅在 prompt 中给出 YAML 示例无法形成程序校验合同。
- **影响**：prompt 只保留职责、语义规则和 schema reference，Runtime manifest 携带精确 schema identity。

### D-03 规范性提示词的适用范围必须显式

- **结论**：每个 Spec 声明其影响的 prompt source；未列入的 prompt 不因该 Spec 自动变化。
- **依据**：Louke 的 Agent 提示词会部署到大量宿主项目，混入仅属于单个宿主项目的技术事实会造成错误泛化。
- **影响**：002 主要影响 Archer 与 Prism；003 再规范实现、测试、安全和收尾角色。

### D-04 Human 直接修改与技术批准不同

- **结论**：Runtime 应把直接 diff 提供给当前 Agent；Agent 可接受无问题的修改，发现问题时通过 inline discussion 讨论。
- **依据**：每轮均有 Runtime commit/baseline，可精确识别 Human 修改；Human 仍可能不用 inline discussion。
- **影响**：不需要新增技术 gate，也不能把 Human 修改自动当作批准。

## 5. 开放产品决定

无。当前未决项均属于 Archer 应自主完成的技术设计，或已由既有产品决定确定。

## 6. 必要性、风险与分流建议

- **既有能力**：当前已有 Agent prompt source/deployment、部分 Runtime manifest/schema、GitHub 集成和设计文档模板，可作为迁移基础。
- **冲突**：现有 prompts 中仍可能包含 Maestro 驱动、Agent 自行推进/commit、或 schema 只写在提示词中的旧合同，需要按本 Spec 后续迁移。
- **重要风险**：若只实现 Runtime graph 而不锁定 prompt bundle，实际运行 Agent 可能继续服从旧职责；若 machine contract 仍是自由文本，程序无法验证设计是否真正落地。
- **分流建议**：Go — 这是 003 实现流程能够安全启动的必要前置设计。

## 7. 可追溯信息

- **Story ID**：`STR-1403`
- **创建时间**：`2026-07-19T00:00:00+08:00`
- **关联 Spec/Issue**：`v0.14-002-workflow-reflow-design`；Issue 待 `M-REQ-APPROVAL` 后建立
- **Sage peer review**：`Pending`
