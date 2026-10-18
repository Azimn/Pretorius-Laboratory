"""End-to-end one-world action offers: books, material world and furniture.

The test uses actual existing source owners. No fake book page, synthetic
bookmark, or duplicate furniture/world state is introduced by the bus.
"""
from pathlib import Path
import tempfile
import unittest

from pretorius_lab.book_library import BookLibrary
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.home_arrangement import HomeArrangements
from pretorius_lab.living_action_port import LivingActionPort
from pretorius_lab.physics import Conflict, LabError


class RealLivingActionPortTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.world = SpatialHabitat.create(self.root / "home.sqlite3")
        HomeLife(self.world).initialize()
        self.clock = DailyRhythm(self.world)
        self.clock.initialize(perishable_meals=True, physical_provisions=True,
                              visible_portions=True, physical_paper=True)
        self.room = HomeArrangements(self.world)
        self.room.initialize()
        self.books = BookLibrary(self.world)
        self.books.initialize()
        self.books.install(
            "book:007", edition_id="synthetic-pages",
            title="A Physicist's Observations", author="Invented fixture",
            pages=[
                "My first account of the polished glass instrument.",
                "I set aside a page for the botanical specimen.",
                "The remainder of this account is reserved for later use.",
            ],
            source_class="original_fixture",
            source_reference="Integration test fixture; not real Victorian text",
        )
        self.actions = LivingActionPort(self.world)

    def find(self, command, **args):
        return next((item for item in self.actions.discover()["offers"]
                     if item["command"] == command and item["args"] == args),
                    None)

    def do(self, command, event_id, *, text=None, bookmark_id=None, **args):
        item = self.find(command, **args)
        self.assertIsNotNone(item, (command, args))
        return self.actions.act(
            item["offer_id"], event_id=event_id, text=text,
            bookmark_id=bookmark_id)

    def walk(self, *stations, label="move"):
        for i, station in enumerate(stations):
            self.do("walk", f"{label}-{i}", station=station)

    def test_book_is_only_offered_at_reachable_location_and_pages_are_real(self):
        self.assertIsNone(self.find(
            "book", book_id="book:007", operation="open"))
        self.walk("station:center", "station:shelf:3", label="approach-shelf")
        observed = self.actions.discover()
        self.assertEqual(set(observed["subject_frame"]), {"inner", "spoken_aloud"})
        self.assertNotIn("polished glass instrument", observed["subject_frame"]["inner"])
        self.assertNotIn("world_epoch", observed["subject_frame"]["inner"])
        before = self.books.catalog()
        self.assertEqual(before, self.books.catalog())
        self.assertIsNotNone(self.find("book", book_id="book:007", operation="open"))
        opening = self.do("book", "open-volume", book_id="book:007", operation="open")
        self.assertEqual(opening["source"]["source_table"], "books_events")
        self.assertTrue(opening["source"]["verified"])
        read = self.do("book", "read-authentic-page",
                       book_id="book:007", operation="read")
        self.assertIn("polished glass instrument", read["subject"]["inner"])
        self.assertNotIn("original_fixture", read["subject"]["inner"])
        self.assertEqual(self.books.verify()["revision"], 3)

    def test_physically_bookmarked_page_and_moved_chair_both_survive_next_day(self):
        self.walk("station:center", "station:shelf:3", label="visit-library")
        self.do("book", "first-open", book_id="book:007", operation="open")
        self.do("book", "turn-one", book_id="book:007", operation="turn", direction=1)
        tag = self.do("book", "mark-page", bookmark_id="pressed-rose-note",
                      book_id="book:007", operation="mark")
        self.assertEqual(tag["source"]["source_table"], "books_events")
        self.do("book", "close-after-mark", book_id="book:007", operation="close")
        bookmark = self.books.catalog("book:007")["book:007"]["bookmarks"]
        self.assertEqual(bookmark, {"pressed-rose-note": 2})

        self.walk("station:center", "station:threshold", "station:hall",
                  "station:parlor", label="parlor-first")
        changed = self.do("arrange:move", "move-chair-by-window",
                          object="chair:parlor", anchor="parlor:window")
        self.assertEqual(changed["source"]["source_table"], "arrangement_events")
        physical = self.room.audit_state()
        self.assertIn("beside the window", self.actions.discover()["subject_frame"]["inner"])
        self.walk("station:hall", "station:bedroom", label="bedtime")
        # World-time advance is an actual DailyRhythm event, not a host label
        # that pretends eight hours passed.
        for n in range(4):
            self.clock.advance(240, event_id=f"late-hour-{n}")
        self.do("sleep", "real-sleep")
        self.walk("station:hall", "station:parlor", label="next-day-parlor")
        again = LivingActionPort(SpatialHabitat(self.world.path))
        self.assertEqual(HomeArrangements(self.world).audit_state(), physical)
        self.assertIn("beside the window", again.discover()["subject_frame"]["inner"])

        again.home.subject.act("walk", station="station:hall", event_id="back-hall")
        again.home.subject.act("walk", station="station:threshold", event_id="back-threshold")
        again.home.subject.act("walk", station="station:center", event_id="back-center")
        again.home.subject.act("walk", station="station:shelf:3", event_id="back-shelf")
        remembered_page = next(
            o for o in again.discover()["offers"] if o["command"] == "book"
            and o["args"] == {"book_id": "book:007", "operation": "open_mark",
                             "bookmark_id": "pressed-rose-note"})
        again.act(remembered_page["offer_id"], event_id="return-to-bookmark")
        second = next(o for o in again.discover()["offers"]
                      if o["command"] == "book" and
                      o["args"] == {"book_id": "book:007", "operation": "read"})
        received = again.act(second["offer_id"], event_id="read-page-two")
        self.assertIn("botanical specimen", received["subject"]["inner"])
        self.assertEqual(self.books.catalog("book:007")["book:007"]["bookmarks"],
                         {"pressed-rose-note": 2})
        self.assertTrue(self.room.verify()["verified"])
        self.assertTrue(self.books.verify()["verified"])

    def test_book_offer_is_stale_after_page_turn_without_mutating_again(self):
        self.walk("station:center", "station:shelf:3", label="to-book")
        self.do("book", "open-for-staleness", book_id="book:007", operation="open")
        old_read = self.find("book", book_id="book:007", operation="read")
        self.do("book", "turn-verified-page", book_id="book:007",
                operation="turn", direction=1)
        rev = self.books.verify()["revision"]
        with self.assertRaises(Conflict):
            self.actions.act(old_read["offer_id"], event_id="stale-book-read")
        self.assertEqual(self.books.verify()["revision"], rev)

    def test_unsupported_or_forged_action_cannot_write_world(self):
        original = self.clock.audit_state()
        with self.assertRaises(Conflict):
            self.actions.act("0" * 64, event_id="fabricated")
        with self.assertRaises(LabError):
            self.actions.act("0" * 64, event_id="bad", text="Imaginary chapter")
        self.assertEqual(original, self.clock.audit_state())
        self.assertTrue(self.books.verify()["verified"])

    def test_missing_bookmark_id_never_claims_saved_reading_position(self):
        self.walk("station:center", "station:shelf:3", label="shelf-note")
        self.do("book", "open-for-mark", book_id="book:007", operation="open")
        offer = self.find("book", book_id="book:007", operation="mark")
        self.assertTrue(offer["requires_bookmark_id"])
        before = self.books.verify()["revision"]
        with self.assertRaises(LabError):
            self.actions.act(offer["offer_id"], event_id="forgot-marker")
        self.assertEqual(self.books.verify()["revision"], before)
        self.assertEqual(self.books.catalog("book:007")["book:007"]["bookmarks"], {})

    def test_old_v5_home_without_book_ledger_still_works(self):
        separate = SpatialHabitat.create(self.root / "no-books.sqlite3")
        HomeLife(separate).initialize()
        DailyRhythm(separate).initialize(
            perishable_meals=True, physical_provisions=True,
            visible_portions=True, physical_paper=True)
        old = LivingActionPort(separate)
        seen = old.discover()
        self.assertTrue(seen["subject_frame"]["inner"].startswith("I "))
        self.assertFalse(any(o["command"] == "book" for o in seen["offers"]))
        first = next(x for x in seen["offers"] if x["command"] == "walk")
        outcome = old.act(first["offer_id"], event_id="old-world-walk")
        self.assertEqual(outcome["source"]["source_table"], "domestic_events")
        self.assertTrue(DailyRhythm(separate).verify()["verified"])


if __name__ == "__main__":
    unittest.main()
