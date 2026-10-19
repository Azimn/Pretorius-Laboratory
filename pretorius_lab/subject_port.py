"""Strict first-person Laboratory bridge for one existing embodied Pretorius.

No LLM is hosted here. This module produces a SOURCE-BASED experiential frame
for the eventual Doctor Lives input. It cannot issue operator-only commands,
read private engineering audits, open the Village, or create autobiographical
memories. Numeric environmental state stays below this boundary.
"""
from __future__ import annotations

import json
import re

from .daily_rhythm import DailyRhythm, VISIBLE_RULES, PAPER_RULES
from .embodied_access import EmbodiedAccess
from .habitat_v2 import SpatialHabitat
from .home_life import HomeLife
from .physics import Conflict, LabError


def _frame(text, spoken=None):
    if not isinstance(text, str) or not re.match(r"^(?:I\b|My\b|Mine\b|Me\b)", text.strip()):
        raise Conflict("Subject experience must be substantial first-person natural language")
    if spoken is not None and (not isinstance(spoken, str) or not spoken.strip()):
        raise Conflict("Malformed out-loud response")
    return {"inner": text, "spoken_aloud": spoken}


def _append(*parts):
    return " ".join(v.strip() for v in parts if isinstance(v, str) and v.strip())


def _from_experience(value):
    if set(value) != {"inner", "spoken_aloud"}:
        raise Conflict("Unexpected hidden fields in experience")
    return _frame(value["inner"], value["spoken_aloud"])


class SubjectPort:
    """Preferred restricted entrypoint for an unchanged Laboratory subject.

    The body and home are mandatory; the opt-in daily rhythm is mandatory.
    All detailed low-level actions still enforce their own physical rules.
    This adapter does NOT supply a model, scheduled cognition or an identity.
    """

    def __init__(self, habitat: SpatialHabitat):
        self.habitat = habitat
        self.home = HomeLife(habitat)
        self.rhythm = DailyRhythm(habitat)
        self.embodied = EmbodiedAccess(habitat)

    def verify(self):
        """ENGINEER ONLY; callers must never pass this dict to Pretorius."""
        return self.rhythm.verify()

    def _station(self):
        return self.embodied.verify()["station"]

    def observe(self):
        """Natural-language perception; never an omniscient geometry dump."""
        self.verify()
        from .rhythm_gate import lit
        station = self._station()
        # The underlying lower-layer gate may reject detailed inspection in
        # darkness. The first-person rhythm description remains accessible.
        first = self.rhythm.look()
        parts = [first["inner"]]
        from .daily_rhythm import available_delivery_day
        with self.habitat._open() as db:
            delivery_day = available_delivery_day(db, station)
        if delivery_day is not None:
            parts.append(
                "I notice the ordinary morning provisions by the hall entry, "
                "left through my standing arrangement with the local supplier.")
        with self.habitat._open() as db:
            bright = lit(db, station)
        if bright:
            # v4: change only the rendering of source-backed, visible objects.
            # Both authoritative state owners remain unchanged.
            with self.habitat._open() as db:
                row = db.execute(
                    "SELECT value FROM rhythm_meta WHERE key='rules'").fetchone()
                if row is None:
                    raise Conflict("No current rhythm authority")
                visual_portions = json.loads(row[0]) in (VISIBLE_RULES, PAPER_RULES)
            if visual_portions:
                from .home_life import _look as home_description
                from .provision_appearance import provision_names
                self.home.verify()
                supplies = self.rhythm.audit_state()  # trusted host only
                physical = self.home.audit_state()  # trusted host only
                parts.append(home_description(
                    physical, station,
                    provision_names=provision_names(supplies)))
            else:
                household = self.home.look()
                parts.append(household["inner"])
            # This local observation includes only nearby physical objects,
            # not offstage items or hidden numbers.
            scene = self.embodied.look()["offered_payload"]
            names = [obj["appearance"] for obj in scene["nearby_objects"]]
            if names:
                parts.append("I can make out " + ", ".join(sorted(names)) + ".")
            carrying = [obj["appearance"] for obj in scene["held_objects"]]
            if carrying:
                parts.append("I am holding " + ", ".join(sorted(carrying)) + ".")
        from .material_objects import MaterialObjects, exists as materials_exist
        with self.habitat._open() as db:
            material_present = materials_exist(db)
        if material_present:
            material_view = MaterialObjects(self.habitat).observe()
            if material_view["inner"].startswith("I can see "):
                parts.append(material_view["inner"])
        from .home_arrangement import HomeArrangements, exists as arrangements_exist
        with self.habitat._open() as db:
            has_arrangements = arrangements_exist(db)
        if has_arrangements:
            seen_room = HomeArrangements(self.habitat).observe()
            if seen_room["inner"].startswith("I can see "):
                parts.append(seen_room["inner"])
        # A move during multi-ledger inspection is not a coherent one-frame
        # viewpoint. Fail closed; callers can retry from the new position.
        if self._station() != station:
            raise Conflict("The body moved during sensory assembly")
        return _frame(_append(*parts))

    def act(self, command: str, *, event_id: str | None = None, **args):
        """Return *only* first-person inner text and optional audible words."""
        self.verify()
        if command == "look":
            if args or event_id is not None:
                # Observation is built from several separately sourced
                # local look receipts; no synthetic cross-ledger event ID.
                raise LabError("Combined look does not accept a synthetic receipt ID")
            return self.observe()
        if command == "walk":
            if set(args) != {"station"}:
                raise LabError("Walking requires an adjacent named station")
            happened = self.home.walk(args["station"], event_id=event_id)
            # Include real physical consequence, then present current bodily
            # regulation to the subject as a separate perspectival impression.
            current = self.rhythm.look()
            return _frame(_append(happened["inner"], current["inner"]),
                          happened["spoken_aloud"])
        if command in {"open", "close"}:
            if set(args) != {"container"}:
                raise LabError("Choose physical furniture")
            return _from_experience(getattr(self.home, command)(
                args["container"], event_id=event_id))
        if command == "take":
            if set(args) != {"item"}:
                raise LabError("Choose an accessible domestic item")
            return _from_experience(self.home.take(args["item"], event_id=event_id))
        if command == "put":
            if set(args) != {"item", "container"}:
                raise LabError("Specify a carried item and a local container")
            return _from_experience(self.home.put(
                args["item"], args["container"], event_id=event_id))
        if command == "shift_stool":
            if set(args) != {"obstructs_path"} or type(args["obstructs_path"]) is not bool:
                raise LabError("Provide the actual intended stool position")
            return _from_experience(self.home.shift_stool(
                obstructs_path=args["obstructs_path"], event_id=event_id))
        if command in {
            "advance", "light", "extinguish", "prepare_meal", "eat",
            "brew_tea", "sleep", "rest", "clean", "experiment", "repair",
            "discard_meal", "write_paper", "read_paper",
            "drink_water", "draw_water", "accept_delivery", "use_washroom",
        }:
            outcome = self.rhythm.act(command, event_id=event_id, **args)
            if command == "advance":
                # Older rhythm receipts legitimately begin "Time passes".
                # Keep their replay stable; adapt the *new subject surface*.
                return _frame("I notice time passing. " + outcome["inner"],
                              outcome["spoken_aloud"])
            return _from_experience(outcome)
        if command.startswith("project:"):
            from .personal_projects import PersonalProjects
            return _from_experience(PersonalProjects(self.habitat).act(
                command.partition(":")[2], event_id=event_id, **args))
        if command.startswith("arrange:"):
            from .home_arrangement import HomeArrangements
            return _from_experience(HomeArrangements(self.habitat).act(
                command.partition(":")[2], event_id=event_id, **args))
        if command.startswith("material:"):
            from .material_objects import MaterialObjects
            op = command.partition(":")[2]
            return _from_experience(MaterialObjects(self.habitat).act(
                op, event_id=event_id, **args))
        if command == "book":
            required = {"book_id", "operation"}
            if not required <= set(args) or set(args) - (
                    required | {"direction", "bookmark_id"}):
                raise LabError("Specify the actual book and reading action")
            action = args["operation"]
            book = self.embodied.book(
                args["book_id"], action, direction=args.get("direction"),
                bookmark_id=args.get("bookmark_id"), event_id=event_id)
            if action == "read":
                # All title/page text is from the installed source edition
                # and physical read receipt; never a model-invented page.
                return _frame(
                    "I read a page of " + book["title"] + ". The words before me read: "
                    + book["page_text"]
                )
            labels = {
                "open": "open", "close": "close", "turn": "turn a page in",
                "mark": "mark a page in", "unmark": "remove a bookmark from",
                "open_mark": "open at a bookmark",
            }
            if action not in labels:
                raise LabError("Unknown book operation")
            return _frame("I " + labels[action] + " the volume.")
        if command == "measure":
            if set(args) != {"instrument", "object_id", "quantity"}:
                raise LabError("A measurement requires an instrument, item and quantity")
            receipt = self.embodied.measure(
                args["instrument"], args["object_id"], args["quantity"],
                event_id=event_id)
            seen = receipt["observation"]
            units = {"g": "grams", "mm": "millimetres"}
            kinds = {"mass_g": "mass", "width_mm": "width",
                     "height_mm": "height", "depth_mm": "depth"}
            unit = units.get(seen["unit"])
            quantity = kinds.get(seen["quantity"])
            if unit is None or quantity is None:
                raise Conflict("Unknown displayed instrument quantity")
            return _frame(
                f"I use the instrument and read a {quantity} of about "
                f"{seen['value']} {unit}."
            )
        if command == "take_book":
            if set(args) != {"book_id"}:
                raise LabError("Take one actual book")
            self.embodied.take(args["book_id"], event_id=event_id)
            return _frame("I lift the volume into my hands.")
        if command == "put_book":
            if set(args) != {"book_id", "anchor_id"}:
                raise LabError("Place the held book at a real reachable location")
            self.embodied.put(args["book_id"], args["anchor_id"], event_id=event_id)
            return _frame("I set the volume down carefully.")
        raise LabError("Action is not available to this embodied subject")
