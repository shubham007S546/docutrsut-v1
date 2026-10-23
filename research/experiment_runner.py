"""
DocuTrust Scientific Experiment Runner
Executes all baselines, retrieval variants, and ablations on the frozen benchmark test set.
Saves comprehensive raw per-query experimental data to research/results/raw_experiment_results.json.
"""
from __future__ import annotations

import asyncio
import datetime
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from backend.agents.contracts import Evidence
from backend.evidence_intelligence import (
    assess_evidence_sufficiency,
    calculate_evidence_confidence,
    detect_policy_conflicts,
    generate_evidence_receipt,
    verify_claims_against_evidence,
)
from backend.rag_engine import rag_engine
from backend.providers.fallback import provider_chain
from backend.providers.llm_gateway import GatewayError
from backend.graph.workflow import _deterministic_synthesis

_GENERATION_CACHE: dict[str, tuple[str, str, str]] = {}
_GROQ_CIRCUIT_BROKEN = False

async def synthesize_answer(
    query: str,
    evidence: list[Evidence],
    conflict_res: Any,
    config_name: str = "SYS-FULL",
) -> tuple[str, str, str]:
    """Returns (answer_text, provider_name, model_name)."""
    global _GROQ_CIRCUIT_BROKEN
    if not evidence:
        return (
            "The uploaded policy does not establish an answer to this question. No evidence found.",
            "deterministic_fallback",
            "empty_evidence_rule"
        )

    # Cache key uniquely isolates configuration arm, conflict detection state, query, and evidence set
    evidence_ids = "|".join(e.chunk_id or e.document_id for e in evidence)
    conflict_flag = "conflict_yes" if getattr(conflict_res, "conflict_detected", False) else "conflict_no"
    cache_key = f"{config_name}::{conflict_flag}::{query}::{evidence_ids}"
    if cache_key in _GENERATION_CACHE:
        return _GENERATION_CACHE[cache_key]

    if _GROQ_CIRCUIT_BROKEN:
        ans = _deterministic_synthesis("policy", query, evidence, conflict_res)
        res = (ans, "deterministic_fallback", "deterministic_synthesis_v1")
        _GENERATION_CACHE[cache_key] = res
        return res

    context = "\n\n".join(f"[{item.document_name} | {item.section} | {item.version}]\n{item.quote}" for item in evidence)
    system_role = "You are an evidence-grounded compliance intelligence assistant in DocuTrust. Answer using ONLY approved policy evidence."
    prompt = f"User Question: {query}\n\nApproved Evidence:\n{context}\n\nProvide an authoritative, grounded answer citing sources inline."

    try:
        gen = await provider_chain.generate(system=system_role, user=prompt)
        ans = gen.text.strip()
        provider_used = getattr(gen, "provider", "groq")
        model_used = getattr(gen, "model", "llama-3.3-70b-versatile")
        res = (ans, str(provider_used), str(model_used))
        _GENERATION_CACHE[cache_key] = res
        return res
    except Exception:
        _GROQ_CIRCUIT_BROKEN = True
        ans = _deterministic_synthesis("policy", query, evidence, conflict_res)
        res = (ans, "deterministic_fallback", "deterministic_synthesis_v1")
        _GENERATION_CACHE[cache_key] = res
        return res

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_frozen_test_set(dataset_path: str = "research/docutrust_bench_pilot.jsonl") -> list[dict[str, Any]]:
    path = Path(dataset_path)
    test_items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("split") == "test":
                test_items.append(item)
    print(f"Loaded {len(test_items)} frozen test set items for evaluation.")
    return test_items


def records_to_evidence(records: list[Any]) -> list[Evidence]:
    evidence_list: list[Evidence] = []
    for r in records:
        evidence_list.append(
            Evidence(
                document_id=r.document_id,
                document_name=r.document_name,
                version=r.policy_version,
                section=r.section,
                quote=r.text,
                score=r.retrieval_score,
                chunk_id=r.chunk_id,
            )
        )
    return evidence_list


async def run_single_query_configuration(
    item: dict[str, Any],
    config_name: str,
) -> dict[str, Any]:
    query = item["query"]
    tenant_id = item["tenant_id"]
    t0 = time.perf_counter()

    # 1. Retrieval Stage based on Configuration
    if config_name == "BASE-A":  # BM25-Only
        records = rag_engine.retrieve(query, tenant_id=tenant_id, mode="bm25", top_k=8)
    elif config_name == "BASE-B":  # Dense-Only
        records = rag_engine.retrieve(query, tenant_id=tenant_id, mode="dense", top_k=8)
    elif config_name in ("BASE-C", "BASE-E", "ABL-5"):  # Hybrid RRF (No Rerank)
        records = rag_engine.retrieve(query, tenant_id=tenant_id, mode="hybrid", rerank=False, top_k=8)
    elif config_name == "ITER-RETRIEVE":  # Bounded Iterative Retrieval
        records = rag_engine.retrieve_iterative(query, tenant_id=tenant_id, mode="hybrid", rerank=True, top_k=8)
    else:  # Hybrid + Cross-Encoder Reranker (BASE-D, SYS-FULL, ABL-1, ABL-2, ABL-3, ABL-4)
        records = rag_engine.retrieve(query, tenant_id=tenant_id, mode="hybrid", rerank=True, top_k=8)

    evidence = records_to_evidence(records)
    retrieved_chunk_ids = [r.chunk_id for r in records]

    # 2. Sufficiency & Abstention Check (except if abstention ablated)
    abstain_disabled = config_name in ("BASE-A", "BASE-B", "BASE-C", "BASE-D", "ABL-4")
    if not abstain_disabled:
        suff_status, suff_reasons = assess_evidence_sufficiency(query, evidence)
    else:
        suff_status, suff_reasons = "SUPPORTED", []

    # 3. Policy Conflict Analysis (except if conflict analysis disabled)
    conflict_disabled = config_name in ("BASE-A", "BASE-B", "BASE-C", "BASE-D", "BASE-E", "ABL-3")
    if not conflict_disabled:
        conflict_res = detect_policy_conflicts(evidence, query=query)
    else:
        from backend.agents.contracts import ConflictAnalysis
        conflict_res = ConflictAnalysis(conflict_detected=False, conflicts=[], resolution_reason="", status="NONE")

    # 4. Version Awareness Filter (dynamically resolved from indexed corpus metadata, eliminating oracle leakage)
    version_disabled = config_name in ("BASE-A", "BASE-B", "BASE-C", "BASE-D", "BASE-E", "ABL-2")
    filtered_evidence = evidence
    if not version_disabled and evidence:
        idx = rag_engine.get_tenant_index(tenant_id)
        doc_names = list(dict.fromkeys(e.document_name for e in evidence if e.document_name))
        active_versions = set()
        for doc_name in doc_names:
            dyn_v = idx.get_active_version(doc_name)
            if dyn_v:
                active_versions.add(dyn_v)
        if active_versions:
            active_passages = [e for e in evidence if e.version in active_versions or e.version in ("General", "None")]
            if active_passages:
                filtered_evidence = active_passages

    # 5. Generation Synthesis
    provider_used = "system_heuristic"
    model_used = "none"
    if not abstain_disabled and suff_status in ("INSUFFICIENT_EVIDENCE", "UNVERIFIED"):
        answer = f"The uploaded policy does not establish an answer to this question: '{query}'. This inquiry has been escalated to the Human Review Queue."
        claims = []
        provider_used = "deterministic_abstention"
        model_used = "policy_gate_v1"
    else:
        answer, provider_used, model_used = await synthesize_answer(query, filtered_evidence, conflict_res, config_name=config_name)

    # 6. Claim-Level Verification (except if ablated)
    verification_disabled = config_name in ("BASE-A", "BASE-B", "BASE-C", "BASE-D", "ABL-1")
    if not verification_disabled and answer:
        claims = verify_claims_against_evidence(answer, filtered_evidence)
    else:
        claims = []

    # 7. Confidence & Routing Decision
    if config_name in ("BASE-A", "BASE-B", "BASE-C", "BASE-D"):
        # Unverified baselines always produce ANSWER unless query explicitly failed
        decision = "ANSWER"
        requires_review = False
        final_confidence = 0.90 if records else 0.20
    else:
        confidence_breakdown = calculate_evidence_confidence(
            filtered_evidence,
            claims,
            conflict_res,
            query
        )
        final_confidence = confidence_breakdown.final_score
        requires_review = (
            confidence_breakdown.decision == "HUMAN REVIEW REQUIRED"
            or suff_status != "SUPPORTED"
            or (conflict_res.conflict_detected and conflict_res.status == "HUMAN REVIEW REQUIRED")
        )
        decision = "ESCALATE_REVIEW" if requires_review else "ANSWER"
        if not abstain_disabled and suff_status in ("INSUFFICIENT_EVIDENCE", "UNVERIFIED"):
            decision = "ABSTAIN"

    # 8. Cryptographic Provenance Receipt
    receipt = None
    if config_name in ("SYS-FULL", "ITER-RETRIEVE", "ABL-1", "ABL-2", "ABL-3", "ABL-4", "ABL-5"):
        receipt = generate_evidence_receipt(
            query=query,
            answer=answer,
            evidence=filtered_evidence,
            confidence_breakdown=confidence_breakdown,
            conflict_analysis=conflict_res,
            agents_used=["Policy Agent", "Verification Agent", "Report Agent"],
            sufficiency_status=suff_status,
            review_reasons=["Review escalated"] if requires_review else [],
        )

    latency_ms = round((time.perf_counter() - t0) * 1000.0, 1)

    return {
        "id": item["id"],
        "category": item["category"],
        "policy_family": item["policy_family"],
        "query": query,
        "is_answerable": item["is_answerable"],
        "expected_decision": item["expected_decision"],
        "expected_review": item["escalation_required"],
        "gold_chunk_ids": item["gold_chunk_ids"],
        "graded_relevance": item.get("graded_relevance", {}),
        "actual_decision": decision,
        "actual_review": requires_review,
        "confidence": final_confidence,
        "retrieved_chunk_ids": retrieved_chunk_ids,
        "generated_answer": answer,
        "claims_count": len(claims),
        "supported_claims": sum(1 for c in claims if c.status == "SUPPORTED"),
        "conflict_detected": conflict_res.conflict_detected,
        "expected_conflict": item["conflict_present"],
        "generator_provider": provider_used,
        "generator_model": model_used,
        "random_seed": 42,
        "receipt_hash": receipt.provenance_hash if receipt else None,
        "latency_ms": latency_ms,
    }


async def run_full_experiment_suite(test_items: list[dict[str, Any]]) -> dict[str, Any]:
    configurations = [
        "BASE-A",         # BM25-Only RAG
        "BASE-B",         # Dense-Only FAISS RAG
        "BASE-C",         # Standard Hybrid RRF
        "BASE-D",         # Hybrid RRF + Cross-Encoder Reranker
        "BASE-E",         # Hybrid RRF + Claim Verification
        "ITER-RETRIEVE",  # Bounded 2-Pass Iterative Retrieval
        "SYS-FULL",       # Full DocuTrust Pipeline
        "ABL-1",          # Full DocuTrust - Claim Verification
        "ABL-2",          # Full DocuTrust - Version Awareness
        "ABL-3",          # Full DocuTrust - Conflict Analysis
        "ABL-4",          # Full DocuTrust - Evidence Abstention
        "ABL-5",          # Full DocuTrust - Cross-Encoder Reranker
    ]

    print(f"\n{'='*70}")
    print(f"RUNNING DOCUTRUST RESEARCH EXPERIMENT SUITE ({len(configurations)} CONFIGS X {len(test_items)} QUERIES)")
    print(f"{'='*70}\n")

    manifest = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
        },
        "provenance": {
            "random_seed": 42,
            "groq_circuit_broken": _GROQ_CIRCUIT_BROKEN,
            "default_model": "llama-3.3-70b-versatile",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        },
        "total_test_items": len(test_items),
        "configurations": configurations,
        "raw_results": {},
    }

    for config in configurations:
        print(f"--> Running Configuration: {config} ...", end="", flush=True)
        config_start = time.perf_counter()
        results_for_config = []
        for item in test_items:
            res = await run_single_query_configuration(item, config)
            results_for_config.append(res)
        elapsed = time.perf_counter() - config_start
        print(f" Done ({len(results_for_config)} items in {elapsed:.1f}s)")
        manifest["raw_results"][config] = results_for_config

    output_path = RESULTS_DIR / "raw_experiment_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n[OK] Successfully saved all raw experiment results to: {output_path}")

    return manifest


if __name__ == "__main__":
    items = load_frozen_test_set()
    asyncio.run(run_full_experiment_suite(items))
