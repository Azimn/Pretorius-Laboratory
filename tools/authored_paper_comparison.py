"""Two-day source-backed household permanence experiment.

Both worlds share initial room/objects, time, the same written content attempt,
body movements and sleep. Only v5 can physically mark/revisit paper.
"""
from pathlib import Path
import tempfile
import json

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.subject_port import SubjectPort
from pretorius_lab.physics import LabError

WORDS = "The desk is a familiar place. I should return to this book."


def prepare(path: Path, *, paper: bool):
    world = SpatialHabitat.create(path)
    HomeLife(world).initialize()
    rhythm = DailyRhythm(world)
    rhythm.initialize(perishable_meals=True, physical_provisions=True,
                      visible_portions=True, physical_paper=paper)
    subject = SubjectPort(world)
    subject.act("walk", event_id="hall", station="station:hall")
    subject.act("walk", event_id="parlor", station="station:parlor")
    subject.act("open", event_id="open-desk", container="desk:parlor")
    return rhythm, subject


def advance_two_days(life, subject):
    for n in range(12):
        life.advance(240, event_id=f"time-{n}")
    subject.act("walk", event_id="rest-hall", station="station:hall")
    subject.act("walk", event_id="rest-bedroom", station="station:bedroom")
    subject.act("sleep", event_id="sleep")
    subject.act("walk", event_id="wake-hall", station="station:hall")
    subject.act("walk", event_id="wake-parlor", station="station:parlor")


def compare():
    with tempfile.TemporaryDirectory() as folder:
        old, old_subject = prepare(Path(folder)/"control.sqlite3", paper=False)
        new, new_subject = prepare(Path(folder)/"candidate.sqlite3", paper=True)
        old_error = False
        try:
            old_subject.act("write_paper", event_id="write", text=WORDS)
        except LabError:
            old_error = True
        new_subject.act("write_paper", event_id="write", text=WORDS)
        # Isolate the simulation time passage from affordance existence.
        # v5 writing truly costs 5 minutes; v4 control receives the same
        # elapsed time from the existing trusted physical clock.
        old.act("tick", event_id="matched-writing-time", minutes=5)
        assert old.audit_state()["minute"] == new.audit_state()["minute"]
        advance_two_days(old, old_subject)
        advance_two_days(new, new_subject)
        old_before = old.audit_state()
        new_before = new.audit_state()
        assert old_before["minute"] == new_before["minute"]
        absent = False
        try:
            old_subject.act("read_paper", event_id="read", page=1)
        except LabError:
            absent = True
        recovered = new_subject.act("read_paper", event_id="read", page=1)["inner"]
        parent_unmodified = new.audit_state()["paper_marks"] == [WORDS]
        data = {
            "schema": "pretorius-authored-material-permanence-v0.1",
            "identical_elapsed_minutes_before_retrieval": old_before["minute"] == new_before["minute"],
            "control_write_unavailable": old_error,
            "control_read_unavailable": absent,
            "candidate_exact_words_retrieved_after_two_days": WORDS in recovered,
            "subject_owned_words_source_verifiable": parent_unmodified,
            "candidate_only_writing_time_cost_minutes": 5,
            "original_v4_replay_valid": old.verify()["verified"],
            "candidate_v5_replay_valid": new.verify()["verified"],
            "autonomous_doctor_tested": False,
            "generalized_unlimited_actions_supported": False,
            "consciousness_or_emotional_attachment_claimed": False,
            "limits": "40 bounded sheet entries; writing ink not depleted; no autonomous Doctor renderer; physical paper is one existing movable item",
        }
        assert all(data[k] for k in (
            "identical_elapsed_minutes_before_retrieval",
            "control_write_unavailable",
            "control_read_unavailable",
            "candidate_exact_words_retrieved_after_two_days",
            "subject_owned_words_source_verifiable",
            "original_v4_replay_valid",
            "candidate_v5_replay_valid")), data
        return data


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True))
