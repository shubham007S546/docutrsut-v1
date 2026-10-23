# DocuTrust Benchmark Dataset Specification: Schema and Field Definitions

**Dataset Name:** `DocuTrust-Bench`  
**Standard Version:** 1.0.0  
**Storage Format:** JSON Lines (`.jsonl`)  
**Target Sample Count:** 400 instances (Balanced across 10 categories)

---

## 1. Schema Definition

Each instance in `DocuTrust-Bench` represents a compliance inquiry evaluated under strict multi-tenant boundaries.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "DocuTrustBenchmarkItem",
  "type": "object",
  "required": [
    "id",
    "category",
    "query",
    "tenant_id",
    "corpus_documents",
    "gold_chunk_ids",
    "expected_decision",
    "gold_claims",
    "conflict_present",
    "active_version",
    "escalation_required"
  ],
  "properties": {
    "id": {
      "type": "string",
      "description": "Unique stable identifier (e.g., DT-BENCH-001)"
    },
    "category": {
      "type": "string",
      "enum": [
        "direct_fact",
        "multihop_reasoning",
        "version_supersession",
        "cross_doc_conflict",
        "insufficient_evidence",
        "ambiguous_authority",
        "prompt_injection",
        "tenant_isolation",
        "citation_attribution",
        "scope_boundary"
      ]
    },
    "query": {
      "type": "string",
      "description": "The exact natural language inquiry submitted by the user"
    },
    "tenant_id": {
      "type": "string",
      "description": "Tenant identifier establishing authorization scope"
    },
    "corpus_documents": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Document names relevant to this inquiry"
    },
    "gold_chunk_ids": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Passage chunk IDs containing definitive evidentiary support (empty if unanswerable)"
    },
    "graded_relevance": {
      "type": "object",
      "additionalProperties": { "type": "integer", "minimum": 0, "maximum": 2 },
      "description": "Mapping of chunk_id to relevance grade: 0=irrelevant, 1=partially related, 2=definitive support"
    },
    "expected_decision": {
      "type": "string",
      "enum": ["ANSWER", "ABSTAIN", "ESCALATE_REVIEW"]
    },
    "gold_answer": {
      "type": "string",
      "description": "Human-adjudicated reference answer (or standard abstention refusal phrase)"
    },
    "gold_claims": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["claim_text", "supporting_chunk_ids"],
        "properties": {
          "claim_text": { "type": "string" },
          "supporting_chunk_ids": { "type": "array", "items": { "type": "string" } },
          "critical": { "type": "boolean" }
        }
      }
    },
    "conflict_present": {
      "type": "boolean",
      "description": "Whether a contradiction exists between rules, scopes, or document versions"
    },
    "conflicting_chunk_pairs": {
      "type": "array",
      "items": {
        "type": "array",
        "items": { "type": "string" },
        "minItems": 2,
        "maxItems": 2
      },
      "description": "Pairs of chunk IDs that assert contradictory requirements"
    },
    "active_version": {
      "type": "string",
      "description": "The authoritative active policy version (e.g., 'v2')"
    },
    "superseded_versions": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Outdated versions that must NOT be cited as current policy"
    },
    "escalation_required": {
      "type": "boolean",
      "description": "True if system should trigger the Human Review Queue"
    },
    "escalation_reasons": {
      "type": "array",
      "items": { "type": "string" }
    },
    "split": {
      "type": "string",
      "enum": ["dev", "test"]
    }
  }
}
```

---

## 2. Dataset Partitioning & Leakage Prevention Rules

1. **Policy-Family Splitting:**
   - Development Set (Dev): 30% (120 queries).
   - Test Set (Test): 70% (280 queries).
   - The test set is partitioned by policy family (e.g., IT Security and Remote Work in Dev; Data Privacy, Procurement, and Financial Compliance in Test) to ensure models and heuristics are evaluated on unseen policy domains.

2. **Zero Information Leakage:**
   - Test passages and queries are strictly isolated during tuning.
   - Ground truth chunk IDs are decoupled from retrieval index names.
