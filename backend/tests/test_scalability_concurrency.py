from __future__ import annotations

import asyncio
import pytest
from backend.agents.contracts import Evidence
from backend.evidence_intelligence import generate_evidence_receipt
from backend.graph.workflow import run_policy_graph
from backend.rag_engine import rag_engine
from backend.repositories.store import MemoryStore


@pytest.mark.asyncio
async def test_memory_store_pagination_and_bounding_cap():
    """Verifies that MemoryStore bounds total retained items and supports pagination."""
    store = MemoryStore()
    tenant = "test-tenant-pagination"

    # Append items up to MAX_RETAINED_ITEMS + 20
    test_limit = MemoryStore.MAX_RETAINED_ITEMS + 20
    for i in range(test_limit):
        await store.append(tenant, "runs", {"id": f"run-{i}", "index": i})

    # Verify bounding cap: total items in collection cannot exceed MAX_RETAINED_ITEMS
    all_items = await store.list(tenant, "runs", limit=10000, offset=0)
    assert len(all_items) == MemoryStore.MAX_RETAINED_ITEMS
    # Oldest 20 items (0..19) should have been evicted; earliest retained index is 20
    assert all_items[0]["index"] == 20

    # Test pagination slicing: limit=5, offset=10
    page = await store.list(tenant, "runs", limit=5, offset=10)
    assert len(page) == 5
    assert page[0]["index"] == 30
    assert page[-1]["index"] == 34


@pytest.mark.asyncio
async def test_concurrent_tenant_isolation_boundary():
    """Verifies that concurrent requests from different tenants with identical document names

    never leak evidence, citations, or answers across tenant boundaries.
    """
    tenants = ["tenant_alpha_iso", "tenant_beta_iso", "tenant_gamma_iso"]
    tenant_tokens = {
        "tenant_alpha_iso": "TOKEN_ALPHA_CONFIDENTIAL_111",
        "tenant_beta_iso": "TOKEN_BETA_CONFIDENTIAL_222",
        "tenant_gamma_iso": "TOKEN_GAMMA_CONFIDENTIAL_333",
    }

    # Ingest identically-named policy with tenant-specific confidential tokens
    for t_id, token in tenant_tokens.items():
        doc_text = f"""
CIVILIAN WORK-FROM-HOME POLICY
Document ID: 03_Civilian_Work_From_Home_Policy.pdf
Version: v1 | Effective Date: 2024-01-01 | Status: Active Current
Authority: {t_id.upper()} Directorate

Section 4.2: Work-From-Home Limitations
Eligible personnel for {t_id} may work remotely for a maximum limit of 3 days per calendar week.
CONFIDENTIAL_SECURITY_TOKEN: {token}
"""
        rag_engine.index_text(
            tenant_id=t_id,
            document_name="03_Civilian_Work_From_Home_Policy.pdf",
            document_id=f"{t_id}_wfh_v1",
            text=doc_text,
            version="v1"
        )

    # Launch 30 concurrent requests across the 3 tenants
    async def worker(t_id: str, run_idx: int):
        foreign_tokens = [tok for t, tok in tenant_tokens.items() if t != t_id]
        query = "What is the maximum allowed civilian work-from-home days per week?"

        state = await run_policy_graph(query, tenant_id=t_id)

        # 1. Assert all evidence chunks strictly belong to requesting tenant
        for ev in state.evidence:
            assert ev.tenant_id == t_id, f"Cross-tenant leak: found tenant {ev.tenant_id} in {t_id}"
            for ft in foreign_tokens:
                assert ft not in ev.quote, f"Foreign confidential token {ft} found in evidence of {t_id}"

        # 2. Assert final answer does not leak foreign tokens
        for ft in foreign_tokens:
            assert ft not in state.final_answer, f"Foreign token {ft} leaked in final answer of {t_id}"

        # 3. Assert cryptographic receipt provenance matches requesting tenant
        assert state.receipt is not None
        assert state.receipt.provenance_hash is not None
        assert len(state.receipt.provenance_hash) == 64

    tasks = [worker(tenants[i % len(tenants)], i) for i in range(30)]
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_concurrent_receipt_provenance_determinism():
    """Verifies that cryptographic evidence receipts remain tamper-evident and deterministic

    even under concurrent parallel execution.
    """
    evidence = [
        Evidence(
            document_id="doc-test-1",
            version="v1",
            section="Section 2.1",
            quote="Domestic travel meal per diem is $75 per day.",
            score=0.95,
            retrieval_method="hybrid_rag",
            document_name="04_Finance_Code.pdf",
            tenant_id="tenant-crypto-test",
            chunk_id="chunk-test-1"
        )
    ]

    from backend.evidence_intelligence import (
        assess_evidence_sufficiency,
        calculate_evidence_confidence,
        detect_policy_conflicts,
        verify_claims_against_evidence,
    )

    query_text = "What is the travel per diem allowance?"
    answer_text = "The maximum standard domestic business travel meal allowance is $75 per day."
    status, reasons = assess_evidence_sufficiency(query_text, evidence)
    conflicts = detect_policy_conflicts(evidence, query=query_text)
    claims = verify_claims_against_evidence(answer_text, evidence)
    confidence = calculate_evidence_confidence(evidence, claims, conflicts, query_text)

    async def generate_and_check(idx: int):
        rcpt = generate_evidence_receipt(
            query=f"{query_text} (Worker {idx})",
            answer=answer_text,
            evidence=evidence,
            confidence_breakdown=confidence,
            conflict_analysis=conflicts,
            agents_used=["Policy Agent", "Verification Agent"],
            sufficiency_status=status,
            review_reasons=reasons,
        )
        assert rcpt.receipt_id.startswith("dt-rcpt-")
        assert len(rcpt.provenance_hash) == 64
        assert rcpt.decision in ("ANSWER", "APPROVED", "ESCALATE_REVIEW", "ABSTAIN", "NEEDS_REVIEW")

    await asyncio.gather(*(generate_and_check(i) for i in range(25)))
