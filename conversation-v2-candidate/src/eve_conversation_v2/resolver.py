"""SuspiciousUtteranceResolverHook — NO-OP in V2 initial implementation.

Do NOT implement MiniLM, self-learning, candidate generation, phonetic
resolver, or probability calibration. Future module name:
SuspiciousUtteranceResolver / RUE (Robust Utterance Engine).
"""

from __future__ import annotations

from .envelope import ResolverMetadata, UtteranceEnvelope


class SuspiciousUtteranceResolverHook:
    """Extension point only.

    Future input may include: raw_asr, candidate transcripts, Child Profile,
    primary_language, learning_languages, learning_level, recent history,
    audio metadata, ASR metadata, phonetic candidates, domain vocabulary.

    Future output: resolved_utterance, confidence, reason, candidate ranking.
    """

    def resolve(self, envelope: UtteranceEnvelope, *, enabled: bool) -> UtteranceEnvelope:
        meta = ResolverMetadata(
            enabled=enabled,
            provider="noop",
            confidence=1.0 if enabled else None,
            reason="NO_OP_PASSTHROUGH",
        )
        # Initial V2: resolved_utterance = raw_asr always.
        return envelope.with_resolved(envelope.raw_asr, meta)
