"""Create a disposable Doctor residency research world, not the canonical home.

Run with a NEW sqlite filename. This script never overwrites existing data.
The study engine and optional projects share the same world SQLite authority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pretorius_lab.book_library import BookLibrary
from pretorius_lab.daily_rhythm import DailyRhythm
from pretorius_lab.field_residency import ResidencyTrial
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.home_arrangement import HomeArrangements
from pretorius_lab.home_life import HomeLife
from pretorius_lab.material_objects import MaterialObjects
from pretorius_lab.personal_projects import PersonalProjects


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create a scratch, isolated Pretorius field trial")
    parser.add_argument("world", help="A new filename ending .sqlite3, not an inhabited world")
    parser.add_argument("--log", help="A new field-observation JSONL log")
    args = parser.parse_args(argv)
    destination = Path(args.world).resolve()
    if destination.exists():
        parser.error("The world already exists. Refusing to reset existing history")
    destination.parent.mkdir(parents=True, exist_ok=True)
    log = Path(args.log).resolve() if args.log else destination.with_suffix(".field.jsonl")
    if log.exists():
        parser.error("The field journal already exists. Refusing to change another study")
    world = SpatialHabitat.create(destination)
    HomeLife(world).initialize()
    DailyRhythm(world).initialize(
        perishable_meals=True, physical_provisions=True,
        visible_portions=True, physical_paper=True)
    HomeArrangements(world).initialize()
    MaterialObjects(world).initialize()
    PersonalProjects(world).initialize()
    BookLibrary(world).initialize()
    # Books must be installed with *real source-backed text* separately. Do
    # not invent a library edition or Doctor's personal memories at startup.
    trial = ResidencyTrial(world, log)
    print(json.dumps({
        "note": "Scratch research world created; no model or unattended scheduler started",
        "world": str(destination), "observer_log": str(log),
        "renderer_packet": trial.packet(),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
