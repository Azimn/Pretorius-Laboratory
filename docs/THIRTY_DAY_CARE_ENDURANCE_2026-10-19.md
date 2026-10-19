# Thirty-day household care envelope, with explicit limits

**Date:** October 19, 2026. **Branch:** experimental PR #38, no merge or inhabited-world migration. **Status:** implemented reference-control script; final-head CI pending (GitHub jobs queued at this writing).

## What this trial can and cannot establish

The existing household physics has finite food, water, fuel, tea and oil. The new opt-in contract gives the Doctor a physically accessible kitchen water source and ordinary date-bound merchant deliveries in the hall. We need to check that this *could* sustain reasonable everyday behavior, and also prove a missing supply source is detected rather than covered up with magic stock.

`pretorius_lab/care_endurance.py` simulates thirty civil days **through the original validated pure DailyRhythm transition function**, not an invented spreadsheet's food equations. The control deliberately drinks water, prepares and eats meals when hungry, cleans when required, rests/sleeps and collects ordinary deliveries. Water drawing and hydration are two different actions. The standing supplier may miss selected days. The same finite stores, resource caps, elapsed minutes, food freshness, daylight and fatigue checks apply.

The controlled envelope **assumes** the Doctor can access the relevant kitchen vessels, move between places, and actually select these activities: `stock_access={"meal":True,"water":True,"tea":True}` and prescribed real stations. That is a *deliberate upper-bound reference*, **not** a source-authenticated in-world 30-day physical record. It provides **no** Doctor autobiographical memory or evidence of neural or ChatGPT independent choices. It must not be cited as proof he is safe running for a month without an operator.

### Supported claims after a passing test

1. A feasible thirty-day reference schedule can draw water, eat and sleep without the v5 pure reducer entering an impossible resource state.
2. Missing two isolated deliveries does not, under this particular stock-management reference plan, automatically lead to permanent starvation.
3. Extended early non-delivery causes a **clear failure**, not silently conjured food.
4. The thirty-day reference reports its real count of selected reducer actions and admits they were **scripted by the test**.

### Non-claims

- Thirty complete days of the actual Doctor operating unaided.
- Thirty days of real object/container/body station movement with one SQLite source receipt per transition.
- Proof of any individual choice by the neural policy or future small external renderer.
- Guaranteed relief if the Doctor refuses supplies, kitchen becomes inaccessible, town deliveries fail indefinitely, or municipal water service is interrupted.
- Authentic Village store purchases, actual money spent, a courier NPC's existence or literal outdoors geometry.

These matter: a reference controller can make excellent choices that Pretorius himself would not make. The absence of an open physical drain is **necessary**, but not sufficient, for ethical unattended deployment.

## How to run the two controls

```bash
python -m unittest discover -s tests -p test_care_endurance.py -v
python -m pretorius_lab.care_endurance --days 30 --miss-delivery 8 --miss-delivery 9
```

The test's first case simulates 30 days with days 8 and 9 omitted from normal delivery. The negative control with nearly a week of no subsequent merchant packets **must** raise an explicit physical resource failure. Any unexplained success in that counterfactual is a bug.

The study output is host audit JSON with day-level need and stock numbers; **never feed it raw to Pretorius**. Only the first-person SubjectPort observations belong inside his subject-facing experience.

## Next meaningful gate before autonomous continuous occupancy

1. Run one **actual** material Ledger/SubjectPort trial lasting at least seven simulated days, not solely the pure reference.
2. Interrupt/reopen the SQLite world, Doctor renderer and observer journal independently; verify exact receipt hashes and original material placements after restart.
3. With an equal physical affordance catalog, compare a heuristic safety-first policy, ChatGPT stand-in and eventual smaller renderer. Give all controllers the **same first-person** source input and evaluate actual resulting world events, blocked actions, delays to relief, and any hallucinated completed deeds.
4. Stress a sealed kitchen cupboard, an unlit room, exhaustion before cooking, zero stocked drinking water, two missed deliveries, a permanently absent supplier, and an invalid Village purchase. A wellness hold must stop progressive unmet suffering until legitimate recourse exists, without masquerading as a meal or erasing a character's decisions.
5. Replace the offstage standing-order source with a separate validated **Village merchant transaction receipt** only after village travel/commerce exists. The household `DailyRhythm` consumption interface should remain stable. Avoid building a second pantry in the game.

Do not promote an Article-of-Artificiality qualification on the strength of scripted care. The target is a meaningful enduring home and reliable first-person causal feedback, not synthetic suffering as a motivational mechanism.
