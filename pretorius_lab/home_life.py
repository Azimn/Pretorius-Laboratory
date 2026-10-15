"""Opt-in domestic life annex over the *same* v2 Laboratory SQLite world.

This adds no second brain, no alternate body position, and no Village authority.
Domestic items and their container histories are replayable. The existing
EmbodiedAccess port remains the sole authority for Pretorius's location.
"""
from __future__ import annotations

import copy
import json
import uuid

from .embodied_access import EmbodiedAccess, STATIONS
from .habitat_v2 import SpatialHabitat
from .physics import Conflict, LabError, canonical, digest
from .store import GENESIS_HASH, _utc

RULES = "pretorius-domestic-life/1"
# No public street passage yet. The Village-facing room remains sealed there.
ROOM_LABELS = {
    "room:sanctum": "my laboratory",
    "room:experiment": "the experimental chamber",
    "room:hall": "the narrow passage of my house",
    "room:kitchen": "my kitchen",
    "room:bedroom": "my bedroom",
    "room:parlor": "my sitting room",
    "room:shop": "the small curiosity shop",
}

CONTAINERS = {
    "wardrobe:bedroom": ("room:bedroom", "wardrobe", 8, True),
    "drawer:bedside": ("room:bedroom", "bedside drawer", 4, True),
    "cupboard:kitchen": ("room:kitchen", "kitchen cupboard", 8, True),
    "table:kitchen": ("room:kitchen", "kitchen table", 4, False),
    "desk:parlor": ("room:parlor", "writing desk", 5, True),
    "display:shop": ("room:shop", "small display case", 4, True),
    "counter:shop": ("room:shop", "shop counter", 4, False),
    "trunk:hall": ("room:hall", "travelling trunk", 5, True),
}
# A compact initial fixture, not claims of lived possession or identity memories.
START_ITEMS = {
    "garment:coat": ("heavy wool coat", "wardrobe:bedroom"),
    "garment:waistcoat": ("dark waistcoat", "wardrobe:bedroom"),
    "garment:shirts": ("folded shirts", "wardrobe:bedroom"),
    "garment:boots": ("polished boots", "wardrobe:bedroom"),
    "linen:bed": ("spare bed linen", "drawer:bedside"),
    "key:workroom": ("workroom key", "drawer:bedside"),
    "tableware:cup": ("porcelain teacup", "cupboard:kitchen"),
    "tableware:teapot": ("earthenware teapot", "cupboard:kitchen"),
    "food:tea": ("tin of tea", "cupboard:kitchen"),
    "food:bread": ("bread loaf", "table:kitchen"),
    "stationery:paper": ("writing paper", "desk:parlor"),
    "stationery:ink": ("ink bottle", "desk:parlor"),
    "curiosity:compass": ("brass pocket compass", "display:shop"),
    "curiosity:crystal": ("tiny crystal specimen", "display:shop"),
    "curiosity:clockwork": ("clockwork trinket", "counter:shop"),
    "case:specimens": ("travelling specimen case", "trunk:hall"),
}
PRICE_KRAJCZAR = {"curiosity:compass": 80, "curiosity:crystal": 45,
                   "curiosity:clockwork": 35}


def initial_state() -> dict:
    return {
        "containers": {
            cid: {"room": room, "name": name, "capacity": capacity,
                  "openable": openable, "open": not openable}
            for cid, (room, name, capacity, openable) in CONTAINERS.items()
        },
        "items": {
            iid: {"name": name, "container": location, "held_by": None}
            for iid, (name, location) in START_ITEMS.items()
        },
        "shop_open": False,
        # The low stool is a real declared collision affordance, not a
        # pseudo-random narrator trigger. It can be moved out of the path.
        "low_stool_obstructs_path": True,
    }


FIXTURE = initial_state()
FIXTURE_DIGEST = digest(FIXTURE)


def _meta(db):
    return {k: json.loads(v) for k, v in db.execute(
        "SELECT key,value FROM domestic_meta")}


def _put(db, key, value):
    db.execute("INSERT OR REPLACE INTO domestic_meta VALUES (?,?)",
               (key, canonical(value)))


def _body_revision(db, revision: int):
    row = db.execute(
        "SELECT envelope,event_hash FROM embodied_events WHERE revision=?",
        (revision,)).fetchone()
    if row is None:
        raise Conflict("Missing embodied source event")
    return json.loads(row[0]), row[1]


def _current_body(db):
    body = {k: json.loads(v) for k, v in db.execute(
        "SELECT key,value FROM embodied_meta")}
    if not body:
        raise LabError("Embodied subject not initialized")
    return body


def _validate_state(state):
    if set(state) != {"containers", "items", "shop_open", "low_stool_obstructs_path"}:
        raise Conflict("Unknown domestic state shape")
    if set(state["containers"]) != set(CONTAINERS) or set(state["items"]) != set(START_ITEMS):
        raise Conflict("Domestic identities were silently added or removed")
    for cid, obj in state["containers"].items():
        room, label, capacity, openable = CONTAINERS[cid]
        if (obj["room"], obj["name"], obj["capacity"], obj["openable"]) != (
                room, label, capacity, openable):
            raise Conflict("Changed fixed domestic furniture")
        if type(obj["open"]) is not bool or (not openable and not obj["open"]):
            raise Conflict("Invalid furniture openness")
    for iid, obj in state["items"].items():
        if obj["name"] != START_ITEMS[iid][0]:
            raise Conflict("Altered persistent item identity")
        if obj["container"] is None:
            if obj["held_by"] != "research-subject:pretorius":
                raise Conflict("Lost or duplicated item")
        elif obj["container"] not in CONTAINERS or obj["held_by"] is not None:
            raise Conflict("Invalid item location or carried ownership")
    for cid, cont in state["containers"].items():
        if sum(obj["container"] == cid for obj in state["items"].values()) > cont["capacity"]:
            raise Conflict("Container over capacity")
    if type(state["shop_open"]) is not bool or type(state["low_stool_obstructs_path"]) is not bool:
        raise Conflict("Bad world switches")


def _room(station):
    if station not in STATIONS:
        raise Conflict("Unrecognized body station")
    return STATIONS[station][0]


def _look(state, station):
    room = _room(station)
    containers = [obj for obj in state["containers"].values() if obj["room"] == room]
    pieces = [f"I am in {ROOM_LABELS[room]}."]
    if containers:
        names = ", ".join(sorted(obj["name"] + (" (closed)" if not obj["open"] else "")
                                 for obj in containers))
        pieces.append(f"I can see {names}.")
    visible = [obj["name"] for obj in state["items"].values()
               if obj["container"] in state["containers"]
               and state["containers"][obj["container"]]["room"] == room
               and state["containers"][obj["container"]]["open"]]
    if visible:
        pieces.append("I can see " + ", ".join(sorted(visible)) + ".")
    if room == "room:shop":
        pieces.append("The curtain separates this little shop from the house.")
        if not state["shop_open"]:
            pieces.append("The shop remains closed; the front window says OPENING SOON.")
    return " ".join(pieces)


def _apply(state: dict, op: str, args: dict, station: str) -> tuple[dict, dict]:
    """Deterministic state transition; only text in 'subject' can be sent to Doctor."""
    new = copy.deepcopy(state)
    room = _room(station)
    spoken = None
    if op == "walk":
        if set(args) != {"from_station", "to_station"} or args["to_station"] != station:
            raise Conflict("Unverifiable body movement")
        if args["from_station"] not in STATIONS or station not in STATIONS[args["from_station"]][1]:
            raise Conflict("Impossible physical adjacency")
        inner = "I walk into " + ROOM_LABELS[room] + "."
        # A collision occurs from the real, stationary obstacle state on
        # entry. The vocal reflex precedes the subject's reflective appraisal.
        if station == "station:shop:private" and new["low_stool_obstructs_path"]:
            spoken = "Ow! My foot!"
            inner = ("My foot catches against the low stool. I jerk it back. "
                     "That was aloud? I had not meant to say anything.")
    elif op == "look":
        if args:
            raise LabError("Looking accepts no arbitrary payload")
        inner = _look(new, station)
    elif op in {"open", "close"}:
        cid = args.get("container")
        if set(args) != {"container"} or cid not in new["containers"]:
            raise LabError("Unknown furniture")
        fixture = new["containers"][cid]
        if fixture["room"] != room or not fixture["openable"]:
            raise LabError("Furniture cannot be operated from here")
        wanted = op == "open"
        if fixture["open"] == wanted:
            raise Conflict("Furniture is already in that state")
        fixture["open"] = wanted
        inner = f"I {op} the {fixture['name']}."
    elif op == "take":
        item = args.get("item")
        if set(args) != {"item"} or item not in new["items"]:
            raise LabError("Unknown physical item")
        obj = new["items"][item]
        cid = obj["container"]
        if cid is None or new["containers"][cid]["room"] != room or (
                not new["containers"][cid]["open"]):
            raise LabError("Item is inaccessible or inside closed furniture")
        # Keep handling simple: one portable item at once until hands are modeled.
        if any(x["held_by"] for x in new["items"].values()):
            raise Conflict("Hands already occupied")
        obj["container"], obj["held_by"] = None, "research-subject:pretorius"
        inner = f"I take the {obj['name']}."
    elif op == "put":
        if set(args) != {"item", "container"}:
            raise LabError("Put requires an item and a furniture destination")
        item, cid = args["item"], args["container"]
        if item not in new["items"] or cid not in new["containers"]:
            raise LabError("Unknown item or furniture")
        obj, cont = new["items"][item], new["containers"][cid]
        if obj["held_by"] != "research-subject:pretorius":
            raise Conflict("Item must actually be carried")
        if cont["room"] != room or not cont["open"]:
            raise LabError("Target furniture is inaccessible or closed")
        if sum(x["container"] == cid for x in new["items"].values()) >= cont["capacity"]:
            raise Conflict("Target furniture is full")
        obj["container"], obj["held_by"] = cid, None
        inner = f"I put the {obj['name']} in the {cont['name']}."
    elif op == "shift_stool":
        if set(args) != {"obstructs_path"} or type(args["obstructs_path"]) is not bool:
            raise LabError("Shifting the stool requires an explicit position")
        if room != "room:shop":
            raise LabError("The stool is not here")
        if args["obstructs_path"] == new["low_stool_obstructs_path"]:
            raise Conflict("Stool already in the requested position")
        new["low_stool_obstructs_path"] = args["obstructs_path"]
        inner = ("I leave the stool in the narrow path." if args["obstructs_path"]
                 else "I move the low stool away from the narrow path.")
    else:
        raise LabError("Not a permitted domestic action")
    _validate_state(new)
    return new, {"inner": inner, "spoken_aloud": spoken}


class HomeLife:
    """Durable, replayable domestic interactions against the real embodied port."""

    def __init__(self, habitat: SpatialHabitat):
        self.habitat = habitat

    def initialize(self) -> dict:
        self.habitat.verify()
        # This is the same existing embodied subject, not a second avatar.
        body = EmbodiedAccess(self.habitat)
        with self.habitat._open() as db:
            has_body = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='embodied_meta'"
            ).fetchone() is not None
        if not has_body:
            body.initialize()
        else:
            body.verify()
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            host = SpatialHabitat._metadata(db)
            subject = _current_body(db)
            db.execute("""CREATE TABLE IF NOT EXISTS domestic_meta(
                key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS domestic_events(
                revision INTEGER PRIMARY KEY,
                event_id TEXT UNIQUE NOT NULL,
                envelope TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                event_hash TEXT UNIQUE NOT NULL)""")
            m = _meta(db)
            if not m:
                for key, value in {
                    "rules": RULES, "fixture_digest": FIXTURE_DIGEST,
                    "lab_id": host["lab_id"], "home_id": host["home_id"],
                    "world_epoch": host["world_epoch"], "mode": host["mode"],
                    "genesis": FIXTURE, "state": FIXTURE,
                    "revision": 0, "head_hash": GENESIS_HASH,
                    "body_seen": subject["revision"],
                    "body_at_install": subject["revision"],
                }.items():
                    _put(db, key, value)
            elif (m["lab_id"], m["world_epoch"], m["fixture_digest"]) != (
                    host["lab_id"], host["world_epoch"], FIXTURE_DIGEST):
                raise Conflict("Domestic environment belongs to a different world")
        return self.verify()

    def _catch_up(self) -> None:
        """Replay any unsurfaced body steps (including those after a crash)."""
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            m = _meta(db)
            body = _current_body(db)
            if (m["lab_id"], m["world_epoch"]) != (body["lab_id"], body["world_epoch"]):
                raise Conflict("Body is not in this Laboratory")
            for revision in range(m["body_seen"] + 1, body["revision"] + 1):
                movement, cursor = _body_revision(db, revision)
                if movement["kind"] == "move":
                    args = {"from_station": movement["before_station"],
                            "to_station": movement["after_station"]}
                    self._append(db, m, "walk", args, movement["after_station"],
                                 revision, cursor, "motion:" + cursor[:32])
                m["body_seen"] = revision
            _put(db, "body_seen", m["body_seen"])

    def _append(self, db, m, op, args, station, body_revision, body_cursor, event_id):
        existing = db.execute(
            "SELECT envelope,event_hash FROM domestic_events WHERE event_id=?",
            (event_id,)).fetchone()
        if existing:
            e = json.loads(existing[0])
            if e["op"] != op or e["args"] != args:
                raise Conflict("Domestic action ID reused with different payload")
            return {**e, "event_hash": existing[1]}
        before = m["state"]
        after, subject = _apply(before, op, args, station)
        e = {
            "event_id": event_id, "op": op, "args": args,
            "lab_id": m["lab_id"], "home_id": m["home_id"],
            "world_epoch": m["world_epoch"],
            "revision": m["revision"] + 1,
            "before_digest": digest(before), "after_digest": digest(after),
            "body_revision": body_revision, "body_cursor": body_cursor,
            "station": station, "subject": subject,
            "previous_hash": m["head_hash"], "utc": _utc(),
        }
        cursor = digest(e)
        db.execute("INSERT INTO domestic_events VALUES (?,?,?,?,?)",
                   (e["revision"], event_id, canonical(e), m["head_hash"], cursor))
        m["state"], m["revision"], m["head_hash"] = after, e["revision"], cursor
        for key in ("state", "revision", "head_hash"):
            _put(db, key, m[key])
        return {**e, "event_hash": cursor}

    def verify(self) -> dict:
        world = self.habitat.verify()
        body = EmbodiedAccess(self.habitat).verify()
        with self.habitat._open() as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='domestic_meta'").fetchone() is None:
                raise LabError("Domestic life is not initialized")
            m = _meta(db)
            if (m["rules"], m["fixture_digest"], m["lab_id"], m["home_id"],
                    m["world_epoch"], m["mode"]) != (
                    RULES, FIXTURE_DIGEST, world["lab_id"], world["home_id"],
                    world["world_epoch"], world["mode"]):
                raise Conflict("Domestic provenance or rules mismatch")
            state = copy.deepcopy(m["genesis"])
            if digest(state) != FIXTURE_DIGEST:
                raise Conflict("Altered domestic genesis")
            _validate_state(state)
            previous, rev = GENESIS_HASH, 0
            body_at_install = m["body_at_install"]
            if type(body_at_install) is not int or body_at_install < 0 or body_at_install > body["revision"]:
                raise Conflict("Invalid domestic initial body revision")
            for n, eid, encoded, prior, head in db.execute(
                    "SELECT revision,event_id,envelope,prev_hash,event_hash "
                    "FROM domestic_events ORDER BY revision"):
                e = json.loads(encoded)
                if (n != rev + 1 or n != e["revision"] or eid != e["event_id"]
                        or prior != previous or e["previous_hash"] != previous
                        or head != digest(e)):
                    raise Conflict("Broken domestic event history")
                if (e["lab_id"], e["home_id"], e["world_epoch"]) != (
                        m["lab_id"], m["home_id"], m["world_epoch"]):
                    raise Conflict("Foreign world in domestic event")
                bod, cursor = _body_revision(db, e["body_revision"]) if e["body_revision"] else (None, GENESIS_HASH)
                if e["body_revision"] and cursor != e["body_cursor"]:
                    raise Conflict("Domestic event's embodied source changed")
                if not e["body_revision"] and e["body_cursor"] != GENESIS_HASH:
                    raise Conflict("Domestic event missing embodied proof")
                if e["body_revision"] < body_at_install or e["body_revision"] > body["revision"]:
                    raise Conflict("Impossible referenced body revision")
                # Body pose at this revision is the destination, or initial
                # station when the home was installed with revision zero.
                station = bod["after_station"] if bod else "station:threshold"
                if (e["station"] != station or e["before_digest"] != digest(state)):
                    raise Conflict("Domestic access or previous state falsified")
                if e["op"] == "walk":
                    if not bod or bod["kind"] != "move" or (
                            e["args"]["from_station"] != bod["before_station"]):
                        raise Conflict("Reflex event is not justified by a body move")
                else:
                    # A look action at a body revision after a move has the
                    # station where the actor genuinely arrived.
                    if e["op"] not in {"look", "open", "close", "take", "put", "shift_stool"}:
                        raise Conflict("Invalid domestic operation")
                after, outcome = _apply(state, e["op"], e["args"], station)
                if e["after_digest"] != digest(after) or e["subject"] != outcome:
                    raise Conflict("Tampered bodily outcome or narrated experience")
                state, previous, rev = after, head, n
            if (m["revision"], m["head_hash"], m["state"]) != (rev, previous, state):
                raise Conflict("Domestic snapshot diverged from replay")
            if type(m["body_seen"]) is not int or not (
                    body_at_install <= m["body_seen"] <= body["revision"]):
                raise Conflict("Invalid reconciled body cursor")
            return {"verified": True, "revision": rev,
                    "head_hash": previous, "world_epoch": m["world_epoch"],
                    "body_seen": m["body_seen"], "pending_body_events": body["revision"] - m["body_seen"]}

    def _do(self, op: str, args: dict, *, event_id: str | None = None) -> dict:
        self.verify()
        self._catch_up()
        event_id = event_id or uuid.uuid4().hex
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
            raise LabError("Invalid domestic event ID")
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            m, bod = _meta(db), _current_body(db)
            # The operator has no permission to invent a new pose.
            if m["body_seen"] != bod["revision"]:
                raise Conflict("Embodied movement must be reconciled first")
            return self._append(db, m, op, args, bod["station"],
                                bod["revision"], bod["head_hash"], event_id)

    def walk(self, station: str, *, event_id: str | None = None) -> dict:
        self.verify()
        self._catch_up()
        if event_id is not None and (
                not isinstance(event_id, str) or len(event_id) > 90 or not event_id):
            raise LabError("Invalid movement event ID")
        receipt = EmbodiedAccess(self.habitat).move(
            station, event_id=event_id or uuid.uuid4().hex)
        self._catch_up()
        with self.habitat._open() as db:
            row = db.execute("SELECT envelope FROM domestic_events WHERE event_id=?",
                             ("motion:" + receipt["event_hash"][:32],)).fetchone()
            if not row:
                raise Conflict("Embodied movement not present in domestic ledger")
            return json.loads(row[0])["subject"]

    def look(self, *, event_id: str | None = None) -> dict:
        return self._do("look", {}, event_id=event_id)["subject"]

    def open(self, container: str, *, event_id: str | None = None):
        return self._do("open", {"container": container}, event_id=event_id)["subject"]

    def close(self, container: str, *, event_id: str | None = None):
        return self._do("close", {"container": container}, event_id=event_id)["subject"]

    def take(self, item: str, *, event_id: str | None = None):
        return self._do("take", {"item": item}, event_id=event_id)["subject"]

    def put(self, item: str, container: str, *, event_id: str | None = None):
        return self._do("put", {"item": item, "container": container},
                        event_id=event_id)["subject"]

    def shift_stool(self, *, obstructs_path: bool, event_id: str | None = None):
        return self._do("shift_stool", {"obstructs_path": obstructs_path},
                        event_id=event_id)["subject"]

    def shop_manifest(self) -> dict:
        """Engineer-only, read-only handoff proposal; no Village synchronizer."""
        self.verify()
        self._catch_up()
        with self.habitat._open() as db:
            m = _meta(db)
            stock = [
                {"object_id": iid, "display_name": obj["name"],
                 "price_krajczar": PRICE_KRAJCZAR[iid]}
                for iid, obj in sorted(m["state"]["items"].items())
                if iid in PRICE_KRAJCZAR and obj["container"] == "display:shop"
            ]
            return {"lab_id": m["lab_id"], "home_id": m["home_id"],
                    "world_epoch": m["world_epoch"], "revision": m["revision"],
                    "head_hash": m["head_hash"], "shop_open": m["state"]["shop_open"],
                    "stock": stock, "mode": "read_only_not_a_village_sale"}

    def audit_state(self) -> dict:
        """Engineer-only; NEVER send this dictionary to the subject."""
        self.verify()
        self._catch_up()
        with self.habitat._open() as db:
            return copy.deepcopy(_meta(db)["state"])
