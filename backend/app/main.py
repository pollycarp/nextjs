from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import router

app = FastAPI(
    title="Research Assistant API",
    description="AI-powered research assistant backend — RAG, CRAG, GraphRAG, Multi-Agent",
    version="0.1.0",
)

# --------------------------------------------------------------------------- #
# CORS — allow the Next.js frontend on port 3000 to call this backend          #
# --------------------------------------------------------------------------- #
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------- #
# Routes                                                                       #
# --------------------------------------------------------------------------- #
app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    """Health check — used by CI and uptime monitors."""
    missing = settings.validate()
    return {
        "status": "ok",
        "version": "0.1.0",
        "phase": 1,
        "env_warnings": [f"Missing env var: {k}" for k in missing],
    }
