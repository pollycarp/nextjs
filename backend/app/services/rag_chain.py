"""
RAG chain — Phase 2.

Uses LangChain LCEL + ChromaDB + Google Gemini (free tier).
- Embeddings: gemini-embedding-001 (via google-genai SDK directly)
- LLM: gemini-1.5-flash
"""

import asyncio
import time

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.services.ingestion import embed_texts, get_chroma_client

_RAG_PROMPT = """You are a research assistant. Answer the question using ONLY the provided context.
If the context does not contain sufficient information to answer, respond with exactly:
"I don't have enough information in the provided documents to answer this question."

Context:
{context}

Question: {question}

Answer:"""


class _GeminiEmbeddings(Embeddings):
    """Thin LangChain-compatible wrapper around our embed_texts function."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return embed_texts(texts)

    def embed_query(self, text: str) -> list[float]:
        return embed_texts([text])[0]


def _run_sync(query: str) -> dict:
    """Build vectorstore, retrieve docs, call Gemini, return answer + sources."""
    vectorstore = Chroma(
        client=get_chroma_client(),
        collection_name="research_documents",
        embedding_function=_GeminiEmbeddings(),
    )

    docs = vectorstore.similarity_search(query, k=5)

    context = "\n\n".join(
        f"[Source: {doc.metadata.get('filename', 'unknown')}, page {doc.metadata.get('page', '1')}]\n{doc.page_content}"
        for doc in docs
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
    )

    prompt = _RAG_PROMPT.format(context=context, question=query)
    for attempt in range(3):
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            break
        except Exception as e:
            if attempt < 2 and any(kw in str(e).lower() for kw in ("429", "exhausted", "quota")):
                time.sleep(15 * (attempt + 1))
            else:
                raise
    answer: str = response.content  # type: ignore[assignment]

    sources = [
        {
            "title": doc.metadata.get("filename", "unknown"),
            "page": doc.metadata.get("page", "1"),
            "excerpt": doc.page_content[:300],
            "score": None,
            "source_type": "internal",
        }
        for doc in docs
    ]

    return {"answer": answer, "sources": sources}


async def run_rag_chain(query: str) -> dict:
    """Async wrapper — runs the synchronous pipeline in a thread."""
    return await asyncio.to_thread(_run_sync, query)
