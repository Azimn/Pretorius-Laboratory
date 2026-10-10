"""Local research CLI. There is deliberately no HTTP or Village write endpoint."""
from __future__ import annotations

import argparse
import json

from .store import Laboratory
from .physics import LabError, Conflict

def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pretorius-lab", description="Permanent Pretorius research laboratory")
    p.add_argument("--db", default="data/pretorius-laboratory.sqlite3")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    sub.add_parser("verify")
    sub.add_parser("checkpoint")
    b = sub.add_parser("backup"); b.add_argument("destination")
    r = sub.add_parser("restore"); r.add_argument("backup"); r.add_argument("destination")
    act = sub.add_parser("act")
    act.add_argument("op", choices=("open", "close", "move", "advance_clock", "note"))
    act.add_argument("value", help="Object ID, ticks, or note text")
    act.add_argument("destination", nargs="?", help="Destination object ID for move")
    off = sub.add_parser("offline-start"); off.add_argument("queue")
    stage = sub.add_parser("offline-stage")
    stage.add_argument("queue")
    stage.add_argument("op", choices=("open", "close", "move", "advance_clock", "note"))
    stage.add_argument("value")
    stage.add_argument("destination", nargs="?")
    local = sub.add_parser("offline-state"); local.add_argument("queue")
    rec = sub.add_parser("reconcile"); rec.add_argument("queue")
    return p

def action(op: str, value: str, destination: str | None) -> dict:
    if op == "move":
        if not destination:
            raise LabError("move requires destination")
        return {"op": op, "object_id": value, "to_id": destination}
    if destination is not None:
        raise LabError("Unexpected destination")
    if op in {"open", "close"}:
        return {"op": op, "object_id": value}
    if op == "advance_clock":
        return {"op": op, "ticks": int(value)}
    return {"op": op, "text": value}

def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    lab = Laboratory(args.db)
    try:
        if args.command == "init":
            result = Laboratory.create(args.db).status()
        elif args.command == "status":
            result = lab.status()
        elif args.command == "verify":
            result = lab.verify()
        elif args.command == "checkpoint":
            result = lab.checkpoint()
        elif args.command == "backup":
            result = lab.backup_to(args.destination)
        elif args.command == "restore":
            result = Laboratory.restore_to(args.backup, args.destination)
        elif args.command == "act":
            result = lab.commit(action(args.op, args.value, args.destination))
        elif args.command == "offline-start":
            result = lab.start_offline(args.queue)
        elif args.command == "offline-stage":
            result = Laboratory.stage_offline(args.queue, action(args.op, args.value, args.destination))
        elif args.command == "offline-state":
            result = Laboratory.offline_state(args.queue)
        else:
            result = lab.reconcile(args.queue)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except (LabError, Conflict, FileNotFoundError, FileExistsError, ValueError, KeyError) as exc:
        parser().exit(2, f"laboratory error: {exc}\n")

if __name__ == "__main__":
    raise SystemExit(main())
