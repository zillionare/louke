# fix-001a — e2e 环境启动契约（Archer 决定）

- **Fix ID**: fix-001a
- **日期**: 2026-07-06
- **作者**: Kilo (经 Aaron 拍板 + glm 评审)
- **关联**: 替代 fix-001 草案（原 fix-001 合并了"环境契约"+"并行执行"两件事，本 fix 只保留前者）
- **关联 spec**: v0.6-005 agent-consolidation, v0.7-001 pre-commit-quality-gates

> **拆 fix 决策**：原 fix-001 包含 (A) e2e env 契约 + (B) Shield/Devon 并行执行。glm 评审指出 (B) 有 4 个阻断性问题（§107 硬约束、merge 顺序逻辑矛盾、`shell=True` 安全、叠加在有 bug 的文件上），且 (B) 的价值/复杂度比存疑。本 fix 只保留 (A)。(B) 推迟到 fix-001b，独立评估。

---

## 0. 前置依赖

### 0.1 (前置 fix-000) project-info.md 历史归档 + parser bug 修复

**glm 评审指出的现有 bug**：`louke/maestro.py:_read_project_info(label)` 逐行扫，返回**第一个匹配**，不分版本段。当 `project-info.md` 含多个 `## vX.Y` 版本段时，永远返回最早版本的字段值（如 `Repo` 字段返回 v0.1 的 `zillionare/specforge` 而非 v0.7 的 `zillionare/louke`）。5 个 parser（maestro / scout / sage / lex / verify_acceptance）都有此问题。

**修复方向**（独立 spec，本 fix 不实施）：
- `project-info.md` 只含**当前活跃版本**字段（无 `## vX.Y` 段头）
- 归档版本段移到 `history.md`（人类查阅，agent 不解析）
- M-MILESTONE 触发：Maestro 把当前段移入 `history.md`，清空 `project-info.md`
- `_read_project_info` 改为"匹配最新段头下的字段"或"无段头即整文件"

**为什么是前置**：本 fix 在 `project-info.md` 加新字段 `[e2e]` 段（实际拆出去后改写 `project.toml`，见 §2.1）。但其他后续 fix 都依赖 project-info.md parser 正确。先修前置，再做本 fix。

### 0.2 本 fix 不做并行执行

**明确划清边界**：本 fix 不涉及 Shield 与 Devon 的 worktree 并行、不涉及 Maestro 调度顺序变更、不涉及 §107 硬约束修改。这些属于 fix-001b，独立 spec 评估。

---

## 1. 问题陈述

### 1.1 当前 e2e 运行环境是隐式的

`louke/shield.py:cmd_run_e2e` 调用 e2e 时，需要 running project。但：

- **谁决定如何启动项目**？文档中没有契约
- **谁决定如何知道 project 就绪**？文档中没有契约
- **谁决定如何 teardown**？文档中没有契约

实际项目启动方式多样（`docker-compose up` / `make e2e-env-up` / `npm run dev`），就绪检测多样（HTTP poll / log pattern / healthcheck endpoint）。**当前没有任何地方记录这些**，用户每次跑 e2e 都要手动串联命令。

### 1.2 当前 shield.py 已删除 quality-gates.toml 残留

v0.7-001 后，`shield.py:_load_quality_gates` / `_load_e2e_config` 已被删除（Qoder 评审发现残留），改为内置默认 + `--config <path>` flag（v0.7-001 后引入但**未实际使用**）。

### 1.3 根因

e2e 的"开发"和"运行"被混淆：

| 维度                     | e2e 开发                     | e2e 运行                      |
| ------------------------ | ---------------------------- | ----------------------------- |
| 谁做                     | Shield                       | CI / 本地用户                 |
| 何时                     | M-E2E 阶段                   | tag 触发 / merge 后           |
| 是否需要 running project | ❌ 不需要                     | ✅ 需要                        |
| 依赖                     | `interfaces.md` + 技术栈决策 | running project + e2e scripts |

**e2e 运行需要"启动项目"**，但启动方式由项目自身决定（Makefile / docker-compose / npm scripts），Louke 不应发明项目结构，只应**记录如何调用**。

---

## 2. 目标

1. **职责清晰**：Archer 在 M-ARCH 决定 e2e env 启动方式；Shield 只写脚本；CI 按契约执行
2. **机器可读**：用 `tomllib` 直接解析，零 regex
3. **项目原生约定**：不发明项目结构；直接复用 `Makefile` / `npm run` / `docker-compose.test.yml`
4. **可降级**：缺失 `[e2e]` 段时本地/CI 走默认（sleep 30s 等就绪 + 无 teardown）
5. **安全**：`shell=False` + `shlex.split`，避免 `shell=True` 注入风险

---

## 3. 契约变更

### 3.1 新文件 `.louke/project/project.toml.toml`

**与 `project-info.md` 分离的原因**（glm 评审 §Q1）：
- `project-info.md`：人类可读元数据（Story / Repo / Smoke Test），5 个 parser 已用 `- **Label**: value` 行级 regex
- `project.toml.toml`：**新增**，机器可解析工具配置（e2e env，未来扩展 CI / hook 等）
- 不嵌入 markdown：避免 regex 抽取 TOML 块的脆弱性（heading 格式偏差时静默失败）

**Schema**：

```toml
# .louke/project/project.toml.toml
# 由 Archer 在 M-ARCH 阶段产出; shield.py / CI 解析.
# 全部字段可选; 缺失时本地/CI 走默认.

[e2e]
# 启动项目 (CI/本地 e2e 前跑)
start = "make e2e-env-up"

# 等项目就绪 (start 后跑; 命令 exit 0 表示就绪)
ready = "curl -sf http://localhost:8000/health"
ready_timeout_seconds = 60   # 默认 60

# e2e 框架 (playwright | testclient | db; 缺失时 Shield 从 deps 推断)
framework = "playwright"

# 浏览器 (playwright 框架时; 其他框架忽略)
browsers = ["chromium"]

# 清理 (e2e 后必跑, 无论成功失败; 缺失则跳过)
teardown = "make e2e-env-down"
```

**字段语义**：
- `start`：项目**已存在的命令**（make target / npm script / docker-compose 文件）；不发明项目结构
- `ready`：返回 0 即就绪；非 0 重试直到 `ready_timeout_seconds` 过期
- `ready_timeout_seconds`：默认 60
- `framework`：playwright / testclient / db；Shield scaffold 据此选模板
- `browsers`：playwright 模式下指定浏览器列表
- `teardown`：缺失则不清理（CI 环境下资源自动回收）

### 3.2 Archer.md 新增 §6.5

```markdown
### 6.5. E2E Environment 契约 (M-ARCH 阶段产出)

你还要决定 e2e 测试环境的启动方式，写入 `.louke/project/project.toml.toml` 的 `[e2e]` 段。

**字段**（全部可选）：

- `start`：启动项目的命令（必须复用项目**已存在的命令**：Makefile target / npm script / docker-compose 文件）
- `ready`：检测项目就绪的命令（exit 0 = 就绪）
- `ready_timeout_seconds`：超时秒数（默认 60）
- `framework`：playwright / testclient / db（Shield 据此选 scaffold 模板）
- `browsers`：playwright 框架时指定浏览器
- `teardown`：清理命令（缺失则不清理）

**约束**：

- 命令必须引用项目**已存在**的入口；不发明项目结构
- 如果项目无现成的启动方式，**不**写 `start`（让 e2e 默认跳过启停，要求用户手动）
- raw session 中保留 quote dialogue：来源 = spec interfaces.md + 项目 Makefile/package.json
- 与 `project-info.md` 分离：人类可读元数据 vs 机器可解析工具配置
```

### 3.3 shield.py `run-e2e` 改动

**新增 `run-e2e --no-env` flag**：跳过自动启停（用户已手动启动项目）。

**实现要点**（`louke/shield.py`）：

```python
import shlex
import time

CONFIG_PATH = Path.cwd() / '.louke' / 'project' / 'project.toml.toml'


def _read_e2e_env_from_config() -> dict:
    """从 .louke/project/project.toml.toml 读 [e2e] 段. 用 tomllib 直接 load, 零 regex."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return {}
    try:
        with open(CONFIG_PATH, 'rb') as f:
            return tomllib.load(f).get('e2e', {})
    except Exception as e:
        print(f'[shield] project.toml.toml 解析失败: {e}', file=sys.stderr)
        return {}


def _run_command(cmd_str: str, cwd: Path) -> int:
    """安全执行 shell 命令 (shell=False + shlex.split, 防注入)."""
    if not cmd_str or not cmd_str.strip():
        return 0
    try:
        args = shlex.split(cmd_str)
    except ValueError as e:
        print(f'[shield] 命令解析失败: {cmd_str!r} ({e})', file=sys.stderr)
        return 1
    return subprocess.run(args, cwd=cwd, shell=False, check=False).returncode


def cmd_run_e2e(args):
    """运行 e2e 测试. 默认按 project.toml.toml [e2e] 段启停项目."""
    cwd = Path.cwd()
    cfg = _default_e2e_config(args.spec)

    env = {} if args.no_env else _read_e2e_env_from_config()
    start = env.get('start', '').strip()
    ready = env.get('ready', '').strip()
    teardown_cmd = env.get('teardown', '').strip()
    ready_timeout = int(env.get('ready_timeout_seconds', 60))

    # 1. Start
    if start:
        print(f'[e2e] start: {start}')
        rc = _run_command(start, cwd)
        if rc != 0:
            print(f'[e2e] start failed (rc={rc})', file=sys.stderr)
            return rc

    # 2. Wait ready (轮询 ready 命令)
    if ready:
        print(f'[e2e] waiting ready ({ready}, timeout {ready_timeout}s)')
        deadline = time.time() + ready_timeout
        while time.time() < deadline:
            if _run_command(ready, cwd) == 0:
                print('[e2e] ready')
                break
            time.sleep(2)
        else:
            print(f'[e2e] timeout waiting ready ({ready_timeout}s)', file=sys.stderr)
            _run_command(teardown_cmd, cwd)
            return 1

    # 3. Run e2e
    cmd = [cfg['command'], *cfg['args'], cfg['path']]
    cmd = [c.replace('{browser}', args.browser) for c in cmd]
    print(f'[e2e] run: {" ".join(cmd)}')
    rc = subprocess.run(cmd, cwd=cwd, shell=False, check=False).returncode

    # 4. Teardown (无论成功失败)
    if teardown_cmd:
        print(f'[e2e] teardown: {teardown_cmd}')
        _run_command(teardown_cmd, cwd)

    return rc
```

**关键安全改动**（glm 评审 §阻断 #3）：
- **删除** `--config <path>` flag（v0.7-001 后引入但未用）
- **新增** `--no-env` flag（跳过自动启停）
- **改** `subprocess.run(shell=True)` → `shell=False + shlex.split(cmd_str)`：即使 `project.toml.toml` 被篡改，也无法注入 shell 元字符

**CLI 变更**：

```
# 旧
lk shield run-e2e [--spec SPEC] [--browser {chromium,firefox,webkit}]
                  [--config CONFIG]            # v0.7-001 后引入, 未使用

# 新
lk shield run-e2e [--spec SPEC] [--browser {chromium,firefox,webkit}]
                  [--no-env]                    # 跳过自动启停, 用户已手动启动
```

### 3.4 Shield.md 契约变更

**当前**：本地验证（`lk shield run-e2e`）是无条件的"启动项目 + 跑 e2e"。

**变更**：本地验证**默认自动启停**（按 `project.toml.toml`）；用户想手动启动项目时加 `--no-env`。

```markdown
## 本地验证 (M-E2E 阶段本地手动验证)

1. 默认自动启停：`lk shield run-e2e` 读 `project.toml.toml [e2e]` 段，按 start/ready/teardown 顺序执行
2. 手动启动项目：用户先跑 `make e2e-env-up` 等，然后用 `lk shield run-e2e --no-env` 跳过自动启停
3. 默认 timeout 60s（`ready_timeout_seconds`）；超时后自动 teardown 并退出非零
```

### 3.5 受影响组件

| 文件                               | 改动                                                                                                                                          | 优先级 |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| `louke/shield.py`                  | `run-e2e` 删 `--config`；加 `--no-env`；新增 `_read_e2e_env_from_config` + `_run_command`（shlex + shell=False）；从 `project.toml.toml` 解析 | P0     |
| `louke/agents/Archer.md`           | 新增 §6.5 E2E Environment 契约                                                                                                                | P0     |
| `louke/agents/Shield.md`           | 本地验证步骤改写（默认自动启停 / `--no-env` 跳过）                                                                                            | P0     |
| `.louke/project/project.toml.toml` | **新建**：模板文件由 `lk init` 部署到新项目（包含 `[e2e]` 注释示例）                                                                          | P1     |
| `README.md` / `README.zh.md`       | 加 "e2e 环境约定" 章节                                                                                                                        | P2     |

---

## 4. 兼容性

**Breaking changes**：
- `lk shield run-e2e --config <path>` 删除（v0.7-001 后引入，未广泛使用）

**非 breaking**：
- `lk shield run-e2e --spec` / `--browser` flag 不变
- `project.toml.toml` 不强制存在（缺失时降级：sleep 30s + 无 teardown）
- M-E2E / M-ARCH / M-DEV 流程不变
- `project-info.md` 不动（仅独立新增 `project.toml.toml`）

---

## 5. 验证

| 场景                                          | 预期                                                   | 验证方式                                                                                                  |
| --------------------------------------------- | ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| Archer M-ARCH 填 `[e2e]` → shield.py 自动启停 | start → wait ready → 跑 e2e → teardown                 | fixture: 起 python http.server，验证 ready poll + teardown                                                |
| 项目无 `project.toml.toml` → 走默认           | 提示"无 e2e env 配置"；sleep 30s 后跑 e2e；无 teardown | fixture: tmp dir 无 config 文件，验证降级路径                                                             |
| `project.toml.toml` 含恶意命令                | `shell=False` + `shlex.split` 阻止注入                 | fixture: `start = "rm -rf /tmp/test; echo pwned"` 验证只执行 `rm -rf /tmp/test` 报错，不执行 `echo pwned` |
| `--no-env` 跳过启停                           | 立即跑 e2e，不读 config                                | manual                                                                                                    |
| ready 超时                                    | 60s 后自动 teardown + exit 1                           | fixture: ready 命令永远返回 1                                                                             |

---

## 6. 实施步骤

### Phase 0: 前置 (glm 评审指出的更紧急项)
1. **fix-000**: 修 `project-info.md` 历史归档 + parser bug（独立 spec）

### Phase 1: 契约落地 (本 fix)
2. **Archer.md** 加 §6.5
3. **Shield.md** 改本地验证步骤
4. **shield.py** 改 `run-e2e` + 加 `_read_e2e_env_from_config` + `_run_command` (shlex 安全)

### Phase 2: 部署
5. `lk init` 模板加 `project.toml.toml`（含 `[e2e]` 注释示例）
6. README 加章节

### Phase 3: 后续（独立 spec）
7. **fix-001b**: Shield/Devon worktree 并行（待评审 §7 收敛）

---

## 7. 与其他 fix / spec 关系

| fix / spec                                 | 关系                                                               |
| ------------------------------------------ | ------------------------------------------------------------------ |
| `fix-000-project-info-history`             | **前置**。先修 parser bug 再做本 fix                               |
| `fix-001b-shield-parallel`                 | **后续**。本 fix 不并行；并行需独立 spec                           |
| `v0.7-001-pre-commit-quality-gates`        | **正交**。v0.7-001 解决 commit-time gate；本 fix 解决 e2e env 启动 |
| `v0.7-002-knowledge-distillation-karpathy` | 无关                                                               |
| `v0.6-009-agent-permission-tightening`     | 间接相关。Shield 在 worktree 仍受 permission 约束（未来 fix-001b） |
| `v0.6-016-quote-dialogue-protocol`         | Archer §6.5 引用 raw session 留 quote dialogue                     |

---

## 8. 待 review 问题

1. **`[e2e]` 字段是否足够？** 未来扩展：是否需要 `[e2e.test]` / `[e2e.lint]` / `[ci]` 等？目前只 e2e，未来 spec 加。
2. **`framework` 字段是否冗余？** Shield 已经能从 deps 推断（playwright 在 deps → playwright）。删字段 vs 显式更好？倾向保留（用户可显式覆盖推断）。
3. **CI 是否同步接入？** 本 fix 不包含 CI workflow。CI 接入可在 fix-001b 一起做（CI 触发也需要 worktree 决策）。当前 fix 只解决"本地"使用场景。
4. **timeout 是否需要分别配置？** `ready_timeout_seconds` vs `e2e_timeout_seconds`（e2e 本身的超时）。当前只 ready_timeout。e2e 自身超时由 pytest/playwright 配置管。

---

## 附录 A: glm 评审意见响应

| glm 评审                         | 我的回应                                                     |
| -------------------------------- | ------------------------------------------------------------ |
| Q1: TOML or YAML? 建议拆两个文件 | ✅ 接受。改用 `project.toml.toml` 独立文件，零 regex 解析     |
| Q2: history split 是更紧急的 bug | ✅ 接受为前置 fix-000，独立 spec                              |
| Q3: §107 硬约束冲突              | ✅ 接受。本 fix 不并行（拆出 fix-001b），无需碰 §107          |
| 阻断 #1: §107 未改               | ✅ 已通过拆分规避                                             |
| 阻断 #2: merge 顺序逻辑混乱      | ✅ 已通过拆分规避（fix-001b 再处理）                          |
| 阻断 #3: `shell=True` 注入风险   | ✅ 接受。改 `shell=False` + `shlex.split`                     |
| 阻断 #4: 叠加在有 bug 的文件     | ✅ 接受。改用独立 `project.toml.toml`，不碰 `project-info.md` |

glm 评审的所有意见都已纳入正文。**glm 评审完全正确**——尤其"merge 顺序逻辑混乱"是我自己的设计漏洞（"先合 Shield 再合 Devon"在 e2e 依赖 Devon 实现时是无意义的），拆出 fix-001b 正是为了避开这个坑。
