"""Local trusted-operator tool for source-backed book editions and physical bookmarks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .book_library import BookLibrary
from .habitat_v2 import SpatialHabitat
from .physics import Conflict, LabError


def main(argv=None):
    parser = argparse.ArgumentParser(description="Book interaction port for spatial habitat")
    parser.add_argument("--db", default="data/sanctum-v2.sqlite3")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("init")
    subs.add_parser("verify")
    catalog = subs.add_parser("catalog")
    catalog.add_argument("book_id", nargs="?")
    install = subs.add_parser("install")
    install.add_argument("book_id")
    install.add_argument("manifest_json")
    for op in ("open", "close", "read"):
        s = subs.add_parser(op)
        s.add_argument("book_id")
    turn = subs.add_parser("turn")
    turn.add_argument("book_id")
    turn.add_argument("direction", type=int, choices=(-1, 1))
    for op in ("mark", "unmark", "open_mark"):
        s = subs.add_parser(op)
        s.add_argument("book_id")
        s.add_argument("bookmark_id")
    args = parser.parse_args(argv)
    lib = BookLibrary(SpatialHabitat(args.db))
    try:
        if args.command == "init":
            out = lib.initialize()
        elif args.command == "verify":
            out = lib.verify()
        elif args.command == "catalog":
            out = lib.catalog(args.book_id)
        elif args.command == "install":
            source = json.loads(Path(args.manifest_json).read_text(encoding="utf-8"))
            if not isinstance(source, dict) or set(source) != {
                    "edition_id", "title", "author",
                    "pages", "source_class", "source_reference"}:
                raise LabError("Invalid installed book source manifest")
            out = lib.install(args.book_id, **source)
        elif args.command == "turn":
            out = lib.operate(args.book_id, "turn", direction=args.direction)
        elif args.command in ("mark", "unmark", "open_mark"):
            out = lib.operate(args.book_id, args.command,
                              bookmark_id=args.bookmark_id)
        else:
            out = lib.operate(args.book_id, args.command)
        print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (LabError, Conflict, ValueError, FileExistsError, FileNotFoundError,
            json.JSONDecodeError, KeyError) as exc:
        parser.exit(2, f"Book laboratory error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
