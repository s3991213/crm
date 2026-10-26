"""CRM Assistant backend: a tool-calling LLM over the student records.

Same API contract as mock_backend/ (see README.md). Run from the project root:
    uvicorn --factory backend.app:default_app --port 8000
"""

import json
import logging
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")

from .agent import Agent  # noqa: E402
from .llm import LLMError, OpenAICompatible, OpenAIEmbedder  # noqa: E402
from .policies import PolicyIndex  # noqa: E402
from .store import Store, StoreError  # noqa: E402

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen/qwen3-14b")
LLM_API_KEY = os.getenv("LLM_API_KEY", "not-needed")
# Qwen3-style models skip their hidden reasoning step when the prompt ends with /no_think: much faster.
LLM_NO_THINK = os.getenv("LLM_NO_THINK", "1") == "1"
# Policy search embeddings; without this model loaded the search falls back to keywords.
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-nomic-embed-text-v1.5")
DB_PATH = Path(os.getenv("CRM_DB", HERE / "data" / "crm.db"))
POLICY_VECTORS = HERE / "data" / "policy-vectors.json"
TRACE_FILE = Path(os.getenv("CRM_TRACES", HERE / "logs" / "traces.jsonl"))

log = logging.getLogger("crm.backend")


def create_app(store: Store, llm, no_think: bool = False, policies: PolicyIndex | None = None) -> FastAPI:
    app = FastAPI(title="CRM Assistant")
    agent = Agent(store, llm, system_suffix="\n/no_think" if no_think else "", policies=policies)
    app.state.store, app.state.agent = store, agent

    class ChatIn(BaseModel):
        message: str
        staff_name: str | None = None
        session_id: str | None = None

    class StaffIn(BaseModel):
        staff_name: str | None = None

    @app.get("/health")
    def health():
        return {"ok": True, "model": getattr(llm, "model", None)}

    @app.post("/chat")
    async def chat(body: ChatIn, x_staff_name: str = Header("Unknown")):
        try:
            reply, trace = await agent.run(body.message, x_staff_name, body.session_id or "default")
        except LLMError as exc:
            log.warning("LLM unavailable: %s", exc)
            raise HTTPException(503, "The assistant's language model is unavailable.") from exc
        write_trace(asdict(trace))
        return reply

    @app.get("/at-risk")
    def at_risk():
        rows = store.at_risk()
        return {"type": "at_risk", "text": f"{len(rows)} students may need attention, highest risk first.",
                "students": rows}

    @app.post("/updates/{update_id}/confirm")
    def confirm(update_id: str, body: StaffIn, x_staff_name: str = Header("Unknown")):
        try:
            done = store.confirm(update_id, x_staff_name)
        except KeyError:
            raise HTTPException(404, "No pending change with that id")
        except StoreError as exc:
            raise HTTPException(409, str(exc))
        return {"ok": True, "text": f"Saved. {done['student_name']}'s {done['field'].lower()} is now **{done['new_value']}**."}

    @app.post("/updates/{update_id}/cancel")
    def cancel(update_id: str, body: StaffIn, x_staff_name: str = Header("Unknown")):
        try:
            store.cancel(update_id, x_staff_name)
        except KeyError:
            pass  # already handled or never existed: either way nothing changes
        return {"ok": True, "text": "Cancelled. Nothing was changed."}

    return app


def write_trace(trace: dict) -> None:
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with TRACE_FILE.open("a") as f:
        f.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), **trace}) + "\n")


def default_app() -> FastAPI:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    store = Store(DB_PATH)
    store.seed_if_empty(HERE / "seed.json")
    policies = PolicyIndex(OpenAIEmbedder(LLM_BASE_URL, EMBED_MODEL, LLM_API_KEY), cache=POLICY_VECTORS)
    return create_app(store, OpenAICompatible(LLM_BASE_URL, LLM_MODEL, LLM_API_KEY), no_think=LLM_NO_THINK,
                      policies=policies)
