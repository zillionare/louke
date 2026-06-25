# {Feature 标题} — Test Plan

- **Spec ID**: {SPEC-ID}
- **创建日期**: {YYYY-MM-DD}

## 测试策略

用 3-7 条说明本功能的测试策略：哪些风险最高、哪些路径必须 E2E、哪些逻辑必须单元测试隔离验证。

> 测试用例住在代码中，不在 test-plan 表格中维护。覆盖矩阵由 `specforge ci-scan` / `tools/check_acs.py` 从测试代码反向生成。

## 测试层级

| 层级 | 用途 | 本项目约定 |
|---|---|---|
| unit | 快速、隔离、验证单个函数/模块/规则 | {如何放置、如何运行} |
| integration | 可选：验证模块间协作 | {若不用则写 N/A} |
| e2e | 从用户/API/CLI 入口验证完整场景 | {如何放置、如何运行} |

## AC 追溯约定

每个有效测试必须在 docstring 或注释中引用至少一个 AC ID：

```text
AC-FR001-01
AC-FR001-02
AC-NFR010-01
```

推荐示例：

```python
def test_example():
    """AC-FR001-01: 描述该测试覆盖的验收点。"""
    ...
```

非 Python 项目也使用同一纯文本 ID，可写在注释中。

## 覆盖率目标

- 需求追溯覆盖：acceptance.md 中每个 AC 必须被 ≥1 个测试引用。
- 代码覆盖率：目标 ≥95%。具体覆盖率工具由项目语言决定（coverage.py / nyc / go test -cover / cargo tarpaulin / lcov 等）。
- `<95%` 默认不接受；若有例外，必须链接 issue 并写明原因。

## 反模式与 CI 门禁

CI 应运行：

```bash
specforge ci-scan --acceptance .specforge/project/specs/{SPEC-ID}/acceptance.md --tests tests/
```

禁止的作伪模式包括：

- `assert True` / `assert 1`
- 无 AC 引用的弱断言（如只断言 not None）
- `try: ... except: pass`
- 无 issue/URL/AC 的 skip / xfail
- 空测试函数
- 测试主体中的 TODO / NotImplemented 且无 issue/URL

## 测试数据

说明测试数据来源、版本、可复现方式、是否可入库、如何在 CI 中获取。

- 小型离线数据：建议放 `tests/assets/`
- 大型真实数据：项目自行约定路径与下载/构建脚本
- 敏感数据：不得入库，必须 mock 或用合成数据

## 推荐 tests/ 布局

该布局是建议，不强制。历史项目可保持现状。

```text
tests/
├── unit/          # 单元测试；建议镜像源码树，但不强制
├── e2e/           # 端到端场景测试
├── assets/        # 离线、可复现测试数据
└── ground_truth/  # 可选：纯实现/参考实现；不得 import 被测系统
```

`ground_truth/` 仅适用于算法、规则引擎、金融计算等需要独立参考实现的项目。

## Judge 评审清单

- [ ] 测试策略覆盖主要风险
- [ ] 每个 AC 都能在测试代码中反向追踪
- [ ] test-plan 不维护具体测试清单/覆盖矩阵
- [ ] 反模式 CI 门禁已启用或有明确豁免
- [ ] 测试数据来源可复现
- [ ] tests/ 布局已说明（使用推荐布局或说明项目自定义布局）
