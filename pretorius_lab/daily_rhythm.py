"""Opt-in deterministic household rhythm for the persistent Pretorius Laboratory.

Same authoritative SQLite file and embodied pose. This has no autonomous
scheduler, no lived-memory claims and no Village-facing write interface.
Numerical physiology and resources are ENGINEER-ONLY; returned experience
is natural-language first-person text.
"""
from __future__ import annotations

import copy
import json
import uuid

from .embodied_access import EmbodiedAccess, STATIONS
from .habitat_v2 import SpatialHabitat
from .home_life import HomeLife, ROOM_LABELS
from .physics import Conflict, LabError, canonical, digest
from .store import GENESIS_HASH, _utc

RULES = "pretorius-daily-rhythm/1"
FRESH_RULES = "pretorius-daily-rhythm/2-perishable-meals"
STOCK_RULES = "pretorius-daily-rhythm/3-physical-provision-access"
VISIBLE_RULES = "pretorius-daily-rhythm/4-visible-provision-portions"
PAPER_RULES = "pretorius-daily-rhythm/5-physical-authored-paper"
CARE_RULES = "pretorius-daily-rhythm/6-provisioned-residency"
# A contracted offstage grocer, not a magically refilling cupboard. Deliveries
# become observable parcels after four real simulated hours, require pickup
# and explicit unpacking. The supplier's village is NOT simulated yet.
DELIVERY_DELAY = 240
DELIVERY_BUNDLE = {"water": 14, "fuel": 8, "rations": 8,
                   "tea": 4, "oil": 3, "reagents": 3, "spares": 2}
MAX_PAPER_PAGES = 40
MAX_PAPER_CHARS = 240
MEAL_FRESH_MINUTES = 360  # deliberately coarse six-hour prepared-food window
LAMPS = ("room:sanctum", "room:experiment", "room:hall", "room:kitchen",
         "room:bedroom", "room:parlor", "room:shop")
DAYLIT = frozenset(("room:sanctum", "room:kitchen",
                    "room:bedroom", "room:parlor", "room:shop"))
SUPPLY_KEYS = ("oil", "water", "fuel", "tea", "rations",
               "reagents", "spares")
SUPPLY_INITIAL = {"oil": 5, "water": 7, "fuel": 4, "tea": 3,
                  "rations": 4, "reagents": 3, "spares": 2}
CLEANABLE = ("room:sanctum", "room:kitchen", "room:shop")
STATION_WORK = "station:bench"
STATION_KITCHEN = "station:kitchen"
STATION_BEDROOM = "station:bedroom"


def initial_state() -> dict:
    return {
        "minute": 7 * 60,
        "fatigue": 2, "hunger": 2, "thirst": 2,
        "supplies": copy.deepcopy(SUPPLY_INITIAL),
        "lamps": {room: 0 for room in LAMPS},
        "cleanliness": {room: 1 for room in CLEANABLE},
        "apparatus": 2,
        "meal_ready": False,
        "experiments": 0,
        "repairs": 0,
        "chores": 0,
    }


INITIAL = initial_state()
INITIAL_DIGEST = digest(INITIAL)
FRESH_INITIAL = {**initial_state(), "meal_prepared_minute": None}
FRESH_INITIAL_DIGEST = digest(FRESH_INITIAL)
PAPER_INITIAL = {**initial_state(), "meal_prepared_minute": None, "paper_marks": []}
PAPER_INITIAL_DIGEST = digest(PAPER_INITIAL)
CARE_INITIAL = {**copy.deepcopy(PAPER_INITIAL),
                "lamps": {**copy.deepcopy(PAPER_INITIAL["lamps"]), "room:washroom": 0},
                "washroom": {"visits": 0, "washed": 0},
                "household_supply": {"ordered_minute": None,
                                     "parcel": "none", "orders": 0,
                                     "delivered": 0, "unpacked": 0}}
CARE_INITIAL_DIGEST = digest(CARE_INITIAL)


def _version_initial(rules: str) -> dict:
    if rules == RULES:
        return INITIAL
    if rules == PAPER_RULES:
        return PAPER_INITIAL
    if rules == CARE_RULES:
        return CARE_INITIAL
    if rules in (FRESH_RULES, STOCK_RULES, VISIBLE_RULES):
        return FRESH_INITIAL
    raise Conflict("Unknown household rhythm rules")


def _meal_stale(s: dict) -> bool:
    prepared = s.get("meal_prepared_minute")
    return prepared is not None and s["meal_ready"] and (
        s["minute"] - prepared >= MEAL_FRESH_MINUTES)
OPERATIONS = {"look", "advance", "tick", "light", "extinguish", "prepare_meal",
              "eat", "brew_tea", "sleep", "rest", "clean", "experiment",
              "repair", "discard_meal", "write_paper", "read_paper",
              "order_provisions", "collect_provisions", "unpack_provisions",
              "drink_water", "eat_bread", "use_washroom", "wash_hands"}


def _metadata(db):
    return {k: json.loads(v) for k, v in db.execute(
        "SELECT key,value FROM rhythm_meta")}


def _set(db, key, value):
    db.execute("INSERT OR REPLACE INTO rhythm_meta(key,value) VALUES (?,?)",
               (key, canonical(value)))


def _current(db, table: str):
    return {k: json.loads(v) for k, v in db.execute(
        f"SELECT key,value FROM {table}")}


def _stock_access(home_state: dict, station: str) -> dict:
    """Engineer-only source-bound food affordances, never an omniscient frame.

    The finite quantity already belongs to DailyRhythm. These actual durable
    objects determine whether those portions can be used *here*.
    """
    from .home_life import START_ITEMS
    room = STATIONS[station][0]
    if room != "room:kitchen":
        return {"meal": False, "tea": False}
    items, containers = home_state["items"], home_state["containers"]

    def available(item_id):
        if item_id not in START_ITEMS:
            raise Conflict("Unknown provision fixture")
        item = items[item_id]
        cid = item["container"]
        if cid is None:
            return item["held_by"] == "research-subject:pretorius"
        container = containers[cid]
        return (container["room"] == room and container["open"])

    return {
        "meal": available("food:bread"),
        "water": available("tableware:cup"),
        "tea": all(available(item) for item in (
            "food:tea", "tableware:teapot", "tableware:cup")),
    }


def _writing_access(home_state: dict, station: str) -> dict:
    """Actual writable/readable paper and ink, wherever the subject may be.

    Reuses authenticated HomeLife object custody and furniture openness;
    no abstract offstage writing ability or subject-supplied availability.
    """
    room = STATIONS[station][0]
    items, furniture = home_state["items"], home_state["containers"]

    def reachable(item_id):
        obj = items[item_id]
        if obj["container"] is None:
            return obj["held_by"] == "research-subject:pretorius"
        target = furniture[obj["container"]]
        return target["room"] == room and target["open"]

    return {"paper": reachable("stationery:paper"),
            "ink": reachable("stationery:ink")}


def _home_snapshots(db) -> dict:
    """Rebuild source-backed domestic states at each historical revision.

    HomeLife.verify has already authenticated the home chain; recomputing
    states here prevents current item positions from leaking into past action
    replays. No caller-supplied affordance bits are trusted.
    """
    from .home_life import _apply as apply_home
    meta = _current(db, "domestic_meta")
    before = copy.deepcopy(meta["genesis"])
    states = {0: before}
    for n, encoded in db.execute(
            "SELECT revision,envelope FROM domestic_events ORDER BY revision"):
        record = json.loads(encoded)
        if (n != len(states) or record["before_digest"] != digest(before)):
            raise Conflict("Invalid historical domestic state for stock access")
        after, subject = apply_home(before, record["op"], record["args"],
                                    record["station"])
        if (record["after_digest"] != digest(after) or
                record["subject"] != subject):
            raise Conflict("Domestic stock history does not replay")
        states[n] = after
        before = after
    if before != meta["state"]:
        raise Conflict("Domestic stock snapshot disagrees with verified live home")
    return states


def _cursor(db, table: str, rev: int):
    if type(rev) is not int or rev < 0:
        return None
    if rev == 0:
        return GENESIS_HASH
    row = db.execute("SELECT event_hash FROM " + table + " WHERE revision=?",
                     (rev,)).fetchone()
    return row[0] if row else None


def _pose(db, body_revision: int, initial_station: str):
    if body_revision == 0:
        return initial_station
    row = db.execute("SELECT envelope FROM embodied_events WHERE revision=?",
                     (body_revision,)).fetchone()
    if row is None:
        raise Conflict("No embodied event supports claimed pose")
    return json.loads(row[0])["after_station"]


def _validate(state: dict) -> None:
    if set(state) not in (set(INITIAL), set(FRESH_INITIAL),
                           set(PAPER_INITIAL), set(CARE_INITIAL)):
        raise Conflict("Daily state schema has drifted")
    if type(state["minute"]) is not int or state["minute"] < INITIAL["minute"]:
        raise Conflict("Invalid simulated time")
    for k in ("fatigue", "hunger", "thirst"):
        if type(state[k]) is not int or not 0 <= state[k] <= 10:
            raise Conflict("Invalid simulated regulation value")
    if set(state["supplies"]) != set(SUPPLY_INITIAL) or any(
        type(v) is not int or v < 0 or v > 200
        for v in state["supplies"].values()
    ):
        raise Conflict("Invalid finite domestic supplies")
    expected_lamps = set(LAMPS) | (
        {"room:washroom"} if "household_supply" in state else set())
    if set(state["lamps"]) != expected_lamps or any(
        type(v) is not int or not 0 <= v <= 60
        for v in state["lamps"].values()
    ):
        raise Conflict("Invalid lamp duration")
    if set(state["cleanliness"]) != set(CLEANABLE) or any(
        type(v) is not int or not 0 <= v <= 3
        for v in state["cleanliness"].values()
    ):
        raise Conflict("Invalid household condition")
    if type(state["apparatus"]) is not int or not 0 <= state["apparatus"] <= 3:
        raise Conflict("Invalid apparatus condition")
    if type(state["meal_ready"]) is not bool:
        raise Conflict("Invalid prepared food state")
    if "meal_prepared_minute" in state:
        prepared = state["meal_prepared_minute"]
        if state["meal_ready"]:
            if (type(prepared) is not int or
                    not INITIAL["minute"] <= prepared <= state["minute"]):
                raise Conflict("Prepared food has no valid preparation time")
        elif prepared is not None:
            raise Conflict("An absent meal cannot retain a preparation time")
    if "paper_marks" in state:
        marks = state["paper_marks"]
        if (type(marks) is not list or len(marks) > MAX_PAPER_PAGES or
                any(type(note) is not str or not note.strip() or
                    len(note) > MAX_PAPER_CHARS or
                    any(ord(ch) < 32 and ch != "\n" for ch in note)
                    for note in marks)):
            raise Conflict("Physically written pages are malformed")
    if "household_supply" in state:
        wc = state.get("washroom")
        if (type(wc) is not dict or set(wc) != {"visits", "washed"}
                or any(type(x) is not int or x < 0 for x in wc.values())):
            raise Conflict("Invalid private washroom record")
        supply = state["household_supply"]
        if (type(supply) is not dict or set(supply) != {
                "ordered_minute", "parcel", "orders", "delivered", "unpacked"}
                or supply["parcel"] not in ("none", "hall", "carried")
                or any(type(supply[k]) is not int or supply[k] < 0
                       for k in ("orders", "delivered", "unpacked"))
                or not (supply["unpacked"] <= supply["delivered"] <= supply["orders"])
                or (supply["ordered_minute"] is not None and (
                    type(supply["ordered_minute"]) is not int or
                    not 420 <= supply["ordered_minute"] <= state["minute"]))):
            raise Conflict("Invalid historic grocer delivery chain")
        if supply["ordered_minute"] is not None and supply["parcel"] != "none":
            raise Conflict("Only one outstanding or delivered parcel at a time")
    if any(type(state[k]) is not int or state[k] < 0
           for k in ("experiments", "repairs", "chores")):
        raise Conflict("Invalid work counters")


def _daylight(s: dict, room: str) -> bool:
    within_day = s["minute"] % 1440
    return room in DAYLIT and 360 <= within_day < 1080


def _can_see(s: dict, room: str) -> bool:
    return _daylight(s, room) or s["lamps"][room] > 0


def _pass_time(s: dict, minutes: int) -> None:
    if type(minutes) is not int or minutes < 0:
        raise LabError("Time must be a positive whole number of minutes")
    before, after = s["minute"], s["minute"] + minutes
    s["minute"] = after
    if "household_supply" in s:
        supply = s["household_supply"]
        ordered = supply["ordered_minute"]
        if ordered is not None and after - ordered >= DELIVERY_DELAY:
            supply["ordered_minute"] = None
            supply["parcel"] = "hall"
            supply["delivered"] += 1
    for room in s["lamps"]:
        s["lamps"][room] = max(0, s["lamps"][room] - minutes)
    s["hunger"] = min(10, s["hunger"] + after // 180 - before // 180)
    s["thirst"] = min(10, s["thirst"] + after // 120 - before // 120)
    s["fatigue"] = min(10, s["fatigue"] + after // 240 - before // 240)
    for room in CLEANABLE:
        s["cleanliness"][room] = min(
            3, s["cleanliness"][room] + after // 720 - before // 720
        )


def _perceive(s: dict, station: str) -> str:
    room = STATIONS[station][0]
    sentence = f"I am in {ROOM_LABELS[room]}."
    if not _can_see(s, room):
        sentence += " It is too dark to make out the furnishings clearly."
    elif _daylight(s, room):
        sentence += " There is daylight enough to see."
    else:
        sentence += " The lamp gives me enough light to see."
    if s["fatigue"] >= 7:
        sentence += " I feel worn out and find it hard to concentrate."
    elif s["fatigue"] >= 4:
        sentence += " I am getting tired."
    if s["hunger"] >= 7:
        sentence += " I am painfully hungry."
    elif s["hunger"] >= 4:
        sentence += " I could do with something to eat."
    if s["thirst"] >= 6:
        sentence += " My mouth is dry."
    if room == "room:sanctum" and _can_see(s, room):
        if s["apparatus"] <= 1:
            sentence += " My instruments look worn and will need attention."
        if s["cleanliness"][room] >= 3:
            sentence += " My work area is cluttered."
    if room == "room:kitchen" and _can_see(s, room):
        sentence += (
            " My prepared meal has been left out too long and must be discarded."
            if _meal_stale(s) else
            " There is a prepared meal to eat." if s["meal_ready"] else
            " I have no meal prepared."
        )
        if s["supplies"]["rations"] <= 0:
            sentence += " I have run out of stored food provisions."
    if "household_supply" in s and _can_see(s, room):
        parcel = s["household_supply"]["parcel"]
        if station == "station:hall" and parcel == "hall":
            sentence += " A provisioner's parcel has been left inside my entrance."
        elif parcel == "carried":
            sentence += " I am carrying the provisioner's parcel."
    if room == "room:washroom":
        sentence += " I have privacy here, with a screened sanitary closet and washstand."
    if room == "room:shop" and _can_see(s, room):
        sentence += " The little shop is hardly fit for trade."
    return sentence


def transition(state: dict, op: str, args: dict, station: str, *,
               stock_access: dict | None = None,
               writing_access: dict | None = None):
    """Pure replayable transition: no raw numbers are returned to the subject."""
    if op not in OPERATIONS or station not in STATIONS or not isinstance(args, dict):
        raise LabError("Unsupported daily-life action or bodily station")
    new = copy.deepcopy(state)
    room = STATIONS[station][0]
    said = None
    if op == "look":
        if args:
            raise LabError("Looking takes no hidden metadata")
        inner = _perceive(new, station)
    elif op == "advance":
        minutes = args.get("minutes")
        if set(args) != {"minutes"} or type(minutes) is not int or (
                minutes < 10 or minutes > 240 or minutes % 10):
            raise LabError("Authorized advance must be 10-240 minutes in 10-minute steps")
        _pass_time(new, minutes)
        inner = "Time passes. " + _perceive(new, station)
    elif op == "tick":
        # Retro turn-cost primitive. Only a trusted world adapter schedules
        # it following an accepted source action; it is NOT a subject command.
        # Unlike 'advance', tiny movement/handling costs can be 1-10 minutes.
        minutes = args.get("minutes")
        if set(args) != {"minutes"} or type(minutes) is not int or (
                minutes < 1 or minutes > 10):
            raise LabError("A physical turn costs 1-10 whole minutes")
        _pass_time(new, minutes)
        inner = "I spend a little time attending to what I have just done."
    elif op == "light":
        if args:
            raise LabError("Lighting needs no arbitrary arguments")
        if new["lamps"][room] > 0 or new["supplies"]["oil"] <= 0:
            raise Conflict("Lamp already lit or oil unavailable")
        new["supplies"]["oil"] -= 1
        new["lamps"][room] = 60
        inner = "I light the lamp. The room is easier to see."
    elif op == "extinguish":
        if args or new["lamps"][room] <= 0:
            raise Conflict("The lamp is not lit or command is malformed")
        new["lamps"][room] = 0
        inner = "I put out the lamp."
    elif op == "prepare_meal":
        if args or station != STATION_KITCHEN:
            raise LabError("A meal must be prepared in the kitchen")
        if not _can_see(new, room) or new["fatigue"] >= 9:
            raise Conflict("Too dark or exhausted to prepare food")
        if "meal_prepared_minute" in new:
            # v2 only: the complete cooking turn needs usable illumination.
            # Old v1 action results and hashes must remain unchanged.
            projected = copy.deepcopy(new)
            _pass_time(projected, 30)
            if not _can_see(projected, room):
                raise Conflict("Not enough light to finish preparing the meal")
        if new["cleanliness"][room] >= 3:
            raise Conflict("The kitchen requires cleaning before food preparation")
        if new["meal_ready"]:
            raise Conflict("A meal is already prepared")
        if stock_access is not None and not stock_access["meal"]:
            raise Conflict("The real food provisions are not within reach")
        for item in ("water", "fuel", "rations"):
            if new["supplies"][item] == 0:
                raise Conflict("Insufficient real provisions for a meal")
            new["supplies"][item] -= 1
        _pass_time(new, 30)
        new["fatigue"] = min(10, new["fatigue"] + 1)
        new["meal_ready"] = True
        if "meal_prepared_minute" in new:
            new["meal_prepared_minute"] = new["minute"]
        inner = "I prepare a simple meal from my stored provisions."
    elif op == "eat":
        if args or station != STATION_KITCHEN or not new["meal_ready"]:
            raise Conflict("I cannot eat an unprepared meal or eat it elsewhere")
        if _meal_stale(new):
            raise Conflict("The prepared meal has been left out too long to eat")
        new["meal_ready"] = False
        if "meal_prepared_minute" in new:
            new["meal_prepared_minute"] = None
        _pass_time(new, 10)
        new["hunger"] = max(0, new["hunger"] - 5)
        inner = "I eat the meal I prepared. I feel less hungry."
    elif op == "discard_meal":
        if "meal_prepared_minute" not in new:
            raise LabError("Meal freshness is not enabled in this world")
        if args or station != STATION_KITCHEN or not _meal_stale(new):
            raise Conflict("Only an actual stale meal may be discarded in the kitchen")
        new["meal_ready"] = False
        new["meal_prepared_minute"] = None
        _pass_time(new, 10)
        inner = "I throw out the meal I left too long. The provisions are wasted."
    elif op == "write_paper":
        if "paper_marks" not in new or writing_access is None:
            raise LabError("Writing on physical paper is unavailable under these world rules")
        entry = args.get("text")
        if (set(args) != {"text"} or type(entry) is not str or
                not entry.strip() or len(entry) > MAX_PAPER_CHARS or
                any(ord(ch) < 32 and ch != "\n" for ch in entry)):
            raise LabError("Write one bounded, nonempty authored paper entry")
        if not writing_access["paper"] or not writing_access["ink"]:
            raise Conflict("I must actually reach my writing paper and ink")
        if len(new["paper_marks"]) >= MAX_PAPER_PAGES:
            raise Conflict("I have no blank paper left in this stack")
        if new["fatigue"] >= 9 or not _can_see(new, room):
            raise Conflict("I cannot write properly while exhausted or in darkness")
        projected = copy.deepcopy(new)
        _pass_time(projected, 5)
        if not _can_see(projected, room):
            raise Conflict("There is not enough light left to finish writing")
        new["paper_marks"].append(entry)
        _pass_time(new, 5)
        inner = "I write on my paper: " + entry
    elif op == "read_paper":
        if "paper_marks" not in new or writing_access is None:
            raise LabError("Written physical paper is unavailable under these world rules")
        page = args.get("page")
        if set(args) != {"page"} or type(page) is not int or page < 1:
            raise LabError("Specify a positive written page")
        if not writing_access["paper"]:
            raise Conflict("I cannot reach the paper I want to read")
        if page > len(new["paper_marks"]):
            raise Conflict("There are no written words on that page yet")
        if new["fatigue"] >= 9 or not _can_see(new, room):
            raise Conflict("I cannot read the paper in these conditions")
        projected = copy.deepcopy(new)
        _pass_time(projected, 2)
        if not _can_see(projected, room):
            raise Conflict("There is not enough light left to finish reading")
        _pass_time(new, 2)
        inner = "I read what is written on my paper: " + new["paper_marks"][page - 1]
    elif op == "brew_tea":
        if args or station != STATION_KITCHEN:
            raise LabError("Tea must be made in the kitchen")
        if not _can_see(new, room) or new["fatigue"] >= 9:
            raise Conflict("Too dark or exhausted to brew tea")
        if stock_access is not None and not stock_access["tea"]:
            raise Conflict("I need the actual tea tin, teapot and cup in reach")
        if any(new["supplies"][k] == 0 for k in ("water", "tea", "fuel")):
            raise Conflict("I have run out of what I need for tea")
        for item in ("water", "tea", "fuel"):
            new["supplies"][item] -= 1
        _pass_time(new, 20)
        new["thirst"] = max(0, new["thirst"] - 4)
        inner = "I prepare and drink tea. The warmth is welcome."
    elif op == "use_washroom":
        if "household_supply" not in new:
            raise LabError("A private washroom is not available in this household")
        if args or station != "station:washroom":
            raise Conflict("I need to go into my separate private washroom")
        new["washroom"]["visits"] += 1
        _pass_time(new, 5)
        inner = "I use the private sanitary closet and attend to my needs."
    elif op == "wash_hands":
        if "household_supply" not in new:
            raise LabError("There is no supported domestic washstand")
        if args or station != "station:washroom" or new["supplies"]["water"] <= 0:
            raise Conflict("I need the washstand and actual stored water")
        new["supplies"]["water"] -= 1
        new["washroom"]["washed"] += 1
        _pass_time(new, 5)
        inner = "I wash my hands at the washstand and dry them."
    elif op == "eat_bread":
        if "household_supply" not in new:
            raise LabError("Simple uncooked food is not available under these rules")
        if args or station != STATION_KITCHEN or new["supplies"]["rations"] <= 0:
            raise Conflict("I need a real portion of bread in my kitchen")
        if stock_access is None or not stock_access["meal"]:
            raise Conflict("I cannot reach the actual bread provisions")
        new["supplies"]["rations"] -= 1
        _pass_time(new, 10)
        new["hunger"] = max(0, new["hunger"] - 4)
        inner = "I take some bread from my stores and eat it. I feel less hungry."
    elif op == "drink_water":
        if "household_supply" not in new:
            raise LabError("Plain-water drinking requires the safe residency profile")
        if args or station != STATION_KITCHEN or not _can_see(new, room):
            raise Conflict("I need the kitchen and enough light for water")
        if stock_access is None or not stock_access["water"] or new["supplies"]["water"] <= 0:
            raise Conflict("I need actual potable stored water and a reachable cup")
        new["supplies"]["water"] -= 1
        _pass_time(new, 5)
        new["thirst"] = max(0, new["thirst"] - 6)
        inner = "I pour drinking water into my cup and drink. My thirst eases."
    elif op == "order_provisions":
        if "household_supply" not in new:
            raise LabError("The household supplier is not configured")
        parcel = new["household_supply"]
        if (args or station != "station:hall" or
                parcel["ordered_minute"] is not None or parcel["parcel"] != "none"):
            raise Conflict("I cannot place another order until the last parcel is dealt with")
        parcel["ordered_minute"] = new["minute"]
        parcel["orders"] += 1
        _pass_time(new, 10)
        inner = "I leave an order for the provisioner on my established household account."
    elif op == "collect_provisions":
        if "household_supply" not in new:
            raise LabError("No household deliveries under this version")
        parcel = new["household_supply"]
        if args or station != "station:hall" or parcel["parcel"] != "hall":
            raise Conflict("There is no parcel waiting within reach")
        parcel["parcel"] = "carried"
        _pass_time(new, 5)
        inner = "I pick up the parcel of food and household supplies from the hall."
    elif op == "unpack_provisions":
        if "household_supply" not in new:
            raise LabError("No household deliveries under this version")
        parcel = new["household_supply"]
        if args or station != STATION_KITCHEN or parcel["parcel"] != "carried":
            raise Conflict("I must bring an actual parcel into my kitchen")
        if any(new["supplies"][item] + qty > 200
               for item, qty in DELIVERY_BUNDLE.items()):
            raise Conflict("My household stores have no space for another delivery")
        for item, qty in DELIVERY_BUNDLE.items():
            new["supplies"][item] += qty
        parcel["parcel"] = "none"
        parcel["unpacked"] += 1
        _pass_time(new, 20)
        inner = "I unpack the provisioner's parcel into my kitchen stores."
    elif op == "sleep":
        if args or station != STATION_BEDROOM:
            raise LabError("Sleep requires the actual bedroom")
        _pass_time(new, 480)
        new["fatigue"] = max(0, new["fatigue"] - 8)
        inner = "I have slept for the night. I feel less exhausted."
    elif op == "rest":
        if args or station != STATION_BEDROOM:
            raise LabError("Rest requires the actual bedroom")
        _pass_time(new, 60)
        new["fatigue"] = max(0, new["fatigue"] - 3)
        inner = "I sit quietly and rest awhile."
    elif op == "clean":
        if args or room not in CLEANABLE or new["cleanliness"][room] <= 0:
            raise Conflict("Nothing here needs cleaning")
        if station not in (STATION_KITCHEN, STATION_WORK,
                           "station:shop:private", "station:shop:public"):
            raise LabError("The work surface is not within reach")
        if new["fatigue"] >= 9 or not _can_see(new, room):
            raise Conflict("Too exhausted or dark to clean carefully")
        _pass_time(new, 30)
        new["cleanliness"][room] = max(0, new["cleanliness"][room] - 2)
        new["fatigue"] = min(10, new["fatigue"] + 1)
        new["chores"] += 1
        inner = "I tidy and clean the area. It looks more orderly."
    elif op == "experiment":
        if args or station != STATION_WORK:
            raise LabError("Experiments must be carried out at the laboratory bench")
        if not _can_see(new, room) or new["fatigue"] >= 7 or new["thirst"] >= 8:
            raise Conflict("Insufficient light, alertness or hydration for careful work")
        if new["cleanliness"][room] >= 3 or new["apparatus"] < 1:
            raise Conflict("The workbench or apparatus needs maintenance")
        if new["supplies"]["reagents"] < 1:
            raise Conflict("Reagents are exhausted")
        new["supplies"]["reagents"] -= 1
        new["apparatus"] -= 1
        new["experiments"] += 1
        _pass_time(new, 60)
        new["fatigue"] = min(10, new["fatigue"] + 2)
        new["cleanliness"][room] = min(3, new["cleanliness"][room] + 1)
        inner = "I complete a careful experiment at my workbench. The apparatus shows wear."
    elif op == "repair":
        if args or station != STATION_WORK:
            raise LabError("Only the nearby workbench may be serviced")
        if not _can_see(new, room) or new["fatigue"] >= 8:
            raise Conflict("Too dark or exhausted to repair the apparatus")
        if new["supplies"]["spares"] <= 0 or new["apparatus"] >= 3:
            raise Conflict("I cannot repair without parts or needlessly replace sound pieces")
        new["supplies"]["spares"] -= 1
        new["apparatus"] = min(3, new["apparatus"] + 2)
        new["repairs"] += 1
        _pass_time(new, 30)
        new["fatigue"] = min(10, new["fatigue"] + 1)
        inner = "I replace the worn component in my apparatus."
    else:
        raise LabError("Unsupported daily operation")
    # Never run an unattended model through indefinite maximum need while
    # the operator has omitted a provision/agent rescue path. Preserve the
    # last safe world state; do not auto-feed the subject or invent supplies.
    if ("household_supply" in new and op in ("advance", "sleep", "rest") and
            (new["hunger"] >= 9 or new["thirst"] >= 9)):
        raise Conflict("Residency safety pause: needs require agent-accessible care")
    _validate(new)
    return new, {"inner": inner, "spoken_aloud": said}


class DailyRhythm:
    """Bounded day-to-day experimental life, under local host authority."""

    def __init__(self, habitat: SpatialHabitat):
        self.habitat = habitat
        self.home = HomeLife(habitat)

    def initialize(self, *, initial_state: dict | None = None, parent=None,
                   perishable_meals: bool = False,
                   physical_provisions: bool = False,
                   visible_portions: bool = False,
                   physical_paper: bool = False,
                   safe_household: bool = False):
        self.home.verify()
        if (type(perishable_meals) is not bool or
                type(physical_provisions) is not bool or
                type(visible_portions) is not bool or
                type(physical_paper) is not bool or
                type(safe_household) is not bool):
            raise LabError("Rule selection must use booleans")
        if physical_provisions and not perishable_meals:
            raise LabError("Physical provisions build on the perishable-meal profile")
        if visible_portions and not physical_provisions:
            raise LabError("Visible portions require real physical provision access")
        if physical_paper and not visible_portions:
            raise LabError("Writable physical paper builds on the active living-home profile")
        if safe_household and not physical_paper:
            raise LabError("Provisioned residency extends the complete physical-paper home")
        selected_rules = (CARE_RULES if safe_household else
                          PAPER_RULES if physical_paper else
                          VISIBLE_RULES if visible_portions else
                          STOCK_RULES if physical_provisions else
                          FRESH_RULES if perishable_meals else RULES)
        seed = copy.deepcopy(initial_state if initial_state is not None
                             else _version_initial(selected_rules))
        _validate(seed)
        if set(seed) != set(_version_initial(selected_rules)):
            raise Conflict("Initial daily-life state does not match its version")
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            host = SpatialHabitat._metadata(db)
            body = _current(db, "embodied_meta")
            home = _current(db, "domestic_meta")
            db.execute("""CREATE TABLE IF NOT EXISTS rhythm_meta(
                key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS rhythm_events(
                revision INTEGER PRIMARY KEY,
                event_id TEXT NOT NULL UNIQUE,
                envelope TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE)""")
            old = _metadata(db)
            if not old:
                vals = {
                    "rules": selected_rules, "lab_id": host["lab_id"],
                    "world_epoch": host["world_epoch"], "home_id": host["home_id"],
                    "genesis": seed, "genesis_digest": digest(seed),
                    "parent": parent, "revision": 0, "head_hash": GENESIS_HASH,
                    "state": seed, "body_at_install": body["revision"],
                    "home_at_install": home["revision"],
                    "initial_station": body["station"],
                }
                for k, value in vals.items():
                    _set(db, k, value)
            elif (old["rules"] not in (RULES, FRESH_RULES, STOCK_RULES, VISIBLE_RULES, PAPER_RULES, CARE_RULES) or
                  (old["lab_id"], old["world_epoch"]) !=
                  (host["lab_id"], host["world_epoch"])):
                raise Conflict("Daily-life state is not from the current Laboratory")
            elif initial_state is not None or parent is not None or (
                    (safe_household and old["rules"] != CARE_RULES) or
                    (physical_paper and not safe_household and
                     old["rules"] not in (PAPER_RULES, CARE_RULES)) or
                    (visible_portions and not physical_paper and
                     old["rules"] not in (VISIBLE_RULES, PAPER_RULES, CARE_RULES)) or
                    (physical_provisions and not visible_portions and
                     old["rules"] not in (STOCK_RULES, VISIBLE_RULES, PAPER_RULES, CARE_RULES)) or
                    (perishable_meals and not physical_provisions and
                     old["rules"] not in (FRESH_RULES, STOCK_RULES, VISIBLE_RULES, PAPER_RULES, CARE_RULES))):
                raise Conflict("An inhabited day-to-day world cannot change its rule profile")
        return self.verify()

    def verify(self):
        self.home.verify()
        bodyproof = EmbodiedAccess(self.habitat).verify()
        world = self.habitat.verify()
        with self.habitat._open() as db:
            if db.execute("SELECT name FROM sqlite_master WHERE name='rhythm_meta'").fetchone() is None:
                raise LabError("Daily-life addon has not been initialized")
            m = _metadata(db)
            if (m["rules"] not in (RULES, FRESH_RULES, STOCK_RULES, VISIBLE_RULES, PAPER_RULES, CARE_RULES) or
                    (m["lab_id"], m["world_epoch"], m["home_id"]) !=
                    (world["lab_id"], world["world_epoch"], world["home_id"])):
                raise Conflict("Daily life uses the wrong authority")
            if digest(m["genesis"]) != m["genesis_digest"]:
                raise Conflict("Daily-life genesis modified without source")
            expected_digest = (INITIAL_DIGEST if m["rules"] == RULES else
                               CARE_INITIAL_DIGEST if m["rules"] == CARE_RULES else
                               PAPER_INITIAL_DIGEST if m["rules"] == PAPER_RULES
                               else FRESH_INITIAL_DIGEST)
            if m["parent"] is None and m["genesis_digest"] != expected_digest:
                raise Conflict("Changed canonical daily-life genesis")
            seed = copy.deepcopy(m["genesis"])
            _validate(seed)
            if set(seed) != set(_version_initial(m["rules"])):
                raise Conflict("Daily life state changed rules during replay")
            home = _current(db, "domestic_meta")
            if (m["home_at_install"] > home["revision"] or
                    m["body_at_install"] > bodyproof["revision"]):
                raise Conflict("Daily-life origin cannot postdate its current world")
            prev, rev = GENESIS_HASH, 0
            home_states = (_home_snapshots(db) if m["rules"] in (
                STOCK_RULES, VISIBLE_RULES, PAPER_RULES, CARE_RULES) else None)
            last_body, last_home = m["body_at_install"], m["home_at_install"]
            for n, event_id, encoded, prior, h in db.execute(
                "SELECT revision,event_id,envelope,prev_hash,event_hash "
                "FROM rhythm_events ORDER BY revision"):
                e = json.loads(encoded)
                if (n != rev + 1 or event_id != e["event_id"] or
                        n != e["revision"] or prior != prev or
                        e["previous_hash"] != prev or h != digest(e)):
                    raise Conflict("Corrupted day-to-day event history")
                if (e["lab_id"], e["world_epoch"], e["home_id"]) != (
                        m["lab_id"], m["world_epoch"], m["home_id"]):
                    raise Conflict("Daily-life event belongs to another world")
                br, hr = e["body_revision"], e["home_revision"]
                if (type(br) is not int or type(hr) is not int or
                        br < last_body or hr < last_home or
                        br > bodyproof["revision"] or hr > home["revision"]):
                    raise Conflict("Day-to-day event has invalid source revisions")
                if (_cursor(db, "embodied_events", br) != e["body_cursor"] or
                        _cursor(db, "domestic_events", hr) != e["home_cursor"]):
                    raise Conflict("Daily-life event cites unverifiable body/home receipts")
                station = _pose(db, br, m["initial_station"])
                if e["station"] != station or e["before_digest"] != digest(seed):
                    raise Conflict("Experience is not supported by the recorded pose/state")
                access = (_stock_access(home_states[hr], station)
                          if home_states is not None else None)
                paper = (_writing_access(home_states[hr], station)
                         if m["rules"] in (PAPER_RULES, CARE_RULES) else None)
                result, subjective = transition(
                    seed, e["op"], e["args"], station,
                    stock_access=access, writing_access=paper)
                if (e["subject"] != subjective or
                        e["after_digest"] != digest(result)):
                    raise Conflict("Daily-life consequences or first-person result altered")
                seed, prev, rev = result, h, n
                last_body, last_home = br, hr
            if (m["state"], m["head_hash"], m["revision"]) != (seed, prev, rev):
                raise Conflict("Materialized daily state cannot be replayed")
            return {"verified": True, "revision": rev, "head_hash": prev,
                    "world_epoch": m["world_epoch"], "minute": seed["minute"],
                    "body_revision": bodyproof["revision"],
                    "home_revision": home["revision"]}

    def act(self, op: str, *, event_id: str | None = None, **args):
        self.verify()
        self.home._catch_up()
        event_id = event_id or uuid.uuid4().hex
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
            raise LabError("Invalid event ID")
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            m = _metadata(db)
            body = _current(db, "embodied_meta")
            home = _current(db, "domestic_meta")
            prior = db.execute(
                "SELECT envelope,event_hash FROM rhythm_events WHERE event_id=?",
                (event_id,)).fetchone()
            if prior:
                e = json.loads(prior[0])
                if e["op"] != op or e["args"] != args:
                    raise Conflict("Event ID cannot be reused for a different action")
                return copy.deepcopy(e["subject"])
            access = (_stock_access(home["state"], body["station"])
                      if m["rules"] in (STOCK_RULES, VISIBLE_RULES, PAPER_RULES, CARE_RULES)
                      else None)
            paper = (_writing_access(home["state"], body["station"])
                     if m["rules"] in (PAPER_RULES, CARE_RULES) else None)
            after, subjective = transition(
                m["state"], op, args, body["station"],
                stock_access=access, writing_access=paper)
            event = {
                "event_id": event_id, "revision": m["revision"] + 1,
                "op": op, "args": args,
                "lab_id": m["lab_id"], "home_id": m["home_id"],
                "world_epoch": m["world_epoch"],
                "body_revision": body["revision"], "body_cursor": body["head_hash"],
                "home_revision": home["revision"], "home_cursor": home["head_hash"],
                "station": body["station"],
                "before_digest": digest(m["state"]),
                "after_digest": digest(after), "subject": subjective,
                "previous_hash": m["head_hash"], "utc": _utc(),
            }
            h = digest(event)
            db.execute("INSERT INTO rhythm_events VALUES (?,?,?,?,?)",
                       (event["revision"], event_id, canonical(event),
                        m["head_hash"], h))
            _set(db, "state", after)
            _set(db, "revision", event["revision"])
            _set(db, "head_hash", h)
            return copy.deepcopy(subjective)

    def look(self, *, event_id=None):
        return self.act("look", event_id=event_id)

    def advance(self, minutes: int, *, event_id=None):
        return self.act("advance", event_id=event_id, minutes=minutes)

    def audit_state(self):
        """Engineer-only state; never supply this to Pretorius's frame."""
        self.verify()
        with self.habitat._open() as db:
            return copy.deepcopy(_metadata(db)["state"])

    def _fork_into(self, clone: SpatialHabitat) -> None:
        """Copy present condition, not the parent's prior life events."""
        self.verify()
        with self.habitat._open() as db:
            m = _metadata(db)
            copied = copy.deepcopy(m["state"])
            parent = {"lab_id": m["lab_id"], "world_epoch": m["world_epoch"],
                      "revision": m["revision"], "head_hash": m["head_hash"],
                      "status": "cloned_state_not_subject_experience"}
        DailyRhythm(clone).initialize(
            initial_state=copied, parent=parent,
            perishable_meals="meal_prepared_minute" in copied,
            physical_provisions=m["rules"] in (STOCK_RULES, VISIBLE_RULES, PAPER_RULES, CARE_RULES),
            visible_portions=m["rules"] in (VISIBLE_RULES, PAPER_RULES, CARE_RULES),
            physical_paper=m["rules"] in (PAPER_RULES, CARE_RULES),
            safe_household=m["rules"] == CARE_RULES)
