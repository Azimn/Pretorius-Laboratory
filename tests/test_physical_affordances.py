"""Prove synthetic mechanical size/mass/reach actually constrain accepted actions."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pretorius_lab import Conflict, LabError
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.embodied_access import EmbodiedAccess
from pretorius_lab.book_custody import BookCustody
from pretorius_lab.physical_affordances import PhysicalAffordances, BASE_PROFILE
from pretorius_lab.shelf_annex import ShelfAnnex


class MechanicalAffordanceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.habitat = SpatialHabitat.create(self.dir / "physical.sqlite3")
        self.actor = EmbodiedAccess(self.habitat)
        self.actor.initialize()
        self.custody = BookCustody(self.habitat)
        self.custody.initialize()
        self.mechanics = PhysicalAffordances(self.habitat)

    def walk(self, station):
        now = self.actor.verify()["station"]
        if now != "station:center":
            self.actor.move("station:center")
        self.actor.move(station)

    def bench_ready(self):
        self.habitat.commit({"op": "place", "object_id": "beaker:001",
                             "anchor_id": "floor:corner:se"})

    def variant(self):
        return copy.deepcopy(BASE_PROFILE)

    def test_base_profile_is_explicit_synthetic_and_accepts_seventeen_book_ids(self):
        result = self.mechanics.initialize()
        self.assertTrue(result["verified"])
        self.assertEqual(result["source_class"], "synthetic_declared_not_measured")
        self.assertEqual(len(self.mechanics.inspect_engineer_only()["object_profiles"]), 18)
        self.walk("station:shelf:3")
        taken = self.actor.take("book:007")
        self.assertEqual(taken["location"]["held_by"], "research-subject:pretorius")
        self.walk("station:shelf:2")
        self.actor.put("book:007", "shelf:2/slot:1")
        self.assertEqual(self.habitat.locate("book:007")["location"]["fixture"], "shelf:2")
        self.assertTrue(self.mechanics.verify()["verified"])
        self.assertTrue(self.custody.verify()["verified"])

    def test_heavy_book_cannot_be_lifted_but_stays_on_bench(self):
        self.bench_ready()
        self.habitat.commit({"op": "place", "object_id": "book:007",
                             "anchor_id": "bench:main/position:left"})
        profile = self.variant()
        profile["object_profiles"]["book:007"]["mass_g"] = 5000
        self.mechanics.initialize(profile=profile)
        self.walk("station:bench")
        before = self.custody.verify()["revision"]
        with self.assertRaisesRegex(LabError, "carrying capacity"):
            self.actor.take("book:007")
        self.assertEqual(self.custody.verify()["revision"], before)
        self.assertEqual(self.habitat.locate("book:007")["location"]["fixture"],
                         "bench:main")

    def test_oversize_volume_can_be_lifted_but_not_shelved(self):
        self.bench_ready()
        self.habitat.commit({"op": "place", "object_id": "book:007",
                             "anchor_id": "bench:main/position:left"})
        profile = self.variant()
        profile["object_profiles"]["book:007"]["width_mm"] = 85
        self.mechanics.initialize(profile=profile)
        self.walk("station:bench")
        self.actor.take("book:007")
        self.walk("station:shelf:3")
        prev = self.custody.verify()["revision"]
        with self.assertRaisesRegex(LabError, "surface clearance: width_mm"):
            self.actor.put("book:007", "shelf:3/slot:7")
        self.assertEqual(self.custody.verify()["revision"], prev)
        self.assertEqual(self.habitat.locate("book:007")["location"]["placement"],
                         "carried")
        self.walk("station:bench")
        self.actor.put("book:007", "bench:main/position:left")

    def test_out_of_reach_shelf_rejected_even_when_actor_at_station(self):
        profile = self.variant()
        profile["actor_limits"]["max_reach_height_mm"] = 1300
        self.mechanics.initialize(profile=profile)
        self.walk("station:shelf:3")
        before = self.custody.verify()["revision"]
        with self.assertRaisesRegex(LabError, "declared reach"):
            self.actor.take("book:007")
        self.assertEqual(self.custody.verify()["revision"], before)
        self.habitat.commit({"op": "place", "object_id": "book:007",
                             "anchor_id": "shelf:1/slot:1"})
        self.walk("station:shelf:1")
        self.actor.take("book:007")
        self.assertEqual(self.habitat.locate("book:007")["location"]["placement"],
                         "carried")

    def test_surface_load_limit_blocks_heavy_book_return(self):
        self.bench_ready()
        self.habitat.commit({"op": "place", "object_id": "book:007",
                             "anchor_id": "bench:main/position:left"})
        profile = self.variant()
        profile["object_profiles"]["book:007"]["mass_g"] = 2150
        profile["anchor_class_limits"]["shelf_slot"]["max_mass_g"] = 2000
        self.mechanics.initialize(profile=profile)
        self.walk("station:bench")
        self.actor.take("book:007")
        self.walk("station:shelf:3")
        with self.assertRaisesRegex(LabError, "supported surface mass"):
            self.actor.put("book:007", "shelf:3/slot:7")
        self.assertEqual(self.habitat.locate("book:007")["location"]["placement"],
                         "carried")

    def test_operator_relocation_also_respects_width_and_mass(self):
        self.bench_ready()
        self.habitat.commit({"op": "place", "object_id": "book:007",
                             "anchor_id": "bench:main/position:left"})
        profile = self.variant()
        profile["object_profiles"]["book:007"]["width_mm"] = 86
        self.mechanics.initialize(profile=profile)
        prev = self.custody.verify()["revision"]
        with self.assertRaisesRegex(LabError, "surface clearance"):
            self.habitat.commit({"op": "place", "object_id": "book:007",
                                 "anchor_id": "shelf:3/slot:7"})
        self.assertEqual(self.custody.verify()["revision"], prev)
        self.assertEqual(self.habitat.locate("book:007")["location"]["fixture"],
                         "bench:main")

    def test_invalid_activation_cannot_retroactively_fit_impossible_scene(self):
        profile = self.variant()
        profile["anchor_class_limits"]["shelf_slot"]["width_mm"] = 30
        with self.assertRaisesRegex(LabError, "surface clearance"):
            self.mechanics.initialize(profile=profile)
        # SQLite transaction rolled back, leaving the world opt-out and intact.
        self.assertEqual(self.habitat.locate("book:007")["location"]["fixture"],
                         "shelf:3")
        self.mechanics.initialize()
        self.assertEqual(self.custody.verify()["revision"], 0)

    def test_profile_is_epoch_immutable_and_digest_tamper_rejected(self):
        initial = self.mechanics.initialize()
        original = self.habitat.verify()
        self.assertEqual(self.mechanics.initialize()["profile_digest"],
                         initial["profile_digest"])
        edited = self.variant()
        edited["object_profiles"]["book:007"]["mass_g"] = 2000
        with self.assertRaises(Conflict):
            self.mechanics.initialize(profile=edited)
        self.assertEqual(original, self.habitat.verify())
        with sqlite3.connect(self.habitat.path) as db:
            db.execute("UPDATE affordance_meta SET value=? WHERE key='profile_digest'",
                       (json.dumps("f"*64),))
        with self.assertRaises(Conflict):
            self.mechanics.verify()
        with self.assertRaises(Conflict):
            self.habitat.backup_to(self.dir / "bad.sqlite3")

    def test_profile_denies_unknown_new_book_registration(self):
        self.mechanics.initialize()
        annex = ShelfAnnex(self.habitat)
        annex.initialize()
        annex.register("book:008", "shelf:1/slot:1", "Recognized archival volume")
        with self.assertRaisesRegex(LabError, "No authorized dimensions"):
            annex.register("book:018", "shelf:1/slot:2", "Uncalibrated volume")
        self.assertEqual(annex.verify()["count"], 1)

    def test_subject_local_look_never_leaks_calibration_or_internal_measurements(self):
        self.mechanics.initialize()
        self.walk("station:shelf:3")
        local = json.dumps(self.actor.look()["offered_payload"])
        for hidden in ("mass_g", "width_mm", "height_mm", "xyz_mm",
                       "max_carry_mass_g", "profile_digest"):
            self.assertNotIn(hidden, local)
        self.assertIn("book:007", local)

    def test_verified_backup_and_sandbox_fork_preserve_custom_profile(self):
        self.bench_ready()
        self.habitat.commit({"op": "place", "object_id": "book:007",
                             "anchor_id": "bench:main/position:left"})
        profile = self.variant()
        profile["object_profiles"]["book:007"]["width_mm"] = 91
        parent = self.mechanics.initialize(profile=profile)["profile_digest"]
        backup = self.dir / "backup.sqlite3"
        self.habitat.backup_to(backup)
        self.assertEqual(PhysicalAffordances(SpatialHabitat(backup)).verify()[
                             "profile_digest"], parent)
        fork = self.dir / "fork.sqlite3"
        self.habitat.fork_to(fork)
        clone = SpatialHabitat(fork)
        self.assertEqual(PhysicalAffordances(clone).verify()["profile_digest"], parent)
        self.assertNotEqual(clone.verify()["world_epoch"],
                            self.habitat.verify()["world_epoch"])
        self.assertEqual(clone.locate("book:007")["location"]["fixture"], "bench:main")

    def test_profile_activation_requires_existing_custody_system(self):
        orphan = SpatialHabitat.create(self.dir / "without-body.sqlite3")
        with self.assertRaisesRegex(LabError, "custody"):
            PhysicalAffordances(orphan).initialize()
        self.assertTrue(orphan.verify()["verified"])

    def test_booleans_and_unlabelled_dimensions_rejected(self):
        p = self.variant()
        p["object_profiles"]["book:007"]["mass_g"] = True
        with self.assertRaises(LabError):
            self.mechanics.initialize(profile=p)
        p2 = self.variant()
        p2["object_profiles"]["book:007"]["source_class"] = "field_measured"
        with self.assertRaises(LabError):
            self.mechanics.initialize(profile=p2)


if __name__ == "__main__":
    unittest.main()
