from eve_conversation_v2.types import DiscardReason, PcmDisposition

from helpers import make_engine


def test_wake_pcm_never_sent_even_if_asr_ready():
    e = make_engine()
    e.on_hello("s", now_ms=0)
    e.on_asr_ready(now_ms=1)
    e.on_wake(now_ms=2)
    rec = e.on_pcm(b"\x00\x01", source="wake", now_ms=3)
    assert rec.disposition == PcmDisposition.DISCARDED
    assert rec.reason == DiscardReason.WAKE_ISOLATION
    assert rec.frame_id not in e.pcm_snapshot().sent_ids
    assert e.listen_snapshot().conversation_open is False
    assert e.pcm_snapshot().post_flush_live is False


def test_wake_does_not_open_conversation():
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    e.on_wake()
    rec = e.on_pcm(b"x", source="conversation")
    assert rec.reason == DiscardReason.WAKE_ISOLATION
    assert e.wake_snapshot().wake_pcm_blocked is True
