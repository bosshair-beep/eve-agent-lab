# Conversation/Core V2 architecture

**WORK_ID:** `EVE_CONVERSATION_CORE_V2_BUILD`  
**Status:** design encoded in this isolated package. Production eve.ai is untouched.

## Why V2 exists

Current Eve is the stable behavioral baseline. Historical defects this architecture
makes explicit (without re-interpreting evidence):

1. **Wake/Câm** — wake PCM leaked into a listen window because `_flush_pending`
   was blocked, `_post_flush_live` stayed false, post-listen PCM was appended
   and never `_send_pcm`. Proven fix chain (mission §1.A) is the V2 PCM invariant.
2. **Identity writers** — system prompt / wake display / greetings could disagree
   (Milo / Ivy / Linh). V2 has one IdentityOwner.
3. **Location fallbacks** — `未知位置` / `广州` must not become authoritative.
4. **Raw ASR** — immutable. Known mishears are not “fixed” by V2 (open track
   SHORT_NOISY_ASR / MiniLM_RUE).

Live patched source was **not hashed** in this environment (production READ-ONLY;
this repo is control-plane only). Behavioral contracts are taken from the mission
text and preserved as comments + tests. Tomorrow’s snapshot must record real
file hashes before integration.

## Canonical pipeline

```
DEVICE AUDIO
  → transport / Opus          (adapter; not redesigned)
  → PCM
  → wake/listen state         WAKE_OWNER + LISTEN_OWNER
  → VAD                       TURN_EVENT_OWNER timeline
  → ASR session               ASR_SESSION_OWNER
  → raw_asr                   IMMUTABLE
  → UtteranceEnvelope
  → SuspiciousUtteranceResolverHook   NO-OP
  → resolved_utterance        == raw_asr
  → Intent
  → Tool                      TOOL_CONTEXT_OWNER
  → LLM
  → TTS                       TTS_PLAYBACK_OWNER
  → Playback
  → turn completion           TURN_EVENT_OWNER
```

## Owners (one authoritative writer each)

See `docs/ownership-matrix.md`. Engine (`ConversationEngineV2`) orchestrates;
it does not let Qwen WS readiness silently own `conversation_open`.

## Proven wake/Câm mapping

| Historical | V2 owner / method |
|---|---|
| `wake` / `wake_pcm_blocked=true` | `WakeOwner.start_wake()` |
| `session.updated` | ASR session events; does **not** open conversation |
| `_flush_pending` blocked | `PcmDeliveryOwner` pending is explicit; flush only if `post_flush_live` |
| `_post_flush_live=false` | `PcmDeliveryOwner.arm_live_forward_after_wake_isolation(conversation_open, asr_ready)` |
| post-listen PCM appended, no `_send_pcm` | forbidden; frame is SENT, PENDING (awaiting READY), or DISCARDED with reason |
| `apply_listen_start_boundary(opened)` | `ListenOwner.apply_listen_start_boundary()` + discard stale/wake buffers |
| `arm_live_forward_after_wake_isolation` | `PcmDeliveryOwner.arm_live_forward_after_wake_isolation` |

Invariant: **wake PCM never becomes user conversational PCM.**

## Session correlation

Every timeline event carries `session_id`, `turn_id` (once a turn is open),
`asr_epoch`, `qwen_session_gen`. PCM contents are not logged.

## Failure / fallback

If V2 fails **before user-visible output** (`TTS_FIRST_AUDIO` / device audio)
and `fallback_to_v1=true`, one V1 fallback is allowed. After user-visible
audio, fallback is **unsafe** and refused. No fallback loops.

## Out of scope (still first-class types)

- MiniLM / RUE (hook only)
- ASR parameter changes (frozen `ASR_BASELINE`)
- TTS provider redesign (state + telemetry only)
- Clean / firmware / production config
