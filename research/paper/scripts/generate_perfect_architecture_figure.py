#!/usr/bin/env python3
"""
generate_perfect_architecture_figure.py
Renders a publication-grade architecture diagram matching the exact layout,
modular dashed grouping, diamond decision nodes, and styling of premier IEEE papers
(matching the user's reference diagram).
Saves to research/paper/figures/fig2_architecture.png and .pdf.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PAPER_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
FIG_DIR = os.path.join(PAPER_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans", "Helvetica"],
    "font.size": 8.5,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight"
})

def draw_perfect_schematic():
    # Canvas size: 16 x 9 inches (ample space, crisp resolution, zero overlaps)
    fig, ax = plt.subplots(figsize=(16, 9.2))
    ax.set_xlim(0, 160)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Helper: draw dashed module container
    def draw_container(x, y, w, h, title, border_color="#38A169", bg_color="#F0FFF4"):
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5",
                              facecolor=bg_color, edgecolor=border_color,
                              linestyle="--", linewidth=1.5, zorder=1)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h - 2.8, title, ha="center", va="center",
                fontsize=10.5, fontweight="bold", color="#1F2937", zorder=2)

    # Helper: draw process box
    def draw_box(x, y, w, h, title, subtitle="", bg="#E2E8F0", border="#475569", zorder=3):
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3",
                              facecolor=bg, edgecolor=border,
                              linestyle="-", linewidth=1.2, zorder=zorder)
        ax.add_patch(rect)
        if subtitle:
            ax.text(x + w / 2, y + h / 2 + 1.2, title, ha="center", va="center",
                    fontsize=8.5, fontweight="bold", color="#0F172A", zorder=zorder+1)
            ax.text(x + w / 2, y + h / 2 - 1.4, subtitle, ha="center", va="center",
                    fontsize=7.2, color="#334155", zorder=zorder+1)
        else:
            ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                    fontsize=8.5, fontweight="bold", color="#0F172A", zorder=zorder+1)

    # Helper: draw diamond decision node
    def draw_diamond(x, y, w, h, text, bg="#CBD5E1", border="#475569", zorder=3):
        pts = np.array([
            [x + w / 2, y + h],
            [x + w, y + h / 2],
            [x + w / 2, y],
            [x, y + h / 2]
        ])
        diamond = Polygon(pts, closed=True, facecolor=bg, edgecolor=border,
                          linewidth=1.2, zorder=zorder)
        ax.add_patch(diamond)
        lines = text.split("\n")
        if len(lines) == 1:
            ax.text(x + w / 2, y + h / 2, lines[0], ha="center", va="center",
                    fontsize=8, fontweight="bold", color="#0F172A", zorder=zorder+1)
        else:
            ax.text(x + w / 2, y + h / 2 + 0.9, lines[0], ha="center", va="center",
                    fontsize=8, fontweight="bold", color="#0F172A", zorder=zorder+1)
            ax.text(x + w / 2, y + h / 2 - 1.1, lines[1], ha="center", va="center",
                    fontsize=7.2, color="#334155", zorder=zorder+1)

    # Helper: draw orthogonal arrow
    def draw_arrow(points, label="", lbl_pos="top", color="#334155"):
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            is_last = (i == len(points) - 2)
            if is_last:
                ax.annotate("", xy=p2, xytext=p1,
                            arrowprops=dict(facecolor=color, edgecolor=color,
                                           arrowstyle="->", lw=1.3),
                            zorder=4)
            else:
                ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color, lw=1.3, zorder=4)
        if label:
            p_mid = points[len(points) // 2]
            y_shift = 1.6 if lbl_pos == "top" else -1.6
            ax.text(p_mid[0], p_mid[1] + y_shift, label, ha="center", va="center",
                    fontsize=7.5, fontweight="bold", color="#1E3A8A",
                    bbox=dict(boxstyle="square,pad=0.15", facecolor="#FFFFFF", edgecolor="#CBD5E1", lw=0.6),
                    zorder=5)

    # ==========================================================================
    # TOP SECTION: INPUT, AUDIT & PREPROCESSING (Y = 60 to 98)
    # ==========================================================================
    
    # 1. Raw Input Box (Blue)
    draw_box(4, 84, 25, 10, "Raw Compliance Query & Context",
             "(Query q, Tenant ID \u03c4, Timestamp t_q)", bg="#BAE6FD", border="#0284C7")

    # Arrow from Raw Input to Stage 1
    draw_arrow([(16.5, 84), (16.5, 75)])

    # 2. Stage 1: Security & Quality Audit (Grey)
    draw_box(4, 65, 25, 10, "Stage 1:", "Security & Boundary Audit",
             bg="#E2E8F0", border="#64748B")

    # Arrow from Stage 1 into Module 1
    draw_arrow([(29, 70), (36, 70)])

    # 3. Module 1: Preprocessing & Dual-Store Ingestion (Dashed Green)
    draw_container(34, 60, 122, 36, "Module 1: Preprocessing, Multi-Tenant Partitioning & Dual Index Store",
                   border_color="#16A34A", bg_color="#F0FDF4")

    # Parallel checks inside Module 1
    draw_box(37, 78, 24, 8, "Tenant Scope Validation", "(Row-Level Security & RLS)",
             bg="#CBD5E1", border="#475569")
    draw_box(37, 65, 24, 8, "Text Quality & Tokenizer", "(L=512 Windowing + SHA-256)",
             bg="#CBD5E1", border="#475569")

    # Branches to Diamond
    draw_arrow([(29, 70), (33, 70), (33, 82), (37, 82)])
    draw_arrow([(29, 70), (33, 70), (33, 69), (37, 69)])

    # Diamond: Quality Passed?
    draw_diamond(67, 70, 14, 11, "Tenant &\nQuality Passed?", bg="#E2E8F0", border="#475569")
    draw_arrow([(61, 82), (64, 82), (64, 75.5), (67, 75.5)])
    draw_arrow([(61, 69), (64, 69), (64, 75.5), (67, 75.5)])

    # Reject Branch (No)
    draw_box(66, 50, 16, 7, "Reject / Boundary Alert", "(Halt & Raise Security Log)",
             bg="#FCA5A5", border="#DC2626")
    draw_arrow([(74, 70), (74, 57)], label="No", lbl_pos="top")

    # Passed Branch (Yes)
    draw_arrow([(81, 75.5), (87, 75.5)], label="Yes", lbl_pos="top")

    # Processing pipeline inside Module 1
    draw_box(87, 71, 21, 9, "Dual-Store Indexing", "(BM25 Lexical + FAISS Dense)",
             bg="#FFFFFF", border="#16A34A")

    draw_arrow([(108, 75.5), (114, 75.5)])

    draw_box(114, 71, 22, 9, "Version Lineage Graph", "(Effective Dates & Status)",
             bg="#FFFFFF", border="#16A34A")

    draw_arrow([(136, 75.5), (142, 75.5)])

    draw_box(142, 71, 12, 9, "Candidate\nPassages E_k", "(Top-K Pool)",
             bg="#FFFFFF", border="#16A34A")

    # ==========================================================================
    # BUS WIRE FROM TOP TO BOTTOM STAGE 2
    # ==========================================================================
    draw_arrow([(148, 71), (148, 48), (4, 48), (4, 37), (5, 37)])

    # ==========================================================================
    # MIDDLE / BOTTOM SECTION: MULTI-AGENT, VERIFICATION & OUTPUT (Y = 2 to 45)
    # ==========================================================================

    # 4. Stage 2: Supervisor Agent & Intent Planner (Orange)
    draw_box(5, 30, 24, 12, "Stage 2: Supervisor Agent", "(Intent Planning & Specialist Dispatch)",
             bg="#FED7AA", border="#EA580C")

    draw_arrow([(29, 36), (36, 36)])

    # 5. Module 2: Multi-Specialist Governance & Hybrid RAG (Dashed Purple)
    draw_container(34, 4, 38, 44, "Module 2: Multi-Specialist RAG",
                   border_color="#9333EA", bg_color="#FAF5FF")

    # 3 Specialist Agents inside Module 2
    draw_box(36, 33, 34, 7, "Security Specialist Agent", "(MFA, Encryption, Device Controls)",
             bg="#E9D5FF", border="#9333EA")
    draw_box(36, 24, 34, 7, "Privacy Specialist Agent", "(GDPR 72h SLA, Retention Schedules)",
             bg="#E9D5FF", border="#9333EA")
    draw_box(36, 15, 34, 7, "Policy Specialist Agent", "(Day Limits, Per Diems, Approvals)",
             bg="#E9D5FF", border="#9333EA")

    # Down from Specialists to Fusion
    draw_box(36, 6, 34, 7, "Hybrid Fusion & Neural Rerank", "(RRF k=60 + Cross-Encoder Reranker)",
             bg="#FFFFFF", border="#7E22CE")

    draw_arrow([(29, 36), (33, 36), (33, 36.5), (36, 36.5)])
    draw_arrow([(29, 36), (33, 36), (33, 27.5), (36, 27.5)])
    draw_arrow([(29, 36), (33, 36), (33, 18.5), (36, 18.5)])
    draw_arrow([(53, 15), (53, 13)])

    # Arrow from Module 2 to Module 3
    draw_arrow([(70, 9.5), (76, 9.5)])

    # 6. Module 3: Evidence Intelligence & Verification (Dashed Green)
    draw_container(74, 4, 38, 44, "Module 3: Verification & Calibrated Abstention",
                   border_color="#16A34A", bg_color="#F0FDF4")

    draw_box(76, 33, 34, 7, "Active-Version Filter", "(Purge Superseded Historical Clauses)",
             bg="#DCFCE7", border="#16A34A")

    draw_box(76, 24, 34, 7, "Cross-Doc Conflict Detector", "(Typed PolicyClause Authority Lattice)",
             bg="#DCFCE7", border="#16A34A")

    draw_box(76, 15, 34, 7, "Sentence-Level NLI Verifier", "(Claim Entailment Scoring >= 0.85)",
             bg="#DCFCE7", border="#16A34A")

    # Diamond in Module 3: Confidence Router
    draw_diamond(82, 6, 22, 7, "Calibrated Confidence\n\u03a9 \u2265 0.70?", bg="#FEF08A", border="#CA8A04")

    draw_arrow([(70, 9.5), (73, 9.5), (73, 36.5), (76, 36.5)])
    draw_arrow([(93, 33), (93, 31)])
    draw_arrow([(93, 24), (93, 22)])
    draw_arrow([(93, 15), (93, 13)])

    # Arrow from Diamond out of Module 3 to Stage 4
    draw_arrow([(104, 9.5), (116, 9.5)])

    # 7. Stage 4: Decision Dispatch & Provenance Notary (Red / Coral)
    draw_box(115, 18, 12, 16, "Stage 4:\nDecision\nDispatch &\nProvenance\nNotary",
             bg="#FCA5A5", border="#E11D48")

    draw_arrow([(104, 9.5), (110, 9.5), (110, 26), (115, 26)])

    # Arrow from Stage 4 into System Deployment
    draw_arrow([(127, 26), (133, 26)])

    # 8. System Deployment & Compliance Output (Dashed Red Container)
    draw_container(131, 4, 27, 44, "System Deployment & Output",
                   border_color="#DC2626", bg_color="#FEF2F2")

    draw_box(133, 34, 23, 7.5, "Attributed Answer", "(Entailed Sentences + In-line Citations)",
             bg="#DCFCE7", border="#16A34A")

    draw_box(133, 24.5, 23, 7.5, "Signed Provenance Receipt", "(SHA-256 Digest & Merkle Tree)",
             bg="#F1F5F9", border="#475569")

    draw_box(133, 15, 23, 7.5, "Escalate Review Ticket", "(Flagged Conflicts / \u03a9 in [0.4, 0.7))",
             bg="#FEF3C7", border="#D97706")

    draw_box(133, 5.5, 23, 7.5, "Safe Abstention Notice", "(Zero Hallucination / OOD Inquiry)",
             bg="#FEE2E2", border="#DC2626")

    # Connect Stage 4 outputs to the 4 pins
    draw_arrow([(127, 26), (130, 26), (130, 37.7), (133, 37.7)])
    draw_arrow([(127, 26), (130, 26), (130, 28.2), (133, 28.2)])
    draw_arrow([(127, 26), (130, 26), (130, 18.7), (133, 18.7)])
    draw_arrow([(127, 26), (130, 26), (130, 9.2), (133, 9.2)])

    # Save outputs
    pdf_out = os.path.join(FIG_DIR, "fig2_architecture.pdf")
    png_out = os.path.join(FIG_DIR, "fig2_architecture.png")
    fig.savefig(pdf_out, dpi=300, bbox_inches="tight")
    fig.savefig(png_out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Master architecture schematic successfully generated!")

if __name__ == "__main__":
    draw_perfect_schematic()
