"""End-to-end persisted dynamic botanical specimens and world-born artifacts."""
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.material_objects import MaterialObjects, DRY_MINUTES
from pretorius_lab.home_affordances import HomeAffordances
from pretorius_lab.physics import Conflict, LabError


class LivingBotanicalObjectTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.world = SpatialHabitat.create(self.root / "world.sqlite3")
        HomeLife(self.world).initialize()
        self.clock = DailyRhythm(self.world)
        self.clock.initialize(perishable_meals=True, physical_provisions=True,
                              visible_portions=True, physical_paper=True)
        self.material = MaterialObjects(self.world)
        self.material.initialize()
        self.home = HomeAffordances(self.world)

    def find(self, command, **args):
        matches = [o for o in self.home.discover()["offers"]
                   if o["command"] == command and o["args"] == args]
        return matches[0] if matches else None

    def do(self, command, eid, *, text=None, **args):
        choice = self.find(command, **args)
        self.assertIsNotNone(choice, (command, args, self.home.discover()))
        return self.home.act(choice["offer_id"], event_id=eid, text=text)

    def travel(self, route, prefix="travel"):
        for n, station in enumerate(route):
            self.do("walk", f"{prefix}{n}", station=station)

    def bring_flower_to_press(self):
        self.travel(["station:hall", "station:kitchen"], "to-kitchen")
        self.assertIsNotNone(self.find("material:take", object="plant:rose-001"))
        self.do("material:take", "collect-flower", object="plant:rose-001")
        self.travel(["station:hall", "station:parlor"], "to-parlor")
        self.do("open", "open-writing-desk", container="desk:parlor")
        self.assertIsNotNone(self.find(
            "material:start_press", flower="plant:rose-001"))
        self.do("material:start_press", "press-flower",
                flower="plant:rose-001")

    def day_passage(self):
        for i in range(DRY_MINUTES // 240):
            self.clock.advance(240, event_id=f"ordinary-day-{i}")

    def finish_and_label(self):
        self.day_passage()
        self.do("material:finish_press", "finish-press", flower="plant:rose-001")
        self.do("material:mount", "mount-real-specimen",
                specimen="specimen:0001")
        label = "Rosa species — dried under pressure; my first mounted flower."
        self.do("material:label", "label-real-specimen",
                text=label, specimen="specimen:0001")
        return label

    def test_sole_flower_material_is_placed_in_a_press_not_created_from_nothing(self):
        self.assertEqual(set(self.material.audit_state()["objects"]), {
            "plant:rose-001", "tool:flower-press",
            "supply:blotter", "sheet:herbarium-001"})
        self.bring_flower_to_press()
        state = self.material.audit_state()["objects"]
        self.assertEqual(state["plant:rose-001"]["stage"], "pressing")
        self.assertEqual(state["plant:rose-001"]["parent"], "tool:flower-press")
        self.assertNotIn("specimen:0001", state)
        self.assertTrue(self.material.verify()["verified"])

    def test_real_72_hour_drying_is_not_an_instant_success_flag(self):
        self.bring_flower_to_press()
        self.assertIsNone(self.find(
            "material:finish_press", flower="plant:rose-001"))
        before = self.material.audit_state()
        with self.assertRaises(Conflict):
            self.material.act("finish_press", event_id="cheat-time",
                              flower="plant:rose-001")
        self.assertEqual(self.material.audit_state(), before)
        for i in range(17):
            self.clock.advance(240, event_id=f"day-passing-{i}")
        self.assertIsNone(self.find("material:finish_press", flower="plant:rose-001"))
        self.clock.advance(240, event_id="real-72-hours")
        self.assertIsNotNone(self.find(
            "material:finish_press", flower="plant:rose-001"))
        self.assertTrue(self.material.verify()["verified"])

    def test_new_identity_is_created_with_provenance_and_exact_authored_label(self):
        self.bring_flower_to_press()
        label = self.finish_and_label()
        state = self.material.audit_state()
        self.assertEqual(state["next_specimen"], 2)
        self.assertEqual(state["objects"]["plant:rose-001"]["stage"], "transformed")
        specimen = state["objects"]["specimen:0001"]
        self.assertEqual(specimen["origin"], "plant:rose-001")
        self.assertEqual(specimen["parent"], "sheet:herbarium-001")
        self.assertEqual(specimen["stage"], "mounted")
        self.assertEqual(specimen["label"], label)
        self.assertIn(label, self.material.observe()["inner"])
        with self.assertRaises(Conflict):
            self.material.act("finish_press", flower="plant:rose-001")
        self.assertTrue(self.material.verify()["verified"])

    def test_finished_sheet_and_specimen_move_as_one_object_through_closed_trunk(self):
        self.bring_flower_to_press()
        label = self.finish_and_label()
        self.do("material:take", "lift-sheet", object="sheet:herbarium-001")
        self.travel(["station:hall"], "sheet-to-hall")
        # This interior passage has no daylight window. The real lamp is
        # required before the Doctor can identify or open the trunk.
        self.assertIsNone(self.find("open", container="trunk:hall"))
        self.do("light", "light-hall", )
        self.do("open", "open-trunk", container="trunk:hall")
        self.do("material:put", "store-herbarium",
                object="sheet:herbarium-001", container="trunk:hall")
        self.assertIn(label, self.material.observe()["inner"])
        self.do("close", "shut-trunk", container="trunk:hall")
        self.assertNotIn(label, self.material.observe()["inner"])
        reopened = MaterialObjects(SpatialHabitat(self.world.path))
        self.assertNotIn(label, reopened.observe()["inner"])
        self.do("open", "reopen-trunk", container="trunk:hall")
        self.assertIn(label, reopened.observe()["inner"])
        self.assertTrue(reopened.verify()["verified"])

    def test_original_world_fork_inherits_material_condition_not_parent_events(self):
        self.bring_flower_to_press()
        label = self.finish_and_label()
        fork = self.root / "other-future.sqlite3"
        self.world.fork_to(fork)
        child = MaterialObjects(SpatialHabitat(fork))
        self.assertTrue(child.verify()["verified"])
        self.assertEqual(child.audit_state(), self.material.audit_state())
        self.assertEqual(child.verify()["revision"], 0)
        self.assertIn(label, child.observe()["inner"])
        self.assertTrue(self.material.verify()["verified"])

    def test_foreign_or_duplicate_authored_actions_cannot_overwrite_history(self):
        self.bring_flower_to_press()
        before = self.material.audit_state()
        first = self.material.act("start_press", event_id="press-flower",
                                  flower="plant:rose-001")
        self.assertTrue(first["inner"].startswith("I "))
        self.assertEqual(self.material.audit_state(), before)
        with self.assertRaises(Conflict):
            self.material.act("take", event_id="press-flower",
                              object="plant:rose-001")
        with self.assertRaises(Conflict):
            self.material.act("label", event_id="invented-label",
                              specimen="specimen:0001", text="Not real")
        self.assertEqual(self.material.audit_state(), before)

    def test_material_receipt_tampering_fails_without_altering_the_original_world(self):
        self.bring_flower_to_press()
        with sqlite3.connect(self.world.path) as db:
            row = db.execute(
                "SELECT envelope FROM botanical_events WHERE event_id=?",
                ("press-flower",)).fetchone()
            record = json.loads(row[0])
            record["minute"] += 1
            db.execute("UPDATE botanical_events SET envelope=? WHERE event_id=?",
                       (json.dumps(record), "press-flower"))
        with self.assertRaises(Conflict):
            self.material.verify()
        self.assertTrue(self.clock.verify()["verified"])
        self.assertTrue(HomeLife(self.world).verify()["verified"])

    def test_no_material_prototype_affects_uninstalled_legacy_worlds(self):
        from pretorius_lab.subject_port import SubjectPort
        other = SpatialHabitat.create(self.root / "older.sqlite3")
        HomeLife(other).initialize()
        DailyRhythm(other).initialize()
        self.assertTrue(DailyRhythm(other).verify()["verified"])
        self.assertTrue(SubjectPort(other).observe()["inner"].startswith("I "))
        with self.assertRaises(LabError):
            MaterialObjects(other).verify()
        self.assertTrue(DailyRhythm(other).verify()["verified"])


if __name__ == "__main__":
    unittest.main()
