"""Opt-in standalone home fixture CLI; all returned subject text is first-person."""
from __future__ import annotations

import argparse
import json

from .embodied_access import EmbodiedAccess
from .habitat_v2 import SpatialHabitat
from .home_life import HomeLife
from .physics import Conflict, LabError


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Permanent Pretorius domestic habitat")
    parser.add_argument("--db", required=True, help="Existing spatial v2 SQLite world")
    sub = parser.add_subparsers(dest="op", required=True)
    for op in ("init", "verify", "look", "shop-manifest", "audit"):
        sub.add_parser(op)
    move = sub.add_parser("walk")
    move.add_argument("station")
    opened = sub.add_parser("open")
    opened.add_argument("container")
    closed = sub.add_parser("close")
    closed.add_argument("container")
    take = sub.add_parser("take")
    take.add_argument("item")
    put = sub.add_parser("put")
    put.add_argument("item")
    put.add_argument("container")
    stool = sub.add_parser("stool")
    stool.add_argument("position", choices=("clear", "obstruct"))
    args = parser.parse_args(argv)
    try:
        home = HomeLife(SpatialHabitat(args.db))
        if args.op == "init":
            data = home.initialize()
        elif args.op == "verify":
            data = home.verify()
        elif args.op == "look":
            data = home.look()
        elif args.op == "walk":
            data = home.walk(args.station)
        elif args.op == "open":
            data = home.open(args.container)
        elif args.op == "close":
            data = home.close(args.container)
        elif args.op == "take":
            data = home.take(args.item)
        elif args.op == "put":
            data = home.put(args.item, args.container)
        elif args.op == "stool":
            data = home.shift_stool(obstructs_path=args.position == "obstruct")
        elif args.op == "shop-manifest":
            data = home.shop_manifest()  # engineer-only, not subject frame
        else:
            data = home.audit_state()  # engineer-only
    except (Conflict, LabError, FileNotFoundError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")
    print(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
