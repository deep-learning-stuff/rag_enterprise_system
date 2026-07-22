"""Agrupado incremental de gaps: preguntas sin respuesta que son la misma pregunta.

Cada pregunta sin respuesta se compara por similitud coseno contra los gaps ya
existentes (misma consulta pgvector que `vector_search`, aplicada a preguntas en vez
de a chunks). Si el más parecido supera el umbral, se le suma (el embedding del gap se
actualiza como media móvil); si no, se abre un gap nuevo.

Deliberadamente greedy y sin reclustering por lotes: un gap es una fila estable en el
tiempo, no algo que se recomponga solo, porque encima se pondrá estado editorial
(fase de borradores) que se perdería si el agrupado se recalculase desde cero.

`gap_max_distance` es un punto de arranque (equivale a similitud coseno ~0.92), no
está calibrado con datos reales como `relevance_threshold` — falta acumular gaps de
verdad para afinarlo igual que se hizo con el umbral de rerank.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.embeddings import embedder
from app.models.gap import Gap
from app.models.query_log import QueryLog


def find_or_create_gap(db: Session, pregunta: str) -> Gap:
    vec = embedder.embed([pregunta])[0]

    row = db.execute(
        select(Gap, Gap.embedding.cosine_distance(vec).label("distance"))
        .order_by("distance")
        .limit(1)
    ).first()

    if row is not None:
        gap, distance = row
        if distance <= settings.gap_max_distance:
            n = gap.n_ocurrencias
            gap.embedding = [(c * n + v) / (n + 1) for c, v in zip(gap.embedding, vec)]
            gap.n_ocurrencias = n + 1
            db.flush()
            return gap

    gap = Gap(pregunta_representativa=pregunta, embedding=vec, n_ocurrencias=1)
    db.add(gap)
    db.flush()
    return gap


def list_gaps(db: Session) -> list[Gap]:
    """Gaps ordenados por cuánto se repiten: el más preguntado primero."""
    return list(db.scalars(select(Gap).order_by(Gap.n_ocurrencias.desc())))


def list_preguntas_por_gap(db: Session) -> dict[int, list[QueryLog]]:
    """Preguntas literales absorbidas por cada gap, para poder expandirlo en el panel."""
    logs = db.scalars(
        select(QueryLog).where(QueryLog.gap_id.isnot(None)).order_by(QueryLog.fecha.desc())
    )
    por_gap: dict[int, list[QueryLog]] = {}
    for log in logs:
        por_gap.setdefault(log.gap_id, []).append(log)
    return por_gap
