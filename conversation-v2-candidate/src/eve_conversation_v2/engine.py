"""ConversationEngineV2 — isolated orchestrator.

Production eve.ai is never imported. This engine is buildable/testable
independently with mock PCM / ASR / Intent / LLM / TTS.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .baseline import ASR_BASELINE, HISTORICAL_IDENTITY_ALIASES
from .envelope import AsrMetadata, AudioMetadata, UtteranceEnvelope
from .errors import IdentityUnsetError, StaleSessionError, UnsafeFallbackError, V2Error
from .fallback import FallbackDecision, FallbackPolicy
from .flags import FeatureFlags, V2Route
from .identity import IdentityOwner, IdentitySnapshot
from .language import LanguageOwner, LanguageSnapshot
from .location import LocationOwner, LocationSnapshot
from .owners_asr import AsrSessionOwner, AsrSessionSnapshot
from .owners_listen import ListenOwner, ListenSnapshot
from .owners_pcm import PcmDeliveryOwner, PcmFrame, PcmRecord, PcmSnapshot
from .owners_tts import TtsPlaybackOwner, TtsSnapshot
from .owners_turn import TurnEventOwner, TurnSnapshot
from .owners_wake import WakeOwner, WakeSnapshot
from .resolver import SuspiciousUtteranceResolverHook
from .tool_context import ToolContext, ToolContextOwner
from .types import (
    DiscardReason,
    IntentName,
    LocationStatus,
    PcmDisposition,
    TimelineEventName,
    TtsPlaybackState,
)


@dataclass
class EngineConfig:
    assistant_name: str
    identity_source: str
    device_id: str
    child_id: str | None = None
    timezone: str | None = None
    flags: FeatureFlags = field(default_factory=FeatureFlags)
    primary_language: str = "vi"
    learning_languages: tuple[str, ...] = ()
    learning_level: str | None = None
    idle_timeout_ms: int = 15_000


@dataclass
class IntentResult:
    name: IntentName
    utterance: str
    tool_context: ToolContext
    clarified: str | None = None
    failed: bool = False
    fail_reason: str | None = None


@dataclass
class TurnResult:
    envelope: UtteranceEnvelope | None
    intent: IntentResult | None
    llm_text: str | None
    route: V2Route
    fallback: FallbackDecision | None
    error: str | None = None


class ConversationEngineV2:
    """Canonical pipeline owner assembly.

    DEVICE AUDIO → transport/Opus → PCM → wake/listen → VAD → ASR →
    raw_asr → UtteranceEnvelope → SuspiciousUtteranceResolverHook →
    resolved_utterance → Intent → Tool → LLM → TTS → Playback → turn end
    """

    def __init__(self, config: EngineConfig) -> None:
        if not (config.assistant_name or "").strip():
            raise IdentityUnsetError("EngineConfig.assistant_name required")
        self.config = config
        self.flags = config.flags
        self.turn = TurnEventOwner()
        self.wake = WakeOwner()
        self.listen = ListenOwner()
        self.asr = AsrSessionOwner()
        self.pcm = PcmDeliveryOwner()
        self.tts = TtsPlaybackOwner()
        self.identity = IdentityOwner(config.assistant_name, config.identity_source)
        self.language = LanguageOwner(
            primary_language=config.primary_language,
            learning_languages=config.learning_languages,
            learning_level=config.learning_level,
        )
        self.location = LocationOwner()
        self.tools = ToolContextOwner(
            device_id=config.device_id,
            child_id=config.child_id,
            timezone=config.timezone,
        )
        self.resolver = SuspiciousUtteranceResolverHook()
        self.fallback_policy = FallbackPolicy()
        self._frame_seq = 0
        self._last_activity_ms = 0
        self._envelope: UtteranceEnvelope | None = None
        self._intent: IntentResult | None = None
        self._llm_text: str | None = None
        self._vad_active = False
        self._history: list[str] = []
        self.last_fallback: FallbackDecision | None = None
        self.asr_baseline = ASR_BASELINE

    # --- snapshots (read-only) ---

    def route(self) -> V2Route:
        return self.flags.route_for(self.config.device_id)

    def sends_to_asr(self) -> bool:
        return self.route() == V2Route.V2_PRIMARY

    def observe_only(self) -> bool:
        return self.route() == V2Route.V2_SHADOW

    def identity_snapshot(self) -> IdentitySnapshot:
        return self.identity.snapshot()

    def language_snapshot(self) -> LanguageSnapshot:
        return self.language.snapshot()

    def location_snapshot(self) -> LocationSnapshot:
        return self.location.snapshot()

    def wake_snapshot(self) -> WakeSnapshot:
        return self.wake.snapshot()

    def listen_snapshot(self) -> ListenSnapshot:
        return self.listen.snapshot()

    def asr_snapshot(self) -> AsrSessionSnapshot:
        return self.asr.snapshot()

    def pcm_snapshot(self) -> PcmSnapshot:
        return self.pcm.snapshot()

    def tts_snapshot(self) -> TtsSnapshot:
        return self.tts.snapshot()

    def turn_snapshot(self) -> TurnSnapshot:
        return self.turn.snapshot()

    def leak_check_identity(self) -> list[str]:
        """Devil helper: names on surfaces that differ from owner."""
        names = self.identity.names_for_all_surfaces()
        auth = self.identity.snapshot().assistant_name
        leaks = [k for k, v in names.items() if v != auth]
        for alias in HISTORICAL_IDENTITY_ALIASES:
            if alias != auth and alias in names.values():
                leaks.append(f"historical_alias:{alias}")
        return leaks

    # --- session ---

    def on_hello(self, session_id: str, *, now_ms: int = 0) -> TurnSnapshot:
        self.turn.set_clock(now_ms)
        self.pcm.reset(reason=DiscardReason.SESSION_RESET)
        self.wake.reset()
        self.listen.reset()
        self.asr.reset_session()
        self.tts.reset()
        self._envelope = None
        self._intent = None
        self._llm_text = None
        self._vad_active = False
        self._frame_seq = 0
        self._last_activity_ms = now_ms
        self.last_fallback = None
        self._history.clear()
        return self.turn.on_hello(session_id)

    def on_wake(self, *, now_ms: int | None = None) -> WakeSnapshot:
        self._stamp(now_ms)
        if not self.turn.snapshot().session_id:
            raise V2Error("wake before hello")
        if not self.turn.snapshot().open:
            self.turn.open_turn()
        if self.listen.snapshot().conversation_open:
            # Repeated wake while live: isolate wake-sourced PCM only.
            # Re-blocking all PCM would mute the open conversation (Câm).
            snap = self.asr.snapshot()
            self.turn.emit(
                TimelineEventName.WAKE,
                asr_epoch=snap.asr_epoch,
                qwen_session_gen=snap.qwen_session_gen,
                detail=self.identity.greeting_text(),
            )
            return self.wake.snapshot()
        self.wake.start_wake()
        # Qwen ready must not open conversation.
        snap = self.asr.snapshot()
        self.turn.emit(
            TimelineEventName.WAKE,
            asr_epoch=snap.asr_epoch,
            qwen_session_gen=snap.qwen_session_gen,
            detail=self.identity.greeting_text(),
        )
        return self.wake.snapshot()

    def on_listen_start(self, *, now_ms: int | None = None) -> ListenSnapshot:
        """Authoritative transition that opens conversation audio."""
        self._stamp(now_ms)
        if not self.turn.snapshot().open:
            self.turn.open_turn()
        self._envelope = None
        self._intent = None
        self._llm_text = None
        self.listen.apply_listen_start_boundary()
        self.pcm.begin_turn_audio()
        self.pcm.discard_stale_and_wake_buffers()
        self.wake.apply_listen_start_boundary()
        asr = self.asr.snapshot()
        armed = self.pcm.arm_live_forward_after_wake_isolation(
            conversation_open=True,
            asr_ready=asr.ready,
        )
        flushed = self.pcm.flush_pending_if_live()
        if any(r.disposition == PcmDisposition.SENT for r in flushed):
            self._maybe_first_pcm(asr)
        self.turn.emit(
            TimelineEventName.LISTEN_START,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
            detail=f"post_flush_live={armed}",
        )
        return self.listen.snapshot()

    def on_listen_stop(self, *, now_ms: int | None = None) -> ListenSnapshot:
        self._stamp(now_ms)
        self.pcm.disarm()
        self.pcm.discard_pending(DiscardReason.CONVERSATION_CLOSED)
        return self.listen.close()

    def on_pcm(
        self,
        pcm: bytes,
        *,
        source: str = "unknown",
        now_ms: int | None = None,
    ) -> PcmRecord:
        self._stamp(now_ms)
        wake = self.wake.snapshot()
        listen = self.listen.snapshot()
        asr = self.asr.snapshot()
        src = source if source in ("wake", "conversation", "unknown") else "unknown"
        if wake.wake_pcm_blocked:
            src = "wake"
        self._frame_seq += 1
        frame = PcmFrame(
            frame_id=self._frame_seq,
            pcm=pcm,
            source=src,  # type: ignore[arg-type]
            epoch=asr.asr_epoch,
            t_ms=self.turn.now_ms,
        )
        rec = self.pcm.ingest(
            frame,
            wake_pcm_blocked=wake.wake_pcm_blocked,
            conversation_open=listen.conversation_open,
            user_visible_route_sends=self.sends_to_asr(),
            observe_only=self.observe_only(),
        )
        if rec.disposition == PcmDisposition.SENT:
            self._maybe_first_pcm(asr)
        self.pcm.assert_no_dead_append()
        return rec

    def on_vad_start(self, *, now_ms: int | None = None) -> None:
        self._stamp(now_ms)
        self._vad_active = True
        asr = self.asr.snapshot()
        self.turn.emit(
            TimelineEventName.VAD_START,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
        )

    def on_vad_end(self, *, now_ms: int | None = None) -> None:
        self._stamp(now_ms)
        self._vad_active = False
        asr = self.asr.snapshot()
        self.turn.emit(
            TimelineEventName.VAD_END,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
        )

    def on_asr_connect_start(self, *, now_ms: int | None = None) -> AsrSessionSnapshot:
        self._stamp(now_ms)
        snap = self.asr.connect_start()
        self.turn.emit(
            TimelineEventName.ASR_CONNECT_START,
            asr_epoch=snap.asr_epoch,
            qwen_session_gen=snap.qwen_session_gen,
        )
        return snap

    def on_asr_ready(self, *, now_ms: int | None = None) -> AsrSessionSnapshot:
        """READY does not open conversation. It may arm PCM only if listen already opened."""
        self._stamp(now_ms)
        snap = self.asr.mark_ready()
        self.turn.emit(
            TimelineEventName.ASR_READY,
            asr_epoch=snap.asr_epoch,
            qwen_session_gen=snap.qwen_session_gen,
        )
        listen = self.listen.snapshot()
        armed = self.pcm.arm_live_forward_after_wake_isolation(
            conversation_open=listen.conversation_open,
            asr_ready=True,
        )
        if armed:
            flushed = self.pcm.flush_pending_if_live()
            if any(r.disposition == PcmDisposition.SENT for r in flushed):
                self._maybe_first_pcm(snap)
        return snap

    def on_asr_disconnect(self, *, now_ms: int | None = None) -> AsrSessionSnapshot:
        self._stamp(now_ms)
        self.pcm.disarm()
        self.pcm.discard_pending(DiscardReason.STALE_EPOCH)
        return self.asr.disconnect()

    def on_asr_reconnect(self, *, now_ms: int | None = None) -> AsrSessionSnapshot:
        self._stamp(now_ms)
        self.pcm.disarm()
        self.pcm.discard_pending(DiscardReason.STALE_EPOCH)
        snap = self.asr.reconnect()
        self.turn.emit(
            TimelineEventName.ASR_RECONNECT,
            asr_epoch=snap.asr_epoch,
            qwen_session_gen=snap.qwen_session_gen,
        )
        return snap

    def on_asr_final(self, raw_asr: str, *, epoch: int, session_gen: int, now_ms: int | None = None) -> UtteranceEnvelope:
        self._stamp(now_ms)
        turn = self.turn.snapshot()
        if not turn.open:
            raise StaleSessionError("ASR final while turn not open")
        if not self.listen.snapshot().conversation_open:
            raise StaleSessionError("ASR final while conversation closed")
        if self._envelope is not None and self._envelope.turn_id == str(turn.turn_id):
            raise StaleSessionError("duplicate ASR final for this turn")
        self.asr.accept_final(epoch=epoch, session_gen=session_gen)
        asr = self.asr.snapshot()
        lang = self.language.snapshot()
        self.turn.emit(
            TimelineEventName.ASR_FINAL,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
        )
        sent_n = self.pcm.snapshot().turn_sent_count
        env = UtteranceEnvelope(
            session_id=str(turn.session_id),
            turn_id=str(turn.turn_id),
            raw_asr=raw_asr,
            resolved_utterance=raw_asr,
            primary_language=lang.primary_language,
            learning_languages=lang.learning_languages,
            learning_level=lang.learning_level,
            asr_language_hint=lang.asr_language_hint,
            conversation_language=lang.conversation_language,
            recent_history=tuple(self._history[-8:]),
            audio_metadata=AudioMetadata(
                duration_ms=max(0, sent_n * 60),
                silero_frames=sent_n,
                preroll_available=False,
                preroll_sent=False,
                qwen_window_ms=0,
            ),
            asr_metadata=AsrMetadata(
                provider="qwen",
                model="qwen-asr",
                session_gen=asr.qwen_session_gen,
                epoch=asr.asr_epoch,
            ),
        )
        self.turn.emit(
            TimelineEventName.RESOLVER_START,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
        )
        env = self.resolver.resolve(env, enabled=self.flags.resolver_enabled)
        self.turn.emit(
            TimelineEventName.RESOLVER_END,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
            detail=env.resolver_metadata.reason,
        )
        if env.resolved_utterance != env.raw_asr:
            raise V2Error("resolver NO-OP violated: resolved_utterance != raw_asr")
        self._envelope = env
        return env

    def on_intent(self, *, now_ms: int | None = None) -> IntentResult:
        self._stamp(now_ms)
        if self._envelope is None:
            raise V2Error("intent before ASR final")
        asr = self.asr.snapshot()
        turn = self.turn.snapshot()
        self.turn.emit(
            TimelineEventName.INTENT_START,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
        )
        text = self._envelope.resolved_utterance
        name = classify_intent(text)
        ctx = self.tools.compose(
            session_id=turn.session_id,
            turn_id=turn.turn_id,
            identity=self.identity.snapshot(),
            language=self.language.snapshot(),
            location=self.location.snapshot(),
        )
        failed = False
        fail_reason = None
        clarified = None
        if name in (IntentName.WEATHER, IntentName.LOCATION) and ctx.location_status != LocationStatus.KNOWN:
            failed = True
            fail_reason = "LOCATION_UNKNOWN"
            clarified = "LOCATION_UNKNOWN"
        result = IntentResult(
            name=name,
            utterance=text,
            tool_context=ctx,
            clarified=clarified,
            failed=failed,
            fail_reason=fail_reason,
        )
        self._intent = result
        self.turn.emit(
            TimelineEventName.INTENT_END,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
            detail=name.value,
        )
        return result

    def on_tool(self, *, now_ms: int | None = None) -> IntentResult:
        self._stamp(now_ms)
        if self._intent is None:
            raise V2Error("tool before intent")
        asr = self.asr.snapshot()
        self.turn.emit(
            TimelineEventName.TOOL_START,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
        )
        # Tools consume ToolContext only — no independent location derivation.
        self.turn.emit(
            TimelineEventName.TOOL_END,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
            detail=self._intent.fail_reason or "ok",
        )
        return self._intent

    def on_llm_start(self, *, now_ms: int | None = None) -> None:
        self._stamp(now_ms)
        asr = self.asr.snapshot()
        self.turn.emit(
            TimelineEventName.LLM_START,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
        )

    def on_llm_first_token(self, token: str, *, now_ms: int | None = None) -> None:
        self._stamp(now_ms)
        asr = self.asr.snapshot()
        self.turn.emit(
            TimelineEventName.LLM_FIRST_TOKEN,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
            detail=self.identity.llm_context_name(),
        )
        self._llm_text = token

    def on_llm_end(self, text: str, *, now_ms: int | None = None) -> str:
        self._stamp(now_ms)
        asr = self.asr.snapshot()
        # Identity must appear as owner name if the mock includes a name slot.
        self._llm_text = text
        self._history.append(text)
        self.turn.emit(
            TimelineEventName.LLM_END,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
        )
        return text

    def on_tts_start(self, *, now_ms: int | None = None) -> TtsPlaybackState:
        self._stamp(now_ms)
        if self.turn.snapshot().fallback_used:
            raise V2Error("V2 TTS suppressed after V1 fallback")
        if self.turn.snapshot().cancelled:
            raise V2Error("V2 TTS suppressed after cancel")
        asr = self.asr.snapshot()
        st = self.tts.transition(TtsPlaybackState.GENERATING, now_ms=self.turn.now_ms)
        self.turn.emit(
            TimelineEventName.TTS_START,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
            detail=self.identity.tts_facing_name(),
        )
        return st

    def on_tts_first_audio(self, *, now_ms: int | None = None) -> TtsPlaybackState:
        self._stamp(now_ms)
        self.tts.mark_provider_first_audio(self.turn.now_ms)
        self.tts.transition(TtsPlaybackState.QUEUED, now_ms=self.turn.now_ms)
        self.tts.transition(TtsPlaybackState.SENDING, now_ms=self.turn.now_ms)
        asr = self.asr.snapshot()
        self.turn.emit(
            TimelineEventName.TTS_FIRST_AUDIO,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
        )
        self.turn.mark_user_visible()
        return self.tts.snapshot().state

    def on_device_first_audio(self, *, now_ms: int | None = None) -> TtsPlaybackState:
        self._stamp(now_ms)
        self.tts.transition(TtsPlaybackState.PLAYING, now_ms=self.turn.now_ms)
        asr = self.asr.snapshot()
        self.turn.emit(
            TimelineEventName.DEVICE_FIRST_AUDIO,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
        )
        return self.tts.snapshot().state

    def on_tts_drain(self, *, now_ms: int | None = None) -> TtsPlaybackState:
        self._stamp(now_ms)
        self.tts.transition(TtsPlaybackState.DRAINING, now_ms=self.turn.now_ms)
        return self.tts.transition(TtsPlaybackState.IDLE, now_ms=self.turn.now_ms)

    def on_cancel(self, *, now_ms: int | None = None) -> TurnSnapshot:
        self._stamp(now_ms)
        self.pcm.discard_pending(DiscardReason.TURN_CANCELLED)
        self.pcm.disarm()
        self.listen.close()
        if self.tts.snapshot().state != TtsPlaybackState.IDLE:
            self.tts.interrupt()
            self.tts.transition(TtsPlaybackState.IDLE, now_ms=self.turn.now_ms)
        return self.turn.cancel()

    def on_idle_timeout(self, *, now_ms: int | None = None) -> TurnSnapshot:
        self._stamp(now_ms)
        asr = self.asr.snapshot()
        self.pcm.discard_pending(DiscardReason.IDLE_TIMEOUT)
        self.pcm.disarm()
        self.listen.close()
        self.turn.emit(
            TimelineEventName.IDLE_TIMEOUT,
            asr_epoch=asr.asr_epoch,
            qwen_session_gen=asr.qwen_session_gen,
        )
        if self.tts.snapshot().state not in (TtsPlaybackState.IDLE, TtsPlaybackState.INTERRUPTED):
            self.tts.interrupt()
            self.tts.transition(TtsPlaybackState.IDLE, now_ms=self.turn.now_ms)
        return self.turn.complete()

    def complete_turn(self, *, now_ms: int | None = None) -> TurnSnapshot:
        self._stamp(now_ms)
        if self.tts.snapshot().state == TtsPlaybackState.PLAYING:
            self.on_tts_drain(now_ms=now_ms)
        return self.turn.complete()

    def fail_before_user_visible(self, reason: str) -> FallbackDecision:
        turn = self.turn.snapshot()
        decision = self.fallback_policy.decide(
            enabled=self.flags.fallback_to_v1,
            user_visible_started=turn.user_visible_started,
            already_used=turn.fallback_used,
            reason=reason,
        )
        if decision.used:
            asr = self.asr.snapshot()
            self.turn.mark_fallback_used()
            self.turn.emit(
                TimelineEventName.FALLBACK_V1,
                asr_epoch=asr.asr_epoch,
                qwen_session_gen=asr.qwen_session_gen,
                detail=reason,
            )
            self.pcm.discard_pending(DiscardReason.TURN_CANCELLED)
            self.pcm.disarm()
            self.listen.close()
            if self.tts.snapshot().state != TtsPlaybackState.IDLE:
                self.tts.interrupt()
                self.tts.transition(TtsPlaybackState.IDLE, now_ms=self.turn.now_ms)
            self.turn.cancel()
        self.last_fallback = decision
        return decision

    def tick(self, now_ms: int) -> None:
        self.turn.set_clock(now_ms)
        if (
            self.listen.snapshot().conversation_open
            and self.config.idle_timeout_ms > 0
            and now_ms - self._last_activity_ms >= self.config.idle_timeout_ms
        ):
            self.on_idle_timeout(now_ms=now_ms)

    def run_text_turn(self, raw_asr: str, *, now_ms: int = 0) -> TurnResult:
        """Mock downstream after a captured raw_asr (no physical Stick)."""
        try:
            asr = self.asr.snapshot()
            env = self.on_asr_final(
                raw_asr, epoch=asr.asr_epoch, session_gen=asr.qwen_session_gen, now_ms=now_ms
            )
            intent = self.on_intent(now_ms=now_ms)
            self.on_tool(now_ms=now_ms)
            self.on_llm_start(now_ms=now_ms)
            name = self.identity.snapshot().assistant_name
            if intent.failed and intent.fail_reason == "LOCATION_UNKNOWN":
                text = f"{name}: LOCATION_UNKNOWN"
            else:
                text = f"{name}: {env.resolved_utterance}"
            self.on_llm_first_token(text[:8], now_ms=now_ms)
            self.on_llm_end(text, now_ms=now_ms)
            if self.sends_to_asr() or self.route() == V2Route.V2_PRIMARY:
                self.on_tts_start(now_ms=now_ms)
                self.on_tts_first_audio(now_ms=now_ms)
                self.on_device_first_audio(now_ms=now_ms)
                self.complete_turn(now_ms=now_ms)
            return TurnResult(
                envelope=env,
                intent=intent,
                llm_text=text,
                route=self.route(),
                fallback=None,
            )
        except (StaleSessionError, V2Error, UnsafeFallbackError) as exc:
            try:
                fb = self.fail_before_user_visible(type(exc).__name__)
            except UnsafeFallbackError:
                fb = None
            return TurnResult(
                envelope=self._envelope,
                intent=self._intent,
                llm_text=self._llm_text,
                route=self.route(),
                fallback=fb,
                error=str(exc),
            )

    def _maybe_first_pcm(self, asr: AsrSessionSnapshot) -> None:
        if not self.turn.timeline.has(TimelineEventName.FIRST_PCM_SENT):
            self.turn.emit(
                TimelineEventName.FIRST_PCM_SENT,
                asr_epoch=asr.asr_epoch,
                qwen_session_gen=asr.qwen_session_gen,
            )

    def _stamp(self, now_ms: int | None) -> None:
        if now_ms is not None:
            self.turn.set_clock(now_ms)
            self._last_activity_ms = now_ms


def classify_intent(text: str) -> IntentName:
    t = text.lower()
    if any(k in t for k in ("nhạc", "music", "baby", "shark", "visa này")):
        return IntentName.MUSIC
    if any(k in t for k in ("thời tiết", "weather")):
        return IntentName.WEATHER
    if any(k in t for k in ("ở đâu", "location", "vị trí")):
        return IntentName.LOCATION
    if any(k in t for k in ("tạm biệt", "goodbye")):
        return IntentName.GOODBYE
    return IntentName.CHAT
