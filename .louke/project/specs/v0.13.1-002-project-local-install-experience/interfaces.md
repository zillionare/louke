---
status: Draft — M-ARCH
spec_id: v0.13.1-002-project-local-install-experience
created: 2026-07-16
---

# 项目本地安装体验 + 发布身份同步 — Interfaces Contract

## Interfaces 通用规则

| 项 | Contract |
| --- | --- |
| 平台 | Unix 指 Linux/macOS；Windows 指原生 Windows 10/11。路径在各自平台按下表解释。 |
| 返回/诊断 | CLI 成功为 exit `0`；失败为非零，诊断写 stderr 且不含 credential。 |
| 运行时模式 | 仅 `local` 或 `global`；每次命令恰有一个模式。 |
| 包来源 | `--index` 是完整 pip index URL；未提供时使用 pip 默认 PyPI index。 |
| 子进程记录 | 仅测试 harness 提供的外部进程 recorder 可观察 argv、顺序和 exit；它不改写 louke 决策。 |

## CLI、文件和进程出口

| ID | 出口 contract | modules | AC 出口 |
| --- | --- | --- | --- |
| I-01 | `install.sh` 在 Unix CWD 执行；`install.bat` 和 `install.ps1` 在 Windows CWD 可各自执行。成功创建 `<CWD>/.venv`，其 Python `import louke` 为 0；选择最高可用 Python `>=3.11`。无兼容 Python 时非零且含 `Python 3.11+ required`；Unix 无 `python3` 时含 `python3 not found`；Windows `.bat` 调用 `.ps1` 时使用 `-ExecutionPolicy Bypass`。 | installers | AC-FR1501-01—04、AC-FR1502-01—04、AC-NFR1502-01—03 |
| I-02 | 安装器成功后 global runtime 存在：Unix `~/.louke/venv/bin/python`，Windows `%USERPROFILE%\\.louke\\venv\\Scripts\\python.exe`；该 Python `import louke` 为 0。local 与 global 是不同目录。重复 installer 不重复写入 PATH 配置。 | installers, runtime_install | AC-FR1503-01—04、AC-NFR1503-01 |
| I-03 | PATH `lk` shim 存在：Unix 的用户 bin `lk` 解析至 global runtime launcher；Windows `where lk` 解析至 global runtime launcher。installer 在必要时以唯一条目更新 shell rc 或用户 PATH。 | installers, shim | AC-FR1501-04、AC-FR1502-04、AC-FR1503-02/03、AC-NFR1503-01 |
| I-04 | `lk install [--index URL] [--version X.Y.Z]` 只在 CWD 创建 local `.venv` 并安装指定/最新包。CWD `.venv` 已存在时非零、stderr 建议 `lk upgrade`，且不修改该目录。 | __main__, install_cli, runtime_install | AC-NFR1503-02 |
| I-05 | PATH `lk <args...>` 仅检查 `<CWD>/.venv`：存在则执行 `<local-python> -m louke <args...>` 并设模式 `local`；不存在则执行 global Python 同样 argv 并设模式 `global`；绝不搜索父目录。两者不存在时非零，stderr 含 `no louke runtime found; run install.sh / install.bat / lk install first`。 | shim, runtime_install, __main__ | AC-FR1504-01—04、AC-FR1505-01—03 |
| I-06 | `lk --version` stdout 唯一一行 `<package-version> (local)` 或 `<package-version> (global)`；版本部分等于所执行 venv 的 `pip show louke` 版本。`lk server` 的 Settings 使用同一 `RuntimeIdentity`。 | shim, __main__, runtime_install, web | AC-FR1506-01—03、AC-FR1512-01 |
| I-07 | `lk upgrade [--local|--global|--both] [--index URL] [--version X.Y.Z]`：无目标等于 `--local`；三目标互斥，多项为 usage error 非零。缺 local/global 目标为非零并指出缺失路径。每个目标 pip argv 为 `<target-python> -m pip install --upgrade [--index-url URL] louke[==X.Y.Z]`，未给 version 时无 `==`。 | __main__, upgrade, runtime_install | AC-FR1507-01/02/04、AC-FR1508-01—05、AC-FR1509-01—04 |
| I-08 | Upgrade process record：每个 pip 的 `{argv,exit_code}`；仅 local pip 成功且 I-09 表示 harness 存在时，后接一个 `{kind:"board",argv,exit_code}`。pip 失败时无 board record；global 永无 board record；版本未变化的第二次 upgrade 不新增 board record。 | upgrade, board adapter | AC-FR1507-01—04、AC-FR1508-01—03、AC-FR1509-04、AC-NFR1503-03 |
| I-09 | 项目 harness manifest 是项目根 `.louke/project/project.toml` 的 `[harness]` 表：缺少该表表示无 harness，board 为 skip/no-op；存在时 `board_args` 为字符串数组，成为 I-08 board argv 的参数。 | upgrade, board adapter | AC-FR1507-01/03/04、AC-FR1508-01/03 |

## 发布、Web UI 出口

| ID | 出口 contract | modules | AC 出口 |
| --- | --- | --- | --- |
| I-10 | 通用纯 API `verify_release_identity(tag: str \| None, artifact_version: str \| None) -> ReleaseIdentityResult` 与等价 CLI `lk release verify --tag TAG --artifact-version VERSION`。结果/stdout JSON 为 `{passed:bool, normalized_tag:str\|null, artifact_version:str\|null, diagnostic:str}`；只去掉 tag 的一个前导 `v`。缺失 tag/version、含 `-dirty`/`+local` 的 tag 或不相等均为 `passed:false`，诊断含可用 tag/版本；无网络、git、文件系统副作用。它不解释 artifact 格式或读取 host 版本文件。 | release_identity, __main__ | AC-FR1510-01/02、AC-NFR1504-01/02 |
| I-11 | **Host release adapter/tool contract**（由每个 host project 的 M-ARCH 选择，非 Louke 默认 Python adapter）：该项目必须在 architecture.md 记录其实际调用、版本源、写入策略、build 和 artifact 类型。若选择 prepare，则 `ADAPTER prepare --tag TAG` 仅按 host 规则准备 build 输入；若选择 inspect，则 `ADAPTER inspect --artifact PATH` 成功时 stdout 唯一 JSON `{artifact:string, version:string}`，其中 `artifact` 规范化后等于 PATH，`version` 从 artifact 内容读取而非文件名。adapter 不得 upload。缺/非法 tag、版本源不能按已选策略准备、build 输入不一致、inspect 非零或 JSON/路径/version 无效均为非零失败。此为变量 `ADAPTER` 的 contract，不创建 adapter registry、公共命令名或 `lk_bump_version`。 | host release adapter/tool, release workflow, release_identity | AC-FR1510-03、AC-NFR1504-01/02 |
| I-12 | Host release workflow：取得 HEAD `TAG`，按 I-11 调用已选 adapter/tool 的 prepare（如有），运行 host build，并对**每个**候选 artifact 调用 I-11 inspect 后调用 I-10。adapter/build 非零、无 artifact、无/多余/格式错误记录、记录 artifact 不匹配、I-10 FAIL 均以非零阻断 publish；仅所有 artifact I-10 PASS 才可 upload。诊断输出 tag、artifact（可用时）、artifact version（可用时）与差异。对于**本 Louke self-host**，`ADAPTER = python tools/louke_python_release_adapter.py`：`prepare --tag TAG` 的 JSON 为 `{"tag":string,"version":string,"version_source":"pyproject.toml:[project].version","write":"updated"|"unchanged"}`，`inspect --artifact PATH` 使用 I-11 JSON；build 是 `python -m build`，并检查 wheel 与 sdist。此 Python/`pyproject.toml` 选择只适用于本仓库，不是最终用户项目的隐含合同。 | release workflow, host release adapter/tool, release_identity, __main__ | AC-FR1510-03 |
| I-13 | Host test bootstrap command：`tests/e2e/run-project-venv integration` 与 `tests/e2e/run-project-venv e2e --profile install|chromium|all --runtime local|global|both`。Unix launcher 只执行 `<repo>/.venv/bin/python`；Windows `run-project-venv.cmd` 只执行 `<repo>\.venv\Scripts\python.exe`。缺少/不可启动的目标解释器向 stderr 输出其绝对路径并 exit `127`；严禁 fallback 到 `python`、`py`、PATH、checkout `sys.executable`。启动的 runner 必须报告 `sys.executable` 等于该 project venv Python，`louke.__file__` 位于该 `.venv`，且 metadata version 等于 current-wheel manifest；任一不符非零且零 product child。 | test bootstrap, integration runner, e2e runner | AC-NFR1502-01—03、AC-NFR1503-01—03 |
| I-14 | 统一参数化 E2E runner：`--profile install|chromium|all --runtime local|global|both`；`all` 顺序运行两 profile，`both` 对每个 profile 运行 local/global。每个 case 创建临时 HOME（Windows 同时 USERPROFILE）、PATH、CWD；local 在 case CWD 创建 `.venv` 后以该 runtime/PATH shim 启动 product child，global 在临时 HOME 创建 global venv 后从无 `.venv` CWD 以该 runtime/PATH shim 启动。Chromium 的 `LOUKE_E2E_SERVER_PYTHON` 必须是选定 case product venv 的绝对 Python 路径，不得等于 runner Python 或位于 repo `.venv`；该 Python 的 `import louke` 路径在 product venv，metadata version 等于 fixture wheel manifest，随后才可执行 `<product-python> -m louke serve`。无效参数、任一子 suite、身份校验失败均非零，临时资源/服务必清理。 | test bootstrap, e2e runner, installers, shim, runtime_install, web | AC-FR1501-04、AC-FR1502-04、AC-FR1503-01—04、AC-FR1504-01—04、AC-FR1505-01—03、AC-FR1506-01—03、AC-FR1507-01—04、AC-FR1508-01—05、AC-FR1509-01—04、AC-NFR1502-01—03、AC-NFR1503-01—03 |
| I-15 | Settings read model `GET /api/ui/settings/runtime` 返回 `200 {version:string, mode:"local"|"global", display:"<version> (<mode>)"}`。Settings 页面在每次 render 读取该出口，将 `display` 与项目目录、`.venv` 路径元数据并列呈现；不得缓存或组合两个模式。 | web, runtime_install | AC-FR1512-01/02 |

## AC → interface → test-plan 闭环

| AC 组 | 接口出口 | test-plan 覆盖策略 |
| --- | --- | --- |
| AC-FR1501-01—04、AC-FR1502-01—04、AC-FR1503-01—04、AC-NFR1502-01—03、AC-NFR1503-01 | I-01、I-02、I-03 | §2.2/2.3、§4「安装与全局暴露」E2E |
| AC-FR1504-01—04、AC-FR1505-01—03、AC-FR1506-01—03 | I-05、I-06 | §4「shim 与版本身份」integration/E2E |
| AC-FR1507-01—04、AC-FR1508-01—05、AC-FR1509-01—04、AC-NFR1503-02/03 | I-04、I-07、I-08、I-09 | §4「安装/升级命令与 harness」unit/integration/E2E |
| AC-FR1510-01—03、AC-NFR1504-01/02 | I-10、I-11、I-12 | §3、§4「发布与 UI」unit + adapter/release smoke |
| AC-FR1512-01/02 | I-06、I-15 | §4「发布与 UI」integration/E2E |

跨模块接口 I-02—09、I-11—I-15 均在 `tests/integration/install_experience/` 有 integration 覆盖；其余单模块 I-01/I-10 仍由对应 unit 或 E2E 策略覆盖。针对 I-13/I-14 的回归检查将 project.toml 和 runner/bootstrap 资产中裸 `python tests/e2e`、裸 `python tests/integration`、裸 `python -m louke` 或 `sys.executable -m louke` 视为失败；唯一允许的 `-m louke` 进程 argv 前缀是已验证 case product Python 绝对路径。测试只从本表出口断言。
