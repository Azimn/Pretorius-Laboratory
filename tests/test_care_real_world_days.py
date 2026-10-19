"""Multi-day real-world receipts: a *host-controlled* care reference itinerary.

Unlike the 30-day pure reducer envelope this replays actual SQLite actor,
home, rhythm, project and botanical provenance. This still is NOT Pretorius
spontaneously choosing an itinerary; it is a realistic operator/reference
control for checking available physical paths and object permanence.
"""
import sqlite3
import tempfile
from pathlib import Path
import unittest

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.home_arrangement import HomeArrangements
from pretorius_lab.material_objects import MaterialObjects
from pretorius_lab.personal_projects import PersonalProjects
from pretorius_lab.care_contract import HouseholdCareContract
from pretorius_lab.unified_home_actions import UnifiedHomeActions


class FourDayRealCareWorldTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "lived.sqlite3"
        self.world = SpatialHabitat.create(self.db)
        HomeLife(self.world).initialize()
        DailyRhythm(self.world).initialize(
            perishable_meals=True, physical_provisions=True,
            visible_portions=True, physical_paper=True)
        HomeArrangements(self.world).initialize()
        MaterialObjects(self.world).initialize()
        PersonalProjects(self.world).initialize()
        HouseholdCareContract(self.world).initialize()
        self.clock = DailyRhythm(self.world)
        self.actions = UnifiedHomeActions(self.world)
        self.seq = 0

    def do(self, command, **args):
        offered = next(
            (o for o in self.actions.discover()["offers"]
             if o["command"] == command and o["args"] == args), None)
        self.assertIsNotNone(offered, (command, args))
        self.seq += 1
        actual = self.actions.execute(
            offered["offer_id"], event_id=f"care-week-{self.seq:04d}")
        self.assertEqual(actual["status"], "committed")
        self.assertEqual(len(actual["source_event_hash"]), 64)
        return actual

    def jump(self, station):
        self.do("walk", station=station)

    def water_until(self, target=2):
        while self.clock.audit_state()["thirst"] > target:
            if self.clock.audit_state()["supplies"]["water"] == 0:
                self.do("draw_water")
            self.do("drink_water")

    def advance_until(self, day, local_minute):
        end = day * 1440 + local_minute
        while end - self.clock.audit_state()["minute"] >= 10:
            delta = end - self.clock.audit_state()["minute"]
            step = min(240, (delta // 10) * 10)
            self.seq += 1
            self.clock.advance(step, event_id=f"care-clock-{self.seq:04d}")

    def meal(self, *, when_hunger=3):
        state = self.clock.audit_state()
        if state["hunger"] < when_hunger:
            return
        if state["cleanliness"]["room:kitchen"] >= 3:
            self.do("clean")
        if state["fatigue"] >= 9:
            self.jump("station:hall")
            self.jump("station:bedroom")
            self.do("rest")
            self.jump("station:hall")
            self.jump("station:kitchen")
        if self.clock.audit_state()["supplies"]["water"] == 0:
            self.do("draw_water")
        self.do("prepare_meal")
        self.do("eat")

    def test_four_real_days_with_one_missed_supplier_and_restart(self):
        # The initial kitchen cupboard is physically closed.
        self.jump("station:hall")
        self.jump("station:kitchen")
        self.do("open", container="cupboard:kitchen")
        # Water is drawn deliberately from a real fitted service. It is not
        # auto-fed by the source clock or a host provisioning callback.
        self.do("draw_water")

        for day in range(4):
            if day > 0:
                # Earlier night ended in an actual real bedroom.
                self.jump("station:hall")
                if day != 2:  # deliberately miss a town delivery
                    packet = self.do("accept_delivery", day=day)
                    self.assertIn("ordinary household delivery", packet["subject"]["inner"])
                self.jump("station:kitchen")

            self.assertEqual(self.clock.audit_state()["minute"] // 1440, day)
            if self.clock.audit_state()["supplies"]["water"] <= 2:
                self.do("draw_water")
            self.water_until()
            self.meal()
            # Follow actual local clock time rather than accumulating
            # extra hours from cooking, walking and hygiene each day.
            self.advance_until(day, 14 * 60)
            self.water_until()
            self.meal(when_hunger=2)
            self.advance_until(day, 19 * 60)
            self.water_until()
            self.advance_until(day, 23 * 60)
            # Separate evening hydration before bed. It consumes actual water,
            # unlike a magic nightly "needs reset" event.
            self.water_until()
            self.jump("station:hall")
            self.jump("station:bedroom")
            self.do("sleep")

        # A process restart must see the *same* physical world and receipt
        # history, including a missed delivery, not a reconstructed scene.
        replay = SpatialHabitat(self.db)
        reopened = DailyRhythm(replay)
        self.assertTrue(reopened.verify()["verified"])
        self.assertTrue(MaterialObjects(replay).verify()["verified"])
        self.assertTrue(HomeArrangements(replay).verify()["verified"])
        self.assertTrue(PersonalProjects(replay).verify()["verified"])
        self.assertTrue(HouseholdCareContract(replay).verify()["verified"])
        st = reopened.audit_state()
        self.assertGreaterEqual(st["minute"], 4 * 1440)
        self.assertLess(st["hunger"], 10)
        self.assertLess(st["thirst"], 10)
        self.assertGreater(st["supplies"]["rations"], 0)
        with sqlite3.connect(self.db) as connection:
            records = connection.execute(
                "SELECT envelope FROM rhythm_events ORDER BY revision").fetchall()
        import json
        deliveries = [json.loads(r[0])["args"]["day"] for r in records
                      if json.loads(r[0])["op"] == "accept_delivery"]
        self.assertEqual(deliveries, [1, 3])
        self.assertGreater(sum('"op":"drink_water"' in r[0] for r in records), 0)
        self.assertGreater(sum('"op":"prepare_meal"' in r[0] for r in records), 0)
        self.assertGreater(sum('"op":"draw_water"' in r[0] for r in records), 0)


if __name__ == "__main__":
    unittest.main()
