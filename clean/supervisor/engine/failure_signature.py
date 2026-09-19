"""Normalized failure signatures. Prose and extra keys cannot mint a new identity."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SIGNATURE_FIELDS = ("layer", "test_case", "assertion", "observed", "source")


def _norm_value(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    return " ".join(text.split())


def normalize_failure_signature(payload: Mapping[str, Any] | None) -> dict[str, str]:
    src = payload or {}
    return {field: _norm_value(src.get(field)) for field in SIGNATURE_FIELDS}


def canonical_failure_json(payload: Mapping[str, Any] | None) -> str:
    normalized = normalize_failure_signature(payload)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def signature_hash(payload: Mapping[str, Any] | None) -> str:
    return hashlib.sha256(canonical_failure_json(payload).encode("utf-8")).hexdigest()


def describe_signature(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized = normalize_failure_signature(payload)
    return {
        "normalized": normalized,
        "canonical": canonical_failure_json(payload),
        "signature_hash": signature_hash(payload),
    }
