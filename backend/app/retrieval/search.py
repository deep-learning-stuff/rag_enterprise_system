"""Recuperación híbrida (Fase 4): vectorial + full-text → RRF → rerank → umbral.

Pasos:
1. Vectorial: encuentra chunks por SIGNIFICADO (aunque no compartan palabras).
2. Full-text: encuentra chunks por PALABRAS exactas (términos concretos, códigos).
3. RRF: fusiona ambas listas por posición (scores no comparables entre sí).
4. Rerank: un modelo re-puntúa la relevancia real de cada candidato.
5. Umbral: si ni el mejor supera el umbral → se devuelve vacío (abstención).
"""

from dataclasses import dataclass

import numpy as np
from sqlalchemy import Text, func, select
from sqlalchemy.dialects.postgresql import TSQUERY
from sqlalchemy.orm import Session

from app.config import settings
from app.embeddings import embedder
from app.models.chunk import Chunk
from app.reranking import reranker


@dataclass
class Candidate:
    """Un chunk recuperado con su traza de scoring (para auditar y afinar)."""

    chunk: Chunk
    vector_rank: int | None
    text_rank: int | None
    rrf_score: float
    rerank_score: float | None = None
    cosine: float | None = None


def _cosine(a: list[float], b) -> float:
    """Similitud coseno entre el vector de la consulta y el embedding de un chunk."""
    if b is None:
        return 0.0  # chunk sin embedding (solo llegó por full-text): no verificable
    va = np.asarray(a, dtype=float)
    vb = np.asarray(b, dtype=float)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(va @ vb / denom) if denom else 0.0


def vector_search(db: Session, query_vec: list[float], k: int) -> list[Chunk]:
    """Top-K chunks por similitud coseno (pgvector + índice HNSW)."""
    return list(
        db.scalars(
            select(Chunk)
            .where(Chunk.embedding.isnot(None))
            .order_by(Chunk.embedding.cosine_distance(query_vec))
            .limit(k)
        )
    )


def _or_tsquery(config: str, query: str):
    """tsquery de `query` con sus términos unidos por OR en lugar de por AND.

    `plainto_tsquery` los une con `&`, lo que exige que TODAS las palabras estén en el
    chunk. Como una pregunta trae palabras que el documento no usa ("fórmula", "cómo"),
    el AND no casaba casi nunca y esta vía devolvía cero. Con OR basta con que coincidan
    algunas, y `ts_rank` ordena por cuántas y con qué peso. Los conectores no ensucian:
    la configuración española ya los descarta como stop words antes de llegar aquí.

    La sustitución de `&` por `|` se hace sobre la SALIDA de `plainto_tsquery`, no sobre
    el texto del usuario: así se conserva su parseo, stemming y saneado (construir un
    tsquery concatenando la entrada a mano sería una vía de inyección).
    """
    return func.replace(
        func.plainto_tsquery(config, query).cast(Text), "&", "|"
    ).cast(TSQUERY)


def fulltext_search(db: Session, query: str, k: int) -> list[Chunk]:
    """Top-K chunks por coincidencia full-text (tsvector + índice GIN).

    Se consulta con las dos configuraciones unidas (`||` sobre tsquery es un OR), las
    mismas con las que se genera `tsv`: `spanish` casa singular con plural y
    `spanish_unaccent` tolera la falta de tildes. Cada una cubre casos que la otra
    rompe; el porqué está detallado en la migración 0006.

    Si la pregunta es solo stop words, `plainto_tsquery` devuelve una tsquery vacía que
    no casa con nada: la consulta sale con 0 filas, que es justo lo que se quiere.
    """
    tsquery = _or_tsquery("spanish", query).op("||")(
        _or_tsquery("spanish_unaccent", query)
    )
    return list(
        db.scalars(
            select(Chunk)
            .where(Chunk.tsv.op("@@")(tsquery))
            .order_by(func.ts_rank(Chunk.tsv, tsquery).desc())
            .limit(k)
        )
    )


def reciprocal_rank_fusion(lists: list[list[Chunk]], k_const: int) -> dict[int, float]:
    """RRF: cada lista aporta 1/(k_const + posición) al score de cada chunk."""
    scores: dict[int, float] = {}
    for ranked in lists:
        for position, chunk in enumerate(ranked, start=1):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k_const + position)
    return scores


def hybrid_search(db: Session, query: str) -> list[Candidate]:
    """Pipeline completo: recupera, fusiona, reranquea y aplica el umbral.

    Devuelve los `final_n` chunks más relevantes por encima del umbral. Si ninguno lo
    supera, devuelve lista vacía (abstención: "no está en los documentos").
    """
    query_vec = embedder.embed([query])[0]

    vec_hits = vector_search(db, query_vec, settings.retrieval_k)
    text_hits = fulltext_search(db, query, settings.retrieval_k)

    vector_rank = {c.id: i for i, c in enumerate(vec_hits, start=1)}
    text_rank = {c.id: i for i, c in enumerate(text_hits, start=1)}
    scores = reciprocal_rank_fusion([vec_hits, text_hits], settings.rrf_k)

    by_id: dict[int, Chunk] = {c.id: c for c in [*vec_hits, *text_hits]}
    fused = sorted(by_id.values(), key=lambda c: scores[c.id], reverse=True)

    # Se reranquea solo un pool de los mejores fusionados (el rerank es más caro).
    pool = fused[: settings.rerank_pool]
    if not pool:
        return []

    rerank_scores = reranker.rerank(query, [c.texto for c in pool])
    candidates = [
        Candidate(
            chunk=c,
            vector_rank=vector_rank.get(c.id),
            text_rank=text_rank.get(c.id),
            rrf_score=scores[c.id],
            rerank_score=score,
            cosine=_cosine(query_vec, c.embedding),
        )
        for c, score in zip(pool, rerank_scores)
    ]

    # Abstención por el score del reranker (que se calcula por ventanas, así que "lee"
    # el chunk entero). Con esa señal, relevante y basura quedan muy separados, de modo
    # que un umbral único basta. El `cosine` se conserva en el candidato solo como traza
    # de depuración; no decide la abstención (su margen es demasiado estrecho para ser
    # fiable, ver config).
    relevantes = [c for c in candidates if c.rerank_score >= settings.relevance_threshold]
    relevantes.sort(key=lambda c: c.rerank_score, reverse=True)
    return relevantes[: settings.final_n]
