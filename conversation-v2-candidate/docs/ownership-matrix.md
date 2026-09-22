# Ownership matrix

One authoritative writer per state. Hidden cross-module mutation is a defect.

| State | Owner | Writers | Readers | Notes |
|---|---|---|---|---|
| `session_id`, `turn_id`, timeline, cancel/complete, `user_visible_started`, `fallback_used` | **TURN_EVENT_OWNER** | `TurnEventOwner` | engine, telemetry, tools | |
| `wake_active`, `wake_pcm_blocked` | **WAKE_OWNER** | `WakeOwner` | PCM ingest | listen boundary clears block **after** discard |
| `conversation_open`, listen boundary applied | **LISTEN_OWNER** | `ListenOwner` | PCM, ASR arm | `listen/start` is the only audio-open transition |
| `asr_epoch`, `qwen_session_gen`, ASR ready/connecting | **ASR_SESSION_OWNER** | `AsrSessionOwner` | envelope, PCM arm, stale-final gate | **must not** set `conversation_open` |
| `post_flush_live`, pending/sent/discarded PCM | **PCM_DELIVERY_OWNER** | `PcmDeliveryOwner` | engine | send-once **or** discard-with-reason; no dead append |
| `primary_language`, `learning_languages`, `conversation_language`, `asr_language_hint`, `tts_locale` | **LANGUAGE_OWNER** | `LanguageOwner` | envelope, tools | fields not collapsed; hint defaults to `vi` |
| `assistant_name` + all identity surfaces | **IDENTITY_OWNER** | `IdentityOwner` (ctor only) | wake, prompt, display, LLM, TTS | no `implicit_fallback` |
| `child_id`, `device_id`, location, timezone, session metadata for tools | **TOOL_CONTEXT_OWNER** | `ToolContextOwner.compose` | intent/tools | location comes from LocationOwner only |
| location value / `LOCATION_UNKNOWN` | **LOCATION_OWNER** (via ToolContext) | `LocationOwner` | tools | rejects `未知位置` / `广州` |
| TTS `IDLE…INTERRUPTED` + send/queue telemetry | **TTS_PLAYBACK_OWNER** | `TtsPlaybackOwner` | engine | does not redesign TTS provider |

## Qwen WS vs conversation

`asr_ready=true` never opens conversation. Arming `post_flush_live` requires
**both** `conversation_open` (ListenOwner) **and** `asr_ready` (AsrSessionOwner).

## Identity surfaces (must match)

`wake_greeting` · `system_prompt` · `display` · `llm_context` · `tts_facing`
