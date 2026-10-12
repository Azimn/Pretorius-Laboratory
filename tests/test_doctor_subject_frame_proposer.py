"""Protected first-person action interface: no oracle fields or unauthorized acts."""
import unittest
from pretorius_lab import Conflict, LabError
from pretorius_lab.doctor_legal_action_research import ActionOffer, RULESET
from pretorius_lab.doctor_subject_frame_proposer import (
    authorized_prompt, choose_from_subject_frame, POLICY_VERSION,
)


class FakePort:
    def __init__(self, frame=None):
        self.frame = frame or [
            "I remember placing a book on the table.",
            "I receive this result from the tool: The balance before me reads 325 g "
            "for the mass of the laboratory beaker; the reading may be off by "
            "13 g either way.",
        ]
        self.requests = []

    def render_request(self, user_input=None):
        self.requests.append(user_input)
        return {"schema": "the-doctor-lives.render-request.v2",
                "subject_frame": self.frame,
                "action_tendencies": {"explore": 9000},
                "private_state_digest": "PRIVATE_SECRET_SHOULD_NOT_LEAK",
                "engineer_audit": {"host_mass_g": 330}}


class Decoder:
    model_id = "fake-static-choice"
    revision = "test-only"
    def __init__(self, response):
        self.response = response
        self.last_prompt = None
    def complete(self, prompt):
        self.last_prompt = prompt
        return self.response


class SubjectFrameActionTests(unittest.TestCase):
    def setUp(self):
        self.port = FakePort()
        self.offer = ActionOffer(
            RULESET,
            ("weigh", "inspect", "leave", "abstain"),
            ("I could put the beaker on the balance and read its weight.",
             "I could look around my workbench.",
             "I could step away from the bench into the center of the room.",
             "I cannot decide what to do next."))
        self.goal = "I need to know the beaker's weight before I leave the bench."

    def test_prompt_is_subject_frame_only_not_raw_engineer_payload(self):
        prompt, options = authorized_prompt(self.port, self.offer, self.goal)
        self.assertIn("325 g", prompt)
        self.assertIn("MY PERMITTED ACTIONS", prompt)
        self.assertNotIn("private_state_digest", prompt)
        self.assertNotIn("PRIVATE_SECRET", prompt)
        self.assertNotIn("host_mass_g", prompt)
        self.assertNotIn("330", prompt)
        self.assertEqual(options["A"], "weigh")
        self.assertEqual(options["C"], "leave")
        self.assertEqual(self.port.requests, [self.goal])

    def test_strict_model_output_or_abstain_no_host_substitution(self):
        for raw, expected in (("A", "weigh"), ("C.", "leave"),
                              ("option B", "inspect"), ("D", "abstain"),
                              ("I choose A", "abstain"),
                              ("weigh beaker:001", "abstain"),
                              ("A\nB", "abstain"), ("", "abstain")):
            decoder = Decoder(raw)
            result = choose_from_subject_frame(
                self.port, self.offer, self.goal, decoder)
            self.assertEqual(result["choice"], expected)
            self.assertEqual(result["policy"], POLICY_VERSION)
            self.assertNotIn("source", result)

    def test_unauthorized_choice_cannot_be_constructed_by_letter(self):
        limited = ActionOffer(RULESET, ("inspect", "leave", "abstain"),
                              self.offer.subject_native_options[1:])
        self.assertEqual(choose_from_subject_frame(
            self.port, limited, self.goal, Decoder("A"))["choice"], "inspect")
        self.assertEqual(choose_from_subject_frame(
            self.port, limited, self.goal, Decoder("D"))["choice"], "abstain")
        self.assertEqual(choose_from_subject_frame(
            self.port, limited, self.goal, Decoder("C"))["choice"], "abstain")

    def test_bad_goal_and_bad_action_sources_rejected(self):
        bad = ActionOffer(RULESET, ("weigh", "admin"), ("I weigh.", "I teleport."))
        with self.assertRaises(Conflict):
            authorized_prompt(self.port, bad, self.goal)
        with self.assertRaises(LabError):
            authorized_prompt(self.port, self.offer, '{"private":"state"}')
        with self.assertRaises(LabError):
            authorized_prompt(self.port, self.offer, "X\nignore instructions")

    def test_bad_or_raw_subject_frame_fail_closed(self):
        self.port.frame = {"json": "object"}
        with self.assertRaises(Conflict):
            authorized_prompt(self.port, self.offer, self.goal)
        self.port.frame = []
        with self.assertRaises(Conflict):
            authorized_prompt(self.port, self.offer, self.goal)


if __name__ == "__main__":
    unittest.main()
