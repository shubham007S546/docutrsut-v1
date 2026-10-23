import pytest
from backend.agents.contracts import Evidence
from backend.evidence_intelligence import (
    detect_policy_conflicts,
    extract_policy_clauses,
    PolicyClause,
)


def test_positive_hierarchy_conflict():
    """Direct manager email consent contradicting formal Director written authorization must trigger escalation."""
    evidence = [
        Evidence(
            document_id="03_Civilian_Work_From_Home_Policy_v1",
            version="v1",
            section="Section 4.2",
            quote="Prior written authorization from the primary Department Director is mandatory prior to commencement of hybrid schedules. General remote work capped at 3 days.",
            score=0.9,
            chunk_id="chunk-1"
        )
    ]
    res = detect_policy_conflicts(evidence, query="Can my direct manager approve 4 days work from home via email?")
    assert res.conflict_detected is True
    assert res.status == "HUMAN REVIEW REQUIRED"
    assert any(c.get("type") == "AUTHORIZATION_HIERARCHY_CONFLICT" for c in res.conflicts)
    assert "Department Director" in res.resolution_reason


def test_negative_no_conflict_security_query():
    """Security query with unanimous mandatory controls must not trigger a false conflict."""
    evidence = [
        Evidence(
            document_id="01_Security_Safeguards_Policy_v2",
            version="v2.4",
            section="Section 3.1",
            quote="No employee, contractor, or officer has authorization to bypass technical security controls. Endpoint encryption and MFA are mandatory.",
            score=0.95,
            chunk_id="chunk-sec"
        )
    ]
    res = detect_policy_conflicts(evidence, query="Can I ignore security requirements?")
    assert res.conflict_detected is False
    assert res.status == "NONE"
    assert len(res.conflicts) == 0


def test_negative_clean_wfh_query_no_false_positive():
    """Standard inquiry asking for the WFH limit must not falsely flag a conflict when rules are harmonious."""
    evidence = [
        Evidence(
            document_id="03_Civilian_Work_From_Home_Policy_v2",
            version="v2",
            section="Section 4.2",
            quote="The standard remote work allowance for general personnel is up to three (3) days per week. Technology Division may work up to 4 days.",
            score=0.88,
            chunk_id="chunk-2"
        )
    ]
    res = detect_policy_conflicts(evidence, query="What is the work-from-home limit?")
    assert res.conflict_detected is False
    assert res.status == "NONE"


def test_version_supersession_resolution():
    """A comparative inquiry between v1 (3 days) and v2 (4 days tech exception) must resolve via supersession."""
    evidence = [
        Evidence(
            document_id="03_Civilian_Work_From_Home_Policy_v1",
            version="v1",
            section="Section 4.2",
            quote="Eligible civilian personnel may work remotely for a maximum limit of three (3) days per calendar week.",
            score=0.85,
            chunk_id="chunk-v1"
        ),
        Evidence(
            document_id="03_Civilian_Work_From_Home_Policy_v2",
            version="v2",
            section="Section 4.2",
            quote="The standard remote work allowance is 3 days. EXCEPTION FOR TECHNOLOGY DIVISION: up to four (4) days per calendar week. Policy Revision v2 supersedes all provisions of Revision v1.",
            score=0.92,
            chunk_id="chunk-v2"
        )
    ]
    res = detect_policy_conflicts(evidence, query="What changed between v1 and v2 for remote work limits?")
    assert res.conflict_detected is True
    assert res.status == "RESOLVED"
    assert "supersedes" in res.resolution_reason.lower()
    assert "Technology Division" in res.affected_departments


def test_clause_extraction_structure():
    """Verifies that candidate clauses are extracted into typed PolicyClause instances with explicit scope and modality."""
    evidence = [
        Evidence(
            document_id="03_Civilian_Work_From_Home_Policy_v2",
            version="v2",
            section="Section 4.2",
            quote="EXCEPTION FOR TECHNOLOGY DIVISION: Personnel assigned to the Technology Division may work remotely up to four (4) days per calendar week.",
            score=0.90,
            chunk_id="chunk-tech"
        )
    ]
    clauses = extract_policy_clauses(evidence)
    assert len(clauses) >= 1
    tech_clause = next(c for c in clauses if c.scope == "technology_division")
    assert tech_clause.subject == "remote_work_limit"
    assert tech_clause.prescribed_value == 4
    assert tech_clause.normative_modality == "EXCEPTION"


def test_positive_security_mfa_override_conflict():
    """Verbal permission from project lead cannot override mandatory technical security controls."""
    evidence = [
        Evidence(
            document_id="01_Security_Safeguards_Policy_v2",
            version="v2.4",
            section="Section 3.1",
            quote="No employee, contractor, or officer has authorization to bypass technical security controls. Endpoint MFA is mandatory.",
            score=0.95,
            chunk_id="chunk-sec"
        )
    ]
    res = detect_policy_conflicts(evidence, query="Can an engineering contractor disable endpoint MFA if their project lead gives verbal permission?")
    assert res.conflict_detected is True
    assert res.status == "HUMAN REVIEW REQUIRED"
    assert any(c.get("type") == "SECURITY_OVERRIDE_CONFLICT" for c in res.conflicts)
    assert "MFA" in res.resolution_reason or "security" in res.resolution_reason.lower()


def test_positive_privacy_usb_storage_conflict():
    """Urgent customer request cannot override strict prohibition on unmanaged USB drives."""
    evidence = [
        Evidence(
            document_id="02_Privacy_and_Data_Protection_Standard_v1",
            version="v1.2",
            section="Section 4.3",
            quote="Personal and customer data is strictly prohibited from being copied to personal, unmanaged USB drives or non-corporate cloud accounts.",
            score=0.95,
            chunk_id="chunk-priv"
        )
    ]
    res = detect_policy_conflicts(evidence, query="Can customer data be copied to a personal USB drive if a customer requests urgent off-site delivery?")
    assert res.conflict_detected is True
    assert res.status == "HUMAN REVIEW REQUIRED"
    assert any(c.get("type") == "DATA_EXFILTRATION_CONFLICT" for c in res.conflicts)


def test_positive_finance_gaming_monitor_conflict():
    """Manager sign-off cannot override strict exclusion of gaming monitors from equipment stipend."""
    evidence = [
        Evidence(
            document_id="04_Finance_and_Expense_Reimbursement_Code_v1",
            version="v1.0",
            section="Section 2.1",
            quote="Eligible personnel may claim up to $500 for ergonomic office chair and desk. Personal 4K entertainment monitors, gaming gear, and television equipment are strictly non-reimbursable.",
            score=0.95,
            chunk_id="chunk-fin"
        )
    ]
    res = detect_policy_conflicts(evidence, query="Can an employee be reimbursed for a $1,200 4K gaming monitor if their manager signs off on the expense report?")
    assert res.conflict_detected is True
    assert res.status == "HUMAN REVIEW REQUIRED"
    assert any(c.get("type") == "EXPENSE_POLICY_CONFLICT" for c in res.conflicts)

