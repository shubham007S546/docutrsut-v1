from __future__ import annotations

from functools import lru_cache
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DocuTrust Agent Runtime"
    app_env: str = "development"
    cors_origins_raw: str = Field(default="http://localhost:3000", validation_alias=AliasChoices("CORS_ORIGINS", "cors_origins"))

    @property
    def cors_origins(self) -> list[str]:
        val = self.cors_origins_raw.strip()
        if val.startswith("[") and val.endswith("]"):
            import json
            try:
                return json.loads(val)
            except Exception:
                pass
        return [item.strip() for item in val.split(",") if item.strip()] or ["http://localhost:3000"]

    database_url: str | None = None
    blob_read_write_token: str | None = None
    better_auth_secret: str | None = None
    storage_mode: str = "memory"
    embedding_api_url: str | None = None
    embedding_api_key: str | None = None
    ocr_api_url: str | None = None
    ocr_api_key: str | None = None
    malware_scanner_api_url: str | None = None
    malware_scanner_api_key: str | None = None
    connector_api_url: str | None = None
    connector_api_key: str | None = None
    max_upload_mb: int = 25
    ai_gateway_base_url: str = "https://ai-gateway.vercel.sh/v1"
    ai_gateway_api_key: str | None = Field(default=None, validation_alias=AliasChoices("VERCEL_AI_GATEWAY_KEY", "AI_GATEWAY_API_KEY"))
    groq_api_key: str | None = None
    gemini_api_key: str | None = Field(default=None, validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"))
    tavily_api_key: str | None = None
    ai_model: str = "openai/gpt-5.4-mini"
    groq_model: str = "openai/gpt-oss-120b"
    gemini_model: str = "gemini-1.5-flash"
    ai_timeout_seconds: float = 45.0
    max_query_chars: int = 4000
    public_demo_enabled: bool = False
    research_enabled: bool = False

    # Ingestion & Chunking settings
    chunk_size: int = 1400
    chunk_overlap: int = 160

    # Retrieval & Ranking settings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranking_enabled: bool = True
    rrf_k: int = 60
    retrieval_mode: str = "hybrid"  # "hybrid", "dense", "bm25"
    fusion_strategy: str = "rrf"  # "rrf" or "weighted"
    retrieval_top_k: int = 8

    # Uncertainty, Sufficiency & Grounding thresholds
    min_evidence_coverage: float = 0.30
    min_retrieval_relevance: float = 0.50
    confidence_threshold: float = 0.70
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def public_status(self) -> dict[str, object]:
        return {"environment": self.app_env, "model_configured": bool(self.ai_gateway_api_key or self.groq_api_key or self.gemini_api_key), "model": self.ai_model, "provider": "fallback_chain", "providers": {"ai_gateway": bool(self.ai_gateway_api_key), "groq": bool(self.groq_api_key), "gemini": bool(self.gemini_api_key), "tavily": bool(self.tavily_api_key)}, "research_enabled": self.research_enabled, "public_demo_enabled": self.public_demo_enabled, "storage": self.storage_mode, "mode": "live" if self.ai_gateway_api_key and self.database_url else "readiness_required"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
