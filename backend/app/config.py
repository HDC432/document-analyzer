from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # 必填 — 读不到则启动失败
    openai_api_key: str

    # 存储路径
    chroma_path: Path = Path("/data/chroma")
    sqlite_path: Path = Path("/data/sqlite/app.db")
    uploads_path: Path = Path("/data/uploads")

    # OpenAI 模型
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"

    # RAG 参数
    top_k: int = 5
    distance_threshold: float = 0.45
    chunk_size: int = 500
    chunk_overlap: int = 80


settings = Settings()
