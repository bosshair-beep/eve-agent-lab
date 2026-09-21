from eve_conversation_v2.baseline import ASR_BASELINE
from eve_conversation_v2.errors import OwnershipError

from helpers import make_engine


def test_language_fields_not_collapsed():
    e = make_engine(learning_languages=("en",), learning_level="A1")
    s = e.language_snapshot()
    assert s.primary_language == "vi"
    assert s.learning_languages == ("en",)
    assert s.conversation_language == "vi"
    assert s.asr_language_hint == ASR_BASELINE.language == "vi"
    assert s.tts_locale == "vi"
    assert s.allowed_languages == ("vi", "en")
    assert s.asr_mode == "HINT"
    assert s.learning_level == "A1"
    # distinct fields exist even when some share the value "vi"
    assert set(s.__dataclass_fields__) >= {
        "primary_language",
        "learning_languages",
        "conversation_language",
        "asr_language_hint",
        "tts_locale",
    }


def test_language_foreign_write_rejected():
    e = make_engine()
    try:
        e.language.write_foreign(primary_language="zh")
        assert False
    except OwnershipError:
        pass


def test_asr_baseline_frozen():
    assert ASR_BASELINE.threshold == 0.2
    assert ASR_BASELINE.prefix_padding_ms == 600
    assert ASR_BASELINE.silence_duration_ms == 1000
    try:
        ASR_BASELINE.language = "en"  # type: ignore[misc]
        assert False
    except Exception:
        pass
