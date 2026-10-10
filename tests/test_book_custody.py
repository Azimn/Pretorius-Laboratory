"""Accepted physical book custody changes across movement, reading and recovery."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pretorius_lab import LabError, Conflict
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.embodied_access import EmbodiedAccess
from pretorius_lab.book_custody import BookCustody
from pretorius_lab.book_library import BookLibrary
from pretorius_lab.shelf_annex import ShelfAnnex


class BookCustodyTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.lab = SpatialHabitat.create(self.root / "house.sqlite3")
        self.books = BookLibrary(self.lab)
        self.books.initialize()
        self.books.install("book:007", edition_id="test-v1",
                           title="Persistent Victorian Volume", author="Test",
                           pages=["A recorded first leaf.", "An unchanging second leaf."],
                           source_class="original_fixture", source_reference="synthetic test")
        self.body = EmbodiedAccess(self.lab)
        self.body.initialize()
        self.custody = BookCustody(self.lab)
        self.custody.initialize()

    def at(self, station):
        current = self.body.verify()["station"]
        if current != "station:center":
            self.body.move("station:center")
        self.body.move(station)

    def take_seventh(self):
        self.at("station:shelf:3")
        return self.body.take("book:007")

    def clear_bench(self):
        self.lab.commit({"op": "place", "object_id": "beaker:001",
                         "anchor_id": "floor:corner:se"})

    def test_take_removes_real_shelf_occupancy_and_survives_restart(self):
        initial = self.lab.scan("shelf:3")["positions"][6]["occupant"]
        self.assertEqual(initial["id"], "book:007")
        original_world = self.lab.verify()
        taken = self.take_seventh()
        self.assertEqual(taken["location"], {"anchor_id": None,
                                             "held_by": "research-subject:pretorius"})
        self.assertIsNone(self.lab.scan("shelf:3")["positions"][6]["occupant"])
        self.assertEqual(self.lab.locate("book:007")["location"]["placement"], "carried")
        self.assertEqual(self.body.look()["offered_payload"]["held_objects"][0]["object_id"],
                         "book:007")
        self.assertEqual(self.lab.verify(), original_world)
        restarted = BookCustody(SpatialHabitat(self.lab.path))
        self.assertEqual(restarted.verify()["revision"], 1)
        self.assertIsNone(SpatialHabitat(self.lab.path).scan("shelf:3")
                          ["positions"][6]["occupant"])

    def test_carry_to_bench_put_down_and_reopen_at_saved_place(self):
        self.clear_bench()
        self.take_seventh()
        self.body.book("book:007", "open")
        self.body.book("book:007", "turn", direction=1)
        self.body.book("book:007", "mark", bookmark_id="paper-flag")
        self.body.book("book:007", "close")
        self.body.move("station:center")
        self.body.move("station:bench")
        result = self.body.put("book:007", "bench:main/position:left")
        self.assertEqual(result["location"]["anchor_id"], "bench:main/position:left")
        self.assertEqual(self.lab.scan("bench:main")["positions"][0]["occupant"]["id"],
                         "book:007")
        self.assertEqual(self.body.look()["offered_payload"]["held_objects"], [])
        reread = EmbodiedAccess(SpatialHabitat(self.lab.path))
        reread.book("book:007", "open_mark", bookmark_id="paper-flag")
        self.assertEqual(reread.book("book:007", "read")["page_text"],
                         "An unchanging second leaf.")
        self.assertEqual(self.books.catalog("book:007")["book:007"]["bookmarks"],
                         {"paper-flag": 2})
        self.assertEqual(self.custody.verify()["revision"], 2)

    def test_subject_can_read_carried_book_but_not_other_distant_book(self):
        self.take_seventh()
        self.body.move("station:center")
        self.assertEqual(self.body.book("book:007", "open")["operation"], "open")
        self.assertEqual(self.body.book("book:007", "read")["page_text"],
                         "A recorded first leaf.")
        with self.assertRaises(LabError):
            self.body.book("book:006", "open")
        self.assertTrue(self.books.verify()["verified"])

    def test_reject_remote_pickup_and_drop_and_double_carry(self):
        with self.assertRaises(LabError):
            self.body.take("book:007")
        self.take_seventh()
        with self.assertRaises(LabError):
            self.body.take("book:006")
        with self.assertRaises(LabError):
            self.body.put("book:007", "shelf:1/slot:1")
        self.body.put("book:007", "shelf:3/slot:7")
        self.assertEqual(self.lab.scan("shelf:3")["positions"][6]["occupant"]["id"],
                         "book:007")
        self.assertEqual(self.custody.verify()["revision"], 2)

    def test_cannot_overlap_workbench_beaker(self):
        self.take_seventh()
        self.body.move("station:center")
        self.body.move("station:bench")
        with self.assertRaises(Conflict):
            self.body.put("book:007", "bench:main/position:left")
        self.assertIsNone(self.lab.scan("shelf:3")["positions"][6]["occupant"])
        self.clear_bench()
        self.body.put("book:007", "bench:main/position:left")
        self.assertEqual(self.lab.locate("book:007")["location"]["fixture"], "bench:main")

    def test_core_admin_cannot_teleport_custody_managed_book(self):
        self.take_seventh()
        with self.assertRaises(Conflict):
            self.lab.commit({"op": "place", "object_id": "book:007",
                             "anchor_id": "shelf:2/slot:1"})
        self.assertEqual(self.custody.verify()["revision"], 1)

    def test_annex_physical_book_moves_without_text_loss(self):
        annex = ShelfAnnex(self.lab)
        annex.initialize()
        annex.register("book:008", "shelf:1/slot:1", "Occult Source")
        self.books.install("book:008", edition_id="occult-v1",
                           title="Occult Source", author="Archivist",
                           pages=["Complete original excerpt."],
                           source_class="original_fixture",
                           source_reference="synthetic source")
        self.at("station:shelf:1")
        self.body.take("book:008")
        self.assertIsNone(self.lab.scan("shelf:1")["positions"][0]["occupant"])
        with self.assertRaises(Conflict):
            annex.move("book:008", "shelf:2/slot:2")
        self.body.move("station:center")
        self.body.move("station:shelf:2")
        self.body.put("book:008", "shelf:2/slot:1")
        self.assertEqual(self.lab.scan("shelf:2")["positions"][0]["occupant"]["id"],
                         "book:008")
        self.body.book("book:008", "open")
        self.assertEqual(self.body.book("book:008", "read")["page_text"],
                         "Complete original excerpt.")
        self.assertTrue(self.custody.verify()["verified"])

    def test_backup_and_fork_preserve_placed_book_separately(self):
        self.clear_bench()
        self.take_seventh()
        self.body.move("station:center")
        self.body.move("station:bench")
        self.body.put("book:007", "bench:main/position:left")
        backup = self.root / "snapshot.sqlite3"
        self.lab.backup_to(backup)
        restored = SpatialHabitat(backup)
        self.assertEqual(restored.locate("book:007")["location"]["fixture"], "bench:main")
        self.assertEqual(BookCustody(restored).verify()["revision"], 2)
        branchfile = self.root / "experiment.sqlite3"
        self.lab.fork_to(branchfile)
        fork = SpatialHabitat(branchfile)
        self.assertEqual(fork.locate("book:007")["location"]["fixture"], "bench:main")
        self.assertNotEqual(self.lab.verify()["world_epoch"],
                            fork.verify()["world_epoch"])
        forkactor = EmbodiedAccess(fork)
        forkactor.take("book:007")
        forkactor.move("station:center")
        forkactor.move("station:shelf:3")
        forkactor.put("book:007", "shelf:3/slot:7")
        self.assertEqual(self.lab.locate("book:007")["location"]["fixture"], "bench:main")
        self.assertEqual(fork.locate("book:007")["location"]["fixture"], "shelf:3")

    def test_fork_while_holding_preserves_possession_not_parent_history(self):
        self.take_seventh()
        root_revision = self.custody.verify()["revision"]
        target = self.root / "holding-fork.sqlite3"
        self.lab.fork_to(target)
        cloned = SpatialHabitat(target)
        self.assertEqual(BookCustody(cloned).verify()["revision"], 1)
        self.assertEqual(cloned.locate("book:007")["location"]["placement"], "carried")
        childactor = EmbodiedAccess(cloned)
        childactor.move("station:center")
        childactor.move("station:bench")
        with self.assertRaises(Conflict):
            childactor.put("book:007", "bench:main/position:left")
        childactor.move("station:center")
        childactor.move("station:shelf:3")
        childactor.put("book:007", "shelf:3/slot:7")
        self.assertEqual(self.custody.verify()["revision"], root_revision)
        self.assertEqual(self.lab.locate("book:007")["location"]["placement"], "carried")

    def test_repeat_event_and_custody_tamper_detection(self):
        self.at("station:shelf:3")
        a = self.body.take("book:007", event_id="carry-once")
        b = self.body.take("book:007", event_id="carry-once")
        self.assertEqual(a["event_hash"], b["event_hash"])
        self.assertEqual(self.custody.verify()["revision"], 1)
        with sqlite3.connect(self.lab.path) as db:
            db.execute("UPDATE custody_events SET event_hash=? WHERE revision=1",
                       ("f" * 64,))
        with self.assertRaises(Conflict):
            self.custody.verify()
        with self.assertRaises(Conflict):
            self.lab.backup_to(self.root / "invalid.sqlite3")

    def test_body_stays_same_station_on_failed_surface_action(self):
        self.at("station:shelf:3")
        before = self.body.verify()
        with self.assertRaises(LabError):
            self.body.put("book:007", "bench:main/position:left")
        self.assertEqual(self.body.verify(), before)
        self.assertEqual(self.custody.verify()["revision"], 0)


if __name__ == "__main__":
    unittest.main()
