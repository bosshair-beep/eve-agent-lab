"""Golden scenario contracts: current Eve (V1 expected) vs V2 result.

These are behavioral contracts derived from the V2 mission and the proven
wake/Câm fix. They are not a re-execution of production.
"""

from __future__ import annotations

from dataclasses import dataclass

from .flags import FeatureFlags


@dataclass(frozen=True)
class GoldenScenario:
    name: str
    v1_expected: str
    notes: str = ""


GOLDEN_SCENARIOS: tuple[GoldenScenario, ...] = (
    GoldenScenario(
        "NORMAL_WAKE",
        "wake PCM never sent to conversational ASR; listen/start required to arm forward",
    ),
    GoldenScenario(
        "NORMAL_VI_CHAT",
        "ASR hint=vi; resolved_utterance=raw_asr; identity consistent on all surfaces",
    ),
    GoldenScenario(
        "MUSIC_REQUEST",
        "raw ASR mishears pass through; music intent still reachable from known examples",
        notes="SHORT_NOISY_ASR remains an open track; V2 must not 'fix' raw_asr",
    ),
    GoldenScenario(
        "WEATHER_REQUEST",
        "without known location, tool/clarify LOCATION_UNKNOWN; never 未知位置/广州",
    ),
    GoldenScenario(
        "LOCATION_REQUEST",
        "same LOCATION_UNKNOWN contract",
    ),
    GoldenScenario(
        "SHORT_UTTERANCE",
        "envelope produced; raw_asr immutable; resolver NO-OP",
    ),
    GoldenScenario(
        "IDLE_GOODBYE",
        "idle timeout completes turn; pending PCM discarded with IDLE_TIMEOUT",
    ),
    GoldenScenario(
        "REPEATED_WAKE",
        "second wake still isolated; no leak of first wake PCM into ASR",
    ),
    GoldenScenario(
        "ASR_RECONNECT",
        "qwen_session_gen increments; conversation_open unchanged; stale finals rejected",
    ),
)

CANARY_FLAGS = FeatureFlags(
    conversation_v2_enabled=True,
    resolver_enabled=False,
    shadow_mode=False,
    canary_device_ids=frozenset({"stick-canary-1"}),
    fallback_to_v1=True,
)

SHADOW_FLAGS = FeatureFlags(
    conversation_v2_enabled=True,
    resolver_enabled=False,
    shadow_mode=True,
    canary_device_ids=frozenset(),
    fallback_to_v1=True,
)

PRODUCTION_SAFE_FLAGS = FeatureFlags()  # all defaults: V2 off
