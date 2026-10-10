# Laboratory Knowledge Boundary and Persistent Books v0.1

**Implemented research interfaces, 2026-10-10.** This is an additive capability for the opt-in SpatialHabitat v2 fixture. It does not change the prior physical schema/manifest or rewrite historical events. Pretorius's production cognition, Frankenstein Village and the unopened shop remain unchanged.

## Governing principle

**The world knows more than its inhabitant.** Exact shelf geometry, coordinates, object conditions and content provenance belong to the physical host. A subject does not automatically know them. It may encounter an object, examine its placement, read a page or eventually make a measurement using an instrument. Only admitted interactions should become candidates for its own experience and memory. A renderer must not be handed administrative SQLite state and asked to pretend it discovered it.

A remembered belief can be wrong while the host's accepted world state remains unchanged. Equally, an event performed while Pretorius was inactive must not be described as something he personally witnessed. World facts, offered perceptual information, subject-admitted observations, remembered episodes, inferences and hearsay are different kinds of evidence.

The qualitative spatial interface now reports a book's shelf, slot and condition without unearned millimetre coordinates. A separate **engineering-only** inspect_object/inspect-geometry endpoint retains exact host geometry for integrity testing. The debug status API also remains administrator-only. Never add those engineering endpoints to the subject's tools. The visible observer methods in habitat_v2 are diagnostic previews; the audit port below is the preferred adapter entrypoint for offered observations.

## Actual source-backed books

Physical book identity and source text are distinct. A fixture book is an actual persistent *world object* with stable location and condition, but it cannot be read beyond its real installed pages. Installing an authorized edition attaches a bounded ordered sequence of immutable UTF-8 page strings with an edition ID, title, author, declared source/rights class, source reference and content digest.

The edition is stored in an additional **world-bound book ledger** inside the SAME SQLite database, scoped to lab ID and world epoch. The older physical ledger remains intact, so previously accepted location events retain their original hashes. The book ledger records installation, opening, page turns, page-read offers, inserting and removing physical bookmarks, closing and reopening directly at an inserted bookmark. Bookmarks and pages persist across restart, and a fork copies the selected book state into its independent sandbox epoch. The canonical home cannot be changed by reading a cloned experimental book.

This is actual stored page text, not an LLM improvising from a title. The current demonstration edition is only three short original research-fixture pages. All other fixture books remain unreadable until a source-backed edition is installed. The system can accept multi-page books for any existing physical book ID, but is not yet a comprehensive digital library, catalog ingestion pipeline or document parser. The operator-supplied source/rights label is not independently verified. Real book imports need source review and page-boundary/edition consistency checks.

Page-read events certify only that the local interface **offered** the stored page bytes with a bound edition digest. They do not prove the model processed the text, understood it or formed a memory. A physical bookmark marks a page inside that particular edition and its placement is durable even if the character later forgets why it is there.

## Reading and bookmark workflow

Initialize a new spatial fixture. Never run init over an existing database:

~~~bash
python -m pretorius_lab.habitat_v2 --db data/sanctum-v2.sqlite3 init
~~~

Initialize the optional book domain, then load the explicitly synthetic sample edition:

~~~bash
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 init
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 install book:007 fixtures/DEMO_BOOK_007.json
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 open book:007
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 read book:007
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 turn book:007 1
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 mark book:007 blue-ribbon
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 close book:007
~~~

On a later session, reopen the **same SQLite file**, turn directly to the existing paper slip and receive the stored page text:

~~~bash
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 open_mark book:007 blue-ribbon
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 read book:007
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 catalog book:007
python -m pretorius_lab.book_cli --db data/sanctum-v2.sqlite3 verify
~~~

A book's physical relocation remains a world-object event handled by SpatialHabitat. The current book port does **not** yet simulate hands, reach, line of sight, cover handling, page tearing, ink marks, moisture, paper aging, or reading while physically standing elsewhere. It is a small bounded document-object interaction mechanism, not a blanket claim of human-scale physics.

## Every offered observation has provenance

A second additive ledger, ObservationPort, stores event-ID-deduplicated, world-epoch-bound records of **the specific qualitative information offered to an interface**. An offered room scene, shelf scan or object examination records the returned payload, the physical world revision and event cursor, timestamp, actor interface label and a hash-linked receipt. Replays verify the receipt payload digest and that its source physical event cursor genuinely existed.

~~~bash
python -m pretorius_lab.observation_receipts --db data/sanctum-v2.sqlite3 init
python -m pretorius_lab.observation_receipts --db data/sanctum-v2.sqlite3 room room:sanctum
python -m pretorius_lab.observation_receipts --db data/sanctum-v2.sqlite3 shelf shelf:3
python -m pretorius_lab.observation_receipts --db data/sanctum-v2.sqlite3 object book:007
python -m pretorius_lab.observation_receipts --db data/sanctum-v2.sqlite3 verify
~~~

This records **information offered**, not confirmed subjective witnessing. If Pretorius's process is not attached, the local CLI's actor label is only a test stand-in. An eventual The Doctor Lives adapter must bind a real subject run ID, render admission outcome and actually consumed source extent to a separately verified memory event. Never equate a returned JSON payload or API call with a lived memory.

The observation ledger is separate from world mutations because looking is generally not a physical change. It still shares the same SQLite file and world epoch. Physical action events, book reading events and offered observations are all preserved in their respective auditable ledgers. Backups verify all installed ledgers. New sandbox forks receive book texts and physical bookmark state, but **not the parent session's observation receipts as alleged fresh observations**.

## Knowledge versus geometry

The host may use a hidden coordinate to determine which shelf is above another or whether an object can fit in a place. That does not make the numeric value available to the subject. A shelf glance may show ordinal order and visible bindings. Specific sizes/distances will require future **measurement actions** with equipment calibration, physical access and uncertainty reporting. No such measuring tool is implemented yet. A textual spatial descriptor may still be more than a realistic eye could know from a doorway, so the next perceptual milestone is position, reach, lighting and occlusion testing.

The phrase "the seventh book over" is permitted only after an interaction that exposes shelf ordering or an earlier admitted observation/remembered fact. A direct administrator look-up would be invalid evidence of free autobiographical recall. Also, "book on third shelf" is not the same measurement as "book exactly 1090 mm from a reference point."

## Integrity scope and remaining limitations

The two new ledgers are tamper-evident **against unintended local corruption** via hashes and reconstruction. They are not remotely signed, protected from a privileged filesystem operator or network-authenticated. Book source provenance labels are asserted by the installer. The current local CLI actor allowlist does not establish that Pretorius was the requester.

Full realism requires future object creation/removal, material composition and degradation, physically constrained reach/handling and line of sight, illumination, noise, temperature, instrument measurements, authored/edited document contents, per-actor permissions and durable experiment scheduler operations. Each new feature should have a versioned contract, test fixtures, controlled migration and failure-mode coverage. An infinity of uninstantiated room details need not be materialized, but anything the host establishes through an accepted observation or action must be consistent, reproducible and recoverable.

**Research discipline:** Track what the host knows, what the interface offered, what a subject demonstrably accessed, what it later reports remembering and what changed in the world. These separate ledgers allow us to measure the mismatch rather than manufacture agreement.

## Compatibility with Frankenstein Village

Laboratory physical truth and experimental observations take priority here. Any later Village representation can be more narrative and lower-resolution, using a versioned, authorized projection of selected objects and events. It need not copy books' full texts, private bookmarks, instrument geometry, test-run traces or even the laboratory database engine. The Village cannot authoritatively change an object by composing prose; a mapped typed action must be accepted by the laboratory authority, with origin, version and consent checks. No cross-world adapter or canon opening is introduced in this implementation.
