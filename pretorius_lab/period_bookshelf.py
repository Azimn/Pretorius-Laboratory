"""Import verified complete pre-1900 public-domain texts into a persistent bookshelf.

The bibliography is an operator-reviewed proposal. The installer checks original
source bytes against Git's content hash and never hallucinates absent text.
It preserves the v2 physical event chain and refuses to replace installed books.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request

from .book_library import BookLibrary
from .habitat_v2 import SpatialHabitat
from .physics import Conflict, LabError, digest

CORPUS_SCHEMA = "victorian-bookshelf-corpus/1"
SOURCE_MAX_BYTES = 12_000_000
SEGMENT_SIZE = 7600
GUTENBERG_START = re.compile(
    r"(?im)^\*{3}\s*START OF (?:THIS|THE) PROJECT GUTENBERG EBOOK\b[\s\S]{0,500}?\*{3}\s*$"
)
GUTENBERG_END = re.compile(
    r"(?im)^\*{3}\s*END OF (?:THIS|THE) PROJECT GUTENBERG EBOOK\b[\s\S]{0,500}?\*{3}\s*$"
)


def git_blob_digest(payload: bytes) -> str:
    header = b"blob " + str(len(payload)).encode("ascii") + b"\x00"
    return hashlib.sha1(header + payload).hexdigest()


def genuine_text(blob: bytes) -> str:
    """Remove ebook distribution wrapping, never invent or summarize words."""
    text = blob.decode("utf-8-sig")
    start, end = GUTENBERG_START.search(text), GUTENBERG_END.search(text)
    if not start or not end or start.end() >= end.start():
        raise LabError("Unknown Gutenberg wrapper; refuse to invent book boundaries")
    body = text[start.end():end.start()].replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(body) < 2000:
        raise LabError("Book text unexpectedly short or truncated")
    return body


def digital_leaves(text: str) -> list[str]:
    """Deterministic UTF-8 text segments; NOT original print pagination."""
    pieces = []
    while text:
        if len(text) <= SEGMENT_SIZE:
            pieces.append(text)
            break
        boundary = text.rfind("\n", SEGMENT_SIZE // 2, SEGMENT_SIZE + 1)
        if boundary < 0:
            boundary = text.rfind(" ", SEGMENT_SIZE // 2, SEGMENT_SIZE + 1)
        if boundary < 0:
            boundary = SEGMENT_SIZE
        else:
            boundary += 1
        segment, text = text[:boundary], text[boundary:]
        if not segment.strip():
            raise LabError("Invalid empty digital leaf")
        pieces.append(segment)
    if not 1 <= len(pieces) <= 10000 or any(not p.strip() or len(p) > 12000 for p in pieces):
        raise LabError("Book is incompatible with bounded storage")
    return pieces


def validate_entry(entry: dict, *, setting_year: int) -> None:
    fields = {"book_id", "anchor_id", "title", "author", "first_publication_year",
              "subject", "source_repository", "source_commit", "source_file",
              "source_bytes", "source_git_blob_sha1", "edition_note", "gutenberg_url", "status"}
    if not isinstance(entry, dict) or set(entry) != fields:
        raise LabError("Unrecognized bibliography entry")
    if not re.fullmatch(r"book:\d{3}", entry["book_id"]):
        raise LabError("Unknown physical book slot ID")
    if type(entry["first_publication_year"]) is not int or entry["first_publication_year"] > setting_year:
        raise LabError("A text is newer than the chosen in-universe year")
    if (not entry["source_repository"].startswith("GITenberg/") or
            not re.fullmatch(r"[0-9a-f]{40}", entry["source_commit"]) or
            not re.fullmatch(r"[0-9a-f]{40}", entry["source_git_blob_sha1"]) or
            not re.fullmatch(r"[0-9A-Za-z._-]+\.txt", entry["source_file"]) or
            type(entry["source_bytes"]) is not int or
            not 10000 < entry["source_bytes"] <= SOURCE_MAX_BYTES):
        raise LabError("Unpinned or malformed source file")
    if not entry["gutenberg_url"].startswith("https://www.gutenberg.org/ebooks/"):
        raise LabError("Missing source bibliography URL")


def read_source(entry: dict) -> bytes:
    repo = entry["source_repository"]
    url = (f"https://raw.githubusercontent.com/{repo}/"
           f"{entry['source_commit']}/{entry['source_file']}")
    with urllib.request.urlopen(
        urllib.request.Request(url, headers={
            "User-Agent": "Pretorius-Laboratory-source-verified-import/1"
        }), timeout=50,
    ) as response:
        payload = response.read(SOURCE_MAX_BYTES + 1)
    if len(payload) != entry["source_bytes"] or len(payload) > SOURCE_MAX_BYTES:
        raise Conflict("Downloaded source byte length differs from pinned edition")
    if git_blob_digest(payload) != entry["source_git_blob_sha1"]:
        raise Conflict("Downloaded bytes do not match pinned Git blob")
    return payload


def import_collection(habitat: SpatialHabitat, bibliography: dict,
                      *, setting_year: int = 1890, fetcher=read_source,
                      dry_run: bool = False, register_annex: bool = False) -> dict:
    if not isinstance(bibliography, dict) or bibliography.get("schema") != CORPUS_SCHEMA:
        raise LabError("Unsupported bookshelf catalog format")
    if type(setting_year) is not int or not 1890 <= setting_year <= 1899:
        raise LabError("The Village's setting is broadly the 1890s, exact year unapproved")
    entries = bibliography.get("entries")
    if not isinstance(entries, list) or not entries:
        raise LabError("Empty bookshelf proposal")
    if len({v["book_id"] for v in entries}) != len(entries):
        raise Conflict("Duplicate physical volume in bibliography")
    for entry in entries:
        validate_entry(entry, setting_year=setting_year)
    host = habitat._verified_status()
    if host["mode"] != "canonical":
        raise Conflict("Install period bookshelf into an explicitly selected canonical fixture only")
    from .shelf_annex import physical_book_objects, ShelfAnnex
    original = physical_book_objects(habitat)
    missing = []
    for entry in entries:
        obj = original.get(entry["book_id"])
        if obj is None and register_annex:
            if entry["anchor_id"] not in host["state"]["anchors"]:
                raise Conflict("Unknown shelf address")
            if any(v["anchor_id"] == entry["anchor_id"] for v in original.values()):
                raise Conflict("Shelf position is already physically occupied")
            missing.append(entry)
        elif not obj or obj["kind"] != "book" or obj["anchor_id"] != entry["anchor_id"]:
            raise Conflict("Physical shelf and bibliography disagree")
    lib = BookLibrary(habitat)
    # The catalog is append-only. No book is overwritten by this process.
    try:
        lib.verify()
    except LabError as exc:
        if "not initialized" not in str(exc):
            raise
        if not dry_run:
            lib.initialize()
    # Download and validate every text before changing a single book record.
    prepared = []
    for entry in entries:
        raw = fetcher(entry)
        if len(raw) != entry["source_bytes"] or git_blob_digest(raw) != entry["source_git_blob_sha1"]:
            raise Conflict("Source mismatch before import")
        pages = digital_leaves(genuine_text(raw))
        prepared.append((entry, pages, hashlib.sha256(raw).hexdigest()))
    if dry_run:
        return {"validated": len(prepared), "installed": 0,
                "would_register_physical": len(missing),
                "source_bytes": sum(entry["source_bytes"] for entry, _, _ in prepared),
                "digital_segments": sum(len(p) for _, p, _ in prepared)}
    prior = lib.catalog()
    # Validate all preexisting slots before *any* new write. An interrupted
    # identical corpus import may resume; a personally owned different
    # book never gets replaced.
    with habitat._open() as db:
        records = db.execute("SELECT value FROM books_meta WHERE key='books'").fetchone()
        installed = json.loads(records[0]) if records else {}
    for entry, pages, source_sha256 in prepared:
        old = installed.get(entry["book_id"])
        if old is not None:
            expected_id = f"gutenberg-{entry['gutenberg_url'].split('/')[-1]}-source-v1"
            if (old["edition"]["edition_id"] != expected_id or
                    old["edition"]["pages"] != pages or
                    old["edition"]["title"] != entry["title"][:250]):
                raise Conflict("Existing personal book differs from pinned corpus: "
                               + entry["book_id"])
    # Register persistent actual book objects only after every source and
    # preexisting edition is validated. Never silently revise core genesis.
    if missing:
        annex = ShelfAnnex(habitat)
        annex.initialize()
        for entry in missing:
            annex.register(entry["book_id"], entry["anchor_id"], entry["title"],
                           event_id="period-physical-" + entry["book_id"].replace(":", "-"))
        annex.verify()
    results = []
    for entry, pages, source_sha256 in prepared:
        book_id = entry["book_id"]
        if book_id in prior:
            results.append({"book_id": book_id, "title": entry["title"],
                            "digital_segments": len(pages), "sha256": source_sha256,
                            "source_bytes": entry["source_bytes"],
                            "result": "identical_previously_installed"})
            continue
        reference = (
            f"{entry['gutenberg_url']} | "
            f"{entry['source_repository']}@{entry['source_commit']}/"
            f"{entry['source_file']} | full-source-sha256:{source_sha256}"
        )
        # Existing BookLibrary metadata source_reference has a bounded field.
        # Keep the immutable Git source address in the bibliography and
        # the shortened Gutenberg reference plus verified digest in the ledger.
        if len(reference) > 250:
            reference = f"{entry['gutenberg_url']} | sha256:{source_sha256}"
        lib.install(
            book_id, edition_id=f"gutenberg-{entry['gutenberg_url'].split('/')[-1]}-source-v1",
            title=entry["title"][:250], author=entry["author"][:250],
            pages=pages, source_class="public_domain_verified",
            source_reference=reference,
            event_id=f"period-shelf-source-{book_id.replace(':', '-')}-v1",
        )
        results.append({"book_id": book_id, "title": entry["title"],
                        "digital_segments": len(pages), "sha256": source_sha256,
                        "source_bytes": entry["source_bytes"],
                        "result": "installed"})
    lib.verify()
    return {"installed": sum(v["result"] == "installed" for v in results),
            "already_present": sum(v["result"] == "identical_previously_installed" for v in results),
            "books": results,
            "shelf_digest": digest(results), "lab_id": host["lab_id"],
            "world_epoch": host["world_epoch"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Install a historically curated full-text laboratory shelf")
    parser.add_argument("--db", required=True, help="A preinitialized v2 SQLite file")
    parser.add_argument("--catalog", default="corpus/victorian_bookshelf_v1.json")
    parser.add_argument("--year", type=int, default=1890)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--register-annex", action="store_true",
                        help="Add missing physical book objects in available anchors")
    args = parser.parse_args(argv)
    try:
        bibliography = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
        outcome = import_collection(
            SpatialHabitat(args.db), bibliography,
            setting_year=args.year, dry_run=args.dry_run,
            register_annex=args.register_annex,
        )
        print(json.dumps(outcome, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, LabError, Conflict) as exc:
        parser.exit(2, f"Book shelf import error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
