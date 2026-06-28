# ADR 003 — specforge 不引入 feature 分支与 develop 分支

- **日期**: 2026-06-15
- **状态**: 已采纳
- **适用范围**: 所有基于 specforge 的项目仓库

## 背景

传统 Git 工作流（典型如 GitFlow）以"feature 周期长、集成慢"为隐含前提，因此引入了两类分支：

1. **`develop`** —— 把"已完成但未发布"的 feature 攒在一起，等版本冻结后统一 release
2. **`feature/*`** —— 为每一个功能单独建分支，跨几天到几周独占存在

但在 Agent 驱动的开发模式下，**单个 feature 的开发时间从几天到几周缩短到几十分钟到几小时**。这一变化让上述两类分支的边际收益降到负值：

- **`feature/*` 变成过度抽象**：分支创建 → push → PR → review → merge 的固定开销（CI、权限、状态机）在 30 分钟的功能面前成为主要成本
- **`develop` 失去"批量集成"价值**：feature 提交频率高到不需要"攒一批"，每次合并本身就是一次集成

specforge 现有约定已经反映这一判断：`main` + `releases/{version}` + `spec/{spec-id}` + `feat/{spec-id}/{task-id}` + `fix/{n}`，没有 `develop`，也没有外层 `feature/*`。但目前只在 README 末尾的 Rationale 区口头说明，没有形式化决策。

## 决策

明确以下两点为 specforge 的架构级约束，未来 PR 不应引入违反项：

1. **不引入 `develop` 分支**：`releases/{version}` 替代其"集成本版本所有上游产物"的职能；版本之间的隔离通过 release 分支名（`releases/v0.3` vs `releases/v0.4`）而不是 develop / master 的双层主干
2. **不引入外层 `feature/*` 分支**：Forge 的 `feat/{spec-id}/{task-id}` 已经是任务级分支，粒度足够细；如需"跨多 task 的大型 feature"，应在 `releases/{version}` 或 `spec/{spec-id}` 内组织，不另开 `feature/*`

如确实需要跨多天、多人协作的"开发沙盒"，使用 **git worktree** 而非新分支——worktree 不污染远程分支命名空间、不需要 PR 流程、不增加下游 Agent 的分支识别负担。

## 备选方案

| 方案                                            | 评估                                                                                      |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **保留 GitFlow 形态**（加 develop + feature/*） | 拒绝：与 Agent 模式节奏不匹配，引入不必要的合并冲突与状态机                               |
| **保留 develop 不保留 feature/***               | 拒绝：没有 develop 也能工作，加它只是增加分层                                             |
| **保留 feature/* 不保留 develop**               | 拒绝：feature/* 周期短，无独占价值                                                        |
| **采用本文方案**                                | ✅ 采纳                                                                                    |
| **极端方案：主干开发 + worktree**               | 部分采用（worktree 已允许），但不强制——specforge 仍允许 `spec/{spec-id}` 这种"半集成"分支 |

## 后果

### 正面

- 分支命名空间简洁，新人上手快
- 没有"何时合并到 develop / 何时从 develop release"的二次决策
- CI 触发路径清晰：push 到 `releases/{version}` 即触发本版本集成验证
- GitOps 工具（branch protection、auto-deploy）配置简单

### 负面 / 风险

- **`spec/{spec-id}` 分支可能变成"长期半成品分支"**（如果用户答复 Sage 的追问很慢）
  - 缓解：scout/sage 各自 prompt 中应提醒用户在 24 小时内响应，否则视为 spec 已冻结
- **跨 spec 复用没有 GitFlow 的 `feature/*` 那么自由**
  - 缓解：Forge 在 `feat/{spec-id}/TASK-XX` 内部可以引用其他 spec 的产物，但合并顺序由 Archer 任务图保证
- **长期演进的次版本线（v1.x 与 v2.x 并行）不适用**
  - 这是 specforge 的明确边界——本 ADR 不解决此场景，超出 specforge 的设计前提

### 后续如果违反

如果未来某个 spec 真的需要 `develop` 或外层 `feature/*`（例如多代际并行），应：

1. 先用 worktree 验证 1–2 个 cycle，确认问题无法靠现有约定解决
2. 提新 ADR 修订本文档（而不是默默引入新约定）
3. 同步更新 `agents/Maestro.md` 的「分支命名约定」节

## 相关引用

- README §Rationale —— 用户在末尾 Rationale 区域已口头说明本决策，本 ADR 是其形式化
- `agents/Maestro.md` 分支命名约定 —— 当前 4 类分支的具体规则
- `agents/Scout.md` Step 3.5 —— 检查 `releases/*` 合入状态的实现依据本决策
- `agents/Forge.md` —— `feat/{spec-id}/{task-id}` 是本 ADR "不引入外层 feature/*" 的具体落地点
- ADR 002 —— 同一时期关于"开发文档版本管理"的另一架构决策

## 修订历史

- 2026-06-15 v1：初稿，采纳。
