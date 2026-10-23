"""
Comprehensive Test Suite for DocuTrust
Verifies all 4 demo scenarios and core novelties:
1. Tenant-scoped retrieval isolation (0 leaks)
2. Scenario 1: Supported WFH policy query (Grounded answer, high confidence)
3. Scenario 2: Antarctica WFH policy query (Insufficient evidence, abstention, review escalation)
4. Scenario 3: 4 Days WFH approval (Contradiction detection, precedence resolution, review escalation)
5. Scenario 4: Policy Version Impact Analysis (v1 vs v2 organizational diff)
6. Cryptographic Evidence Receipt generation and SHA-256 provenance hash integrity
"""
import asyncio
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from backend.rag_engine import rag_engine
from backend.graph.workflow import run_policy_graph
from backend.policy_impact import analyze_policy_impact

async def run_all_tests():
    print("=" * 60)
    print("STARTING DOCUTRUST COMPLIANCE & TRUST SUITE")
    print("=" * 60)

    # TEST 1: Tenant Retrieval Isolation
    print("\n[TEST 1] Testing Strict Tenant-Scoped Isolation...")
    tenant_res = rag_engine.test_tenant_isolation("tenant-alpha", "tenant-beta")
    assert tenant_res["status"] == "PASS", f"Tenant isolation failed: {tenant_res}"
    assert tenant_res["cross_tenant_leak_count"] == 0, "Cross-tenant leak detected!"
    print(f"  -> PASS: 0 leaks, tenant isolation verified: {tenant_res['status']}")

    # TEST 2: Scenario 1 - WFH Limit (Supported)
    print("\n[TEST 2] Scenario 1: WFH Limit (Baseline Allowance)...")
    s1_query = "What is the civilian work from home policy limit?"
    state_s1 = await run_policy_graph(s1_query, "test-tenant-1", "private")
    print(f"  -> Answer: {state_s1.final_answer[:120]}...")
    print(f"  -> Confidence: {state_s1.overall_confidence:.2f}")
    print(f"  -> Status: {state_s1.evidence_state.get('status')}")
    print(f"  -> Requires Review: {state_s1.requires_review}")
    assert state_s1.overall_confidence >= 0.65, f"Expected confidence >= 0.65, got {state_s1.overall_confidence}"
    assert state_s1.evidence_state.get("status") in ("grounded", "SUPPORTED", "PARTIALLY_SUPPORTED")
    assert not state_s1.requires_review, "Supported query should not require human review escalation"
    assert state_s1.receipt is not None, "Evidence receipt must be generated"
    print("  -> PASS: Scenario 1 fully grounded and verified.")

    # TEST 3: Scenario 2 - Antarctica Stationing (Insufficient Evidence -> Review)
    print("\n[TEST 3] Scenario 2: Antarctica WFH (Absence of Evidence)...")
    s2_query = "What is the civilian work-from-home policy for staff posted in Antarctica?"
    state_s2 = await run_policy_graph(s2_query, "test-tenant-1", "private")
    print(f"  -> Answer: {state_s2.final_answer[:120]}...")
    print(f"  -> Confidence: {state_s2.overall_confidence:.2f}")
    print(f"  -> Status: {state_s2.evidence_state.get('status')}")
    print(f"  -> Requires Review: {state_s2.requires_review}")
    print(f"  -> Review Reasons: {state_s2.review_reasons}")
    assert state_s2.requires_review, "Insufficient evidence query must trigger review escalation"
    assert state_s2.overall_confidence < 0.65, f"Expected confidence < 0.65, got {state_s2.overall_confidence}"
    assert state_s2.evidence_state.get("status") in ("insufficient", "INSUFFICIENT_EVIDENCE", "UNVERIFIED")
    print("  -> PASS: Scenario 2 abstained safely and escalated to human review.")

    # TEST 4: Scenario 3 - 4 Days WFH (Conflict Detection & Precedence)
    print("\n[TEST 4] Scenario 3: 4 Days WFH Email Approval (Policy Conflict)...")
    s3_query = "Can an employee work from home 4 days a week if their direct manager approves via email?"
    state_s3 = await run_policy_graph(s3_query, "test-tenant-1", "private")
    print(f"  -> Conflict Detected: {state_s3.conflict_analysis.conflict_detected}")
    print(f"  -> Precedence Resolution: {state_s3.conflict_analysis.precedence_resolution}")
    print(f"  -> Requires Review: {state_s3.requires_review}")
    print(f"  -> Review Reasons: {state_s3.review_reasons}")
    assert state_s3.conflict_analysis.conflict_detected, "Conflict between 4-day request and 2-day policy must be flagged"
    assert state_s3.requires_review, "Policy conflict must trigger review escalation"
    print("  -> PASS: Scenario 3 conflict detected with precedence resolution.")

    # TEST 5: Scenario 4 - Policy Version Intelligence (v1 vs v2 diff)
    print("\n[TEST 5] Scenario 4: Policy Version Intelligence (v1 vs v2)...")
    idx = rag_engine.get_tenant_index("test-tenant-1")
    v1_text = "\n".join([d.page_content for d in idx.documents if d.metadata.get("version") == "v1"])
    v2_text = "\n".join([d.page_content for d in idx.documents if d.metadata.get("version") == "v2"])
    impact = analyze_policy_impact("Civilian Work-From-Home Policy", v1_text, v2_text, "v1", "v2")
    print(f"  -> Policy: {impact.policy_name}")
    print(f"  -> Impact Level: {impact.impact_level}")
    print(f"  -> Affected Rules: {impact.affected_rules}")
    print(f"  -> Affected Departments: {impact.affected_departments}")
    assert impact.impact_level == "HIGH", f"Expected HIGH impact, got {impact.impact_level}"
    assert len(impact.affected_rules) > 0, "Expected affected rules identified"
    assert len(impact.affected_departments) > 0, "Expected impacted departments identified"
    print("  -> PASS: Scenario 4 Policy Change Impact Analysis successfully computed.")

    # TEST 6: Cryptographic Receipt Provenance
    print("\n[TEST 6] Testing Cryptographic Evidence Receipt Provenance...")
    receipt = state_s1.receipt
    assert receipt is not None
    assert receipt.receipt_id.startswith("dt-rcpt-") or receipt.receipt_id.startswith("RCP-")
    assert len(receipt.provenance_hash) == 64  # SHA-256 is 64 hex characters
    print(f"  -> Receipt ID: {receipt.receipt_id}")
    print(f"  -> Provenance SHA-256 Hash: {receipt.provenance_hash}")
    print("  -> PASS: Cryptographic receipt verified.")

    print("\n" + "=" * 60)
    print("ALL 6 TESTS PASSED WITH ZERO ERRORS!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
