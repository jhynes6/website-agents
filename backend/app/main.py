from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import create, debug, query, stats, indexes

app = FastAPI(title="Firestarter Python Backend", version="0.1.0")

# Allow local dev origins; tighten if needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(debug.router, prefix="/api/firestarter", tags=["debug"])
app.include_router(create.router, prefix="/api/firestarter", tags=["create"])
app.include_router(query.router, prefix="/api/firestarter", tags=["query"])
app.include_router(stats.router, prefix="/api/firestarter", tags=["stats"])
app.include_router(indexes.router, prefix="/api/firestarter", tags=["indexes"])


@app.get("/healthz")
async def health() -> dict:
    return {"ok": True}

