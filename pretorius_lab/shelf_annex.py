"""Append-only registry of additional physical books in the existing spatial world.

This is not a second laboratory authority. It adds explicitly witnessed and
versioned object-registration/movement events into already-existing vacant
anchors, while preserving the v2 physical genesis and history.
"""
from __future__ import annotations

import copy
import json
import re
import uuid

from .physics import Conflict, LabError, canonical, digest
from .store import GENESIS_HASH, _utc
from .habitat_v2 import SpatialHabitat, TRUSTED_ACTORS

ANNEX_RULES = "spatial-book-annex/1"
OID = re.compile(r"^book:\d{3}$")


def _meta(db):
    return {key: json.loads(value) for key, value in db.execute(
        "SELECT key,value FROM annex_meta")}


def _put(db, key, value):
    db.execute("INSERT OR REPLACE INTO annex_meta(key,value) VALUES (?,?)",
               (key, canonical(value)))


def _apply(items, action, *, anchors, core, branch, revision):
    if not isinstance(action, dict) or not isinstance(action.get("op"), str):
        raise LabError("Invalid annex action")
    op = action["op"]
    allowed = {
        "register": {"op", "book_id", "anchor_id", "name"},
        "move": {"op", "book_id", "anchor_id"},
        "fork_seed": {"op", "book_id", "record"},
    }
    if op not in allowed or set(action) != allowed[op]:
        raise LabError("Malformed annex action")
    oid = action["book_id"]
    if not isinstance(oid, str) or not OID.fullmatch(oid):
        raise LabError("Invalid physical book ID")
    state = copy.deepcopy(items)
    if op == "fork_seed":
        record = action["record"]
        if branch != "sandbox" or oid in state or not isinstance(record, dict) or set(record) != {
                "kind", "name", "anchor_id", "condition", "revision"}:
            raise Conflict("Forked book registration requires an isolated sandbox")
        if record["kind"] != "book" or record["condition"] != "intact":
            raise Conflict("Unsupported annex object state")
        aid = record["anchor_id"]
        name = record["name"]
    else:
        aid = action["anchor_id"]
        name = action.get("name")
    if not isinstance(aid, str) or aid not in anchors:
        raise LabError("No such actual shelf/placement anchor")
    if anchors[aid]["kind"] not in {"shelf_slot", "bench_spot", "floor_spot"}:
        raise LabError("Unsupported placement type")
    if any(item["anchor_id"] == aid for item in core.values()):
        raise Conflict("Core object occupies the anchor")
    if any(item["anchor_id"] == aid for key, item in state.items() if key != oid):
        raise Conflict("Annex object already occupies anchor")
    if op in {"register", "fork_seed"}:
        if oid in core or oid in state:
            raise Conflict("Stable book ID already exists")
        if not isinstance(name, str) or not 1 <= len(name) <= 250:
            raise LabError("Invalid book title")
        state[oid] = {"kind": "book", "name": name, "anchor_id": aid,
                      "condition": "intact", "revision": revision}
    else:
        if oid not in state:
            raise LabError("Book is not registered in this world")
        if state[oid]["anchor_id"] == aid:
            raise LabError("Book already at this location")
        state[oid]["anchor_id"] = aid
        state[oid]["revision"] = revision
    return state


class ShelfAnnex:
    def __init__(self, habitat: SpatialHabitat):
        self.habitat = habitat

    @staticmethod
    def exists(db) -> bool:
        return db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='annex_meta'"
        ).fetchone() is not None

    def initialize(self):
        self.habitat.verify()
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            host = SpatialHabitat._metadata(db)
            db.execute("""CREATE TABLE IF NOT EXISTS annex_meta(
                key TEXT PRIMARY KEY,value TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS annex_events(
                revision INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL,
                envelope TEXT NOT NULL, prev_hash TEXT NOT NULL,
                event_hash TEXT UNIQUE NOT NULL
            )""")
            prior = _meta(db)
            if not prior:
                for key, value in {
                    "lab_id": host["lab_id"], "home_id": host["home_id"],
                    "world_epoch": host["world_epoch"], "mode": host["mode"],
                    "ruleset": ANNEX_RULES, "revision": 0,
                    "head_hash": GENESIS_HASH, "items": {}
                }.items():
                    _put(db, key, value)
            elif (prior["lab_id"], prior["world_epoch"], prior["ruleset"]) != (
                    host["lab_id"], host["world_epoch"], ANNEX_RULES):
                raise Conflict("Annex belongs to another world")
        return self.verify()

    def verify(self):
        proof = self.habitat.verify()
        with self.habitat._open() as db:
            if not self.exists(db):
                raise LabError("Annex not initialized")
            meta = _meta(db)
            if (meta["lab_id"], meta["world_epoch"], meta["home_id"],
                meta["mode"], meta["ruleset"]) != (
                    proof["lab_id"], proof["world_epoch"], proof["home_id"],
                    proof["mode"], ANNEX_RULES):
                raise Conflict("Annex identity differs from parent physical world")
            host = SpatialHabitat._metadata(db)
            prev, revision, items = GENESIS_HASH, 0, {}
            for n, eid, encoded, prior, h in db.execute(
                    "SELECT revision,event_id,envelope,prev_hash,event_hash FROM annex_events ORDER BY revision"):
                event = json.loads(encoded)
                if (n != revision + 1 or n != event["revision"] or
                        eid != event["event_id"] or prior != prev or
                        event["previous_hash"] != prev or h != digest(event)):
                    raise Conflict("Annex history gap or hash mismatch")
                if (event["lab_id"], event["world_epoch"]) != (
                        meta["lab_id"], meta["world_epoch"]):
                    raise Conflict("Annex event has foreign provenance")
                if event["before_digest"] != digest(items):
                    raise Conflict("Annex replay diverged")
                src = event["physical_world_revision"]
                if type(src) is not int or src < 0 or src > proof["revision"]:
                    raise Conflict("Annex event points outside known world revision")
                actual = GENESIS_HASH if src == 0 else db.execute(
                    "SELECT event_hash FROM events WHERE revision=?", (src,)
                ).fetchone()
                actual = actual if src == 0 else (actual[0] if actual else None)
                if actual != event["physical_event_cursor"]:
                    raise Conflict("Annex event source hash is missing")
                # Historical annex events may have legitimately occupied an
                # anchor later vacated by a core-world action. Apply annex
                # transitions against core object state *as of the event* is
                # deferred; present-day occupancy is validated below.
                items = _apply(items, event["action"],
                               anchors=host["state"]["anchors"], core={},
                               branch=meta["mode"], revision=n)
                if event["after_digest"] != digest(items):
                    raise Conflict("Annex event state hash differs")
                prev, revision = h, n
            if (revision, prev, items) != (
                    meta["revision"], meta["head_hash"], meta["items"]):
                raise Conflict("Annex live state does not replay")
            if any(item["anchor_id"] in {obj["anchor_id"] for obj in
                                          host["state"]["objects"].values()}
                   for item in items.values()):
                raise Conflict("Annex clashes with core physical scene")
            return {"verified": True, "revision": revision, "event_cursor": prev,
                    "count": len(items), "lab_id": meta["lab_id"],
                    "world_epoch": meta["world_epoch"]}

    def items(self):
        self.verify()
        with self.habitat._open() as db:
            return copy.deepcopy(_meta(db)["items"])

    def commit(self, action, *, actor="local_operator", event_id=None,
               expected_placement_revision=None):
        if actor not in TRUSTED_ACTORS:
            raise LabError("Untrusted annex actor")
        event_id = event_id or str(uuid.uuid4())
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
            raise LabError("Invalid annex event ID")
        # A live custody world has one effective placement authority. Existing
        # annex history remains replayed by the old reducer, unchanged.
        from .book_custody import BookCustody, exists as custody_exists
        with self.habitat._open() as source:
            unified = custody_exists(source)
        if unified and isinstance(action, dict) and action.get("op") == "move":
            if actor != "local_operator":
                raise LabError("Subject movement must use bodily custody tools")
            if set(action) != {"op", "book_id", "anchor_id"}:
                raise LabError("Malformed annex relocation")
            receipt = BookCustody(self.habitat).act(
                "operator_place", action["book_id"],
                destination=action["anchor_id"], event_id=event_id,
                expected_placement_revision=expected_placement_revision)
            return {**receipt, "domain": "effective_physical_placement",
                    "legacy_annex_revision_unchanged": True}
        if expected_placement_revision is not None:
            raise LabError("Placement revision guard requires an active custody world")
        self.verify()
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            m = _meta(db)
            host = SpatialHabitat._metadata(db)
            if (m["lab_id"], m["world_epoch"], m["ruleset"]) != (
                    host["lab_id"], host["world_epoch"], ANNEX_RULES):
                raise Conflict("Stale annex source identity")
            prior = db.execute("SELECT envelope,event_hash FROM annex_events WHERE event_id=?",
                               (event_id,)).fetchone()
            if prior:
                previous = json.loads(prior[0])
                if previous["action"] != action or previous["actor"] != actor:
                    raise Conflict("Event ID reused with different annex operation")
                return {**previous, "event_hash": prior[1]}
            from .book_custody import exists as custody_exists, effective_objects
            if custody_exists(db):
                custody = {k: json.loads(v) for k, v in db.execute(
                    "SELECT key,value FROM custody_meta")}
                if action["book_id"] in custody["items"]:
                    raise Conflict("Physical book is controlled by custody ledger")
                if action["op"] in {"move", "register"}:
                    if any(obj["anchor_id"] == action["anchor_id"]
                           for obj in effective_objects(db).values()):
                        raise Conflict("Destination occupied in effective world")
            if action["op"] in {"register", "move"}:
                from .physical_affordances import profile_at, check_surface
                profile = profile_at(db, host)
                check_surface(profile, action["book_id"], action["anchor_id"], host)
            updated = _apply(m["items"], action, anchors=host["state"]["anchors"],
                             core=host["state"]["objects"], branch=m["mode"],
                             revision=m["revision"] + 1)
            row = {
                "event_id": event_id, "revision": m["revision"] + 1,
                "lab_id": m["lab_id"], "world_epoch": m["world_epoch"],
                "actor": actor, "action": action,
                "physical_world_revision": host["revision"],
                "physical_event_cursor": host["head_hash"],
                "before_digest": digest(m["items"]), "after_digest": digest(updated),
                "previous_hash": m["head_hash"], "committed_utc": _utc(),
            }
            h = digest(row)
            db.execute("INSERT INTO annex_events VALUES (?,?,?,?,?)",
                       (row["revision"], event_id, canonical(row), m["head_hash"], h))
            _put(db, "revision", row["revision"])
            _put(db, "head_hash", h)
            _put(db, "items", updated)
            return {**row, "event_hash": h}

    def register(self, oid, anchor_id, name, *, event_id=None):
        return self.commit({"op": "register", "book_id": oid,
                            "anchor_id": anchor_id, "name": name}, event_id=event_id)

    def move(self, oid, anchor_id, *, event_id=None,
             expected_placement_revision=None):
        return self.commit({"op": "move", "book_id": oid,
                            "anchor_id": anchor_id}, event_id=event_id,
                           expected_placement_revision=expected_placement_revision)

    def _fork_into(self, clone):
        self.verify()
        other = ShelfAnnex(clone)
        other.initialize()
        for oid, obj in sorted(self.items().items()):
            other.commit({"op": "fork_seed", "book_id": oid,
                          "record": copy.deepcopy(obj)},
                         event_id="fork-book-" + oid.replace(":", "-"))
        other.verify()


def optional_annex_items(habitat):
    with habitat._open() as db:
        has = ShelfAnnex.exists(db)
    return ShelfAnnex(habitat).items() if has else {}


def physical_book_objects(habitat):
    """Verified combined object lookup for source-backed books."""
    host = habitat._verified_status()
    objects = copy.deepcopy(host["state"]["objects"])
    additions = optional_annex_items(habitat)
    if set(objects) & set(additions):
        raise Conflict("Annex duplicates core object ID")
    objects.update(additions)
    from .book_custody import BookCustody, exists, effective_objects
    with habitat._open() as db:
        has_custody = exists(db)
    if has_custody:
        BookCustody(habitat).verify()
        with habitat._open() as db:
            return effective_objects(db)
    return objects
