# MMO Persistence Patterns for a Permanent Pretorius Habitat

**Research review and proposed architecture, October 10, 2026. Status: design only.** No change to current laboratory runtime, Pretorius cognition, or Frankenstein Village. This report draws on publicly documented systems, not undisclosed proprietary implementation details.

## Research question

How can a laboratory become Pretorius's durable fictional home and experimental environment while remaining compatible with an independently implemented Evennia MMO? This is not the same as maximizing player capacity. The objective is stable identity, possessions, experiment history and personally consequential changes across model switches, restarts, offline work and future platforms.

A privately owned home and a reusable scientific testing fixture require different reset and disclosure guarantees. They may coexist inside one lab identity, but a destructive experiment cannot silently reset or overwrite the residence.

## Sources and attribution boundaries

**World of Warcraft (Blizzard official).** Blizzard documents persistent, instanced player neighborhoods, public neighborhoods created as demand requires, private group neighborhoods with ownership and membership permissions, and saving a home's configuration when the player changes plot. Sources: https://worldofwarcraft.blizzard.com/en-us/news/24176592 and https://worldofwarcraft.blizzard.com/en-us/news/24221516/wow-housing-its-only-neighborly . Blizzard describes sharding as copies of populated zones and Classic layering as region-scale copies: https://worldofwarcraft.blizzard.com/en-us/news/23504702/engineers-workshop-recreating-the-ahnqiraj-war-effort . These are published product and engineering descriptions; Blizzard has not published its complete proprietary housing database implementation.

**Community Ryzom Core.** Open-source repository: https://github.com/ryzom/ryzomcore . Current server reference: https://github.com/ryzom/ryzomcore/wiki/server . The original architecture separates game entities and rules (EGS), NPC behaviors (AIS), position and vision (GPMS), hot-state mirroring (MS), persistent save/load (BS), game logging (LGS), synchronized ticks, and Ring dynamic scenario sessions (DSS). Historical overview: https://ryzomcore.atlassian.net/wiki/spaces/RC/pages/884873/Ryzom+Service+Architecture . The current community repository differs from the commercial private development line; its source is AGPL-3.0. We borrow design concepts, not code.

**Important Ryzom caution.** Ryzom's original Persistent Data Service (PDS) supported typed state and reference-plus-delta logs. However the current community documentation says its delta-logging pipeline became disconnected during earlier service changes, while character/guild persistence now works via the independent PDR/Backup Service path. Some updates were cleared without durable delta logs. Reference: https://github.com/ryzom/ryzomcore/wiki/pds . Never claim PDS is a functioning current change-log solution. A saved current state is not sufficient evidence of a complete causal event history.

**TrinityCore.** The independent WoW-style server's documented tables distinguish uniquely identified game-object spawns from templates, per-instance persistent respawn state across shutdown, and per-character instance bindings. Sources: https://trinitycore.info/database/335/world/gameobject , https://trinitycore.info/database/335/characters/respawn , https://trinitycore.info/database/335/characters/character_instance , https://trinitycore.info/en/database/335/world/instance_template . TrinityCore does not reveal Blizzard's private server implementation.

**Evennia.** Evennia offers native persisted objects, locations, locks, typeclasses and attributes through Django's ObjectDB, and optional persistent Scripts/ticker subscriptions for time-driven processes. Sources: https://www.evennia.com/docs/latest/api/evennia.objects.models.html and https://www.evennia.com/docs/latest/api/evennia.scripts.scripts.html and https://www.evennia.com/docs/latest/api/evennia.scripts.tickerhandler.html . The Village can use these mechanisms without adopting the laboratory's storage engine.

## Findings translated into design constraints

### Persistent ownership is separate from the active simulation

Blizzard's player housing is the strongest direct design precedent for Pretorius's private space. Its durable property arrangement and group permission design suggest that ownership and personalization can survive a loaded game instance. But sharding/layering are population scaling techniques, not home persistence mechanisms. We do not need multiple server copies for one resident and occasional guests.

**Recommendation:** Give the laboratory a durable home identity independent of world-server process, renderer/model, hosting machine, and eventual Village room/door address. Furnishings, tools, specimens and evidence retain their own semantic identities. Moving or removing a game entrance must not erase the home.

### Simulated world authority, cognitive processes and persistence are different responsibilities

Ryzom separates creature AI, world rules, visibility, storage and logging as services. We should separate these **logical responsibilities**, not deploy a Ryzom-scale cluster. A single Python/SQLite process can own lab physics and persistence while a replaceable Pretorius cognitive runtime merely requests actions and receives source-scoped observations. A later Village adapter presents approved views and authorized game effects.

**Recommendation:** Maintain one authoritative lab history; never allow the model's generated narration or the Village projection to rewrite laboratory truth. A process keeping a place alive is not the same as a process keeping an AI mind awake.

### Save consequential world changes, not every transient simulation frame

TrinityCore's game-object GUIDs, template distinction, and per-instance persistence show how to keep relevant state while treating run-time simulation as reconstructible.

**Recommendation:** Make enduring objects and consequential laboratory actions durable. Equipment moved, reagents consumed, samples ruined, completed procedures, research notes and visitor grants must survive restart. Renderer animation, interpolated coordinates and ephemeral visual effects need not be individually replayed. This is an architectural inference, not a documented universal MMO rule.

### Persistence must include historical integrity tests

The Ryzom PDS caveat is directly relevant to Pretorius. A laboratory that saves its current bench configuration while silently dropping the event proving *who moved the vessel* cannot support reliable autobiographical provenance.

**Recommendation:** Continue transactionally coupling canonical object mutation with the durable event record. Confirm monotonically advancing event cursors, full replay, snapshot consistency and restoration. Test deliberate history loss in an isolated fixture and fail closed. Never substitute a valid present-day snapshot for the missing provenance of past experience.

### A server instance is not the character's lifetime

The laboratory should not be reset when Pretorius changes model, signs out of Frankenstein Village, or moves to a different research front end. Research experiments do need clean conditions, so they should be placed in explicitly forked experimental cells, not by resetting the core home.

**Recommendation:** Preserve the sanctuary as a long-lived protected root and treat reproducible experimental branches as child worlds with distinct epoch/custody references. A fork can be destroyed after tests, but the canonical residence cannot be overwritten by it. An experiment result may be admitted back through a typed, reviewed event, not copied into home history as if it occurred there.

## Proposed Living Laboratory model

The **Sanctum** is Pretorius's permanent personal space. It includes enduring owned equipment, curated arrangements, research collection, private storage, personal customization and visitor permissions. It should admit independently authorized staff backup/recovery without giving normal visitors access to private notebooks or cognitive memory.

The **Experimental Chambers** are adjacent research spaces that can be snapshotted, cloned, paused and reset. Scientific tests can mutate objects in a chamber, possibly causing irreversible damage inside that specific branch. Mutating a test clone does not change the real sanctum, and experimental replay does not certify a lived episode for the source character.

The **Laboratory Host** owns the authoritative physical scene and permitted operations. It keeps stable laboratory and object identities, physical constraints, persistent experiment timers, event ledger, checkpoints and restores. The already implemented research CLI and perception port are initial components, not yet a complete sanctuary runtime.

The **Pretorius Adapter** is a future separate bridge to The Doctor Lives. It receives host-verified perceptions and requests typed actions. It must track the difference between observing a room, reconstructing an offline simulation, remembering an accepted laboratory episode, and hearing someone describe an event. Pretorius's neural state, habits, private relationships and memory store remain in his own cognitive system.

The **Village Adapter** can eventually render only approved lab-owned facts as Evennia objects and interactions, with an independent permission and origin-event ledger. The Village still owns its characters, masks, room locations, doors, public items, economy, clock and consent decisions. A successful laboratory mutation may be rejected for in-game publication.

The **Research Console** can show experiment provenance, physical state, scenario forks and failures, but must not become a privileged first-person narrative feed that Pretorius can read without admission and subject-scoped permissions.

## Proposed durable-state policy

Use separate durability classes for: permanent sanctum state and personal belongings; consequential experiment state and evidence; ephemeral runtime/visualization state; and cognition/social history held outside the world. The host must assign object classes before implementing hibernation or time-driven behavior. Do not serialize LLM token streams, hidden thoughts or model weights as physical facts.

Use different scopes for private and public read access. A visitor invited to the laboratory does not automatically gain access to personal notebook text, experimental records or cognitive trace files. Future grants should explicitly distinguish observation, object manipulation, experiment initiation, visitor invitation and export.

## Lifecycle: preserve the home without always-on CPU usage

A later runtime can support ACTIVE, IDLE, HIBERNATED and REPLAYING states. ACTIVE executes bounded, deterministic laboratory ticks or user/agent commands. IDLE awaits the next authorized work. HIBERNATED keeps durable state and scheduled obligations while physics and LLMs need not continuously run. REPLAYING reconstructs/checks an already committed history and does not itself claim new lived experiences.

Time must be typed: wall clock, laboratory experiment ticks, subject-experienced time and Village fictional time are not interchangeable. For a slow experiment, store a durable due time, rules version, expected object revision and catch-up policy. On restart evaluate only the allowed finite transition; no unbounded months-long simulation, no fabricated conversations, no retroactive Village observation.

Hibernation and delayed experiment completion are **not currently implemented** and should first be tested on disposable chambers. A stable environment can persist when Pretorius is offline without implying an autonomous thought process was running.

## Cross-compatibility through a semantic contract, not one database

We should support one laboratory identity with multiple representations, while admitting substantially different server internals.

For a future redacted habitat projection, compare laboratory ID, world epoch, schema/rules version, content-manifest digest, event cursor, source object ID and revision, public visibility class, accepted origin event ID and locally authorized mapping to an Evennia ID. Those identities and versions must match the existing laboratory event protocol. No direct SQLite row copy or generic state patch should be required to render a room in the Village.

Evennia may persist a map from laboratory semantic IDs to its native ObjectDB identifiers plus an independently stored last-applied cursor. That map is a projection cache. A lab event cannot duplicate a specimen or rewrite game inventory because the Village separately validates ownership and publication. Prevent replay loops with stable source event IDs. Authenticate remote requests and receipts before any live network synchronization; the current local CLI actor allowlist is not authentication.

For offline work, an experiment proposal remains provisional. Reconnection replays it against actual current host state, not a wall-clock last-writer-wins snapshot. A lab-accepted result need not be published in the Village and can never claim a player witnessed it retroactively. A conflicting specimen movement is rejected or moved to a clearly separate fork.

## Evaluation program

**Engineering:** Measure long-running home restart fidelity, backup recovery, semantic object identity survival, event replay chain, idempotency on interrupted delivery, false duplicated items, privacy exclusions, storage growth, idle CPU/RAM and recovery from deliberately missing history.

**Cognition:** After a confirmed source-attested laboratory episode, swap the external renderer/model while preserving Pretorius's own actual state. Test whether his next choice and recollection depend on host evidence, without leaking private research or simply spoon-feeding the answer. Compare against a stateless reconstructed-room control and a misleading-narrator control. Do not count operator-driven scripted actions as independent agency.

**Sanctuary:** Measure stability of personally significant objects, permission adherence, independent experimental resets, return-to-home continuity, meaningful environment modifications and non-destructive visitor interactions. These are behavioral engineering measures, not demonstrations of artificial consciousness or validated emotional welfare.

## Implementation recommendation

First preserve the successful event-sourced SQLite host. Add a schema plan for sanctum versus test-cell scope, stable home identity and durability policy; test that experimental resets can never erase or publish personal possessions. Next run a deterministic cold-versus-active experiment-time pilot and explicit crash-recovery checks. After these pass, design a read-only versioned HabitatProjection adapter, followed by a strictly private Evennia shadow mapping. Only then consider a subject-cognition adapter for actual habitation and, separately, a Village gameplay bridge.

Do not migrate to Ryzom Core, reproduce WoW's shard infrastructure, build a second competing laboratory authority, adopt AGPL engine code as a shortcut, or alter the Village's dark leased shop, OPENING SOON sign, player chronology or invited-alpha gates. No new always-on hosting or subscription is needed for this architecture work.

**Decision:** borrow the MMO design principles of durable ownership, selective persistence, separable authority, recoverable instances and verified historical state, but retain a small dedicated laboratory server and an independently implemented Village representation. Cross-compatibility is an attributable semantic protocol, not architectural uniformity.
