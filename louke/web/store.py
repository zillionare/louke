from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .._common import _toml_load
from ..models import SCHEMA as MODELS_SCHEMA
from ..models import config_path, load_config


DOC_NAME_TO_FILE = {
    "spec": "spec.md",
    "acceptance": "acceptance.md",
    "test-plan": "test-plan.md",
}


class ConflictError(RuntimeError):
    pass


class ValidationError(RuntimeError):
    pass


@dataclass
class ResourceMetadata:
    updated_at: str
    last_modified_by: str


class ProjectStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.louke_dir = self.root / ".louke"
        self.project_dir = self.root / ".louke" / "project"
        self.specs_dir = self.project_dir / "specs"
        self.wiki_dir = self.root / ".louke" / "wiki"
        self.wiki_pages_dir = self.wiki_dir / "pages"
        self.activity_path = self.project_dir / ".serve-activity.jsonl"
        self.project_info_path = self.project_dir / "project.toml"
        self.users_path = self.louke_dir / "web-users.json"
        if not self.project_info_path.exists():
            raise FileNotFoundError(f"missing {self.project_info_path}")

    @property
    def spec_id(self) -> str:
        return str((self.project_info().get("project") or {}).get("spec_id") or "")

    def project_info(self) -> dict[str, Any]:
        return _toml_load(self.project_info_path)

    def health_payload(self) -> dict[str, str]:
        return {"status": "ok", "spec_id": self.spec_id}

    def list_users(self) -> list[dict[str, str]]:
        payload = self._read_users_payload()
        users = payload.get("users")
        if not isinstance(users, list):
            return []
        result: list[dict[str, str]] = []
        for item in users:
            if not isinstance(item, dict):
                continue
            username = str(item.get("username") or "").strip()
            password = str(item.get("password") or "")
            if not username:
                continue
            result.append({"username": username, "password": password})
        return result

    def user_exists(self, username: str) -> bool:
        return any(user["username"] == username for user in self.list_users())

    def create_user(self, username: str, password: str) -> None:
        if self.user_exists(username):
            raise ValidationError("username already exists")
        users = self.list_users()
        users.append({"username": username, "password": password})
        payload = {"version": 1, "users": users}
        self._atomic_write_text(self.users_path, self._stable_json(payload) + "\n")

    def verify_user(self, username: str, password: str) -> bool:
        for user in self.list_users():
            if user["username"] == username and user["password"] == password:
                return True
        return False

    def list_spec_documents(self, spec_id: str | None = None) -> list[dict[str, str]]:
        target_spec_id = spec_id or self.spec_id
        items: list[dict[str, str]] = []
        for doc_name, file_name in DOC_NAME_TO_FILE.items():
            path = self.specs_dir / target_spec_id / file_name
            if not path.exists():
                continue
            metadata = self._metadata_for(path)
            items.append(
                {
                    "spec_id": target_spec_id,
                    "doc_name": doc_name,
                    "path": self.relative_path(path),
                    "updated_at": metadata.updated_at,
                    "last_modified_by": metadata.last_modified_by,
                }
            )
        return items

    def doc_path(self, spec_id: str, doc_name: str) -> Path:
        if doc_name not in DOC_NAME_TO_FILE:
            raise ValidationError(f"unsupported document name: {doc_name}")
        path = self.specs_dir / spec_id / DOC_NAME_TO_FILE[doc_name]
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    def wiki_page_path(self, page: str) -> Path:
        page_name = self._normalize_page_name(page)
        return self.wiki_pages_dir / f"{page_name}.md"

    def read_doc(self, spec_id: str, doc_name: str) -> tuple[str, str, ResourceMetadata]:
        path = self.doc_path(spec_id, doc_name)
        body_md = path.read_text(encoding="utf-8")
        return body_md, self._token_for_text(path, body_md), self._metadata_for(path)

    def write_doc(
        self,
        spec_id: str,
        doc_name: str,
        body_md: str,
        version_token: str,
        actor_name: str,
    ) -> tuple[str, ResourceMetadata]:
        path = self.doc_path(spec_id, doc_name)
        self._check_actor(actor_name)
        current = path.read_text(encoding="utf-8")
        self._assert_token(path, current, version_token)
        self._atomic_write_text(path, self._ensure_trailing_newline(body_md))
        metadata = self.record_activity("document.updated", path, actor_name)
        return self._token_for_text(path, body_md), metadata

    def list_wiki_pages(self) -> list[dict[str, str]]:
        if not self.wiki_pages_dir.exists():
            return []
        pages = []
        for path in sorted(self.wiki_pages_dir.rglob("*.md")):
            metadata = self._metadata_for(path)
            relative = path.relative_to(self.wiki_pages_dir).as_posix()
            pages.append(
                {
                    "page": relative[:-3],
                    "path": self.relative_path(path),
                    "updated_at": metadata.updated_at,
                    "last_modified_by": metadata.last_modified_by,
                }
            )
        return pages

    def read_wiki_page(self, page: str) -> tuple[Path, str, str, ResourceMetadata]:
        path = self.wiki_page_path(page)
        if not path.exists():
            raise FileNotFoundError(path)
        body_md = path.read_text(encoding="utf-8")
        return path, body_md, self._token_for_text(path, body_md), self._metadata_for(path)

    def write_wiki_page(
        self,
        page: str,
        body_md: str,
        version_token: str,
        actor_name: str,
    ) -> tuple[Path, str, ResourceMetadata]:
        path = self.wiki_page_path(page)
        self._check_actor(actor_name)
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if path.exists():
            self._assert_token(path, current, version_token)
        elif version_token not in {"", "new"}:
            raise ConflictError("wiki page does not exist yet; use empty token to create it")
        self._atomic_write_text(path, self._ensure_trailing_newline(body_md))
        metadata = self.record_activity("wiki.updated", path, actor_name)
        return path, self._token_for_text(path, body_md), metadata

    def read_bindings(self) -> tuple[dict[str, Any], str, ResourceMetadata]:
        path = config_path(project=True, root=self.root)
        config = load_config(path)
        assignments = config.get("assignments")
        if not isinstance(assignments, dict):
            assignments = {}
        assignments.setdefault("roles", {})
        assignments.setdefault("agents", {})
        config["assignments"] = assignments
        config.setdefault("$schema", MODELS_SCHEMA)
        config.setdefault("version", 1)
        config.setdefault("aliases", {})
        token = self._token_for_json(path, config)
        metadata = self._metadata_for(path) if path.exists() else ResourceMetadata("", "")
        return config, token, metadata

    def write_bindings(
        self,
        config: dict[str, Any],
        version_token: str,
        actor_name: str,
    ) -> tuple[str, ResourceMetadata]:
        path = config_path(project=True, root=self.root)
        self._check_actor(actor_name)
        current, current_token, _ = self.read_bindings()
        if current_token != version_token:
            raise ConflictError("bindings version token is stale")
        payload = {
            "$schema": MODELS_SCHEMA,
            "version": int(config.get("version") or 1),
            "aliases": dict(config.get("aliases") or {}),
            "assignments": {
                "roles": dict((config.get("assignments") or {}).get("roles") or {}),
                "agents": dict((config.get("assignments") or {}).get("agents") or {}),
            },
        }
        self._atomic_write_text(path, self._stable_json(payload) + "\n")
        metadata = self.record_activity("bindings.updated", path, actor_name)
        return self._token_for_json(path, payload), metadata

    def read_text_target(self, target_path: str) -> tuple[Path, str, str, ResourceMetadata]:
        path = self.resolve_target_path(target_path)
        body_md = path.read_text(encoding="utf-8")
        return path, body_md, self._token_for_text(path, body_md), self._metadata_for(path)

    def resolve_target_path(self, target_path: str) -> Path:
        candidate = (self.root / target_path).resolve()
        if not str(candidate).startswith(str(self.root)):
            raise ValidationError("target path escapes project root")
        if not candidate.exists():
            raise FileNotFoundError(candidate)
        return candidate

    def relative_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def record_activity(
        self,
        event_type: str,
        path: Path,
        actor_name: str,
        extra: dict[str, Any] | None = None,
    ) -> ResourceMetadata:
        updated_at = self._now()
        payload: dict[str, Any] = {
            "type": event_type,
            "target": self.relative_path(path),
            "actor_name": actor_name,
            "updated_at": updated_at,
        }
        if extra:
            payload.update(extra)
        self.activity_path.parent.mkdir(parents=True, exist_ok=True)
        with self.activity_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return ResourceMetadata(updated_at=updated_at, last_modified_by=actor_name)

    def latest_activity(self, path: Path) -> ResourceMetadata:
        target = self.relative_path(path)
        latest: dict[str, Any] | None = None
        if self.activity_path.exists():
            for line in self.activity_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("target") == target:
                    latest = record
        if latest:
            return ResourceMetadata(
                updated_at=str(latest.get("updated_at") or ""),
                last_modified_by=str(latest.get("actor_name") or ""),
            )
        if path.exists():
            stat = path.stat()
            updated_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")
            return ResourceMetadata(updated_at=updated_at, last_modified_by="")
        return ResourceMetadata(updated_at="", last_modified_by="")

    def _metadata_for(self, path: Path) -> ResourceMetadata:
        return self.latest_activity(path)

    def _check_actor(self, actor_name: str) -> None:
        if not str(actor_name).strip():
            raise ValidationError("actor_name is required")

    def _assert_token(self, path: Path, current_text: str, version_token: str) -> None:
        current = self._token_for_text(path, current_text)
        if current != version_token:
            raise ConflictError("version token is stale")

    def _token_for_text(self, path: Path, text: str) -> str:
        digest = hashlib.sha256()
        digest.update(self.relative_path(path).encode("utf-8"))
        digest.update(b"\n")
        digest.update(text.encode("utf-8"))
        return digest.hexdigest()

    def _token_for_json(self, path: Path, data: dict[str, Any]) -> str:
        return self._token_for_text(path, self._stable_json(data))

    def _stable_json(self, data: dict[str, Any]) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)

    def _atomic_write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix=f"{path.name}.", dir=str(path.parent))
        with open(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        Path(tmp_path).replace(path)

    def _normalize_page_name(self, page: str) -> str:
        value = str(page).strip().replace("\\", "/")
        if value in {"", ".", ".."}:
            raise ValidationError("wiki page name must not be empty")
        parts = [part for part in value.split("/") if part]
        if not parts or any(part in {".", ".."} for part in parts):
            raise ValidationError("wiki page name contains invalid path segments")
        return "/".join(parts)

    def _ensure_trailing_newline(self, body_md: str) -> str:
        return body_md if body_md.endswith("\n") else body_md + "\n"

    def _now(self) -> str:
        return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")

    def _read_users_payload(self) -> dict[str, Any]:
        if not self.users_path.exists():
            return {"version": 1, "users": []}
        try:
            payload = json.loads(self.users_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"invalid users file: {self.users_path}") from exc
        if not isinstance(payload, dict):
            raise ValidationError("users payload must be an object")
        return payload
