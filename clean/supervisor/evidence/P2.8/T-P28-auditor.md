# T-P28 Auditor — P2.8_WS_HANDSHAKE_FORENSIC (READ ONLY)

**Ticket:** CLEAN_VI_MIGRATION / P2.8_WS_HANDSHAKE_FORENSIC  
**Auditor:** READ ONLY. No live WS/HTTP to Clean runtime (no curl 18010/8000/xiaozhi). No source/runtime/prompt/compose/config/DB writes. No restart. No second live session.  
**Wrote only:** `/opt/xiaozhi-clean/agent-lab/evidence/P2.8/` and `/opt/xiaozhi-clean/agent-lab/reports/P2.8-ws-handshake-forensic.md`  
**Live:** `xz-clean-server` Status=running StartedAt=`2026-09-19T12:16:29.257407561Z` RestartCount=0 Image=`ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:server_latest`  
**Did not run:** `supervisor_sync.py publish` (see §8). `status` only.

Claim labels: **OBSERVED** / **SOURCE_PROVEN** / **INFERRED** / **UNKNOWN**.

---

## 1) Exact P2.7 synthetic in-container client (reconstructed)

**Sources (OBSERVED):**  
`/opt/xiaozhi-clean/agent-lab/tests/p27_live_once.py` SHA-256 `5fe5ff794850ab0b1cd6dc5c7e875d31299a861b29cb2c0e9fc9e77f7e435f90`  
`/opt/xiaozhi-clean/agent-lab/evidence/P2.7/live-capture.json`  
`/tmp/p27-ws-result.json`  
Host wrapper copied that script into the container as `/tmp/p27_live_once.py` and ran `P27_MODE=client`.

| Field | Reconstructed value | Class |
|---|---|---|
| Transport / URI | `ws://127.0.0.1:8000/xiaozhi/v1/` (env `P27_URL`, inside `xz-clean-server`) | OBSERVED |
| Library | `websockets` **14.2**, `websockets.connect(..., additional_headers=..., open_timeout=20)` | SOURCE_PROVEN |
| Device-Id | `30:ed:a0:2a:1b:d8` (header `Device-Id`) | OBSERVED |
| Client-Id | `str(uuid.uuid4())` generated at `run_once()`; **not written** on error path | UNKNOWN (value). SOURCE_PROVEN that it was a **new** UUID, not the 19:19 id |
| Authorization | `Bearer <token>` where token = last `'authorization': 'Bearer …'` in `docker logs --since 72h` | SOURCE_PROVEN extract. INFERRED same token as 19:19 (no later `conn - Headers` line exists) |
| Protocol-Version | `1` | SOURCE_PROVEN |
| Subprotocol | **not set** (`subprotocols=` omitted) | SOURCE_PROVEN absent |
| Origin | **not set** | SOURCE_PROVEN absent |
| User-Agent | default `Python/3.10.20 websockets/14.2` (`USER_AGENT` in `websockets/http11.py`; compose has no `WEBSOCKETS_USER_AGENT`) | INFERRED (library default + env) |
| Other headers | none besides the four above + library handshake (`Upgrade`, `Connection`, `Sec-WebSocket-Key`, `Sec-WebSocket-Version`) | SOURCE_PROVEN / INFERRED |
| Hello payload | `{"type":"hello","version":1,"transport":"websocket","audio_params":{"format":"opus","sample_rate":16000,"channels":1,"frame_duration":60}}` — **no** `features`, **no** `text_font`, **no** `session_id` | SOURCE_PROVEN |
| Timing | `t0=t1=2026-09-19T17:08:07+00:00` (00:08:07 +0700). `open_timeout=20`. First `recv` timeout 25s **not reached**. | OBSERVED |
| After hello | wait until JSON `type==hello` with `session_id`, **then** send listen | SOURCE_PROVEN (never reached) |
| listen/start | **not sent** | SOURCE_PROVEN (code order) + OBSERVED (`ws: {}`) |
| How text was to be delivered | after hello-reply: `{"type":"listen","state":"detect","text":"Hôm nay là ngày bao nhiêu âm lịch?"}` | SOURCE_PROVEN intended. OBSERVED not confirmed delivered |
| Audio / ASR | none planned (no binary frames, no `listen/start`) | SOURCE_PROVEN |
| Post-turn wait | `MAX_WAIT_S=90`, 5s recv slices, break on `tts/stop` | SOURCE_PROVEN (never reached) |
| Client close | `await ws.close()` after TTS stop (default 1000) | SOURCE_PROVEN (never reached) |
| Actual close | `ConnectionClosedOK: received 1000 (OK); then sent 1000 (OK)` | OBSERVED |
| Captured WS messages | `ws: {}` / `ws_json: null` because exception path discards in-flight `ws_msgs` | OBSERVED |
| docker_exec_rc | 1 | OBSERVED |

**Do not invent:** exact P2.7 Client-Id, exact Bearer bytes in this file, whether hello bytes left the client, whether server text `认证失败` was received before the close frame.

---

## 2) Live `/xiaozhi/v1/` path: upgrade → hello wait → auth → device lookup → close(1000)

There is **no FastAPI/aiohttp route table** for `/xiaozhi/v1/`. `websockets.serve` binds `0.0.0.0:8000` and `_handle_connection` accepts **any path**. The `/xiaozhi/v1/` suffix is convention (OTA/nginx), not a server path filter. **SOURCE_PROVEN** `websocket_server.py:76-97`, `app.py:110`.

### 2.1 Early-close inventory (every path that can end the socket before a useful turn)

| # | FILE | LINE | FUNCTION | CONDITION | CLOSE_CODE | LOG_LEVEL | EXPECTED_LOG |
|---|---|---|---|---|---|---|---|
| E1 | `core/websocket_server.py` | 146-153 | `_http_response` | `Connection` header `.lower() != "upgrade"` | **N/A** (HTTP 200 `Server is running\n`, no WS) | none | none. Client would see HTTP status, not `ConnectionClosedOK` |
| E2 | `core/websocket_server.py` | 89-92 | `_handle_connection` | `websocket.request.path` empty | `ws.close()` default **1000** | ERROR | `无法获取请求路径` (`core.websocket_server`) |
| E3 | `core/websocket_server.py` | 95-97 | `_handle_connection` | no `device-id` header **and** no `device-id` query | send text `端口正常，如需测试连接，请启动digital-human测试` then `ws.close()` **1000** | **none** | **none** |
| E4 | `core/websocket_server.py` | 111-115 + 208-227 | `_handle_auth` | `auth_enable` and device not in whitelist and token missing/`Bearer` missing/`verify_token` false | send text `认证失败` then `ws.close()` **1000** | **none** | **none** |
| E5 | `core/websocket_server.py` | 128-137 | `_handle_connection` except/finally | exception inside `ConnectionHandler.handle_connection` or leftover open socket | `ws.close()` **1000** | ERROR if exception | `处理连接时出错: …` and/or `服务器端强制关闭连接时出错` |
| E6 | `core/connection.py` | 203-219 | `handle_connection` | always, if reached | none yet | INFO | `{ip} conn - Headers: {headers}` |
| E7 | `core/connection.py` | 256-267 | `handle_connection` | peer `ConnectionClosed` | already closed | INFO | `客户端断开连接` then finally `_save_and_close` |
| E8 | `core/connection.py` | 258-264 | `handle_connection` | `AuthenticationError` (second gate; WS auth already passed) | return → finally `close()` **1000** | ERROR | `Authentication failed: …` |
| E9 | `core/connection.py` | 265-267 | `handle_connection` | other exception | return → finally `close()` **1000** | ERROR | `Connection error: …` + traceback |
| E10 | `core/connection.py` | 1540-1630 + 328 | `close` / `_save_and_close` | any teardown after handler entered | `ws.close()` **1000** | INFO | `连接资源已释放` (and title-thread side effects) |
| E11 | `core/connection.py` | 1728-1735 | `_check_timeout` | no activity > `close_connection_no_voice_time` (120s) | `close()` **1000** | INFO | `连接超时，准备关闭` |
| E12 | `core/handle/sendAudioHandle.py` | 54-55 | send LAST | `close_after_chat` | `conn.close()` **1000** | (prior TTS INFO) | then E7/E10 |
| E13 | intent exact-match / `handle_exit_intent` | intentHandler / plugin | `退出`/`关闭` or tool goodbye | `close()` **1000** | INFO | `退出意图已处理` then E12 |

**Hello wait (SOURCE_PROVEN):** there is **no** server timer that closes if hello never arrives. After E6 the loop is `async for message in websocket` (`connection.py:256`). Missing hello just idles until E11 (120s). Client-side hello wait is 25s — **not** what happened (same-second close).

**Device lookup (SOURCE_PROVEN):** `_initialize_private_config_async` `connection.py:797-825` **does not close**.  
- Success: INFO `异步获取差异化配置成功` + `need_bind=False`.  
- `DeviceNotFoundException` / `DeviceBindException`: `need_bind=True`, **no close**, **no INFO** on not-found. Later `_route_message` discards.  
These paths **cannot** explain missing `conn - Headers` because they run **after** E6.

**Auth (SOURCE_PROVEN):** runtime `auth_enable` is **not** local `config.yaml` (`enabled: false`). `config_loader.py:61-80` overwrites `server.auth` from **manager-api** `get_server_config()`. Live Redis `server:config` → `server.auth.enabled = true` (**OBSERVED**). `allowed_devices` is stripped; whitelist empty. Token is HMAC-SHA256 of `client_id|device_id|timestamp` (`core/auth.py:52-68`, Java `DeviceServiceImpl.generateWebSocketToken`).

---

## 3) Field-by-field vs known-good physical 19:19 session

Physical **OBSERVED** from existing docker logs (not this test):  
`260919 19:19:16` `core.connection` Headers + hello. Device-Id `30:ed:a0:2a:1b:d8`, Client-Id `17a2b339-f6ca-46b0-b281-decbbdfe774d`, via nginx `clean.eve.ai.vn` → `127.0.0.1:18010`.

| Field | Physical 19:19 | P2.7 synthetic | Verdict |
|---|---|---|---|
| URI path | `/xiaozhi/v1/` (wss Host `clean.eve.ai.vn`) | `ws://127.0.0.1:8000/xiaozhi/v1/` | DIFFERENT (entry). Same Python port **inside** container |
| Host | `clean.eve.ai.vn` | (direct) typical `127.0.0.1:8000` | DIFFERENT |
| X-Real-IP / X-Forwarded-* | present (nginx) | absent | DIFFERENT |
| Upgrade / Connection | websocket / upgrade | library Upgrade | MATCH (role) |
| Authorization | Bearer HMAC token ts=`1789820341` (=19:19 +0700) | same extractor; last 72h Bearer | MATCH (INFERRED same bytes) |
| Device-Id | `30:ed:a0:2a:1b:d8` | `30:ed:a0:2a:1b:d8` | MATCH |
| Client-Id | `17a2b339-f6ca-46b0-b281-decbbdfe774d` | new `uuid4()` | **DIFFERENT** |
| Protocol-Version | `1` | `1` | MATCH |
| Sec-WebSocket-Protocol | absent | absent | MATCH |
| Origin | absent | absent | MATCH |
| User-Agent | absent in logged headers | `Python/3.10.20 websockets/14.2` | DIFFERENT (INFERRED) |
| Hello `type/version/transport` | hello / 1 / websocket | same | MATCH |
| Hello `audio_params` | opus 16000/1/60 | same | MATCH |
| Hello `features` | `mcp=true, glyph_push=true` | **omitted** | DIFFERENT (not reached) |
| Hello `text_font` | noto-v1 present | omitted | DIFFERENT (not reached) |
| After hello | listen detect `Sophia` then listen start + audio/MCP | planned listen detect Vietnamese text; **not sent** | DIFFERENT (execution) |
| Result | Headers + `收到hello消息` + private-config INFO | 1000 same second, no INFO | DIFFERENT |

Header name case is **not** a defect: container `websockets` 14.2 `dict(Headers)` lowercases keys; `Device-Id` → `device-id` (**SOURCE_PROVEN** probe `evidence/P2.8/hdr_case.py`).

---

## 4) Why no new INFO logs

Both sinks are dual-write INFO (`config/logger.py` stdout **and** `tmp/server.log`). Physical 19:19 appears in both. P2.7 window:

- `docker logs --since 3m` / `10m` = **empty** (OBSERVED `docker-logs-window.txt` / `docker-logs-10m.txt` size 0)
- `--tail 40` still ends `19:24:23 +0700` (prior physical teardown)
- `tmp/server.log` mtime `19:37` / last handshake-related line `19:24:23`; later lines are only `构建增强提示词成功` at 19:41 and 20:37 — **no** `conn - Headers` / `收到hello` / `客户端断开连接` at 00:08 Sep 20

Classification:

| Code | Meaning | Fit |
|---|---|---|
| **A handler-early** | WS accepted; closed in `WebSocketServer._handle_connection` **before** `ConnectionHandler.handle_connection` first INFO | **BEST FIT** |
| B before handler | upgrade rejected / never reached `_handle_connection` | weak: HTTP 200 would be `InvalidStatus`, not `received 1000` |
| C wrong process | logs in another container/pid | rejected: in-container `:8000` is this process; both log sinks empty of handshake |
| D client 1000 | client sent 1000 first | rejected: exception text is **received** 1000 then sent 1000 |
| E unknown | residual | only if E3 vs E4 text frame was never distinguished (client discarded it) |

**A** with path **E4** (auth fail, no log) is the only early-close that matches: runtime auth on + Client-Id mismatch + silent close 1000 + no INFO. E3 is the only other silent-1000 path; Device-Id **was** coded to be sent and Headers case-folds, so E3 is weaker.

---

## 5) Protocol fact — text inject

**Normal XiaoZhi does not treat raw WS text as a user utterance.**  
`_route_message` (`connection.py:365-367`): `str` → `handleTextMessage` → JSON + `type` ∈ {hello, abort, listen, iot, mcp, server, ping}. Non-JSON is ERROR `解析到错误的消息` and echo. Bytes → Opus/ASR.

**Supported text inject (SOURCE_PROVEN):** `listen` + `state=detect` + `text` (`listenMessageHandler.py:55-116`) → wakeup rewrite **or** `startToChat(original_text)` without audio. Physical 19:19 used this for `"Sophia"`.

**Voice path:** `listen/start` (+ mode) then binary frames → VAD/ASR. Not required if detect-text is used.

**P2.7 inject:** intended `listen/detect` + Vietnamese text — **supported**, not an unsupported raw-text inject. **It was never sent** (hello-reply wait, then 1000). So P2.7 failure is **handshake/auth**, not “wrong inject method”.

---

## 6) ONE root cause

**ROOT CAUSE:** P2.7 reused the physical device Bearer + Device-Id but generated a **new Client-Id**. Live `server.auth.enabled=true`. `AuthManager.verify_token` binds `client_id|device_id|ts`. HMAC fails → E4 `认证失败` + `close(1000)` with **no log** → no `conn - Headers` / no hello INFO.

| Piece | Class |
|---|---|
| Client closed `received 1000` same second; `ws: {}` | OBSERVED |
| No new INFO in docker logs or `server.log` | OBSERVED |
| Script generates `uuid4()` Client-Id; extracts last log Bearer | SOURCE_PROVEN |
| Redis `server:config` `auth.enabled=true`; yaml `enabled:false` is ignored when manager-api is set | OBSERVED + SOURCE_PROVEN |
| Token algorithm requires matching Client-Id | SOURCE_PROVEN |
| 19:19 Client-Id `17a2b339-…` ≠ P2.7 uuid | OBSERVED vs SOURCE_PROVEN |
| This session actually received the `认证失败` text frame | INFERRED (exception discarded `ws_msgs`) |
| Exact P2.7 Client-Id string | UNKNOWN |

Not chosen as root: missing Device-Id (E3), hello-timeout, device-not-found, listen/detect protocol, wrong container port, log-level, client-initiated 1000.

---

## 7) P2.9 design (DO NOT EXECUTE) — MAX_RETRIES=0

**Goal:** one authorized bound session that either (a) passes auth and yields hello INFO, or (b) captures the first text frame that E3/E4 send.

**MUST:**

1. MAX_RETRIES=**0**. One connect. No wording change, no second Client-Id, no nginx-vs-direct retry in the same ticket.
2. Reuse the **19:19 triad exactly**: Device-Id `30:ed:a0:2a:1b:d8`, Client-Id `17a2b339-f6ca-46b0-b281-decbbdfe774d`, Authorization Bearer from that session (ts `1789820341`). Do **not** `uuid4()` a new Client-Id.
3. Still in-container `ws://127.0.0.1:8000/xiaozhi/v1/` (same process). Do not add a second hop unless Supervisor later authorizes nginx.
4. Client must persist **every** recv (including non-JSON `认证失败` / digital-human) **before** close, even on exception. Today’s `ws: {}` on error is a measurement bug.
5. Hello may stay minimal (P2.7) for handshake isolation; add `features.mcp` only after hello-reply is proven, and only if the ticket still has budget (it will not — MAX_RETRIES=0 means pick **one** hello shape: recommend **minimal hello first** to isolate auth).
6. If hello-reply arrives: **one** `listen/detect` text (supported inject). Do not send raw text. Do not send audio unless the ticket explicitly expands.
7. Do not raise `log_level`, do not restart, do not patch runtime.
8. After `tts/stop` (if any): **do not close** if title-POST avoidance still matters (P2.5). If socket dies, expect title POST.
9. Stop after the single attempt regardless of outcome. Write `evidence/P2.9/` only.

**MUST NOT:** mint a new token via OTA HTTP (`/xiaozhi/ota/`) in P2.9 unless a later ticket authorizes Clean HTTP. Token expire default 30d from `1789820341` — still valid on 2026-09-20 if expire was default.

**Success criteria:** `conn - Headers` + `收到hello消息` in **new** docker/`server.log` lines after the attempt timestamp, **or** captured server text proving E3/E4.

---

## 8) GitHub bridge publish (existing scripts only)

**Script:** `/opt/xiaozhi-clean/agent-lab/bin/supervisor_sync.py`  
**Commands:** `status` | `publish` | `pull`  
**Allowlist:** `supervisor/engine/sync_policy.py` `PUBLISH_ROOTS` = `LOOP_POLICY.md`, `STATE.json`, `BACKLOG.yaml`, `SPEC.md`, `README.md`, `supervisor/`, `tests/loop/`, `bin/supervisor_sync.py`, `reports/P2.6`, `tickets/`.

**This ticket’s files are NOT allowlisted:**

- `reports/P2.8-ws-handshake-forensic.md` — only `reports/P2.6*` matches
- `evidence/P2.8/` — `evidence/` is not a root (`docker-logs` also excluded)

`supervisor/reports/` and `supervisor/evidence/` **would** copy if present.

**VPS state (OBSERVED):** `.github-bridge` **does not exist** (`BRIDGE_GIT=uninitialized`). No `origin`. P2.6: VPS GitHub SSH denied; `gh` not installed. `CURRENT.json` `github.status=WORKSTATION_GH_READY_VPS_AUTH_REQUIRED`, repo `bosshair-beep/eve-agent-lab`.

**Do not run** `python3 /opt/xiaozhi-clean/agent-lab/bin/supervisor_sync.py publish` from this auditor / from the VPS until a human adds `origin` **and** GitHub auth. `publish` would `git init` under `.github-bridge` (outside this ticket’s write paths), commit, then fail push (`GITHUB_HUMAN_ACTION_REQUIRED`).

Workstation path (existing): copy allowlisted files, `gh` push from the authenticated Windows host. Do not change git remotes/auth here.

---

## Safety

Runtime/source/prompt/compose/DB untouched. No WS/HTTP to 18010/8000/xiaozhi. Implementer remains disabled. `supervisor_sync.py publish` not executed.
