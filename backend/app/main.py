from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db
from app.core.rate_limiter import is_allowed
from app.api.routes import router
from app.api.projects import router as projects_router
from app.api.conversations import router as conversations_router
from app.api.analytics import router as analytics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Research Assistant API",
    description="AI-powered research assistant backend — RAG, CRAG, GraphRAG, Multi-Agent",
    version="0.1.0",
    lifespan=lifespan,
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
# Rate limiting — /api/research: 20 req/min per client IP                     #
# --------------------------------------------------------------------------- #
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/api/research":
        client_ip = (request.client.host if request.client else "unknown")
        if not is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again in a minute."},
            )
    return await call_next(request)


# --------------------------------------------------------------------------- #
# Routes                                                                       #
# --------------------------------------------------------------------------- #
app.include_router(router, prefix="/api")
app.include_router(projects_router)
app.include_router(conversations_router)
app.include_router(analytics_router)


@app.get("/health")
async def health():
    """Health check — used by CI and uptime monitors."""
    missing = settings.validate()
    return {
        "status": "ok",
        "version": "0.1.0",
        "phase": 7,
        "env_warnings": [f"Missing env var: {k}" for k in missing],
    }
