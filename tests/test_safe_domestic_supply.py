"""Opt-in household supply and humane life-loop source verification."""
import json
import sqlite3
import tempfile
from pathlib import Path
import unittest

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.daily_rhythm import DailyRhythm, DELIVERY_BUNDLE
from pretorius_lab.unified_home_actions import UnifiedHomeActions
from pretorius_lab.physics import Conflict


class CareWorld(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.lab = SpatialHabitat.create(self.root / "care.sqlite3")
        HomeLife(self.lab).initialize()
        self.time = DailyRhythm(self.lab)
        self.time.initialize(perishable_meals=True, physical_provisions=True,
                             visible_portions=True, physical_paper=True,
                             safe_household=True)
        self.home = UnifiedHomeActions(self.lab)

    def choose(self, command, eid, **kwargs):
        candidates = [x for x in self.home.discover()["offers"]
                      if x["command"] == command and x["args"] == kwargs]
        self.assertEqual(len(candidates), 1, (command, kwargs, candidates))
        return self.home.execute(candidates[0]["offer_id"], event_id=eid)

    def hall(self):
        self.choose("walk", "hall-visit", station="station:hall")

    def kitchen(self, suffix="a"):
        self.choose("walk", "kitchen-"+suffix, station="station:kitchen")

    def test_source_parcel_and_real_unpack_before_resources_increase(self):
        original = self.time.audit_state()
        self.hall()
        self.choose("order_provisions", "order-first")
        self.assertEqual(self.time.audit_state()["supplies"], original["supplies"])
        self.time.advance(240, event_id="delivery-time")
        arrived = self.time.audit_state()
        self.assertEqual(arrived["household_supply"]["parcel"], "hall")
        self.assertEqual(arrived["supplies"], original["supplies"])
        self.choose("collect_provisions", "receive-parcel")
        self.kitchen()
        self.choose("unpack_provisions", "store-parcel")
        delivered = self.time.audit_state()
        self.assertEqual(delivered["household_supply"]["unpacked"], 1)
        self.assertEqual(delivered["meal_ready"], False)
        for item, number in DELIVERY_BUNDLE.items():
            self.assertEqual(delivered["supplies"][item],
                             original["supplies"][item]+number)
        with self.assertRaises(Conflict):
            self.time.act("unpack_provisions", event_id="make-up-parcel")
        self.assertTrue(self.time.verify()["verified"])

    def test_plain_water_no_tea_or_fuel_required(self):
        self.hall()
        self.kitchen("water")
        self.choose("open", "open-kitchen-cupboard", container="cupboard:kitchen")
        prior = self.time.audit_state()
        self.choose("drink_water", "take-plain-water")
        after = self.time.audit_state()
        self.assertEqual(after["supplies"]["water"], prior["supplies"]["water"]-1)
        self.assertEqual(after["supplies"]["tea"], prior["supplies"]["tea"])
        self.assertEqual(after["supplies"]["fuel"], prior["supplies"]["fuel"])
        self.assertLess(after["thirst"], prior["thirst"])
        self.assertTrue(self.time.verify()["verified"])

    def test_uncooked_bread_provides_agent_control_when_fuel_is_not_needed(self):
        self.hall()
        self.kitchen("bread")
        self.choose("open", "open-for-bread", container="cupboard:kitchen")
        before = self.time.audit_state()
        self.choose("eat_bread", "eat-simple-bread")
        after = self.time.audit_state()
        self.assertEqual(after["supplies"]["rations"],
                         before["supplies"]["rations"] - 1)
        self.assertEqual(after["supplies"]["fuel"], before["supplies"]["fuel"])
        self.assertEqual(after["supplies"]["water"], before["supplies"]["water"])
        self.assertLess(after["hunger"], before["hunger"])
        self.assertTrue(self.time.verify()["verified"])

    def test_second_order_possible_only_after_first_handled(self):
        self.hall()
        self.choose("order_provisions", "order-one")
        with self.assertRaises(Conflict):
            self.time.act("order_provisions", event_id="double-order")
        self.time.advance(240, event_id="arrival-one")
        with self.assertRaises(Conflict):
            self.time.act("order_provisions", event_id="order-while-parcel")
        self.choose("collect_provisions", "collect-one")
        self.kitchen("unpack-one")
        self.choose("unpack_provisions", "unpack-one")
        self.choose("walk", "return-hall", station="station:hall")
        self.choose("order_provisions", "order-two")
        self.assertEqual(self.time.audit_state()["household_supply"]["orders"], 2)

    def test_private_washroom_exists_without_punitive_need_meter(self):
        self.hall()
        self.choose("walk", "enter-bedroom", station="station:bedroom")
        walked = self.choose("walk", "enter-washroom", station="station:washroom")
        self.assertIn("washroom", walked["subject"]["inner"])
        self.assertIn("washroom", self.home.subject.observe()["inner"])
        self.choose("use_washroom", "private-attendance")
        before = self.time.audit_state()
        self.choose("wash_hands", "hands-washed")
        state = self.time.audit_state()
        self.assertEqual(state["washroom"], {"visits": 1, "washed": 1})
        self.assertEqual(state["supplies"]["water"], before["supplies"]["water"]-1)
        self.assertNotIn("bladder", state)
        self.assertTrue(self.time.verify()["verified"])

    def test_v5_legacy_world_cannot_access_new_room_and_remains_valid(self):
        legacy = SpatialHabitat.create(self.root/"legacy.sqlite3")
        HomeLife(legacy).initialize()
        old = DailyRhythm(legacy)
        old.initialize(perishable_meals=True, physical_provisions=True,
                       visible_portions=True, physical_paper=True)
        HomeLife(legacy).walk("station:hall", event_id="legacy-hall")
        HomeLife(legacy).walk("station:bedroom", event_id="legacy-bedroom")
        with self.assertRaises(Conflict):
            HomeLife(legacy).walk("station:washroom", event_id="legacy-no-washroom")
        self.assertTrue(old.verify()["verified"])

    def test_extreme_unattended_need_is_suspended_not_torture_or_magic_feeding(self):
        baseline = self.time.audit_state()
        paused = False
        for n in range(15):
            try:
                self.time.advance(240, event_id=f"no-food-day-{n}")
            except Conflict:
                paused = True
                break
        self.assertTrue(paused)
        stopped = self.time.audit_state()
        self.assertLess(stopped["hunger"], 9)
        self.assertLess(stopped["thirst"], 9)
        self.assertEqual(stopped["supplies"], baseline["supplies"])
        self.hall()
        self.choose("order_provisions", "rescue-order")
        self.assertTrue(self.time.verify()["verified"])

    def test_delivery_replay_restart_and_fork_retain_exact_stores(self):
        self.hall()
        self.choose("order_provisions", "persistent-order")
        self.time.advance(240, event_id="persistent-arrival")
        self.choose("collect_provisions", "persistent-collect")
        reopened = DailyRhythm(SpatialHabitat(self.lab.path))
        self.assertEqual(reopened.audit_state()["household_supply"]["parcel"],
                         "carried")
        self.kitchen("delivery-fork")
        self.choose("unpack_provisions", "persistent-unpack")
        path = self.root/"fork.sqlite3"
        self.lab.fork_to(path)
        child = DailyRhythm(SpatialHabitat(path))
        self.assertTrue(child.verify()["verified"])
        self.assertEqual(child.audit_state(), self.time.audit_state())

    def test_fake_receipt_cannot_restock_the_house(self):
        self.hall()
        self.choose("order_provisions", "legitimate-order")
        with sqlite3.connect(self.lab.path) as db:
            old = json.loads(db.execute(
                "SELECT envelope FROM rhythm_events WHERE event_id=?",
                ("legitimate-order",)).fetchone()[0])
            old["op"] = "unpack_provisions"
            db.execute("UPDATE rhythm_events SET envelope=? WHERE event_id=?",
                       (json.dumps(old), "legitimate-order"))
        with self.assertRaises(Conflict):
            self.time.verify()
        self.assertTrue(HomeLife(self.lab).verify()["verified"])


if __name__ == "__main__":
    unittest.main()
