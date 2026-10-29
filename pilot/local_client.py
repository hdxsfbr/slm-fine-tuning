"""Local Hugging Face model as a chat client, for base-vs-tuned evals.

Spec: "local:<model-or-adapter>[@<revision>]", where the model is a Hub id
or a path (unsloth/Qwen3-1.7B) or a LoRA adapter, either a directory
(models/v1/adapter) or a Hub repo, recognised by its adapter_config.json;
the base comes from the adapter's config. "@<revision>" pins the Hub
commit that is loaded. Generation is greedy unless a temperature is given,
with Qwen3's thinking switched off, so the prompt matches what train.py
trained on. Every reply's usage carries the revision that was loaded, so
run.json can cite it.

Needs the training environment (.venv-train): torch, transformers, peft,
and unsloth for the fast 4-bit path. One model serves one process; calls
are serialized with a lock, so run the harness with --workers 1.
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Dict, List, Optional, Tuple

from .clients import ChatClient, Reply

# Inference window. Training used 2048; the base model's rambling replies
# pushed 8-turn conversations past 6144 in 7 of 240 evaluated
# conversations, so the eval window is larger still and max_new_tokens is
# capped to what is left of it. A conversation that still overruns is
# recorded as an error and counts as a failure.
MAX_SEQ_LENGTH = 8192


def split_revision(model: str) -> Tuple[str, Optional[str]]:
    """'repo@rev' -> ('repo', 'rev'); a path or an id without '@' keeps
    revision None."""
    if "@" in model and not os.path.exists(model):
        name, rev = model.rsplit("@", 1)
        return name, (rev or None)
    return model, None


def adapter_config(model: str, revision: Optional[str] = None) -> Optional[Dict]:
    """The adapter_config.json of a LoRA adapter, from a directory or a Hub
    repo; None when the model is not an adapter."""
    local = os.path.join(model, "adapter_config.json")
    if os.path.isfile(local):
        with open(local, encoding="utf-8") as fh:
            return json.load(fh)
    if os.path.isdir(model):
        return None
    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(model, "adapter_config.json", revision=revision)
    except Exception:
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class LocalClient(ChatClient):
    provider = "local"

    def __init__(self, spec: str, model: str, temperature: Optional[float] = None, timeout: float = 180.0):
        super().__init__(spec, model, temperature, timeout)
        self._lock = threading.Lock()
        model, requested = split_revision(model)
        self.adapter = None
        base = model
        cfg = adapter_config(model, requested)
        if cfg:
            base = cfg["base_model_name_or_path"]
            self.adapter = model
        self.base = base
        from unsloth import FastLanguageModel  # noqa: WPS433 (heavy import, on purpose)

        kwargs = {"revision": requested} if requested else {}
        self.hf_model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name=model if self.adapter else base,
            max_seq_length=MAX_SEQ_LENGTH,
            load_in_4bit=True,
            dtype=None,
            **kwargs,
        )
        FastLanguageModel.for_inference(self.hf_model)
        # What was loaded: the adapter's own Hub commit (if it came from the
        # Hub) and the base model's cached snapshot commit. Unsloth may swap
        # the requested base for its own 4-bit copy (unsloth/Qwen3-1.7B
        # becomes unsloth/Qwen3-1.7B-unsloth-bnb-4bit), so the name the
        # loaded config carries is the one whose snapshot is cited.
        self.base = getattr(self.hf_model.config, "_name_or_path", None) or base
        self.revision = requested or _snapshot_revision(model if self.adapter else self.base)
        self.base_revision = _snapshot_revision(self.base) or _snapshot_revision(base)

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
            usage={
                "input_tokens": int(n_in),
                "output_tokens": int(len(new_tokens)),
                "elapsed_s": round(time.time() - t0, 2),
                "model_revision": self.revision,
                "base_revision": self.base_revision,
                "base": self.base,
            },
        )


def _snapshot_revision(repo_or_path: str) -> Optional[str]:
    """The commit hash of the cached Hub snapshot, so a result can cite the
    exact base model revision; None for a local path."""
    if os.path.isdir(repo_or_path):
        return None
    try:
        from huggingface_hub import snapshot_download

        path = snapshot_download(repo_or_path, local_files_only=True)
        rev = os.path.basename(path)
        # Unsloth may have loaded a sibling repo (its own 4-bit copy of the
        # base); the cache folder's refs/main then names the real commit.
        return rev
    except Exception:
        return None
