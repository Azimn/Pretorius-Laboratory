"""Research only: model-selected recall through the existing Doctor subject frame.

The existing port labels recalled queries as externally provided user prompts,
so this is mediated recall, NOT proof of internal self-initiated cognition.
"""
from __future__ import annotations

import re
from .doctor_subject_frame_proposer import choose_from_subject_frame
from .doctor_legal_action_research import ActionOffer, RULESET
from .physics import Conflict, LabError

VERSION = "subject-selected-mediated-recall/1"
OPTIONS = {
    "recall": "I could try to remember what I already experienced.",
    "act": "I could decide with my current available experience.",
    "abstain": "I could refrain from taking an uncertain action.",
}
ORDERINGS = (
    ("recall", "act", "abstain"),
    ("act", "abstain", "recall"),
    ("abstain", "recall", "act"),
)
QUESTION = re.compile(
    r"^(?:What do I remember|Do I recall|Have I|Can I remember|I wonder|Did I).{8,130}[?.]$",
    re.I,
)


def protected(port, query):
    output = port.render_request(user_input=query)
    if output.get("schema") != "the-doctor-lives.render-request.v2":
        raise Conflict("Require production protected subject frame")
    frame = output.get("subject_frame")
    if not isinstance(frame, list) or not frame or not all(
            isinstance(x, str) for x in frame):
        raise Conflict("No safe first-person context")
    return tuple(frame)


class _ProjectedOnlyPort:
    """No brain data, engineering audit or source rows available."""
    def __init__(self, frame):
        self.frame = list(frame)

    def render_request(self, user_input=None):
        return {"schema": "the-doctor-lives.render-request.v2",
                "subject_frame": list(self.frame)}


def select_and_act(port, offer: ActionOffer, goal: str, decoder, *,
                   order_index: int, enable_recall: bool,
                   allocated_question: bool = False) -> dict:
    if offer.ruleset != RULESET or type(order_index) is not int or not (
            0 <= order_index < len(ORDERINGS)):
        raise LabError("Invalid recall offer")
    if not isinstance(goal, str) or not 10 <= len(goal) <= 300:
        raise LabError("Invalid first-person goal")
    if allocated_question and not enable_recall:
        raise LabError("Allocated question requires the recall-enabled research arm")
    original = protected(port, goal)
    decision = "disabled"
    question = None
    queried = ()
    if enable_recall:
        order = ORDERINGS[order_index]
        labels = {chr(65 + i): action for i, action in enumerate(order)}
        prompt = (
            "I should decide whether to remember something before acting. "
            "I must never pretend I already saw a measurement I have not received.\n"
            "WHAT I REMEMBER RIGHT NOW:\n" +
            "\n".join(original[:14])[:6000] +
            "\nMY OBJECTIVE:\n" + goal +
            "\nMY OPTIONS:\n" +
            "\n".join(f"{letter}. {OPTIONS[action]}"
                      for letter, action in labels.items()) +
            "\nReply with only A, B or C."
        )
        if allocated_question:
            # The experiment assigns one inquiry opportunity. The *content*
            # must still come from the model; no researcher-supplied retrieval
            # key or preferred answer is allowed. This is not spontaneous recall.
            decision = "recall"
        else:
            raw = decoder.complete(prompt)
            found = re.fullmatch(
                r"(?:OPTION\s+)?([ABC])[.]?", raw.strip(), re.I
            ) if isinstance(raw, str) else None
            decision = labels.get(found.group(1).upper(), "abstain") if found else "abstain"
        if decision == "recall":
            ask = (
                "I want to ask myself a short question about something I may "
                "have perceived earlier. Write one first-person question "
                "beginning with 'What do I remember' or 'Do I recall', "
                "ending with a question mark. Do not invent an answer.\n"
                "MY CURRENT OBJECTIVE:\n" + goal + "\n"
                "MY PRESENT EXPERIENCE:\n" +
                "\n".join(original[:10])[:3800]
            )
            # The ordinary action decoder is limited to eight output tokens;
            # an independently authored short question needs its own budget.
            # Fake test decoders without complete_question remain supported.
            candidate = getattr(decoder, "complete_question", decoder.complete)(ask)
            if (isinstance(candidate, str) and len(candidate) <= 150 and
                    QUESTION.fullmatch(candidate.strip()) and
                    not any(c in candidate for c in "{}<>\n\r") and
                    not any(x in candidate.lower() for x in (
                        "sqlite", "memory_id", "profile_digest", "source_hash"))):
                question = candidate.strip()
                # This existing port uses EXTERNALLY CUED query semantics.
                # No host check for a correct answer selects a different cue.
                queried = protected(port, question)
            else:
                decision = "invalid_question_abstain"
    if decision in ("abstain", "invalid_question_abstain"):
        return {"policy": VERSION, "choice": "abstain",
                "recall_decision": decision, "generated_query": question,
                "used_extra_frame": False, "model_output_invalid": True}
    # Uniform context budget, no source/answer lookup or curator-selected
    # memory insertion. Only plain first-person strings are forwarded.
    combined = tuple(dict.fromkeys((*queried[:12], *original[:8])))[:18]
    act = choose_from_subject_frame(
        _ProjectedOnlyPort(combined), offer, goal, decoder)
    return {"policy": VERSION, "choice": act["choice"],
            "recall_decision": decision,
            "allocated_question": allocated_question,
            "generated_query": question,
            "used_extra_frame": bool(queried),
            "model_raw_action": act["model_raw_output"],
            "model_output_invalid": act["invalid_output"],
            "mediation": "externally_cued_Doctor_render_request_not_autonomous_self_query"}
