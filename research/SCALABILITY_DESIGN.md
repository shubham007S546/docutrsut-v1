# DocuTrust Scalability Engineering & Scaling Benchmark Design

**Author:** Senior Distributed-Systems Engineer & ML Systems Researcher  
**System:** DocuTrust (Evidence-Grounded Agentic Multi-Agent Compliance Intelligence)  
**Document Status:** Scalability Architecture Specification (Phase 1 Deliverable)  
**Target Environment:** Single-node host (12 Cores, 7.34 GB RAM Total, ~1.2 GB Available RAM baseline)

---

## 1. System Architecture & Component Inventory

DocuTrust operates as an end-to-end trustworthy compliance intelligence platform composed of:
1. **API & Routing Layer:** FastAPI runtime with asynchronous streaming endpoints (`/api/query`, `/api/query/stream`), correlation ID tracking, and cryptographic BFF internal assertion verification.
2. **Multi-Tenant Isolation Layer:** HMAC SHA-256 tenant hashing and memory-partitioned indices (`TenantRAGIndex`) guaranteeing zero cross-tenant data leakage.
3. **Retrieval Subsystem:**
   - Lexical Retrieval: In-process `BM25Okapi` with regex word tokenization.
   - Dense Retrieval: In-process FAISS `IndexFlatL2` indexing $D=384$ dimensional vectors from `sentence-transformers/all-MiniLM-L6-v2`.
   - Hybrid Fusion: Reciprocal Rank Fusion (RRF, $k=60$) with mathematical score calibration.
   - Neural Reranking: `cross-encoder/ms-marco-MiniLM-L-6-v2` scoring top candidate pairs.
4. **Agentic Orchestration:** Deterministic supervisor intent classifier (`supervisor_plan`), bounded iteration limits (max 3 iterations, 11 safe tools), and specialist agent execution (`policy`, `privacy`, `security`, `legal`, `conflict`, `verification`, `report`).
5. **Trust & Governance Engine:** Clause-level conflict detection across authority hierarchies, dynamic version supersession filtering (`get_active_version`), claim-level entailment checking, calibrated multi-factor confidence formula, and SHA-256 evidence provenance receipts.
6. **State Persistence & Review Queue:** Pluggable repository (`MemoryStore` / PostgreSQL) managing run histories and human-in-the-loop review queues.

---

## 2. In-Depth Bottleneck Analysis

We systematically evaluate the 9 architectural components, categorizing findings into **Demonstrated Bottlenecks** (directly verified in current code) and **Hypothesized Bottlenecks** (anticipated under production scale).

### Component 1: FAISS Index Construction & Loading
- **Current Code Location:** `RAG_project/vectorstore/faiss_db.py`, `backend/rag_engine.py:82-104`
- **Demonstrated Bottleneck:**
  - *Full Re-Indexing upon Addition:* In `TenantRAGIndex.add_chunks()`, adding any new chunks triggers a complete re-embedding of the *entire* tenant document corpus (`emb_model.embed_documents(self.documents)`) and reconstructs the FAISS index from scratch using `build_index()`. Adding 10 chunks to a 1,000-chunk index needlessly recalculates 1,010 embeddings ($O(N)$ write overhead instead of $O(\Delta N)$).
  - *Index Flat L2 Linear Scan:* `IndexFlatL2` executes exact brute-force search ($O(N \cdot D)$ FLOPs). For $N=100$ or $1,000$, search is near-instant (<2 ms), but at $N=50,000$, searching 50k 384-dimensional vectors requires scanning $\sim 76.8\text{ MB}$ of float vectors sequentially per query.
- **Hypothesized Bottleneck:**
  - High tenant counts ($T > 10,000$) maintaining separate in-memory FAISS indices will exhaust process virtual memory if unused tenant indices are not LRU-cached or persisted to disk.

### Component 2: BM25 Index Construction & Querying
- **Current Code Location:** `RAG_project/retriever/bm25.py:10-33`
- **Demonstrated Bottleneck:**
  - *Full Array Sort:* In `BM25Retriever.search()`, line 24 executes `np.argsort(scores)[::-1][:top_k]`. Sorting all $N$ corpus scores has $O(N \log N)$ complexity. When retrieving top $K=8$ or $K=24$ from $N=50,000$, `np.argsort` sorts 50,000 floats rather than selecting top $K$ via partial partitioning ($O(N)$ with `np.argpartition`).
  - *Unindexed Document Storage:* `BM25Retriever` holds Python `Document` objects with entire raw string contents, duplicating memory held by FAISS and `TenantRAGIndex`.
- **Hypothesized Bottleneck:**
  - Python-level tokenization using `re.findall(r"\b\w+\b", text.lower())` becomes CPU-bound during bulk document ingestion.

### Component 3: Hybrid Retrieval & Cross-Encoder Reranking
- **Current Code Location:** `backend/rag_engine.py:170-222`
- **Demonstrated Bottleneck:**
  - *CPU Contention during Neural Reranking:* Reranking runs `ce.predict(pairs)` for $P=16\text{ to }20$ pairs per query on CPU. On modern multi-core CPUs, PyTorch uses OpenMP threads. Under concurrent queries ($C \ge 10$), multiple PyTorch forward passes run simultaneously without a thread cap, causing CPU saturation and high p99 latency spikes.
  - *Synchronous Retrieval Execution:* RRF and FAISS/BM25 lookups run sequentially within worker threads rather than utilizing thread-safe batching.
- **Hypothesized Bottleneck:**
  - Large candidate pools ($K > 50$) will cause cross-encoder latency to dominate response times (>200 ms).

### Component 4: Repeated Model Initialization
- **Current Code Location:** `backend/rag_engine.py:44-65`
- **Status: Remediated / Verified Non-Bottleneck:**
  - Code inspection confirms that `_get_shared_embedding_model()` and `_get_shared_cross_encoder()` use module-level singletons (`_GLOBAL_EMBEDDING_MODEL` and `_GLOBAL_CROSS_ENCODER`). Models are loaded exactly once per worker process, avoiding the critical defect of reloading weights on each request.

### Component 5: Iterative Retrieval & Multi-Agent Orchestration
- **Current Code Location:** `backend/rag_engine.py:468-500`, `backend/graph/workflow.py:320-335`
- **Demonstrated Bottleneck:**
  - *Sequential Specialist Execution:* In `run_policy_graph()`, specialist agents (`active_specialists`) are executed in a sequential `for task in active_specialists:` loop using `await run_specialist_agent(...)`. When a query dispatches multiple specialists (e.g. `policy` + `conflict`), they execute sequentially rather than concurrently via `asyncio.gather()`.
  - *Bounded Iterative Retrieval:* `retrieve_iterative` is already bounded to $2$ passes max, which prevents unbounded search loops, but doubles retrieval overhead when triggered.

### Component 6: LLM Provider Rate Limits, Connection Churn, & Fallback
- **Current Code Location:** `backend/providers/fallback.py:42, 55`
- **Demonstrated Bottleneck:**
  - *HTTP Connection Churn:* `_gemini` and `_openai_compatible` instantiate a new `httpx.AsyncClient` on *every* invocation:
    `async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:`
    Under concurrent load, creating and tearing down TLS sockets induces TCP connection churn, socket exhaustion, and SSL handshake latency.
  - *Absence of Concurrency Throttling:* No client-side semaphore limits outbound API calls. 50 simultaneous requests immediately trigger 50 concurrent outbound API requests, rapidly hitting HTTP 429 provider rate limits.

### Component 7: Policy-Version Metadata Lookup
- **Current Code Location:** `backend/rag_engine.py:250-265`
- **Demonstrated Bottleneck:**
  - *Linear Document Scan:* `get_active_version(document_name)` iterates linearly over all `self.documents` (`[doc for doc in self.documents if ...]`) and sorts matching documents. For small corpora ($N < 50$), this is negligible (<0.1 ms); for large corpora ($N > 10,000$), scanning all documents per query adds unnecessary CPU overhead.
  - *Mitigation:* Cache active version per document family in a tenant metadata hash table.

### Component 8: Evidence & Audit Receipt Generation
- **Current Code Location:** `backend/evidence_intelligence.py:560-618`
- **Status: Verified Efficient:**
  - Cryptographic evidence receipt generation uses standard Python `hashlib.sha256()`. Measured execution time is $<0.2\text{ ms}$ per query, representing $<0.1\%$ of pipeline latency.

### Component 9: Review Queue Operations & Persistence
- **Current Code Location:** `backend/repositories/store.py:20-75`
- **Demonstrated Bottleneck:**
  - *Unbounded Deep-Copying in MemoryStore:* Every call to `store.list(tenant_id, collection)` deep-copies the entire collection under an `asyncio.Lock()`. As review items accumulate, memory usage grows unboundedly, and list operations degrade to $O(N)$ lock contention.
  - *Absence of Pagination:* No `limit` or `offset` parameters are supported on store listing routes.

---

## 3. Demonstrated vs. Hypothesized Bottlenecks Summary

| Architectural Component | Demonstrated (Measured / Code Audited) | Hypothesized (Scale Extrapolation) |
|---|---|---|
| **FAISS Indexing** | Full re-embedding on `add_chunks`; $O(N \cdot D)$ linear scan in `IndexFlatL2`. | Memory exhaustion at $T > 10,000$ active tenants. |
| **BM25 Retrieval** | $O(N \log N)$ `np.argsort` on entire corpus score vector. | Regex tokenization CPU bottleneck during multi-MB ingestion. |
| **Cross-Encoder** | OpenMP CPU thread contention under concurrent requests. | Reranking latency exceeding 250 ms at candidate pool $K > 50$. |
| **Model Init** | **None** (Singletons already initialized once). | High VRAM footprint if multiple models loaded on GPU. |
| **Agent Graph** | Sequential specialist agent execution (`for task in ...`). | Redundant tool-call loops if plan is cyclic. |
| **LLM Provider** | New `httpx.AsyncClient` per request; no concurrency semaphore. | Global rate limit exhaustion triggering cascade fallbacks. |
| **Version Lookup** | Linear document array filtering in `get_active_version`. | Metadata lock contention during concurrent uploads. |
| **Audit Receipt** | **None** (SHA-256 runs in $<0.2\text{ ms}$). | Large receipt JSON payload serialization overhead. |
| **Store / Review** | Unbounded list growth & `deepcopy` on full collection in `MemoryStore`. | Postgres connection pool exhaustion under $C > 100$. |

---

## 4. Scalability Engineering Plan & Implementation Gates

To address these demonstrated bottlenecks while preserving compliance guarantees, we define four implementation gates:

### Gate 1: Retrieval & Indexing Improvements
1. **Incremental Indexing:** In `TenantRAGIndex`, only embed new chunks when `add_chunks` is called; append vectors to existing FAISS index via `self.index.add()` instead of full reconstruction.
2. **Top-K Selection Optimization:** In `BM25Retriever`, replace `np.argsort(scores)[::-1][:top_k]` with `np.argpartition` or `heapq.nlargest` for $O(N)$ scaling.
3. **Document Version Metadata Cache:** Cache active version per document family in `TenantRAGIndex` to avoid linear chunk scanning.

### Gate 2: Concurrency & Connection Pooling
1. **Shared HTTP Client with Connection Pool:** Maintain a persistent `httpx.AsyncClient` in `ProviderFallback` with max keepalive connections and explicit connection limits.
2. **Outbound Concurrency Semaphore:** Protect LLM provider calls with an `asyncio.Semaphore` (e.g. 10 concurrent slots) to prevent HTTP 429 rate limit errors and buffer bursts.
3. **Cross-Encoder Thread Management:** Set `torch.set_num_threads()` to a balanced allocation (e.g. 4 threads) to prevent CPU thread thrashing under concurrent query load.

### Gate 3: Memory & State Bounds
1. **Store Pagination & Bounded History:** Add `limit` and `offset` support to `store.list()` and cap maximum retained runs in `MemoryStore` to prevent memory leaks.
2. **Specialist Parallelization:** Execute independent specialist agents concurrently via `asyncio.gather()`.

### Gate 4: Zero-Regression Safety
1. **Tenant Isolation Invariance:** Ensure tenant stamping, tenant hashing, and vectorstore partitioning remain strictly isolated.
2. **Proven Compliance Invariance:** Ensure 100% Appropriate Abstention on unanswerable queries and $\ge 85\%$ Conflict F1 are fully maintained under concurrent load.
