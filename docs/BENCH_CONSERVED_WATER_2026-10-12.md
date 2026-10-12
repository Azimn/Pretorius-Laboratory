# Bench water conservation: standalone physical experiment

**Date:** October 12, 2026
**Research stage:** discrete synthetic liquid v0.1; entirely separate from the Pretorius decision/identity stack.
**Dependency:** subject-controlled apparatus PR #20. The new system does not promote the world into The-Doctor-Lives or Village.

## Hypothesis and falsifiers

An independently operated laboratory should keep physical quantities consistent across separate actions, measurements, restarts and experimental forks. Water entering an existing beaker should measurably increase the beaker's mass, leave its finite source depleted, and reappear in a fixed collection basin when poured. An old measurement should remain historically verifiable after liquid transfers or object movement.

Fail the simulator if a fill or pour creates/erases liquid volume, exceeds a vessel's capacity, succeeds remotely, interacts with a carried/broken beaker, produces the same measured mass in empty and filled cases, changes a previous measured value, or misattributes parent-world experimental history to a fork.

## Implemented environment

The existing permanent bench gets two stationary, nonportable service fixtures: a sealed source reservoir with a declared initial 1,000 mL of water and a 1,000 mL collecting basin. The existing beaker can contain up to 250 mL. Transfer commands fill beaker from reservoir or pour from beaker into basin. Values are integer multiples of 25 mL. There is no infinite tap, random magic refill or silent reset.

Liquid density is deliberately **declared synthetic 1 g/mL**, not a lab-measured chemistry result. A filled beaker's total mass is its original synthetic dry mass plus contained water. The existing calibrated balance is consulted through the same prior authorized method, but its readout is now derived from **historical** material volume at the moment of measurement, respecting the previous 25 g quantization and 13 g uncertainty interval. The older pre-liquid instrument events replay unchanged as dry-beaker measurements. New instrument receipts bind their source liquid cursor and revision.

At the bench, a subject-facing look presents only qualitative water levels and available fill/pour actions. Exact reservoir, beaker and basin volumes remain in a separate engineer-only audit. A transfer receipt describes an offered event; it does not claim the character attended, understood or remembered it.

The existing custody rules control the actual mobile beaker. Water mass counts toward actor lift capacity and placement support, including at the time a beaker is moved. Liquid transfers are denied unless the intact beaker is physically at the bench and the actor is at the bench. Breaking a filled beaker is forbidden until an explicit spill mechanism exists, rather than silently deleting water.

## World integrity

A separate append-only liquid event chain binds world epoch, subject ID, accepted pose, physical world event cursor, effective custody event cursor, frozen profile digest and source volumes before and after each transfer. Every event is replayed against immutable capacity and conservation rules. A repeated event ID is idempotent and conflicting reuse fails closed.

Verifiable SQLite backups retain exact contained water and readout history. A fork inherits the latest finite inventory as initial world state in a distinct epoch, with **zero newly claimed material events** and **zero newly claimed sensory instrument offers**. These are separate from the parent ledger's historical actions.

## Repeat the experiment

From repository root on Python 3.10 or later, using no downloaded AI model and no external API:

    python examples/direct_lab_session.py --output /tmp/bench-water-direct

The direct session initializes source-backed synthetic physical fixtures, weighs the empty beaker (325 g), transfers 100 mL (425 g), pours 50 mL (375 g), then actually carries the still-partly-filled beaker away and uses the freed bench to weigh a book. It refuses impossible quantities and tests exact physical occupancy, then verifies replay, backup and fork independence.

Alternatively, with a new SQLite world initialized through the preexisting spatial, embodied, custody and mechanical CLIs:

    python -m pretorius_lab.embodied_cli --db /tmp/new-lab.sqlite3 init-liquids
    python -m pretorius_lab.embodied_cli --db /tmp/new-lab.sqlite3 go station:center
    python -m pretorius_lab.embodied_cli --db /tmp/new-lab.sqlite3 go station:bench
    python -m pretorius_lab.embodied_cli --db /tmp/new-lab.sqlite3 liquid fill 100
    python -m pretorius_lab.embodied_cli --db /tmp/new-lab.sqlite3 measure balance:bench beaker:001 mass_g
    python -m pretorius_lab.embodied_cli --db /tmp/new-lab.sqlite3 liquid pour 50
    python -m pretorius_lab.embodied_cli --db /tmp/new-lab.sqlite3 verify-liquids

The new world must already have its actor, physical custody and immutable synthetic mechanical profiles initialized before init-liquids.

## Deliberate limitations

This is not computational fluid dynamics, hydrodynamics, chemistry, vaporization, toxicity, temperature, spill physics, physical glass pouring animation, genuine volumetric measurement or a model of real Victorian laboratory plumbing. Stationary reservoirs are finite but have no animated geometry. The water mass/density/capacity and balance calibration are sourced from declared engineering fixture constants. Only the **single existing beaker** can hold mobile fluid. All test actions are independently researcher-scripted, with no Pretorius thought/attention/learning claims.

Next extensions should explore at least two mobile vessels and directed transfers before claiming general material handling. Preserve volume and mass, real physical locality and historical source evidence first.
