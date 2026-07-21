# Test Plan: synthetic-001-demo

## 1. Test Strategy

| Layer | Count | CI |
|-------|-------|----|
| Unit | 3 | yes |
| Integration | 2 | yes |
| E2E | 1 | no |

## 2. Directory Layout

```
tests/
├── unit/synthetic_001_demo/
├── integration/synthetic_001_demo/
└── e2e/synthetic_001_demo/
```

## 3. Test Matrix

| AC ID | Required layers | CI |
|-------|----------------|----|
| `AC-FR0100-01` | U+I | yes |
| `AC-FR0200-01` | U+I | yes |
| `AC-NFR0100-01` | U | yes |

## 4. Runner

```
python -m pytest tests/integration/synthetic_001_demo tests/e2e/synthetic_001_demo -q
```
