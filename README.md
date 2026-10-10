# Pretorius Laboratory

**An enduring place for experiments, not a disposable test fixture.**

Pretorius Laboratory is a standalone, low-cost Python/SQLite research habitat. Laboratory objects, experiments, snapshots and physical consequences persist independently of the model speaking for Pretorius and independently of Frankenstein Village.

This is **research software v0.1**, not a deployed Village location, a network-synchronized simulation or a replacement for Pretorius's cognitive system.

## One laboratory, two eventual representations

The authority is a persistent external laboratory ledger. A private research process interacts with the scene through typed operations; a future Evennia projection may present only explicitly approved, authenticated and Village-authorized effects. The offline copy produces provisional proposals, not a second source of world truth. For now, **only the local authority and offline rehearsal exist**.

An object retains its stable identity across reopening, snapshots, and restored backups. Experiments advance a local clock, and each accepted action creates an idempotent, revisioned, hash-chained record. Deterministic replay checks whether the live scene can actually be reconstructed from its declared history.

## Requirements and first run

Python 3.10 or newer. All runtime dependencies are in the standard library. Commands may be run directly from the cloned repository.

\`\`\`bash
python -m pretorius_lab --db data/laboratory.sqlite3 init
python -m pretorius_lab --db data/laboratory.sqlite3 status
python -m pretorius_lab --db data/laboratory.sqlite3 observe
python -m pretorius_lab --db data/laboratory.sqlite3 act open container:specimen
python -m pretorius_lab --db data/laboratory.sqlite3 act move specimen:alpha bench:main
python -m pretorius_lab --db data/laboratory.sqlite3 act advance_clock 12
python -m pretorius_lab --db data/laboratory.sqlite3 act note "A vessel opened; specimen transferred."
python -m pretorius_lab --db data/laboratory.sqlite3 checkpoint
python -m pretorius_lab --db data/laboratory.sqlite3 verify
\`\`\`

The read-only `observe` command provides a host-verified, machine-readable scene for future cognition adapters. A sealed container hides its contents until opened; notebook entries are never included in this perception payload. The observation includes a lab identity, world epoch, event cursor and provenance class, plus legal action examples computed by the authoritative physics reducer. An observation is not automatically a lived memory or a claim that Pretorius is present.

The same database can be reopened in the next session without reinitialization. The open/close, move, clock and notebook operations are constrained by fixed physical rules. There is no arbitrary state write verb.

## Precision spatial continuity (opt-in v2)

The original v0.1 host remains intact. A new, isolated spatial world prototype adds stable bookshelf coordinates, shelf slot ordinals, capacity-one occupancy, physical object condition and a persistent broken-beaker fixture. Its event-sourced SQLite file must be initialized separately; it is **not** a silent migration of an already-lived Pretorius history.

~~~bash
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 init
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 locate book:007
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 act break beaker:001
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 act collect beaker:001
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 act place beaker:001 floor:corner:nw
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 verify
~~~

On the next session the beaker remains broken in the northwest corner, and book:007 stays on the third shelf in the seventh position unless another accepted event moved it. Experiment forks receive a separate world epoch and cannot change their canonical parent. This is a discrete, precisely anchored physics model, not full rigid-body dynamics, locomotion or cognitive memory.

See [Spatial Habitat v2: exact world-anchored continuity](docs/SPATIAL_HABITAT_V2_AND_CONTINUITY_CONTRACT.md) for persistence invariants, source-monitoring, migration boundaries and proposed behavior tests.

## Perception is not privileged world knowledge

The laboratory stores millimetre-precise spatial anchors internally, but subject-facing room descriptions, shelf scans and object lookups **do not expose exact xyz coordinates**. The precise inspect-geometry command and status APIs are engineer-only debugging facilities. They must not be tools available to Pretorius. Instrument-based measurement is a separate future feature, not a reason to grant omniscient host metadata.

The opt-in world also has source-backed, permanently readable book editions and physical bookmarks stored in the same SQLite file under a separately replayable book ledger. Page content is immutable for a bound edition; absent pages cannot be improvised by the renderer. The included book is a three-page **synthetic test edition**, not a real historical book or an existing Pretorius memory.

~~~bash
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 init
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 install book:007 fixtures/DEMO_BOOK_007.json
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 open book:007
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 read book:007
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 mark book:007 ribbon
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 close book:007
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 open_mark book:007 ribbon
~~~

A separate observation receipt interface permanently records which qualitative room, object or shelf facts the research adapter actually returned. A receipt certifies an offered payload, not that Pretorius read or remembers it.

~~~bash
python -m pretorius_lab.observation_receipts --db data/sanctum-v2.sqlite3 init
python -m pretorius_lab.observation_receipts --db data/sanctum-v2.sqlite3 shelf shelf:3
python -m pretorius_lab.observation_receipts --db data/sanctum-v2.sqlite3 verify
~~~

These additions are available on existing spatial v2 databases without rewriting their physical genesis, event hashes or world epoch. Book installations, page turning, bookmark edits and observation offerings maintain separate append-only ledgers bound to that same physical world. They survive backups; a fork inherits its physical book states and pages, but not a claim that it witnessed its parent's past.

See [Knowledge boundary and persistent books](docs/KNOWLEDGE_BOUNDARY_AND_PERSISTENT_BOOKS_2026-10-10.md). The local actor labels are not network credentials, and the current simulation does not yet implement character reach, lighting, fine-grained object affordances, measured geometry or real cognitive habitation.

## Historical full-text bookshelf, and future Village shop link

The world is broadly situated in the **1890s**; an exact in-fiction calendar year is still pending Village keeper approval. Pretorius's future small, not-yet-open curiosity shop is the public face of a larger building whose interior contains his **permanent full research laboratory and sanctuary**. A future authenticated threshold may permit traversal from the lab simulation into Frankenstein Village and back. **That bridge is not yet implemented**, and neither the shop nor Pretorius has been activated in the game.

An initial seven-volume shelf of complete original pre-1891 works is now available as a reproducible, source-pinned corpus. It includes Cutter on anatomy, two volumes of William James's *Principles of Psychology*, Culpeper on herbal medicine, Scot on witchcraft, Frazer's **original 1890** *Golden Bough* volume I, and Stevenson's *Jekyll and Hyde*. The source files are pinned to individual Git commits and content hashes and assembled into a durable SQLite fixture by the separate [bookshelf acceptance workflow](.github/workflows/period-bookshelf.yml). The generated full-text SQLite artifact is retained by GitHub Actions for a limited period; the repository keeps the manifest/importer so the complete library can be rebuilt.

To install this corpus into a **new** opt-in v2 fixture:

~~~bash
python -m pretorius_lab.habitat_v2 --db data/period-shelf.sqlite3 init
python -m pretorius_lab.period_bookshelf --db data/period-shelf.sqlite3 --catalog corpus/victorian_bookshelf_v1.json --year 1890
python -m pretorius_lab.book_cli --db data/period-shelf.sqlite3 catalog
python -m pretorius_lab.book_cli --db data/period-shelf.sqlite3 open book:002
python -m pretorius_lab.book_cli --db data/period-shelf.sqlite3 read book:002
~~~

The install verifies each complete source's original byte size and immutable Git blob hash, removes modern Project Gutenberg wrapper text and stores the full content as sequential **digital reading leaves** (not original printed page numbers). A book may be reopened at a persistent physical bookmark. Retry of an *identical* source installation is idempotent and retains prior bookmarks; different previously owned editions are never overwritten.

See [The Victorian Library and Future Shop Threshold](docs/VICTORIAN_LIBRARY_AND_SHOP_THRESHOLD.md) for source/edition caveats, proposed character chronology and deferred traversal safeguards. A curated bibliography or successful network import does not mean Pretorius has acquired or read the books in an actual cognitive episode. All full-text tests are currently run on an independent synthetic v2 world.

## Esoteric Annex: ten more complete pre-1891 books

The first shelf now has an opt-in, permanent, **physical ten-book annex**, alongside the original seven titles on shelf three. The new ten are source-pinned complete public-domain works by Blavatsky (both volumes of *Isis Unveiled* and *The Key to Theosophy*), Walter Scott, Catherine Crowe (two books), Edward Bulwer-Lytton (three), and Cotton Mather. Themes include theosophy, witchcraft, mysticism, spiritualism, mesmeric fiction and skeptical historical inquiry. The works are primary texts, not assertions that their supernatural descriptions are physically true.

The annex uses an append-only physical-object ledger to add the new identities and exact shelf positions without rewriting the original spatial v2 event history or existing possessions. The combined fixture can hold **17 books with actual text** and retained reading bookmarks. See [Esoteric full-text annex](docs/ESOTERIC_ANNEX_FULLTEXT_2026-10-10.md) and [the source catalog](corpus/esoteric_annex_1890.json).

To build a *fresh* 17-volume lab, initialize a spatial v2 file, run the original Victorian bookshelf import, then run the additional esoteric import with the explicit flag \`--register-annex\`. The [esoteric bookshelf verification workflow](.github/workflows/esoteric-annex.yml) produces a full SQLite backup artifact; this is a synthetic research fixture rather than Pretorius's actual inhabited home.

## Position-gated subject access (opt-in)

A standalone, event-replayed **embodied laboratory port** now tracks an artificial research actor's durable location, separately from the objective world. A character at the sanctum threshold can see major room features but **cannot enumerate or read a distant shelf**. Walking via the central floor station to the shelf enables a local, source-backed book inspection; there are no default numerical coordinates, unearned page contents, or direct admin-state access. These coarse floor stations are a prototype reach policy, not yet continuous 3D locomotion or sightline physics.

The optional actor's go, look, and book actions have source-bound receipts, and its placement persists across application restart and verified backup. Book page actions are checked against both the current physical book position and actor position in the same SQLite transaction, preventing a book from being read remotely if it was moved elsewhere before the request. A separate experiment fork inherits pose, but not the parent's alleged lived observations.

~~~bash
python -m pretorius_lab.habitat_v2 --db data/embodied-fixture.sqlite3 init
python -m pretorius_lab.book_cli --db data/embodied-fixture.sqlite3 init
python -m pretorius_lab.book_cli --db data/embodied-fixture.sqlite3 install book:007 fixtures/DEMO_BOOK_007.json
python -m pretorius_lab.embodied_cli --db data/embodied-fixture.sqlite3 init
python -m pretorius_lab.embodied_cli --db data/embodied-fixture.sqlite3 look
python -m pretorius_lab.embodied_cli --db data/embodied-fixture.sqlite3 go station:center
python -m pretorius_lab.embodied_cli --db data/embodied-fixture.sqlite3 go station:shelf:3
python -m pretorius_lab.embodied_cli --db data/embodied-fixture.sqlite3 look
python -m pretorius_lab.embodied_cli --db data/embodied-fixture.sqlite3 book open book:007
python -m pretorius_lab.embodied_cli --db data/embodied-fixture.sqlite3 book read book:007
python -m pretorius_lab.embodied_cli --db data/embodied-fixture.sqlite3 verify
~~~

The source-backed 17-book test fixture is also compatible with this port (move to station:shelf:1 to approach its additional ten occult volumes). Direct world-status/BookLibrary CLI calls are **engineer-only** and remain privileged; do not expose them as subject tools. Local actor labels are not authenticated network identities, and offered pages are not proof of cognition.

See [Position-Gated Subject Access](docs/EMBODIED_SUBJECT_ACCESS_2026-10-10.md) for its event contract, limitations, restart/fork tests and next physical milestone: genuine pickup/holding/return of books with single-world occupancy.

## Offline episode and reconciliation

\`\`\`bash
python -m pretorius_lab --db data/laboratory.sqlite3 offline-start data/offline.json
python -m pretorius_lab --db data/laboratory.sqlite3 offline-stage data/offline.json advance_clock 5
python -m pretorius_lab --db data/laboratory.sqlite3 offline-state data/offline.json
python -m pretorius_lab --db data/laboratory.sqlite3 reconcile data/offline.json
\`\`\`

The offline episode remains a separate JSON branch. Its state is provisional. At reconciliation, changes to affected objects are checked against the current committed state, so a specimen vessel moved by another actor is **rejected as a conflict** rather than copied or overwritten. Nonoverlapping valid changes may be accepted locally. Multi-step dependent offline writes and conflicts requiring negotiation are deliberately not auto-merged.

For the conflict example:

\`\`\`bash
python examples/conflict_rehearsal.py
\`\`\`

## Checkpoints, recovery and testing

\`\`\`bash
python -m pretorius_lab --db data/laboratory.sqlite3 backup backups/laboratory-copy.sqlite3
python -m pretorius_lab restore backups/laboratory-copy.sqlite3 data/restored.sqlite3
python -m unittest discover -s tests -v
\`\`\`

The backup command uses SQLite's consistent online backup API and verifies the copied file by replay. Restoration creates a separate database and refuses to overwrite an existing path. Operators must copy backups off-host separately. There is no destructive reset operation.

## Scope and integration safeguards

The current CLI trusts its local operator. It has **no network authentication, cryptographic signatures, remote sync, Village bridge, public event publication, or third-party consent layer**. Every laboratory event is marked research-private. Do not expose this host or offline queue to untrusted network clients. A hash chain detects internal corruption but is not proof against a malicious filesystem operator.

The Doctor Lives remains responsible for Pretorius's identity and cognition. This environment must not silently fabricate first-person world memories from offline experiments. Frankenstein Village retains authority over players, masks, rooms, doors, consent and its event ledger. The existing dark leased shop with its OPENING SOON sign remains untouched. No user-facing room, automatic Pretorius arrival or invited-alpha scope change is implied.

See the [MMO persistence and living-habitat research note](docs/MMO_PERSISTENT_HABITAT_STUDY_2026-10-10.md) for the proposed sanctuary and experimental-chamber separation. See [Executable architecture and trust contract](docs/ARCHITECTURE.md), [The Doctor Lives tracking issue #46](https://github.com/Azimn/The-Doctor-Lives/issues/46), and [Frankenstein Village tracking issue #48](https://github.com/Azimn/frankenstein-village/issues/48).

The next step after this foundation is source-level parity with Stage 04, plus a rigorously authenticated and explicitly non-public shadow projection. Until that review, there is no claim of direct Stage 04 compatibility or synchronized game integration.
