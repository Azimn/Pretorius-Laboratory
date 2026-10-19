"""Seven-day-possible personal projects without invented physical accomplishment."""
import sqlite3
import json
import tempfile
from pathlib import Path
import unittest

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.material_objects import MaterialObjects
from pretorius_lab.home_arrangement import HomeArrangements
from pretorius_lab.personal_projects import PersonalProjects
from pretorius_lab.unified_home_actions import UnifiedHomeActions
from pretorius_lab.physics import Conflict, LabError


class ProspectiveProjectsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.lab = SpatialHabitat.create(self.root / "lab.sqlite3")
        HomeLife(self.lab).initialize()
        self.clock = DailyRhythm(self.lab)
        self.clock.initialize(perishable_meals=True, physical_provisions=True,
                              visible_portions=True, physical_paper=True)
        HomeArrangements(self.lab).initialize()
        MaterialObjects(self.lab).initialize()
        self.projects = PersonalProjects(self.lab)
        self.projects.initialize()
        self.actions = UnifiedHomeActions(self.lab)

    def offer(self, cmd, **args):
        return next((o for o in self.actions.discover()["offers"]
                     if o["command"] == cmd and o["args"] == args), None)

    def do(self, cmd, eid, *, text=None, **args):
        choice = self.offer(cmd, **args)
        self.assertIsNotNone(choice, (cmd, args))
        return self.actions.execute(choice["offer_id"], event_id=eid, text=text)

    def begin(self):
        return self.do("project:start", "begin-vapor-notes",
                       project_id="project:0001",
                       text="Study the influence of steam on glass condensation.")

    def visit_parlor(self):
        self.do("walk", "go-hall", station="station:hall")
        self.do("walk", "go-parlor", station="station:parlor")

    def test_an_independent_intention_is_not_an_already_completed_experiment(self):
        initial = self.projects.audit_state()
        for _ in range(2):
            self.actions.discover()
        self.assertEqual(self.projects.audit_state(), initial)
        result = self.begin()
        self.assertEqual(result["source_table"], "project_events")
        state = self.projects.audit_state()
        p = state["projects"]["project:0001"]
        self.assertEqual(p["status"], "active")
        self.assertEqual(p["receipts"], [])
        self.assertEqual(p["reflections"], [])
        self.assertEqual(self.clock.audit_state()["experiments"], 0)
        self.assertIn("steam on glass", result["subject"]["inner"])
        self.assertTrue(self.projects.verify()["verified"])

    def test_leave_project_paused_read_and_write_elsewhere_resume_unprompted(self):
        self.begin()
        self.do("project:reflect", "reflect-start", project_id="project:0001",
                text="I should compare two vessels, but I have not built the apparatus.")
        self.do("project:pause", "set-aside", project_id="project:0001")
        self.visit_parlor()
        self.do("open", "open-writing-desk", container="desk:parlor")
        note = "The rose has caught the afternoon light. The experiment can wait."
        self.do("write_paper", "write-unrelated", text=note)
        for i in range(6):
            self.clock.advance(240, event_id=f"pass-day-{i}")
        reopened = UnifiedHomeActions(SpatialHabitat(self.lab.path))
        self.assertIsNotNone(next((x for x in reopened.discover()["offers"]
                  if x["command"] == "project:resume"), None))
        self.assertEqual(
            PersonalProjects(self.lab).audit_state()["projects"]["project:0001"]["status"],
            "paused")
        # The world must not secretly resume or finish it.
        self.assertEqual(self.clock.audit_state()["experiments"], 0)
        return_to_work = reopened.execute(
            next(x["offer_id"] for x in reopened.discover()["offers"]
                 if x["command"] == "project:resume"
                 and x["args"] == {"project_id": "project:0001"}),
            event_id="own-decision-to-resume")
        self.assertIn("I decide to return", return_to_work["subject"]["inner"])
        recalled = self.do("project:review", "review-after-return",
                           project_id="project:0001")
        self.assertIn("two vessels", recalled["subject"]["inner"])
        self.assertEqual(self.clock.audit_state()["paper_marks"], [note])
        self.assertTrue(self.projects.verify()["verified"])

    def test_proved_chair_change_associated_without_pretending_project_complete(self):
        self.begin()
        self.visit_parlor()
        physical = self.do("arrange:move", "arrange-for-research",
                           object="chair:parlor", anchor="parlor:window")
        self.assertEqual(physical["source_table"], "arrangement_events")
        attached = self.projects.act(
            "associate", event_id="associate-actual-chair",
            project_id="project:0001",
            source_table=physical["source_table"],
            source_event_id=physical["source_event_id"],
            source_event_hash=physical["source_event_hash"])
        self.assertIn("actually did", attached["inner"])
        p = self.projects.audit_state()["projects"]["project:0001"]
        self.assertEqual(p["status"], "active")
        self.assertEqual(len(p["receipts"]), 1)
        self.assertEqual(p["receipts"][0]["source_event_hash"],
                         physical["source_event_hash"])
        self.assertEqual(self.clock.audit_state()["experiments"], 0)
        self.assertTrue(self.projects.verify()["verified"])

    def test_no_fake_physical_receipt_and_no_double_association(self):
        self.begin()
        before = self.projects.audit_state()
        with self.assertRaises((Conflict, LabError)):
            self.projects.act(
                "associate", event_id="fake-association",
                project_id="project:0001",
                source_table="arrangement_events",
                source_event_id="never-happened",
                source_event_hash="0"*64)
        self.assertEqual(self.projects.audit_state(), before)
        self.visit_parlor()
        changed = self.do("arrange:move", "chair-receipt",
                          object="chair:parlor", anchor="parlor:window")
        args = dict(project_id="project:0001",
                    source_table=changed["source_table"],
                    source_event_id=changed["source_event_id"],
                    source_event_hash=changed["source_event_hash"])
        self.projects.act("associate", event_id="one-association", **args)
        self.projects.act("associate", event_id="one-association", **args)
        with self.assertRaises(Conflict):
            self.projects.act("associate", event_id="duplicate-other-id", **args)
        with self.assertRaises(Conflict):
            self.projects.act("associate", event_id="one-association",
                              **{**args, "source_event_hash": "0"*64})
        self.assertEqual(
            len(self.projects.audit_state()["projects"]["project:0001"]["receipts"]),1)

    def test_project_finish_is_only_self_declared_and_abandon_has_no_auto_resume(self):
        self.begin()
        self.do("project:finish", "self-declared-finished",
                project_id="project:0001")
        p = self.projects.audit_state()["projects"]["project:0001"]
        self.assertEqual(p["status"], "declared_finished")
        self.assertEqual(p["receipts"], [])
        self.assertIsNone(self.offer("project:resume", project_id="project:0001"))
        self.assertIsNone(self.offer("project:reflect", project_id="project:0001"))
        self.assertTrue(self.projects.verify()["verified"])

    def test_world_fork_inherits_recorded_intention_not_parent_receipts(self):
        self.begin()
        self.visit_parlor()
        actual = self.do("arrange:move", "create-fork-evidence",
                         object="chair:parlor", anchor="parlor:window")
        self.projects.act(
            "associate", event_id="link-before-fork", project_id="project:0001",
            source_table=actual["source_table"],
            source_event_id=actual["source_event_id"],
            source_event_hash=actual["source_event_hash"])
        self.do("project:pause", "pause-before-fork", project_id="project:0001")
        path = self.root/"fork.sqlite3"
        self.lab.fork_to(path)
        inherited = PersonalProjects(SpatialHabitat(path))
        p = inherited.audit_state()["projects"]["project:0001"]
        self.assertEqual(p["status"], "paused")
        self.assertEqual(p["receipts"], [])
        self.assertEqual(inherited.verify()["revision"], 0)
        self.assertEqual(self.projects.verify()["revision"], 3)

    def test_corrupt_project_event_fails_full_replay_without_harming_world(self):
        self.begin()
        with sqlite3.connect(self.lab.path) as db:
            raw = db.execute("SELECT envelope FROM project_events WHERE event_id=?",
                             ("begin-vapor-notes",)).fetchone()[0]
            e = json.loads(raw)
            e["args"]["text"] = "I invented the experiment and it succeeded."
            db.execute("UPDATE project_events SET envelope=? WHERE event_id=?",
                       (json.dumps(e), "begin-vapor-notes"))
        with self.assertRaises(Conflict):
            self.projects.verify()
        self.assertTrue(self.clock.verify()["verified"])
        self.assertTrue(HomeLife(self.lab).verify()["verified"])

    def test_seven_days_real_work_then_read_and_write_without_auto_completion(self):
        from pretorius_lab.book_library import BookLibrary
        self.begin()
        # The bench experiment is real world work with an independently
        # replayable apparatus consequence, not a sentence in a task list.
        self.do("walk", "one-week-center", station="station:center")
        self.do("walk", "one-week-bench", station="station:bench")
        physical = self.do("experiment", "real-test-work")
        self.assertEqual(physical["source_table"], "rhythm_events")
        self.assertEqual(self.clock.audit_state()["experiments"], 1)
        self.projects.act(
            "associate", event_id="link-actual-work",
            project_id="project:0001",
            source_table=physical["source_table"],
            source_event_id=physical["source_event_id"],
            source_event_hash=physical["source_event_hash"])
        self.do("project:pause", "leave-work-alone", project_id="project:0001")
        # Read a genuinely installed book and leave a physical page marker.
        books = BookLibrary(self.lab)
        books.initialize()
        books.install(
            "book:007", edition_id="multi-day-notes-fixture",
            title="Glass and the Experimental Method", author="Test author",
            pages=["The apparatus is placed on a cold table.",
                   "The observation should be repeated on another day."],
            source_class="original_fixture",
            source_reference="test fixture, not historic Pretorius canon")
        self.do("walk", "week-back-center", station="station:center")
        self.do("walk", "week-to-shelf", station="station:shelf:3")
        self.do("book", "open-other-reading", book_id="book:007",
                operation="open")
        self.do("book", "turn-other-page", book_id="book:007",
                operation="turn", direction=1)
        self.do("book", "mark-other-page", book_id="book:007",
                operation="mark", bookmark_id="flag-seven-days")
        self.do("book", "close-other-reading", book_id="book:007",
                operation="close")
        self.do("walk", "week-center-again", station="station:center")
        self.do("walk", "week-to-threshold", station="station:threshold")
        self.visit_parlor()
        self.do("open", "week-desk-open", container="desk:parlor")
        self.do("write_paper", "week-private-note",
                text="Other ideas occurred to me while work remained unfinished.")
        original_clock = self.clock.audit_state()["minute"]
        # Forty-two authenticated four-hour advances, not a fake future date.
        for i in range(42):
            self.clock.advance(240, event_id=f"seven-days-{i}")
        restarted = PersonalProjects(SpatialHabitat(self.lab.path))
        p = restarted.audit_state()["projects"]["project:0001"]
        self.assertEqual(p["status"], "paused")
        self.assertEqual(len(p["receipts"]), 1)
        self.assertEqual(self.clock.audit_state()["minute"] - original_clock,
                         7 * 24 * 60)
        self.assertEqual(self.clock.audit_state()["experiments"], 1)
        self.assertEqual(books.catalog("book:007")["book:007"]["bookmarks"],
                         {"flag-seven-days": 2})
        self.assertEqual(self.clock.audit_state()["paper_marks"],
                         ["Other ideas occurred to me while work remained unfinished."])
        self.assertEqual(restarted.verify()["revision"], 4)
        # It takes a NEW explicit choice to revive the dormant plan.
        self.do("project:resume", "week-return-own-choice",
                project_id="project:0001")
        self.assertEqual(restarted.audit_state()["projects"]["project:0001"]["status"],
                         "active")
        self.assertTrue(books.verify()["verified"])

    def test_old_worlds_without_a_project_ledger_still_work(self):
        other = SpatialHabitat.create(self.root/"old-world.sqlite3")
        HomeLife(other).initialize()
        DailyRhythm(other).initialize()
        self.assertTrue(DailyRhythm(other).verify()["verified"])
        with self.assertRaises(LabError):
            PersonalProjects(other).verify()


if __name__ == "__main__":
    unittest.main()
