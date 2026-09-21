from eve_conversation_v2.types import DiscardReason, PcmDisposition, TimelineEventName

from helpers import make_engine


def test_listen_start_arms_forward_when_asr_ready():
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    e.on_wake()
    e.on_pcm(b"wake", source="wake")
    e.on_listen_start()
    assert e.listen_snapshot().conversation_open is True
    assert e.wake_snapshot().wake_pcm_blocked is False
    assert e.pcm_snapshot().post_flush_live is True
    rec = e.on_pcm(b"hi", source="conversation")
    assert rec.disposition == PcmDisposition.SENT
    assert e.turn.timeline.has(TimelineEventName.LISTEN_START)
    assert e.turn.timeline.has(TimelineEventName.FIRST_PCM_SENT)


def test_listen_start_discards_stale_and_wake_buffers():
    e = make_engine()
    e.on_hello("s")
    e.on_wake()
    e.on_pcm(b"wake-buf", source="wake")
    e.on_listen_start()
    sent_from_wake = [r for r in e.pcm.records if r.source == "wake" and r.disposition == PcmDisposition.SENT]
    assert sent_from_wake == []
    discarded = [r for r in e.pcm.records if r.reason == DiscardReason.WAKE_ISOLATION]
    assert discarded
