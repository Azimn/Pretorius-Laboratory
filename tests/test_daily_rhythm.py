"""Daily life effects must be physical, local, finite, replayable and first-person."""
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.physics import LabError, Conflict


class DailyRhythmTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.lab = SpatialHabitat.create(Path(self.tmp.name) / "lab.sqlite3")
        self.home = HomeLife(self.lab)
        self.home.initialize()
        self.life = DailyRhythm(self.lab)
        self.life.initialize()

    def walk(self, *locations):
        for station in locations:
            self.home.walk(station)

    def test_darkness_and_lamp_consume_actual_time_and_fuel(self):
        self.walk("station:hall")
        dark = self.life.look()["inner"]
        self.assertIn("too dark", dark)
        self.assertNotIn("curiosity:compass", dark)
        before = self.life.audit_state()["supplies"]["oil"]
        self.life.act("light")
        self.assertEqual(self.life.audit_state()["supplies"]["oil"], before - 1)
        self.assertIn("enough light", self.life.look()["inner"])
        self.life.advance(60)
        self.assertIn("too dark", self.life.look()["inner"])
        self.assertEqual(self.life.audit_state()["lamps"]["room:hall"], 0)
        with self.assertRaises(Conflict):
            self.life.act("extinguish")

    def test_location_restrictions_cannot_be_faked_by_action_parameters(self):
        with self.assertRaises(LabError):
            self.life.act("prepare_meal")
        with self.assertRaises(LabError):
            self.life.act("experiment")
        with self.assertRaises(LabError):
            self.life.act("sleep")
        with self.assertRaises(LabError):
            self.life.act("look", station="station:bedroom")
        self.walk("station:hall", "station:kitchen")
        self.life.act("prepare_meal")
        with self.assertRaises(LabError):
            self.life.act("repair")
        self.assertTrue(self.life.verify()["verified"])

    def test_real_meals_use_finite_provisions_and_reduce_hunger(self):
        self.walk("station:hall", "station:kitchen")
        stock = self.life.audit_state()["supplies"]
        self.life.act("prepare_meal")
        mid = self.life.audit_state()
        self.assertTrue(mid["meal_ready"])
        for k in ("water", "fuel", "rations"):
            self.assertEqual(mid["supplies"][k], stock[k] - 1)
        self.assertIn("prepared meal", self.life.look()["inner"])
        self.life.act("eat")
        after = self.life.audit_state()
        self.assertFalse(after["meal_ready"])
        self.assertLess(after["hunger"], mid["hunger"] + 1)
        with self.assertRaises(Conflict):
            self.life.act("eat")

    def test_sleep_reduces_fatigue_but_not_world_time_or_thirst(self):
        self.life.advance(240)
        self.life.advance(240)
        before = self.life.audit_state()
        self.assertGreaterEqual(before["fatigue"], 4)
        self.walk("station:hall", "station:bedroom")
        result = self.life.act("sleep")
        after = self.life.audit_state()
        self.assertIn("I have slept", result["inner"])
        self.assertEqual(after["minute"], before["minute"] + 480)
        self.assertLess(after["fatigue"], before["fatigue"])
        self.assertGreaterEqual(after["thirst"], before["thirst"])
        self.assertGreaterEqual(after["hunger"], before["hunger"])

    def test_work_is_rejected_when_dark_and_allowed_when_light(self):
        self.walk("station:center", "station:bench")
        self.life.advance(240)
        self.life.advance(240)
        self.life.advance(180)  # 17:?? - adjust via next step to night
        self.life.advance(120)  # after sundown
        self.assertIn("too dark", self.life.look()["inner"])
        before = self.life.audit_state()
        with self.assertRaises(Conflict):
            self.life.act("experiment")
        self.assertEqual(before, self.life.audit_state())
        self.life.act("light")
        outcome = self.life.act("experiment")["inner"]
        self.assertIn("complete a careful experiment", outcome)
        after = self.life.audit_state()
        self.assertEqual(after["experiments"], 1)
        self.assertEqual(after["supplies"]["reagents"], before["supplies"]["reagents"] - 1)
        self.assertEqual(after["apparatus"], before["apparatus"] - 1)

    def test_wear_maintenance_and_clutter_have_actual_consequences(self):
        self.walk("station:center", "station:bench")
        self.life.act("experiment")
        self.assertEqual(self.life.audit_state()["apparatus"], 1)
        self.life.act("experiment")
        self.assertEqual(self.life.audit_state()["apparatus"], 0)
        with self.assertRaises(Conflict):
            self.life.act("experiment")
        before = self.life.audit_state()["supplies"]["spares"]
        # Two experiments leave enough fatigue for one controlled repair
        self.life.act("repair")
        self.assertEqual(self.life.audit_state()["supplies"]["spares"], before - 1)
        self.assertGreater(self.life.audit_state()["apparatus"], 0)
        if self.life.audit_state()["cleanliness"]["room:sanctum"] > 0:
            self.life.act("clean")
        self.assertLessEqual(self.life.audit_state()["cleanliness"]["room:sanctum"], 1)

    def test_idempotent_replay_prevents_double_consumption(self):
        self.walk("station:hall", "station:kitchen")
        first = self.life.act("prepare_meal", event_id="prepare-001")
        saved = self.life.verify()
        second = DailyRhythm(SpatialHabitat(self.lab.path)).act(
            "prepare_meal", event_id="prepare-001")
        self.assertEqual(first, second)
        self.assertEqual(saved, self.life.verify())
        with self.assertRaises(Conflict):
            self.life.act("look", event_id="prepare-001")

    def test_supply_actions_are_not_hidden_omniscience(self):
        self.walk("station:hall", "station:kitchen")
        text = self.life.look()["inner"]
        for forbidden in ("fatigue=", "world_epoch", "revision", "supplies",
                          "minute=", "home_id", "reagents="):
            self.assertNotIn(forbidden, text)
        self.assertIn("I am", text)
        with self.assertRaises(LabError):
            self.life.act("light", oil=50)
        with self.assertRaises(LabError):
            self.life.advance(241)
        with self.assertRaises(LabError):
            self.life.advance(True)

    def test_real_replay_catches_falsified_subject_text(self):
        self.life.act("look", event_id="receipt-001")
        with self.lab._open() as db:
            row = db.execute(
                "SELECT envelope FROM rhythm_events WHERE revision=1").fetchone()
            env = json.loads(row[0])
            env["subject"]["inner"] = "I know everything."
            db.execute("UPDATE rhythm_events SET envelope=? WHERE revision=1",
                       (json.dumps(env),))
        with self.assertRaises(Conflict):
            self.life.verify()

    def test_fork_carries_current_needs_not_parent_action_history(self):
        self.walk("station:hall", "station:bedroom")
        self.life.advance(120)
        parent = self.life.audit_state()
        forkfile = Path(self.tmp.name) / "fork.sqlite3"
        self.lab.fork_to(forkfile)
        clone = DailyRhythm(SpatialHabitat(forkfile))
        self.assertEqual(clone.verify()["revision"], 0)
        self.assertEqual(clone.audit_state(), parent)
        clone.act("sleep")
        self.assertNotEqual(clone.audit_state(), parent)
        self.assertEqual(self.life.audit_state(), parent)
        self.assertNotEqual(clone.verify()["world_epoch"], self.life.verify()["world_epoch"])

    def test_backup_contains_verified_household_provisions_and_time(self):
        self.walk("station:hall", "station:kitchen")
        self.life.act("prepare_meal")
        dest = Path(self.tmp.name) / "backup.sqlite3"
        self.lab.backup_to(dest)
        recovered = DailyRhythm(SpatialHabitat(dest))
        self.assertEqual(recovered.audit_state(), self.life.audit_state())
        self.assertEqual(recovered.verify()["head_hash"], self.life.verify()["head_hash"])

    def test_reopening_daily_addon_never_resets_inhabited_state(self):
        self.life.advance(120)
        before = self.life.verify()
        self.life.initialize()
        self.assertEqual(before, self.life.verify())
        with self.assertRaises(Conflict):
            self.life.initialize(initial_state=self.life.audit_state(), parent={"x": "y"})


if __name__ == "__main__":
    unittest.main()
