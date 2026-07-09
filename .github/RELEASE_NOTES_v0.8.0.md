# louke v0.8.0

Major release: introduces the **web collaboration server** (`lk serve`), a
browser-based workbench for browsing and editing wiki pages, spec/acceptance
documents, and model bindings - with real-time preview, inline discussion
support, and multi-user conflict awareness.

## Highlights

### Web collaboration server (`lk serve`)

- **`lk serve`** starts a local Starlette/Uvicorn server that renders the
  current louke project as an interactive web workbench.
- **Sidebar navigation**: models, design docs (spec/acceptance/test-plan),
  and wiki - all driven from the current project's `.louke/` directory.
- **Model bindings page**: drag-and-drop role/agent → model binding; saves
  directly to `.louke/models.json` and takes effect for newly started agents.
- **Document editor**: split-pane source + live Markdown preview, with
  inline-discussion rendering, discussion focus mode, and reply actions.
- **Wiki editor**: create nested pages (`dir/page`), auto-grouped by
  first-level directory in the sidebar.
- **Authentication**: register/login flow with session cookies; project-level
  user store.

### Internationalization (i18n)

- Detects the browser/OS locale via `Accept-Language` and serves the UI in
  that language when supported (**zh** / **en**).
- **English fallback**: any unsupported locale (or missing header) falls back
  to English - not Chinese.
- 46 translation keys covering all UI surfaces; `<html lang>` tracks the
  detected language.

### Skill installation fix

- `lk board opencode` now installs skills as **directories**
  (`.opencode/skill/<name>/SKILL.md`) instead of flat `<name>.md` files,
  matching OpenCode's official skill layout. Multi-file skills (templates,
  references, scripts) are now preserved.
- SKILL.md `name:` fields reverted to bare names; the `lk-` prefix is added
  by `prefixed_skill_name()` at install time.

### Other changes

- **Issue #94**: `lk agent lex verify-issue` now accepts `--branch` (was
  always reading `main`).
- **Package cleanup**: removed `louke/.github/workflows/` (louke's own CI
  files that never belonged in the pip package; `release.yml` would have run
  `twine upload` against a downstream project's empty token).
- **Login page** visual refinement: taller buttons, better spacing, focus
  rings, layered shadows.
- **Model resolution**: `lk board opencode` now prefers user-authenticated
  providers over OpenCode Zen, and uses Levenshtein similarity for fuzzy
  model-name matching.

## Verification

- `bats tests/test_web_server.py` + `tests/test_fix_094.bats` +
  `tests/test_board_opencode_skills.bats` + `tests/test_issue_form.bats` -
  all pass.
- `pytest tests/test_web_server.py` - 7/7 pass (i18n fallback, auth flow,
  doc roundtrip, wiki, bindings, discussion).

## Migration

No breaking changes for CLI users. The web server is opt-in (`lk serve`).
Skill layout change is transparent - re-run `lk board opencode` to regenerate
`.opencode/skill/` in the new directory format.
