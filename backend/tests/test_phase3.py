"""
Phase 3 tests — Corrective RAG (CRAG) + GraphRAG.
All LLM and external API calls are mocked.
"""

import json

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, patch

from app.main import app


# ── Shared fixtures ───────────────────────────────────────────────────────── #

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
    """Return a mock ChatGoogleGenerativeAI instance that always returns *answer*."""
    resp = MagicMock()
    resp.content = answer
    instance = MagicMock()
    instance.invoke.return_value = resp
    return instance


# ── CRAG tests ────────────────────────────────────────────────────────────── #

@pytest.mark.asyncio
async def test_relevance_grader_labels_relevant():
    from app.services.crag import grade_relevance

    with patch("app.services.crag.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = _llm_mock("yes")
        result = grade_relevance(
            "methodology research",
            "This document discusses research methodology.",
        )
    assert result == "yes"


@pytest.mark.asyncio
async def test_relevance_grader_labels_irrelevant():
    from app.services.crag import grade_relevance

    with patch("app.services.crag.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = _llm_mock("no")
        result = grade_relevance(
            "GDP of Mars",
            "This document discusses research methodology.",
        )
    assert result == "no"


@pytest.mark.asyncio
async def test_crag_triggers_web_fallback(client, sample_txt_bytes):
    """When all chunks are graded irrelevant, CRAG falls back to web search."""
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    # All grading calls return "no"; the final generation call returns an answer.
    call_count = [0]

    def _side_effect(messages):
        call_count[0] += 1
        resp = MagicMock()
        # Assume ≤ 5 grading calls, then generation
        resp.content = (
            "no"
            if call_count[0] <= 5
            else "Web sources indicate methodology involves systematic approaches."
        )
        return resp

    mock_instance = MagicMock()
    mock_instance.invoke.side_effect = _side_effect

    fake_web = [
        {
            "title": "Web Article",
            "url": "https://example.com",
            "excerpt": "Web content about methodology",
            "source_type": "web",
            "page": None,
            "score": 0.9,
        }
    ]

    with patch("app.services.crag.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = mock_instance
        with patch("app.services.crag.web_search", return_value=fake_web):
            from app.services.crag import run_crag
            result = await run_crag("GDP of Mars")

    assert any(s["source_type"] == "web" for s in result["sources"])


@pytest.mark.asyncio
async def test_crag_labels_source_type(client, sample_txt_bytes):
    """Every source returned by CRAG has a valid source_type."""
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    call_count = [0]

    def _side_effect(messages):
        call_count[0] += 1
        resp = MagicMock()
        resp.content = (
            "yes"
            if call_count[0] <= 5
            else "Methodology involves systematic approaches."
        )
        return resp

    mock_instance = MagicMock()
    mock_instance.invoke.side_effect = _side_effect

    with patch("app.services.crag.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = mock_instance
        from app.services.crag import run_crag
        result = await run_crag("What methodology is discussed?")

    for source in result["sources"]:
        assert source["source_type"] in ("internal", "web")


# ── GraphRAG tests ────────────────────────────────────────────────────────── #

@pytest.mark.asyncio
async def test_entity_extraction():
    from app.services.graph_rag import extract_entities

    entities_json = json.dumps([
        {"entity": "Kenya", "type": "LOCATION"},
        {"entity": "GDP", "type": "METRIC"},
    ])
    with patch("app.services.graph_rag.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = _llm_mock(entities_json)
        result = extract_entities("Kenya's GDP grew significantly.")

    assert len(result) >= 1
    assert all("entity" in e and "type" in e for e in result)


@pytest.mark.asyncio
async def test_relationship_extraction():
    from app.services.graph_rag import extract_relations

    triples_json = json.dumps([
        {"subject": "Kenya", "relation": "has", "object": "GDP"}
    ])
    with patch("app.services.graph_rag.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = _llm_mock(triples_json)
        result = extract_relations("Kenya has a growing GDP.")

    assert len(result) >= 1
    assert all("subject" in r and "relation" in r and "object" in r for r in result)


@pytest.mark.asyncio
async def test_graph_builds_correctly():
    from app.services.graph_rag import build_graph

    entities_json = json.dumps([
        {"entity": "Kenya", "type": "LOCATION"},
        {"entity": "GDP", "type": "METRIC"},
    ])
    triples_json = json.dumps([
        {"subject": "Kenya", "relation": "has", "object": "GDP"}
    ])
    responses = [entities_json, triples_json]
    call_count = [0]

    def _side_effect(messages):
        resp = MagicMock()
        resp.content = responses[call_count[0] % len(responses)]
        call_count[0] += 1
        return resp

    mock_instance = MagicMock()
    mock_instance.invoke.side_effect = _side_effect

    with patch("app.services.graph_rag.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = mock_instance
        G = build_graph(["Kenya's GDP grew significantly."])

    assert G.number_of_nodes() > 0
    assert G.number_of_edges() > 0


@pytest.mark.asyncio
async def test_graph_augmented_retrieval_expands_context(client, sample_txt_bytes):
    """GraphRAG returns an answer and at least 1 source after graph expansion."""
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    entities_json = json.dumps([{"entity": "methodology", "type": "CONCEPT"}])
    triples_json = json.dumps([
        {"subject": "qualitative", "relation": "part_of", "object": "methodology"}
    ])
    # Cycle: entities → relations → answer (for each chunk, then generation)
    seq = [entities_json, triples_json, "The document discusses qualitative and quantitative methodology."]
    call_count = [0]

    def _side_effect(messages):
        resp = MagicMock()
        resp.content = seq[min(call_count[0], len(seq) - 1)]
        call_count[0] += 1
        return resp

    mock_instance = MagicMock()
    mock_instance.invoke.side_effect = _side_effect

    with patch("app.services.graph_rag.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = mock_instance
        from app.services.graph_rag import run_graph_rag
        result = await run_graph_rag("What methodology is discussed?")

    assert len(result["answer"]) > 0
    assert len(result["sources"]) >= 1


# ── API routing tests ─────────────────────────────────────────────────────── #

@pytest.mark.asyncio
async def test_comprehensive_research_type_uses_crag(client, sample_txt_bytes):
    """POST research_type=comprehensive is handled by the CRAG pipeline."""
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    call_count = [0]

    def _side_effect(messages):
        call_count[0] += 1
        resp = MagicMock()
        resp.content = (
            "yes"
            if call_count[0] <= 5
            else "Methodology involves systematic approaches."
        )
        return resp

    mock_instance = MagicMock()
    mock_instance.invoke.side_effect = _side_effect

    with patch("app.services.crag.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = mock_instance
        resp = await client.post(
            "/api/research",
            json={"query": "What methodology is discussed?", "research_type": "comprehensive"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_used"] == "crag"
    assert len(body["answer"]) > 0


@pytest.mark.asyncio
async def test_literature_review_type_uses_graphrag(client, sample_txt_bytes):
    """POST research_type=literature_review is handled by the GraphRAG pipeline."""
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    entities_json = json.dumps([{"entity": "methodology", "type": "CONCEPT"}])
    triples_json = json.dumps([
        {"subject": "qualitative", "relation": "part_of", "object": "methodology"}
    ])
    seq = [entities_json, triples_json, "The document discusses methodology."]
    call_count = [0]

    def _side_effect(messages):
        resp = MagicMock()
        resp.content = seq[min(call_count[0], len(seq) - 1)]
        call_count[0] += 1
        return resp

    mock_instance = MagicMock()
    mock_instance.invoke.side_effect = _side_effect

    with patch("app.services.graph_rag.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value = mock_instance
        resp = await client.post(
            "/api/research",
            json={"query": "What methodology is discussed?", "research_type": "literature_review"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_used"] == "graph_rag"
    assert len(body["answer"]) > 0
