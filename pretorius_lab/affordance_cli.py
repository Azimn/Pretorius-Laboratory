"""Engineer-only mechanical assumptions CLI (never a subject cognition port)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .physical_affordances import PhysicalAffordances
from .habitat_v2 import SpatialHabitat
from .physics import LabError, Conflict


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Engineer-only synthetic dimensions/mass for a persistent lab")
    p.add_argument("--db", required=True)
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--profile", help="Explicit engineered JSON assumptions; not measured")
    sub.add_parser("verify")
    sub.add_parser("inspect-engineer")
    args = p.parse_args(argv)
    profile = PhysicalAffordances(SpatialHabitat(args.db))
    try:
        if args.command == "init":
            config = (json.loads(Path(args.profile).read_text(encoding="utf-8"))
                      if args.profile else None)
            result = profile.initialize(profile=config)
        elif args.command == "verify":
            result = profile.verify()
        else:
            result = profile.inspect_engineer_only()
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except (LabError, Conflict, ValueError, FileNotFoundError) as exc:
        p.exit(2, f"Mechanical laboratory error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
