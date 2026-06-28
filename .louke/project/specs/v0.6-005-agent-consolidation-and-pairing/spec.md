# v0.6-005 — Agent 命名重构（角色 + 智力双维度）— Spec

- **Spec ID**: v0.6-005-agent-consolidation-and-pairing
- **创建日期**: 2026-06-26
- **状态**: 草稿（命名方案待 Aaron 拍板）
- **关联**: v0.6-001-rebrand-to-quanti-forge

## 背景

在软件开发中，我们可以看到有以下流程：

1. 项目奠基。决定本次开发使用的 base brach, 本此发布的版本号、分支等基础设施。
2. 需求定义与澄清。需求可能从一个故事或者 PRD 开始，直到转化成一条条具体的、可以测试的需求结束。这些需求可能是功能性的，也可能是非功能性的（为了完成用户故事必须的、辅助性的）。最终输出是相互印证的 spec, acceptance和测试计划文档。
3. 设计阶段。根据2得到的文档，进行接口和架构设计。在 Agent 开发场景下，人类从这一步起开始淡出。人类可能还需要 review 下 interface 文档，但理论上，可以完全不管架构设计 -- 这是 Agent 应该去做、应该去试的部分。极端地，即使 Agent 设计出来的架构不工作，他们也应该有能力换一个 -- 但必须满足 spec 要求。
4. 构建阶段。这是代码生产的主要阶段。代码有功能代码、单元测试代码和e2e 代码。功能代码与单元测试代码应该由同一 Agent 来编写，但 e2e 代码需要另有其人来编写。
5. 构建阶段还涉及到大量、频繁的 code review，以及要决定哪一个 FR 先做，哪一个后做等等。
6. 需求需要通过 project 管理方法划分成为一个个 milestone。它的意义是，我们可以获得阶段性的成果，这对回滚来说很重要。由于 spec 之间互有依赖，这需要一个很强的架构师来决定。
7. 每个 milestone 结束，就应该打上 tag
8. 所有 milestone 完成，单元测试覆盖率超过约定，e2e 全部跑通，本次开发即可收尾
9. 技术作家入场，结合项目记忆，story, spec 等，撰写用户文档。
10. build master 准备打包发布。

Maestro - 负责协调、推进。

quanti-forge 当前有 **18 个 agent**（含 ROSTER.md + 17 个角色文件，3108 行），命名存在三个问题：

1. **配对不直观**：`Sage` 与 `Lex`、`Hunter` 与 `Shield` 命名看不出"成对儿"
2. **职责不可见**：看到名字不知道它在干什么（例如 `Herald` 是什么？）
3. **智力不显式**：看到名字不知道该配什么级别模型（强/弱）

Aaron 2026-06-26 的命名准则：

> 1. **反映角色的作用**：例如 `Maestro` — 看名字就知道是指挥、有协调能力、智力也不弱
> 2. **反映角色的智力**：看名字就知道大致该用哪个级别的模型
>
> 个别角色很难同时满足以上两点，**尽力追求**。

Aaron 暂未拍板最终方案，本 spec 列出**多个候选方案** + 评估，等 Aaron 决策后再进入实施。

## 命名准则（Aaron 2026-06-26 定稿）

### 准则 1：反映作用（必须）

- 名字本身要**让人知道这个角色做什么**
- 看到名字能立刻判断"它是设计者 / 实现者 / 守门者 / 协调者"
- 必要时配**副标题/标题**（中文括注）强化作用

### 准则 2：反映智力（必须）

- 名字暗示**大致智力级别**，以便用户/调度器自动选模型
- 三档：
  - **强**（claude-sonnet-4 / deepseek-v4-pro / glm-5.2）：复杂推理、架构设计、产出完整 spec
  - **中**（claude-haiku-4.5 / deepseek-v4 / gpt-4o）：常规审核、守门、按清单检查
  - **轻**（claude-haiku-3.5 / gpt-4o-mini / deepseek-v4-mini）：格式校验、关键词扫描、清单勾选

> 准则 2 是软约束：用户可手动覆盖模型，命名只提供默认建议。

### 准则 3：配对可视化（保留旧目标）

- 实施者 ↔ 验收者名字上有视觉关联（不强制 -ie，可考虑其它方案）
- 配对的目的：对话中说"Scout 通过了"用户立刻知道"那 Scoutie 也通过了吗"

## 候选命名方案（待 Aaron 决策）

### 方案 A：**-ie 后缀约定**（原方案，保留参考）

| 角色 | 实施者 | 验收者 (-ie) | 智力暗示 |
|---|---|---|---|
| Story/PRD | Scout | Scoutie | Scout 中 / Scoutie 轻 |
| Interview | Sage | Sagie | Sage 强 / Sagie 中 |
| Test Plan | Probe | Probie | Probe 中 / Probie 轻 |
| 执行规划 | Archer | Archerie | Archer 强 / Archerie 中 |
| 任务执行 | Forge | Forgeie | Forge 强 / Forgeie 中 |
| Bug 修复 | Hunter | Hunterie | Hunter 中 / Hunterie 轻 |
| 指挥 | Maestro | — | 强 |
| 方法论 | Guide | — | 中 |
| 验收汇总 | Herald | — | 中 |

**评估**：
- ✅ 配对可视化强（差一个 `ie`）
- ✅ 智力暗示清晰（无 `-ie` = 实施者，强；`-ie` = 验收者，弱/中）
- ⚠️ 部分词根读音奇怪（Archerie、Hunterie 拼写长）
- ⚠️ 元角色（Maestro/Guide/Herald）不参与配对，规则不统一

**变体 A1**：Aaron 在 2026-06-26 后续反馈中提到"还没定"，所以这是参考方案。

### 方案 B：**-er / -ie 双后缀（实施/守门）**

| 角色 | 实施者 | 守门者 | 智力暗示 |
|---|---|---|---|
| Story/PRD | Scout | Scoutie | 强 / 轻 |
| Interview | Sage | Sageie / Sagie | 强 / 中 |
| Test Plan | Prober | Probier | 强 / 轻 |
| 执行规划 | Archer | Archerie | 强 / 中 |
| 任务执行 | Forger | Forgeie | 强 / 中 |
| Bug 修复 | Hunter | Hunterie | 强 / 轻 |
| 指挥 | Maestro | — | 强 |
| 方法论 | Guider | — | 中 |

**评估**：
- ⚠️ -er 后缀对部分词根不自然（Prober 听起来奇怪）

### 方案 C：**角色 + 智力双标签**（如 Scout-Pro / Scout-Lite）

| 角色 | 实施者 | 守门者 |
|---|---|---|
| Story/PRD | Scout-Pro | Scout-Lite |
| Interview | Sage-Pro | Sage-Lite |
| Test Plan | Probe-Pro | Probe-Lite |
| 执行规划 | Archer-Pro | Archer-Lite |
| 任务执行 | Forge-Pro | Forge-Lite |
| Bug 修复 | Hunter-Pro | Hunter-Lite |
| 指挥 | Maestro-Pro | — |
| 方法论 | Guide-Mid | — |

**评估**：
- ✅ 智力暗示**最显式**（-Pro/-Lite 直接说明）
- ⚠️ 名字变长（10+ 字符）
- ⚠️ 失去"昵称感"，更像工具名

### 方案 D：**守门者用"-Guard"后缀**

| 角色 | 实施者 | 守门者 |
|---|---|---|
| Story/PRD | Scout | ScoutGuard |
| Interview | Sage | SageGuard |
| Test Plan | Probe | ProbeGuard |
| 执行规划 | Archer | ArcherGuard |
| 任务执行 | Forge | ForgeGuard |
| Bug 修复 | Hunter | HunterGuard |
| 指挥 | Maestro | — |
| 方法论 | Guide | — |

**评估**：
- ✅ "Guard" = 守卫，强语义
- ⚠️ "Guard" 暗示强智能（实际验收者是轻模型），语义矛盾

### 方案 E：**实施者 + Watcher 守门者**（来自 Aaron 思路的混合）

| 角色 | 实施者 | 守门者 |
|---|---|---|
| Story/PRD | Scout | ScoutWatcher |
| Interview | Sage | SageWatcher |
| Test Plan | Probe | ProbeWatcher |
| 执行规划 | Archer | ArcherWatcher |
| 任务执行 | Forge | ForgeWatcher |
| Bug 修复 | Hunter | HunterWatcher |
| 指挥 | Maestro | — |
| 方法论 | Guide | — |

**评估**：
- ✅ "Watcher" = 监视者，弱智能职责明确
- ⚠️ 13 字符，仍偏长

### 方案 F：**保持 -ie 但强化智力暗示**（融合方案）

| 角色 | 实施者 (强/中) | 验收者 (-ie, 轻) |
|---|---|---|
| Story/PRD | Scout (中) | Scoutie (轻) |
| Interview | Sage (强) | Sagie (轻) |
| Test Plan | Probe (中) | Probie (轻) |
| 执行规划 | Archer (强) | Archerie (中) |
| 任务执行 | Forge (强) | Forgeie (中) |
| Bug 修复 | Hunter (中) | Hunterie (轻) |
| 指挥 | Maestro (强) | — |
| 方法论 | Guide (中) | — |

每个 agent 的 YAML frontmatter 加 `tier: pro|middle|lite` 显式标注，便于 `quanti_forge_board.py` 自动调度。

**评估**：
- ✅ -ie 配对 + tier 智力双维度
- ✅ 用户可一眼识别配对（差一个 `ie`）+ 通过 tier 字段看智力
- ⚠️ 仍是 13 字符内，复合词为主

## 推荐方案

**方案 F（融合方案）**：保留 `-ie` 配对约定（满足 Aaron 的核心构想）+ 显式 `tier` 字段标注智力。

**理由**：
1. 配对可视化最强（差一个 `ie`，符合 Aaron "一眼成对" 的核心需求）
2. 智力通过 `tier:` frontmatter 字段显式声明，比靠名字猜测更可靠
3. 元角色（Maestro/Guide）保持单名，配对规则不强制适用于元角色
4. 配对映射表（哪个 -ie 替代哪个旧评审）已在 Aaron 反馈中确认

## 削减方案（与命名独立）

无论选哪个命名方案，**agent 总数都建议削减到 13**：

- 6 实施 + 6 -ie 验收 + Maestro = 13
- **Aaron 决策**：Guide 砍掉 → 职责并入 Sagie；Herald 砍掉 → 职责并入 Scoutie
- 旧评审（Warden/Lex/Judge/Cynic/Keeper/Prism/Shield）**全部消失**，被对应 -ie 替代

## 用户故事

### US-010
story: 作为 quanti-forge 用户，我希望看到 agent 名字就知道它在干什么（作用），以便对话引用时立刻定位角色。
priority: P0

### US-020
story: 作为 quanti-forge 用户，我希望看到 agent 名字就知道它大致应该用什么级别模型（智力），以便调度器自动选模型。
priority: P0

### US-030
story: 作为 quanti-forge 用户，我希望实施者 ↔ 验收者配对在名字上一眼可识别，以便对话中提到"Scout 通过了"立刻知道还要看 Scoutie。
priority: P0

### US-040
story: 作为 quanti-forge 用户，我希望 agent 总数 ≤15，以便新用户上手成本可控。
priority: P1

## 功能需求

### FR-010 命名方案落地

**采纳方案 F**：
- 实施者：保留原名（`Scout`, `Sage`, `Probe`, `Archer`, `Forge`, `Hunter`, `Maestro`, `Guide`）
- 验收者：实施者名 + `ie`（`Scoutie`, `Sagie`, `Probie`, `Archerie`, `Forgeie`, `Hunterie`）
- 元角色：保留原名（`Maestro`, `Guide`）

AC: `ls agents/*.md` 含 13 个非 ROSTER 文件 + ROSTER.md。

### FR-020 智力 tier 标注

每个 agent 的 YAML frontmatter 加 `tier:` 字段：

| Tier | 智力 | 默认模型 |
|---|---|---|
| `pro` | 强 | claude-sonnet-4, deepseek-v4-pro, glm-5.2 |
| `middle` | 中 | claude-haiku-4.5, deepseek-v4, gpt-4o |
| `lite` | 轻 | claude-haiku-3.5, gpt-4o-mini, deepseek-v4-mini |

**示例**（agents/Sagie.md）：

```markdown
---
name: sagie
description: 验收 spec.md 完整性 + 方法论问答（替代 Lex + Guide）
tier: lite
mode: all
models:
  - claude-haiku-3.5
  - deepseek-v4-mini
  - gpt-4o-mini
---
```

AC: 每个 agent 的 frontmatter 含 `tier: pro|middle|lite` 字段。

### FR-030 旧 agent 文件处理（shim 机制）

- 旧 `agents/{Warden,Lex,Judge,Cynic,Keeper,Prism,Shield,Arbiter,Herald,Guide}.md` 全部改为 shim
- shim 模板：

```markdown
---
name: {old-name}
description: [已替代] 本 agent 已被 v0.6-005 重构
---

# ⚠️ 本 agent 已被 v0.6-005 重构

- 原职责 → `agents/{NewName}.md`（如 Warden → Scoutie）
- 本文件保留 30 天作为回退路径
```

- 30 天后清理 shim

AC: `cat agents/Warden.md` 含"已替代"或"已合并"字样；shim 不含完整 prompt。

### FR-040 ROSTER.md 重写

新表格 13 行（含 Maestro）：

| 阶段 | 实施者 (tier) | 验收者 (tier) |
|---|---|---|
| 全程 | **Maestro** (pro) | — |
| Story/PRD | **Scout** (middle) | **Scoutie** (lite) |
| Interview | **Sage** (pro) | **Sagie** (lite, 含 Guide 职责) |
| Test Plan | **Probe** (middle) | **Probie** (lite) |
| 执行规划 | **Archer** (pro) | **Archerie** (middle) |
| 任务执行 | **Forge** (pro) | **Forgeie** (middle) |
| Bug 修复 | **Hunter** (middle) | **Hunterie** (lite) |

> **Herald 合并入 Scoutie**：最终验收汇总由 Scoutie 输出
> **Guide 合并入 Sagie**：方法论问答由 Sagie 响应

AC: `agents/ROSTER.md` 表格 7 行数据 + tier 列。

### FR-050 bats 测试更新

- 旧 agent 引用更新到新名（除 shim 验证）
- 新增 `tests/test_agent_naming.bats`（6 个 case）：
  1. 每个 Name 有 Nameie 配对（pair coverage = 6/6）
  2. 每个 agent frontmatter 含 `tier:` 字段
  3. -ie 版 tier ∈ {lite, middle}（不能是 pro）
  4. 旧评审 agent (Warden/Lex/Judge/Cynic/Keeper/Prism/Shield/Arbiter) 全是 shim
  5. shim 含"已替代"或"已合并"
  6. ROSTER.md 表格含所有 13 个 agent + tier 列

AC: `bats tests/*.bats` 0 失败；新 `test_agent_naming.bats` 6/6 通过。

### FR-060 ADR 记录 -ie 约定 + tier 字段

**新 ADR**：`.quanti-forge/wiki/decisions/013-agent-ie-pairing-and-tier.md`

**必含段**：
1. 背景：配对不直观 + 模型成本问题
2. Aaron 命名准则（两条 + 尽力追求）
3. 候选方案 A-F + 评估
4. 最终选择：方案 F
5. 配对表 + tier 表
6. 元角色处理（Herald→Scoutie, Guide→Sagie）
7. 回退方案（30 天 shim）

AC: ADR 文件存在 + 含 7 段必含内容。

## 验收标准

| ID | 描述 | 验证 |
|---|---|---|
| AC-010 | agent 文件数 = 13 | `ls agents/*.md \| grep -v ROSTER \| wc -l` = 13 |
| AC-020 | 每个 Name 有 Nameie 配对 | pair coverage = 6/6 |
| AC-030 | 每个 agent 含 tier 字段 | frontmatter 解析出 tier ∈ {pro, middle, lite} |
| AC-040 | -ie 版 tier ≠ pro | tier 字段值校验 |
| AC-050 | 旧评审 agent 是 shim | `cat agents/Warden.md` 含"已替代" |
| AC-060 | ROSTER.md 表格 7 行 | `grep -c '^\|' agents/ROSTER.md` ≥ 10 |
| AC-070 | ADR 已写 | `.quanti-forge/wiki/decisions/013-agent-ie-pairing-and-tier.md` 存在 |
| AC-080 | bats 全过 | `bats tests/*.bats` 0 失败 |

## 任务拆解

```
T1. Aaron 拍板命名方案（本 spec 等待）
T2. 写 ADR 013 (含候选方案评估)
T3. 起草 6 个新 -ie agent prompt (含 tier 字段)
T4. 把旧评审 (Warden/Lex/Judge/Cynic/Keeper/Prism/Shield/Arbiter/Herald/Guide) 内容合并到对应新 agent
T5. 17 个旧 agent 文件改 shim
T6. 重写 ROSTER.md (7 行 + tier 列)
T7. 新增 tests/test_agent_naming.bats (6 case)
T8. 更新所有 bats tests 中 agent 引用
T9. 跑全量 bats
T10. commit + ADR
```

## 风险

- **R-010** Aaron 还没拍板最终命名方案（候选 A-F），本 spec 是**决策挂起**状态
  → spec 列出所有候选 + 评估，等 Aaron 选择
- **R-020** `tier:` 字段是软约定，工具不强制
  → `tools/quanti_forge_board.py` 读取 tier 并 fallback 到 models 列表
- **R-030** 用户已习惯旧名，新名映射需要过渡
  → 30 天 shim + ADR 含"旧名→新名对照表"
- **R-040** 部分 -ie 名读音奇怪（Archerie）
  → 文档明示"读作 ar-cher-ee"，避免误读

## 关联 spec

- v0.6-001-rebrand：旧 prompt 中 `specforge` 字符串同步换为 `quanti-forge`
- v0.6-003-quanti-forge-web：`/agents` 配置页同步新 agent 名 + tier 字段
- v0.6-004-cron-llm-wiki：cron 默认用 `-ie` 配对的 lite 模型（节约 token）
