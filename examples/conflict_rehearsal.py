"""Demonstrate one persistent scene and an explicit offline conflict."""
from pathlib import Path
import tempfile

from pretorius_lab import Laboratory


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        host = Laboratory.create(root / "permanent.sqlite3")
        offline = root / "pretorius-offline.json"
        host.start_offline(offline)
        staged = Laboratory.stage_offline(
            offline, {"op": "move", "object_id": "container:specimen", "to_id": "room:main"}
        )
        # A second actor changes the canonical object's location first.
        host.commit({"op": "move", "object_id": "container:specimen", "to_id": "room:main"})
        outcome = host.reconcile(offline)
        assert outcome["outcomes"][0]["status"] == "conflicted"
        assert host.verify()["revision"] == 1
        print({"offline_proposal": staged["event_id"],
               "result": outcome["outcomes"][0]["status"],
               "authoritative_revision": host.status()["revision"],
               "specimen_container_location":
                   host.status()["objects"]["container:specimen"]["location"]})


if __name__ == "__main__":
    main()
