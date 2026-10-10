# Spatial Habitat v2 and World-Anchored Continuity

Research engineering contract, October 10, 2026. This is an **opt-in v2 spatial authority**, not a silent conversion of the existing v0.1 laboratory or a deployment of Pretorius's cognitive runtime.

## Research requirement

Pretorius's remembered world and the host's physical world must be separate, independently checkable sources. If he breaks a beaker, gathers the fragments and puts them in a corner, the same object's physical condition, exact location and attributed history must survive interruptions and model changes. If book:007 sits at shelf:3/slot:7, a model that says otherwise is describing an incorrect fact about the host world, unless an accepted movement event intervened.

A reliable external world makes it possible to test how an artificial character reconciles its internal state with evidence that can corroborate or contradict memory. Persistent geometry does not demonstrate consciousness, first-person experience or autobiographical memory, but it removes the narrative generator's authority to invent contradictory physical facts.

## Implementation and strict upgrade boundary

The previous Laboratory v0.1 uses a fixed manifest and event chain with its own schema/ruleset digest. Modifying the manifest in place would invalidate that chain. The new SpatialHabitat authority lives in a separately initialized SQLite file, with spatial-habitat/2.0.0 schema and anchor-physics/1 ruleset. It is a **synthetic standalone successor fixture** until a verified v0.1-to-v2 migration, with an explicit history and provenance mapping, has been built. Never run v0.1 and v2 as competing authoritative instances of the same claimed home.

The v2 fixture defines exact spatial anchors with a stable semantic ID, containing room, parent furniture, ordinal placement, three integer millimetre coordinates and capacity. Shelf three contains ten explicit positions. Its seventh position (shelf:3/slot:7) has coordinates [1090, 300, 1900] mm. The synthetic object book:007 initially resides there. It is not located there because the assistant wrote an evocative description. Its physical location is an independently stored host fact.

Each object retains a stable ID and a revisioned record of type, name, anchor and condition. Beaker:001 begins intact on a bench. Breaking it changes its condition to broken and flags the remains scattered at the same anchor. A collection action gathers the broken remains as one aggregate. Only then may a placement action move the remains to floor:corner:nw. On restart, the object remains broken in that location. This aggregate-fragment rule is a limited physical abstraction, **not** simulated shard trajectories.

All action requests are typed and closed-grammar. Nonexistent objects and anchors, multiple occupants of a capacity-one anchor, unsupported break types and unauthorized state edits fail. Trusted placement currently permits moving between specified anchors without simulating a person's walking, reach, weight, impact dynamics or a continuous trajectory. Advanced physical semantics and path traversal are future experiments. The host can prove precise location and material condition, but must not claim it runs a general-purpose physics engine.

## Operate the exact spatial fixture

Initialize a new v2 world, using a fresh database path:

~~~bash
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 init
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 scan shelf:3
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 locate book:007
~~~

Break, gather and place beaker remains:

~~~bash
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 act break beaker:001
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 act collect beaker:001
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 act place beaker:001 floor:corner:nw
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 checkpoint
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 verify
~~~

A different session, process or model can reopen that same database:

~~~bash
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 locate beaker:001
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 scan shelf:3
~~~

The results depend on prior accepted mutations, not descriptive output style.

## What persistence and forks mean

Every accepted action and resulting world state are written in one SQLite transaction. Event IDs support duplicate-delivery safety. The hash-linked append-only event ledger records the lab/home/epoch identity, actor label, accepted revision, typed command, state digests, version identifiers and timestamp. A deterministic verifier rebuilds state from the genesis fixture and checks events, snapshots, final materialized state and cursor. Backups use SQLite's consistent online backup operation and preserve world identity and full history.

An experimental fork clones the verified scene with a new laboratory identity and world epoch, explicitly labeled sandbox and retaining a parent checkpoint reference. Destructive test actions in a sandbox cannot alter the canonical home. The fork has the same home association for lineage, but its results cannot silently become the residence's events or Pretorius's lived history. Those distinctions are essential for longitudinal experiments.

Local hash chaining checks consistency but does not authenticate a remote publisher or prevent a privileged filesystem editor from rewriting the complete ledger. Actor labels are trusted local names, not cryptographic identities. External signatures, independent immutable history checkpoints and actor permissions are unimplemented.

## Why external permanence matters for cognitive continuity

Personal continuity is not the same as merely returning the same words. A subject can expect an object to still be present, inspect the actual environment, discover it was moved, ask whether it remembers correctly and revise its beliefs. Such interactions provide a controlled way to study persistence, expectation, surprise, epistemic humility and source-aware memory updating.

Separate metrics for free recollection **before seeing the room** from accurate perception **after seeing the room**. A fresh model that reads the exact shelf address is retrieving a world fact; it has not demonstrated cross-session recollection. A model that initially misremembers and then corrects itself on admitted observation is displaying evidence-driven revision, not necessarily stable subject identity.

A possible 2-by-2 battery crosses accessible memory (retained versus withheld) with the external laboratory (unchanged versus host-authorized perturbation). Blindly score whether the character predicts locations before observation, detects mismatches, requests appropriate inspections, corrects beliefs without retrospective confabulation, and distinguishes truly observed events from reported ones. Include a stateless renderer control and a deliberately misleading narrative description to test reliance on authoritative physical state. None of those cognitive efficacy experiments has been performed in this patch.

## Relation to Frankenstein Village

Frankenstein Village remains a co-authored narrative system with a different world-resolution policy. Its Evennia process does not have to store each shelf, millimetre coordinate, or material condition in the same database. It may show an approved projection, possibly with more expressive prose. A versioned adapter can translate permissions and typed semantic events, and separately record the Village's accepted origin-event IDs.

The laboratory owns its physical objects; the Village owns its own rooms, doors, players, economy, time and consent. A lab event is not automatically a Village event, and a creative Village description is not automatically a laboratory state mutation. A remote mutation requires authentication, authority validation and a conflict check at the latest accepted lab revision. An offline or game-side narrative cannot rewrite historical facts or assert observations Pretorius never made.

The Village shop remains dark and Pretorius's arrival remains a separate canon decision. No Village bridge, production cognition, or remote synchronization code was changed.

## Next engineering gates

A verified migration from the original Laboratory v0.1 is needed before declaring v2 the definitive existing home. Subsequent controlled versions can add furniture and object authoring with durable IDs, experimental chamber isolation, weight and geometry constraints, multiple fragments and composition, illumination and occlusion, deterministic bounded physical experiments, object discovery from perspective, and eventual safe visitor interaction.

The permanence criterion is simple: changes must persist independently of narration, while a character may correctly remember, misremember or newly discover those physical facts. The software should make continuity testable, not declare the philosophical identity question resolved.
