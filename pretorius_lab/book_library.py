"""Persistent, source-backed book interaction ledger for SpatialHabitat v2.

Optional additive SQLite tables, not a rewrite of the existing physical event chain.
Each book's actual page bytes and physical reading markers are part of a second,
independently verified domain ledger in the SAME database and world epoch.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import sqlite3
import uuid

from .physics import Conflict, LabError, canonical, digest
from .store import GENESIS_HASH, _utc
from .habitat_v2 import SpatialHabitat, TRUSTED_ACTORS

BOOK_RULES = "bound-book-ledger/1"
ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9:._-]{0,63}$")


def _meta(db: sqlite3.Connection, table: str) -> dict:
    return {k: json.loads(v) for k, v in db.execute(f"SELECT key,value FROM {table}")}


def _put(db: sqlite3.Connection, key: str, value) -> None:
    db.execute("INSERT OR REPLACE INTO books_meta(key,value) VALUES (?,?)",
               (key, canonical(value)))


def _validate_edition(value: dict) -> None:
    if not isinstance(value, dict) or set(value) != {
        "edition_id", "title", "author", "source_class",
        "source_reference", "pages", "content_digest"
    }:
        raise LabError("Invalid edition manifest")
    for field in ("edition_id", "title", "author", "source_class", "source_reference"):
        if not isinstance(value[field], str) or not 1 <= len(value[field]) <= 250:
            raise LabError(f"Missing edition provenance: {field}")
    if not ID_PATTERN.fullmatch(value["edition_id"]):
        raise LabError("Edition identifier must be stable")
    if value["source_class"] not in {
        "original_fixture", "public_domain_verified", "licensed", "original_authorized"
    }:
        raise LabError("Unknown source and rights class")
    pages = value["pages"]
    if not isinstance(pages, list) or not 1 <= len(pages) <= 10000 or any(
            not isinstance(p, str) or not 1 <= len(p) <= 12000 for p in pages):
        raise LabError("Page contents must exist and be bounded")
    if value["content_digest"] != digest({
        k: v for k, v in value.items() if k != "content_digest"
    }):
        raise Conflict("Edition content digest mismatch")


def _validate_record(record: dict) -> None:
    if not isinstance(record, dict) or set(record) != {
        "edition", "opened", "current_page", "bookmarks"
    }:
        raise Conflict("Book state schema mismatch")
    _validate_edition(record["edition"])
    if type(record["opened"]) is not bool:
        raise Conflict("Invalid open/closed book state")
    if type(record["current_page"]) is not int or not (
        1 <= record["current_page"] <= len(record["edition"]["pages"])):
        raise Conflict("Invalid current page")
    marks = record["bookmarks"]
    if not isinstance(marks, dict) or len(marks) > 100 or any(
            not isinstance(key, str) or not ID_PATTERN.fullmatch(key) or
            type(page) is not int or not 1 <= page <= len(record["edition"]["pages"])
            for key, page in marks.items()):
        raise Conflict("Invalid physical bookmarks")


def _apply(books: dict, action: dict, *, sandbox: bool) -> dict:
    if not isinstance(action, dict) or not isinstance(action.get("op"), str):
        raise LabError("Invalid book operation")
    op = action["op"]
    fields = {
        "install": {"op", "book_id", "edition"},
        "fork_seed": {"op", "book_id", "record"},
        "open": {"op", "book_id"},
        "turn": {"op", "book_id", "direction"},
        "mark": {"op", "book_id", "bookmark_id"},
        "unmark": {"op", "book_id", "bookmark_id"},
        "close": {"op", "book_id"},
        "read": {"op", "book_id"},
    }
    if op not in fields or set(action) != fields[op]:
        raise LabError("Unsupported or malformed book action")
    book_id = action["book_id"]
    if not isinstance(book_id, str) or not ID_PATTERN.fullmatch(book_id) or (
            not book_id.startswith("book:")):
        raise LabError("Invalid book ID")
    new = copy.deepcopy(books)
    if op == "install":
        if book_id in new:
            raise Conflict("This edition is already physically installed")
        _validate_edition(action["edition"])
        new[book_id] = {
            "edition": copy.deepcopy(action["edition"]),
            "opened": False, "current_page": 1, "bookmarks": {}
        }
    elif op == "fork_seed":
        if not sandbox or book_id in new:
            raise Conflict("Only an empty sandbox can receive a forked book")
        _validate_record(action["record"])
        new[book_id] = copy.deepcopy(action["record"])
    else:
        if book_id not in new:
            raise LabError("This book has no installed, source-backed pages")
        record = new[book_id]
        if op == "open":
            if record["opened"]:
                raise LabError("Book is already open")
            record["opened"] = True
            record["current_page"] = 1
        elif op == "close":
            if not record["opened"]:
                raise LabError("Book is already closed")
            record["opened"] = False
        elif op == "turn":
            direction = action["direction"]
            if type(direction) is not int or direction not in (-1, 1):
                raise LabError("Turn exactly one page backward or forward")
            if not record["opened"]:
                raise LabError("Book must be open to turn a page")
            target = record["current_page"] + direction
            if not 1 <= target <= len(record["edition"]["pages"]):
                raise LabError("Page outside the physical book")
            record["current_page"] = target
        elif op == "mark":
            marker = action["bookmark_id"]
            if not isinstance(marker, str) or not ID_PATTERN.fullmatch(marker):
                raise LabError("Invalid bookmark ID")
            if not record["opened"]:
                raise LabError("Open the book before inserting a bookmark")
            if marker in record["bookmarks"]:
                raise Conflict("Bookmark already exists; remove it first")
            if len(record["bookmarks"]) >= 100:
                raise LabError("Maximum bookmarks reached")
            record["bookmarks"][marker] = record["current_page"]
        elif op == "unmark":
            marker = action["bookmark_id"]
            if marker not in record["bookmarks"]:
                raise LabError("Unknown physical bookmark")
            del record["bookmarks"][marker]
        elif op == "read":
            if not record["opened"]:
                raise LabError("Open the book before requesting a page")
        _validate_record(record)
    return new


class BookLibrary:
    """Single-file book ledger. Never use this class as an untrusted network endpoint."""

    def __init__(self, habitat: SpatialHabitat):
        self.habitat = habitat

    def initialize(self) -> dict:
        self.habitat.verify()
        db = self.habitat._open()
        try:
            db.execute("BEGIN IMMEDIATE")
            host = SpatialHabitat._metadata(db)
            db.execute("CREATE TABLE IF NOT EXISTS books_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS books_events(
                revision INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL,
                payload TEXT NOT NULL, prev_hash TEXT NOT NULL, event_hash TEXT UNIQUE NOT NULL
            )""")
            prior = _meta(db, "books_meta")
            if not prior:
                seed = {
                    "lab_id": host["lab_id"], "home_id": host["home_id"],
                    "world_epoch": host["world_epoch"], "mode": host["mode"],
                    "ruleset": BOOK_RULES, "revision": 0,
                    "head_hash": GENESIS_HASH, "books": {}
                }
                for k, v in seed.items():
                    _put(db, k, v)
            elif (prior["lab_id"], prior["world_epoch"], prior["ruleset"]) != (
                    host["lab_id"], host["world_epoch"], BOOK_RULES):
                raise Conflict("Book ledger belongs to a different world or ruleset")
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        return self.verify()

    def _verified(self) -> dict:
        result = self.verify()
        return result

    def verify(self) -> dict:
        host_proof = self.habitat.verify()
        with self.habitat._open() as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='books_meta'").fetchone() is None:
                raise LabError("Book ledger not initialized")
            m = _meta(db, "books_meta")
            if (m["lab_id"], m["world_epoch"], m["home_id"], m["mode"], m["ruleset"]) != (
                    host_proof["lab_id"], host_proof["world_epoch"], host_proof["home_id"],
                    host_proof["mode"], BOOK_RULES):
                raise Conflict("Book ledger identity/epoch/authority mismatch")
            books, prev, revision = {}, GENESIS_HASH, 0
            for n, event_id, encoded, stored_prev, event_hash in db.execute(
                    "SELECT revision,event_id,payload,prev_hash,event_hash FROM books_events ORDER BY revision"):
                entry = json.loads(encoded)
                if (n != revision + 1 or event_id != entry["event_id"] or
                        entry["revision"] != n or stored_prev != prev or
                        entry["previous_hash"] != prev or event_hash != digest(entry)):
                    raise Conflict("Book event hash or sequence damaged")
                if (entry["lab_id"], entry["world_epoch"]) != (
                        m["lab_id"], m["world_epoch"]):
                    raise Conflict("Book event world provenance invalid")
                if entry["before_digest"] != digest(books):
                    raise Conflict("Book event prior state mismatch")
                if entry["physical_world_revision"] > host_proof["revision"]:
                    raise Conflict("Book event references a future physical world")
                if entry["physical_event_cursor"] != self._physical_cursor(
                        db, entry["physical_world_revision"]):
                    raise Conflict("Book event references an unknown physical cursor")
                books = _apply(books, entry["action"], sandbox=m["mode"] == "sandbox")
                if entry["after_digest"] != digest(books):
                    raise Conflict("Book state replay mismatch")
                prev, revision = event_hash, n
            if (revision, prev, books) != (m["revision"], m["head_hash"], m["books"]):
                raise Conflict("Book ledger materialized state diverged")
            if any(book_id not in self.habitat.status()["state"]["objects"]
                   or self.habitat.status()["state"]["objects"][book_id]["kind"] != "book"
                   for book_id in books):
                raise Conflict("Edition detached from its physical book identity")
            return {"verified": True, "revision": revision, "event_cursor": prev,
                    "lab_id": m["lab_id"], "world_epoch": m["world_epoch"],
                    "catalog_count": len(books)}

    @staticmethod
    def _physical_cursor(db, revision: int) -> str | None:
        if type(revision) is not int or revision < 0:
            return None
        if revision == 0:
            return GENESIS_HASH
        row = db.execute("SELECT event_hash FROM events WHERE revision=?", (revision,)).fetchone()
        return row[0] if row else None

    def _commit(self, action: dict, *, actor: str = "local_operator",
                event_id: str | None = None) -> dict:
        if actor not in TRUSTED_ACTORS:
            raise LabError("Untrusted local actor label")
        event_id = event_id or str(uuid.uuid4())
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
            raise LabError("Invalid book event ID")
        self._verified()
        db = self.habitat._open()
        try:
            db.execute("BEGIN IMMEDIATE")
            m = _meta(db, "books_meta")
            host = SpatialHabitat._metadata(db)
            if (m["lab_id"], m["world_epoch"], m["ruleset"]) != (
                    host["lab_id"], host["world_epoch"], BOOK_RULES):
                raise Conflict("Book and physical world are not aligned")
            existing = db.execute("SELECT payload,event_hash FROM books_events WHERE event_id=?",
                                  (event_id,)).fetchone()
            if existing:
                previous = json.loads(existing[0])
                if previous["action"] != action or previous["actor"] != actor:
                    raise Conflict("Book event ID used for a different operation")
                db.execute("COMMIT")
                return {**previous, "event_hash": existing[1]}
            physical_id = action["book_id"]
            obj = host["state"]["objects"].get(physical_id)
            if not obj or obj["kind"] != "book":
                raise LabError("A source-backed book must exist as a physical world object")
            updated = _apply(m["books"], action, sandbox=m["mode"] == "sandbox")
            entry = {
                "event_id": event_id, "revision": m["revision"] + 1,
                "lab_id": m["lab_id"], "world_epoch": m["world_epoch"],
                "book_id": physical_id, "actor": actor,
                "source_class": "interface_action_not_proof_of_subject_witnessing",
                "action": action, "before_digest": digest(m["books"]),
                "after_digest": digest(updated),
                "physical_world_revision": host["revision"],
                "physical_event_cursor": host["head_hash"],
                "previous_hash": m["head_hash"], "recorded_utc": _utc(),
            }
            h = digest(entry)
            db.execute("INSERT INTO books_events VALUES (?,?,?,?,?)",
                       (entry["revision"], event_id, canonical(entry), m["head_hash"], h))
            _put(db, "revision", entry["revision"])
            _put(db, "head_hash", h)
            _put(db, "books", updated)
            db.execute("COMMIT")
            return {**entry, "event_hash": h}
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def install(self, book_id: str, *, edition_id: str, title: str, author: str,
                pages: list[str], source_class: str, source_reference: str,
                event_id: str | None = None) -> dict:
        edition = {
            "edition_id": edition_id, "title": title, "author": author,
            "source_class": source_class, "source_reference": source_reference,
            "pages": pages
        }
        edition["content_digest"] = digest(edition)
        _validate_edition(edition)
        return self._commit({"op": "install", "book_id": book_id, "edition": edition},
                            event_id=event_id)

    def operate(self, book_id: str, op: str, *, direction: int | None = None,
                bookmark_id: str | None = None, actor: str = "local_operator",
                event_id: str | None = None) -> dict:
        action = {"op": op, "book_id": book_id}
        if op == "turn":
            action["direction"] = direction
        elif op in {"mark", "unmark"}:
            action["bookmark_id"] = bookmark_id
        elif direction is not None or bookmark_id is not None:
            raise LabError("Extraneous book action parameter")
        result = self._commit(action, actor=actor, event_id=event_id)
        if op != "read":
            return {"book_id": book_id, "operation": op,
                    "library_revision": result["revision"], "event_id": result["event_id"]}
        with self.habitat._open() as db:
            current = _meta(db, "books_meta")["books"][book_id]
        page = current["current_page"]
        edition = current["edition"]
        return {"book_id": book_id, "title": edition["title"], "author": edition["author"],
                "edition_id": edition["edition_id"], "page": page,
                "page_count": len(edition["pages"]),
                "page_text": edition["pages"][page - 1],
                "source_class": edition["source_class"],
                "source_reference": edition["source_reference"],
                "content_digest": edition["content_digest"],
                "delivery_event_id": result["event_id"],
                "delivery_class": "page_offered_to_interface_not_proof_of_reading"}

    def catalog(self, book_id: str | None = None) -> dict:
        self._verified()
        with self.habitat._open() as db:
            books = _meta(db, "books_meta")["books"]
        if book_id:
            if book_id not in books:
                raise LabError("No source-backed edition installed for this book")
            books = {book_id: books[book_id]}
        return {key: {
            "title": value["edition"]["title"], "author": value["edition"]["author"],
            "edition_id": value["edition"]["edition_id"],
            "source_class": value["edition"]["source_class"],
            "page_count": len(value["edition"]["pages"]),
            "opened": value["opened"],
            "page_if_open": value["current_page"] if value["opened"] else None,
            "bookmarks": dict(value["bookmarks"]),
        } for key, value in sorted(books.items())}

    def _fork_into(self, clone: SpatialHabitat) -> None:
        """Copy a verified reading state as a sandbox genesis with recorded provenance."""
        self._verified()
        with self.habitat._open() as db:
            source = _meta(db, "books_meta")
        other = BookLibrary(clone)
        other.initialize()
        for book_id, record in sorted(source["books"].items()):
            other._commit({"op": "fork_seed", "book_id": book_id,
                           "record": copy.deepcopy(record)})
        other.verify()
