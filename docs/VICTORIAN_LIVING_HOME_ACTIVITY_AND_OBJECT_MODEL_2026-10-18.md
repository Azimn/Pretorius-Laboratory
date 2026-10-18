# A lived-in Laboratory: Victorian activity ecology and persistent-object architecture

**Research date:** 2026-10-18. **Goal:** Pretorius is free to pursue, ignore, invent, revisit or abandon activities; the world remains a causally coherent home. **Scope:** design and first affordance-discovery prototype, stacked on the previous v5 physical-paper experiment. No canonical identity or inhabited world migration.

## Historical frame

Our Laboratory currently uses a **late-1800s research/home frame**. English "Victorian" sources are historical analogues, not proof that the Doctor, possibly based in Central Europe, follows English social customs. Choose a precise in-world city and year before asserting specific food, transport, scientific instruments, book editions, religious observances or social conventions. Avoid turning gendered Victorian prescriptive manuals into universal behavior requirements.

Evidence anchors:
- [Cassell's Household Guide, c. 1880s](https://victorianlondon.org/cassells/cassells.htm), especially [cooking](https://victorianlondon.org/cassells/cassells-2.htm), [tea](https://www.victorianlondon.org/cassells/cassells-48.htm) and [household chemistry](https://victorianlondon.org/cassells/cassells-53.htm). These describe actual material processes, ingredients, tools and domestic tasks rather than just aesthetic wallpaper.
- [Natural History Museum: pressing plants and making labeled herbarium sheets](https://www.nhm.ac.uk/discover/how-to-press-flowers.html). A legitimate artifact needs an actual plant, drying media, weight, elapsed time and specimen label/origin; an instant 'press flowers' command that leaves no durable plant would be dishonest.
- [Museums Victoria: late-Victorian scrapbook, c.1880–1910](https://collections.museumsvictoria.com.au/items/257161) — collections of actual acquired images and sometimes pressed natural objects, not generic disposable activity counters.
- [V&A: Arts and Crafts home design](https://www.vam.ac.uk/articles/arts-and-crafts-design-for-the-home) — individual aesthetic expression, furniture and domestic objects.
- [University of Vienna: nineteenth-century scientific societies](https://fsp-wissenschaftsgeschichte.univie.ac.at/research/scientific-societies-in-vienna/) and [Natural History Museum Vienna collection history](https://nhm-wien.ac.at/en/press_/about_the_museum/history). Relevant research activity includes specimen collecting, cataloguing, scientific correspondence, collections and publications rather than only bench experiments.
- [City of Vienna: historic coffeehouse culture](https://www.wien.gv.at/en/leisure/viennese-coffee-culture) — context-specific social/leisure opportunities, once the exterior world exists.

## Activities as opportunities, not chores

| Category | Plausible activities | Existing world support | Missing material substrate |
| --- | --- | --- | --- |
| Reading and writing | read books, mark pages, write journals, letters, sketches, annotate or criticize chapters | Physical books/bookmarks in the older Laboratory; v5 source-bound writable paper | Book-text/edition provenance and chapter progress; independent bound journal, letters, handwriting, bookmarks tied to specific physical volumes |
| Scientific work | prepare apparatus, design protocols, measure, replicate, catalog specimens, compare observations, draft findings | Experiments, repairs, instruments and storage anchors exist | Multi-stage experiments, hypotheses, samples/products, results attached to actual setup and materials |
| Natural history | collect leaves/flowers, dry and press specimens, mount herbarium sheets, sketch species | Specimen case, physical paper and research objects | Accessible plants/garden or exchange source; dynamic specimen identity, timed drying, paper/press/glue, specimen labels |
| Cookery and hospitality | soup, porridge, tea, preserves, baking, table setting, invite someone to dine | Finite tea, one coarse meal, teapot and cup | Individually sourced ingredients, recipes, apparatus, freshness, plates/portions, aesthetic choices, social guests |
| Comfort and rest | sit in favorite chair, arrange flowers, watch rain, listen to music, take a bath, change clothes | Rooms, clothing, lamps, sleep | Seats, usable music objects, weather/washing, bodily comfort and long-lived choice outcomes |
| Collections and crafts | arrange curio displays, assemble scrapbook, repair clockwork, carve, bind or gift a book | Curiosities, desk, containers, fixed movable items | Movable crafted *new* objects, component transformations, cataloguing, damage/repair states |
| Garden and seasons | tend beds, press blooms, dry herbs, observe changing light and weather | Daylight and simulated clock | Real exterior ground, weather, growing things, seasonal growth and decay |
| Communication and culture | correspondence, salon, scientific society, visitor, café, lecture | Sealed shop/village threshold | Mail delivery, other actor identities, shared object provenance, external world integration later |

**If Pretorius never uses an affordance, it remains a world opportunity, not failed content.** Measure available breadth separately from chosen breadth; do not inject fake attraction to uncommon activities to make metrics look good.

## Critical code-audit finding: why more commands alone will not work

The v1 HomeLife validator insists on `set(items) == set(START_ITEMS)` and fixed container IDs; the original v5 physical paper stores text in the DailyRhythm state as `paper_marks`, physically accessible through *one* fixture paper object. These preserve historic replay well but cannot natively create arbitrary persistent new flowers, letters, bound journals, illustrations, dishes or scientific preparations. The next material-world version must allow **world-created object identities and typed state** without silently modifying v1–v5 historical reducers or valid existing DBs. This is a real architecture limit, not a missing item-name list.

## Two layers of freedom

**A. Discover truthful affordances now.** Introduce read-only `HomeAffordances` grounded in the *already deployed* pure physical transitions and current room, possessions, light, stocks and furniture. It returns a first-person experience of possible actions and a separate *trusted-engineer offer list* of exact legal command arguments. No raw world state enters the Doctor's experiential text, no behavioral priority is attached, and the Doctor does not have to accept an offer. Require a world-state stamp when executing a chosen offer: if material conditions change, reobserve and reconsider. Free text remains authored by the Doctor, never filled by the host.

**B. A versioned, extensible material-object authority for the next world.** Each object should have:
- Stable unique object ID, kind, identity/appearance, real physical parent (container/room/held body), ownership/custody and count/quantity.
- Typed components: `Readable`, `Writable`, `Perishable`, `Consumable`, `Container`, `Instrument`, `PressablePlant`, `CraftedResult`. Components define capabilities and validators; do not attach generic fake text as properties.
- Exact provenance from one or more parent resources/action receipts; actual resource depletion for transformations; no creation from thin air.
- Temporal processes (drying, fermenting, meal cooling, lamp oil, flower wilting), advanced by one world clock only; unfinished projects and intermediate conditions persist through downtime.
- Real visible evidence and discoverability based on actual location, light and prior observations, not a global omniscient inventory. The physical world state is separate from what Pretorius presently knows or remembers.
- Append-only event chain, deterministic replay and stable material snapshots, saved atomically in the existing Laboratory SQLite authority; world forks inherit *current artifact state* but not autobiographical events.
- Semantic relations (`made_from`, `stored_in`, `written_by`, `pressed_under`, `part_of_project`, `derived_from_experiment`), all verifiable source IDs.
- Real agency: he may abandon a meal, leave a half-read book, delay a flower press, scribble an unrelated note or invent a project; **no scripted forced consumption of opportunities**.

## Compositional verbs, rather than hundreds of bespoke activities

Build general material operations in the next version: `inspect`, `take`, `put`, `open`, `combine`, `transform`, `heat`, `dry`, `wait`, `repair`, `write`, `read`, `label`, `arrange`, `separate`, `give`. Each operation has precise object component preconditions and real time/material outcomes. An activity such as *press flowers* becomes a plan using these verbs and owned objects, **not** one magic success flag. Likewise *make soup* becomes selecting real ingredients, a container, heat, cooking time, edible prepared food, and cleanup. Rich text can narrate the actual verified steps.

For genuinely novel intentions, an LLM may propose a candidate action sequence, but **only the Laboratory may validate and commit it**. Unsupported intentions get a truthful response about what is missing or a safe alternative, never an invented executed result.

## Evaluation requirements

1. **Object permanence:** create/transform a flower or handwritten page, leave it in a real container, change rooms, rest or restart; it is still there, unchanged unless an independently verified process acts on it.
2. **Visibility:** closed drawer, darkness, remote room or unobserved arrival never discloses hidden details.
3. **Historical replay:** later moving an object never invalidates the event that originally created or read it; tampering source hashes fails validation.
4. **Composable activity:** a specimen can be pressed, mounted, labeled, moved, put in a book and later examined with provenance intact.
5. **Unused affordances:** a week of inactivity leaves unrelated optional opportunities valid; coverage counts are not used as external incentives or success rewards.
6. **Doctor choice:** the subject chooses activity and free-authored contents; distinguish host scheduling, deterministic world routines, bounded grounded arbitration and genuine Doctor-initiated preferences.
7. **Strong cheap controls:** evaluate physical reliability independently from self-directed project selection and habituation; avoid claiming more neural cognition when deterministic rules match.
8. **Lifecycle:** test multiple simulated weeks with material production, unused objects, decay, finite supply replenishment through *real* deliveries, and unexpected interruption; no implicit daily reset.

The first prototype proves **truthful action discovery over the existing fixed-object world**. The full dynamic-object system is *designed here, not yet implemented*. Do not call the Laboratory an arbitrary-action or complete Victorian life simulation until that stronger authority exists and has passed end-to-end experiments.
