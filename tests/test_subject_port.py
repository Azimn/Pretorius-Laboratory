"""Opt-in first-person interface and non-bypassable legacy physics gates."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pretorius_lab.physics import Conflict, LabError
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.embodied_access import EmbodiedAccess
from pretorius_lab.subject_port import SubjectPort
from pretorius_lab.book_library import BookLibrary
from pretorius_lab.book_custody import BookCustody
from pretorius_lab.physical_affordances import PhysicalAffordances
from pretorius_lab.bench_instruments import BenchInstruments


class SubjectPortTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.lab = SpatialHabitat.create(Path(self.temp.name) / "integrated.sqlite3")
        self.home = HomeLife(self.lab)
        self.home.initialize()
        self.daily = DailyRhythm(self.lab)
        self.daily.initialize()
        self.port = SubjectPort(self.lab)
        self.body = EmbodiedAccess(self.lab)

    def walk(self, *stations):
        result = None
        for station in stations:
            result = self.port.act("walk", station=station)
        return result

    def night(self):
        self.daily.advance(240)
        self.daily.advance(240)
        self.daily.advance(240)  # 19:00 in the same laboratory epoch

    def test_only_first_person_frames_leave_port(self):
        first = self.port.act("look")
        self.assertEqual(set(first), {"inner", "spoken_aloud"})
        self.assertTrue(first["inner"].startswith("I "))
        self.assertIsNone(first["spoken_aloud"])
        for token in ("lab_id", "world_epoch", "rhythm_meta", "fatigue=",
                      "revision", "head_hash", "mm]", "embodied_events"):
            self.assertNotIn(token, json.dumps(first))
        self.assertTrue(self.daily.verify()["verified"])
        self.assertTrue(self.home.verify()["verified"])

    def test_darkness_masks_old_body_scene_and_household_contents(self):
        self.walk("station:hall", "station:bedroom")
        clear = self.port.observe()["inner"]
        self.assertIn("wardrobe", clear)
        self.assertNotIn("heavy wool coat", clear)
        self.port.act("open", container="wardrobe:bedroom")
        self.assertIn("heavy wool coat", self.port.observe()["inner"])
        self.night()
        frame = self.port.observe()["inner"]
        self.assertIn("too dark", frame)
        self.assertNotIn("wardrobe", frame)
        self.assertNotIn("heavy wool coat", frame)
        body = self.body.look()["offered_payload"]
        self.assertEqual(body["nearby_objects"], [])
        self.assertEqual(body["perceived_features"], ["darkness"])
        with self.assertRaisesRegex(Conflict, "dark"):
            self.home.look()
        self.port.act("light")
        self.assertIn("heavy wool coat", self.port.observe()["inner"])

    def test_automatic_spoken_reflex_and_aftereffects_share_one_body(self):
        self.walk("station:hall")
        stumble = self.port.act("walk", station="station:shop:private")
        self.assertEqual(stumble["spoken_aloud"], "Ow! My foot!")
        self.assertIn("That was aloud?", stumble["inner"])
        self.assertEqual(self.home.audit_state()["body"]["reflexes"], 1)
        self.assertEqual(self.body.verify()["station"], "station:shop:private")
        reopened = SubjectPort(SpatialHabitat(self.lab.path))
        self.assertIn("I am", reopened.observe()["inner"])
        self.port.act("shift_stool", obstructs_path=False)
        self.walk("station:hall")
        second = self.port.act("walk", station="station:shop:private")
        self.assertIsNone(second["spoken_aloud"])

    def test_legacy_home_handling_cannot_skip_darkness(self):
        self.walk("station:hall", "station:bedroom")
        self.port.act("open", container="wardrobe:bedroom")
        self.night()
        before = self.home.verify()["revision"]
        with self.assertRaisesRegex(Conflict, "dark"):
            self.home.take("garment:coat")
        with self.assertRaisesRegex(Conflict, "dark"):
            self.port.act("take", item="garment:coat")
        self.assertEqual(self.home.verify()["revision"], before)
        self.port.act("light")
        self.port.act("take", item="garment:coat")
        self.assertEqual(self.home.audit_state()["items"]["garment:coat"]["container"], None)

    def test_legacy_book_does_not_read_without_light_even_without_port(self):
        books = BookLibrary(self.lab)
        books.initialize()
        books.install("book:007", edition_id="source", title="Field Notes",
                      author="Fixture", pages=["The ink was still wet."],
                      source_class="original_fixture",
                      source_reference="test fixture only")
        self.walk("station:center", "station:shelf:3")
        self.night()
        with self.assertRaisesRegex(Conflict, "dark"):
            self.body.book("book:007", "open")
        with self.assertRaisesRegex(Conflict, "dark"):
            self.home.look()
        self.assertEqual(books.verify()["revision"], 1)
        self.port.act("light")
        self.port.act("book", book_id="book:007", operation="open")
        page = self.port.act("book", book_id="book:007", operation="read")
        self.assertIn("I read a page of Field Notes", page["inner"])
        self.assertIn("The ink was still wet.", page["inner"])
        self.assertNotIn("content_digest", json.dumps(page))
        self.assertEqual(books.verify()["revision"], 3)

    def test_legacy_book_custody_cannot_move_physical_book_in_dark(self):
        BookCustody(self.lab).initialize()
        self.walk("station:center", "station:shelf:3")
        self.night()
        with self.assertRaisesRegex(Conflict, "dark"):
            self.body.take("book:007")
        self.assertEqual(BookCustody(self.lab).verify()["revision"], 0)
        self.port.act("light")
        response = self.port.act("take_book", book_id="book:007")
        self.assertIn("I lift", response["inner"])
        self.assertEqual(BookCustody(self.lab).verify()["revision"], 1)

    def test_measurement_readout_is_first_person_and_legacy_access_is_gated(self):
        BookCustody(self.lab).initialize()
        PhysicalAffordances(self.lab).initialize()
        BenchInstruments(self.lab).initialize()
        self.walk("station:center", "station:bench")
        read = self.port.act("measure", instrument="balance:bench",
                             object_id="beaker:001", quantity="mass_g")
        self.assertIn("about 325 grams", read["inner"])
        self.assertNotIn("uncertainty_class", json.dumps(read))
        # Stay hydrated so the light intervention remains discriminating.
        self.walk("station:center", "station:threshold",
                  "station:hall", "station:kitchen")
        self.port.act("brew_tea")
        self.walk("station:hall", "station:threshold",
                  "station:center", "station:bench")
        for minutes in (240, 240, 160):
            self.port.act("advance", minutes=minutes)
        self.assertLess(self.daily.audit_state()["thirst"], 8)
        before = BenchInstruments(self.lab).verify()["revision"]
        with self.assertRaisesRegex(Conflict, "dark"):
            self.body.measure("balance:bench", "beaker:001", "mass_g")
        self.assertEqual(BenchInstruments(self.lab).verify()["revision"], before)
        self.port.act("light")
        followup = self.port.act("measure", instrument="balance:bench",
                                 object_id="beaker:001", quantity="mass_g")
        self.assertIn("about 325 grams", followup["inner"])

    def test_unlisted_actions_and_fabricated_access_are_rejected(self):
        for op, args in [
            ("set_hunger", {"value": 0}),
            ("teleport", {"station": "station:kitchen"}),
            ("walk", {"station": "station:kitchen"}),
            ("look", {"source": "secret"}),
            ("take", {"item": "garment:coat", "location": "room:bedroom"}),
            ("measure", {"object_id": "beaker:001"}),
        ]:
            with self.subTest(op=op), self.assertRaises((LabError, Conflict)):
                self.port.act(op, **args)
        self.assertTrue(self.daily.verify()["verified"])

    def test_corrupted_environment_fails_closed_in_legacy_lookup(self):
        self.walk("station:hall")
        with self.lab._open() as db:
            state = json.loads(db.execute(
                "SELECT value FROM rhythm_meta WHERE key='state'").fetchone()[0])
            state["supplies"]["oil"] = 190
            db.execute("UPDATE rhythm_meta SET value=? WHERE key='state'",
                       (json.dumps(state),))
        with self.assertRaises(Conflict):
            self.body.look()
        with self.assertRaises(Conflict):
            self.port.observe()


if __name__ == "__main__":
    unittest.main()
