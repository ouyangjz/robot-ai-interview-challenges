"""Internal mutable state owned by one application instance."""

from dataclasses import dataclass, field
from typing import Optional, Set


@dataclass(slots=True)
class _ApplicationState:
    """State container created and owned by one ``RobotApplication``.

    The leading underscore makes this an implementation detail rather than a
    public model. No state object or mutable member is shared between instances.
    """

    present_person_ids: Set[Optional[str]] = field(default_factory=set)
    reception_active: bool = False
    conversation_active: bool = False
    meeting_active: bool = False
    absence_started_at: Optional[float] = None
    farewell_sent: bool = False

    @property
    def person_present(self) -> bool:
        return bool(self.present_person_ids)

    @property
    def output_suppressed(self) -> bool:
        return self.conversation_active or self.meeting_active
