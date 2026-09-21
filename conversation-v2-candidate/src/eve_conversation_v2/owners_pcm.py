"""PCM_DELIVERY_OWNER — send-once or discard-with-reason. Owns post_flush_live.

Qwen WS ready must not silently arm forwarding; ListenOwner must have opened
conversation first (arm_live_forward_after_wake_isolation).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .types import DiscardReason, PcmDisposition


PcmSource = Literal["wake", "conversation", "unknown"]


@dataclass(frozen=True)
class PcmFrame:
    frame_id: int
    pcm: bytes
    source: PcmSource
    epoch: int
    t_ms: int


@dataclass(frozen=True)
class PcmRecord:
    frame_id: int
    disposition: PcmDisposition
    reason: DiscardReason | None
    source: PcmSource


@dataclass(frozen=True)
class PcmSnapshot:
    post_flush_live: bool
    pending_count: int
    sent_ids: frozenset[int]
    discarded_ids: frozenset[int]


class PcmDeliveryOwner:
    OWNER = "PCM_DELIVERY_OWNER"
    MAX_PENDING = 64

    def __init__(self) -> None:
        self._post_flush_live = False
        self._pending: list[PcmFrame] = []
        self._sent_ids: set[int] = set()
        self._discarded_ids: set[int] = set()
        self.records: list[PcmRecord] = []
        self.first_pcm_sent = False

    def snapshot(self) -> PcmSnapshot:
        return PcmSnapshot(
            post_flush_live=self._post_flush_live,
            pending_count=len(self._pending),
            sent_ids=frozenset(self._sent_ids),
            discarded_ids=frozenset(self._discarded_ids),
        )

    def reset(self, *, reason: DiscardReason = DiscardReason.SESSION_RESET) -> None:
        self.discard_pending(reason)
        self._post_flush_live = False
        self._sent_ids.clear()
        self._discarded_ids.clear()
        self.records.clear()
        self.first_pcm_sent = False

    def disarm(self) -> None:
        self._post_flush_live = False

    def arm_live_forward_after_wake_isolation(self, *, conversation_open: bool, asr_ready: bool) -> bool:
        """Authoritative arm. Returns True iff post_flush_live became true."""
        if conversation_open and asr_ready:
            self._post_flush_live = True
            return True
        self._post_flush_live = False
        return False

    def discard_stale_and_wake_buffers(self) -> list[PcmRecord]:
        out: list[PcmRecord] = []
        for frame in self._pending:
            reason = (
                DiscardReason.WAKE_ISOLATION
                if frame.source == "wake"
                else DiscardReason.STALE_BUFFER
            )
            out.append(self._discard(frame, reason))
        self._pending.clear()
        return out

    def ingest(
        self,
        frame: PcmFrame,
        *,
        wake_pcm_blocked: bool,
        conversation_open: bool,
        user_visible_route_sends: bool,
        observe_only: bool = False,
    ) -> PcmRecord:
        if frame.frame_id in self._sent_ids or frame.frame_id in self._discarded_ids:
            rec = PcmRecord(
                frame_id=frame.frame_id,
                disposition=PcmDisposition.DISCARDED,
                reason=DiscardReason.DUPLICATE_FRAME,
                source=frame.source,
            )
            self.records.append(rec)
            return rec

        if not user_visible_route_sends:
            # Shadow / V1 route: still observe, never "send" to production ASR.
            if wake_pcm_blocked or frame.source == "wake":
                return self._discard(frame, DiscardReason.WAKE_ISOLATION)
            reason = (
                DiscardReason.SHADOW_OBSERVE_ONLY
                if observe_only
                else DiscardReason.ENGINE_NOT_PRIMARY
            )
            return self._discard(frame, reason)

        if wake_pcm_blocked or frame.source == "wake":
            return self._discard(frame, DiscardReason.WAKE_ISOLATION)

        if not conversation_open:
            return self._discard(frame, DiscardReason.CONVERSATION_CLOSED)

        if self._post_flush_live:
            return self._send(frame)

        # conversation open, ASR not live: explicit pending (not append-without-send).
        if len(self._pending) >= self.MAX_PENDING:
            return self._discard(frame, DiscardReason.ASR_NOT_READY)
        self._pending.append(frame)
        rec = PcmRecord(
            frame_id=frame.frame_id,
            disposition=PcmDisposition.PENDING,
            reason=DiscardReason.ASR_NOT_READY,
            source=frame.source,
        )
        self.records.append(rec)
        return rec

    def flush_pending_if_live(self) -> list[PcmRecord]:
        if not self._post_flush_live:
            return []
        out: list[PcmRecord] = []
        pending = self._pending
        self._pending = []
        for frame in pending:
            out.append(self._send(frame))
        return out

    def discard_pending(self, reason: DiscardReason) -> list[PcmRecord]:
        out = [self._discard(f, reason) for f in self._pending]
        self._pending.clear()
        return out

    def _send(self, frame: PcmFrame) -> PcmRecord:
        self._sent_ids.add(frame.frame_id)
        rec = PcmRecord(
            frame_id=frame.frame_id,
            disposition=PcmDisposition.SENT,
            reason=None,
            source=frame.source,
        )
        self.records.append(rec)
        if not self.first_pcm_sent:
            self.first_pcm_sent = True
        return rec

    def _discard(self, frame: PcmFrame, reason: DiscardReason) -> PcmRecord:
        self._discarded_ids.add(frame.frame_id)
        rec = PcmRecord(
            frame_id=frame.frame_id,
            disposition=PcmDisposition.DISCARDED,
            reason=reason,
            source=frame.source,
        )
        self.records.append(rec)
        return rec

    def assert_no_dead_append(self) -> None:
        """Invariant: no frame is both pending and already sent/discarded."""
        pending_ids = {f.frame_id for f in self._pending}
        overlap = pending_ids & (self._sent_ids | self._discarded_ids)
        if overlap:
            raise RuntimeError(f"PCM append-without-send dead state: {overlap}")
