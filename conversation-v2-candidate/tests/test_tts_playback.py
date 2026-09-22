import pytest

from eve_conversation_v2.errors import V2Error
from eve_conversation_v2.types import TtsPlaybackState

from helpers import make_engine


def test_tts_legal_path(live):
    live.on_tts_start()
    assert live.tts_snapshot().state == TtsPlaybackState.GENERATING
    live.on_tts_first_audio()
    assert live.tts_snapshot().state == TtsPlaybackState.SENDING
    assert live.tts.telemetry.provider_first_audio_ms is not None
    assert live.tts.telemetry.first_binary_send_ms is not None
    live.on_device_first_audio()
    assert live.tts_snapshot().state == TtsPlaybackState.PLAYING
    live.on_tts_drain()
    assert live.tts_snapshot().state == TtsPlaybackState.IDLE
    tel = live.tts.telemetry
    assert tel.queue_enqueue_ms is not None
    assert tel.queue_dequeue_ms is not None


def test_illegal_tts_transition_rejected(live):
    with pytest.raises(V2Error):
        live.tts.transition(TtsPlaybackState.PLAYING, now_ms=0)


def test_interrupt_from_playing(live):
    live.on_tts_start()
    live.on_tts_first_audio()
    live.on_device_first_audio()
    live.on_cancel()
    assert live.tts_snapshot().state == TtsPlaybackState.IDLE
    assert live.turn_snapshot().cancelled is True
