# Bench Ruler and Balance: Persistent Instrumented Observation (2026-10-10)

## Implementation

This milestone adds **two fixed, bench-integrated instruments** to the existing persistent laboratory: \`ruler:bench\` and \`balance:bench\`. They are integrated components of the existing workbench fixture, with its single \`bench:main/position:left\` measurement spot, **not** independent newly registered movable physical objects. No new room, source book, character architecture or Village portal has been added.

The instrument layer is an **opt-in** \`BenchInstruments\` append-only SQLite evidence ledger. It requires an initialized spatial-v2 world, actor position, effective physical custody and immutable mechanical-affordance profile. Instruments are only listed under \`available_instruments\` in the subject's local bench look. From elsewhere in the laboratory, the character is not offered either bench instrument.

The actor must stand at \`station:bench\` with the measured object physically placed (not still carried) at \`bench:main/position:left\`. Measuring does not move objects, learn dimensions automatically, or open the book. All instrument interactions use an authorized local command. Measurement results are distinct from engineer-only raw material dimensions, which the character cannot see through its view port.

## Source class and calibration contract

All simulated measurements are derived from the **declared synthetic mechanical profile**. Neither the book bindings nor Pretorius's body have been externally measured. A ruler or balance cannot turn synthetic assumptions into empirical historical evidence.

| Instrument | Quantities | Resolution | Bounded uncertainty |
| --- | --- | --- | --- |
| Bench ruler | width, height, depth | 5 mm | ±3 mm |
| Bench balance | mass | 25 g | ±13 g |

A deterministic integer half-up quantizer produces a simulated readout. The reported \`[low,high]\` interval includes the source fixture value, and the result is tagged \`synthetic_calibrated_fixture_not_real_measurement\`. There is no Gaussian noise model, stochastic instrument error, human misreading, psychometric perceptual guarantee, historical edition calibration or quantified systematic drift. Apparatus assumptions have a fixed, hash-verified calibration profile, not operator-editable readings.

As a concrete test, the original synthetic book's host-only thickness of 42 mm is reported by the ruler as **40 mm ±3 mm**, not the host's private 42 mm. The synthetic 330 g beaker is shown on the balance as **325 g ±13 g**. The actor may reasonably infer an interval, not a divine exact value. The offer of a reading is **not** proof a cognitive renderer attended to, understood or remembered it.

## Actions

~~~bash
# Use a NEW test database or the current initialized laboratory after its
# persistent actor, custody and mechanical profile are verified.
python -m pretorius_lab.embodied_cli --db data/laboratory.sqlite3 init-instruments
python -m pretorius_lab.embodied_cli --db data/laboratory.sqlite3 go station:center
python -m pretorius_lab.embodied_cli --db data/laboratory.sqlite3 go station:bench
python -m pretorius_lab.embodied_cli --db data/laboratory.sqlite3 look
# The original beaker occupies the bench spot on a fresh fixture.
python -m pretorius_lab.embodied_cli --db data/laboratory.sqlite3 measure balance:bench beaker:001 mass_g
python -m pretorius_lab.embodied_cli --db data/laboratory.sqlite3 measure ruler:bench beaker:001 height_mm
python -m pretorius_lab.embodied_cli --db data/laboratory.sqlite3 verify-instruments
~~~

A book must be moved onto the bench with the **existing custody take/put actions**, after clearing the original beaker. Only then can its mass or width be measured. A held object cannot be weighed, and a distant shelf cannot be measured from the bench by naming its book ID. Measuring an unprofiled object or requesting mass from the ruler is rejected.

### Auditable measurement receipts

The accepted \`instrument_events\` record binds: subject ID and actual bench position event, world ID/epoch, physical world revision/hash, annex revision/hash, custody revision/hash, immutable mechanical-profile digest, fixed device-calibration digest, instrument/quantity, object identity, stable bench anchor, event identifier, quantized bounded reading, and a hash-chained predecessor. An event ID retry returns the same historical measurement even if the original book has been moved elsewhere. Reusing that event ID for a different object or quantity fails.

Verification checks event hashes and source world/custody event cursors, reconstructs the **historical location at the measurement** (rather than using current object location), confirms the actual measured object was admitted into the laboratory at that time, confirms bench pose, and independently recalculates the expected readout. Changing the reported reading and recomputing its hash is insufficient to forge a valid instrument reading. As with other local SQLite ledgers, a malicious operator with unrestricted filesystem/code control is not excluded by these checks; this is an internal audit consistency layer, **not tamperproof cryptography**.

Backup stores the complete instrument event history and verifies the copied database. A sandbox fork preserves the inherited physical world, profile and calibration and a provenance reference to the parent measurement cursor, but starts with **zero local measurement events**. It does not claim the child subject previously made or experienced the parent's observations. New readings in the fork are recorded under its own epoch.

## Limits, interpretation and next experiment

The devices are fixed, synthetic fixtures; they do not have new object identities or consume additional bench occupancy. There is no material stress, slipping instruments, physical measurement tool pickup, exact 3D contact simulation, instrument calibration procedure with real reference weights, sight/lighting obstruction, human reading error, probabilistic accuracy, or unit-traceable real source measurements. Measurements are **subject-visible offers**, not autobiographical memories.

The next decisive cognitive test is now available for a *production* Pretorius integration:

1. Request a pre-observation guess of the mass or thickness of a known volume.
2. Require authorized spatial movement, book handling and actual instrument action.
3. Admit only the bounded instrument readout through a subject-access gate, never raw host calibration or exact values.
4. At a later step, ask whether Pretorius recalls the observed interval, distinguishes it from his guess, and updates subsequent shelf/carrying plans.
5. Use a withheld-measurement control and a fresh-seeded experiment fork. Score changed physical decisions and calibration, not performance at repeating prompt text.

The current module establishes the **measurement apparatus and source boundary**, not autonomous agency, subjective experience or an experimentally demonstrated advantage for Pretorius.
