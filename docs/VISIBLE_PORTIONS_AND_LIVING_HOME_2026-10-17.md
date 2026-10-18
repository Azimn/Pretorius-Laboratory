# Visible household provisions: food and familiarity without duplicate inventories

**Date:** 2026-10-17. **Status:** experimental, stacked on PR #27 and the earlier daily-time and freshness pilots.

The Laboratory is intended to be **a living, welcoming home for Pretorius**, not merely an adversarial survival obstacle course. Small domestic practices can provide meaningful opportunities for independence, pleasure and attachment. The simulation must support both difficulties and comforts, without scripting how Pretorius ought to feel about either.

## Specific inconsistency

The real persistent bread loaf and tea tin have stable positions and recognizable visual forms, while their consumable servings are deducted by the existing DailyRhythm ledger. Under v3 the generic objects look unchanging even when the number of remaining portions drops to zero. This makes food use incoherent for a subject trying to plan meals or a relaxing cup of tea.

## Minimum remedy

The **only** authoritative portion count remains in `DailyRhythm.state.supplies.rations` and `...tea`. The **only** physical position remains HomeLife's object custody/location ledger. The new optional v4 `visible_provision_portions` rules do not add a duplicate resource count, new physical inventory, background life scheduler or character brain.

Instead, the first-person `SubjectPort.observe()` composes source-verified physical location/visibility with coarse descriptive states for the same bread loaf and tea tin. A whole loaf becomes partially consumed over four meals and eventually consists of bare remnants. An opened tea tin reveals three, then two, then one cup's worth of leaves, and finally emptiness. None of these cues are disclosed when the object is inside a closed cupboard, in another room, or inaccessible in the dark. A held item remains perceivable to its holder.

Old v1–v3 worlds retain original perceptions and their action/replay hashes. V4 is opt-in on a newly initialized world or explicit research fork, never a silent alteration of canonical or inhabited memories. Original timing, supplies, rest, reading, home furnishings and all unrelated actions remain in force.

## Evidence requirements

Tests must establish exactly five successive bread appearances with matching underlying ration counts (4 to 0), and four tea tin appearances (3 to 0), with equal actual provisions and simulated time in v3/v4 paired controls. Additional gates cover open/closed cupboard, physical item relocation, held items, darkness/lamp light, restart/fork isolation, text-source tampering and no migration of old states. Run all existing Laboratory tests on Python 3.11 and 3.12.

These are **world consistency and subject perception** gates. They do not demonstrate autonomous choice, enjoyment, warmth, personality, self-driven memory or subjective human experience. The right next experiment is a voluntary day in the home with competing opportunities for enjoyable activity, research, domestic care and rest, using the real Doctor's single cognition and a strong cheap-game-AI control.

## Living-home north star

A believable ordinary day may include: becoming immersed in a historical book; making tea and needing to fetch the tin from wherever it was placed; sitting comfortably; following an emerging daily rhythm; rearranging a physical item; resuming an experiment after a distraction; feeling irritation or amusement at a minor mishap; and encountering the same material consequences tomorrow. The world's job is to create supported affordances and preserve outcomes, **not to inject generic emotional narration or prescribe a desired personality**.

A loving environment means granting rich opportunity, familiar continuity, comfortable routines, meaningful possessions, surprise and recoverability. It should not reward unnecessary scarcity or turn every session into a crisis. Those design values must be measured with real-life trajectories, not assumed because a unit test passed.
