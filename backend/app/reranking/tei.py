import logging
import time

import httpx

from app.ingest.tokenizer import split_into_windows
from app.reranking.base import Reranker

logger = logging.getLogger(__name__)


class TEIReranker(Reranker):
    """Cliente del endpoint `/rerank` de TEI (modelo bge-reranker-v2-m3).

    TEI devuelve `[{"index": i, "score": s}, ...]` ordenado por score; lo recolocamos
    en el orden original de `texts` para que quien llama empareje score con candidato.

    Rerank por ventanas: cada texto se parte en ventanas que caben en el límite del
    modelo (~512 tokens en el ligero) y el score del texto es el MÁXIMO de sus ventanas.
    Así el reranker "lee" el chunk entero aunque la parte relevante esté al final; sin
    esto, `truncate` recortaría la cola de los chunks largos y la infravaloraría.
    """

    def __init__(
        self,
        base_url: str,
        *,
        window_tokens: int = 450,
        batch_size: int = 8,
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.window_tokens = window_tokens
        self.batch_size = batch_size
        # Cliente reutilizado (keep-alive), igual que en el embedder: evita abrir un
        # socket nuevo por cada sublote de rerank. Thread-safe, compartible entre hilos.
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        # Se aplana cada texto en sus ventanas, recordando a qué texto pertenece cada
        # una; tras puntuarlas todas, cada texto se queda con el score máximo.
        t0 = time.perf_counter()
        windows: list[str] = []
        owner: list[int] = []
        for i, text in enumerate(texts):
            for w in split_into_windows(text, self.window_tokens):
                windows.append(w)
                owner.append(i)

        win_scores = self._score(query, windows)

        scores = [float("-inf")] * len(texts)
        for i, s in zip(owner, win_scores):
            if s > scores[i]:
                scores[i] = s

        # Traza para diagnosticar la latencia del rerank: nº de ventanas = pasadas reales
        # del modelo. Si ventanas≈textos pero el tiempo es alto, el coste es POR PASADA
        # (modelo pesado en CPU → mirar ONNX/int8); si ventanas≫textos, el coste es el
        # NÚMERO de pasadas (→ mirar rerank_pool / tamaño de ventana).
        logger.info(
            "rerank: %d textos → %d ventanas en %.0f ms",
            len(texts),
            len(windows),
            (time.perf_counter() - t0) * 1000,
        )
        return [s if s != float("-inf") else 0.0 for s in scores]

    def _score(self, query: str, texts: list[str]) -> list[float]:
        # `truncate`: red de seguridad si `query` + ventana superasen el máximo del
        # modelo. Se envía en sub-lotes para no pasar del presupuesto de tokens por
        # petición (evita el 413 Payload Too Large).
        scores = [0.0] * len(texts)
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            resp = self._client.post(
                "/rerank",
                json={"query": query, "texts": batch, "truncate": True},
            )
            resp.raise_for_status()
            for item in resp.json():
                scores[start + item["index"]] = item["score"]
        return scores
