"""One opt-in, source-backed activity surface for Pretorius's lived home.

This does NOT create another clock, object store, brain or physical reducer.
It composes existing HomeAffordances with BookLibrary's actual physical pages,
and returns one stable offer/receipt contract for all currently supported
activities. The Doctor receives ONLY first-person natural-language text.
The trusted host receives action IDs/args and material event proof.
"""
from __future__ import annotations

import json
import re

from .book_library import BookLibrary
from .home_affordances import HomeAffordances
from .physics import Conflict, LabError, digest
from .subject_port import SubjectPort

RULES = "pretorius-unified-home-actions/1"
_EVENT_ID = re.compile(r"[A-Za-z0-9_-]{1,80}\Z")
_BOOK_ACTS = {"open", "close", "read", "turn", "mark", "unmark", "open_mark"}
_RHYTHM = {"advance", "light", "extinguish", "prepare_meal", "eat",
           "brew_tea", "sleep", "rest", "clean", "experiment", "repair",
           "discard_meal", "write_paper", "read_paper",
           "drink_water", "accept_delivery", "use_washroom"}


def _event_table(command):
    if command.startswith("project:"):
        return "project_events"
    if command == "book":
        return "books_events"
    if command == "walk":
        return "embodied_events"
    if command.startswith("material:"):
        return "botanical_events"
    if command.startswith("arrange:"):
        return "arrangement_events"
    if command in {"open", "close", "take", "put", "shift_stool"}:
        return "domestic_events"
    if command in _RHYTHM:
        return "rhythm_events"
    raise LabError("No authenticated material domain for this action")


def _book_details(db):
    """Trusted state only; never expose raw page or bookmark metadata as text."""
    present = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='books_meta'"
    ).fetchone()
    if not present:
        return None
    book = {k: json.loads(v) for k, v in db.execute(
        "SELECT key,value FROM books_meta")}
    return {
        "revision": book["revision"], "head_hash": book["head_hash"],
        "books": book["books"],
    }


class UnifiedHomeActions:
    """Open-world invitation without an agenda or fabricated outcomes."""

    def __init__(self, habitat):
        self.habitat = habitat
        self.home = HomeAffordances(habitat)
        self.subject = SubjectPort(habitat)

    def _catalog(self):
        found = self.home.discover()
        # Confirm the full authored book/source snapshot is authentic.
        with self.habitat._open() as db:
            books = _book_details(db)
        listings = BookLibrary(self.habitat).catalog() if books is not None else {}
        # EmbodiedAccess is the established physical visibility boundary.
        scene = self.subject.embodied.look()["offered_payload"]
        local_ids = {
            x["object_id"] for x in scene["nearby_objects"] + scene["held_objects"]
        }
        with self.habitat._open() as db:
            custody = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='custody_meta'"
            ).fetchone()
            custody_state = (
                {k: json.loads(v) for k, v in db.execute(
                    "SELECT key,value FROM custody_meta")}
                if custody else None)
        # Being visible near a volume is not always enough to touch/read it:
        # high-shelf mechanical reach, darkness and fatigue still apply.
        from .physical_affordances import profile_at, check_actor_reach
        from .book_custody import effective_objects
        from .rhythm_gate import require as require_daily_conditions
        from .habitat_v2 import SpatialHabitat
        from .physics import Conflict
        station = self.subject.embodied.verify()["station"]
        with self.habitat._open() as db:
            host = SpatialHabitat._metadata(db)
            mechanical = profile_at(db, host)
            objects = effective_objects(db)
            try:
                require_daily_conditions(db, station, "book_read")
            except (Conflict, LabError):
                local_ids.clear()
            else:
                for book_id in list(local_ids):
                    if book_id not in listings:
                        continue
                    item = objects.get(book_id)
                    if item is None:
                        local_ids.discard(book_id)
                        continue
                    anchor = item["anchor_id"]
                    if anchor is not None:
                        try:
                            check_actor_reach(mechanical, book_id, anchor,
                                              host, lifting=False)
                        except (Conflict, LabError):
                            local_ids.discard(book_id)
        return found, books, listings, local_ids, custody_state

    def discover(self):
        """Return unranked opportunities plus independently grounded subject text."""
        base, books, catalog, nearby, custody = self._catalog()
        from .personal_projects import PersonalProjects, exists as projects_exist
        with self.habitat._open() as db:
            projects_present = projects_exist(db)
        projects = (PersonalProjects(self.habitat).audit_state()
                    if projects_present else None)
        stamp = digest({
            "home_stamp": base["world_stamp"],
            "books": books, "custody": custody,
            "book_locality": sorted(nearby), "projects": projects,
        })
        offered = []

        def add(command, args, desc, *, free_text=False):
            if not desc.startswith("I could "):
                raise AssertionError("Only natural first-person opportunity prose")
            oid = digest({"stamp": stamp, "command": command, "args": args})
            offered.append({
                "offer_id": oid, "command": command, "args": args,
                "requires_my_own_words": free_text, "description": desc,
                "source_domain": _event_table(command),
            })

        for item in base["offers"]:
            add(item["command"], dict(item["args"]), item["description"],
                free_text=item["requires_my_own_words"])

        for book_id, record in sorted(catalog.items()):
            if book_id not in nearby:
                continue
            title = record["title"]
            prefix = {"book_id": book_id}
            def bookop(action, desc, **kwargs):
                add("book", {**prefix, "operation": action, **kwargs}, desc)

            if record["opened"]:
                bookop("read", "I could read the present page of " + title + ".")
                if record["page_if_open"] > 1:
                    bookop("turn", "I could turn back a page in " + title + ".",
                           direction=-1)
                if record["page_if_open"] < record["page_count"]:
                    bookop("turn", "I could turn forward a page in " + title + ".",
                           direction=1)
                if len(record["bookmarks"]) < 100:
                    n = 1
                    while f"page-flag-{n}" in record["bookmarks"]:
                        n += 1
                    bookop("mark", "I could leave a bookmark in " + title + ".",
                           bookmark_id=f"page-flag-{n}")
                bookop("close", "I could close " + title + ".")
            else:
                bookop("open", "I could open " + title + ".")
                for mark in sorted(record["bookmarks"]):
                    bookop("open_mark", "I could return to a marked page in " +
                           title + ".", bookmark_id=mark)
        if projects_present:
            for option in PersonalProjects(self.habitat).current_offers():
                add("project:" + option["op"], dict(option["args"]),
                    "I could " + option["description"] + ".",
                    free_text=option["free_text"])
        # The apparent opportunities must be descriptive, not obligations.
        fragment = " ".join(o["description"] for o in offered)
        frame = {
            "inner": (base["subject_frame"]["inner"] +
                      (" Other things I could do: " + " ".join(
                          o["description"] for o in offered
                          if o["command"] == "book")
                       if any(o["command"] == "book" for o in offered) else "")),
            "spoken_aloud": None,
        }
        if not frame["inner"].startswith("I "):
            raise Conflict("The Doctor was given an invalid subject perspective")
        # Do not mint usable tokens against a changed material source.
        next_base, next_books, _, next_nearby, next_custody = self._catalog()
        next_projects = (PersonalProjects(self.habitat).audit_state()
                         if projects_present else None)
        other = digest({
            "home_stamp": next_base["world_stamp"],
            "books": next_books, "custody": next_custody,
            "book_locality": sorted(next_nearby), "projects": next_projects,
        })
        if other != stamp:
            raise Conflict("World changed during unified action discovery")
        return {"schema": RULES, "subject_frame": frame, "world_stamp": stamp,
                "offers": offered}

    def execute(self, offer_id, *, event_id, text=None):
        """Commit exactly one still-live real-world offer and return its receipt."""
        if type(offer_id) is not str or not re.fullmatch(r"[0-9a-f]{64}", offer_id):
            raise LabError("Offer identifier must be issued by the source world")
        if type(event_id) is not str or not _EVENT_ID.fullmatch(event_id):
            raise LabError("Stable, bounded material event ID required")
        current = self.discover()
        offer = next((entry for entry in current["offers"]
                      if entry["offer_id"] == offer_id), None)
        if offer is None:
            raise Conflict("The offered activity is no longer possible")
        args = dict(offer["args"])
        if offer["requires_my_own_words"]:
            if type(text) is not str:
                raise LabError("The subject must actually supply their written words")
            args["text"] = text
        elif text is not None:
            raise LabError("An unrelated command cannot invent written content")
        # SubjectPort is the ONLY executor here. It delegates to the existing
        # physical book, paper, flower, furniture, and clock authorities.
        frame = self.subject.act(offer["command"], event_id=event_id, **args)
        table = offer["source_domain"]
        with self.habitat._open() as db:
            row = db.execute(
                "SELECT event_hash FROM " + table + " WHERE event_id=?",
                (event_id,)).fetchone()
        if row is None:
            raise Conflict("No historical world receipt for accepted action")
        # Actual event history must still replay through its own authority.
        if table == "books_events":
            BookLibrary(self.habitat).verify()
        elif table == "botanical_events":
            from .material_objects import MaterialObjects
            MaterialObjects(self.habitat).verify()
        elif table == "project_events":
            from .personal_projects import PersonalProjects
            PersonalProjects(self.habitat).verify()
        elif table == "arrangement_events":
            from .home_arrangement import HomeArrangements
            HomeArrangements(self.habitat).verify()
        else:
            self.subject.verify()
        if (type(frame) is not dict or set(frame) !=
                {"inner", "spoken_aloud"} or
                not frame["inner"].startswith(("I ", "My "))):
            raise Conflict("No authentic first-person outcome of world action")
        return {
            "status": "committed", "subject": frame, "source_event_id": event_id,
            "source_table": table, "source_event_hash": row[0],
            "command": offer["command"], "args": args,
        }
