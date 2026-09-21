"""Isolated Conversation/Core V2 candidate.

Not production. Do not import from live eve.ai runtime.
Integration requires GATE-V2-INTEGRATE = PENDING_HUMAN_SNAPSHOT_AND_APPROVAL.
"""

from .baseline import ASR_BASELINE, WORK_ID
from .engine import ConversationEngineV2
from .flags import FeatureFlags, V2Route
from .version import V2_VERSION

__all__ = [
    "ASR_BASELINE",
    "ConversationEngineV2",
    "FeatureFlags",
    "V2Route",
    "V2_VERSION",
    "WORK_ID",
]
