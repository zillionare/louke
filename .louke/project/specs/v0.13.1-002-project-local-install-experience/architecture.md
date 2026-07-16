---
status: Draft — M-ARCH
spec_id: v0.13.1-002-project-local-install-experience
created: 2026-07-16
---

# 项目本地安装体验 + 发布身份同步 — Architecture

## 1. 范围与架构决定

本期只实现双运行时安装、严格 CWD shim 调度、安装/升级命令、发布版本身份检查，以及 Settings 中的运行时显示；不改变既有项目工作流、`board` 的资源生成语义或 Web 认证边界。所有运行时路径均是用户可观察的 FR-1501—FR-1509 出口。

| 决定                                                                             | 解决的问题                                                            | 放弃的方案                                                        | 主要风险与控制                                                                                                                               | 需求                                                                        |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| 本地 `<CWD>/.venv` 与用户级 `~/.louke/venv` / `%USERPROFILE%\\.louke\\venv` 分离 | 项目隔离且可在任意 clone 使用全局 `lk`                                | 单一全局 venv                                                     | 路径混淆；shim 每次仅检查 CWD，并由 `RuntimeIdentity` 输出模式                                                                               | FR-1501—1506                                                                |
| PATH 上只安装轻量 `lk` shim                                                      | 同一命令可选择 local/global Python                                    | 把全局 console-script 当唯一入口                                  | argv 或递归调用错误；shim 固定 `python -m louke`，保留所有 argv                                                                              | FR-1503—1506                                                                |
| 安装器使用可用的最高 Python 3.11+                                                | 同时满足跨平台和最高版本选择                                          | 固定 `python3` 或捆绑 Python                                      | PATH/Windows launcher 差异；安装器输出已选择解释器，原生 OS E2E 验证                                                                         | FR-1501、1502、NFR-1502                                                     |
| upgrade 先执行 pip、成功后才按 harness 配置调用 board                            | 防止失败升级刷新资源                                                  | 无条件或异步 board                                                | board 失败/无 harness；公开记录区分 pip、board、skipped，pip 失败绝不调用 board                                                              | FR-1507—1509                                                                |
| 发布采用通用 tag/artifact identity gate；本仓库选择 Python self-host adapter | 任意技术栈的 host project 可验证每个发布 artifact 的版本逐字节等于 tag；Louke 本仓库可把 tag 写到其真实版本源 | 假定 `pyproject.toml`、特定构建工具或只信任 artifact 文件名 | adapter 的错误提取或写入可能报错；缺失、无法读取或不等均阻断 publish；Python 选择仅限本仓库 | FR-1510、NFR-1504 |
| Settings 读取本次 server 运行时公开身份                                          | UI 显示真实 `(local                                                   | global)`，不猜测安装路径                                          | 前端自行探测 `.venv`                                                                                                                         | server/shim 身份漂移；server 将启动时 identity 注入公开 Settings read model | FR-1512 |

## 模块划分

| 模块（建议路径）                                              | 职责                                                               | 可依赖                                                                              | 不负责                                                  |
| ------------------------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------- | ------------------------------------------------------- |
| `installers/` (`install.sh`, `install.bat`, `install.ps1`)    | 创建/复用本地与全局 venv，安装包，创建 PATH shim，幂等 PATH 更新   | OS shell、Python launcher、pip、Shim Assets                                         | 解析 `lk upgrade`、Web UI                               |
| `louke/runtime_install.py`                                    | 公开运行时路径、解释器选择、`RuntimeIdentity` 与 runtime 存在性    | 标准库路径/平台信息                                                                 | pip 执行、PATH 修改、向上搜索                           |
| `louke/shim`（随全局安装分发的 Unix/Windows launcher）        | 严格 CWD local-first，或 global fallback；委托 Python module       | `runtime_install`、OS 进程                                                          | louke 命令业务分派、升级策略                            |
| `louke/install_cli.py`                                        | `lk install`：仅在 CWD 创建本地运行时；已有 `.venv` 时拒绝         | `runtime_install`、pip runner                                                       | 全局重装、静默覆盖                                      |
| `louke/upgrade.py`                                            | 目标选择、pip argv、harness 配置读取、条件 board 调用和结果报告    | `runtime_install`、公开 `board` CLI adapter、subprocess                             | shim 路由、board 实现                                   |
| `louke/__main__.py`                                           | 注册 `install`/`upgrade`/`--version` 并把运行时身份传给命令/服务器 | install/upgrade/runtime/web entrypoints                                             | 路径发现的重复实现                                      |
| `louke/web/`                                                  | 从 server runtime identity 生成 Settings read model 与页面文本     | `runtime_install` 的 identity contract、既有 Starlette UI                           | 安装、PATH 或 pip                                       |
| `tests/e2e/run-project-venv` + `.cmd`、`tests/integration/install_experience/`、`tests/e2e/run_e2e.py` | project-venv bootstrap、integration/E2E host 断言及参数化旅程 | project `.venv`、fixture、installer/shim 的公开 CLI | product runtime 的选择或产品实现 |
| `louke/release_identity.py`                                   | 提供无副作用的 tag/version 比较与通用 verifier CLI                 | 标准库                                                                        | 不读取 artifact 格式；host adapter 必须提供已提取的版本                         |
| host project release adapter + host release workflow           | 按该 host 的版本文件、构建工具和 artifact 格式准备、构建、提取版本  | Louke 内置 Python/Node/Go 等全栈 adapter，或假设 `pyproject.toml`              | adapter 是项目架构的一部分；其命令和产物读取规则必须在该项目 M-ARCH 明定并受 gate 验证 |
| `tools/louke_python_release_adapter.py`（仅 Louke self-host） | 作为本仓库 Python/setuptools 的示例：更新 `pyproject.toml` 并读 wheel/sdist 元数据 | 把示例命名/实现当作通用 `lk_bump_version`                                      | 容易被误用为通用机制；仅在 Louke 自身 release workflow 注册，不是安装后项目的默认行为 |

调用方向：`installers → runtime_install → shim/install_cli/upgrade → __main__`；`__main__ → web`；`upgrade → board adapter`；`host release workflow → host release adapter → host build → artifact-version records → release_identity gate → publish`；`project-venv bootstrap → integration/E2E host runner → fixture local/global product runtime`。模块不得反向依赖 Web，也不得令 shim 调用自身 `lk`。

> **Aaron [RESOLVED]:** 要有 `lk_bump_version`，并在架构阶段确定其如何将 tag 版本写入源码、构建和验证 artifact；不可把机制留给 M-DEV。
>> **Aaron:** 错！ 我们不是在谈论 louke 这个项目怎么把版本弄对，而是当 Louke 被用户安装后，如何帮助最终用户在发布产品时，确保他们的 artifact的版本是对的 -- 但最终用户的项目不一定是 python，所以，没有 pyproject.toml 这个文件。这就是我一再说的，为什么要 Archer 根据项目的技术架构 （不是 Louke 的技术架构 -- 除非我们是在用 Louke 开发 Louke 时）来确定如何修改他们的版本。
>>> **Archer:** 接受更正：Louke 的通用保证仅是 tag 与**每个实际待发布 artifact 的已提取版本**的可验证 identity gate；它不读取 `.louke/project/project.toml` 作为产品版本来源，也不假设 `pyproject.toml`、Python 或 setuptools。host project 的 M-ARCH 必须选择/设计其 release adapter/tool：可选 `prepare --tag`（按本项目的版本文件/SCM 规则写入或生成版本）、host build，以及 `inspect --artifact`（输出 artifact 与其嵌入版本）。workflow 把每条 inspect 记录交给 Louke verifier；缺记录、解析失败或不相等均不得发布。本文不把 `lk_bump_version`、adapter registry 或统一 adapter 命令当作通用机制；本仓库的 `louke_python_release_adapter` 仅为 self-host 具体选择，可以改写 Louke 的 `pyproject.toml`，但不能成为最终用户项目的默认机制。请确认：以“host M-ARCH 决定 adapter，Louke 统一验证 tag/artifact identity”的边界取代通用源码改写。

## 2. 发布版本同步：host adapter 边界与本仓库选择

| 设计项 | 任意最终用户 host project 的 M-ARCH 必须确定 | 本 Louke 仓库（self-host）的已选设计 |
| --- | --- | --- |
| 技术栈/真实版本源 | 从实际 build 文件识别；Node 可选择 `package.json`，其他项目选择其真实版本源，绝不默认 Python | Python `>=3.11` + setuptools；真实版本源为根 `pyproject.toml` 的 `[project].version`（当前为 `0.12.1`） |
| adapter/tool | 选择该项目自己的可执行 adapter/tool；其路径或现有 build script 必须写入该项目的 M-ARCH 文档 | host-local `tools/louke_python_release_adapter.py`；不是公共 `lk` 子命令、adapter registry 或安装后用户项目的默认项 |
| 写入策略 | 明定写入版本源、由 SCM 派生，或不写入的原因；明定是否允许工作树变更及清理/恢复 | `prepare --tag TAG` 原子把去一个 `v` 后的 TAG 写入 `[project].version`；只改该字段；release workflow 在 build 后无条件恢复 `pyproject.toml` |
| 构建/产物 | 选择实际 build 命令、候选 artifact 清单和从内容提取版本的方法 | `python -m build` 生成 `dist/*.whl` 与 `dist/*.tar.gz`；分别从 wheel `METADATA`、sdist `PKG-INFO` 读取 `Version` |
| 发布授权 | 每个 artifact 的提取版本交给通用 verifier；任一失败阻断 upload | `lk release verify --tag TAG --artifact-version VERSION` 对 wheel 和 sdist 都 PASS 后才允许 `twine upload` / GitHub Release upload |

本轮**不**引入名为 `lk_bump_version` 的通用命令，也不假设任何 adapter registry 或命令名已获用户认可。上表的 Python tool 是本仓库为使 M-DEV 可实现的 self-host 选择；最终用户的非 Python 项目必须在其自己的 M-ARCH 选择 `package.json` 或其他真实版本源、对应 adapter/tool 和构建工具，M-DEV 只实现该既定选择。

## 3. 关键流程

1. 安装器在当前目录选择最高兼容解释器，创建 `<CWD>/.venv`，并独立创建用户级 global venv；两处均从同一指定包来源安装。成功后安装 PATH shim；重复执行只补齐缺失部分或升级目标版本，PATH 条目不重复。
2. PATH `lk` shim 只测试 `<CWD>/.venv`。存在时以 local Python 委托；否则以 global Python 委托；两者皆缺失时以规定诊断和非零退出。它向底层传递 `LOUKE_RUNTIME_MODE=local|global`，因此 `lk --version` 和 `lk server` 使用同一身份来源。
3. `lk install` 只触碰 CWD local runtime；若 `.venv` 已存在，拒绝且建议 `lk upgrade`。`lk upgrade` 将目标 flags 规范化为 local/global/both，为每个目标运行公开 pip argv；只有成功的 local 更新且检测到 harness 时才调用一次 board。
4. **任意 host project** 的 release workflow 从 HEAD tag 取得 `TAG`，调用该项目 M-ARCH 已选择的 adapter/tool 的可选 prepare，再调用该 host 已选定的 build。adapter 的版本文件、构建工具、是否改写 checkout 均由该项目 M-ARCH 决定；Louke 不读取或改写它们。每个候选 artifact 都必须由同一 adapter 的 inspect 输出单行 JSON `{artifact:string, version:string}`。`version` 是 artifact 内嵌的发布版本，不是文件名推测值。
5. workflow 对每条记录运行 `lk release verify --tag TAG --artifact-version VERSION`（其纯实现为 `verify_release_identity`）。只去掉 tag 的一个前导 `v`；缺 tag、`-dirty`/`+local` 标记、缺/空 version、adapter 非零、JSON 格式错误、artifact 路径不匹配或任一不等均 FAIL，stderr 必须报告 tag、artifact（可用时）、version（可用时）及差异。任何 FAIL 禁止 publish；所有 artifact PASS 才授权 publish。这是跨语言、跨构建工具可验证的最小保证。
6. 当 host 是**本 Louke 仓库**时，release workflow 以 `python tools/louke_python_release_adapter.py prepare --tag TAG` 准备源码，成功 stdout 为唯一 JSON `{"tag":"TAG","version":"X.Y.Z","version_source":"pyproject.toml:[project].version","write":"updated"|"unchanged"}`；再运行 `python -m build`。对 `dist/*.whl` 和 `dist/*.tar.gz` 分别运行 `python tools/louke_python_release_adapter.py inspect --artifact PATH`，成功 stdout 为 I-11 JSON。`prepare` 对缺/非法 tag、不能唯一更新该字段或写入失败非零；build 非零、没有 wheel 或 sdist、inspect 非零/JSON 无效/版本缺失、任一 I-10 FAIL 均不得 publish。workflow 必须在 build 后以 `if: always()` 恢复 `pyproject.toml`。其他 host 不继承此文件名、字段、PEP 440 规则、命令或 `python -m build`；adapter 负责 host build 输入/提取，`release_identity` 负责无副作用真值，artifact gate 是发布授权点。

## 4. 技术栈与依赖

| 选择                    | 版本合同                                                              | 用途                                                                                 | 替代与风险                                                                                                                                     |
| ----------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Python                  | `>=3.11`；CI 3.11/3.12/3.13                                           | 运行时与 installer 选择下限                                                          | 放弃 Python 3.10；解释器发现跨平台不同，由原生矩阵控制                                                                                         |
| setuptools + wheel（仅 Louke self-host adapter） | 现有 `setuptools>=61.0`、`wheel` | 构建 Louke wheel/sdist，并作为 Python adapter 的 artifact inspector 示例 | 放弃把它推广给 host；host M-ARCH 可选其自身稳定构建工具，风险由 host adapter 的 inspect contract 与通用 gate 控制 |
| pip                     | 目标 venv 自带 pip                                                    | 安装/升级                                                                            | 放弃第三方 installer；网络/index 不稳定，以本地 PEP 503 index 测试                                                                             |
| Starlette/uvicorn/httpx | 保持 `starlette>=0.38,<1.0`、`uvicorn>=0.30,<1.0`、`httpx>=0.27,<1.0` | 既有 `lk server` Settings                                                            | 放弃新 Web 框架；1.0 前 API 变化由既有 contract tests 控制                                                                                     |
| pytest + pytest-cov     | 既有 pytest；`pytest-cov` CI 已安装                                   | unit/integration/e2e 与 95% 总门槛                                                   | 放弃 Bats 替换；既有 Bats 保留为回归，新增行为采用 pytest                                                                                      |
| GitHub Actions          | `actions/checkout@v4`、`actions/setup-python@v5`                      | 原生 OS 安装矩阵与 release gate                                                      | 放弃容器 Windows；runner 镜像变化由版本 fixture 适配                                                                                           |

所有依赖与项目 MIT 许可证兼容；不引入新的运行时第三方库。格式化/lint/typecheck 继续使用现有 Ruff `v0.15.20`、mypy `v2.1.0`、pre-commit hooks；文档为 CommonMark Markdown。

## 5. E2E / integration 执行合同

本 spec 的“一套参数化机制”有**两个互不混淆的层**：(1) 唯一 **host runner bootstrap** 是 repo `.venv`，仅承载 `run_e2e.py`、pytest/Playwright、fixture 与断言；(2) 每个参数 case 的 **被测 product runtime** 是 installer 创建的 `<case-cwd>/.venv`（local）或 `<case-home>/.louke/venv`（global），仅承载被测 `lk` / `lk server`。`profile=install|chromium|all` 选择测试目的；`runtime=local|global|both` 选择被测 product runtime；二者是正交维度，均不选择 host Python。runner 的 `sys.executable`、checkout Python、系统 Python 都不得作为 product child；产品 venv 也不得承担 pytest/Playwright host。

install 旅程不要求外部常驻 server。唯一 host bootstrap 为 `tests/e2e/run-project-venv`：Unix 提供无扩展名可执行 launcher，Windows 提供同 basename 的 `run-project-venv.cmd`；这是一个机制的 OS 启动适配，不是两套 runner。Unix 必须解析 repository root 后仅 `exec "<root>/.venv/bin/python" "<root>/tests/e2e/run_e2e.py" ...`（integration 时改为其 integration entry）；Windows `.cmd` 必须仅调用 `"<root>\.venv\Scripts\python.exe" "<root>\tests\e2e\run_e2e.py" ...`。缺少、非文件、不可执行（Unix）或不能启动的解释器必须在 stderr 给出绝对路径并 exit `127`；不得尝试 `python`、`py`、`env python`、`sys.executable` 或 PATH fallback。启动器和 runner 都必须验证 `Path(sys.executable).resolve()` 等于上述 project venv Python、`Path(louke.__file__).resolve()` 位于该 `.venv`，且 `importlib.metadata.version("louke")` 等于 CI/test host 安装的当前 wheel manifest 版本；不符非零并且不启动 product/server child。

> **Archer** [RESOLVED]: 根因确认：原 `[integration]/[e2e].run` 裸调用 `python`，因此 host runner 的解释器、pytest/Playwright 依赖与被测包来源没有被合同约束；同时旧 Chromium server 用 checkout `sys.executable`，会绕过最新 wheel/product runtime。现已改为 `tests/e2e/run-project-venv` project-venv bootstrap：Unix 显式 `.venv/bin/python`，Windows 显式 `.venv\\Scripts\\python.exe`，缺失即 exit 127；runner 与 Chromium product runtime 分别验证 `sys.executable`、`louke.__file__` 和 metadata version，并以静态 gate 禁止裸旧合同。请确认此跨平台同 basename Unix launcher + Windows `.cmd` 的单一 bootstrap 机制，以及 CI 预装 current-wheel 到 repo `.venv` 的前提。


```toml
[integration]
cwd = "."
paths = ["tests/e2e", "tests/integration", "tests/fixtures", "tests/ground_truth"]
framework = "pytest"
run = "tests/e2e/run-project-venv integration"

[e2e]
cwd = "."
paths = ["tests/e2e", "tests/fixtures", "tests/ground_truth"]
framework = "pytest"
run = "tests/e2e/run-project-venv e2e --profile all --runtime both"
```

> **Aaron [RESOLVED]:** E2E 必须是一套参数化机制；按目的选择 local/global runtime。
>> **Archer:** 是一套机制而非一个 Python：`run-project-venv[.cmd]` 永远只启动 repo `.venv` 的 runner；runner 用 `(profile,runtime)` 笛卡尔积建立 case。`install`/`chromium` 只决定执行哪一组旅程，`local`/`global` 只决定该旅程所启动 product child 的绝对 Python。例：`--profile chromium --runtime global` = repo `.venv` 跑浏览器断言，临时 HOME 的 global venv 跑 server；绝不是 repo `.venv` 跑 server。错误示例一律 FAIL：`python -m louke serve`、`sys.executable -m louke serve`、从 repo `.venv` 导出的 `LOUKE_E2E_SERVER_PYTHON`，或让 product venv 执行 pytest。启动 product 前必须验证 product Python 不等于 runner Python、不在 repo `.venv`、其 `louke.__file__` 位于 selected case venv 且 metadata version 等于 fixture wheel；bootstrap 同时验证 runner 必须位于 repo `.venv`。这些双向规则防止旧 v0.13 `python -m louke` 合同复发。请确认该“固定 host bootstrap + 参数化 product runtime”的两层定义。

统一 runner 合同：(1) `--profile install` 运行本期 installer→PATH shim→upgrade 旅程；`--profile chromium` 运行既有 `chromium_e2e` server/browser 回归；`--profile all` 按 install 后 chromium 顺序运行两者。`--runtime local`、`global` 分别只运行该模式；`both` 对每个 profile 各运行一次。(2) runner 为每个 `(profile,runtime)` case 创建独立 `HOME`（Windows 同时 `USERPROFILE`）、空 case CWD 与只含 fixture Python、fixture index server 和临时 user-bin 的 `PATH`；保留 OS 必需系统目录但不继承真实 `~/.louke`、shell rc 或已安装 `lk`。(3) **local**先在 case CWD 执行真实 installer 或 global shim 的 `lk install` 建立 `.venv`，随后仅从该 CWD 运行 PATH `lk`；**global**先在 seed CWD 执行 installer 建立临时 HOME global venv，随后在无 `.venv` CWD 运行 PATH `lk`。(4) install profile 的 product child 是 shim/目标 runtime；Chromium profile 从已验证的 case local/global product runtime 取得 `LOUKE_E2E_SERVER_PYTHON`，并且只以该绝对路径执行 `-m louke serve`。该值不得等于 runner `sys.executable`，不得位于 repo `.venv`；`import louke` 路径与版本必须分别位于 case product venv、等于 fixture wheel 版本，否则失败。裸 `python -m louke`、checkout `sys.executable -m louke`、系统 Python server 启动一律禁止。(5) installer、shim、pip、board、server 都是真实子进程；runner 只设置边界/收集 exit、stdout、stderr、argv；pytest 仅是断言宿主。(6) 无效参数、组合失败或子 suite 失败均非零；runner 在 finally 终止 server、关闭 index 和清理临时资源。集成层使用相同 bootstrap，但不另造 runner。

不设 `start`、`ready`、`teardown`：runner 自己拥有 fixture HTTP/index/server 生命周期并以 finally 清理临时 HOME/PATH/CWD；故没有可裸调用 `python -m louke` 的 server 生命周期合同。CI 以该唯一 `run` 在 `ubuntu-22.04`、`macos-13`、`macos-14`、`windows-2022` 原生运行；Windows 禁止 WSL/Docker。Chromium 通过同一 `--profile chromium` 参数保留。静态回归 gate 扫描本 spec `[integration]/[e2e].run`、bootstrap 与 runner 资产：命中裸 `python tests/e2e`、裸 `python tests/integration`、裸 `python -m louke` 或 `sys.executable -m louke` 即失败；唯一允许的 `-m louke` 前缀是已验证的 product runtime 绝对路径。

## 6. AC、接口与测试闭环

| AC 范围                             | interfaces.md 出口                                                   | test-plan 验证位置            |
| ----------------------------------- | -------------------------------------------------------------------- | ----------------------------- |
| FR-1501—1503、NFR-1502、NFR-1503-01 | I-01—I-04 安装器/运行时/PATH 文件出口                                | §2、§4「安装与全局暴露」      |
| FR-1504—1506                        | I-05 shim 委托与版本出口                                             | §4「shim 与版本身份」         |
| FR-1507—1509、NFR-1503-02/03        | I-06 install/upgrade CLI、I-07 process record、I-08 harness manifest | §4「安装/升级命令与 harness」 |
| FR-1510、NFR-1504                   | I-10 通用 verifier、I-11 host adapter、I-12 artifact gate            | §3、§4「发布与 UI」           |
| FR-1512                             | I-15 Settings runtime read model/DOM                                 | §4「发布与 UI」               |

I-05—I-09、I-11—I-15 的 `modules` 列跨两个或更多模块，均由 `tests/integration/install_experience` 覆盖；所有出口至少有 unit、integration 或 e2e 的 §4 策略。Devon 可按模块/API 写实现和 unit，Shield 可按本节资产路径及接口出口准备环境和 E2E。
