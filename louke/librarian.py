"""Librarian commands - wiki health maintenance.

Librarian responsibilities: raw -> wiki distillation, index maintenance,
lint health checks.
"""

import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path


CACHE_PATH = Path.cwd() / ".louke" / "wiki" / ".cache.toml"


def register(subparsers):
    parser = subparsers.add_parser(
        "librarian", help="wiki health maintenance (Librarian)"
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    p = sub.add_parser(
        "distill", help="raw -> wiki distillation (by LLM; lk only prepares)"
    )
    p.add_argument(
        "--source", default=".louke/raw/", help="raw path (default .louke/raw/)"
    )
    p.add_argument(
        "--target",
        default=".louke/wiki/pages/",
        help="wiki path (default .louke/wiki/pages/)",
    )

    p = sub.add_parser("lint", help="wiki health check (broken links, orphaned pages)")
    p.add_argument("--wiki", default=".louke/wiki/")

    p = sub.add_parser("rebuild-index", help="rebuild wiki navigation index")
    p.add_argument("--wiki", default=".louke/wiki/")

    p = sub.add_parser(
        "compact", help="cron entry: prepare distillation bundle + update last_distill"
    )
    p.add_argument(
        "--dry-run", action="store_true", help="only print plan, do not write files"
    )
    p.add_argument(
        "--threshold-tokens",
        type=int,
        default=50_000,
        help="M0/M1 switch threshold (default 50K)",
    )
    p.add_argument(
        "--m2-threshold",
        type=int,
        default=200_000,
        help="M1/M2 switch threshold (default 200K)",
    )

    p = sub.add_parser(
        "rewrite", help="LLM full rewrite of pages/, via opencode run --agent librarian"
    )
    p.add_argument(
        "--model",
        default="",
        help="specify model ID (highest priority, passed to opencode run --model)",
    )
    p.add_argument(
        "--model-from-config",
        action="store_true",
        help="use lk models bind (second priority)",
    )
    p.add_argument(
        "--full",
        action="store_true",
        help="full rewrite (ignore default incremental, FR-0140.5)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="only print the opencode command to be invoked",
    )


def run(args):
    handlers = {
        "distill": cmd_distill,
        "lint": cmd_lint,
        "rebuild-index": cmd_rebuild_index,
        "compact": cmd_compact,
        "rewrite": cmd_rewrite,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


# ---- .cache.toml (last_distill + SHA256 incremental index) ----


def _read_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return {}
    try:
        with open(CACHE_PATH, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _write_cache(data: dict) -> None:
    try:
        import tomli_w
    except ImportError:
        # writer side has no tomli_w: fall back to hand-crafted construction (avoids new dependency)
        lines = []
        for k, v in data.items():
            if isinstance(v, str):
                lines.append(f'{k} = "{v}"')
            elif isinstance(v, dict):
                lines.append(f"[{k}]")
                for sk, sv in v.items():
                    if isinstance(sv, str):
                        lines.append(f'{sk} = "{sv}"')
                    else:
                        lines.append(f"{sk} = {sv}")
            else:
                lines.append(f"{k} = {v}")
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text("\n".join(lines) + "\n")
        return
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "wb") as f:
        tomli_w.dump(data, f)


def cmd_distill(args):
    """Distill raw -> wiki - lk wrapper around LLM distillation.

    LLM distillation is the LLM's job; lk only:
    1. scans raw/ for sessions with status=resolved
    2. generates a to-be-distilled list (for the LLM to read)
    3. after LLM distillation, lk writes to wiki/

    Currently a placeholder: only scans + prints the list.
    """
    cwd = Path.cwd()
    raw_dir = cwd / args.source
    if not raw_dir.exists():
        print(f"raw dir does not exist: {raw_dir}")
        return 1

    print("=== Distill (scan) ===")
    print(f"Source: {raw_dir}")

    resolved = []
    for fp in sorted(raw_dir.rglob("*.md")):
        try:
            content = fp.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue
        if re.search(r"^status:\s*resolved", content, re.MULTILINE):
            resolved.append(fp)

    print(f"entries to distill (status=resolved): {len(resolved)}")
    for fp in resolved:
        print(f"  - {fp.relative_to(cwd)}")

    print(
        "\nnext step: LLM reads these entries, distills, then writes via lk agent librarian write <wiki-page>"
    )
    return 0


def cmd_lint(args):
    """Wiki lint - find broken links and orphaned pages."""
    cwd = Path.cwd()
    wiki_dir = cwd / args.wiki
    if not wiki_dir.exists():
        print(f"wiki dir does not exist: {wiki_dir}")
        return 1

    print("=== Wiki Lint ===")
    print(f"Wiki: {wiki_dir}")

    pages = list(wiki_dir.rglob("*.md"))
    print(f"Pages: {len(pages)}")

    # find all [[wikilink]] references
    all_refs = set()
    for p in pages:
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue
        refs = re.findall(r"\[\[([^\]]+)\]\]", content)
        all_refs.update(refs)

    # find all page names (excluding .md)
    page_names = {p.stem for p in pages}

    # broken links
    broken = [r for r in all_refs if r not in page_names]
    print(f"\n[broken links] {len(broken)}")
    for b in broken[:10]:
        print(f"  - [[{b}]]")

    # orphaned pages (no wikilink references at all)
    referenced = set()
    for p in pages:
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue
        for r in re.findall(r"\[\[([^\]]+)\]\]", content):
            referenced.add(r)
    orphaned = page_names - referenced
    print(f"\n[orphaned pages] {len(orphaned)}")
    for o in list(orphaned)[:10]:
        print(f"  - {o}.md")

    if broken or orphaned:
        return 1
    print("\n-> wiki healthy")
    return 0


def cmd_rebuild_index(args):
    """Rebuild wiki navigation index.md."""
    cwd = Path.cwd()
    wiki_dir = cwd / args.wiki
    if not wiki_dir.exists():
        return 1

    pages = sorted(wiki_dir.rglob("*.md"))
    print("=== Rebuild Index ===")
    print(f"Pages: {len(pages)}")

    lines = ["# Wiki Index", "", f"{len(pages)} pages total", ""]
    for p in pages:
        rel = p.relative_to(wiki_dir)
        lines.append(f"- [[{p.stem}]] (`{rel}`)")

    index_path = wiki_dir / "index.md"
    index_path.write_text("\n".join(lines) + "\n")
    print(f"✓ Index rebuilt: {index_path}")
    return 0


def _scan_resolved_raw(since: str, until: str) -> tuple[list, list]:
    """Scan raw/ for entries with status=resolved and date in [since, until] range.

    Returns (matched, skipped_no_date).
    - matched: entries satisfying the condition (file_path, file_date, content)
    - skipped_no_date: entries skipped because they have no date field (file_path,)
    """
    cwd = Path.cwd()
    raw_dir = cwd / ".louke/raw/"
    if not raw_dir.exists():
        return [], []

    matched = []
    skipped = []
    for fp in sorted(raw_dir.rglob("*.md")):
        try:
            content = fp.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue

        if not re.search(r"^status:\s*resolved", content, re.MULTILINE):
            continue

        date_m = re.search(r"^date:\s*(\d{4}-\d{2}-\d{2})", content, re.MULTILINE)
        file_date = date_m.group(1) if date_m else ""
        if not file_date:
            # FR-0080 P1-8: no date field -> skip + warning
            skipped.append(fp)
            continue
        if since and file_date < since:
            continue
        if until and file_date > until:
            continue
        matched.append((fp, file_date, content))
    return matched, skipped


def _estimate_tokens(items: list) -> int:
    """Roughly estimate token count (~4 chars / token)."""
    return sum(len(c) for _, _, c in items) // 4


def _cleanup_old_bundles(wiki_dir: Path) -> int:
    """Delete all .compact-bundle*.md under wiki_dir (FR-0140.2 P0-3 / P1-4).

    Bundles are intermediate products of compact and are not persisted.
    Cleanup happens at the start of every compact run.
    Returns the number of deleted files.
    """
    count = 0
    for f in wiki_dir.glob(".compact-bundle*.md"):
        try:
            f.unlink()
            count += 1
        except OSError:
            pass
    return count


def _write_bundle(
    bundle_path: Path, items: list, mode: str, existing_pages: str, dry_run: bool
) -> None:
    """Write a single bundle file."""
    if dry_run:
        return
    total_chars = sum(len(c) for _, _, c in items)
    lines = [
        "# Librarian Compact Bundle",
        f"> Generated: {date.today().isoformat()}",
        f"> Mode: {mode}",
        f"> Raw entries: {len(items)}",
        f"> Total chars: {total_chars}",
        "",
        "## Raw Sessions (append-only history)",
        "",
    ]
    for fp, file_date, content in items:
        lines.append(f"### {fp.name} ({file_date})")
        lines.append("")
        lines.append(content)
        lines.append("")
    lines.extend(
        [
            "## Current Pages (to be REWRITTEN, not patched)",
            "",
            existing_pages or "(empty)",
            "",
            "## Instructions",
            "",
            "Rewrite pages/. Keep decisions that still hold; delete/update outdated ones; add newly emerged topics.",
            "Every wiki decision must be traceable to evidence in raw (quote dialogue syntax, see v0.4-004).",
            "",
        ]
    )
    bundle_path.write_text("\n".join(lines))


def cmd_compact(args):
    """cron entry: prepare distillation bundle + update last_distill.

    FR-0080: removed cmd_from_raw + cmd_daily; merged into cmd_compact.
    FR-0140: auto-select M0/M1/M2 mode based on token volume.
    FR-0140.2 P0-3 / P1-4: clean old bundles just before write (NOT on entry).
    FR-0080 P1-8: skip raw entries without date field + warning.
    """
    cwd = Path.cwd()
    wiki_dir = cwd / ".louke" / "wiki"
    wiki_pages_dir = wiki_dir / "pages"
    raw_dir = cwd / ".louke" / "raw"

    if not raw_dir.exists():
        print("raw dir does not exist: .louke/raw/", file=sys.stderr)
        return 1
    wiki_pages_dir.mkdir(parents=True, exist_ok=True)

    # 2. compute window
    cache = _read_cache()
    last = cache.get("last_distill", "")
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    if not last:
        last = "1970-01-01"
        print(
            f"[compact] cache.last_distill not set, processing all historical raw from {last}"
        )
    else:
        print(f"[compact] last distill: {last}")
    print(f"[compact] distill window: [{last}, {yesterday}]")

    # 3. scan raw
    matched, skipped_no_date = _scan_resolved_raw(since=last, until=yesterday)
    if skipped_no_date:
        print(
            f"[compact] WARN: {len(skipped_no_date)} raw entries have no date field, skipped:"
        )
        for fp in skipped_no_date[:10]:
            print(f"  - {fp.relative_to(cwd)}")
        if len(skipped_no_date) > 10:
            print(f"  ... (+{len(skipped_no_date) - 10} more)")

    if not matched:
        print(
            "[compact] no new raw to distill, zero output (existing bundles preserved)"
        )
        # update last_distill even on zero output to stay idempotent (dry-run does not write).
        # IMPORTANT: do NOT delete bundles here — if we already wrote them
        # on a previous run and there's no new raw, the existing bundles
        # remain valid for `lk agent librarian rewrite`. Deleting them was
        # a footgun (FR-0140.2 footgun-fixed): a no-op compact would wipe
        # the very artifact that downstream rewrite depends on. Cleanup is
        # now performed just before writing fresh bundles below.
        if not args.dry_run:
            cache = _read_cache()
            cache["last_distill"] = yesterday
            _write_cache(cache)
        return 0

    # 4. read existing pages
    existing_pages = ""
    if wiki_pages_dir.exists():
        for fp in sorted(wiki_pages_dir.glob("*.md")):
            try:
                existing_pages += f"\n### {fp.stem}\n\n{fp.read_text(encoding='utf-8', errors='replace')}\n"
            except OSError:
                pass

    # 5. estimate tokens + select mode
    total_tokens = _estimate_tokens(matched)
    m1_thresh = args.threshold_tokens
    m2_thresh = args.m2_threshold
    print(
        f"[compact] token estimate: {total_tokens} (M0<={m1_thresh} < M1<={m2_thresh} < M2)"
    )

    if total_tokens <= m1_thresh:
        mode = "M0_incremental"
    elif total_tokens <= m2_thresh:
        mode = "M1_full"
        print(
            "[compact] WARN: recommend --model gemini-1.5-pro (1M context) or claude-sonnet-4 (200K)"
        )
    else:
        mode = "M2_map_reduce"
        print("[compact] M2: chunk by month, will produce multiple bundles + merged")

    # 6. clean old bundles (footgun-fix: only when we are about to write
    # fresh ones). Bundles are intermediate products of compact and are
    # not persisted beyond the current cached window; deleting them now
    # ensures no stale `.compact-bundle-merged.md` from a previous M2 run
    # leaks into the next M0/M1 run.
    if not args.dry_run:
        cleaned = _cleanup_old_bundles(wiki_dir)
        if cleaned:
            print(f"[compact] cleaned {cleaned} old bundle(s)")

    # 7. write bundle(s)
    if mode == "M2_map_reduce":
        from collections import defaultdict

        grouped = defaultdict(list)
        for fp, file_date, content in matched:
            month = file_date[:7]  # YYYY-MM
            grouped[month].append((fp, file_date, content))
        for month, items in sorted(grouped.items()):
            bundle = wiki_dir / f".compact-bundle-{month}.md"
            _write_bundle(bundle, items, f"M2:{mode}", existing_pages, args.dry_run)
            if not args.dry_run:
                print(
                    f"  + {bundle.name} ({len(items)} entries, ~{_estimate_tokens(items)} tokens)"
                )
        merged = wiki_dir / ".compact-bundle-merged.md"
        merge_lines = [
            "# Librarian Compact Bundle (M2 merged)",
            f"> Generated: {date.today().isoformat()}",
            f"> Bundles: {sorted(grouped.keys())}",
            "",
            "## Sub-bundles",
            "",
        ]
        for month in sorted(grouped.keys()):
            merge_lines.append(f"- .compact-bundle-{month}.md")
        _write_bundle(merged, matched, "M2:merge", existing_pages, args.dry_run)
        if not args.dry_run:
            print(f"  + {merged.name} (references {len(grouped)} sub-bundles)")
    else:
        bundle = wiki_dir / ".compact-bundle.md"
        _write_bundle(bundle, matched, mode, existing_pages, args.dry_run)
        if not args.dry_run:
            print(f"  + {bundle.name} ({len(matched)} entries, ~{total_tokens} tokens)")

    # 7. update last_distill (idempotent: advances after one run, regardless of new entries)
    if not args.dry_run:
        cache = _read_cache()
        cache["last_distill"] = yesterday
        _write_cache(cache)
        print(f"[compact] -> .cache.last_distill: {last or '(unset)'} -> {yesterday}")

    return 0


def cmd_rewrite(args):
    """LLM full rewrite of pages/, via opencode run.

    FR-0130: shell-out to OpenCode CLI, does not call LLM SDK directly.
    FR-0140.4 P1-7: model priority chain --model > --model-from-config > frontmatter.

    Note on `--agent librarian`: opencode refuses to start a subagent as
    the primary target of `opencode run` (subagents can only be dispatched
    FROM a primary, not invoked as one). Instead, we run the default
    primary agent (Maestro) with an explicit "you are playing the
    librarian role" prompt. Maestro has the same tools (bash, edit, read)
    that the librarian subagent needs, and the bundled prompt above
    spells out the exact workflow so the answer is deterministic.
    """
    cwd = Path.cwd()
    wiki_dir = cwd / ".louke" / "wiki"
    bundle_main = wiki_dir / ".compact-bundle.md"
    bundle_merged = wiki_dir / ".compact-bundle-merged.md"

    if not bundle_main.exists() and not bundle_merged.exists():
        print(
            "error: .compact-bundle.md does not exist, please run lk agent librarian compact first",
            file=sys.stderr,
        )
        return 1

    # select bundle: M2 uses merged, others use main
    if bundle_merged.exists() and not args.full:
        bundle = bundle_merged
        mode_hint = "M2_map_reduce"
    else:
        bundle = bundle_main
        mode_hint = "M0/M1_full"

    # Model priority chain (FR-0140.4):
    #   1. --model flag (explicit, always wins)
    #   2. --model-from-config: read current lk models bind
    #   3. librarian frontmatter intelligence quotation (resolved through role bindings)
    #   4. opencode default model from .opencode/opencode.json
    # Without one of these, opencode falls back to a placeholder model
    # (e.g. "volcengine-plan/ark-code-latest") that may not exist on the
    # user's currently-active provider, which surfaces as
    # `ProviderModelNotFoundError -> UnknownError "err_XXXXXX"`.
    model_flag = []
    if args.model:
        model_flag = ["--model", args.model]
    elif args.model_from_config:
        # get current model via louke models bind (FR-0140.4 second priority)
        try:
            bound = subprocess.run(
                ["lk", "models", "bind", "--get-current"],
                capture_output=True,
                text=True,
                check=False,
            )
            if bound.returncode == 0 and bound.stdout.strip():
                model_flag = ["--model", bound.stdout.strip()]
        except FileNotFoundError:
            pass
    if not model_flag:
        # Fall back to Librarian's own abstract binding. This is what
        # `opencode run` honours when --agent-style dispatch happens; for the
        # direct-primary invocation path we mirror the resolved value.
        from .board import agent_source, parse_frontmatter
        from .models import frontmatter_binding, resolve_model

        src = agent_source(Path.cwd())
        libr_path = src / "Librarian.md"
        if libr_path.exists():
            fm, _ = parse_frontmatter(libr_path.read_text(encoding="utf-8"))
            binding = frontmatter_binding(fm)
            if binding:
                model_flag = ["--model", resolve_model(binding)]
        # Last-ditch fallback used to be "do not pass --model" (let
        # opencode use its global default). That default may be a model
        # that is not on the user's active provider, so we always pass
        # --model when we have any candidate. If nothing above yields one,
        # raise an explicit error rather than letting opencode crash with
        # an opaque UnknownError ref code (e.g. err_974c503f).
        if not model_flag:
            print(
                "error: no model available. Set one of:\n"
                "  - lk agent librarian rewrite --model provider/model\n"
                "  - lk agent librarian rewrite --model-from-config\n"
                "  - .louke/models.json assignments (lk models bind ...)",
                file=sys.stderr,
            )
            return 2

    if args.dry_run:
        # No --agent librarian (subagent can't be primary target; see docstring).
        cmd_preview = ["opencode", "run"]
        cmd_preview += model_flag
        cmd_preview += ["--", "<prompt>"]
        print(f"[dry-run] {bundle.name} ({mode_hint})")
        print(f"[dry-run] cmd: {' '.join(cmd_preview)}")
        return 0

    prompt = f"""
You are playing the **Librarian** role. Run as a CLI batch: distill and exit.

# Context: this is an llm-wiki (Karpathy-style)

The wiki is **not** a knowledge base of historical records. It is the
**current best understanding** of every topic the project touches. The
shape is "one concise page per topic, always reflecting the latest and
most correct knowledge". Older material is **not preserved** in the
wiki — it lives in `.louke/raw/` for reference. NEVER add a page like
"本页面已废弃" or migrate-by-preserving-as-archive.

Inputs:
1. {bundle} (raw conversations + existing pages; mode: {mode_hint})
2. .louke/wiki/pages/ (current wiki pages)
3. .louke/raw/ (full source transcripts — the original, unedited record)

# Workflow
1. Read the bundle. Group raw conversations into TOPICS (e.g. one topic
   per agent, per decision, per workflow).
2. For each topic, write **one** canonical page under .louke/wiki/pages/
   that captures the **current state of the truth**. The page should:
   - Start with a 1-2 sentence summary of the topic at the top
   - Then 2-4 sections, each focused on one aspect (current behavior,
     constraints, related decisions, references into raw/)
   - Use frontmatter (name + description) so the wiki index links to it
   - Be CONCISE — single canonical truth, not a discussion history
3. DELETE any page in pages/ that is:
   - A historical / event record (e.g. `2026-07-09-*.md`, `*-interview.md`,
     `end-to-end-test.md`, `first-conversation.md`, `librarian-from-raw.md`)
     — these are scaffolding for raw/, not llm-wiki content
   - A one-time setup log that no longer reflects current behavior
   - A "rewrite of X" / "本页面已废弃" stub
   - **Subsumed** by a newer canonical page (merge content into the
     canonical page first, then delete the old)
4. Pages that earn their keep should be REWRITTEN if they are stale,
   bloated, or include history rather than truth.
5. Some existing pages like `decisions/NNN-*.md`, `agents/<name>.md`,
   and workflow pages are legitimately canonical and should be kept /
   refined, not deleted.

# Anti-patterns (do NOT do these)
- Do not add "已废弃" or deprecation banners to existing pages — delete
  them outright if they no longer carry current truth.
- Do not add date prefixes like "2026-07-09-…" to new pages; llm-wiki
  pages are timeless (the raw/ dir carries the date).
- Do not insert "this was rewritten by librarian on …" metadata; it
  bloats the page and adds no value.
- Do not copy raw conversation transcripts into pages/; that is what
  raw/ is for.

# After editing pages/
1. Run `lk agent librarian rebuild-index` (regenerates index.md from the
   current pages/) — this will pick up your new pages automatically.
2. Run `lk agent librarian lint` for health checks. Self-heal broken
   links or missing frontmatter.

Exit 0 when done. Exit 1 only if lint fails and cannot self-heal.
"""
    # Use the default primary agent (Maestro). Pass --model only when the
    # caller explicitly asked for one; otherwise let opencode use the
    # primary's frontmatter intelligence quotation.
    cmd = ["opencode", "run"]
    cmd += model_flag
    cmd += ["--", prompt]
    print(
        f"[rewrite] shell-out: bundle={bundle.name} mode={mode_hint} model={'<default>' if not model_flag else model_flag[1]}"
    )
    rc = subprocess.run(cmd).returncode
    return rc
