# Shield Python Host Fixture (v0.14-003)

Minimal Python host project for v0.14-003 integration tests.

Used by:
- AC-NFR0500-01 (host project compatibility)
- AC-FR1600-01 (artifact version verification with wheel+sdist)

## Facts

- Stack: Python (pyproject.toml + setuptools)
- Test framework: pytest
- Artifacts: wheel + sdist
- Pre-commit: .pre-commit-config.yaml (preserve-existing)
- CI: .github/workflows/louke-ci.yml
