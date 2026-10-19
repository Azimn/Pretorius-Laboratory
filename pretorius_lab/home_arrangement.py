"""Opt-in persisted furniture arrangements inside the existing Laboratory world.

Deliberately shallow physical model: room + relative placement + orientation.
We keep consequential state, not micrometre coordinates or invented furniture
physics. Changes are append-only, replayed against historical bodily location,
daylight and the real shared home/world epoch.
"""
from __future__ import annotations

import copy
import json
import uuid

from .daily_rhythm import DailyRhythm, PAPER_RULES, _can_see
from .embodied_access import EmbodiedAccess, STATIONS
from .habitat_v2 import SpatialHabitat
from .home_life import HomeLife
from .material_objects import meta, cursor, pose, historic_days
from .physics import Conflict, LabError, canonical, digest
from .store import GENESIS_HASH, _utc

RULES = "pretorius-domestic-arrangement/1"
ROOM = "room:parlor"
ANCHORS = {
    "parlor:window": "beside the window",
    "parlor:hearth": "near the fireplace",
    "parlor:desk": "beside the writing desk",
    "parlor:door": "near the doorway",
}
START = {
    "chair:parlor": {
        "name": "upholstered reading chair",
        "room": ROOM, "anchor": "parlor:hearth", "facing": "parlor:hearth"
    },
    "table:parlor": {
        "name": "small side table",
        "room": ROOM, "anchor": "parlor:desk", "facing": "parlor:window"
    },
}
ORIGINAL = copy.deepcopy(START)
INITIAL_HASH = digest(ORIGINAL)


def exists(db):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='arrangement_meta'"
    ).fetchone() is not None


def _meta(db):
    return {k: json.loads(v) for k, v in db.execute(
        "SELECT key,value FROM arrangement_meta")}


def _set(db, key, value):
    db.execute("INSERT OR REPLACE INTO arrangement_meta VALUES (?,?)",
               (key, canonical(value)))


def validate(state):
    if type(state) is not dict or set(state) != set(START):
        raise Conflict("Unrecognized physical furniture identities")
    occupied = set()
    for oid, item in state.items():
        if (type(item) is not dict or set(item) !=
                {"name", "room", "anchor", "facing"} or
                (item["name"], item["room"]) !=
                (START[oid]["name"], START[oid]["room"]) or
                item["anchor"] not in ANCHORS or
                item["facing"] not in ANCHORS or
                item["anchor"] in occupied):
            raise Conflict("Furniture identity, location or clearance has drifted")
        occupied.add(item["anchor"])


def transition(state, op, args, station, rhythm):
    """Pure deterministic changed-furniture operation, no arbitrary patches."""
    if type(args) is not dict or station not in STATIONS:
        raise LabError("Invalid furniture action or actor pose")
    if STATIONS[station][0] != ROOM:
        raise Conflict("I cannot rearrange furniture in a different room")
    if not _can_see(rhythm, ROOM):
        raise Conflict("I cannot safely rearrange furniture in darkness")
    expected = {"move": {"object", "anchor"}, "turn": {"object", "facing"}}
    if op not in expected or set(args) != expected[op]:
        raise LabError("Specify a real movable furnishing and valid relation")
    oid = args["object"]
    if type(oid) is not str or oid not in state:
        raise Conflict("I cannot find that movable furnishing")
    result = copy.deepcopy(state)
    if op == "move":
        anchor = args["anchor"]
        if anchor not in ANCHORS or anchor == result[oid]["anchor"]:
            raise Conflict("No different, known free place for this furnishing")
        if any(other["anchor"] == anchor for
               key, other in result.items() if key != oid):
            raise Conflict("Another furnishing occupies that place")
        result[oid]["anchor"] = anchor
        inner = ("I move the " + result[oid]["name"] + " " +
                 ANCHORS[anchor] + ".")
    else:
        facing = args["facing"]
        if facing not in ANCHORS or result[oid]["facing"] == facing:
            raise Conflict("The furnishing already faces there, or direction is unknown")
        result[oid]["facing"] = facing
        inner = ("I turn the " + result[oid]["name"] +
                 " to face " + ANCHORS[facing].removeprefix("beside ").removeprefix("near ") + ".")
    validate(result)
    return result, {"inner": inner, "spoken_aloud": None}


class HomeArrangements:
    """Small durable ledger for furnishings; old domestic reducer unchanged."""

    def __init__(self, habitat):
        self.habitat = habitat

    def initialize(self, *, initial_state=None, parent=None):
        HomeLife(self.habitat).verify()
        DailyRhythm(self.habitat).verify()
        body = EmbodiedAccess(self.habitat).verify()
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            if exists(db):
                raise Conflict("Furniture profile already installed")
            daily = meta(db, "rhythm_meta")
            home = meta(db, "domestic_meta")
            world = SpatialHabitat._metadata(db)
            if daily["rules"] != PAPER_RULES:
                raise LabError("Furniture arrangements need the existing v5 lived home")
            seed = copy.deepcopy(initial_state if initial_state is not None else START)
            validate(seed)
            if initial_state is not None and not isinstance(parent, dict):
                raise Conflict("Inherited room needs parent provenance")
            db.execute("CREATE TABLE arrangement_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("""CREATE TABLE arrangement_events(
                revision INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE,
                envelope TEXT NOT NULL,prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE)""")
            values = {
                "rules": RULES, "world_epoch": world["world_epoch"],
                "home_id": world["home_id"], "lab_id": world["lab_id"],
                "genesis": seed, "genesis_hash": digest(seed),
                "parent": parent, "state": seed, "revision": 0,
                "head_hash": GENESIS_HASH,
                "body_at_install": body["revision"],
                "home_at_install": home["revision"],
                "rhythm_at_install": daily["revision"],
            }
            for key, value in values.items():
                _set(db, key, value)
        return self.verify()

    def verify(self):
        world = self.habitat.verify()
        HomeLife(self.habitat).verify()
        DailyRhythm(self.habitat).verify()
        bodyproof = EmbodiedAccess(self.habitat).verify()
        with self.habitat._open() as db:
            if not exists(db):
                raise LabError("Furniture profile has not been installed")
            m = _meta(db)
            if (m["rules"] != RULES or
                    (m["lab_id"], m["home_id"], m["world_epoch"]) !=
                    (world["lab_id"], world["home_id"], world["world_epoch"])):
                raise Conflict("Furniture authority belongs to another world")
            if digest(m["genesis"]) != m["genesis_hash"] or (
                    m["parent"] is None and m["genesis_hash"] != INITIAL_HASH):
                raise Conflict("Furniture starting state was rewritten")
            state = copy.deepcopy(m["genesis"])
            validate(state)
            house = meta(db, "domestic_meta")
            daily = meta(db, "rhythm_meta")
            body = meta(db, "embodied_meta")
            times = historic_days(db)
            last_br, last_hr, last_rr = (
                m["body_at_install"], m["home_at_install"],
                m["rhythm_at_install"])
            prev, rev = GENESIS_HASH, 0
            for n, eid, encoded, old_hash, h in db.execute(
                    "SELECT revision,event_id,envelope,prev_hash,event_hash "
                    "FROM arrangement_events ORDER BY revision"):
                e = json.loads(encoded)
                if (n != rev + 1 or eid != e["event_id"]
                        or e["revision"] != n or old_hash != prev
                        or e["previous_hash"] != prev or digest(e) != h
                        or (e["lab_id"], e["home_id"], e["world_epoch"]) !=
                        (m["lab_id"], m["home_id"], m["world_epoch"])):
                    raise Conflict("Furniture change history was modified")
                br, hr, rr = (
                    e["body_revision"], e["home_revision"], e["rhythm_revision"])
                if not (last_br <= br <= bodyproof["revision"] and
                        last_hr <= hr <= house["revision"] and
                        last_rr <= rr <= daily["revision"]):
                    raise Conflict("Furniture act cites an impossible old source")
                if (e["body_cursor"] != cursor(db, "embodied_events", br) or
                        e["home_cursor"] != cursor(db, "domestic_events", hr) or
                        e["rhythm_cursor"] != cursor(db, "rhythm_events", rr)):
                    raise Conflict("Furniture action lacks real actor/world provenance")
                station = pose(db, br, body)
                if (station != e["station"] or
                        times[rr]["minute"] != e["minute"] or
                        e["before_digest"] != digest(state)):
                    raise Conflict("Furniture action occurred at an invented place or time")
                changed, subject = transition(
                    state, e["op"], e["args"], station, times[rr])
                if e["after_digest"] != digest(changed) or e["subject"] != subject:
                    raise Conflict("Furniture outcome fails causal replay")
                state, prev, rev = changed, h, n
                last_br, last_hr, last_rr = br, hr, rr
            if (m["revision"], m["head_hash"], m["state"]) != (rev, prev, state):
                raise Conflict("Current room layout differs from recorded changes")
            return {"verified": True, "revision": rev,
                    "world_epoch": m["world_epoch"], "head_hash": prev}

    def audit_state(self):
        self.verify()
        with self.habitat._open() as db:
            return copy.deepcopy(_meta(db)["state"])

    def act(self, op, *, event_id=None, **args):
        self.verify()
        HomeLife(self.habitat)._catch_up()
        eid = event_id or uuid.uuid4().hex
        if type(eid) is not str or not 1 <= len(eid) <= 90:
            raise LabError("Invalid domestic change event ID")
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            m = _meta(db)
            old = db.execute(
                "SELECT envelope FROM arrangement_events WHERE event_id=?",
                (eid,)).fetchone()
            if old:
                e = json.loads(old[0])
                if e["op"] != op or e["args"] != args:
                    raise Conflict("One action ID cannot cause two room changes")
                return copy.deepcopy(e["subject"])
            house, clock, body = (
                meta(db, "domestic_meta"), meta(db, "rhythm_meta"),
                meta(db, "embodied_meta"))
            new, subject = transition(
                m["state"], op, args, body["station"], clock["state"])
            e = {
                "event_id": eid, "revision": m["revision"] + 1,
                "op": op, "args": args,
                "world_epoch": m["world_epoch"], "home_id": m["home_id"],
                "lab_id": m["lab_id"], "station": body["station"],
                "minute": clock["state"]["minute"],
                "body_revision": body["revision"],
                "body_cursor": body["head_hash"],
                "home_revision": house["revision"],
                "home_cursor": house["head_hash"],
                "rhythm_revision": clock["revision"],
                "rhythm_cursor": clock["head_hash"],
                "before_digest": digest(m["state"]),
                "after_digest": digest(new), "subject": subject,
                "previous_hash": m["head_hash"], "utc": _utc(),
            }
            h = digest(e)
            db.execute("INSERT INTO arrangement_events VALUES(?,?,?,?,?)",
                       (e["revision"], eid, canonical(e), m["head_hash"], h))
            _set(db, "revision", e["revision"])
            _set(db, "head_hash", h)
            _set(db, "state", new)
            return copy.deepcopy(subject)

    def observe(self):
        """Only physically visible arrangement, never offstage contents."""
        self.verify()
        with self.habitat._open() as db:
            m = _meta(db)
            clock = meta(db, "rhythm_meta")["state"]
            body = meta(db, "embodied_meta")["station"]
            if (STATIONS[body][0] != ROOM or not _can_see(clock, ROOM)):
                return {"inner": "I cannot presently make out the sitting-room arrangement.",
                        "spoken_aloud": None}
            phrases = [
                "the " + item["name"] + " " + ANCHORS[item["anchor"]] +
                ", facing " + ANCHORS[item["facing"]]
                for item in m["state"].values()
            ]
            return {"inner": "I can see " + "; ".join(phrases) + ".",
                    "spoken_aloud": None}

    def available(self):
        self.verify()
        with self.habitat._open() as db:
            m = _meta(db)
            clock = meta(db, "rhythm_meta")["state"]
            body = meta(db, "embodied_meta")["station"]
            choices = []
            for oid, rec in sorted(m["state"].items()):
                for anchor in ANCHORS:
                    choices.extend((
                        ("move", {"object": oid, "anchor": anchor}),
                        ("turn", {"object": oid, "facing": anchor})))
            valid = []
            for op, args in choices:
                try:
                    transition(m["state"], op, args, body, clock)
                except (Conflict, LabError):
                    continue
                name = m["state"][args["object"]]["name"]
                if op == "move":
                    description = "move the " + name + " " + ANCHORS[args["anchor"]]
                else:
                    destination = ANCHORS[args["facing"]]
                    # Make direction distinct in ordinary language. A model
                    # should not receive five identical "reposition" options
                    # that secretly correspond to different source actions.
                    direction = (destination.replace("beside ", "")
                                 .replace("near ", ""))
                    description = "turn the " + name + " to face " + direction
                valid.append({"op": op, "args": args,
                              "description": description})
            return valid

    def _fork_into(self, clone):
        proof = self.verify()
        with self.habitat._open() as db:
            m = _meta(db)
            inherited = copy.deepcopy(m["state"])
            source = {"world_epoch": m["world_epoch"], "revision": m["revision"],
                      "head_hash": proof["head_hash"],
                      "status": "copied_furniture_positions_not_lived_events"}
        return HomeArrangements(clone).initialize(
            initial_state=inherited, parent=source)
