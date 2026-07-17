# STR-1401: v0.14 Workflow Reflow — 生产工作流统一

---

## 0. 原始输入

> 把 v0.12 Runtime 核心、v0.13 Web/Chat、v0.13.1 安装和质量门整合为唯一生产工作流，并增加首版可靠但简单的 return-upstream、bounded waiver、no-new-debt adoption 和内置 lifecycle hooks。

以下三项核心原则是从后续讨论中确认的约束，非用户逐字原话：

1. Runtime 是 workflow 状态、合法转移和权威副作用唯一控制者；Web/CLI/Chat/Agent 不能伪造 program result、pass、approval 或 next step。
2. program 自动执行确定性检查和副作用；semantic Agent 负责理解、分析、设计、代码/测试内容生成、评审；Human 决定产品、价值、风险、requirements approval、M-LOCK、waiver、adoption 和 release。
3. 从 v0.12 核心类库、v0.13 观察面、v0.13.1 安装/质量门到一条完整可完成的 `new_feature` 和 `bug_fix` 生产旅程，并通过 installed-wheel E2E 和 Louke dogfood 证明。

---

## 1. 用户与场景 (Who & Where)

### 1.1 用户画像 (Who)
- **主要角色**：使用 Louke 开发项目的产品负责人兼技术维护者。该角色既是需求的提出者（决定 Go/Park/No-Go、批准 requirements、M-LOCK、waiver、adoption），也是技术方案的参与者（可参与技术 review、暂停 reviewer、提出 constraint）。
- **次要角色**：Louke 自身的发布维护者（负责验证 installed-wheel E2E、dogfood 全流程、执行受控回退）。
- **用户规模**：单一用户（本地桌面应用，无多用户协作）。
- **使用频次**：高频（每日）。该角色在推进功能或修复缺陷时持续与 workflow 交互。
- **网络环境**：稳定办公网络。离线场景下可本地操作，但 Git push、外部 API 调用等需要网络。

### 1.2 使用终端 (Where)
- **终端类型**：Web（桌面浏览器）、CLI、Chat（通过 Web 端 Chat tab）。三者必须看到同一 project、run、当前步骤、合法动作和证据。
- **适配要求**：桌面浏览器，不要求移动端适配。
- **离线场景**：核心 workflow 推进（program step、语义 Agent 工作、human gate）在本地完成；Git push、CI report 接收等需要网络，离线时允许延后但不静默跳过。

### 1.3 产品入口与生命周期 (Access & Lifecycle)
- **主入口**：`lk serve` 启动后，通过 Web 端 Chat/Chat tab 开始和完成操作。CLI 作为辅助入口。
- **辅助入口**：CLI（`lk` 命令）、API（供 program handler 和 adapter 调用）。
- **获得产品**：用户通过 `curl | sh`（Linux/macOS）或 bat/ps（Windows）安装全局 `lk`；在项目目录中 `lk install` 创建本地 `.venv` 并安装 Louke Python 包。首次 setup 通过 `lk serve` 启动后由 Web init-wizard 完成项目初始化、依赖检查和模型就绪确认。
- **升级与迁移**：
  - **升级触发**：用户主动执行 `lk upgrade`（项目级或全局级）。v0.14 不自动升级。
  - **旧 workspace 迁移**：用户通过显式 preview/confirm 采用 v0.14 新 workflow。旧 `current_stage` 不推断为新 run；旧证据只读保留。迁移失败时，旧 workspace 保持原样，用户可在新项目/workspace 使用新 workflow。
  - **失败恢复**：adoption 失败不破坏用户文件、Git history 和既有证据。必要时允许 breaking adoption，用户在新 workspace 使用新流程。
  - **v0.14 不承诺**：跨 workflow definition version 的 in-flight run 迁移、旧 workflow 兼容。这些属于 v0.17。

---

## 2. 功能与价值 (What & Why)

### 2.1 功能描述 (What)

v0.14 将 v0.12 的 Runtime 核心类库、v0.13 的 Web/Chat/Runs 观察面和 v0.13.1 的安装与质量门装配为**唯一生产级工作流**。用户安装后启动 `lk serve`，即可通过 Web/CLI/Chat 任一入口创建 `new_feature` 或 `bug_fix` run，经历完整的 Story → 需求审批 → 设计/M-LOCK → 实现 → 权威测试 → 发布确认 → 归档的流程。

核心能力包括：

- **Runtime 权威控制**：程序是 workflow 状态和合法转移的唯一控制者。确定性检查（lint、typecheck、测试执行、Git 操作）由 program handler 自动执行。语义任务（Story 调研、设计、代码生成、评审）由 Agent 承担，但 Agent 不能伪造 program result、批准 gate 或自行推进 run。
- **return-upstream（返回上游）**：对未发布 active run，用户可在 M-LOCK 后请求返回 definition 声明的固定合法上游目标。目标及下游 artifact/approval/evidence 统一标记 stale/superseded，保留文件、文档和 commit 历史。不可逆外部副作用进入 `needs_attention`。
- **bounded waiver（有界豁免）**：对明确标记为 waivable 的失败检查，用户可提交含 actor/reason/scope/revision 的 waiver。原始失败保留，不改写为 PASS。requirements approval、M-LOCK、identity/secret、CAS、artifact freshness、Agent 自批、伪造 program result、release identity mismatch 永不可 waive。
- **no-new-debt adoption（不新增债务的采用）**：既有项目通过 read-only preview 运行全部检查，历史问题经审计后可冻结为 baseline-known（不是 PASS）。已进入 baseline 的文件一旦被修改，整文件必须符合当前流程并永久退出 baseline。新问题或恶化问题阻断 adoption。关键不变量不可 baseline。
- **内置 lifecycle hooks**：首版只支持 Louke 内置、版本化 hooks，覆盖语义结果保存、用户决定保存、session/artifact 保存和 return-upstream 前后。Hook 由 Runtime 调度，无 transition/gate authority。项目自定义 shell hooks 不做。
- **Agent 职责重组**：Scout/Warden/Keeper 从新 workflow 注销。确定性职责归 program handler，语义残余归 Scribe/Sage/Lex/Prism。Scribe 已有 prompt/Sage peer 合同；v0.14 接入真实 Runtime dispatch。
- **持久化与重启恢复**：Runtime-native run/task/gate/artifact/evidence/event 持久化。关闭浏览器、重启 Louke 或 Agent 失败后，重新进入项目即可从原位置继续，不依赖会话存活。
- **Workflow definition 版本化不可变**：同一版本不可用不同内容重新注册；新 run 默认使用当前 approved definition；已开始 run 固定原版本。

**快乐路径（Happy Path）**：

1. 用户安装 v0.14，在项目目录执行 `lk serve`，Web 端打开项目。
2. 用户在 Chat 中提出新功能设想，Runtime 自动创建 `new_feature` run 并 dispatch Scribe semantic task。
3. Scribe 完成 Story 调研与撰写，Sage 独立 peer review。用户确认 Go 并批准 requirements。
4. Runtime 自动推进到设计阶段，dispatch 对应的 semantic Agent（Archer/Lex 等）。Agent 完成 Test Plan、Architecture、Interfaces 设计草案。
5. 用户可选参与技术 review（暂停 reviewer、查看 diff），最终批准 M-LOCK。
6. Runtime 进入实现阶段，Agent 在 Runtime 指定的 workspace/工作位置中生成代码和测试，program handler 自动执行 lint/typecheck/unit/integration 测试。
7. 用户发现设计遗漏，在 M-LOCK 后请求 return-upstream 到设计阶段。Runtime 标记下游 artifact 为 stale，用户重新经过设计评审和 M-LOCK。
8. 所有检查通过后，Runtime 进入 release confirmation。用户确认发布，Runtime 执行 tag/release/history archive。
9. 用户关闭浏览器。重启 `lk serve` 后，历史 run 完整可读，active run 可继续推进。

### 2.2 问题陈述与目标 (Why)
- **问题陈述**：当前 v0.12 Runtime 核心类库、v0.13 Web/Chat 观察面和 v0.13.1 安装/质量门各自独立，尚未装配为唯一生产工作流。用户从 `lk serve` 启动后无法完成一条从 Story 到发布归档的完整旅程。Scout/Warden/Keeper 仍是三个只包装工具的 Agent，消耗 session 和上下文。没有自动 Driver、production composition root、权威 program result 边界、return-upstream、waiver 和 adoption 机制。
- **北极星目标**：用户安装 v0.14 后，只需 `lk serve` 即可通过 Web/CLI/Chat 任一入口完成一条完整的 `new_feature` 产品旅程，全程由 Runtime 驱动，Agent 只做语义工作，Human 只做产品决策，程序验证所有事实。
- **可观测指标**：
  - 一条完整的 installed-wheel `new_feature` E2E 旅程（setup → Story → 审批 → 设计 → M-LOCK → 实现 → 测试 → release → archive）可无阻塞完成。
  - 该旅程中 Scout、Warden、Keeper 的 task/session/dispatch 数量均为零。
  - program result 不能由客户端或 Agent 伪造（通过 E2E 断言验证）。
  - Louke 自身的 v0.14 开发通过 dogfood 完整使用新 workflow，证明新流程可承担真实项目工作。

### 2.3 行为种子（EARS-lite）

以下为从故事中提取的行为种子，用于 M-SPEC 继续展开；不要求在 M-STORY 锁定完整验收合同：

| 编号   | EARS 句式                                                                                                                                                                                     | 说明                         |
| :----- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------- |
| AC-01  | `WHEN 用户通过 Web/CLI/Chat 启动 new_feature, THE 系统 SHALL 创建 WorkflowRun 并自动执行 program steps 和 dispatch semantic tasks`                                                             | 自动 Driver 入口             |
| AC-02  | `WHEN 一个 Agent 或客户端提交 program result, THE 系统 SHALL 拒绝，仅接受对应 program handler 的真实执行结果`                                                                                | 权威 program result 边界     |
| AC-03  | `WHEN Louke 服务重启, THE 系统 SHALL 从持久化 store 恢复 run、gate、task、artifact、evidence 和当前步骤，允许从原位置继续`                                                                    | 重启恢复                     |
| AC-04  | `WHEN 用户从 Web、CLI 或 Chat 任一入口查看项目, THE 系统 SHALL 呈现相同的 project、run、当前步骤、合法动作和证据`                                                                            | 多入口一致性                 |
| AC-05  | `WHEN 用户请求 return-upstream AND 当前 run 为 active 且未发布, THE 系统 SHALL 展示 definition 声明的固定合法上游目标并等待用户确认`                                                          | return-upstream 目标选择     |
| AC-06  | `WHEN return-upstream 执行, THE 系统 SHALL 将目标步骤及下游 artifact/approval/evidence 标记为 stale/superseded，保留文件、文档和 commit 历史`                                                 | return-upstream 下游 stale   |
| AC-07  | `IF return-upstream 遇到不可逆外部副作用（已 publish/tag）, THE 系统 SHALL 拒绝自动回退并进入 needs_attention`                                                                               | return-upstream 不可逆边界   |
| AC-08  | `WHEN 用户对 waivable 检查提交 waiver, THE 系统 SHALL 记录 actor/reason/scope/target evidence/revision 并保留原始失败证据，不将 FAIL 改写为 PASS`                                             | bounded waiver 记录          |
| AC-09  | `WHERE 检查为 requirements approval、M-LOCK、identity/secret、CAS、artifact freshness、Agent 自批或 release identity mismatch, THE 系统 SHALL 拒绝任何 waiver`                                | 不可 waive 不变量            |
| AC-10  | `WHEN 用户对既有项目请求 adoption preview, THE 系统 SHALL 固定 Git revision/workspace digest、运行全部适用检查并展示可 baseline 的历史问题与阻断 adoption 的新问题`                           | no-new-debt adoption preview |
| AC-11  | `IF baseline 文件在 adoption 后被首次修改, THE 系统 SHALL 对该文件执行当前全部适用检查，全部通过后该文件永久退出 baseline`                                                                    | touch-to-clean               |
| AC-12  | `IF adoption 或 baseline 操作失败, THE 系统 SHALL NOT 破坏用户文件、Git history 或既有证据`                                                                                                  | adoption 失败安全保证        |
| AC-13  | `WHEN 语义结果、用户决定或 session 被保存, THE 系统 SHALL 调用已注册的内置 versioned lifecycle hook`                                                                                          | 内置 lifecycle hooks 调度    |
| AC-14  | `THE 系统 SHALL NOT 在新 workflow run 中创建 Scout、Warden 或 Keeper 的 task、session 或 dispatch`                                                                                            | Agent 注销                   |
| AC-15  | `THE 系统 SHALL NOT 允许以不同内容重新注册同一 workflow definition version`                                                                                                                   | workflow definition 不可变   |
| AC-16  | `THE 系统 SHALL 支持从公开入口（lk serve、Web/CLI）完成 new_feature 和 bug_fix 的完整产品旅程（Story → 审批 → 设计 → M-LOCK → 实现 → 测试 → release → archive）`                             | 完整可完成 workflow          |
| AC-17  | `WHEN installed-wheel E2E 执行, THE 系统 SHALL 断言 Scout/Warden/Keeper dispatch 数量为零且 program result 不可由客户端/Agent 伪造`                                                          | E2E 权威验证                 |

---

## 3. 竞品与边界 (Scope & Competition)

### 3.1 Adopt / Avoid 清单（补全素材，非市场裁决）

鉴于 v0.14 是 Louke 自身 workflow 架构的整合与升级，而非面向终端用户的新功能，本 Story 无直接竞品。以下基于类似 CI/CD pipeline-as-code 产品的实践模式做补全式分析：

| 类型  | 来源                       | 内容                                                                                     | 理由                                                                                     |
| :---- | :------------------------- | :--------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------- |
| Adopt | GitHub Actions / Jenkins   | 将 workflow definition 作为版本化不可变合同，run 创建后固定 definition version，不随定义更新而改变在途 run | 防止 workflow 定义变更导致在途 run 进入不一致状态，与我们已有 catalog 设计一致            |
| Adopt | GitLab CI / CircleCI       | 程序化 gate 执行：pipeline 状态只能由真实执行的 job 结果推进，不能由 API 调用者声明 "pass" | 直接对应 v0.14 的"Agent 不能伪造 program result"核心要求                                  |
| Avoid | 部分 CI 产品的 blanket skip | 允许跳过整组检查的 `--force` 或全局 bypass，导致安全门被静默绕过                         | 我们的旧 `--force` waiver 就是这种模式。v0.14 的 bounded waiver 必须保留原始失败、限制 waivable 范围、永不可 waive 关键不变量 |
| Avoid | 某些 Agent 自批模式        | 允许生成代码的 Agent 自行声明测试通过或代码审查通过，没有独立验证                         | 直接对应 v0.14 的"Agent 不能自批、自报测试或伪造 program result"                          |

### 3.2 Out-of-Scope（明确不做）

以下内容明确属于 v0.17 或更晚版本，不在 v0.14 范围内：

- [ ] 完整 CI report interruption matrix（immediate/safe-point/record-only、迟到报告处理等）。v0.14 只保留完成核心 workflow 必需的权威测试执行和证据。
- [ ] 夜间自动重构、`maintenance/*` 分支、复杂 branch/worktree 生命周期自动化、hotfix 延迟同步自动管理。
- [ ] 跨 workflow definition version 的 in-flight migration、step mapping、兼容旧 workflow。
- [ ] 精细 artifact dependency graph、局部 freshness 传播、自动补偿/reconcile 不可逆副作用。
- [ ] 项目自定义或任意 shell lifecycle hooks；复杂 hook marketplace/policy。
- [ ] baseline finding 的复杂语义 identity、owner/expiry 自动治理和 workspace-level 高级 debt analytics。
- [ ] waiver expiry/renew/revoke/多 waiver 冲突等高级治理。
- [ ] v0.12.1 全面测试债务清理、通用真实环境矩阵、全面浏览器覆盖。
- [ ] 完整 Settings、Chat `/`/`!` 命令、End User Docs AI 编辑（属 v0.15）；i18n（属 v0.16）。
- [ ] 复杂 controlled legacy fallback、旧 Runtime 双版本兼容。
- [ ] 版本号提议/写入的重新设计（复用 v0.13.1 release identity）。

### 3.3 约束条件
- **技术约束**：
  - 程序化 workflow 必须基于 Python（与现有 Louke 技术栈一致）。
  - 持久化 store 必须支持重启恢复，不依赖内存状态或 Agent 会话。
  - v0.13 的 toolbar/sidebar/tab 和 Runs 观察面复用，不重新设计 UI chrome。
- **组织约束**：
  - installed-wheel E2E 和 Louke dogfood 均通过后方可删除旧执行路径和受控回退开关。
  - Spec/AC/Issue/commit hash/artifact digest 等 Trace/Evidence 资产 identity 不因 workflow 变化而重写。

---

## 4. 风险与假设 (Risk & Assumption)

### 4.1 关键假设

| #   | 假设内容                                                                     | 验证方式                                       | 验证负责人 |
| :-- | :--------------------------------------------------------------------------- | :--------------------------------------------- | :--------- |
| 1   | 现有 v0.12 Runtime 核心类库（Store、Catalog、Orchestrator、ProgramStepExecutor）可以无重大重构装配为 production composition root | 代码走查 + 装配原型验证                        | 技术负责人 |
| 2   | v0.13 Web/Chat 的 OpenCode transport 和 SSE streaming 可以可靠接入新 Runtime 的 semantic task dispatch | 集成测试：Chat 中启动 Scribe task 并验证 Runtime state | 技术负责人 |
| 3   | 现有 Git 项目（非 Louke 项目）可以接受 no-new-debt adoption 的 baseline 模型，用户愿意接受"历史问题冻结但不通过"的约束 | 在真实既有项目上试运行 adoption preview        | PM         |
| 4   | return-upstream 的"固定合法目标 + 统一下游 stale"策略覆盖 80% 以上的实际返工场景 | 收集 v0.12/v0.13 开发期间的返工案例并对照验证   | PM         |

### 4.2 主要风险

| #   | 风险描述                                                                           | 影响     | 应对策略                                                                                     |
| :-- | :--------------------------------------------------------------------------------- | :------- | :------------------------------------------------------------------------------------------- |
| 1   | Runtime API 当前可接受客户端提供的 result 字符串，关闭此路径可能影响现有 adapter  | 高       | 逐 adapter 迁移到 program handler 真实执行，设置过渡期标记和 deprecated 警告                  |
| 2   | 从旧 Maestro 驱动切换到自动 Driver 后，隐藏的依赖顺序或副作用可能暴露              | 高       | 先建立完整 responsibility inventory，逐项验证后再注销 Scout/Warden/Keeper                     |
| 3   | no-new-debt adoption 的 baseline 模型可能对既有大型项目过于严格，导致 adoption 失败率高 | 中       | 提供 preview 模式让用户提前评估；必要时允许分步 adoption 或 workspace-level 豁免（v0.17 增强） |
| 4   | installed-wheel E2E 旅程可能因环境差异（Python 版本、OS、网络）而不可复现          | 中       | 使用隔离 venv + 固定依赖版本；CI 中运行 E2E 作为门禁                                          |
| 5   | 重启恢复依赖持久化 store 的完整性；store 损坏或 schema 不兼容可能导致 run 丢失    | 中       | 持久化 store 添加 schema version 和完整性校验；提供只读导出入口                               |

---

## 5. 必要性与冲突 (Necessity & Conflict)

- **已实现？**：否。v0.12 已完成 Runtime 核心类库（Store、Catalog、Orchestrator、ProgramStepExecutor、Gate），但未装配为唯一 production composition root、未接入自动 Driver、未实现完整 `new_feature`/`bug_fix` workflow。v0.13 已完成 Web/Chat/Runs 观察面，但明确将 rollback、waiver、CI interruption 和 workflow reflow 推迟到 v0.14。v0.13.1 已完成安装和 pre-commit 质量门。Scribe prompt/Sage peer 合同已存在，但未接入 Runtime dispatch。Scout/Warden/Keeper 仍存在于 Agent catalog 和 Chat 列表中。
  - 证据：`research-report.md` §3（当前真实实现状态表）；v0.13 story.md:39-40（"本版本不实现：workflow 回退、waive、CI report 中断语义"）。
- **相抵触？**：否。v0.14 是 v0.12/v0.13/v0.13.1 的整合点，不与其目标冲突。v0.12 确立的 Runtime 合同（程序是状态唯一控制者）在 v0.14 中进一步强化为生产现实。v0.13 的 UI chrome 和观察面在 v0.14 中复用。v0.13.1 的安装、AC@version 和 pre-commit 质量门在 v0.14 中继承。
- **结论**：新建。v0.14 是继承 v0.12/v0.13/v0.13.1 的整合版本，不是替代或分叉。往期版本中明确推迟到 v0.14 的能力（return-upstream、waiver、adoption、lifecycle hooks）均为首次实现。

---

## 6. 方案疑议（A/B Advisory，非决策）

- **状态**：无异议。
- **说明**：v0.14 的核心目标（整合 v0.12/v0.13/v0.13.1 + 四项新能力）与往期版本路线一致，无冲突。v0.12 确立的 Human/AI/Program 边界、v0.13 的 UI 设计、v0.13.1 的安装模式在 v0.14 中均被继承和强化，无替代方案需要提出。

---

## 7. 分流结论与门禁 (Gate)

- **分流结论**：Go（Agent 建议）
- **Sage peer review**：PASS；绑定 Story digest：`sha256:4ebac1502e4ef4a842cb264767ed35a2cf45e95349b928bb085589d1f6dbd9a8`；blockers: 0；handoff_ready: true
- **Human 确认**（仅决策点，Agent 已自检其余）：
  - [ ] 分流结论认同（Go / Park / No-Go）
  - [ ] 冲突 / A-B 建议已裁决（无异议）
- **Backlog 登记**：Go → 继续 M-FOUND/M-SPEC 流程

---

## 8. 可追溯种子 (Traceability)

- **Story ID**：`STR-1401`
- **创建时间**：`2026-07-17T00:00:00+08:00`
- **关联 Issue（待填充）**：`#待创建`
- **关联 Spec ID（待填充）**：`#待创建`
- **配套文档**：
  - `research-report.md`：调研报告（研究输入，非规范性合同）
  - `cutover-checklist.md`：生产切换架构与交付约束清单

---

*—— 本故事由 Scribe（M-STORY）于 2026-07-17 生成；经 Sage peer review 且 Human 确认后：Go → 进入后续流程，Park / No-Go → 存档入 Backlog 并标记（story 永久保留，不删除）。*
