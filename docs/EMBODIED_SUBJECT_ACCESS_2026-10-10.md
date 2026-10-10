# Position-Gated Subject Access: Laboratory Milestone v0.1

Implemented additive local research interface on top of SpatialHabitat v2. The original v0.1 host, immutable spatial world genesis, previous source-backed books, past accepted physical mutations, old bookshelf snapshots, and Frankenstein Village runtime are unchanged.

## Physical world ≠ actor knowledge

The physical world has facts its inhabitant may not know: exact anchored positions, object identities, book editions and content hashes, surface condition, room and event history. The research actor now has a **separately durable position** in this world. Its default starting station is the sanctum threshold. A subject-facing look from that threshold offers only the room's major recognizable features, not every item on all shelves. A look while standing at a particular shelf offers that shelf's visible contents and ordinal positions, without privileged millimetre coordinates or unrequested page text. A page can only be opened/read/turned/bookmarked when the actor is adjacent to **that book's current physical shelf**.

This *reduces unearned knowledge*. It does not create human vision or claim subjective consciousness. The local CLI uses a research actor label, not Pretorius's authenticated production cognition, and each receipt proves only that the local interface offered an action result or source data.

## Body state and movement contract

EmbodiedAccess (pretorius_lab/embodied_access.py) adds two world-epoch-bound SQLite tables: embodied_meta and embodied_events. No original SpatialHabitat event/snapshot record is rewritten. One registered subject, research-subject:pretorius, has an initial station and a replay-checked current station. Events have a stable idempotent ID, event revision, previous-event hash, source world cursor and independent physical-annex cursor. Read-only engineer world status and precise geometry continue to exist, but they are forbidden from the subject's tool interface.

The prototype's **discrete movement graph** has:
- a sanctum threshold adjoining the central floor station;
- central floor adjoining three shelves, the workbench, the two corner stations and the experimental chamber entry;
- the chamber entry adjoining its local table station.

Each move must follow an explicitly adjacent station. There is no teleport by supplying a shelf/object ID. The room transition is an internal prototype connection, **not** a doorway to Frankenstein Village. It is not yet a continuous locomotion model, with calibrated walking distance, collision-aware limbs, lighting, acoustic propagation, object blocking or stamina.

The only actual human-scale claim is **categorical reach gating**. At the center station, the interface may offer that the room includes bookshelves and a workbench, but it does not enumerate distant book spines or contents. At shelf 3, the source-backed visible titles of the original seven volumes are offered; at shelf 1, the ten real annex volumes are visible if source installed. A given shelf scan is not globally broadcast to the actor's memory. All sensory offers have an append-only receipt distinguished from actual cognition.

## Atomic actor–book proximity checks

The new EmbodiedAccess.book method is the subject entrypoint for existing BookLibrary verbs: open, close, read, turn, mark, unmark and open_mark. It does not create a second book content or book history system.

For a subject-scoped book action, BookLibrary performs the actual page/bookmark write and the access check **in the same SQLite BEGIN IMMEDIATE write transaction**:
1. Find the physical object in the existing spatial world or validated shelf-annex registry.
2. Determine the book's **current** physical shelf anchor, not where a remembered prior observation placed it.
3. Resolve the body's current station in the same SQLite database/world epoch.
4. Permit the mutation or read receipt only if the actor is at the physical shelf station.
5. Add a historical actor-pose receipt to the book event. Retrospective replays check the referenced embodied event hash and corresponding station; the main BookLibrary append-only hash chain remains independently verifiable.

If an operator moved a volume to another shelf after an earlier look, a new reading attempt at the abandoned position fails. If the actor is at the doorway or at a different shelf, a request to open or read the book fails and does not create a book event. The high-level port *never* hands the LLM the whole library's text by default.

The BookLibrary's preexisting engineer-only direct CLI and low-level Python interfaces remain trusted administrative tools without subject position gating. **Do not expose them** to character renderers or network callers. This is a research workflow, not a remotely authenticated containment boundary.

### Example from a fresh research fixture

    python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 init
    python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 init
    python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 install book:007 fixtures/DEMO_BOOK_007.json
    python -m pretorius_lab.embodied_cli --db data/sanctum-v2.sqlite3 init
    python -m pretorius_lab.embodied_cli --db data/sanctum-v2.sqlite3 look

At the threshold, the next command **must fail** with an explicit proximity error:

    python -m pretorius_lab.embodied_cli --db data/sanctum-v2.sqlite3 book read book:007

Walk through the center and approach the bookshelf, then physically interact at that location:

    python -m pretorius_lab.embodied_cli --db data/sanctum-v2.sqlite3 go station:center
    python -m pretorius_lab.embodied_cli --db data/sanctum-v2.sqlite3 go station:shelf:3
    python -m pretorius_lab.embodied_cli --db data/sanctum-v2.sqlite3 look
    python -m pretorius_lab.embodied_cli --db data/sanctum-v2.sqlite3 book open book:007
    python -m pretorius_lab.embodied_cli --db data/sanctum-v2.sqlite3 book read book:007
    python -m pretorius_lab.embodied_cli --db data/sanctum-v2.sqlite3 book turn book:007 --direction 1
    python -m pretorius_lab.embodied_cli --db data/sanctum-v2.sqlite3 book mark book:007 --bookmark paper-slip
    python -m pretorius_lab.embodied_cli --db data/sanctum-v2.sqlite3 verify

The same interface works with the ten occult annex volumes; the reader has to move to station:shelf:1 first. It continues after process restart with the **same** saved pose and world file. Verified SQLite backups include body history, books, source pages, bookmarks, local offered observations and original physical history. Sandbox forks inherit **position**, with a new epoch and parent-pose provenance, but not their parent's perception events as if they had just been lived.

## Testable research use

A straightforward preregistered controlled study can now separate:

- A subject predicting where a particular book should be **before** approaching the shelf, based on its own prior memory.
- Moving through the accepted laboratory stations, observing the real current shelf and receiving a host-grounded reading opportunity.
- Recording if a new admitted memory accurately changes a mistaken prior belief, preserves correct memories when the world is unchanged, or confabulates titles/text not physically accessible.
- A deliberately manipulated book relocation that only the engineer/host knows until the subject approaches that shelf.

All these comparisons require an actual attached cognitive renderer with a separately auditable accessed/remembered event. The present unit and CLI tests establish **physical access control, source consistency and durable positional replay**, not an improvement in character cognition or subjective awareness.

## Limitations and next physical work

The book is still modelled **at its shelf anchor**, with direct shelf-level access to page operations. There is no persistent hand/holding object, carrying a book to a desk, object transfer through doorways, reach geometry, standing height, occlusion by other objects, illumination, physically accurate page/leaf geometry, margins, erasures, torn pages, dust, handwriting or instrument-based measurement. These must be implemented as typed physical transactions, not as unverified prose; in particular, transferring a book to an actor's hands must remove its occupancy from the shelf and update all subject-visible observations in the same accepted world state.

The current world has one prototype actor, with no visitor, adversary, other occupant, authenticated remote session, live integration with The Doctor Lives or any Village travel. As elsewhere in the laboratory, local trust labels are not cryptographic authority, and replay hashes are audit consistency checks rather than tamperproofing from an administrator with filesystem access.

**Next engineering milestone:** add real physical holding/carried inventory and object transfer, preserving both the owner actor and the book's global spatial identity, then an instrument-measurement experiment. Avoid changing Village before that work is demonstrably stable.
