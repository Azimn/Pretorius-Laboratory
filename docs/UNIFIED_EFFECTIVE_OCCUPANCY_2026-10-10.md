# Unified Effective Occupancy After Book Custody

Status: implemented as an **additive placement-routing policy** for spatial-v2 laboratory worlds that have opted into BookCustody. Historical v2 and original annex event chains retain their exact bytes and replay rules. The work does not enable human cognition, continuous physical simulation, or Frankenstein Village integration.

## Problem reproduced

Before this milestone, taking \`book:007\` from \`shelf:3/slot:7\` made the shelf correctly appear vacant to the subject, but the immutable raw spatial-v2 fixture still reserved the slot as the original book's historical anchor. The older operator place command was rejected by the old reducer even if the real, current world had only a carried book and an empty shelf. A similar mismatch existed for direct annex book moves.

A laboratory has to distinguish **historical provenance** from **current physical occupancy**. Keeping historical events is correct; applying historic raw reservations to every later action is not.

## Resolved: one location policy for new accepted movements

Once the existing \`BookCustody\` tables are initialized, **new** trusted operator \`SpatialHabitat.commit({op: "place", object_id, anchor_id})\` requests and registered annex \`ShelfAnnex.move\` requests route through a shared physical-placement event type in the same *already existing custody ledger*. Its source is the combined original physical object registry, original append-only annex registry and previously accepted custody/location overlays. The result is a unique effective location for each supported physical object: vacant slot, carried by the actor, or placed on a single existing physical anchor.

A trusted operator can put the original \`beaker:001\` into a shelf slot the character has genuinely vacated, including a slot raw v2 still reserves for that now-carried book. This does **not** rewrite the old book genesis, introduce a second beaker, or collapse a real actor's hand with an occupied shelf.

The implementation closes the materialized-state race by checking current effective occupancy and accepting a transfer under **one SQLite \`BEGIN IMMEDIATE\` transaction**. An optional \`expected_placement_revision\` parameter on \`SpatialHabitat.commit\` and \`ShelfAnnex.move\` protects against stale physical-placement plans in the same SQLite transaction, independently of the old v2/annex revision. A stale expectation fails without changing the scene. An operator cannot relocate an object currently carried by the test actor; the actor must put it down first. Occupied surfaces reject placement. Idempotent event identifiers preserve the **historical accepted result** even if later movements occurred. The receiving domain is explicitly returned as \`effective_physical_placement\`; it has its own revision and hash cursor, and **does not increment** the original spatial-v2 or annex ledger revision. The current \`SpatialHabitat.verify()\` still proves historic raw events, while \`BookCustody.verify()\` proves the accepted current placements. Verified backups run both checks.

The subject's \`take\`/\`put\` book interface remains separate and position constrained. Ordinary operator placements have **no claim of subject agency, subject access, or memories**. The actor's local \`look\`, the engineer's \`locate\` and \`scan\`, and the existing BookLibrary source reading lookup use the effective object locations. No exact hidden millimeter coordinates leak to subject-facing observations.

### Reproducible previously failing example

On a **fresh test world** with installed books and the actor/custody ledger opted into the same SQLite database:

~~~text
actor at station:shelf:3
actor take book:007                  # original shelf 3, slot 7 becomes EMPTY
operator place beaker:001 shelf:3/slot:7
                                      # succeeds, consumes actually empty space
actor put book:007 shelf:3/slot:7   # fails; beaker really occupies the slot
operator place beaker:001 bench:main/position:left
actor put book:007 shelf:3/slot:7   # succeeds, same book identity and contents
~~~

The operator \`place\` syntax remains available as \`python -m pretorius_lab.habitat_v2 --db <path> act place <object> <anchor>\`; this command now returns a custody-domain event receipt when custody is initialized, rather than an old-format spatial-v2 \`committed_revision\` event. Consumers should key on the returned \`domain\` and \`event_hash\` instead of assuming all accepted actions increment the original v2 revision.

The dedicated complete **17-volume source-backed** GitHub Actions acceptance job now proves a real occult book's actual Gutenberg source text remains on a workbench while the beaker is moved into that volume's now-vacant original shelf spot. It captures the operator receipt, real empty-then-reoccupied shelf observations, persisted book reading receipt and verified SQLite backup. The smaller unit suite separately verifies replaying existing pre-custody raw events unchanged, idempotence, strict collision rejection, annex move parity, actor-scope denial and fork separation.

## Compatibility and remaining physical gaps

This is an additive **effective occupancy route**, not a migration of the original spatial ledger. The old v2 genesis still names its original book positions, and existing unmodified v2 historical event objects must continue to validate against those positions. The new location ledger overlays the current effective world; verify it before accepting real-world observations. Do not interpret raw \`status()["state"]["objects"]\` as current subject location when custody is on. That status is strictly an engineer-only historic lower layer.

Currently, brand-new **physical annex registrations** still pass the older raw anchor validation; the new movement unification does not automatically permit inserting newly created objects onto slots freed solely by custody. A future versioned registry admission/migration protocol must address this separately with cross-ledger replay, rather than silently weaken a source checksum or old replay invariant.

No mass, object volume, carrying capacity by weight, physical reach geometry, collisions with the character, line of sight, instrument-calibrated measurements, open book deformation, crumpled pages, dust, or mutable margin ink are claimed. These are future **measurable physical affordance** gates. Likewise, the existing world is still an independent synthetic laboratory and the actor is a trusted research test port; no real Pretorius cognitive memory assimilation or Village traversal was invoked.

The next substantive test should add source-verified per-object dimensions and weight, with explicitly bounded shelf and workbench slots and calibration metadata, then measure how capacity constraints change permitted actions. An engineer-only material register should never automatically become omniscient knowledge for Pretorius.
