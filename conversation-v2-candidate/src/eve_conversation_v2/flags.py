from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class V2Route(StrEnum):
    """Where this device's user-visible path should go."""

    V1_PRODUCTION = "V1_PRODUCTION"
    V2_PRIMARY = "V2_PRIMARY"
    V2_SHADOW = "V2_SHADOW"


@dataclass(frozen=True)
class FeatureFlags:
    """V2 feature flags. Defaults keep production behavior.

    conversation_v2_enabled: master switch (default off).
    resolver_enabled: MiniLM/RUE must stay off; even if true, V2 resolver is NO-OP.
    shadow_mode: run V2 observe-only (no user-visible TTS from V2).
    canary_device_ids: devices allowed to use V2 as primary when enabled.
    fallback_to_v1: if V2 fails BEFORE user-visible output, return to V1 once.
    """

    conversation_v2_enabled: bool = False
    resolver_enabled: bool = False
    shadow_mode: bool = False
    canary_device_ids: frozenset[str] = field(default_factory=frozenset)
    fallback_to_v1: bool = True

    def route_for(self, device_id: str) -> V2Route:
        if not self.conversation_v2_enabled:
            return V2Route.V1_PRODUCTION
        in_canary = device_id in self.canary_device_ids
        if self.shadow_mode and not in_canary:
            return V2Route.V2_SHADOW
        if in_canary:
            return V2Route.V2_PRIMARY
        if self.shadow_mode:
            return V2Route.V2_SHADOW
        # Enabled but no canary and not shadow: still V1. Do not silently
        # cut over the fleet.
        return V2Route.V1_PRODUCTION
