import asyncio
import json

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.core.auth import get_optional_user

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


# ── Schemas ───────────────────────────────────────────────────────────────── #

class ResearchRequest(BaseModel):
    query: str
    research_type: Optional[str] = "quick_search"   # quick_search | comprehensive | literature_review
    options: Optional[dict] = {}


class Source(BaseModel):
    title: str
    excerpt: str
    url: Optional[str] = None
    source_type: str = "internal"   # internal | web
    page: Optional[str] = None
    score: Optional[float] = None


class ResearchResponse(BaseModel):
    answer: str
    sources: list[Source]
    research_type: str
    agent_used: str


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    status: str
    message: str
    chunk_count: Optional[int] = None
    page_count: Optional[int] = None


# ── Endpoints ─────────────────────────────────────────────────────────────── #

@router.get("/documents")
async def list_documents(user_id: Optional[str] = Depends(get_optional_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    import app.core.database as db
    return await asyncio.to_thread(db.get_documents, user_id)


@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...), user_id: Optional[str] = Depends(get_optional_user)):
    """Ingest a PDF/DOCX/TXT into ChromaDB."""
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: .pdf, .docx, .txt",
        )

    file_bytes = await file.read()

    from app.services.ingestion import ingest_document

    try:
        result = await ingest_document(file_bytes, filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")

    if user_id:
        import app.core.database as db
        await asyncio.to_thread(
            db.save_document, user_id, result["doc_id"], result["filename"],
            result.get("chunk_count", 0), result.get("page_count", 0), result["status"],
        )

    return UploadResponse(
        doc_id=result["doc_id"],
        filename=result["filename"],
        status=result["status"],
        message=f"Ingested {result['chunk_count']} chunks from {result['page_count']} page(s).",
        chunk_count=result.get("chunk_count"),
        page_count=result.get("page_count"),
    )


@router.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest, user_id: Optional[str] = Depends(get_optional_user)):
    """Run a research query across all pipeline types."""
    if user_id:
        import app.core.database as db
        await asyncio.to_thread(db.log_search, user_id, request.query, request.research_type or "")
    if request.research_type == "quick_search":
        from app.services.rag_chain import run_rag_chain

        try:
            result = await run_rag_chain(request.query)
        except Exception as exc:
            return ResearchResponse(
                answer=f"RAG chain error: {exc}",
                sources=[],
                research_type=request.research_type,
                agent_used="rag_chain_error",
            )
        sources = [
            Source(
                title=s["title"],
                excerpt=s["excerpt"],
                page=s.get("page"),
                score=s.get("score"),
                source_type=s.get("source_type", "internal"),
            )
            for s in result["sources"]
        ]
        return ResearchResponse(
            answer=result["answer"],
            sources=sources,
            research_type=request.research_type,
            agent_used="rag_chain",
        )

    if request.research_type == "comprehensive":
        from app.services.crag import run_crag

        try:
            result = await run_crag(request.query)
        except Exception as exc:
            return ResearchResponse(
                answer=f"CRAG error: {exc}",
                sources=[],
                research_type=request.research_type,
                agent_used="crag_error",
            )
        sources = [
            Source(
                title=s["title"],
                excerpt=s["excerpt"],
                url=s.get("url"),
                page=s.get("page"),
                score=s.get("score"),
                source_type=s.get("source_type", "internal"),
            )
            for s in result["sources"]
        ]
        return ResearchResponse(
            answer=result["answer"],
            sources=sources,
            research_type=request.research_type,
            agent_used="crag",
        )

    if request.research_type == "literature_review":
        from app.services.graph_rag import run_graph_rag

        try:
            result = await run_graph_rag(request.query)
        except Exception as exc:
            return ResearchResponse(
                answer=f"GraphRAG error: {exc}",
                sources=[],
                research_type=request.research_type,
                agent_used="graph_rag_error",
            )
        sources = [
            Source(
                title=s["title"],
                excerpt=s["excerpt"],
                page=s.get("page"),
                score=s.get("score"),
                source_type=s.get("source_type", "internal"),
            )
            for s in result["sources"]
        ]
        return ResearchResponse(
            answer=result["answer"],
            sources=sources,
            research_type=request.research_type,
            agent_used="graph_rag",
        )

    if request.research_type == "deep_research":
        from app.agents.orchestrator import run_pipeline_async

        try:
            state = await run_pipeline_async(request.query)
        except Exception as exc:
            return ResearchResponse(
                answer=f"Pipeline error: {exc}",
                sources=[],
                research_type=request.research_type,
                agent_used="pipeline_error",
            )
        sources = [
            Source(
                title=s["title"],
                excerpt=s["excerpt"],
                page=s.get("page"),
                score=s.get("score"),
                source_type=s.get("source_type", "internal"),
            )
            for s in state["sources"]
        ]
        return ResearchResponse(
            answer=state["final_report"],
            sources=sources,
            research_type=request.research_type,
            agent_used="multi_agent",
        )

    # Phase 5+ stubs
    return ResearchResponse(
        answer=f"[Phase 5 pending] '{request.research_type}' research for: '{request.query}'.",
        sources=[],
        research_type=request.research_type,
        agent_used="stub",
    )


@router.post("/research/stream")
async def research_stream(request: ResearchRequest):
    """SSE streaming endpoint — emits agent status events then the final result."""

    async def _generate():
        from app.agents.researcher import run_researcher
        from app.agents.critic import run_critic
        from app.agents.writer import run_writer
        from app.agents.orchestrator import MAX_REVISIONS

        def _sse(data: dict) -> str:
            return f"data: {json.dumps(data)}\n\n"

        yield _sse({"event": "agent_status", "agent": "researcher", "status": "working"})
        res = await asyncio.to_thread(run_researcher, request.query)
        research_output, sources = res["research_output"], res["sources"]
        yield _sse({"event": "agent_status", "agent": "researcher", "status": "done"})

        revision_count = 0
        critique_output = ""
        flagged_claims: list = []

        while True:
            yield _sse({"event": "agent_status", "agent": "critic", "status": "working"})
            crit = await asyncio.to_thread(run_critic, research_output)
            critique_output = crit["critique_output"]
            flagged_claims = crit["flagged_claims"]
            yield _sse({"event": "agent_status", "agent": "critic", "status": "done"})

            if len(flagged_claims) > 2 and revision_count < MAX_REVISIONS:
                yield _sse({"event": "agent_status", "agent": "researcher", "status": "revising"})
                revised = await asyncio.to_thread(
                    run_researcher,
                    f"{request.query}\n\nAddress critique:\n{critique_output}",
                )
                research_output, sources = revised["research_output"], revised["sources"]
                revision_count += 1
                yield _sse({"event": "agent_status", "agent": "researcher", "status": "revised"})
            else:
                break

        yield _sse({"event": "agent_status", "agent": "writer", "status": "working"})
        wr = await asyncio.to_thread(run_writer, request.query, research_output, critique_output, sources)
        yield _sse({"event": "agent_status", "agent": "writer", "status": "done"})

        yield _sse({"event": "result", "answer": wr["final_report"], "sources": sources, "flagged_claims": flagged_claims})
        yield _sse({"event": "done"})

    return StreamingResponse(_generate(), media_type="text/event-stream")
