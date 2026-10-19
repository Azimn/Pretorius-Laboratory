# Doctor residency: ChatGPT as a provisional renderer

**Research protocol: 2026-10-19. Status: manual experimental field trial.**

## Purpose

Give Pretorius ordinary first-person household perceptions and many possible activities without a scripted daily agenda. Ask a strong ChatGPT renderer to choose independently what he would try, including activities the world does not yet support. Record barriers and genuine consequences. ChatGPT may supply language, reasoning, memory of the chat and initiative that the small future model will lack. Do not credit those supplied abilities to the Doctor's native cognitive architecture.

No OpenAI API key or paid API is required. **This is a human-paced copy-and-commit workflow.** GitHub Actions does not run ChatGPT or autonomous dialogue. There is no unattended life loop.

## Different kinds of existence

- **Verified physical consequence:** a moved chair, real bookmarked page, consumed tea, written page, pressed flower, changed apparatus. Only the original Laboratory material reducers can commit these. Field-trial records cite the original event hash.
- **Long-lived prospective intention:** a project begun, paused, reviewed, resumed, abandoned or self-declared finished. This is a genuine choice record, not proof the experiment physically succeeded.
- **Narrative-only color:** rain-like sounds, momentary thoughts, a strange noise, or an unverified impression. Log separately as narrative_only_unverified. It neither changes material-world conditions nor becomes authenticated perception or canonical memory. If it causes a lasting effect such as a wet coat, that effect needs its own supported source-world transition.
- **Unsupported intended action:** log the original attempted phrasing, barrier category and world stamp. Do not lie to Pretorius that the physical deed occurred.

This text simulation needs consequential identities, placement, conditions and receipts, **not microscopic atomic or geometric modeling**.

## Operator workflow without API costs

Create a NEW scratch world, not the inhabited Doctor home:

    python tools/new_residency_world.py scratch/residency.sqlite3

This prepares the physical household, written paper, optional flower/arrangements, project registry and blank source-backed book catalog. It does NOT invent fake books or memories. Existing personal or production files are never overwritten.

Get a new first-person ChatGPT packet:

    python -m pretorius_lab.field_residency --world scratch/residency.sqlite3 --journal scratch/residency.field.jsonl observe

Copy only the **first_person_world**, **possible_activities**, and **instructions** parts into ChatGPT, along with the Doctor's already-authorized identity constraints through his existing first-person interface. Do not supply hidden engineer state, entity IDs, exact counters or internal machine memories.

Ask for a freely chosen intention or no action at all. The renderer can suggest unlisted things. Keep intended action separate from claimed completion. To enact one offered action, relay that first-person action description:

    python -m pretorius_lab.field_residency --world scratch/residency.sqlite3 --journal scratch/residency.field.jsonl attempt --intent "I could start a project of my own choosing." --text "Examine condensation on glass."

Only a result containing status=committed and an actual source_event_hash means the environment changed. Subsequent first-person character observations can refer to those effects.

For an off-script desire, pass the unscripted text. It may be translated by the *bounded tested* furniture-intent parser; otherwise the simulator records a barrier with no world mutation:

    python -m pretorius_lab.field_residency --world scratch/residency.sqlite3 --journal scratch/residency.field.jsonl attempt --intent "I want to build a pneumatic organ in the pantry"

To log a fleeting subjective moment that is NOT a verified meteorological or physical event:

    python -m pretorius_lab.field_residency --world scratch/residency.sqlite3 --journal scratch/residency.field.jsonl moment --text "I think I hear rain against the window."

Review what the unprompted renderer tries to do but cannot:

    python -m pretorius_lab.field_residency --world scratch/residency.sqlite3 --journal scratch/residency.field.jsonl barriers

To reconcile a crash between a committed world action and the audit's success record, without re-executing physical commands:

    python -m pretorius_lab.field_residency --world scratch/residency.sqlite3 --journal scratch/residency.field.jsonl reconcile

The JSONL sidecar is append-only and hash-chained, but remains **an observer study log**, not the canonical world, an alternate life simulation or the Doctor's autobiographical memory.

## What counts as a useful result?

Run 10-20 human-paced turns without an assigned itinerary. Record attempted intentions, supported commits, barriers, ambiguous offers, unsupported creativity, whether objects/bookmarks/projects survive a next-day revisit, and whether the renderer *claims* anything that has no source receipt. Prefer revealing useful missing affordances over increasing an activity-count score. Unused Victorian activities are perfectly acceptable.

Attribution: choices, creativity, planning and fluent language here belong to **ChatGPT as the temporary renderer**. Source-verified object permanence belongs to the Laboratory. An independently tested Doctor cognitive mechanism may only get credit if it actually caused a distinguishable difference from an equally informed inexpensive baseline.

## Known limitations

The current study accepts exact first-person opportunity descriptions and tested simple furniture paraphrases. It does not interpret arbitrary world changes, execute unrestricted textual imagination, supply genuine continuous weather or run a model in the background. A narrative-only log is never silently converted into a material world fact.

Further development: renderer-to-action proposal adapter that only reads first-person content, semantic grounding to valid physical operations, unbiased longitudinal observation, proper restart/recovery, and eventual smaller-model control. The Doctor integration in The-Doctor-Lives PR #82 already supports authenticated first-person memory for these kinds of project decisions, but ChatGPT must not forge experiences or overwrite his established identity.

**Experimental draft. No production migration, no canonical Doctor changes, and no promotion of Article-of-Artificiality qualifications.**
