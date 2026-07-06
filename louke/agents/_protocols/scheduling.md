# Agent Scheduling Protocol (louke 调度协议)

## 1. 用途

定义 louke 多 agent 在**同一 `releases/{version}` 分支上串行协作**的规则。Maestro 是唯一的调度仲裁者，所有 subagent 必须服从 Maestro 的安排，不自行决定何时写代码、何时评审、何时修复。

**适用场景**:
- Maestro 安排 Devon/Prism/Keeper/Shield 等写代码 agent 的串行顺序
- 任何 agent 发现可能的并发冲突时上报
- 设计 review/gate 修复等写操作的排队规则

## 2. 核心规则

### 2.1 唯一活跃分支

- 每个 version 只有一个活跃开发分支: `releases/{version}`
- 禁止创建任务级分支 (`feat/...`, `fix/...`, `task/...`)
- 禁止在 `releases/{version}` 之外进行功能开发

### 2.2 唯一写者

- 同一时刻，`releases/{version}` 上**只允许一个 agent 产生 commit/push**
- 该写者由 Maestro 显式指定，通常是一个 Devon 实例在处理单个 issue 的 R-G-R 循环
- 其他需要写操作的 agent (Prism/Keeper/Shield 等) 必须经 Maestro 调度，等当前写者完成并 push 后才能接手

### 2.3 读操作窗口

- 当前写者工作期间的**只读审视** (Prism review, Archer 回看, Judge 检查) 也应在 Maestro 调度下进行
- 理想情况下，只读审视在当前写者 R-G-R 三阶段全部 push 后再开始，避免读取到中间不一致状态

### 2.4 任务隔离

- 任务之间以 **commit** 隔离，而非分支
- 每个 R-G-R 阶段一个独立 commit
- 当前处理 issue 的编号应在 commit message 中体现 (`commit-rgr` 自动生成)

## 3. 违反处理

任何 agent 发现以下迹象时，**立即停止当前工作并上报 Maestro**：

- `git log` 中出现非当前任务产生的交错 commit
- CI 上出现多个 PR/工作流同时指向 `releases/{version}`
- 当前工作目录中出现未预期的修改
- 其他 agent 在同一分支上产生了 commit/push

Maestro 决策保留哪一方，必要时回退到上一个一致状态。

## 4. 各 agent 的最小职责

| agent | 职责 |
|---|---|
| **Maestro** | 唯一调度仲裁者；决定谁写、谁读、谁等 |
| **Devon** | 不创建分支；每次处理一个 issue；commit 后立即 push；发现并发冲突立即上报 |
| **Prism** | 不写修复到当前分支，除非 Maestro 显式调度；review 以只读为主 |
| **Keeper** | gate 修复需 Maestro 调度，不插队 |
| **Shield** | e2e 测试写操作需 Maestro 调度 |

## 5. 版本

- v1.0 — 2026-07-05 — 从 Maestro.md 并发约束抽取为独立协议
