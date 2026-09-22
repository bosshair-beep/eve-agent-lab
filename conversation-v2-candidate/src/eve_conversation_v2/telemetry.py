"""Turn-correlated observability. Do not log PCM contents by default."""

from __future__ import annotations

from dataclasses import dataclass, field

from .types import TimelineEventName


@dataclass(frozen=True)
class TimelineEvent:
    name: TimelineEventName
    t_ms: int
    session_id: str
    turn_id: str
    asr_epoch: int
    qwen_session_gen: int
    detail: str = ""


@dataclass
class Timeline:
    events: list[TimelineEvent] = field(default_factory=list)

    def emit(
        self,
        name: TimelineEventName,
        *,
        t_ms: int,
        session_id: str,
        turn_id: str,
        asr_epoch: int,
        qwen_session_gen: int,
        detail: str = "",
    ) -> TimelineEvent:
        ev = TimelineEvent(
            name=name,
            t_ms=t_ms,
            session_id=session_id,
            turn_id=turn_id,
            asr_epoch=asr_epoch,
            qwen_session_gen=qwen_session_gen,
            detail=detail,
        )
        self.events.append(ev)
        return ev

    def names(self) -> list[str]:
        return [e.name.value for e in self.events]

    def has(self, name: TimelineEventName) -> bool:
        return any(e.name == name for e in self.events)
