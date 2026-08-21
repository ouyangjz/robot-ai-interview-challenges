import unittest

from robot_application.application import RobotApplication
from robot_application.models import Effect, Event


def event(event_type, timestamp, person_id=None):
    return Event(event_type=event_type, timestamp=timestamp, person_id=person_id)


class RobotApplicationTests(unittest.TestCase):
    def test_first_entry_welcomes_and_duplicate_entry_does_nothing(self):
        app = RobotApplication()

        effects = app.handle_event(event("PERSON_ENTERED", 0, "p1"))

        self.assertEqual(
            effects,
            [
                Effect("ROBOT_ACTION", "wave_hand", "first entry in reception cycle"),
                Effect("SPEECH", "欢迎光临", "first entry in reception cycle"),
            ],
        )
        self.assertEqual(app.handle_event(event("PERSON_ENTERED", 1, "p1")), [])

    def test_required_example_sequence(self):
        app = RobotApplication()
        sequence = [
            ("PERSON_ENTERED", 0),
            ("PERSON_ENTERED", 1),
            ("CONVERSATION_STARTED", 2),
            ("PERSON_ENTERED", 3),
            ("CONVERSATION_ENDED", 4),
            ("PERSON_LEFT", 5),
            ("TICK", 14),
            ("TICK", 15),
            ("TICK", 16),
            ("PERSON_ENTERED", 20),
        ]

        outputs = [app.handle_event(event(kind, timestamp)) for kind, timestamp in sequence]

        self.assertEqual([len(output) for output in outputs], [2, 0, 0, 0, 0, 0, 0, 1, 0, 2])
        self.assertEqual(outputs[0][0].value, "wave_hand")
        self.assertEqual(outputs[0][1].value, "欢迎光临")
        self.assertEqual(outputs[7][0].value, "欢迎下次光临")
        self.assertEqual(outputs[9][0].value, "wave_hand")

    def test_conversation_suppresses_welcome_without_replaying_it(self):
        app = RobotApplication()

        self.assertEqual(app.handle_event(event("CONVERSATION_STARTED", 0)), [])
        self.assertEqual(app.handle_event(event("PERSON_ENTERED", 1)), [])
        self.assertEqual(app.handle_event(event("CONVERSATION_ENDED", 2)), [])
        self.assertEqual(app.handle_event(event("PERSON_ENTERED", 3)), [])

    def test_meeting_suppresses_due_farewell_without_replaying_it(self):
        app = RobotApplication()
        app.handle_event(event("PERSON_ENTERED", 0))
        app.handle_event(event("PERSON_LEFT", 1))

        self.assertEqual(app.handle_event(event("MEETING_STARTED", 2)), [])
        self.assertEqual(app.handle_event(event("TICK", 11)), [])
        self.assertEqual(app.handle_event(event("MEETING_ENDED", 12)), [])
        self.assertEqual(app.handle_event(event("TICK", 13)), [])

        effects = app.handle_event(event("PERSON_ENTERED", 14))
        self.assertEqual([effect.value for effect in effects], ["wave_hand", "欢迎光临"])

    def test_conversation_and_meeting_are_independent_suppression_states(self):
        app = RobotApplication()

        app.handle_event(event("CONVERSATION_STARTED", 0))
        app.handle_event(event("MEETING_STARTED", 1))
        app.handle_event(event("CONVERSATION_ENDED", 2))

        self.assertTrue(app.snapshot()["meeting_active"])
        self.assertEqual(app.handle_event(event("PERSON_ENTERED", 3)), [])
        self.assertEqual(app.handle_event(event("MEETING_ENDED", 4)), [])

    def test_farewell_at_timeout_boundary_is_only_sent_once(self):
        app = RobotApplication()
        app.handle_event(event("PERSON_ENTERED", 0))
        app.handle_event(event("PERSON_LEFT", 5))

        self.assertEqual(app.handle_event(event("TICK", 14.999)), [])
        farewell = app.handle_event(event("TICK", 15))
        self.assertEqual([effect.value for effect in farewell], ["欢迎下次光临"])
        self.assertEqual(app.handle_event(event("TICK", 16)), [])

    def test_return_before_timeout_continues_same_reception(self):
        app = RobotApplication()
        app.handle_event(event("PERSON_ENTERED", 0, "p1"))
        app.handle_event(event("PERSON_LEFT", 1, "p1"))

        self.assertEqual(app.handle_event(event("PERSON_ENTERED", 9, "p1")), [])
        self.assertEqual(app.handle_event(event("TICK", 20)), [])
        self.assertTrue(app.snapshot()["reception_active"])

    def test_new_entry_after_confirmed_departure_starts_new_reception(self):
        app = RobotApplication()
        app.handle_event(event("PERSON_ENTERED", 0, "p1"))
        app.handle_event(event("PERSON_LEFT", 1, "p1"))
        app.handle_event(event("TICK", 11))

        effects = app.handle_event(event("PERSON_ENTERED", 12, "p1"))

        self.assertEqual([effect.value for effect in effects], ["wave_hand", "欢迎光临"])
        self.assertFalse(app.snapshot()["farewell_sent"])

    def test_last_person_leaving_starts_absence_timer(self):
        app = RobotApplication()
        app.handle_event(event("PERSON_ENTERED", 0, "p1"))
        app.handle_event(event("PERSON_ENTERED", 1, "p2"))

        self.assertEqual(app.handle_event(event("PERSON_LEFT", 2, "p1")), [])
        self.assertTrue(app.snapshot()["person_present"])
        self.assertEqual(app.handle_event(event("TICK", 20)), [])

        app.handle_event(event("PERSON_LEFT", 21, "p2"))
        self.assertEqual(app.handle_event(event("TICK", 30)), [])
        self.assertEqual(len(app.handle_event(event("TICK", 31))), 1)

    def test_duplicate_leave_does_not_restart_absence_timer(self):
        app = RobotApplication()
        app.handle_event(event("PERSON_ENTERED", 0, "p1"))
        app.handle_event(event("PERSON_LEFT", 1, "p1"))
        app.handle_event(event("PERSON_LEFT", 5, "p1"))

        self.assertEqual(len(app.handle_event(event("TICK", 11))), 1)

    def test_snapshot_is_isolated_from_internal_state(self):
        app = RobotApplication()
        app.handle_event(event("PERSON_ENTERED", 0, "p1"))

        first_snapshot = app.snapshot()
        first_snapshot["person_present"] = False
        first_snapshot["present_person_ids"] = ()
        second_snapshot = app.snapshot()

        self.assertTrue(second_snapshot["person_present"])
        self.assertEqual(second_snapshot["present_person_ids"], ("p1",))
        self.assertIsNot(first_snapshot, second_snapshot)

    def test_custom_timeout_and_zero_timeout(self):
        app = RobotApplication(absence_timeout_s=2.5)
        app.handle_event(event("PERSON_ENTERED", 0))
        app.handle_event(event("PERSON_LEFT", 1))
        self.assertEqual(app.handle_event(event("TICK", 3.49)), [])
        self.assertEqual(len(app.handle_event(event("TICK", 3.5))), 1)

        immediate_app = RobotApplication(absence_timeout_s=0)
        immediate_app.handle_event(event("PERSON_ENTERED", 0))
        immediate_app.handle_event(event("PERSON_LEFT", 1))
        self.assertEqual(len(immediate_app.handle_event(event("TICK", 1))), 1)

    def test_invalid_configuration_and_event_are_rejected(self):
        with self.assertRaises(ValueError):
            RobotApplication(absence_timeout_s=-1)

        app = RobotApplication()
        with self.assertRaises(ValueError):
            app.handle_event(event("UNKNOWN", 0))
        with self.assertRaises(ValueError):
            app.handle_event(event("TICK", float("nan")))
        with self.assertRaises(TypeError):
            app.handle_event(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
