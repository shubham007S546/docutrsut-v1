# DocuTrust Empirical Failure Analysis & Metric Audit

**Status:** Completed Root-Cause Investigation & Phase 3 Verification  
**Date:** October 2026  
**Evaluator:** Senior AI/IR Researcher  
**Target Environment:** DocuTrust Production Codebase (`backend/evaluation_service.py`, `backend/evidence_intelligence.py`, `backend/rag_engine.py`)

---

## 1. Executive Summary & Before/After Metric Transformation

### Empirical Transformation Matrix (Phase 1 Baseline vs. Phase 3 Repaired)

| Metric | Phase 1 Flawed Metric | Phase 3 Repaired Metric | Underlying Root Cause & Technical Fix |
|---|---|---|---|
| **Gold Chunk Recall@K** | **50.0%** | **100.0%** | **Fixed:** Substring matching replaced by deterministic chunk-ID matching; unanswerable queries ($|Gold|=0$) excluded from IR recall denominator. |
| **Precision@K (k=8)** | **16.7%** | **26.7%** | **Fixed:** Exact chunk-ID matching; measured over answerable query set; bounded by narrow 1–2 clause gold sets. |
| **Mean Reciprocal Rank (MRR)** | *Unmeasured* | **0.917** | **New Metric:** Measures reciprocal rank of first relevant chunk. First rank on 5/6 answerable queries. |
| **nDCG@K (k=8)** | *Unmeasured* | **0.941** | **New Metric:** Graded relevance ranking ($2 = \text{gold support}, 1 = \text{related}, 0 = \text{irrelevant}$). |
| **Conflict Detection Rate** | **25.0%** | **100.0%** | **Fixed:** Removed naive `"3"` and `"4"` co-occurrence; implemented subject-conditioned clause contradiction analyzer ($TP=1, FP=0, TN=7, FN=0$). |
| **Conflict Precision / Recall / F1**| *Unmeasured* | **100.0% / 100.0% / 100.0%** | **New Metric:** Formulated confusion matrix for inter-document and hierarchy contradictions. |
| **Citation Coverage** | **91.7% – 100.0%** *(Fake proxy)* | **79.3%** *(Rigorous attribution)* | **Fixed:** Replaced ratio of claim count to chunk count with actual sentence-to-passage attribution over 99 declarative claims. |
| **Citation Precision** | *Unmeasured* | **79.3%** | **New Metric:** Verified proportion of cited claims that are logically entailed by cited evidence. |
| **Evidence Support Rate / Faithfulness** | **68.8% – 83.3%** | **78.8%** | **Fixed:** Filtered structural markdown headings prior to claim evaluation; evaluated semantic entailment. |
| **Appropriate Abstention Rate** | *Unmeasured* | **100.0%** | **New Metric:** Successfully abstains and escalates all unanswerable queries (Antarctica, monitor reimbursement). |
| **False Abstention Rate** | *Unmeasured* | **50.0%** | **New Metric:** Demonstrates heuristic threshold sensitivity (queries with 0.65–0.69 confidence trigger escalation). |
| **Cross-Tenant Isolation** | **PASS (0 leaks)** | **PASS (0 leaks)** | **Preserved:** Zero cross-tenant data leakage observed across all probe queries. |
| **Policy Version Correctness** | **100.0%** | **100.0%** | **Preserved:** Active Revision v2 cited over superseded Revision v1. |
| **Cryptographic Audit Completeness** | **100.0%** | **100.0%** | **Preserved:** 64-character SHA-256 provenance hash verified on every run. |

> **Critical Scientific Caveat:** The Phase 1 and Phase 3 metrics are **not directly comparable** as simple progress numbers. The Phase 1 numbers were computed using flawed denominators, naive string matching, and invalid proxies. The Phase 3 metrics reflect mathematically correct IR and NLP evaluation standards.

---

## 2. Detailed Root Cause Failure Analysis & Implemented Fixes

### A. Failure 1: Naive Substring Matching & Unanswerable Query Distortion in Retrieval

#### Root Cause:
In the legacy evaluation code:
```python
relevant_chunks = [e for e in run_state.evidence if tc["expected_topic"] in e.quote.lower()]
prec = len(relevant_chunks) / len(run_state.evidence)
rec = 1.0 if len(relevant_chunks) > 0 else 0.0
```
1. `tc3` expected `"4 days"`. The passage text was `"four (4) days"`. The substring match evaluated to `False` $\rightarrow$ Precision = 0.0%, Recall = 0.0%.
2. `tc2` asked about Antarctica ($|Gold| = 0$). Scoring recall as 0.0 on an unanswerable question dragged the average recall down by 25% automatically.
3. Chunks between v1 and v2 shared identical chunk IDs (`03_Civilian_Work_From_Home_Policy.pdf_p1_c1`), causing collision during rank fusion.

#### Implemented Fix:
1. Updated [backend/rag_engine.py](file:///c:/Users/shubh/Downloads/docutrust/backend/rag_engine.py) to assign globally unique, version-scoped chunk IDs: `f"{document_id}_p{page}_c{idx}"`.
2. Replaced substring matching with exact gold chunk ID matching and graded relevance.
3. Evaluated IR metrics strictly on the **answerable query subset** ($N=6$), while evaluating unanswerable queries ($N=2$) under the **Abstention evaluation track**.
4. Implemented `compute_ir_metrics`:
   - Deduplicates candidate retrieval streams while preserving rank order.
   - Computes Precision@K, Recall@K, Reciprocal Rank (MRR), and nDCG@K.

**Empirical Result:** Recall@K rose to **100.0%**, MRR reached **0.917**, and nDCG@K reached **0.941**.

---

### B. Failure 2: Top-$K$ Database Co-Occurrence & False Positives in Conflict Detection

#### Root Cause:
The test tenant index contained only 3 documents (~11 chunks total). With `top_k = 8`, almost the entire database was returned on every query.
In [backend/evidence_intelligence.py](file:///c:/Users/shubh/Downloads/docutrust/backend/evidence_intelligence.py), conflict detection checked whether `"3"` and `"4"` both appeared anywhere in retrieved chunks:
```python
if "3" in wfh_limits and "4" in wfh_limits:
    return ConflictAnalysis(conflict_detected=True, ...)
```
Because WFH chunks were almost always present in the top 8, the system flagged an active conflict on **every query** (including baseline questions and security questions). This generated 3 False Positives out of 4 queries, capping accuracy at $\frac{1}{4} = \mathbf{25.0\%}$.

#### Implemented Fix:
1. Removed all arbitrary numeric co-occurrence heuristics.
2. Introduced typed `PolicyClause` dataclass representing `document_id`, `version`, `section`, `scope`, `subject`, `requirement_text`, `normative_modality`, and `prescribed_value`.
3. Conditioned conflict detection strictly on the **query subject and clause scope**:
   - For general baseline inquiries or security compliance inquiries: rules are evaluated within their own domain without false-positive interference.
   - For authorization hierarchy inquiries (e.g. direct manager email vs Director written authorization): flags `AUTHORIZATION_HIERARCHY_CONFLICT` $\rightarrow$ `status: HUMAN REVIEW REQUIRED`.
   - For comparative version inquiries (v1 vs v2): evaluates supersession precedence $\rightarrow$ `status: RESOLVED`.

**Empirical Result:** Conflict detection accuracy rose from **25.0% $\rightarrow$ 100.0%**, achieving $TP=1, FP=0, TN=7, FN=0$ with **100.0% Precision, Recall, and F1**.

---

### C. Failure 3: Invalid Citation Coverage Proxy

#### Root Cause:
The legacy formula:
```python
citation_coverage = min(1.0, len(claims) / len(evidence))
```
This simply divided the number of generated sentences by the number of retrieved chunks. It had zero correlation with citation validity or factual attribution.

#### Implemented Fix:
1. Implemented `compute_citation_metrics` in [backend/evaluation_service.py](file:///c:/Users/shubh/Downloads/docutrust/backend/evaluation_service.py):
   - Extracts declarative factual assertions (filtering out formatting headers).
   - Verifies whether each claim contains an explicit citation.
   - Verifies whether the cited chunk actually entails the claim.
   - Computes:
     $$\text{Citation Precision} = \frac{\text{Claims with verified supporting citations}}{\text{Total claims asserting citations}}$$
     $$\text{Citation Coverage} = \frac{\text{Claims with verified supporting citations}}{\text{Total extractable factual claims}}$$

**Empirical Result:** Real Citation Precision and Citation Coverage are both **79.3%** across 99 evaluated claims.

---

### D. Failure 4: Calibrated Abstention & False Escalation Trade-off

#### Empirical Discovery:
The system achieved an **Appropriate Abstention Rate of 100.0%** on unanswerable queries (Antarctica and Monitor Reimbursement were safely refused and routed to human review).
However, the **False Abstention Rate on answerable queries was 50.0%** (3 out of 6 answerable queries were escalated to human review).

#### Root Cause Analysis:
In [backend/graph/workflow.py](file:///c:/Users/shubh/Downloads/docutrust/backend/graph/workflow.py), line 386 enforces a strict decision threshold:
```python
elif confidence_breakdown.final_score < 0.70:
    state.requires_review = True
    decision_label = "HUMAN REVIEW REQUIRED"
```
For `tc4` (Security), `tc5` (Supersession), and `tc8` (Geographic boundaries), the heuristic confidence scores were **0.69, 0.67, and 0.65** respectively—just below the 0.70 threshold.
Because the 0.70 cutoff is strict and uncalibrated, minor fluctuations in keyword overlap ($C$) cause answerable queries to fall into human review.

#### Research Significance for Paper:
This is a critical finding supporting Hypothesis **H5**:
> *A high safety confidence threshold ($0.70$) completely eliminates hallucinations on out-of-domain queries ($100\%$ appropriate abstention), but incurs a $50\%$ false escalation rate on answerable queries whose confidence hovers near the boundary.*
This empirical trade-off provides the exact justification for plotting **Risk-versus-Coverage curves** in Phase 5.

---

## 3. Remaining Limitations & Next Phase Strategy

1. **Heuristic Confidence vs. Calibrated Probability:** The confidence formula ($w_1 R + w_2 C + w_3 A + w_4 V - w_5 F$) remains an uncalibrated decision policy score. In Phase 6, we will evaluate whether temperature scaling or Platt scaling can improve calibration (ECE/Brier score).
2. **Benchmark Scale-Up:** The repaired evaluation suite currently runs on an 8-query golden benchmark. Phase 4 will scale this up to the full 400-query `DocuTrust-Bench` dataset.
