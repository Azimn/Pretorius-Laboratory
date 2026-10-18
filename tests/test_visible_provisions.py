"""Retro material depletion: a loaf and tea tin visibly change as portions go.

Finite portions remain owned by one existing DailyRhythm ledger; physical
location and container openness remain owned by one existing HomeLife ledger.
No new inventory state and no invented omniscient awareness.
"""
from pathlib import Path
import tempfile
import unittest

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.daily_rhythm import DailyRhythm, VISIBLE_RULES
from pretorius_lab.subject_port import SubjectPort
from pretorius_lab.physics import Conflict, LabError


class VisiblePortionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def world(self, name, *, visible=True):
        lab = SpatialHabitat.create(self.root / (name + ".sqlite3"))
        HomeLife(lab).initialize()
        life = DailyRhythm(lab)
        life.initialize(perishable_meals=True, physical_provisions=True,
                        visible_portions=visible)
        subject = SubjectPort(lab)
        subject.act("walk", station="station:hall", event_id=name+"-hall")
        subject.act("walk", station="station:kitchen", event_id=name+"-kitchen")
        return lab, life, subject

    def test_bread_changes_in_four_source_verified_steps(self):
        _, life, subject = self.world("loaf")
        descriptions = ("a whole bread loaf", "most of the bread loaf",
                        "about half of the bread loaf",
                        "the last usable portion", "bare bread remnants")
        for n, expected in enumerate(descriptions):
            state = life.audit_state()
            self.assertEqual(state["supplies"]["rations"], 4-n)
            inner = subject.observe()["inner"]
            self.assertIn(expected, inner)
            self.assertNotIn("rations=", inner)
            self.assertNotIn("world_epoch", inner)
            if n < 4:
                subject.act("prepare_meal", event_id=f"meal-{n}")
                subject.act("eat", event_id=f"eat-{n}")
        before = life.audit_state()
        with self.assertRaises(Conflict):
            subject.act("prepare_meal", event_id="infinite-bread")
        self.assertEqual(life.audit_state(), before)
        self.assertTrue(life.verify()["verified"])

    def test_original_v3_never_changes_old_observations(self):
        _, life, subject = self.world("old-control", visible=False)
        before = subject.observe()["inner"]
        self.assertIn("bread loaf", before)
        self.assertNotIn("enough for four meals", before)
        subject.act("prepare_meal", event_id="make-v3")
        subject.act("eat", event_id="eat-v3")
        after = subject.observe()["inner"]
        self.assertIn("bread loaf", after)
        self.assertNotIn("most of the bread loaf", after)
        self.assertTrue(life.verify()["verified"])

    def test_closed_cupboard_hides_tea_and_open_cupboard_reveals_levels(self):
        _, life, subject = self.world("tea-count")
        first = subject.observe()["inner"]
        self.assertNotIn("tea tin", first)
        subject.act("open", container="cupboard:kitchen", event_id="tea-open")
        self.assertIn("enough leaves for three cups", subject.observe()["inner"])
        for n, expected in enumerate(
                ("enough leaves for two cups", "enough leaves for one cup",
                 "an empty tea tin")):
            subject.act("brew_tea", event_id=f"brew-{n}")
            self.assertIn(expected, subject.observe()["inner"])
        state = life.audit_state()
        self.assertEqual(state["supplies"]["tea"], 0)
        with self.assertRaises(Conflict):
            subject.act("brew_tea", event_id="tea-from-empty-tin")
        self.assertEqual(state, life.audit_state())
        self.assertTrue(life.verify()["verified"])

    def test_food_location_and_custody_still_control_visibility(self):
        _, life, subject = self.world("locating")
        subject.act("take", item="food:bread", event_id="pick-bread")
        self.assertIn("I am holding a whole bread loaf", subject.observe()["inner"])
        subject.act("walk", station="station:hall", event_id="bread-hall")
        subject.act("walk", station="station:parlor", event_id="bread-parlor")
        subject.act("open", container="desk:parlor", event_id="desk-open")
        subject.act("put", item="food:bread", container="desk:parlor",
                    event_id="bread-in-desk")
        self.assertIn("a whole bread loaf", subject.observe()["inner"])
        subject.act("close", container="desk:parlor", event_id="desk-close")
        self.assertNotIn("whole bread loaf", subject.observe()["inner"])
        subject.act("walk", station="station:hall", event_id="back-hall")
        subject.act("walk", station="station:kitchen", event_id="back-kitchen")
        self.assertNotIn("whole bread loaf", subject.observe()["inner"])
        self.assertTrue(life.verify()["verified"])

    def test_daylight_and_lamp_gate_disclose_no_stock_in_dark(self):
        _, life, subject = self.world("night")
        for i in range(3):
            life.advance(240, event_id=f"late-{i}")
        dark = subject.observe()["inner"]
        self.assertIn("too dark", dark)
        self.assertNotIn("whole bread loaf", dark)
        self.assertNotIn("tea tin", dark)
        subject.act("light", event_id="kitchen-lamp")
        lit = subject.observe()["inner"]
        self.assertIn("a whole bread loaf", lit)
        self.assertTrue(life.verify()["verified"])

    def test_restart_and_sandbox_fork_preserve_levels_without_history_clone(self):
        lab, life, subject = self.world("reopen")
        subject.act("prepare_meal", event_id="first-meal")
        subject.act("eat", event_id="first-eat")
        observed = subject.observe()["inner"]
        self.assertIn("most of the bread loaf", observed)
        reopened = SubjectPort(SpatialHabitat(lab.path))
        self.assertIn("most of the bread loaf", reopened.observe()["inner"])
        fork_file = self.root / "child.sqlite3"
        lab.fork_to(fork_file)
        fork_subject = SubjectPort(SpatialHabitat(fork_file))
        self.assertIn("most of the bread loaf", fork_subject.observe()["inner"])
        fork_life = DailyRhythm(SpatialHabitat(fork_file))
        self.assertGreater(fork_life.verify()["revision"], 0)  # local observation receipt
        self.assertNotEqual(fork_life.verify()["world_epoch"], life.verify()["world_epoch"])
        fork_subject.act("prepare_meal", event_id="child-meal")
        fork_subject.act("eat", event_id="child-eat")
        self.assertIn("about half of the bread loaf", fork_subject.observe()["inner"])
        self.assertIn("most of the bread loaf", subject.observe()["inner"])
        self.assertTrue(life.verify()["verified"])

    def test_cannot_silently_convert_v3_or_choose_v4_without_stock_rules(self):
        _, old, _ = self.world("v3", visible=False)
        before = old.audit_state()
        with self.assertRaises(Conflict):
            old.initialize(perishable_meals=True, physical_provisions=True,
                           visible_portions=True)
        self.assertEqual(before, old.audit_state())
        new_lab = SpatialHabitat.create(self.root / "bad-flags.sqlite3")
        HomeLife(new_lab).initialize()
        with self.assertRaises(LabError):
            DailyRhythm(new_lab).initialize(
                perishable_meals=True, visible_portions=True)
        self.assertTrue(old.verify()["verified"])

    def test_corrupt_portion_authority_cannot_invent_visible_inventory(self):
        import json
        lab, life, subject = self.world("integrity")
        subject.observe()
        with lab._open() as db:
            state = life.audit_state()  # use outside nested db below
        # Only mutate the stored state, not the supporting source receipt.
        with lab._open() as db:
            row = db.execute("SELECT value FROM rhythm_meta WHERE key='state'").fetchone()
            payload = json.loads(row[0])
            payload["supplies"]["rations"] = 1
            db.execute("UPDATE rhythm_meta SET value=? WHERE key='state'",
                       (json.dumps(payload),))
        with self.assertRaises(Conflict):
            subject.observe()

if __name__ == "__main__":
    unittest.main()
