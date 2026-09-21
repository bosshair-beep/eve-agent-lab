# Current Eve (V1 expected) vs V2 behavior matrix

Source of V1_EXPECTED: mission invariants + proven wake/Câm fix (not a live
re-run of production). Unexpected divergence = FAIL.

| Scenario | V1_EXPECTED | V2_RESULT | DIFF | DIFF_JUSTIFIED |
|---|---|---|---|---|
| NORMAL_WAKE | wake PCM not conversational ASR | DISCARDED `WAKE_ISOLATION`; conversation stays closed until listen/start | none | — |
| NORMAL_VI_CHAT | ASR hint vi; chat completes; identity consistent | `asr_language_hint=vi`; `resolved=raw`; identity Eve on all surfaces | none | — |
| MUSIC_REQUEST | raw mishear e.g. `visa này` still a user utterance | raw+resolved=`visa này`; intent MUSIC from observed text | none | does **not** restore `mở nhạc đi` (open track SHORT_NOISY_ASR) |
| WEATHER_REQUEST | must not silently use 广州/未知位置 | `LOCATION_UNKNOWN`; tool fail/clarify | none | — |
| LOCATION_REQUEST | same | `LOCATION_UNKNOWN` | none | — |
| SHORT_UTTERANCE | still a turn | envelope; resolver NO-OP | none | — |
| IDLE_GOODBYE | idle ends listen | `IDLE_TIMEOUT` + pending discarded | none | — |
| REPEATED_WAKE | each wake isolated | both wake PCM discarded | none | — |
| ASR_RECONNECT | recover session; no stale final | gen/epoch bump; conversation_open unchanged; stale final rejected | none | — |

ASR parameters (must match current, not “improved”):

`language=vi` `threshold=0.2` `prefix_padding_ms=600` `silence_duration_ms=1000`

V2 does not change these values.
