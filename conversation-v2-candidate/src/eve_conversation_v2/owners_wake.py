"""WAKE_OWNER — wake_active, wake_pcm_blocked."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WakeSnapshot:
    wake_active: bool
    wake_pcm_blocked: bool


class WakeOwner:
    OWNER = "WAKE_OWNER"

    def __init__(self) -> None:
        self._wake_active = False
        self._wake_pcm_blocked = False

    def snapshot(self) -> WakeSnapshot:
        return WakeSnapshot(
            wake_active=self._wake_active,
            wake_pcm_blocked=self._wake_pcm_blocked,
        )

    def start_wake(self) -> WakeSnapshot:
        self._wake_active = True
        self._wake_pcm_blocked = True
        return self.snapshot()

    def apply_listen_start_boundary(self) -> WakeSnapshot:
        """After buffers are discarded, wake no longer blocks new conversational PCM."""
        self._wake_active = False
        self._wake_pcm_blocked = False
        return self.snapshot()

    def reset(self) -> WakeSnapshot:
        self._wake_active = False
        self._wake_pcm_blocked = False
        return self.snapshot()
