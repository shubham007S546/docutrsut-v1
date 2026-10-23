# =============================================================================
# compile_paper.ps1
# Compiles the DocuTrust IEEE-style LaTeX paper to PDF on Windows (MiKTeX).
# Usage:   .\research\paper\compile_paper.ps1
#          .\research\paper\compile_paper.ps1 -Clean
# =============================================================================

param([switch]$Clean)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $ScriptDir

$TexFile  = "docutrust_paper.tex"
$JobName  = "docutrust_paper"
$Log      = "compile.log"

Write-Host "=== DocuTrust Paper Compiler (Windows) ===" -ForegroundColor Cyan
Write-Host "Working directory: $ScriptDir"

# ─── Clean ───────────────────────────────────────────────────
if ($Clean) {
    Write-Host "Cleaning build artifacts..." -ForegroundColor Yellow
    $exts = @("aux","bbl","blg","log","out","pdf","toc","lof","lot","synctex.gz")
    foreach ($ext in $exts) {
        $file = "$JobName.$ext"
        if (Test-Path $file) { Remove-Item $file -Force; Write-Host "  Removed $file" }
    }
    Write-Host "Clean complete." -ForegroundColor Green
    Pop-Location; exit 0
}

# ─── Check prerequisites ─────────────────────────────────────
foreach ($cmd in @("pdflatex", "bibtex")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: '$cmd' not found." -ForegroundColor Red
        Write-Host "  Install MiKTeX from https://miktex.org/download"
        Write-Host "  Or TeX Live from https://tug.org/texlive/"
        Pop-Location; exit 1
    }
}

# ─── 4-pass compilation ──────────────────────────────────────
"" > $Log

Write-Host ""
Write-Host "Pass 1/4: Initial pdflatex..." -ForegroundColor DarkCyan
pdflatex -interaction=nonstopmode $TexFile >> $Log 2>&1

Write-Host "Pass 2/4: bibtex..." -ForegroundColor DarkCyan
bibtex $JobName >> $Log 2>&1

Write-Host "Pass 3/4: pdflatex (resolve refs)..." -ForegroundColor DarkCyan
pdflatex -interaction=nonstopmode $TexFile >> $Log 2>&1

Write-Host "Pass 4/4: pdflatex (finalize)..." -ForegroundColor DarkCyan
pdflatex -interaction=nonstopmode $TexFile >> $Log 2>&1

# ─── Result ──────────────────────────────────────────────────
$PDF = "$JobName.pdf"
if (Test-Path $PDF) {
    $Size = (Get-Item $PDF).Length / 1KB
    Write-Host ""
    Write-Host "=== SUCCESS ===" -ForegroundColor Green
    Write-Host "  PDF: $ScriptDir\$PDF ($([math]::Round($Size, 1)) KB)"
    Write-Host "  Figures: $ScriptDir\figures\"
    Write-Host "  Log: $ScriptDir\$Log"
} else {
    Write-Host ""
    Write-Host "=== COMPILATION FAILED ===" -ForegroundColor Red
    Write-Host "  Check $ScriptDir\$Log for details."
    Get-Content $Log | Select-String -Pattern "error|fatal|undefined" | Select-Object -First 20
    Pop-Location; exit 1
}

Pop-Location
