"""Consequential room changes must survive actual night, restart and forks."""
import json
import sqlite3
import tempfile
from pathlib import Path
import unittest

from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.home_affordances import HomeAffordances
from pretorius_lab.home_arrangement import HomeArrangements
from pretorius_lab.home_intents import act as act_intent, propose
from pretorius_lab.physics import Conflict


class PersistentArrangementTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        self.world = SpatialHabitat.create(self.root / "lived_home.sqlite3")
        HomeLife(self.world).initialize()
        self.clock = DailyRhythm(self.world)
        self.clock.initialize(perishable_meals=True, physical_provisions=True,
                              visible_portions=True, physical_paper=True)
        self.furniture = HomeArrangements(self.world)
        self.furniture.initialize()
        self.home = HomeAffordances(self.world)

    def offered(self, command, **args):
        return next((o for o in self.home.discover()["offers"]
                     if o["command"] == command and o["args"] == args), None)

    def do(self, command, eid, **args):
        offer = self.offered(command, **args)
        self.assertIsNotNone(offer, (command, args))
        return self.home.act(offer["offer_id"], event_id=eid)

    def parlor(self):
        self.do("walk", "go-to-hall", station="station:hall")
        self.do("walk", "go-to-parlor", station="station:parlor")

    def test_unusual_free_text_move_is_real_and_same_chair_is_there_after_sleep(self):
        self.parlor()
        first = self.furniture.observe()["inner"]
        self.assertIn("near the fireplace", first)
        physical_before = self.furniture.audit_state()
        committed = act_intent(
            "Would you move the upholstered chair by the window?",
            self.home, event_id="move-chair-window")
        self.assertEqual(committed["status"], "committed")
        after = self.furniture.audit_state()
        self.assertEqual(after["chair:parlor"]["anchor"], "parlor:window")
        self.assertEqual(after["table:parlor"], physical_before["table:parlor"])
        self.assertIn("beside the window", self.home.subject.observe()["inner"])

        self.do("walk", "leave-to-hall", station="station:hall")
        self.do("walk", "go-to-bedroom", station="station:bedroom")
        for i in range(4):
            self.clock.advance(240, event_id=f"evening-{i}")
        slept = self.home.subject.act("sleep", event_id="night-sleep")
        self.assertIn("slept", slept["inner"])
        self.do("walk", "morning-hall", station="station:hall")
        self.do("walk", "morning-parlor", station="station:parlor")
        morning = HomeArrangements(SpatialHabitat(self.world.path))
        self.assertEqual(morning.audit_state(), after)
        self.assertIn("beside the window", morning.observe()["inner"])
        self.assertIn("beside the window", self.home.subject.observe()["inner"])
        self.assertEqual(morning.verify()["revision"], 1)

    def test_furniture_can_turn_independently_and_other_object_remains_unchanged(self):
        self.parlor()
        table_before = self.furniture.audit_state()["table:parlor"]
        changed = act_intent(
            "Turn the chair to face the doorway",
            self.home, event_id="face-door")
        self.assertEqual(changed["status"], "committed")
        state = self.furniture.audit_state()
        self.assertEqual(state["chair:parlor"]["anchor"], "parlor:hearth")
        self.assertEqual(state["chair:parlor"]["facing"], "parlor:door")
        self.assertEqual(state["table:parlor"], table_before)
        self.assertIn("near the doorway", self.furniture.observe()["inner"])
        self.assertTrue(self.furniture.verify()["verified"])

    def test_occupied_space_stale_offer_and_no_op_cannot_become_fact(self):
        self.parlor()
        self.assertIsNone(self.offered(
            "arrange:move", object="chair:parlor", anchor="parlor:desk"))
        with self.assertRaises(Conflict):
            self.furniture.act("move", event_id="overlap-furniture",
                               object="chair:parlor", anchor="parlor:desk")
        earlier = self.offered(
            "arrange:move", object="chair:parlor", anchor="parlor:window")
        self.assertIsNotNone(earlier)
        self.do("arrange:turn", "turn-chair-door",
                object="chair:parlor", facing="parlor:door")
        with self.assertRaises(Conflict):
            self.home.act(earlier["offer_id"], event_id="stale-chair")
        self.assertEqual(self.furniture.audit_state()["chair:parlor"]["anchor"],
                         "parlor:hearth")
        self.assertEqual(self.furniture.verify()["revision"], 1)

    def test_unsupported_offscript_intent_never_manufactures_an_event(self):
        self.parlor()
        initial = self.furniture.audit_state()
        for words in (
                "Build a mahogany spiral staircase in the sitting room",
                "Move the table somewhere",
                "Move the chair and side table toward the window",
                "I think that I would like to move things",
                "Move the chair by the hearth"):
            result = act_intent(words, self.home,
                                event_id="unsupported-" + str(len(words)))
            self.assertNotEqual(result["status"], "committed")
        self.assertEqual(self.furniture.audit_state(), initial)
        self.assertEqual(self.furniture.verify()["revision"], 0)

    def test_darkness_hides_position_and_disallows_unseen_changes(self):
        self.parlor()
        for i in range(3):
            self.clock.advance(240, event_id=f"late-night-{i}")
        self.assertIsNone(self.offered(
            "arrange:move", object="chair:parlor", anchor="parlor:window"))
        self.assertNotIn("upholstered reading chair",
                         self.furniture.observe()["inner"])
        dark = act_intent("Move the chair by the window",
                          self.home, event_id="move-in-darkness")
        self.assertEqual(dark["status"], "not_currently_possible")
        self.do("light", "parlor-light")
        now = act_intent("Move the chair by the window",
                         self.home, event_id="move-with-lamp")
        self.assertEqual(now["status"], "committed")
        self.assertTrue(self.furniture.verify()["verified"])

    def test_room_changes_survive_world_fork_without_duplicating_its_history(self):
        self.parlor()
        self.do("arrange:move", "change-world-layout",
                object="chair:parlor", anchor="parlor:door")
        parent = self.furniture.audit_state()
        destination = self.root / "fork.sqlite3"
        self.world.fork_to(destination)
        child = HomeArrangements(SpatialHabitat(destination))
        self.assertEqual(parent, child.audit_state())
        self.assertEqual(child.verify()["revision"], 0)
        self.assertTrue(self.furniture.verify()["verified"])

    def test_source_tampering_is_detected_without_altering_the_old_home(self):
        self.parlor()
        self.do("arrange:move", "move-for-audit",
                object="chair:parlor", anchor="parlor:window")
        with sqlite3.connect(self.world.path) as db:
            row = db.execute(
                "SELECT envelope FROM arrangement_events WHERE event_id=?",
                ("move-for-audit",)).fetchone()
            envelope = json.loads(row[0])
            envelope["station"] = "station:bedroom"
            db.execute(
                "UPDATE arrangement_events SET envelope=? WHERE event_id=?",
                (json.dumps(envelope), "move-for-audit"))
        with self.assertRaises(Conflict):
            self.furniture.verify()
        self.assertTrue(HomeLife(self.world).verify()["verified"])
        self.assertTrue(self.clock.verify()["verified"])

    def test_existing_world_without_arrangement_profile_is_unaffected(self):
        from pretorius_lab.subject_port import SubjectPort
        older = SpatialHabitat.create(self.root / "old.sqlite3")
        HomeLife(older).initialize()
        DailyRhythm(older).initialize()
        self.assertTrue(SubjectPort(older).observe()["inner"].startswith("I "))
        self.assertTrue(DailyRhythm(older).verify()["verified"])


if __name__ == "__main__":
    unittest.main()
