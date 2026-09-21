from eve_conversation_v2.baseline import RAW_ASR_KNOWN_EXAMPLES
from eve_conversation_v2.errors import RawAsrMutationError
from eve_conversation_v2.flags import FeatureFlags

from helpers import make_engine


def _final(e, text: str):
    e.on_hello("s")
    e.on_asr_ready()
    e.on_listen_start()
    e.on_vad_start()
    e.on_vad_end()
    env = e.on_asr_final(
        text,
        epoch=e.asr_snapshot().asr_epoch,
        session_gen=e.asr_snapshot().qwen_session_gen,
    )
    return env


def test_resolver_noop_identity():
    e = make_engine()
    env = _final(e, "xin chào")
    assert env.resolved_utterance == env.raw_asr == "xin chào"
    assert env.resolver_metadata.provider == "noop"
    assert env.resolver_metadata.enabled is False
    assert env.resolver_metadata.reason == "NO_OP_PASSTHROUGH"


def test_resolver_enabled_flag_still_noop():
    flags = FeatureFlags(
        conversation_v2_enabled=True,
        resolver_enabled=True,
        canary_device_ids=frozenset({"stick-canary-1"}),
    )
    e = make_engine(flags=flags)
    env = _final(e, "xin chào")
    assert env.resolved_utterance == env.raw_asr
    assert env.resolver_metadata.enabled is True
    assert env.resolver_metadata.provider == "noop"


def test_raw_asr_immutable_and_known_mishears_passthrough():
    e = make_engine()
    for intended, observed in RAW_ASR_KNOWN_EXAMPLES:
        env = _final(make_engine(), observed)
        assert env.raw_asr == observed
        assert env.resolved_utterance == observed
        assert env.raw_asr != intended or intended == observed
        try:
            env.mutate_raw_asr("hack")
            assert False, "should not mutate"
        except RawAsrMutationError:
            pass
