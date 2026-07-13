# v0.12 Product Journey Audit（M-SPEC 探索材料）

> 本文件是需求补全的证据与推理记录，不是已批准 spec、architecture 或 implementation plan。若与 `story.md`、`spec.md`、`acceptance.md` 冲突，以三份正式需求文档在人工审批后的版本为准。

## 目标

用一个问题审计 v0.12：用户从第一次打开 Louke，到创建、评审、批准、执行、恢复、完成并查看历史，是否存在必须手改内部文件、猜状态或绕到终端救火的断点？

## 当前代码证据（2026-07-13）

| 用户旅程 | 当前观察 | 对 v0.12 的含义 |
| --- | --- | --- |
| 初始化后启动 Web | `louke/init.py` 创建目录和模板，但不创建 `.louke/project/project.toml`；`louke/serve.py` 缺该文件直接退出 | 初始化/采用必须形成 server-ready workspace，或提供同等可操作的引导；不能要求用户手写文件 |
| 从主 Web 使用 v0.11 API | `louke/web/app.py:create_app` 只有 home/models/wiki/docs 等路由，没有 mount `opencode_api`、`intent_api`、`backlog_api`、`files_api`、`tasks_api`；v0.11-002 正是该补漏且当前暂停 | v0.12 不能把“已有 sub-app”当成“用户已经能用”；端到端 UI 组装必须属于交付证据 |
| 创建 OpenCode instance | `louke/opencode_api.py` 固定调用 `InMemoryOpenCodeAdapter`；回复为 `echo:`，资源只在进程内存存在 | 必须接真实 adapter、持久 identity、attach/detach/分层退出；mock 只能用于测试且产品必须诚实标记 |
| 调整 Agent model | 当前 models 页已支持拖拽并写 `.louke/models.json`，但语义是用户/项目配置，不绑定 WorkflowRun，也不固化到“下一个 task” | 可复用现有交互，但要新增 run override、task 创建时快照、历史只读和审计语义 |
| 查看项目进度 | 当前事实来源是单一 `project.toml current_stage/spec_id`，没有 Project/WorkflowRun registry、版本化 graph、gate 或 run events | Projects 页面必须读取新 Runtime，而不是从旧 stage 或聊天记录推测 |
| 人类批准 | 当前 Web 有本地用户会话，但没有 requirements approval/M-LOCK 的 artifact digest、stale 检测或批准 UI | gate 的后端强制与用户可完成的审批界面必须同时交付 |
| 失败与完成 | 当前没有 run 级 retry/cancel/archive/resource cleanup；旧 milestone 依赖 Maestro 和命令 | v0.12 必须给出合法恢复/终止动作，并以完成证据决定历史状态 |
| 多项目 Louke 版本 | `install.sh` 固定安装到 `~/.louke/venv` 并把 `~/.local/bin/lk` 链向该环境；`lk upgrade` 只查找并升级当前入口所属 venv；当前没有 workspace root、local/global mode 或 pinned runtime 解析 | v0.12 必须让每个项目固定并隔离 runtime，启动与子任务使用同一 effective identity，并把全局版本降为用户显式选择的兼容模式 |

## 首个可用闭环必须具备的七组能力

1. **初始化与就绪**：`lk serve` 后由 Web init-wizard 完成初始化/采用、首位本地用户、依赖和 model/provider readiness；缺失项可诊断。
2. **可操作项目详情**：图之外提供当前原因、下一动作、产物、审批、session 和事件。
3. **安全生命周期**：失败可恢复，误建可取消，终态可归档，资源清理不删除审计。
4. **完整 workflow**：`new_feature` 与 `bug_fix` 都有明确起点、强制门禁、实现/验证和终点。
5. **证据闭环**：FR/AC 到 task、diff/commit、test result 双向可追溯，缺口阻止完成。
6. **旧版本采用**：预览、显式确认、备份/回滚、legacy 只读；不猜测性恢复。
7. **项目级 Runtime 隔离**：local/global 选择可见且持久，最近 workspace 决定 local 版本，多个项目可同时使用不同版本；损坏 local 不静默换全局，安装/升级需要一致性与恢复证据。

## 不借“可用性”扩张的事项

- 不增加通用 workflow 画布编辑器。
- 不承诺公网多租户、组织权限体系或远程部署。
- 不做浏览器兼容矩阵、移动端和像素级视觉回归。
- 除启动 `lk serve` 外，不把另一条 Louke CLI 作为初始化或配置的唯一路径；init-wizard 在 Web 内完成 Louke 可管理的配置/授权，并诊断操作系统级前置依赖。
- 不在 M-SPEC 指定 local runtime 的物理目录、launcher 实现或具体包管理器；只要求从项目目录可重复解析、隔离、验证并观测 effective runtime。
- 不在 M-SPEC 决定数据库、队列、前端框架、图形库或目录结构。
