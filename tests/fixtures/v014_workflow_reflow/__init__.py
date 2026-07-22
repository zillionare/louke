"""Shield-managed fixtures and stand-ins for the v0.14-001 entry-slice tests.

This package provides the L2 protocol stand-ins and workspace builders shared
by ``tests/integration/v014_workflow_reflow`` and ``tests/e2e/v014_workflow_reflow``.

Per ``test-plan.md`` §6.2, the controllable boundaries are:
  * OpenCode HTTP/SSE (replaced by :class:`L2ScribeStandIn`)
  * GitHub REST/GraphQL (replaced by the ``gh`` stand-in script)
  * Git remote (real bare repo created by :func:`build_isolated_workspace`)

The Runtime core (Driver, SQLite transactions, lease/CAS, review joint
judgement, Git allowlist commit, operation reconcile) is NEVER mocked.
"""
