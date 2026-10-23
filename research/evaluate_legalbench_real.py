"""
DocuTrust Real Public Benchmark Evaluation on Stanford LegalBench (Contract QA)
Evaluates BM25, Dense FAISS, Hybrid RRF, and Cross-Encoder on 80 real commercial contracts
from Stanford's LegalBench benchmark (Guha et al., NeurIPS 2023).
"""
import json
import os
import sys
import time
from pathlib import Path
import numpy as np
from datasets import load_dataset

# Ensure project roots in path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
RAG_DIR = ROOT_DIR / "RAG_project"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from RAG_project.loaders.pdf_loader import Document
from RAG_project.retriever.bm25 import BM25Retriever
from RAG_project.vectorstore.faiss_db import FAISSVectorStore
from backend.evaluation_service import compute_ir_metrics
from backend.rag_engine import (
    TenantRAGIndex,
    _get_shared_cross_encoder,
    _get_shared_embedding_model,
)

def evaluate_legalbench():
    print("=" * 75)
    print("EVALUATING DOCUTRUST ON REAL PUBLIC DATASET: STANFORD LEGALBENCH (NeurIPS 2023)")
    print("Task: contract_qa (80 Real Commercial Legal Contracts & Compliance Queries)")
    print("=" * 75)

    # 1. Load dataset from HuggingFace
    print("[*] Loading 'contract_qa' from 'nguha/legalbench'...")
    ds = load_dataset("nguha/legalbench", "contract_qa", split="test")
    total_items = len(ds)
    print(f"[+] Loaded {total_items} real contract documents and compliance queries.")

    # 2. Convert each contract into a Document object
    tenant_id = "real_legalbench_tenant"
    contract_docs = []
    queries = []
    
    for i, row in enumerate(ds):
        doc_id = f"legalbench_contract_{i:03d}"
        chunk_id = f"legalbench_chunk_{i:03d}"
        doc = Document(
            page_content=row["text"],
            metadata={
                "document_id": doc_id,
                "document_name": f"LegalBench_Contract_{i:03d}.pdf",
                "chunk_id": chunk_id,
                "tenant_id": tenant_id,
                "source": f"LegalBench_Contract_{i:03d}.pdf",
                "page": 1,
                "version": "v1.0",
            }
        )
        contract_docs.append(doc)
        queries.append({
            "query": row["question"],
            "gold_chunk_ids": [chunk_id],
            "graded_relevance": {chunk_id: 2},
            "expected_answer": row["answer"]
        })

    # 3. Build BM25 on the 80 real contracts
    t0_bm25 = time.perf_counter()
    bm25 = BM25Retriever()
    bm25.build(contract_docs)
    bm25_time = time.perf_counter() - t0_bm25
    print(f"[+] Built BM25 index over 80 real contract documents in {bm25_time:.4f}s.")

    # 4. Build Dense FAISS
    t0_faiss = time.perf_counter()
    emb_model = _get_shared_embedding_model()
    _get_shared_cross_encoder()
    
    all_embeddings = []
    batch_size = 32
    for b_start in range(0, len(contract_docs), batch_size):
        b_docs = contract_docs[b_start : b_start + batch_size]
        emb_res = emb_model.embed_documents(b_docs)
        emb_arr = emb_res[1] if isinstance(emb_res, tuple) and len(emb_res) == 2 else emb_res
        all_embeddings.append(emb_arr)

    stacked_embeddings = np.vstack(all_embeddings).astype(np.float32)
    faiss_idx = FAISSVectorStore()
    faiss_idx.build_index(stacked_embeddings, contract_docs)
    faiss_time = time.perf_counter() - t0_faiss
    print(f"[+] Built FAISS Dense index over 80 real contracts in {faiss_time:.4f}s.")

    # 5. Assemble into Tenant Index
    tenant_rag = TenantRAGIndex(tenant_id)
    tenant_rag.documents = contract_docs
    tenant_rag.bm25 = bm25
    tenant_rag.vector_store = faiss_idx

    # 6. Evaluate Retrieval Modes across all 80 real queries
    modes = ["bm25", "dense", "hybrid", "hybrid_rerank"]
    results = {}

    for mode in modes:
        latencies = []
        hit_1_list = []
        mrr_list = []
        ndcg_list = []

        for q in queries:
            q_text = q["query"]
            gold_ids = set(q["gold_chunk_ids"])
            graded_rel = q["graded_relevance"]

            t0 = time.perf_counter()
            if mode == "bm25":
                retrieved, _ = tenant_rag.retrieve(q_text, top_k=8, mode="bm25")
            elif mode == "dense":
                retrieved, _ = tenant_rag.retrieve(q_text, top_k=8, mode="dense")
            elif mode == "hybrid":
                retrieved, _ = tenant_rag.retrieve(q_text, top_k=8, mode="hybrid", rerank=False)
            elif mode == "hybrid_rerank":
                retrieved, _ = tenant_rag.retrieve(q_text, top_k=8, mode="hybrid", rerank=True)
            lat_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(lat_ms)

            retrieved_chunk_ids = [
                r["document"].metadata.get("chunk_id", "")
                for r in retrieved if isinstance(r, dict) and r.get("document")
            ]

            hit_1 = 1.0 if retrieved_chunk_ids and retrieved_chunk_ids[0] in gold_ids else 0.0
            hit_1_list.append(hit_1)

            ir_res = compute_ir_metrics(retrieved_chunk_ids, list(gold_ids), graded_rel, k=8)
            mrr_list.append(ir_res.get("reciprocal_rank", 0.0))
            ndcg_list.append(ir_res.get("ndcg_at_k", 0.0))

        results[mode] = {
            "hit_at_1": float(np.mean(hit_1_list)),
            "mrr": float(np.mean(mrr_list)),
            "ndcg_at_8": float(np.mean(ndcg_list)),
            "latency_p50_ms": float(np.percentile(latencies, 50)),
            "latency_p95_ms": float(np.percentile(latencies, 95)),
            "latency_mean_ms": float(np.mean(latencies)),
        }
        print(f"  -> Mode: {mode:<14} | Hit@1: {results[mode]['hit_at_1']*100:.1f}% | MRR: {results[mode]['mrr']:.4f} | nDCG@8: {results[mode]['ndcg_at_8']:.4f} | p50 Lat: {results[mode]['latency_p50_ms']:.2f}ms")

    # 7. Add Out-of-Scope Calibrated Abstention Test
    # In compliance, if a query asks about unrelated topics (e.g., flight booking in an employment contract),
    # does the system safely abstain?
    ood_queries = [
        "What is the maximum allowed civilian baggage weight for domestic airfare?",
        "How many vacation days are carried over into the next calendar year?",
        "What is the company per diem reimbursement rate for dinner in New York?",
        "What is the minimum GPU memory required for training computer vision models?",
        "Are employees eligible for electric vehicle charging stall subsidies?"
    ]
    ood_abstention_count = 0
    for ood in ood_queries:
        retrieved, _ = tenant_rag.retrieve(ood, top_k=8, mode="hybrid", rerank=True)
        # Check top score calibration
        top_score = retrieved[0].get("calibrated_score", 0.0) if retrieved else 0.0
        # If score < 0.70, it triggers abstention
        if top_score < 0.70:
            ood_abstention_count += 1

    safe_abstention_rate = ood_abstention_count / len(ood_queries)
    print(f"\n[+] Real Calibrated Abstention on OOD Queries: {safe_abstention_rate*100:.1f}% ({ood_abstention_count}/{len(ood_queries)} safely refused)")

    out_data = {
        "dataset_name": "Stanford LegalBench (NeurIPS 2023)",
        "task": "contract_qa",
        "real_documents_count": total_items,
        "queries_count": total_items,
        "results": results,
        "calibrated_abstention_ood_rate": safe_abstention_rate,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    out_file = ROOT_DIR / "research" / "results" / "legalbench_real_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"\n[+] Verifiable real results saved to: {out_file}")
    return out_data

if __name__ == "__main__":
    evaluate_legalbench()
