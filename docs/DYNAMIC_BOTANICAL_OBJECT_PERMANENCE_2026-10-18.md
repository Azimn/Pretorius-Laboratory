# Pretorius's home: first world-created persistent specimen

**Prototype:** 2026-10-18. **GitHub branch:** `experiment/lab-dynamic-botanical-objects-20261018`, stacked on the unranked activity-discovery experiment. **Scientific status:** material simulation engineering, not Doctor cognition or Article-8 progress.

## Why this changes the design

A real-life sandbox cannot be a prewritten list of buttons. A character needs a trustworthy material world, ways to express intentions, and persistent consequences. An unused tool, neglected manuscript, unused flower press or forgotten meal remains part of that world rather than a failed engagement metric.

The Laboratory previously had good static physical book positions, cupboards, finite food and a single append-only written-paper object. But its HomeLife v1 validator fixed the inventory to an exact list of start IDs, so writing a separate `press_flowers` command would only simulate success in prose.

The new `MaterialObjects` annex demonstrates **dynamic item creation from a source item** in exactly the same SQLite Laboratory database, with its own append-only material event history. It does not rewrite HomeLife v1, the old DailyRhythm reducer, existing occupied furniture or Pretorius's established brain/memories.

## First fully causal material activity

The optional experimental household begins with a **single real cut rose**, physically on a kitchen table, and separately installed press, blotting papers and an empty mounting sheet in the parlor writing desk.

1. Pretorius must actually go to the kitchen, pick up the cut flower with an available hand, and carry it to the parlor.
2. He must open the desk and reach both the physical press and blotter sheets.
3. `start_press` moves the source rose **inside the press** and records the true world-clock starting minute. It cannot be used on a nonexistent, remote, duplicated or previously transformed flower.
4. The existing world clock must advance **at least 72 simulated hours**. No instant activity flag or host-provided "ready" assertion can bypass the physics. While the flower is enclosed inside opaque wood, it is not automatically visible.
5. `finish_press` creates a **new identity** `specimen:0001` with provenance `origin:plant:rose-001`. The original flower becomes a consumed source and cannot generate another specimen.
6. `mount` attaches the new specimen to the actual mounting sheet. `label` requires nearby paper and ink and accepts **only the subject's exact supplied text**, not a canned diary entry.
7. Pretorius can carry the sheet to another room and store it in the existing trunk. The mounted flower follows its physical parent; a closed trunk or dark passage hides the artifact. Opening the trunk again reveals the same personally labeled specimen.
8. SQLite restart retains the actual contents and source history. A laboratory fork inherits the **present physical object condition**, but has a fresh event chain and does not claim its Doctor lived through the parent's actions.

The material reducer requires authentic source ledger history: every receipt binds to the actual `body_revision`, `home_revision`, `rhythm_revision`, physical station, parent hashes and exact historical time. Verification replays the *old* household and clock states at the original moment, rather than applying today's possessions to yesterday's action.

## Cross-ledger physical constraints

Old household objects and new created botanical artifacts share **the same actual hands and furniture capacities**. Conditional write guards refuse taking ordinary bread while a flower is held, or putting another item into a writing desk already filled by paper, ink, press, blotters and sheet. The optional affordance catalog also filters these impossible offerings before Pretorius chooses.

The world supplies two views, not one omniscient description:
- The **physical state** is trusted engineer authority and includes hidden material, object ancestry, exact clocks, identifiers and parent receipts.
- The **subject view** includes only first-person, physically perceivable text and unranked available interactions. Pretorius is free to do something else or ignore all opportunities.

## Important limits

This is a proof of compositional material persistence, **not** arbitrary real-world freedom yet. The first fixture supports one botanical source, one press and one herbarium sheet. There is no outside garden, ongoing harvesting, procedural generated flower variants, several simultaneous presses, climate-dependent drying, plant growth or consumable blotter replenishment. Pressing/mounting/labeling presently have no short dedicated turn-time cost; only the **actual 72-hour drying interval** is enforced. The labels use accessible writing paper and ink but do not yet decrement individual blank cards or ink millilitres.

There are not yet full recipe preparation, crafting, journal volumes, creative experiment reagents or spontaneous everyday activities in this new material annex. These should grow from shared object components and compositional verbs in controlled versioned increments rather than unbounded arbitrary metadata patches.

The real Doctor has not independently decided to press a flower in these tests. The engineer-authored steps establish a **world that would honor that intention if he chose it**.

## Follow-up engineering gates

1. Generalize from one source flower to **N independently sourced cuttings**, reusable paper/press components, per-plant identity and several independently drying specimens.
2. Preserve physical transformation across real interruption: start five projects, abandon some, revisit others later, and verify no invisible automatic task completion.
3. Add typed `readable/writable`, `edible/perishable`, `instrument`, `craftable`, and `decorative` components to the same source graph, including a genuinely journal-bound object and chapter-specific book pages.
4. Provide deliberate, natural-language-to-grounded-command translation from the Doctor's self-generated intentions. Never claim the action happened until the actual material reducer commits it.
5. Give domestic objects distinct physical arrangements and aesthetic choices; measure physical state and decisions without assigning compulsory favorite activities.
6. Require coherent interleaving between HomeLife and new object authority with shared carrying/volume rules, historical replay, darkness, moving objects, restart and source tampering.

This work does not advance the 34 Articles of Artificiality engineering score or qualification. The next Article 8 test should ask whether *Pretorius* chooses, varies and revisits these affordances under an equally informed rule-controller comparison—not whether the test author can follow a predetermined scripted recipe.
