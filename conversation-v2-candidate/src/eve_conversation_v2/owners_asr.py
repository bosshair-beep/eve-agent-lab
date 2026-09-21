"""ASR_SESSION_OWNER — asr_epoch, qwen_session_gen, ready. Does not own conversation_open."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import StaleSessionError


@dataclass(frozen=True)
class AsrSessionSnapshot:
    asr_epoch: int
    qwen_session_gen: int
    ready: bool
    connecting: bool


class AsrSessionOwner:
    OWNER = "ASR_SESSION_OWNER"

    def __init__(self) -> None:
        self._asr_epoch = 0
        self._qwen_session_gen = 0
        self._ready = False
        self._connecting = False

    def snapshot(self) -> AsrSessionSnapshot:
        return AsrSessionSnapshot(
            asr_epoch=self._asr_epoch,
            qwen_session_gen=self._qwen_session_gen,
            ready=self._ready,
            connecting=self._connecting,
        )

    def connect_start(self) -> AsrSessionSnapshot:
        self._connecting = True
        self._ready = False
        return self.snapshot()

    def mark_ready(self) -> AsrSessionSnapshot:
        if self._asr_epoch == 0:
            self._asr_epoch = 1
            self._qwen_session_gen = 1
        self._connecting = False
        self._ready = True
        return self.snapshot()

    def disconnect(self) -> AsrSessionSnapshot:
        self._ready = False
        self._connecting = False
        return self.snapshot()

    def reconnect(self) -> AsrSessionSnapshot:
        """New ASR socket. Conversation state is NOT owned here."""
        self._qwen_session_gen += 1
        self._asr_epoch += 1
        self._connecting = True
        self._ready = False
        return self.snapshot()

    def reset_session(self) -> AsrSessionSnapshot:
        self._asr_epoch = 0
        self._qwen_session_gen = 0
        self._ready = False
        self._connecting = False
        return self.snapshot()

    def accept_final(self, *, epoch: int, session_gen: int) -> None:
        if epoch != self._asr_epoch or session_gen != self._qwen_session_gen:
            raise StaleSessionError(
                f"stale ASR final epoch={epoch} gen={session_gen} "
                f"current epoch={self._asr_epoch} gen={self._qwen_session_gen}"
            )
        if not self._ready:
            raise StaleSessionError("ASR final while session not ready")
