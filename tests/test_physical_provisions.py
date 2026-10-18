"""Source-backed household stock access, measured against v2 rules.

Tests physical custody, cupboard reach, historical replay, forks and denials.
Numbers for finite portions still belong to DailyRhythm. This milestone
binds their usability to real objects, not their exact ingredient mass.
"""
import tempfile
from pathlib import Path
import unittest

from pretorius_lab.daily_rhythm import DailyRhythm, STOCK_RULES
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.subject_port import SubjectPort
from pretorius_lab.physics import Conflict


class PhysicalProvisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def world(self, name, v3=True):
        world = SpatialHabitat.create(self.root / (name + ".sqlite3"))
        HomeLife(world).initialize()
        rhythm = DailyRhythm(world)
        rhythm.initialize(perishable_meals=True, physical_provisions=v3)
        subject = SubjectPort(world)
        subject.act("walk", event_id=name+"-hall", station="station:hall")
        subject.act("walk", event_id=name+"-kitchen", station="station:kitchen")
        return world, rhythm, subject

    def remove_bread(self, subject, key):
        subject.act("take", event_id=key+"-grab", item="food:bread")
        subject.act("walk", event_id=key+"-hall-out", station="station:hall")
        subject.act("walk", event_id=key+"-parlor-out", station="station:parlor")
        subject.act("open", event_id=key+"-desk-open", container="desk:parlor")
        subject.act("put", event_id=key+"-stow", item="food:bread", container="desk:parlor")
        subject.act("walk", event_id=key+"-hall-back", station="station:hall")
        subject.act("walk", event_id=key+"-kitchen-back", station="station:kitchen")

    def return_bread(self, subject, key):
        subject.act("walk", event_id=key+"-hall", station="station:hall")
        subject.act("walk", event_id=key+"-parlor", station="station:parlor")
        subject.act("take", event_id=key+"-grab", item="food:bread")
        subject.act("walk", event_id=key+"-hall2", station="station:hall")
        subject.act("walk", event_id=key+"-kitchen", station="station:kitchen")
        subject.act("put", event_id=key+"-table", item="food:bread", container="table:kitchen")

    def test_bread_taken_elsewhere_blocks_cooking_despite_numeric_rations(self):
        _, life, subject = self.world("bread_elsewhere")
        self.remove_bread(subject, "bread")
        initial = life.audit_state()
        self.assertGreater(initial["supplies"]["rations"], 0)
        with self.assertRaises(Conflict):
            subject.act("prepare_meal", event_id="no-bread")
        self.assertEqual(life.audit_state(), initial)
        self.return_bread(subject, "returned")
        subject.act("prepare_meal", event_id="bread-restored")
        self.assertEqual(life.audit_state()["supplies"]["rations"],
                         initial["supplies"]["rations"] - 1)
        self.assertTrue(life.verify()["verified"])

    def test_original_v2_ignores_physical_bread_location_as_control(self):
        _, life, subject = self.world("legacy_control", v3=False)
        self.remove_bread(subject, "bread")
        subject.act("prepare_meal", event_id="old-rules-meal")
        self.assertTrue(life.audit_state()["meal_ready"])
        self.assertTrue(life.verify()["verified"])

    def test_closed_cupboard_prevents_tea_until_physically_opened(self):
        _, life, subject = self.world("closed_cupboard")
        before = life.audit_state()
        with self.assertRaises(Conflict):
            subject.act("brew_tea", event_id="closed-cupboard-tea")
        self.assertEqual(life.audit_state(), before)
        subject.act("open", event_id="open-cupboard", container="cupboard:kitchen")
        subject.act("brew_tea", event_id="actual-tea")
        self.assertEqual(life.audit_state()["supplies"]["tea"],
                         before["supplies"]["tea"] - 1)
        self.assertTrue(life.verify()["verified"])

    def test_tea_tin_moved_out_blocks_brewing_and_restoring_it_repairs(self):
        _, life, subject = self.world("tea_moves")
        subject.act("open", event_id="cup-open", container="cupboard:kitchen")
        subject.act("take", event_id="tea-in-hand", item="food:tea")
        subject.act("walk", event_id="tea-to-hall", station="station:hall")
        subject.act("walk", event_id="tea-to-parlor", station="station:parlor")
        subject.act("open", event_id="parlor-open", container="desk:parlor")
        subject.act("put", event_id="tea-stash", item="food:tea", container="desk:parlor")
        subject.act("walk", event_id="tea-hall-again", station="station:hall")
        subject.act("walk", event_id="tea-kitchen-again", station="station:kitchen")
        before = life.audit_state()
        with self.assertRaises(Conflict):
            subject.act("brew_tea", event_id="tea-away")
        self.assertEqual(life.audit_state(), before)
        subject.act("walk", event_id="tea-return-hall", station="station:hall")
        subject.act("walk", event_id="tea-return-parlor", station="station:parlor")
        subject.act("take", event_id="tea-return-pick", item="food:tea")
        subject.act("walk", event_id="tea-return-hall2", station="station:hall")
        subject.act("walk", event_id="tea-return-kitchen", station="station:kitchen")
        subject.act("put", event_id="tea-return-cupboard", item="food:tea",
                    container="cupboard:kitchen")
        subject.act("brew_tea", event_id="now-tea")
        self.assertTrue(life.verify()["verified"])

    def test_history_uses_old_item_position_not_latest_for_replay(self):
        _, life, subject = self.world("past_position")
        subject.act("open", event_id="cupboard-open", container="cupboard:kitchen")
        subject.act("brew_tea", event_id="tea-when-present")
        subject.act("take", event_id="relocate-tea", item="food:tea")
        subject.act("walk", event_id="relocate-hall", station="station:hall")
        subject.act("walk", event_id="relocate-parlor", station="station:parlor")
        subject.act("open", event_id="relocate-desk", container="desk:parlor")
        subject.act("put", event_id="relocate-store", item="food:tea",
                    container="desk:parlor")
        original = life.verify()
        reopened = DailyRhythm(SpatialHabitat(life.habitat.path))
        self.assertEqual(reopened.verify(), original)
        self.assertEqual(reopened.audit_state()["supplies"]["tea"], 2)

    def test_legacy_direct_rhythm_api_cannot_bypass_physical_absence(self):
        _, life, subject = self.world("direct_api")
        self.remove_bread(subject, "direct-gone")
        before = life.audit_state()
        with self.assertRaises(Conflict):
            life.act("prepare_meal", event_id="direct-bypass-attempt")
        self.assertEqual(life.audit_state(), before)
        self.assertTrue(life.verify()["verified"])

    def test_visible_tea_tin_does_not_replenish_exhausted_portions(self):
        _, life, subject = self.world("exhausted_tea")
        subject.act("open", event_id="cupboard-real", container="cupboard:kitchen")
        for n in range(3):
            subject.act("brew_tea", event_id=f"tea-cup-{n}")
        before = life.audit_state()
        self.assertEqual(before["supplies"]["tea"], 0)
        with self.assertRaises(Conflict):
            subject.act("brew_tea", event_id="no-hidden-refill")
        self.assertEqual(life.audit_state(), before)
        self.assertTrue(life.verify()["verified"])

    def test_v2_cannot_be_migrated_in_place_to_v3(self):
        world, life, _ = self.world("v2_no_upgrade", v3=False)
        with self.assertRaises(Conflict):
            life.initialize(perishable_meals=True, physical_provisions=True)
        self.assertTrue(life.verify()["verified"])
        self.assertNotIn("v3", str(life.audit_state()))

    def test_fork_copies_physical_location_but_not_prior_actions(self):
        world, life, subject = self.world("stock_parent")
        self.remove_bread(subject, "bread-fork")
        world.fork_to(self.root / "child.sqlite3")
        child = SpatialHabitat(self.root / "child.sqlite3")
        child_life = DailyRhythm(child)
        child_subject = SubjectPort(child)
        self.assertEqual(child_life.audit_state(), life.audit_state())
        self.assertEqual(child_life.verify()["revision"], 0)
        with self.assertRaises(Conflict):
            child_subject.act("prepare_meal", event_id="child-no-bread")
        self.assertEqual(child_life.verify()["revision"], 0)
        self.assertTrue(life.verify()["verified"])

    def test_untrusted_extra_affordance_arg_cannot_override_physical_world(self):
        _, life, subject = self.world("cannot-cheat")
        self.remove_bread(subject, "not-here")
        before = life.audit_state()
        with self.assertRaises((Conflict, ValueError)):
            subject.act("prepare_meal", event_id="fake-affordance", stock_access={"meal": True})
        self.assertEqual(life.audit_state(), before)
        self.assertTrue(life.verify()["verified"])

if __name__ == "__main__":
    unittest.main()
