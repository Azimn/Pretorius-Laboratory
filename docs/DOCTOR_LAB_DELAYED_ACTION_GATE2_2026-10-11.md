# Doctor Lives × Laboratory — Gate 2: Delayed physical action choice

**Date:** 2026-10-11  
**Research status:** ENGINEERING PASS for bounded legal action execution; **BEHAVIORAL ADVANTAGE NOT DEMONSTRATED**.  
**Authority:** laboratory [PR #14](https://github.com/Azimn/Pretorius-Laboratory/pull/14), **stacked on unmerged PR #13**; not eligible for automatic production promotion.  
**Production cognition pinned:** \`Azimn/The-Doctor-Lives@56aab5493ef48cdb560881a138b2277ca6ebcce0\`.  
**Base laboratory pinned:** \`Azimn/Pretorius-Laboratory@290ec97727c84728e61f69265949551e4ce911ec\`.  
**CI evidence:** [run 38143905018](https://github.com/Azimn/Pretorius-Laboratory/actions/runs/38143905018), full green; seven genuine brain-memory integration tests and eight legal-action unit tests passed; a 24-arm, fresh-process, six-seed delayed-choice battery passed its *execution/replay* checks. Research workflow uploads detailed \`action-score.json\` and the earlier \`score.json\`.

## The necessary distinction

The physical laboratory is the sole authority over the actual room, instrument events, actor position and side effects. The Doctor Lives brain owns existing recurrent activity, cognition and saved memory. This is **not an LLM text-generation tool-use experiment**. The production Doctor's ordinary ten-way *abstract* action tendencies are translated to a small, fixed legal action vocabulary using a **frozen, explicitly non-learned map**:

| Abstract cognitive tendency | Proposed concrete bench action |
|---|---|
| explore, create, challenge | Weigh the beaker |
| approach, persist, comply | Inspect the workbench |
| avoid, conceal, dominate | Leave the workbench |
| cooperate | Abstain |

The map is not informed by the hidden scoring goal or answer. If a mapped action is no longer legal, it abstains rather than substituting a known-successful action. Model/tool operands cannot be freely synthesized; an engineer-side action gate offers only grounded opportunities available **now**: weigh the actually present beaker, look, walk to the adjacent center, or abstain. Each is independently checked by the laboratory when executed, and the final scorer verifies the accepted host event ID/hash from persistent SQLite history. A host veto, look, abstention, or scripted setup does not count as a successful cognitive decision.

Subject-facing descriptions and goals use natural first-person or subject-safe communication, never raw action scores, world coordinates, source checksums, private object mass, database rows or event revisions. Protected scores and proposal/eligibility diagnostics remain **engineer-only**.

## Task and controls

The narrow goal is to **obtain a reliable, bounded beaker-mass reading before leaving the bench, without redundant measurement**. A trusted experimenter first brings the research actor to the bench and performs the initial physical measurement. The actor receives the balance's rounded synthetic reading (325 g ±13 g) only in the delivered arm. The withheld arm has the same one original accepted physical measurement event but does not receive the first result. Both arms use fresh, separately persisted actual Pretorius brains.

After a new interpreter opens the saved world and brain, each controller gets the same user-safe goal and exactly one delayed physical action opportunity:

- With initial reading delivered: **leave**; weighing again is redundant.
- With initial reading withheld: **weigh**; leaving without knowing the result is premature.

The decision is made by either (a) the real Doctor Lives recurrent policy through the fixed map or (b) a **strong retrieval-only, non-neural decision comparator**, which inspects its own source-matched persisted measurement record and applies a transparent rule. The comparator is not given the experimenter-assigned delivered/withheld label, the raw beaker mass or the answer from a host oracle. It **does share the production brain's persistent memory store** for matching inputs, so it is a non-neural *decision policy*, not a completely separate non-neural memory engine.

Crucial correction: the earliest one-seed prototype handed the baseline its intervention label; this was identified and corrected **before** the six-seed sweep. The final comparator queries the source-bound stored observation instead. The earlier \`1/2\` vs \`2/2\` result is preliminary and should not be reported as an independently fair control result.

## Frozen small-seed sweep and outcome

The expanded engineering sweep used **six fixed recurrent seeds:** 11, 31, 47, 127, 1842 and 2026, each under measured/delivered and measured/withheld conditions, for **12 Doctor and 12 retrieval-only delayed actions**, 24 arms total. This expansion was designed **after seeing the original seed-1842 result**, so it is exploratory, not an independent preregistered efficacy confirmation. Action mappings and outcome rubric were fixed before the six-seed execution.

| Criterion | Real Doctor recurrent policy + fixed action map | Retrieval-only non-neural decision policy |
|---|---:|---:|
| Delivered: leaves rather than repeats an already known measurement | **0/6** | **6/6** |
| Withheld: measures beaker because result was not available | **5/6** | **6/6** |
| Combined goal-correct delayed physical actions | **5/12** | **12/12** |

The actual Doctor policy made **identical action choices in its delivered and withheld pair for every seed**. In five seeds it proposed a second weighing in both conditions; in seed 11 it inspected in both conditions. No condition-dependent behavioral adaptation was observed. The laboratory independently accepted the applicable actions and the scorer checked their genuine persistent physical consequences. Results are archived in the exact-run CI \`action-score.json\`, not reconstructed from anecdotes or narrative success labels.

These comparisons are not a statistically powered inference about all models or all cognitive tasks. The fixed abstract-to-tool mapping may be the dominant bottleneck. A single test goal, six small-network initializations, deterministic synthetic physics and access to only three applicable actions sharply limit generalization. However, the **specific current route from an admitted observed measurement to a different action has failed this controlled test**. Stronger causal claims await a genuine context-conditioned tool proposer and independent holdout tasks.

## Replay, provenance and safety

The earlier admission bridge accepts a host-certified instrument receipt exactly once into the existing \`PretoriusBrainPort.ingest\`. This new gated action layer accepts no freeform operator script, invented operand or unapproved relocation. The accepted action has an independent physical event, not merely the neural policy's assertion. A separate third Python interpreter opens both persistent states and scores the concrete host outcomes. The newly performed second weighing, when selected, is also admitted through the original source-bound measurement ingress rather than through model testimony.

Only disposable world epochs and brain state directories are used. This branch introduces no new production Doctor state schema, no new neural organ, no transfer of alleged personal memory, no connection to the Frankenstein Village runtime.

## Next engineering and research step

The evidence points to a **specific action selection interface**, not an immediate need for a new cognitive architecture. Build a **subject-frame-grounded** concrete action proposer that reads the actual limited firsthand measurement percept and visible eligible actions, forms an explicit prediction of outcome, chooses or abstains, and preserves a separate host authorization contract. Keep the current fixed neural mapping and the retrieval-only comparator as controls. An LLM-based proposer, if added, must be pinned and run locally/CI without paid API and must not have raw protected telemetry. Test counterbalanced objectives, conflicting measurements, misleading self-report, memory removal, shuffled source mappings, and blind holdout grading.

Do not optimize policy mappings against these six seeds and then label the resulting replay a new independent finding. A valid improvement requires a frozen new experiment with held-out tasks, genuine model-dependent action proposals, objective source-verified consequences and separate-process restart.
