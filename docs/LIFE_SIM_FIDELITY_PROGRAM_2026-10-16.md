# Laboratory life-simulation fidelity program

**Established 2026-10-16.** This document is a development constraint, not a claim that Pretorius has become indistinguishable from a human.

## Target

Pretorius Laboratory should approach the causal consistency, meaningful choices and long-term persistence expected of excellent text-first simulations while remaining a modest, reproducible, local Python and SQLite project. Simulate only the aspects of life that materially affect what Pretorius can perceive, choose, remember or experience. A mechanism must earn its complexity through a measured improvement over a simpler control.

The program remains Laboratory-first. Frankenstein Village is a future, separately authoritative social environment. The existing Doctor Lives runtime remains the only owner of Pretorius's identity, memory, goals and recurrent cognition. Never create a second Pretorius brain inside the Laboratory or read hidden world audit values into his first-person thought stream.

## Research anchors

*Cataclysm: Dark Days Ahead* deliberately targets verisimilitude rather than exhaustive physical simulation. Time, movement costs, senses, finite items and survival consequences are coherent and cumulative. https://docs.cataclysmdda.org/design-balance-lore/design-user-experience.html and https://docs.cataclysmdda.org/design-balance-lore/design-balance.html

Inform 7's Standard Rules provide an object/room/action world model with common constraints and action rulebooks, rather than hand-scripting every episode. https://ganelson.github.io/inform/standard_rules/index.html

Classic Sims-style need/utility arbitration, procedural/goal-oriented action planning and compact finite-state schedules are candidate control methods, not goals in themselves. The Doctor Lives already has an experimental Sims-inspired home controller. Reuse existing code and evidence rather than rebuilding it.

## Reality check on the current code

The Laboratory already records durable location and item custody, authentic volume and measurement history, books and source text, body reflexes, rooms and furniture, finite supplies, hunger, thirst, fatigue, laboratory wear, day/night, fuel-burning lamps, domestic work and independent first-person observations. Several mechanisms are opt-in rather than globally active. The world currently advances principally on admitted actions rather than continuously in external wall-clock time. Its social system, weather, ecology, coherent simulated seasons, independent daily NPC activities and genuine multiweek character life trajectories are not established.

The retro turn-cost pilot in PR #25 explicitly charges short movements and handling activities against the original physical clock, and guards an extended visual task against running out of light before completion. The default unmodified subject interface remains a control. The next question is whether the cost is low enough to warrant introducing it into a real Doctor/Laboratory action boundary without violating already admitted historic experiences.

## Fidelity evaluation contract

Every proposed change must have a **physical-world control** using the same initial world, actions, object placements and resource rules, changing only the proposed mechanism. Report exact state and hash verification, legitimate failed actions, repeat/restart and fork behavior, time-to-completion and CPU/runtime cost. End-of-action time consistency should be tested across day/night, fading lamp light, hunger thresholds and deadlines.

Long-horizon studies should contain at least one routine day, disrupted day, recuperation day and a multiday sequence in which old actions still have consequences. Planned next cases include meals left unattended, exhausted versus worn-equipment competition, finite supplies, missed opportunities, a task that cannot be completed in the remaining daylight and interruptions that resume without duplicate events. These are candidate tests, not present capabilities.

A distinct **character-behavior test** must compare unchanged Doctor, the existing Sims-inspired home controller, portable-life hybrid candidate and the strongest cheap first-person rule baseline. All candidates need equivalent permitted information and fair action/computation budgets. Record the character's actual future choices and consequences, not the preferred wording of a response. The strong simple baseline is expected to win frequently, and that is valid negative evidence.

The separate **human-likeness assessment** requires blinded, independently written behavior-vignette judgments covering temporal continuity, spontaneous goals, accumulated quirks, physical attention, mistakes, recovery, changing relationships and long-term idiosyncrasy. Do not award any Article promotion based solely on code tests or subjective statements about consciousness.

## Complexity budget

First use deterministic condition-action rules, fixed affordances, small finite-state machines and a bounded utility selector. Reuse the simulation ledger and original body's qualitative observations. Add caching, learning, lookahead, probabilistic events or new cognitive organs only after a registered comparison demonstrates measurable improvement in plausible consequences or credible observer judgments, with a cost and failure analysis.

Never silently modify an inhabited world ledger's historical reducer, trusted canon, private autobiographical memories, Village state or the real Doctor's neural checkpoint. Research mechanisms enter through opt-in versioned gates and graduate only after safety, causal and longitudinal testing.

## Immediate trajectory

Complete the opt-in source-bound time pilot and independently verify physical day/night effects. Then run a day-to-day continuity benchmark to see whether the most immersion-breaking next defect is food persistence, household object affordances, passive environmental changes or a missing interruption recovery. Fix **one** demonstrated defect with the least mechanism that closes it, rerun the cheap-rule and no-feature controls, and only then consider adding another.

A Laboratory full of elaborate background systems that Pretorius cannot meaningfully perceive or interact with does not meet this fidelity target. A few persistent, causally related choices that reshape tomorrow's world may do much more.
