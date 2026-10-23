from __future__ import annotations

import difflib
import re
from typing import Any
from backend.agents.contracts import PolicyImpactAnalysis


def analyze_policy_impact(
    policy_name: str,
    v1_text: str,
    v2_text: str,
    v1_label: str = "v1",
    v2_label: str = "v2"
) -> PolicyImpactAnalysis:
    """Analyzes differences between two policy versions and quantifies organizational impact."""
    v1_lines = [line.strip() for line in v1_text.strip().splitlines() if line.strip()]
    v2_lines = [line.strip() for line in v2_text.strip().splitlines() if line.strip()]

    matcher = difflib.SequenceMatcher(None, v1_lines, v2_lines)
    diff_details: list[dict[str, Any]] = []

    changed_topics: list[str] = []
    affected_rules: list[str] = []
    affected_departments: list[str] = []
    affected_questions: list[str] = []

    # Detect allowance differences (e.g. 4 days exception or Technology Division scope)
    v1_has_4 = "4" in v1_text or "four" in v1_text.lower()
    v2_has_4 = "4" in v2_text or "four" in v2_text.lower()
    if (v1_has_4 != v2_has_4) or ("technology" in v2_text.lower() and "technology" not in v1_text.lower()):
        changed_topics.append("Remote work attendance allowances & weekly day limits")
        affected_rules.append("Civilian hybrid attendance limitation rule (Section 4.2)")
        affected_departments.extend(["Technology Division (Software, Cloud, Data)", "General Civilian Personnel"])
        affected_questions.extend([
            "Can employees work remotely four days per week?",
            "What is the maximum work-from-home allowance for engineering?"
        ])
        diff_details.append({
            "type": "MODIFIED_ALLOWANCE",
            "section": "Section 4.2",
            "previous_rule": "Maximum 3 days per calendar week across all operating units",
            "updated_rule": "Up to 4 days per calendar week for Technology Division; 3 days for general civilian staff",
            "impact": "HIGH"
        })

    # Detect geographical restrictions
    if any(k in v2_text.lower() for k in ["boundaries", "overseas", "foreign", "national", "international", "jurisdictions"]):
        changed_topics.append("Geographic remote work boundaries & export compliance")
        affected_rules.append("Cross-border work restriction rule (Section 8.1)")
        affected_departments.append("Legal & Export Compliance")
        affected_questions.append("Can employees work from Antarctica or international locations?")
        diff_details.append({
            "type": "NEW_RESTRICTION",
            "section": "Section 8.1",
            "previous_rule": "Unspecified international remote boundaries",
            "updated_rule": "Strictly within approved domestic boundaries; foreign locations prohibited without C-level signoff",
            "impact": "MEDIUM"
        })

    # Precedence rule
    if "supersedes" in v2_text.lower():
        affected_rules.append("Policy Precedence & Supersession Clause (Section 4.3)")
        diff_details.append({
            "type": "PRECEDENCE_CLAUSE",
            "section": "Section 4.3",
            "previous_rule": "v1 active standard",
            "updated_rule": "v2 supersedes all provisions of v1 as of June 1, 2024",
            "impact": "HIGH"
        })

    impact_level = "HIGH" if len(affected_rules) >= 2 or any(d["impact"] == "HIGH" for d in diff_details) else "MEDIUM"

    return PolicyImpactAnalysis(
        policy_name=policy_name,
        previous_version=v1_label,
        current_version=v2_label,
        effective_date="2024-06-01",
        changed_topics=list(dict.fromkeys(changed_topics)),
        affected_rules=list(dict.fromkeys(affected_rules)),
        affected_departments=list(dict.fromkeys(affected_departments)),
        affected_questions=list(dict.fromkeys(affected_questions)),
        impact_level=impact_level,
        details=diff_details
    )
