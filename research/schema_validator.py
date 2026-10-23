"""
DocuTrust Benchmark Schema Validator
Validates benchmark JSON Lines files against research/BENCHMARK_SCHEMA.md specifications.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

VALID_CATEGORIES = {
    "direct_fact",
    "multihop_reasoning",
    "version_supersession",
    "cross_doc_conflict",
    "insufficient_evidence",
    "ambiguous_authority",
    "prompt_injection",
    "tenant_isolation",
    "citation_attribution",
    "scope_boundary",
}

VALID_DECISIONS = {"ANSWER", "ABSTAIN", "ESCALATE_REVIEW"}
VALID_SPLITS = {"dev", "test"}

REQUIRED_FIELDS = [
    "id",
    "category",
    "query",
    "tenant_id",
    "policy_family",
    "corpus_documents",
    "gold_chunk_ids",
    "graded_relevance",
    "expected_decision",
    "gold_answer",
    "gold_claims",
    "conflict_present",
    "conflicting_chunk_pairs",
    "active_version",
    "superseded_versions",
    "escalation_required",
    "escalation_reasons",
    "split",
    "is_answerable",
]


class BenchmarkValidationError(Exception):
    pass


def validate_benchmark_item(item: dict[str, Any], index: int = 0) -> list[str]:
    errors: list[str] = []
    item_id = item.get("id", f"item_at_index_{index}")

    # 1. Required fields presence
    for field in REQUIRED_FIELDS:
        if field not in item:
            errors.append(f"[{item_id}] Missing required field '{field}'")

    if errors:
        return errors

    # 2. Field Types & Enums
    if not isinstance(item["id"], str) or not re.match(r"^DT-BENCH-\d{3,}$", item["id"]):
        errors.append(f"[{item_id}] 'id' must match format 'DT-BENCH-XXX'")

    if item["category"] not in VALID_CATEGORIES:
        errors.append(f"[{item_id}] Invalid category '{item['category']}'. Must be one of {sorted(VALID_CATEGORIES)}")

    if not isinstance(item["query"], str) or len(item["query"].strip()) < 5:
        errors.append(f"[{item_id}] 'query' must be a non-empty string with at least 5 characters")

    if item["expected_decision"] not in VALID_DECISIONS:
        errors.append(f"[{item_id}] Invalid expected_decision '{item['expected_decision']}'. Must be one of {sorted(VALID_DECISIONS)}")

    if item["split"] not in VALID_SPLITS:
        errors.append(f"[{item_id}] Invalid split '{item['split']}'. Must be 'dev' or 'test'")

    if not isinstance(item["is_answerable"], bool):
        errors.append(f"[{item_id}] 'is_answerable' must be a boolean")

    if not isinstance(item["gold_chunk_ids"], list):
        errors.append(f"[{item_id}] 'gold_chunk_ids' must be a list")

    if not isinstance(item["graded_relevance"], dict):
        errors.append(f"[{item_id}] 'graded_relevance' must be a dict")
    else:
        for cid, grade in item["graded_relevance"].items():
            if grade not in (0, 1, 2):
                errors.append(f"[{item_id}] Graded relevance for chunk '{cid}' must be 0, 1, or 2 (got {grade})")

    # 3. Semantic Consistency Invariants
    is_answerable = item["is_answerable"]
    gold_chunks = item.get("gold_chunk_ids", [])

    if not is_answerable:
        if len(gold_chunks) > 0:
            errors.append(f"[{item_id}] Unanswerable queries must have empty 'gold_chunk_ids' (got {len(gold_chunks)})")
        if item["expected_decision"] not in ("ABSTAIN", "ESCALATE_REVIEW"):
            errors.append(f"[{item_id}] Unanswerable queries must expect ABSTAIN or ESCALATE_REVIEW (got {item['expected_decision']})")
        if not item["escalation_required"]:
            errors.append(f"[{item_id}] Unanswerable queries must require review escalation (escalation_required=True)")
    else:
        if len(gold_chunks) == 0:
            errors.append(f"[{item_id}] Answerable queries must have at least one gold chunk in 'gold_chunk_ids'")
        for cid in gold_chunks:
            if item.get("graded_relevance", {}).get(cid, 0) < 1:
                errors.append(f"[{item_id}] Gold chunk '{cid}' must have graded relevance >= 1")

    if item["escalation_required"] and not item.get("escalation_reasons"):
        errors.append(f"[{item_id}] 'escalation_reasons' must be non-empty when escalation_required is True")

    if item["conflict_present"]:
        pairs = item.get("conflicting_chunk_pairs", [])
        if not pairs and item["category"] == "cross_doc_conflict":
            errors.append(f"[{item_id}] Category 'cross_doc_conflict' must list at least one conflicting chunk pair")

    # 4. Leakage & Split Isolation Invariant
    if item["split"] == "dev" and item.get("policy_family") != "remote_work":
        errors.append(f"[{item_id}] Dev split is reserved exclusively for 'remote_work' family to guarantee domain generalization")

    return errors


def validate_benchmark_file(file_path: str | Path) -> dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {path}")

    all_errors: list[str] = []
    items: list[dict[str, Any]] = []

    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                items.append(item)
                item_errors = validate_benchmark_item(item, index=idx)
                all_errors.extend(item_errors)
            except json.JSONDecodeError as err:
                all_errors.append(f"[Line {idx}] JSON decode error: {err}")

    # Global dataset-level checks
    id_counts: dict[str, int] = {}
    for it in items:
        cid = it.get("id", "UNKNOWN")
        id_counts[cid] = id_counts.get(cid, 0) + 1

    duplicate_ids = [cid for cid, count in id_counts.items() if count > 1]
    if duplicate_ids:
        all_errors.append(f"Duplicate IDs found in benchmark: {duplicate_ids}")

    dev_count = sum(1 for it in items if it.get("split") == "dev")
    test_count = sum(1 for it in items if it.get("split") == "test")

    return {
        "valid": len(all_errors) == 0,
        "total_items": len(items),
        "dev_count": dev_count,
        "test_count": test_count,
        "errors": all_errors,
    }


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "research/docutrust_bench_pilot.jsonl"
    print(f"Validating benchmark: {target}")
    summary = validate_benchmark_file(target)
    print(f"Validation Result: {'PASS' if summary['valid'] else 'FAIL'}")
    print(f"Total Items: {summary['total_items']} (Dev: {summary['dev_count']}, Test: {summary['test_count']})")
    if summary["errors"]:
        print(f"Found {len(summary['errors'])} errors:")
        for err in summary["errors"][:10]:
            print(f"  - {err}")
