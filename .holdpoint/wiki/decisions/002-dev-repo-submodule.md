# ADR 002 — 用私有 {repo}-dev 仓做项目内开发文档的版本管理

- **日期**: 2026-06-04
- **状态**: Proposed（未采纳，仅记录想法）

## 背景

即使项目是开源的，开发过程中产生的部分文档（spec、test-plan、task-plan、acceptance、`specs/project-info.md` 等）也不应该对外公开：

- 这些是项目**演进过程**的产物，不是最终用户文档
- 内部讨论、试错思路、临时决策记录暴露出去会误导用户
- 但它们仍需要版本管理（与 spec issue、commit hash 关联、回溯历史）

目前的做法是把 `specs/` 提交到主仓的 `main`，这等同于把开发过程透明化了。

## 备选方案

1. **现状**：`specs/` 提交到主仓
2. **本 ADR 提议**：另开 `{repo}-dev` 私有仓，通过 submodule 嵌入主仓
3. 纯本地 `specs/` 不入库：丧失版本管理，协作不可行
4. 加密后入库：密钥管理、CI 兼容性都是坑；不推荐

## 决策（拟）

采用方案 2：

- 新建私有仓 `{owner}/{repo}-dev`（specforge 即 `zillionare/specforge-dev`），由 owner 维护
- 在主仓下增设 submodule 路径，存放 `specs/`（含 `project-info.md`、`{spec-id}/` 等）
- 公共可见的"项目文档"另起路径（如 `docs/`），只放最终面向用户的内容
- `specforge init` 增加一步询问："是否启用 `{repo}-dev` 子模块？"，默认 yes
- 拥有 `{repo}-dev` 读权限的 owner/contributor：clone 时自动 submodule update，修改 spec 后 commit 推到 `{repo}-dev`
- 无 `{repo}-dev` 权限的 contributor：submodule 目录为空，`specforge` 各 Agent 应能在该目录缺失时优雅降级（读不到 spec 不应阻塞 issue 流程）
- 所有 spec 相关 issue / PR 引用保持原样（`specs/{id}/spec.md` 路径不变），owner 在 push 前确保内容已合并到 `{repo}-dev`

## 优势

- 项目代码保持 100% 开源可读
- 开发过程文档（草稿 spec、面试记录、PR 讨论）天然隔离
- 仍享受 git 版本管理、commit hash 引用、code review
- 已有 GitHub 权限模型直接复用（私有仓 + collaborator 列表）

## 代价 / 风险

- **新仓维护成本**：要再开一个 repo、写好 README、写 access 文档
- **Agent 兼容性**：当前所有 Agent 默认读 `specs/{id}/spec.md`，submodule 未初始化时（contributor 视角）必须降级——需要修改 Sage/Lex/Probe/Archer/Herald 的 fallback 行为
- **submodule 的常见痛点**：clone 时忘了 `--recurse-submodules`、commit hash 漂移、被 IDE 当成普通目录处理
- **owner 视角的"两份提交"**：改 spec 时既要 commit 到 `{repo}-dev`，又要 update 主仓的 submodule 指针——多一步心智
- **协作 issue 引用**：contributor 在 issue 里贴 spec 路径时，看到的内容可能跟 owner 不一致

## 现状

暂不实施。后续触发条件（满足任一）：

- 主仓出现需要"对外保密"性质的 spec 草稿（如未发布的破坏性设计）
- 社区 contributor 增加，开始出现"不期望暴露给用户的过程信息被看到"的反馈
- v0.3 之后，spec 数量超过 5–8 个，`specs/` 目录体积成为可读性负担

触发后，从 Proposed → Accepted，再走 §2.2 正常 spec 流程立项。

## 后续如果实施

1. 创建 `zillionare/specforge-dev` 私有仓
2. 迁移 `specs/` 内容（保留 commit 历史：`git filter-repo --path specs/ --path specs/project-info.md`）
3. 主仓删 `specs/` 目录，加 `.gitmodules` 指向 `{repo}-dev`
4. `specforge init` 模板更新：submodule 设置步骤写入 `install.sh`
5. 修订 Agent prompt（Sage / Lex / Probe / Archer / Herald / Herald）加入 submodule 缺失时的 fallback
6. 更新 README §8 用户手册
