"""Orquestación de respuesta grounded (Fase 5): retrieval → LLM → validación de citas.

Aquí viven los invariantes de CLAUDE.md que no dependen del proveedor:
- si el retrieval no supera el umbral, NO se llama al LLM (abstención directa);
- una respuesta sin citas válidas se trata como no respondida;
- nunca se fuerza una respuesta;
- toda consulta se loguea (`QueryLog`), sea cual sea el resultado.

El `reason` de cada abstención se conserva porque es la materia prima de los gaps
(fase siguiente): distingue "no hay documentos sobre esto" de "el modelo no supo
usarlos".
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.generation import ContextChunk, generator
from app.models.query_log import QueryLog
from app.retrieval.search import Candidate, hybrid_search
from app.services.gaps import find_or_create_gap


@dataclass
class AnswerData:
    """Resultado de la orquestación, en términos de dominio (sin esquemas HTTP)."""

    answered: bool
    answer: str | None
    reason: str | None  # motivo de la abstención; None si hay respuesta
    citations: list[Candidate]  # chunks citados, con su traza de scoring


def _log_query(
    db: Session,
    query: str,
    empresa_id: int,
    candidates: list[Candidate],
    cited_ids: set[int],
    answered: bool,
    reason: str | None,
    crear_gap: bool = True,
) -> None:
    chunks = [
        {
            "chunk_id": c.chunk.id,
            "rerank_score": c.rerank_score,
            "cosine": c.cosine,
            "rrf_score": c.rrf_score,
            "citado": c.chunk.id in cited_ids,
        }
        for c in candidates
    ]
    # La consulta SIEMPRE se registra (invariante), pero no toda abstención abre un gap:
    # `crear_gap=False` para las que no son un hueco de conocimiento (p.ej. falta de acceso).
    gap_id = (
        find_or_create_gap(db, query, empresa_id).id
        if not answered and crear_gap
        else None
    )
    db.add(
        QueryLog(
            pregunta=query,
            empresa_id=empresa_id,
            answered=answered,
            reason=reason,
            chunks=chunks,
            gap_id=gap_id,
        )
    )
    db.commit()


def answer_query(
    db: Session, query: str, empresa_id: int, area_ids: list[int] | None = None
) -> AnswerData:
    candidates = hybrid_search(db, query, empresa_id, area_ids)
    if not candidates:
        # Nada en las áreas del usuario. Antes de abrir un gap, hay que distinguir
        # "no existe" de "existe pero fuera de tu alcance": si SIN filtro de áreas sí hay
        # contenido en la empresa, no es un hueco de conocimiento sino de acceso. El
        # usuario se abstiene igual (nunca ve lo que no le toca), pero NO se crea gap.
        if area_ids is not None and hybrid_search(db, query, empresa_id, None):
            _log_query(
                db, query, empresa_id, [], set(),
                answered=False, reason="fuera_de_alcance", crear_gap=False,
            )
            return AnswerData(
                answered=False, answer=None, reason="fuera_de_alcance", citations=[]
            )
        # Ningún chunk superó el umbral (tampoco en la empresa): gap real.
        _log_query(db, query, empresa_id, [], set(), answered=False, reason="sin_candidatos")
        return AnswerData(answered=False, answer=None, reason="sin_candidatos", citations=[])

    context = [ContextChunk(chunk_id=c.chunk.id, texto=c.chunk.texto) for c in candidates]
    try:
        result = generator.generate(query, context)
    except ValueError:
        # El modelo devolvió algo que no cumple el contrato: no se fuerza respuesta.
        _log_query(db, query, empresa_id, candidates, set(), answered=False, reason="salida_invalida")
        return AnswerData(answered=False, answer=None, reason="salida_invalida", citations=[])

    if not result.answered or not result.answer:
        _log_query(db, query, empresa_id, candidates, set(), answered=False, reason="llm_abstuvo")
        return AnswerData(answered=False, answer=None, reason="llm_abstuvo", citations=[])

    cited_ids = set(result.citations)
    valid_ids = {c.chunk.id for c in candidates}
    if not cited_ids or not cited_ids <= valid_ids:
        # Cita vacía o apuntando a un chunk que no estaba en el contexto → inválida.
        _log_query(db, query, empresa_id, candidates, set(), answered=False, reason="citas_invalidas")
        return AnswerData(answered=False, answer=None, reason="citas_invalidas", citations=[])

    cited = [c for c in candidates if c.chunk.id in cited_ids]
    _log_query(db, query, empresa_id, candidates, cited_ids, answered=True, reason=None)
    return AnswerData(answered=True, answer=result.answer, reason=None, citations=cited)
