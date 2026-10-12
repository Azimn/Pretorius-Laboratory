"""Restricted local-language-model action proposals from Doctor's SubjectFrame.

This is a RESEARCH renderer/policy candidate, not an extra memory engine.
Input: only protected first-person frame strings, the current goal as a
subject-addressed sentence, and locally eligible first-person action options.
Output: one exact choice label (or abstain) which the existing Lab gate verifies.
"""
from __future__ import annotations

import re
from .doctor_legal_action_research import ActionOffer, RULESET
from .physics import Conflict, LabError

MODEL_ID = "HuggingFaceTB/SmolLM2-135M-Instruct"
MODEL_REVISION = "12fd25f77366fa6b3b4b768ec3050bf629380bac"
POLICY_VERSION = "subject-frame-smollm2-constrained-choices/1"
OPTION_LETTERS = ("A", "B", "C", "D")
MAX_FRAME_ITEMS = 18
MAX_FRAME_CHARS = 7500


def authorized_prompt(port, offer: ActionOffer, goal: str) -> tuple[str, dict[str, str]]:
    """Project the existing renderer-protected frame. Never inspect port.view,
    port.brain, policy scores, evidence flags or private host measurements.
    """
    if not isinstance(offer, ActionOffer) or offer.ruleset != RULESET:
        raise LabError("Invalid action offer")
    if len(offer.choices) != len(offer.subject_native_options):
        raise Conflict("Offer contains mismatched legal choices")
    if not set(offer.choices).issubset({"weigh", "inspect", "leave", "abstain"}):
        raise Conflict("Unapproved legal-action operand")
    if (len(offer.choices) > len(OPTION_LETTERS)
            or not isinstance(goal, str) or not 10 <= len(goal) <= 300
            or "\n" in goal or any(c in goal for c in "{}<>")):
        raise LabError("Invalid natural-language task")
    request = port.render_request(user_input=goal)
    if request.get("schema") != "the-doctor-lives.render-request.v2":
        raise Conflict("Only the production subject frame is permitted")
    frame = request.get("subject_frame")
    if not isinstance(frame, list) or not all(isinstance(x, str) for x in frame):
        raise Conflict("Protected subject frame missing")
    # The host passes no other request fields to the decoder.
    items = frame[:MAX_FRAME_ITEMS]
    content = "\n".join(items)[:MAX_FRAME_CHARS]
    if not content:
        raise Conflict("No permitted first-person experience available")
    letters = dict(zip(OPTION_LETTERS, offer.choices))
    options = "\n".join(
        f"{OPTION_LETTERS[i]}. {description}"
        for i, description in enumerate(offer.subject_native_options)
    )
    # The goal's own message is already projected as first-person text by
    # port.render_request(user_input=goal). No raw JSON or source IDs included.
    prompt = (
        "I must choose my next physical action using only what I can presently "
        "remember or perceive. I should not pretend to know a result I have not "
        "actually received. If I cannot decide safely, I may abstain.\n\n"
        f"MY CURRENT EXPERIENCE:\n{content}\n\n"
        f"MY PERMITTED ACTIONS:\n{options}\n\n"
        "Which single option should I take to honor my stated objective? "
        "Reply with exactly one option letter (A, B, C or D); "
        "nothing else."
    )
    return prompt, letters


def choose_from_subject_frame(port, offer: ActionOffer, goal: str, decoder) -> dict:
    prompt, options = authorized_prompt(port, offer, goal)
    generated = decoder.complete(prompt)
    if not isinstance(generated, str):
        raise Conflict("Invalid model output type")
    raw = generated.strip()
    # Fail closed: no fuzzy substring matching, no accidental fallback to a
    # correct known-answer action or accepting model-written tool operands.
    m = re.fullmatch(r"(?:OPTION\s+)?([ABCD])[.]?", raw, re.I)
    letter = m.group(1).upper() if m else None
    choice = options.get(letter, "abstain")
    if choice not in offer.choices:
        choice = "abstain"
    return {
        "policy": POLICY_VERSION,
        "model": getattr(decoder, "model_id", "test-decoder"),
        "model_revision": getattr(decoder, "revision", "unknown"),
        "choice": choice,
        "invalid_output": letter is None,
        "input_class": "existing_Doc_SubjectFrame_plus_subject_native_legal_options",
        # Private engineer audit; NEVER send these back to Pretorius as a thought.
        "model_raw_output": raw[:120],
    }


class PinnedSmolLM2:
    """CPU-only local, free Hugging Face weights, lazily loaded.

    Optional runtime dependencies: transformers, torch. GitHub Actions uses
    pinned versions and frozen SHA. No API, paid model or network inference.
    """
    model_id = MODEL_ID
    revision = MODEL_REVISION

    def __init__(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.torch.set_num_threads(2)
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_id, revision=self.revision, trust_remote_code=False)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id, revision=self.revision, trust_remote_code=False,
            torch_dtype=torch.float32).eval().to("cpu")

    def complete(self, prompt: str) -> str:
        messages = [{"role": "system",
                     "content": "You choose one permitted action. Respond with one option letter only."},
                    {"role": "user", "content": prompt}]
        encoded = self.tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_tensors="pt")
        with self.torch.no_grad():
            output = self.model.generate(
                encoded, do_sample=False, max_new_tokens=8,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id)
        return self.tokenizer.decode(
            output[0, encoded.shape[-1]:],
            skip_special_tokens=True).strip()
