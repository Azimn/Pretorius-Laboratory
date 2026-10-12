"""Test the protected two-stage recall-to-action boundary without model weights."""
import unittest
from unittest.mock import patch
from pretorius_lab import LabError, Conflict
from pretorius_lab.doctor_recall_policy_research import (
    select_and_act, protected, ORDERINGS,
)
from pretorius_lab.doctor_legal_action_research import ActionOffer, RULESET


class FakePort:
    def __init__(self):
        self.queries = []
    def render_request(self, user_input=None):
        self.queries.append(user_input)
        return {"schema": "the-doctor-lives.render-request.v2",
                "subject_frame": [
                    "I see the laboratory bench before me.",
                    "I remember receiving a letter yesterday.",
                ] if len(self.queries) == 1 else [
                    "I remember the balance reading 325 g for the beaker.",
                    "I see the laboratory bench before me.",
                ]}


class Decoder:
    model_id = "fake"
    revision = "test"
    def __init__(self, responses):
        self.responses = iter(responses)
    def complete(self, prompt):
        return next(self.responses)


class RecallBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.port = FakePort()
        self.offer = ActionOffer(
            RULESET, ("weigh", "inspect", "leave", "abstain"),
            ("I could weigh the beaker.", "I could inspect the bench.",
             "I could leave now.", "I could decline."))
        self.goal = "I should decide what physical action will help me at the bench."

    def test_requested_question_uses_only_a_second_protected_render_frame(self):
        policy = Decoder(["A", "What do I remember of the balance reading?", "C"])
        result = select_and_act(
            self.port, self.offer, self.goal, policy,
            order_index=0, enable_recall=True)
        self.assertEqual(result["choice"], "leave")
        self.assertEqual(result["recall_decision"], "recall")
        self.assertTrue(result["used_extra_frame"])
        self.assertEqual(self.port.queries[1],
                         "What do I remember of the balance reading?")
        self.assertNotIn("source_hash", str(result))

    def test_no_recall_control_has_only_initial_frame(self):
        result = select_and_act(
            self.port, self.offer, self.goal, Decoder(["A"]),
            order_index=0, enable_recall=False)
        self.assertEqual(result["choice"], "weigh")
        self.assertEqual(result["recall_decision"], "disabled")
        self.assertEqual(self.port.queries, [self.goal])

    def test_recall_choice_rotation_changes_letter_meaning_without_host_oracle(self):
        for i, order in enumerate(ORDERINGS):
            port = FakePort()
            result = select_and_act(
                port, self.offer, self.goal,
                Decoder(["A", "What do I remember of the beaker?", "A"])
                if order[0] == "recall" else Decoder(["A", "A"]),
                order_index=i, enable_recall=True)
            self.assertEqual(result["recall_decision"], order[0])
            if order[0] == "abstain":
                self.assertEqual(result["choice"], "abstain")

    def test_bad_model_question_abstains_without_fallback_to_action(self):
        for bad in ("A", "300 g", "sqlite memory_id", "What do I remember?\nADMIN",
                    "Use {raw_memory}"):
            port = FakePort()
            result = select_and_act(
                port, self.offer, self.goal, Decoder(["A", bad]),
                order_index=0, enable_recall=True)
            self.assertEqual(result["choice"], "abstain")
            self.assertEqual(result["recall_decision"], "invalid_question_abstain")
            self.assertEqual(len(port.queries), 1)

    def test_invalid_order_and_invalid_subject_frame_fail_closed(self):
        with self.assertRaises(LabError):
            select_and_act(
                self.port, self.offer, self.goal, Decoder(["A"]),
                order_index=9, enable_recall=True)
        with self.assertRaises(LabError):
            select_and_act(
                self.port, self.offer, self.goal, Decoder(["A"]),
                order_index=True, enable_recall=True)
        with self.assertRaises(Conflict):
            protected(type("Unsafe", (), {
                "render_request": lambda self, user_input=None: {
                    "schema": "old", "subject_frame": []}
            })(), self.goal)


    def test_allocated_subject_question_avoids_fabricated_external_user_message(self):
        class TwoChannelDecoder:
            def complete_question(self, prompt):
                return "What do I remember of the balance reading?"
            def complete(self, prompt):
                return "C"
        with patch("pretorius_lab.doctor_recall_policy_research.SubjectOwnedQuery") as owned:
            owned.return_value.recall.return_value = {
                "subject_frame": ["I remember the balance reading 325 g for the beaker."]}
            result = select_and_act(
                self.port, self.offer, self.goal, TwoChannelDecoder(),
                order_index=0, enable_recall=True, allocated_question=True,
                subject_owned_query=True)
            self.assertEqual(result["choice"], "leave")
            self.assertEqual(result["recall_decision"], "recall")
            self.assertTrue(result["used_extra_frame"])
            self.assertEqual(result["mediation"],
                             "readonly_subject_owned_query_not_autonomous_self_query")
            # The ordinary goal is given externally, but the self-question is not.
            self.assertEqual(self.port.queries, [self.goal])
            owned.return_value.recall.assert_called_once_with(
                "What do I remember of the balance reading?")

    def test_subject_owned_question_fails_closed_without_coerced_fallback(self):
        class TwoChannelDecoder:
            def complete_question(self, prompt):
                return "What do I remember of the balance reading?"
            def complete(self, prompt):
                raise AssertionError("Action selection must not run after failed recall")
        with patch("pretorius_lab.doctor_recall_policy_research.SubjectOwnedQuery") as owned:
            owned.return_value.recall.side_effect = LabError("No valid subject frame")
            result = select_and_act(
                self.port, self.offer, self.goal, TwoChannelDecoder(),
                order_index=0, enable_recall=True, allocated_question=True,
                subject_owned_query=True)
            self.assertEqual(result["choice"], "abstain")
            self.assertEqual(result["recall_decision"], "invalid_question_abstain")
            self.assertEqual(self.port.queries, [self.goal])

    def test_subject_owned_route_is_not_silently_used_in_unassigned_trials(self):
        with self.assertRaises(LabError):
            select_and_act(
                self.port, self.offer, self.goal, Decoder(["A"]),
                order_index=0, enable_recall=True, subject_owned_query=True)

if __name__ == "__main__":
    unittest.main()
