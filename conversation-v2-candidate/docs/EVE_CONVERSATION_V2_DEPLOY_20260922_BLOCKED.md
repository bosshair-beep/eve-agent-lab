# EVE Conversation V2 deploy — BLOCKED (2026-09-22)

**TASK:** `EVE_V2_PRODUCTION_INTEGRATION`  
**FINAL_STATUS:** `BLOCKED_NO_AUTHORITATIVE_PROD_ACCESS`  
**Production files changed:** NONE  
**Restarts:** NONE  
**DB / firmware:** NONE  
**Rollback executed:** NO (nothing deployed)

## Phase 0 evidence (this Cloud Agent)

| Item | Value |
|---|---|
| Agent hostname | `cursor` (Ubuntu 24.04 Cloud Agent VM) |
| UTC time | `2026-09-22T00:19:49Z` |
| Workspace | `/workspace` = `bosshair-beep/eve-agent-lab` |
| Branch | `cursor/conversation-v2-candidate-8431` @ `2638c01` |
| `/opt/eve` | **absent** |
| Docker / compose | **absent** |
| SSH `Host eve-vps` | **absent** |
| `14.225.211.8:22` | TCP open |
| SSH login | **Permission denied (publickey)** for ubuntu/root/eve/deploy/admin/xiaozhi |
| Forwarded agent key | present, **not accepted** by VPS |
| `eve-supervisor-readonly` MCP | discovery **error** (SSH args are one string; Host `eve-vps` unresolved) |

Public HTTP only (not a runtime login):

- `eve.ai.vn` → `14.225.211.8`, nginx/1.24.0 (Ubuntu), HTTP/2 200
- Static Eve SPA, Last-Modified `2026-09-18`
- `clean.eve.ai.vn` same IP, nginx
- Default vhost on raw IP is stock nginx welcome

Self-hosted workers visible but **this run is not placed on them**:

- `g:\Eve-VPS @ DESKTOP-GF9R1QV` (`3b823e3b-7cd6-5099-89c5-75dd2c987f2e`)
- `eve-pc`
- `g:\FW_Mai_OTA @ DESKTOP-GF9R1QV`

A Task launch with `workerId` still executed on a Cloud Agent (`usePrivateWorker=false`). Live `/opt/eve`, containers, bind mounts, and conversation source were **not** inspected.

## Phase 1 snapshot

**Not created.** Suggested path `/root/eve-backup/pre-conversation-v2-…` does not exist on production (this VM is not production). Snapshot verification **failed** because there is no authoritative tree to hash.

Per safety rule: **no integration after failed snapshot.**

## Phase 3 candidate tests (isolated, not production)

Run on this agent against `conversation-v2-candidate/` only:

- `TEST_COUNT=65`
- `TESTS_PASS=YES`

These do **not** authorize a production restart.

## Why STOP

Authoritative eve.ai production source/runtime was not reachable. Integrating into `eve-agent-lab` or snapshotting this Cloud Agent would violate “do not assume a repo copy is authoritative.”

## Required next action

Re-run this task **on** `g:\Eve-VPS @ DESKTOP-GF9R1QV` (or any machine with working `Host eve-vps` / authorized SSH to `14.225.211.8`), then:

1. Discover live process/container for `eve.ai.vn`
2. Create verified PRE-V2 snapshot on the VPS
3. Merge V2 while keeping the production wake-flush fix
4. Restart only the conversation service
5. Smoke + rollback report

Do not treat this document as a successful deploy.
