# Pretorius's Victorian Library and the Future Shop Threshold

Status: research content implementation and future integration note, 2026-10-10. **No Frankenstein Village runtime, keeper canon, shop opening, player travel, cognition or production host change.** The currently implemented bookshelf is a *synthetic* lab-v2 fixture until a validated character/world migration exists.

## Timeline and building concept

Frankenstein Village's design decisions pin the setting broadly to the **1890s**, but repeatedly state that an exact civil year has not yet been decided. The liturgical/calendar simulation includes a local 1890 basis, which is not permission to silently declare 1890 the final Village date.

The user's intended character chronology is **immediately before the film's events**, while Pretorius has traveled to reconnect with **Henry** and has leased a small curiosity shop that is still closed with a **COMING SOON / OPENING SOON** sign. Within the future story, that shopfront is a small public-facing portion of the structure. The **full permanent laboratory and sanctuary extend behind and within the building**, including his personal bookshelves, working rooms, collections and experiment apparatus.

The user-approved future concept is **traversal both ways** between the full authoritative laboratory simulation and the Village's potentially more narrative presentation of that same building. This is a development intention, **not** an invitation to expose a public entrance now. The Village repository currently describes Victor Frankenstein as the absent narrative center, whereas the user's film-prologue note refers to Henry. Preserve that naming distinction as an unresolved canon check; do not silently rename the user character's intended correspondent or alter existing Village decisions.

No current decision grants Pretorius an avatar, active storefront, business trading, village timeline insertion, or keeper-authorized arrival.

## Seven candidate full-text shelf volumes

These are historically plausible **titles published no later than 1890**. Their plain-text source versions are commit-pinned GITenberg transcriptions backed by exact Git blob checksums. The corpus manifest lives at [victorian_bookshelf_v1.json](../corpus/victorian_bookshelf_v1.json). Each edition's full bytes can be installed into the existing book domain in a **new, explicitly opted-in** v2 lab file. The books remain ordinary persistent physical objects with named positions on the third shelf. Their actual pages become available only through successful source installation and admitted open/turn/read/bookmark actions.

| Slot | Book | Date / use | Source edition caveat |
| --- | --- | --- | --- |
| 1 | Calvin Cutter, *A Treatise on Anatomy, Physiology, and Hygiene*, revised | 1858; anatomy and medicine | Text-only transcription excludes engraved plates |
| 2 | William James, *The Principles of Psychology*, vol. I | 1890; attention, consciousness and memory | First volume of the two-volume work |
| 3 | William James, *The Principles of Psychology*, vol. II | 1890; habit, will and feeling | Complete second volume, not a shortened synopsis |
| 4 | Nicholas Culpeper, *The Complete Herbal* | Seventeenth-century core; materia medica and occult herbal lore | Digital edition includes later expansions; verify a physically plausible printed imprint before world-canon declaration |
| 5 | Reginald Scot, *The Discoverie of Witchcraft* | 1584 core; magical practices and skeptical examination | Digitized version names later editor Brinsley Nicholson, physical-edition imprint must be checked |
| 6 | James George Frazer, *The Golden Bough*, vol. I, *A Study in Comparative Religion* | **1890 original edition**, magic/anthropology | Do **not** substitute the later 1906–1915 3rd edition or 1922 abridgment |
| 7 | Robert Louis Stevenson, *Strange Case of Dr Jekyll and Mr Hyde* | 1886; identity, transformation and gothic fiction | Fiction, not scientific factual evidence |

The mixture intentionally reflects a researcher conversant with contemporary psychology, anatomy, older medical practice and historical magical traditions. A list of plausible titles does **not** establish that Pretorius has already acquired, handled or read any of them. The program may generate a fresh complete library as a test fixture only; historical acquisitions and familiarity belong to later character history/subject agency.

All selected original literary works are public domain in the United States, but **digital transcriptions and editorial material do not establish a specific historical physical edition**. Project Gutenberg's repository/license notices are removed from the *in-world reading text*, and the full source and checksum remain in the engineer bibliography/receipts. Never imply that digital text chunks equal printed pagination, engraved image plates or a faithful physical facsimile.

### Ingestion and physically persistent reading

With a **newly initialized** spatial v2 SQLite file, and a network connection to the source repository:

~~~bash
python -m pretorius_lab.habitat_v2 --db data/period-shelf.sqlite3 init
python -m pretorius_lab.period_bookshelf --db data/period-shelf.sqlite3 --catalog corpus/victorian_bookshelf_v1.json --year 1890
python -m pretorius_lab.book_cli --db data/period-shelf.sqlite3 catalog
python -m pretorius_lab.book_cli --db data/period-shelf.sqlite3 open book:002
python -m pretorius_lab.book_cli --db data/period-shelf.sqlite3 read book:002
python -m pretorius_lab.book_cli --db data/period-shelf.sqlite3 turn book:002 1
python -m pretorius_lab.book_cli --db data/period-shelf.sqlite3 mark book:002 reading-slip
python -m pretorius_lab.book_cli --db data/period-shelf.sqlite3 close book:002
python -m pretorius_lab.book_cli --db data/period-shelf.sqlite3 verify
~~~

The importer first downloads *every selected complete transcription* and verifies its declared byte length plus Git blob SHA against a commit-pinned source. It strips Project Gutenberg modern wrappers, partitions the original full text into deterministic bounded **digital leaves** without creating text, and rejects unknown wrappers or corrupted/missing sources. A book's main textual content is persisted in SQLite under an edition digest. The research host never invents a missing page from the title.

These leaves support reproducible page turning, but are **not original numbered paper leaves**. Future digitization with verified edition facsimiles and image plates can attach precise printed leaf IDs and figures without altering already accepted page observations.

**Important boundary:** The process will not overwrite any existing installed edition. The prior v0.1 and v2 laboratory databases must not be silently reinitialized or rewritten. Installing these complete titles is not a demonstration that Pretorius has encountered or remembers them.

### Automated full-content acceptance

The repository includes a dedicated GitHub Actions workflow to download and verify the **entire seven-work corpus** and build a disposable, replay-checked SQLite research fixture. A successful run archives the verified database backup, catalog and import report in a downloadable CI artifact. The generated fixture contains actual textual contents, not a list of URLs. It remains subject to GitHub artifact retention; permanent private world state will later require independent durable hosting/backups. The commit-pinned source manifest and deterministic importer remain in the repository for reproducibility.

## Future traversal contract, intentionally not implemented

The public shop and interior sanctuary are different **access and realism policies over a related building**, not necessarily mirror databases. The eventual player-facing storefront could be a compact Evennia room with colorful descriptions; the private full laboratory maintains precise authoritative physical facts. The design goal is that Pretorius can depart the sanctuary through a permitted threshold, inhabit the Village under its separate public canon rules, and return to the **same physical possessions and laboratory event history**.

Future bridge must settle identity + eligibility + actuation through a single confirmed travel transaction, a world/epoch-scoped location token, which authority owns carried objects, how story actions map to physical laboratory operations, clock correspondence, offline conflict handling, and clear consent/observer boundaries. Cross-world dual occupancy, duplicated books/items, retroactively witnessed events and unsupported LLM-invented state are unacceptable. A Village event can be represented in the lab **only if** authorized, mapped and accepted by the relevant world authority; descriptive prose alone cannot change the book location or its actual contents.

Until a separate approved game-development work order, the shop remains dark, Pretorius remains absent from Village launch, and the laboratory is the sole authority for its experimental contents. For now, prioritize a rich real-world substrate and book completeness, not a portal implementation.
