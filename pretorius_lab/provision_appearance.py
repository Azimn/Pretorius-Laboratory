"""Qualitative appearance of real food objects from ONE existing stock authority.

There is no second count. HomeLife owns location/custody; DailyRhythm owns
the remaining provisions and records every consumption. Descriptions belong
only in the verified first-person SubjectPort, not the model's hidden state.
"""
from __future__ import annotations

from .physics import Conflict

BREAD = (
    "bare bread remnants, with nothing substantial left to prepare",
    "the last usable portion of the bread loaf",
    "about half of the bread loaf, enough for two meals",
    "most of the bread loaf, enough for three meals",
    "a whole bread loaf, enough for four meals",
)
TEA = (
    "an empty tea tin",
    "a tea tin with enough leaves for one cup",
    "a tea tin with enough leaves for two cups",
    "a tea tin with enough leaves for three cups",
)


def provision_names(daily_state: dict) -> dict[str, str]:
    """Trusted environment renderer; no arbitrary captions from the subject.

    Values are exact counted portions in the original authoritative daily
    ledger; visual descriptions are discrete game-like approximations.
    """
    supplies = daily_state["supplies"]
    rations, tea = supplies["rations"], supplies["tea"]
    if type(rations) is not int or type(tea) is not int:
        raise Conflict("Invalid authoritative physical provision quantities")
    if not 0 <= rations < len(BREAD) or not 0 <= tea < len(TEA):
        raise Conflict("Remaining food exceeds its original physical containers")
    return {"food:bread": BREAD[rations], "food:tea": TEA[tea]}
