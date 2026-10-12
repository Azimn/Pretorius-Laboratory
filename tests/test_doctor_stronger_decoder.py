"""The stronger decoder remains a pure renderer; never gains engineer state."""
import json
import unittest
from unittest.mock import patch

from pretorius_lab.doctor_stronger_local_decoder import (
    PinnedQwen25, MODEL_ID, MODEL_REVISION, ENGINE,
)
from pretorius_lab.doctor_recall_policy_research import select_and_act
from pretorius_lab.doctor_legal_action_research import ActionOffer, RULESET
from pretorius_lab.doctor_subject_frame_proposer import choose_from_subject_frame


class ProtectedBrain:
    def __init__(self):
        self.calls = []

    def render_request(self, user_input=None):
        self.calls.append(user_input)
        return {
            "schema": "the-doctor-lives.render-request.v2",
            "subject_frame": [
                "I can see the balance on the workbench.",
                "I remember the balance showing about 325 g before I walked away.",
            ],
            "host_mass": 330,
            "engineer_audit": "NEVER_FORWARD_THIS",
        }


class FiniteDecoder:
    model_id = MODEL_ID
    revision = MODEL_REVISION

    def __init__(self, decisions):
        self.answers = iter(decisions)
        self.prompts = []

    def complete(self, prompt):
        self.prompts.append(("action", prompt))
        return next(self.answers)

    def complete_question(self, prompt):
        self.prompts.append(("question", prompt))
        return "What do I remember seeing on the balance?"


class StrongerDecoderTests(unittest.TestCase):
    def setUp(self):
        self.brain = ProtectedBrain()
        self.offer = ActionOffer(
            RULESET, ("weigh", "inspect", "leave", "abstain"),
            ("I could weigh the beaker.", "I could inspect the bench.",
             "I could leave the workbench.", "I could refrain from acting."))
        self.goal = "I must avoid repeating a balance measurement if I already saw one."

    def test_model_is_external_decoder_not_part_of_brain(self):
        self.assertEqual(MODEL_ID, "Qwen/Qwen2.5-1.5B-Instruct")
        self.assertEqual(MODEL_REVISION, "989aa79")
        self.assertTrue(ENGINE.startswith("cpu-"))
        self.assertTrue(callable(PinnedQwen25.complete_question))
        self.assertNotIn("Brain", PinnedQwen25.__name__)

    def test_action_prompt_contains_first_person_but_not_engineer_audit(self):
        stub = FiniteDecoder(["C"])
        result = choose_from_subject_frame(
            self.brain, self.offer, self.goal, stub)
        self.assertEqual(result["choice"], "leave")
        prompt = stub.prompts[0][1]
        self.assertIn("325 g", prompt)
        self.assertNotIn("host_mass", prompt)
        self.assertNotIn("NEVER_FORWARD_THIS", prompt)
        self.assertNotIn("330", prompt)

    def test_model_chosen_recall_produces_a_question_not_host_selected_answer(self):
        stub = FiniteDecoder(["A", "C"])
        result = select_and_act(
            self.brain, self.offer, self.goal, stub,
            order_index=0, enable_recall=True)
        self.assertEqual(result["recall_decision"], "recall")
        self.assertEqual(result["choice"], "leave")
        self.assertTrue(result["used_extra_frame"])
        self.assertEqual(
            result["generated_query"],
            "What do I remember seeing on the balance?")
        self.assertTrue(any(channel == "question" for channel, _ in stub.prompts))
        self.assertEqual(len(self.brain.calls), 2)

    def test_allocated_question_is_model_written_but_not_model_initiated(self):
        stub = FiniteDecoder(["C"])
        result = select_and_act(
            self.brain, self.offer, self.goal, stub,
            order_index=2, enable_recall=True, allocated_question=True)
        self.assertEqual(result["choice"], "leave")
        self.assertTrue(result["allocated_question"])
        self.assertEqual(result["recall_decision"], "recall")
        self.assertEqual(len(stub.prompts), 2)
        self.assertEqual(stub.prompts[0][0], "question")
        self.assertEqual(stub.prompts[1][0], "action")
        self.assertEqual(len(self.brain.calls), 2)

    def test_invalid_choice_still_abstains_without_host_repair(self):
        stub = FiniteDecoder(["I choose C because the weight was given"])
        result = choose_from_subject_frame(
            self.brain, self.offer, self.goal, stub)
        self.assertEqual(result["choice"], "abstain")
        self.assertTrue(result["invalid_output"])


if __name__ == "__main__":
    unittest.main()
