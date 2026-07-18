import httpx

from app.reranking.base import Reranker


class TEIReranker(Reranker):
    """Cliente del endpoint `/rerank` de TEI (modelo bge-reranker-v2-m3).

    TEI devuelve `[{"index": i, "score": s}, ...]` ordenado por score; lo recolocamos
    en el orden original de `texts` para que quien llama empareje score con candidato.
    """

    def __init__(self, base_url: str, *, batch_size: int = 8, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.batch_size = batch_size
        self.timeout = timeout

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        # `truncate`: recorta cada texto al máximo del modelo (los chunks pueden exceder
        # los 512 tokens del reranker). Se envía en sub-lotes para no pasar del
        # presupuesto de tokens por petición (evita el 413 Payload Too Large).
        scores = [0.0] * len(texts)
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            resp = httpx.post(
                f"{self.base_url}/rerank",
                json={"query": query, "texts": batch, "truncate": True},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            for item in resp.json():
                scores[start + item["index"]] = item["score"]
        return scores
