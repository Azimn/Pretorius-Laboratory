# Free-roam trial: ChatGPT as an external decision renderer

**October 19, 2026. Status: opt-in experimental instrumentation, not a running autonomous AI or a neural Doctor evaluation.**

## Purpose

Stop pre-writing a daily itinerary for Pretorius. Give a stand-in conversational renderer a grounded first-person view of the Laboratory, permit it to form its own intentions, and record **what it chooses and what breaks**. We do not need a particle-level physics engine or a prewritten command for every possible action. We do need honest continuity when a choice has a lasting consequence.

A powerful ChatGPT stand-in is a useful *upper-bound exploratory investigator* and a poor substitute for a scientific control of the eventual smaller model. It may invent apparent competence: world-building prose, initiative, reasoning, social interpretation, and time management that are not actually implemented in Pretorius's own cognition. Therefore every record identifies this as `chatgpt-standin-external-proxy-not-native-doctor`.

## What is authoritative?

| Category | Examples | What persists |
| --- | --- | --- |
| Physical / consequential | Move chair, open a drawer, write a genuine page, start a project, place an actual bookmark, prepare a meal, perform a real bench experiment | **Must** execute an original source-validated Laboratory action and retain its receipt, material change, timestamp, provenance and normal replay |
| Prospective intention | "I might compare two liquids tomorrow"; decide to pause an unfinished experiment | Subject-authored prospective project record; never proof that physical work occurred |
| Ambient narrative | A passing impression of the weather, a moment of boredom, a stray thought, a conversational aside | Optional external session transcript tagged **nonmaterial**; does **not** alter scenery, simulate weather, or enter canonical Doctor memories |
| Unavailable/off-script | Press a different flower, rearrange equipment on a table, sketch an anatomical drawing, cook an unsupported recipe | Record exact attempted intention, current capability barrier, and developer follow-up; **never** issue imaginary success receipt |
| No action | Quietly sit, do nothing, change the subject, contemplate | Valid choice. A stand-in observation or idle report need not advance the physical clock or grant a reward |

**Important subtlety:** a narrative event that becomes consequential **is not merely narrative**. If an unseen visitor leaves a note, a fire burns a book, someone moves a chair or a lamp goes out, those changes require explicit source-grounded world events (or remain unverified proposals). An ambient mention of rain may remain transient text if it has no climate-based physical effect, but the actor must not suddenly find plants watered by imagined rainfall.

## A trace separate from Pretorius

`FreeRoamPilot` writes an opt-in engineering-only `free_roam_turns` table in the existing Laboratory SQLite world (the same real world, **not** a replacement physics model). Every turn uses a stable session and turn ID and records:
- The stand-in's **exact proposed** intention.
- Whether it chose a live source-issued action, asked for something unsupported, idled or supplied merely narrative prose.
- The verified physical receipt hash and owning source domain **only when the existing world committed an action**.
- Exact refusal or missing-capability reason on blocked attempts.
- Pending-action crash recovery: check for a matching original source event and replay its authority before reporting a recovered commit. No automatically rerun action, no inventing success after interruption.
- An engineer-facing list of actual barriers and counts for real effects vs nonphysical prose.

There is no automatic task forcing, API key, model choice, score optimizer, environmental rewrite, duplicate autobiography or physical history modification through model text.

## How to use it without API charges

Use `tools/run_free_roam_manual.py` against an explicitly experimental database, with `--experimental-world` and a session ID. To create an isolated sandbox from scratch without overwriting any existing database, pass `--create-sandbox` and a new file path. The script refuses an existing path when creating. Example (from the repository checkout):

```sh
python tools/run_free_roam_manual.py --world pilot-home.sqlite3 --session first-evening --experimental-world --create-sandbox
```

Inside that interactive session submit `{"op":"observe"}` to obtain separate first-person and host-only views. Each physical action request must include a current host-issued `offer_id`, an intentional `turn_id` and an `event_id`. To report a model wish for something the world does not support, submit an `unsupported` turn instead of a fabricated receipt. A later invocation omits `--create-sandbox` and uses the same world and session ID to resume. The tool reads JSON lines (see its header for the documented command format) and returns **two distinct channels**:

1. `subject.inner`: first-person natural-language experience suitable to present to a ChatGPT stand-in. It includes real observed situation and optional possibilities in ordinary language. No raw state IDs, stock counters, source hashes or database paths should enter its first-person experience.
2. `host.offers`: engineering-only exact issued action IDs/args. The human or host program resolves the stand-in's natural language choice to one of these, without leaking the IDs to the character.

Model proposes or declines. Host commits or refuses. Next turn starts from the resulting actual physical state. Use explicit `unsupported` when the model imagines a verb that is not yet modeled, rather than trying to translate the output into a hidden global state patch. `narrative` is a **shadow note**; it is not an injected sensory fact. `idle` is genuine non-action.

This path is manual. It **does not connect the ChatGPT consumer subscription as a programmatic model API**, does not run independently between conversation turns, and does not trigger actual model decisions on GitHub Actions. An OpenAI API-compatible provider, local Ollama or an interactive ChatGPT Work computer-use loop would be a separately tested adapter, not assumed available.

## What to look for in the first unscripted sessions

Give the stand-in ordinary first-person perception. Do not instruct it to try every activity or to maximize scores. Let it do nothing, make a strange request, return to an old note or forget about a task. After 30–50 *voluntary* actions, inspect:
- Which intentions are represented by actual material operations and what the world wrongly claims to have completed.
- Barriers: unavailable verb, missing object, missing prerequisite, impossibly strict parser, artificial resource starvation, room layout limitations, lack of meaningful ambient events, absent social world.
- State continuity after sleep, process restart, multi-day time and project interruption.
- Narrator competence masking absent native cognition: what relied on the large language model rather than the actual Doctor organs.
- Repetitive choice loops, unrealistic motivations or activities that feel forced by the interface.

## Stop conditions and scientific honesty

Do not call this a seven-day **autonomous** life trial if a human or ChatGPT operator still picks each step. This is a **manual interactive stand-in reconnaissance** with genuine world consequences and an accurate gap inventory. A later closed-loop external renderer can be connected to the same subject/host contract, then run a longer hands-off trial with pause limits, budgets and ethical autonomy controls.

Success here means **we learn exactly where the lived-world interface breaks** without corrupting the inhabited Doctor or replacing the source reality with prose. It does not grant Article 7/8 engineering promotions, native cognition superiority or evidence of consciousness.
