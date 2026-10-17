"""Opt-in 1980s-style action-point clock over the existing physical Laboratory.

One short source-bound time tick follows each successful movement or manipulation.
The existing DailyRhythm still owns hunger, thirst, fatigue, lamps and sunlight.
Never changes canonical worlds unless a caller explicitly constructs this port.
The subject gets only natural-language first-person text.

This is NOT a general scheduler, an autonomous Doctor, or a substitute for
a full two-phase transaction across the physical and rhythm ledgers.
"""
from __future__ import annotations

from hashlib import sha256
from copy import deepcopy
import json
import re

from .physics import Conflict, LabError
from .subject_port import SubjectPort

# Small deliberately coarse action costs, with a hard cap of 10 minutes.
# World operations that *already* advance physical time are not charged again.
COSTS = {
    "walk": 2,
    "open": 1,
    "close": 1,
    "take": 1,
    "put": 1,
    "shift_stool": 3,
    "measure": 8,
    "take_book": 2,
    "put_book": 2,
}
BOOK_COSTS = {
    "open": 2, "close": 1, "turn": 1, "read": 10,
    "mark": 1, "unmark": 1, "open_mark": 2,
}
_ID = re.compile(r"[A-Za-z0-9_-]{1,80}\Z")


def _as_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


class TurnCostSubjectPort:
    """A compact game turn system over the *same* subject and material world.

    Accepted actions are followed by a bounded deterministic clock tick.
    The intent row reserves the action ID first, so a crash cannot silently
    let the next timed action overtake incomplete cost accounting.
    Crash after physical action but before tick is retried with the SAME
    source event ID. Crash after tick but before final record fails closed
    for engineer reconciliation instead of inventing the original frame.
    """

    def __init__(self, subject: SubjectPort):
        if not isinstance(subject, SubjectPort):
            raise TypeError("Existing restricted Laboratory SubjectPort required")
        self.subject = subject
        self.subject.verify()
        with self.subject.habitat._open() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS turn_cost_intents (
                world_epoch TEXT NOT NULL, event_id TEXT NOT NULL,
                command TEXT NOT NULL, arguments TEXT NOT NULL,
                clock_event_id TEXT NOT NULL,
                status TEXT NOT NULL, subject_json TEXT,
                PRIMARY KEY(world_epoch, event_id))""")

    def observe(self):
        return self.subject.observe()

    def verify(self):
        return self.subject.verify()

    def _pending(self, db, epoch, *, except_id=None):
        row = db.execute(
            """SELECT event_id FROM turn_cost_intents
               WHERE world_epoch=? AND status='pending' AND event_id != ?
               LIMIT 1""", (epoch, except_id or "")).fetchone()
        if row:
            raise Conflict("A previous physical turn needs recovery before further action")

    def act(self, command: str, *, event_id: str | None = None, **args):
        epoch = self.subject.verify()["world_epoch"]
        cost = COSTS.get(command)
        if command == "book":
            cost = BOOK_COSTS.get(args.get("operation"))
        # This port leaves the existing meaningful duration of experiment,
        # sleep, food preparation, tea, repair and advance unchanged.
        if cost is None:
            with self.subject.habitat._open() as db:
                self._pending(db, epoch)
            return self.subject.act(command, event_id=event_id, **args)
        if not isinstance(event_id, str) or not _ID.fullmatch(event_id):
            raise LabError("A timed action requires a stable bounded source event ID")
        if command == "measure" or (
                command == "book" and args.get("operation") == "read"):
            # A whole uninterrupted visual task needs adequate light at its
            # projected completion, not only at the instant it starts.
            # Deterministic old-school affordance rule over the existing
            # lamp/daylight model. No new world state or invented senses.
            from .daily_rhythm import _can_see, _pass_time
            from .embodied_access import STATIONS
            state = deepcopy(self.subject.rhythm.audit_state())
            station = self.subject.embodied.verify()["station"]
            _pass_time(state, cost)
            if not _can_see(state, STATIONS[station][0]):
                raise Conflict("Not enough usable light remains to finish the task")
        args_json = _as_json(args)
        clock_id = "turn-" + sha256((epoch + "\0" + event_id).encode()).hexdigest()[:48]
        with self.subject.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            self._pending(db, epoch, except_id=event_id)
            old = db.execute("""SELECT command,arguments,clock_event_id,status,subject_json
                  FROM turn_cost_intents WHERE world_epoch=? AND event_id=?""",
                (epoch, event_id)).fetchone()
            if old is None:
                db.execute("INSERT INTO turn_cost_intents VALUES(?,?,?,?,?,?,?)",
                           (epoch, event_id, command, args_json,
                            clock_id, "pending", None))
            else:
                previous_command, previous_args, previous_id, status, saved = old
                if (previous_command, previous_args, previous_id) != (
                        command, args_json, clock_id):
                    raise Conflict("An event ID cannot refer to a different physical action")
                if status == "completed":
                    if saved is None:
                        raise Conflict("The completed turn has no subjective source frame")
                    return json.loads(saved)
                if status != "pending":
                    raise Conflict("Unknown turn source status")
                # Replaying a committed time tick after losing the original
                # composite frame would falsely manufacture historical words.
                if db.execute("SELECT 1 FROM rhythm_events WHERE event_id=?",
                              (clock_id,)).fetchone():
                    raise Conflict("Post-clock crash requires engineer reconciliation")
        # Actual world action first, one deterministic clock event second.
        # If the world operation fails, an intent remains pending; do not
        # pretend it succeeded or silently authorize another action.
        try:
            original = self.subject.act(command, event_id=event_id, **args)
        except (Conflict, LabError, ValueError):
            # A rejected input must not strand the entire world. Remove its
            # reservation only when the authoritative source has NO action
            # receipt and the original world still verifies.
            self.subject.verify()
            domains = {
                "walk": "embodied_events",
                "open": "domestic_events", "close": "domestic_events",
                "take": "domestic_events", "put": "domestic_events",
                "shift_stool": "domestic_events", "book": "books_events",
                "measure": "instrument_events",
                "take_book": "custody_events", "put_book": "custody_events",
            }
            with self.subject.habitat._open() as db:
                table = domains[command]
                accepted = db.execute("SELECT 1 FROM " + table +
                    " WHERE event_id=?", (event_id,)).fetchone()
                if accepted is None:
                    db.execute("""DELETE FROM turn_cost_intents
                        WHERE world_epoch=? AND event_id=? AND status='pending'""",
                        (epoch, event_id))
            raise
        tick = self.subject.rhythm.act("tick", event_id=clock_id, minutes=cost)
        if (set(original) != {"inner", "spoken_aloud"} or
                set(tick) != {"inner", "spoken_aloud"}):
            raise Conflict("Inadmissible source experience")
        # The clock is a world consequence, not repetitive dialogue.
        # Natural first-person changes (darkness, thirst, fatigue) appear
        # during subsequent observations. Keep only the original action's
        # authentic subject experience as the delivered frame.
        result = {
            "inner": original["inner"].strip(),
            "spoken_aloud": original["spoken_aloud"],
        }
        with self.subject.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""UPDATE turn_cost_intents
                  SET status='completed',subject_json=?
                  WHERE world_epoch=? AND event_id=? AND status='pending'""",
                (_as_json(result), epoch, event_id))
            if db.execute("SELECT changes()").fetchone()[0] != 1:
                raise Conflict("Time-cost accounting lost its pending action")
        return result
