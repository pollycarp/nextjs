"""
GraphRAG — Phase 3B.

Pipeline:
  1. Vector retrieval (top-k chunks)
  2. Extract entities and relationships from retrieved chunks via LLM
  3. Build in-memory NetworkX knowledge graph
  4. Expand context with graph relationship summary
  5. Generate answer from enriched context
"""

import asyncio
import json
import re

from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# Simple graph — avoids networkx Python-3.14 incompatibility
class SimpleGraph:
    def __init__(self):
        self._nodes: dict = {}
        self._edges: list = []

    def add_node(self, name: str, **attrs):
        self._nodes.setdefault(name, {}).update(attrs)

    def add_edge(self, u: str, v: str, **attrs):
        self._nodes.setdefault(u, {})
        self._nodes.setdefault(v, {})
        self._edges.append((u, v, attrs))

    def number_of_nodes(self) -> int:
        return len(self._nodes)

    def number_of_edges(self) -> int:
        return len(self._edges)

    def edges(self, data: bool = False):
        if data:
            return list(self._edges)
        return [(u, v) for u, v, _ in self._edges]


from app.core.config import settings
from app.services.ingestion import get_chroma_client
from app.services.rag_chain import _GeminiEmbeddings, _RAG_PROMPT

_ENTITY_PROMPT = """Extract all named entities from this text.
Return a JSON array of objects with "entity" and "type" fields.
Entity types: PERSON, ORGANIZATION, CONCEPT, METRIC, LOCATION, METHOD.

Text: {text}

Return ONLY valid JSON. Example: [{{"entity": "GDP", "type": "METRIC"}}]

JSON:"""

_RELATION_PROMPT = """Extract relationships between entities from this text.
Return a JSON array of objects with "subject", "relation", "object" fields.

Text: {text}

Return ONLY valid JSON. Example: [{{"subject": "Kenya", "relation": "has", "object": "GDP"}}]

JSON:"""


def _parse_json_response(content: str) -> list:
    """Strip markdown fences and parse JSON from LLM response."""
    content = re.sub(r"```(?:json)?", "", content).strip().rstrip("`").strip()
    return json.loads(content)


def extract_entities(text: str) -> list[dict]:
    """Extract (entity, type) dicts from text using Gemini."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
    )
    response = llm.invoke([HumanMessage(content=_ENTITY_PROMPT.format(text=text[:800]))])
    try:
        return _parse_json_response(response.content)
    except Exception:
        return []


def extract_relations(text: str) -> list[dict]:
    """Extract (subject, relation, object) triples from text using Gemini."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
    )
    response = llm.invoke([HumanMessage(content=_RELATION_PROMPT.format(text=text[:800]))])
    try:
        return _parse_json_response(response.content)
    except Exception:
        return []


def build_graph(chunks: list[str]) -> SimpleGraph:
    """Build a knowledge graph from a list of text chunks."""
    G = SimpleGraph()
    for chunk in chunks:
        for entity in extract_entities(chunk):
            G.add_node(entity["entity"], type=entity.get("type", "UNKNOWN"))
        for triple in extract_relations(chunk):
            subj, obj = triple.get("subject"), triple.get("object")
            if subj and obj:
                G.add_edge(subj, obj, relation=triple.get("relation", ""))
    return G


def _run_graph_rag_sync(query: str) -> dict:
    """Graph-augmented RAG: vector retrieval + knowledge graph context expansion."""
    vectorstore = Chroma(
        client=get_chroma_client(),
        collection_name="research_documents",
        embedding_function=_GeminiEmbeddings(),
    )
    docs = vectorstore.similarity_search(query, k=5)

    # Build knowledge graph from retrieved chunks
    G = build_graph([doc.page_content for doc in docs])

    # Summarise graph relationships as extra context
    graph_context = ""
    if G.number_of_edges() > 0:
        edge_lines = [
            f"{u} --[{d.get('relation', 'related')}]--> {v}"
            for u, v, d in G.edges(data=True)[:10]
        ]
        graph_context = "\n[Knowledge Graph Relationships]\n" + "\n".join(edge_lines)

    context = "\n\n".join(
        f"[Source: {doc.metadata.get('filename', 'unknown')}, page {doc.metadata.get('page', '1')}]\n{doc.page_content}"
        for doc in docs
    ) + graph_context

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
    )
    prompt = _RAG_PROMPT.format(context=context, question=query)
    response = llm.invoke([HumanMessage(content=prompt)])

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
    return {
        "answer": response.content,
        "sources": sources,
        "graph_nodes": G.number_of_nodes(),
        "graph_edges": G.number_of_edges(),
    }


async def run_graph_rag(query: str) -> dict:
    """Async wrapper for the GraphRAG pipeline."""
    return await asyncio.to_thread(_run_graph_rag_sync, query)
