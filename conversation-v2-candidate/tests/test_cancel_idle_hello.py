from eve_conversation_v2.types import DiscardReason, PcmDisposition, TimelineEventName

from helpers import make_engine


def test_turn_cancel_discards_pending():
    e = make_engine()
    e.on_hello("s")
    e.on_listen_start()
    rec = e.on_pcm(b"x", source="conversation")
    assert rec.disposition == PcmDisposition.PENDING
    e.on_cancel()
    assert rec.frame_id in e.pcm_snapshot().discarded_ids
    assert e.turn.timeline.has(TimelineEventName.TURN_CANCEL)
    assert e.pcm_snapshot().post_flush_live is False


def test_idle_timeout():
    e = make_engine(idle_timeout_ms=1000)
    e.on_hello("s", now_ms=0)
    e.on_listen_start(now_ms=10)
    rec = e.on_pcm(b"x", source="conversation", now_ms=20)
    e.tick(now_ms=2000)
    assert e.turn.timeline.has(TimelineEventName.IDLE_TIMEOUT)
    assert e.turn.timeline.has(TimelineEventName.TURN_END)
    assert rec.frame_id in e.pcm_snapshot().discarded_ids
    assert e.listen_snapshot().conversation_open is False


def test_new_hello_session_recovery_rejects_stale():
    e = make_engine()
    e.on_hello("s1", now_ms=0)
    e.on_asr_ready()
    e.on_listen_start()
    old_epoch = e.asr_snapshot().asr_epoch
    old_gen = e.asr_snapshot().qwen_session_gen
    e.on_pcm(b"old", source="conversation")
    e.on_hello("s2", now_ms=50)
    assert e.turn_snapshot().session_id == "s2"
    assert e.asr_snapshot().asr_epoch != old_epoch
    assert e.listen_snapshot().conversation_open is False
    rec = e.on_pcm(b"new", source="conversation")
    assert rec.reason in (DiscardReason.CONVERSATION_CLOSED, DiscardReason.ENGINE_NOT_PRIMARY)
    import pytest
    from eve_conversation_v2.errors import StaleSessionError

    e.on_asr_ready()
    e.on_listen_start()
    with pytest.raises(StaleSessionError):
        e.on_asr_final("hi", epoch=old_epoch, session_gen=old_gen)
