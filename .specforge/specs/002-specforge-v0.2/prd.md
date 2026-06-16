# specforge 模型配置 — PRD

## 背景
specforge 定义了 19 个 Agent，每个 Agent 有推荐的模型档位（READMD 第 5 节能力矩阵）。但当前缺少自动化机制让用户在执行 `specforge init` 时配置可用模型，并将模型自动分配给各 Agent。用户目前需要手动查阅能力矩阵表、对照选择模型、再手写配置。

## 目标
让 `specforge init` 在初始化项目时，自动引导用户输入可用的模型列表，specforge 根据能力矩阵（S/A/B/C 档位）打印推荐表，用户手动逐 Agent 指定模型。第一版默认输出 OpenCode 兼容的配置格式。

## 验收标准
- [ ] `specforge init` 运行后，提示用户输入可用模型（模型名称或 provider/model 格式）
- [ ] specforge 根据内置的能力矩阵表，打印推荐表，用户手动逐 Agent 指定模型
- [ ] 输出 OpenCode 兼容的 agent 配置（`.opencode/agents/*.md` 带 frontmatter）
- [ ] 支持国内版和全局版两套模型矩阵（用户选择）
- [ ] 未匹配到相应档位模型时，fallback 到最接近的低档模型

## 非目标（Out of Scope）
- 不支持 Claude Code / Kilo / Codex 的特定格式（v0.2 只支持 OpenCode）
- 不做模型能力评测或自动档位评估
- 不修改 specforge 已有的核心流程逻辑
- 不改变 Agent prompt 内容

## 风险
- 模型矩阵表需硬编码到 specforge 中，新模型发布后需手动更新
- OpenCode 的 agent.md frontmatter schema 可能与 Kilo 不兼容
- 用户输入的模型名称不标准（如拼写错误），分配逻辑需容错

## 关联
- Spec ID: 002-specforge-v0.2
- Project: specforge-v0.2 (#4)
- 相关 Spec: 001-specforge-v0.1 (原始 specforge 流程定义)
