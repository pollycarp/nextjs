<<<<<<< HEAD
# Research Assistance — Build Plan

An AI-powered research assistant for IDinsight, covering Retrieval-Augmented Generation (RAG), Corrective RAG, GraphRAG, and Multi-Agent Systems using LangGraph, CrewAI, and LlamaIndex.

---

## Existing Codebase Summary

**Location:** `nextjs/`

| Layer | Status | Notes |
|---|---|---|
| Frontend UI | 95% done | Next.js 16, React 19, Tailwind v4 — Chat, Dashboard, Projects, Documents, Analytics tabs all built |
| Backend API | 0% | `/api/research` and `/api/upload` are called by UI but don't exist |
| RAG / AI | 0% | LangChain, OpenAI, Pinecone mentioned in footer but never wired up |
| Database | 0% | All data is mock/local state |
| Auth | 0% | No user system |

---

## Target Architecture

```
research_assistance/
├── nextjs/                  ← existing Next.js frontend
└── backend/                 ← Python FastAPI service (to build)
    ├── app/
    │   ├── main.py
    │   ├── api/
    │   ├── core/
    │   ├── services/
    │   │   ├── ingestion.py
    │   │   ├── retrieval.py
    │   │   ├── rag_chain.py
    │   │   ├── crag.py
    │   │   ├── graph_rag.py
    │   │   └── citations.py
    │   ├── agents/
    │   │   ├── researcher.py
    │   │   ├── critic.py
    │   │   ├── writer.py
    │   │   └── orchestrator.py
    │   ├── tools/
    │   │   ├── arxiv_tool.py
    │   │   ├── pubmed_tool.py
    │   │   └── semantic_scholar_tool.py
    │   └── models/
    ├── tests/
    │   ├── test_phase1.py
    │   ├── test_phase2.py
    │   ├── test_phase3.py
    │   ├── test_phase4.py
    │   ├── test_phase5.py
    │   ├── test_phase6.py
    │   └── test_phase7.py
    ├── requirements.txt
    ├── Dockerfile
    └── .env
```

### Multi-Agent Pipeline

```
User Query
    │
    ▼
Manager Agent (LangGraph state machine)
    ├─→ Researcher Agent  (CrewAI)  → fetches sources, runs RAG/CRAG/web search
    ├─→ Critic Agent      (CrewAI)  → checks facts, flags unsupported claims
    └─→ Writer Agent      (CrewAI)  → synthesizes final structured report
```

---

## Phased Build Plan

---

### Phase 1 — Foundation: Python Backend & Environment

**Goal:** Stand up a FastAPI backend that the Next.js frontend can talk to.

**Architecture decision:** The AI/RAG work is Python-native (LangGraph, CrewAI, LlamaIndex). Build a FastAPI service alongside the Next.js frontend and proxy API calls through Next.js's `next.config.ts` rewrites.

**Tasks:**

1. Create `backend/` directory with FastAPI scaffold
2. Set up `requirements.txt`:
   ```
   fastapi uvicorn python-dotenv
   langchain langchain-openai langchain-community
   llama-index llama-index-vector-stores-chroma
   chromadb
   pinecone-client
   openai anthropic
   crewai langgraph
   pypdf python-docx
   pytest pytest-asyncio httpx
   ```
3. Create `/health` endpoint
4. Create stub `/api/research` and `/api/upload` endpoints (return mock data)
5. Configure CORS so Next.js on port 3000 can call backend on port 8000
6. Add `next.config.ts` rewrite: `/api/*` → `http://localhost:8000/api/*`
7. Create `.env` with keys: `OPENAI_API_KEY`, `PINECONE_API_KEY`, `ANTHROPIC_API_KEY`

**Tests (`tests/test_phase1.py`):**

```python
# test_health: GET /health returns 200 with {"status": "ok"}
# test_research_stub: POST /api/research returns valid schema
# test_upload_stub: POST /api/upload returns valid schema
# test_cors_headers: response includes correct CORS headers
# test_env_vars_loaded: all required env vars present and non-empty
```

**Definition of done:** `pytest tests/test_phase1.py` passes; frontend chat sends a message and receives a stub response without CORS errors.

---

### Phase 2 — Document Ingestion & Basic RAG

**Goal:** Upload a PDF, chunk and embed it, answer a question using retrieved context.

**Stack:** LlamaIndex for ingestion, ChromaDB for local vector store, OpenAI `text-embedding-3-small` for embeddings, GPT-4o-mini for generation.

**Tasks:**

1. **Ingestion pipeline** (`backend/app/services/ingestion.py`):
   - Accept PDF, DOCX, TXT
   - Parse with LlamaIndex `SimpleDirectoryReader`
   - Chunk with `SentenceSplitter` (chunk_size=512, overlap=50)
   - Generate embeddings → store in ChromaDB collection keyed by document ID
   - Return document metadata (page count, chunk count, status)

2. **Retrieval service** (`backend/app/services/retrieval.py`):
   - Accept query string + optional document filter
   - Embed query, search ChromaDB with cosine similarity, top-k=5
   - Return ranked chunks with source metadata (filename, page, score)

3. **RAG chain** (`backend/app/services/rag_chain.py`):
   - Build LangChain `RetrievalQA` chain
   - Prompt template: include retrieved context + user question
   - Return: `{ answer, sources: [{title, page, excerpt, score}] }`

4. **Wire up API endpoints:**
   - `POST /api/upload` → ingestion pipeline → return doc ID
   - `POST /api/research` with `research_type: "quick_search"` → RAG chain

5. **Connect frontend `/api/upload`** in `ResearchDashboard.tsx` to real endpoint (replace `setTimeout` simulation)

**Tests (`tests/test_phase2.py`):**

```python
# test_pdf_ingestion: upload sample PDF, assert chunk count > 0 and doc_id returned
# test_docx_ingestion: upload sample DOCX, assert success
# test_embedding_stored: after upload, query ChromaDB and get > 0 results
# test_retrieval_returns_relevant_chunks: query "methodology" → chunks contain that word
# test_retrieval_score_threshold: all returned chunks have score > 0.5
# test_rag_answer_not_empty: POST /api/research returns non-empty answer
# test_rag_sources_attached: response includes at least 1 source with filename
# test_rag_hallucination_guard: question outside document scope returns "I don't know" style answer
# test_unsupported_file_type: upload .exe → 400 error with clear message
```

**Definition of done:** Upload a research PDF via the Documents tab, ask a question in Chat, receive a grounded answer with source citations shown in the UI.

---

### Phase 3 — Advanced RAG: Corrective RAG (CRAG) + GraphRAG

**Goal:** Add retrieval quality evaluation, web search fallback, and entity-relationship understanding.

#### 3A — Corrective RAG

**How it works:** After retrieval, an LLM evaluator grades each chunk as `relevant`, `irrelevant`, or `ambiguous`. If all chunks score below threshold, trigger a web search (Tavily API) and use those results instead.

**Tasks:**

1. **Relevance grader** (`backend/app/services/crag.py`):
   - Prompt: *"Is this document chunk relevant to the query? Answer: yes/no/partial"*
   - Use GPT-4o-mini for speed/cost
   - Aggregate scores: if < 2 relevant chunks, flag as "insufficient"

2. **Web search fallback:**
   - Integrate Tavily Search API (`pip install tavily-python`)
   - If retrieval insufficient → search web → re-rank results → use as context
   - Tag sources as `source_type: "internal"` vs `source_type: "web"`

3. **Add `TAVILY_API_KEY` to `.env`**

4. **Expose via API:** `research_type: "comprehensive"` triggers CRAG pipeline

#### 3B — GraphRAG

**How it works:** Use an LLM to extract entities (people, organizations, concepts, metrics) and relationships from document chunks, store them as a knowledge graph (NetworkX in memory, Neo4j for production), and augment retrieval with graph traversal.

**Tasks:**

1. **Entity/relationship extractor** (`backend/app/services/graph_rag.py`):
   - Prompt LLM to extract `(entity1) --[relationship]--> (entity2)` triples from each chunk
   - Build NetworkX graph per document collection

2. **Graph-augmented retrieval:**
   - Standard vector search → get top-5 chunks
   - For each chunk, find connected entities in graph → fetch neighboring nodes
   - Expand context with related chunks

3. **Add `pip install networkx`** to requirements

4. **Expose via API:** `research_type: "literature_review"` triggers GraphRAG

**Tests (`tests/test_phase3.py`):**

```python
# test_relevance_grader_labels_relevant: relevant chunk + matching query → "yes"
# test_relevance_grader_labels_irrelevant: off-topic chunk → "no"
# test_crag_triggers_web_fallback: query with no matching docs → sources include web results
# test_crag_labels_source_type: all sources have "internal" or "web" source_type field
# test_entity_extraction: extract entities from a paragraph → returns list of (entity, type) tuples
# test_relationship_extraction: extract relations → returns (subject, relation, object) triples
# test_graph_builds_correctly: after extraction, NetworkX graph has > 0 nodes and edges
# test_graph_augmented_retrieval_expands_context: GraphRAG returns more chunks than pure vector search
# test_comprehensive_research_type_uses_crag: POST with research_type=comprehensive uses CRAG path
# test_literature_review_type_uses_graphrag: POST with research_type=literature_review uses GraphRAG
```

**Definition of done:** A question with no relevant documents in the vector store returns web-sourced results labeled as such; a question about relationships between concepts returns graph-augmented context.

---

### Phase 4 — Multi-Agent System with CrewAI + LangGraph

**Goal:** Build a coordinated agent pipeline for deep research tasks: Researcher → Critic → Writer, orchestrated by a Manager.

**LangGraph state machine:**

```
States: START → research → critique → [revise | write] → END
Edges:
  research → critique (always)
  critique → revise (if flagged_claims > 2)
  critique → write (if flagged_claims ≤ 2)
  revise → critique (loop back, max 2 iterations)
```

**State schema:**

```python
class ResearchState(TypedDict):
    query: str
    research_output: str
    critique_output: str
    revision_count: int
    final_report: str
    sources: list[Source]
    flagged_claims: list[str]
```

**Tasks:**

1. **Researcher Agent** (`backend/app/agents/researcher.py`):
   - Role: "Senior Research Analyst"
   - Tools: RAG retrieval, Tavily search, arXiv API
   - Goal: gather evidence for the query

2. **Critic Agent** (`backend/app/agents/critic.py`):
   - Role: "Fact-Checking Specialist"
   - Tools: source verification, claim scoring
   - Goal: identify unsupported claims in researcher output

3. **Writer Agent** (`backend/app/agents/writer.py`):
   - Role: "Research Report Writer"
   - Tools: none (synthesis only)
   - Goal: produce structured Markdown report with sections, citations, confidence scores

4. **Orchestrator** (`backend/app/agents/orchestrator.py`): LangGraph state machine wiring all agents

5. **Streaming endpoint:** `POST /api/research/stream` using Server-Sent Events so the frontend can show which agent is currently active

6. **Update `ChatInterface.tsx`:** Replace `fetch` with SSE connection; display agent status badges ("Researcher is working...", "Critic reviewing...")

**Tests (`tests/test_phase4.py`):**

```python
# test_researcher_agent_returns_sources: run researcher on known topic → sources list non-empty
# test_critic_flags_unsupported_claim: inject a fabricated claim → critic flags it
# test_critic_passes_supported_claim: inject a well-sourced claim → critic approves it
# test_writer_produces_sections: writer output contains Introduction, Methods, Findings, Conclusion
# test_writer_includes_citations: final report markdown contains citation references
# test_orchestrator_revision_loop: state with 3 flagged claims → revision loop triggers
# test_orchestrator_max_revisions_respected: revision_count never exceeds 2
# test_orchestrator_ends_in_final_report: any query → state.final_report non-empty at END
# test_streaming_endpoint_sends_sse_events: SSE stream emits agent_status events
# test_full_pipeline_e2e: upload PDF + query → multi-agent report with sources in < 120 seconds
```

**Definition of done:** Ask "What are the key findings on microfinance impact in Sub-Saharan Africa?" and see a structured, cited Markdown report generated by the agent pipeline with real-time status updates in the chat UI.

---

### Phase 5 — Academic Source Integration

**Goal:** Connect to real academic databases so the Researcher Agent can pull from arXiv, PubMed, and Semantic Scholar.

**Tasks:**

1. **arXiv tool** (`backend/app/tools/arxiv_tool.py`):
   - Use `arxiv` Python package
   - Search by query, return top-10 paper metadata + abstracts
   - Download and auto-ingest PDFs into vector store

2. **PubMed tool** (`backend/app/tools/pubmed_tool.py`):
   - Use NCBI E-utilities REST API (free, no key needed for low volume)
   - Search, fetch abstracts, return structured results

3. **Semantic Scholar tool** (`backend/app/tools/semantic_scholar_tool.py`):
   - Use Semantic Scholar API (free tier)
   - Returns citation counts, influence scores — useful for ranking sources

4. **Citation formatter** (`backend/app/services/citations.py`):
   - Support APA, MLA, Chicago output formats
   - Parse raw metadata into formatted strings

5. **Unified search interface:** All tools share a `BaseSearchTool` interface; Researcher Agent calls them all and merges results ranked by relevance + citation count

6. **Add to `.env`:** `SEMANTIC_SCHOLAR_API_KEY` (optional, higher rate limits)

**Tests (`tests/test_phase5.py`):**

```python
# test_arxiv_search_returns_papers: search "RAG language models" → ≥ 5 papers
# test_arxiv_paper_has_required_fields: each result has title, authors, abstract, url, year
# test_pubmed_search_returns_papers: search "randomized control trial Kenya" → ≥ 3 papers
# test_pubmed_abstract_not_empty: all results have non-empty abstracts
# test_semantic_scholar_returns_citation_count: results include citation_count > 0 for known paper
# test_citation_apa_format: formatter produces APA string with author, year, title, journal
# test_citation_mla_format: formatter produces MLA format
# test_unified_search_deduplicates: same paper from arxiv and semantic scholar → appears once
# test_unified_search_ranked_by_citations: results sorted descending by citation_count
# test_auto_ingest_arxiv_pdf: fetch paper PDF → ingested into ChromaDB → queryable
```

**Definition of done:** Ask "Summarize the state of RCT evidence on conditional cash transfers" and receive a report citing real papers from PubMed and Semantic Scholar with proper APA citations.

---

### Phase 6 — Persistence, Auth & Full Frontend Integration

**Goal:** Replace all mock data with real persistence; add user auth so projects and documents survive page reloads.

**Tasks:**

1. **Database:** Add PostgreSQL via Supabase (free tier). Use `sqlalchemy` + `asyncpg`.
   - Tables: `users`, `projects`, `documents`, `conversations`, `messages`

2. **Auth:** Supabase Auth (JWT). Add `Authorization: Bearer <token>` header to all frontend API calls.

3. **Projects API:**
   - `GET /api/projects` — list user's projects
   - `POST /api/projects` — create project
   - `PUT /api/projects/{id}` — update (title, description, tags)
   - `DELETE /api/projects/{id}` — delete

4. **Documents API:** Persist document metadata to DB; store actual files in Supabase Storage (S3-compatible).

5. **Conversations API:** Persist chat history. Reload conversation on page visit.

6. **Analytics API:** Real metrics from DB (`SELECT COUNT(*)` queries, timestamps).

7. **Frontend wiring:** Replace all `useState` mock data in `ResearchDashboard.tsx` with real API calls using `SWR` or `React Query`.

8. **Production vector store:** Swap ChromaDB → Pinecone for persistence across restarts.

**Tests (`tests/test_phase6.py`):**

```python
# test_create_project: POST /api/projects → 201 with project ID
# test_list_projects_returns_only_user_projects: user A cannot see user B's projects
# test_document_upload_persists_metadata: upload doc → GET /api/documents includes it
# test_document_survives_restart: restart server → document still in DB
# test_conversation_history_persists: send 3 messages → GET /api/conversations returns all 3
# test_pinecone_store_and_retrieve: store embedding → retrieve by query matches original
# test_auth_required_on_protected_routes: no token → 401 on /api/projects
# test_invalid_token_rejected: tampered JWT → 401
# test_analytics_counts_are_accurate: 5 searches → analytics shows search_count=5
```

**Definition of done:** Create an account, upload 3 documents, have a conversation about them, close the browser, log back in — everything is exactly where you left it.

---

### Phase 7 — Deployment & Production Hardening

**Goal:** Ship to production with monitoring, rate limiting, and a passing CI pipeline.

**Tasks:**

1. **Frontend deployment:** Vercel (already configured in the codebase). Set env vars in Vercel dashboard.

2. **Backend deployment:** Railway or Render (both support Python, free tier available). Containerize with `Dockerfile`.

3. **CI/CD:** GitHub Actions workflow:
   ```yaml
   on: [push, pull_request]
   jobs:
     test-backend:  run pytest
     test-frontend: run next build + eslint
     deploy:        on main branch, deploy to Railway + Vercel
   ```

4. **Rate limiting:** Add `slowapi` middleware — 20 requests/min per user for `/api/research`.

5. **Observability:**
   - Structured logging with `structlog`
   - LangSmith tracing for all LangChain/LangGraph calls (set `LANGCHAIN_TRACING_V2=true`)
   - Sentry for error tracking

6. **Cost guardrails:** Track OpenAI token usage per user; warn at $5, hard-limit at $20/month.

7. **Update `layout.tsx`** with real app name and description.

**Tests (`tests/test_phase7.py`):**

```python
# test_health_endpoint_returns_200: GET /health → 200 (smoke test for prod)
# test_rate_limit_enforced: 21 rapid requests → 21st returns 429
# test_openai_tokens_tracked: after research call, token count recorded in DB
# test_docker_build_succeeds: docker build exits 0
# test_langsmith_trace_created: research call → trace appears in LangSmith (integration test)
# test_frontend_build_succeeds: next build exits 0 with no type errors
# test_eslint_passes: eslint returns 0 warnings
```

**Definition of done:** `main` branch push triggers CI; all tests pass; frontend live on Vercel; backend live on Railway; LangSmith shows traces.

---

## Summary

| Phase | Focus | Key Output | Tests |
|---|---|---|---|
| 1 | FastAPI scaffold | Backend running, stubs wired to frontend | 5 |
| 2 | Basic RAG | Upload PDF, get grounded answers with citations | 9 |
| 3 | CRAG + GraphRAG | Web fallback, entity-relationship context | 10 |
| 4 | Multi-Agent (CrewAI + LangGraph) | Researcher → Critic → Writer pipeline | 10 |
| 5 | Academic APIs | arXiv, PubMed, Semantic Scholar, APA citations | 10 |
| 6 | Persistence + Auth | Real DB, login, everything saved | 9 |
| 7 | Deployment + Hardening | Live in production, CI/CD green | 7 |

**Total: 60 tests across 7 phases.**

Each phase gate: all tests for that phase must pass before starting the next.

---

## Environment Variables

```env
# LLM Providers
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Vector Store
PINECONE_API_KEY=
PINECONE_INDEX_NAME=research-assistant

# Web Search
TAVILY_API_KEY=

# Academic APIs
SEMANTIC_SCHOLAR_API_KEY=   # optional

# Database
DATABASE_URL=               # Supabase PostgreSQL connection string
SUPABASE_URL=
SUPABASE_ANON_KEY=

# Observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=          # LangSmith
SENTRY_DSN=
```

## Key Dependencies

| Library | Purpose |
|---|---|
| `fastapi` + `uvicorn` | Python backend framework |
| `langchain` + `langchain-openai` | LLM chains and prompt management |
| `langgraph` | Multi-agent state machine orchestration |
| `crewai` | Role-based agent definitions |
| `llama-index` | Document ingestion and indexing |
| `chromadb` | Local vector store (development) |
| `pinecone-client` | Production vector store |
| `tavily-python` | Web search fallback for CRAG |
| `arxiv` | arXiv paper search and download |
| `networkx` | In-memory knowledge graph for GraphRAG |
| `sqlalchemy` + `asyncpg` | Async PostgreSQL ORM |
| `pytest` + `pytest-asyncio` | Test framework |
| `structlog` | Structured logging |
=======
This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
>>>>>>> 803472ef3263890f7df570b7dfa5b37b21890a35
