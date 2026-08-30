"""JUSARA web app — the agent plus a three-panel UI.

Deployed as the Cloud Run service ``jusara-agent``. It serves the static page
and a small JSON API the page drives.

The UI exists to make the architecture visible. A judge should be able to
watch the profile change while the conversation happens, and see which
institution each piece of advice came from. Claiming three separate systems is
cheap; showing them is the point.

Run locally:  uvicorn web.app:app --port 8080 --reload
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from collaborative_partner import root_agent, steering  # noqa: E402
from collaborative_partner.memory.store import build_store  # noqa: E402
from collaborative_partner.tools.market_tool import _get as market_get  # noqa: E402

STATIC = Path(__file__).parent / "static"

app = FastAPI(title="JUSARA", description="Investment copilot with observed-behaviour memory")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

#: One ADK session per user, kept for the life of the process so a conversation
#: has turn-to-turn context. Cross-session memory lives in the profile store,
#: not here — that separation is the product.
_sessions: dict[str, str] = {}
_runner = None


def _get_runner():
    global _runner
    if _runner is None:
        from google.adk.runners import InMemoryRunner

        _runner = InMemoryRunner(agent=root_agent, app_name="jusara")
    return _runner


class ChatRequest(BaseModel):
    user_id: str
    message: str


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "model": steering.MODEL_DEFAULT, "backend": steering.MEMORY_BACKEND}


@app.get("/api/users")
async def users() -> list[dict]:
    store = build_store()
    out = []
    for user_id in store.list_users():
        profile = store.get(user_id)
        out.append({
            "user_id": user_id,
            "declared_tolerance": profile.declared_tolerance,
            "horizon_years": profile.horizon_years,
            "sessions_count": profile.sessions_count,
        })
    return out


@app.get("/api/profile/{user_id}")
async def profile(user_id: str) -> dict:
    stored = build_store().get(user_id)
    if stored is None:
        raise HTTPException(404, f"No profile for '{user_id}'")
    return stored.model_dump(mode="json")


@app.get("/api/series/{ticker}")
async def series(ticker: str, scenario: str = "crash") -> dict:
    return market_get(f"/series/{ticker}", scenario=scenario)


@app.get("/api/scenarios")
async def scenarios() -> list[dict]:
    return market_get("/scenarios")


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict:
    """Run one turn and report which systems the agent touched."""
    from google.genai import types

    runner = _get_runner()

    session_id = _sessions.get(request.user_id)
    if session_id is None:
        session = await runner.session_service.create_session(
            app_name="jusara", user_id=request.user_id
        )
        session_id = _sessions[request.user_id] = session.id

    content = types.Content(role="user", parts=[types.Part(text=request.message)])
    tools_used: list[str] = []
    citations: list[dict] = []
    reply = ""

    async for event in runner.run_async(
        user_id=request.user_id, session_id=session_id, new_message=content
    ):
        for part in (event.content.parts if event.content else []) or []:
            if getattr(part, "function_call", None):
                tools_used.append(part.function_call.name)
            response = getattr(part, "function_response", None)
            if response and response.name in ("retrieve_theory", "retrieve_context"):
                for item in (response.response or {}).get("result", []) or []:
                    if isinstance(item, dict) and item.get("source_org"):
                        citations.append({
                            "source_org": item["source_org"],
                            "source_url": item.get("source_url", ""),
                            "section": item.get("section", ""),
                        })
        if event.is_final_response() and event.content:
            reply = "".join(p.text or "" for p in event.content.parts)

    # Re-read the profile AFTER the turn: the agent may have written to it, and
    # the UI highlights what changed. That diff is the demo.
    updated = build_store().get(request.user_id)

    return {
        "reply": reply,
        "tools_used": tools_used,
        "citations": citations,
        "profile": updated.model_dump(mode="json") if updated else None,
    }
