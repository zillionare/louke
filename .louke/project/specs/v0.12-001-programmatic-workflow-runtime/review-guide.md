# v0.12-001 M-SPEC Review Guide

> 本页只是 `story.md`、`spec.md`、`acceptance.md` 的评审索引，不取代正式合同，也不能作为人类 requirements approval。目标是先确认少数产品边界，再处理逐条措辞，缩短评审往返。

## 一句话目标

用户从本地 Git workspace 目录启动该项目固定的 Louke（或明确选择兼容的全局版本），可以从 Web 创建 `new_feature` 或 `bug_fix` Project；程序掌握工作流、两次人类门禁和所有权威副作用，Agent 只做语义任务；用户能从创建一路走到验证、发布确认和只读历史，且每个 AC 都有实现与测试证据。

## 已直接来自用户、原则上不再重新发明的边界

1. 程序是 WorkflowRun 状态和合法转移的唯一权威。
2. M-FOUNDATION 程序化，Scout/Warden 不再作为新 workflow 的 Agent/stage。
3. story/spec/acceptance 经用户与 Lex review 后，必须由人类批准，之后才允许 test-plan/architecture/interfaces。
4. 设计文档 review 后仍须 M-LOCK 人类批准，之后才允许实现。
5. sidebar 有 Projects → 当前/历史/创建；详情有 workflow graph 与当前位置。
6. Agent-model 可拖拽修改，已开始 task 不变，下一个 task 生效。
7. 真实 OpenCode 可 detach/attach/分层退出；每步上下文可定制、可追溯。
8. 需求必须落实到实现并由可追溯测试证据验证。
9. 不同项目可以固定并行使用不同 Louke 版本；项目内安装优先，用户明确不采用时允许使用全局版本。

## 用户已确认的 9 个产品决定

| ID                | 当前推荐默认值                                                                                                                                                | 为什么必须现在决定                                          | 主要影响          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ----------------- |
| D1 Project 语义   | 一个 UI Project = 当前 repository/workspace 内的一次开发 workflow；同一 workspace 只允许一个 active 主 Project，已发布产品 hotfix 是并行例外；新需求进入 backlog | 决定列表、identity、分支/worktree 隔离和并发                | FR-1001、NFR-0101 |
| D2 创建 catalog   | 首版只直接创建 `new_feature`、`bug_fix`；不显示 `spec_change`；backlog 可预填后续创建；不创建 GitHub Project，hotfix 引用既有 GitHub Issue                          | 防止入口与实际 workflow 不一致                              | FR-1101、FR-1701  |
| D3 历史策略       | terminal/archived Project 完全只读；首版无原地 resume/retry/fork/物理删除，错误创建走 cancel                                                                  | 决定审计与恢复边界                                          | FR-1201、FR-2001  |
| D4 Model override | 拖拽只写当前 WorkflowRun override；无 override 时继承 Louke Agent 默认；历史只读                                                                              | 决定“下一个 task 生效”的准确作用域                          | FR-1301           |
| D5 首次使用边界   | `lk serve` 后首次打开 setup-only Web，由 init-wizard 完成初始化/采用、首位用户和 readiness；不再要求初始化 CLI 或手写内部文件                                  | 决定未初始化 workspace 如何进入 Web                         | FR-1801、NFR-0401 |
| D6 Bug-fix 分支   | `bug_fix` 专指已有发布产品的 hotfix：必须有 GitHub Issue 并继承既有 spec/AC；quick path 为复现→M-LOCK→R-G-R→回归，需设计时走完整 design，实际新需求退出 hotfix | 这是“固定流程 + 受限动态判断”的首个真实用例                 | FR-0801、FR-1701、FR-2101 |
| D7 收尾确认       | 保留 v0.10 的 human milestone close；它是发布/归档确认，不替代前两次 gate                                                                                     | 避免程序在用户未确认时 tag/publish/close                    | FR-2101           |
| D8 旧版本采用     | v0.10/v0.11 先预览、备份、显式迁移；旧资料作为 legacy history，只凭 `current_stage` 不自动恢复                                                                | 新 Runtime 没有足够证据安全重建旧 run                       | FR-0701、FR-2301  |
| D9 Runtime 来源   | 新项目推荐 local 并固定精确版本；从项目目录解析最近 workspace；只有用户明确选择才使用 global；声明 local 但损坏时 fail closed，不静默回退                    | 决定多项目版本隔离、启动/升级语义和错误是否可被发现         | FR-1801、FR-2401、NFR-0301 |

D1—D9 已映射到正式合同，并由用户在 2026-07-13 批准进入 M-ARCH；下方 threads 保留决策过程。

> **Aaron** [RESOLVED]: D1, 同一 workspace，不允许多个 active project，但 hotfix （已发布产品的 bug）除外。新的需求可以记入 backlog。
>> **Codex**: 已映射到 FR-1001、FR-1101、FR-1701 与 NFR-0101：一个 active 主 Project；已发布产品 hotfix 可并行但全量隔离；新需求进入 backlog。为补齐使用闭环，当前正文规定主 Project 结束后 backlog 条目可预填创建表单、仍需预览确认；若这不是你的意图，请继续回复本 thread。
> **Aaron** [RESOLVED]: D5, lk serve 之后，首次打开，运行 init-wizard 可解决此问题。不使用 cli
>> **Codex**: 已映射到 Story、FR-1801 与 NFR-0301：`lk serve` 在缺少 `project.toml` 时仍启动 setup-only Web，首次访问进入幂等 init-wizard；除启动服务外，不再要求初始化 CLI 或手写内部状态。操作系统级依赖仍可作为前置条件，但向导必须在 Web 内诊断并给出下一动作。
> **Aaron** [RESOLVED]: D6, hot fix 不存在 requirements -- 它们的 requirements 是之前的某个 spec 中定义好的，只是实现出了错误。支持快速流程（必须有 github issue）, RGR。如果需要进行架构设计，则走完整流程。
>> **Codex**: 已映射到 FR-0801、FR-1101、FR-1701、FR-2101 与 FR-2201：hotfix 必须链接 GitHub Issue 和既有已批准 spec/AC；不生成新 requirements/gate；quick path 为复现→M-LOCK→R-G-R→权威回归；需要设计时先走 test-plan/architecture/interfaces review 再 M-LOCK；无法映射既有预期或要求新行为时退出 hotfix、进入 backlog/新需求流程。
> **Aaron** [RESOLVED]: 其它都同意
>> **Codex**: 已据此保留 D2 的两种直接 workflow（并加入你在 D1/D6 指定的 backlog 与既有 Issue 边界），并接受 D3 历史只读、D4 run-scoped model override、D7 human milestone close、D8 显式 legacy migration。请在确认正式正文与这些决定一致后，由 thread initiator 将相应根评论标记 `[RESOLVED]`。
>>> **Aaron**: 好，我批准进入 M-ARCH。

## 明确不进入本轮

- 通用 workflow 画布编辑器
- `spec_change` 直接创建入口和 backlog/GitHub Project 集成
- 历史 run fork/物理删除
- 公网多租户与组织级权限
- 多浏览器兼容矩阵、移动端和像素回归
- 在 M-SPEC 决定数据库、队列、前端框架或图形库

## 当前校验状态

- Lex L1—L5 结构验证：修订后 30/30 FR/NFR、144/144 AC 闭合，五项检查全部通过。
- 第一轮有效 Lex-rubric 语义 review 为 REJECT；修订后完整 re-review 为 `[LEX STAGE1 PASS]`，3 个 Lex blocker threads 均由 initiator 关闭。
- Aaron 已重新批准当前版本：30 条 FR/NFR 均为 `Decided=✅`，6 条 inline threads 均已关闭；进入 M-ARCH 前将重新执行 `quote-check` 作为 gate 记录。OpenCode Lex 空结果及 fallback provenance 详见 `exploration/lex-stage1-attempt.md`。
