"""Paired 48-hour existing-vs-freshness world test, no invented events."""
import json
import tempfile
from pathlib import Path

from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.subject_port import SubjectPort
from pretorius_lab.physics import Conflict


def make(path, fresh):
    world = SpatialHabitat.create(path)
    HomeLife(world).initialize()
    life = DailyRhythm(world)
    life.initialize(perishable_meals=fresh)
    home = HomeLife(world)
    home.walk("station:hall", event_id="walk-hall")
    home.walk("station:kitchen", event_id="walk-kitchen")
    subject = SubjectPort(world)
    return world, life, subject


def compare():
    with tempfile.TemporaryDirectory() as tmp:
        world_a, old, old_subject = make(Path(tmp) / "control.sqlite3", False)
        world_b, fresh, fresh_subject = make(Path(tmp) / "candidate.sqlite3", True)
        old_subject.act("prepare_meal", event_id="make-meal")
        fresh_subject.act("prepare_meal", event_id="make-meal")
        for index in range(12):
            old.advance(240, event_id=f"daytime-{index}")
            fresh.advance(240, event_id=f"daytime-{index}")
        old_before, fresh_before = old.audit_state(), fresh.audit_state()
        if old_before["minute"] != fresh_before["minute"]:
            raise AssertionError("Compared worlds have different elapsed time")
        if old_before["supplies"] != fresh_before["supplies"]:
            raise AssertionError("Freshness generated or erased supplies")
        old_frame = old_subject.observe()["inner"]
        fresh_frame = fresh_subject.observe()["inner"]
        blocked = False
        try:
            fresh_subject.act("eat", event_id="stale-eat")
        except Conflict:
            blocked = True
        if fresh.audit_state() != fresh_before:
            raise AssertionError("Rejected stale eating changed real world")
        old_subject.act("eat", event_id="old-eat")
        discarded = fresh_subject.act("discard_meal", event_id="stale-discard")
        old_after, fresh_after = old.audit_state(), fresh.audit_state()
        report = {
            "schema": "pretorius-multiday-realism-paired-v0.1",
            "duration_minutes_before_intervention": 2880,
            "equal_original_supplies": old_before["supplies"] == fresh_before["supplies"],
            "equal_time_before_intervention": old_before["minute"] == fresh_before["minute"],
            "control_allowed_two_day_old_food": old_after["hunger"] < old_before["hunger"] + 1,
            "new_profile_recognized_stale_food": "must be discarded" in fresh_frame,
            "old_profile_still_describes_edible_meal": "prepared meal to eat" in old_frame,
            "new_profile_rejected_two_day_old_food": blocked,
            "denied_attempt_cost_zero_time_and_supplies": fresh_before["minute"] == (
                fresh_after["minute"] - 10) and fresh_after["supplies"] == fresh_before["supplies"],
            "discarded_provisions_have_actual_consequence": (
                not fresh_after["meal_ready"] and "provisions are wasted" in discarded["inner"]),
            "control_replay": old.verify()["verified"],
            "candidate_replay": fresh.verify()["verified"],
            "control_world_independence": world_a.path != world_b.path,
            "article_qualification": "NOT_ASSESSED",
            "human_likeness": "NOT_ASSESSED",
            "limits": "Scripted two-day fixture, no autonomous Doctor, six-hour threshold is a synthetic coarse approximation",
        }
        expected = (
            "equal_original_supplies",
            "equal_time_before_intervention",
            "control_allowed_two_day_old_food",
            "new_profile_recognized_stale_food",
            "old_profile_still_describes_edible_meal",
            "new_profile_rejected_two_day_old_food",
            "denied_attempt_cost_zero_time_and_supplies",
            "discarded_provisions_have_actual_consequence",
            "control_replay",
            "candidate_replay",
            "control_world_independence",
        )
        assert all(report[name] is True for name in expected), report
        return report


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True))
