"""Manual ChatGPT renderer pilot: physical truth vs transient language vs gaps."""
import json
import sqlite3
import tempfile
from pathlib import Path
import unittest

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.home_arrangement import HomeArrangements
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.material_objects import MaterialObjects
from pretorius_lab.personal_projects import PersonalProjects
from pretorius_lab.book_library import BookLibrary
from pretorius_lab.field_residency import ResidencyTrial, TrialJournal
from pretorius_lab.physics import Conflict, LabError


class ChatGPTResidencyPilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.world = SpatialHabitat.create(self.root / "research.sqlite3")
        HomeLife(self.world).initialize()
        self.clock = DailyRhythm(self.world)
        self.clock.initialize(perishable_meals=True, physical_provisions=True,
                              visible_portions=True, physical_paper=True)
        HomeArrangements(self.world).initialize()
        MaterialObjects(self.world).initialize()
        PersonalProjects(self.world).initialize()
        BookLibrary(self.world).initialize()
        self.log = self.root / "field_observations.jsonl"
        self.trial = ResidencyTrial(self.world, self.log)

    def choose(self, starts, eid, *, text=None):
        choices = [s for s in self.trial.packet()["possible_activities"]
                   if s.startswith(starts)]
        self.assertEqual(len(choices), 1, choices)
        return self.trial.attempt(choices[0], event_id=eid, subject_text=text)

    def parlor(self):
        self.choose("I could walk toward the hall", "hallway-step")
        self.choose("I could walk toward the parlor", "parlor-step")

    def test_only_natural_world_frame_crosses_into_renderer(self):
        first = self.trial.packet()
        self.assertTrue(first["first_person_world"].startswith("I "))
        self.assertTrue(first["possible_activities"])
        self.assertTrue(all(s.startswith("I could ") for s in first["possible_activities"]))
        packet_text = json.dumps(first)
        for secret in ("project:0001", "world_epoch", "source_event_hash",
                       "source_table", "source_domain", "world_stamp", "lab_id"):
            self.assertNotIn(secret, packet_text)
        self.assertEqual(self.trial.barriers(), [])
        self.assertEqual(PersonalProjects(self.world).audit_state()["projects"], {})
        self.assertEqual(self.trial.journal.verify()[0]["kind"], "session")

    def test_freeform_renderer_intention_is_not_physical_success(self):
        start = self.choose("I could start a project", "start-independent-idea",
                            text="I want to compare two ways of heating glass.")
        self.assertEqual(start["status"], "committed")
        self.assertEqual(start["source_table"], "project_events")
        self.assertEqual(self.clock.audit_state()["experiments"], 0)
        assert "I decide" in start["first_person"]
        p = PersonalProjects(self.world).audit_state()["projects"]["project:0001"]
        self.assertEqual(p["intention"], "I want to compare two ways of heating glass.")
        self.assertEqual(p["receipts"], [])
        self.choose("I could leave my unfinished", "pause-independent-idea")
        for day in range(6):
            self.clock.advance(240, event_id=f"field-time-{day}")
        self.trial = ResidencyTrial(SpatialHabitat(self.world.path), self.log)
        self.assertEqual(PersonalProjects(self.world).audit_state()
                         ["projects"]["project:0001"]["status"], "paused")
        self.assertEqual(self.clock.audit_state()["experiments"], 0)
        resumed = self.choose("I could return to the project", "resume-by-choice")
        self.assertEqual(resumed["status"], "committed")
        self.assertIn("I decide to return", resumed["first_person"])
        self.assertTrue(PersonalProjects(self.world).verify()["verified"])

    def test_unusual_furniture_request_commits_real_change_across_next_day(self):
        self.parlor()
        outcome = self.trial.attempt(
            "Move the chair by the window", event_id="residency-chair")
        self.assertEqual(outcome["status"], "committed")
        self.assertEqual(outcome["source_table"], "arrangement_events")
        for i in range(6):
            self.clock.advance(240, event_id=f"tomorrow-{i}")
        restarted = ResidencyTrial(SpatialHabitat(self.world.path), self.log)
        self.assertIn("beside the window", restarted.packet()["first_person_world"])
        self.assertEqual(
            HomeArrangements(self.world).audit_state()["chair:parlor"]["anchor"],
            "parlor:window")
        self.assertTrue(HomeArrangements(self.world).verify()["verified"])

    def test_offscript_barrier_is_recorded_without_fabricated_world_changes(self):
        before = self.clock.audit_state()
        before_arranged = HomeArrangements(self.world).audit_state()
        result = self.trial.attempt(
            "I will go outside and press flowers from my new garden",
            event_id="unscripted-garden")
        self.assertEqual(result["status"], "barrier")
        self.assertEqual(result["kind"], "unsupported_or_ambiguous_intent")
        self.assertEqual(self.clock.audit_state(), before)
        self.assertEqual(HomeArrangements(self.world).audit_state(),
                         before_arranged)
        self.assertEqual(self.trial.barriers()[0]["event_id"], "unscripted-garden")
        self.assertFalse(any(x["kind"] == "physical_receipt"
                             for x in self.trial.journal.verify()))
        with self.assertRaises(Conflict):
            self.trial.attempt(
                "I will go outside and press flowers from my new garden",
                event_id="unscripted-garden")

    def test_momentary_narrative_is_not_weather_or_world_or_false_memory(self):
        before = self.clock.audit_state()
        self.trial.moment("I hear a thin sound like rain against the window.")
        self.assertEqual(self.clock.audit_state(), before)
        last = self.trial.journal.verify()[-1]
        self.assertEqual(last["kind"], "narrative_only_unverified")
        self.assertEqual(last["details"]["world_effect"], None)
        self.assertNotIn("rain", self.trial.packet()["first_person_world"])
        with self.assertRaises(LabError):
            self.trial.moment("It is raining everywhere.")

    def test_authored_note_is_exact_and_not_filled_by_host(self):
        self.parlor()
        self.choose("I could open the writing desk", "desk-open")
        open_page = [s for s in self.trial.packet()["possible_activities"]
                     if "write words of my own choosing" in s]
        self.assertEqual(len(open_page), 1)
        result = self.trial.attempt(open_page[0], event_id="write-my-words",
                                    subject_text="I made no experiment today.")
        self.assertEqual(result["status"], "committed")
        self.assertEqual(self.clock.audit_state()["paper_marks"],
                         ["I made no experiment today."])
        self.assertTrue(self.clock.verify()["verified"])

    def test_recover_interrupted_world_commit_without_second_action(self):
        self.parlor()
        offers = self.trial.actions.discover()
        selected = next(x for x in offers["offers"] if
                        x["command"] == "arrange:move" and
                        x["args"]["object"] == "chair:parlor" and
                        x["args"]["anchor"] == "parlor:window")
        self.trial.journal.append("attempt", {
            "event_id": "crash-between-world-and-log", "renderer": self.trial.renderer,
            "intention": selected["description"],
            "world_stamp": offers["world_stamp"], "match": "exact_visible_opportunity",
            "command": "arrange:move", "source_table": "arrangement_events",
        })
        self.trial.actions.execute(
            selected["offer_id"], event_id="crash-between-world-and-log")
        self.trial = ResidencyTrial(SpatialHabitat(self.world.path), self.log)
        discovered = self.trial.reconcile()
        self.assertEqual(len(discovered), 1)
        self.assertEqual(discovered[0]["status"],
                         "physically_committed_but_delivery_unconfirmed")
        self.assertEqual(self.trial.reconcile(), [])
        self.assertEqual(HomeArrangements(self.world).verify()["revision"], 1)

    def test_tampering_with_observer_log_fails_closed_without_mutating_world(self):
        self.trial.attempt("make a spectral gramophone sing in the yard",
                           event_id="blocked-with-audit")
        contents = self.log.read_text()
        self.log.write_text(contents.replace(
            "blocked-with-audit", "invented-success"), encoding="utf-8")
        with self.assertRaises(Conflict):
            TrialJournal(self.log, self.trial.journal.epoch)
        self.assertEqual(self.clock.audit_state()["experiments"], 0)
        self.assertTrue(self.clock.verify()["verified"])


if __name__ == "__main__":
    unittest.main()
