"""Fixed bench ruler and balance; synthetic measurements with bounded uncertainty.

Instruments are built into the preexisting bench fixture, not additional
mobile objects. A measurement OFFER is not proof of Pretorius remembering it.
"""
from __future__ import annotations

import json
import uuid

from .habitat_v2 import SpatialHabitat
from .embodied_access import EmbodiedAccess, SUBJECT_ID
from .book_custody import BookCustody, effective_objects, _apply as apply_custody
from .physical_affordances import PhysicalAffordances, profile_at
from .physics import Conflict, LabError, canonical, digest
from .store import GENESIS_HASH, _utc

RULES = "bench-instruments/1"
BENCH = "bench:main/position:left"
STATION = "station:bench"
SOURCE = "synthetic_calibrated_fixture_not_real_measurement"
DEVICES = {
    "ruler:bench": {"quantities": ["width_mm", "height_mm", "depth_mm"],
                    "resolution": 5, "uncertainty": 3, "unit": "mm",
                    "calibration": "declared_zero_bias_synthetic"},
    "balance:bench": {"quantities": ["mass_g"], "resolution": 25,
                      "uncertainty": 13, "unit": "g",
                      "calibration": "declared_zero_bias_synthetic"},
}


def exists(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='instrument_meta'").fetchone() is not None


def _meta(db):
    return {k: json.loads(v) for k, v in db.execute("SELECT key,value FROM instrument_meta")}


def _put(db, k, v):
    db.execute("INSERT OR REPLACE INTO instrument_meta(key,value) VALUES (?,?)",
               (k, canonical(v)))


def _cursor(db, table, n):
    if type(n) is not int or n < 0:
        return None
    if n == 0:
        return GENESIS_HASH
    x = db.execute(f"SELECT event_hash FROM {table} WHERE revision=?", (n,)).fetchone()
    return x[0] if x else None


def _pose(db, n):
    if n == 0:
        r = db.execute("SELECT value FROM embodied_meta WHERE key='initial_station'").fetchone()
        return (GENESIS_HASH, json.loads(r[0])) if r else (None, None)
    r = db.execute("SELECT envelope,event_hash FROM embodied_events WHERE revision=?",
                   (n,)).fetchone()
    return (r[1], json.loads(r[0])["after_station"]) if r else (None, None)


def _at_custody_revision(db, n):
    """Reconstruct historical placements rather than validating old measurements
    against the latest scene (which may have changed)."""
    from .book_custody import _meta as custody_meta
    m = custody_meta(db)
    if type(n) is not int or n < 0 or n > m["revision"]:
        raise Conflict("Unknown historic physical placement revision")
    state = {}
    for row in db.execute("SELECT envelope FROM custody_events WHERE revision<=? ORDER BY revision", (n,)):
        state = apply_custody(state, json.loads(row[0])["action"],
                              sandbox=m["mode"] == "sandbox")
    return state


def _readout(profile, device, object_id, quantity):
    if device not in DEVICES or quantity not in DEVICES[device]["quantities"]:
        raise LabError("Unsupported physical measurement")
    if object_id not in profile["object_profiles"]:
        raise LabError("Unprofiled physical object")
    conf = DEVICES[device]
    raw = profile["object_profiles"][object_id][quantity]
    increment = conf["resolution"]
    value = ((2 * raw + increment) // (2 * increment)) * increment
    error = conf["uncertainty"]
    if not value - error <= raw <= value + error:
        raise Conflict("Stated instrument interval excludes synthetic source")
    return {
        "quantity": quantity, "value": value, "unit": conf["unit"],
        "resolution": increment, "uncertainty": error,
        "interval": [value - error, value + error],
        "uncertainty_class": "bounded_declared_fixture",
        "source_class": SOURCE,
    }


class BenchInstruments:
    def __init__(self, habitat: SpatialHabitat):
        self.habitat = habitat

    def _prerequisites(self):
        self.habitat.verify()
        EmbodiedAccess(self.habitat).verify()
        BookCustody(self.habitat).verify()
        return PhysicalAffordances(self.habitat).verify()

    def initialize(self):
        profile = self._prerequisites()
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            host = SpatialHabitat._metadata(db)
            db.execute("CREATE TABLE IF NOT EXISTS instrument_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS instrument_events(
                revision INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL,
                envelope TEXT NOT NULL, prev_hash TEXT NOT NULL,
                event_hash TEXT UNIQUE NOT NULL)""")
            m = _meta(db)
            if not m:
                for k, v in {
                    "lab_id": host["lab_id"], "home_id": host["home_id"],
                    "world_epoch": host["world_epoch"], "mode": host["mode"],
                    "subject_id": SUBJECT_ID, "ruleset": RULES,
                    "devices": DEVICES, "calibration_digest": digest(DEVICES),
                    "profile_digest": profile["profile_digest"],
                    "revision": 0, "head_hash": GENESIS_HASH,
                    "parent_instruments": None,
                }.items():
                    _put(db, k, v)
            else:
                self._header(m, host, profile["profile_digest"])
        return self.verify()

    @staticmethod
    def _header(m, host, profile_digest):
        if (m.get("lab_id"), m.get("home_id"), m.get("world_epoch"),
            m.get("mode"), m.get("subject_id"), m.get("ruleset"),
            m.get("profile_digest"), m.get("calibration_digest")) != (
                host["lab_id"], host["home_id"], host["world_epoch"],
                host["mode"], SUBJECT_ID, RULES,
                profile_digest, digest(DEVICES)):
            raise Conflict("Bench instrument world/calibration binding is invalid")
        if m.get("devices") != DEVICES:
            raise Conflict("Bench instrument calibration was changed")

    def verify(self):
        active = self._prerequisites()
        with self.habitat._open() as db:
            if not exists(db):
                raise LabError("Bench instruments are not initialized")
            host = SpatialHabitat._metadata(db)
            m = _meta(db)
            self._header(m, host, active["profile_digest"])
            p = profile_at(db, host)
            from .book_custody import _raw
            _, original, _, _ = _raw(db)
            h, count = GENESIS_HASH, 0
            for n, event_id, encoded, prior, event_hash in db.execute(
                "SELECT revision,event_id,envelope,prev_hash,event_hash FROM instrument_events ORDER BY revision"):
                e = json.loads(encoded)
                if (n != count + 1 or e["revision"] != n or
                    e["event_id"] != event_id or e["previous_hash"] != prior or
                    prior != h or event_hash != digest(e)):
                    raise Conflict("Instrument event chain cannot be replayed")
                if (e["lab_id"], e["world_epoch"], e["subject_id"],
                    e["profile_digest"], e["calibration_digest"]) != (
                    m["lab_id"], m["world_epoch"], SUBJECT_ID,
                    m["profile_digest"], m["calibration_digest"]):
                    raise Conflict("Instrument event from unrelated world or calibration")
                if (e["world_cursor"] != _cursor(db, "events", e["world_revision"]) or
                    e["annex_cursor"] != _cursor(db, "annex_events", e["annex_revision"]) or
                    e["custody_cursor"] != _cursor(db, "custody_events", e["custody_revision"])):
                    raise Conflict("Source world cursors for measurement are missing")
                if _pose(db, e["body_revision"]) != (e["body_cursor"], STATION):
                    raise Conflict("Reading has no corresponding subject bench position")
                oid = e["object_id"]
                if oid not in original or e["placement"] != BENCH:
                    raise Conflict("Reading references an unregistered object or surface")
                if oid not in host["state"]["objects"]:
                    if e["annex_revision"] == 0:
                        raise Conflict("Measured book not yet in annex")
                    creation = db.execute(
                        "SELECT 1 FROM annex_events WHERE revision<=? AND json_extract(envelope,'$.action.book_id')=? AND json_extract(envelope,'$.action.op') IN ('register','fork_seed')",
                        (e["annex_revision"], oid)).fetchone()
                    if not creation:
                        raise Conflict("Source object did not exist at this measurement")
                positions = _at_custody_revision(db, e["custody_revision"])
                from .shelf_annex import ShelfAnnex
                # Raw genesis is the fallback for never-moved volumes; all
                # custody-handled objects have an explicit historical position.
                physical_location = (positions[oid]["anchor_id"] if oid in positions
                                     else original[oid]["anchor_id"])
                if physical_location != BENCH:
                    raise Conflict("Measurement wasn't taken on the bench")
                if e.get("observation") != _readout(p, e["instrument"], oid, e["quantity"]):
                    raise Conflict("Measurement was altered or manufactured")
                if e["observation_digest"] != digest(e["observation"]):
                    raise Conflict("Measurement digest invalid")
                count, h = n, event_hash
            if (m["revision"], m["head_hash"]) != (count, h):
                raise Conflict("Instrument materialized event cursor mismatch")
            return {"verified": True, "revision": count, "event_cursor": h,
                    "world_epoch": m["world_epoch"],
                    "profile_digest": m["profile_digest"],
                    "calibration_digest": m["calibration_digest"]}

    def measure(self, device, object_id, quantity, *, event_id=None):
        if device not in DEVICES or quantity not in DEVICES[device]["quantities"]:
            raise LabError("Unknown instrument or measurement quantity")
        if not isinstance(object_id, str) or not object_id:
            raise LabError("Invalid target")
        self.verify()
        event_id = event_id or str(uuid.uuid4())
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
            raise LabError("Invalid instrument event ID")
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            m, host = _meta(db), SpatialHabitat._metadata(db)
            old = db.execute(
                "SELECT envelope,event_hash FROM instrument_events WHERE event_id=?",
                (event_id,)).fetchone()
            if old:
                e = json.loads(old[0])
                if (e["instrument"], e["object_id"], e["quantity"]) != (
                        device, object_id, quantity):
                    raise Conflict("Instrument event identifier reused")
                return self._result(e, old[1])
            pose = {k: json.loads(v) for k, v in db.execute(
                "SELECT key,value FROM embodied_meta")}
            custody = {k: json.loads(v) for k, v in db.execute(
                "SELECT key,value FROM custody_meta")}
            if pose["station"] != STATION or (
                    _pose(db, pose["revision"]) != (pose["head_hash"], STATION)):
                raise LabError("Approach the workbench instrument first")
            from .rhythm_gate import require as require_daily_conditions
            require_daily_conditions(db, pose["station"], "measure")
            if _cursor(db, "custody_events", custody["revision"]) != custody["head_hash"]:
                raise Conflict("World handling cursor is invalid")
            obj = effective_objects(db).get(object_id)
            if obj is None or obj["anchor_id"] != BENCH or obj.get("held_by") is not None:
                raise LabError("Place the object on the bench measuring surface")
            if obj["condition"] == "broken" and not obj["collected"]:
                raise LabError("Scattered glass cannot be measured as one intact item")
            profile = profile_at(db, host)
            if profile is None or digest(profile) != m["profile_digest"]:
                raise Conflict("Instrument source profile is unavailable")
            observation = _readout(profile, device, object_id, quantity)
            from .shelf_annex import ShelfAnnex
            if ShelfAnnex.exists(db):
                annex = {k: json.loads(v) for k, v in db.execute(
                    "SELECT key,value FROM annex_meta")}
            else:
                annex = {"revision": 0, "head_hash": GENESIS_HASH}
            e = {
                "revision": m["revision"] + 1, "event_id": event_id,
                "lab_id": m["lab_id"], "world_epoch": m["world_epoch"],
                "subject_id": SUBJECT_ID, "instrument": device,
                "object_id": object_id, "quantity": quantity, "placement": BENCH,
                "observation": observation, "observation_digest": digest(observation),
                "body_revision": pose["revision"], "body_cursor": pose["head_hash"],
                "custody_revision": custody["revision"],
                "custody_cursor": custody["head_hash"],
                "world_revision": host["revision"], "world_cursor": host["head_hash"],
                "annex_revision": annex["revision"], "annex_cursor": annex["head_hash"],
                "profile_digest": m["profile_digest"],
                "calibration_digest": m["calibration_digest"],
                "previous_hash": m["head_hash"], "recorded_utc": _utc(),
                "claim": "instrument_readout_offered_not_lived_memory",
            }
            h = digest(e)
            db.execute("INSERT INTO instrument_events VALUES (?,?,?,?,?)",
                       (e["revision"], event_id, canonical(e), m["head_hash"], h))
            _put(db, "head_hash", h)
            _put(db, "revision", e["revision"])
            return self._result(e, h)

    @staticmethod
    def _result(e, event_hash):
        return {"event_id": e["event_id"], "event_hash": event_hash,
                "instrument": e["instrument"], "object_id": e["object_id"],
                "observation": e["observation"],
                "observation_class": "offered_not_attested_subject_memory"}

    def _fork_into(self, clone):
        self.verify()
        with self.habitat._open() as db:
            parent = _meta(db)
        child = BenchInstruments(clone)
        child.initialize()
        with clone._open() as db:
            db.execute("BEGIN IMMEDIATE")
            _put(db, "parent_instruments", {
                "source_epoch": parent["world_epoch"],
                "source_cursor": parent["head_hash"],
                "source_revision": parent["revision"],
                "claim": "parent_provenance_not_child_sensory_experience",
            })
        child.verify()
