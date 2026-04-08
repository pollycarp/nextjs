"""
Phase 4 tests — Multi-Agent System (Researcher → Critic → Writer).
All LLM calls are mocked.
"""

import json
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, patch

from app.main import app


# ── Fixtures ──────────────────────────────────────────────────────────────── #

@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


async def _upload(client, file_bytes, filename, content_type="application/octet-stream"):
    return await client.post(
        "/api/upload",
        files={"file": (filename, file_bytes, content_type)},
    )


def _llm_mock(answer: str):
    resp = MagicMock()
    resp.content = answer
    instance = MagicMock()
    instance.invoke.return_value = resp
    return instance


_FAKE_SOURCES = [
    {"title": "sample.txt", "page": "1", "excerpt": "methodology text", "score": None, "source_type": "internal"}
]

_FAKE_RESEARCH = "The document discusses qualitative and quantitative methodology frameworks."
_FAKE_CRITIQUE_CLEAN = "APPROVED: Research is well-supported."
_FAKE_CRITIQUE_FLAGGED = (
    "CLAIM: No citation for qualitative method claim.\n"
    "CLAIM: Quantitative method details are missing.\n"
    "CLAIM: Sample size is not mentioned."
)
_FAKE_REPORT = (
    "## Introduction\nThis report covers methodology.\n"
    "## Methods\nQualitative [1] and quantitative [2] methods.\n"
    "## Findings\nKey findings here.\n"
    "## Conclusion\nConclusion here.\n"
    "## References\n[1] sample.txt\n[2] sample.txt"
)


# ── Agent unit tests ───────────────────────────────────────────────────────── #

@pytest.mark.asyncio
async def test_researcher_agent_returns_sources(sample_txt_bytes, client):
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    with patch("app.agents.researcher.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = _llm_mock(_FAKE_RESEARCH)
        from app.agents.researcher import run_researcher
        result = run_researcher("What methodology is discussed?")

    assert len(result["sources"]) >= 1
    assert result["research_output"] == _FAKE_RESEARCH


@pytest.mark.asyncio
async def test_critic_flags_unsupported_claim():
    with patch("app.agents.critic.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = _llm_mock(_FAKE_CRITIQUE_FLAGGED)
        from app.agents.critic import run_critic
        result = run_critic(_FAKE_RESEARCH)

    assert len(result["flagged_claims"]) == 3
    assert result["critique_output"] == _FAKE_CRITIQUE_FLAGGED


@pytest.mark.asyncio
async def test_critic_passes_supported_claim():
    with patch("app.agents.critic.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = _llm_mock(_FAKE_CRITIQUE_CLEAN)
        from app.agents.critic import run_critic
        result = run_critic(_FAKE_RESEARCH)

    assert len(result["flagged_claims"]) == 0
    assert "APPROVED" in result["critique_output"]


@pytest.mark.asyncio
async def test_writer_produces_sections():
    with patch("app.agents.writer.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = _llm_mock(_FAKE_REPORT)
        from app.agents.writer import run_writer
        result = run_writer("query", _FAKE_RESEARCH, _FAKE_CRITIQUE_CLEAN, _FAKE_SOURCES)

    for section in ("Introduction", "Methods", "Findings", "Conclusion", "References"):
        assert section in result["final_report"], f"Missing section: {section}"


@pytest.mark.asyncio
async def test_writer_includes_citations():
    with patch("app.agents.writer.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = _llm_mock(_FAKE_REPORT)
        from app.agents.writer import run_writer
        result = run_writer("query", _FAKE_RESEARCH, _FAKE_CRITIQUE_CLEAN, _FAKE_SOURCES)

    assert "[1]" in result["final_report"]


# ── Orchestrator tests ────────────────────────────────────────────────────── #

@pytest.mark.asyncio
async def test_orchestrator_revision_loop(sample_txt_bytes, client):
    """With > 2 flagged claims the orchestrator triggers a revision pass."""
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    call_count = [0]

    def fake_researcher(query):
        return {"research_output": _FAKE_RESEARCH, "sources": _FAKE_SOURCES}

    def fake_critic(text):
        call_count[0] += 1
        # First call: flag 3 claims → trigger revision; second call: approve
        if call_count[0] == 1:
            return {"critique_output": _FAKE_CRITIQUE_FLAGGED, "flagged_claims": ["a", "b", "c"]}
        return {"critique_output": _FAKE_CRITIQUE_CLEAN, "flagged_claims": []}

    def fake_writer(query, research, critique, sources):
        return {"final_report": _FAKE_REPORT}

    with patch("app.agents.orchestrator.run_researcher", side_effect=fake_researcher), \
         patch("app.agents.orchestrator.run_critic", side_effect=fake_critic), \
         patch("app.agents.orchestrator.run_writer", side_effect=fake_writer):
        from app.agents.orchestrator import run_pipeline
        state = run_pipeline("What methodology is discussed?")

    assert state["revision_count"] == 1
    assert call_count[0] == 2  # critic ran twice


@pytest.mark.asyncio
async def test_orchestrator_max_revisions_respected(sample_txt_bytes, client):
    """revision_count never exceeds MAX_REVISIONS even if critic keeps flagging."""
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    def fake_researcher(query):
        return {"research_output": _FAKE_RESEARCH, "sources": _FAKE_SOURCES}

    def fake_critic(text):
        # Always flag 3 claims
        return {"critique_output": _FAKE_CRITIQUE_FLAGGED, "flagged_claims": ["a", "b", "c"]}

    def fake_writer(query, research, critique, sources):
        return {"final_report": _FAKE_REPORT}

    with patch("app.agents.orchestrator.run_researcher", side_effect=fake_researcher), \
         patch("app.agents.orchestrator.run_critic", side_effect=fake_critic), \
         patch("app.agents.orchestrator.run_writer", side_effect=fake_writer):
        from app.agents.orchestrator import run_pipeline, MAX_REVISIONS
        state = run_pipeline("query")

    assert state["revision_count"] <= MAX_REVISIONS


@pytest.mark.asyncio
async def test_orchestrator_ends_in_final_report(sample_txt_bytes, client):
    """Any query produces a non-empty final_report at the end of the pipeline."""
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    with patch("app.agents.orchestrator.run_researcher", return_value={"research_output": _FAKE_RESEARCH, "sources": _FAKE_SOURCES}), \
         patch("app.agents.orchestrator.run_critic", return_value={"critique_output": _FAKE_CRITIQUE_CLEAN, "flagged_claims": []}), \
         patch("app.agents.orchestrator.run_writer", return_value={"final_report": _FAKE_REPORT}):
        from app.agents.orchestrator import run_pipeline
        state = run_pipeline("any query")

    assert len(state["final_report"]) > 0


# ── API / streaming tests ─────────────────────────────────────────────────── #

@pytest.mark.asyncio
async def test_streaming_endpoint_sends_sse_events(client, sample_txt_bytes):
    """The /api/research/stream endpoint emits SSE events including agent_status and done."""
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    with patch("app.agents.researcher.run_researcher", return_value={"research_output": _FAKE_RESEARCH, "sources": _FAKE_SOURCES}), \
         patch("app.agents.critic.run_critic", return_value={"critique_output": _FAKE_CRITIQUE_CLEAN, "flagged_claims": []}), \
         patch("app.agents.writer.run_writer", return_value={"final_report": _FAKE_REPORT}):
        resp = await client.post(
            "/api/research/stream",
            json={"query": "What methodology?", "research_type": "deep_research"},
        )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    data_lines = [l[5:].strip() for l in resp.text.splitlines() if l.startswith("data:")]
    assert len(data_lines) >= 3

    events = [json.loads(line) for line in data_lines]
    event_types = [e["event"] for e in events]
    assert "agent_status" in event_types
    assert "result" in event_types
    assert "done" in event_types


@pytest.mark.asyncio
async def test_full_pipeline_e2e(client, sample_txt_bytes):
    """Upload a document, run deep_research, get a report with sources."""
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    with patch("app.agents.orchestrator.run_researcher", return_value={"research_output": _FAKE_RESEARCH, "sources": _FAKE_SOURCES}), \
         patch("app.agents.orchestrator.run_critic", return_value={"critique_output": _FAKE_CRITIQUE_CLEAN, "flagged_claims": []}), \
         patch("app.agents.orchestrator.run_writer", return_value={"final_report": _FAKE_REPORT}):
        resp = await client.post(
            "/api/research",
            json={"query": "What methodology is discussed?", "research_type": "deep_research"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_used"] == "multi_agent"
    assert len(body["answer"]) > 0
    assert len(body["sources"]) >= 1
