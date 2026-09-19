# Clean Vietnamese migration — agent lab

Reusable Cursor multi-agent workspace for forensic investigation, later implementation, independent verification, and closed-loop Vietnamese migration.

**This directory is project-support only.** It is not the live runtime.

## Live runtime (do not confuse with this lab)

| Item | Value |
|------|--------|
| Clean root | `/opt/xiaozhi-clean` |
| Python container | `xz-clean-server` |
| Live prompt | `/opt/xiaozhi-clean/overlays/lucy-lang/agent-base-prompt.txt` |
| In-container prompt | `/opt/xiaozhi-esp32-server/agent-base-prompt.txt` (`:ro` bind) |
| `/opt/xiaozhi-clean` git | **not** a git repo |
| Upstream source git | `/opt/xiaozhi-clean/source` (detached `6afc54a`) — **not** assumed live |

## Agents

| Agent | Cursor file | Mode |
|-------|-------------|------|
| MANAGER | this chat / always-on rules | orchestrates |
| AUDITOR | `.cursor/agents/auditor.md` | read-only forensic |
| IMPLEMENTER | `.cursor/agents/implementer.md` | **disabled this bootstrap phase** |
| VERIFIER | `.cursor/agents/verifier.md` | read-only adversarial |

Invoke later with `/auditor`, `/verifier`, `/implementer` (implementer must refuse unless Manager enables).

Custom subagents apply when this folder is the Cursor project root. Task-tool enum may require a Cursor reload.

## Ticket lifecycle

`NEW → INVESTIGATING → ROOT_CAUSE_FOUND → READY_TO_PATCH → PATCHED → VERIFYING → FAILED|PASSED → CLOSED`

`CLOSED` requires Verifier PASS with evidence. Implementer cannot self-close.

## Safety

Do not modify Clean application/runtime, compose, DB, Eve, firmware, or restart containers from this lab unless a human-approved ticket says so.
