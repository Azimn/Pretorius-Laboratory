# Pretorius's domestic home: opt-in v0.1 construction

Status: **standalone implemented research prototype**. Neither the Village nor
the existing inhabited Laboratory is silently migrated or opened. New fixtures
must be initialized on an opted-in `spatial-habitat/2.0.0` database.

## Floor plan and actual objects

The private building connects to the established laboratory threshold:

```text
                     laboratory sanctum -> experimental chamber
                              |
                     narrow interior passage
                +-------------+------------+------------+
                |             |            |            |
             kitchen       bedroom     sitting room   [curtain]
                |             |            |            |
         table/cupboard  bed/wardrobe  desk/chair  tiny shop behind counter
                                                     |
                                               public-facing window
                                                  [CLOSED]
```

The shop's curtain separates its tiny public-facing business from the private
building. **There is no Village street connection, shop opening, or visitor
access.** Its window displays `OPENING SOON`, in agreement with the Village.
The private rooms exist for Pretorius's ordinary life and physical experiments,
not as hidden extra public game content.

Stable furniture includes a kitchen cupboard and table, bedroom wardrobe and
drawer, sitting-room writing desk, hall trunk, shop display case and counter.
Clothing, boots, linens, crockery, tea and bread, writing supplies, specimen case
and a few inexpensive oddities are durable objects in those containers. The
exact inventory is **synthetic fixture data**, not proof that Pretorius has
owned, handled or remembered these objects as part of his personal history.

The same versioned SQLite file contains both physical core world and the
domestic extension. The **existing `EmbodiedAccess` actor** determines his one
room/station; this extension does not create a second pose, model, or brain.
Existing spatial-v2 books, shelves, specimen placements, and laboratory
instruments are unchanged. Home furniture and objects have a distinct ID
namespace and append-only event history; domestic items are not quietly
registered into earlier frozen physical genesis structures.

## Try the opt-in build

Run the existing spatial-v2 initialization only on a **new test DB**:

```bash
python -m pretorius_lab.habitat_v2 --db data/home-pilot.sqlite3 init
python -m pretorius_lab.home_cli --db data/home-pilot.sqlite3 init
python -m pretorius_lab.home_cli --db data/home-pilot.sqlite3 look
python -m pretorius_lab.home_cli --db data/home-pilot.sqlite3 walk station:hall
python -m pretorius_lab.home_cli --db data/home-pilot.sqlite3 walk station:bedroom
python -m pretorius_lab.home_cli --db data/home-pilot.sqlite3 open wardrobe:bedroom
python -m pretorius_lab.home_cli --db data/home-pilot.sqlite3 look
python -m pretorius_lab.home_cli --db data/home-pilot.sqlite3 take garment:coat
python -m pretorius_lab.home_cli --db data/home-pilot.sqlite3 walk station:hall
python -m pretorius_lab.home_cli --db data/home-pilot.sqlite3 walk station:shop:private
python -m pretorius_lab.home_cli --db data/home-pilot.sqlite3 look
python -m pretorius_lab.home_cli --db data/home-pilot.sqlite3 verify
python -m pretorius_lab.home_cli --db data/home-pilot.sqlite3 shop-manifest
```

`home_cli` is a **local research host**, not an agent-enabled external
transport, nor a public world edit API. It deliberately emits a separate
research/verification response for `verify`, `audit`, and `shop-manifest`.
**Never feed their output to the character as subjective input.** For subject
access, use only the natural-language strings `inner` and `spoken_aloud`
returned by `HomeLife.look/walk/open/close/take/put/shift_stool`.

## First-person reflex experiment

A low stool is a declared obstruction in the compact private shop path.
Crossing from the hall into `station:shop:private` produces an actual
embodied **move receipt**, followed by a derived bodily event:

- Mechanical action: the modeled foot catches an obstruction, withdraws,
  and accumulates bounded soreness and additional movement effort.
- Optional public utterance: `Ow! My foot!`
- Subsequent first-person appraisal: `My foot catches against the low stool.
  I jerk it back. That was aloud? I had not meant to say anything.`
- Following movement: effort is higher while the simulated foot remains tender.
  The tenderness decays over subsequent steps.
- Counterfactual: moving the stool out of the path with a real local action
  stops later collisions at the same threshold.

The utterance is **not selected by a deliberating renderer**, and the
reflection cannot precede the underlying event. The simulation does not claim
a real nervous system or true phenomenal pain. A closed-loop model with
deterministic rules is sufficient for this initial behavioral test; richer
kinematics, footwear, observed foot trauma, and response variability remain
future research.

If a body moves through the older embodied interface while the home service
is not running, the next home action replays missed movement effects exactly
once into the append-only domestic ledger. The home receiver must nevertheless
deliver any pending external utterance through a **deduplicated outbox** before
using it in a multi-user/voice runtime. The current code persists event facts;
it does not claim network delivery or exactly-once utterance delivery.
This distinction is intentionally explicit.

## Persistent furniture and object handling

Items have stable identities and one physical container or actor ownership.
Closed containers conceal their contents and cannot be taken from at a distance.
An item can be carried and placed into opened furniture in another room.
The pilot imposes a simple one-carried-object limit as a stand-in for hands.
Capacity constraints, room locality, and idempotent event IDs are enforced
transactionally. Reopening the SQLite DB and backing it up preserve the
same room contents; replay checks event hashes and derived state.

A controlled sandbox fork copies **present-day furniture and possessions**
and the actor's pose, never claiming the clone lived through the parent's
earlier history. It receives a new world epoch and empty domestic event history.
Mutations in the clone do not alter the parent. This is the default
counterfactual test isolation strategy.

## The future two-world shop boundary

Only the storefront needs cross-simulation inventory consistency.
`shop_manifest()` is a read-only, engineer-facing **proposal** containing
the actual currently displayed sale stock, stable IDs, illustrative
krajczár prices, the world epoch and its state hash. It cannot open the shop,
issue currency, remove an object due to a remote claim, or assert a sale.

Future Village integration should use a keeper-authorized idempotent sale
receipt (`sale_id`, `object_id`, quantity or unique-instance identity,
finalized buyer transaction, both world epochs, accepted revisions).
Exactly one authority must finalize each physical transfer; ambiguous/failed
handoffs remain unavailable for sale rather than existing twice. The
Laboratory is authoritative for private space; the Village is authoritative
for public character transactions. The same public stock ID must be removed
or marked unavailable in the Laboratory before another sale can be accepted.

The public shop must remain quite small, with inconvenient opening hours and
financial motivation modeled as later **consequential economic pressure**, not
a blanket instruction that forces him to behave as a particular shopkeeper.
The character's film-rooted past, search for Henry, and the Village's
novel-rooted Victor account stay separate historical/belief sources.
Nothing in this feature generates new autobiographical memories.

## Evidence and next implementation increments

`python -m unittest discover -s tests -p test_home_life.py -v` tests
physical locality, container privacy, stable possessions across restart,
collision/aftereffects, obstacle intervention, body receipt recovery,
shop manifest boundaries, full SQLite backups, tamper detection and isolated
counterfactual forks. The full Laboratory CI must also remain green.

Next add actual lighting/visibility, finite fuel/food and daily sleep,
reusable kitchen and laboratory tasks, equipment condition/repair, a
source-authenticated first-person experience adapter into
`The-Doctor-Lives`, and eventually a trusted shop sale handshake.
This **does not** raise any of the 34 Article progress scores yet.
