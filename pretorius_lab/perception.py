"""Deterministic subject-facing view of the external research laboratory.

This is a local adapter boundary, not a claim that a subject witnessed an event.
No private notebook content or hidden container contents are disclosed.
"""
from __future__ import annotations

from .physics import apply, digest, LabError


def _visible(state: dict, object_id: str) -> bool:
    """An object is visible if none of its ancestors is a closed vessel."""
    cursor = state[object_id]["location"]
    seen = {object_id}
    while cursor is not None:
        if cursor not in state or cursor in seen:
            raise LabError("Invalid containment tree")
        seen.add(cursor)
        parent = state[cursor]
        if parent["kind"] == "container" and not parent["open"]:
            return False
        cursor = parent["location"]
    return True


def observe(laboratory) -> dict:
    """Return host-checked source-scoped observation, never cognition or memory."""
    proof = laboratory.verify()
    status = laboratory.status()
    state = status["objects"]
    visible = {
        key: {
            field: value[field]
            for field in ("kind", "name", "location", "open", "ticks")
            if field in value
        }
        for key, value in sorted(state.items()) if _visible(state, key)
    }
    candidates = [{"op": "advance_clock", "ticks": 1}]
    for key, obj in visible.items():
        if obj["kind"] == "container":
            candidates.append({
                "op": "close" if obj["open"] else "open",
                "object_id": key,
            })
        if not state[key]["fixed"]:
            for dest, receiving in visible.items():
                if dest == key or receiving["kind"] not in {
                    "room", "surface", "container"
                }:
                    continue
                action = {"op": "move", "object_id": key, "to_id": dest}
                try:
                    apply(state, action, proof["revision"] + 1)
                    candidates.append(action)
                except LabError:
                    continue
    payload = {
        "authority": "local_research_host",
        "observation_class": "source_attested_lab_view_not_lived_memory",
        "visibility": "research_private",
        "lab_id": proof["lab_id"],
        "world_epoch": proof["world_epoch"],
        "revision": proof["revision"],
        "event_cursor": proof["head_hash"],
        "state_digest": proof["state_digest"],
        "visible_objects": visible,
        "eligible_action_examples": candidates,
        "notebook_contents_included": False,
    }
    return {**payload, "observation_digest": digest(payload)}
