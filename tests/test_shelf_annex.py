"""Non-destructive annex registration, movement, book text, and fork continuity."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pretorius_lab import Conflict, LabError
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.shelf_annex import ShelfAnnex
from pretorius_lab.book_library import BookLibrary
from pretorius_lab.observation_receipts import ObservationPort


class EsotericAnnexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = SpatialHabitat.create(self.root / "home.sqlite3")
        self.annex = ShelfAnnex(self.home)
        self.annex.initialize()

    def add(self):
        self.annex.register("book:008", "shelf:1/slot:1", "An Occult Volume",
                            event_id="register-8")

    def test_register_durable_physical_book_without_modifying_old_genesis(self):
        earlier = self.home.verify()
        self.add()
        self.assertEqual(self.home.verify(), earlier)
        again = SpatialHabitat(self.home.path)
        self.assertEqual(again.locate("book:008")["location"]["fixture"], "shelf:1")
        self.assertEqual(again.locate("book:008")["location"]["position"], 1)
        self.assertEqual(again.scan("shelf:1")["positions"][0]["occupant"]["id"], "book:008")
        self.assertEqual(again.observe()["objects"]["book:008"]["name"], "An Occult Volume")
        self.assertNotIn("xyz_mm", json.dumps(again.observe()))
        self.assertEqual(ShelfAnnex(again).verify()["revision"], 1)

    def test_core_object_cannot_overlap_registered_annex_book(self):
        self.add()
        with self.assertRaises(Conflict):
            self.home.commit({"op": "place", "object_id": "book:007",
                              "anchor_id": "shelf:1/slot:1"})
        with self.assertRaises(Conflict):
            self.annex.register("book:009", "shelf:1/slot:1", "Duplicate")
        with self.assertRaises(Conflict):
            self.annex.register("book:009", "shelf:3/slot:7", "Over existing core")
        self.assertEqual(self.home.verify()["revision"], 0)

    def test_additional_book_can_be_moved_exactly_once(self):
        self.add()
        self.annex.move("book:008", "shelf:2/slot:2")
        relocated = SpatialHabitat(self.home.path)
        self.assertIsNone(relocated.scan("shelf:1")["positions"][0]["occupant"])
        self.assertEqual(relocated.scan("shelf:2")["positions"][1]["occupant"]["id"],
                         "book:008")
        self.assertEqual(ShelfAnnex(relocated).verify()["revision"], 2)

    def test_persistent_readable_annex_text_and_bookmarks(self):
        self.add()
        lib = BookLibrary(self.home)
        lib.initialize()
        lib.install("book:008", edition_id="annex-edition-1",
                    title="An Occult Volume", author="Archival Fixture",
                    pages=["Original first textual leaf.", "Second textual leaf."],
                    source_class="original_fixture",
                    source_reference="Generated in test for noncanon fixture")
        self.assertEqual(self.home.scan("shelf:1")["positions"][0]["occupant"]["name"],
                         "An Occult Volume")
        lib.operate("book:008", "open")
        lib.operate("book:008", "turn", direction=1)
        lib.operate("book:008", "mark", bookmark_id="inked-slip")
        lib.operate("book:008", "close")
        resumed = BookLibrary(SpatialHabitat(self.home.path))
        resumed.operate("book:008", "open_mark", bookmark_id="inked-slip")
        self.assertEqual(resumed.operate("book:008", "read")["page_text"],
                         "Second textual leaf.")
        self.assertEqual(resumed.catalog("book:008")["book:008"]["bookmarks"],
                         {"inked-slip": 2})

    def test_corrupt_annex_event_detected_and_backup_refused(self):
        self.add()
        with sqlite3.connect(self.home.path) as db:
            db.execute("UPDATE annex_events SET prev_hash=? WHERE revision=1",
                       ("1" * 64,))
        with self.assertRaises(Conflict):
            self.annex.verify()
        with self.assertRaises(Conflict):
            self.home.backup_to(self.root / "corrupted.sqlite3")

    def test_annex_and_contents_survive_backup_and_fork(self):
        self.add()
        lib = BookLibrary(self.home)
        lib.initialize()
        lib.install("book:008", edition_id="original-edition",
                    title="An Occult Volume", author="A. Researcher",
                    pages=["First page", "Second page"],
                    source_class="original_fixture", source_reference="Synthetic test")
        lib.operate("book:008", "open")
        lib.operate("book:008", "mark", bookmark_id="test-marker")
        receipts = ObservationPort(self.home)
        receipts.initialize()
        receipts.expose("shelf", "shelf:1")
        backup = self.root / "backup.sqlite3"
        self.home.backup_to(backup)
        bk = SpatialHabitat(backup)
        self.assertEqual(ShelfAnnex(bk).verify()["count"], 1)
        self.assertEqual(BookLibrary(bk).verify()["catalog_count"], 1)
        self.assertEqual(ObservationPort(bk).verify()["sequence"], 1)
        fork_path = self.root / "fork.sqlite3"
        self.home.fork_to(fork_path)
        fork = SpatialHabitat(fork_path)
        self.assertEqual(ShelfAnnex(fork).items()["book:008"]["anchor_id"],
                         "shelf:1/slot:1")
        self.assertEqual(BookLibrary(fork).catalog("book:008")["book:008"]["bookmarks"],
                         {"test-marker": 1})
        self.assertEqual(ObservationPort(fork).verify()["sequence"], 0)
        ShelfAnnex(fork).move("book:008", "shelf:1/slot:2")
        self.assertEqual(self.home.locate("book:008")["location"]["position"], 1)
        self.assertEqual(fork.locate("book:008")["location"]["position"], 2)

    def test_registration_idempotence(self):
        self.add()
        self.annex.register("book:008", "shelf:1/slot:1", "An Occult Volume",
                            event_id="register-8")
        self.assertEqual(self.annex.verify()["revision"], 1)
        with self.assertRaises(Conflict):
            self.annex.register("book:008", "shelf:1/slot:2", "An Occult Volume",
                                event_id="register-8")

    def test_nonregistered_edition_stays_unreadable(self):
        lib = BookLibrary(self.home)
        lib.initialize()
        with self.assertRaises(LabError):
            lib.install("book:008", edition_id="no-physical-volume",
                        title="An Occult Volume", author="Example",
                        pages=["No book on the shelf."],
                        source_class="original_fixture", source_reference="Test fixture")


if __name__ == "__main__":
    unittest.main()
