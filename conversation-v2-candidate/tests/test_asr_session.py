import pytest

from eve_conversation_v2.errors import StaleSessionError
from eve_conversation_v2.types import DiscardReason, PcmDisposition

from helpers import make_engine


def test_asr_reconnect_bumps_gen_keeps_conversation_open():
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    e.on_listen_start()
    gen1 = e.asr_snapshot().qwen_session_gen
    epoch1 = e.asr_snapshot().asr_epoch
    assert e.listen_snapshot().conversation_open is True
    e.on_asr_reconnect()
    snap = e.asr_snapshot()
    assert snap.qwen_session_gen == gen1 + 1
    assert snap.asr_epoch == epoch1 + 1
    assert snap.ready is False
    assert e.listen_snapshot().conversation_open is True
    assert e.pcm_snapshot().post_flush_live is False
    rec = e.on_pcm(b"x", source="conversation")
    assert rec.disposition == PcmDisposition.PENDING
    e.on_asr_ready()
    assert e.pcm_snapshot().post_flush_live is True


def test_stale_epoch_final_rejected():
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    e.on_listen_start()
    old_epoch = e.asr_snapshot().asr_epoch
    old_gen = e.asr_snapshot().qwen_session_gen
    e.on_asr_reconnect()
    e.on_asr_ready()
    with pytest.raises(StaleSessionError):
        e.on_asr_final("xin chào", epoch=old_epoch, session_gen=old_gen)


def test_reconnect_discards_pending_as_stale():
    e = make_engine()
    e.on_hello("s")
    e.on_listen_start()
    rec = e.on_pcm(b"x", source="conversation")
    assert rec.disposition == PcmDisposition.PENDING
    e.on_asr_reconnect()
    assert rec.frame_id in e.pcm_snapshot().discarded_ids
    reasons = [r.reason for r in e.pcm.records if r.frame_id == rec.frame_id]
    assert DiscardReason.STALE_EPOCH in reasons
