"""A narrowly bounded research proposal port for real Pretorius policy tendencies.

No generative model decodes object/action operands here. A frozen,
goal-blind mapping translates the existing Doctor Lives ABSTRACT recurrent
policy tendency into exactly one lab-approved action (or abstention).
The next-session scorer is separate. A proposal is not an execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .embodied_access import EmbodiedAccess
from .bench_instruments import BenchInstruments
from .physics import Conflict, LabError

RULESET = "research-legal-bench-proposal/1"
LABELS = {
    "weigh": "I could put the beaker on the balance and read its weight.",
    "inspect": "I could look around my workbench.",
    "leave": "I could step away from the bench into the center of the room.",
    "abstain": "I cannot decide what to do next.",
}
# Preregistered BEFORE tests. This deliberately makes the full abstraction
# gap visible; it is not a learned affordance model or an LLM decision.
TENDENCY_MAP = {
    "explore": "weigh", "create": "weigh", "challenge": "weigh",
    "approach": "inspect", "persist": "inspect", "comply": "inspect",
    "avoid": "leave", "conceal": "leave", "dominate": "leave",
    "cooperate": "abstain",
}


@dataclass(frozen=True)
class ActionOffer:
    ruleset: str
    choices: tuple[str, ...]
    subject_native_options: tuple[str, ...]


class LegalBenchActionGate:
    def __init__(self, habitat):
        self.habitat = habitat
        self.actor = EmbodiedAccess(habitat)
        self.instruments = BenchInstruments(habitat)

    def offer(self) -> ActionOffer:
        self.actor.verify()
        self.instruments.verify()
        station = self.actor.verify()["station"]
        if station != "station:bench":
            return ActionOffer(RULESET, ("abstain",), (LABELS["abstain"],))
        choices = ["inspect", "leave", "abstain"]
        # The operator builds eligible action/operands from physically verified
        # current placement, not from model-provided object IDs.
        with self.habitat._open() as db:
            from .book_custody import effective_objects
            objects = effective_objects(db)
            obj = objects.get("beaker:001")
            if (obj and obj["anchor_id"] == "bench:main/position:left"
                    and obj.get("held_by") is None and not (
                        obj["condition"] == "broken" and not obj["collected"])):
                choices.insert(0, "weigh")
        return ActionOffer(RULESET, tuple(choices),
                           tuple(LABELS[c] for c in choices))

    def execute(self, choice: str, *, event_id: str | None = None) -> dict[str, Any]:
        if not isinstance(choice, str) or choice not in LABELS:
            raise LabError("Unknown laboratory action proposal")
        # Recheck source state as close to execution as permitted; operation
        # itself checks the underlying SQLite position/occupancy atomically.
        offer = self.offer()
        if choice not in offer.choices:
            raise Conflict("Proposed action not eligible in current room")
        if choice == "weigh":
            executed = self.actor.measure(
                "balance:bench", "beaker:001", "mass_g", event_id=event_id)
        elif choice == "inspect":
            executed = self.actor.look(event_id=event_id)
        elif choice == "leave":
            executed = self.actor.move("station:center", event_id=event_id)
        else:
            return {"accepted": False, "choice": "abstain", "host_event_hash": None,
                    "reason": "explicit_abstention"}
        return {
            "accepted": True, "choice": choice,
            "host_event_hash": executed["event_hash"],
            "host_event_id": executed["event_id"],
            "host_domain": "instrument" if choice == "weigh" else "embodied",
        }


def propose_from_brain(port, offer: ActionOffer) -> dict[str, Any]:
    """Ask the ACTUAL persisted Doctor neural/state policy, not a host oracle."""
    if not isinstance(offer, ActionOffer) or offer.ruleset != RULESET:
        raise LabError("Invalid legal-action offer")
    thought = port.cognition("laboratory-legal-action-research")
    tendency = thought["selected_action"]
    if tendency not in TENDENCY_MAP:
        raise Conflict("Unknown brain policy tendency")
    mapped = TENDENCY_MAP[tendency]
    # No success-seeking host substitution: an unavailable proposal ABSTAINS
    # rather than silently choosing a correct alternate action.
    choice = mapped if mapped in offer.choices else "abstain"
    return {
        "policy": "real-doctor-recurrent-abstract-tendency-plus-fixed-mapping",
        "brain_policy_decision_id": thought["policy_decision_id"],
        "brain_tendency": tendency,
        "mapped_choice": mapped,
        "choice": choice,
        "eligible": list(offer.choices),
        "mapping_version": RULESET,
        "neural_not_language_model_decoding": True,
    }


def propose_stateful_non_neural(*, observed: bool, offer: ActionOffer) -> dict[str, Any]:
    """Transparent independent comparator; no access to hidden host mass."""
    if not isinstance(observed, bool):
        raise LabError("Stateful comparator must receive a real delivered flag")
    # It can use only a real source-delivery fact. The beaker's private
    # numeric profile is not presented to the baseline.
    mapped = "leave" if observed else "weigh"
    choice = mapped if mapped in offer.choices else "abstain"
    return {
        "policy": "stateful-explicit-instrument-delivery-comparator",
        "mapped_choice": mapped,
        "choice": choice,
        "eligible": list(offer.choices),
        "neural_not_language_model_decoding": True,
    }


def assess_delayed_choice(*, delivered: bool, proposal: dict, receipt: dict,
                          before_instrument_events: int,
                          after_instrument_events: int) -> dict:
    """Predeclared objective, using ONLY approved host outcome events.

    Goal: finish with a bounded beaker measurement known to the agent, and
    do not repeat the measurement if already observed. Thus the delivered
    condition should leave; the withheld condition should reweigh.
    """
    expected = "leave" if delivered else "weigh"
    executed = bool(receipt["accepted"])
    compliant = (
        executed and proposal["choice"] == expected and
        receipt["choice"] == expected and (
            (expected == "weigh" and
             after_instrument_events == before_instrument_events + 1) or
            (expected == "leave" and
             after_instrument_events == before_instrument_events)
        )
    )
    return {
        "goal": "obtain a bounded beaker mass reading without redundant measurement",
        "expected_action": expected,
        "proposed_action": proposal["choice"],
        "host_accepted": executed,
        "host_effect_verified": compliant,
        "success": compliant,
        "no_credit_for_look_abstention_or_controller_action": True,
    }
