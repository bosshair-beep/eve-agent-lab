"""IDENTITY_OWNER — single authoritative assistant identity writer."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import IdentityUnsetError, OwnershipError


@dataclass(frozen=True)
class IdentitySnapshot:
    assistant_name: str
    source: str
    """Where the name was set. Never 'implicit_fallback'."""


class IdentityOwner:
    """Everything consuming identity must read from snapshot().

    Surfaces: wake greeting, system prompt, display, LLM context,
    TTS-facing assistant name.
    """

    OWNER = "IDENTITY_OWNER"

    def __init__(self, assistant_name: str, source: str) -> None:
        name = (assistant_name or "").strip()
        if not name:
            raise IdentityUnsetError(
                "assistant_name is required; hidden identity fallback is forbidden"
            )
        if not (source or "").strip() or source == "implicit_fallback":
            raise IdentityUnsetError(
                "identity source must be explicit (not implicit_fallback)"
            )
        self._snapshot = IdentitySnapshot(assistant_name=name, source=source.strip())

    def snapshot(self) -> IdentitySnapshot:
        return self._snapshot

    def greeting_text(self) -> str:
        return self._snapshot.assistant_name

    def system_prompt_name(self) -> str:
        return self._snapshot.assistant_name

    def display_name(self) -> str:
        return self._snapshot.assistant_name

    def llm_context_name(self) -> str:
        return self._snapshot.assistant_name

    def tts_facing_name(self) -> str:
        return self._snapshot.assistant_name

    def names_for_all_surfaces(self) -> dict[str, str]:
        n = self._snapshot.assistant_name
        return {
            "wake_greeting": n,
            "system_prompt": n,
            "display": n,
            "llm_context": n,
            "tts_facing": n,
        }

    def write(self, *_args, **_kwargs) -> None:
        raise OwnershipError(f"only {self.OWNER} may write identity; identity is immutable after construct")
