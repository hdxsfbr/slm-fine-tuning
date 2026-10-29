"""Offline mock provider.

"mock:<name>" answers every conversation deterministically by asking each
behavior module for its mock_reply(). The model name is mixed into the hash,
so "mock:a" and "mock:b" produce different (but repeatable) outcome mixes.
"mock:flaky" additionally fails every fourth call with a 503, to exercise
the error path.
"""
from __future__ import annotations

import threading
from typing import Dict, List

from .clients import ChatClient, ProviderError, Reply

FLAKY_EVERY = 4


class MockClient(ChatClient):
    provider = "mock"

    def __init__(self, spec, model, temperature=None, timeout=180.0):
        super().__init__(spec, model, temperature, timeout)
        self._calls = 0
        self._lock = threading.Lock()

    def chat(self, system: str, messages: List[Dict[str, str]], max_tokens: int) -> Reply:
        if self.model == "flaky":
            with self._lock:
                self._calls += 1
                n = self._calls
            if n % FLAKY_EVERY == 0:
                raise ProviderError(503, "mock outage")
        from behaviors import BEHAVIORS
        from datagen.generate import mock_teacher_reply

        text = mock_teacher_reply(system, messages, salt=self.model)
        if text is not None:
            return Reply(text=text, finish_reason="stop", usage={"input_tokens": 0, "output_tokens": 0})
        for module in BEHAVIORS.values():
            text = module.mock_reply(system, messages, salt=self.model)
            if text is not None:
                return Reply(text=text, finish_reason="stop", usage={"input_tokens": 0, "output_tokens": 0})
        return Reply(text="Mock reply.", finish_reason="stop", usage={"input_tokens": 0, "output_tokens": 0})
