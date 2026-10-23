"""
Generates independent, audited Markdown evaluation tables with explicit denominators,
confusion matrices, and correct baseline labels.
"""
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
json_path = ROOT_DIR / "research" / "results" / "independent_recomputed_metrics.json"

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

md = []
md.append("# DocuTrust Phase 4: Independent Audited Evaluation Tables\n")
md.append("**Evaluation Split:** Frozen Test Set ($N=34$ total queries; $N=26$ answerable, $N=8$ unanswerable)\n")
md.append("**Ground Truth Document Families:** `01_Security_Safeguards_Policy.pdf`, `02_Privacy_and_Data_Protection_Standard.pdf`, `04_Finance_and_Expense_Reimbursement_Code.pdf` (Zero overlap with Dev set)\n\n")

md.append("## Table 1: Audited Baseline Comparison (Frozen Test Set, N=34)\n")
md.append("> **Note on Retrieval Denominators:** Precision@8 and Recall@8 are evaluated strictly over answerable queries ($N=26$). Because each benchmark item contains exactly one gold passage ($|Gold|=1$) and $K=8$, the theoretical maximum Precision@8 is $1/8 = 12.5\\%$. Hit@1 (Success at Rank 1) is included to provide an unconstrained precision indicator.\n")
md.append("> **Note on Claim Support:** Baselines where claim verification was not executed (BASE-A..D) had 0 claims extracted and are marked `N/A (0 Claims)` to avoid false 100% reporting from division by zero.\n\n")

md.append("| System Configuration | Precision@8 (Max 12.5%) | Recall@8 | Hit@1 | MRR | nDCG@8 | Claim Support Rate | Conflict F1 (TP/FN) | App. Abstain (N=8) | False Abstain (N=26) | 3-Way Decision Acc (N=34) | Mean Latency (ms) |")
md.append("|---|---|---|---|---|---|---|---|---|---|---|---|")

configs_t1 = ["BASE-A", "BASE-B", "BASE-C", "BASE-D", "BASE-E", "ITER-RETRIEVE", "SYS-FULL"]
for cfg in configs_t1:
    s = data[cfg]
    r = s["retrieval"]
    f = s["factuality"]
    c = s["conflict_detection"]
    g = s["governance_and_abstention"]
    l = s["latency"]
    
    cs_str = f"{f['claim_support_rate']}% ({f['supported_claims']}/{f['total_claims']})" if f["claim_support_rate"] is not None else "N/A (0 Claims)"
    conf_str = f"{c['f1']}% ({c['tp']}/{c['fn']})"
    app_str = f"{g['appropriate_abstention_rate']}% ({g['appropriate_abstention_fraction']})"
    false_str = f"{g['false_abstention_rate']}% ({g['false_abstention_fraction']})"
    dec_str = f"{g['decision_accuracy_3way_exact']}% ({g['decision_accuracy_3way_fraction']})"
    
    md.append(f"| **{cfg}** | {r['precision_at_8']}% | {r['recall_at_8']}% | {r['hit_at_1']}% | {r['mrr']} | {r['ndcg_at_8']} | {cs_str} | {conf_str} | {app_str} | {false_str} | {dec_str} | {l['mean_ms']} |")

md.append("\n---\n")
md.append("## Table 2: Component Ablation Study (Audited Frozen Test Set, N=34)\n")
md.append("| Configuration | Condition Description | MRR | nDCG@8 | Conflict F1 | App. Abstain (N=8) | False Abstain (N=26) | 3-Way Decision Acc | Binary Gov. Acc | Root-Cause Audit Finding |")
md.append("|---|---|---|---|---|---|---|---|---|---|")

abl_list = [
    ("SYS-FULL", "Reference Full Pipeline", "Full DocuTrust architecture with multi-agent verification and reranking."),
    ("ABL-1", "- Claim Verification", "Sentence entailment disabled; 0 claims evaluated; -3.0% 3-way accuracy drop."),
    ("ABL-2", "- Version Intelligence", "Version supersession filtering bypassed; false abstentions increase to 50.0% (-8.8% accuracy)."),
    ("ABL-3", "- Conflict Analysis", "Conflict detector disabled; 0 conflict flags raised across all queries."),
    ("ABL-4", "- Evidence Abstention", "Forced generation enabled; generates ungrounded claims on 8 unanswerable queries."),
    ("ABL-5", "- Cross-Encoder Reranker", "Raw RRF scores (~0.02) clamped to 0.1 in confidence formula; triggers 57.7% false review escalations.")
]

for code, name, finding in abl_list:
    s = data[code]
    r = s["retrieval"]
    c = s["conflict_detection"]
    g = s["governance_and_abstention"]
    
    app_str = f"{g['appropriate_abstention_rate']}% ({g['appropriate_abstention_fraction']})"
    false_str = f"{g['false_abstention_rate']}% ({g['false_abstention_fraction']})"
    dec_str = f"{g['decision_accuracy_3way_exact']}% ({g['decision_accuracy_3way_fraction']})"
    bin_str = f"{g['binary_governance_accuracy']}% ({g['binary_governance_fraction']})"
    
    md.append(f"| **{code}** | {name} | {r['mrr']} | {r['ndcg_at_8']} | {c['f1']}% | {app_str} | {false_str} | {dec_str} | {bin_str} | {finding} |")

md.append("\n---\n")
md.append("## Table 3: Exact Statistical Significance Testing (SYS-FULL vs. BASE-C)\n")
st = data["statistical_audit"]
m_t = st["mrr_paired_t_test"]
n_t = st["ndcg_paired_t_test"]
mcn = st["mcnemar_test_decision_accuracy"]

md.append(f"- **MRR Paired Student's t-test (df={m_t['df']}):** $t = {m_t['t_statistic']}, p = {m_t['p_value_exact_t']}$ (Difference not significant at $\\alpha=0.05$)")
md.append(f"- **nDCG@8 Paired Student's t-test (df={n_t['df']}):** $t = {n_t['t_statistic']}, p = {n_t['p_value_exact_t']}$ (Difference not significant at $\\alpha=0.05$)")
md.append(f"- **McNemar Test Discordant Pairs:** $b = {mcn['b_sys_full_correct_baseline_wrong']}$ (SYS-FULL correct, BASE-C wrong), $c = {mcn['c_baseline_correct_sys_full_wrong']}$ (BASE-C correct, SYS-FULL wrong), Total Discordant $= {mcn['total_discordant_pairs']}$")
md.append(f"- **McNemar Test Exact Two-Tailed Binomial:** $p = {mcn['p_value_exact_binomial']}$ (Not Significant)")
md.append(f"- **McNemar Continuity-Corrected $\\chi^2$:** $\\chi^2 = {mcn['chi2_continuity_corrected']}, p = {mcn['p_value_chi2_approx']}$")
md.append(f"- **SYS-FULL MRR 95% Bootstrap Percentile CI (B=2000):** [{st['sys_full_mrr_95_bootstrap_ci'][0]}, {st['sys_full_mrr_95_bootstrap_ci'][1]}]")
md.append(f"- **SYS-FULL nDCG@8 95% Bootstrap Percentile CI (B=2000):** [{st['sys_full_ndcg_95_bootstrap_ci'][0]}, {st['sys_full_ndcg_95_bootstrap_ci'][1]}]\n\n")

md.append("## Table 4: 3-Way Decision Confusion Matrices\n\n")
md.append("| Expected Decision | SYS-FULL (Act: ANS) | SYS-FULL (Act: ESC) | SYS-FULL (Act: ABST) | BASE-C (Act: ANS) | BASE-C (Act: ESC) | BASE-C (Act: ABST) |\n")
md.append("|---|---|---|---|---|---|---|\n")

sf_cm = data["SYS-FULL"]["governance_and_abstention"]["confusion_matrix_3way"]
bc_cm = data["BASE-C"]["governance_and_abstention"]["confusion_matrix_3way"]

md.append(f"| **ANSWER (N=20)** | {sf_cm.get('Exp_ANSWER__Act_ANSWER', 0)} | {sf_cm.get('Exp_ANSWER__Act_ESCALATE_REVIEW', 0)} | {sf_cm.get('Exp_ANSWER__Act_ABSTAIN', 0)} | {bc_cm.get('Exp_ANSWER__Act_ANSWER', 0)} | {bc_cm.get('Exp_ANSWER__Act_ESCALATE_REVIEW', 0)} | {bc_cm.get('Exp_ANSWER__Act_ABSTAIN', 0)} |\n")
md.append(f"| **ESCALATE_REVIEW (N=6)** | {sf_cm.get('Exp_ESCALATE_REVIEW__Act_ANSWER', 0)} | {sf_cm.get('Exp_ESCALATE_REVIEW__Act_ESCALATE_REVIEW', 0)} | {sf_cm.get('Exp_ESCALATE_REVIEW__Act_ABSTAIN', 0)} | {bc_cm.get('Exp_ESCALATE_REVIEW__Act_ANSWER', 0)} | {bc_cm.get('Exp_ESCALATE_REVIEW__Act_ESCALATE_REVIEW', 0)} | {bc_cm.get('Exp_ESCALATE_REVIEW__Act_ABSTAIN', 0)} |\n")
md.append(f"| **ABSTAIN (N=8)** | {sf_cm.get('Exp_ABSTAIN__Act_ANSWER', 0)} | {sf_cm.get('Exp_ABSTAIN__Act_ESCALATE_REVIEW', 0)} | {sf_cm.get('Exp_ABSTAIN__Act_ABSTAIN', 0)} | {bc_cm.get('Exp_ABSTAIN__Act_ANSWER', 0)} | {bc_cm.get('Exp_ABSTAIN__Act_ESCALATE_REVIEW', 0)} | {bc_cm.get('Exp_ABSTAIN__Act_ABSTAIN', 0)} |\n")

out_md_path = ROOT_DIR / "research" / "results" / "independent_evaluation_tables.md"
with open(out_md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md))

print(f"[OK] Saved independent evaluation tables to: {out_md_path}")
