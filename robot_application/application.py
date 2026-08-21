"""Application service that applies reception rules to incoming events."""

import math
from numbers import Real
from typing import List

from .effects import farewell_effects, welcome_effects
from .event_types import (
    ALL_EVENT_TYPES,
    CONVERSATION_ENDED,
    CONVERSATION_STARTED,
    MEETING_ENDED,
    MEETING_STARTED,
    PERSON_ENTERED,
    PERSON_LEFT,
    TICK,
)
from .models import Effect, Event, Snapshot
from .state import _ApplicationState


class RobotApplication:
    """Owns reception state and turns one event into zero or more effects.

    Effects describe intent only. Adapters outside this package are responsible
    for executing speech or robot actions.
    """

    def __init__(self, absence_timeout_s: float = 10.0):
        if (
            not isinstance(absence_timeout_s, Real)
            or isinstance(absence_timeout_s, bool)
            or not math.isfinite(float(absence_timeout_s))
            or absence_timeout_s < 0
        ):
            raise ValueError("absence_timeout_s must be a finite non-negative number")

        self._absence_timeout_s = float(absence_timeout_s)
        self._state = _ApplicationState()

    def handle_event(self, event: Event) -> List[Effect]:
        """Apply one event and return only effects created by that event."""
        self._validate_event(event)

        if event.event_type == PERSON_ENTERED:
            return self._handle_person_entered(event)
        if event.event_type == PERSON_LEFT:
            return self._handle_person_left(event)
        if event.event_type == CONVERSATION_STARTED:
            self._state.conversation_active = True
        elif event.event_type == CONVERSATION_ENDED:
            self._state.conversation_active = False
        elif event.event_type == MEETING_STARTED:
            self._state.meeting_active = True
        elif event.event_type == MEETING_ENDED:
            self._state.meeting_active = False
        elif event.event_type == TICK:
            return self._handle_tick(event)

        return []

    def snapshot(self) -> Snapshot:
        """Return an isolated, serializable view of current state.

        The returned dictionary is newly allocated and contains no mutable
        reference owned by the application.
        """
        person_ids = tuple(
            sorted(
                self._state.present_person_ids,
                key=lambda value: (value is not None, "" if value is None else value),
            )
        )
        return {
            "present_person_ids": person_ids,
            "person_present": self._state.person_present,
            "reception_active": self._state.reception_active,
            "conversation_active": self._state.conversation_active,
            "meeting_active": self._state.meeting_active,
            "absence_started_at": self._state.absence_started_at,
            "farewell_sent": self._state.farewell_sent,
            "absence_timeout_s": self._absence_timeout_s,
        }

    def _handle_person_entered(self, event: Event) -> List[Effect]:
        was_empty = not self._state.person_present
        self._state.present_person_ids.add(event.person_id)

        if was_empty and self._state.reception_active:
            # A return before departure confirmation continues the same cycle.
            self._state.absence_started_at = None

        if self._state.reception_active:
            return []

        self._state.reception_active = True
        self._state.farewell_sent = False

        if self._state.output_suppressed:
            return []
        return welcome_effects()

    def _handle_person_left(self, event: Event) -> List[Effect]:
        # Duplicate or stale leave events do not restart the absence timer.
        if event.person_id not in self._state.present_person_ids:
            return []

        self._state.present_person_ids.remove(event.person_id)
        if self._state.person_present:
            return []

        self._state.absence_started_at = float(event.timestamp)
        self._state.farewell_sent = False
        return []

    def _handle_tick(self, event: Event) -> List[Effect]:
        absence_started_at = self._state.absence_started_at
        if (
            not self._state.reception_active
            or self._state.person_present
            or absence_started_at is None
            or event.timestamp - absence_started_at < self._absence_timeout_s
        ):
            return []

        # Confirm the departure even when output is suppressed. This prevents a
        # later event from replaying an effect that was due during an interaction.
        self._state.reception_active = False
        self._state.absence_started_at = None

        if self._state.output_suppressed:
            self._state.farewell_sent = False
            return []

        self._state.farewell_sent = True
        return farewell_effects()

    @staticmethod
    def _validate_event(event: Event) -> None:
        if not isinstance(event, Event):
            raise TypeError("event must be an Event instance")
        if event.event_type not in ALL_EVENT_TYPES:
            raise ValueError(f"unsupported event_type: {event.event_type!r}")
        if (
            not isinstance(event.timestamp, Real)
            or isinstance(event.timestamp, bool)
            or not math.isfinite(float(event.timestamp))
        ):
            raise ValueError("event timestamp must be a finite number")
