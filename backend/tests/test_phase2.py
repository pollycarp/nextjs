"""
Phase 2 tests — Document ingestion & Basic RAG.
Run:  pytest tests/test_phase2.py -v

Requires a valid OPENAI_API_KEY in backend/.env.
Each test gets a fresh in-memory ChromaDB (see conftest.py).
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.ingestion import get_collection, embed_texts


# ── Shared async client fixture ───────────────────────────────────────────── #

@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── Helpers ───────────────────────────────────────────────────────────────── #

async def _upload(client, file_bytes: bytes, filename: str, content_type: str = "application/octet-stream"):
    return await client.post(
        "/api/upload",
        files={"file": (filename, file_bytes, content_type)},
    )


# ── Ingestion tests ───────────────────────────────────────────────────────── #

@pytest.mark.asyncio
async def test_pdf_ingestion(client, sample_pdf_bytes):
    resp = await _upload(client, sample_pdf_bytes, "sample.pdf", "application/pdf")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "doc_id" in body
    assert body["doc_id"] != "stub-doc-001"
    assert body["chunk_count"] > 0
    assert body["status"] == "processed"


@pytest.mark.asyncio
async def test_docx_ingestion(client, sample_docx_bytes):
    resp = await _upload(
        client,
        sample_docx_bytes,
        "sample.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "doc_id" in body
    assert body["chunk_count"] > 0
    assert body["status"] == "processed"


@pytest.mark.asyncio
async def test_embedding_stored(client, sample_txt_bytes):
    resp = await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")
    assert resp.status_code == 200
    doc_id = resp.json()["doc_id"]

    # Verify embeddings are in ChromaDB under the returned doc_id
    collection = get_collection()
    query_embedding = embed_texts(["methodology"])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=1,
        where={"doc_id": doc_id},
        include=["documents"],
    )
    assert len(results["documents"][0]) > 0


@pytest.mark.asyncio
async def test_retrieval_returns_relevant_chunks(client, sample_txt_bytes):
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    from app.services.retrieval import retrieve_chunks

    chunks = retrieve_chunks("methodology")
    assert len(chunks) > 0
    assert any("methodology" in c["text"].lower() for c in chunks)


@pytest.mark.asyncio
async def test_retrieval_score_threshold(client, sample_txt_bytes):
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    from app.services.retrieval import retrieve_chunks

    chunks = retrieve_chunks("methodology research approaches")
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk["score"] > 0.5, (
            f"Score {chunk['score']:.4f} below 0.5 for: {chunk['text'][:60]!r}"
        )


@pytest.mark.asyncio
async def test_rag_answer_not_empty(client, sample_txt_bytes):
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    resp = await client.post(
        "/api/research",
        json={"query": "What methodology is discussed?", "research_type": "quick_search"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "answer" in body
    assert len(body["answer"]) > 0
    assert "[STUB]" not in body["answer"]
    assert body["agent_used"] == "rag_chain"


@pytest.mark.asyncio
async def test_rag_sources_attached(client, sample_txt_bytes):
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    resp = await client.post(
        "/api/research",
        json={"query": "What methodology is discussed?", "research_type": "quick_search"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "sources" in body
    assert len(body["sources"]) >= 1
    src = body["sources"][0]
    assert "title" in src
    assert src["title"] != ""


@pytest.mark.asyncio
async def test_rag_hallucination_guard(client, sample_txt_bytes):
    await _upload(client, sample_txt_bytes, "sample.txt", "text/plain")

    resp = await client.post(
        "/api/research",
        json={"query": "What is the GDP of Mars?", "research_type": "quick_search"},
    )
    assert resp.status_code == 200, resp.text
    answer = resp.json()["answer"].lower()
    markers = [
        "don't have",
        "do not have",
        "not enough",
        "i don't know",
        "cannot answer",
        "no information",
        "not contain",
        "insufficient",
    ]
    assert any(m in answer for m in markers), (
        f"Expected a 'don't know' style answer, got: {answer[:200]!r}"
    )


@pytest.mark.asyncio
async def test_unsupported_file_type(client):
    resp = await _upload(client, b"MZ fake exe", "malware.exe", "application/octet-stream")
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["detail"]
