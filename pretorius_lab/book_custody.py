"""Physical custody overlay for existing canonical core/annex book identities.

Does not rewrite spatial v2 event hashes or historical shelf manifests.
Accepted custody events are the current location authority for handled books.
"""
from __future__ import annotations

import copy
import json
import uuid

from .physics import Conflict, LabError, canonical, digest
from .store import GENESIS_HASH, _utc
from .habitat_v2 import SpatialHabitat
from .embodied_access import EmbodiedAccess, SUBJECT_ID, STATIONS, ACCESSIBLE_FIXTURE

CUSTODY_RULES = "physical-book-custody/1"


def _meta(db):
    return {k: json.loads(v) for k, v in db.execute("SELECT key,value FROM custody_meta")}


def _put(db, key, value):
    db.execute("INSERT OR REPLACE INTO custody_meta(key,value) VALUES (?,?)", (key, canonical(value)))


def exists(db):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='custody_meta'"
    ).fetchone() is not None


def _raw(db):
    host = SpatialHabitat._metadata(db)
    objects = copy.deepcopy(host["state"]["objects"])
    from .shelf_annex import ShelfAnnex
    annex_revision, annex_cursor = 0, GENESIS_HASH
    if ShelfAnnex.exists(db):
        am = {k: json.loads(v) for k, v in db.execute("SELECT key,value FROM annex_meta")}
        if set(am["items"]) & set(objects):
            raise Conflict("Physical object ID duplicated")
        objects.update(am["items"])
        annex_revision, annex_cursor = am["revision"], am["head_hash"]
    return host, objects, annex_revision, annex_cursor


def effective_objects(db):
    """Return copies of true world objects with carried/placed book location overrides."""
    host, objects, _, _ = _raw(db)
    held = {}
    if exists(db):
        held = _meta(db)["items"]
    for oid, state in held.items():
        if oid not in objects or objects[oid]["kind"] != "book":
            raise Conflict("Custody book has no underlying stable physical identity")
        obj = objects[oid]
        obj["anchor_id"] = state["anchor_id"]
        obj["held_by"] = state["held_by"]
    occupancy = {}
    for oid, obj in objects.items():
        aid = obj["anchor_id"]
        if aid is None:
            if obj.get("held_by") != SUBJECT_ID:
                raise Conflict("Unclaimed physical object")
            continue
        if aid not in host["state"]["anchors"]:
            raise Conflict("Unknown anchor in custody physical view")
        if aid in occupancy:
            raise Conflict("Two objects claim one physical location")
        occupancy[aid] = oid
    return objects


def _station_for_anchor(anchors, aid):
    if aid not in anchors:
        raise LabError("Unknown destination")
    a = anchors[aid]
    if a["parent"].startswith("shelf:"):
        return "station:" + a["parent"]
    for station, fixture in ACCESSIBLE_FIXTURE.items():
        if fixture == aid or fixture == a["parent"]:
            return station
    raise LabError("No subject-accessible placement station")


def _apply(items, action, *, sandbox):
    if not isinstance(action, dict) or not isinstance(action.get("op"), str):
        raise Conflict("Malformed physical handling action")
    op = action["op"]
    expected = {
        "take": {"op", "book_id", "from_anchor"},
        "put": {"op", "book_id", "anchor_id"},
        "fork_seed": {"op", "book_id", "record"},
    }
    if op not in expected or set(action) != expected[op]:
        raise Conflict("Unknown custody reducer operation")
    book_id = action["book_id"]
    if not isinstance(book_id, str) or not book_id.startswith("book:"):
        raise Conflict("Invalid physical book ID")
    state = copy.deepcopy(items)
    if op == "fork_seed":
        if not sandbox or book_id in state:
            raise Conflict("Fork seed only into empty sandbox custody")
        record = action["record"]
        if not isinstance(record, dict) or set(record) != {"anchor_id", "held_by"}:
            raise Conflict("Invalid inherited location")
        if (record["anchor_id"] is None) == (record["held_by"] is None):
            raise Conflict("Book is neither exclusively held nor exclusively placed")
        if record["held_by"] not in (None, SUBJECT_ID):
            raise Conflict("Foreign holder")
        state[book_id] = copy.deepcopy(record)
    elif op == "take":
        aid = action["from_anchor"]
        if not isinstance(aid, str):
            raise Conflict("Missing pre-take anchor")
        old = state.get(book_id)
        if old is not None and (old["anchor_id"] != aid or old["held_by"] is not None):
            raise LabError("Book is not at the claimed shelf/table")
        if any(obj["held_by"] == SUBJECT_ID for obj in state.values()):
            raise LabError("Research actor can carry one book at a time")
        state[book_id] = {"anchor_id": None, "held_by": SUBJECT_ID}
    else:
        if book_id not in state or state[book_id] != {
                "anchor_id": None, "held_by": SUBJECT_ID}:
            raise LabError("The actor is not carrying this book")
        aid = action["anchor_id"]
        if not isinstance(aid, str):
            raise LabError("Missing destination anchor")
        state[book_id] = {"anchor_id": aid, "held_by": None}
    if sum(rec["held_by"] == SUBJECT_ID for rec in state.values()) > 1:
        raise Conflict("Actor has multiple books without capacity")
    return state


class BookCustody:
    def __init__(self, habitat: SpatialHabitat):
        self.habitat = habitat

    def initialize(self):
        self.habitat.verify()
        EmbodiedAccess(self.habitat).verify()
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            host = SpatialHabitat._metadata(db)
            db.execute("CREATE TABLE IF NOT EXISTS custody_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS custody_events(
                revision INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL,
                envelope TEXT NOT NULL, prev_hash TEXT NOT NULL, event_hash TEXT UNIQUE NOT NULL
            )""")
            prior = _meta(db)
            if not prior:
                for k, v in {
                    "lab_id": host["lab_id"], "home_id": host["home_id"],
                    "world_epoch": host["world_epoch"], "mode": host["mode"],
                    "subject_id": SUBJECT_ID, "ruleset": CUSTODY_RULES,
                    "revision": 0, "head_hash": GENESIS_HASH, "items": {},
                }.items():
                    _put(db, k, v)
            elif (prior["lab_id"], prior["world_epoch"], prior["ruleset"]) != (
                    host["lab_id"], host["world_epoch"], CUSTODY_RULES):
                raise Conflict("Custody ledger cannot change world identity")
        return self.verify()

    def verify(self):
        proof = self.habitat.verify()
        EmbodiedAccess(self.habitat).verify()
        from .shelf_annex import ShelfAnnex
        with self.habitat._open() as check:
            has_annex = ShelfAnnex.exists(check)
        if has_annex:
            ShelfAnnex(self.habitat).verify()
        with self.habitat._open() as db:
            if not exists(db):
                raise LabError("Book custody is not initialized")
            meta = _meta(db)
            if (meta["lab_id"], meta["home_id"], meta["world_epoch"],
                meta["mode"], meta["subject_id"], meta["ruleset"]) != (
                    proof["lab_id"], proof["home_id"], proof["world_epoch"],
                    proof["mode"], SUBJECT_ID, CUSTODY_RULES):
                raise Conflict("Custody world provenance mismatch")
            prev, revision, items = GENESIS_HASH, 0, {}
            host, raw, _, _ = _raw(db)
            for n, eid, encoded, prior, h in db.execute(
                "SELECT revision,event_id,envelope,prev_hash,event_hash FROM custody_events ORDER BY revision"
            ):
                event = json.loads(encoded)
                if (n != revision + 1 or eid != event["event_id"] or
                    n != event["revision"] or prior != prev or
                    event["previous_hash"] != prev or h != digest(event)):
                    raise Conflict("Custody event hash chain diverged")
                if (event["lab_id"], event["world_epoch"]) != (
                        meta["lab_id"], meta["world_epoch"]):
                    raise Conflict("Custody event foreign epoch")
                if event["before_digest"] != digest(items):
                    raise Conflict("Custody prior state mismatch")
                body_rev = event["body_revision"]
                if body_rev == 0:
                    body_cursor = GENESIS_HASH
                    body_station = json.loads(db.execute(
                        "SELECT value FROM embodied_meta WHERE key='initial_station'"
                    ).fetchone()[0])
                else:
                    b = db.execute(
                        "SELECT envelope,event_hash FROM embodied_events WHERE revision=?",
                        (body_rev,)).fetchone()
                    body_cursor = b[1] if b else None
                    body_station = json.loads(b[0])["after_station"] if b else None
                if (body_cursor != event["body_cursor"] or
                        body_station != event["body_station"]):
                    raise Conflict("Custody event lacks proven position")
                world_rev = event["world_revision"]
                physical = (GENESIS_HASH if world_rev == 0 else None)
                if world_rev > 0:
                    r = db.execute("SELECT event_hash FROM events WHERE revision=?",
                                   (world_rev,)).fetchone()
                    physical = r[0] if r else None
                if physical != event["world_cursor"]:
                    raise Conflict("Custody references missing world event")
                ar = event["annex_revision"]
                if ar == 0:
                    annex_hash = GENESIS_HASH
                else:
                    t = db.execute("SELECT event_hash FROM annex_events WHERE revision=?",
                                   (ar,)).fetchone() if has_annex else None
                    annex_hash = t[0] if t else None
                if annex_hash != event["annex_cursor"]:
                    raise Conflict("Custody references missing annex event")
                items = _apply(items, event["action"], sandbox=meta["mode"] == "sandbox")
                if event["after_digest"] != digest(items):
                    raise Conflict("Custody event replay failed")
                prev, revision = h, n
            if (meta["items"], meta["revision"], meta["head_hash"]) != (items, revision, prev):
                raise Conflict("Materialized custody is inconsistent")
            for oid, rec in items.items():
                if oid not in raw or raw[oid]["kind"] != "book":
                    raise Conflict("Custody references unknown book")
                if rec["anchor_id"] is not None:
                    if rec["anchor_id"] not in host["state"]["anchors"]:
                        raise Conflict("Custody references unknown anchor")
                    if rec["held_by"] is not None:
                        raise Conflict("Placed book also held")
                elif rec["held_by"] != SUBJECT_ID:
                    raise Conflict("Carried book has no owner")
            effective_objects(db)
            return {"verified": True, "revision": revision, "event_cursor": prev,
                    "items": len(items), "lab_id": meta["lab_id"],
                    "world_epoch": meta["world_epoch"]}

    def act(self, operation, book_id, *, destination=None, event_id=None):
        if operation not in {"take", "put"}:
            raise LabError("Unsupported handling action")
        self.verify()
        event_id = event_id or str(uuid.uuid4())
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
            raise LabError("Invalid handling id")
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            meta = _meta(db)
            body = {k: json.loads(v) for k, v in db.execute(
                "SELECT key,value FROM embodied_meta")}
            host, raw, ar, ah = _raw(db)
            prior = db.execute(
                "SELECT envelope,event_hash FROM custody_events WHERE event_id=?",
                (event_id,)).fetchone()
            if prior:
                e = json.loads(prior[0])
                if e["action"]["op"] != operation or e["action"]["book_id"] != book_id or (
                        operation == "put" and e["action"]["anchor_id"] != destination):
                    raise Conflict("Handling event id reused for a different operation")
                return {"event_id": event_id, "event_hash": prior[1],
                        "book_id": book_id, "location": meta["items"].get(book_id)}
            if book_id not in raw or raw[book_id]["kind"] != "book":
                raise LabError("Unknown physical book")
            effective = effective_objects(db)
            before = effective[book_id]["anchor_id"]
            if operation == "take":
                if destination is not None:
                    raise LabError("Pickup has no destination")
                if before is None:
                    raise LabError("Book is already carried")
                if _station_for_anchor(host["state"]["anchors"], before) != body["station"]:
                    raise LabError("Approach the book before picking it up")
                action = {"op": "take", "book_id": book_id, "from_anchor": before}
            else:
                if before is not None or effective[book_id].get("held_by") != SUBJECT_ID:
                    raise LabError("This book is not in the actor's hands")
                if _station_for_anchor(host["state"]["anchors"], destination) != body["station"]:
                    raise LabError("Stand at the destination before putting the book down")
                if host["state"]["anchors"][destination]["kind"] not in {
                        "shelf_slot", "bench_spot", "floor_spot"}:
                    raise LabError("Not a supported physical surface")
                if any(x["anchor_id"] == destination for x in effective.values()):
                    raise Conflict("Destination occupied")
                action = {"op": "put", "book_id": book_id, "anchor_id": destination}
            updated = _apply(meta["items"], action, sandbox=meta["mode"] == "sandbox")
            event = {
                "revision": meta["revision"] + 1, "event_id": event_id,
                "lab_id": meta["lab_id"], "world_epoch": meta["world_epoch"],
                "action": action, "body_revision": body["revision"],
                "body_cursor": body["head_hash"], "body_station": body["station"],
                "world_revision": host["revision"], "world_cursor": host["head_hash"],
                "annex_revision": ar, "annex_cursor": ah,
                "before_digest": digest(meta["items"]), "after_digest": digest(updated),
                "previous_hash": meta["head_hash"], "recorded_utc": _utc(),
                "claim": "trusted_local_object_transfer_not_proof_of_subject_agency",
            }
            h = digest(event)
            db.execute("INSERT INTO custody_events VALUES (?,?,?,?,?)",
                       (event["revision"], event_id, canonical(event),
                        meta["head_hash"], h))
            _put(db, "items", updated)
            _put(db, "revision", event["revision"])
            _put(db, "head_hash", h)
            return {"book_id": book_id, "event_id": event_id, "event_hash": h,
                    "location": updated[book_id]}

    def _fork_into(self, clone):
        self.verify()
        with self.habitat._open() as db:
            source = _meta(db)
        other = BookCustody(clone)
        other.initialize()
        for oid, record in sorted(source["items"].items()):
            # Fork snapshots retain physical placement / holding under an
            # independent world epoch, but not parent's action-event chain.
            other._seed(oid, record)
        other.verify()

    def _seed(self, oid, record):
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            m = _meta(db)
            host = SpatialHabitat._metadata(db)
            if m["mode"] != "sandbox":
                raise Conflict("Cannot seed canonical custody")
            action = {"op": "fork_seed", "book_id": oid,
                      "record": copy.deepcopy(record)}
            body = {k: json.loads(v) for k, v in db.execute(
                "SELECT key,value FROM embodied_meta")}
            updated = _apply(m["items"], action, sandbox=True)
            ar = 0
            ah = GENESIS_HASH
            from .shelf_annex import ShelfAnnex
            if ShelfAnnex.exists(db):
                am = {k: json.loads(v) for k,v in db.execute("SELECT key,value FROM annex_meta")}
                ar, ah = am["revision"], am["head_hash"]
            e = {
                "revision": m["revision"] + 1,
                "event_id": "fork-custody-" + oid,
                "lab_id": m["lab_id"], "world_epoch": m["world_epoch"],
                "action": action, "body_revision": body["revision"],
                "body_cursor": body["head_hash"], "body_station": body["station"],
                "world_revision": host["revision"], "world_cursor": host["head_hash"],
                "annex_revision": ar, "annex_cursor": ah,
                "before_digest": digest(m["items"]), "after_digest": digest(updated),
                "previous_hash": m["head_hash"], "recorded_utc": _utc(),
                "claim": "copied_physical_snapshot_not_new_subject_experience",
            }
            h = digest(e)
            db.execute("INSERT INTO custody_events VALUES (?,?,?,?,?)",
                       (e["revision"], e["event_id"], canonical(e), m["head_hash"], h))
            _put(db, "revision", e["revision"])
            _put(db, "head_hash", h)
            _put(db, "items", updated)
