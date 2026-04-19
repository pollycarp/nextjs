"""
Corrective RAG (CRAG) — Phase 3A.

Pipeline:
  1. Retrieve top-k chunks from ChromaDB
  2. Grade each chunk: relevant / irrelevant / partial
  3. If < 2 relevant chunks → web search fallback (Tavily)
  4. Generate answer from best available context
"""

import asyncio

from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.services.ingestion import get_chroma_client
from app.services.rag_chain import _GeminiEmbeddings, _RAG_PROMPT

_GRADE_PROMPT = """Is the following document chunk relevant to answering the query?
Answer with exactly one word: yes, no, or partial.

Query: {query}

Chunk: {chunk}

Answer:"""


def grade_relevance(query: str, chunk_text: str) -> str:
    """Grade a single chunk as 'yes', 'no', or 'partial'."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
    )
    prompt = _GRADE_PROMPT.format(query=query, chunk=chunk_text[:500])
    response = llm.invoke([HumanMessage(content=prompt)])
    answer = response.content.strip().lower()
    if "yes" in answer:
        return "yes"
    if "no" in answer:
        return "no"
    return "partial"


def web_search(query: str) -> list[dict]:
    """Search the web using Tavily. Returns list of source dicts."""
    from tavily import TavilyClient  # lazy import — only needed at runtime

    client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    results = client.search(query=query, max_results=5)
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "excerpt": r.get("content", "")[:300],
            "source_type": "web",
            "page": None,
            "score": r.get("score"),
        }
        for r in results.get("results", [])
    ]


def _run_crag_sync(query: str) -> dict:
    """Full CRAG pipeline: retrieve → grade → (web fallback if needed) → generate."""
    vectorstore = Chroma(
        client=get_chroma_client(),
        collection_name="research_documents",
        embedding_function=_GeminiEmbeddings(),
    )
    docs = vectorstore.similarity_search(query, k=5)

    # Grade each retrieved chunk
    relevant_docs = [
        doc for doc in docs
        if grade_relevance(query, doc.page_content) in ("yes", "partial")
    ]

    if len(relevant_docs) >= 2:
        context = "\n\n".join(
            f"[Source: {doc.metadata.get('filename', 'unknown')}, page {doc.metadata.get('page', '1')}]\n{doc.page_content}"
            for doc in relevant_docs
        )
        sources = [
            {
                "title": doc.metadata.get("filename", "unknown"),
                "page": doc.metadata.get("page", "1"),
                "excerpt": doc.page_content[:300],
                "score": None,
                "source_type": "internal",
            }
            for doc in relevant_docs
        ]
    else:
        # Insufficient internal docs — fall back to web search
        web_results = web_search(query)
        context = "\n\n".join(
            f"[Web Source: {r['title']}]\n{r['excerpt']}"
            for r in web_results
        )
        sources = web_results

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
    )
    prompt = _RAG_PROMPT.format(context=context, question=query)
    response = llm.invoke([HumanMessage(content=prompt)])

    return {"answer": response.content, "sources": sources}


async def run_crag(query: str) -> dict:
    """Async wrapper for the CRAG pipeline."""
    return await asyncio.to_thread(_run_crag_sync, query)
