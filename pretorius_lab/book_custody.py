"""Physical custody overlay for books and the intact laboratory beaker.

Old book events replay identically. Versioned take_apparatus/put_apparatus actions
add bounded subject authority without changing underlying world history.
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
    """Return effective single-location authority for carried/placed objects."""
    host, objects, _, _ = _raw(db)
    held = {}
    if exists(db):
        held = _meta(db)["items"]
    for oid, state in held.items():
        if oid not in objects:
            raise Conflict("Custody references no stable physical object identity")
        if state["held_by"] is not None and not (
                objects[oid]["kind"] == "book" or
                (oid == "beaker:001" and objects[oid]["kind"] == "glass_beaker"
                 and objects[oid]["condition"] == "intact")):
            raise Conflict("Only books and intact beaker may be carried")
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
        "take_apparatus": {"op", "object_id", "from_anchor"},
        "put_apparatus": {"op", "object_id", "anchor_id"},
        # Operator-authorized relocation may target a previously reserved raw
        # anchor if that anchor is physically vacant in the effective world.
        "operator_place": {"op", "object_id", "from_anchor", "anchor_id"},
        "fork_seed": {"op", "book_id", "record"},
    }
    if op not in expected or set(action) != expected[op]:
        raise Conflict("Unknown custody reducer operation")
    book_id = (action["object_id"] if op in {
        "operator_place", "take_apparatus", "put_apparatus"} else action["book_id"])
    if not isinstance(book_id, str) or not (
            (op in {"take", "put"} and book_id.startswith("book:")) or
            (op in {"take_apparatus", "put_apparatus"} and book_id == "beaker:001") or
            (op in {"operator_place", "fork_seed"} and
             (book_id.startswith("book:") or book_id == "beaker:001"))):
        raise Conflict("Invalid known physical object ID")
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
    elif op == "operator_place":
        source, destination = action["from_anchor"], action["anchor_id"]
        if (not isinstance(source, str) or not isinstance(destination, str) or
                source == destination):
            raise Conflict("Invalid operator relocation")
        old = state.get(book_id)
        if old is not None and (old["anchor_id"] != source or old["held_by"] is not None):
            raise Conflict("Operator move is not based on current placement")
        state[book_id] = {"anchor_id": destination, "held_by": None}
    elif op in {"take", "take_apparatus"}:
        aid = action["from_anchor"]
        if not isinstance(aid, str):
            raise Conflict("Missing pre-take anchor")
        old = state.get(book_id)
        if old is not None and (old["anchor_id"] != aid or old["held_by"] is not None):
            raise LabError("Book is not at the claimed shelf/table")
        if any(obj["held_by"] == SUBJECT_ID for obj in state.values()):
            raise LabError("Research actor can carry one object at a time")
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
        raise Conflict("Actor has multiple objects without capacity")
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
        from .physical_affordances import PhysicalAffordances, exists as affordances_exist
        with self.habitat._open() as check:
            has_affordances = affordances_exist(check)
        if has_affordances:
            PhysicalAffordances(self.habitat).verify()
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
            from .physical_affordances import profile_at
            active_profile = profile_at(db, host)
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
                if event.get("mechanical_profile_digest") is not None:
                    if (active_profile is None or
                            event["mechanical_profile_digest"] != digest(active_profile)):
                        raise Conflict("Handling event references invalid mechanical assumptions")
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
                if oid not in raw:
                    raise Conflict("Custody references unknown physical object")
                if rec["held_by"] is not None and not (
                        raw[oid]["kind"] == "book" or
                        (oid == "beaker:001" and raw[oid]["kind"] == "glass_beaker"
                         and raw[oid]["condition"] == "intact")):
                    raise Conflict("Only books and intact beaker may be carried")
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

    def act(self, operation, book_id, *, destination=None, event_id=None,
            expected_placement_revision=None):
        if operation not in {"take", "put", "take_apparatus",
                             "put_apparatus", "operator_place"}:
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
            from .physical_affordances import (
                profile_at, check_surface, check_actor_reach)
            active_profile = profile_at(db, host)
            prior = db.execute(
                "SELECT envelope,event_hash FROM custody_events WHERE event_id=?",
                (event_id,)).fetchone()
            if prior:
                e = json.loads(prior[0])
                oid = e["action"].get("object_id", e["action"].get("book_id"))
                if (e["action"]["op"] != operation or oid != book_id or
                        (operation in {"put", "put_apparatus", "operator_place"} and
                         e["action"]["anchor_id"] != destination)):
                    raise Conflict("Handling event id reused for a different operation")
                historical_location = ({"anchor_id": None, "held_by": SUBJECT_ID}
                    if operation in {"take", "take_apparatus"} else
                    {"anchor_id": e["action"]["anchor_id"], "held_by": None})
                return {"event_id": event_id, "event_hash": prior[1],
                        "object_id": book_id, "location": historical_location}
            if expected_placement_revision is not None and (
                    type(expected_placement_revision) is not int or
                    expected_placement_revision != meta["revision"]):
                raise Conflict("Stale effective physical placement revision")
            # Recheck materialized cursors inside the same write transaction:
            # a concurrently accepted move is valid, a falsified head is not.
            pose_revision = body["revision"]
            if pose_revision == 0:
                pose_hash = GENESIS_HASH
                pose_station = body["initial_station"]
            else:
                accepted_pose = db.execute(
                    "SELECT envelope,event_hash FROM embodied_events WHERE revision=?",
                    (pose_revision,)).fetchone()
                pose_hash = accepted_pose[1] if accepted_pose else None
                pose_station = (json.loads(accepted_pose[0])["after_station"]
                                if accepted_pose else None)
            if (pose_hash, pose_station) != (body["head_hash"], body["station"]):
                raise Conflict("The body is not at an accepted pose")
            recorded = (db.execute("SELECT event_hash FROM custody_events WHERE revision=?",
                                   (meta["revision"],)).fetchone()
                        if meta["revision"] else None)
            if (recorded[0] if recorded else GENESIS_HASH) != meta["head_hash"]:
                raise Conflict("Physical custody event head invalid")
            if book_id not in raw:
                raise LabError("Unknown supported physical object")
            if operation in {"take", "put"} and raw[book_id]["kind"] != "book":
                raise LabError("Book handling requires an actual book")
            if operation in {"take_apparatus", "put_apparatus"} and not (
                    book_id == "beaker:001" and raw[book_id]["kind"] == "glass_beaker"
                    and raw[book_id]["condition"] == "intact"):
                raise LabError("Only the intact laboratory beaker is portable apparatus")
            effective = effective_objects(db)
            before = effective[book_id]["anchor_id"]
            if operation == "operator_place":
                # Preserve lower-layer condition invariants even when the new
                # placement is recorded in the custody domain.
                obj = raw[book_id]
                if (obj["kind"] == "glass_beaker" and
                        obj["condition"] == "broken" and not obj["collected"]):
                    raise LabError("Scattered glass fragments must be collected before moving")
                if before is None or effective[book_id].get("held_by") is not None:
                    raise Conflict("Cannot operator-relocate a book held by the actor")
                if destination not in host["state"]["anchors"] or before == destination:
                    raise LabError("Invalid or unchanged placement target")
                if any(o["anchor_id"] == destination for o in effective.values()):
                    raise Conflict("A physical object already occupies that location")
                check_surface(active_profile, book_id, destination, host)
                action = {"op": "operator_place", "object_id": book_id,
                          "from_anchor": before, "anchor_id": destination}
            elif operation in {"take", "take_apparatus"}:
                if destination is not None:
                    raise LabError("Pickup has no destination")
                if before is None:
                    raise LabError("Book is already carried")
                if _station_for_anchor(host["state"]["anchors"], before) != body["station"]:
                    raise LabError("Approach the book before picking it up")
                check_actor_reach(active_profile, book_id, before, host, lifting=True)
                action = ({"op": "take", "book_id": book_id, "from_anchor": before}
                          if operation == "take" else
                          {"op": "take_apparatus", "object_id": book_id,
                           "from_anchor": before})
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
                check_actor_reach(active_profile, book_id, destination, host, lifting=False)
                check_surface(active_profile, book_id, destination, host)
                if operation == "put_apparatus" and (
                        host["state"]["anchors"][destination]["kind"] == "shelf_slot"):
                    raise LabError("Apparatus must be placed on a bench or floor")
                action = ({"op": "put", "book_id": book_id, "anchor_id": destination}
                          if operation == "put" else
                          {"op": "put_apparatus", "object_id": book_id,
                           "anchor_id": destination})
            updated = _apply(meta["items"], action, sandbox=meta["mode"] == "sandbox")
            event = {
                "revision": meta["revision"] + 1, "event_id": event_id,
                "lab_id": meta["lab_id"], "world_epoch": meta["world_epoch"],
                "action": action, "body_revision": body["revision"],
                "body_cursor": body["head_hash"], "body_station": body["station"],
                "world_revision": host["revision"], "world_cursor": host["head_hash"],
                "annex_revision": ar, "annex_cursor": ah,
                "before_digest": digest(meta["items"]), "after_digest": digest(updated),
                **({"mechanical_profile_digest": digest(active_profile)}
                   if active_profile is not None else {}),
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
            return {"object_id": book_id, "event_id": event_id, "event_hash": h,
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
