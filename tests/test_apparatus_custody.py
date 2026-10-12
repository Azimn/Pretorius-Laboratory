"""Direct world-only acceptance for source-bound beaker custody.

No decoder, production Pretorius memory, model weights or Village state.
Original book event schema and actor interface remain unchanged.
"""
import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pretorius_lab import Conflict, LabError
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.embodied_access import EmbodiedAccess
from pretorius_lab.book_custody import BookCustody
from pretorius_lab.physical_affordances import PhysicalAffordances, BASE_PROFILE
from pretorius_lab.bench_instruments import BenchInstruments


class ApparatusCustodyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = SpatialHabitat.create(Path(self.temp.name) / "home.sqlite3")
        self.body = EmbodiedAccess(self.home)
        self.body.initialize()
        self.custody = BookCustody(self.home)
        self.custody.initialize()
        self.mechanics = PhysicalAffordances(self.home)
        self.mechanics.initialize()
        self.balance = BenchInstruments(self.home)
        self.balance.initialize()

    def walk(self, station):
        if self.body.verify()["station"] != "station:center":
            self.body.move("station:center")
        self.body.move(station)

    def cursor(self):
        return (self.home.verify()["revision"], self.body.verify()["revision"],
                self.custody.verify()["revision"], self.balance.verify()["revision"])

    def test_subject_clears_bench_without_operator_and_places_book(self):
        self.walk("station:bench")
        before = self.body.measure("balance:bench", "beaker:001", "mass_g")
        self.assertEqual(before["observation"]["value"], 325)
        self.body.take_apparatus("beaker:001")
        self.assertEqual(self.home.locate("beaker:001")["location"]["placement"],
                         "carried")
        self.assertIsNone(self.home.scan("bench:main")["positions"][0]["occupant"])
        self.assertEqual([x["object_id"] for x in self.body.look()["offered_payload"]["held_objects"]],
                         ["beaker:001"])
        with self.assertRaises(LabError):
            self.body.measure("balance:bench", "beaker:001", "mass_g")
        self.walk("station:corner:se")
        self.body.put_apparatus("beaker:001", "floor:corner:se")
        self.assertEqual(self.home.locate("beaker:001")["location"]["fixture"],
                         "floor:sanctum")
        self.walk("station:shelf:3")
        self.body.take("book:007")
        self.walk("station:bench")
        self.body.put("book:007", "bench:main/position:left")
        self.assertEqual(self.home.locate("book:007")["location"]["fixture"], "bench:main")
        self.assertEqual(self.home.verify()["revision"], 0)
        self.assertEqual(self.custody.verify()["revision"], 4)

    def test_one_hand_across_apparatus_and_books(self):
        self.walk("station:bench")
        self.body.take_apparatus("beaker:001")
        self.walk("station:shelf:3")
        before = self.cursor()
        with self.assertRaises(LabError):
            self.body.take("book:007")
        with self.assertRaises(LabError):
            self.body.put_apparatus("beaker:001", "shelf:3/slot:8")
        self.assertEqual(before, self.cursor())
        self.walk("station:corner:se")
        self.body.put_apparatus("beaker:001", "floor:corner:se")
        self.walk("station:shelf:3")
        self.body.take("book:007")
        self.walk("station:corner:se")
        before = self.cursor()
        with self.assertRaises(LabError):
            self.body.take_apparatus("beaker:001")
        self.assertEqual(before, self.cursor())
        self.assertTrue(self.custody.verify()["verified"])

    def test_distant_taken_broken_and_unregistered_objects_rejected(self):
        self.assertEqual(self.custody.verify()["revision"], 0)
        with self.assertRaises(LabError):
            self.body.take_apparatus("beaker:001")
        self.walk("station:bench")
        for target in ("book:007", "beaker:999", "table:001"):
            with self.subTest(target=target), self.assertRaises(LabError):
                self.body.take_apparatus(target)
        self.home.commit({"op": "break", "object_id": "beaker:001"})
        with self.assertRaises(LabError):
            self.body.take_apparatus("beaker:001")
        self.home.commit({"op": "collect", "object_id": "beaker:001"})
        with self.assertRaises(LabError):
            self.body.take_apparatus("beaker:001")
        self.assertEqual(self.custody.verify()["revision"], 0)

    def test_immutable_capacity_profile_blocks_overweight_apparatus(self):
        # A different fresh world may have a different labelled mechanical
        # test assumption. A profile already initialized cannot change.
        second = SpatialHabitat.create(Path(self.temp.name) / "heavy.sqlite3")
        actor = EmbodiedAccess(second)
        actor.initialize()
        BookCustody(second).initialize()
        p = copy.deepcopy(BASE_PROFILE)
        p["object_profiles"]["beaker:001"]["mass_g"] = 3200
        PhysicalAffordances(second).initialize(profile=p)
        actor.move("station:center")
        actor.move("station:bench")
        with self.assertRaisesRegex(LabError, "carrying capacity"):
            actor.take_apparatus("beaker:001")
        self.assertEqual(BookCustody(second).verify()["revision"], 0)

    def test_idempotent_receipts_and_stale_placement_conflict(self):
        self.walk("station:bench")
        a = self.body.take_apparatus("beaker:001", event_id="beaker-pickup")
        again = self.body.take_apparatus("beaker:001", event_id="beaker-pickup")
        self.assertEqual(a, again)
        self.assertEqual(self.custody.verify()["revision"], 1)
        with self.assertRaises(Conflict):
            self.body.put_apparatus("beaker:001", "bench:main/position:left",
                                    event_id="beaker-pickup")
        self.walk("station:corner:se")
        p = self.body.put_apparatus("beaker:001", "floor:corner:se",
                                    event_id="beaker-setdown")
        same = self.body.put_apparatus("beaker:001", "floor:corner:se",
                                       event_id="beaker-setdown")
        self.assertEqual(p, same)
        self.assertEqual(self.custody.verify()["revision"], 2)
        with self.assertRaises(Conflict):
            self.body.put_apparatus("beaker:001", "floor:corner:nw",
                                    event_id="beaker-setdown")

    def test_held_beaker_restart_backup_and_fork_without_false_sensing(self):
        self.walk("station:bench")
        self.body.take_apparatus("beaker:001")
        reopened = SpatialHabitat(self.home.path)
        self.assertEqual(reopened.locate("beaker:001")["location"]["placement"], "carried")
        backup_path = Path(self.temp.name) / "backup.sqlite3"
        self.home.backup_to(backup_path)
        self.assertEqual(SpatialHabitat(backup_path).locate("beaker:001")["location"]
                         ["placement"], "carried")
        fork_path = Path(self.temp.name) / "child.sqlite3"
        self.home.fork_to(fork_path)
        fork = SpatialHabitat(fork_path)
        child = EmbodiedAccess(fork)
        self.assertEqual(child.verify()["station"], "station:bench")
        self.assertEqual(BenchInstruments(fork).verify()["revision"], 0)
        self.assertNotEqual(fork.verify()["world_epoch"], self.home.verify()["world_epoch"])
        child.move("station:center")
        child.move("station:corner:se")
        child.put_apparatus("beaker:001", "floor:corner:se")
        self.assertEqual(fork.locate("beaker:001")["location"]["fixture"], "floor:sanctum")
        self.assertEqual(self.home.locate("beaker:001")["location"]["placement"], "carried")
        self.assertTrue(BookCustody(fork).verify()["verified"])

    def test_corrupted_apparatus_receipt_rejected(self):
        self.walk("station:bench")
        self.body.take_apparatus("beaker:001")
        with sqlite3.connect(self.home.path) as db:
            db.execute("UPDATE custody_events SET event_hash=? WHERE revision=1",
                       ("f" * 64,))
        with self.assertRaises(Conflict):
            self.custody.verify()
        with self.assertRaises(Conflict):
            self.home.backup_to(Path(self.temp.name) / "bad.sqlite3")


if __name__ == "__main__":
    unittest.main()
