"""Manual free-roam session: one JSON command per line, no model API.

Usage:
 python tools/run_free_roam_manual.py --world SANDBOX.sqlite3 --session first-evening --experimental-world --create-sandbox

Input commands (on stdin):
 {"op":"observe"}
 {"op":"act","turn_id":"t1","offer_id":"<from host offers>","event_id":"receipt-t1","intention":"I move the chair.","text":null}
 {"op":"unsupported","turn_id":"t2","intention":"I want to carve an ivory seal."}
 {"op":"narrative","turn_id":"t3","text":"I find my thoughts wandering."}
 {"op":"idle","turn_id":"t4"}
 {"op":"audit"}
 {"op":"quit"}

Output observation subject text is suitable for the stand-in; host keys are NOT
part of its first-person frame. The operator must not pass hidden engineering
state into the model's Pretorius perspective. Do not use on an inhabited DB.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.free_roam_pilot import FreeRoamPilot


def main():
    p = argparse.ArgumentParser(description="Sandbox-only stand-in Laboratory")
    p.add_argument("--world", type=Path, required=True)
    p.add_argument("--session", required=True)
    p.add_argument("--experimental-world", action="store_true",
                   help="Affirm that this is an expendable sandbox, not an inhabited DB")
    p.add_argument("--create-sandbox", action="store_true",
                   help="Create a brand-new isolated Laboratory at the requested missing path")
    args = p.parse_args()
    if not args.experimental_world:
        p.error("Explicit --experimental-world confirmation required")
    if args.create_sandbox and args.world.exists():
        p.error("Refusing to overwrite an existing physical world")
    if args.create_sandbox:
        from pretorius_lab.home_life import HomeLife
        from pretorius_lab.daily_rhythm import DailyRhythm
        from pretorius_lab.material_objects import MaterialObjects
        from pretorius_lab.home_arrangement import HomeArrangements
        from pretorius_lab.personal_projects import PersonalProjects
        args.world.parent.mkdir(parents=True, exist_ok=True)
        home = SpatialHabitat.create(args.world)
        HomeLife(home).initialize()
        DailyRhythm(home).initialize(
            perishable_meals=True, physical_provisions=True,
            visible_portions=True, physical_paper=True)
        MaterialObjects(home).initialize()
        HomeArrangements(home).initialize()
        PersonalProjects(home).initialize()
    if not args.world.is_file():
        p.error("Provide an existing sandbox or --create-sandbox")
    pilot = FreeRoamPilot(SpatialHabitat(args.world), args.session)
    print(json.dumps({"schema": "shadow-free-roam/1",
                      "message": "Input one JSON object per line. No model is running."}))
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            op = obj["op"]
            if op == "quit":
                break
            if op == "observe":
                result = pilot.observe()
            elif op == "act":
                result = pilot.act(
                    turn_id=obj["turn_id"], intention=obj["intention"],
                    offer_id=obj["offer_id"], event_id=obj["event_id"],
                    text=obj.get("text"))
            elif op == "unsupported":
                result = pilot.unsupported(
                    turn_id=obj["turn_id"], intention=obj["intention"],
                    reason=obj.get("reason", "No corresponding physical operation"))
            elif op == "narrative":
                result = pilot.narrative(
                    turn_id=obj["turn_id"], text=obj["text"],
                    kind=obj.get("kind", "ambient_impression"))
            elif op == "idle":
                result = pilot.idle(
                    turn_id=obj["turn_id"],
                    text=obj.get("text", "I choose not to act right now."))
            elif op == "recover":
                result = pilot.recover(obj["turn_id"])
            elif op == "audit":
                result = pilot.audit()
            else:
                raise ValueError("Unsupported command")
            print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
        except (ValueError, KeyError, TypeError) as exc:
            print(json.dumps({"ok": False, "error": str(exc)}))


if __name__ == "__main__":
    main()
