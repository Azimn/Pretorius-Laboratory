"""Strict, non-fabricating natural-language intent → source-backed home action.

A text-based simulation can interpret an unfamiliar phrasing without writing
imaginary consequences. This narrow parser proposes a real action from the
current authoritative offer catalog. Unsupported, ambiguous or impossible
intentions remain proposals and NEVER mutate the material world.
"""
from __future__ import annotations
import re

from .home_affordances import HomeAffordances
from .physics import LabError
from .home_arrangement import ANCHORS

OBJECT_ALIASES = {
    "chair:parlor": ("chair", "armchair"),
    "table:parlor": ("side table", "small table"),
}
ANCHOR_ALIASES = {
    "parlor:window": ("window",),
    "parlor:hearth": ("fireplace", "hearth", "fire"),
    "parlor:desk": ("writing desk", "desk"),
    "parlor:door": ("doorway", "door"),
}


def _words(raw):
    return re.sub(r"[^a-z ]", " ", raw.lower()).split()


def _contains_phrase(words, phrase):
    tokens = phrase.split()
    return any(words[i:i + len(tokens)] == tokens
               for i in range(len(words) - len(tokens) + 1))


def propose(text, home: HomeAffordances):
    """Make an exact offer-based proposal. No arbitrary property patches."""
    if type(text) is not str or not 1 <= len(text) <= 260:
        raise LabError("A bounded natural language intention is required")
    if not isinstance(home, HomeAffordances):
        raise TypeError("Only the existing physically verified home accepts proposals")
    words = _words(text)
    operations = set()
    if any(v in words for v in ("move", "shift", "put", "place", "rearrange")):
        operations.add("move")
    if any(v in words for v in ("turn", "face", "rotate", "orient")):
        operations.add("turn")
    objects = {
        oid for oid, aliases in OBJECT_ALIASES.items()
        if any(_contains_phrase(words, alias) for alias in aliases)
    }
    # The word "table" alone is ambiguous in this actual house; insist
    # on "side table" instead of accidentally changing the dining table.
    anchors = {
        anchor for anchor, aliases in ANCHOR_ALIASES.items()
        if any(_contains_phrase(words, alias) for alias in aliases)
    }
    if len(operations) != 1 or len(objects) != 1 or len(anchors) != 1:
        return {"status": "needs_specific_real_action", "offer_id": None,
                "reason": "The action, furnishing or exact place is ambiguous"}
    op, oid, anchor = next(iter(operations)), next(iter(objects)), next(iter(anchors))
    wanted = {"object": oid, ("anchor" if op == "move" else "facing"): anchor}
    current = home.discover()
    selected = next((offer for offer in current["offers"]
                     if offer["command"] == "arrange:" + op
                     and offer["args"] == wanted), None)
    if selected is None:
        return {"status": "not_currently_possible", "offer_id": None,
                "reason": "No corresponding source-verified physical offer exists"}
    return {"status": "offered", "offer_id": selected["offer_id"],
            "command": selected["command"], "args": selected["args"],
            "world_stamp": current["world_stamp"]}


def act(text, home: HomeAffordances, *, event_id: str):
    """Perform only a genuinely offered, still valid action."""
    proposal = propose(text, home)
    if proposal["status"] != "offered":
        return proposal
    receipt = home.act(proposal["offer_id"], event_id=event_id)
    return {"status": "committed", "subject": receipt,
            "command": proposal["command"], "args": proposal["args"]}
