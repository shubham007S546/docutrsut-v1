# DocuTrust Research Paper Package: Complete Submission & Reproducibility Suite

**Title:** DocuTrust: Multi-Agent Evidence Governance, Policy Version Precedence, and Calibrated Abstention for Compliance Question Answering  
**Target Venues:** IEEE Transactions on Knowledge and Data Engineering (TKDE) / ACM TOIS / ACL / EMNLP / SIGIR (Applied AI Track)  
**Status:** Complete Manuscript — Independent Scientific Audit Verified — Publication PDF Rendered  
**Date:** October 2026  

---

## 1. Directory Structure

```
research/paper/
├── main.pdf                         ← Complete compiled 7-page IEEE journal publication PDF (2.35 MB)
├── docutrust_paper.pdf              ← Mirror publication PDF
├── main.tex                         ← Complete IEEE-format LaTeX source code
├── docutrust_paper.tex              ← Mirror LaTeX manuscript
├── references.bib                   ← Verified BibTeX bibliography (29 entries, including PRISMA 2020)
├── docutrust_refs.bib               ← Mirror BibTeX file
├── SCIENTIFIC_AUDIT_REPORT.md       ← Full audit reconciling PRISMA counts, abstention, & latency
├── RESULTS_PROVENANCE.md            ← Complete data-to-paper traceability matrix
├── LITERATURE_SCREENING.csv         ← PRISMA screening registry (66 records with transparent criteria)
├── LITERATURE_EVIDENCE_MATRIX.csv   ← Deep evidence synthesis matrix (27 foundational studies)
├── PRIOR_REVIEW_COMPARISON.csv      ← Systematic comparison against prior RAG/NLP reviews
├── compile_paper.sh                 ← Unix/macOS/Linux 4-pass pdflatex compilation script
├── compile_paper.ps1                ← Windows PowerShell MiKTeX compilation script
├── figures/                         ← All 9 publication figures (Vector PDF + 300-DPI PNG)
│   ├── fig1_prisma_flowchart.pdf/.png      ← Figure 1: PRISMA 2020 study selection flow diagram
│   ├── fig2_architecture.pdf/.png          ← Figure 2: DocuTrust end-to-end multi-agent architecture
│   ├── fig3_eval_pipeline.pdf/.png          ← Figure 3: DocuTrust-Bench evaluation & zero-leakage split
│   ├── fig4_retrieval_comparison.pdf/.png   ← Figure 4: Retrieval performance comparison (Hit@1, MRR, nDCG)
│   ├── fig5_ablation.pdf/.png               ← Figure 5: Systematic component ablation analysis
│   ├── fig6_latency_breakdown.pdf/.png      ← Figure 6: Latency audit (BM25 cold start vs. median breakdown)
│   ├── fig7_decision_abstention.pdf/.png    ← Figure 7: 3-way confusion matrix & compliance safety tradeoff
│   ├── fig8_provenance_chain.pdf/.png       ← Figure 8: Conceptual evidence-provenance chain
│   └── fig9_taxonomy.pdf/.png               ← Figure 9: Taxonomy of trustworthy compliance QA
└── scripts/
    ├── generate_all_9_figures.py    ← Python script generating all 9 vector PDFs and PNGs
    └── build_full_publication_pdf.py← Python script compiling the full HTML/PDF manuscript
```

---

## 2. Reconciled Core Results

| Metric | Baseline Best | DocuTrust (SYS-FULL) | Statistical Significance & Verification Notes |
|---|---|---|---|
| **Hit@1** | 76.9% (BASE-A, C, D) | **76.9%** | Dense-only achieved 61.5%; hybrid retrieval is essential |
| **MRR** | 0.878 (BASE-D) | **0.878** | Paired $t(25) = 1.383, p = 0.1787$ (95% Bootstrap CI: $[0.782, 0.962]$) |
| **nDCG@8** | 0.910 (BASE-D) | **0.910** | Paired $t(25) = 1.377, p = 0.1807$ (95% Bootstrap CI: $[0.839, 0.972]$) |
| **Claim Support Rate** | *N/A (0 claims)* | **91.7%** | $187 / 204$ claims strictly entailed by active evidence |
| **Conflict F1** | 0.0% (all baselines) | **85.7%** | Standard prompts missed 100% of out-of-domain conflicts (FN=3) |
| **Safe Non-Answer Rate** | 0.0% (all baselines) | **100.0%** | $8/8$ unanswerable queries safely routed (3 ABSTAIN, 5 ESCALATE) |
| **Exact 3-Way Accuracy** | 58.8% (all baselines) | **44.1%** | $15/34$ exact concordance; baselines blindly answered all 34 |
| **False Abstention Rate** | 0.0% (all baselines) | **53.8%** | $14/26$ answerable queries escalated to human review |
| **Median Latency** | 0.5 ms (BM25 steady) | **236.0 ms** | BM25 mean (1,847.4 ms) was distorted by 40.2s cold start |

---

## 3. Compilation & Reproduction Instructions

### A. View Compiled Publication PDF
The complete, compiled 7-page publication PDF is ready:
- `research/paper/main.pdf`
- `research/paper/docutrust_paper.pdf`

### B. Re-compile via Headless Chromium / Edge
```powershell
python research/paper/scripts/build_full_publication_pdf.py
```

### C. Compile via LaTeX (TeX Live / MiKTeX)
On Linux/macOS:
```bash
bash research/paper/compile_paper.sh
```
On Windows:
```powershell
.\research\paper\compile_paper.ps1
```

### D. Regenerate All 9 Figures from Audited Data
```powershell
python research/paper/scripts/generate_all_9_figures.py
```
