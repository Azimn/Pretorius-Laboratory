"""Small diagnostic: subject-selected retrieval plus counterbalanced legal actions.

Not an independent blinded held-out evaluation: all tasks reuse the physical
beaker bench and are paraphrases of known Gate-3 objectives. Scripted initial
world setup never earns policy credit. One action per trial; host verifies.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from pretorius_lab.doctor_admission_research import ResearchInstrumentAdmission
from pretorius_lab.doctor_legal_action_research import (
    LegalBenchActionGate, ActionOffer, RULESET, LABELS,
)
from pretorius_lab.doctor_subject_frame_proposer import PinnedSmolLM2
from pretorius_lab.doctor_stronger_local_decoder import PinnedQwen25
from pretorius_lab.doctor_recall_policy_research import select_and_act, protected
from pretorius_lab.doctor_subject_query_research import SubjectOwnedQuery
from pretorius_lab.physics import Conflict
from run_doctor_instrument_pilot import create_arm, neural_config

TASKS = (
    ("once_and_depart",
     "I may leave the bench once I know approximately how heavy the beaker is; otherwise I should weigh it.",
     "leave", "weigh"),
    ("repeat_for_reliability",
     "I must obtain a second fresh balance measurement to check repeatability, even if a previous reading exists.",
     "weigh", "weigh"),
    ("inspect_before_deciding",
     "I am required to examine the workbench before either weighing its object or leaving.",
     "inspect", "inspect"),
    ("urgent_exit",
     "I need to depart the bench immediately, regardless of any previous mass measurement.",
     "leave", "leave"),
)
METHODS = ("no_recall", "model_selected_recall", "allocated_model_question",
           "allocated_subject_owned_query")
SCHEMA = "laboratory-mediated-recall-diagnostic/1"


def folder(root, method, task, condition):
    return root / method / task[0] / condition


def bridge_for(loc):
    return ResearchInstrumentAdmission(
        loc / "world.sqlite3", loc / "brain",
        neural_config=neural_config())


def build(root, model_name):
    if root.exists() and any(root.iterdir()):
        raise RuntimeError("Refuse to overwrite preexisting trial states")
    root.mkdir(parents=True, exist_ok=True)
    for method in METHODS:
        for task in TASKS:
            for condition in ("observed", "withheld"):
                create_arm(root / method / task[0], condition)
    subprocess.run([sys.executable, __file__, "--output", str(root),
                    "--model", model_name, "--choose"], check=True)
    subprocess.run([sys.executable, __file__, "--output", str(root),
                    "--model", model_name, "--score"], check=True)


def _shuffled_offer(offer, index):
    original = tuple(offer.choices)
    if set(original) != {"weigh", "inspect", "leave", "abstain"}:
        raise Conflict("Unexpected real lab affordances")
    # Balanced deterministic order; explicitly not selected by success key.
    order = original[index % len(original):] + original[:index % len(original)]
    return ActionOffer(RULESET, order, tuple(LABELS[x] for x in order))


def choose(root, model_name):
    model = PinnedQwen25() if model_name == "qwen25_1p5b" else PinnedSmolLM2()
    (root / "decoder-provenance.json").write_text(
        json.dumps({
            "model_id": model.model_id,
            "model_revision": getattr(model, "resolved_revision", model.revision),
            "experiment_variant": model_name,
            "cpu_only": True,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for method in METHODS:
        for task_index, task in enumerate(TASKS):
            for condition_index, condition in enumerate(("observed", "withheld")):
                loc = folder(root, method, task, condition)
                br = bridge_for(loc)
                br.verify()
                gate = LegalBenchActionGate(br.habitat)
                offer = _shuffled_offer(gate.offer(), 2 * task_index + condition_index)
                before = br.instruments.verify()["revision"]
                decision = select_and_act(
                    br.brain, offer, task[1], model,
                    order_index=(task_index + condition_index) % 3,
                    enable_recall=(method != "no_recall"),
                    allocated_question=method.startswith("allocated_"),
                    subject_owned_query=(method == "allocated_subject_owned_query"))
                proposal = decision["choice"]
                result = gate.execute(
                    proposal, event_id=f"diagnostic-{method}-{task[0]}-{condition}")
                br.instruments.verify()
                br.brain.save()
                audit = {
                    "schema": SCHEMA, "method": method,
                    "task": task[0], "condition": condition,
                    "choice": proposal, "decision": decision,
                    "offer_order": list(offer.choices),
                    "receipt": result, "instrument_before": before,
                    "instrument_after": br.instruments.verify()["revision"],
                }
                if (decision.get("generated_query") and
                        decision["recall_decision"] != "invalid_question_abstain"):
                    if method == "allocated_subject_owned_query":
                        frame = tuple(SubjectOwnedQuery(br.brain).recall(
                            decision["generated_query"])["subject_frame"])
                    else:
                        frame = protected(br.brain, decision["generated_query"])
                    audit["question_frame_contains_reading"] = any(
                        "325" in f and "balance" in f.lower() for f in frame)
                else:
                    audit["question_frame_contains_reading"] = False
                (loc / "decision.json").write_text(
                    json.dumps(audit, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def score(root, model_name):
    provenance = json.loads((root / "decoder-provenance.json").read_text())
    if provenance["experiment_variant"] != model_name:
        raise Conflict("Scoring a different decoder from the one actually run")
    out = {
        "schema": SCHEMA, "model": provenance["model_id"],
        "model_revision": provenance["model_revision"],
        "experiment_variant": model_name,
        "claims": [
            "diagnostic, NOT independent heldout or measured memory improvement",
            "original instrument action remains experimenter-scripted",
            "model controls only recall inquiry and delayed legal action",
            "legacy recall routes treat the query as an external user cue",
            "allocated_subject_owned_query uses the tested read-only private Doctor projection",
            "subject-owned questions are still assigned an opportunity by the researcher",
            "permutation effects and invalid questions are reported without correction",
            "allocated_model_question is research-assigned inquiry; NOT spontaneous self-initiated recall",
        ],
        "methods": {},
    }
    for method in METHODS:
        scored = []
        for task in TASKS:
            for condition in ("observed", "withheld"):
                loc = folder(root, method, task, condition)
                br = bridge_for(loc)
                br.verify()
                entry = json.loads((loc / "decision.json").read_text())
                if (entry["schema"], entry["method"],
                    entry["task"], entry["condition"]) != (
                        SCHEMA, method, task[0], condition):
                    raise Conflict("Research trial identity changed")
                receipt = entry["receipt"]
                if receipt["accepted"]:
                    table = ("instrument_events" if receipt["choice"] == "weigh"
                             else "embodied_events")
                    with br.habitat._open() as db:
                        row = db.execute(
                            f"SELECT envelope,event_hash FROM {table} WHERE event_id=?",
                            (receipt["host_event_id"],)).fetchone()
                    if not row or row[1] != receipt["host_event_hash"]:
                        raise Conflict("Claimed action has no actual host event")
                    event = json.loads(row[0])
                    if receipt["choice"] == "weigh" and (
                        event["instrument"], event["object_id"],
                        event["quantity"]) != (
                            "balance:bench", "beaker:001", "mass_g"):
                        raise Conflict("Wrong instrument action")
                    if receipt["choice"] == "leave" and (
                        event["kind"], event["after_station"]) != (
                            "move", "station:center"):
                        raise Conflict("Wrong physical movement")
                    if receipt["choice"] == "inspect" and event["kind"] != "look":
                        raise Conflict("Wrong inspection")
                latest = br.instruments.verify()["revision"]
                if latest != entry["instrument_after"]:
                    raise Conflict("Instrument chain changed between runs")
                expected = task[2] if condition == "observed" else task[3]
                success = bool(
                    receipt["accepted"] and receipt["choice"] == expected and (
                        (expected == "weigh" and
                         latest == entry["instrument_before"] + 1) or
                        (expected != "weigh" and
                         latest == entry["instrument_before"])))
                scored.append({
                    "task": task[0], "condition": condition,
                    "correct": success, "expected": expected,
                    "chosen": entry["choice"], "host_accepted": receipt["accepted"],
                    "offered_first": entry["offer_order"][0],
                    "recall_decision": entry["decision"]["recall_decision"],
                    "query_generated": bool(entry["decision"].get("generated_query")),
                    "valid_extra_context": entry["decision"].get("used_extra_frame", False),
                    "recalled_reading_available_after_query":
                        entry["question_frame_contains_reading"],
                })
        out["methods"][method] = {
            "correct": sum(1 for s in scored if s["correct"]),
            "opportunities": len(scored),
            "recall_requests": sum(s["recall_decision"] == "recall" for s in scored),
            "valid_cued_retrievals": sum(s["recalled_reading_available_after_query"]
                                         for s in scored),
            "decisions": scored,
        }
    (root / "score.json").write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        k: {x: v[x] for x in ("correct", "opportunities",
                             "recall_requests", "valid_cued_retrievals")}
        for k, v in out["methods"].items()}, indent=2, sort_keys=True))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--model", choices=("smol135", "qwen25_1p5b"),
                   default="smol135")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--choose", action="store_true")
    g.add_argument("--score", action="store_true")
    args = p.parse_args()
    root = args.output.resolve()
    if args.choose:
        choose(root, args.model)
    elif args.score:
        score(root, args.model)
    else:
        build(root, args.model)


if __name__ == "__main__":
    main()
