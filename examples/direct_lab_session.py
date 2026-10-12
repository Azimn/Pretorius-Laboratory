"""Model-free direct visit to the real persistent laboratory, with auditable evidence.

python examples/direct_lab_session.py --output /tmp/direct-lab
Only fresh synthetic research worlds are created. No canonical Pretorius brain,
production saved character, or Frankenstein Village state is touched.
"""
import argparse
import json
from pathlib import Path
import shutil
import sqlite3

from pretorius_lab import Conflict, LabError
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.embodied_access import EmbodiedAccess
from pretorius_lab.book_custody import BookCustody
from pretorius_lab.book_library import BookLibrary
from pretorius_lab.physical_affordances import PhysicalAffordances
from pretorius_lab.bench_instruments import BenchInstruments
from pretorius_lab.bench_liquids import BenchLiquids

PAGES = (
    "The laboratory record states the vessel was intact at first inspection.",
    "The second record says a balance yields bounded observations, not certain truth.",
)


def check(ok, message):
    if not ok:
        raise AssertionError(message)


def run(root):
    if root.exists() and any(root.iterdir()):
        raise FileExistsError("Refusing to overwrite previous lab session")
    root.mkdir(parents=True, exist_ok=True)
    trace = []

    def record(action, outcome, authority="research-subject", evidence=None):
        item = {"action": action, "outcome": outcome, "authority": authority,
                "evidence": evidence or {}}
        trace.append(item)
        print(f"[{len(trace):02d}] {authority}: {action} -> {outcome}", flush=True)

    lab = SpatialHabitat.create(root / "visit-world.sqlite3")
    books = BookLibrary(lab)
    books.initialize()
    books.install(
        "book:007", edition_id="direct-fixture-20261012",
        title="A Small Laboratory Record", author="Synthetic Test Scribe",
        pages=list(PAGES), source_class="original_fixture",
        source_reference="Synthetic test pages; not Pretorius autobiography")
    actor = EmbodiedAccess(lab)
    actor.initialize()
    custody = BookCustody(lab)
    custody.initialize()
    physical = PhysicalAffordances(lab)
    physical.initialize()
    instruments = BenchInstruments(lab)
    instruments.initialize()
    liquids = BenchLiquids(lab)
    liquids.initialize()
    record("Initialize scene and source text", "verified",
           "engineer-setup", {"source": "synthetic_fixture"})

    def revisions():
        return (lab.verify()["revision"], actor.verify()["revision"],
                custody.verify()["revision"], books.verify()["revision"],
                instruments.verify()["revision"], liquids.verify()["revision"])

    def reject(action, callback):
        before = revisions()
        try:
            callback()
        except (Conflict, LabError) as error:
            check(before == revisions(), "Rejected operation changed history: " + action)
            record(action, "REJECTED without mutation",
                   evidence={"exception": type(error).__name__})
            return
        raise AssertionError("Unauthorized operation accepted: " + action)

    doorway = actor.look()["offered_payload"]
    check(doorway["location"]["station"] == "station:threshold", "Wrong start")
    check(not doorway["nearby_objects"] and not doorway["available_instruments"],
          "Distant objects/instruments leaked at doorway")
    record("Look at the room from the threshold", "no distant title or instrument access")
    reject("Read a book without approaching", lambda: actor.book("book:007", "open"))
    reject("Teleport directly to third shelf", lambda: actor.move("station:shelf:3"))

    actor.move("station:center")
    actor.move("station:bench")
    scene = actor.look()["offered_payload"]
    check(scene["available_instruments"] == ["ruler:bench", "balance:bench"],
          "Bench tools not locally visible")
    for private in ("xyz_mm", "profile_digest", "max_carry_mass_g", "mass_g"):
        check(private not in json.dumps(scene), "Privileged state leaked: " + private)
    b1 = actor.measure("balance:bench", "beaker:001", "mass_g",
                       event_id="direct-beaker-weight")
    b2 = actor.measure("balance:bench", "beaker:001", "mass_g",
                       event_id="direct-beaker-weight")
    check(b1 == b2 and instruments.verify()["revision"] == 1, "Idempotency broken")
    check(b1["observation"]["value"] == 325 and
          b1["observation"]["interval"] == [312, 338], "Unexpected fixture reading")
    record("Weigh beaker and repeat event ID",
           "325 g, bounded interval; duplicate does not create new reading",
           evidence=b1["observation"])
    reject("Weigh distant book", lambda:
           actor.measure("balance:bench", "book:007", "mass_g"))
    actor.liquid("fill", 100)
    wet = actor.measure("balance:bench", "beaker:001", "mass_g")
    check(wet["observation"]["value"] == 425,
          "Conserved 100 ml of water did not add 100 g to the balance")
    check(actor.look()["offered_payload"]["beaker_water_level"] == "about half full",
          "Wet beaker not visible qualitatively at the workbench")
    record("Fill beaker with 100 ml of finite water and reweigh",
           "425 g measured rather than the prior 325 g")
    reject("Overfill 100 ml water in 250 ml vessel with 250 ml more",
           lambda: actor.liquid("fill", 250))
    reject("Pour 200 ml of water from only 100 ml held",
           lambda: actor.liquid("pour", 200))
    actor.liquid("pour", 50)
    partially_filled = actor.measure("balance:bench", "beaker:001", "mass_g")
    check(partially_filled["observation"]["value"] == 375,
          "50 ml retained water did not produce the expected bounded mass")
    check(liquids.audit_engineer_only() ==
          {"reservoir_ml": 900, "beaker_ml": 50, "basin_ml": 50},
          "Water disappeared during first material transfer")
    record("Decant 50 ml to a stationary collecting basin",
           "375 g remains on scale; 1000 ml is conserved")

    # Unlike the original experiment, no engineer moves the beaker.
    # The research subject frees the only bench position with its own hands.
    picked = actor.take_apparatus("beaker:001", event_id="subject-beaker-pickup")
    check(picked["location"]["held_by"] == "research-subject:pretorius",
          "Beaker is not physically carried")
    check(lab.scan("bench:main")["positions"][0]["occupant"] is None,
          "Taking apparatus did not vacate the workbench")
    record("Take intact beaker from bench",
           "bench is truly free; held beaker is a subject-owned object")
    reject("Weigh beaker while carried",
           lambda: actor.measure("balance:bench", "beaker:001", "mass_g"))
    actor.move("station:center")
    actor.move("station:shelf:3")
    reject("Take a book while still holding the beaker",
           lambda: actor.take("book:007"))
    actor.move("station:center")
    actor.move("station:corner:se")
    actor.put_apparatus("beaker:001", "floor:corner:se",
                        event_id="subject-beaker-setdown")
    check(lab.locate("beaker:001")["location"]["fixture"] == "floor:sanctum",
          "Subject did not physically place the beaker on the floor")
    record("Carry and set the beaker down in the southeast corner",
           "valid subject-only placement, no engineer relocation")
    actor.move("station:center")
    actor.move("station:shelf:3")
    check(actor.look()["offered_payload"]["nearby_objects"][6]["object_id"] == "book:007",
          "Book not present on third shelf")
    actor.book("book:007", "open")
    leaf = actor.book("book:007", "read")
    check(leaf["page_text"] == PAGES[0], "First leaf not source-backed")
    actor.book("book:007", "turn", direction=1)
    actor.book("book:007", "mark", bookmark_id="silver-paper")
    actor.book("book:007", "close")
    record("Read, turn, mark and close book", "source leaf 1, bookmark at leaf 2")
    actor.take("book:007")
    check(lab.scan("shelf:3")["positions"][6]["occupant"] is None,
          "Picked-up book still physically on shelf")
    check(lab.locate("book:007")["location"]["placement"] == "carried",
          "Book not carried")
    record("Take the book from its shelf", "vacant shelf and real custody")
    reject("Take a second book while holding the first",
           lambda: actor.take("book:006"))

    actor.move("station:center")
    actor.move("station:bench")
    actor.put("book:007", "bench:main/position:left")
    check(lab.scan("bench:main")["positions"][0]["occupant"]["id"] == "book:007",
          "Book not physically on bench")
    check(not actor.look()["offered_payload"]["held_objects"],
          "Book still reported in hand")
    record("Place volume on bench", "occupied bench changed only after clearance")
    mass = actor.measure("balance:bench", "book:007", "mass_g")
    width = actor.measure("ruler:bench", "book:007", "width_mm")
    check(mass["observation"]["unit"] == "g" and
          width["observation"]["unit"] == "mm" and
          instruments.verify()["revision"] == 5, "Wrong instrument ledger")
    record("Measure the book", "bounded source-labelled mass and width",
           evidence={"mass": mass["observation"], "width": width["observation"]})
    reject("Measure beaker after removal",
           lambda: actor.measure("balance:bench", "beaker:001", "mass_g"))

    # Test reverse-order collision without any privileged object placement:
    # the book remains on the workbench while the subject brings the beaker
    # back and tries to put it in the same occupied position.
    actor.move("station:center")
    actor.move("station:corner:se")
    actor.take_apparatus("beaker:001")
    actor.move("station:center")
    actor.move("station:bench")
    reject("Put carried beaker onto the book's occupied bench position",
           lambda: actor.put_apparatus("beaker:001", "bench:main/position:left"))
    actor.move("station:center")
    actor.move("station:corner:se")
    actor.put_apparatus("beaker:001", "floor:corner:se")
    actor.move("station:center")
    actor.move("station:bench")
    record("Return beaker to floor after failed double-occupancy",
           "no privileged intervention; book remains undisturbed on bench")

    # Recreate both handles; no Python object state is reused.
    reopen = SpatialHabitat(lab.path)
    recovered_actor = EmbodiedAccess(reopen)
    check(recovered_actor.verify()["station"] == "station:bench",
          "Actor position did not persist")
    recovered_actor.book("book:007", "open_mark", bookmark_id="silver-paper")
    recovered = recovered_actor.book("book:007", "read")
    check(recovered["page_text"] == PAGES[1], "Bookmark lost its actual second leaf")
    record("Reopen the body and the saved page", "bench position and leaf 2 restored",
           evidence={"leaf": recovered["page"]})

    lab.checkpoint()
    backup_path = root / "visit-backup.sqlite3"
    lab.backup_to(backup_path)
    backup = SpatialHabitat(backup_path)
    check(backup.locate("book:007")["location"]["fixture"] == "bench:main",
          "Backup lost the book")
    check(BenchInstruments(backup).verify()["revision"] == 5,
          "Backup lost readings")
    check(BenchLiquids(backup).audit_engineer_only() ==
          {"reservoir_ml": 900, "beaker_ml": 50, "basin_ml": 50},
          "Backup failed to preserve conserved water")
    check(BookLibrary(backup).catalog("book:007")["book:007"]["bookmarks"] ==
          {"silver-paper": 2}, "Backup lost the bookmark")
    record("Backup and independently reopen persisted world",
           "book pose, source bookmark and measurements preserved",
           "independent-verifier")

    fork_path = root / "visit-fork.sqlite3"
    lab.fork_to(fork_path)
    fork = SpatialHabitat(fork_path)
    child = EmbodiedAccess(fork)
    check(child.verify()["station"] == "station:bench", "Fork pose lost")
    check(BenchInstruments(fork).verify()["revision"] == 0,
          "Parent sensory offers fabricated as new experiences in fork")
    check(BenchLiquids(fork).verify()["revision"] == 0,
          "Fork falsely counts parent material transfers as new acts")
    check(BenchLiquids(fork).audit_engineer_only()["beaker_ml"] == 50,
          "Fork failed to copy actual contained water")
    check(fork.verify()["world_epoch"] != lab.verify()["world_epoch"],
          "Fork inherited the parent's epoch")
    child.take("book:007")
    child.move("station:center")
    child.move("station:shelf:3")
    child.put("book:007", "shelf:3/slot:7")
    check(fork.locate("book:007")["location"]["fixture"] == "shelf:3",
          "Fork failed to move the volume")
    check(lab.locate("book:007")["location"]["fixture"] == "bench:main",
          "Fork mutated parent placement")
    record("Return the volume only in a forked experiment",
           "distinct histories, parent still has its original bench placement",
           "independent-verifier")

    damage = SpatialHabitat.create(root / "damage-world.sqlite3")
    damage.commit({"op": "break", "object_id": "beaker:001"})
    try:
        damage.commit({"op": "place", "object_id": "beaker:001",
                       "anchor_id": "floor:corner:nw"})
    except LabError:
        pass
    else:
        raise AssertionError("Scattered glass moved without collection")
    check(damage.verify()["revision"] == 1, "Denied shards movement wrote history")
    damage.commit({"op": "collect", "object_id": "beaker:001"})
    damage.commit({"op": "place", "object_id": "beaker:001",
                   "anchor_id": "floor:corner:nw"})
    check(damage.locate("beaker:001")["condition"] == "broken",
          "Moving glass magically repaired it")
    record("Break, collect and relocate glass",
           "uncollected shards immobile; damage retained",
           "engineer-controlled-simulation")

    corrupted = root / "tamper-disposable.sqlite3"
    shutil.copy2(backup_path, corrupted)
    with sqlite3.connect(corrupted) as db:
        db.execute("UPDATE instrument_events SET event_hash=? WHERE revision=1",
                   ("f" * 64,))
    try:
        BenchInstruments(SpatialHabitat(corrupted)).verify()
    except Conflict:
        pass
    else:
        raise AssertionError("Forged instrument hash was accepted")
    corrupted.unlink()
    record("Tamper with disposable measurement history",
           "verification rejected the forgery", "independent-verifier")

    checks = {
        "world": lab.verify()["verified"],
        "embodiment": actor.verify()["verified"],
        "book": books.verify()["verified"],
        "custody": custody.verify()["verified"],
        "mechanics": physical.verify()["verified"],
        "instruments": instruments.verify()["verified"],
        "liquids": liquids.verify()["verified"],
        "backup": backup.verify()["verified"],
        "fork": fork.verify()["verified"],
        "damage": damage.verify()["verified"],
    }
    check(all(checks.values()), "A verification gate failed")
    result = {
        "schema": "pretorius-lab-model-free-direct-session/2",
        "status": "PASS", "steps": trace, "checks": checks,
        "denied_actions": sum(x["outcome"].startswith("REJECTED") for x in trace),
        "method": "fully_scripted_subject_actions_no_engineer_physical_intervention",
        "canonical_character_modified": False, "village_modified": False,
        "parent_book_location": lab.locate("book:007")["location"]["fixture"],
        "fork_book_location": fork.locate("book:007")["location"]["fixture"],
        "original_measurements": instruments.verify()["revision"],
        "conserved_inventory_ml": sum(liquids.audit_engineer_only().values()),
        "water_remaining_in_beaker_ml": liquids.audit_engineer_only()["beaker_ml"],
        "fork_new_measurements": BenchInstruments(fork).verify()["revision"],
        "limitations": [
            "No language model or Pretorius brain selected the actions",
            "Fixture pages, water density and physical assumptions are synthetic",
            "Fixed tap and collecting basin have finite discrete capacity, not simulated plumbing",
            "The actor moved the beaker directly, using the existing custody ledger",
            "Discrete simulated stations and noncontinuous physics only",
        ],
    }
    (root / "direct-session-report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("DIRECT_SIMULATION_RESULT " + json.dumps({
        "status": result["status"], "steps": len(trace),
        "denied_actions": result["denied_actions"], "checks": checks,
        "parent_book_location": result["parent_book_location"],
        "fork_book_location": result["fork_book_location"],
    }, sort_keys=True), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.output.resolve())


if __name__ == "__main__":
    main()
