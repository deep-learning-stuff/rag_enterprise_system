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
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            resp = httpx.post(
                f"{self.base_url}/embed",
                json={"inputs": batch},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            vectors.extend(resp.json())
        return vectors
