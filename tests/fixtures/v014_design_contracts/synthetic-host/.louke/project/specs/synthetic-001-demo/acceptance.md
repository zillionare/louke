# Acceptance Criteria: synthetic-001-demo

**Spec ID**: synthetic-001-demo
**Status**: candidate
**Base commit**: abc1234

## 1. Functional Requirements

### `AC-FR0100-01`: Feature implementation

The host project SHALL implement a demo feature that returns a greeting
message. The feature MUST be accessible via `host_app.greet()` and return
a non-empty string.

### `AC-FR0200-01`: API contract

The host project SHALL expose a stable API contract for the greeting
feature. The contract MUST define input (none), output (string), and
error (none) semantics.

## 2. Non-Functional Requirements

### `AC-NFR0100-01`: Performance

The greeting feature SHALL complete in under 10ms on a standard
development machine.
