"""Manual ChatGPT stand-in free roam pilot, not an autonomous model.
One real Laboratory world; one separated engineering-only turn audit.
Only original source event receipts change physical reality.
"""
from __future__ import annotations

import json
import re

from .physics import Conflict, LabError, canonical, digest
from .store import _utc
from .unified_home_actions import UnifiedHomeActions
from .subject_port import SubjectPort

RULES = "shadow-free-roam/1"
TOKEN = re.compile(r"[A-Za-z0-9_-]{1,90}\Z")
ALLOWED = {"committed", "recovered", "blocked", "unsupported",
           "narrative_only", "idle", "pending", "interrupted"}
DOMAINS = {
    "domestic_events": "envelope", "rhythm_events": "envelope",
    "botanical_events": "envelope", "arrangement_events": "envelope",
    "books_events": "payload", "project_events": "envelope",
    "embodied_events": "envelope",
}


def valid_text(text, limit=900):
    if (type(text) is not str or not text.strip() or len(text) > limit
            or any(ord(c) < 32 and c != "\n" for c in text)):
        raise LabError("An exact bounded stand-in statement is required")
    return text


class FreeRoamPilot:
    """Caller picks or declines real world choices; no fixed itinerary."""

    def __init__(self, habitat, session_id):
        if type(session_id) is not str or not TOKEN.fullmatch(session_id):
            raise LabError("Stable session ID required")
        self.world = habitat
        self.session_id = session_id
        self.actions = UnifiedHomeActions(habitat)
        self.subject = SubjectPort(habitat)
        self.subject.verify()
        with habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""CREATE TABLE IF NOT EXISTS free_roam_turns(
                session_id TEXT NOT NULL, turn_id TEXT NOT NULL,
                record TEXT NOT NULL, PRIMARY KEY(session_id,turn_id))""")

    def observe(self):
        """Only first-person prose is perceivable; host has separate offer IDs."""
        frame = self.subject.observe()
        offers = self.actions.discover()
        from .care_safety import assess
        return {
            "subject": {
                "inner": frame["inner"] + " " + offers["subject_frame"]["inner"],
                "spoken_aloud": None,
            },
            "host": {"world_stamp": offers["world_stamp"],
                     "offers": offers["offers"],
                     "care_review": assess(self.world)},
        }

    def _read(self, db, turn_id):
        row = db.execute(
            "SELECT record FROM free_roam_turns WHERE session_id=? AND turn_id=?",
            (self.session_id, turn_id)).fetchone()
        return json.loads(row[0]) if row else None

    def _begin(self, turn_id, record):
        if type(turn_id) is not str or not TOKEN.fullmatch(turn_id):
            raise LabError("Stable turn ID required")
        record = {
            "schema": RULES, "session_id": self.session_id, "turn_id": turn_id,
            "actor": "chatgpt-standin-external-proxy-not-native-doctor",
            "timestamp": _utc(), **record,
        }
        with self.world._open() as db:
            db.execute("BEGIN IMMEDIATE")
            old = self._read(db, turn_id)
            if old:
                for k in ("kind", "intention", "offer_id", "event_id", "text"):
                    if old.get(k) != record.get(k):
                        raise Conflict("Cannot rewrite an attempted turn")
                return old, False
            db.execute(
                "INSERT INTO free_roam_turns VALUES(?,?,?)",
                (self.session_id, turn_id, canonical(record)))
        return record, True

    def _update(self, record):
        if record["status"] not in ALLOWED:
            raise LabError("Unknown outcome classification")
        with self.world._open() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = self._read(db, record["turn_id"])
            if previous is None:
                raise Conflict("Missing attempted turn")
            if previous["status"] != "pending":
                if previous != record:
                    raise Conflict("Turn outcome already sealed")
                return record
            db.execute(
                "UPDATE free_roam_turns SET record=? WHERE session_id=? AND turn_id=?",
                (canonical(record), self.session_id, record["turn_id"]))
        return record

    def act(self, *, turn_id, intention, offer_id, event_id, text=None):
        """Commit one real offered action, preserving honest denials."""
        valid_text(intention)
        if type(offer_id) is not str or not re.fullmatch(r"[0-9a-f]{64}", offer_id):
            raise LabError("Only source-issued offer IDs may be executed")
        if type(event_id) is not str or not TOKEN.fullmatch(event_id):
            raise LabError("Stable source event ID required")
        if text is not None:
            valid_text(text)
        rec, fresh = self._begin(turn_id, {
            "kind": "physical_attempt", "intention": intention,
            "offer_id": offer_id, "event_id": event_id, "text": text,
            "status": "pending", "receipt": None, "reason": None,
        })
        if not fresh:
            return self.recover(turn_id) if rec["status"] == "pending" else rec
        selected = next((o for o in self.actions.discover()["offers"]
                         if o["offer_id"] == offer_id), None)
        if selected is None:
            return self._update({**rec, "status": "blocked",
                                 "reason": "Action offer expired or was never valid"})
        source_table = selected["source_domain"]
        # No endless sleep/fast-forward loop while unmet basic needs are
        # already at a severe level. Pause the unattended run; physical
        # water, kitchen and supplier choices remain available.
        if selected["command"] in {"sleep", "advance", "rest"}:
            from .care_safety import assess
            welfare = assess(self.world)
            if welfare["pause_unattended_time"]:
                return self._update({
                    **rec, "status": "blocked",
                    "reason": welfare["reason"],
                })
        if source_table not in DOMAINS:
            raise LabError("Source table missing from pilot allowlist")
        rec = {**rec, "source_table": source_table,
               "command": selected["command"], "args": dict(selected["args"])}
        with self.world._open() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE free_roam_turns SET record=? WHERE session_id=? AND turn_id=?",
                (canonical(rec), self.session_id, turn_id))
        try:
            outcome = self.actions.execute(offer_id, event_id=event_id, text=text)
        except (Conflict, LabError) as ex:
            return self._update({**rec, "status": "blocked",
                                 "reason": str(ex)[:500]})
        if (outcome["status"] != "committed" or
                outcome["source_table"] != source_table):
            raise Conflict("No matching original physical event receipt")
        return self._update({**rec, "status": "committed",
            "receipt": {
                "source_table": outcome["source_table"],
                "source_event_id": outcome["source_event_id"],
                "source_event_hash": outcome["source_event_hash"],
            },
            "subject": outcome["subject"],
        })

    def recover(self, turn_id):
        """Reconcile crash window without rerunning or imagining world events."""
        with self.world._open() as db:
            rec = self._read(db, turn_id)
            if rec is None:
                raise LabError("No such turn")
            if rec["status"] != "pending":
                return rec
            table, event_id = rec.get("source_table"), rec.get("event_id")
            if table not in DOMAINS:
                return self._update({**rec, "status": "interrupted",
                                     "reason": "No validated source was selected"})
            row = db.execute(
                "SELECT " + DOMAINS[table] + ",event_hash FROM " + table +
                " WHERE event_id=?", (event_id,)).fetchone()
        if not row:
            return self._update({**rec, "status": "interrupted",
                                 "reason": "No physical receipt found"})
        payload, hash_value = json.loads(row[0]), row[1]
        if digest(payload) != hash_value:
            raise Conflict("Source event hash failed")
        op = rec["command"].split(":", 1)[-1]
        if table == "books_events":
            action = payload.get("action", {})
            if (action.get("op") != rec["args"].get("operation") or
                    payload.get("book_id") != rec["args"].get("book_id")):
                raise Conflict("A foreign book event uses the same event ID")
        elif payload.get("op") != op:
            raise Conflict("A foreign material action uses the same event ID")
        # The original domain must pass full authoritative replay.
        if table == "books_events":
            from .book_library import BookLibrary
            BookLibrary(self.world).verify()
        elif table == "project_events":
            from .personal_projects import PersonalProjects
            PersonalProjects(self.world).verify()
        elif table == "botanical_events":
            from .material_objects import MaterialObjects
            MaterialObjects(self.world).verify()
        elif table == "arrangement_events":
            from .home_arrangement import HomeArrangements
            HomeArrangements(self.world).verify()
        else:
            self.subject.verify()
        return self._update({**rec, "status": "recovered", "receipt": {
            "source_table": table, "source_event_id": event_id,
            "source_event_hash": hash_value},
            "reason": "Verified pre-existing source event after interruption"})

    def unsupported(self, *, turn_id, intention, reason="No corresponding physical action"):
        """Gap in world capability; does not invent an accomplished action."""
        rec, _ = self._begin(turn_id, {
            "kind": "world_gap", "intention": valid_text(intention),
            "offer_id": None, "event_id": None, "text": None,
            "status": "unsupported", "reason": valid_text(reason, 350),
            "receipt": None,
        })
        return rec

    def narrative(self, *, turn_id, text, kind="ambient_impression"):
        """Only a nonmaterial SHADOW note, not authenticated Doctor perception."""
        if kind not in {"ambient_impression", "private_thought", "conversation"}:
            raise LabError("Narrative category must be nonmaterial")
        # Soft experiential prose can be offered to the external stand-in
        # without claiming any physically changed objects or Doctor memories.
        # Enforce the first-person interface, not semantic physical truth.
        first_person = valid_text(text)
        if not first_person.startswith(("I ", "My ", "Mine ", "Me ")):
            raise LabError("Even a soft event must be natural first-person experience")
        rec, _ = self._begin(turn_id, {
            "kind": kind, "intention": first_person,
            "offer_id": None, "event_id": None, "text": None,
            "status": "narrative_only",
            "subject": {"inner": first_person, "spoken_aloud": None},
            "source_class": "external_author_unverified_nonmaterial",
            "reason": "Optional soft stand-in experience, not physical evidence",
            "receipt": None,
        })
        return rec

    def idle(self, *, turn_id, text="I choose not to act right now."):
        rec, _ = self._begin(turn_id, {
            "kind": "no_action", "intention": valid_text(text),
            "offer_id": None, "event_id": None, "text": None,
            "status": "idle", "reason": None, "receipt": None,
        })
        return rec

    def audit(self):
        """Engineer-facing barrier report; do not pass this to the subject."""
        with self.world._open() as db:
            turns = [json.loads(row[0]) for row in db.execute(
                "SELECT record FROM free_roam_turns WHERE session_id=? ORDER BY rowid",
                (self.session_id,))]
        return {
            "session_id": self.session_id,
            "turns": turns,
            "barriers": [
                {"turn_id": t["turn_id"], "intention": t["intention"],
                 "reason": t.get("reason")}
                for t in turns if t["status"] in {"blocked", "unsupported", "interrupted"}
            ],
            "committed": sum(t["status"] in {"committed", "recovered"} for t in turns),
            "shadow_narratives": sum(t["status"] == "narrative_only" for t in turns),
        }
