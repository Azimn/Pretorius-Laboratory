"""World-grounded action discovery without forced goals or magic object state."""
from pathlib import Path
import tempfile
import unittest

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.home_affordances import HomeAffordances
from pretorius_lab.physics import Conflict, LabError


class DiscoverableHomeTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.lab = SpatialHabitat.create(self.root / "home.sqlite3")
        HomeLife(self.lab).initialize()
        self.life = DailyRhythm(self.lab)
        self.life.initialize(perishable_meals=True, physical_provisions=True,
                             visible_portions=True, physical_paper=True)
        self.home = HomeAffordances(self.lab)

    def offered(self, command, **args):
        offers = self.home.discover()["offers"]
        result = [x for x in offers if x["command"] == command
                  and x["args"] == args]
        return result[0] if result else None

    def do(self, command, id, **args):
        entry = self.offered(command, **args)
        self.assertIsNotNone(entry, (command, args))
        return self.home.act(entry["offer_id"], event_id=id)

    def kitchen(self):
        self.do("walk", "hallway", station="station:hall")
        self.do("walk", "kitchen", station="station:kitchen")

    def parlor(self):
        self.do("walk", "hallway", station="station:hall")
        self.do("walk", "parlor", station="station:parlor")

    def test_listing_is_nonmutating_and_does_not_choose_his_activity(self):
        before = self.life.audit_state()
        body_before = self.home.body.verify()["station"]
        a = self.home.discover()
        b = self.home.discover()
        self.assertEqual(a, b)
        self.assertEqual(self.life.audit_state(), before)
        self.assertEqual(self.home.body.verify()["station"], body_before)
        self.assertEqual(set(a["subject_frame"]), {"inner", "spoken_aloud"})
        self.assertTrue(a["subject_frame"]["inner"].startswith("I "))
        self.assertNotIn("world_epoch", a["subject_frame"]["inner"])
        self.assertNotIn("rations=", a["subject_frame"]["inner"])
        self.assertTrue(a["offers"])
        self.assertTrue(all(x["description"].startswith("I could ")
                            for x in a["offers"]))
        self.assertTrue(self.life.verify()["verified"])

    def test_closed_cupboard_hides_material_tea_affordance_and_depletion(self):
        self.kitchen()
        self.assertIsNone(self.offered("brew_tea"))
        self.do("open", "open-cupboard", container="cupboard:kitchen")
        self.assertIsNotNone(self.offered("brew_tea"))
        for i in range(3):
            self.do("brew_tea", f"cup-{i}")
        self.assertEqual(self.life.audit_state()["supplies"]["tea"], 0)
        self.assertIsNone(self.offered("brew_tea"))
        self.assertIsNotNone(self.offered("clean") or self.offered("prepare_meal"))
        self.assertTrue(self.life.verify()["verified"])

    def test_paper_writing_is_subject_authored_and_survives_restart(self):
        self.parlor()
        self.assertIsNone(self.offered("write_paper"))
        self.do("open", "open-writing-desk", container="desk:parlor")
        paper = self.offered("write_paper")
        self.assertIsNotNone(paper)
        self.assertTrue(paper["requires_my_own_words"])
        self.assertEqual(paper["args"], {})
        words = "I should finish cataloguing the little crystal tomorrow."
        with self.assertRaises(LabError):
            self.home.act(paper["offer_id"], event_id="missing-my-words")
        self.assertEqual(self.life.audit_state()["paper_marks"], [])
        result = self.home.act(paper["offer_id"], event_id="my-own-note",
                               text=words)
        self.assertIn(words, result["inner"])
        self.assertEqual(self.life.audit_state()["paper_marks"], [words])
        old_page = self.offered("read_paper", page=1)
        self.assertIsNotNone(old_page)
        reopened = HomeAffordances(SpatialHabitat(self.lab.path))
        reread = reopened.act(old_page["offer_id"], event_id="read-after-restart")
        self.assertIn(words, reread["inner"])
        self.assertTrue(self.life.verify()["verified"])

    def test_token_goes_stale_when_physical_location_changes(self):
        self.kitchen()
        bread = self.offered("take", item="food:bread")
        self.assertIsNotNone(bread)
        self.do("walk", "leave-kitchen", station="station:hall")
        before = self.life.audit_state()
        with self.assertRaises(Conflict):
            self.home.act(bread["offer_id"], event_id="remote-bread-take")
        self.assertEqual(self.life.audit_state(), before)
        self.assertTrue(self.life.verify()["verified"])

    def test_when_too_dark_furniture_is_not_magically_accessible(self):
        self.kitchen()
        for i in range(3):
            self.life.advance(240, event_id=f"wait-dark-{i}")
        self.assertNotIn("open", [x["command"] for x in self.home.discover()["offers"]])
        self.assertIsNotNone(self.offered("light"))
        self.do("light", "kitchen-lamp")
        self.assertIsNotNone(
            self.offered("open", container="cupboard:kitchen"))
        self.assertTrue(self.life.verify()["verified"])

    def test_forged_and_wrong_payload_offer_is_not_a_physical_action(self):
        self.kitchen()
        before = self.life.audit_state()
        with self.assertRaises(Conflict):
            self.home.act("0" * 64, event_id="fabricated")
        valid = self.offered("open", container="cupboard:kitchen")
        self.assertIsNotNone(valid)
        with self.assertRaises(LabError):
            self.home.act(valid["offer_id"], event_id="extra-stuff",
                          text="I invent a hidden letter")
        self.assertEqual(self.life.audit_state(), before)
        self.assertTrue(self.life.verify()["verified"])

    def test_returning_to_paper_in_another_room_cannot_read_offstage(self):
        self.parlor()
        self.do("open", "open-desk", container="desk:parlor")
        note = self.offered("write_paper")
        self.home.act(note["offer_id"], event_id="write-real-paper",
                      text="The paper remains in my desk.")
        self.do("close", "shut-desk", container="desk:parlor")
        self.assertIsNone(self.offered("read_paper", page=1))
        self.do("open", "reopen-desk", container="desk:parlor")
        self.assertIsNotNone(self.offered("read_paper", page=1))
        self.do("walk", "back-hall", station="station:hall")
        self.assertIsNone(self.offered("read_paper", page=1))
        self.assertTrue(self.life.verify()["verified"])


if __name__ == "__main__":
    unittest.main()
