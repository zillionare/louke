# v0.13.1 项目本地安装体验 + 发布身份同步 — 验收标准

- **Spec ID**: v0.13.1-002-project-local-install-experience
- **创建日期**: 2026-07-16

> 验收标准中心注册表。spec.md 仅保留 FR/NFR 需求描述和元数据（可测试性/已解决/有效）；
> 详细的可观察、可断言的通关条件存放在此表中。
>
> 编号规范:
> - 在每个 FR/NFR 单元内，AC-N 从 1 开始顺序递增；不可跨单元复用
> - 完整 AC 引用: **AC-FRXXXX-YY**（4 位 FR + 2 位 AC 序号），与 test-plan/issue schema 一致
>
> Lex 阶段 1/2 审查时，验证: (1) 此表存在；(2) spec.md 中每个 FR/NFR 在此处有对应章节；(3) 每个 AC 可测试/可断言。

<a id="ac-fr-1501"></a>
## FR-1501 {linux/mac 一键本地安装 (curl|sh → .venv/)}

### AC-1
- 在 linux 或 macOS 上从某个目录运行 `curl -sSL <install.sh> | bash` 后，`<CWD>/.venv/` 目录被创建。
- `<CWD>/.venv/bin/python -c "import louke"` 以 0 退出（louke 包已安装到本地 venv 中）。

### AC-2
- venv 使用宿主机上存在的最高 Python ≥ 3.11 版本创建。
- 如果宿主机同时有 Python 3.11 和 Python 3.13，则创建的 `.venv/bin/python` 报告 `Python 3.13.x`。

### AC-3
- 在没有兼容 Python 的宿主机上（例如只有 Python 3.10），安装程序以非零退出，stderr 包含子串 `Python 3.11+ required`（或等效的可操作错误）。
- 在 PATH 上没有 `python3` 的宿主机上，安装程序以非零退出并给出清晰的 `python3 not found` 消息。

### AC-4
- 在没有预先存在的 `.venv/` 的干净临时目录上，安装程序退出码为 0。
- FR-1503 放置到 PATH 上的全局 `lk` 命令在安装程序退出 0 后也存在。

AC-FR1501-01, AC-FR1501-02, AC-FR1501-03, AC-FR1501-04

---

<a id="ac-fr-1502"></a>
## FR-1502 {windows 一键本地安装 (bat/ps → .venv/)}

### AC-1
- 在 windows 10/11 上从某个目录运行 `install.bat`（或 `install.ps1`）后，`<CWD>/.venv\` 目录被创建。
- `<CWD>/.venv\Scripts\python.exe -c "import louke"` 以 0 退出。

### AC-2
- venv 使用宿主机上最高的 Python ≥ 3.11 版本创建。
- 如果只安装了 Python 3.10，安装程序以非零退出并给出清晰的可操作错误。

### AC-3
- 默认机制是两个文件: `install.bat` 和 `install.ps1`。任一文件单独即可驱动安装。
- 双击 `install.bat` 即使在 PowerShell 执行策略为 `Restricted` 时也能成功（`.bat` 包装器内部调用 PowerShell 并传 `-ExecutionPolicy Bypass`）。

### AC-4
- 在没有预先存在的 `.venv\` 的干净临时目录上，安装程序退出码为 0。
- FR-1503 放置到 PATH 上的全局 `lk` 命令在安装程序退出 0 后也存在。

AC-FR1502-01, AC-FR1502-02, AC-FR1502-03, AC-FR1502-04

---

<a id="ac-fr-1503"></a>
## FR-1503 {linux/mac + windows 安装程序同时安装全局 `lk`}

### AC-1
- FR-1501 / FR-1502 安装程序以 0 退出后，全局运行时 `~/.louke/venv`（linux/mac）或 `%USERPROFILE%\.louke\venv`（windows）存在。
- `~/.louke/venv/bin/python -c "import louke"`（linux/mac）或 `%USERPROFILE%\.louke\venv\Scripts\python.exe -c "import louke"`（windows）以 0 退出。

### AC-2
- 安装程序以 0 退出后，全局 `lk` 命令在用户的 PATH 上。
- linux/mac: `command -v lk` 返回用户 bin 目录下的路径（例如 `~/.local/bin/lk`），且该路径解析到 `~/.louke/venv/bin/lk`。
- windows: `where lk` 返回用户本地 scripts 目录下的路径（例如 `%LOCALAPPDATA%\Programs\Python\...` 或类似），且该路径解析到 `%USERPROFILE%\.louke\venv\Scripts\lk.exe`。

### AC-3
- PATH 修改（linux/mac: 追加到 `~/.bashrc` / `~/.zshrc` / `~/.profile`；windows: 设置用户级 PATH）是幂等的——重新运行安装程序不会追加重复行。

### AC-4
- 本地 `.venv/` 和全局运行时 `~/.louke/venv` 是不同的目录（每个项目一个 vs. 每个用户一个）。
- 单次安装程序调用后，两者都安装了 louke 包。

AC-FR1503-01, AC-FR1503-02, AC-FR1503-03, AC-FR1503-04

---

<a id="ac-fr-1504"></a>
## FR-1504 {`lk` shim: 本地优先调度，严格 CWD 查找}

### AC-1
- 从包含 `<CWD>/.venv/` 的目录中，运行 `lk {anything}` 导致 `<CWD>/.venv/bin/python -m louke {anything}`（linux/mac）或 `<CWD>/.venv\Scripts\python.exe -m louke {anything}`（windows）被执行。
- 通过设置哨兵环境变量或检查 `lk python --version` 报告的 python 是否匹配 `<CWD>/.venv/bin/python --version` 来验证。

### AC-2
- 查找是严格 CWD 的: 从项目的不包含自身 `.venv/` 的子目录中，shim 不会在父目录中找到 `.venv/`。从 `<repo>/tests/` 运行 `lk`（`.venv` 在 `<repo>/.venv/`）会回退到全局运行时，而非本地运行时。
- 通过集成测试确认，该测试断言从子目录执行 `lk --version` 报告 `(global)`，即使 `<repo>/.venv/` 存在。

### AC-3
- 从不包含本地 `.venv/` 的目录中，shim 根据 FR-1505 回退到全局运行时。
- 在该目录中 `lk --version` 报告 `(global)`。

### AC-4
- 从既没有本地 `.venv/` 也没有全局运行时安装的目录中（例如用户删除了 `~/.louke/venv`），`lk {anything}` 以非零退出，stderr 包含清晰消息: `no louke runtime found; run install.sh / install.bat / lk install first`。

AC-FR1504-01, AC-FR1504-02, AC-FR1504-03, AC-FR1504-04

---

<a id="ac-fr-1505"></a>
## FR-1505 {本地不存在时回退到全局运行时}

### AC-1
- 当 `<CWD>/.venv/` 不存在时，shim 调用 `~/.louke/venv/bin/python -m louke {command} {args}`（linux/mac）或 `%USERPROFILE%\.louke\venv\Scripts\python.exe -m louke {command} {args}`（windows）。
- 通过测试 harness 中观察进程调用来验证（例如 `strace` / 进程 mock）。

### AC-2
- 在没有本地 `.venv/` 的目录中，`lk --version` 报告全局 louke 包版本，后跟 `(global)`。

### AC-3
- 回退对用户透明: 从无本地 venv 的目录中运行 `lk {command}` 的行为与直接调用 `~/.louke/venv/bin/python -m louke {command}` 完全相同。

AC-FR1505-01, AC-FR1505-02, AC-FR1505-03

---

<a id="ac-fr-1506"></a>
## FR-1506 {`lk --version` 后缀指明哪个运行时执行}

### AC-1
- 从有本地 `.venv/` 的目录中，`lk --version` 输出匹配正则 `^<version> \(local\)$`（其中 `<version>` 是 louke 包版本，例如 `0.13.1`）。
- 不包含子串 `(global)`。

### AC-2
- 从没有本地 `.venv/` 的目录中，`lk --version` 输出匹配正则 `^<version> \(global\)$`。
- 不包含子串 `(local)`。

### AC-3
- 版本部分（后缀之前）与在执行运行时中运行 `pip show louke` 报告的包版本匹配。
- 本地运行时版本匹配 `<CWD>/.venv/bin/pip show louke`；全局运行时版本匹配 `~/.louke/venv/bin/pip show louke`。

AC-FR1506-01, AC-FR1506-02, AC-FR1506-03

---

<a id="ac-fr-1507"></a>
## FR-1507 {本地升级 + 自动 `lk board` 同步}

### AC-1
- 从配置了 harness 资源且包含 `<CWD>/.venv/` 的目录中运行 `lk upgrade` 导致:
  - `<CWD>/.venv/` 中的 louke 包升级到目标版本（当未传 `--version` 时按 FR-1509 默认值）；
  - pip 成功后，`lk board {harness-args}` 被调用；
  - 如果 pip 和 board 均成功，则以 0 退出。

### AC-2
- 如果 pip 升级失败（例如网络错误、无效的 `--version`），`lk upgrade` 以非零退出 AND `lk board` 不被调用。
- 通过 mock pip 使其失败并断言 board 从未被调用来验证。

### AC-3
- 如果项目没有配置 harness 资源，`lk upgrade` 仍然成功升级 pip，board 步骤为 no-op（跳过，不报错）。

### AC-4
- `lk upgrade`（默认 = local）和 `lk upgrade --local` 在行为上等价；两者都调用 board，两者都将范围限制为 `<CWD>/.venv/`。

AC-FR1507-01, AC-FR1507-02, AC-FR1507-03, AC-FR1507-04

---

<a id="ac-fr-1508"></a>
## FR-1508 {升级目标标志: `--local` / `--global` / `--both`}

### AC-1
- `lk upgrade`（无标志）仅针对本地运行时，并根据 FR-1507 运行 `lk board`。
- 行为与 `lk upgrade --local` 等价。

### AC-2
- `lk upgrade --global` 仅针对全局运行时。
- 不为任何项目调用 `lk board`（board 不是全局运行时概念）。

### AC-3
- `lk upgrade --both` 在一次调用中同时升级本地和全局运行时。
- `lk board` 仅针对本地目标运行；全局目标不触发 board。

### AC-4
- 在单次调用中传入 `--local`、`--global`、`--both` 中的多个会导致 `lk upgrade` 以非零退出并给出指明冲突标志的用法错误。

### AC-5
- 如果请求的目标不存在（例如 `~/.louke/venv` 缺失时执行 `lk upgrade --global`，或 `<CWD>/.venv/` 缺失时执行 `lk upgrade --local`），`lk upgrade` 以非零退出并给出指明缺失运行时位置的清晰消息。

AC-FR1508-01, AC-FR1508-02, AC-FR1508-03, AC-FR1508-04, AC-FR1508-05

---

<a id="ac-fr-1509"></a>
## FR-1509 {升级 `--index` 和 `--version` 参数}

### AC-1
- `lk upgrade --index https://my-pypi.example.com/simple/ --version 1.2.3` 导致目标运行时中的 pip 收到 `--index-url https://my-pypi.example.com/simple/ louke==1.2.3`。
- 通过检查解析后的 pip 命令来验证（测试 harness mock pip 并捕获参数）。

### AC-2
- `lk upgrade --version 1.2.3`（无 `--index`）保持 pip 默认索引并固定版本为 1.2.3。
- `lk upgrade --index URL`（无 `--version`）使用自定义索引但不固定版本（安装最新）。

### AC-3
- 标志适用于 FR-1508 选择的任何目标: `lk upgrade --both --index X --version Y` 使用索引 X 和版本 Y 升级两个运行时。

### AC-4
- 无效值（例如 `--version not-a-version`）导致 pip 失败；`lk upgrade` 以非零退出，失败模式可观察（非零退出 + stderr）。

AC-FR1509-01, AC-FR1509-02, AC-FR1509-03, AC-FR1509-04

---

<a id="ac-fr-1510"></a>
## FR-1510 {发布身份同步契约}

### AC-1
- 发布身份同步契约存在一个单元测试，接受 stub 输入: `tag="v0.13.1"`, `package_version="0.13.1"` → 返回 PASS。
- 相同输入但 `tag="v0.13.1"`, `package_version="0.13.0"` → 返回 FAIL 并附带包含两个版本的差异文本。

### AC-2
- 契约通过去除前导 `v` 来规范化 tag（因此 `v0.13.1` 和 `0.13.1` 在 tag 侧是等价的）。
- 在 FAIL 时，错误消息指明 tag（规范化后）和包版本，并明确指出差异。

### AC-3
- 发布流水线调用所选机制（M-ARCH 选择: 构建前检查 / 自动编辑 / CI gate / 等），并在 FAIL 时中止发布或相应标记产物。
- 在 PASS 时，发布产物的包版本与 tag 隐含的版本逐字节相等（无前导 `v`，无 `-dirty` 后缀，无 `+local` 标记）。

AC-FR1510-01, AC-FR1510-02, AC-FR1510-03

---

<a id="ac-fr-1512"></a>
## FR-1512 {lk server Web UI Settings 页面显示当前运行时}

### AC-1
- 启动 `lk server` 并打开 Web UI 后，导航到 Settings 页面。
- Settings 页面显示一行包含当前运行时版本的字符串，格式为 `<version> (local)` 或 `<version> (global)`，其中 `<version>` 是当前 louke 包版本。
- 字符串在每次页面渲染时根据 `lk --version` 的输出读取，不缓存。

### AC-2
- 在 Settings 页面，运行时信息与 louke 全局元数据（如项目目录、`.venv/` 路径等）并列显示，便于用户一眼确认当前激活的是本地还是全局运行时。

AC-FR1512-01, AC-FR1512-02

---

<a id="ac-nfr-1502"></a>
## NFR-1502 {跨平台支持矩阵}

### AC-1
- CI 矩阵 job 存在，至少包含以下构建目标:
  - `ubuntu-22.04`（linux x86_64）
  - `macos-13`（macOS x86_64）和 `macos-14`（macOS arm64）
  - `windows-2022`（windows x86_64）
- 每个矩阵单元运行首次安装端到端，并断言 `.venv/` 存在且安装了 louke。

### AC-2
- 在每个受支持的平台上，测试 Python 3.11、3.12 和 3.13（CI 镜像中可用的任何版本）。
- 安装程序选择最高的可用版本 ≥ 3.11。

### AC-3
- 在 windows 矩阵目标上不涉及 WSL2、Docker 或任何虚拟化层——测试在 `windows-2022` 上原生运行。

AC-NFR1502-01, AC-NFR1502-02, AC-NFR1502-03

---

<a id="ac-nfr-1503"></a>
## NFR-1503 {幂等性与安全重运行}

### AC-1
- 连续运行两次 FR-1501 / FR-1502 安装程序（中间无版本变化）导致两次均以 0 退出。
- 不会向用户的 shell rc 文件追加重复的 PATH 条目。

### AC-2
- 从已有 `.venv/` 的目录中运行 `lk install` 以非零退出，stderr 建议 `lk upgrade`。
- 已有的 `.venv/` 不被修改、不被删除、不被重建。

### AC-3
- 连续运行两次 `lk upgrade`（无中间变化）两次均以 0 退出。
- 如果版本未变，第二次运行不会重新调用 `lk board`（在 board 调用层面也是幂等的）。

AC-NFR1503-01, AC-NFR1503-02, AC-NFR1503-03

---

<a id="ac-nfr-1504"></a>
## NFR-1504 {发布身份契约必须可测试}

### AC-1
- FR-1510 的发布身份同步契约实现为纯函数（导入无副作用，无网络调用，契约本身无 git 操作）。
- 一个 pytest 单元测试导入契约模块，用 stub 输入调用它，并在不接触网络或文件系统的情况下断言 PASS / FAIL。

### AC-2
- 单元测试覆盖至少 4 种情况: 版本匹配 PASS、版本不匹配 FAIL、dirty tag FAIL、缺失 tag FAIL。
- 每种情况都断言布尔结果和一个非空诊断字符串。

AC-NFR1504-01, AC-NFR1504-02
