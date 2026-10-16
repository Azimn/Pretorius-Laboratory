"""Local, subject-facing-only Laboratory pilot commands.

Exposes *only* the returned first-person inner narrative and audible words.
This is not a Doctor-Lives brain integration or an operator audit console.
"""
import argparse
import json

from .habitat_v2 import SpatialHabitat
from .subject_port import SubjectPort
from .physics import Conflict, LabError


def main(argv=None):
    parser = argparse.ArgumentParser(description="First-person Pretorius Laboratory port")
    parser.add_argument("--db", required=True)
    sub = parser.add_subparsers(dest="op", required=True)
    for name in ("look", "light", "extinguish", "prepare_meal", "eat", "brew_tea",
                 "sleep", "rest", "clean", "experiment", "repair"):
        sub.add_parser(name)
    walk = sub.add_parser("walk")
    walk.add_argument("station")
    advance = sub.add_parser("advance")
    advance.add_argument("minutes", type=int)
    for name in ("open", "close"):
        sub.add_parser(name).add_argument("container")
    sub.add_parser("take").add_argument("item")
    put = sub.add_parser("put")
    put.add_argument("item")
    put.add_argument("container")
    stool = sub.add_parser("shift_stool")
    stool.add_argument("position", choices=("clear", "obstruct"))
    book = sub.add_parser("book")
    book.add_argument("operation", choices=("open", "close", "read", "turn",
                                           "mark", "unmark", "open_mark"))
    book.add_argument("book_id")
    book.add_argument("--direction", type=int)
    book.add_argument("--bookmark")
    meas = sub.add_parser("measure")
    meas.add_argument("instrument")
    meas.add_argument("object_id")
    meas.add_argument("quantity")
    sub.add_parser("take_book").add_argument("book_id")
    placed = sub.add_parser("put_book")
    placed.add_argument("book_id")
    placed.add_argument("anchor_id")
    args = parser.parse_args(argv)
    fields = vars(args)
    op = fields.pop("op")
    db = fields.pop("db")
    try:
        port = SubjectPort(SpatialHabitat(db))
        if op == "shift_stool":
            options = {"obstructs_path": fields["position"] == "obstruct"}
        elif op == "book":
            options = {"operation": fields["operation"], "book_id": fields["book_id"]}
            if fields["direction"] is not None:
                options["direction"] = fields["direction"]
            if fields["bookmark"] is not None:
                options["bookmark_id"] = fields["bookmark"]
        else:
            options = fields
        result = port.act(op, **options)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (LabError, Conflict, FileNotFoundError, ValueError, KeyError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
