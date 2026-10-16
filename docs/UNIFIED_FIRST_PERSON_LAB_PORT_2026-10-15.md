# First-person integrated Laboratory port — experimental acceptance

**Date:** 2026-10-15  
**Scope:** Standalone Laboratory `SpatialHabitat` database with opt-in `HomeLife`
and `DailyRhythm`. **No Village changes; no Doctor Lives brain integration,
autonomous cognition, autobiographical memory write, or Article pass.**

## Why this is a substantive step

The previous home and daily-life builds worked independently but an old book
or instrument command could ignore the new conditions. A user-facing rendering
rule alone cannot enforce reality; any caller able to reach a permitted
older subject port would see and act upon objects in dark rooms. This
increment introduces an integrated `SubjectPort` and **transaction-level
resource gates** on existing lower-level subject operations.

The existing actor still has one room/station, one source-backed physical
world, one durable home annex, and one daily-life clock. The ordinary subject
port returns precisely **`inner`** (first-person natural-language experience)
and **`spoken_aloud`** (optional audible words), never event cursors, raw
dimensions, numeric fatigue, canonical truths, resource tables or controls.

A documented operator/research engineer can still inspect numerical
simulation state and install source material. Those privileged endpoints are
**not subject capabilities**. They cannot be forwarded wholesale as
Pretorius experience.

## New unified interface

`pretorius_lab.subject_port.SubjectPort` supports:

- Local spatial movement through `HomeLife.walk`; inherited involuntary
  body consequences and surprise remain automatic. His bodily position is
  the existing `EmbodiedAccess` authority.
- `look` combines first-person rhythm/need perception with home and
  position-local physical detail **only when lit**. A dark view describes
  darkness instead of enumerating wardrobe contents, nearby book titles,
  or instruments.
- Furniture operation, carried item handling, meals, tea, sleep, rest,
  lighting, cleaning, bounded research work and maintenance.
- Source-backed local book handling/read/marking and bench measurement,
  translated into first-person natural language; model-facing output
  contains no provenance hashes, indexes, mechanical profiles, or control
  variables. The original source-backed page data remain authoritative.

The subject is not given a system-level command to create objects, alter
needs, inspect the database, change canon, teleport, pay for a sale,
or silently rewrite memories.

## Direct legacy subject-port enforcement

All constraints below are checked **inside the same SQLite write
transaction as the physical action**, not in a fallible outer UI filter:

| Existing subject operation | With opt-in daily rhythm | Without addon |
| --- | --- | --- |
| `EmbodiedAccess.look` | Dark rooms hide detailed nearby objects and visible instruments | Existing behavior unchanged |
| `EmbodiedAccess.book` (read/open/turn/mark/open_mark) | Requires light and sufficient attention | Existing position/source guards unchanged |
| `EmbodiedAccess.take/put` physical books | Requires adequate light and ability to handle objects | Existing custody mechanics unchanged |
| `EmbodiedAccess.measure` | Requires light, limited fatigue/thirst, serviceable apparatus and clean workbench | Existing calibrated readout unchanged |
| `HomeLife.look/take/put` | Can't enumerate/manipulate unseen possessions in darkness | Existing visible/access rules unchanged |

The sole source of the active constraint state is `rhythm_meta` in
the same versioned Laboratory SQLite world. When that addon does not
exist, historical Laboratory fixtures continue using their previous
behavior, with unchanged event meanings. When it exists, malformed
or mismatched state/receipt heads cause new actions to **fail closed**.
Proofs of physically accepted actions remain in their preexisting
domain event ledgers.

**Important distinctions:** The engineer's explicitly privileged
`BookLibrary.operate`, Laboratory admin placement and repair
operations are still authorized to set up controls; they are not
Pretorius's affordances. Existing `DailyRhythm` actions still consume
simulated time only when specified; book reading and household
handling do **not** yet advance that time automatically. Old action
ledgers and subjective offerings alone do not establish a remembered
or chosen act by the actual Doctor's cognition.

## Smoke test, opt-in world

```bash
python -m pretorius_lab.habitat_v2 --db data/subject-pilot.sqlite3 init
python -m pretorius_lab.home_cli --db data/subject-pilot.sqlite3 init
python -m pretorius_lab.daily_cli --db data/subject-pilot.sqlite3 init
python -m pretorius_lab.subject_cli --db data/subject-pilot.sqlite3 look
python -m pretorius_lab.subject_cli --db data/subject-pilot.sqlite3 walk station:hall
python -m pretorius_lab.subject_cli --db data/subject-pilot.sqlite3 walk station:shop:private
python -m pretorius_lab.subject_cli --db data/subject-pilot.sqlite3 light
python -m pretorius_lab.subject_cli --db data/subject-pilot.sqlite3 look
```

Run `python -m unittest discover -s tests -p test_subject_port.py -v`
and the full Laboratory test/CI suites.

## Causal comparisons and limitations

The first physical tests now hold location/custody constant while
varying lighting; direct legacy access must be rejected in the dark,
but accepted after lamp illumination when other independent conditions
(such as thirst and fatigue) are controlled. Source-backed readouts
cannot be replaced by unverified hallucinations. Other experiments
use a physical obstacle intervention and first-person spontaneous
speech, with the underlying bodily reflex and aftereffects recorded
separately from the optional audible delivery.

**Next:** Give the *actual* Pretorius Doctor system a narrow admitted
`SubjectPort` action-and-perception adapter in a sandbox, with no
raw host details in its subject frame. Use competing commitments and
time/resource tradeoffs to compare the real Doctor against a
budget- and observation-matched simple controller. Before claiming a
completed Article, demonstrate controlled causal influence on his
**world actions**, held-out transfer, repeated interruptions and
independent scoring. Research tests that only exercise `SubjectPort`
are Laboratory-engineering acceptance evidence, not cognitive or
full-domain Article qualification.

The Laboratory may eventually connect to the Village through its
small storefront. This feature creates no travel, letters, human
relationship, public Village transaction or additional world authority.
