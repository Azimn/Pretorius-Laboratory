"""Acceptance tests for L0/L1 and local-only L2 offline rehearsal."""
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from pretorius_lab import Laboratory, LabError, Conflict
from pretorius_lab.perception import observe


class LaboratoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.lab = Laboratory.create(self.path / "lab.sqlite3")

    def test_persistent_identity_and_replay(self):
        original = self.lab.status()
        self.lab.commit({"op": "open", "object_id": "container:specimen"})
        self.lab.commit({"op": "move", "object_id": "specimen:alpha", "to_id": "bench:main"})
        self.lab.commit({"op": "advance_clock", "ticks": 13})
        self.lab.commit({"op": "note", "text": "Specimen removed at tick 13."})
        reopened = Laboratory(self.lab.path)
        self.assertEqual(reopened.status()["lab_id"], original["lab_id"])
        self.assertEqual(reopened.status()["world_epoch"], original["world_epoch"])
        self.assertEqual(reopened.status()["objects"]["instrument:clock"]["ticks"], 13)
        self.assertEqual(reopened.status()["objects"]["specimen:alpha"]["location"], "bench:main")
        self.assertEqual(reopened.verify()["revision"], 4)

    def test_object_and_schema_rejections_leave_history_unchanged(self):
        for action in [
            {"op": "move", "object_id": "instrument:clock", "to_id": "room:main"},
            {"op": "move", "object_id": "specimen:alpha", "to_id": "specimen:alpha"},
            {"op": "move", "object_id": "specimen:alpha", "to_id": "missing"},
            {"op": "open", "object_id": "room:main"},
            {"op": "advance_clock", "ticks": -1},
            {"op": "advance_clock", "ticks": True},
            {"op": "note", "text": ""},
            {"op": "set_property", "object_id": "specimen:alpha", "value": "x"},
            {"op": "open", "object_id": "container:specimen", "surprise": "x"},
        ]:
            with self.subTest(action=action), self.assertRaises(LabError):
                self.lab.commit(action)
        self.assertEqual(self.lab.verify()["revision"], 0)

    def test_closed_container_blocks_receiving_and_removal(self):
        with self.assertRaises(LabError):
            self.lab.commit({"op": "move", "object_id": "specimen:alpha", "to_id": "bench:main"})
        self.lab.commit({"op": "open", "object_id": "container:specimen"})
        self.lab.commit({"op": "move", "object_id": "specimen:alpha", "to_id": "bench:main"})
        self.lab.commit({"op": "close", "object_id": "container:specimen"})
        with self.assertRaises(LabError):
            self.lab.commit({"op": "move", "object_id": "specimen:alpha", "to_id": "container:specimen"})
        self.assertEqual(self.lab.verify()["revision"], 3)

    def test_idempotent_deliveries_and_payload_mismatch(self):
        action = {"op": "open", "object_id": "container:specimen"}
        first = self.lab.commit(action, event_id="fixture:event-001")
        again = self.lab.commit(action, event_id="fixture:event-001")
        self.assertEqual(first["committed_revision"], again["committed_revision"])
        with self.assertRaises(Conflict):
            self.lab.commit({"op": "close", "object_id": "container:specimen"}, event_id="fixture:event-001")
        self.assertEqual(self.lab.verify()["revision"], 1)

    def test_snapshot_backup_restore_and_no_overwrite(self):
        self.lab.commit({"op": "advance_clock", "ticks": 9})
        self.lab.checkpoint()
        backup = self.path / "offhost-copy.sqlite3"
        self.assertEqual(self.lab.backup_to(backup)["revision"], 1)
        recovered = self.path / "recovered.sqlite3"
        self.assertEqual(Laboratory.restore_to(backup, recovered)["revision"], 1)
        self.assertEqual(Laboratory(recovered).status()["objects"], self.lab.status()["objects"])
        with self.assertRaises(FileExistsError):
            Laboratory.restore_to(backup, recovered)
        self.lab.commit({"op": "advance_clock", "ticks": 4})
        self.assertEqual(Laboratory(recovered).status()["objects"]["instrument:clock"]["ticks"], 9)
        self.assertEqual(self.lab.verify()["revision"], 2)

    def test_tampering_is_detected(self):
        self.lab.commit({"op": "advance_clock", "ticks": 2})
        with sqlite3.connect(self.lab.path) as db:
            db.execute("UPDATE events SET prev_hash=? WHERE revision=1", ("f" * 64,))
        with self.assertRaises(Conflict):
            self.lab.verify()

    def test_offline_nonconflict_rebases_on_current_world(self):
        queue = self.path / "branch.json"
        self.lab.start_offline(queue)
        Laboratory.stage_offline(queue, {"op": "open", "object_id": "container:specimen"})
        self.lab.commit({"op": "advance_clock", "ticks": 3})
        outcome = self.lab.reconcile(queue)
        self.assertEqual(outcome["outcomes"][0]["status"], "accepted_local")
        self.assertEqual(self.lab.status()["objects"]["instrument:clock"]["ticks"], 3)
        self.assertTrue(self.lab.status()["objects"]["container:specimen"]["open"])
        self.assertEqual(self.lab.verify()["revision"], 2)

    def test_offline_conflicting_same_object_rejected(self):
        queue = self.path / "branch.json"
        self.lab.start_offline(queue)
        Laboratory.stage_offline(queue, {"op": "move", "object_id": "container:specimen", "to_id": "room:main"})
        self.lab.commit({"op": "move", "object_id": "container:specimen", "to_id": "room:main"})
        outcome = self.lab.reconcile(queue)
        self.assertEqual(outcome["outcomes"][0]["status"], "conflicted")
        self.assertEqual(self.lab.verify()["revision"], 1)

    def test_offline_epoch_quarantine(self):
        queue = self.path / "branch.json"
        self.lab.start_offline(queue)
        branch = json.loads(queue.read_text())
        branch["world_epoch"] = "different-world"
        queue.write_text(json.dumps(branch))
        with self.assertRaises(Conflict):
            self.lab.reconcile(queue)
        self.assertEqual(self.lab.verify()["revision"], 0)

    def test_lost_acknowledgement_replay_deduplicates(self):
        queue = self.path / "branch.json"
        self.lab.start_offline(queue)
        Laboratory.stage_offline(queue, {"op": "advance_clock", "ticks": 7})
        self.assertEqual(self.lab.reconcile(queue)["outcomes"][0]["status"], "accepted_local")
        branch = json.loads(queue.read_text())
        branch["proposals"][0]["status"] = "pending"
        queue.write_text(json.dumps(branch))
        self.assertEqual(self.lab.reconcile(queue)["outcomes"][0]["status"], "accepted_local")
        self.assertEqual(self.lab.verify()["revision"], 1)

    def test_offline_overlap_is_not_implicitly_merged(self):
        queue = self.path / "branch.json"
        self.lab.start_offline(queue)
        Laboratory.stage_offline(queue, {"op": "advance_clock", "ticks": 3})
        with self.assertRaises(Conflict):
            Laboratory.stage_offline(queue, {"op": "advance_clock", "ticks": 2})

    def test_concurrent_optimistic_writes_one_wins(self):
        barrier = threading.Barrier(3)
        outcomes = []
        def writer():
            barrier.wait()
            try:
                self.lab.commit({"op": "advance_clock", "ticks": 1},
                                expected_versions={"instrument:clock": 0})
                outcomes.append("accepted")
            except Conflict:
                outcomes.append("conflicted")
        a = threading.Thread(target=writer)
        b = threading.Thread(target=writer)
        a.start()
        b.start()
        barrier.wait()
        a.join(timeout=10)
        b.join(timeout=10)
        self.assertFalse(a.is_alive() or b.is_alive())
        self.assertCountEqual(outcomes, ["accepted", "conflicted"])
        self.assertEqual(self.lab.verify()["revision"], 1)

class PerceptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.lab = Laboratory.create(Path(self.temp.name) / "lab.sqlite3")

    def test_closed_vessel_conceals_specimen_and_action(self):
        scene = observe(self.lab)
        self.assertIn("container:specimen", scene["visible_objects"])
        self.assertNotIn("specimen:alpha", scene["visible_objects"])
        self.assertNotIn({"op": "move", "object_id": "specimen:alpha",
                          "to_id": "bench:main"}, scene["eligible_action_examples"])
        self.assertIn({"op": "open", "object_id": "container:specimen"},
                      scene["eligible_action_examples"])

    def test_open_vessel_reveals_specimen_and_legal_move(self):
        self.lab.commit({"op": "open", "object_id": "container:specimen"})
        scene = observe(self.lab)
        self.assertIn("specimen:alpha", scene["visible_objects"])
        self.assertIn({"op": "move", "object_id": "specimen:alpha",
                       "to_id": "bench:main"}, scene["eligible_action_examples"])
        self.assertIn({"op": "close", "object_id": "container:specimen"},
                      scene["eligible_action_examples"])

    def test_notebook_contents_not_disclosed(self):
        secret = "Private experiment research note not for Village."
        self.lab.commit({"op": "note", "text": secret})
        scene = observe(self.lab)
        self.assertNotIn("entries", scene["visible_objects"]["notebook:primary"])
        self.assertNotIn(secret, json.dumps(scene))
        self.assertEqual(scene["visibility"], "research_private")
        self.assertIn("not_lived_memory", scene["observation_class"])

    def test_observation_is_restart_stable_and_read_only(self):
        one = observe(self.lab)
        again = observe(Laboratory(self.lab.path))
        self.assertEqual(one, again)
        self.assertEqual(self.lab.status()["revision"], 0)
        self.assertEqual(one["event_cursor"], "0" * 64)
        self.lab.commit({"op": "advance_clock", "ticks": 4})
        next_scene = observe(self.lab)
        self.assertNotEqual(one["observation_digest"], next_scene["observation_digest"])
        self.assertEqual(next_scene["visible_objects"]["instrument:clock"]["ticks"], 4)

    def test_observation_refuses_corrupt_state(self):
        self.lab.commit({"op": "advance_clock", "ticks": 1})
        with sqlite3.connect(self.lab.path) as db:
            db.execute("UPDATE events SET event_hash=? WHERE revision=1", ("f" * 64,))
        with self.assertRaises(Conflict):
            observe(self.lab)


if __name__ == "__main__":
    unittest.main()
