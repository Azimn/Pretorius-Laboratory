"""Bench instrument acceptance: local access, quantization, historical proofs."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pretorius_lab import Conflict, LabError
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.embodied_access import EmbodiedAccess
from pretorius_lab.book_custody import BookCustody
from pretorius_lab.physical_affordances import PhysicalAffordances
from pretorius_lab.bench_instruments import BenchInstruments
from pretorius_lab.shelf_annex import ShelfAnnex


class InstrumentTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.lab = SpatialHabitat.create(self.root/"house.sqlite3")
        self.actor = EmbodiedAccess(self.lab)
        self.actor.initialize()
        self.custody = BookCustody(self.lab)
        self.custody.initialize()
        PhysicalAffordances(self.lab).initialize()
        self.instrument = BenchInstruments(self.lab)
        self.instrument.initialize()

    def bench(self):
        if self.actor.verify()["station"] != "station:center":
            self.actor.move("station:center")
        self.actor.move("station:bench")

    def put_seventh_on_bench(self):
        self.lab.commit({"op":"place", "object_id":"beaker:001",
                         "anchor_id":"floor:corner:se"})
        self.actor.move("station:center")
        self.actor.move("station:shelf:3")
        self.actor.take("book:007")
        self.actor.move("station:center")
        self.actor.move("station:bench")
        self.actor.put("book:007", "bench:main/position:left")

    def test_requires_bench_and_reveals_no_engineer_calibration_at_door(self):
        doorway = self.actor.look()["offered_payload"]
        self.assertEqual(doorway["available_instruments"], [])
        self.assertNotIn("mass_g", json.dumps(doorway))
        with self.assertRaisesRegex(LabError, "workbench"):
            self.instrument.measure("balance:bench", "beaker:001", "mass_g")
        self.bench()
        nearby = self.actor.look()["offered_payload"]
        self.assertEqual(nearby["available_instruments"],
                         ["ruler:bench","balance:bench"])
        self.assertNotIn("mass_g", json.dumps(nearby))
        self.assertEqual(self.instrument.verify()["revision"], 0)

    def test_balance_reports_bounded_value_not_raw_profile(self):
        self.bench()
        result = self.instrument.measure("balance:bench", "beaker:001", "mass_g")
        self.assertEqual(result["observation"]["value"], 325)
        self.assertEqual(result["observation"]["interval"], [312,338])
        self.assertEqual(result["observation"]["resolution"], 25)
        self.assertEqual(result["observation"]["unit"], "g")
        self.assertNotIn("profile_digest", json.dumps(result))
        self.assertEqual(result["observation_class"],
                         "offered_not_attested_subject_memory")
        self.assertEqual(self.instrument.verify()["revision"], 1)

    def test_ruler_quantization_and_dimension_choice(self):
        self.put_seventh_on_bench()
        reading = self.instrument.measure("ruler:bench", "book:007", "width_mm")
        self.assertEqual(reading["observation"]["value"], 40)
        self.assertEqual(reading["observation"]["interval"], [37,43])
        self.assertEqual(self.instrument.measure(
            "ruler:bench", "book:007", "height_mm")["observation"]["value"], 255)
        with self.assertRaises(LabError):
            self.instrument.measure("ruler:bench", "book:007", "mass_g")
        with self.assertRaises(LabError):
            self.instrument.measure("balance:bench", "book:007", "width_mm")
        self.assertEqual(self.instrument.verify()["revision"], 2)

    def test_unplaced_book_and_held_book_cannot_be_weighed(self):
        self.bench()
        with self.assertRaisesRegex(LabError, "Place the object"):
            self.instrument.measure("balance:bench", "book:007", "mass_g")
        self.actor.move("station:center")
        self.actor.move("station:shelf:3")
        self.actor.take("book:007")
        self.actor.move("station:center")
        self.actor.move("station:bench")
        with self.assertRaisesRegex(LabError, "Place the object"):
            self.instrument.measure("balance:bench", "book:007", "mass_g")
        self.assertEqual(self.instrument.verify()["revision"], 0)

    def test_repeat_event_returns_historical_reading_after_object_moved(self):
        self.bench()
        before = self.instrument.measure(
            "balance:bench", "beaker:001", "mass_g", event_id="weigh-beaker")
        self.lab.commit({"op": "place", "object_id":"beaker:001",
                         "anchor_id":"floor:corner:se"})
        again = self.instrument.measure(
            "balance:bench", "beaker:001", "mass_g", event_id="weigh-beaker")
        self.assertEqual(again, before)
        with self.assertRaises(Conflict):
            self.instrument.measure("ruler:bench", "beaker:001", "height_mm",
                                    event_id="weigh-beaker")
        self.assertEqual(self.instrument.verify()["revision"], 1)

    def test_historical_reading_survives_moved_book_and_restart(self):
        self.put_seventh_on_bench()
        result = self.instrument.measure("ruler:bench", "book:007", "width_mm")
        self.actor.take("book:007")
        self.actor.move("station:center")
        self.actor.move("station:shelf:2")
        self.actor.put("book:007", "shelf:2/slot:1")
        copy = BenchInstruments(SpatialHabitat(self.lab.path))
        self.assertEqual(copy.verify()["revision"], 1)
        self.assertEqual(copy.verify()["event_cursor"], result["event_hash"])

    def test_uncalibrated_new_book_not_measureable(self):
        self.bench()
        with self.assertRaises(LabError):
            self.instrument.measure("balance:bench", "book:018", "mass_g")
        self.assertEqual(self.instrument.verify()["revision"], 0)

    def test_reject_tampered_observation_even_if_hash_recomputed(self):
        self.bench()
        self.instrument.measure("balance:bench", "beaker:001", "mass_g")
        with sqlite3.connect(self.lab.path) as db:
            row = db.execute("SELECT envelope FROM instrument_events WHERE revision=1").fetchone()
            event = json.loads(row[0])
            event["observation"]["value"] = 9000
            from pretorius_lab.physics import canonical, digest
            event["observation_digest"] = digest(event["observation"])
            db.execute("UPDATE instrument_events SET envelope=?,event_hash=? WHERE revision=1",
                       (canonical(event), digest(event)))
            db.execute("UPDATE instrument_meta SET value=? WHERE key='head_hash'",
                       (canonical(digest(event)),))
        with self.assertRaisesRegex(Conflict, "altered or manufactured"):
            self.instrument.verify()
        with self.assertRaises(Conflict):
            self.lab.backup_to(self.root/"bad.sqlite3")

    def test_backup_preserves_evidence_and_fork_does_not_fake_new_readings(self):
        self.bench()
        original = self.instrument.measure("balance:bench", "beaker:001", "mass_g")
        backup = self.root/"backup.sqlite3"
        self.lab.backup_to(backup)
        restored = BenchInstruments(SpatialHabitat(backup))
        self.assertEqual(restored.verify()["event_cursor"], original["event_hash"])
        separate = self.root/"branch.sqlite3"
        self.lab.fork_to(separate)
        child = SpatialHabitat(separate)
        child_instruments = BenchInstruments(child)
        self.assertEqual(child_instruments.verify()["revision"], 0)
        with child._open() as db:
            from pretorius_lab.bench_instruments import _meta
            lineage = _meta(db)["parent_instruments"]
        self.assertEqual(lineage["source_cursor"], original["event_hash"])
        self.assertNotEqual(child.verify()["world_epoch"],
                            self.lab.verify()["world_epoch"])
        child_instruments.measure("balance:bench", "beaker:001", "mass_g")
        self.assertEqual(self.instrument.verify()["revision"], 1)
        self.assertEqual(child_instruments.verify()["revision"], 1)

    def test_initialization_requires_mechanical_profile(self):
        other = SpatialHabitat.create(self.root/"no-mechanics.sqlite3")
        EmbodiedAccess(other).initialize()
        BookCustody(other).initialize()
        with self.assertRaises(LabError):
            BenchInstruments(other).initialize()

    def test_wrong_world_measurement_history_rejected(self):
        self.bench()
        self.instrument.measure("balance:bench", "beaker:001", "mass_g")
        with sqlite3.connect(self.lab.path) as db:
            db.execute("UPDATE instrument_meta SET value=? WHERE key='world_epoch'",
                       (json.dumps("wrong"),))
        with self.assertRaises(Conflict):
            self.instrument.verify()


if __name__ == "__main__":
    unittest.main()
