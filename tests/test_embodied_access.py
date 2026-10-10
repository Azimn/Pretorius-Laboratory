"""Acceptance tests for source-grounded embodied access in a persistent world."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pretorius_lab import Conflict, LabError
from pretorius_lab.book_library import BookLibrary
from pretorius_lab.embodied_access import EmbodiedAccess
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.shelf_annex import ShelfAnnex


class EmbodiedAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.lab = SpatialHabitat.create(self.root / "home.sqlite3")
        self.library = BookLibrary(self.lab)
        self.library.initialize()
        self.library.install("book:007", edition_id="research-source-v1",
                             title="The Actual Reference Book", author="Test Fixture",
                             pages=["First actual page.", "Another actual page."],
                             source_class="original_fixture",
                             source_reference="synthetic noncanonical unit test source")
        self.port = EmbodiedAccess(self.lab)
        self.port.initialize()

    def approach(self, station="station:shelf:3"):
        self.port.move("station:center")
        return self.port.move(station)

    def test_doorway_cannot_read_any_book_or_see_full_title_list(self):
        at_door = self.port.look()
        self.assertEqual(at_door["offered_payload"]["nearby_objects"], [])
        self.assertNotIn("The Actual Reference Book", json.dumps(at_door))
        self.assertNotIn("xyz_mm", json.dumps(at_door))
        self.assertEqual(at_door["offered_payload"]["location"]["station"],
                         "station:threshold")
        with self.assertRaises(LabError):
            self.port.book("book:007", "open")
        self.assertEqual(self.library.verify()["revision"], 1)

    def test_requires_adjacent_travel_and_reveals_only_nearby_shelf(self):
        with self.assertRaises(LabError):
            self.port.move("station:shelf:3")
        self.port.move("station:center")
        center = self.port.look()["offered_payload"]
        self.assertEqual(center["nearby_objects"], [])
        self.port.move("station:shelf:3")
        near = self.port.look()["offered_payload"]
        self.assertEqual(len(near["nearby_objects"]), 7)
        self.assertEqual(near["nearby_objects"][6]["appearance"],
                         "The Actual Reference Book")
        self.assertEqual(near["nearby_objects"][6]["placement"], 7)
        self.assertNotIn("First actual page", json.dumps(near))
        self.assertNotIn("xyz_mm", json.dumps(near))
        self.assertNotIn("book:008", json.dumps(near))

    def test_read_book_and_preserve_bookmark_across_restart(self):
        self.approach()
        self.port.book("book:007", "open")
        first = self.port.book("book:007", "read")
        self.assertEqual(first["page_text"], "First actual page.")
        self.port.book("book:007", "turn", direction=1)
        self.port.book("book:007", "mark", bookmark_id="scarlet-ribbon")
        self.port.book("book:007", "close")
        new = EmbodiedAccess(SpatialHabitat(self.lab.path))
        self.assertEqual(new.verify()["station"], "station:shelf:3")
        new.book("book:007", "open_mark", bookmark_id="scarlet-ribbon")
        self.assertEqual(new.book("book:007", "read")["page_text"],
                         "Another actual page.")
        self.assertEqual(self.library.catalog("book:007")["book:007"]["bookmarks"],
                         {"scarlet-ribbon": 2})
        self.assertTrue(self.library.verify()["verified"])

    def test_current_position_and_current_physical_book_location_guard_actions(self):
        self.approach()
        # Authorized operator relocates a book after subject has arrived.
        self.lab.commit({"op": "place", "object_id": "book:007",
                         "anchor_id": "shelf:1/slot:1"})
        with self.assertRaises(LabError):
            self.port.book("book:007", "open")
        self.port.move("station:center")
        self.port.move("station:shelf:1")
        self.port.book("book:007", "open")
        self.assertEqual(self.port.book("book:007", "read")["page_text"],
                         "First actual page.")

    def test_look_event_receipt_does_not_claim_subject_experience(self):
        first = self.port.look(event_id="doorway-first")
        same = self.port.look(event_id="doorway-first")
        self.assertEqual(first["event_hash"], same["event_hash"])
        self.assertEqual(self.port.verify()["revision"], 1)
        self.assertEqual(first["offered_payload"]["observation_class"],
                         "offered_not_proof_of_subject_attention")

    def test_move_idempotence_after_pose_change(self):
        a = self.port.move("station:center", event_id="travel-1")
        b = self.port.move("station:center", event_id="travel-1")
        self.assertEqual(a["event_hash"], b["event_hash"])
        self.assertEqual(self.port.verify()["revision"], 1)
        with self.assertRaises(Conflict):
            self.port.move("station:shelf:3", event_id="travel-1")

    def test_physical_annex_uses_same_access_rules(self):
        annex = ShelfAnnex(self.lab)
        annex.initialize()
        annex.register("book:008", "shelf:1/slot:1", "A Forbidden Treatise")
        self.library.install("book:008", edition_id="test-occult-v1",
                             title="A Forbidden Treatise", author="Fixture",
                             pages=["Full archival source one.", "Second archival source."],
                             source_class="original_fixture",
                             source_reference="synthetic test source")
        self.approach("station:shelf:3")
        with self.assertRaises(LabError):
            self.port.book("book:008", "open")
        self.port.move("station:center")
        self.port.move("station:shelf:1")
        self.assertEqual(
            [a["object_id"] for a in self.port.look()["offered_payload"]["nearby_objects"]],
            ["book:008"])
        self.port.book("book:008", "open")
        self.assertEqual(self.port.book("book:008", "read")["page_text"],
                         "Full archival source one.")

    def test_backup_restores_position_and_local_observation_log(self):
        self.approach()
        self.port.look()
        target = self.root / "copy.sqlite3"
        self.lab.backup_to(target)
        recovered = EmbodiedAccess(SpatialHabitat(target))
        self.assertEqual(recovered.verify()["station"], "station:shelf:3")
        self.assertEqual(recovered.verify()["revision"], self.port.verify()["revision"])
        self.assertEqual(recovered.look()["offered_payload"]["nearby_objects"][6]
                         ["appearance"], "The Actual Reference Book")

    def test_fork_copies_pose_but_does_not_import_old_observations(self):
        self.approach()
        self.port.look()
        parent_version = self.port.verify()["revision"]
        target = self.root / "sandbox.sqlite3"
        self.lab.fork_to(target)
        clone = EmbodiedAccess(SpatialHabitat(target))
        self.assertEqual(clone.verify()["station"], "station:shelf:3")
        self.assertEqual(clone.verify()["revision"], 0)
        clone.book("book:007", "open")
        self.assertEqual(self.library.catalog("book:007")["book:007"]["opened"], False)
        self.assertEqual(self.port.verify()["revision"], parent_version)

    def test_forged_body_meta_is_rejected_and_backup_fails_closed(self):
        self.approach()
        with sqlite3.connect(self.lab.path) as db:
            db.execute("UPDATE embodied_meta SET value=? WHERE key='station'",
                       (json.dumps("station:bench"),))
        with self.assertRaises(Conflict):
            self.port.verify()
        with self.assertRaises(Conflict):
            self.lab.backup_to(self.root / "bad.sqlite3")

    def test_history_tamper_detected(self):
        self.approach()
        with sqlite3.connect(self.lab.path) as db:
            db.execute("UPDATE embodied_events SET event_hash=? WHERE revision=1",
                       ("f" * 64,))
        with self.assertRaises(Conflict):
            self.port.verify()

    def test_subject_does_not_know_actual_book_contents_without_source_install(self):
        # Physical volumes exist but only book:007 has installed text.
        self.approach()
        with self.assertRaises(LabError):
            self.port.book("book:006", "read")
        self.assertEqual(self.port.look()["offered_payload"]["nearby_objects"][5]
                         ["appearance"], "Research volume 6")


if __name__ == "__main__":
    unittest.main()
