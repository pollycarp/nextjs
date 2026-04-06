"""
Phase 1 tests — FastAPI scaffold, stubs, CORS, env vars.
Run with:  pytest tests/test_phase1.py -v
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    """Async test client that talks directly to the FastAPI app (no real HTTP)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# --------------------------------------------------------------------------- #
# 1. Health check                                                              #
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


# --------------------------------------------------------------------------- #
# 2. Research stub                                                             #
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_research_stub_returns_valid_schema(client):
    payload = {"query": "What is RAG?", "research_type": "quick_search"}
    response = await client.post("/api/research", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert isinstance(body["answer"], str)
    assert len(body["answer"]) > 0
    assert "sources" in body
    assert isinstance(body["sources"], list)
    assert "research_type" in body
    assert "agent_used" in body


@pytest.mark.asyncio
async def test_research_stub_echoes_research_type(client):
    for r_type in ["quick_search", "comprehensive", "literature_review"]:
        response = await client.post(
            "/api/research", json={"query": "test", "research_type": r_type}
        )
        assert response.status_code == 200
        assert response.json()["research_type"] == r_type


# --------------------------------------------------------------------------- #
# 3. Upload stub                                                               #
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_upload_stub_accepts_pdf(client):
    fake_pdf = b"%PDF-1.4 fake content"
    response = await client.post(
        "/api/upload",
        files={"file": ("test.pdf", fake_pdf, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "doc_id" in body
    assert "filename" in body
    assert body["filename"] == "test.pdf"
    assert "status" in body


@pytest.mark.asyncio
async def test_upload_stub_rejects_unsupported_type(client):
    response = await client.post(
        "/api/upload",
        files={"file": ("malware.exe", b"MZ fake exe", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


# --------------------------------------------------------------------------- #
# 4. CORS headers                                                              #
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_cors_headers_present(client):
    response = await client.options(
        "/api/research",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    # FastAPI returns 200 for CORS preflight
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


# --------------------------------------------------------------------------- #
# 5. Env vars loaded                                                           #
# --------------------------------------------------------------------------- #

def test_env_vars_loaded():
    """Settings object should initialise without crashing."""
    from app.core.config import settings
    # validate() returns a list — it may be non-empty if keys aren't set yet,
    # but the object itself must exist and be the right type.
    assert isinstance(settings.validate(), list)
    assert isinstance(settings.ALLOWED_ORIGINS, list)
    assert len(settings.ALLOWED_ORIGINS) >= 1
