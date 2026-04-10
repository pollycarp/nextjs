"""
Phase 5 tests — Academic Source Integration.
All external HTTP calls are mocked.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

# ── Shared fake data ───────────────────────────────────────────────────────── #

_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.00001v1</id>
    <title>RAG for Language Models: A Survey</title>
    <summary>This paper surveys retrieval-augmented generation methods.</summary>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Jones</name></author>
    <published>2023-01-01T00:00:00Z</published>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2301.00002v1</id>
    <title>Dense Retrieval Techniques</title>
    <summary>We study dense retrieval for open-domain QA.</summary>
    <author><name>Carol White</name></author>
    <published>2023-02-01T00:00:00Z</published>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2301.00003v1</id>
    <title>Corrective RAG</title>
    <summary>We propose corrective RAG to improve answer quality.</summary>
    <author><name>Dave Brown</name></author>
    <published>2023-03-01T00:00:00Z</published>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2301.00004v1</id>
    <title>GraphRAG Approaches</title>
    <summary>Graph-based RAG improves entity-level reasoning.</summary>
    <author><name>Eve Green</name></author>
    <published>2023-04-01T00:00:00Z</published>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2301.00005v1</id>
    <title>Benchmarking RAG Systems</title>
    <summary>We benchmark various RAG configurations.</summary>
    <author><name>Frank Lee</name></author>
    <published>2023-05-01T00:00:00Z</published>
  </entry>
</feed>"""

_PUBMED_ESEARCH = {
    "esearchresult": {"idlist": ["12345678", "87654321", "11111111"]}
}

_PUBMED_EFETCH_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>Impact of cash transfers in Kenya</ArticleTitle>
        <Abstract><AbstractText>This RCT examines conditional cash transfers.</AbstractText></Abstract>
        <AuthorList>
          <Author><LastName>Nguyen</LastName><ForeName>Thi</ForeName></Author>
        </AuthorList>
        <Journal><Title>Journal of Development Economics</Title></Journal>
      </Article>
      <PubDate><Year>2022</Year></PubDate>
    </MedlineCitation>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>87654321</PMID>
      <Article>
        <ArticleTitle>Microfinance and poverty reduction</ArticleTitle>
        <Abstract><AbstractText>We study microfinance impact on household income.</AbstractText></Abstract>
        <AuthorList>
          <Author><LastName>Osei</LastName><ForeName>Kwame</ForeName></Author>
        </AuthorList>
        <Journal><Title>World Development</Title></Journal>
      </Article>
      <PubDate><Year>2021</Year></PubDate>
    </MedlineCitation>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>11111111</PMID>
      <Article>
        <ArticleTitle>RCT evidence on nutrition interventions</ArticleTitle>
        <Abstract><AbstractText>Randomized control trials on nutrition in Sub-Saharan Africa.</AbstractText></Abstract>
        <AuthorList>
          <Author><LastName>Mensah</LastName><ForeName>Ama</ForeName></Author>
        </AuthorList>
        <Journal><Title>Lancet</Title></Journal>
      </Article>
      <PubDate><Year>2020</Year></PubDate>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""

_SS_RESPONSE = {
    "data": [
        {
            "paperId": "ss001",
            "title": "RAG for Language Models: A Survey",  # duplicate of arxiv
            "authors": [{"name": "Alice Smith"}],
            "abstract": "Survey of RAG methods.",
            "year": 2023,
            "citationCount": 120,
            "url": "https://www.semanticscholar.org/paper/ss001",
        },
        {
            "paperId": "ss002",
            "title": "Knowledge Graphs in NLP",
            "authors": [{"name": "Grace Kim"}],
            "abstract": "Knowledge graphs improve NLP tasks.",
            "year": 2022,
            "citationCount": 85,
            "url": "https://www.semanticscholar.org/paper/ss002",
        },
    ]
}


def _mock_httpx_get(url, **kwargs):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "arxiv.org" in url:
        resp.text = _ARXIV_XML
    elif "esearch" in url:
        resp.text = json.dumps(_PUBMED_ESEARCH)
        resp.json = lambda: _PUBMED_ESEARCH
    elif "efetch" in url:
        resp.text = _PUBMED_EFETCH_XML
    elif "semanticscholar" in url:
        resp.text = json.dumps(_SS_RESPONSE)
        resp.json = lambda: _SS_RESPONSE
    return resp


# ── arXiv tests ────────────────────────────────────────────────────────────── #

def test_arxiv_search_returns_papers():
    with patch("app.tools.arxiv_tool.httpx.get", side_effect=_mock_httpx_get):
        from app.tools.arxiv_tool import search_arxiv
        papers = search_arxiv("RAG language models", max_results=5)
    assert len(papers) >= 5


def test_arxiv_paper_has_required_fields():
    with patch("app.tools.arxiv_tool.httpx.get", side_effect=_mock_httpx_get):
        from app.tools.arxiv_tool import search_arxiv
        papers = search_arxiv("RAG language models", max_results=5)
    for p in papers:
        assert p["title"], "title missing"
        assert isinstance(p["authors"], list), "authors must be a list"
        assert p["abstract"], "abstract missing"
        assert p["url"], "url missing"
        assert p["year"] is not None, "year missing"


# ── PubMed tests ───────────────────────────────────────────────────────────── #

def test_pubmed_search_returns_papers():
    with patch("app.tools.pubmed_tool.httpx.get", side_effect=_mock_httpx_get):
        from app.tools.pubmed_tool import search_pubmed
        papers = search_pubmed("randomized control trial Kenya", max_results=5)
    assert len(papers) >= 3


def test_pubmed_abstract_not_empty():
    with patch("app.tools.pubmed_tool.httpx.get", side_effect=_mock_httpx_get):
        from app.tools.pubmed_tool import search_pubmed
        papers = search_pubmed("cash transfers Africa", max_results=5)
    for p in papers:
        assert len(p["abstract"]) > 0, f"Empty abstract for: {p['title']}"


# ── Semantic Scholar tests ─────────────────────────────────────────────────── #

def test_semantic_scholar_returns_citation_count():
    with patch("app.tools.semantic_scholar_tool.httpx.get", side_effect=_mock_httpx_get):
        from app.tools.semantic_scholar_tool import search_semantic_scholar
        papers = search_semantic_scholar("RAG language models", max_results=5)
    assert any(p["citation_count"] > 0 for p in papers)


# ── Citation formatter tests ───────────────────────────────────────────────── #

_META = {
    "title": "Impact of Cash Transfers",
    "authors": ["Nguyen Thi", "Osei Kwame"],
    "year": 2022,
    "journal": "Journal of Development Economics",
    "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
}


def test_citation_apa_format():
    from app.services.citations import format_apa
    apa = format_apa(_META)
    assert "Nguyen Thi" in apa or "Osei Kwame" in apa
    assert "2022" in apa
    assert "Impact of Cash Transfers" in apa
    assert "Journal of Development Economics" in apa


def test_citation_mla_format():
    from app.services.citations import format_mla
    mla = format_mla(_META)
    assert "Impact of Cash Transfers" in mla
    assert "2022" in mla


# ── Unified search tests ───────────────────────────────────────────────────── #

def test_unified_search_deduplicates():
    """The same title appearing in arXiv and Semantic Scholar is deduplicated."""
    with patch("app.tools.arxiv_tool.httpx.get", side_effect=_mock_httpx_get), \
         patch("app.tools.pubmed_tool.httpx.get", side_effect=_mock_httpx_get), \
         patch("app.tools.semantic_scholar_tool.httpx.get", side_effect=_mock_httpx_get):
        from app.tools.unified_search import unified_search
        results = unified_search("RAG language models", max_results=20)

    titles = [p["title"].lower()[:60] for p in results]
    # "RAG for Language Models: A Survey" appears in both arXiv and SS — should be once
    rag_survey = [t for t in titles if "rag for language models" in t]
    assert len(rag_survey) == 1, f"Duplicate found: {rag_survey}"


def test_unified_search_ranked_by_citations():
    """Results are sorted descending by citation_count."""
    with patch("app.tools.arxiv_tool.httpx.get", side_effect=_mock_httpx_get), \
         patch("app.tools.pubmed_tool.httpx.get", side_effect=_mock_httpx_get), \
         patch("app.tools.semantic_scholar_tool.httpx.get", side_effect=_mock_httpx_get):
        from app.tools.unified_search import unified_search
        results = unified_search("RAG", max_results=20)

    counts = [p["citation_count"] for p in results]
    assert counts == sorted(counts, reverse=True), f"Not sorted: {counts}"


# ── Auto-ingest test ───────────────────────────────────────────────────────── #

@pytest.mark.asyncio
async def test_auto_ingest_arxiv_pdf(sample_pdf_bytes):
    """fetch_and_ingest downloads an arXiv PDF and stores it in ChromaDB."""
    fake_pdf_resp = MagicMock()
    fake_pdf_resp.raise_for_status = MagicMock()
    fake_pdf_resp.content = sample_pdf_bytes

    with patch("app.tools.arxiv_tool.httpx.get", return_value=fake_pdf_resp):
        from app.tools.arxiv_tool import fetch_and_ingest
        result = await fetch_and_ingest("2301.00001")

    assert result["status"] in ("processed", "empty")
    assert result["filename"] == "2301.00001.pdf"

    # Verify the document is now queryable in ChromaDB
    from app.services.ingestion import get_collection
    collection = get_collection()
    assert collection.count() > 0
