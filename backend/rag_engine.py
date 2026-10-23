from __future__ import annotations

import datetime
import math
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from backend.config import settings

# Ensure RAG_project is available on sys.path
RAG_PROJECT_DIR = Path(__file__).resolve().parent.parent / "RAG_project"
if str(RAG_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_PROJECT_DIR))

# Import actual RAG_project components
from chunking.text_splitter import TextSplitter
from loaders.pdf_loader import Document
from retriever.bm25 import BM25Retriever
from vectorstore.faiss_db import FAISSVectorStore


@dataclass
class EvidenceRecord:
    evidence_id: str
    document_id: str
    document_name: str
    tenant_id: str
    chunk_id: str
    text: str
    retrieval_score: float
    page_number: int | None = 1
    page_start: int | None = 1
    page_end: int | None = 1
    section: str = "Section 1"
    policy_version: str = "v1"
    effective_from: str = "2024-01-01"
    effective_to: str = "Present"
    source_type: str = "upload"
    bm25_score: float = 0.0
    faiss_score: float = 0.0
    rrf_score: float = 0.0
    ce_score: float | None = None
    retrieval_diagnostics: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_GLOBAL_EMBEDDING_MODEL = None
_GLOBAL_CROSS_ENCODER = None


def _get_shared_embedding_model():
    global _GLOBAL_EMBEDDING_MODEL
    if _GLOBAL_EMBEDDING_MODEL is None:
        try:
            from embeddings.embedding_model import EmbeddingModel
            _GLOBAL_EMBEDDING_MODEL = EmbeddingModel(model_name=settings.embedding_model)
            # Verify embedding dimension compatibility
            if hasattr(_GLOBAL_EMBEDDING_MODEL, "embedding_dim"):
                assert _GLOBAL_EMBEDDING_MODEL.embedding_dim == settings.embedding_dim, (
                    f"Embedding dimension mismatch: expected {settings.embedding_dim}, got {_GLOBAL_EMBEDDING_MODEL.embedding_dim}"
                )
        except Exception as err:
            print(f"[DocuTrust RAG] Embedding model initialization fallback: {err}")
            _GLOBAL_EMBEDDING_MODEL = None
    return _GLOBAL_EMBEDDING_MODEL


def _get_shared_cross_encoder():
    global _GLOBAL_CROSS_ENCODER
    if _GLOBAL_CROSS_ENCODER is None:
        try:
            from sentence_transformers import CrossEncoder
            _GLOBAL_CROSS_ENCODER = CrossEncoder(settings.reranker_model)
        except Exception as err:
            print(f"[DocuTrust RAG] Cross-encoder initialization fallback: {err}")
            _GLOBAL_CROSS_ENCODER = None
    return _GLOBAL_CROSS_ENCODER


class TenantRAGIndex:
    """Manages tenant-isolated retrieval indexes (FAISS + BM25) with configurable hybrid fusion and reranking."""

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        self.documents: list[Document] = []
        self.bm25 = BM25Retriever()
        self.vector_store = FAISSVectorStore()
        self._splitter = TextSplitter()
        self._version_cache: dict[str, str] = {}

    def _get_embedding_model(self):
        return _get_shared_embedding_model()

    def _get_cross_encoder(self):
        return _get_shared_cross_encoder()

    def add_chunks(self, chunks: list[Document]) -> None:
        if not chunks:
            return
        self._version_cache.clear()
        for chunk in chunks:
            # Guarantee strict tenant stamping
            chunk.metadata["tenant_id"] = self.tenant_id
            self.documents.append(chunk)

        # Rebuild BM25 index over updated tenant documents
        if self.documents:
            self.bm25.build(self.documents)

        # Incrementally embed newly added chunks into FAISS
        emb_model = self._get_embedding_model()
        if emb_model and chunks:
            try:
                emb_res = emb_model.embed_documents(chunks)
                if isinstance(emb_res, tuple) and len(emb_res) == 2:
                    valid_docs, embeddings = emb_res
                    if self.vector_store.index is None:
                        self.vector_store.build_index(embeddings, valid_docs)
                    else:
                        self.vector_store.add_documents(embeddings, valid_docs)
                else:
                    if self.vector_store.index is None:
                        self.vector_store.build_index(emb_res, chunks)
                    else:
                        self.vector_store.add_documents(emb_res, chunks)
            except Exception as err:
                print(f"[DocuTrust RAG] FAISS indexing fallback: {err}")

    def delete_document(self, document_id: str) -> int:
        """Removes all chunks associated with a document and safely rebuilds BM25 and FAISS indexes."""
        before_count = len(self.documents)
        self.documents = [d for d in self.documents if d.metadata.get("document_id") != document_id]
        deleted_count = before_count - len(self.documents)

        if deleted_count > 0:
            self._version_cache.clear()
            # Rebuild BM25
            if self.documents:
                self.bm25.build(self.documents)
            else:
                self.bm25 = BM25Retriever()

            # Rebuild FAISS
            emb_model = self._get_embedding_model()
            if emb_model and self.documents:
                try:
                    self.vector_store = FAISSVectorStore()
                    emb_res = emb_model.embed_documents(self.documents)
                    if isinstance(emb_res, tuple) and len(emb_res) == 2:
                        valid_docs, embeddings = emb_res
                        self.vector_store.build_index(embeddings, valid_docs)
                    else:
                        self.vector_store.build_index(emb_res, self.documents)
                except Exception as err:
                    print(f"[DocuTrust RAG] Rebuild FAISS after deletion: {err}")
            else:
                self.vector_store = FAISSVectorStore()

        return deleted_count

    def retrieve(
        self,
        query: str,
        top_k: int = 8,
        version_filter: str | None = None,
        mode: str | None = None,
        rerank: bool | None = None,
        user_role: str | None = None,
        department: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Executes retrieval with full diagnostics, configurable fusion, and cross-encoder reranking."""
        started_time = time.perf_counter()
        active_mode = mode or settings.retrieval_mode
        active_rerank = settings.reranking_enabled if rerank is None else rerank

        if not self.documents:
            return [], {
                "retrieval_method": active_mode,
                "candidate_count": 0,
                "rerank_applied": False,
                "latency_ms": int((time.perf_counter() - started_time) * 1000),
            }

        candidate_multiplier = 4 if active_rerank else 3
        fetch_limit = min(top_k * candidate_multiplier, len(self.documents))

        # 1. Lexical Retrieval via BM25
        bm25_matches: list[dict[str, Any]] = []
        if active_mode in ("bm25", "hybrid"):
            bm25_matches = self.bm25.search(query, top_k=fetch_limit)

        # 2. Vector Retrieval via FAISS
        faiss_matches: list[dict[str, Any]] = []
        if active_mode in ("dense", "hybrid"):
            emb_model = self._get_embedding_model()
            if emb_model and self.vector_store.index is not None:
                try:
                    query_emb = emb_model.embed_query(query)
                    raw_faiss = self.vector_store.search(query_emb, top_k=fetch_limit)
                    for doc in raw_faiss:
                        faiss_matches.append({"document": doc, "score": doc.metadata.get("score", 1.0)})
                except Exception as err:
                    print(f"[DocuTrust RAG] Vector search error: {err}")

        # Helper to check document permissions (ACL)
        def is_authorized(doc: Document) -> bool:
            if doc.metadata.get("tenant_id") != self.tenant_id:
                return False
            if version_filter and doc.metadata.get("version") != version_filter:
                return False
            allowed_roles = doc.metadata.get("allowed_roles")
            if allowed_roles and user_role and user_role not in {"admin", "compliance_lead"}:
                if user_role not in allowed_roles:
                    return False
            doc_dept = doc.metadata.get("department")
            if doc_dept and doc_dept != "all" and department and department != "all":
                if doc_dept.lower() != department.lower():
                    return False
            return True

        # Mode Selection: BM25-only
        if active_mode == "bm25":
            results = []
            for item in bm25_matches:
                doc = item["document"]
                if not is_authorized(doc):
                    continue
                results.append({
                    "document": doc,
                    "rrf_score": float(item.get("score", 0.0)),
                    "bm25_score": float(item.get("score", 0.0)),
                    "faiss_score": 0.0,
                })

        # Mode Selection: Dense-only
        elif active_mode == "dense":
            results = []
            for item in faiss_matches:
                doc = item["document"]
                if not is_authorized(doc):
                    continue
                results.append({
                    "document": doc,
                    "rrf_score": float(item.get("score", 0.0)),
                    "bm25_score": 0.0,
                    "faiss_score": float(item.get("score", 0.0)),
                })

        # Mode Selection: Hybrid via RRF or Weighted Fusion
        else:
            merged: dict[str, dict[str, Any]] = {}
            rrf_k = settings.rrf_k

            if settings.fusion_strategy == "weighted":
                # Max-normalized weighted fusion
                max_bm25 = max((m.get("score", 0.0) for m in bm25_matches), default=1.0) or 1.0
                max_faiss = max((m.get("score", 0.0) for m in faiss_matches), default=1.0) or 1.0

                for item in bm25_matches:
                    doc = item["document"]
                    if not is_authorized(doc):
                        continue
                    cid = doc.metadata.get("chunk_id", str(id(doc)))
                    norm_bm25 = float(item.get("score", 0.0)) / max_bm25
                    if cid not in merged:
                        merged[cid] = {"document": doc, "rrf_score": 0.0, "bm25_score": float(item.get("score", 0.0)), "faiss_score": 0.0}
                    merged[cid]["rrf_score"] += 0.5 * norm_bm25

                for item in faiss_matches:
                    doc = item["document"]
                    if not is_authorized(doc):
                        continue
                    cid = doc.metadata.get("chunk_id", str(id(doc)))
                    norm_faiss = float(item.get("score", 0.0)) / max_faiss
                    if cid not in merged:
                        merged[cid] = {"document": doc, "rrf_score": 0.0, "bm25_score": 0.0, "faiss_score": float(item.get("score", 0.0))}
                    merged[cid]["rrf_score"] += 0.5 * norm_faiss
                    merged[cid]["faiss_score"] = float(item.get("score", 0.0))
            else:
                # Reciprocal Rank Fusion (RRF)
                for rank, item in enumerate(bm25_matches, start=1):
                    doc = item["document"]
                    if not is_authorized(doc):
                        continue
                    cid = doc.metadata.get("chunk_id", str(id(doc)))
                    if cid not in merged:
                        merged[cid] = {"document": doc, "rrf_score": 0.0, "bm25_score": float(item.get("score", 0.0)), "faiss_score": 0.0}
                    merged[cid]["rrf_score"] += 1.0 / (rrf_k + rank)

                for rank, item in enumerate(faiss_matches, start=1):
                    doc = item["document"]
                    if not is_authorized(doc):
                        continue
                    cid = doc.metadata.get("chunk_id", str(id(doc)))
                    if cid not in merged:
                        merged[cid] = {"document": doc, "rrf_score": 0.0, "bm25_score": 0.0, "faiss_score": float(item.get("score", 0.0))}
                    merged[cid]["rrf_score"] += 1.0 / (rrf_k + rank)
                    merged[cid]["faiss_score"] = float(item.get("score", 0.0))

            results = list(merged.values())
            results.sort(key=lambda x: x["rrf_score"], reverse=True)

        # 4. Optional Cross-Encoder Reranking
        rerank_applied = False
        if active_rerank and results:
            ce = self._get_cross_encoder()
            if ce:
                candidate_pool = results[: min(len(results), max(top_k * 2, 10))]
                pairs = [(query, c["document"].page_content) for c in candidate_pool]
                try:
                    ce_scores = ce.predict(pairs)
                    for c, score in zip(candidate_pool, ce_scores):
                        c["ce_score"] = float(score)
                        c["rrf_score"] = float(score)  # order by cross-encoder score
                    candidate_pool.sort(key=lambda x: x.get("ce_score", -999.0), reverse=True)
                    results = candidate_pool
                    rerank_applied = True
                except Exception as ce_err:
                    print(f"[DocuTrust RAG] Cross-encoder reranker fallback: {ce_err}")

        # 5. Scientific Score Calibration across Retrieval Modes
        max_score = max((float(r.get("ce_score" if rerank_applied else "rrf_score", 0.0)) for r in results), default=1.0)
        for rank, item in enumerate(results[:top_k], start=1):
            raw_s = float(item.get("ce_score" if rerank_applied else "rrf_score", 0.0))
            if rerank_applied:
                sig = 1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, raw_s))))
                item["calibrated_score"] = round(min(1.0, max(0.1, sig)), 4)
            elif active_mode == "hybrid":
                theoretical_max_rrf = 2.0 / (settings.rrf_k + 1.0)
                ref_max = max(max_score, theoretical_max_rrf)
                ratio = raw_s / max(1e-6, ref_max)
                rank_discount = 1.0 / (1.0 + 0.08 * (rank - 1))
                item["calibrated_score"] = round(min(1.0, max(0.1, 0.95 * ratio * rank_discount)), 4)
            elif active_mode == "dense":
                norm = (raw_s + 1.0) / 2.0 if -1.0 <= raw_s <= 1.0 else raw_s
                item["calibrated_score"] = round(min(1.0, max(0.1, norm)), 4)
            elif active_mode == "bm25":
                ratio = raw_s / max(1e-6, max_score)
                rank_discount = 1.0 / (1.0 + 0.08 * (rank - 1))
                item["calibrated_score"] = round(min(1.0, max(0.1, 0.92 * ratio * rank_discount)), 4)
            else:
                item["calibrated_score"] = round(min(1.0, max(0.1, raw_s)), 4)

        duration_ms = int((time.perf_counter() - started_time) * 1000)
        diagnostics = {
            "retrieval_method": "hybrid_reranked" if rerank_applied else f"{active_mode}_{settings.fusion_strategy}",
            "candidate_count": len(results),
            "rerank_applied": rerank_applied,
            "fusion_strategy": settings.fusion_strategy,
            "rrf_k": settings.rrf_k,
            "latency_ms": duration_ms,
        }

        return results[:top_k], diagnostics

    def get_active_version(self, document_name: str) -> str | None:
        """Dynamically identifies the active version for a document based on indexed corpus metadata."""
        if document_name in self._version_cache:
            return self._version_cache[document_name]

        matching = [
            doc for doc in self.documents
            if doc.metadata.get("document_name") == document_name or doc.metadata.get("source") == document_name
        ]
        if not matching:
            return None

        def sort_key(d: Document):
            status = 1 if "Active" in d.page_content[:200] else 0
            eff = str(d.metadata.get("effective_date", "1970-01-01"))
            ver = str(d.metadata.get("version", "v0"))
            return (status, eff, ver)

        sorted_docs = sorted(matching, key=sort_key, reverse=True)
        active_ver = sorted_docs[0].metadata.get("version")
        if active_ver:
            self._version_cache[document_name] = str(active_ver)
        return active_ver


class RAGEngine:
    """DocuTrust Unified Evidence Retrieval Engine wrapping RAG_project with tenant isolation."""

    def __init__(self) -> None:
        self.indexes: dict[str, TenantRAGIndex] = {}
        self.splitter = TextSplitter()
        self._seeded_tenants: set[str] = set()

    def get_tenant_index(self, tenant_id: str) -> TenantRAGIndex:
        if tenant_id not in self.indexes:
            self.indexes[tenant_id] = TenantRAGIndex(tenant_id)
            self._seed_default_policies_if_needed(tenant_id)
        return self.indexes[tenant_id]

    def _seed_default_policies_if_needed(self, tenant_id: str) -> None:
        if tenant_id in self._seeded_tenants:
            return
        self._seeded_tenants.add(tenant_id)

        # Standard Policy v1: Civilian Work From Home Policy v1 (Max 3 days)
        v1_text = """
CIVILIAN WORK-FROM-HOME POLICY
Document ID: 03_Civilian_Work_From_Home_Policy.pdf
Version: v1 | Effective Date: 2023-01-15 | Status: Superseded
Authority: Corporate Human Resources & Operations Directorate

Section 1: General Purpose and Scope
This policy governs remote and hybrid work arrangements for civilian personnel across all standard operating units. 
Remote work is an operational privilege extended to eligible staff in administrative and operational functions.

Section 4.2: Work-From-Home Limitations and Attendance Requirements
Eligible civilian personnel may work remotely for a maximum limit of three (3) days per calendar week. 
The remaining two (2) days must be completed on-site at the designated corporate primary office facility.
Prior written authorization from the primary Department Director is mandatory prior to commencement of hybrid schedules.

Section 5.1: Technology and Equipment Safeguards
All remote access must utilize company-issued virtual private networks (VPN) and approved multi-factor credentials. 
Personal computing devices are strictly prohibited from storing or processing unencrypted company compliance data.
"""

        # Updated Policy v2: Civilian Work From Home Policy v2 (Technology Division 4 days exception)
        v2_text = """
CIVILIAN WORK-FROM-HOME POLICY (UPDATED REVISION)
Document ID: 03_Civilian_Work_From_Home_Policy.pdf
Version: v2 | Effective Date: 2024-06-01 | Status: Active Current
Authority: Corporate Human Resources & Executive Operations Board

Section 1: General Purpose and Evolution
This policy establishes updated remote work regulations following the digital infrastructure expansion.

Section 4.2: Work-From-Home Allowances and Division-Specific Limits
The standard remote work allowance for general personnel is up to three (3) days per week.
EXCEPTION FOR TECHNOLOGY DIVISION: Personnel assigned to the Technology Division (Software Engineering, 
Data Science, and Cloud Infrastructure) may work remotely up to four (4) days per calendar week, provided they maintain 
core sprint commitments and attend scheduled monthly all-hands operational reviews on-site.

Section 4.3: Policy Version Precedence and Grandfathering
Policy Revision v2 supersedes all provisions of Revision v1. Where conflicts arise between v1 and v2, 
the terms of Revision v2 shall prevail as of the effective date of June 1, 2024.

Section 8.1: Geographic Boundaries
Remote work is authorized strictly within approved domestic national boundaries. Remote employment or work operations from unauthorized foreign territories or non-approved overseas facilities is strictly prohibited without Executive Committee sign-off.
"""

        # Security Safeguards Policy
        sec_text = """
INFORMATION SECURITY SAFEGUARDS POLICY
Document ID: 01_Security_Safeguards_Policy.pdf
Version: v2.4 | Effective Date: 2024-02-10 | Status: Active Current
Authority: Chief Information Security Officer (CISO)

Section 3.1: Mandatory Security Compliance
No employee, contractor, or officer has authorization to bypass, ignore, or disable technical security controls.
Security controls—including endpoint encryption, firewall enforcement, credential rotation, and multi-factor 
authentication (MFA)—are mandatory requirements under regulatory compliance statutes.

Section 9.4: Incident Escalation and Reporting
Any intentional evasion or non-compliance with security safeguards triggers an immediate severity-1 security review, 
revocation of credentials, and administrative disciplinary proceedings.
"""

        # Privacy and Data Protection Standard
        priv_text = """
DATA PRIVACY AND PROTECTION STANDARD
Document ID: 02_Privacy_and_Data_Protection_Standard.pdf
Version: v1.2 | Effective Date: 2024-03-15 | Status: Active Current
Authority: Data Protection Officer (DPO) & Legal Counsel

Section 2.1: Data Subject Rights and GDPR Fulfillment
All formal customer and employee requests concerning Personal Data access, rectification, or erasure under GDPR and CCPA must be acknowledged within five business days and resolved within thirty (30) calendar days.

Section 4.3: Customer Data and Removable Storage Controls
Personal and customer data is strictly prohibited from being copied to or stored on personal, unmanaged USB drives or non-corporate cloud accounts. All data storage must utilize AES-256 encrypted volumes.

Section 7.2: Data Retention and Incident Disclosure
Employee personnel records must be retained for seven (7) years following employment termination. Security breaches involving unencrypted customer data trigger mandatory notification to the Data Protection Officer and regulatory authorities within seventy-two (72) hours.
"""

        # Finance and Expense Reimbursement Code
        fin_text = """
FINANCIAL EXPENSE AND REIMBURSEMENT CODE
Document ID: 04_Finance_and_Expense_Reimbursement_Code.pdf
Version: v1.0 | Effective Date: 2024-01-01 | Status: Active Current
Authority: Corporate Comptroller & Vice President of Finance

Section 2.1: Home Office Equipment Stipend
Eligible personnel may claim a one-time reimbursement of up to $500 for an ergonomic office chair and work desk with submitted itemized receipts within sixty (60) days of hire. Personal 4K entertainment monitors, gaming gear, and television equipment are strictly non-reimbursable.

Section 3.4: Business Travel Meals and Per Diem
The maximum standard domestic business travel meal allowance is seventy-five dollars ($75) per day. Alcoholic beverages are non-reimbursable without prior written authorization from the Department Vice President.

Section 5.2: Expense Submission Deadlines
All expense reports and associated supporting receipts must be submitted in the finance portal within thirty (30) calendar days of expense incurrence.
"""

        # Ingest baseline compliance documents with initial page mapping
        self.index_text(tenant_id, "03_Civilian_Work_From_Home_Policy.pdf", "03_Civilian_Work_From_Home_Policy_v1", v1_text, version="v1", effective_date="2023-01-15", page_number=1)
        self.index_text(tenant_id, "03_Civilian_Work_From_Home_Policy.pdf", "03_Civilian_Work_From_Home_Policy_v2", v2_text, version="v2", effective_date="2024-06-01", page_number=2)
        self.index_text(tenant_id, "01_Security_Safeguards_Policy.pdf", "01_Security_Safeguards_Policy_v2", sec_text, version="v2.4", effective_date="2024-02-10", page_number=1)
        self.index_text(tenant_id, "02_Privacy_and_Data_Protection_Standard.pdf", "02_Privacy_and_Data_Protection_Standard_v1", priv_text, version="v1.2", effective_date="2024-03-15", page_number=1)
        self.index_text(tenant_id, "04_Finance_and_Expense_Reimbursement_Code.pdf", "04_Finance_and_Expense_Reimbursement_Code_v1", fin_text, version="v1.0", effective_date="2024-01-01", page_number=1)

    def delete_document(self, tenant_id: str, document_id: str) -> int:
        """Deletes a document from the tenant index, rebuilding BM25 and FAISS indexes."""
        idx = self.get_tenant_index(tenant_id)
        return idx.delete_document(document_id)

    def index_chunks(
        self,
        tenant_id: str,
        document_name: str,
        document_id: str,
        chunks: list[Any],
        version: str = "v1",
        effective_date: str = "2024-01-01",
        allowed_roles: list[str] | None = None,
        department: str = "all",
    ) -> int:
        """Indexes pre-processed IngestedChunk objects directly, preserving page numbers, section titles, and ACLs."""
        idx = self.get_tenant_index(tenant_id)
        # Safe deduplication: remove previous chunks for this document if re-indexing
        idx.delete_document(document_id)

        doc_chunks: list[Document] = []
        for idx_c, chunk in enumerate(chunks, start=1):
            page_start = getattr(chunk, "page_start", 1) or 1
            page_end = getattr(chunk, "page_end", page_start) or page_start
            sec_name = getattr(chunk, "section", "General") or "General"
            cid = getattr(chunk, "chunk_id", None) or f"{document_id}_p{page_start}_c{idx_c}"

            doc_chunk = Document(
                page_content=chunk.content if hasattr(chunk, "content") else str(chunk),
                metadata={
                    "source": document_name,
                    "document_id": document_id,
                    "document_name": document_name,
                    "version": version,
                    "effective_date": effective_date,
                    "tenant_id": tenant_id,
                    "page": page_start,
                    "page_start": page_start,
                    "page_end": page_end,
                    "section": sec_name,
                    "chunk_id": cid,
                    "allowed_roles": allowed_roles or [],
                    "department": department,
                },
            )
            doc_chunks.append(doc_chunk)

        idx.add_chunks(doc_chunks)
        return len(doc_chunks)

    def index_text(
        self,
        tenant_id: str,
        document_name: str,
        document_id: str,
        text: str,
        version: str = "v1",
        effective_date: str = "2024-01-01",
        page_number: int = 1,
        allowed_roles: list[str] | None = None,
        department: str = "all",
    ) -> int:
        """Splits raw text and indexes into the tenant FAISS and BM25 store with deduplication."""
        idx = self.get_tenant_index(tenant_id)
        idx.delete_document(document_id)

        doc = Document(
            page_content=text,
            metadata={
                "source": document_name,
                "document_id": document_id,
                "document_name": document_name,
                "version": version,
                "effective_date": effective_date,
                "tenant_id": tenant_id,
                "page": page_number,
                "page_start": page_number,
                "page_end": page_number,
                "allowed_roles": allowed_roles or [],
                "department": department,
            },
        )

        chunks = self.splitter.split_documents([doc])
        for idx_c, chunk in enumerate(chunks, start=1):
            chunk.metadata["tenant_id"] = tenant_id
            chunk.metadata["document_id"] = document_id
            chunk.metadata["document_name"] = document_name
            chunk.metadata["version"] = version
            chunk.metadata["effective_date"] = effective_date
            chunk.metadata["page"] = page_number
            chunk.metadata["page_start"] = page_number
            chunk.metadata["page_end"] = page_number
            chunk.metadata["allowed_roles"] = allowed_roles or []
            chunk.metadata["department"] = department
            chunk.metadata["chunk_id"] = f"{document_id}_p{page_number}_c{idx_c}"

            # Detect section from content
            for line in chunk.page_content.splitlines():
                if "Section " in line:
                    chunk.metadata["section"] = line.strip().split(":")[0].strip()
                    break

        idx.add_chunks(chunks)
        return len(chunks)

    def retrieve_with_diagnostics(
        self,
        query: str,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 8,
        mode: str | None = None,
        rerank: bool | None = None,
        user_role: str | None = None,
        department: str | None = None,
    ) -> tuple[list[EvidenceRecord], dict[str, Any]]:
        """Retrieves tenant-isolated evidence passages alongside complete retrieval diagnostic metadata."""
        idx = self.get_tenant_index(tenant_id)
        version_filter = filters.get("version") if filters else None

        raw_results, diagnostics = idx.retrieve(
            query,
            top_k=top_k,
            version_filter=version_filter,
            mode=mode,
            rerank=rerank,
            user_role=user_role,
            department=department,
        )

        records: list[EvidenceRecord] = []
        candidate_ids: list[str] = []

        for item in raw_results:
            doc: Document = item["document"]
            meta = doc.metadata

            # ENFORCE STRICT TENANT ISOLATION
            if meta.get("tenant_id") != tenant_id:
                continue

            score = float(item.get("calibrated_score", item.get("rrf_score", 0.0)))
            score = round(min(1.0, max(0.1, score)), 4)

            sec_name = meta.get("section")
            if not sec_name or sec_name == "General":
                for line in doc.page_content.splitlines():
                    if "Section " in line:
                        sec_name = line.strip().split(":")[0].strip()
                        break
                sec_name = sec_name or "General"

            chunk_id = str(meta.get("chunk_id", str(uuid.uuid4())))
            candidate_ids.append(chunk_id)

            records.append(
                EvidenceRecord(
                    evidence_id=chunk_id,
                    document_id=str(meta.get("document_id", meta.get("source", "doc"))),
                    document_name=str(meta.get("document_name", meta.get("source", "Policy"))),
                    tenant_id=tenant_id,
                    chunk_id=chunk_id,
                    text=doc.page_content.strip(),
                    retrieval_score=score,
                    page_number=meta.get("page_start", meta.get("page", 1)),
                    page_start=meta.get("page_start", meta.get("page", 1)),
                    page_end=meta.get("page_end", meta.get("page", 1)),
                    section=sec_name,
                    policy_version=str(meta.get("version", "v1")),
                    effective_from=str(meta.get("effective_date", "2024-01-01")),
                    effective_to="Present",
                    source_type="pdf",
                    bm25_score=round(float(item.get("bm25_score", 0.0)), 4),
                    faiss_score=round(float(item.get("faiss_score", 0.0)), 4),
                    rrf_score=round(float(item.get("rrf_score", 0.0)), 4),
                    ce_score=round(float(item.get("ce_score")), 4) if item.get("ce_score") is not None else None,
                    retrieval_diagnostics={
                        "retrieval_method": diagnostics["retrieval_method"],
                        "bm25_score": round(float(item.get("bm25_score", 0.0)), 4),
                        "faiss_score": round(float(item.get("faiss_score", 0.0)), 4),
                        "rrf_score": round(float(item.get("rrf_score", 0.0)), 4),
                        "ce_score": round(float(item.get("ce_score")), 4) if item.get("ce_score") is not None else None,
                    },
                )
            )

        diagnostics["candidate_chunk_ids"] = candidate_ids
        diagnostics["selected_evidence_count"] = len(records)
        return records, diagnostics

    def retrieve(
        self,
        query: str,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 8,
        mode: str | None = None,
        rerank: bool | None = None,
        user_role: str | None = None,
        department: str | None = None,
    ) -> list[EvidenceRecord]:
        """Backwards-compatible retrieval returning list of EvidenceRecord."""
        records, _ = self.retrieve_with_diagnostics(
            query=query,
            tenant_id=tenant_id,
            filters=filters,
            top_k=top_k,
            mode=mode,
            rerank=rerank,
            user_role=user_role,
            department=department,
        )
        return records

    def retrieve_iterative(
        self,
        query: str,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 8,
        mode: str | None = None,
        rerank: bool | None = None,
        max_iterations: int = 2,
    ) -> list[EvidenceRecord]:
        """Bounded 2-pass iterative retrieval expanding query with salient terms from initial evidence."""
        pass_1 = self.retrieve(query, tenant_id=tenant_id, filters=filters, top_k=top_k, mode=mode, rerank=rerank)
        if not pass_1 or max_iterations <= 1:
            return pass_1

        seed_terms = []
        for rec in pass_1[:2]:
            for line in rec.text.splitlines():
                if any(k in line.lower() for k in ("section", "policy", "exception", "authorized", "mandatory", "stipend", "allowance")):
                    seed_terms.extend([w for w in line.split() if len(w) > 4 and w.isalnum()])

        expanded_keywords = " ".join(list(dict.fromkeys(seed_terms))[:4])
        reformulated_query = f"{query} {expanded_keywords}".strip()
        pass_2 = self.retrieve(reformulated_query, tenant_id=tenant_id, filters=filters, top_k=top_k, mode=mode, rerank=rerank)

        seen = set()
        merged: list[EvidenceRecord] = []
        for rec in pass_1 + pass_2:
            if rec.chunk_id not in seen:
                seen.add(rec.chunk_id)
                merged.append(rec)
        return merged[:top_k]

    def test_tenant_isolation(self, tenant_a: str, tenant_b: str) -> dict[str, Any]:
        """Verifies that retrieval for tenant_a never returns tenant_b documents."""
        self.get_tenant_index(tenant_a)
        self.get_tenant_index(tenant_b)

        secret_id = f"confidential-b-{uuid.uuid4()}"
        self.index_text(tenant_b, "Confidential_B.pdf", secret_id, "Tenant B strictly private compliance key: CONFIDENTIAL_TOKEN_998811", version="v1")

        results_for_a = self.retrieve("CONFIDENTIAL_TOKEN_998811", tenant_id=tenant_a)
        leaked = [r for r in results_for_a if r.tenant_id != tenant_a or "CONFIDENTIAL_TOKEN_998811" in r.text]

        results_for_b = self.retrieve("CONFIDENTIAL_TOKEN_998811", tenant_id=tenant_b)
        found_in_b = any("CONFIDENTIAL_TOKEN_998811" in r.text for r in results_for_b)

        return {
            "status": "PASS" if (len(leaked) == 0 and found_in_b) else "FAIL",
            "cross_tenant_leak_count": len(leaked),
            "tenant_b_retrieval_success": found_in_b,
            "tenant_a_isolated": len(leaked) == 0,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "description": "Tenant-scoped vector and lexical filtering verified."
        }


# Global Singleton RAG Engine
rag_engine = RAGEngine()
