from helpers import make_engine

import pytest

from eve_conversation_v2.engine import ConversationEngineV2


@pytest.fixture
def engine() -> ConversationEngineV2:
    e = make_engine()
    e.on_hello("sess-1", now_ms=0)
    return e


@pytest.fixture
def live(engine: ConversationEngineV2) -> ConversationEngineV2:
    engine.on_asr_connect_start(now_ms=1)
    engine.on_asr_ready(now_ms=2)
    engine.on_listen_start(now_ms=3)
    return engine
