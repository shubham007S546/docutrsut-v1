"""
DocuTrust Empirical Plot Generator
Generates publication-quality charts from actual evaluated experimental results.
Outputs saved to research/results/plots/ as PNG and SVG.
"""
from __future__ import annotations

import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = Path(__file__).resolve().parent / "results"
PLOTS_DIR = RESULTS_DIR / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def load_summary() -> dict:
    path = RESULTS_DIR / "experiment_summary.json"
    if not path.exists():
        raise FileNotFoundError(f"Summary not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def plot_retrieval_comparison(summary: dict) -> None:
    configs = ["BASE-A", "BASE-B", "BASE-C", "BASE-D", "ITER-RETRIEVE", "SYS-FULL"]
    labels = ["BM25", "FAISS", "Hybrid RRF", "Hybrid+Rerank", "Iterative", "Full DocuTrust"]

    mrrs = [summary[c]["mrr"] for c in configs]
    ndcgs = [summary[c]["ndcg_at_k"] for c in configs]
    recalls = [summary[c]["recall_at_k"] / 100.0 for c in configs]

    x = np.arange(len(configs))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f9fafb")

    rects1 = ax.bar(x - width, recalls, width, label="Recall@8", color="#3b82f6", edgecolor="#1d4ed8")
    rects2 = ax.bar(x, mrrs, width, label="MRR", color="#0d9488", edgecolor="#0f766e")
    rects3 = ax.bar(x + width, ndcgs, width, label="nDCG@8", color="#8b5cf6", edgecolor="#6d28d9")

    ax.set_ylabel("Metric Score", fontsize=11, fontweight="bold")
    ax.set_title("IR Retrieval Quality Across Baselines & System Variants (Frozen Test Set, N=34)", fontsize=12, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10, fontweight="semibold")
    ax.set_ylim(0.0, 1.15)
    ax.legend(frameon=True, facecolor="#ffffff", edgecolor="#e5e7eb", fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for rects in [rects1, rects2, rects3]:
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f"{height:.2f}",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=8, fontweight="bold")

    plt.tight_layout()
    png_path = PLOTS_DIR / "retrieval_comparison.png"
    svg_path = PLOTS_DIR / "retrieval_comparison.svg"
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()
    print(f"[OK] Saved retrieval comparison plots to {png_path} and {svg_path}")


def plot_ablation_comparison(summary: dict) -> None:
    ablations = [
        ("SYS-FULL", "Full System"),
        ("ABL-1", "- Verification"),
        ("ABL-2", "- Version Aware"),
        ("ABL-3", "- Conflict Det"),
        ("ABL-4", "- Abstention"),
        ("ABL-5", "- Reranker"),
    ]

    names = [label for _, label in ablations]
    dec_acc = [summary[code]["decision_accuracy"] for code, _ in ablations]
    app_abst = [summary[code]["appropriate_abstention_rate"] for code, _ in ablations]
    conf_f1 = [summary[code]["conflict_f1"] for code, _ in ablations]

    x = np.arange(len(ablations))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f9fafb")

    rects1 = ax.bar(x - width, dec_acc, width, label="Decision Accuracy (%)", color="#10b981", edgecolor="#047857")
    rects2 = ax.bar(x, app_abst, width, label="Appropriate Abstention (%)", color="#f59e0b", edgecolor="#b45309")
    rects3 = ax.bar(x + width, conf_f1, width, label="Conflict F1 (%)", color="#ef4444", edgecolor="#b91c1c")

    ax.set_ylabel("Percentage (%)", fontsize=11, fontweight="bold")
    ax.set_title("Ablation Analysis: Trust & Decision Invariants (Frozen Test Set, N=34)", fontsize=12, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=9, fontweight="semibold")
    ax.set_ylim(0, 120)
    ax.legend(frameon=True, facecolor="#ffffff", edgecolor="#e5e7eb", fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for rects in [rects1, rects2, rects3]:
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f"{height:.0f}%",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=8, fontweight="bold")

    plt.tight_layout()
    png_path = PLOTS_DIR / "ablation_comparison.png"
    svg_path = PLOTS_DIR / "ablation_comparison.svg"
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()
    print(f"[OK] Saved ablation comparison plots to {png_path} and {svg_path}")


def plot_risk_coverage_curve() -> None:
    raw_path = RESULTS_DIR / "raw_experiment_results.json"
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sys_runs = data["raw_results"]["SYS-FULL"]
    thresholds = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
    coverages = []
    accuracies = []

    for t in thresholds:
        covered = [r for r in sys_runs if r["confidence"] >= t]
        cov_rate = len(covered) / max(1, len(sys_runs))
        correct = sum(1 for r in covered if r["actual_decision"] == r["expected_decision"])
        acc = (correct / max(1, len(covered))) if covered else 1.0
        coverages.append(cov_rate * 100)
        accuracies.append(acc * 100)

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f9fafb")

    ax.plot(coverages, accuracies, marker="o", linewidth=2.5, color="#0f766e", label="DocuTrust Confidence Frontier")
    for i, t in enumerate(thresholds):
        ax.annotate(f"$\\tau={t}$", (coverages[i], accuracies[i]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, fontweight="bold")

    ax.set_xlabel("Answer Coverage (%)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Empirical Decision Accuracy (%)", fontsize=11, fontweight="bold")
    ax.set_title("DocuTrust Risk-Coverage Trade-off Curve Across Confidence Thresholds", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlim(0, 105)
    ax.set_ylim(40, 105)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(frameon=True, facecolor="#ffffff", edgecolor="#e5e7eb", fontsize=10)

    plt.tight_layout()
    png_path = PLOTS_DIR / "risk_coverage_curve.png"
    svg_path = PLOTS_DIR / "risk_coverage_curve.svg"
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()
    print(f"[OK] Saved risk-coverage curve to {png_path} and {svg_path}")


def generate_all_plots() -> None:
    summary = load_summary()
    plot_retrieval_comparison(summary)
    plot_ablation_comparison(summary)
    plot_risk_coverage_curve()


if __name__ == "__main__":
    generate_all_plots()
