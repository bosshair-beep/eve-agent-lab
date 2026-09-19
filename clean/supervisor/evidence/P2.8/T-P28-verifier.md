# T-P28 Verifier — WS handshake forensic (CLEAN, read-only)

VERIFIER_STATUS=INDEPENDENT_FORENSIC  
RUNTIME_TOUCHED=NO  
CONNECTED_TO_18010_OR_8000=NO  
AUDITOR_FILE_AT_WRITE=ABSENT (`/opt/xiaozhi-clean/agent-lab/evidence/P2.8/T-P28-auditor.md` not present)

This report was reconstructed **before** any P2.8 auditor document. Auditor skim was attempted at the end; file still missing. Disagreements = none to list.

Legend: **FACT** / **STRONG_INFERENCE** / **HYPOTHESIS** / **UNKNOWN**.

---

## 0. Independent P2.7 inventory (listed before any P2.8 auditor read)

### agent-lab (name / content hit on `P2.7`)

| Path | Role |
|---|---|
| `/opt/xiaozhi-clean/agent-lab/tests/p27_live_once.py` | **Client source** (CRLF, 11394 B, SHA-256 `5fe5ff794850ab0b1cd6dc5c7e875d31299a861b29cb2c0e9fc9e77f7e435f90`) |
| `/opt/xiaozhi-clean/agent-lab/evidence/P2.7/live-capture.json` | Host wrapper result |
| `/opt/xiaozhi-clean/agent-lab/evidence/P2.7/preflight.json` | Preflight |
| `/opt/xiaozhi-clean/agent-lab/evidence/P2.7/postflight.json` | Postflight |
| `/opt/xiaozhi-clean/agent-lab/evidence/P2.7/STOP.json` | Stop (no retry) |
| `/opt/xiaozhi-clean/agent-lab/evidence/P2.7/docker-logs-window.txt` | 0 bytes (`docker logs --since 3m` at t1) |
| `/opt/xiaozhi-clean/agent-lab/evidence/P2.7/docker-logs-10m.txt` | 0 bytes |
| `/opt/xiaozhi-clean/agent-lab/evidence/P2.7/docker-logs-tail40.txt` | Historical **19:20–19:24 +0700** physical session only |
| `/opt/xiaozhi-clean/agent-lab/reports/P2.7-live-observation.md` | Phase report (no root-cause claim; recommends T-P2.8) |
| `/opt/xiaozhi-clean/agent-lab/supervisor/reports/P2.7-live-observation.md` | Copy |
| `/opt/xiaozhi-clean/agent-lab/supervisor/evidence/P2.7-auditor.md` | P2.7 auditor (no 1000-cause claim) |
| `/opt/xiaozhi-clean/agent-lab/supervisor/evidence/P2.7-verifier.md` | P2.7 verifier (no 1000-cause claim) |
| `/opt/xiaozhi-clean/agent-lab/supervisor/outbox/P2.7-review.json` | Review request |
| `/opt/xiaozhi-clean/agent-lab/supervisor/tickets/T-P2.7-001.json` | Ticket |
| `/opt/xiaozhi-clean/agent-lab/STATE.json` | Mentions P2.7 |
| `/opt/xiaozhi-clean/agent-lab/supervisor/CURRENT.json` | Mentions P2.7 |

### /tmp P2.7 scripts (host)

| Path | SHA-256 |
|---|---|
| `/tmp/p27-preflight.py` | `e5740409382032741a01daf1af463368cbb04d9c3145b56304e2293e5dbd9836` |
| `/tmp/p27-preflight.sh` | `90f912b28a9e821471fc48089de1b82ff21c8d4a52155dc0170da3c2f364211b` |
| `/tmp/p27-fetch-logs.py` | `cb705592c3cc07a04ebae1edeaad6682b04716154f253b90dbebf4d97d1e2811` |
| `/tmp/p27-fetch-tail.py` | `f14e85084cac137a12520943de32be483c4473c91526b569729ddd377db653af` |
| `/tmp/p27-postflight.py` | `973d7167b72bc369db7dd2703b1132e4c5598709b6698926e689e2dcebdbd1f3` |
| `/tmp/p27-ws-result.json` | `ae73e8c1646e9a7518d3870d584504d2962dd1423d47eac379189962cebad859` |

Related (not P2.7-named): `/opt/xiaozhi-clean/data/ws_hello.py` (older synthetic detect client; Device-Id `11:22:33:44:55:66`, Bearer `test-token`).

P2.8 dir at write: `hdr_case.py`, `ws_connect_probe.py` only. **Not executed** (no sockets).

---

## 1. Challenge: claimed close-1000 cause

### What was actually claimed

**FACT.** P2.7 report / ticket / P2.7 auditor / P2.7 verifier do **not** assert a root cause. They only record `ConnectionClosedOK: received 1000 (OK); then sent 1000 (OK)` at `t0=t1=2026-09-19T17:08:07+00:00` and defer diagnosis to T-P2.8.

**FACT.** Client exception text is peer-first: `received 1000 (OK); then sent 1000 (OK)` (`/tmp/p27-ws-result.json`, `live-capture.json`). That is **not** the library wording for local-first close (`sent 1000; then received 1000`).

### Falsifications of plausible causes

| Claim | Verdict | Why |
|---|---|---|
| helloHandle timed out | **FALSIFY** | `helloHandle.py` has **no hello-wait timeout**. Only wakeup-TTS wait (3s) after wakeup words. P2.7 finished in the same UTC second. |
| `connection.py` idle / no-voice timeout | **FALSIFY** | `timeout_seconds = close_connection_no_voice_time + 60` = 180s (`connection.py` ~184–186, config `close_connection_no_voice_time: 120`). Would also INFO-log. |
| Client teardown `await ws.close()` (`p27_live_once.py:137`) | **FALSIFY as first closer** | That line runs only after hello reply + detect loop. `run_once` never returned (`ws: {}`). Exception is **received** 1000 first. |
| Wrong URL / HTTP 404 / HTTP 200 on `:8000` | **FALSIFY** | Failed HTTP upgrade is `InvalidStatus`, not `ConnectionClosedOK`. `websockets.serve` has **no path filter**. Host map `127.0.0.1:18010→8000`; in-container `/proc/net/tcp` `0.0.0.0:8000` LISTEN (`1F40`). |
| Bind / `need_bind` discarded hello | **FALSIFY as 1000 cause** | `_route_message` waits 1s then **discards** (`connection.py` 348–361). Does **not** close. Would have already logged `{ip} conn - Headers`. |
| `connection.py:close()` default 1000 after a live session | **FALSIFY as P2.7 path** | `close()` calls `ws.close()` with no code → library **1000** (`websockets.asyncio.connection.Connection.close` default `code=1000`). That path is after `handle_connection` and **logs** (`客户端断开连接` / resource-release). P2.7 window logs are empty. |

### Remaining causes consistent with empty INFO + peer 1000 in <1s

**FACT.** `websocket_server._handle_connection` has two early returns that `await websocket.close()` with **no code** (library default **1000**) and **no INFO log**:

1. Missing `device-id` header **and** no `device-id` query param → send `"端口正常，如需测试连接，请启动digital-human测试"` then close (`websocket_server.py` 96–98).
2. `AuthenticationError` → send `"认证失败"` then close (`websocket_server.py` 113–115).

`_handle_auth` runs only if `self.auth_enable` (`websocket_server.py` 207–227). Local `config.yaml` has `server.auth.enabled: false`. Live config is **API-merged**: `get_config_from_api_async` sets `config_data["server"]["auth"] = {"enabled": auth_enabled}` from **Java** (`config_loader.py` 70–80). Changelog default inserts `server.auth.enabled='true'` (`202512131453.sql`). Physical 19:19 session carried a real `Authorization: Bearer <hmac>.<unix_ts>` header (token not repeated here). Java mints that token only when `server.auth.enabled` is true (`DeviceServiceImpl` ~220–226). `AuthManager.verify_token` is HMAC of `{client_id}|{device_id}|{ts}` (`core/auth.py` 51–71); a **new** Client-Id cannot verify a token minted for the physical Client-Id.

**STRONG_INFERENCE.** P2.7 close-1000 is the **pre-`ConnectionHandler` server close**, most likely **auth fail** (`认证失败` + close 1000), because:

- in-container `websockets==14.2`; `connect(..., additional_headers=)` is the real parameter (not ignored);
- client **did** set `Device-Id: 30:ed:a0:2a:1b:d8` (`p27_live_once.py` 81–90);
- client **minted a fresh** `Client-Id = uuid.uuid4()` (`p27_live_once.py` 80) while scraping the **physical** bearer from 72h logs;
- physical Client-Id was `17a2b339-f6ca-46b0-b281-decbbdfe774d`;
- token timestamp `1789820341` ≈ 19:19 +0700; default expiry is 30 days — **not** an expiry fail at 17:08Z;
- empty docker INFO is the fingerprint of those two early-return paths, not `handle_connection`.

**HYPOTHESIS (weaker).** Device-Id header never arrived → `端口正常` path. Contradicted unless `additional_headers` failed silently (no evidence in 14.2).

**UNKNOWN (requires a new authorized session or a forbidden connect).** Which text frame, if any, the client received (`认证失败` vs `端口正常` vs none). `live-capture.json` has `ws: {}` so frames were not saved. Live `sys_params.server.auth.enabled` was **not** read (no HTTP to Clean, no DB query).

---

## 2. Challenge: whether P2.7 reached a Python handler

Split the word “handler”. Do not treat WS upgrade as `helloHandle` / `listenMessageHandler`.

| Layer | Verdict | Evidence |
|---|---|---|
| Something on container `:8000` accepted WS then sent close 1000 | **FACT** | `ConnectionClosedOK received 1000`; not refused / not HTTP status. `:8000` LISTEN in `/proc/net/tcp`. |
| `WebSocketServer._handle_connection` | **STRONG_INFERENCE YES** | That is the only WS app on 8000 (`app.py` → `WebSocketServer.start` → `websockets.serve(self._handle_connection, host, port)`). |
| `ConnectionHandler.handle_connection` | **STRONG_INFERENCE NO** | First statements INFO-log `{ip} conn - Headers: ...` and sample-rate (`connection.py` 218–247). P2.7 `--since 3m` and `--since 10m` are **0 bytes**. Last INFO remains 19:24:23 +0700 physical teardown. |
| `textMessageProcessor` / `helloHandle` / `ListenTextMessageHandler` | **FACT NO** | Those INFO-log `收到hello消息` / `收到listen消息` (`textMessageProcessor.py` 28). Absent in P2.7 window. Client sends detect **only after** hello+`session_id` (`p27_live_once.py` 101–106); exception was earlier. |
| `startToChat` / LLM / `get_lunar` | **FACT NO** | No `大模型收到用户消息`. |

**UNKNOWN.** Whether `_handle_auth` ran (depends on live `auth_enable`). Cannot be proven without a connect or dumping the process config.

---

## 3. Challenge: protocol requirements for text vs audio

**FACT — two listen states, two media paths** (`core/handle/textHandler/listenMessageHandler.py`):

- **Audio:** `state=="start"` → `reset_audio_states()` only. Frames are **binary opus** (decoded in `_route_message`). `state=="stop"` ends the utterance into ASR.
- **Text (direct):** `state=="detect"` **and** `"text" in msg` → `startToChat(conn, original_text)` (or wakeup / `[device_call]` branches). **No audio frames required.**

**FACT — hello is not a media requirement for detect, but it is a gate in this client and in bind routing:**

- `handleHelloMessage` applies optional `audio_params` / `features`; always `send(welcome_msg)` (`helloHandle.py` 42–63). No audio required to answer hello.
- `_route_message` will **not** deliver hello/listen to processors until `bind_completed_event` (1s) and `need_bind` is false (`connection.py` 348–361). Discard ≠ close.
- Server sample-rate default from `xiaozhi.audio_params.sample_rate` is **24000** in `config.yaml`; physical + P2.7 hello both advertise **16000**. That override is hello-time, not a close-1000 condition.

**FACT — physical device used BOTH paths in one session:**

- 19:19:16 hello (features + text_font + opus 16k).
- 19:19:17 `listen/detect` text `"Sophia"` (direct-text, no audio).
- 19:19:17+ `listen/start` `mode=auto` (audio path).

**FALSIFY.** “Direct text requires a prior `listen/start` or opus frames.” Code and 19:19:17 contradict that.

**FALSIFY.** “P2.7 could deliver detect without a hello reply.” This **client** waits for hello+`session_id` before detect. Server detect handler does not require `session_id`, but P2.7 never reached it.

---

## 4. Challenge: direct-text assumption

**The assumption (detect+text → LLM, skip ASR) is TRUE in code and was live-proven at 19:19:17.**

**The assumption that P2.7 exercised that path is FALSE.**

- Detect send is behind hello reply (`p27_live_once.py` 101–106).
- `ws: {}`, `session_id` null, `docker_exec_rc=1`.
- STOP.json: `user_turns=0`, `detect text not confirmed sent`.
- No `收到listen消息` for the Vietnamese utterance.

**Do not treat P2.5/P2.7-adjacent 19:19–19:24 logs as this test’s turn** (already stated in the P2.7 report; **agree**).

---

## 5. Challenge: physical vs synthetic headers / hello

### Physical (19:19:16 +0700) — FACT from `docker logs` header dump + `收到hello消息`

Headers (secrets redacted): `host=clean.eve.ai.vn`, `x-real-ip` / `x-forwarded-for` / `x-forwarded-proto=https`, `upgrade=websocket`, `authorization=Bearer <hmac>.1789820341`, `client-id=17a2b339-f6ca-46b0-b281-decbbdfe774d`, `device-id=30:ed:a0:2a:1b:d8`, `protocol-version=1`.

Hello JSON:

```json
{"type":"hello","version":1,"features":{"mcp":true,"glyph_push":true},"text_font":{"bundle":"noto-v1","charset":"common","size":16,"bpp":4},"transport":"websocket","audio_params":{"format":"opus","sample_rate":16000,"channels":1,"frame_duration":60}}
```

Reached `handle_connection` (headers INFO) and `textMessageProcessor` (hello INFO). Bind/private-config succeeded in 0.069s.

### Synthetic P2.7 — FACT from byte-for-byte client source

- Transport: **in-container** `ws://127.0.0.1:8000/xiaozhi/v1/` (not `clean.eve.ai.vn`, not host `:18010`).
- File is **CRLF** (311 `\r`). Harmless to CPython.
- `USER_TEXT` UTF-8 = `Hôm nay là ngày bao nhiêu âm lịch?` (xxd: `48 c3 b4 6d ...`).
- Headers: `Authorization: Bearer <scraped>`, `Protocol-Version: 1`, `Device-Id: 30:ed:a0:2a:1b:d8`, `Client-Id: <new uuid4 every run>`.
- Hello: `type/version/transport/audio_params` only — **no** `features`, **no** `text_font`.
- Library default `User-Agent: Python/3.10 websockets/14.2`, `ping_interval=20`.
- Compose / config path string `.../xiaozhi/v1/` matches; server does not route on path.

### What the deltas can and cannot cause

| Delta | Can cause peer 1000 before handler logs? |
|---|---|
| Fresh Client-Id + physical bearer | **YES if auth_enable** (`verify_token` binds client_id) |
| Missing `features` / `text_font` | **NO** — optional in `handleHelloMessage`; would be after header INFO |
| Missing proxy `x-real-ip` / `host` | **NO** — unused in device-id/auth checks |
| In-container `:8000` vs public wss | **NO** — same `websockets.serve` |
| Trailing slash on `/xiaozhi/v1/` | **NO** — no path ACL |

**FALSIFY.** “Synthetic hello `audio_params` were illegal / mismatched so the server closed 1000.” Same opus 16k/1/60 as physical. helloHandle does not close on audio_params.

**FALSIFY.** “Physical and synthetic headers were equivalent except Device-Id reuse.” Client-Id and ingress headers differ. Client-Id is the auth-relevant one.

---

## 6. Challenge: any proposed P2.9

**FACT.** No P2.9 ticket in `BACKLOG.yaml`, `CURRENT.json`, `STATE.json`, or P2.7 report. P2.7 recommended **T-P2.8 only**. Auditor file absent — no P2.9 to agree with.

**FALSIFY (pre-empt).** Minting P2.9 as “retry the same in-container client” would:

- violate P2.7 `MAX_TEST_RETRIES=0` / `do_not_retry`;
- reproduce the same 1000 if Client-Id is still a random UUID against a scraped physical token;
- not be a handshake forensic.

A later **authorized** live session (not this verifier) would need a token minted for **that** Client-Id, or the physical Client-Id+token pair, or a proven `auth_enable=false`. **Not tested here.**

---

## Supporting inspections (read-only)

### docker-compose ports — FACT

`/opt/xiaozhi-clean/docker-compose.yml` `xz-clean-server`:

- `127.0.0.1:18010:8000`
- `127.0.0.1:18013:8003`

`docker inspect` HostConfig.PortBindings matches. Host `ss`: `127.0.0.1:18010` `docker-proxy`. No connect issued.

### config.yaml websocket path — FACT

`server.websocket: ws://你的ip或者域名:端口号/xiaozhi/v1/` is the **OTA-advertised** URL, not a listen ACL. `app.py` logs `ws://{ip}:{port}/xiaozhi/v1/` but `websockets.serve` binds `ip:port` only. `log_level: INFO`. Overlay `data/.config.yaml` sets `server.ip/port/http_port`, `manager-api.url`, `prompt_template` — **does not** override `auth.enabled`.

### websockets library default close — FACT

Container `websockets==14.2`. `Connection.close(self, code: int = 1000, reason: str = "")`. Every server `await websocket.close()` / `await ws.close()` without args is **1000**.

### helloHandle timeout — FACT

None. Bind wait is 1s discard in `connection.py`, not helloHandle.

### listen detect vs start — FACT

See §3. `startToChat` is the detect/text sink (`receiveAudioHandle.py` 43+). `need_bind` short-circuits to bind prompt, does not close 1000 by itself.

---

## Auditor disagreements

`T-P28-auditor.md` **absent** after independent reconstruction. P2.8 evidence only contains `hdr_case.py` / `ws_connect_probe.py` (unread-as-truth; not run).

If an auditor later claims:

- helloHandle timeout as the 1000 cause → **disagree** (§1);
- P2.7 reached `listenMessageHandler` / `startToChat` → **disagree** (§2);
- detect+text is not a real protocol → **disagree** (§3–4);
- headers/hello were physical-equivalent → **disagree** (§5);
- P2.9 live retry of `p27_live_once.py` as-is → **disagree** (§6).

---

## Verdict line

P2.7 obtained a WebSocket 101 then a **server-first close 1000** in the same second, with **no new INFO**. That is the `_handle_connection` early-return fingerprint, **not** hello timeout, idle timeout, bind discard, path mismatch, or client `:137` teardown. Best remaining explanation is **auth reject** from a **new Client-Id** plus a **physical bearer**; live `auth.enabled` from Java is **UNKNOWN** without a forbidden query. Detect/text never left the client. Direct-text remains a valid protocol. No P2.9.
