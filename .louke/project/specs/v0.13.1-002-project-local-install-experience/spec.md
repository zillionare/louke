---
locked: true
locked-at: 2026-07-16T10:46:40Z
locked-by: lk agent sage record-lock
---
# v0.13.1 项目本地安装体验 + 发布身份同步 — 规格

- **Spec ID**: v0.13.1-002-project-local-install-experience
- **创建日期**: 2026-07-16
- **状态**: 草稿（Story 重写后；取代 2026-07-16 的 stage-1 草稿）

> **职责分离**: 本文档仅描述需求本身（FR/NFR 描述 + 元数据）。
> 验收标准（可观察、可断言的通关条件）放在 `acceptance.md` 中，以便在不膨胀 spec 的情况下演进。
> 测试计划（`test-plan.md`）同时引用 spec.md 和 acceptance.md 作为输入。

> Story 依据: 本 spec 根据用户 2026-07-16 的 story.md（10 个 US，1 个目标）重写。之前的 Sage 草稿（`sage-v0.13.1-002-stage1-draft.md` 中的 FR-1501..FR-1507 / NFR-1501..NFR-1504）**已废弃** —— story 反转了运行时模型（全局 + 本地双运行时，自动回退），要求原生 Windows 支持，参数化升级，并将发布身份同步降级为仅契约交付。

---

## 用户故事

> 以下 10 个用户故事取自 `story.md` 原文。US 编号 1501..1510 用于追溯（按周期惯例，`002` spec-id 后缀不会传播到 US/FR 编号）。

### US-1501
故事: 作为 linux/mac 新用户（最终用户），我希望从 git clone 目录开始，通过 `curl | sh`，于当前目录创建一个 `.venv` 虚拟环境（使用兼容 louke 的最高 Python 版本），并安装 louke python 包。
优先级: P0

### US-1502
故事: 作为 windows 新用户（最终用户），我希望从 github 下载脚本安装文件到我的 git clone 目录，双击运行，让它于当前目录创建一个 `.venv`（使用兼容 louke 的最高 Python 版本），并安装 louke python 包。
优先级: P0

> **定义**: US-1501 / US-1502 构建的运行时（`.venv` 及其中的 louke python 包）称为**本地运行时**。调用 `lk` 使得本地运行时执行命令称为**本地运行**。

### US-1503
故事: 作为新用户，我希望 US-1501 / US-1502 中使用的安装程序 ALSO 安装一个全局 `lk` 命令到我的 PATH 上，以便后续可以在任意 git clone 目录下运行 `lk install`，于该目录创建 `.venv` 并安装最新的 louke python 包。
优先级: P0

> **定义**: US-1503 构建的运行时（一个 `.venv` 及其中的 louke python 包）称为**全局运行时**。调用 `lk` 使得全局运行时执行命令称为**全局运行**。

### US-1504
故事: 当我运行 `lk --version` 时，输出后缀应匹配实际执行命令的运行时：如果由本地运行时执行，则为 `(local)`；如果由全局运行时执行，则为 `(global)`。二者绝不可混淆。
优先级: P0

### US-1505
故事: 当我在包含本地运行时的目录中运行 `lk {command}` 时，shim 应调用 `{python-runtime} -m louke {command} ...args`（即委托给本地运行时）。示例: `lk models list` → `{python-runtime} -m louke models list`。
优先级: P0

### US-1506
故事: 当我在不包含本地运行时的目录中运行 `lk {command}` 时，shim 应回退到全局运行时。
优先级: P0

### US-1507
故事: 作为现有用户，当我升级本地运行时时，升级操作应（除更新 `.venv` 和 louke python 包外）自动根据项目配置的 harness 执行 `lk board ...`，以刷新 harness 资源。
优先级: P1

### US-1508
故事: 作为现有用户（最终用户），当我从本地运行时运行升级命令时，我希望有一个选项可以同时升级全局安装。当以这种方式升级全局时，升级操作 MUST NOT 为每个项目执行 `lk board`。
优先级: P1

### US-1509
故事: 作为最终用户，当运行升级时，我希望能够指定自定义 PyPI 索引 URL 和特定的 louke 包版本。
优先级: P1

### US-1510
故事: 作为最终用户，我希望 louke 提供一个机制，保证在发布时，构建产物中的 louke 包版本与 git tag 所暗示的版本一致。
优先级: P0

---

## 使用场景

### scenario-1501 — linux/mac 首次安装

用户从刚克隆的目录中运行:

```
curl -sSL https://raw.githubusercontent.com/zillionare/louke/releases/0.13.1/install.sh | bash
```

用户拥有 (a) 当前目录中一个可工作的 `.venv/`，其中安装了 louke python 包，以及 (b) PATH 上指向一个独立全局运行时的 `lk` 命令。

### scenario-1502 — windows 首次安装

用户从 GitHub release 下载 `install.bat` 和 `install.ps1`，将两者放入 git clone 目录，双击 `install.bat`。用户拥有与 scenario-1501 相同的两个结果，适配 Windows PATH 语义。

### scenario-1503 — 从任意目录执行 `lk install`

用户已拥有全局 `lk` 在 PATH 上。从任意 git clone 目录运行 `lk install`。本地运行时出现在 `<CWD>/.venv/`。本地运行时 `lk` 从该目录优先执行。

### scenario-1504 — 版本报告

用户在一个同时存在两个运行时（本地 + 全局）的目录中。从 CWD 运行 `lk --version`：输出反映实际执行的那个运行时版本 + `(local)`。再从不包含本地运行时的目录运行一次，显示全局运行时版本 + `(global)`。

通过`lk server`运行时，在用户界面上显示当前运行时（`{version}(local|global）`)

### scenario-1505 — 本地升级与 board 同步

用户在一个配置了 harness 的项目目录中，拥有本地运行时。运行 `lk upgrade`。`.venv/` 和 louke 包被更新；`lk board ...` 根据项目 harness 配置执行。

### scenario-1506 — 组合升级与自定义 PyPI

用户运行 `lk upgrade --both --index https://pypi.org/simple --version x.y.z`。本地和全局运行时都从 PyPI 升级到 x.y.z。`lk board` 为本地项目执行一次；全局不做任何操作。

### scenario-1507 — 发布身份同步

发布工程师推送 tag `vx.y.z`。发布流水线运行发布身份同步契约（机制由 M-ARCH 选择），并 (a) 如果构建产物中的包版本与 tag 不匹配，则以清晰的错误消息中止发布，或 (b) 生成一个其版本可验证地与 tag 一致的构建产物。

---

## 功能需求

> **格式规范（必读）**: 每个 FR 单元以三级标题 + 空格 + FR-XXXX（大写，4 位零填充）+ {标题} 开头，紧接着一个 3 列元数据表（Valid / Testable / Decided），然后是需求描述；FR 之间用 `---` 分隔。
>
> **编号规范（必读）**: FR 代码使用 **4 位数字**，零填充，本 spec 周期使用 15xx 范围。每个 FR 在 Step 4 通过 spec.md 锚点（`<a id="fr-XXXX">`）和 acceptance.md 锚点（`<a id="ac-fr-XXXX">`）引用。
>
> AC 引用: 验收标准使用 `AC-FRXXXX-YY` 格式（4 位 FR + 2 位 AC），见 `acceptance.md`。

### FR-1501 {linux/mac 一键本地安装 (curl|sh → .venv/)}

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

当用户在 linux 或 macOS 上，从 git clone 目录运行 `curl -sSL <install.sh URL> | bash` 时，系统应:

- 在当前工作目录内创建一个 `.venv/` 目录（使用宿主机上兼容 louke 的最高可用 Python 版本）；
- 将 louke python 包安装到该 `.venv/` 中；
- 如果找不到兼容的 Python、无法创建 `.venv/` 或 pip install 失败，则以非零退出并给出清晰的错误消息；

本地 `.venv/` 是 US-1501 的交付物。验收: `AC-FR1501-01`, `AC-FR1501-02`, `AC-FR1501-03`, `AC-FR1501-04`。

---

### FR-1502 {windows 一键本地安装 (bat/ps → .venv/)}

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

当用户在 windows 上，从 GitHub release 下载脚本安装文件到 git clone 目录，并双击（或以其他方式调用）入口文件时，系统应:

- 在当前工作目录内创建一个 `.venv/` 目录（使用宿主机上兼容 louke 的最高可用 Python 版本）；
- 将 louke python 包安装到该 `.venv/` 中；
- 出现任何安装失败，则以非零退出并给出清晰的错误消息；

验收: `AC-FR1502-01`, `AC-FR1502-02`, `AC-FR1502-03`, `AC-FR1502-04`。

---

### FR-1503 {linux/mac + windows 安装程序同时安装全局 `lk`}

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

FR-1501 和 FR-1502 调用的安装程序应在创建本地 `.venv/` 之外，同时:

- 创建一个单独的全局运行时位置（linux/mac: `~/.louke/venv`；windows: `%USERPROFILE%\.louke\venv`）；
- 将 louke python 包安装到该全局运行时中；
- 将全局 `lk` 命令暴露到用户的 PATH 上（linux/mac: `~/.local/bin` 或用户首选位置中的符号链接或启动器；windows: PATH 上的 `lk.cmd` 或 `lk.exe` shim）。

全局运行时是 US-1503 的交付物，也是 FR-1504..FR-1509 的前置条件。

验收: `AC-FR1503-01`, `AC-FR1503-02`, `AC-FR1503-03`, `AC-FR1503-04`。

---

### FR-1504 {`lk` shim: 本地优先调度，严格 CWD 查找}

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

PATH 上的 `lk` 二进制（由 FR-1503 放置）是一个 SHIM，而非真正的 louke 入口点。当用户运行 `lk {command} {args...}` 时:

- Shim 应检查 `<CWD>/.venv/` 是否存在。**查找是严格 CWD 的——不向上遍历父目录。**（US-1505）
- 如果 `<CWD>/.venv/` 存在，shim 应调用 `<CWD>/.venv/bin/python -m louke {command} {args...}`（linux/mac）或 `<CWD>/.venv\Scripts\python.exe -m louke {command} {args...}`（windows）。
- 如果 `<CWD>/.venv/` 不存在，shim 应根据 FR-1505 回退到全局运行时。
- 如果本地和全局运行时都不存在，shim 应以非零退出并给出清晰的错误消息，告知用户运行 `lk install` 或 curl|sh / install.bat 安装程序。

查找规则有意不递归，以避免在嵌套子目录中产生意外行为；希望本地运行时生效的用户必须从拥有 `.venv/` 的目录调用 `lk`。

验收: `AC-FR1504-01`, `AC-FR1504-02`, `AC-FR1504-03`, `AC-FR1504-04`。

---

### FR-1505 {本地不存在时回退到全局运行时}

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

当 `<CWD>/.venv/` 不存在时，`lk` shim 应调用全局运行时的 Python 并传 `-m louke {command} {args...}`。全局运行时路径为:

- linux/mac: `~/.louke/venv/bin/python`
- windows: `%USERPROFILE%\.louke\venv\Scripts\python.exe`

如果全局运行时也不存在（例如用户从未运行过安装程序），shim 应根据 FR-1504 最后一条以非零退出。

验收: `AC-FR1505-01`, `AC-FR1505-02`, `AC-FR1505-03`。

---

### FR-1506 {`lk --version` 后缀指明哪个运行时执行}

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

当 `lk --version` 运行时，输出应:

- 打印 louke 包版本（与底层 `-m louke --version` 已输出的格式相同）；
- 如果执行运行时是本地运行时（FR-1504 第一分支），追加 `(local)`；
- 如果执行运行时是全局运行时（FR-1505 回退），追加 `(global)`；
- 绝不打印两个后缀，绝不打印错误的后缀，绝不打印空后缀。

验收: `AC-FR1506-01`, `AC-FR1506-02`, `AC-FR1506-03`。

---

### FR-1507 {本地升级 + 自动 `lk board` 同步}

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

当用户从包含本地运行时的目录中运行 `lk upgrade`（或其显式 `--local` 形式，见 FR-1508）时，系统应:

- 使用 pip 升级 `<CWD>/.venv/` 中的 louke python 包；
- pip 升级成功后，调用 `lk board {从项目 harness 配置派生的参数}`，使 harness 资源与运行时升级同步刷新；
- 如果 pip 升级失败，则以非零退出并给出清晰的错误消息；`board` 步骤 SHALL NOT 在 pip 失败时运行；
- 如果项目没有配置 harness 资源（例如未检测到 harness），`board` 步骤为 no-op（跳过）——不以失败告终。

`lk board {args...}` 的具体形式因项目而异；M-ARCH / M-DEV 拥有 harness 配置契约。此 FR 断言可观察的行为: pip 升级 + 与升级成功绑定的尽力而为的 board 调用。

验收: `AC-FR1507-01`, `AC-FR1507-02`, `AC-FR1507-03`, `AC-FR1507-04`。

---

### FR-1508 {升级目标标志: `--local` / `--global` / `--both`}

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

`lk upgrade` 应接受互斥的目标标志。默认（无标志）等同于 `--local`。每次调用只能接受以下之一:

- `lk upgrade` / `lk upgrade --local` — 仅升级本地运行时；根据 FR-1507 运行 `lk board`。
- `lk upgrade --global` — 仅升级全局运行时；不为任何项目运行 `lk board`（全局运行时没有"项目"的概念）。
- `lk upgrade --both` — 在一次调用中同时升级本地和全局运行时；`lk board` 仅针对本地目标运行。

如果用户传入了 `--local`、`--global`、`--both` 中的多个，系统应以非零退出并给出用法错误。

如果请求的目标不存在（例如 `--global` 但没有全局运行时，或 `--local` 但没有 `<CWD>/.venv/`），系统应以非零退出并给出清晰的错误消息，指明缺失的运行时。

验收: `AC-FR1508-01`, `AC-FR1508-02`, `AC-FR1508-03`, `AC-FR1508-04`, `AC-FR1508-05`。

---

### FR-1509 {升级 `--index` 和 `--version` 参数}

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

`lk upgrade` 应接受两个可选标志，独立于 FR-1508 中的目标选择标志:

- `--index <URL>` — 作为 `--index-url` 传给 pip。默认: louke 发布的 PyPI 索引（即 PyPI 本身）。
- `--version <X.Y.Z>` — 作为 `louke==<X.Y.Z>` 传给 pip。默认: 最新发布的 louke 版本。

两个标志适用于 FR-1508 选择的任何目标。每个目标的 pip install 行应派生为 `pip install --index-url <URL> louke[==<X.Y.Z>]`（当未传 `--version` 时省略 `==X.Y.Z` 子句）。

验收: `AC-FR1509-01`, `AC-FR1509-02`, `AC-FR1509-03`, `AC-FR1509-04`。

---

### FR-1510 {发布身份同步契约}

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

Louke 应暴露一个发布身份同步**契约**，保证使用 Louke 开发的项目中，其发布时构建产物中的版本与 git tag 所暗示的版本一致。契约是 FR-1510 所断言的内容；实现契约的*机制*有意不在此处指定——不同项目使用不同的 bump 版本惯例（有些用 `git describe`，有些用手动 `VERSION` 文件，有些用 `bump2version` 等），因此 M-ARCH 在架构审查期间选择机制。契约如下:

- **输入**: 发布分支 HEAD 处的 git tag（例如 `v0.13.1` → 版本 `0.13.1`）以及将嵌入构建产物的版本。
- **输出**: 一个 PASS / FAIL 信号，若 FAIL，则输出清晰的、可操作的错误消息，指明 tag、包版本和差异。
- **FAIL 时的行为**: 发布中止（或者，如果所选机制允许，构建继续但产物被标记为明确的"version-mismatch"指示器——由 M-ARCH 决定）。
- **PASS 时的行为**: 构建产物的版本与 tag 隐含的版本逐字节相等（例如 `0.13.1` == `0.13.1`，无前导 `v`，无 dirty 后缀）。

M-ARCH 必须在 `architecture.md` 中记录所选机制，并链接回此 FR-1510 契约。

验收: `AC-FR1510-01`, `AC-FR1510-02`, `AC-FR1510-03`。


### FR-1512 {lk server Web UI Settings 页面显示当前运行时}

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

在 `lk server` 启动的 Web UI 中，Settings 页面显示当前运行时（`{version} (local|global)`），便于用户在设置区域确认当前激活的是本地还是全局运行时。

> **Aaron [RESOLVED]:** 请在此指定 UI 位置。
>> **Sage:** 已根据用户在 Step 3 给出的口头决策，在 FR-1512 描述中将 UI 位置指定为 Settings 页面。请由 initiator（**Aaron**）标记 `[RESOLVED]` 以关闭本 thread。

验收: `AC-FR1512-01`, `AC-FR1512-02`。

---

## 非功能需求

### NFR-1502 {跨平台支持矩阵}

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

- CI 应覆盖 linux x86_64、macOS x86_64、macOS arm64 和 Windows x86_64。
- 每个平台应执行首次安装端到端，并验证本地 `.venv/` 存在且已安装 louke。
- 支持的 Python 版本应覆盖 3.11、3.12 和 3.13（以 CI 镜像可用版本为准），安装程序选择最高可用的兼容版本。
- Windows 验证应在原生 Windows 环境执行，不依赖 WSL、Docker 或其他虚拟化层。

验收: `AC-NFR1502-01`, `AC-NFR1502-02`, `AC-NFR1502-03`。

---

### NFR-1503 {幂等性与安全重运行}

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

安装程序（FR-1501 / FR-1502）和 `lk install` 命令（US-1503）应可安全重运行:

- 当两个运行时已存在时，重新运行安装程序对于已存在且版本相同的运行时为 no-op，对于已安装版本与"最新"（或 `--version`）不同的运行时则执行升级。
- 当 `<CWD>/.venv/` 已存在时，重新运行 `lk install` 应根据用户确认的拒绝规则以非零退出——它 SHALL NOT 静默升级，也 SHALL NOT 覆盖已有文件。
- `lk upgrade` 在浅层意义上是幂等的: 连续运行两次且无中间变化应两次均以 0 退出。

验收: `AC-NFR1503-01`, `AC-NFR1503-02`, `AC-NFR1503-03`。


---

### NFR-1504 {发布身份契约必须可测试}

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

FR-1510 中的发布身份同步契约应可作为单元测试（使用 Louke 项目本身）: 给定一个 stub "tag at HEAD" + 一个 stub "package version"，契约返回 PASS 或 FAIL 并附带差异。M-ARCH 选择的机制必须允许这样的单元测试（契约内部无可测试的副作用）。

验收: `AC-NFR1504-01`, `AC-NFR1504-02`。

---

## 澄清日志

> 2026-07-16 Sage Stage-1 问答轮次中提出的问题，以及用户选择的默认值。以下条目记录已确定的决策和仍由 M-ARCH/M-DEV 负责的实现选择。

1. **本地运行时查找范围（US-1505）**: 用户选择"严格 CWD 仅限，不向上遍历"。记录在 FR-1504 中。✅。
2. **升级标志语法（US-1507/8/9）**: 用户选择"互斥目标标志"（`--local` / `--global` / `--both`，默认 = local）。记录在 FR-1508 中。✅。
3. **已存在 venv 时 `lk install`（US-1503）**: 用户选择"拒绝 + 建议 `lk upgrade`"。记录在 NFR-1503 AC-2 中。✅。
4. **发布身份机制（US-1510）**: 用户说"这是 Archer 的工作——spec 只定义契约"。记录在 FR-1510 中。FR-1510 的契约已确定，机制由 M-ARCH 选择。
5. **Windows 安装程序格式（US-1502）**: 用户确认默认值为两个文件（`install.bat` + `install.ps1`）。机制细节仍可由 M-ARCH/M-DEV 实现。
6. **FR-1512 UI 位置**: 用户在 Step 3 决定 = Settings 页面（在 `lk server` 启动的 Web UI 中）。记录在 FR-1512 中。
7. **FR-1502 / NFR-1501 时间要求**: 用户多次表态"不对安装时间作要求"（参见 Step 1 line 77 / Step 1 line 143 / Step 3）。删除 FR-1502 中的 5 分钟 bullet 并删除整个 NFR-1501 单元（连同 acceptance.md 中 NFR-1501 的 AC 单元）。

后续阶段事项:

- **FR-1507**: 精确的"未检测到 harness"条件由 M-ARCH 决定；spec 断言可观察的 no-op 行为。
- **FR-1510**: 机制由 M-ARCH 选择并记录在 `architecture.md` 中；spec 仅断言契约。
- **FR-1501 / FR-1503**: 错误消息和 PATH 修改行为的具体实现措辞可在 M-DEV 期间打磨，需求决策不变。
