"""Causal claim separation: reducer resource envelope vs material world receipts."""
import unittest

from pretorius_lab.care_endurance import simulate
from pretorius_lab.physics import Conflict, LabError


class ThirtyDayCareEnvelopeTests(unittest.TestCase):
    def test_thirty_days_with_two_missed_packets_and_no_invisible_feeding(self):
        outcome = simulate(days=30, missed_delivery_days=(8, 9))
        self.assertEqual(outcome["days"], 30)
        self.assertEqual(outcome["missed_deliveries"], [8, 9])
        self.assertEqual(len(outcome["daily"]), 30)
        self.assertGreater(outcome["events"], 100)
        self.assertEqual(
            sum(day["courier_collected"] for day in outcome["daily"]), 27)
        self.assertTrue(all(
            day["ration_stock"] >= 0 and day["water_stock"] >= 0
            for day in outcome["daily"]))
        self.assertTrue(all(
            day["calendar_day"] == i for i, day in enumerate(outcome["daily"])))
        self.assertEqual(outcome["control"],
                         "host-scripted, *not* autonomous Doctor choice")
        self.assertIn("pure reducer only", outcome["source_authenticity"])

    def test_month_with_zero_missed_delivery_is_not_automatic_satisfaction(self):
        outcome = simulate(days=30)
        self.assertGreater(outcome["events"], 120)
        self.assertTrue(all(
            day["thirst_on_waking"] >= 0 and day["hunger_on_waking"] >= 0
            for day in outcome["daily"]))
        # A successful reference-control run is contingent on hundreds of
        # manually selected water/meal/time actions, not just the passage of time.
        self.assertGreater(outcome["events"], 30)

    def test_serious_food_interruption_is_detected_not_covered_by_fake_stock(self):
        with self.assertRaises(Conflict):
            simulate(days=7, missed_delivery_days=(1, 2, 3, 4, 5, 6))

    def test_invalid_study_horizon_and_delivery_dates_are_rejected(self):
        for duration, missed in ((0, ()), (91, ()), (3, (-1,)), (3, (3,))):
            with self.assertRaises(LabError):
                simulate(days=duration, missed_delivery_days=missed)


if __name__ == "__main__":
    unittest.main()
