from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración leída del entorno. `DATABASE_URL` la inyecta docker-compose."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://rag:rag@db:5432/rag"

    # Carpeta donde LocalStorage guarda los ficheros originales (dentro del contenedor).
    storage_dir: str = "/app/storage"

    # Chunking. El modelo de embeddings ya está decidido (skill rag-conventions): BGE-M3.
    # Usamos SU tokenizer para contar tokens exactamente como los verá al embeber.
    # Estos números son un punto de arranque, no dogma: ajustables.
    embedding_model_name: str = "BAAI/bge-m3"
    chunk_target_tokens: int = 700  # objetivo por chunk (rango de la skill: 500-800)
    chunk_overlap_tokens: int = 100  # ~14% de solape entre chunks contiguos

    # Embeddings. BGE-M3 produce vectores de 1024 dimensiones. Se sirve por HTTP (TEI).
    embeddings_url: str = "http://embeddings:80"
    embedding_dim: int = 1024

    # Recuperación (Fase 4). Valores de arranque, ajustables.
    retrieval_k: int = 30  # top-K por cada vía (vectorial y full-text) antes de fusionar
    final_n: int = 8  # cuántos candidatos se devuelven tras rerankear
    rrf_k: int = 60  # constante del Reciprocal Rank Fusion (estándar)

    # Rerank + umbral (Fase 4b). El reranker se sirve por HTTP (segundo TEI).
    reranker_url: str = "http://reranker:80"
    rerank_pool: int = 20  # cuántos candidatos fusionados se pasan al reranker
    relevance_threshold: float = 0.5  # score mínimo del reranker; por debajo → abstención


settings = Settings()
