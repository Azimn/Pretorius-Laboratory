"""Dynamic botanical objects in the SAME append-only Laboratory SQLite world.

Experimental material component prototype, not an alternate clock or brain.
"""
from __future__ import annotations
import copy
import json
import re
import uuid

from .daily_rhythm import (DailyRhythm, PAPER_RULES, _home_snapshots,
                           _stock_access, _writing_access, _can_see,
                           transition as daily_transition)
from .embodied_access import EmbodiedAccess, STATIONS
from .habitat_v2 import SpatialHabitat
from .home_life import HomeLife
from .physics import LabError, Conflict, canonical, digest
from .store import GENESIS_HASH, _utc

RULES = "pretorius-material-objects/botanical-v1"
DRY_MINUTES = 72 * 60
ACTOR = "research-subject:pretorius"
FIXTURE_IDS = ("plant:rose-001", "tool:flower-press",
               "supply:blotter", "sheet:herbarium-001")


def obj(kind, name, parent, stage="ready", origin=None, minute=None, label=None):
    return dict(kind=kind, name=name, parent=parent, stage=stage,
                origin=origin, pressed_minute=minute, label=label)


def genesis():
    return {"objects": {
        "plant:rose-001": obj("flower", "a cut rose", "table:kitchen", "fresh"),
        "tool:flower-press": obj("press", "a wooden flower press", "desk:parlor"),
        "supply:blotter": obj("blotter", "drying blotter sheets", "desk:parlor"),
        "sheet:herbarium-001": obj("mount", "a blank herbarium sheet", "desk:parlor"),
    }, "next_specimen": 1}


FIXTURE = genesis()
FIXTURE_HASH = digest(FIXTURE)


def exists(db):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='botanical_meta'"
    ).fetchone() is not None


def meta(db, table):
    return {k: json.loads(v) for k, v in db.execute(
        "SELECT key,value FROM " + table)}


def write(db, key, value):
    db.execute("INSERT OR REPLACE INTO botanical_meta VALUES (?,?)",
               (key, canonical(value)))


def cursor(db, table, rev):
    if rev == 0:
        return GENESIS_HASH
    row = db.execute("SELECT event_hash FROM " + table + " WHERE revision=?",
                     (rev,)).fetchone()
    return row[0] if row else None


def pose(db, br, body):
    if br == 0:
        return body["initial_station"]
    row = db.execute("SELECT envelope FROM embodied_events WHERE revision=?",
                     (br,)).fetchone()
    if not row:
        raise Conflict("Missing physical actor's historical pose")
    return json.loads(row[0])["after_station"]


def historic_days(db):
    """Independent deterministic replay of historically recorded world time."""
    clock = meta(db, "rhythm_meta")
    homes = _home_snapshots(db)
    state = copy.deepcopy(clock["genesis"])
    from .care_contract import valid as validated_care
    care = validated_care(db)
    series = {0: state}
    delivered_days = set()
    for n, payload in db.execute(
            "SELECT revision,envelope FROM rhythm_events ORDER BY revision"):
        e = json.loads(payload)
        if n != len(series) or digest(state) != e["before_digest"]:
            raise Conflict("Missing historical world clock revision")
        home = homes[e["home_revision"]]
        delivery_day = e["args"].get("day") if e["op"] == "accept_delivery" else None
        new, subjective = daily_transition(
            state, e["op"], e["args"], e["station"],
            stock_access=_stock_access(home, e["station"]),
            writing_access=_writing_access(home, e["station"]),
            delivery_authorized=(
                clock["rules"] == PAPER_RULES and care is not None
                and type(delivery_day) is int
                and delivery_day > care["installed_at_minute"] // 1440
                and delivery_day not in delivered_days),
            care_authorized=care is not None)
        if e["op"] == "accept_delivery":
            delivered_days.add(delivery_day)
        if digest(new) != e["after_digest"] or subjective != e["subject"]:
            raise Conflict("World-clock history has been rewritten")
        series[n] = new
        state = new
    if state != clock["state"]:
        raise Conflict("Current clock and event history differ")
    return series


def validate(state):
    if (type(state) is not dict or set(state) != {"objects", "next_specimen"}
            or type(state["objects"]) is not dict or
            type(state["next_specimen"]) is not int or
            not 1 <= state["next_specimen"] <= 1001):
        raise Conflict("Malformed material object graph")
    items = state["objects"]
    if (not set(FIXTURE_IDS) <= set(items) or
            len(items) != len(FIXTURE_IDS) + state["next_specimen"] - 1):
        raise Conflict("Missing material ancestor or invented specimen")
    sources = set()
    for oid, item in items.items():
        if (type(oid) is not str or not re.fullmatch(r"[a-z][a-z0-9:._-]{1,63}", oid)
                or type(item) is not dict or
                set(item) != {"kind", "name", "parent", "stage",
                              "origin", "pressed_minute", "label"}):
            raise Conflict("Invalid material identity or record")
        if oid in FIXTURE_IDS:
            if (item["kind"], item["name"]) != (
                    FIXTURE["objects"][oid]["kind"], FIXTURE["objects"][oid]["name"]):
                raise Conflict("Fixed material source was changed")
        else:
            if oid != f"specimen:{len(sources)+1:04d}" or item["kind"] != "specimen":
                raise Conflict("Generated specimens have false identities")
            if item["origin"] != "plant:rose-001" or item["origin"] in sources:
                raise Conflict("Multiple descendants from a single flower")
            sources.add(item["origin"])
        if item["kind"] not in ("flower", "press", "blotter", "mount", "specimen"):
            raise Conflict("Unknown material type")
        if item["stage"] not in (
                "fresh", "ready", "pressing", "transformed", "dry", "mounted"):
            raise Conflict("Invalid physical condition")
        parent = item["parent"]
        if parent is None and item["stage"] != "transformed":
            raise Conflict("Material cannot disappear without transformation")
        if parent not in (
                None, ACTOR, *FIXTURE_IDS,
                "table:kitchen", "desk:parlor", "trunk:hall",
                "cupboard:kitchen", "drawer:bedside", "wardrobe:bedroom",
                "display:shop", "counter:shop"):
            raise Conflict("Unknown physical container or owner")
        if parent == oid:
            raise Conflict("Circular object containment")
        if item["pressed_minute"] is not None and (
                type(item["pressed_minute"]) is not int or
                item["pressed_minute"] < 0):
            raise Conflict("Invalid historical drying time")
        if item["label"] is not None and (
                item["kind"] != "specimen" or item["stage"] != "mounted" or
                type(item["label"]) is not str or not item["label"].strip() or
                len(item["label"]) > 160):
            raise Conflict("Malformed herbarium label")
    if len(sources) != state["next_specimen"] - 1:
        raise Conflict("Object creation counter is not grounded")
    if items["plant:rose-001"]["stage"] == "transformed" and not sources:
        raise Conflict("Flower vanished without leaving its specimen")


def root(state, oid):
    visited = set()
    while oid in state["objects"]:
        if oid in visited:
            raise Conflict("Physical object graph contains a cycle")
        visited.add(oid)
        oid = state["objects"][oid]["parent"]
    return oid


def accessible(state, oid, home, station):
    location = root(state, oid)
    if location == ACTOR:
        return True
    container = home["containers"].get(location)
    return bool(container and container["room"] == STATIONS[station][0]
                and container["open"])


def capacity(state, home, container):
    return (sum(x["container"] == container for x in home["items"].values()) +
            sum(x["parent"] == container for x in state["objects"].values())
            < home["containers"][container]["capacity"])


def transition(state, op, args, station, home, rhythm):
    """Pure reducer; never accepts raw state rewrites or invented timestamps."""
    if station not in STATIONS or type(args) is not dict:
        raise LabError("Unknown actor or malformed botanical activity")
    if not _can_see(rhythm, STATIONS[station][0]):
        raise Conflict("I need light to work with these materials")
    new = copy.deepcopy(state)
    items = new["objects"]
    minute = rhythm["minute"]
    if op == "take":
        oid = args.get("object")
        if (set(args) != {"object"} or oid not in items or
                items[oid]["kind"] not in ("flower", "mount") or
                items[oid]["stage"] not in ("fresh", "ready") or
                items[oid]["parent"] in items or
                not accessible(new, oid, home, station) or
                items[oid]["parent"] in (None, ACTOR) or
                any(o["parent"] == ACTOR for o in items.values()) or
                any(o["held_by"] == ACTOR for o in home["items"].values())):
            raise Conflict("I cannot pick up that physical material")
        items[oid]["parent"] = ACTOR
        inner = "I take " + items[oid]["name"] + "."
    elif op == "put":
        oid, cid = args.get("object"), args.get("container")
        if (set(args) != {"object", "container"} or oid not in items or
                items[oid]["parent"] != ACTOR or cid not in home["containers"]
                or home["containers"][cid]["room"] != STATIONS[station][0]
                or not home["containers"][cid]["open"] or
                not capacity(new, home, cid)):
            raise Conflict("That furniture cannot receive the object")
        items[oid]["parent"] = cid
        inner = "I put " + items[oid]["name"] + " into the " + home["containers"][cid]["name"] + "."
    elif op == "start_press":
        flower = items["plant:rose-001"]
        if (set(args) != {"flower"} or args["flower"] != "plant:rose-001"
                or flower["stage"] != "fresh" or flower["parent"] != ACTOR
                or not accessible(new, "tool:flower-press", home, station)
                or not accessible(new, "supply:blotter", home, station)):
            raise Conflict("I need an actual flower, press and blotting paper")
        flower["parent"] = "tool:flower-press"
        flower["stage"] = "pressing"
        flower["pressed_minute"] = minute
        inner = "I put the rose between blotters beneath the flower press."
    elif op == "finish_press":
        flower = items["plant:rose-001"]
        if (set(args) != {"flower"} or args["flower"] != "plant:rose-001"
                or flower["stage"] != "pressing"
                or flower["parent"] != "tool:flower-press"
                or not accessible(new, "tool:flower-press", home, station)
                or minute - flower["pressed_minute"] < DRY_MINUTES):
            raise Conflict("There is no fully dried rose beneath my reachable press")
        oid = f"specimen:{new['next_specimen']:04d}"
        if oid in items:
            raise Conflict("This physical object already exists")
        items[oid] = obj("specimen", "a dried pressed rose", "tool:flower-press",
                         "dry", origin="plant:rose-001", minute=flower["pressed_minute"])
        new["next_specimen"] += 1
        flower["parent"], flower["stage"] = None, "transformed"
        inner = "I lift a distinct dried rose specimen from the press."
    elif op == "mount":
        oid = args.get("specimen")
        if (set(args) != {"specimen"} or oid not in items or
                items[oid]["kind"] != "specimen" or items[oid]["stage"] != "dry"
                or items[oid]["parent"] != "tool:flower-press"
                or not accessible(new, "tool:flower-press", home, station)
                or not accessible(new, "sheet:herbarium-001", home, station)):
            raise Conflict("I cannot mount an inaccessible or unpressed specimen")
        items[oid]["stage"], items[oid]["parent"] = "mounted", "sheet:herbarium-001"
        inner = "I mount the dried rose on my herbarium sheet."
    elif op == "label":
        oid, text = args.get("specimen"), args.get("text")
        if (set(args) != {"specimen", "text"} or oid not in items or
                items[oid]["kind"] != "specimen" or
                items[oid]["stage"] != "mounted" or
                items[oid]["label"] is not None or
                type(text) is not str or not text.strip() or len(text) > 160 or
                any(ord(ch) < 32 and ch != "\n" for ch in text) or
                not accessible(new, "sheet:herbarium-001", home, station) or
                not all(_writing_access(home, station).values())):
            raise Conflict("I need my mounted specimen, paper and ink")
        items[oid]["label"] = text
        inner = "I inscribe beside the rose: " + text
    else:
        raise LabError("No such physical transformation")
    validate(new)
    return new, {"inner": inner, "spoken_aloud": None}


class MaterialObjects:
    """Append-only physical objects, using the existing Lab epoch and clock."""

    def __init__(self, habitat):
        self.habitat = habitat

    def initialize(self, *, initial_state=None, parent=None):
        HomeLife(self.habitat).verify()
        DailyRhythm(self.habitat).verify()
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            if exists(db):
                raise Conflict("A material collection already exists")
            h = meta(db, "domestic_meta")
            r = meta(db, "rhythm_meta")
            b = meta(db, "embodied_meta")
            world = SpatialHabitat._metadata(db)
            if r["rules"] != PAPER_RULES:
                raise LabError("Botanical objects require v5 physically writable home")
            state = copy.deepcopy(initial_state if initial_state is not None else FIXTURE)
            validate(state)
            if initial_state is not None and type(parent) is not dict:
                raise Conflict("Forked material state requires parent proof")
            for cid, container in h["state"]["containers"].items():
                if not capacity(state, h["state"], cid) and (
                        sum(o["container"] == cid for o in h["state"]["items"].values()) +
                        sum(o["parent"] == cid for o in state["objects"].values())
                        > container["capacity"]):
                    raise Conflict("Material fixture overcrowds the existing furniture")
            db.execute("CREATE TABLE botanical_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("""CREATE TABLE botanical_events(
                revision INTEGER PRIMARY KEY,event_id TEXT NOT NULL UNIQUE,
                envelope TEXT NOT NULL,prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE)""")
            values = {"rules": RULES, "lab_id": world["lab_id"],
                      "home_id": world["home_id"], "world_epoch": world["world_epoch"],
                      "genesis": state, "genesis_digest": digest(state),
                      "parent": parent, "state": state,
                      "revision": 0, "head_hash": GENESIS_HASH,
                      "body_at_install": b["revision"], "home_at_install": h["revision"],
                      "rhythm_at_install": r["revision"]}
            for key, value in values.items():
                write(db, key, value)
        return self.verify()

    def verify(self):
        world = self.habitat.verify()
        HomeLife(self.habitat).verify()
        DailyRhythm(self.habitat).verify()
        body_proof = EmbodiedAccess(self.habitat).verify()
        with self.habitat._open() as db:
            if not exists(db):
                raise LabError("Botanical material is not initialized")
            m = meta(db, "botanical_meta")
            if (m["rules"] != RULES or
                    (m["lab_id"], m["home_id"], m["world_epoch"]) !=
                    (world["lab_id"], world["home_id"], world["world_epoch"])):
                raise Conflict("Foreign material history")
            if digest(m["genesis"]) != m["genesis_digest"]:
                raise Conflict("Altered material genesis")
            if m["parent"] is None and m["genesis_digest"] != FIXTURE_HASH:
                raise Conflict("Silent change to the canonical material fixture")
            state = copy.deepcopy(m["genesis"])
            validate(state)
            home = meta(db, "domestic_meta")
            body = meta(db, "embodied_meta")
            rhythm = meta(db, "rhythm_meta")
            hstates, rstates = _home_snapshots(db), historic_days(db)
            prev, rev = GENESIS_HASH, 0
            lb, lh, lr = (m["body_at_install"], m["home_at_install"],
                          m["rhythm_at_install"])
            for n, eid, payload, prior, h in db.execute(
                    "SELECT revision,event_id,envelope,prev_hash,event_hash "
                    "FROM botanical_events ORDER BY revision"):
                e = json.loads(payload)
                if (n != rev + 1 or e["revision"] != n
                        or eid != e["event_id"] or prior != prev
                        or e["previous_hash"] != prev or digest(e) != h
                        or (e["lab_id"], e["home_id"], e["world_epoch"]) !=
                        (m["lab_id"], m["home_id"], m["world_epoch"])):
                    raise Conflict("Botanical material receipt tampered with")
                br, hr, rr = (e[k] for k in (
                    "body_revision", "home_revision", "rhythm_revision"))
                if not (lb <= br <= body_proof["revision"]
                        and lh <= hr <= home["revision"]
                        and lr <= rr <= rhythm["revision"]):
                    raise Conflict("Impossible historical physical source revision")
                if (e["body_cursor"] != cursor(db, "embodied_events", br)
                        or e["home_cursor"] != cursor(db, "domestic_events", hr)
                        or e["rhythm_cursor"] != cursor(db, "rhythm_events", rr)):
                    raise Conflict("Material event cites an altered parent ledger")
                station = pose(db, br, body)
                if (station != e["station"]
                        or e["minute"] != rstates[rr]["minute"]
                        or e["before_digest"] != digest(state)):
                    raise Conflict("Material action used a fabricated room or time")
                new, subjective = transition(
                    state, e["op"], e["args"], station,
                    hstates[hr], rstates[rr])
                if digest(new) != e["after_digest"] or subjective != e["subject"]:
                    raise Conflict("Replayed object transformation disagrees")
                state, prev, rev = new, h, n
                lb, lh, lr = br, hr, rr
            if (m["state"], m["head_hash"], m["revision"]) != (state, prev, rev):
                raise Conflict("Material snapshot diverged from historic actions")
            return {"verified": True, "revision": rev, "head_hash": prev,
                    "world_epoch": m["world_epoch"]}

    def audit_state(self):
        self.verify()
        with self.habitat._open() as db:
            return copy.deepcopy(meta(db, "botanical_meta")["state"])

    def act(self, op, *, event_id=None, **args):
        self.verify()
        HomeLife(self.habitat)._catch_up()
        event_id = event_id or uuid.uuid4().hex
        if type(event_id) is not str or not 1 <= len(event_id) <= 90:
            raise LabError("Invalid material event ID")
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            m = meta(db, "botanical_meta")
            prior = db.execute(
                "SELECT envelope FROM botanical_events WHERE event_id=?",
                (event_id,)).fetchone()
            if prior:
                record = json.loads(prior[0])
                if record["op"] != op or record["args"] != args:
                    raise Conflict("Event ID cannot rewrite an earlier material activity")
                return copy.deepcopy(record["subject"])
            home = meta(db, "domestic_meta")
            rhythm = meta(db, "rhythm_meta")
            body = meta(db, "embodied_meta")
            new, subjective = transition(
                m["state"], op, args, body["station"], home["state"], rhythm["state"])
            e = {
                "event_id": event_id, "revision": m["revision"]+1,
                "op": op, "args": args, "station": body["station"],
                "minute": rhythm["state"]["minute"],
                "lab_id": m["lab_id"], "home_id": m["home_id"],
                "world_epoch": m["world_epoch"],
                "body_revision": body["revision"], "body_cursor": body["head_hash"],
                "home_revision": home["revision"], "home_cursor": home["head_hash"],
                "rhythm_revision": rhythm["revision"],
                "rhythm_cursor": rhythm["head_hash"],
                "before_digest": digest(m["state"]), "after_digest": digest(new),
                "subject": subjective, "previous_hash": m["head_hash"], "utc": _utc(),
            }
            h = digest(e)
            db.execute("INSERT INTO botanical_events VALUES (?,?,?,?,?)",
                       (e["revision"], event_id, canonical(e), m["head_hash"], h))
            write(db, "state", new)
            write(db, "revision", e["revision"])
            write(db, "head_hash", h)
            return copy.deepcopy(subjective)

    def observe(self):
        """Only actually visible specimens/materials appear in first person."""
        self.verify()
        with self.habitat._open() as db:
            m = meta(db, "botanical_meta")
            home = meta(db, "domestic_meta")["state"]
            rhythm = meta(db, "rhythm_meta")["state"]
            station = meta(db, "embodied_meta")["station"]
            visible = []
            if _can_see(rhythm, STATIONS[station][0]):
                for oid, item in sorted(m["state"]["objects"].items()):
                    # A clamped wooden press is opaque. Neither an enclosed
                    # fresh flower nor its dried successor is automatically
                    # visible until it is physically retrieved or mounted.
                    if (item["parent"] == "tool:flower-press"
                            and item["kind"] in ("flower", "specimen")):
                        continue
                    if item["stage"] != "transformed" and accessible(
                            m["state"], oid, home, station):
                        description = item["name"]
                        if item["stage"] == "pressing":
                            description += ", drying under the press"
                        if item["label"] is not None:
                            description += ", labeled " + item["label"]
                        visible.append(description)
            return {"inner": (
                "I can see " + ", ".join(visible) + "." if visible else
                "I see no botanical materials within reach."),
                "spoken_aloud": None}

    def available(self):
        """No ranking: legal action/argument pairs currently possible."""
        self.verify()
        with self.habitat._open() as db:
            m = meta(db, "botanical_meta")
            home = meta(db, "domestic_meta")["state"]
            rhythm = meta(db, "rhythm_meta")["state"]
            station = meta(db, "embodied_meta")["station"]
            requests = []
            for oid, item in sorted(m["state"]["objects"].items()):
                if item["kind"] in ("flower", "mount"):
                    requests.append(("take", {"object": oid}))
                    if item["parent"] == ACTOR:
                        for cid in sorted(home["containers"]):
                            requests.append(("put", {"object": oid, "container": cid}))
                if item["kind"] == "specimen":
                    requests.extend((("mount", {"specimen": oid}),
                                     ("label", {"specimen": oid, "text": "sample"})))
            requests.extend((
                ("start_press", {"flower": "plant:rose-001"}),
                ("finish_press", {"flower": "plant:rose-001"})))
            offers = []
            for op, args in requests:
                try:
                    transition(m["state"], op, args, station, home, rhythm)
                except (Conflict, LabError):
                    continue
                actual_args = {k:v for k,v in args.items() if k != "text"}
                offers.append({
                    "op": op, "args": actual_args, "free_text": op == "label",
                    "description": {
                        "take": "pick up this physical object",
                        "put": "place the carried object in accessible furniture",
                        "start_press": "press the fresh rose between blotters",
                        "finish_press": "take the dried rose out of the press",
                        "mount": "mount the dried rose on a herbarium sheet",
                        "label": "write a label of my own choosing beside the rose",
                    }[op]})
            return offers

    def _fork_into(self, clone):
        proof = self.verify()
        with self.habitat._open() as db:
            m = meta(db, "botanical_meta")
            seed = copy.deepcopy(m["state"])
        return MaterialObjects(clone).initialize(
            initial_state=seed, parent={
                "world_epoch": m["world_epoch"],
                "revision": m["revision"], "head_hash": proof["head_hash"],
                "provenance": "physical_conditions_not_parent_lived_events"})
