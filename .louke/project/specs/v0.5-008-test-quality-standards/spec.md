# 测试质量标准化: CI 静态扫描工具 + tests/ 布局建议 — Spec

- **Spec ID**: v0.5-008-test-quality-standards
- **来源**: issue #71, #72
- **创建日期**: 2026-06-25
- **状态**: 草稿

## 背景

Millionaire 项目临时维护了 `.specforge/tools/check_acs.py` 与 `check_assertions.py`, 用于:

- AC 双向追溯: 测试 docstring/comment 必须引用 `AC-FRXXX-YY`; acceptance.md 中每条 AC 必须被至少一个测试引用
- Assertion hygiene: 禁止 `assert True`, `try: except: pass`, 无 issue 链接的 `pytest.skip/xfail` 等作伪模式

这些规则不是 Millionaire 特有, 是 specforge 方法论的通用质量门禁。

同时, specforge 当前没有推荐的 `tests/` 目录布局。Millionaire 的布局有价值, 但其中 `conftest.py`, `fixture`, `ground_truth` 等是 Python/量化项目强相关, 不应强制推广到所有项目。

## 目标

1. specforge 原生提供 `check_acs.py` 与 `check_assertions.py`, 作为安装/初始化后可用的通用 CI 工具。
2. 重写 `templates/test-plan.md` 为**测试策略文档**, 不再列 UT 清单/覆盖矩阵。
3. 给出推荐 `tests/` 结构: `unit/`, `e2e/`, `assets/`, 可选 `ground_truth/`; 仅建议, 不强制。
4. 建立 `AC traceability` 与 `coverage >= 95%` 的方法论边界: test-plan 讲策略, 工具从代码反查覆盖。

## 非目标

- 不为项目自动生成具体 UT/E2E 测试清单。
- 不从 spec.md 自动生成覆盖矩阵。
- 不强制 Python/pytest 布局。
- 不强制 `ground_truth/` 存在。
- 不在本 spec 实现 coverage.py / lcov / nyc 等语言特定覆盖率采集；本 spec 只定义 traceability/hygiene 静态扫描。

## 用户故事

### US-010
story: 作为 specforge 用户, 我希望每个测试都能反向追溯到 acceptance.md 中的 AC, 以便 CI 能阻止"测试存在但不覆盖需求"的虚假质量。
priority: P0

### US-020
story: 作为 specforge 用户, 我希望 CI 能发现作伪测试 (`assert True`, 空 catch, 无理由 skip), 以便防止测试看似通过但没有断言价值。
priority: P0

### US-030
story: 作为 specforge 用户, 我希望 test-plan.md 只描述测试策略/约定, 不列具体测试用例表, 以便真实覆盖矩阵从测试代码反向生成, 避免文档与代码漂移。
priority: P0

### US-040
story: 作为 specforge 用户, 我希望有一个跨语言可用的推荐 tests/ 布局, 以便新项目有默认结构, 但历史项目不被强制迁移。
priority: P1

## 功能需求

### FR-010 内置 `tools/check_acs.py`

新增 `tools/check_acs.py`, stdlib-only, 支持:

```
python3 tools/check_acs.py --acceptance .specforge/project/specs/<id>/acceptance.md --tests tests/
```

功能:

1. 解析 acceptance.md 中的 AC 列表, 支持两种格式:
   - `### AC-1` / `### AC-2` (当前模板常见)
   - `AC-1:` / `AC-2:` (兼容旧写法)
2. 生成 canonical AC id: `AC-FR010-01`, `AC-NFR020-02`。
3. 扫描测试文件中的 AC 引用:
   - Python docstring/comment: `AC-FR010-01`
   - JS/TS/Go/Rust/Bash 等 comment 中同样匹配纯文本 `AC-FR010-01`
4. 检查:
   - acceptance.md 中每个 AC 至少被一个测试引用
   - 测试中引用的 AC 必须存在于 acceptance.md
5. 输出 human-readable report + `--json` 机器可读 report。
6. 支持 `--legacy-baseline <file>`: baseline 中列出的 missing AC 只 warning, 不 fail。

退出码:
- 0 = 全部通过
- 1 = traceability 失败
- 2 = 参数/文件错误

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### FR-020 内置 `tools/check_assertions.py`

新增 `tools/check_assertions.py`, stdlib-only, 支持:

```
python3 tools/check_assertions.py --tests tests/
```

检查作伪模式 (初版跨语言 + Python 强化):

| ID | 模式 | 说明 |
| -------- | ------ | ---------- |
| FAKE-001 | `assert True` / `assert 1` | 无效断言 |
| FAKE-002 | `assert x is not None` 且无 AC 引用 | 弱断言, 只在无 AC 时 fail |
| FAKE-003 | `try: ... except: pass` | 吞异常 |
| FAKE-004 | `except Exception: pass` | 吞异常 |
| FAKE-005 | `pytest.skip(...)` 无 issue/URL/AC 引用 | 无追踪 skip |
| FAKE-006 | `pytest.mark.skip` / `xfail` 无 issue/URL/AC 引用 | 无追踪 skip/xfail |
| FAKE-007 | 测试函数体只有 `pass` / `return` | 空测试 |
| FAKE-008 | `TODO` / `NotImplemented` 出现在测试主体且无 issue/URL | 未完成测试 |

输出:
- 默认 human-readable
- `--json` 输出 machine-readable
- `--legacy-baseline <file>` 支持历史债务 baseline, baseline 命中只 warning

退出码:
- 0 = 全部通过
- 1 = assertion hygiene 失败
- 2 = 参数/文件错误

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### FR-030 新增 `specforge ci-scan`

`bin/specforge` 新增命令:

```
specforge ci-scan --acceptance <path> --tests <dir> [--json]
specforge ci-scan --spec <spec-id> --tests tests/ [--json]
```

行为:
1. 先运行 `check_acs.py`
2. 再运行 `check_assertions.py`
3. 任一失败则整体 exit 1
4. `--json` 时合并两个工具的 JSON report

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### FR-040 重写 `templates/test-plan.md` 为策略文档

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

删除当前模板中的:
- 单元测试表
- 集成测试表
- E2E 测试表
- 覆盖矩阵

改为以下结构:

- `# {Feature 标题} — Test Plan`
- `## 测试策略`
- `## 测试层级`
- `## AC 追溯约定`
- `## 覆盖率目标`
- `## 反模式与 CI 门禁`
- `## 测试数据`
- `## 推荐 tests/ 布局`
- `## Judge 评审清单`

必须明确:
- 测试用例住在代码中, 不住在 test-plan 表格中
- 每个测试通过 docstring/comment 引用 `AC-FRXXX-YY`
- 覆盖矩阵由 `check_acs.py` 反向生成
- 覆盖率目标: `<95%` 不接受 (但语言具体覆盖率工具由项目选择)

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### FR-050 推荐 tests/ 布局 (建议不强制)

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

在 `templates/test-plan.md` 与 ADR 中推荐:

```
tests/
├── unit/          # 单元测试, 建议镜像源码树 (不强制)
├── e2e/           # 端到端场景测试
├── assets/        # 离线、可复现测试数据
└── ground_truth/  # 可选: 纯实现/参考实现, 禁止 import 被测系统
```

约束:
- `unit/` 与 `e2e/` 推荐存在, 但不由工具强制
- `assets/` 推荐用于测试数据, 命名可项目自定
- `ground_truth/` 明确标注为可选, 仅适合算法/金融/规则引擎等需要参考实现的项目
- 不出现 Python 专属词作为通用要求 (`fixture`, `conftest.py` 只能作为 Python 示例)

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### FR-060 更新 Probe / Judge prompt

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

- Probe: 生成 test-plan 时只写策略, 不列测试清单/覆盖矩阵。
- Judge: 审查 test-plan 的策略完整性, 不要求 test-plan 含所有 UT 明细。
- Herald: 验收时优先运行 `specforge ci-scan` 读取真实测试代码覆盖。

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

## 非功能需求

### NFR-010 stdlib-only

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

`check_acs.py` / `check_assertions.py` 只能使用 Python stdlib, 不引入 pytest/coverage/yaml 依赖。

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### NFR-020 测试覆盖

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

新增:

- `tests/test_ci_tools.bats`
- `tests/fixtures/ci-tools/acceptance.md`
- `tests/fixtures/ci-tools/tests_good/`
- `tests/fixtures/ci-tools/tests_bad/`

覆盖:
- AC 全覆盖 pass
- missing AC fail
- unknown AC fail
- legacy baseline downgrade 为 warning
- assert True fail
- try/except/pass fail
- skip without issue fail
- JSON 输出合法
- `specforge ci-scan` 聚合两个工具结果

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### NFR-030 ADR 留痕

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

新增 `.specforge/wiki/decisions/009-test-quality-standards.md`, 记录:

- test-plan 是策略文档, 不是测试清单
- 覆盖矩阵从测试代码反向生成
- 推荐 tests/ 布局但不强制
- ground_truth 可选
- `fixture` 非通用术语, 只作 Python 示例

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

---

### NFR-040 关闭 issue

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |

实施后关闭:
- #71 — 内置 CI 静态扫描工具
- #72 — 推荐 tests/ 目录布局

每个 issue comment 引用实现 commit 和对应 FR。

| 有效需求 | 可测性 | 是否已决定 |
| -------- | ------ | ---------- |
| ✅        | ✅      | ✅          |
