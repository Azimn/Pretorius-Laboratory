"""One effective physical location across old v2, annex and custody entrypoints.

The original raw event reducers must remain historically replayable, while NEW
operator placements in a custody-enabled world follow effective occupancy.
"""
from pathlib import Path
import tempfile
import unittest

from pretorius_lab import Conflict, LabError
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.book_library import BookLibrary
from pretorius_lab.book_custody import BookCustody
from pretorius_lab.embodied_access import EmbodiedAccess
from pretorius_lab.shelf_annex import ShelfAnnex


class UnifiedOccupancyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lab = SpatialHabitat.create(self.root / "laboratory.sqlite3")
        self.actor = EmbodiedAccess(self.lab)
        self.actor.initialize()
        self.custody = BookCustody(self.lab)
        self.custody.initialize()

    def move(self, station):
        if self.actor.verify()["station"] != "station:center":
            self.actor.move("station:center")
        self.actor.move(station)

    def test_beaker_can_enter_vacated_original_book_shelf_without_shadow_collision(self):
        self.move("station:shelf:3")
        self.actor.take("book:007")
        original_v2 = self.lab.verify()["revision"]
        receipt = self.lab.commit({"op": "place", "object_id": "beaker:001",
                                   "anchor_id": "shelf:3/slot:7"},
                                  event_id="operator-cross-reservation")
        self.assertEqual(receipt["domain"], "effective_physical_placement")
        self.assertTrue(receipt["legacy_world_revision_unchanged"])
        self.assertEqual(self.lab.verify()["revision"], original_v2)
        self.assertEqual(self.lab.scan("shelf:3")["positions"][6]["occupant"]["id"],
                         "beaker:001")
        self.assertIsNone(self.lab.scan("bench:main")["positions"][0]["occupant"])
        self.assertEqual(self.lab.locate("book:007")["location"]["placement"], "carried")
        with self.assertRaises(Conflict):
            self.actor.put("book:007", "shelf:3/slot:7")
        self.lab.commit({"op": "place", "object_id": "beaker:001",
                         "anchor_id": "bench:main/position:left"})
        self.actor.put("book:007", "shelf:3/slot:7")
        self.assertEqual(self.lab.scan("shelf:3")["positions"][6]["occupant"]["id"],
                         "book:007")
        self.assertEqual(self.custody.verify()["revision"], 4)

    def test_operator_place_is_idempotent_and_does_not_move_again_on_retry(self):
        self.move("station:shelf:3")
        self.actor.take("book:007")
        action = {"op": "place", "object_id": "beaker:001",
                  "anchor_id": "shelf:3/slot:7"}
        a = self.lab.commit(action, event_id="operator-place-fixed")
        b = self.lab.commit(action, event_id="operator-place-fixed")
        self.assertEqual(a, b)
        self.assertEqual(self.custody.verify()["revision"], 2)
        with self.assertRaises(Conflict):
            self.lab.commit({"op": "place", "object_id": "beaker:001",
                             "anchor_id": "shelf:2/slot:1"},
                            event_id="operator-place-fixed")

    def test_annex_move_and_raw_core_place_share_same_occupancy(self):
        annex = ShelfAnnex(self.lab)
        annex.initialize()
        annex.register("book:008", "shelf:1/slot:1", "Esoteric source")
        receipt = annex.move("book:008", "shelf:2/slot:1")
        self.assertEqual(receipt["domain"], "effective_physical_placement")
        self.assertEqual(annex.verify()["revision"], 1)
        self.assertIsNone(self.lab.scan("shelf:1")["positions"][0]["occupant"])
        self.assertEqual(self.lab.scan("shelf:2")["positions"][0]["occupant"]["id"],
                         "book:008")
        self.lab.commit({"op": "place", "object_id": "beaker:001",
                         "anchor_id": "shelf:1/slot:1"})
        self.assertEqual(self.lab.scan("shelf:1")["positions"][0]["occupant"]["id"],
                         "beaker:001")
        with self.assertRaises(Conflict):
            annex.move("book:008", "shelf:1/slot:1")
        self.assertEqual(self.custody.verify()["revision"], 2)

    def test_historic_raw_physical_events_still_replay(self):
        # The legacy placement happened BEFORE enabling custody. It must not
        # be retrospectively rerouted or reinterpreted by later code.
        old = SpatialHabitat.create(self.root / "old-events.sqlite3")
        first = old.commit({"op": "place", "object_id": "beaker:001",
                            "anchor_id": "floor:corner:nw"})
        self.assertEqual(first["committed_revision"], 1)
        EmbodiedAccess(old).initialize()
        BookCustody(old).initialize()
        second = old.commit({"op": "place", "object_id": "beaker:001",
                             "anchor_id": "bench:main/position:left"})
        self.assertEqual(second["domain"], "effective_physical_placement")
        self.assertEqual(old.verify()["revision"], 1)
        self.assertTrue(BookCustody(old).verify()["verified"])
        self.assertEqual(old.scan("bench:main")["positions"][0]["occupant"]["id"],
                         "beaker:001")

    def test_book_edition_follows_authorized_operator_relocation(self):
        library = BookLibrary(self.lab)
        library.initialize()
        library.install("book:007", edition_id="fixed-work-v1",
                        title="Verified text", author="Source",
                        pages=["Exact first leaf."],
                        source_class="original_fixture", source_reference="test source")
        moved = self.lab.commit({"op": "place", "object_id": "book:007",
                                 "anchor_id": "shelf:1/slot:1"})
        self.assertEqual(moved["domain"], "effective_physical_placement")
        self.move("station:shelf:3")
        with self.assertRaises(LabError):
            self.actor.book("book:007", "open")
        self.move("station:shelf:1")
        self.actor.book("book:007", "open")
        self.assertEqual(self.actor.book("book:007", "read")["page_text"],
                         "Exact first leaf.")
        self.assertTrue(library.verify()["verified"])

    def test_cannot_operator_relocate_book_currently_held(self):
        self.move("station:shelf:3")
        self.actor.take("book:007")
        with self.assertRaises(Conflict):
            self.lab.commit({"op": "place", "object_id": "book:007",
                             "anchor_id": "shelf:2/slot:4"})
        self.assertEqual(self.lab.locate("book:007")["location"]["placement"], "carried")

    def test_placed_overlay_survives_backup_and_fork(self):
        self.move("station:shelf:3")
        self.actor.take("book:007")
        self.lab.commit({"op": "place", "object_id": "beaker:001",
                         "anchor_id": "shelf:3/slot:7"})
        backup = self.root / "backup.sqlite3"
        self.lab.backup_to(backup)
        restored = SpatialHabitat(backup)
        self.assertEqual(restored.scan("shelf:3")["positions"][6]["occupant"]["id"],
                         "beaker:001")
        self.assertEqual(restored.locate("book:007")["location"]["placement"], "carried")
        experiment = self.root / "experiment.sqlite3"
        self.lab.fork_to(experiment)
        child = SpatialHabitat(experiment)
        self.assertEqual(child.scan("shelf:3")["positions"][6]["occupant"]["id"],
                         "beaker:001")
        self.assertEqual(child.locate("book:007")["location"]["placement"], "carried")
        self.assertNotEqual(child.verify()["world_epoch"], self.lab.verify()["world_epoch"])
        self.assertTrue(BookCustody(child).verify()["verified"])
        child.commit({"op": "place", "object_id": "beaker:001",
                      "anchor_id": "bench:main/position:left"})
        self.assertEqual(self.lab.locate("beaker:001")["location"]["fixture"], "shelf:3")
        self.assertEqual(child.locate("beaker:001")["location"]["fixture"], "bench:main")

    def test_broken_scattered_beaker_cannot_be_moved_by_new_placement_route(self):
        self.lab.commit({"op": "break", "object_id": "beaker:001"})
        with self.assertRaises(LabError):
            self.lab.commit({"op": "place", "object_id": "beaker:001",
                             "anchor_id": "floor:corner:nw"})
        self.assertEqual(self.custody.verify()["revision"], 0)
        self.lab.commit({"op": "collect", "object_id": "beaker:001"})
        self.lab.commit({"op": "place", "object_id": "beaker:001",
                         "anchor_id": "floor:corner:nw"})
        self.assertEqual(self.custody.verify()["revision"], 1)
        self.assertEqual(self.lab.locate("beaker:001")["condition"], "broken")

    def test_stale_effective_placement_revision_fails_without_state_change(self):
        first = self.lab.commit({"op": "place", "object_id": "beaker:001",
                                 "anchor_id": "floor:corner:se"},
                                expected_placement_revision=0)
        self.assertEqual(first["domain"], "effective_physical_placement")
        self.assertEqual(self.custody.verify()["revision"], 1)
        with self.assertRaises(Conflict):
            self.lab.commit({"op": "place", "object_id": "beaker:001",
                             "anchor_id": "floor:corner:nw"},
                            expected_placement_revision=0)
        self.assertEqual(self.custody.verify()["revision"], 1)
        self.assertEqual(self.lab.locate("beaker:001")["location"]["anchor_id"],
                         "floor:corner:se")
        after = self.lab.commit({"op": "place", "object_id": "beaker:001",
                                 "anchor_id": "floor:corner:nw"},
                                expected_placement_revision=1)
        self.assertEqual(self.custody.verify()["revision"], 2)
        self.assertNotEqual(first["event_hash"], after["event_hash"])

    def test_annex_optimistic_revision_guard_is_shared_with_core(self):
        annex = ShelfAnnex(self.lab)
        annex.initialize()
        annex.register("book:008", "shelf:1/slot:1", "Occult volume")
        self.lab.commit({"op": "place", "object_id": "beaker:001",
                         "anchor_id": "floor:corner:se"})
        with self.assertRaises(Conflict):
            annex.move("book:008", "shelf:2/slot:1",
                       expected_placement_revision=0)
        good = annex.move("book:008", "shelf:2/slot:1",
                          expected_placement_revision=1)
        self.assertEqual(good["domain"], "effective_physical_placement")
        self.assertEqual(self.custody.verify()["revision"], 2)

    def test_non_operator_cannot_override_custody_by_admin_place(self):
        with self.assertRaises(LabError):
            self.lab.commit({"op": "place", "object_id": "book:007",
                             "anchor_id": "shelf:2/slot:2"},
                            actor="pretorius_research")
        self.assertEqual(self.custody.verify()["revision"], 0)


if __name__ == "__main__":
    unittest.main()
