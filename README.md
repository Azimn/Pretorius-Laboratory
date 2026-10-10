# Pretorius Laboratory

**An enduring place for experiments, not a disposable test fixture.**

Pretorius Laboratory is a standalone, low-cost Python/SQLite research habitat. Laboratory objects, experiments, snapshots and physical consequences persist independently of the model speaking for Pretorius and independently of Frankenstein Village.

This is **research software v0.1**, not a deployed Village location, a network-synchronized simulation or a replacement for Pretorius's cognitive system.

## One laboratory, two eventual representations

The authority is a persistent external laboratory ledger. A private research process interacts with the scene through typed operations; a future Evennia projection may present only explicitly approved, authenticated and Village-authorized effects. The offline copy produces provisional proposals, not a second source of world truth. For now, **only the local authority and offline rehearsal exist**.

An object retains its stable identity across reopening, snapshots, and restored backups. Experiments advance a local clock, and each accepted action creates an idempotent, revisioned, hash-chained record. Deterministic replay checks whether the live scene can actually be reconstructed from its declared history.

## Requirements and first run

Python 3.10 or newer. All runtime dependencies are in the standard library. Commands may be run directly from the cloned repository.

\`\`\`bash
python -m pretorius_lab --db data/laboratory.sqlite3 init
python -m pretorius_lab --db data/laboratory.sqlite3 status
python -m pretorius_lab --db data/laboratory.sqlite3 observe
python -m pretorius_lab --db data/laboratory.sqlite3 act open container:specimen
python -m pretorius_lab --db data/laboratory.sqlite3 act move specimen:alpha bench:main
python -m pretorius_lab --db data/laboratory.sqlite3 act advance_clock 12
python -m pretorius_lab --db data/laboratory.sqlite3 act note "A vessel opened; specimen transferred."
python -m pretorius_lab --db data/laboratory.sqlite3 checkpoint
python -m pretorius_lab --db data/laboratory.sqlite3 verify
\`\`\`

The read-only `observe` command provides a host-verified, machine-readable scene for future cognition adapters. A sealed container hides its contents until opened; notebook entries are never included in this perception payload. The observation includes a lab identity, world epoch, event cursor and provenance class, plus legal action examples computed by the authoritative physics reducer. An observation is not automatically a lived memory or a claim that Pretorius is present.

The same database can be reopened in the next session without reinitialization. The open/close, move, clock and notebook operations are constrained by fixed physical rules. There is no arbitrary state write verb.

## Offline episode and reconciliation

\`\`\`bash
python -m pretorius_lab --db data/laboratory.sqlite3 offline-start data/offline.json
python -m pretorius_lab --db data/laboratory.sqlite3 offline-stage data/offline.json advance_clock 5
python -m pretorius_lab --db data/laboratory.sqlite3 offline-state data/offline.json
python -m pretorius_lab --db data/laboratory.sqlite3 reconcile data/offline.json
\`\`\`

The offline episode remains a separate JSON branch. Its state is provisional. At reconciliation, changes to affected objects are checked against the current committed state, so a specimen vessel moved by another actor is **rejected as a conflict** rather than copied or overwritten. Nonoverlapping valid changes may be accepted locally. Multi-step dependent offline writes and conflicts requiring negotiation are deliberately not auto-merged.

For the conflict example:

\`\`\`bash
python examples/conflict_rehearsal.py
\`\`\`

## Checkpoints, recovery and testing

\`\`\`bash
python -m pretorius_lab --db data/laboratory.sqlite3 backup backups/laboratory-copy.sqlite3
python -m pretorius_lab restore backups/laboratory-copy.sqlite3 data/restored.sqlite3
python -m unittest discover -s tests -v
\`\`\`

The backup command uses SQLite's consistent online backup API and verifies the copied file by replay. Restoration creates a separate database and refuses to overwrite an existing path. Operators must copy backups off-host separately. There is no destructive reset operation.

## Scope and integration safeguards

The current CLI trusts its local operator. It has **no network authentication, cryptographic signatures, remote sync, Village bridge, public event publication, or third-party consent layer**. Every laboratory event is marked research-private. Do not expose this host or offline queue to untrusted network clients. A hash chain detects internal corruption but is not proof against a malicious filesystem operator.

The Doctor Lives remains responsible for Pretorius's identity and cognition. This environment must not silently fabricate first-person world memories from offline experiments. Frankenstein Village retains authority over players, masks, rooms, doors, consent and its event ledger. The existing dark leased shop with its OPENING SOON sign remains untouched. No user-facing room, automatic Pretorius arrival or invited-alpha scope change is implied.

See [Executable architecture and trust contract](docs/ARCHITECTURE.md), [The Doctor Lives tracking issue #46](https://github.com/Azimn/The-Doctor-Lives/issues/46), and [Frankenstein Village tracking issue #48](https://github.com/Azimn/frankenstein-village/issues/48).

The next step after this foundation is source-level parity with Stage 04, plus a rigorously authenticated and explicitly non-public shadow projection. Until that review, there is no claim of direct Stage 04 compatibility or synchronized game integration.
