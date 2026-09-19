"""Filesystem-backed live gate. In-memory forged decisions and CURRENT overrides cannot pass."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .loop_engine import apply_event, new_ticket

DEFAULT_SUPERVISOR_ROOT = Path("/opt/xiaozhi-clean/agent-lab/supervisor")


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def load_decision_file(root: Path, filename: str | None) -> dict[str, Any] | None:
    if not filename:
        return None
    decisions = (root / "decisions").resolve()
    path = (decisions / filename).resolve()
    if not str(path).startswith(str(decisions)) or not path.is_file():
        raise ValueError("INVALID_DECISION")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["_file_backed"] = True
    data["_source_path"] = str(path)
    return data


def restore_monotonic(disk_ticket: dict[str, Any], incoming: dict[str, Any] | None) -> dict[str, Any]:
    ticket = dict(disk_ticket)
    if not incoming:
        return ticket
    for key in (
        "patch_attempts_used",
        "audit_revisits_used",
        "verification_runs_used",
        "subagent_invocations_used",
    ):
        ticket[key] = max(int(disk_ticket.get(key, 0)), int(incoming.get(key, 0)))
    for key in (
        "max_patch_attempts",
        "max_audit_revisits",
        "max_verification_runs",
        "max_subagent_invocations",
    ):
        # live ceilings come from disk; agents cannot raise via payload
        ticket[key] = int(disk_ticket.get(key, ticket[key]))
    return ticket


def apply_live(
    ticket_id: str,
    event: dict[str, Any],
    *,
    root: Path | None = None,
    decision_file: str | None = None,
) -> dict[str, Any]:
    root = Path(root) if root is not None else DEFAULT_SUPERVISOR_ROOT
    current = _read_json(root / "CURRENT.json", {})
    index = _read_json(root / "failure_index.json", {})
    ticket_path = root / "tickets" / f"{ticket_id}.json"
    if ticket_path.exists():
        disk_ticket = _read_json(ticket_path, {})
        ticket = restore_monotonic(disk_ticket, event.get("ticket_override"))
    else:
        ticket = new_ticket(ticket_id, event.get("title") or ticket_id)
    try:
        decision = load_decision_file(root, decision_file)
    except ValueError:
        ticket["status"] = "BLOCKED_SUPERVISOR"
        ticket["stop_reason"] = "INVALID_DECISION"
        return {"allowed": False, "ticket": ticket, "status": "BLOCKED_SUPERVISOR", "stop_reason": "INVALID_DECISION"}

    if event.get("decision") and not decision:
        return {
            "allowed": False,
            "ticket": ticket,
            "status": "BLOCKED_SUPERVISOR",
            "stop_reason": "SUPERVISOR_DECISION_REQUIRED",
        }

    result = apply_event(
        ticket,
        event,
        current=current,
        decision=decision,
        failure_index=index,
    )
    _write_json(ticket_path, result["ticket"])
    _write_json(root / "failure_index.json", index)
    result["failure_index"] = index
    return result
