"""DEVIL — hunt races, double writers, leaks, fallback loops, resolver drift."""

from __future__ import annotations

import pytest

from eve_conversation_v2.baseline import FORBIDDEN_LOCATION_FALLBACKS
from eve_conversation_v2.errors import ForbiddenLocationFallbackError, StaleSessionError
from eve_conversation_v2.types import DiscardReason, PcmDisposition, TimelineEventName

from helpers import make_engine


@pytest.mark.devil
def test_asr_ready_cannot_open_conversation():
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    assert e.listen_snapshot().conversation_open is False
    rec = e.on_pcm(b"x", source="conversation")
    assert rec.disposition != PcmDisposition.SENT


@pytest.mark.devil
def test_wake_pcm_tagged_conversation_still_blocked():
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    e.on_wake()
    rec = e.on_pcm(b"x", source="conversation")
    assert rec.reason == DiscardReason.WAKE_ISOLATION


@pytest.mark.devil
def test_source_wake_after_listen_still_discarded():
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    e.on_listen_start()
    rec = e.on_pcm(b"x", source="wake")
    assert rec.disposition == PcmDisposition.DISCARDED
    assert rec.reason == DiscardReason.WAKE_ISOLATION


@pytest.mark.devil
def test_stale_final_cannot_enter_new_turn():
    e = make_engine()
    e.on_hello("s1")
    e.on_asr_ready()
    e.on_listen_start()
    epoch, gen = e.asr_snapshot().asr_epoch, e.asr_snapshot().qwen_session_gen
    e.on_hello("s2")
    e.on_asr_ready()
    e.on_listen_start()
    with pytest.raises(StaleSessionError):
        e.on_asr_final("old", epoch=epoch, session_gen=gen)


@pytest.mark.devil
def test_resolver_cannot_change_raw_or_resolved():
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    e.on_listen_start()
    env = e.on_asr_final(
        "visa này",
        epoch=e.asr_snapshot().asr_epoch,
        session_gen=e.asr_snapshot().qwen_session_gen,
    )
    assert env.raw_asr == env.resolved_utterance == "visa này"


@pytest.mark.devil
def test_chinese_location_cannot_become_authoritative():
    e = make_engine()
    for bad in FORBIDDEN_LOCATION_FALLBACKS:
        try:
            e.location.set_known(bad, "devil")
            assert False, bad
        except ForbiddenLocationFallbackError:
            assert e.location_snapshot().location is None


@pytest.mark.devil
def test_timeline_correlation_ids():
    e = make_engine()
    e.on_hello("sess-z")
    e.on_asr_ready()
    e.on_wake()
    e.on_listen_start()
    e.on_pcm(b"x", source="conversation")
    for ev in e.turn.timeline.events:
        assert ev.session_id == "sess-z"
        if ev.name in (
            TimelineEventName.HELLO,
            TimelineEventName.ASR_CONNECT_START,
            TimelineEventName.ASR_READY,
        ):
            continue
        assert ev.turn_id
        assert ev.asr_epoch == e.asr_snapshot().asr_epoch
        assert ev.qwen_session_gen == e.asr_snapshot().qwen_session_gen


@pytest.mark.devil
def test_no_pcm_logged_in_timeline_detail():
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    e.on_listen_start()
    secret = b"PCM_SECRET_BYTES"
    e.on_pcm(secret, source="conversation")
    blob = " ".join(ev.detail for ev in e.turn.timeline.events)
    assert "PCM_SECRET_BYTES" not in blob
    assert secret.decode("latin1") not in blob
