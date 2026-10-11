# Synthetic Mechanical Affordances for Pretorius Laboratory

**2026-10-10 research milestone.** Introduces an *optional immutable, world-epoch-bound* mechanical profile into the existing source-backed Pretorius Laboratory. No new cognitive architecture, production character action, published edition dimension claims, or Frankenstein Village integration.

## Physics contract, assumptions and epistemic boundary

The opt-in \`PhysicalAffordances\` profile adds dimensions (integer **millimetres**) and masses (integer **grams**) for the existing lab beaker and every book identity \`book:001\`–\`book:017\`. Its object profiles also declare \`source_class: synthetic_declared_not_measured\`. Shelf, bench and floor clearance classes specify three independent axis-aligned limits and a maximum supported mass. The single research actor has a maximum single-book carrying mass and an upper height limit for nearby object manipulation.

**These are engineering scenario values, not measured Victorian books.** A catalogued complete Gutenberg text does not authenticate that edition's binding thickness, physical mass, or engravings. There is no printed-edition or laboratory instrument provenance to justify exposing such data as a first-person observation. Numeric mechanical assumptions are engineer-only and do not flow through \`EmbodiedAccess.look\` or the source-backed book text interface.

The initial scenario uses the following values, with the full immutable source-labelled table in \`physical_affordances.BASE_PROFILE\`:

| Constraint | Synthetic value |
| --- | ---: |
| Normal physical research volume | 42 mm thick, 255 mm tall, 180 mm deep, 850 g |
| Two largest occult volumes (IDs 008–009) | 55 mm thick, 255 mm tall, 180 mm deep, 1,600 g |
| Beaker | 55 × 95 × 55 mm, 330 g |
| Shelf slot clearance | 60 × 300 × 255 mm, 2,400 g max |
| Workbench position clearance | 550 × 450 × 550 mm, 15,000 g max |
| Floor position clearance | 1,000 × 1,100 × 1,000 mm, 50,000 g max |
| Test actor's single-item carrying mass | 2,500 g maximum |
| Test actor's vertical manipulation height | 2,000 mm maximum |

Objects are compared without rotation against the destination's listed clearance; this is a deliberately limited first-pass bounding-box test, **not** real collision mechanics, exact individual shelf geometry, finite-element load modelling, friction, hand/grip modelling, weight distribution or posture. An exact synthetic anchor height is used by the host reach test, but not revealed through the subject's viewing port. Nearby movement remains a discrete station graph, rather than continuous locomotion.

The source-verified *text* of books remains completely separate from the numeric physical profile. There is no magical translation of document bytes into the reader's knowledge, and a remembered book location is not automatically synchronized with the actual room.

## Admission, immutability and enforcement

The operator first initializes the spatial-v2 habitat, persistent actor port and custody ledger. Activating a mechanical profile then checks **every currently present object's actual effective placement** for a fitting clearance class and every currently held object's mass. Existing unreachable, oversized, or overloading scenes are rejected on activation; they are never retroactively recast as physically possible.

Once activated, the profile is immutable within that world epoch. Every profile contains fixed schema, source class, exact object identities, dimensional quantities, anchor class limits and actor limits. Arbitrary booleans, floats, negative values, incomplete files, invented provenance classes or unknown unprofiled physical identities are rejected. The SQLite record has an auditable deterministic digest. Forks inherit the same profile bytes and checksum under their own new world epoch, retaining explicit parent-provenance metadata. Backups and recovery verify profile integrity and effective world placement.

\`BookCustody.act\` enforces the following checks in the SAME SQLite \`BEGIN IMMEDIATE\` transaction as a movement:
- **Take:** the actor must be at the object, its host-defined anchor height must not exceed declared reach, and its mass must not exceed declared carrying capacity.
- **Put:** the actor must be at a free destination, the anchor height must be reachable, the object's dimensions and mass must fit its clearance and support limit, and the actor must genuinely be holding that exact book.
- **Subject reading:** even when standing at the correct shelf station, the actor may not open, turn, read or mark a book above the declared manipulation height; if the same book is moved to a reachable shelf (or is already legitimately held), its unchanged source text becomes accessible.
- **Operator placement:** the object must not be held and the target must be unoccupied; target surface clearance and mass limits apply even for privileged engineering movements. Collected/broken glass rules remain separately enforced.
- **New annex registration:** if a mechanical profile is active, a new physical book must already have a valid, explicitly source-labelled profile, and it must fit its designated shelf or supported surface.

If the scenario's declared mass, width, height, depth or reach limit would be violated, the action returns an explicit error, does not create a custody event, and leaves the book in its previous position. The original v2 and shelf-annex event hashes remain unchanged. Newly accepted custody events include the digest of the exact mechanical assumption profile active at acceptance; replay checks that source reference when it is present. Events accepted **before activation** are not rewritten or relabelled as if these rules had been applied.

## Reproducible local workflow

For a *fresh* spatial v2 research fixture, install desired real text editions separately with the existing source-backed bookshelf importer, then initialize the actor, custody and mechanical profile. On a fixture with an impossible current placement, the mechanical initializer fails closed rather than overwriting the room.

~~~bash
python -m pretorius_lab.habitat_v2 --db data/physical-lab.sqlite3 init
python -m pretorius_lab.embodied_cli --db data/physical-lab.sqlite3 init
python -m pretorius_lab.embodied_cli --db data/physical-lab.sqlite3 init-custody
python -m pretorius_lab.affordance_cli --db data/physical-lab.sqlite3 init
python -m pretorius_lab.affordance_cli --db data/physical-lab.sqlite3 verify
# Privileged engineer-only diagnostics, NEVER expose to the character:
python -m pretorius_lab.affordance_cli --db data/physical-lab.sqlite3 inspect-engineer
python -m pretorius_lab.embodied_cli --db data/physical-lab.sqlite3 go station:center
python -m pretorius_lab.embodied_cli --db data/physical-lab.sqlite3 go station:shelf:3
python -m pretorius_lab.embodied_cli --db data/physical-lab.sqlite3 take book:007
python -m pretorius_lab.embodied_cli --db data/physical-lab.sqlite3 verify-custody
~~~

To test a different synthetic size or mass distribution, create a **separate new research world** and pass a strict JSON profile via the \`init --profile synthetic-fixture.json\` flag. A profile cannot be silently updated in a world that already has one. Never label a custom test file as a measured source without genuine provenance; this profile schema intentionally refuses that source class.

The full 17-work GitHub Actions integration builds actual source-verified complete Gutenberg text, creates the physical annex, activates synthetic mechanic limits, carries the genuine *Isis Unveiled* volume to the bench, reads a marked archival leaf, and places the beaker in the book's physically vacant shelf slot. It verifies the physical profile and stored world database both before and after recovery. **The action test is hosted by CI, not a living autonomous Pretorius.**

## Falsification and follow-up

The focused controlled acceptance tests make the rule operational: a 5 kg test book at the bench cannot be lifted under a 2.5 kg cap; a width-85 mm test book may be carried but may not enter a 60 mm shelf slot; a too-heavy book cannot be set down on a shelf rated below its declared mass; a high shelf cannot be manipulated under a lower vertical reach bound even though the actor can stand beside it. Operator relocations are subject to the same clearance rules. Unknown physical book ID registration is denied while the profile is active.

All values are synthetic. Therefore these results prove only that a *declared constraint is enforced*, not that a historically accurate binding, Victorian room, human body or gravitational environment has been measured. Future engineering should include actual instrument-based measurements under controlled uncertainty, an auditable actor-access gate for observed numbers, better orientation/collision semantics, and a source-based edition-to-binding provenance system. Real Pretorius cognition and persistent memories must be tested separately before any claims of behavioral benefit.
