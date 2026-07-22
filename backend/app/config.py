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
    # los documentos"). Calibrado con la batería de 56 preguntas sobre el corpus de
    # Proyecto Desnudo: con bge-reranker-v2-m3 el ruido (preguntas sin respuesta en los
    # documentos) puntúa <= ~0.04, mientras que los aciertos recuperables llegan a 0.6-
    # 1.0. En 0.15 no se cuela ningún falso positivo y se recuperan las preguntas mal
    # escritas que 0.5 descartaba de más. Reajustar cuando entre el corpus real (con
    # más chunks compitiendo, los scores bajan). Valor calibrado, ajustable.
    relevance_threshold: float = 0.15


settings = Settings()
