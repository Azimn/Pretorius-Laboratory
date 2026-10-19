"""Persistent prospective projects, distinct from physical objects and memories.

A project is a *subject-declared intention*, never proof an experiment succeeded.
Verified physical receipts may be associated with it, but no host can turn
project prose into physical results. No agenda, recurring task, expiry, quota,
auto-completion, or inferred preferences. Opt-in additive SQLite world ledger.
"""
from __future__ import annotations

import copy
import json
import re
import uuid

from .daily_rhythm import DailyRhythm
from .embodied_access import EmbodiedAccess
from .habitat_v2 import SpatialHabitat
from .home_life import HomeLife
from .material_objects import cursor, historic_days, meta, pose
from .physics import Conflict, LabError, canonical, digest
from .store import GENESIS_HASH, _utc

RULES = "pretorius-prospective-projects/1"
SOURCES = {
    "domestic_events": "envelope",
    "rhythm_events": "envelope",
    "botanical_events": "envelope",
    "arrangement_events": "envelope",
    "books_events": "payload",
    "custody_events": "envelope",
    "embodied_events": "envelope",
}
STATUS = {"active", "paused", "abandoned", "declared_finished"}
_ID = re.compile(r"project:[0-9]{4}\Z")


def exists(db):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='project_meta'"
    ).fetchone() is not None


def _meta(db):
    return {k: json.loads(v) for k, v in db.execute(
        "SELECT key,value FROM project_meta")}


def _write(db, key, value):
    db.execute("INSERT OR REPLACE INTO project_meta VALUES (?,?)",
               (key, canonical(value)))


def _text(value):
    if (type(value) is not str or not 3 <= len(value) <= 500 or
            not value.strip() or any(
                ord(ch) < 32 and ch != "\n" for ch in value)):
        raise LabError("A bounded, authored project intention is required")
    return value


def _source(db, table, event_id, event_hash):
    if (type(table) is not str or table not in SOURCES or
            type(event_id) is not str or not 1 <= len(event_id) <= 128 or
            type(event_hash) is not str or not re.fullmatch(r"[0-9a-f]{64}", event_hash)):
        raise LabError("Only identified, supported physical receipts may be linked")
    if not db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,)).fetchone():
        raise Conflict("The referenced physical domain is not installed")
    row = db.execute(
        "SELECT " + SOURCES[table] + ",event_hash FROM " + table +
        " WHERE event_id=?", (event_id,),
    ).fetchone()
    if not row or row[1] != event_hash:
        raise Conflict("The associated physical event does not exist as recorded")
    envelope = json.loads(row[0])
    if digest(envelope) != event_hash:
        raise Conflict("The associated physical receipt is altered")
    return {"source_table": table, "source_event_id": event_id,
            "source_event_hash": event_hash}


def _validate(state):
    if (type(state) is not dict or set(state) != {"projects", "next_id"}
            or type(state["projects"]) is not dict or
            type(state["next_id"]) is not int or
            not 1 <= state["next_id"] <= 1001 or
            len(state["projects"]) != state["next_id"] - 1):
        raise Conflict("Invalid project ledger state")
    for n in range(1, state["next_id"]):
        key = f"project:{n:04d}"
        if key not in state["projects"]:
            raise Conflict("A declared project vanished from its record")
        p = state["projects"][key]
        if (type(p) is not dict or set(p) != {
                "intention", "status", "reflections", "receipts"} or
                type(p["intention"]) is not str or
                p["status"] not in STATUS or
                type(p["reflections"]) is not list or
                type(p["receipts"]) is not list):
            raise Conflict("Invalid authored project")
        _text(p["intention"])
        if len(p["reflections"]) > 200 or len(p["receipts"]) > 500:
            raise Conflict("Unbounded personal project log")
        for thought in p["reflections"]:
            _text(thought)
        for link in p["receipts"]:
            if (type(link) is not dict or set(link) != {
                    "source_table", "source_event_id", "source_event_hash"}):
                raise Conflict("Project cites an invalid physical receipt")


def _step(state, op, args, db):
    """Deterministic project choice reducer. Never executes a material action."""
    if type(args) is not dict:
        raise LabError("Malformed project intent")
    s = copy.deepcopy(state)
    projects = s["projects"]
    key = args.get("project_id")
    if op == "start":
        if set(args) != {"project_id", "text"} or key != f"project:{s['next_id']:04d}":
            raise Conflict("A new project needs the next unique identity")
        intention = _text(args["text"])
        projects[key] = {"intention": intention, "status": "active",
                         "reflections": [], "receipts": []}
        s["next_id"] += 1
        inner = "I decide to pursue a project: " + intention
    else:
        if type(key) is not str or key not in projects:
            raise Conflict("No such personally recorded project")
        p = projects[key]
        if op == "review":
            if set(args) != {"project_id"}:
                raise LabError("Review requires only its existing project identity")
            inner = ("I revisit my recorded intention: " + p["intention"] +
                     ". My last chosen status was " + p["status"].replace("_", " ") + ".")
            if p["reflections"]:
                inner += " My latest written reflection was: " + p["reflections"][-1]
            inner += (" I have associated " + str(len(p["receipts"])) +
                      " verified physical events with this project.")
        elif op == "reflect":
            if set(args) != {"project_id", "text"} or p["status"] != "active":
                raise Conflict("Only a voluntarily active project accepts reflection")
            reflection = _text(args["text"])
            if len(p["reflections"]) >= 200:
                raise Conflict("Project reflection limit reached")
            p["reflections"].append(reflection)
            inner = "I add a reflection to my project: " + reflection
        elif op == "associate":
            if set(args) != {"project_id", "source_table", "source_event_id", "source_event_hash"}:
                raise LabError("Attach the exact existing physical event reference")
            if p["status"] != "active" or len(p["receipts"]) >= 500:
                raise Conflict("This project is not accepting new associated work")
            receipt = _source(
                db, args["source_table"], args["source_event_id"],
                args["source_event_hash"])
            if receipt in p["receipts"]:
                raise Conflict("This physical receipt is already associated")
            p["receipts"].append(receipt)
            inner = ("I associate something I actually did with this project. "
                     "That does not, by itself, complete my intention.")
        else:
            new_status = {"pause": "paused", "resume": "active",
                          "abandon": "abandoned", "finish": "declared_finished"}.get(op)
            if new_status is None or set(args) != {"project_id"}:
                raise LabError("Unsupported project decision")
            allowed = {
                "pause": {"active"}, "resume": {"paused"},
                "abandon": {"active", "paused"},
                "finish": {"active"},
            }
            if p["status"] not in allowed[op]:
                raise Conflict("The project is not in a state allowing that choice")
            p["status"] = new_status
            inner = {
                "pause": "I set aside my project without losing the work.",
                "resume": "I decide to return to my unfinished project.",
                "abandon": "I decide not to pursue this project further.",
                "finish": ("I consider this project finished for now. "
                           "That is my decision, not proof of a physical result."),
            }[op]
    _validate(s)
    return s, {"inner": inner, "spoken_aloud": None}


class PersonalProjects:
    """Subject-owned prospective commitments bound to one laboratory epoch."""

    def __init__(self, habitat):
        self.habitat = habitat

    def initialize(self, *, initial_state=None, parent=None):
        HomeLife(self.habitat).verify()
        DailyRhythm(self.habitat).verify()
        EmbodiedAccess(self.habitat).verify()
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            if exists(db):
                raise Conflict("Projects already initialized here")
            world = SpatialHabitat._metadata(db)
            clock, home, body = (
                meta(db, "rhythm_meta"), meta(db, "domestic_meta"),
                meta(db, "embodied_meta"))
            seed = copy.deepcopy(initial_state if initial_state is not None else {
                "projects": {}, "next_id": 1})
            _validate(seed)
            if initial_state is not None and type(parent) is not dict:
                raise Conflict("Copied project obligations require provenance")
            db.execute("CREATE TABLE project_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("""CREATE TABLE project_events(
                revision INTEGER PRIMARY KEY,event_id TEXT NOT NULL UNIQUE,
                envelope TEXT NOT NULL,prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE)""")
            values = {
                "rules": RULES, "world_epoch": world["world_epoch"],
                "lab_id": world["lab_id"], "home_id": world["home_id"],
                "genesis": seed, "genesis_hash": digest(seed),
                "parent": parent, "state": seed,
                "revision": 0, "head_hash": GENESIS_HASH,
                "body_at_install": body["revision"],
                "home_at_install": home["revision"],
                "rhythm_at_install": clock["revision"],
            }
            for key, value in values.items():
                _write(db, key, value)
        return self.verify()

    def verify(self):
        # Project associations cannot outrank physical-world authority. An
        # internally consistent counterfeit receipt in another domain must
        # fail that domain's full event replay, not just its local JSON hash.
        with self.habitat._open() as db:
            if not exists(db):
                raise LabError("Personal projects not initialized")
            snapshot = _meta(db)["state"]
        _validate(snapshot)
        source_domains = {
            item["source_table"]
            for project in snapshot["projects"].values()
            for item in project["receipts"]
        }
        from .material_objects import MaterialObjects
        from .home_arrangement import HomeArrangements
        from .book_library import BookLibrary
        from .book_custody import BookCustody
        for domain in sorted(source_domains):
            if domain == "botanical_events":
                MaterialObjects(self.habitat).verify()
            elif domain == "arrangement_events":
                HomeArrangements(self.habitat).verify()
            elif domain == "books_events":
                BookLibrary(self.habitat).verify()
            elif domain == "custody_events":
                BookCustody(self.habitat).verify()
            elif domain not in SOURCES:
                raise Conflict("Unsupported project evidence authority")
        world = self.habitat.verify()
        HomeLife(self.habitat).verify()
        DailyRhythm(self.habitat).verify()
        body_proof = EmbodiedAccess(self.habitat).verify()
        with self.habitat._open() as db:
            if not exists(db):
                raise LabError("Personal projects not initialized")
            m = _meta(db)
            if (m["rules"] != RULES or
                    (m["lab_id"], m["home_id"], m["world_epoch"]) !=
                    (world["lab_id"], world["home_id"], world["world_epoch"])):
                raise Conflict("Personal projects belong to another world")
            if digest(m["genesis"]) != m["genesis_hash"]:
                raise Conflict("Project genesis has changed")
            if m["parent"] is None and m["genesis"] != {"projects": {}, "next_id": 1}:
                raise Conflict("Original blank prospective ledger was replaced")
            state = copy.deepcopy(m["genesis"])
            _validate(state)
            home = meta(db, "domestic_meta")
            clock = meta(db, "rhythm_meta")
            body = meta(db, "embodied_meta")
            times = historic_days(db)
            br0, hr0, rr0 = (m["body_at_install"],
                             m["home_at_install"], m["rhythm_at_install"])
            prev, rev = GENESIS_HASH, 0
            for n, event_id, payload, prior, h in db.execute(
                    "SELECT revision,event_id,envelope,prev_hash,event_hash "
                    "FROM project_events ORDER BY revision"):
                e = json.loads(payload)
                if (n != rev + 1 or e["revision"] != n or event_id != e["event_id"]
                        or prior != prev or e["previous_hash"] != prev
                        or digest(e) != h or
                        (e["lab_id"], e["home_id"], e["world_epoch"]) !=
                        (m["lab_id"], m["home_id"], m["world_epoch"])):
                    raise Conflict("Project decision history was altered")
                br, hr, rr = (
                    e["body_revision"], e["home_revision"], e["rhythm_revision"])
                if not (br0 <= br <= body_proof["revision"] and
                        hr0 <= hr <= home["revision"] and
                        rr0 <= rr <= clock["revision"]):
                    raise Conflict("Project decision cites impossible material source")
                if (e["body_cursor"] != cursor(db, "embodied_events", br)
                        or e["home_cursor"] != cursor(db, "domestic_events", hr)
                        or e["rhythm_cursor"] != cursor(db, "rhythm_events", rr)
                        or e["station"] != pose(db, br, body)
                        or e["minute"] != times[rr]["minute"]
                        or e["before_digest"] != digest(state)):
                    raise Conflict("Project does not replay at the original world place/time")
                result, subjective = _step(state, e["op"], e["args"], db)
                if (digest(result) != e["after_digest"] or
                        e["subject"] != subjective):
                    raise Conflict("Project decision no longer replays")
                state, prev, rev = result, h, n
                br0, hr0, rr0 = br, hr, rr
            if (m["state"], m["head_hash"], m["revision"]) != (state, prev, rev):
                raise Conflict("Project materialized snapshot differs from history")
            return {"verified": True, "revision": rev, "head_hash": prev,
                    "world_epoch": m["world_epoch"]}

    def audit_state(self):
        self.verify()
        with self.habitat._open() as db:
            return copy.deepcopy(_meta(db)["state"])

    def act(self, op, *, event_id=None, **args):
        self.verify()
        HomeLife(self.habitat)._catch_up()
        eid = event_id if event_id is not None else uuid.uuid4().hex
        if type(eid) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", eid):
            raise LabError("Stable bounded project event ID required")
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            m = _meta(db)
            prior = db.execute(
                "SELECT envelope FROM project_events WHERE event_id=?",
                (eid,)).fetchone()
            if prior:
                e = json.loads(prior[0])
                if e["op"] != op or e["args"] != args:
                    raise Conflict("A project event ID cannot represent a new choice")
                return copy.deepcopy(e["subject"])
            home, body, clock = (
                meta(db, "domestic_meta"), meta(db, "embodied_meta"),
                meta(db, "rhythm_meta"))
            changed, subjective = _step(m["state"], op, args, db)
            event = {
                "event_id": eid, "revision": m["revision"] + 1,
                "op": op, "args": args,
                "world_epoch": m["world_epoch"], "lab_id": m["lab_id"],
                "home_id": m["home_id"], "station": body["station"],
                "minute": clock["state"]["minute"],
                "body_revision": body["revision"], "body_cursor": body["head_hash"],
                "home_revision": home["revision"], "home_cursor": home["head_hash"],
                "rhythm_revision": clock["revision"],
                "rhythm_cursor": clock["head_hash"],
                "before_digest": digest(m["state"]),
                "after_digest": digest(changed),
                "subject": subjective, "previous_hash": m["head_hash"],
                "utc": _utc(),
            }
            event_hash = digest(event)
            db.execute("INSERT INTO project_events VALUES(?,?,?,?,?)",
                       (event["revision"], eid, canonical(event),
                        m["head_hash"], event_hash))
            _write(db, "state", changed)
            _write(db, "revision", event["revision"])
            _write(db, "head_hash", event_hash)
            return copy.deepcopy(subjective)

    def current_offers(self):
        """Trusted project decision catalog; no implied obligation to choose."""
        state = self.audit_state()
        result = []
        next_id = f"project:{state['next_id']:04d}"
        result.append({"op": "start", "args": {"project_id": next_id},
                       "free_text": True,
                       "description": "start a project of my own choosing"})
        for project_id, p in sorted(state["projects"].items()):
            result.append({"op": "review", "args": {"project_id": project_id},
                           "free_text": False, "description":
                           "review a project I previously chose"})
            possible = {
                "active": ["reflect", "pause", "abandon", "finish"],
                "paused": ["resume", "abandon"],
                "abandoned": [],
                "declared_finished": [],
            }[p["status"]]
            for op in possible:
                result.append({"op": op, "args": {"project_id": project_id},
                               "free_text": op == "reflect",
                               "description": {
                                   "reflect": "add my own project reflection",
                                   "pause": "leave my unfinished work alone",
                                   "resume": "return to the project I left unfinished",
                                   "abandon": "abandon my project",
                                   "finish": "declare the project finished",
                               }[op]})
        return result

    def _fork_into(self, clone):
        proof = self.verify()
        with self.habitat._open() as db:
            m = _meta(db)
            # Physical projects may be copied as notes of intent, but any
            # evidence receipt from the parent epoch MUST NOT be passed off
            # as an action experienced by the new branch.
            state = copy.deepcopy(m["state"])
            for p in state["projects"].values():
                p["receipts"] = []
            parent = {"world_epoch": m["world_epoch"], "revision": m["revision"],
                      "head_hash": proof["head_hash"],
                      "interpretation": "inherited_intentions_not_inherited_experiences"}
        return PersonalProjects(clone).initialize(initial_state=state, parent=parent)
