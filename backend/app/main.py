from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import create, debug, query, stats, indexes, agents, agent_debug, resources, inbox_manager, chat, assistant_chat, eval

app = FastAPI(title="MintAgent Python Backend", version="0.1.0")

# Allow local dev origins; tighten if needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(debug.router, prefix="/api/mintagent", tags=["debug"])
app.include_router(create.router, prefix="/api/mintagent", tags=["create"])
app.include_router(chat.router, prefix="/api/mintagent", tags=["chat"])
app.include_router(assistant_chat.router, prefix="/api/mintagent", tags=["assistant_chat"])
app.include_router(query.router, prefix="/api/mintagent", tags=["query"])
app.include_router(stats.router, prefix="/api/mintagent", tags=["stats"])
app.include_router(indexes.router, prefix="/api/mintagent", tags=["indexes"])
app.include_router(agents.router, prefix="/api/mintagent", tags=["agents"])
app.include_router(agent_debug.router, prefix="/api/mintagent", tags=["agent_debug"])
app.include_router(resources.router, prefix="/api/mintagent", tags=["resources"])
app.include_router(inbox_manager.router, prefix="/api/mintagent", tags=["inbox_manager"])
app.include_router(eval.router, prefix="/api/mintagent", tags=["eval"])


@app.get("/healthz")
async def health() -> dict:
    return {"ok": True}

