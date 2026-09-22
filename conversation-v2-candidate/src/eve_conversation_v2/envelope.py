"""UtteranceEnvelope contract. raw_asr is immutable."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .errors import RawAsrMutationError


@dataclass(frozen=True)
class AudioMetadata:
    duration_ms: int = 0
    silero_frames: int = 0
    preroll_available: bool = False
    preroll_sent: bool = False
    qwen_window_ms: int = 0


@dataclass(frozen=True)
class AsrMetadata:
    provider: str = "qwen"
    model: str = "qwen-asr"
    session_gen: int = 0
    epoch: int = 0


@dataclass(frozen=True)
class ResolverMetadata:
    enabled: bool = False
    provider: str = "noop"
    confidence: float | None = None
    reason: str = "NO_OP_PASSTHROUGH"


@dataclass(frozen=True)
class UtteranceEnvelope:
    session_id: str
    turn_id: str
    raw_asr: str
    resolved_utterance: str
    primary_language: str
    learning_languages: tuple[str, ...]
    learning_level: str | None
    asr_language_hint: str
    conversation_language: str
    recent_history: tuple[str, ...]
    audio_metadata: AudioMetadata = field(default_factory=AudioMetadata)
    asr_metadata: AsrMetadata = field(default_factory=AsrMetadata)
    suspicion_flags: tuple[str, ...] = ()
    resolver_metadata: ResolverMetadata = field(default_factory=ResolverMetadata)

    def with_resolved(self, text: str, metadata: ResolverMetadata) -> "UtteranceEnvelope":
        # raw_asr must remain the original bytes/text.
        return replace(self, resolved_utterance=text, resolver_metadata=metadata)

    def mutate_raw_asr(self, _new: str) -> None:
        raise RawAsrMutationError("raw_asr is immutable")
