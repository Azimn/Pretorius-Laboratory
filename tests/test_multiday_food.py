"""Longitudinal prepared-food realism versus unchanged historical rules."""
from pathlib import Path
import tempfile
import unittest

from pretorius_lab.daily_rhythm import DailyRhythm, FRESH_RULES, MEAL_FRESH_MINUTES
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.subject_port import SubjectPort
from pretorius_lab.physics import Conflict, LabError


class PerishableMealTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def new(self, name, *, fresh):
        world = SpatialHabitat.create(self.root / (name + ".sqlite3"))
        HomeLife(world).initialize()
        life = DailyRhythm(world)
        life.initialize(perishable_meals=fresh)
        home = HomeLife(world)
        home.walk("station:hall", event_id=name+"-hall")
        home.walk("station:kitchen", event_id=name+"-kitchen")
        return world, life, SubjectPort(world)

    def pass_hours(self, life, hours, prefix):
        assert hours % 4 == 0
        for n in range(hours // 4):
            life.advance(240, event_id=f"{prefix}-{n}")

    def test_fourteen_hour_meal_wastes_resources_only_in_opt_in(self):
        world, life, subject = self.new("old_meal", fresh=False)
        _, newer, other = self.new("new_meal", fresh=True)
        life.act("prepare_meal", event_id="prepare")
        newer.act("prepare_meal", event_id="prepare")
        self.pass_hours(life, 8, "time-old")
        self.pass_hours(newer, 8, "time-new")
        original = life.audit_state()
        candidate = newer.audit_state()
        self.assertEqual(original["minute"], candidate["minute"])
        self.assertEqual(original["supplies"], candidate["supplies"])
        self.assertTrue(original["meal_ready"] and candidate["meal_ready"])
        self.assertIn("prepared meal to eat", subject.observe()["inner"])
        self.assertIn("must be discarded", other.observe()["inner"])
        before = newer.audit_state()
        with self.assertRaises(Conflict):
            other.act("eat", event_id="cannot-eat-spoiled")
        self.assertEqual(newer.audit_state(), before)
        # True world consequences: discard consumes time and loses provisions.
        result = other.act("discard_meal", event_id="discard-food")
        after = newer.audit_state()
        self.assertIn("provisions are wasted", result["inner"])
        self.assertEqual(after["minute"], before["minute"] + 10)
        self.assertFalse(after["meal_ready"])
        self.assertIsNone(after["meal_prepared_minute"])
        self.assertEqual(after["supplies"], before["supplies"])
        self.assertTrue(newer.verify()["verified"])
        old_outcome = subject.act("eat", event_id="old-food-still-eaten")
        self.assertIn("I eat", old_outcome["inner"])
        self.assertTrue(life.verify()["verified"])

    def test_recovery_new_cooking_and_eating_after_discard(self):
        _, life, subject = self.new("recovery", fresh=True)
        subject.act("prepare_meal", event_id="cooked-1")
        life.advance(210, event_id="time-1")
        life.advance(210, event_id="time-2")
        self.assertIn("left out too long", subject.observe()["inner"])
        subject.act("discard_meal", event_id="discard-1")
        subject.act("prepare_meal", event_id="cooked-2")
        fresh = life.audit_state()
        self.assertLess(fresh["minute"] - fresh["meal_prepared_minute"], MEAL_FRESH_MINUTES)
        self.assertIn("prepared meal to eat", subject.observe()["inner"])
        subject.act("eat", event_id="eat-fresh-2")
        self.assertFalse(life.audit_state()["meal_ready"])
        self.assertIsNone(life.audit_state()["meal_prepared_minute"])
        self.assertEqual(life.audit_state()["supplies"]["rations"], 2)
        self.assertTrue(life.verify()["verified"])

    def test_older_history_replays_identically_and_new_command_denied(self):
        _, life, subject = self.new("historic", fresh=False)
        before = life.audit_state()
        with self.assertRaises(LabError):
            subject.act("discard_meal", event_id="cannot-add-rule")
        self.assertEqual(life.audit_state(), before)
        life.act("prepare_meal", event_id="historic-prepare")
        self.pass_hours(life, 12, "historic-hours")
        subject.act("eat", event_id="historic-eat")
        self.assertEqual(set(life.audit_state()), set(life.audit_state()) - {"meal_prepared_minute"})
        self.assertTrue(DailyRhythm(life.habitat).verify()["verified"])

    def test_stale_food_does_not_auto_vanish_during_multiday_idle(self):
        _, life, subject = self.new("three_days", fresh=True)
        subject.act("prepare_meal", event_id="first")
        self.pass_hours(life, 48, "two-days")
        state = life.audit_state()
        self.assertTrue(state["meal_ready"])
        self.assertGreaterEqual(state["minute"] - state["meal_prepared_minute"], 2*1440)
        self.assertIn("must be discarded", subject.observe()["inner"])
        self.assertTrue(life.verify()["verified"])
        subject.act("discard_meal", event_id="end-of-two-days")
        self.assertFalse(DailyRhythm(life.habitat).audit_state()["meal_ready"])

    def test_fork_preserves_stale_condition_not_parent_lived_history(self):
        world, life, subject = self.new("parent", fresh=True)
        subject.act("prepare_meal", event_id="meal")
        self.pass_hours(life, 8, "hours")
        fork_file = self.root / "branch.sqlite3"
        world.fork_to(fork_file)
        fork = DailyRhythm(SpatialHabitat(fork_file))
        self.assertEqual(fork.audit_state(), life.audit_state())
        self.assertEqual(fork.verify()["revision"], 0)
        self.assertNotEqual(fork.verify()["world_epoch"], life.verify()["world_epoch"])
        SubjectPort(SpatialHabitat(fork_file)).act("discard_meal", event_id="fork-discard")
        self.assertTrue(life.audit_state()["meal_ready"])
        self.assertFalse(fork.audit_state()["meal_ready"])

    def test_wrong_world_rule_cannot_be_migrated_in_place(self):
        world, life, _ = self.new("wrong_rule", fresh=False)
        with self.assertRaises(Conflict):
            life.initialize(perishable_meals=True)
        self.assertTrue(life.verify()["verified"])

    def test_fixed_age_boundary_five_hours_fifty_nine_versus_six_hours(self):
        _, life, subject = self.new("boundary", fresh=True)
        subject.act("prepare_meal", event_id="first")
        for n, minutes in enumerate((240, 119)):
            life.advance(minutes, event_id=f"aged-{n}")
        self.assertNotIn("must be discarded", subject.observe()["inner"])
        life.advance(10, event_id="boundary-over")
        self.assertIn("must be discarded", subject.observe()["inner"])
        with self.assertRaises(Conflict):
            subject.act("eat", event_id="too-old")
        self.assertTrue(life.verify()["verified"])

if __name__ == "__main__":
    unittest.main()
