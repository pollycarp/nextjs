"""Unified search — calls all three tools, deduplicates, ranks by citations."""

from app.tools.arxiv_tool import search_arxiv
from app.tools.pubmed_tool import search_pubmed
from app.tools.semantic_scholar_tool import search_semantic_scholar


def _dedup_key(paper: dict) -> str:
    """Normalised title prefix used as dedup key."""
    return paper.get("title", "").lower().strip()[:60]


def unified_search(query: str, max_results: int = 10) -> list[dict]:
    """Search arXiv, PubMed, and Semantic Scholar; deduplicate; rank by citations."""
    all_papers: list[dict] = []
    for fn in (search_arxiv, search_pubmed, search_semantic_scholar):
        try:
            all_papers.extend(fn(query, max_results=max_results))
        except Exception:
            pass  # one source failing must not kill the whole search

    # Deduplicate by normalised title
    seen: set[str] = set()
    unique: list[dict] = []
    for paper in all_papers:
        key = _dedup_key(paper)
        if key and key not in seen:
            seen.add(key)
            unique.append(paper)

    # Rank by citation count (descending)
    unique.sort(key=lambda p: p.get("citation_count", 0), reverse=True)
    return unique[:max_results]
