// Shield Node Host Fixture (v0.14-003)
// Minimal Node host project for v0.14-003 integration tests.
// Used by:
// - AC-NFR0500-01 (host project compatibility - heterogeneous stack)
// - AC-FR1600-01 (artifact version verification with tarball)

const facts = {
  stack_id: 'node',
  language: 'javascript',
  language_version: '>=18',
  build_system: 'npm',
  test_framework: 'jest',
  artifact_kinds: ['tarball'],
  pre_commit_config_path: '.husky/pre-commit',
  ci_workflow_path: '.github/workflows/louke-ci.yml',
};

module.exports = facts;
