# Inventory coherence v0.1: physical provisions constrain real cooking

Date: 2026-10-17. Draft stacked on multi-day food PR #26, which is stacked on retro action-time PR #25.

## Why this repair is needed

Pretorius's existing kitchen holds a real bread loaf (`food:bread`) and a tea tin (`food:tea`), plus cup and teapot, in a durable physically located domestic ledger. Simultaneously, the DailyRhythm ledger holds numerical portions for `rations` and `tea`. Until this candidate, the actor could physically carry bread and the tea tin to another room, then prepare a meal or tea as though the original ingredients were still on the kitchen table. This is an observable, resource-relevant life-simulation inconsistency.

## Minimum game-AI mechanism

The new opt-in `pretorius-daily-rhythm/3-physical-provision-access` profile reuses the **same** embodied room, kitchen containers, durable item movement and existing finite portion counters. For cooking to proceed, the actual `food:bread` object must be present and accessible in the kitchen (at an open container or held by the subject). For tea, the actual tea tin, teapot and cup must be accessible. A closed cupboard is not an inventory source the subject can magically reach through. Existing nutritional rules, light requirements, work durations and stock decrements are unchanged.

The v3 world grants no new crafting system, no extra character body, no new inventory or background refresh scheduler. The trusted DailyRhythm host checks the **authoritative HomeLife state within the same SQLite action transaction**. Callers cannot inject resource availability through subject arguments. Accepted actions remain bound to the real object's source revision and hash.

Crucially, replay reconstitutes domestic states at the **home revision when each historical daily action occurred**, rather than using an item's current location. If tea was accessible during a drink on Monday and then moved on Tuesday, Monday's event must still be verifiable. HomeHistory is independently source-replayed with the existing HomeLife deterministic reducer.

## Preservation

Old `pretorius-daily-rhythm/1` and `.../2-perishable-meals` rules replay under their original availability decisions and original state hashes. No populated v1/v2 world can be silently upgraded into v3. Forks inherit physical conditions and the rule profile, not historical assertions of personal experience. The real Doctor's memory and neural checkpoint remain unchanged.

This milestone **does not fully unify numerical stocks and object mass**. The physical bread loaf and tea tin still represent containers of portions managed by the existing rhythm ledger. The physical object appearance does not shrink as portions fall, and the simulation does not currently track crumbs, packets or exact fluid volumes. These are explicit known deficits rather than falsely claiming complete inventory unification.

## Measured causal gate

The paired scripted 48-hour trial in `tools/physical_provision_comparison.py` moves the same loaf into a parlor desk in both identical worlds, advances time through two days, sleeps and cleans the kitchen, then attempts to cook. The v2 control can prepare a meal even without bread; the v3 candidate refuses without changing time or provisions. Moving the bread back into the real kitchen enables v3 cooking and consumes one actual ration. Test verification includes later item relocation, previous successful action replay, cupboard opening, fork isolation, rejected forged arguments, and both Python 3.11 and 3.12 full Laboratory suites.

An observed difference proves an **environmental causal-logic gain**, not humanlike decision-making or any qualification of the Articles of Artificiality. Do not promote Article engineering or full-domain scores for these environment-only test fixtures.

## Development priority after this pass

Once physical preconditions are verified in a real multiday world, choose between (a) extending the same stock objects with remaining portions and visible depletion, or (b) testing a source-connected Pretorius autonomous daily trajectory. The next mechanism should be selected by the most damaging demonstrated inconsistency and should win over the cheap unchanged world on a fair measure. Focus on daily agency and constraints before adding weather, cultural systems, or elaborate autonomous NPCs.
