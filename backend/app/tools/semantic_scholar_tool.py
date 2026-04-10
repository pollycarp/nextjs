"""Semantic Scholar search tool — uses the public Graph API (free tier)."""

import httpx

from app.tools.base import BaseSearchTool

_SS_API = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,authors,abstract,year,citationCount,url,externalIds"


class SemanticScholarTool(BaseSearchTool):
    def __init__(self, api_key: str = ""):
        self._api_key = api_key

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        headers = {"x-api-key": self._api_key} if self._api_key else {}
        resp = httpx.get(
            _SS_API,
            params={"query": query, "limit": max_results, "fields": _FIELDS},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        papers = []
        for item in resp.json().get("data", []):
            authors = [a.get("name", "") for a in item.get("authors", [])]
            papers.append({
                "title": item.get("title", ""),
                "authors": authors,
                "abstract": item.get("abstract") or "",
                "url": item.get("url") or f"https://www.semanticscholar.org/paper/{item.get('paperId', '')}",
                "year": item.get("year"),
                "citation_count": item.get("citationCount", 0),
                "source": "semantic_scholar",
                "paper_id": item.get("paperId", ""),
            })
        return papers


def search_semantic_scholar(query: str, max_results: int = 10) -> list[dict]:
    from app.core.config import settings
    return SemanticScholarTool(api_key=settings.PINECONE_API_KEY or "").search(query, max_results)
