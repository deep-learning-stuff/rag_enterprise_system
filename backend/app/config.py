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
    # los documentos"). CALIBRADO PARA gte-multilingual-reranker-base (el reranker actual;
    # sus scores son más bajos que los de bge-reranker-v2-m3, que usaba ~0.15).
    # Batería sobre el corpus de Proyecto Desnudo (22 respondibles + 11 de ruido):
    #   - respondibles: 0.53 a 0.97
    #   - ruido: casi todo <0.08, con 3 borderline fuera de dominio hasta 0.40
    #   - hueco limpio entre 0.40 (ruido más alto) y 0.53 (respondible más baja)
    # 0.42 cae en ese hueco: retiene las 22 respondibles y rechaza todo el ruido, con
    # margen amplio del lado de las respondibles (el error caro es rechazar una respuesta
    # buena; un ruido que se cuele lo caza igual la abstención del LLM). Reajustar al
    # crecer el corpus (más chunks compitiendo → los scores bajan). Si se vuelve a bge,
    # recalibrar (rondaba 0.15). Valor calibrado, ajustable.
    relevance_threshold: float = 0.42

    # Generación (Fase 5). LLM en la nube, configurable por proveedor igual que el
    # reranker: cambiar de proveedor/modelo es cambiar el .env, no el código.
    # - "gemini": capa gratuita en desarrollo (NO válida para uso comercial en la UE;
    #   al pasar a producción con empresas, cambiar de proveedor o a la capa de pago).
    # - "openai": de pago desde el primer token, sin esa restricción.
    llm_provider: str = "gemini"  # "gemini" | "openai"
    llm_model: str = ""  # vacío = modelo por defecto del proveedor (ver generation/)
    gemini_api_key: str = ""
    openai_api_key: str = ""
    llm_timeout: float = 60.0

    # Agrupado de gaps (fase siguiente): distancia coseno máxima para que una pregunta
    # sin respuesta se sume a un gap existente en vez de abrir uno nuevo (~0.08 equivale
    # a similitud ~0.92). Punto de arranque, NO calibrado con datos reales todavía (a
    # diferencia de `relevance_threshold`) — reajustar cuando haya gaps de verdad.
    gap_max_distance: float = 0.08

    # Auth / sesiones (Fase B). La empresa ya no viene por cabecera: sale del usuario
    # autenticado (ver app.deps.get_empresa_id).
    session_cookie_name: str = "session"
    session_ttl_hours: int = 24 * 7  # duración de una sesión
    invite_ttl_hours: int = 24 * 7  # caducidad de una invitación (7 días)
    password_min_length: int = 8  # longitud mínima al fijar contraseña
    # Marcar la cookie como Secure (solo HTTPS). False en desarrollo local (http);
    # poner a True en producción.
    cookie_secure: bool = False


settings = Settings()
