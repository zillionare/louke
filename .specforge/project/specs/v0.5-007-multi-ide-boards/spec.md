# 多 IDE Board 支持 — Spec

- **Spec ID**: v0.5-007-multi-ide-boards
- **创建日期**: 2026-06-24
- **状态**: 草稿
- **关联**: 替代 v0.2-002-specforge FR-001..007 (那批从未实施且与本设计冲突)

## 背景

当前 specforge agent prompt 放在 `.specforge/agents/*.md`, 只有 VS Code 通过 `.github/agents/*.agent.md` 软链能识别. 用户在 opencode 里跑 `/agents` 看不到 specforge 的 19 个 agent, 因为 opencode 只扫:

- `~/.config/opencode/agents/` (全局)
- `.opencode/agents/` (项目级)

**实测验证** (2026-06-24, 在 specforge 自己仓里手工生成 18 个 `.opencode/agents/*.md`):
- ✓ opencode `/agents` 列表正确显示
- ✓ 切到 `sage` agent 后, 左下角 model = `ark/kimi-k2.6` (即 model 隔离生效)
- ✓ 卸载 omo 后仍工作 (无 plugin 依赖)

## 目标

把"为每个 IDE 生成它能识别的 agent 文件"这件事抽成 `specforge board <ide>` 子命令, 支持:

- `vscode` (现有 .github/agents/ 软链, 从 cmd_init_new 抽出)
- `opencode` (新增 .opencode/agents/ 生成)
- 未来 `cursor`, `claude` 等

每个 source agent prompt 加 `models` 数组 frontmatter 字段, primary 在 [0], 后面是 fallback 候选. board opencode 把 `models[0]` 翻译成 opencode 原生 `model: ` 字段.

## 用户故事

### US-010
story: 作为 specforge 用户, 我希望在 opencode 中 `/agents` 命令能看到 specforge 的全部 agent, 以便用 opencode 跑 specforge 工作流.
priority: P0

### US-020
story: 作为 specforge 用户, 我希望每个 agent 在 opencode 里**用各自的 model** (S 档 kimi / A 档 deepseek-v4-pro / B 档 glm / C 档 deepseek-flash), 而不是全部用 opencode 全局默认, 以便发挥成本/能力梯度优势.
priority: P0

### US-030
story: 作为 specforge 用户, 我希望 `specforge init .` 能根据本机环境**自动**生成所需 IDE 的 agent 文件 (检测到 .vscode/ 走 vscode 板, 检测到 ~/.config/opencode/ 走 opencode 板), 不需要手动跑.
priority: P0

### US-040
story: 作为 specforge 用户, 我希望显式跑 `specforge board <ide>` 也能生成, 以便后期切 IDE 时不需要重 init.
priority: P1

### US-050
story: 作为 specforge 用户, 我希望 `specforge board status` 能告诉我当前项目装了哪些板, 以便排查 agent 不见的问题.
priority: P2

### US-060
story: 作为 specforge 维护者, 我希望 `models` 数组里的 fallback 候选**只是占位**, 不立即实现 fallback 切换 (opencode 原生不支持; omo 的 `fallback_models` 是 plugin 扩展), 先把数据结构落地.
priority: P1

## 用户使用场景

### scenario-010 新项目 init 自动装两块板

```
$ ls .vscode/                          # 用户有 vscode 配置
settings.json
$ ls ~/.config/opencode/opencode.json  # 也装了 opencode
ok
$ specforge init my-proj
  → 检测到 .vscode/ → 装 vscode 板 → .github/agents/*.agent.md (18 个软链)
  → 检测到 ~/.config/opencode/ → 装 opencode 板 → .opencode/agents/*.md (18 个生成)
```

### scenario-020 已存在项目, 后期手动加 opencode 板

```
$ cd my-existing-proj
$ ls .opencode/                        # 不存在
$ specforge board opencode             # 显式生成
  → 生成 .opencode/agents/{sage,lex,...}.md
$ specforge board status
  vscode    ✓ (18 agents in .github/agents/)
  opencode  ✓ (18 agents in .opencode/agents/)
```

### scenario-030 源 agent prompt 修改后, 刷新各 IDE 板

```
$ vim .specforge/agents/Sage.md        # 改了 description 或 body
$ specforge board opencode             # 重生成, 幂等
  [=] .opencode/agents/sage.md (refreshed)
```

## 功能需求

### FR-010 source agent prompt 加 `models` 与 `mode` frontmatter

每个 `.specforge/agents/*.md` (specforge 自身仓为 `agents/*.md`) frontmatter 必须包含:

```yaml
---
name: sage
description: 需求澄清与 spec 撰写 — 把 story 翻译为可追踪的 spec
mode: all                    # primary / subagent / all (默认 all, 等同 opencode 原生)
models:                      # specforge 自定义: primary [0] + fallback
  - kimi-k2.6                # primary (抽象名, 不带 provider 前缀)
  - deepseek-v4-pro          # fallback 1
  - glm-5.2                  # fallback 2
---
```

> Aaron： models 仅使用 kimi-k2.6这样的名字，它是一个抽象的模型名，并不是具体的模型 ID，也不要加 provider 前缀。如何绑定到具体的模型，我不知道，请建议。
>> **Sage:** 同意, source 改用抽象名 (cross-user / cross-provider). 绑定方案: 加两层架构 + 新 `specforge models` 子命令 (见 FR-080/090):
>>
>> 1. **抽象层** (source agent): `models: [kimi-k2.6, deepseek-v4-pro, glm-5.2]`
>> 2. **绑定层**: 用户本机 `~/.specforge/models.json` 或项目级 `.specforge/models.json` 存 alias map, 如:
>>    ```json
>>    {
>>      "kimi-k2.6":         "ark/kimi-k2.6",
>>      "deepseek-v4-pro":   "ark/deepseek-v4-pro",
>>      "glm-5.2":           "ark/glm-5.2",
>>      "deepseek-v4-flash": "ark/deepseek-v4-flash"
>>    }
>>    ```
>>    (国外用户可能映射成 `anthropic/claude-opus-4-5` / `openai/gpt-5` 等)
>> 3. **板生成时**: `specforge board opencode` 查 alias map, 把抽象名翻译成 opencode 全名写到 `.opencode/agents/sage.md` 的 `model:` 字段; 找不到对应键则报错并提示 `specforge models bind <抽象名> <opencode 全名>`
>> 4. **首次 init 时**: 若 `~/.specforge/models.json` 不存在, 走 interview (复活 v0.2-002 已废弃的 FR-001~005 思路, 见 FR-090)
>>
>> 这样 source 跨 user / 跨 provider 一致, 不需要改 18 个文件; 用户本机 alias 一次性配好即可. 
>>> Aaron: alias map 如何配置？用户手工改？用户如何知道 opencode 中配置了哪些模型（provider/model），如果有 API 可获得 List，能否智能化关联？
>>>> **Sage:** 调查后确认: `opencode models` 命令存在且**机器可读**（一行一个 `provider/model-id`, stdout 直接 grep 即可）. 所以**用户完全不需要手填**, specforge 可以智能匹配:
>>>>
>>>> **匹配算法** (`specforge models doctor` / `init` interview / `models bind` 都用):
>>>> 1. 对 source 用到的每个抽象名 (如 `kimi-k2.6`), 取归一化 key: 小写去标点 → `kimik26`
>>>> 2. 调 `opencode models 2>/dev/null`, 对每行 (如 `ark/kimi-k2.6`) 取末段小写去标点 → `kimik26`
>>>> 3. 完全相等 → **strong match** (直接用)
>>>> 4. 包含关系 (抽象名是 model 末段子串) → **weak match** (提示用户确认)
>>>> 5. 无匹配 → **fail**, 让用户从全表里选, 或 `models bind` 显式指定
>>>>
>>>> **实测** (你本机, 配了 ark provider 5 个 model + opencode 内置 ~45 个):
>>>>   - `kimi-k2.6` → strong match `ark/kimi-k2.6` ✓ (也 strong match `opencode/kimi-k2.6`, 多重时选 user provider 优先 `ark` 而非 `opencode` 内置, 见匹配规则)
>>>>   - `deepseek-v4-pro` → strong match `ark/deepseek-v4-pro` ✓
>>>>   - `glm-5.2` → strong match `ark/glm-5.2` ✓
>>>>   - `deepseek-v4-flash` → strong match `ark/deepseek-v4-flash` ✓
>>>>
>>>> 即**你的环境零配置开箱即用** — init 不用 interview, 直接调 `opencode models` 跑一遍智能匹配, 写到 `~/.specforge/models.json`. 用户感知到的就是 "specforge init 完了, 它就工作". ✓
>>>>
>>>> 多重 strong match (user provider + opencode 内置) 时优先级:
>>>> 1. 用户项目级 `models.json` 显式绑定
>>>> 2. 用户级 `~/.specforge/models.json` 显式绑定
>>>> 3. **opencode 中非 `opencode/` 前缀的 provider** (用户自己配的 ark / openai / anthropic 等, 一般是 pay-per-token 直连)
>>>> 4. `opencode/` 前缀 (opencode 官方 subscription)
>>>>
>>>> 这样用户配的国内 ark 优先于 opencode 内置, 避免 subscription token 消耗.

**约束**:
- `models` 至少 1 个元素 (primary 必填)
- `models[0]` = primary; fallback 仅作占位 (opencode 原生不消费; 将来 omo plugin 模式可消费)
- `name` 仍保留 (specforge 自己工具用, 文件名也独立维护)
- `mode` 默认 `all` (specforge 现阶段不强制 primary/subagent 分层, US-040 之前讨论的 Maestro 自动编排是 v0.6 后续话题)

档位 → primary model 默认值 (抽象名, 与具体 provider 解耦):

| 档  | Agents                                                                              | primary             | fallback                             |
| --- | ----------------------------------------------------------------------------------- | ------------------- | ------------------------------------ |
| S   | Maestro, Sage, Lex                                                                  | `kimi-k2.6`         | `deepseek-v4-pro`, `glm-5.2`         |
| A   | Probe, Judge, Archer, Cynic, Herald, Arbiter, Warden, Hunter, Shield, Prism, Keeper | `deepseek-v4-pro`   | `kimi-k2.6`, `glm-5.2`               |
| B   | Scout, Forge                                                                        | `glm-5.2`           | `deepseek-v4-pro`                    |
| C   | Librarian, Guide                                                                    | `deepseek-v4-flash` | `glm-5.2`                            |

> **注**: 上表是 specforge 出厂默认值. 用户在本机或项目级 `models.json` 里把抽象名映射到自己的 provider (国内默认 ark, 国外可换 anthropic/openai/google). 见 FR-080/090.
> Aaron: 同上，模型只给抽象名字。比如 kimi-2.6, glm-5.2
>> **Sage:** 已确认, 上表已改成抽象名 (无 `ark/` 前缀). 具体 provider 绑定由 `~/.specforge/models.json` (用户本机 alias map) 完成, 不在 source 里硬编码. ✓

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### FR-020 新增 `specforge board <ide>` 子命令

```
specforge board <ide>           # 生成指定 IDE 的 agent 板
specforge board status          # 列出当前项目装了哪些板
specforge board <ide> --dry-run # 预览
```

`<ide>` 当前支持: `vscode`, `opencode`. 未来扩展: `cursor`, `claude`.

退出码:
- 0 = 成功 (或 dry-run)
- 1 = 未知 ide
- 2 = 当前目录不是 specforge 项目 (无 `.specforge/agents/` 也无 `agents/`)

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### FR-030 `board opencode` 生成 `.opencode/agents/*.md`

行为:

1. 定位 source 目录:
   - 优先 `.specforge/agents/` (installed project)
   - fallback `agents/` (specforge 自身仓, dev mode)

2. 对每个 `*.md` 文件 (跳过 `README.md`, `ROSTER.md`):
   - 解析 frontmatter, 取 `description` / `mode` / `models`
   - 生成 `.opencode/agents/{lowercase-name}.md`, frontmatter:
     ```yaml
     ---
     description: <copied>
     mode: <copied or 'all'>
     model: <models[0]>
     ---
     <body copied>
     ```
   - opencode 原生 frontmatter **不带 `models` 字段** (opencode 不识别会引发警告)

3. `.gitignore` 追加 `.opencode/agents/` (本地生成物, 不入库; 与 `.github/agents/` 规则一致)

4. **幂等**: 重跑无副作用, 同名文件覆盖 (因为是从 source 重生成)

5. **不破坏用户手工添加的 opencode agent**: 只处理 source 里有名字对应的文件; 用户在 `.opencode/agents/` 里手工放的不在 source 名单的 *.md 不动

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### FR-040 `board vscode` 抽取现有逻辑

把 `cmd_init_new` 与 `cmd_init_adopt` 里的 `.github/agents/*.agent.md` 软链逻辑抽到 `cmd_board vscode`. init 现在变成: 创建目录 → 拷贝 source → 调 `cmd_board <detected-ide>` (FR-060).

软链相对路径保持: `.github/agents/sage.agent.md → ../../.specforge/agents/Sage.md`. (跟现状一致)

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### FR-050 `board status` 输出

```
$ specforge board status
vscode    ✓  (.github/agents/ — 18 agent symlinks)
opencode  ✓  (.opencode/agents/ — 18 agent files)
cursor    -  (not installed)
```

每行: `<ide>` + `✓` / `-` + 简述. `✓` 必须同时满足:
1. 板目录存在
2. 至少有 1 个 agent 文件
3. (vscode) 文件是软链, 目标存在
4. (opencode) 文件 frontmatter 含 `model:` 字段

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### FR-060 init 自动探测 IDE 并装板

`cmd_init_new` 与 `cmd_init_adopt` 在拷贝 source 完毕后, 自动探测并装板:

| 探测条件                                                | 装的板     |
| ------------------------------------------------------- | ---------- |
| `.vscode/` 在项目里存在                                 | `vscode`   |
| `~/.config/opencode/opencode.json` 或 `.opencode/` 存在 | `opencode` |
| 都没有                                                  | 不装       |

新增 init flag `--board=<csv>` 覆盖自动探测:
- `--board=opencode,vscode` 强制装两个
- `--board=none` 都不装
- `--board=opencode` 只装 opencode (即便项目有 .vscode/)

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### FR-070 18 个 source agent 加上 `models` 与 `mode`

按 FR-010 档位表, 把现有 18 个 `agents/*.md` 的 frontmatter 加上 `models` 与 `mode`. ROSTER 与 README 不动 (描述性文件, 无需 model 信息).

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### FR-080 抽象名 → provider 全名的自动发现 + alias override

绑定分 3 层, **前两层显式 override, 第三层自动发现**:

| 优先级 | 来源 | 用途 |
|---|---|---|
| 1 (高) | `<project>/.specforge/models.json` | 项目级显式覆盖 |
| 2 | `~/.specforge/models.json` | 用户本机显式默认 |
| 3 (低) | `opencode models` | 自动发现, 零配置 |

显式 alias 文件格式 (可选, 没有也能工作):

```json
{
  "$schema": "specforge://models-alias",
  "version": 1,
  "aliases": {
    "kimi-k2.6": "ark/kimi-k2.6"
  }
}
```

`specforge board opencode` 的 model resolve 流程:
1. 解析 source `models[0]` (抽象名, 如 `kimi-k2.6`)
2. 查项目级 `.specforge/models.json` (有则直接用)
3. 查用户级 `~/.specforge/models.json` (有则直接用)
4. 若仍未命中, 调 `opencode models 2>/dev/null`, 得到一行一个 `provider/model-id`
5. 对抽象名和每个 model-id 末段做 normalize (小写, 去掉 `._-/` 等标点), 完全相等为 strong match
6. strong match 只有 1 个 → 直接用
7. strong match 多个 → 按 provider 优先级选:
   1. 非 `opencode/` 前缀的用户自配 provider (如 `ark/`, `anthropic/`, `openai/`)
   2. `opencode/` 前缀 (官方 subscription)
   3. 若仍并列, 取字典序最小, 并 warning
8. 无 strong match 但有 weak match (包含关系) → 交互确认; 非 tty 下 fail
9. 无匹配 → fail, 提示 `opencode models` 可用列表 + `specforge models bind <abstract> <full>` 手动绑定

新增 `specforge models` 子命令:

```
specforge models list                              # 列出 source 用到的抽象名 + resolve 结果
specforge models doctor                            # 检查未绑定/冲突/弱匹配, 给出建议
specforge models bind <abstract-name> <full-name>  # 写入 ~/.specforge/models.json (override)
specforge models bind <abstract-name> <full-name> --project  # 写项目级 override
specforge models unbind <abstract-name>            # 删除用户级绑定
```

约束:
- `models.json` 不再是必需文件, 只是 override
- 自动发现依赖 opencode CLI; 若 opencode 不在 PATH, board opencode fail 并提示安装/配置 opencode
- board vscode 不需要 model resolve

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### FR-090 init 首次运行的 model resolve

`specforge init` 不再问 region/interview. 规则:

1. 如果本次会生成 opencode board (auto-detect 或 `--board=opencode`), 在 board 前自动运行 `specforge models doctor --ide=opencode --fix-auto`
2. `--fix-auto` 对 strong match 自动写入 `~/.specforge/models.json` (作为缓存, 下次不再调用 `opencode models`)
3. 只有遇到 weak match 或 no match 才进入交互:

```
source model alias: kimi-k2.6
Found candidates from `opencode models`:
  [1] ark/kimi-k2.6          (strong, user provider)
  [2] opencode/kimi-k2.6     (strong, opencode subscription)
Choose [1]:
```

非 tty 时:
- strong match 多个 → 按 FR-080 provider 优先级自动选
- weak/no match → fail, 提示 `specforge models bind`

因此用户正常路径是零配置:

```
specforge init my-proj
  → 检测到 opencode
  → opencode models
  → 自动匹配 kimi-k2.6/deepseek-v4-pro/glm-5.2/deepseek-v4-flash
  → 写 ~/.specforge/models.json 缓存
  → board opencode 生成 .opencode/agents/*.md
```

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

## 非功能需求

### NFR-010 向后兼容

现有 `.github/agents/*.agent.md` 软链规则不变, vscode 用户升级到 0.5.2 不需要重做任何事 (再跑 init 也只是幂等覆盖).

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### NFR-020 provider 解耦

source `models` 数组里**只放抽象名** (如 `kimi-k2.6`, `glm-5.2`), **不带 provider 前缀**. 抽象名 → 全名的映射由用户本机/项目级 `models.json` (FR-080) 完成, specforge 不限定 provider.

ADR 008 记录: 抽象名 → 默认 alias map 的内容, 与"为什么 source 不绑 provider"的理由.

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### NFR-030 测试覆盖

`tests/test_board.bats` (新增) 包含:

- BOARD_T01: `specforge board opencode` 在新项目生成 18 个文件
- BOARD_T02: 生成的文件 frontmatter 含 `model:` 且 = alias-resolve(source `models[0]`)
- BOARD_T03: 生成的文件 body 与 source body 一致 (sha256)
- BOARD_T04: 幂等 - 重跑无变化
- BOARD_T05: `board vscode` 生成软链, 目标可达
- BOARD_T06: `board status` 显示已装板与未装板
- BOARD_T07: `board <unknown-ide>` 退出码 1
- BOARD_T08: init 自动探测 .vscode/ 装 vscode 板 (现有测试改写为通过 board 流程实现)
- BOARD_T09: init 自动探测 ~/.config/opencode/ 装 opencode 板
- BOARD_T10: init --board=none 跳过自动探测
- BOARD_T11: init --board=opencode 显式只装 opencode

`tests/test_models.bats` (新增) 包含:

- MODELS_T01: `specforge models list` 列出 source 用到的全部抽象名
- MODELS_T02: `specforge models doctor` 调 `opencode models` 自动 strong-match
- MODELS_T03: 多个 strong match 时, 非 `opencode/` provider 优先于 `opencode/` provider
- MODELS_T04: `specforge models bind X Y` 写入 `~/.specforge/models.json` override
- MODELS_T05: `specforge models bind X Y --project` 写入项目级 override 且优先级高于用户级
- MODELS_T06: `specforge models unbind X` 删除用户级绑定
- MODELS_T07: `board opencode` 使用 resolve 后的 full model 写 `model:`
- MODELS_T08: `board opencode` 在 no-match 且非 tty 时 fail 并提示 `models bind`
- MODELS_T09: `models doctor --fix-auto` 把 strong match 写入 `~/.specforge/models.json` 缓存
- MODELS_T10: `opencode models` 不存在时 `board opencode` fail, board vscode 不受影响

`tests/test_init.bats` 与 `tests/test_init_adopt_flow.bats` 现有断言保持通过 (NFR-010).

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### NFR-040 ADR 留痕

新增 `.specforge/wiki/decisions/008-multi-ide-boards.md`, 含:

- 背景 (specforge agent 在 opencode 不可见 + cross-provider 抽象需求)
- 决策 (board 子命令 + 抽象 models 数组 + models.json alias map 两层架构)
- 抽象名 → 默认 alias 表 (国内 region preset)
- 备选 A: 在 source 直接写 `ark/kimi-k2.6` (拒绝, 不跨 provider)
- 备选 B: omo plugin 模式 (拒绝, 强依赖 omo)
- 备选 C: 把 alias 写在 source frontmatter (拒绝, 每改 provider 要改 18 个文件)
- 后果 (18 个 source agent 改 frontmatter; 新增 `models` 子命令; init 首次 interview)

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### NFR-050 关闭关联的旧 issue

实施后关闭以下 v0.2 残留 issue (`spec 002-specforge-v0.2` 从未实施, 本 spec 是其更优的取代):

- #18 [FR-001] 交互式收集逗号分隔的可用模型列表 → 由 FR-090 init interview 取代
- #19 [FR-002] 交互式选择国内版/全局版模型策略 → FR-090 region 选项取代
- #20 [FR-003] 打印推荐表并让用户手动指定每个 Agent 模型 → FR-010 档位表 + FR-080 alias map 取代
- #21 [FR-004] 生成 OpenCode 兼容的 agent 配置 → FR-020/030 `board opencode` 取代
- #22 [FR-005] 模型配置持久化到 .specforge/models.json → FR-080 `models.json` 取代
- #23 [FR-006] 可用模型不足时自动降档到低档模型 → 留作 backlog, fallback 由 plugin 实现 (本 spec 仅落地 `models[]` 数据结构)
- #24 [FR-007] init 输出 onboarding 指引 → 已由 cmd_init_new 现有 `下一步` 输出实现 (cc49718 之后)

每条以 commit ref 关闭并加 comment 说明对应到本 spec 的哪个 FR.

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
