from eve_conversation_v2.errors import FallbackLoopError, UnsafeFallbackError
from eve_conversation_v2.flags import FeatureFlags, V2Route
from eve_conversation_v2.golden import CANARY_FLAGS

from helpers import make_engine


def test_canary_primary():
    e = make_engine(flags=CANARY_FLAGS, device_id="stick-canary-1")
    assert e.route() == V2Route.V2_PRIMARY


def test_enabled_without_canary_stays_v1():
    flags = FeatureFlags(conversation_v2_enabled=True, canary_device_ids=frozenset())
    e = make_engine(flags=flags, device_id="stick-other")
    assert e.route() == V2Route.V1_PRODUCTION


def test_shadow_plus_canary_is_primary():
    flags = FeatureFlags(
        conversation_v2_enabled=True,
        shadow_mode=True,
        canary_device_ids=frozenset({"stick-canary-1"}),
    )
    e = make_engine(flags=flags, device_id="stick-canary-1")
    assert e.route() == V2Route.V2_PRIMARY
    other = make_engine(flags=flags, device_id="stick-other")
    assert other.route() == V2Route.V2_SHADOW


def test_fallback_before_user_visible_once():
    e = make_engine()
    e.on_hello("s")
    d = e.fail_before_user_visible("mock_failure")
    assert d.used is True
    assert d.boundary == "BEFORE_USER_VISIBLE_OUTPUT"
    try:
        e.fail_before_user_visible("again")
        assert False, "loop"
    except FallbackLoopError:
        pass


def test_fallback_after_tts_forbidden():
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    e.on_listen_start()
    e.on_tts_start()
    e.on_tts_first_audio()
    try:
        e.fail_before_user_visible("too_late")
        assert False, "unsafe"
    except UnsafeFallbackError:
        pass
