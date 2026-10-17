"""Causal two-world retro action-time comparison. No neural-human-likeness claim."""
from __future__ import annotations

from pathlib import Path
import json
import tempfile

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.subject_port import SubjectPort
from pretorius_lab.turn_cost import TurnCostSubjectPort


def make_world(path):
    w = SpatialHabitat.create(path)
    HomeLife(w).initialize()
    DailyRhythm(w).initialize()
    return w


def run():
    with tempfile.TemporaryDirectory() as tmp:
        old = make_world(Path(tmp) / "uncharged.sqlite3")
        new = make_world(Path(tmp) / "timed.sqlite3")
        old_subject = SubjectPort(old)
        new_subject = TurnCostSubjectPort(SubjectPort(new))
        # Real 17:50 simulation in both independently initialized worlds.
        for world in (old, new):
            life = DailyRhythm(world)
            for i, minutes in enumerate((240, 240, 170)):
                life.advance(minutes, event_id=f'advance-{i}')
        first_minutes = [DailyRhythm(world).audit_state()["minute"] for world in (old, new)]
        if first_minutes != [1070, 1070]:
            raise AssertionError("Worlds did not share the same initial time")
        for n in range(6):
            station = "station:center" if n % 2 == 0 else "station:threshold"
            old_subject.act("walk", event_id=f"step-{n}", station=station)
            new_subject.act("walk", event_id=f"step-{n}", station=station)
        old_life = DailyRhythm(old)
        new_life = DailyRhythm(new)
        old_state, new_state = old_life.audit_state(), new_life.audit_state()
        old_scene = old_subject.observe()["inner"]
        new_scene = new_subject.observe()["inner"]
        report = {
            "schema": "pretorius-retro-time-comparison.v0.1",
            "scenario": "six accepted neighboring room moves starting at 17:50",
            "control_elapsed_minutes": old_state["minute"] - 1070,
            "timed_elapsed_minutes": new_state["minute"] - 1070,
            "control_still_in_daylight": "daylight enough" in old_scene,
            "timed_night_has_arrived": "too dark" in new_scene,
            "control_world_replay_verified": old_life.verify()["verified"],
            "timed_world_replay_verified": new_life.verify()["verified"],
            "source_boundary": "first-person experience only; audit figures engineer-only",
            "does_not_establish": "human-level realism, natural autonomy, or Article qualification",
        }
        assert report["control_elapsed_minutes"] == 0
        assert report["timed_elapsed_minutes"] == 12
        assert report["control_still_in_daylight"]
        assert report["timed_night_has_arrived"]
        assert report["control_world_replay_verified"] and report["timed_world_replay_verified"]
        return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
