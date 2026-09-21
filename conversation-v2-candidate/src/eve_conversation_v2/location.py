"""LOCATION_OWNER — LOCATION_UNKNOWN is first-class. No silent Chinese city fallback."""

from __future__ import annotations

from dataclasses import dataclass

from .baseline import FORBIDDEN_LOCATION_FALLBACKS
from .errors import ForbiddenLocationFallbackError, OwnershipError
from .types import LocationStatus


@dataclass(frozen=True)
class LocationSnapshot:
    status: LocationStatus
    location: str | None
    source: str
    rejected_value: str | None = None


class LocationOwner:
    OWNER = "LOCATION_OWNER"

    def __init__(self) -> None:
        self._snapshot = LocationSnapshot(
            status=LocationStatus.LOCATION_UNKNOWN,
            location=None,
            source="init",
        )

    def snapshot(self) -> LocationSnapshot:
        return self._snapshot

    def set_known(self, location: str, source: str) -> LocationSnapshot:
        value = (location or "").strip()
        if not value:
            return self.set_unknown(source=source, rejected=location)
        if value in FORBIDDEN_LOCATION_FALLBACKS:
            self._snapshot = LocationSnapshot(
                status=LocationStatus.REJECTED_FALLBACK,
                location=None,
                source=source,
                rejected_value=value,
            )
            raise ForbiddenLocationFallbackError(
                f"refusing to authorize location fallback {value!r}; LOCATION_UNKNOWN"
            )
        self._snapshot = LocationSnapshot(
            status=LocationStatus.KNOWN,
            location=value,
            source=source,
        )
        return self._snapshot

    def set_unknown(self, *, source: str, rejected: str | None = None) -> LocationSnapshot:
        self._snapshot = LocationSnapshot(
            status=LocationStatus.LOCATION_UNKNOWN,
            location=None,
            source=source,
            rejected_value=rejected,
        )
        return self._snapshot

    def write_foreign(self, *_args, **_kwargs) -> None:
        raise OwnershipError(f"only {self.OWNER} may write location")
