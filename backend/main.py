from __future__ import annotations

import asyncio
import json
import time
import uuid
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import settings
from backend.agents.contracts import plan_to_dict, result_to_dict, reflection_to_dict
from backend.graph.workflow import run_policy_graph
from backend.repositories.store import store
from backend.security.tenant import RequestContext, request_context, require_role
from backend.providers.fallback import provider_status
from backend.ingestion import IngestionError, prepare_text_document
from backend.api_config import api_status
from backend.evaluation_service import evaluation_service
from backend.policy_impact import analyze_policy_impact
from backend.rag_engine import rag_engine


class QueryIn(BaseModel):
    query: str = Field(min_length=3, max_length=settings.max_query_chars)
    mode: str | None = None
    rerank: bool | None = None
    top_k: int | None = None
    department: str | None = None


class ReviewIn(BaseModel):
    run_id: str = Field(min_length=1, max_length=128)
    decision: str = Field(pattern="^(approved|rejected|request_more_evidence)$")
    note: str = Field(default="", max_length=2000)


app = FastAPI(title=settings.app_name, version="3.2.0")


@app.on_event("startup")
async def initialize_storage() -> None:
    if settings.storage_mode == "postgres" and hasattr(store, "connect"):
        try:
            await store.connect()
        except Exception as err:
            print(f"[Store] Postgres startup connect error (operating in memory mode): {err}")


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Tenant-Id", "X-User-Id", "X-Docutrust-Mode", "X-Role", "X-Internal-Assertion", "Authorization"]
)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/")
def root() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "docutrust-api",
        "version": "3.2.0",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready"
    }


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "service": "docutrust-api", "version": "3.2.0", "timestamp": int(time.time())}


@app.get("/ready")
def readiness() -> dict[str, object]:
    checks = {
        "api": "ok",
        "rag_engine": "ready",
        "ai_provider": "configured" if (settings.ai_gateway_api_key or settings.groq_api_key or settings.gemini_api_key) else "deterministic_fallback_ready",
        "persistence": "postgres" if (settings.database_url and settings.storage_mode == "postgres") else "memory",
    }
    return {"status": "ready", "checks": checks}


@app.get("/api/config/status")
def config_status() -> dict[str, object]:
    return {**settings.public_status(), "api_requirements": api_status()}


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), context: RequestContext = Depends(request_context)) -> dict[str, object]:
    content = await file.read()
    try:
        document = prepare_text_document(file.filename or "upload", file.content_type or "application/octet-stream", content)
        return await store.ingest_document(context.tenant_id, file.filename or "upload", file.content_type or "application/octet-stream", document)
    except IngestionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str, context: RequestContext = Depends(request_context)) -> dict[str, object]:
    success = await store.delete_document(context.tenant_id, document_id)
    return {"status": "deleted" if success else "not_found", "document_id": document_id, "tenant_id": context.tenant_id}


@app.get("/api/documents")
async def list_documents(limit: int = 100, offset: int = 0, context: RequestContext = Depends(request_context)) -> dict[str, object]:
    items = await store.list(context.tenant_id, "documents", limit=limit, offset=offset)
    return {"items": items, "tenant_id": context.tenant_id, "mode": context.mode}


@app.post("/api/query")
async def query(request: QueryIn, context: RequestContext = Depends(request_context)) -> dict[str, object]:
    state = await run_policy_graph(
        query=request.query.strip(),
        tenant_id=context.tenant_id,
        mode=context.mode,
        retrieval_mode=request.mode,
        rerank=request.rerank,
        top_k=request.top_k or 8,
        user_role=context.role,
        department=request.department,
    )
    
    # Persist run
    run_record = {
        "id": state.run_id,
        "actor_id": context.user_id,
        "query": state.query,
        "answer": state.final_answer,
        "confidence": state.overall_confidence,
        "requires_review": state.requires_review,
        "review_reasons": state.review_reasons,
        "events": state.events,
        "evidence": [item.to_dict() for item in state.evidence],
        "receipt": state.receipt.to_dict() if state.receipt else None,
        "breakdown": state.confidence_breakdown.to_dict() if state.confidence_breakdown else None,
        "conflict": state.conflict_analysis.to_dict()
    }
    await store.append(context.tenant_id, "runs", run_record)

    # If review is required, enqueue into review collection
    if state.requires_review:
        await store.append(
            context.tenant_id,
            "reviews",
            {
                "id": state.run_id,
                "run_id": state.run_id,
                "title": state.query,
                "question": state.query,
                "answer": state.final_answer,
                "confidence": state.overall_confidence,
                "reasons": state.review_reasons,
                "status": "Open",
                "kind": "Policy conflict" if state.conflict_analysis.conflict_detected else "Insufficient evidence",
                "owner": "Compliance Lead",
                "created": time.strftime("%Y-%m-%d %H:%M")
            }
        )

    return {
        "run_id": state.run_id,
        "status": "needs_review" if state.requires_review else "completed",
        "goal": state.goal,
        "intent": state.intent,
        "plan": plan_to_dict(state.plan),
        "actions": [tool.to_dict() for tool in state.tool_calls],
        "tools": [tool.name for tool in state.tool_calls],
        "evidence": [e.to_dict() for e in state.evidence],
        "claim_verifications": [c.to_dict() for c in state.claim_verifications],
        "conflict_analysis": state.conflict_analysis.to_dict(),
        "confidence_breakdown": state.confidence_breakdown.to_dict() if state.confidence_breakdown else None,
        "receipt": state.receipt.to_dict() if state.receipt else None,
        "answer": state.final_answer,
        "confidence": state.overall_confidence,
        "requires_review": state.requires_review,
        "review_reasons": state.review_reasons,
        "evidence_state": state.evidence_state,
        "retrieval_diagnostics": state.retrieval_diagnostics,
        "citation_validation": state.evidence_state.get("citation_validation"),
        "agents": [result_to_dict(agent) for agent in state.agents],
        "events": state.events,
        "provider": provider_status()
    }


@app.post("/api/query/stream")
async def query_stream(request: QueryIn, context: RequestContext = Depends(request_context)) -> StreamingResponse:

    async def events():
        yield f"data: {json.dumps({'type': 'run_queued', 'tenant_id': context.tenant_id})}\n\n"
        await asyncio.sleep(0)
        try:
            state = await run_policy_graph(
                query=request.query.strip(),
                tenant_id=context.tenant_id,
                mode=context.mode,
                retrieval_mode=request.mode,
                rerank=request.rerank,
                top_k=request.top_k or 8,
                user_role=context.role,
                department=request.department,
            )

            # Persist run (resilient against database constraints)
            try:
                run_record = {
                    "id": state.run_id,
                    "actor_id": context.user_id,
                    "query": state.query,
                    "answer": state.final_answer,
                    "confidence": state.overall_confidence,
                    "requires_review": state.requires_review,
                    "review_reasons": state.review_reasons,
                    "events": state.events,
                    "evidence": [item.to_dict() for item in state.evidence],
                    "receipt": state.receipt.to_dict() if state.receipt else None,
                    "breakdown": state.confidence_breakdown.to_dict() if state.confidence_breakdown else None,
                    "conflict": state.conflict_analysis.to_dict(),
                    "retrieval_diagnostics": state.retrieval_diagnostics,
                }
                await store.append(context.tenant_id, "runs", run_record)

                if state.requires_review:
                    await store.append(
                        context.tenant_id,
                        "reviews",
                        {
                            "id": state.run_id,
                            "run_id": state.run_id,
                            "title": state.query,
                            "question": state.query,
                            "answer": state.final_answer,
                            "confidence": state.overall_confidence,
                            "reasons": state.review_reasons,
                            "status": "Open",
                            "decision": "pending",
                            "kind": "Policy conflict" if state.conflict_analysis.conflict_detected else "Insufficient evidence",
                            "owner": "Compliance Lead",
                            "created": time.strftime("%Y-%m-%d %H:%M")
                        }
                    )
            except Exception as store_err:
                print(f"[Store Warning] Run persistence caught: {store_err}")

            # Stream every stage event from the 12-stage workflow
            for event in state.events:
                yield f"data: {json.dumps(event)}\n\n"

            # Final summary result payload
            yield f"data: {json.dumps({'type': 'run_result', 'run_id': state.run_id, 'status': 'needs_review' if state.requires_review else 'completed', 'goal': state.goal, 'intent': state.intent, 'plan': plan_to_dict(state.plan), 'actions': [tool.to_dict() for tool in state.tool_calls], 'tools': [tool.name for tool in state.tool_calls], 'evidence': [e.to_dict() for e in state.evidence], 'claim_verifications': [c.to_dict() for c in state.claim_verifications], 'conflict_analysis': state.conflict_analysis.to_dict(), 'confidence_breakdown': state.confidence_breakdown.to_dict() if state.confidence_breakdown else None, 'receipt': state.receipt.to_dict() if state.receipt else None, 'answer': state.final_answer, 'confidence': state.overall_confidence, 'requires_review': state.requires_review, 'review_reasons': state.review_reasons, 'evidence_state': state.evidence_state, 'retrieval_diagnostics': state.retrieval_diagnostics, 'citation_validation': state.evidence_state.get('citation_validation'), 'agents': [result_to_dict(agent) for agent in state.agents], 'provider': provider_status()})}\n\n"
        except Exception as error:
            yield f"data: {json.dumps({'type': 'run_failed', 'message': str(error) or 'The run could not be completed safely.'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/runs")
async def runs(limit: int = 100, offset: int = 0, context: RequestContext = Depends(request_context)) -> dict[str, object]:
    return {"items": await store.list(context.tenant_id, "runs", limit=limit, offset=offset)}


@app.get("/api/review")
async def review(limit: int = 100, offset: int = 0, context: RequestContext = Depends(request_context)) -> dict[str, object]:
    items = await store.list(context.tenant_id, "reviews", limit=limit, offset=offset)
    return {"reviews": items}


@app.post("/api/review")
async def add_review(item: ReviewIn, context: RequestContext = Depends(request_context)) -> dict[str, object]:
    db_decision = "approved" if item.decision == "approved" else "rejected" if item.decision == "rejected" else "pending"
    return await store.append(
        context.tenant_id,
        "reviews",
        {
            **item.model_dump(),
            "decision": db_decision,
            "reviewer_id": context.user_id,
            "status": "Approved" if item.decision == "approved" else "Rejected" if item.decision == "rejected" else "Needs More Evidence",
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    )


@app.get("/api/policy/impact")
async def get_policy_impact(context: RequestContext = Depends(request_context)) -> dict[str, object]:
    """Returns organizational Policy Change Impact Analysis comparing v1 and v2."""
    idx = rag_engine.get_tenant_index(context.tenant_id)
    v1_chunks = [d.page_content for d in idx.documents if d.metadata.get("version") == "v1"]
    v2_chunks = [d.page_content for d in idx.documents if d.metadata.get("version") == "v2"]
    
    v1_full = "\n".join(v1_chunks)
    v2_full = "\n".join(v2_chunks)
    
    impact = analyze_policy_impact("Civilian Work-From-Home Policy", v1_full, v2_full, "v1", "v2")
    return {"impact": impact.to_dict()}


@app.get("/api/security/tenant-test")
async def test_tenant_security(context: RequestContext = Depends(request_context)) -> dict[str, object]:
    """Performs empirical verification of tenant-scoped retrieval isolation."""
    result = rag_engine.test_tenant_isolation(context.tenant_id, f"isolated-probe-{uuid.uuid4().hex[:6]}")
    return {"tenant_isolation_test": result}


@app.get("/api/evaluations")
async def get_evaluations() -> dict[str, object]:
    return evaluation_service.get_status()


@app.post("/api/evaluations/run")
async def run_evaluation(context: RequestContext = Depends(request_context)) -> dict[str, object]:
    results = await evaluation_service.run_evaluation_suite(context.tenant_id)
    return results
