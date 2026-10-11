"""Research-only bridge: verified laboratory instrument -> definitive Pretorius brain.

No policy for acting is invented here. This module only tests reliable,
idempotent *admission* of real host-certified measurement offers to the
existing The-Doctor-Lives brain. Matched withheld receipts are not admitted.
Neither offered input nor stored memory is proof of subjective attention.
Requires The-Doctor-Lives at the pinned external CI revision.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from .bench_instruments import BenchInstruments, _meta as instrument_meta
from .habitat_v2 import SpatialHabitat
from .physics import Conflict, LabError, canonical, digest

BRIDGE_RULES = "pretorius-lab-brain-admission-research/1"
SOURCE_CLASS = "verified_simulated_instrument_receipt"


def _subject_percept(event):
    """Closed, non-freeform numeric instrument-to-first-person projector."""
    from .bench_instruments import DEVICES, SOURCE
    device = event["instrument"]
    obs = event["observation"]
    if device not in DEVICES or obs["source_class"] != SOURCE:
        raise Conflict("Unrecognized or unverified instrument observation")
    if obs["quantity"] not in DEVICES[device]["quantities"]:
        raise Conflict("Instrument cannot observe requested quantity")
    if (type(obs["value"]) is not int or type(obs["uncertainty"]) is not int or
            obs["uncertainty"] < 1 or obs["unit"] != DEVICES[device]["unit"]):
        raise Conflict("Malformed numerical observation")
    if obs["interval"] != [
            obs["value"] - obs["uncertainty"],
            obs["value"] + obs["uncertainty"]]:
        raise Conflict("Instrument uncertainty interval inconsistent")
    # Only a locked list of lab-book IDs can enter the subject presentation.
    # Do not inject raw book titles or arbitrary untrusted object prose.
    oid = event["object_id"]
    if oid == "beaker:001":
        item = "the laboratory beaker"
    elif oid.startswith("book:") and oid[5:].isdigit() and len(oid) == 8:
        item = "the volume on my bench"
    else:
        raise Conflict("Unsupported physical measurement subject")
    label = {"width_mm": "thickness", "height_mm": "height",
             "depth_mm": "depth", "mass_g": "mass"}[obs["quantity"]]
    instrument = ("ruler" if device == "ruler:bench" else "balance")
    return (f"The {instrument} before me reads {obs['value']} {obs['unit']} "
            f"for the {label} of {item}; the reading may be off by "
            f"{obs['uncertainty']} {obs['unit']} either way.")


class ResearchInstrumentAdmission:
    """Two-state recovery guard for an otherwise non-transactional brain port."""

    def __init__(self, lab_path, brain_state_dir, *, neural_config=None):
        # Lazy import: standalone Laboratory must never require the brain.
        from doctor_lives import PretoriusBrainPort
        self.habitat = SpatialHabitat(lab_path)
        self.instruments = BenchInstruments(self.habitat)
        self.instruments.verify()
        self.brain_dir = Path(brain_state_dir)
        self.brain_dir.mkdir(parents=True, exist_ok=True)
        self.brain = PretoriusBrainPort(self.brain_dir, neural_config=neural_config)
        self.sidecar = self.brain_dir / "laboratory_delivery_research.sqlite3"
        world = self.habitat.verify()
        self.epoch = world["world_epoch"]
        self.lab_id = world["lab_id"]
        self._init_log()

    def _open(self):
        db = sqlite3.connect(self.sidecar)
        db.row_factory = sqlite3.Row
        return db

    def _init_log(self):
        with self._open() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS bridge_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS bridge_receipts(
                source_event_id TEXT PRIMARY KEY, instrument_hash TEXT NOT NULL,
                condition TEXT NOT NULL, source TEXT, subject_text TEXT,
                brain_memory_id TEXT, stage TEXT NOT NULL)""")
            old = dict(db.execute("SELECT key,value FROM bridge_meta"))
            required = {"schema": BRIDGE_RULES, "lab_id": self.lab_id,
                        "world_epoch": self.epoch}
            if old:
                if {k: json.loads(v) for k, v in old.items()} != required:
                    raise Conflict("Research bridge belongs to a different laboratory epoch")
            else:
                for k, v in required.items():
                    db.execute("INSERT INTO bridge_meta VALUES (?,?)", (k, canonical(v)))

    def _verified_measurement(self, receipt):
        if not isinstance(receipt, dict):
            raise Conflict("Only an accepted laboratory receipt may be admitted")
        self.instruments.verify()
        eid, h = receipt.get("event_id"), receipt.get("event_hash")
        if not isinstance(eid, str) or not isinstance(h, str):
            raise Conflict("Missing instrument event identity")
        with self.habitat._open() as db:
            row = db.execute(
                "SELECT envelope,event_hash FROM instrument_events WHERE event_id=?",
                (eid,)).fetchone()
            if row is None or row[1] != h:
                raise Conflict("Rejected fabricated, mismatched or replayed instrument receipt")
            event = json.loads(row[0])
            if event["lab_id"] != self.lab_id or event["world_epoch"] != self.epoch:
                raise Conflict("Instrument outcome is from another research world")
            # Explicit equality includes bounded observation: caller cannot
            # alter a number while keeping a valid event hash.
            expected = {"event_id": eid, "event_hash": h,
                        "instrument": event["instrument"],
                        "object_id": event["object_id"],
                        "observation": event["observation"],
                        "observation_class": "offered_not_attested_subject_memory"}
            if receipt != expected:
                raise Conflict("External instrument payload differs from accepted event")
        return event

    def _memories(self, source, text):
        matched = [m for m in self.brain.brain.store.memories(active_only=False)
                   if m["source"] == source]
        if any(m["text"] != text or m["evidence_class"] != "lived_runtime_memory"
               or m["external"] for m in matched):
            raise Conflict("Brain memory provenance contradicts accepted instrument")
        if len(matched) > 1:
            raise Conflict("A lab reading was admitted more than once")
        return matched

    def deliver(self, receipt, *, condition="observed", inject_fault=False):
        """Called only when a trusted controller DELIVERS an accepted readout.

        'withheld' performs the same physical experiment but sends no text to
        Pretorius. Crashes after brain ingest reconcile by deterministic source
        and memory comparison; duplicates are rejected rather than reingested.
        """
        if condition not in {"observed", "withheld"}:
            raise LabError("Unknown preregistered measurement condition")
        event = self._verified_measurement(receipt)
        percept = _subject_percept(event)
        source = "laboratory-instrument:" + receipt["event_hash"]
        eid = event["event_id"]
        with self._open() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM bridge_receipts WHERE source_event_id=?",
                             (eid,)).fetchone()
            if row:
                prior = dict(row)
                if (prior["instrument_hash"], prior["condition"],
                    prior["source"], prior["subject_text"]) != (
                        receipt["event_hash"], condition, source, percept):
                    raise Conflict("One measurement cannot cross under two conditions")
            else:
                db.execute("""INSERT INTO bridge_receipts
                           (source_event_id,instrument_hash,condition,source,
                            subject_text,brain_memory_id,stage)
                           VALUES (?,?,?,?,?,?,?)""",
                           (eid, receipt["event_hash"], condition, source, percept,
                            None, "withheld" if condition == "withheld" else "pending"))
            if condition == "withheld":
                if self._memories(source, ""):
                    raise Conflict("Withheld result leaked into brain")
                return {"condition": "withheld", "admitted": False,
                        "measurement_event_hash": receipt["event_hash"]}
            existing = self._memories(source, "I receive this result from the tool: " + percept)
            if not existing:
                if row and row["stage"] == "committed":
                    raise Conflict("A previously recorded brain memory has disappeared")
                # The production brain alone creates neural/state/memory changes;
                # this controller never mutates brain internal memory tables.
                result = self.brain.ingest({
                    "channel": "tool", "percept": percept,
                    "kind": "observation", "source": source,
                    "novelty": 0.2, "confidence": 1.0})
                self.brain.save()
                if inject_fault:
                    raise RuntimeError("Simulated crash after brain ingest")
                mid = result["memory_id"]
                existing = self._memories(
                    source, "I receive this result from the tool: " + percept)
                if len(existing) != 1 or existing[0]["id"] != mid:
                    raise Conflict("Production brain ingress did not admit exactly one memory")
            mid = existing[0]["id"]
            if row and row["stage"] == "committed" and row["brain_memory_id"] != mid:
                raise Conflict("Recorded brain memory changed across restart")
            db.execute("UPDATE bridge_receipts SET brain_memory_id=?,stage='committed' "
                       "WHERE source_event_id=?", (mid, eid))
            return {"condition": "observed", "admitted": True,
                    "measurement_event_hash": receipt["event_hash"],
                    "brain_memory_id": mid,
                    "brain_tick": self.brain.brain.store.tick,
                    "claim": "accepted_brain_ingress_not_proof_of_attention_or_recall"}

    def verify(self):
        """Engineer-only cross-source admission check (no subject exposure)."""
        self.instruments.verify()
        with self._open() as db:
            for row in db.execute("SELECT * FROM bridge_receipts"):
                r = dict(row)
                with self.habitat._open() as source_db:
                    record = source_db.execute(
                        "SELECT event_hash FROM instrument_events WHERE event_id=?",
                        (r["source_event_id"],)).fetchone()
                    if record is None or record[0] != r["instrument_hash"]:
                        raise Conflict("Research admission references missing host outcome")
                found = self._memories(
                    r["source"],
                    "I receive this result from the tool: " + r["subject_text"])
                if r["condition"] == "withheld":
                    if found or r["stage"] != "withheld":
                        raise Conflict("Withheld host result entered cognition")
                elif r["stage"] == "committed":
                    if len(found) != 1 or found[0]["id"] != r["brain_memory_id"]:
                        raise Conflict("Brain and instrument admission records diverged")
                elif r["stage"] == "pending":
                    # Fail closed until an explicit retry reconciles the crash.
                    raise Conflict("Instrument admission pending recovery")
                else:
                    raise Conflict("Unknown admission stage")
        return {"verified": True, "world_epoch": self.epoch,
                "claim": "brain-ingress-replay-only_no_policy_or_memory_efficacy"}
