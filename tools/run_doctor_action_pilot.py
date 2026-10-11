"""Four-arm fresh-process test: Doctor neural policy vs stateful controller.

Original physical measurement and source admission: scripted, identical.
Delayed test: each policy proposes ONE action; the laboratory decides legality,
executes the accepted action and an independent later process scores it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from pretorius_lab.doctor_admission_research import ResearchInstrumentAdmission
from pretorius_lab.doctor_legal_action_research import (
    LegalBenchActionGate, propose_from_brain, propose_stateful_non_neural,
    assess_delayed_choice,
)
from pretorius_lab.bench_instruments import BenchInstruments
from pretorius_lab.embodied_access import EmbodiedAccess
from pretorius_lab.physics import Conflict
from run_doctor_instrument_pilot import create_arm, neural_config

RULES = "doctor-lab-delayed-policy-battery/1"
GOAL = ("Please find out the laboratory beaker's weight to the balance's "
        "accuracy before leaving this workbench, without unnecessary repetition.")


def _load(root, policy, condition):
    folder = root / policy / condition
    bridge = ResearchInstrumentAdmission(
        folder / "world.sqlite3", folder / "brain",
        neural_config=neural_config())
    gate = LegalBenchActionGate(bridge.habitat)
    return folder, bridge, gate


def source_visible_in_saved_memory(bridge) -> bool:
    """Source-bound retrieval-only baseline: never read treatment assignment.

    This is a deliberately strong non-neural DECISION controller that shares
    the same existing brain storage substrate for received observations.
    It does not inspect host mass or intervention labels.
    """
    bridge.verify()
    with bridge.habitat._open() as db:
        first = db.execute(
            "SELECT event_hash FROM instrument_events WHERE revision=1").fetchone()
    if first is None:
        raise Conflict("No original accepted measurement for retrieval")
    memory_source = "laboratory-instrument:" + first[0]
    records = [
        m for m in bridge.brain.brain.store.memories()
        if m["source"] == memory_source
    ]
    if len(records) > 1 or any(
            r["evidence_class"] != "lived_runtime_memory" or
            "325 g" not in r["text"] for r in records):
        raise Conflict("Invalid or duplicated source-identified stored observation")
    return len(records) == 1


def build(root):
    if root.exists() and any(root.iterdir()):
        raise RuntimeError("Refuse to reuse a research directory")
    root.mkdir(parents=True, exist_ok=True)
    for policy in ("doctor_policy", "stateful_non_neural"):
        for condition in ("observed", "withheld"):
            create_arm(root / policy, condition)
    # Both next-session actions and independent scoring use new interpreters.
    subprocess.run([sys.executable, __file__, "--output", str(root),
                    "--choose"], check=True)
    subprocess.run([sys.executable, __file__, "--output", str(root),
                    "--score"], check=True)


def choose(root):
    for policy in ("doctor_policy", "stateful_non_neural"):
        for condition in ("observed", "withheld"):
            folder, bridge, gate = _load(root, policy, condition)
            bridge.verify()
            offer = gate.offer()
            if "weigh" not in offer.choices:
                raise Conflict("Physical measuring action unexpectedly unavailable")
            # Same goal is offered through the existing source-safe user ingress.
            # This produces an actual neural step for both conditions.
            bridge.brain.ingest({
                "channel": "user", "actor": "Researcher", "kind": "communication",
                "text": GOAL,
                "source": "research-goal-user",
            })
            if policy == "doctor_policy":
                proposal = propose_from_brain(bridge.brain, offer)
            else:
                # Comparator consults its own source-matched persisted
                # measurement memory. It is NEVER passed the condition label.
                proposal = propose_stateful_non_neural(
                    observed=source_visible_in_saved_memory(bridge),
                    offer=offer)
            events_before = bridge.instruments.verify()["revision"]
            receipt = gate.execute(
                proposal["choice"],
                event_id=f"delayed-policy-{policy}-{condition}")
            # Recheck the world and source events after host action.
            bridge.instruments.verify()
            EmbodiedAccess(bridge.habitat).verify()
            events_after = bridge.instruments.verify()["revision"]
            # The physical outcome is admitted only if the actual host
            # measurement event exists and passes verification.
            if receipt["accepted"] and receipt["choice"] == "weigh":
                with bridge.habitat._open() as db:
                    event = db.execute(
                        "SELECT envelope,event_hash FROM instrument_events WHERE event_id=?",
                        (receipt["host_event_id"],)).fetchone()
                    data = json.loads(event[0])
                    from pretorius_lab.bench_instruments import BenchInstruments
                    measured = BenchInstruments._result(data, event[1])
                bridge.deliver(measured, condition="observed")
            elif receipt["accepted"]:
                # Verify the exact accepted movement/look event before
                # providing natural first-person outcome through ingress.
                with bridge.habitat._open() as db:
                    event = db.execute(
                        "SELECT envelope,event_hash FROM embodied_events WHERE event_id=?",
                        (receipt["host_event_id"],)).fetchone()
                if event is None or event[1] != receipt["host_event_hash"]:
                    raise Conflict("Claimed physical action has no source event")
                data = json.loads(event[0])
                if data["kind"] != ("move" if receipt["choice"] == "leave" else "look"):
                    raise Conflict("Mismatched physical operation")
                percept = (
                    "I have left the workbench and returned toward the middle of the laboratory."
                    if receipt["choice"] == "leave"
                    else "I look over my workbench and notice the beaker resting there.")
                bridge.brain.ingest({
                    "channel": "world", "percept": percept,
                    "source": "laboratory-action:" + receipt["host_event_hash"],
                    "kind": "observation",
                })
            bridge.brain.save()
            bridge.verify()
            (folder / "delayed_choice.json").write_text(
                json.dumps({
                    "schema": RULES, "policy": policy,
                    "source_exposure": condition, "goal": GOAL,
                    "offer": {"choices": list(offer.choices),
                              "subject_native_options": list(offer.subject_native_options)},
                    "proposal": proposal, "host_receipt": receipt,
                    "instrument_events_before": events_before,
                    "instrument_events_after": events_after,
                }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def score(root):
    outcomes = {
        "schema": RULES,
        "goal": GOAL,
        "interpretation": [
            "true production Pretorius abstract policy tendencies",
            "fixed non-learned action-label mapping (not generative choice)",
            "scripted earlier physical measurement, policy-selected delayed action",
            "objective host effects separately verified",
            "one action per arm, not evidence of generalizable efficacy",
        ],
        "arms": {},
    }
    for policy in ("doctor_policy", "stateful_non_neural"):
        outcomes["arms"][policy] = {}
        for condition in ("observed", "withheld"):
            folder, bridge, gate = _load(root, policy, condition)
            bridge.verify()
            history = json.loads((folder / "delayed_choice.json").read_text())
            if (history["policy"], history["source_exposure"], history["schema"]) != (
                    policy, condition, RULES):
                raise Conflict("Trial labels were changed")
            proposal, receipt = history["proposal"], history["host_receipt"]
            if receipt["accepted"]:
                table = ("instrument_events" if receipt["choice"] == "weigh"
                         else "embodied_events")
                with bridge.habitat._open() as db:
                    actual = db.execute(
                        f"SELECT envelope,event_hash FROM {table} WHERE event_id=?",
                        (receipt["host_event_id"],)).fetchone()
                    if actual is None or actual[1] != receipt["host_event_hash"]:
                        raise Conflict("Scored action did not occur in the real lab")
                    event = json.loads(actual[0])
                    if receipt["choice"] == "weigh":
                        if (event["instrument"], event["object_id"],
                            event["quantity"]) != (
                                "balance:bench", "beaker:001", "mass_g"):
                            raise Conflict("Scored a different measurement")
                    elif (receipt["choice"] == "leave" and (
                            event["kind"] != "move" or
                            event["after_station"] != "station:center")):
                        raise Conflict("Scored leaving without actually moving")
                    elif receipt["choice"] == "inspect" and event["kind"] != "look":
                        raise Conflict("Scored an unexecuted inspection")
            instrument_final = bridge.instruments.verify()["revision"]
            if instrument_final != history["instrument_events_after"]:
                raise Conflict("Instrument event count changed")
            from pretorius_lab.doctor_admission_research import _subject_percept
            with bridge.habitat._open() as db:
                start = db.execute(
                    "SELECT envelope,event_hash FROM instrument_events WHERE revision=1"
                ).fetchone()
            source = "laboratory-instrument:" + start[1]
            original = [m for m in bridge.brain.brain.store.memories()
                        if m["source"] == source]
            if len(original) != (1 if condition == "observed" else 0):
                raise Conflict("Original measurement source-exposure control leaked")
            scored = assess_delayed_choice(
                delivered=(condition == "observed"), proposal=proposal,
                receipt=receipt,
                before_instrument_events=history["instrument_events_before"],
                after_instrument_events=instrument_final)
            outcomes["arms"][policy][condition] = {
                "brain_checkpoint_reopened": True,
                "initial_verified_host_measurement": True,
                "original_source_memory_count": len(original),
                "policy": proposal["policy"],
                "brain_tendency": proposal.get("brain_tendency"),
                "proposed_choice": proposal["choice"],
                "host_accepted": receipt["accepted"],
                "outcome": scored,
            }
    for policy, trials in outcomes["arms"].items():
        outcomes.setdefault("summary", {})[policy] = {
            "correct_delayed_decisions": sum(
                int(v["outcome"]["success"]) for v in trials.values()),
            "opportunities": len(trials),
        }
    (root / "score.json").write_text(
        json.dumps(outcomes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps(outcomes["summary"], indent=2, sort_keys=True))
    return outcomes


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    stage = p.add_mutually_exclusive_group()
    stage.add_argument("--choose", action="store_true")
    stage.add_argument("--score", action="store_true")
    args = p.parse_args()
    root = args.output.resolve()
    if args.choose:
        choose(root)
    elif args.score:
        score(root)
    else:
        build(root)


if __name__ == "__main__":
    main()
