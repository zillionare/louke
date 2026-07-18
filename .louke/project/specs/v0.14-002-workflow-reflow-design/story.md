# v0.14-002：让宿主项目设计可直接落地并持续受质量门禁保护

本文中的“项目”均指安装和使用 Louke 的宿主项目。Louke 自身采用什么语言、构建文件或 CI 配置，不构成宿主项目的默认事实。

本 Spec 包含两个相互配合的 Story：Story 1 确保 release version 真正进入宿主项目构建物；Story 2 确保 Louke 为宿主项目设计、实现并持续维护强制性的 GitHub Actions CI。两者共享宿主项目事实，但不能互相替代：branch 名称不能证明 artifact 版本，存在 workflow 文件也不能证明质量门禁真实生效。

## Story 1：让宿主项目的 Release Version 可验证地进入构建物

### 原始问题

Human 在创建 release 时已经提供目标版本，例如 `v1.2.3`，Louke 也会记录该版本并反映在 release branch 中。但 branch 名称只代表工作流身份，不能证明宿主项目最终构建物的版本正确。

不同宿主项目的版本源、构建工具、artifact 类型和安装后版本读取方式不同。如果没有统一的版本身份契约，可能出现：

- branch 是 `releases/v1.2.3`，但构建物仍是旧版本；
- 多个 artifact 版本不一致；
- CI 构建成功但 publish 了错误版本；
- 用户安装后无法确认实际安装的版本；
- 全新项目没有既有版本方案，Agent 又把技术选择推回 Human。

### Story 目标

作为使用 Louke 管理宿主项目 release 的维护者，我只需要在创建 release 时提供目标 release version；Louke 应根据宿主项目现状，或为全新项目自行选择合适的技术方案，建立从 release identity 到真实构建物 metadata 和安装后公开版本出口的可验证链路。

### Happy Path

1. Human 提供目标 release version。
2. Louke 保存 canonical version，并与 release branch/tag identity 绑定。
3. Archer 识别已有项目的版本源；若是全新项目，则自行选择版本源、构建方案和 adapter。
4. Devon 实现 adapter 和 CI 接线，Shield 验证真实构建物。
5. CI 构建所有必需 artifact，从 artifact metadata 提取版本并与 canonical version 比较。
6. 所有 artifact 验证通过后才允许 publish；用户安装、部署或运行后可以从公开版本出口确认实际版本。

### 关键边界

- Human 负责提供产品 release version，不负责选择 Maven/Gradle、npm、Cargo 或其它技术方案。
- Archer 负责技术选择、版本映射、adapter contract、构建与验证设计。
- branch 名称不是 artifact 版本来源。
- 不同宿主项目可以有不同版本源和构建方式，但最终必须提供统一的 canonical version 比较结果。
- 版本不一致、无法提取、artifact 缺失或构建结果不确定时，CI 必须阻止 publish。
- 这条 Story 不规定某一种语言、构建工具或配置文件。

### 建议的 Behavior Seeds

- 已有项目能够绑定真实版本源和现有 release workflow。
- 全新项目能够由 Archer 自行选择版本方案和构建工具。
- 带 `v` 前缀的 tag 与宿主项目不带前缀的版本可以按明确规则比较。
- 多个 artifact 中任一版本不匹配时，发布被阻止。
- 安装后的版本来自真实 artifact metadata，而不是 branch 名称或源码中的声明。
- CI 中断、构建失败或结果不确定时，不得标记为 artifact verified。

## Story 2：Louke 为宿主项目托管强制性的 GitHub Actions CI

### 原始问题

CI 是宿主项目开发质量的一部分，但最终用户不应为了使用 Louke 而自行研究测试分层、编写 GitHub Actions YAML、维护 required checks，或在每次架构变化后手工同步 workflow。

Louke 早期可以只支持 GitHub 和 GitHub Actions。现有 Louke 能在 test-plan 中描述命令，也曾提出安装固定 workflow 模板，但尚未形成适用于不同宿主技术栈的完整闭环：

- 初始化代码当前不会安装 CI workflow；
- 固定语言模板不能正确服务 Java、Node、Go、Rust、Python 或混合项目；
- 现有 AC 扫描只能确认 AC 被某个测试引用，不能确认它由必需的 integration/e2e 层覆盖；
- workflow 存在不等于默认分支已把它配置成 required check；
- 宿主项目命令、测试层、artifact 或外部依赖变化后，CI 可能与锁定设计漂移；
- 直接覆盖既有 `.github/workflows/` 会破坏用户资产，完全放任既有 workflow 又不能保证 Louke 的质量合同。

### Story 目标

作为使用 Louke 开发宿主项目的维护者，我希望 Louke 根据已批准需求、宿主项目事实和 Archer 的技术设计，自动完成 GitHub Actions CI 的设计、实现、验证、强制启用和后续更新，使每次 pull request 和受保护分支变更都必须通过与当前设计一致的质量门禁，而不需要我自行开发 CI。

### Happy Path

1. Louke 确认宿主项目的 GitHub repository、默认分支、当前技术栈、构建入口、测试入口、artifact 和既有 workflows。
2. Archer 为每个 AC 定义可观察接口、必需测试层和 CI gate/job，并完成 runner、工具链、job DAG、权限、secret、外部依赖、artifact/evidence 和失败语义设计。
3. 该设计以正式 artifact 和程序支持的 machine-readable CI contract 固化；下游不需要从自然语言猜测 schema 或命令。
4. Devon 按锁定设计创建或更新 Louke 托管的 `.github/workflows/louke-ci.yml` 和必要的宿主项目命令入口；无关既有 workflow 保持不变。
5. Shield 实现 test-plan 指定的 integration/e2e 资产；同一 AC 要求多个测试层时，各层分别提供证据。
6. Louke 对 workflow、CI contract、测试资产和宿主命令做本地确定性校验，提交后触发真实 GitHub Actions run。
7. Louke 确认稳定聚合 check `Louke CI / required` 已由 GitHub Actions 产生并成功，再通过 GitHub repository ruleset 或 branch protection 将其设置为目标分支 required check，并回读确认。
8. 后续设计若改变构建、测试层、artifact、运行环境或 gate，Louke 更新托管 workflow 并再次验证；未同步的漂移会阻止完成，而不是被静默接受。

### 产品边界

- 当前强制支持的 provider 是 GitHub Actions；不要求在本 Story 中支持 GitLab CI、Jenkins 或其它 CI。
- GitHub CI 对每个 Louke 宿主项目都是必需能力，不能整体标记为 `N/A`。单个质量层只有在产品和技术上确实不适用时才可记录 `N/A` 及技术理由；“目前还没写”不是理由。
- Louke 管理固定路径 `.github/workflows/louke-ci.yml`。其它 workflow 默认属于宿主项目既有资产；Louke 不删除、不覆盖，除非锁定设计明确要求复用并能安全合并。
- Archer 决定技术方案；Devon 实现 workflow；Shield 实现 integration/e2e 测试。Human 不负责选择 runner、测试框架、job DAG、缓存或 GitHub Actions 写法。
- Agent 指令只规定各自的专业责任；workflow 生成、验证、GitHub API 写入、证据持久化和失败恢复必须由程序提供，不依赖 Agent 自述成功。
- CI 与 release/publish 分离：pull request CI 不发布生产 artifact；release/publish 必须依赖同一 commit 的 required CI 和 Story 1 的 artifact identity gate。

### 程序能力 Story Seeds

后续 Spec/Acceptance 应把下列种子细化为正式 FR/NFR 和 AC：

1. **Machine-readable CI contract**
   - 为 `.louke/project/project.toml` 或独立受控 artifact 定义有版本的 CI schema；schema 至少表达 provider、managed workflow path、目标分支、触发器、runner/矩阵、setup、jobs/依赖、宿主命令、required check、权限、secret、service、cache、artifact/evidence 和 failure policy。
   - task manifest 必须把同一 schema 和授权字段交给 Archer、Devon、验证程序；不得只把格式写在某个 Agent prompt 中。
   - schema 升级需要迁移和向后兼容诊断；未知字段或未知版本不得被静默忽略。

2. **需求级测试层合同**
   - test-plan/template 提供规范化的 `AC → observable interface → required layer(s) → CI gate/job → rationale` 分配。
   - 跨 2 个以上模块的接口自动要求 integration；面向用户的主成功旅程自动要求 e2e；一个 AC 可以要求多个层。
   - 校验器读取 Acceptance、interfaces、覆盖分配和测试元数据，拒绝未覆盖 AC、错误测试层、漏掉 integration/e2e、未注册测试路径和必需层被 skip/deferred 却无正式依据。
   - 结构闭包由程序验证；Archer/Prism 仍负责判断分层语义是否正确。

3. **冲突安全的托管 workflow 生命周期**
   - 新项目创建托管 workflow；已有项目先盘点并保留其它 workflows。
   - Louke 为托管文件记录生成来源、contract revision/digest 和最后同步版本；相同输入生成稳定结果。
   - 文件未被外部修改时可幂等更新；检测到 Human/其它工具直接修改时不得静默覆盖，必须保留 diff，交由实现 Agent 依据锁定设计完成语义合并，再建立新基线。
   - workflow 缺失、YAML 非法、命令不存在、contract 漂移或 required 聚合不完整时，校验失败。

4. **稳定 required check 与失败传播**
   - 托管 workflow 在 push、pull request 和手动诊断场景运行，并按项目策略覆盖默认分支和 release branches；使用 merge queue 时支持对应触发器。
   - 提供名称稳定且不与其它 workflow 重复的聚合 check `Louke CI / required`。
   - 聚合 check 只有在全部必需 job 成功时才成功；失败、取消、超时、缺失、结果不确定或被非法 skip 都必须失败。
   - format/lint/static、unit、integration、e2e、AC traceability、build 和 artifact verification 按 CI contract 纳入；各 job 可按风险并行，但 required 聚合保持确定性。

5. **GitHub 强制启用与回读**
   - 在 workflow 首次产生目标 check 后，Louke 创建或更新自己拥有的 repository ruleset；能力不支持时使用兼容的 branch protection required status check 机制。
   - 只增加或更新 Louke 拥有的规则，不删除用户已有 ruleset、required check 或 review policy。
   - GitHub 权限、套餐能力、check 尚未出现、API partial success、网络中断或回读不一致时，不得报告“CI 已强制启用”；提供可重试且幂等的恢复路径。

6. **安全与可复现性**
   - 默认使用最小 GitHub token 权限；pull request/fork 代码不得在生产 secret 或高权限 token 上下文执行。
   - 默认 CI 使用可控替身处理第三方服务；真实外部 smoke 单独标识环境和 evidence，不进入无凭据的默认 PR gate。
   - action、runtime、工具链和依赖遵循宿主项目设计的固定/锁定策略；缓存不能成为跳过安装、验证或 artifact identity 的证据。

7. **可观察证据与恢复**
   - 本地校验和 GitHub run 都产生可关联 repository、commit、workflow revision、CI contract digest、required check、job 结果和 artifact identity 的证据。
   - 重试不重复创建 ruleset 或破坏既有 workflow；中断恢复从最后可确认事实继续。
   - workflow 或 branch rule 被外部删除/修改后，Louke 能检测 drift 并恢复到当前锁定合同；无法自动安全恢复时明确阻断，不伪报 PASS。

### 建议的验收场景

- 全新 Java、Node 或其它宿主项目由 Archer 自主选择技术栈后，Louke 能生成并启用与该项目匹配的 CI，而不出现其它语言的虚假路径。
- 已有项目带有多个自定义 workflow 时，Louke 新增或更新托管 workflow，不改变无关文件和既有 required checks。
- integration AC 只有 unit test 引用，或 e2e AC 只有 API/integration 测试时，层级闭包失败。
- 必需 job 失败、取消、超时或未运行时，`Louke CI / required` 失败，PR 不能合并。
- GitHub API 在 ruleset 写入后返回 partial success 或回读不一致时，操作可安全重试且不会报告完成。
- Human 直接编辑托管 workflow 后，Louke 保存并呈现 diff，不静默覆盖；实现 Agent 合并后建立新的 contract digest。
- release workflow 尝试发布一个 required CI 未通过或 artifact version 不匹配的 commit 时，publish 被阻止。
