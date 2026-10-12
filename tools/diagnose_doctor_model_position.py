"""Diagnostic-only positional bias test on a real saved Pretorius subject frame.

No physical actions are executed by this diagnostic. It cannot be counted as
an extra successful cognitive task, and is run after the frozen main battery.
"""
from __future__ import annotations

import json
from pathlib import Path
import argparse

from pretorius_lab.doctor_admission_research import ResearchInstrumentAdmission
from pretorius_lab.doctor_legal_action_research import LegalBenchActionGate, ActionOffer, RULESET, LABELS
from pretorius_lab.doctor_holdout_protocol import TASKS
from pretorius_lab.doctor_subject_frame_proposer import (
    PinnedSmolLM2, choose_from_subject_frame,
)
from run_doctor_instrument_pilot import neural_config


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    root = args.output.resolve()
    decoder = PinnedSmolLM2()
    result = {"status": "diagnostic_only", "claim": "no_accepted_host_actions",
              "model_revision": decoder.revision, "probes": []}
    task = next(t for t in TASKS if t["id"] == "depart_now")
    for exposure in ("observed", "withheld"):
        folder = root / "subject_frame_local_model" / task["id"] / exposure
        bridge = ResearchInstrumentAdmission(
            folder / "world.sqlite3", folder / "brain",
            neural_config=neural_config())
        bridge.verify()
        offer = LegalBenchActionGate(bridge.habitat).offer()
        # Identical context and goal in both prompt alternatives;
        # only the option ordering changes.
        for order in (
                ("weigh", "inspect", "leave", "abstain"),
                ("leave", "inspect", "weigh", "abstain"),
                ("inspect", "weigh", "leave", "abstain")):
            if set(offer.choices) != set(order):
                raise RuntimeError("Physical offer changed before diagnostic")
            shuffled = ActionOffer(
                RULESET, order, tuple(LABELS[key] for key in order))
            proposal = choose_from_subject_frame(
                bridge.brain, shuffled, task["goal"], decoder)
            result["probes"].append({
                "exposure": exposure,
                "options": list(order),
                "model_raw_output": proposal["model_raw_output"],
                "selected_action": proposal["choice"],
                "invalid_output": proposal["invalid_output"],
            })
    (root / "option-order-diagnostic.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
