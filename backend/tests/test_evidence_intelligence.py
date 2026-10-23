from backend.agents.contracts import Evidence, ConflictAnalysis
from backend.evidence_intelligence import (
    assess_evidence_sufficiency,
    calculate_evidence_confidence,
    detect_policy_conflicts,
    generate_evidence_receipt,
    verify_claims_against_evidence,
)


def test_empty_evidence_is_insufficient():
    status, reasons = assess_evidence_sufficiency("What is the retention period?", [])
    assert status == "INSUFFICIENT_EVIDENCE"
    assert len(reasons) > 0


def test_grounded_evidence_has_provenance_receipt():
    evidence_list = [
        Evidence(
            document_id="policy-1",
            version="v2026",
            section="Retention",
            quote="Customer data retention period is 24 months.",
            score=0.94,
            document_name="Data Retention Policy",
            chunk_id="chunk-ret-1"
        )
    ]
    status, reasons = assess_evidence_sufficiency("What is the retention period?", evidence_list)
    assert status == "SUPPORTED"

    conflicts = detect_policy_conflicts(evidence_list, query="What is the retention period?")
    claims = verify_claims_against_evidence("Customer data retention period is 24 months.", evidence_list)
    assert len(claims) > 0
    assert claims[0].status == "SUPPORTED"

    confidence = calculate_evidence_confidence(evidence_list, claims, conflicts, "What is the retention period?")
    assert confidence.final_score >= 0.70

    receipt = generate_evidence_receipt(
        query="What is the retention period?",
        answer="Customer data retention period is 24 months.",
        evidence=evidence_list,
        confidence_breakdown=confidence,
        conflict_analysis=conflicts,
        agents_used=["Policy Agent", "Verification Agent", "Report Agent"],
        sufficiency_status=status,
        review_reasons=reasons
    )
    assert len(receipt.provenance_hash) == 64
    assert receipt.receipt_id.startswith("dt-rcpt-")


def test_insufficient_out_of_domain_requires_review():
    evidence_list = [
        Evidence(
            document_id="policy-1",
            version="v2026",
            section="Section 1",
            quote="Standard civilian remote work allowance is 3 days.",
            score=0.5,
            chunk_id="chunk-1"
        )
    ]
    status, reasons = assess_evidence_sufficiency("What is the policy for staff posted in Antarctica?", evidence_list)
    assert status == "INSUFFICIENT_EVIDENCE"
    assert any("Antarctica" in r for r in reasons)

