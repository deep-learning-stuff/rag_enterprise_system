"""Recuperación híbrida (Fase 4): vectorial + full-text → RRF → rerank → umbral.

Pasos:
1. Vectorial: encuentra chunks por SIGNIFICADO (aunque no compartan palabras).
2. Full-text: encuentra chunks por PALABRAS exactas (términos concretos, códigos).
3. RRF: fusiona ambas listas por posición (scores no comparables entre sí).
4. Rerank: un modelo re-puntúa la relevancia real de cada candidato.
5. Umbral: si ni el mejor supera el umbral → se devuelve vacío (abstención).
"""

from dataclasses import dataclass

from sqlalchemy import func, select
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


def fulltext_search(db: Session, query: str, k: int) -> list[Chunk]:
    """Top-K chunks por coincidencia full-text (tsvector + índice GIN)."""
    tsquery = func.plainto_tsquery("spanish", query)
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
        )
        for c, score in zip(pool, rerank_scores)
    ]

    # Umbral de abstención + orden final por relevancia del reranker.
    relevantes = [c for c in candidates if c.rerank_score >= settings.relevance_threshold]
    relevantes.sort(key=lambda c: c.rerank_score, reverse=True)
    return relevantes[: settings.final_n]
