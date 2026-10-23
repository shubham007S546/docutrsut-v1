# Related Work & Theoretical Positioning of DocuTrust

---

## 1. Literature Overview & Taxonomy

Retrieval-Augmented Generation (RAG) and Agentic Systems for compliance can be structured across four key paradigms:

1. **Foundational & Dense RAG:**
   - *Lewis et al. (NeurIPS 2020):* Introduced RAG combining parametric seq2seq models with non-parametric dense vector indices.
   - *Karpukhin et al. (EMNLP 2020) [DPR]:* Dense Passage Retrieval utilizing dual-encoder architectures.
   - *Robertson et al. (2009) [BM25]:* Standard probabilistic lexical retrieval baseline.

2. **Self-Reflective & Adaptive RAG:**
   - *Asai et al. (ICLR 2024) [Self-RAG]:* Trains language models to generate arbitrary reflection tokens (`[Retrieve]`, `[IsRel]`, `[IsSup]`, `[IsUse]`) to dynamically decide when to retrieve and critique output quality.
     - *Distinction:* Self-RAG requires fine-tuning specialized decoder models on curated critique datasets. DocuTrust operationalizes trust as an external, model-agnostic, multi-agent software architecture without requiring proprietary weight modifications.
   - *Yan et al. (arXiv 2024) [Corrective RAG (CRAG)]:* Uses a lightweight retrieval evaluator to assess document relevance and falls back to web search when retrieval confidence is low.
     - *Distinction:* CRAG addresses low retrieval relevance via external web expansion, which is strictly prohibited in enterprise compliance due to privacy and confidentiality boundaries. DocuTrust enforces tenant-scoped abstention and human escalation rather than web searching.

3. **Claim-Level Grounding & Attribution:**
   - *Gao et al. (ACL 2023) [RARR]:* Research and revision framework attributing claims and editing unsupported output.
   - *Min et al. (EMNLP 2023) [FActScore]:* Decomposes long-form generation into atomic facts and verifies each against a reference text.

4. **Multi-Agent Systems & Tool Governance:**
   - *Wu et al. (arXiv 2023) [AutoGen], Li et al. (arXiv 2023) [Camel]:* Multi-agent conversation frameworks.
   - *DocuTrust Contribution:* Implements deterministic supervisor routing with hard execution bounds (max 3 iterations, 11 allow-listed safe tools), preventing infinite execution loops while enforcing tenant isolation.

---

## 2. Capability Comparison Matrix

| System / Method | Adaptive Retrieval | Claim-Level Verification | Policy Version Awareness | Cross-Doc Conflict Handling | Evidence Abstention | Provenance Receipts | Evaluation Protocol | Primary Limitations Relevant to DocuTrust |
|---|---|---|---|---|---|---|---|---|
| **Standard RAG (Lewis et al., 2020)** | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | ❌ Basic text citation | Open-domain QA (NQ, TriviaQA) | High hallucination; ignores policy supersession; no abstention. |
| **Self-RAG (Asai et al., 2024)** | ✅ Yes (token-based) | ⚠️ Indirect (critique tokens) | ❌ No | ❌ No | ⚠️ Partial (Score threshold) | ❌ No | Factuality benchmarks (PubHealth, PopQA) | Requires custom model fine-tuning; cannot enforce multi-tenant isolation. |
| **CRAG (Yan et al., 2024)** | ✅ Yes (evaluator) | ❌ No | ❌ No | ❌ No | ❌ No (Searches web) | ❌ No | PopQA, Biography | Relies on external web queries; violates enterprise confidentiality. |
| **FActScore (Min et al., 2023)** | ❌ No | ✅ Yes (atomic fact NLI) | ❌ No | ❌ No | ❌ No | ❌ No | Biography generation | Offline post-hoc evaluation metric only; not a live runtime architecture. |
| **DocuTrust (This Work)** | ✅ Yes (Supervisor planning) | ✅ Yes (Clause-level entailment) | ✅ Yes (Supersession diff engine) | ✅ Yes (Pairwise rule precedence) | ✅ Yes (Sufficiency gate & review queue) | ✅ Yes (SHA-256 cryptographic receipt) | DocuTrust-Bench (400 compliance queries) | Multi-stage orchestration adds measurable latency overhead. |

---

## 3. Formulating the Core Academic Contribution

DocuTrust's scientific novelty is situated in **Trustworthy Applied IR & Multi-Agent Systems**:
> **Contribution Statement:**  
> Rather than relying on ungrounded generative fluency, DocuTrust formalizes an end-to-end **Evidence Governance Architecture (EGA)** for multi-tenant compliance QA. We show that integrating:
> 1. In-process hybrid retrieval with policy-version awareness,
> 2. Pairwise conflict and hierarchy resolution,
> 3. Clause-level claim verification, and
> 4. Calibrated evidence-based abstention with cryptographic audit receipts
>
> achieves a statistically superior Pareto frontier on factuality, conflict disclosure, and supersession compliance compared to conventional RAG and agentic architectures, while operating entirely within strict tenant boundaries.
