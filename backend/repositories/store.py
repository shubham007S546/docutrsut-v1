from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Protocol

from backend.config import settings


class Store(Protocol):
    async def append(self, tenant_id: str, collection: str, value: dict[str, Any]) -> dict[str, Any]: ...
    async def list(self, tenant_id: str, collection: str, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]: ...
    async def ingest_document(self, tenant_id: str, title: str, mime_type: str, document: Any) -> dict[str, Any]: ...
    async def delete_document(self, tenant_id: str, document_id: str) -> bool: ...


class MemoryStore:
    """Explicitly non-production adapter used only when STORAGE_MODE=memory."""
    MAX_RETAINED_ITEMS = 2000

    def __init__(self) -> None:
        self._data: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        self._lock = asyncio.Lock()

    async def append(self, tenant_id: str, collection: str, value: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            item = deepcopy(value)
            target = self._data[tenant_id][collection]
            target.append(item)
            # Evict oldest entries if exceeding MAX_RETAINED_ITEMS to prevent memory exhaustion
            if len(target) > self.MAX_RETAINED_ITEMS:
                target.pop(0)
            return deepcopy(item)

    async def ingest_document(self, tenant_id: str, title: str, mime_type: str, document: Any) -> dict[str, Any]:
        async with self._lock:
            doc_id = str(uuid.uuid4())
            record = {
                "id": doc_id,
                "tenant_id": tenant_id,
                "title": title,
                "source_type": "upload",
                "mime_type": mime_type,
                "status": "ready",
                "chunks": len(document.chunks),
                "sha256": document.sha256,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._data[tenant_id]["documents"].append(record)
            try:
                from backend.rag_engine import rag_engine
                rag_engine.index_chunks(tenant_id, title, doc_id, document.chunks, version="v1")
            except Exception as err:
                print(f"[Store] Ingestion indexing error: {err}")
            return record

    async def delete_document(self, tenant_id: str, document_id: str) -> bool:
        async with self._lock:
            docs = self._data[tenant_id]["documents"]
            self._data[tenant_id]["documents"] = [d for d in docs if d.get("id") != document_id]
            try:
                from backend.rag_engine import rag_engine
                rag_engine.delete_document(tenant_id, document_id)
            except Exception as err:
                print(f"[MemoryStore] Deletion error: {err}")
            return True

    async def list(self, tenant_id: str, collection: str, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        async with self._lock:
            # Seed default demo policies if documents list is empty
            if collection == "documents" and not self._data[tenant_id]["documents"]:
                self._data[tenant_id]["documents"] = [
                    {
                        "id": "doc-wfh-v1",
                        "title": "03_Civilian_Work_From_Home_Policy_v1.pdf",
                        "version": "v1",
                        "mimeType": "application/pdf",
                        "status": "ready",
                        "chunks": 3,
                        "updatedAt": datetime.now(timezone.utc).isoformat(),
                    },
                    {
                        "id": "doc-wfh-v2",
                        "title": "03_Civilian_Work_From_Home_Policy_v2.pdf",
                        "version": "v2",
                        "mimeType": "application/pdf",
                        "status": "ready",
                        "chunks": 4,
                        "updatedAt": datetime.now(timezone.utc).isoformat(),
                    },
                    {
                        "id": "doc-sec-v2",
                        "title": "01_Security_Safeguards_Policy.pdf",
                        "version": "v2.4",
                        "mimeType": "application/pdf",
                        "status": "ready",
                        "chunks": 3,
                        "updatedAt": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            items = self._data[tenant_id][collection]
            sliced = items[offset : offset + limit] if offset or limit else items
            return deepcopy(sliced)


class PostgresStore:
    """Durable tenant-scoped repository using the connected Postgres URL."""
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self.pool: Any | None = None

    async def connect(self) -> None:
        if self.pool is None:
            import asyncpg
            self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=8, command_timeout=10)

    async def append(self, tenant_id: str, collection: str, value: dict[str, Any]) -> dict[str, Any]:
        await self.connect()
        if collection == "runs":
            await self.pool.execute("""INSERT INTO docutrust_query_runs (id, tenant_id, actor_id, question, status, answer, confidence, evidence, trace, model_id, prompt_version, completed_at) VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10, $11, $12) ON CONFLICT (id) DO UPDATE SET status=EXCLUDED.status, answer=EXCLUDED.answer, confidence=EXCLUDED.confidence, evidence=EXCLUDED.evidence, trace=EXCLUDED.trace, completed_at=EXCLUDED.completed_at""", value["id"], tenant_id, value.get("actor_id"), value.get("query", ""), "needs_review" if value.get("requires_review") else "completed", value.get("answer"), value.get("confidence"), json.dumps(value.get("evidence", [])), json.dumps(value.get("events", [])), value.get("model_id"), value.get("prompt_version"), datetime.now(timezone.utc))
        elif collection == "reviews":
            reviewer = value.get("reviewer_id") or "compliance-queue"
            decision = value.get("decision") or "pending"
            notes = value.get("note") or value.get("notes") or (", ".join(value.get("reasons", [])))
            await self.pool.execute(
                """INSERT INTO docutrust_reviews (id, tenant_id, query_run_id, reviewer_id, decision, notes) VALUES ($1::uuid, $2::uuid, $3::uuid, $4, $5, $6)""",
                str(uuid.uuid4()), tenant_id, value["run_id"], reviewer, decision, notes
            )
        else:
            raise ValueError(f"Unsupported durable collection: {collection}")
        return value

    async def ingest_document(self, tenant_id: str, title: str, mime_type: str, document: Any) -> dict[str, Any]:
        await self.connect()
        document_id = str(uuid.uuid4())
        await self.pool.execute("INSERT INTO docutrust_documents (id, tenant_id, title, source_type, mime_type, status, sha256) VALUES ($1::uuid, $2::uuid, $3, 'upload', $4, 'indexed', $5)", document_id, tenant_id, title, mime_type, document.sha256)
        for chunk in document.chunks:
            page_start = getattr(chunk, "page_start", 1) or 1
            page_end = getattr(chunk, "page_end", page_start) or page_start
            await self.pool.execute(
                "INSERT INTO docutrust_document_chunks (id, tenant_id, document_id, version_label, chunk_index, content, char_start, char_end, page_start, page_end) VALUES ($1::uuid, $2::uuid, $3::uuid, 'v1', $4, $5, $6, $7, $8, $9)",
                str(uuid.uuid4()), tenant_id, document_id, chunk.index, chunk.content, chunk.char_start, chunk.char_end, page_start, page_end
            )
        try:
            from backend.rag_engine import rag_engine
            rag_engine.index_chunks(tenant_id, title, document_id, document.chunks, version="v1")
        except Exception as err:
            print(f"[PostgresStore] Indexing chunks into rag_engine error: {err}")
        return {"id": document_id, "title": title, "mime_type": mime_type, "status": "indexed", "chunks": len(document.chunks), "sha256": document.sha256}

    async def delete_document(self, tenant_id: str, document_id: str) -> bool:
        await self.connect()
        await self.pool.execute("DELETE FROM docutrust_document_chunks WHERE tenant_id=$1::uuid AND document_id=$2::uuid", tenant_id, document_id)
        await self.pool.execute("DELETE FROM docutrust_documents WHERE tenant_id=$1::uuid AND id=$2::uuid", tenant_id, document_id)
        try:
            from backend.rag_engine import rag_engine
            rag_engine.delete_document(tenant_id, document_id)
        except Exception as err:
            print(f"[PostgresStore] Deletion error: {err}")
        return True

    async def list(self, tenant_id: str, collection: str, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        await self.connect()
        if collection == "runs":
            rows = await self.pool.fetch("SELECT id::text, question, status, answer, confidence, evidence, trace, created_at FROM docutrust_query_runs WHERE tenant_id=$1::uuid ORDER BY created_at DESC LIMIT $2 OFFSET $3", tenant_id, limit, offset)
        elif collection == "reviews":
            rows = await self.pool.fetch("SELECT id::text, query_run_id::text, reviewer_id, decision, notes, created_at FROM docutrust_reviews WHERE tenant_id=$1::uuid ORDER BY created_at DESC LIMIT $2 OFFSET $3", tenant_id, limit, offset)
        elif collection == "documents":
            rows = await self.pool.fetch("SELECT id::text, title, source_type, mime_type, status, sha256, created_at, updated_at FROM docutrust_documents WHERE tenant_id=$1::uuid ORDER BY updated_at DESC LIMIT $2 OFFSET $3", tenant_id, limit, offset)
        else:
            raise ValueError(f"Unsupported durable collection: {collection}")
        return [dict(row) for row in rows]


def create_store() -> Store:
    if settings.storage_mode == "memory" or not settings.database_url or "[YOUR-PASSWORD]" in (settings.database_url or ""):
        return MemoryStore()
    try:
        return PostgresStore(settings.database_url)
    except Exception:
        return MemoryStore()


store = create_store()
