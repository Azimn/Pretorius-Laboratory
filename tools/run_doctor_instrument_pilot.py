"""Two-arm reproducible doctor-laboratory research pilot with a fresh-process read.

This is an ENGINEERING admission test. A fixed research controller performs
the same physical actions in both arms. The neural policy does NOT choose them.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.embodied_access import EmbodiedAccess
from pretorius_lab.book_custody import BookCustody
from pretorius_lab.physical_affordances import PhysicalAffordances
from pretorius_lab.bench_instruments import BenchInstruments
from pretorius_lab.doctor_admission_research import ResearchInstrumentAdmission


def neural_config():
    from doctor_lives.neural import DEFAULT_CONFIG
    settings = dict(DEFAULT_CONFIG)
    settings.update({"neurons": 64, "sensory_dim": 40, "avg_recurrent_degree": 6,
                     "input_degree": 3, "action_population_size": 4,
                     "seed": 1842})
    return settings


def create_arm(output, condition):
    root = output / condition
    root.mkdir(parents=True)
    world = SpatialHabitat.create(root / "world.sqlite3")
    actor = EmbodiedAccess(world)
    actor.initialize()
    BookCustody(world).initialize()
    PhysicalAffordances(world).initialize()
    BenchInstruments(world).initialize()
    # Host-driven, deliberately not selected by the neural policy.
    actor.move("station:center")
    actor.move("station:bench")
    measurement = actor.measure("balance:bench", "beaker:001", "mass_g")
    bridge = ResearchInstrumentAdmission(world.path, root / "brain",
                                         neural_config=neural_config())
    result = bridge.deliver(measurement, condition=condition)
    bridge.verify()
    brain_digest = bridge.brain.save()
    return {
        "condition": condition,
        "world_epoch": world.verify()["world_epoch"],
        "lab_measurement_hash": measurement["event_hash"],
        "host_measurements": BenchInstruments(world).verify()["revision"],
        "port_memory_id": result.get("brain_memory_id"),
        "delivery": result["admitted"],
        "brain_tick": brain_digest["tick"],
    }


def reopen_and_score(root):
    outcome = {"schema": "doctor-laboratory-admission-pilot/1",
               "claims": ["engineering continuity only",
                          "scripted experimenter movement",
                          "no autonomous tool choice",
                          "no model recall or causal memory benefit scored"],
               "arms": {}}
    for condition in ("observed", "withheld"):
        folder = root / condition
        adapter = ResearchInstrumentAdmission(
            folder / "world.sqlite3", folder / "brain")
        adapter.verify()
        subject = adapter.brain.brain.store
        instruments = BenchInstruments(adapter.habitat).verify()
        with adapter.habitat._open() as db:
            row = db.execute(
                "SELECT event_hash FROM instrument_events WHERE revision=1").fetchone()
        found = [m for m in subject.memories()
                 if m["source"] == "laboratory-instrument:" + row[0]]
        outcome["arms"][condition] = {
            "instrument_history_verified": instruments["verified"],
            "instrument_events": instruments["revision"],
            "memory_count_with_matching_verified_source": len(found),
            "source_provenance_classes": sorted({m["evidence_class"] for m in found}),
            "brain_restart_opened": bool(adapter.brain.status()["port_schema"]),
            "brain_tick": subject.tick,
            "brain_state_digest": subject.digest(),
            "world_epoch": adapter.epoch,
        }
    observed = outcome["arms"]["observed"]
    withheld = outcome["arms"]["withheld"]
    outcome["matched_source_exposure_gate"] = (
        observed["instrument_events"] == withheld["instrument_events"] == 1
        and observed["memory_count_with_matching_verified_source"] == 1
        and withheld["memory_count_with_matching_verified_source"] == 0
        and observed["source_provenance_classes"] == ["lived_runtime_memory"]
    )
    if not outcome["matched_source_exposure_gate"]:
        raise AssertionError("Physical outcome/ingress control did not survive fresh-process reopen")
    (root / "score.json").write_text(
        json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return outcome


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = args.output.resolve()
    if args.verify_only:
        print(json.dumps(reopen_and_score(root), indent=2, sort_keys=True))
        return 0
    if root.exists() and any(root.iterdir()):
        raise RuntimeError("Refuse to overwrite an existing research state")
    root.mkdir(parents=True, exist_ok=True)
    for condition in ("observed", "withheld"):
        create_arm(root, condition)
    # A separate Python interpreter opens both existing persisted brain
    # checkpoints and both SQLite physical worlds. No state reuse in memory.
    subprocess.run([
        sys.executable, __file__, "--output", str(root), "--verify-only"
    ], check=True)
    if not (root / "score.json").exists():
        raise RuntimeError("Fresh-process proof was not written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
