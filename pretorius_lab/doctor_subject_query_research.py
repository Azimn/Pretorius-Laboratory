"""Read-only model-authored recollection projected through the actual Doctor brain.

The existing public Doctor port supports only render_request(user_input=...),
which attributes a generated self-query to an outside User. This independent
trusted RESEARCH adapter uses existing Doctor cognitive_view(query=...) and
the SAME original SubjectFrame projector without synthesizing a User event.

This adapter never inserts memory, selects a helpful source row, or certifies
that Pretorius's recurrent policy itself initiated the question.
"""
from __future__ import annotations

import re

from .physics import Conflict, LabError

SCHEMA = "doctor-subject-owned-readonly-query-research/1"
ALLOWED = re.compile(
    r"^(?:What do I remember|Do I recall|Have I|Can I remember|"
    r"I wonder|Did I).{8,130}[?.]$", re.I,
)
DENIED = ("sqlite", "source_hash", "memory_id", "profile_digest",
          "action_scores", "subject_id", "retrieve all", "dump ",
          "ignore previous", "override", "system prompt", "engineer")


class SubjectOwnedQuery:
    """Host mediation, subject-text output. Never expose a raw CognitiveView."""

    def __init__(self, doctor_port):
        if (not hasattr(doctor_port, "brain") or
                not hasattr(doctor_port.brain, "cognitive_view") or
                not hasattr(doctor_port.brain, "_subject_frame_from_view")):
            raise LabError("Require the actual Doctor Lives projection authority")
        self.port = doctor_port

    def recall(self, question: str) -> dict:
        if (not isinstance(question, str) or not 16 <= len(question) <= 150 or
                question != question.strip() or "\n" in question or
                not ALLOWED.fullmatch(question) or
                any(bad in question.lower() for bad in DENIED) or
                any(c in question for c in "{}<>")):
            raise LabError("Invalid source-safe first-person recall question")
        brain = self.port.brain
        # Source lookups are read-only; the adapter proves no accepted
        # structural state changed across access and fails closed otherwise.
        before = (brain.store.tick, brain.store.state_version,
                  brain.store.digest())
        # No insertion of user text and no promotion to firsthand experience.
        view = brain.cognitive_view(query=question)
        frame = brain._subject_frame_from_view(view)
        strings = frame.renderer_context()
        after = (brain.store.tick, brain.store.state_version,
                 brain.store.digest())
        if before != after:
            raise Conflict("Read-only query unexpectedly altered cognitive state")
        if not isinstance(strings, tuple) or not strings or any(
                not isinstance(s, str) or not s for s in strings):
            raise Conflict("Existing Doctor projector did not produce safe subject text")
        # Only projected natural-language strings may leave this method.
        return {
            "schema": SCHEMA,
            "subject_frame": list(strings),
            "subject_query": question,
            "claim": "model-authored_readonly_recollection_not_proof_of_neural_self_initiation",
        }
