"""Behavioral baseline constants.

Live production eve.ai was READ-ONLY in this environment. These values are
taken from the V2 build mission (WORK_ID=EVE_CONVERSATION_CORE_V2_BUILD)
and must not be silently changed. Historical evidence is referenced, not
re-interpreted.
"""

from __future__ import annotations

from dataclasses import dataclass

from .version import WORK_ID

WORK_ID = WORK_ID

# Current ASR baseline — do not change these parameters in V2.
@dataclass(frozen=True)
class AsrBaseline:
    language: str = "vi"
    threshold: float = 0.2
    prefix_padding_ms: int = 600
    silence_duration_ms: int = 1000


ASR_BASELINE = AsrBaseline()

# Proven wake/Câm fix (source: mission §1.A). Preserve invariant:
# wake PCM never becomes user conversational PCM.
WAKE_CAM_FAILURE_CHAIN = (
    "wake",
    "wake_pcm_blocked=true",
    "session.updated",
    "_flush_pending blocked",
    "_post_flush_live=false",
    "post-listen PCM appended",
    "no _send_pcm",
    "Câm",
)

WAKE_CAM_CURRENT_FIX = (
    "apply_listen_start_boundary(opened)",
    "arm_live_forward_after_wake_isolation",
    "discard stale/wake buffers",
    "if Qwen WS ready: _post_flush_live=true",
    "subsequent conversational PCM forwarded",
)

# Raw ASR is immutable. These are known ASR mishears, not wake/Câm.
# V2 must pass them through unchanged (resolver NO-OP).
RAW_ASR_KNOWN_EXAMPLES: tuple[tuple[str, str], ...] = (
    ("mở nhạc đi", "visa này"),
    ("bài babyshark", "baby sack"),
    ("bài hát baby shark", "bày hết bay đi sát"),
)

FORBIDDEN_LOCATION_FALLBACKS: frozenset[str] = frozenset(
    {
        "未知位置",
        "广州",
        "guangzhou",
        "Guangzhou",
    }
)

CHINESE_IDENTITY_LEAK_MARKERS: frozenset[str] = frozenset(
    {
        "未知位置",
        "广州",
    }
)

# Production identity leak names that must not appear unless they ARE the
# authoritative IdentityOwner value.
HISTORICAL_IDENTITY_ALIASES: frozenset[str] = frozenset(
    {"Milo", "Ivy", "Linh", "lucy", "Lucy", "Sophia"}
)

OPEN_TRACKS: tuple[str, ...] = (
    "SHORT_NOISY_ASR",
    "MULTILINGUAL_ASR",
    "ENGLISH_LEARNER_ASR",
    "MINILM_RUE",
    "SELF_LEARNING",
    "TTS_DEVICE_LATENCY_SPIKE",
)
