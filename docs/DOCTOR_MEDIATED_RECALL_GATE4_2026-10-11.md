# Gate 4 — Model-selected recollection before physically verified action

**Date:** 2026-10-11 (Chicago local).  
**Status:** research-only diagnostic stacked on unmerged Gate 3 and Gate 2.  
**Production boundary:** unchanged \`Azimn/The-Doctor-Lives@56aab5493ef48cdb560881a138b2277ca6ebcce0\`. No canonical Pretorius state or Frankenstein Village integration is touched.

## Motivation

The pinned 135M local renderer in Gate 3 scored **3/8** correct bench actions and output option A in all eight action attempts; a separate action-order probe found A under three permutations. The current Doctor brain did **store** the verified balance observation. A four-cue source-verified audit showed the reading resurfaced in its protected first-person frame only with a targeted balance-recall question, not with generic action goals. These findings do not support an inference of improved memory-guided action.

This diagnostic separates a **retrieval decision** from **physical action selection**, without letting an engineer pick the profitable memory or replace an invalid action.

## Exact apparatus

- An opt-in, model-selected short recall gate proposes one of three first-person opportunities: try to remember something, act with what is already available, or abstain. Their A/B/C label order is rotated by a fixed pre-specified formula across tasks and delivered/withheld conditions.
- If it selects recollection, the **same pinned local model** must generate a first-person question itself; a strict parser accepts only a brief human-readable question starting with a self-memory interrogative and rejects machine-control strings, invalid formats and fabricated answer keys. The question is **not** supplied from the previous engineer audit, the answer, the source hash or the benchmark scoring key.
- The question is relayed through the existing Doctor \`PretoriusBrainPort.render_request(user_input=...)\`, returning a **production-projected SubjectFrame only**. That API labels the query as externally cued; therefore this is **model-selected, host-mediated recollection**, not a validated internally generated Pretorius cognitive thought. No raw cognition scores, hidden host true mass or database records enter the decoder. The experimenter does not select a helpful response.
- If recollection succeeds, only protected first-person strings from the requested frame and the original frame are joined using a fixed token/entry budget, without source-based answer picking. If it fails, the actor abstains; the host does not substitute another choice.
- Action selection is still the existing pinned local 135M model under strict single-letter decoding, now with the concrete legal-action option list independently rotated across tasks and measurement exposure. Only the existing physical authorization gate executes a legal action and generates a hash-replayable host receipt.

The model's ordinary action decoding remains capped at 8 tokens. Generating a grammatical memory question uses a **separate fixed 32-token output budget**; this was added as an interface-correctness fix, not a change to the model or learned weights.

## Current diagnostic battery

Two decision methods, each with four bench task variants crossed with delivered/withheld source exposure (16 trials total):
1. **No recall:** action proposal directly from the protected original SubjectFrame. This is the original renderer under action-order counterbalancing.
2. **Model-selected recall:** the model independently chooses whether to request recollection, selects its own question if appropriate, then decides among the identical concrete action affordances.

The four prompts paraphrase known beaker-bench objectives: (i) leave only when a mass reading is known; (ii) obtain a fresh second measurement; (iii) inspect the workbench first; (iv) depart immediately. Because the goal families are already public from Gate 3, this is **not a genuinely held-out task benchmark**, and any increased score would be exploratory diagnostic evidence only.

Scoring happens in a separate Python interpreter reopening real saved world and real Doctor cognitive states. Correctness requires an accepted source-backed host event for the actual target action and appropriate instrument-event increment, never a stated intention. The scored report also includes whether a generated question was accepted, whether the protected queried frame contained an instrument reading, and the selected action and first-option identities. These audit fields are calculated on the engineer side and never alter policy choice.

## Interpretation rules

- Improvement that disappears under action-label rotation is **letter position bias**, not learning or memory improvement.
- An accepted self-generated question without the instrument record in the **subject frame** demonstrates selection of an inquiry but not successful recall.
- An instrument reading resurfacing in the protected frame is **availability**, not proven attention, understanding or accurate future behavior.
- Any observed difference on these four goals can suggest where to fix the integration but cannot establish a general-purpose cognitive advantage. The strong retrieval-only controller from Gate 3 remains the comparison reference at 7/8 on its original tasks, not a numerically identical new treatment baseline.
- This trial does not validate natural unprompted inner monologue, subject consciousness, authentic 1890s weight measurements, autonomous goal choice, or Village operation.

## Next independently confirmable milestone

A stronger, frozen, locally executable decoder should be benchmarked **without tuning on these sixteen cases**, with genuinely unseen objects, counterfactual physical relocation, balanced action order, and a real subject-owned query interface in the Doctor brain (rather than passing its question as a simulated user's instruction). A shared memory-source gate must separately record what actually entered the candidate frame and what was simply persisted in hidden memory. Only model-caused, host-verified outcomes under a new sealed task set can support behavioral improvement claims.

The relevant exact-headed CI is \`.github/workflows/doctor-mediated-recall.yml\`. It pins both the production Doctor repository and free local model and saves \`mediated-recall-score.json\` plus source commits. No result is claimed here until that exact run completes.


## Verified results and failure classification

The exact-source [revised 32-token question-budget CI run 38204076151](https://github.com/Azimn/Pretorius-Laboratory/actions/runs/38204076151) passed all 5 recall-boundary tests and completed the 16-arm frozen research diagnosis. All action receipts were independently reopened and source-verified; the result is **negative**:

| Route | Goal-correct accepted physical decisions | Successful cue requests | Retrieval frames surfacing source measurement |
| --- | ---: | ---: | ---: |
| Existing 135M local renderer with no new recall step | **2/8** | N/A | N/A |
| Same renderer allowed to decide whether to seek memory first | **0/8** | **0/8** | **0/8** |

The revised model-selected route **abstained in all eight trials** at the recall decision stage, without generating a memory question. The first short-question-budget CI run [38204010492](https://github.com/Azimn/Pretorius-Laboratory/actions/runs/38204010492) also scored 0/8 for recall and 2/8 for direct action: seven early abstentions and one decision to act without requesting memory. The change to the fixed 32-token question-generation budget was therefore *not* sufficient: the blocking action was refusal/invalid choice at the earlier model-mediated recall gate.

These scores are not a proof that the production Doctor brain cannot retrieve, reason or act in general. The prior protected multi-cue Doctor audit independently verified **successful targeted retrieval when a suitable external question was supplied**. The current small local renderer cannot yet reliably *choose* that question under the tested interface. The current Doctor public port also labels model-authored self-questions as if they were user-originated prompts; this is a genuine subject-ownership gap independent of model quality.

**Next engineering repair (separate unscored PR):** establish a strict research-only, read-only *subject-owned query capability* that retrieves Doctor's existing memories into an already protected first-person SubjectFrame without inventing an external user's message or exposing database facts. Test it with an explicitly controlled query, including absence in the withheld control, no implicit brain-state mutations, and no raw engineering state. Do **not** credit a researcher-forced query as autonomous recall or rerun this same known eight-task battery and claim new blinded evidence.
