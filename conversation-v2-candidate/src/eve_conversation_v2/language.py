"""LANGUAGE_OWNER — do not collapse language fields."""

from __future__ import annotations

from dataclasses import dataclass

from .baseline import ASR_BASELINE
from .errors import OwnershipError


@dataclass(frozen=True)
class LanguageSnapshot:
    primary_language: str
    learning_languages: tuple[str, ...]
    conversation_language: str
    asr_language_hint: str
    tts_locale: str
    # Future-capable fields (unused tonight; do not remove).
    allowed_languages: tuple[str, ...] = ("vi", "en")
    asr_mode: str = "HINT"  # HINT | AUTO | CODE_SWITCH
    learning_level: str | None = None


class LanguageOwner:
    OWNER = "LANGUAGE_OWNER"

    def __init__(
        self,
        *,
        primary_language: str = "vi",
        learning_languages: tuple[str, ...] = (),
        conversation_language: str | None = None,
        asr_language_hint: str | None = None,
        tts_locale: str | None = None,
        learning_level: str | None = None,
    ) -> None:
        hint = asr_language_hint if asr_language_hint is not None else ASR_BASELINE.language
        conv = conversation_language if conversation_language is not None else primary_language
        locale = tts_locale if tts_locale is not None else conv
        self._snapshot = LanguageSnapshot(
            primary_language=primary_language,
            learning_languages=tuple(learning_languages),
            conversation_language=conv,
            asr_language_hint=hint,
            tts_locale=locale,
            allowed_languages=("vi", "en"),
            asr_mode="HINT",
            learning_level=learning_level,
        )

    def snapshot(self) -> LanguageSnapshot:
        return self._snapshot

    def set_conversation_language(self, language: str) -> LanguageSnapshot:
        s = self._snapshot
        self._snapshot = LanguageSnapshot(
            primary_language=s.primary_language,
            learning_languages=s.learning_languages,
            conversation_language=language,
            asr_language_hint=s.asr_language_hint,
            tts_locale=s.tts_locale,
            allowed_languages=s.allowed_languages,
            asr_mode=s.asr_mode,
            learning_level=s.learning_level,
        )
        return self._snapshot

    def write_foreign(self, *_args, **_kwargs) -> None:
        raise OwnershipError(f"only {self.OWNER} may write language fields")
