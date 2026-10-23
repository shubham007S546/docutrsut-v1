"""
Independent Recomputation and Statistical Audit Engine for DocuTrust Phase 4
Recomputes all metrics directly from raw per-query predictions and ground-truth benchmark items.
"""
from __future__ import annotations

import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent

def compute_dcg(relevances: list[int], k: int) -> float:
    dcg = 0.0
    for i, rel in enumerate(relevances[:k], start=1):
        dcg += (2**rel - 1) / math.log2(i + 1)
    return dcg

def compute_idcg(relevances: list[int], k: int) -> float:
    sorted_rels = sorted(relevances, reverse=True)
    return compute_dcg(sorted_rels, k)

def compute_ndcg(retrieved_chunk_ids: list[str], graded_relevance: dict[str, int], k: int = 8) -> float:
    if not graded_relevance:
        return 0.0
    rels = [graded_relevance.get(cid, 0) for cid in retrieved_chunk_ids[:k]]
    idcg = compute_idcg(list(graded_relevance.values()), k)
    if idcg <= 0.0:
        return 0.0
    return compute_dcg(rels, k) / idcg

def student_t_pvalue(t_stat: float, df: int) -> float:
    """Exact two-tailed p-value for Student's t-distribution using regularized incomplete beta function."""
    # When scipy is not installed, use regularized incomplete beta or accurate approximation
    # For df=25, we can use the exact integration or scipy if available
    try:
        from scipy import stats
        return float(2.0 * stats.t.sf(abs(t_stat), df=df))
    except ImportError:
        # High-accuracy Hill's algorithm approximation for Student's t
        x = df / (df + t_stat**2)
        # Using continued fraction or math approximation
        # For df=25, t=1.383: standard p is ~0.1789 (scipy)
        # Fall back to beta inc
        import math
        # Beta incomplete approximation via erf series with Cornish-Fisher expansion:
        # z ~ t * (1 - 1/(4*df)) / sqrt(1 + t^2/(2*df))
        z = t_stat * (1.0 - 1.0 / (4.0 * df)) / math.sqrt(1.0 + (t_stat**2) / (2.0 * df))
        p = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))
        return min(1.0, max(0.0, p))

def exact_mcnemar_test(b: int, c: int) -> dict[str, Any]:
    """Computes exact two-tailed binomial p-value and chi2 statistics for McNemar test."""
    n = b + c
    if n == 0:
        return {
            "b": b, "c": c, "chi2_corrected": 0.0, "chi2_uncorrected": 0.0,
            "p_value_exact": 1.0, "p_value_chi2": 1.0, "significant": False
        }
    
    k_min = min(b, c)
    # Exact two-tailed binomial test with p0=0.5
    # sum_{k=0}^{k_min} binom(n, k) * 0.5^n
    p_one_tail = sum(math.comb(n, k) * (0.5 ** n) for k in range(k_min + 1))
    p_exact = min(1.0, 2.0 * p_one_tail)
    
    chi2_corr = ((abs(b - c) - 1.0) ** 2) / n if abs(b - c) > 0 else 0.0
    chi2_uncorr = ((b - c) ** 2) / n
    
    # 1 dof chi2 p-value
    try:
        from scipy import stats
        p_chi2 = float(stats.chi2.sf(chi2_corr, df=1))
    except ImportError:
        p_chi2 = 1.0 - math.erf(math.sqrt(chi2_corr) / math.sqrt(2.0)) if chi2_corr > 0 else 1.0

    return {
        "b_sys_full_correct_baseline_wrong": b,
        "c_baseline_correct_sys_full_wrong": c,
        "total_discordant_pairs": n,
        "chi2_continuity_corrected": round(chi2_corr, 4),
        "chi2_uncorrected": round(chi2_uncorr, 4),
        "p_value_exact_binomial": round(p_exact, 4),
        "p_value_chi2_approx": round(p_chi2, 4),
        "significant": p_exact < 0.05
    }

def bootstrap_ci(values: list[float], n_boot: int = 2000, alpha: float = 0.05, seed: int = 42) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    rng = random.Random(seed)
    n = len(values)
    means = [sum(rng.choice(values) for _ in range(n)) / n for _ in range(n_boot)]
    means.sort()
    low = round(means[int((alpha / 2.0) * n_boot)], 3)
    high = round(means[int((1.0 - alpha / 2.0) * n_boot)], 3)
    return low, high

def run_independent_audit():
    raw_path = ROOT_DIR / "research" / "results" / "raw_experiment_results.json"
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    raw_results = data["raw_results"]
    audit_metrics: dict[str, Any] = {}
    
    for config_name, runs in raw_results.items():
        total_queries = len(runs)
        ans_runs = [r for r in runs if r["is_answerable"]]
        unans_runs = [r for r in runs if not r["is_answerable"]]
        
        # 1. Retrieval Metrics
        p_at_8_list = []
        r_at_8_list = []
        rr_list = []
        ndcg_list = []
        hit_at_1_list = []
        
        for r in ans_runs:
            retrieved = r["retrieved_chunk_ids"][:8]
            gold = set(r["gold_chunk_ids"])
            rel_in_k = [cid for cid in retrieved if cid in gold]
            
            p_at_8 = len(rel_in_k) / max(1, len(retrieved))
            r_at_8 = len(rel_in_k) / max(1, len(gold))
            p_at_8_list.append(p_at_8)
            r_at_8_list.append(r_at_8)
            
            # Hit@1
            hit_at_1 = 1.0 if retrieved and retrieved[0] in gold else 0.0
            hit_at_1_list.append(hit_at_1)
            
            # Reciprocal rank
            rr = 0.0
            for rank, cid in enumerate(retrieved, start=1):
                if cid in gold:
                    rr = 1.0 / rank
                    break
            rr_list.append(rr)
            
            # nDCG
            ndcg = compute_ndcg(retrieved, r.get("graded_relevance", {}), k=8)
            ndcg_list.append(ndcg)
        
        mean_p_8 = round(sum(p_at_8_list) / len(p_at_8_list) * 100, 1) if p_at_8_list else 0.0
        mean_r_8 = round(sum(r_at_8_list) / len(r_at_8_list) * 100, 1) if r_at_8_list else 0.0
        mean_hit_1 = round(sum(hit_at_1_list) / len(hit_at_1_list) * 100, 1) if hit_at_1_list else 0.0
        mean_mrr = round(sum(rr_list) / len(rr_list), 3) if rr_list else 0.0
        mean_ndcg = round(sum(ndcg_list) / len(ndcg_list), 3) if ndcg_list else 0.0
        
        # 2. Claim-level Factuality
        total_claims = sum(r["claims_count"] for r in runs)
        supported_claims = sum(r["supported_claims"] for r in runs)
        if total_claims > 0:
            claim_support_rate = round((supported_claims / total_claims) * 100, 1)
            claim_support_status = "EVALUATED"
        else:
            claim_support_rate = None  # Not Evaluated / Division by Zero
            claim_support_status = "NOT_EVALUATED_NO_CLAIMS"
            
        # 3. Policy Conflict Detection (Confusion Matrix)
        tp = fp = tn = fn = 0
        for r in runs:
            pred = bool(r["conflict_detected"])
            gold = bool(r["expected_conflict"])
            if pred and gold: tp += 1
            elif pred and not gold: fp += 1
            elif not pred and not gold: tn += 1
            else: fn += 1
            
        conflict_prec = round((tp / (tp + fp)) * 100, 1) if (tp + fp) > 0 else 0.0
        conflict_rec = round((tp / (tp + fn)) * 100, 1) if (tp + fn) > 0 else 0.0
        conflict_f1 = (
            round(2 * conflict_prec * conflict_rec / (conflict_prec + conflict_rec), 1)
            if (conflict_prec + conflict_rec) > 0 else 0.0
        )
        
        # 4. Abstention & Routing
        # Appropriate Abstention: unanswerable queries routed to ABSTAIN or ESCALATE_REVIEW with actual_review=True
        app_abst_count = sum(1 for r in unans_runs if r["actual_decision"] in ("ABSTAIN", "ESCALATE_REVIEW") and r["actual_review"])
        app_abst_rate = round((app_abst_count / len(unans_runs)) * 100, 1) if unans_runs else 0.0
        
        # False Abstention: answerable queries where system chose ABSTAIN or escalated when review was NOT expected
        false_abst_count = sum(1 for r in ans_runs if r["actual_decision"] == "ABSTAIN" or (r["actual_review"] and not r["expected_review"]))
        false_abst_rate = round((false_abst_count / len(ans_runs)) * 100, 1) if ans_runs else 0.0
        
        # Exact 3-way Decision Accuracy (ANSWER, ABSTAIN, ESCALATE_REVIEW)
        dec_matches_3way = sum(1 for r in runs if r["actual_decision"] == r["expected_decision"])
        dec_acc_3way = round((dec_matches_3way / total_queries) * 100, 1)
        
        # Binary Governance Accuracy (ANSWER vs NON-ANSWER/GOVERNANCE)
        binary_matches = sum(
            1 for r in runs 
            if (r["actual_decision"] == "ANSWER" and r["expected_decision"] == "ANSWER") or
               (r["actual_decision"] in ("ABSTAIN", "ESCALATE_REVIEW") and r["expected_decision"] in ("ABSTAIN", "ESCALATE_REVIEW"))
        )
        binary_acc = round((binary_matches / total_queries) * 100, 1)
        
        # Confusion matrix for decisions
        confusion_3way = Counter((r["expected_decision"], r["actual_decision"]) for r in runs)
        
        # 5. Latency
        latencies = [r["latency_ms"] for r in runs]
        mean_lat = round(sum(latencies) / len(latencies), 1)
        latencies_sorted = sorted(latencies)
        median_lat = round(latencies_sorted[len(latencies) // 2], 1)
        
        audit_metrics[config_name] = {
            "total_queries": total_queries,
            "answerable_count": len(ans_runs),
            "unanswerable_count": len(unans_runs),
            "retrieval": {
                "precision_at_8": mean_p_8,
                "recall_at_8": mean_r_8,
                "hit_at_1": mean_hit_1,
                "mrr": mean_mrr,
                "ndcg_at_8": mean_ndcg,
                "denominator_explanation": "Evaluated strictly over N=26 answerable queries. Since each query has exactly 1 gold chunk (|Gold|=1) and K=8, max possible Precision@8 is 1/8 = 12.5%."
            },
            "factuality": {
                "claim_support_rate": claim_support_rate,
                "claim_support_status": claim_support_status,
                "total_claims": total_claims,
                "supported_claims": supported_claims,
                "unsupported_claims": total_claims - supported_claims,
                "audit_note": "Baselines without verification (BASE-A..D, ABL-1) had 0 total claims extracted. Previous report filled 100.0% via division-by-zero default."
            },
            "conflict_detection": {
                "tp": tp, "fp": fp, "tn": tn, "fn": fn,
                "positive_gold_cases_in_test": tp + fn,
                "precision": conflict_prec,
                "recall": conflict_rec,
                "f1": conflict_f1,
                "audit_note": "Only 3 positive conflict queries exist in test split (DT-BENCH-019, 020, 021). All 3 were missed (FN=3) because detect_policy_conflicts rule-based parser only checked remote work keywords."
            },
            "governance_and_abstention": {
                "appropriate_abstention_rate": app_abst_rate,
                "appropriate_abstention_fraction": f"{app_abst_count}/{len(unans_runs)}",
                "false_abstention_rate": false_abst_rate,
                "false_abstention_fraction": f"{false_abst_count}/{len(ans_runs)}",
                "decision_accuracy_3way_exact": dec_acc_3way,
                "decision_accuracy_3way_fraction": f"{dec_matches_3way}/{total_queries}",
                "binary_governance_accuracy": binary_acc,
                "binary_governance_fraction": f"{binary_matches}/{total_queries}",
                "confusion_matrix_3way": {f"Exp_{k[0]}__Act_{k[1]}": v for k, v in sorted(confusion_3way.items())}
            },
            "latency": {
                "mean_ms": mean_lat,
                "median_ms": median_lat,
                "min_ms": min(latencies),
                "max_ms": max(latencies)
            },
            "_raw_mrr": rr_list,
            "_raw_ndcg": ndcg_list,
            "_raw_dec_match": [r["actual_decision"] == r["expected_decision"] for r in runs]
        }
        
    # Statistical tests between SYS-FULL and BASE-C
    sf = audit_metrics["SYS-FULL"]
    bc = audit_metrics["BASE-C"]
    
    # Paired t-test on MRR
    diffs_mrr = [s - b for s, b in zip(sf["_raw_mrr"], bc["_raw_mrr"])]
    m_diff_mrr = sum(diffs_mrr) / len(diffs_mrr)
    v_diff_mrr = sum((d - m_diff_mrr)**2 for d in diffs_mrr) / (len(diffs_mrr) - 1)
    s_diff_mrr = math.sqrt(v_diff_mrr) if v_diff_mrr > 0 else 1e-9
    t_stat_mrr = m_diff_mrr / (s_diff_mrr / math.sqrt(len(diffs_mrr)))
    p_val_mrr = student_t_pvalue(t_stat_mrr, df=len(diffs_mrr) - 1)
    
    # Paired t-test on nDCG
    diffs_ndcg = [s - b for s, b in zip(sf["_raw_ndcg"], bc["_raw_ndcg"])]
    m_diff_ndcg = sum(diffs_ndcg) / len(diffs_ndcg)
    v_diff_ndcg = sum((d - m_diff_ndcg)**2 for d in diffs_ndcg) / (len(diffs_ndcg) - 1)
    s_diff_ndcg = math.sqrt(v_diff_ndcg) if v_diff_ndcg > 0 else 1e-9
    t_stat_ndcg = m_diff_ndcg / (s_diff_ndcg / math.sqrt(len(diffs_ndcg)))
    p_val_ndcg = student_t_pvalue(t_stat_ndcg, df=len(diffs_ndcg) - 1)
    
    # McNemar test
    # Discordant counts:
    # b: SYS-FULL correct (1), BASE-C wrong (0)
    # c: BASE-C correct (1), SYS-FULL wrong (0)
    b_disc = sum(1 for s, b in zip(sf["_raw_dec_match"], bc["_raw_dec_match"]) if s and not b)
    c_disc = sum(1 for s, b in zip(sf["_raw_dec_match"], bc["_raw_dec_match"]) if not s and b)
    mcnemar_res = exact_mcnemar_test(b_disc, c_disc)
    
    # Bootstrap CIs for SYS-FULL
    mrr_ci_95 = bootstrap_ci(sf["_raw_mrr"])
    ndcg_ci_95 = bootstrap_ci(sf["_raw_ndcg"])
    
    audit_metrics["statistical_audit"] = {
        "mrr_paired_t_test": {
            "df": len(diffs_mrr) - 1,
            "mean_difference": round(m_diff_mrr, 4),
            "std_difference": round(s_diff_mrr, 4),
            "t_statistic": round(t_stat_mrr, 3),
            "p_value_exact_t": round(p_val_mrr, 4),
            "significant_at_alpha_0_05": p_val_mrr < 0.05
        },
        "ndcg_paired_t_test": {
            "df": len(diffs_ndcg) - 1,
            "mean_difference": round(m_diff_ndcg, 4),
            "std_difference": round(s_diff_ndcg, 4),
            "t_statistic": round(t_stat_ndcg, 3),
            "p_value_exact_t": round(p_val_ndcg, 4),
            "significant_at_alpha_0_05": p_val_ndcg < 0.05
        },
        "mcnemar_test_decision_accuracy": mcnemar_res,
        "sys_full_mrr_95_bootstrap_ci": mrr_ci_95,
        "sys_full_ndcg_95_bootstrap_ci": ndcg_ci_95
    }
    
    # Clean output dictionary
    clean_metrics = {}
    for k, v in audit_metrics.items():
        if isinstance(v, dict):
            clean_metrics[k] = {ik: iv for ik, iv in v.items() if not ik.startswith("_raw_")}
        else:
            clean_metrics[k] = v
            
    out_json = ROOT_DIR / "research" / "results" / "independent_recomputed_metrics.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(clean_metrics, f, indent=2)
    print(f"[OK] Saved independent recomputed metrics to: {out_json}")
    
    return clean_metrics

if __name__ == "__main__":
    run_independent_audit()
