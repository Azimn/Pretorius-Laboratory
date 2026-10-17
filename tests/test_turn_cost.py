"""Retro game turn costs must cause real, replayable physical time."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.subject_port import SubjectPort
from pretorius_lab.turn_cost import TurnCostSubjectPort
from pretorius_lab.physics import Conflict, LabError


class TurnCostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.lab = SpatialHabitat.create(Path(self.tmp.name) / "clocked.db")
        HomeLife(self.lab).initialize()
        DailyRhythm(self.lab).initialize()
        self.base = SubjectPort(self.lab)
        self.timed = TurnCostSubjectPort(self.base)

    def state(self):
        return DailyRhythm(self.lab).audit_state()

    def test_simple_movement_actually_consumes_time(self):
        before = self.state()["minute"]
        result = self.timed.act("walk", event_id="move-to-hall", station="station:hall")
        self.assertEqual(self.state()["minute"], before + 2)
        self.assertTrue(result["inner"].startswith(("I ", "My ")))
        self.assertEqual(set(result), {"inner", "spoken_aloud"})
        self.assertNotIn("attending to what I have just done", result["inner"])
        self.assertTrue(self.timed.verify()["verified"])

    def test_duplicate_world_action_never_bills_two_turns(self):
        first = self.timed.act("walk", event_id="unique-step", station="station:hall")
        before = self.state()
        again = TurnCostSubjectPort(SubjectPort(self.lab)).act(
            "walk", event_id="unique-step", station="station:hall")
        self.assertEqual(first, again)
        self.assertEqual(self.state(), before)
        with self.lab._open() as db:
            import json
            ticks = [json.loads(row[0]) for row in db.execute(
                "SELECT envelope FROM rhythm_events")
                if json.loads(row[0])["op"] == "tick"]
            self.assertEqual(len(ticks), 1)

    def test_lamp_and_bodily_regulation_use_same_clock(self):
        self.base.act("light", event_id="lit-at-start")
        initial = self.state()
        self.timed.act("walk", event_id="first-move", station="station:hall")
        after = self.state()
        self.assertEqual(after["minute"], initial["minute"] + 2)
        self.assertEqual(after["lamps"]["room:sanctum"], initial["lamps"]["room:sanctum"] - 2)
        self.assertEqual(after["supplies"], initial["supplies"])
        self.assertTrue(DailyRhythm(self.lab).verify()["verified"])

    def test_invalid_action_consumes_no_time_and_can_retry_event_id(self):
        before = self.state()
        with self.assertRaises((LabError, Conflict)):
            self.timed.act("walk", event_id="try-bedroom", station="station:bedroom")
        self.assertEqual(self.state(), before)
        self.timed.act("walk", event_id="try-bedroom", station="station:hall")
        self.assertEqual(self.state()["minute"], before["minute"] + 2)

    def test_new_command_cannot_rebind_old_source_id(self):
        self.timed.act("walk", event_id="one-id", station="station:hall")
        before = self.state()
        with self.assertRaises(Conflict):
            self.timed.act("take", event_id="one-id", item="garment:boots")
        self.assertEqual(self.state(), before)

    def test_existing_advance_and_work_costs_are_not_double_charged(self):
        before = self.state()["minute"]
        self.timed.act("advance", event_id="existing-timer", minutes=20)
        self.assertEqual(self.state()["minute"], before + 20)
        self.assertEqual(self.state()["hunger"], 2)

    def test_failed_clock_write_requires_retry_of_same_physical_event(self):
        saved_act = self.base.rhythm.act
        def fail_tick(op, *a, **kw):
            if op == "tick":
                raise RuntimeError("injected crash before clock write")
            return saved_act(op, *a, **kw)
        before = self.state()["minute"]
        with patch.object(self.base.rhythm, "act", side_effect=fail_tick):
            with self.assertRaises(RuntimeError):
                self.timed.act("walk", event_id="crash-before-clock", station="station:hall")
        self.assertEqual(self.state()["minute"], before)
        with self.assertRaises(Conflict):
            self.timed.act("walk", event_id="unrelated-action", station="station:threshold")
        retried = self.timed.act("walk", event_id="crash-before-clock", station="station:hall")
        self.assertTrue(retried["inner"].startswith(("I ", "My ")))
        self.assertEqual(self.state()["minute"], before + 2)
        self.assertTrue(self.timed.verify()["verified"])

    def test_post_clock_crash_fails_closed_instead_of_rewriting_history(self):
        from pretorius_lab import turn_cost
        save = turn_cost._as_json
        def fail_result(v):
            if isinstance(v, dict) and "inner" in v:
                raise RuntimeError("injected crash after clock write")
            return save(v)
        with patch.object(turn_cost, "_as_json", side_effect=fail_result):
            with self.assertRaises(RuntimeError):
                self.timed.act("walk", event_id="crash-post-clock", station="station:hall")
        minute = self.state()["minute"]
        self.assertEqual(minute, 422)
        with self.assertRaises(Conflict):
            self.timed.act("walk", event_id="crash-post-clock", station="station:hall")
        self.assertEqual(self.state()["minute"], minute)
        with self.assertRaises(Conflict):
            self.timed.act("advance", event_id="other-time", minutes=10)

    def test_original_subject_remains_unchanged_as_control(self):
        control_file = Path(self.tmp.name) / "unclocked.db"
        control_lab = SpatialHabitat.create(control_file)
        HomeLife(control_lab).initialize()
        DailyRhythm(control_lab).initialize()
        control = SubjectPort(control_lab)
        control.act("walk", event_id="one-move", station="station:hall")
        self.timed.act("walk", event_id="one-move", station="station:hall")
        self.assertEqual(DailyRhythm(control_lab).audit_state()["minute"], 420)
        self.assertEqual(self.state()["minute"], 422)
        self.assertEqual(DailyRhythm(control_lab).audit_state()["fatigue"], self.state()["fatigue"])

    def test_clock_tick_replay_still_rejects_fabricated_text(self):
        self.timed.act("walk", event_id="authentic", station="station:hall")
        with self.lab._open() as db:
            import json
            row = next((r for r in db.execute(
                "SELECT revision,envelope FROM rhythm_events")
                if json.loads(r[1])["op"] == "tick"), None)
            self.assertIsNotNone(row)
            payload = json.loads(row[1])
            payload["subject"]["inner"] = "I have teleported outside."
            db.execute("UPDATE rhythm_events SET envelope=? WHERE revision=?",
                       (json.dumps(payload), row[0]))
        with self.assertRaises(Conflict):
            self.timed.verify()

if __name__ == "__main__":
    unittest.main()
