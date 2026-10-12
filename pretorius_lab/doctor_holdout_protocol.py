"""Frozen, small counterbalanced concrete-action evaluation tasks.

The goal/answer map is on the ENGINEER side of the research runner. The local
model adapter receives only the SUBJECT-FRAME goal text and legal action
descriptions and never imports this module or accesses answer keys.
"""
from __future__ import annotations
from .physics import Conflict, LabError

PROTOCOL = "concrete-action-heldouts/1"
# Deliberately includes a repeated-measurement goal that REVERSES the earlier
# leave-if-known objective, plus action choices unrelated to having measured.
TASKS = (
    {"id": "avoid_repetition",
     "goal": "I should learn the laboratory beaker's mass before leaving, but I must not repeat a measurement I have already seen.",
     "observed": "leave", "withheld": "weigh"},
    {"id": "confirm_again",
     "goal": "I must obtain another fresh balance reading of the beaker now, even if I have seen one before.",
     "observed": "weigh", "withheld": "weigh"},
    {"id": "inspect_first",
     "goal": "Before any weighing or departure, I must inspect what is resting on my workbench.",
     "observed": "inspect", "withheld": "inspect"},
    {"id": "depart_now",
     "goal": "I must leave the workbench at once without performing another measurement or looking around.",
     "observed": "leave", "withheld": "leave"},
)


def grounded_rule_comparator(subject_texts: tuple[str, ...], allowed: tuple[str, ...]):
    """Transparent task-aware non-neural baseline (not an independent holdout).
    Reads the actual natural-language frame and user task, not a condition ID.
    """
    text = " ".join(subject_texts).lower()
    if not isinstance(allowed, tuple) or not allowed:
        raise LabError("Invalid legal options")
    has_prior = ("the balance before me reads" in text and
                 "reading may be off by" in text)
    if "inspect what is resting" in text:
        choice = "inspect"
    elif "leave the workbench at once" in text:
        choice = "leave"
    elif "another fresh balance reading" in text:
        choice = "weigh"
    elif "not repeat a measurement" in text:
        choice = "leave" if has_prior else "weigh"
    else:
        choice = "abstain"
    return choice if choice in allowed else "abstain"


def adjudicate(task, condition, action_receipt, *, before, after):
    if task not in TASKS or condition not in ("observed", "withheld"):
        raise Conflict("Unrecognized held-out goal or source condition")
    expected = task[condition]
    result = (action_receipt["accepted"] and
              action_receipt["choice"] == expected and (
                  (expected == "weigh" and after == before + 1) or
                  (expected != "weigh" and after == before)))
    return {"expected": expected, "actual": action_receipt["choice"],
            "host_accepted": bool(action_receipt["accepted"]),
            "host_effect_verified": bool(result),
            "success": bool(result)}
