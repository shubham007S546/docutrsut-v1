# DocuTrust: Complete Repository Implementation Audit

**Audit Timestamp:** 2026-10-22T22:35:00+05:30  
**Repository:** `DocuTrust` (`c:\Users\shubh\Downloads\docutrust`)  
**Auditor:** Senior AI Engineer, RAG Researcher, Backend Architect, Security Engineer, and Software Testing Specialist  
**Evaluated Environment:** Windows, Python 3.12, Node.js / Next.js 16, PostgreSQL (Neon Serverless), FAISS CPU, PyTorch, Sentence-Transformers  

---

## 1. Executive Summary

DocuTrust is a trust-oriented multi-agent compliance intelligence and retrieval-augmented generation (RAG) platform. The codebase contains a working foundational architecture featuring:
- A Next.js 16 frontend with Tailwind CSS and Recharts;
- A FastAPI backend executing a 12-stage multi-agent trust loop;
- In-process dense vector search via FAISS (`sentence-transformers/all-MiniLM-L6-v2`);
- BM25 sparse keyword retrieval (`rank_bm25`);
- Reciprocal Rank Fusion (RRF, $k=60$);
- Cross-encoder reranking (`ms-marco-MiniLM-L-6-v2`);
- Multi-tenant cryptographic isolation, claim verification, conflict analysis, and SHA-256 evidence receipts.

However, several critical architectural gaps, incomplete integrations, hardcoded heuristics, and unverified data pathways were identified that prevent the platform from operating as a fully generalized, research-grade document intelligence system. This audit catalogues every component, data flow, failure mode, and implementation status.

---

## 2. Technology Stack & Component Inventory

| Layer | Declared Technologies | Actual Implementation & Dependencies | Audit Notes |
|---|---|---|---|
| **Frontend UI** | Next.js 14, React 19, Tailwind CSS | Next.js 16.3.3 (App Router), React 19, Tailwind CSS v4, Lucide Icons, Recharts | Working. Dashboard and modal views render cleanly. |
| **BFF & Edge API** | Next.js API Routes, Better Auth | `app/api/query/stream/route.ts`, `app/api/documents/upload/route.ts`, Better Auth HMAC assertions | Partially diverged. Next.js route has its own internal lightweight RAG logic that bypasses FastAPI when backend is unreachable. |
| **Backend API** | FastAPI, Uvicorn, Pydantic v2 | FastAPI 0.115+, Uvicorn 0.32+, Pydantic 2.8+ (`backend/main.py`) | Fully functional. All 33 unit tests pass. |
| **Database & Schema** | PostgreSQL (Neon), Drizzle ORM | Neon Serverless PostgreSQL with Drizzle tables (`docutrust_tenants`, `docutrust_documents`, `docutrust_document_chunks`, `docutrust_query_runs`, `docutrust_reviews`) | Postgres schema defined. `MemoryStore` is used as in-memory default when database connection is not required. |
| **Dense Vector Store** | FAISS | In-process FAISS CPU index via `RAG_project/vectorstore/faiss_db.py` | Active in `rag_engine.py`. Embeds via `sentence-transformers/all-MiniLM-L6-v2`. |
| **Sparse Lexical Search**| BM25 | `rank_bm25.BM25Okapi` in `RAG_project/retriever/bm25.py` | Working and integrated into `TenantRAGIndex`. |
| **Reranking** | Cross-Encoder | `sentence-transformers/CrossEncoder` (`ms-marco-MiniLM-L-6-v2`) | Implemented in `rag_engine.py`, but **bypassed by default** in `workflow.py` line 292 where `rerank` parameter is not enabled. |
| **LLM Provider Chain** | Groq, Gemini, Vercel AI Gateway | `backend/providers/fallback.py`: Groq (`llama-3.3-70b-versatile` / `gpt-oss-120b`), Gemini (`gemini-2.5-flash`), with deterministic grounded fallback | Live API requests to Groq confirmed working. Deterministic fallback active when credentials fail. |
| **Document Ingestion** | PyMuPDF (`fitz`), pdfplumber, python-docx, mammoth | `backend/ingestion.py` uses `fitz` and `pdfplumber`. DOCX rejected with error in Python backend. Page numbers discarded during extraction. | Critical gap. Page numbers are stripped; OCR is absent. |

---

## 3. End-to-End Data Flow Trace & Analysis

### Flow 1: Document Upload & Ingestion
```text
User File Upload (PDF, DOCX, TXT)
  ├── Route A (Next.js): /api/documents/upload
  │     ├── Parses text via 'unpdf' or 'mammoth'
  │     ├── Stores chunks in Neon PostgreSQL (docutrust_document_chunks)
  │     └── [GAP]: Does NOT notify or index into Python FAISS/BM25 rag_engine!
  └── Route B (FastAPI): /api/documents/upload
        ├── Validates MIME against {"application/pdf", "text/plain", "text/markdown"}
        ├── [GAP]: Rejects DOCX with IngestionError
        ├── PyMuPDF extracts text, but concatenates with "\n\n", discarding page boundaries
        ├── Chunks created with target_chars=1400, overlap=160
        └── store.ingest_document:
              ├── MemoryStore: calls rag_engine.index_text(..., version="v1")
              └── [GAP]: PostgresStore inserts DB rows but fails to index into rag_engine!
```

### Flow 2: Query Processing & Specialist Dispatch
```text
User Natural Language Query
  ├── Validated via Pydantic QueryIn (3-4000 chars)
  ├── RequestContext verifies HMAC-signed BFF assertion (X-Internal-Assertion)
  ├── supervisor_plan analyzes query intent and dispatches specialists (Policy, Privacy, Security, Legal, Conflict)
  ├── rag_engine.retrieve(query, tenant_id, top_k=8)
  │     ├── BM25 search over tenant documents
  │     ├── FAISS dense vector search over tenant embeddings
  │     ├── Reciprocal Rank Fusion (RRF, k=60)
  │     └── [GAP]: Reranking is skipped unless rerank=True is explicitly passed (not passed in workflow)
  ├── Evidence Sufficiency Check (assess_evidence_sufficiency)
  │     ├── [GAP]: Uses hardcoded keyword list ('antarctica', 'perdiem', etc.) rather than generalized thresholding
  ├── Policy Conflict Detection (detect_policy_conflicts)
  ├── Specialist LLM Execution (Groq / Gemini / Deterministic Fallback)
  ├── Claim-Level Verification (verify_claims_against_evidence)
  │     ├── [GAP]: Does not resolve explicit citations to indexed chunk metadata
  │     └── Verifies sentence-level semantic overlap against evidence quotes
  ├── Confidence Score: w1*R + w2*C + w3*A + w4*V - w5*F
  ├── Decision Gate:
  │     ├── If INSUFFICIENT or Conflict or Confidence < 0.70 -> ESCALATE TO HUMAN REVIEW
  │     └── Else -> ANSWER
  └── Cryptographic Evidence Receipt generated (SHA-256 provenance hash)
```

---

## 4. Implementation Matrix

Statuses:
- **Implemented and verified:** Code exists, executes correctly, and verified with tests.
- **Implemented but unverified:** Code exists but lacks complete integration or automated test verification.
- **Partially implemented:** Feature partially implemented with notable omissions or hardcoding.
- **Missing:** Required component is absent.
- **Not applicable:** Not required for the system architecture.

| Component / Subsystem | Status | Current Implementation Details | Identified Gap or Defect |
|---|---|---|---|
| **Multi-Tenant Isolation** | Implemented and verified | SHA-256 hash tenant derivation, HMAC assertion validation, tenant metadata filtering | Complete. 0 cross-tenant leaks verified in tests. |
| **Dense Vector Retrieval** | Implemented and verified | FAISS CPU index with `sentence-transformers/all-MiniLM-L6-v2` | Embedding model not configurable via main Settings; dimension check absent. |
| **BM25 Lexical Retrieval** | Implemented and verified | `rank_bm25.BM25Okapi` in `TenantRAGIndex` | Lexical index not automatically updated on document deletion. |
| **Hybrid Retrieval & RRF** | Implemented and verified | Reciprocal Rank Fusion ($k=60$) combining BM25 and FAISS | $k$ parameter hardcoded; fusion method not configurable. |
| **Cross-Encoder Reranking** | Partially implemented | `ms-marco-MiniLM-L-6-v2` present in `rag_engine.py` | Bypassed in `workflow.py` (`rerank` not passed); fallback on OOM not fully guarded. |
| **Retrieval Traceability** | Partially implemented | Retrieval score passed to evidence | Raw BM25, FAISS, RRF scores, candidate IDs, and latency not recorded in structured trace. |
| **PDF Text Extraction** | Partially implemented | PyMuPDF (`fitz`) and `pdfplumber` | Page numbers discarded; text merged into flat string; chunk `page_start/end` is `None`. |
| **DOCX Text Extraction** | Missing in backend | Next.js uses `mammoth`, but backend raises `IngestionError` | `python-docx` is available in environment but unused in `backend/ingestion.py`. |
| **OCR for Scanned Docs** | Missing | Explicitly rejected with error message | No graceful OCR fallback pipeline for raster-only PDFs or image uploads. |
| **Document ACLs & Authz** | Partially implemented | Tenant-level isolation enforced via BFF assertion | Document-level permission filtering (by role or department) is absent in retrieval. |
| **Claim Verification** | Partially implemented | Word overlap and rule-based entailment in `evidence_intelligence.py` | Deterministic resolution of citation tags `[Doc | Sec | Page]` to real chunk IDs missing. |
| **Abstention & Uncertainty** | Partially implemented | `assess_evidence_sufficiency` checks coverage and scores | Hardcoded entity list (`"antarctica"`, etc.) limits generalization to novel topics. |
| **Prompt Injection Defense** | Partially implemented | System prompt instructions ("Answer ONLY from evidence") | Delimiters around untrusted content can be hardened with XML/tag boundaries. |
| **Safe Document Deletion** | Missing | Ingestion appends only | No deletion endpoint or index eviction mechanism for FAISS and BM25. |
| **Empirical Evaluation Suite**| Partially implemented | Golden dataset (40 items in pilot), IR metrics (Precision@k, Recall@k, MRR, nDCG) | Only 1 baseline automated; comparative multi-baseline evaluation requires end-to-end runner. |

---

## 5. Security & Reliability Vulnerability Inventory

1. **Dual Storage Desynchronization**: Next.js route `/api/documents/upload` writes directly to Neon Postgres but does not call the Python RAG indexing endpoint. Conversely, `PostgresStore.ingest_document` in Python writes to Postgres but forgets to invoke `rag_engine.index_text()`. Only `MemoryStore` correctly indexes into `rag_engine`.
2. **Missing Page-Level Provenance**: Chunks in `rag_engine.py` have hardcoded `page: 1` because `ingestion.py` flattens all pages before chunking. Citations cannot display the actual original page number.
3. **Hardcoded Abstention Triggers**: Detecting unestablished topics via `term in ("antarctica", ...)` is brittle and fails for general compliance documents (e.g. asking about intellectual property, stock grants, or medical leave).
4. **Bypassed Reranking Component**: The cross-encoder reranker in `backend/rag_engine.py` is never called by `backend/graph/workflow.py`, meaning all production and test queries run only on un-reranked hybrid retrieval.
5. **Lack of Document-Level Access Control (ACL)**: All documents in a tenant are accessible to any user in that tenant regardless of role (e.g., general staff vs. compliance officer).
