# Subject-Controlled Apparatus: Direct Laboratory Physics

**Date:** October 12, 2026
**Scope:** Independent research simulation, no active Pretorius cognitive controller and no Village changes. Stacked on direct-world test PR #19.

## Proven need

The previous direct simulation passed, but clearing the bench required an engineer to teleport its beaker to a floor anchor. This is a simulation limitation, not an LLM limitation. A subject must be able to handle its own apparatus before it can complete simple bench tasks.

## Engineering change

The existing custody event ledger now accepts two distinctly typed operations, take_apparatus and put_apparatus, limited to the real, intact laboratory beaker. Historic book take/put event payloads remain unchanged and replay through their original reducer rules. The actor uses only EmbodiedAccess and the previously approved pose, mass, reach and surface authority. The beaker may be taken at its actual current station, carried along existing adjacent floor stations and placed on a free bench or floor. It may not be placed on a shelf or teleport to a remote station.

The hand capacity is shared across books and apparatus. If the actor carries either one, a second object cannot be picked up. The beaker ceases to occupy the bench while held, is visible in the held-object offer, and cannot be weighed while in hand. A physically broken beaker is not eligible for subject handling under this change.

Every accepted operation records its exact world epoch, physical cursor, accepted body pose, previous and resulting custody digests and source mechanical profile. Event IDs are idempotent; conflicting reuse is refused. Backups verify receipts and retain placement; sandbox forks copy current placement without inheriting a previous measurement as lived experience.

## Standalone validation

The model-free visit now requires no privileged beaker relocation. The actor weighs the beaker, takes it, attempts an illegal second pickup, transports it to the floor, fetches a book, measures the book on the newly free bench, then attempts to set the beaker onto the occupied book position. The final attempt must fail without altering either location or ledger revision. Recovery, fork isolation, beaker damage and provenance checks follow.

The dedicated apparatus tests exercise source-bound access, shared carrying capacity, surface collision, weight and reach, idempotent receipts, wrong object types, broken glass, backups, fork persistence and tamper refusal. The exact CI result is separate from this engineering design and must be reported from the real action run.

## Constraints

This is source-verifiable, discrete object handling, not continuous 3D physics, an articulated hand model, fluid simulation or a generalized object registration API. The fixture assumes synthetic mass and dimensions rather than historical measurement. All simulator actions are scripted by the test harness. Their success does not establish Pretorius cognition, autonomy, attention or first-person experience.

To repeat on Python 3.10+ with no downloaded model or paid APIs:

    python examples/direct_lab_session.py --output /tmp/model-free-apparatus

The output includes a directly scored JSON trace and isolated SQLite world, backup and fork artifacts.

## Verified execution evidence

The final exact-branch [direct session CI run 38212173978](https://github.com/Azimn/Pretorius-Laboratory/actions/runs/38212173978) completed all **23** trace stages, rejected all **8** deliberately invalid physical operations without changing accepted event revisions, and passed **9** final replay/backup/fork/measurement integrity checks. Its independent regression run completed **129/129** Python tests, including seven apparatus-specific test cases.

The crucial new result was the removal of the privileged engineer move from the subject's bench-clearing sequence. The subject actually picked up the measured beaker, carried it to the southeast corner, placed it down, handled the book on the newly available bench and then encountered a verified double-occupancy rejection when bringing the beaker back. The serialized trace, parent-world backup, fork and damage fixture were saved by GitHub Actions.

These results validate the specified discrete simulation mechanics on the tested scenarios, not the behavior of a learned or autonomous controller. The branch is a review candidate and has not been promoted into the canonical character or Village.
