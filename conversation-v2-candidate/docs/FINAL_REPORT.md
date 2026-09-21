# FINAL REPORT — EVE_CONVERSATION_CORE_V2_BUILD

```
V2_BUILD_STATUS=PARTIAL
V2_WORK_ROOT=conversation-v2-candidate/
BASELINE_EVE_HASHES=UNAVAILABLE_IN_THIS_ENVIRONMENT
  (production eve.ai READ_ONLY; no Eve application tree in this repo; VPS not touched)

ARCHITECTURE_COMPLETE=YES
OWNERSHIP_MATRIX_COMPLETE=YES
STATE_MACHINE_COMPLETE=YES

SOURCE_IMPLEMENTED=YES
TESTS_PASS=YES
TEST_COUNT=65

WAKE_PCM_INVARIANT=PASS
PCM_DELIVERY_INVARIANT=PASS
ASR_SESSION_INVARIANT=PASS
LANGUAGE_OWNERSHIP=PASS
IDENTITY_OWNERSHIP=PASS
TOOL_CONTEXT_OWNERSHIP=PASS
TTS_PLAYBACK_OWNERSHIP=PASS
UTTERANCE_ENVELOPE=PASS
RESOLVER_HOOK=PASS
RESOLVER_DEFAULT_NOOP=YES
RAW_ASR_IMMUTABLE=YES
SHADOW_MODE_READY=YES
CANARY_READY=YES
FALLBACK_READY=YES

V1_V2_BEHAVIOR_DIFFS=none on golden scenarios
  MUSIC_REQUEST still passes raw 'visa này' through (not a quality fix)
  WEATHER/LOCATION use LOCATION_UNKNOWN (never 未知位置/广州)

KNOWN_OPEN_TRACKS=
SHORT_NOISY_ASR
MULTILINGUAL_ASR
ENGLISH_LEARNER_ASR
MINILM_RUE
SELF_LEARNING
TTS_DEVICE_LATENCY_SPIKE

PRODUCTION_FILES_CHANGED=NONE
PRODUCTION_RESTARTS=NONE
PRODUCTION_DB_CHANGES=NONE
FIRMWARE_CHANGES=NONE

GATE_V2_INTEGRATE=PENDING_HUMAN_SNAPSHOT_AND_APPROVAL

NEXT_ACTION=
Human snapshot current eve.ai tomorrow,
then review candidate and start shadow/canary integration.

STOP.
```

## Why PARTIAL

Isolated V2 (docs A–K, source, 65 unit tests) is complete and passing.
Live Eve file hashes could not be recorded here. Do not treat this as
GATE-V2-INTEGRATE.

## Candidate tree

- Package: `eve_conversation_v2` under `conversation-v2-candidate/src/`
- Tests: `conversation-v2-candidate/tests/` (`python3 -m pytest`)
- Docs: `conversation-v2-candidate/docs/`

## Devil follow-ups that were fixed in this tree

- ASR disconnect now bumps epoch/gen (stale Qwen finals cannot reuse 1/1)
- Cancel closes listen (READY cannot flush PCM after cancel)
- V1 fallback stops V2 TTS (no dual-path audio)
- Wake during an open conversation does not mute tagged conversational PCM
- ASR final requires open turn + listen; duplicate finals rejected
- Hello clears LLM history; envelope PCM stats are per listen turn
