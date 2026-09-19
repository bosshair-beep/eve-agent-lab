"""Deterministic loop policy engine. Agents cannot raise budgets or mint Supervisor decisions."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .failure_signature import signature_hash

DEFAULT_BUDGET = {
    "max_patch_attempts": 2,
    "max_audit_revisits": 2,
    "max_verification_runs": 3,
    "max_subagent_invocations": 8,
}

CANONICAL_STATES = (
    "NEW",
    "AUDITING",
    "ROOT_CAUSE_FOUND",
    "READY_TO_PATCH",
    "IMPLEMENTING",
    "VERIFYING",
    "SUPERVISOR_REVIEW",
    "CLOSED",
    "REJECTED",
    "CANCELLED",
    "BLOCKED_EXTERNAL",
    "BLOCKED_SUPERVISOR",
)

PROGRESS_TOKENS = (
    "NEW_EVIDENCE",
    "NEW_ROOT_CAUSE_EVIDENCE",
    "MEASURABLE_REDUCTION_IN_FAILURE",
    "VERIFIER_CONFIRMED_BEHAVIOR_CHANGE",
)

SUPERVISOR_DECISIONS = (
    "APPROVE",
    "REJECT",
    "INVESTIGATE",
    "STOP",
    "APPROVE_RETRY",
    "APPROVE_SCOPE_EXPANSION",
    "APPROVE_NEW_BUDGET",
)

CIRCUIT_BREAKERS = (
    "SAME_FAILURE_SIGNATURE_TWICE",
    "NO_NEW_EVIDENCE",
    "NO_MEASURABLE_PROGRESS",
    "ROOT_CAUSE_CHANGED",
    "SCOPE_EXPANSION_REQUIRED",
    "DB_SCHEMA_CHANGE_REQUIRED",
    "PROVIDER_CHANGE_REQUIRED",
    "INFRA_CHANGE_REQUIRED",
    "CREDENTIAL_CHANGE_REQUIRED",
    "RUNTIME_RESTART_REQUIRED",
    "SAFETY_BOUNDARY_REACHED",
    "BUDGET_EXHAUSTED",
    "VERIFIER_CANNOT_REPRODUCE",
    "AUDITOR_VERIFIER_UNRESOLVED_DISAGREEMENT",
    "AUTOMATION_DISABLED",
    "GLOBAL_STOP",
    "IMPLEMENTER_DISABLED",
    "SUPERVISOR_DECISION_REQUIRED",
    "DUPLICATE_FAILURE_TICKET",
    "INVALID_BUDGET_MUTATION",
    "INVALID_DECISION",
)

IMPLEMENTATION_ACTIONS = frozenset(
    {
        "START_IMPLEMENTATION",
        "PATCH_ATTEMPT",
        "RETRY_PATCH",
        "ENABLE_IMPLEMENTER",
    }
)
RETRY_ACTIONS = frozenset({"RETRY_AFTER_FAIL", "RETRY_PATCH", "RESUME_AFTER_FAIL"})
FORBIDDEN_IMPLEMENTER_STATES = frozenset({"CLOSED", "SUPERVISOR_APPROVED"})


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_current() -> dict[str, Any]:
    return {
        "project": "CLEAN_VI_MIGRATION",
        "phase": "P2.6_SUPERVISOR_BRIDGE_AND_LOOP_POLICY",
        "automation_enabled": False,
        "global_stop": False,
        "implementer_enabled": False,
        "updated_at": utc_now(),
    }


def new_ticket(
    ticket_id: str,
    title: str,
    *,
    phase: str = "P2.6_SUPERVISOR_BRIDGE_AND_LOOP_POLICY",
    scope: str = "",
    files_allowed: list[str] | None = None,
) -> dict[str, Any]:
    now = utc_now()
    ticket = {
        "ticket_id": ticket_id,
        "title": title,
        "phase": phase,
        "status": "NEW",
        "scope": scope,
        "created_at": now,
        "updated_at": now,
        "audit_revisits_used": 0,
        "patch_attempts_used": 0,
        "verification_runs_used": 0,
        "subagent_invocations_used": 0,
        **DEFAULT_BUDGET,
        "current_failure_signature": None,
        "failure_signature_history": [],
        "new_evidence_since_last_attempt": False,
        "measurable_progress": False,
        "files_allowed": list(files_allowed or []),
        "files_changed": [],
        "tests_required": [],
        "tests_executed": [],
        "tests_passed": [],
        "tests_failed": [],
        "runtime_touched": False,
        "db_touched": False,
        "provider_touched": False,
        "infra_touched": False,
        "auditor_status": "IDLE",
        "implementer_status": "DISABLED",
        "verifier_status": "IDLE",
        "supervisor_required": True,
        "supervisor_decision": None,
        "stop_reason": None,
        "report_path": None,
        "evidence_path": None,
        "evidence_hashes": [],
    }
    return ticket


def _block(ticket: dict[str, Any], reason: str, **extra: Any) -> dict[str, Any]:
    ticket["status"] = "BLOCKED_SUPERVISOR"
    ticket["stop_reason"] = reason
    ticket["updated_at"] = utc_now()
    ticket["supervisor_required"] = True
    result = {
        "allowed": False,
        "ticket": ticket,
        "stop_reason": reason,
        "status": "BLOCKED_SUPERVISOR",
    }
    result.update(extra)
    return result


def _ok(ticket: dict[str, Any], **extra: Any) -> dict[str, Any]:
    ticket["updated_at"] = utc_now()
    result = {"allowed": True, "ticket": ticket, "status": ticket["status"], "stop_reason": None}
    result.update(extra)
    return result


def load_current(path: Path | None = None, data: dict[str, Any] | None = None) -> dict[str, Any]:
    if data is not None:
        current = copy.deepcopy(data)
    elif path is not None and path.exists():
        current = json.loads(path.read_text(encoding="utf-8"))
    else:
        current = default_current()
    current.setdefault("automation_enabled", False)
    current.setdefault("global_stop", False)
    current.setdefault("implementer_enabled", False)
    return current


def validate_decision(decision: dict[str, Any] | None, ticket_id: str) -> tuple[bool, str | None]:
    if not decision:
        return False, "SUPERVISOR_DECISION_REQUIRED"
    if decision.get("ticket_id") != ticket_id:
        return False, "INVALID_DECISION"
    if decision.get("decision") not in SUPERVISOR_DECISIONS:
        return False, "INVALID_DECISION"
    if decision.get("actor") not in {"HUMAN", "SUPERVISOR"}:
        return False, "INVALID_DECISION"
    for required in ("reason", "timestamp"):
        if not decision.get(required):
            return False, "INVALID_DECISION"
    return True, None


def implementation_permitted(current: dict[str, Any]) -> tuple[bool, str | None]:
    if current.get("global_stop") is True:
        return False, "GLOBAL_STOP"
    if current.get("automation_enabled") is not True:
        return False, "AUTOMATION_DISABLED"
    if current.get("implementer_enabled") is not True:
        return False, "IMPLEMENTER_DISABLED"
    return True, None


def retry_permitted_killswitch(current: dict[str, Any]) -> tuple[bool, str | None]:
    if current.get("global_stop") is True:
        return False, "GLOBAL_STOP"
    return True, None


def _budget_would_exceed(ticket: dict[str, Any], counter: str) -> bool:
    used_key = f"{counter}_used"
    max_key = f"max_{counter}"
    return int(ticket[used_key]) + 1 > int(ticket[max_key])


def increment_counter(ticket: dict[str, Any], counter: str) -> dict[str, Any] | None:
    """Return blocked result if ceiling hit; else increment and return None."""
    if _budget_would_exceed(ticket, counter):
        return _block(ticket, "BUDGET_EXHAUSTED", exhausted=counter)
    ticket[f"{counter}_used"] = int(ticket[f"{counter}_used"]) + 1
    return None


def apply_budget_change(ticket: dict[str, Any], change: dict[str, Any] | None) -> dict[str, Any] | None:
    if not change:
        return _block(ticket, "INVALID_BUDGET_MUTATION")
    allowed_keys = set(DEFAULT_BUDGET)
    for key, value in change.items():
        if key not in allowed_keys:
            return _block(ticket, "INVALID_BUDGET_MUTATION")
        if not isinstance(value, int):
            return _block(ticket, "INVALID_BUDGET_MUTATION")
        used_key = key.replace("max_", "") + "_used"
        used = int(ticket[used_key])
        if int(value) < used:
            return _block(ticket, "INVALID_BUDGET_MUTATION")
        ticket[key] = int(value)
    return None


def record_failure_signature(ticket: dict[str, Any], payload: dict[str, Any], failure_index: dict[str, str]) -> dict[str, Any] | None:
    digest = signature_hash(payload)
    history = list(ticket.get("failure_signature_history") or [])
    current = ticket.get("current_failure_signature") or {}
    current_hash = current.get("signature_hash")
    if current_hash == digest or digest in history:
        ticket["current_failure_signature"] = {
            "signature_hash": digest,
            "normalized": payload,
        }
        return _block(ticket, "SAME_FAILURE_SIGNATURE_TWICE")
    owner = failure_index.get(digest)
    if owner and owner != ticket["ticket_id"]:
        return _block(ticket, "DUPLICATE_FAILURE_TICKET", owner_ticket=owner)
    if current_hash:
        history.append(current_hash)
    ticket["failure_signature_history"] = history
    ticket["current_failure_signature"] = {"signature_hash": digest, "fields": payload}
    failure_index[digest] = ticket["ticket_id"]
    return None


def progress_present(event: dict[str, Any], ticket: dict[str, Any] | None = None) -> bool:
    ticket = ticket or {}
    seen = set(ticket.get("evidence_hashes") or [])
    tokens = list(event.get("progress_tokens") or [])
    if event.get("new_evidence_since_last_attempt") is True and "NEW_EVIDENCE" not in tokens:
        tokens.append("NEW_EVIDENCE")
    if event.get("measurable_progress") is True and "MEASURABLE_REDUCTION_IN_FAILURE" not in tokens:
        tokens.append("MEASURABLE_REDUCTION_IN_FAILURE")
    if not any(token in PROGRESS_TOKENS for token in tokens):
        return False
    if any(t in {"NEW_EVIDENCE", "NEW_ROOT_CAUSE_EVIDENCE"} for t in tokens):
        digest = event.get("evidence_sha256")
        path = event.get("evidence_path")
        if not digest or not path or digest in seen:
            return False
        return True
    if "MEASURABLE_REDUCTION_IN_FAILURE" in tokens:
        prev = len(ticket.get("tests_failed") or [])
        new = event.get("tests_failed_count")
        if not isinstance(new, int) or new < 0 or new >= prev:
            return False
        return True
    if "VERIFIER_CONFIRMED_BEHAVIOR_CHANGE" in tokens:
        return event.get("verifier_confirmed") is True and event.get("actor") in {"VERIFIER", "MANAGER"}
    return False


def apply_event(
    ticket: dict[str, Any],
    event: dict[str, Any],
    *,
    current: dict[str, Any] | None = None,
    decision: dict[str, Any] | None = None,
    failure_index: dict[str, str] | None = None,
) -> dict[str, Any]:
    ticket = copy.deepcopy(ticket)
    current = load_current(data=current)
    failure_index = failure_index if failure_index is not None else {}
    action = event.get("action")
    actor = event.get("actor", "MANAGER")

    if actor == "IMPLEMENTER" and (
        event.get("set_status") in FORBIDDEN_IMPLEMENTER_STATES or action in {"VERIFIER_PASS", "CLOSE_TICKET"}
    ):
        return _block(ticket, "SAFETY_BOUNDARY_REACHED")

    if current.get("global_stop") is True and action in {
        "SET_MAX_BUDGET",
        "APPLY_DECISION",
        "CLOSE_TICKET",
        "COUNT_SUBAGENT",
    }:
        return _block(ticket, "GLOBAL_STOP")

    if action == "SET_COUNTERS":
        return _block(ticket, "INVALID_BUDGET_MUTATION")

    if action == "SET_MAX_BUDGET":
        ok, why = retry_permitted_killswitch(current)
        if not ok:
            return _block(ticket, why or "GLOBAL_STOP")
        ok, why = validate_decision(decision, ticket["ticket_id"])
        if not ok:
            return _block(ticket, why or "SUPERVISOR_DECISION_REQUIRED")
        if decision["decision"] not in {"APPROVE_NEW_BUDGET", "APPROVE_RETRY"}:
            return _block(ticket, "INVALID_DECISION")
        blocked = apply_budget_change(ticket, decision.get("approved_budget_change"))
        if blocked:
            return blocked
        ticket["supervisor_decision"] = decision["decision"]
        ticket["stop_reason"] = None
        ticket["status"] = "AUDITING"
        ticket["supervisor_required"] = False
        return _ok(ticket)

    if action in IMPLEMENTATION_ACTIONS:
        ok, why = implementation_permitted(current)
        if not ok:
            return _block(ticket, why or "AUTOMATION_DISABLED")
        if ticket["status"] in {"BLOCKED_SUPERVISOR", "CLOSED", "REJECTED", "CANCELLED"}:
            return _block(ticket, ticket.get("stop_reason") or "SAFETY_BOUNDARY_REACHED")
        blocked = increment_counter(ticket, "patch_attempts")
        if blocked:
            return blocked
        ticket["status"] = "IMPLEMENTING"
        ticket["implementer_status"] = "ACTIVE"
        return _ok(ticket)

    if action == "COUNT_SUBAGENT":
        blocked = increment_counter(ticket, "subagent_invocations")
        if blocked:
            return blocked
        return _ok(ticket)

    if action == "COUNT_AUDIT":
        blocked = increment_counter(ticket, "audit_revisits")
        if blocked:
            return blocked
        ticket["status"] = "AUDITING"
        return _ok(ticket)

    if action == "COUNT_VERIFICATION":
        blocked = increment_counter(ticket, "verification_runs")
        if blocked:
            return blocked
        ticket["status"] = "VERIFYING"
        return _ok(ticket)

    if action == "SCOPE_EXPANSION_REQUIRED":
        return _block(ticket, "SCOPE_EXPANSION_REQUIRED")

    for breaker in (
        "DB_SCHEMA_CHANGE_REQUIRED",
        "PROVIDER_CHANGE_REQUIRED",
        "INFRA_CHANGE_REQUIRED",
        "CREDENTIAL_CHANGE_REQUIRED",
        "RUNTIME_RESTART_REQUIRED",
        "SAFETY_BOUNDARY_REACHED",
        "VERIFIER_CANNOT_REPRODUCE",
        "AUDITOR_VERIFIER_UNRESOLVED_DISAGREEMENT",
        "ROOT_CAUSE_CHANGED",
        "NO_NEW_EVIDENCE",
    ):
        if action == breaker:
            return _block(ticket, breaker)

    if action == "RECORD_FAILURE":
        blocked = record_failure_signature(ticket, event.get("failure") or {}, failure_index)
        if blocked:
            return blocked
        ticket["status"] = "VERIFYING"
        return _ok(ticket, failure_index=failure_index)

    if action in RETRY_ACTIONS:
        ok, why = retry_permitted_killswitch(current)
        if not ok:
            return _block(ticket, why or "GLOBAL_STOP")
        impl_ok, impl_why = implementation_permitted(current)
        if action == "RETRY_PATCH" and not impl_ok:
            return _block(ticket, impl_why or "AUTOMATION_DISABLED")

        if event.get("failure"):
            blocked = record_failure_signature(ticket, event["failure"], failure_index)
            if blocked:
                return blocked

        if not progress_present(event, ticket):
            return _block(ticket, "NO_MEASURABLE_PROGRESS")
        digest = event.get("evidence_sha256")
        if digest:
            hashes = list(ticket.get("evidence_hashes") or [])
            hashes.append(digest)
            ticket["evidence_hashes"] = hashes
            ticket["evidence_path"] = event.get("evidence_path") or ticket.get("evidence_path")

        if event.get("requires_new_budget"):
            okd, why = validate_decision(decision, ticket["ticket_id"])
            if not okd:
                return _block(ticket, why or "SUPERVISOR_DECISION_REQUIRED")
            if decision["decision"] not in {"APPROVE_RETRY", "APPROVE_NEW_BUDGET"}:
                return _block(ticket, "INVALID_DECISION")
            blocked = apply_budget_change(ticket, decision.get("approved_budget_change"))
            if blocked:
                return blocked
            ticket["supervisor_decision"] = decision["decision"]

        if _budget_would_exceed(ticket, "patch_attempts") and action in {"RETRY_PATCH", "RETRY_AFTER_FAIL"}:
            # retry that will patch must have remaining patch budget
            if action == "RETRY_PATCH":
                return _block(ticket, "BUDGET_EXHAUSTED", exhausted="patch_attempts")

        ticket["status"] = "AUDITING"
        ticket["new_evidence_since_last_attempt"] = True
        ticket["measurable_progress"] = True
        return _ok(ticket, failure_index=failure_index)

    if action == "VERIFIER_PASS":
        if actor not in {"VERIFIER", "MANAGER"}:
            return _block(ticket, "SAFETY_BOUNDARY_REACHED")
        ticket["status"] = "SUPERVISOR_REVIEW"
        ticket["supervisor_required"] = True
        ticket["verifier_status"] = "PASS"
        return _ok(ticket)

    if action == "CLOSE_TICKET":
        okd, why = validate_decision(decision, ticket["ticket_id"])
        if not okd:
            return _block(ticket, why or "SUPERVISOR_DECISION_REQUIRED")
        if decision["decision"] != "APPROVE":
            return _block(ticket, "INVALID_DECISION")
        if ticket.get("status") != "SUPERVISOR_REVIEW":
            return _block(ticket, "SUPERVISOR_DECISION_REQUIRED")
        if ticket.get("verifier_status") != "PASS":
            return _block(ticket, "SUPERVISOR_DECISION_REQUIRED")
        ticket["status"] = "CLOSED"
        ticket["supervisor_decision"] = "APPROVE"
        return _ok(ticket)

    if action == "APPLY_DECISION":
        okd, why = validate_decision(decision, ticket["ticket_id"])
        if not okd:
            return _block(ticket, why or "SUPERVISOR_DECISION_REQUIRED")
        kind = decision["decision"]
        ticket["supervisor_decision"] = kind
        if kind == "APPROVE":
            if ticket.get("status") != "SUPERVISOR_REVIEW" or ticket.get("verifier_status") != "PASS":
                return _block(ticket, "SUPERVISOR_DECISION_REQUIRED")
            ticket["status"] = "CLOSED"
        elif kind == "REJECT":
            ticket["status"] = "REJECTED"
        elif kind == "STOP":
            ticket["status"] = "CANCELLED"
        elif kind == "INVESTIGATE":
            ticket["status"] = "AUDITING"
        elif kind in {"APPROVE_RETRY", "APPROVE_NEW_BUDGET"}:
            blocked = apply_budget_change(ticket, decision.get("approved_budget_change") or DEFAULT_BUDGET)
            if blocked:
                return blocked
            ticket["status"] = "AUDITING"
        elif kind == "APPROVE_SCOPE_EXPANSION":
            extra = decision.get("files_allowed_add") or []
            ticket["files_allowed"] = list(ticket.get("files_allowed") or []) + list(extra)
            ticket["status"] = "AUDITING"
        return _ok(ticket)

    if action == "OPEN_TICKET_FOR_FAILURE":
        digest = signature_hash(event.get("failure") or {})
        owner = failure_index.get(digest)
        if owner and owner != ticket["ticket_id"]:
            return _block(ticket, "DUPLICATE_FAILURE_TICKET", owner_ticket=owner)
        failure_index[digest] = ticket["ticket_id"]
        return _ok(ticket, failure_index=failure_index)

    return _block(ticket, "SAFETY_BOUNDARY_REACHED", unknown_action=action)
