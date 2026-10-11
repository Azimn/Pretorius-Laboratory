"""Opt-in spatial habitat v2.

Persistent, host-authoritative discrete spatial simulation for continuity experiments.
It does not modify or silently migrate the v0.1 Laboratory database.
Physical objects use immutable semantic IDs and explicit, metrically located anchors.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sqlite3
import uuid

from .physics import Conflict, LabError, canonical, digest
from .store import GENESIS_HASH, _utc

SPATIAL_SCHEMA = "spatial-habitat/2.0.0"
SPATIAL_RULES = "anchor-physics/1"
TRUSTED_ACTORS = frozenset({"local_operator", "pretorius_research"})
ROOMS = {
    "room:sanctum": {"label": "Pretorius's Sanctum", "durability": "permanent"},
    "room:experiment": {"label": "Experimental Chamber", "durability": "experimental"},
}


def _fixture() -> dict:
    """A small *synthetic* fixed floor plan. Units are millimetres."""
    anchors = {}
    for shelf_number in (1, 2, 3):
        for slot in range(1, 11):
            key = f"shelf:{shelf_number}/slot:{slot}"
            anchors[key] = {
                "room": "room:sanctum", "kind": "shelf_slot",
                "parent": f"shelf:{shelf_number}", "ordinal": slot,
                "xyz_mm": [700 + (slot - 1) * 65, 300, 700 + shelf_number * 400],
                "capacity": 1,
            }
    anchors.update({
        "bench:main/position:left": {
            "room": "room:sanctum", "kind": "bench_spot",
            "parent": "bench:main", "ordinal": 1,
            "xyz_mm": [1600, 1200, 900], "capacity": 1,
        },
        "floor:corner:nw": {
            "room": "room:sanctum", "kind": "floor_spot",
            "parent": "floor:sanctum", "ordinal": 1,
            "xyz_mm": [100, 100, 0], "capacity": 1,
        },
        "floor:corner:se": {
            "room": "room:sanctum", "kind": "floor_spot",
            "parent": "floor:sanctum", "ordinal": 2,
            "xyz_mm": [2800, 2800, 0], "capacity": 1,
        },
        "chamber:table/position:1": {
            "room": "room:experiment", "kind": "bench_spot",
            "parent": "chamber:table", "ordinal": 1,
            "xyz_mm": [900, 900, 900], "capacity": 1,
        },
    })
    objects = {}
    for n in range(1, 8):
        oid = f"book:{n:03d}"
        objects[oid] = {
            "kind": "book", "name": f"Research volume {n}",
            "anchor_id": f"shelf:3/slot:{n}",
            "condition": "intact", "collected": True, "revision": 0,
            "source": "synthetic_initial_fixture",
        }
    objects["beaker:001"] = {
        "kind": "glass_beaker", "name": "Laboratory beaker",
        "anchor_id": "bench:main/position:left",
        "condition": "intact", "collected": True, "revision": 0,
        "source": "synthetic_initial_fixture",
    }
    return {"rooms": copy.deepcopy(ROOMS), "anchors": anchors, "objects": objects, "ticks": 0}


FIXTURE = _fixture()
FIXTURE_DIGEST = digest(FIXTURE)
ALLOWED_ACTION_FIELDS = {
    "place": {"op", "object_id", "anchor_id"},
    "break": {"op", "object_id"},
    "collect": {"op", "object_id"},
    "advance_ticks": {"op", "ticks"},
}


def _valid_state(state: dict) -> None:
    """Validate spatial invariants after every action and on archived genesis."""
    if state["anchors"] != FIXTURE["anchors"] or state["rooms"] != FIXTURE["rooms"]:
        raise Conflict("Unsupported or mutated spatial definitions")
    if type(state["ticks"]) is not int or state["ticks"] < 0:
        raise Conflict("Invalid experiment tick")
    occupied = set()
    for oid, obj in state["objects"].items():
        if oid not in FIXTURE["objects"] or obj["kind"] != FIXTURE["objects"][oid]["kind"]:
            raise Conflict("Object identity/type mismatch")
        aid = obj["anchor_id"]
        if not isinstance(aid, str) or aid not in state["anchors"] or aid in occupied:
            raise Conflict("Missing anchor or double-occupied location")
        occupied.add(aid)
        if obj["condition"] not in {"intact", "broken"}:
            raise Conflict("Unknown physical condition")
        if obj["kind"] != "glass_beaker" and obj["condition"] != "intact":
            raise Conflict("Unsupported broken object")
        if type(obj["revision"]) is not int or obj["revision"] < 0:
            raise Conflict("Invalid object version")
        if type(obj["collected"]) is not bool or (obj["condition"] == "intact" and not obj["collected"]):
            raise Conflict("Invalid fragment state")
    if set(state["objects"]) != set(FIXTURE["objects"]):
        raise Conflict("Object identity registry was changed outside a typed action")


def apply_spatial(state: dict, action: dict, next_revision: int) -> dict:
    if not isinstance(action, dict) or type(next_revision) is not int or next_revision < 1:
        raise LabError("Invalid action")
    op = action.get("op")
    if op not in ALLOWED_ACTION_FIELDS or set(action) != ALLOWED_ACTION_FIELDS[op]:
        raise LabError("Unknown command or unexpected fields")
    result = copy.deepcopy(state)
    if op == "advance_ticks":
        ticks = action["ticks"]
        if type(ticks) is not int or not 1 <= ticks <= 10000:
            raise LabError("Ticks must be 1..10000")
        result["ticks"] += ticks
    else:
        oid = action["object_id"]
        if not isinstance(oid, str) or oid not in result["objects"]:
            raise LabError("Unknown object")
        obj = result["objects"][oid]
        if op == "break":
            if obj["kind"] != "glass_beaker" or obj["condition"] != "intact":
                raise LabError("Only an intact beaker can be broken in this ruleset")
            obj["condition"] = "broken"
            # v2 aggregate approximation: all fragments remain at the break anchor.
            obj["collected"] = False
        elif op == "collect":
            if obj["kind"] != "glass_beaker" or obj["condition"] != "broken" or obj["collected"]:
                raise LabError("Only scattered beaker remains can be collected")
            obj["collected"] = True
        else:
            aid = action["anchor_id"]
            if not isinstance(aid, str) or aid not in result["anchors"]:
                raise LabError("Unknown precise anchor")
            if obj["anchor_id"] == aid:
                raise LabError("Object already occupies that anchor")
            if obj["condition"] == "broken" and not obj["collected"]:
                raise LabError("Scattered fragments must be collected before moving")
            if any(other["anchor_id"] == aid for other in result["objects"].values()):
                raise Conflict("Anchor occupied; objects cannot overlap")
            obj["anchor_id"] = aid
        obj["revision"] = next_revision
    _valid_state(result)
    return result


class SpatialHabitat:
    """Version-isolated v2 authority with a single event/state transaction."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _open(self) -> sqlite3.Connection:
        if not self.path.is_file():
            raise FileNotFoundError(str(self.path))
        db = sqlite3.connect(self.path, isolation_level=None, timeout=10)
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def _metadata(db) -> dict:
        return {k: json.loads(v) for k, v in db.execute("SELECT key,value FROM meta")}

    @staticmethod
    def _set(db, key: str, value) -> None:
        db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (key, canonical(value)))

    @classmethod
    def create(cls, path: str | Path, *, initial_state: dict | None = None,
               parent: dict | None = None, home_id: str | None = None) -> "SpatialHabitat":
        habitat = cls(path)
        habitat.path.parent.mkdir(parents=True, exist_ok=True)
        if habitat.path.exists():
            raise FileExistsError(str(habitat.path))
        seed = copy.deepcopy(initial_state if initial_state is not None else FIXTURE)
        _valid_state(seed)
        db = sqlite3.connect(habitat.path, isolation_level=None)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("""CREATE TABLE events (
                revision INTEGER PRIMARY KEY,
                event_id TEXT NOT NULL UNIQUE,
                envelope TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE
            )""")
            db.execute("""CREATE TABLE snapshots (
                revision INTEGER PRIMARY KEY,
                state_json TEXT NOT NULL,
                state_digest TEXT NOT NULL,
                event_hash TEXT NOT NULL
            )""")
            meta = {
                "lab_id": str(uuid.uuid4()),
                "home_id": home_id or str(uuid.uuid4()),
                "world_epoch": str(uuid.uuid4()),
                "schema_version": SPATIAL_SCHEMA,
                "ruleset_version": SPATIAL_RULES,
                "manifest_digest": FIXTURE_DIGEST,
                "mode": "sandbox" if parent else "canonical",
                "parent": parent,
                "revision": 0,
                "head_hash": GENESIS_HASH,
                "genesis_state": seed,
                "state": seed,
            }
            for k, v in meta.items():
                cls._set(db, k, v)
            db.execute("INSERT INTO snapshots VALUES (?,?,?,?)",
                       (0, canonical(seed), digest(seed), GENESIS_HASH))
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            db.close()
            habitat.path.unlink(missing_ok=True)
            raise
        db.close()
        return habitat

    def status(self) -> dict:
        with self._open() as db:
            m = self._metadata(db)
        return {k: copy.deepcopy(v) for k, v in m.items() if k != "genesis_state"}

    def commit(self, action: dict, *, actor: str = "local_operator",
               event_id: str | None = None, expected_revision: int | None = None,
               expected_placement_revision: int | None = None) -> dict:
        if actor not in TRUSTED_ACTORS:
            raise LabError("Untrusted local actor label")
        event_id = event_id or str(uuid.uuid4())
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
            raise LabError("Invalid event id")
        # Once custody is opted into this world, new trusted physical placements
        # use effective occupancy, not stale reservations of raw v2 genesis.
        # Historical v2 events are NEVER rewritten or replayed differently.
        from .book_custody import BookCustody, exists as custody_exists
        with self._open() as check:
            unified = custody_exists(check)
        if unified and isinstance(action, dict) and action.get("op") == "place":
            if actor != "local_operator":
                raise LabError("Subject movement must use the embodied access port")
            if set(action) != {"op", "object_id", "anchor_id"}:
                raise LabError("Malformed unified placement command")
            if expected_revision is not None:
                revision = self.verify()["revision"]
                if type(expected_revision) is not int or expected_revision != revision:
                    raise Conflict("Stale original-world revision")
            receipt = BookCustody(self).act(
                "operator_place", action["object_id"],
                destination=action["anchor_id"], event_id=event_id,
                expected_placement_revision=expected_placement_revision)
            return {**receipt, "domain": "effective_physical_placement",
                    "legacy_world_revision_unchanged": True}
        if expected_placement_revision is not None:
            raise LabError("Placement revision guard requires an active custody placement")
        # Validate optional physical annex before mutating the primary host.
        from .shelf_annex import ShelfAnnex
        with self._open() as check:
            has_annex = ShelfAnnex.exists(check)
        if has_annex:
            ShelfAnnex(self).verify()
        db = self._open()
        try:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT envelope,event_hash FROM events WHERE event_id=?",
                                  (event_id,)).fetchone()
            if existing:
                previous = json.loads(existing[0])
                if previous["action"] != action or previous["actor"] != actor:
                    raise Conflict("Event ID reused with different payload")
                db.execute("COMMIT")
                return {**previous, "event_hash": existing[1]}
            m = self._metadata(db)
            if (m["schema_version"], m["ruleset_version"], m["manifest_digest"]) != (
                    SPATIAL_SCHEMA, SPATIAL_RULES, FIXTURE_DIGEST):
                raise Conflict("Wrong schema/rules/manifest")
            if expected_revision is not None and (
                    type(expected_revision) is not int or expected_revision != m["revision"]):
                raise Conflict("Stale world revision")
            from .book_custody import exists as custody_exists, effective_objects
            if custody_exists(db):
                custody = {k: json.loads(val) for k, val in db.execute(
                    "SELECT key,value FROM custody_meta")}
                if action.get("object_id") in custody["items"]:
                    raise Conflict("Object location is now governed by physical custody")
                if action["op"] == "place":
                    live = effective_objects(db)
                    if any(obj["anchor_id"] == action["anchor_id"]
                           for obj in live.values()):
                        raise Conflict("Destination physically occupied")
            before = m["state"]
            after = apply_spatial(before, action, m["revision"] + 1)
            if has_annex:
                annex_row = db.execute(
                    "SELECT value FROM annex_meta WHERE key='items'").fetchone()
                annex_items = json.loads(annex_row[0]) if annex_row else {}
                if any(x["anchor_id"] in {v["anchor_id"] for v in after["objects"].values()}
                       for x in annex_items.values()):
                    raise Conflict("Core move would overlap an annex physical book")
            row = {
                "event_id": event_id, "lab_id": m["lab_id"],
                "home_id": m["home_id"], "world_epoch": m["world_epoch"],
                "schema_version": SPATIAL_SCHEMA, "ruleset_version": SPATIAL_RULES,
                "manifest_digest": FIXTURE_DIGEST, "actor": actor,
                "authority": "trusted_local_only", "mode": m["mode"],
                "visibility": "research_private", "action": action,
                "base_revision": m["revision"], "committed_revision": m["revision"] + 1,
                "before_digest": digest(before), "after_digest": digest(after),
                "previous_event_hash": m["head_hash"], "committed_at_utc": _utc(),
            }
            event_hash = digest(row)
            db.execute("INSERT INTO events VALUES (?,?,?,?,?)",
                       (m["revision"] + 1, event_id, canonical(row), m["head_hash"], event_hash))
            self._set(db, "revision", m["revision"] + 1)
            self._set(db, "head_hash", event_hash)
            self._set(db, "state", after)
            db.execute("COMMIT")
            return {**row, "event_hash": event_hash}
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def verify(self) -> dict:
        with self._open() as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise Conflict("SQLite corruption")
            m = self._metadata(db)
            if (m["schema_version"], m["ruleset_version"], m["manifest_digest"]) != (
                    SPATIAL_SCHEMA, SPATIAL_RULES, FIXTURE_DIGEST):
                raise Conflict("Versioned ruleset mismatch")
            state = m["genesis_state"]
            _valid_state(state)
            snaps = {r: (json.loads(s), h, cursor) for r, s, h, cursor in db.execute(
                "SELECT revision,state_json,state_digest,event_hash FROM snapshots")}
            if snaps.get(0) != (state, digest(state), GENESIS_HASH):
                raise Conflict("Genesis snapshot mismatch")
            cursor, rev = GENESIS_HASH, 0
            for n, eid, encoded, prev, h in db.execute(
                    "SELECT revision,event_id,envelope,prev_hash,event_hash FROM events ORDER BY revision"):
                e = json.loads(encoded)
                if n != rev + 1 or n != e["committed_revision"] or e["base_revision"] != rev:
                    raise Conflict("Event sequence gap")
                if prev != cursor or e["previous_event_hash"] != cursor or h != digest(e):
                    raise Conflict("Broken event hash chain")
                if (eid, e["lab_id"], e["world_epoch"], e["home_id"], e["mode"]) != (
                        e["event_id"], m["lab_id"], m["world_epoch"], m["home_id"], m["mode"]):
                    raise Conflict("Source identity mismatch")
                if (e["schema_version"], e["ruleset_version"], e["manifest_digest"]) != (
                        SPATIAL_SCHEMA, SPATIAL_RULES, FIXTURE_DIGEST):
                    raise Conflict("Event contract mismatch")
                if e["before_digest"] != digest(state):
                    raise Conflict("Event does not descend from verified world")
                state = apply_spatial(state, e["action"], n)
                if e["after_digest"] != digest(state):
                    raise Conflict("State transition digest mismatch")
                cursor, rev = h, n
                if rev in snaps and snaps[rev] != (state, digest(state), cursor):
                    raise Conflict("Invalid historical snapshot")
            if (rev, cursor, state) != (m["revision"], m["head_hash"], m["state"]):
                raise Conflict("Materialized state differs from replay")
            if any(i > rev or i < 0 for i in snaps):
                raise Conflict("Unknown snapshot revision")
            return {"verified": True, "lab_id": m["lab_id"],
                    "home_id": m["home_id"], "world_epoch": m["world_epoch"],
                    "mode": m["mode"], "revision": rev, "head_hash": cursor,
                    "state_digest": digest(state), "snapshots": len(snaps)}

    def checkpoint(self) -> dict:
        self.verify()
        db = self._open()
        try:
            db.execute("BEGIN IMMEDIATE")
            m = self._metadata(db)
            db.execute("INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?)",
                       (m["revision"], canonical(m["state"]), digest(m["state"]), m["head_hash"]))
            db.execute("COMMIT")
            return {"revision": m["revision"], "state_digest": digest(m["state"])}
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def backup_to(self, destination: str | Path) -> dict:
        self.verify()
        from .physical_affordances import PhysicalAffordances, exists as affordances_exist
        with self._open() as db:
            has_affordances = affordances_exist(db)
        if has_affordances:
            PhysicalAffordances(self).verify()
        from .book_custody import BookCustody, exists as custody_exists
        with self._open() as db:
            has_custody = custody_exists(db)
        if has_custody:
            BookCustody(self).verify()
        from .embodied_access import EmbodiedAccess
        with self._open() as db:
            has_body = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='embodied_meta'"
            ).fetchone() is not None
        if has_body:
            EmbodiedAccess(self).verify()
        from .shelf_annex import ShelfAnnex
        with self._open() as db:
            has_annex = ShelfAnnex.exists(db)
        if has_annex:
            ShelfAnnex(self).verify()
        with self._open() as db:
            has_books = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='books_meta'"
            ).fetchone() is not None
        if has_books:
            from .book_library import BookLibrary
            BookLibrary(self).verify()
        with self._open() as db:
            has_observations = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='observation_meta'"
            ).fetchone() is not None
        if has_observations:
            from .observation_receipts import ObservationPort
            ObservationPort(self).verify()
        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            raise FileExistsError(str(dest))
        src = self._open()
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
        except Exception:
            dst.close()
            dest.unlink(missing_ok=True)
            raise
        finally:
            src.close()
            dst.close()
        proof = SpatialHabitat(dest).verify()
        if has_annex:
            ShelfAnnex(SpatialHabitat(dest)).verify()
        if has_books:
            BookLibrary(SpatialHabitat(dest)).verify()
        if has_observations:
            ObservationPort(SpatialHabitat(dest)).verify()
        if has_body:
            EmbodiedAccess(SpatialHabitat(dest)).verify()
        if has_custody:
            BookCustody(SpatialHabitat(dest)).verify()
        if has_affordances:
            PhysicalAffordances(SpatialHabitat(dest)).verify()
        return proof

    def fork_to(self, destination: str | Path) -> dict:
        """Create a new *unpublishable* test world from a verified snapshot."""
        m = self._verified_status()
        from .physical_affordances import PhysicalAffordances, exists as affordances_exist
        with self._open() as db:
            has_affordances = affordances_exist(db)
        if has_affordances:
            PhysicalAffordances(self).verify()
        from .book_custody import BookCustody, exists as custody_exists
        with self._open() as db:
            has_custody = custody_exists(db)
        if has_custody:
            BookCustody(self).verify()
        from .embodied_access import EmbodiedAccess
        with self._open() as db:
            has_body = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='embodied_meta'"
            ).fetchone() is not None
        if has_body:
            EmbodiedAccess(self).verify()
        from .shelf_annex import ShelfAnnex
        with self._open() as source:
            has_annex = ShelfAnnex.exists(source)
        if has_annex:
            ShelfAnnex(self).verify()
        with self._open() as source:
            has_books = source.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='books_meta'"
            ).fetchone() is not None
        if has_books:
            from .book_library import BookLibrary
            BookLibrary(self).verify()
        with self._open() as source:
            has_observations = source.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='observation_meta'"
            ).fetchone() is not None
        if has_observations:
            from .observation_receipts import ObservationPort
            ObservationPort(self).verify()
        parent = {
            "lab_id": m["lab_id"], "world_epoch": m["world_epoch"],
            "revision": m["revision"], "head_hash": m["head_hash"],
            "state_digest": digest(m["state"]),
        }
        cloned_state = copy.deepcopy(m["state"])
        # Object revisions belong to the new branch/epoch, not the parent chain.
        for obj in cloned_state["objects"].values():
            obj["revision"] = 0
        clone = SpatialHabitat.create(destination, initial_state=cloned_state,
                                      parent=parent, home_id=m["home_id"])
        # Restore dependency order: physical annex -> actor pose -> custody
        # -> book source editions -> observation ledger.
        if has_annex:
            ShelfAnnex(self)._fork_into(clone)
        if has_body:
            EmbodiedAccess(self)._fork_into(clone)
        if has_affordances:
            PhysicalAffordances(self)._fork_into(clone)
        if has_custody:
            BookCustody(self)._fork_into(clone)
        if has_books:
            BookLibrary(self)._fork_into(clone)
        if has_observations:
            ObservationPort(clone).initialize()
        return clone.verify()

    def _verified_status(self) -> dict:
        """Do not label a moving scene as verified against a different cursor."""
        m = self.status()
        proof = self.verify()
        if (m["lab_id"], m["world_epoch"], m["revision"],
            m["head_hash"], digest(m["state"])) != (
                proof["lab_id"], proof["world_epoch"], proof["revision"],
                proof["head_hash"], proof["state_digest"]):
            raise Conflict("World changed during verified observation; retry")
        return m

    def inspect_object(self, object_id: str) -> dict:
        """Engineering-only exact geometry and object metadata. Never pass to subject."""
        m = self._verified_status()
        from .shelf_annex import physical_book_objects
        obj = physical_book_objects(self).get(object_id)
        if obj is None:
            raise LabError("Unknown object")
        anchor = m["state"]["anchors"].get(obj["anchor_id"])
        return {"object_id": object_id, "object": obj,
                "anchor_id": obj["anchor_id"], "anchor": anchor,
                "lab_id": m["lab_id"], "world_epoch": m["world_epoch"],
                "revision": m["revision"], "event_cursor": m["head_hash"],
                "observation_class": "engineer_only_not_subject_accessible"}

    def _verified_spine_titles(self) -> dict:
        """Source-backed visible book titles, without page text or engineer geometry."""
        with self._open() as db:
            has_books = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='books_meta'"
            ).fetchone() is not None
        if not has_books:
            return {}
        from .book_library import BookLibrary
        BookLibrary(self).verify()
        with self._open() as db:
            row = db.execute("SELECT value FROM books_meta WHERE key='books'").fetchone()
        return {oid: value["edition"]["title"]
                for oid, value in json.loads(row[0]).items()} if row else {}

    def locate(self, object_id: str) -> dict:
        """Subject-facing qualitative location, never privileged spatial coordinates."""
        m = self._verified_status()
        from .shelf_annex import physical_book_objects
        obj = physical_book_objects(self).get(object_id)
        if obj is None:
            raise LabError("Unknown object")
        anchor = m["state"]["anchors"].get(obj["anchor_id"])
        names = self._verified_spine_titles() if obj["kind"] == "book" else {}
        location = ({"holder": obj["held_by"], "placement": "carried"}
                    if anchor is None else
                    {"room": anchor["room"], "fixture": anchor["parent"],
                     "position": anchor["ordinal"], "anchor_id": obj["anchor_id"]})
        return {"object_id": object_id,
                "name": names.get(object_id, obj["name"]), "condition": obj["condition"],
                "location": location,
                "observation_class": "offered_host_fact_not_proof_of_witnessing"}

    def scan(self, parent: str) -> dict:
        m = self._verified_status()
        anchors = m["state"]["anchors"]
        selected = {key: value for key, value in anchors.items() if value["parent"] == parent}
        if not selected:
            raise LabError("Unknown shelf or spatial fixture")
        names = self._verified_spine_titles()
        from .shelf_annex import physical_book_objects
        occupancy = {obj["anchor_id"]: {"id": oid,
                                       "name": names.get(oid, obj["name"]),
                                       "condition": obj["condition"]}
                     for oid, obj in physical_book_objects(self).items()
                     if obj["anchor_id"] is not None}
        return {"fixture_id": parent,
                "positions": [{"anchor_id": key, "ordinal": value["ordinal"],
                               "occupant": occupancy.get(key)}
                              for key, value in sorted(
                                  selected.items(), key=lambda item: item[1]["ordinal"])],
                "revision": m["revision"], "event_cursor": m["head_hash"],
                "mode": m["mode"], "visibility": "research_private"}

    def observe(self, room: str = "room:sanctum") -> dict:
        m = self._verified_status()
        if room not in ROOMS:
            raise LabError("Unknown room")
        state = m["state"]
        from .shelf_annex import physical_book_objects
        objects = physical_book_objects(self)
        names = self._verified_spine_titles()
        return {"room_id": room, "home_id": m["home_id"],
                "lab_id": m["lab_id"], "world_epoch": m["world_epoch"],
                "revision": m["revision"], "event_cursor": m["head_hash"],
                "mode": m["mode"], "observation_class": "source_attested_host_view",
                "visibility": "research_private",
                "objects": {oid: {
                    "name": names.get(oid, obj["name"]), "kind": obj["kind"],
                    "condition": obj["condition"], "collected": obj.get("collected", True),
                    "anchor_id": obj["anchor_id"],
                } for oid, obj in sorted(objects.items())
                    if (obj["anchor_id"] is not None and
                        state["anchors"][obj["anchor_id"]]["room"] == room)}}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Opt-in precise persistent habitat v2")
    parser.add_argument("--db", default="data/habitat-v2.sqlite3")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("verify")
    sub.add_parser("checkpoint")
    sub.add_parser("status")
    look = sub.add_parser("observe"); look.add_argument("room", nargs="?", default="room:sanctum")
    loc = sub.add_parser("locate"); loc.add_argument("object_id")
    inspect = sub.add_parser("inspect-geometry"); inspect.add_argument("object_id")
    scan = sub.add_parser("scan"); scan.add_argument("fixture_id")
    action = sub.add_parser("act")
    action.add_argument("operation", choices=("place", "break", "collect", "advance_ticks"))
    action.add_argument("value")
    action.add_argument("destination", nargs="?")
    backup = sub.add_parser("backup"); backup.add_argument("destination")
    fork = sub.add_parser("fork"); fork.add_argument("destination")
    args = parser.parse_args(argv)
    lab = SpatialHabitat(args.db)
    try:
        if args.cmd == "init":
            result = SpatialHabitat.create(args.db).verify()
        elif args.cmd == "verify":
            result = lab.verify()
        elif args.cmd == "checkpoint":
            result = lab.checkpoint()
        elif args.cmd == "status":
            result = lab.status()
        elif args.cmd == "observe":
            result = lab.observe(args.room)
        elif args.cmd == "locate":
            result = lab.locate(args.object_id)
        elif args.cmd == "inspect-geometry":
            result = lab.inspect_object(args.object_id)
        elif args.cmd == "scan":
            result = lab.scan(args.fixture_id)
        elif args.cmd == "backup":
            result = lab.backup_to(args.destination)
        elif args.cmd == "fork":
            result = lab.fork_to(args.destination)
        else:
            op = args.operation
            if op == "place":
                if args.destination is None:
                    raise LabError("place requires precise destination anchor")
                command = {"op": op, "object_id": args.value,
                           "anchor_id": args.destination}
            elif op == "advance_ticks":
                if args.destination is not None:
                    raise LabError("Unexpected destination")
                command = {"op": op, "ticks": int(args.value)}
            else:
                if args.destination is not None:
                    raise LabError("Unexpected destination")
                command = {"op": op, "object_id": args.value}
            result = lab.commit(command)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (LabError, Conflict, ValueError, KeyError, FileNotFoundError, FileExistsError) as exc:
        parser.exit(2, f"Habitat error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
