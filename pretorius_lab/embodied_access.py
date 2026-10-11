"""Position-constrained subject interface for the persistent laboratory.

This is a *local research gate*, not an authenticated remote player or a
biomechanical locomotion model. It does not expose administrative world state.
Body location and offers are append-only and independently replay-checked.
"""
from __future__ import annotations

import json
from pathlib import Path
import uuid

from .habitat_v2 import SpatialHabitat
from .physics import Conflict, LabError, canonical, digest
from .store import GENESIS_HASH, _utc

BODY_RULES = "embodied-access/1"
SUBJECT_ID = "research-subject:pretorius"
INITIAL_STATION = "station:threshold"
# Discrete navigable floor stations, not invented travel distances.
STATIONS = {
    "station:threshold": ("room:sanctum", ("station:center",)),
    "station:center": ("room:sanctum", (
        "station:threshold", "station:shelf:1", "station:shelf:2",
        "station:shelf:3", "station:bench", "station:corner:nw",
        "station:corner:se", "station:chamber:entry")),
    "station:shelf:1": ("room:sanctum", ("station:center",)),
    "station:shelf:2": ("room:sanctum", ("station:center",)),
    "station:shelf:3": ("room:sanctum", ("station:center",)),
    "station:bench": ("room:sanctum", ("station:center",)),
    "station:corner:nw": ("room:sanctum", ("station:center",)),
    "station:corner:se": ("room:sanctum", ("station:center",)),
    "station:chamber:entry": ("room:experiment",
                              ("station:center", "station:chamber:table")),
    "station:chamber:table": ("room:experiment", ("station:chamber:entry",)),
}
ACCESSIBLE_FIXTURE = {
    "station:shelf:1": "shelf:1",
    "station:shelf:2": "shelf:2",
    "station:shelf:3": "shelf:3",
    "station:bench": "bench:main",
    "station:corner:nw": "floor:corner:nw",
    "station:corner:se": "floor:corner:se",
    "station:chamber:table": "chamber:table",
}


def _meta(db) -> dict:
    return {k: json.loads(v) for k, v in db.execute("SELECT key,value FROM embodied_meta")}


def _put(db, key: str, value) -> None:
    db.execute("INSERT OR REPLACE INTO embodied_meta(key,value) VALUES (?,?)",
               (key, canonical(value)))


def _cursor(db, table: str, revision: int) -> str | None:
    if type(revision) is not int or revision < 0:
        return None
    if revision == 0:
        return GENESIS_HASH
    row = db.execute(f"SELECT event_hash FROM {table} WHERE revision=?",
                     (revision,)).fetchone()
    return row[0] if row else None


def _annex(db) -> tuple[dict, int, str]:
    from .shelf_annex import ShelfAnnex
    if not ShelfAnnex.exists(db):
        return {}, 0, GENESIS_HASH
    m = {k: json.loads(v) for k, v in db.execute("SELECT key,value FROM annex_meta")}
    return m["items"], m["revision"], m["head_hash"]


def _scene(db, host: dict, station: str) -> dict:
    """Small, qualitative view: only close fixture objects can be identified."""
    from .shelf_annex import ShelfAnnex
    objects = dict(host["state"]["objects"])
    if ShelfAnnex.exists(db):
        annex, _, _ = _annex(db)
        if set(annex) & set(objects):
            raise Conflict("Duplicate physical identity")
        objects.update(annex)
    from .book_custody import exists as custody_exists, effective_objects
    if custody_exists(db):
        objects = effective_objects(db)
    books = {}
    exists = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='books_meta'"
    ).fetchone() is not None
    if exists:
        rows = db.execute("SELECT value FROM books_meta WHERE key='books'").fetchone()
        books = json.loads(rows[0]) if rows else {}
    room, neighbors = STATIONS[station]
    known = ACCESSIBLE_FIXTURE.get(station)
    locally_visible = []
    carrying = []
    for oid, obj in sorted(objects.items()):
        anchor_id = obj["anchor_id"]
        if anchor_id is None:
            if obj.get("held_by") == SUBJECT_ID:
                carrying.append({"object_id": oid,
                                 "appearance": books[oid]["edition"]["title"]
                                 if oid in books else obj["name"]})
            continue
        anchor = host["state"]["anchors"][anchor_id]
        if anchor["room"] != room:
            continue
        if (known is None or (
                anchor["parent"] != known and anchor_id != known)):
            continue
        item = {
            "object_id": oid,
            "appearance": books[oid]["edition"]["title"] if oid in books else obj["name"],
            "condition": obj["condition"],
            "placement": (anchor["ordinal"] if anchor["parent"].startswith("shelf:")
                          else anchor["parent"]),
        }
        locally_visible.append(item)
    fixture_labels = {
        "room:sanctum": ["bookshelves", "workbench", "chamber doorway"],
        "room:experiment": ["experimental table", "sanctum doorway"],
    }
    from .bench_instruments import exists as bench_instruments_exist
    tools_visible = (["ruler:bench", "balance:bench"]
                     if station == "station:bench" and bench_instruments_exist(db)
                     else [])
    return {
        "location": {"room": room, "station": station},
        "perceived_features": fixture_labels[room],
        "at_hand_fixture": known,
        "nearby_objects": locally_visible,
        "held_objects": carrying,
        "available_instruments": tools_visible,
        "available_moves": sorted(neighbors),
        "access_level": "qualitative_local_not_global_survey",
        "observation_class": "offered_not_proof_of_subject_attention",
    }


class EmbodiedAccess:
    """Local operator's subject-facing, position-gated laboratory research port."""

    def __init__(self, habitat: SpatialHabitat):
        self.habitat = habitat

    def initialize(self, *, station: str = INITIAL_STATION, parent_pose=None) -> dict:
        if station not in STATIONS:
            raise LabError("Unknown bodily station")
        self.habitat.verify()
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            host = SpatialHabitat._metadata(db)
            db.execute("CREATE TABLE IF NOT EXISTS embodied_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS embodied_events(
                revision INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL,
                envelope TEXT NOT NULL, prev_hash TEXT NOT NULL,
                event_hash TEXT UNIQUE NOT NULL
            )""")
            old = _meta(db)
            if not old:
                for k, v in {
                    "lab_id": host["lab_id"], "home_id": host["home_id"],
                    "world_epoch": host["world_epoch"], "mode": host["mode"],
                    "subject_id": SUBJECT_ID, "ruleset": BODY_RULES,
                    "initial_station": station, "station": station,
                    "parent_pose": parent_pose,
                    "revision": 0, "head_hash": GENESIS_HASH,
                }.items():
                    _put(db, k, v)
            elif (old["lab_id"], old["world_epoch"], old["ruleset"],
                  old["subject_id"]) != (host["lab_id"], host["world_epoch"],
                                         BODY_RULES, SUBJECT_ID):
                raise Conflict("Actor state is bound to another laboratory")
            elif (station != old["initial_station"] and old["revision"] == 0):
                raise Conflict("Cannot reset initial station by calling initialize again")
        return self.verify()

    def verify(self) -> dict:
        proof = self.habitat.verify()
        # Separate completed provenance checks remain outside the DB read.
        from .shelf_annex import ShelfAnnex
        with self.habitat._open() as check:
            has_annex = ShelfAnnex.exists(check)
        if has_annex:
            ShelfAnnex(self.habitat).verify()
        # The body's pose ledger is independent from the source-book ledger.
        # A movement should not rereplay megabytes of unrelated book text.
        # Look/book commands verify source book integrity at point of exposure.
        with self.habitat._open() as db:
            if db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='embodied_meta'"
            ).fetchone() is None:
                raise LabError("Embodied access port not initialized")
            m = _meta(db)
            if (m["lab_id"], m["home_id"], m["world_epoch"], m["mode"],
                    m["subject_id"], m["ruleset"]) != (
                    proof["lab_id"], proof["home_id"], proof["world_epoch"],
                    proof["mode"], SUBJECT_ID, BODY_RULES):
                raise Conflict("Embodied actor provenance mismatch")
            if m["initial_station"] not in STATIONS:
                raise Conflict("Invalid initial actor location")
            prev, revision, station = GENESIS_HASH, 0, m["initial_station"]
            for n, event_id, encoded, prior, h in db.execute(
                "SELECT revision,event_id,envelope,prev_hash,event_hash FROM embodied_events ORDER BY revision"
            ):
                e = json.loads(encoded)
                if (n != revision + 1 or n != e["revision"] or
                        e["event_id"] != event_id or prior != prev or
                        e["previous_hash"] != prev or h != digest(e)):
                    raise Conflict("Embodied event chain corrupted")
                if (e["lab_id"], e["world_epoch"], e["subject_id"]) != (
                        m["lab_id"], m["world_epoch"], SUBJECT_ID):
                    raise Conflict("Embodied event belongs to a different world")
                if (e["world_revision"] > proof["revision"] or
                    e["world_cursor"] != _cursor(db, "events", e["world_revision"])):
                    raise Conflict("Embodied event cites unknown physical world event")
                if "annex_revision" in e:
                    if has_annex:
                        current_annex = _annex(db)
                        if e["annex_revision"] > current_annex[1]:
                            raise Conflict("Embodied event claims future annex")
                        if e["annex_revision"] == 0:
                            recorded_annex = GENESIS_HASH
                        else:
                            record = db.execute(
                                "SELECT event_hash FROM annex_events WHERE revision=?",
                                (e["annex_revision"],)).fetchone()
                            recorded_annex = record[0] if record else None
                        if recorded_annex != e["annex_cursor"]:
                            raise Conflict("Embodied annex provenance mismatch")
                    elif e["annex_revision"] != 0 or e["annex_cursor"] != GENESIS_HASH:
                        raise Conflict("Embodied annex history missing")
                if "custody_revision" in e:
                    crev = e["custody_revision"]
                    if type(crev) is not int or crev < 0:
                        raise Conflict("Bad world-handling cursor revision")
                    if crev == 0:
                        recorded = GENESIS_HASH
                    else:
                        row = db.execute(
                            "SELECT event_hash FROM custody_events WHERE revision=?",
                            (crev,)).fetchone()
                        recorded = row[0] if row else None
                    if recorded != e["custody_cursor"]:
                        raise Conflict("Observation cites missing book handling event")
                if e["before_station"] != station:
                    raise Conflict("Actor event started in wrong position")
                if e["kind"] == "move":
                    dest = e["after_station"]
                    if dest not in STATIONS[station][1] or e.get("offered_payload") is not None:
                        raise Conflict("Actor performed nonadjacent travel")
                    station = dest
                elif e["kind"] == "look":
                    if e["after_station"] != station or not isinstance(
                            e.get("offered_payload"), dict):
                        raise Conflict("Malformed position-local observation")
                else:
                    raise Conflict("Invalid embodied operation")
                if e.get("payload_digest") != digest(e.get("offered_payload")):
                    raise Conflict("Embodied sensory receipt altered")
                prev, revision = h, n
            if (m["revision"], m["head_hash"], m["station"]) != (
                    revision, prev, station):
                raise Conflict("Body state cannot be replayed from its events")
            return {"verified": True, "lab_id": m["lab_id"],
                    "world_epoch": m["world_epoch"], "subject_id": SUBJECT_ID,
                    "revision": revision, "station": station, "event_cursor": prev}

    def _offer(self, kind: str, *, destination: str | None = None,
               event_id: str | None = None) -> dict:
        self.verify()
        event_id = event_id or str(uuid.uuid4())
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
            raise LabError("Invalid action ID")
        if kind not in ("move", "look"):
            raise LabError("Unsupported embodied command")
        if kind == "look":
            from .book_library import BookLibrary
            with self.habitat._open() as check:
                has_books = check.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='books_meta'"
                ).fetchone() is not None
            if has_books:
                # Full source replay happens only before text-derived names
                # actually enter the offered subject perception.
                BookLibrary(self.habitat).verify()
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            m, host = _meta(db), SpatialHabitat._metadata(db)
            old = m["station"]
            existing = db.execute(
                "SELECT envelope,event_hash FROM embodied_events WHERE event_id=?",
                (event_id,)).fetchone()
            if existing:
                prior = json.loads(existing[0])
                if prior["kind"] != kind or (
                    kind == "move" and prior["after_station"] != destination):
                    raise Conflict("Event ID reused for different operation")
                return {"event_id": event_id, "event_hash": existing[1],
                        "station": prior["after_station"],
                        "offered_payload": prior["offered_payload"]}
            if kind == "move":
                if destination not in STATIONS[old][1]:
                    raise LabError("Station is not adjacent; walk through the room")
                new, payload = destination, None
            else:
                if destination is not None:
                    raise LabError("Looking does not move the actor")
                new, payload = old, _scene(db, host, old)
            _, annex_rev, annex_cursor = _annex(db)
            from .book_custody import exists as has_custody
            custody_receipt = {}
            if has_custody(db):
                stored = {k: json.loads(v) for k, v in db.execute(
                    "SELECT key,value FROM custody_meta")}
                custody_receipt = {
                    "custody_revision": stored["revision"],
                    "custody_cursor": stored["head_hash"],
                }
            e = {
                "event_id": event_id, "kind": kind, "subject_id": SUBJECT_ID,
                "lab_id": m["lab_id"], "world_epoch": m["world_epoch"],
                "revision": m["revision"] + 1, "before_station": old,
                "after_station": new, "offered_payload": payload,
                "payload_digest": digest(payload),
                "world_revision": host["revision"],
                "world_cursor": host["head_hash"],
                "annex_revision": annex_rev, "annex_cursor": annex_cursor,
                **custody_receipt,
                "previous_hash": m["head_hash"], "recorded_utc": _utc(),
                "claim": "local_action_or_offer_not_confirmed_lived_memory",
            }
            h = digest(e)
            db.execute("INSERT INTO embodied_events VALUES (?,?,?,?,?)",
                       (e["revision"], event_id, canonical(e), m["head_hash"], h))
            _put(db, "station", new)
            _put(db, "revision", e["revision"])
            _put(db, "head_hash", h)
            return {"event_id": event_id, "event_hash": h,
                    "station": new, "offered_payload": payload}

    def move(self, destination: str, *, event_id: str | None = None) -> dict:
        return self._offer("move", destination=destination, event_id=event_id)

    def look(self, *, event_id: str | None = None) -> dict:
        return self._offer("look", event_id=event_id)

    def book(self, book_id: str, operation: str, *,
             direction: int | None = None, bookmark_id: str | None = None,
             event_id: str | None = None) -> dict:
        """Read and mark only if the stable book is physically at this station.

        BookLibrary tests the source and actor position in the SAME SQLite
        write transaction to prevent a move-between-check-and-read race.
        """
        if operation not in {"open", "close", "read", "turn",
                             "mark", "unmark", "open_mark"}:
            raise LabError("No such subject book action")
        self.verify()
        from .book_library import BookLibrary
        result = BookLibrary(self.habitat).operate(
            book_id, operation, direction=direction, bookmark_id=bookmark_id,
            actor="pretorius_research", event_id=event_id,
            access_actor=SUBJECT_ID,
        )
        return result

    def measure(self, instrument: str, object_id: str, quantity: str, *,
                event_id: str | None = None) -> dict:
        """Bounded subject instrument offer: no raw engineer dimensions."""
        self.verify()
        from .bench_instruments import BenchInstruments
        return BenchInstruments(self.habitat).measure(
            instrument, object_id, quantity, event_id=event_id)

    def take(self, book_id: str, *, event_id: str | None = None) -> dict:
        self.verify()
        from .book_custody import BookCustody
        return BookCustody(self.habitat).act("take", book_id, event_id=event_id)

    def put(self, book_id: str, anchor_id: str, *,
            event_id: str | None = None) -> dict:
        self.verify()
        from .book_custody import BookCustody
        return BookCustody(self.habitat).act(
            "put", book_id, destination=anchor_id, event_id=event_id)

    def _fork_into(self, clone: SpatialHabitat) -> None:
        self.verify()
        with self.habitat._open() as db:
            root = _meta(db)
        EmbodiedAccess(clone).initialize(
            station=root["station"],
            parent_pose={"world_epoch": root["world_epoch"],
                         "body_cursor": root["head_hash"],
                         "body_revision": root["revision"],
                         "source_class": "copied_pose_not_new_experience"},
        )
