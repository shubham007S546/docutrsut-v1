from __future__ import annotations

import uuid
import datetime
from dataclasses import dataclass, field, asdict
from typing import Literal, Any

ClaimStatus = Literal["SUPPORTED", "NOT_SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED"]
EvidenceSufficiencyStatus = Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "CONFLICTING", "INSUFFICIENT_EVIDENCE", "UNVERIFIED"]
AgentKind = Literal["supervisor", "policy", "privacy", "security", "legal", "conflict", "verification", "report"]
ActionKind = Literal["retrieve_more_evidence", "ask_specialist", "verify_claims", "resolve_conflict", "finish", "request_human_review"]


@dataclass
class Evidence:
    document_id: str
    version: str
    section: str
    quote: str
    start: int = 0
    end: int = 0
    score: float = 0.0
    retrieval_method: str = "hybrid_rag"
    document_name: str = ""
    tenant_id: str = ""
    chunk_id: str = ""
    effective_from: str = "2024-01-01"
    effective_to: str = "Present"
    page_number: int | None = 1
    page_start: int | None = 1
    page_end: int | None = 1
    bm25_score: float = 0.0
    faiss_score: float = 0.0
    rrf_score: float = 0.0
    ce_score: float | None = None
    retrieval_diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConfidenceBreakdown:
    retrieval_relevance: float  # R (0.0 - 1.0)
    evidence_coverage: float    # C (0.0 - 1.0)
    source_agreement: float     # A (0.0 - 1.0)
    verification_strength: float # V (0.0 - 1.0)
    conflict_penalty: float     # F (0.0 - 1.0)
    final_score: float          # Combined formula: w1*R + w2*C + w3*A + w4*V - w5*F
    decision: str               # "ANSWER" | "HUMAN REVIEW REQUIRED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClaimVerification:
    claim_id: str
    claim_text: str
    status: ClaimStatus
    supporting_evidence_ids: list[str] = field(default_factory=list)
    conflicting_evidence_ids: list[str] = field(default_factory=list)
    document_name: str = ""
    section: str = ""
    version: str = ""
    confidence: float = 0.0
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConflictAnalysis:
    conflict_detected: bool = False
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    status: Literal["NONE", "RESOLVED", "UNRESOLVED", "HUMAN REVIEW REQUIRED"] = "NONE"
    resolution_reason: str = ""
    affected_departments: list[str] = field(default_factory=list)

    @property
    def precedence_resolution(self) -> str:
        return self.resolution_reason

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["precedence_resolution"] = self.resolution_reason
        return data


@dataclass
class PolicyImpactAnalysis:
    policy_name: str
    previous_version: str
    current_version: str
    effective_date: str
    changed_topics: list[str] = field(default_factory=list)
    affected_rules: list[str] = field(default_factory=list)
    affected_departments: list[str] = field(default_factory=list)
    affected_questions: list[str] = field(default_factory=list)
    impact_level: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceReceipt:
    receipt_id: str
    query: str
    decision: str
    confidence: float
    confidence_breakdown: dict[str, Any]
    evidence_status: str
    documents: list[str]
    versions: list[str]
    sections: list[str]
    agents: list[str]
    conflicts: list[dict[str, Any]]
    human_review_required: bool
    review_reasons: list[str]
    evidence_ids: list[str]
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    provenance_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PlanTask:
    task: str
    agent: AgentKind
    priority: int
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentPlan:
    goal: str
    subtasks: list[PlanTask]
    selected_tools: list[str]
    execution_order: list[str]
    success_criteria: list[str]
    intent: str = "policy_question"
    risk_level: Literal["low", "medium", "high"] = "medium"
    planner_mode: Literal["llm", "supervisor"] = "supervisor"
    rationale: str = ""
    max_iterations: int = 3
    current_step: int = 0
    status: Literal["planned", "executing", "completed", "needs_review"] = "planned"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReflectionResult:
    answer_complete: bool
    evidence_sufficient: bool
    unsupported_claims: list[str]
    conflicts: list[str]
    next_action: ActionKind
    confidence: float
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolCall:
    name: str
    arguments: dict
    result_summary: str
    iteration: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentResult:
    agent: AgentKind
    status: Literal["completed", "failed", "skipped"]
    answer: str
    confidence: float
    reason_for_selection: str = ""
    claims: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    requires_review: bool = False
    evidence: list[Evidence] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    model: str | None = None
    latency_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunState:
    run_id: str
    tenant_id: str
    query: str
    mode: Literal["private", "public_demo"] = "private"
    goal: str = ""
    intent: str = "policy_analysis"
    plan: AgentPlan | None = None
    agents: list[AgentResult] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    reflections: list[ReflectionResult] = field(default_factory=list)
    completed_tasks: list[str] = field(default_factory=list)
    pending_tasks: list[str] = field(default_factory=list)
    requires_review: bool = False
    review_reasons: list[str] = field(default_factory=list)
    final_answer: str | None = None
    overall_confidence: float = 0.0
    confidence_breakdown: ConfidenceBreakdown | None = None
    evidence_state: dict[str, Any] = field(default_factory=dict)
    claim_verifications: list[ClaimVerification] = field(default_factory=list)
    conflict_analysis: ConflictAnalysis = field(default_factory=ConflictAnalysis)
    receipt: EvidenceReceipt | None = None
    observations: list[dict[str, Any]] = field(default_factory=list)
    retrieval_diagnostics: dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)

    def emit(self, event_type: str, **payload: object) -> None:
        event = {"type": event_type, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), **payload}
        self.events.append(event)

    def add_tool_call(self, name: str, arguments: dict, result_summary: str, iteration: int) -> None:
        self.tool_calls.append(ToolCall(name, arguments, result_summary, iteration))
        self.emit("tool_completed", tool=name, arguments=arguments, result_summary=result_summary, iteration=iteration)

    def add_reflection(self, reflection: ReflectionResult) -> None:
        self.reflections.append(reflection)
        self.emit("reflection", **asdict(reflection))


def plan_to_dict(plan: AgentPlan | None) -> dict | None:
    return asdict(plan) if plan else None

def result_to_dict(result: AgentResult) -> dict:
    return asdict(result)

def reflection_to_dict(result: ReflectionResult | None) -> dict | None:
    return asdict(result) if result else None

MAX_ITERATIONS = 3
MAX_TOOL_CALLS = 12
MAX_TOKEN_BUDGET = 12000
SAFE_TOOLS = {
    "analyze_intent",
    "search_documents",
    "retrieve_document_sections",
    "inspect_document_metadata",
    "check_evidence_sufficiency",
    "detect_conflicts",
    "verify_claims_against_evidence",
    "calculate_evidence_confidence",
    "generate_evidence_receipt",
    "request_human_review",
    "policy_version_impact"
}
