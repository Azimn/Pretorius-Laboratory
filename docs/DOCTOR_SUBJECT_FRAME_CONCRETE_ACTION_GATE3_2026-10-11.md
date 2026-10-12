# Gate 3 — Protected SubjectFrame Concrete Tool Proposal

Date: 2026-10-11  
Branch: \`research/doctor-legal-actions-gate2-20261011\`, stacked atop unmerged research PR #14 (and #13). Production The-Doctor-Lives remains unmodified.

## Research motivation and controls

Gate 2 showed that the actual production Doctor recurrent policy, passed through a fixed abstract-tendency-to-tool mapping, made the **same concrete action** whether a prior balance result reached the brain or was withheld (5/12 successes across six seeds), while a strong source-based decision rule achieved 12/12 on that small task. See the immutable [Gate 2 null result](DOCTOR_LAB_DELAYED_ACTION_GATE2_2026-10-11.md). The next test addresses the **language-rendering/action-selection seam**, not the internal brain architecture.

The proposed candidate is the pretrained **SmolLM2-135M-Instruct** language model (Apache-2.0), run on CPU using local weights at Hugging Face commit \`12fd25f77366fa6b3b4b768ec3050bf629380bac\`. The model is separate from Doctor's recurrent substrate and **must not** be described as a new mind, a recovered production character, or learned cognitive efficacy. It serves only as an experimental **external language action renderer** consuming the existing production protected \`PretoriusBrainPort.render_request(...).subject_frame\`. It has no authority to edit memories or act directly; it cannot see the production brain's raw state, memory-record IDs, scores, embedding layers, hidden object mass, original world events, event hashes or source control labels.

The model sees exactly: (1) the first 18 subject-native first-person frame items within 7,500 characters, including a first-person projected user objective; (2) an ordered collection of first-person **currently legal** laboratory actions from the established \`LegalBenchActionGate\`; and (3) an instruction to output one option letter. The response must match a single A/B/C/D option label. Anything else **abstains**. There is no fuzzy parsing, success-seeking action replacement or model-chosen arbitrary tool operands. Each accepted action is validated again against current physical world and persisted under the host's own event receipts.

## Frozen counterbalanced tasks

The new, small benchmark uses four goal texts, each crossed with delivered/withheld original measurement exposure; the complete task and answer keys live **only in the engineer scorer** at \`doctor_holdout_protocol.py\`. The local model gets the goal as a projected first-person message and the subject frame, not the task ID or expected action.

| Task | Delivered goal-correct action | Withheld goal-correct action |
| --- | --- | --- |
| Avoid repeating a known mass measurement | leave | weigh |
| Obtain a new confirmatory measurement even if earlier result known | weigh | weigh |
| Inspect what is physically on the bench first | inspect | inspect |
| Leave the bench immediately, regardless of unfinished measurement | leave | leave |

This is **eight new tasks per controller**, not a statistically powered performance study or blind generalization test. The task list was written after earlier Gate 2 results, so it is a **new engineering benchmark**, not independently preregistered evidence.

The local model is compared to two unchanged or transparent alternatives:
- **Existing Gate 2 neural abstract action-to-tool mapping.** Its existing abstract recurrent scores and frozen mapping are *not* tuned to these goal texts. It remains a deliberately goal-insensitive legacy control.
- **Transparent goal-aware non-neural rule.** This controller uses only the same subject frame and a frozen rule over the natural-language task. It shares production Doctor's stored observations. It was written for these public benchmark objectives and is therefore **not a blind learned-policy comparator**. Its score is a sanity/control ceiling, not validation of cognitive novelty.

Every controller's scenario begins with a separate existing-disposable Pretorius brain and lab world, with accepted beaker measurement physically performed by a **scripted experimenter**; this setup does not count as policy agency. The controlled exposure toggles only whether that accepted instrument result is delivered through the existing brain subject ingress and persisted before the later action proposal. A new Python process loads the current goal and obtains the next action from a controller. A third process verifies the resulting exact host event ID/hash and source-world histories and independently scores correctness. Abstentions, ineligible actions, look without inspection goal, repeated measurements when avoidable, and narrated but unexecuted actions do not receive positive scores.

## Current experiment boundary and nonclaims

This is a renderer/plugin *tool selection experiment*. It is **not** full Pretorius cognition becoming a free-running actor, continuous control in Frankenstein Village, a neural learning demonstration, a stable autonomous goal selection process, authentic historical instrument perception, an identity consistency comparison, or a demonstration of consciousness.

If the language model outperforms the static map, one interpretation is that a general-purpose decoder can produce more conditional legal action choices from the same bounded frame. Such performance would not prove the recurrent brain caused the improvement; the memory/state ablations and a real retrieval-only decision control remain crucial. Conversely, weak performance does not disconfirm all models or all neural cognition—it only localizes a failure under the specific small renderer, framing and finite action list.

The next *genuinely independent* gate should use withheld/new objects, counterfactual physical changes and a separate non-scripted model-selected longer physical sequence, while controlling token budget and provenance access. No production PR should merge purely because a four-goal test is green.

## Reproduction

The separate [subject-frame local model GitHub Actions workflow](../.github/workflows/doctor-subject-frame-local.yml) installs the fixed real production Doctor brain, the current research lab, CPU-only PyTorch/Transformers, and **downloads an exact-pinned free language model**. No API keys or paid model access are required. The workflow runs strict prompt-and-action-boundary tests then the full task benchmark, saving machine-readable \`subject-frame-score.json\` and both exact Git source commits as artifacts.

**Verified evaluation results, including negative outcomes, must be recorded from the exact successful model workflow and not from unit-test substitutions.**
