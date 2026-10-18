"""Unified voluntary action/receipt interface for Pretorius's existing home.

This is an opt-in trusted transport, NOT a new material reducer, planner,
scheduler, brain, memory store, or action ranking system. It combines the
existing truthful home affordances with source-backed, position-checked book
reading/bookmark operations. All persistent effects remain in their original
single SQLite Laboratory source authorities.
"""
from __future__ import annotations

import json

from .home_affordances import HomeAffordances
from .book_library import BookLibrary
from .physics import Conflict, LabError, digest
from .habitat_v2 import SpatialHabitat
from .embodied_access import SUBJECT_ID
from .book_custody import exists as custody_exists, effective_objects, _station_for_anchor
from .physical_affordances import profile_at, check_actor_reach
from .rhythm_gate import require as require_conditions

RULES = "pretorius-voluntary-action-port/1"
_BOOK_OPS = ("open", "read", "turn", "mark", "open_mark", "unmark", "close")
_RECEIPTS = {
    "walk": ("embodied_events", "envelope"),
    "open": ("domestic_events", "envelope"),
    "close": ("domestic_events", "envelope"),
    "take": ("domestic_events", "envelope"),
    "put": ("domestic_events", "envelope"),
    "brew_tea": ("rhythm_events", "envelope"),
    "prepare_meal": ("rhythm_events", "envelope"),
    "eat": ("rhythm_events", "envelope"),
    "rest": ("rhythm_events", "envelope"),
    "sleep": ("rhythm_events", "envelope"),
    "clean": ("rhythm_events", "envelope"),
    "experiment": ("rhythm_events", "envelope"),
    "repair": ("rhythm_events", "envelope"),
    "light": ("rhythm_events", "envelope"),
    "extinguish": ("rhythm_events", "envelope"),
    "discard_meal": ("rhythm_events", "envelope"),
    "write_paper": ("rhythm_events", "envelope"),
    "read_paper": ("rhythm_events", "envelope"),
    "book": ("books_events", "payload"),
}


def _source_table(command):
    if command.startswith("material:"):
        return "botanical_events", "envelope"
    if command.startswith("arrange:"):
        return "arrangement_events", "envelope"
    if command not in _RECEIPTS:
        raise LabError("Unsupported source receipt domain")
    return _RECEIPTS[command]


class LivingActionPort:
    """Unranked multi-domain offers with live-state stale-token rejection."""

    def __init__(self, habitat):
        self.habitat = habitat
        self.home = HomeAffordances(habitat)

    def _books(self):
        """Read ONLY locally reachable books, using existing book access rules."""
        with self.habitat._open() as db:
            tables = {
                t[0] for t in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
            if "books_meta" not in tables:
                return [], {"installed": False}
        catalog = BookLibrary(self.habitat).catalog()
        with self.habitat._open() as db:
            world = SpatialHabitat._metadata(db)
            bookmeta = {k: json.loads(v) for k, v in db.execute(
                "SELECT key,value FROM books_meta")}
            body = {k: json.loads(v) for k, v in db.execute(
                "SELECT key,value FROM embodied_meta")}
            if custody_exists(db):
                locations = effective_objects(db)
                custody = {k: json.loads(v) for k, v in db.execute(
                    "SELECT key,value FROM custody_meta")}
                custody_stamp = (custody["revision"], custody["head_hash"])
            else:
                locations = world["state"]["objects"]
                custody_stamp = None
            profile = profile_at(db, world)
            offers = []
            for book_id, record in sorted(catalog.items()):
                obj = locations.get(book_id)
                if not obj or obj["kind"] != "book":
                    continue
                loc, holder = obj.get("anchor_id"), obj.get("held_by")
                if loc is None:
                    if holder != SUBJECT_ID:
                        continue
                elif _station_for_anchor(world["state"]["anchors"], loc) != body["station"]:
                    continue
                try:
                    if loc is not None:
                        check_actor_reach(profile, book_id, loc, world, lifting=False)
                    require_conditions(db, body["station"], "book_read")
                    readable = True
                except (Conflict, LabError):
                    readable = False
                # Closing and removing bookmarks do not require enough
                # light to read. Source BookLibrary decides final legality.
                possible = []
                if record["opened"]:
                    if readable:
                        possible.append(("read", {}, "read the current page"))
                        if record["page_if_open"] > 1:
                            possible.append(("turn", {"direction": -1},
                                             "turn one page backward"))
                        if record["page_if_open"] < record["page_count"]:
                            possible.append(("turn", {"direction": 1},
                                             "turn one page forward"))
                        if len(record["bookmarks"]) < 100:
                            possible.append(("mark", {}, "place a bookmark of my choosing"))
                    possible.append(("close", {}, "close this book"))
                else:
                    if readable:
                        possible.append(("open", {}, "open this book at the beginning"))
                        for marker in sorted(record["bookmarks"]):
                            possible.append(("open_mark", {"bookmark_id": marker},
                                             "open at my bookmark " + marker))
                for marker in sorted(record["bookmarks"]):
                    possible.append(("unmark", {"bookmark_id": marker},
                                     "remove bookmark " + marker))
                for op, args, wording in possible:
                    offers.append({
                        "command": "book",
                        "args": {"book_id": book_id, "operation": op, **args},
                        "requires_my_own_words": False,
                        "requires_bookmark_id": op == "mark",
                        "description": "I could " + wording + " in " +
                                       record["title"] + ".",
                    })
            stamp = {
                "installed": True, "revision": bookmeta["revision"],
                "head_hash": bookmeta["head_hash"],
                "physical_revision": world["revision"],
                "physical_head": world["head_hash"],
                "body_revision": body["revision"],
                "body_head": body["head_hash"],
                "custody": custody_stamp,
            }
            return offers, stamp

    def discover(self):
        """First-person possibilities; exact source commands only in host plane."""
        # A real embodied look appends a perception receipt, increasing
        # bodily event revision. Obtain that source-bound observation FIRST,
        # before freezing the body/book action-offer snapshot.
        seen = self.home.subject.observe()
        base = self.home.discover()
        books, book_stamp = self._books()
        stamp = digest({
            "rules": RULES, "home": base["world_stamp"], "books": book_stamp
        })
        offers = []
        for original in base["offers"]:
            offers.append({k: v for k, v in original.items()
                           if k != "offer_id"} |
                          {"requires_bookmark_id": False})
        offers.extend(books)
        # A single global stamp invalidates previously offered book/furniture
        # actions whenever an unrelated physical source changes.
        ids = set()
        for offer in offers:
            token = digest({
                "state": stamp, "command": offer["command"],
                "args": offer["args"],
                "needs_text": offer["requires_my_own_words"],
                "needs_bookmark": offer["requires_bookmark_id"],
            })
            if token in ids:
                raise Conflict("Duplicate source action capability")
            ids.add(token)
            offer["offer_id"] = token
        # No new brain/prospective memory data: readable opportunities are
        # merely another verified part of the already presented home.
        extra = " ".join(entry["description"] for entry in books)
        # Existing SubjectPort is the sole truthful local scene view.
        # A list of possibilities alone cannot tell the Doctor WHERE the
        # chair actually ended up yesterday, so include lived surroundings.
        text = seen["inner"] + " " + base["subject_frame"]["inner"]
        if extra:
            text += " " + extra
        frame = {"inner": text, "spoken_aloud": None}
        # If the book changes while enumerating, do not present an incoherent
        # offer. Home itself already verifies its own initial/final stamp.
        _, end = self._books()
        if end != book_stamp:
            raise Conflict("Book world changed while I considered my options")
        return {"rules": RULES, "world_stamp": stamp,
                "subject_frame": frame, "offers": offers}

    def _receipt(self, command, event_id):
        table, field = _source_table(command)
        with self.habitat._open() as db:
            row = db.execute(
                "SELECT " + field + ",event_hash FROM " + table +
                " WHERE event_id=?", (event_id,)).fetchone()
        if row is None:
            raise Conflict("No durable source event for claimed completed action")
        payload, hash_ = json.loads(row[0]), row[1]
        if digest(payload) != hash_:
            raise Conflict("Source event hash mismatch")
        # Full source owners are the only verifiers, not this adapter.
        if command == "book":
            BookLibrary(self.habitat).verify()
        elif command.startswith("material:"):
            from .material_objects import MaterialObjects
            MaterialObjects(self.habitat).verify()
        elif command.startswith("arrange:"):
            from .home_arrangement import HomeArrangements
            HomeArrangements(self.habitat).verify()
        elif table == "rhythm_events":
            self.home.rhythm.verify()
        elif table == "embodied_events":
            # A walk's stable external ID names its genuine body-motion
            # receipt. HomeLife independently creates the domestic motion
            # consequence under motion:<body_hash_prefix>, not that ID.
            self.home.body.verify()
            self.home.home.verify()
            with self.habitat._open() as db:
                companion = db.execute(
                    "SELECT envelope,event_hash FROM domestic_events WHERE event_id=?",
                    ("motion:" + hash_[:32],)).fetchone()
            if (companion is None or
                    digest(json.loads(companion[0])) != companion[1]):
                raise Conflict("Movement has no verified household consequence")
        else:
            self.home.home.verify()
        return {"source_table": table, "source_event_id": event_id,
                "source_event_hash": hash_, "verified": True}

    def act(self, offer_id, *, event_id, text=None, bookmark_id=None):
        """Execute one currently offered action and return material proof."""
        if (type(offer_id) is not str or type(event_id) is not str
                or not 1 <= len(event_id) <= 80):
            raise LabError("A live offer and durable action ID are required")
        snapshot = self.discover()
        offer = next((o for o in snapshot["offers"]
                      if o["offer_id"] == offer_id), None)
        if offer is None:
            raise Conflict("The proposed action is stale or was never offered")
        if offer["requires_my_own_words"] != (text is not None):
            raise LabError("Authored words are required only for genuine writing")
        if offer["requires_bookmark_id"] != (bookmark_id is not None):
            raise LabError("A new bookmark needs its subject-chosen identifier")
        if offer["command"] == "book":
            args = dict(offer["args"])
            if bookmark_id is not None:
                args["bookmark_id"] = bookmark_id
            frame = self.home.subject.act("book", event_id=event_id, **args)
        else:
            # The original home catalog retains the true base capability
            # token. The outer token is only an additional source guard.
            base = self.home.discover()
            original = next(
                (o for o in base["offers"] if
                 o["command"] == offer["command"] and
                 o["args"] == offer["args"] and
                 o["requires_my_own_words"] ==
                 offer["requires_my_own_words"]), None)
            if original is None:
                raise Conflict("Underlying physical offer disappeared")
            frame = self.home.act(original["offer_id"],
                                  event_id=event_id, text=text)
        if set(frame) != {"inner", "spoken_aloud"} or not frame["inner"].startswith("I "):
            raise Conflict("World action did not return a first-person experience")
        return {"subject": frame, "command": offer["command"],
                "args": dict(offer["args"]), "source":
                self._receipt(offer["command"], event_id)}
