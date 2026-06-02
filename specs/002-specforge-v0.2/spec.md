# specforge 模型配置 — Spec

- **Spec ID**: 002-specforge-v0.2
- **创建日期**: 2026-06-02
- **状态**: 评审中

## 用户故事

| ID | 故事 | 验收条件 | 优先级 |
|----|------|---------|--------|
| US-001 | 作为 specforge 用户，我想在 `init` 时输入可用模型列表，以便 specforge 自动为各 Agent 匹配合适模型 | 交互式提示后，`.opencode/agents/` 下生成带 frontmatter 的 19 个 agent 文件 | P0 |
| US-002 | 作为 specforge 用户，我想选择国内版或全局版模型策略，以便适配我的模型可用环境 | 选择后 specforge 使用对应能力矩阵进行匹配 | P0 |
| US-003 | 作为 specforge 用户，我想手动为每个 Agent 指定模型，以便精确控制模型分配 | 打印推荐表后，用户可逐 Agent 输入模型名 | P0 |

## 功能需求

> **锚点约定（必读）**：每个 FR 单元前必须有显式 HTML 锚点 `<a id="fr-XXX"></a>`（小写、3 位零填充）。

<a id="fr-001"></a>
**FR-001**: specforge init 交互式收集可用模型列表，输入方式为逗号分隔的字符串（如 `deepseek-v4-pro, gpt-5.5, kimi-k2.6`）  可测试性: ✅

<a id="fr-002"></a>
**FR-002**: init 交互式询问区域策略（国内版 / 全局版），用户选择后加载对应能力矩阵  可测试性: ✅

<a id="fr-003"></a>
**FR-003**: 根据用户选择的区域和可用模型，打印推荐表（Agent 名称 → 推荐档位 → 推荐模型），供用户手动为每个 Agent 指定模型  可测试性: ✅

<a id="fr-004"></a>
**FR-004**: 用户手动指定后，生成 OpenCode 兼容的 agent 配置文件到 `.opencode/agents/*.md`，frontmatter 包含 `model`、`description`、`mode`（默认 `all`）三个字段  可测试性: ✅

<a id="fr-005"></a>
**FR-005**: 模型配置持久化到 `.specforge/models.json`，记录区域策略、可用模型列表、Agent→模型映射  可测试性: ✅

<a id="fr-006"></a>
**FR-006**: specforge init 输出 onboarding 指引文本（已有功能 v0.1），并在指引中说明后续 Agent 加载方式  可测试性: ✅

## 非功能需求

| ID | 需求 | 指标 |
|----|------|------|
| NFR-001 | 模型矩阵数据与实际代码解耦，便于后续更新 | 能力矩阵存为独立数据文件（JSON/YAML），不硬编码在主逻辑中 |
| NFR-002 | init 交互过程有明确的输入校验和错误提示 | 非法输入时给出具体修复指引 |

## 澄清记录（Sage Interview 产出）

| # | 问题 | 用户回答 |
|---|------|---------|
| Q1 | OpenCode agent.md frontmatter 含哪些字段？ | model + description + mode（全量，Kilo 兼容） |
| Q2 | 国内版/全局版选择方式？ | 交互式询问（init 过程打印选项） |
| Q3 | 用户输入可用模型的方式？ | 逗号分隔字符串（如 `gpt-5.5, deepseek-v4-pro`） |
| Q4 | 同一档位多个可用模型时的选择策略？ | 不做自动匹配，打印推荐表让用户手动为每个 Agent 指定 |
| Q5 | project-info.md 多 spec 共存设计？ | 不允许并发开发多需求，project-info.md 直接替换为新 spec 信息 |
| Q6 | 模型配置是否持久化？ | 是，写入 `.specforge/models.json` |

## Lex 审核结果

- [ ] 所有需求可追踪到用户故事
- [ ] 所有需求可断言（有明确的测试方法）
- [ ] 没有模糊词汇
- [ ] 所有 FR 都有显式锚点 `<a id="fr-XXX"></a>`
