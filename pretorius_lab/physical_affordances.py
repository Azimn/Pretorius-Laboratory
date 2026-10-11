"""Opt-in, source-labelled mechanical affordances for a persistent synthetic lab.

No measured historical book dimensions are claimed. The values are explicit
integer engineering fixture assumptions, never first-person subject knowledge.
They are frozen per world epoch and protected by a deterministic digest.
"""
from __future__ import annotations

import copy
import json

from .habitat_v2 import SpatialHabitat
from .physics import Conflict, LabError, canonical, digest

AFFORDANCE_RULES = "fixture-mechanical-affordances/1"
SOURCE_CLASS = "synthetic_declared_not_measured"
# Coordinates and dimensions use mm, mass is integer grams; these are
# conservative synthetic test capacities, not 1890s printed-edition data.
BASE_PROFILE = {
    "schema": AFFORDANCE_RULES,
    "source_class": SOURCE_CLASS,
    "object_profiles": {
        **{f"book:{i:03d}": {
            "mass_g": (1600 if i in (8, 9) else 850),
            "width_mm": (55 if i in (8, 9) else 42),
            "height_mm": 255,
            "depth_mm": 180,
            "source_class": SOURCE_CLASS,
        } for i in range(1, 18)},
        "beaker:001": {
            "mass_g": 330, "width_mm": 55, "height_mm": 95,
            "depth_mm": 55, "source_class": SOURCE_CLASS,
        },
    },
    "anchor_class_limits": {
        "shelf_slot": {
            "width_mm": 60, "height_mm": 300, "depth_mm": 255,
            "max_mass_g": 2400,
        },
        "bench_spot": {
            "width_mm": 550, "height_mm": 450, "depth_mm": 550,
            "max_mass_g": 15000,
        },
        "floor_spot": {
            "width_mm": 1000, "height_mm": 1100, "depth_mm": 1000,
            "max_mass_g": 50000,
        },
    },
    "actor_limits": {
        "max_carry_mass_g": 2500,
        "max_reach_height_mm": 2000,
    },
}


def _meta(db):
    return {k: json.loads(v) for k, v in db.execute(
        "SELECT key,value FROM affordance_meta")}


def exists(db):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='affordance_meta'"
    ).fetchone() is not None


def _put(db, key, value):
    db.execute("INSERT OR REPLACE INTO affordance_meta(key,value) VALUES (?,?)",
               (key, canonical(value)))


def validate(profile):
    if (not isinstance(profile, dict) or set(profile) != {
            "schema", "source_class", "object_profiles",
            "anchor_class_limits", "actor_limits"} or
            profile["schema"] != AFFORDANCE_RULES or
            profile["source_class"] != SOURCE_CLASS):
        raise LabError("Invalid or unsupported mechanical profile provenance")
    ids = profile["object_profiles"]
    if not isinstance(ids, dict) or set(ids) != set(BASE_PROFILE["object_profiles"]):
        raise LabError("Every physical fixture object requires an explicit profile")
    for key, p in ids.items():
        if not isinstance(p, dict) or set(p) != {
                "mass_g", "width_mm", "height_mm", "depth_mm", "source_class"} or (
                p["source_class"] != SOURCE_CLASS):
            raise LabError("Invalid source-labelled object profile: " + key)
        for quantity in ("mass_g", "width_mm", "height_mm", "depth_mm"):
            val = p[quantity]
            if type(val) is not int or not 1 <= val <= 100000:
                raise LabError("Invalid mechanical quantity: " + key + "." + quantity)
    classes = profile["anchor_class_limits"]
    if not isinstance(classes, dict) or set(classes) != {
            "shelf_slot", "bench_spot", "floor_spot"}:
        raise LabError("Unknown or incomplete anchor clearance classes")
    for kind, limit in classes.items():
        if not isinstance(limit, dict) or set(limit) != {
                "width_mm", "height_mm", "depth_mm", "max_mass_g"}:
            raise LabError("Invalid clearance profile: " + kind)
        if any(type(v) is not int or not 1 <= v <= 1000000
               for v in limit.values()):
            raise LabError("Invalid physical clearance units")
    actor = profile["actor_limits"]
    if not isinstance(actor, dict) or set(actor) != {
            "max_carry_mass_g", "max_reach_height_mm"}:
        raise LabError("Invalid carrying/reach profile")
    if any(type(v) is not int or not 1 <= v <= 100000
           for v in actor.values()):
        raise LabError("Invalid actor limit")
    return profile


def profile_at(db, host):
    """Return verified immutable per-world assumptions or None if opt-out."""
    if not exists(db):
        return None
    m = _meta(db)
    if (m.get("lab_id"), m.get("home_id"), m.get("world_epoch"),
            m.get("mode"), m.get("ruleset")) != (
            host["lab_id"], host["home_id"], host["world_epoch"],
            host["mode"], AFFORDANCE_RULES):
        raise Conflict("Mechanical profile belongs to another world")
    config = m.get("profile")
    try:
        validate(config)
    except LabError as exc:
        raise Conflict("Mechanical calibration metadata corrupted") from exc
    if m.get("profile_digest") != digest(config):
        raise Conflict("Mechanical profile fingerprint changed")
    return config


def check_surface(profile, object_id, anchor_id, host):
    if profile is None:
        return
    obj = profile["object_profiles"].get(object_id)
    if obj is None:
        raise LabError("No authorized dimensions/mass profile for " + object_id)
    anchor = host["state"]["anchors"].get(anchor_id)
    if anchor is None:
        raise LabError("Unknown physical placement")
    aperture = profile["anchor_class_limits"].get(anchor["kind"])
    if aperture is None:
        raise LabError("No mechanical clearance profile for surface")
    for side in ("width_mm", "height_mm", "depth_mm"):
        if obj[side] > aperture[side]:
            raise LabError("Object exceeds surface clearance: " + side)
    if obj["mass_g"] > aperture["max_mass_g"]:
        raise LabError("Object exceeds supported surface mass")


def check_actor_reach(profile, object_id, anchor_id, host, *, lifting):
    if profile is None:
        return
    if object_id not in profile["object_profiles"]:
        raise LabError("Object lacks source-labelled mechanical data")
    anchor = host["state"]["anchors"].get(anchor_id)
    if anchor is None:
        raise LabError("Unknown physical station anchor")
    if anchor["xyz_mm"][2] > profile["actor_limits"]["max_reach_height_mm"]:
        raise LabError("Physical location exceeds actor's declared reach")
    if lifting and profile["object_profiles"][object_id]["mass_g"] > (
            profile["actor_limits"]["max_carry_mass_g"]):
        raise LabError("Book mass exceeds declared carrying capacity")


def check_carried(profile, object_id):
    if profile is None:
        return
    p = profile["object_profiles"].get(object_id)
    if p is None:
        raise LabError("Book has no mechanical profile")
    if p["mass_g"] > profile["actor_limits"]["max_carry_mass_g"]:
        raise LabError("Book exceeds carrying capacity")


class PhysicalAffordances:
    def __init__(self, habitat: SpatialHabitat):
        self.habitat = habitat

    def initialize(self, *, profile=None):
        self.habitat.verify()
        candidate = copy.deepcopy(BASE_PROFILE if profile is None else profile)
        validate(candidate)
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            host = SpatialHabitat._metadata(db)
            db.execute("CREATE TABLE IF NOT EXISTS affordance_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            prior = _meta(db)
            if not prior:
                # Reject enabling mechanical rules over an already impossible
                # scene; do not retroactively rewrite older physical history.
                from .book_custody import effective_objects
                objects = effective_objects(db)
                for oid, obj in objects.items():
                    if obj["anchor_id"] is not None:
                        check_surface(candidate, oid, obj["anchor_id"], host)
                    elif obj.get("held_by") is not None:
                        check_carried(candidate, oid)
                for k, v in {
                    "lab_id": host["lab_id"], "home_id": host["home_id"],
                    "world_epoch": host["world_epoch"], "mode": host["mode"],
                    "ruleset": AFFORDANCE_RULES,
                    "profile": candidate, "profile_digest": digest(candidate),
                    "parent_affordance": None,
                }.items():
                    _put(db, k, v)
            else:
                existing = profile_at(db, host)
                if existing != candidate:
                    raise Conflict("A world cannot silently rewrite its mechanical assumptions")
        return self.verify()

    def verify(self):
        proof = self.habitat.verify()
        with self.habitat._open() as db:
            if not exists(db):
                raise LabError("Physical affordances not initialized")
            host = SpatialHabitat._metadata(db)
            profile = profile_at(db, host)
            from .book_custody import effective_objects
            objects = effective_objects(db)
            for oid, obj in objects.items():
                if obj["anchor_id"] is None:
                    check_carried(profile, oid)
                else:
                    check_surface(profile, oid, obj["anchor_id"], host)
            return {"verified": True, "world_epoch": proof["world_epoch"],
                    "profile_digest": digest(profile), "object_count": len(objects),
                    "source_class": SOURCE_CLASS}

    def inspect_engineer_only(self):
        self.verify()
        with self.habitat._open() as db:
            return copy.deepcopy(_meta(db)["profile"])

    def _fork_into(self, clone):
        self.verify()
        with self.habitat._open() as db:
            m = _meta(db)
        target = PhysicalAffordances(clone)
        target.initialize(profile=m["profile"])
        with clone._open() as db:
            db.execute("BEGIN IMMEDIATE")
            _put(db, "parent_affordance", {
                "world_epoch": m["world_epoch"],
                "profile_digest": m["profile_digest"],
                "source_class": "inherited_fixture_assumptions_not_measurement",
            })
        target.verify()
