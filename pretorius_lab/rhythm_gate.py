"""Transactional resource/visibility policy for opt-in Laboratory rhythm worlds.

This is a low-level condition check inside the SAME SQLite transaction as
legacy books, custody and instrument actions; a higher-level adapter alone
could not prevent bypass by calling an older endpoint directly.
Without a rhythm addon, existing Laboratory worlds remain unchanged.
"""
from __future__ import annotations

import json

from .physics import Conflict

RULES = "pretorius-daily-rhythm/1"
FRESH_RULES = "pretorius-daily-rhythm/2-perishable-meals"
STOCK_RULES = "pretorius-daily-rhythm/3-physical-provision-access"
VISIBLE_RULES = "pretorius-daily-rhythm/4-visible-provision-portions"

def _data(db):
    if db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='rhythm_meta'"
    ).fetchone() is None:
        return None
    state_row = db.execute("SELECT value FROM rhythm_meta WHERE key='state'").fetchone()
    head_row = db.execute("SELECT value FROM rhythm_meta WHERE key='head_hash'").fetchone()
    revision_row = db.execute("SELECT value FROM rhythm_meta WHERE key='revision'").fetchone()
    rules_row = db.execute("SELECT value FROM rhythm_meta WHERE key='rules'").fetchone()
    if not all((state_row, head_row, revision_row, rules_row)):
        raise Conflict("Incomplete active environmental constraint record")
    state = json.loads(state_row[0])
    head = json.loads(head_row[0])
    revision = json.loads(revision_row[0])
    rules = json.loads(rules_row[0])
    if rules not in (RULES, FRESH_RULES, STOCK_RULES, VISIBLE_RULES) or type(revision) is not int or revision < 0:
        raise Conflict("Environmental constraint rules are invalid")
    if revision:
        source = db.execute(
            "SELECT envelope,event_hash FROM rhythm_events WHERE revision=?",
            (revision,)).fetchone()
        if source is None or source[1] != head:
            raise Conflict("Environmental constraint source receipt is missing")
        from .physics import digest
        rec = json.loads(source[0])
        if digest(rec) != head or rec["after_digest"] != digest(state):
            raise Conflict("Environmental constraint source state is inconsistent")
    else:
        from .store import GENESIS_HASH
        from .physics import digest
        genesis = db.execute(
            "SELECT value FROM rhythm_meta WHERE key='genesis_digest'"
        ).fetchone()
        if head != GENESIS_HASH or genesis is None or (
            json.loads(genesis[0]) != digest(state)
        ):
            raise Conflict("Environmental initial state is inconsistent")
    from .daily_rhythm import _validate
    _validate(state)
    return state

def lit(db, station):
    """No full scene data; this returns an engineer/internal affordance boolean."""
    state = _data(db)
    if state is None:
        return True
    from .embodied_access import STATIONS
    from .daily_rhythm import _can_see
    if station not in STATIONS:
        raise Conflict("Unknown physical station")
    return _can_see(state, STATIONS[station][0])

def require(db, station, activity):
    """Reject fine work under active constraints; read-only darkness is handled by port."""
    state = _data(db)
    if state is None:
        return
    from .embodied_access import STATIONS
    from .daily_rhythm import _can_see
    if station not in STATIONS:
        raise Conflict("Unknown physical station")
    if activity not in {"book_read", "book_handle", "measure", "home_inspect", "home_handle"}:
        raise Conflict("Unknown resource-gated activity")
    room = STATIONS[station][0]
    if not _can_see(state, room):
        raise Conflict("It is too dark for that detailed action")
    if activity == "measure":
        if state["fatigue"] >= 7 or state["thirst"] >= 8:
            raise Conflict("Too fatigued or thirsty for a reliable measurement")
        if state["apparatus"] <= 0:
            raise Conflict("The laboratory apparatus needs maintenance")
        if state["cleanliness"]["room:sanctum"] >= 3:
            raise Conflict("The work area needs cleaning")
    elif activity == "book_read":
        if state["fatigue"] >= 9:
            raise Conflict("Too fatigued to attend to the page")
    elif activity in {"book_handle", "home_handle"}:
        if state["fatigue"] >= 10:
            raise Conflict("Too exhausted to handle objects carefully")
