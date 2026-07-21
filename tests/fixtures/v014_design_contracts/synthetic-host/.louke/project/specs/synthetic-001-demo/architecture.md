# Architecture: synthetic-001-demo

## 1. Overview

The synthetic host project uses a minimal architecture with 3 modules
to demonstrate Louke's design-contract validation in a host project
context.

## 2. Module Table

| ID | Module | Responsibility |
|----|--------|---------------|
| `ARC-DESIGN` | DESIGN | Design entry and artifact generation |
| `ARC-REGISTRY` | REGISTRY | Schema and contract registry |
| `ARC-STORE` | STORE | Persistent artifact storage |

## 3. Dependency Flow

```
FACTS → DESIGN → REGISTRY → STORE
```

- `DESIGN` reads host project facts and generates design artifacts
- `REGISTRY` manages schema and contract registration
- `STORE` persists all artifacts to disk

## 4. Security Boundaries

All artifacts are stored in `.louke/project/specs/` with read-only
permissions for CI. No secrets are embedded in design artifacts.
