from __future__ import annotations


class V2Error(Exception):
    """Base error for the isolated Conversation/Core V2 candidate."""


class OwnershipError(V2Error):
    """Raised when a non-owner attempts to write owned state."""


class IdentityUnsetError(V2Error):
    """No hidden identity fallback: assistant identity must be explicit."""


class ForbiddenLocationFallbackError(V2Error):
    """Chinese or hardcoded city fallbacks must not become authoritative location."""


class RawAsrMutationError(V2Error):
    """raw_asr is immutable once captured."""


class StaleSessionError(V2Error):
    """ASR final or PCM bound to a stale epoch/generation."""


class FallbackLoopError(V2Error):
    """Automatic V1 fallback may occur at most once per turn, before user-visible output."""


class UnsafeFallbackError(V2Error):
    """Fallback after user-visible output is forbidden."""
