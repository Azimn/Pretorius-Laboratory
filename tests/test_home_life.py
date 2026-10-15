"""Permanent domestic possessions and non-deliberative body-reflex regression."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pretorius_lab.embodied_access import EmbodiedAccess
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.physics import Conflict, LabError


class DomesticLifeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.lab = SpatialHabitat.create(Path(self.temp.name) / "laboratory.sqlite3")
        self.home = HomeLife(self.lab)
        self.home.initialize()

    def walk_to(self, *stations):
        return [self.home.walk(station) for station in stations]

    def test_home_rooms_and_closed_furniture_appear_from_body_position(self):
        self.assertEqual(self.home.verify()["revision"], 0)
        self.assertTrue(self.home.look()["inner"].startswith("I am in my laboratory."))
        self.walk_to("station:hall", "station:bedroom")
        first = self.home.look()["inner"]
        self.assertIn("wardrobe (closed)", first)
        self.assertNotIn("heavy wool coat", first)
        self.home.open("wardrobe:bedroom")
        self.assertIn("heavy wool coat", self.home.look()["inner"])
        self.home.close("wardrobe:bedroom")
        self.assertNotIn("heavy wool coat", self.home.look()["inner"])
        self.assertEqual(self.lab.verify()["revision"], 0)

    def test_real_object_moves_across_rooms_and_remains_on_restart(self):
        self.walk_to("station:hall", "station:bedroom")
        self.home.open("wardrobe:bedroom")
        self.home.take("garment:coat")
        self.walk_to("station:hall", "station:parlor")
        self.home.open("desk:parlor")
        put = self.home.put("garment:coat", "desk:parlor")
        self.assertIn("writing desk", put["inner"])
        reopened = HomeLife(SpatialHabitat(self.lab.path))
        self.assertIn("heavy wool coat", reopened.look()["inner"])
        self.assertEqual(reopened.audit_state()["items"]["garment:coat"]["container"],
                         "desk:parlor")
        self.walk_to("station:hall", "station:bedroom")
        self.home.open("wardrobe:bedroom") if not self.home.audit_state()["containers"]["wardrobe:bedroom"]["open"] else None
        self.assertNotIn("heavy wool coat", self.home.look()["inner"])
        self.assertTrue(reopened.verify()["verified"])

    def test_reflex_speech_is_automatic_and_surprises_the_subject(self):
        steps = self.walk_to("station:hall", "station:shop:private")
        reflex = steps[-1]
        self.assertEqual(reflex["spoken_aloud"], "Ow! My foot!")
        self.assertIn("That was aloud?", reflex["inner"])
        self.assertIn("I had not meant", reflex["inner"])
        # A logged physical move, not an instruction to synthesize dialogue.
        with self.lab._open() as db:
            row = db.execute(
                "SELECT envelope FROM domestic_events WHERE revision=2").fetchone()
            event = json.loads(row[0])
            body = db.execute(
                "SELECT envelope FROM embodied_events WHERE revision=2").fetchone()
        self.assertEqual(event["op"], "walk")
        self.assertEqual(event["body_revision"], 2)
        self.assertEqual(event["station"], "station:shop:private")
        self.assertEqual(event["subject"], reflex)
        self.assertNotIn("world_epoch", reflex["inner"])
        self.assertNotIn("nociception=", reflex["inner"])
        self.assertEqual(HomeLife(SpatialHabitat(self.lab.path)).verify()["revision"], 2)

    def test_moving_stool_prevents_reflex_in_identical_future_room(self):
        self.walk_to("station:hall", "station:shop:private")
        self.home.shift_stool(obstructs_path=False)
        self.home.walk("station:hall")
        second = self.home.walk("station:shop:private")
        self.assertIsNone(second["spoken_aloud"])
        self.assertNotIn("My foot catches", second["inner"])
        self.assertFalse(self.home.audit_state()["low_stool_obstructs_path"])

    def test_unrelated_person_only_at_subject_station_and_one_hand_limit(self):
        self.walk_to("station:hall", "station:kitchen")
        with self.assertRaises(LabError):
            self.home.open("wardrobe:bedroom")
        with self.assertRaises(LabError):
            self.home.take("garment:coat")
        self.home.open("cupboard:kitchen")
        self.home.take("tableware:teapot")
        with self.assertRaises(Conflict):
            self.home.take("tableware:cup")
        with self.assertRaises(LabError):
            self.home.put("tableware:teapot", "wardrobe:bedroom")
        self.assertEqual(self.home.audit_state()["items"]["tableware:teapot"]["held_by"],
                         "research-subject:pretorius")

    def test_shop_manifest_is_small_closed_and_scoped_to_shop_stock(self):
        manifest = self.home.shop_manifest()
        self.assertFalse(manifest["shop_open"])
        self.assertEqual(manifest["mode"], "read_only_not_a_village_sale")
        self.assertEqual([x["object_id"] for x in manifest["stock"]],
                         ["curiosity:compass", "curiosity:crystal"])
        self.assertNotIn("food:tea", str(manifest))
        self.assertNotIn("garment:coat", str(manifest))
        self.assertNotIn("case:specimens", str(manifest))
        self.walk_to("station:hall", "station:shop:private")
        self.assertIn("OPENING SOON", self.home.look()["inner"])
        self.home.open("display:shop")
        self.home.take("curiosity:compass")
        self.assertEqual([x["object_id"] for x in self.home.shop_manifest()["stock"]],
                         ["curiosity:crystal"])
        self.home.put("curiosity:compass", "counter:shop")
        self.assertEqual([x["object_id"] for x in self.home.shop_manifest()["stock"]],
                         ["curiosity:crystal"])
        self.assertNotIn("garment:coat", json.dumps(self.home.shop_manifest()))

    def test_crash_gap_reconciles_embodied_motion_once(self):
        body = EmbodiedAccess(self.lab)
        body.move("station:hall", event_id="step-to-hall")
        body.move("station:shop:private", event_id="step-to-shop")
        self.assertEqual(self.home.verify()["pending_body_events"], 2)
        self.home.look()
        self.assertEqual(self.home.verify()["pending_body_events"], 0)
        with self.lab._open() as db:
            events = [json.loads(row[0]) for row in db.execute(
                "SELECT envelope FROM domestic_events ORDER BY revision")]
        self.assertEqual([x["op"] for x in events], ["walk", "walk", "look"])
        self.assertEqual(events[1]["subject"]["spoken_aloud"], "Ow! My foot!")
        self.home.look()
        with self.lab._open() as db:
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM domestic_events WHERE op='walk'").fetchone()[0], 2)
        self.assertTrue(self.home.verify()["verified"])

    def test_replay_event_identity_and_state_tampering_detection(self):
        self.home.walk("station:hall", event_id="same-move")
        before = self.home.verify()
        self.assertEqual(self.home.walk("station:hall", event_id="same-move")["spoken_aloud"], None)
        self.assertEqual(self.home.verify(), before)
        with self.assertRaises(Conflict):
            self.home.walk("station:bedroom", event_id="same-move")
        with self.lab._open() as db:
            value = json.loads(db.execute(
                "SELECT value FROM domestic_meta WHERE key='state'").fetchone()[0])
            value["shop_open"] = True
            db.execute("UPDATE domestic_meta SET value=? WHERE key='state'",
                       (json.dumps(value),))
        with self.assertRaises(Conflict):
            self.home.verify()

    def test_full_sqlite_backup_includes_domestic_history(self):
        self.walk_to("station:hall", "station:bedroom")
        self.home.open("wardrobe:bedroom")
        self.home.take("garment:coat")
        backup = Path(self.temp.name) / "backup.sqlite3"
        self.lab.backup_to(backup)
        copy = HomeLife(SpatialHabitat(backup))
        self.assertEqual(copy.audit_state()["items"]["garment:coat"]["held_by"],
                         "research-subject:pretorius")
        self.assertEqual(copy.verify()["revision"], self.home.verify()["revision"])

    def test_installation_is_non_destructive_and_refuses_reseed(self):
        before = self.home.verify()
        self.home.initialize()
        self.assertEqual(before, self.home.verify())
        self.walk_to("station:hall", "station:kitchen")
        self.home.open("cupboard:kitchen")
        after = self.home.verify()
        self.home.initialize()
        self.assertEqual(after, self.home.verify())


if __name__ == "__main__":
    unittest.main()
