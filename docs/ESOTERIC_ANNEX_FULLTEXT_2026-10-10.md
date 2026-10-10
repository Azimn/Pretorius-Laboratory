# Pretorius Laboratory: Esoteric Annex (1890 Fixture)

**Scope:** ten additional complete historic texts installed in a discrete, source-backed laboratory fixture. This does not change Frankenstein Village, Pretorius's memories or the closed curiosity shop.

## Contents

All ten source texts were composed or published before 1891, though particular transcriptions and later editions must not be mistaken for first printing facsimiles. The archival source identifiers, fixed Git commit, file byte length and Git blob checksum are in [the esoteric source manifest](../corpus/esoteric_annex_1890.json).

| Shelf 1 position | Author and title | Original work date |
| --- | --- | --- |
| 1 | H. P. Blavatsky, Isis Unveiled, Volume I: Science | 1877 |
| 2 | H. P. Blavatsky, Isis Unveiled, Volume II: Theology | 1877 |
| 3 | H. P. Blavatsky, The Key to Theosophy | 1889 |
| 4 | Walter Scott, Letters on Demonology and Witchcraft | 1830 |
| 5 | Catherine Crowe, The Night Side of Nature | 1848 |
| 6 | Edward Bulwer-Lytton, Zanoni | 1842 |
| 7 | Edward Bulwer-Lytton, A Strange Story | 1862 |
| 8 | Cotton Mather, The Wonders of the Invisible World | 1693 |
| 9 | Edward Bulwer-Lytton, The Coming Race | 1871 |
| 10 | Catherine Crowe, Ghosts and Family Legends | 1859 |

This gives Pretorius sources on occult philosophy, Victorian spiritualism, witchcraft and superstition, as well as skepticism and occult-themed fiction. The books describe historical beliefs or imagined events. Their appearance on the shelf does not make supernatural claims part of the laboratory's laws of physics.

## A physical shelf, not merely hyperlinks

The original seven books stay in the seven positions of shelf three. The ten new physical books have distinct persistent identities book:008 through book:017, registered into the previously empty first-shelf anchors with an additional append-only and replay-verified spatial annex. This adds known physical objects without changing the original laboratory manifest digest, identity, existing events, snapshots or original seven books.

The annex validates full source provenance and occupancy, rejects conflicting placements, supports moving an existing registered book to a different vacant anchor, and preserves object identity through restart, backup and experimental forks. Book content and physical bookmarks remain attached to that object's identity in the existing source-backed book ledger. Qualitative shelf observations show visible book titles but never disclose precise internal measurements or unread page contents.

## Source ingestion

Each GITenberg source is pinned by commit and Git blob SHA-1. The importer validates complete byte length, source hash and Gutenberg start/end markers, strips digital-distribution wrapping, and stores all remaining actual text in bounded deterministic digital reading segments. Some early Gutenberg files have older character encodings; the decoder preserves verification of original source bytes and uses an explicit deterministic codec fallback. Digital segments are not the paper pagination of a verified historical edition. No illustrations, engraved occult diagrams or printed-leaf numbering are claimed to have been reconstructed.

Work date is checked against the explicitly selected 1890 fixture year. An older text published in a later English translation is not admissible simply because the original work is old. For example, Waite's English translation of Eliphas Levi's Transcendental Magic came out in **1896**, so it is not quietly added to this 1890 shelf. The Mathers Abramelin publication from **1898** and Crowley's 1904 Goetia edition are likewise not used as if already available.

A hypothetical historical research library may contain competing explanations: theosophy, spirit reports, literary speculation, skeptical analysis and church-based witch trial narratives. None is endorsed as science by the simulator.

## Rebuild the full collection

Initialize a fresh isolated spatial-v2 test world, import the initial seven books, then import the esoteric annex with an explicit request to register missing physical books:

    python -m pretorius_lab.habitat_v2 --db data/esoteric-home.sqlite3 init
    python -m pretorius_lab.period_bookshelf --db data/esoteric-home.sqlite3 --catalog corpus/victorian_bookshelf_v1.json --year 1890
    python -m pretorius_lab.period_bookshelf --db data/esoteric-home.sqlite3 --catalog corpus/esoteric_annex_1890.json --year 1890 --register-annex
    python -m pretorius_lab.habitat_v2 --db data/esoteric-home.sqlite3 scan shelf:1
    python -m pretorius_lab.book_cli --db data/esoteric-home.sqlite3 catalog
    python -m pretorius_lab.book_cli --db data/esoteric-home.sqlite3 open book:008
    python -m pretorius_lab.book_cli --db data/esoteric-home.sqlite3 read book:008

Repeated imports of identical content are idempotent; installations that conflict with the existing physical placement or with a different personal book edition are rejected. The dedicated esoteric-annex GitHub Actions workflow downloads and verifies all 17 complete texts, checks occupied shelf positions, verifies the persisted database and uploads the full-text SQLite backup, import receipts and visible shelf scans as a downloadable research artifact.

Neither this build nor a research CLI session proves Pretorius entered the room, acquired the books or read them. A future genuinely embodied agent must earn access through movement, reach and observation. The upcoming shop-to-Village traversal remains separate and deferred.
