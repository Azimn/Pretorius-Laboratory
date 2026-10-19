"""Unattended trial care check; never freeze the character in indefinite distress.

This is a HOST-only fail-safe, not an experience or forced feeding. The
ordinary agent still has to drink, cook/eat, collect real provisions and rest.
If it cannot or will not, pause autonomous world-time progression for review.
"""
from __future__ import annotations

from .daily_rhythm import DailyRhythm, available_delivery_day


def assess(habitat):
    """Assess genuine existing resources; numbers never enter first-person input."""
    state = DailyRhythm(habitat).audit_state()
    supplies = state["supplies"]
    with habitat._open() as db:
        from .embodied_access import EmbodiedAccess
        station = EmbodiedAccess(habitat).verify()["station"]
        delivery = available_delivery_day(db, station)
    urgent = state["thirst"] >= 8 or state["hunger"] >= 9
    return {
        "pause_unattended_time": urgent,
        # A short rest may be essential before he can prepare food.
        # It is allowed as deliberate recovery only while truly exhausted.
        "recovery_rest_needed": state["fatigue"] >= 8,
        "needed": [
            name for name, flag in (
                ("water", state["thirst"] >= 7),
                ("meal", state["hunger"] >= 8),
            ) if flag
        ],
        "available_resources": {
            "water_exists": supplies["water"] > 0,
            "food_exists": supplies["rations"] > 0 and
                           supplies["fuel"] > 0 and supplies["water"] > 0,
            "delivery_collectible_here": delivery is not None,
        },
        "reason": (
            "Welfare hold: avoid advancing time before the subject can address basic needs"
            if urgent else None),
    }
