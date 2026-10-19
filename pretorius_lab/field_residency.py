"""Opt-in manual ChatGPT-as-renderer residency field trial.

No OpenAI API, no autonomous renderer, no second world, no memory injection.
The AI receives first-person observations and choice descriptions, never
engineer state or physical IDs. Only source-verified offers can change the
world. An append-only audit logs blocked intentions and narrative-only color
separately from actual persistent physical receipts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import uuid

from .habitat_v2 import SpatialHabitat
from .home_affordances import HomeAffordances
from .home_intents import propose as propose_furniture
from .physics import Conflict, LabError, canonical, digest
from .unified_home_actions import UnifiedHomeActions

RULES = "pretorius-residency-observer/1"
WORDS = 800
_DOMAINS = {
    "rhythm_events": "envelope",
    "embodied_events": "envelope",
    "domestic_events": "envelope",
    "arrangement_events": "envelope",
    "botanical_events": "envelope",
    "books_events": "payload",
    "project_events": "envelope",
    "custody_events": "envelope",
}
_PREFIX = re.compile(r"^(?:i (?:could|want to|would like to|intend to)|please)\s+", re.I)


def _short(text, label, limit=WORDS):
    if type(text) is not str or not text.strip() or len(text) > limit:
        raise LabError(label + " must be a bounded, nonempty text")
    if any(ord(ch) < 32 and ch != "\n" for ch in text):
        raise LabError("Control characters are not supported")
    return text.strip()


def _normalized(text):
    text = _short(text, "Intention")
    text = _PREFIX.sub("", text.strip())
    return re.sub(r"\s+", " ", text.strip(" .!?\n\t")).casefold()


class TrialJournal:
    """Plain append-only experiment log, NEVER a source-of-truth world ledger."""

    def __init__(self, path: str | Path, epoch: str):
        self.path = Path(path)
        self.epoch = epoch
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.append("session", {"rules": RULES, "world_epoch": epoch})
        self.verify()

    def verify(self):
        previous, entries = "GENESIS", []
        try:
            with self.path.open("r", encoding="utf-8") as file:
                for line in file:
                    row = json.loads(line)
                    unsigned = {k: row[k] for k in (
                        "seq", "previous_hash", "kind", "details")}
                    if (set(row) != {*unsigned.keys(), "entry_hash"} or
                            row["seq"] != len(entries) + 1 or
                            row["previous_hash"] != previous or
                            digest(unsigned) != row["entry_hash"]):
                        raise Conflict("The observation log has been altered")
                    previous = row["entry_hash"]
                    entries.append(row)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise Conflict("Cannot replay the residency observation log") from exc
        if not entries or entries[0]["kind"] != "session" or (
                entries[0]["details"] != {
                    "rules": RULES, "world_epoch": self.epoch}):
            raise Conflict("Observation log belongs to another world or protocol")
        return entries

    def append(self, kind, details):
        previous_rows = self.verify() if self.path.exists() else []
        unsigned = {
            "seq": len(previous_rows) + 1,
            "previous_hash": (previous_rows[-1]["entry_hash"]
                              if previous_rows else "GENESIS"),
            "kind": kind, "details": details,
        }
        row = {**unsigned, "entry_hash": digest(unsigned)}
        # The sidecar is deliberately non-authoritative, but fsync protects
        # a recorded attempt when the simulation process is interrupted.
        import os
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical(row) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return row


class ResidencyTrial:
    """Human-paced renderer study over ONE actual verified Laboratory world."""

    def __init__(self, habitat, journal_path, *, renderer="chatgpt-provisional"):
        self.world = habitat
        self.actions = UnifiedHomeActions(habitat)
        self.renderer = _short(renderer, "Renderer identity", 100)
        with habitat._open() as db:
            epoch = SpatialHabitat._metadata(db)["world_epoch"]
        self.journal = TrialJournal(journal_path, epoch)

    def packet(self):
        """Only first-person text and unlabeled possible activities for ChatGPT.

        No hidden IDs, numeric counters, stored state or canonical autobiog.
        The external renderer may also propose something NOT on this list.
        """
        discovered = self.actions.discover()
        offers = list(dict.fromkeys(x["description"] for x in discovered["offers"]))
        return {
            "protocol": "manual-provisional-character-turn/1",
            "first_person_world": discovered["subject_frame"]["inner"],
            "possible_activities": offers,
            "instructions": (
                "Act as the provisional voice of Dr. Septimius Pretorius. "
                "Decide for yourself what to do or whether to do nothing. "
                "Use first-person natural language. You may propose anything, "
                "including something not listed. State one intended action "
                "separately from any thoughts. Do NOT claim that an action "
                "succeeded until its real-world result has been returned. "
                "Do not invent observations, past experiences, or possessions "
                "that the source has not supplied."
            ),
        }

    def _find_offer(self, intention, offers):
        canonical_intent = _normalized(intention)
        # Match an explicitly offered activity's natural language, not raw
        # world object IDs or a command written by the model.
        matched = [
            o for o in offers if _normalized(o["description"]) == canonical_intent
        ]
        if len(matched) == 1:
            return matched[0], "exact_visible_opportunity"
        if len(matched) > 1:
            return None, "ambiguous_opportunities"
        # A narrow parser is allowed to interpret furniture intentions, but
        # it may ONLY return an offer that is live in the real Laboratory.
        furniture = propose_furniture(intention, HomeAffordances(self.world))
        if furniture["status"] == "offered":
            selected = [
                x for x in offers
                if x["command"] == furniture["command"]
                and x["args"] == furniture["args"]
            ]
            if len(selected) == 1:
                return selected[0], "verified_furniture_paraphrase"
        return None, "unsupported_or_ambiguous_intent"

    def attempt(self, intention, *, event_id=None, subject_text=None):
        """Accept external choice. Never treat model prose as physical truth."""
        intention = _short(intention, "Intention")
        eid = event_id or "residency-" + uuid.uuid4().hex
        if type(eid) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", eid):
            raise LabError("Invalid world event identifier")
        past = self.journal.verify()
        if any(e["details"].get("event_id") == eid for e in past
               if e["kind"] == "attempt"):
            raise Conflict("A residency intent cannot silently be submitted twice")
        current = self.actions.discover()
        choice, matched_by = self._find_offer(intention, current["offers"])
        self.journal.append("attempt", {
            "event_id": eid, "renderer": self.renderer, "intention": intention,
            "world_stamp": current["world_stamp"],
            "match": matched_by,
            "command": choice["command"] if choice else None,
            "source_table": choice["source_domain"] if choice else None,
        })
        if choice is None:
            result = {"status": "barrier", "kind": matched_by,
                      "first_person": (
                          "I cannot yet find a reliable way to do that here. "
                          "Nothing in the room has been changed.")}
            self.journal.append("barrier", {"event_id": eid, **result})
            return result
        if choice["requires_my_own_words"]:
            if subject_text is None:
                result = {
                    "status": "needs_authored_text", "kind": "missing_words",
                    "first_person": "I still need to decide what words to write."
                }
                self.journal.append("barrier", {"event_id": eid, **result})
                return result
            subject_text = _short(subject_text, "Subject's own text", 500)
        elif subject_text is not None:
            raise LabError("Text is allowed only for genuinely authored actions")
        try:
            outcome = self.actions.execute(
                choice["offer_id"], event_id=eid, text=subject_text)
        except (Conflict, LabError) as exc:
            result = {
                "status": "barrier", "kind": "physical_denial",
                "first_person": (
                    "I cannot complete that action under the present conditions."),
                "source_error_class": type(exc).__name__,
            }
            self.journal.append("barrier", {"event_id": eid, **result})
            return result
        receipt = {
            "status": "committed", "event_id": eid,
            "source_table": outcome["source_table"],
            "source_event_hash": outcome["source_event_hash"],
            "first_person": outcome["subject"]["inner"],
        }
        self.journal.append("physical_receipt", receipt)
        return receipt

    def moment(self, first_person_text):
        """Record subjective color with NO durable material-world assertion.

        This is explicitly renderer-authored narrative, not verified weather,
        material state, personal memory or an authenticated perception.
        """
        first_person_text = _short(first_person_text, "Narrative aside", 500)
        if not re.match(r"^(I|My|Me|Mine)\b", first_person_text):
            raise LabError("Narrative notes must be in first person")
        return self.journal.append("narrative_only_unverified", {
            "renderer": self.renderer, "text": first_person_text,
            "world_effect": None,
            "status": "not_evidence_of_physical_change",
        })

    def barriers(self):
        return [r["details"] for r in self.journal.verify()
                if r["kind"] == "barrier"]

    def reconcile(self):
        """Detect interrupted commits without rerunning any material action.

        A crash can occur after the Lab commits and before the sidecar receives
        the outcome. Preserve exactly-once physical history and flag missing
        evidence for inspection rather than guessing what the model saw.
        """
        log = self.journal.verify()
        finalized = {
            r["details"]["event_id"]
            for r in log if r["kind"] in {"physical_receipt", "barrier",
                                         "recovered_physical_receipt"}
        }
        pending = [r["details"] for r in log
                   if r["kind"] == "attempt" and
                   r["details"]["event_id"] not in finalized]
        recovered = []
        with self.world._open() as db:
            for item in pending:
                domain = item["source_table"]
                if domain not in _DOMAINS:
                    recovered.append({"event_id": item["event_id"],
                                      "status": "unresolved"})
                    continue
                row = db.execute(
                    "SELECT " + _DOMAINS[domain] + ",event_hash FROM " +
                    domain + " WHERE event_id=?", (item["event_id"],)
                ).fetchone()
                if row is None:
                    recovered.append({"event_id": item["event_id"],
                                      "status": "unresolved"})
                    continue
                if digest(json.loads(row[0])) != row[1]:
                    raise Conflict("A recovered physical source receipt was altered")
                proof = {"event_id": item["event_id"],
                         "source_table": domain, "source_event_hash": row[1],
                         "status": "physically_committed_but_delivery_unconfirmed"}
                self.journal.append("recovered_physical_receipt", proof)
                recovered.append(proof)
        return recovered


def main(argv=None):
    p = argparse.ArgumentParser(description="Opt-in, manual ChatGPT Doctor residency")
    p.add_argument("--world", required=True, help="Existing research Laboratory SQLite")
    p.add_argument("--journal", required=True, help="Append-only observation sidecar JSONL")
    p.add_argument("command", choices=["observe", "attempt", "moment", "barriers", "reconcile"])
    p.add_argument("--intent")
    p.add_argument("--text")
    p.add_argument("--event-id")
    args = p.parse_args(argv)
    trial = ResidencyTrial(SpatialHabitat(args.world), args.journal)
    if args.command == "observe":
        result = trial.packet()
    elif args.command == "attempt":
        result = trial.attempt(args.intent, event_id=args.event_id, subject_text=args.text)
    elif args.command == "moment":
        result = trial.moment(args.text)
    elif args.command == "barriers":
        result = trial.barriers()
    else:
        result = trial.reconcile()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
