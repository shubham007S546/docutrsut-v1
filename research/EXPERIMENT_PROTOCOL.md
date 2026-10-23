# DocuTrust Experiment Runner & Evaluation Protocol

**Standard Protocol for Reproducible Baseline Execution and Ablation Analysis**

---

## 1. Experimental Conditions & Control Variables

To ensure scientific comparability, all experimental runs must adhere to strict controls:

1. **Identical Document Corpus:**
   - Every system operates on the exact same indexed policy chunks (chunk size: 500 characters, overlap: 80 characters, tokenized identically).
2. **Identical Generation Model:**
   - Same foundation model (Groq `openai/gpt-oss-120b` or Gemini `gemini-2.5-flash`), temperature ($T = 0.0$ for deterministic greedy decoding, or $T = 0.1$ with fixed random seeds for repeated stochastic runs).
3. **Context Window Budget:**
   - In all baselines, retrieved context is capped at $K=8$ chunks (maximum 4,000 characters).
4. **Hardware Environment Logging:**
   - System CPU, GPU, memory, OS version, and library versions are logged into `research/experiment_manifest.json`.

---

## 2. Baseline Matrix Specification

| System Code | System Name | Retrieval Mechanism | Reranking | Verification | Governance / Abstention |
|---|---|---|---|---|---|
| **`BASE-A`** | BM25-Only | BM25 (Okapi) | None | None | None (Generates answer always) |
| **`BASE-B`** | Dense-Only | FAISS (`all-MiniLM-L6-v2`) | None | None | None |
| **`BASE-C`** | Hybrid RRF | FAISS + BM25 ($k=60$) | None | None | None |
| **`BASE-D`** | Hybrid + Reranker | FAISS + BM25 ($k=60$, top 20) | Cross-Encoder (`ms-marco`) | None | None |
| **`BASE-E`** | Hybrid + Verifier | FAISS + BM25 | None | Claim-level NLI | Simple refusal if ungrounded |
| **`SYS-FULL`** | Full DocuTrust | FAISS + BM25 + Version Aware | Cross-Encoder | Claim-level NLI | Sufficiency Gate + Conflict Detector + Heuristic Confidence + Provenance Receipt |

---

## 3. Statistical Testing and Credibility Standards

1. **Bootstrap Confidence Intervals:**
   - For all reported metrics (Precision@K, Recall@K, Support Rate, Conflict F1), compute 95% bootstrap confidence intervals ($B = 10,000$ iterations).
2. **Paired Significance Testing:**
   - For paired baseline comparisons (e.g., `BASE-C` vs. `SYS-FULL`):
     - McNemar's test for binary outcome metrics (Decision Accuracy, Conflict Detection, Appropriate Abstention).
     - Paired Student's $t$-test or Wilcoxon signed-rank test for continuous metrics (F1, MRR, nDCG@K).
3. **Reporting Effect Sizes:**
   - Report Cohen's $d$ or Cliff's delta in addition to $p$-values. Do not rely exclusively on $p < 0.05$.
4. **Reproducibility Manifest:**
   - Save git commit hash, configuration parameters, prompt templates, raw generation outputs, and calculated metrics for every experiment run.
