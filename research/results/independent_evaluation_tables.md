# DocuTrust Phase 4: Independent Audited Evaluation Tables

**Evaluation Split:** Frozen Test Set ($N=34$ total queries; $N=26$ answerable, $N=8$ unanswerable)

**Ground Truth Document Families:** `01_Security_Safeguards_Policy.pdf`, `02_Privacy_and_Data_Protection_Standard.pdf`, `04_Finance_and_Expense_Reimbursement_Code.pdf` (Zero overlap with Dev set)


## Table 1: Audited Baseline Comparison (Frozen Test Set, N=34)

> **Note on Retrieval Denominators:** Precision@8 and Recall@8 are evaluated strictly over answerable queries ($N=26$). Because each benchmark item contains exactly one gold passage ($|Gold|=1$) and $K=8$, the theoretical maximum Precision@8 is $1/8 = 12.5\%$. Hit@1 (Success at Rank 1) is included to provide an unconstrained precision indicator.

> **Note on Claim Support:** Baselines where claim verification was not executed (BASE-A..D) had 0 claims extracted and are marked `N/A (0 Claims)` to avoid false 100% reporting from division by zero.


| System Configuration | Precision@8 (Max 12.5%) | Recall@8 | Hit@1 | MRR | nDCG@8 | Claim Support Rate | Conflict F1 (TP/FN) | App. Abstain (N=8) | False Abstain (N=26) | 3-Way Decision Acc (N=34) | Mean Latency (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **BASE-A** | 12.5% | 100.0% | 76.9% | 0.865 | 0.899 | N/A (0 Claims) | 0.0% (0/3) | 0.0% (0/8) | 0.0% (0/26) | 58.8% (20/34) | 1847.4 |
| **BASE-B** | 12.5% | 100.0% | 61.5% | 0.779 | 0.835 | N/A (0 Claims) | 0.0% (0/3) | 0.0% (0/8) | 0.0% (0/26) | 58.8% (20/34) | 17.3 |
| **BASE-C** | 12.5% | 100.0% | 76.9% | 0.86 | 0.895 | N/A (0 Claims) | 0.0% (0/3) | 0.0% (0/8) | 0.0% (0/26) | 58.8% (20/34) | 14.2 |
| **BASE-D** | 12.5% | 100.0% | 76.9% | 0.878 | 0.91 | N/A (0 Claims) | 0.0% (0/3) | 0.0% (0/8) | 0.0% (0/26) | 58.8% (20/34) | 333.4 |
| **BASE-E** | 12.5% | 100.0% | 76.9% | 0.86 | 0.895 | 91.1% (226/248) | 0.0% (0/3) | 87.5% (7/8) | 11.5% (3/26) | 58.8% (20/34) | 16.7 |
| **ITER-RETRIEVE** | 12.5% | 100.0% | 76.9% | 0.878 | 0.91 | 91.7% (187/204) | 85.7% (3/0) | 100.0% (8/8) | 53.8% (14/26) | 44.1% (15/34) | 473.3 |
| **SYS-FULL** | 12.5% | 100.0% | 76.9% | 0.878 | 0.91 | 91.7% (187/204) | 85.7% (3/0) | 100.0% (8/8) | 53.8% (14/26) | 44.1% (15/34) | 237.8 |

---

## Table 2: Component Ablation Study (Audited Frozen Test Set, N=34)

| Configuration | Condition Description | MRR | nDCG@8 | Conflict F1 | App. Abstain (N=8) | False Abstain (N=26) | 3-Way Decision Acc | Binary Gov. Acc | Root-Cause Audit Finding |
|---|---|---|---|---|---|---|---|---|---|
| **SYS-FULL** | Reference Full Pipeline | 0.878 | 0.91 | 85.7% | 100.0% (8/8) | 53.8% (14/26) | 44.1% (15/34) | 64.7% (22/34) | Full DocuTrust architecture with multi-agent verification and reranking. |
| **ABL-1** | - Claim Verification | 0.878 | 0.91 | 85.7% | 100.0% (8/8) | 69.2% (18/26) | 32.4% (11/34) | 52.9% (18/34) | Sentence entailment disabled; 0 claims evaluated; -3.0% 3-way accuracy drop. |
| **ABL-2** | - Version Intelligence | 0.878 | 0.91 | 85.7% | 100.0% (8/8) | 50.0% (13/26) | 47.1% (16/34) | 67.6% (23/34) | Version supersession filtering bypassed; false abstentions increase to 50.0% (-8.8% accuracy). |
| **ABL-3** | - Conflict Analysis | 0.878 | 0.91 | 0.0% | 100.0% (8/8) | 53.8% (14/26) | 44.1% (15/34) | 64.7% (22/34) | Conflict detector disabled; 0 conflict flags raised across all queries. |
| **ABL-4** | - Evidence Abstention | 0.878 | 0.91 | 85.7% | 100.0% (8/8) | 46.2% (12/26) | 41.2% (14/34) | 64.7% (22/34) | Forced generation enabled; generates ungrounded claims on 8 unanswerable queries. |
| **ABL-5** | - Cross-Encoder Reranker | 0.86 | 0.895 | 85.7% | 87.5% (7/8) | 15.4% (4/26) | 64.7% (22/34) | 85.3% (29/34) | Raw RRF scores (~0.02) clamped to 0.1 in confidence formula; triggers 57.7% false review escalations. |

---

## Table 3: Exact Statistical Significance Testing (SYS-FULL vs. BASE-C)

- **MRR Paired Student's t-test (df=25):** $t = 1.383, p = 0.1787$ (Difference not significant at $\alpha=0.05$)
- **nDCG@8 Paired Student's t-test (df=25):** $t = 1.377, p = 0.1807$ (Difference not significant at $\alpha=0.05$)
- **McNemar Test Discordant Pairs:** $b = 7$ (SYS-FULL correct, BASE-C wrong), $c = 12$ (BASE-C correct, SYS-FULL wrong), Total Discordant $= 19$
- **McNemar Test Exact Two-Tailed Binomial:** $p = 0.3593$ (Not Significant)
- **McNemar Continuity-Corrected $\chi^2$:** $\chi^2 = 0.8421, p = 0.3588$
- **SYS-FULL MRR 95% Bootstrap Percentile CI (B=2000):** [0.782, 0.962]
- **SYS-FULL nDCG@8 95% Bootstrap Percentile CI (B=2000):** [0.839, 0.972]


## Table 4: 3-Way Decision Confusion Matrices


| Expected Decision | SYS-FULL (Act: ANS) | SYS-FULL (Act: ESC) | SYS-FULL (Act: ABST) | BASE-C (Act: ANS) | BASE-C (Act: ESC) | BASE-C (Act: ABST) |

|---|---|---|---|---|---|---|

| **ANSWER (N=20)** | 8 | 11 | 1 | 20 | 0 | 0 |

| **ESCALATE_REVIEW (N=6)** | 0 | 4 | 2 | 6 | 0 | 0 |

| **ABSTAIN (N=8)** | 0 | 5 | 3 | 8 | 0 | 0 |
