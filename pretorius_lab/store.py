"""SQLite authority: transactional events, replay, snapshots and offline reconciliation.

This is a single-user trusted research host, NOT a network-authenticated service.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import sqlite3
import uuid

from .physics import (
    SCHEMA_VERSION, RULESET_VERSION, MANIFEST_DIGEST, LabError, Conflict,
    canonical, digest, initial_state, affected_ids, apply,
)

GENESIS_HASH = "0" * 64
TRUSTED_LOCAL_ACTORS = frozenset({"local_operator", "pretorius_research"})

def _utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()

def _meta(db: sqlite3.Connection) -> dict:
    return {key: json.loads(value) for key, value in db.execute("SELECT key,value FROM meta")}

def _put(db: sqlite3.Connection, key: str, value) -> None:
    db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (key, canonical(value)))

def _atomic_json(path: Path, value: dict, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical(value) + "\n"
    if exclusive and path.exists():
        raise FileExistsError(str(path))
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("x", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if exclusive and path.exists():
            raise FileExistsError(str(path))
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)

class Laboratory:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        if not self.path.is_file():
            raise FileNotFoundError(str(self.path))
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @classmethod
    def create(cls, path: str | Path) -> "Laboratory":
        lab = cls(path)
        lab.path.parent.mkdir(parents=True, exist_ok=True)
        if lab.path.exists():
            raise FileExistsError(str(lab.path))
        db = sqlite3.connect(lab.path, isolation_level=None)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("""CREATE TABLE events (
                revision INTEGER PRIMARY KEY,
                event_id TEXT NOT NULL UNIQUE,
                envelope TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE
            )""")
            db.execute("""CREATE TABLE snapshots (
                revision INTEGER PRIMARY KEY,
                state_json TEXT NOT NULL,
                state_digest TEXT NOT NULL,
                event_hash TEXT NOT NULL
            )""")
            state = initial_state()
            initial = {
                "lab_id": str(uuid.uuid4()), "world_epoch": str(uuid.uuid4()),
                "schema_version": SCHEMA_VERSION, "ruleset_version": RULESET_VERSION,
                "content_manifest_digest": MANIFEST_DIGEST,
                "revision": 0, "head_hash": GENESIS_HASH,
                "state": state,
            }
            for key, value in initial.items():
                _put(db, key, value)
            db.execute("INSERT INTO snapshots VALUES (?,?,?,?)",
                       (0, canonical(state), digest(state), GENESIS_HASH))
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK") if db.in_transaction else None
            raise
        finally:
            db.close()
        return lab

    def status(self) -> dict:
        with self._connect() as db:
            m = _meta(db)
            return {**{k: v for k, v in m.items() if k != "state"},
                    "state_digest": digest(m["state"]), "objects": m["state"]}

    def event(self, event_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT envelope FROM events WHERE event_id=?", (event_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def commit(self, action: dict, *, actor: str = "local_operator",
               expected_versions: dict | None = None, event_id: str | None = None,
               origin_branch: str | None = None) -> dict:
        # Authentication is assumed at this trusted local CLI boundary; this
        # allowlist is not an authentication protocol for network clients.
        if actor not in TRUSTED_LOCAL_ACTORS:
            raise LabError("Untrusted local actor")
        event_id = event_id or str(uuid.uuid4())
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
            raise LabError("Invalid event ID")
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT envelope FROM events WHERE event_id=?", (event_id,)).fetchone()
            if existing:
                prior = json.loads(existing[0])
                if prior["action"] != action or prior["actor_id"] != actor or prior["origin_branch"] != origin_branch:
                    raise Conflict("Idempotency key reused with different request")
                db.execute("COMMIT")
                return prior
            m = _meta(db)
            if (m["schema_version"], m["ruleset_version"], m["content_manifest_digest"]) != (
                    SCHEMA_VERSION, RULESET_VERSION, MANIFEST_DIGEST):
                raise Conflict("Schema, rules or content manifest mismatch")
            ids = affected_ids(action)
            state = m["state"]
            if not ids <= state.keys():
                raise LabError("Unknown object")
            if expected_versions is not None:
                if set(expected_versions) != ids or any(
                    type(expected_versions[i]) is not int or
                    state[i]["revision"] != expected_versions[i] for i in ids
                ):
                    raise Conflict("Changed object precondition; manual review required")
            previous = m["revision"]
            updated = apply(state, action, previous + 1)
            envelope = {
                "event_id": event_id, "lab_id": m["lab_id"],
                "world_epoch": m["world_epoch"], "schema_version": SCHEMA_VERSION,
                "ruleset_version": RULESET_VERSION, "content_manifest_digest": MANIFEST_DIGEST,
                "actor_id": actor, "authority": "trusted_local_only",
                "visibility": "research_private", "source_class": (
                    "offline_proposal_accepted_by_local_host" if origin_branch else "local_host_attested"
                ),
                "origin_branch": origin_branch, "action": action,
                "base_revision": previous, "committed_revision": previous + 1,
                "preconditions": {i: state[i]["revision"] for i in sorted(ids)},
                "before_digest": digest(state), "after_digest": digest(updated),
                "previous_event_hash": m["head_hash"], "committed_at_utc": _utc(),
            }
            event_hash = digest({"previous_event_hash": m["head_hash"], "envelope": envelope})
            db.execute("INSERT INTO events VALUES (?,?,?,?,?)",
                       (previous + 1, event_id, canonical(envelope), m["head_hash"], event_hash))
            _put(db, "revision", previous + 1)
            _put(db, "state", updated)
            _put(db, "head_hash", event_hash)
            db.execute("COMMIT")
            return {**envelope, "event_hash": event_hash}
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def checkpoint(self) -> dict:
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            m = _meta(db)
            state_hash = digest(m["state"])
            db.execute("INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?)",
                       (m["revision"], canonical(m["state"]), state_hash, m["head_hash"]))
            db.execute("COMMIT")
            return {"revision": m["revision"], "state_digest": state_hash,
                    "event_hash": m["head_hash"]}
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def verify(self) -> dict:
        with self._connect() as db:
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise Conflict("SQLite integrity check failed")
            m = _meta(db)
            if (m["schema_version"], m["ruleset_version"], m["content_manifest_digest"]) != (
                    SCHEMA_VERSION, RULESET_VERSION, MANIFEST_DIGEST):
                raise Conflict("Version or manifest mismatch")
            state = initial_state()
            snapshots = {r: (json.loads(s), h, cursor) for r, s, h, cursor in
                         db.execute("SELECT revision,state_json,state_digest,event_hash FROM snapshots")}
            cursor = GENESIS_HASH
            if snapshots.get(0) != (state, digest(state), cursor):
                raise Conflict("Invalid genesis checkpoint")
            revision = 0
            for row_rev, event_id, payload, prev_hash, event_hash in db.execute(
                    "SELECT revision,event_id,envelope,prev_hash,event_hash FROM events ORDER BY revision"):
                envelope = json.loads(payload)
                if row_rev != revision + 1 or row_rev != envelope["committed_revision"]:
                    raise Conflict("Event sequence gap")
                if prev_hash != cursor or envelope["previous_event_hash"] != cursor:
                    raise Conflict("Broken event hash chain")
                if event_id != envelope["event_id"] or envelope["lab_id"] != m["lab_id"] or (
                        envelope["world_epoch"] != m["world_epoch"]):
                    raise Conflict("Event identity or epoch mismatch")
                if (envelope["schema_version"], envelope["ruleset_version"],
                    envelope["content_manifest_digest"]) != (
                        SCHEMA_VERSION, RULESET_VERSION, MANIFEST_DIGEST):
                    raise Conflict("Event contract mismatch")
                if envelope["base_revision"] != revision or envelope["before_digest"] != digest(state):
                    raise Conflict("Invalid source state")
                ids = affected_ids(envelope["action"])
                if envelope["preconditions"] != {i: state[i]["revision"] for i in sorted(ids)}:
                    raise Conflict("Invalid object preconditions")
                state = apply(state, envelope["action"], row_rev)
                if envelope["after_digest"] != digest(state) or event_hash != digest({
                        "previous_event_hash": cursor, "envelope": envelope}):
                    raise Conflict("Event/state hash mismatch")
                revision, cursor = row_rev, event_hash
                if revision in snapshots and snapshots[revision] != (state, digest(state), cursor):
                    raise Conflict("Corrupt or diverged checkpoint")
            if revision != m["revision"] or cursor != m["head_hash"] or state != m["state"]:
                raise Conflict("Materialized state does not match replay")
            if set(snapshots) - set(range(revision + 1)):
                raise Conflict("Snapshot from future revision")
            return {"verified": True, "lab_id": m["lab_id"],
                    "world_epoch": m["world_epoch"], "revision": revision,
                    "head_hash": cursor, "state_digest": digest(state),
                    "snapshots": len(snapshots)}

    def backup_to(self, destination: str | Path) -> dict:
        self.verify()
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(str(destination))
        # SQLite online backup handles WAL safely. Never copy the DB file directly.
        source = self._connect()
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
        except Exception:
            target.close()
            destination.unlink(missing_ok=True)
            raise
        finally:
            source.close()
            target.close()
        return Laboratory(destination).verify()

    @staticmethod
    def restore_to(backup: str | Path, destination: str | Path) -> dict:
        # Restore creates a separate database, never overwrites a live world.
        Laboratory(backup).verify()
        return Laboratory(backup).backup_to(destination)

    def start_offline(self, queue_path: str | Path) -> dict:
        self.verify()
        m = self.status()
        branch = {
            "branch_id": str(uuid.uuid4()), "lab_id": m["lab_id"],
            "world_epoch": m["world_epoch"], "schema_version": SCHEMA_VERSION,
            "ruleset_version": RULESET_VERSION, "content_manifest_digest": MANIFEST_DIGEST,
            "base_revision": m["revision"], "base_head_hash": m["head_hash"],
            "base_state": m["objects"], "proposals": [],
        }
        _atomic_json(Path(queue_path), branch, exclusive=True)
        return {k: v for k, v in branch.items() if k != "base_state"}

    @staticmethod
    def _queue(queue_path: str | Path) -> dict:
        return json.loads(Path(queue_path).read_text(encoding="utf-8"))

    @staticmethod
    def offline_state(queue_path: str | Path) -> dict:
        b = Laboratory._queue(queue_path)
        state = b["base_state"]
        for offset, p in enumerate(b["proposals"], 1):
            state = apply(state, p["action"], b["base_revision"] + offset)
        return state

    @staticmethod
    def stage_offline(queue_path: str | Path, action: dict) -> dict:
        path = Path(queue_path)
        branch = Laboratory._queue(path)
        if not isinstance(branch.get("proposals"), list):
            raise LabError("Malformed offline branch")
        ids = affected_ids(action)
        if not ids <= branch["base_state"].keys():
            raise LabError("Unknown object")
        # v0.1 intentionally disallows multiple staged writes to the same
        # object. A later version may track per-proposal causal dependencies.
        for prior in branch["proposals"]:
            if ids & set(prior["expected_versions"]):
                raise Conflict("Overlapping offline proposals need a new checkpoint")
        state = Laboratory.offline_state(path)
        apply(state, action, branch["base_revision"] + len(branch["proposals"]) + 1)
        proposed = {
            "event_id": str(uuid.uuid4()), "action": action,
            "expected_versions": {i: branch["base_state"][i]["revision"] for i in sorted(ids)},
            "status": "pending",
        }
        branch["proposals"].append(proposed)
        _atomic_json(path, branch)
        return proposed

    def reconcile(self, queue_path: str | Path) -> dict:
        path = Path(queue_path)
        branch = self._queue(path)
        m = self.status()
        if (branch["lab_id"], branch["world_epoch"], branch["schema_version"],
            branch["ruleset_version"], branch["content_manifest_digest"]) != (
                m["lab_id"], m["world_epoch"], SCHEMA_VERSION, RULESET_VERSION,
                MANIFEST_DIGEST):
            raise Conflict("Branch identity, epoch or version mismatch: quarantined")
        results = []
        for proposal in branch["proposals"]:
            if proposal["status"] != "pending":
                results.append({"event_id": proposal["event_id"], "status": proposal["status"]})
                continue
            try:
                event = self.commit(
                    proposal["action"], actor="pretorius_research",
                    event_id=proposal["event_id"],
                    expected_versions=proposal["expected_versions"],
                    origin_branch=branch["branch_id"],
                )
                proposal["status"] = "accepted_local"
                proposal["committed_revision"] = event["committed_revision"]
            except (Conflict, LabError) as exc:
                proposal["status"] = "conflicted"
                proposal["reason"] = str(exc)
            # Persist each outcome, so restart after a lost acknowledgement
            # replays an already accepted event with the same idempotency key.
            _atomic_json(path, branch)
            results.append({"event_id": proposal["event_id"], "status": proposal["status"],
                            "revision": proposal.get("committed_revision"),
                            "reason": proposal.get("reason")})
        return {"branch_id": branch["branch_id"], "outcomes": results}
