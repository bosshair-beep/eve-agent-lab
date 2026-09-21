"""TTS_PLAYBACK_OWNER — explicit playback states. Does not redesign TTS provider."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import V2Error
from .types import TtsPlaybackState


LEGAL_TRANSITIONS: dict[TtsPlaybackState, frozenset[TtsPlaybackState]] = {
    TtsPlaybackState.IDLE: frozenset({TtsPlaybackState.GENERATING, TtsPlaybackState.INTERRUPTED}),
    TtsPlaybackState.GENERATING: frozenset(
        {TtsPlaybackState.QUEUED, TtsPlaybackState.INTERRUPTED, TtsPlaybackState.IDLE}
    ),
    TtsPlaybackState.QUEUED: frozenset(
        {TtsPlaybackState.SENDING, TtsPlaybackState.INTERRUPTED, TtsPlaybackState.IDLE}
    ),
    TtsPlaybackState.SENDING: frozenset(
        {TtsPlaybackState.PLAYING, TtsPlaybackState.DRAINING, TtsPlaybackState.INTERRUPTED}
    ),
    TtsPlaybackState.PLAYING: frozenset(
        {TtsPlaybackState.DRAINING, TtsPlaybackState.INTERRUPTED, TtsPlaybackState.IDLE}
    ),
    TtsPlaybackState.DRAINING: frozenset({TtsPlaybackState.IDLE, TtsPlaybackState.INTERRUPTED}),
    TtsPlaybackState.INTERRUPTED: frozenset({TtsPlaybackState.IDLE, TtsPlaybackState.GENERATING}),
}


@dataclass
class TtsTelemetry:
    provider_first_audio_ms: int | None = None
    queue_enqueue_ms: int | None = None
    queue_dequeue_ms: int | None = None
    first_binary_send_ms: int | None = None
    last_binary_send_ms: int | None = None
    device_playback_state: str | None = None


@dataclass(frozen=True)
class TtsSnapshot:
    state: TtsPlaybackState
    telemetry: TtsTelemetry


class TtsPlaybackOwner:
    OWNER = "TTS_PLAYBACK_OWNER"

    def __init__(self) -> None:
        self._state = TtsPlaybackState.IDLE
        self.telemetry = TtsTelemetry()

    def snapshot(self) -> TtsSnapshot:
        return TtsSnapshot(state=self._state, telemetry=self.telemetry)

    def reset(self) -> None:
        self._state = TtsPlaybackState.IDLE
        self.telemetry = TtsTelemetry()

    def interrupt(self) -> TtsPlaybackState:
        if self._state != TtsPlaybackState.IDLE:
            self._state = TtsPlaybackState.INTERRUPTED
        return self._state

    def transition(self, new: TtsPlaybackState, *, now_ms: int) -> TtsPlaybackState:
        allowed = LEGAL_TRANSITIONS[self._state]
        if new not in allowed:
            raise V2Error(f"illegal TTS transition {self._state} -> {new}")
        self._state = new
        if new == TtsPlaybackState.GENERATING:
            pass
        elif new == TtsPlaybackState.QUEUED:
            self.telemetry.queue_enqueue_ms = now_ms
        elif new == TtsPlaybackState.SENDING:
            self.telemetry.queue_dequeue_ms = now_ms
            if self.telemetry.first_binary_send_ms is None:
                self.telemetry.first_binary_send_ms = now_ms
            self.telemetry.last_binary_send_ms = now_ms
        elif new == TtsPlaybackState.PLAYING:
            self.telemetry.device_playback_state = "PLAYING"
        elif new == TtsPlaybackState.IDLE:
            self.telemetry.device_playback_state = "IDLE"
        return self._state

    def mark_provider_first_audio(self, now_ms: int) -> None:
        if self.telemetry.provider_first_audio_ms is None:
            self.telemetry.provider_first_audio_ms = now_ms

    def mark_binary_send(self, now_ms: int) -> None:
        if self.telemetry.first_binary_send_ms is None:
            self.telemetry.first_binary_send_ms = now_ms
        self.telemetry.last_binary_send_ms = now_ms
