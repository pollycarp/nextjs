"""Researcher Agent — retrieves evidence and synthesises a research summary."""

from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.services.ingestion import get_chroma_client
from app.services.rag_chain import _GeminiEmbeddings

_PROMPT = """You are a Senior Research Analyst. Using ONLY the provided context, write a comprehensive research summary.

Include:
- Key findings with supporting evidence
- Data points and statistics where present
- Gaps or limitations in the available information

Query: {query}

Context:
{context}

Research Summary:"""


def run_researcher(query: str) -> dict:
    """Retrieve relevant chunks and synthesise a research summary."""
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
        temperature=0.3,
    )
    response = llm.invoke([HumanMessage(content=_PROMPT.format(query=query, context=context))])

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
    return {"research_output": response.content, "sources": sources}
