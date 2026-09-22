# Feature flags, canary, shadow, fallback

`FeatureFlags` (`eve_conversation_v2.flags`)

| Flag | Default | Meaning |
|---|---|---|
| `conversation_v2_enabled` | `false` | Master switch. Off → V1 production path. |
| `resolver_enabled` | `false` | Even if true, resolver is still NO-OP (no MiniLM). |
| `shadow_mode` | `false` | V2 observes; does not send PCM to ASR / user-visible TTS as primary. |
| `canary_device_ids` | empty | Devices allowed to use V2 as primary when enabled. |
| `fallback_to_v1` | `true` | One safe fallback before user-visible output. |

## Routing

```
if not conversation_v2_enabled:
    V1_PRODUCTION
elif device_id in canary_device_ids:
    V2_PRIMARY          # even if shadow_mode (canary is the exception)
elif shadow_mode:
    V2_SHADOW
else:
    V1_PRODUCTION       # no silent fleet cutover
```

## Fallback boundary (exact)

**Allowed:** V2 exception **before** `TTS_FIRST_AUDIO` / `user_visible_started`,
at most once per turn.

**Forbidden:** fallback after device/TTS audio started; second fallback
(loop); fallback that mutates production config.

Complex automatic failover across in-flight TTS is **not** built because it
is unsafe. Human abort / `on_cancel` is the path after user-visible start.

## Tomorrow enablement (do not execute tonight)

1. Keep `conversation_v2_enabled=false` in production.
2. After snapshot: deploy candidate **behind flags**.
3. `shadow_mode=true` for observe.
4. Add **one** Stick id to `canary_device_ids`.
5. Expand only with human approval.
