"""Allowlist for GitHub bridge publish. Unrelated Clean runtime paths are refused."""

from __future__ import annotations

from pathlib import Path

SECRET_NAME_MARKERS = (
    ".env",
    "credentials",
    "credential",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    ".pem",
    ".p12",
    ".key",
    "secrets",
    "secret",
    "api_key",
    "apikey",
    "api-token",
    "token",
    "private_key",
    "known_hosts",
    "deploy.key",
)

# Relative to agent-lab/
PUBLISH_ROOTS = (
    "LOOP_POLICY.md",
    "STATE.json",
    "BACKLOG.yaml",
    "SPEC.md",
    "README.md",
    "supervisor/",
    "tests/loop/",
    "bin/supervisor_sync.py",
    "reports/P2.6",
    "tickets/",
)

FORBIDDEN_PREFIXES = (
    "../",
    "overlays/",
    "source/",
    "data/",
    "docker-compose",
    "backups/",
)

FORBIDDEN_EXACT_FRAGMENTS = (
    "docker-logs",
    "__pycache__",
    ".pyc",
)


def is_secret_path(path: Path) -> bool:
    name = path.name.lower()
    full = str(path).lower().replace("\\", "/")
    return any(marker in name or marker in full for marker in SECRET_NAME_MARKERS)


def is_publish_allowed(rel_path: str) -> tuple[bool, str]:
    normalized = rel_path.replace("\\", "/").lstrip("./")
    if normalized.startswith("/") or normalized.startswith("opt/") or "xiaozhi-clean/" in normalized and not normalized.startswith("supervisor"):
        if any(normalized.startswith(p) for p in ("LOOP_POLICY.md", "STATE.json", "supervisor/", "tests/loop/", "bin/", "reports/", "tickets/", "BACKLOG.yaml", "SPEC.md", "README.md")):
            pass
        else:
            return False, "outside_agent_lab_allowlist"
    for prefix in FORBIDDEN_PREFIXES:
        if normalized.startswith(prefix) or f"/{prefix}" in normalized:
            return False, "runtime_or_escape_path"
    for frag in FORBIDDEN_EXACT_FRAGMENTS:
        if frag in normalized:
            return False, "excluded_artifact"
    if is_secret_path(Path(normalized)):
        return False, "secret_path"
    allowed = False
    for root in PUBLISH_ROOTS:
        if normalized == root.rstrip("/") or normalized.startswith(root):
            allowed = True
            break
    if not allowed:
        return False, "not_in_publish_allowlist"
    return True, "ok"
