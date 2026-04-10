"""PubMed search tool — uses NCBI E-utilities REST API (no key required)."""

import xml.etree.ElementTree as ET

import httpx

from app.tools.base import BaseSearchTool

_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _fetch_abstracts(pmids: list[str]) -> dict[str, dict]:
    """Return {pmid: {title, abstract, authors, year, journal}} for each ID."""
    if not pmids:
        return {}
    resp = httpx.get(
        _EFETCH,
        params={"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"},
        timeout=20,
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    out: dict[str, dict] = {}
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID", "")
        title = article.findtext(".//ArticleTitle", "")
        abstract = " ".join(
            t.text or ""
            for t in article.findall(".//AbstractText")
        ).strip()
        authors = [
            f"{a.findtext('LastName', '')} {a.findtext('ForeName', '')}".strip()
            for a in article.findall(".//Author")
        ]
        year_text = article.findtext(".//PubDate/Year", "")
        year = int(year_text) if year_text.isdigit() else None
        journal = article.findtext(".//Journal/Title", "")
        out[pmid] = {
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "year": year,
            "journal": journal,
        }
    return out


class PubMedTool(BaseSearchTool):
    def search(self, query: str, max_results: int = 10) -> list[dict]:
        search_resp = httpx.get(
            _ESEARCH,
            params={"db": "pubmed", "term": query, "retmax": max_results, "retmode": "json"},
            timeout=15,
        )
        search_resp.raise_for_status()
        data = search_resp.json()
        pmids: list[str] = data.get("esearchresult", {}).get("idlist", [])

        abstracts = _fetch_abstracts(pmids)
        papers = []
        for pmid in pmids:
            meta = abstracts.get(pmid, {})
            papers.append({
                "title": meta.get("title", ""),
                "authors": meta.get("authors", []),
                "abstract": meta.get("abstract", ""),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "year": meta.get("year"),
                "citation_count": 0,
                "source": "pubmed",
                "paper_id": pmid,
                "journal": meta.get("journal", ""),
            })
        return papers


def search_pubmed(query: str, max_results: int = 10) -> list[dict]:
    return PubMedTool().search(query, max_results)
