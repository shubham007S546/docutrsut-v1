#!/usr/bin/env bash
# =============================================================================
# compile_paper.sh
# Compiles the DocuTrust IEEE-style LaTeX paper to PDF.
# Requirements: TeX Live / MiKTeX with IEEEtran, amsmath, booktabs, etc.
# Usage:   bash research/paper/compile_paper.sh
#          bash research/paper/compile_paper.sh --clean
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

TEX_FILE="docutrust_paper.tex"
BIB_FILE="docutrust_refs.bib"
JOB_NAME="docutrust_paper"
LOG="compile.log"

echo "=== DocuTrust Paper Compiler ==="
echo "Working directory: $SCRIPT_DIR"

# ─── Clean if requested ──────────────────────────────────────
if [[ "${1:-}" == "--clean" ]]; then
  echo "Cleaning build artifacts..."
  rm -f "${JOB_NAME}."{aux,bbl,blg,log,out,pdf,toc,lof,lot,synctex.gz}
  echo "Clean complete."
  exit 0
fi

# ─── Check prerequisites ─────────────────────────────────────
for cmd in pdflatex bibtex; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' not found. Please install TeX Live or MiKTeX."
    echo "  Ubuntu/Debian: sudo apt-get install texlive-full"
    echo "  macOS:         brew install --cask mactex"
    echo "  Windows:       https://miktex.org/download"
    exit 1
  fi
done

# ─── 4-pass compilation (standard for IEEEtran + bibtex) ─────
echo ""
echo "Pass 1/4: Initial pdflatex..."
pdflatex -interaction=nonstopmode "$TEX_FILE" >> "$LOG" 2>&1

echo "Pass 2/4: bibtex..."
bibtex "$JOB_NAME" >> "$LOG" 2>&1 || true

echo "Pass 3/4: pdflatex (resolve refs)..."
pdflatex -interaction=nonstopmode "$TEX_FILE" >> "$LOG" 2>&1

echo "Pass 4/4: pdflatex (finalize)..."
pdflatex -interaction=nonstopmode "$TEX_FILE" >> "$LOG" 2>&1

# ─── Check output ─────────────────────────────────────────────
PDF="${JOB_NAME}.pdf"
if [[ -f "$PDF" ]]; then
  SIZE=$(du -sh "$PDF" | cut -f1)
  echo ""
  echo "=== SUCCESS ==="
  echo "  PDF produced: $SCRIPT_DIR/$PDF ($SIZE)"
  echo "  Figures expected in: $SCRIPT_DIR/figures/"
  echo "  Full build log: $SCRIPT_DIR/$LOG"
else
  echo ""
  echo "=== COMPILATION FAILED ==="
  echo "  Check $SCRIPT_DIR/$LOG for error details."
  grep -i "error\|fatal\|undefined" "$LOG" | head -30 || true
  exit 1
fi
