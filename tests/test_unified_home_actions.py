"""Cross-domain real-world offers, bookmarks and meaningful state continuity."""
import tempfile
from pathlib import Path
import unittest

from pretorius_lab.book_library import BookLibrary
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_affordances import HomeAffordances
from pretorius_lab.home_arrangement import HomeArrangements
from pretorius_lab.home_life import HomeLife
from pretorius_lab.material_objects import MaterialObjects
from pretorius_lab.physics import Conflict, LabError
from pretorius_lab.unified_home_actions import UnifiedHomeActions


class UnifiedRealHomeTest(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.world = SpatialHabitat.create(self.root / "world.sqlite3")
        HomeLife(self.world).initialize()
        DailyRhythm(self.world).initialize(
            perishable_meals=True, physical_provisions=True,
            visible_portions=True, physical_paper=True)
        HomeArrangements(self.world).initialize()
        MaterialObjects(self.world).initialize()
        self.books = BookLibrary(self.world)
        self.books.initialize()
        self.books.install(
            "book:007", edition_id="source-fixture-1",
            title="Pretorius's Research Volume", author="Test fixture",
            pages=["The little copper instrument lay on the workbench.",
                   "I shall return to this observation tomorrow.",
                   "The apparatus remained arranged as before."],
            source_class="original_fixture",
            source_reference="tests: real source text, not Pretorius autobiography",
        )
        self.actions = UnifiedHomeActions(self.world)

    def offer(self, cmd, **args):
        return next((item for item in self.actions.discover()["offers"]
                     if item["command"] == cmd and item["args"] == args), None)

    def do(self, cmd, eid, *, text=None, **args):
        offer = self.offer(cmd, **args)
        self.assertIsNotNone(offer, (cmd, args))
        return self.actions.execute(offer["offer_id"], event_id=eid, text=text)

    def visit_parlor(self):
        self.do("walk", "to-hall", station="station:hall")
        self.do("walk", "to-parlor", station="station:parlor")

    def visit_shelf3(self):
        self.do("walk", "to-center", station="station:center")
        self.do("walk", "to-shelf", station="station:shelf:3")

    def test_one_catalog_preserves_material_paper_and_furniture_actions(self):
        initial = self.actions.discover()
        self.assertEqual(initial, self.actions.discover())
        self.assertEqual(set(initial["subject_frame"]), {"inner", "spoken_aloud"})
        self.assertTrue(initial["subject_frame"]["inner"].startswith("I "))
        self.assertTrue(all(item["description"].startswith("I could ")
                            for item in initial["offers"]))
        self.assertFalse(any(item["command"] == "book" for item in initial["offers"]))
        self.visit_parlor()
        self.assertIsNotNone(self.offer(
            "arrange:move", object="chair:parlor", anchor="parlor:window"))
        chair = self.do("arrange:move", "chair-to-window",
                        object="chair:parlor", anchor="parlor:window")
        self.assertEqual(chair["source_table"], "arrangement_events")
        self.assertEqual(len(chair["source_event_hash"]), 64)
        self.do("open", "open-desk", container="desk:parlor")
        paper = self.offer("write_paper")
        self.assertTrue(paper["requires_my_own_words"])
        msg = "The chair remains by the window. I intend to read later."
        written = self.do("write_paper", "authored-note", text=msg)
        self.assertIn(msg, written["subject"]["inner"])
        reopened = UnifiedHomeActions(SpatialHabitat(self.world.path))
        self.assertIn("beside the window", reopened.subject.observe()["inner"])
        self.assertEqual(
            DailyRhythm(self.world).audit_state()["paper_marks"], [msg])

    def test_physically_bookmarked_page_survives_real_sleep_and_restart(self):
        self.visit_shelf3()
        self.assertIsNotNone(self.offer(
            "book", book_id="book:007", operation="open"))
        self.do("book", "open-volume", book_id="book:007", operation="open")
        read = self.do("book", "read-page-one",
                       book_id="book:007", operation="read")
        self.assertIn("copper instrument", read["subject"]["inner"])
        self.do("book", "page-forward", book_id="book:007",
                operation="turn", direction=1)
        marked = self.offer(
            "book", book_id="book:007", operation="mark",
            bookmark_id="page-flag-1")
        self.assertIsNotNone(marked)
        mark = self.actions.execute(
            marked["offer_id"], event_id="place-real-bookmark")
        self.assertEqual(mark["source_table"], "books_events")
        self.do("book", "close-volume",
                book_id="book:007", operation="close")
        self.assertEqual(
            self.books.catalog("book:007")["book:007"]["bookmarks"],
            {"page-flag-1": 2})
        # World clock moves; a bookmark belongs to the book, not yesterday.
        clock = DailyRhythm(self.world)
        for i in range(6):
            clock.advance(240, event_id=f"next-day-{i}")
        reopened = UnifiedHomeActions(SpatialHabitat(self.world.path))
        at_marker = next(x for x in reopened.discover()["offers"]
                         if x["command"] == "book" and
                         x["args"] == {"book_id": "book:007",
                                      "operation": "open_mark",
                                      "bookmark_id": "page-flag-1"})
        reopened.execute(at_marker["offer_id"], event_id="return-to-mark")
        reread = reopened.execute(
            next(x["offer_id"] for x in reopened.discover()["offers"]
                 if x["command"] == "book" and
                 x["args"] == {"book_id": "book:007", "operation": "read"}),
            event_id="return-to-second-page")
        self.assertIn("return to this observation tomorrow", reread["subject"]["inner"])
        self.assertEqual(
            self.books.catalog("book:007")["book:007"]["page_if_open"], 2)
        self.assertTrue(self.books.verify()["verified"])

    def test_book_changes_stale_offer_no_fabricated_page(self):
        self.visit_shelf3()
        open_offer = self.offer(
            "book", book_id="book:007", operation="open")
        self.do("book", "open-then-stale", book_id="book:007", operation="open")
        with self.assertRaises(Conflict):
            self.actions.execute(open_offer["offer_id"], event_id="fake-reopen")
        with self.assertRaises(LabError):
            self.actions.execute("0" * 64, event_id="invented-book-page")
        self.assertEqual(self.books.catalog("book:007")["book:007"]["page_if_open"], 1)

    def test_offstage_book_is_not_offered_as_global_reading_knowledge(self):
        initial = self.actions.discover()
        self.assertFalse(any(x["command"] == "book" for x in initial["offers"]))
        self.visit_parlor()
        self.assertFalse(any(x["command"] == "book" for x in self.actions.discover()["offers"]))
        self.assertTrue(self.books.verify()["verified"])

    def test_provenance_of_experimental_botanical_items_without_duplicate_world(self):
        self.do("walk", "to-hall", station="station:hall")
        self.do("walk", "to-kitchen", station="station:kitchen")
        flower = self.do("material:take", "pickup-real-rose",
                         object="plant:rose-001")
        self.assertEqual(flower["source_table"], "botanical_events")
        self.assertEqual(
            MaterialObjects(self.world).audit_state()["objects"]
            ["plant:rose-001"]["parent"], "research-subject:pretorius")
        self.assertTrue(MaterialObjects(self.world).verify()["verified"])

    def test_no_performance_quota_and_unselected_offers_never_create_events(self):
        first = self.actions.discover()
        self.actions.discover()
        with self.world._open() as db:
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM botanical_events").fetchone()[0], 0)
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM arrangement_events").fetchone()[0], 0)
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM books_events "
                "WHERE event_id LIKE 'place-real%'").fetchone()[0], 0)
        self.assertEqual(first, self.actions.discover())


if __name__ == "__main__":
    unittest.main()
