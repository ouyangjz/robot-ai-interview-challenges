"""Effect factories keep user-facing output choices out of state transitions."""

from typing import List

from .models import Effect


def welcome_effects() -> List[Effect]:
    reason = "first entry in reception cycle"
    return [
        Effect(effect_type="ROBOT_ACTION", value="wave_hand", reason=reason),
        Effect(effect_type="SPEECH", value="欢迎光临", reason=reason),
    ]


def farewell_effects() -> List[Effect]:
    return [
        Effect(
            effect_type="SPEECH",
            value="欢迎下次光临",
            reason="absence timeout reached",
        )
    ]
