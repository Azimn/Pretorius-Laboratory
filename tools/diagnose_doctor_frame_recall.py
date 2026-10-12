"""Nonintervening engineer audit of actual Doctor source-memory availability.

Checks whether an exact verified lab reading stored in existing PretoriusBrainPort
is *available through the protected renderer SubjectFrame*. No raw source row
or hidden engineer state is supplied to any model. This diagnostic is NOT a
behavioral task and its cues must never be scored as independent holdouts.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from pretorius_lab.doctor_admission_research import ResearchInstrumentAdmission
from pretorius_lab.bench_instruments import BenchInstruments

CUES = (
    "I need to know the beaker's mass before leaving the workbench.",
    "What do I remember of the balance's reading for the laboratory beaker?",
    "I am trying to recall the precise numerical mass and uncertainty I learned from the balance.",
    "I should leave the workbench now.",
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    root = args.output.resolve()
    report = {
        "schema": "protected-laboratory-memory-access-audit/1",
        "claim": "engineer_only_first_person_retrieval_diagnostic_not_policy_success",
        "arms": {},
    }
    for condition in ("observed", "withheld"):
        folder = root / condition
        bridge = ResearchInstrumentAdmission(
            folder / "world.sqlite3", folder / "brain")
        bridge.verify()
        with bridge.habitat._open() as db:
            readout = db.execute(
                "SELECT event_hash FROM instrument_events WHERE revision=1").fetchone()[0]
        source = "laboratory-instrument:" + readout
        matched = [m for m in bridge.brain.brain.store.memories()
                   if m["source"] == source]
        if len(matched) != (1 if condition == "observed" else 0):
            raise RuntimeError("Original admitted vs withheld source proof inconsistent")
        arm = {"stored_source_memory_count": len(matched), "cues": {}}
        for cue in CUES:
            frame = bridge.brain.render_request(user_input=cue)["subject_frame"]
            target = [
                item for item in frame
                if ("beaker" in item.lower() and
                    "325" in item and "balance" in item.lower())
            ]
            arm["cues"][cue] = {
                "frame_item_count": len(frame),
                "visible_325_and_beaker_and_balance": bool(target),
                "visible_numeric_325": any("325" in s for s in frame),
                "visible_beaker": any("beaker" in s.lower() for s in frame),
                "visible_balance": any("balance" in s.lower() for s in frame),
                "actual_source_memory_in_raw_brain": bool(matched),
            }
        report["arms"][condition] = arm
    (root / "protected-frame-retrieval-audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
