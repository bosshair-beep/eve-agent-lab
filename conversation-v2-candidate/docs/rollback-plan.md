# Rollback plan (PRE-V2)

## Principle

Production remains the rollback target until a human-verified snapshot exists.
This candidate does not replace live files.

## PRE-V2 rollback point (create tomorrow, not tonight)

Record:

- git commit / image tag of live eve.ai
- prompt file sha256
- ASR config (vi / 0.2 / 600 / 1000)
- TTS provider name + endpoint (no secrets in this repo)
- compose/unit file hashes
- `conversation_v2_enabled=false` confirmed

## Rollback steps (if canary misbehaves)

1. Set `conversation_v2_enabled=false` (immediate; returns fleet to V1 route).
2. If a canary process was patched, restore the snapshot artifact; **do not** restart the whole fleet unless the snapshot restore requires it.
3. Do not “fix forward” by enabling MiniLM or changing ASR thresholds.
4. Leave the proven wake-flush fix in place on V1.

## What V2 fallback already does

Per-turn `fallback_to_v1` only **before user-visible output**, once.
It is not a substitute for fleet rollback.
