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
from app.generation import generator
from app.models.document import Document
from app.models.gap import Gap
from app.models.query_log import QueryLog
from app.retrieval.search import hybrid_search
from app.services import documents as documents_service

# Estados en los que un gap sigue "abierto" y tiene sentido re-comprobarlo.
_ESTADOS_ABIERTOS = ("pendiente", "borrador")


def find_or_create_gap(db: Session, pregunta: str, empresa_id: int) -> Gap:
    vec = embedder.embed([pregunta])[0]

    # El agrupado es POR empresa: una pregunta solo se suma a un gap de su misma empresa.
    row = db.execute(
        select(Gap, Gap.embedding.cosine_distance(vec).label("distance"))
        .where(Gap.empresa_id == empresa_id)
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

    gap = Gap(
        pregunta_representativa=pregunta, embedding=vec, n_ocurrencias=1, empresa_id=empresa_id
    )
    db.add(gap)
    db.flush()
    return gap


def list_gaps(db: Session, empresa_id: int) -> list[Gap]:
    """Gaps de la empresa, ordenados por cuánto se repiten: el más preguntado primero."""
    return list(
        db.scalars(
            select(Gap)
            .where(Gap.empresa_id == empresa_id)
            .order_by(Gap.n_ocurrencias.desc())
        )
    )


def list_preguntas_por_gap(db: Session, empresa_id: int) -> dict[int, list[QueryLog]]:
    """Preguntas literales absorbidas por cada gap de la empresa, para expandirlo en el panel."""
    logs = db.scalars(
        select(QueryLog)
        .where(QueryLog.empresa_id == empresa_id)
        .where(QueryLog.gap_id.isnot(None))
        .order_by(QueryLog.fecha.desc())
    )
    por_gap: dict[int, list[QueryLog]] = {}
    for log in logs:
        por_gap.setdefault(log.gap_id, []).append(log)
    return por_gap


# --- Borradores: ciclo editorial de un gap (pendiente -> borrador -> ingerido/descartado) ---


def get_gap(db: Session, gap_id: int, empresa_id: int) -> Gap | None:
    """Gap por id, SOLO si pertenece a la empresa (aislamiento por tenant).

    Si el gap es de otra empresa se devuelve None, igual que si no existiera: el router
    responde 404 y así no se filtra ni la existencia de gaps ajenos.
    """
    gap = db.get(Gap, gap_id)
    if gap is None or gap.empresa_id != empresa_id:
        return None
    return gap


def preguntas_de_gap(db: Session, gap_id: int) -> list[QueryLog]:
    """Preguntas literales absorbidas por un gap concreto (la más reciente primero)."""
    return list(
        db.scalars(
            select(QueryLog)
            .where(QueryLog.gap_id == gap_id)
            .order_by(QueryLog.fecha.desc())
        )
    )


def _preguntas_literales(db: Session, gap_id: int) -> list[str]:
    """Solo el texto de cada pregunta del gap (para acotar el borrador)."""
    return [log.pregunta for log in preguntas_de_gap(db, gap_id)]


def generar_borrador(db: Session, gap: Gap) -> Gap:
    """Genera (o regenera) el esqueleto Markdown del gap y lo deja en estado `borrador`.

    No se puede regenerar un gap ya ingerido: su documento ya vive en la base.
    """
    if gap.estado == "ingerido":
        raise ValueError("El gap ya se ingirió; su documento ya está en la base.")
    texto = generator.generate_draft(
        gap.pregunta_representativa, _preguntas_literales(db, gap.id)
    )
    gap.borrador = texto
    gap.estado = "borrador"
    db.commit()
    db.refresh(gap)
    return gap


def guardar_borrador(db: Session, gap: Gap, texto: str) -> Gap:
    """Guarda el texto del borrador editado por la persona."""
    if gap.estado not in ("borrador", "pendiente"):
        raise ValueError(f"No se puede editar el borrador de un gap en estado {gap.estado!r}.")
    gap.borrador = texto
    gap.estado = "borrador"
    db.commit()
    db.refresh(gap)
    return gap


def ingerir_borrador(db: Session, gap: Gap, area_ids: list[int]) -> Gap:
    """Ingesta el borrador como documento nuevo y marca el gap como `ingerido`.

    Cierra el ciclo del panel de gaps: el borrador aprobado vuelve al pipeline de
    ingesta (parse -> chunk -> embed) y queda enlazado al gap vía `documento_id`.

    `area_ids` son las áreas que el admin marca al subir (al menos una, de la empresa);
    el documento NO hereda automáticamente todas las áreas: quien lo sube decide su
    alcance, igual que en una subida normal (validación en `set_document_areas`).
    """
    if gap.estado != "borrador":
        raise ValueError("Solo se puede subir un borrador activo (genéralo primero).")
    if not gap.borrador or not gap.borrador.strip():
        raise ValueError("El gap no tiene borrador que ingerir.")
    doc = documents_service.create_document_from_text(
        db,
        texto=gap.borrador,
        nombre=f"gap-{gap.id}-{gap.pregunta_representativa[:60]}",
        empresa_id=gap.empresa_id,  # el documento nace en la misma empresa que el gap
        area_ids=area_ids,
    )
    gap.documento_id = doc.id
    gap.estado = "ingerido"
    db.commit()
    db.refresh(gap)
    return gap


def descartar_gap(db: Session, gap: Gap) -> Gap:
    """Marca el gap como `descartado` (no se redactará documento para él)."""
    gap.estado = "descartado"
    db.commit()
    db.refresh(gap)
    return gap


# --- Re-chequeo: ¿algún gap abierto ya está cubierto por documentos nuevos? ---


def recheck_gaps(db: Session, empresa_id: int) -> list[Gap]:
    """Re-comprueba los gaps abiertos contra la base ya actualizada (sin LLM).

    Para cada gap `pendiente`/`borrador` re-lanza SOLO el retrieval (`hybrid_search`, que
    ya aplica el umbral del reranker). Si vuelve a superar el umbral Y el documento que lo
    cubre es MÁS NUEVO que la última vez que el gap falló (`ultima_vez`), lo marca como
    `posible_resuelto` apuntando a ese documento. El filtro por fecha evita falsos
    positivos: un gap creado porque el LLM se abstuvo (con el retrieval ya pasando) no se
    marcaría sin que haya entrado contenido nuevo de verdad.

    No cierra ningún gap: solo pone la marca para que un humano confirme o la ignore.
    """
    gaps = db.scalars(
        select(Gap)
        .where(Gap.empresa_id == empresa_id)
        .where(Gap.estado.in_(_ESTADOS_ABIERTOS))
    ).all()
    for gap in gaps:
        candidatos = hybrid_search(db, gap.pregunta_representativa, gap.empresa_id)
        cubre_doc_id = None
        for c in candidatos:
            doc = db.get(Document, c.chunk.doc_id)
            if doc is not None and doc.fecha_subida > gap.ultima_vez:
                cubre_doc_id = doc.id
                break
        gap.posible_resuelto = cubre_doc_id is not None
        gap.resuelto_por_doc_id = cubre_doc_id
    db.commit()
    return list(gaps)


def confirmar_resuelto(db: Session, gap: Gap) -> Gap:
    """Confirma que el gap ya está cubierto por un documento existente → `resuelto`."""
    if not gap.posible_resuelto:
        raise ValueError("Este gap no está marcado como posible resuelto.")
    gap.estado = "resuelto"
    gap.posible_resuelto = False  # ya resuelto: la marca de "quizá" deja de aplicar
    db.commit()
    db.refresh(gap)
    return gap


def ignorar_resuelto(db: Session, gap: Gap) -> Gap:
    """Descarta la marca de posible resolución; el gap sigue abierto."""
    gap.posible_resuelto = False
    gap.resuelto_por_doc_id = None
    db.commit()
    db.refresh(gap)
    return gap
