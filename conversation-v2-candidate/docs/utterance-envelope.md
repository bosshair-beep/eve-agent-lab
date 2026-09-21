# UtteranceEnvelope contract

Frozen dataclass `eve_conversation_v2.envelope.UtteranceEnvelope`.

| Field | V2 initial |
|---|---|
| `session_id` | from TURN_EVENT_OWNER |
| `turn_id` | from TURN_EVENT_OWNER |
| `raw_asr` | **IMMUTABLE** once captured |
| `resolved_utterance` | `= raw_asr` |
| `primary_language` | LanguageOwner |
| `learning_languages` | LanguageOwner |
| `learning_level` | LanguageOwner / None |
| `asr_language_hint` | `vi` (ASR_BASELINE; not collapsed with conversation_language) |
| `conversation_language` | LanguageOwner |
| `recent_history` | last LLM texts (bounded) |
| `audio_metadata.duration_ms` | derived from sent frames (mock) |
| `audio_metadata.silero_frames` | sent frame count |
| `audio_metadata.preroll_available` | false tonight |
| `audio_metadata.preroll_sent` | false tonight |
| `audio_metadata.qwen_window_ms` | 0 tonight |
| `asr_metadata.provider` | `qwen` |
| `asr_metadata.model` | `qwen-asr` |
| `asr_metadata.session_gen` | ASR_SESSION_OWNER |
| `asr_metadata.epoch` | ASR_SESSION_OWNER |
| `suspicion_flags` | empty (no MiniLM) |
| `resolver_metadata.enabled` | `flags.resolver_enabled` (default false) |
| `resolver_metadata.provider` | `noop` |
| `resolver_metadata.confidence` | `1.0` if enabled else `None` |
| `resolver_metadata.reason` | `NO_OP_PASSTHROUGH` |

`mutate_raw_asr` raises `RawAsrMutationError`.

Known raw ASR examples (must pass through unchanged):

- `mở nhạc đi` → `visa này`
- `bài babyshark` → `baby sack`
- `bài hát baby shark` → `bày hết bay đi sát`
