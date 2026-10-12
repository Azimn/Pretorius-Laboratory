# Physical Book Handling: Persistent Custody v0.1

**Implementation scope:** standalone spatial-v2 research fixture only. No Frankenstein Village shop activation, no Pretorius cognitive integration and no edits to existing main-world historical event hashes.

## Problem and authority

Before this addition, book text, bookmarks and a body's station persisted, but a volume remained on its original shelf while the character supposedly carried it. That was an invalid physical model. `BookCustody` introduces an explicit, append-only SQLite location authority for **handled** books. Its event chain is tied to the laboratory ID and world epoch, the physical-world and physical-annex event cursors, and the actor's exact accepted station and event cursor.

Book identity and immutable source text remain in their original registries. Taking a book changes its **effective location** from a shelf or work surface to `held_by=research-subject:pretorius` and `anchor_id=null`. Putting the book down changes its location to an existing unoccupied anchor with `held_by=null`. At no time may the book simultaneously occupy a shelf and the actor's hands, or both the bench and a shelf. Only one volume can be carried by the test actor at once.

The original v2 manifest cannot be rewritten without invalidating accepted history. Custody therefore operates as a separately replay-verified overlay, **not** as a change to the original genetic fixture manifest. Every subject-facing shelf, room, locate and nearby-object view consults the effective location and omits an object being carried elsewhere. The actor's nearby observation now offers a separately identified carried book. The volume's full page text and bookmark remain the **same existing BookLibrary edition**, not copied into a fake pocket book.

## Supported operations

The actor must approach a book's currently effective physical surface and execute an accepted `take`. A book can then move with the actor along the existing discrete station graph, and subject-scoped page operations remain authorized while it is genuinely held. To set it down, the actor must move to the destination station and `put` it on a free, preexisting surface. A floor, shelf position or bench surface can hold only one object in this discrete model. The main workbench starts occupied by the physical beaker. The original v0.1 workflow used a privileged operator to move it, but the separate subject-controlled apparatus extension now permits the actor to take and carry that intact beaker to the floor. The same shared custody ledger enforces single-object capacity across beaker and books; this does not rewrite older book event schemas.

All custody changes are within one `BEGIN IMMEDIATE` SQLite transaction including the relevant actor and physical anchor check. Event-ID retries are idempotent. Disallowed distant pickup, remote drop, already-held book, second carried book, double occupancy and direct core/annex writes to custody-managed books fail closed. A subject page-reading event also records which physical custody history the interface used, permitting retrospective checks that a carried or relocated book was accessible.

World-state backups verify the custody ledger and retain the actor's current position, accepted book placement, source text and physical bookmarks. Experimental sandbox forks copy the **present** book location and body position into a separate epoch, but do not convert original historical sensory offers into new experiences for the fork.

## Example

The steps below deliberately initialize a **fresh, synthetic fixture**. Do not reinitialize a previously lived database.

```bash
python -m pretorius_lab.habitat_v2 --db data/handling-test.sqlite3 init
python -m pretorius_lab.book_cli --db data/handling-test.sqlite3 init
python -m pretorius_lab.book_cli --db data/handling-test.sqlite3 install book:007 fixtures/DEMO_BOOK_007.json
python -m pretorius_lab.embodied_cli --db data/handling-test.sqlite3 init
python -m pretorius_lab.embodied_cli --db data/handling-test.sqlite3 init-custody
python -m pretorius_lab.habitat_v2 --db data/handling-test.sqlite3 act place beaker:001 floor:corner:se
python -m pretorius_lab.embodied_cli --db data/handling-test.sqlite3 go station:center
python -m pretorius_lab.embodied_cli --db data/handling-test.sqlite3 go station:shelf:3
python -m pretorius_lab.embodied_cli --db data/handling-test.sqlite3 take book:007
python -m pretorius_lab.habitat_v2 --db data/handling-test.sqlite3 scan shelf:3
python -m pretorius_lab.embodied_cli --db data/handling-test.sqlite3 go station:center
python -m pretorius_lab.embodied_cli --db data/handling-test.sqlite3 go station:bench
python -m pretorius_lab.embodied_cli --db data/handling-test.sqlite3 put book:007 bench:main/position:left
python -m pretorius_lab.habitat_v2 --db data/handling-test.sqlite3 scan bench:main
python -m pretorius_lab.embodied_cli --db data/handling-test.sqlite3 book open book:007
python -m pretorius_lab.embodied_cli --db data/handling-test.sqlite3 book read book:007
python -m pretorius_lab.embodied_cli --db data/handling-test.sqlite3 verify-custody
```

The CI test suite includes deliberate book relocation while held, main-world persistence, source-bound reading from the hands or workbench, duplicate action identifiers, occupied surface refusal, tamper detection, annex-book handling, recovery, and independent forks. The complete seventeen-volume acceptance workflow also tests removing the actual stored public-domain text of *Isis Unveiled* from its first shelf, carrying it to a cleared bench, reopening at its real bookmark and reading the same source text at the bench.

## Remaining limitations and next step

This is **discrete occupancy**, not rigid-body mechanics. Grasp position, hand capacity in physical units, posture, weight, objects obstructing the path, open-book movement, wear and tear, dust, page damage, lighting, sensory uncertainty, temperature, and accurate instrument measurements are not yet simulated. **Subsequent compatibility update:** The original fixture retains its old raw book anchor as historical provenance, but new trusted operator/annex **movements** in a custody-enabled world now route through effective occupancy. A book's vacated shelf slot can receive the beaker without rewriting the old world events. **Registering newly invented objects** into locations reserved by an old raw object still requires a separate versioned registration protocol. See [Unified Effective Occupancy](UNIFIED_EFFECTIVE_OCCUPANCY_2026-10-10.md).

The local actor label is not a credential and read receipts are not proof of subject attention or autobiographical recollection. No agent was demonstrated to autonomously decide to move or read any book. Source-oriented controlled cognitive tests must still measure a character's beliefs **before** it discovers that another actor moved a physical object.

Future work should finish unifying **new object registration** without changing historical event hashes; then add hands/realistic object dimensions and source-grounded instrumental measurements. The shop in Frankenstein Village and two-way travel remain deferred until the lab can be reliably inhabited.
## Subsequent subject-controlled apparatus extension

The independent direct session now performs beaker transfer using the subject-facing take-apparatus and put-apparatus commands. The beaker cannot be weighed while held, placed remotely, dropped onto an occupied bench, or carried at the same time as a book. Broken beakers remain out of scope for subject pickup. The original book take/put events retain their historical payload schemas. See [Subject-Controlled Apparatus](SUBJECT_APPARATUS_CUSTODY_2026-10-12.md) for the tested scope and [direct CI run 38212173978](https://github.com/Azimn/Pretorius-Laboratory/actions/runs/38212173978) for 23 accepted/rejected trace stages and 129 passing regressions.
