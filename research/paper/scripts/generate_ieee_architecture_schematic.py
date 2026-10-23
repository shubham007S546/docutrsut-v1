#!/usr/bin/env python3
"""
generate_ieee_architecture_schematic.py
Generates the publication-grade IEEE Transactions architecture schematic for DocuTrust.
Strictly eliminates:
- Container border overlap (Reject Alert is safely inside Module 1, 8 units above Modules 2 & 3).
- Bounding box text overflow (all subtitles and titles have tested widths and font sizes).
- Diamond clipping (diamonds use compact centered text).
- 100% orthogonal Manhattan routing with clear labeled paths.
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PAPER_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
FIG_DIR = os.path.join(PAPER_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

def generate_schematic():
    plt.close("all")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Segoe UI", "DejaVu Sans"],
        "mathtext.fontset": "cm",
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight"
    })

    fig, ax = plt.subplots(figsize=(16, 9.2))
    ax.set_xlim(0, 160)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # High-Contrast WCAG-Compliant Palette
    C_CONTAINER_GREEN_BG = "#F0FDF4"
    C_CONTAINER_GREEN_BD = "#16A34A"
    C_CONTAINER_PURPLE_BG = "#FAF5FF"
    C_CONTAINER_PURPLE_BD = "#9333EA"
    C_CONTAINER_RED_BG = "#FEF2F2"
    C_CONTAINER_RED_BD = "#DC2626"
    
    C_BLUE_BOX_BG = "#E0F2FE"
    C_BLUE_BOX_BD = "#0284C7"
    C_GREY_STAGE_BG = "#F1F5F9"
    C_GREY_STAGE_BD = "#64748B"
    C_ORANGE_STAGE_BG = "#FFEDD5"
    C_ORANGE_STAGE_BD = "#EA580C"
    C_CORAL_STAGE_BG = "#FFE4E6"
    C_CORAL_STAGE_BD = "#E11D48"
    C_WHITE_BOX_BG = "#FFFFFF"
    C_WHITE_BOX_BD = "#475569"
    C_PURPLE_BOX_BG = "#F3E8FF"
    C_PURPLE_BOX_BD = "#7E22CE"
    C_GREEN_BOX_BG = "#DCFCE7"
    C_GREEN_BOX_BD = "#15803D"
    C_AMBER_BOX_BG = "#FEF3C7"
    C_AMBER_BOX_BD = "#D97706"
    C_RED_ALERT_BG = "#FEE2E2"
    C_RED_ALERT_BD = "#B91C1C"
    WIRE_COLOR = "#334155"

    def draw_container(x, y, w, h, title, border, bg):
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25",
                              facecolor=bg, edgecolor=border,
                              linestyle="--", linewidth=1.3, zorder=1)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h - 2.2, f"  {title}  ",
                ha="center", va="center", fontsize=8.6,
                fontweight="bold", color="#0F172A",
                bbox=dict(boxstyle="round,pad=0.25", facecolor=bg, edgecolor=border, lw=0.8),
                zorder=2)

    def draw_box(x, y, w, h, title, subtitle="", bg="#FFFFFF", border="#475569", title_color="#0F172A", sub_color="#334155"):
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.18",
                              facecolor=bg, edgecolor=border,
                              linestyle="-", linewidth=1.1, zorder=3)
        ax.add_patch(rect)
        if subtitle:
            ax.text(x + w / 2, y + h / 2 + 1.1, title,
                    ha="center", va="center", fontsize=7.6,
                    fontweight="bold", color=title_color, zorder=4)
            ax.text(x + w / 2, y + h / 2 - 1.1, subtitle,
                    ha="center", va="center", fontsize=6.6,
                    color=sub_color, zorder=4)
        else:
            ax.text(x + w / 2, y + h / 2, title,
                    ha="center", va="center", fontsize=7.6,
                    fontweight="bold", color=title_color, zorder=4)

    def draw_diamond(x, y, w, h, text1, text2="", bg="#F1F5F9", border="#475569"):
        pts = np.array([
            [x + w / 2, y + h],
            [x + w, y + h / 2],
            [x + w / 2, y],
            [x, y + h / 2]
        ])
        diamond = Polygon(pts, closed=True, facecolor=bg, edgecolor=border,
                          linewidth=1.2, zorder=3)
        ax.add_patch(diamond)
        if text2:
            ax.text(x + w / 2, y + h / 2 + 0.8, text1, ha="center", va="center",
                    fontsize=7.0, fontweight="bold", color="#0F172A", zorder=4)
            ax.text(x + w / 2, y + h / 2 - 0.8, text2, ha="center", va="center",
                    fontsize=6.4, color="#334155", zorder=4)
        else:
            ax.text(x + w / 2, y + h / 2, text1, ha="center", va="center",
                    fontsize=7.2, fontweight="bold", color="#0F172A", zorder=4)

    def draw_wire(points, label="", lbl_pos="top", arrow=True):
        xs, ys = zip(*points)
        ax.plot(xs, ys, color=WIRE_COLOR, linewidth=1.3, zorder=2)
        if arrow:
            ax.annotate("", xy=points[-1], xytext=points[-2],
                        arrowprops=dict(arrowstyle="-|>", color=WIRE_COLOR,
                                       lw=1.3, mutation_scale=11), zorder=2)
        if label:
            mx = (points[0][0] + points[1][0]) / 2
            my = (points[0][1] + points[1][1]) / 2
            dy = 1.3 if lbl_pos == "top" else (-1.3 if lbl_pos == "bottom" else 0)
            dx = 1.6 if lbl_pos == "right" else (-1.6 if lbl_pos == "left" else 0)
            ax.text(mx + dx, my + dy, label, fontsize=6.8, fontweight="bold",
                    color="#0F172A", ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#FFFFFF", edgecolor="#CBD5E1", lw=0.6),
                    zorder=5)

    # -------------------------------------------------------------------------
    # TOP ROW: INGESTION & DUAL INDEX STORE (Y: 52 to 96)
    # -------------------------------------------------------------------------
    draw_box(2, 65, 12, 14, "Raw Query q", "(Compliance Task)", bg=C_BLUE_BOX_BG, border=C_BLUE_BOX_BD)
    draw_box(15.5, 65, 14, 14, "Stage 1:\nSecurity &\nScope Audit", bg=C_GREY_STAGE_BG, border=C_GREY_STAGE_BD)
    draw_wire([(14, 72), (15.5, 72)])

    # Module 1 Container: Y in [52, 96]
    draw_container(32, 52, 125, 44, "Module 1: Document Ingestion & Dual Index Store",
                   border=C_CONTAINER_GREEN_BD, bg=C_CONTAINER_GREEN_BG)

    draw_box(34.5, 77.5, 26, 8.5, "Tenant Scope Validation",
             "(Row-Level Isolation & Auth)", bg=C_GREY_STAGE_BG, border=C_WHITE_BOX_BD)
    draw_box(34.5, 63.5, 26, 8.5, "Semantic Tokenizer & Chunker",
             "(L=512 Chunks + SHA-256)", bg=C_GREY_STAGE_BG, border=C_WHITE_BOX_BD)

    draw_wire([(29.5, 72), (32, 72), (32, 81.75), (34.5, 81.75)])
    draw_wire([(29.5, 72), (32, 72), (32, 67.75), (34.5, 67.75)])

    draw_diamond(64.5, 69.5, 15, 11, "Tenant & Format", "Passed?", bg="#E2E8F0", border=C_WHITE_BOX_BD)
    draw_wire([(60.5, 81.75), (62.5, 81.75), (62.5, 75), (64.5, 75)])
    draw_wire([(60.5, 67.75), (62.5, 67.75), (62.5, 75), (64.5, 75)])

    # Reject Alert: Safe inside Module 1 at Y in [54.5, 62], completely above Module 2/3 (which start at Y <= 44)
    draw_box(63.5, 54.5, 17, 7.5, "Reject Alert",
             "(Security Halt & Log)", bg=C_RED_ALERT_BG, border=C_RED_ALERT_BD,
             title_color="#991B1B", sub_color="#7F1D1D")
    draw_wire([(72, 69.5), (72, 62)], label="No", lbl_pos="right")

    draw_wire([(79.5, 75), (85, 75)], label="Yes", lbl_pos="top")

    draw_box(85, 69.5, 23, 11, "Dual-Store Indexing",
             "(BM25 Lexical + FAISS Dense)", bg=C_WHITE_BOX_BG, border=C_CONTAINER_GREEN_BD)
    draw_wire([(108, 75), (113, 75)])

    draw_box(113, 69.5, 24, 11, "Policy Version Lineage",
             "(Active Dates & Supersession)", bg=C_WHITE_BOX_BG, border=C_CONTAINER_GREEN_BD)
    draw_wire([(137, 75), (142, 75)])

    draw_box(142, 69.5, 13, 11, "Passages E_k\n(Top-K Pool)",
             bg=C_WHITE_BOX_BG, border=C_CONTAINER_GREEN_BD)

    # Z-Bus Wire from Module 1 down to Stage 2: routes through clear whitespace at Y=48
    draw_wire([(148.5, 69.5), (148.5, 48), (3.5, 48), (3.5, 34), (4.5, 34)],
              label="Evidence Pool E_k & Query q", lbl_pos="top")

    # -------------------------------------------------------------------------
    # BOTTOM ROW: MULTI-AGENT, VERIFICATION & DEPLOYMENT (Y: 2 to 44)
    # -------------------------------------------------------------------------
    draw_box(4.5, 27, 24, 14, "Stage 2: Supervisor Agent",
             "(Plan & Specialist Dispatch)", bg=C_ORANGE_STAGE_BG, border=C_ORANGE_STAGE_BD)

    # Module 2 Container: Multi-Specialist RAG
    draw_container(32, 2, 38, 42, "Module 2: Multi-Specialist RAG Engine",
                   border=C_CONTAINER_PURPLE_BD, bg=C_CONTAINER_PURPLE_BG)

    draw_box(34.5, 30.5, 33, 7.5, "Security Specialist Agent",
             "(MFA, Encryption, Hardware)", bg=C_PURPLE_BOX_BG, border=C_PURPLE_BOX_BD)
    draw_box(34.5, 21.5, 33, 7.5, "Privacy Specialist Agent",
             "(GDPR 72h SLA, Retention)", bg=C_PURPLE_BOX_BG, border=C_PURPLE_BOX_BD)
    draw_box(34.5, 12.5, 33, 7.5, "Policy Specialist Agent",
             "(Day Limits, Approvals, Caps)", bg=C_PURPLE_BOX_BG, border=C_PURPLE_BOX_BD)
    draw_box(34.5, 3.5, 33, 7.5, "Hybrid Fusion & Neural Rerank",
             "(RRF k=60 + Cross-Encoder)", bg=C_WHITE_BOX_BG, border=C_PURPLE_BOX_BD)

    draw_wire([(28.5, 34), (31.5, 34), (31.5, 34.25), (34.5, 34.25)])
    draw_wire([(28.5, 34), (31.5, 34), (31.5, 25.25), (34.5, 25.25)])
    draw_wire([(28.5, 34), (31.5, 34), (31.5, 16.25), (34.5, 16.25)])
    draw_wire([(51, 12.5), (51, 11)])

    draw_wire([(67.5, 7.25), (73, 7.25)])

    # Module 3 Container: Verification & Abstention
    draw_container(73, 2, 38, 42, "Module 3: Verification & Abstention",
                   border=C_CONTAINER_GREEN_BD, bg=C_CONTAINER_GREEN_BG)

    draw_box(75.5, 30.5, 33, 7.5, "Active-Version Filter",
             "(Prune Superseded Clauses)", bg=C_GREEN_BOX_BG, border=C_GREEN_BOX_BD)
    draw_box(75.5, 21.5, 33, 7.5, "Cross-Doc Conflict Detector",
             "(Policy Authority Lattice)", bg=C_GREEN_BOX_BG, border=C_GREEN_BOX_BD)
    draw_box(75.5, 12.5, 33, 7.5, "Sentence-Level NLI Verifier",
             "(Claim Entailment \u2265 0.85)", bg=C_GREEN_BOX_BG, border=C_GREEN_BOX_BD)

    draw_diamond(79.5, 3.5, 25, 7.5, "Confidence Router", "\u03a9 \u2265 0.70?",
                 bg=C_AMBER_BOX_BG, border=C_AMBER_BOX_BD)

    draw_wire([(67.5, 7.25), (70.5, 7.25), (70.5, 34.25), (75.5, 34.25)])
    draw_wire([(92, 30.5), (92, 29)])
    draw_wire([(92, 21.5), (92, 20)])
    draw_wire([(92, 12.5), (92, 11)])

    draw_wire([(104.5, 7.25), (109, 7.25), (109, 23), (113, 23)])

    # Stage 4: Decision Dispatch & Provenance Notary
    draw_box(113, 13, 14, 20, "Stage 4:\nDecision\nDispatch &\nNotary",
             bg=C_CORAL_STAGE_BG, border=C_CORAL_STAGE_BD)

    # System Deployment & Output Container
    draw_container(129.5, 2, 28.5, 42, "System Deployment & Output",
                   border=C_CONTAINER_RED_BD, bg=C_CONTAINER_RED_BG)

    draw_box(131.5, 32.5, 24.5, 7.5, "Attributed Answer",
             "(Entailed Text + Citations)", bg=C_GREEN_BOX_BG, border=C_GREEN_BOX_BD)
    draw_box(131.5, 22.5, 24.5, 7.5, "Provenance Receipt",
             "(Signed SHA-256 Merkle)", bg=C_WHITE_BOX_BG, border=C_WHITE_BOX_BD)
    draw_box(131.5, 12.5, 24.5, 7.5, "Escalate Review Ticket",
             "(Conflict / 0.4 \u2264 \u03a9 < 0.7)", bg=C_AMBER_BOX_BG, border=C_AMBER_BOX_BD)
    draw_box(131.5, 2.5, 24.5, 7.5, "Safe Abstention Notice",
             "(Zero Hallucination / OOD)", bg=C_RED_ALERT_BG, border=C_RED_ALERT_BD)

    draw_wire([(127, 23), (129, 23), (129, 36.25), (131.5, 36.25)])
    draw_wire([(127, 23), (129, 23), (129, 26.25), (131.5, 26.25)])
    draw_wire([(127, 23), (129, 23), (129, 16.25), (131.5, 16.25)])
    draw_wire([(127, 23), (129, 23), (129, 6.25), (131.5, 6.25)])

    png_path = os.path.join(FIG_DIR, "fig2_architecture.png")
    pdf_path = os.path.join(FIG_DIR, "fig2_architecture.pdf")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Generated clean architecture schematic:\n  - {png_path}\n  - {pdf_path}")
    return png_path, pdf_path

if __name__ == "__main__":
    generate_schematic()
