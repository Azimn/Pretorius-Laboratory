# Doctor Lives × Permanent Laboratory: Instrument Ingress Gate 1

**Date:** 2026-10-11  
**Status:** research-only integration prototype, review pending; *not* promoted into the production Doctor brain.

## Frozen reproducibility authority

- Physical world: [Pretorius-Laboratory](https://github.com/Azimn/Pretorius-Laboratory), base \`290ec97727c84728e61f69265949551e4ce911ec\`; research implementation in [PR #13](https://github.com/Azimn/Pretorius-Laboratory/pull/13). Exact tested branch head and base are emitted to the CI artifact.
- Cognitive system: [The-Doctor-Lives](https://github.com/Azimn/The-Doctor-Lives), exact production main \`56aab5493ef48cdb560881a138b2277ca6ebcce0\` (pinned in the separate CI checkout and SHA-checked before execution). This is the **actual** \`PretoriusBrainPort\` with recurrent cognition, persistent state and its existing provenance-bearing memory admission. No new simulated brain is fabricated.
- Research CI: [Doctor Lives × Laboratory admission workflow](https://github.com/Azimn/Pretorius-Laboratory/actions/runs/38142165200). 7 integration tests passed, including stale/corrupt receipt refusal, one-per-receipt idempotency, partial-crash reconciliation, persisted original world event check, independent world-epoch refusal and later physical relocation of a measured object.
- Same pinned workflow runs a separate-interpreter, two-arm pilot. It saves a machine-readable \`score.json\` containing both epochs, brain digests, instrument-event counts, provenance-class counts and explicit **engineering-only** claims. Artifacts are research evidence, not promotion credentials.

## Interface ownership

**The Laboratory remains authoritative for:**
- Current physical placement, actor's accepted station, real movement/measurement operations and instrument calibration;
- Source-labelled synthetic beaker mass and bounded simulated ruler/balance readout;
- Signed-by-hash, replay-checked local instrument event identity, source world, epoch and custody history.

**The Doctor Lives remains authoritative for:**
- All memory insertion, neural state and thought evolution, source classification and brain checkpointing.
- Memory is admitted exclusively through the production \`PretoriusBrainPort.ingest\` subject ingress path. The research controller cannot directly create or edit Doctor memory rows.

**The research controller is not an agent:**
- It may deliver a verified host instrument readout into the **preexisting** subject-native perception projection, or withhold exactly the same readout.
- It does not choose a goal, invent a new policy, convert the production brain's action tendencies to eligible world acts, or infer what Pretorius attended to.
- Its allowlisted projector converts only known ruler/balance quantities and their bounded measured values into natural first-person instrument experience; it does not copy a raw JSON readout, world UUID, source hash, hidden host mass or actual calibration/protected profile into a subject frame.
- The local \`research-subject:pretorius\` label is a **research identity**, not cryptographic proof that a remote or autonomous Pretorius was authenticated.

## Experimental steps and original matched control

Each arm has its own disposable world epoch, same synthetic initial geometry and beaker and same small neural model configuration (64 recurrent units with frozen seed 1842). Each arm has its own independent new Pretorius state directory, never canonical state.

1. Initialize the persistent physical room, actor, custody, mechanical assumptions and bench instruments.
2. A **scripted experimenter**, not Pretorius's neural policy, walks threshold → center → bench and performs an authorized physical balance measurement of the beaker.
3. The host accepts and records a bounded synthetic reading **325 g ±13 g**, derived from an engineering beaker profile whose protected exact value is **330 g**. The source is not a genuine historical instrument measurement.
4. In the **observed/delivered** arm, the controller first verifies the complete host instrument ledger, matches the specific accepted event ID and hash, and projects the reading through the existing Doctor subject ingress. It saves the resulting brain checkpoint and source-to-memory admission journal.
5. In the **withheld** arm, precisely the same host-side physical measurement takes place, but the research controller does **not** call the brain ingress port. This is a *source-exposure manipulation*, not a cognitive-lesion experiment.
6. Start a **new Python interpreter** to open both existing persistent brain checkpoints, physical-world SQLite files and their admission ledgers. Score admission by original accepted instrument source, not by string occurrences in an LLM's narration. The two-arm \`score.json\` is saved as an artifact.

### Result: engineering-only

| Metric | Delivered | Withheld |
|---|---:|---:|
| Physically accepted instrument events | 1 | 1 |
| Source-matched, brain-admitted instrument memories after new-process restart | 1 | 0 |
| Independent brain and world opened from persisted state | yes | yes |
| Neural policy chose experimenter's measurement action | no | no |
| Numerical prediction / later spontaneous recall / changed handling behavior tested | no | no |

CI output reports \`matched_source_exposure_gate=true\`. The observed record has Doctor's existing \`lived_runtime_memory\` classification, but this constitutes **brain-ingress storage after verified delivery**, not proof of awareness, understanding or reliable eventual recall. The withheld record has no corresponding admitted memory. The actor's physical event history is identical by actions/instrument choice, not byte-identical due to independently created epochs/event IDs. Both arms share the same fixture/protocol.

## Crash semantics and source protection

The research controller uses a sidecar SQLite journal with fixed world-epoch identity and a deterministic per-measurement source key built from the accepted instrument event hash. Receipt presentation must match the original event in full; tampered numbers, altered event hashes, foreign worlds or mismatched source registrations fail closed.

The production brain and laboratory journal cannot commit atomically as two databases. Therefore a simulated crash **after** production brain ingress and before recording a successful bridge delivery is handled by reopening the existing brain source-indexed memory and reconciling *exactly one* matching record. The retry never inserts another measurement memory. If the journal says a delivered memory exists but it has disappeared or changed source, verification fails.

This is local integrity/cross-record coherence only. A fully privileged malicious file operator could replace both databases and their receipts; no network or cryptographic remote-authentication claim is made.

## What this experiment does NOT establish

- No demonstrated autonomous Pretorius goal or meaningful choice; a deterministic experimenter runs the movement/measurement script.
- No measured prediction before observation, no surprise/revision of a belief, no later blind numerical report, and no outcome improvement versus a retrieval-only or non-neural controller.
- No spontaneous self-initiated cognition, subject consciousness or demonstrable "lived attention."
- No promotion of research module to production Doctor main, no editing of canonical Pretorius state, no Frankenstein Village integration.
- A single matched source-exposure case is a **software correctness check**; it does not estimate a generalizable treatment effect.

## Next independently reviewable gate

**Gate 2: Cognition → legal action choice → observed consequence → later independent choice.**

Pin the same production model and world revisions, then author a hidden physical task. Implement a capability-scoped action proposal port that displays only subject-native affordances, validates a model or policy-proposed action/operand pair against host eligibility, and does not let the controller select the goal-relevant answer. Require logged premeasurement expectation, actual approved measurement action, material world consequence, and a later, separate-context retrieval/redecision attempt. Compare at minimum (a) full production policy + verified measurement, (b) same policy + measurement withheld, (c) strong stateful non-neural retrieval baseline. Independently score goal completion, irrelevant/denied action proposals, false firsthand memory, abstention, numerical calibration, and changed choices; never credit the deterministic host's scripted actions as neural policy successes.

Review this PR and those gates independently under The-Doctor-Lives [Issue #53](https://github.com/Azimn/The-Doctor-Lives/issues/53) before considering promotion into production. The old runbook's one-turn evidence and separate reviewer gates still govern production changes.
