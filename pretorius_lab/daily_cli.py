"""Local daily-life pilot CLI. This is NOT Pretorius's subjective telemetry port."""
from __future__ import annotations

import argparse
import json

from .daily_rhythm import DailyRhythm
from .habitat_v2 import SpatialHabitat
from .physics import Conflict, LabError


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Bounded domestic time, meals, light, rest and equipment maintenance")
    parser.add_argument("--db", required=True, help="Existing opt-in home spatial-v2 DB")
    sub = parser.add_subparsers(dest="op", required=True)
    for op in ("init", "verify", "audit", "look", "light", "extinguish",
               "prepare_meal", "eat", "brew_tea", "sleep", "rest",
               "clean", "experiment", "repair"):
        sub.add_parser(op)
    advance = sub.add_parser("advance")
    advance.add_argument("minutes", type=int)
    args = parser.parse_args(argv)
    try:
        life = DailyRhythm(SpatialHabitat(args.db))
        if args.op == "init":
            result = life.initialize()
        elif args.op == "verify":
            result = life.verify()
        elif args.op == "audit":
            result = life.audit_state()  # engineer-only, never subject access
        elif args.op == "advance":
            result = life.advance(args.minutes)
        else:
            result = life.act(args.op)
    except (LabError, Conflict, FileNotFoundError, ValueError) as exc:
        parser.exit(2, str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
