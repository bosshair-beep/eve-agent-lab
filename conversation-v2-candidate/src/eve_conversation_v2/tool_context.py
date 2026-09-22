"""TOOL_CONTEXT_OWNER — tools must not independently derive location or identity."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import OwnershipError
from .identity import IdentitySnapshot
from .language import LanguageSnapshot
from .location import LocationSnapshot
from .types import LocationStatus, SessionId, TurnId


@dataclass(frozen=True)
class ToolContext:
    child_id: str | None
    device_id: str
    conversation_language: str
    learning_languages: tuple[str, ...]
    location: str | None
    location_status: LocationStatus
    timezone: str | None
    session_id: str
    turn_id: str
    assistant_name: str
    asr_language_hint: str


class ToolContextOwner:
    OWNER = "TOOL_CONTEXT_OWNER"

    def __init__(
        self,
        *,
        device_id: str,
        child_id: str | None = None,
        timezone: str | None = None,
    ) -> None:
        self._device_id = device_id
        self._child_id = child_id
        self._timezone = timezone
        self._last: ToolContext | None = None

    def snapshot(self) -> ToolContext | None:
        return self._last

    def compose(
        self,
        *,
        session_id: SessionId,
        turn_id: TurnId,
        identity: IdentitySnapshot,
        language: LanguageSnapshot,
        location: LocationSnapshot,
    ) -> ToolContext:
        ctx = ToolContext(
            child_id=self._child_id,
            device_id=self._device_id,
            conversation_language=language.conversation_language,
            learning_languages=language.learning_languages,
            location=location.location,
            location_status=location.status,
            timezone=self._timezone,
            session_id=str(session_id),
            turn_id=str(turn_id),
            assistant_name=identity.assistant_name,
            asr_language_hint=language.asr_language_hint,
        )
        self._last = ctx
        return ctx

    def write_foreign(self, *_args, **_kwargs) -> None:
        raise OwnershipError(f"only {self.OWNER} may write ToolContext")
