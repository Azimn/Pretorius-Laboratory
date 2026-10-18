"""Scripted 3-day comparison: physical food location must constrain cooking."""
from pathlib import Path
import json
import tempfile

from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.subject_port import SubjectPort
from pretorius_lab.physics import Conflict


def new_world(path, *, physical):
    world = SpatialHabitat.create(path)
    HomeLife(world).initialize()
    daily = DailyRhythm(world)
    daily.initialize(perishable_meals=True, physical_provisions=physical)
    subject = SubjectPort(world)
    subject.act("walk", event_id="initial-hall", station="station:hall")
    subject.act("walk", event_id="initial-kitchen", station="station:kitchen")
    return daily, subject


def displace(subject):
    subject.act("take", event_id="bread-pick", item="food:bread")
    subject.act("walk", event_id="out-hall", station="station:hall")
    subject.act("walk", event_id="out-parlor", station="station:parlor")
    subject.act("open", event_id="open-writing-desk", container="desk:parlor")
    subject.act("put", event_id="bread-away", item="food:bread", container="desk:parlor")
    subject.act("walk", event_id="return-hall", station="station:hall")
    subject.act("walk", event_id="return-kitchen", station="station:kitchen")


def restore(subject):
    subject.act("walk", event_id="fetch-hall", station="station:hall")
    subject.act("walk", event_id="fetch-parlor", station="station:parlor")
    subject.act("take", event_id="fetch-bread", item="food:bread")
    subject.act("walk", event_id="fetch-hall-back", station="station:hall")
    subject.act("walk", event_id="fetch-kitchen", station="station:kitchen")
    subject.act("put", event_id="bread-restocked", item="food:bread",
                container="table:kitchen")


def prepare_after_two_days(daily, subject):
    for n in range(12):
        daily.advance(240, event_id=f"two-days-{n}")
    subject.act("walk", event_id="sleep-hall", station="station:hall")
    subject.act("walk", event_id="sleep-bedroom", station="station:bedroom")
    subject.act("sleep", event_id="recover-body")
    subject.act("walk", event_id="wake-hall", station="station:hall")
    subject.act("walk", event_id="wake-kitchen", station="station:kitchen")
    subject.act("clean", event_id="wash-kitchen")


def compare():
    with tempfile.TemporaryDirectory() as path:
        control, ordinary = new_world(Path(path)/"old.sqlite3", physical=False)
        candidate, bounded = new_world(Path(path)/"new.sqlite3", physical=True)
        displace(ordinary)
        displace(bounded)
        for daily, subject in ((control, ordinary), (candidate, bounded)):
            prepare_after_two_days(daily, subject)
        before_v2, before_v3 = control.audit_state(), candidate.audit_state()
        assert before_v2["minute"] == before_v3["minute"], "time mismatch"
        assert before_v2["supplies"] == before_v3["supplies"], "supply mismatch"
        original = ordinary.act("prepare_meal", event_id="old-impossible-food")
        blocked = False
        try:
            bounded.act("prepare_meal", event_id="new-physical-denial")
        except Conflict:
            blocked = True
        after_refusal = candidate.audit_state()
        restore(bounded)
        actual = bounded.act("prepare_meal", event_id="bread-physically-returned")
        after = candidate.audit_state()
        data = {
            "schema": "pretorius-physical-provision-comparison.v0.1",
            "simulated_elapsed_days_before_food_test": 2,
            "same_minutes_and_supplies_before_attempt":
                before_v2["minute"] == before_v3["minute"] and
                before_v2["supplies"] == before_v3["supplies"],
            "old_version_cooked_without_bread_in_kitchen":
                "prepare a simple meal" in original["inner"],
            "new_version_rejected_cooking_without_bread": blocked,
            "new_version_rejected_without_resource_or_time_change":
                before_v3 == after_refusal,
            "bread_return_restores_physical_cooking":
                "prepare a simple meal" in actual["inner"] and
                after["supplies"]["rations"] == before_v3["supplies"]["rations"] - 1,
            "old_world_replay_valid": control.verify()["verified"],
            "new_world_replay_valid": candidate.verify()["verified"],
            "qualifies_34_articles": False,
            "longitudinal_doctor_agency_tested": False,
            "limitation": "Physical availability of bread/tea bound to quantitative provisions; unit portions still in daily ledger, not individually modeled",
        }
        assert all(v is True for k,v in data.items() if k in (
            "same_minutes_and_supplies_before_attempt",
            "old_version_cooked_without_bread_in_kitchen",
            "new_version_rejected_cooking_without_bread",
            "new_version_rejected_without_resource_or_time_change",
            "bread_return_restores_physical_cooking",
            "old_world_replay_valid",
            "new_world_replay_valid")), data
        return data


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True))
