"""A bounded 30-day household resource envelope, NOT an autonomous Doctor.

This is an explicit scripted counterfactual/reference controller applying
the SAME pure validated household reducer as the real source-world history.
It is useful for proving that ordinary resources can remain satisfiable for
30 days without auto-feeding. It cannot prove the Doctor will choose actions,
navigate safely, or live independently.
"""
from __future__ import annotations

import argparse
import json

from .daily_rhythm import initial_state, transition
from .physics import Conflict, LabError

PHYSICAL_ACCESS_ASSUMED = {"meal": True, "tea": True, "water": True}
MINUTES_PER_DAY = 1440


def simulate(*, days=30, missed_delivery_days=()):
    if type(days) is not int or not 1 <= days <= 90:
        raise LabError("Resource-envelope trial accepts 1-90 civil days")
    missed = set(missed_delivery_days)
    if any(type(x) is not int or not 1 <= x < days for x in missed):
        raise LabError("Missed days must be later, valid calendar dates")
    state = initial_state()
    state["meal_prepared_minute"] = None
    state["paper_marks"] = []
    last_delivery_day = 0
    proof = []
    outcomes = []
    source_events = 0

    def act(op, room, **args):
        nonlocal state, source_events
        old = state
        state, text = transition(
            state, op, args, room,
            stock_access=PHYSICAL_ACCESS_ASSUMED,
            care_authorized=True,
            delivery_authorized=(
                op == "accept_delivery" and args["day"] > last_delivery_day))
        source_events += 1
        proof.append((op, state["minute"], text["inner"]))
        # Material action provenance here is reducer-level only; the real
        # in-world receipts remain a separate integration test.
        assert state["minute"] >= old["minute"]
        return text

    def until(local_minute):
        """Move ordinary test clock forward without jumping into yesterday."""
        end = (state["minute"] // MINUTES_PER_DAY) * MINUTES_PER_DAY + local_minute
        while end - state["minute"] >= 10:
            amount = min(240, ((end - state["minute"]) // 10) * 10)
            act("advance", "station:bedroom", minutes=amount)

    def drink_until(max_thirst=3):
        # At this point the test controller assumes the subject has arrived
        # at the kitchen with an actually opened physical teacup.
        while state["thirst"] > max_thirst:
            if state["supplies"]["water"] == 0:
                act("draw_water", "station:kitchen")
            act("drink_water", "station:kitchen")

    def meal_if_needed():
        # Kitchen cleanliness/ fatigue are genuine constraints; do not
        # bypass them or secretly reset their values.
        if state["hunger"] < 4:
            return
        if state["fatigue"] >= 9:
            act("rest", "station:bedroom")
        if state["cleanliness"]["room:kitchen"] >= 3:
            act("clean", "station:kitchen")
        if state["supplies"]["water"] == 0:
            act("draw_water", "station:kitchen")
        if (state["supplies"]["rations"] == 0 or
                state["supplies"]["fuel"] == 0):
            raise Conflict("No real food route exists before the next delivery")
        act("prepare_meal", "station:kitchen")
        act("eat", "station:kitchen")

    for day in range(days):
        # Day 0 begins at 07:00; sleep from 23:00 gives the next sunrise.
        if state["minute"] // MINUTES_PER_DAY != day:
            raise Conflict("Scripted test entered the wrong world calendar day")
        start = state["minute"]
        if day > 0 and day not in missed:
            if not 360 <= start % MINUTES_PER_DAY < 1080:
                raise Conflict("Source delivery must be daytime, not automatic")
            act("accept_delivery", "station:hall", day=day)
            last_delivery_day = day
        drink_until()
        meal_if_needed()
        until(14 * 60)
        drink_until()
        meal_if_needed()
        until(19 * 60)
        drink_until()
        until(23 * 60)
        # A competent reference controller cannot subject the resident to
        # lengthy severe distress and call that a pass.
        if state["hunger"] >= 9 or state["thirst"] >= 8:
            raise Conflict("Unsafe unmet needs before a routine night")
        act("sleep", "station:bedroom")
        outcomes.append({
            "calendar_day": day, "morning_minute": start,
            "next_morning_minute": state["minute"],
            "hunger_on_waking": state["hunger"],
            "thirst_on_waking": state["thirst"],
            "fatigue_on_waking": state["fatigue"],
            "ration_stock": state["supplies"]["rations"],
            "water_stock": state["supplies"]["water"],
            "world_actions": source_events,
            "courier_collected": day > 0 and day not in missed,
        })
    # This is deliberately engineer-side only, never a first-person message.
    return {
        "protocol": "care-resource-envelope/1",
        "control": "host-scripted, *not* autonomous Doctor choice",
        "days": days, "missed_deliveries": sorted(missed),
        "events": source_events,
        "daily": outcomes,
        "final_resources": state["supplies"],
        "final_needs": {k: state[k] for k in ("hunger", "thirst", "fatigue")},
        "source_authenticity": "pure reducer only; no SQLite/world receipt",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Thirty-day pure world-care reference control")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--miss-delivery", action="append", type=int, default=[])
    args = parser.parse_args(argv)
    print(json.dumps(simulate(
        days=args.days, missed_delivery_days=args.miss_delivery),
        ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
