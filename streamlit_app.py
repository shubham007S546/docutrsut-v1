"""
DOCUTRUST: Evidence-Grounded Agentic Multi-Agent RAG System
Root Streamlit Entrypoint
"""
import sys
from pathlib import Path

# Add project root and RAG_project to sys.path
ROOT_DIR = Path(__file__).resolve().parent
RAG_DIR = ROOT_DIR / "RAG_project"
for d in [str(ROOT_DIR), str(RAG_DIR)]:
    if d not in sys.path:
        sys.path.insert(0, d)

# Execute RAG_project/streamlit_app.py
with open(RAG_DIR / "streamlit_app.py", encoding="utf-8") as f:
    code = f.read()

exec(code, globals())
