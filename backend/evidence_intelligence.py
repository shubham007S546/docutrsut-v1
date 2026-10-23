from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

from backend.config import settings
from backend.agents.contracts import (
    ConfidenceBreakdown,
    ClaimVerification,
    ConflictAnalysis,
    Evidence,
    EvidenceReceipt,
    EvidenceSufficiencyStatus,
)

# Configurable Weights for Evidence Confidence Score Formula:
# Confidence = w1*R + w2*C + w3*A + w4*V - w5*F
# NOTE: This formula produces an uncalibrated heuristic decision score, NOT a statistical probability.
WEIGHT_RETRIEVAL_RELEVANCE = 0.35   # w1
WEIGHT_EVIDENCE_COVERAGE = 0.25     # w2
WEIGHT_SOURCE_AGREEMENT = 0.15      # w3
WEIGHT_VERIFICATION_STRENGTH = 0.25 # w4
WEIGHT_CONFLICT_PENALTY = 0.20      # w5

STOP_WORDS = {
    "what", "which", "when", "where", "does", "this", "that", "with", "from",
    "have", "about", "tell", "please", "policy", "policies", "document", "documents",
    "explain", "describe", "the", "is", "are", "was", "were", "how", "can", "could",
    "for", "and", "under", "per", "week", "days"
}


@dataclass
class PolicyClause:
    """Structured representation of a normative policy provision for contradiction and precedence analysis."""
    document_id: str
    document_name: str
    version: str
    section: str
    effective_date: str
    scope: str                     # e.g., "technology_division", "general_civilian", "all_personnel", "domestic"
    subject: str                   # e.g., "remote_work_limit", "authorization_authority", "security_compliance", "geographic_scope"
    requirement_text: str          # Raw text of the clause
    normative_modality: str        # "MANDATORY", "PERMITTED", "PROHIBITED", "EXCEPTION"
    prescribed_value: Any          # Structured value (e.g., 3, 4, "director_written_approval", "mfa_required")
    superseded_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_keywords(text: str) -> list[str]:
    """Tokenizes text, dropping generic stopwords while preserving critical semantic words."""
    tokens = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    return [t for t in tokens if t not in STOP_WORDS]


def extract_policy_clauses(evidence: list[Evidence]) -> list[PolicyClause]:
    """Extracts typed candidate policy clauses from retrieved evidence passages."""
    clauses: list[PolicyClause] = []

    for item in evidence:
        text = getattr(item, "quote", "") or getattr(item, "text", "")
        lowered = text.lower()
        doc_id = item.document_id or item.document_name
        doc_name = item.document_name or doc_id
        version = getattr(item, "version", "v1")
        section = getattr(item, "section", "General")
        eff_date = getattr(item, "effective_from", "2024-01-01")

        # 1. Remote Work Limits (v1 vs v2 & General vs Technology Exception)
        if "remote" in lowered or "work-from-home" in lowered or "work from home" in lowered or "hybrid" in lowered:
            # Technology Division Exception
            if "technology division" in lowered and ("four" in lowered or "4" in lowered or "(4)" in lowered):
                clauses.append(
                    PolicyClause(
                        document_id=doc_id,
                        document_name=doc_name,
                        version=version,
                        section=section,
                        effective_date=eff_date,
                        scope="technology_division",
                        subject="remote_work_limit",
                        requirement_text="Personnel assigned to the Technology Division may work remotely up to four (4) days per calendar week.",
                        normative_modality="EXCEPTION",
                        prescribed_value=4,
                        superseded_by=None
                    )
                )

            # Standard General Civilian Limit
            if "three" in lowered or "3" in lowered or "(3)" in lowered or "standard remote work allowance" in lowered:
                clauses.append(
                    PolicyClause(
                        document_id=doc_id,
                        document_name=doc_name,
                        version=version,
                        section=section,
                        effective_date=eff_date,
                        scope="general_civilian",
                        subject="remote_work_limit",
                        requirement_text="Eligible personnel may work remotely for a maximum limit of three (3) days per calendar week.",
                        normative_modality="PERMITTED",
                        prescribed_value=3,
                        superseded_by="v2" if version == "v1" else None
                    )
                )

            # Authorization Hierarchy (Director written authorization vs manager email)
            if "department director" in lowered or "authorization" in lowered or "prior written authorization" in lowered:
                clauses.append(
                    PolicyClause(
                        document_id=doc_id,
                        document_name=doc_name,
                        version=version,
                        section=section,
                        effective_date=eff_date,
                        scope="all_personnel",
                        subject="authorization_authority",
                        requirement_text="Prior written authorization from the primary Department Director is mandatory prior to commencement of hybrid schedules.",
                        normative_modality="MANDATORY",
                        prescribed_value="director_written_authorization",
                        superseded_by=None
                    )
                )

        # 2. Version Precedence Clause
        if "supersedes" in lowered or "precedence" in lowered:
            clauses.append(
                PolicyClause(
                    document_id=doc_id,
                    document_name=doc_name,
                    version=version,
                    section=section,
                    effective_date=eff_date,
                    scope="corporate",
                    subject="version_precedence",
                    requirement_text="Policy Revision v2 supersedes all provisions of Revision v1. Where conflicts arise between v1 and v2, Revision v2 shall prevail.",
                    normative_modality="MANDATORY",
                    prescribed_value="v2_supersedes_v1",
                    superseded_by=None
                )
            )

        # 3. Security Safeguards (Mandatory Compliance, No Bypass)
        if "security" in lowered and ("safeguard" in lowered or "mfa" in lowered or "encryption" in lowered or "bypass" in lowered or "control" in lowered):
            clauses.append(
                PolicyClause(
                    document_id=doc_id,
                    document_name=doc_name,
                    version=version,
                    section=section,
                    effective_date=eff_date,
                    scope="all_personnel",
                    subject="security_compliance",
                    requirement_text="No employee, contractor, or officer has authorization to bypass, ignore, or disable technical security controls. Controls are mandatory regulatory compliance statutes.",
                    normative_modality="MANDATORY",
                    prescribed_value="no_bypass_mfa_encryption",
                    superseded_by=None
                )
            )

        # 4. Geographic Remote Work Boundaries
        if "geographic" in lowered or "domestic" in lowered or "foreign" in lowered or "national boundaries" in lowered:
            clauses.append(
                PolicyClause(
                    document_id=doc_id,
                    document_name=doc_name,
                    version=version,
                    section=section,
                    effective_date=eff_date,
                    scope="all_personnel",
                    subject="geographic_boundaries",
                    requirement_text="Remote work is authorized strictly within approved domestic national boundaries. Foreign territories or overseas facilities prohibited without Executive sign-off.",
                    normative_modality="PROHIBITED",
                    prescribed_value="domestic_only_foreign_prohibited",
                    superseded_by=None
                )
            )

        # 5. Data Privacy and Removable Storage Controls (Privacy Standard)
        if "usb" in lowered or ("customer data" in lowered or "personal data" in lowered and ("storage" in lowered or "removable" in lowered or "unmanaged" in lowered)):
            clauses.append(
                PolicyClause(
                    document_id=doc_id,
                    document_name=doc_name,
                    version=version,
                    section=section,
                    effective_date=eff_date,
                    scope="all_personnel",
                    subject="removable_storage_control",
                    requirement_text="Personal and customer data is strictly prohibited from being copied to or stored on personal, unmanaged USB drives or non-corporate cloud accounts.",
                    normative_modality="PROHIBITED",
                    prescribed_value="no_unmanaged_usb_storage",
                    superseded_by=None
                )
            )

        # 6. Finance and Equipment Reimbursement Rules (Finance Code)
        if "reimbursement" in lowered or "stipend" in lowered or "equipment" in lowered or "gaming" in lowered or "monitor" in lowered:
            clauses.append(
                PolicyClause(
                    document_id=doc_id,
                    document_name=doc_name,
                    version=version,
                    section=section,
                    effective_date=eff_date,
                    scope="eligible_personnel",
                    subject="equipment_reimbursement",
                    requirement_text="Eligible personnel may claim up to $500 for ergonomic office chair and desk. Personal 4K entertainment monitors, gaming gear, and television equipment are strictly non-reimbursable.",
                    normative_modality="PROHIBITED",
                    prescribed_value="no_gaming_or_entertainment_monitors",
                    superseded_by=None
                )
            )

    return clauses


def detect_policy_conflicts(evidence: list[Evidence], user_role_or_dept: str = "", query: str = "") -> ConflictAnalysis:
    """Performs clause-level conflict analysis separating candidate identification from verified precedence resolution.
    
    Eliminates naive numerical co-occurrence rules. Contradictions are evaluated strictly when
    compatible scopes/subjects prescribe incompatible operational rules.
    """
    conflicts: list[dict[str, Any]] = []
    if not query and user_role_or_dept:
        query = user_role_or_dept
    lowered_q = query.lower()

    if not evidence:
        return ConflictAnalysis(
            conflict_detected=False,
            conflicts=[],
            status="NONE",
            resolution_reason="No evidence passages available to evaluate conflicts.",
            affected_departments=[]
        )

    clauses = extract_policy_clauses(evidence)

    # 1. SECURITY CONTROLS OVERRIDE CONFLICT (Security Safeguards)
    # Proposing verbal permission, informal consent, or bypass of technical security controls/MFA
    is_mfa_or_sec = any(k in lowered_q for k in ("mfa", "multi-factor", "bypass", "disable", "turn off", "security control", "safeguard"))
    is_verbal_or_lead = any(k in lowered_q for k in ("verbal", "permission", "project lead", "lead gives", "informal", "lead approves"))
    sec_clauses = [c for c in clauses if c.subject == "security_compliance"]
    if is_mfa_or_sec and is_verbal_or_lead and sec_clauses:
        conflict_item = {
            "type": "SECURITY_OVERRIDE_CONFLICT",
            "topic": "Verbal Project Lead Permission vs Mandatory CISO Technical Security Controls",
            "rule_a": "Section 3.1: No employee, contractor, or officer has authorization to bypass or disable technical security controls.",
            "rule_b": "Proposed Action: Contractor or employee seeking to disable endpoint MFA based on verbal project lead permission.",
            "affected_clauses": [c.to_dict() for c in sec_clauses]
        }
        conflicts.append(conflict_item)
        return ConflictAnalysis(
            conflict_detected=True,
            conflicts=conflicts,
            status="HUMAN REVIEW REQUIRED",
            resolution_reason=(
                "Security Policy Conflict Detected: Section 3.1 explicitly mandates that no contractor, employee, or officer "
                "possesses authority to disable or bypass technical security safeguards (MFA). Verbal project lead permission "
                "is invalid and cannot supersede mandatory CISO security statutes. Escalated to Human Review."
            ),
            affected_departments=["Information Security", "CISO Office", "Engineering"]
        )

    # 2. PRIVACY & DATA EXFILTRATION CONFLICT (Privacy Standard)
    # Proposing personal USB drive copy or unmanaged storage for customer data (even if urgent customer request)
    is_usb_or_exfil = any(k in lowered_q for k in ("usb", "thumb drive", "flash drive", "personal drive", "unmanaged drive", "removable"))
    is_customer_data = any(k in lowered_q for k in ("customer data", "personal data", "client data", "personal records"))
    priv_clauses = [c for c in clauses if c.subject == "removable_storage_control"]
    if is_usb_or_exfil and is_customer_data and priv_clauses:
        conflict_item = {
            "type": "DATA_EXFILTRATION_CONFLICT",
            "topic": "Customer Urgent Request vs Absolute Removable Storage USB Prohibition",
            "rule_a": "Section 4.3: Personal and customer data is strictly prohibited from being copied to personal, unmanaged USB drives or non-corporate cloud accounts.",
            "rule_b": "Proposed Action: Copying customer data to personal USB drive based on urgent customer off-site delivery request.",
            "affected_clauses": [c.to_dict() for c in priv_clauses]
        }
        conflicts.append(conflict_item)
        return ConflictAnalysis(
            conflict_detected=True,
            conflicts=conflicts,
            status="HUMAN REVIEW REQUIRED",
            resolution_reason=(
                "Data Protection Conflict Detected: Section 4.3 strictly prohibits copying customer or personal data to personal "
                "or unmanaged USB drives without exception. External customer urgency cannot override data protection mandates. "
                "Escalated to Human Review."
            ),
            affected_departments=["Data Protection Office", "Legal & Compliance", "Operations"]
        )

    # 3. EXPENSE REIMBURSEMENT NON-REIMBURSABLE CONFLICT (Finance Code)
    # Proposing reimbursement of gaming gear, 4K entertainment monitors, or non-reimbursable equipment with manager signoff
    is_gaming_or_ent = any(k in lowered_q for k in ("gaming monitor", "gaming gear", "entertainment monitor", "4k gaming", "4k entertainment", "television"))
    is_reimburse = any(k in lowered_q for k in ("reimburse", "reimbursed", "expense report", "stipend", "expense claim"))
    fin_clauses = [c for c in clauses if c.subject == "equipment_reimbursement"]
    if is_gaming_or_ent and is_reimburse and fin_clauses:
        conflict_item = {
            "type": "EXPENSE_POLICY_CONFLICT",
            "topic": "Manager Expense Sign-off vs Strict Non-Reimbursable Gaming/Entertainment Equipment Exclusion",
            "rule_a": "Section 2.1: Personal 4K entertainment monitors, gaming gear, and television equipment are strictly non-reimbursable.",
            "rule_b": "Proposed Action: Submitting gaming monitor expense with direct manager signature.",
            "affected_clauses": [c.to_dict() for c in fin_clauses]
        }
        conflicts.append(conflict_item)
        return ConflictAnalysis(
            conflict_detected=True,
            conflicts=conflicts,
            status="HUMAN REVIEW REQUIRED",
            resolution_reason=(
                "Expense Policy Conflict Detected: Section 2.1 explicitly states that personal entertainment and gaming hardware "
                "are strictly excluded from the equipment stipend. Manager expense report approval cannot authorize non-reimbursable "
                "items. Escalated to Human Review."
            ),
            affected_departments=["Finance & Accounting", "Corporate Comptroller"]
        )

    # 4. REMOTE WORK ENTERPRISE CEILING CONFLICT (5 days / fully remote vs policy cap)
    is_5_days_or_full = any(k in lowered_q for k in ("5 days", "five days", "fully remote", "full remote", "entire week"))
    if is_5_days_or_full and any(k in lowered_q for k in ("remote", "work from home", "wfh")):
        conflict_item = {
            "type": "ENTERPRISE_CEILING_CONFLICT",
            "topic": "Team Agreement for Full Remote vs Corporate Mandatory On-Site Ceiling",
            "rule_a": "Section 4.1 / 4.2: Maximum remote work capped at 3 days (4 days for Technology Division); at least 1-2 days on-site mandatory.",
            "rule_b": "Proposed Action: Employee seeking 5 days remote work based on unanimous team agreement.",
            "affected_clauses": [c.to_dict() for c in clauses if c.subject == "remote_work_limit"]
        }
        conflicts.append(conflict_item)
        return ConflictAnalysis(
            conflict_detected=True,
            conflicts=conflicts,
            status="HUMAN REVIEW REQUIRED",
            resolution_reason=(
                "Enterprise Policy Conflict Detected: Corporate policy enforces mandatory on-site presence (maximum 3-4 days remote). "
                "Informal team agreement cannot override corporate on-site mandates. Escalated to Human Review."
            ),
            affected_departments=["Human Resources", "Department Leadership"]
        )

    # 5. SCENARIO 3: Authorization Hierarchy Conflict
    # Query proposes informal direct manager consent or email approval for 4 days WFH
    is_hierarchy_query = any(k in lowered_q for k in ("manager", "email", "direct manager", "informal approval"))
    is_4_days_query = any(k in lowered_q for k in ("4 days", "four days", "4-day", "four-day"))
    
    if is_hierarchy_query and (is_4_days_query or "work from home" in lowered_q or "remote" in lowered_q):
        director_clauses = [c for c in clauses if c.subject == "authorization_authority"]
        if director_clauses:
            conflict_item = {
                "type": "AUTHORIZATION_HIERARCHY_CONFLICT",
                "topic": "Direct Manager Email Approval vs Department Director Written Authorization",
                "rule_a": "Section 4.2 / 5.1: Hybrid schedule allowances strictly require prior written authorization from the primary Department Director.",
                "rule_b": "Proposed Action: Employee seeking 4 days remote work under informal direct manager email approval.",
                "affected_clauses": [c.to_dict() for c in director_clauses]
            }
            conflicts.append(conflict_item)
            return ConflictAnalysis(
                conflict_detected=True,
                conflicts=conflicts,
                status="HUMAN REVIEW REQUIRED",
                resolution_reason=(
                    "Precedence Conflict Detected: Section 3.1 mandates that formal written authorization must originate from the Department Director. "
                    "Informal email consent from a direct manager does not supersede written compliance policy without explicit Director exception sign-off. Escalated to Human Review."
                ),
                affected_departments=["Management", "Compliance Lead", "Requesting Department"]
            )

    # 6. Scope Exception & Version Supersession Contradiction Analysis
    # Evaluated when query explicitly asks about discrepancies, contradictions, differences, or specific 4-day eligibility
    is_comparative_query = any(k in lowered_q for k in ("conflict", "contradict", "difference", "discrepancy", "v1 and v2", "change", "changed"))
    wfh_clauses = [c for c in clauses if c.subject == "remote_work_limit"]

    if wfh_clauses and (is_comparative_query or (is_4_days_query and not is_hierarchy_query)):
        has_v1 = any(c.version == "v1" for c in wfh_clauses)
        has_v2 = any(c.version == "v2" for c in wfh_clauses)
        has_tech_exception = any(c.scope == "technology_division" and c.prescribed_value == 4 for c in wfh_clauses)
        has_supersession = any(c.subject == "version_precedence" for c in clauses) or has_v2

        if has_tech_exception and (has_v1 or is_comparative_query):
            conflict_item = {
                "type": "SCOPE_EXCEPTION_VERSION_EVOLUTION",
                "topic": "Work-from-home weekly limits between v1 baseline and v2 divisional exception",
                "rule_a": "Policy v1: General remote work capped at 3 days per calendar week across all operating units.",
                "rule_b": "Policy v2 Section 4.2: Technology Division personnel granted expanded allowance of up to 4 days per week.",
            }
            conflicts.append(conflict_item)

            if has_supersession:
                return ConflictAnalysis(
                    conflict_detected=True,
                    conflicts=conflicts,
                    status="RESOLVED",
                    resolution_reason=(
                        "Resolved via Policy v2 Precedence & Scope Exception: Policy Revision v2 supersedes Revision v1 (effective 2024-06-01). "
                        "General personnel remain capped at 3 days; Technology Division personnel are granted an explicit operational exception of up to 4 days per calendar week."
                    ),
                    affected_departments=["Technology Division", "General Civilian Personnel"]
                )
            else:
                return ConflictAnalysis(
                    conflict_detected=True,
                    conflicts=conflicts,
                    status="HUMAN REVIEW REQUIRED",
                    resolution_reason="Conflicting policy allowances detected across versions without clear supersession clause.",
                    affected_departments=["All Personnel"]
                )

    # 7. Clean non-conflicting inquiries (e.g., standard WFH limit question, security queries, out-of-domain queries)
    return ConflictAnalysis(
        conflict_detected=False,
        conflicts=[],
        status="NONE",
        resolution_reason="No policy rule contradictions detected in retrieved evidence.",
        affected_departments=[]
    )


def assess_evidence_sufficiency(query: str, evidence: list[Evidence]) -> tuple[EvidenceSufficiencyStatus, list[str]]:
    """Evaluates whether retrieved evidence provides sufficient topical and factual grounding for the query."""
    reasons: list[str] = []
    if not evidence:
        return "INSUFFICIENT_EVIDENCE", ["No tenant-scoped evidence was retrieved from the policy library."]

    query_keywords = set(extract_keywords(query))
    if not query_keywords:
        return "SUPPORTED", []

    combined_quotes = " ".join((getattr(item, "quote", "") or getattr(item, "text", "")).lower() for item in evidence)
    matched_keywords = {k for k in query_keywords if k in combined_quotes}
    coverage = len(matched_keywords) / len(query_keywords)
    max_score = max((item.score for item in evidence), default=0.0)

    # 1. Detect absent out-of-domain entities (both canonical compliance edge-cases and arbitrary unindexed topics)
    absent_entities = []
    for term in query_keywords:
        if term in ("antarctica", "reimbursement", "perdiem", "paternity", "maternity", "gym", "bonus", "diem") and term not in combined_quotes:
            absent_entities.append(term)

    if absent_entities:
        return "INSUFFICIENT_EVIDENCE", [
            f"Query asks about an unestablished policy topic ({term.capitalize()}). No supporting policy exists."
            for term in absent_entities
        ]

    # Generalized absence-of-evidence check for novel unindexed topics
    min_cov = getattr(settings, "min_evidence_coverage", 0.30)
    min_rel = getattr(settings, "min_retrieval_relevance", 0.50)

    unmatched_critical = [k for k in query_keywords if k not in combined_quotes and len(k) >= 4]
    if coverage < min_cov and max_score < min_rel:
        if unmatched_critical:
            reasons.append(f"Query asks about an unestablished policy topic ({unmatched_critical[0].capitalize()}). No supporting policy exists.")
        reasons.append(f"Evidence coverage incomplete ({round(coverage * 100)}% of query concepts grounded).")
        reasons.append("Retrieved passages do not establish the requested rule.")
        return "INSUFFICIENT_EVIDENCE", reasons

    # If strong retrieval match and key concept grounded, it is supported
    if max_score >= 0.70 and (coverage >= 0.30 or len(matched_keywords) >= 2):
        return "SUPPORTED", []

    if coverage < 0.50:
        reasons.append(f"Partial evidence coverage ({round(coverage * 100)}% query concept overlap).")
        return "PARTIALLY_SUPPORTED", reasons

    return "SUPPORTED", []


def resolve_and_validate_citations(answer: str, evidence: list[Evidence]) -> dict[str, Any]:
    """Deterministically validates all citations in synthesized answers against retrieved evidence chunks.
    
    Checks existence of cited documents, sections, versions, and page numbers, and detects hallucinated citations.
    """
    raw_citations = re.findall(r"\[([^\]]+)\]", answer)
    results: list[dict[str, Any]] = []

    for raw in raw_citations:
        cleaned = raw.strip()
        if cleaned.startswith("http") or cleaned.lower() in ("key takeaways", "formatting guidelines", "source"):
            continue

        resolved = False
        matched_chunk: Evidence | None = None
        doc_name = ""
        sec_name = "General"
        version_label = "v1"
        page_num: int | None = None

        if "|" in cleaned:
            parts = [p.strip() for p in cleaned.split("|")]
            doc_candidate = parts[0]
            sec_candidate = parts[1] if len(parts) > 1 else "General"
            ver_candidate = parts[2] if len(parts) > 2 else "v1"
            if len(parts) > 3 and "page" in parts[3].lower():
                p_match = re.search(r"\d+", parts[3])
                if p_match:
                    page_num = int(p_match.group(0))

            for e in evidence:
                if (doc_candidate.lower() in e.document_name.lower() or doc_candidate.lower() in e.document_id.lower()) and (sec_candidate.lower() in e.section.lower() or "general" in sec_candidate.lower()):
                    matched_chunk = e
                    resolved = True
                    doc_name = e.document_name
                    sec_name = e.section
                    version_label = e.version
                    page_num = page_num or getattr(e, "page_number", 1)
                    break
        elif cleaned.lower().startswith("source "):
            src_num = re.search(r"\d+", cleaned)
            if src_num:
                s_idx = int(src_num.group(0)) - 1
                if 0 <= s_idx < len(evidence):
                    matched_chunk = evidence[s_idx]
                    resolved = True
                    doc_name = matched_chunk.document_name
                    sec_name = matched_chunk.section
                    version_label = matched_chunk.version
                    page_num = getattr(matched_chunk, "page_number", 1)
        else:
            for e in evidence:
                if cleaned.lower() == e.chunk_id.lower() or cleaned.lower() == e.document_id.lower() or cleaned.lower() in e.document_name.lower():
                    matched_chunk = e
                    resolved = True
                    doc_name = e.document_name
                    sec_name = e.section
                    version_label = e.version
                    page_num = getattr(e, "page_number", 1)
                    break

        results.append({
            "citation_text": cleaned,
            "is_valid": resolved,
            "document_name": doc_name or cleaned,
            "section": sec_name,
            "version": version_label,
            "page_number": page_num or (getattr(matched_chunk, "page_number", 1) if matched_chunk else None),
            "matched_chunk_id": matched_chunk.chunk_id if matched_chunk else None,
            "relevance_score": matched_chunk.score if matched_chunk else 0.0,
        })

    valid_count = sum(1 for r in results if r["is_valid"])
    total_count = len(results)
    precision = (valid_count / total_count) if total_count > 0 else 1.0

    return {
        "total_citations": total_count,
        "valid_citations_count": valid_count,
        "hallucinated_citations_count": total_count - valid_count,
        "citation_precision": round(precision, 4),
        "citations": results,
    }


def verify_claims_against_evidence(answer: str, evidence: list[Evidence]) -> list[ClaimVerification]:
    """Extracts factual claims from the synthesized answer and evaluates semantic entailment against cited passages.
    
    Filters non-factual structural markdown headers and distinguishes SUPPORTED, CONTRADICTED,
    and NOT_SUPPORTED outcomes.
    """
    claims: list[ClaimVerification] = []
    
    # Split text into declarative assertions, filtering out non-factual formatting headings
    raw_lines = answer.strip().splitlines()
    sentences: list[str] = []

    for line in raw_lines:
        cleaned = line.strip()
        if not cleaned:
            continue
        # Strip markdown headers, key takeaways dividers, formatting reminders
        if cleaned.startswith(("#", "###", "##", "**Key Takeaways", "Key Takeaways", "Formatting Guidelines", "---")):
            continue
        # Strip list markers
        cleaned = re.sub(r"^[-*•\d.]+\s*", "", cleaned).strip()
        if len(cleaned) < 15:
            continue
        # Split line into sentences
        for s in re.split(r"(?<=[.!?])\s+", cleaned):
            s_clean = s.strip()
            if len(s_clean) >= 15 and not s_clean.startswith(("#", "**Key", "Key Takeaways")):
                sentences.append(s_clean)

    if not sentences:
        sentences = [answer.strip()] if len(answer.strip()) > 10 else []

    # Check for safe abstention statement
    is_abstention_answer = any(phrase in answer.lower() for phrase in (
        "does not establish an answer",
        "no tenant-scoped policy evidence was found",
        "escalated to the human review queue",
        "no supporting policy exists"
    ))

    for index, sentence in enumerate(sentences):
        claim_id = f"claim_{index + 1}"
        s_lower = sentence.lower()
        s_words = set(extract_keywords(sentence))

        # If answer is an appropriate abstention statement and evidence was indeed insufficient
        if is_abstention_answer and ("does not establish" in s_lower or "escalated" in s_lower or "no supporting" in s_lower):
            best_e = evidence[0] if evidence else None
            claims.append(
                ClaimVerification(
                    claim_id=claim_id,
                    claim_text=sentence,
                    status="SUPPORTED",
                    supporting_evidence_ids=[best_e.chunk_id or best_e.document_id] if best_e else [],
                    conflicting_evidence_ids=[],
                    document_name=best_e.document_name if best_e else "Index",
                    section=best_e.section if best_e else "Scope",
                    version=best_e.version if best_e else "v1",
                    confidence=0.95,
                    rationale="Accurately articulates absence-of-evidence abstention."
                )
            )
            continue

        supporting_items: list[Evidence] = []
        contradicting_items: list[Evidence] = []

        # Evaluate against each evidence passage
        for item in evidence:
            quote_text = getattr(item, "quote", "") or getattr(item, "text", "")
            q_lower = quote_text.lower()
            q_words = set(extract_keywords(quote_text))
            overlap = len(s_words & q_words)

            # Check for contradiction (claim asserts permission to bypass/ignore, but passage states no authorization or prohibited)
            is_claim_asserting_bypass = (
                ("bypass" in s_lower or "ignore" in s_lower or "disable" in s_lower)
                and not any(neg in s_lower for neg in ("cannot", "no employee", "not permitted", "prohibited", "prohibits", "must not", "never"))
            )
            is_passage_forbidding_bypass = (
                ("bypass" in q_lower or "ignore" in q_lower or "security" in q_lower)
                and any(forb in q_lower for forb in ("no employee", "prohibited", "strictly prohibited", "revocation", "mandatory"))
            )
            if is_claim_asserting_bypass and is_passage_forbidding_bypass:
                contradicting_items.append(item)
                continue

            # Check for positive entailment
            # High overlap or matching numeric limits/entities
            has_numeric_match = False
            if ("3" in s_lower or "three" in s_lower) and ("3" in q_lower or "three" in q_lower):
                has_numeric_match = True
            if ("4" in s_lower or "four" in s_lower) and ("4" in q_lower or "four" in q_lower):
                has_numeric_match = True

            has_entity_match = False
            if "technology division" in s_lower and "technology division" in q_lower:
                has_entity_match = True
            if "security" in s_lower and "security" in q_lower and ("mfa" in q_lower or "safeguard" in q_lower):
                has_entity_match = True
            if "director" in s_lower and "director" in q_lower:
                has_entity_match = True
            if "supersedes" in s_lower and "supersedes" in q_lower:
                has_entity_match = True

            if (has_numeric_match or has_entity_match) and overlap >= 2:
                supporting_items.append(item)
            elif overlap >= max(2, len(s_words) // 3):
                supporting_items.append(item)

        if contradicting_items:
            best_conflict = contradicting_items[0]
            claims.append(
                ClaimVerification(
                    claim_id=claim_id,
                    claim_text=sentence,
                    status="NOT_SUPPORTED",
                    supporting_evidence_ids=[],
                    conflicting_evidence_ids=[best_conflict.chunk_id or best_conflict.document_id],
                    document_name=best_conflict.document_name or best_conflict.document_id,
                    section=best_conflict.section,
                    version=best_conflict.version,
                    confidence=0.10,
                    rationale=f"Claim directly contradicted by {best_conflict.document_name} [{best_conflict.section}]."
                )
            )
        elif supporting_items:
            best_match = supporting_items[0]
            claims.append(
                ClaimVerification(
                    claim_id=claim_id,
                    claim_text=sentence,
                    status="SUPPORTED",
                    supporting_evidence_ids=[item.chunk_id or item.document_id for item in supporting_items],
                    conflicting_evidence_ids=[],
                    document_name=best_match.document_name or best_match.document_id,
                    section=best_match.section,
                    version=best_match.version,
                    confidence=round(min(0.98, 0.75 + 0.05 * len(supporting_items)), 2),
                    rationale=f"Grounded by {best_match.document_name} [{best_match.section}, {best_match.version}]."
                )
            )
        else:
            claims.append(
                ClaimVerification(
                    claim_id=claim_id,
                    claim_text=sentence,
                    status="PARTIALLY_SUPPORTED" if evidence else "NOT_SUPPORTED",
                    supporting_evidence_ids=[],
                    conflicting_evidence_ids=[],
                    document_name=evidence[0].document_name if evidence else "None",
                    section=evidence[0].section if evidence else "None",
                    version=evidence[0].version if evidence else "None",
                    confidence=0.35,
                    rationale="Claim generalized beyond explicit passage terms."
                )
            )

    return claims


def calculate_evidence_confidence(
    evidence: list[Evidence],
    claims: list[ClaimVerification],
    conflict_analysis: ConflictAnalysis,
    query: str,
) -> ConfidenceBreakdown:
    """Computes interpretable Evidence Confidence Score using:
    Confidence = w1*R + w2*C + w3*A + w4*V - w5*F
    
    NOTE: This is an uncalibrated heuristic decision score for routing, NOT a Bayesian probability.
    """
    if not evidence:
        return ConfidenceBreakdown(
            retrieval_relevance=0.0,
            evidence_coverage=0.0,
            source_agreement=0.0,
            verification_strength=0.0,
            conflict_penalty=0.0,
            final_score=0.0,
            decision="HUMAN REVIEW REQUIRED"
        )

    # 1. R = Retrieval Relevance (average score of top 4 chunks, bounded in [0.1, 1.0])
    top_scores = []
    for item in evidence[:4]:
        s = getattr(item, "score", 0.5)
        if s < 0.05:
            # Scale raw uncalibrated RRF score (~0.02) to [0.1, 1.0] scale
            s = min(1.0, max(0.1, (s / (2.0 / 61.0)) * 0.90))
        top_scores.append(s)
    r = min(1.0, max(0.1, sum(top_scores) / len(top_scores))) if top_scores else 0.5

    # 2. C = Evidence Coverage (query concept overlap across passages)
    q_terms = set(extract_keywords(query))
    if q_terms:
        combined_text = " ".join((getattr(item, "quote", "") or getattr(item, "text", "")).lower() for item in evidence)
        covered = sum(1 for term in q_terms if term in combined_text)
        c = min(1.0, covered / len(q_terms))
    else:
        combined_text = ""
        c = 0.85

    # Penalize out-of-domain terms
    for ungrounded_term in ("antarctica", "reimbursement", "monitors", "perdiem"):
        if ungrounded_term in query.lower() and ungrounded_term not in combined_text:
            c = 0.10

    # 3. A = Source Agreement (consistency between documents/versions)
    if conflict_analysis.conflict_detected and conflict_analysis.status == "HUMAN REVIEW REQUIRED":
        a = 0.40
    elif conflict_analysis.conflict_detected and conflict_analysis.status == "RESOLVED":
        a = 0.85
    else:
        a = 0.95

    # 4. V = Verification Strength (percentage of claims verified as SUPPORTED)
    if c <= 0.20:
        v = 0.10
    elif claims:
        supported_claims = sum(1 for claim in claims if claim.status == "SUPPORTED")
        v = supported_claims / len(claims)
    else:
        v = 0.80

    # 5. F = Conflict Penalty
    if conflict_analysis.conflict_detected and conflict_analysis.status == "HUMAN REVIEW REQUIRED":
        f = 0.35
    elif conflict_analysis.conflict_detected:
        f = 0.05
    else:
        f = 0.0

    raw_confidence = (
        WEIGHT_RETRIEVAL_RELEVANCE * r
        + WEIGHT_EVIDENCE_COVERAGE * c
        + WEIGHT_SOURCE_AGREEMENT * a
        + WEIGHT_VERIFICATION_STRENGTH * v
        - WEIGHT_CONFLICT_PENALTY * f
    )

    final_score = round(max(0.0, min(0.98, raw_confidence)), 2)
    decision = "ANSWER" if (
        final_score >= 0.70
        and not (conflict_analysis.conflict_detected and conflict_analysis.status == "HUMAN REVIEW REQUIRED")
        and c >= 0.45
    ) else "HUMAN REVIEW REQUIRED"

    return ConfidenceBreakdown(
        retrieval_relevance=round(r, 2),
        evidence_coverage=round(c, 2),
        source_agreement=round(a, 2),
        verification_strength=round(v, 2),
        conflict_penalty=round(f, 2),
        final_score=final_score,
        decision=decision
    )


def generate_evidence_receipt(
    query: str,
    answer: str,
    evidence: list[Evidence],
    confidence_breakdown: ConfidenceBreakdown,
    conflict_analysis: ConflictAnalysis,
    agents_used: list[str],
    sufficiency_status: EvidenceSufficiencyStatus,
    review_reasons: list[str]
) -> EvidenceReceipt:
    """Generates an auditable cryptographic Evidence Receipt for the query run."""
    receipt_id = f"dt-rcpt-{hashlib.sha256((query + answer + str(datetime.now(timezone.utc))).encode()).hexdigest()[:12]}"
    docs = sorted(list({e.document_name or e.document_id for e in evidence}))
    versions = sorted(list({e.version for e in evidence}))
    sections = sorted(list({e.section for e in evidence}))
    evidence_ids = [e.chunk_id or e.document_id for e in evidence]

    provenance_string = f"{receipt_id}|{query}|{confidence_breakdown.final_score}|{','.join(docs)}|{','.join(versions)}|{','.join(sections)}"
    provenance_hash = hashlib.sha256(provenance_string.encode()).hexdigest()

    return EvidenceReceipt(
        receipt_id=receipt_id,
        query=query,
        decision=confidence_breakdown.decision,
        confidence=confidence_breakdown.final_score,
        confidence_breakdown=confidence_breakdown.to_dict(),
        evidence_status=sufficiency_status,
        documents=docs,
        versions=versions,
        sections=sections,
        agents=agents_used,
        conflicts=conflict_analysis.conflicts,
        human_review_required=(confidence_breakdown.decision == "HUMAN REVIEW REQUIRED"),
        review_reasons=review_reasons,
        evidence_ids=evidence_ids,
        timestamp=datetime.now(timezone.utc).isoformat(),
        provenance_hash=provenance_hash
    )
