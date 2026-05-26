from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="")
    openai_chat_model: str = Field(default="gpt-4o")
    openai_embedding_model: str = Field(default="text-embedding-3-small")
    semantic_cache_embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    openai_reasoning_effort: str = Field(default="medium")
    openai_lightweight_model: str = Field(default="")
    openai_lightweight_reasoning_effort: str = Field(default="low")

    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_username: str = Field(default="default")
    redis_password: str = Field(default="")
    redis_db: int = Field(default=0)
    redis_ssl: bool = Field(default=False)
    redis_max_connections: int = Field(default=4)

    ctx_admin_key: str = Field(default="")
    mcp_agent_key: str = Field(default="")
    ctx_surface_id: str = Field(default="")
    ctx_redis_instance_id: str = Field(default="")

    backend_host: str = Field(default="127.0.0.1")
    backend_port: int = Field(default=8040)
    cors_origin: str = Field(default="http://localhost:3040")
    demo_domain: str = Field(default="reddash")
    show_final_verifier_trace_step: bool = Field(default=False)
    show_llm_trace_steps: bool = Field(default=False)


def get_settings() -> Settings:
    return Settings()
