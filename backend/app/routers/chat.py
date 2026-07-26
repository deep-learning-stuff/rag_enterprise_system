"""Chat persistente (Fase C): conversaciones y mensajes de un usuario.

Cada usuario ve y opera SOLO sus conversaciones (aislamiento por usuario, además del de
empresa). El RAG es por empresa, así que un superadmin (sin empresa) queda fuera vía
`get_empresa_id`. La restricción por áreas se aplica al recuperar (`get_restriccion_areas`).
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, get_empresa_id, get_restriccion_areas
from app.generation import GenerationError
from app.models.conversacion import Conversacion
from app.models.mensaje import Mensaje
from app.models.usuario import Usuario
from app.schemas import (
    ConversacionDetalleOut,
    ConversacionOut,
    MensajeIn,
    MensajeOut,
    SearchResultOut,
)
from app.services import chat as service

router = APIRouter(prefix="/conversaciones", tags=["chat"])


def _to_mensaje_out(m: Mensaje) -> MensajeOut:
    return MensajeOut(
        id=m.id,
        rol=m.rol,
        texto=m.texto,
        consulta_resuelta=m.consulta_resuelta,
        answered=m.answered,
        reason=m.reason,
        citas=[SearchResultOut(**c) for c in (m.citas or [])],
        creado=m.creado,
    )


def _detalle(db: Session, conv: Conversacion) -> ConversacionDetalleOut:
    return ConversacionDetalleOut(
        id=conv.id,
        titulo=conv.titulo,
        creada=conv.creada,
        actualizada=conv.actualizada,
        mensajes=[_to_mensaje_out(m) for m in service.mensajes_de(db, conv.id)],
    )


def _procesar(fn):
    """Ejecuta la orquestación traduciendo los fallos del LLM a HTTP (como /answer)."""
    try:
        return fn()
    except GenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"proveedor LLM no disponible: {exc}"
        ) from exc


@router.get("", response_model=list[ConversacionOut])
def list_conversaciones(
    usuario: Usuario = Depends(get_current_user),
    empresa_id: int = Depends(get_empresa_id),
    db: Session = Depends(get_db),
) -> list[ConversacionOut]:
    """Conversaciones del usuario, la más activa primero."""
    return [
        ConversacionOut.model_validate(c)
        for c in service.listar_conversaciones(db, empresa_id, usuario.id)
    ]


@router.post("", response_model=ConversacionDetalleOut, status_code=201)
def crear_conversacion(
    body: MensajeIn,
    usuario: Usuario = Depends(get_current_user),
    empresa_id: int = Depends(get_empresa_id),
    area_ids: list[int] | None = Depends(get_restriccion_areas),
    db: Session = Depends(get_db),
) -> ConversacionDetalleOut:
    """Abre una conversación nueva con el primer mensaje (título = ese mensaje truncado)."""
    texto = body.mensaje.strip()
    if not texto:
        raise HTTPException(status_code=422, detail="El mensaje no puede estar vacío")
    conv = _procesar(
        lambda: service.crear_conversacion(db, empresa_id, usuario.id, texto, area_ids)
    )
    return _detalle(db, conv)


@router.get("/{conv_id}", response_model=ConversacionDetalleOut)
def get_conversacion(
    conv_id: int,
    usuario: Usuario = Depends(get_current_user),
    empresa_id: int = Depends(get_empresa_id),
    db: Session = Depends(get_db),
) -> ConversacionDetalleOut:
    conv = service.get_conversacion(db, conv_id, empresa_id, usuario.id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return _detalle(db, conv)


@router.post("/{conv_id}/mensajes", response_model=list[MensajeOut])
def enviar_mensaje(
    conv_id: int,
    body: MensajeIn,
    usuario: Usuario = Depends(get_current_user),
    empresa_id: int = Depends(get_empresa_id),
    area_ids: list[int] | None = Depends(get_restriccion_areas),
    db: Session = Depends(get_db),
) -> list[MensajeOut]:
    """Envía un seguimiento y devuelve los dos mensajes nuevos (usuario y asistente)."""
    texto = body.mensaje.strip()
    if not texto:
        raise HTTPException(status_code=422, detail="El mensaje no puede estar vacío")
    conv = service.get_conversacion(db, conv_id, empresa_id, usuario.id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    m_user, m_bot = _procesar(
        lambda: service.responder(db, conv, texto, empresa_id, area_ids)
    )
    return [_to_mensaje_out(m_user), _to_mensaje_out(m_bot)]


@router.delete("/{conv_id}", status_code=204)
def borrar_conversacion(
    conv_id: int,
    usuario: Usuario = Depends(get_current_user),
    empresa_id: int = Depends(get_empresa_id),
    db: Session = Depends(get_db),
) -> None:
    conv = service.get_conversacion(db, conv_id, empresa_id, usuario.id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    service.eliminar_conversacion(db, conv)
