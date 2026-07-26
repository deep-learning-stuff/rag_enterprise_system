from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginIn(BaseModel):
    """Credenciales de acceso."""

    email: str
    password: str


class UsuarioOut(BaseModel):
    """Usuario hacia el frontend. No expone `password_hash`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nombre: str
    rol: str
    empresa_id: int | None
    empresa_nombre: str | None = None
    activo: bool
    invitacion_pendiente: bool


class AceptarInvitacionIn(BaseModel):
    """El usuario invitado fija su contraseña usando el token del enlace."""

    token: str
    password: str


class EmpresaIn(BaseModel):
    """Alta de empresa (solo superadmin)."""

    nombre: str


class EmpresaOut(BaseModel):
    """Empresa hacia el frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    creada: datetime


class UsuarioCrearIn(BaseModel):
    """Alta de usuario por invitación. `empresa_id` es obligatorio para superadmin e
    ignorado para admin (siempre su propia empresa)."""

    email: str
    nombre: str
    rol: str  # "admin" | "usuario"
    empresa_id: int | None = None


class UsuarioCreadoOut(BaseModel):
    """Usuario recién creado + el enlace de invitación (a copiar y enviar)."""

    usuario: UsuarioOut
    enlace_invitacion: str


class EnlaceInvitacionOut(BaseModel):
    """Enlace de una invitación regenerada."""

    enlace_invitacion: str


class AreaIn(BaseModel):
    """Alta o renombrado de un área (el nombre; la empresa sale del admin autenticado)."""

    nombre: str


class AreaOut(BaseModel):
    """Área hacia el frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class UsuarioAreasIn(BaseModel):
    """Áreas a asignar a un usuario (reemplazan las actuales). Puede ir vacía (no ve nada)."""

    area_ids: list[int]


class DocumentOut(BaseModel):
    """Representación de un documento hacia el frontend. No expone `storage_ref`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    tipo: str
    estado: str
    fecha_subida: datetime
    area_ids: list[int]


class DocumentAreasIn(BaseModel):
    """Áreas a asignar a un documento (reemplazan las actuales). Al menos una."""

    area_ids: list[int]


class ChunkOut(BaseModel):
    """Un chunk hacia el frontend (para inspeccionar el troceo)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    page_start: int | None
    page_end: int | None
    section: str | None
    chunk_index: int
    texto: str


class SearchQuery(BaseModel):
    """Petición de búsqueda."""

    query: str


class SearchResultOut(BaseModel):
    """Un chunk recuperado con su traza de scoring."""

    chunk_id: int
    doc_id: int
    chunk_index: int
    page_start: int | None
    page_end: int | None
    texto: str
    rerank_score: float | None
    cosine: float | None
    rrf_score: float
    vector_rank: int | None
    text_rank: int | None


class PreguntaGapOut(BaseModel):
    """Una de las preguntas literales absorbidas por un gap."""

    id: int
    pregunta: str
    fecha: datetime


class GapOut(BaseModel):
    """Gap: grupo de preguntas sin respuesta que son, en esencia, la misma pregunta."""

    id: int
    pregunta_representativa: str
    n_ocurrencias: int
    estado: str
    borrador: str | None
    documento_id: int | None
    posible_resuelto: bool
    resuelto_por_doc_id: int | None
    primera_vez: datetime
    ultima_vez: datetime
    preguntas: list[PreguntaGapOut]


class BorradorIn(BaseModel):
    """Texto del borrador editado por la persona antes de subirlo."""

    borrador: str


class IngestBorradorIn(BaseModel):
    """Áreas a las que se sube el documento nacido del borrador (al menos una)."""

    area_ids: list[int]


class MensajeIn(BaseModel):
    """Un mensaje del usuario (pregunta o seguimiento)."""

    mensaje: str


class MensajeOut(BaseModel):
    """Mensaje de una conversación hacia el frontend.

    En los del usuario, `consulta_resuelta` trae la versión autónoma con la que se
    recuperó, si hubo que reescribir un seguimiento. En los del asistente, `citas` son las
    fuentes (mismo formato que una búsqueda) y `reason` el motivo si se abstuvo.
    """

    id: int
    rol: str
    texto: str | None
    consulta_resuelta: str | None
    answered: bool | None
    reason: str | None
    citas: list[SearchResultOut]
    creado: datetime


class ConversacionOut(BaseModel):
    """Conversación en la lista (sin mensajes)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    creada: datetime
    actualizada: datetime


class ConversacionDetalleOut(BaseModel):
    """Conversación con todos sus mensajes."""

    id: int
    titulo: str
    creada: datetime
    actualizada: datetime
    mensajes: list[MensajeOut]


class AnswerOut(BaseModel):
    """Respuesta grounded (Fase 5). Si `answered` es False, `reason` dice por qué:

    - "sin_candidatos": ningún chunk superó el umbral de relevancia (gap claro).
    - "fuera_de_alcance": no hay nada en las áreas del usuario, pero el contenido SÍ existe
      en la empresa (falta de acceso, no de conocimiento): no se abre gap.
    - "llm_abstuvo": había candidatos pero el modelo no encontró la respuesta en ellos.
    - "citas_invalidas": el modelo respondió pero citando chunks fuera del contexto.
    - "salida_invalida": el modelo no devolvió el JSON del contrato.
    """

    answered: bool
    answer: str | None
    reason: str | None
    citations: list[SearchResultOut]
