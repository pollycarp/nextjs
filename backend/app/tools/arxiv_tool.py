"""arXiv search tool — uses the arXiv Atom API via httpx."""

import xml.etree.ElementTree as ET

import httpx

from app.tools.base import BaseSearchTool

_ARXIV_NS = "http://www.w3.org/2005/Atom"
_ARXIV_API = "https://export.arxiv.org/api/query"


def _parse_arxiv_response(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    papers = []
    for entry in root.findall(f"{{{_ARXIV_NS}}}entry"):
        raw_id = entry.findtext(f"{{{_ARXIV_NS}}}id", "")
        paper_id = raw_id.split("/abs/")[-1].split("v")[0]
        title = (entry.findtext(f"{{{_ARXIV_NS}}}title") or "").strip().replace("\n", " ")
        abstract = (entry.findtext(f"{{{_ARXIV_NS}}}summary") or "").strip().replace("\n", " ")
        authors = [
            a.findtext(f"{{{_ARXIV_NS}}}name", "")
            for a in entry.findall(f"{{{_ARXIV_NS}}}author")
        ]
        published = entry.findtext(f"{{{_ARXIV_NS}}}published", "")
        year = int(published[:4]) if len(published) >= 4 else None
        url = f"https://arxiv.org/abs/{paper_id}"
        papers.append({
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "url": url,
            "year": year,
            "citation_count": 0,
            "source": "arxiv",
            "paper_id": paper_id,
        })
    return papers


class ArxivTool(BaseSearchTool):
    def search(self, query: str, max_results: int = 10) -> list[dict]:
        resp = httpx.get(
            _ARXIV_API,
            params={"search_query": f"all:{query}", "max_results": max_results},
            timeout=15,
        )
        resp.raise_for_status()
        return _parse_arxiv_response(resp.text)


def search_arxiv(query: str, max_results: int = 10) -> list[dict]:
    return ArxivTool().search(query, max_results)


async def fetch_and_ingest(arxiv_id: str) -> dict:
    """Download an arXiv PDF and ingest it into ChromaDB."""
    import asyncio
    from app.services.ingestion import ingest_document

    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    def _download():
        resp = httpx.get(pdf_url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        return resp.content

    pdf_bytes = await asyncio.to_thread(_download)
    return await ingest_document(pdf_bytes, f"{arxiv_id}.pdf")
