import pytest

from eve_conversation_v2.errors import ForbiddenLocationFallbackError, OwnershipError
from eve_conversation_v2.types import IntentName, LocationStatus

from helpers import make_engine


def test_default_location_unknown():
    e = make_engine()
    assert e.location_snapshot().status == LocationStatus.LOCATION_UNKNOWN
    assert e.location_snapshot().location is None


def test_chinese_fallback_rejected():
    e = make_engine()
    with pytest.raises(ForbiddenLocationFallbackError):
        e.location.set_known("广州", "legacy_weather")
    assert e.location_snapshot().status == LocationStatus.REJECTED_FALLBACK
    assert e.location_snapshot().location is None
    with pytest.raises(ForbiddenLocationFallbackError):
        e.location.set_known("广州市", "legacy")
    with pytest.raises(ForbiddenLocationFallbackError):
        e.location.set_known("GUANGZHOU", "legacy")


def test_weather_tool_clarifies_location_unknown():
    e = make_engine()
    e.on_hello("s")
    e.on_asr_ready()
    e.on_listen_start()
    e.on_asr_final(
        "thời tiết hôm nay",
        epoch=e.asr_snapshot().asr_epoch,
        session_gen=e.asr_snapshot().qwen_session_gen,
    )
    intent = e.on_intent()
    assert intent.name == IntentName.WEATHER
    assert intent.failed is True
    assert intent.fail_reason == "LOCATION_UNKNOWN"
    ctx = e.on_tool().tool_context
    assert ctx.location_status == LocationStatus.LOCATION_UNKNOWN
    assert ctx.location is None
    assert ctx.assistant_name == "Eve"
    assert ctx.device_id == "stick-canary-1"
    assert ctx.asr_language_hint == "vi"


def test_tool_context_not_foreign_writable():
    e = make_engine()
    with pytest.raises(OwnershipError):
        e.tools.write_foreign(location="广州")
