"""Public input and output models."""

from dataclasses import dataclass
from typing import Optional, Tuple, TypedDict


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


class Snapshot(TypedDict):
    """Public, detached view returned by ``RobotApplication.snapshot``."""

    present_person_ids: Tuple[Optional[str], ...]
    person_present: bool
    reception_active: bool
    conversation_active: bool
    meeting_active: bool
    absence_started_at: Optional[float]
    farewell_sent: bool
    absence_timeout_s: float
