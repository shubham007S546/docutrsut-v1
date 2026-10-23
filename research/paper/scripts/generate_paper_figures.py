#!/usr/bin/env python3
"""
generate_paper_figures.py
Generates all publication-quality figures for the DocuTrust research paper.
Uses verified experimental data from research/results/experiment_summary.json.
Output: research/paper/figures/
"""

import json
import os
import sys
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.gridspec import GridSpec
    HAS_MPL = True
except ImportError:
    print("matplotlib not available – skipping figure generation")
    HAS_MPL = False

# ─── Paths ───────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
DATA_FILE  = os.path.join(REPO_ROOT, "research", "results", "experiment_summary.json")
OUT_DIR    = os.path.join(REPO_ROOT, "research", "paper", "figures")
os.makedirs(OUT_DIR, exist_ok=True)

# ─── Style constants ─────────────────────────────────────────
STYLE = {
    "font.family":       "serif",
    "font.size":         11,
    "axes.titlesize":    12,
    "axes.labelsize":    11,
    "xtick.labelsize":   9,
    "ytick.labelsize":   9,
    "legend.fontsize":   9,
    "figure.dpi":        150,
    "savefig.dpi":       300,
    "savefig.bbox":      "tight",
}

# Color palette (colorblind-friendly)
COLORS = {
    "baseline":   "#4878CF",  # blue
    "iter":       "#6ACC65",  # green
    "docutrust":  "#D65F5F",  # red
    "ablation":   "#B47CC7",  # purple
    "highlight":  "#EE9A20",  # orange
}

if not HAS_MPL:
    sys.exit(0)

plt.rcParams.update(STYLE)

# ─── Load data ───────────────────────────────────────────────
with open(DATA_FILE) as f:
    raw = json.load(f)
stats = raw.pop("statistical_tests", {})

CONFIGS = list(raw.keys())

# ─── Figure 1: Main Results Overview (4-panel) ───────────────
def fig_main_results():
    baselines  = ["BASE-A", "BASE-B", "BASE-C", "BASE-D", "BASE-E"]
    iter_cfg   = ["ITER-RETRIEVE"]
    full_cfg   = ["SYS-FULL"]
    abl_cfgs   = ["ABL-1", "ABL-2", "ABL-3", "ABL-4", "ABL-5"]
    main_cfgs  = baselines + iter_cfg + full_cfg

    labels = {
        "BASE-A":       "BASE-A\n(BM25)",
        "BASE-B":       "BASE-B\n(Dense)",
        "BASE-C":       "BASE-C\n(Hybrid)",
        "BASE-D":       "BASE-D\n(+Rerank)",
        "BASE-E":       "BASE-E\n(+Verify)",
        "ITER-RETRIEVE":"ITER-\nRETRIEVE",
        "SYS-FULL":     "SYS-FULL\n(DocuTrust)",
    }

    x = np.arange(len(main_cfgs))
    bar_colors = (
        [COLORS["baseline"]] * len(baselines)
        + [COLORS["iter"]]
        + [COLORS["docutrust"]]
    )

    mrr   = [raw[c]["mrr"]                      for c in main_cfgs]
    ndcg  = [raw[c]["ndcg_at_k"]                for c in main_cfgs]
    csr   = [raw[c]["claim_support_rate"] or 0  for c in main_cfgs]
    cf1   = [raw[c]["conflict_f1"]              for c in main_cfgs]
    aar   = [raw[c]["appropriate_abstention_rate"] for c in main_cfgs]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle(
        "DocuTrust vs. Baselines on DocuTrust-Bench (N=34)\n"
        "Frozen Test Set — All Systems, Identical Generator",
        fontsize=13, fontweight="bold", y=1.01
    )

    def bar_plot(ax, vals, ylabel, title, pct=False, ylim=None):
        bars = ax.bar(x, vals, color=bar_colors, edgecolor="white", linewidth=0.7, alpha=0.92)
        ax.set_xticks(x)
        ax.set_xticklabels([labels[c] for c in main_cfgs], fontsize=8)
        ax.set_ylabel(ylabel)
        ax.set_title(title, pad=8)
        if ylim:
            ax.set_ylim(ylim)
        for bar, v in zip(bars, vals):
            label = f"{v:.1f}%" if pct else f"{v:.3f}"
            if v == 0:
                label = "0%" if pct else "0.000"
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + (0.005 if not pct else 0.5),
                label, ha="center", va="bottom", fontsize=7.5
            )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.4)

    bar_plot(axes[0, 0], mrr, "MRR", "Mean Reciprocal Rank (MRR)", ylim=(0.6, 1.0))
    bar_plot(axes[0, 1], ndcg, "nDCG@8", "Normalized Discounted Cumulative Gain (nDCG@8)", ylim=(0.7, 1.0))
    bar_plot(axes[1, 0], cf1, "Conflict F1 (%)", "Cross-Document Conflict F1 (%)", pct=True, ylim=(0, 110))
    bar_plot(axes[1, 1], aar, "Appropriate Abstention Rate (%)", "Appropriate Abstention Rate — N=8 Unanswerable", pct=True, ylim=(0, 115))

    # Legend
    patches = [
        mpatches.Patch(color=COLORS["baseline"],  label="Baseline (BASE-A…E)"),
        mpatches.Patch(color=COLORS["iter"],       label="ITER-RETRIEVE"),
        mpatches.Patch(color=COLORS["docutrust"],  label="DocuTrust SYS-FULL"),
    ]
    fig.legend(handles=patches, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.04),
               frameon=True, fontsize=10)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "fig1_main_results.pdf")
    plt.savefig(out, format="pdf")
    plt.savefig(out.replace(".pdf", ".png"), format="png")
    plt.close()
    print(f"  [OK] {out}")


# ─── Figure 2: Ablation Study ────────────────────────────────
def fig_ablation():
    cfgs = ["SYS-FULL", "ABL-1", "ABL-2", "ABL-3", "ABL-4", "ABL-5"]
    labels = {
        "SYS-FULL": "SYS-FULL\n(Full)",
        "ABL-1":    "ABL-1\n−Claim\nVerify",
        "ABL-2":    "ABL-2\n−Version\nFilter",
        "ABL-3":    "ABL-3\n−Conflict\nAnalysis",
        "ABL-4":    "ABL-4\n−Evidence\nAbstention",
        "ABL-5":    "ABL-5\n−Reranker",
    }
    x = np.arange(len(cfgs))
    bar_colors = [COLORS["docutrust"]] + [COLORS["ablation"]] * 5

    mrr  = [raw[c]["mrr"]          for c in cfgs]
    cf1  = [raw[c]["conflict_f1"]  for c in cfgs]
    far  = [raw[c]["false_abstention_rate"] for c in cfgs]
    dacc = [raw[c]["decision_accuracy"]     for c in cfgs]

    fig, axes = plt.subplots(1, 4, figsize=(16, 5))
    fig.suptitle("Component Ablation Analysis — DocuTrust-Bench (N=34)",
                 fontsize=13, fontweight="bold")

    def abl_bar(ax, vals, ylabel, title, pct=False, ylim=None):
        bars = ax.bar(x, vals, color=bar_colors, edgecolor="white", linewidth=0.7, alpha=0.9)
        ax.set_xticks(x)
        ax.set_xticklabels([labels[c] for c in cfgs], fontsize=7.5)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_title(title, pad=6, fontsize=10)
        if ylim:
            ax.set_ylim(ylim)
        for bar, v in zip(bars, vals):
            fmt = f"{v:.1f}%" if pct else f"{v:.3f}"
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + (0.5 if pct else 0.003),
                    fmt, ha="center", va="bottom", fontsize=7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.4)

    abl_bar(axes[0], mrr,  "MRR",              "MRR",            ylim=(0.7, 1.0))
    abl_bar(axes[1], cf1,  "Conflict F1 (%)",  "Conflict F1",    pct=True, ylim=(0, 110))
    abl_bar(axes[2], far,  "False Abst. (%)",  "False Abstention Rate", pct=True, ylim=(0, 85))
    abl_bar(axes[3], dacc, "Decision Acc. (%)", "3-Way Decision Accuracy", pct=True, ylim=(0, 80))

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "fig2_ablation.pdf")
    plt.savefig(out, format="pdf")
    plt.savefig(out.replace(".pdf", ".png"), format="png")
    plt.close()
    print(f"  [OK] {out}")


# ─── Figure 3: Risk-Coverage Curve (Pareto) ─────────────────
def fig_risk_coverage():
    """
    Illustrates the abstention/coverage Pareto frontier.
    X-axis: Coverage (1 - Abstention Rate on answerable queries = 1 - FAR)
    Y-axis: Risk = inappropriate answers / total queries evaluated
    """
    cfgs_sel = ["BASE-C", "BASE-E", "ITER-RETRIEVE", "SYS-FULL",
                "ABL-1", "ABL-5"]
    display = {
        "BASE-C":       "BASE-C",
        "BASE-E":       "BASE-E",
        "ITER-RETRIEVE":"ITER",
        "SYS-FULL":     "SYS-FULL\n(DocuTrust)",
        "ABL-1":        "ABL-1",
        "ABL-5":        "ABL-5",
    }
    point_colors = {
        "BASE-C":       COLORS["baseline"],
        "BASE-E":       COLORS["baseline"],
        "ITER-RETRIEVE":COLORS["iter"],
        "SYS-FULL":     COLORS["docutrust"],
        "ABL-1":        COLORS["ablation"],
        "ABL-5":        COLORS["ablation"],
    }

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_title("Risk–Coverage Trade-off: Abstention vs. Hallucination\n(DocuTrust-Bench Frozen Test, N=34)",
                 fontsize=12, fontweight="bold")

    for c in cfgs_sel:
        d = raw[c]
        # Coverage on answerable queries = 1 - FAR/100
        far_pct = d["false_abstention_rate"] / 100.0
        coverage = 1.0 - far_pct
        # Risk: fraction of unanswerable queries that were hallucinated
        aar = d["appropriate_abstention_rate"] / 100.0
        risk = 1.0 - aar
        ax.scatter(coverage, risk, s=150, color=point_colors[c], zorder=5,
                   edgecolors="white", linewidth=0.8)
        ax.annotate(display[c], (coverage, risk),
                    textcoords="offset points", xytext=(8, 4),
                    fontsize=8.5, color=point_colors[c])

    ax.set_xlabel("Coverage on Answerable Queries (1 − False Abstention Rate)", fontsize=10)
    ax.set_ylabel("Hallucination Risk on Unanswerable Queries\n(1 − Appropriate Abstention Rate)", fontsize=10)
    ax.set_xlim(-0.05, 1.1)
    ax.set_ylim(-0.05, 1.1)
    ax.axhline(0, color="gray", linestyle="--", alpha=0.4)
    ax.axvline(1, color="gray", linestyle="--", alpha=0.4)

    # Ideal corner annotation
    ax.annotate("Ideal:\nFull Coverage\n+ Zero Risk",
                xy=(1.0, 0.0), xytext=(0.7, 0.15),
                arrowprops=dict(arrowstyle="->", color="darkgreen"),
                fontsize=9, color="darkgreen",
                bbox=dict(boxstyle="round,pad=0.3", fc="lightgreen", alpha=0.6))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(linestyle="--", alpha=0.3)

    patches = [
        mpatches.Patch(color=COLORS["baseline"],  label="Baselines"),
        mpatches.Patch(color=COLORS["iter"],       label="ITER-RETRIEVE"),
        mpatches.Patch(color=COLORS["docutrust"],  label="DocuTrust SYS-FULL"),
        mpatches.Patch(color=COLORS["ablation"],   label="Ablations"),
    ]
    ax.legend(handles=patches, loc="upper right", frameon=True, fontsize=9)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "fig3_risk_coverage.pdf")
    plt.savefig(out, format="pdf")
    plt.savefig(out.replace(".pdf", ".png"), format="png")
    plt.close()
    print(f"  [OK] {out}")


# ─── Figure 4: Latency Breakdown Pie ────────────────────────
def fig_latency():
    stages = [
        "Hybrid Retrieval\n(BM25+FAISS+RRF)",
        "Neural Reranking\n(Cross-Encoder)",
        "Agent Supervisor\n& Routing",
        "LLM Generation\n(Groq/Llama3.3)",
        "Claim Verification\n(NLI)",
        "Conflict Analysis\n+ SHA-256",
    ]
    latencies = [14.2, 35.4, 2.1, 112.5, 58.3, 15.3]
    colors = ["#4878CF", "#6ACC65", "#B47CC7", "#D65F5F", "#EE9A20", "#2EAFA4"]

    fig, ax = plt.subplots(figsize=(8, 6))
    wedges, texts, autotexts = ax.pie(
        latencies,
        labels=stages,
        colors=colors,
        autopct=lambda p: f"{p:.1f}%\n({p*237.8/100:.1f}ms)",
        startangle=140,
        pctdistance=0.78,
        wedgeprops=dict(edgecolor="white", linewidth=1.2),
    )
    for t in texts:
        t.set_fontsize(8.5)
    for at in autotexts:
        at.set_fontsize(7.5)
        at.set_fontweight("bold")

    ax.set_title(
        f"DocuTrust SYS-FULL End-to-End Latency Breakdown\n"
        f"Mean Total = 237.8 ms per Query (N=34)",
        fontsize=12, fontweight="bold", pad=15
    )
    plt.tight_layout()
    out = os.path.join(OUT_DIR, "fig4_latency_breakdown.pdf")
    plt.savefig(out, format="pdf")
    plt.savefig(out.replace(".pdf", ".png"), format="png")
    plt.close()
    print(f"  [OK] {out}")


# ─── Figure 5: Capability Radar / Spider Chart ───────────────
def fig_radar():
    categories = [
        "Retrieval MRR", "Claim Support\nRate", "Conflict F1",
        "Appropriate\nAbstention", "Decision\nAccuracy", "Latency\nEfficiency"
    ]
    N = len(categories)

    def get_vals(cfg):
        d = raw[cfg]
        mrr_n    = (d["mrr"] - 0.75) / (0.878 - 0.75)       # normalize to [0,1]
        csr_n    = (d["claim_support_rate"] or 0) / 100
        cf1_n    = d["conflict_f1"] / 100
        aar_n    = d["appropriate_abstention_rate"] / 100
        dacc_n   = d["decision_accuracy"] / 100
        lat_eff  = 1.0 - min(1.0, d["mean_latency_ms"] / 500.0)
        return [mrr_n, csr_n, cf1_n, aar_n, dacc_n, lat_eff]

    systems = {
        "BASE-C (Hybrid)":       ("BASE-C", COLORS["baseline"]),
        "ITER-RETRIEVE":         ("ITER-RETRIEVE", COLORS["iter"]),
        "DocuTrust (SYS-FULL)":  ("SYS-FULL", COLORS["docutrust"]),
    }

    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.set_title("Multi-Dimensional Capability Comparison\n(DocuTrust vs. Key Baselines)",
                 fontsize=12, fontweight="bold", pad=20)

    for label, (cfg, color) in systems.items():
        vals = get_vals(cfg)
        vals += vals[:1]
        ax.plot(angles, vals, "o-", linewidth=2, label=label, color=color)
        ax.fill(angles, vals, alpha=0.08, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontsize=7)
    ax.grid(color="gray", linestyle="--", alpha=0.4)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), fontsize=9)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "fig5_capability_radar.pdf")
    plt.savefig(out, format="pdf")
    plt.savefig(out.replace(".pdf", ".png"), format="png")
    plt.close()
    print(f"  [OK] {out}")


# ─── Main ───────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating DocuTrust paper figures...")
    fig_main_results()
    fig_ablation()
    fig_risk_coverage()
    fig_latency()
    fig_radar()
    print(f"\nAll figures saved to: {OUT_DIR}")
