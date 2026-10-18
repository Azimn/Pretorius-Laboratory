"""The Doctor can write, relocate, and later reread HIS OWN physical paper."""
from pathlib import Path
import tempfile
import unittest

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.daily_rhythm import DailyRhythm, MAX_PAPER_PAGES
from pretorius_lab.subject_port import SubjectPort
from pretorius_lab.physics import Conflict, LabError


class AuthoredPaperTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def home(self, name, *, paper=True):
        world = SpatialHabitat.create(self.root / (name + ".sqlite3"))
        HomeLife(world).initialize()
        life = DailyRhythm(world)
        life.initialize(perishable_meals=True, physical_provisions=True,
                        visible_portions=True, physical_paper=paper)
        subject = SubjectPort(world)
        subject.act("walk", event_id=name+"-hall", station="station:hall")
        subject.act("walk", event_id=name+"-parlor", station="station:parlor")
        subject.act("open", event_id=name+"-desk", container="desk:parlor")
        return world, life, subject

    def test_freeform_authored_words_are_durable_exact_and_time_costed(self):
        world, life, subject = self.home("authored")
        words = "The lamp glows against my notes. I should mend the balance tomorrow."
        before = life.audit_state()["minute"]
        produced = subject.act("write_paper", event_id="my-thought-1", text=words)
        self.assertEqual(produced["inner"], "I write on my paper: " + words)
        self.assertEqual(life.audit_state()["minute"], before + 5)
        read = subject.act("read_paper", event_id="read-my-note", page=1)
        self.assertEqual(read["inner"], "I read what is written on my paper: " + words)
        self.assertEqual(life.audit_state()["minute"], before + 7)
        reopened = SubjectPort(SpatialHabitat(world.path))
        self.assertIn(words, reopened.act("read_paper", event_id="after-restart", page=1)["inner"])
        self.assertTrue(life.verify()["verified"])

    def test_closed_desk_prevents_writing_and_reading_until_open(self):
        _, life, subject = self.home("drawer")
        subject.act("write_paper", event_id="first", text="Leave the vase near the desk.")
        subject.act("close", event_id="close-desk", container="desk:parlor")
        before = life.audit_state()
        with self.assertRaises(Conflict):
            subject.act("read_paper", event_id="can't-reach", page=1)
        with self.assertRaises(Conflict):
            subject.act("write_paper", event_id="can't-write", text="not actually possible")
        self.assertEqual(life.audit_state(), before)
        subject.act("open", event_id="reopen", container="desk:parlor")
        self.assertIn("Leave the vase", subject.act("read_paper", event_id="recovered", page=1)["inner"])
        self.assertTrue(life.verify()["verified"])

    def test_paper_follows_real_physical_custody_across_rooms_and_days(self):
        world, life, subject = self.home("carried")
        words = "The old manuscript belongs on the parlor desk."
        subject.act("write_paper", event_id="write", text=words)
        subject.act("take", event_id="take", item="stationery:paper")
        subject.act("walk", event_id="hall", station="station:hall")
        subject.act("walk", event_id="kitchen", station="station:kitchen")
        subject.act("open", event_id="kitchen-open", container="cupboard:kitchen")
        subject.act("put", event_id="store", item="stationery:paper",
                    container="cupboard:kitchen")
        subject.act("close", event_id="kitchen-close", container="cupboard:kitchen")
        before = life.audit_state()
        with self.assertRaises(Conflict):
            subject.act("read_paper", event_id="behind-closed-door", page=1)
        self.assertEqual(life.audit_state(), before)
        subject.act("open", event_id="kitchen-again", container="cupboard:kitchen")
        self.assertIn(words, subject.act("read_paper", event_id="read-in-kitchen", page=1)["inner"])
        subject.act("walk", event_id="leave-hall", station="station:hall")
        subject.act("walk", event_id="leave-parlor", station="station:parlor")
        with self.assertRaises(Conflict):
            subject.act("read_paper", event_id="offstage", page=1)
        # All past written words still replay even after their paper moved.
        self.assertTrue(DailyRhythm(SpatialHabitat(world.path)).verify()["verified"])

    def test_two_days_later_notes_persist_without_fabricated_memory(self):
        _, life, subject = self.home("after-days")
        words = "Perhaps I should take the quiet morning to read."
        subject.act("write_paper", event_id="write-in-parlor", text=words)
        # Over two simulated days later, an interruption and natural sleep.
        for n in range(12):
            life.advance(240, event_id=f"day-pass-{n}")
        subject.act("walk", event_id="sleep-hall", station="station:hall")
        subject.act("walk", event_id="sleep-bedroom", station="station:bedroom")
        subject.act("sleep", event_id="sleep-after-days")
        subject.act("walk", event_id="wake-hall", station="station:hall")
        subject.act("walk", event_id="wake-parlor", station="station:parlor")
        frame = subject.act("read_paper", event_id="later-encounter", page=1)
        self.assertIn(words, frame["inner"])
        self.assertEqual(len(life.audit_state()["paper_marks"]), 1)
        self.assertTrue(life.verify()["verified"])

    def test_requires_actual_ink_and_valid_visible_work_conditions(self):
        _, life, subject = self.home("no-ink")
        subject.act("take", event_id="ink-take", item="stationery:ink")
        subject.act("walk", event_id="ink-hall", station="station:hall")
        subject.act("walk", event_id="ink-bedroom", station="station:bedroom")
        subject.act("open", event_id="drawer-open", container="drawer:bedside")
        subject.act("put", event_id="ink-deposit", item="stationery:ink",
                    container="drawer:bedside")
        subject.act("walk", event_id="ink-hall2", station="station:hall")
        subject.act("walk", event_id="ink-parlor", station="station:parlor")
        before = life.audit_state()
        with self.assertRaises(Conflict):
            life.act("write_paper", event_id="direct-bypass", text="I cannot write this.")
        self.assertEqual(life.audit_state(), before)
        self.assertTrue(life.verify()["verified"])

    def test_subject_cannot_rewrite_stored_page_by_reusing_receipt(self):
        _, life, subject = self.home("ids")
        subject.act("write_paper", event_id="same-id", text="A written promise.")
        old = life.audit_state()
        subject.act("write_paper", event_id="same-id", text="A written promise.")
        self.assertEqual(life.audit_state(), old)
        with self.assertRaises(Conflict):
            subject.act("write_paper", event_id="same-id", text="A different promise.")
        self.assertEqual(life.audit_state(), old)
        self.assertTrue(life.verify()["verified"])

    def test_sunset_and_lamp_are_real_visual_preconditions(self):
        _, life, subject = self.home("near-night")
        life.advance(240, event_id="morning-to-eleven")
        life.advance(240, event_id="afternoon")
        life.advance(170, event_id="late-afternoon")
        life.act("tick", event_id="minute-1755", minutes=5)
        before = life.audit_state()
        self.assertEqual(before["minute"] % 1440, 17*60+55)
        with self.assertRaises(Conflict):
            subject.act("write_paper", event_id="too-late-to-write",
                        text="Not yet actually written")
        self.assertEqual(life.audit_state(), before)
        subject.act("light", event_id="lamp-lit")
        subject.act("write_paper", event_id="lamp-enabled-writing",
                    text="The lamp lets me finish this page.")
        self.assertEqual(life.audit_state()["minute"] % 1440, 18*60)
        subject.act("extinguish", event_id="lamp-out")
        with self.assertRaises(Conflict):
            subject.act("read_paper", event_id="no-night-reading", page=1)
        subject.act("light", event_id="lamp-again")
        self.assertIn("lamp lets me finish",
                      subject.act("read_paper", event_id="read-lit-page", page=1)["inner"])
        self.assertTrue(life.verify()["verified"])

    def test_text_bounds_and_missing_pages_cost_no_time(self):
        _, life, subject = self.home("rejected")
        before = life.audit_state()
        for payload in ("", "   ", "x"*241, "\x00bad"):
            with self.subTest(payload=payload[:12]):
                with self.assertRaises(LabError):
                    subject.act("write_paper", text=payload)
        with self.assertRaises((Conflict, LabError)):
            subject.act("read_paper", page=1)
        self.assertEqual(life.audit_state(), before)
        self.assertTrue(life.verify()["verified"])

    def test_old_version_cannot_write_and_remains_unchanged(self):
        _, old, subject = self.home("old-v4", paper=False)
        before = old.audit_state()
        with self.assertRaises(LabError):
            subject.act("write_paper", event_id="no-v5", text="Invisible history.")
        self.assertEqual(old.audit_state(), before)
        self.assertNotIn("paper_marks", old.audit_state())
        with self.assertRaises(Conflict):
            old.initialize(perishable_meals=True, physical_provisions=True,
                           visible_portions=True, physical_paper=True)
        self.assertTrue(old.verify()["verified"])

    def test_fork_inherits_written_paper_not_parent_lived_events(self):
        world, life, subject = self.home("parent-paper")
        subject.act("write_paper", event_id="on-parent", text="A home I can return to.")
        child_path = self.root / "fork.sqlite3"
        world.fork_to(child_path)
        child = SpatialHabitat(child_path)
        child_subject = SubjectPort(child)
        child_life = DailyRhythm(child)
        self.assertEqual(child_life.audit_state()["paper_marks"],
                         life.audit_state()["paper_marks"])
        self.assertEqual(child_life.verify()["revision"], 0)
        child_subject.act("write_paper", event_id="on-child", text="A different second thought.")
        self.assertEqual(len(child_life.audit_state()["paper_marks"]), 2)
        self.assertEqual(len(life.audit_state()["paper_marks"]), 1)
        self.assertTrue(child_life.verify()["verified"])
        self.assertTrue(life.verify()["verified"])

    def test_paper_pages_are_finite_and_source_verified(self):
        _, life, subject = self.home("bounded")
        for page in range(MAX_PAPER_PAGES):
            subject.act("write_paper", event_id=f"page-{page}", text=f"Page {page+1}")
        before = life.audit_state()
        with self.assertRaises(Conflict):
            subject.act("write_paper", event_id="page-overflow", text="Too much")
        self.assertEqual(life.audit_state(), before)
        self.assertIn("Page 40", subject.act("read_paper", page=40)["inner"])
        self.assertTrue(life.verify()["verified"])

if __name__ == "__main__":
    unittest.main()
