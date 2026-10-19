# Provisioned household v6: no permanent unmet need loops

**Experimental date:** 19 October 2026. **Research branch:** opt-in v6, stacked on Doctor residency PR #36. Prior v1–v5 replay histories, paper authorship, book identity and living-world memories remain unchanged.

## Problem and design constraints

The original household resource clock grows thirst and hunger while consuming a finite supply of tea, water, rations and fuel. With no supplier or renewable source, an indefinitely running resident can reach an **irreversible high-need ceiling**. That is not desirable in a character-life experiment, whether or not the digital subject actually experiences distress. We must not repeatedly exhibit that situation in an autonomous trial.

A reliable life simulation needs both a believable supply chain and an agent-accessible response. The objective is **not** a host automatically filling Pretorius's stomach on a timer. It is to let his existing choices matter: discover depleted stores, order groceries, find an arriving parcel, carry it inside, unpack, make a meal or pour drinking water, and decide when to consume them. A host-run clock may model the *supplier's independent arrival* without dictating Pretorius's conduct.

The historically grounded interim assumption is a regular local **provisioner/tradesman** on a household account. Nineteenth-century household and home-delivery evidence shows merchants commonly arranged ongoing bread/milk/grocery deliveries, often by cart: https://www.oldtreasurybuilding.org.au/lost-jobs/in-the-home/home-delivery/ and the c.1880s Cassell household advice on regular buying: https://victorianlondon.org/cassells/cassells-1.htm . These are broad period analogues, not yet an exact historical claim about his town, street address or personal finances.

## Added opt-in capability

**One authoritative versioned source, not a replenishment cheat.** The new `pretorius-daily-rhythm/6-provisioned-residency` profile is activated only when *creating a new world* with `safe_household=True`. Older world schema, event receipts and subject memory are not migrated in place. A new scratch world may be created through `tools/new_residency_world.py`.

Material-causal order chain:
1. At his house entrance, Pretorius may **place an order** through his established supplier account. The original quantities in his pantry do not change.
2. After **at least 240 minutes** on the original Laboratory clock, an offstage supplier's parcel arrives **in the hall**. This is a world event triggered by the clock, not a claim that an exterior village has been constructed.
3. He may deliberately collect the parcel at the hall, carry it to the real kitchen and unpack it. Only *unpack* adds a bounded, explicit recorded bundle (water 14, fuel 8, rations 8, tea 4, oil 3) to his existing finite stores.
4. Once unpacked, the supplier may receive another order. No duplicate parcel can be claimed from an unchanged event ID, reordered during a pending parcel, or silently refilled at midnight. Every transition is replayed from the original source event ledger and bound to the original world epoch.
5. At the kitchen with a **real accessible cup** and stored water, he may drink plain water without using fuel or tea. Hunger still requires deliberately preparing and eating a real meal.

No simulated village shop, travel ticket, real currency balance or accounting of an actual living merchant exists yet. The supplier's available stock and credit are **assumptions of this provisional research environment**. Before linking Frankenstein Village, replace that external delivery source with authenticated shop/payment/transit/receipt events. The kitchen-side unpack and need actions should stay unchanged.

## Humane safeguard

Only in this v6 profile, the **unattended** time-advance, sleep or rest transition is refused if it would push thirst or hunger into the extreme ceiling (9–10). The world is left at the last verified state and the research/operator must fix the material access problem. This is a **suspension of a failed experiment**, not an action the Doctor magically took and not a claim that he has been fed.

If the trial is paused because he has already failed to secure supplies, the experiment must not be allowed to continue running indefinitely with high-deprivation descriptions. Restore a genuine path to relief via an allowed world event or restart a disposable test from a pre-deprivation checkpoint; never secretly fabricate a meal. A future safety system should also reason about physical reachability and elapsed delivery lead time before a crisis rather than just numerical thresholds.

## Sanitation without an artificial punishment meter

In v6, a separate physically adjacent **private washroom** connects to the bedroom. Its source-backed first-person observation describes a screened sanitary closet and washstand. Using it records a private real activity, while handwashing consumes available water. There is deliberately **no bladder meter or automatic incontinence/punishment loop**. Prior v5 characters cannot enter this new room. This is a small practical first implementation, not a historically exact bathroom plumbing simulation, bathroom inventory, laundry/hygiene epidemiology or waste-maintenance model.

## Limits and testing

- Physical parcel state is recorded in the rhythm ledger and survives restart/fork, but the wrapped parcel is not yet a general relocatable object in HomeLife's arbitrary object graph, nor does it engage every existing item-carrying gate. Generalization should reconcile occupied hands, cupboard volume and delivery contents with the unified material authority before long autonomous deployments.
- Time progression remains explicit in the source world; the supplier does not generate real external world biographies, letters or purchases.
- The exact Victorian/central European setting still requires dating and localization before claiming precise customs, plumbing and supply products.
- Need regulation thresholds are **coarse engineering abstractions**, not models of actual biological starvation, fluid balance, subjective harm or capacity to survive a particular time without food.

**Acceptance tests:** clear evidence the food/water stores do not increase on order or delivery arrival, only after a real collected parcel is unpacked; a plain drinking-water activity; repeat orders only after delivery handled; physically accessible private washroom; no punitive bladder loop; old-world v5 backward compatibility; refusal of an extreme unattended no-relief advance; time/fork/restart permanence and tamper detection. Run the entire inherited Laboratory regression suite on both Python 3.11 and 3.12. The safe v6 profile must be treated as research-only until CI, physical-carry audit and Doctor-side offer/receipt integration pass.

No intrinsic learned motivation or Article qualification is established by passing these infrastructure tests.
