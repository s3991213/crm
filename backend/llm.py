"""Chat-completion client for any OpenAI-compatible server (LM Studio, vLLM, Ollama, hosted APIs).

The agent only depends on `complete()`, so tests swap in a scripted fake.
"""

import json
import re
import time
from dataclasses import dataclass, field

from openai import AsyncOpenAI, OpenAIError

THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


class LLMError(Exception):
    """The model server could not be reached or returned something unusable."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON text, exactly as the model produced it


@dataclass
class Completion:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    ms: int = 0


def strip_thinking(text: str | None) -> str:
    """Drop <think>…</think> blocks some reasoning models put in the reply."""
    text = THINK.sub("", text or "")
    return text.split("</think>")[-1].strip()


class OpenAICompatible:
    def __init__(self, base_url: str, model: str, api_key: str = "not-needed", timeout: float = 120,
                 temperature: float = 0.0, reasoning_effort: str | None = None):
        self.model = model
        self.temperature = temperature
        # "none" turns off thinking where /no_think doesn't (Qwen3.5 in LM Studio). Only sent when set, since some
        # hosted APIs reject the parameter for models that don't reason.
        self.extra = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=1)

    async def complete(self, messages: list[dict], tools: list[dict]) -> Completion:
        start = time.perf_counter()
        try:
            r = await self.client.chat.completions.create(
                model=self.model, messages=messages, tools=tools, temperature=self.temperature, **self.extra,
            )
        except OpenAIError as exc:
            raise LLMError(str(exc)) from exc
        if not r.choices:
            raise LLMError("The model returned no choices.")
        msg = r.choices[0].message
        return Completion(
            content=strip_thinking(msg.content),
            tool_calls=[ToolCall(c.id, c.function.name, c.function.arguments or "{}") for c in msg.tool_calls or []],
            prompt_tokens=getattr(r.usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(r.usage, "completion_tokens", 0) or 0,
            ms=round((time.perf_counter() - start) * 1000),
        )


def assistant_message(c: Completion) -> dict:
    """The assistant turn to append to the conversation before sending tool results back."""
    msg = {"role": "assistant", "content": c.content or None}
    if c.tool_calls:
        msg["tool_calls"] = [
            {"id": t.id, "type": "function", "function": {"name": t.name, "arguments": t.arguments}}
            for t in c.tool_calls
        ]
    return msg


def tool_message(call: ToolCall, result: dict) -> dict:
    return {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)}


class OpenAIEmbedder:
    """Embeddings from the same kind of server, for the policy search (backend/policies.py)."""

    def __init__(self, base_url: str, model: str, api_key: str = "not-needed", timeout: float = 60):
        self.model = model
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=1)
        # nomic-embed models are trained with these prefixes and do noticeably worse without them.
        self.doc_prefix, self.query_prefix = ("search_document: ", "search_query: ") if "nomic" in model else ("", "")

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        try:
            r = await self.client.embeddings.create(model=self.model, input=texts)
        except OpenAIError as exc:
            raise LLMError(str(exc)) from exc
        return [d.embedding for d in sorted(r.data, key=lambda d: d.index)]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embed([self.doc_prefix + t for t in texts])

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed([self.query_prefix + text]))[0]
