"""ASR / TOOL / TTS investigator contract tests."""

from eve_conversation_v2.types import TimelineEventName

from helpers import make_engine


def test_asr_investigator_invariants(live):
    rec = live.on_pcm(b"x", source="conversation")
    assert rec.disposition.value in {"SENT", "DISCARDED", "PENDING"}
    if rec.disposition.value == "DISCARDED":
        assert rec.reason is not None
    live.pcm.assert_no_dead_append()
    assert live.asr_snapshot().ready is True
    # Qwen ready did not own conversation_open
    live.on_asr_disconnect()
    assert live.listen_snapshot().conversation_open is True


def test_tool_investigator_context_propagation():
    e = make_engine(child_id="child-9", timezone="Asia/Ho_Chi_Minh")
    e.on_hello("s")
    e.on_asr_ready()
    e.on_listen_start()
    e.on_asr_final(
        "xin chào",
        epoch=e.asr_snapshot().asr_epoch,
        session_gen=e.asr_snapshot().qwen_session_gen,
    )
    ctx = e.on_intent().tool_context
    assert ctx.child_id == "child-9"
    assert ctx.timezone == "Asia/Ho_Chi_Minh"
    assert ctx.conversation_language == "vi"
    assert ctx.assistant_name == e.identity.display_name()
    assert ctx.session_id == str(e.turn_snapshot().session_id)
    assert ctx.turn_id == str(e.turn_snapshot().turn_id)


def test_tts_investigator_telemetry_distinct():
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    e.on_listen_start()
    e.on_tts_start(now_ms=10)
    e.on_tts_first_audio(now_ms=20)
    e.on_device_first_audio(now_ms=30)
    tel = e.tts.telemetry
    assert tel.provider_first_audio_ms == 20
    assert tel.queue_enqueue_ms == 20
    assert tel.first_binary_send_ms == 20
    assert tel.device_playback_state == "PLAYING"
    assert e.turn.timeline.has(TimelineEventName.TTS_FIRST_AUDIO)
    assert e.turn.timeline.has(TimelineEventName.DEVICE_FIRST_AUDIO)
