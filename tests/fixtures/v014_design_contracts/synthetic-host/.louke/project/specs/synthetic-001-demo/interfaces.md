# Interfaces: synthetic-001-demo

## 1. Interface Summary

| ID | Name | Modules |
|----|------|---------|
| `IF-DES-01` | Design entry | DESIGN, STORE |
| `IF-DES-02` | Validation result | VALIDATOR, REGISTRY, STORE |
| `IF-REG-01` | Registry discover | REGISTRY, STORE |

## 2. Interface Details

### IF-DES-01 — Design entry

| 字段 | 合同 |
|---|---|
| `modules` | `DESIGN, STORE` |
| invocation | `python -m louke._tools.design_coordinator start --spec synthetic-001-demo` |
| output | `{spec_id, stage:"m-design", status:"entered"}` |
| architecture | `ARC-DESIGN`, `ARC-STORE` |

### IF-DES-02 — Validation result

| 字段 | 合同 |
|---|---|
| `modules` | `VALIDATOR, REGISTRY, STORE` |
| invocation | `python -m louke._tools.design_contract validate --manifest PATH --format json --output PATH` |
| output | `{status:"pass|fail", revision_id, checks:[{check_id,status,fr_ids,ac_ids,interface_ids,architecture_anchors,contract_refs,retryable,remediation}], evidence_digest}` |
| stable check IDs | `DESIGN.TRACE.CLOSURE`, `DESIGN.INTERFACE.RESOLUTION`, `DESIGN.ARCH.CARRIER`, `DESIGN.CONTRACT.PARITY`, `DESIGN.SCHEMA.ACTIVE` |
| exit | 全部 pass 为 0；任一 fail 为非 0 |
| architecture | `ARC-VALIDATE`, `ARC-STORE` |

### IF-REG-01 — Registry discover

| 字段 | 合同 |
|---|---|
| `modules` | `REGISTRY, STORE` |
| invocation | `python -m louke._tools.contract_registry discover --format json` |
| output | `{registry_version, registry_digest, schemas:[{identity,kind,version,digest,status}]}` |
| architecture | `ARC-REGISTRY`, `ARC-STORE` |
