# DocuTrust Research-Grade Upgrade Plan: Methodology, Evaluation, and Contributions

**Author:** Senior AI Researcher (IR / NLP / Trustworthy AI)  
**System:** DocuTrust (Evidence-Grounded Agentic Multi-Agent RAG for Compliance QA)  
**Document Status:** Formal Research Plan (Phase 1 & Phase 2 Deliverable)  
**Target Venues:** ACL / EMNLP / CIKM / SIGIR / AAAI (Applied / Human-Centered AI Track)

---

## 1. System Audit & Baseline Architecture Status

### A. Component Implementation Matrix

| Architecture Component | Current Code Location | Operational Status | Technical Audit Notes |
|---|---|---|---|
| **Multi-Tenant Isolation** | `backend/security/tenant.py`, `app/api/query/stream/route.ts` | **Fully Functional** | Cryptographic HMAC SHA-256 BFF assertion; tenant hashing; zero cross-tenant leakage verified in integration probe tests. |
| **Hybrid Retrieval (Dense + Sparse)** | `backend/rag_engine.py`, `RAG_project/vectorstore/faiss_db.py`, `RAG_project/retriever/bm25.py` | **Fully Functional** | In-process FAISS dense (`all-MiniLM-L6-v2`) + BM25 combined via Reciprocal Rank Fusion ($k=60$). |
| **Supervisor Planner** | `backend/graph/workflow.py` (`supervisor_plan`), `backend/agents/contracts.py` | **Fully Functional** | Deterministic intent classification using keyword and regex routing; guarantees bounded execution (max 3 iterations, 11 safe tools). |
| **Specialist Agents (7)** | `backend/graph/workflow.py` (`run_specialist_agent`), `backend/agents/contracts.py` | **Functional (LLM + Deterministic Fallback)** | Groq / Gemini / OpenAI gateway integration with deterministic fallback template for offline reproducibility. |
| **Claim-Level Verification** | `backend/evidence_intelligence.py` (`verify_claims_against_evidence`) | **Partially Implemented (Heuristic)** | Sentence extraction with bag-of-words token overlap threshold. Lacks formal Natural Language Inference (NLI) or LLM entailment verification. |
| **Evidence Sufficiency & Abstention** | `backend/evidence_intelligence.py` (`assess_evidence_sufficiency`) | **Partially Implemented (Heuristic)** | Query-passage keyword overlap with hardcoded pattern checks (e.g. Antarctica). Needs semantic thresholding and calibrated abstention. |
| **Conflict Analysis & Precedence** | `backend/evidence_intelligence.py` (`detect_policy_conflicts`) | **Partially Implemented (Heuristic)** | Rule/numerical co-occurrence matching across retrieved chunks; susceptible to false positives in small corpora. |
| **Heuristic Confidence Formula** | `backend/evidence_intelligence.py` (`calculate_evidence_confidence`) | **Fully Functional (Heuristic)** | Linear weighted formula ($w_1 R + w_2 C + w_3 A + w_4 V - w_5 F$). Uncalibrated score; cannot be claimed as a Bayesian probability. |
| **Cryptographic Evidence Receipt** | `backend/evidence_intelligence.py` (`generate_evidence_receipt`) | **Fully Functional** | SHA-256 provenance hash linking receipt ID, query, final score, documents, versions, and sections. |
| **Policy Change Impact Diff** | `backend/policy_impact.py` | **Fully Functional** | Structured diff between policy versions (v1 vs v2) computing impacted organizational departments and allowances. |
| **Human Review Queue** | `backend/main.py`, `app/api/review/route.ts` | **Fully Functional** | State machine persisting flagged queries into review collection with triage actions (Approve, Reject, Request More Evidence). |
| **Evaluation Suite** | `backend/evaluation_service.py`, `app/api/evaluations/route.ts` | **Critical Deficiencies (Phase 1 Finding)** | $N=4$ sample size; string-matching precision/recall; invalid citation coverage formula; penalizes unanswerable questions. |

---

## 2. Research Question & Measurable Hypotheses

### Primary Research Question
> *"Can combining hybrid retrieval, policy-version awareness, cross-document conflict detection, claim-level evidence verification, and evidence-based abstention improve the reliability, factual grounding, and auditability of document-grounded compliance question answering compared to conventional RAG and agentic baselines?"*

### Hypotheses to Test Experimentally
- **H1 (Retrieval Superiority):** Hybrid retrieval (BM25 + FAISS with RRF) achieves higher evidence recall and MRR than either dense-only or lexical-only retrieval on multi-clause compliance documents.
- **H2 (Factuality via Claim Verification):** Claim-level verification significantly reduces unsupported claims and hallucinations ($p < 0.01$) compared to unverified single-pass RAG generation.
- **H3 (Temporal & Version Precision):** Policy-version-aware retrieval and supersession logic eliminates outdated clause citations and supersession errors ($>95\%$ accuracy) when answering queries on evolving document corpora.
- **H4 (Contradiction Disclosure):** Multi-document conflict detection achieves higher F1 on identifying and localizing mutually contradictory policy requirements than standard baseline prompts.
- **H5 (Safe Abstention & Coverage):** Evidence sufficiency checks and confidence-based abstention significantly reduce unsupported answers on unanswerable/out-of-scope questions while maintaining high answer coverage ($>85\%$) on valid queries.
- **H6 (Overhead Trade-off):** The multi-stage verification, conflict analysis, and governance pipeline introduces measurable latency and token overhead, which can be quantified in risk-versus-latency trade-off curves.

---

## 3. Evaluation Dataset Architecture: DocuTrust-Bench ($N=400$)

To replace the flawed $N=4$ evaluation, we design **DocuTrust-Bench**, a reproducible benchmark of 400 annotated queries across 10 distinct compliance categories.

### Category Distribution
| Category ID | Category Name | Target Size | Primary Purpose | Key Ground Truth Labels |
|---|---|---|---|---|
| `CAT-01` | Direct Fact Retrieval | 50 | Tests single-clause factual extraction | Target Chunk ID, Exact Answer |
| `CAT-02` | Multi-Hop Policy Reasoning | 50 | Tests cross-section synthesis | Multiple Gold Chunk IDs |
| `CAT-03` | Policy Version Changes & Supersession | 50 | Tests temporal v1 vs v2 precedence | Gold Active Version, Superseded Version |
| `CAT-04` | Cross-Document Contradictions | 50 | Tests detection of contradictory clauses | Conflicting Chunk Pairs, Precedence Rule |
| `CAT-05` | Out-of-Domain / Insufficient Evidence | 50 | Tests safe abstention on absent policies | Expected Decision: `ABSTAIN` |
| `CAT-06` | Boundary / Ambiguous Authority Cases | 40 | Tests human review escalation trigger | Expected Decision: `ESCALATE_REVIEW` |
| `CAT-07` | Embedded Prompt Injections | 30 | Tests robustness against adversarial documents | Attack Neutralization: PASS/FAIL |
| `CAT-08` | Cross-Tenant Authorization Probes | 30 | Tests tenant-scoped data isolation | Leak Count: 0 |
| `CAT-09` | Granular Citation Attribution | 50 | Tests sentence-to-citation entailment | Claim-to-Chunk Mapping, Support Level |
| **Total** | **Comprehensive Benchmark** | **400** | Balanced, reproducible evaluation | Machine-readable JSONL format |

### Benchmark Schema (`research/benchmark_schema.json`)
```json
{
  "id": "DT-BENCH-001",
  "category": "version_supersession",
  "query": "What is the maximum remote work allowance for data engineers under the active policy?",
  "tenant_id": "tenant-compliance-eval",
  "relevant_doc_ids": ["03_Civilian_Work_From_Home_Policy.pdf"],
  "active_version": "v2",
  "superseded_version": "v1",
  "gold_chunk_ids": ["chunk-wfh-v2-sec4.2"],
  "conflict_present": true,
  "expected_decision": "ANSWER",
  "expected_answer_keywords": ["four days", "4 days", "technology division", "v2 supersedes v1"],
  "expected_claims": [
    {
      "claim": "Technology Division staff may work remotely up to 4 days per week.",
      "supporting_chunk_id": "chunk-wfh-v2-sec4.2",
      "required": true
    }
  ],
  "escalation_required": false,
  "notes": "v1 allowed 3 days; v2 Section 4.2 grants 4 days to technology staff and supersedes v1."
}
```

---

## 4. Experimental Baselines

To rigorously establish empirical superiority, all configurations will run against identical queries, the same document corpus, and the same underlying generation engine:

1. **Baseline A (BM25-Only RAG):** Lexical BM25 search ($k=8$) + standard generation prompt.
2. **Baseline B (Dense-Only RAG):** FAISS dense embedding search (`all-MiniLM-L6-v2`, $k=8$) + standard generation prompt.
3. **Baseline C (Standard Hybrid RAG):** FAISS + BM25 combined via Reciprocal Rank Fusion ($k=60$, top 8) + standard generation prompt without post-processing.
4. **Baseline D (Hybrid RAG + Cross-Encoder Reranker):** Hybrid retrieval followed by `cross-encoder/ms-marco-MiniLM-L-6-v2` reranking top 8 from top 20 candidates.
5. **Baseline E (Hybrid RAG + Claim Verification):** Baseline C with sentence-level claim decomposition and entailment verification, filtering unsupported assertions.
6. **System F (Full DocuTrust Pipeline):** Hybrid retrieval + Cross-Encoder + Policy-Version Precedence Filter + Pairwise Conflict Detection + Claim Verification + Calibrated Abstention + SHA-256 Audit Provenance.
7. **System G (Self-RAG Reference Comparison):** Formal literature comparison and, if compute/weights permit, an evaluation against Self-RAG reflection tokens `[Retrieve]`, `[IsRel]`, `[IsSup]`, `[IsUse]`.

---

## 5. Metrics Specification

### A. Retrieval Quality (Information Retrieval)
- **Gold-Chunk Precision@K:** Proportion of retrieved chunks that belong to the annotated gold chunk set:
  $$\text{P@K} = \frac{|\text{Retrieved}_K \cap \text{Gold}|}{K}$$
- **Gold-Chunk Recall@K:** Proportion of gold chunks retrieved in top-$K$:
  $$\text{R@K} = \frac{|\text{Retrieved}_K \cap \text{Gold}|}{|\text{Gold}|}$$
- **Mean Reciprocal Rank (MRR):** Reciprocal rank of the first relevant chunk:
  $$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$
- **nDCG@K:** Normalized Discounted Cumulative Gain over graded relevance (0 = irrelevant, 1 = related, 2 = definitive gold support).

### B. Answer Factuality & Citation Attribution
- **Claim Support Rate:** Percentage of extracted factual claims evaluated as logically entailed by cited evidence:
  $$\text{Support Rate} = \frac{N_{\text{supported claims}}}{N_{\text{total claims}}}$$
- **Hallucination / Unsupported Claim Rate:** Percentage of extracted claims classified as ungrounded or contradicted:
  $$\text{Unsupported Rate} = \frac{N_{\text{unsupported claims}}}{N_{\text{total claims}}}$$
- **Citation Precision:** Proportion of inline citations that entail the accompanying claim.
- **Citation Recall / Coverage:** Proportion of factual claims that have at least one valid supporting citation.

### C. Version Precedence & Conflict Handling
- **Superseded Policy Leakage Rate:** Percentage of responses citing or asserting an outdated/superseded clause as current fact.
- **Conflict Detection F1:** Harmonic mean of precision and recall in flagging contradictory rules across documents.
- **Conflict Localization Accuracy:** Proportion of detected conflicts that correctly identify the conflicting clauses.

### D. Abstention & Trust
- **Appropriate Abstention Rate:** Precision and recall in abstaining on unanswerable/out-of-domain questions (`CAT-05`).
- **False Abstention Rate:** Rate of incorrect refusal on validly answerable queries (`CAT-01` through `CAT-04`).
- **Risk-Coverage Curve:** Empirical accuracy plotted against varying decision confidence thresholds.

### E. System Efficiency & Overhead
- End-to-end latency: Mean, median, and 95th percentile (ms).
- Breakdown: Retrieval latency vs. agent planning vs. generation vs. claim verification.
- Token consumption and compute cost per query.

---

## 6. Ablation Study Plan

We isolate individual components by disabling one mechanism at a time on the 400-query benchmark:

1. **Ablation 1 (- Claim Verification):** Run full system without claim verification; assess impact on hallucination rate and latency.
2. **Ablation 2 (- Policy-Version Awareness):** Disable version filtering and supersession rules; measure superseded-clause usage rate.
3. **Ablation 3 (- Conflict Analysis):** Disable pairwise conflict detector; measure missed contradiction rate.
4. **Ablation 4 (- Evidence-Based Abstention):** Force system to attempt answering all queries; measure hallucination rate on unanswerable queries.
5. **Ablation 5 (- Reranking):** Remove Cross-Encoder reranker; measure drop in Precision@K and MRR.
6. **Ablation 6 (Dense-Only Retrieval):** Replace hybrid RRF with FAISS-only dense retrieval.
7. **Ablation 7 (BM25-Only Retrieval):** Replace hybrid RRF with BM25-only lexical retrieval.
8. **Ablation 8 (Single-Pass RAG Baseline):** Strip all multi-agent stages; perform standard retrieve-and-generate pass.

---

## 7. Academic Novelty, Gaps, and Risks

### Novelty Differentiation Matrix
| System / Paradigm | Adaptive Reflection | Claim Entailment Check | Policy Version Awareness | Cross-Doc Conflict Precedence | Calibrated Abstention | Tamper-Evident Provenance |
|---|---|---|---|---|---|---|
| **Standard RAG (Lewis et al.)** | ❌ None | ❌ None | ❌ None | ❌ None | ❌ None | ❌ None |
| **Self-RAG (Asai et al.)** | ✅ Token-level | ❌ Token heuristic | ❌ None | ❌ None | ⚠️ Partial (Threshold) | ❌ None |
| **CRAG (Yan et al.)** | ⚠️ Web search | ❌ None | ❌ None | ❌ None | ❌ None | ❌ None |
| **DocuTrust (Ours)** | ✅ Multi-Agent Supervisor | ✅ Clause Entailment | ✅ Version & Supersession | ✅ Hierarchy & Precedence | ✅ Sufficiency-Based Gate | ✅ SHA-256 Provenance Receipt |

### Scientific Novelty Risks & Mitigations
- **Risk 1: "Just system engineering / prompt chaining without novelty."**  
  *Mitigation:* Formulate the contribution not as arbitrary plumbing, but as a formal **Evidence Governance Framework** with measurable Pareto frontier improvements in the **Factuality-vs-Abstention-vs-Latency Trade-off**.
- **Risk 2: "Heuristic confidence is uncalibrated."**  
  *Mitigation:* Explicitly state that the multi-factor equation is a decision policy rule, evaluate its empirical Brier score / ECE, and plot the empirical Risk-Coverage trade-off curve.
- **Risk 3: "Unfair comparison with Self-RAG."**  
  *Mitigation:* Do not claim superiority over Self-RAG without running a fair identical-corpus baseline or properly qualifying architectural trade-offs.

---

## 8. Compute Requirements & Execution Budget

- **Local GPU/CPU Inference:**
  - Embedding (`all-MiniLM-L6-v2`): ~15 ms / query (CPU/GPU local, zero external cost).
  - Cross-Encoder Reranker (`ms-marco-MiniLM-L-6-v2`): ~30 ms / query (local PyTorch, zero external cost).
- **LLM Generation:**
  - Fast Inference via configured Groq API (`openai/gpt-oss-120b` or Llama 3) / Google Gemini:
  - 400 test cases $\times$ 4 baselines $\approx$ 1,600 inferences.
  - Estimated token consumption: ~1.2M tokens total.
  - Compute cost: Low (< $2.00 or within free tiers).
  - Zero expensive multi-GPU cluster training required for Phase 1–5 experiments.

---

## 9. Phased Execution Roadmap

- **Phase 1 (Complete):** Repository and evaluation audit; failure analysis of weak metrics; exact replication of reported numbers.
- **Phase 2 (Current):** Research upgrade plan; benchmark schema; baselines and ablation design.
- **Phase 3:** Fix evaluation scripts, implement robust IR metrics, fix conflict detector false positives, and upgrade claim verification.
- **Phase 4:** Build the 400-query benchmark dataset (`research/benchmark_dataset.jsonl`) and reproducible experiment runner.
- **Phase 5:** Run full baseline matrix (Baselines A–F) and all 8 ablations; generate raw result tables.
- **Phase 6:** Analyze empirical findings, statistical significance ($p$-values, confidence intervals), and assess whether model fine-tuning is justified.
- **Phase 7:** Produce publication-ready artifacts: LaTeX tables, figures, reproducibility package, and formal research paper manuscript.
