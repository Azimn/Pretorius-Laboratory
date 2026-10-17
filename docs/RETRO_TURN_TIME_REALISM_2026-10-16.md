# Retro game turn-cost pilot for Pretorius Laboratory

**Date:** 2026-10-16. **Status:** opt-in prototype, no change to default inhabited Laboratory worlds or Pretorius canonical identity.

## Aim

Increase material and temporal believability in the existing text-only Laboratory with a *small, old-school game technique*: every accepted movement and minor manipulation consumes a little of the same world clock used for light, hunger, thirst, fatigue, and accumulated household conditions. We are not implementing another clock, a life-needs framework, a planner, or a graphics/physics system.

The world already tracks exact persistent physical state, day/night, lamps, supplies, physiological needs and object handling. However, most moving and examining operations previously consumed **zero world minutes**. This permits indefinite movement while ambient daylight, needs and oil remain frozen. That is a concrete simulation inconsistency, not merely unpolished prose.

## Precedents

*Cataclysm: Dark Days Ahead* describes verisimilitude and action/time cost as central to its world, even when literal realism would make gameplay worse. See https://docs.cataclysmdda.org/development_process.html and https://docs.cataclysmdda.org/design-balance-lore/design-user-experience.html .

Inform's Standard Rules use a consistent physical world model and action rules rather than individually scripted outcomes: https://ganelson.github.io/inform/standard_rules/index.html .

The Sims-inspired motive mechanism remains in The Doctor Lives and is neither duplicated nor replaced. This pilot lives in the independent Laboratory. Transfer to real Doctor cognition is a separate, future experiment requiring safe authority and receipt integration.

## Minimal implementation

A new **pure replayable** `tick` operation in the existing DailyRhythm reducer advances 1 through 10 simulated minutes. Earlier `advance` and existing work events retain their original durations and semantics, preserving version-one history replay. Tick cannot be chosen directly through the subject's normal activity API.

The optional `TurnCostSubjectPort` wraps the one existing `SubjectPort`. It charges two minutes for moving between adjacent stations, one for small handling actions, three for shifting the stool, eight for measurement, and ten for reading a book page. Actual time-consuming household activities such as experimenting, resting, cooking and sleep are not charged twice. Every tick updates the existing sources of truth for daylight and bodily state. The subject hears only first-person consequences. The exact tick counts are engineer-side rules, not raw subjective telemetry.

Timed actions need a stable, host-authorized event ID. The adapter records pending intents in the **same world database**, prevents reassigning an event ID to another command, prevents a later timed action from overtaking an unresolved one, and caches the exact first-person response after successful completion. A rejected action does not cost minutes and its reservation is released only when authoritative world verification and absence of the physical receipt show no action occurred. On interruption after the physical action but before the time tick, retrying the same ID can finish the tick. In the narrower post-clock/pre-final-record crash window, replay fails closed and requires explicit engineering reconciliation, rather than recomposing an unverified historic utterance.

The wrapper is not a security-enforced replacement for every older API. It is an experimental *single-host action interface*. Any future integration must prevent privileged legacy side channels and demonstrate safe use across the real Doctor bridge.

## Matched-world measurement

`tools/retro_action_time_comparison.py` starts two independently constructed and materially equivalent real Laboratory worlds at 17:50. Both execute exactly six legal, adjacent moves. The unchanged control world receives zero minutes; the timed world receives twelve minutes and reaches 18:02. The daylight difference must be **observed in the actual first-person subject frame**, and both independently persisted world ledgers must replay successfully. No narrative-only claim is credited.

`tests/test_turn_cost.py` evaluates actual movement, state cost, replay and idempotency, lamp fuel duration, zero-cost denial, binding against changed requests, existing work durations, crash before/after the tick, source-text tampering, and the unchanged-world control. The dedicated GitHub Actions workflow tests both Python 3.11 and 3.12, executes the physical comparison and runs the full existing Laboratory regression suite.

## Research grade

The meaningful **new verified target** is temporal physical consistency, not new autonomous intelligence. A passed causal control demonstrates that moving and manipulating objects can affect time-dependent world conditions, something the old default did not. It does not establish humanlike motivations, real-world time, independent spontaneous action, age/seasonal biology, calibrated historical accuracy, improved player immersion, or general cross-environment cognitive transfer.

No 34-Article engineering or qualification gate may be promoted based solely on this infrastructure. The canonical tracker remains independently controlled by Doctor Lives.

## What should come next

First obtain reproducible multi-hour/multi-day trajectories in one material world and identify impossible interactions. Then consider **one** simple background event rule at a time, such as prepared-food spoilage or an NPC schedule, only when a control comparison shows improved causal consistency or believable choice consequences. Preserve existing event-sourced authority, first-person access limits, and one Pretorius identity across every change.

The standard for Laboratory competitiveness is a persistent, coherently evolving text world with credible cause and effect, recoverable interruptions, meaningful constraints, and behavior that withstands blinded comparison against an inexpensive rule-based character. More content, tokens, or neural parameters do not automatically satisfy this standard.
