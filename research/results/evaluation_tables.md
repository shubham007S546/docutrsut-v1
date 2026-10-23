## Table 1: Benchmark Baseline Comparison (Frozen Test Set, N=34)

| System Configuration | Precision@8 | Recall@8 | MRR | nDCG@8 | Claim Support | Conflict F1 | App. Abstain | Decision Acc. | Latency (ms) |
|---|---|---|---|---|---|---|---|---|---|
| **BASE-A** | 12.5% | 100.0% | 0.865 | 0.899 | N/A (0 Claims) | 0.0% | 0.0% | 58.8% | 1847.4 |
| **BASE-B** | 12.5% | 100.0% | 0.779 | 0.835 | N/A (0 Claims) | 0.0% | 0.0% | 58.8% | 17.3 |
| **BASE-C** | 12.5% | 100.0% | 0.86 | 0.895 | N/A (0 Claims) | 0.0% | 0.0% | 58.8% | 14.2 |
| **BASE-D** | 12.5% | 100.0% | 0.878 | 0.91 | N/A (0 Claims) | 0.0% | 0.0% | 58.8% | 333.4 |
| **BASE-E** | 12.5% | 100.0% | 0.86 | 0.895 | 91.1% | 0.0% | 87.5% | 58.8% | 16.7 |
| **ITER-RETRIEVE** | 12.5% | 100.0% | 0.878 | 0.91 | 91.7% | 85.7% | 100.0% | 44.1% | 473.3 |
| **SYS-FULL** | 12.5% | 100.0% | 0.878 | 0.91 | 91.7% | 85.7% | 100.0% | 44.1% | 237.8 |

---

## Table 2: Component Ablation Study (Frozen Test Set, N=34)

| Ablated Configuration | Precision@8 | Recall@8 | MRR | nDCG@8 | Conflict F1 | App. Abstain | Decision Acc. | Impact Observation |
|---|---|---|---|---|---|---|---|---|
| **SYS-FULL** | 12.5% | 100.0% | 0.878 | 0.91 | 85.7% | 100.0% | 44.1% | Full DocuTrust Pipeline (Benchmark Baseline) |
| **ABL-1** | 12.5% | 100.0% | 0.878 | 0.91 | 85.7% | 100.0% | 32.4% | Ablation 1: - Claim Verification (Removes sentence entailment) |
| **ABL-2** | 12.5% | 100.0% | 0.878 | 0.91 | 85.7% | 100.0% | 47.1% | Ablation 2: - Policy Version Awareness (Ignores v1 vs v2 supersession) |
| **ABL-3** | 12.5% | 100.0% | 0.878 | 0.91 | 0.0% | 100.0% | 44.1% | Ablation 3: - Conflict Analysis (Disables hierarchy contradiction detector) |
| **ABL-4** | 12.5% | 100.0% | 0.878 | 0.91 | 85.7% | 100.0% | 41.2% | Ablation 4: - Evidence Abstention (Forced generation on ungrounded queries) |
| **ABL-5** | 12.5% | 100.0% | 0.86 | 0.895 | 85.7% | 87.5% | 64.7% | Ablation 5: - Cross-Encoder Reranker (Standard RRF retrieval only) |

---

## Table 3: Statistical Hypothesis Testing (SYS-FULL vs. BASE-C)

- **MRR Paired t-test:** $t = 1.383, p = 0.1787$ (Not Significant)
- **nDCG@8 Paired t-test:** $t = 1.377, p = 0.1807$ (Not Significant)
- **Decision Accuracy McNemar Test:** $\chi^2 = 0.842, p = 0.3593$ (Not Significant)
- **Full System MRR 95% Bootstrap CI:** [0.782, 0.962]
- **Full System nDCG@8 95% Bootstrap CI:** [0.839, 0.972]