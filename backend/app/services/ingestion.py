"""
Document ingestion pipeline — Phase 2.

Parses PDF/DOCX/TXT with LlamaIndex, chunks with SentenceSplitter (512/50),
embeds with Google gemini-embedding-001, stores in ChromaDB.
"""

import uuid
import tempfile
from pathlib import Path
from typing import Optional

import chromadb

from app.core.config import settings

# ── ChromaDB singleton ────────────────────────────────────────────────────── #

CHROMA_PATH = Path(__file__).parent.parent.parent / "data" / "chroma"
_chroma_client: Optional[chromadb.ClientAPI] = None

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return _chroma_client


def get_collection() -> chromadb.Collection:
    return get_chroma_client().get_or_create_collection(
        name="research_documents",
        metadata={"hnsw:space": "cosine"},
    )


# ── Embedding helper ──────────────────────────────────────────────────────── #

def embed_texts(texts: list[str]) -> list[list[float]]:
    from google import genai
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    embeddings = []
    for text in texts:
        result = client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=text,
        )
        embeddings.append(list(result.embeddings[0].values))
    return embeddings


# ── Ingestion ─────────────────────────────────────────────────────────────── #

async def ingest_document(file_bytes: bytes, filename: str) -> dict:
    """
    Parse, chunk, embed, and store a document.
    Returns: {doc_id, filename, chunk_count, page_count, status}
    """
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'")

    doc_id = str(uuid.uuid4())

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / filename
        file_path.write_bytes(file_bytes)

        from llama_index.core import SimpleDirectoryReader
        from llama_index.core.node_parser import SentenceSplitter

        reader = SimpleDirectoryReader(input_files=[str(file_path)])
        documents = reader.load_data()

        splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        nodes = splitter.get_nodes_from_documents(documents)

    if not nodes:
        return {
            "doc_id": doc_id,
            "filename": filename,
            "chunk_count": 0,
            "page_count": len(documents),
            "status": "empty",
        }

    texts = [node.get_content() for node in nodes]
    embeddings = embed_texts(texts)

    collection = get_collection()
    ids = [f"{doc_id}_{i}" for i in range(len(nodes))]
    metadatas = [
        {
            "doc_id": doc_id,
            "filename": filename,
            "chunk_index": i,
            "page": str(node.metadata.get("page_label", "1")),
        }
        for i, node in enumerate(nodes)
    ]
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    return {
        "doc_id": doc_id,
        "filename": filename,
        "chunk_count": len(nodes),
        "page_count": len(documents),
        "status": "processed",
    }
