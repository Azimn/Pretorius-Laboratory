# Multi-day food realism: historical compatibility and measurable simulation consequence

Status: 2026-10-17 experimental, branch experiment/lab-multiday-meal-freshness-20261017. Stacked after opt-in clocked actions PR #25. No existing inhabited world migrated, no changes to canonical Pretorius identity or cognitive state.

## Observed defect

The original Laboratory has a Boolean `meal_ready` state. An uneaten meal persists as edible for any length of simulated time, even while sunlight, fuel, hunger, fatigue and the condition of the house change. In a text life simulation this is a material causal inconsistency. Multi-day accumulation of consequences is more valuable than decorative narrative detail.

## Minimum proposed mechanism

Add an optional `pretorius-daily-rhythm/2-perishable-meals` profile with a single extra field, `meal_prepared_minute`, inside the **existing authoritative daily-state ledger**. Prepared meals age against the existing clock, with no timers, daemons, random numbers, new autonomous agents, or second world authority. After a coarse six-hour period a prepared meal is described as left out too long, cannot be eaten, and must be consciously discarded in the real kitchen. Throwing it out consumes ten simulated minutes and does **not** refund the physical water, rations, or fuel previously used. A fresh meal may subsequently be prepared, provided existing light, cleanliness, fatigue and stock constraints permit it.

The threshold is **game-world approximation**, not a food-safety recommendation or a realistic spoilage model. The key tested mechanism is that time has consequences. A production simulator could later distinguish perishable ingredients, refrigeration, serving conditions and contamination, but only if a measured need justifies that complexity.

## Legacy-history protection

Profile v1 retains its original state schema, reducer behavior and digest. Existing previously admitted events replay under their original rules. An old world cannot select the new profile in place, and newly constructed opt-in v2 worlds are independently initialized. Forks of v2 worlds inherit **material conditions** including the physical age of a meal, never their parent's lived event claims. The restricted SubjectPort and existing resource transaction guard accept v2 only when an actual versioned daily world was created. The v1 subject does not acquire a new discard capability.

## Adversarial controls

The paired experiment at `tools/multiday_food_comparison.py` creates independent source-backed worlds with materially equivalent provisions and identical actions for 48 simulated hours. The original rules allow the old meal to be eaten; the v2 rules classify it as stale, refuse eating without advancing the clock or mutating stocks, and support a source-recorded discard with actual wasted provisions. Both event histories must replay independently.

The tests cover the exact six-hour threshold, recovery by cooking again, 48-hour unattended food persistence rather than magical deletion, body and room authority, restart/replay, rule isolation, denial without resource mutation, and forked-world independence. The full Laboratory suite and the opt-in turn-clock tests must continue to pass on Python 3.11 and 3.12.

## Related game simulation discipline

Inform's check, carry-out and report phases separate legal action validation, world updates and presentation. Cataclysm: Dark Days Ahead emphasizes verisimilitude, with time and material constraints affecting available future actions. This proposed change applies exactly that principle in the same Laboratory system rather than introducing a more complex general biology model.

References:
https://inform-7-handbook.readthedocs.io/en/latest/chapter_4_actions/rulebooks_%26_stop_the_action/
https://docs.cataclysmdda.org/design-balance-lore/design-balance.html

## Interpretation and next work

A passed benchmark is evidence of **environmental causal fidelity** and longitudinal persistence, not spontaneous life, adaptive intelligence, human consciousness, or any 34-Article qualification. No Doctor action controller is modified. Subsequent work should score multi-day resource decisions and mistakes made by the actual Doctor against an equally informed simple rule controller, then develop only the lowest-cost missing mechanism.

The Laboratory should become more life-like because yesterday's accepted actions constrain today's legitimate options, not because every scene receives invented sensory prose.
