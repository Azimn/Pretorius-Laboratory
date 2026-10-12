# Gate 6: subject-owned read-only recall in legal laboratory decisions

**Status:** research-only integration candidate, stacked on Gate 5 PR #17. Reuses the independently validated protected query adapter from PR #16. This is not a new Doctor Lives public interface or Village change.

## Purpose

Gate 5's exact-head completed Qwen diagnostic found 4/8 correct without an extra recall opportunity, 2/8 when the decoder had to elect recall, and 3/8 when a second question opportunity was assigned. Six questions were attempted in the allocated arm, but zero protected post-query frames surfaced the source-backed 325 g beaker reading. Previously, those model-written self-questions were incorrectly routed through `render_request(user_input=...)`, attributing internal inquiry to an outside user.

This gate holds the same pinned brain, Qwen weights, task texts, goal exposure, objective correct action, physical authority and legal option permutations fixed. A fourth clearly named research condition allows an **assigned question opportunity with model-written text**, but sends any valid question via the existing read-only Doctor cognitive view and first-person projector without forging a new incoming User event.

## Implementation and boundaries

The existing direct, model-selected, and externally cued allocated branches remain unchanged in name and scoring. The new `allocated_subject_owned_query` arm uses the exact adapter developed and source-verified in PR #16. Only subject projected strings reach the action renderer. A failed or invalid question abstains, without a host-selected corrective query or a substitute legal act. Re-querying for an engineer-side evidence check is read-only and must not create memories or action credit.

All four arms have four existing bench objectives crossed with actual-delivered versus withheld instrument ingress (32 trial instances on a fresh CI run). Results are scored after reopening the hash-verified SQLite world and require an independently accepted physical event. The existing result from Gate 5 is not relabeled as if this new arm had already been measured.

Do **not** interpret an engineer-assigned opportunity as spontaneous neural recall. Do **not** interpret a successfully projected source record as a gain in action correctness without independent source-backed effects. The tasks are still publicly known; this is an integration diagnostic rather than a novel blind holdout. Model size, learned cognition, autobiographical identity and subjective consciousness are not tested here.

## Acceptance and stop conditions

The focused tests must prove that a generated self-question is passed to `SubjectOwnedQuery` and **never** arrives as `User` through the old rendering port. They must also prove failure-to-retrieve abstains without executing an action, that unassigned methods cannot silently activate the new retrieval route, and that the actual Doctor readonly projector passes its existing delivered/withheld and nonmutation tests.

The pinned free CPU model CI must report each route separately, including correct accepted actions, generated questions, verified retrieved readouts and abstentions. If the new route still produces zero useful recalled evidence or no score gain, record the null; do not automatically tune prompts on these known items and rebrand them a blind result.

Before production promotion, a proper public Doctor-owned internal query capability and a **sealed new-object, changed-location memory-ablation task family** remain required. Keep Frankenstein Village and canonical Pretorius state untouched.
