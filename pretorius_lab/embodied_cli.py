"""Trusted local embodied laboratory interface; never exposes engineer-only geometry."""
from __future__ import annotations

import argparse
import json

from .embodied_access import EmbodiedAccess
from .habitat_v2 import SpatialHabitat
from .physics import Conflict, LabError


def main(argv=None):
    p = argparse.ArgumentParser(description="Position-constrained laboratory research subject")
    p.add_argument("--db", required=True, help="Preexisting spatial-v2 laboratory SQLite file")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("verify")
    sub.add_parser("look")
    sub.add_parser("init-custody")
    sub.add_parser("verify-custody")
    take = sub.add_parser("take")
    take.add_argument("book_id")
    put = sub.add_parser("put")
    put.add_argument("book_id")
    put.add_argument("destination")
    go = sub.add_parser("go")
    go.add_argument("station")
    book = sub.add_parser("book")
    book.add_argument("operation", choices=(
        "open", "close", "read", "turn", "mark", "unmark", "open_mark"))
    book.add_argument("book_id")
    book.add_argument("--direction", type=int, choices=(-1, 1))
    book.add_argument("--bookmark")
    args = p.parse_args(argv)
    actor = EmbodiedAccess(SpatialHabitat(args.db))
    try:
        if args.command == "init":
            result = actor.initialize()
        elif args.command == "verify":
            result = actor.verify()
        elif args.command == "look":
            result = actor.look()
        elif args.command == "init-custody":
            from .book_custody import BookCustody
            result = BookCustody(actor.habitat).initialize()
        elif args.command == "verify-custody":
            from .book_custody import BookCustody
            result = BookCustody(actor.habitat).verify()
        elif args.command == "take":
            result = actor.take(args.book_id)
        elif args.command == "put":
            result = actor.put(args.book_id, args.destination)
        elif args.command == "go":
            result = actor.move(args.station)
        else:
            result = actor.book(args.book_id, args.operation,
                                direction=args.direction,
                                bookmark_id=args.bookmark)
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (Conflict, LabError, FileNotFoundError, ValueError) as exc:
        p.exit(2, f"Embodied laboratory error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
