#!/usr/bin/env python3
"""specforge board/models — IDE agent board generation and model alias resolution.

Stdlib-only helper called by bin/specforge.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SKIP_AGENT_FILES = {"README.md", "ROSTER.md"}
AGENT_ORDER_SKIP = {"README", "ROSTER"}
DEFAULT_USER_CONFIG = Path.home() / ".specforge" / "models.json"
PROJECT_CONFIG = Path(".specforge/models.json")


@dataclass
class AgentPrompt:
    source: Path
    name: str
    description: str
    mode: str
    models: list[str]
    body: str
    frontmatter: dict[str, Any]


class SpecforgeError(RuntimeError):
    pass


def note(msg: str) -> None:
    print(f"specforge: {msg}", file=sys.stderr)


def normalize_model_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def split_model_tail(full_model: str) -> str:
    return full_model.rsplit("/", 1)[-1]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"$schema": "specforge://models-config", "version": 1, "aliases": {}, "assignments": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SpecforgeError(f"invalid JSON in {path}: {exc}") from exc
    data.setdefault("$schema", "specforge://models-config")
    data.setdefault("version", 1)
    data.setdefault("aliases", {})
    data.setdefault("assignments", {})
    return data


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def user_config_path() -> Path:
    return Path(os.environ.get("SPECFORGE_MODELS_CONFIG", str(DEFAULT_USER_CONFIG))).expanduser()


def project_config_path() -> Path:
    return Path(os.environ.get("SPECFORGE_PROJECT_MODELS_CONFIG", str(PROJECT_CONFIG))).expanduser()


def parse_frontmatter(text: str, source: Path) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise SpecforgeError(f"{source} missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise SpecforgeError(f"{source} has unterminated YAML frontmatter")
    raw = text[4:end]
    body = text[end + len("\n---\n") :]
    data: dict[str, Any] = {}
    current_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and current_key:
            data.setdefault(current_key, []).append(line[4:].strip())
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value == "":
                data[key] = []
                current_key = key
            else:
                data[key] = value.strip('"\'')
                current_key = key
    return data, body


def dump_frontmatter(data: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def detect_agent_dir() -> Path:
    candidates = [Path(".specforge/agents"), Path("agents")]
    for candidate in candidates:
        if candidate.is_dir() and any(p.suffix == ".md" for p in candidate.iterdir()):
            return candidate
    raise SpecforgeError("current directory is not a specforge project (no .specforge/agents/ or agents/)")


def load_agents(agent_dir: Path | None = None) -> list[AgentPrompt]:
    agent_dir = agent_dir or detect_agent_dir()
    agents: list[AgentPrompt] = []
    for source in sorted(agent_dir.glob("*.md")):
        if source.name in SKIP_AGENT_FILES:
            continue
        text = source.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text, source)
        name = str(fm.get("name") or source.stem).strip()
        if name in AGENT_ORDER_SKIP:
            continue
        description = str(fm.get("description") or "specforge agent").strip()
        mode = str(fm.get("mode") or "all").strip()
        models = fm.get("models")
        if not isinstance(models, list) or not models:
            raise SpecforgeError(f"{source} must define non-empty models: list in frontmatter")
        agents.append(AgentPrompt(source, name, description, mode, [str(x).strip() for x in models], body, fm))
    return agents


def collect_model_aliases(agents: list[AgentPrompt]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for agent in agents:
        assignments = effective_assignment(agent.name, agent.models)
        for model in assignments:
            if model not in seen:
                seen.add(model)
                values.append(model)
    return values


def tier_for_agent(name: str) -> str | None:
    n = name.lower()
    tiers = {
        "S": {"maestro", "sage", "lex"},
        "A": {"probe", "judge", "archer", "cynic", "herald", "arbiter", "warden", "hunter", "shield", "prism", "keeper"},
        "B": {"scout", "forge"},
        "C": {"librarian", "guide"},
    }
    for tier, names in tiers.items():
        if n in names:
            return tier
    return None


def merged_assignments() -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    user = load_json(user_config_path()).get("assignments", {})
    project = load_json(project_config_path()).get("assignments", {})
    for key, value in user.items():
        if isinstance(value, list):
            merged[key.lower()] = [str(x) for x in value]
    for key, value in project.items():
        if isinstance(value, list):
            merged[key.lower()] = [str(x) for x in value]
    return merged


def effective_assignment(agent_name: str, default_models: list[str]) -> list[str]:
    assignments = merged_assignments()
    agent_key = agent_name.lower()
    if agent_key in assignments:
        return assignments[agent_key]
    tier = tier_for_agent(agent_name)
    if tier and f"tier:{tier.lower()}" in assignments:
        return assignments[f"tier:{tier.lower()}"]
    if tier and f"tier:{tier}" in assignments:
        return assignments[f"tier:{tier}"]
    return default_models


def list_opencode_models() -> list[str]:
    env_models = os.environ.get("SPECFORGE_OPENCODE_MODELS")
    if env_models:
        return [line.strip() for line in env_models.splitlines() if line.strip()]
    env_file = os.environ.get("SPECFORGE_OPENCODE_MODELS_FILE")
    if env_file:
        return [line.strip() for line in Path(env_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    try:
        out = subprocess.check_output(["opencode", "models"], stderr=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise SpecforgeError("opencode models failed; install/configure opencode or bind models manually") from exc
    return [line.strip() for line in out.decode("utf-8", errors="replace").splitlines() if line.strip()]


def merged_aliases() -> dict[str, str]:
    merged: dict[str, str] = {}
    for cfg in (load_json(user_config_path()), load_json(project_config_path())):
        aliases = cfg.get("aliases", {})
        if isinstance(aliases, dict):
            for key, value in aliases.items():
                merged[str(key)] = str(value)
    return merged


def resolve_model(alias: str, opencode_models: list[str] | None = None) -> str:
    explicit = merged_aliases()
    if alias in explicit:
        return explicit[alias]
    models = opencode_models if opencode_models is not None else list_opencode_models()
    want = normalize_model_name(alias)
    strong = [m for m in models if normalize_model_name(split_model_tail(m)) == want]
    if strong:
        return choose_model(strong)
    weak = [m for m in models if want in normalize_model_name(split_model_tail(m)) or normalize_model_name(split_model_tail(m)) in want]
    if len(weak) == 1 and sys.stdin.isatty():
        answer = input(f"Use weak match {alias} -> {weak[0]}? [Y/n] ").strip().lower()
        if answer in ("", "y", "yes"):
            return weak[0]
    raise SpecforgeError(f"unknown model alias '{alias}'; run 'specforge models bind {alias} <opencode-full-name>'")


def choose_model(candidates: list[str]) -> str:
    user_provider = sorted([m for m in candidates if not m.startswith("opencode/")])
    if user_provider:
        return user_provider[0]
    return sorted(candidates)[0]


def update_gitignore(entry: str, dry_run: bool = False) -> None:
    if os.environ.get("SPECFORGE_BOARD_NO_GITIGNORE") == "1":
        return
    p = Path(".gitignore")
    if p.exists():
        lines = p.read_text(encoding="utf-8").splitlines()
    else:
        lines = []
    if entry in lines:
        return
    if dry_run:
        print(f"[+] .gitignore add {entry}")
        return
    with p.open("a", encoding="utf-8") as f:
        if lines and lines[-1] != "":
            f.write("\n")
        f.write(entry + "\n")


def cmd_board_opencode(args: argparse.Namespace) -> int:
    agents = load_agents()
    out_dir = Path(".opencode/agents")
    opencode_models = list_opencode_models()
    if args.dry_run:
        print(f"[dry-run] mkdir -p {out_dir}")
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
    for agent in agents:
        models = effective_assignment(agent.name, agent.models)
        primary = models[0]
        full_model = resolve_model(primary, opencode_models)
        target = out_dir / f"{agent.name.lower()}.md"
        fm = {
            "description": agent.description,
            "mode": agent.mode or "all",
            "model": full_model,
        }
        content = dump_frontmatter(fm) + "\n" + agent.body.lstrip("\n")
        if args.dry_run:
            print(f"[+] {target} model={full_model}")
        else:
            target.write_text(content, encoding="utf-8")
            print(f"[+] {target} model={full_model}")
    update_gitignore(".opencode/agents/", args.dry_run)
    return 0


def cmd_board_vscode(args: argparse.Namespace) -> int:
    agent_dir = detect_agent_dir()
    out_dir = Path(".github/agents")
    if args.dry_run:
        print(f"[dry-run] mkdir -p {out_dir}")
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
    for source in sorted(agent_dir.glob("*.md")):
        if source.name in SKIP_AGENT_FILES:
            continue
        target = out_dir / f"{source.stem}.agent.md"
        rel = os.path.relpath(source, out_dir)
        if args.dry_run:
            print(f"[+] {target} -> {rel}")
        else:
            if target.exists() or target.is_symlink():
                target.unlink()
            target.symlink_to(rel)
            print(f"[+] {target} -> {rel}")
    update_gitignore(".github/agents/", args.dry_run)
    return 0


def cmd_board_status(_args: argparse.Namespace) -> int:
    vscode_dir = Path(".github/agents")
    opencode_dir = Path(".opencode/agents")
    v_count = len(list(vscode_dir.glob("*.agent.md"))) if vscode_dir.is_dir() else 0
    o_count = len(list(opencode_dir.glob("*.md"))) if opencode_dir.is_dir() else 0
    print(f"vscode    {'✓' if v_count else '-'}  ({vscode_dir}/ — {v_count} agents)")
    print(f"opencode  {'✓' if o_count else '-'}  ({opencode_dir}/ — {o_count} agents)")
    return 0


def cmd_board(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="specforge board")
    p.add_argument("ide", choices=["opencode", "vscode", "status"])
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    if args.ide == "opencode":
        return cmd_board_opencode(args)
    if args.ide == "vscode":
        return cmd_board_vscode(args)
    return cmd_board_status(args)


def cmd_models_list(_args: argparse.Namespace) -> int:
    agents = load_agents()
    aliases = collect_model_aliases(agents)
    try:
        op_models = list_opencode_models()
    except SpecforgeError:
        op_models = []
    for alias in aliases:
        try:
            resolved = resolve_model(alias, op_models) if op_models else merged_aliases().get(alias, "-")
        except SpecforgeError:
            resolved = "-"
        print(f"{alias}\t{resolved}")
    return 0


def cmd_models_doctor(args: argparse.Namespace) -> int:
    agents = load_agents()
    aliases = collect_model_aliases(agents)
    op_models = list_opencode_models()
    cfg_path = user_config_path()
    cfg = load_json(cfg_path)
    ok = True
    for alias in aliases:
        try:
            resolved = resolve_model(alias, op_models)
            print(f"✓ {alias} -> {resolved}")
            if args.fix_auto:
                cfg.setdefault("aliases", {})[alias] = resolved
        except SpecforgeError as exc:
            print(f"✗ {alias}: {exc}")
            ok = False
    if args.fix_auto:
        save_json(cfg_path, cfg)
        print(f"wrote {cfg_path}")
    return 0 if ok else 1


def cmd_models_bind(args: argparse.Namespace) -> int:
    path = project_config_path() if args.project else user_config_path()
    cfg = load_json(path)
    cfg.setdefault("aliases", {})[args.abstract_name] = args.full_name
    save_json(path, cfg)
    print(f"bound {args.abstract_name} -> {args.full_name} in {path}")
    return 0


def cmd_models_unbind(args: argparse.Namespace) -> int:
    path = project_config_path() if args.project else user_config_path()
    cfg = load_json(path)
    cfg.setdefault("aliases", {}).pop(args.abstract_name, None)
    save_json(path, cfg)
    print(f"unbound {args.abstract_name} in {path}")
    return 0


def parse_model_chain(value: str) -> list[str]:
    models = [v.strip() for v in value.split(",") if v.strip()]
    if not models:
        raise SpecforgeError("model chain must not be empty")
    return models


def cmd_models_assign(args: argparse.Namespace) -> int:
    path = project_config_path() if args.project else user_config_path()
    cfg = load_json(path)
    chain = parse_model_chain(args.models)
    for target in [x.strip().lower() for x in args.target.split(",") if x.strip()]:
        cfg.setdefault("assignments", {})[target] = chain
        print(f"assigned {target} -> {','.join(chain)} in {path}")
    save_json(path, cfg)
    return 0


def cmd_models_assign_unset(args: argparse.Namespace) -> int:
    path = project_config_path() if args.project else user_config_path()
    cfg = load_json(path)
    for target in [x.strip().lower() for x in args.target.split(",") if x.strip()]:
        cfg.setdefault("assignments", {}).pop(target, None)
        print(f"unset assignment {target} in {path}")
    save_json(path, cfg)
    return 0


def cmd_models_assign_list(_args: argparse.Namespace) -> int:
    assignments = merged_assignments()
    if not assignments:
        print("(no assignments)")
        return 0
    for key, value in sorted(assignments.items()):
        print(f"{key}\t{','.join(value)}")
    return 0


def cmd_models(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="specforge models")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    doctor = sub.add_parser("doctor")
    doctor.add_argument("--fix-auto", action="store_true")
    bind = sub.add_parser("bind")
    bind.add_argument("abstract_name")
    bind.add_argument("full_name")
    bind.add_argument("--project", action="store_true")
    unbind = sub.add_parser("unbind")
    unbind.add_argument("abstract_name")
    unbind.add_argument("--project", action="store_true")
    assign = sub.add_parser("assign")
    assign_sub = assign.add_subparsers(dest="assign_cmd", required=True)
    assign_list = assign_sub.add_parser("list")
    assign_set = assign_sub.add_parser("set")
    assign_set.add_argument("target")
    assign_set.add_argument("models")
    assign_set.add_argument("--project", action="store_true")
    assign_unset = assign_sub.add_parser("unset")
    assign_unset.add_argument("target")
    assign_unset.add_argument("--project", action="store_true")
    args = p.parse_args(argv)
    if args.cmd == "list":
        return cmd_models_list(args)
    if args.cmd == "doctor":
        return cmd_models_doctor(args)
    if args.cmd == "bind":
        return cmd_models_bind(args)
    if args.cmd == "unbind":
        return cmd_models_unbind(args)
    if args.cmd == "assign":
        if args.assign_cmd == "list":
            return cmd_models_assign_list(args)
        if args.assign_cmd == "set":
            return cmd_models_assign(args)
        if args.assign_cmd == "unset":
            return cmd_models_assign_unset(args)
    raise SpecforgeError("unknown models command")


def main(argv: list[str]) -> int:
    if not argv:
        raise SpecforgeError("usage: specforge_board.py <board|models> ...")
    if argv[0] == "board":
        return cmd_board(argv[1:])
    if argv[0] == "models":
        return cmd_models(argv[1:])
    raise SpecforgeError(f"unknown command: {argv[0]}")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except SpecforgeError as exc:
        print(f"specforge: {exc}", file=sys.stderr)
        raise SystemExit(1)
