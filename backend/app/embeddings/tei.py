import httpx

from app.embeddings.base import Embedder


class TEIEmbedder(Embedder):
    """Cliente de HuggingFace Text Embeddings Inference (TEI).

    Llama al endpoint `/embed` del servidor. TEI limita el tamaño de lote por petición
    (por defecto 32), así que troceamos la entrada en sub-lotes.
    """

    def __init__(self, base_url: str, *, batch_size: int = 32, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.batch_size = batch_size
        # Cliente reutilizado: mantiene un pool de conexiones vivas (keep-alive) hacia TEI
        # en vez de abrir y cerrar un socket TCP en cada llamada. httpx.Client es
        # thread-safe, así que las peticiones que corren en paralelo en el threadpool de
        # FastAPI pueden compartirlo sin pisarse.
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            resp = self._client.post("/embed", json={"inputs": batch})
            resp.raise_for_status()
            vectors.extend(resp.json())
        return vectors
