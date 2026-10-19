"""Care policy and genuine household provisions must close real finite loops."""
import tempfile
from pathlib import Path
import unittest

from pretorius_lab.daily_rhythm import DailyRhythm, transition
from pretorius_lab.home_life import HomeLife
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.material_objects import MaterialObjects
from pretorius_lab.home_arrangement import HomeArrangements
from pretorius_lab.personal_projects import PersonalProjects
from pretorius_lab.free_roam_pilot import FreeRoamPilot
from pretorius_lab.unified_home_actions import UnifiedHomeActions
from pretorius_lab.care_safety import assess
from pretorius_lab.care_contract import HouseholdCareContract
from pretorius_lab.physics import Conflict


class HouseholdCareTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.path = Path(t.name) / "safe-laboratory.sqlite3"
        self.world = SpatialHabitat.create(self.path)
        HomeLife(self.world).initialize()
        self.clock = DailyRhythm(self.world)
        self.clock.initialize(perishable_meals=True, physical_provisions=True,
                              visible_portions=True, physical_paper=True)
        MaterialObjects(self.world).initialize()
        HomeArrangements(self.world).initialize()
        PersonalProjects(self.world).initialize()
        HouseholdCareContract(self.world).initialize()
        self.home = UnifiedHomeActions(self.world)

    def choice(self, command, **args):
        return next((item for item in self.home.discover()["offers"]
                     if item["command"] == command and item["args"] == args), None)

    def do(self, command, eid, **args):
        o = self.choice(command, **args)
        self.assertIsNotNone(o, (command, args))
        return self.home.execute(o["offer_id"], event_id=eid)

    def go_kitchen(self, prefix="walk"):
        self.do("walk", prefix + "-hall", station="station:hall")
        self.do("walk", prefix + "-kitchen", station="station:kitchen")

    def go_hall(self, prefix="walk"):
        self.do("walk", prefix + "-hall", station="station:hall")

    def next_day(self, label):
        for i in range(6):
            self.clock.advance(240, event_id=f"{label}-{i}")

    def test_real_cup_plain_drinking_water_not_forced_to_make_tea(self):
        self.go_kitchen()
        self.assertIsNone(self.choice("drink_water"))
        self.do("open", "open-kitchen-cupboard", container="cupboard:kitchen")
        amount = self.clock.audit_state()["supplies"]["water"]
        after = self.do("drink_water", "drink-water")
        self.assertIn("drink a cup of water", after["subject"]["inner"])
        self.assertEqual(self.clock.audit_state()["supplies"]["water"], amount-1)
        self.assertTrue(self.clock.verify()["verified"])

    def test_an_unseen_courier_cannot_claim_delivery_before_world_morning(self):
        from pretorius_lab.daily_rhythm import available_delivery_day
        self.go_hall()
        with self.world._open() as db:
            self.assertIsNone(available_delivery_day(db, "station:hall"))
        with self.assertRaises(Conflict):
            self.clock.act("accept_delivery", event_id="cheat-day1", day=1)
        # A direct pure reducer caller cannot inject supply into the world.
        with self.assertRaises(Conflict):
            transition(self.clock.audit_state(), "accept_delivery",
                       {"day": 1}, "station:hall", delivery_authorized=False)
        self.next_day("tomorrow")
        with self.world._open() as db:
            self.assertEqual(available_delivery_day(db, "station:hall"), 1)
        self.assertIn("supplier", self.home.subject.observe()["inner"])
        before = self.clock.audit_state()["supplies"]["rations"]
        r = self.do("accept_delivery", "collect-day1", day=1)
        self.assertEqual(r["source_table"], "rhythm_events")
        self.assertEqual(self.clock.audit_state()["supplies"]["rations"], before+4)
        self.assertTrue(self.clock.verify()["verified"])

    def test_depleted_real_tea_can_recover_after_voluntary_supply_collection(self):
        self.go_kitchen()
        self.do("open", "cupboard", container="cupboard:kitchen")
        for i in range(3):
            self.do("brew_tea", f"tea-{i}")
        self.assertEqual(self.clock.audit_state()["supplies"]["tea"], 0)
        self.assertIsNone(self.choice("brew_tea"))
        self.do("walk", "return-hall", station="station:hall")
        self.next_day("day1")
        self.do("accept_delivery", "fresh-packet", day=1)
        self.assertIsNone(self.choice("accept_delivery", day=1))
        with self.assertRaises(Conflict):
            self.clock.act("accept_delivery", event_id="duplicate-day1", day=1)
        # Real fatigue is independent of food inventory. Returning home
        # after a whole day may require rest before further kitchen work.
        self.do("walk", "care-to-bedroom", station="station:bedroom")
        self.do("rest", "care-rest")
        self.do("walk", "care-return-hall", station="station:hall")
        self.do("walk", "back-to-kitchen", station="station:kitchen")
        self.assertIsNotNone(self.choice("brew_tea"))
        self.do("brew_tea", "tea-after-real-restock")
        self.assertTrue(MaterialObjects(self.world).verify()["verified"])
        self.assertTrue(PersonalProjects(self.world).verify()["verified"])
        self.assertTrue(self.clock.verify()["verified"])

    def test_delivery_is_daily_not_an_exploit_and_survives_reopen(self):
        self.go_hall()
        self.next_day("day1")
        self.do("accept_delivery", "day1-arrived", day=1)
        fresh = UnifiedHomeActions(SpatialHabitat(self.path))
        self.assertIsNone(next((o for o in fresh.discover()["offers"]
               if o["command"] == "accept_delivery"), None))
        self.next_day("day2")
        new_packet = next((o for o in fresh.discover()["offers"]
                           if o["command"] == "accept_delivery"
                           and o["args"] == {"day": 2}), None)
        self.assertIsNotNone(new_packet)
        fresh.execute(new_packet["offer_id"], event_id="day2-arrived")
        self.assertTrue(DailyRhythm(SpatialHabitat(self.path)).verify()["verified"])

    def test_original_laboratory_without_opt_in_has_no_invisible_delivery(self):
        from pretorius_lab.daily_rhythm import available_delivery_day
        other = SpatialHabitat.create(self.path.parent / "old-unenrolled.sqlite3")
        HomeLife(other).initialize()
        historic = DailyRhythm(other)
        historic.initialize(perishable_meals=True, physical_provisions=True,
                            visible_portions=True, physical_paper=True)
        from pretorius_lab.subject_port import SubjectPort
        SubjectPort(other).act("walk", event_id="other-hall", station="station:hall")
        for i in range(6):
            historic.advance(240, event_id=f"old-clock-{i}")
        with other._open() as db:
            self.assertIsNone(available_delivery_day(db, "station:hall"))
        with self.assertRaises(Conflict):
            historic.act("accept_delivery", event_id="no-contract", day=1)
        SubjectPort(other).act("walk", event_id="old-bedroom",
                               station="station:bedroom")
        with self.assertRaises(Conflict):
            historic.act("use_washroom", event_id="no-ensuite")
        self.assertTrue(historic.verify()["verified"])

    def test_opt_in_contract_follows_world_fork_without_inventing_old_deliveries(self):
        self.go_hall()
        self.next_day("fork-day")
        self.do("accept_delivery", "original-parcel", day=1)
        dest = self.path.parent / "care-fork.sqlite3"
        self.world.fork_to(dest)
        fork = SpatialHabitat(dest)
        self.assertTrue(HouseholdCareContract(fork).verify()["verified"])
        self.assertTrue(DailyRhythm(fork).verify()["verified"])
        # Inherited pantry condition, not duplicate parent action history.
        self.assertEqual(DailyRhythm(fork).audit_state()["supplies"],
                         self.clock.audit_state()["supplies"])
        with fork._open() as db:
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM rhythm_events").fetchone()[0], 0)

    def test_private_period_washroom_is_reachable_with_no_bladder_drain(self):
        self.go_hall("to-washroom")
        self.do("walk", "to-private-bedroom", station="station:bedroom")
        available = self.choice("use_washroom")
        self.assertIsNotNone(available)
        before = self.clock.audit_state()
        result = self.do("use_washroom", "ordinary-private-washroom")
        self.assertIn("private washroom", result["subject"]["inner"])
        after = self.clock.audit_state()
        self.assertEqual(after["minute"] - before["minute"], 10)
        self.assertEqual(after["supplies"], before["supplies"])
        self.assertFalse("bladder" in after)
        self.assertTrue(self.clock.verify()["verified"])
        self.assertTrue(MaterialObjects(self.world).verify()["verified"])

    def test_welfare_hold_stops_long_sleep_loop_not_access_to_actual_food(self):
        pilot = FreeRoamPilot(self.world, "closed-loops")
        self.go_hall()
        self.next_day("hungry1")
        self.next_day("hungry2")
        status = assess(self.world)
        self.assertTrue(status["pause_unattended_time"])
        self.assertIn("water", status["needed"])
        self.do("walk", "sleep-bedroom", station="station:bedroom")
        offered = next(o for o in pilot.observe()["host"]["offers"]
                       if o["command"] == "sleep")
        time_before = self.clock.audit_state()["minute"]
        result = pilot.act(
            turn_id="neglected-needs", intention="I would sleep again.",
            offer_id=offered["offer_id"], event_id="unattended-sleep")
        self.assertEqual(result["status"], "blocked")
        self.assertIn("Welfare hold", result["reason"])
        self.assertEqual(self.clock.audit_state()["minute"], time_before)
        # Unlike aimless time-skipping, short fatigue recovery allows him
        # to regain the ability to prepare food. Don't block his only remedy.
        self.assertTrue(assess(self.world)["recovery_rest_needed"])
        relief = next(o for o in pilot.observe()["host"]["offers"]
                      if o["command"] == "rest")
        rested = pilot.act(
            turn_id="necessary-recovery-rest", intention="I need a short rest.",
            offer_id=relief["offer_id"], event_id="rest-to-recover")
        self.assertEqual(rested["status"], "committed")
        self.assertLess(self.clock.audit_state()["fatigue"], 10)
        self.do("walk", "back-to-hall", station="station:hall")
        self.assertIsNotNone(self.choice("accept_delivery", day=2))
        self.do("accept_delivery", "get-relief", day=2)
        self.do("walk", "to-kitchen", station="station:kitchen")
        self.do("open", "cupboard-for-relief", container="cupboard:kitchen")
        for i in range(3):
            self.do("drink_water", f"water-for-recovery-{i}")
        self.assertLess(self.clock.audit_state()["thirst"], 8)
        self.assertTrue(self.clock.verify()["verified"])


if __name__ == "__main__":
    unittest.main()
