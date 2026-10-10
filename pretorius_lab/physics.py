"""Deterministic laboratory physics. No renderer output is authoritative."""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0.0"
RULESET_VERSION = "lab-physics-0.1.0"

# IDs are deliberately stable. Do not regenerate them when reopening the lab.
MANIFEST = {
    "room:main": {"kind": "room", "name": "The Laboratory", "fixed": True, "location": None},
    "bench:main": {"kind": "surface", "name": "Oak laboratory bench", "fixed": True, "location": "room:main"},
    "container:specimen": {"kind": "container", "name": "Sealed specimen vessel", "fixed": False, "location": "bench:main", "open": False},
    "specimen:alpha": {"kind": "specimen", "name": "Unclassified specimen", "fixed": False, "location": "container:specimen"},
    "instrument:clock": {"kind": "clock", "name": "Experiment clock", "fixed": True, "location": "bench:main", "ticks": 0},
    "notebook:primary": {"kind": "notebook", "name": "Research notebook", "fixed": True, "location": "bench:main", "entries": []},
}

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

MANIFEST_DIGEST = digest(MANIFEST)

class LabError(ValueError):
    """A command failed validation and must not alter committed history."""

class Conflict(LabError):
    """Optimistic preconditions or world/epoch do not match."""

def initial_state() -> dict:
    result = copy.deepcopy(MANIFEST)
    for value in result.values():
        value["revision"] = 0
    return result

def affected_ids(action: dict) -> set[str]:
    operation = action.get("op")
    if operation in {"open", "close", "move"}:
        ids = {action.get("object_id")}
        if operation == "move":
            ids.add(action.get("to_id"))
        return ids
    if operation == "advance_clock":
        return {"instrument:clock"}
    if operation == "note":
        return {"notebook:primary"}
    raise LabError("Unknown laboratory operation")

def apply(state: dict, action: dict, revision: int) -> dict:
    if not isinstance(action, dict) or not isinstance(revision, int) or revision < 1:
        raise LabError("Invalid action or revision")
    # A closed grammar is essential. Do not permit arbitrary object/property patches.
    op = action.get("op")
    expected_fields = {
        "move": {"op", "object_id", "to_id"},
        "open": {"op", "object_id"},
        "close": {"op", "object_id"},
        "advance_clock": {"op", "ticks"},
        "note": {"op", "text"},
    }
    if op not in expected_fields or set(action) != expected_fields[op]:
        raise LabError("Unexpected or missing action fields")
    result = copy.deepcopy(state)
    if op in {"open", "close"}:
        oid = action["object_id"]
        if not isinstance(oid, str) or oid not in result or result[oid]["kind"] != "container":
            raise LabError("Only known containers can be opened or closed")
        desired = op == "open"
        if result[oid]["open"] == desired:
            raise LabError("Container is already in the requested state")
        result[oid]["open"] = desired
        result[oid]["revision"] = revision
    elif op == "move":
        oid, dest = action["object_id"], action["to_id"]
        if not isinstance(oid, str) or not isinstance(dest, str) or oid not in result or dest not in result:
            raise LabError("Unknown source or destination")
        obj, target = result[oid], result[dest]
        if obj["fixed"] or oid == dest:
            raise LabError("Cannot move fixed objects or move objects into themselves")
        if target["kind"] not in {"room", "surface", "container"}:
            raise LabError("Not a valid receiving location")
        if target["kind"] == "container" and not target["open"]:
            raise LabError("Destination container is closed")
        if obj["location"] == dest:
            raise LabError("Object is already at this location")
        # No object may become its own ancestor.
        cursor = dest
        visited = set()
        while cursor is not None:
            if cursor == oid or cursor in visited:
                raise LabError("Containment cycle")
            visited.add(cursor)
            cursor = result[cursor]["location"]
        obj["location"] = dest
        obj["revision"] = revision
    elif op == "advance_clock":
        ticks = action["ticks"]
        if type(ticks) is not int or not 1 <= ticks <= 10000:
            raise LabError("ticks must be an integer from 1 to 10000")
        result["instrument:clock"]["ticks"] += ticks
        result["instrument:clock"]["revision"] = revision
    else:
        text = action["text"]
        if not isinstance(text, str) or not 1 <= len(text) <= 2000 or any(ord(c) < 32 and c not in "\n\t" for c in text):
            raise LabError("Invalid notebook text")
        result["notebook:primary"]["entries"].append({"text": text, "revision": revision})
        result["notebook:primary"]["revision"] = revision
    return result
