# 008 — 多 IDE Board 与抽象模型名

- **状态**: 已采纳
- **日期**: 2026-06-25
- **关联 spec**: v0.5-007-multi-ide-boards

## 背景

specforge 的 agent prompt 放在 `.specforge/agents/`，VS Code 通过 `.github/agents/*.agent.md` 软链可识别，但 OpenCode 只扫描 `.opencode/agents/*.md` 与 `~/.config/opencode/agents/*.md`，因此默认看不到 specforge 的 Sage/Lex/Maestro 等 agent。

同时，agent 的推荐模型不能在 source 中写成 `ark/kimi-k2.6` 这类 provider 绑定 ID。不同用户可能使用 ark、opencode subscription、anthropic、openai、google 或其它 provider。source 必须跨 provider。

## 决策

### 1. 引入 board 子命令

`specforge board <ide>` 负责生成 IDE 能识别的 agent 板：

- `specforge board vscode` → `.github/agents/*.agent.md`
- `specforge board opencode` → `.opencode/agents/*.md`
- `specforge board status` → 显示当前项目板状态

`init` 自动探测 IDE 并调用 board；用户也可后续手动运行。

### 2. Source agent 只写抽象模型名

每个 source agent frontmatter 加：

```yaml
mode: all
models:
  - kimi-k2.6
  - deepseek-v4-pro
  - glm-5.2
```

`models[0]` 是 primary，后面是 fallback 候选。source 不写 provider 前缀。

### 3. 具体 provider/model 自动发现

OpenCode 提供机器可读命令：

```bash
opencode models
```

输出一行一个 `provider/model-id`。specforge 使用这个列表把抽象名解析成真实模型：

- `kimi-k2.6` → `ark/kimi-k2.6` 或 `opencode/kimi-k2.6`
- `deepseek-v4-pro` → `ark/deepseek-v4-pro`
- `glm-5.2` → `ark/glm-5.2`

匹配规则：

1. 抽象名与 model-id 末段 normalize 后完全相等 → strong match
2. 多个 strong match 时，优先非 `opencode/` provider（用户显式配置的 provider）
3. 无 strong match 时，允许用户通过 `specforge models bind` 显式绑定

### 4. models.json 只作 override/cache

两层配置：

- 用户级：`~/.specforge/models.json`
- 项目级：`.specforge/models.json`（优先级更高）

用途：

- 保存自动发现的结果，减少重复调用 `opencode models`
- 允许用户覆盖默认解析
- 允许用户更新 agent/tier → 模型链 assignment

## 默认档位

| 档 | Agents | primary | fallback |
|---|---|---|---|
| S | Maestro, Sage, Lex | `kimi-k2.6` | `deepseek-v4-pro`, `glm-5.2` |
| A | Probe, Judge, Archer, Cynic, Herald, Arbiter, Warden, Hunter, Shield, Prism, Keeper | `deepseek-v4-pro` | `kimi-k2.6`, `glm-5.2` |
| B | Scout, Forge | `glm-5.2` | `deepseek-v4-pro` |
| C | Librarian, Guide | `deepseek-v4-flash` | `glm-5.2` |

## 备选

### A. Source 直接写 `ark/kimi-k2.6`

拒绝。绑定了 maintainer 当前 provider，不跨用户、不跨地区。

### B. 依赖 oh-my-openagent

拒绝。omo 是完整 OpenCode plugin，包含 Hashline、LSP、AST、Team Mode、MCP、hooks 等。specforge 只需要 OpenCode 原生 agent 发现与 model 隔离，不应该强依赖 omo。

### C. 让用户手工编辑 `.opencode/agents/*.md`

拒绝。生成物会漂移，升级不可控。

## 后果

- 新增 `specforge board` 与 `specforge models` 两组命令
- 18 个 agent prompt frontmatter 增加 `mode` 与 `models`
- OpenCode 用户无需 omo 即可看到 specforge agents
- 若用户不满意默认映射，可通过 `specforge models bind` 或 `specforge models assign` 覆盖
