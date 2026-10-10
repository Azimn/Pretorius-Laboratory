"""Observation receipts attest offered host facts, not consciousness or memory."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pretorius_lab import Conflict, LabError
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.observation_receipts import ObservationPort


class ObservationReceiptsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = SpatialHabitat.create(self.root / "home.sqlite3")
        self.port = ObservationPort(self.home)
        self.port.initialize()

    def test_shelf_offer_records_exact_objects_without_coordinates(self):
        event = self.port.expose("shelf", "shelf:3")
        offered = event["offered_payload"]
        self.assertEqual(offered["positions"][6]["occupant"]["id"], "book:007")
        self.assertNotIn("xyz_mm", json.dumps(event))
        self.assertEqual(event["delivery_class"],
                         "offered_to_interface_not_proof_of_reading_or_memory")
        again = ObservationPort(SpatialHabitat(self.home.path))
        self.assertEqual(again.verify()["sequence"], 1)

    def test_room_and_object_receipts_remain_separate(self):
        room = self.port.expose("room", "room:sanctum")
        obj = self.port.expose("object", "book:007")
        self.assertNotEqual(room["delivery_id"], obj["delivery_id"])
        self.assertEqual(obj["offered_payload"]["location"]["position"], 7)
        self.assertNotIn("xyz_mm", json.dumps(obj))
        self.assertEqual(self.port.verify()["sequence"], 2)

    def test_world_change_creates_attributable_new_observation(self):
        old = self.port.expose("object", "beaker:001")
        self.home.commit({"op": "break", "object_id": "beaker:001"})
        updated = self.port.expose("object", "beaker:001")
        self.assertEqual(old["offered_payload"]["condition"], "intact")
        self.assertEqual(updated["offered_payload"]["condition"], "broken")
        self.assertTrue(self.port.verify()["verified"])

    def test_duplicate_event_deduplicates_but_changed_payload_rejected(self):
        one = self.port.expose("room", "room:sanctum", delivery_id="fixture-room-1")
        again = self.port.expose("room", "room:sanctum", delivery_id="fixture-room-1")
        self.assertEqual(one["receipt_hash"], again["receipt_hash"])
        self.assertEqual(self.port.verify()["sequence"], 1)
        self.home.commit({"op": "break", "object_id": "beaker:001"})
        with self.assertRaises(Conflict):
            self.port.expose("room", "room:sanctum", delivery_id="fixture-room-1")

    def test_tampered_receipt_detected_and_backup_refused(self):
        self.port.expose("shelf", "shelf:3")
        with sqlite3.connect(self.home.path) as db:
            db.execute("UPDATE observation_events SET prev_hash=? WHERE sequence=1",
                       ("f" * 64,))
        with self.assertRaises(Conflict):
            self.port.verify()
        with self.assertRaises(Conflict):
            self.home.backup_to(self.root / "corrupt.sqlite3")

    def test_backup_retains_receipt_and_fork_resets_delivery_history(self):
        self.port.expose("room", "room:sanctum")
        backup = self.root / "home-backup.sqlite3"
        self.home.backup_to(backup)
        self.assertEqual(ObservationPort(SpatialHabitat(backup)).verify()["sequence"], 1)
        fork_path = self.root / "fork.sqlite3"
        self.home.fork_to(fork_path)
        child = ObservationPort(SpatialHabitat(fork_path))
        self.assertEqual(child.verify()["sequence"], 0)
        child.expose("object", "book:007")
        self.assertEqual(child.verify()["sequence"], 1)
        self.assertEqual(self.port.verify()["sequence"], 1)

    def test_untrusted_actor_blocked(self):
        with self.assertRaises(LabError):
            self.port.expose("room", "room:sanctum", actor="remote_unknown")
        self.assertEqual(self.port.verify()["sequence"], 0)


if __name__ == "__main__":
    unittest.main()
