# DocuTrust Reproducibility Checklist & Environment Specification

This document details the exact environment, dependencies, commands, and seeds required to reproduce all findings and test runs in DocuTrust.

---

## 1. System & Hardware Environment

- **Operating System:** Windows 11 / Windows Server (PowerShell 5.1+)
- **Python Runtime:** Python 3.12.10
- **Node.js Runtime:** Node.js v20+ / pnpm v9+
- **Terminal Encoding Requirement:** `$env:PYTHONIOENCODING="utf-8"` (prevents cp1252 character mapping crashes with unicode non-breaking hyphens)

---

## 2. Key Dependencies & Model Checkpoints

| Dependency | Version / Checkpoint | License | Purpose |
|---|---|---|---|
| `sentence-transformers` | `sentence-transformers/all-MiniLM-L6-v2` | Apache 2.0 | Dense passage and query vector embeddings (384-dim) |
| `faiss-cpu` | 1.8.0+ | MIT | In-process inner-product similarity search |
| `rank-bm25` | 0.2.2+ | Apache 2.0 | Sparse lexical keyword scoring |
| `fastapi` | 0.110+ | MIT | Backend agent runtime |
| `pydantic` | 2.6+ | MIT | Contract definitions and schema validation |
| `pytest` | 9.0.2 | MIT | Automated test verification |
| `groq` / `google-generativeai` | Cloud APIs | Proprietary / API | LLM generation fallback chain |

---

## 3. Verification Commands

### Backend Test Suite (13 Unit & Security Tests)
```powershell
$env:PYTHONIOENCODING="utf-8"
python -m pytest backend/tests
```
*Expected Result:* `13 passed in ~2.3s`

### Compliance Integration Suite (6 Core Scenarios)
```powershell
$env:PYTHONIOENCODING="utf-8"
python test_docutrust_suite.py
```
*Expected Result:*
- Tenant Isolation: PASS (0 leaks)
- Scenario 1 (WFH Limit): Grounded, Confidence >= 0.65
- Scenario 2 (Antarctica): Abstains, Escalates to Review
- Scenario 3 (4 Days WFH): Conflict Detected, Escalates
- Scenario 4 (Policy Diff): v1 vs v2 HIGH impact computed
- Scenario 6 (Cryptographic Receipt): 64-character SHA-256 hash verified

### Replication of Current Evaluation Service
```powershell
$env:PYTHONIOENCODING="utf-8"
python -c "import asyncio, json; from backend.evaluation_service import evaluation_service; res = asyncio.run(evaluation_service.run_evaluation_suite()); print(json.dumps(res, indent=2))"
```
*Expected Output:*
- Replicates Precision@K (16.7%), Recall@K (50.0%), Conflict Detection Rate (25.0%), and Citation Coverage (100.0%).
