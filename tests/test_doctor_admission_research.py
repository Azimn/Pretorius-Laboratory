"""Cross-repository research pilot: real PretoriusBrainPort + physical lab.

Run with pinned The-Doctor-Lives installed by research GitHub Actions.
The normal standalone laboratory suite skips these optional cross-repo tests.
"""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pretorius_lab import Conflict
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.embodied_access import EmbodiedAccess
from pretorius_lab.book_custody import BookCustody
from pretorius_lab.physical_affordances import PhysicalAffordances
from pretorius_lab.bench_instruments import BenchInstruments
from pretorius_lab.doctor_admission_research import ResearchInstrumentAdmission

HAS_DOCTOR = importlib.util.find_spec("doctor_lives") is not None


@unittest.skipUnless(HAS_DOCTOR, "cross-repo integration requires pinned The-Doctor-Lives")
class DoctorInstrumentAdmissionTests(unittest.TestCase):
    @classmethod
    def small_neural(cls):
        from doctor_lives.neural import DEFAULT_CONFIG
        p = dict(DEFAULT_CONFIG)
        p.update({"neurons": 64, "sensory_dim": 40,
                  "avg_recurrent_degree": 6, "input_degree": 3,
                  "action_population_size": 4, "seed": 1842})
        return p

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.lab = SpatialHabitat.create(self.root / "world.sqlite3")
        self.actor = EmbodiedAccess(self.lab)
        self.actor.initialize()
        BookCustody(self.lab).initialize()
        PhysicalAffordances(self.lab).initialize()
        self.instruments = BenchInstruments(self.lab)
        self.instruments.initialize()
        self.actor.move("station:center")
        self.actor.move("station:bench")
        self.receipt = self.actor.measure("balance:bench", "beaker:001", "mass_g")

    def bridge(self, brain="treatment"):
        return ResearchInstrumentAdmission(
            self.lab.path, self.root / brain, neural_config=self.small_neural())

    def test_real_brain_ingress_and_restart_with_verified_host_memory(self):
        br = self.bridge()
        before = br.brain.status()
        admitted = br.deliver(self.receipt)
        self.assertTrue(admitted["admitted"])
        self.assertIn("brain_memory_id", admitted)
        row = br.brain.brain.store.get_memory(admitted["brain_memory_id"])
        self.assertEqual(row["evidence_class"], "lived_runtime_memory")
        self.assertEqual(row["kind"], "observation")
        self.assertIn("325 g", row["text"])
        self.assertNotIn("330 g", row["text"])
        self.assertNotIn("profile_digest", row["text"])
        self.assertTrue(br.verify()["verified"])
        self.assertGreater(br.brain.status()["tick"], before["tick"])
        del br
        restarted = self.bridge()
        self.assertEqual(restarted.deliver(self.receipt)["brain_memory_id"],
                         admitted["brain_memory_id"])
        self.assertTrue(restarted.verify()["verified"])
        self.assertEqual(len([m for m in restarted.brain.brain.store.memories()
                              if m["source"] == "laboratory-instrument:" +
                              self.receipt["event_hash"]]), 1)

    def test_withheld_control_uses_identical_host_receipt_without_brain_admission(self):
        with_brain = self.bridge("observed")
        without_brain = self.bridge("withheld")
        measured = with_brain.deliver(self.receipt, condition="observed")
        denied = without_brain.deliver(self.receipt, condition="withheld")
        self.assertTrue(measured["admitted"])
        self.assertFalse(denied["admitted"])
        self.assertTrue(with_brain.verify()["verified"])
        self.assertTrue(without_brain.verify()["verified"])
        self.assertEqual(len([x for x in without_brain.brain.brain.store.memories()
                              if x["source"] == "laboratory-instrument:" +
                              self.receipt["event_hash"]]), 0)
        self.assertEqual(self.instruments.verify()["revision"], 1)
        with self.assertRaises(Conflict):
            without_brain.deliver(self.receipt, condition="observed")

    def test_fake_reading_and_bad_hash_rejected_without_brain_change(self):
        br = self.bridge()
        before = br.brain.brain.store.tick
        changed = dict(self.receipt)
        changed["observation"] = dict(changed["observation"])
        changed["observation"]["value"] = 90000
        with self.assertRaises(Conflict):
            br.deliver(changed)
        changed = dict(self.receipt)
        changed["event_hash"] = "0" * 64
        with self.assertRaises(Conflict):
            br.deliver(changed)
        self.assertEqual(br.brain.brain.store.tick, before)
        self.assertTrue(br.verify()["verified"])

    def test_crash_between_brain_ingress_and_bridge_commit_recovers_once(self):
        br = self.bridge()
        with self.assertRaisesRegex(RuntimeError, "Simulated crash"):
            br.deliver(self.receipt, inject_fault=True)
        self.assertEqual(
            len([m for m in br.brain.brain.store.memories()
                 if m["source"] == "laboratory-instrument:" +
                 self.receipt["event_hash"]]), 1)
        del br
        restarted = self.bridge()
        admitted = restarted.deliver(self.receipt)
        self.assertTrue(admitted["admitted"])
        self.assertTrue(restarted.verify()["verified"])
        self.assertEqual(
            len([m for m in restarted.brain.brain.store.memories()
                 if m["source"] == "laboratory-instrument:" +
                 self.receipt["event_hash"]]), 1)

    def test_cross_epoch_state_fails_closed(self):
        br = self.bridge()
        br.deliver(self.receipt)
        other = SpatialHabitat.create(self.root / "unrelated.sqlite3")
        EmbodiedAccess(other).initialize()
        BookCustody(other).initialize()
        PhysicalAffordances(other).initialize()
        BenchInstruments(other).initialize()
        with self.assertRaises(Conflict):
            ResearchInstrumentAdmission(
                other.path, self.root / "treatment",
                neural_config=self.small_neural())

    def test_later_object_relocation_does_not_invalidate_source_history(self):
        br = self.bridge()
        br.deliver(self.receipt)
        self.lab.commit({"op": "place", "object_id": "beaker:001",
                         "anchor_id": "floor:corner:se"})
        self.assertTrue(BenchInstruments(self.lab).verify()["verified"])
        self.assertTrue(br.verify()["verified"])
        with self.assertRaises(Conflict):
            # Same host event cannot be relabelled a control after brain delivery.
            br.deliver(self.receipt, condition="withheld")

    def test_model_scoring_not_claimed_from_direct_memory_presence(self):
        br = self.bridge()
        br.deliver(self.receipt)
        # Production model state actually runs; its recurrent policy is NOT
        # represented as selecting the measurement action. Only memory ingress
        # and source provenance are an evaluated engineering outcome.
        decision = br.brain.cognition("lab-research-pilot")
        self.assertTrue(isinstance(decision["action_scores"], dict))
        self.assertTrue(br.verify()["verified"])
        self.assertNotIn("selected_lab_action", decision)


if __name__ == "__main__":
    unittest.main()
