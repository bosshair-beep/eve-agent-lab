"""Safe V1 fallback boundary.

Fallback MAY return to current production path only if:
- fallback_to_v1 is true
- V2 has not produced user-visible output (no TTS_FIRST_AUDIO / DEVICE_FIRST_AUDIO)
- fallback has not already been used this turn

Fallback MUST NOT:
- trigger after TTS audio has been sent to the device
- loop (one shot)
- enable Implementer or change production config
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import FallbackLoopError, UnsafeFallbackError


@dataclass(frozen=True)
class FallbackDecision:
    used: bool
    reason: str
    boundary: str = "BEFORE_USER_VISIBLE_OUTPUT"


class FallbackPolicy:
    BOUNDARY = "BEFORE_USER_VISIBLE_OUTPUT"

    def decide(
        self,
        *,
        enabled: bool,
        user_visible_started: bool,
        already_used: bool,
        reason: str,
    ) -> FallbackDecision:
        if not enabled:
            return FallbackDecision(used=False, reason="fallback_to_v1=false")
        if already_used:
            raise FallbackLoopError("V1 fallback already used this turn")
        if user_visible_started:
            raise UnsafeFallbackError(
                "V1 fallback after user-visible output is unsafe; leave V2 turn to complete or human abort"
            )
        return FallbackDecision(used=True, reason=reason, boundary=self.BOUNDARY)
