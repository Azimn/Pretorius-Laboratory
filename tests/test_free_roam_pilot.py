"""Free-living ChatGPT stand-in safety: no narration as material evidence."""
import tempfile
from pathlib import Path
import unittest

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.home_arrangement import HomeArrangements
from pretorius_lab.material_objects import MaterialObjects
from pretorius_lab.personal_projects import PersonalProjects
from pretorius_lab.free_roam_pilot import FreeRoamPilot
from pretorius_lab.physics import Conflict


class ShadowPilotTests(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.world = SpatialHabitat.create(Path(root.name) / "lab.sqlite3")
        HomeLife(self.world).initialize()
        DailyRhythm(self.world).initialize(
            perishable_meals=True, physical_provisions=True,
            visible_portions=True, physical_paper=True)
        MaterialObjects(self.world).initialize()
        HomeArrangements(self.world).initialize()
        PersonalProjects(self.world).initialize()
        self.pilot = FreeRoamPilot(self.world, "chatgpt-shadow-A")

    def choice(self, command, **args):
        return next((x for x in self.pilot.observe()["host"]["offers"]
                     if x["command"] == command and x["args"] == args), None)

    def do(self, command, num, *, text=None, **args):
        offer = self.choice(command, **args)
        self.assertIsNotNone(offer, (command, args))
        return self.pilot.act(
            turn_id=f"turn-{num}", intention="I choose " + command,
            offer_id=offer["offer_id"], event_id=f"real-{num}", text=text)

    def parlor(self):
        self.do("walk", "hall", station="station:hall")
        self.do("walk", "parlor", station="station:parlor")

    def test_narrative_is_shadow_only_not_an_invented_chair_move(self):
        original = HomeArrangements(self.world).audit_state()
        prior = self.pilot.observe()
        moment = self.pilot.narrative(
            turn_id="soft-window", text="I imagine moving the chair by the window.")
        self.assertEqual(moment["source_class"],
                         "external_author_unverified_nonmaterial")
        self.assertEqual(moment["subject"]["inner"],
                         "I imagine moving the chair by the window.")
        self.pilot.unsupported(
            turn_id="wish-for-carving",
            intention="I want to carve a wooden face into the side table.",
            reason="No source-backed carving operation")
        self.pilot.idle(turn_id="just-watch-rain")
        self.assertEqual(HomeArrangements(self.world).audit_state(), original)
        self.assertEqual(DailyRhythm(self.world).audit_state()["minute"], 420)
        self.assertEqual(self.pilot.observe()["subject"], prior["subject"])
        audit = self.pilot.audit()
        self.assertEqual(audit["committed"], 0)
        self.assertEqual(audit["shadow_narratives"], 1)
        self.assertEqual(len(audit["barriers"]), 1)
        self.assertIn("carve a wooden face", audit["barriers"][0]["intention"])

    def test_real_world_action_replays_and_persists_across_process_restart(self):
        self.parlor()
        pre = self.choice("arrange:move", object="chair:parlor",
                          anchor="parlor:window")
        outcome = self.pilot.act(
            turn_id="chair-choice",
            intention="I move the chair by the window.",
            offer_id=pre["offer_id"], event_id="chair-material-receipt")
        self.assertEqual(outcome["status"], "committed")
        self.assertEqual(outcome["receipt"]["source_table"], "arrangement_events")
        self.assertEqual(
            HomeArrangements(self.world).audit_state()["chair:parlor"]["anchor"],
            "parlor:window")
        other = FreeRoamPilot(SpatialHabitat(self.world.path), "chatgpt-shadow-A")
        self.assertEqual(other.audit()["committed"], 3)
        self.assertIn("beside the window", other.observe()["subject"]["inner"])
        self.assertEqual(other.act(
            turn_id="chair-choice", intention="I move the chair by the window.",
            offer_id=pre["offer_id"], event_id="chair-material-receipt"),
            outcome)
        self.assertTrue(HomeArrangements(self.world).verify()["verified"])

    def test_stale_offer_is_logged_as_blocker_and_does_not_change_world(self):
        self.parlor()
        old = self.choice("arrange:move", object="chair:parlor",
                          anchor="parlor:window")
        self.do("arrange:turn", "face-chair",
                object="chair:parlor", facing="parlor:door")
        blocked = self.pilot.act(
            turn_id="stale-proposal", intention="I move the chair beside the window.",
            offer_id=old["offer_id"], event_id="stale-no-receipt")
        self.assertEqual(blocked["status"], "blocked")
        self.assertIsNone(blocked["receipt"])
        self.assertEqual(
            HomeArrangements(self.world).audit_state()["chair:parlor"]["anchor"],
            "parlor:hearth")
        with self.world._open() as db:
            self.assertIsNone(db.execute(
                "SELECT 1 FROM arrangement_events WHERE event_id='stale-no-receipt'"
            ).fetchone())
        self.assertEqual(self.pilot.audit()["barriers"][-1]["turn_id"],
                         "stale-proposal")

    def test_project_starts_with_subject_words_not_completed_physical_experiment(self):
        before = DailyRhythm(self.world).audit_state()["experiments"]
        offered = self.choice("project:start", project_id="project:0001")
        result = self.pilot.act(
            turn_id="own-intention",
            intention="I want to investigate odd properties of crystal.",
            offer_id=offered["offer_id"], event_id="actual-project-declaration",
            text="Investigate how a crystal behaves in weak lamplight.")
        self.assertEqual(result["status"], "committed")
        self.assertEqual(result["receipt"]["source_table"], "project_events")
        self.assertEqual(DailyRhythm(self.world).audit_state()["experiments"], before)
        self.assertEqual(
            PersonalProjects(self.world).audit_state()["projects"]["project:0001"]["status"],
            "active")

    def test_interrupted_receipt_is_reconciled_from_physics_not_trusted_prose(self):
        self.parlor()
        offer = self.choice("arrange:move", object="chair:parlor",
                            anchor="parlor:window")
        self.pilot._begin("interrupted-delivery", {
            "kind": "physical_attempt", "intention": "I move my chair.",
            "offer_id": offer["offer_id"], "event_id": "real-window-move",
            "text": None, "status": "pending", "receipt": None,
            "reason": None, "source_table": "arrangement_events",
            "command": "arrange:move", "args": offer["args"],
        })
        self.pilot.actions.execute(
            offer["offer_id"], event_id="real-window-move")
        recovered = FreeRoamPilot(
            SpatialHabitat(self.world.path), "chatgpt-shadow-A"
        ).recover("interrupted-delivery")
        self.assertEqual(recovered["status"], "recovered")
        self.assertEqual(recovered["receipt"]["source_event_id"], "real-window-move")
        self.assertTrue(HomeArrangements(self.world).verify()["verified"])

    def test_interrupted_without_receipt_does_not_forge_success(self):
        original = HomeArrangements(self.world).audit_state()
        self.pilot._begin("interrupted-unexecuted", {
            "kind": "physical_attempt", "intention": "I wish to move the chair.",
            "offer_id": "0"*64, "event_id": "no-such-event",
            "text": None, "status": "pending", "receipt": None,
            "reason": None, "source_table": "arrangement_events",
            "command": "arrange:move",
            "args": {"object": "chair:parlor", "anchor": "parlor:window"},
        })
        result = self.pilot.recover("interrupted-unexecuted")
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual(result["receipt"], None)
        self.assertEqual(HomeArrangements(self.world).audit_state(), original)
        self.assertTrue(any(x["turn_id"] == "interrupted-unexecuted"
                            for x in self.pilot.audit()["barriers"]))

    def test_soft_event_must_be_first_person_and_cannot_claim_a_source_receipt(self):
        from pretorius_lab.physics import LabError
        before = HomeArrangements(self.world).audit_state()
        with self.assertRaises(LabError):
            self.pilot.narrative(turn_id="invalid-witness",
                                 text="The chair moved itself across the room.")
        witness = self.pilot.narrative(
            turn_id="wind-no-effect",
            text="I hear a passing draft against the window.",
            kind="ambient_impression")
        self.assertEqual(witness["status"], "narrative_only")
        self.assertIsNone(witness["receipt"])
        self.assertEqual(HomeArrangements(self.world).audit_state(), before)

    def test_reusing_an_old_turn_id_with_different_intent_is_denied(self):
        self.pilot.narrative(turn_id="a-thought",
                             text="I wonder if I should make tea.")
        with self.assertRaises(Conflict):
            self.pilot.narrative(turn_id="a-thought",
                                 text="I already brewed tea.")


if __name__ == "__main__":
    unittest.main()
