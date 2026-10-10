"""Continuity, object permanence, recovery, and authority tests for opt-in habitat v2."""
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from pretorius_lab import LabError, Conflict
from pretorius_lab.habitat_v2 import SpatialHabitat, apply_spatial, FIXTURE


class SpatialContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lab = SpatialHabitat.create(self.root / "sanctum.sqlite3")

    def test_seventh_book_of_third_shelf_is_exact(self):
        first = self.lab.locate("book:007")
        self.assertEqual(first["anchor_id"], "shelf:3/slot:7")
        self.assertEqual(first["anchor"]["ordinal"], 7)
        self.assertEqual(first["anchor"]["parent"], "shelf:3")
        self.assertEqual(first["anchor"]["xyz_mm"], [1090, 300, 1900])
        scan = self.lab.scan("shelf:3")["positions"]
        self.assertEqual(len(scan), 10)
        self.assertEqual(scan[6]["occupant"]["id"], "book:007")
        again = SpatialHabitat(self.lab.path).locate("book:007")
        self.assertEqual(first, again)

    def test_beaker_break_gather_and_place_corner_persists(self):
        self.lab.commit({"op": "break", "object_id": "beaker:001"})
        broken = self.lab.locate("beaker:001")
        self.assertEqual(broken["object"]["condition"], "broken")
        self.assertFalse(broken["object"]["collected"])
        with self.assertRaises(LabError):
            self.lab.commit({"op": "place", "object_id": "beaker:001",
                             "anchor_id": "floor:corner:nw"})
        self.lab.commit({"op": "collect", "object_id": "beaker:001"})
        placed = self.lab.commit({"op": "place", "object_id": "beaker:001",
                                  "anchor_id": "floor:corner:nw"})
        self.assertEqual(placed["committed_revision"], 3)
        morning = SpatialHabitat(self.lab.path)
        location = morning.locate("beaker:001")
        self.assertEqual(location["object"]["condition"], "broken")
        self.assertEqual(location["anchor_id"], "floor:corner:nw")
        self.assertEqual(location["anchor"]["xyz_mm"], [100, 100, 0])
        self.assertEqual(morning.verify()["revision"], 3)
        self.assertEqual(morning.scan("floor:sanctum")["positions"][0]["occupant"]["id"],
                         "beaker:001")

    def test_book_move_is_exact_and_old_slot_becomes_empty(self):
        command = {"op": "place", "object_id": "book:007",
                   "anchor_id": "shelf:2/slot:9"}
        self.lab.commit(command)
        morning = SpatialHabitat(self.lab.path)
        self.assertEqual(morning.locate("book:007")["anchor_id"], "shelf:2/slot:9")
        self.assertIsNone(morning.scan("shelf:3")["positions"][6]["occupant"])
        self.assertEqual(morning.scan("shelf:2")["positions"][8]["occupant"]["id"],
                         "book:007")

    def test_overlapping_objects_cannot_occupy_same_slot(self):
        with self.assertRaises(Conflict):
            self.lab.commit({"op": "place", "object_id": "book:006",
                             "anchor_id": "shelf:3/slot:7"})
        self.assertEqual(self.lab.verify()["revision"], 0)

    def test_no_arbitrary_details_or_unlocated_objects(self):
        for bad in [
            {"op": "place", "object_id": "book:007", "anchor_id": "shelf:3/slot:11"},
            {"op": "place", "object_id": "invented", "anchor_id": "shelf:2/slot:8"},
            {"op": "break", "object_id": "book:001"},
            {"op": "break", "object_id": "beaker:001", "location": "somewhere"},
            {"op": "advance_ticks", "ticks": True},
            {"op": "place", "object_id": "book:007", "anchor_id": ["x"]},
        ]:
            with self.subTest(bad=bad), self.assertRaises((LabError, Conflict)):
                self.lab.commit(bad)
        self.assertEqual(self.lab.verify()["revision"], 0)

    def test_event_idempotence_and_stale_world_guard(self):
        command = {"op": "place", "object_id": "book:007",
                   "anchor_id": "shelf:2/slot:10"}
        first = self.lab.commit(command, event_id="same-event", expected_revision=0)
        second = self.lab.commit(command, event_id="same-event", expected_revision=0)
        self.assertEqual(first["event_hash"], second["event_hash"])
        self.assertEqual(self.lab.verify()["revision"], 1)
        with self.assertRaises(Conflict):
            self.lab.commit({"op": "break", "object_id": "beaker:001"},
                            event_id="same-event")
        with self.assertRaises(Conflict):
            self.lab.commit({"op": "break", "object_id": "beaker:001"},
                            expected_revision=0)
        self.assertEqual(self.lab.verify()["revision"], 1)

    def test_forked_experiment_does_not_mutate_the_home(self):
        self.lab.commit({"op": "place", "object_id": "book:007",
                         "anchor_id": "shelf:2/slot:10"})
        parent = self.lab.verify()
        fork_path = self.root / "experiment.sqlite3"
        info = self.lab.fork_to(fork_path)
        clone = SpatialHabitat(fork_path)
        self.assertEqual(info["mode"], "sandbox")
        self.assertNotEqual(parent["lab_id"], info["lab_id"])
        self.assertNotEqual(parent["world_epoch"], info["world_epoch"])
        self.assertEqual(parent["home_id"], info["home_id"])
        self.assertEqual(clone.status()["parent"]["head_hash"], parent["head_hash"])
        clone.commit({"op": "break", "object_id": "beaker:001"})
        self.assertEqual(clone.locate("beaker:001")["object"]["condition"], "broken")
        self.assertEqual(self.lab.locate("beaker:001")["object"]["condition"], "intact")
        self.assertEqual(self.lab.locate("book:007")["anchor_id"], "shelf:2/slot:10")
        self.assertEqual(self.lab.verify()["revision"], 1)

    def test_checkpoint_and_backup_restore_keep_coordinates(self):
        self.lab.commit({"op": "break", "object_id": "beaker:001"})
        self.lab.checkpoint()
        saved = self.root / "backup.sqlite3"
        self.assertEqual(self.lab.backup_to(saved)["revision"], 1)
        with self.assertRaises(FileExistsError):
            self.lab.backup_to(saved)
        saved_copy = SpatialHabitat(saved)
        self.assertEqual(saved_copy.locate("book:007")["anchor"]["ordinal"], 7)
        self.lab.commit({"op": "collect", "object_id": "beaker:001"})
        self.assertEqual(saved_copy.locate("beaker:001")["object"]["collected"], False)
        self.assertEqual(self.lab.verify()["revision"], 2)

    def test_event_history_tampering_fails_closed(self):
        self.lab.commit({"op": "break", "object_id": "beaker:001"})
        with sqlite3.connect(self.lab.path) as db:
            db.execute("UPDATE events SET prev_hash=? WHERE revision=1", ("f" * 64,))
        with self.assertRaises(Conflict):
            self.lab.locate("beaker:001")

    def test_materialized_state_without_event_detected(self):
        with sqlite3.connect(self.lab.path) as db:
            row = db.execute("SELECT value FROM meta WHERE key='state'").fetchone()[0]
            state = json.loads(row)
            state["objects"]["book:007"]["anchor_id"] = "shelf:2/slot:9"
            db.execute("UPDATE meta SET value=? WHERE key='state'",
                       (json.dumps(state),))
        with self.assertRaises(Conflict):
            self.lab.verify()

    def test_observation_never_invents_an_object(self):
        scene = self.lab.observe("room:sanctum")
        self.assertEqual(scene["revision"], 0)
        self.assertEqual(scene["observation_class"], "source_attested_host_view")
        self.assertEqual(set(scene["objects"]), set(FIXTURE["objects"]))
        self.assertEqual(scene["objects"]["book:007"]["anchor_id"], "shelf:3/slot:7")
        self.assertNotIn("book:999", scene["objects"])
        self.assertEqual(self.lab.observe("room:experiment")["objects"], {})

    def test_concurrent_mutations_one_revision_wins(self):
        gate = threading.Barrier(3)
        results = []
        def writer():
            gate.wait()
            try:
                self.lab.commit({"op": "break", "object_id": "beaker:001"},
                                expected_revision=0)
                results.append("accepted")
            except Conflict:
                results.append("conflict")
        a = threading.Thread(target=writer)
        b = threading.Thread(target=writer)
        a.start()
        b.start()
        gate.wait()
        a.join(timeout=10)
        b.join(timeout=10)
        self.assertFalse(a.is_alive() or b.is_alive())
        self.assertCountEqual(results, ["accepted", "conflict"])
        self.assertEqual(self.lab.verify()["revision"], 1)


if __name__ == "__main__":
    unittest.main()
