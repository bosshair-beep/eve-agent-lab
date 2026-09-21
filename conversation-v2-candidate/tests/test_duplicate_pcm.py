from eve_conversation_v2.types import DiscardReason, PcmDisposition

from helpers import make_engine


def test_duplicate_pcm_not_sent_twice(live):
    first = live.on_pcm(b"a", source="conversation")
    assert first.disposition == PcmDisposition.SENT
    # Re-inject same frame_id via owner
    from eve_conversation_v2.owners_pcm import PcmFrame

    dup = PcmFrame(
        frame_id=first.frame_id,
        pcm=b"a",
        source="conversation",
        epoch=live.asr_snapshot().asr_epoch,
        t_ms=0,
    )
    rec = live.pcm.ingest(
        dup,
        wake_pcm_blocked=False,
        conversation_open=True,
        user_visible_route_sends=True,
    )
    assert rec.disposition == PcmDisposition.DISCARDED
    assert rec.reason == DiscardReason.DUPLICATE_FRAME
    sent = [r for r in live.pcm.records if r.frame_id == first.frame_id and r.disposition == PcmDisposition.SENT]
    assert len(sent) == 1


def test_no_append_without_send_dead_state(live):
    live.on_pcm(b"a", source="conversation")
    live.pcm.assert_no_dead_append()
    live.on_asr_disconnect()
    live.on_pcm(b"b", source="conversation")
    live.pcm.assert_no_dead_append()
