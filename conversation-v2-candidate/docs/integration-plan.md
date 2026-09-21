# Tomorrow integration plan — PREPARE ONLY. DO NOT EXECUTE.

GATE-V2-INTEGRATE = **PENDING_HUMAN_SNAPSHOT_AND_APPROVAL**  
No agent may self-approve this gate.

## Human sequence

1. **Snapshot current eve.ai** (code, prompts, compose, ASR/TTS config, DB schema dump if needed — no DB writes).
2. **Verify snapshot** (hashes, container image ids, prompt sha256, ASR baseline still vi/0.2/600/1000).
3. **Create PRE-V2 rollback point** (see `rollback-plan.md`).
4. **Deploy V2 behind feature flag** (`conversation_v2_enabled=false` on boot). Copy candidate to `/opt/eve/releases/conversation-v2-candidate/` — do not replace live modules until flag on.
5. **Enable shadow mode** (`conversation_v2_enabled=true`, `shadow_mode=true`, empty or non-matching canary). Compare V1/V2 envelopes + timelines.
6. **Compare V1/V2** using `docs/behavior-matrix.md`. Unexpected DIFF = STOP.
7. **Enable one canary Stick** (`canary_device_ids={that id}`).
8. **Run** wake / chat / music / weather / location.
9. **Inspect** ASR finals, TTS telemetry (provider first audio vs device first audio), latency. TTS spike track stays open.
10. **Expand only with human approval.**

## Adapter work tomorrow (not done tonight)

Wire `ConversationEngineV2` in front of live:

- Opus decode → `on_pcm`
- device `listen/start` → `on_listen_start`
- existing wake path → `on_wake` **without removing** the live wake-flush fix until V2 is proven
- Qwen WS ready/reconnect → `on_asr_ready` / `on_asr_reconnect`
- ASR final text → `on_asr_final` then existing intent/LLM/TTS **or** V2 mocks replaced by real adapters

Do **not** delete the current proven wake-flush fix from baseline as part of a naive swap.

## Clean / firmware / DB

Not in this integration. `PRODUCTION_DB_CHANGES=NONE` unless a later human ticket says otherwise.
