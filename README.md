<div align="center">

<img src="public/icon.svg" alt="DocuTrust Logo" width="80" height="80"/>

# DocuTrust

### Evidence-Grounded Agentic Policy Intelligence Platform

*A trust-oriented multi-agent RAG system for auditable enterprise compliance decisions*

[![Next.js](https://img.shields.io/badge/Next.js-16.3-black?logo=next.js&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791?logo=postgresql&logoColor=white)](https://neon.tech)
[![License](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-19%2F19%20passing-22c55e)](test_docutrust_suite.py)

[Live Demo](#) · [Quick Start](#quick-start) · [Deployment](#deployment) · [API Docs](http://localhost:8000/docs)

</div>

---

## What is DocuTrust?

DocuTrust answers compliance questions using **only evidence grounded in your uploaded documents**. It never hallucinates — if the answer is not in your documents, it explicitly refuses and escalates to a human reviewer.

**The core promise:** Every answer is cited, confidence-scored, claim-verified, and cryptographically receipted. Every decision is auditable.

```
Upload policy PDFs  →  Ask a question  →  Get a cited, scored, receipted answer
```

---

## Problem It Solves

| Traditional Approach | DocuTrust |
|---|---|
| LLM gives confident-sounding wrong answers | Abstains when evidence is insufficient |
| No source attribution | Every claim linked to a document chunk |
| Black-box decisions | Full audit trail with SHA-256 receipt |
| Single model, single failure point | 7 specialist agents + provider fallback chain |
| No conflict detection | Detects contradictions across policy versions |
| Manual compliance review | Automated escalation to human review queue |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER QUERY                               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              SUPERVISOR PLANNER (Intent Classification)         │
│  • Keyword + regex routing into bounded AgentPlan               │
│  • Max 3 iterations · Max 12 tool calls                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│           HYBRID RETRIEVAL ENGINE (Tenant-Isolated)             │
│                                                                 │
│   Dense Search (FAISS)        Sparse Search (BM25)              │
│   sentence-transformers/      rank-bm25 / BM25Okapi             │
│   all-MiniLM-L6-v2                                              │
│           │                           │                         │
│           └──────────┬────────────────┘                         │
│                      ▼                                          │
│          Reciprocal Rank Fusion (k=60)                          │
│          Cross-Encoder Reranking                                │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼ EVIDENCE PASSAGES
┌─────────────────────────────────────────────────────────────────┐
│                    SUFFICIENCY GATE                             │
│   coverage ≥ 0.30  AND  relevance ≥ 0.50  AND  chunks ≥ 1     │
└──────────┬────────────────────────────────────────┬────────────┘
           │                                        │
    [INSUFFICIENT]                           [SUFFICIENT]
           │                                        │
           ▼                                        ▼
┌──────────────────────┐              ┌─────────────────────────┐
│  ABSTAIN & ESCALATE  │              │   7 SPECIALIST AGENTS   │
│                      │              │                         │
│  • Log to review     │              │  Policy · Privacy       │
│    queue             │              │  Security · Legal       │
│  • requires_review   │              │  Conflict · Verify      │
│    = true            │              │  Report                 │
│  • Return grounded   │              └────────────┬────────────┘
│    refusal message   │                           │
└──────────────────────┘                           ▼
                               ┌─────────────────────────────────┐
                               │     CLAIM-LEVEL VERIFICATION    │
                               │  SUPPORTED / PARTIALLY /        │
                               │  CONTRADICTED / UNVERIFIABLE    │
                               └────────────────┬────────────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │      CONFIDENCE FORMULA         │
                               │                                 │
                               │  Score = w1·R + w2·C + w3·A    │
                               │          + w4·V - w5·F         │
                               │                                 │
                               │  R = Retrieval relevance        │
                               │  C = Query term coverage        │
                               │  A = Inter-document agreement   │
                               │  V = Verified claim ratio       │
                               │  F = Conflict penalty           │
                               │                                 │
                               │  Threshold: 0.70               │
                               └────────────────┬────────────────┘
                                                │
                         ┌──────────────────────┴──────────────────┐
                    [< 0.70]                                   [≥ 0.70]
                         │                                         │
                         ▼                                         ▼
               HUMAN REVIEW QUEUE                      DECISION SYNTHESIS
               (Approve / Reject /                              │
               Request Evidence)                                ▼
                                               ┌─────────────────────────┐
                                               │  SHA-256 EVIDENCE       │
                                               │  RECEIPT                │
                                               │  query + answer +       │
                                               │  timestamp + chunk IDs  │
                                               └─────────────────────────┘
```

---

## Seven Specialist Agents

| Agent | Domain | What It Does |
|---|---|---|
| 🏢 **Policy** | HR & Operations | Employee handbooks, WFH limits, hours, allowances |
| 🔒 **Privacy** | Data Protection | GDPR, retention schedules, consent, data subject rights |
| 🛡️ **Security** | InfoSec | Encryption, MFA, credentials, endpoint controls |
| ⚖️ **Legal** | Compliance | Contracts, jurisdiction, statutory obligations |
| ⚡ **Conflict** | Resolution | Version diffs, departmental exceptions, hierarchy precedence |
| ✅ **Verification** | Claim Audit | Sentence-level claim extraction vs. cited evidence passages |
| 📄 **Report** | Synthesis | Audit brief + cryptographic evidence receipt |

---

## Trust Invariants

These are **system-level guarantees** — not aspirational features:

- **Bounded execution** — hard cap: 3 iterations, 12 tool calls. No infinite loops.
- **Absence-of-evidence abstention** — if the corpus doesn't contain an answer, it refuses with a grounded message rather than speculating.
- **Zero cross-tenant leakage** — every FAISS index, BM25 corpus, and DB row is scoped to `tenant_id`. Verified by probe tests.
- **Prompt injection defence** — document content is delimited as data; the system prompt instructs the model to ignore any instructions embedded in documents.
- **Tool sandboxing** — only 11 allowlisted tools (all retrieval/analysis). No shell, no web navigation, no arbitrary code execution.

---

## Tech Stack

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| Next.js | 16.3.3 | App Router, SSR, API routes (BFF) |
| React | 19 | UI framework |
| TypeScript | 5.7.3 | Type safety |
| Tailwind CSS | 4.3 | Styling |
| Better Auth | 1.7 | Authentication (email/password, HTTP-only cookies) |
| Drizzle ORM | 0.45 | Type-safe DB schema and queries |
| Vercel Blob | 2.8 | Raw file storage |
| Recharts | 3.8 | Analytics charts |
| Lucide React | 1.16 | Icons |
| AI SDK | 7.0 | Streaming AI responses |

### Backend
| Technology | Version | Purpose |
|---|---|---|
| FastAPI | 0.115 | REST API + streaming |
| Python | 3.12 | Runtime |
| Uvicorn | 0.30 | ASGI server |
| Pydantic v2 | 2.8 | Request/response validation |
| asyncpg | 0.29 | Async PostgreSQL driver |
| FAISS-CPU | 1.8 | Dense vector search |
| sentence-transformers | 3.0 | Embeddings (`all-MiniLM-L6-v2`) + reranking (`ms-marco-MiniLM-L-6-v2`) |
| rank-bm25 | 0.2 | BM25 sparse retrieval |
| PyPDF | 5.0 | PDF text extraction |
| httpx | 0.27 | Async HTTP (AI provider calls) |
| Groq SDK | 0.11 | Groq LLM API |

### Infrastructure
| Service | Purpose |
|---|---|
| Neon (PostgreSQL) | Serverless database — tenants, documents, chunks, query runs, reviews |
| Vercel Blob | Raw uploaded file persistence |
| Groq | Primary LLM (llama-3.3-70b-versatile) |
| Google Gemini | Secondary LLM fallback |
| Deterministic grounded fallback | Final fallback — zero hallucination during provider outages |

---

## Database Schema

```sql
docutrust_tenants        -- Tenant registry (one per user account)
docutrust_documents      -- Uploaded policy files (metadata + SHA-256)
docutrust_document_chunks -- Text chunks with page/char positions
docutrust_query_runs     -- Every query: question, answer, confidence, evidence, trace
docutrust_reviews        -- Human review decisions (approve/reject/request_more)

-- Auth tables (managed by better-auth)
user · session · account · verification
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/ready` | Readiness check (all subsystems) |
| `GET` | `/status` | Provider + storage status |
| `POST` | `/query` | Submit a policy question |
| `GET` | `/runs/{id}` | Get query run result |
| `GET` | `/documents` | List tenant documents |
| `POST` | `/ingest` | Ingest a document into RAG |
| `POST` | `/review` | Submit human review decision |
| `GET` | `/evaluations` | Run automated evaluation suite |
| `POST` | `/policy/impact` | Compute policy version diff |

Full interactive docs at `http://localhost:8000/docs`

---

## Quick Start

### Prerequisites

- **Node.js** 22+ and **pnpm** (`npm install -g pnpm`)
- **Python** 3.12+
- A **[Neon](https://neon.tech)** account (free tier — create a database)
- A **[Groq](https://console.groq.com)** API key (free tier)
- A **[Vercel](https://vercel.com)** account (free — for Blob storage)

---

### Step 1 — Clone the repository

```bash
git clone https://github.com/shubham007S546/docutrsut-v1.git
cd docutrsut-v1
```

---

### Step 2 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your real values (minimum required):

```env
DATABASE_URL=postgresql://...          # from Neon dashboard
BETTER_AUTH_SECRET=<32-char-random>    # run: openssl rand -hex 32
BETTER_AUTH_URL=http://localhost:3000  # your app URL
GROQ_API_KEY=gsk_...                   # from console.groq.com
BLOB_READ_WRITE_TOKEN=vercel_blob_...  # from Vercel storage dashboard
STORAGE_MODE=postgres
```

---

### Step 3 — Start the Python backend

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Start the server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify:
```bash
curl http://localhost:8000/health
# → {"status":"ok","service":"docutrust-api","version":"3.2.0"}

curl http://localhost:8000/ready
# → {"api":"ok","rag_engine":"ready","ai_provider":"configured",...}
```

---

### Step 4 — Start the Next.js frontend

Open a new terminal:

```bash
pnpm install
pnpm dev
```

Open → **http://localhost:3000**

---

### Step 5 — Test the full stack

```bash
# Backend unit tests (13 tests)
python -m pytest backend/tests/ -v

# Compliance & trust suite (6 integration scenarios)
python -m pytest test_docutrust_suite.py -v
```

Expected output:
```
✅  test_tenant_isolation          PASSED
✅  test_scenario_wfh_limit        PASSED  (confidence: 0.79)
✅  test_scenario_antarctica        PASSED  (abstained correctly)
✅  test_scenario_hierarchy_conflict PASSED
✅  test_scenario_policy_diff       PASSED  (impact: HIGH)
✅  test_cryptographic_receipt      PASSED  (SHA-256 verified)
```

---

## Deployment

### Option A — Vercel + Railway (Recommended · Free tier available)

This is the easiest path. No server management required.

---

#### Step 1 — Delete the old GitHub repo history (already done)

Your repo at `https://github.com/shubham007S546/docutrsut-v1` is clean and ready.

---

#### Step 2 — Deploy the Frontend on Vercel

1. Go to **https://vercel.com/new**
2. Click **"Import Git Repository"**
3. Connect your GitHub account if not already connected
4. Select **`docutrsut-v1`** from the list
5. Vercel auto-detects Next.js — leave all settings as default
6. Click **Deploy** → wait ~2 minutes

You will get a URL like: `https://docutrsut-v1.vercel.app`

7. Go to your Vercel project → **Settings → Environment Variables**
8. Add each variable from your `.env` file, **but change these**:

| Variable | Value for Production |
|---|---|
| `BETTER_AUTH_URL` | `https://docutrsut-v1.vercel.app` |
| `CORS_ORIGINS` | `https://docutrsut-v1.vercel.app` |
| `ENVIRONMENT` | `production` |
| `BETTER_AUTH_SECRET` | Your secret (same as local) |
| `DATABASE_URL` | Your Neon URL (same as local) |
| `GROQ_API_KEY` | Your Groq key (same as local) |
| `BLOB_READ_WRITE_TOKEN` | Your Vercel Blob token |

9. Go to **Deployments** → click **Redeploy** (to pick up the env vars)

---

#### Step 3 — Deploy the Python Backend on Railway

1. Go to **https://railway.app** → click **New Project**
2. Select **"Deploy from GitHub repo"**
3. Authorize Railway and select **`docutrsut-v1`**
4. Railway will auto-detect Python — click **Deploy**
5. Once deployed, go to **Settings → Service**:
   - Set **Start Command** to:
     ```
     python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
     ```
   - Set **Root Directory** to: *(leave blank — backend imports work from project root)*
6. Go to **Variables** → add all your `.env` values, **changing**:

| Variable | Value |
|---|---|
| `CORS_ORIGINS` | `https://docutrsut-v1.vercel.app` |
| `ENVIRONMENT` | `production` |

7. Railway gives you a public URL like:
   `https://docutrsut-v1-backend.up.railway.app`

---

#### Step 4 — Connect Frontend to Backend

Back in Vercel → **Settings → Environment Variables**, add:

```
NEXT_PUBLIC_BACKEND_URL=https://docutrsut-v1-backend.up.railway.app
```

Then **Redeploy** on Vercel again.

---

#### Step 5 — Verify Production

```bash
# Backend health
curl https://docutrsut-v1-backend.up.railway.app/health

# Frontend
# Open https://docutrsut-v1.vercel.app in browser
# Sign up → Upload a PDF → Ask a question → Verify answer has citations
```

---

### Option B — Docker on a VPS

Use this for full control (DigitalOcean, AWS EC2, Hetzner, etc.)

#### Requirements
- Ubuntu 22.04 server with minimum **2GB RAM** (ML models need memory)
- Docker + Docker Compose installed

```bash
# SSH into your server
ssh root@YOUR_SERVER_IP

# Install Docker
curl -fsSL https://get.docker.com | sh
apt-get install -y docker-compose-plugin

# Clone the repo
git clone https://github.com/shubham007S546/docutrsut-v1.git
cd docutrsut-v1

# Configure environment
cp .env.example .env
nano .env
# Change: BETTER_AUTH_URL=http://YOUR_SERVER_IP:3000
# Change: CORS_ORIGINS=http://YOUR_SERVER_IP:3000

# Build and start
docker compose up --build -d

# Check status
docker compose ps
curl http://localhost:8000/health
# Open http://YOUR_SERVER_IP:3000 in browser
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and run the test suite
4. Commit: `git commit -m "feat: your feature description"`
5. Push: `git push origin feature/your-feature`
6. Open a Pull Request

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

**DocuTrust** — Evidence-grounded. Auditable. Trustworthy.

Built with ❤️ · [Report a Bug](https://github.com/shubham007S546/docutrsut-v1/issues) · [Request a Feature](https://github.com/shubham007S546/docutrsut-v1/issues)

</div>
