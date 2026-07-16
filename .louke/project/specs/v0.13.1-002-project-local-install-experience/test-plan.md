# v0.13.1 项目本地安装体验 + 发布身份同步 — Test Plan

- **Spec ID**: `v0.13.1-002-project-local-install-experience`
- **Created**: 2026-07-16
- **Related acceptance**: `.louke/project/specs/v0.13.1-002-project-local-install-experience/acceptance.md`
- **Related interfaces**: `.louke/project/specs/v0.13.1-002-project-local-install-experience/interfaces.md`（M-ARCH 产出；断言出口见 §6.5）

## 1. 立场与边界

### 1.1. Black-box Statement

仅断言用户可见出口：安装脚本/`lk` 的退出码、stdout/stderr、`--version` 文本、实际创建的 `.venv` 与 PATH 可执行文件、真实子进程 argv、构建产物元数据，以及 `lk server` Settings 页面。不会读取私有对象、实现模块内部状态，或替换 louke 自身调度逻辑。

### 1.2. Non-observable Objects (tests do not directly depend on)

- shim、安装器、upgrade、release 或 server 的私有函数、类层级和中间数据；
- 源码结构、monkeypatch 调用次数、私有缓存；
- 未在 M-ARCH `interfaces.md` 定义的内部 harness 判定。

`board`、pip 或 Python 委托只通过真实 CLI 发起的外部子进程 argv/退出码验证；不替换被测 louke 的命令分派。

### 1.3. Cheating Patterns (CI enforced interception)

| # | Cheating Pattern | Typical Symptom |
| --- | --- | --- |
| 1 | 改断言迎合实现 | 把 non-zero 改成仅检查输出 |
| 2 | skip 逃避 | 无 issue 链接的平台 skip |
| 3 | 断言弱化 | 只检查目录，未执行 `import louke` |
| 4 | 吞掉失败 | `try/except: pass` 覆盖安装失败 |
| 5 | 过度 mock | 替换 louke shim/upgrade/board |
| 6 | 循环真值 | 用被测版本解析实现计算预期 |
| 7 | 硬编码偶然值 | 不从 fixture tag/包元数据计算版本 |
| 8 | 无意义通过 | `assert True` 或仅对象非空 |

### 1.4. Safeguards (CI checks + PR process)

1. 每个测试函数首行注释或 docstring 写完整 AC ID；`lk agent archer ci-scan` 检查 AC 与测试双向闭合。
2. 禁止单独真值断言、无依据 skip、吞异常和 mock louke 内部；平台不可用只能由 CI job 条件控制。
3. PR 必须标注新 AC、spec 变更或环境修复；“实现与 spec 不一致所以改测试”不接受。
4. 若 M-ARCH 未提供 AC 所需出口，先补 interfaces.md；不得窥探实现绕过。

### 1.5. Test Division of Labor

- **Devon**：`tests/unit/` 的纯版本契约、CLI 参数/目标选择、命令构造及 UI 对公开运行时信息的单元测试。
- **Shield**：`tests/integration/install_experience/` 的真实子进程/临时 HOME-CWD-PATH 集成测试，及 `tests/e2e/install_experience/` 的安装、双运行时、升级和原生平台旅程。
- **共同**：只使用本计划及后续 interfaces.md 的公开出口；Shield 不替代 Devon 的单元断言。

---

## 2. Test Environment

### 2.1. Directory Layout (recommended)

```
tests/
├── e2e/run-project-venv[.cmd]        # shared project-venv launcher
├── unit/install_experience/          # pytest：纯契约与公开 CLI 参数
├── integration/install_experience/   # pytest -m integration：真实 CLI + 临时环境
├── e2e/install_experience/           # pytest -m e2e：跨进程用户旅程
├── fixtures/install_experience/      # wheel、简单索引、harness 项目、版本 fixture
└── ground_truth/                     # 独立版本规范化真值
```

现有 Bats 回归测试保留；本 spec 新增测试使用既有 `pytest`（`[meta].test_framework = "pytest"`）。命名为 `test_<scenario>__<variant>.py` / `test_ac_<fr>_<ac>_<meaning>`；每个函数必须带 AC 标记。

### 2.2. Execution

CI/test host 先在 `<repo>/.venv` 安装由当前 checkout 构建的 wheel 与全部 test dependency；单元、integration 和 E2E runner 都由该 project venv 运行。integration **只**执行 `[integration].run` 的 `tests/e2e/run-project-venv integration`；E2E **只**执行 `[e2e].run` 的 `tests/e2e/run-project-venv e2e --profile all --runtime both`，不得为 install/Chromium 维护两套入口。Unix bootstrap 只调用 `.venv/bin/python`，Windows `.cmd` 只调用 `.venv\Scripts\python.exe`；目标解释器不存在/不可启动时打印绝对路径并 exit `127`，绝不回退裸 `python`、`py`、PATH 或 checkout `sys.executable`。runner 开始前断言其 `sys.executable` 是 project venv Python，`import louke` 文件在 project `.venv`，metadata version 等于 current-wheel manifest。runner 可启动 pytest 作断言宿主，但被测 `lk` 或 server 必须是 case local/global product runtime 的真实子进程，绝不以 checkout Python 代替。

单一 `tests/e2e/run_e2e.py` 接受 `--profile install|chromium|all`、`--runtime local|global|both`。`all` 先跑本期 install profile，再跑既有 Chromium profile；`both` 对每个 profile 各跑 local/global。每个 `(profile,runtime)` case 由 runner 创建临时根目录：`HOME`（Windows 同时 `USERPROFILE`）指向临时用户目录，`CWD` 指向独立 case 项目，`PATH` 仅注入 fixture Python、临时 user-bin、fixture index server 所需命令和 OS 系统目录，不继承真实 `~/.louke`、shell rc 或既有 `lk`。**local**先在 case CWD 用真实 installer 或 global `lk install` 建立 `.venv`，随后在同一 CWD 经 PATH `lk` 运行；**global**先在 seed CWD 用 installer 建立临时 HOME global runtime，随后从无 `.venv` CWD 经 PATH `lk` 运行。Chromium profile 的 `LOUKE_E2E_SERVER_PYTHON` 必须是已选择 case product venv 的绝对 Python 路径，且不等于 runner Python、也不在 repo `.venv`；该解释器执行探针以验证 `sys.executable`、`louke.__file__` 位于 product venv、metadata version 等于 fixture wheel manifest，成功后才允许 `<product-python> -m louke serve`。installer、shim、pip、board、server 都是真实子进程；runner 只能准备环境并观察 exit/stdout/stderr/argv，finally 清理所有临时资源。

CI 在 `ubuntu-22.04`、`macos-13`、`macos-14`、`windows-2022` 原生执行首次安装 E2E；每个平台覆盖可用 Python 3.11、3.12、3.13，并以多版本 fixture 验证最高兼容版本选择。Windows job 不得经 WSL、Docker 或虚拟化代理。

### 2.3. Test Data

`tests/fixtures/install_experience/` 保存由当前源码构建的可安装测试 wheel 和本地 PEP 503 simple index；同一 wheel 先安装进 repo `.venv`（runner）再由 fixture index 安装进 case product venv。测试 HTTP 服务仅替代外部 PyPI/curl 下载，不实现 louke 行为。fixture manifest 记录 wheel 版本、校验和、runner/project Python 绝对路径及每个 product Python 路径。最小临时项目覆盖无 harness、有 harness、CWD `.venv`、仅父目录 `.venv` 与缺失运行时。

Unix 用受控 `PATH` 提供多版本 Python 启动器；Windows 在原生 runner 以 `py -3.x`/已安装解释器准备等价情形。成功必须实际执行 venv Python 的 `import louke`。

---

## 3. Ground Truth Method

### 3.1. General Principle

独立真值是标准库脚本：从 fixture manifest 读取 tag 和包版本，tag 只允许去掉一个前导 `v`，比较规范化 tag 与包版本的逐字节值。其用于 FR-1510/NFR-1504 PASS/FAIL、dirty/缺失 tag 的预期；其余断言以 OS 文件、进程退出码、`pip show louke` 与页面文本为真值。

### 3.2. Ground Truth Isolation (mandatory rule)

真值脚本位于 `tests/ground_truth/`，只可导入标准库和 fixture 数据，不可导入 `louke` 或调用其 CLI；变更由 Shield 审阅。版本预期不得从被测发布身份契约返回值反向取得。

---

## 4. Test Scope

覆盖 spec 中所有 ✅ FR-1501—FR-1510、FR-1512、NFR-1502—NFR-1504 及 story 的七个场景。以下是按可观察行为组织的验证策略，不是测试用例/coverage matrix：

- **安装与全局暴露**：在干净 clone CWD 运行 Unix `curl | bash`、Windows `install.bat` 和 `install.ps1`；验证本地/独立全局 venv、包导入、PATH `lk`、rc/PATH 幂等、无兼容 Python/无 `python3` 的可操作失败，以及 Windows Restricted policy。覆盖 AC-FR1501-01—04、AC-FR1502-01—04、AC-FR1503-01—04、AC-NFR1502-01—03、AC-NFR1503-01。
- **shim 与版本身份**：从本地 venv CWD、无 venv 子目录、仅全局目录和无运行时目录调用真实 PATH `lk`；使用运行时输出、argv 与 `pip show louke` 比较委托目标及 `<version> (local|global)`。覆盖 AC-FR1504-01—04、AC-FR1505-01—03、AC-FR1506-01—03。
- **安装/升级命令与 harness**：在临时项目执行 `lk install`、默认/`--local`/`--global`/`--both` upgrade，以本地索引实际升级；从公开子进程记录验证 pip `--index-url`/`louke==version`、成功后 board、pip 失败不 board、无 harness no-op、冲突/缺失目标错误及重复运行幂等。覆盖 AC-FR1507-01—04、AC-FR1508-01—05、AC-FR1509-01—04、AC-NFR1503-02—03。
- **发布与 UI**：以 stub tag/artifact version 对 I-10 纯契约及 CLI 断言 PASS/FAIL；用语言无关的 fake host adapter/tool 验证已选 `prepare`（如有）→ host build → 每 artifact `inspect` JSON → I-10 gate 的顺序，缺失/非法 tag、写入失败、build 失败、无 artifact、错误记录或任一 mismatch 必须阻断 upload。对于本 Louke self-host，Shield 以真实 `python tools/louke_python_release_adapter.py prepare --tag TAG` 验证只更新 `pyproject.toml [project].version`、输出 I-12 JSON，并以真实 `python -m build` 的 wheel/sdist 验证 inspect；finally 恢复版本源。该 Python 测试只覆盖本仓库已选 adapter，不是其他 host 的要求：非 Python host 必须由其 M-ARCH 按其实际 `package.json` 或其他版本源和构建工具替换这一段设计，M-DEV 只实现已选 adapter/tool。启动 `lk server` 后由浏览器或现有 Web TestClient 导航 Settings，验证每次渲染显示当前 `<version> (local|global)`，且与项目/venv 元数据并列。覆盖 AC-FR1510-01—03、AC-NFR1504-01—02、AC-FR1512-01—02。
- **runner/runtime 身份与旧合同回归**：integration 运行 bootstrap 后验证 runner 三元组（`sys.executable`、`louke.__file__`、metadata version）只来自 repo `.venv` 与 current-wheel manifest；E2E 对每个 `(profile,runtime)` 验证 profile 只选旅程、runtime 只选 case product venv，Chromium server 三元组只来自该 product venv。静态检查 `[integration]/[e2e].run`、bootstrap、runner 和 Chromium asset，命中裸 `python tests/e2e`、裸 `python tests/integration`、裸 `python -m louke`、checkout `sys.executable -m louke`、repo `.venv` 作为 `LOUKE_E2E_SERVER_PYTHON` 或 product venv 运行 pytest 即失败；缺 project venv 也必须 exit `127` 而非 fallback。覆盖 I-13/I-14，并防止 v0.13 的依赖缺失或陈旧 checkout product 回归。

---

## 5. Acceptance Criteria

1. 上述所有 AC 都有至少一个带 AC ID 的 pytest 测试，且 `ci-scan` 闭合。
2. 单元层覆盖无副作用版本契约、目标/参数验证和公开命令构造；集成层覆盖 CLI→运行时/pip/board 与 server→UI 组合；E2E 覆盖脚本/PATH `lk` 开始的跨进程安装和升级。
3. 覆盖率遵循 `pyproject.toml` 全局 `fail_under = 95`；不得用 skip/exclude 降低门槛。
4. 四平台首次安装 E2E 与 release identity PASS/FAIL gate 都是 CI 阻断项。

---

## 6. External Dependency Layered Testing (project optional)

### 6.1. Three Unavoidable Constraints

| # | Constraint | Consequence |
| --- | --- | --- |
| C1 | PyPI、GitHub raw、HOME/PATH 与解释器安装是环境依赖 | 生产网络不可成为 CI 真值 |
| C2 | Windows shell policy 与 Unix shell rc 不同 | 必须由原生 runner 验证 |
| C3 | pip、Python、board 是外部进程 | 可控来源/记录进程，不能替换 louke 决策 |

### 6.2. Stance: Controllable vs Mock

本地 simple index、HTTP 脚本源、临时 HOME/PATH、受控解释器和外部子进程 recorder 是可控外部依赖。必须运行真实安装脚本、shim 和 venv Python；不得 mock runtime 选择、upgrade、release 契约或 Settings 渲染。

### 6.3. Three-Layer Test Pyramid

| Layer | Name | Default Run | Boundary |
| --- | --- | --- | --- |
| L1 | unit | CI | 版本契约、参数互斥、规范化、命令参数 |
| L2 | integration | CI；`tests/e2e/run-project-venv integration` | repo `.venv` host runner 的身份检查、真实 CLI 与临时 venv/index/HOME 组合、server UI 合成；每个 product child 经对应 local/global runtime |
| L3 | e2e | CI 平台矩阵；`tests/e2e/run-project-venv e2e --profile all --runtime both` | 参数化 install 与既有 Chromium server/browser 回归；repo `.venv` runner 与 product venv 身份隔离、curl/bat/ps1、PATH shim、双运行时、升级、release workflow smoke |

L3 标记 `e2e`，无 issue 不可 skip；网络仅使用 fixture 服务，仍可重复。

### 6.4. Responsibility Contract of Test Infrastructure

| Component | Responsibility (external) | Boundary |
| --- | --- | --- |
| local package index | 提供固定 wheel 和安装请求记录 | 不判断 upgrade 目标/版本 |
| script HTTP source | 为 `curl` 提供真实 install.sh | 不执行安装逻辑 |
| process recorder | 捕获真实 pip/python/board argv、顺序和退出码 | 不生成或改写 louke 命令 |
| temporary user home | 隔离 `.louke`、rc、PATH | 不模拟文件系统语义 |
| browser/TestClient | 从公开页面/HTTP 读取 Settings | 不读 server 内部状态 |

### 6.5. Assertion Basis — Closure with interfaces.md

M-ARCH 必须在 `interfaces.md` 定义本计划使用且必须覆盖的出口：安装器与 `lk install/upgrade` CLI 参数/退出码/stdout/stderr；shim 委托和 `lk --version` stdout；本地/全局 runtime、PATH shim、rc/PATH 文件；可观察 pip/board 子进程记录；通用 tag/artifact verifier、host adapter/tool 的 prepare/inspect JSON、版本写入策略、build artifact 与 release gate；参数化 local/global runtime bootstrap 与 Chromium server；Settings 页面运行时文本。host 的版本文件、构建工具和版本提取规则只由该 host 的 M-ARCH 从真实技术栈选择；测试不得假定 `pyproject.toml`。本仓库选择 Python adapter 是 self-host 个例；非 Python 项目以其 `package.json` 或其他真实版本源替换。缺出口时不得以私有实现替代断言。

本期接口出口已锁定为 I-01—I-15：安装/双 venv/PATH 为 I-01—03，`lk install` 为 I-04，shim/版本为 I-05—06，upgrade/pip-board/harness 为 I-07—09，通用 verifier/host adapter/artifact gate 为 I-10—I-12，project-venv bootstrap 为 I-13，参数化 runtime/bootstrap 为 I-14，Settings read model/页面为 I-15。§4 覆盖这些出口；跨模块 I-02—09、I-11—I-15 必须由 `tests/integration/install_experience/` 覆盖，不能仅保留 unit 或 E2E。

---

## 7. CI Gate

```bash
lk agent archer ci-scan \
  --acceptance .louke/project/specs/v0.13.1-002-project-local-install-experience/acceptance.md \
  --tests tests/
```

验证 AC 引用闭合、反模式静态扫描、覆盖率 ≥95% 与 ground truth 隔离；平台矩阵执行 §2.2 原生安装 E2E 和 release identity gate。

---

## 8. Judge Review Checklist

- [x] 覆盖安装、双运行时调度、升级、发布与 Settings 风险
- [x] 每个 AC 归入可执行验证策略并要求测试 AC 标记
- [x] 不维护逐条测试用例或 coverage matrix
- [x] 定义 `ci-scan` 与反模式限制
- [x] fixture、索引与 HOME/PATH 可重复
- [x] 明确 unit/integration/e2e 目录与责任边界
- [x] 发布版本真值独立于被测实现
- [x] 外部依赖以受控 stand-in 分层
- [x] M-ARCH 完成 interfaces.md 后复核最终出口闭合
