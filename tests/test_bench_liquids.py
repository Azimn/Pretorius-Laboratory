"""Model-independent water conservation, mass readings and physical provenance."""
import copy
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pretorius_lab import Conflict, LabError
from pretorius_lab.bench_liquids import BenchLiquids
from pretorius_lab.bench_instruments import BenchInstruments
from pretorius_lab.book_custody import BookCustody
from pretorius_lab.embodied_access import EmbodiedAccess
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.physical_affordances import PhysicalAffordances, BASE_PROFILE


class WaterTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.world = SpatialHabitat.create(self.root / "world.sqlite3")
        self.actor = EmbodiedAccess(self.world)
        self.actor.initialize()
        self.custody = BookCustody(self.world)
        self.custody.initialize()
        self.physical = PhysicalAffordances(self.world)
        self.physical.initialize()
        self.scale = BenchInstruments(self.world)
        self.scale.initialize()
        self.water = BenchLiquids(self.world)
        self.water.initialize()

    def bench(self):
        self.actor.move("station:center")
        self.actor.move("station:bench")

    def cursors(self):
        return (self.world.verify()["revision"], self.actor.verify()["revision"],
                self.custody.verify()["revision"], self.scale.verify()["revision"],
                self.water.verify()["revision"])

    def test_fill_pour_conserve_water_and_change_actual_balance_readings(self):
        self.bench()
        first = self.actor.measure("balance:bench", "beaker:001", "mass_g")
        self.assertEqual(first["observation"]["value"], 325)
        self.actor.liquid("fill", 100)
        second = self.actor.measure("balance:bench", "beaker:001", "mass_g")
        self.assertEqual(second["observation"]["value"], 425)
        self.assertEqual(second["observation"]["interval"], [412,438])
        self.assertEqual(self.actor.look()["offered_payload"]["beaker_water_level"],
                         "about half full")
        self.actor.liquid("pour", 100)
        last = self.actor.measure("balance:bench", "beaker:001", "mass_g")
        self.assertEqual(last["observation"]["value"], 325)
        self.assertEqual(self.water.audit_engineer_only(),
                         {"reservoir_ml": 900, "beaker_ml": 0, "basin_ml": 100})
        self.assertEqual(self.scale.verify()["revision"], 3)
        self.assertTrue(self.water.verify()["verified"])

    def test_no_distant_fill_or_handheld_fill_and_no_hidden_exposure(self):
        self.assertNotIn("fill", self.actor.look()["offered_payload"]["available_liquid_actions"])
        with self.assertRaises(LabError):
            self.actor.liquid("fill", 100)
        self.bench()
        scene = self.actor.look()["offered_payload"]
        self.assertIn("fill", scene["available_liquid_actions"])
        self.assertNotIn("reservoir_ml", str(scene))
        self.assertNotIn("beaker_ml", str(scene))
        self.actor.take_apparatus("beaker:001")
        with self.assertRaises(LabError):
            self.actor.liquid("fill", 100)
        self.assertFalse(self.actor.look()["offered_payload"]["available_liquid_actions"])
        self.assertEqual(self.water.verify()["revision"], 0)

    def test_finite_reservoir_capacity_and_bad_commands_never_mutate_state(self):
        self.bench()
        for amount in (0, -25, 26, 251, True, 1.5):
            with self.subTest(amount=amount), self.assertRaises(LabError):
                self.actor.liquid("fill", amount)
        with self.assertRaises(LabError):
            self.actor.liquid("pour", 25)
        self.actor.liquid("fill", 250)
        before = self.cursors()
        with self.assertRaises(LabError):
            self.actor.liquid("fill", 25)
        self.assertEqual(self.cursors(), before)
        for _ in range(3):
            self.actor.liquid("pour", 250)
            self.actor.liquid("fill", 250)
        self.actor.liquid("pour", 250)
        self.assertEqual(self.water.audit_engineer_only(),
                         {"reservoir_ml": 0, "beaker_ml": 0, "basin_ml": 1000})
        before = self.cursors()
        with self.assertRaises(LabError):
            self.actor.liquid("fill", 25)
        with self.assertRaises(LabError):
            self.actor.liquid("pour", 25)
        self.assertEqual(self.cursors(), before)

    def test_idempotent_transfer_receipt_and_event_id_conflict(self):
        self.bench()
        original = self.actor.liquid("fill", 75, event_id="fill-once")
        again = self.actor.liquid("fill", 75, event_id="fill-once")
        self.assertEqual(original, again)
        self.assertEqual(self.water.verify()["revision"], 1)
        for op, amount in (("fill", 50), ("pour", 75)):
            with self.assertRaises(Conflict):
                self.actor.liquid(op, amount, event_id="fill-once")
        self.assertEqual(self.water.audit_engineer_only()["beaker_ml"], 75)

    def test_full_beaker_cannot_break_and_held_beaker_keeps_water(self):
        self.bench()
        self.actor.liquid("fill", 125)
        initial = self.world.verify()["revision"]
        with self.assertRaisesRegex(LabError, "Decant"):
            self.world.commit({"op": "break", "object_id": "beaker:001"})
        self.assertEqual(self.world.verify()["revision"], initial)
        self.actor.take_apparatus("beaker:001")
        self.assertEqual(self.actor.look()["offered_payload"]["beaker_water_level"],
                         "about half full")
        self.actor.move("station:center")
        self.actor.move("station:corner:se")
        self.actor.put_apparatus("beaker:001", "floor:corner:se")
        self.assertEqual(self.water.audit_engineer_only()["beaker_ml"], 125)
        self.assertTrue(self.custody.verify()["verified"])
        self.assertTrue(self.physical.verify()["verified"])

    def test_filled_beaker_requires_live_mass_capacity_to_pick_up(self):
        different = SpatialHabitat.create(self.root / "low-capacity.sqlite3")
        actor = EmbodiedAccess(different)
        actor.initialize()
        BookCustody(different).initialize()
        p = copy.deepcopy(BASE_PROFILE)
        p["actor_limits"]["max_carry_mass_g"] = 400
        PhysicalAffordances(different).initialize(profile=p)
        BenchLiquids(different).initialize()
        actor.move("station:center")
        actor.move("station:bench")
        actor.liquid("fill", 100)
        with self.assertRaisesRegex(LabError, "carrying capacity"):
            actor.take_apparatus("beaker:001")
        self.assertEqual(BookCustody(different).verify()["revision"], 0)

    def test_backup_and_fork_inherit_inventory_but_not_parent_sensory_events(self):
        self.bench()
        self.actor.liquid("fill", 100)
        self.actor.measure("balance:bench", "beaker:001", "mass_g")
        backup_path = self.root / "backup.sqlite3"
        self.world.backup_to(backup_path)
        restored = SpatialHabitat(backup_path)
        self.assertEqual(BenchLiquids(restored).audit_engineer_only()["beaker_ml"], 100)
        self.assertEqual(BenchInstruments(restored).verify()["revision"], 1)
        fork_path = self.root / "fork.sqlite3"
        self.world.fork_to(fork_path)
        fork = SpatialHabitat(fork_path)
        fork_liquid = BenchLiquids(fork)
        self.assertEqual(fork_liquid.audit_engineer_only(),
                         {"reservoir_ml": 900, "beaker_ml": 100, "basin_ml": 0})
        self.assertEqual(fork_liquid.verify()["revision"], 0)
        self.assertEqual(BenchInstruments(fork).verify()["revision"], 0)
        fork_actor = EmbodiedAccess(fork)
        new_measure = fork_actor.measure("balance:bench", "beaker:001", "mass_g")
        self.assertEqual(new_measure["observation"]["value"], 425)
        fork_actor.liquid("pour", 100)
        self.assertEqual(fork_liquid.audit_engineer_only()["beaker_ml"], 0)
        self.assertEqual(self.water.audit_engineer_only()["beaker_ml"], 100)
        self.assertNotEqual(fork.verify()["world_epoch"], self.world.verify()["world_epoch"])

    def test_corrupted_liquid_history_fails_backup_and_instrument_verification(self):
        self.bench()
        self.actor.liquid("fill", 100)
        self.actor.measure("balance:bench", "beaker:001", "mass_g")
        with sqlite3.connect(self.world.path) as db:
            db.execute("UPDATE liquid_events SET event_hash=? WHERE revision=1",
                       ("f" * 64,))
        with self.assertRaises(Conflict):
            self.water.verify()
        with self.assertRaises(Conflict):
            self.scale.verify()
        with self.assertRaises(Conflict):
            self.world.backup_to(self.root / "bad.sqlite3")

    def test_historical_scale_readings_survive_state_change_and_book_moves(self):
        self.bench()
        dry = self.actor.measure("balance:bench", "beaker:001", "mass_g")
        self.actor.liquid("fill", 125)
        wet = self.actor.measure("balance:bench", "beaker:001", "mass_g")
        self.assertNotEqual(dry["observation"]["value"], wet["observation"]["value"])
        self.actor.liquid("pour", 125)
        self.actor.take_apparatus("beaker:001")
        self.actor.move("station:center")
        self.actor.move("station:corner:se")
        self.actor.put_apparatus("beaker:001", "floor:corner:se")
        self.assertEqual(self.scale.verify()["revision"], 2)
        self.assertEqual(BenchInstruments(SpatialHabitat(self.world.path)).verify()["revision"], 2)


if __name__ == "__main__":
    unittest.main()
