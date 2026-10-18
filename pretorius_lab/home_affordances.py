"""Discover currently possible activities in Pretorius's *real* home.

The world remains the one authoritative Laboratory SQLite database.
A host can inspect executable command specs; the Doctor can experience only
the first-person natural-language possibilities. No activity is chosen here,
and this never inserts preferences, synthetic memories or free resources.

This module is an opt-in prototype over the existing v5 physical-paper world.
It does not add generic object creation, historical migration, or an agent.
"""
from __future__ import annotations

from .daily_rhythm import (
    DailyRhythm, PAPER_RULES, _stock_access, _writing_access,
    _can_see, transition,
)
from .embodied_access import EmbodiedAccess, STATIONS
from .home_life import HomeLife, ROOM_LABELS, _apply
from .physics import Conflict, LabError, digest
from .subject_port import SubjectPort

_DOMESTIC_OPERATIONS = ("open", "close", "take", "put")
_RHYTHM_OPERATIONS = {
    "brew_tea": "brew a cup of tea",
    "prepare_meal": "prepare a simple meal",
    "eat": "eat the meal I have prepared",
    "rest": "rest for a while",
    "sleep": "go to sleep",
    "clean": "tidy this room",
    "experiment": "work on an experiment",
    "repair": "repair the apparatus",
    "discard_meal": "discard the spoiled meal",
    "light": "light the room's lamp",
    "extinguish": "put out the lamp",
}


class HomeAffordances:
    """Observation-only planner/executor with per-world, per-state offer stamps.

    There is NO AI preference ranking here: every currently legal choice is
    presented without recommendation or quota. Hidden engineering counts stay
    out of the natural-language first-person experience.
    """

    def __init__(self, habitat):
        self.subject = SubjectPort(habitat)
        self.home = HomeLife(habitat)
        self.rhythm = DailyRhythm(habitat)
        self.body = EmbodiedAccess(habitat)

    def _snapshot(self):
        self.subject.verify()
        with self.subject.habitat._open() as db:
            row = db.execute(
                "SELECT value FROM rhythm_meta WHERE key='rules'").fetchone()
            if row is None:
                raise LabError("Household rhythm was not initialized")
            import json
            rules = json.loads(row[0])
        # This prototype is intentionally limited to the existing v5 world.
        if rules != PAPER_RULES:
            raise LabError("Discoverable household prototype requires v5 physical-paper rules")
        state = self.rhythm.audit_state()
        material = self.home.audit_state()
        station = self.body.verify()["station"]
        from .material_objects import MaterialObjects, exists as materials_exist
        with self.subject.habitat._open() as db:
            has_materials = materials_exist(db)
        new_objects = (MaterialObjects(self.subject.habitat).audit_state()
                       if has_materials else None)
        from .home_arrangement import HomeArrangements, exists as arrangement_exists
        with self.subject.habitat._open() as db:
            has_room_changes = arrangement_exists(db)
        arranged = (HomeArrangements(self.subject.habitat).audit_state()
                    if has_room_changes else None)
        stamp = digest({
            "world_epoch": self.subject.verify()["world_epoch"],
            "rhythm": state, "material": material, "station": station,
            "rules": rules, "dynamic_objects": new_objects,
            "room_arrangements": arranged,
        })
        return state, material, station, stamp

    def discover(self):
        """Return both the trusted offer catalog and a separate subject frame."""
        state, material, station, stamp = self._snapshot()
        room = STATIONS[station][0]
        visible = _can_see(state, room)
        stock = _stock_access(material, station)
        writing = _writing_access(material, station)
        from .material_objects import MaterialObjects, exists as botanical_exists, ACTOR
        with self.subject.habitat._open() as db:
            botanical_enabled = botanical_exists(db)
        botanical_state = (MaterialObjects(self.subject.habitat).audit_state()
                           if botanical_enabled else None)
        botanical_items = botanical_state["objects"] if botanical_state else {}
        botanical_in_hand = any(
            x["parent"] == ACTOR for x in botanical_items.values())
        offers = []

        def add(command, args, description, *, free_text=False):
            if not description.startswith("I could "):
                raise AssertionError("Every proposed ability must be first-person")
            if any(record["command"] == command and
                   record["args"] == args for record in offers):
                raise AssertionError("Duplicate available activity")
            # An ID is an execution capability ONLY while the material world
            # and actor body stay exactly as they were when it was offered.
            token = digest({"world": stamp, "command": command, "args": args})
            offers.append({
                "offer_id": token, "command": command,
                "args": args, "requires_my_own_words": free_text,
                "description": description,
            })

        for next_station in STATIONS[station][1]:
            # The actual HomeLife walk reducer validates adjacency and
            # foot collision; this never invents a second floor plan.
            _apply(material, "walk", {
                "from_station": station, "to_station": next_station},
                next_station)
            next_room = STATIONS[next_station][0]
            name = ROOM_LABELS[next_room]
            add("walk", {"station": next_station},
                "I could walk toward " + name + ".")

        if visible:
            for cid, container in sorted(material["containers"].items()):
                for op in ("open", "close"):
                    try:
                        _apply(material, op, {"container": cid}, station)
                    except (Conflict, LabError):
                        continue
                    add(op, {"container": cid},
                        "I could " + op + " the " + container["name"] + ".")

            for iid, item in sorted(material["items"].items()):
                if botanical_in_hand:
                    continue
                try:
                    _apply(material, "take", {"item": iid}, station)
                except (Conflict, LabError):
                    pass
                else:
                    add("take", {"item": iid},
                        "I could pick up the " + item["name"] + ".")

            for iid, item in sorted(material["items"].items()):
                if item["held_by"] == "research-subject:pretorius":
                    for cid, container in sorted(material["containers"].items()):
                        combined = sum(
                            obj["parent"] == cid for obj in botanical_items.values())
                        combined += sum(
                            obj["container"] == cid
                            for obj in material["items"].values())
                        if combined >= container["capacity"]:
                            continue
                        try:
                            _apply(material, "put", {
                                "item": iid, "container": cid}, station)
                        except (Conflict, LabError):
                            continue
                        add("put", {"item": iid, "container": cid},
                            "I could put the " + item["name"] +
                            " in the " + container["name"] + ".")

        for op, phrase in _RHYTHM_OPERATIONS.items():
            try:
                transition(state, op, {}, station, stock_access=stock,
                           writing_access=writing)
            except (Conflict, LabError):
                continue
            add(op, {}, "I could " + phrase + ".")

        # A freeform paper offer contains no precomposed text. The sample
        # text is used ONLY for pure reducer availability testing and is
        # never executed, recorded or disclosed as the subject's own words.
        try:
            transition(state, "write_paper",
                       {"text": "A line of my choosing."}, station,
                       stock_access=stock, writing_access=writing)
        except (Conflict, LabError):
            pass
        else:
            add("write_paper", {},
                "I could write words of my own choosing on my paper.",
                free_text=True)

        for page in range(1, len(state["paper_marks"]) + 1):
            try:
                transition(state, "read_paper", {"page": page}, station,
                           stock_access=stock, writing_access=writing)
            except (Conflict, LabError):
                continue
            add("read_paper", {"page": page},
                "I could reread page " + str(page) + " of my paper.")

        # New objects use a verified material reducer, not a separate world.
        from .material_objects import MaterialObjects, exists as materials_exist
        with self.subject.habitat._open() as db:
            has_materials = materials_exist(db)
        if has_materials:
            botanical = MaterialObjects(self.subject.habitat)
            for possibility in botanical.available():
                add("material:" + possibility["op"], possibility["args"],
                    "I could " + possibility["description"] + ".",
                    free_text=possibility["free_text"])
        # Room arrangement is an optional source-replayed material change.
        # It is an opportunity, not a checklist or a prescribed objective.
        from .home_arrangement import HomeArrangements, exists as arrangement_exists
        with self.subject.habitat._open() as db:
            has_room_changes = arrangement_exists(db)
        if has_room_changes:
            for choice in HomeArrangements(self.subject.habitat).available():
                add("arrange:" + choice["op"], choice["args"],
                    "I could " + choice["description"] + ".")
        # Do not quietly grant offstage objects, knowledge or obligations.
        frame = {
            "inner": ("I am in " + ROOM_LABELS[room] +
                      ". Possibilities I can presently recognize: " +
                      (" ".join(o["description"] for o in offers)
                       if offers else "Nothing more comes readily to hand.")),
            "spoken_aloud": None,
        }
        # Read-only verification is essential: the affordance catalog
        # itself must not consume a minute, make tea, or create memories.
        _, _, _, after_stamp = self._snapshot()
        if after_stamp != stamp:
            raise Conflict("The home changed during affordance discovery")
        return {"subject_frame": frame, "world_stamp": stamp, "offers": offers}

    def act(self, offer_id: str, *, event_id: str, text: str | None = None):
        """Only accept a live offer; delegate *all* real effects to SubjectPort."""
        if type(offer_id) is not str or type(event_id) is not str:
            raise LabError("A live offered action and stable event ID are required")
        current = self.discover()
        offer = next((o for o in current["offers"]
                      if o["offer_id"] == offer_id), None)
        if offer is None:
            raise Conflict("This activity was never possible here, or the world has changed")
        arguments = dict(offer["args"])
        if offer["requires_my_own_words"]:
            if type(text) is not str:
                raise LabError("Only the subject can provide their own words")
            arguments["text"] = text
        elif text is not None:
            raise LabError("No invented extra author text for this world action")
        # All material changes use the single underlying Laboratory SQLite
        # world. The subject itself never receives host state/command metadata.
        return self.subject.act(offer["command"], event_id=event_id, **arguments)
