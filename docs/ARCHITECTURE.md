# Permanent Laboratory Authority: executable contract v0.1

Status: research-only implementation. The local executable is not a public network service and cannot write Frankenstein Village history. This repository is a new host, not a migration of The Doctor Lives Stage 04 data.

## Ownership and persistence

The laboratory has one durable SQLite authority. It owns lab object identities, containment, experiment ticks, private notebook entries, mutations, and accepted lab history. Laboratory time is a counter of experimental ticks, not UTC and not 1890s Village time. Pretorius's cognitive state, reconstructed autobiography, subjective memory provenance, secrets, relationships, and model weights are **not** owned by this host.

The stable lab_id identifies the logical laboratory, while world_epoch identifies its current lineage. Both persist across restarts and backups. The schema version, ruleset version and SHA-256 of the content manifest are distinct from the materialized state revision and event cursor. A future adapter must compare all of these dimensions before rendering accepted changes.

The v0.1 laboratory scene contains a room, fixed bench, closed specimen vessel, specimen, research clock and private notebook. Identifiers are explicitly defined in physics.py, never regenerated when reopened. State transitions are pure and deterministic, and the same reducer is used for writes and verifier replay.

## Event history

An accepted event contains source actor, operation, base and committed revisions, object revision preconditions, lab ID, epoch, manifest and rule versions, before and after state digests, a previous-event cursor and the UTC recording timestamp. Events are append-only and SHA-256 chained, with a unique event ID. SQLite BEGIN IMMEDIATE protects the revision increment and state write in the same transaction. A duplicate event ID with an identical payload is idempotent; an attempted reuse for a different request is rejected.

The verifier reconstructs state from the immutable built-in manifest and replays each persisted event. It checks revision continuity, IDs, epoch, versions, reducer preconditions, state digests, hash chain, materialized head and snapshots. This is **integrity detection**, not a cryptographic signature: anyone with filesystem write access can alter the SQLite file and recreate hashes. Signed remote event receipts, identity verification and external checkpoints are future security work.

## Offline research and reconciliation

An offline branch is a separate JSON file containing the base scene and history cursor, stable branch ID, epoch, rules and manifest version, and provisional proposed actions. It never mutates the host at staging time. The file is explicitly not world canon and its contents must not be narrated as authoritative Village memories.

Reconnection rechecks lab identity, epoch, schema/rules and manifest. Proposed actions are submitted against the latest authoritative world with per-object version preconditions, inside a single-writer transaction. A changed affected object becomes an explicit conflict, even when the wall-clock time of the offline action is later. A changed unrelated object need not block a semantically valid proposal. The host still re-runs all physical constraints.

In v0.1, the offline queue prohibits overlapping staged mutations that touch the same object. This conservative limitation avoids improperly reparenting dependent offline actions until a causal dependency/rebase system exists. A failed proposal remains conflicted in the offline record rather than editing the host event log. Outcomes are persisted one at a time; retry after a lost acknowledgment deduplicates accepted commands by stable proposal event ID. The queue is a research-side *proposal* mechanism, not multi-master replication.

The JSON queue has no network authentication, tamper-proof custody, signer keys, or third-party consent. Do not import externally supplied queue files without trusted operator review. Offline branch promotion only certifies **accepted local laboratory events**, never Village canon.

## Recoverability

SQLite native backup produces a transactionally consistent copy even with WAL files. The source and restored database are verified through full replay. Restores create a new destination and will not overwrite a living database. Backups must be separately copied off-host by the operator; this prototype does not claim such a drill was performed.

The explicit snapshot table ties scene JSON and state digest to a revision and event hash. The first snapshot is revision zero; further checkpoints are operator-triggered. The current build makes no destructive reset command. Research experiments should use restored clones rather than rewinding or rewriting the authoritative history.

## Trust and safety boundaries

Only trusted local command callers are supported. The local actor allowlist documents possible research principals but is **not authentication**. There is no HTTP endpoint, signature/MAC, credential storage, network sync, public viewer, consent authority, or Evennia adapter. All recorded events use visibility=research_private. Notebook text is private research data and cannot be projected or published by default.

A future interface must accept separately authenticated and authorized commands, enforce actor/mask/operation scopes and third-party consent, attach signatures or MACs with rotation and provenance, and distinguish who observed an event from who requested it. Evennia retains player, public inventory, door, room, timeline, consent, account/mask, and canonical game-event authority. No laboratorial object can appear in a public Village room merely because its research host event was accepted. Mirror publication requires an independent Village approval and an origin-event deduplication ledger.

Pretorius is not present at Village launch and his leased shop remains dark with the OPENING SOON sign. The site, door, story arrival, and disclosure boundaries have no decision here. Invited-alpha scope and Gate C are unaffected.

## Staged delivery / evidence

L0: stable research lab, durable DB, object definitions, checkpoints, verified backups and non-destructive restore, present in this repository.

L1: local typed event envelope, hash chain, unique origin events, deterministic replay, event and state version checks, present as an **internal format**, not an interoperable signed wire standard.

L2: research offline proposals, selective local-host acceptance or conflict, epoch quarantine and lost-ack deduplication, present in conservative form. Causal dependent multi-command offline merges are not supported.

L3: shadow read-only Evennia projection and authorized origin mapping, **not built**.

L4: explicit Village keeper/canon decision and player permissions, **not authorized**.

L5: multi-host reconnect, signed grants, independent operator recovery, real off-host soak and production assurance, **not built**.

## Upstream links

The Doctor Lives issue #46 and design PR #45: https://github.com/Azimn/The-Doctor-Lives/issues/46

Frankenstein Village issue #48 and design PR #47: https://github.com/Azimn/frankenstein-village/issues/48

The existing Stage 04 world_host_ledger.py is referenced in upstream design notes, but was not present at the exact main path queried when this initial repository was bootstrapped. Do not claim code reuse or schema equivalence without a source-level parity and import test.

## Migration prerequisites

Before connecting to an upstream experiment, identify its actual Stage 04 world-host source ref and verify object definitions, ticks, provenance and event semantics. Build an explicit read-only importer with an attested source digest. Never copy an archive or synthesize a lived memory by silently treating imported events as new experiences.

Before Evennia synchronization, freeze a canonical versioned schema and test adversarial actor attribution, forged receipts, privacy, revocations, world epoch splits, object duplication, scene ownership, item already moved, clock mapping, backups and interrupted deliveries. Only then consider a development-only shadow projection.
