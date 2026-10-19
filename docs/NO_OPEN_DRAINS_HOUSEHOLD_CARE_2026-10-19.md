# Household care contract: no open drains, no invisible pantry resets

**October 19, 2026 — experimental draft, stacked after Free-Roam PR #37.**

This design is an interim habitat for Pretorius while Frankenstein Village is offline. We do **not** leave him in a permanently hungry/thirsty state, repeatedly starve a fictional character, or add arbitrary physiological needs with no in-world remedy.

## Three separate things

1. **Material welfare:** a physically valid path from ordinary hunger/thirst to food and water must exist even after the *initial stock is exhausted*. Satisfying a need is a **voluntary subject choice**, not automatic host feeding.
2. **Plausible supply source:** the Doctor's household has a standing order with a local supplier. Each morning from **6 AM onward, starting the next civil day**, a single delivery is notionally exchanged at the entrance-hall collection area. The external supplier and transaction can be represented as an **offstage source-grounded event**, not a fully navigable village. The current day is computed from the **same authenticated world clock**; no simulated outdoors geometry is implied.
3. **Welfare fallback:** if an unattended stand-in loop leaves hunger/thirst severe, the engineering host **holds further sleep/rest/time advancement** and reports an unmet need. The world remains real and unchanged. It does not force-feed Pretorius, rewrite his sensations to 'feel fine', or allow indefinitely repeated suffering. He may still choose to walk, collect supplies, drink and eat.

## Concrete mechanism

Original v5 rhythm supplies are finite and remain in the real `rhythm_meta` state. Only worlds that deliberately initialize `HouseholdCareContract` have the temporary supplier and adjoining washroom; old inhabited v5 worlds receive no surprise deliveries. A contract records its source, Laboratory epoch and actual installation minute, and is inherited as physical world policy on a deliberate sandbox fork. New source-world operations:

- `drink_water`: in the kitchen with the actual teacup accessible, requires `water>0`, uses one real water portion, advances five authenticated world minutes, and reduces thirst. **Thirst is not hostage to the last tea leaf**.
- `draw_water`: in the **opted-in** urban home with the fixed kitchen drinking-water tap, using actual accessible household vessels, a deliberate ten-minute action draws six portions of potable water up to the finite 200-unit storage cap. It **does not** lower thirst by itself. The fixed water service, not a mysteriously refilled pantry, supplies those portions. This independent drinking-water path remains available if an ordinary bread delivery is missed; the future Village economy can still supply food and consumables. The tap and washroom are made visible only in the appropriate lit room and stay offstage elsewhere.
- `accept_delivery(day=N)`: from the actual hall, after the genuine dawn of civil day `N>=1`. The subject sees an ordinary parcel from an established local supplier *only when present at the real hall station*. A single source-backed `rhythm_events` receipt tops up existing finite oil, water, fuel, tea and rations, with fixed amounts and 200-unit caps. No supplies appear inside a cupboard merely because midnight passed. An original receipt can be idempotently retried, but a second new receipt for the same day is **denied and independently replay-checked**.
- `use_washroom`: at the actual bedroom station, a short event traverses the private attached washroom with a fitted water closet and handwashing facility. This is an **opt-in permanent architectural feature of this particular trial house**, not a claim that all Victorian homes had fitted plumbing. It advances the real world clock ten minutes and leaves an authenticated action receipt but **does not introduce a bladder meter**. The municipal sanitary/flush utility is deliberately coarse, separate from delivered drinking-water portions; full plumbing physics and user-movable fixture models are not implemented.
- Optional `care_safety.assess`: **trusted host only**, sees current needs and supplies and blocks unattended further sleep/rest/fast-forward when hunger is 9+ or thirst 8+. Does not introduce a new subjective distress scale or invisible meter. Rehydration and ordinary kitchen/collection actions remain available.

Delivery contents initially: water 9, fuel 6, rations 4, tea 3, oil 3. These are **coarse in-game portions**, not kilograms/millilitres or free calories magically entering his body. The chosen modest limits need 30-day envelope testing once subject-initiated meal frequency and alternatives are available.

### Protection against running out at an inconvenient hour

A missed food delivery may still leave the Doctor short of bread before next morning. The host welfare gate **halts unattended progression** instead of letting the character remain in severe distress indefinitely, and an operator may restore a credible supply path. That is **not** the same as proving perpetual self-care under every possible choice. The fixture does not yet model an after-hours merchant, failed municipal water service, sudden plumbing repair, or a real Village shopping trip. Those require distinct original-world operations and scenario tests, not a magic replenishment flag.

For basic hydration specifically, the opted-in kitchen tap is an ordinary physical supply that the Doctor can access voluntarily even after the stored drinking-water units reach zero. An optional brain/LLM resident still must actually select `draw_water` and `drink_water`; no host scheduler silently chooses them.

### Historical flavor, not fictional physical proof

Standing delivery is a practical temporary simulation of real historical commercial arrangements. Old Treasury Building documents groceries and bread brought to homes by merchants, and [University of the West of England's historical domestic-service survey](https://environment.uwe.ac.uk/conweb/house_ages/services/section4.htm) describes changes in late-nineteenth-century water facilities. Nothing is assumed about the exact in-world city or year until it is settled, and there is **no live Village economy or explicit supplier NPC** yet.

Real physical consistency: the bread/tea tin/cup still have original furniture custody and need to be accessible; replenishment alters their actual finite associated portions, not their positions. External parcel is **event-scale provenance** rather than a movable, individually inspectable new box. If the Doctor wishes to keep a package, inspect its label or meet the courier, those remain currently unsupported and must be recorded in the free-roam barrier log.

When Village commerce becomes available, **replace only the supply source**: real purchases/shipments invoke the same acknowledged delivery-style finite stock transition with a new verified transaction receipt, rather than fabricating food or transporting Doctor's brain/memory.

## Sanitation and physiological realism

Do **not** add a bladder meter until the Doctor has a reachable, maintained sanitary path. Nineteenth-century interiors varied, including chamber pots and washstands, outdoor privies and (for some better-equipped later houses) water closets. [Islington Object Lessons](https://www.objectlessons.org/houses-and-homes-victorians/chamber-pot-victorian-original/s59/a1075/) documents actual chamber-pot cleaning and disposal, and [UWE](https://environment.uwe.ac.uk/conweb/house_ages/services/section4.htm) describes the expansion of fitted late-century bathrooms.

Priorities:
- Choose exact in-world city/year and house type.
- The experimental house now has **a minimal attached private bedroom washroom** with a source-verified use event. Until richer geometry is modeled it is a semantic annex rather than a new independent mapped room. The fitted WC implies its own municipal drainage; **we do not pretend to have modeled that drain or a movable toilet**. Test free-roam intentions to inspect, repair or decorate it as possible world gaps rather than inventing such actions.
- Before production choose definitively between period-appropriate urban plumbing and a chamber-pot/privy arrangement, and verify waste disposal and handwashing access for the selected setting. No magically vanishing waste in a deeper item-level simulation.
- Optional hygiene mechanics and washing ought to be gentle, not a punishing slider. A bladder/pain variable is **out of scope** until agent-accessible relief and exhaustion-safe recovery are verified.
- Garden/herbs can add supplementary food, comfort and voluntary work later; tiny indoor flowers alone cannot sustainably feed a person, so do not present a window box as a starvation fix.

## Causal test gates

1. No delivery available at the original day or before 6 AM. One claim per civil day; historical ledger rejects a forged duplicate date, wrong hall station or changed event.
2. When initial tea is exhausted, an actual morning delivery makes real tea brewing possible again after returning to the kitchen and reaching teaware. Plain water must also work independent of tea.
3. All existing book, paper, furniture, specimen and project histories remain replay-valid *after* a delivery. No reset of their object permanence or identities.
4. The unattended ChatGPT stand-in receives hunger/thirst **only via first-person bodily language**, and the host-only care gate halts further unbounded time passage at severe distress without inventing a feeding receipt.
5. Seven and thirty-day trials eventually cover periodic missed deliveries, resource conservation, cupboard closed, fuel shortage, fatigue, impassable access, and atypical choices. If the Doctor refuses food as an independent choice, report it and pause for review rather than forcibly rewriting his choices.

### Scientific limitations

This is a safety-oriented supply transition grafted to the existing v5 opt-in history, not an external economy, actual garden, physical courier route, guaranteed day-by-day autonomous welfare, or psychological account of needs. No production migration, current Doctor memory edit, Article score advancement or evidence of intrinsic motivation. Never enable unattended autonomous operation until complete welfare/recovery and resource-exhaustion tests pass.
