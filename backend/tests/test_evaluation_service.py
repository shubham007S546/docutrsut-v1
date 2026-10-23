import pytest
from backend.evaluation_service import compute_ir_metrics, compute_citation_metrics
from backend.agents.contracts import ClaimVerification


def test_ir_metrics_empty_relevant_set_unanswerable():
    """Unanswerable queries (|Gold| = 0) must not set recall to 0.0 or distort the IR denominator."""
    res = compute_ir_metrics(
        retrieved_chunk_ids=["chunk_1", "chunk_2"],
        gold_chunk_ids=[],
        graded_relevance={},
        k=4
    )
    assert res["recall_at_k"] is None
    assert res["precision_at_k"] == 0.0
    assert res["gold_count"] == 0


def test_ir_metrics_duplicate_retrieved_chunks():
    """Duplicate chunk IDs in retrieval must be deduplicated when computing rank and precision."""
    res = compute_ir_metrics(
        retrieved_chunk_ids=["chunk_1", "chunk_1", "chunk_2"],
        gold_chunk_ids=["chunk_1", "chunk_2"],
        k=2
    )
    # Deduplication yields ["chunk_1", "chunk_2"]
    assert res["relevant_retrieved_count"] == 2
    assert res["precision_at_k"] == 1.0
    assert res["recall_at_k"] == 1.0
    assert res["reciprocal_rank"] == 1.0


def test_ir_metrics_multiple_relevant_passages():
    """Tests MRR and nDCG when multiple relevant passages exist at various ranks."""
    res = compute_ir_metrics(
        retrieved_chunk_ids=["irrelevant_1", "gold_1", "irrelevant_2", "gold_2"],
        gold_chunk_ids=["gold_1", "gold_2"],
        graded_relevance={"gold_1": 2, "gold_2": 2},
        k=4
    )
    assert res["relevant_retrieved_count"] == 2
    assert res["precision_at_k"] == 0.5
    assert res["recall_at_k"] == 1.0
    # First gold at rank 2: RR = 1/2 = 0.5
    assert res["reciprocal_rank"] == 0.5
    assert res["ndcg_at_k"] > 0.0


def test_citation_metrics_all_supported():
    """Claims with verified citations should yield 1.0 precision and coverage."""
    claims = [
        ClaimVerification(
            claim_id="c1",
            claim_text="General staff can work remotely up to 3 days.",
            status="SUPPORTED",
            supporting_evidence_ids=["chunk_wfh_1"],
            conflicting_evidence_ids=[],
            document_name="Policy.pdf",
            section="Section 4.2",
            version="v2",
            confidence=0.9,
            rationale="Grounded"
        )
    ]
    res = compute_citation_metrics(claims)
    assert res["citation_precision"] == 1.0
    assert res["citation_coverage"] == 1.0
    assert res["supported_claims"] == 1


def test_citation_metrics_missing_and_unsupported_citations():
    """Evaluates citation precision when claims lack supporting evidence or are unsupported."""
    claims = [
        ClaimVerification(
            claim_id="c1",
            claim_text="Staff receive free lunch daily.",
            status="NOT_SUPPORTED",
            supporting_evidence_ids=[],
            conflicting_evidence_ids=[],
            document_name="None",
            section="None",
            version="None",
            confidence=0.1,
            rationale="Ungrounded"
        ),
        ClaimVerification(
            claim_id="c2",
            claim_text="Technology division staff can work 4 days remotely.",
            status="SUPPORTED",
            supporting_evidence_ids=["chunk_wfh_2"],
            conflicting_evidence_ids=[],
            document_name="Policy.pdf",
            section="Section 4.2",
            version="v2",
            confidence=0.95,
            rationale="Grounded"
        )
    ]
    res = compute_citation_metrics(claims)
    assert res["total_claims"] == 2
    assert res["supported_claims"] == 1
    assert res["unsupported_claims"] == 1
    assert res["citation_coverage"] == 0.5
    assert res["citation_precision"] == 1.0  # Only c2 claimed citation, and it was supported
