# 009 — 测试质量标准: AC 追溯、反模式扫描与 tests/ 布局建议

- **状态**: 已采纳
- **日期**: 2026-06-25
- **关联 spec**: v0.5-008-test-quality-standards
- **关联 issue**: #71, #72

## 背景

Millionaire 项目临时维护了 `check_acs.py` 与 `check_assertions.py`，用于检查 AC 追溯与测试作伪模式。这些规则不是 Millionaire 特有，而是 specforge 项目的通用质量门禁。

同时，specforge 缺少推荐的 `tests/` 结构，导致新项目在 unit/e2e/assets/ground_truth 的职责划分上反复讨论。

## 决策

### 1. test-plan 是策略文档

`test-plan.md` 不维护测试用例清单，不维护覆盖矩阵。

实际测试用例住在代码里，通过 docstring/comment 引用 AC ID：

```text
AC-FR001-01
AC-NFR010-01
```

覆盖矩阵由 `check_acs.py` 从测试代码反向生成。

### 2. specforge 原生提供 CI 静态扫描工具

新增：

- `tools/check_acs.py`
- `tools/check_assertions.py`
- `tools/ci_scan.py`
- `specforge ci-scan`

### 3. 推荐 tests/ 布局，但不强制

```text
tests/
├── unit/
├── e2e/
├── assets/
└── ground_truth/  # 可选
```

`ground_truth/` 仅适合算法、金融计算、规则引擎等需要独立参考实现的项目，不作为通用强制项。

### 4. 不使用 Python 专属术语作为通用要求

`fixture`、`conftest.py` 是 pytest 生态术语，只能作为 Python 示例，不进入通用要求。

## 备选

### A. 继续让各项目复制 Millionaire 工具

拒绝。会导致工具分叉、规则漂移、bug 修复无法共享。

### B. 从 spec 自动生成 test-plan 覆盖矩阵

拒绝。覆盖矩阵应从真实测试代码反向生成，否则容易成为过期文档。

### C. 强制 scaffold Millionaire tests/ 布局

拒绝。Millionaire 的 `ground_truth/`、真实行情数据与 Python fixture 是项目特定设计。

## 后果

- specforge 项目可以直接在 CI 中运行 `specforge ci-scan`
- `templates/test-plan.md` 变为策略文档
- Probe/Judge/Herald prompt 改为围绕策略、门禁与真实测试代码
- #71/#72 关闭
