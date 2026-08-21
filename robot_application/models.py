"""Public input and output models."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Event:
    event_type: str
    timestamp: float
    person_id: Optional[str] = None


@dataclass(frozen=True)
class Effect:
    effect_type: str
    value: str
    reason: str
