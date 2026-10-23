# DocuTrust Scaling Benchmark & Empirical Evaluation Suite

This directory contains the reproducible empirical scaling and concurrency benchmarking harness for the **DocuTrust** platform, evaluating behavior across data volume ($N \in \{100, 1000, 10000\}$ chunks), concurrency levels ($C \in \{1, 5, 10, 25, 50\}$ simultaneous requests), and strict multi-tenant security boundaries.

---

## 1. Objectives & Methodological Guardrails

1. **Controlled Corpus Scaling:** Evaluate latency, memory (RSS), disk serialization, and Information Retrieval effectiveness (Hit@1, MRR, nDCG@8) across controlled corpus sizes without modifying the underlying gold compliance ground truth.
2. **Explicit Distractor Labeling:** All synthetic distractors are generated with deterministic seeds (`seed=42`) and explicitly prefixed with `[SYNTHETIC DISTRACTOR]`. They are never presented as authentic organizational policy.
3. **Frozen Evaluation Annotations:** IR evaluation is performed against the frozen, expert-annotated query set from `research/docutrust_bench_pilot.jsonl` (Direct Fact, Multi-hop, Policy Supersession, Conflict Detection).
4. **Isolated Concurrency Load:** Measures throughput (completed requests/sec), latency percentiles ($p_{50}, p_{95}, p_{99}$), and resource utilization (CPU %, peak RSS MB) using bounded asyncio worker pools.
5. **Zero Cross-Tenant Leakage Verification:** Fires concurrent adversarial requests across synthetic tenants with identically named policies and overlapping clauses to empirically verify isolation barriers and cryptographic provenance receipts.

---

## 2. Directory Structure

```
research/scaling/
├── README.md                     <- Reproducibility instructions & methodology
├── benchmark_runner.py           <- Unified benchmark execution harness
├── results/
│   ├── scaling_results.json      <- Full raw empirical benchmark metrics
│   └── scaling_summary.md        <- Formatted summary tables & analytical narrative
└── plots/
    ├── plot_corpus_vs_index_time_and_disk.png
    ├── plot_corpus_vs_latency_percentiles.png
    ├── plot_corpus_vs_ir_metrics.png
    └── plot_concurrency_vs_throughput.png
```

---

## 3. How to Run the Scaling Benchmark

### Prerequisites
Ensure backend and RAG dependencies are installed:
```bash
pip install -r requirements.txt
pip install -r RAG_project/requirements.txt
pip install psutil matplotlib numpy
```

### Execution
Run the standalone benchmark suite from the repository root:
```bash
python research/scaling/benchmark_runner.py
```

### Execution Phases
1. **System Profiling:** Detects host OS, processor architecture, available RAM, and CPU core topology.
2. **Phase 2 (Data-Scaling):**
   - Ingests gold compliance documents alongside controlled batches of synthetic distractor chunks ($N = 100, 1000, 10000$).
   - Benchmarks index build time, serialization size, deserialization load time, and memory delta.
   - Computes $p_{50}, p_{95}, p_{99}$ retrieval latency across BM25, Dense FAISS, Hybrid RRF, and Hybrid + Cross-Encoder reranking.
   - Evaluates Hit@1, MRR, and nDCG@8 against frozen annotations.
   - Executes the 50,000-chunk feasibility and memory boundary probe.
3. **Phase 3 (Concurrency Load Test):**
   - Simulates concurrent query streams ($C \in \{1, 5, 10, 25, 50\}$).
   - Measures completed throughput (req/s), latency distributions, and CPU/memory pressure for both retrieval-only and full 12-stage multi-agent workflows.
4. **Phase 5 (Multi-Tenant Isolation Test):**
   - Fires 100 parallel cross-tenant queries across 5 synthetic tenants with identically named policies.
   - Validates that zero foreign chunks or tenant security tokens leak across tenant boundaries.
   - Verifies cryptographic evidence receipt provenance.
5. **Artifact Generation:** Automatically writes `scaling_results.json`, `scaling_summary.md`, and high-resolution matplotlib plots.

---

## 4. Key Performance Metrics Recorded

| Dimension | Metric | Description |
| :--- | :--- | :--- |
| **Corpus Scaling** | `index_construction_time_sec` | Wall-clock time to embed documents and build BM25 + FAISS indexes |
| | `index_disk_size_mb` | Total serialized storage on disk for index and metadata pickle |
| | `index_load_time_sec` | Time to deserialize vector index and document store into memory |
| | `peak_rss_mb` | Peak process resident set size memory during indexing and retrieval |
| | `latency_p50_ms`, `p95`, `p99` | Retrieval response latency percentiles per query |
| | `hit_at_1`, `mrr`, `ndcg_at_8` | Classical Information Retrieval accuracy metrics against gold citations |
| **Concurrency** | `throughput_rps` | Completed requests per second under bounded semaphore load |
| | `cpu_percent` | Host CPU utilization percentage during benchmark execution |
| | `error_rate` | Percentage of failed, timed-out, or unhandled requests |
| **Tenant Isolation** | `cross_tenant_evidence_leaks`| Number of retrieved evidence passages belonging to another tenant (Target: 0) |
| | `foreign_secret_token_leaks` | Number of occurrences of another tenant's secret token in answers (Target: 0) |
| | `verified_receipts` | Count of verified tamper-evident cryptographic provenance receipts |

---

## 5. Scientific Integrity Standards

- **No Data Fabrication:** Every number in `scaling_results.json` reflects physical measurements recorded on the execution host.
- **Constant Gold Evidence:** Distractors are added without modifying gold policy citations or answer keys.
- **Resource Boundary Transparency:** When hardware constraints (e.g., host RAM limits) bound feasibility for extreme scales ($N \ge 50{,}000$), the physical bottleneck is documented rather than extrapolated.
