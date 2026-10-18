# Continuity of place: what the home must remember

**Date:** October 18, 2026. **Scope:** research engineering, draft stacked on PR #31. This is a practical continuity guarantee, not a claim of subjective consciousness or a replacement for the Doctor's memories.

## The essential principle

The Laboratory is not a staged scene re-created anew after each interaction. It is a persistent place with shared, authoritative physical state. **If Pretorius changes something he can expect to encounter again, that change must survive sleep, interrupted conversations, model replacement, and a restarted process.** The world must retain it even if the Doctor forgets it. Conversely, the Doctor's recollection may be wrong; the world is not obliged to change to match his beliefs.

The simulation does **not** need to calculate the friction coefficient of a chair, the weave density of its fabric, or every hand gesture. Its material truth needs enough precision to answer concrete follow-up questions coherently: Which chair? Which room? Where was it left? Which way does it face? Does another item obstruct that spot? Who moved it and when, according to the world ledger?

## Record meaningful consequences, not microscopic movements

Three categories:
- **Persistent material changes**: furniture location and orientation, object ownership/container, written text, used ingredients, opened or damaged objects, placed bookmark, experiment setup, repaired or abandoned project, and created artifacts. These require a committed world operation, a stable identity and replayable state transition.
- **Temporal world processes**: day/night, plant drying, food spoilage, body fatigue and supported clock transitions. Store the starting source event and derive elapsed effects from the authoritative time. Never make items spring back at midnight unless an actual world process moved them.
- **Momentary expressions**: idle glances, transient attention, a passing thought, or a descriptive aside need not create a physical event. They may matter to the Doctor's cognitive record without inventing a rearranged room.

A previously read page with a physical bookmark belongs to the first category. The established BookLibrary already has event-replayed `mark`, `open_mark`, `turn`, `read` and `close` with bookmarks bound to actual source pages; this branch deliberately does **not** duplicate or overwrite that authority. We should extend free-action discovery to those book operations in a subsequent pass.

## Demonstrated change: rearranging the sitting room

The first experimental relative-position rules use stable identities `chair:parlor` and `table:parlor`, one actual room, and four physical relations: near the fireplace, beside the window, beside the writing desk, and near the doorway. A piece occupies exactly one relative-position slot; its orientation is a separate retained property. This is **semantically exact** for a text simulation even without 3-D floating-point coordinates.

Examples:
- Move the reading chair from the fireplace to the window.
- Turn the chair toward the door without changing its place.
- Leave the room, pass a night in the bedroom, and return in the morning: the window-side chair is there and the rest of the scene is unchanged.
- Attempt to put the chair where the small side table already stands: rejected; there cannot be two incompatible objects occupying the same spot.
- Turn off the light and try to relocate an unseen chair: no source-backed offer. Light the room and reconsider.

The physical furniture state is **not** inferred from what the Doctor says happened. Only an accepted event alters it. Every event has a stable ID, action grammar, before/after state digests, world epoch, historical actor station, clock minute, and exact body/home/rhythm event cursors. A hash chain allows deterministic replay and detects altered records.

As in the earlier botanical experiments, a sandbox fork inherits the **current layout**, not a copy of the parent character's autobiographical experiences. An older Laboratory without this optional addon remains unchanged.

## Permissive intentions without imaginary outcomes

A language model may propose unfamiliar actions in ordinary prose. The bridge must translate a proposal into typed, validated world operations:
1. Interpret the request and identify object(s), location(s), relation(s) and requested physical consequence.
2. Resolve the object identities against the current room and persistent registry; check access, darkness, collision and what actions are possible.
3. Present possible exact operations as **opportunities, not commands**. Only the Doctor's selected opportunity may be executed.
4. Commit the operation and return the resulting truthful first-person experience. Preserve the event for later visits.
5. If the request cannot be represented yet, respond with uncertainty/unsupported action; **do not invent an accomplished deed**, do not silently mutate arbitrary JSON metadata, and do not write a false memory that it succeeded.

An initial deliberately narrow parser handles natural-language variations of moving and turning the parlor chair/side table. It never presents itself as an arbitrary natural-language world editor. This adapter may later be replaced by a model-powered proposer **but not by a model-powered physics authority**; the same source-validated events must remain the boundary.

## Reuse existing durable systems

| Behavior | Existing keeper |
| --- | --- |
| Walking, actual body location, moving past an obstruction | EmbodiedAccess + HomeLife |
| Opening drawers, moving fixed possessions, shared carry/container capacity | HomeLife (plus MaterialObjects overlay for botanical sources) |
| Authentic pages, bookmarks and reading position | BookLibrary |
| World clock, hunger, sleep, finite supplies and written-paper pages | DailyRhythm |
| New objects made from real materials, such as pressed flower specimen | MaterialObjects |
| New furniture relative positions and orientation | HomeArrangements experimental addon |
| Cognition, perception and personal memory | The-Doctor-Lives via authenticated first-person SubjectPort |

**Single-world authority is critical.** The add-ons share the exact same underlying SQLite world and history source. They are not independent simulations allowed to contradict one another.

## What this draft still does not do

Only two movable parlor furnishings and four registered placement relations are implemented. No cross-room furniture transportation, arbitrary object generation, universal language-to-action compiler, unbounded decorative placement, automatic journaling of spontaneous model thoughts, global synchronized atomics across every ledger, or physical chapter navigation integration in the affordance catalog has been demonstrated here. This is **not** a full freeform world engine yet.

The most valuable next step is to generalize the placement operation to more already-source-identified objects and furnishings, and to give the actual Doctor a constrained proposal interface for personally chosen projects. Do not build dozens of bespoke daily schedule tasks just to simulate variety. Preserving each consequential chosen state is more important than counting how many activities were offered or completed.

Research Article scores remain untouched: material world correctness is not evidence of endogenous learned habits, pleasure, or consciousness.
