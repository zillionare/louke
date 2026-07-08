"""Stage result artifacts for Maestro gates.

Artifacts live under:
    .louke/project/stage-results/{spec_id}/{stage}/

Kinds currently used in the first runtime-enforced slice:
    - author-result.json
    - review-result.json
    - gate-result.json
    - waiver.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ._common import PROJECT_INFO_PATH, _toml_load

SCHEMA_VERSION = 1
STAGE_RESULTS_ROOT = Path('.louke/project/stage-results')


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _spec_dir(spec_id: str) -> Path:
    return Path('.louke/project/specs') / spec_id


def contract_bundle_paths(spec_id: str) -> List[Path]:
    spec_dir = _spec_dir(spec_id)
    return [
        spec_dir / 'spec.md',
        spec_dir / 'acceptance.md',
        spec_dir / 'test-plan.md',
        spec_dir / 'architecture.md',
        spec_dir / 'interfaces.md',
        PROJECT_INFO_PATH,
    ]


def _stable_project_contract_payload() -> bytes:
    data = _toml_load(PROJECT_INFO_PATH)
    stable = {
        'meta': {
            'test_framework': str(((data.get('meta') or {}).get('test_framework', '') or '')).strip(),
        },
        'e2e': (data.get('e2e') or {}),
    }
    return json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _contract_payload_bytes(path: Path) -> bytes:
    if path == PROJECT_INFO_PATH:
        return _stable_project_contract_payload()
    return path.read_bytes()


def compute_contract_bundle_hash(spec_id: str) -> str:
    """Hash the current contract bundle.

    Core contract documents are hashed as full file contents. `project.toml` is
    narrowed to stable contract fields only, so runtime state like `current_stage`
    does not stale reviewer/author artifacts.
    """
    sha = hashlib.sha256()
    for path in contract_bundle_paths(spec_id):
        sha.update(str(path.as_posix()).encode('utf-8'))
        if path.exists():
            sha.update(b'\0exists\0')
            sha.update(_contract_payload_bytes(path))
        else:
            sha.update(b'\0missing\0')
    return sha.hexdigest()


def stage_dir(spec_id: str, stage: str) -> Path:
    return STAGE_RESULTS_ROOT / spec_id / stage


def artifact_path(spec_id: str, stage: str, kind: str) -> Path:
    return stage_dir(spec_id, stage) / f'{kind}.json'


def _normalize_strings(values: Optional[Iterable[str]]) -> List[str]:
    if not values:
        return []
    out = []
    for value in values:
        text = str(value).strip()
        if text:
            out.append(text)
    return out


def _payload_hash(payload: Dict[str, Any]) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(blob).hexdigest()


def write_stage_result(
    *,
    spec_id: str,
    stage: str,
    kind: str,
    role: str,
    verdict: str,
    reviewed_targets: Optional[Iterable[str]] = None,
    blocking_findings: Optional[Iterable[str]] = None,
    accepted_risks: Optional[Iterable[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    contract_bundle_hash: Optional[str] = None,
) -> Path:
    path = artifact_path(spec_id, stage, kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        'schema_version': SCHEMA_VERSION,
        'spec_id': spec_id,
        'stage': stage,
        'kind': kind,
        'role': role,
        'verdict': verdict,
        'reviewed_targets': _normalize_strings(reviewed_targets),
        'blocking_findings': _normalize_strings(blocking_findings),
        'accepted_risks': _normalize_strings(accepted_risks),
        'created_at': _utc_now_iso(),
        'contract_bundle_hash': contract_bundle_hash or compute_contract_bundle_hash(spec_id),
        'metadata': metadata or {},
    }
    payload['output_hash'] = _payload_hash(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path


def load_stage_result(spec_id: str, stage: str, kind: str) -> Optional[Dict[str, Any]]:
    path = artifact_path(spec_id, stage, kind)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None


def verify_stage_result_hash(data: Dict[str, Any]) -> bool:
    if not data or 'output_hash' not in data:
        return False
    payload = dict(data)
    expected = payload.pop('output_hash', '')
    return _payload_hash(payload) == expected
