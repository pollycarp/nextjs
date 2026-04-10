"""Shared interface for all academic search tools."""

from abc import ABC, abstractmethod


class BaseSearchTool(ABC):
    """All search tools return a list of paper dicts with these standard fields:

    {
        "title":          str,
        "authors":        list[str],
        "abstract":       str,
        "url":            str,
        "year":           int | None,
        "citation_count": int,        # 0 when unknown
        "source":         str,        # "arxiv" | "pubmed" | "semantic_scholar"
        "paper_id":       str,
    }
    """

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> list[dict]:
        """Search and return standardised paper dicts."""
        ...
