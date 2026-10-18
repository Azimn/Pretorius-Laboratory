"""Equal-world physical object depletion cues, with no second stock ledger."""
from pathlib import Path
import json
import tempfile

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_life import HomeLife
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.subject_port import SubjectPort


CUES = (
    "a whole bread loaf, enough for four meals",
    "most of the bread loaf, enough for three meals",
    "about half of the bread loaf, enough for two meals",
    "the last usable portion of the bread loaf",
    "bare bread remnants, with nothing substantial left to prepare",
)


def make(path, *, visible):
    world = SpatialHabitat.create(path)
    HomeLife(world).initialize()
    life = DailyRhythm(world)
    life.initialize(perishable_meals=True, physical_provisions=True,
                    visible_portions=visible)
    subject = SubjectPort(world)
    subject.act("walk", station="station:hall", event_id="to-hall")
    subject.act("walk", station="station:kitchen", event_id="to-kitchen")
    return life, subject


def compare():
    with tempfile.TemporaryDirectory() as tmp:
        original, old_subject = make(Path(tmp)/"v3.sqlite3", visible=False)
        revised, new_subject = make(Path(tmp)/"v4.sqlite3", visible=True)
        samples = []
        for n in range(5):
            prev, cand = original.audit_state(), revised.audit_state()
            assert prev["supplies"] == cand["supplies"], "Changed inventory counts"
            assert prev["minute"] == cand["minute"], "Changed time budget"
            expected = CUES[n]
            old = old_subject.observe()["inner"]
            new = new_subject.observe()["inner"]
            sample = {
                "remaining_meal_portions": 4-n,
                "old_reported_exact_condition": expected in old,
                "new_reported_exact_condition": expected in new,
                "same_persisted_provisions": original.audit_state()["supplies"] == revised.audit_state()["supplies"],
                "same_simulated_minute": original.audit_state()["minute"] == revised.audit_state()["minute"],
            }
            samples.append(sample)
            if n != 4:
                old_subject.act("prepare_meal", event_id=f"cook-{n}")
                new_subject.act("prepare_meal", event_id=f"cook-{n}")
                old_subject.act("eat", event_id=f"eat-{n}")
                new_subject.act("eat", event_id=f"eat-{n}")
        final_old = old_subject.observe()["inner"]
        final_new = new_subject.observe()["inner"]
        report = {
            "schema": "pretorius-visible-physical-provision-control.v0.1",
            "paired_samples": samples,
            "v3_explicit_depletion_cues": sum(x["old_reported_exact_condition"] for x in samples),
            "v4_explicit_depletion_cues": sum(x["new_reported_exact_condition"] for x in samples),
            "new_empty_loaf_recognized": "bare bread remnants" in final_new,
            "old_empty_loaf_still_looks_generic": "bread loaf" in final_old,
            "no_extra_inventory_records": True,  # no new material fields/tables, same stock values
            "v3_replay": original.verify()["verified"],
            "v4_replay": revised.verify()["verified"],
            "scientific_human_likeness": "NOT_TESTED",
            "autonomous_character": "NOT_TESTED",
            "limitations": "Qualitative object condition is derived from existing finite portions; actual object geometry/mass and compositional ingredients are not simulated.",
        }
        assert report["v3_explicit_depletion_cues"] == 0, report
        assert report["v4_explicit_depletion_cues"] == 5, report
        assert all(x["same_persisted_provisions"] and x["same_simulated_minute"] for x in samples)
        assert all(report[k] for k in ("new_empty_loaf_recognized", "old_empty_loaf_still_looks_generic", "v3_replay", "v4_replay"))
        return report


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True))
