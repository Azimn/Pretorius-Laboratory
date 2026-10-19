"""Opt-in standing household supplier contract, not a free global pantry patch.

The contract registers a permanent offstage supply source *within this world*.
It does not add food itself or trigger automatic eating. The original
DailyRhythm action commits each dated voluntary delivery as the sole physical
supply authority. Older worlds with no contract remain untouched.
"""
from __future__ import annotations
import json

from .habitat_v2 import SpatialHabitat
from .physics import Conflict, LabError, canonical, digest

RULES = "pretorius-care-standing-supplier/1"
SOURCE = "standing-order-from-nearby-town"


def exists(db):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='care_contract'"
    ).fetchone() is not None


def _read(db):
    if not exists(db):
        return None
    return {k: json.loads(v) for k, v in db.execute(
        "SELECT key,value FROM care_contract")}


def valid(db):
    """Validate in the current transaction; do NOT recursively verify rhythm."""
    m = _read(db)
    if m is None:
        return None
    world = SpatialHabitat._metadata(db)
    row = db.execute(
        "SELECT value FROM rhythm_meta WHERE key='state'").fetchone()
    if row is None:
        raise Conflict("Care agreement has no physical world clock")
    clock = json.loads(row[0])
    data = {
        "rules": m.get("rules"), "supplier": m.get("supplier"),
        "lab_id": m.get("lab_id"), "home_id": m.get("home_id"),
        "world_epoch": m.get("world_epoch"),
        "installed_at_minute": m.get("installed_at_minute"),
        "sanitation": m.get("sanitation"),
        "water_service": m.get("water_service"),
        "inherited_from": m.get("inherited_from"),
    }
    if (data["rules"] != RULES or data["supplier"] != SOURCE
            or data["sanitation"] != "private-bedroom-washroom-with-water-closet"
            or data["water_service"] != "fixed-potable-kitchen-tap"
            or (data["lab_id"], data["home_id"], data["world_epoch"]) !=
            (world["lab_id"], world["home_id"], world["world_epoch"])
            or type(data["installed_at_minute"]) is not int
            or data["installed_at_minute"] < 420
            or data["installed_at_minute"] > clock["minute"]
            or digest(data) != m.get("contract_hash")):
        raise Conflict("Standing supply agreement lacks valid world provenance")
    return data


class HouseholdCareContract:
    def __init__(self, habitat):
        self.habitat = habitat

    def initialize(self, *, inherited_from=None):
        from .daily_rhythm import DailyRhythm, PAPER_RULES
        clock = DailyRhythm(self.habitat)
        clock.verify()
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            if exists(db):
                raise Conflict("Standing supplier agreement already installed")
            world = SpatialHabitat._metadata(db)
            rhythm = {k: json.loads(v) for k, v in db.execute(
                "SELECT key,value FROM rhythm_meta")}
            if rhythm["rules"] != PAPER_RULES:
                raise LabError("Living-world paper v5 is required for care contract")
            data = {
                "rules": RULES, "supplier": SOURCE,
                "lab_id": world["lab_id"], "home_id": world["home_id"],
                "world_epoch": world["world_epoch"],
                "installed_at_minute": rhythm["state"]["minute"],
                "sanitation": "private-bedroom-washroom-with-water-closet",
                "water_service": "fixed-potable-kitchen-tap",
                "inherited_from": inherited_from,
            }
            db.execute(
                "CREATE TABLE care_contract(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            for key, value in {**data, "contract_hash": digest(data)}.items():
                db.execute("INSERT INTO care_contract VALUES (?,?)",
                           (key, canonical(value)))
        return self.verify()

    def verify(self):
        with self.habitat._open() as db:
            data = valid(db)
        if data is None:
            raise LabError("This world has no signed supply agreement")
        return {"verified": True, "rules": data["rules"]}

    def _fork_into(self, child):
        self.verify()
        with self.habitat._open() as db:
            parent = valid(db)
        return HouseholdCareContract(child).initialize(inherited_from={
            "lab_id": parent["lab_id"], "world_epoch": parent["world_epoch"],
            "original_installation": parent["installed_at_minute"],
        })
