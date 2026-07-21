"""IF-REG-01 machine contract registry — discover / resolve / validate (FR-0700).

The active source is the package-owned ``louke/schemas/registry.json`` plus the
schema documents under ``louke/schemas/{machine-contracts,agent-io}/<identity>/
<version>.json``.  The registry is fail-closed: while the atomic activation gate
is open every schema stays ``candidate`` and :func:`resolve` refuses with
``SCHEMA_NOT_ACTIVE``.  ``discover`` may surface candidates, and ``validate``
checks instance bytes against a packaged schema without granting an active
verdict.  AC-FR0700-01.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMAS_ROOT = Path(__file__).resolve().parents[1] / "schemas"
REGISTRY_PATH = SCHEMAS_ROOT / "registry.json"

ERROR_CODES = (
    "SCHEMA_UNKNOWN",
    "SCHEMA_NOT_ACTIVE",
    "SCHEMA_DIGEST_MISMATCH",
    "SCHEMA_VALIDATION_FAILED",
    "SCHEMA_MIGRATION_REQUIRED",
)


class RegistryError(Exception):
    """A fail-closed registry rejection carrying an IF-REG-01 error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class RegistryView:
    """The result of :func:`discover`."""

    registry_version: str
    registry_digest: str
    schemas: list[dict[str, Any]]


@dataclass(frozen=True)
class SchemaRef:
    """A caller-supplied reference to a packaged schema."""

    identity: str
    version: str
    digest: str | None = None


@dataclass(frozen=True)
class SchemaDocument:
    """A resolved active schema document."""

    identity: str
    version: str
    digest: str
    schema: dict[str, Any]


@dataclass(frozen=True)
class ValidationResult:
    """The result of :func:`validate`."""

    valid: bool
    schema_ref: dict[str, Any]
    document_digest: str
    errors: list[dict[str, Any]] = field(default_factory=list)


def file_digest(data: bytes) -> str:
    """Return the ``sha256:``-prefixed digest of ``data``."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_registry() -> dict[str, Any]:
    """Load and return the package-owned registry document."""
    if not REGISTRY_PATH.is_file():
        raise RegistryError("SCHEMA_UNKNOWN", f"registry not found: {REGISTRY_PATH}")
    return json.loads(REGISTRY_PATH.read_bytes())


def _all_entries(registry: dict[str, Any]) -> list[dict[str, Any]]:
    return list(registry.get("schemas", [])) + list(
        registry.get("agent_io_schemas", [])
    )


def discover(kind: str | None = None) -> RegistryView:
    """Discover registry schemas, optionally narrowed to a single ``kind``.

    Every required machine-contract kind and Agent I/O schema is surfaced with
    its ``identity``/``version``/``digest``/``status``.  Candidates are shown but
    never resolvable.  AC-FR0700-01.
    """
    registry = load_registry()
    entries = _all_entries(registry)
    if kind is not None:
        entries = [e for e in entries if e.get("kind") == kind]
    return RegistryView(
        registry_version=registry["registry_version"],
        registry_digest=file_digest(REGISTRY_PATH.read_bytes()),
        schemas=[dict(e) for e in entries],
    )


def _find_entry(registry: dict[str, Any], identity: str) -> list[dict[str, Any]]:
    return [e for e in _all_entries(registry) if e["identity"] == identity]


def resolve(identity: str, version: str, digest: str) -> SchemaDocument:
    """Resolve an *active* schema by exact identity/version/digest.

    Fail-closed: unknown identity/version raises ``SCHEMA_UNKNOWN``; a candidate
    (not-yet-activated) schema raises ``SCHEMA_NOT_ACTIVE``; a drifted digest
    raises ``SCHEMA_DIGEST_MISMATCH``.  No fallback.  AC-FR0700-01.
    """
    registry = load_registry()
    by_identity = _find_entry(registry, identity)
    if not by_identity:
        raise RegistryError("SCHEMA_UNKNOWN", f"unknown schema identity: {identity}")
    entry = next((e for e in by_identity if e["version"] == version), None)
    if entry is None:
        raise RegistryError(
            "SCHEMA_UNKNOWN",
            f"unknown version {version} for {identity}; no compatible migration",
        )
    if entry.get("status") != "active":
        raise RegistryError(
            "SCHEMA_NOT_ACTIVE",
            f"{identity}@{version} is {entry.get('status')}; activation gate is open",
        )
    if digest != entry["digest"]:
        raise RegistryError(
            "SCHEMA_DIGEST_MISMATCH",
            f"digest mismatch for {identity}@{version}",
        )
    schema = json.loads((SCHEMAS_ROOT / entry["path"]).read_bytes())
    return SchemaDocument(identity, version, entry["digest"], schema)


def _load_schema_entry(registry: dict[str, Any], ref: SchemaRef) -> dict[str, Any]:
    by_identity = _find_entry(registry, ref.identity)
    if not by_identity:
        raise RegistryError(
            "SCHEMA_UNKNOWN", f"unknown schema identity: {ref.identity}"
        )
    entry = next((e for e in by_identity if e["version"] == ref.version), None)
    if entry is None:
        raise RegistryError(
            "SCHEMA_UNKNOWN",
            f"unknown version {ref.version} for {ref.identity}",
        )
    if ref.digest is not None and ref.digest != entry["digest"]:
        raise RegistryError(
            "SCHEMA_DIGEST_MISMATCH",
            f"digest mismatch for {ref.identity}@{ref.version}",
        )
    return entry


def validate(schema_ref: SchemaRef, instance_bytes: bytes) -> ValidationResult:
    """Validate ``instance_bytes`` against the packaged schema for ``schema_ref``.

    Resolves the schema by identity/version (and digest when supplied), then runs
    Draft 2020-12 validation.  Unknown ref → ``SCHEMA_UNKNOWN``; digest drift →
    ``SCHEMA_DIGEST_MISMATCH``.  AC-FR0700-01.
    """
    from jsonschema import Draft202012Validator

    registry = load_registry()
    entry = _load_schema_entry(registry, schema_ref)
    schema = json.loads((SCHEMAS_ROOT / entry["path"]).read_bytes())
    document_digest = file_digest(instance_bytes)
    try:
        instance = json.loads(instance_bytes)
    except json.JSONDecodeError as exc:
        return ValidationResult(
            valid=False,
            schema_ref={
                "identity": schema_ref.identity,
                "version": schema_ref.version,
                "digest": entry["digest"],
            },
            document_digest=document_digest,
            errors=[
                {
                    "json_pointer": "",
                    "keyword": "parse",
                    "expected": "json",
                    "actual_type": str(exc),
                }
            ],
        )
    validator = Draft202012Validator(schema)
    errors = []
    for err in sorted(
        validator.iter_errors(instance), key=lambda e: list(e.absolute_path)
    ):
        errors.append(
            {
                "json_pointer": "/" + "/".join(str(p) for p in err.absolute_path),
                "keyword": err.validator,
                "expected": err.validator_value,
                "actual_type": type(err.instance).__name__,
            }
        )
    return ValidationResult(
        valid=not errors,
        schema_ref={
            "identity": schema_ref.identity,
            "version": schema_ref.version,
            "digest": entry["digest"],
        },
        document_digest=document_digest,
        errors=errors,
    )


def _emit(payload: Any, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:  # pragma: no cover - human formatting is incidental
        print(payload)


def main(argv: list[str] | None = None) -> int:
    """CLI mirror of the registry API: discover / resolve / validate."""
    parser = argparse.ArgumentParser(prog="python -m louke._tools.contract_registry")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--format", choices=("json",), default="json")
    sub = parser.add_subparsers(dest="command", required=True)

    p_disc = sub.add_parser("discover", parents=[common])
    p_disc.add_argument("--kind", default=None)

    p_res = sub.add_parser("resolve", parents=[common])
    p_res.add_argument("--identity", required=True)
    p_res.add_argument("--version", required=True)
    p_res.add_argument("--digest", required=True)

    p_val = sub.add_parser("validate", parents=[common])
    p_val.add_argument("--identity", required=True)
    p_val.add_argument("--version", required=True)
    p_val.add_argument("--digest", default=None)
    p_val.add_argument("--instance", required=True, help="path to instance JSON")

    args = parser.parse_args(argv)

    try:
        if args.command == "discover":
            view = discover(args.kind)
            _emit(
                {
                    "registry_version": view.registry_version,
                    "registry_digest": view.registry_digest,
                    "schemas": view.schemas,
                },
                args.format,
            )
            return 0
        if args.command == "resolve":
            doc = resolve(args.identity, args.version, args.digest)
            _emit(
                {
                    "identity": doc.identity,
                    "version": doc.version,
                    "digest": doc.digest,
                },
                args.format,
            )
            return 0
        if args.command == "validate":
            ref = SchemaRef(args.identity, args.version, args.digest)
            result = validate(ref, Path(args.instance).read_bytes())
            _emit(
                {
                    "valid": result.valid,
                    "schema_ref": result.schema_ref,
                    "document_digest": result.document_digest,
                    "errors": result.errors,
                },
                args.format,
            )
            return 0 if result.valid else 1
    except RegistryError as exc:
        _emit({"error": exc.code, "message": exc.message}, args.format)
        return 2
    return 2  # pragma: no cover - argparse enforces a command


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
