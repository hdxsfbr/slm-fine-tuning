"""Local Hugging Face model as a chat client, for base-vs-tuned evals.

Spec: "local:<model-or-adapter>", where the model is a Hub id or a path
(unsloth/Qwen3-1.7B) or a saved LoRA adapter directory (models/v1/adapter,
recognised by its adapter_config.json; the base comes from the adapter's
config). Generation is greedy unless a temperature is given, with Qwen3's
thinking switched off, so the prompt matches what train.py trained on.

Needs the training environment (.venv-train): torch, transformers, peft,
and unsloth for the fast 4-bit path. One model serves one process; calls
are serialized with a lock, so run the harness with --workers 1.
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Dict, List, Optional

from .clients import ChatClient, Reply

# Inference window. Training used 2048; the base model's rambling replies
# pushed a few 8-turn conversations past that, so the eval window is larger
# and max_new_tokens is capped to what is left of it.
MAX_SEQ_LENGTH = 6144


class LocalClient(ChatClient):
    provider = "local"

    def __init__(self, spec: str, model: str, temperature: Optional[float] = None, timeout: float = 180.0):
        super().__init__(spec, model, temperature, timeout)
        self._lock = threading.Lock()
        self.adapter = None
        base = model
        cfg_path = os.path.join(model, "adapter_config.json")
        if os.path.isfile(cfg_path):
            with open(cfg_path, encoding="utf-8") as fh:
                base = json.load(fh)["base_model_name_or_path"]
            self.adapter = model
        self.base = base
        from unsloth import FastLanguageModel  # noqa: WPS433 (heavy import, on purpose)

        self.hf_model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name=model if self.adapter else base,
            max_seq_length=MAX_SEQ_LENGTH,
            load_in_4bit=True,
            dtype=None,
        )
        FastLanguageModel.for_inference(self.hf_model)
        self.revision = _snapshot_revision(base)

    def chat(self, system: str, messages: List[Dict[str, str]], max_tokens: int) -> Reply:
        import torch

        chat = [{"role": "system", "content": system}] + self._clean(messages)
        with self._lock:
            prompt = self.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.hf_model.device)
            n_in = inputs["input_ids"].shape[1]
            room = max(16, MAX_SEQ_LENGTH - n_in - 8)
            gen_kwargs = {"max_new_tokens": min(max_tokens, room), "pad_token_id": self.tokenizer.eos_token_id}
            if self.temperature is not None and self.temperature > 0:
                gen_kwargs.update({"do_sample": True, "temperature": self.temperature})
            else:
                gen_kwargs.update({"do_sample": False})
            t0 = time.time()
            with torch.no_grad():
                out = self.hf_model.generate(**inputs, **gen_kwargs)
            new_tokens = out[0, n_in:]
            text = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
            finished = bool(len(new_tokens) < gen_kwargs["max_new_tokens"])
        return Reply(
            text=text,
            finish_reason="stop" if finished else "length",
            usage={"input_tokens": int(n_in), "output_tokens": int(len(new_tokens)), "elapsed_s": round(time.time() - t0, 2)},
        )


def _snapshot_revision(repo_or_path: str) -> Optional[str]:
    """The commit hash of the cached Hub snapshot, so a result can cite the
    exact base model revision; None for a local path."""
    if os.path.isdir(repo_or_path):
        return None
    try:
        from huggingface_hub import snapshot_download

        path = snapshot_download(repo_or_path, local_files_only=True)
        return os.path.basename(path)
    except Exception:
        return None
