"""Conserved synthetic water in the existing portable laboratory beaker.

Fixed bench tap and receiving basin are stationary *fixtures*, not new
movable objects. No chemistry, pressure, spilling, humidity or cognition
is claimed. Exact source volumes are engineer-audit data.
"""
from __future__ import annotations

import copy
import json
import uuid

from .physics import Conflict, LabError, canonical, digest
from .store import GENESIS_HASH, _utc
from .habitat_v2 import SpatialHabitat
from .embodied_access import EmbodiedAccess, SUBJECT_ID
from .book_custody import BookCustody, effective_objects
from .physical_affordances import PhysicalAffordances, profile_at
from .bench_instruments import _pose, _cursor, _at_custody_revision

RULES = "bench-conserved-liquid/1"
SOURCE = "synthetic_declared_water_at_one_gram_per_ml"
BENCH = "bench:main/position:left"
STATION = "station:bench"
TOTAL_ML = 1000
VESSEL_CAP_ML = 250
BASIN_CAP_ML = 1000
STEP_ML = 25
INITIAL = {"reservoir_ml": TOTAL_ML, "beaker_ml": 0, "basin_ml": 0}


def exists(db):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='liquid_meta'"
    ).fetchone() is not None


def _meta(db):
    return {k: json.loads(v) for k, v in db.execute("SELECT key,value FROM liquid_meta")}


def _put(db, key, value):
    db.execute("INSERT OR REPLACE INTO liquid_meta(key,value) VALUES (?,?)",
               (key, canonical(value)))


def _valid(state):
    if not isinstance(state, dict) or set(state) != set(INITIAL):
        raise Conflict("Liquid inventory schema corrupted")
    for key, maximum in (("reservoir_ml", TOTAL_ML),
                         ("beaker_ml", VESSEL_CAP_ML),
                         ("basin_ml", BASIN_CAP_ML)):
        n = state[key]
        if type(n) is not int or n < 0 or n > maximum or n % STEP_ML:
            raise Conflict("Liquid volume out of conserved capacity range")
    if sum(state.values()) != TOTAL_ML:
        raise Conflict("Synthetic water was created or destroyed")
    return state


def _apply(state, operation, ml):
    if operation not in ("fill", "pour"):
        raise LabError("Unknown liquid handling operation")
    if type(ml) is not int or not STEP_ML <= ml <= VESSEL_CAP_ML or ml % STEP_ML:
        raise LabError("Liquid measure must be 25 to 250 ml in 25 ml steps")
    out = copy.deepcopy(_valid(state))
    if operation == "fill":
        origin, target = "reservoir_ml", "beaker_ml"
        capacity = VESSEL_CAP_ML
    else:
        origin, target = "beaker_ml", "basin_ml"
        capacity = BASIN_CAP_ML
    if out[origin] < ml:
        raise LabError("Insufficient water at the source")
    if out[target] + ml > capacity:
        raise LabError("Receiving vessel does not have enough capacity")
    out[origin] -= ml
    out[target] += ml
    return _valid(out)


def volume_at(db, revision=None):
    """Historical liquid state at exact revision, without subject projection.

    A world with no liquid system retains its old dry-beaker semantics.
    The caller must authenticate material ledger before trusting its values.
    """
    if not exists(db):
        if revision not in (None, 0):
            raise Conflict("Historical liquid events do not exist")
        return copy.deepcopy(INITIAL)
    m = _meta(db)
    if revision is None:
        revision = m["revision"]
    if type(revision) is not int or revision < 0 or revision > m["revision"]:
        raise Conflict("Unknown liquid event revision")
    state = copy.deepcopy(m["origin_state"])
    _valid(state)
    for n, encoded in db.execute(
            "SELECT revision,envelope FROM liquid_events WHERE revision<=? ORDER BY revision",
            (revision,)):
        e = json.loads(encoded)
        if n != e["revision"]:
            raise Conflict("Inconsistent liquid revision")
        state = _apply(state, e["operation"], e["volume_ml"])
    return state


def public_level(ml):
    """Ordinal qualitative observation, not a raw engineer volume."""
    if ml == 0:
        return "empty"
    if ml <= 50:
        return "a little water"
    if ml <= 125:
        return "about half full"
    if ml < VESSEL_CAP_ML:
        return "mostly full"
    return "full"


class BenchLiquids:
    def __init__(self, habitat: SpatialHabitat):
        self.habitat = habitat

    def _pre(self):
        self.habitat.verify()
        EmbodiedAccess(self.habitat).verify()
        BookCustody(self.habitat).verify()
        return PhysicalAffordances(self.habitat).verify()

    def initialize(self, *, _fork_origin=None, _parent=None):
        self._pre()
        initial = _valid(copy.deepcopy(INITIAL if _fork_origin is None else _fork_origin))
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            host = SpatialHabitat._metadata(db)
            db.execute("CREATE TABLE IF NOT EXISTS liquid_meta("
                       "key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS liquid_events(
                revision INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL,
                envelope TEXT NOT NULL, prev_hash TEXT NOT NULL,
                event_hash TEXT UNIQUE NOT NULL)""")
            m = _meta(db)
            if not m:
                for k, v in {
                    "lab_id": host["lab_id"], "home_id": host["home_id"],
                    "world_epoch": host["world_epoch"], "mode": host["mode"],
                    "subject_id": SUBJECT_ID, "ruleset": RULES,
                    "source_class": SOURCE, "origin_state": initial,
                    "origin_digest": digest(initial), "state": initial,
                    "revision": 0, "head_hash": GENESIS_HASH,
                    "parent_liquid_custody": _parent,
                }.items():
                    _put(db, k, v)
            elif (_fork_origin is not None or m["origin_state"] != initial):
                raise Conflict("Liquid state cannot be reset during reinitialization")
        return self.verify()

    def verify(self):
        self._pre()
        with self.habitat._open() as db:
            if not exists(db):
                raise LabError("Synthetic bench liquids are not initialized")
            m = _meta(db)
            host = SpatialHabitat._metadata(db)
            if (m["lab_id"], m["home_id"], m["world_epoch"], m["mode"],
                m["subject_id"], m["ruleset"], m["source_class"]) != (
                    host["lab_id"], host["home_id"], host["world_epoch"],
                    host["mode"], SUBJECT_ID, RULES, SOURCE):
                raise Conflict("Liquid source/world provenance mismatch")
            state = _valid(copy.deepcopy(m["origin_state"]))
            if digest(state) != m["origin_digest"]:
                raise Conflict("Material genesis digest changed")
            if (m["parent_liquid_custody"] is not None and
                    (not isinstance(m["parent_liquid_custody"], dict) or
                     m["mode"] != "sandbox")):
                raise Conflict("Illegitimate liquid fork provenance")
            h, count = GENESIS_HASH, 0
            profile = profile_at(db, host)
            if profile is None:
                raise Conflict("Liquid handling requires declared mechanical profiles")
            from .book_custody import _raw
            _, originals, _, _ = _raw(db)
            for n, event_id, encoded, prior, event_hash in db.execute(
                "SELECT revision,event_id,envelope,prev_hash,event_hash "
                "FROM liquid_events ORDER BY revision"
            ):
                e = json.loads(encoded)
                if (n != count + 1 or e["revision"] != n or
                    e["event_id"] != event_id or e["previous_hash"] != h or
                    prior != h or event_hash != digest(e)):
                    raise Conflict("Liquid event chain corrupted")
                if (e["world_epoch"], e["lab_id"], e["subject_id"],
                    e["profile_digest"]) != (
                    m["world_epoch"], m["lab_id"], SUBJECT_ID, digest(profile)):
                    raise Conflict("Liquid event references foreign provenance")
                if (e["world_cursor"] != _cursor(db, "events", e["world_revision"]) or
                    e["custody_cursor"] != _cursor(
                        db, "custody_events", e["custody_revision"])):
                    raise Conflict("Liquid event references unknown physical scene")
                if _pose(db, e["body_revision"]) != (e["body_cursor"], STATION):
                    raise Conflict("Liquid transfer was not at the bench")
                placements = _at_custody_revision(db, e["custody_revision"])
                original = originals["beaker:001"]["anchor_id"]
                historical = (placements["beaker:001"]["anchor_id"]
                              if "beaker:001" in placements else original)
                if historical != BENCH:
                    raise Conflict("Liquid was transferred to an inaccessible vessel")
                if e["before_digest"] != digest(state):
                    raise Conflict("Liquid before-state tampered")
                try:
                    state = _apply(state, e["operation"], e["volume_ml"])
                except LabError as exc:
                    raise Conflict("Recorded liquid transfer is physically invalid") from exc
                # No overflowing the real beaker's declared bench spot.
                full_mass = profile["object_profiles"]["beaker:001"]["mass_g"] + state["beaker_ml"]
                bench_cap = profile["anchor_class_limits"]["bench_spot"]["max_mass_g"]
                if full_mass > bench_cap:
                    raise Conflict("Liquid transfer exceeded supported bench mass")
                if e["after_digest"] != digest(state):
                    raise Conflict("Liquid after-state tampered")
                count, h = n, event_hash
            if (m["revision"], m["head_hash"], m["state"]) != (count, h, state):
                raise Conflict("Liquid state differs from conserved event replay")
            return {"verified": True, "revision": count, "event_cursor": h,
                    "world_epoch": m["world_epoch"], "source_class": SOURCE,
                    "inventory_digest": digest(state), "conserved_ml": TOTAL_ML}

    def transfer(self, operation, ml, *, event_id=None):
        if operation not in ("fill", "pour"):
            raise LabError("Invalid liquid command")
        if type(ml) is not int or not STEP_ML <= ml <= VESSEL_CAP_ML or ml % STEP_ML:
            raise LabError("Transfer must be in bounded 25 ml increments")
        self.verify()
        event_id = event_id or str(uuid.uuid4())
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
            raise LabError("Invalid liquid event id")
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            m = _meta(db)
            old = db.execute("SELECT envelope,event_hash FROM liquid_events WHERE event_id=?",
                             (event_id,)).fetchone()
            if old:
                e = json.loads(old[0])
                if (e["operation"], e["volume_ml"]) != (operation, ml):
                    raise Conflict("Liquid event ID reused with another operation")
                return self._receipt(e, old[1])
            host = SpatialHabitat._metadata(db)
            body = {k: json.loads(v) for k, v in db.execute(
                "SELECT key,value FROM embodied_meta")}
            custody = {k: json.loads(v) for k, v in db.execute(
                "SELECT key,value FROM custody_meta")}
            if (body["station"] != STATION or
                _pose(db, body["revision"]) != (body["head_hash"], STATION)):
                raise LabError("Approach the laboratory bench to handle water")
            if _cursor(db, "custody_events", custody["revision"]) != custody["head_hash"]:
                raise Conflict("Liquid transfer custody source is invalid")
            beaker = effective_objects(db)["beaker:001"]
            if beaker["anchor_id"] != BENCH or beaker.get("held_by") is not None:
                raise LabError("Set down the actual beaker at the bench before transfer")
            if beaker["condition"] != "intact":
                raise LabError("Broken glass cannot contain laboratory water")
            updated = _apply(m["state"], operation, ml)
            p = profile_at(db, host)
            dry_mass = p["object_profiles"]["beaker:001"]["mass_g"]
            if (dry_mass + updated["beaker_ml"] >
                    p["anchor_class_limits"]["bench_spot"]["max_mass_g"]):
                raise LabError("Water-filled beaker exceeds bench load")
            if digest(m["state"]) != digest(volume_at(db, m["revision"])):
                raise Conflict("Materialized liquid balance cannot be replayed")
            e = {
                "revision": m["revision"] + 1, "event_id": event_id,
                "lab_id": m["lab_id"], "world_epoch": m["world_epoch"],
                "subject_id": SUBJECT_ID, "operation": operation,
                "volume_ml": ml, "body_revision": body["revision"],
                "body_cursor": body["head_hash"],
                "custody_revision": custody["revision"],
                "custody_cursor": custody["head_hash"],
                "world_revision": host["revision"], "world_cursor": host["head_hash"],
                "profile_digest": digest(p),
                "before_digest": digest(m["state"]),
                "after_digest": digest(updated), "previous_hash": m["head_hash"],
                "recorded_utc": _utc(),
                "claim": "source_bounded_water_transfer_not_subject_memory",
            }
            h = digest(e)
            db.execute("INSERT INTO liquid_events VALUES (?,?,?,?,?)",
                       (e["revision"], event_id, canonical(e), m["head_hash"], h))
            _put(db, "state", updated)
            _put(db, "revision", e["revision"])
            _put(db, "head_hash", h)
            return self._receipt(e, h)

    @staticmethod
    def _receipt(event, event_hash):
        return {
            "event_id": event["event_id"], "event_hash": event_hash,
            "operation": event["operation"],
            "observation": ("Water flows into the glass beaker."
                            if event["operation"] == "fill"
                            else "Water flows from the glass beaker to the collecting basin."),
            "observation_class": "offered_not_attested_subject_experience",
        }

    def audit_engineer_only(self):
        self.verify()
        with self.habitat._open() as db:
            return copy.deepcopy(_meta(db)["state"])

    def _fork_into(self, clone):
        self.verify()
        with self.habitat._open() as db:
            m = _meta(db)
        BenchLiquids(clone).initialize(
            _fork_origin=m["state"], _parent={
                "parent_epoch": m["world_epoch"],
                "parent_revision": m["revision"],
                "parent_cursor": m["head_hash"],
                "claim": "inherited_liquid_inventory_not_new_subject_transfer",
            })
