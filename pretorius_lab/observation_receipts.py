"""Persistent receipts for host-grounded observations offered to a subject interface.

A receipt proves the local interface handed back specified host-backed data.
It does NOT prove an LLM attended, read, remembered, or subjectively witnessed it.
Engineering-only inspect/status endpoints deliberately do not create receipts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import uuid

from .habitat_v2 import SpatialHabitat, TRUSTED_ACTORS
from .physics import Conflict, LabError, canonical, digest
from .store import GENESIS_HASH, _utc

RECEIPT_RULES = "observation-offer-ledger/1"


def _meta(db):
    return {k: json.loads(v) for k, v in db.execute("SELECT key,value FROM observation_meta")}


def _put(db, k, v):
    db.execute("INSERT OR REPLACE INTO observation_meta(key,value) VALUES (?,?)",
               (k, canonical(v)))


class ObservationPort:
    def __init__(self, habitat: SpatialHabitat):
        self.habitat = habitat

    def initialize(self) -> dict:
        self.habitat.verify()
        with self.habitat._open() as db:
            db.execute("BEGIN IMMEDIATE")
            host = SpatialHabitat._metadata(db)
            db.execute("CREATE TABLE IF NOT EXISTS observation_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS observation_events(
                sequence INTEGER PRIMARY KEY, delivery_id TEXT UNIQUE NOT NULL,
                payload TEXT NOT NULL, prev_hash TEXT NOT NULL, event_hash TEXT UNIQUE NOT NULL
            )""")
            prior = _meta(db)
            if not prior:
                for key, value in {
                    "lab_id": host["lab_id"], "world_epoch": host["world_epoch"],
                    "home_id": host["home_id"], "ruleset": RECEIPT_RULES,
                    "sequence": 0, "head_hash": GENESIS_HASH,
                }.items():
                    _put(db, key, value)
            elif (prior["lab_id"], prior["world_epoch"], prior["ruleset"]) != (
                    host["lab_id"], host["world_epoch"], RECEIPT_RULES):
                raise Conflict("Observation ledger bound to wrong physical world")
        return self.verify()

    @staticmethod
    def _source_cursor(db, revision):
        if type(revision) is not int or revision < 0:
            return None
        if revision == 0:
            return GENESIS_HASH
        row = db.execute("SELECT event_hash FROM events WHERE revision=?", (revision,)).fetchone()
        return row[0] if row else None

    def verify(self) -> dict:
        proof = self.habitat.verify()
        with self.habitat._open() as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='observation_meta'").fetchone() is None:
                raise LabError("Observation receipt port has not been initialized")
            m = _meta(db)
            if (m["lab_id"], m["world_epoch"], m["home_id"], m["ruleset"]) != (
                    proof["lab_id"], proof["world_epoch"], proof["home_id"], RECEIPT_RULES):
                raise Conflict("Observation receipt provenance mismatch")
            prev, seq = GENESIS_HASH, 0
            for n, did, encoded, prior, event_hash in db.execute(
                    "SELECT sequence,delivery_id,payload,prev_hash,event_hash FROM observation_events ORDER BY sequence"):
                e = json.loads(encoded)
                if (n != seq + 1 or n != e["sequence"] or did != e["delivery_id"] or
                        prior != prev or e["previous_hash"] != prev or digest(e) != event_hash):
                    raise Conflict("Observation receipt chain corrupted")
                if (e["lab_id"], e["world_epoch"]) != (m["lab_id"], m["world_epoch"]):
                    raise Conflict("Observation issued for wrong world")
                if (e["world_revision"] > proof["revision"] or
                        e["world_cursor"] != self._source_cursor(db, e["world_revision"])):
                    raise Conflict("Observation receipt cites uncommitted world state")
                if e["payload_digest"] != digest(e["offered_payload"]):
                    raise Conflict("Observation offered payload changed")
                prev, seq = event_hash, n
            if (seq, prev) != (m["sequence"], m["head_hash"]):
                raise Conflict("Observation ledger head mismatch")
            return {"verified": True, "sequence": seq, "head_hash": prev,
                    "lab_id": m["lab_id"], "world_epoch": m["world_epoch"]}

    def expose(self, kind: str, target: str, *, actor: str = "pretorius_research",
               delivery_id: str | None = None) -> dict:
        if actor not in TRUSTED_ACTORS:
            raise LabError("Actor must be a trusted local source interface")
        if kind not in {"room", "shelf", "object"} or not isinstance(target, str):
            raise LabError("Unsupported observation request")
        delivery_id = delivery_id or str(uuid.uuid4())
        if not isinstance(delivery_id, str) or not 1 <= len(delivery_id) <= 128:
            raise LabError("Invalid delivery ID")
        self.verify()
        # Read only the subject-facing ports. No engineer-only xyz_mm data.
        if kind == "room":
            payload = self.habitat.observe(target)
        elif kind == "shelf":
            payload = self.habitat.scan(target)
        else:
            payload = self.habitat.locate(target)
        world_revision = payload["revision"] if "revision" in payload else None
        world_cursor = payload["event_cursor"] if "event_cursor" in payload else None
        # locate() intentionally suppresses host internals. Bind it to a
        # verified source cursor here, without returning those internals.
        if world_revision is None:
            verified = self.habitat._verified_status()
            world_revision, world_cursor = verified["revision"], verified["head_hash"]
        db = self.habitat._open()
        try:
            db.execute("BEGIN IMMEDIATE")
            m = _meta(db)
            host = SpatialHabitat._metadata(db)
            if (host["revision"], host["head_hash"]) != (world_revision, world_cursor):
                raise Conflict("World changed during exposure; retry")
            existing = db.execute("SELECT payload,event_hash FROM observation_events WHERE delivery_id=?",
                                  (delivery_id,)).fetchone()
            if existing is not None:
                e = json.loads(existing[0])
                if (e["kind"], e["target"], e["actor"]) != (kind, target, actor):
                    raise Conflict("Delivery ID reused with different observation")
                if e["payload_digest"] != digest(payload):
                    raise Conflict("Retry changed the delivered observation")
                db.execute("COMMIT")
                return {**e, "receipt_hash": existing[1]}
            e = {
                "delivery_id": delivery_id,
                "sequence": m["sequence"] + 1,
                "lab_id": m["lab_id"], "world_epoch": m["world_epoch"],
                "world_revision": world_revision, "world_cursor": world_cursor,
                "kind": kind, "target": target, "actor": actor,
                "offered_payload": payload, "payload_digest": digest(payload),
                "claim": "offered_to_interface_not_proof_of_reading_or_memory",
                "previous_hash": m["head_hash"], "recorded_utc": _utc(),
            }
            event_hash = digest(e)
            db.execute("INSERT INTO observation_events VALUES (?,?,?,?,?)",
                       (e["sequence"], delivery_id, canonical(e), m["head_hash"], event_hash))
            _put(db, "sequence", e["sequence"])
            _put(db, "head_hash", event_hash)
            db.execute("COMMIT")
            return {"offered_payload": payload, "delivery_id": delivery_id,
                    "receipt_hash": event_hash,
                    "delivery_class": e["claim"]}
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()


def main(argv=None):
    p = argparse.ArgumentParser(description="Source-grounded subject observation receipts")
    p.add_argument("--db", default="data/sanctum-v2.sqlite3")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("verify")
    for kind in ("room", "shelf", "object"):
        cmd = sub.add_parser(kind)
        cmd.add_argument("target")
    args = p.parse_args(argv)
    port = ObservationPort(SpatialHabitat(args.db))
    try:
        if args.cmd == "init":
            result = port.initialize()
        elif args.cmd == "verify":
            result = port.verify()
        else:
            result = port.expose(args.cmd, args.target)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except (Conflict, LabError, FileNotFoundError, ValueError) as exc:
        p.exit(2, f"Observation error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
