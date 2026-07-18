import httpx

from app.reranking.base import Reranker


class TEIReranker(Reranker):
    """Cliente del endpoint `/rerank` de TEI (modelo bge-reranker-v2-m3).

    TEI devuelve `[{"index": i, "score": s}, ...]` ordenado por score; lo recolocamos
    en el orden original de `texts` para que quien llama empareje score con candidato.
    """

    def __init__(self, base_url: str, *, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        resp = httpx.post(
            f"{self.base_url}/rerank",
            json={"query": query, "texts": texts},
            timeout=self.timeout,
        )
        resp.raise_for_status()

        scores = [0.0] * len(texts)
        for item in resp.json():
            scores[item["index"]] = item["score"]
        return scores
