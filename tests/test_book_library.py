"""Source-bound reading and object-permanence acceptance tests."""
import json
import sqlite3
from pathlib import Path
import tempfile
import unittest

from pretorius_lab import Conflict, LabError
from pretorius_lab.book_library import BookLibrary
from pretorius_lab.habitat_v2 import SpatialHabitat


PAGES = [
    "The glass instrument stood on the oak bench. No change was recorded.",
    "During the second trial, a single bubble appeared. Its cause was not established.",
    "The observer closed the notebook. Future trials require an independent control.",
]


class BookPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = SpatialHabitat.create(self.root / "home.sqlite3")
        self.books = BookLibrary(self.home)
        self.books.initialize()

    def install(self, book_id="book:007"):
        return self.books.install(
            book_id, edition_id=f"fixture-{book_id.replace(':', '-')}-v1",
            title="A Short Laboratory Log", author="Synthetic fixture author",
            source_class="original_fixture",
            source_reference="test fixture: original material, not Pretorius canon",
            pages=PAGES,
        )

    def test_pages_exist_as_authorized_source_bytes_and_keep_their_order(self):
        self.install()
        with self.assertRaises(LabError):
            self.books.operate("book:007", "read")
        self.books.operate("book:007", "open")
        first = self.books.operate("book:007", "read")
        self.assertEqual(first["page"], 1)
        self.assertEqual(first["page_text"], PAGES[0])
        self.assertEqual(first["delivery_class"],
                         "page_offered_to_interface_not_proof_of_reading")
        self.books.operate("book:007", "turn", direction=1)
        second = self.books.operate("book:007", "read")
        self.assertEqual(second["page_text"], PAGES[1])
        self.assertEqual(BookLibrary(SpatialHabitat(self.home.path)).verify()["revision"], 5)

    def test_bookmark_keeps_place_through_restart(self):
        self.install()
        self.books.operate("book:007", "open")
        self.books.operate("book:007", "turn", direction=1)
        self.books.operate("book:007", "turn", direction=1)
        self.books.operate("book:007", "mark", bookmark_id="paper-slip")
        self.books.operate("book:007", "close")
        reopened = BookLibrary(SpatialHabitat(self.home.path))
        self.assertEqual(reopened.catalog("book:007")["book:007"]["bookmarks"],
                         {"paper-slip": 3})
        reopened.operate("book:007", "open_mark", bookmark_id="paper-slip")
        page = reopened.operate("book:007", "read")
        self.assertEqual(page["page"], 3)
        self.assertEqual(page["page_text"], PAGES[2])
        reopened.operate("book:007", "unmark", bookmark_id="paper-slip")
        self.assertEqual(reopened.catalog("book:007")["book:007"]["bookmarks"], {})
        self.assertTrue(reopened.verify()["verified"])

    def test_no_unbacked_book_pages_may_be_fabricated(self):
        with self.assertRaises(LabError):
            self.books.operate("book:004", "open")
        self.assertEqual(self.books.catalog(), {})
        self.assertEqual(self.books.verify()["revision"], 0)

    def test_read_only_room_observation_does_not_expose_text_or_coordinates(self):
        self.install()
        scene = self.home.observe()
        for word in PAGES:
            self.assertNotIn(word, json.dumps(scene))
        self.assertNotIn("xyz_mm", json.dumps(scene))
        self.assertNotIn("xyz_mm", json.dumps(self.home.scan("shelf:3")))
        self.assertNotIn("xyz_mm", json.dumps(self.home.locate("book:007")))
        self.assertIn("xyz_mm", json.dumps(self.home.inspect_object("book:007")))

    def test_duplicate_read_event_does_not_duplicate_historical_receipt(self):
        self.install()
        self.books.operate("book:007", "open")
        one = self.books.operate("book:007", "read", event_id="same-receipt")
        two = self.books.operate("book:007", "read", event_id="same-receipt")
        self.assertEqual(one["delivery_event_id"], two["delivery_event_id"])
        self.assertEqual(self.books.verify()["revision"], 3)
        with self.assertRaises(Conflict):
            self.books.operate("book:007", "close", event_id="same-receipt")

    def test_book_pages_immutable_after_installation(self):
        self.install()
        with self.assertRaises(Conflict):
            self.install()
        self.assertEqual(self.books.verify()["catalog_count"], 1)

    def test_book_history_detects_tampering_and_fails_closed(self):
        self.install()
        self.books.operate("book:007", "open")
        with sqlite3.connect(self.home.path) as db:
            row = db.execute("SELECT value FROM books_meta WHERE key='books'").fetchone()[0]
            value = json.loads(row)
            value["book:007"]["edition"]["pages"][0] = "Substituted fictitious text."
            db.execute("UPDATE books_meta SET value=? WHERE key='books'",
                       (json.dumps(value),))
        with self.assertRaises(Conflict):
            self.books.catalog("book:007")

    def test_wrong_physical_world_epoch_is_rejected(self):
        self.install()
        with sqlite3.connect(self.home.path) as db:
            db.execute("UPDATE books_meta SET value=? WHERE key='world_epoch'",
                       (json.dumps("other-epoch"),))
        with self.assertRaises(Conflict):
            self.books.verify()

    def test_backup_recovers_book_text_and_bookmark(self):
        self.install()
        self.books.operate("book:007", "open")
        self.books.operate("book:007", "mark", bookmark_id="blue-ribbon")
        backup = self.root / "backup.sqlite3"
        self.home.backup_to(backup)
        restored = BookLibrary(SpatialHabitat(backup))
        self.assertTrue(restored.verify()["verified"])
        self.assertEqual(restored.catalog("book:007")["book:007"]["bookmarks"],
                         {"blue-ribbon": 1})
        self.assertEqual(restored.operate("book:007", "read")["page_text"], PAGES[0])

    def test_fork_carries_books_and_marks_without_mutating_parent(self):
        self.install()
        self.books.operate("book:007", "open")
        self.books.operate("book:007", "turn", direction=1)
        self.books.operate("book:007", "mark", bookmark_id="research-note")
        forkpath = self.root / "chamber.sqlite3"
        self.home.fork_to(forkpath)
        fork = SpatialHabitat(forkpath)
        fork_books = BookLibrary(fork)
        self.assertTrue(fork_books.verify()["verified"])
        self.assertNotEqual(fork.verify()["world_epoch"], self.home.verify()["world_epoch"])
        self.assertEqual(fork_books.catalog("book:007")["book:007"]["bookmarks"],
                         {"research-note": 2})
        fork_books.operate("book:007", "turn", direction=1)
        self.assertEqual(fork_books.operate("book:007", "read")["page"], 3)
        self.assertEqual(self.books.catalog("book:007")["book:007"]["page_if_open"], 2)

    def test_wrong_actor_cannot_write_book_ledger(self):
        self.install()
        with self.assertRaises(LabError):
            self.books.operate("book:007", "open", actor="untrusted_actor")
        self.assertEqual(self.books.verify()["revision"], 1)

    def test_turn_and_bookmark_preconditions(self):
        self.install()
        for op, kwargs in [
            ("turn", {"direction": 1}),
            ("mark", {"bookmark_id": "ribbon"}),
            ("open_mark", {"bookmark_id": "ribbon"}),
            ("unmark", {"bookmark_id": "ribbon"}),
        ]:
            with self.subTest(op=op), self.assertRaises(LabError):
                self.books.operate("book:007", op, **kwargs)
        self.assertEqual(self.books.verify()["revision"], 1)


if __name__ == "__main__":
    unittest.main()
