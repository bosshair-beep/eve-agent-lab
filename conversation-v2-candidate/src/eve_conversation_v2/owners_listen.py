"""LISTEN_OWNER — conversation_open. listen/start is the authoritative audio open."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListenSnapshot:
    conversation_open: bool
    listen_boundary_applied: bool


class ListenOwner:
    OWNER = "LISTEN_OWNER"

    def __init__(self) -> None:
        self._conversation_open = False
        self._listen_boundary_applied = False

    def snapshot(self) -> ListenSnapshot:
        return ListenSnapshot(
            conversation_open=self._conversation_open,
            listen_boundary_applied=self._listen_boundary_applied,
        )

    def apply_listen_start_boundary(self) -> ListenSnapshot:
        self._conversation_open = True
        self._listen_boundary_applied = True
        return self.snapshot()

    def close(self) -> ListenSnapshot:
        self._conversation_open = False
        self._listen_boundary_applied = False
        return self.snapshot()

    def reset(self) -> ListenSnapshot:
        return self.close()
