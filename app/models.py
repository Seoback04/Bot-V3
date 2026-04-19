"""Runtime constants and small value objects."""
from __future__ import annotations

from dataclasses import dataclass


LOW_CONFIDENCE_THRESHOLD: float = 0.6
HIGH_CONFIDENCE_THRESHOLD: float = 0.85


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 2.0


DEFAULT_RETRY = RetryPolicy()
