"""CPU local-model first-person action-choice experiment with bounded legal acts.

8 trials for each controller, two measurement-source conditions and four
objective variants. Separate child Python processes decide and score. Every
choice is executed through the existing real lab authority; no host fallback.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from pretorius_lab.doctor_admission_research import ResearchInstrumentAdmission
from pretorius_lab.doctor_legal_action_research import (
    LegalBenchActionGate, propose_from_brain,
)
from pretorius_lab.doctor_subject_frame_proposer import (
    PinnedSmolLM2, choose_from_subject_frame, MODEL_ID, MODEL_REVISION,
)
from pretorius_lab.doctor_holdout_protocol import (
    TASKS, PROTOCOL, adjudicate, grounded_rule_comparator,
)
from pretorius_lab.bench_instruments import BenchInstruments
from pretorius_lab.physics import Conflict
from run_doctor_instrument_pilot import create_arm, neural_config

CONTROLLERS = ("subject_frame_local_model", "fixed_neural_mapping",
               "task_aware_non_neural")


def arm_path(root, control, task, condition):
    return root / control / task["id"] / condition


def load(root, control, task, condition):
    location = arm_path(root, control, task, condition)
    bridge = ResearchInstrumentAdmission(
        location / "world.sqlite3", location / "brain",
        neural_config=neural_config())
    return location, bridge, LegalBenchActionGate(bridge.habitat)


def build(root):
    if root.exists() and any(root.iterdir()):
        raise RuntimeError("Research run directory is not empty; refusing overwrite")
    root.mkdir(parents=True, exist_ok=True)
    for control in CONTROLLERS:
        for task in TASKS:
            for condition in ("observed", "withheld"):
                create_arm(root / control / task["id"], condition)
    subprocess.run([sys.executable, __file__, "--output", str(root), "--choose"],
                   check=True)
    subprocess.run([sys.executable, __file__, "--output", str(root), "--score"],
                   check=True)


def choose(root):
    decoder = PinnedSmolLM2()
    for control in CONTROLLERS:
        for task in TASKS:
            for condition in ("observed", "withheld"):
                loc, bridge, gate = load(root, control, task, condition)
                bridge.verify()
                offer = gate.offer()
                if "weigh" not in offer.choices:
                    raise Conflict("Lab beaker not on measurement bench")
                if control == "subject_frame_local_model":
                    proposal = choose_from_subject_frame(
                        bridge.brain, offer, task["goal"], decoder)
                elif control == "fixed_neural_mapping":
                    # Baseline deliberately remains unchanged from Gate 2 and
                    # does NOT retrieve the new goal when mapping tendency.
                    proposal = propose_from_brain(bridge.brain, offer)
                else:
                    from pretorius_lab.doctor_subject_frame_proposer import authorized_prompt
                    # Identical protected experience, but a transparent
                    # task-specific non-neural decision algorithm.
                    authorized_prompt(bridge.brain, offer, task["goal"])
                    frame = bridge.brain.render_request(
                        user_input=task["goal"])["subject_frame"]
                    choice = grounded_rule_comparator(
                        tuple(frame), offer.choices)
                    proposal = {"policy": "transparent-task-aware-rule",
                                "choice": choice}
                before = bridge.instruments.verify()["revision"]
                receipt = gate.execute(
                    proposal["choice"],
                    event_id=f"heldout-{control}-{task['id']}-{condition}")
                # Do not give success credit for policy's claim. The lab
                # must independently attest to an accepted physical event.
                bridge.instruments.verify()
                after = bridge.instruments.verify()["revision"]
                bridge.brain.save()
                (loc / "choice.json").write_text(
                    json.dumps({"protocol": PROTOCOL, "controller": control,
                                "task_id": task["id"], "condition": condition,
                                "proposal": proposal, "receipt": receipt,
                                "before": before, "after": after},
                               indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def score(root):
    result = {
        "protocol": PROTOCOL,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "first_person_only": True,
        "predeclared_goals": [t["id"] for t in TASKS],
        "warnings": [
            "Only 4 benchmark goals x 2 exposure conditions; not a powered effect estimate",
            "The local model is a renderer candidate, not Pretorius's recurrent substrate",
            "Non-neural task-aware rule was authored for the public benchmark goals",
            "Old fixed neural mapping is goal blind and was not tuned",
            "Goal and initial host measurement are set up by a scripted experimenter",
        ],
        "trials": {},
        "summary": {},
    }
    for control in CONTROLLERS:
        result["trials"][control] = {}
        successes = 0
        for task in TASKS:
            result["trials"][control][task["id"]] = {}
            for condition in ("observed", "withheld"):
                loc, bridge, gate = load(root, control, task, condition)
                bridge.verify()
                e = json.loads((loc / "choice.json").read_text(encoding="utf-8"))
                if (e["protocol"], e["controller"], e["condition"], e["task_id"]) != (
                        PROTOCOL, control, condition, task["id"]):
                    raise Conflict("Research outcomes have modified trial identity")
                receipt = e["receipt"]
                if receipt["accepted"]:
                    target = ("instrument_events" if receipt["choice"] == "weigh"
                              else "embodied_events")
                    with bridge.habitat._open() as db:
                        row = db.execute(
                            f"SELECT envelope,event_hash FROM {target} WHERE event_id=?",
                            (receipt["host_event_id"],)).fetchone()
                    if row is None or row[1] != receipt["host_event_hash"]:
                        raise Conflict("Unverified physical action credited")
                    event = json.loads(row[0])
                    if receipt["choice"] == "weigh" and (
                            event["instrument"], event["object_id"],
                            event["quantity"]) != (
                            "balance:bench", "beaker:001", "mass_g"):
                        raise Conflict("Wrong instrument event offered as success")
                    if receipt["choice"] == "leave" and (
                            event["kind"], event["after_station"]) != (
                            "move", "station:center"):
                        raise Conflict("Wrong movement offered as leaving")
                    if receipt["choice"] == "inspect" and event["kind"] != "look":
                        raise Conflict("Wrong event offered as inspection")
                if bridge.instruments.verify()["revision"] != e["after"]:
                    raise Conflict("Unreplayable measurement history")
                scored = adjudicate(task, condition, receipt, before=e["before"],
                                     after=e["after"])
                successes += int(scored["success"])
                result["trials"][control][task["id"]][condition] = {
                    **scored, "model_output": e["proposal"].get("model_raw_output"),
                    "invalid_model_output": e["proposal"].get("invalid_output"),
                }
        result["summary"][control] = {
            "correct": successes, "opportunities": len(TASKS) * 2,
            "by_goal": {
                task["id"]: sum(int(
                    result["trials"][control][task["id"]][condition]["success"])
                    for condition in ("observed", "withheld"))
                for task in TASKS
            },
        }
    (root / "score.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    steps = parser.add_mutually_exclusive_group()
    steps.add_argument("--choose", action="store_true")
    steps.add_argument("--score", action="store_true")
    args = parser.parse_args()
    root = args.output.resolve()
    if args.choose:
        choose(root)
    elif args.score:
        score(root)
    else:
        build(root)


if __name__ == "__main__":
    main()
