import pytest

from eve_conversation_v2.baseline import ASR_BASELINE, RAW_ASR_KNOWN_EXAMPLES
from eve_conversation_v2.flags import V2Route
from eve_conversation_v2.golden import GOLDEN_SCENARIOS, PRODUCTION_SAFE_FLAGS, SHADOW_FLAGS
from eve_conversation_v2.types import IntentName, LocationStatus, PcmDisposition, TimelineEventName

from helpers import make_engine


def _prep_live(e):
    e.on_hello("s")
    e.on_asr_ready()
    e.on_listen_start()
    return e


@pytest.mark.golden
def test_golden_registry_complete():
    names = {s.name for s in GOLDEN_SCENARIOS}
    assert names == {
        "NORMAL_WAKE",
        "NORMAL_VI_CHAT",
        "MUSIC_REQUEST",
        "WEATHER_REQUEST",
        "LOCATION_REQUEST",
        "SHORT_UTTERANCE",
        "IDLE_GOODBYE",
        "REPEATED_WAKE",
        "ASR_RECONNECT",
    }


@pytest.mark.golden
def test_normal_wake():
    e = _prep_live(make_engine())
    # re-hello path for clean wake
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    e.on_wake()
    rec = e.on_pcm(b"w", source="wake")
    v1_expected = "wake PCM never sent to conversational ASR"
    v2_result = rec.disposition.value
    diff = v2_result != "SENT"
    assert diff  # discarded, matches V1 expected isolation
    assert rec.disposition == PcmDisposition.DISCARDED


@pytest.mark.golden
def test_normal_vi_chat():
    e = _prep_live(make_engine())
    e.on_pcm(b"x", source="conversation")
    e.on_vad_start()
    e.on_vad_end()
    result = e.run_text_turn("xin chào")
    assert result.error is None
    assert result.envelope.asr_language_hint == ASR_BASELINE.language == "vi"
    assert result.envelope.resolved_utterance == result.envelope.raw_asr
    assert result.llm_text.startswith("Eve:")
    assert e.leak_check_identity() == []
    names = e.turn.timeline.names()
    for required in (
        "HELLO",
        "ASR_READY",
        "LISTEN_START",
        "VAD_START",
        "VAD_END",
        "ASR_FINAL",
        "RESOLVER_START",
        "RESOLVER_END",
        "INTENT_START",
        "INTENT_END",
        "LLM_START",
        "TTS_START",
        "TURN_END",
    ):
        assert required in names


@pytest.mark.golden
def test_music_request_passthrough_raw_asr():
    intended, observed = RAW_ASR_KNOWN_EXAMPLES[0]
    e = _prep_live(make_engine())
    result = e.run_text_turn(observed)
    assert result.envelope.raw_asr == observed
    assert result.envelope.resolved_utterance == observed
    assert result.envelope.raw_asr != intended
    assert result.intent.name == IntentName.MUSIC


@pytest.mark.golden
def test_weather_and_location_unknown():
    e = _prep_live(make_engine())
    weather = e.run_text_turn("thời tiết hôm nay")
    assert weather.intent.fail_reason == "LOCATION_UNKNOWN"
    assert weather.intent.tool_context.location_status == LocationStatus.LOCATION_UNKNOWN
    assert "广州" not in (weather.llm_text or "")
    assert "未知位置" not in (weather.llm_text or "")
    e2 = _prep_live(make_engine())
    loc = e2.run_text_turn("tôi đang ở đâu")
    assert loc.intent.name == IntentName.LOCATION
    assert loc.intent.fail_reason == "LOCATION_UNKNOWN"


@pytest.mark.golden
def test_short_utterance():
    e = _prep_live(make_engine())
    result = e.run_text_turn("ạ")
    assert result.envelope.raw_asr == "ạ"
    assert result.envelope.resolved_utterance == "ạ"


@pytest.mark.golden
def test_idle_goodbye():
    e = make_engine(idle_timeout_ms=100)
    e.on_hello("s", now_ms=0)
    e.on_listen_start(now_ms=1)
    e.tick(now_ms=500)
    assert e.turn.timeline.has(TimelineEventName.IDLE_TIMEOUT)
    assert e.turn_snapshot().completed is True


@pytest.mark.golden
def test_repeated_wake():
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    e.on_wake()
    a = e.on_pcm(b"w1", source="wake")
    e.on_listen_start()
    e.on_wake()
    b = e.on_pcm(b"w2", source="wake")
    assert a.disposition == PcmDisposition.DISCARDED
    assert b.disposition == PcmDisposition.DISCARDED
    assert a.frame_id not in e.pcm_snapshot().sent_ids
    assert b.frame_id not in e.pcm_snapshot().sent_ids


@pytest.mark.golden
def test_asr_reconnect_golden():
    e = _prep_live(make_engine())
    open_before = e.listen_snapshot().conversation_open
    g = e.asr_snapshot().qwen_session_gen
    e.on_asr_reconnect()
    assert e.listen_snapshot().conversation_open == open_before
    assert e.asr_snapshot().qwen_session_gen == g + 1


@pytest.mark.golden
def test_production_flags_do_not_send_pcm():
    e = make_engine(flags=PRODUCTION_SAFE_FLAGS, device_id="any")
    assert e.route() == V2Route.V1_PRODUCTION
    e.on_hello("s")
    e.on_asr_ready()
    e.on_listen_start()
    rec = e.on_pcm(b"x", source="conversation")
    assert rec.disposition == PcmDisposition.DISCARDED
    assert rec.reason.value == "ENGINE_NOT_PRIMARY"


@pytest.mark.golden
def test_shadow_observe_only():
    e = make_engine(flags=SHADOW_FLAGS, device_id="any")
    assert e.route() == V2Route.V2_SHADOW
    e.on_hello("s")
    e.on_asr_ready()
    e.on_listen_start()
    rec = e.on_pcm(b"x", source="conversation")
    assert rec.reason.value == "SHADOW_OBSERVE_ONLY"
