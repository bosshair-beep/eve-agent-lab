# V2 state machines (text)

## 1. Wake / listen / PCM

```
                    on_hello
                       │
                       ▼
                  SESSION_IDLE
                       │
          ┌────────────┼────────────────┐
          │ on_wake                     │ on_asr_ready
          ▼                             ▼
   WAKE_ACTIVE                    ASR_READY
   wake_pcm_blocked=true          conversation_open=false
   PCM → DISCARD WAKE_ISOLATION   post_flush_live=false
          │                             │
          │ on_listen_start             │ on_listen_start
          └────────────┬────────────────┘
                       ▼
         apply_listen_start_boundary
         discard stale/wake buffers
         conversation_open=true
         wake_pcm_blocked=false
                       │
          ┌────────────┴────────────┐
          │ asr_ready               │ asr not ready
          ▼                         ▼
   post_flush_live=true      post_flush_live=false
   PCM → SENT (once)         PCM → PENDING (explicit)
                             on_asr_ready → flush SENT
                             reconnect → discard STALE_EPOCH
```

Câm anti-pattern (forbidden): append PCM to a buffer while `_post_flush_live=false`
with no disposition. V2 records SENT, PENDING, or DISCARDED only.

## 2. ASR session

```
epoch=0 gen=0 not-ready
   on_asr_connect_start → connecting
   on_asr_ready         → epoch/gen at least 1, ready
   on_asr_disconnect    → not-ready (epoch/gen unchanged)
   on_asr_reconnect     → epoch++, gen++, not-ready
   accept_final         → require epoch+gen match AND ready
                          else STALE (does not enter turn)
```

Conversation_open is **not** in this machine.

## 3. Turn

```
HELLO → (optional WAKE) → LISTEN_START → VAD_START → VAD_END
  → ASR_FINAL → RESOLVER_* → INTENT_* → TOOL_* → LLM_* → TTS_*
  → DEVICE_FIRST_AUDIO → TURN_END

cancel → TURN_CANCEL (pending PCM discarded)
idle   → IDLE_TIMEOUT → TURN_END
```

## 4. TTS playback

```
IDLE → GENERATING → QUEUED → SENDING → PLAYING → DRAINING → IDLE
         │            │         │         │
         └────────────┴─────────┴─────────┴──► INTERRUPTED → IDLE
```

Telemetry (distinct): provider first audio, queue enqueue, queue dequeue,
first binary send, last binary send, device playback state.

## 5. Fallback

```
V2 error
  if user_visible_started → REFUSE (unsafe)
  if fallback already used → REFUSE (loop)
  if fallback_to_v1        → FALLBACK_V1 once, before TTS_FIRST_AUDIO
```
