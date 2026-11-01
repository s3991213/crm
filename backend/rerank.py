"""Rerankers for the policy search: they re-order the hybrid search's best candidates by reading each one with the
question, which the first stage (keywords and embeddings, each looking at the two separately) can't do.

Both take a question and a list of passage texts and return the order to show them in, best first. If one fails,
the policy search keeps the order it had (see PolicyIndex.search).

- CrossEncoderReranker: a small cross-encoder model run in this process with onnxruntime. Fast, no server needed;
  the model is downloaded from Hugging Face once and cached.
- LLMReranker: the chat model ranks the candidates in one call. Nothing to install, but it adds a model call.
"""

import asyncio
import json
import logging
import re

log = logging.getLogger("crm.rerank")

# Cross-encoders with ready-made ONNX files on Hugging Face: name -> (repo, file).
CROSS_ENCODERS = {
    "minilm": ("cross-encoder/ms-marco-MiniLM-L6-v2", "onnx/model.onnx"),  # 22M parameters
    "mxbai": ("mixedbread-ai/mxbai-rerank-xsmall-v1", "onnx/model.onnx"),  # 70M
    "bge": ("Xenova/bge-reranker-base", "onnx/model_int8.onnx"),  # 278M, 8-bit
}


def make_reranker(name: str, llm=None, no_think: bool = True):
    """The reranker called `name` ("llm", a CROSS_ENCODERS name, or "off"), or None for none. A cross-encoder that
    can't be loaded (packages missing, no download) is logged and left out: the search still works without it."""
    if name in ("", "off", "none"):
        return None
    if name == "llm":
        return LLMReranker(llm, no_think)
    if name not in CROSS_ENCODERS:
        raise ValueError(f"Unknown reranker {name!r}: use llm, off or one of {', '.join(CROSS_ENCODERS)}")
    try:
        return CrossEncoderReranker(*CROSS_ENCODERS[name])
    except Exception as exc:
        log.warning("Reranker %s unavailable, searching without it: %s", name, exc)
        return None


class CrossEncoderReranker:
    def __init__(self, repo: str, onnx_file: str = "onnx/model.onnx", max_length: int = 512):
        import onnxruntime  # only needed when this reranker is used
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        self.model = f"{repo}:{onnx_file}"
        self.session = onnxruntime.InferenceSession(hf_hub_download(repo, onnx_file),
                                                    providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.session.get_inputs()}
        self.tokenizer = Tokenizer.from_file(hf_hub_download(repo, "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length)
        self.tokenizer.enable_padding()

    def scores(self, question: str, texts: list[str]) -> list[float]:
        import numpy as np

        enc = self.tokenizer.encode_batch([(question, t) for t in texts])
        feeds = {"input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                 "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64)}
        if "token_type_ids" in self.inputs:
            feeds["token_type_ids"] = np.array([e.type_ids for e in enc], dtype=np.int64)
        logits = self.session.run(None, feeds)[0]
        return [float(x) for x in logits.reshape(len(texts), -1)[:, 0]]

    async def rerank(self, question: str, texts: list[str]) -> list[int]:
        scores = await asyncio.to_thread(self.scores, question, texts)
        return sorted(range(len(texts)), key=lambda i: -scores[i])


LLM_PROMPT = """Staff at a college asked a question. Below are numbered sections from the college's policies.
Rank the sections by how directly they answer the question, best first. Judge by meaning, not shared words.

Question: {question}

{sections}

Reply with only a JSON list of the section numbers, best first, for example [3, 1, 2]."""


class LLMReranker:
    def __init__(self, llm, no_think: bool = True):
        self.llm, self.no_think = llm, no_think
        self.model = getattr(llm, "model", "?")

    async def rerank(self, question: str, texts: list[str]) -> list[int]:
        sections = "\n\n".join(f"[{i + 1}] {t}" for i, t in enumerate(texts))
        prompt = LLM_PROMPT.format(question=question, sections=sections) + ("\n/no_think" if self.no_think else "")
        c = await self.llm.complete([{"role": "user", "content": prompt}], None)
        found = re.search(r"\[[\d,\s]*\]", c.content or "")
        order = []
        for n in json.loads(found.group()) if found else []:
            if 1 <= n <= len(texts) and n - 1 not in order:
                order.append(n - 1)
        if not order:
            raise ValueError(f"No ranking in the reply: {c.content[:200]!r}")
        return order + [i for i in range(len(texts)) if i not in order]  # any it left out keep their place
