# Gate 5: stronger local action language model, same Pretorius brain

**Status:** research-only stacked PR #17. No canonical character state, model weights, physical-world history, or Doctor Lives production code modified.

## Why this test exists

The original `SmolLM2-135M-Instruct` consistently chose the first listed option on the four-goal action diagnostic. A prior retrieval audit also found a stored instrument observation may be absent from an unconstrained subject-frame query, although an appropriately targeted question can surface it. Those are separate potential causes: **decoder capacity/presentation bias** versus **retrieval accessibility**. Upgrading the language decoder alone cannot establish which is decisive.

This experiment replaces only the **action/recall language decoder** with [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct), using a verified fixed Git commit prefix `989aa79`. The exact resolved full model Git revision is retained in CI's `decoder-provenance.json`. The prior 135M runner and baseline still exist. All output remains local CPU inference, no paid inference provider, no model-edit access to Pretorius's brain database, no direct world-admin status.

## Data/subject trust boundary

An independent research controller does the initial beaker measurement identically in delivered and withheld arms, then delivers only allowed first-person instrument words to Doctor Lives ingress when appropriate. The existing production `PretoriusBrainPort` remains the sole owner of saved neural and memory state.

The stronger model is a **renderer** over the same existing first-person SubjectFrame, a natural subject-directed goal, and a shuffled finite list of legal acts from `LegalBenchActionGate`. It sees neither the experiment condition label nor hidden beaker mass, source checksums, event hashes, raw memory rows, action scores, or the scorer's correct-action key.

A model must select **A/B/C/D exactly** or abstain. The host independently rechecks placement/action eligibility and executes the proposed physical action. A separate interpreter verifies SQLite physical event receipts and scores the actual outcome, not the model's self-report.

When recollection is enabled, the model first chooses **remember, act now, or abstain**, with answer positions rotated. If it chooses recall, it generates a brief first-person question using a dedicated question-generation instruction and longer token budget; the existing Doctor renderer projects any returned memory as first-person natural language. The research controller may not manually insert a known-useful memory. This is **mediated** retrieval: `render_request(user_input=...)` still treats a generated question as an externally cued query, not proof that the cognition system spontaneously queried itself.

## Frozen comparison and quality gates

The research diagnostic retains the previous four task texts, observed/withheld source exposure and two variants (**no second retrieval** and **model-selected second retrieval**), totaling 16 new trials per decoder. Legal-action ordering is counterbalanced. The old 135M result is **historical**, not a new independent run on an unexposed blind holdout.

The run must report separately:
- Actual objective-correct host actions, including abstentions and errors, for both variants;
- Number of optional recall decisions, accepted first-person questions, and readouts actually available in the resulting protected frame;
- Whether the action varies appropriately with the goal and delivered-versus-withheld evidence rather than tracking answer position;
- Exact Doctor brain Git SHA, lab research SHA, model SHA, dependencies and scoring code.

**Interpretation:** A higher score would support the narrower claim that a stronger *external decision renderer* uses the bounded context better on these tasks, **not** that the recurrent neural substrate learned, that Pretorius achieved autonomous identity continuity, or that subjective awareness exists. A model that still chooses the first choice or repeatedly abstains has not solved the issue. A production promotion requires additional genuinely novel blind goals/objects, matched memory ablations, model-independent action authorization and explicit temporal memory retention tests.

No Frankenstein Village connection is changed.


## First verified model-capacity comparison

The unchanged 135M reference was re-executed at [CI 38205106560](https://github.com/Azimn/Pretorius-Laboratory/actions/runs/38205106560). The stronger 1.5B model completed its first **16-arm** experiment at [CI 38205106641](https://github.com/Azimn/Pretorius-Laboratory/actions/runs/38205106641), with resolved full Hugging Face model Git SHA `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.

| Task variant | SmolLM2 135M | Qwen2.5 1.5B |
|---|---:|---:|
| No additional retrieval, objective-correct host acts | 2/8 | **4/8** |
| Model first decides whether to recall, objective-correct host acts | 0/8 | **2/8** |
| Successful elective extra recall requests | 0 | **0** |

The stronger renderer improves the performance of the *initial* action-selection task, but it still never chose a valid retrieval request at the metacognitive gate. This is a partial improvement, not evidence of spontaneous memory-guided behavior. It does **not** isolate model size from training data, checkpoint, prompting or architecture, and it does not justify a treatment-effect claim from eight task contexts.

### Explicitly separate allocated-question diagnostic

A subsequent controlled condition `allocated_model_question` gives the external renderer exactly one opportunity to formulate a **model-written** first-person memory question before action selection. It bypasses the separately failed question-*initiation* meta-decision; the host cannot supply a known useful cue, alternate an invalid query, or select the correct act. This is not autonomous memory initiation and is **not part of the original baseline**. Report its own valid queries, actual frame retrieval evidence and independently verified physical-action score. Distinguish it from the old `model_selected_recall` arm.
