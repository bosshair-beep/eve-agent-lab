"""TURN_EVENT_OWNER — session_id, turn_id, turn lifecycle, timeline."""

from __future__ import annotations

from dataclasses import dataclass

from .telemetry import Timeline, TimelineEvent
from .types import SessionId, TimelineEventName, TurnId


@dataclass(frozen=True)
class TurnSnapshot:
    session_id: SessionId
    turn_id: TurnId
    turn_seq: int
    open: bool
    user_visible_started: bool
    fallback_used: bool
    cancelled: bool
    completed: bool


class TurnEventOwner:
    OWNER = "TURN_EVENT_OWNER"

    def __init__(self, *, now_ms: int = 0) -> None:
        self._session_id = SessionId("")
        self._turn_seq = 0
        self._turn_id = TurnId("")
        self._open = False
        self._user_visible_started = False
        self._fallback_used = False
        self._cancelled = False
        self._completed = False
        self.timeline = Timeline()
        self._now_ms = now_ms
        self._clock_owner = True

    def snapshot(self) -> TurnSnapshot:
        return TurnSnapshot(
            session_id=self._session_id,
            turn_id=self._turn_id,
            turn_seq=self._turn_seq,
            open=self._open,
            user_visible_started=self._user_visible_started,
            fallback_used=self._fallback_used,
            cancelled=self._cancelled,
            completed=self._completed,
        )

    def set_clock(self, now_ms: int) -> None:
        self._now_ms = now_ms

    @property
    def now_ms(self) -> int:
        return self._now_ms

    def on_hello(self, session_id: str) -> TurnSnapshot:
        self._session_id = SessionId(session_id)
        self._turn_seq = 0
        self._turn_id = TurnId("")
        self._open = False
        self._user_visible_started = False
        self._fallback_used = False
        self._cancelled = False
        self._completed = False
        self.timeline = Timeline()
        self.emit(TimelineEventName.HELLO)
        return self.snapshot()

    def open_turn(self) -> TurnSnapshot:
        self._turn_seq += 1
        self._turn_id = TurnId(f"{self._session_id}:t{self._turn_seq}")
        self._open = True
        self._user_visible_started = False
        self._fallback_used = False
        self._cancelled = False
        self._completed = False
        return self.snapshot()

    def mark_user_visible(self) -> None:
        self._user_visible_started = True

    def mark_fallback_used(self) -> None:
        self._fallback_used = True

    def cancel(self) -> TurnSnapshot:
        self._cancelled = True
        self._open = False
        self.emit(TimelineEventName.TURN_CANCEL)
        return self.snapshot()

    def complete(self) -> TurnSnapshot:
        self._completed = True
        self._open = False
        self.emit(TimelineEventName.TURN_END)
        return self.snapshot()

    def emit(self, name: TimelineEventName, *, asr_epoch: int = 0, qwen_session_gen: int = 0, detail: str = "") -> TimelineEvent:
        return self.timeline.emit(
            name,
            t_ms=self._now_ms,
            session_id=str(self._session_id),
            turn_id=str(self._turn_id),
            asr_epoch=asr_epoch,
            qwen_session_gen=qwen_session_gen,
            detail=detail,
        )
