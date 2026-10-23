# DocuTrust: Implementation and Research-Readiness Roadmap

This roadmap organizes the required platform upgrades in order of dependency, risk, value, and implementation effort.

---

## Priority & Dependency Matrix

| Stage | Focus Area | Dependencies | Risk | Value | Effort | Status |
|---|---|---|---|---|---|---|
| **Phase 2** | Robust Document Ingestion & Page-Level Provenance | `fitz`, `pdfplumber`, `python-docx` | Medium | Critical | Moderate | **Ready to Implement** |
| **Phase 3** | Retrieval Engine Enhancements (Configurable Models, Reranker Activation, Traceability) | Phase 2 chunks & metadata | Low | High | Moderate | **Ready to Implement** |
| **Phase 4** | Grounded Answer Generation & Prompt Injection Defense | Phase 3 retrieval trace | Low | High | Low-Mod | **Ready to Implement** |
| **Phase 5** | Citation & Claim Verification Pipeline | Phase 2 (page numbers), Phase 4 | Medium | Critical | Moderate | **Ready to Implement** |
| **Phase 6** | Generalized Uncertainty, Sufficiency & Abstention | Phase 3 retrieval scores | Low | High | Low-Mod | **Ready to Implement** |
| **Phase 7** | Enterprise Security, Document ACLs & Safe Cleanup | RequestContext, Store | Medium | High | Moderate | **Ready to Implement** |
| **Phase 8** | Multi-Baseline Evaluation Framework & Benchmark Runner | Phases 3, 5, 6 | Low | Critical | High | **Ready to Implement** |
| **Phase 9** | Visualization & Research Dashboard | Phase 8 empirical results | Low | High | Moderate | **Ready to Implement** |
| **Phase 10**| Comprehensive Test Suite Expansion | All previous phases | Low | Critical | Moderate | **Ready to Implement** |
| **Phase 11**| Research Documentation & Scientific Artifacts | Phase 8 & 10 verification | None | Critical | Moderate | **Ready to Implement** |

---

## Detailed Execution Steps

### Stage 1: Document Ingestion & Page Preservation (Phase 2)
1. **Multi-Format Ingestion**: Wire `python-docx` for `.docx` and add support for `.txt`, `.md`, `.json` with clean structure extraction.
2. **Page Number Extraction**: Extract text page-by-page from PDFs using PyMuPDF (`fitz`), preserving `page_number` for each chunk.
3. **Structured Ingestion & Deduplication**: Compute document sha256, sanitize filenames, prevent duplicate indexing, and provide clean re-indexing.
4. **OCR Fallback Architecture**: Provide an OCR interface / graceful fallback for scanned PDFs or images.
5. **Durable Store Indexing**: Ensure `PostgresStore.ingest_document` indexes into `rag_engine` just as `MemoryStore` does.

### Stage 2: Retrieval Upgrades & Traceability (Phase 3)
1. **Configurable Dense Embeddings**: Allow configurable embedding model name and assert query/document dimension matching.
2. **Configurable Fusion & RRF**: Make RRF parameter $k$ and fusion strategy configurable via settings.
3. **Active Cross-Encoder Reranking**: Enable reranker in `workflow.py` with configurable top candidates pool and graceful fallback on OOM or error.
4. **Retrieval Traceability**: Record diagnostic metadata (retrieval method, candidate chunk IDs, raw BM25, FAISS, RRF, and cross-encoder scores, retrieval latency) on each query run.

### Stage 3: Answer Generation, Grounding & Injection Defense (Phase 4)
1. **Prompt Injection Boundary**: Delimit untrusted document evidence using XML-style tags (`<untrusted_evidence>...</untrusted_evidence>`) with strict instructions preventing instruction override.
2. **Generalized Synthesis**: Expand deterministic synthesis beyond hardcoded demo queries so arbitrary evidence generates structured, grounded answers when LLMs are unavailable.
3. **Multi-Document Synthesis**: Explicitly compare multiple documents and versions when relevant.

### Stage 4: Citation & Claim Verification (Phase 5)
1. **Deterministic Citation Resolution**: Validate that inline citations (e.g. `[Document | Section | Page]`) resolve to real retrieved chunks.
2. **Page Number Display**: Include real page numbers in citations and claim attribution.
3. **Semantic Claim-Evidence Verification**: Check whether claims are SUPPORTED, PARTIALLY_SUPPORTED, CONTRADICTED, or NOT_SUPPORTED.

### Stage 5: Generalized Uncertainty & Abstention (Phase 6)
1. **Configurable Sufficiency Thresholds**: Replace hardcoded keyword matching with generalized thresholds: coverage, relevance, and semantic overlap.
2. **Taxonomy of Abstention**: Distinguish missing evidence from conflicting evidence from ambiguous scope.

### Stage 6: Security, Access Control & Index Cleanup (Phase 7)
1. **Document-Level Permissions (ACL)**: Support role/department filtering during retrieval.
2. **Safe Deletion & Index Eviction**: Provide safe document deletion from FAISS, BM25, and database.
3. **Input Validation & Safe Error Handling**: Prevent credential or stack trace leakage.

### Stage 7: Evaluation Suite, Visualizations & Research Artifacts (Phases 8, 9, 10, 11)
1. **Evaluation Framework**: Run and compare the 5 baselines:
   - BM25
   - Dense FAISS
   - Hybrid (BM25 + FAISS via RRF)
   - Hybrid + Cross-Encoder Reranker
   - With vs. Without Citation Verification
2. **Empirical Metrics**: Calculate Recall@k, Precision@k, MRR, nDCG@k, claim support rate, correct abstention rate, operational latencies.
3. **Visualizations**: Generate empirical research plots and update frontend explainability.
4. **Documentation**: Author all required docs (`ARCHITECTURE.md`, `RETRIEVAL_DESIGN.md`, `SECURITY_AND_LIMITATIONS.md`, `EVALUATION_METHODOLOGY.md`, `EXPERIMENT_RESULTS.md`, `RESEARCH_GAPS.md`, `KNOWN_LIMITATIONS.md`, and updated `README.md`).
