from __future__ import annotations

from eve_conversation_v2.engine import ConversationEngineV2, EngineConfig
from eve_conversation_v2.golden import CANARY_FLAGS


def make_engine(
    *,
    device_id: str = "stick-canary-1",
    name: str = "Eve",
    flags=CANARY_FLAGS,
    **kwargs,
) -> ConversationEngineV2:
    return ConversationEngineV2(
        EngineConfig(
            assistant_name=name,
            identity_source="candidate_config",
            device_id=device_id,
            flags=flags,
            **kwargs,
        )
    )
