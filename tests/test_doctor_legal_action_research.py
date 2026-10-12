"""Boundary tests: policy choices do not bypass physical world action authority."""
import tempfile
import unittest
from pathlib import Path

from pretorius_lab import LabError, Conflict
from pretorius_lab.embodied_access import EmbodiedAccess
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.book_custody import BookCustody
from pretorius_lab.physical_affordances import PhysicalAffordances
from pretorius_lab.bench_instruments import BenchInstruments
from pretorius_lab.doctor_legal_action_research import (
    LegalBenchActionGate, ActionOffer, TENDENCY_MAP, RULESET,
    propose_from_brain, propose_stateful_non_neural, assess_delayed_choice,
)


class LegalActionBoundaryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.lab = SpatialHabitat.create(Path(tmp.name) / "world.sqlite3")
        self.actor = EmbodiedAccess(self.lab)
        self.actor.initialize()
        BookCustody(self.lab).initialize()
        PhysicalAffordances(self.lab).initialize()
        BenchInstruments(self.lab).initialize()
        self.gate = LegalBenchActionGate(self.lab)

    def at_bench(self):
        self.actor.move("station:center")
        self.actor.move("station:bench")

    def test_bench_only_legal_options_never_expose_host_mass(self):
        door = self.gate.offer()
        self.assertEqual(door.choices, ("abstain",))
        self.at_bench()
        choices = self.gate.offer()
        self.assertEqual(choices.choices, ("weigh", "inspect", "leave", "abstain"))
        self.assertTrue(all("I " in v for v in choices.subject_native_options))
        self.assertNotIn("330", str(choices.subject_native_options))
        self.assertNotIn("mass_g", str(choices.subject_native_options))

    def test_lost_beaker_changes_action_eligibility_and_stale_action_refused(self):
        self.at_bench()
        self.lab.commit({"op": "place", "object_id": "beaker:001",
                         "anchor_id": "floor:corner:se"})
        self.assertNotIn("weigh", self.gate.offer().choices)
        with self.assertRaises(Conflict):
            self.gate.execute("weigh")
        self.assertEqual(BenchInstruments(self.lab).verify()["revision"], 0)

    def test_model_cannot_inject_operand_or_request_privileged_action(self):
        self.at_bench()
        for name in ("operator_place", "weigh:book:007", "admin", "", 9):
            with self.assertRaises(LabError):
                self.gate.execute(name)
        self.assertEqual(BenchInstruments(self.lab).verify()["revision"], 0)

    def test_accepted_weigh_uses_real_host_event_and_not_synthetic_success(self):
        self.at_bench()
        executed = self.gate.execute("weigh", event_id="legal-accepted")
        self.assertTrue(executed["accepted"])
        self.assertEqual(executed["host_domain"], "instrument")
        self.assertEqual(BenchInstruments(self.lab).verify()["revision"], 1)
        duplicate = self.gate.execute("weigh", event_id="legal-accepted")
        self.assertEqual(duplicate, executed)
        self.assertEqual(BenchInstruments(self.lab).verify()["revision"], 1)

    def test_move_changes_physical_actor_state_and_cannot_reuse_bench_offer(self):
        self.at_bench()
        receipt = self.gate.execute("leave")
        self.assertTrue(receipt["accepted"])
        self.assertEqual(self.actor.verify()["station"], "station:center")
        with self.assertRaises(Conflict):
            self.gate.execute("leave")

    def test_stateful_comparator_no_host_numerical_inputs(self):
        offer = ActionOffer(RULESET, ("weigh", "inspect", "leave", "abstain"),
                            ("I could weigh.", "I could look.", "I could leave.", "I cannot decide."))
        self.assertEqual(propose_stateful_non_neural(observed=False, offer=offer)["choice"],
                         "weigh")
        self.assertEqual(propose_stateful_non_neural(observed=True, offer=offer)["choice"],
                         "leave")
        with self.assertRaises(LabError):
            propose_stateful_non_neural(observed=0.5, offer=offer)

    def test_fixed_brain_tendency_not_automatically_replaced_by_goal_oracle(self):
        class DummyBrain:
            def cognition(self, trigger):
                return {"policy_decision_id": "policy-1",
                        "selected_action": "approach"}
        offer = ActionOffer(RULESET, ("weigh", "inspect", "leave", "abstain"),
                            ("weigh", "look", "leave", "abstain"))
        result = propose_from_brain(DummyBrain(), offer)
        self.assertEqual(result["choice"], "inspect")
        self.assertEqual(result["brain_tendency"], "approach")
        self.assertEqual(len(TENDENCY_MAP), 10)
        self.assertFalse(assess_delayed_choice(
            delivered=False, proposal=result,
            receipt={"accepted": True, "choice": "inspect"},
            before_instrument_events=1, after_instrument_events=1)["success"])

    def test_abstention_is_never_goal_success(self):
        self.at_bench()
        outcome = self.gate.execute("abstain")
        self.assertFalse(outcome["accepted"])
        s = assess_delayed_choice(
            delivered=True, proposal={"choice": "abstain"},
            receipt=outcome, before_instrument_events=0, after_instrument_events=0)
        self.assertFalse(s["success"])


if __name__ == "__main__":
    unittest.main()
