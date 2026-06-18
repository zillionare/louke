# ADR 005 — VS Code / GitHub Copilot 自定义 Agent 集成

- **日期**: 2026-06-17
- **状态**: 已采纳（既存行为形式化）

## 背景

`specforge init`（无论是 `init <name>` 新建模式还是 `init .` adopt 模式）会把 specforge 框架自带的 19 个 agent prompt 文件拷贝到项目本地 `.specforge/agents/{Name}.md`。

GitHub Copilot for VS Code 支持 "custom agent"，要求 agent prompt 文件位于 `.github/agents/{Name}.agent.md`（注意双扩展名）。直接把 19 个文件拷成两份会造成同步漂移。

## 决策

`specforge init` 在检测到目标目录下存在 `.vscode/` 时，自动为每个 agent 在 `.github/agents/{Name}.agent.md` 创建一条**相对软链**指向 `.specforge/agents/{Name}.md`。

```text
.github/agents/Sage.agent.md  →  ../../.specforge/agents/Sage.md
.github/agents/Lex.agent.md   →  ../../.specforge/agents/Lex.md
…（19 个软链全部使用相对路径）
```

同时在项目 `.gitignore` 追加：

```text
.github/agents/
.specforge/agents/
.specforge/templates/
```

理由：

- `.github/agents/`：这是给 VS Code 看的本地视图，由 init 重建即可，不应入库。
- `.specforge/agents/`、`.specforge/templates/`：framework 副本，由 init 重建即可，与项目无关。
- **`.specforge/project/` 故意不在 ignore 列表中** — 那是项目产出物（`project-info.md`、`specs/{spec-id}/...`），必须随项目入库。

## 不做的事

- **install / uninstall 都不会触碰 `.specforge/project/`** — 进入 init 流程时若 `.specforge/project/` 已存在则保留原状；卸载时只清理 framework 副本（`.specforge/agents/` `.specforge/templates/` `.github/agents/`），`.specforge/project/` 保留。
- 不为非 VS Code 编辑器（JetBrains、Neovim 等）创建对应软链；后续若需要支持，应通过 `--editor=` 显式声明。

## 影响面

- `bin/specforge` `cmd_init_new` / `cmd_init_adopt`：实现上述软链与 gitignore 写入；adopt 模式下把整段 `.specforge/` 一次性 ignore 的旧逻辑改为只 ignore `agents/` `templates/` 两个子目录。
- `tests/test_init_adopt_flow.bats` `FR14_T0[1-5]`：断言新 gitignore 内容、并显式断言 `.specforge/project/` 没被 ignore。

## 备选方案

1. 不创建软链，让用户手动复制 — 易漂移。
2. 用硬拷贝 — 修改 `.specforge/agents/X.md` 后 `.github/agents/X.agent.md` 不同步。
3. 软链放到全局 `$SPECFORGE_HOME` — 跨贡献者机器不可移植。
4. **采用：相对软链 + 项目级 `.gitignore`**（本决议）。
