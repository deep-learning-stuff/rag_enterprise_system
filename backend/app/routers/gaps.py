import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_empresa_id_admin
from app.generation import GenerationError
from app.models.gap import Gap
from app.models.query_log import QueryLog
from app.schemas import BorradorIn, GapOut, IngestBorradorIn, PreguntaGapOut
from app.services import gaps as service

router = APIRouter(tags=["gaps"])


def _to_gap_out(gap: Gap, preguntas: list[QueryLog]) -> GapOut:
    return GapOut(
        id=gap.id,
        pregunta_representativa=gap.pregunta_representativa,
        n_ocurrencias=gap.n_ocurrencias,
        estado=gap.estado,
        borrador=gap.borrador,
        documento_id=gap.documento_id,
        posible_resuelto=gap.posible_resuelto,
        resuelto_por_doc_id=gap.resuelto_por_doc_id,
        primera_vez=gap.primera_vez,
        ultima_vez=gap.ultima_vez,
        preguntas=[
            PreguntaGapOut(id=log.id, pregunta=log.pregunta, fecha=log.fecha)
            for log in preguntas
        ],
    )


def _get_gap_or_404(db: Session, gap_id: int, empresa_id: int) -> Gap:
    gap = service.get_gap(db, gap_id, empresa_id)
    if gap is None:
        raise HTTPException(status_code=404, detail="Gap no encontrado")
    return gap


@router.get("/gaps", response_model=list[GapOut])
def list_gaps(
    empresa_id: int = Depends(get_empresa_id_admin), db: Session = Depends(get_db)
) -> list[GapOut]:
    """Gaps (preguntas sin respuesta, agrupadas), el más preguntado primero."""
    gaps = service.list_gaps(db, empresa_id)
    preguntas_por_gap = service.list_preguntas_por_gap(db, empresa_id)
    return [_to_gap_out(g, preguntas_por_gap.get(g.id, [])) for g in gaps]


# Antes de "/gaps/{gap_id}/..." para que "recheck" no se lea como un gap_id.
@router.post("/gaps/recheck", response_model=list[GapOut])
def recheck_gaps(
    empresa_id: int = Depends(get_empresa_id_admin), db: Session = Depends(get_db)
) -> list[GapOut]:
    """Re-comprueba los gaps abiertos: marca los que la base actualizada ya cubriría."""
    service.recheck_gaps(db, empresa_id)
    gaps = service.list_gaps(db, empresa_id)
    preguntas_por_gap = service.list_preguntas_por_gap(db, empresa_id)
    return [_to_gap_out(g, preguntas_por_gap.get(g.id, [])) for g in gaps]


@router.post("/gaps/{gap_id}/draft", response_model=GapOut)
def generate_draft(
    gap_id: int,
    empresa_id: int = Depends(get_empresa_id_admin),
    db: Session = Depends(get_db),
) -> GapOut:
    """Genera (o regenera) el esqueleto de documento para cubrir el gap."""
    gap = _get_gap_or_404(db, gap_id, empresa_id)
    try:
        gap = service.generar_borrador(db, gap)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"proveedor LLM no disponible: {exc}") from exc
    return _to_gap_out(gap, service.preguntas_de_gap(db, gap.id))


@router.put("/gaps/{gap_id}/draft", response_model=GapOut)
def save_draft(
    gap_id: int,
    body: BorradorIn,
    empresa_id: int = Depends(get_empresa_id_admin),
    db: Session = Depends(get_db),
) -> GapOut:
    """Guarda el texto del borrador editado por la persona."""
    gap = _get_gap_or_404(db, gap_id, empresa_id)
    try:
        gap = service.guardar_borrador(db, gap, body.borrador)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_gap_out(gap, service.preguntas_de_gap(db, gap.id))


@router.post("/gaps/{gap_id}/ingest", response_model=GapOut)
def ingest_draft(
    gap_id: int,
    body: IngestBorradorIn,
    empresa_id: int = Depends(get_empresa_id_admin),
    db: Session = Depends(get_db),
) -> GapOut:
    """Sube el borrador aprobado como documento nuevo (vuelve al pipeline de ingesta).

    El admin marca las áreas de acceso del documento (al menos una, de su empresa)."""
    gap = _get_gap_or_404(db, gap_id, empresa_id)
    try:
        gap = service.ingerir_borrador(db, gap, body.area_ids)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_gap_out(gap, service.preguntas_de_gap(db, gap.id))


@router.post("/gaps/{gap_id}/discard", response_model=GapOut)
def discard_gap(
    gap_id: int,
    empresa_id: int = Depends(get_empresa_id_admin),
    db: Session = Depends(get_db),
) -> GapOut:
    """Descarta el gap: no se redactará documento para él."""
    gap = _get_gap_or_404(db, gap_id, empresa_id)
    gap = service.descartar_gap(db, gap)
    return _to_gap_out(gap, service.preguntas_de_gap(db, gap.id))


@router.post("/gaps/{gap_id}/resolve", response_model=GapOut)
def resolve_gap(
    gap_id: int,
    empresa_id: int = Depends(get_empresa_id_admin),
    db: Session = Depends(get_db),
) -> GapOut:
    """Confirma que el gap ya está cubierto por un documento existente → `resuelto`."""
    gap = _get_gap_or_404(db, gap_id, empresa_id)
    try:
        gap = service.confirmar_resuelto(db, gap)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_gap_out(gap, service.preguntas_de_gap(db, gap.id))


@router.post("/gaps/{gap_id}/ignore-resolved", response_model=GapOut)
def ignore_resolved_gap(
    gap_id: int,
    empresa_id: int = Depends(get_empresa_id_admin),
    db: Session = Depends(get_db),
) -> GapOut:
    """Ignora la marca de posible resolución; el gap sigue abierto."""
    gap = _get_gap_or_404(db, gap_id, empresa_id)
    gap = service.ignorar_resuelto(db, gap)
    return _to_gap_out(gap, service.preguntas_de_gap(db, gap.id))
