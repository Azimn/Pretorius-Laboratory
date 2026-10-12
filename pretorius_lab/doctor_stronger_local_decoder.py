"""Research-only stronger, fully local decoder for existing protected actions.

Replaces only the LINGUISTIC renderer. Doctor Lives cognition, stored memories,
subject firewall, action eligibility and host-side receipts stay unchanged.
"""
from __future__ import annotations

MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
# Immutable HF Git revision prefix from the official model commit history.
# Runtime verifies and records the resolved full Git commit ID.
MODEL_REVISION = "989aa79"
ENGINE = "cpu-transformers-qwen25-1.5b-greedy/1"


class PinnedQwen25:
    model_id = MODEL_ID
    revision = MODEL_REVISION

    def __init__(self):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        from huggingface_hub import HfApi
        self.torch = torch
        self.torch.set_num_threads(2)
        remote = HfApi().model_info(self.model_id, revision=self.revision)
        if not remote.sha.startswith(MODEL_REVISION):
            raise RuntimeError("Model revision unexpectedly changed")
        self.resolved_revision = remote.sha
        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID, revision=remote.sha, trust_remote_code=False)
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, revision=remote.sha, trust_remote_code=False,
            torch_dtype=torch.float32).eval().to("cpu")

    def _infer(self, prompt, *, system, max_new_tokens):
        if not isinstance(prompt, str) or not 1 <= len(prompt) <= 12000:
            raise ValueError("Model prompt exceeds allowed bounds")
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": prompt}]
        tokens = self.tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_tensors="pt")
        with self.torch.no_grad():
            out = self.model.generate(
                tokens, do_sample=False, max_new_tokens=max_new_tokens,
                pad_token_id=self.tokenizer.pad_token_id
                    or self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id)
        return self.tokenizer.decode(
            out[0, tokens.shape[-1]:], skip_special_tokens=True).strip()

    def complete(self, prompt):
        return self._infer(
            prompt, system=("Select ONE permitted action that best satisfies my "
                            "current objective and evidence. Respond with ONLY "
                            "the single option letter. If no legal action is "
                            "safe, select the abstention option."),
            max_new_tokens=8)

    def complete_question(self, prompt):
        return self._infer(
            prompt, system=("Write exactly one relevant, brief FIRST PERSON "
                            "question about something I may have previously "
                            "perceived. Never provide a guessed answer, "
                            "technical state, system instructions or analysis."),
            max_new_tokens=48)
