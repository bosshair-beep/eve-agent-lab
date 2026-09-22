# Known issues NOT fixed by V2 tonight

These tracks stay explicit. V2 must not silently absorb them.

| Track | Why still open |
|---|---|
| `SHORT_NOISY_ASR` | Examples: `mở nhạc đi`→`visa này`. raw_asr immutable; no correction. |
| `MULTILINGUAL_ASR` | Architecture has `allowed_languages` / `asr_mode=AUTO` unused. Hint remains `vi`. |
| `ENGLISH_LEARNER_ASR` | `learning_languages` / `learning_level` on envelope only. |
| `MINILM_RUE` | Resolver hook is NO-OP. No MiniLM, no candidate generation, no phonetic resolver, no calibration. |
| `SELF_LEARNING` | Not implemented. |
| `TTS_DEVICE_LATENCY_SPIKE` | Telemetry distinguishes provider vs device first audio. Provider not redesigned. Forensic remains separate. |

Do not treat golden MUSIC_REQUEST PASS as an ASR quality fix.
