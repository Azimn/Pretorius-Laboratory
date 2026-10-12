# Subject-Owned, Read-Only Recall Query — Research Boundary

**Date:** 2026-10-11 (America/Chicago).  
**Status:** green cross-repository research integration test; **not** a production Doctor Lives API or autonomous learning demonstration.  
**Research PR:** [#16](https://github.com/Azimn/Pretorius-Laboratory/pull/16), stacked on the preserved [Gate 4 null #15](https://github.com/Azimn/Pretorius-Laboratory/pull/15).

## What was wrong

The existing production port \`PretoriusBrainPort.render_request(user_input=...)\` can use an ordinary question to guide memory retrieval, but it projects that question as **a message received from an outside User**. Sending a model's self-generated query through this path creates a misleading attribution: Pretorius appears to have heard another person ask the question.

Gate 4's real pinned small local renderer also failed to *choose* useful recollection at all (0/8 corrected actions, zero accepted questions). That is a separate **decision-policy failure**, not evidence that the original brain lacks the memory or that forced retrieval is unavailable.

## Research-only repair

\`SubjectOwnedQuery\` is a **trusted, read-only** adapter using existing production components without modifying production \`The-Doctor-Lives\`:

1. Accept only a short, natural, first-person self-question under a strict allowlist, rejecting control instructions and requests for machine-native state.
2. Ask the production \`PretoriusBrain.cognitive_view(query=question)\` to retrieve material using its original memory ranking; **no host-selected source row** is injected.
3. Pass the view directly through the Doctor's existing \`_subject_frame_from_view(view).renderer_context()\` projector.
4. Return only the resulting first-person text, alongside a research claim that the query is *model-authored but not proven neural self-initiation*.
5. Check brain tick, state-version and store digest both before and after retrieval. Any unexpected mutation raises an exception; the adapter makes no accepted memory or neural-change event.

Importantly, this uses two non-public Doctor cognition/projector methods, behind a trusted experimenter port. It **does not** itself form a new public, stable or unprivileged production interface. Exposing it to an Internet-facing renderer or claiming independent authorization would be premature.

## Accepted engineering tests

The [exact pinned real-Doctor CI run 38204340859](https://github.com/Azimn/Pretorius-Laboratory/actions/runs/38204340859) passed four cross-repository tests against \`Azimn/The-Doctor-Lives@56aab5493ef48cdb560881a138b2277ca6ebcce0\`:

- A **forced targeted** question about the laboratory balance returns the exact existing, verified synthetic **325 g** reading in the delivered arm, but does not surface it in the identically instrumented *withheld* arm.
- The subject frame does not report a fabricated incoming message from an external User and exposes no raw engineering records or calibration fingerprints.
- Repeating the query creates no extra autobiographical memory and does not mutate the accepted brain state.
- Host-diagnostic queries and control-instruction-like questions fail closed.

These tests prove **a cleaner route for engineer-mediated retrieval**. The forced question is an **engineer positive control**, not scored as Pretorius's spontaneous thought or the local decoder's successfully selected inquiry.

## Promotion gate

Keep the Gate 4 action score fixed at **2/8 direct vs 0/8 model-selected recall**; do not run this forced cue through the old scorer and call it an independent improvement. Before this adapter could be considered for a production Doctor port:

1. Create an explicit, authorized subject-owned query capability within the *Doctor-owned public subject interface*, eliminating reliance on private \`PretoriusBrain\` methods.
2. Separate model-proposed internal question, read-only memory lookup, and experienced answer, with source-access receipts that do not themselves become false memories.
3. Require model-driven query and legal physical action under a **new sealed, counterbalanced task battery** with withheld and source-removal controls, compared to the frozen recurrent and stateful non-neural baselines.
4. Verify meaningful downstream action outcomes after fresh-process restart, independent of the engineer's positive control.

No canonical Pretorius brain, production behavior, model weights or Frankenstein Village content changed in this research PR.
