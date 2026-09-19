# CLEAN_VI_MIGRATION — Loop Policy (P2.6)

**Status:** MANDATORY for MANAGER, AUDITOR, IMPLEMENTER, and VERIFIER.  
**Scope:** Orchestration control plane only. This policy does not authorize Vietnamese migration or Clean runtime changes.  
**Machine enforcement:** `agent-lab/supervisor/engine/loop_engine.py`  
**Live gate (mandatory for Manager):** `agent-lab/supervisor/engine/gate.py` `apply_live()`  
**Ticket schema:** `agent-lab/supervisor/schema/ticket.schema.json`  
**Project kill switch:** `agent-lab/supervisor/CURRENT.json`

Manager MUST mutate tickets only through `apply_live()`. In-memory `apply_event()` is for unit tests. Supervisor decisions MUST be files under `supervisor/decisions/`. `CURRENT.json` on disk is the kill-switch source of truth for live operations.

Agents MAY use less budget than the ceilings. Agents MUST NOT increase ceilings themselves. Only HUMAN or SUPERVISOR may authorize a new budget via a decision file under `agent-lab/supervisor/decisions/`.

---

## 1. Hard defaults PER TICKET

These are HARD CEILINGS:

| Budget | Constant | Ceiling |
|--------|----------|---------|
| Patch attempts | `MAX_PATCH_ATTEMPTS` | **2** |
| Audit revisits | `MAX_AUDIT_REVISITS` | **2** |
| Verification runs | `MAX_VERIFICATION_RUNS` | **3** |
| Subagent invocations | `MAX_SUBAGENT_INVOCATIONS` | **8** |

Stored on each ticket as `max_*` and `*_used`. Counters are monotonic non-decreasing except when a valid Supervisor `APPROVE_NEW_BUDGET` / `APPROVE_RETRY` decision explicitly sets a new ceiling. An agent MUST NOT:

- rewrite `*_used` downward;
- raise `max_*` without a decision file;
- open a second ticket to reset counters for the same normalized failure signature.

---

## 2. Ticket state machine

Canonical lifecycle:

```
NEW
 → AUDITING
 → ROOT_CAUSE_FOUND
 → READY_TO_PATCH
 → IMPLEMENTING
 → VERIFYING
```

From `VERIFYING`:

- PASS → `SUPERVISOR_REVIEW` → `CLOSED` **only after Supervisor `APPROVE`**
- FAIL → retry eligibility evaluation
  - retry allowed → `AUDITING`
  - circuit breaker → `BLOCKED_SUPERVISOR`

Other states:

- `REJECTED` — Supervisor `REJECT`
- `CANCELLED` — Supervisor `STOP` or human cancel
- `BLOCKED_EXTERNAL` — waiting on external/human infra not in ticket scope
- `BLOCKED_SUPERVISOR` — circuit breaker or missing required Supervisor decision

Historical bootstrap aliases (`INVESTIGATING`, `PATCHED`, `PASSED`, `FAILED`) are **not** canonical for new work. Existing P1/P2 tickets keep their recorded status in `BACKLOG.yaml` / evidence; they are not rewritten.

### Role locks

| Actor | MUST NOT set |
|-------|----------------|
| IMPLEMENTER | `CLOSED`, `SUPERVISOR_REVIEW` as self-approval, `SUPERVISOR_APPROVED`, any Supervisor decision |
| VERIFIER | implementation files; MUST NOT patch to obtain PASS |
| MANAGER | MUST NOT skip `SUPERVISOR_REVIEW` after PASS; MUST NOT treat missing decision as approval |
| ANY AGENT | `automation_enabled=true`, `global_stop=false` after a human/Supervisor set `global_stop=true`, `implementer_enabled=true` during P2.6 |

`CLOSED` requires: Verifier PASS **and** Supervisor decision `APPROVE` on that ticket id.

---

## 3. Circuit breakers (immediate STOP)

If any condition fires:

- `TICKET_STATUS=BLOCKED_SUPERVISOR`
- **No additional implementation attempt is allowed**
- Remaining patch budget MUST NOT be spent

| Code | Meaning |
|------|---------|
| `SAME_FAILURE_SIGNATURE_TWICE` | Normalized failure signature hash seen twice on this ticket (or globally bound to another open ticket) |
| `NO_NEW_EVIDENCE` | Retry without new evidence artifact/hash |
| `NO_MEASURABLE_PROGRESS` | Retry without an allowed progress token |
| `ROOT_CAUSE_CHANGED` | New root-cause layer/assertion that is not a refinement of the recorded cause — requires Supervisor re-scope |
| `SCOPE_EXPANSION_REQUIRED` | Fix needs files/systems outside `files_allowed` |
| `DB_SCHEMA_CHANGE_REQUIRED` | |
| `PROVIDER_CHANGE_REQUIRED` | |
| `INFRA_CHANGE_REQUIRED` | |
| `CREDENTIAL_CHANGE_REQUIRED` | |
| `RUNTIME_RESTART_REQUIRED` | |
| `SAFETY_BOUNDARY_REACHED` | Attempt would touch forbidden surfaces (runtime, Eve, firmware, compose, etc.) |
| `BUDGET_EXHAUSTED` | Any `*_used` would exceed `max_*` |
| `VERIFIER_CANNOT_REPRODUCE` | |
| `AUDITOR_VERIFIER_UNRESOLVED_DISAGREEMENT` | After allowed audit revisits |

`IMPLEMENTING` is also refused when:

- `CURRENT.automation_enabled != true` → stop reason `AUTOMATION_DISABLED`
- `CURRENT.global_stop == true` → stop reason `GLOBAL_STOP`
- `CURRENT.implementer_enabled != true` → stop reason `IMPLEMENTER_DISABLED`

---

## 4. Failure signature (machine-readable)

Prose MUST NOT be part of the identity. Cosmetic wording changes MUST NOT create a new signature.

Required fields (normalized):

```json
{
  "layer": "WEATHER_CONTEXT",
  "test_case": "E_LOCAL_WEATHER",
  "assertion": "NO_UNEXPECTED_CJK",
  "observed": "zh_CN",
  "source": "context"
}
```

Normalization:

1. Keep only those five fields.
2. Convert each value to string; trim; collapse internal whitespace to a single space; lowercase.
3. Empty / missing → `""`.
4. Extra keys (`hypothesis`, `notes`, `summary`, agent names) are **ignored**.
5. Canonical JSON: UTF-8, sorted keys, no extra whitespace (`separators=(',', ':')`).
6. `signature_hash` = SHA-256 hex of that canonical JSON.

If the same `signature_hash` occurs twice:

- STOP immediately (`SAME_FAILURE_SIGNATURE_TWICE`)
- Do **not** spend remaining patch budget

Global index: `agent-lab/supervisor/failure_index.json` maps `signature_hash → ticket_id`. Opening a new ticket for an already-indexed unclosed signature is a circuit breaker, not a fresh budget.

---

## 5. Progress rule

Every retry after FAIL must include **at least one** of:

| Token | Mechanical requirement |
|-------|------------------------|
| `NEW_EVIDENCE` | `evidence_path` + `evidence_sha256` not previously recorded on the ticket |
| `NEW_ROOT_CAUSE_EVIDENCE` | same hash/path rule |
| `MEASURABLE_REDUCTION_IN_FAILURE` | `tests_failed_count` strictly less than prior `tests_failed` length |
| `VERIFIER_CONFIRMED_BEHAVIOR_CHANGE` | `verifier_confirmed=true` and actor VERIFIER or MANAGER |

A progress token **without** those fields is **not** progress.

Otherwise:

- `STOP_REASON=NO_MEASURABLE_PROGRESS`
- `TICKET_STATUS=BLOCKED_SUPERVISOR`

Non-progress (explicitly rejected):

- rephrasing the same hypothesis;
- repeating the same test without new evidence;
- changing unrelated files;
- retrying because “maybe it works now”;
- switching model/agent to repeat the same reasoning;
- cosmetic changes that do not affect the failed assertion.

---

## 6. Supervisor gate

Accepted decisions (files in `agent-lab/supervisor/decisions/` only):

`APPROVE` · `REJECT` · `INVESTIGATE` · `STOP` · `APPROVE_RETRY` · `APPROVE_SCOPE_EXPANSION` · `APPROVE_NEW_BUDGET`

A decision MUST contain: `ticket_id`, `decision`, `reason`, `timestamp`, `actor` (`HUMAN` or `SUPERVISOR`), and `approved_budget_change` when the decision alters ceilings.

Rules:

- Agents MUST NOT manufacture Supervisor decisions.
- Absence of a decision is **not** approval.
- PASS does not close a ticket; it only reaches `SUPERVISOR_REVIEW`.
- `APPROVE_RETRY` permits retry **only** within the explicit `approved_budget_change` (or remaining unused budget if the decision says so). It does not enable Implementer or automation.

---

## 7. Kill switches

File: `agent-lab/supervisor/CURRENT.json`

| Field | P2.6 value | Effect |
|-------|------------|--------|
| `automation_enabled` | **false** | No autonomous implementation loop may start |
| `global_stop` | false unless human/Supervisor sets true | If true, all patch/retry stops immediately |
| `implementer_enabled` | **false** | Implementer remains disabled |

Read-only reporting/audit may continue if it does not touch runtime.

No agent may set `global_stop=false` after a human/Supervisor set it true. No agent may set `automation_enabled=true` in P2.6.

---

## 8. Subagent accounting

Each Manager spawn of Auditor, Verifier, Implementer, or other Task/subagent counts as **one** `subagent_invocations_used` on the active ticket. Exceeding 8 → `BUDGET_EXHAUSTED` → `BLOCKED_SUPERVISOR`.

---

## 9. Publish / GitHub

Control/reporting repository (not the XiaoZhi source tree). Sync helper: `agent-lab/bin/supervisor_sync.py`. Never commit secrets, env files, private keys, or unrelated Clean runtime files.

---

## 10. P2.6 non-goals

Do not: modify Clean application/source/runtime; live prompts; overlays; compose; DB; containers; providers; Eve; firmware; COM4/COM6; firewall/DNS/nginx; enable IMPLEMENTER; begin Vietnamese migration.
