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
    retrieval_k: int = (
        30  # top-K por cada vía (vectorial y full-text) antes de fusionar
    )
    final_n: int = 8  # cuántos candidatos se devuelven tras rerankear
    rrf_k: int = 60  # constante del Reciprocal Rank Fusion (estándar)

    # Rerank + umbral (Fase 4b). El reranker se sirve por HTTP (segundo TEI).
    reranker_url: str = "http://reranker:80"
    rerank_pool: int = 10  # cuántos candidatos fusionados se pasan al reranker
    # Tamaño de ventana (tokens de passage) al rerankear. El reranker ligero solo "ve"
    # ~512 tokens, así que cada chunk se trocea en ventanas y se puntúa por el máximo:
    # así "lee" el chunk entero aunque la respuesta esté al final (sin esto, el truncado
    # infravalora la cola). Con el modelo grande (8192) se puede subir por env.
    reranker_window_tokens: int = 450

    # Umbral de abstención sobre el score del reranker: por debajo → gap ("no está en
    # los documentos"). Con el rerank por ventanas, la señal separa limpio (relevante
    # >= ~0.8, basura <= ~0.05), así que un umbral único basta y es robusto a escala
    # (el reranker juzga relevancia real por par consulta-chunk, no depende de cuántos
    # documentos haya). Valor de arranque, ajustable.
    relevance_threshold: float = 0.5


settings = Settings()
