# Pretorius: daily-life environmental consequences (opt-in pilot)

Date: 2026-10-15. **Implemented as an isolated Laboratory research addon**, not a
replacement for the existing inhabited world, the cognitive identity substrate,
or Frankenstein Village.

This pilot uses the **same existing spatial-v2 Laboratory SQLite database**
and the **same existing embodied Pretorius station** established by
`HomeLife`. It adds no new character, router, renderer, Village connector or
biographical memories. Daily activity is explicit local host work, not a
background daemon; this implementation alone does not constitute autonomous
agency, true emotional experience or a passed Article.

## Why this layer

The preceding home pilot created a kitchen, bedroom, sitting room and very
small closed shop with permanent furniture, possessions and a first-person
collision reflex. This second increment gives ordinary activity real costs.
Without such costs, sentences about fatigue, hunger, need for rest, failed
tools or household conditions are merely style. The current implementation
keeps numerical accounting in a versioned, deterministic **engineer-only**
annex and emits only natural-language first-person experience.

## Versioned capabilities

- **Simulated time:** an explicit research-host `advance` of 10–240 minutes.
  Light changes with a simple day/night window; no pretend real-time daemon.
- **Illumination:** daylit rooms are bright between 06:00 and 18:00. The
  windowless inner passage and experimental chamber need lamps even by day.
  Lighting a room burns a real finite oil allocation for up to 60 simulated
  minutes. If the light expires, the room returns to darkness.
- **Needs:** hunger, thirst and fatigue increase with elapsed simulated
  time. Sleep advances eight hours and reduces fatigue without concealing
  increasing thirst or hunger. Short rest provides less recovery.
- **Kitchen:** stored food provisions, fuel and water are consumed when a
  meal is prepared. A prepared meal remains until eaten; eating reduces
  hunger, and tea takes tea leaves, water and fuel. These provisions are
  a **separate finite pantry allocation**: the prior decorative home
  `food:bread` fixture is not falsely claimed to be the consumed object.
  Full reconciliation with individual furniture item quantities is next.
- **Experiments:** operating at the real Laboratory bench requires usable
  apparatus, light, reagents, a sufficiently clean work area and tolerable
  fatigue/thirst. It consumes reagent stock, degrades apparatus, takes time
  and increases fatigue/clutter. An unserviceable apparatus prevents work.
- **Repairs and cleaning:** repairs consume limited spare components and
  improve apparatus condition. Cleaning takes time, increases exertion and
  clears accumulated clutter. Tasks are station-local; the host cannot
  invent that Pretorius is in the bedroom or kitchen.
- **Persistence and replay:** every accepted action is hash-chained in
  `rhythm_events`, with recorded body and domestic source cursors. SQLite
  restart, independent verification and full Laboratory backup preserve
  the same world condition. Sandbox forks retain **present state** but
  start a new world epoch and have no fabricated lived action history.
- **First-person surface:** `DailyRhythm.act/look/advance` return
  `{"inner": "...", "spoken_aloud": null}`, never numeric needs, world IDs
  or engineering metadata. The `audit_state()` method and CLI `audit`
  are explicitly engineer-only.

## Try on a fresh, explicitly opted-in fixture

```bash
python -m pretorius_lab.habitat_v2 --db data/daily-pilot.sqlite3 init
python -m pretorius_lab.home_cli --db data/daily-pilot.sqlite3 init
python -m pretorius_lab.daily_cli --db data/daily-pilot.sqlite3 init

python -m pretorius_lab.home_cli --db data/daily-pilot.sqlite3 walk station:hall
python -m pretorius_lab.home_cli --db data/daily-pilot.sqlite3 walk station:kitchen
python -m pretorius_lab.daily_cli --db data/daily-pilot.sqlite3 look
python -m pretorius_lab.daily_cli --db data/daily-pilot.sqlite3 prepare_meal
python -m pretorius_lab.daily_cli --db data/daily-pilot.sqlite3 eat
python -m pretorius_lab.daily_cli --db data/daily-pilot.sqlite3 advance 120
python -m pretorius_lab.daily_cli --db data/daily-pilot.sqlite3 verify
```

Night/light test: advance until after sundown; attempt an experiment from the
workbench without adequate light, then light the laboratory lamp and retry
under otherwise equal conditions.

```bash
python -m unittest discover -s tests -p test_daily_rhythm.py -v
python -m unittest discover -s tests -v
```

## Experimental causal tests

The focused suite tests lighting versus darkness, actual supply consumption,
required locality, work denial from missing resources or equipment wear,
fatigue recovery across sleep and time advance, idempotent action receipts,
source-bound first-person text, tamper rejection, opt-in isolation, verified
backup and counterfactual forks. A passing software acceptance suite
establishes mechanics, not independent Article qualification.

Future registered interventions should hold the renderer and situation
constant while varying **one genuine condition**: fatigue, room light,
available oil, reagent supply, repair stock, training history or spare time.
Require actual action differences under equal-observation simple controllers,
plus held-out scenarios beyond authored fixtures.

## Deliberate boundaries

This is a discrete simulation, not high-fidelity rigid-body physics or
physiological neuroscience. There is not yet a unified continuous clock,
automatic time advance, wear per individual apparatus part, ambient
temperature, physical food item consumption, tool learning, true sleep
activity, external letters or a direct Doctor cognition port. Other
`HomeLife` and book interfaces do **not** yet inherit all daily-life
resource gates; a future unified Pretorius subject adapter must enforce
those gates consistently. Do not award Article progress based merely on
installing this opt-in pilot. First measure causal behavioral effects,
repeat them outside the initial scripted contexts, and then update the
versioned 34-Article evidence register.

The Laboratory remains private and authoritative for these objects.
Frankenstein Village retains its separate canon and remains unchanged.
