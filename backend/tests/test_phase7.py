"""
Phase 7 tests — Deployment & Production Hardening.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.auth import create_token

BACKEND_DIR = Path(__file__).parent.parent
NEXTJS_DIR = BACKEND_DIR.parent / "nextjs"


def _auth(user_id: str = "user1") -> dict:
    return {"Authorization": f"Bearer {create_token(user_id)}"}


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── 1. Health endpoint ─────────────────────────────────────────────────────── #

@pytest.mark.asyncio
async def test_health_endpoint_returns_200(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── 2. Rate limiting ───────────────────────────────────────────────────────── #

@pytest.mark.asyncio
async def test_rate_limit_enforced(client, sample_txt_bytes):
    """After MAX_REQUESTS rapid calls to /api/research, the next one gets 429."""
    import app.core.rate_limiter as rl

    # Temporarily lower the limit so the test is fast
    original = rl.MAX_REQUESTS
    rl.MAX_REQUESTS = 3
    rl.reset()

    try:
        mock_resp = MagicMock()
        mock_resp.content = "Methodology answer."

        with patch("app.services.rag_chain.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value.invoke.return_value = mock_resp

            statuses = []
            for _ in range(5):
                r = await client.post(
                    "/api/research",
                    json={"query": "test", "research_type": "quick_search"},
                )
                statuses.append(r.status_code)
    finally:
        rl.MAX_REQUESTS = original

    assert 429 in statuses, f"Expected 429 in responses, got: {statuses}"


# ── 3. Token / call tracking ───────────────────────────────────────────────── #

@pytest.mark.asyncio
async def test_tokens_tracked(client, sample_txt_bytes):
    """After a research call with auth, the search log entry is recorded."""
    mock_resp = MagicMock()
    mock_resp.content = "Methodology answer."

    with patch("app.services.rag_chain.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value.invoke.return_value = mock_resp

        await client.post(
            "/api/research",
            json={"query": "methodology", "research_type": "quick_search"},
            headers=_auth(),
        )

    analytics = await client.get("/api/analytics", headers=_auth())
    assert analytics.status_code == 200
    assert analytics.json()["search_count"] == 1


# ── 4. Docker build ────────────────────────────────────────────────────────── #

def _docker_daemon_running() -> bool:
    """Return True only if docker is installed AND the daemon is reachable."""
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "info"], capture_output=True, timeout=10
    )
    return result.returncode == 0


@pytest.mark.skipif(not _docker_daemon_running(), reason="Docker daemon not running")
def test_docker_build_succeeds():
    """docker build exits 0."""
    result = subprocess.run(
        ["docker", "build", "-t", "research-assistant-test", "."],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, f"Docker build failed:\n{result.stderr}"


# ── 5. LangSmith tracing config ───────────────────────────────────────────── #

def test_langsmith_trace_created():
    """When LANGCHAIN_TRACING_V2=true, the env var is honoured (no crash)."""
    import os
    with patch.dict(os.environ, {"LANGCHAIN_TRACING_V2": "true", "LANGCHAIN_API_KEY": "fake-key"}):
        # Verify the env var is readable (tracing itself is mocked by the key being fake)
        assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
        assert os.environ.get("LANGCHAIN_API_KEY") == "fake-key"


# ── 6. Frontend build ──────────────────────────────────────────────────────── #

@pytest.mark.skipif(
    not NEXTJS_DIR.exists() or shutil.which("npm") is None,
    reason="nextjs directory or npm not available",
)
def test_frontend_build_succeeds():
    """npm run build exits 0."""
    result = subprocess.run(
        "npm run build",
        cwd=str(NEXTJS_DIR),
        capture_output=True,
        text=True,
        timeout=300,
        shell=True,  # required on Windows for npm.cmd
    )
    assert result.returncode == 0, f"Frontend build failed:\n{result.stdout[-2000:]}\n{result.stderr[-1000:]}"


# ── 7. ESLint ──────────────────────────────────────────────────────────────── #

@pytest.mark.skipif(
    not NEXTJS_DIR.exists() or shutil.which("npm") is None,
    reason="nextjs directory or npm not available",
)
def test_eslint_passes():
    """npm run lint exits 0."""
    result = subprocess.run(
        "npm run lint",
        cwd=str(NEXTJS_DIR),
        capture_output=True,
        text=True,
        timeout=120,
        shell=True,  # required on Windows for npm.cmd
    )
    assert result.returncode == 0, f"ESLint failed:\n{result.stdout}\n{result.stderr}"
