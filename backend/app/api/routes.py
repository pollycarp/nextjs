from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional

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

@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
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

    return UploadResponse(
        doc_id=result["doc_id"],
        filename=result["filename"],
        status=result["status"],
        message=f"Ingested {result['chunk_count']} chunks from {result['page_count']} page(s).",
        chunk_count=result.get("chunk_count"),
        page_count=result.get("page_count"),
    )


@router.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    """Run a research query. quick_search → real RAG chain; others → Phase 3 stubs."""
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

    # Phase 4+ stubs
    return ResearchResponse(
        answer=(
            f"[Phase 4 pending] '{request.research_type}' research for: '{request.query}'."
        ),
        sources=[],
        research_type=request.research_type,
        agent_used="stub",
    )
