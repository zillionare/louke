from __future__ import annotations

from pathlib import Path
from typing import Any

from ..board import agent_source, parse_frontmatter
from ..models import frontmatter_binding, resolve_model
from .store import ProjectStore, ValidationError


ROLE_TO_AGENTS = {
    "S": ["Judge", "Sage", "Archer", "Prism"],
    "A": ["Maestro", "Scribe", "Devon", "Shield"],
    "B": ["Lex", "Warden", "Keeper", "Scout", "Librarian"],
}
AGENT_TO_ROLE = {
    agent: role for role, agents in ROLE_TO_AGENTS.items() for agent in agents
}


def get_bindings_payload(store: ProjectStore) -> dict[str, Any]:
    config, version_token, metadata = store.read_bindings()
    aliases = dict(config.get("aliases") or {})
    assignments = _normalize_assignments(config.get("assignments") or {})
    defaults = _agent_default_models(store.root)
    resolved_roles = {}
    for role in ROLE_TO_AGENTS:
        abstract = assignments["roles"].get(role, "")
        resolved_roles[role] = {
            "abstract": abstract,
            "full": _resolve_full_model(abstract, store.root, aliases)
            if abstract
            else "",
        }
    resolved_agents = {}
    for agent, role in AGENT_TO_ROLE.items():
        if agent in assignments["agents"]:
            source = "agent"
            abstract = assignments["agents"][agent]
        elif role in assignments["roles"]:
            source = "role"
            abstract = assignments["roles"][role]
        else:
            source = "default"
            abstract = defaults.get(agent, "")
        resolved_agents[agent] = {
            "source": source,
            "role": role,
            "abstract": abstract,
            "full": _resolve_full_model(abstract, store.root, aliases)
            if abstract
            else "",
        }
    catalog = []
    for abstract in _catalog_models(assignments, defaults, aliases):
        catalog.append(
            {
                "abstract": abstract,
                "full": _resolve_full_model(abstract, store.root, aliases),
            }
        )
    return {
        "version_token": version_token,
        "aliases": aliases,
        "assignments": assignments,
        "resolved": {
            "roles": resolved_roles,
            "agents": resolved_agents,
        },
        "catalog": catalog,
        "roster": ROLE_TO_AGENTS,
        "updated_at": metadata.updated_at,
        "last_modified_by": metadata.last_modified_by,
    }


def save_bindings_payload(
    store: ProjectStore,
    payload: dict[str, Any],
    actor_name: str,
) -> dict[str, Any]:
    aliases = dict(payload.get("aliases") or {})
    assignments = _normalize_assignments(payload.get("assignments") or {})
    _validate_assignments(assignments)
    token, metadata = store.write_bindings(
        {
            "aliases": aliases,
            "assignments": assignments,
        },
        version_token=str(payload.get("version_token") or ""),
        actor_name=actor_name,
    )
    response = get_bindings_payload(store)
    response["version_token"] = token
    response["updated_at"] = metadata.updated_at
    response["last_modified_by"] = metadata.last_modified_by
    return response


def _normalize_assignments(assignments: dict[str, Any]) -> dict[str, dict[str, str]]:
    roles = dict(assignments.get("roles") or {})
    agents = dict(assignments.get("agents") or {})
    return {
        "roles": {
            str(key): str(value) for key, value in roles.items() if str(value).strip()
        },
        "agents": {
            str(key): str(value) for key, value in agents.items() if str(value).strip()
        },
    }


def _validate_assignments(assignments: dict[str, dict[str, str]]) -> None:
    invalid_roles = sorted(set(assignments["roles"]) - set(ROLE_TO_AGENTS))
    invalid_agents = sorted(set(assignments["agents"]) - set(AGENT_TO_ROLE))
    if invalid_roles:
        raise ValidationError(f"invalid role assignments: {', '.join(invalid_roles)}")
    if invalid_agents:
        raise ValidationError(f"invalid agent assignments: {', '.join(invalid_agents)}")


def _agent_default_models(root: Path) -> dict[str, str]:
    source = agent_source(root)
    defaults = {}
    for agent in sorted(AGENT_TO_ROLE):
        path = source / f"{agent}.md"
        if not path.exists():
            defaults[agent] = ""
            continue
        frontmatter, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        defaults[agent] = frontmatter_binding(frontmatter)
    return defaults


def _resolve_full_model(abstract: str, root: Path, aliases: dict[str, str]) -> str:
    if not abstract:
        return ""
    if abstract in aliases:
        return aliases[abstract]
    return resolve_model(abstract, root=root, models=[], auth=set(), costs={})


def _catalog_models(
    assignments: dict[str, dict[str, str]],
    defaults: dict[str, str],
    aliases: dict[str, str],
) -> list[str]:
    models = set(defaults.values())
    models.update(assignments["roles"].values())
    models.update(assignments["agents"].values())
    models.update(aliases.keys())
    return sorted(model for model in models if model)
