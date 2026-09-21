from eve_conversation_v2.types import DiscardReason, PcmDisposition

from helpers import make_engine


def test_ready_before_listen_does_not_arm_or_send():
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    assert e.asr_snapshot().ready is True
    assert e.listen_snapshot().conversation_open is False
    assert e.pcm_snapshot().post_flush_live is False
    rec = e.on_pcm(b"x", source="conversation")
    assert rec.disposition == PcmDisposition.DISCARDED
    assert rec.reason == DiscardReason.CONVERSATION_CLOSED


def test_ready_after_listen_flushes_pending_once():
    e = make_engine()
    e.on_hello("s")
    e.on_listen_start()
    assert e.pcm_snapshot().post_flush_live is False
    p1 = e.on_pcm(b"a", source="conversation")
    p2 = e.on_pcm(b"b", source="conversation")
    assert p1.disposition == PcmDisposition.PENDING
    assert p2.disposition == PcmDisposition.PENDING
    e.on_asr_connect_start()
    e.on_asr_ready()
    assert e.pcm_snapshot().post_flush_live is True
    snap = e.pcm_snapshot()
    assert p1.frame_id in snap.sent_ids
    assert p2.frame_id in snap.sent_ids
    # exactly once
    sent = [r for r in e.pcm.records if r.disposition == PcmDisposition.SENT]
    assert {r.frame_id for r in sent} == {p1.frame_id, p2.frame_id}
    assert len(sent) == 2
