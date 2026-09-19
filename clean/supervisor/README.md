# Supervisor bridge (local control plane)

This directory is the Cursor-team ↔ external ChatGPT Supervisor control/reporting surface.

It is **not** the XiaoZhi application tree. Do not copy runtime, overlays, compose, DB, or secrets here.

## Layout

| Path | Meaning |
|------|---------|
| `CURRENT.json` | Tiny project status + kill switches |
| `schema/` | ticket / message / decision / current JSON Schema |
| `engine/` | Deterministic loop policy (budgets, signatures, gates) |
| `inbox/` | Instructions **for** the Cursor team |
| `outbox/` | Messages/reports **to** Supervisor |
| `decisions/` | Supervisor/human decisions only |
| `reports/` | Short checkpoint reports for Supervisor |
| `evidence/` | Hashes + excerpts published for review (not giant logs) |
| `tickets/` | Machine-readable ticket JSON instances |
| `failure_index.json` | Global `signature_hash → ticket_id` |

## Kill switches

`CURRENT.json`:

- `automation_enabled` MUST be `false` during P2.6
- `global_stop: true` stops all patch/retry immediately
- `implementer_enabled` MUST remain `false` until a later Supervisor-approved phase

Absence of a file in `decisions/` is **not** approval.

## Sync

Explicit command (no daemon, no cron):

```bash
python3 /opt/xiaozhi-clean/agent-lab/bin/supervisor_sync.py status
python3 /opt/xiaozhi-clean/agent-lab/bin/supervisor_sync.py publish
python3 /opt/xiaozhi-clean/agent-lab/bin/supervisor_sync.py pull
```

One git push attempt per `publish` invocation.
