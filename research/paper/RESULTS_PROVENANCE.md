# DocuTrust Results Provenance: Complete Data-to-Paper Traceability Matrix

This document provides complete, line-by-line provenance for every empirical number, test statistic, benchmark count, and literature review figure reported in the DocuTrust research paper.

---

## 1. Systematic Literature Review & PRISMA Counts

| Metric / Count | Reported Value | Source File | Line / Key / Cell Reference | Evaluation / Script |
|---|---|---|---|---|
| Total Screening Records | 66 | `research/paper/LITERATURE_SCREENING.csv` | Header + 66 rows | `len(rows)` in `LITERATURE_SCREENING.csv` |
| ACL Anthology Records | 34 | `research/paper/LITERATURE_SCREENING.csv` | Column: `Source_Database` | `Source_Database == 'ACL Anthology'` |
| arXiv Records | 14 | `research/paper/LITERATURE_SCREENING.csv` | Column: `Source_Database` | `Source_Database == 'arXiv'` |
| ACM Digital Library | 9 | `research/paper/LITERATURE_SCREENING.csv` | Column: `Source_Database` | `Source_Database == 'ACM Digital Library'` |
| IEEE Xplore Records | 6 | `research/paper/LITERATURE_SCREENING.csv` | Column: `Source_Database` | `Source_Database == 'IEEE Xplore'` |
| Scopus / Semantic Scholar | 3 | `research/paper/LITERATURE_SCREENING.csv` | Column: `Source_Database` | `Source_Database in ['Scopus', 'Semantic Scholar']` |
| Title/Abstract Exclusions | 0 | `research/paper/LITERATURE_SCREENING.csv` | Column: `Title_Abstract_Screen` | All 66 pre-screened to meet entry criteria |
| Full-Text Assessed | 66 | `research/paper/LITERATURE_SCREENING.csv` | Column: `Full_Text_Screen` | All 66 reports retrieved |
| Full-Text Excluded | 10 | `research/paper/LITERATURE_SCREENING.csv` | Column: `Exclusion_Reason` | E1: 2, E2: 2, E3: 2, E4: 2, E5: 2 |
| Primary Included Studies | 56 | `research/paper/LITERATURE_SCREENING.csv` | Column: `Final_Status` | `Final_Status == 'Included'` |
| In-Depth Evidence Matrix | 27 | `research/paper/LITERATURE_EVIDENCE_MATRIX.csv` | Header + 27 rows | Extracted deep synthesis cohort |

---

## 2. Benchmark Pilot & Split Protocol

| Dimension | Count | Source File | Exact Key / Object Path |
|---|---|---|---|
| Total Benchmark Queries | 50 | `research/docutrust_bench_pilot.jsonl` | 50 JSONL objects |
| Development Set (Tuning) | 16 | `research/docutrust_bench_pilot.jsonl` | `item["policy_id"] == "03_Civilian_Work_From_Home_Policy.pdf"` |
| Frozen Test Set (Evaluation)| 34 | `research/docutrust_bench_pilot.jsonl` | `item["policy_id"] != "03_Civilian_Work_From_Home_Policy.pdf"` |
| Test Answerable Queries | 26 | `research/docutrust_bench_pilot.jsonl` | `item["ground_truth_answerable"] == True` |
| Test Unanswerable Queries | 8 | `research/docutrust_bench_pilot.jsonl` | `item["ground_truth_answerable"] == False` |
| Total Inference Trials | 408 | `research/results/raw_experiment_results.json` | 12 configurations $\times$ 34 test items |
| Security Domain Queries | 12 | `research/docutrust_bench_pilot.jsonl` | `item["domain"] == "security"` |
| Privacy Domain Queries | 11 | `research/docutrust_bench_pilot.jsonl` | `item["domain"] == "privacy"` |
| Finance Domain Queries | 11 | `research/docutrust_bench_pilot.jsonl` | `item["domain"] == "finance"` |

---

## 3. Retrieval Performance Metrics (Answerable Test Queries, N = 26)

| Configuration | Metric | Value | Source File | JSON Path |
|---|---|---|---|---|
| **BASE-A (BM25)** | Hit@1 | 76.9% | `research/results/independent_recomputed_metrics.json` | `['BASE-A']['retrieval']['hit_at_1']` |
| | MRR | 0.865 | `research/results/independent_recomputed_metrics.json` | `['BASE-A']['retrieval']['mrr']` |
| | nDCG@8 | 0.899 | `research/results/independent_recomputed_metrics.json` | `['BASE-A']['retrieval']['ndcg_at_8']` |
| **BASE-B (Dense FAISS)** | Hit@1 | 61.5% | `research/results/independent_recomputed_metrics.json` | `['BASE-B']['retrieval']['hit_at_1']` |
| | MRR | 0.779 | `research/results/independent_recomputed_metrics.json` | `['BASE-B']['retrieval']['mrr']` |
| | nDCG@8 | 0.835 | `research/results/independent_recomputed_metrics.json` | `['BASE-B']['retrieval']['ndcg_at_8']` |
| **BASE-C (Hybrid RRF)** | Hit@1 | 76.9% | `research/results/independent_recomputed_metrics.json` | `['BASE-C']['retrieval']['hit_at_1']` |
| | MRR | 0.860 | `research/results/independent_recomputed_metrics.json` | `['BASE-C']['retrieval']['mrr']` |
| | nDCG@8 | 0.895 | `research/results/independent_recomputed_metrics.json` | `['BASE-C']['retrieval']['ndcg_at_8']` |
| **BASE-D (+ Cross-Encoder)** | Hit@1 | 76.9% | `research/results/independent_recomputed_metrics.json` | `['BASE-D']['retrieval']['hit_at_1']` |
| | MRR | 0.878 | `research/results/independent_recomputed_metrics.json` | `['BASE-D']['retrieval']['mrr']` |
| | nDCG@8 | 0.910 | `research/results/independent_recomputed_metrics.json` | `['BASE-D']['retrieval']['ndcg_at_8']` |
| **SYS-FULL (DocuTrust)** | Hit@1 | 76.9% | `research/results/independent_recomputed_metrics.json` | `['SYS-FULL']['retrieval']['hit_at_1']` |
| | MRR | 0.878 | `research/results/independent_recomputed_metrics.json` | `['SYS-FULL']['retrieval']['mrr']` |
| | nDCG@8 | 0.910 | `research/results/independent_recomputed_metrics.json` | `['SYS-FULL']['retrieval']['ndcg_at_8']` |
| | MRR 95% Bootstrap CI | [0.782, 0.962] | `research/results/independent_recomputed_metrics.json` | `['statistical_audit']['sys_full_mrr_95_bootstrap_ci']` |
| | nDCG 95% Bootstrap CI | [0.839, 0.972] | `research/results/independent_recomputed_metrics.json` | `['statistical_audit']['sys_full_ndcg_95_bootstrap_ci']` |

---

## 4. Factuality, Governance & Decision Metrics (N = 34)

| Configuration | Metric | Value | Source File | JSON Path |
|---|---|---|---|---|
| **SYS-FULL** | Claim Support Rate | 91.7% (187/204) | `research/results/independent_recomputed_metrics.json` | `['SYS-FULL']['factuality']['claim_support_rate']` |
| | Conflict F1 | 85.7% (P=75.0, R=100) | `research/results/independent_recomputed_metrics.json` | `['SYS-FULL']['conflict_detection']['f1']` |
| | Safe Non-Answer Rate | 100.0% (8/8) | `research/results/independent_recomputed_metrics.json` | `['SYS-FULL']['governance_and_abstention']['appropriate_abstention_rate']` |
| | False Abstention Rate | 53.8% (14/26) | `research/results/independent_recomputed_metrics.json` | `['SYS-FULL']['governance_and_abstention']['false_abstention_rate']` |
| | Exact 3-Way Accuracy | 44.1% (15/34) | `research/results/independent_recomputed_metrics.json` | `['SYS-FULL']['governance_and_abstention']['decision_accuracy_3way_exact']` |
| | Binary Gov. Accuracy | 64.7% (22/34) | `research/results/independent_recomputed_metrics.json` | `['SYS-FULL']['governance_and_abstention']['binary_governance_accuracy']` |
| **ABL-1 (- Claim Ver.)** | Exact 3-Way Accuracy | 32.4% (11/34) | `research/results/independent_recomputed_metrics.json` | `['ABL-1']['governance_and_abstention']['decision_accuracy_3way_exact']` |
| | False Abstention Rate | 69.2% (18/26) | `research/results/independent_recomputed_metrics.json` | `['ABL-1']['governance_and_abstention']['false_abstention_rate']` |
| **ABL-2 (- Version Filter)** | Exact 3-Way Accuracy | 47.1% (16/34) | `research/results/independent_recomputed_metrics.json` | `['ABL-2']['governance_and_abstention']['decision_accuracy_3way_exact']` |
| **ABL-3 (- Conflict Det.)** | Conflict F1 | 0.0% (TP=0, FN=3) | `research/results/independent_recomputed_metrics.json` | `['ABL-3']['conflict_detection']['f1']` |
| **ABL-4 (- Sufficiency Gate)**| Exact 3-Way Accuracy | 41.2% (14/34) | `research/results/independent_recomputed_metrics.json` | `['ABL-4']['governance_and_abstention']['decision_accuracy_3way_exact']` |
| **ABL-5 (- Reranker)** | Exact 3-Way Accuracy | 64.7% (22/34) | `research/results/independent_recomputed_metrics.json` | `['ABL-5']['governance_and_abstention']['decision_accuracy_3way_exact']` |
| | Steady-State Median Latency | 17.1 ms | `research/results/independent_recomputed_metrics.json` | `['ABL-5']['latency']['median_ms']` |

---

## 5. Latency & Timing Provenance

| Configuration | Metric | Value | Source File | JSON Path | Audit Notes |
|---|---|---|---|---|---|
| **BASE-A (BM25)** | Arithmetic Mean | 1,847.4 ms | `research/results/independent_recomputed_metrics.json` | `['BASE-A']['latency']['mean_ms']` | Includes 40,223.6 ms cold-start on query #1 |
| | Median (Steady-State)| 0.5 ms | `research/results/independent_recomputed_metrics.json` | `['BASE-A']['latency']['median_ms']` | Pure inverted index lookup |
| | Minimum Latency | 0.4 ms | `research/results/independent_recomputed_metrics.json` | `['BASE-A']['latency']['min_ms']` | Query #14 |
| | Maximum Latency | 40,223.6 ms | `research/results/independent_recomputed_metrics.json` | `['BASE-A']['latency']['max_ms']` | Query #1 cold-start index build |
| **BASE-B (Dense)** | Median Latency | 15.1 ms | `research/results/independent_recomputed_metrics.json` | `['BASE-B']['latency']['median_ms']` | FAISS IndexFlatIP cosine similarity |
| **BASE-C (Hybrid RRF)**| Median Latency | 14.0 ms | `research/results/independent_recomputed_metrics.json` | `['BASE-C']['latency']['median_ms']` | BM25 + FAISS + RRF score merge |
| **BASE-D (+ Cross-Enc)**| Median Latency | 235.0 ms | `research/results/independent_recomputed_metrics.json` | `['BASE-D']['latency']['median_ms']` | Cross-encoder adds ~221 ms |
| **SYS-FULL** | Mean Latency | 237.8 ms | `research/results/independent_recomputed_metrics.json` | `['SYS-FULL']['latency']['mean_ms']` | Complete multi-agent pipeline |
| | Median Latency | 236.0 ms | `research/results/independent_recomputed_metrics.json` | `['SYS-FULL']['latency']['median_ms']` | Steady-state pipeline execution |
| | Min / Max Latency | 214.6 / 265.9 ms | `research/results/independent_recomputed_metrics.json` | `['SYS-FULL']['latency']['min_ms'/'max_ms']`| Tightly bounded variance |

---

## 6. Statistical Significance Tests

| Test | Contrast | Statistic | p-value | Significance ($\alpha = 0.05$) |
|---|---|---|---|---|
| Paired Student's t-test | MRR (SYS-FULL vs. BASE-A) | $t(25) = 1.383$ | $p = 0.1787$ | Not significant |
| Paired Student's t-test | nDCG@8 (SYS-FULL vs. BASE-A) | $t(25) = 1.377$ | $p = 0.1807$ | Not significant |
| McNemar's Test | Decision Acc (SYS-FULL vs. BASE-D)| 19 discordant pairs | $p = 0.3593$ | Not significant |
