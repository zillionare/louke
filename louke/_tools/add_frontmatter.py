#!/usr/bin/env python3
"""
Add YAML frontmatter to agents/*.md so VS Code recognizes them as custom agents.
Idempotent: files that already have frontmatter are skipped.
"""

from pathlib import Path

AGENTS_DIR = Path(__file__).parent.parent / "agents"
DESCRIPTIONS = {
    "Sage": "Story peer review and requirements authoring — independently review Story, then produce Spec and Acceptance contracts",
    "Scribe": "M-STORY author — discover, clarify, and return a review-ready Story with a Go/Park/No-Go recommendation",
    "Lex": "Requirements semantic reviewer — audit Story coverage, Spec/Acceptance assertability, and scope fidelity",
    "Archer": "Test plan + architecture — designs test-plan / architecture / interfaces",
    "Maestro": "Pipeline orchestrator — manages the development workflow",
    "Devon": "Coding implementation — implements features per spec (R-G-R)",
    "Prism": "Independent technical review — test-plan, architecture, code, and e2e quality",
    "Shield": "e2e test authoring — writes e2e tests per test-plan (B-tier)",
    "Judge": "S-tier security audit — deep review of sensitive information leakage risks",
    "Librarian": "Knowledge base — manages wiki, decision records and project memory",
}

for md_file in sorted(AGENTS_DIR.glob("*.md")):
    name = md_file.stem  # e.g. "Sage", "Maestro"
    text = md_file.read_text(encoding="utf-8")

    # Skip if already has frontmatter
    if text.startswith("---\n"):
        print(f"  ⏭️  {md_file.name} (already has frontmatter)")
        continue

    desc = DESCRIPTIONS.get(name, name)

    frontmatter = f"---\nname: {name.lower()}\ndescription: {desc}\n---\n\n"
    md_file.write_text(frontmatter + text, encoding="utf-8")
    print(f"  ✅ {md_file.name} ({desc})")

print(f"\nDone: {len(list(AGENTS_DIR.glob('*.md')))} files processed")
